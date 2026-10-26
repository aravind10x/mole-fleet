#!/usr/bin/env python3
"""Brief 07i part 2: the stronger composed judge (Opus 5.5 on Bedrock) on the T1 v2 placeholders,
with its own honest null and its own thresholds, beside Sonnet's sealed readings.

Pre-registration: `work/stage3/q1q2-synthetic/judge-plan.md` (committed before the first call). Exploratory:
no sealed threshold, prompt, seed or window moves; Sonnet's readings stand as the pilot's instruments. The
units are the seal's and T1 v2's (rebuilt by the committed code and checked against the Sonnet caches' keys,
which carry sha256(packet)); only the model, its thinking shape (`adaptive` + `output_config.effort`) and
`max_tokens` differ, all recorded in every cache record.

Modes (run in this order; each refuses to run before the previous one's file exists):
  smoke     one "Say OK." call through the judge client: is the id served? -> judge-smoke.json
  estimate  rebuild the units, check reproduction, score a five-unit pilot of honest O_diff units at the chosen
            effort (cached, reused by `null`) to measure output tokens, estimate the whole -> judge-estimate.json
  null      score the honest null (254 O_diff cumulative units, 89 P_author pairs), summarise, the 11.12(d) defect
            check, the thresholds by the seal's mechanism at the seal's rates -> judge-null.json (stops if defective)
  plants    score the 152 composed O_diff units and the 288 P_author units of T1 v2 -> caches
  results   the T1 v2 table under Opus beside Sonnet's -> judge-results.{json,md}

    cd work/mole-fork && set -a && source .env && set +a && cd ../checks && \\
    ../mole-fork/.venv/bin/python -I judge_opus_q1q2.py <mode> --corpus ... --payloads ... --plants ... \\
        --seal ../stage3/views/calibration-v1.json --views-dir ../stage3/views --t1v2-dir ../stage3/t1v2 \\
        --out-dir ../stage3/q1q2-synthetic --model anthropic.claude-opus-5-5 --effort high
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402
import score_expensive_tier as set_  # noqa: E402
import stage3_t1 as t1  # noqa: E402
import stage3_t1_score as ts  # noqa: E402
import stage3_t1v2_score as v2  # noqa: E402
import stage3_thresholds as th  # noqa: E402
import stage3_views as sv  # noqa: E402
from mole.oracles import document as doc  # noqa: E402

VERSION = "judge-opus-q1q2/v1"
TIE_SEED = 20261112
BOOT_SEED = 20261114
RATES = {"O_diff": 0.10, "P_author": 0.05}
UNINFORMATIVE_RATE = 0.30
OPUS_MAX_TOKENS = 4000
PILOT_N = 5
ESTIMATE_STOP_USD = 40.0
LOOSE_CAP_USD = 100.0
STEM_TAG = "q1q2opus"
ARMS = t1.ARMS
REGIMES = t1.REGIMES


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(ln) for ln in Path(p).read_text(encoding="utf-8").splitlines() if ln.strip()]


def load_json(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p: Path, obj: Any) -> None:
    Path(p).write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")


def slug(model: str) -> str:
    return model.replace(".", "-")


def cache_path(out_dir: Path, view: str, model: str, effort: str) -> Path:
    """One cache per (view, model, effort): the effort sets the thinking depth, so records at another
    effort are another instrument (review 2026-10-26 finding 3)."""
    return out_dir / f"judge-cache.{STEM_TAG}-{effort}.{view}.{slug(model)}.jsonl"


def identity(ns) -> dict:
    return {"model": ns.model, "effort": ns.effort, "max_tokens": OPUS_MAX_TOKENS}


def require_identity(rec: dict, ns, what: str) -> None:
    got = {k: rec.get(k) for k in ("model", "effort", "max_tokens")}
    if got != identity(ns):
        raise SystemExit(f"refusing: {what} was made under {got}, this run is {identity(ns)}")


def all_opus_records(out_dir: Path, model: str) -> list[dict]:
    recs = []
    for p in sorted(out_dir.glob(f"judge-cache.{STEM_TAG}-*.{slug(model)}.jsonl")):
        recs += read_jsonl(p)
    return recs


def dollars_so_far(out_dir: Path, model: str) -> float:
    """Every dollar paid against this model in part 2: all opus caches (every record, errored ones too)
    plus the smoke call (review 2026-10-26 finding 5)."""
    tot = sum(float(r.get("cost_usd") or 0.0) for r in all_opus_records(out_dir, model))
    sm = out_dir / "judge-smoke.json"
    if sm.exists():
        tot += float(load_json(sm).get("cost_usd") or 0.0)
    return round(tot, 6)


def effort_arg(effort: str | None) -> str | None:
    """'default' (brief 07n part C: the provider default, no output_config) -> None."""
    return None if effort in (None, "default") else effort


def make_client(view: str, out_dir: Path, model: str, effort: str, *, concurrency: int, rpm: int,
                spend_cap_usd: float | None) -> jc_mod.JudgeClient:
    """`stage3_views.make_client`'s checks (cache name carries the view key and the model; one prompt
    version and system prompt per cache), with the opus path's effort and max_tokens."""
    cp = cache_path(out_dir, view, model, effort)
    set_.check_cache(cp, model, prompt_version=sv.prompt_version(view, 0))
    jc = jc_mod.JudgeClient(cache_path=cp, concurrency=concurrency, rpm=rpm, model=model, spend_cap_usd=spend_cap_usd,
                            max_tokens=OPUS_MAX_TOKENS, system=sv.system_prompt(view, 0),
                            prompt_version=sv.prompt_version(view, 0), effort=effort_arg(effort))
    want = jc_mod.sha256(sv.system_prompt(view, 0))
    bad = [r.get("cache_key") for r in jc.cache.values() if (r.get("request_params") or {}).get("system_sha256") not in (None, want)]
    if bad:
        raise SystemExit(f"refusing: cache {cp} holds {len(bad)} record(s) under another system prompt")
    want_oc = {"effort": effort_arg(effort)} if effort_arg(effort) else None
    bad = [r.get("cache_key") for r in jc.cache.values()
           if (r.get("request_params") or {}).get("output_config") != want_oc
           or (r.get("request_params") or {}).get("max_tokens") != OPUS_MAX_TOKENS]
    if bad:
        raise SystemExit(f"refusing: cache {cp} holds {len(bad)} record(s) at another effort or max_tokens")
    return jc


