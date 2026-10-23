#!/usr/bin/env python3
"""Expensive tier for a FORK audit corpus: one judge-P call per account-day of a fork JSONL
corpus (e.g. work/mole-fork/data/corpus/spike/prefix_v1.jsonl).

Unit: an account-day is (account, ts[:10]) with at least one exit_code == 0 event (a missing
exit_code counts as 0, as in judge_smoke._ok_rows). day_index = rank of the date among the
corpus's distinct dates over ALL audit rows (failed ones included), as in the cheap tier.

Packet (identical to work/checks/judge_smoke.py's fork path): the account-day's
exit_code == 0 events, the raw JSONL event dicts, sorted by str(ts) with file order kept on
ties (judge_smoke._ok_rows), rendered with mole...account_history.render_event through
judge_client.p_packet (P_PACKET_INTRO, PACKET_CAP_CHARS = 150,000 middle elision).
Label "<corpus stem>:<account>/<date>" (judge_smoke's fork label), view "P".

LABEL-BLIND: never reads is_malicious, task ids or transcripts (render_event reads only
ts/service/action/resource_id/args/exit_code/error/result_meta/is_external).

Cache: --cache must carry the model id (dots -> dashes) in its file name; the run refuses a
cache holding records from another model or prompt version (score_expensive_tier.check_cache;
JudgeClient also refuses). Rerun = resume: scored/refused account-days come from the cache,
only missing or errored ones are called.

Outputs: --out parquet (score_expensive_tier.PARQUET_COLUMNS + n_events) and
<out minus .parquet>.meta.json (counts by outcome, dollars, mean tokens, wall-clock, model,
script sha256, score distribution). --smoke N scores N account-days spread over the corpus,
writes <out minus .parquet>.smoke.json with the extrapolation and NO parquet.
--dry-run builds every packet and prints the count, chars and a cost estimate; no client is
built and nothing is called or written.

--view VIEW (Stage 3 design 11.12(b), brief 07f B2; default P_legacy = this script as G0e ran it,
byte-identical packets). P_own / P_ctx: the account-day packet under the SHARED harm text
(stage3_views.py), each ownCloud edit rendered as the account sent it, the audit layer's `edit`
block dropped and, for P_own, the whole-document `content` dropped too; parquet + meta as for
P_legacy, labels "<stem>:<view>:<account>/<date>", one judge cache per view (the cache file
name must carry the view). P_author: one packet per (author, class document) over the corpus
days (`--author-unit author-day` for the robustness units), the author's own changes as diff
hunks with `--context N` lines (0 = none); writes --out as JSON {meta, summary, rows}.
`--base seed|<parent corpus .jsonl>` is the documents' day-0 state (the class seeder's content,
or the parent's end state for a branched corpus); `--authors a,b` restricts P_author to those
accounts.

--whole-key KEY (repeatable; Stage 3 S5.1) lifts the renderer's 4,000-char per-argument cap for
KEY (account_history.whole_key_set), e.g. `--whole-key content` for an ownCloud/GitLab target
document or `--whole-key description --whole-key body` for plane, so P renders the target
document's text whole, as the composed-document O view (score_o_composed.py) does. Without
the flag the packets are byte-identical to before. The keys are recorded in the meta.

    cd /abs/work/mole-fork && set -a && source .env && set +a && \\
      .venv/bin/python -I /abs/work/checks/score_fork_corpus.py \\
        --corpus /abs/work/mole-fork/data/corpus/spike/prefix_v1.jsonl \\
        --out /abs/work/stage2/scores/prefix_v1.expensive.parquet \\
        --cache /abs/work/stage2/scores/judge-cache.prefix_v1.anthropic-claude-sonnet-5.jsonl \\
        --model anthropic.claude-sonnet-5 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import functools
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent                      # work/checks
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402  (also puts the fork on sys.path)
from judge_client import (  # noqa: E402
    JUDGE_SYSTEM, P_PACKET_INTRO, PACKET_CAP_CHARS, PRICES, PROMPT_VERSION, PROVIDER,
    JudgeClient, cache_key, get_render_event, p_packet,
)
import score_expensive_tier as set_  # noqa: E402  (shared table/cache helpers)
import stage3_views as sv  # noqa: E402  (the shared-harm views, brief 07f B2)

VIEW = set_.VIEW                                    # "P"
PARQUET_COLUMNS = set_.PARQUET_COLUMNS + ["n_events"]
# Dry-run estimate constants (fixed by the brief; judge_smoke measured 2.15 chars/token on
# rendered audit rows with the Sonnet 5 tokenizer).
EST_CHARS_PER_TOKEN = 2.15
EST_INPUT_USD_PER_MTOK = 2.00
EST_OUTPUT_USD_PER_MTOK = 10.00
EST_OUTPUT_TOKENS = 230
FLAG_THRESHOLD = 50


# ── corpus -> account-days (judge_smoke-identical rows) ──────────────────

def read_jsonl(path: Path) -> tuple[list[dict], int]:
    """-> (events in file order, number of skipped lines). Only an unparseable LAST line is
    tolerated (a corpus still being appended to); any other bad line raises."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    out, skipped = [], 0
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            if i == len(lines) - 1:
                skipped += 1
                print(f"WARNING: skipped a partial last line of {path} (still being written?)",
                      file=sys.stderr)
                continue
            raise
    return out, skipped


