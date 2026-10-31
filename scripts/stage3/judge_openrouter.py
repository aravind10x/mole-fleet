#!/usr/bin/env python3
"""Brief 07n part A: a judge on an OpenRouter chat model through the fork's `mole/llm/openrouter.py`
client, with the Bedrock judge client's cache format, retry policy and accounting
(`work/checks/judge_client.py`), so every downstream reader (stage3_views.to_row, summarise,
defect_check, the T1 v2 analysis) reads these records as it reads Sonnet's.

Facts this module relies on (2026-10-26):
* `OpenRouterClient(model, api_key).complete(messages, temperature, max_tokens)` posts one
  chat completion and returns a ChatResponse (content with any `<think>` block stripped,
  usage with prompt/completion/reasoning tokens and the provider-reported cost when present,
  finish_reason). It rotates to OPENROUTER_API_KEY_<n> on a 402 / key-limit 403; this module
  removes those variables from the process environment before construction so key 1 is the only
  key and a spent key is a stop (KeyExhaustedError -> JudgeAborted).
* Outcome classes for an OpenAI-style response (judge-dep-plan.md A3): finish_reason
  `content_filter` (or a provider refusal field) = refused; empty content, a `length` stop without
  JSON, or no parseable verdict = errored (a refusal written as prose is errored); errored units
  are re-asked up to MAX_PARSE_RETRIES times, as the Bedrock client does.
* Cost: the provider-reported `usage.cost` when it is positive, else the list price
  (prompt / completion USD per token, passed in from the models endpoint), both recorded.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from collections.abc import Awaitable, Callable, Iterable
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc  # noqa: E402  (the cache key, sha256, _parse_verdict, JudgeAborted, _now_iso)

sys.path.insert(0, str(jc.FORK))
from mole.llm.base import ChatMessage  # noqa: E402

PROVIDER = "openrouter"
MAX_TOKENS = 4000
TEMPERATURE = 0.0
MAX_PARSE_RETRIES = 2
MAX_TRANSIENT_RETRIES = 3
TRANSIENT_BACKOFF_S = 5.0
RATE_LIMIT_PAUSE_S = 60.0
MAX_429_RETRIES = 2
KEY_FALLBACK_PREFIX = "OPENROUTER_API_KEY_"
MODERATION_PREFIX = "moderation 403: "   # brief 23: an OpenRouter moderation flag, kept as a refusal when asked


def drop_fallback_keys() -> list[str]:
    """Remove OPENROUTER_API_KEY_<n> from this process so the fork client holds key 1 only
    (names returned, never values)."""
    names = sorted(k for k in os.environ if k.startswith(KEY_FALLBACK_PREFIX) and k[len(KEY_FALLBACK_PREFIX):].isdigit())
    for k in names:
        os.environ.pop(k, None)
    return names


def classify(resp: Any, parse: jc.ReplyParser | None = None) -> dict:
    """ChatResponse-like -> {outcome, score, flag, rationale, finish_reason, error}. With `parse`
    (brief 23), judge_client.classify_parsed decides scored / errored for non-empty content."""
    fr = getattr(resp, "finish_reason", None)
    if fr in ("content_filter", "refusal"):
        return {"outcome": "refused", "score": None, "flag": None, "rationale": None, "finish_reason": fr, "error": None}
    text = (getattr(resp, "content", None) or "").strip()
    if not text:
        return {"outcome": "errored", "score": None, "flag": None, "rationale": None, "finish_reason": fr,
                "error": f"empty content (finish_reason={fr})"}
    if parse is not None:
        return jc.classify_parsed(text, parse, {"finish_reason": fr})
    v = jc._parse_verdict(text)
    if v.get("score") is None:
        return {"outcome": "errored", "score": None, "flag": None, "rationale": text[:300], "finish_reason": fr,
                "error": f"no parseable score (finish_reason={fr})"}
    return {"outcome": "scored", "score": int(v["score"]), "flag": bool(v["flag"]), "rationale": v.get("rationale"),
            "finish_reason": fr, "error": None}


def _status(exc: BaseException) -> int | None:
    s = getattr(exc, "status_code", None)
    return int(s) if isinstance(s, int) else None


def is_moderation_403(exc: BaseException) -> bool:
    """OpenRouter's input moderation answers 403 with a message naming moderation or a flag."""
    msg = str(exc).lower()
    return _status(exc) == 403 and ("moderation" in msg or "flagged" in msg)


