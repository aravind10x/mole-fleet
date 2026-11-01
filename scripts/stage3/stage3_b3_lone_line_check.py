#!/usr/bin/env python3
"""Brief 27 E1 and E4 (B3): the default-mode replay of the T1 v3 manifest, and brief 26's check reproduced through the
application module's new lone-line arm and valid-draw restriction (`stage3_t1.PartSInserter`). $0, no API call; every
document state is an in-memory copy of the null corpus; nothing on disk changes but this script's outputs.

  replay  E1: `plant_all` on the T1 v3 manifest's payloads and seed with the pre-change module (the fork's
          scripts/stage3/stage3_t1.py at e3409b9, sha256 52a79312), the new module's Inserter, and the new module's
          PartSInserter without a valid-draws file; every plant's record and rows (the produced corpus: every document
          state's content) compared by hash, and the records' hash against the manifest's plants_sha256.
  dryrun  E4 (a): brief 26's script, unchanged (sha256 999cb737), run against the new module in default mode into
          --out-dir; its drop lists and every per-item and per-lone-line valid-draw set compared with brief 26's output
          (edd289ce); differences counted by reason, never reconciled.
  lines   E4 (b): each of the 234 lone lines through the new arm in restricted mode (brief 26's file) at each listed
          valid draw, RUNS_PER_DRAW seeded samples each: the line's target found once, the application equal to the
          intended result, the line not already present, the line present at its time and at the end of its day; the
          per-line verdicts compared with brief 26's. Beside: every drawable draw brief 26 did not list, applied in default
          mode and read by the arm's own check at the drawn state.
  items   beside E4: every item's listed valid draws through the restricted lone arm, and Part S's pair selection
          (`plant_pair`) on all 124 items.
  report  work/stage3/b3/lone-line-arm-v0.json from the parts (ids, counts, reason codes, days, honest account names and
          hashes only; brief 26's guard refuses any item line, anchor, declared effect or document text).

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_lone_line_check.py replay
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import inspect
import json
import multiprocessing as mp
import random
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_inserter_dry_run as dr  # noqa: E402  (brief 26's script: read and run, never changed)
import stage3_t1 as t1  # noqa: E402
import stage3_views as sv  # noqa: E402

VERSION = "b3-lone-line-arm/v0"
PROJECT = HERE.parent.parent
FORK = PROJECT / "work" / "mole-fork"
B3 = PROJECT / "work" / "stage3" / "b3"
PARTS = B3 / "lone-line-arm"
OUT = B3 / "lone-line-arm-v0.json"
TEMPLATE = sv.jc_mod.FORK / "bootstrap" / "org_template.yaml"
T1V3 = PROJECT / "work" / "stage3" / "t1v3" / "plants-v3.json"
B26_JSON = B3 / "inserter-dry-run-v0.json"
B26_JSON_SHA256 = "edd289ce"                     # prefix, as STATUS records it
B26_SCRIPT = HERE / "stage3_b3_inserter_dry_run.py"
B26_SCRIPT_SHA256 = "999cb7375cdefe212335e307cef6120c702436be1c6d5270f621844750b3ddf5"
PRE_COMMIT = "e3409b9"                          # the fork's last change to the module before brief 27
PRE_SHA256 = "52a79312b1e2ce4618451e620c766c1e5aabe6b93cbde0f59a22aa72ed0d96e2"
PRE_CLASS_SHA256 = "24d3d147d6f5e6a052820714dfefebe2442aaeaf5f796cf299fe319c41027b4a"
RUN_SEED = "b27-lone-line-check-20261101"       # the timestamp samples of this check (not Part S's stream)
RUNS_PER_DRAW = 2                               # as brief 26: two placed samples per draw
ACCEPTED = "accepted at the drawn state"


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_json(o: Any) -> str:
    return sha256_bytes(json.dumps(o, sort_keys=True, default=str).encode("utf-8"))


def class_sha256(cls: type) -> str:
    return sha256_bytes(inspect.getsource(cls).encode("utf-8"))


def _rng(*parts: Any) -> random.Random:
    return random.Random("|".join(str(p) for p in (RUN_SEED,) + parts))


def fingerprint() -> dict:
    """The inputs a part was made with: the module, this harness, the valid-draws file, brief 26's script."""
    return {"module_sha256": sha256_bytes(Path(t1.__file__).read_bytes()),
            "harness_sha256": sha256_bytes(Path(__file__).resolve().read_bytes()),
            "valid_draws_sha256": sha256_bytes(B26_JSON.read_bytes()),
            "brief26_script_sha256": sha256_bytes(B26_SCRIPT.read_bytes())}


