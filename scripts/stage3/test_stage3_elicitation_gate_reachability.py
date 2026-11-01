"""Tests for stage3_elicitation_gate_reachability.py (brief 29 E0-5): the three certification gates of E0-3 at k
samples, the item classes, the provider determinacy of Part 3's fingerprint join, and, on the real files (skipped when
absent), the reproduction of brief 25's published counts and of Part 3's join block. Ids and aggregates only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_gate_reachability as gr  # noqa: E402

ROOT = HERE.parent.parent


def _item(gi=True, k=(0.0, 0.0), kw=(1.0, 0.0), s=(0.0, 0.5), sw=(0.0, 0.5), sn=None, snw=None):
    readers = {"kimi": {"D_part": list(k), "D_whole": list(kw)}, "sol": {"D_part": list(s), "D_whole": list(sw)}}
    if sn is not None:
        readers["sonnet55"] = {"D_part": list(sn), "D_whole": list(snw)}
    return {"id": "x", "set": "candidate", "writer": "w", "gate_i": gi, "readers": readers}


# ── gate (ii) rules ──────────────────────────────────────────────────────────────────────────────

def test_every_rule():
    assert gr.every([0.0, 0.0]) is True and gr.every([0.0, 0.5]) is False and gr.every([0.0]) is True
    assert gr.every([0.0, None]) is None


def test_sol_mean_rule_threshold_inclusive():
    assert gr.sol_mean([0.5, 0.5]) is True and gr.sol_mean([1.0, 0.0]) is True and gr.sol_mean([1.0, 0.5]) is False
    assert gr.sol_mean([None, 0.0]) is None


# ── gate (iii), three readings ───────────────────────────────────────────────────────────────────

def test_gate_iii_readings():
    g = gr.gate_iii([1.0, 0.0], [0.0, 0.5])          # each reader credits on a different sample
    assert g == {"per_reader_any": True, "same_sample": False, "both_both": False}
    g = gr.gate_iii([0.5, 1.0], [1.0, 0.5])
    assert g == {"per_reader_any": True, "same_sample": True, "both_both": True}
    assert gr.gate_iii([0.0, 0.0], [1.0, 1.0])["per_reader_any"] is False
    assert gr.gate_iii([1.0, None], [1.0, 1.0]) is None


# ── classes (certification protocol section 6) ───────────────────────────────────────────────────

def test_classes():
    sol = ("kimi", "sol", "sol_mean")
    assert gr.classify(_item(gi=False), *sol, k=2) == "loud"
    assert gr.classify(_item(), *sol, k=2) == "certified"                             # kimi s0, sol s1
    assert gr.classify(_item(kw=(0.0, 0.0), sw=(0.0, 0.0)), *sol, k=2) == "quiet_but_illegible"
    assert gr.classify(_item(sw=(0.0, 0.0)), *sol, k=2) == "mixed"
    assert gr.classify(_item(k=(0.0, 0.5)), *sol, k=2) == "part_derivable"            # kimi credits a part once
    assert gr.classify(_item(s=(1.0, 0.5)), *sol, k=2) == "part_derivable"            # sol's mean 0.75
    assert gr.classify(_item(k=(0.0, None)), *sol, k=2) == "not_evaluable"
    assert gr.classify(_item(gi=None), *sol, k=2) == "certified"                      # no rater line: (i) not applied
    assert gr.classify(_item(k=(0.0, 0.5), sw=(1.0, 0.0)), *sol, k=1) == "certified"  # one sample: s0 only


def test_strict_second_reader_rule():
    it = _item(sn=(0.0, 0.5), snw=(1.0, 1.0))
    assert gr.classify(it, "kimi", "sol", "sol_mean", k=2) == "certified"
    assert gr.classify(it, "kimi", "sonnet55", "every", k=2) == "part_derivable"
    assert gr.classify(_item(), "kimi", "sonnet55", "every", k=2) == "not_evaluable"   # no Sonnet 5.5 reading


def test_tally_counts_and_readings():
    items = [_item(), _item(kw=(1.0, 1.0), sw=(0.5, 0.5)), _item(gi=False), _item(kw=(0.0, 0.0), sw=(0.0, 0.0))]
    t = gr.tally(items, "kimi", "sol", "sol_mean", k=2)
    assert t["n"] == 4 and t["classes"]["certified"] == 2 and t["classes"]["loud"] == 1
    assert t["classes"]["quiet_but_illegible"] == 1 and t["gate_ii_pass"] == 3 and t["gate_i_pass"] == 3
    assert t["certified_by_reading"] == {"per_reader_any": 2, "same_sample": 1, "both_both": 1}


# ── Part 3's join: which reads have a determined provider ────────────────────────────────────────

def test_determined_provider():
    export = [{"tokens_prompt": 10, "tokens_completion": 5, "provider": "Wafer", "precision": "MXFP4"},
              {"tokens_prompt": 10, "tokens_completion": 5, "provider": "Wafer", "precision": "MXFP4"},
              {"tokens_prompt": 20, "tokens_completion": 5, "provider": "Wafer", "precision": "MXFP4"},
              {"tokens_prompt": 20, "tokens_completion": 5, "provider": "Relace", "precision": "FP4"},
              {"tokens_prompt": 30, "tokens_completion": 5, "provider": "Morph", "precision": "FP8"}]
    recs = [{"input_tokens": 10, "output_tokens": 5}, {"input_tokens": 10, "output_tokens": 5},
            {"input_tokens": 20, "output_tokens": 5}, {"input_tokens": 20, "output_tokens": 5},
            {"input_tokens": 30, "output_tokens": 5}]
    assert gr.determinacy(recs, export) == ["shared_same", "shared_same", "ambiguous", "ambiguous", "unique"]


def test_wafer_cell():
    prov = {("b25", 0, "a", c): ("Wafer", "MXFP4", "unique") for c in gr.CONDS}
    assert gr.wafer_cell(prov, "b25", 0, "a", strict=True) is True
    prov[("b25", 0, "a", "part1")] = ("Wafer", "MXFP4", "ambiguous")
    assert gr.wafer_cell(prov, "b25", 0, "a", strict=True) is False and gr.wafer_cell(prov, "b25", 0, "a", strict=False)
    prov[("b25", 0, "a", "part2")] = ("Relace", "FP4", "unique")
    assert gr.wafer_cell(prov, "b25", 0, "a", strict=False) is False
    assert gr.wafer_cell(prov, "b25", 1, "a", strict=False) is False                      # no reads at all


# ── the real files (ids and aggregates only) ─────────────────────────────────────────────────────

needs_files = pytest.mark.skipif(not (ROOT / gr.STRATUM).exists() or not (ROOT / gr.KIMI_CSV).exists(),
                                 reason="brief 23/25 files not on disk")


@needs_files
def test_reproduces_brief25_stratum_and_arms():
    items = gr.load_b25(ROOT)
    cand = [i for i in items if i["set"] == "candidate"]
    t = gr.tally(cand, "kimi", "sol", "sol_mean", k=2)
    assert t["n"] == 78 and t["gate_i_pass"] == 78 and t["gate_ii_pass"] == 28            # brief 25: 28 of 78
    assert t["classes"]["certified"] == 11 and t["classes"]["quiet_but_illegible"] == 7   # A6.17.5: 11 and 7
    assert t["classes"]["mixed"] == 10


@needs_files
def test_nulls_are_46_and_none_certified():
    nulls = [i for i in gr.load_b25(ROOT) if i["set"] in ("control", "sham")]
    t = gr.tally(nulls, "kimi", "sol", "sol_mean", k=2)
    assert t["n"] == 46 and t["classes"].get("certified", 0) == 0 and t["gate_ii_pass"] == 46


@needs_files
def test_join_reproduces_part3_block():
    J = gr.kimi_join(ROOT)
    part3 = json.loads((ROOT / gr.PART3).read_text())["kimi"]
    assert J["join"] == part3["join"]
    assert J["by_brief"] == part3["by_brief"]


@needs_files
def test_t1_two_samples_only_on_the_retest_items():
    t1 = [i for i in gr.load_b23(ROOT) if i["set"] in ("t1_v2_conforming", "t1_v3_middle")]
    assert len(t1) == 48 and sum(1 for i in t1 if gr.has_samples(i, "kimi", 2)) == 10