def _ok(e: dict) -> bool:
    return (e.get("exit_code") or 0) == 0


def account_days(events: list[dict]) -> tuple[list[tuple[str, str]], dict[str, int], dict]:
    """-> (sorted unit keys, day_index map, {key: rows}). rows per key are the account-day's
    exit_code == 0 events sorted by str(ts), file order on ties: exactly judge_smoke._ok_rows
    (computed in one pass instead of one scan per account-day)."""
    all_dates = sorted({str(e.get("ts") or "")[:10] for e in events if e.get("ts")})
    day_idx = {d: i + 1 for i, d in enumerate(all_dates)}
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for e in events:
        if _ok(e) and e.get("account") and e.get("ts"):
            groups[(e["account"], str(e["ts"])[:10])].append(e)
    rows = {k: sorted(v, key=lambda e: str(e.get("ts") or "")) for k, v in groups.items()}
    return sorted(rows), day_idx, rows


def build_items(stem: str, keys, day_idx, rows, render_event=None,
                whole_keys: list[str] | None = None) -> list[dict]:
    render_event = render_event or get_render_event()
    if whole_keys:
        render_event = functools.partial(render_event, whole_keys=tuple(whole_keys))
    items = []
    for a, d in keys:
        r = rows[(a, d)]
        pk, trunc = p_packet(render_event, PACKET_CAP_CHARS, a, d, r)
        label = f"{stem}:{a}/{d}"
        items.append({"account": a, "date": d, "day_index": day_idx[d], "label": label,
                      "packet": pk, "truncated": bool(trunc), "n_events": len(r),
                      "key": cache_key(VIEW, label, pk)})
    return items


def estimate(items: list[dict]) -> dict:
    """Cost estimate before any call: input tokens = (system prompt + packet chars) / 2.15,
    230 output tokens per call, $2/MTok in, $10/MTok out; no retries, no cache hits."""
    n = len(items)
    packet_chars = sum(len(it["packet"]) for it in items)
    input_chars = packet_chars + n * len(JUDGE_SYSTEM)
    in_tok = input_chars / EST_CHARS_PER_TOKEN
    out_tok = n * EST_OUTPUT_TOKENS
    usd = (in_tok * EST_INPUT_USD_PER_MTOK + out_tok * EST_OUTPUT_USD_PER_MTOK) / 1e6
    return {"n_account_days": n, "packet_chars": packet_chars,
            "system_chars_per_call": len(JUDGE_SYSTEM), "input_chars": input_chars,
            "est_input_tokens": round(in_tok), "est_output_tokens": out_tok,
            "est_cost_usd": round(usd, 4), "chars_per_token": EST_CHARS_PER_TOKEN,
            "usd_per_mtok_in": EST_INPUT_USD_PER_MTOK, "usd_per_mtok_out": EST_OUTPUT_USD_PER_MTOK,
            "output_tokens_per_call": EST_OUTPUT_TOKENS,
            "n_truncated": sum(1 for it in items if it["truncated"])}


