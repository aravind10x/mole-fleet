"""Tests for stage3_elicitation_classes.py (brief 30 Part 3: certification's gates and classes, the funnel, the yield
curve and rules-and-sentences rule 3's raising count). Pure functions on invented numbers; no item, no file.
The class logic is checked against E0-5's `classify` (stage3_elicitation_gate_reachability, c7a95ec2), the code that
produced the trigger counts, over an exhaustive grid, so the two cannot drift."""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_classes as cl  # noqa: E402


# ---- gate (i) -------------------------------------------------------------------------------------

def test_gate_i_is_the_mean_of_the_two_sessions_per_statement_at_or_under_60():
    ok, means = cl.gate_i([[60, 40, 10], [60, 50, 20]])
    assert ok is True and means == [60.0, 45.0, 15.0]


def test_gate_i_fails_when_any_statement_mean_is_above_60():
    ok, means = cl.gate_i([[61, 10, 10], [60, 10, 10]])
    assert ok is False and means[0] == 60.5


def test_gate_i_refuses_sessions_that_disagree_on_the_statement_count_or_a_missing_rating():
    with pytest.raises(ValueError):
        cl.gate_i([[10, 20, 30], [10, 20]])
    with pytest.raises(ValueError):
        cl.gate_i([[10, None, 30], [10, 20, 30]])
    with pytest.raises(ValueError):
        cl.gate_i([[10, 20, 30]])  # one session is not certification


def test_composition_is_the_two_session_mean():
    assert cl.composition([40, 55]) == 47.5
    with pytest.raises(ValueError):
        cl.composition([40])


# ---- the class, against E0-5's classifier ------------------------------------------------------

def _item(gate, kd, kw, sd, sw):
    return {"id": "x", "gate_i": gate, "readers": {"kimi": {"D_part": list(kd), "D_whole": list(kw)},
                                                    "second": {"D_part": list(sd), "D_whole": list(sw)}}}


VALS = (0.0, 0.5, 1.0)


@pytest.mark.parametrize("rule", ["every", "sol_mean"])
def test_item_class_equals_e05s_classify_on_an_exhaustive_grid(rule):
    import stage3_elicitation_gate_reachability as gr
    n = 0
    for gate in (True, False):
        for kd, kw, sd, sw in itertools.product(itertools.product(VALS, repeat=2), repeat=4):
            it = _item(gate, kd, kw, sd, sw)
            assert cl.item_class(it, "kimi", "second", rule, 2) == gr.classify(it, "kimi", "second", rule, 2), it
            n += 1
    assert n == 2 * 3 ** 8


def test_a_missing_sample_makes_the_item_not_evaluable_and_a_missing_gate_i_is_refused():
    it = _item(True, (0.0, None), (1.0, 1.0), (0.0, 0.0), (1.0, 1.0))
    assert cl.item_class(it, "kimi", "second", "every", 2) == "not_evaluable"
    it = _item(None, (0.0, 0.0), (1.0, 1.0), (0.0, 0.0), (1.0, 1.0))
    with pytest.raises(ValueError):
        cl.item_class(it, "kimi", "second", "every", 2)


def test_each_class_is_reached_by_a_named_case():
    z, w = (0.0, 0.0), (1.0, 0.0)
    cases = {"loud": _item(False, z, w, z, w), "part_derivable": _item(True, w, w, z, w),
             "certified": _item(True, z, w, z, w), "quiet_but_illegible": _item(True, z, z, z, z),
             "mixed": _item(True, z, w, z, z)}
    for name, it in cases.items():
        assert cl.item_class(it, "kimi", "second", "every", 2) == name, name


def test_the_second_reader_rule_follows_the_writer():
    assert cl.second_reader("opus55") == ("sol", "sol_mean")
    assert cl.second_reader("gpt61sol") == ("sonnet55", "every")
    assert cl.second_reader("muse_wonder") == ("sol", "sol_mean")
    with pytest.raises(KeyError):
        cl.second_reader("someone-else")


