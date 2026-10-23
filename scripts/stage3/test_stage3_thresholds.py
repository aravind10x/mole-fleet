import json
import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage3_thresholds as th  # noqa: E402

TIED = [5] * 40 + [10] * 30 + [20] * 20 + [60] * 6 + [72] * 4      # n = 100


def test_tied_rule_hits_rate_exactly():
    r = th.randomised_threshold(TIED, 0.05, seed=7)
    assert r["kind"] == "unit" and r["threshold"] == 60 and r["n"] == 100 and r["distinct_scores"] == 5
    assert r["share_above"] == pytest.approx(0.04) and r["share_at"] == pytest.approx(0.06)
    assert r["p_tie"] == pytest.approx((0.05 - 0.04) / 0.06, abs=1e-12)
    assert abs(th.expected_flag_rate(TIED, r) - 0.05) < 1e-12
    assert abs(r["expected_rate"] - 0.05) < 1e-12
    json.dumps(r)                                     # plain JSON


def test_tied_rule_at_ten_percent():
    r = th.randomised_threshold(TIED, 0.10, seed=7)
    # share above 20 is exactly 0.10, so t = 20 with no tie flags (p_tie 0)
    assert r["threshold"] == 20 and abs(th.expected_flag_rate(TIED, r) - 0.10) < 1e-12 and r["p_tie"] == 0.0
    r = th.randomised_threshold(TIED, 0.20, seed=7)    # above 10 is 0.30 > B, above 20 is 0.10, at 20 is 0.20 -> p 0.5
    assert r["threshold"] == 20 and r["p_tie"] == pytest.approx(0.5)


def test_is_flagged_deterministic_and_monte_carlo():
    r = th.randomised_threshold(TIED, 0.05, seed=7)
    assert th.is_flagged(72, r, "a") and not th.is_flagged(20, r, "a")
    labels = [f"acct-{i}|day-{i % 30}" for i in range(20000)]
    first = [th.is_flagged(60, r, lab) for lab in labels]
    assert first == [th.is_flagged(60, r, lab) for lab in labels]
    assert abs(sum(first) / len(first) - r["p_tie"]) < 0.02
    r2 = dict(r, seed=8)                                 # a different seed gives a different draw set
    assert [th.is_flagged(60, r2, lab) for lab in labels] != first


def test_tie_uniform():
    u = th.tie_uniform(3, "x")
    assert u == th.tie_uniform(3, "x") and 0.0 <= u < 1.0 and u != th.tie_uniform(4, "x")
    us = [th.tie_uniform(0, str(i)) for i in range(5000)]
    assert abs(sum(us) / len(us) - 0.5) < 0.02


def test_exact_quantile_gives_rate():
    s = list(range(1, 101))                              # distinct: 5 above 95
    r = th.randomised_threshold(s, 0.05, seed=1)
    assert r["threshold"] == 95 and r["p_tie"] == 0.0 and abs(r["expected_rate"] - 0.05) < 1e-12
    r = th.randomised_threshold([1] * 90 + [2] * 10, 0.10, seed=1)
    assert abs(th.expected_flag_rate([1] * 90 + [2] * 10, r) - 0.10) < 1e-12


def test_sentinels_and_empty():
    hi = th.randomised_threshold(TIED, 1.0, seed=1)
    lo = th.randomised_threshold(TIED, 0.0, seed=1)
    assert hi["threshold"] is None and hi["p_tie"] == 1.0 and hi["expected_rate"] == 1.0
    assert lo["threshold"] is None and lo["p_tie"] == 0.0 and lo["expected_rate"] == 0.0
    for lab in ("a", "b", "c"):
        assert th.is_flagged(0, hi, lab) and th.is_flagged(-5, hi, lab) and not th.is_flagged(100, lo, lab)
    assert th.expected_flag_rate(TIED, hi) == 1.0 and th.expected_flag_rate(TIED, lo) == 0.0
    assert th.randomised_threshold(TIED, 1.5, seed=1)["threshold"] is None
    with pytest.raises(ValueError):
        th.randomised_threshold([], 0.05, seed=1)
    with pytest.raises(ValueError):
        th.expected_flag_rate([], hi)


def test_expected_flag_rate_on_other_sample():
    r = th.randomised_threshold(TIED, 0.05, seed=7)
    other = [60] * 50 + [80] * 50
    assert th.expected_flag_rate(other, r) == pytest.approx(0.5 + 0.5 * r["p_tie"])


