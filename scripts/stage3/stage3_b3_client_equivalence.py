#!/usr/bin/env python3
"""Brief 31 (2026-11-01, blue, $0, no request sent): the judge client's default-path equivalence against the sealed
nulls S3 reads against.

G1, requests. For each of S3's nine view-and-judge cells (plan.md section 2.6) the null's packets are rebuilt from the
corpus with the pinned view modules and matched to the cell's judge cache by cache key (view | label | sha256(packet)).
Every reproduced packet goes to the bound-hash client and to the current client, each built with the cell's settings
as its caller builds it and an injected stub transport that records the request and returns a fixed reply: nothing is
sent. The two requests are compared as canonical JSON bytes, the two returned records field by field (ts and latency_s
aside), and the request the current client sends against the request fields the null's own call recorded. GPT-6 Sol
runs on the Converse path, which the bound hash lacks: its pair is brief 09's client (8390cfd7, the provider check's)
and the current one; its null was scored on OpenRouter (07p), so its recorded request fields differ by the provider
switch, named field by field. The OpenRouter client (off S3's path; it scored Sol's null) is compared the same way.

G2, replies. The caches' key names are reported; no cache holds the raw reply (parsed fields only), so the fallback
runs: a parser test by construction over every reply shape the old parsers accept, built from their code and their
tests (never from cached content), through the old and current parsers and the scoring loops' retry defaults.

Writes counts, field names, key names and hashes only: no packet, reply, rationale or score.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_client_equivalence.py [--out PATH]
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import types
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Mapping, Sequence

HERE = Path(__file__).resolve().parent                 # work/checks
ROOT = HERE.parents[1]                                 # tais-project-selection
FORK = ROOT / "work" / "mole-fork"
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402  (puts the fork on sys.path)
import stage3_author_doc as ad  # noqa: E402
import stage3_views as sv  # noqa: E402

import anthropic  # noqa: E402
import httpx2  # noqa: E402
from anthropic.types import Message, RefusalStopDetails, TextBlock, ThinkingBlock, Usage  # noqa: E402

VERSION = "b3-judge-client-equivalence/v0"
OUT = "work/stage3/b3/judge-client-equivalence-v0.json"
CORPUS = "work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl"
CORPUS_SHA256 = "ffc1f6cd423cae68ac5bd752580f845a838625ebc57a9cf1e083d7e6ddaeeb74"

# Every client version compared, by sha256, with where its bytes come from (the fork history or the working file).
SOURCES: dict[str, dict[str, Any]] = {
    "jc_1675a966": {"sha256": "1675a966514326bb0c8467495cc7db424a557f3deae8b732b283ec869cdf43cd",
                    "git": ("afeeb5b", "results/stage3/q1q2-synthetic/judge_client.amended-2026-10-26.py"),
                    "role": "bound: the last hash test_stage3_t1v3_score.py accepts (07n part C, 2026-10-26); B1's nulls recorded it"},
    "jc_80f1bdba": {"sha256": "80f1bdbaba92327d89a15ee9e1dde9e513350e9a6b96627c6ae1351a3d6a34c2",
                    "git": ("dc4af84", "results/stage3/q1q2-synthetic/judge_client.amended-2026-10-26.py"),
                    "role": "07i part 2 (2026-10-26), the hash before the bound one"},
    "jc_8390cfd7": {"sha256": "8390cfd789c98e65cd6362adaed62a55c2f792e50907636b37006b3efb093e3e",
                    "git": ("f1124b6", "scripts/stage3/judge_client.py"),
                    "role": "brief 09 (2026-10-29): BedrockConverseJudge added; Sol's provider check ran on it"},
    "jc_72d394e3": {"sha256": "72d394e33584f7a5fe9ab638f4fc95c57ae9d0d7d0c93bf2c2d15928c4daf198",
                    "file": "work/checks/judge_client.py", "role": "current; pinned by plan.md (S1)"},
    "jo_29f5157a": {"sha256": "29f5157a5ca6c185eae93eb5229afeb06db65741171f9e14cf7661db7796cefa",
                    "git": ("aeddf52", "scripts/stage3/judge_openrouter.py"),
                    "role": "the OpenRouter client before brief 23 (fork history's only earlier version; 07p's records carry no client hash)"},
    "jo_e812157c": {"sha256": "e812157cb991445c12cd4c9197505b27cc03c04f1b23dbde447d417d88b71034",
                    "file": "work/checks/judge_openrouter.py", "role": "current; pinned by plan.md (S1)"},
}
BOUND, CURRENT, CONVERSE_BASE, PREVIOUS = "jc_1675a966", "jc_72d394e3", "jc_8390cfd7", "jc_80f1bdba"
JO_OLD, JO_NOW = "jo_29f5157a", "jo_e812157c"

SONNET, OPUS, SOL_BEDROCK, SOL_OPENROUTER = ("anthropic.claude-sonnet-5", "anthropic.claude-opus-4-8",
                                             "us.openai.gpt-6-sol", "openai/gpt-6-sol")
JUDGE_NAMES = {"sonnet": "Sonnet 5", "opus48": "Opus 4.8", "sol": "GPT-6 Sol"}
VOLATILE = ("ts", "latency_s")
RAW_REPLY_KEYS = ("text", "raw", "raw_text", "raw_reply", "reply", "response", "response_text", "content", "message",
                  "output", "completion", "choices")
# The stub's one reply, written here (never taken from a cache).
STUB_TEXT = '{"score": 12, "flag": false, "rationale": "stub reply"}'


# ── loading the client versions ─────────────────────────────────────────────

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def source_text(name: str) -> str:
    """The client version's bytes, checked against its sha256 (refuses on a mismatch)."""
    s = SOURCES[name]
    if "git" in s:
        commit, path = s["git"]
        raw = subprocess.run(["git", "-C", str(FORK), "show", f"{commit}:{path}"], check=True, capture_output=True).stdout
    else:
        raw = (ROOT / s["file"]).read_bytes()
    got = sha256_bytes(raw)
    if got != s["sha256"]:
        raise SystemExit(f"refusing: {name} has sha256 {got}, expected {s['sha256']}")
    return raw.decode("utf-8")


