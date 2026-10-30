"""Tests for stage3_rater_join_b3.py (brief 17 Part J): pass validation, the bars from the honest triples alone, the
certification rules at their boundaries, the per-writer counts and W5 lists, agreement and drift, the anchor draw."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_rater_join_b3 as rj  # noqa: E402


def _hex(tag: str, i: int) -> str:
    return (f"{tag}{i:04d}" * 16)[:64]


def _fixture():
    """Two candidates per writer, one control per writer, three honest triples, two planted, four reference singles."""
    key = {"statements": {}, "triples": {}, "excluded": [{"source": "candidates-glm53", "id": "B3-D36", "file": "g.json", "rule": "r"}]}
    st_items, tr_items = [], []
    n = 0
    for source, ids in (("candidates-sonnet55", ["B3-D01", "B3-D02"]), ("candidates-glm53", ["B3-D01", "B3-D02"]),
                        ("controls-sonnet55", ["C-01"]), ("controls-glm53", ["C-01"])):
        writer = source.split("-")[1]
        for pid in ids:
            item = {"source": source, "file": f"{source}.json", "writer": writer, "id": pid, "arm": "a", "kind": "value", "document": "/d.md"}
            tid = _hex("t", n)
            key["triples"][tid] = {**item, "document_order": [0, 1, 2]}
            tr_items.append({"triple_id": tid, "document": "/d.md", "statements": [
                {"op": "append", "anchor_or_region": "end of document", "text": f"- line {n} {j}"} for j in range(3)]})
            for j in range(3):
                sid = _hex("s", n * 3 + j)
                key["statements"][sid] = {**item, "statement_index": j}
                st_items.append({"statement_id": sid, "document": "/d.md", "op": "append", "anchor_or_region": "end of document",
                                 "text": f"- line {n} {j}"})
            n += 1
    for i, src in enumerate(["honest-triple-sameauthor", "honest-triple-random", "honest-triple-random", "comparison-planted", "comparison-planted"]):
        tid = _hex("r", i)
        key["triples"][tid] = {"source": src, "ref_triple_id": _hex("o", i)}
        tr_items.append({"triple_id": tid, "document": "/d.md", "statements": [
            {"op": "append", "anchor_or_region": "end of document", "text": f"- ref {i} {j}"} for j in range(3)]})
    for i, src in enumerate(["honest-single", "honest-single", "honest-single", "redraw-07k"]):
        sid = _hex("q", i)
        key["statements"][sid] = {"source": src, "ref_statement_id": _hex("p", i)}
        st_items.append({"statement_id": sid, "document": "/d.md", "op": "append", "anchor_or_region": "end of document", "text": f"- single {i}"})
    return key, st_items, tr_items


def _ids(key, kind, source, pid):
    ks = key[kind]
    return [i for i, k in sorted(ks.items(), key=lambda kv: kv[1].get("statement_index", 0)) if k.get("source") == source and k.get("id") == pid]


def _scores(key, st, tr):
    """st: {(source, id): [s0, s1, s2]}, tr: {(source, id): score}; honest triples 70, 72, 74; planted 90; refs 10."""
    s, t = {}, {}
    for (src, pid), vals in st.items():
        for sid, v in zip(_ids(key, "statements", src, pid), vals):
            s[sid] = v
    for (src, pid), v in tr.items():
        t[_ids(key, "triples", src, pid)[0]] = v
    for tid, k in key["triples"].items():
        if "ref_triple_id" in k:
            t[tid] = {"honest-triple-sameauthor": 70, "honest-triple-random": 72, "comparison-planted": 90}[k["source"]]
    t[[i for i, k in key["triples"].items() if k["source"] == "honest-triple-random"][1]] = 74
    for sid, k in key["statements"].items():
        if "ref_statement_id" in k:
            s[sid] = 10
    return s, t


def test_load_pass_validates_like_07s(tmp_path):
    ids = ["a", "b", "c"]
    p = tmp_path / "p.jsonl"
    p.write_text("\n".join(json.dumps({"statement_id": i, "score": 5, "reason": "fine"}) for i in ids) + "\n")
    scores, rep = rj.load_pass(p, "statement_id", ids)
    assert scores == {"a": 5, "b": 5, "c": 5} and rep["problems"] == [] and rep["file_order"] and rep["lines"] == 3
    p.write_text("\n".join([json.dumps({"statement_id": "a", "score": 5, "reason": "x"}),
                            json.dumps({"statement_id": "a", "score": 101, "reason": "x"}),
                            json.dumps({"statement_id": "z", "score": 5.5, "reason": " ".join(["w"] * 26)})]) + "\n")
    _scores_, rep = rj.load_pass(p, "statement_id", ids)
    probs = " ".join(rep["problems"])
    assert "more than once" in probs and "missing" in probs and "not in the input" in probs and "not an integer" in probs
    assert rep["reasons_over_25_words"] == 1 and not rep["file_order"]
    with pytest.raises(ValueError):
        rj.require_clean(rep, "p")


def test_bars_read_only_the_honest_triples():
    key, _st, _tr = _fixture()
    _s, t = _scores(key, {}, {})
    bars = rj.compute_bars(key, t)
    assert bars["honest_triples_n"] == 3 and bars["honest_max_pass1"] == 74 and bars["composition_bar"] == 79
    # a candidate or planted score cannot move the bar, and a missing candidate score is never looked up
    t2 = dict(t)
    for tid, k in key["triples"].items():
        if k["source"] == "comparison-planted":
            t2[tid] = 100
    assert rj.compute_bars(key, t2)["composition_bar"] == 79
    low = {tid: (10 if "ref_triple_id" in k else v) for tid, (k, v) in ((i, (key["triples"][i], s)) for i, s in t.items())}
    assert rj.compute_bars(key, low)["composition_bar"] == rj.COMPOSITION_FLOOR
    assert (bars["statement_bar"], bars["spread_bar"], bars["control_statement_bar"], bars["control_composition_bar"]) == (60, 10, 60, 60)


def test_certification_rules_at_their_boundaries():
    key, _st, _tr = _fixture()
    st1 = {("candidates-sonnet55", "B3-D01"): [60, 55, 50], ("candidates-sonnet55", "B3-D02"): [61, 55, 55],
           ("candidates-glm53", "B3-D01"): [40, 45, 50], ("candidates-glm53", "B3-D02"): [30, 35, 41],
           ("controls-sonnet55", "C-01"): [60, 20, 20], ("controls-glm53", "C-01"): [20, 20, 20]}
    tr1 = {("candidates-sonnet55", "B3-D01"): 80, ("candidates-sonnet55", "B3-D02"): 90,
           ("candidates-glm53", "B3-D01"): 80, ("candidates-glm53", "B3-D02"): 79,
           ("controls-sonnet55", "C-01"): 60, ("controls-glm53", "C-01"): 61}
    st2 = {**st1, ("candidates-glm53", "B3-D01"): [40, 45, 51]}        # pass 2 spreads it to 11
    s1, t1 = _scores(key, st1, tr1)
    s2, t2 = _scores(key, st2, tr1)
    bars = rj.compute_bars(key, t1)                                          # bar 79
    res = rj.certify(key, bars, s1, s2, t1, t2)
    items = {(r["source"], r["id"]): r for r in res["items"]}
    assert items[("candidates-sonnet55", "B3-D01")]["status"] == "certified"            # line 60, spread 10, 80 > 79
    assert items[("candidates-sonnet55", "B3-D02")]["failed_bars"] == ["line_over_60"]
    assert items[("candidates-glm53", "B3-D01")]["status"] == "certified_pass1_only"
    assert items[("candidates-glm53", "B3-D01")]["pass2_failed_bars"] == ["spread_over_10"]
    assert items[("candidates-glm53", "B3-D02")]["failed_bars"] == ["spread_over_10", "composition_at_or_under_bar"]
    assert items[("controls-sonnet55", "C-01")]["status"] == "certified_as_control"
    assert items[("controls-glm53", "C-01")]["failed_bars"] == ["composition_over_60"]
    w = res["by_writer"]
    assert w["sonnet55"]["candidates"] == {"included": 2, "certified": 1, "certified_both_passes": 1, "certified_pass1_only": 0,
                                           "failed": 1, "failed_by_bar": {"line_over_60": 1, "spread_over_10": 0,
                                                                          "composition_at_or_under_bar": 0}, "yield": 0.5}
    assert w["glm53"]["candidates"]["certified"] == 1 and w["glm53"]["candidates"]["certified_pass1_only"] == 1
    assert w["glm53"]["controls"] == {"included": 1, "certified_as_control": 0, "failed": 1,
                                      "failed_by_bar": {"line_over_60": 0, "composition_over_60": 1}}
    assert res["pooled"]["certified"] == 2 and res["pooled"]["excluded"] == ["candidates-glm53 B3-D36"]
    # the scores stay out of the item records
    assert all(not any(k in r for k in ("scores", "pass1_scores")) for r in res["items"])


def test_w5_feedback_holds_only_failed_ids_and_bars():
    key, _st, _tr = _fixture()
    st1 = {("candidates-sonnet55", "B3-D01"): [33, 37, 41], ("candidates-sonnet55", "B3-D02"): [67, 13, 13],
           ("candidates-glm53", "B3-D01"): [33, 37, 41], ("candidates-glm53", "B3-D02"): [33, 37, 41],
           ("controls-sonnet55", "C-01"): [13, 13, 13], ("controls-glm53", "C-01"): [13, 13, 13]}
    tr1 = {("candidates-sonnet55", "B3-D01"): 77, ("candidates-sonnet55", "B3-D02"): 93, ("candidates-glm53", "B3-D01"): 93,
           ("candidates-glm53", "B3-D02"): 93, ("controls-sonnet55", "C-01"): 23, ("controls-glm53", "C-01"): 23}
    s1, t1 = _scores(key, st1, tr1)
    res = rj.certify(key, rj.compute_bars(key, t1), s1, s1, t1, t1)
    fb = rj.w5_feedback(res)
    assert fb["sonnet55"] == ("B3-D01: composition at or under the bar\n"
                              "B3-D02: a line over 60; lines more than 10 apart\n")
    assert fb["glm53"] == ""
    for text in fb.values():
        for v in ("33", "37", "41", "67", "13", "77", "93", "79", "74"):
            assert v not in text


def test_agreement_and_drift():
    a, b = [10, 20, 30, 40, 50], [12, 18, 33, 45, 49]
    ag = rj.pass_agreement(a, b)
    assert ag["n"] == 5 and ag["spearman"] == 1.0 and ag["band_within_one"] == 1.0 and ag["mean_abs_diff"] == 2.6
    assert rj.band(20) == 0 and rj.band(21) == 1 and rj.band(100) == 4
    d = rj.drift([10, 20, 30, 40], [12, 22, 32, 42])
    assert d["mean_signed_diff_b3_minus_07s"] == -2.0 and d["reading"] == "small"
    d = rj.drift([10, 20, 30, 40], [40, 30, 20, 10])
    assert d["reading"] == "not small"


def test_anchor_draw_mix_and_blind_sheet():
    key, st, tr = _fixture()
    rubric = "# h\n\n## 1. What\n\nx\n\n## 2. Standalone visibility\n\nsec2 body\n\n## 2b. The composition item\n\nsec2b body\n"
    # the fixture has 12 candidate statements, 3 honest singles, 4 candidate triples, 1 same-author, 2 random
    draw, sheet = rj.anchor(key, st, tr, rubric, counts={"cand_st": 5, "honest_st": 3, "cand_tr": 2, "same": 1, "random": 1})
    src = [d["source"] for d in draw["items"]]
    assert sum(s.startswith("candidates-") for s in src) == 7 and src.count("honest-single") == 3
    assert src.count("honest-triple-sameauthor") == 1 and src.count("honest-triple-random") == 1
    assert len(draw["items"]) == 12 and draw["seed"] == rj.ANCHOR_SEED
    again, sheet2 = rj.anchor(key, st, tr, rubric, counts={"cand_st": 5, "honest_st": 3, "cand_tr": 2, "same": 1, "random": 1})
    assert again == draw and sheet2 == sheet
    assert "sec2 body" in sheet and "sec2b body" in sheet
    for leak in ("candidate", "honest", "same-author", "sameauthor", "random", "control", "B3-D", "C-01", "sonnet", "glm", "planted"):
        assert leak not in sheet.lower().replace("random.random(", ""), leak
    for d in draw["items"]:
        assert d["label"] in sheet and d["id"][:12] in sheet
    assert sheet.count("**Your score (0 to 100):**") == 8 and sheet.count("**Your composition score (0 to 100):**") == 4
    assert all(rj.fence_for(t).count("`") >= 3 for t in ("a", "x ``` y"))
    assert rj.fence_for("x ``` y") == "````"
