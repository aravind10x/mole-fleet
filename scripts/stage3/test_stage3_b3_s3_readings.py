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


# ── brief 33's dated notes 2 and 3 (G3, G4, G6, O1, O2, O5, O7, O8) and notes 4 and 5 (G7, G8, (a) to (c), O3, O4) ─────

def test_a_singular_instrument_at_floor_a_is_not_read_g3(matrix):
    sp = dr._spec(**dr._all(beta=0.0, noise=5.0))
    scores = dr.synthetic_scores(matrix, sp)
    I = rd.Instrument("C", matrix, scores["rows"], True)
    r = I.read("subset", False, True)
    assert r["a"] == {"fit_ok": False, "not_read": "floor", "n": 17} and r["b"]["not_read"] == "floor" and r["recall"] is None
    L = rd.instrument_label(r["a"], r["b"])
    assert L["label"] is None and L["a"] is None


def test_precedence_floor_then_ceiling_then_fit_o1(matrix):
    sp = dr._spec(**dr._all(beta=0.0, noise=5.0, base=6.0))        # every flag set: past the ceiling
    scores = dr.synthetic_scores(matrix, sp)
    I = rd.Instrument("C", matrix, scores["rows"], True)
    ids = I.evaluable_ids("subset")[:3]                              # too few for a fit: the ceiling still comes first
    r = I.read("subset", True, True, ids=ids)
    assert r["b"]["not_read"] == "ceiling" and r["a"]["reason"] == "the design is singular"
    r = I.read("subset", True, False, ids=ids)
    assert r["b"]["not_read"] == "floor"                             # floor before the ceiling


def test_an_unscored_application_leaves_the_denominator_not_its_item_o2():
    rng = np.random.default_rng(2)
    F = np.array([[1.0, np.nan], [0.0, 0.0], [np.nan, np.nan], [1.0, 1.0]])
    m = rd.clustered_mean(rng, F)
    assert m["n"] == 3 and m["applications"] == 5 and m["unscored_applications"] == 1 and m["point"] == pytest.approx(3 / 5) and m["k"] == 3
    a = np.array([[80.0, np.nan], [70.0, 75.0]])
    b = np.array([[10.0, 20.0], [np.nan, np.nan], [30.0, np.nan]])
    au = rd.auroc_clustered(rng, a, b)
    assert au["n_a"] == 2 and au["n_b"] == 2 and au["applications_a"] == 3 and au["applications_b"] == 3 and au["point"] == 1.0


def test_both_flags_are_read_and_the_unit_flag_stays_beside(matrix):
    sp = dr._spec(**dr._all(beta=0.0, noise=5.0))
    scores = dr.synthetic_scores(matrix, sp)
    for r in scores["rows"]:
        if r["view"] == "P_author_doc_iso" and r["judge"] == "opus48" and r["arm"] == "item" and r["flag"] is not None and r["regime"] == "candidate":
            r["flag"] = True                                           # the union flags every candidate; the unit flag is left as drawn; the sham as drawn
    I = rd.Instrument("C", matrix, scores["rows"], True)
    sham = {i: s for i, s in I.summary.items() if I.items[i]["regime"] == "sham"}
    fl = I.floor(sham)
    assert fl["b"]["quiet"]["point"] == 1.0 and fl["b_unit"]["quiet"]["point"] < 1.0
    r = I.read("subset", True, fl["b"]["pass"])
    assert r["recall"]["point"] == 1.0 and r["recall_unit"]["point"] < 1.0 and r["b"]["not_read"] == "ceiling"


