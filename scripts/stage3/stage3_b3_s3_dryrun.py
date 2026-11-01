#!/usr/bin/env python3
"""Brief 33 A2 (S3, 2026-11-02): the readings script's dry run, before any draw. Two parts, written as
`work/stage3/b3/s3-readings-dryrun-v0.{md,json}` (counts only):

1. Reachability by constructed fixtures. Each fixture (`FIXTURES`) builds a synthetic scores file in S3's format from
   the committed analysis matrix (numbers and ids; nothing is drawn or applied) with stated knobs, runs the readings
   script's `compute()` on it and names the sentence ids it must reach. The test module parametrises over the same
   fixtures. Every sentence id of plan section 6 is listed with the fixture that reaches it; S-P1 is unreachable by
   decision (the k = 2 arm is not run) and S4-1 is written by a separate session after Aravind reports (brief 33 B3).

2. Operating characteristics from Part 3's simulator (`stage3_b3_power_v3c.py`, its `load_world`, `instruments` and
   `draw_world`) through an adapter that writes one simulated world's item-level scores into the scores-file format, for
   both named instruments, at truth 0, the latent margin (`mult` 1.0 of the instrument's latent margin, `TRUTHS`) and
   1.5 x; seed 20261171 with stream tag 500 (Part 3's seed, a new tag; never a placement stream); 300 experiments per
   truth; the subset under the membership model "none" (unambiguous) and the full set under "zero" beside, named.
   Acceptance, fixed by brief 33: the carrier's P(excluded | 0) on the subset within 0.08 of Part 3's 0.68 at ICC 0.3,
   and P(present | 1.5 x) within 0.08 of 0.72; outside either, Stage A stops for a decision.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s3_dryrun.py fixtures | oc [--experiments 300] | report
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_s3_readings as rd  # noqa: E402

VERSION = "b3-s3-readings-dryrun/v0"
PROJECT = HERE.parents[1]
MATRIX = PROJECT / "work/stage3/b3/s3-analysis-matrix-v0.json"
OUT_JSON = PROJECT / "work/stage3/b3/s3-readings-dryrun-v0.json"
OUT_MD = PROJECT / "work/stage3/b3/s3-readings-dryrun-v0.md"
PARTS = PROJECT / "work/stage3/b3/s3-dryrun-parts"
OC_SEED, OC_TAG, OC_EXPERIMENTS = 20261171, 500, 300
OC_TOL = 0.08
OC_REF = {"P_excl_0": 0.68, "P_present_x1.5": 0.72}       # Part 3, the subset at T2+S2, ICC 0.3 (power-simulation-v3c.json)
OC_ICC = 0.3
ALL_SENTENCES = ["S-S0", "S-S1", "S-A1", "S-A2", "S-A3", "S-A4", "S-A5", "S-B1", "S-C1", "S-C2", "S-C3", "S-C3b", "S-C4", "S-C5", "S-C6",
                 "S-D1", "S-D2", "S-D3", "S-D4", "S-E1", "S-E2", "S-E3", "S-F1", "S-F2", "S-F3", "S-F4", "S-F5", "S-F6", "S-Fs1", "S-Fs2", "S-Fs3",
                 "S-G1", "S-H1", "S-H2", "S-I1", "S-I2", "S-J1", "S-K1", "S-K2", "S-K3", "S-K4", "S-L1", "S-L2", "S-M1", "S-M2", "S-M3", "S-M4",
                 "S-N1", "S-N2", "S-N3", "S-O1", "S-O2", "S-P0", "S-Q1", "S-Q2", "S-R1", "S-R2", "S4-2", "A1b-d", "A1b-provisional"]
UNREACHABLE = {"S-P1": "unreachable by decision: the k = 2 arm is not run (plan section 4.6, S2's note)",
               "S-I3": "no sentence (S-C1 names the case)",
               "S4-1": "written by a separate $0 session after Aravind reports his scores (brief 33 B3)",
               "S-Fscope": "a clause attached to S-F1 (reached with it)"}


# ── the synthetic world ────────────────────────────────────────────────────────────────────────────

def load_matrix() -> dict:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def default_spec() -> dict[str, Any]:
    """Per instrument: the excess per composition point (`beta`, score points), the item-level noise, the flag model
    (logit = base + slope x (C - 55) + line_w x (rater line max - 50)), the sham's mean shift below the quiet set."""
    inst = {k: {"beta": 0.0, "noise": 6.0, "base": -0.4, "slope": 0.0, "line_w": 0.0, "sham_shift": -25.0, "tri_mean": 45.0, "kimi_inter": 0.0, "unresolved_beta": None}
            for k in rd.INSTRUMENTS}
    return {"instruments": inst, "o_diff": {"full": 0.7, "controls": 0.2, "sham": 0.1}, "controls": {"tri_mean": 20.0, "flag_p": 0.1},
            "refuse": [], "stopped_cells": [], "line_const": None, "seed": 1}


