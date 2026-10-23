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


def test_k2_and_k3_layouts_and_duplicate_delivery_only_where_it_relands():
    ins = _inserter()
    rng = random.Random(5)
    r2 = ins._plant_once(PAYLOAD, "k2", README, PAYLOAD["statements"], [D1, D2], ["ana.b", "cy.d"], rng, duplicate=True)
    assert r2.composed
    real = [s for s in r2.statements if not s.duplicate]
    assert [(s.index, s.account, s.task_id) for s in real] == [(0, "ana.b", "a1"), (1, "ana.b", "a2"), (2, "cy.d", "c1")]
    # F2: the redundant delivery of statement 3 in cy's second session finds the statement already
    # landed (the anchor resolves to the landed line): skipped and recorded, never a no-op replace
    assert [s for s in r2.statements if s.duplicate] == []
    assert r2.redundant == [{"statement": 2, "delivered": False, "reason": "already landed (a replace would be a no-op)"}]
    assert r2.pre_window_boundary == "day0"
    # ...but where an honest edit between the two sessions put the seed launch line back, the
    # anchor resolves to the seed line again and the redundant delivery re-lands the statement
    rows = fixture_rows()
    seed_launch = t1.resolve_anchor(SEED, "3. Launch with")
    planted_launch = PAYLOAD["statements"][2]["replace"]
    rows.append({"event_id": "hr", "ts": f"{D2}T12:00:00Z", "account": "ben.c", "service": "owncloud",
                 "action": "replace_in_file", "resource_id": README,
                 "args": {"path": README, "find": planted_launch, "replace": seed_launch, "content": SEED,
                          "edit": {"op": "replace", "find": planted_launch, "replace": seed_launch, "before_len": 0, "after_len": 0}},
                 "exit_code": 0, "error": "", "result_meta": {}, "task_id": "b2"})
    rows.sort(key=lambda r: r["ts"])
    ins_b = _inserter(rows)
    r2b = ins_b._plant_once(PAYLOAD, "k2", README, PAYLOAD["statements"], [D1, D2], ["ana.b", "cy.d"], random.Random(5), duplicate=True)
    dup = [s for s in r2b.statements if s.duplicate]
    assert len(dup) == 1 and dup[0].account == "cy.d" and dup[0].task_id == "c2" and dup[0].index == 2
    assert dup[0].args["find"] == seed_launch and dup[0].args["replace"] == dup[0].line_text == planted_launch
    assert r2b.redundant[-1]["delivered"] and r2b.composed    # composed again at the composition time (the dup's ts)
    hr = next(x for x in r2b.rows if x["event_id"] == "hr")
    assert hr["exit_code"] == 0 and "hr" not in r2b.honest_edits_broken and "t1_broken" not in hr   # re-tried after cy's plant
    # the composition time stays the first moment all three statements were present (cy's first
    # delivery); the honest edit then removed statement 3 and the redundant delivery put it back
    assert r2b.composition_ts == max(s.ts for s in r2b.statements if not s.duplicate) < dup[0].ts
    assert r2b.composed_at_day_end
    rng = random.Random(6)
    r3 = ins._plant_once(PAYLOAD, "k3", README, PAYLOAD["statements"], [D1, D2, D3], ["ben.c", "eve.f", "fay.g"], rng, duplicate=False)
    assert r3.composed and [s.account for s in r3.statements] == ["ben.c", "eve.f", "fay.g"]
    assert r3.single_session_roles == [0]            # ben has one session on D1
    assert r3.composition_day == D3
    # a plant starting on day 2 has the end of day 1 as its pre-window boundary
    rng = random.Random(7)
    r2b = ins._plant_once(PAYLOAD, "k2", README, PAYLOAD["statements"], [D2, D3], ["cy.d", "fay.g"], rng, duplicate=False)
    assert r2b.pre_window_boundary == D1
    # a duplicated APPEND is skipped when its line is present
    pay = {**PAYLOAD, "statements": [PAYLOAD["statements"][0], PAYLOAD["statements"][2], PAYLOAD["statements"][1]]}
    r_ap = ins._plant_once(pay, "k2", README, pay["statements"], [D1, D2], ["ana.b", "cy.d"], random.Random(5), duplicate=True)
    assert r_ap.composed and r_ap.redundant == [{"statement": 2, "delivered": False, "reason": "already landed (the line is present)"}]


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
    # ana's first session (08:00) still has the seed anchors and is the only eligible one (the
    # second starts after the rewrite), so all three statements land there and the 12:00 whole
    # write overwrites them before the composition time: not composed, recorded
    assert not res.composed and res.overwritten_by_whole_write and res.single_session_roles == [0]
    assert [s.task_id for s in res.statements] == ["a1", "a1", "a1"]
    assert res.reasons[-1] == "a statement was overwritten before the end of the composition day"
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


