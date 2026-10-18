#!/usr/bin/env python3
"""O view (TRACK-B part 2 section 6 / Amendment 1 A6 sanity line): the same per-account judge,
shown each coalition's JOINED account-day, one call per (coalition instance, branch day).

Unit: (instance, date) for every instance of --branch-id in --coalitions (loaded with
mole.generator.coalitions.load_coalitions) and every branch day of --corpus, i.e. every date
present in the corpus that is after the resume manifest's branch_from.day (optionally
restricted by --days). A (instance, date) on which NEITHER member has an exit_code == 0
event is skipped (no call, score null, outcome "skipped" in the full document).

Packet: judge_client.group_packet(render_event, PACKET_CAP_CHARS, O_PACKET_INTRO, date,
[(requester, rows), (approver, rows)]) with O_PACKET_INTRO the Stage 1 O intro
(judge_client.O_PACKET_INTRO, verbatim copy of f1_upstream_row.O_PACKET_INTRO). rows = that
account's exit_code == 0 events of the date, sorted by str(ts) with file order on ties
(score_fork_corpus.account_days, identical to the P view). A member with no successful
event that day is KEPT as an empty block ("== Account: x  Actions (0):"), as f1_upstream_row
did for absent pair members. Block order: requester, then approver (the coalition file's
role order). Label "<corpus stem>:O:<instance id>/<date>", view "O".

Scoring: judge_client.JudgeClient.score_many exactly as score_fork_corpus (same request
params: JUDGE_SYSTEM, max_tokens 900, thinking disabled for a non-5-5 id, no temperature;
refusal -> outcome "refused", no parseable score / transport failure -> "errored"). Cache
and resume as score_fork_corpus: --cache must carry the model id (score_expensive_tier.
check_cache); scored/refused records are served from it, errored ones re-asked.

Outputs: --out = the plain {instance_id: {date: score|null}} mapping (what the measurement
code reads as --o-scores); <out minus .json>.full.json = {meta, scores, outcomes, packets}.
--smoke N scores N items spread over (date, instance) and writes ONLY
<out minus .json>.smoke.json (full-document format). --dry-run builds every packet, prints
the count, chars and a cost estimate (score_fork_corpus.estimate constants) and writes
nothing.

    cd /abs/work/mole-fork && set -a && source .env && set +a && \\
      .venv/bin/python -I /abs/work/checks/score_o_view.py \\
        --corpus /abs/work/mole-fork/data/corpus/spike/branch_A_r2.jsonl --branch-id A \\
        --coalitions /abs/work/mole-fork/bootstrap/coalitions_stage2b.yaml \\
        --out /abs/work/stage2/scores/branch_A_r2.o-view.json \\
        --cache /abs/work/stage2/scores/judge-cache.o-view.branch_A_r2.anthropic-claude-sonnet-5.jsonl \\
        --model anthropic.claude-sonnet-5 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent                      # work/checks
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402  (also puts the fork on sys.path)
from judge_client import (  # noqa: E402
    JUDGE_SYSTEM, O_PACKET_INTRO, PACKET_CAP_CHARS, PRICES, PROMPT_VERSION, PROVIDER,
    JudgeAborted, JudgeClient, cache_key, get_render_event, group_packet,
)
import score_expensive_tier as set_  # noqa: E402
import score_fork_corpus as sfc  # noqa: E402
from mole.generator.coalitions import load_coalitions  # noqa: E402

VIEW = "O"
INTRO_NAME = "judge_client.O_PACKET_INTRO"


def out_sibling(out: Path, suffix: str) -> Path:
    """<out minus .json><suffix>: x.o-view.json -> x.o-view.full.json."""
    out = Path(out)
    stem = out.name[: -len(".json")] if out.name.endswith(".json") else out.name
    return out.with_name(stem + suffix)


def branch_days(corpus: Path, events: list[dict], days_arg: str | None) -> tuple[list[str], dict]:
    m = json.loads((corpus.parent / (corpus.name + ".resume.json")).read_text(encoding="utf-8"))
    bf = (m.get("branch_from") or {}).get("day")
    if not bf:
        raise SystemExit(f"{corpus.name}.resume.json has no branch_from.day")
    present = sorted({str(e.get("ts") or "")[:10] for e in events if e.get("ts")})
    days = [d for d in present if d > bf]
    if days_arg:
        want = [d.strip() for d in days_arg.split(",") if d.strip()]
        bad = [d for d in want if d not in days]
        if bad:
            raise SystemExit(f"--days {bad} are not branch days of {corpus.name} ({days})")
        days = [d for d in days if d in want]
    return days, m


def build_items(stem: str, instances, days: list[str], rows: dict,
                render_event=None) -> tuple[list[dict], list[dict]]:
    """-> (items to score, skipped (instance, date) with neither member active)."""
    render_event = render_event or get_render_event()
    items, skipped = [], []
    for inst in instances:
        members = [inst.roles["requester"], inst.roles["approver"]]
        for d in days:
            blocks = [(a, rows.get((a, d), [])) for a in members]
            n_ev = {a: len(r) for a, r in blocks}
            if not any(n_ev.values()):
                skipped.append({"instance": inst.id, "date": d, "n_events": n_ev})
                continue
            pk, trunc = group_packet(render_event, PACKET_CAP_CHARS, O_PACKET_INTRO, d, blocks)
            label = f"{stem}:O:{inst.id}/{d}"
            items.append({"instance": inst.id, "account": inst.id, "date": d, "label": label,
                          "packet": pk, "truncated": bool(trunc), "n_events": n_ev,
                          "key": cache_key(VIEW, label, pk)})
    return items, skipped


async def score_items(jc: JudgeClient, items: list[dict], batch_log_path: Path,
                      cache_path: Path) -> tuple[dict[str, dict], str | None]:
    """set_.score_items with view "O": -> ({label: record}, abort reason or None)."""
    t0 = time.monotonic()
    stop = asyncio.Event()
    mon = asyncio.create_task(set_._progress(jc, len(items), batch_log_path, t0, stop))
    aborted, recs = None, None
    try:
        recs = await jc.score_many([(VIEW, it["label"], it["packet"]) for it in items])
    except JudgeAborted as exc:
        aborted = str(exc) or (jc.abort or "aborted")
    finally:
        stop.set()
        await mon
    if recs is not None:
        return {it["label"]: r for it, r in zip(items, recs)}, None
    latest = set_.latest_records(cache_path)
    out = {}
    for it in items:
        r = jc.cache.get(it["key"]) or latest.get(it["key"])
        if r is not None:
            out[it["label"]] = r
    return out, aborted


async def amain(ns, client_factory: Callable[..., JudgeClient] = JudgeClient) -> int:
    t_start = time.time()
    corpus, coal, out, cache_path = Path(ns.corpus), Path(ns.coalitions), Path(ns.out), Path(ns.cache)
    for p, what in ((corpus, "--corpus"), (coal, "--coalitions")):
        if not p.is_absolute() or not p.exists():
            raise SystemExit(f"{what} must be an existing absolute path: {p}")
    for p, what in ((out, "--out"), (cache_path, "--cache")):
        if not p.is_absolute():
            raise SystemExit(f"{what} must be absolute: {p}")
    if not out.name.endswith(".json"):
        raise SystemExit("--out must end in .json")
    stem = corpus.name[: -len(".jsonl")] if corpus.name.endswith(".jsonl") else corpus.stem
    model = set_.resolve_model(ns.model)
    if model not in PRICES:
        raise SystemExit(f"no price for model {model!r}")
    batch_log_path = Path(ns.batch_log) if ns.batch_log else out.parent / "judge-batches.jsonl"
    n_cache_records = set_.check_cache(cache_path, model)

    instances = load_coalitions(coal, ns.branch_id)
    events, skipped_lines = sfc.read_jsonl(corpus)
    days, manifest = branch_days(corpus, events, ns.days)
    mstat = sfc.manifest_status(corpus)
    mc = manifest.get("coalitions") or {}
    checks = {"manifest_branch_id": mc.get("branch_id"),
              "branch_id_matches": mc.get("branch_id") == ns.branch_id,
              "manifest_coalitions_sha256": mc.get("file_sha256"),
              "coalitions_sha256": set_.sha256_file(coal),
              "manifest_days": [d.get("day") for d in manifest.get("days") or []]}
    checks["coalitions_sha256_matches"] = checks["manifest_coalitions_sha256"] == checks["coalitions_sha256"]
    checks["days_match_manifest"] = (ns.days is not None) or days == checks["manifest_days"]
    if not checks["branch_id_matches"]:
        raise SystemExit(f"--branch-id {ns.branch_id} but {corpus.name} manifest says {mc.get('branch_id')}")
    if not checks["coalitions_sha256_matches"]:
        print(f"WARNING: coalitions file sha256 differs from the corpus manifest's", file=sys.stderr)
    if not checks["days_match_manifest"]:
        print(f"WARNING: branch days {days} != manifest days {checks['manifest_days']}", file=sys.stderr)
    if mstat and mstat["past_last_boundary"]:
        print(f"WARNING: {corpus.name} extends past its manifest's last day boundary", file=sys.stderr)

    _, _, rows = sfc.account_days(events)
    items, skipped = build_items(stem, instances, days, rows, getattr(ns, "render_event", None))
    est = sfc.estimate(items)
    cached_keys = set(set_.latest_records(cache_path)) if cache_path.exists() else set()
    n_cached = sum(1 for it in items if it["key"] in cached_keys)
    print(f"model={model} corpus={corpus.name} branch={ns.branch_id} instances="
          f"{[i.id for i in instances]} days={days}; cache {cache_path.name} ({n_cache_records} records)",
          file=sys.stderr)
    print(f"{len(items)} O calls ({len(skipped)} skipped: neither member active), "
          f"{est['packet_chars']:,} packet chars, {est['n_truncated']} truncated; "
          f"{n_cached} already in the cache; estimate ${est['est_cost_usd']:.2f} "
          f"(${est['est_cost_usd'] / max(1, len(items)):.4f}/call, chars/{sfc.EST_CHARS_PER_TOKEN}, "
          f"{sfc.EST_OUTPUT_TOKENS} out tok, ${sfc.EST_INPUT_USD_PER_MTOK:g}/${sfc.EST_OUTPUT_USD_PER_MTOK:g} per MTok)",
          file=sys.stderr)
    if ns.dry_run:
        print(json.dumps({"dry_run": True, "corpus": str(corpus), "branch_id": ns.branch_id,
                          "model": model, "days": days, "instances": [i.id for i in instances],
                          "n_calls": len(items), "n_skipped": len(skipped),
                          "n_already_cached": n_cached, "checks": checks, **est,
                          "packets": {it["label"]: {"chars": len(it["packet"]),
                                                    "truncated": it["truncated"],
                                                    "n_events": it["n_events"]} for it in items}}))
        return 0

    target = set_.smoke_select(items, ns.smoke) if ns.smoke else items
    jc = client_factory(cache_path=cache_path, concurrency=ns.concurrency, rpm=ns.rpm,
                        model=model, spend_cap_usd=ns.spend_cap_usd)
    recs, aborted = await score_items(jc, target, batch_log_path, cache_path)
    note = f"score_o_view {'smoke ' + str(ns.smoke) if ns.smoke else 'full'} {stem}"
    jc.batch_log(batch_log_path, note=note + (" ABORTED" if aborted else ""))
    st = jc.stats()

    scores: dict[str, dict] = {i.id: {} for i in instances}
    outcomes: dict[str, dict] = {i.id: {} for i in instances}
    packets: dict[str, dict] = {i.id: {} for i in instances}
    records: dict[str, dict] = {i.id: {} for i in instances}
    tset = {it["label"] for it in target}
    for it in items:
        packets[it["instance"]][it["date"]] = {"chars": len(it["packet"]), "truncated": it["truncated"],
                                               "n_events": it["n_events"]}
        if it["label"] not in tset:
            continue
        r = recs.get(it["label"])
        oc = r["outcome"] if r else "missing"
        sc = r.get("score") if r and oc == "scored" else None
        scores[it["instance"]][it["date"]] = sc
        outcomes[it["instance"]][it["date"]] = oc
        if r:
            records[it["instance"]][it["date"]] = {k: r.get(k) for k in (
                "score", "flag", "rationale", "outcome", "stop_reason", "stop_details", "error",
                "input_tokens", "output_tokens", "cost_usd", "model_served", "attempts",
                "latency_s", "ts", "cache_key")}
    if not ns.smoke:
        for s in skipped:
            scores[s["instance"]][s["date"]] = None
            outcomes[s["instance"]][s["date"]] = "skipped"
            packets[s["instance"]][s["date"]] = {"chars": 0, "truncated": False, "n_events": s["n_events"]}
    got = [r for r in recs.values()]
    oc_count = Counter(r["outcome"] for r in got)
    dollars = round(sum(float(r.get("cost_usd") or 0.0) for r in got), 6)
    wall = round(time.time() - t_start, 1)
    meta = {
        "corpus": str(corpus), "corpus_stem": stem, "branch_id": ns.branch_id,
        "coalitions": str(coal), "corpus_manifest": mstat, "checks": checks,
        "instances": {i.id: {"requester": i.roles["requester"], "approver": i.roles["approver"]}
                      for i in instances},
        "days": days, "n_events": len(events), "n_skipped_lines": skipped_lines,
        "model": model, "provider": PROVIDER, "region": jc.region,
        "prompt_version": PROMPT_VERSION, "request_params": jc_mod.request_params(model),
        "judge_system_sha256": jc_mod.sha256(JUDGE_SYSTEM),
        "o_packet_intro": INTRO_NAME, "o_packet_intro_sha256": jc_mod.sha256(O_PACKET_INTRO),
        "packet_cap_chars": PACKET_CAP_CHARS, "view": VIEW,
        "label_format": "<corpus stem>:O:<instance id>/<date>",
        "packet_definition": "group_packet(render_event, PACKET_CAP_CHARS, O_PACKET_INTRO, date, "
                             "[(requester, ok_rows), (approver, ok_rows)]); a member with no "
                             "exit_code==0 event that day is kept as an empty block; "
                             "(instance, date) with neither member active is skipped",
        "n_items": len(items), "n_target": len(target), "n_skipped_inactive": len(skipped),
        "n_calls": len(got), "n_calls_this_run": st["calls"], "n_cached_this_run": st["cached"],
        "counts_by_outcome": {k: oc_count.get(k, 0) for k in ("scored", "refused", "errored")},
        "refused": oc_count.get("refused", 0),
        "dollars": dollars, "dollars_this_run": st["dollars"],
        "estimate": est, "concurrency": ns.concurrency, "rpm": ns.rpm,
        "spend_cap_usd": ns.spend_cap_usd, "cache": str(cache_path), "batch_log": str(batch_log_path),
        "aborted": aborted, "complete": aborted is None and len(got) == len(target),
        "judge_stats": st, "wall_clock_s": wall,
        "script": str(Path(__file__).resolve()),
        "script_sha256": set_.sha256_file(Path(__file__).resolve()),
        "judge_client_sha256": set_.sha256_file(Path(jc_mod.__file__).resolve()),
        "timestamp": set_._now_iso(), "python": sys.version.split()[0],
    }
    doc = {"meta": meta, "scores": scores, "outcomes": outcomes, "packets": packets,
           "records": records}
    out.parent.mkdir(parents=True, exist_ok=True)
    if ns.smoke:
        meta["smoke_n"] = ns.smoke
        p = out_sibling(out, ".smoke.json")
        p.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
        print(f"SMOKE {len(got)}/{len(target)}: {meta['counts_by_outcome']} ${dollars:.4f}; "
              f"scores {[(it['label'], scores[it['instance']].get(it['date'])) for it in target]}; wrote {p}")
    else:
        out.write_text(json.dumps(scores, indent=1), encoding="utf-8")
        out_sibling(out, ".full.json").write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
        print(f"wrote {out} and {out_sibling(out, '.full.json').name}: {len(got)}/{len(target)} records, "
              f"{meta['counts_by_outcome']}, ${dollars:.4f} in records (${st['dollars']:.4f} this run), "
              f"{wall}s", file=sys.stderr)
    if aborted:
        print(f"ABORTED: {aborted}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", required=True, help="absolute path to the branch audit .jsonl")
    ap.add_argument("--branch-id", required=True, choices=["A", "B", "C"])
    ap.add_argument("--coalitions", required=True, help="absolute coalitions-v1 yaml")
    ap.add_argument("--out", required=True, help="absolute output .json ({instance: {date: score}})")
    ap.add_argument("--cache", required=True,
                    help="absolute judge cache .jsonl; its name must carry the model id (dots->dashes)")
    ap.add_argument("--model", default=None, help="default: env JUDGE_MODEL, else " + jc_mod.DEFAULT_MODEL)
    ap.add_argument("--days", default=None, help="comma-separated subset of the branch days")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--rpm", type=int, default=40)
    ap.add_argument("--spend-cap-usd", type=float, default=10.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--smoke", type=int, default=0)
    ap.add_argument("--batch-log", default=None, help="default <out dir>/judge-batches.jsonl")
    return ap


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(amain(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
