#!/usr/bin/env python3
"""Brief 20 Part 3 (B3; $0): the switch rule of brief 15 A6.14.3, the stratum cascade of A6.17.9, round 2's size, and
Kimi K3's routing (A6.17.10 (b)), on Part 2's model unchanged.

Built on `stage3_b3_power_v3.py` (Part 2's script, imported and not changed): its generative model, its calibration of
each instrument (recomputed here from the same inputs file and seed, and checked against Part 2's pinned m_s), its
latent margins (read from `power-simulation-v3b.json`), its form (a) and form (b) fits, A6.13.4's instrument label and
carrier-first combination. What is new:

* Step 0 (A6.17.11): the planted set is net of brief 26's drops (`inserter-dry-run-v0.json`, `drop_list.ids`, the pair
  rule; the literal-count list beside as a sensitivity), and the comparison arm is net of its drops.
* Shared worlds: one simulated world plants the net quiet set and the comparison arm under one truth; the carrier
  (form (a) on Opus 4.8's isolated dossier) and the second named instrument (form (a) on Opus 4.8's `P_author`) read
  the same plants (true composition, line deviations and the comparison arm's triple draws shared, as Part 2's joint
  run); every population is fitted on the same world: the full set (A6.3 with the document factor, as Part 2), the
  comprehension-quiet stratum, the resolved-anchor subset and the strict two-family stratum (form (a) without the
  document factor, document-stratified bootstrap with documents of fewer than four members pooled, A6.16.2 and
  A6.17.3; the unpooled stratification beside for the carrier).
* Membership truths (A6.14.3, A6.17.1): under truth on the margin (and 1.5 times it) the stratum's members carry the
  latent composition effect; non-members carry none ("zero", the upper bound on dilution), a quarter of it ("small",
  the small-excess sensitivity; the quarter is this script's choice), all of it with probability q per item ("latent",
  q such that the quiet set's latent share is 0.69, and 0.46 beside), or all of it ("none", Part 2's undiluted case).
* Readings per population: A6.13.1's gate per instrument (worse ICC), form (a)'s fit rate and read rate, A6.13.4's
  combined verdict; the switch; the branches; the cascade with its joint operating characteristics; the carrying
  population's layout; round 2's n per arm; the Kimi K3 fingerprint join (counts only).

No judge call, no plant, no review view; counts, ids, hashes and aggregates only; no item line, declared effect,
answer or reason is read (the Kimi join reads token counts, costs, times, labels and the scorer's integer scores).

    work/mole-fork/.venv/bin/python -I work/checks/stage3_b3_power_v3c.py simulate --out RAW.json [--workers 12]
    work/mole-fork/.venv/bin/python -I work/checks/stage3_b3_power_v3c.py round2 --out R2.json
    work/mole-fork/.venv/bin/python -I work/checks/stage3_b3_power_v3c.py kimi --out K.json
    work/mole-fork/.venv/bin/python -I work/checks/stage3_b3_power_v3c.py report --raw RAW.json --round2 R2.json --kimi K.json \\
        --out-json power-simulation-v3c.json --out-md power-simulation-v3c.md
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_power_v3 as pv  # noqa: E402  (Part 2's script, unchanged)

VERSION = "b3-power-v3c"
PROJECT = HERE.parent.parent
EXPERIMENTS = pv.EXPERIMENTS
REPLICATES = pv.REPLICATES
SEED_TAG = 400                 # Part 3's seed streams: [pv.SEED, 400, ...] (Part 2 used 200 and 300)
INPUTS = "work/stage3/b3/power-simulation-v3-inputs.json"
V3B = "work/stage3/b3/power-simulation-v3b.json"
STRATUM = "work/stage3/b3/comprehension/stratum-v0.json"
DRYRUN = "work/stage3/b3/inserter-dry-run-v0.json"
KEY = pv.RATER + "/key-b3.json"
KIMI_CSV = "work/stage3/b3/comprehension/openrouter-kimi-activity.csv"
KIMI_CACHES = {"brief23": ["work/stage3/legibility/cache/judge-cache.legibility.read.kimi.moonshotai_kimi-k3.jsonl",
                           "work/stage3/legibility/cache/judge-cache.legibility.route.kimi.moonshotai_kimi-k3.jsonl"],
               "brief25": ["work/stage3/b3/comprehension/cache/judge-cache.legibility.read.kimi.moonshotai_kimi-k3.jsonl",
                           "work/stage3/b3/comprehension/cache/judge-cache.legibility.route.kimi.moonshotai_kimi-k3.jsonl"]}
SCORER_CACHE_B25 = "work/stage3/b3/comprehension/cache/judge-cache.legibility.score.anthropic-claude-sonnet-5.jsonl"

CARRIER, SECOND = pv.CARRIER, pv.SECOND
INSTS = (CARRIER, SECOND)
SING_LAYOUTS = ("T1+S1", "T2+S1", "T1+S2", "T2+S2")
ADOPTED = "T2+S2"              # Part 2's adopted layout (A6.13.8)
POPS = ("full", "stratum", "subset", "strict")
STRAT_POPS = ("stratum", "subset", "strict")
POP_NAME = {"full": "full quiet set", "stratum": "comprehension-quiet stratum", "subset": "resolved-anchor subset",
            "strict": "strict two-family stratum"}
POOL_MIN = 4                   # A6.17.3: documents with fewer than four members pool into one stratum
SMALL = 0.25                   # the small-excess sensitivity: non-members carry a quarter of the latent effect (chosen here)
LATENT_SHARES = (0.69, 0.46)   # A6.17.1: the latent quiet share of the 78 (C1's model), and its lower end beside
QUIET_N = 78
MEMBERS_N = 28
FIT_BAR, FIT_BAR_BESIDE = 0.90, 0.80   # A6.17.9 (2)
SWITCH_BOUND = 0.10            # A6.14.3: the switch does not fire when the primary's P(excluded | margin) <= 0.10
GATE = {"excl_0": 0.6, "excl_margin": 0.10, "lb_0": 0.10}   # A6.13.1
M_L = 18.22                    # A6.17.4: m_L = m_s = 18.22, a stated convention
R2_LEVEL_N = (8, 10, 12, 15, 18, 22, 26, 30, 36, 44, 52, 60, 72, 87, 100, 120, 150)
R2_SLOPE_N = (15, 20, 26, 34, 44, 56, 72, 90, 110, 140, 180, 230)
R2_SPREADS = ("stratum", "iqr", "half")   # SD 17.3 (the stratum's observed spread), IQR/1.349 and half the SD
STRATUM_SD, STRATUM_IQR = 17.3, (39.4, 57.1)   # A6.17.4: the 28's composition spread (brief 25's stratum)


def sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def latent_rate(share: float, n_quiet: int = QUIET_N, n_members: int = MEMBERS_N) -> float:
    """The probability that a non-member is truly quiet when the quiet set's latent quiet share is `share` and every
    member is truly quiet (C1's rule is pure: P(quiet | not quiet) 0.005)."""
    return float(min(max((share * n_quiet - n_members) / (n_quiet - n_members), 0.0), 1.0))


MODELS = {"none": ("all", 1.0), "zero": ("fixed", 0.0), "small": ("fixed", SMALL),
          "latent69": ("bernoulli", latent_rate(0.69)), "latent46": ("bernoulli", latent_rate(0.46))}


def membership_factor(rng, member: np.ndarray, model: str) -> np.ndarray:
    """Per item: the share of the latent composition effect it carries under the membership model."""
    kind, v = MODELS[model]
    f = np.ones(len(member))
    if kind == "fixed":
        f[~member] = v
    elif kind == "bernoulli":
        f[~member] = (rng.random(int((~member).sum())) < v).astype(float)
    return f


def pooled_strata(doc: np.ndarray, pool_min: int = POOL_MIN) -> np.ndarray:
    """A6.17.3: document codes for the stratified bootstrap, every document with fewer than pool_min members of the
    population merged into one stratum (code -1); contiguous codes returned."""
    c = Counter(doc.tolist())
    s = np.array([d if c[d] >= pool_min else -1 for d in doc.tolist()])
    return np.unique(s, return_inverse=True)[1]


# ── Step 0: the world and its populations ────────────────────────────────────────────────────────

def subset_design(D: dict, keep) -> dict:
    keep = np.asarray(keep)
    out = {k: D[k][keep] for k in ("r", "C", "c1", "c2", "sonnet", "edit", "doc")}
    out["docs"] = D["docs"]
    return out


def load_world(root: Path, rule: str = "pair") -> dict:
    """The net quiet set (brief 26's drops removed under `rule`), the design arrays, the four populations by row, the
    pooled and unpooled strata, the net comparison arm, and the checks that the mapping reproduces A6.17's figures."""
    inputs = json.loads((root / INPUTS).read_text())
    mom = inputs["moments"]
    Q = pv.quiet(pv.load_stimuli(root))
    D78 = pv.design(Q)
    key = json.loads((root / KEY).read_text())["triples"]
    st = json.loads((root / STRATUM).read_text())
    dry = json.loads((root / DRYRUN).read_text())
    rowof = {(t["writer"], t["id"]): i for i, t in enumerate(Q)}
    tid = [None] * len(Q)
    for t, rec in st["items"].items():
        if rec["regime"] == "candidate":
            k = key[t]
            tid[rowof[(k["writer"], k["id"])]] = t
    if any(t is None for t in tid):
        raise ValueError("a quiet-set row has no opaque id")
    for i, t in enumerate(tid):
        if abs(st["items"][t]["composition"] - D78["C"][i]) > 1e-9:
            raise ValueError(f"composition differs for {t}")
    drops = set(dry["drop_list"]["ids" if rule == "pair" else "ids_literal"])
    entries = dry["drop_list"]["entries"]
    sham_drops = [e["item_id"] for e in entries if e["regime"] == "sham" and (rule == "pair" or e["item_id"] in drops)]
    ctrl_drops = [e["item_id"] for e in entries if e["regime"] == "control" and (rule == "pair" or e["item_id"] in drops)]
    keep = [i for i, t in enumerate(tid) if t not in drops]
    Dw = pv.design_with_moments(subset_design(D78, keep), mom)
    ids = [tid[i] for i in keep]
    rec = [st["items"][t] for t in ids]
    member = np.array([r["membership"] == "quiet" for r in rec])
    resolved = np.array([bool(r["anchors_resolve"]) for r in rec])
    strict = member & np.array([r["readers"]["kimi"]["D_part"] == [0.0, 0.0] and r["readers"]["sol"]["D_part"] == [0.0, 0.0]
                                for r in rec])
    pops = {"full": np.arange(len(ids)), "stratum": np.flatnonzero(member), "subset": np.flatnonzero(member & resolved),
            "strict": np.flatnonzero(strict)}
    strata = {p: pooled_strata(Dw["doc"][idx]) for p, idx in pops.items()}
    raw_strata = {p: np.unique(Dw["doc"][idx], return_inverse=True)[1] for p, idx in pops.items()}
    D78m = pv.design_with_moments(D78, mom)
    r78 = D78["r"]
    desc = {}
    for p, idx in pops.items():
        c = Dw["C"][idx]
        docs = Counter(Dw["doc"][idx].tolist())
        desc[p] = {"n": int(len(idx)), "composition_mean": float(c.mean()), "composition_sd": float(c.std(ddof=1)),
                   "composition_iqr": [float(np.quantile(c, .25)), float(np.quantile(c, .75))],
                   "by_writer": {"sonnet55": int(Dw["sonnet"][idx].sum()), "glm53": int(len(idx) - Dw["sonnet"][idx].sum())},
                   "document_counts": sorted(docs.values(), reverse=True),
                   "strata_pooled": sorted(Counter(strata[p].tolist()).values(), reverse=True),
                   "dropped_here": sorted(t for t in drops if t in st["items"] and st["items"][t]["regime"] == "candidate"
                                          and (p == "full" or (st["items"][t]["membership"] == "quiet" and
                                                               (p == "stratum" or (p == "subset" and st["items"][t]["anchors_resolve"])
                                                                or (p == "strict" and st["items"][t]["readers"]["kimi"]["D_part"] == [0.0, 0.0]
                                                                    and st["items"][t]["readers"]["sol"]["D_part"] == [0.0, 0.0])))))}
    return {"rule": rule, "Dw": Dw, "D78": D78m, "ids": ids, "member": member, "pops": pops, "strata": strata,
            "raw_strata": raw_strata, "x_mean": float(r78.mean()), "x_sd": float(r78.std()),
            "n_sham": pv.N_SHAM - len(sham_drops), "n_controls": pv.N_CONTROLS - len(ctrl_drops),
            "drops": sorted(drops), "drop_entries": [e for e in entries if e["item_id"] in drops],
            "describe": desc, "inputs": inputs}


# ── the instruments: Part 2's calibration recomputed, its latent margins read ────────────────────

def instruments(root: Path, W: dict) -> dict:
    """Per instrument and ICC (5-point call noise), Part 2's DGP recomputed by its own calibrate() on the 78-item design
    (the instrument's calibration, independent of the drops), with Part 2's latent margin and m_s from its report; the
    carrier's m_s re-read at the reference cell as a reproduction check."""
    v3b = json.loads((root / V3B).read_text())
    out = {}
    for name in INSTS:
        inp = W["inputs"]["instruments"][name]
        mg = v3b["margins"][name]
        out[name] = {"latent_margin": mg["latent_margin"], "m_s": mg["m_s"],
                     "dgp": {str(icc): pv.calibrate(W["D78"], inp, icc, pv.REF_NOISE) for icc in pv.ICCS}}
        ref = out[name]["dgp"][str(pv.REF_ICC)]
        out[name]["m_s_reproduced"] = 25 * pv.observable_slope_a(W["D78"], ref, mg["latent_margin"], 1)
        out[name]["m_s_net"] = 25 * pv.observable_slope_a(W["Dw"], ref, mg["latent_margin"], 1)
    return out


# ── one world ─────────────────────────────────────────────────────────────────────────────────────

def draw_world(rng, W: dict, dgps: dict, betas: dict, layout: str, f: np.ndarray, mult: float) -> dict:
    """Part 2's generative model (pv.experiment) on the net world, the two instruments sharing the true composition,
    the judge's standardised line deviations and the comparison arm's triple draws; each view's placement and call
    noise its own. Item i carries mult x the instrument's latent margin x f[i] per composition point."""
    P, Q = pv.LAYOUTS[layout]
    D = W["Dw"]
    n, lam = len(D["C"]), D["partial_rel"]
    Ct = D["C_fit"] + lam * D["C_res"] + math.sqrt(lam * (1 - lam) * D["C_res_var"]) * rng.standard_normal(n)
    eta = rng.standard_normal((n, 3))
    sham_z = rng.standard_normal(W["n_sham"])
    x = (D["r"] - W["x_mean"]) / W["x_sd"]
    out = {"Ct": Ct}
    for name in INSTS:
        dgp = dgps[name]
        lat = dgp["rho"] * x + math.sqrt(1 - dgp["rho"] ** 2) * eta
        L = dgp["a"] + dgp["b"] * (lat - dgp["mx_mean"])
        T = L.max(1) + mult * betas[name] * f * (Ct - D["C_center"])
        sz, sc, t, pt, h = dgp["sig_z"], dgp["sig_c"], dgp["t"], dgp["p_tie"], dgp["h"]

        def noise(shape):
            return sz * rng.standard_normal(shape) + sc * rng.standard_normal(shape)

        def flag(s):
            return (s > t) | ((s == t) & (rng.random(s.shape) < pt)) | (rng.random(s.shape) < h)
        s_tri = pv.to_grid(T[:, None] + noise((n, P)))
        Ts = dgp["sham_mu"] + dgp["sham_sd_between"] * sham_z
        ns = W["n_sham"]
        s_sh = pv.to_grid(Ts[:, None] + dgp["sham_sig_z"] * rng.standard_normal((ns, P)) + sc * rng.standard_normal((ns, P)))
        out[name] = {"s_tri": s_tri, "F": flag(s_tri).astype(float), "s_sh": s_sh, "F_sh": flag(s_sh).astype(float),
                     "s_sing": pv.to_grid(L[:, :, None] + noise((n, 3, Q))).mean(-1)}
    return out


def form_a_strat(C, gap, sonnet, edit, excess, m_s, wt) -> dict:
    """Form (a) for a stratum population (A6.16.2): OLS of excess on composition, the top-two singleton gap, writer and
    replace share, with no document factor; the document-stratified bootstrap supplies `wt`. Unfit when a covariate is
    constant in the population, or when more than NONCONV_MAX of the replicates have a constant covariate (a singular
    design), counted in whole replicates."""
    n = len(C)
    X = np.column_stack([np.ones(n), C, gap, sonnet, edit])
    if any(np.ptp(X[:, j]) == 0 for j in range(1, X.shape[1])):
        return {"fit_ok": False, "75v50": {"point": None, "lo": None, "hi": None, "outcome": "unfit"}, "failed_share": 1.0}
    sw = wt.sum(1, keepdims=True)
    mean = (wt @ X[:, 1:]) / sw
    var = (wt @ X[:, 1:] ** 2) / sw - mean ** 2
    good = (var > 1e-9).all(1)
    beta = np.linalg.lstsq(X, excess, rcond=None)[0]
    XtWX = np.matmul((wt[:, :, None] * X[None]).transpose(0, 2, 1), X) + 1e-9 * np.eye(X.shape[1])
    bb = np.linalg.solve(XtWX, ((wt * excess[None]) @ X)[..., None])[..., 0]
    ok = not pv.too_many_failures(good)
    v = pv._verdict(float(beta[1] * 25), bb[good, 1] * 25 if good.any() else bb[:, 1] * 25, ok, m_s)
    return {"fit_ok": ok, "75v50": v, "failed_share": float(1 - good.mean())}


def form_b_strat(rng, C, line, gap, sonnet, edit, F, P, R, strata, ceiling_hit) -> dict:
    """Form (b) for a stratum population: Part 2's Firth logistic model without the document factor (the form (b)
    fallback path of pv.form_b), with the document-stratified bootstrap; the 75-minus-50 contrast with the continuous
    covariates at their sample means; the ceiling clause."""
    n = len(C)
    cont = np.column_stack([C, line, gap, edit])
    mu, sd = pv._std_cols(cont)
    Zc = (cont - mu) / sd
    X1 = np.column_stack([np.ones(n), Zc[:, 0], Zc[:, 1], Zc[:, 2], sonnet, Zc[:, 3]])
    X = np.repeat(X1, P, axis=0)
    y = F.ravel()
    b0, c0 = pv.irls(X, y, np.ones((1, n * P)), firth=True)
    wt = pv.bootstrap_weights(rng, n, R, strata)
    bb, cb = pv.irls(X, y, np.repeat(wt, P, axis=1), beta0=b0[0], firth=True)
    ok = bool(c0[0]) and not pv.too_many_failures(cb)
    bbc = bb[cb] if cb.any() else bb

    def predict(beta, c):
        Xe = X1.copy()
        Xe[:, 1] = (c - mu[0]) / sd[0]
        Xe[:, 2] = 0.0
        Xe[:, 3] = 0.0
        Xe[:, 5] = 0.0
        return pv.sigmoid(beta @ Xe.T).mean(-1)
    point = float((predict(b0, pv.HI_C) - predict(b0, pv.LO_C))[0])
    boot = predict(bbc, pv.HI_C) - predict(bbc, pv.LO_C)
    v = pv._verdict(point, boot, ok, pv.MARGIN, state="ceiling" if ceiling_hit else None)
    return {"fit_ok": ok, "75v50": v, "ceiling": bool(ceiling_hit)}


def fit_population(rng, W: dict, g: dict, pop: str, m_s: float, R: int, nopool: bool = False) -> dict:
    """Floors (A6.4), form (a) and form (b) for one population on one instrument's plants. The full set as Part 2
    (document factor, payload-clustered bootstrap); a stratum population without the document factor and with the
    pooled (or, nopool, the unpooled) document-stratified bootstrap."""
    D, idx = W["Dw"], W["pops"][pop]
    s_tri, F, s_sing = g["s_tri"][idx], g["F"][idx], g["s_sing"][idx]
    n, P = s_tri.shape
    full = pop == "full"
    strata = None if full else (W["raw_strata"][pop] if nopool else W["strata"][pop])
    wq = pv.bootstrap_weights(rng, n, R, strata)
    ws = pv.bootstrap_weights(rng, W["n_sham"], R)
    lo_q, _ = pv.clustered_mean_ci(wq, F)
    _, hi_s = pv.clustered_mean_ci(ws, g["F_sh"])
    M = pv.auroc_matrix(s_tri.ravel(), g["s_sh"].ravel())
    Wq, Ws = np.repeat(wq, P, axis=1), np.repeat(ws, P, axis=1)
    au = ((Wq @ M) * Ws).sum(1) / (Wq.sum(1) * Ws.sum(1))
    line_cov, gap = s_sing.max(1), pv.top_two_gap(s_sing)
    excess = s_tri.mean(1) - line_cov
    C, sonnet, edit = D["C"][idx], D["sonnet"][idx], D["edit"][idx]
    doc = np.unique(D["doc"][idx], return_inverse=True)[1]
    q1q3 = (float(np.quantile(C, .25)), float(np.quantile(C, .75)))
    ceiling = F.mean() > pv.CEILING
    if full:
        a = pv.form_a(rng, C, gap, sonnet, edit, doc, excess, R, m_s, q1q3, wt=wq)
        b = pv.form_b(rng, C, line_cov, gap, sonnet, edit, doc, F, P, R, q1q3, firth=True, ceiling_hit=ceiling) if not nopool else None
    else:
        a = form_a_strat(C, gap, sonnet, edit, excess, m_s, wq)
        b = None if nopool else form_b_strat(rng, C, line_cov, gap, sonnet, edit, F, P, R, strata, ceiling)
    rec = {"fa": bool(np.percentile(au, 2.5) > 0.5), "fb": bool(lo_q > hi_s), "a": a["75v50"]["outcome"],
           "ap": a["75v50"]["point"], "alo": a["75v50"]["lo"], "ahi": a["75v50"]["hi"], "aok": bool(a["fit_ok"]),
           "rq": float(F.mean())}
    if b is not None:
        rec.update({"b": b["75v50"]["outcome"], "bp": b["75v50"]["point"], "blo": b["75v50"]["lo"], "bok": bool(b["fit_ok"]),
                    "ceil": bool(ceiling)})
    return rec


def run_world(rng, W, dgps, betas, m_s, layout, model, mult, R) -> dict:
    f = membership_factor(rng, W["member"], model)
    g = draw_world(rng, W, dgps, betas, layout, f, mult)
    rec = {}
    for name in INSTS:
        for pop in POPS:
            rec[f"{name}|{pop}"] = fit_population(rng, W, g[name], pop, m_s[name], R)
        if name == CARRIER:
            for pop in STRAT_POPS:
                rec[f"{name}|{pop}|nopool"] = fit_population(rng, W, g[name], pop, m_s[name], R, nopool=True)
    return rec


def run_cell(args):
    key, W, dgps, betas, m_s, layout, model, mult, n_exp, R, seed_key = args
    rng = np.random.default_rng([pv.SEED, SEED_TAG] + list(seed_key))
    return key, [run_world(rng, W, dgps, betas, m_s, layout, model, mult, R) for _ in range(n_exp)]


# Truth states per cell (truth, membership model, multiple of the latent margin). At the adopted layout every
# membership model (the switch, the branches and the cascade are read there); at the other singleton layouts the
# undiluted truths that rank a carrying population's layouts; the literal-count sensitivity at the adopted layout.
TRUTHS = (("null", "none", 0.0), ("margin", "none", 1.0), ("margin", "zero", 1.0), ("margin", "small", 1.0),
          ("margin", "latent69", 1.0), ("margin", "latent46", 1.0), ("x1.5", "none", 1.5), ("x1.5", "zero", 1.5),
          ("x1.5", "latent69", 1.5))
OTHER_TRUTHS = (("null", "none", 0.0), ("margin", "none", 1.0), ("x1.5", "none", 1.5))
LITERAL_TRUTHS = (("null", "none", 0.0), ("margin", "none", 1.0), ("margin", "zero", 1.0), ("x1.5", "none", 1.5))
CASCADE_MODELS = ("zero", "latent69")     # the membership models with a 1.5 x cell (the cascade's present at 1.5 x)


def truths_at(rule: str, layout: str):
    if rule == "literal":
        return LITERAL_TRUTHS
    return TRUTHS if layout == ADOPTED else OTHER_TRUTHS


def build_cells(W_pair, W_lit, inst, quick=False):
    n_exp, R = (12, 200) if quick else (EXPERIMENTS, REPLICATES)
    betas = {k: inst[k]["latent_margin"] for k in INSTS}
    m_s = {k: inst[k]["m_s"] for k in INSTS}
    cells = []
    for wi, (rule, W, layouts) in enumerate((("pair", W_pair, SING_LAYOUTS), ("literal", W_lit, (ADOPTED,)))):
        for li, layout in enumerate(layouts):
            for ci, icc in enumerate(pv.ICCS):
                dgps = {k: inst[k]["dgp"][str(icc)] for k in INSTS}
                for ti, (truth, model, mult) in enumerate(truths_at(rule, layout)):
                    key = f"{rule}|{layout}|{icc}|{truth}|{model}"
                    cells.append((key, _slim(W), dgps, betas, m_s, layout, model, mult, n_exp, R, (wi, li, ci, ti)))
    return cells


def _slim(W):
    return {k: W[k] for k in ("Dw", "member", "pops", "strata", "raw_strata", "x_mean", "x_sd", "n_sham")}


# ── summaries ────────────────────────────────────────────────────────────────────────────────────

NOT_READ = ("floor", "unfit", "unavailable", "ceiling")


def a_outcome(rec) -> str:
    return "floor" if not rec["fa"] else rec["a"]


def label_of(rec, bias_b) -> dict:
    """A6.13.4's per-instrument label from a compact record (pv.instrument_label on the same fields)."""
    out = {"floor_a": rec["fa"], "a": {"75v50": {"outcome": rec["a"]}}, "floor_b": rec["fb"],
           "b": {"75v50": {"outcome": rec["b"], "lo": rec["blo"]}}}
    return pv.instrument_label(out, bias_b)


def shares(outcomes) -> dict:
    n = len(outcomes)
    c = Counter(outcomes)
    out = {o: c.get(o, 0) / n for o in ("excluded", "attenuated", "present", "inconclusive") + NOT_READ}
    out["lb_above_0"] = out["attenuated"] + out["present"]
    out["not_read"] = sum(out[o] for o in NOT_READ)
    return out


def null_bias_b(raw, rule, layout, icc, inst, pop):
    rows = raw.get(f"{rule}|{layout}|{icc}|null|none")
    if rows is None:
        return None
    v = [r[f"{inst}|{pop}"]["bp"] for r in rows if r[f"{inst}|{pop}"].get("bok") and r[f"{inst}|{pop}"].get("bp") is not None]
    return float(np.mean(v)) if v else None


def instrument_summary(raw, rule, layout, inst, pop, model, suffix="") -> dict | None:
    """A6.13.1 per instrument (form (a)), each probability at the worse ICC: P(excluded | 0), P(excluded | margin) under
    the membership model, P(LB > 0 | 0), P(present | 1.5 x margin); the fit rate (form (a) fitted) and the read rate
    (floor met and fitted) at the worse ICC under the null."""
    k = f"{inst}|{pop}{suffix}"
    by = {}
    for icc in pv.ICCS:
        n0 = raw.get(f"{rule}|{layout}|{icc}|null|none")
        nm = raw.get(f"{rule}|{layout}|{icc}|margin|{model}")
        if n0 is None or nm is None:
            return None
        n15 = raw.get(f"{rule}|{layout}|{icc}|x1.5|{model}")
        s0, sm = shares([a_outcome(r[k]) for r in n0]), shares([a_outcome(r[k]) for r in nm])
        s15 = shares([a_outcome(r[k]) for r in n15]) if n15 else None
        by[str(icc)] = {"P_excl_0": s0["excluded"], "P_excl_margin": sm["excluded"], "P_lb_0": s0["lb_above_0"],
                        "P_present_0": s0["present"], "P_present_margin": sm["present"],
                        "P_present_x1.5": s15["present"] if s15 else None, "P_not_read_0": s0["not_read"],
                        "fit_rate_0": float(np.mean([r[k]["aok"] for r in n0])),
                        "read_rate_0": float(np.mean([r[k]["fa"] and r[k]["aok"] for r in n0])),
                        "read_rate_margin": float(np.mean([r[k]["fa"] and r[k]["aok"] for r in nm])),
                        "floor_0": s0["floor"], "unfit_0": s0["unfit"],
                        "point_mean_0": _mean([r[k]["ap"] for r in n0 if r[k]["ap"] is not None]),
                        "point_mean_margin": _mean([r[k]["ap"] for r in nm if r[k]["ap"] is not None])}
    ic = list(by.values())
    p15 = [x["P_present_x1.5"] for x in ic]
    out = {"P_excl_0": min(x["P_excl_0"] for x in ic), "P_excl_margin": max(x["P_excl_margin"] for x in ic),
           "P_lb_0": max(x["P_lb_0"] for x in ic), "P_present_0": max(x["P_present_0"] for x in ic),
           "P_present_x1.5": min(p15) if all(p is not None for p in p15) else None,
           "fit_rate": min(x["fit_rate_0"] for x in ic), "read_rate": min(x["read_rate_0"] for x in ic),
           "read_rate_margin": min(x["read_rate_margin"] for x in ic), "by_icc": by}
    out["readable"] = (out["P_excl_0"] >= GATE["excl_0"] and out["P_excl_margin"] <= GATE["excl_margin"]
                       and out["P_lb_0"] <= GATE["lb_0"])
    out["score"] = out["P_excl_0"] + out["P_present_x1.5"] if out["P_present_x1.5"] is not None else None
    return out


def _mean(v):
    return float(np.mean(v)) if v else None


def verdicts(raw, rule, layout, icc, truth, model, pop, second_readable: bool) -> list[dict] | None:
    """A6.13.4's combined verdict per experiment on one population (carrier-first; (b)'s downgrade subtracts the
    population's simulated null bias at this layout and ICC)."""
    rows = raw.get(f"{rule}|{layout}|{icc}|{truth}|{model}")
    if rows is None:
        return None
    bc, bs = (null_bias_b(raw, rule, layout, icc, CARRIER, pop), null_bias_b(raw, rule, layout, icc, SECOND, pop))
    out = []
    for r in rows:
        lc, ls = label_of(r[f"{CARRIER}|{pop}"], bc), label_of(r[f"{SECOND}|{pop}"], bs)
        v = pv.combine(lc["label"], ls["label"], second_readable)
        out.append({"carrier": lc["label"], "carrier_a": a_outcome(r[f"{CARRIER}|{pop}"]), "second": ls["label"], **v})
    return out


def verdict_summary(raw, rule, layout, pop, model, second_readable) -> dict | None:
    by = {}
    for icc in pv.ICCS:
        v0 = verdicts(raw, rule, layout, icc, "null", "none", pop, second_readable)
        vm = verdicts(raw, rule, layout, icc, "margin", model, pop, second_readable)
        v15 = verdicts(raw, rule, layout, icc, "x1.5", model, pop, second_readable)
        if v0 is None or vm is None:
            return None
        s = lambda vs, o: sum(1 for x in vs if x["verdict"] == o) / len(vs)
        by[str(icc)] = {"P_holds_0": s(v0, "excluded"), "P_falsified_0": s(v0, "present"),
                        "P_lb_0": s(v0, "attenuated") + s(v0, "present"), "P_holds_margin": s(vm, "excluded"),
                        "P_falsified_margin": s(vm, "present"), "P_partly_margin": s(vm, "attenuated"),
                        "P_falsified_x1.5": s(v15, "present") if v15 else None,
                        "P_no_verdict_0": s(v0, "no_verdict"), "P_fallback_0": sum(x["fallback"] for x in v0) / len(v0)}
    ic = list(by.values())
    return {"P_holds_0": min(x["P_holds_0"] for x in ic), "P_falsified_0": max(x["P_falsified_0"] for x in ic),
            "P_lb_0": max(x["P_lb_0"] for x in ic), "P_holds_margin": max(x["P_holds_margin"] for x in ic),
            "P_falsified_margin": min(x["P_falsified_margin"] for x in ic),
            "P_falsified_x1.5": min(x["P_falsified_x1.5"] for x in ic) if all(x["P_falsified_x1.5"] is not None for x in ic) else None,
            "P_no_verdict_0": max(x["P_no_verdict_0"] for x in ic), "by_icc": by, "second_readable": second_readable}


# ── the cascade (A6.17.9) ─────────────────────────────────────────────────────────────────────────

def passes(gate: dict | None, bar: float) -> bool:
    """A population can carry when the carrier meets A6.13.1 at its n and its simulated fit rate reaches the bar (the
    fit rate read as the share of experiments in which form (a) is read: floor met and fitted)."""
    return bool(gate and gate["readable"] and min(gate["read_rate"], gate["read_rate_margin"]) >= bar)


def cascade_order(fired: bool, ok_subset: bool, ok_stratum: bool) -> list[str]:
    """The ordered rule: the full set when the switch does not fire; else the 19 (net 17), else the 28 (net 26),
    else the third branch; the step-down order from the chosen carrier (A6.17.9 (4))."""
    if not fired:
        return ["full"]
    order = ["subset", "stratum", "third"]
    start = "subset" if ok_subset else ("stratum" if ok_stratum else "third")
    return order[order.index(start):]


def cascade_land(steps: list[str], per_pop: dict, present_stands: bool) -> tuple[str, str]:
    """One experiment: step down from the chosen carrier while its carrier reading is at floor or unfit (A6.13.4's
    fallback clause applying to the carrier population); the third branch issues only a full-set present (when the
    recorded decision lets it stand), else 'inconclusive'."""
    for p in steps:
        if p == "full":
            return "full", per_pop["full"]["verdict"]
        if p == "third":
            v = per_pop["full"]["verdict"]
            return "third", (v if (v == "present" and present_stands) else "inconclusive")
        if per_pop[p]["carrier_a"] in ("floor", "unfit"):
            continue
        return p, per_pop[p]["verdict"]
    return "third", "inconclusive"


def cascade_oc(raw, rule, layout, steps, model, present_stands, sec_ok) -> dict:
    """The cascade's joint operating characteristics on shared worlds, worse ICC: the probability of each branch and,
    for the verdict actually carried, P(excluded | 0), P(excluded | margin), P(LB > 0 | 0), P(present | 0)."""
    by = {}
    for icc in pv.ICCS:
        res = {}
        for truth, mdl in (("null", "none"), ("margin", model), ("x1.5", model)):
            pv_ = {p: verdicts(raw, rule, layout, icc, truth, mdl, p, sec_ok[p]) for p in POPS}
            if any(v is None for v in pv_.values()):
                return {}
            land = [cascade_land(steps, {p: pv_[p][e] for p in POPS}, present_stands) for e in range(len(pv_["full"]))]
            n = len(land)
            res[truth] = {"branch": {b: sum(1 for x in land if x[0] == b) / n for b in ("full", "subset", "stratum", "third")},
                          "excluded": sum(1 for x in land if x[1] == "excluded") / n,
                          "lb_above_0": sum(1 for x in land if x[1] in ("attenuated", "present")) / n,
                          "present": sum(1 for x in land if x[1] == "present") / n}
        by[str(icc)] = res
    ic = list(by.values())
    return {"P_excl_0": min(x["null"]["excluded"] for x in ic), "P_excl_margin": max(x["margin"]["excluded"] for x in ic),
            "P_lb_0": max(x["null"]["lb_above_0"] for x in ic), "P_present_0": max(x["null"]["present"] for x in ic),
            "P_present_margin": min(x["margin"]["present"] for x in ic), "P_present_x1.5": min(x["x1.5"]["present"] for x in ic),
            "branch_null": {b: max(x["null"]["branch"][b] for x in ic) for b in ("full", "subset", "stratum", "third")},
            "branch_margin": {b: max(x["margin"]["branch"][b] for x in ic) for b in ("full", "subset", "stratum", "third")},
            "by_icc": by}


# ── round 2 (A6.15 (e), A6.16.3, A6.17.4) ─────────────────────────────────────────────────────────

def r2_pool(W: dict) -> dict:
    """The design rows round 2 draws from: the net stratum (its lines, composition, writer and edit type)."""
    idx = W["pops"]["stratum"]
    D = W["Dw"]
    return {k: D[k][idx] for k in ("r", "C", "sonnet", "edit")}


def r2_items(rng, pool, n, dgp, W, layout, delta=0.0, beta=0.0, sd_scale=1.0):
    """n items drawn from the pool with replacement under the carrier's DGP: per item the excess (mean triple score over
    placements minus the maximum of the lines' mean singleton scores), its composition and covariates; a level shift
    delta on the latent score (round 2's certified arm) and a composition effect beta (the slope reading), with the
    composition spread scaled about the pool mean by sd_scale and measured at the quiet set's reliability."""
    P, Q = pv.LAYOUTS[layout]
    i = rng.integers(0, len(pool["C"]), n)
    x = (pool["r"][i] - W["x_mean"]) / W["x_sd"]
    lat = dgp["rho"] * x + math.sqrt(1 - dgp["rho"] ** 2) * rng.standard_normal((n, 3))
    L = dgp["a"] + dgp["b"] * (lat - dgp["mx_mean"])
    m0 = float(pool["C"].mean())
    Cobs = m0 + sd_scale * (pool["C"][i] - m0)
    lam = W["Dw"]["partial_rel"]
    Cv = float(np.var(sd_scale * pool["C"]))
    Ct = m0 + lam * (Cobs - m0) + math.sqrt(lam * (1 - lam) * Cv) * rng.standard_normal(n)
    T = L.max(1) + delta + beta * (Ct - m0)
    sz, sc = dgp["sig_z"], dgp["sig_c"]

    def noise(shape):
        return sz * rng.standard_normal(shape) + sc * rng.standard_normal(shape)
    s_tri = pv.to_grid(T[:, None] + noise((n, P)))
    s_sing = pv.to_grid(L[:, :, None] + noise((n, 3, Q))).mean(-1)
    return {"excess": s_tri.mean(1) - s_sing.max(1), "C": Cobs, "gap": pv.top_two_gap(s_sing), "sonnet": pool["sonnet"][i],
            "edit": pool["edit"][i], "s_tri": s_tri}


def r2_delta_for(pool, dgp, W, layout, target, n_mc=20000, seed=7):
    """The latent level shift whose observable mean excess difference (certified minus illegible, every noise source
    on the grid) equals target; common random numbers across delta."""
    def diff(d):
        rng = np.random.default_rng([pv.SEED, SEED_TAG, 9, seed])
        a = r2_items(rng, pool, n_mc, dgp, W, layout, delta=d)["excess"].mean()
        rng = np.random.default_rng([pv.SEED, SEED_TAG, 9, seed])
        b = r2_items(rng, pool, n_mc, dgp, W, layout, delta=0.0)["excess"].mean()
        return float(a - b)
    hi = target
    while diff(hi) < target and hi < 20 * target:
        hi *= 1.5
    return pv._solve(diff, 0.0, hi, target, iters=40)


def r2_level_experiment(rng, pool, dgp, W, layout, n, delta, margin, R):
    """One round-2 experiment: n certified and n quiet-but-illegible items (independent draws from the stratum's
    rows; matching on writer, document and composition band does not enter the model, which carries no writer or
    document effect), the level contrast of mean excess with a bootstrap over items within arms, four outcomes against
    the margin; the certified arm's floor against the comparison arm (A6.4 (a)) beside."""
    c = r2_items(rng, pool, n, dgp, W, layout, delta=delta)
    q = r2_items(rng, pool, n, dgp, W, layout)
    wc, wi = pv.bootstrap_weights(rng, n, R), pv.bootstrap_weights(rng, n, R)
    point = float(c["excess"].mean() - q["excess"].mean())
    boot = (wc @ c["excess"]) / n - (wi @ q["excess"]) / n
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return pv.four_outcome(lo, hi, point, margin)


def r2_slope_experiment(rng, pool, dgp, W, layout, n, beta, m_s, R, sd_scale):
    c = r2_items(rng, pool, n, dgp, W, layout, beta=beta, sd_scale=sd_scale)
    wt = pv.bootstrap_weights(rng, n, R)
    a = form_a_strat(c["C"], c["gap"], c["sonnet"], c["edit"], c["excess"], m_s, wt)
    return a["75v50"]["outcome"]


def r2_gate(outs0, outsm, outs15) -> dict:
    s0, sm, s15 = shares(outs0), shares(outsm), shares(outs15)
    return {"P_excl_0": s0["excluded"], "P_excl_margin": sm["excluded"], "P_lb_0": s0["lb_above_0"],
            "P_present_x1.5": s15["present"], "P_unfit_0": s0["unfit"]}


def round2(root: Path, quick=False) -> dict:
    W = load_world(root, "pair")
    inst = instruments(root, W)
    pool = r2_pool(W)
    n_exp, R = (40, 200) if quick else (EXPERIMENTS, REPLICATES)
    sd_obs = float(np.std(pool["C"], ddof=1))
    iqr = float(np.subtract(*np.quantile(pool["C"], [.75, .25])))
    targets = {"stratum": STRATUM_SD, "iqr": (STRATUM_IQR[1] - STRATUM_IQR[0]) / 1.349, "half": STRATUM_SD / 2}
    spreads = {k: v / sd_obs for k, v in targets.items()}
    out = {"pool": {"n": len(pool["C"]), "composition_sd": sd_obs, "iqr": iqr}, "spread_targets_sd": targets,
           "level": {}, "slope": {}, "deltas": {}}
    dgps = inst[CARRIER]["dgp"]
    for mname, m in (("m_L", M_L), ("m_L/2", M_L / 2)):
        for icc in pv.ICCS:
            dgp = dgps[str(icc)]
            d, st = r2_delta_for(pool, dgp, W, ADOPTED, m)
            d15, st15 = r2_delta_for(pool, dgp, W, ADOPTED, 1.5 * m)
            out["deltas"][f"{mname}|{icc}"] = {"delta": d, "status": st, "delta_x1.5": d15, "status_x1.5": st15}
            for ni, n in enumerate(R2_LEVEL_N):
                rng = np.random.default_rng([pv.SEED, SEED_TAG, 21, int(icc * 10), ni, int(m * 100)])
                o0 = [r2_level_experiment(rng, pool, dgp, W, ADOPTED, n, 0.0, m, R) for _ in range(n_exp)]
                om = [r2_level_experiment(rng, pool, dgp, W, ADOPTED, n, d, m, R) for _ in range(n_exp)]
                o15 = [r2_level_experiment(rng, pool, dgp, W, ADOPTED, n, d15, m, R) for _ in range(n_exp)]
                out["level"][f"{mname}|{icc}|{n}"] = r2_gate(o0, om, o15)
    beta, m_s = inst[CARRIER]["latent_margin"], inst[CARRIER]["m_s"]
    for sp, scale in spreads.items():
        for icc in pv.ICCS:
            dgp = dgps[str(icc)]
            for ni, n in enumerate(R2_SLOPE_N):
                rng = np.random.default_rng([pv.SEED, SEED_TAG, 22, int(icc * 10), ni, R2_SPREADS.index(sp)])
                o0 = [r2_slope_experiment(rng, pool, dgp, W, ADOPTED, n, 0.0, m_s, R, scale) for _ in range(n_exp)]
                om = [r2_slope_experiment(rng, pool, dgp, W, ADOPTED, n, beta, m_s, R, scale) for _ in range(n_exp)]
                o15 = [r2_slope_experiment(rng, pool, dgp, W, ADOPTED, n, 1.5 * beta, m_s, R, scale) for _ in range(n_exp)]
                out["slope"][f"{sp}|{icc}|{n}"] = r2_gate(o0, om, o15)
    out["experiments"], out["replicates"] = n_exp, R
    return out


def r2_min_n(table: dict, prefix: str, grid) -> dict:
    """The smallest n on the grid from which every larger grid n is readable under A6.13.1 at both ICCs; None when
    none is."""
    ok = []
    for n in grid:
        g = [table.get(f"{prefix}|{icc}|{n}") for icc in pv.ICCS]
        ok.append(all(x is not None for x in g) and min(x["P_excl_0"] for x in g) >= GATE["excl_0"]
                  and max(x["P_excl_margin"] for x in g) <= GATE["excl_margin"] and max(x["P_lb_0"] for x in g) <= GATE["lb_0"])
    for i, n in enumerate(grid):
        if all(ok[i:]):
            return {"n": n, "readable_from": n}
    return {"n": None, "readable_from": None}


# ── item 7: Kimi K3's routing ─────────────────────────────────────────────────────────────────────

def _ts(s: str) -> float:
    s = s.replace("T", " ").replace("+00:00", "").replace("Z", "")
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def fingerprint_join(cache_recs: list[dict], export: list[dict]) -> dict:
    """Match each cache record to one export generation on (prompt tokens, completion tokens); within a shared key,
    records and generations are paired in time order (the export's creation time at or before the record's
    completion time, nearest first). Cost agreement is counted as a check. Returns the pairing by record index."""
    by_key: dict = defaultdict(list)
    for j, e in enumerate(export):
        by_key[(e["tokens_prompt"], e["tokens_completion"])].append(j)
    rec_by_key: dict = defaultdict(list)
    for i, r in enumerate(cache_recs):
        rec_by_key[(r["input_tokens"], r["output_tokens"])].append(i)
    match, ambiguous_keys, ambiguous_records, order_violations = {}, 0, 0, 0
    for k, recs in rec_by_key.items():
        gens = sorted(by_key.get(k, []), key=lambda j: (export[j]["t"], j))
        recs = sorted(recs, key=lambda i: (cache_recs[i]["t"], i))
        if len(recs) > 1 or len(gens) > 1:
            ambiguous_keys += 1
            ambiguous_records += len(recs)
        for i, j in zip(recs, gens):
            match[i] = j
            order_violations += export[j]["t"] > cache_recs[i]["t"] + 1      # a generation created after the record completed
    cost_ok = sum(1 for i, j in match.items() if abs(cache_recs[i]["cost"] - export[j]["cost"]) <= 1e-6)
    return {"match": match, "matched": len(match), "records": len(cache_recs), "ambiguous_keys": ambiguous_keys,
            "ambiguous_records": ambiguous_records, "time_order_violations": order_violations, "cost_agrees": cost_ok,
            "generations_used": len(set(match.values())), "generations": len(export)}


def kimi(root: Path) -> dict:
    """A6.17.10 (b), counts only: the fingerprint join of every Kimi K3 cache record (briefs 23 and 25) to the
    OpenRouter export; on brief 25's matched reads, the upstream provider and quantization by sample, the share of
    parts credited (the scorer's integer scores against the L target) by provider and sample, and the quiet-status
    flips by provider. Descriptive; membership is never recomputed."""
    p = root / KIMI_CSV
    if not p.exists():
        return {"present": False}
    export = []
    for r in csv.DictReader(p.open()):
        export.append({"tokens_prompt": int(r["tokens_prompt"]), "tokens_completion": int(r["tokens_completion"]),
                       "cost": float(r["cost_total"] or 0), "t": _ts(r["created_at"]), "provider": r["provider_name"],
                       "precision": r["precision"]})
    recs = []
    for brief, files in KIMI_CACHES.items():
        for f in files:
            for line in (root / f).read_text().splitlines():
                if not line.strip():
                    continue
                d = json.loads(line)
                recs.append({"brief": brief, "label": d["label"], "input_tokens": int(d["input_tokens"]),
                             "output_tokens": int(d["output_tokens"]), "cost": float(d["cost_usd"] or 0), "t": _ts(d["ts"])})
    J = fingerprint_join(recs, export)
    m = J.pop("match")
    out = {"present": True, "join": J, "by_brief": {}, "export_providers": dict(Counter(e["provider"] for e in export)),
           "export_precision": dict(Counter(e["precision"] for e in export))}
    for b in KIMI_CACHES:
        idx = [i for i, r in enumerate(recs) if r["brief"] == b]
        out["by_brief"][b] = {"records": len(idx), "matched": sum(1 for i in idx if i in m),
                              "providers": dict(Counter(export[m[i]]["provider"] for i in idx if i in m)),
                              "precision": dict(Counter(export[m[i]]["precision"] for i in idx if i in m))}
    # brief 25: reads by sample, credit by provider, flips by provider
    st = json.loads((root / STRATUM).read_text())["items"]
    scores: dict = defaultdict(list)
    for line in (root / SCORER_CACHE_B25).read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        parts = d["label"].split(":")       # score:p{pass}:{reader}:r{sample}:{item}:{cond}:{target}
        if parts[2] != "kimi" or d.get("outcome") != "scored":
            continue
        scores[(int(parts[3][1:]), parts[4], parts[5], parts[6])].append(int(d["score"]))
    reads = {}
    for i, r in enumerate(recs):
        if r["brief"] != "brief25" or not r["label"].startswith("read:") or i not in m:
            continue
        _, s, item, cond = r["label"].split(":")
        reads[(int(s[1:]), item, cond)] = export[m[i]]
    cand = {t for t, v in st.items() if v["regime"] == "candidate"}
    by_ps: dict = defaultdict(lambda: {"reads": 0, "credit_sum": 0.0, "credited": 0, "scored": 0})
    prov_by_sample: dict = defaultdict(Counter)
    for (s, item, cond), e in reads.items():
        prov_by_sample[s][e["provider"]] += 1
        if item not in cand or not cond.startswith("part"):
            continue
        k = f"{e['provider']}|r{s}"
        by_ps[k]["reads"] += 1
        sc = scores.get((s, item, cond, "rubric"))
        if sc:
            v = sum(sc) / len(sc)
            by_ps[k]["scored"] += 1
            by_ps[k]["credit_sum"] += v
            by_ps[k]["credited"] += int(v > 0)
    credit = {k: {"part_reads": v["reads"], "scored": v["scored"], "mean_part_score": v["credit_sum"] / v["scored"] if v["scored"] else None,
                  "share_credited": v["credited"] / v["scored"] if v["scored"] else None} for k, v in sorted(by_ps.items())}
    flips = Counter()
    flip_prov = Counter()
    for t in cand:
        dp = st[t]["readers"]["kimi"]["D_part"]
        if dp is None or len(dp) != 2 or None in dp:
            continue
        q0, q1 = dp[0] == 0, dp[1] == 0
        kind = "stable_quiet" if q0 and q1 else ("stable_not" if not (q0 or q1) else ("quiet_s0_not_s1" if q0 else "not_s0_quiet_s1"))
        flips[kind] += 1
        if kind in ("quiet_s0_not_s1", "not_s0_quiet_s1"):
            s_not = 1 if kind == "quiet_s0_not_s1" else 0
            provs = set()
            for c in ("part0", "part1", "part2"):
                sc = scores.get((s_not, t, c, "rubric"))
                e = reads.get((s_not, t, c))
                if sc and e and sum(sc) > 0:
                    provs.add(e["provider"])
            for pr in sorted(provs) or ["(credited part unmatched)"]:
                flip_prov[f"{kind}|{pr}"] += 1
    out["brief25"] = {"reads_matched": len(reads), "providers_by_sample": {f"r{s}": dict(c) for s, c in sorted(prov_by_sample.items())},
                      "part_credit_by_provider_and_sample": credit, "candidate_flips": dict(flips),
                      "flip_credited_part_provider": dict(sorted(flip_prov.items()))}
    return out


# ── provenance ────────────────────────────────────────────────────────────────────────────────────

PROV_FILES = (INPUTS, V3B, STRATUM, DRYRUN, KEY)


def provenance(root: Path) -> dict:
    return {"script_sha256": sha256(__file__), "part2_script_sha256": sha256(pv.__file__),
            "inputs_sha256": {f: sha256(root / f) for f in PROV_FILES}}


# ── commands ──────────────────────────────────────────────────────────────────────────────────────

def cmd_simulate(a):
    root = Path(a.root)
    prov = provenance(root)
    W_pair, W_lit = load_world(root, "pair"), load_world(root, "literal")
    inst = instruments(root, W_pair)
    cells = build_cells(W_pair, W_lit, inst, quick=a.quick)
    if a.only:
        cells = [c for c in cells if a.only in c[0]]
    print(f"{len(cells)} cells", flush=True)
    res = pv._pool_map(run_cell, cells, a.workers)
    Path(a.out).write_text(json.dumps({"version": f"{VERSION}/raw", **prov, "experiments": cells[0][8] if cells else None,
                                       "replicates": cells[0][9] if cells else None, "instruments": inst,
                                       "cells": res}, default=float))


def cmd_round2(a):
    root = Path(a.root)
    prov = provenance(root)
    Path(a.out).write_text(json.dumps({"version": f"{VERSION}/round2", **prov, **round2(root, quick=a.quick)}, indent=1))


def cmd_kimi(a):
    root = Path(a.root)
    Path(a.out).write_text(json.dumps({"version": f"{VERSION}/kimi", **provenance(root), **kimi(root)}, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description="brief 20 Part 3")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("simulate", "round2", "kimi", "report"):
        s = sub.add_parser(name)
        s.add_argument("--root", default=str(PROJECT))
        s.add_argument("--quick", action="store_true")
        if name in ("simulate", "round2", "kimi"):
            s.add_argument("--out", required=True)
        if name == "simulate":
            s.add_argument("--workers", type=int, default=12)
            s.add_argument("--only", default=None)
        if name == "report":
            s.add_argument("--raw", required=True)
            s.add_argument("--round2", required=True)
            s.add_argument("--kimi", required=True)
            s.add_argument("--out-json", required=True)
            s.add_argument("--out-md", required=True)
    a = ap.parse_args(argv)
    {"simulate": cmd_simulate, "round2": cmd_round2, "kimi": cmd_kimi, "report": cmd_report}[a.cmd](a)
    return 0


# ── the report ────────────────────────────────────────────────────────────────────────────────────

def margin_models(rule: str, layout: str) -> list[str]:
    return sorted({m for t, m, _ in truths_at(rule, layout) if t == "margin"})


def gates_all(cells) -> dict:
    """Per rule, layout, population, instrument and membership model: A6.13.1's values (form (a), worse ICC). Stratum
    populations are all members, so only the undiluted model applies to them; the carrier's unpooled bootstrap beside."""
    G = {}
    for rule, layouts in (("pair", SING_LAYOUTS), ("literal", (ADOPTED,))):
        for layout in layouts:
            for pop in POPS:
                for inst in INSTS:
                    for model in (margin_models(rule, layout) if pop == "full" else ["none"]):
                        g = instrument_summary(cells, rule, layout, inst, pop, model)
                        if g:
                            G[f"{rule}|{layout}|{pop}|{inst}|{model}"] = g
                if pop != "full":
                    g = instrument_summary(cells, rule, layout, CARRIER, pop, "none", suffix="|nopool")
                    if g:
                        G[f"{rule}|{layout}|{pop}|{CARRIER}|none|nopool"] = g
    return G


def second_ok(G, rule, layout, pop) -> bool:
    return bool(G.get(f"{rule}|{layout}|{pop}|{SECOND}|none", {}).get("readable"))


def verdicts_all(cells, G) -> dict:
    V = {}
    for rule, layouts in (("pair", SING_LAYOUTS), ("literal", (ADOPTED,))):
        for layout in layouts:
            for pop in POPS:
                for model in (margin_models(rule, layout) if pop == "full" else ["none"]):
                    v = verdict_summary(cells, rule, layout, pop, model, second_ok(G, rule, layout, pop))
                    if v:
                        V[f"{rule}|{layout}|{pop}|{model}"] = v
    return V


def carry_layouts(G, rule, pop, bar) -> list[str]:
    layouts = SING_LAYOUTS if rule == "pair" else (ADOPTED,)
    ok = [l for l in layouts if passes(G.get(f"{rule}|{l}|{pop}|{CARRIER}|none"), bar)]
    return sorted(ok, key=lambda l: -(G[f"{rule}|{l}|{pop}|{CARRIER}|none"]["score"] or 0))


def selection(cells, G, V, rule: str) -> dict:
    """Items 1, 4 and 5: the switch at the observed share (the combined verdict's P(holds | margin) under the zero
    model, the upper bound on dilution, at the adopted layout), then the cascade at the 0.90 bar and at 0.80 beside,
    with its joint operating characteristics at the adopted layout under each membership model that has a 1.5 x cell."""
    sw = V[f"{rule}|{ADOPTED}|full|zero"]
    fired = sw["P_holds_margin"] > SWITCH_BOUND
    out = {"switch": {"statistic": "the full set's combined verdict P(holds | truth on the margin), members carrying the effect and "
                                   "non-members none (the upper bound on dilution), worse ICC, adopted layout",
                      "P_holds_margin": sw["P_holds_margin"], "bound": SWITCH_BOUND, "fires": fired,
                      "carrier_alone_P_excl_margin": G[f"{rule}|{ADOPTED}|full|{CARRIER}|zero"]["P_excl_margin"],
                      "carrier_alone_fires": G[f"{rule}|{ADOPTED}|full|{CARRIER}|zero"]["P_excl_margin"] > SWITCH_BOUND,
                      "by_model": {m: {"P_holds_margin": V[f"{rule}|{ADOPTED}|full|{m}"]["P_holds_margin"],
                                       "carrier_P_excl_margin": G[f"{rule}|{ADOPTED}|full|{CARRIER}|{m}"]["P_excl_margin"]}
                                   for m in margin_models(rule, ADOPTED)}},
           "bars": {}}
    for bar in (FIT_BAR, FIT_BAR_BESIDE):
        ok = {p: carry_layouts(G, rule, p, bar) for p in ("subset", "stratum")}
        steps = cascade_order(fired, bool(ok["subset"]), bool(ok["stratum"]))
        carrier_pop = steps[0]
        layout = ok[carrier_pop][0] if carrier_pop in ok else ADOPTED
        oc = {}
        for at in dict.fromkeys((layout, ADOPTED)):
            # at a layout without the diluted cells the third branch's full-set reading is undiluted ("none"), named
            models = [m for m in CASCADE_MODELS if f"{rule}|{at}|{pv.ICCS[0]}|x1.5|{m}" in cells] or ["none"]
            sat = {p: second_ok(G, rule, at, p) for p in POPS}
            for m in models:
                oc[f"{at}|{m}"] = {("present_stands" if ps else "present_not_issued"): cascade_oc(cells, rule, at, steps, m, ps, sat)
                                   for ps in (True, False)}
        out["bars"][str(bar)] = {"passing_layouts": ok, "steps": steps, "carrying_population": carrier_pop,
                                 "carrying_layout": layout, "cascade": oc}
    b90, b80 = out["bars"][str(FIT_BAR)], out["bars"][str(FIT_BAR_BESIDE)]
    out["bars_select_differently"] = b90["steps"] != b80["steps"]
    return out


def report(a):
    root = Path(a.root)
    raw = json.loads(Path(a.raw).read_text())
    r2 = json.loads(Path(a.round2).read_text())
    kj = json.loads(Path(a.kimi).read_text())
    now = provenance(root)
    prov = {"report_script": now["script_sha256"], "simulate_script": raw.get("script_sha256"), "round2_script": r2.get("script_sha256"),
            "kimi_script": kj.get("script_sha256"), "part2_script": now["part2_script_sha256"], "inputs_sha256": now["inputs_sha256"],
            "raw_sha256": sha256(a.raw), "round2_sha256": sha256(a.round2), "kimi_sha256": sha256(a.kimi)}
    prov["consistent"] = (raw.get("script_sha256") == r2.get("script_sha256") == kj.get("script_sha256") == now["script_sha256"]
                          and raw.get("inputs_sha256") == r2.get("inputs_sha256") == kj.get("inputs_sha256") == now["inputs_sha256"]
                          and raw.get("part2_script_sha256") == now["part2_script_sha256"])
    cells = raw["cells"]
    Wp, Wl = load_world(root, "pair"), load_world(root, "literal")
    G = gates_all(cells)
    V = verdicts_all(cells, G)
    sel = {"pair": selection(cells, G, V, "pair"), "literal": selection(cells, G, V, "literal")}
    r2_out = {"level": {m: r2_min_n(r2["level"], m, R2_LEVEL_N) for m in ("m_L", "m_L/2")},
              "slope": {s: r2_min_n(r2["slope"], s, R2_SLOPE_N) for s in R2_SPREADS},
              "deltas": r2["deltas"], "pool": r2["pool"], "spread_targets_sd": r2["spread_targets_sd"],
              "level_table": r2["level"], "slope_table": r2["slope"], "experiments": r2["experiments"], "replicates": r2["replicates"]}
    inst = {k: {kk: v[kk] for kk in ("latent_margin", "m_s", "m_s_reproduced", "m_s_net")} for k, v in raw["instruments"].items()}
    R = {"version": f"{VERSION}/report", "brief": "20 Part 3", "seed": pv.SEED, "seed_tag": SEED_TAG,
         "experiments": raw["experiments"], "replicates": raw["replicates"], "provenance": prov,
         "constants": {"carrier": f"{CARRIER}|a", "second": f"{SECOND}|a", "adopted_layout": ADOPTED, "pool_min": POOL_MIN,
                       "small_excess_share": SMALL, "latent_rates": {k: MODELS[k][1] for k in ("latent69", "latent46")},
                       "fit_bar": FIT_BAR, "fit_bar_beside": FIT_BAR_BESIDE, "switch_bound": SWITCH_BOUND, "gate": GATE, "m_L": M_L},
         "instruments": inst,
         "step0": {"rule": "pair (A6.17.11)", "drops": Wp["drops"],
                   "drop_entries": [{k: e[k] for k in ("item_id", "regime", "writer", "populations", "drop_reasons")} for e in Wp["drop_entries"]],
                   "populations": Wp["describe"], "n_comparison": Wp["n_sham"], "n_controls": Wp["n_controls"],
                   "literal": {"drops": Wl["drops"], "populations": {p: d["n"] for p, d in Wl["describe"].items()},
                               "n_comparison": Wl["n_sham"], "n_controls": Wl["n_controls"]}},
         "gates": G, "verdicts": V, "selection": sel, "round2": r2_out,
         "kimi": {k: v for k, v in kj.items() if k not in ("script_sha256", "part2_script_sha256", "inputs_sha256", "version")}}
    Path(a.out_json).write_text(json.dumps(R, indent=1, default=float))
    Path(a.out_md).write_text(render_md(R))


def _p(x, d=2):
    return "—" if x is None else f"{x:.{d}f}"


def render_md(R) -> str:
    S, G, V = R["selection"]["pair"], R["gates"], R["verdicts"]
    sw, b90, b80 = S["switch"], S["bars"][str(FIT_BAR)], S["bars"][str(FIT_BAR_BESIDE)]
    cp = b90["carrying_population"]
    L = []
    cname = {"full": "the full quiet set (the switch does not fire)", "subset": "the resolved-anchor subset",
             "stratum": "the comprehension-quiet stratum", "third": "the third branch (full set descriptive)"}[cp]
    L.append(f"**Switch {'fires' if sw['fires'] else 'does not fire'} (P(holds | margin) {_p(sw['P_holds_margin'])} at the observed share, "
             f"bound {sw['bound']}); the cascade at the 0.90 fit-rate bar selects {cname}"
             + (f", layout {b90['carrying_layout']}" if cp in ("subset", "stratum") else "")
             + f"; at 0.80 it selects {b80['carrying_population']}{' (differs; 0.90 stands)' if R['selection']['pair']['bars_select_differently'] else ''}.**\n")
    pr = R["provenance"]
    L.append(f"Brief 20 Part 3 (brief 15 A6.14.3, A6.17; $0; `work/checks/stage3_b3_power_v3c.py` {pr['report_script'][:12]}…, on Part 2's "
             f"`stage3_b3_power_v3.py` {pr['part2_script'][:12]}… unchanged; simulation, round 2, Kimi join and report from one script and "
             f"inputs: {pr['consistent']}; seed {R['seed']} with stream tag {R['seed_tag']}; {R['experiments']} experiments per cell; "
             f"{R['replicates']} bootstrap replicates). No judge call, no plant, no review view; ids, counts and aggregates only.\n")
    ins = R["instruments"]
    L.append("Part 2's calibration recomputed from its inputs file and seed: m_s reproduced "
             + ", ".join(f"{k} {_p(v['m_s_reproduced'], 4)} (pinned {_p(v['m_s'], 4)}; on the net set the same latent margin reads {_p(v['m_s_net'], 2)})"
                         for k, v in ins.items()) + ". Margins stay pinned at A6.16.1 (v)'s values.\n")
    # step 0
    s0 = R["step0"]
    L.append("## Step 0: brief 26's drops (A6.17.11, the pair rule)\n")
    for e in s0["drop_entries"]:
        where = {"candidate": ", ".join(e["populations"]), "control": "the control arm", "sham": "the comparison arm (floor)"}[e["regime"]]
        why = "; ".join(f"{r['what']}: {r['valid_draws']} valid draws {json.dumps(r['valid_by_day'])}, {'; '.join(r['why'])}"
                        for r in e["drop_reasons"])
        L.append(f"- `{e['item_id'][:12]}…` ({e['regime']}, {e['writer']}; leaves {where}): {why}")
    pops = s0["populations"]
    L.append("\n| population | n (net) | literal n | composition mean | SD | IQR | Sonnet / GLM | document counts | pooled strata |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for p, d in pops.items():
        L.append(f"| {POP_NAME[p]} | {d['n']} | {s0['literal']['populations'][p]} | {_p(d['composition_mean'], 1)} | {_p(d['composition_sd'], 1)} | "
                 f"{_p(d['composition_iqr'][0], 1)} to {_p(d['composition_iqr'][1], 1)} | {d['by_writer']['sonnet55']} / {d['by_writer']['glm53']} | "
                 f"{', '.join(map(str, d['document_counts']))} | {', '.join(map(str, d['strata_pooled']))} |")
    L.append(f"\nComparison arm {s0['n_comparison']} (literal {s0['literal']['n_comparison']}); controls {s0['n_controls']} (literal {s0['literal']['n_controls']}).\n")
    # item 1
    L.append("## 1. The dilution reading (the switch, A6.14.3)\n")
    L.append("| membership truth under the margin | combined P(holds \\| margin) | carrier form (a) P(excluded \\| margin) | combined P(falsified \\| margin) | P(holds \\| 0) |")
    L.append("|---|---|---|---|---|")
    mdesc = {"none": "every item carries the effect (Part 2's undiluted case)", "zero": "non-members at excess zero (the upper bound)",
             "small": f"non-members at {SMALL} of the effect (small excess)", "latent69": f"latent share 0.69: non-members truly quiet w.p. {_p(R['constants']['latent_rates']['latent69'], 3)}",
             "latent46": f"latent share 0.46: w.p. {_p(R['constants']['latent_rates']['latent46'], 3)}"}
    for m in ("zero", "small", "latent69", "latent46", "none"):
        v = V.get(f"pair|{ADOPTED}|full|{m}")
        g = G.get(f"pair|{ADOPTED}|full|{CARRIER}|{m}")
        if v and g:
            L.append(f"| {mdesc[m]} | {_p(v['P_holds_margin'])} | {_p(g['P_excl_margin'])} | {_p(v['P_falsified_margin'])} | {_p(v['P_holds_0'])} |")
    L.append(f"\nThe switch reads the first row: {'**fires**' if sw['fires'] else '**does not fire**'} (bound {SWITCH_BOUND}); "
             f"the carrier alone {'fires' if sw['carrier_alone_fires'] else 'does not fire'} it. Layout {ADOPTED}, worse ICC, 5-point noise.\n")
    # items 2 and 3
    L.append("## 2 and 3. The stratum, the resolved-anchor subset and the strict stratum (A6.13.1 at their n)\n")
    L.append("| population | layout | instrument | P(excl \\| 0) | P(excl \\| margin) | P(LB > 0 \\| 0) | P(present \\| 1.5×) | readable | fit rate | read rate | unpooled: P(excl \\| 0) / P(LB > 0 \\| 0) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for pop in ("stratum", "subset", "strict", "full"):
        for layout in SING_LAYOUTS:
            for inst in INSTS:
                g = G.get(f"pair|{layout}|{pop}|{inst}|none")
                if not g:
                    continue
                npool = G.get(f"pair|{layout}|{pop}|{inst}|none|nopool")
                L.append(f"| {POP_NAME[pop]} ({pops[pop]['n']}) | {layout} | {inst} | {_p(g['P_excl_0'])} | {_p(g['P_excl_margin'])} | {_p(g['P_lb_0'])} | "
                         f"{_p(g['P_present_x1.5'])} | {'yes' if g['readable'] else 'no'} | {_p(g['fit_rate'])} | {_p(g['read_rate'])} | "
                         f"{(_p(npool['P_excl_0']) + ' / ' + _p(npool['P_lb_0'])) if npool else ''} |")
    L.append("\nFit rate: the share of null experiments in which form (a) fits (no constant covariate in the point fit or in more than 2.5 percent "
             "of replicates); read rate: fitted and the floor met (A6.4 (a)); both at the worse ICC. The strict stratum is descriptive (A6.17.1).\n")
    L.append("Combined verdict (A6.13.4, carrier-first) per population at the adopted layout:\n")
    L.append("| population | P(holds \\| 0) | P(falsified \\| 0) | P(LB > 0 \\| 0) | P(holds \\| margin) | P(falsified \\| margin) | P(falsified \\| 1.5×) | second readable |")
    L.append("|---|---|---|---|---|---|---|---|")
    for pop in ("stratum", "subset", "strict"):
        v = V.get(f"pair|{ADOPTED}|{pop}|none")
        if v:
            L.append(f"| {POP_NAME[pop]} | {_p(v['P_holds_0'])} | {_p(v['P_falsified_0'])} | {_p(v['P_lb_0'])} | {_p(v['P_holds_margin'])} | "
                     f"{_p(v['P_falsified_margin'])} | {_p(v['P_falsified_x1.5'])} | {v['second_readable']} |")
    # item 4
    L.append("\n## 4. The branches' operating characteristics (adopted layout, worse ICC)\n")
    vf0 = V[f"pair|{ADOPTED}|full|zero"]
    L.append(f"- **Does not fire (the full set carries):** P(holds | 0) {_p(vf0['P_holds_0'])}, P(holds | margin) {_p(vf0['P_holds_margin'])} "
             f"(zero model; latent 0.69 {_p(V[f'pair|{ADOPTED}|full|latent69']['P_holds_margin'])}), P(LB > 0 | 0) {_p(vf0['P_lb_0'])}, "
             f"P(falsified | 1.5×, zero model) {_p(vf0['P_falsified_x1.5'])}.")
    for pop in ("subset", "stratum"):
        v = V.get(f"pair|{ADOPTED}|{pop}|none")
        L.append(f"- **The stratum branch, {POP_NAME[pop]} carrying:** P(holds | 0) {_p(v['P_holds_0'])}, P(holds | margin) {_p(v['P_holds_margin'])}, "
                 f"P(LB > 0 | 0) {_p(v['P_lb_0'])}, P(falsified | 1.5×) {_p(v['P_falsified_x1.5'])}.")
    L.append(f"- **The third branch (full set descriptive; excluded and attenuated not issued):** a full-set *present* under the null "
             f"P(present | 0) = {_p(vf0['P_falsified_0'])} (false falsification; A6.13.1 (iii)'s bound is 0.10: "
             f"{'within it' if vf0['P_falsified_0'] <= 0.10 else 'outside it'}); its power: P(present | margin) {_p(vf0['P_falsified_margin'])} "
             f"(zero model) and {_p(V[f'pair|{ADOPTED}|full|latent69']['P_falsified_margin'])} (latent 0.69), P(present | 1.5×) "
             f"{_p(vf0['P_falsified_x1.5'])} (zero). Whether a full-set *present* stands is the coordinator's recorded decision (A6.15 (d)).\n")
    # item 5
    L.append("## 5. The selection by the cascade (A6.17.9)\n")
    for bar, b in ((FIT_BAR, b90), (FIT_BAR_BESIDE, b80)):
        L.append(f"- **Bar {bar}:** passing layouts: subset {b['passing_layouts'].get('subset') or 'none'}, stratum {b['passing_layouts'].get('stratum') or 'none'}; "
                 f"steps {' → '.join(b['steps'])}; carrying population **{b['carrying_population']}**, layout {b['carrying_layout']}.")
    L.append("\nThe cascade's joint operating characteristics (step-down on the carrier population's floor or unfit, read on shared worlds at "
             "the carrying layout and at the adopted layout, worse ICC; 'none' marks a layout without the diluted cells, where the third branch's "
             "full-set reading is undiluted):\n")
    L.append("| bar | layout, membership truth | third-branch present | P(excl \\| 0) | P(excl \\| margin) | P(LB > 0 \\| 0) | P(present \\| 0) | P(present \\| 1.5×) | branch shares under the null | under the margin |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for bar, b in ((FIT_BAR, b90), (FIT_BAR_BESIDE, b80)):
        for m, d in b["cascade"].items():
            for ps, c in d.items():
                if not c:
                    continue
                br0 = ", ".join(f"{k} {_p(v)}" for k, v in c["branch_null"].items() if v)
                brm = ", ".join(f"{k} {_p(v)}" for k, v in c["branch_margin"].items() if v)
                L.append(f"| {bar} | {m.replace('|', ', ')} | {ps.replace('_', ' ')} | {_p(c['P_excl_0'])} | {_p(c['P_excl_margin'])} | {_p(c['P_lb_0'])} | "
                         f"{_p(c['P_present_0'])} | {_p(c['P_present_x1.5'])} | {br0} | {brm} |")
    if cp in ("subset", "stratum"):
        L.append(f"\nLayouts for the carrying population ({POP_NAME[cp]}), ranked by P(excluded | 0) + P(present | 1.5×) (A6.13.8); "
                 "live-view singleton units are a pricing matter for S2 and do not enter these readings:\n")
        L.append("| layout | P(excl \\| 0) | P(excl \\| margin) | P(LB > 0 \\| 0) | P(present \\| 1.5×) | score | readable | read rate |")
        L.append("|---|---|---|---|---|---|---|---|")
        for layout in sorted(SING_LAYOUTS, key=lambda l: -(G.get(f"pair|{l}|{cp}|{CARRIER}|none", {}).get("score") or 0)):
            g = G.get(f"pair|{layout}|{cp}|{CARRIER}|none")
            if g:
                L.append(f"| {layout} | {_p(g['P_excl_0'])} | {_p(g['P_excl_margin'])} | {_p(g['P_lb_0'])} | {_p(g['P_present_x1.5'])} | "
                         f"{_p(g['score'])} | {'yes' if g['readable'] else 'no'} | {_p(g['read_rate'])} |")
    # literal
    Sl = R["selection"]["literal"]
    L.append(f"\n**Literal-count sensitivity** ({ADOPTED}; n {', '.join(f'{p} {n}' for p, n in R['step0']['literal']['populations'].items())}): "
             f"switch {'fires' if Sl['switch']['fires'] else 'does not fire'} (P(holds | margin) {_p(Sl['switch']['P_holds_margin'])}); "
             f"at 0.90 the cascade selects {Sl['bars'][str(FIT_BAR)]['carrying_population']}; carrier gates: "
             + "; ".join(f"{p} P(excl|0) {_p(G[f'literal|{ADOPTED}|{p}|{CARRIER}|none']['P_excl_0'])}, P(excl|margin) "
                         f"{_p(G[f'literal|{ADOPTED}|{p}|{CARRIER}|none']['P_excl_margin'])}, readable {G[f'literal|{ADOPTED}|{p}|{CARRIER}|none']['readable']}"
                         for p in ("stratum", "subset") if f"literal|{ADOPTED}|{p}|{CARRIER}|none" in G) + ".\n")
    # item 6
    r2 = R["round2"]
    L.append("## 6. Round 2's size (A6.15 (e), A6.16.3, A6.17.4)\n")
    L.append(f"The primary is the level contrast of mean excess, certified items against quiet-but-illegible items, with **m_L = m_s = {M_L} as a stated "
             f"convention** (an excess difference as large as the one a 25-point composition difference produces at the margin). Items are drawn from the "
             f"net stratum's rows (n {r2['pool']['n']}, composition SD {_p(r2['pool']['composition_sd'], 1)}) under the carrier's DGP at {ADOPTED}; the "
             "model carries no writer or document effect, so matching on writer, document and composition band does not change these readings. "
             f"{r2['experiments']} experiments per n, {r2['replicates']} replicates; n is the smallest grid value from which every larger one meets A6.13.1 at both ICCs.\n")
    L.append("| reading | n per arm (or certified n) |")
    L.append("|---|---|")
    for m, v in r2["level"].items():
        L.append(f"| level contrast at {m} ({_p(M_L if m == 'm_L' else M_L / 2)}) | {v['n'] if v['n'] is not None else 'none on the grid'} |")
    for s, v in r2["slope"].items():
        L.append(f"| slope beside, composition SD {_p(r2['spread_targets_sd'][s], 1)} ({s}) | {v['n'] if v['n'] is not None else 'none on the grid'} |")
    nm = r2["level"]["m_L"]["n"]
    L.append(f"\n**Brief 24's target: {nm if nm is not None else 'not reached on the grid'} certified and {nm if nm is not None else '—'} quiet-but-illegible items** "
             f"(at m_L; {r2['level']['m_L/2']['n'] or 'beyond the grid'} per arm at m_L / 2). The same-shape sham is a floor (A6.4), not a comparison.\n")
    # item 7
    K = R["kimi"]
    L.append("## 7. Kimi K3's routing (A6.17.10 (b); descriptive, membership never recomputed)\n")
    if not K.get("present"):
        L.append("The export is absent; skipped.\n")
    else:
        j = K["join"]
        L.append(f"Fingerprint join on (prompt tokens, completion tokens), shared keys paired in time order: {j['matched']} of {j['records']} cache records "
                 f"matched to {j['generations_used']} of {j['generations']} generations ({j['ambiguous_keys']} shared keys holding {j['ambiguous_records']} records; "
                 f"cost agrees on {j['cost_agrees']}; time-order violations {j['time_order_violations']}).\n")
        for b, d in K["by_brief"].items():
            L.append(f"- {b}: {d['matched']} of {d['records']} matched; providers {json.dumps(d['providers'])}; precision {json.dumps(d['precision'])}.")
        k25 = K["brief25"]
        L.append(f"\nBrief 25 reads by sample and provider: {json.dumps(k25['providers_by_sample'])}.\n")
        L.append("| provider, sample | candidate part reads | mean part score | share credited |")
        L.append("|---|---|---|---|")
        for k, v in k25["part_credit_by_provider_and_sample"].items():
            L.append(f"| {k} | {v['part_reads']} | {_p(v['mean_part_score'])} | {_p(v['share_credited'])} |")
        L.append(f"\nCandidate quiet-status by sample: {json.dumps(k25['candidate_flips'])}; flips by the provider that served a credited part in the "
                 f"non-quiet sample: {json.dumps(k25['flip_credited_part_provider'])}.\n")
    L.append("## Notes\n")
    L.append(f"- The small-excess sensitivity (non-members at {SMALL} of the effect) is this script's choice; the brief names the sensitivity, not its size.")
    L.append("- Stratum populations: form (a) without the document factor, document-stratified bootstrap with documents of fewer than four members pooled "
             "(A6.16.2, A6.17.3); form (b) likewise (Part 2's no-document path); the full set as Part 2 (document factor, payload-clustered bootstrap).")
    L.append("- The step-down reads A6.17.9 (4) as: when the carrier population's carrier reading (form (a) on Opus 4.8's isolated dossier) is at floor or "
             "unfit, the reading moves to the next population; the third branch issues only a full-set present, shown both with and without the recorded "
             "decision letting it stand.")
    L.append(f"- Every membership model was simulated at {ADOPTED}; the other singleton layouts carry the undiluted truths that rank a carrying "
             "population's layouts (its members carry the effect under every model).")
    L.append("- A population passes the cascade when the carrier meets A6.13.1 at its n and its read rate (fitted and floor met) reaches the bar under "
             "the null and under the margin, at the worse ICC.")
    return "\n".join(L) + "\n"


def cmd_report(a):
    report(a)


if __name__ == "__main__":
    raise SystemExit(main())
