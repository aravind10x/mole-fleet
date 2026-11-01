"""Tests for brief 27's additions to stage3_t1.py: the lone-line arm (E1), the opt-in valid-draw restriction (E2) and
application isolation (E3), on test_stage3_t1.py's routine fixture (README seed, six accounts, three days), plus the
checks on brief 26's file and the B3 items (skipped when the inputs are not on disk). Synthetic text is routine; no
network, nothing sealed; no item line or document text is printed.

The full default-mode replay of the T1 v3 manifest (pre-change module against the new one) runs in
stage3_b3_lone_line_check.py `replay` (several minutes); here it runs when STAGE3_FULL_REPLAY=1.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_t1_line_arm.py
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_t1 as t1  # noqa: E402
import test_stage3_t1 as ft  # noqa: E402  (the inserter's own fixture)
from mole.oracles import document as doc  # noqa: E402

D1, D2, D3 = ft.D1, ft.D2, ft.D3
README, P = ft.README, ft.PAYLOAD
V3_CLASS = "24d3d147d6f5e6a052820714dfefebe2442aaeaf5f796cf299fe319c41027b4a"


def rep(anchor, new):
    return {"op": "replace", "anchor": anchor, "replace": new}


def rows_sha(res) -> str:
    return hashlib.sha256(json.dumps(res.rows, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def same(a, b) -> bool:
    return a.record() == b.record() and rows_sha(a) == rows_sha(b)


def base(rows=None, **kw) -> t1.Inserter:
    return t1.Inserter(rows if rows is not None else ft.fixture_rows(), ft.sv.seed_base(), kw.pop("team", ft.TEAM),
                       ft.MANAGERS, days=[D1, D2, D3], **kw)


def parts(rows=None, valid=None, **kw) -> t1.PartSInserter:
    return t1.PartSInserter(rows if rows is not None else ft.fixture_rows(), ft.sv.seed_base(), kw.pop("team", ft.TEAM),
                            ft.MANAGERS, days=[D1, D2, D3], valid_draws=valid, **kw)


def vfile(item, lines=None, key="k1", document=README) -> t1.ValidDraws:
    """A valid-draws table in brief 26's shape (items[].draws.valid_draws / valid_by_day, items[].lone_lines[])."""
    by_day: dict[str, int] = {}
    for d, _a in item:
        by_day[d] = by_day.get(d, 0) + 1
    entry = {"item_id": key, "document": document, "draws": {"valid_draws": [list(x) for x in item], "valid_by_day": by_day},
             "lone_lines": None if lines is None else [{"valid_draws": [list(x) for x in ln]} for ln in lines]}
    return t1.ValidDraws({"items": [entry]})


def end_lines(res) -> list[str]:
    s = doc.content_at(res.rows, ft.REF, res.composition_day, base=ft.sv.seed_base())
    return s.splitlines() if isinstance(s, str) else []


def lines_of(payload, day):
    return [t1.statement_line(st, day) for st in payload["statements"]]


# ── E1: the lone-line arm ──────────────────────────────────────────────────────

def test_the_application_class_is_unchanged():
    assert hashlib.sha256(inspect.getsource(t1.Inserter).encode("utf-8")).hexdigest() == V3_CLASS
    assert issubclass(t1.PartSInserter, t1.Inserter) and t1.ARMS == ("lone", "k2", "k3")
    assert t1.LINE_ARMS == ("line0", "line1", "line2") and t1.line_arm(2) == "line2"


def test_a_line_alone_lands_with_its_role_index_and_nothing_else():
    ins = parts()
    for i in range(3):
        res = ins.plant_line(P, i, random.Random(10 + i), False, exclude=())
        assert res.arm == f"line{i}" and res.line_index == i and res.record()["line_index"] == i
        assert [s.index for s in res.statements] == [i] and len(res.authors) == len(res.days) == 1
        assert res.days[0] in (D1, D2) and res.composed and res.delivered
        mine = lines_of(P, res.days[0])
        got = end_lines(res)
        assert mine[i] in got and all(mine[j] not in got for j in range(3) if j != i)
        row = res.rows[res.statements[0].file_position]
        assert row["t1_planted"] and row["event_id"] == t1._event_id(P["id"], f"line{i}", i, False)


