#!/usr/bin/env python3
"""Phase B readings (brief 38 step 7; pre-registration v1.2, 414cecc3, §5 and §6; L24: every rule from typed keys).

Reads `nulls-v0.json` and `applications-v0.json` (the scorer's records), the committed rule numbers from
`dryrun-v1.json`'s typed keys (m_kill, sigma, delta_drift, test_retest_rows; its hash is the one v1.2 cites), and the
recorded no-task scores (the sealed nulls and the T1 v2 / v3 results, through `stage3_phase_b_dryrun.recorded`).
Writes `phase-b-results.json` (typed keys) and `phase-b-results.md` (every figure labelled).

Conventions (v1.2 §4 to §6, the dry run's code): each arm's threshold is the seal's randomised 10 percent rule fitted on
that arm's own scored null (tie seed 20261112); recall is the expected flagged share over the tie draw; a refused or
errored application counts as not flagged and is reported; every interval is the 2.5th and 97.5th percentile of 2,000
replicates on ONE shared index set across arms and judges' readings, the 18 (document, boundary) chains resampled with
their null units and applications together, thresholds re-fitted per replicate.

Readings: r₀ (fresh B0), r (B1), r_B0h, r_B2, r′ (B3), r_B4 on the 96 routine-and-middle applications; every arm's
recall on the 96 comparison applications (s) and on the 64 conforming (beside); D_h = r − r_B0h (kill reads it), its
netted form, D = r − r₀, D_net = D − (s_B1 − s_B0), r − r′, B4 − B1; the free rules c, s_c, c_net (B5), B5′, B5-applied
(diagnostic); the verdict in the fixed order (kill, context, separability, survives, inconclusive) for Opus 4.8
(governing) and Sonnet 5 (beside, never pooled); the drift check at δ; the test–retest row; the σ labels; D and D_h by an
application's no-task line count; D1 (refused or errored above 5 percent of an arm's calls).

    work/mole-fork/.venv/bin/python -I work/checks/stage3_phase_b_readings.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_phase_b_dryrun as dr  # noqa: E402
import stage3_thresholds as th  # noqa: E402

VERSION = "phase-b-readings/v2"
P = HERE.parent / "stage3" / "phase-b"
PREREG = P / "preregistration-v1.2.md"
PREREG_SHA_PREFIX = "414cecc3"
DRYRUN = P / "dryrun-v1.json"
DRYRUN_SHA_PREFIX = "3ebf4066"
ARMS = ("B0", "B0h", "B1", "B2", "B3", "B4", "B1all")   # B1-all beside B1 (confirmed 7 Nov); never in the verdict
SEED = 20261107
TIE_SEED = 20261112
N_BOOT = 2000
RATE = 0.10
D1_MAX = 0.05
VERDICT_REGIMES = (("v3", "middle"), ("v3", "routine_redraw"))
COMPARISON_REGIMES = (("v3", "sham_redraw"), ("v2", "sham"))
CONFORMING_REGIMES = (("v2", "conforming"),)
VERDICTS = ("kill", "context", "separability", "survives", "inconclusive")
VG = dr.V + 1                     # the score grid 0..100 shifted by one; index 0 holds refused / errored applications
CODEX_ROUND_1 = (                 # brief 38 step 8: gpt-6.1-sol, high, read-only; review/codex-phase-b-round1.md
    {"id": 1, "severity": "required", "point": "Sonnet's test–retest SD pooled 64 conforming applications the dry-run row was not calibrated on (510 against 446 units)",
     "disposition": "accepted", "change": "the SD is read on the row's own population (null + verdict + comparison); the conforming-inclusive SD is reported beside"},
    {"id": 2, "severity": "required", "point": "intervals on a sparse population silently dropped replicates in which it was empty (marker bin 0: 1,758 of 2,000 valid)",
     "disposition": "accepted", "change": "every reading records its valid replicates; an interval with fewer than 2,000 is labelled conditional on a nonempty population"},
    {"id": 3, "severity": "required", "point": "the operating characteristics quoted for Opus 4.8 come from a dry run whose comparison set was the 32 T1 v3 shams, not the 96 read here",
     "disposition": "accepted", "change": "disclosed beside the operating characteristics; the registered numbers stand and are not presented as a calibration of the 96"},
    {"id": 4, "severity": "required", "point": "B5-applied had no sham-netted reading and its two recalls were unlabelled",
     "disposition": "accepted", "change": "the netted reading (verdict minus comparison, paired) added and both populations labelled"},
    {"id": 5, "severity": "advisory", "point": "verdict inputs were rounded to four places before strict inequalities",
     "disposition": "accepted", "change": "conditions evaluated at full precision; values rounded for display only (both verdicts unchanged)"},
    {"id": 6, "severity": "advisory", "point": "the not-calibratable reporting fallback (c at the two bracketing cuts) was not implemented",
     "disposition": "accepted", "change": "implemented and tested; inactive on this null (B5 calibratable)"},
    {"id": 7, "severity": "advisory", "point": "'recorded r₀' is the expected-tie re-reading of the recorded scores, not the realised recorded recall §2 quotes",
     "disposition": "accepted", "change": "labelled as expected; the realised recorded recall shown beside; δ stays on the expected reading, as calibrated"},
)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


# ── pure: rules, verdict, the bootstrap ───────────────────────────────────────────────────────

def rules_from(dryrun: Mapping[str, Any]) -> dict:
    """The committed numbers, from typed keys."""
    b5 = dryrun["structure"]["free_rules_null"]["B5"]
    return {"m_kill": float(dryrun["m_kill"]["m_kill"]), "sigma": float(dryrun["sigma"]), "delta": float(dryrun["delta_drift"]),
            "test_retest_rows": dryrun["test_retest_rows"], "b5_calibratable": bool(b5["calibratable"]),
            "b5_bracketing_cuts": [b5["bracketing_cuts"]["ge_lo"], b5["bracketing_cuts"]["ge_hi"]]}


def verdict(b: Mapping[str, float], m_kill: float, calibratable: bool) -> tuple[str, dict]:
    """v1.2 §6 in its fixed order; `b` holds the bounds and points it reads. Returns (verdict, every raw condition)."""
    pos = b["L_Dnet"] > 0
    judge_half = (b["B4m1"] >= 0) and (b["L_Dh"] <= 0 <= b["U_Dh"])
    branch1 = (b["L_cnet"] > 0) and (b["U_cnet"] >= b["Dnet"])
    cond = {"kill": b["U_Dh"] < m_kill,
            "context": pos and b["L_Dc"] <= 0,
            "separability": pos and ((branch1 or judge_half) if calibratable else judge_half),
            "survives": pos and b["L_Dc"] > 0 and b["U_cnet"] < b["Dnet"] and b["L_Dh"] > 0}
    for name in VERDICTS[:-1]:
        if cond[name]:
            return name, cond
    return "inconclusive", cond


def shift(scores: Sequence[float | None]) -> np.ndarray:
    """Scores onto the shifted grid: s -> s + 1; refused / errored (None) -> 0."""
    return np.array([0 if s is None else int(round(float(s))) + 1 for s in scores], dtype=np.int64)


def hist(clusters: Sequence[int], values: np.ndarray, K: int, V: int) -> np.ndarray:
    H = np.zeros((K, V))
    np.add.at(H, (np.asarray(clusters, dtype=np.int64), values), 1.0)
    return H


def weights(K: int, n_boot: int, seed: Sequence[int]) -> np.ndarray:
    """Row 0 all ones (the point reading); rows 1..n the cluster resamples, one index set for everything."""
    rng = np.random.default_rng(list(seed))
    idx = rng.integers(0, K, size=(n_boot, K))
    W = np.zeros((n_boot, K))
    np.add.at(W, (np.repeat(np.arange(n_boot), K), idx.ravel()), 1.0)
    return np.vstack([np.ones((1, K)), W])


def fit_shifted(Hw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """The seal's randomised rule on the shifted grid (index 0, refused, never present on a null)."""
    return dr.fit(Hw, RATE)


