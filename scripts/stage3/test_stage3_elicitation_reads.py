"""Tests for stage3_elicitation_reads.py (brief 30 Part 3: development and certification reads on a converted writer
round). The pure parts only: which units a phase reads, how reader and scorer records become per-item statistics, and
the cache separation of the two phases. Synthetic records; no model call, no key, no item."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_reads as rd  # noqa: E402
import stage3_legibility as lg  # noqa: E402

ROWS = [{"item_id": "a1", "regime": "v2_conforming", "retest": False},
        {"item_id": "a2", "regime": "v2_conforming", "retest": False},
        {"item_id": "a3", "regime": "v2_conforming", "retest": False}]


def _read(fam, s, item, cond, answer="a"):
    lab = lg.read_label(s, item, cond)
    return {"label": lab, "cache_key": lab, "outcome": "scored", "parsed": {"answer": answer}}


def _score(fam, s, item, cond, p, score):
    lab = lg.score_label(p, fam, s, item, cond, "rubric")
    return {"label": lab, "cache_key": lab, "outcome": "scored", "score": score, "parsed": {}}


def test_phases_read_one_and_two_samples_and_name_their_caches_apart(tmp_path):
    assert rd.PHASES["dev"]["samples"] == (0,) and rd.PHASES["cert"]["samples"] == (0, 1)
    a = rd.phase_dir(tmp_path, "opus55", 1, "dev")
    b = rd.phase_dir(tmp_path, "opus55", 1, "cert")
    assert a != b and a.name == "dev" and b.name == "cert"
    assert "r1" in str(a) and "opus55" in str(a)
    with pytest.raises(KeyError):
        rd.phase_dir(tmp_path, "opus55", 1, "other")


def test_the_two_readers_follow_the_writer():
    assert rd.reader_names("opus55") == ("kimi", "sol")
    assert rd.reader_names("gpt61sol") == ("kimi", "sonnet55")


def test_units_cover_every_item_condition_and_sample_of_the_phase_and_only_the_named_items():
    u = rd.units_for(ROWS, ("kimi", "sol"), (0, 1))
    assert set(u) == {"kimi", "sol"}
    assert len(u["kimi"]) == 3 * 4 * 2
    assert {c for _, _, c in u["kimi"]} == set(lg.CONDS)
    u2 = rd.units_for(ROWS, ("kimi", "sol"), (0,), only_ids={"a2"})
    assert {i for _, i, _ in u2["sol"]} == {"a2"} and len(u2["sol"]) == 4


def test_units_refuse_an_id_that_is_not_in_the_round():
    with pytest.raises(ValueError):
        rd.units_for(ROWS, ("kimi", "sol"), (0,), only_ids={"NOPE"})


def _records(whole, parts, fam="kimi", item="a1", s=0, passes=(1, 2)):
    reads, scores = [], []
    for cond in lg.CONDS:
        reads.append(_read(fam, s, item, cond))
        v = whole if cond == "whole" else parts[lg.PARTS.index(cond)]
        for p in passes:
            scores.append(_score(fam, s, item, cond, p, v))
    return reads, scores


def test_collect_gives_d_whole_and_the_maximum_part_per_sample_from_the_two_scorer_passes():
    reads, scores = _records(1, [0, 0, 1])
    rec = rd.records({"kimi": reads}, scores)
    got = rd.collect(rec, ROWS[:1], ("kimi",), (0,))
    g = got["a1"]["kimi"]
    assert (g["D_whole"], g["D_part"], g["status"]) == ([1.0], [1.0], ["computed"])


def test_collect_leaves_none_where_a_read_was_refused_or_missing_never_a_zero():
    reads, scores = _records(1, [0, 0, 0])
    reads[1] = {"label": reads[1]["label"], "cache_key": reads[1]["label"], "outcome": "refused", "parsed": {}}
    scores = [s for s in scores if ":part0:" not in s["label"]]
    rec = rd.records({"kimi": reads}, scores)
    got = rd.collect(rec, ROWS[:1], ("kimi",), (0,))["a1"]["kimi"]
    assert got["D_part"] == [None] and got["D_whole"] == [1.0] and got["status"][0] != "computed"


def test_collect_mean_of_two_passes_is_half_when_they_disagree():
    reads, _ = _records(1, [0, 0, 0])
    scores = []
    for cond in lg.CONDS:
        scores.append(_score("kimi", 0, "a1", cond, 1, 1 if cond == "whole" else 0))
        scores.append(_score("kimi", 0, "a1", cond, 2, 0))
    got = rd.collect(rd.records({"kimi": reads}, scores), ROWS[:1], ("kimi",), (0,))["a1"]["kimi"]
    assert got["D_whole"] == [0.5]


def test_class_inputs_build_the_item_shape_the_classifier_takes():
    reads, scores = _records(1, [0, 0, 0])
    got = rd.collect(rd.records({"kimi": reads}, scores), ROWS[:1], ("kimi",), (0,))
    got["a1"]["sol"] = {"D_whole": [1.0], "D_part": [0.0], "status": ["computed"]}
    items = rd.class_inputs(got, {"a1": True}, ("kimi", "sol"))
    assert items == [{"id": "a1", "gate_i": True, "readers": {"kimi": {"D_whole": [1.0], "D_part": [0.0]},
                                                              "sol": {"D_whole": [1.0], "D_part": [0.0]}}}]


def test_class_inputs_refuse_an_item_with_no_gate_i_verdict():
    with pytest.raises(ValueError):
        rd.class_inputs({"a1": {}}, {}, ("kimi", "sol"))


# ---- the wiring through E2's run_experiment, with stub clients (no network) ---------------------------------------

class _Stub:
    """The client interface run_units and the runner use: score_many, batch_log, cache, cache_path, total_spent."""

    def __init__(self, role, whole=1, part=0):
        self.cache, self.role, self.whole, self.part, self.cache_path, self.calls = {}, role, whole, part, None, 0

    async def score_many(self, units):
        for view, label, packet in units:
            self.calls += 1
            rec = {"label": label, "cache_key": label, "outcome": "scored", "cost_usd": 0.001}
            if self.role == "read":
                rec["parsed"] = {"answer": "an answer"}
            else:
                rec["score"] = self.whole if label.endswith(":whole:rubric") else self.part
                rec["parsed"] = {}
            self.cache[label] = rec

    def batch_log(self, log, note=""):
        pass

    def total_spent(self):
        return 0.001 * len(self.cache)


def test_run_round_reads_every_unit_scores_two_passes_and_collects(tmp_path):
    import asyncio
    packets = {(r["item_id"], c): f"packet {r['item_id']} {c}" for r in ROWS for c in lg.CONDS}
    rub = {r["item_id"]: "the composed effect" for r in ROWS}
    readers = {"kimi": _Stub("read"), "sonnet55": _Stub("read")}
    scorer = _Stub("score", whole=1, part=0)
    guard = lg.SpendGuard(10.0)
    guard.clients = list(readers.values()) + [scorer]
    out = asyncio.run(rd.run_round(ROWS, packets, readers, scorer, rub, ("kimi", "sonnet55"), (0, 1), guard, tmp_path / "log.jsonl"))
    assert out["run"]["read"]["kimi"]["missing_after"] == 0 and out["run"]["read"]["sonnet55"]["missing_after"] == 0
    assert readers["kimi"].calls == 3 * 4 * 2          # three items, four conditions, two samples
    assert scorer.calls == 2 * 3 * 4 * 2 * 2           # two readers, then the same, two passes
    c = out["collected"]
    g = c["a1"]["kimi"]
    assert (g["D_whole"], g["D_part"], g["status"]) == ([1.0, 1.0], [0.0, 0.0], ["computed", "computed"])
    assert set(c) == {"a1", "a2", "a3"}


def test_run_round_only_ids_limits_the_reads_to_the_named_items(tmp_path):
    import asyncio
    packets = {(r["item_id"], c): "p" for r in ROWS for c in lg.CONDS}
    readers = {"kimi": _Stub("read"), "sol": _Stub("read")}
    scorer = _Stub("score")
    guard = lg.SpendGuard(10.0)
    guard.clients = list(readers.values()) + [scorer]
    out = asyncio.run(rd.run_round(ROWS, packets, readers, scorer, {r["item_id"]: "x" for r in ROWS}, ("kimi", "sol"), (0,), guard,
                                   tmp_path / "log.jsonl", only_ids={"a2"}))
    assert set(out["collected"]) == {"a2"} and readers["kimi"].calls == 4


def test_a_spend_stop_leaves_the_run_aborted_and_reports_it(tmp_path):
    import asyncio
    packets = {(r["item_id"], c): "p" for r in ROWS for c in lg.CONDS}
    readers = {"kimi": _Stub("read"), "sol": _Stub("read")}
    scorer = _Stub("score")
    guard = lg.SpendGuard(0.0)            # the stop is already reached
    guard.clients = list(readers.values()) + [scorer]
    out = asyncio.run(rd.run_round(ROWS, packets, readers, scorer, {r["item_id"]: "x" for r in ROWS}, ("kimi", "sol"), (0,), guard,
                                   tmp_path / "log.jsonl"))
    assert any(v["aborted"] for v in out["run"]["read"].values())
    assert out["run"]["score"].get("skipped") is True


# ---- per-condition scores (the feedback needs each statement's own part score) and collecting from a cache directory ----

def test_collect_carries_each_conditions_own_score_per_sample():
    reads, _ = _records(1, [0, 0, 1])
    scores = []
    vals = {"whole": (1, 1), "part0": (0, 0), "part1": (1, 0), "part2": (1, 1)}
    for cond, (p1, p2) in vals.items():
        scores.append(_score("kimi", 0, "a1", cond, 1, p1))
        scores.append(_score("kimi", 0, "a1", cond, 2, p2))
    got = rd.collect(rd.records({"kimi": reads}, scores), ROWS[:1], ("kimi",), (0,))["a1"]["kimi"]
    assert got["cond_scores"] == [{"whole": 1.0, "part0": 0.0, "part1": 0.5, "part2": 1.0}]


def test_collect_dir_reads_the_phase_caches_and_equals_collect_on_the_same_records(tmp_path):
    import json as _json
    reads, scores = _records(1, [0, 0, 1])
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "judge-cache.legibility.read.kimi.moonshotai_kimi-k3.jsonl").write_text("\n".join(_json.dumps(r) for r in reads) + "\n")
    (cache / "judge-cache.legibility.score.anthropic-claude-sonnet-5.jsonl").write_text("\n".join(_json.dumps(r) for r in scores) + "\n")
    got = rd.collect_dir(tmp_path, ROWS[:1], ("kimi",), (0,))
    want = rd.collect(rd.records({"kimi": reads}, scores), ROWS[:1], ("kimi",), (0,))
    assert got == want and got["a1"]["kimi"]["D_part"] == [1.0]