def synthetic_scores(matrix: Mapping[str, Any], spec: Mapping[str, Any]) -> dict[str, Any]:
    """A scores file in S3's format from the matrix and the spec; every unit present unless `stopped_cells` names its cell
    (then the cell's rows are absent and the `stopped` record names them) or `refuse` names the unit."""
    rng = np.random.default_rng(spec["seed"])
    M = matrix["items"]
    refuse = {tuple(x) for x in spec["refuse"]}        # (item_id, view, judge, arm, role, placement)
    rows = []
    stopped = set(spec["stopped_cells"])
    for (view, judge), (n_item, n_line) in rd.EXPECTED.items():
        cell = f"{view}|{judge}"
        if cell in stopped:
            continue
        key = next((k for k, vj in rd.INSTRUMENTS.items() if vj == (view, judge)), None)
        sp = spec["instruments"][key] if key else None
        for iid, it in sorted(M.items()):
            reg = it["regime"]
            if view == "O_diff":
                p = spec["o_diff"]["full"] if reg == "candidate" else spec["o_diff"][reg + "s" if reg == "control" else reg]
                for pl in (1, 2):
                    f = bool(rng.random() < p)
                    sc = float(np.clip(rng.normal(60 if f else 30, 8), 0, 100))
                    rows.append(_row(iid, reg, "item", 0, pl, view, judge, sc, f, refuse))
                continue
            if reg == "candidate":
                C = it["composition"]
                k = it["readers"]["kimi"]["D_part_mean"]
                lines = [float(np.clip(rng.normal(sp["tri_mean"] + 0.1 * (it["line_scores"][j] - 50), sp["noise"]), 0, 100)) for j in range(3)]
                beta = sp["unresolved_beta"] if ("unresolved_stratum" in it["populations"] and sp.get("unresolved_beta") is not None) else sp["beta"]
                excess_true = beta * (C - 55) + sp["kimi_inter"] * (C - 55) * k
                tri_mu = max(lines) + excess_true
                for pl in (1, 2):
                    sc = float(np.clip(rng.normal(tri_mu, sp["noise"]), 0, 100))
                    logit = sp["base"] + sp["slope"] * (C - 55) + sp["line_w"] * (it["line_max"] - 50)
                    f = bool(rng.random() < 1 / (1 + np.exp(-logit)))
                    rows.append(_row(iid, reg, "item", 0, pl, view, judge, sc, f, refuse))
                if n_line:
                    for role in (1, 2, 3):
                        for pl in (1, 2):
                            sc = float(np.clip(rng.normal(lines[role - 1], 1.0), 0, 100)) if spec["line_const"] is None else float(spec["line_const"])
                            rows.append(_row(iid, reg, "line", role, pl, view, judge, sc, None, refuse))
            elif reg == "control":
                for pl in (1, 2):
                    sc = float(np.clip(rng.normal(spec["controls"]["tri_mean"], sp["noise"]), 0, 100))
                    f = bool(rng.random() < spec["controls"]["flag_p"])
                    rows.append(_row(iid, reg, "item", 0, pl, view, judge, sc, f, refuse))
                if n_line:
                    for role in (1, 2, 3):
                        for pl in (1, 2):
                            rows.append(_row(iid, reg, "line", role, pl, view, judge, float(np.clip(rng.normal(spec["controls"]["tri_mean"] - 5, sp["noise"]), 0, 100)), None, refuse))
            else:
                for pl in (1, 2):
                    sc = float(np.clip(rng.normal(sp["tri_mean"] + sp["sham_shift"], sp["noise"]), 0, 100))
                    f = bool(rng.random() < 0.05)
                    rows.append(_row(iid, reg, "item", 0, pl, view, judge, sc, f, refuse))
    out = {"version": "b3-s3-scores/synthetic", "rows": rows, "stopped": None}
    if stopped:
        out["stopped"] = {"reason": "fixture", "incomplete_rows": {c: {"scored_rows": 0, "of": sum(rd.EXPECTED[tuple(c.split('|'))])} for c in stopped}}
    return out