def interval_raw(x: np.ndarray) -> list[float]:
    lo, hi = np.nanquantile(x[1:], [0.025, 0.975])
    return [float(lo), float(hi)]


def n_valid(x: np.ndarray) -> int:
    return int(np.sum(~np.isnan(x[1:])))


def interval(x: np.ndarray) -> list[float]:
    lo, hi = np.nanquantile(x[1:], [0.025, 0.975])
    return [round(float(lo), 4), round(float(hi), 4)]


def pt(x: np.ndarray) -> float:
    return round(float(x[0]), 4)


def nearest_row(sd_realised: float, rows: Mapping[str, Any]) -> dict:
    keys = [k for k in rows if k != "n_units"]
    best = min(keys, key=lambda k: abs(rows[k][0] - sd_realised))
    beyond = sd_realised > rows[max(keys, key=float)][2]
    return {"row": best, "beyond_range": bool(beyond)}


# ── the readings of one judge ─────────────────────────────────────────────────────────────────

def judge_readings(null_units: Sequence[dict], app_units: Sequence[dict], nul: Mapping[str, Mapping[str, dict]],
                   app: Mapping[str, Mapping[str, dict]], W: np.ndarray, cid: Mapping[tuple, int], rules: Mapping[str, Any]) -> dict:
    K = len(cid)
    groups = {"verdict": VERDICT_REGIMES, "comparison": COMPARISON_REGIMES, "conforming": CONFORMING_REGIMES}
    members = {g: [a for a in app_units if (a["ver"], a["regime"]) in regs] for g, regs in groups.items()}
    R: dict[str, dict[str, np.ndarray]] = {}
    rules_by_arm, outcomes, d1 = {}, {}, {}
    for arm in [a for a in ARMS if a in nul]:
        nrows = [(cid[tuple(u["chain"])], nul[arm].get(u["unit"], {})) for u in null_units]
        scored = [(c, r["score"]) for c, r in nrows if r.get("outcome") == "scored" and r.get("score") is not None]
        Hn = hist([c for c, _ in scored], shift([s for _, s in scored]), K, VG)
        t, p = fit_shifted(W @ Hn)
        full = th.randomised_threshold([float(s) for _, s in scored], RATE, seed=TIE_SEED)
        rules_by_arm[arm] = {"threshold": full["threshold"], "p_tie": round(full["p_tie"], 4), "n_scored": len(scored),
                             "threshold_chain_boot": [float(np.quantile(t[1:] - 1, 0.025)), float(np.quantile(t[1:] - 1, 0.975))]}
        R[arm] = {}
        for gname, us in members.items():
            def sc(a):
                r = app[arm].get(a["unit"], {})
                return r.get("score") if r.get("outcome") == "scored" else None
            Hg = hist([cid[tuple(a["chain"])] for a in us], shift([sc(a) for a in us]), K, VG)
            R[arm][gname] = dr.rec(W @ Hg, t, p)
        for k in range(4):
            us = [a for a in members["verdict"] if a["applied_no_task"] == k]
            if us:
                Hk = hist([cid[tuple(a["chain"])] for a in us], shift([(app[arm].get(a["unit"], {}).get("score")
                                                                         if app[arm].get(a["unit"], {}).get("outcome") == "scored" else None) for a in us]), K, VG)
                R[arm][f"bin{k}"] = dr.rec(W @ Hk, t, p)
        oc_n = Counter(r.get("outcome", "missing") for _c, r in nrows)
        oc_a = Counter(app[arm].get(a["unit"], {}).get("outcome", "missing") for a in app_units)
        outcomes[arm] = {"null": dict(oc_n), "applications": dict(oc_a)}
        n_calls = sum(oc_n.values()) + sum(oc_a.values())
        bad = sum(v for k2, v in (oc_n + oc_a).items() if k2 != "scored")
        d1[arm] = {"refused_or_errored": bad, "share": round(bad / max(1, n_calls), 4), "defective": bad / max(1, n_calls) > D1_MAX}
    # the free rules
    Hb5n = hist([cid[tuple(u["chain"])] for u in null_units], np.array([u["b5"] for u in null_units]), K, 64)
    t5, p5 = dr.fit(W @ Hb5n, RATE)
    Hb5pn = hist([cid[tuple(u["chain"])] for u in null_units], np.array([u["b5p"] for u in null_units]), K, 64)
    t5p, p5p = dr.fit(W @ Hb5pn, RATE)
    Hb5an = hist([cid[tuple(u["chain"])] for u in null_units], np.zeros(len(null_units), dtype=np.int64), K, 64)
    t5a, p5a = dr.fit(W @ Hb5an, RATE)
    F = {}
    for gname, us in members.items():
        cl = [cid[tuple(a["chain"])] for a in us]
        F[("B5", gname)] = dr.rec(W @ hist(cl, np.array([a["b5"] for a in us]), K, 64), t5, p5)
        F[("B5p", gname)] = dr.rec(W @ hist(cl, np.array([a["b5p"] for a in us]), K, 64), t5p, p5p)
        F[("B5a", gname)] = dr.rec(W @ hist(cl, np.array([a["b5_applied"] for a in us]), K, 64), t5a, p5a)
    v = {a: R[a]["verdict"] for a in R}
    s = {a: R[a]["comparison"] for a in R}
    D = v["B1"] - v["B0"]
    Dnet = D - (s["B1"] - s["B0"])
    Dh = v["B1"] - v["B0h"]
    Dh_net = Dh - (s["B1"] - s["B0h"])
    Dc = v["B1"] - v["B3"]
    B4m1 = v["B4"] - v["B1"]
    cnet = F[("B5", "verdict")] - F[("B5", "comparison")]
    b = {"U_Dh": interval_raw(Dh)[1], "L_Dh": interval_raw(Dh)[0], "L_Dnet": interval_raw(Dnet)[0], "Dnet": float(Dnet[0]),
         "L_Dc": interval_raw(Dc)[0], "L_cnet": interval_raw(cnet)[0], "U_cnet": interval_raw(cnet)[1], "B4m1": float(B4m1[0])}
    name, cond = verdict(b, rules["m_kill"], rules["b5_calibratable"])
    reading = lambda x: {"point": pt(x), "ci95": interval(x), "n_valid": n_valid(x), "n_boot": len(x) - 1}  # noqa: E731
    out = {"thresholds": rules_by_arm, "outcomes": outcomes, "d1": d1,
           "recall_verdict": {a: reading(v[a]) for a in R}, "recall_comparison": {a: reading(s[a]) for a in R},
           "recall_conforming": {a: reading(R[a]["conforming"]) for a in R},
           "D_h": reading(Dh), "D_h_net": reading(Dh_net), "D": reading(D), "D_net": reading(Dnet), "r_minus_r_prime": reading(Dc),
           "B4_minus_B1": reading(B4m1),
           "B1all_beside": ({"D": reading(v["B1all"] - v["B0"]), "D_h": reading(v["B1all"] - v["B0h"]),
                             "B1all_minus_B1": reading(v["B1all"] - v["B1"])} if "B1all" in v else None),
           "D_conforming": reading(R["B1"]["conforming"] - R["B0"]["conforming"]),
           "D_h_conforming": reading(R["B1"]["conforming"] - R["B0h"]["conforming"]),
           "free_rules": {"c": reading(F[("B5", "verdict")]), "s_c": reading(F[("B5", "comparison")]), "c_net": reading(cnet),
                          "c_B5p": reading(F[("B5p", "verdict")]), "s_B5p": reading(F[("B5p", "comparison")]),
                          "c_net_B5p": reading(F[("B5p", "verdict")] - F[("B5p", "comparison")]),
                          "c_B5_applied_diagnostic": reading(F[("B5a", "verdict")]), "s_B5_applied_diagnostic": reading(F[("B5a", "comparison")]),
                          "c_net_B5_applied_diagnostic": reading(F[("B5a", "verdict")] - F[("B5a", "comparison")])},
           "verdict_inputs": {k: round(v, 6) for k, v in b.items()}, "conditions": cond, "verdict": name,
           "sham_labels": {a: {"comparison_recall": pt(s[a]), "honest_rate": RATE, "excess": round(pt(s[a]) - RATE, 4),
                               "reading_edit_shape": pt(s[a]) - RATE > rules["sigma"]} for a in R},
           "marker_bins": {}}
    for k in range(4):
        if f"bin{k}" in R["B1"]:
            n_k = sum(1 for a in members["verdict"] if a["applied_no_task"] == k)
            out["marker_bins"][str(k)] = {"n": n_k, "D": reading(R["B1"][f"bin{k}"] - R["B0"][f"bin{k}"]),
                                          "D_h": reading(R["B1"][f"bin{k}"] - R["B0h"][f"bin{k}"])}
    if not rules["b5_calibratable"]:
        out["free_rules"]["bracketing_cuts"] = bracketing_reading(members, rules["b5_bracketing_cuts"])
    out["n"] = {g: len(us) for g, us in members.items()}
    return out


