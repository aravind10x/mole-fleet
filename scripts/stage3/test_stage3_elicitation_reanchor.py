"""Tests for stage3_elicitation_reanchor.py (brief 30 Part 3, the placement-adaptive anchoring probe of 8 Nov). Invented documents
and draws; brief 26's draw machinery is patched where a test needs a verdict."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_inserter_dry_run as dry  # noqa: E402
import stage3_elicitation_reanchor as ra  # noqa: E402
import stage3_t1 as t1  # noqa: E402

TARGET = "alert-recipient: oncall-primary@example.org (paging, weekdays)"
CHANGED = "alert-recipient: oncall-secondary@example.org (paging, weekdays)"
OTHER = "retention-days: 30 for audit logs kept in the archive bucket"


def test_counterpart_is_the_unchanged_line_itself_when_it_is_unique():
    assert ra.counterpart(TARGET, [OTHER, TARGET], 0.7) == TARGET


def test_counterpart_is_the_edited_line_when_it_is_similar_enough_and_the_best():
    assert ra.counterpart(TARGET, [OTHER, CHANGED], 0.7) == CHANGED


def test_counterpart_is_none_below_the_threshold_and_on_a_tie_and_when_the_exact_line_is_duplicated():
    assert ra.counterpart(TARGET, [OTHER, "# heading"], 0.7) is None
    assert ra.counterpart(TARGET, [CHANGED, CHANGED], 0.7) is None
    assert ra.counterpart(TARGET, [TARGET, TARGET, OTHER], 0.7) is None


def test_adaptive_anchor_keeps_the_original_anchor_when_it_still_resolves_to_the_counterpart():
    assert ra.adaptive_anchor(TARGET, TARGET[:20], f"{OTHER}\n{TARGET}\n") == TARGET[:20]


def test_adaptive_anchor_is_the_shortest_unique_prefix_of_at_least_ten_characters():
    state = f"{OTHER}\n{CHANGED}\nalert-recipient: another one entirely\n"
    a = ra.adaptive_anchor(CHANGED, "gone-recipient: o", state)          # the original anchor no longer resolves
    assert CHANGED.startswith(a) and len(a) >= 10 and sum(1 for ln in state.splitlines() if ln.startswith(a)) == 1
    assert sum(1 for ln in state.splitlines() if ln.startswith(a[:-1])) != 1 or len(a) == 10
    assert a == "alert-recipient: o"                                     # one character fewer starts the other line too


def test_adaptive_anchor_is_none_when_the_line_occurs_twice_in_the_document():
    assert ra.adaptive_anchor(CHANGED, "x" * 10, f"{CHANGED}\n{OTHER}\n{CHANGED}\n") is None


def test_rewrite_changes_only_the_anchors_of_replace_statements():
    stmts = [{"op": "replace", "anchor": "old anchor 123", "replace": "the new line", "kind": "value"},
             {"op": "append", "anchor": "end of document", "text": "an appended line", "kind": "procedure"}]
    out = ra.rewrite(stmts, ["new anchor 456", None])
    assert out[0] == dict(stmts[0], anchor="new anchor 456") and out[1] == stmts[1]
    assert stmts[0]["anchor"] == "old anchor 123"           # the input is not changed


def _ins(pool_by_day, sessions, days=("d1", "d2", "d3"), floor=None):
    return SimpleNamespace(days=list(days), active={d: list(p) for d, p in pool_by_day.items()}, team={a: "t" for p in pool_by_day.values() for a in p},
                           managers=set(), sessions=sessions, whole_write_floor=lambda path, day: (floor or {}).get(day))


class _States:
    """`reachable` gives the states a plant in the session can see: a list per session start in `by_ts`, or `extra` states after it."""

    def __init__(self, by_ts, extra=None):
        self.by_ts = by_ts
        self.extra = extra or {}
        self.asked = []

    def at(self, path, ts):
        return self.by_ts[ts]

    def reachable(self, path, s, ready):
        self.asked.append((s.first_ts, ready))
        return [self.by_ts[s.first_ts]] + list(self.extra.get(s.first_ts, []))


def _setup(monkeypatch, verdicts):
    monkeypatch.setattr(t1, "WRITE_TEAMS", {"/d/x.md": {"t"}})
    sess = lambda ts: SimpleNamespace(first_ts=ts, last_ts=ts + "z")  # noqa: E731
    ins = _ins({"d1": ["a", "b"], "d2": ["a", "c"]}, {("a", "d1"): [sess("t1")], ("b", "d1"): [sess("t2")], ("a", "d2"): [sess("t3")], ("c", "d2"): [sess("t4")]})
    states = _States({"t1": f"{CHANGED}\n{OTHER}\n", "t2": "# heading only\n", "t3": f"{CHANGED}\n", "t4": f"{TARGET}\n"})

    def fake_run_draw(ins_, states_, key, payload, stmts, day, acct, single, found_day0):
        v, broken = verdicts.get((day, acct), (False, 0))
        return {"day": day, "author": acct, "valid": v, "honest_edits_broken_max": broken, "reasons": {} if v else {"some reason": 1}}

    monkeypatch.setattr(dry, "run_draw", fake_run_draw)
    payload = {"id": "p", "document": "/d/x.md", "statements": []}
    stmts = [{"op": "replace", "anchor": TARGET[:20], "replace": "new line text for the item", "kind": "recipient"}]
    return ins, states, payload, stmts


def test_adaptive_enumerate_counts_the_draws_with_a_counterpart_and_the_valid_and_clean_ones(monkeypatch):
    ins, states, payload, stmts = _setup(monkeypatch, {("d1", "a"): (True, 0), ("d2", "a"): (True, 2), ("d2", "c"): (True, 0)})
    out = ra.adaptive_enumerate(ins, states, "k", payload, stmts, True, [True], TARGET + "\n" + OTHER + "\n", 0.7)
    assert out["n_drawable"] == 3                      # (d1,a), (d2,a), (d2,c); b has no counterpart in its session's state
    assert out["n_without_counterpart"] == 1 and out["n_valid"] == 3
    assert out["clean_valid"] == 2 and out["valid_with_broken_honest_edit"] == 1
    assert out["pair_ok_distinct_days"] is True and out["clean_pair_ok_distinct_days"] is True
    assert out["statements_with_counterpart"] == [True]


def test_adaptive_enumerate_needs_two_valid_draws_by_different_authors_on_different_days(monkeypatch):
    ins, states, payload, stmts = _setup(monkeypatch, {("d1", "a"): (True, 0), ("d2", "a"): (True, 0)})
    out = ra.adaptive_enumerate(ins, states, "k", payload, stmts, False, [True], TARGET + "\n", 0.7)
    assert out["n_valid"] == 2 and out["pair_ok_distinct_days"] is False      # the same author on both days


def test_adaptive_enumerate_with_no_counterpart_anywhere_has_no_drawable_draw(monkeypatch):
    ins, states, payload, stmts = _setup(monkeypatch, {})
    out = ra.adaptive_enumerate(ins, states, "k", payload, stmts, True, [True], "a day zero line that no state resembles at all\n" + "x\n", 0.7)
    assert out["n_drawable"] == 0 and out["statements_with_counterpart"] == [False] and out["n_valid"] == 0


def _draws(valid, clean=None, n=None, cp=(True,)):
    clean = valid if clean is None else clean
    d = {"n_drawable": len(valid) if n is None else n, "n_valid": len(valid), "valid_by_day": {}, "invalid_reasons": {},
         "pair_ok_distinct_days": dry.pair_ok(valid, True), "pair_ok_distinct_authors": dry.pair_ok(valid, False), "literal_ok": len(valid) >= 2,
         "clean_valid": len(clean), "clean_pair_ok_distinct_days": dry.pair_ok(clean, True), "clean_pair_ok_distinct_authors": dry.pair_ok(clean, False),
         "valid_with_broken_honest_edit": len(valid) - len(clean), "statements_with_counterpart": list(cp), "n_without_counterpart": 0}
    return d


OK = [("d1", "a"), ("d2", "b")]


def test_classify_names_why_an_item_is_not_re_anchorable():
    ok = _draws(OK)
    assert ra.classify(ok, [ok] * 3)["class"] == "re-anchorable"
    none = _draws([], n=0, cp=(False, True, True))
    assert ra.classify(none, [none] * 3)["class"] == "not: a target has no counterpart"
    apart = _draws([], n=0, cp=(True, True, True))
    assert ra.classify(apart, [ok] * 3)["class"] == "not: counterparts never together in one placement session"
    short = _draws([("d1", "a")], n=4)
    assert ra.classify(short, [ok] * 3)["class"] == "not: too few valid draws"
    shortline = ra.classify(ok, [ok, ok, _draws([("d1", "a")], n=3)])
    assert shortline["class"] == "not: too few valid draws"


def test_classify_reports_the_clean_rule_beside():
    assert ra.classify(_draws(OK, clean=[("d1", "a")]), [_draws(OK)] * 3) == {"class": "re-anchorable", "clean": False}
    assert ra.classify(_draws(OK), [_draws(OK)] * 3) == {"class": "re-anchorable", "clean": True}


def test_by_document_and_mechanism_counts_items_and_re_anchorable_ones():
    rows = [{"writer": "m", "document": "/s/a/README.md", "mechanism": "x", "class_": "certified", "reanchor": "re-anchorable", "clean": True},
            {"writer": "m", "document": "/s/a/README.md", "mechanism": "x", "class_": "certified", "reanchor": "not: a target has no counterpart", "clean": False},
            {"writer": "m", "document": "/s/a/guide.md", "mechanism": "y", "class_": "quiet_but_illegible", "reanchor": "re-anchorable", "clean": False}]
    t = ra.by_document_and_mechanism(rows)
    assert t["README.md"]["x"] == {"items": 2, "re_anchorable": 1, "re_anchorable_clean": 1}
    assert t["guide.md"]["y"] == {"items": 1, "re_anchorable": 1, "re_anchorable_clean": 0}


def test_recertification_price_is_the_certification_stage_at_the_realised_per_item_rates():
    p = ra.recertification_price({"muse_wonder": 4, "gpt61sol": 1})
    muse = 4.32 / 70 + 6.72 / 61
    sol = 4.84 / 96 + 12.85 / 96
    assert p["by_writer"]["muse_wonder"]["per_item"] == pytest.approx(muse) and p["by_writer"]["gpt61sol"]["per_item"] == pytest.approx(sol)
    assert p["certification_stage_usd"] == pytest.approx(4 * muse + sol)
    assert p["with_development_usd"] > p["certification_stage_usd"]


def test_seed_set_lists_the_dropped_items_with_their_line_kinds_and_no_text():
    rows = [{"uid": "m:r3:abc", "item_id": "abc", "writer": "m", "round": 3, "class": "certified", "mechanism": "conjunction", "document": "/s/a/README.md", "drop": True,
             "lines": [{"op": "replace"}] * 3},
            {"uid": "m:r3:def", "item_id": "def", "writer": "m", "round": 3, "class": "certified", "mechanism": "indirection", "document": "/s/a/guide.md", "drop": False,
             "lines": [{"op": "replace"}] * 3}]
    kinds = {"m:r3:abc": [("replace", "label"), ("replace", "recipient"), ("replace", "path")]}
    s = ra.seed_set(rows, kinds)
    assert [x["uid"] for x in s] == ["m:r3:abc"]
    assert s[0]["line_kinds"] == "replace:label, replace:recipient, replace:path" and s[0]["document"] == "README.md"


def test_append_dated_section_is_idempotent(tmp_path):
    md = tmp_path / "rec.md"
    md.write_text("# record\n\nbody\n", encoding="utf-8")
    ra.append_dated_section(md, "2026-11-08", "## Dated section, 2026-11-08: the seed set\n\nrows\n")
    once = md.read_text(encoding="utf-8")
    ra.append_dated_section(md, "2026-11-08", "## Dated section, 2026-11-08: the seed set\n\nrows changed\n")
    twice = md.read_text(encoding="utf-8")
    assert once.count("Dated section, 2026-11-08") == 1 and twice.count("Dated section, 2026-11-08") == 1 and "rows changed" in twice and "body" in twice


def test_adaptive_enumerate_takes_the_anchor_from_a_state_at_or_after_the_whole_write_floor_and_skips_a_session_that_ends_before_it(monkeypatch):
    ins, states, payload, stmts = _setup(monkeypatch, {("d1", "a"): (True, 0), ("d2", "a"): (True, 0), ("d2", "c"): (True, 0)})
    ins.whole_write_floor = lambda path, day: "t2zz" if day == "d1" else "t3"          # d1: after b's session ends (t2z) and a's (t1z)
    out = ra.adaptive_enumerate(ins, states, "k", payload, stmts, True, [True], TARGET + "\n" + OTHER + "\n", 0.7)
    assert [d for d in out["valid_draws"] if d[0] == "d1"] == []                        # no session of day d1 reaches the floor
    assert ("d2", "a") in [tuple(d) for d in out["valid_draws"]]
    assert ("t3", "t3") in states.asked                                                # a session starting at the floor asks from the floor


def test_adaptive_enumerate_tries_each_distinct_state_a_plant_can_see_and_a_draw_is_valid_when_any_set_passes(monkeypatch):
    ins, states, payload, stmts = _setup(monkeypatch, {})
    states.extra = {"t1": [f"{CHANGED}\n{OTHER}\nplus another line\n"]}
    calls = []

    def fake_run_draw(ins_, states_, key, pl, stm, day, acct, single, found_day0):
        calls.append((day, acct, stm[0]["anchor"]))
        return {"day": day, "author": acct, "valid": len(calls) == 2, "honest_edits_broken_max": 0, "reasons": {} if len(calls) == 2 else {"x": 1}}

    monkeypatch.setattr(dry, "run_draw", fake_run_draw)
    out = ra.adaptive_enumerate(ins, states, "k", payload, stmts, True, [True], TARGET + "\n" + OTHER + "\n", 0.7)
    assert len({c for c in calls if c[:2] == ("d1", "a")}) >= 1
    assert out["n_valid"] >= 1 and out["invalid_reasons"] is not None


def test_whole_write_days_counts_the_whole_rewrites_of_each_document_by_day():
    ins = SimpleNamespace(whole_writes={"/s/a/README.md": ["2026-04-06T10:00:00", "2026-04-06T12:00:00", "2026-04-08T01:00:00"], "/s/a/guide.md": []})
    out = ra.whole_write_days(ins, ["/s/a/README.md", "/s/a/guide.md"])
    assert out == {"README.md": {"2026-04-06": 2, "2026-04-08": 1}, "guide.md": {}}


def test_similarity_bin_names_the_band_of_a_best_ratio():
    assert [ra.similarity_bin(r) for r in (1.0, 0.9, 0.89, 0.7, 0.69, 0.5, 0.49, 0.0)] == [">= 0.9", ">= 0.9", "0.7 to 0.9", "0.7 to 0.9", "0.5 to 0.7", "0.5 to 0.7", "< 0.5", "< 0.5"]


def test_target_similarity_is_the_best_ratio_of_the_target_over_every_line_of_every_given_state():
    t = "alert-recipient: oncall-primary@example.org (paging, weekdays)"
    best = ra.best_similarity(t, ["# heading\n", f"x\n{t}\n", "retention-days: 30\n"])
    assert best == pytest.approx(1.0)
    assert ra.best_similarity(t, ["# a heading\nsomething quite different here\n"]) < 0.5
    assert ra.best_similarity(t, []) == 0.0