def load_module(name: str, text: str, as_file: Path, inject: Mapping[str, types.ModuleType] | None = None) -> types.ModuleType:
    """Execute a client version as its own module. `as_file` keeps its path constants (HERE, FORK) as the working
    copy's; `inject` binds module names (e.g. judge_client) for the duration of its imports."""
    mod = types.ModuleType(name)
    mod.__file__ = str(as_file)
    saved = {k: sys.modules.get(k) for k in (inject or {})}
    sys.modules.update(inject or {})
    sys.modules[name] = mod
    try:
        exec(compile(text, f"{name}.py", "exec"), mod.__dict__)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    return mod


def load_clients() -> dict[str, types.ModuleType]:
    mods = {n: load_module(n, source_text(n), HERE / "judge_client.py") for n in SOURCES if n.startswith("jc_")}
    mods[JO_OLD] = load_module(JO_OLD, source_text(JO_OLD), HERE / "judge_openrouter.py", inject={"judge_client": mods[BOUND]})
    mods[JO_NOW] = load_module(JO_NOW, source_text(JO_NOW), HERE / "judge_openrouter.py", inject={"judge_client": mods[CURRENT]})
    return mods


# ── comparison helpers ──────────────────────────────────────────────────────

def canon(o: Any) -> bytes:
    return json.dumps(o, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=repr).encode("utf-8")


def diff_paths(a: Any, b: Any, pre: str = "") -> list[str]:
    """Field paths where a (bound) and b (current) differ; names only, never values."""
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        out: list[str] = []
        for k in sorted(set(a) | set(b), key=str):
            p = f"{pre}.{k}" if pre else str(k)
            if k not in a:
                out.append(f"{p} (current only)")
            elif k not in b:
                out.append(f"{p} (bound only)")
            else:
                out += diff_paths(a[k], b[k], p)
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [f"{pre} (length)"]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in diff_paths(x, y, f"{pre}[{i}]")]
    return [] if canon(a) == canon(b) else [pre or "(value)"]


def strip_volatile(rec: Mapping[str, Any]) -> dict:
    return {k: v for k, v in rec.items() if k not in VOLATILE}


async def _no_sleep(_s: float) -> None:
    return None


# ── stub transports (record the request, send nothing) ──────────────────────

def a_msg(text: str | None = STUB_TEXT, *, stop_reason: str | None = "end_turn", stop_details: Any = None,
          blocks: list | None = None, inp: int = 1000, out: int = 50) -> Message:
    content = blocks if blocks is not None else ([] if text is None else [TextBlock(type="text", text=text)])
    return Message.model_construct(id="msg_stub", type="message", role="assistant", content=content, model="stub-model",
                                   stop_reason=stop_reason, stop_sequence=None, stop_details=stop_details,
                                   usage=Usage(input_tokens=inp, output_tokens=out))


def status_error(cls: type, code: int) -> BaseException:
    req = httpx2.Request("POST", "https://bedrock-mantle.us-east-1.api.aws/anthropic/v1/messages")
    return cls(f"HTTP {code}", response=httpx2.Response(code, request=req), body=None)


class StubMessages:
    def __init__(self, script: Sequence[Any] = ()):
        self.script = list(script)
        self.calls: list[dict] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(copy.deepcopy(kwargs))
        item = self.script.pop(0) if self.script else a_msg()
        if isinstance(item, BaseException):
            raise item
        return item


class StubAnthropic:
    def __init__(self, script: Sequence[Any] = ()):
        self.messages = StubMessages(script)


def c_resp(text: str | None = STUB_TEXT, stop: str | None = "end_turn", content: list | None = None) -> dict:
    blocks = content if content is not None else ([] if text is None else [{"text": text}])
    return {"output": {"message": {"role": "assistant", "content": blocks}}, "stopReason": stop,
            "usage": {"inputTokens": 1000, "outputTokens": 50, "totalTokens": 1050}}


class ClientError(Exception):
    """botocore's ClientError shape: `.response["Error"]["Code"]`."""

    def __init__(self, code: str):
        super().__init__(code)
        self.response = {"Error": {"Code": code, "Message": code}}


class StubConverse:
    def __init__(self, script: Sequence[Any] = ()):
        self.script = list(script)
        self.calls: list[dict] = []

    def converse(self, **kw: Any) -> Any:
        self.calls.append(copy.deepcopy(kw))
        item = self.script.pop(0) if self.script else c_resp()
        if isinstance(item, BaseException):
            raise item
        return item


def o_resp(content: str | None = STUB_TEXT, finish: str | None = "stop") -> SimpleNamespace:
    return SimpleNamespace(content=content, finish_reason=finish,
                           usage=SimpleNamespace(input_tokens=1000, output_tokens=50, reasoning_tokens=20, cost_usd=0.001))


class StubOpenRouter:
    def __init__(self, script: Sequence[Any] = ()):
        self.script = list(script)
        self.calls: list[dict] = []

    async def complete(self, messages: Sequence[Any], *, temperature: Any = None, max_tokens: Any = None) -> Any:
        self.calls.append({"messages": [m.to_openai() for m in messages], "temperature": temperature, "max_tokens": max_tokens})
        item = self.script.pop(0) if self.script else o_resp()
        if isinstance(item, BaseException):
            raise item
        return item


OR_PRICES = {"prompt": 2.0e-6, "completion": 1.0e-5}


# ── G1: the null packets, rebuilt ───────────────────────────────────────────