#: the inputs as this process loaded them (the module is imported above); a part carries this fingerprint, and is
#: saved only when the inputs on disk still match it at the end of the run (Codex round 2)
FINGERPRINT_AT_IMPORT = fingerprint()


def check_parts(parts: Mapping[str, Mapping[str, Any]], fp: Mapping[str, str]) -> None:
    """The report assembles only parts made with the current inputs."""
    bad = sorted(n for n, part in parts.items() if part.get("fingerprint") != dict(fp))
    if bad:
        raise SystemExit(f"refusing: parts made with other inputs (re-run them): {bad}")


# ── E1: the replay ─────────────────────────────────────────────────────────────────────────────────

def pre_change_source() -> bytes:
    src = subprocess.run(["git", "-C", str(FORK), "show", f"{PRE_COMMIT}:scripts/stage3/stage3_t1.py"],
                         capture_output=True, check=True).stdout
    if sha256_bytes(src) != PRE_SHA256:
        raise SystemExit(f"refusing: the fork's {PRE_COMMIT} module is not {PRE_SHA256[:8]}")
    return src


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _replay_one(task: tuple[str, str | None]) -> tuple[str, dict]:
    variant, pre_path = task
    mod = load_module(Path(pre_path), "stage3_t1_pre27") if variant == "pre" else t1
    cls = t1.PartSInserter if variant == "parts" else mod.Inserter
    man = json.loads(T1V3.read_text(encoding="utf-8"))
    corpus, payloads_path = Path(man["corpus"]), Path(man["payloads"])
    if sha256_bytes(corpus.read_bytes()) != man["corpus_sha256"] or sha256_bytes(payloads_path.read_bytes()) != man["payloads_sha256"]:
        raise SystemExit("refusing: the corpus or the payloads differ from the T1 v3 manifest's")
    team, managers = mod.team_maps(TEMPLATE)
    ins = cls(sv.read_jsonl(corpus), sv.seed_base(), team, managers)
    pl, results = mod.plant_all(ins, mod.load_payloads(payloads_path), man["plan"]["seed"])
    recs = [r.record() for r in results]
    return variant, {"class": cls.__name__, "class_sha256": class_sha256(cls), "inserter_class_sha256": class_sha256(mod.Inserter),
                     "module_sha256": sha256_bytes(Path(mod.__file__).read_bytes()), "plan_sha256": sha256_json(pl),
                     "plants_sha256": sha256_bytes(json.dumps(recs, sort_keys=True).encode("utf-8")),
                     "plants": [[r.payload_id, r.arm, sha256_json(rec), sha256_json(r.rows)] for r, rec in zip(results, recs)]}


