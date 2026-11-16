#!/usr/bin/env python3
"""The repeat table (coordinator, 2026-11-16; `NEXT-STEPS-2026-11-16-night.md` 5b). Blue side, $0, records on file only;
counts, rates and hashes.

The headline's 48 routine and middle plants across:
* three scorings of the monitor (composed view, Opus 4.8): the record's flags (13 Nov record, at its own 10 percent
  rule); the frozen-state scores (P0 Part 2, arm B, at arm B's 13 Nov rule from ETJ/scores-B.json); and the
  single-statement block's full-plant arm (16 Nov, its own fresh null and rule);
* two follower runs of the full plant: the 13 Nov core and the block's concurrent full-plant arm.
Per scoring: plant-level miss counts and flips between scorings. Per run: uptake (50:50 follower mixture) and
carried-and-missed S = mean over plants of uptake x missed, raw, under the positive audit's two completions, and (the
core only, now) both audits; each run with its own scoring (core: the record; repeat: its own). Pooled by plant: the
mean of the two runs' per-plant S. Intervals: payload bootstrap within regime, 2,000 replicates; the core and the
pooled figures with the core's seed 20261113, the repeat with its block's 20261116."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_ft_join as fj  # noqa: E402

SEED_CORE = 20261113
SEED_SS = 20261116
N_BOOT = 2000


def miss_and_flips(flags: Mapping[str, Mapping[str, bool]], ids: Sequence[str]) -> dict:
    names = list(flags)
    return {"missed": {n: sum(1 for p in ids if not flags[n][p]) for n in names},
            "flips": {a: {b: sum(1 for p in ids if bool(flags[a][p]) != bool(flags[b][p])) for b in names} for a in names}}


def per_plant_uptake(outs: Sequence[Mapping], man: Sequence[Mapping], *, weights: Mapping | None, arm: str = "planted") -> np.ndarray:
    by: dict[tuple, list] = defaultdict(list)
    for r in fj.latest_by_run(outs):
        if r["arm"] == arm:
            by[(r["payload_id"], r["follower"])].append(r)
    return np.array([np.mean([fj._rate(by.get((m["payload_id"], f), []), "low", weights=weights) or 0.0 for f in fj.FOLLOWERS])
                     for m in man], dtype=float)


def boot(vals: np.ndarray, regimes: Sequence[str], *, n_boot: int = N_BOOT, seed: int = SEED_CORE) -> dict:
    rng = np.random.default_rng(seed)
    cols = [np.flatnonzero(np.array(regimes) == g) for g in ("routine", "middle", "alarming") if (np.array(regimes) == g).any()]
    idx = np.concatenate([g[rng.integers(0, len(g), size=(n_boot, len(g)))] for g in cols], axis=1)
    reps = np.asarray(vals)[idx].mean(axis=1)
    return {"point": round(float(np.mean(vals)), 6), "lo": round(float(np.percentile(reps, 2.5)), 6), "hi": round(float(np.percentile(reps, 97.5)), 6)}


def both_audits_uptake(outs: Sequence[Mapping], man: Sequence[Mapping], neg_rows: Sequence[Mapping], *,
                       weights: Mapping[str, Mapping | None]) -> tuple[np.ndarray, np.ndarray]:
    """Per-plant full-plant uptake on both audits: the positive lower completion with the negative audit's acting runs
    (unclear as not acting), and the positive upper with unclear as acting (as the core's both-audits join)."""
    import stage3_ss_neg as sn
    rows = [r for r in neg_rows if r.get("arm") == "planted" or r.get("control")]
    lo = per_plant_uptake(sn.neg_flip(outs, rows, unclear_acting=False), man, weights=weights["lower"])
    hi = per_plant_uptake(sn.neg_flip(outs, rows, unclear_acting=True), man, weights=weights["upper"])
    return lo, hi


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    import stage3_etj as et
    import stage3_ft_run as fr
    import stage3_p1_joins as pj
    import stage3_ss as ss
    import argparse
    ap = argparse.ArgumentParser(description="The repeat table (v0; v1 fills the repeat's both-audits cells).")
    ap.add_argument("--neg-table", type=Path, help="SS/audit-neg-table-SS.json (v1)")
    ap.add_argument("--expect-neg-sha256")
    a = ap.parse_args(argv)
    S3 = HERE.parent / "stage3"
    V5 = S3 / "v5"
    ver = "v1" if a.neg_table else "v0"
    out_j, out_m = V5 / "SS" / f"repeat-table-{ver}.json", V5 / "SS" / f"repeat-table-{ver}.md"
    for p in (out_j, out_m):
        if p.exists():
            raise SystemExit(f"{p} exists; never overwritten")
    src = {"manifest": fr.RED_FT / "cells-manifest.json", "core_outcomes": V5 / "FT" / "outcomes-core-v0.jsonl",
           "core_audit": V5 / "FT" / "audit-table-core.json", "core_neg_audit": V5 / "P0" / "audit-neg-table-core.json",
           "frozen_scores": V5 / "P0" / "frozen-B-v0.json", "etj_scores_B": V5 / "ETJ" / "scores-B.json",
           "ss_outcomes": V5 / "SS" / "outcomes-SS-v0.jsonl", "ss_scores": V5 / "SS" / "scores-SS-v0.json",
           "ss_audit": V5 / "SS" / "audit-table-SS.json"}
    manifest = fr.load_manifest(src["manifest"])
    man = sorted([m for m in manifest if m.get("scorable", True) and m.get("regime") in ("routine", "middle")], key=lambda m: m["payload_id"])
    ids, regs = [m["payload_id"] for m in man], [m["regime"] for m in man]
    rd = lambda p: [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]  # noqa: E731
    core, ssout = rd(src["core_outcomes"]), rd(src["ss_outcomes"])
    fl = fj.load_flags()
    rec = {p: v["flag10"] for p, v in fj.payload_flags(manifest, fl).items()}
    sb = json.loads(src["etj_scores_B"].read_text(encoding="utf-8"))
    frz_app = et.flags(json.loads(src["frozen_scores"].read_text(encoding="utf-8"))["scores"], sb["rule10"])
    frz = {m["payload_id"]: bool(frz_app[fj.resolve_application(fl, m["application_id"])]) for m in man}
    ssf = json.loads(src["ss_scores"].read_text(encoding="utf-8"))["flags10"]
    rep = {p: bool(ssf[f"full:{p}"]) for p in ids}
    flags = {"recorded": rec, "frozen_state": frz, "repeat": rep}
    mf = miss_and_flips(flags, ids)
    missed = {n: np.array([0.0 if flags[n][p] else 1.0 for p in ids]) for n in flags}
    # uptake and S per run
    core_table = json.loads(src["core_audit"].read_text(encoding="utf-8"))
    cw = {c: fj.audit_weights(core, core_table, completion=c) for c in ("upper", "lower")}
    ss_table = json.loads(src["ss_audit"].read_text(encoding="utf-8"))
    sw = {c: ss.audit_weights(ssout, ss_table, c) for c in ("upper", "lower")}
    neg = json.loads(src["core_neg_audit"].read_text(encoding="utf-8"))["runs"]
    u = {"core": {"raw": per_plant_uptake(core, man, weights=None), **{c: per_plant_uptake(core, man, weights=cw[c]) for c in cw}},
         "repeat": {"raw": per_plant_uptake(ssout, man, weights=None), **{c: per_plant_uptake(ssout, man, weights=sw[c]) for c in sw}}}
    both = {"lower": per_plant_uptake(pj.neg_outcomes(core, neg, unclear_acting=False), man, weights=cw["lower"]),
            "upper": per_plant_uptake(pj.neg_outcomes(core, neg, unclear_acting=True), man, weights=cw["upper"])}
    seed = {"core": SEED_CORE, "repeat": SEED_SS}
    run_flag = {"core": "recorded", "repeat": "repeat"}
    S = {r: {k: boot(u[r][k] * missed[run_flag[r]], regs, seed=seed[r]) for k in ("raw", "upper", "lower")} for r in u}
    S["core"]["both_audits_lower"] = boot(both["lower"] * missed["recorded"], regs, seed=SEED_CORE)
    S["core"]["both_audits_upper"] = boot(both["upper"] * missed["recorded"], regs, seed=SEED_CORE)
    S["repeat"]["both_audits"] = "pending: the block's predicate-negative audit (preregistration-v1-addition-neg-audit.md 5f405aee)"
    if a.neg_table:
        if _sha(a.neg_table) != a.expect_neg_sha256:
            raise SystemExit("refusing: the negative-audit table is not the one of record")
        src["ss_neg_audit"] = a.neg_table
        nt = json.loads(a.neg_table.read_text(encoding="utf-8"))
        rlo, rhi = both_audits_uptake(ssout, man, nt["runs"] if isinstance(nt, dict) else nt, weights=sw)
        del S["repeat"]["both_audits"]
        S["repeat"]["both_audits_lower"] = boot(rlo * missed["repeat"], regs, seed=SEED_SS)
        S["repeat"]["both_audits_upper"] = boot(rhi * missed["repeat"], regs, seed=SEED_SS)
    uptake = {r: boot(u[r]["raw"], regs, seed=seed[r]) for r in u}
    pooled = {k: boot((u["core"][k] * missed["recorded"] + u["repeat"][k] * missed["repeat"]) / 2, regs, seed=SEED_CORE)
              for k in ("raw", "upper", "lower")}
    pooled["both_audits"] = "pending: needs the repeat's both-audits count"
    if a.neg_table:
        del pooled["both_audits"]
        pooled["both_audits_lower"] = boot((both["lower"] * missed["recorded"] + rlo * missed["repeat"]) / 2, regs, seed=SEED_CORE)
        pooled["both_audits_upper"] = boot((both["upper"] * missed["recorded"] + rhi * missed["repeat"]) / 2, regs, seed=SEED_CORE)
    # beside: each run under each scoring, raw
    cross = {r: {n: boot(u[r]["raw"] * missed[n], regs, seed=seed[r]) for n in flags} for r in u}
    res = {"label": "descriptive; records on file; no new claim", "n_plants": len(ids), "monitor": mf, "uptake": uptake, "S": S,
           "pooled_by_plant": pooled, "S_raw_each_run_under_each_scoring": cross,
           "sources": {k: _sha(v) for k, v in src.items()},
           "seeds": {"core_and_pooled": SEED_CORE, "repeat": SEED_SS}}
    out_j.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"missed": mf["missed"], "flips": mf["flips"], "uptake": uptake, "S": S, "pooled": pooled}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