def manifest_status(corpus: Path) -> dict | None:
    """Resume-manifest view of the corpus: days completed and whether the file is longer than
    the last completed day boundary (a run still writing, or a crashed partial day)."""
    p = corpus.parent / (corpus.name + ".resume.json")
    if not p.exists():
        return None
    m = json.loads(p.read_text(encoding="utf-8"))
    days = m.get("days") or []
    size = corpus.stat().st_size
    last = days[-1] if days else None
    return {"n_days_planned": m.get("n_days"), "days_completed": [d.get("day") for d in days],
            "last_audit_bytes": (last or {}).get("audit_bytes"), "file_bytes": size,
            "past_last_boundary": (last is None and size > 0) or
                                  (last is not None and size != int(last.get("audit_bytes") or 0)),
            "branch_from": m.get("branch_from")}


# ── table ────────────────────────────────────────────────────────────────

def make_frame(rows: list[dict]):
    """score_expensive_tier.make_frame (same columns and dtypes) + n_events (int64)."""
    f = set_.make_frame(rows)                 # selects set_.PARQUET_COLUMNS
    f["n_events"] = [int(r["n_events"]) for r in rows]
    f["n_events"] = f["n_events"].astype("int64")
    return f[PARQUET_COLUMNS]


def score_distribution(rows: list[dict]) -> dict:
    """Over scored account-days (the corpus is assumed honest; no label is read)."""
    import numpy as np
    s = np.array([r["score"] for r in rows if r["outcome"] == "scored" and not math.isnan(r["score"])],
                 dtype=float)
    if not len(s):
        return {"n_scored": 0}
    q = lambda p: float(np.percentile(s, p))   # noqa: E731  (linear interpolation)
    return {"n_scored": int(len(s)), "mean": round(float(s.mean()), 3), "p50": q(50), "p90": q(90),
            "p95": q(95), "p99": q(99), "max": float(s.max()),
            f"share_ge_{FLAG_THRESHOLD}": round(float((s >= FLAG_THRESHOLD).mean()), 6),
            f"n_ge_{FLAG_THRESHOLD}": int((s >= FLAG_THRESHOLD).sum()),
            "n_flag_true": int(sum(1 for r in rows if r["outcome"] == "scored" and r["flag"] is True))}


# ── run ──────────────────────────────────────────────────────────────────

