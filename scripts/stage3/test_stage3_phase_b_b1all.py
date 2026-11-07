"""Tests for stage3_phase_b_b1all.py: synthetic only (the renderer tests' two-edit document and invented tasks)."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_phase_b_b1all as b1a  # noqa: E402
import stage3_phase_b_grounded as g  # noqa: E402
import test_stage3_phase_b_grounded as t  # noqa: E402

FEEDS = {"s1": [t.T_FREE, t.T_WRITE_PORT], "s2": [g.TaskInfo("Tidy /work/bob-kay/notes.md for ann.lee. Then stop.")]}


def edits():
    e1 = g.Edit("ann.lee", "2030-01-01T09:00:00Z", t.PATH, frozenset({"Port"}), t.T_WRITE_PORT, "s1|2")
    e2 = g.Edit("bob.kay", "2030-01-02T10:30:00Z", t.PATH, frozenset(), FEEDS["s2"][0], "s2|1")
    e3 = g.Edit("cy.do", "2030-01-02T11:00:00Z", t.PATH, frozenset(), None, "s3|0")
    return [e1, e2, e3]


def test_b1all_lists_every_fed_item_scrubbed_and_ends_with_the_task_in_force():
    e1, e2, e3 = edits()
    assert b1a.suffix(e1, FEEDS, t.ROSTER) == b1a.LEAD + g.fold(t.T_FREE.text) + b1a.SEP + g.fold(t.T_WRITE_PORT.text)
    assert b1a.suffix(e3, FEEDS, t.ROSTER) == "; no task in force"
    s2 = b1a.suffix(e2, FEEDS, t.ROSTER)
    assert "bob-kay" not in s2 and "ann.lee" not in s2 and "/work/<workspace>/notes.md" in s2 and "<account>" in s2
    assert all(b1a.last_is_in_force(FEEDS, e) for e in (e1, e2, e3))


def test_b1all_packet_is_b0_plus_one_header_block_naming_no_account():
    _rows, _base, units = t.synthetic_units()
    u = units[1]
    text = u["packet"].split("chars):\n", 1)[1]
    out = g.render_packets(t.PATH, u["boundary"], u["write_ts"], text, edits(), t.POOL, roster=t.ROSTER)
    pk = b1a.packet(t.PATH, u["boundary"], u["write_ts"], text, edits(), FEEDS, roster=t.ROSTER)
    head = g.sealed_head(t.PATH, u["boundary"], u["write_ts"])
    tail = out["B0"]["packet"][len(head):]
    assert pk["packet"].startswith(head) and pk["packet"].endswith(tail)
    block = pk["packet"][len(head): len(pk["packet"]) - len(tail)].splitlines()
    assert block[0] == g.HEADER_TITLE.format(n=3) and all(ln.startswith("- 2030-") for ln in block[1:])
    b1_block = out["B1"]["packet"][len(head): len(out["B1"]["packet"]) - len(tail)].splitlines()
    assert block[0] == b1_block[0]
    for a in ("ann.lee", "ann-lee", "bob.kay", "bob-kay", "cy.do", "cy-do"):
        assert a not in "\n".join(block[1:])
    assert pk["over_cap"] is False
