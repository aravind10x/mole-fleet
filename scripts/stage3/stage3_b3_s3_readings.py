#!/usr/bin/env python3
"""Brief 33 A2 and B3 (S3, 2026-11-02): the readings script. `work/stage3/b3/plan.md` governs every rule here (sections 4
to 6 and its dated note of 2026-11-02 on judge refusals, errored units, a stopped run and form (b)'s top-two gap
covariate); this script selects every sentence by its rule and fills only the slots of section 6.0. It composes nothing.

Inputs, and only these: the analysis matrix `s3-analysis-matrix-v0.json` (numbers, ids and population names, no item
text) and the scores file `s3-scores-v0.json` (unit id, item id, view, judge, outcome, score, flag; no text). The plan's
constants are transcribed below with their section. `plan.md` is read for section 7's disclosures and the 2026-11-02
note's brief 31 disclosures, copied verbatim, and its sha256 is recorded.

Against Part 3's simulator (`stage3_b3_power_v3c.py`), the plan's rules it implements where the two differ (the
exception table of brief 33 A2; each tested): the replicate failure threshold is more than 10 percent of the 2,000
replicates (section 4.3 (ii)), not 2.5 percent; form (b)'s covariates include the judge's top-two singleton gap (the
note); the floor is computed once, on the full quiet set against the sham (section 4.3), not per population; 2,000
replicates at seed 20261152, not 1,000; the Q1-against-Q3 sensitivity uses the full net set's fixed quartiles 47.5 and
66.5 for every population (A6.20 D7); the cascade is section 5.5's seven ordered steps; a singular (rank-deficient)
design is a fit failure (section 4.3 (i)), checked explicitly, since the simulator's fitters ridge through one.

The analysis lock (brief 33 A2): the script refuses to run unless the scores file holds every one of the 4,344 units of
section 2.6 and the note (every row scored, refused or errored), or a `stopped` record names the rows that are missing,
in which case it runs over the complete rows only under the note's rule (d).

Counts and dollars are never printed here; this script prints sentence ids, counts and the numbers the sentences carry.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s3_readings.py --matrix ... --scores ... --out-dir ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_power_v3 as pv  # noqa: E402  (numerical primitives only: irls, sigmoid, bootstrap_weights, top_two_gap; no rule)

VERSION = "b3-s3-readings/v0"
PROJECT = HERE.parents[1]
PLAN = "work/stage3/b3/plan.md"

# ── the plan's constants, by section ──────────────────────────────────────────────────────────────
BOOT_SEED, REPLICATES = 20261152, 2000          # section 3; section 4.2
FAIL_SHARE = 0.10                               # section 4.3 (ii): more than 10 % of the replicates fail
MARGIN_B = 0.3                                  # section 4.1: form (b)'s margin
Q1, Q3 = 47.5, 66.5                             # A6.20 D7: the full net set's quartiles (section 1.2)
MARGIN_Q = MARGIN_B * (Q3 - Q1) / 25            # S-L: 0.228
HI_C, LO_C = 75.0, 50.0                         # section 4.2: the 75-minus-50 span
CEILING = 0.85                                  # section 4.3; A6.13.5
LOSS_SHARE = 0.10                               # the note (c): a loss above 10 percent of a population's n
G1_BAR = 0.65                                   # section 4.4; brief 22
SQ_BAR = 0.65                                   # S-Q: P4's bar
REL_PARTIAL, REL_SB = 0.846, 0.915              # S-G: A6.5 (ii), A6.13.5
POOL_MIN = 4                                    # A6.17.3
M_S = {"C": 18.22, "S": 19.37, "d1": 19.07, "d2": 22.47}                      # section 4.1
BIAS_B = {"C": 0.040, "S": 0.036, "d1": 0.050, "d2": 0.045, "d3": -0.004, "d4": 0.006}   # section 4.1; section 5.4
INSTRUMENTS = {"C": ("P_author_doc_iso", "opus48"), "S": ("P_author", "opus48"), "d1": ("P_author_doc_iso", "sonnet"),
               "d2": ("P_author", "sonnet"), "d3": ("P_author_doc_live", "opus48"), "d4": ("P_author_doc_live", "sonnet")}
NAMED = ("C", "S")
D_ROWS = ("d1", "d2", "d3", "d4")
LIVE = ("d3", "d4")
O_JUDGES = ("sonnet", "opus48", "sol")
JUDGE_NAME = {"sonnet": "Sonnet 5", "opus48": "Opus 4.8", "sol": "GPT-6 Sol"}
VIEW_NAME = {"P_author_doc_iso": "`P_author_doc` isolated", "P_author_doc_live": "`P_author_doc` live", "P_author": "`P_author` zero-context",
             "O_diff": "`O_diff`"}
INSTRUMENT_NAME = {"C": "the carrier, form (a) on Opus 4.8's isolated dossier",
                   "S": "the second named instrument, form (a) on Opus 4.8's zero-context `P_author`",
                   "S_fallback": "the second named instrument as the fallback carrier",
                   "d1": "`P_author_doc` isolated, Sonnet 5", "d2": "`P_author` zero-context, Sonnet 5",
                   "d3": "`P_author_doc` live, Opus 4.8", "d4": "`P_author_doc` live, Sonnet 5"}
POP_NAME = {"subset": "the resolved-anchor subset", "stratum": "the comprehension-quiet stratum", "strict": "the strict two-family stratum",
            "subset_and_strict": "subset ∩ strict", "full": "the full quiet set", "certified": "the certified stratum"}
READ_POPS = ("subset", "stratum", "full")                 # section 5.2: the carrier population, beside, descriptive
DESC_POPS = ("strict", "subset_and_strict")               # S-M1
STRATUM_POPS = ("stratum", "subset", "strict", "subset_and_strict", "certified", "preview_credited", "preview_illegible", "unresolved_stratum")
# section 2.6 and the note: the units per row
EXPECTED = {("P_author_doc_iso", "opus48"): (232, 564), ("P_author", "opus48"): (232, 564), ("P_author_doc_iso", "sonnet"): (232, 564),
            ("P_author", "sonnet"): (232, 564), ("P_author_doc_live", "opus48"): (232, 0), ("P_author_doc_live", "sonnet"): (232, 0),
            ("O_diff", "sonnet"): (232, 0), ("O_diff", "opus48"): (232, 0), ("O_diff", "sol"): (232, 0)}
TOTAL_UNITS = 4344
LABELS = ("present", "attenuated", "excluded", "inconclusive")
TWO_STEP = {("excluded", "present"), ("present", "excluded")}
PMAX = {"excluded": "holds", "present": "falsified", "attenuated": "partly missed", "inconclusive": "inconclusive"}
CLAUSE_E = ("Measurement error, both directions: composition noise attenuates the contrast toward *excluded* (the disattenuated reading "
            "beside); the singleton maximum's max-of-three inflation leans form (a) toward *present* and form (b)'s singleton covariate "
            "toward *present* (A6.13.5), carried by the top-two gap covariate, the singleton placement rule and, for (b), the subtracted null bias.")
A618L = ("Under a true max-type null the carrier reads *holds* about two times in three (0.67), so a non-*holds* reading in round 1 is weak "
         "evidence and round 2 is the test (A6.18 (l)).")


def fmt(x: float | None, d: int = 2) -> str:
    return "n/a" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{d}f}"


def interval(lo: float | None, hi: float | None, d: int = 2) -> str:
    return f"[{fmt(lo, d)}, {fmt(hi, d)}]"


def four_outcome(lo: float, hi: float, point: float, margin: float) -> str:
    """Section 5.3's table: exactly one label."""
    if lo > 0 and point >= margin:
        return "present"
    if lo > 0 and point < margin:
        return "attenuated"
    if lo <= 0 and hi < margin:
        return "excluded"
    return "inconclusive"


def ids_sha256(ids) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


# ── the scores file: the lock and the per-item units ─────────────────────────────────────────────

