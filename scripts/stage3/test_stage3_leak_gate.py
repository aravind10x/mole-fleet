"""Tests for stage3_leak_gate.py (design v4 section 11.4; brief 07b F2.4): the permutation
leak gate that replaces the fixed 0.6 band. Synthetic features only; no corpus is needed.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_leak_gate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_leak_gate as lg  # noqa: E402


def _accounts(n_acc: int, days: int) -> list[str]:
    return [f"acc{a:02d}" for a in range(n_acc) for _ in range(days)]


def test_grouped_folds_keep_every_account_in_one_fold_and_spread_positives():
    groups = _accounts(20, 3)
    pos_acc = {"acc00", "acc01", "acc02", "acc03"}
    y = np.array([int(g in pos_acc) for g in groups])
    fold = lg.grouped_folds(groups, y, seed=3, folds=5)
    assert len(fold) == len(groups)
    for g in set(groups):
        assert len({fold[i] for i, gg in enumerate(groups) if gg == g}) == 1
    # positive accounts land in distinct folds when there are at least as many folds
    assert len({fold[i] for i in range(len(groups)) if y[i]}) == 4


def test_account_level_labels_mark_whole_accounts_and_keep_the_count():
    groups = _accounts(10, 3)
    y = lg.account_labels(groups, n_positive_accounts=3, seed=7)
    pos = {g for g, v in zip(groups, y) if v}
    assert len(pos) == 3 and y.sum() == 9
    assert all(v == (g in pos) for g, v in zip(groups, y))


def test_within_account_permutation_keeps_one_positive_per_account():
    groups = ["a", "a", "b", "b", "c", "c"]
    y = np.array([1, 0, 0, 1, 1, 0])
    for seed in range(10):
        p = lg.permute_within_account(groups, y, seed)
        for g in "abc":
            assert sum(v for gg, v in zip(groups, p) if gg == g) == 1


def test_grouped_classifier_on_pure_noise_sits_near_half_and_the_gate_is_the_p95():
    rng = np.random.default_rng(0)
    groups = _accounts(30, 3)
    X = rng.normal(size=(len(groups), 6))
    y = lg.account_labels(groups, 6, seed=1)
    obs = lg.classify_grouped(X, y, groups, seed=1)
    assert 0.0 <= obs["auroc"] <= 1.0 and obs["folds_used"] == 5
    band = lg.permutation_band(lambda s: {"m": X}, groups, n_positive_accounts=6,
                               seeds=range(100, 160), fold_seed_offset=777777)
    t = np.array(band["classifiers"]["m"]["two_sided_values"])
    assert len(t) == 60
    assert abs(band["classifiers"]["m"]["gate_p95"] - float(np.percentile(t, 95))) < 1e-12
    assert 0.5 <= band["classifiers"]["m"]["gate_p95"] <= 1.0


def test_null_observed_values_fall_inside_the_band_at_about_the_nominal_rate():
    rng = np.random.default_rng(1)
    groups = _accounts(30, 3)
    X = rng.normal(size=(len(groups), 6))
    band = lg.permutation_band(lambda s: {"m": X}, groups, 6, seeds=range(200, 400),
                               fold_seed_offset=777777)
    gate = band["classifiers"]["m"]["gate_p95"]
    above = 0
    for seed in range(40):
        y = lg.account_labels(groups, 6, seed=5000 + seed)
        obs = lg.classify_grouped(X, y, groups, seed=5000 + seed + 777777)
        above += obs["auroc_two_sided"] > gate
    assert above <= 8                      # nominal 5 percent of 40 is 2; allow noise


def test_planted_signal_is_above_the_gate():
    rng = np.random.default_rng(2)
    groups = _accounts(30, 3)
    y = lg.account_labels(groups, 6, seed=9)
    X = rng.normal(size=(len(groups), 6))
    X[:, 0] += 3.0 * y                                  # a strong account-level leak
    band = lg.permutation_band(lambda s: {"m": X}, groups, 6, seeds=range(300, 400),
                               fold_seed_offset=777777)
    obs = lg.classify_grouped(X, y, groups, seed=9 + 777777)
    verdict = lg.gate_verdict(obs["auroc_two_sided"], band["classifiers"]["m"]["gate_p95"])
    assert verdict["above_band"] and obs["auroc_two_sided"] > 0.9


def test_fold_seed_is_decoupled_from_the_label_seed():
    # the same labels with two fold seeds give (in general) different folds: the fold
    # permutation is not the label permutation
    groups = _accounts(12, 2)
    y = lg.account_labels(groups, 3, seed=4)
    f1 = lg.grouped_folds(groups, y, seed=4 + 777777)
    f2 = lg.grouped_folds(groups, y, seed=4 + 777777 + 1)
    assert not np.array_equal(f1, f2)


def test_prereg_text_is_written_before_the_statistic():
    md = lg.prereg_block()
    assert "written before" in md.lower() and "95th percentile" in md and "two-sided" in md
