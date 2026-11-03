"""Tests for stage3_elicitation_e1e2.py (brief 30 Part 2): the E1 and E2 item selections, the read and scorer units,
the stops (each run's cap, the pause and the hard stop over both), the key-limit record (numbers only), the per-sample
values under the combined L-target rule, the served-provider summary, the pinned reader's construction, and one run on
fake clients (the off-pin re-issue, scoring only answered reads). On the real files (skipped when absent): the counts,
the rendering against briefs 23 and 25, and E0-5's estimates. Ids and aggregates only."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_e1e2 as e12  # noqa: E402
import stage3_legibility as lg  # noqa: E402

ROOT = HERE.parent.parent


def _row(i, regime, retest=False, source=None, **kw):
    r = {"item_id": i, "regime": regime, "retest": retest, **kw}
    if source:
        r["source"] = source
    return r


# ── the L target ─────────────────────────────────────────────────────────────────────────────────

def test_l_target_rubric_for_test_items_false_for_nulls():
    assert [e12.l_target(r) for r in ("candidate", "v2_conforming", "v3_middle")] == ["rubric"] * 3
    assert [e12.l_target(r) for r in ("control", "sham")] == ["false", "false"]
    with pytest.raises(ValueError):
        e12.l_target("honest_random")


# ── selections ───────────────────────────────────────────────────────────────────────────────────

def test_select_e1_is_the_t1_items_read_once():
    rows = [_row("b", "v2_conforming"), _row("a", "v3_middle"), _row("c", "v2_conforming", retest=True),
            _row("d", "control"), _row("e", "honest_random")]
    got = e12.select_e1(rows, expected=2)
    assert [r["item_id"] for r in got] == ["a", "b"] and all(r["source"] == "b23" for r in got)
    with pytest.raises(SystemExit):
        e12.select_e1(rows, expected=3)


def test_select_e2_is_brief25s_items_and_every_t1_item():
    rows23 = [_row("t1", "v2_conforming"), _row("t2", "v3_middle", retest=True), _row("n", "control")]
    rows25 = [_row("c1", "candidate"), _row("s1", "sham"), _row("k1", "control")]
    got = e12.select_e2(rows23, rows25, expected=5)
    assert [(r["item_id"], r["source"]) for r in got] == [("c1", "b25"), ("k1", "b25"), ("s1", "b25"), ("t1", "b23"), ("t2", "b23")]
    with pytest.raises(SystemExit):
        e12.select_e2(rows23, rows25, expected=6)


def test_select_e2_refuses_an_id_in_both_briefs():
    with pytest.raises(SystemExit):
        e12.select_e2([_row("x", "v2_conforming")], [_row("x", "candidate")], expected=2)


# ── units ────────────────────────────────────────────────────────────────────────────────────────

def test_read_units_e1_three_readers_at_r1():
    u = e12.read_units("e1", [_row("a", "v2_conforming"), _row("b", "v3_middle")])
    assert set(u) == {"kimi", "sol", "sonnet55"}
    assert all(len(v) == 8 and {s for s, _, _ in v} == {1} for v in u.values())
    assert {c for _, _, c in u["sol"]} == set(lg.CONDS)


def test_read_units_e2_pinned_kimi_two_samples():
    u = e12.read_units("e2", [_row("a", "candidate"), _row("b", "sham"), _row("c", "v2_conforming")])
    assert set(u) == {"kimi"} and len(u["kimi"]) == 3 * 2 * 4
    assert {s for s, _, _ in u["kimi"]} == {0, 1}


def test_scorer_units_l_target_two_passes():
    assert e12.scorer_units(_row("a", "candidate")) == [(1, "rubric"), (2, "rubric")]
    assert e12.scorer_units(_row("a", "sham")) == [(1, "false"), (2, "false")]


def test_rubric_text_by_source():
    rub23 = {"test": {"t": "R23"}}
    rub25 = {"rubric": {"c": "R25", "f": "F25"}, "paired": {}, "own": {}}
    assert e12.rubric_text(_row("t", "v2_conforming", source="b23"), "whole", "rubric", rub23, rub25) == "R23"
    assert e12.rubric_text(_row("c", "candidate", source="b25"), "part0", "rubric", rub23, rub25) == "R25"
    assert e12.rubric_text(_row("s", "sham", source="b25", false_target="f"), "whole", "false", rub23, rub25) == "F25"


# ── stops ────────────────────────────────────────────────────────────────────────────────────────

def test_stops():
    assert e12.stop_usd("e1", 0.0) == 6.50
    assert e12.stop_usd("e2", 3.10) == pytest.approx(23.36 - 3.10)            # the pause binds before the cap
    assert e12.stop_usd("e2", 3.10, past_pause=True) == pytest.approx(28.60)   # then the cap, under 35.04 - 3.10
    assert e12.stop_usd("e2", 6.50, past_pause=True) == pytest.approx(28.54)   # the hard stop over both binds
    assert e12.stop_usd("e2", 0.0) == pytest.approx(23.36)


# ── the key-limit record ─────────────────────────────────────────────────────────────────────────

def test_limits_summary_numbers_only():
    key = {"data": {"label": "sk-or-v1-abc...xyz", "limit": 100.0, "limit_remaining": 61.5, "usage": 38.5, "usage_weekly": 12.0,
                    "limit_reset": "weekly", "is_free_tier": False, "extra": "x"}}
    credits = {"data": {"total_credits": 400.0, "total_usage": 300.25}}
    s = e12.limits_summary(key, credits)
    assert "label" not in s["key"] and "extra" not in s["key"]
    assert s["key"]["limit_remaining"] == 61.5 and s["key"]["limit_reset"] == "weekly"
    assert s["account"] == {"total_credits": 400.0, "total_usage": 300.25, "remaining": 99.75}
    assert s["headroom_usd"] == 61.5
    assert e12.limits_summary({"data": {"limit": None, "limit_remaining": None}}, credits)["headroom_usd"] == 99.75


# ── per-sample values ────────────────────────────────────────────────────────────────────────────

def _read(fam_s, item, cond, answer="a"):   # ids are hex: lg.parse_label reads [0-9a-f]+
    return {"cache_key": f"{fam_s}:{item}:{cond}", "label": lg.read_label(fam_s, item, cond), "outcome": "scored",
            "parsed": {"answer": answer}}


def _score(fam, s, item, cond, target, p, score):
    return {"cache_key": f"s{p}:{fam}:{s}:{item}:{cond}:{target}", "label": lg.score_label(p, fam, s, item, cond, target),
            "outcome": "scored", "score": score, "parsed": {"declined": False}}


def test_sample_values_whole_and_max_part_against_the_l_target():
    reads = [_read(0, "c", c) for c in lg.CONDS] + [_read(0, "d", c) for c in lg.CONDS]
    scores = []
    for item, target, vals in (("c", "rubric", {"whole": (1, 1), "part0": (0, 0), "part1": (1, 0), "part2": (0, 0)}),
                               ("d", "false", {"whole": (0, 0), "part0": (0, 0), "part1": (0, 0), "part2": (0, 0)})):
        for c, (a, b) in vals.items():
            scores += [_score("kimi", 0, item, c, target, 1, a), _score("kimi", 0, item, c, target, 2, b)]
    rec = e12.Recs({"kimi": reads}, scores)
    assert e12.sample_values(rec, "kimi", 0, _row("c", "candidate")) == (1.0, 0.5)
    assert e12.sample_values(rec, "kimi", 0, _row("d", "sham")) == (0.0, 0.0)
    assert e12.sample_values(rec, "kimi", 1, _row("c", "candidate")) == (None, None)    # no sample 1


def test_sample_values_none_when_a_part_is_refused():
    reads = [_read(0, "c", c) for c in lg.CONDS]
    reads[2] = {**reads[2], "outcome": "refused", "parsed": {}}
    scores = [_score("kimi", 0, "c", c, "rubric", p, 1) for c in lg.CONDS for p in (1, 2)]
    assert e12.sample_values(e12.Recs({"kimi": reads}, scores), "kimi", 0, _row("c", "candidate")) == (None, None)


# ── served provider and precision ────────────────────────────────────────────────────────────────

def test_served_summary_counts_final_attempt_and_off_pin_attempts():
    on = {"provider": "Wafer", "precision": "mxfp4", "on_pin": True}
    off = {"provider": "Other", "precision": "fp8", "on_pin": False}
    recs = [{"cache_key": "a", "label": "read:r0:a:whole", "outcome": "scored", "served": [on]},
            {"cache_key": "b", "label": "read:r0:b:whole", "outcome": "errored", "served": [off]},
            {"cache_key": "b", "label": "read:r0:b:whole", "outcome": "scored", "served": [on]},
            {"cache_key": "c", "label": "read:r0:c:whole", "outcome": "refused", "served": []}]
    s = e12.served_summary(recs)
    assert s["final_records"] == 3 and s["final_by_provider"] == {"Wafer|mxfp4|on_pin": 2, "none": 1}
    assert s["attempts_off_pin"] == 1 and s["final_off_pin"] == 0
    assert s["per_record"]["read:r0:a:whole"] == {"outcome": "scored", "provider": "Wafer", "precision": "mxfp4", "on_pin": True}


def test_printable_summary_passes_the_print_guard():
    recs = [{"cache_key": "a", "label": "read:r0:a:whole", "outcome": "scored",
             "served": [{"provider": "Sail Research", "precision": "fp4", "on_pin": False}, {"provider": "Wafer", "precision": "mxfp4", "on_pin": True}]}]
    s = {"exp": "e1", "dollars": {"total": 1.0}, "kimi_served": {k: v for k, v in e12.served_summary(recs).items() if k != "per_record"},
         "run": {"read": {"kimi": {"aborted": False, "abort_reason": "free text here"}}, "score": {"aborted": False}}}
    with pytest.raises(ValueError):
        lg.check_safe(lg.strip_reasons(s))           # the provider keys carry '|' and spaces
    p = e12.printable(s)
    lg.check_safe(p)
    assert p["kimi_served"] == {"final_records": 1, "final_on_pin": 1, "attempts_off_pin": 1, "final_off_pin": 0}


# ── the pinned reader ────────────────────────────────────────────────────────────────────────────

def test_pinned_reader_is_on_key_2_with_the_wafer_pin(tmp_path, monkeypatch):
    import judge_openrouter as jo
    import judge_openrouter_pin as pin
    monkeypatch.delenv(jo.REASONING_ENV, raising=False)
    models = {"price_source": "test", "models": {pin.KIMI_MODEL: {"pricing": {"prompt": "0.0000002", "completion": "0.000015"}}}}
    j = e12.make_pinned_kimi(tmp_path / "c.jsonl", models, cap=1.0, guard=None, listing={"Wafer": ["mxfp4"]})
    assert isinstance(j, pin.PinnedOpenRouterJudge) and j.pin == pin.KIMI_K3_WAFER_MXFP4
    assert j.api_key_env == "OPENROUTER_API_KEY_2" and j.temperature is None and j.system == lg.READER_SYSTEM
    assert j.prompt_version == lg.READER_PROMPT_VERSION and j.concurrency == lg.READER_CONCURRENCY


# ── a run on fake clients ────────────────────────────────────────────────────────────────────────

class FakeClient:
    """score_many answers each unit; `fail_first` labels are errored on their first issue (as an off-pin reply is)."""

    def __init__(self, kind, fail_first=(), score=1):
        self.kind, self.fail_first, self.score_value = kind, set(fail_first), score
        self.cache, self.issued, self.spent = {}, [], 0.0

    async def score_many(self, units):
        for view, label, packet in units:
            key = f"{view}|{label}"
            if key in self.cache:
                continue
            self.issued.append(label)
            self.spent += 0.01
            if label in self.fail_first:
                self.fail_first.discard(label)
                continue
            rec = {"cache_key": key, "label": label, "outcome": "scored"}
            rec.update({"parsed": {"answer": "x"}} if self.kind == "read" else {"score": self.score_value, "parsed": {"declined": False}})
            self.cache[key] = rec
        return []

    def total_spent(self):
        return self.spent

    def batch_log(self, path, note=None):
        return {}


def test_run_reissues_errored_reads_and_scores_every_answer(tmp_path):
    rows = [_row("a", "candidate", source="b25"), _row("b", "sham", source="b25", false_target="a")]
    units = {"kimi": [(s, r["item_id"], c) for r in rows for s in (0, 1) for c in lg.CONDS]}
    packets = {(r["item_id"], c): "p" for r in rows for c in lg.CONDS}
    reader = FakeClient("read", fail_first={lg.read_label(1, "a", "part1")})
    scorer = FakeClient("score")
    guard = lg.SpendGuard(10.0)
    guard.clients = [reader, scorer]
    out = asyncio.run(e12.run_experiment(rows, packets, {"kimi": reader}, scorer, lambda row, c, t: "R", units, guard,
                                         tmp_path / "log.jsonl", offset=0))
    assert out["read"]["kimi"]["missing_after"] == 0 and out["read"]["kimi"]["rounds"] == 2
    assert reader.issued.count(lg.read_label(1, "a", "part1")) == 2 and len(set(reader.issued)) == 16
    assert len(scorer.issued) == 16 * 2 and out["score"]["aborted"] is False


def test_run_stops_reissuing_after_the_limit(tmp_path):
    rows = [_row("a", "candidate", source="b25")]
    units = {"kimi": [(0, "a", c) for c in lg.CONDS]}

    class AlwaysFails(FakeClient):
        async def score_many(self, units):
            for _v, label, _p in units:
                self.issued.append(label)
            return []

    reader, scorer = AlwaysFails("read"), FakeClient("score")
    guard = lg.SpendGuard(10.0)
    guard.clients = [reader, scorer]
    out = asyncio.run(e12.run_experiment(rows, {("a", c): "p" for c in lg.CONDS}, {"kimi": reader}, scorer, lambda *a: "R", units,
                                         guard, tmp_path / "log.jsonl", offset=0))
    assert out["read"]["kimi"]["rounds"] == 1 + e12.REISSUE_ROUNDS and out["read"]["kimi"]["missing_after"] == 4
    assert scorer.issued == []


# ── the real files (skipped when absent) ─────────────────────────────────────────────────────────

REAL = (ROOT / "work/stage3/legibility/items-v0.json").exists() and (ROOT / "work/stage3/b3/comprehension/items-v0.json").exists()


@pytest.mark.skipif(not REAL, reason="briefs 23 and 25's item files are not present")
def test_real_counts_and_rendering():
    src = e12.load_sources(ROOT)
    assert src["checks"] and all(src["checks"].values()), src["checks"]
    e1 = e12.select_e1(src["rows23"])
    e2 = e12.select_e2(src["rows23"], src["rows25"])
    assert len(e1) == 38 and len(e2) == 172
    assert {r["regime"] for r in e2 if r["source"] == "b25"} == {"candidate", "control", "sham"}
    assert sum(len(v) for v in e12.read_units("e1", e1).values()) == 3 * 152
    assert len(e12.read_units("e2", e2)["kimi"]) == 1376


@pytest.mark.skipif(not REAL, reason="briefs 23 and 25's caches are not present")
def test_real_estimates_reproduce_e0_5():
    est = e12.e0_5_estimates(ROOT)
    assert est["e1"]["total_usd"] == 3.23 and est["e2"]["total_usd"] == 14.29