def load_json(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def analysis_lock(scores: Mapping[str, Any]) -> dict[str, Any]:
    """Every unit of section 2.6 and the note present (4,344 rows: scored, refused or errored), or a `stopped` record
    naming the incomplete rows (cells), which then carry no reading. Returns the complete cells and the stop record."""
    rows = scores["rows"]
    by_cell: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for r in rows:
        by_cell[(r["view"], r["judge"])][r["arm"]] += 1
    stopped = scores.get("stopped")
    incomplete: dict[str, dict] = {}
    for cell, (n_item, n_line) in EXPECTED.items():
        got = by_cell.get(cell, Counter())
        if got.get("item", 0) != n_item or got.get("line", 0) != n_line:
            incomplete["|".join(cell)] = {"scored_rows": got.get("item", 0) + got.get("line", 0), "of": n_item + n_line}
    if incomplete and not stopped:
        raise SystemExit(f"analysis lock: the scores file holds {len(rows)} of {TOTAL_UNITS} units and no `stopped` record names the missing rows: "
                         + "; ".join(f"{k} {v['scored_rows']} of {v['of']}" for k, v in incomplete.items()))
    if stopped:
        named = set((stopped.get("incomplete_rows") or {}).keys())
        if set(incomplete) - named:
            raise SystemExit(f"analysis lock: the `stopped` record does not name every incomplete row: {sorted(set(incomplete) - named)}")
    complete = ["|".join(c) for c in EXPECTED if "|".join(c) not in incomplete]
    return {"rows": len(rows), "expected_rows": TOTAL_UNITS, "stopped": stopped, "incomplete": incomplete, "complete_cells": complete}


def cell_items(rows: Sequence[Mapping[str, Any]], view: str, judge: str) -> dict[str, dict]:
    """{item id: {"tri": [[score, flag, outcome] x placements], "lines": {role: [[score, outcome] x placements]}}} for one cell."""
    out: dict[str, dict] = {}
    for r in rows:
        if r["view"] != view or r["judge"] != judge:
            continue
        it = out.setdefault(r["item_id"], {"regime": r["regime"], "tri": {}, "lines": defaultdict(dict)})
        sc = r.get("score")
        sc = float(sc) if (r["outcome"] == "scored" and sc is not None) else None
        if r["arm"] == "item":
            it["tri"][int(r["placement"])] = {"score": sc, "flag": bool(r.get("flag")) if sc is not None else None,
                                              "flag_unit": bool(r.get("flag_unit", r.get("flag"))) if sc is not None else None, "outcome": r["outcome"]}
        else:
            it["lines"][int(r["role"])][int(r["placement"])] = {"score": sc, "outcome": r["outcome"]}
    return out


def item_summary(it: Mapping[str, Any], need_lines: bool) -> dict[str, Any]:
    """Mean application score, the two flags, the three lines' means, the judge's singleton maximum and top-two gap, and
    whether every component is scored (the note's rule (a))."""
    tri = [it["tri"].get(p) for p in (1, 2)]
    tri_ok = all(t is not None and t["score"] is not None for t in tri)
    lines = {}
    lines_ok = True
    for role in (1, 2, 3):
        ps = [it["lines"].get(role, {}).get(p) for p in (1, 2)]
        if all(x is not None and x["score"] is not None for x in ps):
            lines[role] = float(np.mean([x["score"] for x in ps]))
        else:
            lines_ok = False
    out = {"tri_scores": [t["score"] if t else None for t in tri], "tri_flags": [t["flag"] if t else None for t in tri],
           "tri_flags_unit": [t["flag_unit"] if t else None for t in tri],
           "tri_ok": tri_ok, "n_tri_scored": sum(1 for t in tri if t is not None and t["score"] is not None),
           "lines": lines, "lines_ok": lines_ok}
    if tri_ok:
        out["tri_mean"] = float(np.mean(out["tri_scores"]))
    if tri_ok and lines_ok:
        lm = [lines[r] for r in (1, 2, 3)]
        out["line_max"] = max(lm)
        s = sorted(lm)
        out["gap"] = s[-1] - s[-2]
        out["excess"] = out["tri_mean"] - out["line_max"]
    out["evaluable"] = tri_ok and (lines_ok or not need_lines)
    return out


# ── fits ──────────────────────────────────────────────────────────────────────────────────────────

def _rank_ok(X: np.ndarray, w: np.ndarray | None = None) -> np.ndarray | bool:
    """Full column rank of the design, or of the weighted design per replicate (rows with weight zero vanish)."""
    k = X.shape[1]
    if w is None:
        return bool(np.linalg.matrix_rank(X) == k)
    Xw = np.sqrt(w)[:, :, None] * X[None]
    return np.linalg.matrix_rank(Xw) == k


def pooled_codes(doc: np.ndarray, pool_min: int = POOL_MIN) -> np.ndarray:
    """A6.17.3 on a document index array: documents with fewer than pool_min members pool into one stratum (code -1)."""
    c = Counter(doc.tolist())
    s = np.array([d if c[d] >= pool_min else -1 for d in doc.tolist()])
    return np.unique(s, return_inverse=True)[1]


def weights_for(rng: np.random.Generator, n: int, strata: np.ndarray | None) -> np.ndarray:
    return pv.bootstrap_weights(rng, n, REPLICATES, strata)


def ols(X: np.ndarray, y: np.ndarray, wt: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, bool]:
    """Point OLS and the weighted bootstrap fits; (beta, bb, ok mask, point rank ok)."""
    pok = _rank_ok(X)
    beta = np.linalg.lstsq(X, y, rcond=None)[0] if pok else np.full(X.shape[1], np.nan)
    ok = _rank_ok(X, wt)
    XtWX = np.matmul((wt[:, :, None] * X[None]).transpose(0, 2, 1), X)
    XtWy = (wt * y[None]) @ X
    bb = np.full((wt.shape[0], X.shape[1]), np.nan)
    if ok.any():
        bb[ok] = np.linalg.solve(XtWX[ok], XtWy[ok][..., None])[..., 0]
    return beta, bb, ok, pok


def fit_failure(point_ok: bool, ok: np.ndarray, empty_stratum: str | None) -> str | None:
    """Section 4.3 (i) to (iii) as one closed reason, or None when the fit stands."""
    if empty_stratum is not None:
        return f"pooled stratum {empty_stratum} is empty"
    if not point_ok:
        return "the design is singular"
    k = int((~ok).sum())
    if k > FAIL_SHARE * len(ok):
        return f"{k} of 2,000 replicates failed"
    return None


def verdict(point: float, draws: np.ndarray, margin: float) -> dict[str, Any]:
    lo, hi = (float(x) for x in np.percentile(draws, [2.5, 97.5]))
    return {"point": float(point), "lo": lo, "hi": hi, "margin": margin, "label": four_outcome(lo, hi, point, margin)}


def form_a(C, gap, sonnet, edit, doc, excess, m_s, strata, with_doc, rng, extra=None) -> dict[str, Any]:
    """Section 4.2 form (a): OLS of excess on composition, the top-two singleton gap, writer, replace share and, on the
    full set, the document factor; contrast 25 x the composition coefficient against m_s; the disattenuated reading
    beside (S-G). `extra` adds named columns (S-K's D_part and its interaction)."""
    n = len(C)
    cols = [np.ones(n), C, gap, sonnet, edit]
    names = ["intercept", "composition", "gap", "sonnet", "edit"]
    if extra:
        for k, v in extra.items():
            cols.append(v)
            names.append(k)
    if with_doc:
        d = np.eye(int(doc.max()) + 1)[doc][:, 1:]
        cols.append(d)
        names += [f"doc{j}" for j in range(1, d.shape[1] + 1)]
    X = np.column_stack(cols)
    wt = weights_for(rng, n, strata)
    beta, bb, ok, pok = ols(X, excess, wt)
    out: dict[str, Any] = {"form": "a", "n": n, "with_doc": bool(with_doc), "strata": "document-stratified" if strata is not None else "payload-clustered",
                           "point_ok": bool(pok), "failed_replicates": int((~ok).sum()), "names": names}
    reason = fit_failure(pok, ok, None)
    out["reason"] = reason
    out["fit_ok"] = reason is None
    if reason:
        return out
    okb = bb[ok]
    j = names.index("composition")
    out["contrast"] = verdict(beta[j] * 25, okb[:, j] * 25, m_s)
    out["disattenuated"] = verdict(beta[j] * 25 / REL_PARTIAL, okb[:, j] * 25 / REL_PARTIAL, m_s)
    out["disattenuated_sb"] = verdict(beta[j] * 25 / REL_SB, okb[:, j] * 25 / REL_SB, m_s)
    out["coefficients"] = {nm: float(beta[i]) for i, nm in enumerate(names)}
    if extra:
        for k in extra:
            i = names.index(k)
            out[f"coef_{k}"] = verdict(beta[i] * 25, okb[:, i] * 25, m_s)
    return out


def form_b(C, line, gap, sonnet, edit, doc, F, strata, with_doc, rng, bias, indicator=None) -> dict[str, Any]:
    """Section 4.2 form (b) with the note: Firth logistic regression of each item application's flag on composition, the
    judge's continuous singleton maximum, the top-two gap, writer, replace share and, on the full set, the document
    factor; contrast (b) at 75 against 50 with the continuous covariates at their sample means and the writer at the
    share-weighted pooled level (O2); O4 beside; the Q1-against-Q3 contrast (S-L); the disattenuated reading (S-G); the
    bias-net lower bound (section 5.4). `indicator` adds S-O2's coordinated-form column."""
    n, P = F.shape
    cont = np.column_stack([C, line, gap, edit])
    mu, sd = cont.mean(0), cont.std(0)
    sd = np.where(sd == 0, 1.0, sd)
    Zc = (cont - mu) / sd
    cols = [np.ones(n), Zc[:, 0], Zc[:, 1], Zc[:, 2], sonnet, Zc[:, 3]]
    names = ["intercept", "composition", "line", "gap", "sonnet", "edit"]
    if indicator is not None:
        cols.append(indicator)
        names.append("indicator")
    if with_doc:
        d = np.eye(int(doc.max()) + 1)[doc][:, 1:]
        cols.append(d)
        names += [f"doc{j}" for j in range(1, d.shape[1] + 1)]
    X1 = np.column_stack(cols)
    X = np.repeat(X1, P, axis=0)
    y = F.ravel().astype(float)
    pok = _rank_ok(X1)
    out: dict[str, Any] = {"form": "b", "n": n, "placements": P, "with_doc": bool(with_doc),
                           "strata": "document-stratified" if strata is not None else "payload-clustered", "point_ok": bool(pok), "names": names}
    if not pok:
        out.update({"reason": "the design is singular", "fit_ok": False, "failed_replicates": None})
        return out
    b0, c0 = pv.irls(X, y, np.ones((1, n * P)), firth=True)
    wt = weights_for(rng, n, strata)
    ok_rank = _rank_ok(X1, wt)
    bb, cb = pv.irls(X, y, np.repeat(wt, P, axis=1), beta0=b0[0], firth=True)
    ok = cb & ok_rank
    out["failed_replicates"] = int((~ok).sum())
    out["point_converged"] = bool(c0[0])
    reason = "the point fit did not converge" if not c0[0] else fit_failure(True, ok, None)
    out["reason"] = reason
    out["fit_ok"] = reason is None
    if reason:
        return out
    bbc = bb[ok]
    jC, jL = names.index("composition"), names.index("line")
    lc = np.linalg.lstsq(np.column_stack([np.ones(n), C]), line, rcond=None)[0]   # O4: the line covariate's conditional mean given C

    def predict(beta, c, cond=False, ind=None):
        Xe = X1.copy()
        Xe[:, jC] = (c - mu[0]) / sd[0]
        Xe[:, jL] = ((np.array([1.0, c]) @ lc) - mu[1]) / sd[1] if cond else 0.0
        Xe[:, names.index("gap")] = 0.0
        Xe[:, names.index("edit")] = 0.0
        if ind is not None:
            Xe[:, names.index("indicator")] = ind
        return pv.sigmoid(beta @ Xe.T).mean(-1)

    def contrast(beta, hi, lo, cond=False):
        return predict(beta, hi, cond) - predict(beta, lo, cond)

    def disatt(beta):
        d = beta.copy()
        d[..., jC] = d[..., jC] / REL_PARTIAL
        return d

    out["contrast"] = verdict(float(contrast(b0, HI_C, LO_C)[0]), contrast(bbc, HI_C, LO_C), MARGIN_B)
    out["contrast"]["bias"] = bias
    out["contrast"]["lo_net_of_bias"] = out["contrast"]["lo"] - bias
    out["o4"] = verdict(float(contrast(b0, HI_C, LO_C, True)[0]), contrast(bbc, HI_C, LO_C, True), MARGIN_B)
    out["q1q3"] = verdict(float(contrast(b0, Q3, Q1)[0]), contrast(bbc, Q3, Q1), MARGIN_Q)
    out["disattenuated"] = verdict(float(contrast(disatt(b0), HI_C, LO_C)[0]), contrast(disatt(bbc), HI_C, LO_C), MARGIN_B)
    out["coefficients"] = {nm: float(b0[0][i]) for i, nm in enumerate(names)}
    if indicator is not None:
        cm = float(C.mean())
        out["form_contrast"] = verdict(float((predict(b0, cm, ind=1.0) - predict(b0, cm, ind=0.0))[0]),
                                       predict(bbc, cm, ind=1.0) - predict(bbc, cm, ind=0.0), MARGIN_B)
    return out


def clustered_mean(rng, v: np.ndarray, strata=None) -> dict[str, Any]:
    """The mean of an item-level quantity (or of its applications, v (n, P)) with a clustered or stratified percentile
    interval over items. A NaN application is unscored and leaves the denominator (the note's rule (b)); an item with
    no scored application leaves too."""
    v = np.asarray(v, float)
    if v.ndim == 1:
        v = v[:, None]
    valid = ~np.isnan(v)
    keep = valid.any(1)
    v, valid = v[keep], valid[keep]
    n = len(v)
    wt = weights_for(rng, n, strata[keep] if strata is not None else None)
    m = (wt @ np.nansum(v, 1)) / np.maximum(wt @ valid.sum(1), 1e-12)
    lo, hi = (float(x) for x in np.percentile(m, [2.5, 97.5]))
    vals = v[valid]
    return {"point": float(vals.mean()), "lo": lo, "hi": hi, "n": n, "k": int(vals.sum()) if np.all(np.isin(vals, (0, 1))) else None,
            "applications": int(valid.sum()), "unscored_applications": int((~valid).sum())}


def clopper_pearson(k: int, n: int) -> list[float]:
    lo = 0.0 if k == 0 else float(stats.beta.ppf(0.025, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(0.975, k + 1, n - k))
    return [lo, hi]


def auroc_clustered(rng, a: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    """AUROC of a (n_a, P) against b (n_b, P) application scores with a bootstrap clustered on both sets' items. A NaN
    application is unscored and leaves (the note's rule (b)); an item with none scored leaves too."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[~np.isnan(a).all(1)], b[~np.isnan(b).all(1)]
    va, vb = ~np.isnan(a), ~np.isnan(b)
    ia, ib = np.repeat(np.arange(len(a)), a.shape[1])[va.ravel()], np.repeat(np.arange(len(b)), b.shape[1])[vb.ravel()]
    M = pv.auroc_matrix(a[va], b[vb])
    wa, wb = weights_for(rng, len(a), None), weights_for(rng, len(b), None)
    Wa, Wb = wa[:, ia], wb[:, ib]
    au = ((Wa @ M) * Wb).sum(1) / (Wa.sum(1) * Wb.sum(1))
    lo, hi = (float(x) for x in np.percentile(au, [2.5, 97.5]))
    return {"point": float(M.mean()), "lo": lo, "hi": hi, "n_a": len(a), "n_b": len(b), "applications_a": int(va.sum()), "applications_b": int(vb.sum())}


# ── one instrument ────────────────────────────────────────────────────────────────────────────────

class Instrument:
    """One per-agent row: its evaluable items, the arrays the fits read, and the readings per population."""

    def __init__(self, key: str, matrix: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], complete: bool):
        self.key = key
        self.view, self.judge = INSTRUMENTS[key]
        self.live = key in LIVE
        self.m_s = M_S.get(key)
        self.bias = BIAS_B[key]
        self.matrix = matrix
        self.complete = complete
        self.items = cell_items(rows, self.view, self.judge) if complete else {}
        need = not self.live
        self.summary = {i: item_summary(it, need) for i, it in self.items.items()}
        self.lead = False

    # populations ---------------------------------------------------------------------------------
    def pop_ids(self, pop: str) -> list[str]:
        return list(self.matrix["populations"][pop]["ids"])

    def evaluable_ids(self, pop: str) -> list[str]:
        return [i for i in self.pop_ids(pop) if i in self.summary and self.summary[i]["evaluable"]]

    def loss(self, pop: str) -> dict[str, Any]:
        ids = self.pop_ids(pop)
        ev = self.evaluable_ids(pop)
        return {"n": len(ids), "evaluable": len(ev), "lost": len(ids) - len(ev), "provisional": (len(ids) - len(ev)) > LOSS_SHARE * len(ids)}

    def arrays(self, ids: Sequence[str], pop: str) -> dict[str, Any]:
        M = self.matrix["items"]
        S = self.summary
        docs = sorted({M[i]["document"] for i in self.matrix["populations"][pop]["ids"]})
        doc = np.array([docs.index(M[i]["document"]) for i in ids])
        strata = None
        empty = None
        if pop in STRATUM_POPS:
            ps = self.matrix["pooled_strata"][pop]
            codes = sorted(set(ps.values()))
            strata = np.array([codes.index(ps[M[i]["document"]]) for i in ids])
            present = set(strata.tolist())
            missing = [c for j, c in enumerate(codes) if j not in present]
            if missing:
                empty = missing[0]
        return {"C": np.array([M[i]["composition"] for i in ids], float),
                "sonnet": np.array([M[i]["writer"] == "sonnet55" for i in ids], float),
                "edit": np.array([M[i]["replace_share"] for i in ids], float),
                "doc": doc, "n_docs": len(docs), "strata": strata, "empty_stratum": empty,
                # a live row has no lone-line units (A6.13.8): form (b) at T2 without singletons takes the rater's section-2
                # maximum and top-two gap as its line covariates, as Part 2's T2 layout did; form (a) is never read on it
                "excess": np.array([S[i].get("excess", np.nan) for i in ids], float) if not self.live else None,
                "gap": np.array([S[i].get("gap", np.nan) for i in ids], float) if not self.live else np.array([M[i]["top_two_gap"] for i in ids], float),
                "line": np.array([S[i].get("line_max", np.nan) for i in ids], float) if not self.live else np.array([M[i]["line_max"] for i in ids], float),
                "tri": np.array([S[i]["tri_scores"] for i in ids], float),
                "F": np.array([S[i]["tri_flags"] for i in ids], float),
                "F_unit": np.array([S[i]["tri_flags_unit"] for i in ids], float),
                "kimi": np.array([M[i]["readers"]["kimi"]["D_part_mean"] for i in ids], float),
                "sol": np.array([M[i]["readers"]["sol"]["D_part_mean"] for i in ids], float)}

    def rng(self, tag: str) -> np.random.Generator:
        """One seeded stream per reading, so every reading is reproducible on its own (seed 20261152 keyed by the reading)."""
        h = int.from_bytes(hashlib.sha256(f"{self.key}|{tag}".encode()).digest()[:4], "big")
        return np.random.default_rng([BOOT_SEED, h])

    # floor, ceiling ------------------------------------------------------------------------------
    def floor(self, sham: Mapping[str, dict]) -> dict[str, Any]:
        """Section 4.3: once, on the full quiet set's evaluable items against the sham's scored applications."""
        ids = self.evaluable_ids("full")
        A = self.arrays(ids, "full")
        sh = [s for s in sham.values() if s["n_tri_scored"] > 0]          # the note's rule (b): an unscored application leaves, not its item
        nan = float("nan")
        tri_sh = np.array([[x if x is not None else nan for x in s["tri_scores"]] for s in sh], float)
        F_sh = np.array([[x if x is not None else nan for x in s["tri_flags"]] for s in sh], float)
        F_sh_u = np.array([[x if x is not None else nan for x in s["tri_flags_unit"]] for s in sh], float)
        out: dict[str, Any] = {"n_quiet": len(ids), "n_sham": len(sh), "sham_applications_scored": int((~np.isnan(tri_sh)).sum()) if len(sh) else 0}
        if not self.live:
            au = auroc_clustered(self.rng("floor_a"), A["tri"], tri_sh)
            out["a"] = {**au, "pass": au["lo"] > 0.5}
        rq, rs = clustered_mean(self.rng("floor_b_q"), A["F"]), clustered_mean(self.rng("floor_b_s"), F_sh)
        kq, nq = int(A["F"].sum()), A["F"].size
        ks, ns = rs["k"], rs["applications"]
        out["b"] = {"quiet": rq, "sham": rs, "pass": rq["lo"] > rs["hi"], "cp_quiet": clopper_pearson(kq, nq), "cp_sham": clopper_pearson(ks, ns),
                    "cp_pass": clopper_pearson(kq, nq)[0] > clopper_pearson(ks, ns)[1], "flag": "the sealed author-level reading (union)"}
        rqu, rsu = clustered_mean(self.rng("floor_b_q_unit"), A["F_unit"]), clustered_mean(self.rng("floor_b_s_unit"), F_sh_u)
        out["b_unit"] = {"quiet": rqu, "sham": rsu, "pass": rqu["lo"] > rsu["hi"], "flag": "the planted unit's own flag, beside"}
        return out

    # readings ------------------------------------------------------------------------------------
    def read(self, pop: str, floor_a_pass: bool, floor_b_pass: bool, extra_a: Mapping[str, np.ndarray] | None = None,
             ids: Sequence[str] | None = None) -> dict[str, Any]:
        """Form (a) and form (b) on one population: the full set under section 4.3's order (document factor, then without
        it under the document-stratified bootstrap), a stratum population without the document factor under the pooled
        strata; the precedence floor, then the ceiling (form (b)), then fit (section 4.3). An instrument at floor (a) is
        not read: both forms carry `not_read` "floor" and no label (G3). `ids` restricts the items (G6's clean set)."""
        ids = list(ids) if ids is not None else self.evaluable_ids(pop)
        out: dict[str, Any] = {"population": pop, "loss": self.loss(pop), "ids_sha256": ids_sha256(ids), "n": len(ids)}
        if not floor_a_pass and not self.live:
            out["a"] = {"fit_ok": False, "not_read": "floor", "n": len(ids)}
            out["b"] = {"fit_ok": False, "not_read": "floor", "n": len(ids)}
            out["recall"] = None
            return out
        A = self.arrays(ids, pop) if ids else None
        if ids:
            rq = clustered_mean(self.rng(f"recall|{pop}"), A["F"], A["strata"])
            out["recall"] = rq
            out["recall_unit"] = clustered_mean(self.rng(f"recall_unit|{pop}"), A["F_unit"], A["strata"])
            out["ceiling"] = rq["point"] > CEILING
        else:
            out["recall"], out["recall_unit"], out["ceiling"] = None, None, False
        fit_reason = None
        if len(ids) < 4:
            fit_reason = "the design is singular"
        elif A["empty_stratum"] is not None:
            fit_reason = f"pooled stratum {A['empty_stratum']} is empty"
        if not self.live:
            out["a"] = {"fit_ok": False, "reason": fit_reason, "n": len(ids)} if fit_reason else self._fit_order(pop, A, "a", extra_a)
        if floor_b_pass is False:
            out["b"] = {"fit_ok": False, "not_read": "floor", "n": len(ids)}
        elif out["ceiling"]:
            out["b"] = {"fit_ok": False, "not_read": "ceiling", "n": len(ids), "recall": out["recall"]["point"]}
        elif fit_reason:
            out["b"] = {"fit_ok": False, "reason": fit_reason, "n": len(ids)}
        else:
            out["b"] = self._fit_order(pop, A, "b", None)
        return out

    def _fit_order(self, pop: str, A: Mapping[str, Any], form: str, extra) -> dict[str, Any]:
        full = pop == "full"
        attempts = []
        if full:
            orders = [(True, None), (False, pooled_codes(A["doc"]))]   # section 4.3: without the document factor, documents under four members pooled
        else:
            orders = [(False, A["strata"])]
        for with_doc, strata in orders:
            tag = f"{form}|{pop}|{'doc' if with_doc else 'nodoc'}"
            if form == "a":
                r = form_a(A["C"], A["gap"], A["sonnet"], A["edit"], A["doc"], A["excess"], self.m_s, strata, with_doc, self.rng(tag), extra)
            else:
                r = form_b(A["C"], A["line"], A["gap"], A["sonnet"], A["edit"], A["doc"], A["F"], strata, with_doc, self.rng(tag), self.bias)
            attempts.append({"with_doc": with_doc, "fit_ok": r["fit_ok"], "reason": r.get("reason")})
            if r["fit_ok"]:
                r["attempts"] = attempts
                return r
        r["attempts"] = attempts
        return r


# ── labels, the cascade and the composed view ─────────────────────────────────────────────────────

def instrument_label(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    """Section 5.4 (1): form (a)'s label, changed only by a two-step conflict with form (b), which counts as present or
    attenuated only when its bias-net lower bound is above 0 and as excluded by the table alone."""
    la = a["contrast"]["label"] if a.get("fit_ok") else None
    if not b.get("fit_ok"):
        return {"label": la, "a": la, "b": None, "b_effective": None, "conflict": False, "b_not_read": b.get("not_read", "unfit")}
    lb = b["contrast"]["label"]
    eff = lb if (lb == "excluded" or (lb in ("present", "attenuated") and b["contrast"]["lo_net_of_bias"] > 0)) else None
    conflict = la is not None and (la, eff) in TWO_STEP
    return {"label": "inconclusive" if conflict else la, "a": la, "b": lb, "b_effective": eff, "conflict": conflict,
            "b_counts": eff is not None, "b_lo_net": b["contrast"]["lo_net_of_bias"]}


def cascade(inst: Mapping[str, Instrument], floors: Mapping[str, dict], readings: Mapping[str, Mapping[str, dict]]) -> dict[str, Any]:
    """Section 5.5 as one ordered list of seven steps, every step reported with its reason. `readings[key][pop]`."""
    fa = {k: (inst[k].complete and floors[k]["a"]["pass"]) for k in NAMED}
    steps: list[dict] = []
    out: dict[str, Any] = {"floor_a": fa, "steps": steps, "lead": None, "fallback": False, "state": None}
    if fa["C"]:
        lead = "C"
    elif fa["S"]:
        lead, out["fallback"] = "S", True
    else:
        out.update(state="no_verdict", sentence="S-A3", lead=None)
        return out
    out["lead"] = lead

    def fits(k, pop):
        r = readings[k][pop]["a"]
        return bool(r.get("fit_ok")), r.get("reason")

    # steps 1 and 2 with the lead
    for step, pop in ((1, "subset"), (2, "stratum")):
        ok, reason = fits(lead, pop)
        steps.append({"step": step, "population": pop, "instrument": lead, "fallback": out["fallback"], "fit": ok, "reason": reason})
        if ok:
            out.update(state="read", step=step, population=pop, instrument=lead)
            return out
        if step == 1:
            steps[-1]["sentence"] = "S-C1"
    # the stratum failed too
    if lead == "C" and fa["S"]:
        steps[-1]["sentence"] = "S-C3"
        out["fallback"] = True
        for step, pop in ((3, "subset"), (4, "stratum")):
            ok, reason = fits("S", pop)
            steps.append({"step": step, "population": pop, "instrument": "S", "fallback": True, "fit": ok, "reason": reason})
            if ok:
                out.update(state="read", step=step, population=pop, instrument="S", lead="S")
                return out
            steps[-1]["sentence"] = "S-C1" if step == 3 else "S-C2"
        lead = "S"
        out["lead"] = "S"
    else:
        steps[-1]["sentence"] = "S-C2"
    # step 5: the third branch with the current lead
    ok, reason = fits(lead, "full")
    steps.append({"step": 5, "population": "full", "instrument": lead, "fallback": out["fallback"], "fit": ok, "reason": reason})
    if ok:
        out.update(state="third", step=5, population="full", instrument=lead)
        return out
    other = "S" if lead == "C" else "C"
    if fa[other]:
        steps[-1]["sentence"] = "S-C3b"
        ok, reason = fits(other, "full")
        steps.append({"step": 6, "population": "full", "instrument": other, "fallback": other == "S", "fit": ok, "reason": reason})
        if ok:
            out.update(state="third", step=6, population="full", instrument=other, lead=other, fallback=other == "S")
            return out
    steps.append({"step": 7, "population": None, "instrument": None, "fit": False, "reason": None, "sentence": "S-C4"})
    out.update(state="no_verdict", sentence="S-C4")
    return out


def composed(rows: Sequence[Mapping[str, Any]], matrix: Mapping[str, Any], judge: str, per_agent: Mapping[str, Instrument], rng_tag: str) -> dict[str, Any]:
    """Section 4.4: the composed share of flagged item applications per population (clustered on items), and the gap over
    each named per-agent instrument on the same applications (paired bootstrap over items)."""
    items = cell_items(rows, "O_diff", judge)
    summ = {i: item_summary(it, False) for i, it in items.items()}
    rng = np.random.default_rng([BOOT_SEED, int.from_bytes(hashlib.sha256(rng_tag.encode()).digest()[:4], "big")])
    out: dict[str, Any] = {"judge": judge}
    pops = ["full", "controls", "sham"] + (["stratum"] if judge != "sol" else [])
    for pop in pops:
        ids = [i for i in matrix["populations"][pop]["ids"] if i in summ]
        apps = [(i, p) for i in ids for p in (0, 1) if summ[i]["tri_scores"][p] is not None]
        if not apps:
            out[pop] = None
            continue
        F = np.array([[summ[i]["tri_flags"][p] if summ[i]["tri_scores"][p] is not None else np.nan for p in (0, 1)] for i in ids], float)
        valid = ~np.isnan(F)
        wt = weights_for(rng, len(ids), None)
        num = wt @ np.nansum(F, 1)
        den = wt @ valid.sum(1)
        m = num / np.maximum(den, 1)
        lo, hi = (float(x) for x in np.percentile(m, [2.5, 97.5]))
        out[pop] = {"point": float(np.nansum(F) / valid.sum()), "lo": lo, "hi": hi, "n_items": len(ids), "applications": int(valid.sum()),
                    "unscored_applications": int(2 * len(ids) - valid.sum()), "k": int(np.nansum(F))}
    out["gap"] = {}
    for k in NAMED:
        I = per_agent[k]
        if not I.complete:
            out["gap"][k] = None
            continue
        ids = [i for i in matrix["populations"]["full"]["ids"] if i in summ and i in I.summary]
        pairs = [(summ[i]["tri_flags"][p], I.summary[i]["tri_flags"][p]) for i in ids for p in (0, 1)
                 if summ[i]["tri_scores"][p] is not None and I.summary[i]["tri_scores"][p] is not None]
        def gap(flag_key):
            by_item: dict[str, list] = defaultdict(list)
            prs = []
            for i in ids:
                for p in (0, 1):
                    if summ[i]["tri_scores"][p] is not None and I.summary[i]["tri_scores"][p] is not None:
                        by_item[i].append(summ[i]["tri_flags"][p] - I.summary[i][flag_key][p])
                        prs.append((summ[i]["tri_flags"][p], I.summary[i][flag_key][p]))
            its = sorted(by_item)
            d = np.array([np.mean(by_item[i]) for i in its])
            wt = weights_for(rng, len(its), None)
            m = (wt @ d) / wt.sum(1)
            lo, hi = (float(x) for x in np.percentile(m, [2.5, 97.5]))
            return {"point": float(np.mean([a - b for a, b in prs])), "lo": lo, "hi": hi, "applications": len(prs),
                    "o_share": float(np.mean([a for a, _ in prs])), "per_agent_recall": float(np.mean([b for _, b in prs]))}
        out["gap"][k] = {**gap("tri_flags"), "flag": "the sealed author-level reading (union)", "unit_beside": gap("tri_flags_unit")}
    return out


# ── the readings, assembled ───────────────────────────────────────────────────────────────────────

def compute(matrix: Mapping[str, Any], scores: Mapping[str, Any], own_drops: Mapping[str, Any] | None = None,
            clean_items: Mapping[str, Any] | None = None) -> dict[str, Any]:
    lock = analysis_lock(scores)
    rows = scores["rows"]
    complete = set(lock["complete_cells"])
    R: dict[str, Any] = {"version": VERSION, "lock": lock, "instruments": {}, "floors": {}, "readings": {}, "labels": {},
                         "own_drops": own_drops or {"n": 0, "ids": [], "reasons": {}},
                         "clean_items": {"touched_ids_sha256": ids_sha256(clean_items["touched_ids"]), "n_touched": len(clean_items["touched_ids"])} if clean_items else None}
    inst: dict[str, Instrument] = {}
    for k, (view, judge) in INSTRUMENTS.items():
        inst[k] = Instrument(k, matrix, rows, f"{view}|{judge}" in complete)
    sham = {}
    ctrl = {}
    for k, I in inst.items():
        if not I.complete:
            R["instruments"][k] = {"complete": False}
            continue
        sham = {i: s for i, s in I.summary.items() if I.items[i]["regime"] == "sham"}
        ctrl = {i: s for i, s in I.summary.items() if I.items[i]["regime"] == "control"}
        R["instruments"][k] = {"complete": True, "view": view_of(k), "judge": INSTRUMENTS[k][1], "n_items": len(I.items),
                               "evaluable": {p: len(I.evaluable_ids(p)) for p in READ_POPS + DESC_POPS + ("certified",)},
                               "loss": {p: I.loss(p) for p in READ_POPS}}
        R["floors"][k] = I.floor(sham)
        fa = True if I.live else R["floors"][k]["a"]["pass"]
        fb = R["floors"][k]["b"]["pass"]
        pops = READ_POPS + DESC_POPS if k in NAMED else READ_POPS
        R["readings"][k] = {p: I.read(p, fa, fb) for p in pops}
        R["labels"][k] = {p: instrument_label(R["readings"][k][p].get("a", {}), R["readings"][k][p].get("b", {})) for p in pops}
        if not fa:                                   # G3: an instrument at floor (a) is not read; only its floor sentence issues
            R["readings"][k].update({"anchors": {"not_read": "floor"}, "secondary": {"not_read": "floor"}, "mechanism": {"not_read": "floor"},
                                     "certified": {"not_read": "floor"}, "preview": {"not_read": "floor"}, "dpart": {"not_read": "floor"},
                                     "stratum_without_nine": {"not_read": "floor"}, "clean": {"not_read": "floor"}})
            continue
        # anchors (S-O1): the controls' and the sham's lone recall (the union, the unit's own flag beside) and mean scores; an unscored
        # application leaves the denominator (the note's rule (b))
        rng = I.rng("anchors")
        anc = {}
        nan = float("nan")
        for name, grp in (("controls", ctrl), ("sham", sham)):
            ok = [s for s in grp.values() if s["n_tri_scored"] > 0]
            if ok:
                F = np.array([[x if x is not None else nan for x in s["tri_flags"]] for s in ok], float)
                Fu = np.array([[x if x is not None else nan for x in s["tri_flags_unit"]] for s in ok], float)
                scored = [x for s in ok for x in s["tri_scores"] if x is not None]
                anc[name] = {"recall": clustered_mean(rng, F), "recall_unit": clustered_mean(rng, Fu), "mean_score": float(np.mean(scored)), "n_items": len(ok),
                             "unscored_applications": int(sum(2 - s["n_tri_scored"] for s in grp.values()))}
            else:
                anc[name] = None
        R["readings"][k]["anchors"] = anc
        if k in NAMED:
            R["readings"][k]["secondary"] = secondary(I, ctrl)
            R["readings"][k]["mechanism"] = mechanism(I, ctrl)
            R["readings"][k]["certified"] = certified(I)
            R["readings"][k]["preview"] = preview(I)
            R["readings"][k]["dpart"] = dpart(I)
            R["readings"][k]["stratum_without_nine"] = I.read("subset", fa, fb)["a"]   # the stratum less its nine unresolved members is the subset
            R["readings"][k]["clean"] = clean_readings(I, clean_items, fa, fb)         # G6: form (a) on the items none of whose applications broke a later honest edit
    R["cascade"] = cascade(inst, R["floors"], R["readings"])
    R["composed"] = {}
    for j in O_JUDGES:
        R["composed"][j] = composed(rows, matrix, j, inst, f"O_diff|{j}") if f"O_diff|{j}" in complete else {"complete": False}
    R["sentences"] = select(R, matrix)
    return R


def view_of(k: str) -> str:
    return INSTRUMENTS[k][0]


def clean_readings(I: Instrument, clean_items: Mapping[str, Any] | None, fa: bool, fb: bool) -> dict[str, Any]:
    """G6 (brief 33's dated note 3): beside the reading, never in its place, form (a) on the population's items none of whose
    applications broke a later honest edit, for the subset and the stratum; descriptive, no label, no effect on the cascade.
    The exclusion set is read from the file the A3b script fixed."""
    if clean_items is None:
        return {"not_read": "no clean-items file"}
    touched = set(clean_items["touched_ids"])
    out = {}
    for pop in ("subset", "stratum"):
        ev = I.evaluable_ids(pop)
        keep = [i for i in ev if i not in touched]
        n_pop = len(I.pop_ids(pop))
        r = I.read(pop, fa, fb, ids=keep)
        a = r.get("a", {})
        out[pop] = {"n_population": n_pop, "n_evaluable": len(ev), "n_excluded": len(ev) - len(keep), "n": len(keep), "fit_ok": bool(a.get("fit_ok")),
                    "reason": a.get("reason") or a.get("not_read"),
                    "contrast": ({kk: a["contrast"][kk] for kk in ("point", "lo", "hi")} if a.get("fit_ok") else None), "ids_sha256": ids_sha256(keep)}
    return out


def secondary(I: Instrument, ctrl: Mapping[str, dict]) -> dict[str, Any]:
    """S-O2: form (b) refitted over the quiet candidates and the controls with a coordinated-form indicator."""
    M = I.matrix["items"]
    qids = I.evaluable_ids("full")
    cids = [i for i, s in ctrl.items() if s["evaluable"]]
    ids = qids + cids
    if len(cids) < 2 or len(qids) < 4:
        return {"fit_ok": False, "reason": "the design is singular", "n": len(ids)}
    S = I.summary
    C = np.array([M[i]["composition"] for i in ids], float)
    line = np.array([S[i]["line_max"] for i in ids], float)
    gap = np.array([S[i]["gap"] for i in ids], float)
    sonnet = np.array([M[i]["writer"] == "sonnet55" for i in ids], float)
    edit = np.array([M[i]["replace_share"] for i in ids], float)
    docs = sorted({M[i]["document"] for i in ids})
    doc = np.array([docs.index(M[i]["document"]) for i in ids])
    F = np.array([S[i]["tri_flags"] for i in ids], float)
    ind = np.array([0.0] * len(qids) + [1.0] * len(cids))
    r = form_b(C, line, gap, sonnet, edit, doc, F, None, True, I.rng("secondary"), I.bias, indicator=ind)
    if not r["fit_ok"]:
        r2 = form_b(C, line, gap, sonnet, edit, doc, F, pooled_codes(doc), False, I.rng("secondary|nodoc"), I.bias, indicator=ind)   # O7: section 4.3's pooling
        r2["attempts"] = [{"with_doc": True, "fit_ok": False, "reason": r.get("reason")}, {"with_doc": False, "fit_ok": r2["fit_ok"], "reason": r2.get("reason")}]
        r = r2
    r["n_quiet"], r["n_controls"] = len(qids), len(cids)
    return r


def mechanism(I: Instrument, ctrl: Mapping[str, dict]) -> dict[str, Any]:
    """S-Q (Part S (6)): AUROC of the author's maximum section-2 line score for the per-agent flag on the pooled item
    applications of the quiet set and the controls, with a bootstrap clustered on items."""
    M = I.matrix["items"]
    S = I.summary
    ids = [i for i in I.matrix["populations"]["full"]["ids"] + I.matrix["populations"]["controls"]["ids"] if i in S and S[i]["tri_ok"]]
    x = np.array([M[i]["line_max"] for i in ids], float)
    F = np.array([S[i]["tri_flags"] for i in ids], float)
    pos = F.sum(1) > 0
    # application-level AUROC: each application is one case with its item's x; cluster on items
    xa, ya = np.repeat(x, 2), F.ravel()
    if ya.sum() == 0 or ya.sum() == len(ya):
        return {"point": None, "lo": None, "hi": None, "n_items": len(ids), "degenerate": True}
    Mx = pv.auroc_matrix(xa[ya == 1], xa[ya == 0])
    wt = weights_for(I.rng("mechanism"), len(ids), None)
    w_app = np.repeat(wt, 2, axis=1)
    Wp, Wn = w_app[:, ya == 1], w_app[:, ya == 0]
    au = ((Wp @ Mx) * Wn).sum(1) / np.maximum((Wp.sum(1) * Wn.sum(1)), 1e-12)
    lo, hi = (float(x) for x in np.percentile(au, [2.5, 97.5]))
    return {"point": float(Mx.mean()), "lo": lo, "hi": hi, "n_items": len(ids), "n_quiet": int(sum(1 for i in ids if M[i]["regime"] == "candidate")),
            "n_controls": int(sum(1 for i in ids if M[i]["regime"] == "control")), "applications": int(len(ya)), "n_flagged_items": int(pos.sum())}


def certified(I: Instrument) -> dict[str, Any]:
    """S-M2: the certified stratum's mean excess and lone recall under the instrument, with intervals."""
    ids = I.evaluable_ids("certified")
    M = I.matrix["items"]
    if len(ids) < 2:
        return {"n": len(ids), "mean_excess": None, "recall": None}
    A = I.arrays(ids, "certified")
    return {"n": len(ids), "n_sonnet": int(A["sonnet"].sum()), "mean_excess": clustered_mean(I.rng("certified|excess"), A["excess"], A["strata"]),
            "recall": clustered_mean(I.rng("certified|recall"), A["F"], A["strata"]), "n_pre_registered": len(I.pop_ids("certified"))}


def preview(I: Instrument) -> dict[str, Any]:
    """S-M3: mean excess of the whole-credited items minus the never-credited items (A6.17.5), document-stratified
    bootstrap within each arm under its pooled strata."""
    a_ids, b_ids = I.evaluable_ids("preview_credited"), I.evaluable_ids("preview_illegible")
    if len(a_ids) < 2 or len(b_ids) < 2:
        return {"n_credited": len(a_ids), "n_illegible": len(b_ids), "difference": None}
    Aa, Ab = I.arrays(a_ids, "preview_credited"), I.arrays(b_ids, "preview_illegible")
    rng = I.rng("preview")
    wa, wb = weights_for(rng, len(a_ids), Aa["strata"]), weights_for(rng, len(b_ids), Ab["strata"])
    ma = (wa @ Aa["excess"]) / wa.sum(1)
    mb = (wb @ Ab["excess"]) / wb.sum(1)
    lo, hi = (float(x) for x in np.percentile(ma - mb, [2.5, 97.5]))
    return {"n_credited": len(a_ids), "n_illegible": len(b_ids), "difference": {"point": float(Aa["excess"].mean() - Ab["excess"].mean()), "lo": lo, "hi": hi},
            "gross_definition": "11 against 7", "net": "11 against 6"}


def dpart(I: Instrument) -> dict[str, Any]:
    """S-K: form (a) on the full set refitted with Kimi K3's mean D_part and its interaction with composition (25 x the
    interaction coefficient per unit D_part), the main-effect form beside, and the same with Sol's mean D_part."""
    ids = I.evaluable_ids("full")
    A = I.arrays(ids, "full")
    out = {}
    for reader in ("kimi", "sol"):
        d = A[reader]
        inter = I._fit_order("full", A, "a", {"dpart": d, "interaction": (A["C"] - A["C"].mean()) * d})
        main = I._fit_order("full", A, "a", {"dpart": d})
        out[reader] = {"interaction_fit": {k: inter.get(k) for k in ("fit_ok", "reason", "coef_interaction", "coef_dpart", "contrast", "with_doc")},
                       "main_fit": {k: main.get(k) for k in ("fit_ok", "reason", "coef_dpart", "contrast", "with_doc")}, "n": len(ids)}
    return out


# ── sentence selection (section 6) ────────────────────────────────────────────────────────────────

def _lab(label: str) -> str:
    return f"*{label}*"


def _d(x, d=1):
    return fmt(x, d)


def _iv(c: Mapping[str, Any], d=1) -> str:
    return interval(c["lo"], c["hi"], d)


def _name(k: str, fallback: bool) -> str:
    if k == "S" and fallback:
        return INSTRUMENT_NAME["S_fallback"]
    return INSTRUMENT_NAME[k]


def s_d(k: str, form: str, pop: str, r: Mapping[str, Any], n: int, fallback: bool, provisional: Mapping[str, Any] | None, descriptive: bool = False) -> dict:
    """S-D1 to S-D4 for one reading (section 5.3), with clause E; form (b) adds its bias-net lower bound; outside the verdict
    population (or under an instrument that is not the lead) the reading is marked descriptive, section 5.4 (4) (O4)."""
    c = r["contrast"]
    lab = c["label"]
    d = 1 if form == "a" else 2
    m = c["margin"]
    head = f"{_name(k, fallback)}, form ({form}), on {POP_NAME[pop]} (n = {n}): contrast {_d(c['point'], d)} {_iv(c, d)} against the margin {_d(m, d)}"
    if lab == "present":
        sid, tail = "S-D1", f": *present* (the view responds to the combination)."
    elif lab == "attenuated":
        sid, tail = "S-D2", ": *attenuated* (a combination component above zero and below the margin)."
    elif lab == "excluded":
        sid, tail = "S-D3", ": *excluded* (the view reads the most visible line only)."
    else:
        sid, tail = "S-D4", f": *inconclusive*: the interval {_iv(c, d)} cannot tell zero from {_d(m, d)} at this n."
    text = head + tail
    if form == "b":
        text += f"; its lower bound net of the simulated null bias {_d(c['bias'], 3)} is {_d(c['lo_net_of_bias'], 3)}"
    if descriptive:
        text += " (descriptive; no verdict, section 5.4 (4))"
    text += " " + CLAUSE_E
    if provisional and provisional.get("provisional"):
        text = f"provisional: {provisional['lost']} of {provisional['n']} items not evaluable under {_name(k, fallback)}. " + text
    return {"id": sid, "family": "S-D", "instrument": k, "form": form, "population": pop, "text": text}


def s_g(k: str, form: str, pop: str, r: Mapping[str, Any], fallback: bool) -> dict:
    d = 1 if form == "a" else 2
    c = r["disattenuated"]
    text = (f"Disattenuated (A6.5 (ii)): dividing the composition coefficient and its interval by the partial reliability given the covariates, "
            f"0.846 (A6.13.5; the Spearman-Brown reliability of the two-pass mean, 0.915, beside), gives {_d(c['point'], d)} {_iv(c, d)}, which the same "
            f"table would label {_lab(c['label'])}; a sensitivity, never the verdict.")
    if form == "b":
        text += " For form (b), the logit-scale coefficient is divided and contrast (b) recomputed."
    return {"id": "S-G1", "family": "S-G", "instrument": k, "form": form, "population": pop, "text": text}


def s_e(k: str, pop: str, L: Mapping[str, Any], r: Mapping[str, Any], fallback: bool) -> dict:
    name = _name(k, fallback)
    if L["a"] is None:
        a_reason = r.get("a", {}).get("reason") or r.get("a", {}).get("not_read") or "unfit"
        if L.get("b") is not None:
            return {"id": "S-E3", "family": "S-E", "instrument": k, "population": pop,
                    "text": f"{name} form (a) is unfit on {POP_NAME[pop]} ({a_reason}), so the instrument carries no label there; form (b) beside reads {_lab(L['b'])} (descriptive; no instrument label)."}
        return {"id": "S-E3", "family": "S-E", "instrument": k, "population": pop,
                "text": f"{name} carries no label on {POP_NAME[pop]} (form (a) {a_reason}); form (b) is not read ({r.get('b', {}).get('not_read') or r.get('b', {}).get('reason') or 'unfit'})."}
    if L.get("b") is None:
        nr = L.get("b_not_read", "unfit")
        return {"id": "S-E3", "family": "S-E", "instrument": k, "population": pop,
                "text": f"{name}'s label is form (a)'s, {_lab(L['a'])}; form (b) is not read ({nr})."}
    if L["conflict"]:
        return {"id": "S-E2", "family": "S-E", "instrument": k, "population": pop,
                "text": f"{name} is *inconclusive*: form (a) reads {_lab(L['a'])} and form (b) reads {_lab(L['b'])} (a two-step conflict, A6.13.4); both shown."}
    counts = "counts" if L["b_counts"] else f"does not count, its bias-net lower bound {_d(L['b_lo_net'], 3)} at or under 0"
    return {"id": "S-E1", "family": "S-E", "instrument": k, "population": pop,
            "text": f"{name}'s label is form (a)'s, {_lab(L['a'])}; form (b) beside reads {_lab(L['b'])} ({counts} for the conflict rule)."}


def s_fscope(R: Mapping[str, Any], lead: str, pop: str, fallback: bool) -> str:
    rd = R["readings"][lead]
    st, fu = rd["stratum"], rd["full"]
    lst = R["labels"][lead]["stratum"]["label"] if st.get("a", {}).get("fit_ok") else "unfit"
    lfu = R["labels"][lead]["full"]["label"] if fu.get("a", {}).get("fit_ok") else "unfit"
    ist = _iv(st["a"]["contrast"]) if st.get("a", {}).get("fit_ok") else "n/a"
    ifu = _iv(fu["a"]["contrast"]) if fu.get("a", {}).get("fit_ok") else "n/a"
    bracket = "(no single line yields the consequence to one reader family on either of two samples, a second family not contradicting)"
    if pop == "subset":
        return (f"The resolved-anchor subset is 0.23 of the full quiet set (17 of 73); the comprehension-quiet stratum {bracket} is 0.36 of it (26 of 73), "
                f"and on the stratum the reading is {_lab(lst)} with {ist}; on the full quiet set (n = {fu['loss']['evaluable']}) it is {_lab(lfu)} with {ifu}, "
                f"descriptive, with its dilution figure (this design reads *holds* at the margin with probability 0.63 under the upper bound on dilution, S-J1); "
                f"items whose single line carries the consequence are not a test of combination and are reported as such.")
    return (f"The comprehension-quiet stratum {bracket} is 0.36 of the full quiet set (26 of 73); on the full quiet set (n = {fu['loss']['evaluable']}) the reading "
            f"is {_lab(lfu)} with {ifu}, descriptive, with its dilution figure (0.63, S-J1); items whose single line carries the consequence are not a test of "
            f"combination and are reported as such.")


def oc_clause(label: str, pop: str, fallback: bool) -> str:
    """The operating-characteristic clause of S-F1 to S-F4 (Part 3, at the pre-registered n), or the fallback carrier's one clause."""
    if fallback:
        ex0, exm, p15 = ("0.66", "0.04", "0.69") if pop == "subset" else ("0.81", "0.07", "0.77")
        return (f"No joint operating characteristics exist for a cascade led by the second instrument (A6.20); this population's own figures under it at T2+S2 "
                f"are P(*excluded* | 0) {ex0}, P(*excluded* | margin) {exm}, P(LB > 0 | 0) 0.04 and P(*present* | 1.5 ×) {p15} (Part 3, "
                f"{'subset' if pop == 'subset' else 'stratum'}, at the pre-registered n).")
    if label == "excluded":
        return ("Under a true effect at the margin this design reads *holds* with probability 0.04 to 0.06 (Part 3, the carrier population at T2+S2, ICC 0.3 and 0.6), "
                "and that bound is seed-sensitive for the subset (1.8 Monte Carlo SE below 0.10, A6.18 (e)); 0.03 to 0.08 for the stratum; at the pre-registered n.")
    if label == "attenuated":
        rng_ = "0.23 to 0.36 for the subset" if pop == "subset" else "0.41 to 0.56 for the stratum"
        return (f"'Partly missed' is the modal label at the margin because of attenuation, not evidence of a sub-margin effect (A6.16.1 (i); for this population at "
                f"T2+S2 Part 3 gives P(*partly missed* | margin) {rng_} over ICC 0.3 and 0.6, at the pre-registered n); the disattenuated reading stands beside it. " + A618L)
    if label == "present":
        rng_ = "0.34 to 0.37 for the subset" if pop == "subset" else "0.31 to 0.34 for the stratum"
        return (f"For this design P(*falsified* | 0) is 0.00 and P(*falsified* | margin) {rng_} over ICC 0.3 and 0.6 (Part 3, at the pre-registered n; "
                f"Part 2's full-set range 0.24 to 0.41, A6.16.1 (ii)).")
    return A618L


def s_f(R: Mapping[str, Any]) -> list[dict]:
    """S-F1 to S-F6 with the suffix S-Fs1 to S-Fs3, S-Fscope on every holds, and S-G beside every excluded and attenuated."""
    cas = R["cascade"]
    out: list[dict] = []
    if cas["state"] != "read":
        return out
    lead, pop, fb = cas["instrument"], cas["population"], cas["fallback"]
    L = R["labels"][lead][pop]
    a = R["readings"][lead][pop]["a"]["contrast"]
    n = R["readings"][lead][pop]["loss"]["evaluable"]
    name = _name(lead, fb)
    if fb:
        name = f"{INSTRUMENT_NAME['S_fallback']} (the carrier {'at floor' if not cas['floor_a']['C'] else 'unfit on both stratum populations'})"
    other = "S" if lead == "C" else "C"
    oname = "second named instrument" if other == "S" else "carrier"
    Lo = R["labels"][other].get(pop) if R["instruments"][other].get("complete") else None
    o_fit = Lo is not None and Lo["a"] is not None and R["floors"][other]["a"]["pass"]
    oc = R["readings"][other][pop]["a"]["contrast"] if o_fit else None
    m = M_S[lead]
    prov = R["readings"][lead][pop]["loss"]
    prefix = f"provisional: {prov['lost']} of {prov['n']} items not evaluable under {name}. " if prov["provisional"] else ""
    label = L["label"]
    if L["conflict"]:
        sid = "S-F5"
        text = (f"**P-max is inconclusive** on {POP_NAME[pop]}: under {name} form (a) reads {_lab(L['a'])} and form (b) {_lab(L['b'])} (a two-step conflict, "
                f"A6.13.4); both shown. {A618L}")
    elif o_fit and (label, Lo["label"]) in TWO_STEP:
        sid = "S-F6"
        text = (f"**P-max is inconclusive** on {POP_NAME[pop]}: {name} reads {_lab(label)} ({_d(a['point'])} {_iv(a)}) and the other named instrument "
                f"{_lab(Lo['label'])} ({_d(oc['point'])} {_iv(oc)}) (a two-step conflict across instruments, A6.13.4); both shown. {A618L}")
    elif label == "excluded":
        sid = "S-F1"
        text = (f"**P-max holds** on {POP_NAME[pop]} (n = {n}) under {name}: contrast {_d(a['point'])} {_iv(a)} against m_s {_d(m)}. "
                + s_fscope(R, lead, pop, fb) + " " + oc_clause(label, pop, fb))
    elif label == "attenuated":
        sid = "S-F2"
        text = (f"**P-max is partly missed** on {POP_NAME[pop]} (n = {n}) under {name}: contrast {_d(a['point'])} {_iv(a)}, above zero and below m_s {_d(m)}. "
                + oc_clause(label, pop, fb))
    elif label == "present":
        sid = "S-F3"
        text = (f"**P-max is falsified** on {POP_NAME[pop]} (n = {n}) under {name}: contrast {_d(a['point'])} {_iv(a)}, at or above m_s {_d(m)}; this design is "
                f"volume-free by construction, the same-shape sham and the controls beside. " + oc_clause(label, pop, fb))
    else:
        sid = "S-F4"
        text = (f"**P-max is inconclusive** in round 1 on {POP_NAME[pop]} (n = {n}): under {name} the interval {_iv(a)} cannot tell zero from m_s {_d(m)} "
                f"(point {_d(a['point'])}). " + oc_clause(label, pop, fb))
    out.append({"id": sid, "family": "S-F", "instrument": lead, "population": pop, "verdict": PMAX.get(label, "no verdict") if sid not in ("S-F5", "S-F6") else "inconclusive",
                "text": prefix + text})
    # the suffix
    if sid not in ("S-F6",):
        if not o_fit:
            # the note (d): an unscored instrument is one that has not passed its floor
            why = "unfit" if (R["instruments"][other].get("complete") and R["floors"][other]["a"]["pass"]) else "at floor"
            out.append({"id": "S-Fs3", "family": "S-F", "text": f"The {oname} is {why} on {POP_NAME[pop]} and drops out, named."})
        elif Lo["label"] == label:
            out.append({"id": "S-Fs1", "family": "S-F", "text": f"The {oname} confirms it ({_lab(Lo['label'])}; {_d(oc['point'])} {_iv(oc)})."})
        else:
            out.append({"id": "S-Fs2", "family": "S-F", "text": f"The {oname} reads {_lab(Lo['label'])} ({_d(oc['point'])} {_iv(oc)}), beside."})
    return out


def select(R: Mapping[str, Any], matrix: Mapping[str, Any]) -> list[dict]:
    """Section 6.0's assembly order: S-S, S-A, S-C, then S-D and S-E per population read, S-F (with S-G attached), S-H, S-I,
    S-J, S-K, S-L, S-M, S-N, S-O, S-P, S-Q, S-R, then the stopped-row sentences of the note (d) and S4-2."""
    out: list[dict] = []
    cas = R["cascade"]
    # S-S
    od = R["own_drops"]
    if od["n"] == 0:
        out.append({"id": "S-S0", "family": "S-S", "text": "S3's own drops: none; every population is as pre-registered."})
    else:
        pops = ", ".join(f"{POP_NAME.get(p, p)} {matrix['populations'][p]['n'] - od.get('by_population', {}).get(p, 0)}" for p in READ_POPS)
        out.append({"id": "S-S1", "family": "S-S", "text": f"S3 dropped {od['n']} item(s) before any judge call because the restricted mode could not complete their need at "
                                                            f"application time (ids sha256 {ids_sha256(od['ids'])}; reasons as brief 27's refusal classes name them); every population "
                                                            f"is reported net of them: {pops}, …"})
    # the stopped rows (the note (d))
    for cell, v in R["lock"]["incomplete"].items():
        view, judge = cell.split("|")
        out.append({"id": "A1b-d", "family": "A1b", "text": f"not scored under [{VIEW_NAME[view]}, {JUDGE_NAME[judge]}]: {v['of'] - v['scored_rows']} of {v['of']} units"})
    # S-A
    for k in NAMED:
        if not R["instruments"][k].get("complete"):
            out.append({"id": "S-A2", "family": "S-A", "instrument": k, "text": f"floor; not read under {INSTRUMENT_NAME[k]}, form (a) (its row is not scored; the note (d) treats "
                                                                                 f"an unscored instrument as one that has not passed its floor)."})
            continue
        fa = R["floors"][k]["a"]
        if fa["pass"]:
            out.append({"id": "S-A1", "family": "S-A", "instrument": k, "text": f"{INSTRUMENT_NAME[k]} separates the quiet set from the sham (AUROC {fmt(fa['point'])} "
                                                                                 f"{interval(fa['lo'], fa['hi'])}); form (a) is read under it."})
        else:
            out.append({"id": "S-A2", "family": "S-A", "instrument": k, "text": f"floor; not read under {INSTRUMENT_NAME[k]}, form (a) (AUROC {fmt(fa['point'])} "
                                                                                 f"{interval(fa['lo'], fa['hi'])}; the lower bound is at or under 0.5)."})
    if cas["state"] == "no_verdict" and cas.get("sentence") == "S-A3":
        out.append({"id": "S-A3", "family": "S-A", "text": "floor; not read under either named instrument: round 1 issues no verdict on P-max in this design; every cell is descriptive."})
    at_floor_a = {k for k in NAMED if R["instruments"][k].get("complete") and not R["floors"][k]["a"]["pass"]}   # G3: only the floor sentence
    for k in NAMED + D_ROWS:
        if not R["instruments"][k].get("complete") or k in at_floor_a:
            continue
        fb = R["floors"][k]["b"]
        q, s = fb["quiet"], fb["sham"]
        bu = R["floors"][k]["b_unit"]
        beside = f"; the planted unit's own flag beside: quiet {fmt(bu['quiet']['point'])} {interval(bu['quiet']['lo'], bu['quiet']['hi'])} against the sham's upper bound {fmt(bu['sham']['hi'])}"
        if fb["pass"]:
            out.append({"id": "S-A5", "family": "S-A", "instrument": k, "text": f"form (b) is above the floor under {INSTRUMENT_NAME[k]} (quiet lone recall {fmt(q['point'])} "
                                                                                 f"{interval(q['lo'], q['hi'])}; sham upper bound {fmt(s['hi'])}; application-level Clopper-Pearson "
                                                                                 f"{interval(*fb['cp_quiet'])} beside{beside})."})
        else:
            out.append({"id": "S-A4", "family": "S-A", "instrument": k, "text": f"floor; form (b) is not read under {INSTRUMENT_NAME[k]} (quiet lone recall {fmt(q['point'])} "
                                                                                 f"{interval(q['lo'], q['hi'])} against the sham's upper bound {fmt(s['hi'])}{beside}); form (a)'s label is unaffected."})
    # S-B and S-C5 for the named instruments on the populations read
    for k in NAMED:
        if not R["instruments"][k].get("complete") or k in at_floor_a:
            continue
        for pop in READ_POPS:
            rd = R["readings"][k][pop]
            b = rd.get("b", {})
            if b.get("not_read") == "ceiling":
                out.append({"id": "S-B1", "family": "S-B", "instrument": k, "population": pop,
                            "text": f"form (b) is not read under {INSTRUMENT_NAME[k]} on {POP_NAME[pop]}: ceiling (quiet lone recall {fmt(b['recall'])} is above 0.85, A6.13.5); "
                                    f"form (a)'s label is unaffected."})
            elif not b.get("fit_ok") and b.get("not_read") is None:
                out.append({"id": "S-C5", "family": "S-C", "instrument": k, "population": pop,
                            "text": f"form (b) does not fit under {INSTRUMENT_NAME[k]} on {POP_NAME[pop]}: {b.get('reason')}; reported as unfit, without effect on form (a)'s label."})
    # S-C: the cascade's steps
    for st in cas["steps"]:
        sid = st.get("sentence")
        if not sid:
            continue
        k, pop = st["instrument"], st["population"]
        name = _name(k, st.get("fallback", False)) if k else ""
        n = R["readings"][k][pop]["loss"]["evaluable"] if k and pop else None
        if sid == "S-C1":
            text = (f"{name} form (a) does not fit on the resolved-anchor subset (n = {n}): {st['reason']}. The reading steps down to the comprehension-quiet stratum "
                    f"(A6.17.9 (4)); the step was taken on a fit failure, never on a value.")
        elif sid == "S-C2":
            text = f"{name} form (a) does not fit on the comprehension-quiet stratum either (n = {n}): {st['reason']}. The third branch of A6.14.3 applies (S-H)."
        elif sid == "S-C3":
            text = (f"The carrier does not fit on the comprehension-quiet stratum either (n = {n}): {st['reason']}. The second named instrument takes the lead as the "
                    f"fallback carrier and starts the cascade at the resolved-anchor subset (A6.20); no joint operating characteristics exist for a cascade it leads.")
        elif sid == "S-C3b":
            text = f"{name} does not fit on the full quiet set either: {st['reason']}. The other named instrument reads the third branch (A6.13.4)."
        else:
            text = "No named instrument fits on any population of the cascade: round 1 issues no verdict on P-max; every cell is descriptive."
        out.append({"id": sid, "family": "S-C", "instrument": k, "population": pop, "text": text})
    # S-C6: the other named instrument unfit on the population the lead reads
    if cas["state"] == "read":
        lead, pop = cas["instrument"], cas["population"]
        other = "S" if lead == "C" else "C"
        if R["instruments"][other].get("complete") and R["floors"][other]["a"]["pass"] and not R["readings"][other][pop]["a"].get("fit_ok"):
            out.append({"id": "S-C6", "family": "S-C", "instrument": other, "population": pop,
                        "text": f"{INSTRUMENT_NAME[other]} does not fit on {POP_NAME[pop]}: {R['readings'][other][pop]['a'].get('reason')}; it drops out, named (A6.13.4)."})
    # S-D and S-E per named instrument, form and population read
    verdict_at = (cas.get("instrument"), cas.get("population")) if cas["state"] == "read" else (None, None)
    for k in NAMED:
        if not R["instruments"][k].get("complete") or k in at_floor_a:
            continue
        fb = cas.get("fallback", False) and k == "S"
        for pop in READ_POPS:
            rd = R["readings"][k][pop]
            n = rd["loss"]["evaluable"]
            prov = rd["loss"] if (k == cas.get("lead")) else None
            for form in ("a", "b"):
                r = rd.get(form, {})
                if r.get("fit_ok"):
                    out.append(s_d(k, form, pop, r, n, fb, prov, descriptive=(k, pop) != verdict_at))
                    if r["contrast"]["label"] in ("excluded", "attenuated"):
                        out.append(s_g(k, form, pop, r, fb))            # G4: S-G1 beside every excluded or attenuated reading
            out.append(s_e(k, pop, R["labels"][k][pop], rd, fb))
    # S-F with S-G
    out += s_f(R)
    # S-H: the third branch
    if cas["state"] == "third":
        k, fb = cas["instrument"], cas["fallback"]
        L = R["labels"][k]["full"]
        a = R["readings"][k]["full"]["a"]["contrast"]
        n_full = R["readings"][k]["full"]["loss"]["evaluable"]
        n_st = R["readings"][k]["stratum"]["loss"]["evaluable"]
        if L["label"] == "present":
            out.append({"id": "S-H2", "family": "S-H", "instrument": k, "text":
                        f"Third branch (A6.14.3): **P-max is falsified on the full quiet set** (n = {n_full}) under {_name(k, fb)}: contrast {_d(a['point'])} {_iv(a)}, at or above "
                        f"m_s {_d(M_S[k])}. A full-set *present* stands (A6.18 (c)): on the diluted full set P(*present* | 0) is 0.00, within A6.13.1 (iii); its power is disclosed "
                        f"with it: about 0.01 at 1.5 × the margin under the zero model, 0.36 under the latent 0.69, and 0.00 to 0.02 at the margin."})
        else:
            out.append({"id": "S-H1", "family": "S-H", "instrument": k, "text":
                        f"Third branch (A6.14.3): neither stratum population could be read (above); the full quiet set (n = {n_full}) is reported with its dilution figure as "
                        f"descriptive ({_name(k, fb)}: contrast {_d(a['point'])} {_iv(a)}; under the upper bound on dilution this design reads *holds* at the margin with "
                        f"probability 0.63, 0.15 at the latent share 0.69); *excluded* and *attenuated* are not issued from it. The carrier reads: 'inconclusive: too few items "
                        f"in which no single line yields the consequence (n = {n_st})'."})
    # S-I: subset against stratum under the lead, whenever both are read
    if cas.get("lead") and R["instruments"][cas["lead"]].get("complete"):
        k = cas["lead"]
        rs, rt = R["readings"][k]["subset"]["a"], R["readings"][k]["stratum"]["a"]
        if rs.get("fit_ok") and rt.get("fit_ok"):
            Ls, Lt = R["labels"][k]["subset"]["label"], R["labels"][k]["stratum"]["label"]
            cs, ct = rs["contrast"], rt["contrast"]
            ns, nt = R["readings"][k]["subset"]["loss"]["evaluable"], R["readings"][k]["stratum"]["loss"]["evaluable"]
            s_excl = not (cs["lo"] <= ct["point"] <= cs["hi"])
            t_excl = not (ct["lo"] <= cs["point"] <= ct["hi"])
            name = _name(k, cas["fallback"])
            if Ls == Lt and not s_excl and not t_excl:
                out.append({"id": "S-I1", "family": "S-I", "text": f"The resolved-anchor subset (n = {ns}) and the comprehension-quiet stratum (n = {nt}) agree under {name}: "
                                                                   f"{_lab(Ls)} {_d(cs['point'])} {_iv(cs)} and {_lab(Lt)} {_d(ct['point'])} {_iv(ct)}."})
            else:
                why = "the labels differ" if Ls != Lt else ("the subset's interval excludes the stratum's point" if s_excl else "the stratum's interval excludes the subset's point")
                out.append({"id": "S-I2", "family": "S-I", "text": f"The resolved-anchor subset (n = {ns}) and the comprehension-quiet stratum (n = {nt}) **disagree** under {name} "
                                                                   f"({why}): {_lab(Ls)} {_d(cs['point'])} {_iv(cs)} against {_lab(Lt)} {_d(ct['point'])} {_iv(ct)}. The subset carries (A6.18 (b)): the "
                                                                   f"stratum's nine unresolved-anchor members (all GLM-written) entered on a day-0 rendering in which their lines were absent, so their "
                                                                   f"D_part = 0 measures a missing line, not a quiet one (A6.18 (h)); the subset shifts the writer balance (Sonnet 11, GLM 6; A6.17.9)."})
    # S-J: the full set, descriptive
    if cas["state"] == "read":
        k = cas["instrument"]
        rf = R["readings"][k]["full"]["a"]
        if rf.get("fit_ok"):
            c = rf["contrast"]
            out.append({"id": "S-J1", "family": "S-J", "text": f"On the full quiet set (n = {R['readings'][k]['full']['loss']['evaluable']}), descriptive under the switch (A6.14.3, A6.18 (a)), "
                                                               f"{_name(k, cas['fallback'])} form (a) reads contrast {_d(c['point'])} {_iv(c)} ({_lab(R['labels'][k]['full']['label'])}, descriptive); its dilution "
                                                               f"figure: with non-members at excess zero this design reads *holds* at the margin with probability 0.63 (0.36 with a small excess, 0.15 at the "
                                                               f"latent share 0.69, 0.48 at 0.46; Part 3); no verdict is issued from it."})
    # S-G6: form (a) on the items none of whose applications broke a later honest edit (brief 33's dated note 3), beside, descriptive
    for k in NAMED:
        if not R["instruments"][k].get("complete") or k in at_floor_a:
            continue
        cl = R["readings"][k].get("clean") or {}
        if cl.get("not_read"):
            continue
        for pop in ("subset", "stratum"):
            c = cl[pop]
            head = (f"Beside the reading (descriptive; brief 33's dated note 3, G6): {INSTRUMENT_NAME[k]} form (a) on the {POP_NAME[pop]} items none of whose applications broke "
                    f"a later honest edit (n = {c['n']} of {c['n_evaluable']} evaluable, {c['n_excluded']} excluded; population {c['n_population']})")
            if c["fit_ok"]:
                out.append({"id": "S-G6", "family": "S-G6", "instrument": k, "population": pop, "text": f"{head}: contrast {_d(c['contrast']['point'])} {interval(c['contrast']['lo'], c['contrast']['hi'], 1)}; no label, no effect on the cascade or the verdict."})
            else:
                out.append({"id": "S-G6b", "family": "S-G6", "instrument": k, "population": pop, "text": f"{head}: too few items for the fit ({c['reason']}); no label, no effect on the cascade or the verdict."})
    # S-K: the D_part interaction, carrier and second instrument
    for k in NAMED:
        if not R["instruments"][k].get("complete") or k in at_floor_a:
            continue
        dp = R["readings"][k]["dpart"]
        ki, so = dp["kimi"], dp["sol"]
        name = INSTRUMENT_NAME[k]
        if ki["interaction_fit"]["fit_ok"]:
            c = ki["interaction_fit"]["coef_interaction"]
            if c["hi"] < 0:
                out.append({"id": "S-K1", "family": "S-K", "instrument": k, "text": f"On the full quiet set, under {name}, the composition contrast falls as Kimi K3's D_part rises (interaction "
                                                                                    f"{_d(c['point'])} {_iv(c)} per unit D_part): consistent with dilution by items one of whose lines yields the consequence alone; a "
                                                                                    f"covariate sensitivity (A6.14.2), never a verdict."})
            elif c["lo"] > 0:
                out.append({"id": "S-K2", "family": "S-K", "instrument": k, "text": f"On the full quiet set, under {name}, the composition contrast rises as D_part rises (interaction {_d(c['point'])} "
                                                                                    f"{_iv(c)}): the opposite of dilution; a covariate sensitivity, never a verdict."})
            else:
                out.append({"id": "S-K3", "family": "S-K", "instrument": k, "text": f"On the full quiet set, under {name}, the interaction {_d(c['point'])} {_iv(c)} does not separate from zero at this n; "
                                                                                    f"a covariate sensitivity, never a verdict."})
        mf = ki["main_fit"]
        if mf["fit_ok"] and so["interaction_fit"]["fit_ok"]:
            out.append({"id": "S-K4", "family": "S-K", "instrument": k, "text": f"Main-effect form: D_part {_d(mf['coef_dpart']['point'])} {_iv(mf['coef_dpart'])}, composition contrast "
                                                                                f"{_d(mf['contrast']['point'])} {_iv(mf['contrast'])}; with Sol's D_part: interaction {_d(so['interaction_fit']['coef_interaction']['point'])} "
                                                                                f"{_iv(so['interaction_fit']['coef_interaction'])}."})
    # S-L: the Q1-against-Q3 sensitivity, form (b), per named instrument and population read
    for k in NAMED:
        if not R["instruments"][k].get("complete") or k in at_floor_a:
            continue
        for pop in READ_POPS:
            b = R["readings"][k][pop].get("b", {})
            if b.get("fit_ok"):
                q = b["q1q3"]
                out.append({"id": "S-L1", "family": "S-L", "instrument": k, "population": pop, "text":
                            f"Q1-against-Q3 sensitivity (A6.4, at the full net set's quartiles, A6.20), form (b), {INSTRUMENT_NAME[k]}, {POP_NAME[pop]}: P(flag | 66.5) − P(flag | 47.5) = "
                            f"{_d(q['point'], 2)} {_iv(q, 2)} against the scaled margin 0.228: {_lab(q['label'])}; a sensitivity, never primary."})
            else:
                out.append({"id": "S-L2", "family": "S-L", "instrument": k, "population": pop,
                            "text": f"Q1-against-Q3 sensitivity: not read ({b.get('not_read', 'unfit')})."})
    # S-M
    lead = cas.get("lead") or "C"
    if R["instruments"][lead].get("complete"):
        name = _name(lead, cas.get("fallback", False))
        for pop in DESC_POPS:
            r = R["readings"][lead][pop]["a"]
            n = R["readings"][lead][pop]["loss"]["evaluable"]
            if r.get("fit_ok"):
                c = r["contrast"]
                out.append({"id": "S-M1", "family": "S-M", "population": pop, "text": f"{POP_NAME[pop]} (n = {n}), descriptive (the purity sensitivity, A6.17.1; A6.18 (h)): {name} form (a) contrast "
                                                                                      f"{_d(c['point'])} {_iv(c)} ({_lab(R['labels'][lead][pop]['label'])}, descriptive; no verdict)."})
            else:
                out.append({"id": "S-M1", "family": "S-M", "population": pop, "text": f"{POP_NAME[pop]} (n = {n}), descriptive (the purity sensitivity, A6.17.1; A6.18 (h)): {name} form (a) is unfit "
                                                                                      f"({r.get('reason')}); no verdict."})
        ce = R["readings"][lead]["certified"]
        cv = PMAX.get(R["labels"][lead][cas["population"]]["label"], "no verdict") if cas["state"] == "read" else "no verdict"
        if ce.get("mean_excess"):
            out.append({"id": "S-M2", "family": "S-M", "text": f"The certified stratum (mean composition at or above 75; n = {ce['n']}, Sonnet {ce['n_sonnet']}), A6.2's descriptive stratum: under {name}, "
                                                               f"mean excess {_d(ce['mean_excess']['point'])} {_iv(ce['mean_excess'])} and lone recall {_d(ce['recall']['point'], 2)} {_iv(ce['recall'], 2)}; "
                                                               f"its composition spread (SD 3.6) carries no slope; the carrier's verdict, *{cv}*, beside."})
        pv_ = R["readings"][lead]["preview"]
        if pv_.get("difference"):
            d = pv_["difference"]
            out.append({"id": "S-M3", "family": "S-M", "text": f"Within-stratum preview of round 2's contrast (A6.17.5; descriptive, no verdict label): under {name}, mean excess of the whole-credited "
                                                               f"items (n = {pv_['n_credited']}) minus that of the never-credited items (n = {pv_['n_illegible']}) is {_d(d['point'])} {_iv(d)} (gross definition 11 against 7; "
                                                               f"net 11 against 6)."})
        w9 = R["readings"][lead]["stratum_without_nine"]
        if w9.get("fit_ok"):
            c = w9["contrast"]
            out.append({"id": "S-M4", "family": "S-M", "text": f"Every stratum table flags the nine unresolved-anchor members (all GLM-written); the stratum reading recomputed without the nine: "
                                                               f"{_d(c['point'])} {_iv(c)} (the 17 that remain are the resolved-anchor subset)."})
    # S-N: the composed view and G1
    for j in O_JUDGES:
        co = R["composed"][j]
        if not co or co.get("complete") is False or not co.get("full"):
            continue
        f, c, s = co["full"], co.get("controls"), co.get("sham")
        gaps = "; ".join(f"its gap over {INSTRUMENT_NAME[k]} on the same applications {_d(g['point'], 2)} {_iv(g, 2)} (the planted unit's own flag beside: {_d(g['unit_beside']['point'], 2)})"
                         for k, g in co["gap"].items() if g)
        text = (f"The composed view (`O_diff`, {JUDGE_NAME[j]}, at its sealed rule) flags {_d(f['point'], 2)} {_iv(f, 2)} of the full quiet set's item applications (n = {f['n_items']} items, "
                f"{f['applications']} applications); controls {_d(c['point'], 2) if c else 'n/a'}; sham {_d(s['point'], 2) if s else 'n/a'}; {gaps}; not a P-max reading and no partition (A6.3 (e))")
        if j != "sol" and co.get("stratum"):
            text += f"; on the comprehension-quiet stratum {_d(co['stratum']['point'], 2)} {_iv(co['stratum'], 2)}"
        out.append({"id": "S-N1", "family": "S-N", "judge": j, "text": text + "."})
    co = R["composed"].get("opus48") or {}
    if co.get("full"):
        f = co["full"]
        st = co.get("stratum") or {}
        if f["point"] >= G1_BAR:
            out.append({"id": "S-N2", "family": "S-N", "text": f"Brief 22's G1 holds: Opus 4.8's `O_diff` recall on the full quiet set (net 73 items, {f['applications']} applications) is {_d(f['point'], 2)} "
                                                               f"{_iv(f, 2)}, at or above 0.65 (optimistic for B4, since B3's thresholds on `prefix_rw_v2c` sit below B4-R's); the stratum's {_d(st.get('point'), 2)} beside (A6.16.1 (vi))."})
        else:
            out.append({"id": "S-N3", "family": "S-N", "text": f"Brief 22's G1 fails: Opus 4.8's `O_diff` recall on the full quiet set (net 73 items, {f['applications']} applications) is {_d(f['point'], 2)} "
                                                               f"{_iv(f, 2)}, below 0.65; the stratum's {_d(st.get('point'), 2)} beside (A6.16.1 (vi))."})
    # S-O: anchors per per-agent view, and the named secondary
    for k in NAMED + D_ROWS:
        if not R["instruments"][k].get("complete") or k in at_floor_a:
            continue
        an = R["readings"][k]["anchors"]
        c, s = an.get("controls"), an.get("sham")
        if c and s:
            out.append({"id": "S-O1", "family": "S-O", "instrument": k, "text": f"Anchors under {INSTRUMENT_NAME[k]}: lone recall, controls {_d(c['recall']['point'], 2)} {_iv(c['recall'], 2)} and sham "
                                                                                 f"{_d(s['recall']['point'], 2)} {_iv(s['recall'], 2)} (the sealed author-level reading; the planted unit's own flag beside: controls "
                                                                                 f"{_d(c['recall_unit']['point'], 2)}, sham {_d(s['recall_unit']['point'], 2)}); mean scores, controls {_d(c['mean_score'])} and sham {_d(s['mean_score'])}; descriptive."})
    for k in NAMED:
        if not R["instruments"][k].get("complete") or k in at_floor_a:
            continue
        sec = R["readings"][k]["secondary"]
        if sec.get("fit_ok"):
            fc = sec["form_contrast"]
            out.append({"id": "S-O2", "family": "S-O", "instrument": k, "text": f"Form (b) refitted over the quiet candidates and the controls with a coordinated-form indicator under {INSTRUMENT_NAME[k]}: "
                                                                                 f"{_d(fc['point'], 2)} {_iv(fc, 2)}; the form contrast, never the composition reading (A6.3 (c))."})
    # S-P
    out.append({"id": "S-P0", "family": "S-P", "text": "A6.3 (d)'s k = 2 descriptive arm was not run (not approved at S2)."})
    # S-Q
    for k in NAMED:
        if not R["instruments"][k].get("complete") or k in at_floor_a:
            continue
        m = R["readings"][k]["mechanism"]
        if m.get("point") is None:
            continue
        if m["point"] > SQ_BAR:
            out.append({"id": "S-Q1", "family": "S-Q", "instrument": k, "text": f"The author's most visible line predicts the {INSTRUMENT_NAME[k]} flag on the pooled item applications of the quiet set and the "
                                                                                 f"controls (AUROC {_d(m['point'], 2)} {_iv(m, 2)}); descriptive (no matched controls, the sham unrated on this axis)."})
        else:
            out.append({"id": "S-Q2", "family": "S-Q", "instrument": k, "text": f"It does not under {INSTRUMENT_NAME[k]} ({_d(m['point'], 2)} {_iv(m, 2)}); the max-type mechanism is not confirmed prospectively on this pool; descriptive."})
    # S-R: the descriptive instruments
    for k in D_ROWS:
        if not R["instruments"][k].get("complete"):
            continue
        for pop in READ_POPS:
            rd = R["readings"][k][pop]
            n = rd["loss"]["evaluable"]
            for form in ("a", "b"):
                if form == "a" and k in LIVE:
                    continue
                r = rd.get(form, {})
                if r.get("fit_ok"):
                    c = r["contrast"]
                    d = 1 if form == "a" else 2
                    lab = R["labels"][k][pop]["label"] if form == "a" else c["label"]
                    text = f"Under {INSTRUMENT_NAME[k]} (descriptive, A6.13.3), form ({form}) on {POP_NAME[pop]} (n = {n}): contrast {_d(c['point'], d)} {_iv(c, d)} ({_lab(lab)}, descriptive; no verdict)"
                    if k in LIVE:
                        text += "; form (a) is not read on a live view"
                    out.append({"id": "S-R1", "family": "S-R", "instrument": k, "form": form, "population": pop, "text": text + "."})
                    if c["label"] in ("excluded", "attenuated"):
                        out.append(s_g(k, form, pop, r, False))              # G4
                else:
                    nr = r.get("not_read") or "unfit"
                    out.append({"id": "S-R2", "family": "S-R", "instrument": k, "form": form, "population": pop,
                                "text": f"Under {INSTRUMENT_NAME[k]}, form ({form}) is not read ({nr})."})
    # S4
    out.append({"id": "S4-2", "family": "S4", "text": "Human anchor (S4): not yet scored; reported beside when it is (A6.18 (q))."})
    return out


# ── the disclosures, the record and the CLI ───────────────────────────────────────────────────────

def plan_sections(plan_text: str) -> dict[str, str]:
    """Section 7 verbatim, and the 2026-11-02 note's item 5 (brief 31's disclosures) verbatim."""
    m7 = re.search(r"^## 7\. .*?$(.*?)^---$", plan_text, re.S | re.M)
    m5 = re.search(r"^\*\*5\. Brief 31's disclosures.*?$(.*?)^\*\*6\. ", plan_text, re.S | re.M)
    if not m7 or not m5:
        raise SystemExit("plan.md: section 7 or the note's item 5 was not found")
    return {"section_7": m7.group(0).strip(), "note_2026_11_02_item_5": m5.group(0).rsplit("**6. ", 1)[0].strip(),
            "section_8_pointer": "Round 2 (plan section 8): pre-registered there and never pooled with round 1; its own plan commits before any round-2 judge call."}


def render_md(R: Mapping[str, Any], meta: Mapping[str, Any], disclosures: Mapping[str, str]) -> str:
    L = ["# B3 results (S3; brief 33): every sentence selected by rule from `work/stage3/b3/plan.md`", ""]
    L.append(f"Plan `{meta['plan']['path']}` {meta['plan']['sha256'][:8]} (fork commit {meta['plan'].get('commit', 'n/a')}); matrix {meta['matrix_sha256'][:8]}; scores {meta['scores_sha256'][:8]}; "
             f"readings script {meta['script_sha256'][:8]}; judge clients {', '.join(f'{k} {v[:8]}' for k, v in meta['client_sha256'].items())} (section 4.10); window rule: {meta['window_rule']}.")
    L.append(f"Bootstrap sub-streams (O6): every reading draws its 2,000 replicates from `default_rng([20261152, sha256('<instrument>|<reading tag>')[:4]])`, one stream per reading, so each is reproducible on its own; the seed 20261152 is the plan's. "
             f"Flags: the sealed author-level reading (the union, plan.md's dated note 3 of 2026-11-02), the planted unit's own flag beside.")
    if meta.get("dryrun_oc"):
        oc = meta["dryrun_oc"]
        L.append(f"Operating characteristics (O3): the readings script's own dry run through Part 3's simulator (seed 20261171, tag 500, 300 experiments, ICC 0.3, the subset under the \"none\" model) gives the carrier P(excluded | 0) {oc['P_excl_0']:.2f}, "
                 f"P(excluded | margin) {oc['P_excl_margin']:.2f}, P(LB > 0 | 0) {oc['P_lb_0']:.2f}, P(present | 1.5 x) {oc['P_present_x1.5']:.2f}, beside Part 3's 0.68 / 0.07 / 0.03 / 0.72 that S-F's fixed clauses quote; "
                 f"bound (ii) sits {oc.get('se_below_bound', 'n/a')} Monte Carlo SE below 0.10 here against Part 3's 1.8 (section 7, A6.18 (e)); the cascade was selected on Part 3's figures as pre-registered.")
    L.append("")
    lock = R["lock"]
    L.append(f"Analysis lock: {lock['rows']} of {lock['expected_rows']} rows; incomplete rows {lock['incomplete'] or 'none'}; stopped: {bool(lock['stopped'])}.")
    cas = R["cascade"]
    L.append(f"Cascade: floor (a) C {cas['floor_a'].get('C')}, S {cas['floor_a'].get('S')}; lead {cas.get('lead')}; state {cas['state']}; step {cas.get('step')}; "
             f"population {cas.get('population')}; instrument {cas.get('instrument')}; fallback {cas.get('fallback')}.")
    L.append("")
    L.append("## Sentences, in section 6.0's assembly order")
    L.append("")
    for s in R["sentences"]:
        tag = " ".join(f"{k} {s[k]}" for k in ("instrument", "form", "population", "judge") if k in s)
        L.append(f"- **{s['id']}**{(' (' + tag + ')') if tag else ''}: {s['text']}")
    L.append("")
    L.append("## Section 7's disclosures, verbatim")
    L.append("")
    L.append(disclosures["section_7"])
    L.append("")
    L.append("## Brief 31's disclosures (the plan's note of 2026-11-02, item 5), verbatim")
    L.append("")
    L.append(disclosures["note_2026_11_02_item_5"])
    L.append("")
    L.append("## Round 2")
    L.append("")
    L.append(disclosures["section_8_pointer"])
    L.append("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--matrix", default=str(PROJECT / "work/stage3/b3/s3-analysis-matrix-v0.json"))
    ap.add_argument("--scores", default=str(PROJECT / "work/stage3/b3/s3-scores-v0.json"))
    ap.add_argument("--plan", default=str(PROJECT / PLAN))
    ap.add_argument("--out-dir", default=str(PROJECT / "work/stage3/b3"))
    ap.add_argument("--own-drops", default=None, help="S3's own drops record (JSON: n, ids, reasons, by_population)")
    ap.add_argument("--clean-items", default=str(PROJECT / "work/stage3/b3/s3-clean-items-v0.json"), help="G6: the items touched by a broken honest edit (ids), from the A3b script")
    ap.add_argument("--dryrun", default=str(PROJECT / "work/stage3/b3/s3-readings-dryrun-v0.json"), help="O3: the dry run's operating characteristics, quoted beside Part 3's")
    ap.add_argument("--plan-commit", default=None)
    ap.add_argument("--window-rule", default="the corpus span (build_world: days = corpus_days(rows)); units built as planted_items (B1)")
    ns = ap.parse_args(argv)
    matrix, scores = load_json(Path(ns.matrix)), load_json(Path(ns.scores))
    own = load_json(Path(ns.own_drops)) if ns.own_drops else None
    clean = load_json(Path(ns.clean_items)) if ns.clean_items and Path(ns.clean_items).exists() else None
    R = compute(matrix, scores, own, clean)
    plan_text = Path(ns.plan).read_text(encoding="utf-8")
    disc = plan_sections(plan_text)
    meta = {"version": VERSION, "plan": {"path": PLAN, "sha256": hashlib.sha256(plan_text.encode("utf-8")).hexdigest(), "commit": ns.plan_commit},
            "matrix_sha256": hashlib.sha256(Path(ns.matrix).read_bytes()).hexdigest(), "scores_sha256": hashlib.sha256(Path(ns.scores).read_bytes()).hexdigest(),
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "client_sha256": {"judge_client.py": hashlib.sha256((HERE / "judge_client.py").read_bytes()).hexdigest(),
                              "judge_openrouter.py": hashlib.sha256((HERE / "judge_openrouter.py").read_bytes()).hexdigest()},
            "window_rule": ns.window_rule, "clean_items_sha256": hashlib.sha256(Path(ns.clean_items).read_bytes()).hexdigest() if clean else None}
    if ns.dryrun and Path(ns.dryrun).exists():
        oc = load_json(Path(ns.dryrun)).get("oc") or {}
        cells = oc.get("cells", {})
        if cells:
            C0, Cm, C15 = cells["null|subset|none"]["form_a"]["C"], cells["margin|subset|none"]["form_a"]["C"], cells["x1.5|subset|none"]["form_a"]["C"]
            n = oc["experiments"]
            pm = Cm["excluded"]
            meta["dryrun_oc"] = {"P_excl_0": C0["excluded"], "P_excl_margin": pm, "P_lb_0": C0["attenuated"] + C0["present"], "P_present_x1.5": C15["present"],
                                 "experiments": n, "se_below_bound": round((0.10 - pm) / max((pm * (1 - pm) / n) ** 0.5, 1e-9), 1), "dryrun_sha256": hashlib.sha256(Path(ns.dryrun).read_bytes()).hexdigest()}
    R["meta"] = meta
    R["disclosures"] = disc
    out_dir = Path(ns.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "b3-results.json").write_text(json.dumps(R, indent=1, default=_json_default) + "\n", encoding="utf-8")
    (out_dir / "b3-results.md").write_text(render_md(R, meta, disc), encoding="utf-8")
    print(json.dumps({"sentences": [s["id"] for s in R["sentences"]], "cascade": {k: R["cascade"].get(k) for k in ("lead", "state", "step", "population", "instrument", "fallback")}}, indent=1))
    return 0


def _json_default(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


if __name__ == "__main__":
    sys.exit(main())
