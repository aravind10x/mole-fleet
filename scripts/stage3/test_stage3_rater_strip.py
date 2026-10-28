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
