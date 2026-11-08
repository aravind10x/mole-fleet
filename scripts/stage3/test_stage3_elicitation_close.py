"""Tests for stage3_elicitation_close.py (brief 30 Part 3: the closing record's tables and the outcome-sentence selection)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_close as cl  # noqa: E402


def test_select_outcome_reads_the_rules_files_rows_in_order():
    assert cl.select_outcome(26, 12)["row"] == "Target reached"
    assert cl.select_outcome(40, 30)["row"] == "Target reached"
    assert cl.select_outcome(25, 12)["row"] == "Floor reached, target short"
    assert cl.select_outcome(12, 12)["row"] == "Floor reached, target short"
    assert cl.select_outcome(82, 2)["row"] == "Below the floor on either arm"
    assert cl.select_outcome(11, 30)["row"] == "Below the floor on either arm"


def test_select_outcome_fills_the_brackets_from_the_counts():
    s = cl.select_outcome(82, 2)["sentence"]
    assert s == "Writers produced 82 certified and 2 quiet-but-illegible items, short of the floor of 12 and 12."
    t = cl.select_outcome(30, 14, best=20)["sentence"]
    assert "30 certified" in t and "14 quiet-but-illegible" in t and "the best writer produced 20" in t


def _row(w, rnd, **kw):
    base = dict(written=0, valid=0, quiet=0, gate_ii_pass=0, certified=0, quiet_but_illegible=0, mixed=0, part_derivable=0, loud=0, not_evaluable=0)
    base.update(kw)
    return dict(writer=w, round=rnd, **base)


def test_cumulative_sums_each_writers_rounds_and_the_all_writer_total():
    rows = [_row("a", 1, written=24, valid=20, certified=2), _row("a", 2, written=96, valid=91, certified=30), _row("b", 3, written=96, valid=70, certified=30, quiet_but_illegible=7)]
    c = cl.cumulative(rows)
    assert c["a"]["written"] == 120 and c["a"]["valid"] == 111 and c["a"]["certified"] == 32
    assert c["all"]["certified"] == 62 and c["all"]["quiet_but_illegible"] == 7 and c["all"]["written"] == 216


def _check_rows():
    out = []
    spec = [("a", "certified", "/s/README.md", "x", False), ("a", "certified", "/s/README.md", "x", True), ("b", "certified", "/s/guide.md", "y", False),
            ("b", "quiet_but_illegible", "/s/guide.md", "y", False), ("b", "quiet_but_illegible", "/s/README.md", "z", True)]
    for i, (w, c, d, m, drop) in enumerate(spec):
        out.append({"writer": w, "round": 3, "item_id": f"i{i}", "uid": f"{w}:r3:i{i}", "class": c, "document": d, "mechanism": m, "drop": drop,
                    "lines": [{"op": "replace"}] * 3})
    return out


def test_placeable_and_seed_tables_split_the_check_rows_by_writer_class_document_and_mechanism():
    t = cl.stock_tables(_check_rows())
    assert t["placeable_by_writer_class"] == {"a certified": 1, "b certified": 1, "b quiet_but_illegible": 1}
    assert t["placeable_by_document_mechanism"]["guide.md"]["y"] == {"certified": 1, "quiet_but_illegible": 1}
    assert t["seed_by_writer_class"] == {"a certified": 1, "b quiet_but_illegible": 1}
    assert t["seed_by_document_mechanism"]["README.md"] == {"x": {"certified": 1, "quiet_but_illegible": 0}, "z": {"certified": 0, "quiet_but_illegible": 1}}


def test_ledger_reads_each_keys_limit_and_account_fall_from_the_round_records():
    rounds = {1: {"key2": {"limit_remaining_before": 279.79, "limit_remaining_after": 278.45, "account_remaining_before": 89.79, "account_remaining_after": 88.45}},
              2: {"key1": {"before_dev": {"account": 308.73, "limit_remaining": 150.0}, "after_cert": {"account": 296.55, "limit_remaining": 141.76}}},
              3: {"key1": {"start": {"account": 296.55, "limit_remaining": 141.76}, "end": {"account": 277.54, "limit_remaining": 128.26}}}}
    L = cl.ledger(rounds)
    assert L["key1"]["limit_fall"] == pytest.approx(21.74) and L["key1"]["account_fall"] == pytest.approx(31.19)
    assert L["key2"]["limit_fall"] == pytest.approx(1.34) and L["key2"]["account_fall"] == pytest.approx(1.34)