def build_null_items(corpus: Path) -> dict[str, list[dict]]:
    """The honest units behind the sealed nulls, as their scorers built them (stage3_views_seal.reproduction_check,
    judge_opus_q1q2.build, stage3_b1_dossier.build_world): {view key: [{label, packet, key}]}."""
    rows = sv.read_jsonl(corpus)
    days = sv.corpus_days(rows)
    base = sv.seed_base()
    paths = sv.class_doc_paths()
    stem = sv.stem_of(corpus)
    tl = {p: sv.document_timeline(rows, p, base) for p in paths}
    out: dict[str, list[dict]] = {
        "P_author": sv.author_items(stem, sv.author_units(rows, paths, days, base, "pair", tl), 0),
        "O_diff": [it for it in sv.cumulative_diff_units(rows, paths, days, base, stem, tl) if it.get("packet") is not None],
    }
    pre = {p: ad.pre_window_state(rows, p, base, days[0]) for p in paths}
    units = ad.dossier_units(tl, paths, days)
    for key in ad.KEYS:
        out[key] = ad.dossier_items(stem, units, key, tl, pre, rows)
    return {k: [{"label": it["label"], "packet": it["packet"], "key": it["key"]} for it in v] for k, v in out.items()}


def cells() -> list[dict]:
    """S3's nine cells, in plan.md section 2.6's order, each with its caller's settings, cache and null."""
    def b1(key: str, judge: str) -> dict:
        model, tag, mt = {"opus48": (OPUS, "b1opus-default", 4000), "sonnet": (SONNET, "b1", jc_mod.MAX_TOKENS)}[judge]
        return {"cell": f"{key}|{judge}", "view_key": key, "judge": judge, "family": "anthropic", "model": model,
                "max_tokens_arg": mt, "system": ad.system_prompt(key), "prompt_version": ad.prompt_version(key),
                "caller": "stage3_b1_dossier.make_client",
                "cache": f"work/stage3/b1/judge-cache.{tag}.{key}.{model.replace('.', '-')}.jsonl",
                "null": "work/stage3/b1/b1-null.json", "null_rows": ("judges", judge, "views", key, "rows"),
                "null_client": "1675a966 (recorded: b1-null.json judges.<judge>.step.judge_client)"}

    def opus(view: str) -> dict:
        return {"cell": f"{view}|opus48", "view_key": view, "judge": "opus48", "family": "anthropic", "model": OPUS,
                "max_tokens_arg": 4000, "system": sv.system_prompt(view, 0), "prompt_version": sv.prompt_version(view, 0),
                "caller": "judge_opus_q1q2.make_client (effort default)",
                "cache": f"work/stage3/q1q2-synthetic/opus48/judge-cache.q1q2opus-default.{view}.anthropic-claude-opus-4-8.jsonl",
                "null": "work/stage3/q1q2-synthetic/opus48/judge-null.json", "null_rows": ("views", view, "rows"),
                "null_client": "not recorded in the null; 1675a966 is 07n part C's own amendment (t1v3-plan.md section 8)"}

    def sonnet(view: str) -> dict:
        return {"cell": f"{view}|sonnet", "view_key": view, "judge": "sonnet", "family": "anthropic", "model": SONNET,
                "max_tokens_arg": None, "system": sv.system_prompt(view, 0), "prompt_version": sv.prompt_version(view, 0),
                "caller": "stage3_views.make_client (max_tokens left at the client default)",
                "cache": f"work/stage3/views/judge-cache.{view}.anthropic-claude-sonnet-5.jsonl",
                "null": "work/stage3/views/calibration-v1.json",
                "null_rows_file": f"work/stage3/views/{ {'P_author': 'p_author_c0', 'O_diff': 'o_diff_cumulative'}[view] }.json",
                "null_rows": ("rows",),
                "null_client": "fdce438b (recorded: views/p_author_c0.json, o_diff_cumulative.json meta.judge_client_sha256); "
                               "not on disk; bridged to 1675a966 by t1v3-plan.md section 8"}

    sol = {"cell": "O_diff|sol", "view_key": "O_diff", "judge": "sol", "family": "converse", "model": SOL_BEDROCK,
           "max_tokens_arg": None, "system": sv.system_prompt("O_diff", 0), "prompt_version": sv.prompt_version("O_diff", 0),
           "caller": "stage3_sol_provider_check / stage3_pilot_archive (BedrockConverseJudge defaults)",
           "cache": "work/stage3/q1q2-synthetic/judge-cache.q1q2extra.O_diff.openai_gpt-6-sol.jsonl",
           "null": "work/stage3/q1q2-synthetic/extra-judge-null.sol.json", "null_rows": ("views", "O_diff", "rows"),
           "null_client": "OpenRouter (judge_openrouter, 07p; inferred 29f5157a); reused on Bedrock after brief 09's provider check (8390cfd7)"}
    return [b1(ad.ISO, "opus48"), opus("P_author"), b1(ad.ISO, "sonnet"), sonnet("P_author"),
            b1(ad.LIVE, "opus48"), b1(ad.LIVE, "sonnet"), sonnet("O_diff"), opus("O_diff"), sol]


CACHE_KEEP = ("cache_key", "view", "label", "outcome", "packet_sha256", "packet_chars", "model", "prompt_version",
              "request_params", "parse_retries", "attempts", "stop_reason", "finish_reason")


def cache_index(path: Path) -> tuple[dict[str, dict], dict]:
    """{cache_key: the record's non-content fields} and the cache's shape (key names, outcome counts). Scores,
    flags and rationales are not kept."""
    idx: dict[str, dict] = {}
    keys: Counter = Counter()
    nested: dict[str, Counter] = {}
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        n += 1
        keys.update(d.keys())
        for k, v in d.items():
            if isinstance(v, dict):
                nested.setdefault(k, Counter()).update(v.keys())
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                nested.setdefault(f"{k}[]", Counter()).update(v[0].keys())
        idx[d["cache_key"]] = {k: d.get(k) for k in CACHE_KEEP}
    shape = {"records": n, "keys": sorted(keys), "keys_on_every_record": sorted(k for k, c in keys.items() if c == n),
             "nested_keys": {k: sorted(c) for k, c in sorted(nested.items())},
             "raw_reply_field": sorted(k for k in keys if k in RAW_REPLY_KEYS),
             "holds_raw_reply_text": any(k in RAW_REPLY_KEYS for k in keys)}
    return idx, shape


def null_labels(cell: Mapping[str, Any]) -> set[str]:
    """The null's unit labels (Sonnet's sealed nulls list their rows in the step-1 output the seal read)."""
    o: Any = json.loads((ROOT / cell.get("null_rows_file", cell["null"])).read_text(encoding="utf-8"))
    for k in cell["null_rows"]:
        o = o[k]
    return {r["label"] for r in o}