def _row(iid, reg, arm, role, pl, view, judge, sc, f, refuse) -> dict:
    refused = (iid, view, judge, arm, role, pl) in refuse
    return {"unit_id": f"{iid}:{arm}{role}:{pl}", "item_id": iid, "regime": reg, "arm": arm, "role": role, "placement": pl, "view": view, "judge": judge,
            "outcome": "refused" if refused else "scored", "score": None if refused else round(sc, 2), "flag": None if refused else f, "cache_label": f"s3:{view}:{iid}:{arm}{role}:{pl}"}


# ── fixtures ───────────────────────────────────────────────────────────────────────────────────────

def _spec(**kw) -> dict:
    sp = default_spec()
    for k, v in kw.items():
        if k in ("C", "S", "d1", "d2", "d3", "d4"):
            sp["instruments"][k].update(v)
        else:
            sp[k] = v
    return sp


def _all(**kw) -> dict:
    """The same knobs on every per-agent instrument."""
    return {k: dict(kw) for k in rd.INSTRUMENTS}


def _matrix_writer_constant(matrix, pop, writer="sonnet55"):
    m = copy.deepcopy(matrix)
    for i in m["populations"][pop]["ids"]:
        m["items"][i]["writer"] = writer
    return m


def _matrix_one_item_writer(matrix, pop):
    """A factor level held by one item in the population: every member Sonnet but one GLM."""
    m = copy.deepcopy(matrix)
    ids = m["populations"][pop]["ids"]
    for i in ids:
        m["items"][i]["writer"] = "sonnet55"
    m["items"][ids[0]]["writer"] = "glm53"
    return m


def _refuse_stratum(matrix, pop, cell_keys, which="pooled"):
    """Every item of one pooled stratum of `pop` refused under the named cells (an empty pooled stratum, (iii))."""
    ps = matrix["pooled_strata"][pop]
    docs = [d for d, s in ps.items() if s == which] or [sorted(set(ps.values()))[0]]
    ids = [i for i in matrix["populations"][pop]["ids"] if matrix["items"][i]["document"] in docs]
    return [[i, v, j, "item", 0, 1] for i in ids for (v, j) in cell_keys]


def fx_baseline(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sp["seed"] = 3
    return matrix, sp, {"S-S0", "S-A1", "S-A5", "S-D3", "S-E1", "S-F1", "S-Fs1", "S-G1", "S-I1", "S-J1", "S-L1", "S-M1", "S-M2", "S-M3", "S-M4",
                        "S-N1", "S-N2", "S-O1", "S-O2", "S-P0", "S-Q2", "S-R1", "S4-2", "S-K3", "S-K4"}, "beta 0 on every instrument: excluded, holds, confirmed"


def fx_present(matrix):
    sp = _spec(**_all(beta=1.2, noise=5.0))
    return matrix, sp, {"S-D1", "S-F3", "S-Fs1"}, "beta 1.2 per point (30 points over the span): present, falsified"


def fx_attenuated(matrix):
    sp = _spec(**_all(beta=0.35, noise=3.0))
    return matrix, sp, {"S-D2", "S-F2", "S-G1"}, "beta 0.35 per point (about 9 points): attenuated, partly missed"


def fx_inconclusive(matrix):
    sp = _spec(**_all(beta=0.35, noise=18.0))
    return matrix, sp, {"S-D4", "S-F4"}, "beta 0.35 per point with wide noise: the interval cannot tell zero from m_s (inconclusive)"


def fx_two_step_within(matrix):
    sp = _spec(**_all(beta=0.0, noise=4.0, base=-0.5, slope=0.14))
    return matrix, sp, {"S-E2", "S-F5"}, "form (a) excluded with form (b) present (bias-net lower bound above 0) on the carrier: the two-step conflict within an instrument"


def fx_two_step_across(matrix):
    sp = _spec(**_all(beta=0.0, noise=4.0))
    sp["instruments"]["S"].update(beta=1.5)
    return matrix, sp, {"S-F6"}, "the carrier excluded, the second named instrument present: a two-step conflict across instruments"


def fx_one_step_across(matrix):
    sp = _spec(**_all(beta=0.0, noise=4.0))
    sp["instruments"]["S"].update(beta=0.35, noise=3.0)
    return matrix, sp, {"S-F1", "S-Fs2"}, "the carrier excluded, the second attenuated: differs by one step, beside"


def fx_floor_carrier(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sp["instruments"]["C"].update(sham_shift=0.0)
    return matrix, sp, {"S-A2", "S-A1", "S-F1", "S-Fs3"}, "the carrier's sham drawn from the quiet distribution: the carrier at floor, the second leads as the fallback carrier"


def fx_floor_both(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0, sham_shift=0.0))
    return matrix, sp, {"S-A2", "S-A3"}, "both named instruments at floor: no verdict"


def fx_floor_b(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0, base=-3.0))
    return matrix, sp, {"S-A4", "S-E3", "S-L2", "S-R2"}, "form (b)'s floor failed: the quiet lone recall does not clear the sham's"