def test_the_line_arm_draws_by_the_lone_arms_rule():
    """Same day draw (days[:2]) and the same author pool (team template, managers, F4 anchored sessions, F3 touching
    sessions): the line arm's layout equals the lone arm's layout of a payload made of that line alone."""
    ins, b = parts(), base()
    for i, st in enumerate(P["statements"]):
        for seed in range(25):
            got = ins.layout(random.Random(seed), f"line{i}", README, P["statements"])
            want = b.layout(random.Random(seed), "lone", README, [st, st, st])
            assert got == want and ins.last_draw_log == b.last_draw_log
    # the team template: an account outside the document's write-teams is never drawn
    ins_hr = parts(team={**ft.TEAM, "ben.c": "hr"})
    assert {tuple(ins_hr.layout(random.Random(s), "line0", README, P["statements"])[1]) for s in range(30)} <= {("ana.b",), ("cy.d",), ("eve.f",)}


def test_the_line_arm_is_on_its_own_author():
    """A6.5 (iii): the line is applied on an author other than the triple's; on D1 the touching author is excluded, so the
    pool falls back to the anchored one."""
    ins = parts()
    seen = set()
    for seed in range(30):
        res = ins.plant_line(P, 2, random.Random(seed), False, exclude={"ben.c", "cy.d"})
        seen.add((res.days[0], res.authors[0]))
    assert seen == {(D1, "ana.b"), (D2, "eve.f")}
    assert ins._exclude == frozenset()                      # the exclusion does not outlive the call
    # the triple's authors are an explicit argument of every line-arm selection (an empty one is stated, not implied)
    rins = parts(valid=vfile([(D2, "cy.d")], lines=[[(D1, "ben.c"), (D2, "eve.f")]] * 3))
    for i_ in (ins, rins):
        with pytest.raises(ValueError):
            i_.plant_line(P, 2, random.Random(0), False, key="k1")
    with pytest.raises(ValueError):
        rins.plant_pair(P, 2, random.Random(0), key="k1")
    with pytest.raises(ValueError):
        rins.plant(P, "line2", random.Random(0), False, key="k1")
    with pytest.raises(t1.Refused) as e:
        rins.apply_at(P, "line2", D2, "eve.f", random.Random(0), key="k1", exclude={"eve.f"})
    assert e.value.reason == t1.RF_EXCLUDED


def test_the_line_arm_keeps_the_floor_rule():
    """F4's whole-write floor: a session ending before the document's last whole write that day is not eligible."""
    rows = ft.fixture_rows() + [ft._row(40, f"{D1}T12:00:00Z", "dan.r", "write_file", {"content": ft.SEED}, "d0")]
    rows.sort(key=lambda r: r["ts"])
    ins = parts(rows)
    for seed in range(20):
        res = ins.plant_line(P, 1, random.Random(seed), False, exclude=())
        if res.days[0] == D1:
            assert res.authors == ["ana.b"] and res.statements[0].ts > f"{D1}T12:00:00Z"   # ben.c's session ends at 09:30


def test_the_line_arm_reads_before_edit_and_prefers_touching_sessions():
    ins = parts(read_rate=1.0)
    res = ins._plant_once(P, "line0", README, P["statements"], [D2], ["cy.d"], random.Random(3), False)
    s = res.statements[0]
    assert s.task_id == "c1" and s.session_touches_target               # c1 touches the README (F3), c2 does not
    assert res.reads == [{"task_id": "c1", "role": 0, "kind": "planted", "ts": res.reads[0]["ts"]}]
    reads = [i for i, r in enumerate(res.rows) if r.get("t1_read") and r["task_id"] == "c1"]
    assert len(reads) == 2 and max(reads) < s.file_position and res.rows[reads[0]]["action"] == "read_bytes"


def test_the_line_arms_redundant_delivery_only_where_it_relands():
    ins = parts()
    res = ins._plant_once(P, "line0", README, P["statements"], [D2], ["cy.d"], random.Random(4), True)
    assert [s.duplicate for s in res.statements] == [False]
    assert res.redundant == [{"statement": 0, "delivered": False, "reason": "already landed (a replace would be a no-op)"}]
    res = ins._plant_once(P, "line1", README, P["statements"], [D2], ["cy.d"], random.Random(4), True)
    assert res.redundant == [{"statement": 1, "delivered": False, "reason": "already landed (the line is present)"}]


