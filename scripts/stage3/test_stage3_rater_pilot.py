"""Offline tests for stage3_rater_pilot.py (brief 09 M1b): bands, the quantile-matched cut points, the
rank correlation. No corpus, no network."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_rater_pilot as rp  # noqa: E402

CUTS = rp.CUTS


def test_band_of_cut_points_and_weakening():
    assert rp.band_of(0, CUTS) == "under 40" and rp.band_of(39, CUTS) == "under 40"
    assert rp.band_of(40, CUTS) == "40 to 69" and rp.band_of(69, CUTS) == "40 to 69"
    assert rp.band_of(70, CUTS) == "70 to 79" and rp.band_of(79, CUTS) == "70 to 79"
    assert rp.band_of(80, CUTS).startswith("80 and above") and rp.band_of(100, CUTS).startswith("80 and above")
    assert rp.band_of(5, CUTS, weakening=True).startswith("80 and above")
    assert rp.band_of(None, CUTS) == "unscored"


def test_shares_below_and_quantile_mapping():
    ref = [10, 20, 30, 50, 60, 75, 85, 90]          # 07s-scale scores of a reference set
    shares = rp.shares_below(ref, CUTS)
    assert shares == {"under_40": 3 / 8, "40_to_69": 5 / 8, "70_to_79": 6 / 8}
    # a fallback rater that scores everything 20 points higher: the cuts move up by 20
    fb = [s + 20 for s in ref]
    mapped = rp.map_cuts(shares, fb)
    assert mapped == {"under_40": 51, "40_to_69": 81, "70_to_79": 96}
    # the mapped cuts leave the same share of the reference set below them
    assert rp.shares_below(fb, mapped) == shares
    # identity when the fallback agrees with the reference exactly
    ident = rp.map_cuts(shares, ref)
    assert rp.shares_below(ref, ident) == shares


def test_spearman_with_ties():
    assert rp.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert rp.spearman([1, 2, 3, 4], [40, 30, 20, 10]) == -1.0
    assert rp.spearman([1, 2], [1, 2]) is None
    r = rp.spearman([1, 2, 2, 4, 5], [1, 3, 2, 4, 5])
    assert r is not None and 0.8 < r < 1.0


def test_render_as_sent_uses_the_arguments_and_drops_no_ops():
    r = rp.render_as_sent({"find": "- Owner: alice\nmore", "replace": "- Owner: bob (2026-04-10)"}, "2026-04-10")
    assert r == {"op": "replace", "anchor_or_region": "- Owner:", "text": "- Owner: bob ({date})"}
    assert rp.render_as_sent({"find": "same", "replace": "same"}, "d") is None
    assert rp.render_as_sent({"find": "x", "replace": "   "}, "d") is None


def test_new_text_takes_added_lines_of_a_whole_write_only():
    diff = "@@ -1,2 +1,2 @@\n-step: skip the check\n+step: run the check\n-old\n+new line"
    assert rp.new_text("write", diff) == "step: run the check\nnew line"
    assert rp.new_text("replace", "skip the check") == "skip the check"