def replay(procs: int = 3) -> dict:
    man = json.loads(T1V3.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        pre = Path(td) / "stage3_t1_pre27.py"
        pre.write_bytes(pre_change_source())
        with mp.get_context("fork").Pool(procs) as pool:
            out = dict(pool.map(_replay_one, [("pre", str(pre)), ("new", None), ("parts", None)], chunksize=1))
    a, b, c = out["pre"], out["new"], out["parts"]
    same_plants = a["plants"] == b["plants"] == c["plants"]
    per_plant_diff = sum(1 for x, y, z in zip(a["plants"], b["plants"], c["plants"]) if not x == y == z)
    return {"manifest": str(T1V3.relative_to(PROJECT)), "manifest_sha256": sha256_bytes(T1V3.read_bytes()),
            "manifest_plants_sha256": man["plants_sha256"], "seed": man["plan"]["seed"], "n_plants": len(a["plants"]),
            "by_arm": dict(Counter(p[1] for p in a["plants"])),
            "variants": {k: {kk: v for kk, v in out[k].items() if kk != "plants"} for k in ("pre", "new", "parts")},
            "records_equal": [p[2] for p in a["plants"]] == [p[2] for p in b["plants"]] == [p[2] for p in c["plants"]],
            "rows_equal": [p[3] for p in a["plants"]] == [p[3] for p in b["plants"]] == [p[3] for p in c["plants"]],
            "plants_differing": per_plant_diff,
            "plants_sha256_equal_manifest": a["plants_sha256"] == b["plants_sha256"] == c["plants_sha256"] == man["plants_sha256"],
            "identical": same_plants and a["plan_sha256"] == b["plan_sha256"] == c["plan_sha256"]
                         and a["plants_sha256"] == b["plants_sha256"] == c["plants_sha256"] == man["plants_sha256"]}


def module_diff() -> dict:
    """The module diff, pre-change to new, as hunks (line ranges and counts; module code only, no item text)."""
    old = pre_change_source().decode("utf-8").splitlines()
    new = Path(t1.__file__).read_text(encoding="utf-8").splitlines()
    hunks = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag != "equal":
            hunks.append({"op": tag, "old_lines": [i1 + 1, i2], "new_lines": [j1 + 1, j2], "removed": i2 - i1, "added": j2 - j1})
    src = Path(t1.__file__).read_text(encoding="utf-8")
    return {"hunks": hunks, "removed": sum(h["removed"] for h in hunks), "added": sum(h["added"] for h in hunks),
            "inserter_class_source_in_old_and_new": inspect.getsource(t1.Inserter) in "\n".join(old) + "\n" and
            inspect.getsource(t1.Inserter) in src}


# ── E4 (a): brief 26's script, unchanged ──────────────────────────────────────────────────────────

def _set(draws: Sequence) -> set[tuple[str, str]]:
    return {tuple(x) for x in draws}


def compare_dryrun(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict:
    diffs: Counter = Counter()
    if old["drop_list"]["ids"] != new["drop_list"]["ids"]:
        diffs["drop list (pair rule)"] += 1
    if old["drop_list"]["ids_literal"] != new["drop_list"]["ids_literal"]:
        diffs["drop list (literal count)"] += 1
    if old["drop_list"]["net_n"] != new["drop_list"]["net_n"]:
        diffs["net n's"] += 1
    for side in (old, new):
        ids = [it["item_id"] for it in side["items"]]
        if len(ids) != len(set(ids)):
            diffs["duplicate item ids"] += 1
    oi, ni = {it["item_id"]: it for it in old["items"]}, {it["item_id"]: it for it in new["items"]}
    if set(oi) != set(ni):
        diffs["item ids"] += 1
    n_sets = n_line_sets = 0
    for k in sorted(set(oi) & set(ni)):
        a, b = oi[k], ni[k]
        n_sets += 1
        if _set(a["draws"]["valid_draws"]) != _set(b["draws"]["valid_draws"]):
            diffs["item valid-draw set"] += 1
        if a["draws"]["n_drawable"] != b["draws"]["n_drawable"]:
            diffs["item drawable draws"] += 1
        if len(a["lone_lines"]) != len(b["lone_lines"]):
            diffs["lone-line count"] += 1
        for la, lb in zip(a["lone_lines"], b["lone_lines"]):
            n_line_sets += 1
            if _set(la["valid_draws"]) != _set(lb["valid_draws"]):
                diffs["lone-line valid-draw set"] += 1
            if la["n_drawable"] != lb["n_drawable"]:
                diffs["lone-line drawable draws"] += 1
        if (a["drop"], a["drop_literal"]) != (b["drop"], b["drop_literal"]):
            diffs["item drop decision"] += 1
        if a != b:
            diffs["item record (any field)"] += 1
    skip = {"module", "written", "s1_restriction", "module_findings"}
    sections = {s: old.get(s) == new.get(s) for s in old if s not in skip}
    fo = [(f["id"], f["count"], f["count_of"]) for f in old["module_findings"]]
    fn = [(f["id"], f["count"], f["count_of"]) for f in new["module_findings"]]
    if fo != fn:
        diffs["module finding counts"] += 1
    return {"differences_by_reason": dict(diffs), "items_compared": n_sets, "lone_line_sets_compared": n_line_sets,
            "sections_equal": sections, "module_finding_counts_equal": fo == fn,
            "module_finding_lines": {"old": {f["id"]: f["lines"] for f in old["module_findings"]},
                                     "new": {f["id"]: f["lines"] for f in new["module_findings"]}},
            "module_old": {k: old["module"][k] for k in ("sha256", "inserter_class_sha256", "inserter_class_equals_t1v3_manifest")},
            "module_new": {k: new["module"][k] for k in ("sha256", "inserter_class_sha256", "inserter_class_equals_t1v3_manifest")},
            "module_lines_new": new["module"]["lines"],
            "drop_ids": new["drop_list"]["ids"], "drop_ids_literal": new["drop_list"]["ids_literal"], "net_n": new["drop_list"]["net_n"],
            "reproduced": not diffs}


def dryrun(out_dir: Path, procs: int) -> dict:
    if sha256_bytes(B26_SCRIPT.read_bytes()) != B26_SCRIPT_SHA256:
        raise SystemExit("refusing: brief 26's script is not the one brief 26 ran")
    old_raw = B26_JSON.read_bytes()
    if not sha256_bytes(old_raw).startswith(B26_JSON_SHA256):
        raise SystemExit("refusing: brief 26's output is not edd289ce")
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.resolve() == B3.resolve():
        raise SystemExit("refusing: --out-dir would overwrite brief 26's output")
    t0 = datetime.now()
    subprocess.run([sys.executable, "-I", str(B26_SCRIPT), "run", "--out-dir", str(out_dir), "--procs", str(procs)],
                   cwd=str(HERE), check=True, stdout=subprocess.DEVNULL)
    secs = (datetime.now() - t0).total_seconds()
    new_raw = (out_dir / "inserter-dry-run-v0.json").read_bytes()
    out = compare_dryrun(json.loads(old_raw), json.loads(new_raw))
    out.update({"script": str(B26_SCRIPT.relative_to(PROJECT)), "script_sha256": B26_SCRIPT_SHA256,
                "old_sha256": sha256_bytes(old_raw), "new_json": str((out_dir / "inserter-dry-run-v0.json").relative_to(PROJECT)),
                "new_sha256": sha256_bytes(new_raw), "new_md_sha256": sha256_bytes((out_dir / "inserter-dry-run-v0.md").read_bytes()),
                "procs": procs, "seconds": round(secs)})
    return out


# ── E4 (b) and the items: workers (fork: the inserters are built once and shared) ─────────────────

_G: dict[str, Any] = {}


def _init(valid_path: Path) -> None:
    rows = sv.read_jsonl(dr.CORPUS)
    team, managers = t1.team_maps(TEMPLATE)
    _G["valid"] = t1.ValidDraws.load(valid_path)
    _G["ins"] = t1.PartSInserter(rows, sv.seed_base(), team, managers, valid_draws=_G["valid"])     # restricted
    _G["ins_default"] = t1.PartSInserter(rows, sv.seed_base(), team, managers)                     # default mode


def _payload(it: Mapping[str, Any]) -> dict:
    return {"id": it["payload_id"], "document": it["document"], "statements": it["statements"], "arm": dr.RATED_ARM[it["regime"]]}


def _apply_listed(ins: t1.PartSInserter, ins_d: t1.PartSInserter, payload: Mapping[str, Any], arm: str, key: str,
                  d: str, a: str) -> tuple[str | None, bool | None]:
    """RUNS_PER_DRAW restricted applications at a listed draw: (None, same) when every sample is accepted, else the
    first refusal's reason. `same`: the first sample's document (rows) and record equal the default mode's
    `apply_at` at the same draw and seed (no restriction: no list, no check)."""
    same = None
    ex = () if arm in t1.LINE_ARMS else None          # independent applications at listed draws: no triple to exclude
    for k in range(RUNS_PER_DRAW):
        try:
            res = ins.apply_at(payload, arm, d, a, _rng(key, arm, d, a, k), key=key, exclude=ex)
        except t1.Refused as r:
            return r.reason, same
        if k == 0:
            try:
                dflt = ins_d.apply_at(payload, arm, d, a, _rng(key, arm, d, a, k), exclude=ex)
                same = dflt.record() == res.record() and sha256_json(dflt.rows) == sha256_json(res.rows)
            except ValueError:
                same = False
    return None, same


def _check_unlisted(ins: t1.PartSInserter, payload: Mapping[str, Any], arm: str, key: str, d: str, a: str) -> str:
    """Beside: a draw brief 26 did not list, in default mode, read by the arm's own check at the drawn state."""
    ex = () if arm in t1.LINE_ARMS else None
    for k in range(RUNS_PER_DRAW):
        try:
            res = ins.apply_at(payload, arm, d, a, _rng(key, arm, d, a, k, "unlisted"), exclude=ex)
        except ValueError:
            return t1.RF_REJECTED
        reason = ins.check_application(res, payload["statements"])
        if reason is not None:
            return reason
    return ACCEPTED


def _drawable(ins: t1.PartSInserter, path: str, stmts: Sequence[Mapping[str, Any]]) -> list[tuple[str, str]]:
    anchors = [st["anchor"] for st in stmts if st["op"] == "replace"]
    return [(day, a) for day in ins.days[:2] for a in dr.drawable_authors(ins, path, day, anchors)[0]]


def _line_task(task: tuple) -> dict:
    key, i, it = task
    ins, ins_d = _G["ins"], _G["ins_default"]
    payload, arm = _payload(it), t1.line_arm(i)
    listed = _set(ins.valid.draws(key, i, it["document"]))
    drawable = _drawable(ins, it["document"], [it["statements"][i]])
    accepted, refused, unlisted, same = [], Counter(), Counter(), Counter()
    for d, a in drawable:
        if (d, a) in listed:
            r, eq = _apply_listed(ins, ins_d, payload, arm, key, d, a)
            same[str(eq)] += 1
            if r is None:
                accepted.append((d, a))
            else:
                refused[r] += 1
        else:
            unlisted[_check_unlisted(ins_d, payload, arm, key, d, a)] += 1
    return {"key": key, "line": i, "n_drawable": len(drawable), "n_listed": len(listed),
            "listed_not_drawable": len(listed - set(drawable)), "accepted": sorted(accepted),
            "refused_listed": dict(refused), "unlisted": dict(unlisted), "identical_to_default": dict(same)}


def _item_task(task: tuple) -> dict:
    key, it = task
    ins, ins_d = _G["ins"], _G["ins_default"]
    payload = _payload(it)
    listed = _set(ins.valid.draws(key, "item", it["document"]))
    drawable = _drawable(ins, it["document"], it["statements"])
    accepted, refused, unlisted, same = [], Counter(), Counter(), Counter()
    for d, a in drawable:
        if (d, a) in listed:
            r, eq = _apply_listed(ins, ins_d, payload, "lone", key, d, a)
            same[str(eq)] += 1
            if r is None:
                accepted.append((d, a))
            else:
                refused[r] += 1
        else:
            unlisted[_check_unlisted(ins_d, payload, "lone", key, d, a)] += 1
    try:
        pair = ins.plant_pair(payload, "item", _rng(key, "pair"), key=key)
        pair_out = {"refused": None, "draws": [[x.days[0], x.authors[0]] for x in pair],
                    "refused_draws": [x["reason"] for x in pair[0].refused_draws]}
    except t1.Refused as r:
        pair_out = {"refused": r.reason, "draws": [], "refused_draws": [x["reason"] for x in r.refused]}
    return {"key": key, "n_drawable": len(drawable), "n_listed": len(listed), "listed_not_drawable": len(listed - set(drawable)),
            "accepted": sorted(accepted), "refused_listed": dict(refused), "unlisted": dict(unlisted), "pair": pair_out,
            "identical_to_default": dict(same)}


def _pool_map(fn, tasks: list, procs: int) -> list:
    _init(B26_JSON)
    with mp.get_context("fork").Pool(procs) as pool:
        return pool.map(fn, tasks, chunksize=1)


def lines(procs: int) -> dict:
    items, _meta = dr.load_items(dr.input_paths())
    b26 = {it["item_id"]: it for it in json.loads(B26_JSON.read_text(encoding="utf-8"))["items"]}
    tasks = [(it["item_id"], i, it) for it in items if it["regime"] == "candidate" for i in range(3)]
    res = _pool_map(_line_task, tasks, procs)
    diffs: Counter = Counter()
    per_line, refused, unlisted = [], Counter(), Counter()
    two_authors = literal = 0
    for r in res:
        old = b26[r["key"]]["lone_lines"][r["line"]]
        acc = [tuple(x) for x in r["accepted"]]
        pair = bool(t1.compatible_pairs(acc, False))
        two_authors += pair
        literal += len(acc) >= 2
        refused.update(r["refused_listed"])
        unlisted.update(r["unlisted"])
        if set(acc) != _set(old["valid_draws"]):
            diffs["valid-draw set (accepted by the arm vs brief 26's)"] += 1
        if pair != old["pair_ok_distinct_authors"]:
            diffs["two valid draws by different authors"] += 1
        if (len(acc) >= 2) != old["literal_ok"]:
            diffs["literal two valid draws"] += 1
        if r["n_drawable"] != old["n_drawable"]:
            diffs["drawable draws"] += 1
        if r["listed_not_drawable"]:
            diffs["listed draw not drawable"] += 1
        per_line.append({"item_id": r["key"], "line": r["line"] + 1, "drawable": r["n_drawable"], "listed": r["n_listed"],
                         "accepted": len(acc), "two_by_different_authors": pair, "brief26_two_by_different_authors": old["pair_ok_distinct_authors"],
                         "refused_listed": r["refused_listed"], "unlisted": r["unlisted"]})
    same = sum((Counter(r["identical_to_default"]) for r in res), Counter())
    if same.get("False"):
        diffs["restricted application differs from default mode at the same draw and seed"] += same["False"]
    return {"identical_to_default": dict(same),
            "lines": len(res), "drawable_draws": sum(r["n_drawable"] for r in res), "listed_draws": sum(r["n_listed"] for r in res),
            "accepted_draws": sum(len(r["accepted"]) for r in res), "samples_per_draw": RUNS_PER_DRAW,
            "two_valid_distinct_authors": two_authors, "literal_two_valid": literal,
            "refused_listed_by_reason": dict(refused), "unlisted_by_check": dict(unlisted),
            "differences_by_reason": dict(diffs), "reproduced": not diffs, "per_line": per_line}


def items_check(procs: int) -> dict:
    items, _meta = dr.load_items(dr.input_paths())
    b26 = json.loads(B26_JSON.read_text(encoding="utf-8"))
    old = {it["item_id"]: it for it in b26["items"]}
    res = _pool_map(_item_task, [(it["item_id"], it) for it in items], procs)
    diffs: Counter = Counter()
    refused, unlisted, pair_refused = Counter(), Counter(), Counter()
    per_item = []
    for r in res:
        o = old[r["key"]]
        acc = [tuple(x) for x in r["accepted"]]
        refused.update(r["refused_listed"])
        unlisted.update(r["unlisted"])
        if set(acc) != _set(o["draws"]["valid_draws"]):
            diffs["valid-draw set (accepted by the restricted lone arm vs brief 26's)"] += 1
        if r["n_drawable"] != o["draws"]["n_drawable"]:
            diffs["drawable draws"] += 1
        pair_ok = r["pair"]["refused"] is None
        if pair_ok != o["draws"]["pair_ok_distinct_days"]:
            diffs["pair selection vs brief 26's item need"] += 1
        if not pair_ok:
            pair_refused[r["pair"]["refused"]] += 1
        per_item.append({"item_id": r["key"], "drawable": r["n_drawable"], "listed": r["n_listed"], "accepted": len(acc),
                         "pair": r["pair"], "brief26_item_pair_ok": o["draws"]["pair_ok_distinct_days"], "refused_listed": r["refused_listed"],
                         "unlisted": r["unlisted"]})
    dropped = sorted(r["key"] for r in res if r["pair"]["refused"] is not None)
    same = sum((Counter(r["identical_to_default"]) for r in res), Counter())
    if same.get("False"):
        diffs["restricted application differs from default mode at the same draw and seed"] += same["False"]
    return {"identical_to_default": dict(same), "items": len(res), "drawable_draws": sum(r["n_drawable"] for r in res), "listed_draws": sum(r["n_listed"] for r in res),
            "accepted_draws": sum(len(r["accepted"]) for r in res), "samples_per_draw": RUNS_PER_DRAW,
            "refused_listed_by_reason": dict(refused), "unlisted_by_check": dict(unlisted),
            "pair_refused": len(dropped), "pair_refused_by_reason": dict(pair_refused), "pair_refused_ids": dropped,
            "pair_refused_equals_brief26_drop_list": dropped == sorted(b26["drop_list"]["ids"]),
            "differences_by_reason": dict(diffs), "reproduced": not diffs, "per_item": per_item}


# ── outputs ────────────────────────────────────────────────────────────────────────────────────────

def _guard() -> list[str]:
    from stage3_t1v2_checks import DOCS
    items, _meta = dr.load_items(dr.input_paths())
    day0 = {path: text for (_svc, path), text in sv.seed_base().items() if path in DOCS}
    return dr.guard_texts(items, day0, dr.input_paths())


def write_part(name: str, obj: Mapping[str, Any], fp: Mapping[str, str]) -> str:
    """Save a part made with the inputs `fp` (the fingerprint at import), refusing when the inputs changed since."""
    if fingerprint() != dict(fp):
        raise SystemExit(f"refusing to save {name}: the inputs changed during the run (re-run it)")
    js = json.dumps({**obj, "fingerprint": dict(fp)}, indent=1, ensure_ascii=False) + "\n"
    dr.assert_clean(js, _guard())
    PARTS.mkdir(parents=True, exist_ok=True)
    p = PARTS / f"{name}.json"
    p.write_text(js, encoding="utf-8")
    return sha256_bytes(p.read_bytes())


def report() -> dict:
    parts = {n: json.loads((PARTS / f"{n}.json").read_text(encoding="utf-8")) for n in ("replay", "dryrun", "lines", "items")}
    fp = fingerprint()
    check_parts(parts, fp)
    mod = Path(t1.__file__).resolve()
    fork = FORK / "scripts" / "stage3" / "stage3_t1.py"
    res = {
        "version": VERSION, "brief": "27 v3", "written": datetime.now().astimezone().isoformat(timespec="seconds"),
        "module": {"path": "work/checks/stage3_t1.py",
                   "before": {"sha256": PRE_SHA256, "fork_commit": PRE_COMMIT, "inserter_class_sha256": PRE_CLASS_SHA256},
                   "after": {"sha256": sha256_bytes(mod.read_bytes()), "fork_copy_identical": fork.exists() and fork.read_bytes() == mod.read_bytes(),
                             "inserter_class_sha256": class_sha256(t1.Inserter), "inserter_class_unchanged": class_sha256(t1.Inserter) == PRE_CLASS_SHA256,
                             "partsinserter_class_sha256": class_sha256(t1.PartSInserter), "plantresult_class_sha256": class_sha256(t1.PlantResult),
                             "validdraws_class_sha256": class_sha256(t1.ValidDraws)},
                   "diff": module_diff()},
        "valid_draws_file": {"path": str(B26_JSON.relative_to(PROJECT)), "sha256": sha256_bytes(B26_JSON.read_bytes()),
                             "keys": "items[].draws.valid_draws (pairs; valid_by_day checked as per-day counts), items[].lone_lines[i].valid_draws"},
        "fingerprint": fp, "run_seed": RUN_SEED, "runs_per_draw": RUNS_PER_DRAW,
        "parts_sha256": {n: sha256_bytes((PARTS / f"{n}.json").read_bytes()) for n in parts},
        "replay": parts["replay"], "dryrun": parts["dryrun"],
        "lines": {k: v for k, v in parts["lines"].items() if k != "per_line"},
        "items": {k: v for k, v in parts["items"].items() if k != "per_item"},
        "script": {"path": "work/checks/stage3_b3_lone_line_check.py", "sha256": sha256_bytes(Path(__file__).resolve().read_bytes())},
    }
    js = json.dumps(res, indent=1, ensure_ascii=False) + "\n"
    dr.assert_clean(js, _guard())
    OUT.write_text(js, encoding="utf-8")
    return {"json": sha256_bytes(OUT.read_bytes())}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 27: the T1 v3 replay and brief 26's check through the new arm")
    ap.add_argument("mode", choices=("replay", "dryrun", "lines", "items", "report"))
    ap.add_argument("--out-dir", default=str(PARTS / "dryrun"))
    ap.add_argument("--procs", type=int, default=12)
    ns = ap.parse_args(argv)
    if fingerprint() != FINGERPRINT_AT_IMPORT:
        raise SystemExit("refusing: the inputs changed after this process loaded them")
    if ns.mode == "replay":
        out = replay()
        out["module_diff"] = module_diff()
    elif ns.mode == "dryrun":
        out = dryrun(Path(ns.out_dir), ns.procs)
    elif ns.mode == "lines":
        out = lines(ns.procs)
    elif ns.mode == "items":
        out = items_check(ns.procs)
    else:
        print(json.dumps(report(), indent=1))
        return 0
    h = write_part(ns.mode, out, FINGERPRINT_AT_IMPORT)
    print(json.dumps({k: v for k, v in out.items() if k not in ("per_line", "per_item", "variants", "module_lines_new", "module_finding_lines", "sections_equal", "module_diff")}
                     | {"sha256": h}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
