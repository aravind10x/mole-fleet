"""Tests for stage3_b3_s3_readings.py (brief 33 A2): the plan's rules where they differ from Part 3's simulator (the
exception table, each asserted), the label table, the instrument label and the cascade on constructed records, the
analysis lock, and reachability: every fixture of stage3_b3_s3_dryrun.FIXTURES reaches the sentence ids it names (each
runs the whole pipeline on a synthetic scores file built from the committed matrix; nothing drawn, nothing applied).

Run: cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_s3_readings.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_power_v3 as pv  # noqa: E402
import stage3_b3_s3_dryrun as dr  # noqa: E402
import stage3_b3_s3_readings as rd  # noqa: E402


@pytest.fixture(scope="module")
def matrix():
    return dr.load_matrix()


# ── the exception table against Part 3's simulator ───────────────────────────────────────────────

def test_replicate_failure_threshold_is_the_plans_ten_percent_not_the_simulators():
    assert rd.FAIL_SHARE == 0.10 and pv.NONCONV_MAX == 0.025
    ok = np.ones(2000, bool)
    ok[:199] = False
    assert rd.fit_failure(True, ok, None) is None            # 199 of 2,000 fail: under 10 percent, the fit stands
    ok[:201] = False
    assert rd.fit_failure(True, ok, None) == "201 of 2,000 replicates failed"
    assert pv.too_many_failures(ok)                           # the simulator's 2.5 percent rule would already have failed at 199


def test_bootstrap_is_2000_replicates_at_seed_20261152_not_the_simulators_1000():
    assert rd.REPLICATES == 2000 and pv.REPLICATES == 1000 and rd.BOOT_SEED == 20261152


def test_q1_q3_are_the_full_net_sets_fixed_quartiles_for_every_population():
    assert (rd.Q1, rd.Q3) == (47.5, 66.5) and rd.MARGIN_Q == pytest.approx(0.228)


def test_form_b_includes_the_top_two_gap_covariate_and_form_a_too(matrix):
    rng = np.random.default_rng(3)
    n = 40
    C, line, gap = rng.normal(55, 15, n), rng.normal(40, 8, n), rng.gamma(2, 3, n)
    sonnet, edit = (rng.random(n) < 0.5).astype(float), rng.random(n)
    doc = rng.integers(0, 3, n)
    F = (rng.random((n, 2)) < 0.5).astype(float)
    b = rd.form_b(C, line, gap, sonnet, edit, doc, F, None, True, np.random.default_rng(1), 0.04)
    assert "gap" in b["names"] and "line" in b["names"]
    a = rd.form_a(C, gap, sonnet, edit, doc, rng.normal(0, 5, n), 18.22, None, True, np.random.default_rng(2))
    assert "gap" in a["names"]


def test_a_singular_design_is_a_fit_failure_although_the_simulators_fitter_converges():
    rng = np.random.default_rng(5)
    n = 30
    C = rng.normal(55, 15, n)
    sonnet = np.ones(n)                                     # a covariate constant in the population
    edit, gap, line = rng.random(n), rng.gamma(2, 3, n), rng.normal(40, 8, n)
    doc = np.zeros(n, int)
    F = (rng.random((n, 2)) < 0.5).astype(float)
    # Codex's finding (brief 33's exception table): the simulator's form_a returns fit_ok on a rank-deficient design (lstsq solves it)
    assert pv.form_a(np.random.default_rng(1), C, gap, sonnet, edit, doc, rng.normal(0, 5, n), 1000, 18.22, (47.5, 66.5))["fit_ok"] is True
    b = rd.form_b(C, line, gap, sonnet, edit, doc, F, None, False, np.random.default_rng(1), 0.04)
    assert b["fit_ok"] is False and b["reason"] == "the design is singular"
    a = rd.form_a(C, gap, sonnet, edit, doc, rng.normal(0, 5, n), 18.22, None, False, np.random.default_rng(2))
    assert a["fit_ok"] is False and a["reason"] == "the design is singular"


def test_replicates_that_lose_a_factor_level_held_by_one_item_fail_by_rank():
    rng = np.random.default_rng(7)
    n = 17
    C, gap, edit = rng.normal(55, 15, n), rng.gamma(2, 3, n), rng.random(n)
    sonnet = np.zeros(n)
    sonnet[0] = 1.0                                          # the level held by one item
    a = rd.form_a(C, gap, sonnet, edit, np.zeros(n, int), rng.normal(0, 5, n), 18.22, None, False, np.random.default_rng(2))
    share = a["failed_replicates"] / rd.REPLICATES
    assert 0.25 < share < 0.5 and a["reason"].endswith("of 2,000 replicates failed")   # about (1 - 1/n)^n of the replicates omit it


def test_the_floor_is_computed_once_on_the_full_set_against_the_sham(matrix):
    sp = dr._spec(**dr._all(beta=0.0, noise=5.0))
    scores = dr.synthetic_scores(matrix, sp)
    I = rd.Instrument("C", matrix, scores["rows"], True)
    sham = {i: s for i, s in I.summary.items() if I.items[i]["regime"] == "sham"}
    fl = I.floor(sham)
    assert fl["n_quiet"] == 73 and fl["n_sham"] == 22 and fl["a"]["n_a"] == 73 and fl["a"]["n_b"] == 22


def test_the_cascade_is_seven_ordered_steps_on_constructed_records():
    class I:  # noqa: N801
        def __init__(self, complete=True):
            self.complete = complete
    inst = {"C": I(), "S": I()}
    floors = {"C": {"a": {"pass": True}}, "S": {"a": {"pass": True}}}

    def R(c_sub, c_str, s_sub, s_str, c_full, s_full):
        f = lambda ok: {"a": {"fit_ok": ok, "reason": None if ok else "the design is singular"}}  # noqa: E731
        return {"C": {"subset": f(c_sub), "stratum": f(c_str), "full": f(c_full)}, "S": {"subset": f(s_sub), "stratum": f(s_str), "full": f(s_full)}}
    c = rd.cascade(inst, floors, R(True, True, True, True, True, True))
    assert c["state"] == "read" and c["step"] == 1 and c["population"] == "subset" and c["instrument"] == "C" and not c["fallback"]
    c = rd.cascade(inst, floors, R(False, True, True, True, True, True))
    assert c["step"] == 2 and c["steps"][0]["sentence"] == "S-C1"
    c = rd.cascade(inst, floors, R(False, False, True, True, True, True))
    assert c["step"] == 3 and c["instrument"] == "S" and c["fallback"] and c["steps"][1]["sentence"] == "S-C3"
    c = rd.cascade(inst, floors, R(False, False, False, True, True, True))
    assert c["step"] == 4 and c["steps"][2]["sentence"] == "S-C1"
    c = rd.cascade(inst, floors, R(False, False, False, False, True, True))
    assert c["state"] == "third" and c["step"] == 5 and c["instrument"] == "S" and c["steps"][3]["sentence"] == "S-C2"
    c = rd.cascade(inst, floors, R(False, False, False, False, True, False))
    assert c["state"] == "third" and c["step"] == 6 and c["instrument"] == "C" and c["steps"][4]["sentence"] == "S-C3b"
    c = rd.cascade(inst, floors, R(False, False, False, False, False, False))
    assert c["state"] == "no_verdict" and c["steps"][-1]["step"] == 7 and c["sentence"] == "S-C4"
    # the carrier at floor: S leads from step 1 as the fallback carrier; no population step for a floor
    c = rd.cascade(inst, {"C": {"a": {"pass": False}}, "S": {"a": {"pass": True}}}, R(True, True, True, True, True, True))
    assert c["lead"] == "S" and c["fallback"] and c["step"] == 1 and c["population"] == "subset"
    # S at floor while C leads and C is unfit on both: step 2 fails straight to the third branch (S-C2)
    c = rd.cascade(inst, {"C": {"a": {"pass": True}}, "S": {"a": {"pass": False}}}, R(False, False, True, True, True, True))
    assert c["state"] == "third" and c["step"] == 5 and c["instrument"] == "C" and c["steps"][1]["sentence"] == "S-C2"
    c = rd.cascade(inst, {"C": {"a": {"pass": False}}, "S": {"a": {"pass": False}}}, R(True, True, True, True, True, True))
    assert c["state"] == "no_verdict" and c["sentence"] == "S-A3"


def test_the_label_table_of_section_5_3():
    assert rd.four_outcome(1.0, 30.0, 20.0, 18.22) == "present"
    assert rd.four_outcome(1.0, 15.0, 8.0, 18.22) == "attenuated"
    assert rd.four_outcome(-5.0, 10.0, 2.0, 18.22) == "excluded"
    assert rd.four_outcome(-5.0, 20.0, 8.0, 18.22) == "inconclusive"
    assert rd.four_outcome(0.0, 10.0, 2.0, 18.22) == "excluded"      # L = 0 is "L <= 0"


def test_the_instrument_label_and_form_b_s_bias_net_rule():
    a = {"fit_ok": True, "contrast": {"label": "excluded"}}
    b = {"fit_ok": True, "contrast": {"label": "present", "lo_net_of_bias": 0.01}}
    L = rd.instrument_label(a, b)
    assert L["label"] == "inconclusive" and L["conflict"]
    b["contrast"]["lo_net_of_bias"] = -0.01
    L = rd.instrument_label(a, b)
    assert L["label"] == "excluded" and not L["conflict"] and not L["b_counts"]
    b = {"fit_ok": True, "contrast": {"label": "attenuated", "lo_net_of_bias": 0.02}}
    assert rd.instrument_label(a, b)["label"] == "excluded"          # one step: (a)'s label stands
    b = {"fit_ok": True, "contrast": {"label": "excluded", "lo_net_of_bias": -0.3}}
    assert rd.instrument_label({"fit_ok": True, "contrast": {"label": "present"}}, b)["conflict"]   # (b) excluded counts by the table alone
    assert rd.instrument_label(a, {"fit_ok": False, "not_read": "ceiling"})["b_not_read"] == "ceiling"


def test_the_analysis_lock_refuses_a_short_file_without_a_stopped_record(matrix):
    sp = dr._spec()
    scores = dr.synthetic_scores(matrix, sp)
    assert len(scores["rows"]) == 4344
    assert rd.analysis_lock(scores)["incomplete"] == {}
    short = {"rows": scores["rows"][:-1], "stopped": None}
    with pytest.raises(SystemExit, match="analysis lock"):
        rd.analysis_lock(short)
    short["stopped"] = {"incomplete_rows": {"O_diff|sol": {"scored_rows": 231, "of": 232}}}
    lk = rd.analysis_lock(short)
    assert "O_diff|sol" in lk["incomplete"] and "O_diff|sol" not in lk["complete_cells"]
    short["stopped"] = {"incomplete_rows": {"O_diff|opus48": {"scored_rows": 231, "of": 232}}}   # names the wrong row
    with pytest.raises(SystemExit, match="does not name"):
        rd.analysis_lock(short)


def test_a_refused_component_makes_the_item_not_evaluable_under_that_instrument_only(matrix):
    sp = dr._spec()
    sid = matrix["populations"]["subset"]["ids"][0]
    sp["refuse"] = [[sid, "P_author_doc_iso", "opus48", "line", 2, 1]]
    scores = dr.synthetic_scores(matrix, sp)
    C = rd.Instrument("C", matrix, scores["rows"], True)
    S = rd.Instrument("S", matrix, scores["rows"], True)
    assert not C.summary[sid]["evaluable"] and S.summary[sid]["evaluable"]
    assert C.loss("subset") == {"n": 17, "evaluable": 16, "lost": 1, "provisional": False}
    assert S.loss("subset")["lost"] == 0


# ── reachability: every fixture reaches its sentence ids ──────────────────────────────────────────

@pytest.fixture(scope="module")
def fixture_results():
    """Every fixture run once, in parallel (each runs the whole pipeline with 2,000-replicate bootstraps)."""
    import multiprocessing as mp
    import os
    procs = int(os.environ.get("S3_FIXTURE_PROCS", "5"))
    names = sorted(dr.FIXTURES)
    dr._G["matrix"] = dr.load_matrix()
    with mp.get_context("fork").Pool(procs) as pool:
        outs = pool.map(dr._fixture_one, names, chunksize=1)
    return dict(zip(names, outs))


@pytest.mark.parametrize("name", sorted(dr.FIXTURES))
def test_fixture_reaches_its_sentence_ids(name, fixture_results):
    r = fixture_results[name]
    assert r["ok"], (name, r["missing"], r["cascade"])


def test_every_sentence_id_is_reached_by_some_fixture_except_the_decided_ones(fixture_results):
    reached = set()
    for r in fixture_results.values():
        reached |= set(r["reached"])
    missing = [s for s in dr.ALL_SENTENCES if s not in reached]
    assert missing == [], missing
    assert "S-P1" in dr.UNREACHABLE and "S4-1" in dr.UNREACHABLE
