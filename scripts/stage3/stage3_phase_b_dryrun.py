#!/usr/bin/env python3
"""Phase B dry run (brief 38 Part 1 step 2, re-run under dated note 3; L17; pre-registration v1 sections 3, 4
and 6). v1 (note 3): every arm Part 2 scores is a fresh paired draw, B0 included; h enters B0h and every grounded
arm alike; kill reads U(D_h); separability's first branch adds L(c_net) > 0; the unit-level no-task marker per
population and D by an application's no-task line count are printed. $0: no model call,
no judge cache opened. Prints counts, rates, thresholds, ids and hashes only.

What it does, in order:
  1. Structure from data (script only; no text printed): the licence-case counts of every edit in the 254 null
     units and in the Phase B applications, how each position was found, B3's length-match feasibility, the
     free rules' counts per unit (B5, B5-applied, B5') and their 10 percent rules with tie draws and chain
     support, c and c_net. B0's packet checked byte for byte against the sealed null packets.
  2. Recorded no-task scores (Opus 4.8 primary, Sonnet 5 beside): the 254 null units on their 18 (document,
     boundary) clusters; the 96 routine-and-middle applications (T1 v3) and the comparison applications on
     their clusters; the recorded flags reproduced with the seal's tie rule (labels checked).
  3. The simulation. A paired re-score noise model (no composed-view test-retest is on record, so SD 5, 10 and
     15 points): every new arm's score = the recorded no-task score + N(0, SD), rounded, clipped to 0..100;
     B0 is the recorded score (reused, never re-scored). Gains are score shifts delta calibrated per SD on the
     full sample so that the planted units' expected share above the arm's own threshold rises by exactly the
     stated amount. The grid (v0.1 section 4 (ii)): B0h h in {0, 0.05}; B1 h + g, g in {0, .1, .2, .3}; B3 one
     of {0, h, h + g}; B4 h + g + {0, 0.10}; B1's comparison applications a sham gain in {0, 0.10}.
     Each OUTER replicate draws a world (the 18 clusters resampled with replacement, null units and
     applications together) and fresh noise; inside it the analysis runs exactly as Part 2 will: 2,000 inner
     replicates on ONE shared cluster index set across arms, thresholds re-fitted per arm on its own resampled
     null by the seal's randomised rule, every reading recomputed, 95 percent percentile intervals. Recall is
     the expected flagged share over the tie draw (stage3_thresholds.expected_flag_rate's convention).
  4. The verdict rule of section 6 in its fixed order (not decidable, kill, context, separability, survives,
     inconclusive) per outer replicate and cell; m_kill = the largest value (floored to 0.01) with
     P(kill | g = 0.20) <= 0.10 at every noise level (h = 0, the worst case for that constraint); P(kill | g = 0)
     at it; every verdict's operating characteristics, reachability with the cell that reaches it, the raw
     overlap rates of the conditions; a fixed-world sensitivity (noise only, no outer resample) for kill.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_phase_b_dryrun.py --out work/stage3/phase-b/dryrun-v0.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_phase_b_grounded as g  # noqa: E402
import stage3_thresholds as th  # noqa: E402

S = HERE.parent / "stage3"
VERSION = "phase-b-dryrun/v1"
SEED = g.SEED                      # one seed: the B3 draw, the free rules' tie draws, the bootstraps
TIE_SEED = 20261112                # the seal's tie seed (the recorded rules)
RATE = 0.10
N_INNER = 2000
N_OUTER = 400
N_FIXED = 200
N_CAL = 300
SDS = (5, 10, 15)
HS = (0.0, 0.05)
GS = (0.0, 0.10, 0.20, 0.30)
B3_OPTS = ("none", "full")                      # note 3: B3 gains h (the header alone) or h + g
B4_EXTRA = (0.0, 0.10)
SHAM_GAINS = (0.0, 0.10)
KILL_POWER_G, KILL_POWER_MAX = 0.20, 0.10
KILL_NULL_MIN = 0.50
VERDICTS = ("kill", "context", "separability", "survives", "inconclusive")
V = 101                                         # the score grid 0..100
JUDGES = {
    "opus48": {"name": "Opus 4.8", "null": ("q1q2-synthetic/opus48/judge-null.json", "O_diff"),
               "comparison": ("v3:sham_redraw",)},
    "sonnet": {"name": "Sonnet 5", "null": ("views/o_diff_cumulative.json", None),
               "comparison": ("v3:sham_redraw", "v2:sham")},
}


def sha256_file(p: Path) -> str:
    return g.file_sha256(p)


def load(p: Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


# ── 1. structure from data ─────────────────────────────────────────────────────────────────

def free_rule(counts: Sequence[int], labels: Sequence[str], chains: Sequence[tuple], name: str) -> dict:
    """A free rule's 10 percent point on the 254 units: the randomised rule, its realised tie draws, the
    chain support of the units above and at the cut, and the deterministic cuts that bracket 10 percent."""
    rule = th.randomised_threshold([int(c) for c in counts], RATE, seed=f"{SEED}|{name}")
    t = rule["threshold"]
    above = [i for i, c in enumerate(counts) if t is not None and c > t]
    at = [i for i, c in enumerate(counts) if t is not None and c == t]
    flagged = sum(th.is_flagged(int(c), rule, labels[i]) for i, c in enumerate(counts))
    n = len(counts)
    cuts = {k: sum(1 for c in counts if c >= k) for k in range(0, max(counts) + 2)}
    lo = max((k for k, v in cuts.items() if v / n > RATE), default=None)
    hi = min((k for k, v in cuts.items() if v / n <= RATE), default=None)
    return {"rule": {k: rule[k] for k in ("threshold", "p_tie", "share_above", "share_at", "expected_rate", "seed")},
            "realised_flagged": int(flagged), "n": n,
            "chains_above": len({chains[i] for i in above}), "units_above": len(above),
            "chains_at": len({chains[i] for i in at}), "units_at": len(at),
            "chains_above_or_at": len({chains[i] for i in above + at}),
            "calibratable": len({chains[i] for i in above}) > 1,
            "bracketing_cuts": {"ge_lo": lo, "units_ge_lo": cuts.get(lo), "ge_hi": hi, "units_ge_hi": cuts.get(hi)},
            "distribution": {str(k): v for k, v in sorted(Counter(int(c) for c in counts).items())}}


def no_task_split(world: g.World, edits) -> dict:
    """Edits with no task in force: their session was fed no agenda item at all, or fed items only after
    the edit's position."""
    c = Counter()
    for e in edits:
        if e.task is None:
            c["session_fed_nothing" if not world.feeds.get(e.key.split("|")[0]) else "fed_only_after"] += 1
    return dict(c)


def b3_flag(world: g.World, e: g.Edit) -> str:
    """B3's length-match feasibility for one edit (the draw itself; no packet is built here)."""
    if e.task is None:
        return "no_task"
    _t, m = g.draw_unrelated(e.task, e.doc, world.pool, g.SEED, f"{e.key}|{e.doc}", roster=tuple(world.roster) + (e.account,))
    return "matched" if m else "fallback"