AMAX = {"a": 90, "b": 80, "c": 80, "d": 50, "e": 10, "f": 10}
AW = {"a": 2, "b": 3, "c": 5, "d": 20, "e": 30, "f": 30, "quiet": 10}   # total 100; quiet has no units


def test_author_level_threshold():
    r = th.author_level_threshold(AMAX, AW, 0.05, seed=3)
    # cost(max > 80) = 0.02, cost(max == 80) = 0.08 -> t = 80, p = 0.375
    assert r["kind"] == "author" and r["threshold"] == 80 and r["total_weight"] == 100 and r["n_authors"] == 7
    assert r["cost_above"] == pytest.approx(0.02) and r["cost_at"] == pytest.approx(0.08)
    assert r["p_tie"] == pytest.approx(0.375) and r["expected_cost"] == pytest.approx(0.05, abs=1e-12)
    assert r["deterministic_threshold"] == 90 and r["deterministic_cost"] == pytest.approx(0.02)
    assert r["deterministic_cost"] <= 0.05
    assert not th.is_flagged(AMAX.get("quiet"), r, "quiet")
    assert th.is_flagged(AMAX["a"], r, "a") and not th.is_flagged(AMAX["d"], r, "d")
    hi = th.author_level_threshold(AMAX, AW, 1.0, seed=3)
    assert not th.is_flagged(None, hi, "quiet") and th.is_flagged(10, hi, "e")
    json.dumps(r)


def test_author_none_and_validation():
    r = th.author_level_threshold(dict(AMAX, quiet=None), AW, 0.05, seed=3)
    assert r["threshold"] == 80 and r["total_weight"] == 100
    with pytest.raises(ValueError):
        th.author_level_threshold({"zz": 5}, AW, 0.05, seed=3)       # max without a weight
    with pytest.raises(ValueError):
        th.author_level_threshold({}, {}, 0.05, seed=3)


def test_author_p_clamped_when_quiet_weight_dominates():
    r = th.author_level_threshold({"a": 5}, {"a": 1, "q": 99}, 0.5, seed=0)
    assert r["threshold"] == 5 and r["p_tie"] == 1.0 and r["expected_cost"] == pytest.approx(0.01)


def _wellbehaved():
    amax = {f"u{i}": (i * 37) % 101 for i in range(300)}
    aw = {a: 1 + (i % 4) for i, a in enumerate(amax)}
    return amax, aw


def test_bootstrap_contains_point_and_reproducible():
    amax, aw = _wellbehaved()
    point = th.author_level_threshold(amax, aw, 0.05, seed=1)["deterministic_threshold"]
    b1 = th.bootstrap_author_threshold(amax, aw, 0.05, seed=11, n_boot=500)
    b2 = th.bootstrap_author_threshold(amax, aw, 0.05, seed=11, n_boot=500)
    assert b1 == b2 and b1["n_boot"] == 500 and sum(b1["distribution"].values()) == 500
    lo, hi = b1["ci95"]
    assert lo <= point <= hi and lo <= b1["median"] <= hi
    json.dumps(b1)


def test_clopper_pearson():
    for k in (0, 12, 24):
        lo, hi = th.clopper_pearson(k, 24)
        assert lo <= k / 24 <= hi
    assert th.clopper_pearson(0, 24)[0] == 0.0 and th.clopper_pearson(24, 24)[1] == 1.0
    lo, hi = th.clopper_pearson(12, 24)
    assert abs(lo - 0.291) < 0.005 and abs(hi - 0.709) < 0.005
    assert abs(th.clopper_pearson(0, 24)[1] - 0.142) < 0.005


def test_clopper_pearson_fallback_agrees():
    for k, n in ((0, 24), (3, 24), (12, 24), (24, 24), (7, 150)):
        a, b = th.clopper_pearson(k, n), th._clopper_pearson_exact(k, n, 0.05)
        assert abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) < 1e-6


def test_degeneracy_helpers():
    assert th.distinct_above_median([1, 2, 3, 4, 5, 6, 7]) == 3             # median 4
    assert th.distinct_above_median([0] * 10 + [5, 5, 9]) == 2              # median 0
    assert th.distinct_above_median([3, 3, 3]) == 0
    assert th.distinct_above_median(TIED) == 3                              # median 10 -> 20, 60, 72
    assert th.top_share(TIED) == pytest.approx(0.40) and th.top_share([1]) == 1.0
    with pytest.raises(ValueError):
        th.top_share([])