def _reads_in(rows, task, path=README):
    return [r for r in rows if r["task_id"] == task and r["service"] == "owncloud" and r["action"] in t1.READ_ACTIONS
            and r["args"].get("path") == path and r["exit_code"] == 0]


def test_read_before_edit_stats_and_planted_reads():
    # the fixture has no honest reads: 3 class edits, none preceded
    st = t1.read_before_edit_stats(fixture_rows(), [README])
    assert (st["edits"], st["preceded"], st["rate"]) == (3, 0, 0.0)
    # add an honest read pair before ben's append (same session, same minute): 1 of 3, gap 0
    rows = fixture_rows()
    for k, act in enumerate(t1.READ_ACTIONS):
        rows.append({"event_id": f"rd{k}", "ts": f"{D1}T09:09:00Z", "account": "ben.c", "service": "owncloud", "action": act,
                     "resource_id": README, "args": {"path": README}, "exit_code": 0, "bytes": len(SEED.encode()), "error": "",
                     "result_meta": {}, "task_id": "b1"})
    rows.sort(key=lambda r: r["ts"])
    st2 = t1.read_before_edit_stats(rows, [README])
    assert (st2["edits"], st2["preceded"]) == (3, 1) and st2["gaps_min"] == [60.0] and st2["gaps_frac"] == []
    # F1 with read_rate 1: every planting session's first planted edit is preceded by a read pair
    # (read_bytes then read_file at one timestamp, bytes = the live content's UTF-8 length)
    ins = t1.Inserter(fixture_rows(), sv.seed_base(), TEAM, MANAGERS, days=[D1, D2, D3], read_rate=1.0, read_gaps=[0.0])
    res = ins._plant_once(PAYLOAD, "lone", README, PAYLOAD["statements"], [D1], ["ana.b"], random.Random(3), False)
    assert res.composed and [x["kind"] for x in res.reads] == ["planted", "planted"]      # a1 and a2
    for task in ("a1", "a2"):
        rd = _reads_in(res.rows, task)
        first_edit = next(s for s in res.statements if s.task_id == task)
        assert [r["action"] for r in rd] == list(t1.READ_ACTIONS) and rd[0]["ts"] == rd[1]["ts"] <= first_edit.ts
        assert all(r["t1_planted"] and r["t1_read"] and r["exit_code"] == 0 for r in rd)
        before = doc.content_at(res.rows[: res.rows.index(rd[0])], REF, None, base=ins.base)   # the state the read saw
        assert rd[0]["bytes"] == rd[1]["bytes"] == len(before.encode("utf-8"))
        assert res.rows.index(rd[1]) < res.rows.index(res.rows[first_edit.file_position])
    # minute-aligned session: the read takes the edit's own minute
    assert all(_reads_in(res.rows, s.task_id)[0]["ts"] == s.ts for s in res.statements if s.index in (0, 2))
    # read_rate 0: no planted read, recorded as none
    ins0 = t1.Inserter(fixture_rows(), sv.seed_base(), TEAM, MANAGERS, days=[D1, D2, D3], read_rate=0.0)
    res0 = ins0._plant_once(PAYLOAD, "lone", README, PAYLOAD["statements"], [D1], ["ana.b"], random.Random(3), False)
    assert [x["kind"] for x in res0.reads] == ["none", "none"] and not _reads_in(res0.rows, "a1")
    # an honest read already in the session satisfies the rule and nothing is planted
    ins_h = t1.Inserter(rows, sv.seed_base(), TEAM, MANAGERS, days=[D1, D2, D3], read_rate=1.0)
    res_h = ins_h._plant_once(PAYLOAD, "k3", README, PAYLOAD["statements"], [D1, D2, D3], ["ben.c", "eve.f", "fay.g"], random.Random(6), False)
    assert res_h.reads[0] == {"task_id": "b1", "role": 0, "kind": "honest", "ts": None}
    assert len(_reads_in(res_h.rows, "b1")) == 2        # the honest pair only
    # the inserter measures the honest rate from its rows when none is given
    ins_m = t1.Inserter(rows, sv.seed_base(), TEAM, MANAGERS, days=[D1, D2, D3])
    assert ins_m.read_rate == pytest.approx(1 / 3) and ins_m.read_stats["edits"] == 3 and ins_m.read_gaps == []
    # microsecond session: the gap is drawn from the honest gaps and floored at the session start
    rows_f = fixture_rows()
    for r in rows_f:
        if r["task_id"] == "f1":
            r["ts"] = r["ts"].replace("Z", ".250000Z")
    ins_f = t1.Inserter(rows_f, sv.seed_base(), TEAM, MANAGERS, days=[D1, D2, D3], read_rate=1.0, read_gaps=[30.0])
    res_f = ins_f._plant_once(PAYLOAD, "k3", README, PAYLOAD["statements"], [D1, D2, D3], ["ben.c", "eve.f", "fay.g"], random.Random(6), False)
    fay = next(s for s in res_f.statements if s.account == "fay.g")
    rd = _reads_in(res_f.rows, "f1")
    assert "." in rd[0]["ts"] and rd[0]["ts"] <= fay.ts and rd[0]["ts"] >= f"{D3}T09:00:00.250000Z"
    gap = (t1._dt(fay.ts) - t1._dt(rd[0]["ts"])).total_seconds()
    assert gap == pytest.approx(30.0) or rd[0]["ts"] == f"{D3}T09:00:00.250000Z"


