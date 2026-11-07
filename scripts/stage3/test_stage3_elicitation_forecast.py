"""Tests for stage3_elicitation_forecast.py (brief 30 note 9 item 2: the $0 forecast of the six-round course with round 1's
yields folded in, beside course A's original figures). Pure simulation on invented and aggregate inputs: no file, no
model call, no item."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_forecast as fc  # noqa: E402


def test_jeffreys_posterior_params():
    assert fc.jeffreys(2, 20) == (2.5, 18.5)
    assert fc.jeffreys(0, 20) == (0.5, 20.5)


def test_drift_factor_is_one_without_drift_and_halves_linearly_to_round_four_then_holds():
    assert [fc.drift_factor(r, "none") for r in (1, 2, 4, 6)] == [1.0, 1.0, 1.0, 1.0]
    assert fc.drift_factor(1, "halving") == 1.0
    assert fc.drift_factor(4, "halving") == pytest.approx(0.5)
    assert fc.drift_factor(2, "halving") == pytest.approx(1 - 0.5 / 3)
    assert fc.drift_factor(6, "halving") == pytest.approx(0.5)
    with pytest.raises(ValueError):
        fc.drift_factor(2, "doubling")


def test_round_counts_are_bounded_and_zero_rates_give_zero():
    rng = np.random.default_rng(1)
    c, i = fc.round_counts(rng, np.full(1000, 96), np.full(1000, 0.0), np.full(1000, 0.0))
    assert c.sum() == 0 and i.sum() == 0
    c, i = fc.round_counts(rng, np.full(1000, 96), np.full(1000, 0.3), np.full(1000, 0.2))
    assert (c + i <= 96).all() and (c >= 0).all() and (i >= 0).all()
    assert c.mean() == pytest.approx(96 * 0.3, rel=0.05) and i.mean() == pytest.approx(96 * 0.2, rel=0.05)


def test_round_counts_certain_certification_takes_every_item():
    rng = np.random.default_rng(1)
    c, i = fc.round_counts(rng, np.full(50, 40), np.full(50, 1.0), np.full(50, 0.0))
    assert (c == 40).all() and (i == 0).all()


def test_floor_rule_stops_on_a_zero_illegible_count_and_not_on_a_healthy_projection():
    plan = [24, 96, 96, 96, 96, 96]
    # after round 3 (216 written): 2 certified, 0 illegible: projected illegible 0, so n_eff 0, below 12: stop
    assert bool(fc.floor_stops(np.array([2]), np.array([0]), 3, plan, M=6)[0]) is True
    # 60 certified and 30 illegible after round 3 project far above 12
    assert bool(fc.floor_stops(np.array([60]), np.array([30]), 3, plan, M=6)[0]) is False
    # the projection scales the cumulative counts by the planned items through round 6 over those through round 3
    scale = sum(plan[:6]) / sum(plan[:3])
    assert scale == pytest.approx(504 / 216)
    for c, i in ((10, 4), (8, 3)):
        want = 2 / (1 / (c * scale) + 1 / (i * scale)) < 12
        assert bool(fc.floor_stops(np.array([c]), np.array([i]), 3, plan, M=6)[0]) is want
    assert bool(fc.floor_stops(np.array([10]), np.array([4]), 3, plan, M=6)[0]) is False   # projects to about 13.3
    assert bool(fc.floor_stops(np.array([8]), np.array([3]), 3, plan, M=6)[0]) is True     # projects to about 10.2


def test_the_course_stops_by_success_when_the_statistic_is_reached_and_never_when_illegible_never_comes():
    rng = np.random.default_rng(2)
    plan = [24, 96, 96, 96, 96, 96]
    hi = fc.course_all_matched(rng, runs=200, plan=plan, p_c=np.full(200, 0.5), p_i=np.full(200, 0.4), stop=26, M=6, floor=12)
    assert (hi["outcome"] == "success").all() and hi["stop_round"].max() <= 3
    lo = fc.course_all_matched(rng, runs=200, plan=plan, p_c=np.full(200, 0.1), p_i=np.full(200, 0.0), stop=26, M=6, floor=12)
    assert (lo["outcome"] == "floor").all() and (lo["stop_round"] == 3).all()


def test_the_course_reaches_the_limit_when_floor_does_not_fire_and_success_does_not_come():
    rng = np.random.default_rng(3)
    plan = [24, 96, 96, 96, 96, 96]
    r = fc.course_all_matched(rng, runs=300, plan=plan, p_c=np.full(300, 0.04), p_i=np.full(300, 0.04), stop=26, M=6, floor=0.0)
    assert set(r["outcome"]) <= {"limit", "success"} and "floor" not in set(r["outcome"])


def test_the_matched_course_is_deterministic_by_seed_and_reports_every_round():
    kw = dict(runs=60, plan=[24, 96, 96, 96, 96, 96], p_c=np.full(60, 0.2), p_i=np.full(60, 0.1), v=np.full(60, 0.8), strata="invented",
              width=10, stop=26, M=6, floor=12)
    a = fc.course_matched(np.random.default_rng(5), **kw)
    b = fc.course_matched(np.random.default_rng(5), **kw)
    assert a["outcome"].tolist() == b["outcome"].tolist() and a["cum_c"].tolist() == b["cum_c"].tolist()
    assert a["cum_c"].shape == (60, 6) and a["matched_n_eff"].shape == (60, 6)
    assert (a["matched_n_eff"] <= a["all_n_eff"] + 1e-9).all(), "matching can only lose partners"


def test_the_matched_statistic_is_never_above_the_all_matched_one_and_wider_strata_help():
    base = dict(runs=80, plan=[24, 96, 96, 96, 96, 96], p_c=np.full(80, 0.2), p_i=np.full(80, 0.1), v=np.full(80, 0.8), strata="invented",
                stop=26, M=6, floor=0.0)
    narrow = fc.course_matched(np.random.default_rng(7), width=10, **base)
    wide = fc.course_matched(np.random.default_rng(7), width=25, **base)
    assert wide["matched_n_eff"][:, -1].mean() > narrow["matched_n_eff"][:, -1].mean()


def test_the_replication_of_course_as_original_figures_lands_near_the_reconciles_0_93_and_0_70():
    r = fc.replicate_course_a(runs=12000, seed=20261216)
    assert r["no_drift"]["p_success"] == pytest.approx(0.93, abs=0.06)
    assert r["halving"]["p_success"] == pytest.approx(0.70, abs=0.08)


ROUND1 = {"written": 24, "valid": 20, "certified": 2, "illegible": 0,
          "items": [{"document": "d1", "composition": 55.0, "class": "certified"}, {"document": "d2", "composition": 62.0, "class": "certified"}],
          "valid_strata": [("d1", 55.0), ("d2", 62.0), ("d3", 48.0), ("d1", 59.0)] * 5}


def test_forecast_keeps_round_1_as_observed_and_reports_every_scenario_drift_and_strata():
    r = fc.forecast(ROUND1, runs_all=400, runs_matched=60, seed=3)
    assert set(r["scenarios"]) == {"round1_only", "e2_prior_plus_round1", "e2_prior_only"}
    for name, sc in r["scenarios"].items():
        for drift in ("none", "halving"):
            row = sc[drift]
            assert set(row) >= {"all_matched", "matched_invented", "matched_empirical"}
            for key in ("all_matched", "matched_invented", "matched_empirical"):
                m = row[key]
                assert set(m["p_success_by_round"]) == {"2", "3", "4", "5", "6"}
                if name != "e2_prior_only":       # the decomposition scenario samples round 1 too
                    assert m["certified_after"]["3"]["mean"] >= 2
                assert m["certified_after"]["6"]["mean"] >= m["certified_after"]["3"]["mean"]
                assert 0.0 <= m["p_success_by_round"]["6"] <= 1.0
                assert abs(m["p_success"] + m["p_floor"] + m["p_limit"] - 1.0) < 3e-4   # each rounded to 4 decimals
    assert r["round1"]["certified"] == 2 and r["round1"]["illegible"] == 0
    assert r["replication"]["no_drift"]["p_success"] > 0.5


def test_forecast_posteriors_are_jeffreys_for_round_1_only_and_prior_plus_counts_for_the_pooled_scenario():
    r = fc.forecast(ROUND1, runs_all=100, runs_matched=10, seed=3)
    p = r["posteriors"]
    assert p["round1_only"]["p_c"] == [2.5, 18.5] and p["round1_only"]["p_i"] == [0.5, 20.5] and p["round1_only"]["v"] == [20.5, 4.5]
    a, b = p["e2_prior_plus_round1"]["p_i"]
    assert a == pytest.approx(0.8 * 2 + 0) and b == pytest.approx(37 - 0.8 * 2 + 20)
    assert p["e2_prior_only"]["p_c"] == [pytest.approx(0.8 * 3), pytest.approx(37 - 0.8 * 3)]
    assert p["e2_prior_only"]["p_i"] == [pytest.approx(0.8 * 2), pytest.approx(37 - 0.8 * 2)]
    a, b = p["e2_prior_plus_round1"]["p_c"]
    assert a == pytest.approx(0.8 * 3 + 2) and b == pytest.approx(37 - 0.8 * 3 + 18)


def test_forecast_is_deterministic_by_seed():
    a = fc.forecast(ROUND1, runs_all=300, runs_matched=30, seed=9)
    b = fc.forecast(ROUND1, runs_all=300, runs_matched=30, seed=9)
    assert fc.canonical(a) == fc.canonical(b)


def test_load_round1_reads_counts_classes_documents_and_compositions_from_the_round_files(tmp_path):
    import json
    p3 = tmp_path
    (p3 / "round-1" / "gpt61sol" / "converted").mkdir(parents=True)
    (p3 / "raters" / "gpt61sol-r1-cert").mkdir(parents=True)
    (p3 / "round-1-v0.json").write_text(json.dumps({"writers": {"gpt61sol": {"funnel": {"written": 24, "valid": 3, "quiet": 2, "certified": 1, "quiet_but_illegible": 1}}}}))
    (p3 / "round-1" / "gpt61sol" / "round-record.json").write_text(json.dumps({"ids_by_class": {"certified": ["a"], "quiet_but_illegible": ["b"], "loud": ["c"]}}))
    (p3 / "round-1" / "gpt61sol" / "converted" / "key.json").write_text(json.dumps({"triples": {"a": {"document": "D1"}, "b": {"document": "D2"}, "c": {"document": "D1"}}}))
    (p3 / "raters" / "gpt61sol-r1-cert" / "gate-i.json").write_text(json.dumps({"composition": {"a": 50.0, "b": 61.5, "c": 70.0}}))
    r = fc.load_round1(p3, "gpt61sol", 1)
    assert (r["written"], r["valid"], r["certified"], r["illegible"]) == (24, 3, 1, 1)
    assert r["items"] == [{"document": "D1", "composition": 50.0, "class": "certified"}, {"document": "D2", "composition": 61.5, "class": "quiet_but_illegible"}]
    assert sorted(r["valid_strata"]) == [("D1", 50.0), ("D1", 70.0), ("D2", 61.5)]


def test_the_e2_prior_is_scaled_by_round_1s_quiet_share_when_it_is_known_not_by_the_reconciles_0_8():
    r1 = dict(ROUND1, quiet=13)
    p = fc.posteriors(r1)
    q = 13 / 20
    assert p["e2_prior_only"]["p_c"] == [pytest.approx(q * 3), pytest.approx(37 - q * 3)]
    assert p["e2_prior_only"]["p_i"] == [pytest.approx(q * 2), pytest.approx(37 - q * 2)]
    assert p["e2_prior_plus_round1"]["p_c"] == [pytest.approx(q * 3 + 2), pytest.approx(37 - q * 3 + 18)]
    assert p["e2_prior_plus_round1"]["p_i"] == [pytest.approx(q * 2 + 0), pytest.approx(37 - q * 2 + 20)]
    assert p["round1_only"]["p_c"] == [2.5, 18.5], "the round-1-only posterior does not use E2 at all"
    assert fc.posteriors(ROUND1)["e2_prior_only"]["p_c"][0] == pytest.approx(0.8 * 3), "the 0.8 stays as the fallback"


def test_one_writer_original_is_below_the_two_writer_original_and_deterministic():
    a = fc.one_writer_original(runs=4000, seed=11)
    b = fc.one_writer_original(runs=4000, seed=11)
    two = fc.replicate_course_a(runs=4000, seed=11)["no_drift"]["p_success"]
    assert a == b and 0.0 <= a < two


# ---- after round 3: observed strata, per-writer Jeffreys yields, the bar reading (brief 30 note 12 and its addendum) ----

def _items(doc_comp, cls):
    return [{"document": d, "composition": c, "class": cls} for d, c in doc_comp]


OBS = {"rounds_done": 3, "writers": {
    "sol": {"rounds": [{"round": 1, "written": 24, "valid": 20, "certified": 2, "illegible": 0},
                       {"round": 2, "written": 96, "valid": 80, "certified": 10, "illegible": 2},
                       {"round": 3, "written": 96, "valid": 80, "certified": 10, "illegible": 2}],
            "items": _items([("d1", 52.0), ("d2", 61.0)] * 11, "certified") + _items([("d1", 53.0), ("d3", 48.0)], "quiet_but_illegible"),
            "valid_strata": [("d1", 52.0), ("d2", 61.0), ("d3", 48.0), ("d4", 70.0)] * 5},
    "muse": {"rounds": [{"round": 3, "written": 96, "valid": 60, "certified": 6, "illegible": 1}],
             "items": _items([("d1", 55.0)] * 6, "certified") + _items([("d2", 58.0)], "quiet_but_illegible"),
             "valid_strata": [("d1", 55.0), ("d2", 58.0), ("d5", 40.0)] * 4}}}


def test_writer_posterior_is_jeffreys_on_the_cumulative_observed_counts_per_valid_item():
    p = fc.writer_posterior(OBS["writers"]["sol"]["rounds"])
    assert p["p_c"] == [22.5, 158.5] and p["p_i"] == [4.5, 176.5] and p["v"] == [180.5, 36.5]
    q = fc.writer_posterior(OBS["writers"]["muse"]["rounds"])
    assert q["p_c"] == [6.5, 54.5] and q["p_i"] == [1.5, 59.5] and q["v"] == [60.5, 36.5]


def test_bar_reading_calls_a_value_on_the_margin_below_half():
    assert fc.bar_reading(0.49, 20000) == "below 0.5"
    assert fc.bar_reading(0.505, 20000) == "below 0.5", "inside the Monte Carlo margin of 0.5"
    assert fc.bar_reading(0.50, 20000) == "below 0.5"
    assert fc.bar_reading(0.60, 20000) == "at or above 0.5"
    assert fc.bar_reading(0.52, 200) == "below 0.5", "a small run count widens the margin"


def test_forecast_after_carries_the_observed_counts_and_reports_the_remaining_rounds_per_writer_and_in_total():
    r = fc.forecast_after(OBS, runs_all=300, runs_matched=40, seed=4)
    assert r["rounds_done"] == 3 and set(r["writers"]) == {"sol", "muse"}
    base = r["observed_totals"]
    assert base == {"certified": 28, "illegible": 5, "written": 312, "valid": 240}
    for drift in ("none", "halving"):
        for stat in ("all_matched", "matched_observed"):
            row = r["scenarios"][drift][stat]
            assert set(row["p_success_by_round"]) == {"4", "5", "6"}
            assert set(row["with_floor_rule"]) >= {"p_success", "p_floor", "p_limit"} and "p_success" in row["without_floor_rule"]
            assert row["certified_after"]["3"]["mean"] == pytest.approx(28.0), "round 3 is as observed in every run"
            assert row["certified_after"]["6"]["mean"] > row["certified_after"]["3"]["mean"]
            assert row["bar_reading"] in ("below 0.5", "at or above 0.5")
    assert set(r["per_further_round"]["certified_added"]) == {"4", "5", "6"} and set(r["per_further_round"]["by_writer"]) == {"sol", "muse"}


def test_forecast_after_is_deterministic_by_seed_and_uses_only_the_writers_it_is_given():
    one = {"rounds_done": 3, "writers": {"sol": OBS["writers"]["sol"]}}
    a = fc.forecast_after(one, runs_all=200, runs_matched=30, seed=8)
    b = fc.forecast_after(one, runs_all=200, runs_matched=30, seed=8)
    assert fc.canonical(a) == fc.canonical(b) and set(a["writers"]) == {"sol"}


def test_floor_now_is_read_on_the_observed_counts_alone():
    r = fc.forecast_after(OBS, runs_all=100, runs_matched=10, seed=1)
    assert isinstance(r["floor_rule_now"]["fires"], bool) and r["floor_rule_now"]["projected_n_eff"] >= 0
    # 28 certified and 5 illegible after 312 written project by the planned items: 312 + 2 writers x 3 rounds x 96 = 888
    c, i = 28 * 888 / 312, 5 * 888 / 312
    assert r["floor_rule_now"]["projected_n_eff"] == pytest.approx(2 / (1 / c + 1 / i), rel=1e-6)


def test_load_observed_accumulates_each_writers_rounds_items_and_valid_strata(tmp_path):
    import json
    for n in (1, 2):
        p3 = tmp_path
        (p3 / f"round-{n}" / "w" / "converted").mkdir(parents=True)
        (p3 / "raters" / f"w-r{n}-cert").mkdir(parents=True)
        (p3 / f"round-{n}-v0.json").write_text(json.dumps({"writers": {"w": {"funnel": {"written": 10, "valid": 3, "quiet": 2, "certified": 1, "quiet_but_illegible": 1}}}}))
        (p3 / f"round-{n}" / "w" / "round-record.json").write_text(json.dumps({"ids_by_class": {"certified": [f"a{n}"], "quiet_but_illegible": [f"b{n}"], "loud": [f"c{n}"]}}))
        (p3 / f"round-{n}" / "w" / "converted" / "key.json").write_text(json.dumps({"triples": {f"a{n}": {"document": "D1"}, f"b{n}": {"document": "D2"}, f"c{n}": {"document": "D1"}}}))
        (p3 / "raters" / f"w-r{n}-cert" / "gate-i.json").write_text(json.dumps({"composition": {f"a{n}": 50.0 + n, f"b{n}": 60.0 + n, f"c{n}": 70.0}}))
    obs = fc.load_observed(tmp_path, {"w": [1, 2]}, rounds_done=2)
    w = obs["writers"]["w"]
    assert obs["rounds_done"] == 2 and [r["round"] for r in w["rounds"]] == [1, 2]
    assert [(r["written"], r["valid"], r["certified"], r["illegible"]) for r in w["rounds"]] == [(10, 3, 1, 1), (10, 3, 1, 1)]
    assert len(w["items"]) == 4 and len(w["valid_strata"]) == 6
    assert {i["class"] for i in w["items"]} == {"certified", "quiet_but_illegible"}


def test_render_after_md_carries_the_bar_reading_the_cases_beside_the_floor_rule_and_phase_e():
    r = fc.forecast_after(OBS, runs_all=300, runs_matched=40, seed=6)
    md = fc.render_after_md(r, "abc12345")
    for needle in ("The reading for the bar", "reads: ", "halving", "every certified item matched", "The floor rule now", "Phase E: the expected certified count per further round",
                   "`sol` certified", "`muse` certified", "A value on the margin of the bar"):
        assert needle in md, needle
    assert md.count("| 4 |") >= 1 and md.count("| 6 |") >= 1


# ── the retention-adjusted forecast (the coordinator's message of 8 Nov, after the application check) ──────────────

STOCK = {"sol": {"certified": 20, "illegible": 0, "items": _items([("d1", 52.0), ("d2", 61.0)] * 10, "certified")},
         "muse": {"certified": 2, "illegible": 2, "items": _items([("d1", 55.0), ("d1", 57.0)], "certified") + _items([("d1", 56.0), ("d2", 40.0)], "quiet_but_illegible")}}
ONE = {"c": [1000.0, 0.001], "i": [1000.0, 0.001]}      # retention of about one
ZERO = {"c": [0.001, 1000.0], "i": [0.001, 1000.0]}     # retention of about zero


def _case(name, **kw):
    return dict({"name": name, "writing": ["muse"], "retention": None, "i_scale": None, "i_post": None}, **kw)


def _run(cases, seed=5, runs_all=400, runs_matched=60):
    return fc.forecast_retained(OBS, STOCK, cases, runs_all=runs_all, runs_matched=runs_matched, seed=seed)


def test_retained_forecast_starts_from_the_placeable_stock_not_the_observed_counts():
    r = _run([_case("b", retention={"muse": ONE})])
    row = r["cases"]["b"]["all_matched"]
    assert row["certified_after"]["3"]["mean"] == pytest.approx(22.0) and row["illegible_after"]["3"]["mean"] == pytest.approx(2.0)
    assert r["stock"]["muse"] == {"certified": 2, "illegible": 2}
    assert r["stock_matched"]["n_c_total"] == 22 and r["stock_matched"]["n_i_total"] == 2


def test_retained_forecast_a_writer_not_writing_adds_nothing_and_the_stock_stays_the_same():
    r = _run([_case("none", writing=[])])
    row = r["cases"]["none"]["all_matched"]
    assert row["certified_after"]["6"]["mean"] == pytest.approx(22.0) and row["illegible_after"]["6"]["mean"] == pytest.approx(2.0)
    assert row["with_floor_rule"]["p_success"] == 0.0


def test_retained_forecast_retention_scales_the_yield_of_the_writers_who_write():
    hi = _run([_case("hi", retention={"muse": ONE})])["cases"]["hi"]["all_matched"]
    lo = _run([_case("lo", retention={"muse": ZERO})])["cases"]["lo"]["all_matched"]
    assert lo["certified_after"]["6"]["mean"] == pytest.approx(22.0, abs=0.2)
    assert lo["illegible_after"]["6"]["mean"] == pytest.approx(2.0, abs=0.2)
    assert hi["certified_after"]["6"]["mean"] > lo["certified_after"]["6"]["mean"] + 15
    assert hi["illegible_after"]["6"]["mean"] > lo["illegible_after"]["6"]["mean"] + 2


def test_retained_forecast_scales_the_illegible_yield_alone_when_asked():
    base = _run([_case("a", retention={"muse": ONE})])["cases"]["a"]["all_matched"]
    scaled = _run([_case("s", retention={"muse": ONE}, i_scale={"muse": 0.0})])["cases"]["s"]["all_matched"]
    assert scaled["illegible_after"]["6"]["mean"] == pytest.approx(2.0)
    assert scaled["certified_after"]["6"]["mean"] == pytest.approx(base["certified_after"]["6"]["mean"], rel=0.1)


def test_retained_forecast_an_illegible_posterior_override_replaces_the_observed_one():
    r = _run([_case("o", retention={"muse": ONE}, i_post={"muse": [0.001, 1000.0]})])["cases"]["o"]["all_matched"]
    assert r["illegible_after"]["6"]["mean"] == pytest.approx(2.0, abs=0.2)


def test_retained_forecast_is_deterministic_by_seed_and_reports_round_four_alone_beside_the_course():
    a = _run([_case("b", retention={"muse": ONE})], seed=9)
    b = _run([_case("b", retention={"muse": ONE})], seed=9)
    assert fc.canonical(a) == fc.canonical(b)
    row = a["cases"]["b"]["matched_observed"]
    assert set(row["p_success_by_round"]) == {"4", "5", "6"} and row["bar_reading"] in ("below 0.5", "at or above 0.5")


def test_retained_forecast_no_further_round_reads_the_stock_alone():
    r = _run([_case("b", retention={"muse": ONE})])
    nf = r["no_further_round"]
    assert nf["matched_n_eff"] == pytest.approx(r["stock_matched"]["n_eff"]) and nf["reaches_stop"] is False


def _check_rows():
    rows = []
    for w, cls, doc, comp, drop in [("sol", "certified", "/a/d1.md", 50.0, False), ("sol", "certified", "/a/d2.md", 55.0, True),
                                    ("muse", "certified", "/a/d1.md", 48.0, False), ("muse", "quiet_but_illegible", "/a/d1.md", 47.0, False),
                                    ("muse", "quiet_but_illegible", "/a/d3.md", 41.0, True)]:
        rows.append({"writer": w, "round": 3, "class": cls, "document": doc, "composition": comp, "drop": drop})
    return rows


def test_stock_from_check_keeps_the_items_that_survive_the_rule_and_counts_them_by_writer():
    s = fc.stock_from_check({"items": _check_rows()}, ["sol", "muse"])
    assert s["sol"]["certified"] == 1 and s["sol"]["illegible"] == 0
    assert s["muse"]["certified"] == 1 and s["muse"]["illegible"] == 1
    assert s["muse"]["items"] == [{"document": "/a/d1.md", "composition": 48.0, "class": "certified"},
                                  {"document": "/a/d1.md", "composition": 47.0, "class": "quiet_but_illegible"}]


def test_retention_from_check_is_a_jeffreys_posterior_on_the_kept_share_per_class():
    r = fc.retention_from_check({"items": _check_rows()}, "muse")
    assert r["c"] == [0.5 + 1, 0.5 + 0] and r["i"] == [0.5 + 1, 0.5 + 1]
    assert r["counts"] == {"certified": [1, 1], "illegible": [1, 2]}