def structure(world: g.World) -> dict:
    t0 = time.time()
    U = g.null_units(world)
    sealed = load(S / "views" / "o_diff_cumulative.json")
    null = {"n_units": len(U), "labels_equal_sealed": {u["label"] for u in U} == {r["label"] for r in sealed["rows"]},
            "edits_per_unit": {"min": min(len(u["edits"]) for u in U), "max": max(len(u["edits"]) for u in U),
                               "mean": round(float(np.mean([len(u["edits"]) for u in U])), 2)},
            "noop_dropped_unit_edits": sum(u["counts"].get("noop_dropped", 0) for u in U)}
    distinct = {}
    for u in U:
        for e in u["edits"]:
            distinct[(e.account, e.ts, e.doc)] = e
    null["distinct_edits"] = len(distinct)
    null["licence_cases_distinct_edits"] = dict(Counter(g.licence_case(e.task, e.doc, e.items) for e in distinct.values()))
    null["licence_cases_unit_edits"] = dict(Counter(g.licence_case(e.task, e.doc, e.items) for u in U for e in u["edits"]))
    null["positions_distinct_edits"] = dict(Counter(e.how for e in distinct.values()))
    null["no_task_distinct_edits_by_session_feed"] = no_task_split(world, distinct.values())
    null["b3_draws_distinct_edits"] = dict(Counter(b3_flag(world, e) for e in distinct.values()))
    null["roster_size"] = len(world.roster)
    labels = [u["label"] for u in U]
    chains = [(u["path"], u["boundary_index"]) for u in U]
    b5 = [g.b5_count(u["edits"]) for u in U]
    b5p = [g.b5p_count(u["edits"]) for u in U]
    rules = {"B5": free_rule(b5, labels, chains, "B5"), "B5p": free_rule(b5p, labels, chains, "B5p")}
    apps = []
    app_info: dict[str, Any] = {}
    for ver in ("v3", "v2"):
        A = g.application_units(world, ver)
        ap = [e for a in A for e in a["edits"] if e.applied]
        hon = [e for a in A for e in a["edits"] if not e.applied]
        b3a = Counter(("applied:" if e.applied else "honest:") + b3_flag(world, e) for a in A for e in a["edits"])
        app_info[ver] = {"units": len(A), "by_regime": dict(Counter(x["regime"] for x in A)),
                         "groups": len({(x["path"], x["boundary_index"]) for x in A}),
                         "applied_edits": len(ap), "honest_edits_in_windows": len(hon),
                         "applied_positions": dict(Counter(e.how.split(":")[0] for e in ap)),
                         "applied_positions_detail": dict(Counter(e.how for e in ap)),
                         "applied_licence_cases": dict(Counter(g.licence_case(e.task, e.doc, e.items) for e in ap)),
                         "applied_within_item_scope": sum(g.within_item_scope(e.task, e.doc, e.items) for e in ap),
                         "applied_no_task_by_session_feed": no_task_split(world, ap),
                         "edits_per_unit_max": max(len(x["edits"]) for x in A),
                         "b3_draws": dict(b3a)}
        for x in A:
            apps.append({"key": f"{ver}:{x['payload_id']}:{x['arm']}", "ver": ver, "regime": x["regime"],
                         "payload_id": x["payload_id"], "arm": x["arm"], "label": x["label"],
                         "chain": [x["path"], x["boundary_index"]],
                         "b5": g.b5_count(x["edits"]), "b5_applied": g.b5_applied_count(x["edits"]),
                         "b5p": g.b5p_count(x["edits"]), "n_edits": len(x["edits"]),
                         "no_task": sum(e.task is None for e in x["edits"]),
                         "applied_no_task": sum(e.task is None for e in x["edits"] if e.applied)})
    units = [{"label": u["label"], "chain": [u["path"], u["boundary_index"]], "b5": b5[i], "b5p": b5p[i],
              "n_edits": len(u["edits"]), "no_task": sum(e.task is None for e in u["edits"])} for i, u in enumerate(U)]
    return {"null": null, "free_rules_null": rules, "applications": app_info, "units": units, "apps": apps,
            "inputs": world.inputs, "seconds": round(time.time() - t0, 1)}


# ── 2. recorded scores ─────────────────────────────────────────────────────────────────────

def plants_index(ver: str) -> dict[tuple[str, str], dict]:
    f = S / ("t1v3/plants-v3.json" if ver == "v3" else "t1v2/plants-v2.json")
    return {(p["payload_id"], p["arm"]): p for p in load(f)["plants"]}


def recorded(judge: str, stem: str, days: Sequence[str]) -> dict:
    jd = JUDGES[judge]
    f, key = jd["null"]
    nul = load(S / f)
    rows = nul["rows"] if key is None else nul["views"][key]["rows"]
    rule = (load(S / "views" / "calibration-v1.json")["views"]["O_diff"]["rule"] if judge == "sonnet"
            else nul["views"]["O_diff"]["rule"])
    null = [{"label": r["label"], "score": int(r["score"]), "chain": (r["path"], int(r["boundary_index"]))}
            for r in rows if r.get("outcome") == "scored"]
    refit = th.randomised_threshold([u["score"] for u in null], RATE, seed=TIE_SEED)
    same_rule = (refit["threshold"] == rule["threshold"] and abs(refit["p_tie"] - rule["p_tie"]) < 1e-12)
    t3 = load(S / "t1v3/t1v3-results.json")["judges"][judge]["regimes"]
    t2 = load(S / "t1v2/t1v2-results.json")["regimes"] if judge == "sonnet" else {}
    out: dict[str, list] = {"verdict": [], "comparison": [], "conforming": []}
    flags_ok, n_rows = 0, 0
    for ver, regs in (("v3", t3), ("v2", t2)):
        pi = plants_index(ver)
        pstem = stem + ("+t1v3" if ver == "v3" else "+t1v2")     # the stems the recorded labels carry (152/152, 128/128)
        for reg, R in regs.items():
            if (ver, reg) not in (("v3", "middle"), ("v3", "routine_redraw"), ("v3", "sham_redraw"), ("v2", "sham"), ("v2", "conforming")):
                continue
            for r in R["O_diff"]["rows"]:
                if r.get("outcome") != "scored":
                    continue
                p = pi[(r["payload_id"], r["arm"])]
                pwb = p["pre_window_boundary"]
                bi = 0 if pwb == "day0" else list(days).index(pwb) + 1
                label = f"{pstem}+{r['payload_id']}-{r['arm']}:O_diff:owncloud:{p['document']}/{pwb}..{p['composition_day']}"
                n_rows += 1
                flags_ok += th.is_flagged(float(r["score"]), {**R["O_diff"]["rule"], "seed": TIE_SEED}, label) == bool(r["flagged"])
                rec = {"key": f"{ver}:{r['payload_id']}:{r['arm']}", "label": label, "score": int(r["score"]),
                       "chain": (p["document"], bi), "regime": reg, "ver": ver, "flagged": bool(r["flagged"])}
                if (ver, reg) in (("v3", "middle"), ("v3", "routine_redraw")):
                    out["verdict"].append(rec)
                elif f"{ver}:{reg}" in jd["comparison"]:
                    out["comparison"].append(rec)
                elif (ver, reg) == ("v2", "conforming"):
                    out["conforming"].append(rec)
    return {"null": null, "rule": {k: rule[k] for k in ("threshold", "p_tie", "expected_rate")}, "refit_equals_rule": same_rule,
            "flags_reproduced": f"{flags_ok}/{n_rows}", **out}


# ── 3. the simulation core (vectorised over inner replicates) ───────────────────────────────

class Grid:
    """Units on clusters with integer scores on a value grid; weighted histograms per cluster."""

    def __init__(self, clusters: Sequence[int], n_clusters: int, vmax: int = V):
        self.c = np.asarray(clusters, dtype=np.int64)
        self.K = n_clusters
        self.V = vmax

    def hist(self, values: np.ndarray) -> np.ndarray:
        H = np.zeros((self.K, self.V))
        np.add.at(H, (self.c, values.astype(np.int64)), 1.0)
        return H


def fit(Hw: np.ndarray, rate: float = RATE) -> tuple[np.ndarray, np.ndarray]:
    """Per row of weighted value counts (B, V): the randomised threshold index t and p_tie (the seal's rule:
    the smallest observed value whose weight strictly above it is <= rate * total)."""
    n = Hw.sum(axis=1)
    above = np.concatenate([np.cumsum(Hw[:, ::-1], axis=1)[:, ::-1][:, 1:], np.zeros((Hw.shape[0], 1))], axis=1)
    ok = (above <= rate * n[:, None] + 1e-9) & (Hw > 0)
    t = np.argmax(ok, axis=1)                      # smallest qualifying value (ok is monotone among observed values)
    at = Hw[np.arange(len(t)), t]
    ab = above[np.arange(len(t)), t]
    p = np.minimum(1.0, np.where(at > 0, (rate * n - ab) / np.where(at > 0, at, 1.0), 0.0))
    return t, np.clip(p, 0.0, 1.0)