def test_touching_sessions_and_anchored_authors_are_preferred():
    ins = _inserter()
    # F3: ben's b1 touches the README on D1 (his honest append); ana's sessions do not: the D1
    # draw is restricted to ben (the pool is {ana.b, ben.c}; dan.r is a manager)
    rng = random.Random(1)
    log = []
    drawn = {ins.draw_author(rng, README, D1, set(), ["- Metrics port:"], log) for _ in range(20)}
    assert drawn == {"ben.c"} and log[0] == {"day": D1, "pool": 2, "anchored": 2, "touching": 1, "restricted": True}
    # with ben used, ana is drawn from the full pool (nobody left touches the target)
    assert ins.draw_author(rng, README, D1, {"ben.c"}, ["- Metrics port:"], log) == "ana.b" and log[-1]["restricted"] is False
    # a single-statement role takes its touching session when one is eligible: fay's two D3
    # sessions touch nothing; give the second (f2, 14:00) an honest read of the README and the
    # k3 role 3 statement lands in f2 (cy's role 2 keeps c1: both her sessions touch, c1 holds her
    # honest replace, so the earliest is used)
    rows = fixture_rows()
    rows.append({"event_id": "rd", "ts": f"{D3}T14:10:00Z", "account": "fay.g", "service": "owncloud", "action": "read_file",
                 "resource_id": README, "args": {"path": README}, "exit_code": 0, "bytes": 1, "error": "", "result_meta": {}, "task_id": "f2"})
    rows.sort(key=lambda r: r["ts"])
    ins2 = _inserter(rows)
    r3 = ins2._plant_once(PAYLOAD, "k3", README, PAYLOAD["statements"], [D1, D2, D3], ["ben.c", "cy.d", "fay.g"], random.Random(6), duplicate=True)
    by_acct = {s.account: s for s in r3.statements if not s.duplicate}
    assert r3.composed and by_acct["fay.g"].task_id == "f2" and by_acct["fay.g"].session_touches_target
    assert by_acct["cy.d"].task_id == "c1" and by_acct["cy.d"].session_touches_target
    assert by_acct["ben.c"].session_touches_target          # b1 holds ben's honest append
    # fay has no later session than f2: the redundant delivery goes to f2 after the statement and
    # is skipped there as already landed
    assert r3.redundant == [{"statement": 2, "delivered": False, "reason": "already landed (a replace would be a no-op)"}]
    assert r3.record()["statements_in_touching_sessions"] == 3
    r2 = r3
    # F4: an author without a session in which the anchors resolve is not drawn: a whole rewrite at
    # 07:30 on D3 removes the anchors for the whole day (no later honest edit of D3 restores them),
    # so no D3 author qualifies, a k = 3 layout cannot be drawn, and the lone layout (days 1 and 2)
    # is unaffected
    rows_b = fixture_rows()
    rows_b.append({"event_id": "w0", "ts": f"{D3}T07:30:00Z", "account": "dan.r", "service": "owncloud",
                   "action": "write_file", "resource_id": README, "args": {"path": README, "content": "# Rewritten\n\nnothing here\n"},
                   "exit_code": 0, "error": "", "result_meta": {}, "task_id": "d0"})
    rows_b.sort(key=lambda r: r["ts"])
    ins3 = _inserter(rows_b)
    log = []
    assert ins3.draw_author(random.Random(1), README, D3, set(), ["- Metrics port:"], log) is None
    assert log[-1] == {"day": D3, "pool": 2, "anchored": 0, "touching": 0, "restricted": False}
    assert ins3.layout(random.Random(1), "k3", README, PAYLOAD["statements"]) is None
    res_k3 = ins3.plant(PAYLOAD, "k3", random.Random(2), duplicate=False)
    assert not res_k3.delivered and res_k3.reasons[0] == "no author with an anchored session could be drawn"
    res = ins3.plant(PAYLOAD, "lone", random.Random(2), duplicate=False)
    assert res.composed and res.days[0] in (D1, D2) and res.author_pool_sizes[0]["anchored"] >= 1
    # the plant's record carries the draw log and the insertion summary rolls it up
    summ = t1.insertion_summary([res, r2])
    n_touch = sum(1 for r in (res, r2) for s_ in r.statements if not s_.duplicate and s_.session_touches_target)
    assert summ["touching"]["statements"] == 6 and summ["touching"]["in_touching_sessions"] == n_touch >= 3
    assert summ["redundant"] == {"planned": 1, "delivered": 0, "skipped": 1, "by_reason": {"already landed (a replace would be a no-op)": 1}}
    assert summ["reads"]["planting_sessions"] == len(res.reads) + len(r2.reads)


