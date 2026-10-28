"""Tests for stage3_rater_join_07s.py (brief 07s part J): the statistics and the labels the join relies on."""
from __future__ import annotations

import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_rater_join_07s as rj  # noqa: E402


def test_bands_ranks_spearman_auroc():
    assert [rj.band(x) for x in (0, 20, 21, 40, 41, 60, 61, 80, 81, 100)] == [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
    assert rj.ranks([3, 1, 3, 2]) == [3.5, 1.0, 3.5, 2.0]
    assert abs(rj.spearman([1, 2, 3, 4], [10, 20, 30, 40]) - 1) < 1e-12
    assert abs(rj.spearman([1, 2, 3, 4], [4, 3, 2, 1]) + 1) < 1e-12
    assert rj.spearman([1, 1, 1], [1, 2, 3]) is None
    assert rj.auroc([2, 3], [1]) == 1.0 and rj.auroc([1], [2, 3]) == 0.0 and rj.auroc([2], [2]) == 0.5
    assert rj.auroc([], [1]) is None


def test_describe_and_bootstrap():
    d = rj.describe([0, 20, 40, 60, 80, 100])
    assert d["n"] == 6 and d["median"] == 50 and d["bands"]["0-20"] == round(2 / 6, 3) and d["share_ge_80"] == round(2 / 6, 3)
    rng = random.Random(1)
    ci = rj.boot_two(rj.auroc, [[90], [80], [70]], [[10], [20], [30]], rng, n=200)
    assert ci == [1.0, 1.0]
    ci = rj.boot_one(lambda v: sum(v) / len(v), [5, 5, 5], rng, n=50)
    assert ci == [5.0, 5.0]


def test_handle_and_format_match():
    h = rj.handle_regex(["kofi.o52", "frank.s"])
    assert h.search("verified (kofi.o52)") and h.search("by kofi-o52 today") and h.search("escalate to frank.s, post")
    assert not h.search("frank.sh script") and not h.search("checklist.md")
    assert rj.format_matched("- Port: 9080", h) and not rj.format_matched("a\nb", h) and not rj.format_matched("x frank.s", h)


def test_labels():
    assert rj.arm_label("payloads-v1.json", None) == "v1"
    assert rj.arm_label("payloads-v2.json", "sham") == "v2 sham"
    assert rj.arm_label("payloads-v3.json", "routine_redraw") == "v2 conforming"
    assert rj.arm_label("payloads-v3.json", "middle") == "v3 middle"
    assert rj.regime_label("v1", None) == "v1" and rj.regime_label("replant", "sham") == "replant sham"
    assert rj.text_group([{"file": "replant", "arm": "v1"}, {"file": "v1", "arm": None}]) == "v1"
    assert rj.text_group([{"file": "v3", "arm": "sham_redraw"}, {"file": "replant", "arm": "sham"}, {"file": "v2", "arm": "sham"}]) == "v2 sham"
    assert rj.text_group([{"file": "v3", "arm": "routine_redraw"}, {"file": "v2", "arm": "conforming"}]) == "v2 conforming"
    assert rj.text_group([{"file": "v3", "arm": "middle"}]) == "v3 middle"
