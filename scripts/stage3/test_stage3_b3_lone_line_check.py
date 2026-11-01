"""Tests for stage3_b3_lone_line_check.py (brief 27 E1 and E4): the comparison with brief 26's output counts differences
by reason, the pre-change module is the fork's 52a79312, and the module diff stays outside the Inserter class. Synthetic
records carry ids and counts only; no network, nothing sealed.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_lone_line_check.py
"""
from __future__ import annotations

import copy
import hashlib
import inspect
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_lone_line_check as lc  # noqa: E402
import stage3_t1 as t1  # noqa: E402

D1, D2 = "2026-04-06", "2026-04-07"


def _item(key, valid, lines=None, drop=False):
    return {"item_id": key, "drop": drop, "drop_literal": False,
            "draws": {"valid_draws": [list(x) for x in valid], "n_drawable": len(valid) + 1},
            "lone_lines": [{"valid_draws": [list(x) for x in ln], "n_drawable": len(ln)} for ln in (lines or [])]}


def _result(items, drop=()):
    return {"items": items, "drop_list": {"ids": list(drop), "ids_literal": [], "net_n": {"78": 1}},
            "module": {"sha256": "a", "inserter_class_sha256": "b", "inserter_class_equals_t1v3_manifest": True, "lines": {}},
            "module_findings": [{"id": "M1", "lines": [1], "count": 7, "count_of": "x"}], "totals": {"items": len(items)},
            "written": "now", "s1_restriction": "line 1"}


def test_an_identical_rerun_reproduces():
    old = _result([_item("k1", [(D1, "a"), (D2, "b")], [[(D1, "a")]] * 3), _item("k2", [(D1, "c")], drop=True)], drop=["k2"])
    new = copy.deepcopy(old)
    new["module"] = {**old["module"], "sha256": "z", "lines": {"x": 9}}
    new["module_findings"][0]["lines"] = [42]                  # line numbers move; counts do not
    new["written"], new["s1_restriction"] = "later", "line 42"
    c = lc.compare_dryrun(old, new)
    assert c["reproduced"] and c["differences_by_reason"] == {} and c["items_compared"] == 2 and c["lone_line_sets_compared"] == 3
    assert all(c["sections_equal"].values()) and c["module_finding_counts_equal"]


def test_differences_are_counted_by_reason():
    old = _result([_item("k1", [(D1, "a"), (D2, "b")], [[(D1, "a")]] * 3), _item("k2", [(D1, "c")], drop=True)], drop=["k2"])
    new = copy.deepcopy(old)
    new["items"][0]["draws"]["valid_draws"] = [[D1, "a"]]
    new["items"][0]["lone_lines"][1]["valid_draws"] = []
    new["drop_list"]["ids"] = []
    new["module_findings"][0]["count"] = 8
    c = lc.compare_dryrun(old, new)
    assert not c["reproduced"]
    assert c["differences_by_reason"] == {"item valid-draw set": 1, "lone-line valid-draw set": 1, "drop list (pair rule)": 1,
                                          "item record (any field)": 1, "module finding counts": 1}
    assert c["sections_equal"]["items"] is False and c["sections_equal"]["drop_list"] is False


def test_order_within_a_valid_set_is_not_a_difference():
    old = _result([_item("k1", [(D1, "a"), (D2, "b")])])
    new = copy.deepcopy(old)
    new["items"][0]["draws"]["valid_draws"].reverse()
    c = lc.compare_dryrun(old, new)
    assert c["differences_by_reason"] == {"item record (any field)": 1}       # the set is equal; the record's order is not


@pytest.mark.skipif(not (lc.FORK / ".git").exists(), reason="the fork's history is not on disk")
def test_the_pre_change_module_is_the_forks_52a79312_and_the_diff_stays_outside_the_inserter():
    src = lc.pre_change_source()
    assert hashlib.sha256(src).hexdigest() == lc.PRE_SHA256
    d = lc.module_diff()
    assert d["inserter_class_source_in_old_and_new"] and d["hunks"]
    lines, start = inspect.getsourcelines(t1.Inserter)
    end = start + len(lines) - 1
    old_lines = src.decode("utf-8").splitlines()
    old_start = next(i + 1 for i, ln in enumerate(old_lines) if ln.startswith("class Inserter:"))
    old_end = old_start + len(lines) - 1
    for h in d["hunks"]:
        a, b = h["new_lines"]
        assert b < start or a > end or h["added"] == 0, h            # nothing added inside the class
        oa, ob = h["old_lines"]
        assert ob < old_start or oa > old_end or h["removed"] == 0, h  # nothing removed from it
    assert hashlib.sha256(inspect.getsource(t1.Inserter).encode("utf-8")).hexdigest() == lc.PRE_CLASS_SHA256


def test_duplicate_item_ids_are_a_difference():
    old = _result([_item("k1", [(D1, "a"), (D2, "b")]), _item("k2", [(D1, "c")])])
    new = copy.deepcopy(old)
    new["items"].insert(0, _item("k2", [(D2, "z")]))           # a changed duplicate before the original
    c = lc.compare_dryrun(old, new)
    assert not c["reproduced"] and c["differences_by_reason"].get("duplicate item ids") == 1


def test_the_report_refuses_parts_made_by_other_inputs():
    fp = {"module_sha256": "m", "harness_sha256": "h", "valid_draws_sha256": "v", "brief26_script_sha256": "s"}
    ok = {"replay": {"fingerprint": fp}, "lines": {"fingerprint": dict(fp)}}
    lc.check_parts(ok, fp)
    with pytest.raises(SystemExit):
        lc.check_parts({**ok, "lines": {"fingerprint": {**fp, "module_sha256": "older"}}}, fp)
    with pytest.raises(SystemExit):
        lc.check_parts({**ok, "items": {}}, fp)                  # a part without a fingerprint
    cur = lc.fingerprint()
    assert set(cur) == set(fp) and cur["module_sha256"] == hashlib.sha256(Path(t1.__file__).read_bytes()).hexdigest()


def test_a_part_is_saved_only_with_the_inputs_it_was_run_with(tmp_path, monkeypatch):
    """The fingerprint is taken when the harness imports its inputs; a part whose inputs changed during the run is not
    saved."""
    monkeypatch.setattr(lc, "PARTS", tmp_path)
    monkeypatch.setattr(lc, "_guard", lambda: [])
    assert lc.FINGERPRINT_AT_IMPORT == lc.fingerprint()
    stale = {**lc.FINGERPRINT_AT_IMPORT, "module_sha256": "0" * 64}
    with pytest.raises(SystemExit):
        lc.write_part("replay", {"identical": True}, stale)
    assert not (tmp_path / "replay.json").exists()
    lc.write_part("replay", {"identical": True}, lc.FINGERPRINT_AT_IMPORT)
    assert (tmp_path / "replay.json").exists()