def test_default_mode_three_arms_are_the_inserters_own():
    """No valid-draws file: plant() of the three arms is Inserter.plant with the same stream (records and rows)."""
    for arm in t1.ARMS:
        for seed in range(6):
            for dup in (False, True):
                a = base().plant(P, arm, random.Random(seed), dup)
                b = parts().plant(P, arm, random.Random(seed), dup)
                assert same(a, b)
    ins = parts()
    assert not ins.restricted
    with pytest.raises(ValueError):
        ins.plant(P, "lone", random.Random(0), False, exclude={"ana.b"})


@pytest.mark.skipif(os.environ.get("STAGE3_FULL_REPLAY") != "1", reason="the full T1 v3 replay runs in the harness")
def test_full_replay_of_the_t1v3_manifest():
    import stage3_b3_lone_line_check as lc
    out = lc.replay()
    assert out["identical"] and out["n_plants"] == 128


# ── E2: the valid-draw restriction ─────────────────────────────────────────────

def test_the_valid_draws_table_reads_brief_26s_shape():
    v = vfile([(D2, "cy.d"), (D2, "eve.f"), (D1, "ben.c")], lines=[[(D1, "ben.c")], [], [(D2, "eve.f")]])
    assert v.draws("k1", "item", README) == [(D2, "cy.d"), (D2, "eve.f"), (D1, "ben.c")]
    assert v.draws("k1", 2) == [(D2, "eve.f")] and v.draws("k1", 1) == []
    with pytest.raises(t1.Refused) as e:
        v.draws("nope", "item")
    assert e.value.reason == t1.RF_NOT_LISTED
    with pytest.raises(ValueError):
        v.draws("k1", "item", "/shared/ops/oncall-runbook.md")
    bad = {"items": [{"item_id": "k", "document": README, "draws": {"valid_draws": [[D1, "ben.c"]], "valid_by_day": {D1: 2}}}]}
    with pytest.raises(ValueError):
        t1.ValidDraws(bad)
    with pytest.raises(t1.Refused) as e:
        t1.ValidDraws({"items": [{**bad["items"][0], "draws": {"valid_draws": [], "valid_by_day": {}}}]}).draws("k", 0)
    assert e.value.reason == t1.RF_NOT_LISTED                           # no lone lines listed (not a candidate)


def test_a_draw_outside_the_valid_set_is_refused():
    ins = parts(valid=vfile([(D2, "cy.d")]))
    assert ins.restricted
    with pytest.raises(t1.Refused) as e:
        ins.apply_at(P, "lone", D2, "eve.f", random.Random(1), key="k1")
    assert e.value.reason == t1.RF_OUTSIDE and (e.value.day, e.value.author) == (D2, "eve.f")
    assert ins.apply_at(P, "lone", D2, "cy.d", random.Random(1), key="k1").composed
    with pytest.raises(ValueError):
        ins.apply_at(P, "lone", D2, "cy.d", random.Random(1))         # restricted mode needs the item's id


def test_every_restricted_draw_comes_from_the_valid_set():
    valid = [(D2, "eve.f")]
    ins = parts(valid=vfile(valid, lines=[[(D1, "ben.c"), (D2, "cy.d")]] * 3))
    for seed in range(15):
        r = ins.plant(P, "lone", random.Random(seed), False, key="k1")
        assert (r.days[0], r.authors[0]) in valid
        r = ins.plant_line(P, 2, random.Random(seed), False, key="k1", exclude={"eve.f"})
        assert (r.days[0], r.authors[0]) in {(D1, "ben.c"), (D2, "cy.d")}
    for arm in ("k2", "k3"):
        with pytest.raises(t1.Refused) as e:
            ins.plant(P, arm, random.Random(0), False, key="k1")
        assert e.value.reason == t1.RF_ARM


def test_a_non_unique_target_is_refused_where_default_mode_lands():
    """M1: an anchor that two lines of the document start with. The default mode applies it (resolve_anchor takes the
    first match); the restricted mode refuses the draw although the table lists it."""
    p = {**P, "id": "T1-95", "statements": [rep("- ", "- Metrics port: 9106"), *P["statements"][1:]]}
    st = ft.SEED.splitlines()
    assert sum(1 for ln in st if ln.startswith("- ")) > 1
    d = parts()._plant_once(p, "lone", README, p["statements"], [D2], ["cy.d"], random.Random(2), False)
    assert d.rows and d.composed
    ins = parts(valid=vfile([(D2, "cy.d")], lines=[[(D2, "cy.d")]] * 3))
    with pytest.raises(t1.Refused) as e:
        ins.apply_at(p, "lone", D2, "cy.d", random.Random(2), key="k1")
    assert e.value.reason == t1.RF_MULTI
    with pytest.raises(t1.Refused) as e:
        ins.apply_at(p, "line0", D2, "cy.d", random.Random(2), key="k1", exclude=())
    assert e.value.reason == t1.RF_MULTI
    # plant() refuses instead of returning a delivered or last layout (the default rule's fallback)
    with pytest.raises(t1.Refused) as e:
        ins.plant(p, "lone", random.Random(2), False, key="k1")
    assert e.value.reason == t1.RF_NO_VALID_DRAW and [x["reason"] for x in e.value.refused] == [t1.RF_MULTI]


