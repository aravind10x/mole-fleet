#!/usr/bin/env python3
"""Brief 20 (B3 power simulation v3; $0): the stimulus set's moments, the score-unit margin m_s, the
simulation of brief 15 A6.3's two forms under A6.4's floors and A6.6's gates, and the estimate per layout.

Inputs are files already on disk and none is a B3 outcome: the rater key and the four pass files (scores
only; no reason is read into any output), the writer checks' replace-edit anchors (payload id and
statement number only), B1's and the T1 runs' per-plant lone scores and sealed rules, the seal's and
B1's null summaries, and the realised per-unit costs of B1, T1 v3, B4-R and brief 09's Sol check.
Counts, ids and aggregates only; no item text is read or printed.

The generative model (stated in full in the report): a triple's per-agent score on one plant is the
maximum of its three lines' judge visibilities, plus a composition term under the alternative, plus a
placement deviation and a call-level noise, clipped to 0..100 and rounded to the 5-point grid. A line's
visibility is a + b * (rho * z(rater line mean) + sqrt(1 - rho^2) * eta). Placements share the triple's
latent score with the stated ICC; the call noise is added on top. Each instrument's level and spread are
calibrated to B1's pooled non-alarming lone plants (planted-unit flag rate and score SD); the control
arm (v2's 24 same-shape sham payloads) to the sham lone plants (mean and SD); the honest path (the
author's honest pairs on other documents) is an independent Bernoulli read off the sham. Composition is
measured with the quiet set's test-retest noise: the true composition is drawn given the two-pass mean
at the Spearman-Brown reliability.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_b3_power_v3.py inputs --out-json V3.json
    work/mole-fork/.venv/bin/python -I work/checks/stage3_b3_power_v3.py simulate --inputs V3.json \\
        --out-json SIM.json [--workers 12]
    work/mole-fork/.venv/bin/python -I work/checks/stage3_b3_power_v3.py report --inputs V3.json \\
        --sim SIM.json --out-json power-simulation-v3.json --out-md power-simulation-v3.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from scipy import stats

SEED = 20261171
EXPERIMENTS = 300
REPLICATES = 1000
QUIET_BAR = 60.0
MARGIN = 0.3
LO_C, HI_C = 50.0, 75.0
WRITERS = ("sonnet55", "glm53")
ICCS = (0.3, 0.6)
NOISES = (0.0, 5.0, 10.0)
RHO = 0.5
REF_NOISE = 5.0
MULTIPLES = (1.5, 2.0)
NONCONV_MAX = 0.025  # O3's fallback when more bootstrap fits than the 2.5 percent tail fail with the document factor
LAYOUTS = {  # name: (placements of each quiet triple, singleton placements per line)
    "T1": (1, 0), "T2": (2, 0), "T1+S1": (1, 1), "T2+S1": (2, 1), "T1+S2": (1, 2), "T2+S2": (2, 2)}
INSTRUMENTS = (("dossier_iso", "opus48"), ("dossier_iso", "sonnet"), ("dossier_live", "opus48"),
               ("dossier_live", "sonnet"), ("P_author", "opus48"), ("P_author", "sonnet"))
N_SHAM = 24
N_CONTROLS = 22

RATER = "work/stage3/b3/rater"
CHECKS = {"sonnet55": "work/stage3/b3/checks-b3-sonnet55-rerun.json", "glm53": "work/stage3/b3/checks-b3-glm53.json"}
B1 = "work/stage3/b1/b1-results.json"
SEAL = "work/stage3/views/calibration-v1.json"
OPUS_NULL = "work/stage3/q1q2-synthetic/opus48/judge-null.json"
T1 = {"replant": "work/stage3/t1-replant/replant-results.json", "v2_sonnet": "work/stage3/t1v2/t1v2-results.json",
      "v2_opus48": "work/stage3/q1q2-synthetic/opus48/judge-results.json", "v3": "work/stage3/t1v3/t1v3-results.json"}
# Non-alarming lone regimes (A6.4) and the control arm (v2's 24 sham payloads, planted under v2 and the re-plant).
QUIET_REGIMES = (("v2", "conforming"), ("v3", "middle"), ("v3", "routine_redraw"), ("replant", "v1"))
SHAM_REGIMES = (("v2", "sham"), ("replant", "sham"))
B1_READING = {"dossier_iso": "isolated", "dossier_live": "live"}


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _scores(path, idk):
    out = {}
    for line in Path(path).read_text().splitlines():
        if line.strip():
            d = json.loads(line)
            out[d[idk]] = float(d["score"])
    return out


# ---------------------------------------------------------------- P1: the stimulus set

def load_stimuli(root: Path) -> list[dict]:
    """Every candidate triple (B3-D36 already excluded at stripping), keyed by (writer, id), with both passes'
    statement and composition scores, the document and the per-statement edit type (replace or append)."""
    r = root / RATER
    key = json.loads((r / "key-b3.json").read_text())
    s1, s2 = _scores(r / "ratings-b3-statements-p1.jsonl", "statement_id"), _scores(r / "ratings-b3-statements-p2.jsonl", "statement_id")
    t1, t2 = _scores(r / "ratings-b3-triples-p1.jsonl", "triple_id"), _scores(r / "ratings-b3-triples-p2.jsonl", "triple_id")
    replace = set()
    for w, f in CHECKS.items():
        d = json.loads((root / f).read_text())
        if d["payloads_sha256"] != key["sources"][f"candidates-{w}"]["sha256"]:
            raise ValueError(f"{f}: payload hash does not match the key's candidates-{w}")
        for a in d["anchors"]:
            if a["payload"].startswith("B3-D"):
                replace.add((w, a["payload"], int(a["statement"]) - 1))  # anchors number statements from 1
    lines: dict = {}
    for sid, v in key["statements"].items():
        if v["source"].startswith("candidates-"):
            lines.setdefault((v["writer"], v["id"]), {})[v["statement_index"]] = (s1[sid], s2[sid])
    out = []
    for tid, v in key["triples"].items():
        if not v["source"].startswith("candidates-"):
            continue
        k = (v["writer"], v["id"])
        L = lines[k]
        if sorted(L) != [0, 1, 2]:
            raise ValueError(f"{k}: statements {sorted(L)}")
        out.append({"writer": v["writer"], "id": v["id"], "document": v["document"],
                    "p1": [L[j][0] for j in range(3)], "p2": [L[j][1] for j in range(3)],
                    "c1": t1[tid], "c2": t2[tid], "replace": [int((k[0], k[1], j) in replace) for j in range(3)]})
    out.sort(key=lambda x: (WRITERS.index(x["writer"]), x["id"]))
    return out


def quiet(triples, rule="mean"):
    if rule == "mean":
        ok = lambda t: all((a + b) / 2 <= QUIET_BAR for a, b in zip(t["p1"], t["p2"]))
    elif rule == "pass1":
        ok = lambda t: all(a <= QUIET_BAR for a in t["p1"])
    elif rule == "both":
        ok = lambda t: all(a <= QUIET_BAR and b <= QUIET_BAR for a, b in zip(t["p1"], t["p2"]))
    else:
        raise ValueError(rule)
    return [t for t in triples if ok(t)]


def design(Q: list[dict]) -> dict:
    """Arrays of the fixed design: rater line means, composition (two-pass mean and both passes), writer,
    replace share, document index."""
    docs = sorted({t["document"] for t in Q})
    r = np.array([[(a + b) / 2 for a, b in zip(t["p1"], t["p2"])] for t in Q])
    return {"r": r, "C": np.array([(t["c1"] + t["c2"]) / 2 for t in Q]), "c1": np.array([t["c1"] for t in Q]),
            "c2": np.array([t["c2"] for t in Q]), "sonnet": np.array([t["writer"] == "sonnet55" for t in Q], float),
            "edit": np.array([sum(t["replace"]) / 3 for t in Q]), "doc": np.array([docs.index(t["document"]) for t in Q]),
            "docs": docs}


def spearman_brown(r: float) -> float:
    return 2 * r / (1 + r)


def top_two_gap(x: np.ndarray) -> np.ndarray:
    s = np.sort(x, axis=-1)
    return s[..., -1] - s[..., -2]


def _residual(y, Z):
    beta, *_ = np.linalg.lstsq(Z, y, rcond=None)
    return y - Z @ beta


def rater_covariates(D) -> np.ndarray:
    """The covariates of form (b) without the singleton arm: intercept, rater top line, rater top-two gap,
    writer, replace share, document dummies."""
    n = len(D["C"])
    doc = np.eye(len(D["docs"]))[D["doc"]][:, 1:]
    return np.column_stack([np.ones(n), D["r"].max(1), top_two_gap(D["r"]), D["sonnet"], D["edit"], doc])


def moments(triples: list[dict]) -> dict:
    Q = quiet(triples)
    D = design(Q)
    C, r = D["C"], D["r"]
    q = lambda v, p: float(np.quantile(v, p))  # numpy's default: linear interpolation (A6.11)
    top, spread = r.max(1), r.max(1) - r.min(1)
    rr = float(np.corrcoef(D["c1"], D["c2"])[0, 1])
    Z = rater_covariates(D)
    e1, e2 = _residual(D["c1"], Z), _residual(D["c2"], Z)
    r_res = float(np.corrcoef(e1, e2)[0, 1])
    sp = lambda a, b: float(stats.spearmanr(a, b).statistic)
    by_w = {w: [t for t in Q if t["writer"] == w] for w in WRITERS}
    all_by_w = {w: [t for t in triples if t["writer"] == w] for w in WRITERS}
    hi = C >= 75
    return {
        "n_candidates": len(triples), "n_candidates_by_writer": {w: len(v) for w, v in all_by_w.items()},
        "quiet_rule": "every statement's two-pass mean at or under 60 (A6.2)",
        "n_quiet": len(Q), "n_quiet_by_writer": {w: len(v) for w, v in by_w.items()},
        "n_quiet_sensitivity": {"pass1_only": len(quiet(triples, "pass1")), "both_passes": len(quiet(triples, "both"))},
        "n_quiet_sensitivity_by_writer": {rule: {w: sum(t["writer"] == w for t in quiet(triples, rule)) for w in WRITERS}
                                          for rule in ("pass1", "both")},
        "composition": {"q1": q(C, .25), "median": q(C, .5), "q3": q(C, .75), "p90": q(C, .9), "min": float(C.min()),
                        "max": float(C.max()), "mean": float(C.mean()), "sd": float(C.std(ddof=1)),
                        "n_ge_75": int(hi.sum()), "n_ge_70": int((C >= 70).sum()), "n_le_50": int((C <= 50).sum()),
                        "n_ge_75_by_writer": {w: int(sum(1 for t, c in zip(Q, C) if c >= 75 and t["writer"] == w)) for w in WRITERS},
                        "sonnet_share_ge_75": float(D["sonnet"][hi].mean()) if hi.any() else None,
                        "by_writer": {w: {"n": len(v), "median": q([(t["c1"] + t["c2"]) / 2 for t in v], .5),
                                          "mean": float(np.mean([(t["c1"] + t["c2"]) / 2 for t in v]))} for w, v in by_w.items()}},
        "test_retest": {"pearson_pass1_pass2": rr, "spearman_brown": spearman_brown(rr),
                        "pass_diff_sd": float(np.std(D["c1"] - D["c2"], ddof=1)),
                        "partial": {"covariates": "rater top line, rater top-two gap, writer, replace share, document",
                                    "pearson_of_residuals": r_res, "spearman_brown": spearman_brown(r_res)}},
        "correlations": {"pearson_comp_top": float(np.corrcoef(C, top)[0, 1]), "spearman_comp_top": sp(C, top),
                         "pearson_comp_spread": float(np.corrcoef(C, spread)[0, 1]), "spearman_comp_spread": sp(C, spread),
                         "pearson_comp_gap": float(np.corrcoef(C, top_two_gap(r))[0, 1]),
                         "pearson_comp_mean_line": float(np.corrcoef(C, r.mean(1))[0, 1])},
        "top_line": {"mean": float(top.mean()), "mean_at_comp_ge_70": float(top[C >= 70].mean()),
                     "mean_at_comp_ge_75": float(top[hi].mean()), "sd": float(top.std(ddof=1)),
                     "gap_mean": float(top_two_gap(r).mean()), "spread_mean": float(spread.mean())},
        "edit_type": {w: {"statements": 3 * len(v), "replace": sum(sum(t["replace"]) for t in v),
                          "replace_share": sum(sum(t["replace"]) for t in v) / (3 * len(v)) if v else None,
                          "triples_by_n_replace": {str(k): sum(sum(t["replace"]) == k for t in v) for k in range(4)}}
                      for w, v in by_w.items()},
        "edit_type_all_candidates": {w: sum(sum(t["replace"]) for t in v) for w, v in all_by_w.items()},
        "documents": {d: int((D["doc"] == i).sum()) for i, d in enumerate(D["docs"])},
    }


# ---------------------------------------------------------------- B1 / T1 priors and P2

def expected_flag(x, t, p_tie):
    x = np.asarray(x, float)
    return np.where(x > t, 1.0, np.where(x == t, p_tie, 0.0))


def _lone(pus: dict) -> list[dict]:
    out = []
    for k, ents in pus.items():
        if not k.endswith(":lone"):
            continue
        if len(ents) != 1 or ents[0].get("outcome") != "scored":
            raise ValueError(f"lone plant {k}: {len(ents)} entries, outcome {ents[0].get('outcome')}")
        e = ents[0]
        hon = max(e["honest_other_pairs"].values()) if e["honest_other_pairs"] else -1.0
        out.append({"plant": k, "score": float(e["score"]), "union_max": float(e["union_max"]), "honest_max": float(hon)})
    return out


def load_instrument(root: Path, view: str, judge: str) -> dict:
    """Per-plant lone scores by regime, the sealed author rule and the null summary, from blue result files."""
    plants: dict = {}
    if view.startswith("dossier"):
        b1 = json.loads((root / B1).read_text())
        rd = b1["judges"][judge]["readings"][B1_READING[view]]
        rule = rd["author_rule"]
        null = rd["null_summary"]
        null_src = f"{B1} judges.{judge}.readings.{B1_READING[view]}.null_summary"
        for planting, regime in QUIET_REGIMES + SHAM_REGIMES:
            plants[f"{planting}:{regime}"] = _lone(rd["plantings"][planting]["planted_unit_scores"][regime])
        src = B1
    else:
        rules = []
        for planting, regime in QUIET_REGIMES + SHAM_REGIMES:
            if planting == "replant":
                f = T1["replant"]; R = json.loads((root / f).read_text())["judges"][judge]["regimes"]
            elif planting == "v3":
                f = T1["v3"]; R = json.loads((root / f).read_text())["judges"][judge]["regimes"]
            elif judge == "sonnet":
                f = T1["v2_sonnet"]; R = json.loads((root / f).read_text())["regimes"]
            else:
                f = T1["v2_opus48"]; R = json.loads((root / f).read_text())["opus_full"]["regimes"]
            pa = R[regime]["P_author"]
            rules.append((pa["author_rule"]["threshold"], pa["author_rule"]["p_tie"]))
            plants[f"{planting}:{regime}"] = _lone(pa["planted_unit_scores"])
        if len(set(rules)) != 1:
            raise ValueError(f"P_author {judge}: rules differ across files {set(rules)}")
        rule = {"threshold": rules[0][0], "p_tie": rules[0][1]}
        if judge == "sonnet":
            null = json.loads((root / SEAL).read_text())["views"]["P_author"]["summary"]
            null_src = f"{SEAL} views.P_author.summary"
        else:
            null = json.loads((root / OPUS_NULL).read_text())["views"]["P_author"]["summary"]
            null_src = f"{OPUS_NULL} views.P_author.summary"
        src = "T1 replant, v2 and v3 results"
    return {"view": view, "judge": judge, "t": float(rule["threshold"]), "p_tie": float(rule["p_tie"]),
            "null": {"median": float(null["median"]), "p95": float(null["p95"]), "n": int(null["n"]), "source": null_src},
            "plants": plants, "source": src}


def margin_ms(scores, t, null_median, null_p95, target=MARGIN):
    """A6.4: the smallest D with P(t - D < s <= t) >= target over the reference lone plants (read with the lower
    end closed, so D is attained: the interval [t - D, t] holds at least ceil(target * n) plants); fallback
    target * (null p95 - median) when fewer than that share of the plants sit at or below t."""
    s = np.sort(np.asarray(scores, float))
    n = len(s)
    need = math.ceil(target * n - 1e-9)
    below = s[s <= t][::-1]
    if len(below) >= need and need > 0:
        return {"m_s": float(t - below[need - 1]), "rule": "A6.4 primary: smallest D with P(t - D <= s <= t) >= 0.3",
                "n": n, "n_at_or_below_t": int(len(below)), "need": need}
    return {"m_s": float(target * (null_p95 - null_median)), "rule": "A6.4 fallback: 0.3 x (honest null p95 - median)",
            "n": n, "n_at_or_below_t": int(len(below)), "need": need}


def margin_exact(plants, t, p_tie, target=MARGIN):
    """Beside: the smallest uniform shift D of the planted-unit score that raises the sealed-rule flag rate (the
    union with the author's unshifted honest pairs, ties at p_tie) by at least target; None when no D does."""
    s = np.array([p["score"] for p in plants]); h = np.array([p["honest_max"] for p in plants])
    base = expected_flag(np.maximum(s, h), t, p_tie).mean()
    cands = sorted({max(0.0, t - x) for x in s} | {max(0.0, t - x) + 1e-6 for x in s})
    for D in cands:
        if expected_flag(np.maximum(s + D, h), t, p_tie).mean() - base >= target - 1e-12:
            return {"D": round(D, 6), "base_rate": float(base)}
    return {"D": None, "base_rate": float(base)}


def summarise_plants(plants, t, p_tie) -> dict:
    s = np.array([p["score"] for p in plants]); u = np.array([p["union_max"] for p in plants])
    return {"n": len(plants), "mean": float(s.mean()), "sd": float(s.std(ddof=1)), "median": float(np.median(s)),
            "planted_unit_rate": float(expected_flag(s, t, p_tie).mean()), "recall": float(expected_flag(u, t, p_tie).mean())}


def instrument_inputs(inst: dict) -> dict:
    t, pt = inst["t"], inst["p_tie"]
    qp = [p for k in QUIET_REGIMES for p in inst["plants"][f"{k[0]}:{k[1]}"]]
    sp = [p for k in SHAM_REGIMES for p in inst["plants"][f"{k[0]}:{k[1]}"]]
    quiet_s, sham_s = summarise_plants(qp, t, pt), summarise_plants(sp, t, pt)
    h = 1 - (1 - sham_s["recall"]) / max(1 - sham_s["planted_unit_rate"], 1e-9)
    ms = margin_ms([p["score"] for p in qp], t, inst["null"]["median"], inst["null"]["p95"])
    return {"view": inst["view"], "judge": inst["judge"], "t": t, "p_tie": pt, "null": inst["null"],
            "by_regime": {f"{a}:{b}": summarise_plants(inst["plants"][f"{a}:{b}"], t, pt) for a, b in QUIET_REGIMES + SHAM_REGIMES},
            "quiet_prior": quiet_s, "sham_prior": sham_s, "honest_path": float(max(h, 0.0)),
            "m_s": ms, "m_s_exact_beside": margin_exact(qp, t, pt),
            "m_s_fallback_value": float(MARGIN * (inst["null"]["p95"] - inst["null"]["median"])),
            "source": inst["source"]}


# ---------------------------------------------------------------- the generative model

def to_grid(x):
    return np.clip(np.round(np.asarray(x) / 5.0) * 5.0, 0.0, 100.0)


def flag_prob_latent(T, sig_w, t, p_tie):
    """P(the grid score of T + N(0, sig_w^2) is flagged by the rule s > t, ties at t with p_tie)."""
    g = 5.0 * math.floor(t / 5.0) + 5.0  # the smallest grid value above t
    p = stats.norm.sf((g - 2.5 - T) / sig_w) if g <= 100 else np.zeros_like(T)
    if abs(t / 5.0 - round(t / 5.0)) < 1e-9 and p_tie > 0:
        p = p + p_tie * (stats.norm.sf((t - 2.5 - T) / sig_w) - stats.norm.sf((t + 2.5 - T) / sig_w))
    return p


def _solve(f, lo, hi, target, iters=60):
    """Bisection for an increasing f with a bracket check: returns (x, status). When the target lies outside
    [f(lo), f(hi)] the nearest end is returned with status 'at_lower_end' or 'at_upper_end' (the closest attainable
    value), never a silent drift to an arbitrary end."""
    flo, fhi = f(lo), f(hi)
    if target <= flo:
        return lo, ("ok" if math.isclose(target, flo, rel_tol=1e-9, abs_tol=1e-12) else "at_lower_end")
    if target >= fhi:
        return hi, ("ok" if math.isclose(target, fhi, rel_tol=1e-9, abs_tol=1e-12) else "at_upper_end")
    for _ in range(iters):
        mid = (lo + hi) / 2
        if f(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, "ok"


def line_latent(rng, x, rho, n):
    """Judge line visibilities, standardised: rho * x + sqrt(1 - rho^2) * eta, n worlds."""
    eta = rng.standard_normal((n,) + x.shape)
    return rho * x[None] + math.sqrt(1 - rho * rho) * eta


def calibrate(D, inp, icc, noise, rho=RHO, n_cal=400, seed=SEED):
    """Level a and scale (via the latent SD) of the quiet triples' per-agent score so that under the null the
    planted-unit flag rate and the grid SD match the pooled non-alarming lone plants; the control arm's mean
    and SD match the sham lone plants. Returns the DGP parameters."""
    rng = np.random.default_rng([seed, 1])
    r = D["r"]; x = (r - r.mean()) / r.std()
    lat = line_latent(rng, x, rho, n_cal)
    mx = lat.max(-1); mx_c = mx - mx.mean()
    v_mx = float(mx.var())
    Nw = rng.standard_normal(mx.shape)
    t, pt = inp["t"], inp["p_tie"]
    tgt_rate, tgt_sd = inp["quiet_prior"]["planted_unit_rate"], inp["quiet_prior"]["sd"]

    def parts(s_lat):
        vb = icc * max(s_lat ** 2 - noise ** 2, 1e-6)
        return math.sqrt(vb / v_mx), math.sqrt(max(s_lat ** 2 - vb, 1e-9))

    def level_for(s_lat):
        b, sw = parts(s_lat)
        rate = lambda a: float(flag_prob_latent(a + b * mx_c, sw, t, pt).mean())
        tr = min(max(tgt_rate, 1e-3), 0.999)
        return _solve(rate, -150.0, 250.0, tr)

    def grid_sd(s_lat):
        b, sw = parts(s_lat)
        a, _ = level_for(s_lat)
        return float(to_grid(a + b * mx_c + sw * Nw).std())

    lo_s = max(noise + 0.5, 2.0)
    status = {}
    s_lat, status["quiet_sd"] = _solve(grid_sd, lo_s, 120.0, tgt_sd, iters=40)
    b, sw = parts(s_lat); a, status["quiet_rate"] = level_for(s_lat)
    sz = math.sqrt(max(sw ** 2 - noise ** 2, 0.0))
    g = to_grid(a + b * mx_c + sw * Nw)
    # control arm: latent N(mu, vb) per sham triple, within noise per plant
    Ns1, Ns2 = rng.standard_normal(20000), rng.standard_normal(20000)
    tm, ts = inp["sham_prior"]["mean"], inp["sham_prior"]["sd"]

    def sham_parts(s_lat_s):
        vb = icc * max(s_lat_s ** 2 - noise ** 2, 1e-6)
        return math.sqrt(vb), math.sqrt(max(s_lat_s ** 2 - vb, 1e-9))

    def sham_mu(s_lat_s):
        sb, sws = sham_parts(s_lat_s)
        return _solve(lambda m: float(to_grid(m + sb * Ns1 + sws * Ns2).mean()), -150.0, 150.0, tm, iters=40)

    def sham_sd(s_lat_s):
        sb, sws = sham_parts(s_lat_s)
        return float(to_grid(sham_mu(s_lat_s)[0] + sb * Ns1 + sws * Ns2).std())

    s_lat_s, status["sham_sd"] = _solve(sham_sd, lo_s, 120.0, ts, iters=30)
    sb, sws = sham_parts(s_lat_s); mu_s, status["sham_mean"] = sham_mu(s_lat_s)
    gs = to_grid(mu_s + sb * Ns1 + sws * Ns2)
    ach = {"quiet_rate": float(flag_prob_latent(a + b * mx_c, sw, t, pt).mean()), "quiet_grid_sd": float(g.std()),
           "quiet_grid_mean": float(g.mean()), "sham_grid_mean": float(gs.mean()), "sham_grid_sd": float(gs.std()),
           "sham_rate": float(flag_prob_latent(mu_s + sb * Ns1, sws, t, pt).mean())}
    targets = {"quiet_rate": tgt_rate, "quiet_grid_sd": tgt_sd, "sham_grid_mean": tm, "sham_grid_sd": ts,
               "sham_rate": inp["sham_prior"].get("planted_unit_rate")}
    tol = {"quiet_rate": 0.01, "quiet_grid_sd": 0.5, "sham_grid_mean": 0.5, "sham_grid_sd": 0.5}
    misses = {k: {"target": targets[k], "achieved": ach[k]} for k in tol if abs(ach[k] - targets[k]) > tol[k]}
    return {"a": a, "b": b, "mx_mean": float(mx.mean()), "sig_z": sz, "sig_c": noise, "sig_w": sw, "s_lat": s_lat,
            "rho": rho, "icc": icc, "t": t, "p_tie": pt, "h": inp["honest_path"],
            "sham_mu": mu_s, "sham_sd_between": sb, "sham_sig_z": math.sqrt(max(sws ** 2 - noise ** 2, 0.0)),
            "achieved": ach, "targets": targets, "status": status, "misses": misses}


def true_contrast(D, dgp, beta, rho=RHO, n=400, seed=SEED, c_hi=HI_C, c_lo=LO_C):
    """The true lone flag contrast, composition set to c_hi against c_lo for every quiet triple, averaged over the
    design and the judge's line draws, honest path included."""
    rng = np.random.default_rng([seed, 2])
    r = D["r"]; x = (r - r.mean()) / r.std()
    mx = line_latent(rng, x, rho, n).max(-1)
    T = dgp["a"] + dgp["b"] * (mx - dgp["mx_mean"])
    m = D["C"].mean(); h = dgp["h"]
    pf = lambda c: 1 - (1 - h) * (1 - flag_prob_latent(T + beta * (c - m), dgp["sig_w"], dgp["t"], dgp["p_tie"]))
    return float((pf(c_hi) - pf(c_lo)).mean())


def true_contrast_conditional(D, dgp, beta, c_hi=HI_C, c_lo=LO_C):
    """Primary truth for form (b), matched to O2's estimand: the lone flag probability with the judge's true line
    maximum held at its mean, composition set to c_hi against c_lo, honest path included."""
    m, h = D["C"].mean(), dgp["h"]
    pf = lambda c: 1 - (1 - h) * (1 - flag_prob_latent(np.array([dgp["a"] + beta * (c - m)]), dgp["sig_w"], dgp["t"], dgp["p_tie"]))
    return float((pf(c_hi) - pf(c_lo))[0])


def beta_for_contrast(D, dgp, target=MARGIN, rho=RHO, kind="conditional"):
    f = (lambda b: true_contrast_conditional(D, dgp, b)) if kind == "conditional" else (lambda b: true_contrast(D, dgp, b, rho))
    hi = 1.0
    while f(hi) < target and hi < 1e3:
        hi *= 2
    if f(hi) < target:
        return None
    return _solve(f, 0.0, hi, target, iters=50)[0]


def observable_slope_a(D, dgp, beta, Q=1, n_worlds=200, seed=SEED):
    """Form (a)'s truth: the error-free population value of form (a)'s own coefficient. Excess (a triple's grid score
    minus the maximum of its lines' mean grid scores over Q singleton placements) is regressed, as form (a) is fitted,
    on the TRUE composition with the top-two singleton gap, writer, replace share and document; the coefficient at
    beta minus at 0 (the null part is the max-of-three bias, read separately). The grid clips and rounds, so a latent
    shift of beta per point shows as a smaller slope near the ends of the scale. Common random numbers across beta."""
    rng = np.random.default_rng([seed, 3, Q])
    r = D["r"]; x = (r - r.mean()) / r.std(); n = len(D["C"])
    L = dgp["a"] + dgp["b"] * (line_latent(rng, x, dgp["rho"], n_worlds) - dgp["mx_mean"])
    M = L.max(-1)
    lam = D["partial_rel"]
    Ct = D["C_fit"] + lam * D["C_res"] + math.sqrt(lam * (1 - lam) * D["C_res_var"]) * rng.standard_normal((n_worlds, n))
    w = dgp["sig_w"] * rng.standard_normal((n_worlds, n))
    sing = to_grid(L[..., None] + dgp["sig_w"] * rng.standard_normal(L.shape + (Q,))).mean(-1)
    smax, gap = sing.max(-1), top_two_gap(sing)
    docd = np.eye(len(D["docs"]))[D["doc"]][:, 1:]
    Z = np.tile(np.column_stack([D["sonnet"], D["edit"], docd]), (n_worlds, 1))
    X = np.column_stack([np.ones(n_worlds * n), Ct.ravel(), gap.ravel(), Z])
    m = D["C_center"]

    def slope(b):
        y = (to_grid(M + b * (Ct - m) + w) - smax).ravel()
        return float(np.linalg.lstsq(X, y, rcond=None)[0][1])
    return slope(beta) - slope(0.0)


def beta_for_slope(D, dgp, target_slope, Q=1, cap=50.0):
    """The latent beta whose form-(a) population coefficient (observable_slope_a) equals target_slope; None when the
    0..100 scale cannot show it (the coefficient saturates below the target for every beta up to cap times it)."""
    f = lambda b: observable_slope_a(D, dgp, b, Q)
    hi = max(target_slope, 1e-3)
    while f(hi) < target_slope and hi < cap * target_slope:
        hi *= 1.5
    if f(hi) < target_slope:
        return None
    return _solve(f, 0.0, hi, target_slope, iters=40)[0]


# ---------------------------------------------------------------- estimation

def four_outcome(lo, hi, point, margin):
    if lo <= 0 and hi < margin:
        return "excluded"
    if lo > 0 and point < margin:
        return "attenuated"
    if lo > 0 and point >= margin:
        return "present"
    return "inconclusive"


def irls(X, y, w, beta0=None, iters=30, tol=1e-7, ridge=1e-8, max_step=4.0, firth=False):
    """Batched weighted logistic regression. X (n, k), y (n,), w (R, n) frequency weights. Returns beta (R, k)
    and a converged mask (R,). firth=True maximises the Firth-penalised likelihood (log L + 1/2 log det I): the
    score gains h_i (1/2 - p_i), h the hat diagonal w_i p_i (1 - p_i) x_i' I^-1 x_i, and the estimate stays
    finite under separation (A6.13.5)."""
    R, k = w.shape[0], X.shape[1]
    beta = np.zeros((R, k)) if beta0 is None else np.broadcast_to(beta0, (R, k)).copy()
    conv = np.zeros(R, bool)
    eye = ridge * np.eye(k)
    for _ in range(iters):
        eta = np.clip(beta @ X.T, -35, 35)
        p = 1 / (1 + np.exp(-eta))
        W = w * p * (1 - p)
        H = np.matmul((W[:, :, None] * X[None]).transpose(0, 2, 1), X) + eye
        if firth:
            Hinv = np.linalg.inv(H)
            hat = W * np.einsum("nk,rkj,nj->rn", X, Hinv, X)
            g = (w * (y[None] - p) + hat * (0.5 - p)) @ X
            full = np.clip(np.einsum("rkj,rj->rk", Hinv, g), -max_step, max_step)
            # step halving on the penalised log-likelihood: undamped Fisher scoring can oscillate (a sparse document)
            ll0, t = _firth_loglik(X, y, w, beta, eye), np.ones(R)
            for _ in range(30):
                bad = _firth_loglik(X, y, w, beta + t[:, None] * full, eye) < ll0 - 1e-12
                if not bad.any():
                    break
                t = np.where(bad, t / 2, t)
            beta = beta + t[:, None] * full
            conv = np.abs(full).max(1) < tol
            if conv.all():
                break
            continue
        else:
            g = (w * (y[None] - p)) @ X
            step = np.linalg.solve(H, g[..., None])[..., 0]
        step = np.clip(step, -max_step, max_step)
        beta = beta + step
        conv = np.abs(step).max(1) < tol
        if conv.all():
            break
    return beta, conv & (np.abs(beta).max(1) < 25)


def _firth_loglik(X, y, w, beta, eye):
    """The Firth-penalised log-likelihood per replicate: sum w (y eta - log(1 + e^eta)) + 1/2 log det I(beta)."""
    eta = np.clip(beta @ X.T, -35, 35)
    p = 1 / (1 + np.exp(-eta))
    W = w * p * (1 - p)
    H = np.matmul((W[:, :, None] * X[None]).transpose(0, 2, 1), X) + eye
    return (w * (y[None] * eta - np.logaddexp(0.0, eta))).sum(1) + 0.5 * np.linalg.slogdet(H)[1]


def sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -35, 35)))