async def built_anthropic(mod: types.ModuleType, cell: Mapping[str, Any], items: Sequence[dict]) -> list[tuple[dict | None, dict]]:
    stub = StubAnthropic()
    kw: dict[str, Any] = {"max_tokens": cell["max_tokens_arg"]} if cell["max_tokens_arg"] is not None else {}
    jc = mod.JudgeClient(cache_path=None, concurrency=1, rpm=10**9, model=cell["model"], spend_cap_usd=None, region="us-east-1",
                         client=stub, sleep=_no_sleep, verbose=False, system=cell["system"],
                         prompt_version=cell["prompt_version"], **kw)
    out = []
    for it in items:
        n0 = len(stub.messages.calls)
        rec = await jc.score(cell["view_key"], it["label"], it["packet"])
        out.append((stub.messages.calls[n0] if len(stub.messages.calls) > n0 else None, rec))
    return out


async def built_converse(mod: types.ModuleType, cell: Mapping[str, Any], items: Sequence[dict]) -> list[tuple[dict | None, dict]]:
    stub = StubConverse()
    j = mod.BedrockConverseJudge(None, cell["model"], system=cell["system"], prompt_version=cell["prompt_version"],
                                 concurrency=1, rpm=10**9, region="us-east-1", client=stub, sleep=_no_sleep, verbose=False)
    out = []
    for it in items:
        n0 = len(stub.calls)
        rec = await j.score(cell["view_key"], it["label"], it["packet"])
        out.append((stub.calls[n0] if len(stub.calls) > n0 else None, rec))
    return out


async def built_openrouter(mod: types.ModuleType, cell: Mapping[str, Any], items: Sequence[dict]) -> list[tuple[dict | None, dict]]:
    stub = StubOpenRouter()
    j = mod.OpenRouterJudge(None, SOL_OPENROUTER, system=cell["system"], prompt_version=cell["prompt_version"], prices=OR_PRICES,
                            price_source="stub", concurrency=1, rpm=10**9, client=stub, sleep=_no_sleep, verbose=False)
    out = []
    for it in items:
        n0 = len(stub.calls)
        rec = await j.score(cell["view_key"], it["label"], it["packet"])
        out.append((stub.calls[n0] if len(stub.calls) > n0 else None, rec))
    return out


def sent_fields(family: str, req: Mapping[str, Any]) -> dict:
    """The request as sent, in the recorded request_params' vocabulary (the packet by sha256 and length)."""
    if family == "anthropic":
        msgs = req.get("messages") or []
        out = {"model": req.get("model"), "max_tokens": req.get("max_tokens"), "thinking": req.get("thinking"),
               "system_sha256": jc_mod.sha256(req["system"]) if "system" in req else None,
               "system_chars": len(req["system"]) if "system" in req else None}
        extra = sorted(set(req) - {"model", "max_tokens", "thinking", "messages", "system"})
        packet = msgs[0]["content"] if len(msgs) == 1 and msgs[0].get("role") == "user" else None
    elif family == "converse":
        sys_text = "".join(b.get("text", "") for b in req.get("system") or [])
        msgs = req.get("messages") or []
        out = {"model": req.get("modelId"), "max_tokens": (req.get("inferenceConfig") or {}).get("maxTokens"),
               "temperature": "not sent (provider default)" if "temperature" not in (req.get("inferenceConfig") or {}) else req["inferenceConfig"]["temperature"],
               "reasoning": "provider default" if "additionalModelRequestFields" not in req else "sent",
               "system_sha256": jc_mod.sha256(sys_text), "system_chars": len(sys_text)}
        extra = sorted(set(req) - {"modelId", "system", "messages", "inferenceConfig"})
        packet = msgs[0]["content"][0]["text"] if len(msgs) == 1 and msgs[0].get("role") == "user" and len(msgs[0]["content"]) == 1 else None
    else:   # openrouter
        msgs = req.get("messages") or []
        sys_text = msgs[0]["content"] if msgs and msgs[0].get("role") == "system" else ""
        out = {"max_tokens": req.get("max_tokens"), "temperature": req.get("temperature"),
               "system_sha256": jc_mod.sha256(sys_text), "system_chars": len(sys_text)}
        extra = []
        packet = msgs[1]["content"] if len(msgs) == 2 and msgs[1].get("role") == "user" else None
    out["packet_sha256"] = jc_mod.sha256(packet) if isinstance(packet, str) else None
    out["packet_chars"] = len(packet) if isinstance(packet, str) else None
    out["other_request_keys"] = extra
    return out


def recorded_fields(family: str, rec: Mapping[str, Any]) -> dict:
    rp = dict(rec.get("request_params") or {})
    out = {k: rp.get(k) for k in (("model", "max_tokens", "thinking", "system_sha256", "system_chars") if family == "anthropic"
                                  else ("model", "max_tokens", "temperature", "reasoning", "system_sha256", "system_chars"))}
    if family == "openrouter":
        out.pop("model")
        out.pop("reasoning")
    out["packet_sha256"] = rec.get("packet_sha256")
    out["packet_chars"] = rec.get("packet_chars")
    out["other_request_keys"] = sorted(set(rp) - {"model", "max_tokens", "thinking", "system_sha256", "system_chars",
                                                  "temperature", "reasoning", "api"} - ({"output_config"} if rp.get("output_config") is None else set()))
    return out