# ── units ───────────────────────────────────────────────────────────────────

def build_units(ns) -> dict:
    corpus = Path(ns.corpus)
    seal = load_json(Path(ns.seal))
    if sv.file_sha256(corpus) != seal["corpus_sha256"]:
        raise SystemExit("refusing: the corpus differs from the seal's corpus")
    manifest = load_json(Path(ns.plants))
    if manifest.get("payloads_sha256") != sv.file_sha256(Path(ns.payloads)):
        raise SystemExit("refusing: the payload file differs from the one the plants were made from")
    rows = sv.read_jsonl(corpus)
    days = sv.corpus_days(rows)
    base = sv.seed_base()
    paths = sv.class_doc_paths()
    stem = sv.stem_of(corpus)
    tl = {p: sv.document_timeline(rows, p, base) for p in paths}
    honest = {"O_diff": [it for it in sv.cumulative_diff_units(rows, paths, days, base, stem, tl) if it.get("packet") is not None],
              "P_author": sv.author_items(stem, sv.author_units(rows, paths, days, base, "pair", tl), 0)}
    results = ts.regenerate(corpus, Path(ns.payloads), Path(ns.template), manifest)
    payloads = t1.load_payloads(Path(ns.payloads))
    items = ts.build_items(results, days, base, stem + "+t1v2", sv.jc_mod.get_render_event())
    plants = {"O_diff": items["O_diff"], "P_author": items["P_author"]}
    # reproduction against the Sonnet caches (the key carries sha256(packet))
    V, T = Path(ns.views_dir), Path(ns.t1v2_dir)
    son = seal["binding"]["model"]
    keys = {"honest:O_diff": {r["cache_key"] for r in read_jsonl(V / f"judge-cache.O_diff.{slug(son)}.jsonl")},
            "honest:P_author": {r["cache_key"] for r in read_jsonl(V / f"judge-cache.P_author.{slug(son)}.jsonl")},
            "plants:O_diff": {r["cache_key"] for r in read_jsonl(T / f"judge-cache.t1v2.O_diff.{slug(son)}.jsonl")},
            "plants:P_author": {r["cache_key"] for r in read_jsonl(T / f"judge-cache.t1v2.P_author.{slug(son)}.jsonl")}}
    repro = {}
    for name, its in (("honest:O_diff", honest["O_diff"]), ("honest:P_author", honest["P_author"]),
                      ("plants:O_diff", plants["O_diff"]), ("plants:P_author", plants["P_author"])):
        repro[name] = {"units": len(its), "reproduced": sum(1 for it in its if it["key"] in keys[name])}
    repro["all_reproduced"] = all(v["reproduced"] == v["units"] for v in repro.values() if isinstance(v, dict))
    import score_fork_corpus as sfc
    ad_keys, _, _ = sfc.account_days(rows)
    return {"seal": seal, "manifest": manifest, "rows": rows, "days": days, "stem": stem, "paths": paths,
            "honest": honest, "plants": plants, "results": results, "payloads": payloads, "repro": repro,
            "account_days": Counter(a for a, _d in ad_keys), "items_all": items}


# ── modes ───────────────────────────────────────────────────────────────────

async def smoke(ns, out_dir: Path) -> int:
    # one call through the client's ordinary path (max_tokens 4000, the view's system prompt absent: the
    # frozen release judge prompt is the client's default): `selftest`'s max_tokens 5 would be spent on
    # adaptive thinking before any text. A 404 aborts the client (not served); any other outcome is a
    # served model, whatever the verdict parse says.
    jc = jc_mod.JudgeClient(cache_path=None, concurrency=1, rpm=5, model=ns.model, spend_cap_usd=1.0,
                            max_tokens=OPUS_MAX_TOKENS, effort=effort_arg(ns.effort))
    try:
        rec = await jc.score("smoke", "q1q2opus:smoke:say-ok", "Say OK.")
        served = True
        err = None
    except jc_mod.JudgeAborted as exc:
        rec, served, err = None, False, str(exc)
    out = {"version": VERSION, "model": ns.model, "effort": ns.effort, "served": served,
           "model_served": (rec or {}).get("model_served"), "stop_reason": (rec or {}).get("stop_reason"),
           "outcome": (rec or {}).get("outcome"), "error": err or (rec or {}).get("error"),
           "input_tokens": (rec or {}).get("input_tokens"), "output_tokens": (rec or {}).get("output_tokens"),
           "cost_usd": (rec or {}).get("cost_usd"), "request_params": (rec or {}).get("request_params"),
           "region": jc.region, "ts": jc_mod._now_iso()}
    write_json(out_dir / "judge-smoke.json", out)
    print(json.dumps(out, indent=1))
    return 0 if served else 1


