"""Brief 07i part 2: the additive judge-client amendment for an Opus 5.5 id (adaptive thinking,
output_config.effort, the price entry, max_tokens) leaves the Sonnet path byte for byte unchanged.
No network: the request kwargs are captured through an injected fake client."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import judge_client as jc  # noqa: E402

SON = "anthropic.claude-sonnet-5"
OPUS = "anthropic.claude-opus-5-5"


def test_sonnet_request_params_and_thinking_are_unchanged():
    assert jc.thinking_param(SON) == {"type": "disabled"}
    assert jc.thinking_param("anthropic.claude-sonnet-5-5") == {"type": "between_tools"}
    assert jc.thinking_param("anthropic.claude-opus-4-7") == {"type": "disabled"}
    p = jc.request_params(SON, 900, "sys")
    assert p == {"model": SON, "max_tokens": 900, "thinking": {"type": "disabled"},
                 "system_sha256": jc.sha256("sys"), "system_chars": 3}
    assert "output_config" not in jc.request_params(SON, 900, "sys", effort=None)


def test_opus_path_adaptive_thinking_effort_and_price():
    assert jc.thinking_param(OPUS) == {"type": "adaptive"}
    p = jc.request_params(OPUS, 4000, "sys", effort="high")
    assert p["thinking"] == {"type": "adaptive"} and p["output_config"] == {"effort": "high"} and p["max_tokens"] == 4000
    assert jc.PRICES[OPUS] == {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00}
    assert abs(jc.cost_usd(OPUS, 1_000_000, 100_000) - (4.0 + 2.0)) < 1e-9


class _Resp:
    def __init__(self):
        self.content = [type("B", (), {"type": "thinking", "thinking": ""})(),
                        type("B", (), {"type": "text", "text": '{"score": 12, "flag": false, "rationale": "r"}'})()]
        self.stop_reason = "end_turn"
        self.stop_details = None
        self.model = "claude-opus-5-5"
        self.usage = type("U", (), {"input_tokens": 100, "output_tokens": 300})()


class _Fake:
    def __init__(self):
        self.kwargs = []
        self.messages = self

    async def create(self, **kw):
        self.kwargs.append(kw)
        return _Resp()


def test_opus_client_sends_output_config_and_records_it(tmp_path):
    fake = _Fake()
    c = jc.JudgeClient(cache_path=tmp_path / "c.anthropic-claude-opus-5-5.jsonl", concurrency=1, rpm=100, model=OPUS,
                       spend_cap_usd=None, max_tokens=4000, client=fake, region="us-east-1", verbose=False,
                       system="sys", prompt_version="v", effort="high")
    rec = asyncio.run(c.score("O_diff", "lbl", "packet"))
    kw = fake.kwargs[0]
    assert kw["thinking"] == {"type": "adaptive"} and kw["output_config"] == {"effort": "high"} and kw["max_tokens"] == 4000
    assert rec["outcome"] == "scored" and rec["score"] == 12
    assert rec["request_params"]["output_config"] == {"effort": "high"} and rec["request_params"]["thinking"] == {"type": "adaptive"}
    assert abs(rec["cost_usd"] - (100 * 4.0 + 300 * 20.0) / 1e6) < 1e-9


def test_opus_client_requires_an_effort_and_sonnet_sends_none(tmp_path):
    with pytest.raises(ValueError):
        jc.JudgeClient(cache_path=None, concurrency=1, rpm=100, model=OPUS, spend_cap_usd=None, region="us-east-1", verbose=False)
    fake = _Fake()
    c = jc.JudgeClient(cache_path=None, concurrency=1, rpm=100, model=SON, spend_cap_usd=None, client=fake,
                       region="us-east-1", verbose=False, system="sys", prompt_version="v")
    rec = asyncio.run(c.score("P_own", "lbl", "packet"))
    assert "output_config" not in fake.kwargs[0] and fake.kwargs[0]["thinking"] == {"type": "disabled"}
    assert "output_config" not in rec["request_params"]
