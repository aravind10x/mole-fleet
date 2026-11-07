"""Tests for stage3_elicitation_round.py (brief 30 Part 3: the round record's figures). Pure functions on invented numbers."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_round as rr  # noqa: E402


def test_rater_proxy_agreement_is_the_rank_correlation_of_the_two_sessions_means():
    dev = {"a": 10.0, "b": 20.0, "c": 30.0, "d": 40.0}
    assert rr.rater_proxy(dev, {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0})["spearman"] == pytest.approx(1.0)
    assert rr.rater_proxy(dev, {"a": 4.0, "b": 3.0, "c": 2.0, "d": 1.0})["spearman"] == pytest.approx(-1.0)
    r = rr.rater_proxy(dev, {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0})
    assert r["n"] == 4


def test_rater_proxy_also_reports_agreement_on_within_target():
    dev = {"a": 10.0, "b": 70.0, "c": 30.0, "d": 90.0}
    cert = {"a": 20.0, "b": 50.0, "c": 62.0, "d": 80.0}      # within target (<= 60): dev T,F,T,F ; cert T,T,F,F
    r = rr.rater_proxy(dev, cert)
    assert r["within_target_agreement"] == pytest.approx(2 / 4)


def test_rater_proxy_uses_only_statements_both_sessions_rated():
    r = rr.rater_proxy({"a": 1.0, "b": 2.0, "z": 3.0}, {"a": 1.0, "b": 2.0})
    assert r["n"] == 2


def test_reader_proxy_compares_dev_to_certification_on_whole_and_part_credit_among_read_items():
    dev = {"a1": {"kimi": {"D_whole": [1.0], "D_part": [0.0]}}, "a2": {"kimi": {"D_whole": [0.0], "D_part": [1.0]}},
           "a3": {"kimi": {"D_whole": [1.0], "D_part": [0.0]}}}
    cert = {"a1": {"kimi": {"D_whole": [0.0, 1.0], "D_part": [0.0, 0.0]}},       # agrees on both
            "a2": {"kimi": {"D_whole": [0.0, 0.0], "D_part": [0.0, 0.0]}}}        # dev part credited, cert not: disagrees on part
    r = rr.reader_proxy(dev, cert, ("kimi",))
    assert r["kimi"]["n"] == 2                      # a3 was not read in certification (it failed gate (i))
    assert r["kimi"]["whole_agreement"] == pytest.approx(1.0)
    assert r["kimi"]["part_agreement"] == pytest.approx(0.5)


def test_reader_proxy_skips_a_none_value_instead_of_counting_it_as_agreement():
    dev = {"a1": {"kimi": {"D_whole": [None], "D_part": [0.0]}}}
    cert = {"a1": {"kimi": {"D_whole": [1.0, 1.0], "D_part": [0.0, 0.0]}}}
    r = rr.reader_proxy(dev, cert, ("kimi",))["kimi"]
    assert r["whole_n"] == 0 and r["part_n"] == 1 and r["part_agreement"] == 1.0
