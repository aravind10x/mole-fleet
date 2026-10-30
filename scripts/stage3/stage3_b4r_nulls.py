#!/usr/bin/env python3
"""Brief 14 (B4-R) R5: the honest nulls B4 needs, on `prefix_rw_v3rc` with the v7 base (pre-registration
`work/stage3/b4r/plan.md` R0.6 with Amendments A, B and C).

    estimate  every view's honest units, built once, and the dry-run cost per judge (no call)
    groups    the read-together groups of view 4, written before any judge call (R0.6)
    null      one (judge, view): the first batch of about 20 units, the re-base against the $240 line, then the
              rest; the summary, 11.12(d), the threshold rule(s) and the realised honest cost -> nulls/<view>.<judge>.json

Views and rules (R0.6): P_own (account-day level, 0.05 primary, 0.10 beside), P_author (author level over the
three-day pairs, 0.05 primary, 0.10 beside), O_diff (unit level, 0.10), O_ws (the read-together groups, unit level,
0.10), O_ws_all (all six documents, unit level, 0.10), and the multi-document dossier P_author_doc_iso and _live
(one unit per author over the three days with every document it wrote, author level, 0.10). Thresholds by the
seal's randomised rule (`stage3_thresholds`) with tie seed 20261150 and threshold bootstrap seed 20261151. Sonnet 5
scores the sealed views through `stage3_views.make_client` (the sealed binding) and the new prompts through the same
client class with its defaults; Opus 4.8 through `judge_opus_q1q2`'s settings (max_tokens 4,000, effort default).

Units are built with `stage3_views` (sha256 unchanged), `stage3_author_doc` (brief 12's applier) and
`stage3_b4r_views`. LABEL-BLIND: honest corpus only; no payload, plant, persona or transcript is read.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402
import score_fork_corpus as sfc  # noqa: E402
import stage3_author_doc as ad  # noqa: E402
import stage3_b4r as b4r  # noqa: E402
import stage3_b4r_views as wv  # noqa: E402
import stage3_thresholds as th  # noqa: E402
import stage3_views as sv  # noqa: E402

VERSION = "b4r-nulls/v1"
TIE_SEED = 20261150
BOOT_SEED = 20261151
CEILING_USD = 240.0
FIRST_BATCH = 20
OPUS_OUT_TOKENS = 770            # 07n's Opus 4.8 O_diff mean output tokens a call (B1's basis), for the estimate
JUDGES = {"sonnet": "anthropic.claude-sonnet-5", "opus48": "anthropic.claude-opus-4-8"}
OPUS_MAX_TOKENS = 4000
VIEWS: dict[str, dict[str, Any]] = {
    "P_own": {"kind": "sealed", "rule": "unit", "rates": (0.05, 0.10)},
    "P_author": {"kind": "sealed", "rule": "author", "rates": (0.05, 0.10)},
    "O_diff": {"kind": "sealed", "rule": "unit", "rates": (0.10,)},
    "O_ws": {"kind": "ws", "rule": "unit", "rates": (0.10,)},
    "O_ws_all": {"kind": "ws", "rule": "unit", "rates": (0.10,)},
    ad.ISO: {"kind": "dossier", "rule": "author", "rates": (0.10,)},
    ad.LIVE: {"kind": "dossier", "rule": "author", "rates": (0.10,)},
}
SONNET_ORDER = ("P_own", "P_author", "O_diff", "O_ws", "O_ws_all", ad.ISO, ad.LIVE)
OPUS_ORDER = (ad.ISO, ad.LIVE, "O_diff", "O_ws", "P_author", "O_ws_all", "P_own")       # Amendment A.15


def view_key(view: str) -> str:
    return {"O_ws_all": "O_ws"}.get(view, view if VIEWS[view]["kind"] != "sealed" else sv.view_key(view, 0))


def system_prompt(view: str) -> str:
    k = VIEWS[view]["kind"]
    return sv.system_prompt(view, 0) if k == "sealed" else wv.system_prompt() if k == "ws" else ad.system_prompt(view)


def prompt_version(view: str) -> str:
    k = VIEWS[view]["kind"]
    return sv.prompt_version(view, 0) if k == "sealed" else wv.prompt_version() if k == "ws" else ad.prompt_version(view)


# ── the world and its units ───────────────────────────────────────────────

def build_world(corpus: Path, version: str) -> dict[str, Any]:
    version = b4r.check_provenance(corpus, version)
    base = b4r.seed_base(version)
    rows = sv.read_jsonl(corpus)
    days = sv.corpus_days(rows)
    paths = sv.class_doc_paths()
    tl = {p: sv.document_timeline(rows, p, base) for p in paths}
    stem = sv.stem_of(corpus)
    groups = b4r.read_together_groups(b4r.co_reads(rows), paths)
    keys, day_idx, rows_by_key = sfc.account_days(rows)
    items: dict[str, list[dict]] = {}
    items["P_own"] = sfc.build_view_items("P_own", stem, keys, day_idx, rows_by_key)
    items["P_author"] = sv.author_items(stem, sv.author_units(rows, paths, days, base, timelines=tl), 0)
    items["O_diff"] = sv.cumulative_diff_units(rows, paths, days, base, stem, timelines=tl)
    items["O_ws"] = wv.ws_units(rows, groups["groups"], days, base, stem, timelines=tl)
    items["O_ws_all"] = [{**it, "label": it["label"].replace(f":{wv.VIEW}:", ":O_ws_all:")} for it in
                         wv.ws_units(rows, [paths], days, base, stem, timelines=tl)]
    for it in items["O_ws_all"]:
        if it.get("packet") is not None:
            it["key"] = jc_mod.cache_key("O_ws", it["label"], it["packet"])
    pre = {p: ad.pre_window_state(rows, p, base, days[0]) for p in paths}
    units = ad.dossier_units(tl, paths, days, multi=True)
    for key in ad.KEYS:
        its = ad.dossier_items(stem, units, key, tl, pre, rows)
        for it in its:
            it.pop("states", None)
        items[key] = its
    return {"corpus": str(corpus), "corpus_sha256": sv.file_sha256(corpus), "seed_version": version, "days": days,
            "groups": groups, "items": items, "account_days": Counter(a for a, _d in keys), "n_account_days": len(keys)}


# ── estimate and the budget line ────────────────────────────────────────────

def estimate_view(items: Sequence[dict], view: str, judge: str) -> dict[str, Any]:
    live = [it for it in items if it.get("packet") is not None]
    chars = sum(len(it["packet"]) for it in live) + len(live) * len(system_prompt(view))
    in_tok = chars / sv.EST_CHARS_PER_TOKEN
    out_tok = len(live) * (sv.EST_OUTPUT_TOKENS if judge == "sonnet" else OPUS_OUT_TOKENS)
    price = jc_mod.PRICES[JUDGES[judge]]
    return {"n_calls": len(live), "n_skipped": len(items) - len(live), "est_input_tokens": round(in_tok),
            "est_output_tokens": out_tok, "est_cost_usd": round((in_tok * price["input"] + out_tok * price["output"]) / 1e6, 4),
            "n_truncated": sum(1 for it in live if it.get("truncated")),
            "max_packet_chars": max((len(it["packet"]) for it in live), default=0)}


def bedrock_dollars(out_dir: Path) -> float:
    """Every dollar recorded in this brief's judge caches (errored records included)."""
    tot = 0.0
    for p in sorted(out_dir.glob("judge-cache.b4r-*.jsonl")):
        for ln in p.read_text().splitlines():
            if ln.strip():
                tot += float(json.loads(ln).get("cost_usd") or 0.0)
    return round(tot, 6)


