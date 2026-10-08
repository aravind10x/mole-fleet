"""Shared release-judge scaffold (scripts/first_cut_monitors.py): prompt version and the
per-call cost record (tokens_in, tokens_out, dollars) every M2/M3/M4 verdict carries.
Scripted fake LLM client only; no network."""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest

from mole.llm.base import ChatResponse, TokenUsage
from mole.monitors.release import cost

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import first_cut_monitors as fcm  # noqa: E402


class _FakeLLM:
    backend = "fake"
    model_id = "fake/judge"

    def __init__(self, body='{"score": 42, "flag": false, "rationale": "r"}', usage=None):
        self.body, self.usage, self.seen = body, usage, []

    async def complete(self, messages, **_kw):
        self.seen.append(messages)
        if self.usage is None:
            return types.SimpleNamespace(content=self.body)        # client reports no usage
        return ChatResponse(content=self.body, usage=self.usage, model_id=self.model_id)


@pytest.fixture(autouse=True)
def _clean_prices(monkeypatch):
    monkeypatch.setattr(cost, "PRICE_PER_MTOK", {})
    monkeypatch.setattr(cost, "_PRICE_HOOK", None)
    monkeypatch.delenv("JUDGE_PRICE_PER_MTOK", raising=False)


def test_judge_records_provider_cost_and_prompt_version():
    llm = _FakeLLM(usage=TokenUsage(input_tokens=1200, output_tokens=80, cost_usd=0.0031))
    v = asyncio.run(fcm.judge(llm, "packet", label="x"))
    assert v["score"] == 42 and v["flag"] is False
    assert (v["tokens_in"], v["tokens_out"], v["dollars"]) == (1200, 80, 0.0031)
    assert v["cost_source"] == "provider" and v["tokens_estimated"] is False
    assert (v["input_tokens"], v["output_tokens"], v["cost_usd"]) == (1200, 80, 0.0031)  # legacy keys
    assert v["prompt_version"] == fcm.JUDGE_PROMPT_VERSION
    assert llm.seen[0][0].content == fcm.JUDGE_SYSTEM


def test_judge_falls_back_to_price_table_when_provider_reports_no_cost(monkeypatch):
    monkeypatch.setitem(cost.PRICE_PER_MTOK, "fake/judge", (2.0, 8.0))
    llm = _FakeLLM(usage=TokenUsage(input_tokens=1_000_000, output_tokens=500_000, cost_usd=0.0))
    v = asyncio.run(fcm.judge(llm, "packet", label="x"))
    assert v["dollars"] == pytest.approx(2.0 + 4.0) and v["cost_source"] == "price_table"


def test_price_hook_and_env_override(monkeypatch):
    cost.set_price_hook(lambda model, tin, tout: 0.5 if model == "fake/judge" else None)
    llm = _FakeLLM(usage=TokenUsage(input_tokens=10, output_tokens=10))
    v = asyncio.run(fcm.judge(llm, "packet", label="x"))
    assert v["dollars"] == 0.5 and v["cost_source"] == "price_hook"
    cost.set_price_hook(None)
    monkeypatch.setenv("JUDGE_PRICE_PER_MTOK", "1.0,3.0")
    v = asyncio.run(fcm.judge(llm, "packet", label="x"))
    assert v["dollars"] == pytest.approx(10 * 1e-6 + 10 * 3e-6) and v["cost_source"] == "price_env"


def test_judge_without_usage_estimates_tokens_and_marks_unpriced():
    llm = _FakeLLM(usage=None)
    v = asyncio.run(fcm.judge(llm, "p" * 4000, label="x"))
    assert v["tokens_estimated"] is True
    assert v["tokens_in"] >= 1000 and v["tokens_out"] > 0
    assert v["dollars"] == 0.0 and v["cost_source"] == "unpriced"


def test_ensure_cost_fields_backfills_legacy_verdicts():
    v = cost.ensure_cost_fields({"input_tokens": 7, "output_tokens": 3, "cost_usd": 0.01})
    assert (v["tokens_in"], v["tokens_out"], v["dollars"]) == (7, 3, 0.01)
    e = cost.ensure_cost_fields({"error": "boom"})
    assert (e["tokens_in"], e["tokens_out"], e["dollars"]) == (0, 0, 0.0)
