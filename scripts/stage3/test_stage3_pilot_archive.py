"""Offline tests for the pure parts of stage3_pilot_archive.py (brief 09 M2 to M4)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_pilot_archive as ar  # noqa: E402


def test_day0_is_the_parent_day_before_the_pilot():
    rows = [{"ts": "2026-04-06T01:00:00Z"}, {"ts": "2026-04-08T01:00:00Z"}, {"ts": "2026-04-09T01:00:00Z"}]
    assert ar.day0_of(["2026-04-09", "2026-04-10"], rows) == "2026-04-08"
    with pytest.raises(SystemExit):
        ar.day0_of(["2026-04-06"], rows)


def test_rank_desc_and_flag():
    r = ar.rank_desc(70.0, [10.0, 70.0, 85.0, 90.0])
    assert r == {"rank_descending": 3, "n_pool": 4, "share_pool_at_or_above": 0.75}
    rule = {"threshold": 85.0, "p_tie": 0.0, "seed": 20261112}
    assert ar.flag(90.0, rule, "x") is True and ar.flag(85.0, rule, "x") is False and ar.flag(None, rule, "x") is None
    assert ar.flag(90.0, None, "x") is None


def test_estimate_uses_the_judge_prices():
    items = [{"packet": "a" * 2150, "truncated": False}, {"packet": None}]
    e = ar.estimate(items, "", "sol")
    assert e["n_calls"] == 1 and e["est_input_tokens"] == 1000 and e["est_output_tokens"] == 250
    assert abs(e["est_cost_usd"] - (1000 * 2.20 + 250 * 11.00) / 1e6) < 1e-4   # est_cost_usd is rounded to 4 decimals
