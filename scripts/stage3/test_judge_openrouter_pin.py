"""Offline tests for judge_openrouter_pin.py (brief 29 E0-7, dated note 1): the provider pin is opt-in, the default
path is byte-identical on the wire to judge_openrouter.py's, the pinned request is the default request plus one
`provider` key, and every pinned record carries the served provider and precision. No network: the fork client's
OpenAI SDK posts through an httpx MockTransport that records the request bytes."""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
from pathlib import Path

import httpx
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import judge_client as jc  # noqa: E402
import judge_openrouter as jo  # noqa: E402
import judge_openrouter_pin as jp  # noqa: E402
import mole.llm.openrouter as orc  # noqa: E402

PRICES = {"prompt": 0.192 / 1e6, "completion": 15.0 / 1e6}
MODEL = "moonshotai/kimi-k3"
LISTING = {"Wafer": ["mxfp4"], "Sail Research": ["fp4"], "Morph": ["fp8"], "Fireworks": ["unknown"]}
JUDGE_OPENROUTER_SHA256 = "e812157cb991445c12cd4c9197505b27cc03c04f1b23dbde447d417d88b71034"   # brief 15 A6.24 (3)


def _answer(text: str) -> dict | None:
    t = text.strip()
    return {"answer": t} if t else None


class Wire:
    """Captures every request the SDK sends and answers with canned OpenRouter chat completions."""

    def __init__(self, replies: list[dict]):
        self.replies = list(replies)
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json=self.replies.pop(0))

    @property
    def bodies(self) -> list[bytes]:
        return [r.content for r in self.requests]


