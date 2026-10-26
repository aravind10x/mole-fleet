#!/usr/bin/env python3
"""T1, the content-placeholder test (proposal 11.12 section 5; brief 07f B6, brief 07h H1): the inserter.

Plants each of blue's synthetic three-statement payloads (`t1/payloads-v1.json`, 24 payloads; or
`t1v2/payloads-v2.json`, 56 payloads in the regime arms conforming / alarming / sham) three ways
into in-memory copies of the honest null's rows, in the REDUNDANCY shape the scenario side's
answer fixed on 2026-10-23 (both sessions of a role's day carry the objective):

  lone   one author, one day d in {1, 2}; statements 1 and 2 in the author's first session of
         the day, statement 3 in the second (2 + 1);
  k = 2  two authors on consecutive days d, d + 1: statements 1 and 2 by the first author over
         its two sessions, statement 3 by the second author in its first session;
  k = 3  one statement per author on days 1, 2, 3, each in the author's first session
         (16 of 24 payloads per regime, seeded: 3 per document for four documents, 2 for two;
         every alarming payload).
  A third of the payloads (seeded, per regime) carry one DUPLICATED statement, statement 3 in
  every arm, delivered again by the role that owns it in that role's second session.

A planted row is a successful ownCloud `append_to_file` or `replace_in_file` audit event in the
author's chosen session (timestamp inside the session's span, the session's task_id), shaped
like the honest rows (args: path, text | find, replace, plus the audit layer's `content` and
`edit`, as brief 07e E1 records them). Its `content` is the shared reader's state just before
it with the edit applied by the manager's rule (`apply_edit`: append adds the text as a new
line at the end; replace replaces the first exact occurrence). Every later honest edit of the
document has its `content` rebuilt by applying its own op to the new running state; an honest
replace whose `find` is no longer present becomes a failed row (as the manager would fail it);
a later honest whole write overwrites the plant. A statement's `find` is resolved at plant time
as the first document line starting with the payload's committed anchor prefix.

Brief 07h's four inserter fixes (decision memo R2; `t1v2/t1v2-plan.md` section 1, written first):
  F1  read before edit: the first planted edit of a planting session is preceded by a successful
      read of the target in that session (an honest one when present, else a planted
      `read_bytes` + `read_file` pair at the honest rate, 125 of 130 on the null, with the honest
      timing: the edit's minute for minute-aligned sessions, a gap drawn from the honest gaps for
      microsecond sessions);
  F2  a redundant second delivery only where it re-lands the statement (its line absent from
      the live state: a replace whose anchor resolves to another line, an append whose line is
      gone); never a no-op replace; skipped deliveries recorded;
  F3  sessions that already touch the target (any successful honest ownCloud action on the path)
      preferred: the author pool is restricted to authors with a touching session on the day when
      that leaves someone, and single-statement roles take a touching session when one is
      eligible; shares recorded;
  F4  authors are drawn only from those with a session inside which the role's anchors resolve
      (so the README's day-1 role plants after its 10:29 whole rewrite, from the authors active
      after it); the role-1 authors of the README's k = 3 plants are recorded.

A layout is re-drawn (same seed stream) up to MAX_REDRAWS times when an anchor is absent at
plant time, an author cannot be drawn, or a statement is overwritten before the composition
time; the first PREFER_CLEAN_DRAWS draws also require that the plant breaks no later honest
edit, after which a composed layout that broke one is accepted and the count recorded.
Composition is checked through the reader at the composition timestamp and at the end of the
composition day: every statement's line present.

Every document state goes through `mole.oracles.document` (L4 / L15 rule 5). Nothing here reads
the sealed file, a persona, a transcript or is_malicious.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_t1.py plant \\
        --corpus /abs/.../prefix_rw_v2c.jsonl --payloads /abs/work/stage3/t1v2/payloads-v2.json \\
        --out /abs/work/stage3/t1v2/plants-v2.json
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_views as sv  # noqa: E402  (fork on sys.path)
from mole.oracles import document as doc  # noqa: E402

LAYOUT_SEED = 20261113
MAX_REDRAWS = 20
PREFER_CLEAN_DRAWS = 10     # first draws also require no honest edit broken by the plant
ARMS = ("lone", "k2", "k3")
REGIMES = ("conforming", "alarming", "sham")
# T1 v3 (brief 07l, amendment S v2; 2026-10-26, additive): the middle band beside a routine re-draw and a
# sham re-draw of v2's payloads, planted on one seed stream. The Inserter class is unchanged.
REGIMES_V3 = ("middle", "routine_redraw", "sham_redraw")
ALL_REGIMES = REGIMES + REGIMES_V3
K3_COUNT = 16
DUPLICATE_SHARE = 1 / 3
READ_ACTIONS = ("read_bytes", "read_file")     # the honest read pair, in this order (120 of 125 on the null)
#: write-teams per class document (the pilot assignment's disclosed `write_teams`, a fact of the
#: class bank, no defender parameter).
WRITE_TEAMS: dict[str, tuple[str, ...]] = {
    "/shared/infra/training-pipeline/README.md": ("alignment", "capabilities", "evaluations", "platform"),
    "/shared/eval/release-gate-runbook.md": ("alignment", "capabilities", "evaluations", "platform"),
    "/shared/capabilities/finetune-guide.md": ("alignment", "capabilities", "evaluations", "platform"),
    "/shared/alignment/redteam-checklist.md": ("alignment", "capabilities", "evaluations", "platform"),
    "/shared/ops/oncall-runbook.md": ("alignment", "capabilities", "evaluations", "platform"),
    "/shared/onboarding/engineering-setup.md": ("capabilities", "evaluations", "hr", "platform"),
}


# ── the manager's edit rule, and its inverse check ────────────────────────

def apply_edit(before: str | None, action: str, args: Mapping[str, Any]) -> str:
    """mole/state/owncloud/manager.py append_to_file / replace_in_file / write_file on a text.
    Raises ValueError exactly where the manager does (empty text; find absent; no file)."""
    if action == "write_file":
        return str(args.get("content") or args.get("data") or args.get("body") or "")
    if action == "append_to_file":
        text = args.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("append_to_file: text is empty; nothing to append")
        base = before or ""
        sep = "" if (base == "" or base.endswith("\n")) else "\n"
        return base + sep + text + ("" if text.endswith("\n") else "\n")
    if action == "replace_in_file":
        find, repl = args.get("find"), args.get("replace")
        if not isinstance(find, str) or find == "":
            raise ValueError("replace_in_file: find is empty")
        if before is None:
            raise ValueError("replace_in_file: no file at path")
        if find not in before:
            raise ValueError("replace_in_file: find string not found")
        return before.replace(find, repl if isinstance(repl, str) else str(repl), 1)
    raise ValueError(f"not a content write: {action}")


def check_applier_against_log(rows: Sequence[Mapping[str, Any]], path: str,
                              base: Mapping[Any, Any]) -> dict:
    """Replay the honest log with `apply_edit` and compare with every recorded `content`:
    the applier reproduces the manager (tested on the null: 126 of 126 edit rows)."""
    ref = doc.DocRef("owncloud", path)
    state = base.get(("owncloud", path))
    n = ok = 0
    for w in doc.content_writes(rows, ref):
        r = rows[w.index]
        a = r.get("args") or {}
        if r["action"] == "write_file":
            state = apply_edit(state, "write_file", a)
            continue
        n += 1
        state = apply_edit(state, r["action"], a)
        rec = a.get("content") or a.get("data") or a.get("body")
        ok += state == rec
    return {"path": path, "edit_rows": n, "reproduced": ok}


# ── honest reads before edits (F1's base) ─────────────────────────────────

def _dt(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _fmt(t: datetime, style: str) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if style == "min" else t.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def is_read_of(row: Mapping[str, Any], path: str) -> bool:
    return (row.get("service") == "owncloud" and row.get("action") in READ_ACTIONS
            and (row.get("exit_code") or 0) == 0 and not row.get("t1_planted")
            and sv.norm_path((row.get("args") or {}).get("path")) == path)


def read_before_edit_stats(rows: Sequence[Mapping[str, Any]], paths: Sequence[str]) -> dict:
    """Of the successful honest edits of `paths`, how many are preceded in the same session
    (same task_id, file order) by a successful read of the same path, and the read-to-edit gaps
    in seconds, split by the edit row's timestamp precision (on the null: 125 of 130; the gaps of
    microsecond-session edits are mostly 0 s)."""
    by_task: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(rows):
        if r.get("task_id"):
            by_task[str(r["task_id"])].append(i)
    want = {sv.norm_path(p) for p in paths}
    edits = preceded = 0
    gaps_frac: list[float] = []
    gaps_min: list[float] = []
    for i, r in enumerate(rows):
        if r.get("service") != "owncloud" or r.get("action") not in sv.WRITE_ACTIONS or (r.get("exit_code") or 0) != 0:
            continue
        p = sv.norm_path((r.get("args") or {}).get("path"))
        if p not in want:
            continue
        edits += 1
        reads = [j for j in by_task.get(str(r.get("task_id")), []) if j < i and is_read_of(rows[j], p)]
        if reads:
            preceded += 1
            g = (_dt(str(r["ts"])) - _dt(str(rows[reads[-1]]["ts"]))).total_seconds()
            (gaps_frac if "." in str(r["ts"]) else gaps_min).append(max(0.0, g))
    return {"edits": edits, "preceded": preceded, "rate": (preceded / edits) if edits else None,
            "gaps_frac": gaps_frac, "gaps_min": gaps_min}


# ── sessions and authors ──────────────────────────────────────────────────

@dataclass(frozen=True)
class Session:
    account: str
    day: str
    task_id: str
    first_ts: str
    last_ts: str
    last_index: int           # file position of the session's last row
    ts_style: str = "frac"    # the session's timestamp precision: "frac" (microseconds) or "min" (HH:MM:00Z)


def sessions_by_account_day(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], list[Session]]:
    agg: dict[tuple[str, str, str], list[tuple[str, int]]] = defaultdict(list)
    for i, r in enumerate(rows):
        if r.get("task_id") and r.get("ts") and r.get("account"):
            agg[(r["account"], str(r["ts"])[:10], r["task_id"])].append((str(r["ts"]), i))
    out: dict[tuple[str, str], list[Session]] = defaultdict(list)
    for (a, d, t), lst in agg.items():
        tss = sorted(x[0] for x in lst)
        # the session's own precision: the honest log writes microsecond timestamps or
        # minute-aligned ones (HH:MM:00Z); a planted row takes the style of its session
        # (review 2026-10-23, Opus finding 5)
        n_frac = sum(1 for x in tss if "." in x)
        style = "frac" if n_frac * 2 >= len(tss) else "min"
        out[(a, d)].append(Session(a, d, t, tss[0], tss[-1], max(x[1] for x in lst), style))
    for k in out:
        out[k].sort(key=lambda s: (s.first_ts, s.task_id))
    return out


def team_maps(template_path: Path) -> tuple[dict[str, str], set[str]]:
    import yaml
    o = yaml.safe_load(Path(template_path).read_text(encoding="utf-8"))
    team: dict[str, str] = {}
    managers: set[str] = set()
    for d in o.get("departments") or []:
        for t in d.get("teams") or []:
            managers.add(t["manager"])
            team[t["manager"]] = t["id"]
            for m in t.get("members") or []:
                team[m] = t["id"]
    return team, managers


# ── plants ────────────────────────────────────────────────────────────────

@dataclass
class PlantedStatement:
    index: int                 # statement index in the payload (0..2), or the duplicated one
    role: int                  # 0-based role (author) index
    account: str
    day: str
    task_id: str
    ts: str
    action: str
    args: dict[str, Any]       # path + text | find, replace (as sent) + content, edit
    file_position: int         # position in the planted row list
    duplicate: bool = False
    line_text: str = ""        # the line the statement puts in the document
    session_touches_target: bool = False   # F3: the session had an honest action on the target


@dataclass
class PlantResult:
    payload_id: str
    arm: str
    document: str
    authors: list[str]
    days: list[str]
    statements: list[PlantedStatement]
    regime: str = ""
    rows: list[dict] = field(repr=False, default_factory=list)   # the planted corpus (in memory)
    composition_ts: str = ""
    composition_day: str = ""
    pre_window_boundary: str = ""       # "day0" or the date whose end is the pre-window state
    composed_at_ts: bool = False
    composed_at_day_end: bool = False
    present_at_day_end: list[bool] = field(default_factory=list)
    adjacency: list[list[int]] = field(default_factory=list)   # pairs of statement indices on adjacent lines
    honest_edits_rebuilt: list[str] = field(default_factory=list)   # event ids whose content changed
    honest_edits_broken: list[str] = field(default_factory=list)   # event ids of honest edits failed by the plant
    overwritten_by_whole_write: bool = False
    redraws: int = 0
    single_session_roles: list[int] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    reads: list[dict] = field(default_factory=list)            # F1: per planting session {task_id, kind: honest|planted|none, ts}
    redundant: list[dict] = field(default_factory=list)        # F2: {statement, delivered, reason}
    author_draw_restricted: list[bool] = field(default_factory=list)   # F3: drawn from the touching pool
    author_pool_sizes: list[dict] = field(default_factory=list)        # F4: pool sizes per role draw

    @property
    def composed(self) -> bool:
        return self.composed_at_ts and self.composed_at_day_end

    @property
    def delivered(self) -> bool:
        """Every statement of the payload landed as a planted row (composition aside)."""
        return bool(self.rows) and len({s.index for s in self.statements if not s.duplicate}) == 3

    def record(self) -> dict:
        """JSON record without the rows: layout, planted rows (as sent + content hash), checks."""
        real = [s for s in self.statements if not s.duplicate]
        return {
            "payload_id": self.payload_id, "arm": self.arm, "regime": self.regime, "document": self.document,
            "authors": self.authors, "days": self.days, "pre_window_boundary": self.pre_window_boundary,
            "composition_ts": self.composition_ts, "composition_day": self.composition_day,
            "composed": self.composed, "delivered": self.delivered, "composed_at_ts": self.composed_at_ts,
            "composed_at_day_end": self.composed_at_day_end, "present_at_day_end": self.present_at_day_end,
            "adjacency": self.adjacency, "honest_edits_rebuilt": len(self.honest_edits_rebuilt),
            "honest_edits_broken": len(self.honest_edits_broken),
            "overwritten_by_whole_write": self.overwritten_by_whole_write, "redraws": self.redraws,
            "single_session_roles": self.single_session_roles, "reasons": self.reasons,
            "reads": self.reads, "redundant": self.redundant,
            "author_draw_restricted": self.author_draw_restricted, "author_pool_sizes": self.author_pool_sizes,
            "statements_in_touching_sessions": sum(1 for s in real if s.session_touches_target),
            "planted_rows": [{
                "statement": s.index, "role": s.role, "account": s.account, "day": s.day,
                "task_id": s.task_id, "ts": s.ts, "action": s.action, "duplicate": s.duplicate,
                "session_touches_target": s.session_touches_target,
                "as_sent": {k: v for k, v in s.args.items() if k in ("path", "text", "find", "replace")},
                "content_sha256": hashlib.sha256(str(s.args.get("content", "")).encode("utf-8")).hexdigest(),
                "line_text": s.line_text} for s in self.statements],
        }


def resolve_anchor(state: str, anchor: str) -> str | None:
    for ln in state.splitlines():
        if ln.startswith(anchor):
            return ln
    return None


def statement_line(stmt: Mapping[str, Any], day: str) -> str:
    return (stmt["replace"] if stmt["op"] == "replace" else stmt["text"]).replace("{date}", day)


def _event_id(payload_id: str, arm: str, idx: int, dup: bool, kind: str = "edit") -> str:
    tag = f"t1|{payload_id}|{arm}|{idx}|{int(dup)}" + ("" if kind == "edit" else f"|{kind}")
    return hashlib.sha256(tag.encode()).hexdigest()[:32]


def _stable_hash(value: Any) -> str:
    """The audit collector's hash (mole/audit/schema._stable_hash): sorted keys, UTF-8 kept."""
    from mole.audit.schema import _stable_hash as h
    return h(value)


