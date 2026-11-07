#!/usr/bin/env python3
"""Phase B sensitivity (brief 38 dated note 6; post-look, labelled; the committed construction governs).

From `nulls-v0.json` and `applications-v0.json`, through the committed readings code (`stage3_phase_b_readings.py`,
`judge_readings` unchanged), with only the bootstrap index set or the interval construction varied:
  - U(D_h) under the committed percentile construction beside the basic (2·θ̂ − q₀.₀₂₅) and normal (θ̂ + 1.96·SD)
    constructions, on the committed index set `default_rng([20261107, 11])`;
  - U(D_h) and L(D_net) (Opus 4.8) and Sonnet 5's U(D_h) over 60 other index sets `default_rng([20261107, k])`,
    k = 12 to 71, percentile construction; the Monte Carlo error as the SD over those seeds.
Nothing here changes the verdict, which is read on the committed construction and seed. Prints numbers only and writes
`work/stage3/phase-b/phase-b-sensitivity-v0.json`.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_phase_b_sensitivity.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_phase_b_readings as rd  # noqa: E402

VERSION = "phase-b-sensitivity/v0"
OTHER_SEEDS = tuple(range(12, 72))
COMMITTED = 11


def vectors(null_units, app_units, nul, app, W, cid, rules):
    """The D_h and D_net replicate vectors (row 0 the point), recomputed exactly as `judge_readings` does."""
    K = len(cid)
    groups = {"verdict": rd.VERDICT_REGIMES, "comparison": rd.COMPARISON_REGIMES}
    members = {g: [a for a in app_units if (a["ver"], a["regime"]) in regs] for g, regs in groups.items()}
    R = {}
    for arm in ("B0", "B0h", "B1"):
        scored = [(cid[tuple(u["chain"])], nul[arm][u["unit"]]["score"]) for u in null_units
                  if nul[arm].get(u["unit"], {}).get("outcome") == "scored"]
        t, p = rd.fit_shifted(W @ rd.hist([c for c, _ in scored], rd.shift([s for _, s in scored]), K, rd.VG))
        R[arm] = {}
        for g, us in members.items():
            sc = [app[arm].get(a["unit"], {}).get("score") if app[arm].get(a["unit"], {}).get("outcome") == "scored" else None for a in us]
            R[arm][g] = rd.dr.rec(W @ rd.hist([cid[tuple(a["chain"])] for a in us], rd.shift(sc), K, rd.VG), t, p)
    Dh = R["B1"]["verdict"] - R["B0h"]["verdict"]
    D = R["B1"]["verdict"] - R["B0"]["verdict"]
    Dnet = D - (R["B1"]["comparison"] - R["B0"]["comparison"])
    return Dh, Dnet


def constructions(x: np.ndarray) -> dict:
    pt, reps = float(x[0]), x[1:]
    lo, hi = np.quantile(reps, [0.025, 0.975])
    sd = float(np.std(reps, ddof=1))
    return {"point": round(pt, 4), "percentile": [round(float(lo), 4), round(float(hi), 4)],
            "basic": [round(2 * pt - float(hi), 4), round(2 * pt - float(lo), 4)],
            "normal": [round(pt - 1.96 * sd, 4), round(pt + 1.96 * sd, 4)]}


def main() -> int:
    N = rd.load(rd.P / "nulls-v0.json")
    A = rd.load(rd.P / "applications-v0.json")
    rules = rd.rules_from(rd.load(rd.DRYRUN))
    null_units, app_units = N["units"], A["units"]
    clus = sorted({tuple(u["chain"]) for u in null_units})
    cid = {c: i for i, c in enumerate(clus)}
    out = {"version": VERSION, "inputs": {"nulls_sha256": rd.sha256_file(rd.P / "nulls-v0.json"),
                                          "applications_sha256": rd.sha256_file(rd.P / "applications-v0.json"),
                                          "readings_sha256": rd.sha256_file(HERE / "stage3_phase_b_readings.py")},
           "script_sha256": rd.sha256_file(Path(__file__).resolve()), "m_kill": rules["m_kill"],
           "committed_index_set": f"default_rng([{rd.SEED}, {COMMITTED}])", "other_index_sets": f"default_rng([{rd.SEED}, k]), k = {OTHER_SEEDS[0]} to {OTHER_SEEDS[-1]}",
           "judges": {}}
    for judge in ("opus48", "sonnet"):
        nul, app = N["scores"][judge], A["scores"][judge]
        Wc = rd.weights(len(clus), rd.N_BOOT, (rd.SEED, COMMITTED))
        Dh, Dnet = vectors(null_units, app_units, nul, app, Wc, cid, rules)
        J = {"committed": {"D_h": constructions(Dh), "D_net": constructions(Dnet)}}
        uh, ln = [], []
        for k in OTHER_SEEDS:
            Dh_k, Dnet_k = vectors(null_units, app_units, nul, app, rd.weights(len(clus), rd.N_BOOT, (rd.SEED, k)), cid, rules)
            uh.append(float(np.quantile(Dh_k[1:], 0.975)))
            ln.append(float(np.quantile(Dnet_k[1:], 0.025)))
        J["over_seeds"] = {"n_seeds": len(OTHER_SEEDS),
                           "U_D_h": {"min": round(min(uh), 4), "max": round(max(uh), 4), "sd": round(float(np.std(uh, ddof=1)), 4),
                                     "n_below_m_kill": sum(u < rules["m_kill"] for u in uh)},
                           "L_D_net": {"min": round(min(ln), 4), "max": round(max(ln), 4), "n_positive": sum(x > 0 for x in ln)}}
        out["judges"][judge] = J
        print(judge, json.dumps(J))
    p = rd.P / "phase-b-sensitivity-v0.json"
    p.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {p} sha256 {rd.sha256_file(p)[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