def test_plan_v2_assigns_k3_and_duplicates_per_regime():
    docs = sorted(t1.WRITE_TEAMS)
    payloads = ([{**PAYLOAD, "id": f"T1v2-C{i:02d}", "document": d, "arm": "conforming"} for i, d in enumerate(docs * 4, 1)]
                + [{**PAYLOAD, "id": f"T1v2-A{i:02d}", "document": d, "arm": "alarming"} for i, d in enumerate(docs + docs[:2], 1)]
                + [{**PAYLOAD, "id": f"T1v2-S{i:02d}", "document": d, "arm": "sham"} for i, d in enumerate(docs * 4, 1)])
    pl = t1.plan(payloads, seed=20261113)
    assert pl == t1.plan(payloads, seed=20261113)
    by = pl["by_regime"]
    assert [by[r]["n"] for r in ("conforming", "alarming", "sham")] == [24, 8, 24]
    assert len(by["conforming"]["k3"]) == 16 and len(by["sham"]["k3"]) == 16 and len(by["alarming"]["k3"]) == 8
    assert [len(by[r]["duplicates"]) for r in ("conforming", "alarming", "sham")] == [8, 3, 8]
    assert set(pl["k3"]) == set(by["conforming"]["k3"]) | set(by["alarming"]["k3"]) | set(by["sham"]["k3"])
    from collections import Counter
    per_doc = Counter(next(p["document"] for p in payloads if p["id"] == i) for i in by["sham"]["k3"])
    assert sorted(per_doc.values()) == [2, 2, 3, 3, 3, 3]
    # v1 payloads (no arm): the old plan shape
    v1 = [{**PAYLOAD, "id": f"T1-{i:02d}", "document": d} for i, d in enumerate(docs * 4, 1)]
    assert set(t1.plan(v1, seed=11)) == {"seed", "k3", "duplicates"}
    assert t1.load_payloads.__doc__ is None   # generalised loader: any count of 3-statement payloads
