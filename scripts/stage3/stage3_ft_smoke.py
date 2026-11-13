#!/usr/bin/env python3
"""Line FT, part H2: the smoke's cells. Blue side; honest content only (the honest prefix prefix_rw_v2c),
nothing planted. Prints counts and ids.

* Workspace: every class document at its final honest state (blue's replay, `stage3_ft_slots`' state
  indices: 0 = day-0 seed, then one per successful content write, log order), written in red's frozen
  format: flat files plus history.json {"as_of", "paths": {file: world path}, "revisions": {file:
  [{rev, account, ts, op, lines_added, lines_removed}]}}; op is write / append_to / replace from the
  corpus action; lines are difflib's changed lines with 1-based line numbers. One workspace serves
  every smoke cell (the `clean` arm).
* Draw (seeded, default seed 20261113, n 20): tasks whose slot exists in its document's final state;
  documents are visited round-robin in a seeded order; at each visit the document's next task is one
  whose action tool has been drawn least so far (ties by a seeded shuffle), so documents and action
  tools both spread evenly. The same cells run for every follower.

`python -I stage3_ft_smoke.py` writes work/stage3/v5/FT/smoke/ (workspace, manifest) and refuses to overwrite.
"""
from __future__ import annotations

import argparse
import difflib
import json
import random
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

PROJECT = HERE.parent.parent
FT_DIR = PROJECT / "work" / "stage3" / "v5" / "FT"
SMOKE_DIR = FT_DIR / "smoke"
SEED = 20261113


@dataclass(frozen=True)
class State:
    index: int
    ts: str
    account: str | None
    action: str | None
    text: str


def load_states() -> dict[str, list[State]]:
    """As stage3_ft_slots.load_honest_states, keeping each write's account and action."""
    import stage3_ft_slots as sl
    import stage3_views as sv
    rows = sv.read_jsonl(Path(sl.CORPUS))
    base = sv.seed_base()
    out: dict[str, list[State]] = {}
    for p in sv.class_doc_paths():
        lst = [State(0, "seed", None, None, base[("owncloud", p)])]
        for ch in sv.document_timeline(rows, p, base):
            if ch.after is not None:
                lst.append(State(len(lst), str(ch.ts), ch.account, ch.action, ch.after))
        out[p] = lst
    return out


def _op(action: str | None) -> str:
    a = (action or "").lower()
    return "append_to" if "append" in a else "write" if "write" in a else "replace"


def _diff(before: str, after: str) -> tuple[list[dict], list[dict]]:
    a, b = before.splitlines(), after.splitlines()
    added, removed = [], []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag in ("replace", "delete"):
            removed += [{"line_no": i + 1, "text": a[i]} for i in range(i1, i2)]
        if tag in ("replace", "insert"):
            added += [{"line_no": j + 1, "text": b[j]} for j in range(j1, j2)]
    return added, removed


def write_workspace(states: Mapping[str, Sequence[State]], root: Path) -> Path:
    root = Path(root)
    if root.exists():
        raise SystemExit(f"{root} exists; never overwritten")
    root.mkdir(parents=True)
    paths, revisions, last_ts = {}, {}, []
    for doc, lst in states.items():
        fname = doc.rsplit("/", 1)[-1]
        if fname in paths:
            raise ValueError(f"two class documents share the file name {fname}")
        paths[fname] = doc
        (root / fname).write_text(lst[-1].text, encoding="utf-8")
        revs = []
        for prev, cur in zip(lst, lst[1:]):
            added, removed = _diff(prev.text, cur.text)
            revs.append({"rev": cur.index, "account": cur.account, "ts": cur.ts, "op": _op(cur.action),
                         "lines_added": added, "lines_removed": removed})
            last_ts.append(cur.ts)
        revisions[fname] = revs
    hist = {"as_of": max(last_ts) if last_ts else "seed", "paths": paths, "revisions": revisions}
    (root / "history.json").write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    return root


def draw_tasks(states: Mapping[str, Sequence[State]], slots: Sequence[Mapping], tasks: Sequence[Mapping], *,
               n: int = 20, seed: int = SEED) -> list[dict]:
    rng = random.Random(seed)
    final = {d: lst[-1].index for d, lst in states.items()}
    slot_of = {s["slot_id"]: s for s in slots}
    by_doc: dict[str, list[dict]] = {}
    for t in sorted(tasks, key=lambda t: t["task_id"]):
        s = slot_of.get(t["slot_id"])
        if s and s["document"] in final and final[s["document"]] in s["honest_states"]:
            by_doc.setdefault(s["document"], []).append(dict(t))
    for lst in by_doc.values():
        rng.shuffle(lst)
    docs = sorted(by_doc)
    rng.shuffle(docs)
    used: Counter = Counter()
    out: list[dict] = []
    while len(out) < n and any(by_doc[d] for d in docs):
        for d in docs:
            if len(out) >= n or not by_doc[d]:
                continue
            pick = min(by_doc[d], key=lambda t: used[t["action_tool"]])   # first of the least used (list is shuffled)
            by_doc[d].remove(pick)
            used[pick["action_tool"]] += 1
            out.append(pick)
    return out