def test_the_clean_set_reading_is_descriptive_and_beside_g6(matrix):
    sp = dr._spec(**dr._all(beta=0.0, noise=5.0))
    scores = dr.synthetic_scores(matrix, sp)
    clean = dr._clean(matrix, 3, 1)
    R = rd.compute(matrix, scores, None, clean)
    c = R["readings"]["C"]["clean"]
    assert c["subset"]["n"] == 14 and c["subset"]["n_excluded"] == 3 and c["subset"]["n_population"] == 17 and c["subset"]["fit_ok"]
    assert c["stratum"]["n"] == 22 and c["stratum"]["n_excluded"] == 4
    assert "label" not in c["subset"]["contrast"] and R["cascade"]["population"] == "subset"       # no label, no effect on the cascade
    assert R["clean_items"]["n_touched"] == 4
    ids = [s["id"] for s in R["sentences"]]
    assert "S-G6" in ids
    sub = next(s for s in R["sentences"] if s["id"] == "S-G6" and s["instrument"] == "C" and s["population"] == "subset")
    assert "n = 14 of 17 evaluable, 3 excluded" in sub["text"] and "no label" in sub["text"]


def test_s_g1_sits_beside_every_excluded_or_attenuated_reading_g4(matrix):
    sp = dr._spec(**dr._all(beta=0.0, noise=5.0))
    sp["seed"] = 3
    scores = dr.synthetic_scores(matrix, sp)
    R = rd.compute(matrix, scores, None, None)
    S = R["sentences"]
    for i, s in enumerate(S):
        if s["id"] in ("S-D2", "S-D3"):
            assert S[i + 1]["id"] == "S-G1" and S[i + 1]["instrument"] == s["instrument"] and S[i + 1]["population"] == s["population"] and S[i + 1]["form"] == s["form"]
    assert sum(1 for s in S if s["id"] == "S-G1") == sum(1 for s in S if s["id"] in ("S-D2", "S-D3")) + sum(1 for s in S if s["id"] == "S-R1" and "*excluded*" in s["text"] or s["id"] == "S-R1" and "*attenuated*" in s["text"])
    # O4: S-D outside the verdict population is marked descriptive, the verdict's is not
    v = R["cascade"]
    for s in S:
        if s["id"].startswith("S-D"):
            marked = "(descriptive; no verdict, section 5.4 (4))" in s["text"]
            assert marked == ((s["instrument"], s["population"]) != (v["instrument"], v["population"]))


def test_s_e_wording_when_a_is_unfit_and_b_fitted_o8():
    L = {"label": None, "a": None, "b": "excluded", "b_effective": "excluded", "conflict": False, "b_counts": True, "b_lo_net": -0.1}
    r = {"a": {"fit_ok": False, "reason": "the design is singular"}, "b": {"fit_ok": True}}
    s = rd.s_e("C", "subset", L, r, False)
    assert s["id"] == "S-E3" and "form (a) is unfit" in s["text"] and "form (b) beside reads *excluded*" in s["text"]


def test_secondary_pools_strata_as_section_4_3_does_o7():
    import inspect
    src = inspect.getsource(rd.secondary)
    assert "pooled_codes(doc)" in src and "np.unique(doc, return_inverse=True)" not in src


def test_slot_arithmetic_on_hand_made_designs_o5():
    rng = np.random.default_rng(11)
    n = 60
    C = rng.uniform(30, 80, n)
    gap, sonnet, edit = rng.gamma(2, 3, n), (rng.random(n) < 0.5).astype(float), rng.random(n)
    doc = rng.integers(0, 3, n)
    excess = 0.4 * (C - 55) + 2.0 * gap + rng.normal(0, 0.01, n)          # a slope of 0.4 a point: the contrast is 25 x 0.4
    a = rd.form_a(C, gap, sonnet, edit, doc, excess, 18.22, None, True, np.random.default_rng(1))
    assert a["contrast"]["point"] == pytest.approx(10.0, abs=0.05) and a["contrast"]["label"] == "attenuated"
    assert a["disattenuated"]["point"] == pytest.approx(10.0 / 0.846, abs=0.1)
    # form (b): O2's contrast (line at its sample mean) against O4's (line at its conditional mean given composition)
    line = 40 + 0.5 * (C - 55) + rng.normal(0, 1, n)
    logit = -0.5 + 0.12 * (C - 55)
    F = (rng.random((n, 2)) < 1 / (1 + np.exp(-logit[:, None]))).astype(float)
    b = rd.form_b(C, line, gap, sonnet, edit, doc, F, None, False, np.random.default_rng(2), 0.04)
    assert b["fit_ok"] and 0.3 < b["contrast"]["point"] < 0.95 and b["contrast"]["lo_net_of_bias"] == pytest.approx(b["contrast"]["lo"] - 0.04)
    assert b["o4"]["point"] != pytest.approx(b["contrast"]["point"])
    assert b["q1q3"]["margin"] == pytest.approx(0.228)
    # the Clopper-Pearson pair and the paired gap's sign
    assert rd.clopper_pearson(0, 10) == [0.0, pytest.approx(0.3085, abs=1e-3)] and rd.clopper_pearson(10, 10)[1] == 1.0
    assert rd.four_outcome(0.05, 0.2, 0.1, 0.3) == "attenuated"


