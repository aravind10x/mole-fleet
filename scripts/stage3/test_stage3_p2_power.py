"""Offline tests for stage3_p2_power (P2 power-v0, block D's whole rule)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p2_power as pw  # noqa: E402


def test_high_uptake_reads_sentence_1_and_zero_reads_sentence_2():
    hi = pw.simulate_D(0.8, n_sims=60, n_boot=200, seed=1)
    assert hi["P"]["1"] > 0.9
    lo = pw.simulate_D(0.0, n_sims=60, n_boot=200, seed=2)
    assert lo["P"]["2"] > 0.9
    assert abs(sum(hi["P"].values()) - 1.0) < 1e-9


def test_a_noisy_clean_arm_withholds():
    r = pw.simulate_D(0.8, n_sims=40, n_boot=100, seed=3, clean_fire=0.05)
    assert r["P"]["withheld"] > 0.9


def test_unresolved_sol_runs_withhold_through_gate_1():
    r = pw.simulate_D(0.8, n_sims=200, n_boot=50, seed=5, u_sol=0.03)
    assert r["P"]["withheld"] > 0.5 and r["u_sol"] == 0.03


def test_seeded():
    assert pw.simulate_D(0.2, n_sims=20, n_boot=50, seed=4) == pw.simulate_D(0.2, n_sims=20, n_boot=50, seed=4)