def bootstrap_weights(rng, n, R, strata=None):
    if strata is None:
        idx = rng.integers(0, n, (R, n))
    else:
        idx = np.empty((R, n), int)
        pos = 0
        for s in np.unique(strata):
            members = np.flatnonzero(strata == s)
            idx[:, pos:pos + len(members)] = members[rng.integers(0, len(members), (R, len(members)))]
            pos += len(members)
    w = np.zeros((R, n))
    np.add.at(w, (np.repeat(np.arange(R), n), idx.ravel()), 1.0)
    return w


def _std_cols(M):
    mu, sd = M.mean(0), M.std(0)
    sd[sd == 0] = 1.0
    return mu, sd


def reliability_given(c1, c2, Z):
    """A6.5 (ii): the Spearman-Brown reliability of the two-pass mean's residual on the covariates Z (the
    correlation of the two passes' residuals, stepped up)."""
    r = float(np.corrcoef(_residual(c1, Z), _residual(c2, Z))[0, 1])
    return spearman_brown(r)


def too_many_failures(converged) -> bool:
    """O3 and the unfit rule: more than NONCONV_MAX of the replicates failed, counted in whole replicates."""
    return int((~np.asarray(converged)).sum()) > NONCONV_MAX * len(converged)


def valid_rel(x):
    return x is not None and np.isfinite(x) and 0 < x <= 1


def _verdict(point, boot, ok, margin, state=None):
    """One reading from a point estimate and its bootstrap draws. A failed fit is 'unfit' (not read), never a verdict;
    `state` (e.g. 'ceiling') marks a reading the rules do not read, with its interval kept for the record."""
    if not ok:
        return {"point": point, "lo": None, "hi": None, "outcome": state or "unfit"}
    if state:
        lo, hi = np.percentile(boot, [2.5, 97.5])
        return {"point": point, "lo": float(lo), "hi": float(hi), "outcome": state}
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"point": point, "lo": float(lo), "hi": float(hi), "outcome": four_outcome(lo, hi, point, margin)}


def form_b(rng, C, line, gap, sonnet, edit, doc, F, P, R, q1q3, c12=None, firth=False, ceiling_hit=False):
    """Form (b): logistic regression of the plant-level flag on composition, the line covariate, the top-two gap,
    writer, replace share and document; contrast at 75 against 50 (and Q3 against Q1), standardised over the
    sample's writer and document composition with the continuous covariates at their sample means;
    payload-clustered percentile bootstrap. Falls back to the document-stratified bootstrap without the
    document factor when the full model does not converge on the sample or in more than NONCONV_MAX of the
    bootstrap replicates (O3). The fit used is 'unfit' (no verdict) when its point fit fails or more than
    NONCONV_MAX of its replicates fail; otherwise the interval is read on the converged replicates. Beside: O4's
    contrast with the line covariate and the gap at their conditional means given composition, and A6.5's
    disattenuated contrast (the composition coefficient divided by the partial reliability given the covariates)."""
    n = len(C)
    rep = lambda v: np.repeat(v, P, axis=0)
    cont = np.column_stack([C, line, gap, edit])
    mu, sd = _std_cols(cont)
    Zc = (cont - mu) / sd
    docd = np.eye(int(doc.max()) + 1)[doc][:, 1:]

    def build(with_doc):
        cols = [np.ones(n), Zc[:, 0], Zc[:, 1], Zc[:, 2], sonnet, Zc[:, 3]] + ([docd] if with_doc else [])
        return np.column_stack(cols)

    y = F.ravel()  # rows: triple-major, placements within
    out = {"fallback_reason": None}
    for with_doc in (True, False):
        X = rep(build(with_doc))
        b0, c0 = irls(X, y, np.ones((1, n * P)), firth=firth)
        # O3 read for a bootstrapped fit: the model "does not converge with" the document factor when the point fit
        # fails or more replicates fail than the percentile interval's tail mass; separated replicates otherwise
        # throw arbitrary contrasts into the interval's tails
        if with_doc and not c0[0]:
            out["fallback_reason"] = "point"
            continue
        wt = bootstrap_weights(rng, n, R, None if with_doc else doc)
        bb, cb = irls(X, y, np.repeat(wt, P, axis=1), beta0=b0[0], firth=firth)
        if with_doc and too_many_failures(cb):
            out["fallback_reason"] = "bootstrap"
            continue
        break
    out["doc_factor"] = bool(with_doc)
    out["point_converged"] = bool(c0[0])
    out["boot_nonconverged"] = float(1 - cb.mean())
    ok = bool(c0[0]) and not too_many_failures(cb)
    out["fit_ok"] = ok
    out["ceiling"] = bool(ceiling_hit)
    st = "ceiling" if ceiling_hit else None  # A6.13.5: a cell whose quiet lone recall exceeds the ceiling is not read on (b)
    bbc = bb[cb] if cb.any() else bb
    Xb = build(with_doc)
    Zrel = np.column_stack([np.ones(n), line, gap, sonnet, edit] + ([docd] if with_doc else []))
    rel = reliability_given(c12[0], c12[1], Zrel) if c12 is not None else None
    sb = spearman_brown(float(np.corrcoef(c12[0], c12[1])[0, 1])) if c12 is not None else None
    out["partial_rel_measured"] = rel
    # O4: the line covariate and the gap at their conditional means given composition (linear in C)
    lc = np.linalg.lstsq(np.column_stack([np.ones(n), C]), np.column_stack([line, gap]), rcond=None)[0]

    def predict(beta, c, cond=None):
        """cond: None (line and gap at their sample means, O2), 'line' (the line covariate at its conditional mean
        given composition, O4) or 'joint' (line and gap both at their conditional means)."""
        Xe = Xb.copy()
        Xe[:, 1] = (c - mu[0]) / sd[0]
        lg = np.array([1.0, c]) @ lc
        Xe[:, 2] = (lg[0] - mu[1]) / sd[1] if cond in ("line", "joint") else 0.0
        Xe[:, 3] = (lg[1] - mu[2]) / sd[2] if cond == "joint" else 0.0
        Xe[:, 5] = 0.0
        return sigmoid(beta @ Xe.T).mean(-1)

    def contrast(beta, chi, clo, cond=None):
        return predict(beta, chi, cond) - predict(beta, clo, cond)

    def disatt(beta, factor):
        d = beta.copy(); d[..., 1] = d[..., 1] / factor
        return d

    qm = MARGIN * (q1q3[1] - q1q3[0]) / 25
    out["75v50"] = _verdict(float(contrast(b0, HI_C, LO_C)[0]), contrast(bbc, HI_C, LO_C), ok, MARGIN, state=st)
    out["q3vq1"] = _verdict(float(contrast(b0, q1q3[1], q1q3[0])[0]), contrast(bbc, q1q3[1], q1q3[0]), ok, qm, state=st)
    out["75v50_o4"] = _verdict(float(contrast(b0, HI_C, LO_C, "line")[0]), contrast(bbc, HI_C, LO_C, "line"), ok, MARGIN, state=st)
    out["75v50_o4_joint"] = _verdict(float(contrast(b0, HI_C, LO_C, "joint")[0]), contrast(bbc, HI_C, LO_C, "joint"), ok, MARGIN, state=st)
    # A6.5 (ii): a log-odds-slope sensitivity, conditional on the estimated reliability (held fixed across replicates)
    if valid_rel(rel):
        out["75v50_disatt"] = _verdict(float(contrast(disatt(b0, rel), HI_C, LO_C)[0]), contrast(disatt(bbc, rel), HI_C, LO_C), ok, MARGIN, state=st)
    if valid_rel(sb):
        out["75v50_disatt_sb"] = _verdict(float(contrast(disatt(b0, sb), HI_C, LO_C)[0]), contrast(disatt(bbc, sb), HI_C, LO_C), ok, MARGIN, state=st)
    p75 = predict(bbc, HI_C)
    out["width_at_75"] = float(np.subtract(*np.percentile(p75, [97.5, 2.5]))) if ok else None
    return out


def form_a(rng, C, gap, sonnet, edit, doc, excess, R, m_s, q1q3, wt=None, c12=None):
    """Form (a): OLS of excess (mean triple score over placements minus the maximum of the lines' mean singleton
    scores) on composition, the top-two singleton gap, writer, replace share and document; slope x 25 against
    m_s; payload-clustered percentile bootstrap (one row per triple). Beside: A6.5's disattenuated slope (divided
    by the partial reliability of composition given these covariates)."""
    n = len(C)
    docd = np.eye(int(doc.max()) + 1)[doc][:, 1:]
    X = np.column_stack([np.ones(n), C, gap, sonnet, edit, docd])
    beta = np.linalg.lstsq(X, excess, rcond=None)[0]
    if wt is None:
        wt = bootstrap_weights(rng, n, R)
    XtWX = np.matmul((wt[:, :, None] * X[None]).transpose(0, 2, 1), X) + 1e-9 * np.eye(X.shape[1])
    XtWy = (wt * excess[None]) @ X
    bb = np.linalg.solve(XtWX, XtWy[..., None])[..., 0]
    rel = reliability_given(c12[0], c12[1], np.column_stack([np.ones(n), gap, sonnet, edit, docd])) if c12 is not None else None
    sb = spearman_brown(float(np.corrcoef(c12[0], c12[1])[0, 1])) if c12 is not None else None
    out = {"fit_ok": True, "partial_rel_measured": rel}
    qs = q1q3[1] - q1q3[0]
    out["75v50"] = _verdict(float(beta[1] * 25), bb[:, 1] * 25, True, m_s)
    out["q3vq1"] = _verdict(float(beta[1] * qs), bb[:, 1] * qs, True, m_s * qs / 25)
    if valid_rel(rel):
        out["75v50_disatt"] = _verdict(float(beta[1] * 25 / rel), bb[:, 1] * 25 / rel, True, m_s)
    if valid_rel(sb):
        out["75v50_disatt_sb"] = _verdict(float(beta[1] * 25 / sb), bb[:, 1] * 25 / sb, True, m_s)
    xe = np.concatenate([[1.0, HI_C], X[:, 2:].mean(0)])
    pe = bb @ xe
    out["width_at_75"] = float(np.subtract(*np.percentile(pe, [97.5, 2.5])))
    return out


