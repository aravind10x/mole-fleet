"""OpenRouter client rotates to OPENROUTER_API_KEY_2 on a 401/402 and 402 trips the breaker."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from mole.generator.run import _is_auth_error
from mole.llm.base import ChatMessage
from mole.llm.openrouter import OpenRouterClient


class _Err(Exception):
    def __init__(self, status):
        super().__init__(f"Error code: {status} - requires more credits")
        self.status_code = status


def test_402_is_an_auth_class_failure():
    assert _is_auth_error(_Err(402))
    assert _is_auth_error(RuntimeError("Error code: 402 - {'error': {'message': 'This request requires more credits'}}"))
    assert not _is_auth_error(RuntimeError("Error code: 429"))


def test_client_rotates_key_on_402(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-one")
    monkeypatch.setenv("OPENROUTER_API_KEY_2", "key-two")
    client = OpenRouterClient(model="x/y", api_key="key-one")
    calls = []

    class _FakeOpenAI:
        def __init__(self, key):
            self.key = key
        def post(self, path, *, cast_to, body):
            calls.append(self.key)
            if self.key == "key-one":
                raise _Err(402)
            msg = SimpleNamespace(content="ok", tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")],
                                   usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))

    client._client = _FakeOpenAI("key-one")
    import mole.llm.openrouter as mod
    monkeypatch.setattr(mod, "OpenAI", lambda base_url, api_key, default_headers=None, **kw: _FakeOpenAI(api_key))
    resp = asyncio.run(client.complete([ChatMessage(role="user", content="hi")]))
    assert resp.content == "ok"
    assert calls == ["key-one", "key-two"]
    assert client._fallback_keys == ["key-two"]


def test_reasoning_effort_env_adds_body_param(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-one")
    monkeypatch.setenv("OPENROUTER_REASONING_EFFORT", "low")
    client = OpenRouterClient(model="x/y", api_key="key-one")
    seen = {}

    class _FakeOpenAI:
        def post(self, path, *, cast_to, body):
            seen.update(body)
            msg = SimpleNamespace(content="ok", tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")],
                                   usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))

    client._client = _FakeOpenAI()
    asyncio.run(client.complete([ChatMessage(role="user", content="hi")]))
    assert seen.get("reasoning") == {"effort": "low"}


def test_client_sets_short_timeout_and_no_sdk_retries(monkeypatch):
    """A hung upstream request must surface as APITimeoutError to mole/llm/retry.py within
    minutes, not be swallowed by the SDK's 600 s x 3 default (observed: one hung call froze a
    generated day for 15 minutes)."""
    import httpx
    from mole.llm import openrouter as mod
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-one")
    seen = {}

    class _FakeOpenAI:
        def __init__(self, **kw):
            seen.update(kw)
    monkeypatch.setattr(mod, "OpenAI", lambda **kw: _FakeOpenAI(**kw))
    mod.OpenRouterClient(model="m")
    assert seen["max_retries"] == 0
    assert isinstance(seen["timeout"], httpx.Timeout)
    assert seen["timeout"].read == 300.0 and seen["timeout"].connect == 10.0
    monkeypatch.setenv("OPENROUTER_READ_TIMEOUT", "45")
    mod.OpenRouterClient(model="m")
    assert seen["timeout"].read == 45.0