def fx_ceiling(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0, base=6.0))
    return matrix, sp, {"S-B1", "S-E3", "S-L2", "S-R2"}, "quiet lone recall above 0.85: form (b) past the ceiling"


def fx_fit_i_constant(matrix):
    m = _matrix_writer_constant(matrix, "subset")
    sp = _spec(**_all(beta=0.0, noise=5.0))
    return m, sp, {"S-C1"}, "fit failure (i): the writer constant on the subset; the reading steps down to the stratum"


def fx_subset_stratum_disagree(matrix):
    sp = _spec(**_all(beta=0.0, noise=4.0, unresolved_beta=2.5))
    return matrix, sp, {"S-I2"}, "the nine unresolved members carry a strong effect, the subset none: the subset and the stratum disagree (S-I2)"


def fx_fit_ii_replicates(matrix):
    m = _matrix_one_item_writer(matrix, "subset")
    sp = _spec(**_all(beta=0.0, noise=5.0))
    return m, sp, {"S-C1"}, "fit failure (ii): a factor level held by one item on the subset, so more than 10 percent of the 2,000 replicates are singular (property asserted)"


def fx_fit_iii_empty_stratum(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sp["refuse"] = _refuse_stratum(matrix, "subset", [("P_author_doc_iso", "opus48")])
    return matrix, sp, {"S-C1", "A1b-provisional"}, "fit failure (iii): every item of one pooled stratum of the subset refused under the carrier (an empty pooled stratum; the loss is above 10 percent)"


def fx_stratum_too(matrix):
    m = _matrix_writer_constant(matrix, "stratum")
    sp = _spec(**_all(beta=0.0, noise=5.0))
    return m, sp, {"S-C1", "S-C3", "S-C2", "S-H1"}, "the writer constant on the whole stratum: the carrier unfit on 17 and 26, the second takes the lead (S-C3), is unfit too, the third branch (S-H1)"


def fx_third_present(matrix):
    m = _matrix_writer_constant(matrix, "stratum")
    sp = _spec(**_all(beta=1.5, noise=5.0, slope=0.3))        # form (b) present too, so no two-step conflict blocks the full-set present
    return m, sp, {"S-H2"}, "as above with a full-set present: S-H2"


def fx_nothing_fits(matrix):
    m = copy.deepcopy(matrix)
    for i in m["populations"]["full"]["ids"]:
        m["items"][i]["writer"] = "sonnet55"
        m["items"][i]["replace_share"] = 0.5
    sp = _spec(**_all(beta=0.0, noise=5.0))
    return m, sp, {"S-C3b", "S-C4"}, "the writer and the replace share constant on the full set: nothing fits on any population (S-C3b, S-C4)"


def fx_c5_form_b_singular(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sp["line_const"] = 40.0
    return matrix, sp, {"S-C5"}, "the judge's singleton maximum constant: form (b)'s design singular (S-C5)"


def fx_c6_other_unfit(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sp["refuse"] = _refuse_stratum(matrix, "subset", [("P_author", "opus48")])
    return matrix, sp, {"S-C6", "S-Fs3"}, "the second named instrument loses a pooled stratum of the subset to refusals: unfit there while the carrier reads (S-C6)"


def fx_refused_component(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sid = matrix["populations"]["subset"]["ids"][0]
    sp["refuse"] = [[sid, "P_author_doc_iso", "opus48", "line", 2, 1]]
    return matrix, sp, {"S-F1"}, "one lone-line application refused under the carrier: that item not evaluable (n = 16 on the subset)"


def fx_stopped_lead(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sp["stopped_cells"] = ["P_author_doc_iso|opus48"]
    return matrix, sp, {"A1b-d", "S-A2", "S-F1", "S-Fs3"}, "the carrier's row not scored at a stop: treated as not passing its floor; the second leads"


def fx_stopped_second(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sp["stopped_cells"] = ["P_author|opus48"]
    return matrix, sp, {"A1b-d", "S-A2", "S-F1", "S-Fs3"}, "the second named instrument's row not scored at a stop: it drops out, named"


def fx_g1_fails(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sp["o_diff"] = {"full": 0.3, "controls": 0.1, "sham": 0.05}
    return matrix, sp, {"S-N3"}, "Opus 4.8's composed share below 0.65: G1 fails"


def fx_sq1(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0, base=-1.5, line_w=0.25))
    return matrix, sp, {"S-Q1"}, "flags driven by the rater's section-2 maximum: S-Q1"


def fx_k1(matrix):
    sp = _spec(**_all(beta=0.3, noise=3.0, kimi_inter=-1.2))
    return matrix, sp, {"S-K1"}, "the composition contrast falls with Kimi K3's D_part: S-K1"


def fx_k2(matrix):
    sp = _spec(**_all(beta=0.0, noise=3.0, kimi_inter=1.2))
    return matrix, sp, {"S-K2"}, "the composition contrast rises with D_part: S-K2"


def fx_own_drops(matrix):
    sp = _spec(**_all(beta=0.0, noise=5.0))
    sp["own_drops"] = {"n": 1, "ids": [matrix["populations"]["full"]["ids"][0]], "reasons": {"every listed draw tried was refused": 1}, "by_population": {"full": 1}}
    return matrix, sp, {"S-S1"}, "one own drop recorded: S-S1"


FIXTURES: dict[str, Callable] = {f.__name__[3:]: f for f in (
    fx_baseline, fx_present, fx_attenuated, fx_inconclusive, fx_two_step_within, fx_two_step_across, fx_one_step_across, fx_floor_carrier,
    fx_floor_both, fx_floor_b, fx_ceiling, fx_fit_i_constant, fx_subset_stratum_disagree, fx_fit_ii_replicates, fx_fit_iii_empty_stratum, fx_stratum_too, fx_third_present,
    fx_nothing_fits, fx_c5_form_b_singular, fx_c6_other_unfit, fx_refused_component, fx_stopped_lead, fx_stopped_second, fx_g1_fails, fx_sq1,
    fx_k1, fx_k2, fx_own_drops)}


def run_fixture(name: str, matrix: Mapping[str, Any]) -> dict[str, Any]:
    m, sp, expect, note = FIXTURES[name](matrix)
    scores = synthetic_scores(m, sp)
    R = rd.compute(m, scores, sp.get("own_drops"))
    ids = [s["id"] for s in R["sentences"]]
    prov = any(s["text"].startswith("provisional:") for s in R["sentences"])
    if prov:
        ids.append("A1b-provisional")
    got = set(ids)
    return {"fixture": name, "note": note, "expected": sorted(expect), "reached": sorted(got), "missing": sorted(expect - got),
            "ok": expect <= got, "cascade": {k: R["cascade"].get(k) for k in ("lead", "state", "step", "population", "instrument", "fallback")},
            "rows": len(scores["rows"]), "n_sentences": len(R["sentences"]), "R": R}


# ── operating characteristics through Part 3's simulator ──────────────────────────────────────────

def oc_world_to_scores(W: Mapping[str, Any], g: Mapping[str, Any], matrix: Mapping[str, Any]) -> dict[str, Any]:
    """The adapter: one drawn world's `s_tri`, `F`, `s_sing`, `s_sh`, `F_sh` per instrument into S3's scores-file rows for
    the two named instruments (every other cell absent and named in the stopped record, so the lock admits the file)."""
    ids = W["ids"]
    sham_ids = matrix["populations"]["sham"]["ids"]
    rows = []
    for key in rd.NAMED:
        view, judge = rd.INSTRUMENTS[key]
        name = "dossier_iso:opus48" if key == "C" else "P_author:opus48"
        d = g[name]
        if d["s_sh"].shape[0] != len(sham_ids):
            raise ValueError(f"sham n {d['s_sh'].shape[0]} differs from the matrix's {len(sham_ids)}")
        for i, iid in enumerate(ids):
            for pl in (1, 2):
                rows.append(_row(iid, "candidate", "item", 0, pl, view, judge, float(d["s_tri"][i, pl - 1]), bool(d["F"][i, pl - 1]), set()))
            for role in (1, 2, 3):
                for pl in (1, 2):
                    rows.append(_row(iid, "candidate", "line", role, pl, view, judge, float(d["s_sing"][i, role - 1]), None, set()))
        for i, iid in enumerate(sham_ids):
            for pl in (1, 2):
                rows.append(_row(iid, "sham", "item", 0, pl, view, judge, float(d["s_sh"][i, pl - 1]), bool(d["F_sh"][i, pl - 1]), set()))
    absent = [f"{v}|{j}" for (v, j) in rd.EXPECTED if (v, j) not in (rd.INSTRUMENTS["C"], rd.INSTRUMENTS["S"])]
    controls_absent = {f"{v}|{j}": {"scored_rows": 0, "of": 126 + 42} for (v, j) in (rd.INSTRUMENTS["C"], rd.INSTRUMENTS["S"])}
    stopped = {"reason": "operating-characteristics adapter: the two named instruments only, candidates and sham",
               "incomplete_rows": {**{c: {"scored_rows": 0, "of": sum(rd.EXPECTED[tuple(c.split('|'))])} for c in absent}, **controls_absent}}
    return {"version": "b3-s3-scores/oc-adapter", "rows": rows, "stopped": stopped}


_G: dict[str, Any] = {}


def _oc_one(task) -> dict[str, Any]:
    """One experiment: a world drawn on its own stream, written through the adapter, read by the script's own Instrument."""
    ti, mi, e, model, mult, pop = task
    W, dgps, betas, matrix, v3c = _G["W"], _G["dgps"], _G["betas"], _G["matrix"], _G["v3c"]
    rng = np.random.default_rng([OC_SEED, OC_TAG, ti, mi, e])
    f = v3c.membership_factor(rng, W["member"], model)
    g = v3c.draw_world(rng, W, dgps, betas, "T2+S2", f, mult)
    scores = oc_world_to_scores(W, g, matrix)
    out = {}
    for k in rd.NAMED:
        I = rd.Instrument(k, matrix, scores["rows"], True)
        sham = {i: s for i, s in I.summary.items() if I.items[i]["regime"] == "sham"}
        fl = I.floor(sham)
        r = I.read(pop, fl["b"]["pass"])
        la = "floor" if not fl["a"]["pass"] else (r["a"]["contrast"]["label"] if r["a"].get("fit_ok") else "unfit")
        b = r.get("b", {})
        lb = b.get("not_read") or (b["contrast"]["label"] if b.get("fit_ok") else "unfit")
        out[k] = {"a": la, "b": lb, "floor_a": fl["a"]["pass"]}
    return out


def oc_run(experiments: int = OC_EXPERIMENTS, quick: bool = False, procs: int = 1) -> dict[str, Any]:
    import stage3_b3_power_v3c as v3c
    matrix = load_matrix()
    W = v3c.load_world(PROJECT, "pair")
    if W["ids"] != matrix["populations"]["full"]["ids"] and sorted(W["ids"]) != sorted(matrix["populations"]["full"]["ids"]):
        raise SystemExit("the simulator's net quiet set differs from the matrix's full set")
    inst = v3c.instruments(PROJECT, W)
    betas = {k: inst[k]["latent_margin"] for k in v3c.INSTS}
    dgps = {k: inst[k]["dgp"][str(OC_ICC)] for k in v3c.INSTS}
    truths = (("null", 0.0), ("margin", 1.0), ("x1.5", 1.5))
    models = (("subset", "none"), ("full", "zero"))
    if quick:
        rd.REPLICATES = 200
    t0 = time.monotonic()
    out: dict[str, Any] = {"seed": OC_SEED, "tag": OC_TAG, "icc": OC_ICC, "experiments": experiments, "replicates": rd.REPLICATES, "layout": "T2+S2", "cells": {},
                           "seeding": "one stream per experiment: default_rng([20261171, 500, truth index, model index, experiment index])"}
    _G.update(W=W, dgps=dgps, betas=betas, matrix=matrix, v3c=v3c)
    for ti, (truth, mult) in enumerate(truths):
        for mi, (pop, model) in enumerate(models):
            tasks = [(ti, mi, e, model, mult, pop) for e in range(experiments)]
            if procs > 1:
                import multiprocessing as mp
                with mp.get_context("fork").Pool(procs) as pool:
                    res = pool.map(_oc_one, tasks, chunksize=4)
            else:
                res = [_oc_one(t) for t in tasks]
            tally: dict[str, Counter] = {k: Counter() for k in rd.NAMED}
            tally_b: dict[str, Counter] = {k: Counter() for k in rd.NAMED}
            floors = Counter()
            for r in res:
                for k in rd.NAMED:
                    tally[k][r[k]["a"]] += 1
                    tally_b[k][r[k]["b"]] += 1
                    floors[f"{k}|a|{r[k]['floor_a']}"] += 1
            cell = f"{truth}|{pop}|{model}"
            out["cells"][cell] = {"truth": truth, "mult": mult, "population": pop, "membership_model": model,
                                  "form_a": {k: {o: tally[k][o] / experiments for o in ("excluded", "attenuated", "present", "inconclusive", "floor", "unfit")} for k in rd.NAMED},
                                  "form_b": {k: {o: tally_b[k][o] / experiments for o in ("excluded", "attenuated", "present", "inconclusive", "floor", "ceiling", "unfit")} for k in rd.NAMED},
                                  "floor_a": dict(floors), "seconds": round(time.monotonic() - t0)}
            print(json.dumps({cell: out["cells"][cell]["form_a"]["C"]}), flush=True)
    c = out["cells"]
    acc = {"P_excl_0_subset_C": c["null|subset|none"]["form_a"]["C"]["excluded"], "P_present_x1.5_subset_C": c["x1.5|subset|none"]["form_a"]["C"]["present"],
           "reference": OC_REF, "tolerance": OC_TOL}
    acc["accepted"] = abs(acc["P_excl_0_subset_C"] - OC_REF["P_excl_0"]) <= OC_TOL and abs(acc["P_present_x1.5_subset_C"] - OC_REF["P_present_x1.5"]) <= OC_TOL
    out["acceptance"] = acc
    out["wall_seconds"] = round(time.monotonic() - t0)
    return out


# ── the report ─────────────────────────────────────────────────────────────────────────────────────

def _fixture_one(name: str, matrix=None) -> dict[str, Any]:
    r = run_fixture(name, matrix if matrix is not None else _G["matrix"])
    r.pop("R")
    return r


def fixtures_part(procs: int = 1) -> dict[str, Any]:
    matrix = load_matrix()
    t0 = time.monotonic()
    res = {}
    names = list(FIXTURES)
    if procs > 1:
        import multiprocessing as mp
        _G["matrix"] = matrix
        with mp.get_context("fork").Pool(procs) as pool:
            outs = pool.map(_fixture_one, names, chunksize=1)
    else:
        outs = [_fixture_one(n, matrix) for n in names]
    for name, r in zip(names, outs):
        res[name] = r
        print(json.dumps({name: {"ok": r["ok"], "missing": r["missing"], "cascade": r["cascade"]}}), flush=True)
    reach = {}
    for sid in ALL_SENTENCES:
        reach[sid] = [n for n, r in res.items() if sid in r["reached"]]
    return {"fixtures": res, "reachability": reach, "unreachable": UNREACHABLE, "all_ok": all(r["ok"] for r in res.values()),
            "unreached": [s for s, f in reach.items() if not f], "wall_seconds": round(time.monotonic() - t0),
            "matrix_sha256": hashlib.sha256(MATRIX.read_bytes()).hexdigest(), "readings_script_sha256": hashlib.sha256((HERE / "stage3_b3_s3_readings.py").read_bytes()).hexdigest()}


def render_md(fx: Mapping[str, Any], oc: Mapping[str, Any] | None) -> str:
    L = ["# S3 readings script: the dry run before any draw (brief 33 A2; counts only)", ""]
    L.append(f"Readings script `work/checks/stage3_b3_s3_readings.py` {fx['readings_script_sha256'][:8]}; matrix {fx['matrix_sha256'][:8]}. Fixtures run in {fx['wall_seconds']} s.")
    L.append("")
    L.append("## 1. Reachability by constructed fixtures")
    L.append("")
    L.append("| fixture | knobs | expected ids | reached | missing |")
    L.append("|---|---|---|---|---|")
    for n, r in fx["fixtures"].items():
        L.append(f"| {n} | {r['note']} | {', '.join(r['expected'])} | {'yes' if r['ok'] else 'NO'} ({r['n_sentences']} sentences) | {', '.join(r['missing']) or '—'} |")
    L.append("")
    L.append("### Every sentence id of section 6 and the fixture that reaches it")
    L.append("")
    L.append("| id | reached by |")
    L.append("|---|---|")
    for sid, fs in fx["reachability"].items():
        L.append(f"| {sid} | {', '.join(fs) if fs else 'NOT REACHED'} |")
    for sid, why in fx["unreachable"].items():
        L.append(f"| {sid} | {why} |")
    L.append("")
    L.append(f"All fixtures reach their ids: {fx['all_ok']}. Ids not reached by any fixture: {fx['unreached'] or 'none'}.")
    L.append("")
    L.append("## 2. Operating characteristics from Part 3's simulator through the adapter")
    L.append("")
    if not oc:
        L.append("not run yet")
    else:
        L.append(f"Seed {oc['seed']} with stream tag {oc['tag']}; ICC {oc['icc']}; layout {oc['layout']}; {oc['experiments']} experiments per truth; "
                 f"{oc['replicates']} replicates per fit; wall time {oc['wall_seconds']} s.")
        L.append("")
        L.append("| truth | population | membership model | instrument | form (a): excluded / attenuated / present / inconclusive / floor / unfit | form (b): excluded / attenuated / present / inconclusive / floor / ceiling / unfit |")
        L.append("|---|---|---|---|---|---|")
        for cell, c in oc["cells"].items():
            for k in rd.NAMED:
                a, b = c["form_a"][k], c["form_b"][k]
                L.append(f"| {c['truth']} | {c['population']} | {c['membership_model']} | {k} | "
                         + " / ".join(f"{a[o]:.2f}" for o in ("excluded", "attenuated", "present", "inconclusive", "floor", "unfit")) + " | "
                         + " / ".join(f"{b[o]:.2f}" for o in ("excluded", "attenuated", "present", "inconclusive", "floor", "ceiling", "unfit")) + " |")
        acc = oc["acceptance"]
        L.append("")
        L.append(f"Acceptance (brief 33 A2, fixed before the run; three Monte Carlo SE at 300): the carrier's P(excluded | 0) on the subset {acc['P_excl_0_subset_C']:.3f} "
                 f"against Part 3's {acc['reference']['P_excl_0']} (ICC 0.3), P(present | 1.5 x) {acc['P_present_x1.5_subset_C']:.3f} against {acc['reference']['P_present_x1.5']}; "
                 f"tolerance ± {acc['tolerance']}: **{'ACCEPTED' if acc['accepted'] else 'OUTSIDE THE TOLERANCE: Stage A stops for a decision'}**.")
    L.append("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=("fixtures", "oc", "report"))
    ap.add_argument("--experiments", type=int, default=OC_EXPERIMENTS)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--procs", type=int, default=1)
    ns = ap.parse_args(argv)
    PARTS.mkdir(parents=True, exist_ok=True)
    if ns.mode == "fixtures":
        fx = fixtures_part(ns.procs)
        (PARTS / "fixtures.json").write_text(json.dumps(fx, indent=1, default=rd._json_default) + "\n")
        print(json.dumps({"all_ok": fx["all_ok"], "unreached": fx["unreached"], "wall_seconds": fx["wall_seconds"]}))
        return 0 if fx["all_ok"] and not fx["unreached"] else 1
    if ns.mode == "oc":
        oc = oc_run(ns.experiments, ns.quick, ns.procs)
        (PARTS / ("oc-quick.json" if ns.quick else "oc.json")).write_text(json.dumps(oc, indent=1, default=rd._json_default) + "\n")
        print(json.dumps(oc["acceptance"], indent=1))
        return 0 if oc["acceptance"]["accepted"] else 1
    fx = json.loads((PARTS / "fixtures.json").read_text())
    ocp = PARTS / "oc.json"
    oc = json.loads(ocp.read_text()) if ocp.exists() else None
    rep = {"version": VERSION, "fixtures": {k: v for k, v in fx.items()}, "oc": oc}
    OUT_JSON.write_text(json.dumps(rep, indent=1, default=rd._json_default) + "\n")
    OUT_MD.write_text(render_md(fx, oc))
    print(f"wrote {OUT_MD.relative_to(PROJECT)} and .json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
