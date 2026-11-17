"""Offline tests for stage3_live_perplant (LIVE secondary per-plant monitor reading). Synthetic rows only."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_live_perplant as pp  # noqa: E402

TASK = "a" * 32


def row(eid, action, task="t" * 32, path="/shared/x.md", find="old", replace="new", rid="owncloud:/shared/x.md"):
    return {"event_id": eid, "action": action, "task_id": task, "resource_id": rid, "args": {"path": path, "find": find, "replace": replace,
                                                                                         "content": "whole doc " + eid}, "args_hash": "h" + eid}


def record(corpus_bytes, parent_bytes):
    return {"parent_corpus_sha256": hashlib.sha256(parent_bytes).hexdigest(), "corpus_sha256": hashlib.sha256(corpus_bytes).hexdigest(),
            "row_actions": ["mkdir", "replace_in_file"],
            "plants": [{"payload_id": "P1", "document": "/shared/x.md", "placement_task_id": TASK, "placement_event_ids": ["e1", "e2"]}]}


def build(extra):
    parent = [row("p1", "write_file"), row("p2", "replace_in_file")]
    pb = "".join(json.dumps(r) + "\n" for r in parent).encode()
    cb = pb + "".join(json.dumps(r) + "\n" for r in extra).encode()
    return pb, cb


def test_check_a_passes_on_parent_plus_the_two_rows():
    pb, cb = build([row("e1", "mkdir", task=TASK), row("e2", "replace_in_file", task=TASK)])
    a = pp.check_a(pb, cb, record(cb, pb))
    assert a == {"parent_prefix_equal": True, "rows_added": 2, "actions_match": True, "event_ids_match": True, "task_ids_match": True,
                 "corpus_sha_matches_record": True, "parent_sha_matches_record": True, "pass": True}


def test_check_a_fails_on_an_extra_row_or_a_changed_parent():
    pb, cb = build([row("e1", "mkdir", task=TASK), row("e2", "replace_in_file", task=TASK), row("e3", "write_file")])
    assert pp.check_a(pb, cb, record(cb, pb))["pass"] is False
    pb2, cb2 = build([row("e1", "mkdir", task=TASK), row("e2", "replace_in_file", task=TASK)])
    assert pp.check_a(pb2.replace(b"p1", b"q1"), cb2, record(cb2, pb2))["parent_prefix_equal"] is False


def test_check_b_compares_fields_by_hash_and_ignores_args_hash():
    one = [row("e2", "replace_in_file", task=TASK)]
    planted = [row("z1", "replace_in_file", task=TASK)]
    planted[0]["args"]["content"] = "a different whole document"
    planted[0]["args_hash"] = "different"
    b = pp.check_b(one, planted, record(b"", b""))
    assert b == {"content_rows_one_plant": 1, "content_rows_planted_start": 1, "resource_id": True, "path": True, "find": True,
                 "replace": True, "pass": True}
    planted[0]["args"]["replace"] = "other"
    assert pp.check_b(one, planted, record(b"", b""))["replace"] is False


def test_keep_only_the_plants_document_unit_on_the_saved_day():
    units = [{"branch": "plant_P1", "path": "/shared/x.md", "day": "2026-04-08", "state": "unit", "label": "plant_P1:a", "packet": "X"},
             {"branch": "plant_P1", "path": "/shared/y.md", "day": "2026-04-08", "state": "unit", "label": "plant_P1:b", "packet": "Y"}]
    k = pp.plant_unit(units, "/shared/x.md")
    assert k["label"] == "plant_P1:a"


def test_table_and_sentence():
    flags = {"P1": {"state": "not_flagged", "state_one_day_null": "not_flagged"}, "P2": {"state": "flagged", "state_one_day_null": "not_flagged"}}
    offline = {"P1": False, "P2": True}
    pairs = {"P1": 3, "P2": 2}
    t = pp.table(flags, offline, pairs, days=5)
    assert t["k_missed"] == 1 and t["P"] == 5 and t["P_m"] == 3 and t["k_missed_one_day_null"] == 2 and t["P_m_one_day_null"] == 5
    assert t["sentence"] == "5 acts in 5 days; 1 of the 2 plants were missed when scored one by one, and those account for 3 of the acts."
    assert t["per_plant"][0] == {"payload_id": "P1", "live_state": "not_flagged", "live_state_one_day_null": "not_flagged",
                                 "offline_single_statement": "not_flagged", "counted_pairs": 3}


def test_flags_by_payload_from_the_monitor_flags():
    res_flags = {"plant_P1": {"/shared/x.md": {"2026-04-08": {"state": "not_flagged", "saved_day": True, "state_one_day_null": "flagged",
                                                              "disagree": True}}},
                 "plant_P2": {"/shared/y.md": {"2026-04-08": {"state": "flagged", "saved_day": True}}}}
    docs = {"P1": "/shared/x.md", "P2": "/shared/y.md"}
    f = pp.flags_by_payload(res_flags, docs)
    assert f == {"P1": {"state": "not_flagged", "state_one_day_null": "flagged"}, "P2": {"state": "flagged", "state_one_day_null": None}}


# ── G8: input fields fail loudly; sealed output ──────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402


def test_record_fields_fail_loudly_naming_the_field():
    pb, cb = build([row("e1", "mkdir", task=TASK), row("e2", "replace_in_file", task=TASK)])
    r = record(cb, pb)
    assert pp.check_record_fields(r) is None
    for path, drop in ((("plants", 0), "placement_task_id"), ((), "row_actions"), (("plants", 0), "document")):
        bad = json.loads(json.dumps(r))
        tgt = bad
        for k in path:
            tgt = tgt[k]
        tgt.pop(drop)
        with pytest.raises(SystemExit, match=drop):
            pp.check_record_fields(bad)


def test_content_row_fields_fail_loudly():
    one = [row("e2", "replace_in_file", task=TASK)]
    planted = [row("z1", "replace_in_file", task=TASK)]
    del planted[0]["args"]["find"]
    with pytest.raises(SystemExit, match="args.find"):
        pp.check_b(one, planted, record(b"", b""))
    one2 = [dict(row("e2", "replace_in_file", task=TASK))]
    del one2[0]["resource_id"]
    with pytest.raises(SystemExit, match="resource_id"):
        pp.check_b(one2, [row("z1", "replace_in_file", task=TASK)], record(b"", b""))
