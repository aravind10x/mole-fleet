"""Offline tests for stage3_p2_power_w (P2 power-v1: block W's uptake class and work clause)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p2_power_w as pw  # noqa: E402


def test_large_fall_reads_U1_and_none_reads_U3_or_U4():
    big = pw.simulate_W_class(-0.5, n_sims=60, n_boot=200, seed=1)
    assert big["P"]["U1"] > 0.8
    none = pw.simulate_W_class(0.0, n_sims=60, n_boot=200, seed=2)
    assert none["P"]["U3"] + none["P"]["U4"] > 0.85
    assert abs(sum(big["P"].values()) - 1) < 1e-9


def test_work_clause_probabilities():
    same = pw.simulate_W_work(0.0, n_sims=60, n_boot=200, seed=3)
    assert same["P"]["excluded"] > 0.5
    drop = pw.simulate_W_work(-0.4, n_sims=60, n_boot=200, seed=4)
    assert drop["P"]["lowered"] > 0.9


def test_seeded():
    assert pw.simulate_W_class(-0.1, n_sims=10, n_boot=20, seed=5) == pw.simulate_W_class(-0.1, n_sims=10, n_boot=20, seed=5)
