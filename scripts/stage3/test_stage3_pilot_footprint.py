"""Offline tests for stage3_pilot_footprint.py (brief 09 M1c and M6): features, rule fit and placement on a
tiny fixture. No corpus."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_pilot_footprint as fp  # noqa: E402


def _w(account, day, path, task, chars, index):
    return {"account": account, "day": day, "path": path, "task_id": task, "chars": chars, "index": index}


def test_features_counts_bursts_coedits_and_first_time_authors():
    writes = [_w("a", "d1", "/p", "t1", 10, 0), _w("a", "d1", "/p", "t1", 20, 1), _w("a", "d1", "/q", "t2", 5, 2),
              _w("b", "d1", "/p", "t3", 7, 3), _w("a", "d2", "/p", "t4", 1, 4)]
    active = {"d1": ["a", "b", "c"], "d2": ["a", "b"]}
    f = fp.features(writes, active, prior_authors={"/p": {"a"}})
    assert f[("a", "d1")] == {"writes": 3, "max_writes_one_doc": 2, "total_chars": 35, "max_chars": 20,
                             "coedit_same_day": 2, "coedit_window": 2, "first_time_author_writes": 1, "session_burst": 2}
    assert f[("b", "d1")]["first_time_author_writes"] == 1 and f[("b", "d1")]["coedit_same_day"] == 2
    assert f[("c", "d1")] == {k: 0.0 for k in fp.FEATURES}
    assert f[("a", "d2")]["coedit_same_day"] == 1 and f[("a", "d2")]["coedit_window"] == 2


def test_fit_rules_and_apply_rule_with_intervals():
    feats = {("h%d" % i, "d"): {k: 0.0 for k in fp.FEATURES} for i in range(17)}
    feats[("h17", "d")] = {k: 1.0 for k in fp.FEATURES}
    feats[("h18", "d")] = {k: 1.0 for k in fp.FEATURES}
    feats[("h19", "d")] = {k: 4.0 for k in fp.FEATURES}
    rules = fp.fit_rules(feats, rate=0.05)
    r = rules["writes"]
    # the seal's mechanism: the smallest observed t with share strictly above it <= 0.05 (here t = 1, p_tie 0)
    assert r["threshold"] == 1.0 and r["p_tie"] == 0.0 and abs(r["expected_rate"] - 0.05) < 1e-12 and not r["degenerate"]
    res = fp.apply_rule(r, {**feats, ("x", "d"): {k: 5.0 for k in fp.FEATURES}}, "writes", [("x", "d"), ("h0", "d")], "stem")
    assert res["flagged"] == 1 and res["n"] == 2 and res["interval"] == [0.0126, 0.9874]


def test_placement_and_chance():
    p = fp.placement(3, [0, 0, 1, 2, 3, 5])
    assert p == {"count": 3, "share_honest_below": round(4 / 6, 4), "share_honest_at_or_below": round(5 / 6, 4)}
    assert abs(fp.chance(0.05, 2) - 0.0975) < 1e-12
