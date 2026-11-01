"""Offline tests for stage3_b3_comprehension (brief 25): synthetic fixtures only, no item file, no network.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_comprehension.py
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_comprehension as bc  # noqa: E402


# ── C1: the model ──

def test_rule_prob_every_majority_and_mean_on_known_cases():
    th = [0.7, 0.1, 0.2]
    assert bc.rule_prob(th, 2, ("every", None)) == pytest.approx(0.49)
    assert bc.rule_prob(th, 2, ("majority", None)) == pytest.approx(0.49)          # strict majority of two is both
    assert bc.rule_prob(th, 3, ("majority", None)) == pytest.approx(3 * 0.7 ** 2 * 0.3 + 0.7 ** 3)
    # mean <= 0.25 at k = 2: (0, 0) or (0, 0.5) in either order
    assert bc.rule_prob(th, 2, ("mean", 0.25)) == pytest.approx(0.49 + 2 * 0.7 * 0.1)
    # mean <= 0.5 at k = 2: adds (0.5, 0.5) and (0, 1) in either order
    assert bc.rule_prob(th, 2, ("mean", 0.5)) == pytest.approx(0.49 + 2 * 0.07 + 0.01 + 2 * 0.14)
    assert bc.rule_prob(th, 4, ("mean", 1.0)) == pytest.approx(1.0)
    assert bc.rule_prob([1.0, 0.0, 0.0], 3, ("every", None)) == pytest.approx(1.0)


def test_mean_one_third_at_three_samples_includes_the_boundary():
    th = [0.5, 0.25, 0.25]
    # (0, 0, 1) has mean exactly 1/3 and is included; (0, 0.5, 0.5) too
    p = bc.rule_prob(th, 3, ("mean", 1 / 3))
    want = 0.5 ** 3 + 3 * 0.5 ** 2 * 0.25 + 3 * 0.5 ** 2 * 0.25 + 3 * 0.5 * 0.25 ** 2
    assert p == pytest.approx(want)


def _synthetic(n, pi, theta, rng, retest_share=0.25):
    data = []
    for _ in range(n):
        z = "Q" if rng.random() < pi else "N"
        row = {}
        reps = 2 if rng.random() < retest_share else 1
        for f, t in theta.items():
            row[f] = [rng.choices((0, 1, 2), weights=t[z])[0] for _ in range(reps)]
        data.append(row)
    return data


def test_em_recovers_well_separated_classes_and_orients_q_on_the_anchor():
    rng = random.Random(7)
    theta = {"kimi": {"Q": [0.95, 0.03, 0.02], "N": [0.1, 0.1, 0.8]},
             "sol": {"Q": [0.8, 0.1, 0.1], "N": [0.3, 0.1, 0.6]},
             "sonnet55": {"Q": [0.9, 0.05, 0.05], "N": [0.15, 0.05, 0.8]}}
    data = _synthetic(1500, 0.35, theta, rng)
    fit = bc.lca_fit(data, starts=6, rng=random.Random(1))
    assert fit["pi_quiet"] == pytest.approx(0.35, abs=0.04)
    for f in theta:
        for z in ("Q", "N"):
            assert fit["theta"][f][z][0] == pytest.approx(theta[f][z][0], abs=0.05)
    assert fit["theta"]["kimi"]["Q"][0] > fit["theta"]["kimi"]["N"][0]


def test_em_label_is_stable_when_the_start_lands_on_the_swapped_mode():
    rng = random.Random(3)
    theta = {"kimi": {"Q": [0.9, 0.05, 0.05], "N": [0.1, 0.1, 0.8]},
             "sol": {"Q": [0.7, 0.1, 0.2], "N": [0.4, 0.1, 0.5]},
             "sonnet55": {"Q": [0.9, 0.05, 0.05], "N": [0.2, 0.1, 0.7]}}
    data = _synthetic(400, 0.6, theta, rng)
    fits = [bc.lca_fit(data, starts=3, rng=random.Random(s)) for s in range(5)]
    for fit in fits:
        assert fit["theta"]["kimi"]["Q"][0] > 0.7 and fit["theta"]["kimi"]["N"][0] < 0.3
        assert fit["pi_quiet"] == pytest.approx(fits[0]["pi_quiet"], abs=1e-4)


def test_smoothing_keeps_rates_off_the_boundary():
    data = [{"kimi": [0, 0], "sol": [0], "sonnet55": [0]} for _ in range(5)] + [{"kimi": [2], "sol": [2], "sonnet55": [2]} for _ in range(5)]
    fit = bc.lca_fit(data, starts=4, rng=random.Random(0))
    assert 0 < fit["theta"]["kimi"]["Q"][2] < 0.2 and 0 < fit["theta"]["kimi"]["N"][0] < 0.2
    mle = bc.lca_fit(data, smooth=0.0, starts=4, rng=random.Random(0))
    assert mle["theta"]["kimi"]["Q"][0] == pytest.approx(1.0, abs=1e-6)


def test_operating_characteristics_multiply_across_readers():
    fit = {"pi_quiet": 0.5, "theta": {"kimi": {"Q": [0.9, 0.05, 0.05], "N": [0.2, 0.1, 0.7]},
                                      "sol": {"Q": [0.6, 0.2, 0.2], "N": [0.3, 0.2, 0.5]}}}
    oc = bc.operating(fit, 2, {"kimi": ("every", None), "sol": ("mean", 0.5)})
    assert oc["quiet"] == pytest.approx(0.81 * bc.rule_prob([0.6, 0.2, 0.2], 2, ("mean", 0.5)))
    assert oc["nonquiet"] == pytest.approx(0.04 * bc.rule_prob([0.3, 0.2, 0.5], 2, ("mean", 0.5)))


def _row(k, ri, q, nq):
    return {"k": k, "rule": bc.rule_name(bc.SOL_RULES[ri]), "rule_index": ri, "quiet": q, "nonquiet": nq}


def test_choose_prefers_the_smallest_feasible_k_then_the_highest_first_figure():
    t = [_row(2, 0, 0.79, 0.01), _row(2, 3, 0.85, 0.09), _row(2, 1, 0.82, 0.05), _row(3, 3, 0.95, 0.01)]
    c = bc.choose(t)
    assert c["feasible"] and c["k"] == 2 and c["rule_index"] == 3


def test_choose_falls_back_to_the_smallest_shortfall():
    t = [_row(2, 0, 0.6, 0.02), _row(2, 3, 0.75, 0.12), _row(3, 3, 0.75, 0.12), _row(4, 2, 0.5, 0.0)]
    c = bc.choose(t)
    assert not c["feasible"] and c["k"] == 2 and c["rule_index"] == 3
    assert bc.shortfall(0.75, 0.12) == pytest.approx(0.07)


def _instrument(values):
    """values: {item: {reader: (r0, r1 or None)}} -> an instrument-v0.json-like structure."""
    pf = {f: {"items": {}} for f in bc.PLAN_READERS}
    for i, per in values.items():
        for f in bc.PLAN_READERS:
            r0, r1 = per[f]
            rec = {"regime": "v2_conforming", "r0": {"D_part": r0}}
            if r1 is not None or per.get("retest"):
                rec["r1"] = {"D_part": r1}
            pf[f]["items"][i] = rec
    pf["kimi"]["items"]["n0"] = {"regime": "honest_random", "r0": {"D_part": 0.0}}
    for f in ("sol", "sonnet55"):
        pf[f]["items"]["n0"] = {"regime": "honest_random", "r0": {"D_part": 0.0}}
    return {"per_family": pf}


def test_plan_data_counts_flips_and_the_proxy_on_test_items_only():
    vals = {"a": {"kimi": (0.0, 0.0), "sol": (0.0, 0.5), "sonnet55": (None, 0.0), "retest": True},
            "b": {"kimi": (1.0, 0.0), "sol": (0.0, 0.0), "sonnet55": (1.0, 1.0)},
            "c": {"kimi": (0.5, None), "sol": (1.0, None), "sonnet55": (0.0, None)}}
    data, counts = bc.plan_data(_instrument(vals))
    assert counts["n_test_items"] == 3
    assert counts["flips"] == {"kimi": 1, "sol": 1, "sonnet55": 0}
    assert counts["retest_pairs"] == {"kimi": 2, "sol": 2, "sonnet55": 1}
    assert counts["proxy_both_quiet_r0"] == 1
    assert counts["quiet_r0"] == {"kimi": 1, "sol": 2, "sonnet55": 1} and counts["n_r0"]["sonnet55"] == 2
    assert data[0]["sonnet55"] == [0] and data[0]["sol"] == [0, 1] and data[2]["kimi"] == [1]


def test_category_refuses_off_grid_values():
    assert bc.category(0.5) == 1 and bc.category(None) is None
    with pytest.raises(ValueError):
        bc.category(0.25)


def test_build_plan_refuses_figures_other_than_the_briefs():
    vals = {"a": {"kimi": (0.0, 0.0), "sol": (0.0, 0.0), "sonnet55": (0.0, 0.0)}}
    with pytest.raises(SystemExit):
        bc.build_plan(_instrument(vals), boot_n=5)


def test_model_checks_report_implied_and_observed_rates():
    fit = {"pi_quiet": 0.5, "theta": {f: {"Q": [1.0, 0.0, 0.0], "N": [0.0, 0.0, 1.0]} for f in bc.PLAN_READERS}}
    counts = {"flips": {f: 0 for f in bc.PLAN_READERS}, "retest_pairs": {f: 10 for f in bc.PLAN_READERS},
              "quiet_r0": {f: 24 for f in bc.PLAN_READERS}, "n_r0": {f: 48 for f in bc.PLAN_READERS}}
    mc = bc.model_checks(fit, counts)
    assert mc["kimi"]["implied_flip_rate"] == 0 and mc["kimi"]["implied_quiet_share_one_sample"] == pytest.approx(0.5)
    assert math.isclose(mc["sol"]["observed_quiet_share_r0"], 0.5)


def test_reader_relative_fit_takes_symmetric_error_from_the_flip_rate():
    # kimi: 10 pairs, 2 flips; sol: 10 pairs, 5 flips; sonnet: none paired (e at 0.5)
    data = [{"kimi": [0, 2] if i < 2 else [0, 0], "sol": [0, 1] if i < 5 else [2, 2], "sonnet55": [0]} for i in range(10)]
    rr = bc.reader_relative_fit(data)
    e = (1 - math.sqrt(1 - 0.4)) / 2
    assert rr["theta"]["kimi"]["e"] == pytest.approx(e) and rr["theta"]["kimi"]["Q"][0] == pytest.approx(1 - e)
    assert rr["theta"]["sol"]["e"] == pytest.approx(0.5)
    assert rr["theta"]["sol"]["h"] == pytest.approx(5 / 15)   # credited sol samples: 5 at 0.5, 10 at 1
    assert rr["theta"]["sonnet55"]["e"] == pytest.approx(0.5)
    assert sum(rr["theta"]["kimi"]["N"]) == pytest.approx(1.0)
