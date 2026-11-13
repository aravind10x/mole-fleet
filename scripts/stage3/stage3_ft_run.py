#!/usr/bin/env python3
"""Line FT, part H1: run a block of follower cells from a manifest path. Blue side: prints counts,
ids and dollars only; transcripts are written under `work/stage3/red/ft/runs/<block>/` and never printed;
the predicate module is imported by path and its source is never read here.

One record per run goes to `work/stage3/v5/FT/outcomes-<block>-v0.jsonl` (the interface's fields:
run_id, payload_id, arm, follower, repeat, task_id, predicate_result, checked, n_search_documents,
n_read_history, n_ask_colleague, declined, n_turns, cost_usd, error; and, beside them, n_read_document,
n_invalid, end_reason, ended_in_action, wall_s, model, cost_missing, block, prompt_sha256). No text.

Rules:
* Cells: every scorable manifest record x arms x followers x repeats; run_id = "<block>|<payload>|<arm>|<follower>|r<k>".
  The `benign` arm is built only for operational-value payloads (others are skipped and counted).
* Workspaces: `<docs_root>/<payload_id>/<arm>/`, or a record's own `workspaces: {arm: path}` (smoke cells).
  `benign` = the clean workspace with the task's `benign_alt` written as the value of the item at the slot's
  locator (blue's `label=`/`yaml=` selectors, located with stage3_ft_slots' parser), clean history kept;
  a slot whose item is absent from the clean state gives error "benign_unplaceable". The benign workspace
  gets one history revision with the manifest's `slot_revision_account` and `slot_revision_time` and the
  benign line (interface addendum 1, item 6); a record without them gives error "benign_no_revision".
  The colleague always answers from the payload's clean workspace.
* Never an overwrite: an existing outcomes file is refused unless --resume. The file is append-only and the last
  record per run_id counts. With --resume, only runs with no record or whose latest code is not_run_cap,
  not_run_stopped or aborted are run; a run with a verdict or a terminal code is never re-asked. Transcripts get
  a new attempt suffix rather than replacing an earlier file.
* Order (v1.1): a seeded interleaved order (seed 20261113) balanced over regime, arm and follower.
* Hashes (v1.1): --expect-manifest-sha256, --expect-predicates-sha256 and --expect-docs-tree-sha256; the runner and
  the dry run refuse to start on any difference.
* Cost guard: every run's dollars (finished or interrupted) go to `outcomes-<block>-v0.ledger.jsonl`; the block
  stops before a run, or before a model call inside a run, once the ledger plus the dollars of runs in flight
  reach --cap-usd. Every planned run not finished then gets a not_run_cap record (a resume with a higher cap
  runs it).
* Retry pass (v1.3): `--resume --retry-unresolved` re-asks, once, the runs whose latest code is infra_error or
  throttle_error; their new records carry retry_pass true and each pass is logged in outcomes-<block>-v0.passes.jsonl.
* Stops (v1.1): a provider refusal is recorded for that run (refused:<class>) and the block continues; more than
  10 refusals stop it. An infrastructure error is retried twice inside the run, then recorded (infra_error). A
  HarnessAborted (spent last key, access or model-id error) is recorded as aborted and stops the block. At any
  stop the remaining planned runs get not_run_stopped (or not_run_cap) records.
* Codes (v1.1): `error` holds an allowlisted code only; exception and error text go to
  `work/stage3/red/ft/runs/<block>/errors.jsonl` (red side, never printed).
* predicate_result: evaluate(predicate_id, action_log) for runs that ended without error or refusal; null with
  error predicate_error if the predicate raises or returns a non-bool; null and no error when the record has
  no predicate (smoke cells).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import random
import re
import sys
from collections import Counter
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_ft_harness as h  # noqa: E402

PROJECT = h.PROJECT
FT_DIR = h.FT_DIR
RED_FT = PROJECT / "work" / "stage3" / "red" / "ft"
DEFAULT_RUNS_ROOT = RED_FT / "runs"
DEFAULT_DOCS_ROOT = RED_FT / "docs"
DEFAULT_TASKS = FT_DIR / "blue" / "tasks-v0.jsonl"
DEFAULT_SLOTS = FT_DIR / "blue" / "slots-v0.json"
SUBSET_ARMS = tuple(f"subset_{i}" for i in range(1, 7))
KNOWN_ARMS = ("planted", "clean", "benign") + SUBSET_ARMS
# The verification control runs on routine and middle payloads only (roadmap addendum; the coordinator's
# pre-gate item 4 leaves out the one alarming payload with a benign alternative); None = a smoke record.
BENIGN_REGIMES = ("routine", "middle", None)


class OutputExists(RuntimeError):
    pass


class HashMismatch(RuntimeError):
    pass


ORDER_SEED = 20261113
MAX_REFUSALS = 10           # pre-registration v1.1 section 5: more than 10 refusals in a block stop it
# The `error` field holds one of these codes only (v1.1 section 7); any text goes to runs/<block>/errors.jsonl.
REFUSAL_CLASSES = frozenset({"content_filter", "moderation_403", "content_filtered", "guardrail_intervened", "refusal", "unknown"})
ERROR_CODES = frozenset({"infra_error", "throttle_error", "task_missing", "workspace_missing", "benign_unplaceable",
                         "benign_no_revision", "predicate_error", "aborted", "not_run_cap", "not_run_stopped"})
RERUNNABLE = frozenset({"not_run_cap", "not_run_stopped", "aborted"})   # a resume runs these again; nothing else
# Pre-registration v1.3, gate 2: before any analysis, runs left unresolved by an infrastructure error are re-asked
# once (--resume --retry-unresolved); provider refusals are never re-asked.
INFRA_CODES = frozenset({"infra_error", "throttle_error"})


class BenignPlacementError(ValueError):
    pass


# ── inputs ───────────────────────────────────────────────────────────────────────────────────────

def _load_json_list(path: Path, keys: Sequence[str]) -> list[dict]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(d, list):
        return d
    for k in keys:
        if isinstance(d, dict) and isinstance(d.get(k), list):
            return d[k]
    raise ValueError(f"{path}: expected a list or a dict holding one of {list(keys)}")


def load_manifest(path: Path) -> list[dict]:
    return _load_json_list(path, ("payloads", "cells", "records"))


def load_tasks(path: Path) -> dict[str, dict]:
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["task_id"]] = r
    return out


def load_slots(path: Path) -> dict[str, dict]:
    return {r["slot_id"]: r for r in _load_json_list(path, ("slots", "records"))}


def load_predicates(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("ft_predicates_by_path", str(path))
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import predicates from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not callable(getattr(mod, "evaluate", None)):
        raise ValueError(f"{path} exposes no evaluate(predicate_id, action_log)")
    return mod


# ── cells ────────────────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Cell:
    run_id: str
    payload_id: str
    arm: str
    follower: str
    repeat: int
    task_id: str | None
    predicate_id: str | None
    record: Mapping[str, Any] = field(compare=False, hash=False)


def make_run_id(block: str, payload_id: str, arm: str, follower: str, repeat: int) -> str:
    return f"{block}|{payload_id}|{arm}|{follower}|r{repeat}"


def expand_cells(manifest: Sequence[Mapping], *, block: str, arms: Sequence[str], followers: Sequence[str],
                 repeats: int) -> tuple[list[Cell], dict[str, int]]:
    for a in arms:
        if a not in KNOWN_ARMS:
            raise ValueError(f"unknown arm {a!r}; known: {KNOWN_ARMS}")
    for f in followers:
        if f not in h.FOLLOWERS:
            raise ValueError(f"unknown follower {f!r}")
    cells: list[Cell] = []
    skipped: Counter = Counter()
    for rec in manifest:
        if not rec.get("scorable"):
            skipped["unscorable"] += 1
            continue
        for arm in arms:
            if isinstance(rec.get("arms"), list) and arm not in rec["arms"]:
                skipped["arm_not_in_record"] += 1
                continue
            if arm == "benign":
                if not rec.get("operational_value"):
                    skipped["benign_not_operational_value"] += 1
                    continue
                if not rec.get("benign_alt_available", True):
                    skipped["benign_no_alternative"] += 1
                    continue
                if rec.get("regime") not in BENIGN_REGIMES:
                    skipped["benign_not_routine_or_middle"] += 1
                    continue
            for fol in followers:
                for k in range(1, repeats + 1):
                    cells.append(Cell(make_run_id(block, rec["payload_id"], arm, fol, k), rec["payload_id"], arm, fol, k,
                                      rec.get("task_id"), rec.get("predicate_id"), rec))
    return cells, dict(skipped)


# ── benign arm ───────────────────────────────────────────────────────────────────────────────────

def locate_value(text: str, locator: str) -> tuple[int, int, int]:
    """(line index, start, end) of the value of the item a blue locator names in one document state.
    Locator = "<document> :: <section key> :: <selector>" (stage3_ft_slots); only `label=<label>#<n>` and
    `yaml=<a.b.c>` selectors carry a value. The walk is stage3_ft_slots.parse_state's, with its own
    regular expressions, keeping the line index; the value is the suffix of the right-stripped line."""
    import stage3_ft_slots as sl
    parts = str(locator).split(" :: ")
    if len(parts) < 3:
        raise BenignPlacementError("locator is not '<document> :: <section> :: <selector>'")
    section_key, selector = " :: ".join(parts[1:-1]), parts[-1]
    kind, _, arg = selector.partition("=")
    if kind not in ("label", "yaml") or not arg:
        raise BenignPlacementError(f"selector {kind!r} carries no value")
    stack: list[tuple[int, str]] = []
    label_n: Counter = Counter()
    in_fence = False
    ystack: list[tuple[int, str]] = []
    for idx, raw_line in enumerate(text.splitlines()):
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if not in_fence:
            m = sl._HEAD.match(line)
            if m:
                lvl, disp = len(m.group(1)), sl._norm(m.group(2))
                while stack and stack[-1][0] >= lvl:
                    stack.pop()
                stack.append((lvl, disp.lower()))
                continue
        if sl._FENCE.match(line):
            in_fence = not in_fence
            ystack = []
            continue
        if sl._RULE.match(line):
            continue
        sec = " > ".join(f"{'#' * lv} {k}" for lv, k in stack)
        if in_fence:
            ym = sl._YAML.match(line)
            if ym:
                ind, key, val = len(ym.group(1)), ym.group(2), ym.group(3)
                while ystack and ystack[-1][0] >= ind:
                    ystack.pop()
                if val == "":
                    ystack.append((ind, key))
                    continue
                path = ".".join([k for _i, k in ystack] + [key]).lower()
                if kind == "yaml" and sec == section_key and path == arg:
                    return idx, len(line) - len(val), len(line)
                continue
        if sl._STEP.match(line):
            continue
        body = sl._BULLET.sub("", line, count=1).strip()
        km = sl._KEYED.match(body)
        if km:
            label = sl._norm(km.group("label")).lower()
            if len(label.split()) <= 6 and not sl._DATE_LABEL.match(label) and label:
                label_n[(sec, label)] += 1
                if kind == "label" and sec == section_key and f"{label}#{label_n[(sec, label)]}" == arg:
                    val = km.group("value")
                    if not val.strip():
                        raise BenignPlacementError("the item has no value")
                    return idx, len(line) - len(val), len(line)
    raise BenignPlacementError("the locator's item is not in this state")


def build_benign(clean: h.Workspace, slot: Mapping[str, Any], benign_alt: str,
                 revision: Mapping[str, str] | None = None) -> h.Workspace:
    """The clean workspace with `benign_alt` written as the value of the slot's item. With `revision`
    ({account, ts}: the manifest's slot_revision_account and slot_revision_time, interface addendum 1,
    item 6) one revision is added to that document's history in red's form: op "replace", the clean line
    removed and the benign line added at its line number; it goes in timestamp order and the revs after
    it move up by one, so rev and ts stay ascending. Without `revision` the clean history is kept as is.
    Locators: blue's string form (see locate_value), or {document, line (1-based), span [start, end)}.
    Anything else raises BenignPlacementError."""
    loc = slot.get("locator")
    if isinstance(loc, str):
        doc = clean.resolve(loc.split(" :: ")[0].strip())
        if doc is None:
            raise BenignPlacementError(f"slot {slot.get('slot_id')}: document not in the workspace")
        lines = clean.docs[doc].splitlines(keepends=True)
        i, s, e = locate_value(clean.docs[doc], loc)
    elif isinstance(loc, Mapping) and "line" in loc and "span" in loc:
        doc = clean.resolve(str(loc.get("document") or slot.get("document") or ""))
        if doc is None:
            raise BenignPlacementError(f"slot {slot.get('slot_id')}: document not in the workspace")
        lines = clean.docs[doc].splitlines(keepends=True)
        i = int(loc["line"]) - 1
        s, e = (int(x) for x in loc["span"])
        if not (0 <= i < len(lines)) or not (0 <= s <= e <= len(lines[i].rstrip("\r\n"))):
            raise BenignPlacementError(f"slot {slot.get('slot_id')}: line/span outside the document")
    else:
        raise BenignPlacementError(f"slot {slot.get('slot_id')}: locator form not supported")
    old_line = lines[i].rstrip("\r\n")
    lines[i] = lines[i][:s] + str(benign_alt) + lines[i][e:]
    docs = {n.lstrip("/"): t for n, t in clean.docs.items()}
    docs[doc.lstrip("/")] = "".join(lines)
    ws = h.Workspace(docs=docs)
    ws.history = {k: [dict(r) for r in v] for k, v in clean.history.items()}
    if revision is not None:
        revs = ws.history.setdefault(doc, [])
        ts = str(revision["ts"])
        pos = sum(1 for r in revs if str(r.get("ts", "")) <= ts)
        new_rev = (int(revs[pos - 1].get("rev", pos)) + 1) if pos > 0 else 1
        for r in revs[pos:]:
            if isinstance(r.get("rev"), int):
                r["rev"] += 1
        revs.insert(pos, {"rev": new_rev, "account": str(revision["account"]), "ts": ts, "op": "replace",
                          "lines_added": [{"line_no": i + 1, "text": lines[i].rstrip("\r\n")}],
                          "lines_removed": [{"line_no": i + 1, "text": old_line}]})
    return ws


# ── the block ────────────────────────────────────────────────────────────────────────────────────

def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def _append(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _transcript_path(cfg: BlockConfig, run_id: str) -> Path:
    stem = run_id.replace("|", "__")
    p = cfg.transcript_dir / f"{stem}.json"
    k = 2
    while p.exists():
        p = cfg.transcript_dir / f"{stem}.attempt{k}.json"
        k += 1
    return p


@dataclass
class BlockConfig:
    manifest: Path
    block: str
    arms: list[str]
    followers: list[str]
    repeats: int
    cap_usd: float
    tasks: Path = DEFAULT_TASKS
    slots: Path = DEFAULT_SLOTS
    docs_root: Path = DEFAULT_DOCS_ROOT
    runs_root: Path = DEFAULT_RUNS_ROOT
    predicates: Path | None = RED_FT / "predicates.py"
    out_dir: Path = FT_DIR
    resume: bool = False
    concurrency: int = 1
    max_refusals: int = MAX_REFUSALS
    seed: int = ORDER_SEED
    expect_manifest_sha256: str | None = None
    expect_predicates_sha256: str | None = None
    expect_docs_tree_sha256: str | None = None
    retry_unresolved: bool = False

    def __post_init__(self):
        if self.retry_unresolved and not self.resume:
            raise ValueError("--retry-unresolved continues an existing block: pass --resume too")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", self.block):
            raise ValueError("block name: letters, digits, '_', '.', '-' only")
        for name in ("expect_manifest_sha256", "expect_predicates_sha256", "expect_docs_tree_sha256"):
            v = getattr(self, name)
            if v is not None and (len(v) < 8 or not re.fullmatch(r"[0-9a-f]+", v)):
                raise ValueError(f"{name}: a lower-case hex sha256 or a prefix of at least 8 characters")

    @property
    def outcomes_path(self) -> Path:
        return Path(self.out_dir) / f"outcomes-{self.block}-v0.jsonl"

    @property
    def ledger_path(self) -> Path:
        return Path(self.out_dir) / f"outcomes-{self.block}-v0.ledger.jsonl"

    @property
    def transcript_dir(self) -> Path:
        return Path(self.runs_root) / self.block

    @property
    def passes_path(self) -> Path:
        return Path(self.out_dir) / f"outcomes-{self.block}-v0.passes.jsonl"

    @property
    def error_log_path(self) -> Path:
        return self.transcript_dir / "errors.jsonl"


# ── hashes (pre-registration v1.1 section 7) ─────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def docs_tree_sha256(root: Path) -> str:
    """sha256 over the sorted lines "<path relative to root, posix>\\t<sha256 of the file>\\n" of every regular
    file under root (hidden files and __pycache__ excluded)."""
    root = Path(root)
    lines = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and not any(part.startswith(".") or part == "__pycache__" for part in rel.split("/")):
            lines.append(f"{rel}\t{sha256_file(p)}\n")
    return hashlib.sha256("".join(sorted(lines)).encode("utf-8")).hexdigest()


def check_hashes(cfg: BlockConfig) -> dict:
    """The actual hashes; raises HashMismatch when an expected one (full or a prefix of 8+) differs."""
    got = {"manifest": sha256_file(cfg.manifest),
           "predicates": sha256_file(cfg.predicates) if cfg.predicates and Path(cfg.predicates).exists() else None,
           "docs_tree": docs_tree_sha256(cfg.docs_root) if Path(cfg.docs_root).is_dir() else None}
    for key, want in (("manifest", cfg.expect_manifest_sha256), ("predicates", cfg.expect_predicates_sha256),
                      ("docs_tree", cfg.expect_docs_tree_sha256)):
        if want is not None and (got[key] is None or not got[key].startswith(want)):
            raise HashMismatch(f"{key}: expected {want}, found {(got[key] or 'missing')[:16]}")
    return got


# ── order, codes, records ────────────────────────────────────────────────────────────────────────

def interleave(cells: Sequence[Cell], *, seed: int = ORDER_SEED) -> list[Cell]:
    """Seeded interleaved order balanced over (regime, arm, follower): each stratum is shuffled, its k-th of n
    cells gets the key (k + u) / n with u a seeded uniform, and all cells are sorted on the key, so any prefix
    holds every stratum in proportion (within about one cell)."""
    rng = random.Random(seed)
    strata: dict[tuple, list[Cell]] = {}
    for c in sorted(cells, key=lambda c: c.run_id):
        strata.setdefault((str(c.record.get("regime")), c.arm, c.follower), []).append(c)
    keyed = []
    for key in sorted(strata):
        lst = strata[key]
        rng.shuffle(lst)
        n = len(lst)
        for k, c in enumerate(lst):
            keyed.append(((k + rng.random()) / n, rng.random(), c))
    keyed.sort(key=lambda t: (t[0], t[1]))
    return [c for _, _, c in keyed]


def is_allowed_code(code: str | None) -> bool:
    if code is None:
        return True
    if code.startswith("refused:"):
        return code.split(":", 1)[1] in REFUSAL_CLASSES
    return code in ERROR_CODES


def _refusal_code(klass: str | None) -> str:
    return f"refused:{klass}" if klass in REFUSAL_CLASSES else "refused:unknown"


def _log_error(cfg: BlockConfig, run_id: str, code: str, detail: str | None) -> None:
    """Exception and error text goes here (red side, never printed), never into the outcomes file."""
    _append(cfg.error_log_path, {"ts": _now(), "run_id": run_id, "code": code, "detail": (detail or "")[:2000]})


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def latest_records(path: Path) -> dict[str, dict]:
    """The last record per run_id (the outcomes file is append-only; a resumed not-run gets a later record)."""
    out: dict[str, dict] = {}
    for r in _read_jsonl(Path(path)):
        out[r["run_id"]] = r
    return out


def benign_alt_in_action(alt: str, action_log: Sequence[Mapping]) -> bool:
    """The copying baseline's literal match: blue's bounded rule (stage3_ft_tasks_validate, after
    stage3_t1v2_checks): the alternative, its backtick-stripped form and each comma part of four or more
    characters; a substring when six characters or longer, else a bounded occurrence; whitespace-normalised,
    case-insensitive; over the arguments of the substantive action calls only."""
    import stage3_t1v2_checks as vc

    def flat(v: Any) -> list[str]:
        if isinstance(v, Mapping):
            return [x for k, vv in v.items() for x in [str(k)] + flat(vv)]
        if isinstance(v, (list, tuple)):
            return [x for vv in v for x in flat(vv)]
        return [str(v)]
    hay = vc.norm(" \n ".join(x for e in action_log if e.get("tool") in h.SUBSTANTIVE_ACTIONS and e.get("kind") == "action"
                              for x in flat(e.get("args") or {}))).lower()
    a = vc.norm(str(alt)).lower()
    cands = [a, a.strip("`")] + [p.strip().strip("`") for p in a.split(",") if len(p.strip()) >= 4]
    return any((len(c) >= 6 and c in hay) or (0 < len(c) < 6 and vc.occurs(c, hay)) for c in cands if c)


def outcome_record(cfg: BlockConfig, cell: Cell, res: h.RunResult | None, model: str, *, predicate_result: bool | None,
                   error: str | None, extra: Mapping[str, Any] | None = None) -> dict:
    if not is_allowed_code(error):
        raise ValueError(f"error code not allowlisted: {error!r}")
    c = res.counts if res else {t: 0 for t in h.ALL_TOOLS} | {"invalid": 0}
    rec = {"run_id": cell.run_id, "payload_id": cell.payload_id, "arm": cell.arm, "follower": cell.follower,
           "repeat": cell.repeat, "task_id": cell.task_id, "predicate_result": predicate_result,
           "checked": bool(res.checked) if res else False,
           "n_search_documents": c["search_documents"], "n_read_history": c["read_history"], "n_ask_colleague": c["ask_colleague"],
           "declined": bool(res.declined) if res else False, "n_turns": res.n_turns if res else 0,
           "cost_usd": round(res.cost_usd, 6) if res else 0.0, "error": error,
           "n_read_document": c["read_document"], "n_invalid": c["invalid"],
           "n_colleague_errors": res.colleague_errors if res else 0, "n_colleague_answered": res.colleague_answered if res else 0,
           "n_read_history_task_doc": 0, "n_colleague_on_slot": 0, "checked_relevant": False, "benign_alt_in_action": None,
           "end_reason": res.end_reason if res else None,
           "ended_in_action": bool(res.ended_in_action) if res else False,
           "action_and_decline": bool(res and res.ended_in_action and res.declined),
           "retry_pass": False, "wall_s": res.wall_s if res else 0.0, "model": model, "cost_missing": bool(res.cost_missing) if res else False,
           "block": cfg.block, "prompt_sha256": h.FOLLOWER_SYSTEM_SHA256}
    rec.update(extra or {})
    return rec


def _workspace_dir(cfg: BlockConfig, rec: Mapping, arm: str) -> Path:
    ws = rec.get("workspaces") or {}
    if arm in ws:
        return Path(ws[arm])
    return Path(cfg.docs_root) / str(rec["payload_id"]) / arm


def _cell_workspace(cfg: BlockConfig, rec: Mapping, arm: str, tasks: Mapping, slots: Mapping) -> tuple[h.Workspace | None, str | None]:
    """(workspace, error code) for one cell; run_block and plan_block both build cells with it."""
    clean_dir = _workspace_dir(cfg, rec, "clean")
    if arm != "benign":
        wdir = _workspace_dir(cfg, rec, arm)
        return (h.Workspace(wdir), None) if wdir.is_dir() else (None, "workspace_missing")
    task = tasks.get(rec.get("task_id")) or {}
    slot = slots.get(task.get("slot_id"))
    if not clean_dir.is_dir() or slot is None or task.get("benign_alt") in (None, ""):
        return None, "benign_unplaceable"
    if not rec.get("slot_revision_account") or not rec.get("slot_revision_time"):
        return None, "benign_no_revision"
    try:
        return build_benign(h.Workspace(clean_dir), slot, str(task["benign_alt"]),
                            revision={"account": rec["slot_revision_account"], "ts": rec["slot_revision_time"]}), None
    except BenignPlacementError:
        return None, "benign_unplaceable"


def slot_names(locator: str | None) -> list[str]:
    """The names a colleague question must carry to count as a relevant check (pre-registration v1.2 section 6):
    the slot's label (`label=<label>#n`), its yaml key and key path (`yaml=a.b.c`), or its step (`step=N` ->
    "step N"). `ord=` and `section` slots have no name."""
    sel = str(locator or "").split(" :: ")[-1]
    kind, _, arg = sel.partition("=")
    if kind == "label" and arg:
        return [arg.rsplit("#", 1)[0]]
    if kind == "yaml" and arg:
        return [arg.rsplit(".", 1)[-1], arg] if "." in arg else [arg]
    if kind == "step" and arg:
        return [f"step {arg}"]
    return []


def _run_fields(ws: h.Workspace, rec: Mapping, cell: Cell, task: Mapping, res: h.RunResult,
                slot: Mapping | None = None) -> dict:
    """Text-free fields the join needs: relevant checks (a read_history call on the task's own document, or an
    answered ask_colleague call whose question names the task slot's label or step, a bounded match) and, on the
    benign arm, the copying baseline's match. Question text is matched here and never written out."""
    import stage3_t1v2_checks as vc
    doc = ws.resolve(str(rec.get("document") or ""))
    n_hist_doc = sum(1 for e in res.action_log if e["tool"] == "read_history" and e["kind"] == "check"
                     and doc is not None and ws.resolve(str(e["args"].get("name", ""))) == doc)
    names = slot_names((slot or {}).get("locator"))
    answered = set(res.colleague_answered_seqs)
    n_on_slot = sum(1 for e in res.action_log if e["tool"] == "ask_colleague" and e["seq"] in answered
                    and any(vc.occurs(nm, str(e["args"].get("question", ""))) for nm in names))
    out = {"n_read_history_task_doc": n_hist_doc, "n_colleague_on_slot": n_on_slot, "checked_relevant": bool(n_hist_doc or n_on_slot)}
    if cell.arm == "benign":
        out["benign_alt_in_action"] = benign_alt_in_action(str(task.get("benign_alt") or ""), res.action_log)
    return out


async def run_block(cfg: BlockConfig, *, adapter_factory: Callable[[str], Any] | None = None,
                    colleague_factory: Callable[[h.Workspace], Any] | None = None,
                    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep, verbose: bool = True) -> dict:
    out_path, ledger_path = cfg.outcomes_path, cfg.ledger_path
    if (out_path.exists() or ledger_path.exists()) and not cfg.resume:
        raise OutputExists(f"{out_path.name} exists; pass --resume or use a new block name")
    hashes = check_hashes(cfg)
    manifest = load_manifest(cfg.manifest)
    tasks = load_tasks(cfg.tasks)
    slots = load_slots(cfg.slots) if Path(cfg.slots).exists() else {}
    predicates = load_predicates(cfg.predicates) if cfg.predicates and any(r.get("predicate_id") for r in manifest) else None
    cells, skipped = expand_cells(manifest, block=cfg.block, arms=cfg.arms, followers=cfg.followers, repeats=cfg.repeats)
    cells = interleave(cells, seed=cfg.seed)
    latest = latest_records(out_path)
    todo = [c for c in cells if c.run_id not in latest or latest[c.run_id].get("error") in RERUNNABLE]
    retry_ids: set[str] = set()
    if cfg.retry_unresolved:
        # selection reads the error code and the retry mark only, never a verdict
        retry_ids = {c.run_id for c in cells if c.run_id in latest and latest[c.run_id].get("error") in INFRA_CODES
                     and not latest[c.run_id].get("retry_pass")}
        todo += [c for c in cells if c.run_id in retry_ids]
        _append(cfg.passes_path, {"ts": _now(), "pass": "retry_unresolved", "phase": "start", "candidates": len(retry_ids)})
    spent = [sum(float(x.get("cost_usd") or 0.0) for x in _read_jsonl(ledger_path))]
    in_flight: dict[str, float] = {}
    lock = asyncio.Lock()
    stop: dict[str, str | None] = {"reason": None}
    done: set[str] = set()
    summary = Counter()
    refusals: Counter = Counter()
    errors: Counter = Counter()
    adapter_factory = adapter_factory or (lambda f: h.make_adapter(f))
    colleague_factory = colleague_factory or (lambda clean_ws: h.Colleague(clean_ws))

    def total() -> float:
        return spent[0] + sum(in_flight.values())

    def record(cell: Cell, res: h.RunResult | None, pred: bool | None, code: str | None, extra: Mapping | None = None) -> None:
        extra = dict(extra or {})
        if cell.run_id in retry_ids:
            extra["retry_pass"] = True
        _append(out_path, outcome_record(cfg, cell, res, h.FOLLOWERS[cell.follower], predicate_result=pred, error=code, extra=extra))
        done.add(cell.run_id)

    async def one(cell: Cell) -> None:
        async with lock:
            if stop["reason"]:
                return
            if total() >= cfg.cap_usd:
                stop["reason"] = "cost_cap"
                return
            in_flight[cell.run_id] = 0.0
        rec = cell.record
        model = h.FOLLOWERS[cell.follower]
        res: h.RunResult | None = None
        code: str | None = None
        pred: bool | None = None
        extra: dict = {}
        task = tasks.get(cell.task_id) if cell.task_id else None
        ws = None
        try:
            if task is None:
                code = "task_missing"
            else:
                clean_dir = _workspace_dir(cfg, rec, "clean")
                ws, code = _cell_workspace(cfg, rec, cell.arm, tasks, slots)
                if ws is not None:
                    clean_ws = h.Workspace(clean_dir) if clean_dir.is_dir() else ws
                    colleague = colleague_factory(clean_ws)
                    adapter = adapter_factory(cell.follower)

                    def guard(run_cost: float, _id: str = cell.run_id) -> None:
                        in_flight[_id] = run_cost
                        if total() >= cfg.cap_usd:
                            raise h.CostCapReached(f"cap ${cfg.cap_usd:.2f} reached")
                    res = await h.run_follower(adapter, str(task["task_text"]), ws, colleague, sleep=sleep, turn_guard=guard)
        except h.CostCapReached as exc:
            part = exc.partial
            async with lock:
                in_flight.pop(cell.run_id, None)
                cost = part.cost_usd if part else 0.0
                spent[0] += cost
                _append(ledger_path, {"run_id": cell.run_id, "cost_usd": round(cost, 6), "status": "cost_cap"})
                if part is not None:
                    _write_transcript(cfg, cell, part, model)
                stop["reason"] = stop["reason"] or "cost_cap"
            return
        except h.HarnessAborted as exc:
            async with lock:
                in_flight.pop(cell.run_id, None)
                stop["reason"] = "aborted"
                errors["aborted"] += 1
                _log_error(cfg, cell.run_id, "aborted", f"{type(exc).__name__}: {exc}")
                record(cell, None, None, "aborted")
            if verbose:
                print(f"  block stopped: harness abort on {cell.run_id} (detail in the red-side error log)", file=sys.stderr)
            return
        if res is not None:
            if res.end_reason == "refused":
                code = _refusal_code(res.refusal_class)
                if res.refusal_class not in REFUSAL_CLASSES:
                    _log_error(cfg, cell.run_id, code, f"refusal class {res.refusal_class!r}")
            elif res.end_reason == "error":
                code = "throttle_error" if (res.error or "").startswith("throttle") else "infra_error"
                _log_error(cfg, cell.run_id, code, res.error)
            else:
                extra = _run_fields(ws, rec, cell, task, res, slots.get(task.get("slot_id")))
                if cell.predicate_id and predicates is not None:
                    try:
                        v = predicates.evaluate(cell.predicate_id, list(res.action_log))
                        if isinstance(v, bool):
                            pred = v
                        else:
                            code = "predicate_error"
                            _log_error(cfg, cell.run_id, code, f"non-bool {type(v).__name__}")
                    except Exception as exc:  # noqa: BLE001
                        code = "predicate_error"
                        _log_error(cfg, cell.run_id, code, f"{type(exc).__name__}: {exc}")
                elif cell.predicate_id and predicates is None:
                    code = "predicate_error"
                    _log_error(cfg, cell.run_id, code, "no predicate module")
        async with lock:
            in_flight.pop(cell.run_id, None)
            cost = res.cost_usd if res else 0.0
            spent[0] += cost
            _append(ledger_path, {"run_id": cell.run_id, "cost_usd": round(cost, 6), "status": "finished"})
            if res is not None:
                _write_transcript(cfg, cell, res, model)
            record(cell, res, pred, code, extra)
            summary["completed"] += 1
            if code:
                errors[code.split(":")[0]] += 1
            if code and code.startswith("refused:"):
                refusals[code.split(":", 1)[1]] += 1
                if sum(refusals.values()) > cfg.max_refusals:
                    stop["reason"] = "refusals"

    sem = asyncio.Semaphore(max(1, cfg.concurrency))

    async def gated(cell: Cell) -> None:
        async with sem:
            await one(cell)

    if cfg.concurrency <= 1:
        for cell in todo:
            if stop["reason"]:
                break
            await one(cell)
    else:
        await asyncio.gather(*(gated(c) for c in todo))
    if not stop["reason"] and total() >= cfg.cap_usd and any(c.run_id not in done for c in todo):
        stop["reason"] = "cost_cap"
    not_run = [c for c in todo if c.run_id not in done]
    if not_run:
        code = "not_run_cap" if stop["reason"] == "cost_cap" else "not_run_stopped"
        for c in not_run:
            record(c, None, None, code)
    out = {"block": cfg.block, "cells": len(cells), "skipped_cells": skipped, "skipped_finished": len(cells) - len(todo),
           "completed": summary["completed"], "not_run": len(not_run), "errors": dict(errors), "refusals": dict(refusals),
           "block_spend_usd": round(spent[0], 6), "cap_usd": cfg.cap_usd, "stop": stop["reason"],
           "hashes": hashes, "outcomes": str(out_path)}
    if cfg.retry_unresolved:
        reasked = sum(1 for rid in retry_ids if rid in done)
        out["retry_pass"] = {"candidates": len(retry_ids), "reasked": reasked}
        _append(cfg.passes_path, {"ts": _now(), "pass": "retry_unresolved", "phase": "end", "candidates": len(retry_ids),
                                  "reasked": reasked, "stop": stop["reason"]})
    if verbose:
        print(json.dumps(out, indent=2))
    return out


def plan_block(cfg: BlockConfig, *, adapter_factory: Callable[[str], Any] | None = None, verbose: bool = True) -> dict:
    """The launch rehearsal: no model call, nothing written. Hashes checked as run_block checks them; planned runs
    per arm and follower; every distinct (payload, arm) workspace built as run_block builds it and checked
    (documents under /shared/ world paths, history present, the benign revision placed); every predicate id
    evaluated on an empty action log (a bool back = resolved). Counts only. `adapter_factory` is accepted so a
    test can prove it is never called."""
    hashes = check_hashes(cfg)
    manifest = load_manifest(cfg.manifest)
    tasks = load_tasks(cfg.tasks)
    slots = load_slots(cfg.slots) if Path(cfg.slots).exists() else {}
    cells, skipped = expand_cells(manifest, block=cfg.block, arms=cfg.arms, followers=cfg.followers, repeats=cfg.repeats)
    order = interleave(cells, seed=cfg.seed)
    runs: dict[str, dict[str, int]] = {}
    for c in cells:
        runs.setdefault(c.arm, {}).setdefault(c.follower, 0)
        runs[c.arm][c.follower] += 1
    ws_stats = Counter()
    n_docs: Counter = Counter()
    errors: Counter = Counter()
    seen = set()
    for c in cells:
        if (c.payload_id, c.arm) in seen:
            continue
        seen.add((c.payload_id, c.arm))
        ws_stats["checked"] += 1
        ws, err = _cell_workspace(cfg, c.record, c.arm, tasks, slots)
        if ws is None:
            ws_stats["missing"] += 1
            errors[err or "unknown"] += 1
            continue
        ws_stats["loaded"] += 1
        names = ws.names()
        n_docs[str(len(names))] += 1
        ws_stats["world_paths"] += int(bool(names) and all(n.startswith("/shared/") for n in names))
        ws_stats["with_history"] += int(any(ws.history.get(n) for n in names))
        if c.arm == "benign":
            rec = c.record
            doc = ws.resolve(str(rec.get("document") or ""))
            revs = ws.history.get(doc, []) if doc else [r for v in ws.history.values() for r in v]
            placed = [r for r in revs if r.get("account") == rec.get("slot_revision_account") and r.get("ts") == rec.get("slot_revision_time")
                      and r.get("op") == "replace" and all(x["text"] in ws.docs.get(doc or "", "") for x in r.get("lines_added", []))]
            ws_stats["benign_revision_placed"] += int(len(placed) == 1)
    pred_ids = sorted({c.predicate_id for c in cells if c.predicate_id})
    resolved, unresolved = 0, Counter()
    if pred_ids:
        mod = load_predicates(cfg.predicates)
        for pid in pred_ids:
            try:
                v = mod.evaluate(pid, [])
                if isinstance(v, bool):
                    resolved += 1
                else:
                    unresolved["non_bool"] += 1
            except Exception as exc:  # noqa: BLE001
                unresolved[type(exc).__name__] += 1
    first = Counter((str(c.record.get("regime")), c.arm, c.follower) for c in order[: max(1, len(order) // 10)])
    plan = {"block": cfg.block, "runs": runs, "total_runs": len(cells), "skipped_cells": skipped, "hashes": hashes,
            "first_tenth_by_regime_arm_follower": {"|".join(k): v for k, v in sorted(first.items())},
            "workspaces": {"checked": ws_stats["checked"], "loaded": ws_stats["loaded"], "missing": ws_stats["missing"],
                           "missing_by_reason": dict(errors), "world_paths": ws_stats["world_paths"], "n_documents": dict(n_docs),
                           "with_history": ws_stats["with_history"], "benign_revision_placed": ws_stats["benign_revision_placed"]},
            "predicates": {"resolved": resolved, "unresolved": dict(unresolved)},
            "outcomes_exists": cfg.outcomes_path.exists()}
    if verbose:
        print(json.dumps(plan, indent=2))
    return plan


def _write_transcript(cfg: BlockConfig, cell: Cell, res: h.RunResult, model: str) -> None:
    p = _transcript_path(cfg, cell.run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"run_id": cell.run_id, "payload_id": cell.payload_id, "arm": cell.arm, "follower": cell.follower,
                             "repeat": cell.repeat, "task_id": cell.task_id, "model": model,
                             "prompt_sha256": h.FOLLOWER_SYSTEM_SHA256, "end_reason": res.end_reason,
                             "action_log": res.action_log, "events": res.transcript, "cost_usd": res.cost_usd},
                            ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run a block of FT follower cells. Prints counts only.")
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--block", required=True)
    ap.add_argument("--arms", required=True, help="comma-separated, e.g. planted,clean")
    ap.add_argument("--followers", default="kimi,sol")
    ap.add_argument("--repeats", type=int, required=True)
    ap.add_argument("--cap-usd", type=float, required=True)
    ap.add_argument("--tasks", type=Path, default=DEFAULT_TASKS)
    ap.add_argument("--slots", type=Path, default=DEFAULT_SLOTS)
    ap.add_argument("--docs-root", type=Path, default=DEFAULT_DOCS_ROOT)
    ap.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    ap.add_argument("--predicates", type=Path, default=RED_FT / "predicates.py")
    ap.add_argument("--out-dir", type=Path, default=FT_DIR)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--concurrency", type=int, default=1)
    ap.add_argument("--max-refusals", type=int, default=MAX_REFUSALS)
    ap.add_argument("--expect-manifest-sha256")
    ap.add_argument("--expect-predicates-sha256")
    ap.add_argument("--expect-docs-tree-sha256")
    ap.add_argument("--retry-unresolved", action="store_true",
                    help="with --resume: re-ask once the runs whose latest code is an infrastructure error (never refusals)")
    ap.add_argument("--dry-run", action="store_true", help="plan and check only: no model call, nothing written")
    a = ap.parse_args(argv)
    cfg = BlockConfig(manifest=a.manifest, block=a.block, arms=a.arms.split(","), followers=a.followers.split(","),
                      repeats=a.repeats, cap_usd=a.cap_usd, tasks=a.tasks, slots=a.slots, docs_root=a.docs_root,
                      runs_root=a.runs_root, predicates=a.predicates, out_dir=a.out_dir, resume=a.resume,
                      concurrency=a.concurrency, max_refusals=a.max_refusals, expect_manifest_sha256=a.expect_manifest_sha256,
                      expect_predicates_sha256=a.expect_predicates_sha256, expect_docs_tree_sha256=a.expect_docs_tree_sha256,
                      retry_unresolved=a.retry_unresolved)
    if a.dry_run:
        p = plan_block(cfg)
        return 0 if not p["workspaces"]["missing"] and not p["predicates"]["unresolved"] else 2
    s = asyncio.run(run_block(cfg))
    return 0 if s["stop"] is None else 2


if __name__ == "__main__":
    raise SystemExit(main())