# ── brief 33's dated notes 4 and 5 ───────────────────────────────────────────────────────────────

def test_no_s_m_sentence_without_a_lead_and_the_forbidden_families_hold_g8(fixture_results):
    r = fixture_results["floor_both"]
    assert r["cascade"]["lead"] is None and r["cascade"]["state"] == "no_verdict"
    assert not any(i.startswith("S-M") for i in r["reached"]) and r["forbidden_present"] == [] and r["ok"]
    # the family check itself: an id, a family, and the instrument-less case
    S = [{"id": "S-M1", "family": "S-M"}, {"id": "S-D3", "family": "S-D", "instrument": "C"}, {"id": "S-A2", "family": "S-A", "instrument": "C"}]
    assert dr.forbidden_present(S, {("S-M", None), ("S-D", "C"), ("S-D", "S"), ("S-A2", "S"), ("S-E", None)}) == ["S-D|C", "S-M|None"]


def test_d_rows_at_floor_a_issue_no_s_a4_or_s_a5_c(fixture_results):
    r = fixture_results["floor_d_rows"]
    assert r["ok"] and r["forbidden_present"] == [] and "S-R2" in r["reached"] and "S-F1" in r["reached"]


def test_g7s_fixtures_an_unscored_unit_and_an_open_unit_at_a_stop(fixture_results):
    r = fixture_results["errored_twice_unscored"]
    assert r["ok"] and r["subset_loss"]["C"] == {"n": 17, "evaluable": 16, "lost": 1, "provisional": False} and r["subset_loss"]["S"]["lost"] == 0
    assert r["lock_incomplete"] == {} and r["rows"] == 4344
    r = fixture_results["errored_once_stopped"]
    assert r["ok"] and r["rows"] == 4343 and r["lock_incomplete"] == {"P_author_doc_iso|opus48": {"scored_rows": 795, "of": 796}}
    assert r["cascade"]["lead"] == "S" and r["cascade"]["fallback"] and "C" not in r["subset_loss"]


def test_a_missing_unit_flag_is_missing_never_the_unions_b():
    rows = [{"view": "P_author_doc_iso", "judge": "opus48", "item_id": "i", "regime": "candidate", "arm": "item", "placement": 1, "outcome": "scored", "score": 60.0, "flag": True},
            {"view": "P_author_doc_iso", "judge": "opus48", "item_id": "i", "regime": "candidate", "arm": "item", "placement": 2, "outcome": "scored", "score": 60.0, "flag": True, "flag_unit": False},
            {"view": "P_author_doc_iso", "judge": "opus48", "item_id": "i", "regime": "candidate", "arm": "item", "placement": 3, "outcome": "scored", "score": 60.0, "flag": True, "flag_unit": None}]
    it = rd.cell_items(rows, "P_author_doc_iso", "opus48")["i"]["tri"]
    assert it[1]["flag"] is True and it[1]["flag_unit"] is None
    assert it[2]["flag"] is True and it[2]["flag_unit"] is False
    assert it[3]["flag_unit"] is None