def clustered_mean_ci(w, v):
    """w (R, n_clusters), v (n_clusters, P) -> percentile interval of the plant mean."""
    m = (w @ v.sum(1)) / (w.sum(1) * v.shape[1])
    return np.percentile(m, [2.5, 97.5])


def auroc_matrix(a, b):
    return (a[:, None] > b[None, :]) + 0.5 * (a[:, None] == b[None, :])


def experiment(rng, D, dgp, layout, beta, m_s, q1q3, R=REPLICATES, forms=("a", "b"), tail_copies=None,
               firth=False, ceiling=None, shared=None):
    """One simulated planting. firth and ceiling (A6.13.5) apply to form (b); shared supplies the draws two
    instruments have in common when they read the same plants (true composition 'Ct', the judge's standardised
    line deviations 'eta', the control arm's standardised triple draws 'sham_z'); without it every draw is made
    here, in the order of the first run."""
    P, Q = LAYOUTS[layout]
    r = D["r"]
    n = len(D["C"])
    x = (r - r.mean()) / r.std()
    Cobs, mc = D["C"], D["C_center"]
    # true composition given the measured two-pass mean and the design: shrunk toward the design's prediction at
    # the partial reliability, so that the measurement error is independent of every design covariate
    lam = D["partial_rel"]
    if shared is None:
        Ct = D["C_fit"] + lam * D["C_res"] + math.sqrt(lam * (1 - lam) * D["C_res_var"]) * rng.standard_normal(n)
        lat = line_latent(rng, x, dgp["rho"], 1)[0]
    else:
        Ct = shared["Ct"]
        lat = dgp["rho"] * x + math.sqrt(1 - dgp["rho"] ** 2) * shared["eta"]
    L = dgp["a"] + dgp["b"] * (lat - dgp["mx_mean"])  # line visibilities, score units (centred on the max)
    T = L.max(1) + beta * (Ct - mc)
    sz, sc, t, pt, h = dgp["sig_z"], dgp["sig_c"], dgp["t"], dgp["p_tie"], dgp["h"]
    noise = lambda shape: sz * rng.standard_normal(shape) + sc * rng.standard_normal(shape)
    s_tri = to_grid(T[:, None] + noise((n, P)))
    flag = lambda s: (s > t) | ((s == t) & (rng.random(s.shape) < pt)) | (rng.random(s.shape) < h)
    F = flag(s_tri).astype(float)
    Ts = dgp["sham_mu"] + dgp["sham_sd_between"] * (rng.standard_normal(N_SHAM) if shared is None else shared["sham_z"])
    s_sh = to_grid(Ts[:, None] + dgp["sham_sig_z"] * rng.standard_normal((N_SHAM, P)) + sc * rng.standard_normal((N_SHAM, P)))
    F_sh = flag(s_sh).astype(float)
    out = {}
    # floor (b): quiet lone recall LB (clustered) above the control arm's UB; plant-level Clopper-Pearson beside
    wq, ws = bootstrap_weights(rng, n, R), bootstrap_weights(rng, N_SHAM, R)
    lo_q, _ = clustered_mean_ci(wq, F); _, hi_s = clustered_mean_ci(ws, F_sh)
    out["floor_b"] = bool(lo_q > hi_s)
    kq, ks = int(F.sum()), int(F_sh.sum())
    cp_lo = stats.beta.ppf(0.025, kq, n * P - kq + 1) if kq > 0 else 0.0
    cp_hi = stats.beta.ppf(0.975, ks + 1, N_SHAM * P - ks) if ks < N_SHAM * P else 1.0
    out["floor_b_cp"] = bool(cp_lo > cp_hi)
    out["recall_quiet"], out["recall_sham"] = float(F.mean()), float(F_sh.mean())
    if Q > 0:
        s_sing = to_grid(L[:, :, None] + noise((n, 3, Q))).mean(-1)
        line_cov, gap = s_sing.max(1), top_two_gap(s_sing)
        M = auroc_matrix(s_tri.ravel(), s_sh.ravel())
        Wq, Ws = np.repeat(wq, P, axis=1), np.repeat(ws, P, axis=1)
        au = ((Wq @ M) * Ws).sum(1) / (Wq.sum(1) * Ws.sum(1))
        out["auroc"] = float(M.mean())
        out["floor_a"] = bool(np.percentile(au, 2.5) > 0.5)
        if "a" in forms:
            excess = s_tri.mean(1) - line_cov
            out["a"] = form_a(rng, Cobs, gap, D["sonnet"], D["edit"], D["doc"], excess, R, m_s, q1q3, wt=wq, c12=(D["c1"], D["c2"]))
    else:
        line_cov, gap = r.max(1), top_two_gap(r)
    if "b" in forms:
        out["b"] = form_b(rng, Cobs, line_cov, gap, D["sonnet"], D["edit"], D["doc"], F, P, R, q1q3, c12=(D["c1"], D["c2"]),
                          firth=firth, ceiling_hit=ceiling is not None and F.mean() > ceiling)
    # partial reliability of composition given this layout's covariates (true over measured residual variance)
    doc = np.eye(len(D["docs"]))[D["doc"]][:, 1:]
    Z = np.column_stack([np.ones(n), line_cov, gap, D["sonnet"], D["edit"], doc])
    out["partial_rel"] = float(_residual(Ct, Z).var() / _residual(Cobs, Z).var())
    return out


# ---------------------------------------------------------------- the grid

def design_with_moments(D, mom, tail_double=False):
    D = dict(D)
    if tail_double:
        hi = np.flatnonzero(D["C"] >= 75)
        for k in ("r", "C", "c1", "c2", "sonnet", "edit", "doc"):
            D[k] = np.concatenate([D[k], D[k][hi]])
    D["sb"] = mom["test_retest"]["spearman_brown"]
    D["partial_rel"] = mom["test_retest"]["partial"]["spearman_brown"]
    D["var_c"] = float(np.var(D["C"], ddof=1))
    D["C_center"] = float(np.mean(D["C"]))
    Z = rater_covariates(D)
    D["C_res"] = _residual(D["C"], Z)
    D["C_fit"] = D["C"] - D["C_res"]
    D["C_res_var"] = float(D["C_res"].var())
    return D


def run_cell(args):
    """One (instrument, layout, ICC, noise, truth) cell: EXPERIMENTS experiments."""
    (key, D, dgp, layout, truth, beta, m_s, q1q3, forms, n_exp, R, seed_key) = args
    rng = np.random.default_rng([SEED] + list(seed_key))
    rows = [experiment(rng, D, dgp, layout, beta, m_s, q1q3, R=R, forms=forms) for _ in range(n_exp)]
    return key, summarise_cell(rows, layout, truth)


def summarise_cell(rows, layout, truth):
    n = len(rows)
    P, Q = LAYOUTS[layout]
    s = {"n": n, "P_floor_b": sum(not r["floor_b"] for r in rows) / n,
         "P_floor_b_cp": sum(not r["floor_b_cp"] for r in rows) / n,
         "recall_quiet_mean": float(np.mean([r["recall_quiet"] for r in rows])),
         "recall_sham_mean": float(np.mean([r["recall_sham"] for r in rows])),
         "partial_rel_mean": float(np.mean([r["partial_rel"] for r in rows]))}
    if Q > 0:
        s["P_floor_a"] = sum(not r["floor_a"] for r in rows) / n
        s["auroc_mean"] = float(np.mean([r["auroc"] for r in rows]))
    for form in ("a", "b"):
        if not rows or form not in rows[0]:
            continue
        floor_key = "floor_a" if form == "a" else "floor_b"
        f = {}
        fit = [r for r in rows if r[form]["fit_ok"]]
        f["unfit_share"] = 1 - len(fit) / n
        for c in ("75v50", "q3vq1", "75v50_o4", "75v50_o4_joint", "75v50_disatt", "75v50_disatt_sb"):
            if not any(c in r[form] for r in rows):
                continue
            # floor first (A6.4), then a failed fit, then a reading this experiment could not produce (an invalid
            # reliability for the disattenuated readings): none of them is a verdict
            oc = [("floor" if not r[floor_key] else (r[form][c]["outcome"] if c in r[form] else "unavailable")) for r in rows]
            f[c] = {o: oc.count(o) / n for o in ("floor", "unfit", "unavailable", "ceiling", "excluded", "attenuated", "present", "inconclusive")}
            f[c]["lb_above_0"] = f[c]["attenuated"] + f[c]["present"]  # a read verdict whose lower bound is above 0
            fc = [r for r in fit if c in r[form]]
            pts = np.array([r[form][c]["point"] for r in fc]) if fc else np.array([np.nan])
            f[c]["n_fit"] = len(fc)
            f[c]["point_mean"] = float(pts.mean()); f[c]["point_median"] = float(np.median(pts))
            f[c]["point_mcse"] = float(pts.std(ddof=1) / math.sqrt(len(pts))) if len(pts) > 1 else float("nan")
            f[c]["point_sd"] = float(pts.std(ddof=1)) if len(pts) > 1 else float("nan")
            f[c]["ci_width_mean"] = float(np.mean([r[form][c]["hi"] - r[form][c]["lo"] for r in fc])) if fc else float("nan")
        f["width_at_75_mean"] = float(np.mean([r[form]["width_at_75"] for r in fit])) if fit else float("nan")
        rels = [r[form]["partial_rel_measured"] for r in rows if r[form].get("partial_rel_measured") is not None]
        f["partial_rel_measured_mean"] = float(np.mean(rels)) if rels else None
        if form == "b":
            f["doc_factor_share"] = float(np.mean([r["b"]["doc_factor"] for r in rows]))
            f["fallback_point_share"] = float(np.mean([r["b"]["fallback_reason"] == "point" for r in rows]))
            f["fallback_bootstrap_share"] = float(np.mean([r["b"]["fallback_reason"] == "bootstrap" for r in rows]))
            f["boot_nonconverged_mean"] = float(np.mean([r["b"]["boot_nonconverged"] for r in rows]))
        s[form] = f
    s["truth"] = truth
    return s


def truths_for(c, Q, noise, m_s):
    """The truth states of one cell. Primary: the null, form (b) at a conditional contrast of 0.3 and form (a) at an
    observed score slope of m_s / 25 (A6.6), each skipped where the instrument cannot show it. At the reference
    noise only, beside: (b) at 0.3 defined marginally over the design, and both forms at 1.5 and 2 times their
    margin (the effect at which a layout would become readable)."""
    t = [("null", 0.0, ("a", "b") if Q else ("b",))]
    if c["beta_b"] is not None:
        t.append(("alt_b", c["beta_b"], ("b",)))
    if Q and c["beta_a"][str(Q)] is not None:
        t.append(("alt_a", c["beta_a"][str(Q)], ("a",)))
    if noise == REF_NOISE:
        if c["beta_b_marginal"] is not None:
            t.append(("alt_b_marginal", c["beta_b_marginal"], ("b",)))
        for mult in MULTIPLES:
            if c["beta_b_mult"].get(str(mult)) is not None:
                t.append((f"alt_b_x{mult}", c["beta_b_mult"][str(mult)], ("b",)))
            if Q and c["beta_a_mult"][str(mult)][str(Q)] is not None:
                t.append((f"alt_a_x{mult}", c["beta_a_mult"][str(mult)][str(Q)], ("a",)))
    return t


def build_cells(inputs, D, cal, quick=False):
    """Every cell of the main grid, with its parameters."""
    mom = inputs["moments"]
    q1q3 = (mom["composition"]["q1"], mom["composition"]["q3"])
    n_exp = 20 if quick else EXPERIMENTS
    R = 200 if quick else REPLICATES
    cells = []
    for ii, (view, judge) in enumerate(INSTRUMENTS):
        name = f"{view}:{judge}"
        m_s = inputs["instruments"][name]["m_s"]["m_s"]
        for ci, icc in enumerate(ICCS):
            for ni, noise in enumerate(NOISES):
                c = cal[f"{name}|{icc}|{noise}|{RHO}"]
                for li, layout in enumerate(LAYOUTS):
                    Q = LAYOUTS[layout][1]
                    for ti, (truth, beta, forms) in enumerate(truths_for(c, Q, noise, m_s)):
                        key = f"{name}|{layout}|{icc}|{noise}|{truth}"
                        cells.append((key, D, c["dgp"], layout, truth, beta, m_s, q1q3, forms, n_exp, R, (ii, li, ci, ni, ti)))
    return cells


def calibrate_one(D, inp, icc, noise, rho=RHO):
    dgp = calibrate(D, inp, icc, noise, rho=rho)
    beta_b = beta_for_contrast(D, dgp, rho=rho)
    beta_m = beta_for_contrast(D, dgp, rho=rho, kind="marginal")
    return {"dgp": dgp, "beta_b": beta_b, "beta_b_check": true_contrast_conditional(D, dgp, beta_b) if beta_b is not None else None,
            "beta_b_marginal_at_beta_b": true_contrast(D, dgp, beta_b, rho) if beta_b is not None else None,
            "beta_b_marginal": beta_m, "beta_b_mult": {str(m): beta_for_contrast(D, dgp, MARGIN * m, rho=rho) for m in MULTIPLES},
            # form (a)'s estimand depends on the singleton placements (the gap covariate's noise), so its truth is per Q
            "beta_a": {str(Q): beta_for_slope(D, dgp, inp["m_s"]["m_s"] / 25.0, Q) for Q in (1, 2)},
            "beta_a_latent_equivalent": inp["m_s"]["m_s"] / 25.0,
            "observed_slope_x25_at_latent_m_s": {str(Q): 25 * observable_slope_a(D, dgp, inp["m_s"]["m_s"] / 25.0, Q) for Q in (1, 2)},
            "beta_a_mult": {str(m): {str(Q): beta_for_slope(D, dgp, m * inp["m_s"]["m_s"] / 25.0, Q) for Q in (1, 2)} for m in MULTIPLES},
            "conditional_contrast_at_beta_a": true_contrast_conditional(D, dgp, inp["m_s"]["m_s"] / 25.0)}


def calibrate_all(inputs, D, rhos=(RHO,)):
    cal = {}
    for view, judge in INSTRUMENTS:
        name = f"{view}:{judge}"
        inp = inputs["instruments"][name]
        for icc in ICCS:
            for noise in NOISES:
                for rho in rhos:
                    cal[f"{name}|{icc}|{noise}|{rho}"] = calibrate_one(D, inp, icc, noise, rho)
    return cal


def _pool_map(fn, cells, workers):
    out = {}
    if workers <= 1:
        for c in cells:
            k, v = fn(c); out[k] = v
        return out
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for k, v in ex.map(fn, cells, chunksize=1):
            out[k] = v
            print(f"done {k}", flush=True)
    return out


# ---------------------------------------------------------------- gates (A6.6)

def gate_values(sim_cells, name, form, layout, noise=REF_NOISE, alt=None, suffix="", comp="75v50"):
    """Per (instrument, form, layout): P(excluded | 0) and P(present | 0.3) at the worse of the two ICCs (reading:
    the gate holds only when it holds at both), at the reference call noise. `alt` names another truth state
    (the marginal definition or an effect multiple) for the beside readings."""
    alt = alt or ("alt_a" if form == "a" else "alt_b")
    ex, pr, at, inc0, inc1, fl0, fl1, uf0, uf1 = [], [], [], [], [], [], [], [], []
    for icc in ICCS:
        n0 = sim_cells.get(f"{name}|{layout}|{icc}|{noise}|null{suffix}", {}).get(form, {}).get(comp)
        n1 = sim_cells.get(f"{name}|{layout}|{icc}|{noise}|{alt}{suffix}", {}).get(form, {}).get(comp)
        if n0 is None or n1 is None:
            return None
        ex.append(n0["excluded"]); pr.append(n1["present"]); at.append(n1["attenuated"])
        inc0.append(n0["inconclusive"]); inc1.append(n1["inconclusive"])
        fl0.append(n0["floor"]); fl1.append(n1["floor"])
        uf0.append(n0.get("unfit", 0.0) + n0.get("unavailable", 0.0)); uf1.append(n1.get("unfit", 0.0) + n1.get("unavailable", 0.0))
    nr0 = [a + b for a, b in zip(fl0, uf0)]; nr1 = [a + b for a, b in zip(fl1, uf1)]  # not read: within each ICC first
    return {"P_excl_0": min(ex), "P_present_alt": min(pr), "P_attenuated_alt": at[int(np.argmin(pr))],
            "P_detect_alt": min(p + a for p, a in zip(pr, at)), "P_floor_0": max(fl0), "P_floor_alt": max(fl1),
            "P_unfit_0": max(uf0), "P_unfit_alt": max(uf1), "P_not_read_0": max(nr0), "P_not_read_alt": max(nr1),
            "P_inconclusive_0": max(inc0), "P_inconclusive_alt": max(inc1),
            "readable": min(ex) >= 0.6 and min(pr) >= 0.6, "score": min(ex) + min(pr),
            "by_icc": {str(i): {"P_excl_0": e, "P_present_alt": p} for i, e, p in zip(ICCS, ex, pr)}}


def gate_table(sim_cells, alt_for=None, layouts=None, suffix="", comp="75v50"):
    names = [f"{v}:{j}" for v, j in INSTRUMENTS]
    table = {}
    for layout in layouts or LAYOUTS:
        Q = LAYOUTS[layout][1]
        for name in names:
            for form in (("a", "b") if Q else ("b",)):
                alt = alt_for(form) if alt_for else None
                g = gate_values(sim_cells, name, form, layout, alt=alt, suffix=suffix, comp=comp)
                if g is not None:
                    table[f"{name}|{form}|{layout}"] = g
    return table


def pick_layout(table):
    readable_layouts = {}
    for layout in LAYOUTS:
        cands = [(k, g) for k, g in table.items() if k.endswith(f"|{layout}") and g["readable"]]
        if cands:
            k, g = max(cands, key=lambda kg: kg[1]["score"])
            readable_layouts[layout] = {"carrying": k, "score": g["score"], "n_readable_instruments": len(cands),
                                        "readable": sorted(k for k, _ in cands)}
    with_s = {l: v for l, v in readable_layouts.items() if LAYOUTS[l][1] > 0}
    without_s = {l: v for l, v in readable_layouts.items() if LAYOUTS[l][1] == 0}
    if with_s:
        return readable_layouts, max(with_s, key=lambda l: with_s[l]["score"]), "the readable layout with the singleton arm with the highest sum"
    if without_s:
        return readable_layouts, max(without_s, key=lambda l: without_s[l]["score"]), "no singleton layout readable; the best readable without it (A6.5(i) named)"
    return readable_layouts, None, "no layout readable under any instrument"


def residual_bias(sim_cells, inputs):
    """A6.6's trigger: the mean point estimate under the null at the reference noise, the worse ICC; (a) against
    half of m_s, (b) against 0.15 on the 75-minus-50 contrast."""
    bias = {}
    for view, judge in INSTRUMENTS:
        name = f"{view}:{judge}"
        m_s = inputs["instruments"][name]["m_s"]["m_s"]
        for layout in LAYOUTS:
            for form in ("a", "b"):
                for noise in NOISES:
                    vals = [sim_cells.get(f"{name}|{layout}|{icc}|{noise}|null", {}).get(form) for icc in ICCS]
                    if any(v is None for v in vals):
                        continue
                    b = [v["75v50"]["point_mean"] for v in vals]
                    se = [v["75v50"]["point_mcse"] for v in vals]
                    bound = m_s / 2 if form == "a" else 0.15
                    if any(not np.isfinite(x) for x in b):
                        # no fitted experiment at some ICC: the bias is unknown, which never clears the trigger
                        bias[f"{name}|{form}|{layout}|{noise}"] = {"bias_worse_icc": float("nan"), "mcse": float("nan"), "by_icc": dict(zip(map(str, ICCS), b)),
                                                                   "trigger_bound": bound, "material": None}
                        continue
                    i = int(np.argmax(np.abs(b)))
                    bias[f"{name}|{form}|{layout}|{noise}"] = {"bias_worse_icc": b[i], "mcse": se[i], "by_icc": dict(zip(map(str, ICCS), b)),
                                                               "trigger_bound": bound, "material": abs(b[i]) > bound,
                                                               "n_fit_by_icc": [v["75v50"].get("n_fit") for v in vals]}
    return bias


