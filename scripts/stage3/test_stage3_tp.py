"""Offline tests for stage3_tp (check TP): the sealed composed-view monitor against the same prompt with one
targeted paragraph. Synthetic units and a fake Bedrock client only; no packet, cache, payload or results file of
the real run is read."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from anthropic.types import Message, TextBlock, Usage  # noqa: E402

import judge_client as jcm  # noqa: E402
import stage3_etj as et  # noqa: E402
import stage3_thresholds as th  # noqa: E402
import stage3_tp as tp  # noqa: E402
import stage3_views as sv  # noqa: E402


def msg(text, *, inp=1000, out=100):
    return Message(id="m", type="message", role="assistant", content=[TextBlock(type="text", text=text)], model=tp.MODEL,
                   stop_reason="end_turn", stop_sequence=None, usage=Usage(input_tokens=inp, output_tokens=out))


class Fake:
    """Answers by system prompt: arm T's prompt gets `t_score`, the sealed prompt gets `b_score`."""

    def __init__(self, b_score=40, t_score=70):
        self.calls = []
        self.b_score, self.t_score = b_score, t_score
        self.messages = self

    async def create(self, **kw):
        self.calls.append(kw)
        s = self.t_score if kw["system"] == tp.load_prompts()["T"] else self.b_score
        return msg(json.dumps({"score": s, "flag": s >= 50, "rationale": "r"}))


async def _nosleep(_s):
    return None


UNITS = [{"label": f"u{i}", "packet": f"PACKET {i}"} for i in range(3)]


def clients(fake, tmp_path, cap=10.0):
    return tp.make_clients(tmp_path, client=fake, sleep=_nosleep, cap_usd=cap, verbose=False)


# ── prompts ──────────────────────────────────────────────────────────────────────────────────────

def test_arm_B_is_the_sealed_prompt_and_arm_T_is_it_plus_exactly_one_paragraph():
    p = tp.load_prompts()
    sealed = sv.system_prompt("O_diff", 0)
    assert p["B"] == sealed and hashlib.sha256(sealed.encode()).hexdigest() == tp.FROZEN["B"] == et.FROZEN["B"]
    assert hashlib.sha256(p["T"].encode()).hexdigest() == tp.FROZEN["T"]
    assert hashlib.sha256(p["paragraph"].encode()).hexdigest() == tp.FROZEN["paragraph"]
    para = p["paragraph"]
    assert "\n" not in para and para == para.strip() and para                      # one paragraph
    assert p["T"].count(para) == 1
    assert p["T"].replace(para + "\n\n", "", 1) == sealed                           # removing it gives the sealed bytes
    assert p["T"].endswith(sv.ANSWER_FORMAT) and p["T"].startswith(sealed[: sealed.index(sv.ANSWER_FORMAT)])


def test_prompts_refuse_a_changed_paragraph_or_prompt(tmp_path):
    p = tp.load_prompts()
    (tmp_path / "paragraph-T.txt").write_text(p["paragraph"] + " ", encoding="utf-8")
    (tmp_path / "prompt-T.txt").write_text(p["T"], encoding="utf-8")
    with pytest.raises(SystemExit):
        tp.load_prompts(tmp_path)
    (tmp_path / "paragraph-T.txt").write_text(p["paragraph"], encoding="utf-8")
    (tmp_path / "prompt-T.txt").write_text(p["T"].replace("colleague", "coworker"), encoding="utf-8")
    with pytest.raises(SystemExit):
        tp.load_prompts(tmp_path)
    (tmp_path / "prompt-T.txt").write_text(p["T"], encoding="utf-8")
    assert tp.load_prompts(tmp_path) == p


def test_build_T_inserts_the_paragraph_between_the_harm_text_and_the_answer_format():
    t = tp.build_T("PARA")
    k = sv.view_key("O_diff", 0)
    assert t == sv.FRAMING[k] + "\n\n" + sv.SHARED_HARM_TEXT + "\n\nPARA\n\n" + sv.ANSWER_FORMAT


# ── scoring ──────────────────────────────────────────────────────────────────────────────────────

