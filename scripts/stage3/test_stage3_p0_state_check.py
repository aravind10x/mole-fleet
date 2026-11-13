"""Offline tests for stage3_p0_state_check (line P0, Part 1): which order the live world applied writes in, and
whether a recorded state existed. Synthetic ownCloud logs only."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p0_state_check as sc  # noqa: E402

P = "/shared/ops/doc.md"
BASE = {("owncloud", P): "a\n"}


def w(i, ts, real, content=None, append=None, find=None, replace=None, content_after=None):
    """As in the real log, every ownCloud write row carries the document's full content after the write."""
    if content is not None:
        return {"service": "owncloud", "action": "write_file", "args": {"path": P, "content": content}, "ts": ts, "real_ts": real, "exit_code": 0, "event_id": f"e{i}"}
    if append is not None:
        return {"service": "owncloud", "action": "append_to_file", "args": {"path": P, "content": content_after}, "ts": ts, "real_ts": real,
                "exit_code": 0, "event_id": f"e{i}"}
    return {"service": "owncloud", "action": "replace_in_file", "args": {"path": P, "find": find, "replace": replace, "content": content_after},
            "ts": ts, "real_ts": real, "exit_code": 0, "event_id": f"e{i}"}


def read(i, ts, real, nbytes):
    return {"service": "owncloud", "action": "read_file", "args": {"path": P}, "ts": ts, "real_ts": real, "bytes": nbytes, "exit_code": 0, "event_id": f"e{i}"}


# The file (= execution) order: append "b", then a replace of "b" -> "c" whose simulated ts is EARLIER than the append's.
ROWS = [w(0, "2026-04-06T10:00:00Z", 1.0, append="b\n", content_after="a\nb\n"),
        read(1, "2026-04-06T10:05:00Z", 2.0, len("a\nb\n")),
        w(2, "2026-04-06T09:00:00Z", 3.0, find="b", replace="c", content_after="a\nc\n"),
        read(3, "2026-04-06T11:00:00Z", 4.0, len("a\nc\n"))]


def test_orders():
    o = sc.orders(ROWS)
    assert o["file"] == [0, 1, 2, 3] and o["ts"] == [2, 0, 1, 3] and o["real_ts"] == [0, 1, 2, 3]


def test_event_consistency_picks_the_live_order():
    c = sc.event_consistency(ROWS, [P], BASE)
    assert c["file"] == {"reads": 2, "read_bytes_match": 2, "replaces": 1, "replace_find_present": 1}
    assert c["ts"]["replace_find_present"] == 0            # in simulated-time order the replace runs before "b" exists
    assert c["real_ts"] == c["file"]


def test_state_in_each_order():
    assert sc.state(ROWS, sc.orders(ROWS)["file"], P, BASE) == "a\nc\n"
    assert sc.state(ROWS, sc.orders(ROWS)["ts"], P, BASE) == "a\nb\n"


def test_a_ts_bounded_state_is_live_only_if_it_is_a_file_prefix():
    # bound 09:30: only the replace (ts 09:00) qualifies, but in file order it came after the append (ts 10:00)
    live = sc.live_state(ROWS, P, "2026-04-06T09:30:00Z", BASE)
    assert live["prefix"] is False and live["n_selected"] == 1 and live["n_excluded_before_last"] == 1
    assert live["content_equals_prefix"] is True       # with full-content writes, the selected state is a real write's own state
    full = sc.live_state(ROWS, P, "2026-04-06", BASE)        # the day end: every write qualifies
    assert full["prefix"] is True and full["content_equals_prefix"] is True


def test_compare_orders_at_a_bound():
    assert sc.compare_at(ROWS, P, "2026-04-06T09:30:00Z", BASE) == {"differs": False, "line_set_differs": False}   # one write selected
    d = sc.compare_at(ROWS, P, "2026-04-06", BASE)          # both writes: file order ends on the replace, time order on the append
    assert d == {"differs": True, "line_set_differs": True}
    assert sc.compare_at(ROWS, P, "2026-04-06T08:00:00Z", BASE) == {"differs": False, "line_set_differs": False}


def test_plant_fields_are_whitelisted():
    rec = {"payload_id": "X", "arm": "lone", "regime": "middle", "document": P, "pre_window_boundary": "day0",
           "composition_ts": "t", "composition_day": "d", "composed": True, "delivered": True, "planted_rows": [{"text": "secret"}]}
    assert sc.plant_fields(rec) == {k: rec[k] for k in sc.PLANT_FIELDS}
    assert "planted_rows" not in sc.plant_fields(rec)