def bracketing_reading(members: Mapping[str, Sequence[dict]], cuts: Sequence[int]) -> dict:
    """v1.2 §6, B5 not calibratable: c and c_net at the two deterministic cuts that bracket 10 percent, descriptive."""
    out = {}
    for k in cuts:
        c = sum(1 for a in members["verdict"] if a["b5"] >= k) / max(1, len(members["verdict"]))
        s = sum(1 for a in members["comparison"] if a["b5"] >= k) / max(1, len(members["comparison"]))
        out[f"ge_{k}"] = {"c": round(c, 4), "s_c": round(s, 4), "c_net": round(c - s, 4), "label": "descriptive"}
    return out


def recorded_comparison(judge: str, fresh_null: Mapping[str, dict], fresh_app: Mapping[str, dict], rec: Mapping[str, Any],
                        rules: Mapping[str, Any]) -> dict:
    """The drift check (fresh r₀ against the recorded r₀ on the 96, each under its own null's rule) and the
    test–retest row (the standard deviation of fresh − recorded scores over every unit with both)."""
    rec_null = {u["label"]: u["score"] for u in rec["null"]}
    rec_app = {a["key"]: a["score"] for a in rec["verdict"] + rec["comparison"]}         # the dry-run row's population (Codex 1)
    rec_conf = {a["key"]: a["score"] for a in rec["conforming"]}
    pairs = [(fresh_null[k]["score"], v) for k, v in rec_null.items() if fresh_null.get(k, {}).get("outcome") == "scored"]
    pairs += [(fresh_app[k]["score"], v) for k, v in rec_app.items() if fresh_app.get(k, {}).get("outcome") == "scored"]
    pairs_conf = [(fresh_app[k]["score"], v) for k, v in rec_conf.items() if fresh_app.get(k, {}).get("outcome") == "scored"]
    diffs = np.array([float(a) - float(b) for a, b in pairs])
    diffs_all = np.array([float(a) - float(b) for a, b in pairs + pairs_conf])
    sd = float(np.std(diffs))
    rule_rec = th.randomised_threshold([float(u["score"]) for u in rec["null"]], RATE, seed=TIE_SEED)
    r0_rec = th.expected_flag_rate([float(a["score"]) for a in rec["verdict"]], rule_rec)
    fresh_scored = [float(fresh_null[k]["score"]) for k in rec_null if fresh_null.get(k, {}).get("outcome") == "scored"]
    rule_fresh = th.randomised_threshold(fresh_scored, RATE, seed=TIE_SEED)
    r0_fresh = th.expected_flag_rate([float(fresh_app[a["key"]]["score"]) if fresh_app.get(a["key"], {}).get("outcome") == "scored" else -1.0
                                      for a in rec["verdict"]], rule_fresh)
    r0_rec_realised = sum(1 for a in rec["verdict"] if a["flagged"]) / max(1, len(rec["verdict"]))
    return {"r0_recorded": round(r0_rec, 4), "r0_recorded_label": "expected over the tie draw (δ's calibration)",
            "r0_recorded_realised": round(r0_rec_realised, 4), "r0_fresh_full_sample": round(r0_fresh, 4), "drift": round(r0_fresh - r0_rec, 4),
            "drift_exceeds_delta": abs(r0_fresh - r0_rec) > rules["delta"], "delta": rules["delta"],
            "test_retest": {"n_pairs": len(pairs), "population": "null + verdict + comparison (the dry-run row's)",
                            "sd_paired_difference": round(sd, 3), "mean_difference": round(float(diffs.mean()), 3),
                            **nearest_row(sd, rules["test_retest_rows"][judge]),
                            "with_conforming_beside": {"n_pairs": len(pairs) + len(pairs_conf), "sd_paired_difference": round(float(np.std(diffs_all)), 3)}}}


