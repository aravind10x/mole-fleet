#!/usr/bin/env python3
"""Brief 30 Part 3: development and certification reads on a converted writer round. Blue side.

The reads reuse E2's runner (`stage3_elicitation_e1e2`, 7aac0157, unchanged): its `run_experiment` (readers in parallel,
re-issue of unscored reads, then the scorer, two passes, against the item's own composed effect), its `Recs`, its pinned
Kimi K3 constructor (Wafer at MXFP4, key 2) and the reader's own units, labels and caches. This module adds what a
converted writer round needs: the units of a phase, the cache directories that keep the development reads apart from
certification's (protocol section 1: nothing a writer was shown is served again to certification), the per-item
statistics, and the item shape the classifier takes.

No item text, rubric, answer or key is printed or written outside the caches; ids are opaque.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_elicitation_classes as cl
import stage3_elicitation_e1e2 as e12
import stage3_legibility as lg

VERSION = "elicitation-reads/v0"
TARGET = "rubric"                      # every converted item is read against its own composed effect
PHASES = {"dev": {"samples": (0,), "label": "development"}, "cert": {"samples": (0, 1), "label": "certification"}}


def phase_dir(root: Path, writer: str, round_no: int, phase: str) -> Path:
    PHASES[phase]  # KeyError on an unknown phase
    return Path(root) / writer / f"r{round_no}" / phase


def reader_names(writer: str) -> tuple[str, str]:
    return ("kimi", cl.second_reader(writer)[0])


def units_for(rows: Sequence[Mapping[str, Any]], fams: Sequence[str], samples: Sequence[int],
              only_ids: set[str] | None = None) -> dict[str, list[tuple[int, str, str]]]:
    ids = {r["item_id"] for r in rows}
    if only_ids is not None:
        missing = sorted(set(only_ids) - ids)
        if missing:
            raise ValueError(f"ids not in the round: {missing}")
        ids = set(only_ids)
    return {f: [(s, r["item_id"], c) for r in rows if r["item_id"] in ids for s in samples for c in lg.CONDS] for f in fams}


def records(reader_records: Mapping[str, Iterable[Mapping[str, Any]]], scorer_records: Iterable[Mapping[str, Any]]):
    return e12.Recs(reader_records, scorer_records)


def collect(rec: Any, rows: Sequence[Mapping[str, Any]], fams: Sequence[str], samples: Sequence[int]) -> dict[str, dict]:
    """Per item and reader, one entry per sample: D_whole, D_part (None where a condition is refused or missing, never a
    zero) and the statistic's status."""
    out: dict[str, dict] = {}
    for row in rows:
        per: dict[str, dict] = {}
        for f in fams:
            dw, dp, stt, cs = [], [], [], []
            for s in samples:
                st = rec.item_stat(f, s, row, TARGET)
                cs.append({c: (None if v is None else float(v)) for c, v in st["cond_scores"].items()})
                dw.append(None if st["D_whole"] is None else float(st["D_whole"]))
                dp.append(None if st["D_part"] is None else float(st["D_part"]))
                stt.append(st["status"])
            per[f] = {"D_whole": dw, "D_part": dp, "status": stt, "cond_scores": cs}
        out[row["item_id"]] = per
    return out


def collect_dir(d: Path, rows: Sequence[Mapping[str, Any]], fams: Sequence[str], samples: Sequence[int],
                only_ids: set[str] | None = None) -> dict[str, dict]:
    """`collect` from a phase directory's caches, offline ($0): the readers' and the scorer's records as the run left them."""
    cache = Path(d) / "cache"
    readers = {f: lg.read_jsonl(p) for f in fams for p in sorted(cache.glob(f"judge-cache.legibility.read.{f}.*.jsonl"))}
    scorer = [r for p in sorted(cache.glob("judge-cache.legibility.score.*.jsonl")) for r in lg.read_jsonl(p)]
    sel = [r for r in rows if only_ids is None or r["item_id"] in only_ids]
    return collect(records(readers, scorer), sel, fams, samples)


def class_inputs(collected: Mapping[str, Mapping[str, Any]], gate_i_by_id: Mapping[str, bool],
                 fams: Sequence[str]) -> list[dict]:
    items = []
    for item_id in sorted(collected):
        if item_id not in gate_i_by_id:
            raise ValueError(f"item {item_id} has no gate (i) verdict")
        items.append({"id": item_id, "gate_i": bool(gate_i_by_id[item_id]),
                      "readers": {f: {"D_whole": list(collected[item_id][f]["D_whole"]),
                                      "D_part": list(collected[item_id][f]["D_part"])} for f in fams}})
    return items


