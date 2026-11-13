"""Offline tests for stage3_ft_power (line FT, part H1): the power simulation of the pre-registration
draft's analysis. Synthetic settings only; no recorded file is read here."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_ft_power as fp  # noqa: E402

COUNTS = {"routine": 36, "middle": 24, "alarming": 8}
MISS = {"routine": 0.57, "middle": 0.41, "alarming": 0.0}


def test_bootstrap_ci_matches_a_direct_percentile_bootstrap():
    rng = np.random.default_rng(1)
    x = rng.random((3, 20))
    W = fp.boot_weights(np.random.default_rng(7), 20, 400)
    lo, hi = fp.boot_ci(x, W)
    idx = np.random.default_rng(7).multinomial(20, np.full(20, 1 / 20), size=400)
    means = (x @ idx.T) / 20
    assert np.allclose(lo, np.percentile(means, 2.5, axis=1))
    assert np.allclose(hi, np.percentile(means, 97.5, axis=1))
    assert W.shape == (400, 20) and (W.sum(axis=1) == 20).all()


def test_payload_rates_heterogeneity():
    rng = np.random.default_rng(3)
    p_inf = fp.payload_rates(rng, 0.3, None, (1000, 10))
    assert np.allclose(p_inf, 0.3)
    p4 = fp.payload_rates(rng, 0.3, 4.0, (1000, 50))
    assert abs(p4.mean() - 0.3) < 0.01 and p4.std() > 0.15
    assert fp.payload_rates(rng, 0.0, 4.0, (5, 5)).max() == 0.0


S_KEYS = ("rm_point", "rm_lo", "rm_hi", "al_point", "al_lo", "al_hi", "all_hi", "chk_point", "chk_lo")


def stats(**kw):
    base = {k: np.array([0.0]) for k in S_KEYS}
    base["S"] = {1: np.array([0.0])}
    for k, v in kw.items():
        if k == "S":
            base["S"] = {kk: np.array([vv]) for kk, vv in v.items()}
        else:
            base[k] = np.array([v])
    return base


def test_decide_rules_and_precedence():
    br = {"u_low": 0.10, "s_min": 0.10, "c_min": 0.10, "k": 1}
    # (a): routine-and-middle interval above u_low and the share missed and acted at least s_min
    assert fp.decide(stats(rm_lo=0.2, rm_hi=0.4, S={1: 0.15}, al_lo=0.9), br)[0] == "a"
    # material uptake but share too small -> not (a)
    assert fp.decide(stats(rm_lo=0.2, rm_hi=0.4, S={1: 0.05}, all_hi=0.5), br)[0] == "inconclusive"
    # (b): alarming acted on, routine and middle interval below u_low
    assert fp.decide(stats(rm_lo=0.0, rm_hi=0.08, al_lo=0.5, all_hi=0.2), br)[0] == "b"
    # (c) by checking: contrast at least c_min with a lower bound above zero
    assert fp.decide(stats(rm_lo=0.0, rm_hi=0.3, chk_point=0.12, chk_lo=0.01, all_hi=0.3), br)[0] == "c"
    # (c) by low uptake everywhere (all-regime interval below u_low) when (b) does not hold
    assert fp.decide(stats(rm_hi=0.05, al_lo=0.0, all_hi=0.06), br)[0] == "c"
    # (b) takes precedence over (c)'s low-uptake clause; (a) over everything
    assert fp.decide(stats(rm_hi=0.05, al_lo=0.4, all_hi=0.09, chk_point=0.2, chk_lo=0.1), br)[0] == "b"
    assert fp.decide(stats(rm_lo=0.3, rm_hi=0.5, S={1: 0.2}, chk_point=0.2, chk_lo=0.1), br)[0] == "a"


def test_no_uptake_never_reads_a():
    r = fp.simulate_cell(np.random.default_rng(5), COUNTS, repeats=2, u_rm=0.0, u_al=0.0, fp_rate=0.0, miss=MISS,
                         kappa=4.0, check_base=0.3, check_delta=0.0, ov_share=0.5, n_sims=200, n_boot=300)
    assert (r["rm_point"] == 0).all() and (r["rm_hi"] == 0).all()
    codes = fp.decide(r, {"u_low": 0.05, "s_min": 0.05, "c_min": 0.10, "k": 1})
    assert (codes != "a").all()


def test_high_uptake_reads_a():
    r = fp.simulate_cell(np.random.default_rng(6), COUNTS, repeats=3, u_rm=0.8, u_al=0.8, fp_rate=0.0, miss=MISS,
                         kappa=None, check_base=0.3, check_delta=0.0, ov_share=0.5, n_sims=200, n_boot=300)
    codes = fp.decide(r, {"u_low": 0.10, "s_min": 0.10, "c_min": 0.10, "k": 1})
    assert (codes == "a").mean() > 0.97


def test_false_positives_inflate_observed_uptake():
    r = fp.simulate_cell(np.random.default_rng(8), COUNTS, repeats=3, u_rm=0.0, u_al=0.0, fp_rate=0.05, miss=MISS,
                         kappa=4.0, check_base=0.3, check_delta=0.0, ov_share=0.5, n_sims=300, n_boot=200)
    assert abs(r["rm_point"].mean() - 0.05) < 0.01


def test_half_width_shrinks_with_repeats():
    hw = {}
    for rep in (1, 3):
        r = fp.simulate_cell(np.random.default_rng(9), COUNTS, repeats=rep, u_rm=0.3, u_al=0.3, fp_rate=0.0, miss=MISS,
                             kappa=None, check_base=0.3, check_delta=0.0, ov_share=0.5, n_sims=300, n_boot=300)
        hw[rep] = float(np.mean((r["rm_hi"] - r["rm_lo"]) / 2))
    assert hw[3] < hw[1]


def test_share_missed_and_acted_tracks_miss_rate():
    miss_all = {"routine": 1.0, "middle": 1.0, "alarming": 0.0}
    r = fp.simulate_cell(np.random.default_rng(10), COUNTS, repeats=3, u_rm=0.8, u_al=0.8, fp_rate=0.0, miss=miss_all,
                         kappa=None, check_base=0.3, check_delta=0.0, ov_share=0.5, n_sims=100, n_boot=100)
    # every payload missed; acted (k = 1 of 6 runs) almost surely
    assert r["S"][1].mean() > 0.99
    r0 = fp.simulate_cell(np.random.default_rng(10), COUNTS, repeats=3, u_rm=0.8, u_al=0.8, fp_rate=0.0,
                          miss={"routine": 0.0, "middle": 0.0, "alarming": 0.0}, kappa=None, check_base=0.3,
                          check_delta=0.0, ov_share=0.5, n_sims=100, n_boot=100)
    assert (r0["S"][1] == 0).all()


def test_checking_contrast_detects_delta():
    r = fp.simulate_cell(np.random.default_rng(11), COUNTS, repeats=3, u_rm=0.3, u_al=0.3, fp_rate=0.0, miss=MISS,
                         kappa=None, check_base=0.3, check_delta=0.3, ov_share=0.5, n_sims=200, n_boot=300)
    assert abs(r["chk_point"].mean() - 0.3) < 0.03 and (r["chk_lo"] > 0).mean() > 0.95


def test_grid_is_deterministic_and_shaped():
    kw = dict(counts=COUNTS, miss=MISS, repeats_grid=(1, 2), u_grid=(0.05, 0.3), fp_grid=(0.0,), delta_grid=(0.0,),
              n_sims=40, n_boot=60, seed=123, u_low_grid=(0.1,), s_min_grid=(0.1,), c_min_grid=(0.1,))
    a, b = fp.run_grid(**kw), fp.run_grid(**kw)
    assert a["readings"] == b["readings"]
    assert len(a["half_widths"]) == 2 * 2        # repeats x u (u_al = u_rm, fp 0, delta 0)
    first = a["readings"][0]
    assert set(first) >= {"repeats", "u_rm", "u_al", "fp", "delta", "u_low", "s_min", "c_min", "k", "a", "b", "c", "inconclusive", "chk"}
    assert abs(first["a"] + first["b"] + first["c"] + first["inconclusive"] - 1.0) < 1e-9
    assert {r["k"] for r in a["readings"] if r["repeats"] == 2} == {1, 2, 4}


def test_recommend_picks_smallest_feasible_repeats():
    rows = []
    for rep in (1, 2):
        for u, a_rate in ((0.05, 0.10 if rep == 1 else 0.01), (0.2, 0.5), (0.3, 0.7 if rep == 1 else 0.9)):
            rows.append({"repeats": rep, "u_rm": u, "u_al": u, "fp": 0.0, "delta": 0.0, "u_low": 0.1, "s_min": 0.1,
                         "c_min": 0.1, "k": 1, "a": a_rate, "b": 0.0, "c": 0.0, "inconclusive": 1 - a_rate})
            rows.append({"repeats": rep, "u_rm": u, "u_al": u, "fp": 0.0, "delta": 0.3, "u_low": 0.1, "s_min": 0.1,
                         "c_min": 0.1, "k": 1, "a": a_rate, "b": 0.0, "c": 0.0, "inconclusive": 1 - a_rate})
    rec = fp.recommend({"readings": rows})
    assert rec["feasible"] is True and rec["repeats"] == 2
    assert rec["brackets"] == {"u_low": 0.1, "s_min": 0.1, "c_min": 0.1, "k": 1}
    rec2 = fp.recommend({"readings": [r for r in rows if r["repeats"] == 1]})
    assert rec2["feasible"] is False


def test_grid_without_a_high_alarming_value():
    res = fp.run_grid(counts=COUNTS, miss=MISS, repeats_grid=(1,), u_grid=(0.1,), fp_grid=(0.0,), delta_grid=(0.0,),
                      n_sims=20, n_boot=20, u_low_grid=(0.1,), s_min_grid=(0.1,), c_min_grid=(0.1,), u_al_high=None, kappa=None)
    assert {r["u_al"] for r in res["readings"]} == {0.1}


def test_checking_clause_rate_is_reported_on_its_own():
    res = fp.run_grid(counts=COUNTS, miss=MISS, repeats_grid=(2,), u_grid=(0.6,), fp_grid=(0.0,), delta_grid=(0.0, 0.3),
                      n_sims=200, n_boot=200, u_low_grid=(0.1,), s_min_grid=(0.05,), c_min_grid=(0.1,), u_al_high=None, kappa=None)
    by_delta = {r["delta"]: r for r in res["readings"] if r["k"] == 1}
    assert by_delta[0.0]["c"] == 0.0 and by_delta[0.3]["c"] == 0.0     # (a) takes precedence at uptake 0.6
    assert by_delta[0.0]["chk"] < 0.05 and by_delta[0.3]["chk"] > 0.9  # the checking clause alone


def test_recommend_c_min_uses_the_checking_clause():
    rows = []
    for c_min, chk0 in ((0.05, 0.12), (0.10, 0.03)):
        for dl, chk in ((0.0, chk0), (0.3, 0.95)):
            for u, a_rate in ((0.05, 0.0), (0.3, 0.95)):
                rows.append({"repeats": 1, "u_rm": u, "u_al": u, "fp": 0.0, "delta": dl, "u_low": 0.1, "s_min": 0.1,
                             "c_min": c_min, "k": 1, "a": a_rate, "b": 0.0, "c": 0.0, "inconclusive": 1 - a_rate, "chk": chk})
    rec = fp.recommend({"readings": rows})
    assert rec["brackets"]["c_min"] == 0.10
    assert rec["c_min_check"]["0.05"]["alpha_chk"] == 0.12


def test_columnar_round_trip():
    rows = [{"x": 1, "y": 0.5}, {"x": 2, "y": 0.25}]
    col = fp.to_columns(rows)
    assert col == {"columns": ["x", "y"], "rows": [[1, 0.5], [2, 0.25]]}
    assert fp.from_columns(col) == rows


def test_run_weighted_S_tracks_miss_times_uptake():
    r = fp.simulate_cell(np.random.default_rng(12), COUNTS, repeats=3, u_rm=0.3, u_al=0.3, fp_rate=0.0, miss=MISS,
                         kappa=None, check_base=0.08, check_delta=0.0, ov_share=16 / 48, n_sims=400, n_boot=200)
    n_rt, n_md = COUNTS["routine"], COUNTS["middle"]
    expect = 0.3 * (n_rt * MISS["routine"] + n_md * MISS["middle"]) / (n_rt + n_md)
    assert abs(r["S_run"].mean() - expect) < 0.01
    assert (r["S_run_lo"] <= r["S_run"]).all() and (r["S_run"] <= r["S_run_hi"]).all()


def test_decide_on_run_weighted_S():
    st = stats(rm_lo=0.2, rm_hi=0.4, S={1: 0.0}, al_lo=0.5, all_hi=0.5)
    st["S_run"] = np.array([0.06])
    assert fp.decide(st, {"u_low": 0.1, "s_min": 0.05, "c_min": 0.1, "k": "run"})[0] == "a"
    assert fp.decide(st, {"u_low": 0.1, "s_min": 0.08, "c_min": 0.1, "k": "run"})[0] == "inconclusive"


def test_grid_in_run_mode_has_one_k_and_n_ov():
    res = fp.run_grid(counts=COUNTS, miss=MISS, repeats_grid=(3,), u_grid=(0.3,), fp_grid=(0.0,), delta_grid=(0.0,),
                      n_sims=30, n_boot=30, u_low_grid=(0.1,), s_min_grid=(0.05,), c_min_grid=(0.05,), u_al_high=None,
                      s_mode="run", ov_share=16 / 48)
    assert {r["k"] for r in res["readings"]} == {"run"}
    assert fp.n_benign({"routine": 24, "middle": 24, "alarming": 8}, 16 / 48) == 16


# ── power-v3: the final decision tree of pre-registration v1.1 ─────────────────────────────────────

C56 = {"routine": 24, "middle": 24, "alarming": 8}
GOV = {"routine": 0.5833, "middle": 0.2917, "alarming": 0.0}


def tree(u_k, u_s, u_al=None, fp_rate=0.0, rho=0.0, seed=5, n=150):
    return fp.simulate_tree(np.random.default_rng(seed), C56, u_rm={"kimi": u_k, "sol": u_s},
                            u_al={"kimi": u_al if u_al is not None else u_k, "sol": u_al if u_al is not None else u_s},
                            fp_rate=fp_rate, rho=rho, miss=GOV, identical_share=40 / 48, kappa=4.0, n_sims=n, n_boot=300)


def test_tree_high_uptake_reads_a_and_none_reads_c():
    assert tree(0.8, 0.8)["(a)"] > 0.95
    assert tree(0.0, 0.0)["(c)"] > 0.95


def test_tree_followers_that_differ_read_on_the_mixture_and_flag_the_difference():
    r = tree(0.02, 0.6)
    assert r["(a)"] + r["(e)"] > 0.8 and r["followers_differ"] > 0.8
    assert tree(0.8, 0.8)["followers_differ"] < 0.05


def test_tree_clean_false_positives_trip_gate1():
    assert tree(0.3, 0.3, fp_rate=0.05)["withheld: clean control"] > 0.9


def test_tree_unresolved_runs_make_gate2_bite():
    assert tree(0.12, 0.12, rho=0.3)["withheld: unresolved runs"] > 0.3


def test_tree_alarming_only_reads_b():
    assert tree(0.0, 0.0, u_al=0.8)["(b)"] > 0.9


def test_tree_is_seeded_and_sums_to_one():
    a, b = tree(0.2, 0.2), tree(0.2, 0.2)
    import stage3_ft_join as fj
    assert a == b and abs(sum(a[k] for k in fj.LABELS) - 1.0) < 1e-9


def test_tree_clean_bound_switch():
    lit = fp.simulate_tree(np.random.default_rng(7), C56, u_rm={"kimi": 0.3, "sol": 0.3}, u_al={"kimi": 0.3, "sol": 0.3}, fp_rate=0.0,
                           rho=0.03, miss=GOV, identical_share=40 / 48, kappa=4.0, n_sims=150, n_boot=300)
    off = fp.simulate_tree(np.random.default_rng(7), C56, u_rm={"kimi": 0.3, "sol": 0.3}, u_al={"kimi": 0.3, "sol": 0.3}, fp_rate=0.0,
                           rho=0.03, miss=GOV, identical_share=40 / 48, kappa=4.0, n_sims=150, n_boot=300, bound_clean=False)
    assert lit["withheld: unresolved runs"] > 0.5 and off["(a)"] > 0.8


def test_tree_reading_e_when_only_differing_states_carry_S():
    r = fp.simulate_tree(np.random.default_rng(3), C56, u_rm={"kimi": 0.5, "sol": 0.5}, u_al={"kimi": 0.5, "sol": 0.5}, fp_rate=0.0,
                         rho=0.0, miss=GOV, identical_share=0.0, kappa=4.0, n_sims=100, n_boot=200)
    assert r["(e)"] > 0.95