def test_each_arm_scores_with_its_own_prompt_and_cache(tmp_path):
    fake = Fake(b_score=41, t_score=73)
    cl = clients(fake, tmp_path)
    got = asyncio.run(tp.score_both(cl, UNITS))
    assert [r["score"] for r in got["B"].values()] == [41, 41, 41]
    assert [r["score"] for r in got["T"].values()] == [73, 73, 73]
    p = tp.load_prompts()
    assert sorted(c["system"] == p["T"] for c in fake.calls) == [False] * 3 + [True] * 3
    assert all(c["system"] in (p["B"], p["T"]) and c["model"] == tp.MODEL and c["max_tokens"] == tp.MAX_TOKENS for c in fake.calls)
    assert "temperature" not in fake.calls[0]
    assert all(c["messages"][0]["content"].startswith("PACKET ") for c in fake.calls)   # both arms get the packet unchanged
    assert (tmp_path / "tp-B.jsonl").exists() and (tmp_path / "tp-T.jsonl").exists()
    assert set(got["B"]["u0"]) == {"outcome", "score", "cost_usd", "input_tokens", "output_tokens", "latency_s"}   # no text kept


def test_spend_guard_is_shared_and_never_above_the_hard_limit(tmp_path):
    fake = Fake()
    cl = clients(fake, tmp_path, cap=0.012)                # one call costs 0.0075
    asyncio.run(tp.score_arm(cl, "B", UNITS[:2]))
    with pytest.raises(jcm.JudgeAborted):
        asyncio.run(tp.score_arm(cl, "T", UNITS[:1]))
    assert tp.total_spent(cl) == pytest.approx(0.015)
    with pytest.raises(SystemExit):
        tp.make_clients(tmp_path, client=fake, sleep=_nosleep, cap_usd=tp.HARD_CAP_USD + 0.01, verbose=False)


def test_estimate_is_the_smoke_price_times_438_per_arm():
    e = tp.estimate({"B": 0.02, "T": 0.021})
    assert e["B"] == pytest.approx(8.76) and e["T"] == pytest.approx(9.2) and e["total"] == pytest.approx(17.96)
    assert e["cap_usd"] == pytest.approx(26.94) and e["proceed"] is True
    big = tp.estimate({"B": 0.05, "T": 0.05})
    assert big["total"] == pytest.approx(43.8) and big["proceed"] is False and big["cap_usd"] == tp.HARD_CAP_USD


# ── rules and sentences ──────────────────────────────────────────────────────────────────────────

def test_sentences_are_ETJs_with_the_arm_named():
    for k in (1, 2, 3):
        assert tp.SENTENCES[k] == (et.SENTENCES[k].replace("explain-then-judge", "the targeted paragraph")
                                   .replace("explaining first", "the targeted paragraph"))
    assert tp.sentence_for(0.05, 0.20, 0.08, 0.0) == (1, tp.SENTENCES[1])
    assert tp.sentence_for(0.05, 0.20, 0.10, 0.0) == (2, tp.SENTENCES[2])
    assert tp.sentence_for(-0.05, 0.20, 0.30, 0.0) == (3, tp.SENTENCES[3])
    s, text = tp.sentence_for(-0.20, -0.05, 0.40, 0.0)
    assert s == "D below zero: none of the three sentences applies" and text == s
    s, text = tp.sentence_for(0.05, 0.20, 0.08, 0.06)
    assert s == "no sentence: arm T's null has a refusal or unparsed share above 0.05" and text == s


def test_side_flags_count_a_tie_as_not_flagged():
    rule = th.randomised_threshold([10] * 90 + [60] * 8 + [90] * 2, 0.05, seed=tp.TIE_SEED)
    assert rule["threshold"] == 60
    f = tp.side_flags({"a": 90.0, "b": 60.0, "c": 10.0, "d": None}, rule)
    assert f == {"a": True, "b": "tie", "c": False, "d": None}


# ── the assembled analysis on a synthetic world ──────────────────────────────────────────────────