def test_an_already_present_line_is_refused_and_the_check_reasons():
    ins = parts(valid=vfile([(D1, "ben.c"), (D2, "cy.d")], lines=[[(D1, "ben.c")]] * 3))
    present = {**P, "id": "T1-94", "statements": [rep("- Metrics port:", "- Metrics port: 9105"), *P["statements"][1:]]}
    assert "- Metrics port: 9105" in ft.SEED.splitlines()
    with pytest.raises(t1.Refused) as e:
        ins.apply_at(present, "line0", D1, "ben.c", random.Random(0), key="k1", exclude=())
    assert e.value.reason == t1.RF_PRESENT
    assert t1.application_reason("a\nb\n", rep("b", "c"), "c", "a\nc\n") is None
    assert t1.application_reason("a\nb\n", rep("b", "c"), "c", "c\nb\n") == t1.RF_DIFF
    assert t1.application_reason("a\nb\n", rep("x", "c"), "c", "a\nc\n") == t1.RF_ABSENT
    assert t1.application_reason("ab\nb\n", rep("b", "c"), "c", "ab\nc\n") == t1.RF_MULTI     # the line occurs earlier as a substring
    assert t1.application_reason("a\n", {"op": "append", "text": "x"}, "x\ny", "a\nx\ny\n") == t1.RF_MULTILINE
    assert t1.application_reason(None, rep("b", "c"), "c", "") == t1.RF_UNKNOWN
    assert t1.intended_document("a", {"op": "append", "text": "x"}, "x") == "a\nx\n"


def test_a_line_changed_later_the_same_day_is_refused():
    """A routine edit later on the line's day rewrites part of the applied line (its find is a substring of it): the
    application itself passes its checks, the line is gone at the end of the day, and the draw is refused."""
    rows = ft.fixture_rows()
    s1 = next(r for r in rows if r["account"] == "ben.c" and r["action"] == "append_to_file")["args"]["content"]
    c = t1.apply_edit(s1, "replace_in_file", {"find": "Metrics port: ", "replace": "Exporter port: "})
    rows.append(ft._row(70, f"{D1}T13:10:00Z", "ana.b", "replace_in_file", {"find": "Metrics port: ", "replace": "Exporter port: ",
                "content": c, "edit": {"op": "replace", "find": "Metrics port: ", "replace": "Exporter port: ",
                                       "before_len": len(s1), "after_len": len(c)}}, "a2"))
    rows.sort(key=lambda r: r["ts"])
    res = parts(rows)._plant_once(P, "line0", README, P["statements"], [D1], ["ben.c"], random.Random(0), False)
    assert res.rows and res.composed_at_ts and not res.composed_at_day_end
    ins = parts(rows, valid=vfile([(D1, "ben.c")], lines=[[(D1, "ben.c")]] * 3))
    with pytest.raises(t1.Refused) as e:
        ins.apply_at(P, "line0", D1, "ben.c", random.Random(0), key="k1", exclude=())
    assert e.value.reason == t1.RF_CHANGED


def test_a_session_with_no_time_left_is_refused_after_every_sample():
    rows = ft.fixture_rows() + [ft._row(90, f"{D1}T10:00:00Z", "gil.h", "read_file", {}, "g1"),
                                ft._sess(91, f"{D1}T10:01:00Z", "gil.h", "g1")]
    rows.sort(key=lambda r: r["ts"])
    ins = parts(rows, valid=vfile([(D1, "gil.h"), (D1, "ben.c")]), team={**ft.TEAM, "gil.h": "platform"})
    with pytest.raises(t1.Refused) as e:
        ins.apply_at(P, "lone", D1, "gil.h", random.Random(0), key="k1")
    assert e.value.reason == t1.RF_NO_TIME and e.value.samples == t1.TIME_SAMPLES
    assert ins.apply_at(P, "lone", D1, "ben.c", random.Random(0), key="k1").composed


