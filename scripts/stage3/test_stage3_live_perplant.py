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


# ── G8 fix 1 (coordinator, 17 Nov 17:35 IST): the sealed `table` mode ───────────────────────────────────────────────

import stage3_live_monitor as lm  # noqa: E402


def _table_inputs(tmp_path, monkeypatch, *, per_plant=None):
    monkeypatch.setattr(lm, "MON", tmp_path / "mon")
    cp = lm.campaign_paths("t")
    lm.open_campaign(cp)
    lm.write_envelopes(cp["dir"], "perplant", {"campaign": "t"},
                       {"flags": {"P1": {"state": "not_flagged", "state_one_day_null": "not_flagged"},
                                  "P2": {"state": "flagged", "state_one_day_null": "not_flagged"}},
                        "offline_single_statement": {"P1": False, "P2": True}, "scores": {"x": 1.0}})
    rec = {"plants": [{"slot_id": "S1", "payload_id": "P1"}, {"slot_id": "S2", "payload_id": "P2"}]}
    rp = tmp_path / "placement.json"
    rp.write_text(json.dumps(rec))
    jo = tmp_path / "join-outcome.json"
    jo.write_text(json.dumps({"P": 5, "per_plant": per_plant if per_plant is not None else
                              [{"slot_id": "S1", "counted": 3}, {"slot_id": "S2", "counted": 2}]}))
    jm = tmp_path / "join-machinery.json"
    jm.write_text(json.dumps({"completed_days": 1, "outcome_sha256": hashlib.sha256(jo.read_bytes()).hexdigest(),
                              "inputs": {"placement-planted": hashlib.sha256(rp.read_bytes()).hexdigest()[:8]}}))
    return cp, ["table", "--campaign", "t", "--join-outcome", str(jo), "--join-machinery", str(jm), "--placement-record", str(rp)]


def test_table_mode_writes_the_sealed_table_and_prints_machinery_only(tmp_path, monkeypatch, capsys):
    cp, argv = _table_inputs(tmp_path, monkeypatch)
    assert pp.main(argv) == 0
    out = capsys.readouterr().out
    printed = json.loads(out)
    assert lm._outcome_keys_in(printed) == [] and "acts in" not in out
    assert printed["plants_in_table"] == 2 and printed["units_expected"] == 11 and printed["complete"] is False
    assert set(printed["fields_present"]) == {"has_P", "has_k_missed", "has_P_m", "has_k_missed_one_day_null",
                                              "has_P_m_one_day_null", "has_days", "has_sentence", "has_per_plant"}
    assert all(printed["fields_present"].values())
    op = cp["dir"] / "outcome-perplant-table.json"
    assert printed["outcome_file"] == op.name and printed["outcome_file_sha256"] == hashlib.sha256(op.read_bytes()).hexdigest()
    t = json.loads(op.read_text())
    expect = pp.table({"P1": {"state": "not_flagged", "state_one_day_null": "not_flagged"},
                       "P2": {"state": "flagged", "state_one_day_null": "not_flagged"}}, {"P1": False, "P2": True},
                      {"P1": 3, "P2": 2}, days=1)
    assert {k: t[k] for k in expect} == expect
    assert t["join_P"] == 5 and t["plants_with_join_entry"] == 2


def test_table_mode_refuses_inputs_that_are_not_the_named_ones(tmp_path, monkeypatch):
    cp, argv = _table_inputs(tmp_path, monkeypatch)
    jo = Path(argv[argv.index("--join-outcome") + 1])
    jo.write_text(jo.read_text() + " ")                                   # the join outcome is not the one its machinery names
    with pytest.raises(SystemExit, match="join outcome"):
        pp.main(argv)
    cp, argv = _table_inputs(tmp_path / "b", monkeypatch)
    rp = Path(argv[argv.index("--placement-record") + 1])
    rp.write_text(rp.read_text() + " ")
    with pytest.raises(SystemExit, match="placement record"):
        pp.main(argv)
    cp, argv = _table_inputs(tmp_path / "c", monkeypatch)
    o = cp["dir"] / "outcome-perplant.json"
    o.write_text(o.read_text() + " ")
    with pytest.raises(SystemExit, match="outcome-perplant"):
        pp.main(argv)


def test_table_mode_fails_loudly_on_a_missing_join_field(tmp_path, monkeypatch):
    cp, argv = _table_inputs(tmp_path, monkeypatch, per_plant=[{"slot_id": "S1"}])
    with pytest.raises(SystemExit, match="counted"):
        pp.main(argv)
