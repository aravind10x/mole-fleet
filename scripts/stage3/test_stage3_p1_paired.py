"""Offline tests for stage3_p1_paired (paired judge differences on the core; descriptive, post hoc). Synthetic only."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p1_paired as pp  # noqa: E402


def world():
    man, outs = [], []
    for i in range(8):
        reg = "routine" if i % 2 == 0 else "middle"
        man.append({"payload_id": f"P{i}", "regime": reg, "scorable": True})
        for f in ("kimi", "sol"):
            for k in range(1, 4):
                outs.append({"run_id": f"c|P{i}|planted|{f}|r{k}", "payload_id": f"P{i}", "arm": "planted", "follower": f,
                             "predicate_result": k <= (3 if i < 4 else 0), "error": None})
    man.append({"payload_id": "A0", "regime": "alarming", "scorable": True})
    return man, outs


def test_values_and_paired_difference():
    man, outs = world()
    base = {f"P{i}": {"flag10": i % 2 == 0} for i in range(8)} | {"A0": {"flag10": True}}
    other = {f"P{i}": {"flag10": False} for i in range(8)} | {"A0": {"flag10": False}}
    vb = pp.payload_values(outs, man, base)
    vo = pp.payload_values(outs, man, other)
    assert len(vb["missed"]) == 8 and vb["regimes"].count("routine") == 4
    assert vb["carried_missed"].mean() == pytest.approx(0.25)                # uptake 1 only on P0..P3, of which P1, P3 missed
    r = pp.paired(vo["carried_missed"], vb["carried_missed"], vb["regimes"], n_boot=500, seed=1)
    assert r["point"] == pytest.approx(0.5 - 0.25)
    assert r["lo"] <= r["point"] <= r["hi"]
    m = pp.paired(vo["missed"], vb["missed"], vb["regimes"], n_boot=500, seed=1)
    assert m["point"] == pytest.approx(1.0 - 0.5)


def test_seeded_and_same_resamples_for_both():
    man, outs = world()
    a = np.arange(8, dtype=float)
    regs = ["routine", "middle"] * 4
    assert pp.paired(a, a, regs, n_boot=100, seed=3) == {"point": 0.0, "lo": 0.0, "hi": 0.0, "n": 8}
    assert pp.paired(a, a * 0, regs, n_boot=100, seed=3) == pp.paired(a, a * 0, regs, n_boot=100, seed=3)
