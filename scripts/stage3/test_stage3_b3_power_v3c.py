"""Tests for stage3_b3_power_v3c.py (brief 20 Part 3): the membership models, the pooling rule, form (a) for a stratum
population, the cascade, the fingerprint join, round 2's n rule, the report's gate and verdict logic on constructed
records, and, on the files on disk, Step 0's net populations and Part 2's m_s reproduced. No network, nothing sealed.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_power_v3c.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_power_v3 as pv  # noqa: E402
import stage3_b3_power_v3c as P  # noqa: E402

ON_DISK = (P.PROJECT / P.STRATUM).exists() and (P.PROJECT / P.DRYRUN).exists() and (P.PROJECT / P.V3B).exists()


def test_latent_rate_and_membership_models():
    assert P.latent_rate(0.69) == pytest.approx((0.69 * 78 - 28) / 50)
    assert P.latent_rate(0.46) == pytest.approx((0.46 * 78 - 28) / 50)
    assert P.latent_rate(0.2) == 0.0 and P.latent_rate(1.0) == 1.0
    member = np.array([True, False, False, True, False])
    rng = np.random.default_rng(1)
    assert P.membership_factor(rng, member, "none").tolist() == [1, 1, 1, 1, 1]
    assert P.membership_factor(rng, member, "zero").tolist() == [1, 0, 0, 1, 0]
    assert P.membership_factor(rng, member, "small").tolist() == [1, P.SMALL, P.SMALL, 1, P.SMALL]
    f = np.array([P.membership_factor(rng, member, "latent69") for _ in range(4000)])
    assert (f[:, member] == 1).all() and set(np.unique(f[:, ~member])) <= {0.0, 1.0}
    assert f[:, ~member].mean() == pytest.approx(P.latent_rate(0.69), abs=0.02)


def test_pooling_rule_merges_documents_under_four_members():
    doc = np.array([0, 0, 0, 0, 1, 1, 1, 2, 3, 3, 3, 3])
    s = P.pooled_strata(doc)
    assert sorted(np.bincount(s).tolist()) == [4, 4, 4]
    assert s[4] == s[7] and s[0] != s[4] and s[8] != s[4]
    assert len(np.unique(P.pooled_strata(np.array([0, 1, 2])))) == 1


def test_form_a_strat_recovers_the_slope_and_marks_a_constant_covariate_unfit():
    rng = np.random.default_rng(3)
    n = 400
    C = rng.uniform(20, 90, n)
    gap, sonnet, edit = rng.uniform(0, 20, n), (rng.random(n) < 0.5).astype(float), rng.choice([0, 1 / 3, 2 / 3, 1], n)
    excess = 0.8 * C + 0.1 * gap + rng.normal(0, 3, n)
    wt = pv.bootstrap_weights(rng, n, 300)
    a = P.form_a_strat(C, gap, sonnet, edit, excess, 10.0, wt)
    assert a["fit_ok"] and a["75v50"]["point"] == pytest.approx(20.0, abs=1.0) and a["75v50"]["outcome"] == "present"
    flat = P.form_a_strat(C, gap, np.ones(n), edit, excess, 10.0, wt)
    assert not flat["fit_ok"] and flat["75v50"]["outcome"] == "unfit"


def test_form_a_strat_unfit_when_replicates_lose_a_covariate():
    # one Sonnet item among eleven: about a third of the replicates drop it, a constant writer column
    rng = np.random.default_rng(4)
    n = 11
    C, gap, edit = rng.uniform(20, 90, n), rng.uniform(0, 20, n), rng.choice([0, 1 / 3, 2 / 3, 1], n)
    sonnet = np.zeros(n); sonnet[0] = 1
    a = P.form_a_strat(C, gap, sonnet, edit, rng.normal(0, 3, n), 10.0, pv.bootstrap_weights(rng, n, 400))
    assert not a["fit_ok"] and a["failed_share"] > pv.NONCONV_MAX


def test_cascade_order_and_step_down():
    assert P.cascade_order(False, True, True) == ["full"]
    assert P.cascade_order(True, True, True) == ["subset", "stratum", "third"]
    assert P.cascade_order(True, False, True) == ["stratum", "third"]
    assert P.cascade_order(True, False, False) == ["third"]
    per = {"full": {"verdict": "present", "carrier_a": "present"}, "subset": {"verdict": "excluded", "carrier_a": "floor"},
           "stratum": {"verdict": "attenuated", "carrier_a": "attenuated"}}
    assert P.cascade_land(["subset", "stratum", "third"], per, True) == ("stratum", "attenuated")
    per["stratum"]["carrier_a"] = "unfit"
    assert P.cascade_land(["subset", "stratum", "third"], per, True) == ("third", "present")
    assert P.cascade_land(["subset", "stratum", "third"], per, False) == ("third", "inconclusive")
    per["full"]["verdict"] = "excluded"
    assert P.cascade_land(["third"], per, True) == ("third", "inconclusive")       # excluded is not issued there
    assert P.cascade_land(["full"], per, False) == ("full", "excluded")


def test_fingerprint_join_pairs_shared_keys_in_time_order():
    recs = [{"input_tokens": 10, "output_tokens": 5, "cost": 0.1, "t": 100.0},
            {"input_tokens": 10, "output_tokens": 5, "cost": 0.2, "t": 50.0},
            {"input_tokens": 7, "output_tokens": 3, "cost": 0.3, "t": 70.0},
            {"input_tokens": 9, "output_tokens": 9, "cost": 0.4, "t": 80.0}]
    export = [{"tokens_prompt": 10, "tokens_completion": 5, "cost": 0.1, "t": 95.0},
              {"tokens_prompt": 10, "tokens_completion": 5, "cost": 0.2, "t": 45.0},
              {"tokens_prompt": 7, "tokens_completion": 3, "cost": 0.3, "t": 69.0}]
    J = P.fingerprint_join(recs, export)
    assert J["match"] == {1: 1, 0: 0, 2: 2} and J["matched"] == 3 and J["records"] == 4
    assert J["ambiguous_keys"] == 1 and J["ambiguous_records"] == 2 and J["cost_agrees"] == 3 and J["time_order_violations"] == 0


def test_round2_n_is_the_first_grid_value_from_which_every_larger_one_is_readable():
    ok = {"P_excl_0": 0.9, "P_excl_margin": 0.0, "P_lb_0": 0.03}
    bad = {"P_excl_0": 0.5, "P_excl_margin": 0.0, "P_lb_0": 0.03}
    grid = (10, 20, 30, 40)
    t = {}
    for n, g in zip(grid, (ok, bad, ok, ok)):
        for icc in pv.ICCS:
            t[f"m|{icc}|{n}"] = g
    assert P.r2_min_n(t, "m", grid) == {"n": 30, "readable_from": 30}
    for icc in pv.ICCS:
        t[f"m|{icc}|40"] = bad
    assert P.r2_min_n(t, "m", grid)["n"] is None


def _rec(a="excluded", fa=True, b="excluded", blo=-0.1, aok=True):
    return {"fa": fa, "fb": True, "a": a, "ap": 0.0, "alo": -1.0, "ahi": 1.0, "aok": aok, "rq": 0.5,
            "b": b, "bp": 0.0, "blo": blo, "bok": True, "ceil": False}


def _cells(null_a, margin_a, x15_a, n=10):
    cells = {}
    for icc in pv.ICCS:
        for truth, model, oc in (("null", "none", null_a), ("margin", "none", margin_a), ("x1.5", "none", x15_a),
                                 ("margin", "zero", null_a)):
            rows = []
            for i in range(n):
                r = {}
                for inst in P.INSTS:
                    for pop in P.POPS:
                        r[f"{inst}|{pop}"] = _rec(oc[i % len(oc)], b=oc[i % len(oc)], blo=0.2 if oc[i % len(oc)] == "present" else -0.1)
                    for pop in P.STRAT_POPS:
                        r[f"{P.CARRIER}|{pop}|nopool"] = _rec(oc[i % len(oc)])
                rows.append(r)
            cells[f"pair|{P.ADOPTED}|{icc}|{truth}|{model}"] = rows
    return cells


def test_gate_and_combined_verdict_on_constructed_records():
    cells = _cells(["excluded"], ["attenuated", "present"], ["present"])
    g = P.instrument_summary(cells, "pair", P.ADOPTED, P.CARRIER, "subset", "none")
    assert g["P_excl_0"] == 1.0 and g["P_excl_margin"] == 0.0 and g["P_lb_0"] == 0.0 and g["P_present_x1.5"] == 1.0
    assert g["readable"] and g["fit_rate"] == 1.0 and g["read_rate"] == 1.0 and P.passes(g, P.FIT_BAR)
    v = P.verdict_summary(cells, "pair", P.ADOPTED, "subset", "none", True)
    assert v["P_holds_0"] == 1.0 and v["P_holds_margin"] == 0.0 and v["P_falsified_margin"] == 0.5
    # the full set under the zero model reads like the null here, so the switch fires
    vz = P.verdict_summary(cells, "pair", P.ADOPTED, "full", "zero", True)
    assert vz["P_holds_margin"] == 1.0 > P.SWITCH_BOUND
    floor = _cells(["excluded"], ["attenuated"], ["present"])
    for rows in floor.values():
        for r in rows:
            r[f"{P.CARRIER}|stratum"]["fa"] = False
    gs = P.instrument_summary(floor, "pair", P.ADOPTED, P.CARRIER, "stratum", "none")
    assert gs["read_rate"] == 0.0 and not P.passes(gs, P.FIT_BAR_BESIDE)
    oc = P.cascade_oc(floor, "pair", P.ADOPTED, ["stratum", "third"], "none", False, {p: True for p in P.POPS})
    assert oc["branch_null"]["third"] == 1.0 and oc["P_excl_0"] == 0.0


# ── on the files on disk (ids and counts only) ─────────────────────────────────

@pytest.mark.skipif(not ON_DISK, reason="brief 25's, brief 26's or Part 2's outputs are not on disk")
def test_step0_net_populations_under_the_pair_rule_and_the_literal_count():
    W = P.load_world(P.PROJECT, "pair")
    d = W["describe"]
    assert {p: d[p]["n"] for p in P.POPS} == {"full": 73, "stratum": 26, "subset": 17, "strict": 20}
    assert W["n_sham"] == 22 and W["n_controls"] == 21 and len(W["drops"]) == 8
    assert d["stratum"]["document_counts"] == [6, 6, 6, 4, 3, 1] and d["stratum"]["strata_pooled"] == [6, 6, 6, 4, 4]
    assert d["subset"]["by_writer"] == {"sonnet55": 11, "glm53": 6} and d["subset"]["strata_pooled"] == [7, 6, 4]
    Wl = P.load_world(P.PROJECT, "literal")
    assert {p: Wl["describe"][p]["n"] for p in P.POPS} == {"full": 77, "stratum": 27, "subset": 18, "strict": 21}
    assert Wl["n_sham"] == 23 and Wl["n_controls"] == 22


@pytest.mark.skipif(not ON_DISK, reason="Part 2's outputs are not on disk")
def test_part2_calibration_reproduces_the_pinned_m_s():
    W = P.load_world(P.PROJECT, "pair")
    inst = P.instruments(P.PROJECT, W)
    assert inst[P.CARRIER]["m_s_reproduced"] == pytest.approx(18.224650828480566, abs=1e-9)
    assert inst[P.SECOND]["m_s_reproduced"] == pytest.approx(19.36678769083121, abs=1e-9)


@pytest.mark.skipif(not ON_DISK, reason="Part 2's outputs are not on disk")
def test_one_world_reads_every_population_on_both_instruments():
    W = P.load_world(P.PROJECT, "pair")
    inst = P.instruments(P.PROJECT, W)
    dgps = {k: inst[k]["dgp"]["0.3"] for k in P.INSTS}
    r = P.run_world(np.random.default_rng(9), P._slim(W), dgps, {k: inst[k]["latent_margin"] for k in P.INSTS},
                    {k: inst[k]["m_s"] for k in P.INSTS}, "T1+S1", "zero", 1.0, 60)
    assert set(r) == {f"{i}|{p}" for i in P.INSTS for p in P.POPS} | {f"{P.CARRIER}|{p}|nopool" for p in P.STRAT_POPS}
    assert all(r[k]["a"] in ("excluded", "attenuated", "present", "inconclusive", "unfit") for k in r)
    assert all("b" in r[f"{i}|{p}"] for i in P.INSTS for p in P.POPS)