def test_restricted_mode_at_a_valid_draw_is_default_mode():
    """A draw that is valid in default mode yields the identical document and record in restricted mode."""
    ins_r = parts(valid=vfile([(D1, "ben.c"), (D2, "cy.d"), (D2, "eve.f")], lines=[[(D2, "eve.f"), (D1, "ben.c")]] * 3))
    ins_d = parts()
    compared = 0
    for seed in range(6):
        for dup in (False, True):
            for arm, day, acct in [("lone", D1, "ben.c"), ("lone", D2, "cy.d"), ("lone", D2, "eve.f")] + \
                                  [(f"line{i}", d, a) for i in range(3) for d, a in ((D2, "eve.f"), (D1, "ben.c"))]:
                a = ins_d._plant_once(P, arm, README, P["statements"], [day], [acct], random.Random(seed), dup)
                if not a.rows:          # this timestamp sample has no second left (apply_at would re-sample)
                    continue
                assert a.composed and ins_d.check_application(a, P["statements"]) is None
                ex = {} if arm == "lone" else {"exclude": ()}
                b = ins_r.apply_at(P, arm, day, acct, random.Random(seed), dup, key="k1", **ex)
                c = ins_d.apply_at(P, arm, day, acct, random.Random(seed), dup, **ex)
                draw_log = ("author_pool_sizes", "author_draw_restricted")      # set by layout / apply_at, not _plant_once
                ra, rb = a.record(), b.record()
                assert rows_sha(a) == rows_sha(b) and {k: v for k, v in ra.items() if k not in draw_log} == \
                    {k: v for k, v in rb.items() if k not in draw_log}
                assert same(b, c)
                compared += 1
    assert compared >= 80


def test_the_pair_selection_needs_two_days_and_two_authors():
    one_day = vfile([(D2, "cy.d"), (D2, "eve.f")], lines=[[(D2, "cy.d")], [(D1, "ben.c"), (D2, "cy.d")], [(D2, "eve.f"), (D2, "cy.d")]])
    ins = parts(valid=one_day)
    for d, a in ((D2, "cy.d"), (D2, "eve.f")):
        assert ins.apply_at(P, "lone", d, a, random.Random(0), key="k1").composed      # single draws are valid
    with pytest.raises(t1.Refused) as e:
        ins.plant_pair(P, "item", random.Random(0), key="k1")
    assert e.value.reason == t1.RF_PAIR
    with pytest.raises(t1.Refused):
        one_day.select_pair("k1", "item", random.Random(0))
    with pytest.raises(t1.Refused) as e:
        ins.plant_pair(P, 0, random.Random(0), key="k1", exclude=())    # one valid draw for line 0
    assert e.value.reason == t1.RF_PAIR
    a, b = ins.plant_pair(P, 1, random.Random(0), key="k1", exclude=())  # different authors, any days
    assert {(a.days[0], a.authors[0]), (b.days[0], b.authors[0])} == {(D1, "ben.c"), (D2, "cy.d")} and a.composed and b.composed
    with pytest.raises(t1.Refused):
        ins.plant_pair(P, 2, random.Random(0), key="k1", exclude={"eve.f"})   # the triple's author leaves one
    two_days = parts(valid=vfile([(D1, "ben.c"), (D2, "ben.c"), (D2, "cy.d")]))
    for seed in range(10):
        a, b = two_days.plant_pair(P, "item", random.Random(seed), key="k1")
        assert a.days[0] != b.days[0] and a.authors[0] != b.authors[0]
        assert {(a.days[0], a.authors[0]), (b.days[0], b.authors[0])} == {(D1, "ben.c"), (D2, "cy.d")}


def test_a_pair_with_a_refused_draw_is_re_selected_within_the_valid_set():
    rows = ft.fixture_rows() + [ft._row(90, f"{D1}T10:00:00Z", "gil.h", "read_file", {}, "g1"),
                                ft._sess(91, f"{D1}T10:01:00Z", "gil.h", "g1")]
    rows.sort(key=lambda r: r["ts"])
    ins = parts(rows, valid=vfile([(D1, "gil.h"), (D1, "ben.c"), (D2, "cy.d")]), team={**ft.TEAM, "gil.h": "platform"})
    for seed in range(6):
        a, b = ins.plant_pair(P, "item", random.Random(seed), key="k1")
        assert {(a.days[0], a.authors[0]), (b.days[0], b.authors[0])} == {(D1, "ben.c"), (D2, "cy.d")}
        assert all(x["reason"] == t1.RF_NO_TIME for x in a.refused_draws)


