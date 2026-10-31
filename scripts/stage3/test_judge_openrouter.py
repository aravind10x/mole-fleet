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


# ── brief 23 (2026-10-31): parser, temperature null, moderation as a refusal ──

class Status403(Exception):
    status_code = 403


def test_parser_and_null_temperature(tmp_path):
    fake = Fake([_resp("It moves the port.")])
    j = jo.OpenRouterJudge(tmp_path / "c.jsonl", "moonshotai/kimi-k3", system="sys", prompt_version="v", prices=PRICES,
                           price_source="test", client=fake, verbose=False, temperature=None,
                           parse=lambda t: {"answer": t} if t.strip() else None)
    rec = asyncio.run(j.score("legib-read", "read:r0:ab:whole", "pkt"))
    assert rec["outcome"] == "scored" and rec["parsed"] == {"answer": "It moves the port."}
    assert fake.calls[0]["temperature"] is None and rec["request_params"]["temperature"] == "not sent (provider default)"
    assert jo.classify(_resp("x", finish="content_filter"), parse=lambda t: {"a": t})["outcome"] == "refused"


def test_moderation_403_is_a_refusal_only_when_asked(tmp_path):
    class Raising(Fake):
        async def complete(self, messages, *, temperature, max_tokens):
            self.calls.append(1)
            raise Status403("Error code: 403 - Your input was flagged by moderation")
    j = jo.OpenRouterJudge(tmp_path / "c.jsonl", "anthropic/claude-sonnet-5.5", system="sys", prompt_version="v", prices=PRICES,
                           price_source="test", client=Raising([]), verbose=False, moderation_as_refusal=True)
    rec = asyncio.run(j.score("legib-read", "read:r0:ab:whole", "pkt"))
    assert rec["outcome"] == "refused" and rec["finish_reason"] == "moderation_403" and j.abort is None
    j2 = jo.OpenRouterJudge(None, "anthropic/claude-sonnet-5.5", system="sys", prompt_version="v", prices=PRICES,
                            price_source="test", client=Raising([]), verbose=False)
    with pytest.raises(jc.JudgeAborted):
        asyncio.run(j2.score("legib-read", "read:r0:ab:whole", "pkt"))
    plain = Status403("Error code: 403 - key limit")
    assert not jo.is_moderation_403(plain)


def test_score_many_settles_every_call_before_raising(tmp_path):
    class Status400(Exception):
        status_code = 400

    class Mixed(Fake):
        async def complete(self, messages, *, temperature, max_tokens):
            await asyncio.sleep(0.01 if messages[1].content == "bad" else 0.05)
            self.calls.append(messages[1].content)
            if messages[1].content == "bad":
                raise Status400("Error code: 400")
            return _resp('{"score": 1, "flag": false, "rationale": "r"}')
    fake = Mixed([])
    j = jo.OpenRouterJudge(tmp_path / "c.jsonl", "moonshotai/kimi-k3", system="sys", prompt_version="v", prices=PRICES,
                           price_source="test", client=fake, verbose=False, concurrency=4)
    with pytest.raises(jc.JudgeAborted):
        asyncio.run(j.score_many([("v", "a", "bad"), ("v", "b", "ok1"), ("v", "c", "ok2")]))
    assert sorted(fake.calls) == ["bad", "ok1", "ok2"]
    assert len([ln for ln in (tmp_path / "c.jsonl").read_text().splitlines() if ln.strip()]) == 2


def test_api_key_env_selects_one_key_and_survives_the_drop(monkeypatch):   # brief 23
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-one")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "test-key-two")
    seen = []
    import mole.llm.openrouter as orc

    class FakeClient:
        def __init__(self, model, api_key):
            seen.append(api_key)
    monkeypatch.setattr(orc, "OpenRouterClient", FakeClient)
    a = jo.OpenRouterJudge(None, "moonshotai/kimi-k3", system="s", prompt_version="v", prices=PRICES, price_source="t",
                           api_key_env="OPENROUTER_API_KEY_2", verbose=False)
    b = jo.OpenRouterJudge(None, "anthropic/claude-sonnet-5.5", system="s", prompt_version="v", prices=PRICES, price_source="t",
                           api_key_env="OPENROUTER_API_KEY_2", verbose=False)
    a._get_client()
    assert "OPENROUTER_API_KEY_2" not in os.environ   # dropped: the fork client cannot rotate to it
    b._get_client()
    assert seen == ["test-key-two", "test-key-two"]
    jo._STASHED.pop("OPENROUTER_API_KEY_2", None)