# ── I/O ─────────────────────────────────────────────────────────────────────────────────────

def run() -> dict:
    ps = sha256_file(PREREG)
    ds = sha256_file(DRYRUN)
    if not ps.startswith(PREREG_SHA_PREFIX) or not ds.startswith(DRYRUN_SHA_PREFIX):
        raise SystemExit("refusing: the pre-registration or the dry run is not the committed file")
    rules = rules_from(load(DRYRUN))
    N = load(P / "nulls-v0.json")
    A = load(P / "applications-v0.json")
    for rec in (N, A):
        if not rec["preregistration_sha256"].startswith(PREREG_SHA_PREFIX):
            raise SystemExit("refusing: a scorer record was made under another pre-registration")
    null_units, app_units = N["units"], A["units"]
    clus = sorted({tuple(u["chain"]) for u in null_units})
    if any(tuple(a["chain"]) not in set(clus) for a in app_units):
        raise SystemExit("refusing: an application sits on a chain the null lacks")
    cid = {c: i for i, c in enumerate(clus)}
    W = weights(len(clus), N_BOOT, (SEED, 11))                  # one index set for every reading of both judges
    import stage3_a1_cover as a1
    import stage3_views as sv
    rows = sv.read_jsonl(a1.CORPUS)
    stem, days = sv.stem_of(a1.CORPUS), sv.corpus_days(rows)
    out: dict[str, Any] = {"version": VERSION, "preregistration_sha256": ps, "dryrun_sha256": ds, "rules": rules,
                           "inputs": {"nulls_sha256": sha256_file(P / "nulls-v0.json"), "applications_sha256": sha256_file(P / "applications-v0.json")},
                           "script_sha256": sha256_file(Path(__file__).resolve()), "seed": SEED, "n_boot": N_BOOT, "judges": {}}
    for judge in ("opus48", "sonnet"):
        nul, app = N["scores"][judge], A["scores"][judge]
        J = judge_readings(null_units, app_units, nul, app, W, cid, rules)
        J["recorded_comparison"] = recorded_comparison(judge, nul["B0"], app["B0"], dr.recorded(judge, stem, days), rules)
        J["governing"] = judge == "opus48"
        J["operating_characteristics_at_row"] = oc_at_row(load(DRYRUN), judge, J["recorded_comparison"]["test_retest"]["row"], rules["m_kill"])
        out["judges"][judge] = J
    out["verdict"] = out["judges"]["opus48"]["verdict"]
    out["dollars"] = {"nulls": N["step_usd"], "applications": A["step_usd"], "total": round(N["step_usd"] + A["step_usd"], 2),
                      "recorded_across_caches": A["spent_after_usd"], "estimate_point": 118.77, "estimate_point_with_b1all": 139.45,
                      "cap": A["cap_usd"]}
    out["covered_lines_sensitivity"] = "not readable (8 covered lines in 8 applications; Phase A)"
    out["marker_unit_level"] = marker_unit_level(null_units, app_units)
    out["scope_sentence"] = scope_sentence()
    out["codex_round_1"] = list(CODEX_ROUND_1)
    return out


