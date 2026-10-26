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