async def amain(ns, client_factory: Callable[..., JudgeClient] = JudgeClient) -> int:
    if getattr(ns, "view", "P_legacy") != "P_legacy":
        return await amain_view(ns, client_factory)
    t_start = time.time()
    corpus = Path(ns.corpus)
    if not corpus.is_absolute() or not corpus.exists():
        raise SystemExit(f"--corpus must be an existing absolute path: {corpus}")
    stem = corpus.name[: -len(".jsonl")] if corpus.name.endswith(".jsonl") else corpus.stem
    model = set_.resolve_model(ns.model)
    if model not in PRICES:
        raise SystemExit(f"no price for model {model!r}")
    out = Path(ns.out)
    cache_path = Path(ns.cache)
    batch_log_path = Path(ns.batch_log) if ns.batch_log else out.parent / "judge-batches.jsonl"
    n_cache_records = set_.check_cache(cache_path, model)
    mstat = manifest_status(corpus)
    print(f"model={model} corpus={corpus} cache={cache_path} ({n_cache_records} records)",
          file=sys.stderr)
    if mstat and mstat["past_last_boundary"]:
        print(f"WARNING: {corpus.name} is {mstat['file_bytes']:,} bytes but its manifest's last "
              f"completed day ends at {mstat['last_audit_bytes']} bytes (days completed "
              f"{mstat['days_completed']}); the generator may still be writing it.", file=sys.stderr)

    events, skipped = read_jsonl(corpus)
    keys, day_idx, rows_by_key = account_days(events)
    whole_keys = list(getattr(ns, "whole_key", None) or [])
    items = build_items(stem, keys, day_idx, rows_by_key, getattr(ns, "render_event", None),
                        whole_keys=whole_keys)
    est = estimate(items)
    cached_keys = set(set_.latest_records(cache_path)) if cache_path.exists() else set()
    n_cached = sum(1 for it in items if it["key"] in cached_keys)
    print(f"{est['n_account_days']} account-days over {len(day_idx)} dates, {len(events):,} events; "
          f"{est['packet_chars']:,} packet chars ({est['input_chars']:,} with the system prompt), "
          f"{est['n_truncated']} truncated; {n_cached} already in the cache", file=sys.stderr)
    print(f"estimate: ~{est['est_input_tokens']:,} input tokens (chars/{EST_CHARS_PER_TOKEN}) + "
          f"{est['est_output_tokens']:,} output tokens ({EST_OUTPUT_TOKENS}/call) at "
          f"${EST_INPUT_USD_PER_MTOK:g}/${EST_OUTPUT_USD_PER_MTOK:g} per MTok = "
          f"${est['est_cost_usd']:.2f} (no retries, before cache hits)", file=sys.stderr)
    if ns.dry_run:
        print(json.dumps({"dry_run": True, "corpus": str(corpus), "model": model,
                          "n_dates": len(day_idx), "n_events": len(events),
                          "n_already_cached": n_cached, "whole_keys": whole_keys, **est}))
        return 0

    target = set_.smoke_select(items, ns.smoke) if ns.smoke else items
    jc = client_factory(cache_path=cache_path, concurrency=ns.concurrency, rpm=ns.rpm,
                        model=model, spend_cap_usd=ns.spend_cap_usd)
    raw_rows, aborted = await set_.score_items(jc, target, batch_log_path, cache_path)
    by_label = {it["label"]: it for it in target}
    rows = [{**r, "n_events": by_label[f"{stem}:{r['account']}/{r['date']}"]["n_events"]}
            for r in raw_rows]
    note = f"score_fork_corpus {'smoke ' + str(ns.smoke) if ns.smoke else 'full'} {stem}"
    jc.batch_log(batch_log_path, note=note + (" ABORTED" if aborted else ""))
    st = jc.stats()
    wall = round(time.time() - t_start, 1)
    summ = set_.summarise(rows) if rows else {"n": 0}
    common = {
        "corpus": str(corpus), "corpus_stem": stem, "corpus_manifest": mstat,
        "n_events": len(events), "n_skipped_lines": skipped, "n_dates": len(day_idx),
        "model": model, "provider": PROVIDER, "region": jc.region,
        "prompt_version": PROMPT_VERSION, "request_params": jc_mod.request_params(model),
        "judge_system_sha256": jc_mod.sha256(JUDGE_SYSTEM),
        "p_packet_intro_sha256": jc_mod.sha256(P_PACKET_INTRO),
        "packet_cap_chars": PACKET_CAP_CHARS, "view": VIEW, "whole_keys": whole_keys,
        "label_format": "<corpus stem>:<account>/<date>",
        "concurrency": ns.concurrency, "rpm": ns.rpm, "spend_cap_usd": ns.spend_cap_usd,
        "cache": str(cache_path), "batch_log": str(batch_log_path), "estimate": est,
        "n_target": len(target), "n_rows": len(rows), "aborted": aborted,
        "summary": summ, "score_distribution": score_distribution(rows) if rows else {"n_scored": 0},
        "judge_stats": st, "wall_clock_s": wall,
        "script": str(Path(__file__).resolve()),
        "script_sha256": set_.sha256_file(Path(__file__).resolve()),
        "judge_client_sha256": set_.sha256_file(Path(jc_mod.__file__).resolve()),
        "timestamp": set_._now_iso(), "python": sys.version.split()[0],
    }

    if ns.smoke:
        ext = set_.extrapolate(rows, items, model, ns.concurrency, ns.rpm) if rows else None
        R = {**common, "smoke_n": ns.smoke, "extrapolation": ext,
             "sample": [{k: (None if k == "score" and math.isnan(r[k]) else r[k]) for k in (
                 "account", "date", "day_index", "outcome", "score", "packet_chars", "n_events",
                 "input_tokens", "output_tokens", "cost_usd", "latency_s", "attempts")} for r in rows]}
        set_.sibling(out, ".smoke.json").write_text(json.dumps(R, indent=1, default=str), encoding="utf-8")
        print(f"\nSMOKE {len(rows)}/{ns.smoke} account-days, model {model}: {summ.get('by_outcome')}")
        if ext:
            print(f"  extrapolation to {ext['n_target']}: naive ${ext['naive_cost_usd']:.2f}, ratio "
                  f"${ext['ratio_cost_usd']:.2f}; wall-clock ~{ext['wall_clock_min']:.0f} min")
        print(f"  wrote {set_.sibling(out, '.smoke.json')}")
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
    set_.sibling(out, ".meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    sd = meta["score_distribution"]
    print(f"wrote {out} ({len(rows)}/{len(target)} rows, {summ.get('by_outcome')}, "
          f"${summ.get('dollars_total', 0):.2f} in records) in {wall}s; scores: {sd}", file=sys.stderr)
    if aborted:
        print(f"ABORTED: {aborted}", file=sys.stderr)
        return 1
    return 0


# ── the shared-harm views (brief 07f B2) ─────────────────────────────────

def view_base(ns, rows: list[dict]) -> dict:
    """`--base seed` -> the class seeder's day-0 content; a parent corpus path -> its class
    documents' state at the end of its last day (a branched corpus), through the reader."""
    b = getattr(ns, "base", None) or "seed"
    if b == "seed":
        return sv.seed_base()
    parent = Path(b)
    if not parent.is_absolute() or not parent.exists():
        raise SystemExit(f"--base must be 'seed' or an existing absolute parent corpus: {b}")
    prow = sv.read_jsonl(parent)
    return sv.corpus_end_base(prow, sv.corpus_days(prow)[-1])


def build_view_items(view: str, stem: str, keys, day_idx, rows, render_event=None) -> list[dict]:
    """P_own / P_ctx account-day items (same units as the legacy view)."""
    render_event = render_event or get_render_event()
    items = []
    for a, d in keys:
        r = rows[(a, d)]
        pk, trunc = sv.p_packet(view, render_event, a, d, r)
        label = f"{stem}:{view}:{a}/{d}"
        items.append({"account": a, "date": d, "day_index": day_idx[d], "label": label,
                      "packet": pk, "truncated": bool(trunc), "n_events": len(r),
                      "key": cache_key(view, label, pk)})
    return items


async def amain_view(ns, client_factory: Callable[..., JudgeClient] = JudgeClient) -> int:
    t_start = time.time()
    view, context = ns.view, int(getattr(ns, "context", 0) or 0)
    if view not in ("P_own", "P_ctx", "P_author"):
        raise SystemExit(f"--view must be P_legacy, P_own, P_ctx or P_author, got {view!r}")
    if context and view != "P_author":
        raise SystemExit("--context applies to --view P_author only")
    corpus = Path(ns.corpus)
    if not corpus.is_absolute() or not corpus.exists():
        raise SystemExit(f"--corpus must be an existing absolute path: {corpus}")
    stem = sv.stem_of(corpus)
    model = set_.resolve_model(ns.model)
    if model not in PRICES:
        raise SystemExit(f"no price for model {model!r}")
    out, cache_path = Path(ns.out), Path(ns.cache)
    batch_log_path = Path(ns.batch_log) if ns.batch_log else out.parent / "judge-batches.jsonl"
    events, skipped = read_jsonl(corpus)
    days = sv.corpus_days(events)
    mstat = manifest_status(corpus)
    if view == "P_author":
        base = view_base(ns, events)
        paths = sv.class_doc_paths()
        authors = [a for a in (getattr(ns, "authors", None) or "").split(",") if a] or None
        units = sv.author_units(events, paths, days, base, getattr(ns, "author_unit", "pair") or "pair",
                                authors=authors)
        items = sv.author_items(stem, units, context)
    else:
        keys, day_idx, rows_by_key = account_days(events)
        items = build_view_items(view, stem, keys, day_idx, rows_by_key, getattr(ns, "render_event", None))
    system = sv.system_prompt(view, context)
    est = sv.estimate(items, system, model)
    print(f"view={sv.view_key(view, context)} model={model} corpus={corpus} units={len(items)} "
          f"days={days} packet_chars={est['packet_chars']:,} truncated={est['n_truncated']} "
          f"estimate ${est['est_cost_usd']:.2f}", file=sys.stderr)
    if ns.dry_run:
        print(json.dumps({"dry_run": True, "corpus": str(corpus), "model": model, "view": view,
                          "context": context, "n_units": len(items), "n_dates": len(days),
                          **sv.prompt_record(view, context), **est}))
        return 0
    jc = sv.make_client(view, cache_path, model, context=context, concurrency=ns.concurrency,
                        rpm=ns.rpm, spend_cap_usd=ns.spend_cap_usd, client_factory=client_factory)
    recs, aborted = await sv.score_items(jc, items, view, context)
    jc.batch_log(batch_log_path, note=f"score_fork_corpus {sv.view_key(view, context)} {stem}"
                                      + (" ABORTED" if aborted else ""))
    rows = [sv.to_row(it, recs.get(it["key"])) for it in items]
    summ = sv.summarise(rows)
    meta = {**sv.meta_common(view, context, model, jc),
            "corpus": str(corpus), "corpus_stem": stem, "corpus_manifest": mstat,
            "corpus_sha256": sv.file_sha256(corpus), "n_events": len(events),
            "n_skipped_lines": skipped, "n_dates": len(days), "days": days,
            "base": getattr(ns, "base", None) or "seed",
            "author_unit": getattr(ns, "author_unit", None) if view == "P_author" else None,
            "cache": str(cache_path), "batch_log": str(batch_log_path), "estimate": est,
            "n_units": len(items), "n_rows": len(rows), "aborted": aborted,
            "complete": aborted is None and all(r["outcome"] == "scored" for r in rows),
            "summary": summ, "defect_check": sv.defect_check(summ, packets_ok=est["n_truncated"] == 0),
            "script": str(Path(__file__).resolve()),
            "script_sha256": set_.sha256_file(Path(__file__).resolve()),
            "wall_clock_s": round(time.time() - t_start, 1)}
    out.parent.mkdir(parents=True, exist_ok=True)
    if view == "P_author":
        out.write_text(json.dumps({"meta": meta, "summary": summ, "rows": rows}, indent=1, default=str),
                       encoding="utf-8")
    else:
        frame_rows = [{**r, "packet_truncated": bool(r.get("truncated")), "cache_read_tokens": 0,
                       "provider": PROVIDER, "region": jc.region, "score": (math.nan if r.get("score") is None else float(r["score"]))}
                      for r in rows]
        make_frame(frame_rows).to_parquet(out, index=False)
        meta["view"] = view
        meta["out"] = str(out)
        set_.sibling(out, ".meta.json").write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    print(f"wrote {out}: {summ['by_outcome']}, ${summ['dollars_total']:.2f} in records; "
          f"scores min/median/p95/max = {summ.get('min')}/{summ.get('median')}/{summ.get('p95')}/{summ.get('max')}",
          file=sys.stderr)
    if aborted:
        print(f"ABORTED: {aborted}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", required=True, help="absolute path to the fork audit .jsonl")
    ap.add_argument("--out", required=True, help="absolute output .parquet")
    ap.add_argument("--cache", required=True,
                    help="absolute judge cache .jsonl; its name must carry the model id (dots->dashes)")
    ap.add_argument("--model", default=None, help="default: env JUDGE_MODEL, else " + jc_mod.DEFAULT_MODEL)
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--rpm", type=int, default=40)
    ap.add_argument("--spend-cap-usd", type=float, default=20.0)
    ap.add_argument("--dry-run", action="store_true", help="build packets, print count/chars/estimate; no calls")
    ap.add_argument("--smoke", type=int, default=0, help="score N spread account-days, report, exit")
    ap.add_argument("--batch-log", default=None, help="default <out dir>/judge-batches.jsonl")
    ap.add_argument("--whole-key", action="append", default=[], metavar="KEY",
                    help="arg key rendered without the 4,000-char cap (repeatable), e.g. content")
    ap.add_argument("--view", choices=("P_legacy", "P_own", "P_ctx", "P_author"), default="P_legacy",
                    help="Stage 3 11.12(b) view (default: the legacy release judge, unchanged)")
    ap.add_argument("--context", type=int, default=0,
                    help="P_author: surrounding lines per change (0 = the instrument, 3 = the variant)")
    ap.add_argument("--author-unit", choices=("pair", "author-day"), default="pair",
                    help="P_author unit: (author, document) over the corpus days, or per day")
    ap.add_argument("--authors", default=None, help="P_author: comma-separated accounts to restrict to")
    ap.add_argument("--base", default="seed",
                    help="documents' day-0 state: 'seed' (the class seeder) or a parent corpus path")
    return ap


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(amain(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