class OpenRouterJudge:
    """One (model, view) judge over the fork's OpenRouter client. `client` (tests) is any object
    with an async `complete(messages, *, temperature, max_tokens)`; by default an
    OpenRouterClient on key 1 is built once. `prices` = {"prompt": USD/token, "completion": USD/token}.
    Brief 23 (2026-10-31): `parse` replaces the verdict parser (judge_client.classify_parsed), and
    temperature=None asks for the provider default: the fork client always writes the field, so it
    goes out as JSON null (the OpenAI-compatible schema's "unset"), recorded as null."""

    def __init__(self, cache_path: Path | None, model: str, *, system: str, prompt_version: str,
                 prices: dict[str, float], price_source: str, concurrency: int = 4, rpm: int = 30,
                 max_tokens: int = MAX_TOKENS, temperature: float | None = TEMPERATURE,
                 spend_cap_usd: float | None = None, client: Any = None,
                 sleep: Callable[[float], Awaitable[None]] = asyncio.sleep, verbose: bool = True,
                 parse: jc.ReplyParser | None = None, moderation_as_refusal: bool = False):
        self.model, self.system, self.prompt_version = model, system, prompt_version
        self.parse = parse
        # brief 23: a moderation 403 is that unit's refusal (recorded, not re-asked) instead of a run stop
        self.moderation_as_refusal = moderation_as_refusal
        self.prices, self.price_source = prices, price_source
        self.concurrency, self.rpm, self.max_tokens, self.temperature = concurrency, rpm, max_tokens, temperature
        self.spend_cap_usd = spend_cap_usd
        self.cache_path = Path(cache_path) if cache_path else None
        self._injected = client
        self._client = None
        self._sleep = sleep
        self._verbose = verbose
        self._sem: asyncio.Semaphore | None = None
        self._stamps: list[float] = []
        self._lock: asyncio.Lock | None = None
        self.abort: str | None = None
        self.cache: dict[str, dict] = {}
        self.dollars_cached = 0.0
        self.dollars = 0.0
        self._c: dict[str, int] = {k: 0 for k in ("calls", "requests", "cached", "scored", "refused", "errored",
                                                   "input_tokens", "output_tokens", "reasoning_tokens", "rate_waits",
                                                   "n_429", "transient_retries", "parse_retries")}
        self._load_cache()

    # cache -------------------------------------------------------------------
    def _load_cache(self) -> None:
        if not (self.cache_path and self.cache_path.exists()):
            return
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            self.dollars_cached += float(d.get("cost_usd") or 0.0)
            if d.get("outcome") in ("scored", "refused"):
                if d.get("model") != self.model or d.get("prompt_version") != self.prompt_version:
                    raise ValueError(f"cache {self.cache_path} holds a record from model={d.get('model')!r} "
                                     f"prompt_version={d.get('prompt_version')!r}; this judge is {self.model!r} / {self.prompt_version!r}")
                self.cache[d["cache_key"]] = d

    def _save(self, rec: dict) -> None:
        if self.cache_path:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cache_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # client ------------------------------------------------------------------
    def _get_client(self) -> Any:
        if self._injected is not None:
            return self._injected
        if self._client is None:
            drop_fallback_keys()
            from mole.llm.openrouter import OpenRouterClient
            self._client = OpenRouterClient(model=self.model, api_key=os.environ.get("OPENROUTER_API_KEY"))
        return self._client

    def _log(self, msg: str) -> None:
        if self._verbose:
            print(msg, file=sys.stderr, flush=True)

    async def _throttle(self) -> None:
        if self.rpm <= 0:
            return
        assert self._lock is not None
        async with self._lock:
            now = time.monotonic()
            self._stamps = [t for t in self._stamps if now - t < 60.0]
            if len(self._stamps) >= self.rpm:
                wait = 60.0 - (now - self._stamps[0]) + 0.05
                self._c["rate_waits"] += 1
                await self._sleep(wait)
            self._stamps.append(time.monotonic())

    def total_spent(self) -> float:
        return self.dollars_cached + self.dollars

    def cost_of(self, usage: Any) -> tuple[float, str]:
        prov = float(getattr(usage, "cost_usd", 0.0) or 0.0)
        listed = (int(getattr(usage, "input_tokens", 0) or 0) * self.prices["prompt"]
                  + int(getattr(usage, "output_tokens", 0) or 0) * self.prices["completion"])
        return (prov, "provider") if prov > 0 else (listed, "list")

    async def _request(self, packet: str, label: str) -> tuple[Any | None, str | None]:
        from mole.llm.openrouter import KeyExhaustedError
        n429 = n_tr = 0
        msgs = [ChatMessage(role="system", content=self.system), ChatMessage(role="user", content=packet)]
        while True:
            if self.abort:
                raise jc.JudgeAborted(self.abort)
            if self.spend_cap_usd is not None and self.total_spent() >= self.spend_cap_usd:
                self.abort = f"judge spend cap ${self.spend_cap_usd:.2f} reached (${self.total_spent():.4f} paid against this cache)"
                raise jc.JudgeAborted(self.abort)
            await self._throttle()
            self._c["requests"] += 1
            try:
                return await self._get_client().complete(msgs, temperature=self.temperature, max_tokens=self.max_tokens), None
            except KeyExhaustedError as exc:
                self.abort = f"key spent or capped on {label}: {str(exc)[:200]}"
                raise jc.JudgeAborted(self.abort) from exc
            except Exception as exc:  # noqa: BLE001  (SDK status errors, timeouts, connection errors)
                s = _status(exc)
                if self.moderation_as_refusal and is_moderation_403(exc):
                    return None, MODERATION_PREFIX + str(exc)[:200]
                if s in (400, 401, 403, 404):
                    self.abort = f"HTTP {s} {type(exc).__name__} on {label} (model {self.model}): {str(exc)[:300]}"
                    raise jc.JudgeAborted(self.abort) from exc
                if s == 429:
                    self._c["n_429"] += 1
                    n429 += 1
                    if n429 > MAX_429_RETRIES:
                        return None, f"HTTP 429 after {MAX_429_RETRIES} retries"
                    self._log(f"  429 on {label}; pausing {RATE_LIMIT_PAUSE_S:.0f} s")
                    await self._sleep(RATE_LIMIT_PAUSE_S)
                    continue
                err = f"{type(exc).__name__}" + (f" HTTP {s}" if s else "")
                n_tr += 1
                if n_tr > MAX_TRANSIENT_RETRIES:
                    return None, f"{err} after {MAX_TRANSIENT_RETRIES} retries: {str(exc)[:200]}"
                self._c["transient_retries"] += 1
                self._log(f"  transient error on {label} ({err}); retry {n_tr}/{MAX_TRANSIENT_RETRIES}")
                await self._sleep(TRANSIENT_BACKOFF_S * n_tr)

    async def score(self, view: str, label: str, packet: str) -> dict:
        key = jc.cache_key(view, label, packet)
        if key in self.cache:
            self._c["cached"] += 1
            return dict(self.cache[key])
        if self.abort:
            raise jc.JudgeAborted(self.abort)
        if self._sem is None:
            self._sem = asyncio.Semaphore(self.concurrency)
            self._lock = asyncio.Lock()
        async with self._sem:
            rec = await self._score_uncached(key, view, label, packet)
        self._c["calls"] += 1
        self._c[rec["outcome"]] += 1
        if rec["outcome"] != "errored":
            self.cache[key] = rec
        self._save(rec)
        return dict(rec)

    async def _score_uncached(self, key: str, view: str, label: str, packet: str) -> dict:
        t0 = time.monotonic()
        tok = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}
        cost = 0.0
        sources: list[str] = []
        attempts: list[dict] = []
        n_parse = 0
        while True:
            resp, err = await self._request(packet, label)
            if resp is None:
                if err and err.startswith(MODERATION_PREFIX):
                    c = {"outcome": "refused", "score": None, "flag": None, "rationale": None, "finish_reason": "moderation_403", "error": err}
                    attempts.append({"outcome": "refused", "finish_reason": "moderation_403"})
                    break
                c = {"outcome": "errored", "score": None, "flag": None, "rationale": None, "finish_reason": None, "error": err}
                attempts.append({"outcome": "errored", "finish_reason": None})
                break
            u = getattr(resp, "usage", None)
            for k in tok:
                tok[k] += int(getattr(u, k, 0) or 0)
            dc, src = self.cost_of(u)
            cost += dc
            sources.append(src)
            self.dollars += dc
            for k in tok:
                self._c[k] += int(getattr(u, k, 0) or 0)
            c = classify(resp, self.parse)
            attempts.append({"outcome": c["outcome"], "finish_reason": c["finish_reason"]})
            if c["outcome"] == "errored" and n_parse < MAX_PARSE_RETRIES:
                n_parse += 1
                self._c["parse_retries"] += 1
                self._log(f"  no score on {label} ({c['error']}); re-asking {n_parse}/{MAX_PARSE_RETRIES}")
                continue
            break
        return {"cache_key": key, "view": view, "label": label, **c, "stop_reason": c.get("finish_reason"),
                "stop_details": None, "provider": PROVIDER, "model": self.model, "model_served": self.model,
                "region": None, **tok, "cache_read_tokens": 0, "cache_write_tokens": 0,
                "cost_usd": round(cost, 8), "cost_source": sorted(set(sources)), "price_source": self.price_source,
                "packet_chars": len(packet), "packet_sha256": jc.sha256(packet), "prompt_version": self.prompt_version,
                "request_params": {"model": self.model, "max_tokens": self.max_tokens, "temperature": self.temperature,
                                   "reasoning": "provider default", "system_sha256": jc.sha256(self.system),
                                   "system_chars": len(self.system)},
                "parse_retries": n_parse, "attempts": attempts, "latency_s": round(time.monotonic() - t0, 3),
                "ts": jc._now_iso()}

    async def score_many(self, items: Iterable[tuple[str, str, str]]) -> list[dict]:
        return list(await asyncio.gather(*[self.score(v, l, p) for v, l, p in items]))

    def stats(self) -> dict:
        return {**self._c, "dollars": round(self.dollars, 6), "dollars_cached": round(self.dollars_cached, 6),
                "dollars_total": round(self.total_spent(), 6), "aborted": self.abort, "model": self.model, "provider": PROVIDER}

    def batch_log(self, path: Path, note: str | None = None) -> dict:
        rec = {"ts": jc._now_iso(), "note": note, **self.stats(), "cache": str(self.cache_path)}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        return rec
