"""Per-call deadline on the OpenRouter client (brief 07e, prefix_rw_v2b day 3, 2026-10-22):
one provider request hung for 100+ minutes in a socket read that the httpx read timeout never
ended, and the runner's day bucket waited on it. The fix is a harness parameter, not a world
parameter: an overall deadline around the thread call (OPENROUTER_CALL_DEADLINE_S, default
600 s) raised as a retryable timeout, and that specific error capped at three attempts before
the session dies as an llm_error (a request that hangs three times will hang a fourth)."""
from __future__ import annotations

import asyncio
import time

import pytest

from mole.llm import retry as R
from mole.llm.base import ChatMessage, ChatResponse, TokenUsage
from mole.llm.openrouter import CallDeadlineError, OpenRouterClient


def _client(monkeypatch, post):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    c = OpenRouterClient(model="m")

    class FakeHTTP:
        def post(self, *a, **k):
            return post()
    c._client = FakeHTTP()
    return c


def test_a_call_that_never_returns_raises_the_deadline_error_within_the_deadline(monkeypatch):
    monkeypatch.setenv("OPENROUTER_CALL_DEADLINE_S", "0.3")

    def hang():
        time.sleep(3)
        raise AssertionError("not reached by the caller")
    c = _client(monkeypatch, hang)
    t0 = time.monotonic()
    with pytest.raises(CallDeadlineError) as e:
        asyncio.run(c.complete([ChatMessage(role="user", content="hi")]))
    assert time.monotonic() - t0 < 2.0
    assert "OPENROUTER_CALL_DEADLINE_S" in str(e.value) and "0.3" in str(e.value)


def test_the_default_deadline_is_ten_minutes(monkeypatch):
    monkeypatch.delenv("OPENROUTER_CALL_DEADLINE_S", raising=False)
    from mole.llm.openrouter import call_deadline_s
    assert call_deadline_s() == 600.0
    monkeypatch.setenv("OPENROUTER_CALL_DEADLINE_S", "42")
    assert call_deadline_s() == 42.0


def test_the_deadline_error_is_retryable_like_a_timeout():
    assert R.is_retryable(CallDeadlineError("x"), R.RetryPolicy())
    assert issubclass(CallDeadlineError, TimeoutError)


class _Inner:
    backend = "fake"
    model_id = "m"

    def __init__(self, fails: int):
        self.fails, self.calls = fails, 0

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None, seed=None):
        self.calls += 1
        if self.calls <= self.fails:
            raise CallDeadlineError("openrouter: no response within 1s")
        return ChatResponse(content="ok", tool_calls=[], usage=TokenUsage(), backend="fake", model_id="m")


async def _nosleep(_s):
    return None


def test_three_deadline_hits_end_the_session_even_under_unlimited_retries():
    inner = _Inner(fails=99)
    rc = R.RetryingLLMClient(inner, R.RetryPolicy(max_attempts=0), sleep=_nosleep)   # unlimited
    with pytest.raises(CallDeadlineError):
        asyncio.run(rc.complete([ChatMessage(role="user", content="hi")]))
    assert inner.calls == 3


def test_two_deadline_hits_then_success_recovers():
    inner = _Inner(fails=2)
    rc = R.RetryingLLMClient(inner, R.RetryPolicy(max_attempts=40), sleep=_nosleep)
    out = asyncio.run(rc.complete([ChatMessage(role="user", content="hi")]))
    assert out.content == "ok" and inner.calls == 3


def test_other_transient_errors_keep_the_configured_cap():
    class Flaky(_Inner):
        async def complete(self, messages, **kw):
            self.calls += 1
            if self.calls <= self.fails:
                raise ConnectionError("reset")
            return ChatResponse(content="ok", tool_calls=[], usage=TokenUsage(), backend="fake", model_id="m")
    inner = Flaky(fails=5)
    rc = R.RetryingLLMClient(inner, R.RetryPolicy(max_attempts=40), sleep=_nosleep)
    assert asyncio.run(rc.complete([ChatMessage(role="user", content="hi")])).content == "ok"
    assert inner.calls == 6
