"""OpenRouter backend — hosted OpenAI-v1 chat-completions via openrouter.ai.

The default reproduction backend: hosted models behind an OpenAI-v1 API
(base_url https://openrouter.ai/api/v1) with plain API-key auth. The key is a
static secret read once from OPENROUTER_API_KEY (process env only, never a file
on a shared disk).

Robustness for reasoning / DeepSeek-style models that emit malformed
`{}`-prefixed tool-call args: raw `.post()` body bypass (skips the OpenAI SDK's
O(n^2) per-call maybe_transform that serializes the event loop on long sessions),
malformed-arg-tolerant `_parse_tool_args`, empty-200 degrade, dotted tool-name
sanitization, and the `</think>` / `<invoke>` reasoning-leak guards.

Env:
  OPENROUTER_API_KEY   required — the OpenRouter API key (process env ONLY).
  OPENROUTER_API_KEY_2, _3, ...  optional fallback keys, used in numeric order when
                       the active key dies (401, 402, or 403 key/credit/limit); with
                       none left a spent key raises KeyExhaustedError (not retried).
  OPENROUTER_MODEL     model slug, e.g. `deepseek/deepseek-v4-pro` (default) or
                       `deepseek/deepseek-v4-flash`.
  OPENROUTER_BASE_URL  default https://openrouter.ai/api/v1.
  OPENROUTER_REFERER / OPENROUTER_TITLE  optional attribution headers OpenRouter
                       uses for its public rankings (harmless if unset).
  OPENROUTER_SEND_SEED=1  opt into sending `seed` (off by default; temp-0 moots it,
                       and an unknown-param 400 would kill sessions).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading

import httpx
from openai import OpenAI
from openai.types.chat import ChatCompletion

from .base import ChatMessage, ChatResponse, TokenUsage, ToolCall, ToolSchema
from .retry import is_key_exhaustion
from .toolcalls import _parse_xml_function_calls, _strip_xml_function_calls


DEFAULT_CALL_DEADLINE_S = 600.0


def call_deadline_s() -> float:
    """The overall per-call deadline (seconds): OPENROUTER_CALL_DEADLINE_S, default 600."""
    return float(os.environ.get("OPENROUTER_CALL_DEADLINE_S", DEFAULT_CALL_DEADLINE_S))


class CallDeadlineError(TimeoutError):
    """No response within the per-call deadline (brief 07e, 2026-10-22: one request of
    prefix_rw_v2b hung for 100+ minutes in a socket read the httpx read timeout never ended,
    and the runner's day bucket waited on it). A harness timeout, not a world parameter: it
    is retryable like APITimeoutError, and mole/llm/retry.py caps it at three attempts per
    call before the session dies as an llm_error (a request that hangs three times will hang
    a fourth). The blocked worker thread is a daemon thread and is abandoned (a blocking
    socket read cannot be cancelled); it never holds the runner's exit."""


class KeyExhaustedError(RuntimeError):
    """Every configured OpenRouter key is spent or capped (402, or a 403 naming a
    key/credit/limit). Deliberately carries no status code: the retry layer must not
    re-ask, and the run's auth breaker still sees the original 402/403 via __cause__."""

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_READ_TIMEOUT_S = 300.0  # seconds; see OpenRouterClient._make_client

DEFAULT_MODEL = "deepseek/deepseek-v4-pro"


def _parse_tool_args(args) -> dict:
    """Tolerantly parse tool-call arguments into a dict.

    Some DeepSeek deployments emit an empty `{}` prefix before the real object,
    so a bare `json.loads` raises "Extra data" and, being non-retryable, kills the
    whole session at turn 1. Walk successive JSON values and take the first
    non-empty dict; never crash a session over one bad tool call.
    """
    if not isinstance(args, str):
        return args or {}
    try:
        parsed = json.loads(args)
    except json.JSONDecodeError:
        parsed, dec, i = {}, json.JSONDecoder(), 0
        while i < len(args):
            while i < len(args) and args[i].isspace():
                i += 1
            if i >= len(args):
                break
            try:
                obj, i = dec.raw_decode(args, i)
            except json.JSONDecodeError:
                break
            if isinstance(obj, dict) and obj:
                parsed = obj
                break
    return parsed if isinstance(parsed, dict) else {}



logger = logging.getLogger(__name__)


def _token_usage(usage) -> TokenUsage:
    """TokenUsage from an OpenAI-compatible usage object. OpenRouter adds `cost` (USD for
    the call), `prompt_tokens_details.cached_tokens` and
    `completion_tokens_details.reasoning_tokens`; the openai SDK keeps unknown fields as
    attributes / in model_extra, so read them defensively."""
    if usage is None:
        return TokenUsage()
    def _get(obj, name, default=0):
        v = getattr(obj, name, None)
        if v is None and hasattr(obj, "model_extra") and isinstance(obj.model_extra, dict):
            v = obj.model_extra.get(name)
        if v is None and isinstance(obj, dict):
            v = obj.get(name)
        return v if v is not None else default
    ptd = _get(usage, "prompt_tokens_details", None)
    ctd = _get(usage, "completion_tokens_details", None)
    try:
        cost = float(_get(usage, "cost", 0.0) or 0.0)
    except (TypeError, ValueError):
        cost = 0.0
    return TokenUsage(
        input_tokens=int(_get(usage, "prompt_tokens", 0) or 0),
        output_tokens=int(_get(usage, "completion_tokens", 0) or 0),
        cached_input_tokens=int(_get(ptd, "cached_tokens", 0) or 0) if ptd is not None else 0,
        reasoning_tokens=int(_get(ctd, "reasoning_tokens", 0) or 0) if ctd is not None else 0,
        cost_usd=cost,
    )

class OpenRouterClient:
    """LLMClient for an OpenRouter OpenAI-v1 chat-completions model."""

    backend = "openrouter"

    def _make_client(self, key: str, headers: dict[str, str] | None) -> OpenAI:
        """One OpenAI-v1 client. Timeouts are OURS, not the SDK's: the SDK default is a
        600 s read timeout with 2 silent retries, so a single upstream request that never
        answers can hold a session (and, because sessions run in ordered sim-time buckets,
        a whole generated day) for 30 minutes. Read timeout 300 s (long reasoning turns
        exist), SDK retries off; mole/llm/retry.py owns retries and already treats
        APITimeoutError / ReadTimeout as retryable. Override with OPENROUTER_READ_TIMEOUT."""
        read_s = float(os.environ.get("OPENROUTER_READ_TIMEOUT", DEFAULT_READ_TIMEOUT_S))
        return OpenAI(
            base_url=self._base_url,
            api_key=key,
            default_headers=headers or None,
            timeout=httpx.Timeout(connect=10.0, read=read_s, write=60.0, pool=60.0),
            max_retries=0,
        )

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
    ) -> None:
        key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError(
                "OPENROUTER_API_KEY is required for LLM_BACKEND=openrouter "
                "(set it in the process environment; never a file on a shared disk)."
            )
        self.model_id = model
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._send_seed = os.environ.get("OPENROUTER_SEND_SEED") == "1"
        # Optional OpenRouter attribution headers (used for its public rankings).
        headers: dict[str, str] = {}
        if os.environ.get("OPENROUTER_REFERER"):
            headers["HTTP-Referer"] = os.environ["OPENROUTER_REFERER"]
        if os.environ.get("OPENROUTER_TITLE"):
            headers["X-Title"] = os.environ["OPENROUTER_TITLE"]
        # Static API key (OpenRouter keys don't expire hourly like short-lived cloud tokens),
        # so set once at construction. One client; the connection pool is reused.
        self._client = self._make_client(key, headers)
        # Fallback keys: OPENROUTER_API_KEY_2, _3, ... (numeric order). On a dead
        # key -- 401, or a spent/capped key (402, or 403 "Key limit exceeded";
        # retry.is_key_exhaustion) -- the client retires that key, switches to the
        # next key that has not itself died, and re-issues the call, so a long run
        # survives a key hitting its spend cap. With no live key left a spent key
        # raises KeyExhaustedError (non-retryable) instead of being re-asked forever.
        # Logs name keys by index / env-var name, never by value.
        self._headers = headers
        names = sorted(
            (k for k in os.environ
             if k.startswith("OPENROUTER_API_KEY_") and k[len("OPENROUTER_API_KEY_"):].isdigit()
             and os.environ[k] and os.environ[k] != key),
            key=lambda k: int(k[len("OPENROUTER_API_KEY_"):]))
        self._fallback_keys: list[str] = [os.environ[k] for k in names]
        self._keys: list[str] = [key, *self._fallback_keys]
        self._key_names: list[str] = ["OPENROUTER_API_KEY", *names]
        self._key_pos = 0                     # index into self._keys of the active key
        self._dead_keys: set[int] = set()
        self._key_lock = threading.Lock()     # _call runs in worker threads

    def _key_label(self, pos: int) -> str:
        return f"key #{pos + 1} ({self._key_names[pos]})"

    def _retire_key(self, pos: int, reason: str) -> bool:
        """Mark key `pos` dead; if it is still the active key, switch to the next key
        that has not died. Returns True iff a live key is active afterwards."""
        with self._key_lock:
            self._dead_keys.add(pos)
            if self._key_pos != pos:          # another call already rotated past it
                return self._key_pos not in self._dead_keys
            for nxt in range(pos + 1, len(self._keys)):
                if nxt not in self._dead_keys:
                    self._key_pos = nxt
                    self._client = self._make_client(self._keys[nxt], self._headers)
                    logger.warning("openrouter: API %s failed (%s); switched to %s",
                                   self._key_label(pos), reason, self._key_label(nxt))
                    return True
            logger.error("openrouter: API %s failed (%s); no unexhausted fallback key left "
                         "(%d configured)", self._key_label(pos), reason, len(self._keys))
            return False

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSchema] | None = None,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        seed: int | None = None,
    ) -> ChatResponse:
        # Some deployments reject dotted tool names (our convention is
        # `<service>.<action>`); sanitize on the way out, reverse on parse.
        sanitized_map: dict[str, str] = {}
        if tools:
            for t in tools:
                if "." in t.name:
                    sanitized_map[t.name.replace(".", "_")] = t.name

        def _call() -> ChatResponse:
            body: dict = {
                "model": self._model,
                "messages": [m.to_openai() for m in messages],
                "temperature": temperature,
            }
            if tools:
                tool_payload = []
                for t in tools:
                    raw = t.to_openai()
                    if "function" in raw:
                        raw = dict(raw)
                        raw["function"] = dict(raw["function"])
                        raw["function"]["name"] = raw["function"]["name"].replace(".", "_")
                    tool_payload.append(raw)
                body["tools"] = tool_payload
            if max_tokens is not None:
                body["max_tokens"] = max_tokens
            if seed is not None and self._send_seed:
                body["seed"] = seed
            # Optional reasoning-effort control (OpenRouter `reasoning` param) for
            # reasoning models. Env OPENROUTER_REASONING_EFFORT in {low, medium, high};
            # unset = provider default. Used only for the measured cost/quality
            # comparison; the generator default is unset.
            effort = os.environ.get("OPENROUTER_REASONING_EFFORT", "").strip().lower()
            if effort in ("low", "medium", "high"):
                body["reasoning"] = {"effort": effort}

            # One attempt per live key: each dead-key failure retires that key, so
            # the loop ends after at most len(self._keys) attempts.
            while True:
                with self._key_lock:
                    pos, client = self._key_pos, self._client
                try:
                    resp = client.post(
                        "/chat/completions", cast_to=ChatCompletion, body=body,
                    )
                    break
                except Exception as exc:                              # noqa: BLE001
                    status = getattr(exc, "status_code", None)
                    exhausted = is_key_exhaustion(exc)
                    if not (exhausted or status == 401):
                        raise
                    reason = f"HTTP {status}" + (" key/credit limit" if exhausted else "")
                    if self._retire_key(pos, reason):
                        continue
                    if exhausted:
                        raise KeyExhaustedError(
                            f"openrouter: every configured API key is spent or capped "
                            f"(last tried {self._key_label(pos)}: {reason}); add credit or "
                            f"configure OPENROUTER_API_KEY_<n>") from exc
                    raise
            # OpenAI-compatible 200 with empty `choices` (oversized prompt / flap):
            # degrade to an empty completion so the retry layer's empty-200 path
            # handles it instead of an IndexError surfacing.
            if not resp.choices:
                u = getattr(resp, "usage", None)
                return ChatResponse(
                    content="", tool_calls=[],
                    usage=_token_usage(u),
                    backend=self.backend, model_id=self._model,
                    finish_reason="empty_choices",
                )

            choice = resp.choices[0]
            tool_calls: list[ToolCall] = []
            for tc in choice.message.tool_calls or []:
                returned_name = tc.function.name
                original_name = sanitized_map.get(returned_name, returned_name)
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=original_name,
                        arguments=_parse_tool_args(tc.function.arguments),
                    )
                )

            content_text = choice.message.content or ""
            if "</think>" in content_text:
                content_text = content_text.split("</think>", 1)[1].lstrip()
            if not tool_calls and "<invoke" in content_text:
                tool_calls = _parse_xml_function_calls(content_text, sanitized_map)
                if tool_calls:
                    content_text = _strip_xml_function_calls(content_text)

            usage = resp.usage
            return ChatResponse(
                content=content_text,
                tool_calls=tool_calls,
                usage=_token_usage(usage),
                backend=self.backend,
                model_id=self._model,
                finish_reason=choice.finish_reason or "stop",
            )

        deadline = call_deadline_s()
        try:
            return await asyncio.wait_for(_in_daemon_thread(_call), timeout=deadline)
        except asyncio.TimeoutError:
            raise CallDeadlineError(
                f"openrouter: no response within {deadline:g}s (OPENROUTER_CALL_DEADLINE_S); "
                f"the request is abandoned and retried") from None


async def _in_daemon_thread(fn):
    """Run `fn` in a DAEMON thread and await its result. asyncio.to_thread uses the default
    executor, whose threads are joined at loop shutdown: a request abandoned by the deadline
    (blocked in a socket read) would then hold the runner's exit until the socket died. A
    daemon thread is abandoned for good."""
    import threading
    loop = asyncio.get_running_loop()
    fut: asyncio.Future = loop.create_future()

    def _deliver(setter, value):
        if not fut.done():
            setter(value)

    def _runner():
        try:
            result = fn()
        except BaseException as exc:                                   # noqa: BLE001
            loop.call_soon_threadsafe(_deliver, fut.set_exception, exc)
        else:
            loop.call_soon_threadsafe(_deliver, fut.set_result, result)

    threading.Thread(target=_runner, name="openrouter-call", daemon=True).start()
    return await fut


def from_env() -> OpenRouterClient:
    """Construct from OPENROUTER_* environment variables."""
    return OpenRouterClient(
        model=os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL),
        base_url=os.environ.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL),
    )
