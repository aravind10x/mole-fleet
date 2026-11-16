"""Tests for note/numbermap.py, on synthetic records. Run: cd note && python -m pytest -q test_numbermap.py"""
import json

import numbermap as nn


def _row(**kw):
    base = {"id": "X1", "status": "released", "numbers": [], "locate": [], "record": "r.md"}
    base.update(kw)
    return base


def test_norm_minus_bold_and_pipes():
    assert nn.norm("**−0.014** \\| `x`") == "-0.014 | x"


def test_number_in_respects_boundaries():
    assert nn.number_in("0.135", "+0.135 [+0.003, +0.271]")
    assert nn.number_in("−0.014", "| raw | -0.014 [-0.087, 0.062] |")
    assert not nn.number_in("0.13", "0.135")
    assert not nn.number_in("35", "0.0035")


def test_check_row_line_locator(tmp_path):
    (tmp_path / "r.md").write_text("| raw | −0.014 [−0.087, 0.062] |\nother\n")
    ok = _row(numbers=["0.014", "0.087"], locate=[{"line": "| raw | -0.014 [-0.087, 0.062] |"}])
    assert nn.check_row(ok, tmp_path) == []
    bad = _row(numbers=["0.099"], locate=[{"line": "| raw | -0.014"}])
    assert any("0.099" in e for e in nn.check_row(bad, tmp_path))
    missing = _row(locate=[{"line": "not there"}])
    assert any("locator not found" in e for e in nn.check_row(missing, tmp_path))


def test_check_row_json_expr_and_derived(tmp_path):
    (tmp_path / "c.json").write_text(json.dumps([{"a": 1, "b": 1}, {"a": 1, "b": 2}, {"a": 3, "b": 3}]))
    r = _row(record="c.json", numbers=["2", "3"], locate=[{"json_expr": "sum(x['a'] == x['b'] for x in d)"},
                                                          {"json_expr": "len(d)"}])
    assert nn.check_row(r, tmp_path) == []
    r2 = _row(record="c.json", numbers=["5"], locate=[{"json_expr": "len(d)"}], derived="3 + 2 = 5")
    assert nn.check_row(r2, tmp_path) == []


def test_unreleased_rows_are_skipped_and_missing_record_fails(tmp_path):
    assert nn.check_row(_row(status="slot", record=None), tmp_path) == []
    assert nn.check_row(_row(record="nope.md"), tmp_path) == ["X1: record missing: nope.md"]


def test_shipped_map_is_well_formed():
    doc = nn.load_map()
    ids = [r["id"] for r in doc["rows"]]
    assert len(ids) == len(set(ids))
    for r in doc["rows"]:
        assert r["status"] in {"released", "design", "slot", "not_in_repository"}
        if r["status"] == "released":
            assert r["record"] and r["locate"]
        held = ("results/stage3/t1", "results/stage3/b1/", "results/stage3/b3/", "results/stage3/q1q2-synthetic/",
                "results/stage3/phase-b/", "results/stage3/find-the-plant/", "results/stage3/prep-report.md")
        assert not (r.get("record") or "").startswith(held), r["id"]