def apply_gates(sim_cells, inputs):
    """A6.6 as written: readability picks the layout (pick_layout). Then the residual-bias rules: a carrier must be
    readable and have a residual null bias at 5 points that is known and not material; at an adopted single-singleton
    layout, a material bias for the carrying instrument moves the layout to its two-placement singleton variant for
    both forms, where a form whose bias stays material hands the partition to the other. When no eligible carrier
    is left the adoption is unresolved (the coordinator decides); it is never reported as adopted."""
    table = gate_table(sim_cells)
    readable_layouts, adopted, basis = pick_layout(table)
    bias = residual_bias(sim_cells, inputs)
    material = lambda k: bias.get(f"{k}|{REF_NOISE}", {}).get("material")
    out = {"table": table, "readable_layouts": readable_layouts, "adopted_by_gate": adopted, "basis": basis, "bias": bias,
           "bias_trigger": None, "adopted": None, "carrier": None}
    if adopted is None:
        out["status"] = "none_readable"
        return out
    layout = adopted
    first = readable_layouts[adopted]["carrying"]
    name = first.split("|")[0]
    if LAYOUTS[layout][1] == 1:
        fired = {f: material(f"{name}|{f}|{layout}") for f in ("a", "b")}
        out["bias_trigger"] = {"instrument": name, "material_by_form": fired}
        if any(v is True for v in fired.values()):
            layout = layout.replace("S1", "S2")
            out["bias_trigger"]["moved_to"] = layout
            out["bias_trigger"]["after"] = {f: bias.get(f"{name}|{f}|{layout}|{REF_NOISE}") for f in ("a", "b")}
    readable_here = sorted(((k, g) for k, g in table.items() if k.endswith(f"|{layout}") and g["readable"]), key=lambda kg: -kg[1]["score"])
    eligible = [(k, g) for k, g in readable_here if material(k) is False]
    out["readable_at_final"] = [k for k, _ in readable_here]
    out["ineligible_at_final"] = {k: material(k) for k, _ in readable_here if material(k) is not False}
    if eligible:
        # A6.6: the carrying instrument's other form carries when one form's bias stays material; else the best eligible
        own = [kg for kg in eligible if kg[0].split("|")[0] == name]
        k, g = (own or eligible)[0]
        out.update(adopted=layout, carrier=k, status="adopted")
    else:
        out.update(adopted=None, carrier=None, status="unresolved",
                   unresolved_layout=layout,
                   note=f"no readable carrier at {layout} has a known, non-material residual bias: the coordinator decides")
    return out


def too_thin_check(gates, sens_tables, sens_cells=None, sens_layouts=None, unattainable=()):
    """A6.6: the above-75 tail is too thin when no instrument reaches P(present | 0.3) of 0.6 and the doubled-tail
    sensitivity clears 0.6 for some instrument. States: 'not_applicable' (some instrument reaches 0.6), 'pending'
    (no tail run), 'incomplete' (the tail run does not cover every instrument, form and layout of the gate table:
    a null cell, or an alternative cell not recorded as unattainable, is missing; a negative verdict is then not
    licensed), 'too_thin', 'not_too_thin'."""
    best_pres = max((g["P_present_alt"], k) for k, g in gates["table"].items())
    base = {"best_present": best_pres}
    if best_pres[0] >= 0.6:
        return {**base, "state": "not_applicable", "tail_doubled_cleared": []}
    tt = sens_tables.get("tail_doubled")
    if not tt:
        return {**base, "state": "pending", "tail_doubled_cleared": []}
    cleared = sorted(k for k, g in tt.items() if g["P_present_alt"] >= 0.6)
    sc, un = sens_cells or {}, set(unattainable)
    missing, unatt = [], []
    for k in gates["table"]:
        name, form, layout = k.split("|")
        if sens_layouts is not None and layout not in sens_layouts:
            missing.append(f"{k}|layout not run")
            continue
        for icc in ICCS:
            if form not in sc.get(f"{name}|{layout}|{icc}|{REF_NOISE}|null", {}):
                missing.append(f"{k}|{icc}|null")
            alt = f"{name}|{layout}|{icc}|{REF_NOISE}|alt_{form}"
            if form not in sc.get(alt, {}):
                (unatt if f"{alt}|tail_doubled" in un else missing).append(f"{k}|{icc}|alt")
    state = "too_thin" if cleared else ("incomplete" if missing else "not_too_thin")
    return {**base, "state": state, "tail_doubled_cleared": cleared, "missing": missing, "unattainable_under_tail": unatt}


# ---------------------------------------------------------------- P4: the estimate per layout

T1V3_SCORE = {"sonnet": "work/stage3/t1v3/t1v3-score.sonnet.json", "opus48": "work/stage3/t1v3/t1v3-score.opus48.json"}
B4R = "work/stage3/b4r/b4r-results.json"
SOL_CHECK = "work/stage3/pilot/measure/sol-provider-check.json"
N_QUIET = 78


def unit_costs(root: Path) -> dict:
    """Realised dollars per scored unit: B1 (the dossier, prefix_rw_v2c) with T1 v3 (P_author and O_diff on the same
    prefix) on one side, B4-R's nulls (prefix_rw_v3rc) on the other; Sol on O_diff through Bedrock from brief 09's
    provider check (realised, and its estimate basis, since Converse reports no reasoning tokens). The estimate
    uses the higher of the bases per unit."""
    b1 = json.loads((root / B1).read_text())["accounting"]
    b4 = json.loads((root / B4R).read_text())["nulls"]
    sol = json.loads((root / SOL_CHECK).read_text())
    out = {}
    for view, key in (("dossier_iso", "isolated"), ("dossier_live", "live")):
        for j in ("sonnet", "opus48"):
            a = b1[f"{j}:{key}"]
            n4 = b4[f"P_author_doc_{'iso' if key == 'isolated' else 'live'}.{j}"]
            out[f"{view}:{j}"] = {"B1/T1v3": a["dollars"] / a["records"]["scored"], "B4-R": n4["dollars"] / n4["n_units"]}
    for j in ("sonnet", "opus48"):
        v = json.loads((root / T1V3_SCORE[j]).read_text())["views"]
        for view in ("P_author", "O_diff"):
            n4 = b4[f"{view}.{j}"]
            out[f"{view}:{j}"] = {"B1/T1v3": v[view]["dollars"] / v[view]["n"], "B4-R": n4["dollars"] / n4["n_units"]}
    js = sol["judge_stats"]
    out["O_diff:sol"] = {"brief09 realised": js["dollars_total"] / js["scored"], "brief09 estimate basis": sol["estimate"]["est_cost_usd"] / sol["estimate"]["n_calls"]}
    for k, v in out.items():
        v["used"] = max(v.values())
    return out


def estimate(costs: dict) -> dict:
    """Units and dollars per view and judge at each layout: every quiet triple, the 22 controls and the 24 control-arm
    (sham) items planted lone at the layout's placements, scored under the six per-agent cells and O_diff (Sonnet 5,
    Opus 4.8, Sol through Bedrock); the 234 singleton lines at the layout's singleton placements under the six
    per-agent cells only (A6.8). The sealed nulls and the planted authors' honest pairs are reused, not re-scored.
    The controls' 66 singleton lines are an add-on, priced beside."""
    per_agent = [f"{v}:{j}" for v, j in INSTRUMENTS]
    odiff = ["O_diff:sonnet", "O_diff:opus48", "O_diff:sol"]
    out = {}
    for layout, (P, Q) in LAYOUTS.items():
        lone = (N_QUIET + N_CONTROLS + N_SHAM) * P
        rows = {}
        for k in per_agent:
            u = lone + 3 * N_QUIET * Q
            rows[k] = {"lone_units": lone, "singleton_units": 3 * N_QUIET * Q, "units": u, "dollars": u * costs[k]["used"]}
        for k in odiff:
            rows[k] = {"lone_units": lone, "singleton_units": 0, "units": lone, "dollars": lone * costs[k]["used"]}
        tot = sum(r["dollars"] for r in rows.values())
        addon = sum(3 * N_CONTROLS * Q * costs[k]["used"] for k in per_agent)
        out[layout] = {"rows": rows, "units": sum(r["units"] for r in rows.values()), "dollars": tot,
                       "stop_line_2x": 2 * tot, "controls_singleton_addon_dollars": addon}
    return out


# ---------------------------------------------------------------- the report

def _f(x, d=2):
    return "—" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def _cellget(cells, key, form, comp="75v50", field=None):
    c = cells.get(key, {}).get(form)
    if c is None:
        return None
    return c[comp] if field is None else c[comp].get(field)


def cmd_report(a):
    root = Path(a.root)
    inputs = json.loads(Path(a.inputs).read_text())
    sim = json.loads(Path(a.sim).read_text())
    sens = json.loads(Path(a.sensitivity).read_text()) if a.sensitivity else None
    cells = sim["cells"]
    mom = inputs["moments"]
    gates = apply_gates(cells, inputs)
    beside = {"marginal_truth": pick_layout(gate_table(cells, alt_for=lambda f: "alt_b_marginal" if f == "b" else "alt_a")),
              "multiples": {str(m): pick_layout(gate_table(cells, alt_for=lambda f, m=m: f"alt_{f}_x{m}")) for m in MULTIPLES}}
    beside_tables = {"marginal_truth": gate_table(cells, alt_for=lambda f: "alt_b_marginal" if f == "b" else "alt_a"),
                     "multiples": {str(m): gate_table(cells, alt_for=lambda f, m=m: f"alt_{f}_x{m}") for m in MULTIPLES}}
    sens_tables, sens_subs = {}, {}
    if sens:
        tags = sorted({k.split("|")[-1] for k in sens["cells"]})
        for tag in tags:
            sub = {k[: k.rindex("|")]: v for k, v in sens["cells"].items() if k.endswith("|" + tag)}
            sens_subs[tag] = sub
            sens_tables[tag] = gate_table(sub, layouts=sens["layouts"])
    # too thin (A6.6): at the best layout, P(present | 0.3) < 0.6 for every instrument, and the doubled tail clears it
    too_thin = too_thin_check(gates, sens_tables, sens_subs.get("tail_doubled"), sens["layouts"] if sens else None,
                              sens.get("unattainable", []) if sens else [])
    here = sha256(__file__)
    bind_inputs(root, a.inputs)  # the raw files still match the inputs record
    prov = {"report_script": here, "sim_script": sim.get("script_sha256"), "sensitivity_script": sens.get("script_sha256") if sens else None,
            "inputs_file": sha256(a.inputs), "sim_inputs": sim.get("inputs_sha256_file"), "sensitivity_inputs": sens.get("inputs_sha256_file") if sens else None}
    prov["consistent"] = (prov["sim_script"] == here and prov["sim_inputs"] == prov["inputs_file"]
                          and (sens is None or (prov["sensitivity_script"] == here and prov["sensitivity_inputs"] == prov["inputs_file"])))
    beside_comps = {c: gate_table(cells, comp=c) for c in ("75v50_o4", "75v50_o4_joint", "75v50_disatt", "75v50_disatt_sb", "q3vq1")}
    costs = unit_costs(root)
    est = estimate(costs)
    result = {"version": "b3-power-v3/report", "seed": SEED, "experiments": sim["experiments"], "replicates": sim["replicates"],
              "rho": sim["rho"], "moments": mom, "instruments": inputs["instruments"], "calibration": sim["calibration"],
              "gates": gates, "beside_gates": {k: (v if k != "multiples" else v) for k, v in beside.items()},
              "beside_tables": beside_tables, "sensitivity_tables": sens_tables, "too_thin": too_thin,
              "beside_comps": beside_comps, "provenance": prov,
              "unit_costs": costs, "estimate": est, "cells": cells, "sensitivity_cells": sens["cells"] if sens else None,
              "inputs_sha256": inputs["inputs_sha256"], "script_sha256": here,
              "cost_files_sha256": {f: sha256(root / f) for f in [B1, B4R, SOL_CHECK] + list(T1V3_SCORE.values())}}
    Path(a.out_json).write_text(json.dumps(result, indent=1, default=str))
    Path(a.out_md).write_text(render_md(result))


def _rel_range(cells, layout):
    v = [c["partial_rel_mean"] for k, c in cells.items() if k.split("|")[1] == layout and k.split("|")[3] == str(REF_NOISE) and k.endswith("|null")]
    return f"{layout} {min(v):.3f} to {max(v):.3f}" if v else f"{layout} —"


MODEL_MD = [
    "## The generative model (as simulated)", "",
    "- **Design, fixed:** the 78 quiet triples as rated: each line's two-pass rater mean, the two-pass composition mean, writer, replace share (from the writers' checks), document. "
    "The control arm is v2's 24 same-shape sham payloads; it has no rater scores, so its per-agent score is drawn whole.",
    "- **Line visibility:** for line j of triple i, L_ij = a + b (ℓ_ij − mean max ℓ), ℓ_ij = ρ z(rater mean) + √(1 − ρ²) η_ij, η ~ N(0, 1) drawn per world; ρ = 0.5 primary "
    "(an assumption: B0's Z2 AUROC of the author's maximum rater score, 0.66 to 0.84, suggests an author-level correlation near 0.6 over the full range but does not identify a line-level one, and the quiet set's range is restricted), 0.3 and 0.7 beside.",
    "- **Triple score:** T_i = max_j L_ij + β (C*_i − mean C). Under max-type truth β = 0. Each placement p: s_ip = grid(T_i + z_ip + c_ip), z ~ N(0, σ_z²) (placement), c ~ N(0, σ_c²) (call noise, 0, 5 or 10). "
    "Each singleton placement of line j: grid(L_ij + z + c), its own author, independent deviations. grid() clips to 0..100 and rounds to the 5-point grid.",
    "- **ICC:** σ_z² = (1 − ICC)/ICC × Var_i(between), so the ICC is the between-triple share of the null latent score before call noise (the residual ICC under the alternative; the composition term adds between-triple variance there); the call noise is added on top.",
    "- **Calibration, per instrument, ICC and noise:** a and the latent SD are set so that, under the null, the quiet triples' planted-unit flag rate and grid SD equal B1's pooled non-alarming lone plants; "
    "the control arm's latent mean and SD so that its grid mean and SD equal the sham lone plants'. The author's honest pairs on other documents enter as an independent Bernoulli h per plant, read off the sham; independence can overstate the union (Opus 4.8's `P_author`: quiet recall 0.559 observed, about 0.577 under independence), which favours the floor slightly.",
    "- **Flag:** grid score above t, ties at t drawn at p_tie (only where t is on the grid), or the honest path.",
    "- **Composition measurement:** the true composition is drawn given the two-pass mean and the design (rater line covariates, writer, replace share, document): shrunk toward the design's prediction at the "
    "partial reliability measured in P1 (0.846), so the measurement error is independent of every design covariate. The judge responds to the true composition; the analysis uses the measured one.",
    "- **Truth for (b):** β such that, with the judge's true line maximum held at its mean, the lone flag probability at composition 75 minus at 50 is 0.3 (O2's estimand). Beside: β for 0.3 averaged over the design's lines (marginal), and for 0.45 and 0.6. "
    "**Truth for (a):** the latent β at which form (a)'s own coefficient, free of composition measurement error, × 25 equals m_s: excess (a triple's grid score minus the maximum of its lines' mean grid scores over the layout's singleton placements) "
    "regressed on the true composition with form (a)'s covariates (the top-two singleton gap, writer, replace share, document), call and placement noise included, at β minus at 0 (the null part is the max-of-three bias, read separately). "
    "It depends on the number of singleton placements (S1 or S2), so it is calibrated per layout family; the grid clips and rounds, so β exceeds m_s / 25 and, for the largest margins, no β shows m_s (then (a)'s alternative is not attainable and the cell cannot be readable). 1.5 and 2 times m_s beside.",
    "- **Estimators, as fitted in A6.3:** (a) OLS of excess (mean triple score over its placements minus the maximum over lines of each line's mean singleton score) on composition, the top-two singleton gap, writer, replace share and document; "
    "(b) logistic regression of every lone plant's flag on composition, the line covariate (the judge's singleton maximum where the arm runs, else the rater's top line), the top-two gap of the same scores, writer, replace share and document, "
    "falling back to the document-stratified bootstrap without the factor when the full model does not converge (O3); its contrast standardised over the sample's writer and document composition with the continuous covariates at their sample means (O2). "
    "Payload-clustered percentile bootstrap, 1,000 replicates; the four-outcome table on 0.3 for (b) and m_s for (a); floors first (A6.4).",
    "- **Layouts:** T1/T2 = each quiet triple planted once/twice; +S1/+S2 = each of its three lines also planted alone once/twice (A6.5(iii)'s variant). The control arm is planted at the triples' placements.", ""]


READINGS_MD = [
    "## Readings and deviations (every choice the brief does not spell out)", "",
    "1. **Instruments.** The six per-agent cells A6.3 names: the isolated and the live dossier under Opus 4.8 and Sonnet 5, the sealed `P_author` under both. Every B3 plant is lone, so Sonnet's dossier is in scope throughout. `O_diff` is A6.3 (e)'s beside reading: priced in P4, not simulated (no partition).",
    "2. **m_s.** s is the planted unit's own score (B1's `score`), the per-plant lone score A6.4 names. With the open lower end A6.4 writes, the set of qualifying D has no minimum; m_s is its infimum, the required shift (any D above it qualifies; at m_s itself the closed interval holds the 0.3, the open one may hold fewer, e.g. 26 against 21 of 84 for Opus 4.8's isolated dossier at 32). The shift that raises the full sealed-rule flag rate (the union with the author's unshifted honest pairs, ties at p_tie) by 0.3 is beside. Reference plants pooled over the four non-alarming regimes (84).",
    "3. **The control arm** is v2's 24 same-shape sham payloads (W2; B3's sham). Its prior pools their lone plants as planted under v2 and the re-plant (48); in the simulation it is planted at the layout's triple placements (24 × P).",
    "4. **Covariates.** A6.6 and brief 20 ask for every covariate (top-two gap, writer, edit type, document) in every simulated model: (a) carries the document factor though A6.3 (a) lists three covariates; (b) carries the top-two gap as A6.5 (iii) requires for both forms. Without the singleton arm, (b)'s line covariate and gap are the rater's (two-pass means). Edit type is the triple's share of replace edits (0, 1/3, 2/3, 1).",
    "5a. **O3 in a bootstrapped fit.** The document factor is dropped (document-stratified bootstrap instead) when the full model fails on the sample or in more than 2.5 percent of the bootstrap replicates (the percentile interval's tail mass). With six documents of 11 to 14 triples, a resample often leaves a document all flagged or all unflagged; the separated replicates' contrasts are unstable at any iteration count and would otherwise fill the interval's tails (found in a first run, which applied O3 to the point fit only: Opus 4.8's live dossier had half its replicates non-converged and intervals of 0.72 against a sampling SD of 0.09; that run is superseded). The model used is then **unfit** (no verdict, counted with the floor as not read) when its own point fit fails or more than 2.5 percent of its replicates fail; otherwise its interval is read on the converged replicates only. A failed fit is never evidence for *excluded*.",
    "5. **O2's contrast** is standardised: the predicted probability averaged over the sample's rows (their writer and document) with composition set to 75 or 50 and the continuous covariates (line covariate, gap, replace share) at their sample means. This is the share-weighted pooled level for both factors and does not collapse when a document's coefficient diverges.",
    "6. **The gate** holds only when it holds at both ICCs (each probability taken at the worse ICC) at the 5-point call noise, the level at which A6.6 reads the bias trigger; every noise level is tabled. The carrying instrument of a layout is its readable (view, judge, form) with the highest P(excluded | 0) + P(present | 0.3). The bias trigger is read for the carrying instrument of an adopted single-singleton layout; the table gives it for every instrument.",
    "7. **The truth for (b)** is the contrast with the judge's true line maximum at its mean, the scientific counterpart of O2's estimand without measurement error (the fitted logistic model approximates the threshold model, and its covariate is the measured maximum, so the estimator's population value is not exactly this truth; the simulation measures the gap as bias). The marginal definition (averaged over the lines) is shown beside; it can need a smaller or a larger composition effect for the same 0.3 (smaller where the mean line sits near the threshold, larger near the ceiling, as for Opus 4.8's live dossier), and it is not what the model estimates.",
    "8. **Inputs the brief does not name.** The judge-rater line correlation ρ (0.5; 0.3 and 0.7 beside) is needed by any model that ties the judge's line scores to the rater's. The DGP gives writer, edit type and document no effect (an assumption, not a bound: real effects could move probabilities toward a floor or ceiling, and dropping the document factor under O3 would then leave some confounding). The latent score is normal and clipped; for the bimodal judges (Sonnet's dossiers, Opus 4.8's `P_author`) the calibration matches the flag rate and SD, not the shape.",
    "9. **Composition's reliability** in the simulation is the partial reliability measured in P1 given the rater covariates (0.846), not A6.5's 'about 0.87'; the Spearman-Brown value of the plain two-pass mean is 0.915.",
    "10. **The 5-point grid.** Thresholds off the grid (83, 62, 58 and 68) flag from the next grid value up; ties at p_tie occur only where t is on the grid (85 for Sonnet's `P_author`, 40 for Opus 4.8's live dossier).",
    "11. **Floors.** (b)'s floor is read on the payload-clustered intervals (quiet lower bound above the control arm's upper bound), the plant-level Clopper-Pearson floor beside in the JSON; (a)'s floor is AUROC(quiet triple plants vs control-arm plants, per-agent score) with a clustered lower bound above 0.5, read only where (a) runs.",
    "12. **The estimate** counts no new honest units: the sealed nulls and the planted authors' honest pairs on other documents are reused. Singleton plants are scored under the per-agent views only (A6.8), not under `O_diff` (A6.3 (e) lists the triples, controls and sham). Each unit is priced at the higher of B1/T1 v3 (prefix_rw_v2c, B3's prefix) and B4-R (prefix_rw_v3rc); Sol at the higher of brief 09's realised cost and its estimate basis, since Bedrock's Converse API reports no reasoning tokens.", ""]


