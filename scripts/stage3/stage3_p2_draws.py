#!/usr/bin/env python3
"""Line P2, step 2.2 (`P2/brief-harness.md`; design `P2/preregistration-v1.md` section 3, 19d4a7d5): the D and H draws,
ids only, and the exact need table. Blue side; reads blue's goals, bank, need matrix and slots, the core manifest's ids,
regimes and slot ids, and the payloads' frozen CLEAN documents by script (to check that a needed slot exists); prints
counts.

* D: `random.Random(20261114)`; for payload ids in sorted order, `randrange(3)` picks among the three goals of the
  payload's slot (the slot of its core task), goals in file order.
* Eligibility (H): a task is eligible for a payload only if every slot it needs exists in that payload's clean documents
  (blue's own parser, `stage3_ft_slots.parse_state`, on the frozen clean text); a task that needs nothing is eligible.
* Need table (exact): per payload slot, the arrival weight of the runnable tasks that need it and of those that may touch
  it without needing it, as shares of all weight and of runnable weight, before and after eligibility; means over the
  payloads and by regime; how many payloads have an empty stratum.
* H: payloads in sorted order, one `random.Random(20261114)` stream; per payload, tasks sorted by id,
  `choices(..., weights=arrival weights)` with replacement: 2 from the eligible tasks that need the slot, 1 from those
  that may touch it and do not need it, the rest up to 4 from all eligible runnable tasks; an empty stratum's draws go
  to the last.

v1 (`P2/preregistration-v1.1.md` sections A and D, ab171917; `python stage3_p2_draws.py v1`): the 54 payloads red's
validity table keeps (8f6538b0); D by the same rule on them; need at each payload's clean state by blue's
`stage3_ft_bank.need_at_state` (398e2e09), called rule-defined need shares; H drawn exactly as section D (any = all
runnable tasks; each draw its own id and its actual need class). Writes `draw-D-v1.json`, `draw-H-v1.json`,
`need-table-v1.json`; v0 files are kept.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

SEED = 20261114
H_COUNTS = (("need", 2), ("may_touch", 1), ("all", 1))
PROJECT = HERE.parent.parent
P2 = PROJECT / "work" / "stage3" / "v5" / "P2"


def slot_exists(text: str, locator: str) -> bool:
    import stage3_ft_slots as sl
    parts = str(locator).split(" :: ")
    section_key, selector = " :: ".join(parts[1:-1]), parts[-1]
    if selector == "section":
        return section_key in sl._sections_of(text)
    return any(it["section_key"] == section_key and it["selector"] == selector for it in sl.parse_state(text))


def clean_docs(docs_root: Path, payload_id: str) -> dict[str, str]:
    import stage3_ft_harness as h
    return dict(h.Workspace(Path(docs_root) / payload_id / "clean").docs)


def eligible(task_entry: Mapping, slots: Mapping[str, Mapping], clean: Mapping[str, str]) -> bool:
    for s in task_entry.get("needs") or []:
        sl_ = slots[s]
        text = clean.get(sl_["document"])
        if text is None or not slot_exists(text, sl_["locator"]):
            return False
    return True


def _scorable(manifest: Sequence[Mapping]) -> list[Mapping]:
    return sorted([m for m in manifest if m.get("scorable", True)], key=lambda m: m["payload_id"])


def draw_D(manifest: Sequence[Mapping], goals: Sequence[Mapping]) -> dict:
    by_slot: dict[str, list[Mapping]] = {}
    for g in goals:                                              # file order
        by_slot.setdefault(g["slot_id"], []).append(g)
    rng = random.Random(SEED)
    out = []
    for m in _scorable(manifest):
        gs = by_slot[m["slot_id"]]
        if len(gs) != 3:
            raise ValueError(f"{m['payload_id']}: slot has {len(gs)} goals, not 3")
        i = rng.randrange(3)
        out.append({"payload_id": m["payload_id"], "slot_id": m["slot_id"], "goal_id": gs[i]["goal_id"], "goal_index": i,
                    "action_tool": gs[i]["action_tool"]})
    return {"rule": "random.Random(20261114); payloads sorted; randrange(3) over the slot's three goals in file order",
            "seed": SEED, "n": len(out), "draws": out}


def _populations(m: Mapping, matrix: Mapping, bank: Sequence[Mapping], slots: Mapping, docs_root: Path) -> dict:
    s = m["slot_id"]
    runnable = sorted([b for b in bank if b.get("runnable")], key=lambda b: b["task_id"])
    clean = clean_docs(docs_root, m["payload_id"])
    tasks = matrix["tasks"]
    ok = {b["task_id"]: eligible(tasks[b["task_id"]], slots, clean) for b in runnable}
    need = [b for b in runnable if s in (tasks[b["task_id"]].get("needs") or [])]
    may = [b for b in runnable if s in (tasks[b["task_id"]].get("may_touch") or []) and s not in (tasks[b["task_id"]].get("needs") or [])]
    return {"need": need, "may_touch": may, "all": runnable, "ok": ok}


def need_table(manifest: Sequence[Mapping], matrix: Mapping, bank: Sequence[Mapping], slots: Mapping, docs_root: Path) -> dict:
    all_w = sum(float(b["weight"]) for b in bank)
    run_w = sum(float(b["weight"]) for b in bank if b.get("runnable"))
    rows = {}
    for m in _scorable(manifest):
        pop = _populations(m, matrix, bank, slots, docs_root)
        w = lambda xs: sum(float(b["weight"]) for b in xs)  # noqa: E731
        el = lambda xs: [b for b in xs if pop["ok"][b["task_id"]]]  # noqa: E731
        rows[m["payload_id"]] = {"regime": m.get("regime"), "slot_id": m["slot_id"],
                                 "n_need": len(pop["need"]), "n_may_touch": len(pop["may_touch"]),
                                 "n_need_eligible": len(el(pop["need"])), "n_may_touch_eligible": len(el(pop["may_touch"])),
                                 "need_weight_share_all": w(pop["need"]) / all_w, "need_weight_share_runnable": w(pop["need"]) / run_w,
                                 "may_touch_weight_share_all": w(pop["may_touch"]) / all_w,
                                 "may_touch_weight_share_runnable": w(pop["may_touch"]) / run_w,
                                 "need_eligible_weight_share_all": w(el(pop["need"])) / all_w,
                                 "may_touch_eligible_weight_share_all": w(el(pop["may_touch"])) / all_w}
    keys = [k for k in next(iter(rows.values())) if k.endswith(("_all", "_runnable"))]
    mean = lambda rs: {k: (sum(r[k] for r in rs) / len(rs) if rs else None) for k in keys}  # noqa: E731
    return {"weights": {"all": all_w, "runnable": run_w}, "payloads": rows, "mean": mean(list(rows.values())),
            "by_regime": {g: mean([r for r in rows.values() if r["regime"] == g]) for g in ("routine", "middle", "alarming")},
            "n_empty": {"need": sum(1 for r in rows.values() if r["n_need"] == 0),
                        "may_touch": sum(1 for r in rows.values() if r["n_may_touch"] == 0),
                        "need_eligible": sum(1 for r in rows.values() if r["n_need_eligible"] == 0),
                        "may_touch_eligible": sum(1 for r in rows.values() if r["n_may_touch_eligible"] == 0)}}


def draw_H(manifest: Sequence[Mapping], matrix: Mapping, bank: Sequence[Mapping], slots: Mapping, docs_root: Path) -> dict:
    rng = random.Random(SEED)
    out = []
    for m in _scorable(manifest):
        pop = _populations(m, matrix, bank, slots, docs_root)
        carry = 0
        strata = [(name, k, [b for b in pop[name] if pop["ok"][b["task_id"]]]) for name, k in H_COUNTS]
        for j, (name, k, xs) in enumerate(strata):
            k = k + (carry if j == len(strata) - 1 else 0)
            if not xs:
                carry += k
                continue
            for t in rng.choices(xs, weights=[float(b["weight"]) for b in xs], k=k):
                out.append({"payload_id": m["payload_id"], "slot_id": m["slot_id"], "stratum": name, "task_id": t["task_id"]})
    return {"rule": "random.Random(20261114); payloads sorted; tasks sorted by id; choices with arrival weights, with replacement; "
                    "2 need, 1 may_touch, rest up to 4 from all runnable; eligible tasks only; an empty stratum's draws go to the last",
            "seed": SEED, "n": len(out), "draws": out}


# ── v1 (preregistration-v1.1 sections A and D, ab171917) ──────────────────────────────────────────

def retained(manifest: Sequence[Mapping], validity: Sequence[Mapping]) -> list[Mapping]:
    """The scorable payloads the red side's validity table keeps (section A), sorted by id."""
    ok = {v["payload_id"]: bool(v["valid"]) for v in validity}
    sc = _scorable(manifest)
    missing = [m["payload_id"] for m in sc if m["payload_id"] not in ok]
    if missing:
        raise ValueError(f"payloads missing from the validity table: {missing}")
    return [m for m in sc if ok[m["payload_id"]]]