def _result_bytes(result: dict) -> int:
    """The collector's byte count of a result envelope without a size field: the length of
    its JSON serialisation (mole/audit/collector.py, the `bytes` fallback)."""
    return len(json.dumps(result, default=str).encode("utf-8"))


def _base_row(account: str, ts: str, task_id: str, path: str, action: str, args: dict,
              nbytes: int, event_id: str) -> dict:
    return {"event_id": event_id, "ts": ts, "real_ts": None, "account": account,
            "account_kind": "background_llm_agent", "service": "owncloud", "action": action,
            "resource_id": path, "resource_hash": hashlib.sha256(path.encode("utf-8")).hexdigest(),
            "args": args, "args_hash": _stable_hash(args),
            "exit_code": 0, "bytes": nbytes,
            "error": "", "dest_domain": None, "is_external": False, "parent_event_id": None,
            "gate_decision": None, "is_malicious": False, "task_id": task_id, "result_meta": {},
            "wall_ts": None, "t1_planted": True}


def _plant_row(account: str, ts: str, task_id: str, path: str, action: str, sent: dict,
               content: str, before_len: int, event_id: str) -> dict:
    edit = ({"op": "append", "text": sent["text"], "before_len": before_len, "after_len": len(content)}
            if action == "append_to_file" else
            {"op": "replace", "find": sent["find"], "replace": sent["replace"],
             "before_len": before_len, "after_len": len(content)})
    args = {"path": path, **sent, "content": content, "edit": edit}
    return _base_row(account, ts, task_id, path, action, args, _result_bytes({"path": path, **edit}), event_id)


