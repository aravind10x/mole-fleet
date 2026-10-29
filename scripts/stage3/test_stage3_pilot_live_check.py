"""Offline tests for the pure parts of stage3_pilot_live_check.py (brief 09 M1)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_pilot_live_check as lc  # noqa: E402


def test_role_day_bar():
    assert abs(lc.role_day_bar(1, 0.4) - 0.4) < 1e-12
    assert abs(lc.role_day_bar(2, 0.4) - 0.64) < 1e-12
    assert abs(lc.role_day_bar(2, 0.2) - 0.36) < 1e-12


def test_role_day_yield_groups_sessions_by_account_and_day():
    sess = [{"account": "a", "day": "d1", "advanced": True}, {"account": "a", "day": "d1", "advanced": False},
            {"account": "b", "day": "d2", "advanced": False}, {"account": "b", "day": "d2", "advanced": False},
            {"account": "c", "day": "d3", "advanced": True}]
    r = lc.role_day_yield(sess)
    assert r["n_role_days"] == 3 and r["n_yielded"] == 2 and abs(r["share"] - 2 / 3) < 1e-12
    by = {(x["account"], x["day"]): x for x in r["role_days"]}
    assert by[("a", "d1")]["sessions"] == 2 and by[("a", "d1")]["yielded"] is True and by[("a", "d1")]["bar_0.4"] == 0.64
    assert by[("c", "d3")]["sessions"] == 1 and by[("c", "d3")]["bar_0.4"] == 0.4
    assert lc.role_day_yield([])["share"] is None


def test_overwrite_counts_before_composition_only():
    seq = [("coalition", "replace_in_file", "d1", 1), ("other", "write_file", "d1", 0),
           ("coalition", "append_to_file", "d2", 2), ("coalition", "replace_in_file", "d2", 3),
           ("other", "replace_in_file", "d3", 2)]
    # composition at index 3 (n = 3 facts): the loss on d3 is after composition and not counted
    c = lc.overwrite_counts(seq, first_composed_index=4)
    assert c == {"other:write_file": 1, "total": 1}
    # never composed: every loss counts
    c2 = lc.overwrite_counts(seq, first_composed_index=None)
    assert c2["total"] == 2 and c2["other:replace_in_file"] == 1
    assert lc.overwrite_counts([], None) == {}


def test_window_bounds_use_the_oracle_rule_for_day_form_bounds():
    """A 10-character window bound is a whole day (oracle._le / _before_start); the first version
    compared full timestamps with a date string and dropped every write on the window's last day."""
    import importlib.util
    fork = Path(__file__).resolve().parent.parent / "mole-fork"
    oracle = lc.po.load_oracle(fork)
    assert not oracle._gt("2026-04-10T23:59:00Z", "2026-04-10")
    assert oracle._gt("2026-04-11T00:00:01Z", "2026-04-10")
    assert not oracle._before_start("2026-04-09T00:00:01Z", "2026-04-09")
    assert oracle._before_start("2026-04-08T23:59:59Z", "2026-04-09")