def compare_cell(cell: Mapping[str, Any], items: Sequence[dict], idx: Mapping[str, dict], mods: Mapping[str, types.ModuleType],
                 pair: tuple[str, str], family: str, builder: Callable) -> dict:
    """Bound-vs-current request and record equality on every item, and the current request against the record."""
    old = asyncio.run(builder(mods[pair[0]], cell, items))
    new = asyncio.run(builder(mods[pair[1]], cell, items))
    req_diff: Counter = Counter()
    rec_diff: Counter = Counter()
    vs_rec: Counter = Counter()
    n_req_eq = n_rec_eq = n_vs_eq = n_missing = 0
    dig_old, dig_new = hashlib.sha256(), hashlib.sha256()
    keys_now: set[str] = set()
    for it, (ro, reco), (rn, recn) in zip(items, old, new):
        if ro is None or rn is None:
            n_missing += 1
            continue
        bo, bn = canon(ro), canon(rn)
        dig_old.update(bo + b"\n")
        dig_new.update(bn + b"\n")
        keys_now |= set(rn)
        if bo == bn:
            n_req_eq += 1
        else:
            req_diff.update(diff_paths(ro, rn))
        d = diff_paths(strip_volatile(reco), strip_volatile(recn))
        n_rec_eq += not d
        rec_diff.update(d)
        cached = idx[it["key"]]
        d2 = diff_paths(recorded_fields(family, cached), sent_fields(family, rn))
        d2 += [] if recn["cache_key"] == cached["cache_key"] else ["cache_key"]
        n_vs_eq += not d2
        vs_rec.update(d2)
    n = len(items) - n_missing
    return {"pair": [p.split("_", 1)[-1] for p in pair], "compared": n, "not_sent_by_one_client": n_missing,
            "requests_byte_equal": n_req_eq, "request_diff_fields": dict(req_diff),
            "records_equal": n_rec_eq, "record_diff_fields": dict(rec_diff),
            "request_keys_current": sorted(keys_now),
            "requests_digest_bound": dig_old.hexdigest(), "requests_digest_current": dig_new.hexdigest(),
            "sent_vs_recorded_equal": n_vs_eq, "sent_vs_recorded_diff_fields": dict(vs_rec)}


def g1(mods: Mapping[str, types.ModuleType]) -> tuple[list[dict], dict]:
    corpus = ROOT / CORPUS
    if sha256_file(corpus) != CORPUS_SHA256:
        raise SystemExit("refusing: the corpus differs from the sealed corpus")
    built = build_null_items(corpus)
    out, shapes = [], {}
    for cell in cells():
        cp = ROOT / cell["cache"]
        idx, shape = cache_index(cp)
        shapes[cell["cache"]] = shape
        items_all = built[cell["view_key"]]
        rep = [it for it in items_all if it["key"] in idx]
        labels = null_labels(cell)
        null_sub = [idx[it["key"]] for it in rep]
        attempts = Counter(">".join(a.get("outcome") or "?" for a in (r.get("attempts") or [])) for r in null_sub)
        row: dict[str, Any] = {
            "cell": cell["cell"], "view": cell["view_key"], "judge": JUDGE_NAMES[cell["judge"]], "model": cell["model"],
            "family": cell["family"], "caller": cell["caller"],
            "cache": {"path": cell["cache"], "sha256": sha256_file(cp), "records": shape["records"]},
            "null": {"path": cell["null"], "sha256": sha256_file(ROOT / cell["null"]), "rows": len(labels),
                     **({"rows_from": cell["null_rows_file"], "rows_from_sha256": sha256_file(ROOT / cell["null_rows_file"])}
                        if "null_rows_file" in cell else {}),
                     "client": cell["null_client"]},
            "units_rebuilt": len(items_all), "reproduced_in_cache": len(rep),
            "null_labels_reproduced": sum(1 for it in rep if it["label"] in labels),
            "null_records": {"outcomes": dict(Counter(r.get("outcome") for r in null_sub)),
                             "with_reasks": sum(1 for r in null_sub if (r.get("parse_retries") or 0) > 0),
                             "attempt_sequences": dict(attempts),
                             "stop_labels": dict(Counter(r.get("stop_reason") or r.get("finish_reason") for r in null_sub))},
        }
        if cell["family"] == "anthropic":
            row["comparison"] = compare_cell(cell, rep, idx, mods, (BOUND, CURRENT), "anthropic", built_anthropic)
            if cell["judge"] == "sonnet":   # one step further back on Sonnet's path (80f1bdba has no Opus 4.8 entry)
                row["chain_80f1bdba_to_bound"] = compare_cell(cell, rep, idx, mods, (PREVIOUS, BOUND), "anthropic", built_anthropic)
        else:
            row["comparison"] = compare_cell(cell, rep, idx, mods, (CONVERSE_BASE, CURRENT), "converse", built_converse)
            row["off_path_openrouter"] = compare_cell(cell, rep, idx, mods, (JO_OLD, JO_NOW), "openrouter", built_openrouter)
        out.append(row)
        c = row["comparison"]
        print(f"{row['cell']:<26} rebuilt {row['units_rebuilt']:>4} reproduced {row['reproduced_in_cache']:>4} "
              f"compared {c['compared']:>4} bytes-equal {c['requests_byte_equal']:>4} records-equal {c['records_equal']:>4} "
              f"sent=recorded {c['sent_vs_recorded_equal']:>4} {sorted(c['sent_vs_recorded_diff_fields'])}", flush=True)
    return out, shapes


# ── G2: the parser test by construction ─────────────────────────────────────