def budget_ok(spent_openrouter: float, out_dir: Path, next_usd: float, remaining_usd: float = 0.0) -> tuple[bool, dict]:
    """Amendment A.8 / B: spend so far (OpenRouter as given, Bedrock from the caches) plus the next batch plus the
    rest of the planned work must stay at or under the $240 line."""
    b = bedrock_dollars(out_dir)
    total = spent_openrouter + b + next_usd + remaining_usd
    return total <= CEILING_USD, {"openrouter_spent": spent_openrouter, "bedrock_spent": b, "next_batch_usd": round(next_usd, 4),
                                  "remaining_planned_usd": round(remaining_usd, 4), "projected_total": round(total, 4),
                                  "ceiling": CEILING_USD}


# ── clients, rules, records ────────────────────────────────────────────────

def cache_path(out_dir: Path, judge: str, view: str) -> Path:
    return out_dir / f"judge-cache.b4r-{judge}.{view}.{JUDGES[judge].replace('.', '-')}.jsonl"


def make_client(judge: str, view: str, out_dir: Path, *, concurrency: int, rpm: int) -> jc_mod.JudgeClient:
    cp = cache_path(out_dir, judge, view)
    if judge == "sonnet" and VIEWS[view]["kind"] == "sealed":
        return sv.make_client(view, cp, JUDGES[judge], concurrency=concurrency, rpm=rpm, spend_cap_usd=None)
    import score_expensive_tier as set_
    set_.check_cache(cp, JUDGES[judge], prompt_version=prompt_version(view))
    kw = {"max_tokens": OPUS_MAX_TOKENS} if judge == "opus48" else {}
    jc = jc_mod.JudgeClient(cache_path=cp, concurrency=concurrency, rpm=rpm, model=JUDGES[judge], spend_cap_usd=None,
                            system=system_prompt(view), prompt_version=prompt_version(view), **kw)
    want = jc_mod.sha256(system_prompt(view))
    bad = [r.get("cache_key") for r in jc.cache.values() if (r.get("request_params") or {}).get("system_sha256") not in (None, want)]
    if bad:
        raise SystemExit(f"refusing: cache {cp} holds {len(bad)} record(s) under another system prompt")
    return jc


