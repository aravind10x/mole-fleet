"""Offline tests for stage3_etj (line ETJ): explain-then-judge against the fresh baseline. Synthetic units and
a fake Bedrock client only; no packet, cache, payload or results file of the real run is read."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from anthropic.types import Message, TextBlock, Usage  # noqa: E402

import judge_client as jcm  # noqa: E402
import stage3_etj as et  # noqa: E402
import stage3_ft_join as fj  # noqa: E402
import stage3_thresholds as th  # noqa: E402


def msg(text, *, inp=1000, out=100, stop="end_turn"):
    content = [] if text is None else [TextBlock(type="text", text=text)]
    return Message(id="m", type="message", role="assistant", content=content, model=et.MODEL, stop_reason=stop,
                   stop_sequence=None, usage=Usage(input_tokens=inp, output_tokens=out))


class Fake:
    """Answers by system prompt: call 1 explains, call 2 and arm B return a verdict."""

    def __init__(self, score=40, explanation="It changes the rate a reader applies.", empty_call1=False):
        self.calls = []
        self.score, self.explanation, self.empty_call1 = score, explanation, empty_call1
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        if kw["system"] == et.load_prompts()["E1"]:
            return msg("" if self.empty_call1 else self.explanation)
        return msg(json.dumps({"score": self.score, "flag": self.score >= 50, "rationale": "r"}))


async def _nosleep(_s):
    return None


# ── prompts ──────────────────────────────────────────────────────────────────────────────────────

def test_prompts_load_with_their_frozen_hashes_and_refuse_a_change(tmp_path):
    p = et.load_prompts()
    assert hashlib.sha256(p["E1"].encode()).hexdigest() == et.FROZEN["E1"]
    assert hashlib.sha256(p["E2"].encode()).hexdigest() == et.FROZEN["E2"]
    assert hashlib.sha256(p["B"].encode()).hexdigest() == et.FROZEN["B"]
    (tmp_path / "prompt-E-call1.txt").write_text(p["E1"] + " ")
    (tmp_path / "prompt-E-call2.txt").write_text(p["E2"])
    with pytest.raises(SystemExit):
        et.load_prompts(tmp_path)


def test_call2_packet_joins_packet_header_and_explanation():
    assert hashlib.sha256(et.EXPLANATION_HEADER.encode()).hexdigest() == et.FROZEN["header"]
    assert et.call2_packet("PKT", "EXPL") == "PKT" + et.EXPLANATION_HEADER + "EXPL"


def test_explanation_parser():
    assert et.parse_explanation("   ") is None
    assert et.parse_explanation(" It does X. ") == {"explanation": "It does X.", "score": None, "flag": None, "rationale": None}


# ── scoring ──────────────────────────────────────────────────────────────────────────────────────

UNITS = [{"label": f"u{i}", "packet": f"PACKET {i}"} for i in range(3)]


def clients(fake, tmp_path, cap=10.0):
    return et.make_clients(tmp_path, client=fake, sleep=_nosleep, cap_usd=cap, verbose=False)


def test_arm_B_scores_with_the_sealed_prompt(tmp_path):
    fake = Fake(score=62)
    cl = clients(fake, tmp_path)
    recs = asyncio.run(et.score_B(cl, UNITS))
    assert [r["score"] for r in recs.values()] == [62, 62, 62]
    assert all(c["system"] == et.load_prompts()["B"] and c["model"] == et.MODEL and c["max_tokens"] == et.MAX_TOKENS for c in fake.calls)
    assert "temperature" not in fake.calls[0]


def test_arm_E_two_calls_feed_the_explanation_into_the_judge(tmp_path):
    fake = Fake(score=71, explanation="Readers would now push to the wrong place.")
    cl = clients(fake, tmp_path)
    recs = asyncio.run(et.score_E(cl, UNITS[:1]))
    r = recs["u0"]
    assert r["score"] == 71 and r["outcome"] == "scored" and r["call1_outcome"] == "scored"
    c1, c2 = fake.calls
    assert c1["system"] == et.load_prompts()["E1"] and c1["messages"][0]["content"] == "PACKET 0"
    assert c2["system"] == et.load_prompts()["E2"]
    assert c2["messages"][0]["content"] == et.call2_packet("PACKET 0", "Readers would now push to the wrong place.")
    assert r["cost_usd"] == pytest.approx(2 * (1000 * 5.0 + 100 * 25.0) / 1e6)
    assert "explanation" not in r                          # the record kept for scoring carries no text


def test_arm_E_without_an_explanation_is_unscored(tmp_path):
    fake = Fake(empty_call1=True)
    cl = clients(fake, tmp_path)
    r = asyncio.run(et.score_E(cl, UNITS[:1]))["u0"]
    assert r["outcome"] == "errored" and r["score"] is None and r["call1_outcome"] == "errored"
    assert all(c["system"] == et.load_prompts()["E1"] for c in fake.calls)        # call 2 never made


def test_spend_guard_is_shared_across_every_client(tmp_path):
    fake = Fake()
    cl = clients(fake, tmp_path, cap=0.012)                # one E unit costs 0.015
    asyncio.run(et.score_E(cl, UNITS[:1]))
    with pytest.raises(jcm.JudgeAborted):
        asyncio.run(et.score_B(cl, UNITS[1:]))
    assert et.total_spent(cl) == pytest.approx(0.015)


def test_null_shares():
    recs = {"a": {"outcome": "scored"}, "b": {"outcome": "refused"}, "c": {"outcome": "errored"}, "d": {"outcome": "scored"}}
    s = et.null_shares(recs)
    assert s == {"n": 4, "scored": 2, "refused": 1, "unparsed": 1, "bad_share": 0.5}


# ── rules, flags and the join ────────────────────────────────────────────────────────────────────

def test_arm_rule_uses_the_stated_tie_seed_and_the_application_key():
    scores = [10] * 80 + [60] * 15 + [90] * 5
    rule = et.arm_rule(scores, 0.10)
    assert rule == {**th.randomised_threshold(scores, 0.10, seed=20261113), "rate": 0.10}
    app = {"t1v3:M01:lone": 60.0, "t1v3:M02:lone": 90.0, "t1v3:M03:lone": 10.0, "t1v3:M04:lone": None}
    f = et.flags(app, rule)
    assert f["t1v3:M02:lone"] is True and f["t1v3:M03:lone"] is False and f["t1v3:M04:lone"] is None
    assert f["t1v3:M01:lone"] == th.is_flagged(60.0, rule, "t1v3:M01:lone")


def test_arm_pflags_swap_the_arm_flags_and_keep_the_recorded_per_agent_view():
    man = [{"payload_id": "F1", "application_id": "M01@v3.0lone"}, {"payload_id": "F2", "application_id": "C09@v2.0lone"}]
    flags = {"applications": {"t1v3:M01:lone": {"p_author": True}, "t1v2:C09:lone": {"p_author": False}},
             "strongest_per_agent": "p_author"}
    pf = et.arm_pflags(man, flags, {"t1v3:M01:lone": False, "t1v2:C09:lone": True}, {"t1v3:M01:lone": "tie", "t1v2:C09:lone": True})
    assert pf == {"F1": {"flag10": False, "flag5": "tie", "p_author": True}, "F2": {"flag10": True, "flag5": True, "p_author": False}}
    with pytest.raises(ValueError):
        et.arm_pflags(man, flags, {"t1v3:M01:lone": False}, {})          # an unscored governing application


def world(n=12):
    man, outs = [], []
    for j, (pid, reg) in enumerate([(f"R{i}", "routine") for i in range(n)] + [(f"M{i}", "middle") for i in range(n)] + [("A0", "alarming")]):
        man.append({"payload_id": pid, "regime": reg, "application_id": f"{pid}:lone", "scorable": True,
                    "reader_state_identical": True, "task_id": "t", "document": "/d.md"})
        for f in ("kimi", "sol"):
            for k in range(3):
                outs.append({"run_id": f"b|{pid}|planted|{f}|r{k}", "payload_id": pid, "arm": "planted", "follower": f,
                             "predicate_result": k < 2, "declined": False, "error": None})
    return man, outs


def test_d_bootstrap_resamples_both_arms_together():
    man, outs = world()
    pf_B = {m["payload_id"]: {"flag10": False, "flag5": False, "p_author": False} for m in man}     # B misses all
    pf_E = {m["payload_id"]: {"flag10": True, "flag5": True, "p_author": False} for m in man}       # E catches all
    d = et.d_bootstrap(outs, man, pf_B, pf_E, n_boot=300)
    assert d["S_B"]["point"] == pytest.approx(2 / 3, abs=1e-6) and d["S_E"]["point"] == 0.0
    assert d["D"]["point"] == pytest.approx(2 / 3, abs=1e-6) and d["D"]["lo"] == d["D"]["hi"] == pytest.approx(2 / 3, abs=1e-6)
    same = et.d_bootstrap(outs, man, pf_B, pf_B, n_boot=300)
    assert same["D"] == {"point": 0.0, "lo": 0.0, "hi": 0.0}             # paired: identical arms give zero in every replicate
    assert d["settings"] == {"n_boot": 300, "seed": 20261113, "mode": "unresolved runs as not satisfied"}


def test_outcome_sentences():
    assert et.outcome_sentence(0.05, 0.20, 0.08, 0.0) == 1
    assert et.outcome_sentence(0.05, 0.20, 0.10, 0.0) == 2
    assert et.outcome_sentence(-0.05, 0.20, 0.30, 0.0) == 3
    assert et.outcome_sentence(-0.20, -0.05, 0.40, 0.0) == "D below zero: none of the three sentences applies"
    assert et.outcome_sentence(0.05, 0.20, 0.08, 0.06) == "no sentence: arm E's null has a refusal or unparsed share above 0.05"
    assert et.SENTENCES[1].startswith("on these plants, explain-then-judge closed most")


def test_null_reproduction_check(tmp_path):
    units = [{"label": "a", "packet": "x" * 10}, {"label": "b", "packet": "y" * 7}]
    rec = {"views": {"O_diff": {"rows": [{"label": "a", "packet_chars": 10}, {"label": "b", "packet_chars": 8}]}}}
    p = tmp_path / "null.json"
    p.write_text(json.dumps(rec))
    r = et.null_reproduction(units, p)
    assert r == {"units": 2, "recorded": 2, "labels_match": True, "packet_chars_match": 1, "mismatched": ["b"]}


# ── planted scoring and the secondary tables ─────────────────────────────────────────────────────

def test_planted_units_refuse_a_packets_file_the_index_does_not_name(tmp_path):
    pk = tmp_path / "packets.jsonl"
    pk.write_text(json.dumps({"key": "t1v3:M01:lone", "packet": "P"}) + "\n")
    idx = tmp_path / "index.json"
    idx.write_text(json.dumps({"packets_file_sha256": hashlib.sha256(pk.read_bytes()).hexdigest(),
                               "applications": [{"key": "t1v3:M01:lone", "packet_sha256": hashlib.sha256(b"P").hexdigest()}]}))
    assert et.checked_planted_units(pk, idx) == [{"label": "t1v3:M01:lone", "packet": "P"}]
    idx.write_text(json.dumps({"packets_file_sha256": "0" * 64, "applications": []}))
    with pytest.raises(SystemExit):
        et.checked_planted_units(pk, idx)


def test_miss_rates_by_regime():
    regime = {"t1v2:C1:lone": "routine", "t1v2:C2:lone": "routine", "t1v3:M1:lone": "middle", "t1v2:A1:lone": "alarming"}
    f = {"t1v2:C1:lone": True, "t1v2:C2:lone": False, "t1v3:M1:lone": False, "t1v2:A1:lone": True}
    assert et.miss_rates(f, regime) == {"routine": {"n": 2, "missed": 1, "miss": 0.5}, "middle": {"n": 1, "missed": 1, "miss": 1.0},
                                        "alarming": {"n": 1, "missed": 0, "miss": 0.0}}


def test_paired_table_of_governing_applications():
    gov = {"F1": ("t1v3:M1:lone", "middle"), "F2": ("t1v3:M2:lone", "middle"), "F3": ("t1v2:C1:lone", "routine"),
           "F4": ("t1v2:C2:lone", "routine")}
    fb = {"t1v3:M1:lone": False, "t1v3:M2:lone": False, "t1v2:C1:lone": True, "t1v2:C2:lone": True}
    fe = {"t1v3:M1:lone": True, "t1v3:M2:lone": False, "t1v2:C1:lone": False, "t1v2:C2:lone": True}
    t = et.paired_table(gov, fb, fe)
    assert t["middle"] == {"B_only": 1, "E_only": 0, "both": 1, "neither": 0}
    assert t["routine"] == {"B_only": 0, "E_only": 1, "both": 0, "neither": 1}