def text_shapes() -> list[tuple[str, str]]:
    """Every branch of first_cut_monitors._parse_verdict (the default parser of every client version) and the
    shapes of the clients' own tests; written here, never read from a cache."""
    long_r = "r" * 900
    return [
        ("clean json (test_judge_client VERDICT)", '{"score": 72, "flag": true, "rationale": "Changed the gate config then deployed."}'),
        ("clean json, low score (test_judge_openrouter)", '{"score": 12, "flag": false, "rationale": "r"}'),
        ("score 50, model flag false (flag is score >= 50)", '{"score": 50, "flag": false, "rationale": "r"}'),
        ("score 49, model flag true", '{"score": 49, "flag": true, "rationale": "r"}'),
        ("score 0", '{"score": 0, "flag": false, "rationale": "r"}'),
        ("score 100", '{"score": 100, "flag": true, "rationale": "r"}'),
        ("json inside prose", 'Here is my verdict: {"score": 33, "flag": false, "rationale": "r"} Thanks.'),
        ("json in a code fence", '```json\n{"score": 61, "flag": true, "rationale": "r"}\n```'),
        ("surrounding whitespace", '\n\n  {"score": 7, "flag": false, "rationale": "r"}  \n'),
        ("score as a string", '{"score": "42", "flag": false, "rationale": "r"}'),
        ("score as a float", '{"score": 42.9, "flag": false, "rationale": "r"}'),
        ("score as a word", '{"score": "high", "flag": true, "rationale": "r"}'),
        ("score null", '{"score": null, "flag": true, "rationale": "r"}'),
        ("score bool", '{"score": true, "flag": true, "rationale": "r"}'),
        ("score negative", '{"score": -5, "flag": false, "rationale": "r"}'),
        ("score above 100", '{"score": 150, "flag": true, "rationale": "r"}'),
        ("no score key", '{"flag": true, "rationale": "r"}'),
        ("empty object", '{}'),
        ("nested score only", '{"verdict": {"score": 20}}'),
        ("extra keys", '{"score": 25, "flag": false, "rationale": "r", "confidence": 0.8}'),
        ("refused marker, score null (brief 23's marker; opt-in parser only)", '{"refused": true, "score": null, "rationale": "r"}'),
        ("refused marker with a score", '{"refused": true, "score": 0, "flag": false, "rationale": "r"}'),
        ("rationale longer than 600", '{"score": 15, "flag": false, "rationale": "' + long_r + '"}'),
        ("rationale a number", '{"score": 15, "flag": false, "rationale": 3}'),
        ("rationale a list", '{"score": 15, "flag": false, "rationale": ["a", "b"]}'),
        ("rationale missing", '{"score": 15, "flag": false}'),
        ("non-ascii rationale", '{"score": 15, "flag": false, "rationale": "r\\u00e9sum\\u00e9 \\u2014 ok"}'),
        ("truncated json (salvage; test_classify_salvages_truncated_json)", '{"score": 77, "flag": true, "rationale": "cut off he'),
        ("truncated before rationale", '{"score": 64, "fl'),
        ("malformed json with a score (salvage)", '{"score": 63, "rationale": "a" "b"}'),
        ("two json objects (greedy span, salvage)", '{"score": 10, "flag": false} and then {"score": 90, "flag": true}'),
        ("score in prose without braces (salvage)", 'My "score": 30 because nothing changed.'),
        ("four-digit score in a fragment (salvage reads three)", '{"score": 1000, "rationale": "x'),
        ("unparseable prose (test 'I cannot help')", "I cannot help with that."),
        ("plain DECLINED", "DECLINED"),
        ("braces without json", "{not json at all}"),
    ]


def anthropic_shapes() -> list[tuple[str, Message]]:
    refusal = RefusalStopDetails(type="refusal", category="cyber", explanation="classifier")
    out = [(f"end_turn: {n}", a_msg(t)) for n, t in text_shapes()]
    out += [
        ("refusal, no content", a_msg(None, stop_reason="refusal", stop_details=refusal)),
        ("refusal with partial json (test_classify_refusal_even_with_partial_json)", a_msg('{"score": 9', stop_reason="refusal", stop_details=refusal)),
        ("refusal, details None", a_msg(None, stop_reason="refusal")),
        ("refusal, details as a dict", a_msg(None, stop_reason="refusal", stop_details={"type": "refusal", "category": "bio", "explanation": None})),
        ("max_tokens, empty (test_classify_max_tokens_empty_is_errored)", a_msg(None, stop_reason="max_tokens")),
        ("max_tokens, truncated json", a_msg('{"score": 58, "flag": true, "rationale": "trunc', stop_reason="max_tokens")),
        ("max_tokens, full json", a_msg('{"score": 58, "flag": true, "rationale": "r"}', stop_reason="max_tokens")),
        ("end_turn, whitespace only", a_msg("   \n ")),
        ("end_turn, no content", a_msg(None)),
        ("thinking then text", a_msg(blocks=[ThinkingBlock(type="thinking", thinking="considering", signature="sig"),
                                             TextBlock(type="text", text='{"score": 44, "flag": false, "rationale": "r"}')])),
        ("thinking only", a_msg(blocks=[ThinkingBlock(type="thinking", thinking="considering", signature="sig")])),
        ("json split across two text blocks", a_msg(blocks=[TextBlock(type="text", text='{"score": 81, "flag": '),
                                                            TextBlock(type="text", text='true, "rationale": "r"}')])),
        ("stop_sequence with json", a_msg('{"score": 22, "flag": false, "rationale": "r"}', stop_reason="stop_sequence")),
        ("stop_reason None with json", a_msg('{"score": 22, "flag": false, "rationale": "r"}', stop_reason=None)),
        ("content None", Message.model_construct(id="m", type="message", role="assistant", content=None, model="stub-model",
                                                 stop_reason="end_turn", stop_sequence=None, stop_details=None,
                                                 usage=Usage(input_tokens=1, output_tokens=1))),
    ]
    return out


def converse_shapes() -> list[tuple[str, Any]]:
    out = [(f"end_turn: {n}", c_resp(t)) for n, t in text_shapes()]
    out += [
        ("content_filtered with text (test_classify_converse_outcomes)", c_resp("x", stop="content_filtered")),
        ("guardrail_intervened with text", c_resp("x", stop="guardrail_intervened")),
        ("content_filtered, no content", c_resp(None, stop="content_filtered")),
        ("max_tokens, empty", c_resp(None, stop="max_tokens")),
        ("max_tokens, truncated json", c_resp('{"score": 58, "flag": true, "rationale": "trunc', stop="max_tokens")),
        ("reasoning block then text", c_resp(content=[{"reasoningContent": {"reasoningText": {"text": "hmm"}}},
                                                      {"text": '{"score": 72, "flag": true, "rationale": "r"}'}])),
        ("reasoning only", c_resp(content=[{"reasoningContent": {"reasoningText": {"text": "hmm"}}}])),
        ("json split across two text blocks", c_resp(content=[{"text": '{"score": 81, "flag": '}, {"text": 'true, "rationale": "r"}'}])),
        ("text block with text None", c_resp(content=[{"text": None}])),
        ("whitespace only", c_resp("  \n")),
        ("stopReason None with json", c_resp('{"score": 22, "flag": false, "rationale": "r"}', stop=None)),
        ("no output", {"stopReason": "end_turn", "usage": {}}),
        ("response None", None),
    ]
    return out


