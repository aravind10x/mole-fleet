"""Offline tests for judge_client.BedrockConverseJudge (2026-10-29, brief 09 amendment: OpenAI models on
Bedrock through the Converse API). No network: the boto3 client is injected."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import judge_client as jc  # noqa: E402

MODEL = "us.openai.gpt-6-sol"


def _resp(text, stop="end_turn", inp=1000, out=200):
    content = [] if text is None else [{"text": text}]
    return {"output": {"message": {"role": "assistant", "content": content}}, "stopReason": stop,
            "usage": {"inputTokens": inp, "outputTokens": out, "totalTokens": inp + out}}


class ClientError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.response = {"Error": {"Code": code, "Message": code}}


class Fake:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def converse(self, **kw):
        self.calls.append(kw)
        item = self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


async def no_sleep(_s):
    return None


def make(script, tmp_path=None, **kw):
    fake = Fake(script)
    j = jc.BedrockConverseJudge((tmp_path / "c.jsonl") if tmp_path else None, MODEL, system="sys", prompt_version="v",
                                client=fake, sleep=no_sleep, verbose=False, region="us-east-1", **kw)
    return j, fake


VERDICT = '{"score": 72, "flag": true, "rationale": "r"}'


def test_classify_converse_outcomes():
    assert jc.classify_converse(_resp(VERDICT))["outcome"] == "scored"
    assert jc.classify_converse(_resp("I cannot help."))["outcome"] == "errored"
    assert jc.classify_converse(_resp(None, stop="max_tokens"))["outcome"] == "errored"
    assert jc.classify_converse(_resp("x", stop="content_filtered"))["outcome"] == "refused"
    assert jc.classify_converse(_resp("x", stop="guardrail_intervened"))["outcome"] == "refused"
    # reasoning blocks are not text
    r = {"output": {"message": {"content": [{"reasoningContent": {"reasoningText": {"text": "hmm"}}}, {"text": VERDICT}]}}, "stopReason": "end_turn", "usage": {}}
    assert jc.classify_converse(r)["score"] == 72


def test_request_shape_record_cost_and_cache(tmp_path):
    j, fake = make([_resp(VERDICT)], tmp_path)
    rec = asyncio.run(j.score("O_diff", "lbl", "packet"))
    kw = fake.calls[0]
    assert kw["modelId"] == MODEL and kw["system"] == [{"text": "sys"}] and kw["messages"][0]["content"][0]["text"] == "packet"
    assert kw["inferenceConfig"] == {"maxTokens": jc.CONVERSE_MAX_TOKENS} and "temperature" not in json.dumps(kw)
    assert rec["outcome"] == "scored" and rec["score"] == 72 and rec["flag"] is True
    assert rec["provider"] == "bedrock-converse" and rec["model"] == MODEL and rec["model_served"] == MODEL
    assert rec["input_tokens"] == 1000 and rec["output_tokens"] == 200 and rec["reasoning_tokens"] is None
    assert abs(rec["cost_usd"] - (1000 * 2.20 + 200 * 11.00) / 1e6) < 1e-12
    assert rec["cache_key"] == jc.cache_key("O_diff", "lbl", "packet") and rec["prompt_version"] == "v"
    assert rec["request_params"]["max_tokens"] == 4000 and rec["request_params"]["api"] == "bedrock-runtime Converse"
    # served from the cache by a second judge; another model's cache is refused
    j2, fake2 = make([], tmp_path)
    assert asyncio.run(j2.score("O_diff", "lbl", "packet"))["score"] == 72 and j2.stats()["cached"] == 1 and not fake2.calls
    assert abs(j2.dollars_cached - rec["cost_usd"]) < 1e-12
    with pytest.raises(ValueError):
        jc.BedrockConverseJudge(tmp_path / "c.jsonl", "global.openai.gpt-6-sol", system="sys", prompt_version="v", client=Fake([]))


def test_reask_on_no_score_then_errored_stays_uncached():
    j, fake = make([_resp("not json"), _resp(VERDICT)])
    rec = asyncio.run(j.score("O_diff", "a", "p"))
    assert rec["outcome"] == "scored" and rec["parse_retries"] == 1 and len(rec["attempts"]) == 2 and rec["input_tokens"] == 2000
    j2, _ = make([_resp("nope"), _resp("nope"), _resp("nope")])
    rec2 = asyncio.run(j2.score("O_diff", "a", "p"))
    assert rec2["outcome"] == "errored" and len(rec2["attempts"]) == 3 and rec2["cache_key"] not in j2.cache
    assert j2.stats()["errored"] == 1 and j2.stats()["parse_retries"] == 2


def test_refusal_is_recorded_not_reasked():
    j, fake = make([_resp("x", stop="content_filtered")])
    rec = asyncio.run(j.score("O_diff", "a", "p"))
    assert rec["outcome"] == "refused" and rec["score"] is None and len(fake.calls) == 1 and rec["cache_key"] in j.cache


def test_abort_codes_throttling_and_transient_errors():
    j, _ = make([ClientError("ValidationException")])
    with pytest.raises(jc.JudgeAborted):
        asyncio.run(j.score("O_diff", "a", "p"))
    assert "ValidationException" in (j.abort or "")
    j2, fake2 = make([ClientError("ThrottlingException"), _resp(VERDICT)])
    assert asyncio.run(j2.score("O_diff", "a", "p"))["score"] == 72 and j2.stats()["n_throttled"] == 1 and len(fake2.calls) == 2
    j3, fake3 = make([ClientError("ThrottlingException")] * 3)
    assert asyncio.run(j3.score("O_diff", "a", "p"))["outcome"] == "errored" and len(fake3.calls) == 3
    j4, fake4 = make([ClientError("InternalServerException"), ClientError("ServiceUnavailableException"), _resp(VERDICT)])
    assert asyncio.run(j4.score("O_diff", "a", "p"))["score"] == 72 and j4.stats()["transient_retries"] == 2


def test_spend_cap_aborts():
    j, _ = make([_resp(VERDICT, inp=1_000_000, out=0), _resp(VERDICT)], spend_cap_usd=1.0)
    asyncio.run(j.score("O_diff", "a", "p"))          # $2.20 paid
    with pytest.raises(jc.JudgeAborted):
        asyncio.run(j.score("O_diff", "b", "p"))
    assert "spend cap" in (j.abort or "")


def test_converse_with_a_parser():   # brief 23
    parse = lambda t: {"answer": t} if t.strip() else None
    c = jc.classify_converse(_resp("It moves the port."), parse=parse)
    assert c["outcome"] == "scored" and c["parsed"] == {"answer": "It moves the port."} and c["finish_reason"] == "end_turn"
    assert jc.classify_converse(_resp("x", stop="content_filtered"), parse=parse)["outcome"] == "refused"
    j, fake = make([_resp("an answer")], parse=parse)
    rec = asyncio.run(j.score("legib-read", "read:r0:ab:whole", "pkt"))
    assert rec["outcome"] == "scored" and rec["parsed"]["answer"] == "an answer"
    assert "temperature" not in fake.calls[0]["inferenceConfig"]
