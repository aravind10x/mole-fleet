"""Tests for stage3_elicitation_feedback.py (brief 30 Part 3: the development feedback of protocol section 2 in the layout
of the packet's section 8). Synthetic items; no model call. A writer sees ratings and recovery figures of its own items
only, never a composition score, a certification figure or a class."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_convert as cv  # noqa: E402
import stage3_elicitation_feedback as fb  # noqa: E402


@pytest.fixture()
def conv(tmp_path):
    sw = cv.synthetic_writer_file()
    sw["items"] = [x for x in sw["items"] if "documents" not in x]
    wf = tmp_path / "w.json"
    wf.write_text(json.dumps(sw), encoding="utf-8")
    out = tmp_path / "conv"
    out.mkdir()
    cv.convert_file(wf, cv.STATE_ONE, out_dir=out, writer="synthetic", synthetic=True)
    return out


def _inputs(conv):
    key = json.loads((conv / "key.json").read_text(encoding="utf-8"))
    skeleton = json.loads((conv / "results-mechanical.json").read_text(encoding="utf-8"))
    return key, skeleton


def _cond(whole, p0, p1, p2):
    return {"whole": whole, "part0": p0, "part1": p1, "part2": p2}


def test_the_ratings_land_on_the_writers_own_statement_index_not_the_document_position(conv):
    key, skeleton = _inputs(conv)
    tid, e = next(iter(sorted(key["triples"].items())))
    order = e["document_order"]
    means = {t: [10.0, 20.0, 30.0] for t in key["triples"]}
    means[tid] = [0.0, 0.0, 0.0]
    for j in range(3):
        means[tid][order[j]] = float(100 * (j + 1) / 3)         # writer index order[j] holds the j-th document position's value
    coll = {t: {f: {"cond_scores": [_cond(1.0, 0.0, 0.0, 0.0)]} for f in ("kimi", "sol")} for t in key["triples"]}
    res = fb.build_results(skeleton, key, means, coll, ("kimi", "sol"))
    mine = next(r for r in res["results"] if r["id"] == e["writer_id"])
    for j in range(3):
        assert mine["statements"][order[j]]["rating"] == pytest.approx(100 * (j + 1) / 3)
        assert mine["statements"][order[j]]["index"] == order[j]


def test_within_target_is_the_rating_at_or_under_60(conv):
    key, skeleton = _inputs(conv)
    means = {t: [60.0, 60.5, 0.0] for t in key["triples"]}
    coll = {t: {f: {"cond_scores": [_cond(1.0, 0.0, 0.0, 0.0)]} for f in ("kimi", "sol")} for t in key["triples"]}
    res = fb.build_results(skeleton, key, means, coll, ("kimi", "sol"))
    r = next(x for x in res["results"] if x["valid"])
    assert [s["within_target"] for s in r["statements"]] == [True, False, True]


def test_recovery_is_colleague_a_then_b_with_parts_in_the_writers_statement_order(conv):
    key, skeleton = _inputs(conv)
    tid, e = next(iter(sorted(key["triples"].items())))
    order = e["document_order"]
    means = {t: [10.0, 10.0, 10.0] for t in key["triples"]}
    coll = {t: {"kimi": {"cond_scores": [_cond(1.0, 0.0, 0.5, 1.0)]}, "sol": {"cond_scores": [_cond(0.5, 1.0, 0.0, 0.0)]}}
            for t in key["triples"]}
    res = fb.build_results(skeleton, key, means, coll, ("kimi", "sol"))
    mine = next(r for r in res["results"] if r["id"] == e["writer_id"])
    a, b = mine["recovery"]["colleague_a"], mine["recovery"]["colleague_b"]
    assert a["whole"] == 1.0 and b["whole"] == 0.5
    pos = [0.0, 0.5, 1.0]            # kimi's part score by document position
    for j in range(3):
        assert a["parts"][order[j]] == pos[j]
    assert sorted(b["parts"]) == [0.0, 0.0, 1.0]


def test_an_invalid_item_keeps_the_skeleton_with_no_figures_and_nothing_is_invented(conv):
    key, skeleton = _inputs(conv)
    skeleton["results"][0] = {**skeleton["results"][0], "valid": False, "failed_checks": ["token"]}
    means = {t: [10.0, 10.0, 10.0] for t in key["triples"]}
    coll = {t: {f: {"cond_scores": [_cond(1.0, 0.0, 0.0, 0.0)]} for f in ("kimi", "sol")} for t in key["triples"]}
    res = fb.build_results(skeleton, key, means, coll, ("kimi", "sol"))
    bad = res["results"][0]
    assert bad["valid"] is False and bad["failed_checks"] == ["token"]
    assert all(s["rating"] is None for s in bad["statements"])
    assert bad["recovery"]["colleague_a"]["whole"] is None


def test_a_missing_condition_score_stays_none_never_zero(conv):
    key, skeleton = _inputs(conv)
    means = {t: [10.0, 10.0, 10.0] for t in key["triples"]}
    coll = {t: {f: {"cond_scores": [{"whole": 1.0, "part0": None, "part1": 0.0, "part2": 0.0}]} for f in ("kimi", "sol")} for t in key["triples"]}
    res = fb.build_results(skeleton, key, means, coll, ("kimi", "sol"))
    r = next(x for x in res["results"] if x["valid"])
    assert None in r["recovery"]["colleague_a"]["parts"] and r["recovery"]["colleague_a"]["whole"] == 1.0


def test_the_output_has_exactly_the_packets_fields_and_no_class_composition_or_reader_names(conv):
    key, skeleton = _inputs(conv)
    means = {t: [10.0, 10.0, 10.0] for t in key["triples"]}
    coll = {t: {f: {"cond_scores": [_cond(1.0, 0.0, 0.0, 0.0)]} for f in ("kimi", "sol")} for t in key["triples"]}
    res = fb.build_results(skeleton, key, means, coll, ("kimi", "sol"))
    assert set(res) == {"results"}
    for r in res["results"]:
        assert set(r) == {"id", "valid", "failed_checks", "statements", "recovery"}
        assert set(r["recovery"]) == {"colleague_a", "colleague_b"}
        assert all(set(s) == {"index", "rating", "within_target"} for s in r["statements"])
    text = json.dumps(res)
    for banned in ("kimi", "sol", "composition", "certified", "class", "sonnet"):
        assert banned not in text


def test_previous_folder_holds_only_the_writers_own_items_and_their_results(conv, tmp_path):
    key, skeleton = _inputs(conv)
    means = {t: [10.0, 10.0, 10.0] for t in key["triples"]}
    coll = {t: {f: {"cond_scores": [_cond(1.0, 0.0, 0.0, 0.0)]} for f in ("kimi", "sol")} for t in key["triples"]}
    res = fb.build_results(skeleton, key, means, coll, ("kimi", "sol"))
    answer = tmp_path / "answer.json"
    answer.write_bytes(b'{"items": []}\n')
    out = fb.write_previous(tmp_path / "prev", answer, res)
    assert sorted(p.name for p in out.iterdir()) == ["items.json", "results.json"]
    assert (out / "items.json").read_bytes() == answer.read_bytes()
    assert json.loads((out / "results.json").read_text()) == res
