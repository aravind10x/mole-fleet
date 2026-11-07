"""Tests for stage3_elicitation_followups.py (brief 30 Part 3: the application check's two follow-ups of 8 Nov, the line
forms of the illegible items and the retention-adjusted forecast cases). Invented trees; counts only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_followups as fu  # noqa: E402

SECRET = "an invented statement text that must never reach an output"


def _stmt(op: str, kind: str) -> dict:
    return {"op": op, "kind": kind, "anchor": SECRET + " anchor", "replace": SECRET, "region": "r", "alone": "a", "token": "tok"}


def _tree(tmp_path: Path, writer: str, rnd: int, items: dict[str, tuple[str, str, list[tuple[str, str]]]]) -> None:
    """items: id -> (class, mechanism, [(op, kind)] x 3)."""
    r = tmp_path / f"round-{rnd}" / writer
    (r / "converted").mkdir(parents=True)
    ids_by_class: dict[str, list[str]] = {}
    for i, (c, _m, _l) in items.items():
        ids_by_class.setdefault(c, []).append(i)
    (r / "round-record.json").write_text(json.dumps({"ids_by_class": ids_by_class}), encoding="utf-8")
    key = {"triples": {i: {"mechanism": m, "document": "/d/x.md", "plantings": [{"file": "v2", "id": f"p-{i}", "arm": "conforming"}]}
                       for i, (_c, m, _l) in items.items()}}
    pays = {"payloads": [{"id": f"p-{i}", "document": "/d/x.md", "statements": [_stmt(op, k) for op, k in lines]} for i, (_c, _m, lines) in items.items()]}
    (r / "converted" / "key.json").write_text(json.dumps(key), encoding="utf-8")
    (r / "converted" / "payloads.json").write_text(json.dumps(pays), encoding="utf-8")


A3 = [("append", "procedure")] * 3
R3 = [("replace", "procedure")] * 3
MIX = [("append", "procedure"), ("replace", "procedure"), ("replace", "recipient")]


def _fixture(tmp_path: Path) -> Path:
    _tree(tmp_path, "wa", 2, {"a1": ("certified", "des", A3), "a2": ("part_derivable", "des", A3), "a3": ("certified", "des", A3),
                              "a4": ("mixed", "ind", MIX)})
    _tree(tmp_path, "wb", 3, {"b1": ("quiet_but_illegible", "ord", R3), "b2": ("quiet_but_illegible", "ord", R3),
                              "b3": ("certified", "ord", R3), "b4": ("quiet_but_illegible", "des", MIX), "b5": ("loud", "des", MIX)})
    return tmp_path


def test_line_forms_reads_every_valid_item_with_its_class_mechanism_and_operations(tmp_path):
    forms = fu.line_forms(_fixture(tmp_path), [("wa", 2), ("wb", 3)])
    assert len(forms) == 9
    by = {f["item_id"]: f for f in forms}
    assert by["a1"]["form"] == "append-only" and by["b1"]["form"] == "replace-bearing" and by["a4"]["form"] == "replace-bearing"
    assert by["a4"]["ops"] == "1 append + 2 replace" and by["b1"]["ops"] == "3 replace"
    assert by["b1"]["class"] == "quiet_but_illegible" and by["b1"]["mechanism"] == "ord" and by["b1"]["writer"] == "wb"
    assert by["a4"]["lines"] == [("append", "procedure"), ("replace", "procedure"), ("replace", "recipient")]


def test_form_table_counts_valid_items_by_writer_form_and_class(tmp_path):
    forms = fu.line_forms(_fixture(tmp_path), [("wa", 2), ("wb", 3)])
    t = fu.form_table(forms)
    assert t["wa"]["append-only"] == {"valid": 3, "certified": 2, "quiet_but_illegible": 0, "other": 1}
    assert t["wa"]["replace-bearing"]["valid"] == 1
    assert t["wb"]["replace-bearing"] == {"valid": 5, "certified": 1, "quiet_but_illegible": 3, "other": 1}
    assert "append-only" not in t["wb"]


def test_mechanism_table_counts_by_mechanism_and_form_across_writers(tmp_path):
    forms = fu.line_forms(_fixture(tmp_path), [("wa", 2), ("wb", 3)])
    t = fu.mechanism_table(forms)
    assert t["des"]["append-only"] == {"valid": 3, "certified": 2, "quiet_but_illegible": 0, "other": 1, "writers": ["wa"]}
    assert t["des"]["replace-bearing"]["quiet_but_illegible"] == 1 and t["ord"]["replace-bearing"]["valid"] == 3
    assert "append-only" not in t["ord"]


def test_illegible_feasibility_says_an_item_could_be_three_appends_only_where_its_mechanism_has_an_append_only_precedent(tmp_path):
    forms = fu.line_forms(_fixture(tmp_path), [("wa", 2), ("wb", 3)])
    f = fu.illegible_feasibility(forms)
    assert f["items"] == 3 and f["could_be_three_appends"] == 1 and f["need_a_replaced_line"] == 2
    assert f["by_mechanism"]["ord"]["items"] == 2 and f["by_mechanism"]["ord"]["could_be_three_appends"] is False
    assert f["by_mechanism"]["ord"]["append_only_precedent"] == {"valid": 0, "certified": 0, "quiet_but_illegible": 0}
    assert f["by_mechanism"]["des"]["could_be_three_appends"] is True
    assert f["by_mechanism"]["des"]["append_only_precedent"] == {"valid": 3, "certified": 2, "quiet_but_illegible": 0}
    # the replaced lines of the item: the content kind the converter gave them (procedure: a numbered step replaced)
    assert f["by_mechanism"]["ord"]["replace_lines"] == {"procedure": 6}
    assert f["by_mechanism"]["des"]["replace_lines"] == {"procedure": 1, "recipient": 1}


def test_outputs_carry_no_statement_text(tmp_path):
    forms = fu.line_forms(_fixture(tmp_path), [("wa", 2), ("wb", 3)])
    blob = json.dumps({"t": fu.form_table(forms), "m": fu.mechanism_table(forms), "f": fu.illegible_feasibility(forms)})
    assert SECRET not in blob and "anchor" not in blob


def test_cases_name_the_scenarios_and_take_retention_from_the_check_and_the_append_only_record():
    check = {"items": [{"writer": "muse", "class": "certified", "drop": d, "round": 3, "document": "/a", "composition": 40.0} for d in [False] + [True] * 4]
             + [{"writer": "muse", "class": "quiet_but_illegible", "drop": d, "round": 3, "document": "/a", "composition": 40.0} for d in [False, True, True]]
             + [{"writer": "sol", "class": "certified", "drop": d, "round": 3, "document": "/a", "composition": 40.0} for d in [False] * 9 + [True]]}
    cs = fu.cases(check, writer="muse", sol="sol", feasible_share=2 / 7, append_only_valid=168, append_only_illegible=0)
    assert [c["name"] for c in cs] == ["B", "A1", "A2", "A3"]
    b, a1, a2, a3 = cs
    assert b["retention"]["muse"]["c"] == [0.5 + 1, 0.5 + 4] and b["retention"]["muse"]["i"] == [0.5 + 1, 0.5 + 2]
    assert a1["retention"]["muse"]["c"] == [0.5 + 9, 0.5 + 1] and a1["retention"]["muse"]["i"] == a1["retention"]["muse"]["c"]
    assert a2["i_scale"] == {"muse": pytest.approx(2 / 7)} and a2["retention"] == a1["retention"]
    assert a3["i_post"] == {"muse": [0.5 + 0, 0.5 + 168]} and all(c["writing"] == ["muse"] for c in cs)


def test_form_risk_counts_append_only_items_replace_bearing_items_and_append_lines_by_writer(tmp_path):
    forms = fu.line_forms(_fixture(tmp_path), [("wa", 2), ("wb", 3)])
    r = fu.form_risk(forms)
    assert r["append_only"] == {"valid": 3, "quiet_but_illegible": 0, "writers": ["wa"]}
    assert r["replace_bearing"]["wa"] == {"valid": 1, "quiet_but_illegible": 0}
    assert r["replace_bearing"]["wb"] == {"valid": 5, "quiet_but_illegible": 3}
    assert r["append_lines"] == {"wa": {"append": 10, "lines": 12}, "wb": {"append": 2, "lines": 15}}
