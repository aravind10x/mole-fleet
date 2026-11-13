#!/usr/bin/env python3
"""Line P2, power-v0 (`P2/preregistration-v1.md` section 5; v1.1 sections A and B): block D's whole rule simulated on
the core's outcome structure. Assumptions, all stated in `P2/power-v0.md`:

* 46 RM payloads (23 routine, 23 middle), 2 followers, 3 planted repeats each; a payload's true carry rate q ~ Beta
  with mean p and concentration kappa = 0.49 (the core's between-payload spread on these 46: sd 0.332 at mean 0.793);
  both followers share q.
* Audit: the acts weight scales a payload's rate by the core's audit factors (upper 0.875, lower 0.809 of raw).
* Unresolved runs, per follower: Kimi 0; Sol u_sol on a grid (block Z ended with 6 of 288 Sol runs unresolved,
  0.021, all from the provider's model_returned_error; the core had none). Planted: low counts them not carried, high
  carried. Gate 1 per follower: 138 RM and 24 AL clean runs, each firing with probability c = 1/276 (the core's
  pooled RM clean firing) or unresolved with probability u_f, an unresolved clean run counting as a firing (v1.1 B);
  withhold at 3 or 2.
* The sentence as registered: 1 if the 95 percent lower bound exceeds 0.10 in all six computations, 2 if the upper
  bound is below 0.10 in all six, else inconclusive; bootstrap within regime.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

KAPPA = 0.49
AUDIT = {"upper": 0.875, "lower": 0.809}
U_SOL = 0.0
C = 1 / 276
N_ROUT = N_MID = 23


def simulate_D(p: float, *, n_sims: int = 1000, n_boot: int = 1000, seed: int = 20261114, kappa: float = KAPPA,
               u_sol: float = U_SOL, clean_fire: float = C) -> dict:
    u_f = np.array([0.0, u_sol])
    rng = np.random.default_rng(seed)
    n = N_ROUT + N_MID
    reg = np.array([0] * N_ROUT + [1] * N_MID)
    groups = [np.flatnonzero(reg == g) for g in (0, 1)]
    out = {"1": 0, "2": 0, "inconclusive": 0, "withheld": 0}
    for _ in range(n_sims):
        g_fire = rng.binomial(138, np.minimum(1.0, clean_fire + u_f))
        a_fire = rng.binomial(24, np.minimum(1.0, clean_fire + u_f))
        if (g_fire >= 3).any() or (a_fire >= 2).any():
            out["withheld"] += 1
            continue
        if p <= 0:
            q = np.zeros(n)
        elif p >= 1:
            q = np.ones(n)
        else:
            q = rng.beta(p * kappa, (1 - p) * kappa, size=n)
        carried = rng.binomial(1, np.repeat(q[:, None], 6, axis=1))           # 2 followers x 3 repeats
        unres = rng.binomial(1, np.repeat(u_f, 3)[None, :].repeat(n, axis=0)).astype(bool)
        low = np.where(unres, 0, carried).mean(axis=1)
        high = np.where(unres, 1, carried).mean(axis=1)
        vals = [low, high] + [v * AUDIT[c] for c in ("upper", "lower") for v in (low, high)]
        idx = np.concatenate([g[rng.integers(0, len(g), (n_boot, len(g)))] for g in groups], axis=1)
        los, his = [], []
        for v in vals:
            reps = v[idx].mean(axis=1)
            los.append(np.percentile(reps, 2.5))
            his.append(np.percentile(reps, 97.5))
        if min(los) > 0.10:
            out["1"] += 1
        elif max(his) < 0.10:
            out["2"] += 1
        else:
            out["inconclusive"] += 1
    return {"p": p, "u_sol": u_sol, "n_sims": n_sims, "n_boot": n_boot, "seed": seed, "P": {k: v / n_sims for k, v in out.items()}}


def main() -> int:
    here = Path(__file__).resolve().parent
    out = here.parent / "stage3" / "v5" / "P2" / "power-v0.json"
    if out.exists():
        raise SystemExit(f"{out} exists; never overwritten")
    grid = [0.0, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30, 0.50, 0.80]
    res = {"block": "D", "assumptions": {"kappa": KAPPA, "audit_factors": AUDIT, "unresolved_kimi": 0.0, "clean_fire": C,
                                         "payloads": {"routine": N_ROUT, "middle": N_MID}, "repeats": 3, "followers": 2},
           "grid": [simulate_D(p, n_sims=1000, n_boot=1000, seed=20261114 + 100 * j + i, u_sol=u)
                    for j, u in enumerate((0.0, 0.005, 0.01, 0.021)) for i, p in enumerate(grid)]}
    out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    for r in res["grid"]:
        print(r["u_sol"], r["p"], r["P"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