def openrouter_shapes() -> list[tuple[str, Any]]:
    out = [(f"stop: {n}", o_resp(t)) for n, t in text_shapes()]
    out += [
        ("content_filter (test_classify_outcomes)", o_resp("x", finish="content_filter")),
        ("refusal finish", o_resp("x", finish="refusal")),
        ("length, empty", o_resp("", finish="length")),
        ("length, truncated json", o_resp('{"score": 58, "flag": true, "rationale": "trunc', finish="length")),
        ("content None", o_resp(None)),
        ("whitespace only", o_resp("  \n")),
        ("finish None with json", o_resp('{"score": 22, "flag": false, "rationale": "r"}', finish=None)),
    ]
    return out


def classify_equal(shapes: Sequence[tuple[str, Any]], old: Callable, new: Callable, new_none: Callable) -> dict:
    diffs: dict[str, list[str]] = {}
    outcomes: Counter = Counter()
    n_eq = 0
    for name, resp in shapes:
        a, b, c = old(copy.deepcopy(resp)), new(copy.deepcopy(resp)), new_none(copy.deepcopy(resp))
        d = diff_paths(a, b) + [f"{p} (parse=None)" for p in diff_paths(a, c)]
        outcomes[a["outcome"]] += 1
        if d:
            diffs[name] = d
        else:
            n_eq += 1
    return {"shapes": len(shapes), "equal": n_eq, "differences": diffs, "outcomes_bound": dict(outcomes)}


def anthropic_sequences() -> list[tuple[str, list]]:
    ok = a_msg('{"score": 72, "flag": true, "rationale": "r"}')
    ref = a_msg(None, stop_reason="refusal", stop_details=RefusalStopDetails(type="refusal", category="cyber", explanation="c"))
    empty = a_msg(None, stop_reason="max_tokens")
    prose = a_msg("I cannot help with that.")
    return [
        ("scored", [ok]),
        ("refusal then scored (one refusal re-ask)", [ref, ok]),
        ("refusal twice (refused after one re-ask)", [ref, ref]),
        ("empty then scored", [empty, ok]),
        ("unparseable three times (errored after two re-asks)", [prose, prose, prose]),
        ("unparseable then refusal twice", [prose, ref, ref]),
        ("refusal then unparseable three times", [ref, prose, prose, prose]),
        ("salvaged truncated reply", [a_msg('{"score": 77, "flag": true, "rationale": "cut', stop_reason="max_tokens")]),
        ("HTTP 500 then scored (transient retry)", [status_error(anthropic.InternalServerError, 500), ok]),
        ("HTTP 529 four times (errored after three retries)", [status_error(anthropic.InternalServerError, 529)] * 4),
        ("HTTP 429 then scored (pause and retry)", [status_error(anthropic.RateLimitError, 429), ok]),
        ("connection error then scored", [anthropic.APIConnectionError(request=httpx2.Request("POST", "https://x")), ok]),
        ("HTTP 403 first (abort)", [status_error(anthropic.PermissionDeniedError, 403)]),
        ("refusal then HTTP 403 (abort after a paid attempt)", [ref, status_error(anthropic.PermissionDeniedError, 403)]),
        ("unparseable then HTTP 404 (abort after a paid attempt)", [prose, status_error(anthropic.NotFoundError, 404)]),
    ]


def converse_sequences() -> list[tuple[str, list]]:
    ok = c_resp('{"score": 72, "flag": true, "rationale": "r"}')
    prose = c_resp("I cannot help.")
    return [
        ("scored", [ok]),
        ("refusal (not re-asked)", [c_resp("x", stop="content_filtered")]),
        ("unparseable then scored", [prose, ok]),
        ("unparseable three times", [prose, prose, prose]),
        ("throttled then scored", [ClientError("ThrottlingException"), ok]),
        ("transient then scored", [ClientError("InternalServerException"), ok]),
        ("ValidationException first (abort)", [ClientError("ValidationException")]),
        ("unparseable then AccessDenied (abort after a paid attempt)", [prose, ClientError("AccessDeniedException")]),
    ]


def run_loop(mod: types.ModuleType, family: str, script: list, cache_dir: Path) -> dict:
    """One unit through a client version's whole scoring loop with a scripted stub; -> the returned record (or the
    abort), the number of requests and the cache file's lines (volatile fields aside)."""
    cp = cache_dir / f"{family}.jsonl"
    if cp.exists():
        cp.unlink()
    if family == "anthropic":
        stub = StubAnthropic(script)
        j = mod.JudgeClient(cache_path=cp, model=SONNET, spend_cap_usd=None, region="us-east-1", client=stub,
                            sleep=_no_sleep, verbose=False, system="sys", prompt_version="v")
        calls = stub.messages.calls
    else:
        stub = StubConverse(script)
        j = mod.BedrockConverseJudge(cp, SOL_BEDROCK, system="sys", prompt_version="v", region="us-east-1", client=stub,
                                     sleep=_no_sleep, verbose=False)
        calls = stub.calls
    try:
        res: Any = strip_volatile(asyncio.run(j.score("O_diff", "unit", "packet")))
    except mod.JudgeAborted as exc:
        res = {"raised": "JudgeAborted", "message": str(exc)}
    lines = [strip_volatile(json.loads(x)) for x in cp.read_text(encoding="utf-8").splitlines()] if cp.exists() else []
    return {"result": res, "requests": len(calls), "cache_lines": lines}


def loop_equal(sequences: Callable[[], list[tuple[str, list]]], old: types.ModuleType, new: types.ModuleType, family: str) -> dict:
    """Each client version gets its own freshly built script (exceptions are not copied between runs)."""
    diffs: dict[str, list[str]] = {}
    n_eq = 0
    with tempfile.TemporaryDirectory() as td:
        a_dir, b_dir = Path(td) / "a", Path(td) / "b"
        a_dir.mkdir()
        b_dir.mkdir()
        for (name, sa), (_n, sb) in zip(sequences(), sequences()):
            a, b = run_loop(old, family, sa, a_dir), run_loop(new, family, sb, b_dir)
            d = diff_paths(a, b)
            if d:
                diffs[name] = d
            else:
                n_eq += 1
    return {"sequences": len(sequences()), "equal": n_eq, "differences": diffs}