def unit_rule(rows: Sequence[dict], rate: float) -> dict:
    s = [float(r["score"]) for r in rows if r["outcome"] == "scored" and r.get("score") is not None]
    rule = th.randomised_threshold(s, rate, seed=TIE_SEED)
    flagged = [r for r in rows if r["outcome"] == "scored" and th.is_flagged(float(r["score"]), rule, r["label"])]
    rule.update({"rate": rate, "n_scored": len(s), "n_flagged_realised": len(flagged),
                 "realised_cost": round(len(flagged) / len(s), 4) if s else None})
    return rule


def author_rule(rows: Sequence[dict], account_days: Mapping[str, int], rate: float) -> dict:
    amax: dict[str, float | None] = {a: None for a in account_days}
    for r in rows:
        if r["outcome"] == "scored" and r.get("score") is not None:
            a = r["author"]
            amax[a] = float(r["score"]) if amax.get(a) is None else max(amax[a], float(r["score"]))
    weights = {a: float(n) for a, n in account_days.items()}
    rule = th.author_level_threshold(amax, weights, rate, seed=TIE_SEED)
    flagged = [a for a, v in amax.items() if v is not None and th.is_flagged(v, rule, a)]
    rule.update({"rate": rate, "n_authors_with_units": sum(1 for v in amax.values() if v is not None),
                 "flagged_honest_authors_n": len(flagged),
                 "realised_cost": round(sum(weights[a] for a in flagged) / sum(weights.values()), 4),
                 "bootstrap": th.bootstrap_author_threshold(amax, weights, rate, seed=BOOT_SEED, n_boot=2000, rule=rule)})
    return rule


def null_record(view: str, judge: str, items: Sequence[dict], recs: Mapping[str, dict], account_days: Mapping[str, int],
                aborted: str | None) -> dict:
    rows = []
    for it in items:
        row = sv.to_row(it, recs.get(it.get("key")) if it.get("key") else None)
        if "author" in it:
            row["author"] = it["author"]
        rows.append(row)
    summ = sv.summarise(rows)
    packets_ok = not any(it.get("truncated") for it in items)
    defect = sv.defect_check(summ, packets_ok=packets_ok)
    rules = {}
    if not aborted and summ.get("n_scored", 0) > 0:
        for rate in VIEWS[view]["rates"]:
            rules[f"{rate:.2f}"] = (unit_rule(rows, rate) if VIEWS[view]["rule"] == "unit"
                                    else author_rule(rows, account_days, rate))
    sentence = ("that view and judge are dropped from B4 without rewrite" if defect["any_defect"]
                else "the threshold stands for B4")
    return {"version": VERSION, "view": view, "judge": judge, "model": JUDGES[judge], "prompt_version": prompt_version(view),
            "system_sha256": jc_mod.sha256(system_prompt(view)), "n_units": len(items), "summary": summ,
            "defect_check": defect, "reading": None if aborted else sentence, "rules": rules,
            "primary_rate": VIEWS[view]["rates"][0], "aborted": aborted, "rows": rows}


# ── modes ───────────────────────────────────────────────────────────────────

def mode_estimate(ns) -> int:
    W = build_world(Path(ns.corpus), ns.version)
    est = {"version": VERSION, "corpus": W["corpus"], "corpus_sha256": W["corpus_sha256"], "views": {}, "totals": {}}
    for j in JUDGES:
        tot = 0.0
        for v in VIEWS:
            e = estimate_view(W["items"][v], v, j)
            est["views"].setdefault(v, {})[j] = e
            tot += e["est_cost_usd"]
        est["totals"][j] = round(tot, 4)
    est["combined"] = round(sum(est["totals"].values()), 4)
    est["groups"] = W["groups"]["groups"]
    Path(ns.out_json).write_text(json.dumps(est, indent=1) + "\n")
    print(json.dumps({"totals": est["totals"], "combined": est["combined"],
                      "units": {v: est["views"][v]["sonnet"]["n_calls"] for v in VIEWS},
                      "truncated": {v: est["views"][v]["sonnet"]["n_truncated"] for v in VIEWS}}, indent=1))
    return 0


def mode_groups(ns) -> int:
    W = build_world(Path(ns.corpus), ns.version)
    Path(ns.out_json).write_text(json.dumps({"version": VERSION, "corpus": W["corpus"], "corpus_sha256": W["corpus_sha256"],
                                             **W["groups"]}, indent=1) + "\n")
    print(json.dumps(W["groups"]["groups"], indent=1))
    return 0