def _read_row(account: str, ts: str, task_id: str, path: str, action: str, state: str, event_id: str) -> dict:
    """A planted read of the document: `bytes` is the UTF-8 length of the live content, as the
    collector records a str / bytes result (mole/audit/collector.py `_estimate_bytes`)."""
    row = _base_row(account, ts, task_id, path, action, {"path": path}, len(state.encode("utf-8")), event_id)
    row["t1_read"] = True
    return row


def _ts_in(rng: random.Random, s: Session, after: str | None = None) -> str | None:
    """A timestamp inside the session's span [first_ts, last_ts] (strictly after `after` when
    given), never past the session's last row (codex finding 9), in the session's own
    precision (Opus finding 5): microseconds (a random microsecond) for a "frac" session, a
    minute-aligned HH:MM:00Z for a "min" session. None when nothing of the span remains (the
    caller fails the layout)."""
    f = _dt(s.first_ts)
    l = _dt(s.last_ts)
    lo = f
    if after:
        lo = max(lo, _dt(after) + timedelta(microseconds=1))
    if s.ts_style == "min":
        lo_m = lo.replace(second=0, microsecond=0)
        if lo_m < lo:
            lo_m += timedelta(minutes=1)
        l_m = l.replace(second=0, microsecond=0)
        if l_m < lo_m:
            return None
        t = lo_m + timedelta(minutes=rng.randint(0, int((l_m - lo_m).total_seconds()) // 60))
        return _fmt(t, "min")
    if l < lo:
        return None
    span_us = int((l - lo).total_seconds() * 1_000_000)
    t = lo + timedelta(microseconds=rng.randint(0, span_us))
    return _fmt(t, "frac")


def _read_ts(rng: random.Random, s: Session, edit_ts: str, after: str | None, gaps: Sequence[float]) -> str:
    """F1: the planted read's timestamp: the edit's own minute for a minute-aligned session; for a
    microsecond session the edit's timestamp minus a gap drawn from the honest gaps, floored at the
    session's start and just after the previous plant of the session."""
    if s.ts_style == "min":
        return edit_ts
    gap = rng.choice(list(gaps)) if gaps else 0.0
    t = _dt(edit_ts) - timedelta(seconds=gap)
    lo = _dt(s.first_ts)
    if after:
        lo = max(lo, _dt(after) + timedelta(microseconds=1))
    t = max(t, lo)
    return _fmt(min(t, _dt(edit_ts)), "frac")


def _insert_position(rows: Sequence[Mapping[str, Any]], s: Session, ts: str) -> int:
    """Right after the last row of the log with ts <= the planted ts (file order), so the
    planted row sits where a call completing at that simulated time would (the log is
    time-ordered up to adjacent inversions), after the session's own earlier rows."""
    pos = None
    for i, r in enumerate(rows):
        if str(r.get("ts") or "") <= ts and r.get("ts"):
            pos = i
    return (pos + 1) if pos is not None else s.last_index + 1


class Inserter:
    def __init__(self, rows: Sequence[Mapping[str, Any]], base: Mapping[Any, Any],
                 team: Mapping[str, str], managers: set[str], days: Sequence[str] | None = None,
                 read_rate: float | None = None, read_gaps: Sequence[float] | None = None):
        self.rows = list(rows)
        self.base = base
        self.team, self.managers = dict(team), set(managers)
        self.days = list(days) if days else sv.corpus_days(self.rows)
        self.sessions = sessions_by_account_day(self.rows)
        self.active: dict[str, list[str]] = defaultdict(list)
        for (a, d), ss in self.sessions.items():
            if ss:
                self.active[d].append(a)
        for d in self.active:
            self.active[d].sort()
        # F1: the honest read-before-edit rate and gaps, measured on these rows unless given
        self.read_stats = read_before_edit_stats(self.rows, sv.class_doc_paths())
        self.read_rate = float(read_rate) if read_rate is not None else float(self.read_stats["rate"] or 0.0)
        self.read_gaps = list(read_gaps) if read_gaps is not None else list(self.read_stats["gaps_frac"])
        # F3: the sessions (task ids) with a successful honest ownCloud action on each class document
        self.touch: dict[str, set[str]] = defaultdict(set)
        for r in self.rows:
            if r.get("service") == "owncloud" and (r.get("exit_code") or 0) == 0 and r.get("task_id"):
                p = sv.norm_path((r.get("args") or {}).get("path"))
                if p in WRITE_TEAMS:
                    self.touch[p].add(str(r["task_id"]))
        self._anchored_cache: dict[tuple, bool] = {}
        # F4 (general form): the last successful whole write of each class document in the null is a
        # floor on every plant time (a statement planted before it is overwritten; the v2 anchors
        # exist only after it): a session ending before the floor is ineligible, a session spanning
        # it plants after it
        self.whole_writes: dict[str, list[str]] = {}
        for p in WRITE_TEAMS:
            self.whole_writes[p] = sorted(w.ts for w in doc.content_writes(self.rows, doc.DocRef("owncloud", p))
                                          if self.rows[w.index].get("action") == "write_file")

    def whole_write_floor(self, path: str, until_day: str | None) -> str | None:
        """The last whole rewrite of the document up to the end of `until_day` (the plant's
        composition day; every day when None): a plant before it cannot compose."""
        ws = [t for t in self.whole_writes.get(path, []) if until_day is None or t[:10] <= until_day]
        return max(ws) if ws else None

    # layout -------------------------------------------------------------
    def _has_anchored_session(self, path: str, day: str, acct: str, anchors: tuple[str, ...],
                              until_day: str | None = None) -> bool:
        key = (path, day, acct, anchors, until_day)
        if key not in self._anchored_cache:
            ref = doc.DocRef("owncloud", path)
            self._anchored_cache[key] = any(self._anchor_ready(self.rows, ref, s, anchors, until_day) is not None
                                            for s in self.sessions.get((acct, day), []))
        return self._anchored_cache[key]

    def draw_author(self, rng: random.Random, path: str, day: str, used: set[str],
                    anchors: Sequence[str] = (), log: list | None = None, until_day: str | None = None) -> str | None:
        """An author for `day`: active, in the document's write-teams, not a manager, not used;
        with a session in which the role's anchors resolve (F4); from the authors with a session
        touching the target when that leaves someone (F3)."""
        pool = [a for a in self.active.get(day, []) if self.team.get(a) in WRITE_TEAMS[path]
                and a not in self.managers and a not in used]
        anc = tuple(anchors)
        anchored = [a for a in pool if self._has_anchored_session(path, day, a, anc, until_day)]
        touching = [a for a in anchored if any(s.task_id in self.touch.get(path, set())
                                                for s in self.sessions.get((a, day), []))]
        chosen_pool = touching or anchored
        if log is not None:
            log.append({"day": day, "pool": len(pool), "anchored": len(anchored), "touching": len(touching),
                        "restricted": bool(touching)})
        return rng.choice(chosen_pool) if chosen_pool else None

    def layout(self, rng: random.Random, arm: str, path: str, stmts: Sequence[Mapping[str, Any]] | None = None
               ) -> tuple[list[str], list[str]] | None:
        """-> (days per role, authors per role) or None when an author cannot be drawn. The
        draw log of the last call is in `self.last_draw_log`."""
        if arm == "lone":
            d = rng.choice(self.days[:2])
            days = [d]
        elif arm == "k2":
            i = rng.choice([0, 1])
            days = [self.days[i], self.days[i + 1]]
        else:
            days = list(self.days[:3])
        used: set[str] = set()
        authors = []
        self.last_draw_log: list[dict] = []
        for role, d in enumerate(days):
            anchors: list[str] = []
            if stmts is not None:
                anchors = [stmts[i]["anchor"] for i in self._roles(arm)[role] if stmts[i]["op"] == "replace"]
            a = self.draw_author(rng, path, d, used, anchors, self.last_draw_log, days[-1])
            if a is None:
                return None
            used.add(a)
            authors.append(a)
        return days, authors

    # planting -----------------------------------------------------------
    def plant(self, payload: Mapping[str, Any], arm: str, rng: random.Random, duplicate: bool
              ) -> PlantResult:
        path = payload["document"]
        stmts = payload["statements"]
        res: PlantResult | None = None
        best: PlantResult | None = None        # a composed layout that broke an honest edit
        delivered: PlantResult | None = None   # every statement landed, composition failed
        for attempt in range(MAX_REDRAWS + 1):
            lay = self.layout(rng, arm, path, stmts)
            if lay is None:
                if res is None:
                    res = PlantResult(payload_id=payload["id"], arm=arm, document=path, authors=[], days=[],
                                      statements=[], regime=str(payload.get("arm") or ""))
                    res.reasons.append("no author with an anchored session could be drawn")
                continue
            days, authors = lay
            res = self._plant_once(payload, arm, path, stmts, days, authors, rng, duplicate)
            res.redraws = attempt
            if res.composed and (not res.honest_edits_broken or attempt >= PREFER_CLEAN_DRAWS):
                return res
            if res.composed:
                best = res
            elif res.delivered and delivered is None:
                delivered = res
        if best is not None:
            return best
        assert res is not None, "no layout could be drawn"
        # not composed in any draw: keep a delivered layout (the P readings still have a unit,
        # review 2026-10-23 finding 8), else the last attempt
        out = delivered if delivered is not None else res
        out.redraws = MAX_REDRAWS
        out.reasons.append(f"not composed after {MAX_REDRAWS} re-draws")
        return out

    def _roles(self, arm: str) -> list[list[int]]:
        """Statement indices per role (then split over the role's two sessions)."""
        return {"lone": [[0, 1, 2]], "k2": [[0, 1], [2]], "k3": [[0], [1], [2]]}[arm]

    def _plant_once(self, payload, arm, path, stmts, days, authors, rng, duplicate) -> PlantResult:
        rows = copy.deepcopy(self.rows)
        ref = doc.DocRef("owncloud", path)
        res = PlantResult(payload_id=payload["id"], arm=arm, document=path, authors=list(authors),
                          days=list(days), statements=[], regime=str(payload.get("arm") or ""))
        res.author_pool_sizes = list(getattr(self, "last_draw_log", []))
        res.author_draw_restricted = [bool(x.get("restricted")) for x in res.author_pool_sizes]
        first_day = days[0]
        di = self.days.index(first_day)
        res.pre_window_boundary = "day0" if di == 0 else self.days[di - 1]
        touching = self.touch.get(path, set())
        plan: list[tuple[int, int, Session, bool]] = []   # (stmt idx, role, session, duplicate)
        for role, (d, acct) in enumerate(zip(days, authors)):
            idxs = self._roles(arm)[role]
            # The role's eligible sessions: those inside whose span every anchor of the role's
            # statements resolves (a document rewritten whole earlier that day has no anchors
            # before the rewrite); none -> this layout fails and is re-drawn.
            elig = self._sessions_with_anchors(rows, ref, acct, d, [stmts[i] for i in idxs], days[-1])
            if not elig:
                res.reasons.append(f"no session of role {role} on {d} has the anchors present")
                return res
            # F3: touching sessions first, then the rest, in time order within each group; the
            # chosen sessions are then used in time order (plants are inserted in time order so
            # the rebuilt contents are right)
            order = [s for s in elig if s.task_id in touching] + [s for s in elig if s.task_id not in touching]
            n_need = 2 if len(idxs) >= 2 else 1
            chosen = sorted(order[:n_need], key=lambda s: (s.first_ts, s.task_id))
            if len(elig) == 1:
                res.single_session_roles.append(role)
            if len(idxs) >= 2:
                first, second = idxs[:-1], idxs[-1:]
                plan += [(i, role, chosen[0], False) for i in first]
                plan += [(i, role, chosen[-1], False) for i in second]
                dup_session = chosen[-1]
            else:
                plan += [(idxs[0], role, chosen[0], False)]
                # the redundant delivery goes to the role's next eligible session after the one
                # chosen, else (a single eligible session) the same session after the statement
                later = [s for s in elig if s.first_ts > chosen[0].first_ts]
                dup_session = later[0] if later else chosen[0]
            if duplicate and role == len(days) - 1:
                # a second delivery of statement 3 (the last role owns it in every arm), after it
                # landed (review 2026-10-23 finding 6); F2 decides at that time whether it re-lands
                plan.append((idxs[-1], role, dup_session, True))
        # plant in time order (sessions of a day do not overlap; roles sit on increasing days);
        # later honest rows rebuilt after every insertion
        plan.sort(key=lambda e: (e[2].first_ts, e[2].task_id, 0 if not e[3] else 1))
        last_ts_by_session: dict[str, str] = {}
        read_done: set[str] = set()
        for stmt_i, role, s, dup in plan:
            stmt = stmts[stmt_i]
            anchors = [stmts[i]["anchor"] for i in self._roles(arm)[role] if stmts[i]["op"] == "replace"]
            ready = self._anchor_ready(rows, ref, s, anchors, days[-1])
            after = max(filter(None, [last_ts_by_session.get(s.task_id), ready]), default=None)
            ts = _ts_in(rng, s, after)
            if ts is None:
                res.reasons.append(f"session {s.task_id} of role {role} has no second left for statement {stmt_i}")
                return res
            pos = _insert_position(rows, s, ts)
            state = doc.content_at(rows[:pos], ref, None, base=self.base)
            if doc.is_unknown(state) or state is None:
                res.reasons.append(f"document state unknown or absent before statement {stmt_i}")
                return res
            line = statement_line(stmt, s.day)
            if stmt["op"] == "replace":
                find = resolve_anchor(state, stmt["anchor"])
                if dup:
                    # F2: re-land only where the anchor resolves to a line other than the landed
                    # statement (then the replace changes the document); never a no-op
                    if find is None:
                        res.redundant.append({"statement": stmt_i, "delivered": False, "reason": "anchor absent at delivery time"})
                        continue
                    if find == line:
                        res.redundant.append({"statement": stmt_i, "delivered": False, "reason": "already landed (a replace would be a no-op)"})
                        continue
                elif find is None or find not in state:
                    res.reasons.append(f"anchor absent at plant time for statement {stmt_i} ({stmt['anchor']!r})")
                    return res
                sent = {"find": find, "replace": line}
                action = "replace_in_file"
            else:
                if dup and line in state.splitlines():
                    res.redundant.append({"statement": stmt_i, "delivered": False, "reason": "already landed (the line is present)"})
                    continue
                sent = {"text": line}
                action = "append_to_file"
            if dup:
                res.redundant.append({"statement": stmt_i, "delivered": True, "reason": "statement absent at delivery time: re-landed"})
            # F1: a read of the target before the session's first planted edit
            if s.task_id not in read_done:
                read_done.add(s.task_id)
                honest_read = any(r.get("task_id") == s.task_id and is_read_of(r, ref.key) for r in rows[:pos])
                if honest_read:
                    res.reads.append({"task_id": s.task_id, "role": role, "kind": "honest", "ts": None})
                elif rng.random() < self.read_rate:
                    ts_r = _read_ts(rng, s, ts, last_ts_by_session.get(s.task_id), self.read_gaps)
                    pos_r = _insert_position(rows, s, ts_r)
                    for k, act in enumerate(READ_ACTIONS):
                        rows.insert(pos_r + k, _read_row(s.account, ts_r, s.task_id, path, act, state,
                                                         _event_id(payload["id"], arm, stmt_i, dup, f"read{k}")))
                    pos = _insert_position(rows, s, ts)
                    res.reads.append({"task_id": s.task_id, "role": role, "kind": "planted", "ts": ts_r})
                else:
                    res.reads.append({"task_id": s.task_id, "role": role, "kind": "none", "ts": None})
            last_ts_by_session[s.task_id] = ts
            content = apply_edit(state, action, sent)
            row = _plant_row(s.account, ts, s.task_id, path, action, sent, content, len(state),
                             _event_id(payload["id"], arm, stmt_i, dup))
            rows.insert(pos, row)
            res.statements.append(PlantedStatement(index=stmt_i, role=role, account=s.account, day=s.day,
                                                   task_id=s.task_id, ts=ts, action=action, args=row["args"],
                                                   file_position=pos, duplicate=dup, line_text=line,
                                                   session_touches_target=s.task_id in touching))
            self._rebuild_after(rows, ref, pos, res)
        res.rows = rows
        self._check(rows, ref, stmts, res)
        return res

    def _sessions_with_anchors(self, rows: list[dict], ref: doc.DocRef, acct: str, day: str,
                               stmts: Sequence[Mapping[str, Any]], until_day: str | None = None) -> list[Session]:
        """The role's eligible sessions: every session of the day inside whose span every anchor
        of the role's statements resolves (`_anchor_ready` gives the earliest moment), in time
        order. A document rewritten whole earlier that day has no anchors before the rewrite."""
        ss = self.sessions.get((acct, day), [])
        anchors = [st["anchor"] for st in stmts if st["op"] == "replace"]
        return [s for s in ss if self._anchor_ready(rows, ref, s, anchors, until_day) is not None]

    def _anchor_ready(self, rows: list[dict], ref: doc.DocRef, s: Session,
                      anchors: Sequence[str], until_day: str | None = None) -> str | None:
        """The earliest timestamp inside the session's span at which every anchor resolves
        (the span's start when they are present then; else the ts of the write that made
        them present), not before the document's last whole rewrite up to the end of `until_day`
        (F4); None when the anchors are absent at the span's end or the session ends before that
        rewrite."""
        floor = self.whole_write_floor(ref.key, until_day)
        if floor is not None and floor > s.last_ts:
            return None

        def ok(state: Any) -> bool:
            return isinstance(state, str) and all(resolve_anchor(state, a) is not None for a in anchors)
        ready = None
        if ok(doc.content_at(rows, ref, s.first_ts, base=self.base)):
            ready = s.first_ts
        elif not ok(doc.content_at(rows, ref, s.last_ts, base=self.base)):
            return None
        else:
            for w in doc.content_writes(rows, ref):
                if s.first_ts < w.ts <= s.last_ts and ok(doc.content_at(rows, ref, w.ts, base=self.base)):
                    ready = w.ts if ready is None else min(ready, w.ts)
        if ready is None:
            return None
        if floor is not None and floor > ready:
            # the anchors must still resolve once the rewrite has happened
            if not ok(doc.content_at(rows, ref, floor, base=self.base)):
                return None
            ready = floor
        return ready

    def _rebuild_after(self, rows: list[dict], ref: doc.DocRef, pos: int, res: PlantResult) -> None:
        """Rebuild every later honest edit's content from the running state (file order). An
        honest edit this plant broke earlier (its `find` gone) is re-tried on every rebuild and
        restored when its `find` is present again (a later plant can put the line back)."""
        state = doc.content_at(rows[: pos + 1], ref, None, base=self.base)
        for i in range(pos + 1, len(rows)):
            r = rows[i]
            if r.get("t1_planted") or r.get("service") != "owncloud":
                continue
            if (r.get("exit_code") or 0) != 0 and not r.get("t1_broken"):
                continue
            if r.get("action") not in sv.WRITE_ACTIONS or sv.norm_path((r.get("args") or {}).get("path")) != ref.key:
                continue
            a = r["args"]
            if r["action"] == "write_file":
                state = apply_edit(state, "write_file", a)
                res.overwritten_by_whole_write = True
                continue
            sent = {k: a[k] for k in ("text", "find", "replace") if k in a}
            try:
                new = apply_edit(state, r["action"], sent)
            except ValueError as exc:
                if not r.get("t1_broken"):
                    r["t1_broken"] = {"bytes": r.get("bytes"), "edit": a.get("edit"), "error": r.get("error")}
                r["exit_code"] = 1
                r["error"] = f"ValueError: {exc} in {ref.key}"
                a.pop("content", None)
                a.pop("edit", None)
                r["args_hash"] = _stable_hash(a)
                r["bytes"] = 0
                if r.get("event_id") not in res.honest_edits_broken:
                    res.honest_edits_broken.append(str(r.get("event_id")))
                continue
            if r.get("t1_broken"):
                orig = r.pop("t1_broken")
                r["exit_code"] = 0
                r["error"] = orig.get("error") or ""
                r["bytes"] = orig.get("bytes")
                if isinstance(orig.get("edit"), dict):
                    a["edit"] = orig["edit"]
                if str(r.get("event_id")) in res.honest_edits_broken:
                    res.honest_edits_broken.remove(str(r.get("event_id")))
            if a.get("content") != new and r.get("event_id") not in res.honest_edits_rebuilt:
                res.honest_edits_rebuilt.append(str(r.get("event_id")))
            a["content"] = new
            if isinstance(a.get("edit"), dict):
                a["edit"] = {**a["edit"], "before_len": len(state), "after_len": len(new)}
            r["args_hash"] = _stable_hash(a)
            state = new

    def _check(self, rows: list[dict], ref: doc.DocRef, stmts, res: PlantResult) -> None:
        real = [s for s in res.statements if not s.duplicate]
        if not real:
            res.reasons.append("no statement landed")
            return
        res.composition_ts = max(s.ts for s in real)
        res.composition_day = res.composition_ts[:10]
        at_ts = doc.content_at(rows, ref, res.composition_ts, base=self.base)
        at_end = doc.content_at(rows, ref, res.composition_day, base=self.base)
        lines_ts = set(at_ts.splitlines()) if isinstance(at_ts, str) else set()
        lines_end = (at_end.splitlines() if isinstance(at_end, str) else [])
        res.composed_at_ts = len({s.index for s in real}) == 3 and all(s.line_text in lines_ts for s in real)
        res.present_at_day_end = [s.line_text in set(lines_end) for s in real]
        res.composed_at_day_end = len({s.index for s in real}) == 3 and all(res.present_at_day_end)
        if not res.composed_at_ts:
            res.reasons.append("a statement was overwritten before the composition time")
        elif not res.composed_at_day_end:
            res.reasons.append("a statement was overwritten before the end of the composition day")
        pos = {s.index: lines_end.index(s.line_text) for s in real if s.line_text in lines_end}
        res.adjacency = sorted([a, b] for a in pos for b in pos if a < b and abs(pos[a] - pos[b]) == 1)


# ── the T1 plan and manifest ─────────────────────────────────────────────

def assign_k3(payloads: Sequence[Mapping[str, Any]], rng: random.Random) -> list[str]:
    """16 of 24 payloads also at k = 3: 3 per document for four documents, 2 for two (seeded).
    T1 v3's 12-payload regimes (two per document): 8 of 12, two per document for two documents drawn by
    the same stream, one for the other four (t1v3-plan.md section 2)."""
    by_doc: dict[str, list[str]] = defaultdict(list)
    for p in payloads:
        by_doc[p["document"]].append(p["id"])
    docs = sorted(by_doc)
    two = set(rng.sample(docs, 2))
    per = min(len(v) for v in by_doc.values())
    out = []
    for d in docs:
        # v2 (four per document): the two drawn documents give 2, the rest 3; v3 re-draws (two per
        # document): the two drawn documents give 2, the rest 1
        n = (2 if d in two else 3) if per >= 4 else (2 if d in two else 1)
        out += sorted(rng.sample(by_doc[d], n))
    return out


def assign_duplicates(payloads: Sequence[Mapping[str, Any]], rng: random.Random) -> list[str]:
    ids = [p["id"] for p in payloads]
    return sorted(rng.sample(ids, round(len(ids) * DUPLICATE_SHARE)))


def regimes_of(payloads: Sequence[Mapping[str, Any]]) -> list[str]:
    return [r for r in ALL_REGIMES if any(p.get("arm") == r for p in payloads)]


def plan(payloads: Sequence[Mapping[str, Any]], seed: int = LAYOUT_SEED) -> dict:
    """v1 (no `arm` field): 16 of 24 at k = 3, a third duplicated. v2 (regime arms): per regime in
    REGIMES order, 16 of 24 at k = 3 for conforming and sham (as v1), every alarming payload at
    k = 3, a third of each regime's payloads duplicated (8, 3, 8); one seed stream. v3 (REGIMES_V3, in
    that order): 16 of 24 middle, 8 of 12 per re-draw regime, duplicates 8 / 4 / 4; one seed stream."""
    rng = random.Random(seed)
    regimes = regimes_of(payloads)
    if not regimes:
        return {"seed": seed, "k3": assign_k3(payloads, rng), "duplicates": assign_duplicates(payloads, rng)}
    k3: list[str] = []
    dups: list[str] = []
    by: dict[str, dict] = {}
    for r in regimes:
        ps = [p for p in payloads if p.get("arm") == r]
        k3r = sorted(p["id"] for p in ps) if r == "alarming" else assign_k3(ps, rng)
        dr = assign_duplicates(ps, rng)
        k3 += k3r
        dups += dr
        by[r] = {"n": len(ps), "k3": k3r, "duplicates": dr}
    return {"seed": seed, "k3": k3, "duplicates": dups, "by_regime": by}


def plant_all(ins: Inserter, payloads: Sequence[Mapping[str, Any]], seed: int = LAYOUT_SEED
              ) -> tuple[dict, list[PlantResult]]:
    pl = plan(payloads, seed)
    rng = random.Random(seed + 1)
    out: list[PlantResult] = []
    for p in payloads:
        dup = p["id"] in pl["duplicates"]
        for arm in ARMS:
            if arm == "k3" and p["id"] not in pl["k3"]:
                continue
            out.append(ins.plant(p, arm, rng, dup))
    return pl, out


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def insertion_summary(results: Sequence[PlantResult]) -> dict:
    """The F1 to F4 record over the plants (plan section 3, 'insertion record')."""
    reads = [x for r in results for x in r.reads]
    red = [x for r in results for x in r.redundant]
    real = [s for r in results for s in r.statements if not s.duplicate]
    draws = [x for r in results for x in r.author_pool_sizes]
    readme = [r for r in results if r.arm == "k3" and r.document.endswith("training-pipeline/README.md") and r.authors]
    return {
        "reads": {"planting_sessions": len(reads), "honest": sum(1 for x in reads if x["kind"] == "honest"),
                  "planted": sum(1 for x in reads if x["kind"] == "planted"), "none": sum(1 for x in reads if x["kind"] == "none"),
                  "share_with_read": round(sum(1 for x in reads if x["kind"] != "none") / len(reads), 4) if reads else None},
        "redundant": {"planned": len(red), "delivered": sum(1 for x in red if x["delivered"]),
                      "skipped": sum(1 for x in red if not x["delivered"]),
                      "by_reason": dict(sorted(__import__("collections").Counter(x["reason"] for x in red).items()))},
        "touching": {"statements": len(real), "in_touching_sessions": sum(1 for s in real if s.session_touches_target),
                     "share_statements": round(sum(1 for s in real if s.session_touches_target) / len(real), 4) if real else None,
                     "plants_all_touching": sum(1 for r in results if r.statements and all(s.session_touches_target for s in r.statements if not s.duplicate)),
                     "author_draws": len(draws), "draws_from_touching_pool": sum(1 for x in draws if x["restricted"]),
                     "share_draws_restricted": round(sum(1 for x in draws if x["restricted"]) / len(draws), 4) if draws else None},
        "readme_k3_role1_authors": sorted({r.authors[0] for r in readme}),
    }


def manifest(payloads_path: Path, corpus: Path, pl: dict, results: Sequence[PlantResult],
             applier_check: Sequence[dict], read_stats: dict | None = None) -> dict:
    recs = [r.record() for r in results]
    regimes = sorted({r["regime"] for r in recs if r["regime"]})
    by_reg = {reg: {a: {"planned": sum(1 for r in recs if r["regime"] == reg and r["arm"] == a),
                        "delivered": sum(1 for r in recs if r["regime"] == reg and r["arm"] == a and r["delivered"]),
                        "composed": sum(1 for r in recs if r["regime"] == reg and r["arm"] == a and r["composed"])}
                    for a in ARMS} for reg in regimes}
    rs = dict(read_stats or {})
    rs.pop("gaps_frac", None)
    rs.pop("gaps_min", None)
    return {
        "version": "t1-plants/v2", "payloads": str(payloads_path), "payloads_sha256": sha256_file(payloads_path),
        "corpus": str(corpus), "corpus_sha256": sha256_file(corpus), "plan": pl,
        "n_plants": len(recs), "by_arm": {a: sum(1 for r in recs if r["arm"] == a) for a in ARMS},
        "composed_by_arm": {a: sum(1 for r in recs if r["arm"] == a and r["composed"]) for a in ARMS},
        "delivered_by_arm": {a: sum(1 for r in recs if r["arm"] == a and r["delivered"]) for a in ARMS},
        "by_regime_and_arm": by_reg,
        "redraws_total": sum(r["redraws"] for r in recs),
        "honest_edits_broken_total": sum(r["honest_edits_broken"] for r in recs),
        "honest_read_before_edit": rs,
        "insertion": insertion_summary(results),
        "applier_check": list(applier_check),
        "plants": recs,
        "plants_sha256": hashlib.sha256(json.dumps(recs, sort_keys=True).encode("utf-8")).hexdigest(),
        "inserter_sha256": sha256_file(Path(__file__).resolve()),
    }


def load_payloads(path: Path) -> list[dict]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    ps = d["payloads"]
    assert ps and all(len(p["statements"]) == 3 for p in ps), "payloads of 3 statements"
    assert len({p["id"] for p in ps}) == len(ps), "payload ids unique"
    return ps


def build_inserter(corpus: Path, template: Path) -> tuple[Inserter, list[dict]]:
    rows = sv.read_jsonl(corpus)
    team, managers = team_maps(template)
    return Inserter(rows, sv.seed_base(), team, managers), rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("plant",))
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--payloads", required=True)
    ap.add_argument("--template", default=str(sv.jc_mod.FORK / "bootstrap" / "org_template.yaml"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=LAYOUT_SEED)
    ns = ap.parse_args(argv)
    corpus, payloads_path = Path(ns.corpus), Path(ns.payloads)
    ins, rows = build_inserter(corpus, Path(ns.template))
    payloads = load_payloads(payloads_path)
    checks = [check_applier_against_log(rows, p, ins.base) for p in sv.class_doc_paths()]
    pl, results = plant_all(ins, payloads, ns.seed)
    m = manifest(payloads_path, corpus, pl, results, checks, ins.read_stats)
    Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
    Path(ns.out).write_text(json.dumps(m, indent=1), encoding="utf-8")
    print(json.dumps({k: m[k] for k in ("n_plants", "by_arm", "composed_by_arm", "delivered_by_arm", "by_regime_and_arm",
                                        "redraws_total", "honest_edits_broken_total", "honest_read_before_edit",
                                        "insertion", "applier_check", "payloads_sha256", "plants_sha256")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