def test_main_refuses_without_the_clean_items_file_at_its_hash_and_a_passing_g9_check_a(tmp_path):
    bad = tmp_path / "clean.json"
    with pytest.raises(SystemExit, match="clean-items"):
        rd.main(["--clean-items", str(bad)])
    bad.write_text('{"touched_ids": []}\n')
    with pytest.raises(SystemExit, match="clean-items"):
        rd.main(["--clean-items", str(bad)])
    good = rd.PROJECT / "work/stage3/b3/s3-clean-items-v0.json"
    assert rd.hashlib.sha256(good.read_bytes()).hexdigest().startswith(rd.CLEAN_ITEMS_SHA256)
    with pytest.raises(SystemExit, match="G9"):
        rd.main(["--clean-items", str(good), "--honest-check", str(tmp_path / "none.json")])
    (tmp_path / "hc.json").write_text('{"pass": false}\n')
    with pytest.raises(SystemExit, match="G9"):
        rd.main(["--clean-items", str(good), "--honest-check", str(tmp_path / "hc.json")])


def test_s_g6b_quotes_the_fits_own_reason_o4(matrix, monkeypatch):
    monkeypatch.setattr(rd, "REPLICATES", 200)
    sp = dr._spec(**dr._all(beta=0.0, noise=5.0))
    scores = dr.synthetic_scores(matrix, sp)
    R = rd.compute(matrix, scores, None, dr._clean(matrix, 15, 0))
    texts = {(s["population"]): s["text"] for s in R["sentences"] if s["id"] == "S-G6b" and s["instrument"] == "C"}
    cl = R["readings"]["C"]["clean"]
    assert set(texts) == {"subset", "stratum"}
    for pop, t in texts.items():
        assert cl[pop]["reason"] in t and "no label" in t
        if cl[pop]["n"] < 4:
            assert f"too few items for the fit (n = {cl[pop]['n']}" in t
        else:
            assert "too few items" not in t and "not read on the restricted set" in t


def test_the_results_header_names_note_3_for_s_g6_and_carries_the_union_flag_disclosure_o3():
    R = {"lock": {"rows": 4344, "expected_rows": 4344, "incomplete": {}, "stopped": None}, "cascade": {"floor_a": {"C": True, "S": True}, "state": "read", "lead": "C"},
         "sentences": [{"id": "S-S0", "family": "S-S", "text": "x"}]}
    hc = {"pass": True, "applications_sha256": "a", "cells": {
        "P_author_doc_iso|opus48": {"units": 796, "units_with_no_other_pair": 73, "of_which_single_pair_on_the_planted_document": 60, "of_which_author_absent_explained": 13,
                                     "of_which_unexplained": 0, "authors_absent_explained_no_class_write": 2, "authors_absent_unexplained": 0, "documents_absent": 0, "unit_authors": 37},
        "P_author_doc_live|opus48": {"units": 232, "units_with_no_other_pair": 26, "of_which_single_pair_on_the_planted_document": 19, "of_which_author_absent_explained": 7,
                                      "of_which_unexplained": 0, "authors_absent_explained_no_class_write": 2, "authors_absent_unexplained": 0, "documents_absent": 0, "unit_authors": 35}}}
    meta = {"plan": {"path": "p", "sha256": "0" * 64}, "matrix_sha256": "1" * 64, "scores_sha256": "2" * 64, "script_sha256": "3" * 64, "client_sha256": {}, "window_rule": "w",
            "honest_check": {**rd.honest_check_summary(hc), "sha256": "4" * 64}}
    md = rd.render_md(R, meta, {"section_7": "", "note_2026_11_02_item_5": "", "section_8_pointer": ""})
    head = md.splitlines()[0]
    assert "brief 33's dated note 3 of 2026-11-02" in head and "S-G6" in head
    assert "Union-flag disclosure (brief 33's dated note 5" in md and "73 of 796 units (26 of 232 on each live row)" in md and "as in B1" in md
    assert meta["honest_check"]["per_agent"]["identical_across_cells"] and meta["honest_check"]["per_agent"]["cells"] == 1
