"""Tests for stage3_b3_inserter_dry_run.py (brief 26): the line check, the joint check, the draw enumeration through the
unchanged application module (stage3_t1.py) on test_stage3_t1.py's routine fixture, the drop rule, the reason
mapping and the output guard. Synthetic documents are routine text; no network, nothing sealed.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_inserter_dry_run.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_inserter_dry_run as dr  # noqa: E402
import stage3_t1 as t1  # noqa: E402
import test_stage3_t1 as ft  # noqa: E402  (the inserter's own fixture: README seed, six accounts, three days)

D1, D2, D3 = ft.D1, ft.D2, ft.D3


def rep(anchor, new):
    return {"op": "replace", "anchor": anchor, "replace": new}


def app(text):
    return {"op": "append", "text": text}


# ── the line check ─────────────────────────────────────────────────────────────

def test_replace_found_once_applies_exactly():
    s = "alpha one\nbeta two\n"
    c = dr.check_line(s, rep("beta", "beta three"), "beta three")
    assert c["found"] and c["unique"] and c["diff_equal"] and not c["already_present"] and c["reason"] is None
    assert dr.intended(s, rep("beta", "x"), "x") == "alpha one\nx\n"


def test_absent_target_and_the_reverse_case_reason():
    s = "alpha one\n"
    assert dr.check_line(s, rep("gamma", "g"), "g")["reason"] == dr.R_ABSENT
    assert dr.check_line(s, rep("gamma", "g"), "g", found_at_day0=True)["reason"] == dr.R_CHANGED_BEFORE


def test_two_anchored_lines_are_not_unique():
    c = dr.check_line("beta one\nbeta two\n", rep("beta", "b"), "b")
    assert c["found"] and not c["unique"] and c["anchor_lines"] == 2 and c["reason"] == dr.R_MULTI


def test_resolved_line_occurring_earlier_as_a_substring_is_not_unique_and_misapplies():
    # the manager's replace hits the first substring occurrence: inside line 1, not the anchored line 2
    s = "see foo bar here\nfoo bar\n"
    c = dr.check_line(s, rep("foo", "foo baz"), "foo baz")
    assert c["anchor_lines"] == 1 and c["find_occurrences"] == 2 and not c["unique"]
    assert not c["diff_equal"] and c["reason"] == dr.R_MULTI
    assert t1.apply_edit(s, "replace_in_file", {"find": "foo bar", "replace": "foo baz"}) != dr.intended(s, rep("foo", "x"), "foo baz")


def test_line_already_present():
    assert dr.check_line("a\nb\n", app("b"), "b")["reason"] == dr.R_PRESENT
    assert dr.check_line("a\nb\n", rep("a", "b"), "b")["reason"] == dr.R_PRESENT


def test_append_is_found_once_and_gets_a_line_ending_where_missing():
    for s in ("a\n", "a", ""):
        c = dr.check_line(s, app("z"), "z")
        assert c["found"] and c["unique"] and c["diff_equal"] and c["reason"] is None
    assert dr.intended("a", app("z"), "z") == "a\nz\n"


def test_unknown_state_and_multiline_line():
    assert dr.check_line(None, app("z"), "z")["reason"] == dr.R_UNKNOWN_STATE
    assert dr.check_line("a\n", app("y\nz"), "y\nz")["reason"] == dr.R_MULTILINE


# ── the joint check (the item's lines do not affect one another) ───────────────

def test_independent_lines_compose():
    s = "alpha one\nbeta two\ngamma three\n"
    j = dr.joint_check(s, [rep("alpha", "alpha 1"), app("delta {date}"), rep("gamma", "gamma 3")], D1)
    assert j == {"ok": True, "reason": None}


def test_two_lines_targeting_one_line():
    s = "alpha one\nbeta two\n"
    assert dr.joint_check(s, [rep("alpha", "a1"), rep("alpha o", "a2"), app("z")], D1)["reason"] == dr.R_INTERFERE_SAME


def test_an_earlier_line_changes_a_later_target():
    s = "beta two\nalpha one\n"
    j = dr.joint_check(s, [rep("beta", "alpha zero"), rep("alpha", "alpha 1"), app("z")], D1)
    assert j["reason"] == dr.R_INTERFERE_TARGET


def test_an_earlier_line_adds_a_second_match():
    s = "alpha one\nbeta two\n"
    j = dr.joint_check(s, [app("alpha extra"), rep("alpha", "alpha 1"), app("z")], D1)
    assert j["reason"] == dr.R_INTERFERE_MATCH


def test_an_earlier_line_already_puts_a_later_line_in():
    s = "alpha one\n"
    assert dr.joint_check(s, [app("z"), app("z"), app("y")], D1)["reason"] == dr.R_INTERFERE_PRESENT


def test_a_line_failing_alone_fails_the_joint_check_with_its_reason():
    s = "alpha one\n"
    assert dr.joint_check(s, [rep("gamma", "g"), app("y"), app("z")], D1)["reason"] == dr.R_ABSENT
    # at a draw's reachable state a line failing alone makes the state not applicable: only mutual interference counts
    assert dr.joint_check(s, [rep("gamma", "g"), app("y"), app("z")], D1, alone_required=False) == {"ok": None, "reason": None}
    assert dr.joint_check(s, [app("z"), app("z"), app("y")], D1, alone_required=False)["reason"] == dr.R_INTERFERE_PRESENT


# ── the module's reasons never carry text out ──────────────────────────────────

def test_module_reasons_map_to_codes_without_the_anchor():
    r = dr.map_module_reason("anchor absent at plant time for statement 2 ('- Metrics port:')")
    assert r == dr.R_ABSENT and "Metrics" not in r
    assert dr.map_module_reason("a statement was overwritten before the composition time") == dr.R_CHANGED_AFTER
    assert dr.map_module_reason("session t9 of role 0 has no second left for statement 1") == dr.R_NO_TIME
    assert dr.map_module_reason("something new") == dr.R_UNMAPPED
    assert dr.brief_class(dr.R_CHANGED_AFTER) == dr.brief_class(dr.R_CHANGED_BEFORE) == "target line changed by a later routine edit"
    assert dr.brief_class(dr.R_INTERFERE_SAME) == "other"


def test_the_guard_refuses_guarded_text():
    dr.assert_clean('{"ok": true}', ["- Metrics port: 9106"])
    with pytest.raises(SystemExit):
        dr.assert_clean('{"x": "- Metrics port: 9106"}', ["- Metrics port: 9106"])


# ── the draw rule and the drop rule ────────────────────────────────────────────

def test_pair_rule():
    assert dr.pair_ok([(D1, "a"), (D2, "b")], True)
    assert not dr.pair_ok([(D1, "a"), (D1, "b")], True) and dr.pair_ok([(D1, "a"), (D1, "b")], False)
    assert not dr.pair_ok([(D1, "a"), (D2, "a")], True) and not dr.pair_ok([(D1, "a"), (D2, "a")], False)
    assert not dr.pair_ok([(D1, "a")], False)


def _draws(valid, drawable=None):
    drawable = len(valid) if drawable is None else drawable
    return {"n_drawable": drawable, "n_valid": len(valid), "valid_by_day": {}, "invalid_reasons": {dr.R_MULTI: 1} if drawable > len(valid) else {},
            "pair_ok_distinct_days": dr.pair_ok(valid, True), "pair_ok_distinct_authors": dr.pair_ok(valid, False),
            "literal_ok": len(valid) >= 2}


def test_decide_drops_an_item_short_of_two_placements_or_a_candidate_with_a_short_lone_line():
    ok = _draws([(D1, "a"), (D2, "b")])
    assert dr.decide({}, ok, None)["drop"] is False
    one_day = _draws([(D2, "a"), (D2, "b")], drawable=3)
    d = dr.decide({}, one_day, None)
    assert d["drop"] and not d["drop_literal"] and d["drop_reasons"][0]["why"] == [dr.R_MULTI]
    none = _draws([], drawable=0)
    assert dr.decide({}, none, None)["drop_reasons"][0]["why"] == [dr.R_NO_DRAW]
    lone = [_draws([(D1, "a"), (D1, "b")]), _draws([(D1, "a")], drawable=2), _draws([(D1, "a"), (D2, "c")])]
    d = dr.decide({}, ok, lone)
    assert d["drop"] and [r["what"] for r in d["drop_reasons"]] == ["lone line 2"] and d["drop_literal"]


def test_reverse_forward_and_uniqueness_counts():
    def ln(found0, unique0, d1, d2):
        return {"day0": {"found": found0, "unique": unique0},
                "bank_days": {D1: dict(zip(("states", "found", "unique"), d1)), D2: dict(zip(("states", "found", "unique"), d2))}}
    rows = [{"item_id": "a", "regime": "candidate", "lines": [
                ln(True, True, (3, 0, 0), (2, 0, 0)),        # the reverse case: absent on both drawable days
                ln(True, True, (3, 3, 3), (2, 2, 0)),        # found everywhere, not unique on day 2
                ln(False, False, (3, 3, 3), (2, 2, 2))]},    # the forward case
            {"item_id": "b", "regime": "sham", "lines": [ln(True, True, (3, 1, 1), (2, 2, 2))]}]
    rc = dr.reverse_case(rows, [D1, D2])
    assert rc["count"] == 1 and rc["ids"] == ["a:1"] and rc["by_regime"] == {"candidates": 1}
    assert rc["absent_on_one_drawable_day"] == 1 and rc["absent_in_some_state_of_a_drawable_day"] == 2
    assert rc["forward_case_count"] == 1 and rc["forward_case_found_unique_on_both_days"] == 1
    assert rc["uniqueness"]["not_unique_in_some_state"] == ["a:2"]
    assert rc["uniqueness"]["not_unique_in_every_state_of_a_drawable_day"] == ["a:2"]


# ── through the module, on the inserter's own fixture ──────────────────────────

def _ins():
    return t1.Inserter(ft.fixture_rows(), ft.sv.seed_base(), ft.TEAM, ft.MANAGERS, days=[D1, D2, D3])


def test_states_reachable_inside_a_session_and_per_day():
    ins = _ins()
    st = dr.States(ins)
    b1 = ins.sessions[("ben.c", D1)][0]
    assert len(st.reachable(ft.README, b1, b1.first_ts)) == 2          # before and after ben's 09:10 append
    a2 = ins.sessions[("ana.b", D1)][1]
    assert len(st.reachable(ft.README, a2, a2.first_ts)) == 1
    assert [len(st.day_states(ft.README, d)) for d in (D1, D2, D3)] == [2, 3, 1]


def test_drawable_authors_is_the_modules_pool():
    ins = _ins()
    a1, log1 = dr.drawable_authors(ins, ft.README, D1, ["- Metrics port:"])
    a2, log2 = dr.drawable_authors(ins, ft.README, D2, ["- Metrics port:"])
    assert a1 == ["ben.c"] and log1["restricted"]                      # the touching session is preferred (F3)
    assert a2 == ["cy.d", "eve.f"]
    assert dr.drawable_authors(ins, ft.README, D2, ["- No such line:"])[0] == []


def test_enumerated_draws_of_a_routine_item_are_valid_through_the_module():
    ins = _ins()
    p = ft.PAYLOAD
    out = dr.enumerate_draws(ins, dr.States(ins), "t", p, p["statements"], False, [True, True, True])
    assert out["n_drawable"] == 3 and out["module_runs_placed"] == 3 * dr.RUNS_PER_DRAW
    assert out["module_runs"] == out["module_runs_placed"] + out["module_samples_no_time"]
    assert out["states_checked"] > 0
    assert out["n_valid"] == 3 and out["pair_ok_distinct_days"] and not out["invalid_reasons"]
    assert sorted(map(tuple, out["valid_draws"])) == [(D1, "ben.c"), (D2, "cy.d"), (D2, "eve.f")]
    assert [(pl["draws_found"], pl["draws_unique"], pl["draws_diff_equal"]) for pl in out["per_line"]] == [(3, 3, 3)] * 3


def test_an_item_whose_target_never_resolves_has_no_draw_and_is_dropped():
    ins = _ins()
    p = {**ft.PAYLOAD, "id": "T1-98", "statements": [rep("- No such line:", "x"), *ft.PAYLOAD["statements"][1:]]}
    out = dr.enumerate_draws(ins, dr.States(ins), "t", p, p["statements"], False, [False, True, True])
    assert out["n_drawable"] == 0 and out["n_valid"] == 0
    d = dr.decide({}, out, None)
    assert d["drop"] and d["drop_reasons"][0]["why"] == [dr.R_NO_DRAW]


def test_interfering_lines_invalidate_every_draw():
    ins = _ins()
    p = {**ft.PAYLOAD, "id": "T1-97", "statements": [rep("- Metrics port:", "- Metrics port: 9106"), app("x {date}"),
                                                     rep("- Metrics port:", "- Metrics port: 9107")]}
    out = dr.enumerate_draws(ins, dr.States(ins), "t", p, p["statements"], False, [True, True, True])
    assert out["n_drawable"] == 3 and out["n_valid"] == 0
    assert dr.R_INTERFERE_SAME in out["joint_failures"]


def test_a_module_run_that_stops_part_way_fails_with_the_named_statement():
    # line 1 removes line 3's target; in ben.c's single session the module finds no anchor for line 3 and returns
    # early, without attaching its rows
    ins = _ins()
    p = {**ft.PAYLOAD, "id": "T1-96", "statements": [rep("- Metrics port:", "- Exporter port: 9106"), app("x {date}"),
                                                     rep("- Metrics port:", "- Metrics port: 9107")]}
    r = dr.module_run(ins, p, "lone", p["statements"], D1, "ben.c", dr._rng("t", 0), False, [True, True, True])
    assert not r["ok"] and r["stopped"] and r["lines"][2]["reason"] == dr.R_ABSENT and dr.R_ABSENT in r["reasons"]
    assert 0 not in r["lines"] and 1 not in r["lines"]
    assert dr.statement_named("anchor absent at plant time for statement 2 ('- x')") == 2
    assert dr.statement_named("no session of role 0 on 2026-04-06 has the anchors present") is None
    out = dr.enumerate_draws(ins, dr.States(ins), "t", p, p["statements"], False, [True, True, True])
    assert out["n_valid"] == 0 and dr.R_INTERFERE_SAME in out["joint_failures"]


def test_a_session_with_no_room_fails_for_time_only_after_every_sample():
    # gil.h's one-minute touching session leaves no minute for line 2 after line 1: every sample stops, and the draw
    # fails for time; ben.c's draw on the same day stays valid
    rows = ft.fixture_rows() + [ft._row(90, f"{D1}T10:00:00Z", "gil.h", "read_file", {}, "g1"),
                                ft._sess(91, f"{D1}T10:01:00Z", "gil.h", "g1")]
    rows.sort(key=lambda r: r["ts"])
    ins = t1.Inserter(rows, ft.sv.seed_base(), {**ft.TEAM, "gil.h": "platform"}, ft.MANAGERS, days=[D1, D2, D3])
    p = ft.PAYLOAD
    assert dr.drawable_authors(ins, ft.README, D1, ["- Metrics port:"])[0] == ["ben.c", "gil.h"]
    d = dr.run_draw(ins, dr.States(ins), "t", p, p["statements"], D1, "gil.h", False, [True, True, True])
    assert not d["valid"] and d["module_samples"] == dr.MAX_SAMPLES == d["module_samples_no_time"]
    assert d["reasons"] == {dr.R_NO_TIME: dr.MAX_SAMPLES}
    assert dr.run_draw(ins, dr.States(ins), "t", p, p["statements"], D1, "ben.c", False, [True, True, True])["valid"]


def test_a_lone_line_goes_through_the_one_statement_role_path():
    ins = _ins()
    st = ft.PAYLOAD["statements"][0]
    single = {"id": "T1-99#L1", "document": ft.README, "statements": [st], "arm": "singleton"}
    out = dr.enumerate_draws(ins, dr.States(ins), "t:1", single, [st], True, [True])
    assert out["n_drawable"] == 3 and out["n_valid"] == 3          # presence read here, not the module's three-index composed
    assert out["pair_ok_distinct_authors"] and out["pair_ok_distinct_days"]


def test_a_module_run_compares_the_planted_bytes_with_the_intended_document():
    ins = _ins()
    p = ft.PAYLOAD
    r = dr.module_run(ins, p, "lone", p["statements"], D1, "ben.c", dr._rng("t", 0), False, [True, True, True])
    assert r["ok"] and r["composed"] and all(r["lines"][i]["diff_equal"] for i in range(3))


def test_module_record_finds_every_cited_line_and_hashes_the_class():
    m = dr.module_record()
    assert all(isinstance(v, int) and v > 0 for v in m["lines"].values())
    assert len(m["inserter_class_sha256"]) == 64 and m["candidates"][0]["part_s_uses"]


# ── the real inputs (ids and counts only) ──────────────────────────────────────

@pytest.mark.skipif(not dr.input_paths()["items_v0"].exists(), reason="brief 25's items file is not on disk")
def test_items_load_with_brief_25s_ids_and_the_four_populations():
    items, meta = dr.load_items(dr.input_paths())
    assert len(items) == 124 and meta["stratum_ids_sha256"].startswith("410e7461")
    by = {p: sum(1 for it in items if p in it["populations"]) for p in ("78", "28", "19", "21")}
    assert by == {"78": 78, "28": 28, "19": 19, "21": 21}
    assert sum(1 for it in items if "28" in it["populations"] and not it["anchors_resolve"]) == 9
