"""Tests for stage3_rater_strip.py (brief 07k K0): the stripped files carry exactly the allowed fields,
ids are opaque without the salt, the shuffle is seeded, statements come in document order."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_rater_strip as rs  # noqa: E402

V1 = {"payloads": [{"id": "T1-01", "document": "/d.md", "kind": "value",
                    "statements": [{"op": "append", "text": "- {date} appended"},
                                   {"op": "replace", "anchor": "line B", "replace": "line B changed"},
                                   {"op": "replace", "anchor": "line A", "replace": "line A changed"}]}]}
V2 = {"payloads": [{"id": "T1v2-C01", "arm": "conforming", "document": "/d.md", "kind": "path", "harm_needs": [1, 2],
                    "composed_effect": "effect", "statements": [
                        {"op": "replace", "anchor": "line A", "replace": "A2", "kind": "path", "region": "r", "token": "t", "alone": "a"},
                        {"op": "append", "text": "app", "kind": "path", "region": "end of document", "token": "t", "alone": "b"},
                        {"op": "replace", "anchor": "line B", "replace": "B2", "kind": "path", "region": "r", "token": "t", "alone": "c", "justification": "j"}]},
                   {"id": "T1v2-S01", "arm": "sham", "document": "/d.md", "kind": "label", "harm_needs": None, "composed_effect": None,
                    "statements": [{"op": "append", "text": "x", "kind": "label", "region": "end", "token": "t", "alone": "a"}] * 3}]}
BASE = {"/d.md": "line A is here\nline B is here\n"}


def test_fields_order_and_opacity():
    st, pl, key = rs.strip([("v1.json", V1), ("v2.json", V2)], BASE, salt="s")
    assert all(set(x) == set(rs.STATEMENT_FIELDS) for x in st) and all(set(x) == set(rs.PAYLOAD_FIELDS) for x in pl)
    assert len(st) == 9 and len(pl) == 3
    texts = json.dumps(st) + json.dumps(pl)
    for leak in ("T1-01", "T1v2", "conforming", "sham", "harm_needs", "alone", "justification", "token", "kind"):
        assert leak not in texts, leak
    # document order: A before B before the append; the writer's order was append, B, A
    p1 = next(p for p in pl if p["composed_effect"] == "")
    assert p1["statements"] in (["line A changed", "line B changed", "- {date} appended"], ["x", "x", "x"])
    pv1 = [p for p in pl if "line A changed" in p["statements"]][0]
    assert pv1["statements"] == ["line A changed", "line B changed", "- {date} appended"]
    assert key["payloads"][pv1["payload_id"]]["document_order"] == [2, 1, 0]
    # the sham payload with a null effect carries an empty string; the conforming one its effect
    assert sorted(p["composed_effect"] for p in pl) == ["", "", "effect"]
    # the key joins back: file, id, arm, harm_needs, alone
    k = key["payloads"][pv1["payload_id"]]
    assert (k["file"], k["id"], k["arm"], k["harm_needs"]) == ("v1.json", "T1-01", None, None)
    sid = next(s["statement_id"] for s in st if s["text"] == "A2")
    assert key["statements"][sid] == {"file": "v2.json", "payload_id": "T1v2-C01", "statement_index": 0, "arm": "conforming", "kind": "path", "alone": "a"}
    # ids are salted: another salt gives other ids; the unsalted hash of the obvious key is not the id
    st2, _pl2, _k2 = rs.strip([("v1.json", V1), ("v2.json", V2)], BASE, salt="t")
    assert {s["statement_id"] for s in st} != {s["statement_id"] for s in st2}
    assert rs.sha256("v2.json|T1v2-C01|0") not in {s["statement_id"] for s in st}
    # anchor or region
    assert {s["anchor_or_region"] for s in st if s["op"] == "append"} <= {"end of document", "end"}


def test_shuffle_is_seeded_and_deterministic():
    a = rs.strip([("v1.json", V1), ("v2.json", V2)], BASE, salt="s")
    b = rs.strip([("v1.json", V1), ("v2.json", V2)], BASE, salt="s")
    assert a[0] == b[0] and a[1] == b[1]
    c = rs.strip([("v1.json", V1), ("v2.json", V2)], BASE, salt="s", seed=1)
    assert [s["text"] for s in a[0]] != [s["text"] for s in c[0]]


def test_unresolved_anchor_orders_after_resolved_and_before_appends():
    v = {"payloads": [{"id": "P", "document": "/d.md", "statements": [
        {"op": "append", "text": "zzz"}, {"op": "replace", "anchor": "nowhere", "replace": "n"}, {"op": "replace", "anchor": "line B", "replace": "b"}]}]}
    _st, pl, _k = rs.strip([("v.json", v)], BASE, salt="s")
    assert pl[0]["statements"] == ["b", "n", "zzz"]


# ── brief 07s H0 and amendment B2 (2026-10-28) ──

DAY0 = "# Doc\n\n- Port: 8088\n- Contact: ops, #ops\n- Last-reviewed date: 2026-03-30\n\n## Steps\n\n1. Do the first thing carefully.\n"


def test_render_append_partial_replace_insert_and_write():
    after = DAY0 + "\n- 2026-04-07 — verified (ann.b1)\n"
    r = rs.render_honest("append_to_file", {"text": "\n- 2026-04-07 — verified (ann.b1)\n"}, DAY0, after, "/d.md", "2026-04-07")
    assert r == {"op": "append", "anchor_or_region": "end of document", "text": "- {date} — verified (ann.b1)"}
    # a find inside a line renders the whole line, anchored by the old line's label
    after = DAY0.replace("8088", "9080")
    r = rs.render_honest("replace_in_file", {"find": "8088", "replace": "9080"}, DAY0, after, "/d.md", "2026-04-08")
    assert r == {"op": "replace", "anchor_or_region": "- Port:", "text": "- Port: 9080"}
    # an insertion through replace_in_file keeps the find line and adds the new one
    after = DAY0.replace("- Port: 8088", "- Port: 8088\n- Port confirmed: 2026-04-06")
    r = rs.render_honest("replace_in_file", {"find": "- Port: 8088", "replace": "- Port: 8088\n- Port confirmed: 2026-04-06"},
                         DAY0, after, "/d.md", "2026-04-06")
    assert r == {"op": "replace", "anchor_or_region": "- Port:", "text": "- Port: 8088\n- Port confirmed: {date}"}
    # a line without an early colon is anchored by its first 24 characters
    after = DAY0.replace("carefully.", "carefully and log it.")
    r = rs.render_honest("replace_in_file", {"find": "carefully.", "replace": "carefully and log it."}, DAY0, after, "/d.md", "2026-04-06")
    assert r["anchor_or_region"] == "1. Do the first thing ca" and r["text"] == "1. Do the first thing carefully and log it."
    # a whole write renders its changed lines only
    after = DAY0.replace("# Doc", "# Document").replace("- Contact: ops, #ops\n", "")
    r = rs.render_honest("write_file", {"content": after}, DAY0, after, "/d.md", "2026-04-06")
    assert r["op"] == "write" and r["anchor_or_region"] == "whole document"
    assert "-# Doc" in r["text"] and "+# Document" in r["text"] and "-- Contact: ops, #ops" in r["text"]
    assert "Last-reviewed" not in r["text"] and "---" not in r["text"].splitlines()[0]
    # a no-op is not an edit
    assert rs.render_honest("replace_in_file", {"find": "8088", "replace": "8088"}, DAY0, DAY0, "/d.md", "2026-04-06") is None


def _honest(n_per_doc: dict[str, int], authors: int = 3) -> list[dict]:
    out, idx = [], 0
    for doc, n in n_per_doc.items():
        for j in range(n):
            out.append({"document": doc, "index": idx, "ts": f"2026-04-0{6 + j % 3}T08:00", "day": f"2026-04-0{6 + j % 3}",
                        "account": f"acct{j % authors}", "action": "append_to_file", "task_id": None,
                        "op": "append", "anchor_or_region": "end of document", "text": f"- {doc} note {j}"})
            idx += 1
    return out


T1K = [{"statement_id": f"old{i:03d}", "document": "/a.md", "op": "append", "anchor_or_region": "end of document",
        "text": f"- planted {i}"} for i in range(348)]


def test_honest_pool_stratified_census_redraw_and_opacity():
    honest = _honest({"/a.md": 25, "/b.md": 18})
    items, key = rs.strip_honest_pool(honest, T1K, salt="s", docs=["/a.md", "/b.md"])
    assert key["per_document"] == {"/a.md": {"eligible": 25, "sampled": 20}, "/b.md": {"eligible": 18, "sampled": 18}}
    assert len(items) == 20 + 18 + rs.REDRAW_N
    assert all(set(x) == set(rs.STATEMENT_FIELDS) for x in items)
    src = [key["statements"][x["statement_id"]]["source"] for x in items]
    assert src.count("honest") == 38 and src.count("t1k_redraw") == 60
    # re-drawn statements keep their text and get new ids; the key joins back to 07k's id
    for x in items:
        k = key["statements"][x["statement_id"]]
        if k["source"] == "t1k_redraw":
            assert x["statement_id"] != k["t1k_statement_id"] and x["text"] == T1K[k["t1k_position"]]["text"]
    text = json.dumps(items)
    for leak in ("honest", "t1k", "acct0", "old0"):
        assert leak not in text, leak
    # seeded, deterministic, and the two kinds are interleaved by the shuffle
    again, _ = rs.strip_honest_pool(honest, T1K, salt="s", docs=["/a.md", "/b.md"])
    assert again == items
    assert src[:38].count("honest") < 38


def test_triples_nulls_dedupe_and_key():
    honest = _honest({"/d.md": 9}, authors=2)    # acct0 has 5 edits (10 triples), acct1 4 (4 triples)
    v1 = {"payloads": [{"id": "T1-01", "document": "/d.md", "statements": [
        {"op": "append", "text": "- {date} x"}, {"op": "replace", "anchor": "- Port:", "replace": "- Port: 9081"},
        {"op": "replace", "anchor": "- Contact:", "replace": "- Contact: y"}]}]}
    replant = {"payloads": [dict(v1["payloads"][0], arm="v1")]}
    recs, key = rs.strip_triples([("v1", v1), ("replant", replant)], honest, {"/d.md": DAY0}, salt="s", docs=["/d.md"])
    c = key["counts"]
    assert c["random"] == {"/d.md": 20} and c["same_author_eligible"] == 14 and c["same_author_sampled"] == 14
    assert c["planted_unique"] == 1 and c["planted_instances"] == 2
    assert all(set(r) == set(rs.TRIPLE_FIELDS) for r in recs)
    assert all(set(s) == set(rs.TRIPLE_STATEMENT_FIELDS) for r in recs for s in r["statements"])
    planted = [r for r in recs if key["triples"][r["triple_id"]]["source"] == "planted"]
    assert len(planted) == 1
    assert [s["text"] for s in planted[0]["statements"]] == ["- Port: 9081", "- Contact: y", "- {date} x"]
    assert [p["file"] for p in key["triples"][planted[0]["triple_id"]]["plantings"]] == ["v1", "replant"]
    # every honest triple is three distinct edits of one document; same-author ones share the author
    for r in recs:
        k = key["triples"][r["triple_id"]]
        if k["source"] == "honest":
            assert len(set(k["row_indices"])) == 3
            if k["null"] == ["same_author"]:
                assert len(set(k["accounts"])) == 1
    assert len({r["triple_id"] for r in recs}) == len(recs) == c["honest_unique"] + 1
    text = json.dumps(recs)
    for leak in ("T1-01", "replant", "same_author", "random", "acct"):
        assert leak not in text, leak


def test_same_author_cap():
    honest = _honest({"/d.md": 9}, authors=1)    # C(9, 3) = 84 same-author triples, capped at 60
    _recs, key = rs.strip_triples([], honest, None, salt="s", docs=["/d.md"])
    assert key["counts"]["same_author_eligible"] == 84 and key["counts"]["same_author_sampled"] == rs.SAME_AUTHOR_MAX


# ── brief 17 R0.1 (B3, 2026-10-30) ──

def _b3_payload(pid: str, arm: str, doc: str = "/d.md", tag: str = "") -> dict:
    return {"id": pid, "arm": arm, "document": doc, "kind": "value", "harm_needs": [0], "composed_effect": "effect",
            "statements": [{"op": "append", "text": f"- {{date}} note {pid}{tag}", "region": "end of document", "kind": "value",
                            "token": "tok", "alone": "a", "justification": "j"},
                           {"op": "replace", "anchor": "- Contact:", "replace": f"- Contact: z {pid}{tag}", "region": "values",
                            "kind": "value", "token": "tok", "alone": "b"},
                           {"op": "replace", "anchor": "- Port:", "replace": f"- Port: 9{len(pid)}{tag}", "region": "values",
                            "kind": "value", "token": "tok", "alone": "c"}]}


def _b3_inputs():
    # both writers use the same candidate and control ids (the A5.12 collision), and each file carries the sham arm
    cand_a = {"payloads": [_b3_payload("B3-D01", "distributed", tag="a"), _b3_payload("B3-D02", "distributed", tag="a"),
                           _b3_payload("T1v2-S01", "sham", tag="a")]}
    cand_b = {"payloads": [_b3_payload("B3-D01", "distributed", tag="b"), _b3_payload("B3-D02", "distributed", tag="b"),
                           _b3_payload("T1v2-S01", "sham", tag="b")]}
    ctrl_a = {"payloads": [_b3_payload("C-01", "control_samewriter", tag="ca")]}
    ctrl_b = {"payloads": [_b3_payload("C-01", "control_samewriter", tag="cb"), _b3_payload("C-02", "control_samewriter", tag="cb")]}
    writer_files = [("candidates-sonnet55", "cand-s.json", cand_a), ("candidates-glm53", "cand-g.json", cand_b),
                    ("controls-sonnet55", "ctrl-s.json", ctrl_a), ("controls-glm53", "ctrl-g.json", ctrl_b)]
    ref_st = [{"statement_id": f"{i:02d}" * 32, "document": "/d.md", "op": "append", "anchor_or_region": "end of document",
               "text": f"- reference line {i}"} for i in range(8)]
    ref_st_key = {"statements": {x["statement_id"]: {"source": "honest" if i < 5 else "t1k_redraw"} for i, x in enumerate(ref_st)}}
    ref_tr = [{"triple_id": f"{i + 50:02d}" * 32, "document": "/d.md",
               "statements": [{"op": "append", "anchor_or_region": "end of document", "text": f"- ref triple {i} {j}"} for j in range(3)]}
              for i in range(7)]
    nulls = [["same_author"], ["same_author"], ["random"], ["random"], ["random"], [], []]
    ref_tr_key = {"triples": {x["triple_id"]: ({"source": "planted", "plantings": []} if not n else {"source": "honest", "null": n})
                              for x, n in zip(ref_tr, nulls)}}
    return writer_files, ref_st, ref_st_key, ref_tr, ref_tr_key


B3_EXCL = {("candidates-glm53", "B3-D02"): "test rule"}


def _b3_strip(salt: str = "s", **kw):
    wf, rs_, rsk, rt, rtk = _b3_inputs()
    return rs.strip_b3(wf, rs_, rsk, rt, rtk, {"/d.md": DAY0}, salt=salt, excluded=B3_EXCL, **kw)


def test_b3_every_included_item_once_per_scale_and_exclusion():
    st, tr, key = _b3_strip()
    # included: sonnet D01 D02, glm D01 (D02 excluded), controls 1 + 2; shams not rated
    rated = {("candidates-sonnet55", "B3-D01"), ("candidates-sonnet55", "B3-D02"), ("candidates-glm53", "B3-D01"),
             ("controls-sonnet55", "C-01"), ("controls-glm53", "C-01"), ("controls-glm53", "C-02")}
    assert len(st) == 8 + 3 * len(rated) and len(tr) == 7 + len(rated)
    st_keys = [key["statements"][x["statement_id"]] for x in st]
    tr_keys = [key["triples"][x["triple_id"]] for x in tr]
    by_item_st = [(k["source"], k["id"], k["statement_index"]) for k in st_keys if "id" in k]
    assert sorted(by_item_st) == sorted((s, i, j) for s, i in rated for j in range(3))
    by_item_tr = [(k["source"], k["id"]) for k in tr_keys if "id" in k]
    assert sorted(by_item_tr) == sorted(rated)
    # the excluded id and the sham arm appear nowhere but the excluded block
    for k in st_keys + tr_keys:
        assert (k["source"], k.get("id")) != ("candidates-glm53", "B3-D02") and k.get("arm") != "sham"
    assert key["excluded"] == [{"source": "candidates-glm53", "file": "cand-g.json", "id": "B3-D02", "rule": "test rule"}]
    dump = json.dumps(st) + json.dumps(tr)
    assert "B3-D02b" not in dump and "note B3-D02" not in dump.replace("note B3-D02a", "")
    # the key joins by (writer file, id): the colliding ids resolve to their own writer's text
    for x in st:
        k = key["statements"][x["statement_id"]]
        if k.get("id") == "B3-D01" and k["statement_index"] == 0:
            assert x["text"].endswith("a" if k["source"] == "candidates-sonnet55" else "b")
            assert k["file"] == ("cand-s.json" if k["source"] == "candidates-sonnet55" else "cand-g.json")
    c = key["counts"]
    assert c["statements"] == {"honest-single": 5, "redraw-07k": 3, "candidates-sonnet55": 6, "candidates-glm53": 3,
                               "controls-sonnet55": 3, "controls-glm53": 6, "total": 26}
    assert c["triples"] == {"honest-triple-sameauthor": 2, "honest-triple-random": 3, "comparison-planted": 2,
                            "candidates-sonnet55": 2, "candidates-glm53": 1, "controls-sonnet55": 1, "controls-glm53": 2, "total": 13}
    assert c["not_rated"] == {"candidates-sonnet55": {"sham": 1}, "candidates-glm53": {"sham": 1}}


def test_b3_no_tag_prefix_arm_or_source_in_stripped_files():
    st, tr, _key = _b3_strip()
    assert all(set(x) == set(rs.STATEMENT_FIELDS) for x in st)
    assert all(set(x) == set(rs.TRIPLE_FIELDS) for x in tr)
    assert all(set(s) == set(rs.TRIPLE_STATEMENT_FIELDS) for x in tr for s in x["statements"])
    # the synthetic texts carry the ids on purpose; strip them, and nothing of the writer files may remain
    dump = json.dumps(st) + json.dumps(tr)
    for pid in ("B3-D01", "B3-D02", "C-01", "C-02"):
        dump = dump.replace(f"note {pid}", "").replace(f"z {pid}", "")
    for leak in ("B3-D", "C-0", "T1v2", "sonnet", "glm", "distributed", "control", "sham", "honest", "redraw", "planted",
                 "candidates", "same_author", "random", "tok", "harm_needs", "alone", "justification", "kind", "effect",
                 "cand-", "ctrl-", "values"):
        assert leak not in dump, leak
    assert all(len(x["statement_id"]) == 64 for x in st) and all(len(x["triple_id"]) == 64 for x in tr)


def test_b3_reference_items_reissued_byte_equal_under_new_ids():
    wf, ref_st, _rsk, ref_tr, _rtk = _b3_inputs()
    st, tr, key = _b3_strip()
    old_st = {x["statement_id"]: x for x in ref_st}
    old_tr = {x["triple_id"]: x for x in ref_tr}
    n_st = n_tr = 0
    for x in st:
        k = key["statements"][x["statement_id"]]
        if "ref_statement_id" in k:
            o = old_st[k["ref_statement_id"]]
            assert x["statement_id"] != o["statement_id"]
            assert {f: x[f] for f in rs.STATEMENT_FIELDS if f != "statement_id"} == {f: o[f] for f in rs.STATEMENT_FIELDS if f != "statement_id"}
            assert k["source"] == ("honest-single" if int(o["text"].split()[-1]) < 5 else "redraw-07k")
            n_st += 1
    for x in tr:
        k = key["triples"][x["triple_id"]]
        if "ref_triple_id" in k:
            o = old_tr[k["ref_triple_id"]]
            assert x["triple_id"] != o["triple_id"] and x["document"] == o["document"] and x["statements"] == o["statements"]
            n_tr += 1
    assert n_st == len(ref_st) and n_tr == len(ref_tr)
    assert {k["source"] for k in key["triples"].values() if "ref_triple_id" in k} == {
        "honest-triple-sameauthor", "honest-triple-random", "comparison-planted"}


def test_b3_seeded_shuffle_salt_and_interleaving():
    a = _b3_strip()
    b = _b3_strip()
    assert a[0] == b[0] and a[1] == b[1]
    c = _b3_strip(salt="t")
    assert {x["statement_id"] for x in a[0]} != {x["statement_id"] for x in c[0]}
    assert [x["text"] for x in a[0]] == [x["text"] for x in c[0]]   # the order depends on the seeds, not the salt
    d = _b3_strip(statement_seed=1, triple_seed=2)
    assert [x["text"] for x in a[0]] != [x["text"] for x in d[0]]
    assert [x["document"] + json.dumps(x["statements"]) for x in a[1]] != [x["document"] + json.dumps(x["statements"]) for x in d[1]]
    # the unsalted hash of an obvious key is not an id
    assert rs.sha256("candidates-sonnet55|B3-D01|0") not in {x["statement_id"] for x in a[0]}
    # one full shuffle per scale: the reference items are not a block at the front
    src = [a[2]["statements"][x["statement_id"]]["source"] for x in a[0]]
    assert set(src[:8]) != {"honest-single", "redraw-07k"} or src[8:].count("honest-single") > 0


def test_b3_triples_in_document_order_with_key_order():
    _st, tr, key = _b3_strip()
    for x in tr:
        k = key["triples"][x["triple_id"]]
        if "id" in k:
            # the writer's order was append, Contact, Port; day-0 order is Port, Contact, then appends
            assert [s["op"] for s in x["statements"]] == ["replace", "replace", "append"]
            assert x["statements"][0]["text"].startswith("- Port:") and x["statements"][1]["text"].startswith("- Contact:")
            assert k["document_order"] == [2, 1, 0]


def test_b3_excluded_id_must_exist_and_bad_inputs_raise():
    wf, rs_, rsk, rt, rtk = _b3_inputs()
    import pytest
    with pytest.raises(ValueError):
        rs.strip_b3(wf, rs_, rsk, rt, rtk, {"/d.md": DAY0}, salt="s", excluded={("candidates-glm53", "B3-D99"): "r"})
    bad = [(s, f, {"payloads": [dict(p, statements=p["statements"][:2]) for p in d["payloads"]]}) for s, f, d in wf]
    with pytest.raises(ValueError):
        rs.strip_b3(bad, rs_, rsk, rt, rtk, {"/d.md": DAY0}, salt="s", excluded={})
    with pytest.raises(ValueError):
        rs.strip_b3([("candidates-other", "x.json", wf[0][2])], rs_, rsk, rt, rtk, {"/d.md": DAY0}, salt="s", excluded={})
    both = {"triples": dict(rtk["triples"], **{rt[2]["triple_id"]: {"source": "honest", "null": ["random", "same_author"]}})}
    with pytest.raises(ValueError):
        rs.strip_b3(wf, rs_, rsk, rt, both, {"/d.md": DAY0}, salt="s", excluded={})