def _need_fn():
    import stage3_ft_bank as fb
    return fb.need_at_state


def populations_at_state(m: Mapping, bank: Sequence[Mapping], slots: Mapping[str, Mapping], docs_root: Path, *,
                         need_fn=None) -> dict:
    """Section D: blue's class rule on the payload's clean state alone (`need_at_state`). need = runnable tasks that
    need the payload's slot there; may_touch = those that may touch it and do not need it; any = all runnable tasks.
    Each list sorted by task id; `cls` gives every runnable task's actual class for this payload."""
    need_fn = need_fn or _need_fn()
    s = m["slot_id"]
    doc = slots[s]["document"]
    of_doc = [x for x in slots.values() if x["document"] == doc]
    text = clean_docs(docs_root, m["payload_id"]).get(doc, "")
    runnable = sorted([b for b in bank if b.get("runnable")], key=lambda b: b["task_id"])
    cls = {}
    for b in runnable:
        n = need_fn(b, of_doc, text)
        cls[b["task_id"]] = "needs" if s in n["needs"] else "may_touch" if s in n["may_touch"] else "no"
    return {"need": [b for b in runnable if cls[b["task_id"]] == "needs"],
            "may_touch": [b for b in runnable if cls[b["task_id"]] == "may_touch"], "any": runnable, "cls": cls}


