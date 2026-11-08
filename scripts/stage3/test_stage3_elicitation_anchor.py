"""Tests for stage3_elicitation_anchor.py (brief 30 Part 3, protocol section 9: the human anchor). Invented items and documents only."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_anchor as an  # noqa: E402
import stage3_legibility as lg  # noqa: E402

DOC = "/shared/x/guide.md"
DAY0 = {DOC: "# Guide\nline one of the invented guide\nline two of the invented guide\n"}


def _item(uid, cls, writer="wa", rnd=1):
    return {"uid": uid, "writer": writer, "round": rnd, "item_id": uid.split(":")[-1], "class": cls, "document": DOC, "mechanism": "invented-mech",
            "statements": [{"op": "replace", "anchor_or_region": "line one of the inv", "text": f"line one changed by {uid.split(':')[-1]} A"},
                           {"op": "append", "anchor_or_region": "end of document", "text": f"appended by {uid.split(':')[-1]} B"},
                           {"op": "append", "anchor_or_region": "end of document", "text": f"appended by {uid.split(':')[-1]} C"}]}


def _pool(n_cert=14, n_ill=3, n_mixed=6, n_part=9, n_loud=4, n_ne=2):
    out = []
    for cls, n in (("certified", n_cert), ("quiet_but_illegible", n_ill), ("mixed", n_mixed), ("part_derivable", n_part), ("loud", n_loud), ("not_evaluable", n_ne)):
        out += [_item(f"w:r1:{cls[:3]}{i:02d}", cls) for i in range(n)]
    return out


def test_eligible_are_the_items_that_pass_gate_i_and_are_classed():
    el = an.eligible(_pool())
    assert {i["class"] for i in el} == {"certified", "quiet_but_illegible", "mixed", "part_derivable"}
    assert len(el) == 14 + 3 + 6 + 9


def test_draw_takes_ten_certified_and_ten_of_the_others_by_the_seeded_rule():
    d = an.draw(_pool(), seed=20261211, size=20)
    by = {i["uid"]: i for i in _pool()}
    cls = [by[u]["class"] for u in d["order"]]
    assert len(d["order"]) == 20 and len(set(d["order"])) == 20
    assert sum(c == "certified" for c in cls) == 10 and sum(c in ("quiet_but_illegible", "mixed", "part_derivable") for c in cls) == 10
    assert not any(c in ("loud", "not_evaluable") for c in cls)


def test_draw_is_deterministic_by_seed_and_does_not_depend_on_the_input_order():
    a = an.draw(_pool(), seed=20261211, size=20)
    b = an.draw(list(reversed(_pool())), seed=20261211, size=20)
    c = an.draw(_pool(), seed=1, size=20)
    assert a == b and a != c


def test_draw_follows_the_documented_random_sequence():
    items = an.eligible(_pool())
    cert = sorted(i["uid"] for i in items if i["class"] == "certified")
    other = sorted(i["uid"] for i in items if i["class"] != "certified")
    rng = random.Random(20261211)
    pc, po = rng.sample(cert, 10), rng.sample(other, 10)
    order = pc + po
    rng.shuffle(order)
    parts = {u: rng.randrange(3) for u in order}
    order_b = list(order)
    rng.shuffle(order_b)
    d = an.draw(_pool(), seed=20261211, size=20)
    assert d["order"] == order and d["part"] == parts and d["order_b"] == order_b


def test_draw_takes_all_certified_when_fewer_than_ten_exist_and_fills_from_the_others():
    d = an.draw(_pool(n_cert=6), seed=20261211, size=20)
    by = {i["uid"]: i for i in _pool(n_cert=6)}
    cls = [by[u]["class"] for u in d["order"]]
    assert sum(c == "certified" for c in cls) == 6 and len(cls) == 20


def test_draw_gives_each_item_one_part_of_the_three_and_a_second_order_of_the_same_items():
    d = an.draw(_pool(), seed=20261211, size=20)
    assert set(d["part"]) == set(d["order"]) and set(d["part"].values()) <= {0, 1, 2}
    assert sorted(d["order_b"]) == sorted(d["order"])


def test_sheet_shows_the_whole_and_then_in_a_second_block_the_part_with_the_fixed_question_and_no_class():
    pool = _pool()
    items = {i["uid"]: i for i in pool}
    d = an.draw(pool, seed=20261211, size=20)
    sheet = an.render_sheet(d, items, DAY0, "test-salt")
    assert sheet.count(lg.QUESTION) == 40
    assert sheet.index("Block A") < sheet.index("Block B")
    first = d["order"][0]
    whole = lg.reader_packet(DOC, DAY0[DOC], items[first]["statements"])
    part = lg.reader_packet(DOC, DAY0[DOC], [items[first]["statements"][d["part"][first]]])
    assert whole.strip() in sheet and part.strip() in sheet
    for word in ("certified", "illegible", "mixed", "part_derivable", "loud", "invented-mech"):
        assert word not in sheet
    assert "w:r1" not in sheet                                  # the ids on the sheet are opaque


def test_sheet_ids_are_opaque_and_unique_and_the_key_maps_them_back():
    pool = _pool()
    d = an.draw(pool, seed=20261211, size=20)
    key = an.make_key(d, {i["uid"]: i for i in pool}, "test-salt")
    assert len(set(key["sheet_ids"].values())) == 20
    assert set(key["sheet_ids"]) == set(d["order"])
    row = key["items"][d["order"][0]]
    assert set(row) >= {"sheet_id", "writer", "round", "item_id", "class", "mechanism", "part_index"}


def test_counts_report_the_draw_by_class_and_writer_without_ids():
    pool = _pool()
    d = an.draw(pool, seed=20261211, size=20)
    c = an.draw_counts(d, {i["uid"]: i for i in pool})
    assert sum(c["by_class"].values()) == 20 and c["by_class"]["certified"] == 10
    assert sum(c["by_writer"].values()) == 20 and "w:r1" not in json.dumps(c)


def test_part_label_names_the_statement_by_its_position_not_its_text():
    assert an.part_label(0) == "the first edit" and an.part_label(2) == "the third edit"


def test_sheet_ids_depend_on_the_salt_so_the_records_alone_do_not_give_them():
    assert an.sheet_id("salt-a", "w:r1:abc") != an.sheet_id("salt-b", "w:r1:abc")
    assert an.sheet_id("salt-a", "w:r1:abc") == an.sheet_id("salt-a", "w:r1:abc")
    assert an.sheet_id("salt-a", "w:r1:abc").startswith("H") and len(an.sheet_id("salt-a", "w:r1:abc")) == 7