ORDER_OFFSET = 500   # call-order seed offset (lg.ORDER_SEED + offset), clear of E1's 300 and E2's 400


async def run_round(rows: Sequence[Mapping[str, Any]], packets: Mapping[tuple[str, str], str], readers: Mapping[str, Any],
                    scorer: Any, rubrics: Mapping[str, str], fams: Sequence[str], samples: Sequence[int], guard: Any, log: Path,
                    only_ids: set[str] | None = None, offset: int = ORDER_OFFSET) -> dict:
    """Every named reader on the round's items (or `only_ids`) at the phase's samples, re-issuing unscored reads, then the
    scorer on every answered read against the item's own composed effect, two passes (E2's run_experiment); returns the
    run summary and the per-item statistics."""
    units = units_for(rows, fams, samples, only_ids)
    sel = [r for r in rows if only_ids is None or r["item_id"] in only_ids]
    run = await e12.run_experiment(sel, packets, {f: readers[f] for f in fams}, scorer,
                                   lambda row, cond, target: rubrics[row["item_id"]], units, guard, log, offset)
    rec = records({f: readers[f].cache.values() for f in fams}, scorer.cache.values())
    return {"run": run, "collected": collect(rec, sel, fams, samples)}


# ── the live run (guards as E2's: key-limit record, the pin, cache drift, the spend stop) ──────────────────────

PROJECT = Path(__file__).resolve().parent.parent.parent
ELICIT = PROJECT / "work" / "stage3" / "elicitation"
PART3 = ELICIT / "part3"
READS_ROOT = PART3 / "reads"
LIMITS_DIR = PART3 / "limits"
MODELS = ELICIT / "pricing" / "models-v0.json"
ROUTES23 = PROJECT / "work" / "stage3" / "legibility" / "routes-v0.json"