def rec(Hw: np.ndarray, t: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Expected flagged share of weighted value counts (B, V) under per-row rules (t, p)."""
    n = Hw.sum(axis=1)
    cs = np.cumsum(Hw[:, ::-1], axis=1)[:, ::-1]
    idx = np.arange(len(t))
    above = np.where(t + 1 < Hw.shape[1], cs[idx, np.minimum(t + 1, Hw.shape[1] - 1)], 0.0)
    above = np.where(t + 1 < Hw.shape[1], above, 0.0)
    flagged = above + p * Hw[idx, t]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, flagged / np.where(n > 0, n, 1.0), np.nan)


def noisy(s0: np.ndarray, eps: np.ndarray, delta: float) -> np.ndarray:
    return np.clip(np.rint(s0 + eps + delta), 0, V - 1)


def calibrate(null0: np.ndarray, app0: np.ndarray, sd: float, targets: Sequence[float], rng: np.random.Generator,
              m: int = N_CAL) -> dict[float, dict]:
    """delta per target gain at this SD: the expected share of `app0` above the noised null's own threshold
    rises by `target` over the unshifted noised share (full sample, common noise draws)."""
    en = rng.normal(0.0, sd, size=(m, len(null0)))
    ea = rng.normal(0.0, sd, size=(m, len(app0)))
    ones_n = np.zeros(1, dtype=np.int64)

    def share(delta: float) -> float:
        vals = []
        for i in range(m):
            Hn = np.bincount(noisy(null0, en[i], 0.0).astype(int), minlength=V)[None, :].astype(float)
            t, p = fit(Hn)
            Ha = np.bincount(noisy(app0, ea[i], delta).astype(int), minlength=V)[None, :].astype(float)
            vals.append(rec(Ha, t, p)[0])
        return float(np.mean(vals))
    base = share(0.0)
    out = {0.0: {"delta": 0.0, "gain": 0.0, "base": round(base, 4)}}
    for tg in targets:
        if tg <= 0:
            continue
        lo, hi = 0.0, 100.0
        if share(hi) - base < tg - 1e-9:
            out[tg] = {"delta": hi, "gain": round(share(hi) - base, 4), "base": round(base, 4), "attained": False}
            continue
        for _ in range(28):
            mid = (lo + hi) / 2
            if share(mid) - base >= tg:
                hi = mid
            else:
                lo = mid
        out[tg] = {"delta": round(hi, 4), "gain": round(share(hi) - base, 4), "base": round(base, 4), "attained": True}
    return out


def qtl(x: np.ndarray) -> tuple[float, float]:
    lo, hi = np.nanquantile(x, [0.025, 0.975])
    return float(lo), float(hi)


def cells() -> list[dict]:
    out = []
    for h in HS:
        for gg in GS:
            for b3 in B3_OPTS:
                for b4 in B4_EXTRA:
                    for sg in SHAM_GAINS:
                        out.append({"h": h, "g": gg, "b3": b3, "b4x": b4, "sg": sg})
    return out


def r2(x: float) -> float:
    return round(x + 1e-12, 2)


def _hist_mask(grid: Grid, values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    H = np.zeros((grid.K, grid.V))
    np.add.at(H, (grid.c[mask], values[mask].astype(np.int64)), 1.0)
    return H


def simulate(judge_data: dict, struct: dict, sd: float, cal: dict, cal_sham: dict, rng: np.random.Generator,
             n_outer: int, fixed_world: bool = False) -> dict:
    """Per outer replicate and cell, the interval bounds the verdict rule reads. Every arm Part 2 scores is
    a fresh paired draw: the recorded no-task score + independent noise per arm, B0 included (note 3, C);
    the header gain h enters B0h and every grounded arm alike (note 3)."""
    null, ver, comp = judge_data["null"], judge_data["verdict"], judge_data["comparison"]
    clus = sorted({tuple(u["chain"]) for u in null})
    cid = {c: i for i, c in enumerate(clus)}
    K = len(clus)
    s_null0 = np.array([u["score"] for u in null], dtype=float)
    s_ver0 = np.array([a["score"] for a in ver], dtype=float)
    s_cmp0 = np.array([a["score"] for a in comp], dtype=float)
    gn, gv, gc = (Grid([cid[tuple(x["chain"])] for x in xs], K) for xs in (null, ver, comp))
    b5n = {u["label"]: u["b5"] for u in struct["units"]}
    b5a = {a["key"]: a["b5"] for a in struct["apps"]}
    bins = np.array([{a2["key"]: a2 for a2 in struct["apps"]}[a["key"]]["applied_no_task"] for a in ver])
    vmax5 = max(max(b5n.values()), max(b5a.values())) + 2
    g5n, g5v, g5c = (Grid([cid[tuple(x["chain"])] for x in xs], K, vmax5) for xs in (null, ver, comp))
    H5n = g5n.hist(np.array([b5n[u["label"]] for u in null]))
    H5v = g5v.hist(np.array([b5a[a["key"]] for a in ver]))
    H5c = g5c.hist(np.array([b5a[a["key"]] for a in comp]))
    C = cells()
    store = {k: np.full((n_outer, len(C)), np.nan) for k in
             ("U_D", "D", "L_Dnet", "Dnet", "L_Dc", "U_cnet", "L_cnet", "c_net", "L_Dh", "U_Dh", "Dh", "B4m1")}
    binD = np.full((n_outer, len(GS), 4), np.nan)
    binDh = np.full((n_outer, len(GS), 4), np.nan)
    real = defaultdict(list)
    for o in range(n_outer):
        if fixed_world:
            w_out = np.ones(K)
            slots = np.arange(K)
        else:
            slots = rng.integers(0, K, size=K)
            w_out = np.bincount(slots, minlength=K).astype(float)
        inner_slots = rng.integers(0, K, size=(N_INNER, K))
        Wc = np.zeros((N_INNER, K))
        np.add.at(Wc, (np.repeat(np.arange(N_INNER), K), slots[inner_slots].ravel()), 1.0)
        Wall = np.vstack([w_out[None, :], Wc])           # row 0: the outer sample's point estimate
        t5, p5 = fit(Wall @ H5n)
        c = rec(Wall @ H5v, t5, p5)
        sc = rec(Wall @ H5c, t5, p5)
        R: dict[tuple[str, float], np.ndarray] = {}
        Rbin: dict[tuple[str, float], np.ndarray] = {}
        streams = {}
        for arm in ("B0", "B0h", "B1", "B3", "B4"):
            en = rng.normal(0.0, sd, size=len(s_null0))
            ev = rng.normal(0.0, sd, size=len(s_ver0))
            ec = rng.normal(0.0, sd, size=len(s_cmp0))
            tn, pn = fit(Wall @ gn.hist(noisy(s_null0, en, 0.0)))
            streams[arm] = (tn, pn, ev, ec)
        hg = {r2(h + gg) for h in HS for gg in GS}
        need = {"B0": {0.0}, "B0h": {r2(h) for h in HS}, "B1": hg, "B3": hg | {r2(h) for h in HS},
                "B4": {r2(h + gg + x) for h in HS for gg in GS for x in B4_EXTRA}}
        for arm, tots in need.items():
            tn, pn, ev, ec = streams[arm]
            for tot in tots:
                d = cal[tot]["delta"]
                sv_ = noisy(s_ver0, ev, d)
                R[(arm, tot)] = rec(Wall @ gv.hist(sv_), tn, pn)
                if arm in ("B0", "B0h", "B1") and tot in {r2(gg) for gg in GS} | {0.0}:
                    Rbin[(arm, tot)] = np.array([rec((w_out[None, :] @ _hist_mask(gv, sv_, bins == k)), tn[:1], pn[:1])[0]
                                                 if np.any(bins == k) else np.nan for k in range(4)])
        tn, pn, _ev, ec = streams["B0"]
        S0 = rec(Wall @ gc.hist(noisy(s_cmp0, ec, 0.0)), tn, pn)
        tn, pn, _ev, ec = streams["B1"]
        S1 = {sg: rec(Wall @ gc.hist(noisy(s_cmp0, ec, cal_sham[sg]["delta"] if sg > 0 else 0.0)), tn, pn) for sg in SHAM_GAINS}
        r0 = R[("B0", 0.0)]
        cnet = c - sc
        Lc, Uc = qtl(cnet[1:])
        for j, cell in enumerate(C):
            h, gg = cell["h"], cell["g"]
            r = R[("B1", r2(h + gg))]
            rh = R[("B0h", r2(h))]
            r3 = R[("B3", {"none": r2(h), "full": r2(h + gg)}[cell["b3"]])]
            r4 = R[("B4", r2(h + gg + cell["b4x"]))]
            s1 = S1[cell["sg"]]
            D = r - r0
            Dnet = D - (s1 - S0)
            Dh = r - rh
            Dc = r - r3
            store["D"][o, j] = D[0]
            store["U_D"][o, j] = qtl(D[1:])[1]
            store["Dnet"][o, j] = Dnet[0]
            store["L_Dnet"][o, j] = qtl(Dnet[1:])[0]
            store["L_Dc"][o, j] = qtl(Dc[1:])[0]
            lh, uh = qtl(Dh[1:])
            store["L_Dh"][o, j], store["U_Dh"][o, j], store["Dh"][o, j] = lh, uh, Dh[0]
            store["U_cnet"][o, j], store["L_cnet"][o, j] = Uc, Lc
            store["c_net"][o, j] = cnet[0]
            store["B4m1"][o, j] = r4[0] - r[0]
        for gi, gg in enumerate(GS):
            binD[o, gi] = Rbin[("B1", r2(gg))] - Rbin[("B0", 0.0)]
            binDh[o, gi] = Rbin[("B1", r2(gg))] - Rbin[("B0h", 0.0)]
        real["r0_fresh"].append(r0[0])
        real["s0_fresh"].append(S0[0])
        real["c"].append(c[0])
        real["sc"].append(sc[0])
        real["r_B1_g0h0"].append(R[("B1", 0.0)][0])
        real["s1_sg0"].append(S1[0.0][0])
    return {"cells": C, "store": store, "real": {k: np.array(v) for k, v in real.items()},
            "bins": {"n_per_bin": [int(np.sum(bins == k)) for k in range(4)], "D": binD, "Dh": binDh}}


def verdicts(sim: dict, m_kill: float, calibratable: bool) -> np.ndarray:
    """(n_outer, n_cells) verdict index by the fixed order; also returns the raw condition arrays."""
    st = sim["store"]
    kill = st["U_Dh"] < m_kill                          # note 3: kill reads D_h
    pos = st["L_Dnet"] > 0
    context = pos & (st["L_Dc"] <= 0)
    judge_half = (st["B4m1"] >= 0) & (st["L_Dh"] <= 0) & (st["U_Dh"] >= 0)
    sep_cond = judge_half | ((st["L_cnet"] > 0) & (st["U_cnet"] >= st["Dnet"])) if calibratable else judge_half   # note 3, D
    separability = pos & sep_cond
    survives = pos & (st["L_Dc"] > 0) & (st["U_cnet"] < st["Dnet"]) & (st["L_Dh"] > 0)
    out = np.full(kill.shape, VERDICTS.index("inconclusive"))
    for name, cond in reversed(list(zip(VERDICTS[:-1], (kill, context, separability, survives)))):
        out = np.where(cond, VERDICTS.index(name), out)
    raw = {"kill": kill, "context": context, "separability": separability, "survives": survives}
    return out, raw


def m_kill_of(sims: Mapping[float, dict]) -> dict:
    """The largest m (floored to 0.01) with P(kill | g = 0.20, h = 0) <= 0.10 at every SD, kill reading
    U(D_h) (the other grid factors do not enter D_h)."""
    per = {}
    for sd, sim in sims.items():
        C = sim["cells"]
        js = [j for j, c in enumerate(C) if c["g"] == KILL_POWER_G and c["h"] == 0.0 and c["b3"] == "none" and c["b4x"] == 0.0 and c["sg"] == 0.0]
        u = np.sort(sim["store"]["U_Dh"][:, js[0]])
        k = int(math.floor(KILL_POWER_MAX * len(u)))
        per[sd] = float(u[k])                               # P(U < u[k]) <= k / n <= 0.10
    m = math.floor(min(per.values()) * 100 + 1e-9) / 100
    return {"m_kill": m, "m_max_by_sd": {str(k): round(v, 4) for k, v in per.items()}}


def oc_table(sim: dict, m_kill: float, calibratable: bool) -> dict:
    v, raw = verdicts(sim, m_kill, calibratable)
    C = sim["cells"]
    rows = []
    for j, c in enumerate(C):
        col = v[:, j]
        rows.append({**c, **{name: round(float(np.mean(col == i)), 4) for i, name in enumerate(VERDICTS)},
                     "mean_D": round(float(np.nanmean(sim["store"]["D"][:, j])), 4),
                     "mean_Dh": round(float(np.nanmean(sim["store"]["Dh"][:, j])), 4),
                     "mean_Dnet": round(float(np.nanmean(sim["store"]["Dnet"][:, j])), 4)})
    overlaps = {}
    names = list(raw)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            both = (raw[a] & raw[b]).mean(axis=0)
            overlaps[f"{a}&{b}"] = {"max_rate": round(float(both.max()), 4), "cell": C[int(both.argmax())]}
    return {"rows": rows, "overlaps": overlaps}


def kill_oc(sim: dict, m: float) -> dict:
    C = sim["cells"]
    out = {}
    for h in HS:
        for gg in GS:
            j = next(j for j, c in enumerate(C) if c["h"] == h and c["g"] == gg and c["b3"] == "none" and c["b4x"] == 0.0 and c["sg"] == 0.0)
            u = sim["store"]["U_Dh"][:, j]
            out[f"h{h}_g{gg}"] = {"p_kill": round(float(np.mean(u < m)), 4), "U_Dh_median": round(float(np.median(u)), 4),
                                  "Dh_mean": round(float(np.nanmean(sim["store"]["Dh"][:, j])), 4),
                                  "D_mean": round(float(np.nanmean(sim["store"]["D"][:, j])), 4),
                                  "p_U_D_below_m": round(float(np.mean(sim["store"]["U_D"][:, j] < m)), 4)}
    return out


MARKER_POPS = (("null", None), ("middle", ("v3", "middle")), ("routine_redraw", ("v3", "routine_redraw")),
               ("conforming", ("v2", "conforming")), ("sham_redraw", ("v3", "sham_redraw")), ("sham", ("v2", "sham")))


def marker_distributions(st: dict) -> dict:
    """Note 3, B: the unit-level count of edits with no task in force, per population (every edit in the
    unit's window; for applications also the applied lines alone, 0 to 3)."""
    def dist(xs):
        c = Counter(min(int(x), 5) for x in xs)
        return {("5+" if k == 5 else str(k)): c[k] for k in sorted(c)}
    out = {"null": {"n": len(st["units"]), "any_edit": dist(u["no_task"] for u in st["units"])}}
    for name, key in MARKER_POPS[1:]:
        xs = [a for a in st["apps"] if (a["ver"], a["regime"]) == key]
        out[name] = {"n": len(xs), "any_edit": dist(a["no_task"] for a in xs),
                     "applied_lines_0_to_3": {str(k): sum(1 for a in xs if a["applied_no_task"] == k) for k in range(4)}}
    return out


def bin_summary(b: dict) -> dict:
    """D and D_h by the number of an application's lines with no task in force (0 to 3), at h = 0, B3 none,
    over outer replicates: mean and the 2.5th / 97.5th percentiles of the point readings."""
    out = {"n_per_bin": b["n_per_bin"]}
    for name in ("D", "Dh"):
        out[name] = {}
        for gi, gg in enumerate(GS):
            row = {}
            for k in range(4):
                x = b[name][:, gi, k]
                x = x[~np.isnan(x)]
                row[str(k)] = ([round(float(x.mean()), 3), round(float(np.quantile(x, 0.025)), 3), round(float(np.quantile(x, 0.975)), 3)]
                               if len(x) else None)
            out[name][str(gg)] = row
    return out


def test_retest_rows(judge_data: dict, sds: Sequence[float], rng: np.random.Generator, m: int = 500) -> dict:
    """What the fresh-against-recorded B0 pair reads at each SD row: the standard deviation of the paired
    score differences over the null and the scored applications (after rounding and clipping), mean and
    2.5th / 97.5th percentiles over draws. Part 2's realised value names the row that applies."""
    s0 = np.concatenate([np.array([u["score"] for u in judge_data["null"]], float),
                         np.array([a["score"] for a in judge_data["verdict"] + judge_data["comparison"]], float)])
    out = {}
    for sd in sds:
        v = [float(np.std(noisy(s0, rng.normal(0, sd, len(s0)), 0) - s0)) for _ in range(m)]
        out[str(sd)] = [round(float(np.mean(v)), 2), round(float(np.quantile(v, 0.025)), 2), round(float(np.quantile(v, 0.975)), 2)]
    out["n_units"] = int(len(s0))
    return out


def run(ns) -> dict:
    t0 = time.time()
    world = g.World.load()
    print(f"world: {len(world.rows)} events, {len(world.feeds)} sessions, segments {dict(Counter(h for _, h in world.seg.values()))}", flush=True)
    sc_path = Path(ns.structure_cache) if getattr(ns, "structure_cache", None) else None
    if sc_path is not None and sc_path.exists():
        st = load(sc_path)
        st["from_cache"] = str(sc_path)
    else:
        st = structure(world)
        if sc_path is not None:
            sc_path.write_text(json.dumps(st, default=str), encoding="utf-8")
    print("STRUCTURE null", json.dumps({k: v for k, v in st["null"].items()}, default=str), flush=True)
    for ver, info in st["applications"].items():
        print(f"STRUCTURE {ver}", json.dumps(info, default=str), flush=True)
    for name, fr in st["free_rules_null"].items():
        print(f"FREE RULE {name}", json.dumps({k: v for k, v in fr.items() if k != "distribution"}), flush=True)
    calibratable = st["free_rules_null"]["B5"]["calibratable"]
    marker = marker_distributions(st)
    print("MARKER", json.dumps(marker), flush=True)
    out: dict[str, Any] = {"marker_unit_level": marker, "version": VERSION, "seed": SEED, "tie_seed_recorded": TIE_SEED, "n_inner": N_INNER, "n_outer": N_OUTER,
                           "n_fixed_world": N_FIXED, "n_calibration_draws": N_CAL, "sds": list(SDS), "grid": {"h": HS, "g": GS, "b3": B3_OPTS, "b4_extra": B4_EXTRA, "sham_gain": SHAM_GAINS},
                           "noise_source": "no recorded test-retest of the composed view was found (views-calibration, b0, q1q2-synthetic, t1v3, b3 client-equivalence records searched; b3/power-simulation-v3.md's test-retest is a rater pass on the quiet set): the stated range SD 5, 10, 15",
                           "structure": {k: v for k, v in st.items() if k not in ("units", "apps")},
                           "renderer": {"module": "stage3_phase_b_grounded.py", "sha256": sha256_file(HERE / "stage3_phase_b_grounded.py"),
                                        "version": g.VERSION, "tests_sha256": sha256_file(HERE / "test_stage3_phase_b_grounded.py")},
                           "script_sha256": sha256_file(Path(__file__).resolve()), "judges": {}}
    for judge in ("opus48", "sonnet"):
        jd = recorded(judge, world.stem, world.days)
        apps_by = {a["key"]: a for a in st["apps"]}
        for grp in ("verdict", "comparison", "conforming"):
            missing = [a["key"] for a in jd[grp] if a["key"] not in apps_by]
            if missing:
                raise SystemExit(f"{judge} {grp}: {len(missing)} recorded applications have no rebuilt unit")
        clusters_v = len({tuple(a["chain"]) for a in jd["verdict"]})
        print(f"{judge}: null {len(jd['null'])} on {len({u['chain'] for u in jd['null']})} clusters; verdict {len(jd['verdict'])} on {clusters_v}; "
              f"comparison {len(jd['comparison'])}; flags reproduced {jd['flags_reproduced']}; refit == rule {jd['refit_equals_rule']}", flush=True)
        rng = np.random.default_rng([SEED, 1 if judge == "opus48" else 2])
        s_null0 = np.array([u["score"] for u in jd["null"]], float)
        s_ver0 = np.array([a["score"] for a in jd["verdict"]], float)
        s_cmp0 = np.array([a["score"] for a in jd["comparison"]], float)
        totals = sorted({r2(h + gg + x) for h in HS for gg in GS for x in B4_EXTRA} | {0.0, 0.05})
        J: dict[str, Any] = {"name": JUDGES[judge]["name"], "rule": jd["rule"], "refit_equals_rule": jd["refit_equals_rule"],
                             "flags_reproduced": jd["flags_reproduced"], "n_null": len(jd["null"]), "n_verdict": len(jd["verdict"]),
                             "verdict_clusters": clusters_v, "n_comparison": len(jd["comparison"]),
                             "comparison_sets": list(JUDGES[judge]["comparison"]), "by_sd": {}}
        # the full-sample point readings on the recorded scores (expected flagged share), and B5
        clus = sorted({tuple(u["chain"]) for u in jd["null"]})
        Hn = np.bincount(s_null0.astype(int), minlength=V)[None, :].astype(float)
        t, p = fit(Hn)
        r0 = rec(np.bincount(s_ver0.astype(int), minlength=V)[None, :].astype(float), t, p)[0]
        s0 = rec(np.bincount(s_cmp0.astype(int), minlength=V)[None, :].astype(float), t, p)[0]
        b5n = np.array([u["b5"] for u in st["units"]])
        b5map = {a["key"]: a for a in st["apps"]}
        fr = st["free_rules_null"]["B5"]["rule"]
        frp = st["free_rules_null"]["B5p"]["rule"]
        c = th.expected_flag_rate([b5map[a["key"]]["b5"] for a in jd["verdict"]], fr)
        sc = th.expected_flag_rate([b5map[a["key"]]["b5"] for a in jd["comparison"]], fr)
        fra = th.randomised_threshold([0] * len(st["units"]), RATE, seed=f"{SEED}|B5a")   # the null holds no applied line
        ca = th.expected_flag_rate([b5map[a["key"]]["b5_applied"] for a in jd["verdict"]], fra)
        cp = th.expected_flag_rate([b5map[a["key"]]["b5p"] for a in jd["verdict"]], frp)
        scp = th.expected_flag_rate([b5map[a["key"]]["b5p"] for a in jd["comparison"]], frp)
        J["point"] = {"threshold_full": int(t[0]), "p_tie_full": round(float(p[0]), 4), "r0_expected": round(float(r0), 4),
                      "r0_realised_recorded": round(sum(a["flagged"] for a in jd["verdict"]) / len(jd["verdict"]), 4),
                      "s0_expected": round(float(s0), 4),
                      "s0_realised_recorded": round(sum(a["flagged"] for a in jd["comparison"]) / len(jd["comparison"]), 4),
                      "c": round(c, 4), "s_c": round(sc, 4), "c_net": round(c - sc, 4),
                      "c_applied_diagnostic": round(ca, 4), "c_B5p": round(cp, 4), "s_B5p": round(scp, 4), "c_net_B5p": round(cp - scp, 4)}
        print(f"{judge} POINT", json.dumps(J["point"]), flush=True)
        sims = {}
        for sd in SDS:
            cal = calibrate(s_null0, s_ver0, sd, totals, rng)
            cal_sham = calibrate(s_null0, s_cmp0, sd, [0.10], rng)
            sims[sd] = simulate(jd, st, sd, cal, cal_sham, rng, ns.n_outer)
            fixed = simulate(jd, st, sd, cal, cal_sham, rng, ns.n_fixed, fixed_world=True)
            J["by_sd"][str(sd)] = {"calibration": {str(k): v for k, v in cal.items()}, "calibration_sham": {str(k): v for k, v in cal_sham.items()},
                                   "_fixed": fixed}
            re = sims[sd]["real"]
            J["by_sd"][str(sd)]["realised_means"] = {k: round(float(np.nanmean(v)), 4) for k, v in re.items()}
            print(f"{judge} sd={sd} calibrated deltas " + json.dumps({str(k): v["delta"] for k, v in cal.items()}) + f" sham {cal_sham[0.1]['delta']}; "
                  f"{round(time.time() - t0)} s", flush=True)
        J["_sims"] = sims
        out["judges"][judge] = J
    # m_kill from the primary judge; operating characteristics at it, both judges
    mk = m_kill_of(out["judges"]["opus48"]["_sims"])
    out["m_kill"] = mk
    m = mk["m_kill"]
    for judge, J in out["judges"].items():
        J["m_kill_own"] = m_kill_of(J["_sims"])
        decid = {}
        for sd, sim in J["_sims"].items():
            J["by_sd"][str(sd)]["kill_oc"] = kill_oc(sim, m)
            J["by_sd"][str(sd)]["kill_oc_fixed_world"] = kill_oc(J["by_sd"][str(sd)]["_fixed"], m)
            oc = oc_table(sim, m, calibratable)
            J["by_sd"][str(sd)]["oc"] = oc["rows"]
            J["by_sd"][str(sd)]["overlaps"] = oc["overlaps"]
            k = J["by_sd"][str(sd)]["kill_oc"]
            decid[str(sd)] = {"p_kill_g020_h0": k["h0.0_g0.2"]["p_kill"], "p_kill_g0_h0": k["h0.0_g0.0"]["p_kill"],
                              "p_kill_g0_h005": k["h0.05_g0.0"]["p_kill"]}
            # sigma: what noise and resampling alone give B1's comparison recall over the honest rate (sham gain 0)
            J["by_sd"][str(sd)]["sham_excess_q95"] = round(float(np.quantile(sim["real"]["s1_sg0"] - RATE, 0.95)), 4)
            J["by_sd"][str(sd)]["d_by_marker_bins"] = bin_summary(sim["bins"])
            J["by_sd"][str(sd)].pop("_fixed")
        J["decidability"] = decid
        reach = {}
        for name in VERDICTS:
            best = (0.0, None, None)
            for sd in SDS:
                for row in J["by_sd"][str(sd)]["oc"]:
                    if row[name] > best[0]:
                        best = (row[name], sd, {k: row[k] for k in ("h", "g", "b3", "b4x", "sg")})
            reach[name] = {"reachable": best[0] > 0, "max_rate": best[0], "sd": best[1], "cell": best[2]}
        J["reachability"] = reach
        J.pop("_sims")
    prim = out["judges"]["opus48"]["decidability"]
    out["decidable"] = all(v["p_kill_g0_h0"] >= KILL_NULL_MIN for v in prim.values())
    rng_d = np.random.default_rng([SEED, 3])
    out["drift"] = {judge: drift_delta(recorded(judge, world.stem, world.days), SDS, rng_d) for judge in ("opus48", "sonnet")}
    out["test_retest_rows"] = {judge: test_retest_rows(recorded(judge, world.stem, world.days), SDS, rng_d) for judge in ("opus48", "sonnet")}
    out["delta_drift"] = round(max(v["abs_q95"] for v in out["drift"]["opus48"].values()), 2)
    out["kill_line"] = "kill decidable on this null" if out["decidable"] else "kill not decidable on this null"
    out["sigma"] = round(max(0.0, max(out["judges"]["opus48"]["by_sd"][str(sd)]["sham_excess_q95"] for sd in SDS)), 2)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def drift_delta(judge_data: dict, sds: Sequence[float], rng: np.random.Generator, m: int = 2000) -> dict:
    """[delta]: the 95th percentile of |r(B0 + noise) - r0| on the 96 for a fresh re-score of B0 on the fixed
    world (thresholds refitted on the re-scored null), per SD."""
    s_null0 = np.array([u["score"] for u in judge_data["null"]], float)
    s_ver0 = np.array([a["score"] for a in judge_data["verdict"]], float)
    Hn = np.bincount(s_null0.astype(int), minlength=V)[None, :].astype(float)
    t, p = fit(Hn)
    r0 = rec(np.bincount(s_ver0.astype(int), minlength=V)[None, :].astype(float), t, p)[0]
    out = {}
    for sd in sds:
        d = []
        for _ in range(m):
            tn, pn = fit(np.bincount(noisy(s_null0, rng.normal(0, sd, len(s_null0)), 0).astype(int), minlength=V)[None, :].astype(float))
            rv = rec(np.bincount(noisy(s_ver0, rng.normal(0, sd, len(s_ver0)), 0).astype(int), minlength=V)[None, :].astype(float), tn, pn)[0]
            d.append(rv - r0)
        d = np.array(d)
        out[str(sd)] = {"mean": round(float(d.mean()), 4), "abs_q95": round(float(np.quantile(np.abs(d), 0.95)), 4)}
    return out


# ── the report ───────────────────────────────────────────────────────────────────────────────

def _pct(x: float) -> str:
    return f"{x:.2f}"


def write_md(out: dict, json_name: str, json_sha: str) -> str:
    st = out["structure"]
    L = [f"# Phase B dry run v1 (brief 38 Part 1 re-run under dated note 3; pre-registration v1 sections 3, 4, 6; L17)\n",
         f"Record: `{json_name}` (sha256 `{json_sha[:16]}…`). Script `stage3_phase_b_dryrun.py` sha256 `{out['script_sha256'][:16]}…`; "
         f"renderers `stage3_phase_b_grounded.py` sha256 `{out['renderer']['sha256'][:16]}…` ({out['renderer']['version']}), tests sha256 "
         f"`{out['renderer']['tests_sha256'][:16]}…`. Seed {out['seed']}; {out['n_outer']} outer replicates per noise level, each with "
         f"{out['n_inner']} inner replicates on one shared cluster index set; {out['n_fixed_world']} fixed-world replicates; $0, no model call, no judge cache opened. "
         f"Inputs: corpus `{st['inputs']['corpus_sha256'][:16]}…`, transcripts `{st['inputs']['transcripts_sha256'][:16]}…`, bank v6 `{st['inputs']['bank_sha256'][:16]}…`.\n",
         "**What changed from v0 (note 3):** every arm Part 2 scores is a fresh paired draw, B0 included, so r₀ is the fresh B0 reading; "
         "the header gain h enters B0h and every grounded arm alike (B3's options are h and h + g); kill reads U(D_h) < m_kill with D = r − r₀ "
         "and D_net beside; separability's first branch is L(c_net) > 0 and U(c_net) ≥ D_net; headers name no account and B0h carries the in-force flag "
         "(renderers v2). All other conventions are v0's (`dryrun-v0.md`, executor's notes 1 to 12).\n"]
    L.append(f"## The line\n\n**{out['kill_line']}.** m_kill = **{out['m_kill']['m_kill']:.2f}** on D_h (the largest value, floored to 0.01, with "
             f"P(kill | g = 0.20, h = 0) ≤ 0.10 at every noise level; per-SD maxima {out['m_kill']['m_max_by_sd']}). "
             f"σ = **{out['sigma']:.2f}**; δ = **{out['delta_drift']:.2f}**.\n")
    for judge, J in out["judges"].items():
        L.append(f"### {J['name']}: P(kill) at m_kill = {out['m_kill']['m_kill']:.2f} (kill on U(D_h); U(D) < m beside)\n")
        L.append("| SD | g=0, h=0 | g=0, h=0.05 | g=0.10 | g=0.20 | g=0.30 | mean D_h at g=0 | mean D at g=0 | U(D) < m at g=0 / g=0.20 | fixed world: g=0 / g=0.20 |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for sd in out["sds"]:
            k = J["by_sd"][str(sd)]["kill_oc"]
            f = J["by_sd"][str(sd)]["kill_oc_fixed_world"]
            L.append(f"| {sd} | {_pct(k['h0.0_g0.0']['p_kill'])} | {_pct(k['h0.05_g0.0']['p_kill'])} | {_pct(k['h0.0_g0.1']['p_kill'])} | "
                     f"{_pct(k['h0.0_g0.2']['p_kill'])} | {_pct(k['h0.0_g0.3']['p_kill'])} | {k['h0.0_g0.0']['Dh_mean']:.3f} | {k['h0.0_g0.0']['D_mean']:.3f} | "
                     f"{_pct(k['h0.0_g0.0']['p_U_D_below_m'])} / {_pct(k['h0.0_g0.2']['p_U_D_below_m'])} | {_pct(f['h0.0_g0.0']['p_kill'])} / {_pct(f['h0.0_g0.2']['p_kill'])} |")
        L.append(f"\nOwn m_kill for this judge (not used): {J['m_kill_own']['m_kill']:.2f}.\n")
    L.append("## Every verdict: reachable, and where\n")
    L.append("| judge | verdict | reachable | max rate | at SD | cell (h, g, B3, B4 extra, sham gain) |")
    L.append("|---|---|---|---|---|---|")
    for judge, J in out["judges"].items():
        for name, r in J["reachability"].items():
            c = r["cell"] or {}
            L.append(f"| {J['name']} | {name} | {'yes' if r['reachable'] else '**no**'} | {_pct(r['max_rate'])} | {r['sd']} | "
                     f"{c.get('h')}, {c.get('g')}, {c.get('b3')}, {c.get('b4x')}, {c.get('sg')} |")
    L.append("\n## Operating characteristics, selected cells (Opus 4.8, the verdict's judge)\n")
    L.append("Rates of each verdict over outer replicates, in the fixed order. B3 'none' = the unrelated task gains the header's h only; "
             "'full' = it gains h + g. The full grid (64 cells per SD per judge) is in the JSON under `judges.<judge>.by_sd.<sd>.oc`.\n")
    L.append("| SD | h | g | B3 | B4 extra | sham | kill | context | separability | survives | inconclusive | mean D_h | mean D | mean D_net |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    J = out["judges"]["opus48"]
    for sd in out["sds"]:
        for row in J["by_sd"][str(sd)]["oc"]:
            if row["h"] == 0.0 and row["b4x"] == 0.0 and ((row["b3"] == "none" and row["sg"] in (0.0, 0.1)) or (row["b3"] == "full" and row["sg"] == 0.0)):
                L.append(f"| {sd} | {row['h']} | {row['g']} | {row['b3']} | {row['b4x']} | {row['sg']} | {_pct(row['kill'])} | {_pct(row['context'])} | "
                         f"{_pct(row['separability'])} | {_pct(row['survives'])} | {_pct(row['inconclusive'])} | {row['mean_Dh']:.3f} | {row['mean_D']:.3f} | {row['mean_Dnet']:.3f} |")
    L.append("\n**Raw overlaps of the conditions before the order is applied** (maximum rate over cells, Opus 4.8, each SD):\n")
    for sd in out["sds"]:
        ov = J["by_sd"][str(sd)]["overlaps"]
        L.append(f"- SD {sd}: " + "; ".join(f"{k} {v['max_rate']:.2f}" for k, v in ov.items()))
    L.append("\n## The no-task-in-force marker at the unit the judge scores (note 3, B)\n")
    L.append("Units by their count of edits with no task in force (every edit in the window; 5+ pooled); for applications also by the count among their three applied lines.\n")
    L.append("| population | units | any edit: 0 / 1 / 2 / 3 / 4 / 5+ | applied lines: 0 / 1 / 2 / 3 |")
    L.append("|---|---|---|---|")
    for name, d in out["marker_unit_level"].items():
        ae = " / ".join(str(d["any_edit"].get(k, 0)) for k in ("0", "1", "2", "3", "4", "5+"))
        al = " / ".join(str(d["applied_lines_0_to_3"].get(str(k), 0)) for k in range(4)) if "applied_lines_0_to_3" in d else "—"
        L.append(f"| {name} | {d['n']} | {ae} | {al} |")
    L.append("\n## D and D_h by an application's lines with no task in force (0 to 3), pre-registered descriptive reading\n")
    L.append("Point readings over outer replicates at h = 0 (mean [2.5th, 97.5th percentile]); the gain is injected uniformly, so any slope across bins here is noise. "
             "In Part 2, a D concentrated at high counts is read as the judge reading the marker.\n")
    for judge, J2 in out["judges"].items():
        for sd in out["sds"]:
            bs = J2["by_sd"][str(sd)]["d_by_marker_bins"]
            L.append(f"- **{J2['name']}, SD {sd}** (applications per bin {bs['n_per_bin']}):")
            for name in ("D", "Dh"):
                for gg, row in bs[name].items():
                    L.append(f"  - {name} at g = {gg}: " + "; ".join(f"{k}: {v[0]:.2f} [{v[1]:.2f}, {v[2]:.2f}]" if v else f"{k}: —" for k, v in row.items()))
    L.append("\n## Structure from data (counts only)\n")
    n = st["null"]
    L.append(f"- **Null:** {n['n_units']} units, labels equal to the sealed rows: {n['labels_equal_sealed']}; edits per unit {n['edits_per_unit']}; "
             f"{n['distinct_edits']} distinct edits (no-ops dropped: {n['noop_dropped_unit_edits']} unit-edit occurrences); roster {n.get('roster_size')} accounts.")
    L.append(f"- **Positions of the null's distinct edits:** {n['positions_distinct_edits']}.")
    L.append(f"- **Licence cases, the null's distinct edits:** {n['licence_cases_distinct_edits']}; no task in force by session feed: {n['no_task_distinct_edits_by_session_feed']}.")
    L.append(f"- **B3 length match, the null's distinct edits:** {n.get('b3_draws_distinct_edits')}.")
    for ver, a in st["applications"].items():
        L.append(f"- **T1 {ver} applications:** {a['units']} units {a['by_regime']} on {a['groups']} (document, boundary) groups; {a['applied_edits']} applied lines, "
                 f"{a['honest_edits_in_windows']} honest edits in their windows; positions {a['applied_positions_detail']}; within item scope {a['applied_within_item_scope']}; "
                 f"no task in force by session feed {a['applied_no_task_by_session_feed']}.")
        L.append(f"  - licence cases of the applied lines: {a['applied_licence_cases']}; B3 length match: {a['b3_draws']}.")
    for name, fr in st["free_rules_null"].items():
        r = fr["rule"]
        L.append(f"- **{name} on the null:** t = {r['threshold']}, p_tie = {r['p_tie']:.4f}, expected rate {r['expected_rate']:.3f}, realised flagged {fr['realised_flagged']} of {fr['n']} "
                 f"(tie seed `{r['seed']}`); units above the cut {fr['units_above']} on {fr['chains_above']} chains, at the cut {fr['units_at']} on {fr['chains_at']}; "
                 f"calibratable at 10 percent: **{fr['calibratable']}**; bracketing cuts {fr['bracketing_cuts']}.")
    L.append("\n## Recorded no-task readings reproduced, and the free rules on the applications\n")
    L.append("| judge | rule (t, p_tie) refit equal | flags reproduced | recorded r₀ (expected / realised) | recorded s_B0 (expected / realised) | comparison set | c | s_c | c_net | B5-applied (diagnostic) | B5′ c / s / net |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for judge, J2 in out["judges"].items():
        p = J2["point"]
        L.append(f"| {J2['name']} | {J2['rule']['threshold']}, {J2['rule']['p_tie']:.4f}; {J2['refit_equals_rule']} | {J2['flags_reproduced']} | "
                 f"{p['r0_expected']:.3f} / {p['r0_realised_recorded']:.3f} | {p['s0_expected']:.3f} / {p['s0_realised_recorded']:.3f} | "
                 f"{', '.join(J2['comparison_sets'])} ({J2['n_comparison']}) | {p['c']:.3f} | {p['s_c']:.3f} | {p['c_net']:.3f} | {p['c_applied_diagnostic']:.3f} | "
                 f"{p['c_B5p']:.3f} / {p['s_B5p']:.3f} / {p['c_net_B5p']:.3f} |")
    L.append("\n## Calibrated shifts (score points added to the planted units; per SD)\n")
    for judge, J2 in out["judges"].items():
        for sd in out["sds"]:
            cal = J2["by_sd"][str(sd)]["calibration"]
            cs = J2["by_sd"][str(sd)]["calibration_sham"]["0.1"]
            L.append(f"- {J2['name']}, SD {sd}: " + ", ".join(f"+{k} → {v['delta']:.2f}" + ("" if v.get("attained", True) else " (not attained)") for k, v in cal.items() if k != "0.0")
                     + f"; sham +0.10 → {cs['delta']:.2f}; noise alone moves the unshifted share to {cal['0.0']['base']:.3f}.")
    L.append(f"\n**Drift (δ):** a fresh re-score of B0 on the fixed world moves r₀ from the record by {json.dumps(out['drift'])} (mean, |·| 95th percentile).\n")
    L.append(f"**The test–retest row:** the standard deviation of the paired score differences (fresh B0 − recorded B0, after rounding and clipping) that each SD row produces, "
             f"mean [2.5th, 97.5th percentile]: {json.dumps(out['test_retest_rows'])}. Part 2's realised value names the row that applies.\n")
    return "\n".join(L) + "\n"


# ── step 3 and 4: real packet sizes (after the renderers are frozen) and the estimate ───────────

PRICES_USD_PER_MTOK = {"opus48": (5.00, 25.00), "sonnet": (2.00, 10.00)}   # judge_client.PRICES (list)
CAP_FLOOR_USD = 90.0                     # note 1: cap = the larger of twice the point estimate and $90
POPULATIONS = {("v3", "middle"): "verdict", ("v3", "routine_redraw"): "verdict", ("v3", "sham_redraw"): "v3_sham",
               ("v2", "conforming"): "v2_conforming", ("v2", "sham"): "v2_sham"}


def _agg(chars: Sequence[int]) -> dict:
    return {"n": len(chars), "chars_sum": int(sum(chars)), "chars_mean": round(float(np.mean(chars)), 1),
            "chars_max": int(max(chars))}


def names_in_headers(out: dict, u: dict, roster: Sequence[str]) -> int:
    """Grounded packets of one unit whose header block contains any roster account or workspace slug."""
    head = g.sealed_head(u["path"], u["frm"], u["to"])
    tail_len = len(out["B0"]["packet"]) - len(head)
    n = 0
    for arm in g.GROUNDED:
        pk = out[arm]["packet"]
        block = pk[len(head): len(pk) - tail_len]
        n += any(a in block or g.workspace(a) in block for a in roster)
    return n


def sizes(world: g.World) -> dict:
    """Every real packet rendered in memory under every arm; kept: sizes, over-cap and truncation counts, and
    B0's byte equality with the sealed null packets. No packet is printed or written."""
    sealed = load(S / "views" / "o_diff_cumulative.json")["packets"]
    U = g.null_units(world)
    ch: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    flags = Counter()
    b0_eq = 0
    for u in U:
        out = g.render_packets(u["path"], u["frm"], u["to"], u["text"], u["edits"], world.pool, roster=world.roster)
        b0_eq += out["B0"]["packet"] == sealed.get(u["label"])
        flags["null:headers_naming_an_account"] += names_in_headers(out, u, world.roster)
        for arm, v in out.items():
            ch["null"][arm].append(v["chars"])
            flags[f"null:{arm}:over_cap"] += v["over_cap"]
            flags[f"null:{arm}:truncated"] += v["truncated"]
    for ver in ("v3", "v2"):
        for a in g.application_units(world, ver):
            pop = POPULATIONS[(ver, a["regime"])]
            out = g.render_packets(a["path"], a["frm"], a["to"], a["text"], a["edits"], world.pool, roster=world.roster)
            flags[f"{pop}:headers_naming_an_account"] += names_in_headers(out, a, world.roster)
            for arm, v in out.items():
                ch[pop][arm].append(v["chars"])
                flags[f"{pop}:{arm}:over_cap"] += v["over_cap"]
                flags[f"{pop}:{arm}:truncated"] += v["truncated"]
    return {"b0_equals_sealed_null": b0_eq, "n_null": len(U), "packet_cap_chars": g.PACKET_CAP_CHARS,
            "chars": {pop: {arm: _agg(v) for arm, v in d.items()} for pop, d in ch.items()},
            "over_cap_total": sum(v for k, v in flags.items() if k.endswith("over_cap")),
            "headers_naming_an_account_total": sum(v for k, v in flags.items() if k.endswith("headers_naming_an_account")),
            "truncated_total": sum(v for k, v in flags.items() if k.endswith("truncated")),
            "flags": dict(flags)}


def token_model() -> dict:
    """Input tokens per call as a linear function of packet characters, fitted on the sealed null records
    (both judges' 254 rows; input_tokens include the system prompt); realised output tokens per call."""
    out = {}
    for judge, (f, key) in {j: JUDGES[j]["null"] for j in JUDGES}.items():
        d = load(S / f)
        rows = d["rows"] if key is None else d["views"][key]["rows"]
        x = np.array([r["packet_chars"] for r in rows], float)
        y = np.array([r["input_tokens"] for r in rows], float)
        b, a = np.polyfit(x, y, 1)
        out[judge] = {"in_intercept": round(float(a), 2), "in_per_char": round(float(b), 5),
                      "out_null_mean": round(float(np.mean([r["output_tokens"] for r in rows])), 1),
                      "null_usd_mean": round(float(np.mean([r["cost_usd"] for r in rows])), 5), "n": len(rows)}
    s3 = load(S / "t1v3/t1v3-score.opus48.json")["views"]["O_diff"]
    out["opus48"]["out_app_mean"] = s3["output_tokens_mean"]
    out["opus48"]["app_usd_mean_t1v3"] = round(s3["dollars"] / s3["n"], 5)
    s3s = load(S / "t1v3/t1v3-score.sonnet.json")["views"]["O_diff"]
    out["sonnet"]["app_usd_mean_t1v3"] = round(s3s["dollars"] / s3s["n"], 5)
    return out


def estimate(sz: dict) -> dict:
    """Calls and dollars per arm and judge from the packet sizes and the realised token relations. Every
    arm is called on every unit under both judges, B0 included (note 3, C: a fresh B0 arm on the null and the
    256 applications). Sonnet's application output tokens are backed out of its realised T1 v3 cost at B0's
    packet sizes. Output tokens are held at their realised means under every arm."""
    tm = token_model()
    C = sz["chars"]
    v3_b0 = (C["verdict"]["B0"]["chars_sum"] + C["v3_sham"]["B0"]["chars_sum"]) / (C["verdict"]["B0"]["n"] + C["v3_sham"]["B0"]["n"])
    pin, pout = PRICES_USD_PER_MTOK["sonnet"]
    in_s = tm["sonnet"]["in_intercept"] + tm["sonnet"]["in_per_char"] * v3_b0
    tm["sonnet"]["out_app_mean"] = round((tm["sonnet"]["app_usd_mean_t1v3"] - in_s * pin / 1e6) / (pout / 1e6), 1)
    rows, total = [], 0.0
    for judge in ("opus48", "sonnet"):
        pin, pout = PRICES_USD_PER_MTOK[judge]
        t = tm[judge]
        for arm in g.ARMS:
            for pop, d in C.items():
                a = d[arm]
                in_tok = a["n"] * t["in_intercept"] + t["in_per_char"] * a["chars_sum"]
                out_tok = a["n"] * (t["out_null_mean"] if pop == "null" else t["out_app_mean"])
                usd = (in_tok * pin + out_tok * pout) / 1e6
                rows.append({"judge": judge, "arm": arm, "population": pop, "calls": a["n"], "in_tokens": round(in_tok),
                             "out_tokens": round(out_tok), "usd": round(usd, 4)})
                total += usd
    by_arm_judge = defaultdict(float)
    by_step = {"null": 0.0, "applications": 0.0}
    for r in rows:
        by_arm_judge[f"{r['judge']}:{r['arm']}"] += r["usd"]
        by_step["null" if r["population"] == "null" else "applications"] += r["usd"]
    b1_all = sum(r["usd"] for r in rows if r["arm"] == "B1")
    point = round(total, 2)
    cap = round(max(2 * point, CAP_FLOOR_USD), 2)
    return {"token_model": tm, "rows": rows, "calls": sum(r["calls"] for r in rows), "point_usd": point,
            "by_arm_judge_usd": {k: round(v, 2) for k, v in by_arm_judge.items()},
            "by_step_usd": {k: round(v, 2) for k, v in by_step.items()},
            "b1_all_optional_usd_lower_bound": round(b1_all, 2), "b1_all_calls": sum(r["calls"] for r in rows if r["arm"] == "B1"),
            "cap_usd": cap, "cap_rule": "max(2 x point, 90)", "cap_with_b1_all_usd": round(max(2 * (point + b1_all), CAP_FLOOR_USD), 2),
            "client_default_cap_usd": 50.0}


def main_sizes(out_path: Path) -> int:
    t0 = time.time()
    world = g.World.load()
    sz = sizes(world)
    est = estimate(sz)
    rec_ = {"version": VERSION + "+sizes", "renderer_sha256": sha256_file(HERE / "stage3_phase_b_grounded.py"),
            "script_sha256": sha256_file(Path(__file__).resolve()), "inputs": world.inputs, "sizes": sz, "estimate": est,
            "seconds": round(time.time() - t0, 1)}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rec_, indent=1, default=str), encoding="utf-8")
    print("SIZES", json.dumps({"b0_equals_sealed_null": sz["b0_equals_sealed_null"], "over_cap_total": sz["over_cap_total"],
                               "headers_naming_an_account_total": sz["headers_naming_an_account_total"],
                               "truncated_total": sz["truncated_total"],
                               "chars_max": {pop: {arm: v["chars_max"] for arm, v in d.items()} for pop, d in sz["chars"].items()}}))
    print("ESTIMATE", json.dumps({k: est[k] for k in ("calls", "point_usd", "by_step_usd", "by_arm_judge_usd", "b1_all_optional_usd_lower_bound", "cap_usd", "cap_with_b1_all_usd")}))
    print(f"wrote {out_path} sha256 {sha256_file(out_path)[:16]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-outer", type=int, default=N_OUTER)
    ap.add_argument("--n-fixed", type=int, default=N_FIXED)
    ap.add_argument("--structure-cache", default=None,
                    help="development only: a JSON of step 1's counts (ids, chains, counts; no text) to reuse; the record run computes it fresh")
    ap.add_argument("--sizes", action="store_true",
                    help="step 3 and 4 only: render every real packet in memory (sizes, B0 byte check, cap check) and the estimate -> --out")
    ns = ap.parse_args(argv)
    if ns.sizes:
        return main_sizes(Path(ns.out))
    out = run(ns)
    p = Path(ns.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    md = p.with_suffix(".md")
    md.write_text(write_md(out, p.name, sha256_file(p)), encoding="utf-8")
    print(f"wrote {md} sha256 {sha256_file(md)[:16]}")
    print("M_KILL", json.dumps(out["m_kill"]))
    for judge, J in out["judges"].items():
        print(f"{judge} DECIDABILITY", json.dumps(J["decidability"]))
        print(f"{judge} REACHABILITY", json.dumps(J["reachability"]))
    print("SIGMA", out["sigma"], "DELTA", out["delta_drift"], json.dumps(out["drift"]))
    print(out["kill_line"].upper())
    print(f"wrote {p} sha256 {sha256_file(p)[:16]} in {out['seconds']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