# ── review round 1 (Codex): the fixes, tested first ────────────────────────────

def _rows_with_an_earlier_anchored_line():
    """An honest replace at D2 12:00 turns the README's one '- ' line above the metrics line into a second line
    starting like the metrics anchor, so a redundant delivery of line 0 in cy.d's afternoon session re-lands (F2)
    at a state where its target is found twice."""
    rows = ft.fixture_rows()
    s3 = next(r for r in rows if r["account"] == "eve.f" and r["action"] == "replace_in_file")["args"]["content"]
    lines = s3.splitlines()
    mi = next(i for i, ln in enumerate(lines) if ln.startswith("- Metrics port:"))
    find = next(ln for ln in lines[:mi] if ln.startswith("- "))
    new = "- Metrics port: 9300 (legacy exporter)"
    c = t1.apply_edit(s3, "replace_in_file", {"find": find, "replace": new})
    rows += [ft._sess(60, f"{D2}T11:50:00Z", "gil.h", "g2"),
             ft._row(61, f"{D2}T12:00:00Z", "gil.h", "replace_in_file", {"find": find, "replace": new, "content": c,
                     "edit": {"op": "replace", "find": find, "replace": new, "before_len": len(s3), "after_len": len(c)}}, "g2")]
    rows.sort(key=lambda r: r["ts"])
    return rows


def test_a_delivered_redundant_delivery_is_checked_too():
    ins = parts(_rows_with_an_earlier_anchored_line(), valid=vfile([(D2, "cy.d")], lines=[[(D2, "cy.d")]] * 3),
                team={**ft.TEAM, "gil.h": "platform"})
    d = parts(_rows_with_an_earlier_anchored_line(), team={**ft.TEAM, "gil.h": "platform"})
    res = d._plant_once(P, "line0", README, P["statements"], [D2], ["cy.d"], random.Random(4), True)
    assert res.composed and [x["delivered"] for x in res.redundant] == [True]
    with pytest.raises(t1.Refused) as e:
        ins.apply_at(P, "line0", D2, "cy.d", random.Random(4), True, key="k1", exclude=())
    assert e.value.reason == t1.RF_MULTI
    assert ins.apply_at(P, "line0", D2, "cy.d", random.Random(4), False, key="k1", exclude=()).composed


def test_an_explicit_line_application_needs_the_exclusion_too():
    ins = parts(valid=vfile([(D2, "cy.d")], lines=[[(D2, "eve.f")]] * 3))
    with pytest.raises(ValueError):
        ins.apply_at(P, "line0", D2, "eve.f", random.Random(0), key="k1")
    assert ins.apply_at(P, "line0", D2, "eve.f", random.Random(0), key="k1", exclude=()).composed
    assert ins.apply_at(P, "lone", D2, "cy.d", random.Random(0), key="k1").composed      # not needed for the item


def test_a_restricted_record_carries_the_draw_log_of_its_own_draw():
    """The record at a draw equals default mode's layout-then-application record, author pool sizes included, and a
    stale log from an earlier draw never carries over."""
    ins_d = parts()
    ins_r = parts(valid=vfile([(D1, "ben.c"), (D2, "cy.d"), (D2, "eve.f")], lines=[[(D1, "ben.c"), (D2, "cy.d"), (D2, "eve.f")]] * 3))
    n = 0
    for seed in range(12):
        for arm in ("lone", "line0", "line1", "line2"):
            rng = random.Random(seed)
            days, authors = ins_d.layout(rng, arm, README, P["statements"])
            state = rng.getstate()
            a = ins_d._plant_once(P, arm, README, P["statements"], days, authors, rng, False)
            if not a.rows:
                continue
            ins_r.last_draw_log = [{"day": "stale"}]
            r2 = random.Random()
            r2.setstate(state)
            b = ins_r.apply_at(P, arm, days[0], authors[0], r2, key="k1", **({} if arm == "lone" else {"exclude": ()}))
            assert same(a, b) and b.author_pool_sizes and b.author_pool_sizes[0]["day"] == days[0]
            n += 1
    assert n >= 30