H_COUNTS_V1 = (("need", 2), ("may_touch", 1), ("any", 1))


def draw_H_v1(kept: Sequence[Mapping], bank: Sequence[Mapping], slots: Mapping, docs_root: Path, *, need_fn=None) -> dict:
    rng = random.Random(SEED)                                       # one generator, created once
    out = []
    for m in sorted(kept, key=lambda m: m["payload_id"]):
        pop = populations_at_state(m, bank, slots, docs_root, need_fn=need_fn)
        carry = 0
        for name, k in H_COUNTS_V1:
            k = k + (carry if name == "any" else 0)
            xs = pop[name]
            if not xs:
                carry += k
                continue
            for t in rng.choices(xs, weights=[float(b["weight"]) for b in xs], k=k):
                out.append({"draw_id": f"H{len(out) + 1:04d}", "payload_id": m["payload_id"], "slot_id": m["slot_id"],
                            "stratum": name, "task_id": t["task_id"], "need_class": pop["cls"][t["task_id"]]})
    return {"rule": "preregistration-v1.1 section D: random.Random(20261114) created once; payloads sorted; strata need, "
                    "may_touch, any; tasks sorted by id; choices with arrival weights, k = 2, 1, rest to 4; an empty stratum's "
                    "draws pass to any (all runnable tasks); need at the payload's clean state (need_at_state)",
            "seed": SEED, "n": len(out), "draws": out}


