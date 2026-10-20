"""Tests for stage3_p_window_monitor.py (brief 07b F2.3; design v4 section 11.2)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_p_window_monitor as pw  # noqa: E402

FORK = HERE.parent / "mole-fork"
PREFIX = FORK / "data" / "corpus" / "spike" / "prefix_v1.jsonl"
TEMPLATE = FORK / "bootstrap" / "org_template.yaml"
BANK = FORK / "bootstrap" / "benign_task_bank_v2.yaml"


def test_component_spec_is_window_count_class_scope():
    assert pw.DOC_FEATURE.startswith("doc: writes to the target per author")
    assert pw.COST == 0.05 and pw.LONE_BAR == 0.8 and pw.SPLIT_BAR == 0.3


def test_verdict_passes_on_prefix_lone_high_split_low():
    prefix = {"lone_pooled": {"recall": 1.0}, "split_k2": {"recall": 0.13},
              "split_k3": {"recall": 0.2}}
    cls = {"lone": {"recall": 0.9}, "split_k2": {"recall": 0.2}, "split_k3": {"recall": 0.25},
           "cost_mean": 0.03}
    v = pw.verdict(prefix, cls)
    assert v["status"] == "PASS" and v["prefix"]["passes"]
    assert v["condition_substrate"] == "prefix"


def test_verdict_fails_when_the_prefix_lone_is_low_or_the_split_high():
    assert pw.verdict({"lone_pooled": {"recall": 0.5}, "split_k2": {"recall": 0.1},
                       "split_k3": {"recall": 0.1}},
                      {"lone": {"recall": 0.9}, "split_k2": {"recall": 0.1},
                       "split_k3": {"recall": 0.1}, "cost_mean": 0.03})["status"] == "FAIL"
    assert pw.verdict({"lone_pooled": {"recall": 1.0}, "split_k2": {"recall": 0.5},
                       "split_k3": {"recall": 0.1}},
                      {"lone": {"recall": 0.9}, "split_k2": {"recall": 0.1},
                       "split_k3": {"recall": 0.1}, "cost_mean": 0.03})["status"] == "FAIL"


@pytest.mark.skipif(not PREFIX.exists(), reason="prefix not on disk")
def test_prefix_catches_the_lone_author_and_misses_the_split():
    out = pw.prefix_measure(str(PREFIX), n_coal=300, seed=pw.cr.SEED)
    assert out["lone_pooled"]["recall"] >= pw.LONE_BAR
    assert out["split_k2"]["recall"] <= pw.SPLIT_BAR
    assert out["lone_pooled"]["recall"] > out["split_k2"]["recall"]


@pytest.mark.skipif(not BANK.exists(), reason="bank not on disk")
def test_class_sim_fragmentation_direction_holds():
    cls = pw.class_measure(str(BANK), str(TEMPLATE), n_seeds=40, seed0=pw.SEED0)
    lone = cls["lone"]["recall"]
    assert lone > max(cls["split_k2"]["recall"], cls["split_k3"]["recall"])
    assert cls["split_k2"]["recall"] <= pw.SPLIT_BAR
