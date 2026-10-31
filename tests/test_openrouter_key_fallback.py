"""OpenRouter client rotates to OPENROUTER_API_KEY_2 on a 401/402 (and a 403 key-limit),
fails fast once no unexhausted key is left, and 402 trips the breaker."""
from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace

import pytest

from mole.generator.run import _is_auth_error
from mole.llm.base import ChatMessage
from mole.llm.openrouter import KeyExhaustedError, OpenRouterClient


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


# ── key exhaustion (402 / 403 key-limit): rotate, then fail fast ─────────────

class PermissionDeniedError(Exception):          # name-matches the openai SDK class
    def __init__(self, status, message):
        super().__init__(f"Error code: {status} - {{'error': {{'message': '{message}', "
                         f"'code': {status}}}}}")
        self.status_code = status


_LIMIT_403 = (403, "Key limit exceeded (weekly limit)")
_CREDIT_402 = (402, "This request requires more credits")


def _ok():
    msg = SimpleNamespace(content="ok", tool_calls=[])
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")],
                           usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))


def _scripted(monkeypatch, script: dict, keys=("key-one", "key-two")):
    """OpenRouterClient over fake OpenAI clients. `script[key]` is a list of outcomes
    popped per call: an (status, message) tuple raises, "ok" returns a completion;
    an exhausted list repeats its last outcome."""
    import mole.llm.openrouter as mod
    monkeypatch.setenv("OPENROUTER_API_KEY", keys[0])
    for i, k in enumerate(keys[1:], start=2):
        monkeypatch.setenv(f"OPENROUTER_API_KEY_{i}", k)
    calls: list[str] = []

    class _FakeOpenAI:
        def __init__(self, key):
            self.key = key

        def post(self, path, *, cast_to, body):
            calls.append(self.key)
            outs = script[self.key]
            out = outs.pop(0) if len(outs) > 1 else outs[0]
            if out == "ok":
                return _ok()
            raise PermissionDeniedError(*out)

    monkeypatch.setattr(mod, "OpenAI",
                        lambda base_url, api_key, default_headers=None, **kw: _FakeOpenAI(api_key))
    return mod.OpenRouterClient(model="x/y"), calls


def _retrying(client):
    from mole.llm.retry import RetryingLLMClient, RetryPolicy

    async def _no_sleep(_s):
        return None
    return RetryingLLMClient(client, RetryPolicy(), sleep=_no_sleep)   # unlimited policy


def _complete(client):
    return asyncio.run(client.complete([ChatMessage(role="user", content="hi")]))


@pytest.mark.parametrize("err", [_LIMIT_403, _CREDIT_402], ids=["403-limit", "402-credit"])
def test_key_exhaustion_rotates_once_then_raises_non_retryable(monkeypatch, caplog, err):
    client, calls = _scripted(monkeypatch, {"key-one": [err], "key-two": [err]})
    with caplog.at_level(logging.WARNING, logger="mole.llm.openrouter"):
        with pytest.raises(KeyExhaustedError) as ei:
            _complete(_retrying(client))       # unlimited retry policy still gives up
    assert calls == ["key-one", "key-two"]     # rotated once, never re-asked the same key
    assert _is_auth_error(ei.value)            # the run's auth breaker still sees it
    text = caplog.text + str(ei.value)
    assert "key #1" in text and "key #2" in text
    assert "key-one" not in text and "key-two" not in text   # never the key value


@pytest.mark.parametrize("err", [_LIMIT_403, _CREDIT_402], ids=["403-limit", "402-credit"])
def test_key_exhaustion_rotation_recovers_on_the_next_key(monkeypatch, err):
    client, calls = _scripted(monkeypatch, {"key-one": [err], "key-two": ["ok"]})
    assert _complete(_retrying(client)).content == "ok"
    assert _complete(_retrying(client)).content == "ok"       # stays on key #2
    assert calls == ["key-one", "key-two", "key-two"]


def test_single_key_exhaustion_raises_after_one_attempt(monkeypatch):
    client, calls = _scripted(monkeypatch, {"key-one": [_LIMIT_403]}, keys=("key-one",))
    with pytest.raises(KeyExhaustedError):
        _complete(_retrying(client))
    assert calls == ["key-one"]


def test_429_still_retries_without_rotating(monkeypatch):
    client, calls = _scripted(monkeypatch, {
        "key-one": [(429, "Rate limit exceeded"), (429, "Rate limit exceeded"), "ok"],
        "key-two": ["ok"]})
    assert _complete(_retrying(client)).content == "ok"
    assert calls == ["key-one"] * 3


def test_plain_403_grant_flap_still_retries(monkeypatch):
    client, calls = _scripted(monkeypatch, {"key-one": [(403, ""), "ok"], "key-two": ["ok"]})
    assert _complete(_retrying(client)).content == "ok"
    assert calls == ["key-one", "key-one"]


def test_retry_layer_does_not_retry_key_exhaustion():
    from mole.llm.retry import RetryPolicy, is_retryable
    p = RetryPolicy()
    assert not is_retryable(PermissionDeniedError(*_LIMIT_403), p)
    assert not is_retryable(PermissionDeniedError(*_CREDIT_402), p)
    assert not is_retryable(PermissionDeniedError(403, "Insufficient credits on this key"), p)
    assert is_retryable(PermissionDeniedError(403, ""), p)            # grant flap: unchanged
    assert is_retryable(PermissionDeniedError(429, "Rate limit exceeded"), p)



def test_temperature_none_omits_the_field_and_a_float_is_sent(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-one")
    monkeypatch.delenv("OPENROUTER_REASONING_EFFORT", raising=False)
    client = OpenRouterClient(model="x/y", api_key="key-one")
    seen = []

    class _FakeOpenAI:
        def post(self, path, *, cast_to, body):
            seen.append(dict(body))
            msg = SimpleNamespace(content="ok", tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")],
                                   usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1))

    client._client = _FakeOpenAI()
    asyncio.run(client.complete([ChatMessage(role="user", content="hi")], temperature=None))
    asyncio.run(client.complete([ChatMessage(role="user", content="hi")]))
    assert "temperature" not in seen[0] and seen[1]["temperature"] == 0.0