def need_table_v1(kept: Sequence[Mapping], bank: Sequence[Mapping], slots: Mapping, docs_root: Path, *, need_fn=None) -> dict:
    """Rule-defined need shares (section D) on the retained payloads."""
    all_w = sum(float(b["weight"]) for b in bank)
    run_w = sum(float(b["weight"]) for b in bank if b.get("runnable"))
    w = lambda xs: sum(float(b["weight"]) for b in xs)  # noqa: E731
    rows = {}
    for m in kept:
        pop = populations_at_state(m, bank, slots, docs_root, need_fn=need_fn)
        rows[m["payload_id"]] = {"regime": m.get("regime"), "slot_id": m["slot_id"], "n_need": len(pop["need"]),
                                 "n_may_touch": len(pop["may_touch"]),
                                 "need_weight_share_all": w(pop["need"]) / all_w, "need_weight_share_runnable": w(pop["need"]) / run_w,
                                 "may_touch_weight_share_all": w(pop["may_touch"]) / all_w,
                                 "may_touch_weight_share_runnable": w(pop["may_touch"]) / run_w}
    keys = [k for k in next(iter(rows.values())) if k.endswith(("_all", "_runnable"))]
    mean = lambda rs: {k: (sum(r[k] for r in rs) / len(rs) if rs else None) for k in keys}  # noqa: E731
    return {"label": "rule-defined need shares (need_at_state on each payload's clean state)", "n_payloads": len(rows),
            "weights": {"all": all_w, "runnable": run_w}, "payloads": rows, "mean": mean(list(rows.values())),
            "by_regime": {g: mean([r for r in rows.values() if r["regime"] == g]) for g in ("routine", "middle", "alarming")},
            "n_empty": {"need": sum(1 for r in rows.values() if r["n_need"] == 0),
                        "may_touch": sum(1 for r in rows.values() if r["n_may_touch"] == 0)}}


def task_map_D(draw: Mapping, goals: Sequence[Mapping]) -> dict[str, dict]:
    """The runner's task map for D: each payload's drawn goal as its task (the goal's text is the task text)."""
    by = {g["goal_id"]: g for g in goals}
    out = {}
    for x in draw["draws"]:
        g = by[x["goal_id"]]
        out[x["payload_id"]] = {"task_id": g["goal_id"], "task_text": g["goal_text"], "slot_id": g["slot_id"],
                                "action_tool": g["action_tool"], "source": "goals-v0", "goal_index": x["goal_index"]}
    return out