def _reply(content="the change does x", provider="Wafer", gen="gen-1", finish="stop", cost=0.0021):
    return {"id": gen, "object": "chat.completion", "created": 1, "model": MODEL, "provider": provider,
            "choices": [{"index": 0, "finish_reason": finish, "message": {"role": "assistant", "content": content}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200, "cost": cost,
                      "completion_tokens_details": {"reasoning_tokens": 40}}}


@pytest.fixture
def wire(monkeypatch):
    """Route the fork client's OpenAI SDK through a MockTransport; one key in the environment."""
    w = Wire([])
    real = orc.OpenAI

    def make(**kw):
        return real(**kw, http_client=httpx.Client(transport=httpx.MockTransport(w.handler)))

    monkeypatch.setattr(orc, "OpenAI", make)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-1")
    monkeypatch.delenv("OPENROUTER_API_KEY_2", raising=False)
    monkeypatch.delenv(jo.REASONING_ENV, raising=False)
    return w


def _kw(**over):
    kw = dict(system="sys", prompt_version="v", prices=PRICES, price_source="test", verbose=False, parse=_answer,
              temperature=None, moderation_as_refusal=True, sleep=lambda s: asyncio.sleep(0))
    kw.update(over)
    return kw


def _strip(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k not in ("ts", "latency_s")}


def test_judge_openrouter_is_unchanged():
    assert hashlib.sha256((HERE / "judge_openrouter.py").read_bytes()).hexdigest() == JUDGE_OPENROUTER_SHA256


def test_kimi_pin_body():
    assert jp.KIMI_K3_WAFER_MXFP4.body() == {"order": ["wafer"], "allow_fallbacks": False, "quantizations": ["mxfp4"]}
    assert jp.ProviderPin(order=("wafer",)).body() == {"order": ["wafer"], "allow_fallbacks": False}


@pytest.mark.parametrize("temperature,effort", [(None, None), (0.0, None), (None, "high")])
def test_no_pin_is_byte_identical_to_judge_openrouter(wire, monkeypatch, temperature, effort):
    if effort:
        monkeypatch.setenv(jo.REASONING_ENV, effort)
    wire.replies = [_reply(), _reply()]
    plain = jo.OpenRouterJudge(None, MODEL, **_kw(temperature=temperature))
    ra = asyncio.run(plain.score("read", "read:r0:x:whole", "packet"))
    nopin = jp.PinnedOpenRouterJudge(None, MODEL, **_kw(temperature=temperature), pin=None)
    rb = asyncio.run(nopin.score("read", "read:r0:x:whole", "packet"))
    a, b = wire.requests
    assert a.url == b.url and a.method == b.method and a.content == b.content
    assert _strip(ra) == _strip(rb) and "served" not in rb and "provider" not in json.loads(b.content)


def test_pinned_request_is_default_plus_provider(wire):
    wire.replies = [_reply(), _reply(gen="gen-2")]
    asyncio.run(jo.OpenRouterJudge(None, MODEL, **_kw()).score("read", "l", "packet"))
    pinned = jp.PinnedOpenRouterJudge(None, MODEL, **_kw(), pin=jp.KIMI_K3_WAFER_MXFP4, endpoint_listing=LISTING)
    rec = asyncio.run(pinned.score("read", "l", "packet"))
    default, pinned_body = (json.loads(c) for c in wire.bodies)
    assert list(pinned_body) == list(default) + ["provider"]
    assert pinned_body == {**default, "provider": jp.KIMI_K3_WAFER_MXFP4.body()}
    assert rec["outcome"] == "scored" and rec["request_params"]["provider"] == jp.KIMI_K3_WAFER_MXFP4.body()
    assert rec["served"] == [{"provider": "Wafer", "precision": "mxfp4", "precision_source": "endpoint listing",
                              "generation_id": "gen-2", "on_pin": True}]


def test_pinned_record_is_default_record_plus_served(wire):
    wire.replies = [_reply(), _reply()]
    ra = asyncio.run(jo.OpenRouterJudge(None, MODEL, **_kw()).score("read", "l", "packet"))
    rb = asyncio.run(jp.PinnedOpenRouterJudge(None, MODEL, **_kw(), pin=jp.KIMI_K3_WAFER_MXFP4,
                                              endpoint_listing=LISTING).score("read", "l", "packet"))
    rb = _strip(rb)
    rb["request_params"] = {k: v for k, v in rb["request_params"].items() if k != "provider"}
    assert {k: v for k, v in rb.items() if k != "served"} == _strip(ra)


def test_off_pin_reply_is_errored_and_not_cached(wire, tmp_path):
    wire.replies = [_reply(provider="Sail Research")]
    j = jp.PinnedOpenRouterJudge(tmp_path / "c.jsonl", MODEL, **_kw(), pin=jp.KIMI_K3_WAFER_MXFP4, endpoint_listing=LISTING)
    rec = asyncio.run(j.score("read", "l", "packet"))
    assert rec["outcome"] == "errored" and rec["score"] is None and "Sail Research" in rec["error"]
    assert rec["served"][0] == {"provider": "Sail Research", "precision": None, "precision_source": "endpoint listing",
                                "generation_id": "gen-1", "on_pin": False}
    assert rec["cost_usd"] > 0 and j.cache == {} and j.stats()["errored"] == 1


def test_every_attempt_is_recorded(wire):
    wire.replies = [_reply(content="   ", gen="gen-a"), _reply(gen="gen-b")]
    j = jp.PinnedOpenRouterJudge(None, MODEL, **_kw(), pin=jp.KIMI_K3_WAFER_MXFP4, endpoint_listing=LISTING)
    rec = asyncio.run(j.score("read", "l", "packet"))
    assert rec["outcome"] == "scored" and len(rec["attempts"]) == 2
    assert [s["generation_id"] for s in rec["served"]] == ["gen-a", "gen-b"]


def test_concurrent_units_keep_their_own_served_records(wire):
    wire.replies = [_reply(gen=f"gen-{i}") for i in range(6)]
    j = jp.PinnedOpenRouterJudge(None, MODEL, **_kw(concurrency=6, rpm=0), pin=jp.KIMI_K3_WAFER_MXFP4, endpoint_listing=LISTING)
    recs = asyncio.run(j.score_many([("read", f"l{i}", "same packet") for i in range(6)]))
    sent = {json.loads(r.content)["provider"]["order"][0] for r in wire.requests}
    assert sent == {"wafer"} and len({r["served"][0]["generation_id"] for r in recs}) == 6


def test_served_precision():
    pin = jp.KIMI_K3_WAFER_MXFP4
    assert jp.served_precision("Wafer", pin, LISTING) == "mxfp4"
    assert jp.served_precision("Sail Research", pin, LISTING) is None          # not in the filter
    assert jp.served_precision("Nobody", pin, LISTING) is None
    loose = jp.ProviderPin(order=("chutes",), quantizations=("fp4",))
    assert jp.served_precision("Chutes", loose, {"Chutes": ["mxfp4"]}) == "mxfp4"   # fp4 includes mxfp4 (OpenRouter docs)
    assert jp.served_precision("X", jp.ProviderPin(order=("x",)), {"X": ["fp4", "fp8"]}) is None   # two, no filter


def test_on_pin():
    pin = jp.KIMI_K3_WAFER_MXFP4
    assert jp.on_pin("Wafer", "mxfp4", pin) and not jp.on_pin("Wafer", "fp8", pin)
    assert not jp.on_pin("Sail Research", "mxfp4", pin) and not jp.on_pin(None, "mxfp4", pin)
    assert jp.on_pin("Wafer", None, jp.ProviderPin(order=("wafer/us",)))      # endpoint slug: base provider matches


def test_endpoint_listing_parse():
    data = {"data": {"endpoints": [{"provider_name": "Wafer", "quantization": "mxfp4", "tag": "wafer"},
                                   {"provider_name": "Wafer", "quantization": "mxfp4", "tag": "wafer/us"},
                                   {"provider_name": "Morph", "quantization": "fp8", "tag": "morph/fp8"}]}}
    assert jp.listing_from_endpoints(data) == {"Morph": ["fp8"], "Wafer": ["mxfp4"]}