def manifest(drawn: Sequence[Mapping], slots: Sequence[Mapping], workspace: Path) -> list[dict]:
    slot_of = {s["slot_id"]: s for s in slots}
    return [{"payload_id": f"S{i:02d}", "regime": None, "task_id": t["task_id"], "slot_id": t["slot_id"],
             "document": slot_of[t["slot_id"]]["document"], "action_tool": t["action_tool"], "predicate_id": None,
             "scorable": True, "operational_value": slot_of[t["slot_id"]]["slot_kind"] == "operational_value",
             "workspaces": {"clean": str(workspace)}} for i, t in enumerate(drawn, 1)]


def summarise(rows: Sequence[Mapping], *, concurrency: int) -> dict:
    """Per follower: runs, cost (mean, 90th percentile, total), turns, wall-clock, sustainable runs per hour
    at `concurrency`, the share ending in a substantive action tool, each check tool's base rate (share of
    runs calling it), end reasons and error classes. Counts only."""
    import numpy as np
    out = {}
    for fol in sorted({r["follower"] for r in rows}):
        rs = [r for r in rows if r["follower"] == fol]
        n = len(rs)
        cost = [float(r["cost_usd"]) for r in rs]
        wall = [float(r["wall_s"]) for r in rs]
        out[fol] = {"n_runs": n, "cost_mean": round(sum(cost) / n, 6), "cost_p90": round(float(np.percentile(cost, 90)), 6),
                    "cost_total": round(sum(cost), 6), "turns_mean": round(sum(r["n_turns"] for r in rs) / n, 2),
                    "turns_max": max(r["n_turns"] for r in rs), "wall_mean_s": round(sum(wall) / n, 1),
                    "wall_p90_s": round(float(np.percentile(wall, 90)), 1),
                    "runs_per_hour": round(concurrency * 3600 / (sum(wall) / n), 1),
                    "share_ended_in_action": round(sum(bool(r["ended_in_action"]) for r in rs) / n, 4),
                    "share_declined": round(sum(bool(r["declined"]) for r in rs) / n, 4),
                    "check_share": {t: round(sum(r[f"n_{t}"] > 0 for r in rs) / n, 4) for t in ("search_documents", "read_history", "ask_colleague")}
                    | {"any": round(sum(bool(r["checked"]) for r in rs) / n, 4)},
                    "check_calls_mean": {t: round(sum(r[f"n_{t}"] for r in rs) / n, 2) for t in ("search_documents", "read_history", "ask_colleague")},
                    "read_document_mean": round(sum(r.get("n_read_document", 0) for r in rs) / n, 2),
                    "invalid_calls": sum(r.get("n_invalid", 0) for r in rs),
                    "end_reasons": dict(Counter(r["end_reason"] for r in rs)),
                    "errors": dict(Counter(str(r["error"]).split(":")[0] for r in rs if r["error"])),
                    "cost_missing": sum(bool(r.get("cost_missing")) for r in rs)}
    return out


BLOCKS = (("core", 56, 2), ("verification", 32, 1), ("dose", 12, 8))   # (block, payloads, cells per payload)


def run_count_table(per: Mapping[str, Mapping], *, concurrency: int, repeats: Sequence[int] = (1, 2)) -> list[dict]:
    """Runs, dollars (mean per-run cost) and wall-clock hours (followers in parallel, `concurrency` runs at a
    time each) for the pre-registration's blocks: core and verification on both followers; dose on one
    follower (either) or both."""
    rows = []
    for block, n, cells in BLOCKS:
        sets = [("kimi", "sol")] if block != "dose" else [("kimi",), ("sol",), ("kimi", "sol")]
        for r in repeats:
            for fs in sets:
                per_f = n * cells * r
                rows.append({"block": block, "payloads": n, "cells_per_payload": cells, "repeats": r, "followers": "+".join(fs),
                             "runs": per_f * len(fs), "usd": round(sum(per_f * per[f]["cost_mean"] for f in fs), 2),
                             "hours": round(max(per_f * per[f]["wall_mean_s"] for f in fs) / concurrency / 3600, 2)})
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the FT smoke cells (counts only).")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args(argv)
    slots = json.loads((FT_DIR / "blue" / "slots-v0.json").read_text(encoding="utf-8"))
    tasks = [json.loads(x) for x in (FT_DIR / "blue" / "tasks-v0.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    st = load_states()
    ws = write_workspace(st, SMOKE_DIR / "ws-final")
    drawn = draw_tasks(st, slots, tasks, n=a.n, seed=a.seed)
    man = manifest(drawn, slots, ws)
    mp = SMOKE_DIR / "smoke-manifest-v0.json"
    if mp.exists():
        raise SystemExit(f"{mp} exists")
    mp.write_text(json.dumps(man, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"cells": len(man), "by_document": Counter(m["document"] for m in man),
                      "by_action_tool": Counter(m["action_tool"] for m in man),
                      "operational_value": sum(m["operational_value"] for m in man),
                      "states_final": {d: lst[-1].index for d, lst in st.items()}, "task_ids": [m["task_id"] for m in man]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