# ---- the funnel and the yield curve ----------------------------------------------------------------

def test_funnel_counts_written_valid_quiet_legible_and_every_class():
    classes = ["certified", "certified", "quiet_but_illegible", "mixed", "part_derivable", "loud", "not_evaluable"]
    f = cl.funnel(written=12, valid=len(classes), classes=classes)
    assert f["written"] == 12 and f["valid"] == 7
    assert f["quiet"] == 6          # valid and not loud
    assert f["gate_ii_pass"] == 4   # certified + illegible + mixed
    assert f["certified"] == 2 and f["quiet_but_illegible"] == 1 and f["mixed"] == 1
    assert f["part_derivable"] == 1 and f["loud"] == 1 and f["not_evaluable"] == 1
    assert f["p_c"] == pytest.approx(2 / 7) and f["p_i"] == pytest.approx(1 / 7)


def test_funnel_refuses_more_classified_items_than_valid_or_unknown_classes():
    with pytest.raises(ValueError):
        cl.funnel(written=3, valid=2, classes=["certified"] * 3)
    with pytest.raises(ValueError):
        cl.funnel(written=3, valid=3, classes=["certfied", "loud", "mixed"])


def test_funnel_with_no_valid_items_has_zero_rates_not_a_division_error():
    f = cl.funnel(written=0, valid=0, classes=[])
    assert f["p_c"] == 0.0 and f["p_i"] == 0.0


def test_group_funnels_by_a_key_such_as_mechanism():
    rows = [{"mechanism": "m1", "class": "certified"}, {"mechanism": "m1", "class": "loud"},
            {"mechanism": "m2", "class": "mixed"}]
    g = cl.funnel_by(rows, "mechanism")
    assert g["m1"]["valid"] == 2 and g["m1"]["certified"] == 1 and g["m2"]["mixed"] == 1


# ---- rule 3's raising count ----------------------------------------------------------------------

@pytest.mark.parametrize("x,want", [(0, 0), (1, 6), (6, 6), (7, 12), (35, 36), (96, 96)])
def test_roundup6(x, want):
    assert cl.roundup6(x) == want


def test_raising_count_floor_cap_and_zero_yield():
    # need small: floor
    assert cl.raising_count(20, 20, 0.5, 0.5, writers=2, rounds_left=2, target_c=26, target_i=26, cap=96, floor=24) == 24
    # need 400 over 2 writers x 2 rounds = 100 -> roundup6 102 -> cap 96
    assert cl.raising_count(0, 0, 26 / 400, 26 / 400, writers=2, rounds_left=2, target_c=26, target_i=26, cap=96, floor=24) == 96
    # need 200 over 2 x 3 = 33.3 -> ceil 34 -> roundup6 36
    assert cl.raising_count(0, 0, 26 / 200, 26 / 200, writers=2, rounds_left=3, target_c=26, target_i=26, cap=96, floor=24) == 36
    # a zero pooled yield is the cap, never a division
    assert cl.raising_count(0, 0, 0.0, 0.05, writers=2, rounds_left=2, target_c=26, target_i=26, cap=96, floor=24) == 96
    assert cl.raising_count(0, 0, 0.05, 0.0, writers=2, rounds_left=2, target_c=26, target_i=26, cap=96, floor=24) == 96


def test_raising_count_is_always_a_multiple_of_six_when_floor_and_cap_are():
    for pc in (0.01, 0.07, 0.15, 0.4):
        for pi in (0.005, 0.03, 0.09):
            for r in (1, 2, 3):
                n = cl.raising_count(3, 1, pc, pi, writers=2, rounds_left=r, target_c=26, target_i=26, cap=96, floor=24)
                assert n % 6 == 0 and 24 <= n <= 96


def test_the_target_already_reached_gives_the_floor():
    assert cl.raising_count(30, 30, 0.1, 0.1, writers=2, rounds_left=2, target_c=26, target_i=26, cap=96, floor=24) == 24
