#!/usr/bin/env python3
"""Brief 29 E0-7 (dated note 1, brief 15 A6.24 (3)): OpenRouter's provider preferences for a reader judge, opt-in,
in a module of its own so that `judge_openrouter.py` stays at e812157c and S3's pin does not move.

`PinnedOpenRouterJudge` is `judge_openrouter.OpenRouterJudge` with one more keyword, `pin`:
* `pin=None` (the default) runs the parent's code unchanged: the same request bytes, the same record.
* With a `ProviderPin`, every request is the default request plus one top-level `provider` key (provider order,
  fallbacks disabled, an optional quantization filter), and every record carries `served`: per attempt, the provider
  OpenRouter reports in the response, its precision, the generation id and whether it is on the pin, plus
  `request_params.provider`. A reply served off the pin is recorded as errored (paid, never cached), so a re-run
  re-issues it (certification protocol section 3: a call served elsewhere is discarded and re-issued).

Facts this module relies on (2026-11-02; OpenRouter's provider-routing guide and the public endpoint listing):
* `provider: {order, allow_fallbacks, quantizations}` in the chat-completion body; a base slug ("wafer") matches the
  provider's variant and region endpoints but not a service tier; `fp4` in the filter includes `mxfp4` and `nvfp4`,
  `fp8` includes `mxfp8`; with fallbacks disabled a request no named provider can serve fails instead of rerouting.
* The response carries the serving provider's name in a top-level `provider` field and the generation id in `id`.
  The precision is not in the response; it is taken from `GET /models/{model}/endpoints` (free, no key), as the
  pinned provider's quantization within the filter, and `GET /generation?id=` is read by the probe.
* Kimi K3's pin is Wafer at MXFP4 (brief 24 third amendment; brief 15 A6.18 (m)): Wafer's three listed endpoints
  (`wafer`, `wafer/us`, `wafer/fast`) are all MXFP4.

The fork client builds the request body inside its worker thread; the pin is added to that body by a thin proxy
around the OpenAI SDK client (`_PinnedPost`), and the served fields come back through a per-call box carried by the
messages' OpenAI form (stripped before sending). Nothing in `mole/llm/openrouter.py` or `judge_openrouter.py` changes.

Probe (E0-7: one call costing cents; prints numbers and names only):
    set -a; source work/mole-fork/.env; set +a
    work/mole-fork/.venv/bin/python -I work/checks/judge_openrouter_pin.py probe \\
        --out work/stage3/elicitation/kimi-pin-probe-v0.json --key-env OPENROUTER_API_KEY_2
"""
from __future__ import annotations

import argparse
import asyncio
import contextvars
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc  # noqa: E402
import judge_openrouter as jo  # noqa: E402  (puts the fork on sys.path)
from mole.llm.base import ChatMessage  # noqa: E402
from mole.llm.openrouter import DEFAULT_BASE_URL, OpenRouterClient  # noqa: E402

VERSION = "judge-openrouter-pin/v0"
KIMI_MODEL = "moonshotai/kimi-k3"
PRECISION_SOURCE = "endpoint listing"
# OpenRouter's quantization filter: a broad value includes its named variants (provider-routing guide)
FILTER_INCLUDES = {"fp4": {"fp4", "mxfp4", "nvfp4"}, "fp8": {"fp8", "mxfp8"}}


@dataclass(frozen=True)
class ProviderPin:
    """OpenRouter provider preferences: `order` (provider or endpoint slugs), fallbacks off by default, and an
    optional quantization filter."""
    order: tuple[str, ...]
    allow_fallbacks: bool = False
    quantizations: tuple[str, ...] | None = None

    def body(self) -> dict:
        b: dict = {"order": list(self.order), "allow_fallbacks": self.allow_fallbacks}
        if self.quantizations:
            b["quantizations"] = list(self.quantizations)
        return b


KIMI_K3_WAFER_MXFP4 = ProviderPin(order=("wafer",), allow_fallbacks=False, quantizations=("mxfp4",))


