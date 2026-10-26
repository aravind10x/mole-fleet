"""Offline tests for judge_openrouter.py (brief 07n part A): classification, cache format, re-asks,
cost accounting and the key-1-only environment. No network."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import judge_client as jc  # noqa: E402
import judge_openrouter as jo  # noqa: E402

PRICES = {"prompt": 0.18 / 1e6, "completion": 20.0 / 1e6}


def _resp(content, finish="stop", inp=100, out=50, reasoning=20, cost=0.0):
    return SimpleNamespace(content=content, finish_reason=finish,
                           usage=SimpleNamespace(input_tokens=inp, output_tokens=out, reasoning_tokens=reasoning, cost_usd=cost))


class Fake:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def complete(self, messages, *, temperature, max_tokens):
        self.calls.append({"messages": messages, "temperature": temperature, "max_tokens": max_tokens})
        return self.responses.pop(0)


def test_classify_outcomes():
    assert jo.classify(_resp('{"score": 12, "flag": false, "rationale": "r"}'))["outcome"] == "scored"
    assert jo.classify(_resp("I cannot help with that."))["outcome"] == "errored"
    assert jo.classify(_resp("", finish="length"))["outcome"] == "errored"
    assert jo.classify(_resp("x", finish="content_filter"))["outcome"] == "refused"


def test_record_shape_cost_and_reask(tmp_path):
    fake = Fake([_resp("not json"), _resp('{"score": 72, "flag": true, "rationale": "r"}', cost=0.0)])
    j = jo.OpenRouterJudge(tmp_path / "c.jsonl", "moonshotai/kimi-k3", system="sys", prompt_version="v", prices=PRICES,
                           price_source="test", client=fake, verbose=False, sleep=lambda s: asyncio.sleep(0))
    rec = asyncio.run(j.score("O_diff", "lbl", "packet"))
    assert rec["outcome"] == "scored" and rec["score"] == 72 and rec["parse_retries"] == 1 and len(rec["attempts"]) == 2
    assert rec["input_tokens"] == 200 and rec["output_tokens"] == 100 and rec["reasoning_tokens"] == 40
    assert abs(rec["cost_usd"] - (200 * PRICES["prompt"] + 100 * PRICES["completion"])) < 1e-12 and rec["cost_source"] == ["list"]
    assert rec["cache_key"] == jc.cache_key("O_diff", "lbl", "packet") and rec["request_params"]["temperature"] == 0.0
    assert rec["request_params"]["max_tokens"] == 4000 and rec["request_params"]["reasoning"] == "provider default"
    assert fake.calls[0]["messages"][0].role == "system" and fake.calls[0]["messages"][1].content == "packet"
    # served from the cache on a second client
    j2 = jo.OpenRouterJudge(tmp_path / "c.jsonl", "moonshotai/kimi-k3", system="sys", prompt_version="v", prices=PRICES,
                            price_source="test", client=Fake([]), verbose=False)
    assert asyncio.run(j2.score("O_diff", "lbl", "packet"))["score"] == 72 and j2.stats()["cached"] == 1
    assert abs(j2.dollars_cached - rec["cost_usd"]) < 1e-12
    # a cache from another model is refused
    with pytest.raises(ValueError):
        jo.OpenRouterJudge(tmp_path / "c.jsonl", "z-ai/glm-5.3", system="sys", prompt_version="v", prices=PRICES, price_source="t", client=Fake([]))


def test_provider_cost_wins_and_errored_is_reasked_then_kept_uncached(tmp_path):
    fake = Fake([_resp('{"score": 5, "flag": false, "rationale": "r"}', cost=0.0123)])
    j = jo.OpenRouterJudge(None, "z-ai/glm-5.3", system="sys", prompt_version="v", prices=PRICES, price_source="t", client=fake, verbose=False)
    rec = asyncio.run(j.score("P_author", "l", "p"))
    assert rec["cost_usd"] == 0.0123 and rec["cost_source"] == ["provider"]
    fake2 = Fake([_resp("nope"), _resp("nope"), _resp("nope")])
    j2 = jo.OpenRouterJudge(None, "z-ai/glm-5.3", system="sys", prompt_version="v", prices=PRICES, price_source="t", client=fake2, verbose=False, sleep=lambda s: asyncio.sleep(0))
    rec2 = asyncio.run(j2.score("P_author", "l", "p"))
    assert rec2["outcome"] == "errored" and len(rec2["attempts"]) == 3 and rec2["cache_key"] not in j2.cache
    assert j2.stats()["errored"] == 1 and j2.stats()["parse_retries"] == 2


def test_spend_cap_aborts_and_fallback_keys_are_dropped(tmp_path, monkeypatch):
    fake = Fake([_resp('{"score": 5, "flag": false, "rationale": "r"}', cost=1.0), _resp('{"score": 5, "flag": false, "rationale": "r"}', cost=1.0)])
    j = jo.OpenRouterJudge(None, "z-ai/glm-5.3", system="sys", prompt_version="v", prices=PRICES, price_source="t", client=fake, verbose=False, spend_cap_usd=0.5)
    asyncio.run(j.score("O_diff", "a", "p"))
    with pytest.raises(jc.JudgeAborted):
        asyncio.run(j.score("O_diff", "b", "q"))
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "x")
    monkeypatch.setenv("OPENROUTER_API_KEY_3", "y")
    assert jo.drop_fallback_keys() == ["OPENROUTER_API_KEY_2", "OPENROUTER_API_KEY_3"]
    assert "OPENROUTER_API_KEY_2" not in os.environ