def cmd_run(ns: Any) -> int:
    import asyncio
    import json
    import judge_client as jc
    import stage3_elicitation_convert as cv
    from collections import Counter
    conv = Path(ns.converted_dir)
    d = phase_dir(Path(ns.out_root), ns.writer, ns.round, ns.phase)
    d.mkdir(parents=True, exist_ok=True)
    day0 = e12.day0_texts()
    items, rubrics = cv.build_reader_items(conv, day0)
    rows = items["items"]
    triples = {t["triple_id"]: t for t in json.loads((conv / "stripped-triples.json").read_text(encoding="utf-8"))}
    packets = lg.all_packets(rows, triples, day0)
    only = None
    if ns.only_ids:
        only = set(json.loads(Path(ns.only_ids).read_text(encoding="utf-8")))
    fams = reader_names(ns.writer)
    samples = PHASES[ns.phase]["samples"]
    stop = float(ns.cap_usd)
    lim = e12._latest_limits(LIMITS_DIR)
    if lim["headroom_usd"] is not None and lim["headroom_usd"] < stop:
        raise SystemExit(f"refusing: headroom ${lim['headroom_usd']:.2f} (the smaller of key 2's limit and the account) is below this run's stop ${stop:.2f}")
    if lg.any_cache_records(d) and not ns.resume:
        raise SystemExit("refusing: calls are already on file; pass --resume to continue this run")
    lg.check_reasoning_env()
    models = json.loads(MODELS.read_text(encoding="utf-8"))
    routes = json.loads(ROUTES23.read_text(encoding="utf-8"))
    import judge_openrouter_pin as pin
    endpoints = pin.fetch_endpoints(pin.KIMI_MODEL)
    listing = pin.listing_from_endpoints(endpoints)
    if pin.served_precision("Wafer", pin.KIMI_K3_WAFER_MXFP4, listing) != "mxfp4":
        raise SystemExit("refusing: Wafer at MXFP4 is not in Kimi K3's endpoint listing")
    (d / "kimi-endpoints.json").write_text(json.dumps({"fetched_at": jc._now_iso(), "listing": listing,
                                                      "sha256": jc.sha256(json.dumps(endpoints, sort_keys=True))}, indent=1) + "\n")
    guard = lg.SpendGuard(stop)
    readers: dict[str, Any] = {}
    for fam in fams:
        if fam == "kimi":
            cp = lg.reader_cache(d, fam, lg.FAMILIES[fam].get("openrouter"))
            readers[fam] = e12.make_pinned_kimi(cp, models, cap=stop, guard=guard, listing=listing)
        else:
            ch = routes["chosen"][fam]
            readers[fam] = lg.make_reader(fam, ch["route"], ch["model"], lg.reader_cache(d, fam, ch["model"]), models, cap=stop, guard=guard)
    scorer = lg.make_scorer(lg.scorer_cache(d), cap=stop, guard=guard)
    drift = {f: lg.cache_drift(c, lg.READER_SYSTEM) for f, c in readers.items()}
    drift["scorer"] = lg.cache_drift(scorer, lg.SCORER_SYSTEM)
    if any(drift.values()):
        raise SystemExit(f"refusing: cached records under another system prompt or max_tokens: {drift}")
    guard.clients = list(readers.values()) + [scorer]
    rub = rubrics["test"]
    summary: dict[str, Any] = {"version": VERSION, "writer": ns.writer, "round": ns.round, "phase": ns.phase,
                               "items": len(only) if only is not None else len(rows), "samples": list(samples), "fams": list(fams),
                               "started_at": jc._now_iso(), "resume": bool(ns.resume), "stop_usd": stop, "limits_file": lim["file"],
                               "headroom_usd": lim["headroom_usd"], "packets_sha256": lg.packets_sha256(packets),
                               "script_sha256": lg.file_sha256(Path(__file__))}
    res = asyncio.run(run_round(rows, packets, readers, scorer, rub, fams, samples, guard, d / "run-batches.jsonl", only_ids=only))
    summary["run"] = res["run"]
    summary["finished_at"] = jc._now_iso()
    summary["dollars"] = {**{f: round(c.total_spent(), 4) for f, c in readers.items()}, "scorer": round(scorer.total_spent(), 4),
                          "total": round(guard.total(), 4)}
    summary["kimi_served"] = {k: v for k, v in e12.served_summary(list(lg.read_jsonl(readers["kimi"].cache_path))).items() if k != "per_record"}
    summary["outcomes"] = {f: dict(Counter(r.get("outcome") for r in lg.latest(lg.read_jsonl(c.cache_path)).values()))
                           for f, c in {**readers, "scorer": scorer}.items()}
    summary["stopped"] = guard.total() >= stop or any(v["aborted"] for v in res["run"]["read"].values()) or \
        bool(res["run"]["score"].get("aborted"))
    (d / "collected.json").write_text(json.dumps(res["collected"], indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (d / "run-summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    lg.emit(e12.printable(summary))
    return 0


def cmd_collect(ns: Any) -> int:
    """Rebuild a phase's collected.json offline from its caches ($0): the per-item statistics with per-condition scores."""
    import json
    import stage3_elicitation_convert as cv
    conv = Path(ns.converted_dir)
    d = phase_dir(Path(ns.out_root), ns.writer, ns.round, ns.phase)
    items, _ = cv.build_reader_items(conv, e12.day0_texts())
    only = set(json.loads(Path(ns.only_ids).read_text(encoding="utf-8"))) if ns.only_ids else None
    got = collect_dir(d, items["items"], reader_names(ns.writer), PHASES[ns.phase]["samples"], only)
    (d / "collected.json").write_text(json.dumps(got, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"items": len(got), "phase": ns.phase, "writer": ns.writer}))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="brief 30 Part 3: development and certification reads")
    sub = ap.add_subparsers(dest="cmd", required=True)
    k = sub.add_parser("collect")
    k.add_argument("--writer", required=True, choices=sorted(cl.SECOND))
    k.add_argument("--round", type=int, required=True)
    k.add_argument("--phase", required=True, choices=sorted(PHASES))
    k.add_argument("--converted-dir", required=True)
    k.add_argument("--out-root", default=str(READS_ROOT))
    k.add_argument("--only-ids", default=None)
    r = sub.add_parser("run")
    r.add_argument("--writer", required=True, choices=sorted(cl.SECOND))
    r.add_argument("--round", type=int, required=True)
    r.add_argument("--phase", required=True, choices=sorted(PHASES))
    r.add_argument("--converted-dir", required=True)
    r.add_argument("--out-root", default=str(READS_ROOT))
    r.add_argument("--cap-usd", type=float, required=True)
    r.add_argument("--only-ids", default=None)
    r.add_argument("--resume", action="store_true")
    ns = ap.parse_args(argv)
    return {"run": cmd_run, "collect": cmd_collect}[ns.cmd](ns)


if __name__ == "__main__":
    raise SystemExit(main())