def _slug(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def _allowed(pin: ProviderPin) -> set[str] | None:
    if not pin.quantizations:
        return None
    return set().union(*(FILTER_INCLUDES.get(q, {q}) for q in pin.quantizations))


def on_pin(provider: str | None, precision: str | None, pin: ProviderPin) -> bool:
    """The served provider is one the pin names (by base slug) and, under a filter, its precision passes it."""
    if not provider or _slug(provider) not in {o.split("/")[0] for o in pin.order}:
        return False
    allowed = _allowed(pin)
    return allowed is None or (precision or "") in allowed


def served_precision(provider: str | None, pin: ProviderPin, listing: dict[str, list[str]]) -> str | None:
    """The served provider's quantization from the endpoint listing, within the pin's filter; None when the
    provider is not listed, none of its quantizations passes the filter, or more than one could have served."""
    q = set(listing.get(provider or "", []))
    allowed = _allowed(pin)
    if allowed is not None:
        q &= allowed
    return q.pop() if len(q) == 1 else None


def listing_from_endpoints(data: dict) -> dict[str, list[str]]:
    """`GET /models/{model}/endpoints` -> {provider name: sorted quantizations}."""
    out: dict[str, set[str]] = {}
    for e in data["data"]["endpoints"]:
        out.setdefault(e["provider_name"], set()).add(e.get("quantization") or "unknown")
    return {k: sorted(v) for k, v in sorted(out.items())}


def fetch_endpoints(model: str, base_url: str = DEFAULT_BASE_URL) -> dict:
    import httpx
    r = httpx.get(f"{base_url.rstrip('/')}/models/{model}/endpoints", timeout=30.0)
    r.raise_for_status()
    return r.json()


# ── the client: the fork's OpenRouterClient with the pin added to its request body ───────────────────

class _BoxDict(dict):
    """A message's OpenAI form carrying the call's box (removed by _PinnedPost before sending)."""
    box: list


class _BoxedMessage(ChatMessage):
    def to_openai(self) -> dict[str, Any]:
        d = _BoxDict(super().to_openai())
        d.box = self._box
        return d


def _boxed(m: ChatMessage, box: list) -> ChatMessage:
    b = _BoxedMessage(role=m.role, content=m.content, tool_call_id=m.tool_call_id, name=m.name, tool_calls=m.tool_calls)
    b._box = box
    return b


def served_fields(resp: Any) -> dict:
    """The serving provider and generation id from an OpenRouter chat completion (SDK object or dict)."""
    extra = getattr(resp, "model_extra", None) or (resp if isinstance(resp, dict) else {})
    provider = extra.get("provider", getattr(resp, "provider", None))
    gen = resp.get("id") if isinstance(resp, dict) else getattr(resp, "id", None)
    return {"provider": provider, "generation_id": gen}


class _PinnedPost:
    """Wraps the OpenAI SDK client: `post` sends the body with `provider` appended and fills the call's box."""

    def __init__(self, inner: Any, pin: ProviderPin):
        self._inner, self._pin = inner, pin

    def post(self, path: str, *, cast_to: Any, body: dict, **kw: Any) -> Any:
        msgs = body.get("messages") or []
        box = next((m.box for m in msgs if isinstance(m, _BoxDict)), None)
        out = {k: ([dict(m) for m in v] if k == "messages" else v) for k, v in body.items()}
        out["provider"] = self._pin.body()
        resp = self._inner.post(path, cast_to=cast_to, body=out, **kw)
        if box is not None:
            box.append(served_fields(resp))
        return resp

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class PinnedOpenRouterClient(OpenRouterClient):
    """The fork client with a provider pin; `complete` returns its ChatResponse with `.served` set."""

    def __init__(self, model: str, base_url: str = DEFAULT_BASE_URL, api_key: str | None = None, *, pin: ProviderPin):
        self._pin = pin
        super().__init__(model=model, base_url=base_url, api_key=api_key)

    def _make_client(self, key: str, headers: dict[str, str] | None) -> Any:
        return _PinnedPost(super()._make_client(key, headers), self._pin)

    async def complete(self, messages: list[ChatMessage], **kw: Any) -> Any:
        box: list[dict] = []
        resp = await super().complete([_boxed(m, box) for m in messages], **kw)
        resp.served = box[-1] if box else {"provider": None, "generation_id": None}
        return resp


# ── the judge ────────────────────────────────────────────────────────────────────────────────────

_ATTEMPTS: contextvars.ContextVar[list | None] = contextvars.ContextVar("pinned_attempts", default=None)


class PinnedOpenRouterJudge(jo.OpenRouterJudge):
    """OpenRouterJudge with an opt-in provider pin (see the module docstring). `endpoint_listing` is
    {provider name: quantizations}; when None it is fetched once from OpenRouter's public endpoint listing."""

    def __init__(self, *args: Any, pin: ProviderPin | None = None, endpoint_listing: dict[str, list[str]] | None = None,
                 **kw: Any):
        super().__init__(*args, **kw)
        self.pin = pin
        self.endpoint_listing = endpoint_listing

    def _get_client(self) -> Any:
        if self.pin is None or self._injected is not None:
            return super()._get_client()
        if self._client is None:
            key = jo.key_from_env(self.api_key_env)
            jo.drop_fallback_keys()
            self._client = PinnedOpenRouterClient(model=self.model, api_key=key, pin=self.pin)
        return self._client

    def _listing(self) -> dict[str, list[str]]:
        if self.endpoint_listing is None:
            self.endpoint_listing = listing_from_endpoints(fetch_endpoints(self.model))
        return self.endpoint_listing

    def served_record(self, raw: dict) -> dict:
        assert self.pin is not None
        prec = served_precision(raw.get("provider"), self.pin, self._listing())
        return {"provider": raw.get("provider"), "precision": prec, "precision_source": PRECISION_SOURCE,
                "generation_id": raw.get("generation_id"), "on_pin": on_pin(raw.get("provider"), prec, self.pin)}

    async def _request(self, packet: str, label: str) -> tuple[Any | None, str | None]:
        resp, err = await super()._request(packet, label)
        box = _ATTEMPTS.get()
        if self.pin is not None and box is not None and resp is not None:
            box.append(self.served_record(getattr(resp, "served", None) or {}))
        return resp, err

    async def _score_uncached(self, key: str, view: str, label: str, packet: str) -> dict:
        if self.pin is None:
            return await super()._score_uncached(key, view, label, packet)
        served: list[dict] = []
        token = _ATTEMPTS.set(served)
        try:
            rec = await super()._score_uncached(key, view, label, packet)
        finally:
            _ATTEMPTS.reset(token)
        rec["request_params"] = {**rec["request_params"], "provider": self.pin.body()}
        rec["served"] = served
        off = [s for s in served if not s["on_pin"]]
        if off and rec["outcome"] != "errored":
            rec.update(outcome="errored", score=None, flag=None, rationale=None,
                       error="served off the pin: " + ", ".join(f"{s['provider']} ({s['precision']})" for s in off))
        return rec


# ── the probe ────────────────────────────────────────────────────────────────────────────────────

PROBE_SYSTEM = "You are a connectivity check. Answer in one word."
PROBE_PACKET = "Reply with the single word: ready"


def _probe_parse(text: str) -> dict | None:
    t = text.strip()
    return {"answer_chars": len(t)} if t else None


def fetch_generation(gen_id: str, key: str, base_url: str = DEFAULT_BASE_URL, tries: int = 8) -> dict | None:
    """`GET /generation?id=` (free); its statistics can lag the completion by a few seconds."""
    import httpx
    for i in range(tries):
        r = httpx.get(f"{base_url.rstrip('/')}/generation", params={"id": gen_id},
                      headers={"Authorization": f"Bearer {key}"}, timeout=30.0)
        if r.status_code == 200:
            return r.json().get("data")
        time.sleep(2.0 * (i + 1))
    return None


GENERATION_FIELDS = ("provider_name", "model", "tokens_prompt", "tokens_completion", "native_tokens_reasoning",
                     "total_cost", "finish_reason", "streamed", "cancelled", "created_at")


def cmd_probe(a: argparse.Namespace) -> int:
    key = jo.key_from_env(a.key_env)
    if not key:
        raise SystemExit(f"{a.key_env} is not set (source work/mole-fork/.env)")
    if jo.reasoning_setting() != "provider default":
        raise SystemExit(f"refusing: {jo.REASONING_ENV} is set; the readers run at the provider default")
    endpoints = fetch_endpoints(a.model)
    listing = listing_from_endpoints(endpoints)
    pin = KIMI_K3_WAFER_MXFP4
    available = served_precision("Wafer", pin, listing) == "mxfp4"
    if not available:
        raise SystemExit(f"Wafer at MXFP4 is not in the endpoint listing for {a.model}: {listing}")
    models = json.loads(Path(a.models).read_text()) if a.models else {}
    pr = (models.get("models", {}).get(a.model) or {}).get("pricing") or {"prompt": "0", "completion": "0"}
    j = PinnedOpenRouterJudge(None, a.model, system=PROBE_SYSTEM, prompt_version=VERSION + "/probe",
                              prices={"prompt": float(pr["prompt"]), "completion": float(pr["completion"])},
                              price_source=models.get("price_source", "none"), concurrency=1, rpm=0, temperature=None,
                              max_tokens=a.max_tokens, spend_cap_usd=a.cap, parse=_probe_parse, verbose=True,
                              api_key_env=a.key_env, pin=pin, endpoint_listing=listing)
    rec = asyncio.run(j.score("probe", "probe:kimi-pin:0", PROBE_PACKET))
    gens = []
    for s in rec.get("served", []):
        g = fetch_generation(s["generation_id"], key) if s.get("generation_id") else None
        gens.append({k: g.get(k) for k in GENERATION_FIELDS} | {"precision_like_fields": {k: v for k, v in g.items()
                     if any(t in k.lower() for t in ("quant", "precision", "variant"))}} if g else None)
    keep = ("outcome", "error", "finish_reason", "input_tokens", "output_tokens", "reasoning_tokens", "cost_usd",
            "cost_source", "price_source", "packet_sha256", "prompt_version", "request_params", "served", "attempts",
            "latency_s", "ts")
    out = {"version": VERSION + "/probe", "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "judge_openrouter_sha256": hashlib.sha256((HERE / "judge_openrouter.py").read_bytes()).hexdigest(),
           "model": a.model, "key_env": a.key_env, "pin": pin.body(),
           "endpoint_listing": listing, "endpoint_listing_sha256": jc.sha256(json.dumps(endpoints, sort_keys=True)),
           "wafer_mxfp4_listed": available, "record": {k: rec.get(k) for k in keep},
           "answer_chars": (rec.get("parsed") or {}).get("answer_chars"), "generation": gens}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    s0 = (rec.get("served") or [{}])[-1]
    print(f"probe: outcome {rec['outcome']}; served {s0.get('provider')} at {s0.get('precision')} (on pin {s0.get('on_pin')}); "
          f"generation endpoint provider {[g and g.get('provider_name') for g in gens]}; cost ${rec.get('cost_usd', 0):.5f}; "
          f"tokens in {rec.get('input_tokens')} out {rec.get('output_tokens')}; wrote {a.out}")
    return 0 if rec["outcome"] == "scored" and s0.get("on_pin") else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("probe", help="one pinned Kimi K3 call (cents); records the served provider and precision")
    p.add_argument("--out", required=True)
    p.add_argument("--model", default=KIMI_MODEL)
    p.add_argument("--key-env", default="OPENROUTER_API_KEY_2")
    p.add_argument("--models", default="work/stage3/b3/comprehension/models-v0.json", help="list prices (fallback cost)")
    p.add_argument("--max-tokens", type=int, default=2000)
    p.add_argument("--cap", type=float, default=0.10)
    a = ap.parse_args(argv)
    return {"probe": cmd_probe}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