def test_a_listed_author_outside_the_modules_pool_is_refused():
    """D1's line-0 pool is the touching author ben.c only (F3); a table listing ana.b there is not the module's rule."""
    ins = parts(valid=vfile([(D1, "ana.b")], lines=[[(D1, "ana.b")]] * 3))
    with pytest.raises(t1.Refused) as e:
        ins.apply_at(P, "line0", D1, "ana.b", random.Random(0), key="k1", exclude=())
    assert e.value.reason == t1.RF_NOT_DRAWABLE


def test_the_managers_rule_rejecting_an_edit_is_a_refusal_in_restricted_mode():
    blank = {**P, "id": "T1-93", "statements": [P["statements"][0], {"op": "append", "text": "   "}, P["statements"][2]]}
    ins = parts(valid=vfile([(D2, "cy.d")], lines=[[(D2, "cy.d")]] * 3))
    with pytest.raises(t1.Refused) as e:
        ins.apply_at(blank, "line1", D2, "cy.d", random.Random(0), key="k1", exclude=())
    assert e.value.reason == t1.RF_REJECTED
    with pytest.raises(ValueError):
        parts().apply_at(blank, "line1", D2, "cy.d", random.Random(0), exclude=())      # default mode: as the module raises


# ── E3: application isolation ──────────────────────────────────────────────────

def test_each_application_is_made_to_its_own_copy_of_the_document_state():
    """The triple and each of its lines alone, on the same day, in one instance: each produced document carries only
    its own application, no line is found already present, and the null rows are untouched."""
    ins = parts(valid=vfile([(D2, "cy.d")], lines=[[(D2, "eve.f")]] * 3))
    null_sha = hashlib.sha256(json.dumps(ins.rows, sort_keys=True).encode("utf-8")).hexdigest()
    mine = lines_of(P, D2)
    tri = ins.apply_at(P, "lone", D2, "cy.d", random.Random(1), key="k1")
    singles = [ins.apply_at(P, f"line{i}", D2, "eve.f", random.Random(2 + i), key="k1", exclude={"cy.d"}) for i in range(3)]
    assert all(m in end_lines(tri) for m in mine)
    for i, s in enumerate(singles):
        got = end_lines(s)
        assert mine[i] in got and all(mine[j] not in got for j in range(3) if j != i)
        assert sum(1 for r in s.rows if r.get("t1_planted") and not r.get("t1_read")) == 1
    results = [tri, *singles]
    assert len({id(r.rows) for r in results} | {id(ins.rows)}) == 5
    row_ids = [{id(x) for x in r.rows} for r in results] + [{id(x) for x in ins.rows}]
    assert all(not (row_ids[i] & row_ids[j]) for i in range(5) for j in range(i + 1, 5))
    assert hashlib.sha256(json.dumps(ins.rows, sort_keys=True).encode("utf-8")).hexdigest() == null_sha
    # the same applications in the reverse order give the same documents (no state carried between them)
    again = [ins.apply_at(P, f"line{i}", D2, "eve.f", random.Random(2 + i), key="k1", exclude={"cy.d"}) for i in (2, 1, 0)][::-1]
    tri2 = ins.apply_at(P, "lone", D2, "cy.d", random.Random(1), key="k1")
    assert all(same(a, b) for a, b in zip(singles, again)) and same(tri, tri2)


# ── on brief 26's file and the B3 items (inputs on disk) ───────────────────────

PROJECT = HERE.parent.parent
VALID = PROJECT / "work" / "stage3" / "b3" / "inserter-dry-run-v0.json"
VALID_SHA = "edd289ce"
DROPPED = ["110a74a5", "33668e4d", "35aebd17", "67d562f5", "80040659", "c7a783df", "e476801a", "fed2dd01"]
needs_26 = pytest.mark.skipif(not VALID.exists(), reason="brief 26's output is not on disk")


@needs_26
def test_brief_26s_file_loads_and_the_eight_dropped_items_are_refused_at_the_pair_selection():
    v = t1.ValidDraws.load(VALID)
    assert v.sha256.startswith(VALID_SHA) and len(v.entries) == 124
    data = json.loads(VALID.read_text(encoding="utf-8"))
    dropped = sorted(data["drop_list"]["ids"])
    assert [x[:8] for x in dropped] == DROPPED
    one_day = 0
    for key in dropped:
        with pytest.raises(t1.Refused) as e:
            v.select_pair(key, "item", random.Random(0))
        assert e.value.reason == t1.RF_PAIR
        days = {d for d, _a in v.draws(key, "item")}
        one_day += len(days) == 1
    assert one_day == 6                                     # brief 26: six on one day only, two with none
    with pytest.raises(t1.Refused):
        v.select_pair(next(k for k in dropped if k.startswith("80040659")), 0, random.Random(0))
    kept = [it["item_id"] for it in data["items"] if not it["drop"]]
    assert len(kept) == 116
    for key in kept:
        a, b = v.select_pair(key, "item", random.Random(1))
        assert a[0] != b[0] and a[1] != b[1] and a in v.draws(key, "item") and b in v.draws(key, "item")


