#!/usr/bin/env python3
"""Step 1 of brief 07f, after the honest calibrations: the randomised thresholds of every view,
the P_author author-level rule with its bootstrap interval and headroom diagnostic, the O_diff
per-document base rates and the uninformative class, the 11.12(d) defect check per view, and the
seal record (views-calibration.md section 6; the prep report's sealed list).

Reads the step-1 outputs under work/stage3/views/ (P_own / P_ctx parquet + meta; P_author and
the O views as JSON) and writes `calibration-v1.json` (the seal: every threshold, p_tie, seed,
the shared text's version and hash, the prompt records) plus a Markdown table. Nothing here
calls the judge. No placeholder is read.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_views_seal.py --views-dir work/stage3/views \\
        --corpus work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl --out work/stage3/views/calibration-v1.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_thresholds as th  # noqa: E402
import stage3_views as sv  # noqa: E402

TIE_SEED = 20261112
BOOT_SEED = 20261114
RATES = {"P_own": 0.05, "P_ctx": 0.05, "P_author": 0.05, "P_author_ctx": 0.05, "O_diff": 0.10, "O_whole": 0.10}
UNINFORMATIVE_RATE = 0.30
N_BOOT = 2000


def load_p_parquet(views_dir: Path, stem: str) -> tuple[list[dict], dict]:
    import pandas as pd
    f = pd.read_parquet(views_dir / f"{stem}.parquet")
    meta = json.loads((views_dir / f"{stem}.meta.json").read_text(encoding="utf-8"))
    rows = []
    for r in f.to_dict("records"):
        rows.append({"account": r["account"], "date": r["date"], "outcome": r["outcome"],
                     "score": None if (r["score"] is None or (isinstance(r["score"], float) and math.isnan(r["score"]))) else float(r["score"]),
                     "label": f"{meta['corpus_stem']}:{meta['view']}:{r['account']}/{r['date']}",
                     "packet_truncated": bool(r.get("packet_truncated"))})
    return rows, meta


def load_json(views_dir: Path, name: str) -> dict:
    return json.loads((views_dir / name).read_text(encoding="utf-8"))


def scored(rows: list[dict]) -> list[dict]:
    return [r for r in rows if r.get("outcome") == "scored" and r.get("score") is not None]


def unit_rule(rows: list[dict], view_key: str, rate: float) -> dict:
    s = [float(r["score"]) for r in scored(rows)]
    rule = th.randomised_threshold(s, rate, seed=TIE_SEED)
    rule["view"] = view_key
    rule["n_flagged_expected"] = round(th.expected_flag_rate(s, rule) * len(s), 3)
    rule["n_flagged_realised"] = sum(1 for r in scored(rows) if th.is_flagged(float(r["score"]), rule, r["label"]))
    det = th.randomised_threshold(s, rate, seed=TIE_SEED)      # deterministic reading: strictly above t, or at-or-above the next value
    # the "at most B" deterministic threshold: smallest t with share(score >= t) <= B
    vals = sorted(set(s))
    det_t = None
    for t in vals:
        if sum(1 for x in s if x >= t) / len(s) <= rate:
            det_t = t
            break
    rule["deterministic_threshold_at_or_above"] = det_t
    rule["deterministic_rate"] = (sum(1 for x in s if x >= det_t) / len(s)) if det_t is not None else 0.0
    return rule


def author_rule(rows: list[dict], account_days: Counter, view_key: str, rate: float) -> dict:
    """An author is flagged when any of their (author, document) units reaches the threshold;
    cost = flagged authors' active account-days over all active account-days."""
    amax: dict[str, float | None] = {a: None for a in account_days}
    for r in scored(rows):
        a = r["author"]
        amax[a] = max(amax.get(a) or -1.0, float(r["score"])) if amax.get(a) is not None else float(r["score"])
    weights = {a: float(n) for a, n in account_days.items()}
    rule = th.author_level_threshold(amax, weights, rate, seed=TIE_SEED)
    rule["view"] = view_key
    rule["n_authors_with_units"] = sum(1 for v in amax.values() if v is not None)
    rule["author_max_distribution"] = dict(sorted(Counter(v for v in amax.values() if v is not None).items()))
    flagged = [a for a, v in amax.items() if v is not None and th.is_flagged(v, rule, a)]
    rule["flagged_honest_authors"] = sorted(flagged)
    rule["realised_cost"] = round(sum(weights[a] for a in flagged) / sum(weights.values()), 4)
    rule["bootstrap"] = th.bootstrap_author_threshold(amax, weights, rate, seed=BOOT_SEED, n_boot=N_BOOT)
    return rule


