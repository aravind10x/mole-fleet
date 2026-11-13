#!/usr/bin/env python3
"""Line P2, block Z (`P2/preregistration-v1.md` section 3, 19d4a7d5): the descriptive estimand over the dose join's
items (`stage3_ft_join.dose_analysis`). Per item, the mean uptake of its eligible (can-fire) partial cells minus its
full triple's uptake; averaged with equal weight over the items that have an eligible cell; 95 percent interval by
resampling items (`random.Random`, seed 20261114 for P2). Counts and rates only."""
from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from typing import Any

SEED = 20261114
N_BOOT = 2000


def estimand(dose: Mapping[str, Any], *, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    per, n_cells, n_none = {}, 0, 0
    for pid, it in sorted(dose["items"].items()):
        cells = [c for c in it["subsets"].values() if c.get("can_fire")]
        vals = [c["uptake"] for c in cells if c.get("uptake") is not None]
        n_none += len(cells) - len(vals)
        full = it["full"]["uptake"]
        if not vals or full is None:
            continue
        n_cells += len(vals)
        per[pid] = round(sum(vals) / len(vals) - full, 6)
    xs = list(per.values())
    point = sum(xs) / len(xs) if xs else None
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(n_boot)) if xs else []
    q = lambda p: boots[min(len(boots) - 1, max(0, int(round(p * (len(boots) - 1)))))] if boots else None  # noqa: E731
    return {"label": "launched by amendment after the core's result; descriptive", "n_items": len(xs), "n_cells": n_cells,
            "n_cells_without_uptake": n_none, "per_item": per, "point": round(point, 6) if point is not None else None,
            "lo": q(0.025), "hi": q(0.975), "boot_mean": sum(boots) / len(boots) if boots else None,
            "n_boot": n_boot, "seed": seed, "resampling": "items, with replacement"}


# ── post hoc table (coordinator ruling, 2026-11-14), after the registered premise failed ────────────────────────────

POSTHOC_LABEL = "post hoc, after the registered premise failed; descriptive"
PARTIAL = tuple(f"subset_{i}" for i in range(1, 7))


def _item_boot(vals: Sequence[float], n_boot: int, seed: int) -> dict:
    xs = [v for v in vals if v is not None]
    if not xs:
        return {"point": None, "lo": None, "hi": None, "n_items": 0}
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(n_boot))
    q = lambda p: boots[min(len(boots) - 1, max(0, int(round(p * (len(boots) - 1)))))]  # noqa: E731
    return {"point": round(sum(xs) / len(xs), 6), "lo": round(q(0.025), 6), "hi": round(q(0.975), 6), "n_items": len(xs)}


def posthoc(dose_outcomes: Sequence[Mapping], dose_manifest: Sequence[Mapping], *, exclude: Sequence[str] = ("D378d17ac",),
            n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """k = how many of the item's literal-bearing statements (manifest `literal_statements`) a partial cell holds, the
    cells' statements being the join's registered SUBSET_STATEMENTS. Uptake is the 50:50 follower mixture of the
    carried share of a cell's runs (unresolved as not carried, and both ways for the contrast). Items in `exclude`
    are shown and left out of every average."""
    import stage3_ft_join as fj
    by: dict[tuple, list] = {}
    for r in fj.latest_by_run(dose_outcomes):
        by.setdefault((r["payload_id"], r["arm"], r["follower"]), []).append(r)

    def u(pid: str, arm: str, mode: str = "low") -> float | None:
        vals = [fj._rate(by.get((pid, arm, f), []), mode) for f in fj.FOLLOWERS]
        return None if any(v is None for v in vals) else 0.5 * vals[0] + 0.5 * vals[1]
    items, by_k_item, contrast = {}, {"0": [], "1": [], "2": []}, {"raw": [], "adverse_smaller": [], "adverse_larger": []}
    full_v, clean_v = [], []
    stray = {"cells": 0, "runs": 0, "fires": 0}
    excluded = {}
    for m in sorted(dose_manifest, key=lambda m: m["payload_id"]):
        pid, lit = m["payload_id"], set(int(x) for x in m["literal_statements"])
        cells = {}
        for arm in PARTIAL:
            k = len(lit & fj.SUBSET_STATEMENTS[arm])
            runs = [r for f in fj.FOLLOWERS for r in by.get((pid, arm, f), [])]
            cells[arm] = {"k": k, "uptake": u(pid, arm), "runs": len(runs), "fires": sum(1 for r in runs if r.get("predicate_result") is True),
                          "unresolved": sum(1 for r in runs if r.get("predicate_result") is None)}
        clean_runs = [r for f in fj.FOLLOWERS for r in by.get((pid, "clean", f), [])]
        clean_fires = sum(1 for r in clean_runs if r.get("predicate_result") is True)
        items[pid] = {"literal_statements": sorted(lit), "full": u(pid, "planted"), "clean": u(pid, "clean"),
                      "clean_fires": f"{clean_fires} of {len(clean_runs)}", "cells": cells}
        if pid in exclude:
            excluded[pid] = f"clean arm fired on {clean_fires} of {len(clean_runs)} runs"
            continue
        full_v.append(items[pid]["full"])
        clean_v.append(items[pid]["clean"])
        for kk in ("0", "1", "2"):
            us = [c["uptake"] for c in cells.values() if c["k"] == int(kk) and c["uptake"] is not None]
            if us:
                by_k_item[kk].append(sum(us) / len(us))
        pos = [a for a, c in cells.items() if c["k"] >= 1]
        if pos:
            def part(mode):
                vs = [u(pid, a, mode) for a in pos]
                return None if any(v is None for v in vs) else sum(vs) / len(vs)
            f_lo, f_hi = u(pid, "planted", "low"), u(pid, "planted", "high")
            contrast["raw"].append(None if f_lo is None or part("low") is None else f_lo - part("low"))
            contrast["adverse_smaller"].append(None if f_lo is None or part("high") is None else f_lo - part("high"))
            contrast["adverse_larger"].append(None if f_hi is None or part("low") is None else f_hi - part("low"))
            items[pid]["contrast"] = round(contrast["raw"][-1], 6) if contrast["raw"][-1] is not None else None
        for c in cells.values():
            if c["k"] == 0:
                stray["cells"] += 1
                stray["runs"] += c["runs"]
                stray["fires"] += c["fires"]
    return {"label": POSTHOC_LABEL, "subset_statements_source": "stage3_ft_join.SUBSET_STATEMENTS (registered in FT v1.3 section 6)",
            "items": items, "excluded": excluded,
            "by_k": {kk: _item_boot(v, n_boot, seed) for kk, v in by_k_item.items()},
            "full": _item_boot(full_v, n_boot, seed), "clean": _item_boot(clean_v, n_boot, seed),
            "contrast": {k: _item_boot(v, n_boot, seed) for k, v in contrast.items()}, "stray": stray}