def summary_md(R) -> list:
    """The coordinator's summary; every number and every direction is read from the result."""
    g, cells, insts = R["gates"], R["cells"], R["instruments"]
    tab = g["table"]
    unfit0 = max((t["P_unfit_0"] for t in tab.values()), default=0.0)
    two = [k for k in tab if LAYOUTS[k.split("|")[2]][0] == 2]
    best_p = max(tab.items(), key=lambda kv: kv[1]["P_present_alt"])
    best_d = {f: max(((k, v) for k, v in tab.items() if k.split("|")[1] == f and v["P_excl_0"] >= 0.6), key=lambda kv: kv[1]["P_detect_alt"], default=None) for f in ("a", "b")}
    mt, m15 = R["beside_gates"]["marginal_truth"], R["beside_gates"]["multiples"]["1.5"]
    at5 = lambda form, single: [v for k, v in g["bias"].items() if k.split("|")[1] == form and k.endswith(f"|{REF_NOISE}")
                                and (LAYOUTS[k.split("|")[2]][1] > 0) == single]
    bias_b, bias_b0, bias_a = at5("b", True), at5("b", False), at5("a", True)
    b_s1 = [v["bias_worse_icc"] for k, v in g["bias"].items() if k.split("|")[1] == "b" and "S1" in k.split("|")[2] and k.endswith(f"|{REF_NOISE}")]
    b_s2 = [v["bias_worse_icc"] for k, v in g["bias"].items() if k.split("|")[1] == "b" and "S2" in k.split("|")[2] and k.endswith(f"|{REF_NOISE}")]
    bias_a = [v for v in bias_a if v["material"] is not None]; bias_b = [v for v in bias_b if v["material"] is not None]
    bias_b0 = [v for v in bias_b0 if v["material"] is not None]
    sig_pos = sum(v["bias_worse_icc"] > 2 * v["mcse"] for v in bias_b); sig_neg = sum(v["bias_worse_icc"] < -2 * v["mcse"] for v in bias_b)
    att = {"a": [], "b": []}
    for n in insts:
        for l, (P, Q) in LAYOUTS.items():
            for form in (("a", "b") if Q else ("b",)):
                v = [cells.get(f"{n}|{l}|{icc}|{REF_NOISE}|alt_{form}", {}).get(form, {}).get("75v50", {}).get("point_mean") for icc in ICCS]
                if all(x is not None for x in v):
                    att[form].append(np.mean(v) / (insts[n]["m_s"]["m_s"] if form == "a" else MARGIN))
    rel = [c["partial_rel_mean"] for k, c in cells.items() if k.endswith("|null")]
    fallback = [n for n, i in insts.items() if "fallback" in i["m_s"]["rule"]]
    cal = R["calibration"]
    a_never = sorted({k.split("|")[0] for k, v in cal.items() if any(x is None for x in v["beta_a"].values())})
    a_never2 = sorted({k.split("|")[0] for k, v in cal.items() if any(x is None for x in v["beta_a_mult"]["2.0"].values())})
    est = R["estimate"]
    L = ["## Summary", ""]
    if g["status"] == "adopted":
        L.append(f"- **The gate adopts {g['adopted']}** ({g['basis']}; carrier {g['carrier']}).")
    elif g["status"] == "unresolved":
        L.append(f"- **Unresolved:** the gate finds {g['adopted_by_gate']} readable, but {g['note']}.")
    else:
        ex2 = [tab[k]["P_excl_0"] for k in two]
        L.append(f"- **The gate as written finds no readable layout.** The highest P(present | 0.3) of any instrument, form and layout is {best_p[1]['P_present_alt']:.2f} "
                 f"({best_p[0]}); the gate needs 0.6 together with P(excluded | 0) ≥ 0.6. P(excluded | 0) is the lesser constraint: {min(ex2):.2f} to {max(ex2):.2f} at the two-placement layouts.")
    dd = "; ".join(f"({f}) {v[1]['P_detect_alt']:.2f} at {v[0].split('|')[0]} {v[0].split('|')[2]} with P(excluded | 0) {v[1]['P_excl_0']:.2f}" for f, v in best_d.items() if v)
    L.append(f"- **Why: the truth sits on the margin.** *Present* needs the point estimate at or above the margin; when the true effect equals the margin, a median-unbiased estimator lands above it about half the time, "
             f"and these estimators are attenuated: the mean estimate under the alternative is {min(att['b']):.2f} to {max(att['b']):.2f} of the truth for (b) and {min(att['a']):.2f} to {max(att['a']):.2f} for (a) "
             f"(composition's partial reliability given the covariates is {min(rel):.2f} to {max(rel):.2f}; (a)'s truth is set on the observed 5-point scale, so its shortfall is measurement error and finite-sample behaviour, not clipping). "
             f"Detection is not the problem: the best P(present or attenuated | 0.3) among cells with P(excluded | 0) ≥ 0.6 is {dd}. "
             f"Failed fits are counted as not read, so they cap P(excluded | 0): the largest P(unfit | 0) in the gate table is {unfit0:.2f}.")
    L.append(f"- **Beside, not gate inputs:** with (b)'s truth averaged over the lines (marginal) the gate would find {', '.join(mt[0]) or 'no layout'} readable and adopt {mt[1] or 'none'}; "
             f"at 1.5 × the margin it would find {', '.join(m15[0]) or 'no layout'} readable and adopt {m15[1] or 'none'}. Under A6.6 as written these change nothing; whether the gate meant P(present) with the truth on the margin is the coordinator's and Aravind's question.")
    tt = R["too_thin"] or {}
    if g["status"] == "none_readable":
        state = tt.get("state")
        L.append(f"- **Too thin:** {state} (with the above-75 tail doubled, instrument-forms clearing 0.6: {', '.join(tt.get('tail_doubled_cleared', [])) or 'none'}). "
                 + {"pending": "The tail-doubled run is missing; A6.1 is not applied until it is read.",
                    "incomplete": "The tail-doubled run does not cover every instrument and layout; a negative verdict is not licensed until it does.",
                    "too_thin": "A6.7's one writing round is licensed.",
                    "not_too_thin": "By A6.1 as written the reading is *unreadable* (B3 ends, reported with these numbers); given the margin point above, applying A6.1 or amending A6.6 is the coordinator's and Aravind's decision.",
                    "not_applicable": "Some instrument reaches 0.6, so the rule does not apply."}.get(state, "Not run."))
    mat = [k for k, v in g["bias"].items() if v["material"] and k.endswith(f"|{REF_NOISE}")]
    unk = [k for k, v in g["bias"].items() if v["material"] is None and k.endswith(f"|{REF_NOISE}")]
    if sig_pos > len(bias_b) / 2 and sig_neg == 0:
        dirn = (f"**(b)'s bias with the singleton covariate leans toward a false *present* ({sig_pos} of {len(bias_b)} cells above twice their Monte Carlo SE, {sig_neg} below), not toward a false *excluded* as A6.5 (iii) states**: "
                "the singleton maximum overstates visibility most where the lines are close, which is at low composition, so the covariate under-controls the line at high composition")
    elif sig_neg > len(bias_b) / 2 and sig_pos == 0:
        dirn = f"(b)'s bias with the singleton covariate leans toward a false *excluded* ({sig_neg} of {len(bias_b)} cells below twice their Monte Carlo SE), the direction A6.5 (iii) names"
    else:
        dirn = f"(b)'s bias with the singleton covariate has no consistent direction ({sig_pos} of {len(bias_b)} cells above twice their Monte Carlo SE, {sig_neg} below)"
    L.append(f"- **Residual null bias at 5-point noise:** (a) {min(v['bias_worse_icc'] for v in bias_a):+.2f} to {max(v['bias_worse_icc'] for v in bias_a):+.2f} score points against triggers of "
             f"{min(v['trigger_bound'] for v in bias_a):.2f} to {max(v['trigger_bound'] for v in bias_a):.2f}; (b) {min(v['bias_worse_icc'] for v in bias_b):+.3f} to {max(v['bias_worse_icc'] for v in bias_b):+.3f} with the singleton covariate, "
             f"{min(v['bias_worse_icc'] for v in bias_b0):+.3f} to {max(v['bias_worse_icc'] for v in bias_b0):+.3f} with the rater's (trigger 0.15), over successful fits. Material: {', '.join(mat) or 'none'}; unknown: {', '.join(unk) or 'none'}. {dirn}; "
             f"mean over cells {np.mean(b_s1):+.3f} with one singleton placement against {np.mean(b_s2):+.3f} with two.")
    fb = ", ".join(f"{n} by the fallback ({insts[n]['m_s']['m_s']:.2f})" for n in fallback) or "none by the fallback"
    big = ", ".join(f"{n} {i['m_s']['m_s']:.0f}" for n, i in insts.items() if i["m_s"]["m_s"] >= 40) or "none at 40 or more"
    L.append(f"- **m_s:** {len(insts) - len(fallback)} cells by A6.4's primary rule, {fb}. Where a judge's below-threshold plants sit near the floor of the scale the rule gives a large margin ({big}). "
             f"Form (a)'s alternative of m_s is not attainable on the observed 0..100 scale for: {', '.join(a_never) or 'none'}; twice m_s for: {', '.join(a_never2) or 'none'}.")
    L.append(f"- **Estimate (P4):** from ${est['T1']['dollars']:.2f} (T1) to ${est['T2+S2']['dollars']:.2f} (T2+S2; stop at ${est['T2+S2']['stop_line_2x']:.2f}), every view and judge including `O_diff` and Sol.")
    L.append("")
    return L