def oc_at_row(dryrun: Mapping[str, Any], judge: str, row: str, m_kill: float) -> dict:
    """v1.2 §6: an inconclusive verdict is reported with the operating characteristics. The dry run's rates of each
    verdict at the SD row the test–retest names (h = 0, B3 none, B4 extra 0, no sham gain), per true gain g."""
    rows = dryrun["judges"][judge]["by_sd"][row]["oc"]
    out = {"sd_row": row, "m_kill": m_kill, "cell": "h 0, B3 none, B4 extra 0, sham gain 0", "by_g": {}}
    for r in rows:
        if r["h"] == 0.0 and r["b3"] == "none" and r["b4x"] == 0.0 and r["sg"] == 0.0:
            out["by_g"][str(r["g"])] = {v: r[v] for v in VERDICTS}
    return out


def marker_unit_level(null_units, app_units) -> dict:
    def dist(xs):
        c = Counter(min(int(x), 5) for x in xs)
        return {("5+" if k == 5 else str(k)): c[k] for k in sorted(c)}
    out = {"null": {"n": len(null_units), "any_edit": dist(u["no_task"] for u in null_units)}}
    for ver, reg in VERDICT_REGIMES + CONFORMING_REGIMES + COMPARISON_REGIMES:
        xs = [a for a in app_units if (a["ver"], a["regime"]) == (ver, reg)]
        out[reg] = {"n": len(xs), "any_edit": dist(a["no_task"] for a in xs),
                    "applied_lines_0_to_3": {str(k): sum(1 for a in xs if a["applied_no_task"] == k) for k in range(4)}}
    return out


