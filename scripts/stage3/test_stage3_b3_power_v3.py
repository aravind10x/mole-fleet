"""Brief 20 (B3 power simulation v3): the stimulus moments, m_s, the estimators, the generative model's
calibration and the A6.6 gates (`stage3_b3_power_v3.py`)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy import optimize, stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_power_v3 as bp  # noqa: E402

ROOT = HERE.parents[1]
HAVE_DATA = (ROOT / bp.RATER / "key-b3.json").exists() and (ROOT / bp.B1).exists()


# ---------------------------------------------------------------- P1 on the files on disk

@pytest.mark.skipif(not HAVE_DATA, reason="rater and B1 files not on disk")
def test_moments_reproduce_a62_figures():
    triples = bp.load_stimuli(ROOT)
    assert len(triples) == 89
    m = bp.moments(triples)
    assert m["n_quiet"] == 78 and m["n_quiet_by_writer"] == {"sonnet55": 41, "glm53": 37}
    c = m["composition"]
    assert (c["q1"], c["median"], c["q3"], c["max"]) == (47.5, 55.75, 68.0, 85.0)
    assert (c["n_ge_75"], c["n_ge_70"], c["n_le_50"]) == (11, 17, 30)
    assert c["n_ge_75_by_writer"] == {"sonnet55": 9, "glm53": 2}
    assert round(m["test_retest"]["pearson_pass1_pass2"], 3) == 0.843
    assert round(m["test_retest"]["spearman_brown"], 3) == 0.915
    assert round(m["correlations"]["pearson_comp_spread"], 2) == 0.32
    assert round(m["top_line"]["mean"]) == 44 and round(m["top_line"]["mean_at_comp_ge_70"]) == 52


@pytest.mark.skipif(not HAVE_DATA, reason="rater files not on disk")
def test_edit_types_match_writer_checks():
    # the writers' checks count 18 (Sonnet) and 51 (GLM, B3-D36's two included) replace edits in the distributed arm
    triples = bp.load_stimuli(ROOT)
    n = {w: sum(sum(t["replace"]) for t in triples if t["writer"] == w) for w in bp.WRITERS}
    assert n["sonnet55"] == 18
    ck = json.loads((ROOT / bp.CHECKS["glm53"]).read_text())
    d36 = sum(1 for a in ck["anchors"] if a["payload"] == "B3-D36")
    assert n["glm53"] == 51 - d36


def test_quantiles_are_linear_interpolation():
    v = [10, 20, 30, 40]
    assert np.quantile(v, 0.25) == 17.5  # numpy's default (A6.11)


def test_spearman_brown():
    assert bp.spearman_brown(0.843) == pytest.approx(0.9148, abs=1e-4)


# ---------------------------------------------------------------- m_s

def test_margin_primary_rule():
    # t = 60; ten plants: four above, six at or below (60, 55, 50, 40, 20, 10); 0.3 x 10 = 3 needed -> [50, 60], D = 10
    s = [90, 80, 75, 70, 60, 55, 50, 40, 20, 10]
    r = bp.margin_ms(s, 60, 5, 80)
    assert r["m_s"] == 10 and r["rule"].startswith("A6.4 primary")


def test_margin_fallback_when_too_few_below():
    s = [90, 80, 75, 70, 65, 64, 63, 62, 61, 10]
    r = bp.margin_ms(s, 60, 5, 45)
    assert r["rule"].startswith("A6.4 fallback") and r["m_s"] == pytest.approx(0.3 * 40)


def test_margin_exact_counts_the_honest_union():
    # two plants already flagged through the honest path cannot be raised by a shift
    plants = [{"score": x, "honest_max": h} for x, h in [(50, 70), (50, 70), (50, 0), (50, 0), (90, 0)]]
    r = bp.margin_exact(plants, 60, 0.0, target=0.3)
    assert r["base_rate"] == pytest.approx(0.6)
    # raising 0.3 needs both remaining plants at 50 -> D just above 10
    assert r["D"] == pytest.approx(10.000001, abs=1e-5)


# ---------------------------------------------------------------- grid, flags, outcomes

def test_grid_and_latent_flag_probability():
    assert list(bp.to_grid([-3, 2.4, 2.6, 61, 103])) == [0, 0, 5, 60, 100]
    rng = np.random.default_rng(0)
    T, sw, t, pt = 58.0, 7.0, 60.0, 0.4
    s = bp.to_grid(T + sw * rng.standard_normal(400000))
    mc = ((s > t) + pt * (s == t)).mean()
    assert float(bp.flag_prob_latent(np.array([T]), sw, t, pt)[0]) == pytest.approx(mc, abs=0.003)
    # off-grid threshold: no ties
    s2 = bp.to_grid(T + sw * rng.standard_normal(400000))
    assert float(bp.flag_prob_latent(np.array([T]), sw, 62.0, 0.9)[0]) == pytest.approx((s2 > 62).mean(), abs=0.003)


@pytest.mark.parametrize("lo,hi,pt,expect", [(-0.1, 0.2, 0.05, "excluded"), (0.05, 0.4, 0.2, "attenuated"),
                                             (0.05, 0.6, 0.35, "present"), (-0.1, 0.5, 0.2, "inconclusive"),
                                             (0.0, 0.29, 0.1, "excluded")])
def test_four_outcome_table(lo, hi, pt, expect):
    assert bp.four_outcome(lo, hi, pt, 0.3) == expect


# ---------------------------------------------------------------- estimators

def test_irls_matches_direct_mle():
    rng = np.random.default_rng(3)
    n, k = 150, 4
    X = np.column_stack([np.ones(n), rng.standard_normal((n, k - 1))])
    y = (rng.random(n) < bp.sigmoid(X @ np.array([-0.3, 0.8, -0.5, 0.2]))).astype(float)
    nll = lambda b: -np.sum(y * (X @ b) - np.log1p(np.exp(X @ b)))
    ref = optimize.minimize(nll, np.zeros(k), method="BFGS").x
    b, conv = bp.irls(X, y, np.ones((1, n)))
    assert conv[0] and np.allclose(b[0], ref, atol=1e-4)
    # frequency weights equal row duplication
    w = rng.integers(0, 3, n).astype(float)
    Xd, yd = np.repeat(X, w.astype(int), 0), np.repeat(y, w.astype(int))
    bd, _ = bp.irls(Xd, yd, np.ones((1, len(yd))))
    bw, _ = bp.irls(X, y, w[None])
    assert np.allclose(bd, bw, atol=1e-6)


def test_bootstrap_weights_and_strata():
    rng = np.random.default_rng(1)
    w = bp.bootstrap_weights(rng, 10, 50)
    assert w.shape == (50, 10) and np.all(w.sum(1) == 10)
    strata = np.array([0, 0, 0, 1, 1, 2, 2, 2, 2, 2])
    ws = bp.bootstrap_weights(rng, 10, 50, strata)
    for s in np.unique(strata):
        assert np.all(ws[:, strata == s].sum(1) == (strata == s).sum())


def test_form_a_recovers_a_known_slope():
    rng = np.random.default_rng(5)
    n = 78
    C = rng.uniform(20, 85, n); gap = rng.uniform(0, 30, n); son = (rng.random(n) < 0.5).astype(float)
    edit = rng.integers(0, 4, n) / 3; doc = rng.integers(0, 6, n)
    y = 0.8 * C + 0.1 * gap + rng.standard_normal(n) * 0.01
    out = bp.form_a(rng, C, gap, son, edit, doc, y, 200, m_s=10.0, q1q3=(47.5, 68.0))
    assert out["75v50"]["point"] == pytest.approx(20.0, abs=0.05) and out["75v50"]["outcome"] == "present"


def test_auroc_matrix():
    a, b = np.array([3.0, 2.0, 1.0]), np.array([2.0, 0.0])
    m = bp.auroc_matrix(a, b)
    assert m.mean() == pytest.approx(stats.mannwhitneyu(a, b).statistic / 6)


# ---------------------------------------------------------------- the generative model

def _toy_design(n=78, seed=0):
    rng = np.random.default_rng(seed)
    r = np.clip(rng.normal(35, 14, (n, 3)), 5, 60)
    C = np.clip(0.6 * r.max(1) + rng.normal(25, 12, n), 15, 85)
    D = {"r": r, "C": C, "c1": C + rng.normal(0, 5, n), "c2": C + rng.normal(0, 5, n),
         "sonnet": (rng.random(n) < 0.5).astype(float), "edit": rng.integers(0, 4, n) / 3,
         "doc": np.arange(n) % 6, "docs": [f"d{i}" for i in range(6)]}
    mom = {"test_retest": {"spearman_brown": 0.915, "partial": {"spearman_brown": 0.85}}}
    return bp.design_with_moments(D, mom)


def _toy_inputs(rate=0.5, sd=25.0, t=62.0, p_tie=0.7):
    return {"t": t, "p_tie": p_tie, "honest_path": 0.08,
            "quiet_prior": {"planted_unit_rate": rate, "sd": sd},
            "sham_prior": {"mean": 16.0, "sd": 15.0}}


def test_calibration_hits_its_targets():
    D = _toy_design()
    dgp = bp.calibrate(D, _toy_inputs(), 0.3, 5.0)
    a = dgp["achieved"]
    assert a["quiet_rate"] == pytest.approx(0.5, abs=0.01)
    assert a["quiet_grid_sd"] == pytest.approx(25.0, abs=0.5)
    assert a["sham_grid_mean"] == pytest.approx(16.0, abs=0.3) and a["sham_grid_sd"] == pytest.approx(15.0, abs=0.5)
    # within-triple variance is the placement deviation plus the call noise; the ICC is the between-triple share
    # of the latent variance before the call noise
    assert dgp["sig_z"] ** 2 + dgp["sig_c"] ** 2 == pytest.approx(dgp["sig_w"] ** 2)
    assert dgp["sig_z"] ** 2 / (dgp["s_lat"] ** 2 - 5.0 ** 2) == pytest.approx(1 - 0.3)


def test_beta_for_contrast_hits_the_target():
    D = _toy_design()
    dgp = bp.calibrate(D, _toy_inputs(), 0.6, 5.0)
    beta = bp.beta_for_contrast(D, dgp)
    assert beta is not None and bp.true_contrast_conditional(D, dgp, beta) == pytest.approx(0.3, abs=1e-3)
    beta_m = bp.beta_for_contrast(D, dgp, kind="marginal")
    assert bp.true_contrast(D, dgp, beta_m) == pytest.approx(0.3, abs=1e-3)
    # holding the line maximum at its mean gives the steeper (conditional) contrast, so it needs the smaller shift
    assert beta < beta_m
    assert bp.true_contrast(D, dgp, 0.0) == pytest.approx(0.0, abs=1e-12)
    assert bp.true_contrast_conditional(D, dgp, 0.0) == pytest.approx(0.0, abs=1e-12)


def test_experiment_is_seeded():
    D = _toy_design()
    dgp = bp.calibrate(D, _toy_inputs(), 0.3, 5.0)
    one = bp.experiment(np.random.default_rng([1, 2]), D, dgp, "T1+S1", 0.0, 20.0, (47.5, 68.0), R=100)
    two = bp.experiment(np.random.default_rng([1, 2]), D, dgp, "T1+S1", 0.0, 20.0, (47.5, 68.0), R=100)
    assert json.dumps(one, sort_keys=True) == json.dumps(two, sort_keys=True)


def test_no_within_noise_means_no_singleton_inflation():
    # with placement and call noise at zero, a triple's grid score equals the grid maximum of its lines, so
    # excess is exactly zero under the null and form (a)'s slope is zero
    D = _toy_design()
    dgp = dict(bp.calibrate(D, _toy_inputs(), 0.6, 0.0))
    dgp["sig_z"] = 0.0; dgp["sig_c"] = 0.0
    out = bp.experiment(np.random.default_rng(9), D, dgp, "T1+S1", 0.0, 20.0, (47.5, 68.0), R=100, forms=("a",))
    assert abs(out["a"]["75v50"]["point"]) < 1e-9


def test_singleton_inflation_biases_excess_down():
    D = _toy_design()
    dgp = bp.calibrate(D, _toy_inputs(), 0.6, 5.0)
    rng = np.random.default_rng(4)
    r = D["r"]; x = (r - r.mean()) / r.std()
    lat = bp.line_latent(rng, x, dgp["rho"], 200)
    L = dgp["a"] + dgp["b"] * (lat - dgp["mx_mean"])
    noisy = L + dgp["sig_w"] * rng.standard_normal(L.shape)
    assert (noisy.max(-1) - L.max(-1)).mean() > 0  # the max of three calls sits above the true max


def test_true_composition_error_is_independent_of_the_design():
    D = _toy_design()
    rng = np.random.default_rng(2)
    lam = D["partial_rel"]
    draws = np.array([D["C_fit"] + lam * D["C_res"] + math.sqrt(lam * (1 - lam) * D["C_res_var"]) * rng.standard_normal(len(D["C"]))
                      for _ in range(4000)])
    err = D["C"][None] - draws  # measured minus true
    Z = bp.rater_covariates(D)
    # every design covariate is uncorrelated with the error, on average over draws
    cov = (err - err.mean(1, keepdims=True)) @ (Z[:, 1:] - Z[:, 1:].mean(0)) / len(D["C"])
    assert np.abs(cov.mean(0)).max() < 0.2
    resid_true = np.array([bp._residual(d, Z) for d in draws[:500]])
    assert (resid_true.var(1).mean() / D["C_res_var"]) == pytest.approx(lam, abs=0.03)


# ---------------------------------------------------------------- gates

def _cell(excl=0.0, pres=0.0, att=0.0, form="b"):
    d = {"75v50": {"floor": 0.0, "excluded": excl, "attenuated": att, "present": pres, "inconclusive": 1 - excl - pres - att,
                   "point_mean": 0.0, "point_mcse": 0.0}}
    return {form: d}


def test_gates_prefer_a_readable_singleton_layout():
    sim = {}
    name = "dossier_iso:opus48"
    for icc in bp.ICCS:
        # T2 (no singleton) is readable with a higher score; T1+S1 is readable under form (b) with a lower one
        sim[f"{name}|T2|{icc}|5.0|null"] = _cell(excl=0.9)
        sim[f"{name}|T2|{icc}|5.0|alt_b"] = _cell(pres=0.9)
        sim[f"{name}|T1+S1|{icc}|5.0|null"] = {**_cell(excl=0.7), **_cell(excl=0.1, form="a")}
        sim[f"{name}|T1+S1|{icc}|5.0|alt_b"] = _cell(pres=0.65)
        sim[f"{name}|T1+S1|{icc}|5.0|alt_a"] = _cell(pres=0.1, form="a")
    inputs = {"instruments": {f"{v}:{j}": {"m_s": {"m_s": 10.0}} for v, j in bp.INSTRUMENTS}}
    g = bp.apply_gates(sim, inputs)
    assert set(g["readable_layouts"]) == {"T2", "T1+S1"}
    assert g["adopted"] == "T1+S1" and g["readable_layouts"]["T1+S1"]["carrying"] == f"{name}|b|T1+S1"


def test_gates_need_both_iccs():
    sim = {}
    name = "P_author:sonnet"
    for icc, pres in zip(bp.ICCS, (0.7, 0.5)):
        sim[f"{name}|T1|{icc}|5.0|null"] = _cell(excl=0.8)
        sim[f"{name}|T1|{icc}|5.0|alt_b"] = _cell(pres=pres)
    inputs = {"instruments": {f"{v}:{j}": {"m_s": {"m_s": 10.0}} for v, j in bp.INSTRUMENTS}}
    g = bp.apply_gates(sim, inputs)
    assert g["adopted"] is None and g["table"][f"{name}|b|T1"]["P_present_alt"] == 0.5


# ---------------------------------------------------------------- the estimate

def test_estimate_counts_units_per_layout():
    costs = {f"{v}:{j}": {"used": 0.01} for v, j in bp.INSTRUMENTS}
    costs.update({k: {"used": 0.001} for k in ("O_diff:sonnet", "O_diff:opus48", "O_diff:sol")})
    est = bp.estimate(costs)
    e = est["T2+S1"]
    lone = (78 + 22 + 24) * 2
    assert e["rows"]["dossier_iso:opus48"]["units"] == lone + 234 and e["rows"]["O_diff:sol"]["units"] == lone
    assert e["units"] == 6 * (lone + 234) + 3 * lone
    assert e["dollars"] == pytest.approx(6 * (lone + 234) * 0.01 + 3 * lone * 0.001)
    assert est["T1"]["rows"]["P_author:sonnet"]["singleton_units"] == 0 and est["T1+S2"]["rows"]["P_author:sonnet"]["singleton_units"] == 468
    assert e["stop_line_2x"] == pytest.approx(2 * e["dollars"])


@pytest.mark.skipif(not HAVE_DATA, reason="cost files not on disk")
def test_unit_costs_use_the_higher_basis():
    c = bp.unit_costs(ROOT)
    assert set(c) == {f"{v}:{j}" for v, j in bp.INSTRUMENTS} | {"O_diff:sonnet", "O_diff:opus48", "O_diff:sol"}
    for v in c.values():
        assert v["used"] == max(x for k, x in v.items() if k != "used") > 0


def test_form_b_falls_back_when_a_document_separates():
    # every plant of document 0 flagged: its dummy separates, so O3 drops the factor and stratifies the bootstrap
    rng = np.random.default_rng(11)
    n = 78
    C = rng.uniform(20, 85, n); line = rng.uniform(10, 60, n); gap = rng.uniform(0, 30, n)
    son = (rng.random(n) < 0.5).astype(float); edit = rng.integers(0, 4, n) / 3; doc = np.arange(n) % 6
    F = (rng.random((n, 1)) < 0.5).astype(float)
    F[doc == 0] = 1.0
    out = bp.form_b(rng, C, line, gap, son, edit, doc, F, 1, 200, (47.5, 68.0))
    assert out["doc_factor"] is False and out["fallback_reason"] in ("point", "bootstrap")
    # two documents of 39 triples at a flag rate of one half: no resample separates, so the factor stays (with six
    # documents of 13, about 3 percent of resamples separate one and O3 falls back, as in the B3 design)
    F2 = (rng.random((n, 1)) < 0.5).astype(float)
    out2 = bp.form_b(rng, C, line, gap, son, edit, np.arange(n) % 2, F2, 1, 200, (47.5, 68.0))
    assert out2["doc_factor"] is True and out2["fallback_reason"] is None and out2["boot_nonconverged"] <= bp.NONCONV_MAX


# ---------------------------------------------------------------- after the codex review (round 1)

def test_solve_reports_an_unbracketed_target():
    f = lambda x: 2 * x + 1
    x, st = bp._solve(f, 0.0, 10.0, 7.0)
    assert st == "ok" and x == pytest.approx(3.0, abs=1e-9)
    assert bp._solve(f, 0.0, 10.0, 0.5) == (0.0, "at_lower_end")
    assert bp._solve(f, 0.0, 10.0, 30.0) == (10.0, "at_upper_end")


def test_unattainable_sham_sd_takes_the_closest_value_and_is_recorded():
    # a control-arm SD of 5 cannot be met with 10-point call noise: the calibration must take the narrowest
    # attainable arm, record the miss, and never drift to the wide end of the search
    D = _toy_design()
    inp = _toy_inputs(); inp["sham_prior"] = {"mean": 7.3, "sd": 5.0, "planted_unit_rate": 0.0}
    dgp = bp.calibrate(D, inp, 0.3, 10.0)
    assert dgp["status"]["sham_sd"] == "at_lower_end" and "sham_grid_sd" in dgp["misses"]
    assert dgp["achieved"]["sham_grid_sd"] < 12.0


def test_a_failed_fit_is_never_excluded():
    rng = np.random.default_rng(2)
    n = 78
    C = rng.uniform(20, 85, n); line = rng.uniform(10, 60, n); gap = rng.uniform(0, 30, n)
    son = (rng.random(n) < 0.5).astype(float); edit = rng.integers(0, 4, n) / 3; doc = np.arange(n) % 6
    out = bp.form_b(rng, C, line, gap, son, edit, doc, np.ones((n, 1)), 1, 200, (47.5, 68.0))
    assert out["fit_ok"] is False
    assert all(out[c]["outcome"] == "unfit" for c in ("75v50", "q3vq1", "75v50_o4"))


def test_observed_slope_is_below_the_latent_one_near_the_ceiling_and_calibrates():
    D = _toy_design()
    dgp = dict(bp.calibrate(D, _toy_inputs(rate=0.8, sd=20.0), 0.6, 5.0))
    lat = 40 / 25
    obs = bp.observable_slope_a(D, dgp, lat)
    assert 0 < obs < lat  # clipping at 100 hides part of a latent shift
    beta = bp.beta_for_slope(D, dgp, lat)
    assert beta is not None and beta > lat and bp.observable_slope_a(D, dgp, beta) == pytest.approx(lat, rel=1e-3)
    assert bp.beta_for_slope(D, dgp, 150 / 25) is None  # 150 points over 25 cannot show on a 0..100 scale


def _gate_inputs():
    return {"instruments": {f"{v}:{j}": {"m_s": {"m_s": 10.0}} for v, j in bp.INSTRUMENTS}}


def _set(sim, name, layout, null_a, null_b, alt_a, alt_b, bias_a=0.0, bias_b=0.0):
    for icc in bp.ICCS:
        sim[f"{name}|{layout}|{icc}|5.0|null"] = {**_cell(excl=null_b), **_cell(excl=null_a, form="a")}
        sim[f"{name}|{layout}|{icc}|5.0|null"]["a"]["75v50"]["point_mean"] = bias_a
        sim[f"{name}|{layout}|{icc}|5.0|null"]["b"]["75v50"]["point_mean"] = bias_b
        sim[f"{name}|{layout}|{icc}|5.0|alt_b"] = _cell(pres=alt_b)
        sim[f"{name}|{layout}|{icc}|5.0|alt_a"] = _cell(pres=alt_a, form="a")


def test_bias_switch_to_an_unreadable_variant_is_unresolved():
    # codex round 1: a readable T1+S1 whose carrier has a material (b) bias moves to T1+S2, which is not readable
    name, sim = "dossier_iso:opus48", {}
    _set(sim, name, "T1+S1", 0.8, 0.8, 0.1, 0.8, bias_b=0.2)
    _set(sim, name, "T1+S2", 0.1, 0.1, 0.1, 0.1)
    g = bp.apply_gates(sim, _gate_inputs())
    assert g["adopted_by_gate"] == "T1+S1" and g["bias_trigger"]["moved_to"] == "T1+S2"
    assert g["status"] == "unresolved" and g["adopted"] is None and g["carrier"] is None


def test_both_forms_material_leaves_nothing_eligible():
    # codex round 2: with both forms' bias material at the variant, neither may carry
    name, sim = "dossier_iso:opus48", {}
    _set(sim, name, "T1+S1", 0.8, 0.8, 0.8, 0.8, bias_a=9.0, bias_b=0.2)
    _set(sim, name, "T1+S2", 0.8, 0.8, 0.8, 0.8, bias_a=9.0, bias_b=0.2)
    g = bp.apply_gates(sim, _gate_inputs())
    assert g["status"] == "unresolved"


def test_a_directly_chosen_variant_checks_eligibility_and_hands_over():
    # codex round 2: S2 chosen directly; its best form (a) is material, the clean form (b) is readable and carries
    name, sim = "dossier_iso:opus48", {}
    _set(sim, name, "T1+S2", 0.9, 0.7, 0.9, 0.7, bias_a=9.0)
    g = bp.apply_gates(sim, _gate_inputs())
    assert g["adopted_by_gate"] == "T1+S2" and g["status"] == "adopted" and g["carrier"] == f"{name}|b|T1+S2"
    # and a clean form that is not readable cannot carry
    sim2 = {}
    _set(sim2, name, "T1+S2", 0.9, 0.2, 0.9, 0.2, bias_a=9.0)
    assert bp.apply_gates(sim2, _gate_inputs())["status"] == "unresolved"


def test_unknown_bias_never_clears_the_trigger():
    name, sim = "dossier_iso:opus48", {}
    _set(sim, name, "T1+S2", 0.9, 0.9, 0.9, 0.9, bias_a=float("nan"), bias_b=float("nan"))
    g = bp.apply_gates(sim, _gate_inputs())
    assert g["bias"][f"{name}|a|T1+S2|5.0"]["material"] is None and g["status"] == "unresolved"


def test_failure_count_rule_is_in_whole_replicates():
    conv = np.ones(1000, bool); conv[:25] = False
    assert not bp.too_many_failures(conv)  # 25 of 1,000 is not more than 2.5 percent
    conv[25] = False
    assert bp.too_many_failures(conv)


def test_form_a_truth_matches_form_a_itself():
    # codex round 2: the calibrated alternative must be form (a)'s own error-free coefficient. Without composition
    # measurement error, form (a)'s mean estimate at beta minus at 0 recovers the target slope x 25
    D = dict(_toy_design()); D["partial_rel"] = 1.0
    dgp = bp.calibrate(D, _toy_inputs(rate=0.6, sd=25.0), 0.6, 5.0)
    target = 20.0 / 25
    beta = bp.beta_for_slope(D, dgp, target, Q=1)
    est = lambda b, seed: np.mean([bp.experiment(np.random.default_rng([seed, i]), D, dgp, "T1+S1", b, 20.0, (47.5, 68.0), R=50, forms=("a",))["a"]["75v50"]["point"] for i in range(150)])
    assert est(beta, 1) - est(0.0, 1) == pytest.approx(20.0, abs=2.5)


def test_too_thin_states():
    gates = {"table": {"x|b|T1": {"P_present_alt": 0.4}}}
    full = {f"x|T1|{icc}|5.0|{tr}": {"b": {}} for icc in bp.ICCS for tr in ("null", "alt_b")}
    assert bp.too_thin_check(gates, {})["state"] == "pending"
    assert bp.too_thin_check(gates, {"tail_doubled": {"x|b|T1": {"P_present_alt": 0.7}}}, full, ["T1"])["state"] == "too_thin"
    assert bp.too_thin_check(gates, {"tail_doubled": {"x|b|T1": {"P_present_alt": 0.5}}}, full, ["T1"])["state"] == "not_too_thin"
    # a tail run that lacks an instrument's null cells cannot license a negative verdict
    gates2 = {"table": {"x|b|T1": {"P_present_alt": 0.4}, "y|b|T1": {"P_present_alt": 0.3}}}
    assert bp.too_thin_check(gates2, {"tail_doubled": {"x|b|T1": {"P_present_alt": 0.5}}}, full, ["T1"])["state"] == "incomplete"
    assert bp.too_thin_check({"table": {"x|b|T1": {"P_present_alt": 0.65}}}, {})["state"] == "not_applicable"


# ---------------------------------------------------------------- after the codex review (round 3)

def test_a_reading_missing_in_some_experiments_is_unavailable_not_a_crash():
    D = _toy_design()
    dgp = bp.calibrate(D, _toy_inputs(), 0.6, 5.0)
    rows = [bp.experiment(np.random.default_rng([3, i]), D, dgp, "T1+S1", 0.0, 20.0, (47.5, 68.0), R=50) for i in range(4)]
    for order in (rows, rows[::-1]):
        rr = [json.loads(json.dumps(r)) for r in order]
        rr[0]["a"].pop("75v50_disatt")  # the first (or last) experiment had an invalid reliability
        s = bp.summarise_cell(rr, "T1+S1", "null")
        assert s["a"]["75v50_disatt"]["unavailable"] == pytest.approx(0.25 * (1 - s["P_floor_a"]), abs=0.26)
        assert s["a"]["75v50_disatt"]["n_fit"] == 3


def test_too_thin_needs_full_coverage():
    gates = {"table": {"x|b|T1": {"P_present_alt": 0.4}, "x|b|T2": {"P_present_alt": 0.4}}}
    cells = {f"x|{l}|{icc}|5.0|{t}": {"b": {}} for l in ("T1", "T2") for icc in bp.ICCS for t in ("null", "alt_b")}
    tab = {"x|b|T1": {"P_present_alt": 0.5}, "x|b|T2": {"P_present_alt": 0.5}}
    assert bp.too_thin_check(gates, {"tail_doubled": tab}, cells, ["T1", "T2"])["state"] == "not_too_thin"
    # codex round 3: a layout the tail run skipped, or a missing alternative, is not coverage
    assert bp.too_thin_check(gates, {"tail_doubled": tab}, cells, ["T1"])["state"] == "incomplete"
    cut = {k: v for k, v in cells.items() if k != "x|T2|0.3|5.0|alt_b"}
    assert bp.too_thin_check(gates, {"tail_doubled": tab}, cut, ["T1", "T2"])["state"] == "incomplete"
    # an alternative recorded as unattainable under the doubled tail is covered (it cannot clear)
    r = bp.too_thin_check(gates, {"tail_doubled": tab}, cut, ["T1", "T2"], ["x|T2|0.3|5.0|alt_b|tail_doubled"])
    assert r["state"] == "not_too_thin" and r["unattainable_under_tail"] == ["x|b|T2|0.3|alt"]
