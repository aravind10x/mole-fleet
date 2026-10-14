#!/usr/bin/env python3
"""Track A expensive tier e(a, d): one judge-P call per evaluation account-day of a released
MOLE corpus (pre-registration: work/mole-fork/protocol/TRACK-A.md sections 1 and 3).

Unit and days (identical to work/checks/score_cheap_tier.py): an account-day is
(account, ts[:10]) with at least one exit_code == 0 event; day index = rank of the date among
the corpus's distinct dates (over ALL audit rows, failed ones included); evaluation days 6..30.

Packet (identical to work/checks/judge_smoke.py for the released corpus): the account-day's
exit_code == 0 events sorted by (ts, event_id), each row dict built as judge_smoke.rows_of
does (args via upstream_matchers_as_detectors.parse_args_json), rendered with
mole...account_history.render_event through judge_client.p_packet (P_PACKET_INTRO,
PACKET_CAP_CHARS middle elision). Scored with judge_client.JudgeClient.score_many, view "P",
label "<account>/<date>".

LABEL-BLIND: this script never opens the labels parquet and never reads the audit
`is_malicious` column. The optional --cheap check reads ONLY the columns
account, date, day_index, is_eval_day of the cheap-tier table.

Cache: --cache must carry the model id (dots -> dashes) in its file name, because the
judge cache key (view|label|sha256(packet)) does not; the run refuses to start if any cache
record has a different `model`. A rerun reuses the cache: scored/refused records are served
from it and only missing or errored account-days are called. The spend cap counts every
dollar recorded in the cache file plus this process's spend.

Outputs: --out parquet (one row per account-day that has a record) and
<out minus .parquet>.meta.json. --smoke N scores N account-days spread evenly over the
evaluation days, prints per-call means and the extrapolation to the full set, writes
<out minus .parquet>.smoke.json, and does NOT write the parquet.

    cd work/mole-fork && set -a && source .env && set +a && \\
      JUDGE_MODEL=anthropic.claude-sonnet-5 .venv/bin/python -I \\
      /abs/work/checks/score_expensive_tier.py --data-dir /abs/work/upstream-data \\
      --corpus gpt53_single_day --out /abs/work/stage2/scores/gpt53_single_day.expensive.parquet \\
      --cheap /abs/work/stage2/scores/gpt53_single_day.cheap.parquet --smoke 20
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent                      # work/checks
PROJECT = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402  (also puts the fork on sys.path)
from judge_client import (  # noqa: E402
    DEFAULT_MODEL, JUDGE_SYSTEM, P_PACKET_INTRO, PACKET_CAP_CHARS, PRICES, PROMPT_VERSION,
    PROVIDER, JudgeAborted, JudgeClient, cache_key, get_render_event, p_packet,
)
from upstream_matchers_as_detectors import parse_args_json  # noqa: E402

VIEW = "P"
AUDIT_COLS = ["event_id", "ts", "account", "service", "action", "resource_id", "args",
              "exit_code", "is_external"]           # is_malicious deliberately NOT read
CHEAP_COLS = ["account", "date", "day_index", "is_eval_day"]   # no label column read
PROGRESS_EVERY = 100
BATCH_LOG_EVERY = 500
POLL_S = 2.0

PARQUET_COLUMNS = [
    "account", "date", "day_index", "outcome", "score", "flag", "stop_reason", "stop_category",
    "input_tokens", "output_tokens", "cache_read_tokens", "cost_usd", "model", "model_served",
    "provider", "region", "prompt_version", "packet_chars", "packet_truncated", "attempts",
    "latency_s",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def model_slug(model: str) -> str:
    return model.replace(".", "-")


def default_cache_path(scores_dir: Path, corpus: str, model: str) -> Path:
    return Path(scores_dir) / f"judge-cache.{corpus}.{model_slug(model)}.jsonl"


def sibling(out: Path, suffix: str) -> Path:
    """<out minus .parquet><suffix>, e.g. x.expensive.parquet -> x.expensive.meta.json."""
    out = Path(out)
    stem = out.name[: -len(".parquet")] if out.name.endswith(".parquet") else out.stem
    return out.with_name(stem + suffix)


def parse_days(s: str) -> tuple[int, int]:
    lo, _, hi = s.partition("-")
    lo_i, hi_i = int(lo), int(hi or lo)
    if not 1 <= lo_i <= hi_i:
        raise argparse.ArgumentTypeError(f"bad --days {s!r}")
    return lo_i, hi_i


# ── cache guard ──────────────────────────────────────────────────────────

def check_cache(cache_path: Path, model: str) -> int:
    """Refuse a cache whose file name does not carry the model id, or that holds any record
    (any outcome) for another model or prompt version. Returns the number of records."""
    if model_slug(model) not in Path(cache_path).name:
        raise SystemExit(f"refusing: cache file name {Path(cache_path).name!r} does not carry the "
                         f"model id {model_slug(model)!r} (the cache key does not include the model)")
    if not Path(cache_path).exists():
        return 0
    n, bad = 0, Counter()
    for line in Path(cache_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n += 1
        d = json.loads(line)
        if d.get("model") != model or d.get("prompt_version") != PROMPT_VERSION:
            bad[f"{d.get('model')}|{d.get('prompt_version')}"] += 1
    if bad:
        raise SystemExit(f"refusing: cache {cache_path} holds records for other models or prompt "
                         f"versions {dict(bad)} (configured {model!r}|{PROMPT_VERSION!r})")
    return n


# ── account-days and packets (label-blind) ───────────────────────────────

def load_units(data_dir: Path, corpus: str, days: tuple[int, int]):
    """-> (keys, day_idx, rows_of). keys: sorted (account, date) unit account-days whose
    day index is in `days`. rows_of(key) returns judge_smoke-identical row dicts."""
    import pandas as pd
    df = pd.read_parquet(Path(data_dir) / "data" / "audit" / corpus / "0000.parquet",
                         columns=AUDIT_COLS)
    all_dates = sorted(set(df["ts"].str.slice(0, 10)))
    day_idx = {d: i + 1 for i, d in enumerate(all_dates)}       # = score_cheap_tier.day_index_map
    df = df[df["exit_code"] == 0].copy()
    df["day"] = df["ts"].str.slice(0, 10)
    df = df.sort_values(["ts", "event_id"], kind="stable").reset_index(drop=True)
    groups = df.groupby(["account", "day"], sort=True).indices
    keys = sorted(k for k in groups if days[0] <= day_idx[k[1]] <= days[1])
    col = {c: df[c].to_numpy() for c in AUDIT_COLS}

    def rows_of(key: tuple[str, str]) -> list[dict]:
        out = []
        for j in groups.get(key, []):
            rid = col["resource_id"][j]
            out.append({"ts": col["ts"][j], "service": col["service"][j], "action": col["action"][j],
                        "args": parse_args_json(col["args"][j]), "exit_code": int(col["exit_code"][j]),
                        "resource_id": rid if isinstance(rid, str) and rid else None,
                        "is_external": bool(col["is_external"][j]), "event_id": col["event_id"][j]})
        return out

    return keys, day_idx, rows_of


def build_items(keys, day_idx, rows_of, render_event=None) -> list[dict]:
    render_event = render_event or get_render_event()
    items = []
    for a, d in keys:
        rows = rows_of((a, d))
        pk, trunc = p_packet(render_event, PACKET_CAP_CHARS, a, d, rows)
        label = f"{a}/{d}"
        items.append({"account": a, "date": d, "day_index": day_idx[d], "label": label,
                      "packet": pk, "truncated": bool(trunc), "n_events": len(rows),
                      "key": cache_key(VIEW, label, pk)})
    return items


def check_against_cheap(cheap_path: Path, keys, day_idx, days: tuple[int, int]) -> dict:
    """The account-day set must equal the cheap table's rows with day_index in `days`
    (for 6..30 that is exactly is_eval_day == True); day_index must agree."""
    import pandas as pd
    ch = pd.read_parquet(cheap_path, columns=CHEAP_COLS)
    sel = ch[(ch["day_index"] >= days[0]) & (ch["day_index"] <= days[1])]
    want = {(a, d): int(i) for a, d, i in zip(sel["account"], sel["date"], sel["day_index"])}
    got = {k: day_idx[k[1]] for k in keys}
    res = {"cheap": str(cheap_path), "n_cheap": len(want), "n_ours": len(got),
           "missing": sorted(f"{a}/{d}" for a, d in set(want) - set(got))[:10],
           "extra": sorted(f"{a}/{d}" for a, d in set(got) - set(want))[:10],
           "day_index_mismatch": sorted(f"{a}/{d}" for (a, d), i in got.items()
                                        if (a, d) in want and want[(a, d)] != i)[:10]}
    if days == (6, 30):
        ev = ch[ch["is_eval_day"]]
        res["n_cheap_is_eval_day"] = int(len(ev))
        res["equals_is_eval_day"] = set(zip(ev["account"], ev["date"])) == set(got)
    res["ok"] = not (res["missing"] or res["extra"] or res["day_index_mismatch"]) and \
        res.get("equals_is_eval_day", True)
    return res


def smoke_select(items: list[dict], n: int) -> list[dict]:
    """Deterministic: sort by (date, account), take n positions evenly spaced over the list
    (centre of each of n equal strata), which spreads them across the evaluation days."""
    srt = sorted(items, key=lambda it: (it["date"], it["account"]))
    m = len(srt)
    if n >= m:
        return srt
    return [srt[int((i + 0.5) * m / n)] for i in range(n)]


# ── records -> table ─────────────────────────────────────────────────────

def latest_records(cache_path: Path) -> dict[str, dict]:
    """Last record per cache_key in the cache file (any outcome)."""
    out: dict[str, dict] = {}
    if cache_path and Path(cache_path).exists():
        for line in Path(cache_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                out[d["cache_key"]] = d
    return out


def to_row(it: dict, r: dict) -> dict:
    score = r.get("score")
    return {
        "account": it["account"], "date": it["date"], "day_index": int(it["day_index"]),
        "outcome": r["outcome"],
        "score": float(score) if score is not None else math.nan,
        "flag": r.get("flag"),
        "stop_reason": r.get("stop_reason"),
        "stop_category": (r.get("stop_details") or {}).get("category"),
        "input_tokens": int(r.get("input_tokens") or 0),
        "output_tokens": int(r.get("output_tokens") or 0),
        "cache_read_tokens": int(r.get("cache_read_tokens") or 0),
        "cost_usd": float(r.get("cost_usd") or 0.0),
        "model": r.get("model"), "model_served": r.get("model_served"),
        "provider": r.get("provider"), "region": r.get("region"),
        "prompt_version": r.get("prompt_version"),
        "packet_chars": int(len(it["packet"])),
        "packet_truncated": bool(it["truncated"]),
        "attempts": int(len(r.get("attempts") or [])),
        "latency_s": float(r.get("latency_s") or 0.0),
    }


def make_frame(rows: list[dict]):
    import pandas as pd
    f = pd.DataFrame(rows, columns=PARQUET_COLUMNS)
    f = f.astype({"day_index": "int64", "score": "float64", "flag": "boolean",
                  "input_tokens": "int64", "output_tokens": "int64", "cache_read_tokens": "int64",
                  "cost_usd": "float64", "packet_chars": "int64", "packet_truncated": "bool",
                  "attempts": "int64", "latency_s": "float64"})
    for c in ("account", "date", "outcome", "stop_reason", "stop_category", "model",
              "model_served", "provider", "region", "prompt_version"):
        f[c] = f[c].astype("object")
    return f


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    oc = Counter(r["outcome"] for r in rows)
    mean = (lambda k: (sum(r[k] for r in rows) / n) if n else None)
    return {"n": n, "by_outcome": {k: oc.get(k, 0) for k in ("scored", "refused", "errored")},
            "dollars_total": round(sum(r["cost_usd"] for r in rows), 6),
            "mean_input_tokens": mean("input_tokens"), "mean_output_tokens": mean("output_tokens"),
            "mean_cost_usd": mean("cost_usd"), "mean_latency_s": mean("latency_s"),
            "mean_attempts": mean("attempts"),
            "n_truncated": sum(1 for r in rows if r["packet_truncated"]),
            "refusal_categories": dict(Counter(r["stop_category"] or "none" for r in rows
                                               if r["outcome"] == "refused"))}


def extrapolate(rows: list[dict], all_items: list[dict], model: str, concurrency: int,
                rpm: int) -> dict:
    """Cost and wall-clock for every item in all_items from the measured rows. Input tokens
    are fitted as a + b * packet_chars (least squares) and applied to every packet's size;
    the naive mean-cost x N is also given."""
    n_all = len(all_items)
    n = len(rows)
    p = PRICES[model]
    xs = [r["packet_chars"] for r in rows]
    ys = [r["input_tokens"] / max(1, r["attempts"]) for r in rows]      # per attempt
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    a = my - b * mx
    mean_att = sum(r["attempts"] for r in rows) / n
    mean_out = sum(r["output_tokens"] for r in rows) / n
    total_chars = sum(len(it["packet"]) for it in all_items)
    fit_in = (n_all * a + b * total_chars) * mean_att
    fit_cost = (fit_in * p["input"] + n_all * mean_out * p["output"]) / 1e6
    # ratio estimator (robust to one outlier packet): sample input tokens per packet char
    ratio = sum(r["input_tokens"] for r in rows) / max(1, sum(xs))
    ratio_in = ratio * total_chars
    ratio_cost = (ratio_in * p["input"] + n_all * mean_out * p["output"]) / 1e6
    mean_lat = sum(r["latency_s"] for r in rows) / n
    per_min = min(float(rpm), concurrency * 60.0 / mean_lat) if mean_lat > 0 else float(rpm)
    return {"n_target": n_all, "naive_cost_usd": round(sum(r["cost_usd"] for r in rows) / n * n_all, 2),
            "fit_input_tokens_a": round(a, 1), "fit_tokens_per_char_b": round(b, 5),
            "fit_input_tokens_total": round(fit_in), "fit_cost_usd": round(fit_cost, 2),
            "ratio_input_tokens_per_char": round(ratio, 5), "ratio_input_tokens_total": round(ratio_in),
            "ratio_cost_usd": round(ratio_cost, 2),
            "mean_packet_chars_sample": round(mx), "mean_packet_chars_all": round(total_chars / n_all),
            "mean_latency_s": round(mean_lat, 2), "calls_per_min": round(per_min, 1),
            "binding_limit": "rpm" if per_min >= rpm else "concurrency/latency",
            "wall_clock_min": round(n_all / per_min, 1)}


# ── run ──────────────────────────────────────────────────────────────────

async def _progress(jc: JudgeClient, n_total: int, batch_log_path: Path, t0: float,
                    stop: asyncio.Event) -> None:
    last_p = last_b = 0
    while True:
        try:
            await asyncio.wait_for(stop.wait(), timeout=POLL_S)
            finished = True
        except asyncio.TimeoutError:
            finished = False
        s = jc.stats()
        done = s["calls"] + s["cached"]
        if done // PROGRESS_EVERY > last_p or (finished and done != last_p * PROGRESS_EVERY):
            last_p = done // PROGRESS_EVERY
            print(f"[{done}/{n_total}] calls={s['calls']} cached={s['cached']} scored={s['scored']} "
                  f"refused={s['refused']} errored={s['errored']} 429s={s['n_429']} "
                  f"${s['dollars']:.2f} this run, ${s['dollars_total']:.2f} against cache, "
                  f"{time.monotonic() - t0:.0f}s", file=sys.stderr, flush=True)
        if s["calls"] // BATCH_LOG_EVERY > last_b:
            last_b = s["calls"] // BATCH_LOG_EVERY
            jc.batch_log(batch_log_path, note=f"score_expensive_tier progress calls={s['calls']}")
        if finished:
            return


async def score_items(jc: JudgeClient, items: list[dict], batch_log_path: Path,
                      cache_path: Path) -> tuple[list[dict], str | None]:
    """-> (rows for every item that has a record, abort reason or None)."""
    t0 = time.monotonic()
    stop = asyncio.Event()
    mon = asyncio.create_task(_progress(jc, len(items), batch_log_path, t0, stop))
    aborted = None
    recs: list[dict] | None = None
    try:
        recs = await jc.score_many([(VIEW, it["label"], it["packet"]) for it in items])
    except JudgeAborted as exc:
        aborted = str(exc) or (jc.abort or "aborted")
    finally:
        stop.set()
        await mon
    if recs is not None:
        return [to_row(it, r) for it, r in zip(items, recs)], None
    latest = latest_records(cache_path)
    rows = []
    for it in items:
        r = jc.cache.get(it["key"]) or latest.get(it["key"])
        if r is not None:
            rows.append(to_row(it, r))
    return rows, aborted


def resolve_model(ns_model: str | None) -> str:
    return ns_model or os.environ.get("JUDGE_MODEL") or DEFAULT_MODEL


async def amain(ns, client_factory: Callable[..., JudgeClient] = JudgeClient) -> int:
    t_start = time.time()
    model = resolve_model(ns.model)
    if model not in PRICES:
        raise SystemExit(f"no price for model {model!r}")
    out = Path(ns.out)
    scores_dir = out.parent
    cache_path = Path(ns.cache) if ns.cache else default_cache_path(scores_dir, ns.corpus, model)
    batch_log_path = Path(ns.batch_log) if ns.batch_log else scores_dir / "judge-batches.jsonl"
    days = ns.days if isinstance(ns.days, tuple) else parse_days(ns.days)
    n_cache_records = check_cache(cache_path, model)
    print(f"model={model} cache={cache_path} ({n_cache_records} records) days={days[0]}-{days[1]}",
          file=sys.stderr)

    keys, day_idx, rows_of = load_units(Path(ns.data_dir), ns.corpus, days)
    cheap_check = None
    if ns.cheap:
        cheap_check = check_against_cheap(Path(ns.cheap), keys, day_idx, days)
        print(f"cheap-table check: {cheap_check}", file=sys.stderr)
        if not cheap_check["ok"]:
            raise SystemExit("refusing: account-day set differs from the cheap table")
    items = build_items(keys, day_idx, rows_of, getattr(ns, "render_event", None))
    print(f"{len(items)} account-days on days {days[0]}-{days[1]}, "
          f"{sum(len(i['packet']) for i in items):,} packet chars, "
          f"{sum(i['truncated'] for i in items)} truncated", file=sys.stderr)
    target = smoke_select(items, ns.smoke) if ns.smoke else items

    jc = client_factory(cache_path=cache_path, concurrency=ns.concurrency, rpm=ns.rpm,
                        model=model, spend_cap_usd=ns.spend_cap_usd)
    rows, aborted = await score_items(jc, target, batch_log_path, cache_path)
    note = f"score_expensive_tier {'smoke ' + str(ns.smoke) if ns.smoke else 'full'} {ns.corpus}"
    jc.batch_log(batch_log_path, note=note + (" ABORTED" if aborted else ""))
    st = jc.stats()
    wall = round(time.time() - t_start, 1)
    summ = summarise(rows) if rows else {"n": 0}
    common = {
        "corpus": ns.corpus, "days": list(days), "model": model, "provider": PROVIDER,
        "region": jc.region, "prompt_version": PROMPT_VERSION,
        "request_params": jc_mod.request_params(model),
        "judge_system_sha256": jc_mod.sha256(JUDGE_SYSTEM),
        "p_packet_intro_sha256": jc_mod.sha256(P_PACKET_INTRO),
        "packet_cap_chars": PACKET_CAP_CHARS, "view": VIEW, "label_format": "<account>/<date>",
        "concurrency": ns.concurrency, "rpm": ns.rpm, "spend_cap_usd": ns.spend_cap_usd,
        "cache": str(cache_path), "batch_log": str(batch_log_path), "cheap_check": cheap_check,
        "n_target": len(target), "n_rows": len(rows), "aborted": aborted,
        "summary": summ, "judge_stats": st, "wall_clock_s": wall,
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "judge_client_sha256": sha256_file(Path(jc_mod.__file__).resolve()),
        "timestamp": _now_iso(), "python": sys.version.split()[0],
    }

    if ns.smoke:
        ext = extrapolate(rows, items, model, ns.concurrency, ns.rpm) if rows else None
        R = {**common, "smoke_n": ns.smoke, "extrapolation": ext,
             "sample": [{"account": r["account"], "date": r["date"], "day_index": r["day_index"],
                         "outcome": r["outcome"], "score": None if math.isnan(r["score"]) else r["score"],
                         "packet_chars": r["packet_chars"], "input_tokens": r["input_tokens"],
                         "output_tokens": r["output_tokens"], "cost_usd": r["cost_usd"],
                         "latency_s": r["latency_s"], "attempts": r["attempts"]} for r in rows]}
        sibling(out, ".smoke.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
        print(f"\nSMOKE {len(rows)}/{ns.smoke} account-days, model {model}: {summ.get('by_outcome')}")
        if rows:
            print(f"  per call: input {summ['mean_input_tokens']:,.0f} tok, output "
                  f"{summ['mean_output_tokens']:,.0f} tok, ${summ['mean_cost_usd']:.4f}, latency "
                  f"{summ['mean_latency_s']:.1f}s, attempts {summ['mean_attempts']:.2f}; total "
                  f"${summ['dollars_total']:.4f}; 429s seen {st['n_429']}")
            print(f"  extrapolation to {ext['n_target']}: naive ${ext['naive_cost_usd']:.2f}; "
                  f"fitted (input = {ext['fit_input_tokens_a']:.0f} + {ext['fit_tokens_per_char_b']:.4f}"
                  f" x chars) ${ext['fit_cost_usd']:.2f}; ratio ({ext['ratio_input_tokens_per_char']:.4f} tok/char)"
                  f" ${ext['ratio_cost_usd']:.2f}; wall-clock ~{ext['wall_clock_min']:.0f} min at "
                  f"{ext['calls_per_min']:.1f} calls/min (limit: {ext['binding_limit']})")
        print(f"  wrote {sibling(out, '.smoke.json')}")
        if aborted:
            print(f"ABORTED: {aborted}", file=sys.stderr)
        return 1 if aborted else 0

    frame = make_frame(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, index=False)
    meta = {**common, "out": str(out), "complete": aborted is None and len(rows) == len(target),
            "counts_by_outcome": summ.get("by_outcome"), "dollars_total": summ.get("dollars_total"),
            "mean_tokens_per_call": {"input": summ.get("mean_input_tokens"),
                                     "output": summ.get("mean_output_tokens")},
            "n_missing": len(target) - len(rows)}
    sibling(out, ".meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    print(f"wrote {out} ({len(rows)}/{len(target)} rows, {summ.get('by_outcome')}, "
          f"${summ.get('dollars_total', 0):.2f} in records) in {wall}s", file=sys.stderr)
    if aborted:
        print(f"ABORTED: {aborted}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data-dir", required=True, help="released corpus root (untrusted; absolute path)")
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cache", default=None,
                    help="judge cache JSONL; default <out dir>/judge-cache.<corpus>.<model-slug>.jsonl")
    ap.add_argument("--model", default=None, help="default: env JUDGE_MODEL, else " + DEFAULT_MODEL)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--rpm", type=int, default=40)
    ap.add_argument("--smoke", type=int, default=0, help="score N spread account-days, report, exit")
    ap.add_argument("--spend-cap-usd", type=float, default=300.0)
    ap.add_argument("--days", type=parse_days, default=(6, 30))
    ap.add_argument("--cheap", default=None,
                    help="cheap-tier parquet to check the account-day set against (reads only "
                         "account, date, day_index, is_eval_day)")
    ap.add_argument("--batch-log", default=None, help="default <out dir>/judge-batches.jsonl")
    return ap


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(amain(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