def cross_provider(mods: Mapping[str, types.ModuleType]) -> dict:
    """Sol's null parsed its replies on OpenRouter (29f5157a); S3 parses Sol's on Converse (72d394e3). On the same
    reply text the two wrappers give the same outcome, score, flag and rationale."""
    keys = ("outcome", "score", "flag", "rationale")
    diffs: dict[str, list[str]] = {}
    n_eq = 0
    for name, t in text_shapes():
        a = mods[JO_OLD].classify(o_resp(t))
        b = mods[CURRENT].classify_converse(c_resp(t))
        d = diff_paths({k: a.get(k) for k in keys}, {k: b.get(k) for k in keys})
        if d:
            diffs[name] = d
        else:
            n_eq += 1
    return {"texts": len(text_shapes()), "equal": n_eq, "differences": diffs,
            "refusal_signals": "provider-specific by construction: OpenRouter finish_reason content_filter / refusal; "
                               "Converse stopReason content_filtered / guardrail_intervened"}


def g2(mods: Mapping[str, types.ModuleType]) -> dict:
    o, n = mods[BOUND], mods[CURRENT]
    cb = mods[CONVERSE_BASE]
    jo_o, jo_n = mods[JO_OLD], mods[JO_NOW]
    return {
        "label": "by construction, not by re-parse",
        "default_parser": {"module": "work/mole-fork/scripts/first_cut_monitors.py", "function": "_parse_verdict",
                           "sha256": sha256_file(FORK / "scripts" / "first_cut_monitors.py"),
                           "same_object_in_every_client": all(m._parse_verdict is jc_mod._parse_verdict for m in (o, n, cb))},
        "anthropic_classify": classify_equal(anthropic_shapes(), o.classify, n.classify, lambda r: n.classify(r, None)),
        "anthropic_classify_80f1bdba_to_bound": classify_equal(anthropic_shapes(), mods[PREVIOUS].classify, o.classify, o.classify),
        "anthropic_loop_80f1bdba_to_bound": loop_equal(anthropic_sequences, mods[PREVIOUS], o, "anthropic"),
        "anthropic_loop": loop_equal(anthropic_sequences, o, n, "anthropic"),
        "converse_classify": classify_equal(converse_shapes(), cb.classify_converse, n.classify_converse,
                                            lambda r: n.classify_converse(r, None)),
        "converse_loop": loop_equal(converse_sequences, cb, n, "converse"),
        "openrouter_classify_off_path": classify_equal(openrouter_shapes(), jo_o.classify, jo_n.classify, lambda r: jo_n.classify(r, None)),
        "sol_null_to_s3_cross_provider": cross_provider(mods),
        "defaults": {name: {"bound": getattr(o, name, None), "current": getattr(n, name, None)}
                     for name in ("MAX_TOKENS", "DEFAULT_MODEL", "MAX_PARSE_RETRIES", "MAX_REFUSAL_RETRIES", "MAX_429_RETRIES",
                                  "MAX_TRANSIENT_RETRIES", "TRANSIENT_BACKOFF_S", "RATE_LIMIT_PAUSE_S", "DEFAULT_SPEND_CAP_USD",
                                  "REQUEST_TIMEOUT_S", "PROVIDER")}
                    | {"ABORT_STATUSES": {"bound": sorted(o.ABORT_STATUSES), "current": sorted(n.ABORT_STATUSES)},
                       "PRICES[sonnet-5, opus-4-8]": {"bound": {m: o.PRICES[m] for m in (SONNET, OPUS)},
                                                       "current": {m: n.PRICES[m] for m in (SONNET, OPUS)}},
                       "CONVERSE_MAX_TOKENS": {"bound": cb.CONVERSE_MAX_TOKENS, "current": n.CONVERSE_MAX_TOKENS},
                       "CONVERSE_PRICES[us.openai.gpt-6-sol]": {"bound": cb.CONVERSE_PRICES[SOL_BEDROCK], "current": n.CONVERSE_PRICES[SOL_BEDROCK]},
                       "openrouter MAX_TOKENS, TEMPERATURE": {"bound": [jo_o.MAX_TOKENS, jo_o.TEMPERATURE], "current": [jo_n.MAX_TOKENS, jo_n.TEMPERATURE]}},
    }


# ── main ────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(ROOT / OUT))
    ns = ap.parse_args(argv)
    mods = load_clients()
    rows, shapes = g1(mods)
    parser = g2(mods)
    for k in ("anthropic_classify", "anthropic_loop", "anthropic_classify_80f1bdba_to_bound", "anthropic_loop_80f1bdba_to_bound", "converse_classify", "converse_loop", "openrouter_classify_off_path",
              "sol_null_to_s3_cross_provider"):
        v = parser[k]
        tot = v.get("shapes", v.get("sequences", v.get("texts")))
        print(f"G2 {k:<34} {v['equal']}/{tot} equal; differences: {sorted(v['differences'])}", flush=True)
    out = {"version": VERSION, "brief": "31 (645ceb96)", "script_sha256": sha256_file(Path(__file__)),
           "clients": {k: {"sha256": v["sha256"], "source": (f"fork {v['git'][0]}:{v['git'][1]}" if "git" in v else v["file"]),
                           "role": v["role"]} for k, v in SOURCES.items()},
           "corpus": {"path": CORPUS, "sha256": CORPUS_SHA256},
           "pinned_view_modules": {m: sha256_file(HERE / m) for m in ("stage3_views.py", "stage3_author_doc.py", "stage3_b1_dossier.py")},
           "g1_cells": rows, "g2_cache_shapes": shapes, "g2_parser": parser}
    Path(ns.out).write_text(json.dumps(out, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote {ns.out} sha256 {sha256_file(Path(ns.out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