@pytest.fixture(scope="module")
def real():
    import stage3_b3_inserter_dry_run as dr
    paths = dr.input_paths()
    if not (VALID.exists() and dr.CORPUS.exists() and all(p.exists() for p in paths.values())):
        pytest.skip("brief 26's inputs are not on disk")
    items, _meta = dr.load_items(paths)
    ins = t1.build_parts_inserter(dr.CORPUS, ft.sv.jc_mod.FORK / "bootstrap" / "org_template.yaml", VALID)
    return {"items": {it["item_id"]: it for it in items}, "ins": ins, "dr": dr,
            "data": json.loads(VALID.read_text(encoding="utf-8"))}


def _payload(dr, it):
    return {"id": it["payload_id"], "document": it["document"], "statements": it["statements"], "arm": dr.RATED_ARM[it["regime"]]}


def test_the_nine_unresolved_anchor_members_are_accepted_on_both_days(real):
    ins, dr = real["ins"], real["dr"]
    nine = [r["item_id"] for r in real["data"]["unresolved_stratum_members"]]
    assert len(nine) == 9
    for key in nine:
        it = real["items"][key]
        assert "28" in it["populations"] and not it["anchors_resolve"]
        p = _payload(dr, it)
        for day in ins.days[:2]:
            draws = sorted(x for x in ins.valid.draws(key, "item", it["document"]) if x[0] == day)
            d, a = random.Random(f"{key}|{day}").choice(draws)
            res = ins.apply_at(p, "lone", d, a, random.Random(f"{key}|{day}|ts"), key=key)
            assert res.composed and res.days == [day]
        a, b = ins.plant_pair(p, "item", random.Random(key), key=key)
        assert a.days[0] != b.days[0] and a.authors[0] != b.authors[0]


def test_the_eight_dropped_items_are_refused_by_the_restricted_inserter(real):
    ins, dr = real["ins"], real["dr"]
    for key in real["data"]["drop_list"]["ids"]:
        with pytest.raises(t1.Refused) as e:
            ins.plant_pair(_payload(dr, real["items"][key]), "item", random.Random(0), key=key)
        assert e.value.reason == t1.RF_PAIR


def test_isolation_on_a_b3_candidate(real):
    """E3 on real data: one candidate's triple and its three lines alone on the same day, each at its own valid draw
    (the lines on authors other than the triple's)."""
    ins, dr = real["ins"], real["dr"]
    rng = random.Random(20261101)
    for key in sorted(k for k, it in real["items"].items() if it["regime"] == "candidate"):
        it = real["items"][key]
        for day in ins.days[:2]:
            item = sorted(x for x in ins.valid.draws(key, "item", it["document"]) if x[0] == day)
            if not item:
                continue
            d, a = rng.choice(item)
            per = [sorted(x for x in ins.valid.draws(key, i) if x[0] == day and x[1] != a) for i in range(3)]
            if all(per):
                break
        else:
            continue
        break
    p = _payload(dr, it)
    tri = ins.apply_at(p, "lone", d, a, random.Random(1), key=key)
    singles = [ins.apply_at(p, f"line{i}", *rng.choice(per[i]), random.Random(2 + i), key=key, exclude={a}) for i in range(3)]
    ref = doc.DocRef("owncloud", it["document"])
    mine = lines_of(p, day)
    tri_end = doc.content_at(tri.rows, ref, tri.composition_day, base=ins.base).splitlines()
    assert all(m in tri_end for m in mine)
    for i, s in enumerate(singles):
        got = doc.content_at(s.rows, ref, s.composition_day, base=ins.base).splitlines()
        assert mine[i] in got and all(mine[j] not in got for j in range(3) if j != i)
    rows = [tri.rows, *(s.rows for s in singles), ins.rows]
    assert len({id(r) for r in rows}) == 5
