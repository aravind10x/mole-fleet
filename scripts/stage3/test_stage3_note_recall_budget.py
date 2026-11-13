"""Tests for stage3_note_recall_budget.py (line NOTE, recall against honest budget, blue side).

Synthetic scores only: no corpus, cache, key or recorded file is read. The rules under test are the
ones that decide a count in the note: the threshold at each budget (the seal's randomised tie rule),
recall (expected over the tie draw and realised on the seal's label-hashed draw), the chain-clustered
bootstrap (null units and applications resampled together), and the tail counts (units above the
threshold, the chains they sit on, distinct writes among them)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_thresholds as th  # noqa: E402
import stage3_note_recall_budget as nr  # noqa: E402


def U(label, score, chain=("doc", 0), write=0):
    return {"label": label, "score": score, "chain": chain, "write_index": write}


def A(label, score, chain=("doc", 0), regime="middle"):
    return {"key": label, "label": label, "score": score, "chain": chain, "regime": regime}


# ── the constants the brief fixes ────────────────────────────────────────────────────────────

def test_constants_are_the_briefs():
    assert nr.BUDGETS == (0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20)
    assert nr.N_BOOT == 2000
    assert nr.BOOT_SEED == 20261113
    assert nr.TIE_SEED == 20261112


# ── the threshold at each budget ─────────────────────────────────────────────────────────────

def test_rule_gives_the_null_exactly_its_budget():
    scores = [5] * 40 + [10] * 30 + [20] * 20 + [60] * 6 + [72] * 4
    for b in nr.BUDGETS:
        rule = nr.fit_rule(scores, b)
        assert abs(th.expected_flag_rate(scores, rule) - b) < 1e-12, b
        assert rule["seed"] == nr.TIE_SEED


def test_rule_at_five_percent_on_a_tied_null_is_the_seals_rule():
    scores = [5] * 40 + [10] * 30 + [20] * 20 + [60] * 6 + [72] * 4
    r = nr.fit_rule(scores, 0.05)
    assert r["threshold"] == 60 and abs(r["p_tie"] - 1 / 6) < 1e-12      # 4 above, 6 at, need 5 of 100


def test_threshold_falls_as_budget_rises():
    rng = np.random.default_rng(3)
    scores = [int(x) for x in rng.integers(0, 101, size=254)]
    ts = [nr.fit_rule(scores, b)["threshold"] for b in nr.BUDGETS]
    assert ts == sorted(ts, reverse=True)


def test_one_percent_is_two_and_a_half_units():
    assert abs(nr.units_at_budget(254, 0.01) - 2.54) < 1e-12
    assert abs(nr.units_at_budget(254, 0.02) - 5.08) < 1e-12


# ── the vectorised fit and recall agree with the seal's code ─────────────────────────────────

def test_vectorised_fit_matches_the_seals_rule_on_random_nulls():
    rng = np.random.default_rng(11)
    for trial in range(30):
        n = int(rng.integers(20, 300))
        scores = [int(x) for x in rng.integers(0, 101, size=n)] if trial % 2 else [int(x) for x in rng.choice([10, 30, 50, 70], size=n)]
        apps = [int(x) for x in rng.integers(0, 101, size=40)]
        H = np.bincount(scores, minlength=nr.V).astype(float)[None, :]
        Ha = np.bincount(apps, minlength=nr.V).astype(float)[None, :]
        for b in nr.BUDGETS:
            t, p = nr.fit_rows(H, b)
            rule = th.randomised_threshold(scores, b, seed=1)
            assert int(t[0]) == rule["threshold"], (trial, b)
            assert abs(float(p[0]) - rule["p_tie"]) < 1e-9, (trial, b)
            got = float(nr.recall_rows(Ha, t, p)[0])
            assert abs(got - th.expected_flag_rate(apps, rule)) < 1e-9, (trial, b)


# ── recall, expected and realised ────────────────────────────────────────────────────────────

def test_expected_recall_of_applications_under_a_null_rule():
    null = [10] * 90 + [50] * 10
    rule = nr.fit_rule(null, 0.05)               # t = 50, p_tie = 0.5
    assert rule["threshold"] == 50 and abs(rule["p_tie"] - 0.5) < 1e-12
    assert abs(nr.expected_recall([10, 50, 60, 90], rule) - (0.5 + 1 + 1) / 4) < 1e-12


def test_realised_recall_uses_the_label_hashed_tie_draw():
    null = [10] * 90 + [50] * 10
    rule = nr.fit_rule(null, 0.05)
    apps = [A(f"a{i}", 50) for i in range(200)] + [A("hi", 99), A("lo", 1)]
    got = nr.realised_recall(apps, rule)
    want = sum(th.is_flagged(a["score"], rule, a["label"]) for a in apps) / len(apps)
    assert got == want
    tied = sum(th.is_flagged(50, rule, f"a{i}") for i in range(200))
    assert 70 < tied < 130                       # about half of 200 at p_tie 0.5


def test_realised_recall_is_monotone_in_budget_for_fixed_labels():
    rng = np.random.default_rng(5)
    null = [int(x) for x in rng.integers(0, 101, size=254)]
    apps = [A(f"x{i}", int(s)) for i, s in enumerate(rng.integers(0, 101, size=96))]
    vals = [nr.realised_recall(apps, nr.fit_rule(null, b)) for b in nr.BUDGETS]
    assert vals == sorted(vals)


def test_unscored_application_counts_as_not_flagged():
    rule = nr.fit_rule([10] * 90 + [50] * 10, 0.05)
    apps = [A("a", 99), A("b", None)]
    assert nr.realised_recall(apps, rule) == 0.5


def test_recall_of_an_empty_population_is_none():
    rule = nr.fit_rule([1, 2, 3], 0.1)
    assert nr.realised_recall([], rule) is None


# ── the tail of the honest null: units, chains, distinct writes ──────────────────────────────

def _nested_null():
    """Two chains. Chain a: units for writes 1..4, nested (unit k contains writes 1..k); the third write is
    the culprit, so units 3 and 4 score high. Chain b: one unit, write 9, scoring high on its own."""
    units = [U("a1", 10, ("a", 0), 1), U("a2", 10, ("a", 0), 2), U("a3", 90, ("a", 0), 3), U("a4", 90, ("a", 0), 4),
             U("b1", 80, ("b", 0), 9)] + [U(f"q{i}", 5, ("b", 0), 20 + i) for i in range(5)]
    contained = {("a", 0, 1): {1}, ("a", 0, 2): {1, 2}, ("a", 0, 3): {1, 2, 3}, ("a", 0, 4): {1, 2, 3, 4}, ("b", 0, 9): {9}}
    for i in range(5):
        contained[("b", 0, 20 + i)] = {20 + i}
    return units, contained


def test_tail_counts_units_chains_unit_writes_and_contained_writes():
    units, contained = _nested_null()
    tc = nr.tail_counts(units, lambda s: s >= 80, contained)
    assert tc == {"units": 3, "chains": 2, "unit_writes": 3, "contained_writes": 5}
    # the nested units hold writes 1, 2, 3, 4 (a) and 9 (b): five, not the three that end the units


def test_tail_counts_of_an_empty_tail():
    units, contained = _nested_null()
    assert nr.tail_counts(units, lambda s: s > 100, contained) == {"units": 0, "chains": 0, "unit_writes": 0, "contained_writes": 0}


def test_tail_counts_without_a_contained_map_leave_it_out():
    units, _ = _nested_null()
    tc = nr.tail_counts(units, lambda s: s >= 80, None)
    assert tc["units"] == 3 and tc["contained_writes"] is None


def test_tail_row_gives_strict_and_at_or_above_sets_and_the_realised_draw():
    units, contained = _nested_null()
    # ten units, scores 90 x2, 80 x1, 10 x2, 5 x5; budget 0.20 -> two units: both 90s strictly above, p_tie 0 at 80? share above 80 = 0.2 <= B
    row = nr.tail_row(units, 0.20, contained)
    assert row["threshold"] == 80
    assert row["units_above"] == 2 and row["units_at"] == 1 and row["units_at_or_above"] == 3
    assert row["strict"]["units"] == 2 and row["at_or_above"]["units"] == 3
    assert row["strict"]["contained_writes"] == 4         # writes 1..4 on chain a
    assert row["at_or_above"]["contained_writes"] == 5
    assert abs(row["expected_flagged_units"] - 2.0) < 1e-9  # exactly budget x n
    assert 2 <= row["realised_flagged_units"] <= 3


# ── the chain bootstrap ──────────────────────────────────────────────────────────────────────

def test_weights_are_reproducible_and_row_zero_is_the_point():
    W1 = nr.weights(18, 50, 20261113)
    W2 = nr.weights(18, 50, 20261113)
    assert W1.shape == (51, 18) and (W1 == W2).all()
    assert (W1[0] == 1).all()
    assert (W1[1:].sum(axis=1) == 18).all()                 # each replicate draws K chains with replacement
    assert not (nr.weights(18, 50, 1) == W1).all()


def _two_chain_world():
    # chain 0: null 10 x 8, 50 x 2; applications scoring 90 (all flagged at any budget >= 0.2 ...)
    # chain 1: null 10 x 10; applications scoring 10 (never flagged beyond ties)
    null = [U(f"n0_{i}", 10 if i < 8 else 50, ("c0", 0)) for i in range(10)] + [U(f"n1_{i}", 10, ("c1", 0)) for i in range(10)]
    apps = [A(f"a0_{i}", 90, ("c0", 0)) for i in range(4)] + [A(f"a1_{i}", 10, ("c1", 0)) for i in range(4)]
    return null, apps


def test_bootstrap_resamples_null_units_and_applications_of_a_chain_together():
    null, apps = _two_chain_world()
    clus = sorted({u["chain"] for u in null})
    cid = {c: i for i, c in enumerate(clus)}
    Hn = nr.chain_hist([cid[u["chain"]] for u in null], [u["score"] for u in null], len(clus))
    Ha = nr.chain_hist([cid[a["chain"]] for a in apps], [a["score"] for a in apps], len(clus))
    # replicate 0 = the point; replicate 1 takes chain 1 twice; replicate 2 takes chain 0 twice
    W = np.array([[1, 1], [0, 2], [2, 0]], dtype=float)
    out = nr.recall_by_replicate(Hn, Ha, 0.10, W)
    # point: null 20 units, 10 percent = 2 units above 10: threshold 10? above 10 = 2 units (the two 50s) <= 2 -> t = 10, p_tie 0
    assert abs(out[0] - 0.5) < 1e-12
    # chain 1 only: null is all 10s; t = 10, nothing above, p_tie = 0.1 on 20 of them -> apps (all 10s) flagged w.p. 0.1
    assert abs(out[1] - 0.1) < 1e-12
    # chain 0 only (doubled): null 16 tens, 4 fifties of 20; 10 percent = 2 units; t = 50, above 0, p_tie = 0.5; apps 90 -> flagged
    assert abs(out[2] - 1.0) < 1e-12


def test_bootstrap_intervals_are_replicate_percentiles_and_carry_valid_counts():
    null, apps = _two_chain_world()
    res = nr.bootstrap_recall(null, {"middle": apps}, (0.10, 0.20), n_boot=300, seed=7)
    cell = res["middle"][0.10]
    assert cell["n_valid"] == 300
    lo, hi = cell["ci95"]
    assert 0.0 <= lo <= cell["point"] <= hi <= 1.0
    assert abs(cell["point"] - 0.5) < 1e-12


def test_bootstrap_is_reproducible_under_the_seed():
    null, apps = _two_chain_world()
    a = nr.bootstrap_recall(null, {"m": apps}, (0.05, 0.10), n_boot=200, seed=20261113)
    b = nr.bootstrap_recall(null, {"m": apps}, (0.05, 0.10), n_boot=200, seed=20261113)
    assert a == b


def test_population_empty_in_some_replicates_is_conditional():
    null = [U(f"n0_{i}", 10, ("c0", 0)) for i in range(10)] + [U(f"n1_{i}", 10 + i, ("c1", 0)) for i in range(10)]
    apps = [A("only", 99, ("c1", 0))]                       # chain 0 holds no application
    res = nr.bootstrap_recall(null, {"p": apps}, (0.10,), n_boot=400, seed=1)
    cell = res["p"][0.10]
    assert 0 < cell["n_valid"] < 400                       # replicates that drop chain 1 have no application
    assert cell["ci95"][0] <= cell["ci95"][1]


def test_an_application_on_a_chain_the_null_lacks_is_refused():
    null = [U("n", 10, ("c0", 0))]
    with pytest.raises(ValueError):
        nr.bootstrap_recall(null, {"p": [A("x", 50, ("zzz", 3))]}, (0.1,), n_boot=10, seed=1)


# ── reproducing the record ───────────────────────────────────────────────────────────────────

def test_record_check_passes_on_a_two_place_match_and_fails_otherwise():
    assert nr.record_matches(0.552, 0.55) is True
    assert nr.record_matches(0.344, 0.34) is True
    assert nr.record_matches(0.331, 0.34) is False
    assert nr.record_matches(0.60, 0.55) is False


# ── widths and the sentence helper ───────────────────────────────────────────────────────────

def test_first_budget_where_the_interval_is_wider_than_a_limit():
    rows = [{"budget": 0.02, "ci95": [0.4, 0.6]}, {"budget": 0.05, "ci95": [0.3, 0.8]}, {"budget": 0.10, "ci95": [0.1, 0.9]}]
    assert nr.first_wide(rows, 0.40) == 0.05
    assert nr.first_wide(rows, 0.95) is None


# ── the assembler for loaded rows ────────────────────────────────────────────────────────────

def test_assemble_maps_recorded_rows_to_units_and_drops_unscored():
    null_rows = [{"label": "n1", "score": 12, "chain": ("d", 0), "write_index": 3}]
    app_rows = {"middle": [{"key": "k1", "label": "l1", "score": 70, "chain": ("d", 0)}]}
    units, apps = nr.assemble(null_rows, app_rows)
    assert units == [U("n1", 12, ("d", 0), 3)]
    assert apps["middle"] == [{"key": "k1", "label": "l1", "score": 70, "chain": ("d", 0), "regime": "middle"}]


def test_default_seed_is_the_briefs():
    null, apps = _two_chain_world()
    a = nr.bootstrap_recall(null, {"m": apps}, (0.10,), n_boot=60)
    b = nr.bootstrap_recall(null, {"m": apps}, (0.10,), n_boot=60, seed=20261113)
    assert a == b


def test_wide_budgets_lists_every_budget_over_the_limit():
    rows = [{"budget": 0.02, "ci95": [0.0, 0.5]}, {"budget": 0.05, "ci95": [0.3, 0.6]}, {"budget": 0.10, "ci95": [0.1, 0.9]}]
    assert nr.wide_budgets(rows, 0.40) == [0.02, 0.10]
    assert nr.wide_budgets(rows, 0.95) == []


def test_tail_matches_a2_compares_the_at_or_above_counts_to_the_audits_record():
    row = {"threshold": 78.0, "at_or_above": {"units": 30, "chains": 9, "unit_writes": 21, "contained_writes": 80}}
    rec = {"threshold": 78.0, "tail": {"units": 30, "chains": 9, "distinct_unit_writes": 21, "distinct_contained_writes": 80}}
    assert nr.tail_matches_a2(row, rec) is True
    rec["tail"]["distinct_contained_writes"] = 79
    assert nr.tail_matches_a2(row, rec) is False
    rec["tail"]["distinct_contained_writes"] = 80
    rec["threshold"] = 77.0
    assert nr.tail_matches_a2(row, rec) is False
