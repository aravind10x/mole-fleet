#!/usr/bin/env python3
"""Line P2, block H (`P2/preregistration-v1.md` section 3; amended by `preregistration-v1.1.md` section D, ab171917):
the draws with their tasks for the runner, and the join. Counts and rates only; no sentence.

* Tasks: each draw of `draw-H-v1.json` with its bank task's offline text (`text_offline`) and expected action tool;
  the slot is the payload's.
* Joint table (descriptive), for each arm: need class (needs, may_touch, no; the draw's actual class for its payload)
  by access (content returned before the run's last action; before the end for a run with no action) by carry
  (red's `evaluate_any`; unresolved runs their own class). Equal weight per draw: a draw's runs (one per follower)
  share its weight. Intervals resample payloads, taking all of a payload's draws and both followers together
  (2,000 replicates, numpy seed 20261114).
* The same by stratum; access at the first firing action where the scorer fires; clean-arm firings listed by pair.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_ft_join as fj  # noqa: E402

SEED = 20261114
N_BOOT = 2000
NEED = ("needs", "may_touch", "no")
ACCESS = ("access", "no_access")
CARRY = ("carried", "not_carried", "unresolved")


def draws_with_tasks(draw: Mapping, bank: Sequence[Mapping]) -> list[dict]:
    by = {b["task_id"]: b for b in bank}
    out = []
    for d in draw["draws"]:
        b = by[d["task_id"]]
        out.append({"draw_id": d["draw_id"], "payload_id": d["payload_id"], "stratum": d["stratum"], "need_class": d["need_class"],
                    "task": {"task_id": d["task_id"], "task_text": b["text_offline"], "slot_id": d["slot_id"],
                             "action_tool": b["expected_action_tool"]}})
    return out


def _cell(r: Mapping) -> str:
    carry = "unresolved" if r.get("predicate_result") is None else "carried" if r["predicate_result"] else "not_carried"
    acc = "access" if r.get("access_last_action") else "no_access"
    return f"{r['need_class']}|{acc}|{carry}"


def _draw_shares(runs: Sequence[Mapping], keyf) -> dict[str, dict[str, float]]:
    """{draw_id: {key: share of the draw's runs}} (equal weight per draw)."""
    by: dict[str, list] = defaultdict(list)
    for r in runs:
        by[r["draw_id"]].append(keyf(r))
    return {d: {k: n / len(ks) for k, n in Counter(ks).items()} for d, ks in by.items()}


def _boot_shares(per_draw: Mapping[str, Mapping[str, float]], draw_payload: Mapping[str, str], keys: Sequence[str],
                 n_boot: int, seed: int) -> dict[str, dict]:
    draws = sorted(per_draw)
    pay = sorted({draw_payload[d] for d in draws})
    of = {p: [i for i, d in enumerate(draws) if draw_payload[d] == p] for p in pay}
    mat = np.array([[per_draw[d].get(k, 0.0) for k in keys] for d in draws])
    point = mat.mean(axis=0)
    rng = np.random.default_rng(seed)
    reps = np.empty((n_boot, len(keys)))
    for b in range(n_boot):
        idx = np.concatenate([of[pay[i]] for i in rng.integers(0, len(pay), len(pay))])
        reps[b] = mat[idx].mean(axis=0)
    return {k: {"share": round(float(point[j]), 6), "lo": round(float(np.percentile(reps[:, j], 2.5)), 6),
                "hi": round(float(np.percentile(reps[:, j], 97.5)), 6)} for j, k in enumerate(keys)}


def joint_table(outs: Sequence[Mapping], *, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    latest = fj.latest_by_run(outs)
    keys = [f"{n}|{a}|{c}" for n in NEED for a in ACCESS for c in CARRY]
    res: dict[str, Any] = {"label": "descriptive; equal weight per draw; intervals resample payloads (all their draws and both followers)"}
    for arm in ("planted", "clean"):
        rs = [r for r in latest if r["arm"] == arm]
        if not rs:
            continue
        dp = {r["draw_id"]: r["payload_id"] for r in rs}
        cells = _boot_shares(_draw_shares(rs, _cell), dp, keys, n_boot, seed)
        cnt = Counter(_cell(r) for r in rs)
        for k in keys:
            cells[k]["n_runs"] = cnt.get(k, 0)
        res[arm] = {"n_runs": len(rs), "n_draws": len(dp), "n_payloads": len(set(dp.values())), "cells": cells}
    return res


def _rate_boot(rs: Sequence[Mapping], pred, n_boot: int, seed: int) -> dict:
    if not rs:
        return {"point": None, "lo": None, "hi": None, "n_runs": 0}
    dp = {r["draw_id"]: r["payload_id"] for r in rs}
    sh = _boot_shares(_draw_shares(rs, lambda r: "yes" if pred(r) else "no"), dp, ["yes"], n_boot, seed)["yes"]
    return {"point": sh["share"], "lo": sh["lo"], "hi": sh["hi"], "n_runs": len(rs)}


def analyse_H(outs: Sequence[Mapping], *, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    latest = fj.latest_by_run(outs)
    by_stratum = {}
    for s in sorted({r["stratum"] for r in latest}):
        by_stratum[s] = {}
        for arm in ("planted", "clean"):
            rs = [r for r in latest if r["stratum"] == s and r["arm"] == arm]
            by_stratum[s][arm] = {"carry": _rate_boot([r for r in rs if r.get("predicate_result") is not None],
                                                      lambda r: r["predicate_result"] is True, n_boot, seed),
                                  "access": _rate_boot(rs, lambda r: bool(r.get("access_last_action")), n_boot, seed),
                                  "unresolved": sum(1 for r in rs if r.get("predicate_result") is None)}
    fired: dict[str, list] = defaultdict(list)
    for r in latest:
        if r["arm"] == "clean" and r.get("predicate_result") is True:
            fired[r["draw_id"]].append(r)
    clean_firings = [{"draw_id": d, "payload_id": rs[0]["payload_id"], "task_id": rs[0].get("task_id"),
                      "followers": sorted(r["follower"] for r in rs)} for d, rs in sorted(fired.items())]
    first = {}
    for arm in ("planted", "clean"):
        f = [r for r in latest if r["arm"] == arm and r.get("predicate_result") is True]
        first[arm] = {"n_fired": len(f), "access_at_first_firing": sum(1 for r in f if r.get("access_first_firing") is True),
                      "no_access_at_first_firing": sum(1 for r in f if r.get("access_first_firing") is False),
                      "unknown": sum(1 for r in f if r.get("access_first_firing") is None)}
    return {"joint": joint_table(latest, n_boot=n_boot, seed=seed), "by_stratum": by_stratum, "clean_firings": clean_firings,
            "access_at_first_firing": first,
            "need_class_counts": dict(Counter(r["need_class"] for r in latest if r["arm"] == "planted")),
            "label": "H: no sentence; an instance for this bank, these states and the runnable 0.438 of arrival weight; descriptive"}


def main(argv: list[str] | None = None) -> int:
    import argparse
    P2 = HERE.parent / "stage3" / "v5" / "P2"
    ap = argparse.ArgumentParser(description="P2 block H: draws with tasks, or the join (counts and rates only).")
    ap.add_argument("mode", choices=("tasks", "join"))
    ap.add_argument("--draws", type=Path, default=P2 / "draw-H-v1.json")
    ap.add_argument("--bank", type=Path, default=P2 / "blue" / "bank-tasks-v0.jsonl")
    ap.add_argument("--outcomes", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    a = ap.parse_args(argv)
    if a.out.exists():
        raise SystemExit(f"{a.out} exists; never overwritten")
    if a.mode == "tasks":
        bank = [json.loads(x) for x in a.bank.read_text(encoding="utf-8").splitlines() if x.strip()]
        out = draws_with_tasks(json.loads(a.draws.read_text(encoding="utf-8")), bank)
        a.out.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"draws": len(out), "payloads": len({d["payload_id"] for d in out}),
                          "tools": dict(Counter(d["task"]["action_tool"] for d in out))}))
        return 0
    rows = [json.loads(x) for x in a.outcomes.read_text(encoding="utf-8").splitlines() if x.strip()]
    res = analyse_H(rows, n_boot=a.n_boot)
    a.out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"need_class_counts": res["need_class_counts"], "clean_firings": len(res["clean_firings"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
