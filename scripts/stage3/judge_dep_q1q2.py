#!/usr/bin/env python3
"""Brief 07n part A: judge dependence of the composed view. Two non-Anthropic judges (Kimi K3 and
GLM 5.3 through OpenRouter, key 1 only) each get the seal's units, their own honest null, their own
thresholds by the seal's mechanism and the 11.12(d) defect check before any plant is scored; then the
T1 v2 plants; the T1 v2 table under each judge beside Sonnet's.

Pre-registration: `work/stage3/q1q2-synthetic/judge-dep-plan.md` (committed before the first call).
Builds on `judge_opus_q1q2.py` (the unit builder, the threshold and per-document helpers, the
analysis through `stage3_t1v2_score.analyse_v2`) and `judge_openrouter.py` (the adapter).

Modes, per --judge (kimi | glm), in order; each refuses to run before the previous one's file exists:
  models    resolve the ids, context and prices from the OpenRouter models endpoint -> judge-dep-models.json
  smoke     the first five honest O_diff units (cached; output tokens measured) -> judge-dep-smoke.<judge>.json
  estimate  both judges' estimates from the smokes -> judge-dep-estimate.json (stop line $30, cap $40)
  null      the honest null, defect check, thresholds -> judge-dep-null.<judge>.json
  plants    the 152 composed O_diff and 288 P_author units -> judge-dep-plants.<judge>.json
  results   the table for every judge with a plant run -> judge-dep-results.{json,md}

    cd work/mole-fork && set -a && source .env && set +a && cd ../checks && \\
    ../mole-fork/.venv/bin/python -I judge_dep_q1q2.py <mode> --judge kimi --corpus ... --payloads ... --plants ... \\
        --seal ../stage3/views/calibration-v1.json --views-dir ../stage3/views --t1v2-dir ../stage3/t1v2 \\
        --out-dir ../stage3/q1q2-synthetic --plan ../stage3/q1q2-synthetic/judge-dep-plan.md
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import judge_client as jc_mod  # noqa: E402
import judge_openrouter as jo  # noqa: E402
import judge_opus_q1q2 as base  # noqa: E402
import stage3_t1_score as ts  # noqa: E402
import stage3_t1v2_score as v2  # noqa: E402
import stage3_thresholds as th  # noqa: E402
import stage3_views as sv  # noqa: E402

VERSION = "judge-dep-q1q2/v1"
JUDGES = {"kimi": {"name": "Kimi K3", "id": "moonshotai/kimi-k3"},
          "glm": {"name": "GLM 5.3", "id": "z-ai/glm-5.3"}}
MODELS_URL = "https://openrouter.ai/api/v1/models"
SMOKE_N = 5
ESTIMATE_STOP_USD = 30.0
CAP_USD = 40.0
STEM_TAG = "q1q2dep"
ARMS = base.ARMS
REGIMES = base.REGIMES
RATES = base.RATES


def slug(model: str) -> str:
    return model.replace("/", "_").replace(":", "_").replace(".", "-")


def cache_path(out_dir: Path, view: str, judge: str) -> Path:
    return out_dir / f"judge-cache.{STEM_TAG}.{view}.{slug(JUDGES[judge]['id'])}.jsonl"


def models_file(out_dir: Path) -> dict:
    return base.load_json(out_dir / "judge-dep-models.json")


def prices_of(models: dict, judge: str) -> tuple[dict[str, float], str]:
    m = models["judges"][judge]
    return {"prompt": float(m["pricing"]["prompt"]), "completion": float(m["pricing"]["completion"])}, models["price_source"]


def make_judge(view: str, judge: str, out_dir: Path, models: dict, *, concurrency: int, rpm: int,
               spend_cap_usd: float | None) -> jo.OpenRouterJudge:
    prices, src = prices_of(models, judge)
    cp = cache_path(out_dir, view, judge)
    j = jo.OpenRouterJudge(cp, JUDGES[judge]["id"], system=sv.system_prompt(view, 0), prompt_version=sv.prompt_version(view, 0),
                           prices=prices, price_source=src, concurrency=concurrency, rpm=rpm, spend_cap_usd=spend_cap_usd)
    want = jc_mod.sha256(sv.system_prompt(view, 0))
    bad = [r.get("cache_key") for r in j.cache.values() if (r.get("request_params") or {}).get("system_sha256") not in (None, want)
           or (r.get("request_params") or {}).get("max_tokens") != jo.MAX_TOKENS]
    if bad:
        raise SystemExit(f"refusing: cache {cp} holds {len(bad)} record(s) under another system prompt or max_tokens")
    return j


def all_records(out_dir: Path, judge: str) -> list[dict]:
    recs = []
    for p in sorted(out_dir.glob(f"judge-cache.{STEM_TAG}.*.{slug(JUDGES[judge]['id'])}.jsonl")):
        recs += base.read_jsonl(p)
    return recs


def dollars_so_far(out_dir: Path) -> dict:
    per = {j: round(sum(float(r.get("cost_usd") or 0.0) for r in all_records(out_dir, j)), 6) for j in JUDGES}
    per["total"] = round(sum(per.values()), 6)
    return per


def allowance_left(out_dir: Path) -> float:
    return max(0.0, CAP_USD - dollars_so_far(out_dir)["total"])


# ── modes ───────────────────────────────────────────────────────────────────

def models(ns, out_dir: Path) -> int:
    with urllib.request.urlopen(MODELS_URL, timeout=60) as r:
        data = json.load(r)["data"]
    by_id = {m["id"]: m for m in data}
    out: dict[str, Any] = {"version": VERSION, "source": MODELS_URL, "fetched_at": jc_mod._now_iso(),
                           "price_source": f"openrouter-list:{MODELS_URL}@{jc_mod._now_iso()[:10]}", "judges": {}}
    for j, spec in JUDGES.items():
        m = by_id.get(spec["id"])
        out["judges"][j] = {"name": spec["name"], "id": spec["id"], "served": m is not None,
                            "context_length": (m or {}).get("context_length"),
                            "pricing": {k: (m or {}).get("pricing", {}).get(k) for k in ("prompt", "completion", "internal_reasoning")},
                            "supported_parameters": (m or {}).get("supported_parameters"),
                            "candidates_seen": sorted(i for i in by_id if spec["id"].split("/")[1].split("-")[0] in i.lower())}
    out["served"] = [j for j in JUDGES if out["judges"][j]["served"]]
    base.write_json(out_dir / "judge-dep-models.json", out)
    print(json.dumps({j: {k: v for k, v in d.items() if k != "candidates_seen"} for j, d in out["judges"].items()}, indent=1))
    return 0 if out["served"] else 1


async def smoke(ns, out_dir: Path) -> int:
    m = models_file(out_dir)
    if not m["judges"][ns.judge]["served"]:
        raise SystemExit(f"refusing: {ns.judge} is not served")
    U = base.build_units(ns)
    if not U["repro"]["all_reproduced"]:
        raise SystemExit(f"refusing: the units do not reproduce the Sonnet caches' packets: {U['repro']}")
    pilot = U["honest"]["O_diff"][:SMOKE_N]
    j = make_judge("O_diff", ns.judge, out_dir, m, concurrency=1, rpm=ns.rpm, spend_cap_usd=0.5)
    recs, aborted = await sv.score_items(j, pilot, "O_diff", 0)
    out = {"version": VERSION, "judge": ns.judge, "model": JUDGES[ns.judge]["id"], "n": len(pilot), "aborted": aborted,
           "labels": [it["label"] for it in pilot],
           "records": [{k: r.get(k) for k in ("label", "outcome", "score", "finish_reason", "input_tokens", "output_tokens",
                                             "reasoning_tokens", "cost_usd", "cost_source", "attempts", "latency_s")} for r in recs.values()],
           "packet_chars": [len(it["packet"]) + len(sv.system_prompt("O_diff", 0)) for it in pilot],
           "dollars": j.stats()["dollars"], "stats": j.stats(), "ts": jc_mod._now_iso()}
    base.write_json(out_dir / f"judge-dep-smoke.{ns.judge}.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "labels"}, indent=1))
    return 1 if aborted else 0


def _est(items: list[dict], view: str, prices: dict[str, float], chars_per_token: float, out_per_call: float) -> dict:
    live = [it for it in items if it.get("packet") is not None]
    chars = sum(len(it["packet"]) + len(sv.system_prompt(view, 0)) for it in live)
    in_tok = chars / chars_per_token
    out_tok = len(live) * out_per_call
    return {"n_calls": len(live), "packet_chars": chars, "est_input_tokens": round(in_tok), "est_output_tokens": round(out_tok),
            "est_cost_usd": round(in_tok * prices["prompt"] + out_tok * prices["completion"], 4)}


def estimate(ns, out_dir: Path) -> int:
    m = models_file(out_dir)
    U = base.build_units(ns)
    out: dict[str, Any] = {"version": VERSION, "judges": {}, "stop_line_usd": ESTIMATE_STOP_USD, "cap_usd": CAP_USD}
    total = 0.0
    for j in m["served"]:
        sp = out_dir / f"judge-dep-smoke.{j}.json"
        if not sp.exists():
            raise SystemExit(f"refusing: no smoke for {j}")
        s = base.load_json(sp)
        scored = [r for r in s["records"] if r["outcome"] == "scored"]
        if len(scored) < 3:
            raise SystemExit(f"refusing: the {j} smoke scored {len(scored)} of {s['n']} units; no estimate without a usable smoke")
        outs = [int(r["output_tokens"] or 0) for r in s["records"]]
        ins = [int(r["input_tokens"] or 0) for r in s["records"]]
        cpt = (sum(s["packet_chars"]) / sum(ins)) if sum(ins) else 2.15
        per = sum(outs) / len(outs)
        prices, _src = prices_of(m, j)
        est = {k: _est(U["honest"][v] if k.startswith("honest") else U["plants"][v], v, prices, cpt, per)
               for k, v in (("honest:O_diff", "O_diff"), ("honest:P_author", "P_author"), ("plants:O_diff", "O_diff"), ("plants:P_author", "P_author"))}
        tot = round(sum(e["est_cost_usd"] for e in est.values()), 2)
        est_max = round(sum(_est(U["honest"][v] if k.startswith("honest") else U["plants"][v], v, prices, cpt, max(outs))["est_cost_usd"]
                            for k, v in (("honest:O_diff", "O_diff"), ("honest:P_author", "P_author"), ("plants:O_diff", "O_diff"), ("plants:P_author", "P_author"))), 2)
        worst = round(sum(_est(U["honest"][v] if k.startswith("honest") else U["plants"][v], v, prices, cpt, jo.MAX_TOKENS)["est_cost_usd"]
                          for k, v in (("honest:O_diff", "O_diff"), ("honest:P_author", "P_author"), ("plants:O_diff", "O_diff"), ("plants:P_author", "P_author"))), 2)
        out["judges"][j] = {"model": JUDGES[j]["id"], "smoke": {"n": s["n"], "scored": len(scored), "output_tokens": outs, "input_tokens": ins,
                                                              "output_tokens_per_call": round(per, 1), "chars_per_input_token": round(cpt, 3),
                                                              "reasoning_tokens": [int(r["reasoning_tokens"] or 0) for r in s["records"]], "dollars": s["dollars"]},
                            "estimates": est, "total_est_usd": tot, "total_at_smoke_max_output": est_max, "total_if_every_call_hit_max_tokens": worst}
        total += tot
    out["total_est_usd"] = round(total, 2)
    out["under_stop_line"] = total <= ESTIMATE_STOP_USD
    out["dollars_so_far"] = dollars_so_far(out_dir)
    out["reproduction"] = U["repro"]
    out["ts"] = jc_mod._now_iso()
    base.write_json(out_dir / "judge-dep-estimate.json", out)
    print(json.dumps({k: v for k, v in out.items() if k != "reproduction"}, indent=1))
    return 0 if out["under_stop_line"] else 2


async def score_view(view: str, items: list[dict], ns, out_dir: Path, m: dict, note: str) -> tuple[dict, list[dict], float]:
    left = allowance_left(out_dir)
    if left <= 0:
        raise SystemExit(f"refusing: the part's allowance ${CAP_USD} is spent ({dollars_so_far(out_dir)})")
    j = make_judge(view, ns.judge, out_dir, m, concurrency=ns.concurrency, rpm=ns.rpm, spend_cap_usd=None)
    j.spend_cap_usd = j.dollars_cached + left
    recs, aborted = await sv.score_items(j, items, view, 0)
    j.batch_log(out_dir / "judge-dep-batches.jsonl", note=note + (" ABORTED" if aborted else ""))
    if aborted:
        raise SystemExit(f"ABORTED on {note}: {aborted}")
    rows = [sv.to_row(it, recs.get(it["key"])) for it in items]
    for row, it in zip(rows, items):
        r = recs.get(it["key"]) or {}
        row["reasoning_tokens"] = r.get("reasoning_tokens")
        row["finish_reason"] = r.get("finish_reason")
    return recs, rows, j.stats()["dollars"]


async def null(ns, out_dir: Path) -> int:
    est_p = out_dir / "judge-dep-estimate.json"
    if not est_p.exists():
        raise SystemExit("refusing: run `estimate` first")
    est = base.load_json(est_p)
    if not est.get("under_stop_line"):
        raise SystemExit(f"refusing: the estimate ${est.get('total_est_usd')} is over the stop line")
    m = models_file(out_dir)
    U = base.build_units(ns)
    if not U["repro"]["all_reproduced"]:
        raise SystemExit(f"refusing: the units do not reproduce: {U['repro']}")
    out: dict[str, Any] = {"version": VERSION, "judge": ns.judge, "model": JUDGES[ns.judge]["id"], "max_tokens": jo.MAX_TOKENS,
                           "temperature": jo.TEMPERATURE, "views": {}, "dollars": 0.0, "stop": False, "defective": {}}
    for view in ("O_diff", "P_author"):
        recs, rows, dollars = await score_view(view, U["honest"][view], ns, out_dir, m, f"{STEM_TAG} {ns.judge} null {view}")
        out["dollars"] += dollars
        summ = sv.summarise(rows)
        defect = sv.defect_check(summ, packets_ok=not any(r.get("truncated") for r in rows))
        rec: dict[str, Any] = {"n_units": len(rows), "summary": summ, "defect_check": defect,
                               "finish_reasons": dict(Counter(r.get("finish_reason") for r in rows)),
                               "refused_or_errored_by_document": {p: sum(1 for r in rows if r.get("path") == p and r["outcome"] in ("refused", "errored")) for p in sorted({r.get("path") for r in rows})},
                               "output_tokens_mean": round(sum(r.get("output_tokens") or 0 for r in rows) / max(1, len(rows)), 1),
                               "reasoning_tokens_mean": round(sum(r.get("reasoning_tokens") or 0 for r in rows) / max(1, len(rows)), 1),
                               "rows": rows}
        out["views"][view] = rec
        out["defective"][view] = defect["any_defect"]
        out["dollars_cumulative"] = dollars_so_far(out_dir)
        base.write_json(out_dir / f"judge-dep-null.{ns.judge}.json", out)
        if defect["any_defect"] or summ["n_scored"] == 0:
            out["stop"] = True
            out["ts"] = jc_mod._now_iso()
            base.write_json(out_dir / f"judge-dep-null.{ns.judge}.json", out)
            print(json.dumps({"stop": True, "judge": ns.judge, "view": view, "defect_check": defect,
                              "summary": {k: summ.get(k) for k in ("n", "by_outcome", "top_share", "distinct_above_median")}}, indent=1))
            return 1
        if view == "O_diff":
            rule = base.unit_rule(rows, view, RATES[view])
            rec["rule"] = rule
            rec["per_document"] = base.per_document(rows, rule)
            rec["units_by_span_days"] = dict(Counter(r.get("span_days") for r in rows))
        else:
            rec["unit_rule"] = base.unit_rule(rows, view, RATES[view])
            rec["author_rule"] = base.author_rule(rows, U["account_days"], RATES[view])
    out["ts"] = jc_mod._now_iso()
    out["dollars_cumulative"] = dollars_so_far(out_dir)
    base.write_json(out_dir / f"judge-dep-null.{ns.judge}.json", out)
    print(json.dumps({"judge": ns.judge, "dollars": out["dollars"], "defective": out["defective"],
                      "O_diff_rule": {k: out["views"]["O_diff"]["rule"].get(k) for k in ("threshold", "p_tie", "expected_rate", "distinct_scores")},
                      "P_author_author_rule": {k: out["views"]["P_author"]["author_rule"].get(k) for k in ("threshold", "p_tie", "expected_cost", "realised_cost")},
                      "summaries": {v: {k: out["views"][v]["summary"].get(k) for k in ("n", "by_outcome", "median", "p90", "p95", "max", "top_share", "distinct_above_median")} for v in out["views"]}}, indent=1))
    return 0


async def plants(ns, out_dir: Path) -> int:
    np_ = out_dir / f"judge-dep-null.{ns.judge}.json"
    if not np_.exists():
        raise SystemExit("refusing: run `null` first")
    nul = base.load_json(np_)
    if nul.get("stop"):
        raise SystemExit(f"refusing: {ns.judge}'s null is defective under 11.12(d); this judge stopped")
    m = models_file(out_dir)
    U = base.build_units(ns)
    if not U["repro"]["all_reproduced"]:
        raise SystemExit(f"refusing: the units do not reproduce: {U['repro']}")
    dollars = 0.0
    counts = {}
    for view in ("O_diff", "P_author"):
        recs, rows, d = await score_view(view, U["plants"][view], ns, out_dir, m, f"{STEM_TAG} {ns.judge} plants {view}")
        dollars += d
        counts[view] = dict(Counter(r["outcome"] for r in rows))
    base.write_json(out_dir / f"judge-dep-plants.{ns.judge}.json", {"version": VERSION, "judge": ns.judge, "model": JUDGES[ns.judge]["id"],
                                                                     "dollars": dollars, "outcomes": counts, "dollars_cumulative": dollars_so_far(out_dir),
                                                                     "ts": jc_mod._now_iso()})
    print(json.dumps({"judge": ns.judge, "dollars": dollars, "outcomes": counts}, indent=1))
    return 0


# ── results ─────────────────────────────────────────────────────────────────

def _pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    vx = sum((a - mx) ** 2 for a in xs)
    vy = sum((b - my) ** 2 for b in ys)
    return round(cov / math.sqrt(vx * vy), 4) if vx > 0 and vy > 0 else None


def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        k = i
        while k + 1 < len(order) and xs[order[k + 1]] == xs[order[i]]:
            k += 1
        r = (i + k) / 2 + 1
        for t in range(i, k + 1):
            ranks[order[t]] = r
        i = k + 1
    return ranks


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    return _pearson(_ranks(xs), _ranks(ys)) if len(xs) >= 3 else None


def correlations(son_rows: dict[str, float], rows: list[dict]) -> dict:
    pairs = [(son_rows[r["label"]], float(r["score"])) for r in rows if r.get("outcome") == "scored" and r.get("score") is not None and r["label"] in son_rows]
    xs, ys = [a for a, _ in pairs], [b for _, b in pairs]
    return {"n_shared_scored": len(pairs), "pearson": _pearson(xs, ys), "spearman": _spearman(xs, ys)}


def results(ns, out_dir: Path) -> int:
    U = base.build_units(ns)
    seal, manifest, payloads = U["seal"], U["manifest"], U["payloads"]
    son = seal["binding"]["model"]
    V, T = Path(ns.views_dir), Path(ns.t1v2_dir)
    son_res = base.load_json(T / "t1v2-results.json")
    son_honest = {"O_diff": {r["label"]: float(r["score"]) for r in base.read_jsonl(V / f"judge-cache.O_diff.{base.slug(son)}.jsonl") if r["outcome"] == "scored"},
                  "P_author": {r["label"]: float(r["score"]) for r in base.read_jsonl(V / f"judge-cache.P_author.{base.slug(son)}.jsonl") if r["outcome"] == "scored"}}
    son_plants = {"O_diff": {r["label"]: float(r["score"]) for r in base.read_jsonl(T / f"judge-cache.t1v2.O_diff.{base.slug(son)}.jsonl") if r["outcome"] == "scored"},
                  "P_author": {r["label"]: float(r["score"]) for r in base.read_jsonl(T / f"judge-cache.t1v2.P_author.{base.slug(son)}.jsonl") if r["outcome"] == "scored"}}
    son_inv = base.invisibility(son_res, seal["views"]["P_author"]["author_rule"])
    h_po = ts.honest_pown(V / "p_own.parquet", seal["views"]["P_own"]["rule"], U["stem"])
    out: dict[str, Any] = {"version": VERSION, "judge_dep_plan_sha256": sv.file_sha256(Path(ns.plan)) if ns.plan else None,
                           "judges": {}, "sonnet": {"model": son, "invisibility": son_inv,
                                                     "thresholds": {"O_diff": {k: seal["views"]["O_diff"]["rule"].get(k) for k in ("threshold", "p_tie", "expected_rate")},
                                                                    "P_author_author": {k: seal["views"]["P_author"]["author_rule"].get(k) for k in ("threshold", "p_tie", "expected_cost", "realised_cost")}}},
                           "dollars": dollars_so_far(out_dir), "stopped": {}}
    done = []
    for j in JUDGES:
        np_ = out_dir / f"judge-dep-null.{j}.json"
        if not np_.exists():
            out["stopped"][j] = "no null run"
            continue
        nul = base.load_json(np_)
        if nul.get("stop") or not (out_dir / f"judge-dep-plants.{j}.json").exists():
            out["stopped"][j] = "null defective under 11.12(d)" if nul.get("stop") else "plants not scored"
            out["judges"][j] = {"model": JUDGES[j]["id"], "null": {v: {k: nul["views"][v].get(k) for k in ("n_units", "summary", "defect_check", "finish_reasons", "refused_or_errored_by_document")} for v in nul["views"]}}
            continue
        recs = {"O_diff": {r["cache_key"]: r for r in base.read_jsonl(cache_path(out_dir, "O_diff", j))},
                "P_author": {r["cache_key"]: r for r in base.read_jsonl(cache_path(out_dir, "P_author", j))},
                "P_own": {r["cache_key"]: r for r in base.read_jsonl(T / f"judge-cache.t1v2.P_own.{base.slug(son)}.jsonl")},
                "P_author_ctx": {r["cache_key"]: r for r in base.read_jsonl(T / f"judge-cache.t1v2.P_author_ctx.{base.slug(son)}.jsonl")}}
        jseal = base.opus_seal(seal, nul)
        honest = {"P_author": base.honest_pairs_from_rows(nul["views"]["P_author"]["rows"]), "P_author_ctx": ts.honest_pairs(base.load_json(V / "p_author_c3.json"))}
        h_od = ts.honest_odiff_dayend({"rows": nul["views"]["O_diff"]["rows"]}, jseal["views"]["O_diff"]["rule"])
        res = v2.analyse_v2(U["items_all"], recs, jseal, U["results"], payloads, manifest, honest=honest, honest_odiff=h_od, honest_pieces=h_po)
        not_ev = {reg: {k: v for k, v in res["regimes"][reg]["incomplete"].items() if k in ("O_diff", "P_author")} for reg in res["regimes"]}
        jh = [float(r["score"]) for r in nul["views"]["O_diff"]["rows"] if r["outcome"] == "scored"]
        comp = {reg: [float(x["score"]) for x in res["regimes"][reg]["O_diff"]["rows"] if x["score"] is not None] for reg in res["regimes"]}
        inv = base.invisibility(res, jseal["views"]["P_author"]["author_rule"])
        plant_rows = {v: [sv.to_row(it, recs[v].get(it["key"])) for it in U["plants"][v]] for v in ("O_diff", "P_author")}
        table = {reg: {"O_diff_share": res["regimes"][reg]["O_diff"]["share"], "O_diff_ci95": res["regimes"][reg]["O_diff"]["ci95"],
                       "O_diff_by_arm": res["regimes"][reg]["O_diff"]["by_arm"],
                       "O_diff_paired_control": res["regimes"][reg]["O_diff"]["paired_honest_control"]["share_among_counterpart_unflagged"],
                       "P_author": {a: {"recall": res["regimes"][reg]["P_author"]["arms"][a]["recall"], "ci95": res["regimes"][reg]["P_author"]["arms"][a]["ci95"], "n": res["regimes"][reg]["P_author"]["arms"][a]["n_delivered"]} for a in ARMS},
                       "document_classes": res["regimes"][reg]["O_diff"]["document_classes"], "evaluable": not not_ev[reg]} for reg in res["regimes"]}
        out["judges"][j] = {"model": JUDGES[j]["id"],
                            "thresholds": {"O_diff": {k: jseal["views"]["O_diff"]["rule"].get(k) for k in ("threshold", "p_tie", "expected_rate", "n", "distinct_scores")},
                                           "P_author_author": {k: jseal["views"]["P_author"]["author_rule"].get(k) for k in ("threshold", "p_tie", "expected_cost", "realised_cost")},
                                           "P_author_unit": {k: jseal["views"]["P_author"]["unit_rule"].get(k) for k in ("threshold", "p_tie", "expected_rate")}},
                            "null": {v: {k: nul["views"][v].get(k) for k in ("n_units", "summary", "defect_check", "finish_reasons", "refused_or_errored_by_document", "output_tokens_mean", "reasoning_tokens_mean")} for v in nul["views"]},
                            "honest_exceedance_per_document": {p: v["expected_exceedance_under_pooled_rule"] for p, v in jseal["views"]["O_diff"]["per_document"].items()},
                            "table": table, "not_evaluable": {r: v for r, v in not_ev.items() if v}, "incomplete": res["incomplete"],
                            "curve": base.curve(jh, comp), "invisibility": inv,
                            "correlations_with_sonnet": {"honest_O_diff": correlations(son_honest["O_diff"], nul["views"]["O_diff"]["rows"]),
                                                         "honest_P_author": correlations(son_honest["P_author"], nul["views"]["P_author"]["rows"]),
                                                         "plants_O_diff": correlations(son_plants["O_diff"], plant_rows["O_diff"]),
                                                         "plants_P_author": correlations(son_plants["P_author"], plant_rows["P_author"])},
                            "plants_outcomes": {v: dict(Counter(r["outcome"] for r in plant_rows[v])) for v in plant_rows},
                            "regime_contrasts": res.get("regime_contrasts"), "full": res}
        done.append(j)
    # the Sonnet rows beside
    out["sonnet"]["table"] = {reg: {"O_diff_share": son_res["regimes"][reg]["O_diff"]["share"], "O_diff_ci95": son_res["regimes"][reg]["O_diff"]["ci95"],
                                    "O_diff_by_arm": son_res["regimes"][reg]["O_diff"]["by_arm"],
                                    "O_diff_paired_control": son_res["regimes"][reg]["O_diff"]["paired_honest_control"]["share_among_counterpart_unflagged"],
                                    "P_author": {a: {"recall": son_res["regimes"][reg]["P_author"]["arms"][a]["recall"], "ci95": son_res["regimes"][reg]["P_author"]["arms"][a]["ci95"]} for a in ARMS},
                                    "document_classes": son_res["regimes"][reg]["O_diff"]["document_classes"]} for reg in REGIMES}
    out["sonnet"]["curve"] = base.curve(list(son_honest["O_diff"].values()), {reg: [float(x["score"]) for x in son_res["regimes"][reg]["O_diff"]["rows"] if x["score"] is not None] for reg in REGIMES})
    # the predictions (judge-dep-plan.md A2)
    s_conf = son_res["regimes"]["conforming"]["O_diff"]["share"]
    son_inv_set = set(son_inv["conforming"]["invisible_ids"])
    preds: dict[str, Any] = {}
    for j in done:
        t = out["judges"][j]["table"]
        ev = t["conforming"]["evaluable"] and t["sham"]["evaluable"]
        c, s = t["conforming"]["O_diff_share"], t["sham"]["O_diff_share"]
        preds[f"1_{j}"] = {"prediction": "conforming composed recall within 0.15 of Sonnet's and the sham rate at or under 0.10",
                           "conforming": c, "sonnet_conforming": s_conf, "sham": s, "evaluable": ev,
                           "held": (abs(c - s_conf) <= 0.15 and s <= 0.10) if ev else None}
        lone = t["conforming"]["P_author"]["lone"]["recall"]
        preds[f"3_{j}"] = {"prediction": "P_author's conforming lone recall under 0.3", "lone": lone, "evaluable": t["conforming"]["evaluable"],
                           "held": (lone < 0.3) if t["conforming"]["evaluable"] else None}
    inv_sets = {j: set(out["judges"][j]["invisibility"]["conforming"]["invisible_ids"]) for j in done}
    every = set.intersection(*inv_sets.values()) if inv_sets else set()
    preds["2_invisible_under_every_judge"] = {"prediction": "the payloads invisible under every judge hold at least 8 of the 13 invisible under Sonnet",
                                             "sonnet_invisible": sorted(son_inv_set), "n_sonnet_invisible": len(son_inv_set),
                                             "per_judge_invisible": {j: sorted(v) for j, v in inv_sets.items()},
                                             "invisible_under_every_judge_including_sonnet": sorted(every & son_inv_set),
                                             "overlap_with_sonnet": len(every & son_inv_set), "judges_counted": done,
                                             "evaluable": bool(done) and all(out["judges"][j]["table"]["conforming"]["evaluable"] for j in done),
                                             "held": (len(every & son_inv_set) >= 8) if done else None}
    out["predictions"] = preds
    out["judges_done"] = done
    out["disclosures"] = ["the placeholder writer's model family (Claude) differs from these judges, which removes the shared-family caveat for these rows",
                          "each judge's thresholds are its own, by the seal's mechanism at the sealed rates with the sealed tie seed and labels; no sealed threshold moves",
                          "P_own and the P_author context-3 variant stay at Sonnet; only O_diff and P_author (context 0) are re-scored",
                          f"provider-default reasoning, temperature {jo.TEMPERATURE}, max_tokens {jo.MAX_TOKENS}: an operating point, not a calibration",
                          "key 1 only (fallback keys removed from the process); costs from the provider's reported usage cost where present, else list price"]
    out["ts"] = jc_mod._now_iso()
    base.write_json(out_dir / "judge-dep-results.json", out)
    md = results_md(out)
    (out_dir / "judge-dep-results.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def _f(v):
    return "–" if v is None else (f"{v:.3f}" if isinstance(v, float) else str(v))


def results_md(out: dict) -> str:
    L = [f"# Judge dependence of the composed view (brief 07n part A; {out['ts']}; plan sha256 {str(out.get('judge_dep_plan_sha256'))[:16]}…)\n"]
    first = []
    for k, p in out["predictions"].items():
        held = "not evaluable" if p.get("evaluable") is False or p.get("held") is None else str(p["held"])
        if k.startswith("1_"):
            first.append(f"prediction 1 ({k[2:]}): held {held} (conforming {_f(p['conforming'])} against Sonnet {_f(p['sonnet_conforming'])}; sham {_f(p['sham'])})")
        elif k.startswith("3_"):
            first.append(f"prediction 3 ({k[2:]}): held {held} (lone {_f(p['lone'])})")
        else:
            first.append(f"prediction 2: held {held} ({p['overlap_with_sonnet']} of {p['n_sonnet_invisible']} Sonnet-invisible payloads invisible under every judge)")
    L.append("**" + "; ".join(first) + f". Stopped: {out['stopped'] or 'none'}. Dollars {out['dollars']}.**\n")
    judges = out["judges_done"]
    for j in judges:
        J = out["judges"][j]
        L.append(f"- **{j}** ({J['model']}): O_diff rule {J['thresholds']['O_diff']}; P_author author rule {J['thresholds']['P_author_author']}; "
                 f"null O_diff {J['null']['O_diff']['summary']['by_outcome']} (median {_f(J['null']['O_diff']['summary'].get('median'))}, p90 {_f(J['null']['O_diff']['summary'].get('p90'))}, max {_f(J['null']['O_diff']['summary'].get('max'))}; "
                 f"reasoning tokens {J['null']['O_diff'].get('reasoning_tokens_mean')} a call), null P_author {J['null']['P_author']['summary']['by_outcome']}; "
                 f"correlations with Sonnet {J['correlations_with_sonnet']}; plants outcomes {J['plants_outcomes']}.")
    for j, why in out["stopped"].items():
        L.append(f"- **{j}** stopped: {why}; null {json.dumps((out['judges'].get(j) or {}).get('null', {}), default=str)[:600]}")
    L.append(f"- **Sonnet (sealed)**: O_diff rule {out['sonnet']['thresholds']['O_diff']}; P_author author rule {out['sonnet']['thresholds']['P_author_author']}.\n")
    heads = ["Sonnet"] + judges
    L.append("| reading | regime | " + " | ".join(heads) + " |")
    L.append("|---|---|" + "---|" * len(heads))
    def tab(j):
        return out["sonnet"]["table"] if j == "Sonnet" else out["judges"][j]["table"]
    for reg in REGIMES:
        L.append(f"| O_diff composed flagged (own rule) | {reg} | " + " | ".join(f"{_f(tab(j)[reg]['O_diff_share'])} {tab(j)[reg]['O_diff_ci95']}" for j in heads) + " |")
        L.append(f"| O_diff by arm lone / k2 / k3 | {reg} | " + " | ".join(" / ".join(f"{tab(j)[reg]['O_diff_by_arm'][a]['flagged']}/{tab(j)[reg]['O_diff_by_arm'][a]['n']}" for a in ARMS) for j in heads) + " |")
        L.append(f"| O_diff paired honest control | {reg} | " + " | ".join(_f(tab(j)[reg]["O_diff_paired_control"]) for j in heads) + " |")
        for a in ARMS:
            L.append(f"| P_author {a} recall (author rule) | {reg} | " + " | ".join(f"{_f(tab(j)[reg]['P_author'][a]['recall'])} {tab(j)[reg]['P_author'][a]['ci95']}" for j in heads) + " |")
    L.append("\n**Invisible payloads (flagged in no arm by O_diff and by no arm's P_author, conforming):** " + json.dumps(
        {"sonnet": out["sonnet"]["invisibility"]["conforming"]["invisible_ids"], **{j: out["judges"][j]["invisibility"]["conforming"]["invisible_ids"] for j in judges},
         "every_judge_and_sonnet": out["predictions"]["2_invisible_under_every_judge"]["invisible_under_every_judge_including_sonnet"]}))
    L.append("\n**Document classes (conforming):** " + "; ".join(
        f"{p.split('/')[-1]}: " + ", ".join(f"{j} {tab(j)['conforming']['document_classes'][p]['class']} ({tab(j)['conforming']['document_classes'][p]['t1_flagged']}/{tab(j)['conforming']['document_classes'][p]['t1_composed']})" for j in heads)
        for p in out["sonnet"]["table"]["conforming"]["document_classes"]))
    L.append("\n**Recall at honest exceedance (conforming composed recall at the t nearest each honest exceedance; sham beside):**")
    for j in heads:
        cv = out["sonnet"]["curve"] if j == "Sonnet" else out["judges"][j]["curve"]
        picks = []
        for target in (0.05, 0.10, 0.20, 0.30):
            best = min(cv, key=lambda r: abs(r["honest_exceedance"] - target))
            picks.append(f"t {best['t']}: {_f(best.get('conforming_recall'))} at honest {_f(best['honest_exceedance'])} (sham {_f(best.get('sham_recall'))})")
        L.append(f"- {j}: " + "; ".join(picks))
    L.append("\nDisclosures: " + "; ".join(out["disclosures"]) + ".")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mode", choices=("models", "smoke", "estimate", "null", "plants", "results"))
    ap.add_argument("--judge", choices=tuple(JUDGES), default=None)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--payloads", required=True)
    ap.add_argument("--plants", required=True)
    ap.add_argument("--seal", required=True)
    ap.add_argument("--views-dir", required=True)
    ap.add_argument("--t1v2-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--plan", default=None)
    ap.add_argument("--template", default=str(sv.jc_mod.FORK / "bootstrap" / "org_template.yaml"))
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--rpm", type=int, default=30)
    ns = ap.parse_args(argv)
    out_dir = Path(ns.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if ns.mode in ("smoke", "null", "plants") and not ns.judge:
        raise SystemExit("--judge is required for this mode")
    if ns.mode == "models":
        return models(ns, out_dir)
    if ns.mode == "smoke":
        return asyncio.run(smoke(ns, out_dir))
    if ns.mode == "estimate":
        return estimate(ns, out_dir)
    if ns.mode == "null":
        return asyncio.run(null(ns, out_dir))
    if ns.mode == "plants":
        return asyncio.run(plants(ns, out_dir))
    return results(ns, out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