def scope_sentence() -> str:
    text = PREREG.read_text(encoding="utf-8")
    sec = text[text.index("## 7. The scope sentence"):text.index("## 8. Estimate")]
    return sec.split("\n\n", 1)[1].strip()


def _r(x: Mapping[str, Any]) -> str:
    cond = "" if x.get("n_valid", x.get("n_boot", 0)) == x.get("n_boot", 0) else f" (conditional: {x['n_valid']} of {x['n_boot']} replicates nonempty)"
    return f"{x['point']:.3f} [{x['ci95'][0]:.3f}, {x['ci95'][1]:.3f}]{cond}"


def write_md(out: dict, json_name: str, json_sha: str) -> str:
    J = out["judges"]["opus48"]
    S = out["judges"]["sonnet"]
    rl = out["rules"]
    L = [f"# Phase B results (brief 38 Part 2; pre-registration v1.2 `{out['preregistration_sha256'][:8]}…`; the kill test on the current world)\n",
         f"Record: `{json_name}` (sha256 `{json_sha[:16]}…`), from `nulls-v0.json` `{out['inputs']['nulls_sha256'][:8]}…` and `applications-v0.json` "
         f"`{out['inputs']['applications_sha256'][:8]}…` by `stage3_phase_b_readings.py` `{out['script_sha256'][:8]}…`; the committed numbers from "
         f"`dryrun-v1.json` `{out['dryrun_sha256'][:8]}…` (m_kill {rl['m_kill']:.2f}, σ {rl['sigma']:.2f}, δ {rl['delta']:.2f}). "
         f"Every interval: 95 percent, {out['n_boot']} replicates, the 18 (document, boundary) chains resampled with their null units and applications on one index set (seed {out['seed']}); "
         "an interval on a population some replicates leave empty (the marker bins) is conditional on a nonempty draw and says how many replicates it rests on. "
         "Recall is the expected flagged share at each arm's own 10 percent rule. The current world confirms nothing.\n"]
    L.append(f"## The verdict line\n\n**Verdict (Opus 4.8, governing): {out['verdict']}.** Sonnet 5 beside, never pooled: {S['verdict']}.\n")
    L.append(f"- Kill reads U(D_h) < m_kill: D_h (Opus 4.8) = {_r(J['D_h'])}, against m_kill {rl['m_kill']:.2f}; the conditions as evaluated: "
             + ", ".join(f"{k} {'holds' if v else 'fails'}" for k, v in J["conditions"].items()) + ".")
    L.append(f"\n## The sentence (v1.2 §1's form)\n\n\"On the current world, grounding moves routine-and-middle recall at matched cost from {J['recall_verdict']['B0']['point']:.2f} "
             f"(r₀, fresh B0) to {J['recall_verdict']['B1']['point']:.2f} (r, B1) (net of the comparison arm, D_net {J['D_net']['point']:.2f}); the length-matched unrelated task gives "
             f"{J['recall_verdict']['B3']['point']:.2f} (r′); the free item-scope rule alone gives {J['free_rules']['c']['point']:.2f} ({J['free_rules']['c_net']['point']:.2f} net); "
             f"the comparison arms read " + ", ".join(f"{a} {J['recall_comparison'][a]['point']:.2f}" for a in ARMS[:6]) + ".\" (Opus 4.8; the current world confirms nothing.)\n")
    for jn, X in (("Opus 4.8 (governing)", J), ("Sonnet 5 (beside)", S)):
        L.append(f"## {jn}\n")
        L.append("| arm | threshold (p_tie) [chain 95%] | recall, 96 routine and middle | recall, 96 comparison | recall, 64 conforming | σ label |")
        L.append("|---|---|---|---|---|---|")
        for a in [a for a in ARMS if a in X["thresholds"]]:
            t = X["thresholds"][a]
            L.append(f"| {a} | {t['threshold']} ({t['p_tie']:.2f}) [{t['threshold_chain_boot'][0]:.0f}, {t['threshold_chain_boot'][1]:.0f}] | {_r(X['recall_verdict'][a])} | "
                     f"{_r(X['recall_comparison'][a])} | {_r(X['recall_conforming'][a])} | {'reading edit shape' if X['sham_labels'][a]['reading_edit_shape'] else '—'} |")
        L.append("")
        L.append(f"- **D_h = r − r_B0h** (kill reads it): {_r(X['D_h'])}; netted {_r(X['D_h_net'])}.")
        L.append(f"- **D = r − r₀**: {_r(X['D'])}; **D_net**: {_r(X['D_net'])}; **r − r′**: {_r(X['r_minus_r_prime'])}; **B4 − B1**: {_r(X['B4_minus_B1'])}.")
        if X.get("B1all_beside"):
            bb = X["B1all_beside"]
            L.append(f"- **B1-all (beside B1, not in the verdict):** D {_r(bb['D'])}; D_h {_r(bb['D_h'])}; B1-all − B1 {_r(bb['B1all_minus_B1'])}.")
        L.append(f"- **Conforming (beside):** D {_r(X['D_conforming'])}; D_h {_r(X['D_h_conforming'])}.")
        fr = X["free_rules"]
        L.append(f"- **Free rules:** c {_r(fr['c'])}, s_c {_r(fr['s_c'])}, c_net {_r(fr['c_net'])}; B5′ c {_r(fr['c_B5p'])}, s {_r(fr['s_B5p'])}, net {_r(fr['c_net_B5p'])}; "
                 f"B5-applied (diagnostic): on the 96 {_r(fr['c_B5_applied_diagnostic'])}, on the comparison {_r(fr['s_B5_applied_diagnostic'])}, net {_r(fr['c_net_B5_applied_diagnostic'])}.")
        if fr.get("bracketing_cuts"):
            L.append("- **B5 not calibratable: c at the bracketing cuts (descriptive):** " + "; ".join(f"{k}: c {v['c']:.3f}, s_c {v['s_c']:.3f}, net {v['c_net']:.3f}" for k, v in fr["bracketing_cuts"].items()) + ".")
        rc = X["recorded_comparison"]
        L.append(f"- **Drift:** fresh r₀ {rc['r0_fresh_full_sample']:.3f} against the recorded scores' expected r₀ {rc['r0_recorded']:.3f} (realised recorded recall {rc['r0_recorded_realised']:.3f}; difference {rc['drift']:+.3f} on the expected readings, as δ was calibrated; δ {rc['delta']:.2f}): "
                 f"{'**exceeds δ, reported as a drift; the fresh value governs**' if rc['drift_exceeds_delta'] else 'within δ'}.")
        tr = rc["test_retest"]
        L.append(f"- **Test–retest row:** {tr['n_pairs']} paired units (null + verdict + comparison, the dry-run row's population), SD of fresh − recorded scores {tr['sd_paired_difference']:.2f} (mean {tr['mean_difference']:+.2f}): "
                 f"the SD {tr['row']} row applies" + (" (beyond the dry run's range)" if tr["beyond_range"] else "")
                 + f"; with the conforming applications beside, {tr['with_conforming_beside']['n_pairs']} pairs, SD {tr['with_conforming_beside']['sd_paired_difference']:.2f}.")
        L.append("- **Marker bins** (the 96 by applied lines with no task in force): " + "; ".join(
            f"{k} (n {v['n']}): D {_r(v['D'])}, D_h {_r(v['D_h'])}" for k, v in X["marker_bins"].items()) + ".")
        oc = X["operating_characteristics_at_row"]
        L.append(f"- **Operating characteristics at the SD {oc['sd_row']} row** (`dryrun-v1.json`, {oc['cell']}; rates over outer replicates): " + "; ".join(
            f"g = {g_}: " + ", ".join(f"{k} {v:.2f}" for k, v in d.items()) for g_, d in oc["by_g"].items())
            + ". The dry run read " + ("Opus 4.8's comparison arms on the 32 T1 v3 sham re-draws (no Opus record held T1 v2's shams), not the 96 read here, so its D_net and free-rule rates rest on another comparison population; the registered numbers stand and these rates are not a calibration of the 96." if jn.startswith("Opus") else "Sonnet 5's comparison arms on the same 96 comparison applications read here."))
        L.append("- **Outcomes and D1:** " + "; ".join(f"{a} {X['d1'][a]['refused_or_errored']} refused or errored ({X['d1'][a]['share']:.3f}{', DEFECTIVE' if X['d1'][a]['defective'] else ''})" for a in X["d1"]) + ".\n")
    L.append("## The no-task marker at the unit level\n")
    L.append("| population | units | any edit: 0 / 1 / 2 / 3 / 4 / 5+ | applied lines: 0 / 1 / 2 / 3 |")
    L.append("|---|---|---|---|")
    for name, d in out["marker_unit_level"].items():
        ae = " / ".join(str(d["any_edit"].get(k, 0)) for k in ("0", "1", "2", "3", "4", "5+"))
        al = " / ".join(str(d["applied_lines_0_to_3"].get(str(k), 0)) for k in range(4)) if "applied_lines_0_to_3" in d else "—"
        L.append(f"| {name} | {d['n']} | {ae} | {al} |")
    d = out["dollars"]
    L.append(f"\n## Spend and scope\n\n- **Dollars:** nulls ${d['nulls']:.2f}, applications ${d['applications']:.2f}, total ${d['total']:.2f} against the estimate ${d['estimate_point_with_b1all']:.2f} with B1-all (${d['estimate_point']:.2f} without; cap ${d['cap']:.2f}; recorded across both caches ${d['recorded_across_caches']:.2f}, the smoke included).")
    L.append(f"- **Covered-lines sensitivity:** {out['covered_lines_sensitivity']}.")
    L.append(f"- **The scope sentence, as committed (v1.2 §7):** {out['scope_sentence']}\n")
    L.append("## The Codex round (brief 38 step 8; gpt-6.1-sol, high, read-only; `review/codex-phase-b-round1.md`)\n")
    L.append("Codex's verdict: the governing inconclusive and Sonnet 5's kill stand; the corrections below changed no reading the verdicts read.\n")
    L.append("| # | severity | point | disposition | change |")
    L.append("|---|---|---|---|---|")
    for c in out["codex_round_1"]:
        L.append(f"| {c['id']} | {c['severity']} | {c['point']} | {c['disposition']} | {c['change']} |")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(P / "phase-b-results.json"))
    ns = ap.parse_args(argv)
    out = run()
    p = Path(ns.out)
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    md = p.with_suffix(".md")
    md.write_text(write_md(out, p.name, sha256_file(p)), encoding="utf-8")
    keys = {j: {k: out["judges"][j][k] for k in ("verdict", "D_h", "D", "D_net", "r_minus_r_prime")} for j in out["judges"]}
    print("VERDICT", out["verdict"], json.dumps(keys))
    print(f"wrote {p} sha256 {sha256_file(p)[:16]}; {md.name} sha256 {sha256_file(md)[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