def main_v1(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P2 v1 draws and need table on the retained payloads (ids and counts only).")
    ap.add_argument("--manifest", type=Path, default=PROJECT / "work" / "stage3" / "red" / "ft" / "cells-manifest.json")
    ap.add_argument("--docs-root", type=Path, default=PROJECT / "work" / "stage3" / "red" / "ft" / "docs")
    ap.add_argument("--validity", type=Path, default=P2 / "red-scorer-validity-v0.json")
    ap.add_argument("--goals", type=Path, default=P2 / "blue" / "goals-v0.jsonl")
    ap.add_argument("--bank", type=Path, default=P2 / "blue" / "bank-tasks-v0.jsonl")
    ap.add_argument("--slots", type=Path, default=PROJECT / "work" / "stage3" / "v5" / "FT" / "blue" / "slots-v0.json")
    a = ap.parse_args(argv)
    outs = {n: P2 / f"{n}-v1.json" for n in ("draw-D", "draw-H", "need-table")}
    for q in outs.values():
        if q.exists():
            raise SystemExit(f"{q} exists; never overwritten")
    import stage3_ft_run as fr
    kept = retained(fr.load_manifest(a.manifest), json.loads(a.validity.read_text(encoding="utf-8")))
    goals = [json.loads(x) for x in a.goals.read_text(encoding="utf-8").splitlines() if x.strip()]
    bank = [json.loads(x) for x in a.bank.read_text(encoding="utf-8").splitlines() if x.strip()]
    slots = {x["slot_id"]: x for x in json.loads(a.slots.read_text(encoding="utf-8"))}
    d, t, hh = draw_D(kept, goals), need_table_v1(kept, bank, slots, a.docs_root), draw_H_v1(kept, bank, slots, a.docs_root)
    for name, obj in (("draw-D", d), ("need-table", t), ("draw-H", hh)):
        outs[name].write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")
    from collections import Counter
    print(json.dumps({"retained": len(kept), "by_regime": dict(Counter(m["regime"] for m in kept)),
                      "D": {"n": d["n"], "goal_index": dict(Counter(x["goal_index"] for x in d["draws"]))},
                      "need_table": {"mean": t["mean"], "by_regime": t["by_regime"], "n_empty": t["n_empty"]},
                      "H": {"n": hh["n"], "by_stratum": dict(Counter(x["stratum"] for x in hh["draws"])),
                            "by_need_class": dict(Counter(x["need_class"] for x in hh["draws"])),
                            "distinct_tasks": len({x["task_id"] for x in hh["draws"]})}}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="P2 draws and need table (ids and counts only).")
    ap.add_argument("--manifest", type=Path, default=PROJECT / "work" / "stage3" / "red" / "ft" / "cells-manifest.json")
    ap.add_argument("--docs-root", type=Path, default=PROJECT / "work" / "stage3" / "red" / "ft" / "docs")
    ap.add_argument("--goals", type=Path, default=P2 / "blue" / "goals-v0.jsonl")
    ap.add_argument("--bank", type=Path, default=P2 / "blue" / "bank-tasks-v0.jsonl")
    ap.add_argument("--matrix", type=Path, default=P2 / "blue" / "need-matrix-v0.json")
    ap.add_argument("--slots", type=Path, default=PROJECT / "work" / "stage3" / "v5" / "FT" / "blue" / "slots-v0.json")
    a = ap.parse_args(argv)
    outs = {n: P2 / f"{n}-v0.json" for n in ("draw-D", "draw-H", "need-table")}
    for p in outs.values():
        if p.exists():
            raise SystemExit(f"{p} exists; never overwritten")
    import stage3_ft_run as fr
    manifest = fr.load_manifest(a.manifest)
    goals = [json.loads(x) for x in a.goals.read_text(encoding="utf-8").splitlines() if x.strip()]
    bank = [json.loads(x) for x in a.bank.read_text(encoding="utf-8").splitlines() if x.strip()]
    matrix = json.loads(a.matrix.read_text(encoding="utf-8"))
    slots = {s["slot_id"]: s for s in json.loads(a.slots.read_text(encoding="utf-8"))}
    d, t, hh = draw_D(manifest, goals), need_table(manifest, matrix, bank, slots, a.docs_root), draw_H(manifest, matrix, bank, slots, a.docs_root)
    for name, obj in (("draw-D", d), ("need-table", t), ("draw-H", hh)):
        outs[name].write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")
    from collections import Counter
    print(json.dumps({"D": {"n": d["n"], "goal_index": dict(Counter(x["goal_index"] for x in d["draws"]))},
                      "need_table": {"mean": t["mean"], "by_regime": t["by_regime"], "n_empty": t["n_empty"]},
                      "H": {"n": hh["n"], "by_stratum": dict(Counter(x["stratum"] for x in hh["draws"])),
                            "distinct_tasks": len({x["task_id"] for x in hh["draws"]})}}, indent=1))
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "task-map-D":
        out = P2 / "tasks-D-v1.json"
        if out.exists():
            raise SystemExit(f"{out} exists; never overwritten")
        gl = [json.loads(x) for x in (P2 / "blue" / "goals-v0.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        tm = task_map_D(json.loads((P2 / "draw-D-v1.json").read_text(encoding="utf-8")), gl)
        out.write_text(json.dumps(tm, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"payloads": len(tm), "distinct_goals": len({t["task_id"] for t in tm.values()})}))
        raise SystemExit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "v1":
        raise SystemExit(main_v1(sys.argv[2:]))
    raise SystemExit(main())
