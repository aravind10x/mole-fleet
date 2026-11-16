"""Offline tests for stage3_ss_repeat (the repeat table: the headline's 48 plants across scorings and runs). Synthetic."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_ss_repeat as rp  # noqa: E402


def man(n=6):
    return [{"payload_id": f"P{i}", "regime": "routine" if i % 2 == 0 else "middle", "scorable": True} for i in range(n)]


def outs(m, carry):
    o = []
    for p, c in zip([x["payload_id"] for x in m], carry):
        for f in ("kimi", "sol"):
            for k in range(1, 4):
                o.append({"run_id": f"r|{p}|planted|{f}|r{k}", "payload_id": p, "arm": "planted", "follower": f,
                          "predicate_result": k <= c, "error": None, "checked": False, "declined": False})
    return o


def test_misses_and_flips():
    flags = {"rec": {"P0": True, "P1": False, "P2": False}, "frz": {"P0": True, "P1": True, "P2": False}, "rep": {"P0": False, "P1": False, "P2": False}}
    r = rp.miss_and_flips(flags, ["P0", "P1", "P2"])
    assert r["missed"] == {"rec": 2, "frz": 1, "rep": 3}
    assert r["flips"]["rec"]["frz"] == 1 and r["flips"]["rec"]["rep"] == 1 and r["flips"]["frz"]["rep"] == 2
    assert r["flips"]["rec"]["rec"] == 0 and r["flips"]["frz"]["rec"] == 1


def test_per_plant_uptake_and_s():
    m = man()
    o = outs(m, [3, 3, 0, 3, 1, 2])
    up = rp.per_plant_uptake(o, m, weights=None)
    assert list(up) == pytest.approx([1, 1, 0, 1, 1 / 3, 2 / 3])
    missed = np.array([1, 0, 1, 0, 1, 1], dtype=float)
    s = rp.boot(up * missed, [x["regime"] for x in m], n_boot=200, seed=1)
    assert s["point"] == pytest.approx((1 + 0 + 0 + 0 + 1 / 3 + 2 / 3) / 6, abs=1e-6)


def test_pooled_by_plant_is_the_mean_of_the_two_runs_per_plant():
    a, b = np.array([0.2, 0.4, 0.0]), np.array([0.0, 0.4, 0.6])
    r = rp.boot((a + b) / 2, ["routine", "middle", "routine"], n_boot=100, seed=3)
    assert r["point"] == pytest.approx(np.mean([(0.2 + 0.0) / 2, 0.4, 0.3]), abs=1e-6)