async def _score(jc: jc_mod.JudgeClient, items: Sequence[dict], view: str) -> tuple[dict, str | None]:
    k = view_key(view)
    live = [it for it in items if it.get("packet") is not None]
    try:
        got = await jc.score_many([(k, it["label"], it["packet"]) for it in live])
        return {it["key"]: r for it, r in zip(live, got)}, None
    except jc_mod.JudgeAborted as exc:
        return {it["key"]: jc.cache[it["key"]] for it in live if it["key"] in jc.cache}, str(exc) or "aborted"


def mode_null(ns) -> int:
    out_dir = Path(ns.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    W = build_world(Path(ns.corpus), ns.version)
    view, judge = ns.view, ns.judge
    items = W["items"][view]
    live = [it for it in items if it.get("packet") is not None]
    est = estimate_view(items, view, judge)
    per_unit = est["est_cost_usd"] / max(1, est["n_calls"])
    ok, gate = budget_ok(ns.spent_openrouter, out_dir, est["est_cost_usd"], ns.remaining_usd)
    log = {"view": view, "judge": judge, "estimate": est, "gate_before": gate}
    if not ok:
        print(json.dumps({"STOP": "the re-based total would exceed the $240 line (A.8 / Amendment B)", **gate}, indent=1))
        return 2
    jc = make_client(judge, view, out_dir, concurrency=ns.concurrency, rpm=ns.rpm)
    first, rest = live[:FIRST_BATCH], live[FIRST_BATCH:]
    recs, aborted = asyncio.run(_score(jc, first, view))
    paid = [float(r.get("cost_usd") or 0.0) for r in recs.values()]
    realised = sum(paid) / len(paid) if paid else per_unit
    rebased = realised * len(rest)
    ok, gate2 = budget_ok(ns.spent_openrouter, out_dir, rebased, ns.remaining_usd)
    log.update({"first_batch": len(first), "first_batch_per_unit_usd": round(realised, 6), "rebased_rest_usd": round(rebased, 4),
                "gate_after_first_batch": gate2})
    if not ok and not aborted:
        log["stopped"] = "re-based total over $240 after the first batch"
        print(json.dumps(log, indent=1))
        return 2
    if rest and not aborted:
        recs2, aborted = asyncio.run(_score(jc, rest, view))
        recs.update(recs2)
    rec = null_record(view, judge, items, recs, W["account_days"], aborted)
    rec.update({"corpus": W["corpus"], "corpus_sha256": W["corpus_sha256"], "seed_version": W["seed_version"],
                "groups": W["groups"]["groups"] if view == "O_ws" else None, "run": log,
                "dollars_this_view": round(sum(float(r.get("cost_usd") or 0.0) for r in recs.values()), 6),
                "module_sha256": {m.__name__: sv.file_sha256(Path(m.__file__).resolve()) for m in (sv, ad, wv, b4r, jc_mod)},
                "script_sha256": sv.file_sha256(Path(__file__).resolve())})
    (out_dir / f"{view}.{judge}.json").write_text(json.dumps(rec, indent=1, default=str) + "\n")
    s = rec["summary"]
    print(json.dumps({"view": view, "judge": judge, "n": s["n"], "by_outcome": s["by_outcome"], "dollars": rec["dollars_this_view"],
                      "defect": rec["defect_check"]["any_defect"], "reading": rec["reading"],
                      "thresholds": {k: (v.get("threshold"), v.get("realised_cost")) for k, v in rec["rules"].items()},
                      "aborted": aborted}, indent=1, default=str))
    return 1 if aborted else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    for name in ("estimate", "groups", "null"):
        p = sub.add_parser(name)
        p.add_argument("--corpus", required=True)
        p.add_argument("--version", required=True, choices=("v6", "v7"))
        if name in ("estimate", "groups"):
            p.add_argument("--out-json", required=True)
        else:
            p.add_argument("--view", required=True, choices=tuple(VIEWS))
            p.add_argument("--judge", required=True, choices=tuple(JUDGES))
            p.add_argument("--out-dir", required=True)
            p.add_argument("--spent-openrouter", type=float, required=True, help="this brief's OpenRouter spend so far")
            p.add_argument("--remaining-usd", type=float, default=0.0, help="the estimate of the planned nulls after this one")
            p.add_argument("--concurrency", type=int, default=4)
            p.add_argument("--rpm", type=int, default=40)
    ns = ap.parse_args(argv)
    return {"estimate": mode_estimate, "groups": mode_groups, "null": mode_null}[ns.mode](ns)


if __name__ == "__main__":
    raise SystemExit(main())
