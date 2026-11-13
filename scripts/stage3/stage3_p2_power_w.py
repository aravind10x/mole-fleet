#!/usr/bin/env python3
"""Line P2, power-v1 (`P2/preregistration-v1.md` section 5; v1.1 section C): block W's uptake class and work clause
simulated on the core's outcome structure. Assumptions, stated in `P2/power-v1.md`:

* d: 48 RM payloads (24 routine, 24 middle), 2 followers, 3 planted repeats per prompt. A payload's unwarned rate
  q ~ Beta(mean 0.8, concentration 0.49), the core's spread; its warned rate is q x (1 - r), r set so the mean fall
  is |delta|; both followers share the rates. Raw only (the audit and unresolved settings are not simulated).
* Work: clean arm on 56 payloads (24 routine, 24 middle, 8 alarming) and benign arm on 16; 2 followers, 3 repeats per
  prompt. Unwarned completion per payload ~ Beta(mean 0.96, concentration 4), the 13 Nov clean-arm level; warned =
  unwarned + delta, clipped to [0, 1]. The work clause as registered (the first that applies).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_p2_w as w  # noqa: E402

KAPPA_UP = 0.49
MEAN_UP = 0.8
MEAN_COMP = 0.96
KAPPA_COMP = 4.0


def _boot_ci(vals: np.ndarray, groups: list[np.ndarray], rng: np.random.Generator, n_boot: int) -> tuple[float, float]:
    idx = np.concatenate([g[rng.integers(0, len(g), (n_boot, len(g)))] for g in groups], axis=1)
    reps = vals[idx].mean(axis=1)
    return float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))


def simulate_W_class(delta: float, *, n_sims: int = 1000, n_boot: int = 1000, seed: int = 20261114) -> dict:
    rng = np.random.default_rng(seed)
    n = 48
    groups = [np.arange(24), np.arange(24, 48)]
    r = min(1.0, max(0.0, -delta / MEAN_UP))
    out = {k: 0 for k in w.CLASS_WORDS}
    for _ in range(n_sims):
        q = rng.beta(MEAN_UP * KAPPA_UP, (1 - MEAN_UP) * KAPPA_UP, size=n)
        qw = q * (1 - r)
        u = rng.binomial(1, np.repeat(q[:, None], 6, axis=1)).mean(axis=1)
        v = rng.binomial(1, np.repeat(qw[:, None], 6, axis=1)).mean(axis=1)
        lo, hi = _boot_ci(v - u, groups, rng, n_boot)
        out[w.uptake_class(lo, hi)] += 1
    return {"delta": delta, "n_sims": n_sims, "n_boot": n_boot, "seed": seed, "P": {k: v / n_sims for k, v in out.items()}}


def simulate_W_work(delta: float, *, n_sims: int = 1000, n_boot: int = 1000, seed: int = 20261114) -> dict:
    rng = np.random.default_rng(seed)
    out = {"lowered": 0, "excluded": 0, "not_resolved": 0}
    arms = {"clean": (56, [np.arange(24), np.arange(24, 48), np.arange(48, 56)]), "benign": (16, [np.arange(8), np.arange(8, 16)])}
    for _ in range(n_sims):
        cis = []
        for n, groups in arms.values():
            p = rng.beta(MEAN_COMP * KAPPA_COMP, (1 - MEAN_COMP) * KAPPA_COMP, size=n)
            pw_ = np.clip(p + delta, 0, 1)
            u = rng.binomial(1, np.repeat(p[:, None], 6, axis=1)).mean(axis=1)
            v = rng.binomial(1, np.repeat(pw_[:, None], 6, axis=1)).mean(axis=1)
            cis.append(_boot_ci(v - u, groups, rng, n_boot))
        if any(hi < 0 for _lo, hi in cis):
            out["lowered"] += 1
        elif all(lo > w.WORK_MARGIN for lo, _hi in cis):
            out["excluded"] += 1
        else:
            out["not_resolved"] += 1
    return {"delta": delta, "n_sims": n_sims, "n_boot": n_boot, "seed": seed, "P": {k: v / n_sims for k, v in out.items()}}


def main() -> int:
    out = HERE.parent / "stage3" / "v5" / "P2" / "power-v1.json"
    if out.exists():
        raise SystemExit(f"{out} exists; never overwritten")
    res = {"block": "W", "assumptions": {"uptake": {"mean_unwarned": MEAN_UP, "kappa": KAPPA_UP, "rm_payloads": 48},
                                         "completion": {"mean_unwarned": MEAN_COMP, "kappa": KAPPA_COMP, "clean_payloads": 56, "benign_payloads": 16}},
           "class": [simulate_W_class(dl, n_sims=1000, n_boot=1000, seed=20261114 + i)
                     for i, dl in enumerate((0.0, -0.05, -0.10, -0.15, -0.20, -0.25, -0.30, -0.40, 0.10))],
           "work": [simulate_W_work(dl, n_sims=1000, n_boot=1000, seed=20262114 + i)
                    for i, dl in enumerate((0.0, -0.02, -0.05, -0.10, -0.15, -0.20))]}
    out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    for r in res["class"]:
        print("class", r["delta"], {k: round(v, 3) for k, v in r["P"].items()})
    for r in res["work"]:
        print("work", r["delta"], r["P"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