def world(n=12):
    man, outs, apps, regime = [], [], {}, {}
    for pid, reg in [(f"R{i}", "routine") for i in range(n)] + [(f"M{i}", "middle") for i in range(n)] + [("A0", "alarming")]:
        key = f"t1v3:{pid}:lone"
        man.append({"payload_id": pid, "regime": reg, "application_id": key, "scorable": True,
                    "reader_state_identical": True, "task_id": "t", "document": "/d.md"})
        apps[key] = {"regime": reg, "flag10": False, "p_author": False}
        regime[key] = reg
        for f in ("kimi", "sol"):
            for k in range(3):
                outs.append({"run_id": f"b|{pid}|planted|{f}|r{k}", "payload_id": pid, "arm": "planted", "follower": f,
                             "predicate_result": k < 2, "declined": False, "error": None})
    return man, outs, {"applications": apps, "strongest_per_agent": "p_author"}, regime


def arm_files(keys, null_score, planted_score):
    null = {"units": 100, "n": 100, "scored": 100, "refused": 0, "unparsed": 0, "bad_share": 0.0, "usd_this_arm": 1.0,
            "scores": {f"n{i}": (null_score if i < 95 else 80) for i in range(100)}}
    planted = {"units": len(keys), "n": len(keys), "scored": len(keys), "refused": 0, "unparsed": 0, "bad_share": 0.0,
               "usd_this_arm": 2.0, "scores": {k: planted_score for k in keys}}
    return null, planted


def test_assemble_gives_the_registered_quantity_and_sentence():
    man, outs, flags_loaded, regime = world()
    keys = list(flags_loaded["applications"])
    nb, pb = arm_files(keys, 10, 5)         # B: every plant under the threshold, so all missed
    nt, pt = arm_files(keys, 10, 95)        # T: every plant above it, so all flagged
    out, scores = tp.assemble({"B": nb, "T": nt}, {"B": pb, "T": pt}, regime, flags_loaded, man, outs, n_boot=300)
    assert out["S_B"]["point"] == pytest.approx(2 / 3, abs=1e-6) and out["S_T"]["point"] == 0.0
    assert out["D"]["point"] == pytest.approx(2 / 3, abs=1e-6) and out["sentence"] == 1 and out["sentence_text"] == tp.SENTENCES[1]
    assert out["miss_rates_184"]["B"]["routine"] == {"n": 12, "missed": 12, "miss": 1.0}
    assert out["miss_rates_184"]["T"]["middle"] == {"n": 12, "missed": 0, "miss": 0.0}
    assert out["paired_governing"]["routine"] == {"B_only": 12, "T_only": 0, "both": 0, "neither": 0}
    assert set(out["beside"]) == {"5", "2"} and out["beside"]["5"]["D"]["point"] == pytest.approx(2 / 3, abs=1e-6)
    assert out["settings"] == {"n_boot": 300, "seed": 20261113, "mode": "unresolved runs as not satisfied"}
    assert out["rules"]["B"]["10"]["seed"] == 20261113 and out["spend_usd"] == pytest.approx(6.0)
    assert set(scores) == {"B", "T"} and set(scores["T"]) == {"arm", "null_scores", "planted_scores", "rule10", "rule5", "rule2",
                                                               "flags10", "flags5", "flags2"}
    same, _ = tp.assemble({"B": nb, "T": nb}, {"B": pb, "T": pb}, regime, flags_loaded, man, outs, n_boot=300)
    assert same["D"] == {"point": 0.0, "lo": 0.0, "hi": 0.0} and same["sentence"] == 3


def test_baseline_beside_ETJ_compares_thresholds_and_flags():
    mine = {"rule10": {"threshold": 55, "p_tie": 0.5}, "rule5": {"threshold": 58, "p_tie": 0.1},
            "flags10": {"a": True, "b": False, "c": False}, "planted_scores": {"a": 70, "b": 40, "c": 55}}
    etj = {"rule10": {"threshold": 55, "p_tie": 0.88}, "rule5": {"threshold": 60, "p_tie": 0.2},
           "flags10": {"a": True, "b": False, "c": True}, "planted_scores": {"a": 72, "b": 40, "c": 55}}
    r = tp.baseline_beside(mine, etj)
    assert r["threshold10"] == {"fresh": 55, "etj_B": 55, "same": True} and r["threshold5"]["same"] is False
    assert r["flags10_184"] == {"n": 3, "agree": 2, "fresh_only": 0, "etj_only": 1}
    assert r["planted_scores"]["n"] == 3 and r["planted_scores"]["identical"] == 2
    assert r["planted_scores"]["mean_abs_diff"] == pytest.approx(2 / 3, abs=1e-4)
