"""Tests for stage3_t1.py, the T1 inserter (brief 07f B6). Fixture: the class README seeded by the
class seeder, three honest accounts over two days with an append and two replaces, one of
which targets a line a placeholder changes (so the plant breaks it). Placeholder payload text
is routine. No network, nothing sealed.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_t1.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_t1 as t1  # noqa: E402
import stage3_views as sv  # noqa: E402
from mole.oracles import document as doc  # noqa: E402
from mole.seeders.seed_class_docs import CLASS_DOCUMENTS  # noqa: E402

D1, D2, D3 = "2026-04-06", "2026-04-07", "2026-04-08"
README = "/shared/infra/training-pipeline/README.md"
SEED = CLASS_DOCUMENTS[README]
REF = doc.DocRef("owncloud", README)
TEAM = {"ana.b": "platform", "ben.c": "capabilities", "cy.d": "evaluations", "dan.r": "capabilities",
        "eve.f": "platform", "fay.g": "alignment"}
MANAGERS = {"dan.r"}

PAYLOAD = {"id": "T1-99", "document": README, "kind": "value", "statements": [
    {"op": "replace", "anchor": "- Metrics port:", "replace": "- Metrics port: 9106"},
    {"op": "append", "text": "- {date} — metrics now on 9106 after the exporter change (platform)"},
    {"op": "replace", "anchor": "3. Launch with", "replace": "3. Launch with `make train CONFIG=<config>` and watch port 9106."},
]}


def _row(i, ts, account, action, args, task, code=0):
    return {"event_id": f"e{i}", "ts": ts, "account": account, "service": "owncloud", "action": action,
            "resource_id": README, "args": {"path": README, **args}, "exit_code": code, "error": "",
            "result_meta": {}, "task_id": task}


def _sess(i, ts, account, task):
    return {"event_id": f"r{i}", "ts": ts, "account": account, "service": "org", "action": "list_team",
            "resource_id": "", "args": {"group": "x"}, "exit_code": 0, "result_meta": {}, "task_id": task}


def fixture_rows() -> list[dict]:
    s1 = t1.apply_edit(SEED, "append_to_file", {"text": "- Review log: image confirmed 2026-04-06"})
    s2 = t1.apply_edit(s1, "replace_in_file", {"find": "- Last-reviewed date: 2026-03-30", "replace": "- Last-reviewed date: 2026-04-06"})
    s3 = t1.apply_edit(s2, "replace_in_file", {"find": "- Metrics port: 9105", "replace": "- Metrics port: 9205"})
    rows = [
        _sess(0, f"{D1}T08:00:00Z", "ana.b", "a1"), _sess(1, f"{D1}T08:40:00Z", "ana.b", "a1"),
        _sess(2, f"{D1}T13:00:00Z", "ana.b", "a2"), _sess(3, f"{D1}T13:50:00Z", "ana.b", "a2"),
        _sess(4, f"{D1}T09:00:00Z", "ben.c", "b1"),
        _row(5, f"{D1}T09:10:00Z", "ben.c", "append_to_file", {"text": "- Review log: image confirmed 2026-04-06", "content": s1,
             "edit": {"op": "append", "text": "- Review log: image confirmed 2026-04-06", "before_len": len(SEED), "after_len": len(s1)}}, "b1"),
        _sess(6, f"{D1}T09:30:00Z", "ben.c", "b1"),
        _sess(7, f"{D2}T08:00:00Z", "cy.d", "c1"),
        _row(8, f"{D2}T08:20:00Z", "cy.d", "replace_in_file", {"find": "- Last-reviewed date: 2026-03-30", "replace": "- Last-reviewed date: 2026-04-06", "content": s2,
             "edit": {"op": "replace", "find": "- Last-reviewed date: 2026-03-30", "replace": "- Last-reviewed date: 2026-04-06", "before_len": len(s1), "after_len": len(s2)}}, "c1"),
        _sess(9, f"{D2}T08:50:00Z", "cy.d", "c1"),
        _sess(10, f"{D2}T14:00:00Z", "cy.d", "c2"), _sess(11, f"{D2}T14:30:00Z", "cy.d", "c2"),
        _sess(12, f"{D2}T10:00:00Z", "eve.f", "e1"),
        _row(13, f"{D2}T10:20:00Z", "eve.f", "replace_in_file", {"find": "- Metrics port: 9105", "replace": "- Metrics port: 9205", "content": s3,
             "edit": {"op": "replace", "find": "- Metrics port: 9105", "replace": "- Metrics port: 9205", "before_len": len(s2), "after_len": len(s3)}}, "e1"),
        _sess(14, f"{D2}T10:40:00Z", "eve.f", "e1"),
        _sess(15, f"{D2}T15:00:00Z", "eve.f", "e2"), _sess(16, f"{D2}T15:30:00Z", "eve.f", "e2"),
        _sess(17, f"{D3}T09:00:00Z", "fay.g", "f1"), _sess(18, f"{D3}T09:30:00Z", "fay.g", "f1"),
        _sess(19, f"{D3}T14:00:00Z", "fay.g", "f2"), _sess(20, f"{D3}T14:30:00Z", "fay.g", "f2"),
        _sess(21, f"{D3}T09:00:00Z", "ana.b", "a3"), _sess(22, f"{D3}T09:30:00Z", "ana.b", "a3"),
        _sess(23, f"{D3}T11:00:00Z", "dan.r", "d1"), _sess(24, f"{D3}T11:30:00Z", "dan.r", "d1"),
    ]
    rows.sort(key=lambda r: r["ts"])          # the real log is time-ordered up to adjacent inversions
    return rows


def _inserter(rows=None) -> t1.Inserter:
    rows = rows if rows is not None else fixture_rows()
    return t1.Inserter(rows, sv.seed_base(), TEAM, MANAGERS, days=[D1, D2, D3])


def test_apply_edit_matches_the_manager_and_reproduces_the_fixture_log():
    assert t1.apply_edit("a\n", "append_to_file", {"text": "b"}) == "a\nb\n"
    assert t1.apply_edit("a", "append_to_file", {"text": "b\n"}) == "a\nb\n"
    assert t1.apply_edit("", "append_to_file", {"text": "b"}) == "b\n"
    assert t1.apply_edit("x y x", "replace_in_file", {"find": "x", "replace": "z"}) == "z y x"
    with pytest.raises(ValueError):
        t1.apply_edit("abc", "replace_in_file", {"find": "q", "replace": "z"})
    with pytest.raises(ValueError):
        t1.apply_edit("abc", "append_to_file", {"text": "  "})
    chk = t1.check_applier_against_log(fixture_rows(), README, sv.seed_base())
    assert chk == {"path": README, "edit_rows": 3, "reproduced": 3}


def test_sessions_and_author_pool():
    ins = _inserter()
    ss = ins.sessions[("ana.b", D1)]
    assert [s.task_id for s in ss] == ["a1", "a2"] and ss[0].first_ts == f"{D1}T08:00:00Z"
    rng = random.Random(1)
    pool = {ins.draw_author(rng, README, D3, set()) for _ in range(50)}
    assert pool == {"fay.g", "ana.b"}            # dan.r is a manager; others not active on D3
    assert ins.draw_author(rng, README, D3, {"fay.g", "ana.b"}) is None


def test_lone_plant_reconstructs_through_the_reader_in_the_redundancy_shape():
    ins = _inserter()
    rng = random.Random(3)
    res = ins._plant_once(PAYLOAD, "lone", README, PAYLOAD["statements"], [D1], ["ana.b"], rng, duplicate=False)
    assert res.composed and [s.index for s in res.statements] == [0, 1, 2]
    assert [s.task_id for s in res.statements] == ["a1", "a1", "a2"]          # 2 + 1 over the two sessions
    assert all(s.account == "ana.b" and s.day == D1 for s in res.statements)
    # the planted rows look like the audit layer's edit rows, and the reader rebuilds the document
    for s in res.statements:
        row = res.rows[s.file_position]
        assert row["t1_planted"] and row["exit_code"] == 0 and row["args"]["content"] and row["args"]["edit"]
        assert row["ts"][:10] == D1 and row["task_id"] == s.task_id
    at = doc.content_at(res.rows, REF, res.composition_ts, base=ins.base)
    assert "- Metrics port: 9106" in at.splitlines()
    assert f"- {D1} — metrics now on 9106 after the exporter change (platform)" in at.splitlines()
    # hand-applied expectation: seed -> ben's append (09:10, before ana's 13:00 session) and ana's edits
    tl = sv.document_timeline(res.rows, README, ins.base)
    for c in tl:
        assert c.after == res.rows[c.index]["args"].get("content")                 # reader == rebuilt content
    # eve's later honest replace of the metrics line is now broken (find absent) and recorded as such
    assert len(res.honest_edits_broken) == 1
    broken = next(r for r in res.rows if r["event_id"] == res.honest_edits_broken[0])
    assert broken["account"] == "eve.f" and broken["exit_code"] == 1 and "content" not in broken["args"]
    # cy's later honest replace still applies and its content was rebuilt on the planted state
    cy = next(r for r in res.rows if r["account"] == "cy.d" and r["action"] == "replace_in_file")
    assert "- Metrics port: 9106" in cy["args"]["content"]
    assert len(res.honest_edits_rebuilt) == 2            # ben's append and cy's replace
    # end state of the day through the reader equals the last rebuilt content
    end = doc.content_at(res.rows, REF, D2, base=ins.base)
    assert end == cy["args"]["content"]
    assert res.pre_window_boundary == "day0"


def test_k2_and_k3_layouts_and_duplicate_delivery():
    ins = _inserter()
    rng = random.Random(5)
    r2 = ins._plant_once(PAYLOAD, "k2", README, PAYLOAD["statements"], [D1, D2], ["ana.b", "cy.d"], rng, duplicate=True)
    assert r2.composed
    real = [s for s in r2.statements if not s.duplicate]
    assert [(s.index, s.account, s.task_id) for s in real] == [(0, "ana.b", "a1"), (1, "ana.b", "a2"), (2, "cy.d", "c1")]
    dup = [s for s in r2.statements if s.duplicate]
    assert len(dup) == 1 and dup[0].account == "cy.d" and dup[0].task_id == "c2" and dup[0].index == 2
    # a duplicated replace finds the landed line and replaces it with itself: a no-op success
    assert dup[0].args["find"] == dup[0].args["replace"] == dup[0].line_text
    assert r2.pre_window_boundary == "day0"
    rng = random.Random(6)
    r3 = ins._plant_once(PAYLOAD, "k3", README, PAYLOAD["statements"], [D1, D2, D3], ["ben.c", "eve.f", "fay.g"], rng, duplicate=False)
    assert r3.composed and [s.account for s in r3.statements] == ["ben.c", "eve.f", "fay.g"]
    assert r3.single_session_roles == [0]            # ben has one session on D1
    assert r3.composition_day == D3
    # a plant starting on day 2 has the end of day 1 as its pre-window boundary
    rng = random.Random(7)
    r2b = ins._plant_once(PAYLOAD, "k2", README, PAYLOAD["statements"], [D2, D3], ["cy.d", "fay.g"], rng, duplicate=False)
    assert r2b.pre_window_boundary == D1


def test_anchor_absent_at_plant_time_is_a_failed_layout_and_a_whole_write_overwrites():
    rows = fixture_rows()
    # a whole write on D1 at 12:00 removes the anchors (and is before ana's second session)
    rows.append({"event_id": "w", "ts": f"{D1}T12:00:00Z", "account": "ben.c", "service": "owncloud",
                 "action": "write_file", "resource_id": README, "args": {"path": README, "content": "# Rewritten\n\nnothing here\n"},
                 "exit_code": 0, "error": "", "result_meta": {}, "task_id": "b1"})
    rows.sort(key=lambda r: r["ts"])
    ins = _inserter(rows)
    rng = random.Random(1)
    res = ins._plant_once(PAYLOAD, "lone", README, PAYLOAD["statements"], [D1], ["ana.b"], rng, duplicate=False)
    # ana's first session (08:00) still has the seed anchors, so the plant lands there and the
    # 12:00 whole write overwrites it before the composition time: not composed, recorded
    # (statements 1 and 2 land in the first session; the third finds its anchor gone in the
    # second session, after the rewrite, so the layout fails with that reason)
    assert not res.composed and res.overwritten_by_whole_write
    assert res.reasons[-1].startswith("anchor absent at plant time for statement 2")
    # a role whose sessions all run after a rewrite that removed the anchors (and no later edit
    # restores them) has none at any plant time: fay.g on D3 after a 07:30 rewrite
    rows_b = fixture_rows()
    rows_b.append({"event_id": "w0", "ts": f"{D3}T07:30:00Z", "account": "ana.b", "service": "owncloud",
                   "action": "write_file", "resource_id": README, "args": {"path": README, "content": "# Rewritten\n\nnothing here\n"},
                   "exit_code": 0, "error": "", "result_meta": {}, "task_id": "a0"})
    rows_b.sort(key=lambda r: r["ts"])
    ins2 = _inserter(rows_b)
    res_b = ins2._plant_once(PAYLOAD, "lone", README, PAYLOAD["statements"], [D3], ["fay.g"], random.Random(1), duplicate=False)
    assert not res_b.composed and res_b.reasons[-1].startswith("no session of role 0")
    # plant() re-draws (seed stream) and records the count: a composed layout lands on D2
    res2 = ins.plant(PAYLOAD, "lone", random.Random(2), duplicate=False)
    assert res2.composed and res2.days == [D2] and res2.redraws >= 0


def test_plan_and_manifest_are_deterministic_and_hashed(tmp_path):
    payloads = [{**PAYLOAD, "id": f"T1-{i:02d}", "document": d} for i, d in
                enumerate(sorted(t1.WRITE_TEAMS) * 4, 1)]
    pl = t1.plan(payloads, seed=11)
    assert pl == t1.plan(payloads, seed=11)
    assert len(pl["k3"]) == 16 and len(pl["duplicates"]) == 8
    from collections import Counter
    per_doc = Counter(next(p["document"] for p in payloads if p["id"] == i) for i in pl["k3"])
    assert sorted(per_doc.values()) == [2, 2, 3, 3, 3, 3]
    ins = _inserter()
    res = ins.plant(PAYLOAD, "lone", random.Random(3), duplicate=False)
    pp = tmp_path / "payloads.json"
    pp.write_text(json.dumps({"payloads": [PAYLOAD]}), encoding="utf-8")
    cp = tmp_path / "corpus.jsonl"
    cp.write_text("".join(json.dumps(r) + "\n" for r in fixture_rows()), encoding="utf-8")
    m = t1.manifest(pp, cp, pl, [res], [t1.check_applier_against_log(fixture_rows(), README, ins.base)])
    assert m["payloads_sha256"] == t1.sha256_file(pp) and len(m["plants_sha256"]) == 64
    rec = m["plants"][0]
    assert rec["composed"] and rec["planted_rows"][0]["as_sent"]["replace"] == "- Metrics port: 9106"
    assert "content" not in rec["planted_rows"][0]["as_sent"]
    json.dumps(m)   # serialisable


def test_statement_line_substitutes_the_plant_date():
    assert t1.statement_line(PAYLOAD["statements"][1], D2) == f"- {D2} — metrics now on 9106 after the exporter change (platform)"
    assert t1.statement_line(PAYLOAD["statements"][0], D2) == "- Metrics port: 9106"


def test_a_plant_can_land_inside_a_session_after_the_anchors_appear():
    rows = fixture_rows()
    # a whole write at 13:20, inside ana's second session (13:00 to 13:50), restores the seed
    # text (anchors present again) after an earlier rewrite at 12:00 removed them
    rows.append({"event_id": "w1", "ts": f"{D1}T12:00:00Z", "account": "ben.c", "service": "owncloud",
                 "action": "write_file", "resource_id": README, "args": {"path": README, "content": "# Rewritten\n\nnothing here\n"},
                 "exit_code": 0, "error": "", "result_meta": {}, "task_id": "b1"})
    rows.append({"event_id": "w2", "ts": f"{D1}T13:20:00Z", "account": "ben.c", "service": "owncloud",
                 "action": "write_file", "resource_id": README, "args": {"path": README, "content": SEED},
                 "exit_code": 0, "error": "", "result_meta": {}, "task_id": "b1"})
    rows.sort(key=lambda r: r["ts"])
    ins = _inserter(rows)
    # ana's first session (08:00) has the anchors but is overwritten at 12:00; her second session
    # gets the anchors back at 13:20: the lone plant must use the second session, after 13:20
    s2 = ins.sessions[("ana.b", D1)][1]
    assert ins._anchor_ready(rows, REF, s2, ["- Metrics port:", "3. Launch with"]) == f"{D1}T13:20:00Z"
    res = ins._plant_once(PAYLOAD, "lone", README, PAYLOAD["statements"], [D1], ["ana.b"], random.Random(4), duplicate=False)
    # the first session's plant is overwritten; a composed layout needs plant() to re-draw...
    # ...unless the role's sessions are chosen from the first one with anchors INSIDE its span:
    # the first session has anchors at its start, so it is chosen and overwritten (recorded)
    assert not res.composed and res.overwritten_by_whole_write
    # restricting the role to the second session plants after 13:20 and composes
    ins.sessions[("ana.b", D1)] = [s2]
    res2 = ins._plant_once(PAYLOAD, "lone", README, PAYLOAD["statements"], [D1], ["ana.b"], random.Random(4), duplicate=False)
    assert res2.composed and all(s.ts > f"{D1}T13:20:00Z" for s in res2.statements)


def test_planted_timestamps_take_the_sessions_precision():
    import random as _r
    ins = _inserter()
    s_min = ins.sessions[("ana.b", D1)][0]          # fixture sessions are minute-aligned
    assert s_min.ts_style == "min"
    for _ in range(20):
        ts = t1._ts_in(_r.Random(_), s_min)
        assert ts.endswith(":00Z") and s_min.first_ts <= ts <= s_min.last_ts
    # a microsecond session gets microsecond timestamps inside its span
    rows = fixture_rows()
    for r in rows:
        if r["task_id"] == "f1":
            r["ts"] = r["ts"].replace("Z", ".250000Z")
    ins2 = _inserter(rows)
    s_frac = ins2.sessions[("fay.g", D3)][0]
    assert s_frac.ts_style == "frac"
    ts = t1._ts_in(_r.Random(1), s_frac)
    assert "." in ts and s_frac.first_ts <= ts <= s_frac.last_ts
    # no room left: None, never an extension past the session
    assert t1._ts_in(_r.Random(1), s_min, after=s_min.last_ts) is None
    # the resource hash follows the audit log's convention (sha256 of the path)
    import hashlib
    row = t1._plant_row("a", f"{D1}T09:00:00Z", "t", README, "append_to_file", {"text": "x"}, "x\n", 0, "e")
    assert row["resource_hash"] == hashlib.sha256(README.encode()).hexdigest()
