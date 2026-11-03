"""Tests for stage3_elicitation_gate_reachability_v1.py (brief 30 Part 2): decision 8's trigger (reconcile-e2-rule
cb9f626e: the boundary counts at cap 96 and at cap 48), the Wilson intervals, the E1 and E2 merges into E0-5's item
form, the nulls' whole and part credit under the pinned reader, the cell rates, and, on the real files (skipped when
absent), the orientation beside (E0-5's 11 / 10 / 5) and the run files' completeness. Ids and aggregates only."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_gate_reachability_v1 as g1  # noqa: E402

ROOT = HERE.parent.parent


# ── decision 8's lines and trigger ───────────────────────────────────────────────────────────────

def test_items_over_three_writer_rounds():
    assert g1.round_items(96) == 432 and g1.round_items(48) == 240


@pytest.mark.parametrize("cap,cert,ill,fires_c,fires_i", [
    (96, 4, 9, True, False), (96, 5, 9, False, False),       # certified: fewer than 5 of 78 fires
    (96, 9, 2, False, True), (96, 9, 3, False, False),       # illegible: fewer than 3 of 78 fires
    (48, 8, 9, True, False), (48, 9, 9, False, False),       # beside at cap 48: fewer than 9
    (48, 9, 3, False, True), (48, 9, 4, False, False),       # and fewer than 4
])
def test_trigger_boundaries(cap, cert, ill, fires_c, fires_i):
    t = g1.trigger(cert, ill, n=78, cap=cap)
    assert t["fires_certified"] is fires_c and t["fires_illegible"] is fires_i and t["fires"] is (fires_c or fires_i)


def test_trigger_lines_as_the_rule_states_them():
    t96, t48 = g1.trigger(0, 0, cap=96), g1.trigger(0, 0, cap=48)
    assert (t96["fire_if_certified_fewer_than"], t96["fire_if_illegible_fewer_than"]) == (5, 3)
    assert (t48["fire_if_certified_fewer_than"], t48["fire_if_illegible_fewer_than"]) == (9, 4)
    assert t96["certified_rate_line"] == pytest.approx(26 / 432) and t96["illegible_rate_line"] == pytest.approx(12 / 432)


def test_wilson():
    lo, hi = g1.wilson(5, 78)
    assert (round(lo, 3), round(hi, 3)) == (0.028, 0.141)      # the rule file's example
    assert g1.wilson(0, 46)[0] == 0.0 and g1.wilson(0, 0) is None


# ── merges into E0-5's item form ─────────────────────────────────────────────────────────────────

def _t1(i, r1=None):
    return {"id": i, "set": "t1_v2_conforming", "writer": None, "gate_i": True, "n_lines": 3,
            "readers": {f: {"D_whole": [1.0, r1], "D_part": [0.0, r1]} for f in ("kimi", "sol", "sonnet55")}}


def test_merge_e1_fills_the_second_sample_of_the_items_read_once():
    items = [_t1("a"), _t1("b", r1=0.5)]
    out = g1.merge_e1(items, {"kimi": {"a": (1.0, 0.0)}, "sol": {"a": (0.5, 0.5)}, "sonnet55": {"a": (None, None)}})
    a, b = out
    assert a["readers"]["kimi"] == {"D_whole": [1.0, 1.0], "D_part": [0.0, 0.0]}
    assert a["readers"]["sol"] == {"D_whole": [1.0, 0.5], "D_part": [0.0, 0.5]}
    assert a["readers"]["sonnet55"]["D_whole"] == [1.0, None]          # a refusal stays None (not evaluable)
    assert b["readers"]["kimi"] == {"D_whole": [1.0, 0.5], "D_part": [0.0, 0.5]}   # a retest item keeps brief 23's r1
    assert items[0]["readers"]["kimi"]["D_whole"] == [1.0, None]       # the input is not changed


def test_merge_e1_refuses_overwriting_a_second_sample():
    with pytest.raises(ValueError):
        g1.merge_e1([_t1("b", r1=0.5)], {"kimi": {"b": (1.0, 0.0)}, "sol": {}, "sonnet55": {}})


def test_add_pinned_reader():
    out = g1.add_pinned([_t1("a"), _t1("b")], {"a": {"D_whole": [0.0, 1.0], "D_part": [0.0, 0.0]}})
    assert out[0]["readers"]["kimi_pin"] == {"D_whole": [0.0, 1.0], "D_part": [0.0, 0.0]}
    assert out[1]["readers"]["kimi_pin"] == {"D_whole": [None, None], "D_part": [None, None]}
    assert "kimi_pin" not in _t1("a")["readers"]


# ── the nulls under the pinned reader, the cell rates ────────────────────────────────────────────

def _null(i, dw, dp):
    return {"id": i, "set": "sham", "readers": {"kimi_pin": {"D_whole": list(dw), "D_part": list(dp)}}}


def test_null_credit_counts_items_and_cells():
    nulls = [_null("a", (0.0, 0.0), (0.0, 0.0)), _null("b", (0.5, 0.0), (0.0, 0.0)), _null("c", (0.0, 0.0), (0.0, 1.0)),
             _null("d", (None, None), (None, None))]
    c = g1.null_credit(nulls, "kimi_pin")
    assert c["items"] == 4 and c["evaluable_items"] == 3
    assert c["whole_credit_items"] == 1 and c["part_credit_items"] == 1 and c["whole_credit_ids"] == ["b"]
    assert c["cells"] == 6 and c["whole_credit_cells"] == 1 and c["part_credit_cells"] == 1


def test_cell_rates():
    items = [_null("a", (1.0, 0.0), (0.5, 0.0)), _null("b", (None, 1.0), (None, 0.0))]
    r = g1.cell_rates(items, "kimi_pin")
    assert r == {"cells": 3, "D_part_pos": 1, "D_whole_pos": 2, "share_D_part_pos": 1 / 3, "share_D_whole_pos": 2 / 3}


def test_usage_windows_compare_key_usage_with_the_runs_openrouter_records():
    checks = [("e1", {"checked_at": "t0", "key": {"usage": 100.0}}), ("e2", {"checked_at": "t1", "key": {"usage": 102.5}}),
              ("e2", {"checked_at": "t2", "key": {"usage": 120.0}})]
    w = g1.usage_windows(checks, {"e1": 2.0, "e2": 16.0})
    assert [(x["from"], x["to"], x["run"]) for x in w] == [("t0", "t1", "e1"), ("t1", "t2", "e2")]
    assert w[0]["key_usage_delta_usd"] == pytest.approx(2.5) and w[0]["not_in_run_records_usd"] == pytest.approx(0.5)
    assert w[1]["not_in_run_records_usd"] == pytest.approx(1.5)


# ── the real files (skipped when absent) ─────────────────────────────────────────────────────────

REAL = (ROOT / "work/stage3/b3/comprehension/stratum-v0.json").exists()
RUNS = all((ROOT / f"work/stage3/elicitation/e1e2/{e}/run-summary.json").exists() for e in ("e1", "e2"))


@pytest.mark.skipif(not REAL, reason="brief 25's stratum file is not present")
def test_real_orientation_beside_is_e0_5s():
    o = g1.orientation(ROOT)
    assert o["classes"]["certified"] == 11 and o["certified_by_reading"]["same_sample"] == 10
    assert o["certified_by_reading"]["both_both"] == 5 and o["classes"]["quiet_but_illegible"] == 7


@pytest.mark.skipif(not (REAL and RUNS), reason="E1 and E2's run files are not present")
def test_real_report_covers_every_item():
    R = g1.build(ROOT)
    assert R["e2"]["sets"]["b3_candidates"]["kimi_pin+sol (sol_mean)"]["n"] == 78
    assert R["e2"]["sets"]["nulls_46"]["kimi_pin+sol (sol_mean)"]["n"] == 46
    assert R["e2"]["sets"]["t1_items"]["kimi_pin+sol (sol_mean)"]["n"] == 48
    assert R["e1"]["t1_items_brief23_readers"]["kimi+sol (sol_mean)"]["n"] == 48
    assert R["trigger"]["cap_96"]["n"] == 78 and isinstance(R["trigger"]["cap_96"]["fires"], bool)