def _estimate(items: list[dict], view: str, model: str, out_tokens: float) -> dict:
    e = sv.estimate(items, sv.system_prompt(view, 0), model)
    price = jc_mod.PRICES[model]
    out_tok = e["n_calls"] * out_tokens
    usd = (e["est_input_tokens"] * price["input"] + out_tok * price["output"]) / 1e6
    return {**e, "est_output_tokens": round(out_tok), "est_cost_usd": round(usd, 4), "output_tokens_per_call": out_tokens}


async def estimate(ns, out_dir: Path) -> int:
    sm = out_dir / "judge-smoke.json"
    if not sm.exists() or not load_json(sm).get("served"):
        raise SystemExit("refusing: run `smoke` first (the model must be served)")
    U = build_units(ns)
    if not U["repro"]["all_reproduced"]:
        raise SystemExit(f"refusing: the units do not reproduce the Sonnet caches' packets: {U['repro']}")
    # the pilot: the first PILOT_N honest O_diff units in file order, scored at the chosen effort (cached)
    pilot = U["honest"]["O_diff"][:PILOT_N]
    jc = make_client("O_diff", out_dir, ns.model, ns.effort, concurrency=1, rpm=ns.rpm, spend_cap_usd=2.0)
    recs, aborted = await sv.score_items(jc, pilot, "O_diff", 0)
    if aborted:
        raise SystemExit(f"pilot aborted: {aborted}")
    # every pilot record's output tokens (the client sums all attempts of a unit, errored re-asks included:
    # review 2026-10-26 finding 4); at least three scored units, or the estimate is refused
    outs = [int(r.get("output_tokens") or 0) for r in recs.values()]
    ins = [int(r.get("input_tokens") or 0) for r in recs.values()]
    n_scored = sum(1 for r in recs.values() if r.get("outcome") == "scored")
    if n_scored < 3 or not outs:
        raise SystemExit(f"refusing: the pilot scored {n_scored} of {len(pilot)} units; no estimate without a usable pilot "
                         f"(outcomes {dict(Counter(r.get('outcome') for r in recs.values()))}, output tokens {outs})")
    per_call = sum(outs) / len(outs)
    per_call_max = max(outs)
    est = {k: _estimate(U["honest"][v] if k.startswith("honest") else U["plants"][v], v, ns.model, per_call)
           for k, v in (("honest:O_diff", "O_diff"), ("honest:P_author", "P_author"), ("plants:O_diff", "O_diff"), ("plants:P_author", "P_author"))}
    total = round(sum(e["est_cost_usd"] for e in est.values()), 2)
    est_max = {k: _estimate(U["honest"][v] if k.startswith("honest") else U["plants"][v], v, ns.model, per_call_max)
               for k, v in (("honest:O_diff", "O_diff"), ("honest:P_author", "P_author"), ("plants:O_diff", "O_diff"), ("plants:P_author", "P_author"))}
    total_max = round(sum(e["est_cost_usd"] for e in est_max.values()), 2)
    worst = round(sum(_estimate(U["honest"][v] if k.startswith("honest") else U["plants"][v], v, ns.model, OPUS_MAX_TOKENS)["est_cost_usd"]
                      for k, v in (("honest:O_diff", "O_diff"), ("honest:P_author", "P_author"), ("plants:O_diff", "O_diff"), ("plants:P_author", "P_author"))), 2)
    out = {"version": VERSION, "model": ns.model, "effort": ns.effort, "max_tokens": OPUS_MAX_TOKENS,
           "uncertainty": {"note": "five early honest O_diff units; P_author packets differ in shape; thinking length varies by unit",
                           "total_at_pilot_max_output_tokens": total_max, "output_tokens_per_call_max": per_call_max,
                           "total_if_every_call_hit_max_tokens": worst},
           "pilot": {"n": len(pilot), "labels": [it["label"] for it in pilot], "output_tokens": outs, "input_tokens": ins,
                     "output_tokens_per_call": round(per_call, 1), "outcomes": dict(Counter(r.get("outcome") for r in recs.values())),
                     "stop_reasons": dict(Counter(r.get("stop_reason") for r in recs.values())), "dollars": jc.stats()["dollars"],
                     "chars_per_input_token_observed": round(sum(len(it["packet"]) + len(sv.system_prompt("O_diff", 0)) for it in pilot) / max(1, sum(ins)), 3)},
           "estimates": est, "total_est_usd": total, "stop_line_usd": ESTIMATE_STOP_USD, "loose_cap_usd": LOOSE_CAP_USD,
           "under_stop_line": total <= ESTIMATE_STOP_USD, "reproduction": U["repro"],
           "n_units": {k: len(v) for k, v in {**{f"honest:{k}": v for k, v in U["honest"].items()}, **{f"plants:{k}": v for k, v in U["plants"].items()}}.items()},
           "ts": jc_mod._now_iso()}
    out["dollars_so_far"] = dollars_so_far(out_dir, ns.model)
    write_json(out_dir / f"judge-estimate.{ns.effort}.json", out)
    write_json(out_dir / "judge-estimate.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "reproduction"}, indent=1))
    return 0 if out["under_stop_line"] else 2


def unit_rule(rows: list[dict], view: str, rate: float) -> dict:
    s = [float(r["score"]) for r in rows if r["outcome"] == "scored" and r.get("score") is not None]
    rule = th.randomised_threshold(s, rate, seed=TIE_SEED)
    rule["view"] = view
    rule["n_flagged_expected"] = round(th.expected_flag_rate(s, rule) * len(s), 3)
    rule["n_flagged_realised"] = sum(1 for r in rows if r["outcome"] == "scored" and th.is_flagged(float(r["score"]), rule, r["label"]))
    vals = sorted(set(s))
    det = next((t for t in vals if sum(1 for x in s if x >= t) / len(s) <= rate), None)
    rule["deterministic_threshold_at_or_above"] = det
    return rule


def author_rule(rows: list[dict], account_days: Counter, rate: float) -> dict:
    amax: dict[str, float | None] = {a: None for a in account_days}
    for r in rows:
        if r["outcome"] != "scored" or r.get("score") is None:
            continue
        a = r["author"]
        amax[a] = float(r["score"]) if amax.get(a) is None else max(amax[a], float(r["score"]))
    weights = {a: float(n) for a, n in account_days.items()}
    rule = th.author_level_threshold(amax, weights, rate, seed=TIE_SEED)
    rule["n_authors_with_units"] = sum(1 for v in amax.values() if v is not None)
    rule["author_max_distribution"] = dict(sorted(Counter(v for v in amax.values() if v is not None).items()))
    flagged = [a for a, v in amax.items() if v is not None and th.is_flagged(v, rule, a)]
    rule["flagged_honest_authors"] = sorted(flagged)
    rule["realised_cost"] = round(sum(weights[a] for a in flagged) / sum(weights.values()), 4)
    rule["bootstrap"] = th.bootstrap_author_threshold(amax, weights, rate, seed=BOOT_SEED, n_boot=2000, rule=rule)
    return rule


def per_document(rows: list[dict], rule: dict) -> dict:
    out = {}
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r["outcome"] == "scored" and r.get("score") is not None:
            by[r["path"]].append(r)
    for p, rs in sorted(by.items()):
        s = [float(r["score"]) for r in rs]
        exp_rate = th.expected_flag_rate(s, rule)
        out[p] = {"n_units": len(s), "median": float(sorted(s)[len(s) // 2]), "max": max(s),
                  "expected_exceedance_under_pooled_rule": round(exp_rate, 4),
                  "realised_flagged_under_pooled_rule": sum(1 for r in rs if th.is_flagged(float(r["score"]), rule, r["label"])),
                  "uninformative": exp_rate > UNINFORMATIVE_RATE}
    return out


def global_cap(out_dir: Path, ns, allowance: float) -> float:
    """The cap handed to one view's client: its own cache's spend so far plus whatever the global
    allowance (1.5 x the estimate, never above the brief's loose cap) has left after every opus dollar
    paid so far in part 2 (review 2026-10-26 finding 5)."""
    spent = dollars_so_far(out_dir, ns.model)
    remaining = max(0.0, min(allowance, LOOSE_CAP_USD) - spent)
    return remaining


async def score_view(view: str, items: list[dict], ns, out_dir: Path, allowance: float, note: str) -> tuple[dict, list[dict], float]:
    remaining = global_cap(out_dir, ns, allowance)
    if remaining <= 0:
        raise SystemExit(f"refusing: the global allowance ${allowance} is spent (${dollars_so_far(out_dir, ns.model)} so far)")
    jc = make_client(view, out_dir, ns.model, ns.effort, concurrency=ns.concurrency, rpm=ns.rpm, spend_cap_usd=None)
    jc.spend_cap_usd = jc.dollars_cached + remaining
    recs, aborted = await sv.score_items(jc, items, view, 0)
    jc.batch_log(out_dir / "judge-batches.jsonl", note=note + (" ABORTED" if aborted else ""))
    if aborted:
        raise SystemExit(f"ABORTED on {note}: {aborted}")
    rows = [sv.to_row(it, recs.get(it["key"])) for it in items]
    return recs, rows, jc.stats()["dollars"]


async def null(ns, out_dir: Path) -> int:
    est_p = out_dir / "judge-estimate.json"
    if not est_p.exists():
        raise SystemExit("refusing: run `estimate` first")
    est = load_json(est_p)
    if not est.get("under_stop_line") or est.get("effort") != ns.effort or est.get("model") != ns.model:
        raise SystemExit(f"refusing: the estimate on file ({est.get('model')}, {est.get('effort')}, ${est.get('total_est_usd')}) does not license this run")
    require_identity(est, ns, "the estimate")
    cap = round(est["total_est_usd"] * 1.5, 2)
    U = build_units(ns)
    if not U["repro"]["all_reproduced"]:
        raise SystemExit(f"refusing: the units do not reproduce: {U['repro']}")
    out: dict[str, Any] = {"version": VERSION, "model": ns.model, "effort": ns.effort, "max_tokens": OPUS_MAX_TOKENS,
                           "allowance_usd": cap, "views": {}, "dollars": 0.0, "stop": False, "defective": {}}
    for view in ("O_diff", "P_author"):
        recs, rows, dollars = await score_view(view, U["honest"][view], ns, out_dir, cap, f"{STEM_TAG} null {view}")
        out["dollars"] += dollars
        summ = sv.summarise(rows)
        defect = sv.defect_check(summ, packets_ok=not any(r.get("truncated") for r in rows))
        rec: dict[str, Any] = {"n_units": len(rows), "summary": summ, "defect_check": defect,
                               "model_served": dict(Counter(r.get("model_served") for r in rows)),
                               "stop_reasons": dict(Counter(r.get("stop_reason") for r in rows)),
                               "output_tokens_mean": round(sum(r.get("output_tokens") or 0 for r in rows) / max(1, len(rows)), 1),
                               "rows": rows}
        out["views"][view] = rec
        out["defective"][view] = defect["any_defect"]
        # the report is written before any threshold is fitted, so a defective or empty null still leaves
        # F4's record (review 2026-10-26 finding 7)
        out["dollars_cumulative"] = dollars_so_far(out_dir, ns.model)
        write_json(out_dir / "judge-null.json", out)
        if defect["any_defect"] or summ["n_scored"] == 0:
            out["stop"] = True
            out["ts"] = jc_mod._now_iso()
            write_json(out_dir / "judge-null.json", out)
            print(json.dumps({"stop": True, "view": view, "defect_check": defect, "summary": {k: summ.get(k) for k in ("n", "by_outcome", "top_share", "distinct_above_median")}}, indent=1))
            return 1
        if view == "O_diff":
            rule = unit_rule(rows, view, RATES[view])
            rec["rule"] = rule
            rec["per_document"] = per_document(rows, rule)
            rec["units_by_span_days"] = dict(Counter(r.get("span_days") for r in rows))
        else:
            rec["unit_rule"] = unit_rule(rows, view, RATES[view])
            rec["author_rule"] = author_rule(rows, U["account_days"], RATES[view])
            rec["headroom_three_or_fewer_one_line_changes"] = {"n_pairs": sum(1 for r in rows if r.get("n_changes", 0) <= 3 and r.get("all_one_line")),
                                                              "max": max([float(r["score"]) for r in rows if r.get("n_changes", 0) <= 3 and r.get("all_one_line") and r.get("score") is not None], default=None)}
    out["ts"] = jc_mod._now_iso()
    out["dollars_cumulative"] = dollars_so_far(out_dir, ns.model)
    write_json(out_dir / "judge-null.json", out)
    print(json.dumps({"dollars": out["dollars"], "defective": out["defective"], "stop": out["stop"],
                      "O_diff_rule": {k: out["views"]["O_diff"]["rule"].get(k) for k in ("threshold", "p_tie", "expected_rate", "distinct_scores")},
                      "P_author_author_rule": {k: out["views"]["P_author"]["author_rule"].get(k) for k in ("threshold", "p_tie", "expected_cost", "realised_cost")},
                      "summaries": {v: {k: out["views"][v]["summary"].get(k) for k in ("n", "by_outcome", "median", "p90", "p95", "max", "top_share", "distinct_above_median")} for v in out["views"]}}, indent=1))
    return 1 if out["stop"] else 0


async def plants(ns, out_dir: Path) -> int:
    np_ = out_dir / "judge-null.json"
    if not np_.exists():
        raise SystemExit("refusing: run `null` first")
    nul = load_json(np_)
    if nul.get("stop"):
        raise SystemExit("refusing: the null is defective under 11.12(d); part 2 stopped")
    require_identity(nul, ns, "the null")
    est = load_json(out_dir / "judge-estimate.json")
    require_identity(est, ns, "the estimate")
    cap = round(est["total_est_usd"] * 1.5, 2)
    U = build_units(ns)
    if not U["repro"]["all_reproduced"]:
        raise SystemExit(f"refusing: the units do not reproduce: {U['repro']}")
    dollars = 0.0
    counts = {}
    for view in ("O_diff", "P_author"):
        recs, rows, d = await score_view(view, U["plants"][view], ns, out_dir, cap, f"{STEM_TAG} plants {view}")
        dollars += d
        counts[view] = dict(Counter(r["outcome"] for r in rows))
    write_json(out_dir / "judge-plants.json", {"version": VERSION, **identity(ns), "dollars": dollars, "outcomes": counts,
                                                "dollars_cumulative": dollars_so_far(out_dir, ns.model), "ts": jc_mod._now_iso()})
    print(json.dumps({"dollars": dollars, "outcomes": counts}, indent=1))
    return 0


# ── results ─────────────────────────────────────────────────────────────────

def opus_seal(seal: dict, nul: dict) -> dict:
    """The Sonnet seal with the O_diff rule / per-document record and the P_author rules replaced by the
    stronger judge's own (P_own and P_author_ctx stay Sonnet's, disclosed)."""
    s = json.loads(json.dumps(seal))
    o = nul["views"]["O_diff"]
    s["views"]["O_diff"]["rule"] = o["rule"]
    s["views"]["O_diff"]["per_document"] = o["per_document"]
    p = nul["views"]["P_author"]
    s["views"]["P_author"]["unit_rule"] = p["unit_rule"]
    s["views"]["P_author"]["author_rule"] = p["author_rule"]
    s["binding"] = {**s["binding"], "model": nul["model"], "note": "O_diff and P_author under the stronger judge; P_own and P_author_ctx Sonnet"}
    return s


def honest_pairs_from_rows(rows: list[dict]) -> dict[tuple[str, str], float]:
    return {(r["author"], r["path"]): float(r["score"]) for r in rows if r.get("outcome") == "scored" and r.get("score") is not None}


def curve(honest_scores: list[float], per_regime_scores: dict[str, list[float]]) -> list[dict]:
    ts_ = sorted(set(honest_scores) | {x for v in per_regime_scores.values() for x in v})
    out = []
    for t in ts_:
        row = {"t": t, "honest_exceedance": round(sum(1 for x in honest_scores if x >= t) / len(honest_scores), 4)}
        for reg, sc in per_regime_scores.items():
            row[f"{reg}_recall"] = round(sum(1 for x in sc if x >= t) / len(sc), 4) if sc else None
        out.append(row)
    return out


def invisibility(res: dict, arule: dict) -> dict:
    """Payloads flagged in no arm by O_diff (sealed/own pooled rule) and by no arm's P_author (author rule, union)."""
    out = {}
    for reg, r in res["regimes"].items():
        o_any: dict[str, bool] = defaultdict(bool)
        for x in r["O_diff"]["rows"]:
            o_any[x["payload_id"]] |= bool(x["flagged"])
        pa_any: dict[str, bool] = defaultdict(bool)
        for key, units in r["P_author"]["planted_unit_scores"].items():
            pid = key.split(":")[0]
            pa_any[pid] |= any(u["union_max"] is not None and th.is_flagged(float(u["union_max"]), arule, u["author"]) for u in units)
        pids = sorted(set(o_any) | set(pa_any))
        inv = [p for p in pids if not o_any[p] and not pa_any[p]]
        out[reg] = {"n_payloads": len(pids), "O_diff_any_arm": sum(1 for p in pids if o_any[p]), "P_author_any_arm": sum(1 for p in pids if pa_any[p]),
                    "invisible": len(inv), "invisible_ids": inv}
    return out


def results(ns, out_dir: Path) -> int:
    if not (out_dir / "judge-plants.json").exists():
        raise SystemExit("refusing: run `plants` first")
    U = build_units(ns)
    seal, manifest, payloads = U["seal"], U["manifest"], U["payloads"]
    nul = load_json(out_dir / "judge-null.json")
    require_identity(nul, ns, "the null")
    require_identity(load_json(out_dir / "judge-plants.json"), ns, "the plant run")
    son = seal["binding"]["model"]
    V, T = Path(ns.views_dir), Path(ns.t1v2_dir)
    # records: Opus for O_diff and P_author (plants), Sonnet for P_own and P_author_ctx
    recs = {"O_diff": {r["cache_key"]: r for r in read_jsonl(cache_path(out_dir, "O_diff", ns.model, ns.effort))},
            "P_author": {r["cache_key"]: r for r in read_jsonl(cache_path(out_dir, "P_author", ns.model, ns.effort))},
            "P_own": {r["cache_key"]: r for r in read_jsonl(T / f"judge-cache.t1v2.P_own.{slug(son)}.jsonl")},
            "P_author_ctx": {r["cache_key"]: r for r in read_jsonl(T / f"judge-cache.t1v2.P_author_ctx.{slug(son)}.jsonl")}}
    oseal = opus_seal(seal, nul)
    honest = {"P_author": honest_pairs_from_rows(nul["views"]["P_author"]["rows"]),
              "P_author_ctx": ts.honest_pairs(load_json(V / "p_author_c3.json"))}
    h_od = ts.honest_odiff_dayend({"rows": nul["views"]["O_diff"]["rows"]}, oseal["views"]["O_diff"]["rule"])
    h_po = ts.honest_pown(V / "p_own.parquet", seal["views"]["P_own"]["rule"], U["stem"])
    res_opus = v2.analyse_v2(U["items_all"], recs, oseal, U["results"], payloads, manifest, honest=honest, honest_odiff=h_od, honest_pieces=h_po)
    son_res = load_json(T / "t1v2-results.json")
    # the exploratory curves
    opus_h = [float(r["score"]) for r in nul["views"]["O_diff"]["rows"] if r["outcome"] == "scored"]
    son_h = [float(r["score"]) for r in read_jsonl(V / f"judge-cache.O_diff.{slug(son)}.jsonl") if r["outcome"] == "scored"]
    def composed_scores(res):
        return {reg: [float(x["score"]) for x in res["regimes"][reg]["O_diff"]["rows"] if x["score"] is not None] for reg in res["regimes"]}
    curves = {"opus": curve(opus_h, composed_scores(res_opus)), "sonnet": curve(son_h, composed_scores(son_res))}
    inv = {"opus": invisibility(res_opus, oseal["views"]["P_author"]["author_rule"]),
           "sonnet": invisibility(son_res, seal["views"]["P_author"]["author_rule"])}
    # the comparison table
    def row(res, reg):
        r = res["regimes"].get(reg)
        if not r:
            return None
        return {"O_diff_share": r["O_diff"]["share"], "O_diff_ci95": r["O_diff"]["ci95"], "O_diff_by_arm": r["O_diff"]["by_arm"],
                "O_diff_paired_control": r["O_diff"]["paired_honest_control"]["share_among_counterpart_unflagged"],
                "P_author": {a: {"recall": r["P_author"]["arms"][a]["recall"], "ci95": r["P_author"]["arms"][a]["ci95"], "n": r["P_author"]["arms"][a]["n_delivered"]} for a in ARMS},
                "P_author_curve": r["P_author"]["curve"], "document_classes": r["O_diff"]["document_classes"],
                "incomplete": r["incomplete"]}
    table = {reg: {"opus": row(res_opus, reg), "sonnet": row(son_res, reg)} for reg in REGIMES}
    # a regime whose Opus O_diff or P_author units did not all score is not evaluable (review 2026-10-26 finding 6);
    # its recalls stay in the table as provisional, marked, and no prediction is read on it
    not_evaluable = {reg: {k: v for k, v in (table[reg]["opus"] or {}).get("incomplete", {}).items() if k in ("O_diff", "P_author")} for reg in REGIMES}
    for reg in REGIMES:
        if table[reg]["opus"] is not None:
            table[reg]["opus"]["evaluable"] = not not_evaluable[reg]
    c_o, c_s = table["conforming"]["opus"], table["conforming"]["sonnet"]
    sh_o = table["sham"]["opus"]
    ev1 = not not_evaluable["conforming"] and not not_evaluable["sham"]
    pred1 = {"prediction": "conforming composed recall rises above Sonnet's 0.34 while the sham arm stays at or under 0.10, at Opus's own 10 percent honest threshold",
             "opus_conforming_O_diff": c_o["O_diff_share"], "sonnet_conforming_O_diff": c_s["O_diff_share"], "opus_sham_O_diff": sh_o["O_diff_share"],
             "evaluable": ev1,
             "held": (c_o["O_diff_share"] is not None and c_o["O_diff_share"] > c_s["O_diff_share"] and sh_o["O_diff_share"] <= 0.10) if ev1 else None}
    d_o = (c_o["O_diff_share"] or 0) - (c_s["O_diff_share"] or 0)
    d_pa = (c_o["P_author"]["lone"]["recall"] or 0) - (c_s["P_author"]["lone"]["recall"] or 0)
    ev2 = not not_evaluable["conforming"]
    pred2 = {"prediction": "P_author's conforming lone recall rises by less than O_diff's conforming composed recall does (Opus minus Sonnet)",
             "O_diff_rise": round(d_o, 4), "P_author_lone_rise": round(d_pa, 4), "evaluable": ev2, "held": (d_pa < d_o) if ev2 else None}
    dollars = {"null_run": nul["dollars"], "plants_run": load_json(out_dir / "judge-plants.json")["dollars"],
               "smoke": (load_json(out_dir / "judge-smoke.json") or {}).get("cost_usd"),
               "cumulative_all_opus_records_plus_smoke": dollars_so_far(out_dir, ns.model)}
    dollars["total"] = dollars["cumulative_all_opus_records_plus_smoke"]
    out = {"version": VERSION, "model": ns.model, "model_served": nul["views"]["O_diff"]["model_served"], "effort": ns.effort,
           "max_tokens": OPUS_MAX_TOKENS, "judge_plan_sha256": sv.file_sha256(Path(ns.plan)) if ns.plan else None,
           "thresholds": {"opus": {"O_diff": {k: oseal["views"]["O_diff"]["rule"].get(k) for k in ("threshold", "p_tie", "expected_rate", "n", "distinct_scores")},
                                   "P_author_author": {k: oseal["views"]["P_author"]["author_rule"].get(k) for k in ("threshold", "p_tie", "expected_cost", "realised_cost")},
                                   "P_author_unit": {k: oseal["views"]["P_author"]["unit_rule"].get(k) for k in ("threshold", "p_tie", "expected_rate")}},
                          "sonnet": {"O_diff": {k: seal["views"]["O_diff"]["rule"].get(k) for k in ("threshold", "p_tie", "expected_rate", "n", "distinct_scores")},
                                     "P_author_author": {k: seal["views"]["P_author"]["author_rule"].get(k) for k in ("threshold", "p_tie", "expected_cost", "realised_cost")}}},
           "null_summaries": {v: nul["views"][v]["summary"] for v in nul["views"]}, "null_defect_check": {v: nul["views"][v]["defect_check"] for v in nul["views"]},
           "honest_exceedance_per_document": {"opus": {p: v["expected_exceedance_under_pooled_rule"] for p, v in oseal["views"]["O_diff"]["per_document"].items()},
                                              "sonnet": {p: v["expected_exceedance_under_pooled_rule"] for p, v in seal["views"]["O_diff"]["per_document"].items()}},
           "predictions": {"1": pred1, "2": pred2}, "table": table, "curves": curves, "invisibility": inv, "dollars": dollars,
           "incomplete": res_opus["incomplete"], "not_evaluable_regimes": {r: v for r, v in not_evaluable.items() if v},
           "regime_contrasts_opus": res_opus.get("regime_contrasts"),
           "disclosures": ["the T1 v2 placeholders were written by a Claude session (brief 07g) and the judge shares the model family",
                           "P_own and the P_author context-3 variant stay at Sonnet; only O_diff and P_author (context 0) are re-scored",
                           "Opus's thresholds are its own (same mechanism, same rates, same tie seed and labels), not the seal's; no sealed threshold moves",
                           f"effort {ns.effort}, max_tokens {OPUS_MAX_TOKENS}, adaptive thinking: an operating point, not a calibration"],
           "opus_full": res_opus, "ts": jc_mod._now_iso()}
    write_json(out_dir / "judge-results.json", out)
    md = results_md(out)
    (out_dir / "judge-results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def _f(v):
    return "–" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))


def results_md(out: dict) -> str:
    p1, p2 = out["predictions"]["1"], out["predictions"]["2"]
    def held(p):
        return "not evaluable (an Opus unit did not score)" if not p.get("evaluable", True) else str(p["held"])
    L = [f"# The stronger composed judge (brief 07i part 2; {out['model']} served as {list(out['model_served'])}; effort {out['effort']}; {out['ts']})\n",
         f"**Prediction 1 held: {held(p1)}** (conforming composed recall Opus {_f(p1['opus_conforming_O_diff'])} against Sonnet {_f(p1['sonnet_conforming_O_diff'])}; sham Opus {_f(p1['opus_sham_O_diff'])}). "
         f"**Prediction 2 held: {held(p2)}** (O_diff rise {_f(p2['O_diff_rise'])}, P_author lone rise {_f(p2['P_author_lone_rise'])}). Dollars {out['dollars']}. "
         + (f"**Not evaluable regimes: {out['not_evaluable_regimes']}.** " if out.get("not_evaluable_regimes") else "") + "\n",
         f"Opus thresholds: O_diff {out['thresholds']['opus']['O_diff']}; P_author author-level {out['thresholds']['opus']['P_author_author']}. "
         f"Sonnet (sealed): O_diff {out['thresholds']['sonnet']['O_diff']}; P_author author-level {out['thresholds']['sonnet']['P_author_author']}.\n",
         f"Null defect check: {out['null_defect_check']}; null summaries: " + json.dumps({v: {k: s.get(k) for k in ('n', 'by_outcome', 'median', 'p90', 'p95', 'max', 'top_share', 'distinct_above_median')} for v, s in out['null_summaries'].items()}) + "\n",
         "| reading | conforming Opus (Sonnet) | alarming Opus (Sonnet) | sham Opus (Sonnet) |", "|---|---|---|---|"]
    def cell(reg, f):
        o, s = out["table"][reg]["opus"], out["table"][reg]["sonnet"]
        return f"{f(o)} ({f(s)})" if o and s else "–"
    L.append("| O_diff composed flagged (own pooled rule) | " + " | ".join(cell(r, lambda x: f"{_f(x['O_diff_share'])} {x['O_diff_ci95']}") for r in REGIMES) + " |")
    L.append("| O_diff by arm lone / k2 / k3 | " + " | ".join(cell(r, lambda x: " / ".join(f"{x['O_diff_by_arm'][a]['flagged']}/{x['O_diff_by_arm'][a]['n']}" for a in ARMS)) for r in REGIMES) + " |")
    L.append("| O_diff paired honest control | " + " | ".join(cell(r, lambda x: _f(x["O_diff_paired_control"])) for r in REGIMES) + " |")
    for a in ARMS:
        L.append(f"| P_author {a} recall (author rule) | " + " | ".join(cell(r, lambda x, a=a: f"{_f(x['P_author'][a]['recall'])} {x['P_author'][a]['ci95']}") for r in REGIMES) + " |")
    L.append("\n**Document classes (conforming; Opus class (Sonnet class)):** " + "; ".join(
        f"{p.split('/')[-1]}: {v['class']} {v['t1_flagged']}/{v['t1_composed']} ({out['table']['conforming']['sonnet']['document_classes'][p]['class']} {out['table']['conforming']['sonnet']['document_classes'][p]['t1_flagged']}/{out['table']['conforming']['sonnet']['document_classes'][p]['t1_composed']})"
        for p, v in out["table"]["conforming"]["opus"]["document_classes"].items()) + f". Honest exceedance per document Opus {out['honest_exceedance_per_document']['opus']}.\n")
    L.append("**Invisibility (payloads flagged in no arm by O_diff and by no arm's P_author):** " + json.dumps({j: {r: {k: v[k] for k in ('n_payloads', 'O_diff_any_arm', 'P_author_any_arm', 'invisible')} for r, v in d.items()} for j, d in out["invisibility"].items()}) + "\n")
    L.append("**Exploratory recall-at-honest-exceedance (conforming composed recall at t; honest exceedance at t), Opus then Sonnet, at the honest exceedances nearest 0.10, 0.20, 0.30, 0.40:**")
    for j in ("opus", "sonnet"):
        picks = []
        for target in (0.10, 0.20, 0.30, 0.40):
            best = min(out["curves"][j], key=lambda r: abs(r["honest_exceedance"] - target))
            picks.append(f"t {best['t']}: conforming {_f(best.get('conforming_recall'))} at honest {_f(best['honest_exceedance'])} (sham {_f(best.get('sham_recall'))})")
        L.append(f"- {j}: " + "; ".join(picks))
    L.append("\nDisclosures: " + "; ".join(out["disclosures"]) + ".")
    L.append(f"\nIncomplete views: {out['incomplete'] or 'none'}.")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=("smoke", "estimate", "null", "plants", "results"))
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--payloads", required=True)
    ap.add_argument("--plants", required=True)
    ap.add_argument("--seal", required=True)
    ap.add_argument("--views-dir", required=True)
    ap.add_argument("--t1v2-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--template", default=str(sv.jc_mod.FORK / "bootstrap" / "org_template.yaml"))
    ap.add_argument("--model", default="anthropic.claude-opus-5-5")
    ap.add_argument("--effort", default="high")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--rpm", type=int, default=30)
    ns = ap.parse_args(argv)
    out_dir = Path(ns.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if ns.mode == "smoke":
        return asyncio.run(smoke(ns, out_dir))
    if ns.mode == "estimate":
        return asyncio.run(estimate(ns, out_dir))
    if ns.mode == "null":
        return asyncio.run(null(ns, out_dir))
    if ns.mode == "plants":
        return asyncio.run(plants(ns, out_dir))
    return results(ns, out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
