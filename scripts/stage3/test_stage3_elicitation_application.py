"""Tests for stage3_elicitation_application.py (brief 30 Part 3, the edit-application check of the certified and the
quiet-but-illegible items against the states round 2 uses). Invented trees and invented draws; the inserter itself is
brief 26's and is not run here."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_application as ap  # noqa: E402
import stage3_b3_inserter_dry_run as dry  # noqa: E402


def _stmt(tag: str) -> dict:
    return {"op": "replace", "anchor": f"anchor {tag} xxxxxxxx", "replace": f"replacement {tag} yyyyyyyy", "region": "r", "kind": "value", "alone": "a", "token": tag}


def _tree(tmp_path: Path, writer: str, rnd: int, classes: dict[str, str], docs: dict[str, str], comp: dict[str, float]) -> Path:
    """part3/round-N/<writer>/{round-record.json, converted/{key,payloads}.json} and raters/<writer>-rN-cert/gate-i.json."""
    p = tmp_path
    r = p / f"round-{rnd}" / writer
    (r / "converted").mkdir(parents=True)
    ids_by_class: dict[str, list[str]] = {}
    for i, c in classes.items():
        ids_by_class.setdefault(c, []).append(i)
    (r / "round-record.json").write_text(json.dumps({"writer": writer, "round": rnd, "ids_by_class": ids_by_class}), encoding="utf-8")
    key = {"triples": {i: {"writer": writer, "mechanism": "m", "document": docs[i],
                           "plantings": [{"file": "v2", "id": f"p-{i}", "arm": "conforming"}]} for i in classes}}
    pays = {"payloads": [{"id": f"p-{i}", "document": docs[i], "arm": "conforming", "statements": [_stmt(f"{i}{k}") for k in range(3)]}
                         for i in classes]}
    (r / "converted" / "key.json").write_text(json.dumps(key), encoding="utf-8")
    (r / "converted" / "payloads.json").write_text(json.dumps(pays), encoding="utf-8")
    g = p / "raters" / f"{writer}-r{rnd}-cert"
    g.mkdir(parents=True)
    (g / "gate-i.json").write_text(json.dumps({"composition": comp, "gate_i": {i: True for i in classes}}), encoding="utf-8")
    return p


def test_discover_lists_the_writer_rounds_that_have_a_round_record(tmp_path):
    _tree(tmp_path, "wa", 1, {"x": "certified"}, {"x": "/d1"}, {"x": 50.0})
    _tree(tmp_path, "wb", 3, {"y": "certified"}, {"y": "/d1"}, {"y": 40.0})
    (tmp_path / "round-2" / "wc").mkdir(parents=True)        # a directory with no record is not a round
    assert ap.discover(tmp_path) == [("wa", 1), ("wb", 3)]


def test_load_items_takes_only_certified_and_illegible_items_with_their_own_statements(tmp_path):
    classes = {"c1": "certified", "i1": "quiet_but_illegible", "l1": "loud", "m1": "mixed", "p1": "part_derivable", "n1": "not_evaluable"}
    docs = {k: "/d1" for k in classes}
    _tree(tmp_path, "wa", 3, classes, docs, {k: 45.0 for k in classes})
    items = ap.load_items(tmp_path, [("wa", 3)])
    assert [it["item_id"] for it in items] == ["c1", "i1"]
    c1 = items[0]
    assert (c1["writer"], c1["round"], c1["class"], c1["document"], c1["composition"]) == ("wa", 3, "certified", "/d1", 45.0)
    assert c1["payload_id"] == "p-c1" and len(c1["statements"]) == 3 and c1["statements"][0]["token"] == "c10"


def test_load_items_refuses_an_item_whose_payload_is_missing(tmp_path):
    _tree(tmp_path, "wa", 3, {"c1": "certified"}, {"c1": "/d1"}, {"c1": 50.0})
    pj = tmp_path / "round-3" / "wa" / "converted" / "payloads.json"
    pj.write_text(json.dumps({"payloads": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="payload"):
        ap.load_items(tmp_path, [("wa", 3)])


def test_load_items_refuses_a_payload_that_is_not_three_statements(tmp_path):
    _tree(tmp_path, "wa", 3, {"c1": "certified"}, {"c1": "/d1"}, {"c1": 50.0})
    pj = tmp_path / "round-3" / "wa" / "converted" / "payloads.json"
    d = json.loads(pj.read_text(encoding="utf-8"))
    d["payloads"][0]["statements"] = d["payloads"][0]["statements"][:2]
    pj.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(ValueError, match="three"):
        ap.load_items(tmp_path, [("wa", 3)])


def test_load_items_keys_an_item_by_writer_round_and_id_because_the_converters_ids_repeat_across_rounds(tmp_path):
    # the converter's `_opaque` ignores its salt: the same writer numbering gives the same id in every round
    _tree(tmp_path, "wa", 1, {"c1": "certified"}, {"c1": "/d1"}, {"c1": 50.0})
    _tree(tmp_path, "wa", 2, {"c1": "certified"}, {"c1": "/d1"}, {"c1": 41.0})
    _tree(tmp_path, "wb", 2, {"c1": "certified"}, {"c1": "/d2"}, {"c1": 44.0})
    items = ap.load_items(tmp_path, [("wa", 1), ("wa", 2), ("wb", 2)])
    assert [it["item_id"] for it in items] == ["c1", "c1", "c1"]
    assert len({it["uid"] for it in items}) == 3
    assert {it["uid"] for it in items} == {"wa:r1:c1", "wa:r2:c1", "wb:r2:c1"}


def test_load_items_refuses_the_same_writer_round_listed_twice(tmp_path):
    _tree(tmp_path, "wa", 1, {"c1": "certified"}, {"c1": "/d1"}, {"c1": 50.0})
    with pytest.raises(ValueError, match="twice"):
        ap.load_items(tmp_path, [("wa", 1), ("wa", 1)])


def _draws(valid, clean, n_drawable=None):
    return {"n_drawable": n_drawable if n_drawable is not None else len(valid), "n_valid": len(valid),
            "valid_by_day": {"d1": sum(1 for d, _ in valid if d == "d1"), "d2": sum(1 for d, _ in valid if d == "d2")},
            "pair_ok_distinct_days": dry.pair_ok(valid, True), "pair_ok_distinct_authors": dry.pair_ok(valid, False),
            "literal_ok": len(valid) >= 2, "invalid_reasons": {}, "clean_valid": len(clean),
            "clean_pair_ok_distinct_days": dry.pair_ok(clean, True), "clean_pair_ok_distinct_authors": dry.pair_ok(clean, False),
            "valid_with_broken_honest_edit": len(valid) - len(clean)}


def test_decide_row_drops_an_item_that_lacks_two_placements_on_different_days_by_different_authors():
    item = _draws([("d1", "a"), ("d1", "b")], [("d1", "a"), ("d1", "b")])
    lone = [_draws([("d1", "a"), ("d2", "b")], [("d1", "a"), ("d2", "b")])] * 3
    dec = ap.decide_row(item, lone)
    assert dec["drop"] is True and dec["drop_reasons"][0]["what"] == "item"
    assert dec["drop_literal"] is False                      # two valid draws exist, so the literal count keeps it


def test_decide_row_drops_an_item_for_a_lone_line_that_lacks_two_authors():
    item = _draws([("d1", "a"), ("d2", "b")], [("d1", "a"), ("d2", "b")])
    lone = [_draws([("d1", "a"), ("d2", "b")], [("d1", "a")]), _draws([("d1", "a"), ("d2", "a")], []), _draws([("d1", "a"), ("d2", "b")], [])]
    dec = ap.decide_row(item, lone)
    assert dec["drop"] is True and [r["what"] for r in dec["drop_reasons"]] == ["lone line 2"]


def test_decide_row_keeps_an_item_that_passes_every_need_and_reports_the_clean_need_beside():
    item = _draws([("d1", "a"), ("d2", "b")], [("d1", "a")])
    lone = [_draws([("d1", "a"), ("d2", "b")], [("d1", "a"), ("d2", "b")])] * 3
    dec = ap.decide_row(item, lone)
    assert dec["drop"] is False and dec["drop_reasons"] == []
    assert dec["drop_clean"] is True            # no clean pair on different days for the item: dropped under the clean rule


def test_decide_row_clean_rule_keeps_an_item_with_clean_pairs_everywhere():
    clean = [("d1", "a"), ("d2", "b")]
    dec = ap.decide_row(_draws(clean, clean), [_draws(clean, clean)] * 3)
    assert dec["drop"] is False and dec["drop_clean"] is False


def test_summarise_counts_items_and_drops_by_writer_round_and_class():
    rows = [
        {"writer": "wa", "round": 1, "class": "certified", "drop": False, "drop_clean": False, "drop_literal": False},
        {"writer": "wa", "round": 1, "class": "certified", "drop": True, "drop_clean": True, "drop_literal": False},
        {"writer": "wb", "round": 3, "class": "quiet_but_illegible", "drop": True, "drop_clean": True, "drop_literal": True},
        {"writer": "wb", "round": 3, "class": "certified", "drop": False, "drop_clean": True, "drop_literal": False},
    ]
    s = ap.summarise(rows)
    assert s["wa"]["1"]["certified"] == {"items": 2, "dropped": 1, "dropped_literal": 0, "dropped_clean": 1, "kept": 1}
    assert s["wb"]["3"]["quiet_but_illegible"] == {"items": 1, "dropped": 1, "dropped_literal": 1, "dropped_clean": 1, "kept": 0}
    assert s["wb"]["3"]["certified"]["kept"] == 1


def _row(writer, doc, comp, cls, drop):
    return {"writer": writer, "round": 3, "document": doc, "composition": comp, "class": cls, "drop": drop, "drop_clean": drop}


def test_matched_before_and_after_the_drops_removes_a_dropped_item_from_its_stratum():
    rows = [_row("wb", "/d1", 31, "certified", False), _row("wb", "/d1", 33, "certified", True), _row("wb", "/d1", 35, "quiet_but_illegible", False),
            _row("wb", "/d2", 31, "certified", False)]
    m = ap.matched_before_after(rows)
    assert m["before"]["n_c"] == 2 and m["before"]["n_i"] == 1 and m["before"]["n_c_total"] == 3
    assert m["after"]["n_c"] == 1 and m["after"]["n_i"] == 1 and m["after"]["n_eff"] == pytest.approx(1.0)


def test_matched_after_drops_is_zero_when_the_only_illegible_item_is_dropped():
    rows = [_row("wb", "/d1", 31, "certified", False), _row("wb", "/d1", 35, "quiet_but_illegible", True)]
    m = ap.matched_before_after(rows)
    assert m["before"]["n_eff"] == pytest.approx(1.0) and m["after"]["n_eff"] == 0.0


def test_assert_clean_refuses_to_write_a_guarded_string():
    ap.assert_clean('{"x": 1}', ["secret anchor text"])
    with pytest.raises(SystemExit):
        ap.assert_clean('{"x": "a secret anchor text b"}', ["secret anchor text"])


def test_guard_texts_hold_every_line_anchor_and_region_of_every_item_and_long_lines_of_the_day0_documents():
    items = [{"statements": [{"op": "replace", "anchor": "an anchor of some length", "replace": "a replacement line {date} then a long tail here", "region": "x"}]}]
    g = ap.guard_texts(items, {"/d": "short\nthis is a day zero document line that is long enough"})
    assert "an anchor of some length" in g and "a replacement line " in g and " then a long tail here" in g
    assert "x" not in g                                      # a fragment under twelve characters is not a guard string
    assert "this is a day zero document line that is long enough" in g and "short" not in g


def test_enumerate_with_clean_counts_the_valid_draws_that_break_no_honest_edit(monkeypatch):
    ins = SimpleNamespace(days=["d1", "d2", "d3"])
    pools = {"d1": ["a", "b"], "d2": ["b", "c"]}
    monkeypatch.setattr(dry, "drawable_authors", lambda ins_, path, day, anchors: (pools[day], {"pool": len(pools[day]), "anchored": 0, "touching": 0}))
    verdicts = {("d1", "a"): (True, 0), ("d1", "b"): (True, 3), ("d2", "b"): (True, 0), ("d2", "c"): (False, 0)}

    def fake_run_draw(ins_, states, key, payload, stmts, day, acct, single, found_day0):
        v, broken = verdicts[(day, acct)]
        return {"day": day, "author": acct, "valid": v, "module_samples": 2, "module_samples_no_time": 0, "module_runs_placed": 2,
                "module_runs_ok": 2 if v else 0, "module_composed": 2, "module_stopped": 0, "states_checked": 1, "joint_states_applicable": 1,
                "joint_failures": {}, "reasons": {} if v else {"x": 1}, "line_fail": {0: {}, 1: {}, 2: {}}, "honest_edits_broken_max": broken}

    monkeypatch.setattr(dry, "run_draw", fake_run_draw)
    payload = {"id": "p", "document": "/d", "statements": [_stmt("a"), _stmt("b"), _stmt("c")]}
    out = ap.enumerate_with_clean(ins, object(), "k", payload, payload["statements"], False, [True, True, True])
    assert out["n_valid"] == 3 and out["clean_valid"] == 2 and out["valid_with_broken_honest_edit"] == 1
    assert out["clean_pair_ok_distinct_days"] is True          # (d1, a) and (d2, b): different days and authors
    assert dry.run_draw is fake_run_draw                       # the module's function is put back


def test_enumerate_with_clean_puts_back_the_module_function_after_an_error(monkeypatch):
    ins = SimpleNamespace(days=["d1", "d2"])
    monkeypatch.setattr(dry, "drawable_authors", lambda *a, **k: (["a"], {"pool": 1, "anchored": 0, "touching": 0}))

    def boom(*a, **k):
        raise RuntimeError("x")

    monkeypatch.setattr(dry, "run_draw", boom)
    with pytest.raises(RuntimeError):
        ap.enumerate_with_clean(ins, object(), "k", {"document": "/d"}, [_stmt("a")], True, [True])
    assert dry.run_draw is boom


def _brow(writer, op_pattern, drop, mech="m", doc="/shared/x/README.md", clean=None, lone_authors=None):
    lines = [{"op": op, "day0_found": True} for op in op_pattern]
    lone = [{"n_drawable": (3 if lone_authors is None else lone_authors[i])} for i in range(3)]
    return {"writer": writer, "round": 3, "class": "certified", "mechanism": mech, "document": doc, "drop": drop,
            "drop_clean": drop if clean is None else clean, "lines": lines, "lone_lines": lone}


def test_breakdown_counts_items_and_drops_by_the_pattern_of_operations_per_writer():
    rows = [_brow("wa", ["append"] * 3, False), _brow("wa", ["append"] * 3, False), _brow("wa", ["append", "append", "replace"], True),
            _brow("wb", ["replace"] * 3, True), _brow("wb", ["replace"] * 3, False)]
    b = ap.breakdown(rows)
    assert b["by_operations"]["wa"]["3 append"] == {"items": 2, "dropped": 0, "dropped_clean": 0}
    assert b["by_operations"]["wa"]["2 append + 1 replace"] == {"items": 1, "dropped": 1, "dropped_clean": 1}
    assert b["by_operations"]["wb"]["3 replace"] == {"items": 2, "dropped": 1, "dropped_clean": 1}


def test_breakdown_counts_lone_lines_with_no_author_by_operation():
    rows = [_brow("wb", ["replace"] * 3, True, lone_authors=[0, 0, 5]), _brow("wa", ["append"] * 3, False)]
    b = ap.breakdown(rows)
    assert b["lone_lines_by_operation"]["wb"]["replace"] == {"lines": 3, "no_author": 2}
    assert b["lone_lines_by_operation"]["wa"]["append"] == {"lines": 3, "no_author": 0}


def test_breakdown_counts_by_mechanism_and_by_document_name():
    rows = [_brow("wa", ["append"] * 3, False, mech="x", doc="/shared/a/README.md"),
            _brow("wa", ["append"] * 3, True, mech="y", doc="/shared/a/README.md"),
            _brow("wa", ["append"] * 3, True, mech="y", doc="/shared/b/guide.md")]
    b = ap.breakdown(rows)
    assert b["by_mechanism"]["wa"]["y"] == {"items": 2, "dropped": 2, "dropped_clean": 2}
    assert b["by_document"]["wa"]["README.md"] == {"items": 2, "dropped": 1, "dropped_clean": 1}
    assert b["by_document"]["wa"]["guide.md"]["items"] == 1
