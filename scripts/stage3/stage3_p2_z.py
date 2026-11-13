#!/usr/bin/env python3
"""Line P2, block Z (`P2/preregistration-v1.md` section 3, 19d4a7d5): the descriptive estimand over the dose join's
items (`stage3_ft_join.dose_analysis`). Per item, the mean uptake of its eligible (can-fire) partial cells minus its
full triple's uptake; averaged with equal weight over the items that have an eligible cell; 95 percent interval by
resampling items (`random.Random`, seed 20261114 for P2). Counts and rates only."""
from __future__ import annotations

import random
from collections.abc import Mapping
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