def render_md(R) -> str:
    mom, insts, g = R["moments"], R["instruments"], R["gates"]
    cells = R["cells"]
    names = [f"{v}:{j}" for v, j in INSTRUMENTS]
    L = []
    ad = g["adopted"]
    tt = R["too_thin"] or {}
    if g["status"] == "adopted":
        carry = g["carrier"]
        t = g["table"].get(carry, {})
        moved = g.get("bias_trigger") and g["bias_trigger"].get("moved_to")
        L.append(f"**Adopted layout (A6.6 gate): {ad}**: carried by {carry.split('|')[0]} form ({carry.split('|')[1]}); "
                 f"P(excluded | 0) {t.get('P_excl_0', float('nan')):.2f}, P(present | 0.3) {t.get('P_present_alt', float('nan')):.2f} at the worse ICC and 5-point call noise"
                 + (f"; moved from {g['adopted_by_gate']} by the residual-bias trigger" if moved else "") + ".")
    elif g["status"] == "unresolved":
        L.append(f"**No layout is adopted: the gate finds {g['adopted_by_gate']} readable, but {g['note']}.**")
    else:
        state = tt.get("state")
        nxt = {"pending": "the too-thin check is pending (the tail-doubled run is missing), so A6.1 is not yet applied",
               "incomplete": "the too-thin check is incomplete (the tail-doubled run does not cover every instrument and layout), so A6.1 is not yet applied",
               "too_thin": "the above-75 tail is too thin (A6.7's one writing round is licensed)",
               "not_too_thin": ("the tail is not too thin, so by A6.1 as written the reading is unreadable; the gate asks for P(present) with the true effect on the margin, "
                                "which an unbiased estimator meets about half the time, so whether to apply A6.1 or amend A6.6 is the coordinator's and Aravind's decision"),
               "not_applicable": "some instrument reaches P(present | 0.3) of 0.6 but not with P(excluded | 0) of 0.6, so the too-thin rule does not apply; by A6.1 as written the reading is unreadable, and the coordinator decides"}.get(state, "the too-thin check was not run")
        L.append(f"**None is readable under A6.6's gate as written: no layout passes under any per-agent instrument (best P(present | 0.3) {tt.get('best_present', [float('nan')])[0]:.2f} against 0.6); {nxt}.**")
    L.append("")
    prov = R.get("provenance", {})
    if not prov.get("consistent", False):
        L.append(f"**Provenance check failed:** the simulation or sensitivity file was not produced by this script and inputs file ({json.dumps(prov)}). The numbers below are not bound to this code.")
        L.append("")
    L.append(f"Brief 20 (B3 power simulation v3; $0; `work/checks/stage3_b3_power_v3.py` {R['script_sha256'][:12]}… (simulation, sensitivities and report from the same script and inputs: {prov.get('consistent')}); seed {R['seed']}; "
             f"{R['experiments']} experiments per cell; payload-clustered percentile bootstrap, {R['replicates']} replicates). "
             "Inputs are files on disk and none is a B3 outcome; counts, ids and aggregates only.")
    L.append("")
    L += summary_md(R)
    # ---- P1
    c, tr = mom["composition"], mom["test_retest"]
    L += ["## P1. The stimulus set", "",
          f"Quiet set under A6.2's mean rule (every statement's two-pass mean at or under 60): **{mom['n_quiet']}** of {mom['n_candidates']} "
          f"(Sonnet 5.5 {mom['n_quiet_by_writer']['sonnet55']}, GLM 5.3 {mom['n_quiet_by_writer']['glm53']}); sensitivities: pass-1-only rule "
          f"{mom['n_quiet_sensitivity']['pass1_only']} ({mom['n_quiet_sensitivity_by_writer']['pass1']}), both passes {mom['n_quiet_sensitivity']['both_passes']} "
          f"({mom['n_quiet_sensitivity_by_writer']['both']}).", "",
          "| quantity | value |", "|---|---|",
          f"| mean composition, linear-interpolation quantiles | Q1 {c['q1']}, median {c['median']}, Q3 {c['q3']}, p90 {c['p90']:.2f}, min {c['min']}, max {c['max']} |",
          f"| mean, SD | {c['mean']:.2f}, {c['sd']:.2f} |",
          f"| at or above 75 / 70; at or under 50 | {c['n_ge_75']} / {c['n_ge_70']}; {c['n_le_50']} |",
          f"| at or above 75 by writer (writer imbalance there) | Sonnet {c['n_ge_75_by_writer']['sonnet55']}, GLM {c['n_ge_75_by_writer']['glm53']} (Sonnet share {c['sonnet_share_ge_75']:.3f}) |",
          f"| composition by writer (median, mean) | Sonnet {c['by_writer']['sonnet55']['median']}, {c['by_writer']['sonnet55']['mean']:.2f}; GLM {c['by_writer']['glm53']['median']}, {c['by_writer']['glm53']['mean']:.2f} |",
          f"| test-retest r (pass 1 vs pass 2, quiet set); Spearman-Brown of the two-pass mean | {tr['pearson_pass1_pass2']:.3f}; **{tr['spearman_brown']:.3f}** |",
          f"| partial: r of the passes' residuals on the rater covariates; its Spearman-Brown | {tr['partial']['pearson_of_residuals']:.3f}; **{tr['partial']['spearman_brown']:.3f}** ({tr['partial']['covariates']}) |",
          f"| composition with the top line (Pearson; Spearman) | {mom['correlations']['pearson_comp_top']:.3f}; {mom['correlations']['spearman_comp_top']:.3f} |",
          f"| composition with the spread (Pearson; Spearman) | {mom['correlations']['pearson_comp_spread']:.3f}; {mom['correlations']['spearman_comp_spread']:.3f} |",
          f"| composition with the top-two gap; with the mean line (Pearson) | {mom['correlations']['pearson_comp_gap']:.3f}; {mom['correlations']['pearson_comp_mean_line']:.3f} |",
          f"| top line mean: overall; at composition 70 or above; 75 or above | {mom['top_line']['mean']:.2f}; {mom['top_line']['mean_at_comp_ge_70']:.2f}; {mom['top_line']['mean_at_comp_ge_75']:.2f} |",
          f"| replace-edit share of statements (quiet set) | Sonnet {mom['edit_type']['sonnet55']['replace']}/{mom['edit_type']['sonnet55']['statements']} = {mom['edit_type']['sonnet55']['replace_share']:.3f}; GLM {mom['edit_type']['glm53']['replace']}/{mom['edit_type']['glm53']['statements']} = {mom['edit_type']['glm53']['replace_share']:.3f} |",
          f"| triples by number of replace edits (0/1/2/3) | Sonnet {'/'.join(str(v) for v in mom['edit_type']['sonnet55']['triples_by_n_replace'].values())}; GLM {'/'.join(str(v) for v in mom['edit_type']['glm53']['triples_by_n_replace'].values())} |",
          f"| documents (quiet triples) | {', '.join(f'{k.split(chr(47))[-1]} {v}' for k, v in mom['documents'].items())} |", ""]
    # ---- P2
    L += ["## P2. The score-unit margin m_s (A6.4)", "",
          "Reference: the lone plants of the non-alarming regimes pooled (v2 conforming 24, v3 middle 24 and routine re-draw 12, the re-plant 24; 84 plants), "
          "the planted unit's score, the sealed author rule's threshold t. Primary rule: the smallest D with P(t − D ≤ s ≤ t) ≥ 0.3 (lower end read closed so D is attained). "
          "Beside: the smallest shift that raises the sealed-rule flag rate (union with the author's unshifted honest pairs, ties at p_tie) by 0.3.", "",
          "| view, judge | t (p_tie) | plants ≤ t of 84 (need 26) | rule | **m_s** | exact shift beside | fallback value 0.3 × (p95 − median) | null median, p95 (source) |",
          "|---|---|---|---|---|---|---|---|"]
    for n in names:
        i = insts[n]; m = i["m_s"]
        L.append(f"| {n} | {i['t']:g} ({i['p_tie']:.3f}) | {m['n_at_or_below_t']} | {'primary' if 'primary' in m['rule'] else '**fallback** (fewer than 0.3 at or below t)'} | **{m['m_s']:.2f}** | "
                 f"{_f(i['m_s_exact_beside']['D'])} (base rate {i['m_s_exact_beside']['base_rate']:.3f}) | {i['m_s_fallback_value']:.2f} | {i['null']['median']:g}, {i['null']['p95']:.1f} (`{i['null']['source']}`) |")
    L.append("")
    # ---- priors and calibration
    cal = R["calibration"]
    L += ["## Inputs to the simulation: B1's priors and the calibration", "",
          "Quiet prior: the 84 non-alarming lone plants (planted-unit flag rate, recall with the honest union, score mean and SD). Control arm: v2's 24 same-shape sham payloads, lone, as planted under v2 and the re-plant (48 plants). "
          "Honest path h = 1 − (1 − sham recall)/(1 − sham planted-unit rate). Calibration at 5-point call noise shown (every noise level in the JSON).", "",
          "β_b: the latent composition effect (score points per composition point) giving (b)'s conditional contrast of 0.3 (the marginal-truth β beside); β_a: the latent effect at which form (a)'s own error-free coefficient × 25 "
          "(excess on true composition with the singleton gap, writer, replace share and document, singleton noise at one or two placements) equals m_s (— where the 0..100 scale cannot show it); "
          "'observed at m_s/25': that coefficient × 25 when the latent effect is m_s / 25.", "",
          "| view, judge | quiet: rate / recall / mean / SD | sham: rate / recall / mean / SD | h | ICC 0.3: σ_within; β_b (marg.); β_a S1 / S2; observed at m_s/25 S1 / S2 | ICC 0.6: same | m_s |",
          "|---|---|---|---|---|---|---|"]
    for n in names:
        i = insts[n]; q, sh = i["quiet_prior"], i["sham_prior"]
        cc = [cal[f"{n}|{icc}|{REF_NOISE}|{R['rho']}"] for icc in ICCS]
        cs = ["{:.1f}; {} ({}); {} / {}; {:.1f} / {:.1f}".format(x["dgp"]["sig_w"], _f(x["beta_b"], 3), _f(x["beta_b_marginal"], 3), _f(x["beta_a"]["1"], 3), _f(x["beta_a"]["2"], 3),
                                                       x["observed_slope_x25_at_latent_m_s"]["1"], x["observed_slope_x25_at_latent_m_s"]["2"]) for x in cc]
        L.append(f"| {n} | {q['planted_unit_rate']:.3f} / {q['recall']:.3f} / {q['mean']:.1f} / {q['sd']:.1f} | {sh['planted_unit_rate']:.3f} / {sh['recall']:.3f} / {sh['mean']:.1f} / {sh['sd']:.1f} | {i['honest_path']:.3f} | {cs[0]} | {cs[1]} | {i['m_s']['m_s']:.2f} |")
    L.append("")
    miss = [(k, v["dgp"]["misses"], v["dgp"]["status"]) for k, v in cal.items() if v["dgp"].get("misses")]
    if miss:
        L.append("**Calibration targets not attainable** (the closest attainable value is used; target → achieved): " + "; ".join(
            f"{k.rsplit('|', 1)[0]}: " + ", ".join(f"{m} {d['target']:.3f} → {d['achieved']:.3f}" for m, d in ms.items()) for k, ms, st in miss)
            + ". A control-arm SD below what the call noise and the grid allow cannot be matched: the simulated control arm is wider than the observed one, which lowers the floor's margin.")
    else:
        L.append("Every calibration target is met within tolerance (rate 0.01, SD and mean 0.5) at every ICC and noise level.")
    noa = sorted({k.rsplit('|', 1)[0] + f" (S{q})" for k, v in cal.items() for q, b in v["beta_a"].items() if b is None})
    if noa:
        L.append(f"Form (a)'s alternative is not attainable on the observed scale (no latent effect gives an observed slope × 25 of m_s; P(present | m_s) is not defined and the cell cannot be readable): {', '.join(noa)}.")
    L.append("")
    L.append("By regime (planted-unit rate, recall, SD; n): " + "; ".join(
        f"{n}: " + ", ".join(f"{k} {v['planted_unit_rate']:.2f}/{v['recall']:.2f}/{v['sd']:.0f} ({v['n']})" for k, v in insts[n]["by_regime"].items()) for n in names) + ".")
    L.append("")
    L += MODEL_MD
    # ---- gate table
    L += ["## P3. The gate table (A6.6; 5-point call noise; each probability at the worse of ICC 0.3 and 0.6)", "",
          "Truth states: form (b) at a 75-minus-50 contrast of 0 and of 0.3, the contrast defined with the judge's true line maximum held at its mean (the scientific counterpart of O2's estimand; the fitted logistic model is an approximation to the threshold model, and its line covariate is the measured, not the true, maximum); "
          "form (a) at an observed score slope × 25 of 0 and of m_s on the 5-point grid. Floor and failed fits ('unfit') are counted as not read (A6.4). Readable: P(excluded | 0) ≥ 0.6 and P(present | 0.3) ≥ 0.6, each at the worse ICC (both ICCs shown). "
          "P(detect) = P(present or attenuated | 0.3), beside. Monte Carlo SE at 300 experiments: about 0.028 at 0.6, 0.029 at 0.5.", "",
          "| view, judge | form | layout | P(floor \\| 0) | P(unfit \\| 0) | P(excluded \\| 0) (ICC 0.3 / 0.6) | P(present \\| 0.3) (ICC 0.3 / 0.6) | P(attenuated \\| 0.3) | P(detect \\| 0.3) | P(inconcl. \\| 0) | P(inconcl. \\| 0.3) | P(floor or unfit \\| 0.3) | readable |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, t in g["table"].items():
        n, form, layout = k.split("|")
        bi = t["by_icc"]
        L.append(f"| {n} | ({form}) | {layout} | {t['P_floor_0']:.2f} | {t['P_unfit_0']:.2f} | {t['P_excl_0']:.2f} ({bi['0.3']['P_excl_0']:.2f} / {bi['0.6']['P_excl_0']:.2f}) | "
                 f"{t['P_present_alt']:.2f} ({bi['0.3']['P_present_alt']:.2f} / {bi['0.6']['P_present_alt']:.2f}) | {t['P_attenuated_alt']:.2f} | {t['P_detect_alt']:.2f} | {t['P_inconclusive_0']:.2f} | {t['P_inconclusive_alt']:.2f} | "
                 f"{t['P_not_read_alt']:.2f} | {'**yes**' if t['readable'] else 'no'} |")
    L.append("")
    L += ["### Gate outcome", ""]
    if g["readable_layouts"]:
        for l, v in g["readable_layouts"].items():
            L.append(f"- {l}: readable under {v['n_readable_instruments']} instrument-form(s) ({', '.join(v['readable'])}); carrying {v['carrying']} (sum {v['score']:.2f}).")
    else:
        L.append("- No (instrument, form, layout) is readable.")
    L.append(f"- Adopted by the gate: {g['adopted_by_gate'] or 'none'} ({g['basis']}); after the residual-bias trigger: {g['adopted'] or 'none'}.")
    if g.get("bias_trigger"):
        L.append(f"- Residual-bias trigger at the adopted layout: {json.dumps(g['bias_trigger'])}.")
    tt = R["too_thin"]
    if g["status"] == "unresolved":
        L.append(f"- Unresolved: readable at {g['unresolved_layout']}: {', '.join(g['readable_at_final']) or 'none'}; their residual-bias materiality (True = material, None = unknown): {json.dumps(g['ineligible_at_final'])}.")
    if tt:
        L.append(f"- Too thin (A6.6): best P(present | 0.3) anywhere {tt['best_present'][0]:.2f} ({tt['best_present'][1]}); "
                 f"instrument-forms clearing 0.6 with the tail doubled: {', '.join(tt['tail_doubled_cleared']) or 'none'}; **state: {tt['state']}**"
                 + (f" (missing cells: {', '.join(tt.get('missing', [])[:12])}{'…' if len(tt.get('missing', [])) > 12 else ''})" if tt.get("missing") else "") + ".")
    L.append("")
    # ---- beside readings of the same experiments
    L += ["### Beside readings of the same experiments (5-point noise, worse ICC; not gate inputs)", "",
          "O4: (b)'s contrast with the line covariate at its conditional mean given composition (linear in composition), the gap at its sample mean; beside it, line and gap both at their conditional means. "
          "Disattenuated (A6.5 (ii)): the composition coefficient (log-odds for (b)) divided by the partial reliability given the fitted covariates (Spearman-Brown of the two passes' residual correlation, computed in each experiment), "
          "and by the plain Spearman-Brown value; a log-odds-slope sensitivity, not an exact correction for this threshold model, and its interval is conditional on the estimated reliability (held fixed across replicates; O4's conditional means likewise). "
          "No reading is called *excluded* without it beside. Q1 versus Q3: 47.5 against 68.0, margin scaled by 20.5 / 25.", "",
          "| view, judge | form | layout | O4 (line): excl \\| 0 / pres \\| alt | O4 (line and gap) | disattenuated (partial) | disattenuated (Spearman-Brown) | Q1–Q3 | primary |", "|---|---|---|---|---|---|---|---|---|"]
    bc = R["beside_comps"]
    for k, t in g["table"].items():
        n, form, layout = k.split("|")
        cell = lambda c: (lambda v: f"{v['P_excl_0']:.2f} / {v['P_present_alt']:.2f}" if v else "—")(bc[c].get(k))
        L.append(f"| {n} | ({form}) | {layout} | {cell('75v50_o4')} | {cell('75v50_o4_joint')} | {cell('75v50_disatt')} | {cell('75v50_disatt_sb')} | {cell('q3vq1')} | {t['P_excl_0']:.2f} / {t['P_present_alt']:.2f} |")
    L.append("")
    # ---- residual bias
    L += ["## Residual null bias after the top-two gap covariate (A6.5(iii), A6.6)", "",
          "Mean point estimate under the null (truth 0), the worse ICC, with its Monte Carlo SE, over the experiments whose fit succeeded (conditional on a successful fit; an instrument with no successful fit at some ICC has an unknown bias, which never clears the trigger). "
          "(a): slope × 25 in score points, trigger at half of m_s; (b): the 75-minus-50 contrast, trigger at 0.15. "
          "A positive (b) bias leans toward a false *present*; a negative one toward a false *excluded*. Under the alternative, the mean estimate against the truth (0.3 for (b); m_s for (a)) is the attenuation, beside.", "",
          "| view, judge | form | layout | noise 0 | noise 5 | noise 10 | trigger bound | material at 5 | direction at 5 | mean estimate under the alternative (5-point noise, ICC 0.3 / 0.6) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for n in names:
        for form in ("a", "b"):
            for layout, (P, Q) in LAYOUTS.items():
                if form == "a" and not Q:
                    continue
                bb = [g["bias"].get(f"{n}|{form}|{layout}|{noise}") for noise in NOISES]
                if any(x is None for x in bb):
                    continue
                alt = "alt_a" if form == "a" else "alt_b"
                am = [_cellget(cells, f"{n}|{layout}|{icc}|{REF_NOISE}|{alt}", form, field="point_mean") for icc in ICCS]
                truth = insts[n]["m_s"]["m_s"] if form == "a" else MARGIN
                b5 = bb[1]["bias_worse_icc"]
                direction = ("toward a false present" if b5 > 0 else "toward a false excluded") if abs(b5) > 2 * bb[1]["mcse"] else "within MC error"
                L.append(f"| {n} | ({form}) | {layout} | " + " | ".join(f"{x['bias_worse_icc']:+.3f} ({x['mcse']:.3f})" for x in bb)
                         + f" | {bb[1]['trigger_bound']:.3f} | {'**yes**' if bb[1]['material'] else ('unknown' if bb[1]['material'] is None else 'no')} | {direction} | {_f(am[0], 3)} / {_f(am[1], 3)} (truth {truth:.3g}) |")
    L.append("")
    # ---- full tables
    L += ["## Simulation tables, every noise level and ICC", "",
          "Per cell: P(floor | 0); P(excluded | 0); P(inconclusive | 0); then under the alternative P(floor), P(present), P(attenuated), P(inconclusive); the bootstrap interval width of the "
          "model-predicted value at composition 75 (probability for (b), excess in score points for (a)) under the null; the Q1-versus-Q3 sensitivity (47.5 vs 68.0, margin scaled by 20.5/25): "
          "P(excluded | 0) and P(present | alternative); the partial reliability of composition given the layout's covariates (true over measured residual variance); for (b), the share of experiments fitted with the document factor, the share that fell back under O3 because more than 2.5 percent of the bootstrap fits failed with it, and the mean share of non-converged bootstrap fits in the model used.", ""]
    hdr = "| view, judge | layout | ICC | noise | form | floor\\|0 | excl\\|0 | inc\\|0 | floor\\|alt | pres\\|alt | att\\|alt | inc\\|alt | width at 75 | Q1–Q3 excl\\|0 | Q1–Q3 pres\\|alt | partial rel. | doc factor; O3 bootstrap fallback; non-conv. |"
    L += [hdr, "|" + "---|" * 17]
    for n in names:
        for layout, (P, Q) in LAYOUTS.items():
            for icc in ICCS:
                for noise in NOISES:
                    for form in (("a", "b") if Q else ("b",)):
                        alt = "alt_a" if form == "a" else "alt_b"
                        c0 = cells.get(f"{n}|{layout}|{icc}|{noise}|null", {})
                        c1 = cells.get(f"{n}|{layout}|{icc}|{noise}|{alt}", {})
                        if form not in c0 or form not in c1:
                            continue
                        z, o = c0[form], c1[form]
                        dn = f"{z['doc_factor_share']:.2f}; {z.get('fallback_bootstrap_share', float('nan')):.2f}; {z['boot_nonconverged_mean']:.3f}" if form == "b" else "—"
                        L.append(f"| {n} | {layout} | {icc} | {noise:g} | ({form}) | {z['75v50']['floor']:.2f} | {z['75v50']['excluded']:.2f} | {z['75v50']['inconclusive']:.2f} | "
                                 f"{o['75v50']['floor']:.2f} | {o['75v50']['present']:.2f} | {o['75v50']['attenuated']:.2f} | {o['75v50']['inconclusive']:.2f} | {z['width_at_75_mean']:.3f} | "
                                 f"{z['q3vq1']['excluded']:.2f} | {o['q3vq1']['present']:.2f} | {c0['partial_rel_mean']:.3f} | {dn} |")
    L.append("")
    # ---- beside
    L += ["## Beside the gate (not gate inputs)", ""]
    mt = R["beside_gates"]["marginal_truth"]
    L.append(f"- **Form (b)'s truth defined marginally** (the 0.3 contrast averaged over the design's lines rather than at the mean line): readable layouts {list(mt[0]) or 'none'}; would adopt {mt[1] or 'none'}.")
    for m, v in R["beside_gates"]["multiples"].items():
        L.append(f"- **Effect at {m} × the margin** (contrast {MARGIN * float(m):.2f} for (b); slope × 25 = {m} × m_s for (a)), reading still against the margin: readable layouts {list(v[0]) or 'none'}; would adopt {v[1] or 'none'}.")
    L.append("")
    L += ["P(present) at the reference noise, the worse ICC, by truth state (primary 0.3 / m_s; (b) marginal; 1.5 ×; 2 ×):", "",
          "| view, judge | form | layout | P(excl \\| 0) | primary | (b) marginal | 1.5 × | 2 × |", "|---|---|---|---|---|---|---|---|"]
    for k, t in g["table"].items():
        n, form, layout = k.split("|")
        mg = R["beside_tables"]["marginal_truth"].get(k, {}).get("P_present_alt") if form == "b" else None
        m15 = R["beside_tables"]["multiples"]["1.5"].get(k, {}).get("P_present_alt")
        m2 = R["beside_tables"]["multiples"]["2.0"].get(k, {}).get("P_present_alt")
        L.append(f"| {n} | ({form}) | {layout} | {t['P_excl_0']:.2f} | {t['P_present_alt']:.2f} | {_f(mg)} | {_f(m15)} | {_f(m2)} |")
    L.append("")
    if R["sensitivity_tables"]:
        L += ["### Sensitivities (5-point noise, worse ICC; primary truth states)", "",
              "| variant | view, judge | form | layout | P(floor \\| 0) | P(excl \\| 0) | P(present \\| 0.3) | P(detect \\| 0.3) | readable |", "|---|---|---|---|---|---|---|---|---|"]
        for tag, tab in R["sensitivity_tables"].items():
            for k, t in tab.items():
                n, form, layout = k.split("|")
                L.append(f"| {tag} | {n} | ({form}) | {layout} | {t['P_floor_0']:.2f} | {t['P_excl_0']:.2f} | {t['P_present_alt']:.2f} | {t['P_detect_alt']:.2f} | {'**yes**' if t['readable'] else 'no'} |")
        L.append("")
    # ---- disattenuation
    L += ["## Disattenuation factors (A6.5(ii))", "",
          f"Spearman-Brown reliability of the two-pass mean: **{tr['spearman_brown']:.3f}** (r {tr['pearson_pass1_pass2']:.3f}). Partial reliability given the rater covariates "
          f"(Spearman-Brown of the residual correlation): **{tr['partial']['spearman_brown']:.3f}** (A6.5 said about 0.87). In the simulation, the partial reliability given each layout's covariates "
          "(true over measured residual variance, mean over experiments, null, 5-point noise; range over instruments and ICCs): "
          + ", ".join(_rel_range(cells, l) for l in LAYOUTS) + ". Without the singleton arm the covariates are the rater's, so the value sits near the data's; with it the "
          "judge's singleton scores replace the rater's line covariates and explain less of composition, so the partial reliability rises toward the Spearman-Brown value.", ""]
    L += READINGS_MD
    # ---- estimate
    est, costs = R["estimate"], R["unit_costs"]
    L += ["## P4. The estimate per layout (A6.12; no cap; for Aravind's approval with the adopted layout)", "",
          "Per-unit dollars (realised): " + "; ".join(f"{k} " + ", ".join(f"{b} ${v:.4f}" for b, v in c.items() if b != "used") + f" → **${c['used']:.4f}**" for k, c in costs.items()) + ". The higher basis is used.", "",
          "| layout | lone plants per view (quiet + controls + sham) | singleton plants per per-agent view | units, all views | **dollars** | stop at 2× | controls' singletons add-on |", "|---|---|---|---|---|---|---|"]
    for l, e in est.items():
        r0 = e["rows"][names[0]]
        L.append(f"| {l} | {r0['lone_units']} | {r0['singleton_units']} | {e['units']} | **${e['dollars']:.2f}** | ${e['stop_line_2x']:.2f} | ${e['controls_singleton_addon_dollars']:.2f} |")
    L.append("")
    L += ["| layout | " + " | ".join(est["T1"]["rows"]) + " |", "|---|" + "---|" * len(est["T1"]["rows"])]
    for l, e in est.items():
        L.append(f"| {l} | " + " | ".join(f"{r['units']} / ${r['dollars']:.2f}" for r in e["rows"].values()) + " |")
    L.append("")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- CLI

def cmd_inputs(a):
    root = Path(a.root)
    triples = load_stimuli(root)
    mom = moments(triples)
    insts = {}
    for view, judge in INSTRUMENTS:
        insts[f"{view}:{judge}"] = instrument_inputs(load_instrument(root, view, judge))
    files = [RATER + "/key-b3.json"] + [f"{RATER}/ratings-b3-{s}-p{p}.jsonl" for s in ("statements", "triples") for p in (1, 2)] \
        + list(CHECKS.values()) + [B1, SEAL, OPUS_NULL] + list(T1.values())
    out = {"version": "b3-power-v3/inputs", "seed": SEED, "moments": mom, "instruments": insts,
           "inputs_sha256": {f: sha256(root / f) for f in files}}
    Path(a.out_json).write_text(json.dumps(out, indent=1))
    print(json.dumps({"n_quiet": mom["n_quiet"], "by_writer": mom["n_quiet_by_writer"], "composition": mom["composition"],
                      "test_retest": mom["test_retest"]}, indent=1))


def _quiet_design(root):
    triples = load_stimuli(root)
    return design(quiet(triples))


def bind_inputs(root: Path, inputs_path: str):
    """Provenance captured before any computation: this script's hash, the inputs file's hash, and a check that
    every raw file the simulation reads (the rater key and pass files, the writers' checks) still has the hash
    the inputs file recorded. A mismatch stops the run."""
    inputs = json.loads(Path(inputs_path).read_text())
    bad = [f for f, h in inputs["inputs_sha256"].items() if sha256(root / f) != h]
    if bad:
        raise SystemExit(f"raw inputs changed since {inputs_path} was written: {bad}")
    return {"script_sha256": sha256(__file__), "inputs_sha256_file": sha256(inputs_path),
            "raw_inputs_checked": sorted(inputs["inputs_sha256"])}, inputs


def cmd_simulate(a):
    root = Path(a.root)
    prov, inputs = bind_inputs(root, a.inputs)
    mom = inputs["moments"]
    D = design_with_moments(_quiet_design(root), mom)
    cal = calibrate_all(inputs, D)
    cells = build_cells(inputs, D, cal, quick=a.quick)
    if a.only:
        cells = [c for c in cells if a.only in c[0]]
    print(f"{len(cells)} cells", flush=True)
    res = _pool_map(run_cell, cells, a.workers)
    out = {"version": "b3-power-v3/sim", **prov,
           "seed": SEED, "experiments": cells[0][9] if cells else None,
           "replicates": cells[0][10] if cells else None, "rho": RHO,
           "calibration": cal,
           "cells": res}
    Path(a.out_json).write_text(json.dumps(out, indent=1))


def sensitivity_cells(inputs, D, which, layouts, n_exp, R):
    """Sensitivities at the reference noise, both ICCs: the regime priors (lowest and highest non-alarming
    regime planted-unit rate), the judge-rater line correlation (0.3, 0.7) and the doubled tail (A6.6)."""
    mom = inputs["moments"]
    q1q3 = (mom["composition"]["q1"], mom["composition"]["q3"])
    cells, skipped = [], []  # skipped: alternatives not attainable under the variant (no beta shows the margin)
    for ii, (view, judge) in enumerate(INSTRUMENTS):
        name = f"{view}:{judge}"
        inp = inputs["instruments"][name]
        m_s = inp["m_s"]["m_s"]
        variants = []
        if which in ("regime", "all"):
            regs = {k: v for k, v in inp["by_regime"].items() if k in [f"{a}:{b}" for a, b in QUIET_REGIMES]}
            lo = min(regs, key=lambda k: regs[k]["planted_unit_rate"]); hi = max(regs, key=lambda k: regs[k]["planted_unit_rate"])
            for tag, rk in (("regime_low", lo), ("regime_high", hi)):
                inp2 = dict(inp); inp2["quiet_prior"] = regs[rk]
                variants.append((f"{tag}={rk}", inp2, RHO, D))
        if which in ("rho", "all"):
            for rho in (0.3, 0.7):
                variants.append((f"rho={rho}", inp, rho, D))
        if which in ("tail", "all"):
            variants.append(("tail_doubled", inp, RHO, design_with_moments(D, mom, tail_double=True)))
        for vi, (tag, inp2, rho, D2) in enumerate(variants):
            for ci, icc in enumerate(ICCS):
                c = calibrate_one(D2, inp2, icc, REF_NOISE, rho)
                for li, layout in enumerate(layouts):
                    Q = LAYOUTS[layout][1]
                    prim = [x for x in truths_for(c, Q, REF_NOISE, m_s) if x[0] in ("null", "alt_b", "alt_a")]
                    for want in (("alt_b", "alt_a") if Q else ("alt_b",)):
                        if want not in [x[0] for x in prim]:
                            skipped.append(f"{name}|{layout}|{icc}|{REF_NOISE}|{want}|{tag}")
                    for ti, (truth, beta, forms) in enumerate(prim):
                        key = f"{name}|{layout}|{icc}|{REF_NOISE}|{truth}|{tag}"
                        cells.append((key, D2, c["dgp"], layout, truth, beta, m_s, q1q3, forms, n_exp, R, (100 + ii, vi, li, ci, ti)))
    return cells, skipped


def cmd_sensitivity(a):
    root = Path(a.root)
    prov, inputs = bind_inputs(root, a.inputs)
    D = design_with_moments(_quiet_design(root), inputs["moments"])
    layouts = a.layouts.split(",")
    cells, skipped = sensitivity_cells(inputs, D, a.which, layouts, 20 if a.quick else EXPERIMENTS, 200 if a.quick else REPLICATES)
    print(f"{len(cells)} cells", flush=True)
    res = _pool_map(run_cell, cells, a.workers)
    Path(a.out_json).write_text(json.dumps({"version": "b3-power-v3/sensitivity", **prov,
                                            "which": a.which, "layouts": layouts, "cells": res, "unattainable": skipped}, indent=1))


# ---------------------------------------------------------------- Part 2 (brief 15 A6.13): one latent margin, the corrected gate

CARRIER = "dossier_iso:opus48"  # A6.13.3: form (a) on Opus 4.8's isolated dossier
SECOND = "P_author:opus48"      # form (a) on Opus 4.8's zero-context P_author
CEILING = 0.85                  # A6.13.5: (b) is not read where the quiet lone recall exceeds it
BIAS_B_V3B = 0.05               # A6.13.5: (b)'s residual-bias trigger on the contrast
REF_ICC = 0.3                   # the reference cell of the latent margin (ICC 0.3, 5-point noise; A6.13.2's verified figures)
ROLE = {f"{CARRIER}|a": "carrier", f"{SECOND}|a": "second", f"{CARRIER}|b": "supporting", f"{SECOND}|b": "supporting"}
PMAX = {"excluded": "holds", "present": "falsified", "attenuated": "partly_missed"}
TWO_STEP = {("excluded", "present"), ("present", "excluded")}
NOT_READ = ("floor", "unfit", "unavailable", "ceiling")


def role(name, form):
    if form == "a" and name.startswith("dossier_live"):
        return "n/a (live view, A6.13.3)"  # a live reading of a singleton would show its co-planted siblings
    return ROLE.get(f"{name}|{form}", "descriptive")


def margins_v3b(D, cal, inputs):
    """A6.13.2: the latent margin is beta_b, the latent composition effect at which form (b)'s 75-minus-50 contrast is
    0.3, at the reference cell (ICC 0.3, 5-point noise); m_s is form (a)'s error-free coefficient x 25 at it (one
    singleton placement). Beside: the old A6.4 value (superseded), and each form's error-free reading of the same
    latent effect in every other ICC, noise and singleton cell (the drift from the reference)."""
    out = {}
    for view, judge in INSTRUMENTS:
        name = f"{view}:{judge}"
        ref = cal[f"{name}|{REF_ICC}|{REF_NOISE}|{RHO}"]
        beta = ref["beta_b"]
        drift = {}
        for icc in ICCS:
            for noise in NOISES:
                c = cal[f"{name}|{icc}|{noise}|{RHO}"]
                drift[f"{icc}|{noise}"] = {"a_x25_S1": 25 * observable_slope_a(D, c["dgp"], beta, 1),
                                           "a_x25_S2": 25 * observable_slope_a(D, c["dgp"], beta, 2),
                                           "b_contrast": true_contrast_conditional(D, c["dgp"], beta),
                                           "b_contrast_x1.5": true_contrast_conditional(D, c["dgp"], 1.5 * beta)}
        old = inputs["instruments"][name]["m_s"]
        out[name] = {"latent_margin": beta, "latent_margin_x25": 25 * beta, "m_s": drift[f"{REF_ICC}|{REF_NOISE}"]["a_x25_S1"],
                     "m_s_old": old["m_s"], "m_s_old_rule": old["rule"], "drift": drift}
    return out


def build_cells_v3b(inputs, D, cal, margins, quick=False):
    """The corrected gate's grid: every instrument and layout, ICC 0.3 and 0.6; at 5-point noise the null, the latent
    margin and 1.5 times it; at 0 and 10 points the null and the margin. Both forms read the same world (A6.13.2);
    form (b) with the Firth fit and the ceiling clause."""
    q1q3 = (inputs["moments"]["composition"]["q1"], inputs["moments"]["composition"]["q3"])
    n_exp, R = (20, 200) if quick else (EXPERIMENTS, REPLICATES)
    cells = []
    for ii, (view, judge) in enumerate(INSTRUMENTS):
        name = f"{view}:{judge}"
        m_s, beta = margins[name]["m_s"], margins[name]["latent_margin"]
        for ci, icc in enumerate(ICCS):
            for ni, noise in enumerate(NOISES):
                c = cal[f"{name}|{icc}|{noise}|{RHO}"]
                truths = [("null", 0.0), ("margin", beta)] + ([("x1.5", 1.5 * beta)] if noise == REF_NOISE else [])
                for li, layout in enumerate(LAYOUTS):
                    forms = ("a", "b") if LAYOUTS[layout][1] else ("b",)
                    for ti, (truth, b) in enumerate(truths):
                        cells.append((f"{name}|{layout}|{icc}|{noise}|{truth}", D, c["dgp"], layout, truth, b, m_s, q1q3, forms,
                                      n_exp, R, (200 + ii, li, ci, ni, ti), {"firth": True, "ceiling": CEILING}))
    return cells


def run_cell_v3b(args):
    (key, D, dgp, layout, truth, beta, m_s, q1q3, forms, n_exp, R, seed_key, kw) = args
    rng = np.random.default_rng([SEED] + list(seed_key))
    rows = [experiment(rng, D, dgp, layout, beta, m_s, q1q3, R=R, forms=forms, **kw) for _ in range(n_exp)]
    return key, summarise_cell(rows, layout, truth)


def gate_values_v3b(cells, name, form, layout, noise=REF_NOISE, comp="75v50"):
    """A6.13.1, per instrument, form and layout, each probability at the worse of the two ICCs: P(excluded | 0),
    P(excluded | truth on the margin), P(LB > 0 | 0); P(present | 1.5 x margin) beside (5-point noise only).
    Readable: P(excluded | 0) >= 0.6, P(excluded | margin) <= 0.10 and P(LB > 0 | 0) <= 0.10. A reading not read
    (floor, unfit, ceiling) counts as neither excluded nor LB > 0."""
    ex0, exm, lb0, p15, nr0, nrm, by = [], [], [], [], [], [], {}
    for icc in ICCS:
        n0 = cells.get(f"{name}|{layout}|{icc}|{noise}|null", {}).get(form, {}).get(comp)
        nm = cells.get(f"{name}|{layout}|{icc}|{noise}|margin", {}).get(form, {}).get(comp)
        if n0 is None or nm is None:
            return None
        n15 = cells.get(f"{name}|{layout}|{icc}|{noise}|x1.5", {}).get(form, {}).get(comp)
        ex0.append(n0["excluded"]); exm.append(nm["excluded"]); lb0.append(n0["lb_above_0"])
        p15.append(n15["present"] if n15 else None)
        nr0.append(sum(n0.get(o, 0.0) for o in NOT_READ)); nrm.append(sum(nm.get(o, 0.0) for o in NOT_READ))
        by[str(icc)] = {"P_excl_0": ex0[-1], "P_excl_margin": exm[-1], "P_lb_0": lb0[-1], "P_present_x1.5": p15[-1],
                        "ceiling_0": n0.get("ceiling", 0.0), "unfit_0": n0.get("unfit", 0.0), "floor_0": n0.get("floor", 0.0)}
    pres = min(p15) if all(x is not None for x in p15) else None
    readable = min(ex0) >= 0.6 and max(exm) <= 0.10 and max(lb0) <= 0.10
    return {"P_excl_0": min(ex0), "P_excl_margin": max(exm), "P_lb_0": max(lb0), "P_present_x1.5": pres,
            "P_not_read_0": max(nr0), "P_not_read_margin": max(nrm), "readable": readable,
            "score": (min(ex0) + pres) if pres is not None else None, "neutral": min(min(ex0), 1 - max(exm)), "by_icc": by,
            "role": role(name, form)}


def gate_table_v3b(cells, noise=REF_NOISE):
    tab = {}
    for layout, (P, Q) in LAYOUTS.items():
        for view, judge in INSTRUMENTS:
            name = f"{view}:{judge}"
            for form in (("a", "b") if Q else ("b",)):
                g = gate_values_v3b(cells, name, form, layout, noise)
                if g is not None:
                    tab[f"{name}|{form}|{layout}"] = g
    return tab


def residual_bias_v3b(cells, margins):
    """The residual null bias (mean point under the null over successful fits, the worse ICC), against half of the new
    m_s for (a) and 0.05 for (b) (A6.13.5); unknown never clears the trigger."""
    out = {}
    for view, judge in INSTRUMENTS:
        name = f"{view}:{judge}"
        for layout in LAYOUTS:
            for form in ("a", "b"):
                for noise in NOISES:
                    vals = [cells.get(f"{name}|{layout}|{icc}|{noise}|null", {}).get(form) for icc in ICCS]
                    if any(v is None for v in vals):
                        continue
                    b = [v["75v50"]["point_mean"] for v in vals]
                    bound = margins[name]["m_s"] / 2 if form == "a" else BIAS_B_V3B
                    if any(not np.isfinite(x) for x in b):
                        out[f"{name}|{form}|{layout}|{noise}"] = {"bias_worse_icc": float("nan"), "by_icc": dict(zip(map(str, ICCS), b)), "bound": bound, "material": None}
                        continue
                    i = int(np.argmax(np.abs(b)))
                    out[f"{name}|{form}|{layout}|{noise}"] = {"bias_worse_icc": b[i], "mcse": vals[i]["75v50"]["point_mcse"],
                                                              "by_icc": dict(zip(map(str, ICCS), b)), "bound": bound, "material": abs(b[i]) > bound}
    return out


def adopt_v3b(tab, bias):
    """A6.6's choice under A6.13, for the carrier (form (a) on Opus 4.8's isolated dossier; every form-(a) layout has
    the singleton arm): its readable layouts in order of P(excluded | 0) + P(present | 1.5 x margin) (power first).
    For each, A6.6's residual-bias trigger at a single-singleton layout ((a) above half of m_s, or (b) above 0.05,
    for the carrier's instrument) moves it to the two-placement singleton variant; a candidate is adopted when the
    carrier is readable at its final layout with a known, non-material (a) bias, else the next is tried. The second
    named instrument never carries at adoption: A6.13.4 hands it the verdict only in an experiment where the
    carrier is at floor or unfit, which the joint run simulates. With no eligible layout, the layout maximising
    min(P(excluded | 0), 1 - P(excluded | margin)) for the carrier is adopted and labelled descriptive (A6.13.6, as
    Part 2's item 3 words it)."""
    mat = lambda form, layout: bias.get(f"{CARRIER}|{form}|{layout}|{REF_NOISE}", {}).get("material")
    ok = sorted((l for l in LAYOUTS if LAYOUTS[l][1] > 0 and tab.get(f"{CARRIER}|a|{l}", {}).get("readable")),
                key=lambda l: -tab[f"{CARRIER}|a|{l}"]["score"])
    second_ok = [l for l in LAYOUTS if LAYOUTS[l][1] > 0 and tab.get(f"{SECOND}|a|{l}", {}).get("readable")]
    out = {"carrier": f"{CARRIER}|a", "carrier_readable_layouts": ok, "second_readable_layouts": second_ok, "trail": []}
    for cand in ok:
        final, trig = cand, None
        if LAYOUTS[cand][1] == 1:
            fired = {f: mat(f, cand) for f in ("a", "b")}
            trig = {"at": cand, "material": fired}
            if any(v is True for v in fired.values()):
                final = cand.replace("S1", "S2")
                trig["moved_to"] = final
        a_mat = mat("a", final)
        eligible = bool(tab.get(f"{CARRIER}|a|{final}", {}).get("readable")) and a_mat is False
        out["trail"].append({"candidate": cand, "final": final, "trigger": trig, "a_bias_material": a_mat, "eligible": eligible})
        if eligible:
            out.update(adopted=final, label="readable", chosen_before_trigger=cand, trigger=trig,
                       b_bias_material_at_final=mat("b", final), reason=None)
            return out
    cand = [l for l in LAYOUTS if LAYOUTS[l][1] > 0 and f"{CARRIER}|a|{l}" in tab]
    best = max(cand, key=lambda l: tab[f"{CARRIER}|a|{l}"]["neutral"])
    out.update(adopted=best, label="descriptive", chosen_before_trigger=None, trigger=None, b_bias_material_at_final=mat("b", best),
               reason="no layout is readable for the carrier with a non-material (a) bias after A6.6's trigger; the layout maximising "
                      "min(P(excluded | 0), 1 - P(excluded | margin)) for the carrier")
    return out


# ---- A6.13.4: the combined verdict, carrier-first, simulated on shared plants

def instrument_label(out, bias_b):
    """A6.13.4 per instrument: form (a)'s label is the label; form (b) changes it only on a two-step conflict
    (excluded against present), and counts as present or attenuated only when its lower bound stays above 0 after
    subtracting the cell's simulated null bias. A reading not read is its own state."""
    a = "floor" if not out.get("floor_a", False) else out["a"]["75v50"]["outcome"]
    braw = "floor" if not out["floor_b"] else out["b"]["75v50"]["outcome"]
    beff = None
    if braw == "excluded":
        beff = "excluded"
    elif braw in ("attenuated", "present"):
        lo = out["b"]["75v50"]["lo"]
        if lo is not None and bias_b is not None and np.isfinite(bias_b) and lo - bias_b > 0:
            beff = braw
    label = "inconclusive" if (a, beff) in TWO_STEP else a
    return {"label": label, "a": a, "b": braw, "b_effective": beff, "b_conflict": (a, beff) in TWO_STEP}


def combine(carrier, second, second_readable):
    """A6.13.4 across instruments, carrier-first. The carrier's label is the verdict; the second named instrument
    confirms it when it agrees, makes it inconclusive only on a two-step conflict, and is otherwise beside; at floor,
    unfit or unreadable it drops out. If the carrier is at floor or unfit, the second's label is the verdict (the
    fallback carrier)."""
    drop = ("floor", "unfit")
    s = second if (second_readable and second not in drop) else None
    if carrier in drop:
        v = s if s is not None else "no_verdict"
        return {"verdict": v, "fallback": True, "confirmed": False, "second_used": s is not None, "conflict": False}
    if s is not None and (carrier, s) in TWO_STEP:
        return {"verdict": "inconclusive", "fallback": False, "confirmed": False, "second_used": True, "conflict": True}
    return {"verdict": carrier, "fallback": False, "confirmed": s == carrier, "second_used": s is not None, "conflict": False}


def joint_cells_v3b(inputs, D, cal, margins, tab, null_b, quick=False, rhos_view=(1.0, 0.0)):
    """A6.13.4's operating characteristics: per singleton layout, ICC and truth (null, or both instruments at their
    latent margins), the carrier and the second named instrument read the same simulated plants (true composition,
    the control arm's triple draws, and the judge's line deviations, shared fully or drawn independently beside);
    placement and call noise are each view's own. (b)'s downgrade subtracts that cell's simulated null bias."""
    q1q3 = (inputs["moments"]["composition"]["q1"], inputs["moments"]["composition"]["q3"])
    n_exp, R = (20, 200) if quick else (EXPERIMENTS, REPLICATES)
    cells = []
    for li, layout in enumerate(l for l in LAYOUTS if LAYOUTS[l][1] > 0):
        sec_ok = bool(tab.get(f"{SECOND}|a|{layout}", {}).get("readable"))
        for ci, icc in enumerate(ICCS):
            dc, ds = cal[f"{CARRIER}|{icc}|{REF_NOISE}|{RHO}"]["dgp"], cal[f"{SECOND}|{icc}|{REF_NOISE}|{RHO}"]["dgp"]
            for ti, truth in enumerate(("null", "margin")):
                for vi, rv in enumerate(rhos_view):
                    betas = (0.0, 0.0) if truth == "null" else (margins[CARRIER]["latent_margin"], margins[SECOND]["latent_margin"])
                    bb = (null_b.get(f"{CARRIER}|{layout}|{icc}"), null_b.get(f"{SECOND}|{layout}|{icc}"))
                    cells.append((f"{layout}|{icc}|{truth}|eta_shared={rv}", D, dc, ds, layout, betas,
                                  (margins[CARRIER]["m_s"], margins[SECOND]["m_s"]), q1q3, sec_ok, bb, rv, n_exp, R, (300, li, ci, ti, vi)))
    return cells


def run_joint(args):
    (key, D, dc, ds, layout, betas, m_s, q1q3, sec_ok, bb, rv, n_exp, R, seed_key) = args
    rng = np.random.default_rng([SEED] + list(seed_key))
    n = len(D["C"]); lam = D["partial_rel"]
    rows = []
    for _ in range(n_exp):
        Ct = D["C_fit"] + lam * D["C_res"] + math.sqrt(lam * (1 - lam) * D["C_res_var"]) * rng.standard_normal(n)
        eta = rng.standard_normal((n, 3)); sham_z = rng.standard_normal(N_SHAM)
        eta2 = rv * eta + math.sqrt(1 - rv * rv) * rng.standard_normal((n, 3))
        kw = {"firth": True, "ceiling": CEILING}
        oc = experiment(rng, D, dc, layout, betas[0], m_s[0], q1q3, R=R, forms=("a", "b"), shared={"Ct": Ct, "eta": eta, "sham_z": sham_z}, **kw)
        os_ = experiment(rng, D, ds, layout, betas[1], m_s[1], q1q3, R=R, forms=("a", "b"), shared={"Ct": Ct, "eta": eta2, "sham_z": sham_z}, **kw)
        lc, ls = instrument_label(oc, bb[0]), instrument_label(os_, bb[1])
        v = combine(lc["label"], ls["label"], sec_ok)
        rows.append({"carrier": lc, "second": ls, **v, "pmax": PMAX.get(v["verdict"], "inconclusive")})
    k = len(rows)
    share = lambda f: sum(1 for r in rows if f(r)) / k
    summ = {"n": k, "second_readable": sec_ok, "bias_b_used": {"carrier": bb[0], "second": bb[1]},
            **{f"P_{o}": share(lambda r, o=o: r["pmax"] == o) for o in ("holds", "falsified", "partly_missed", "inconclusive")},
            "P_confirmed": share(lambda r: r["confirmed"]), "P_fallback": share(lambda r: r["fallback"]),
            "P_conflict_across": share(lambda r: r["conflict"]), "P_conflict_within_carrier": share(lambda r: r["carrier"]["b_conflict"]),
            "carrier_labels": {o: share(lambda r, o=o: r["carrier"]["label"] == o) for o in ("excluded", "attenuated", "present", "inconclusive", "floor")},
            "second_labels": {o: share(lambda r, o=o: r["second"]["label"] == o) for o in ("excluded", "attenuated", "present", "inconclusive", "floor")}}
    return key, summ


def cmd_simulate_v3b(a):
    root = Path(a.root)
    prov, inputs = bind_inputs(root, a.inputs)
    D = design_with_moments(_quiet_design(root), inputs["moments"])
    cal = calibrate_all(inputs, D)
    margins = margins_v3b(D, cal, inputs)
    cells = build_cells_v3b(inputs, D, cal, margins, quick=a.quick)
    if a.only:
        cells = [c for c in cells if a.only in c[0]]
    print(f"{len(cells)} cells", flush=True)
    res = _pool_map(run_cell_v3b, cells, a.workers)
    out = {"version": "b3-power-v3b/sim", **prov, "seed": SEED, "experiments": cells[0][9] if cells else None,
           "replicates": cells[0][10] if cells else None, "rho": RHO, "margins": margins, "calibration": cal, "cells": res}
    Path(a.out_json).write_text(json.dumps(out, indent=1))


def null_means_b(cells):
    """(b)'s simulated null bias per instrument, layout and ICC at 5-point noise (A6.13.4's downgrade)."""
    out = {}
    for k, v in cells.items():
        name, layout, icc, noise, truth = k.split("|")
        if truth == "null" and noise == str(REF_NOISE) and "b" in v:
            out[f"{name}|{layout}|{icc}"] = v["b"]["75v50"]["point_mean"]
    return out


def cmd_joint_v3b(a):
    root = Path(a.root)
    prov, inputs = bind_inputs(root, a.inputs)
    sim = json.loads(Path(a.sim).read_text())
    if sim.get("script_sha256") != prov["script_sha256"]:
        raise SystemExit("the v3b simulation was produced by another script version")
    D = design_with_moments(_quiet_design(root), inputs["moments"])
    cal, margins = sim["calibration"], sim["margins"]
    tab = gate_table_v3b(sim["cells"])
    cells = joint_cells_v3b(inputs, D, cal, margins, tab, null_means_b(sim["cells"]), quick=a.quick)
    print(f"{len(cells)} joint cells", flush=True)
    res = _pool_map(run_joint, cells, a.workers)
    Path(a.out_json).write_text(json.dumps({"version": "b3-power-v3b/joint", **prov, "sim_sha256": sha256(a.sim), "cells": res}, indent=1))


FIRST_RUN = {"md": "work/stage3/b3/power-simulation-v3.md", "json": "work/stage3/b3/power-simulation-v3.json"}


def cmd_report_v3b(a):
    root = Path(a.root)
    prov_now, inputs = bind_inputs(root, a.inputs)
    sim = json.loads(Path(a.sim).read_text())
    joint = json.loads(Path(a.joint).read_text())
    here = prov_now["script_sha256"]
    prov = {"report_script": here, "sim_script": sim.get("script_sha256"), "joint_script": joint.get("script_sha256"),
            "inputs_file": prov_now["inputs_sha256_file"], "sim_inputs": sim.get("inputs_sha256_file"), "joint_inputs": joint.get("inputs_sha256_file"),
            "joint_sim": joint.get("sim_sha256"), "sim_file": sha256(a.sim)}
    prov["consistent"] = (prov["sim_script"] == here == prov["joint_script"] and prov["sim_inputs"] == prov["inputs_file"] == prov["joint_inputs"]
                          and prov["joint_sim"] == prov["sim_file"])
    cells = sim["cells"]
    tables = {str(nz): gate_table_v3b(cells, nz) for nz in NOISES}
    tab = tables[str(REF_NOISE)]
    bias = residual_bias_v3b(cells, sim["margins"])
    adoption = adopt_v3b(tab, bias)
    est = estimate(unit_costs(root))
    first = {k: {"path": v, "sha256": sha256(root / v) if (root / v).exists() else None} for k, v in FIRST_RUN.items()}
    R = {"version": "b3-power-v3b/report", "seed": SEED, "experiments": sim["experiments"], "replicates": sim["replicates"], "rho": sim["rho"],
         "provenance": prov, "first_run": first, "margins": sim["margins"], "gate": tab, "gate_by_noise": tables, "bias": bias,
         "adoption": adoption, "joint": joint["cells"], "estimate": est, "unit_costs": unit_costs(root),
         "constants": {"carrier": f"{CARRIER}|a", "second": f"{SECOND}|a", "ceiling": CEILING, "bias_b_trigger": BIAS_B_V3B, "ref_icc": REF_ICC, "ref_noise": REF_NOISE},
         "cells": cells, "script_sha256": here, "inputs_sha256": inputs["inputs_sha256"]}
    Path(a.out_json).write_text(json.dumps(R, indent=1, default=str))
    Path(a.out_md).write_text(render_v3b(R))


def _p(x):
    return "—" if x is None else f"{x:.2f}"


def _joint_worse(J, layout):
    """The combined verdict's operating characteristics at a layout, the worse ICC for each error, shared line deviations."""
    rows = [J.get(f"{layout}|{icc}|{t}|eta_shared=1.0") for icc in ICCS for t in ("null", "margin")]
    if any(r is None for r in rows):
        return None
    n0 = [J[f"{layout}|{icc}|null|eta_shared=1.0"] for icc in ICCS]
    nm = [J[f"{layout}|{icc}|margin|eta_shared=1.0"] for icc in ICCS]
    return {"holds_0": min(r["P_holds"] for r in n0), "falsified_0": max(r["P_falsified"] for r in n0),
            "holds_margin": max(r["P_holds"] for r in nm), "falsified_margin": min(r["P_falsified"] for r in nm)}


def render_v3b(R) -> str:
    ad, M, tab, J, est = R["adoption"], R["margins"], R["gate"], R["joint"], R["estimate"]
    L = []
    lay = ad["adopted"]
    ck = f"{ad['carrier'].split('|')[0]}|a|{lay}"
    cg = tab.get(ck, {})
    jw = _joint_worse(J, lay)
    L.append(f"**Adopted layout (A6.13): {lay}, {ad['label']}.** Carried by form (a) on {ad['carrier'].split('|')[0]} (the carrier); "
             f"P(excluded | 0) {_p(cg.get('P_excl_0'))}, P(excluded | margin) {_p(cg.get('P_excl_margin'))}, P(LB > 0 | 0) {_p(cg.get('P_lb_0'))}, "
             f"P(present | 1.5 × margin) {_p(cg.get('P_present_x1.5'))} (worse ICC, 5-point noise)"
             + (f"; combined verdict P(holds | 0) {jw['holds_0']:.2f}, P(falsified | 0) {jw['falsified_0']:.2f}, P(holds | margin) {jw['holds_margin']:.2f}, P(falsified | margin) {jw['falsified_margin']:.2f}" if jw else "")
             + (f". {ad['reason']}." if ad.get("reason") else "."))
    L.append("")
    prov = R["provenance"]
    if not prov["consistent"]:
        L.append(f"**Provenance check failed:** {json.dumps(prov)}. The numbers below are not bound to this code.")
        L.append("")
    fr = R["first_run"]
    L.append(f"Brief 20 Part 2 (brief 15 A6.13; $0; `work/checks/stage3_b3_power_v3.py` {R['script_sha256'][:12]}…, simulation, joint run and report from one script and inputs: {prov['consistent']}; "
             f"seed {R['seed']}; {R['experiments']} experiments per cell; payload-clustered percentile bootstrap, {R['replicates']} replicates). "
             f"The first run under A6.6's original gate stays in the record: `{fr['md']['path']}` {(fr['md']['sha256'] or '')[:8]}…, `{fr['json']['path']}` {(fr['json']['sha256'] or '')[:8]}…. "
             "Inputs are files on disk and none is a B3 outcome; counts, ids and aggregates only.")
    L.append("")
    # ---- summary
    readable = sorted(k for k, g in tab.items() if g["readable"])
    by_layout = {l: [k for k in readable if k.endswith(f"|{l}")] for l in LAYOUTS}
    mat_b = sorted(k.rsplit("|", 1)[0] for k, v in R["bias"].items() if k.endswith(f"|{REF_NOISE}") and k.split("|")[1] == "b" and v["material"])
    mat_a = sorted(k.rsplit("|", 1)[0] for k, v in R["bias"].items() if k.endswith(f"|{REF_NOISE}") and k.split("|")[1] == "a" and v["material"])
    ceil = sorted({k.rsplit("|", 1)[0] for k, g in tab.items() if k.split("|")[1] == "b" and max(v["ceiling_0"] for v in g["by_icc"].values()) > 0.5})
    L += ["## Summary", ""]
    trail = "; ".join(f"{t['candidate']}" + (f" → {t['final']} (trigger {json.dumps(t['trigger']['material'])})" if t["trigger"] and t["trigger"].get("moved_to") else "")
                      + f": {'eligible' if t['eligible'] else 'not eligible'}" for t in ad["trail"])
    L.append(f"- **Adoption:** the carrier {ad['carrier']} is readable at {', '.join(ad['carrier_readable_layouts']) or 'no layout'} "
             f"(the second named instrument at {', '.join(ad['second_readable_layouts']) or 'no layout'}; it never carries at adoption, only in an experiment where the carrier is at floor or unfit). "
             f"Candidates in order of P(excluded | 0) + P(present | 1.5 × margin), with A6.6's residual-bias trigger: {trail or 'none'}. Final: {lay}, {ad['label']}.")
    def cell_names(keys):
        keys = [k for k in keys if not tab[k]["role"].startswith("n/a")]
        return ", ".join("{} ({}, {})".format(k.split("|")[0], k.split("|")[1], tab[k]["role"]) for k in keys) or "none"
    L.append("- **Readable cells under A6.13.1 (5-point noise, worse ICC; form (a) on the live dossiers left out, not applicable under A6.13.3):** "
             + "; ".join(f"{l}: {cell_names(v)}" for l, v in by_layout.items()) + ".")
    L.append(f"- **One latent margin (A6.13.2):** m_s for the carrier {M[CARRIER]['m_s']:.2f} (was {M[CARRIER]['m_s_old']:.2f}); second {M[SECOND]['m_s']:.2f} (was {M[SECOND]['m_s_old']:.2f}). Full table below.")
    L.append(f"- **Residual null bias (5-point noise):** (b) above 0.05 at: {', '.join(mat_b) or 'none'}; (a) above half of m_s at: {', '.join(mat_a) or 'none'}.")
    L.append(f"- **Ceiling clause:** (b) not read in most experiments (quiet lone recall above {CEILING}) for: {', '.join(ceil) or 'none'}.")
    L.append(f"- **Estimate (P4, unchanged):** {lay} ${est[lay]['dollars']:.2f} (stop at ${est[lay]['stop_line_2x']:.2f}); every layout in the P4 table below.")
    L.append("")
    # ---- m_s
    L += ["## m_s under A6.13.2 (old rule beside, superseded)", "",
          f"The latent margin β* is form (b)'s β_b at the reference cell (ICC {REF_ICC}, {REF_NOISE:g}-point call noise): the latent composition effect at which (b)'s 75-minus-50 contrast, with the judge's true line maximum at its mean, is 0.3. "
          "m_s is form (a)'s error-free coefficient × 25 at β* (excess on true composition with form (a)'s covariates, one singleton placement). Both forms' alternatives are this same latent effect. "
          "Beside: each form's error-free reading of β* in the other ICC and singleton cells at 5-point noise (the drift from the reference; the 0- and 10-point drift is in the JSON, `margins.<instrument>.drift`).", "",
          "| view, judge | β* × 25 | **m_s (A6.13.2)** | m_s old (A6.4, superseded) | old rule | (a) × 25 at β*: ICC 0.3 S2; ICC 0.6 S1 / S2 | (b) contrast at β*: ICC 0.6; at 1.5 β*: ICC 0.3 / 0.6 |",
          "|---|---|---|---|---|---|---|"]
    for view, judge in INSTRUMENTS:
        n = f"{view}:{judge}"; m = M[n]; d = m["drift"]
        r3, r6 = d[f"{REF_ICC}|{REF_NOISE}"], d[f"0.6|{REF_NOISE}"]
        L.append(f"| {n} | {m['latent_margin_x25']:.1f} | **{m['m_s']:.2f}** | {m['m_s_old']:.2f} | {'primary' if 'primary' in m['m_s_old_rule'] else 'fallback'} | "
                 f"{r3['a_x25_S2']:.2f}; {r6['a_x25_S1']:.2f} / {r6['a_x25_S2']:.2f} | {r6['b_contrast']:.3f}; {r3['b_contrast_x1.5']:.3f} / {r6['b_contrast_x1.5']:.3f} |")
    L.append("")
    # ---- gate
    L += ["## The gate under A6.13.1 (5-point call noise; worse of ICC 0.3 and 0.6, both shown)", "",
          "Readable: P(excluded | 0) ≥ 0.6 (power to confirm P-max), P(excluded | margin) ≤ 0.10 (false confirmation), P(LB > 0 | 0) ≤ 0.10 (false refutation). P(present | 1.5 × margin) beside: the ability to label a large effect. "
          "Readings not read (floor, unfit, (b)'s ceiling) count as neither *excluded* nor LB > 0; their share is shown. Form (b): Firth fit and the ceiling clause. Role from A6.13.3; descriptive cells carry no verdict. Monte Carlo SE at 300 experiments: about 0.017 at 0.10, 0.028 at 0.6.", "",
          "| view, judge | form | role | layout | P(excl \\| 0) (0.3 / 0.6) | P(excl \\| margin) (0.3 / 0.6) | P(LB > 0 \\| 0) (0.3 / 0.6) | P(present \\| 1.5×) | not read \\| 0 / \\| margin | readable |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    order = sorted(tab, key=lambda k: ({"carrier": 0, "second": 1, "supporting": 2}.get(tab[k]["role"], 3), k.split("|")[0], k.split("|")[1], list(LAYOUTS).index(k.split("|")[2])))
    for k in order:
        g = tab[k]; n, form, layout = k.split("|"); b = g["by_icc"]
        L.append(f"| {n} | ({form}) | {g['role']} | {layout} | {g['P_excl_0']:.2f} ({b['0.3']['P_excl_0']:.2f} / {b['0.6']['P_excl_0']:.2f}) | "
                 f"{g['P_excl_margin']:.2f} ({b['0.3']['P_excl_margin']:.2f} / {b['0.6']['P_excl_margin']:.2f}) | {g['P_lb_0']:.2f} ({b['0.3']['P_lb_0']:.2f} / {b['0.6']['P_lb_0']:.2f}) | "
                 f"{_p(g['P_present_x1.5'])} | {g['P_not_read_0']:.2f} / {g['P_not_read_margin']:.2f} | {'**yes**' if g['readable'] else 'no'} |")
    L.append("")
    L += ["### The gate at 0 and 10 points of call noise (readable cells; worse ICC: P(excl | 0) / P(excl | margin) / P(LB > 0 | 0))", ""]
    for nz in ("0.0", "10.0"):
        t2 = R["gate_by_noise"][nz]
        rd = [f"{k} {g['P_excl_0']:.2f} / {g['P_excl_margin']:.2f} / {g['P_lb_0']:.2f}" for k, g in sorted(t2.items())
              if g["readable"] and not g["role"].startswith("n/a")]
        cr = t2.get(f"{CARRIER}|a|{lay}")
        L.append(f"- {float(nz):g} points: readable {', '.join(rd) or 'none'}; the carrier at {lay}: " + (f"{cr['P_excl_0']:.2f} / {cr['P_excl_margin']:.2f} / {cr['P_lb_0']:.2f}" if cr else "—") + ".")
    L.append("")
    # ---- bias
    L += ["## Residual null bias (A6.13.5: (b) trigger 0.05; (a) half of the new m_s)", "",
          "Mean point estimate under the null over successful fits, the worse ICC; the Monte Carlo SE at 5 points beside. Positive (b) leans toward a false *present*.", "",
          "| view, judge | form | layout | noise 0 | noise 5 (MC SE) | noise 10 | bound | material at 5 |", "|---|---|---|---|---|---|---|---|"]
    for view, judge in INSTRUMENTS:
        n = f"{view}:{judge}"
        for form in ("a", "b"):
            for layout in LAYOUTS:
                bb = [R["bias"].get(f"{n}|{form}|{layout}|{nz}") for nz in NOISES]
                if any(x is None for x in bb):
                    continue
                f5 = bb[1]
                L.append(f"| {n} | ({form}) | {layout} | {bb[0]['bias_worse_icc']:+.3f} | {f5['bias_worse_icc']:+.3f} ({f5.get('mcse', float('nan')):.3f}) | {bb[2]['bias_worse_icc']:+.3f}"
                         + f" | {f5['bound']:.3f} | {'**yes**' if f5['material'] else ('unknown' if f5['material'] is None else 'no')} |")
    L.append("")
    # ---- joint
    L += ["## The combined verdict's operating characteristics (A6.13.4; 5-point noise)", "",
          "The carrier (form (a), Opus 4.8 isolated dossier) and the second named instrument (form (a), Opus 4.8 zero-context `P_author`) read the same simulated plants: the same true composition, the same control-arm triples and, primary, the same judge line deviations (shared η); "
          "placement and call noise are each view's own. Under 'margin' both instruments sit at their own latent margins. Per instrument (b) changes (a)'s label only on a two-step conflict and counts as *present* or *attenuated* only when its lower bound minus the cell's simulated null bias stays above 0; "
          "the second instrument drops out where it is not readable at the layout. P-max: *holds* on *excluded*, *falsified* on *present*, *partly missed* on *attenuated*, *inconclusive* otherwise. Beside: the line deviations drawn independently for the two views (η independent).", "",
          "| layout | ICC | η | second readable | P(holds \\| 0) | P(falsified \\| 0) | P(partly \\| 0) | P(inconcl. \\| 0) | P(holds \\| margin) | P(falsified \\| margin) | P(partly \\| margin) | P(inconcl. \\| margin) | confirmed \\| 0 / \\| margin | fallback \\| 0 / \\| margin |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for layout in [l for l in LAYOUTS if LAYOUTS[l][1] > 0]:
        for icc in ICCS:
            for rv in ("1.0", "0.0"):
                z, m = J.get(f"{layout}|{icc}|null|eta_shared={rv}"), J.get(f"{layout}|{icc}|margin|eta_shared={rv}")
                if not z or not m:
                    continue
                L.append(f"| {layout} | {icc} | {'shared' if rv == '1.0' else 'independent'} | {z['second_readable']} | {z['P_holds']:.2f} | {z['P_falsified']:.2f} | {z['P_partly_missed']:.2f} | {z['P_inconclusive']:.2f} | "
                         f"{m['P_holds']:.2f} | {m['P_falsified']:.2f} | {m['P_partly_missed']:.2f} | {m['P_inconclusive']:.2f} | {z['P_confirmed']:.2f} / {m['P_confirmed']:.2f} | {z['P_fallback']:.2f} / {m['P_fallback']:.2f} |")
    L.append("")
    # ---- estimate
    L += ["## P4. The estimate per layout (unchanged from the first run)", "",
          "| layout | lone plants per view | singleton plants per per-agent view | units, all views | **dollars** | stop at 2× |", "|---|---|---|---|---|---|"]
    for l, e in est.items():
        r0 = e["rows"][f"{INSTRUMENTS[0][0]}:{INSTRUMENTS[0][1]}"]
        L.append(f"| {l} | {r0['lone_units']} | {r0['singleton_units']} | {e['units']} | **${e['dollars']:.2f}** | ${e['stop_line_2x']:.2f} |")
    L.append("")
    L += V3B_READINGS
    return "\n".join(L) + "\n"


V3B_READINGS = [
    "## Readings and deviations (Part 2)", "",
    "1. **The latent margin's reference cell.** β_b depends on the ICC and the call noise (they set the within-triple spread the conditional contrast is read against). A6.13.2's verified figures (β_b × 25 of 21.5 and 24.8 for the two Opus 4.8 instruments) are the ICC 0.3, 5-point cell, so β* is fixed there for each instrument and S1 pre-registers one m_s per instrument; the other cells' readings of the same β* are tabled as drift.",
    "2. **Truth states.** 'margin' is β* and '1.5 × margin' is 1.5 β*, the same latent effect for both forms in every ICC and noise cell; each form is read against its own margin (0.3 for (b), m_s for (a)).",
    "3. **The gate** holds only at the worse ICC (the smaller P(excluded | 0), the larger P(excluded | margin) and P(LB > 0 | 0)) at 5-point noise; the 0- and 10-point gates are listed. A reading not read counts as neither *excluded* nor LB > 0, so its share is shown beside: a cell that is often not read can meet the two upper bounds without information.",
    "4. **Adoption** follows A6.6 restricted to the named readings (A6.13.3): the carrier's readable layouts (every form-(a) layout carries the singleton arm) in order of P(excluded | 0) + P(present | 1.5 × margin) ('power first'); for each, A6.6's residual-bias trigger at a single-singleton layout ((a) above half of the new m_s, (b) above 0.05, for the carrier's instrument) moves it to the two-placement singleton variant, which is adopted only if the carrier is readable there with a non-material (a) bias, else the next candidate is tried. The second named instrument does not carry at adoption: A6.13.4 makes it the verdict only in an experiment where the carrier is at floor or unfit, and the joint run simulates that. With no eligible layout, Part 2's item 3 rule applies (the layout maximising min(P(excluded | 0), 1 − P(excluded | margin)) for the carrier, labelled descriptive); A6.13.6's text says the highest P(excluded | 0), and Part 2's neutral rule is used as the later instruction.",
    "4a. **Form (a) on the live dossiers** is simulated with independent singleton plants, but A6.13.3 rules it out (a live reading of a singleton would show its co-planted siblings); those rows are labelled not applicable and left out of the readable list.",
    "5. **The joint run** shares the true composition, the control-arm triple draws and the judge's standardised line deviations between the two Opus 4.8 views (the same judge reading the same lines); placement and call noise are independent. The fully independent line deviations are the other bound. The second instrument's readability is read from this file's gate table; (b)'s downgrade subtracts the null bias of the same instrument, layout and ICC at 5-point noise.",
    "6. **Form (b)** now uses the Firth penalised fit (A6.13.5) in the point fit and every bootstrap replicate, by Fisher scoring with step halving on the penalised log-likelihood (undamped scoring can oscillate on a sparse document); O3's document-factor fallback and the unfit rule are kept and now rarely bite. The ceiling clause is applied per experiment on the observed quiet lone recall (above 0.85: (b) is not read).",
    "7. **m_s's old values** (A6.4's rule on B1's reference plants) are kept beside as the superseded calibration; the first run's file is unchanged.",
    "8. **The estimate** is P4's, unchanged (same units, same per-unit bases).", ""]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("inputs"); s.add_argument("--out-json", required=True); s.set_defaults(fn=cmd_inputs)
    s = sub.add_parser("simulate"); s.add_argument("--inputs", required=True); s.add_argument("--out-json", required=True)
    s.add_argument("--workers", type=int, default=1); s.add_argument("--quick", action="store_true"); s.add_argument("--only", default="")
    s.set_defaults(fn=cmd_simulate)
    s = sub.add_parser("sensitivity"); s.add_argument("--inputs", required=True); s.add_argument("--out-json", required=True)
    s.add_argument("--which", default="all"); s.add_argument("--layouts", default=",".join(LAYOUTS))
    s.add_argument("--workers", type=int, default=1); s.add_argument("--quick", action="store_true")
    s.set_defaults(fn=cmd_sensitivity)
    s = sub.add_parser("simulate-v3b"); s.add_argument("--inputs", required=True); s.add_argument("--out-json", required=True)
    s.add_argument("--workers", type=int, default=1); s.add_argument("--quick", action="store_true"); s.add_argument("--only", default="")
    s.set_defaults(fn=cmd_simulate_v3b)
    s = sub.add_parser("joint-v3b"); s.add_argument("--inputs", required=True); s.add_argument("--sim", required=True); s.add_argument("--out-json", required=True)
    s.add_argument("--workers", type=int, default=1); s.add_argument("--quick", action="store_true")
    s.set_defaults(fn=cmd_joint_v3b)
    s = sub.add_parser("report-v3b"); s.add_argument("--inputs", required=True); s.add_argument("--sim", required=True); s.add_argument("--joint", required=True)
    s.add_argument("--out-json", required=True); s.add_argument("--out-md", required=True)
    s.set_defaults(fn=cmd_report_v3b)
    s = sub.add_parser("report"); s.add_argument("--inputs", required=True); s.add_argument("--sim", required=True)
    s.add_argument("--sensitivity", default=""); s.add_argument("--out-json", required=True); s.add_argument("--out-md", required=True)
    s.set_defaults(fn=cmd_report)
    a = p.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