def headroom(rows: list[dict]) -> dict:
    """Scores of the honest pairs whose window holds three or fewer one-line changes: what a lone
    three-statement author competes with (11.12(c))."""
    small = [r for r in scored(rows) if r.get("n_changes", 0) <= 3 and r.get("n_lines_changed", 0) <= r.get("n_changes", 0)]
    s = sorted(float(r["score"]) for r in small)
    return {"n_pairs": len(small), "scores": s, "max": s[-1] if s else None,
            "median": (s[len(s) // 2] if s else None), "histogram": dict(sorted(Counter(s).items()))}


def per_document(rows: list[dict], rule: dict) -> dict:
    out = {}
    by: dict[str, list[dict]] = defaultdict(list)
    for r in scored(rows):
        by[r["path"]].append(r)
    for p, rs in sorted(by.items()):
        s = [float(r["score"]) for r in rs]
        exp_rate = th.expected_flag_rate(s, rule)
        own = th.randomised_threshold(s, rule["rate"], seed=TIE_SEED)
        out[p] = {"n_units": len(s), "median": float(sorted(s)[len(s) // 2]), "max": max(s),
                  "expected_exceedance_under_pooled_rule": round(exp_rate, 4),
                  "realised_flagged_under_pooled_rule": sum(1 for r in rs if th.is_flagged(float(r["score"]), rule, r["label"])),
                  "own_quantile_threshold": own["threshold"], "own_p_tie": own["p_tie"],
                  "uninformative": exp_rate > UNINFORMATIVE_RATE}
    return out


def truncation_check(view_rows: list[dict], view: str, corpus_rows: list[dict]) -> dict:
    """D3 for the P views: for each truncated packet, whether the elided middle removed a class
    document edit of that account-day (the renderer's cap elides the middle of the block; we
    rebuild the packet and look for each class edit's text in it)."""
    import score_fork_corpus as sfc
    keys, day_idx, by_key = sfc.account_days(corpus_rows)
    render = sv.jc_mod.get_render_event()
    paths = set(sv.class_doc_paths())
    out = {"n_truncated": 0, "truncated_units": [], "class_edits_elided": 0}
    for r in view_rows:
        if not r.get("packet_truncated"):
            continue
        out["n_truncated"] += 1
        rows = by_key[(r["account"], r["date"])]
        pk, _ = sv.p_packet(view, render, r["account"], r["date"], rows)
        edits = [x for x in rows if sv.is_class_write(x, paths)]
        missing = 0
        for x in edits:
            a = x.get("args") or {}
            txt = a.get("text") if x["action"] == "append_to_file" else a.get("replace") if x["action"] == "replace_in_file" else None
            if txt and txt.strip()[:60] not in pk:
                missing += 1
        out["truncated_units"].append({"account": r["account"], "date": r["date"], "class_edits": len(edits), "elided": missing})
        out["class_edits_elided"] += missing
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--views-dir", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    V = Path(ns.views_dir)
    corpus_rows = sv.read_jsonl(Path(ns.corpus))
    import score_fork_corpus as sfc
    keys, _, _ = sfc.account_days(corpus_rows)
    account_days = Counter(a for a, _d in keys)
    n_ad = len(keys)

    seal: dict[str, Any] = {"version": "views-calibration/v1", "corpus": ns.corpus,
                            "corpus_sha256": sv.file_sha256(Path(ns.corpus)), "n_active_account_days": n_ad,
                            "shared_harm_version": sv.SHARED_HARM_VERSION, "shared_harm_sha256": sv.SHARED_HARM_SHA256,
                            "tie_seed": TIE_SEED, "bootstrap_seed": BOOT_SEED, "rates": RATES,
                            "uninformative_rate": UNINFORMATIVE_RATE, "views": {}}
    # P_own / P_ctx
    for stem, view in (("p_own", "P_own"), ("p_ctx", "P_ctx")):
        if not (V / f"{stem}.parquet").exists():
            seal["views"][view] = {"missing": True}
            continue
        rows, meta = load_p_parquet(V, stem)
        summ = sv.summarise(rows)
        trunc = truncation_check(rows, view, corpus_rows)
        defect = sv.defect_check(summ, packets_ok=trunc["class_edits_elided"] == 0)
        seal["views"][view] = {"prompt": sv.prompt_record(view), "n_units": len(rows), "summary": summ,
                               "truncation": trunc, "defect_check": defect,
                               "rule": unit_rule(rows, view, RATES[view]), "dollars": meta.get("dollars_total")}
    # P_author (pair units, two contexts) and the author-day robustness units
    for name, view, ctx in (("p_author_c0.json", "P_author", 0), ("p_author_c3.json", "P_author", 3)):
        if not (V / name).exists():
            seal["views"][sv.view_key(view, ctx)] = {"missing": True}
            continue
        d = load_json(V, name)
        rows = d["rows"]
        summ = sv.summarise(rows)
        k = sv.view_key(view, ctx)
        rec = {"prompt": sv.prompt_record(view, ctx), "n_units": len(rows), "summary": summ,
               "defect_check": sv.defect_check(summ, packets_ok=d["meta"]["estimate"]["n_truncated"] == 0),
               "unit_rule": unit_rule(rows, k, RATES[k]),
               "author_rule": author_rule(rows, account_days, k, RATES[k]),
               "headroom_three_or_fewer_one_line_changes": headroom(rows),
               "dollars": summ.get("dollars_total")}
        seal["views"][k] = rec
    if (V / "p_author_c0_authorday.json").exists():
        d = load_json(V, "p_author_c0_authorday.json")
        rows = d["rows"]
        summ = sv.summarise(rows)
        seal["views"]["P_author_authorday"] = {"n_units": len(rows), "summary": summ,
                                               "unit_rule": unit_rule(rows, "P_author", RATES["P_author"]),
                                               "author_rule": author_rule(rows, account_days, "P_author", RATES["P_author"]),
                                               "dollars": summ.get("dollars_total")}
    # O_diff cumulative and O_whole
    for name, view in (("o_diff_cumulative.json", "O_diff"), ("o_whole_eachwrite.json", "O_whole")):
        if not (V / name).exists():
            seal["views"][view] = {"missing": True}
            continue
        d = load_json(V, name)
        rows = d["rows"]
        summ = sv.summarise(rows)
        rule = unit_rule(rows, view, RATES[view])
        rec = {"prompt": sv.prompt_record(view), "n_units": len(rows), "summary": summ,
               "defect_check": sv.defect_check(summ, packets_ok=d["meta"]["estimate"]["n_truncated"] == 0),
               "rule": rule, "per_document": per_document(rows, rule), "dollars": summ.get("dollars_total")}
        if view == "O_diff":
            spans = Counter(r.get("span_days") for r in scored(rows))
            rec["units_by_span_days"] = dict(sorted((str(k), v) for k, v in spans.items()))
            rec["units_by_boundary"] = dict(sorted(Counter(r.get("boundary") for r in scored(rows)).items()))
            rec["uninformative_documents"] = sorted(p for p, v in rec["per_document"].items() if v["uninformative"])
        seal["views"][view] = rec
    seal["dollars_total"] = round(sum(float(v.get("dollars") or 0) for v in seal["views"].values()), 4)
    Path(ns.out).write_text(json.dumps(seal, indent=1, default=str), encoding="utf-8")
    # a short Markdown table
    lines = ["| view | units | refused/errored | median | p90 | p95 | max | distinct > median | top share | t | p_tie | expected rate | deterministic (>=) | defect |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in seal["views"].items():
        if v.get("missing"):
            lines.append(f"| {k} | missing | | | | | | | | | | | | |")
            continue
        s = v["summary"]
        rule = v.get("rule") or v.get("unit_rule")
        dc = v.get("defect_check") or {}
        lines.append(f"| {k} | {v['n_units']} | {s.get('refused_or_errored_share')} | {s.get('median')} | {s.get('p90')} | {s.get('p95')} | {s.get('max')} | "
                     f"{s.get('distinct_above_median')} | {s.get('top_share')} | {rule['threshold']} | {round(rule['p_tie'], 4)} | {rule['expected_rate']} | "
                     f"{rule.get('deterministic_threshold_at_or_above')} ({round(rule.get('deterministic_rate', 0), 3)}) | {'DEFECT' if dc.get('any_defect') else 'none'} |")
    for k in ("P_author", "P_author_ctx", "P_author_authorday"):
        v = seal["views"].get(k) or {}
        ar = v.get("author_rule")
        if ar:
            lines.append(f"\n**{k} author level:** t = {ar['threshold']}, p_tie = {round(ar['p_tie'], 4)}, expected cost {ar['expected_cost']}, "
                         f"realised cost {ar['realised_cost']} (flagged honest authors {len(ar['flagged_honest_authors'])}); deterministic t = {ar['deterministic_threshold']} "
                         f"(cost {ar['deterministic_cost']}); bootstrap 95% {ar['bootstrap']['ci95']} (median {ar['bootstrap']['median']}, {N_BOOT} replicates); "
                         f"author-max distribution {ar['author_max_distribution']}.")
            h = v.get("headroom_three_or_fewer_one_line_changes")
            if h:
                lines.append(f"Headroom (pairs with <= 3 one-line changes, n = {h['n_pairs']}): max {h['max']}, median {h['median']}, histogram {h['histogram']}.")
    od = seal["views"].get("O_diff") or {}
    if od.get("per_document"):
        lines.append("\n| document | O_diff units | median | max | expected exceedance (pooled rule) | own q threshold | class |")
        lines.append("|---|---|---|---|---|---|---|")
        for p, v in od["per_document"].items():
            lines.append(f"| {p} | {v['n_units']} | {v['median']} | {v['max']} | {v['expected_exceedance_under_pooled_rule']} | {v['own_quantile_threshold']} (p_tie {round(v['own_p_tie'], 3)}) | {'uninformative' if v['uninformative'] else 'not uninformative (pending T1)'} |")
    Path(ns.out).with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
