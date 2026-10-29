"""Offline tests for stage3_sol_provider_check.py: the seeded draw, the three statistics and the pass rule."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_sol_provider_check as sc  # noqa: E402

RULE = {"threshold": 86.0, "p_tie": 0.9, "seed": 20261112}


def test_draw_is_seeded_and_order_independent():
    labs = [f"prefix_rw_v2c:O_diff:owncloud:/d/b0..@{i}" for i in range(254)]
    d1 = sc.draw_labels(labs)
    d2 = sc.draw_labels(list(reversed(labs)))
    assert d1 == d2 and len(d1) == 40 and len(set(d1)) == 40


def test_compare_pass_and_fail():
    pairs = [(f"l{i}", float(s), float(s)) for i, s in enumerate([5, 10, 20, 30, 40, 50, 60, 70, 80, 90] * 4)]
    c = sc.compare(pairs, RULE)
    assert c["pass"] and c["spearman"] == 1.0 and c["median_abs_diff"] == 0 and c["verdict_unchanged"] == 40
    # a scale shift of 6 fails the median bar even with the order kept
    shifted = [(l, a, a + 6) for l, a, _b in pairs]
    c2 = sc.compare(shifted, RULE)
    assert not c2["pass"] and c2["spearman"] == 1.0 and c2["median_abs_diff"] == 6 and not c2["conditions"]["median_abs_diff_le_5"]
    # verdict flips above the rule's threshold are counted
    flipped = [(l, a, (95.0 if a == 80 else a)) for l, a, _b in pairs]
    c3 = sc.compare(flipped, RULE)
    assert c3["verdict_unchanged"] == 36 and c3["conditions"]["verdict_unchanged_ge_36_of_40"]
    # fewer than 40 pairs cannot pass
    assert not sc.compare(pairs[:39], RULE)["pass"]
