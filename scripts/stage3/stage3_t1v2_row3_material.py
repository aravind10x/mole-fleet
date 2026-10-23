#!/usr/bin/env python3
"""Brief 07h H5: the $0 material for row 3's consequence (proposal section 5 / plan section 3), read
from t1v2-results.json and the T1 v2 judge caches (blue's own synthetic placeholders) and the
sealed O_diff honest calibration output. Mechanical sub-conditions of row 3: do the misses sit on
judge-limited documents; are at least two documents informative. Exploratory (post hoc, labelled,
no threshold changed): the conforming O_diff recall against every candidate threshold beside the
honest exceedance at that threshold, from the step-1 honest O_diff scores.

    .venv/bin/python -I work/checks/stage3_t1v2_row3_material.py --results work/stage3/t1v2/t1v2-results.json \\
        --cache work/stage3/t1v2/judge-cache.t1v2.O_diff.anthropic-claude-sonnet-5.jsonl \\
        --honest-odiff work/stage3/views/o_diff_cumulative.json --payloads work/stage3/t1v2/payloads-v2.json --out work/stage3/t1v2/row3-material
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--honest-odiff", required=True)
    ap.add_argument("--payloads", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    res = json.loads(Path(ns.results).read_text())
    pay = {p["id"]: p for p in json.loads(Path(ns.payloads).read_text())["payloads"]}
    conf = res["regimes"]["conforming"]
    classes = conf["O_diff"]["document_classes"]
    rows = conf["O_diff"]["rows"]
    t = conf["O_diff"]["rule"]["threshold"]
    misses = [x for x in rows if not x["flagged"]]
    by_doc = Counter(x["document"] for x in misses)
    on_jl = sum(1 for x in misses if classes[x["document"]]["class"].startswith("judge-limited"))
    informative = [d for d, c in classes.items() if c["class"].startswith("informative")]
    out = {"threshold": t, "n_composed": len(rows), "n_flagged": len(rows) - len(misses), "n_missed": len(misses),
           "misses_by_document": dict(by_doc), "misses_on_judge_limited_documents": on_jl,
           "misses_on_informative_documents": len(misses) - on_jl, "informative_documents": informative,
           "at_least_two_informative": len(informative) >= 2,
           "every_miss_on_a_judge_limited_document": on_jl == len(misses),
           "miss_scores": sorted(x["score"] for x in misses),
           "miss_score_bands": dict(Counter("<=30" if x["score"] <= 30 else "31-60" if x["score"] <= 60 else "61-77" if x["score"] < t else ">=t" for x in misses)),
           "flagged_scores": sorted(x["score"] for x in rows if x["flagged"]),
           "by_harm_family_hint": {}, "misses_by_kind": dict(Counter(pay[x["payload_id"]]["kind"] for x in misses)),
           "misses_by_arm": dict(Counter(x["arm"] for x in misses))}
    # per payload: which arms were caught (composition dose does not vary with the split)
    per_pay = defaultdict(dict)
    for x in rows:
        per_pay[x["payload_id"]][x["arm"]] = (x["score"], x["flagged"])
    out["per_payload"] = {k: v for k, v in sorted(per_pay.items())}
    out["payloads_never_flagged"] = sorted(k for k, v in per_pay.items() if not any(f for _s, f in v.values()))
    out["payloads_flagged_in_every_arm"] = sorted(k for k, v in per_pay.items() if all(f for _s, f in v.values()))
    # rationales of the misses (blue's own placeholders): the cache records keyed by label
    cache = {}
    for line in Path(ns.cache).read_text().splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        cache[r.get("label")] = r
    sample_keys = [k for k in list(cache)[:1]]
    out["cache_record_keys"] = sorted(cache[sample_keys[0]].keys()) if sample_keys else []
    rats = []
    for x in misses:
        lab = next((k for k in cache if k and x["payload_id"] + "-" + x["arm"] + ":O_diff" in k), None)
        r = cache.get(lab) or {}
        txt = r.get("rationale") or r.get("reason") or r.get("raw") or r.get("text") or ""
        rats.append({"payload_id": x["payload_id"], "arm": x["arm"], "document": x["document"].split("/")[-1], "score": x["score"],
                     "kind": pay[x["payload_id"]]["kind"], "rationale": str(txt)[:400]})
    out["miss_rationales"] = rats
    # exploratory: conforming recall against every candidate t, with the honest exceedance at t
    hon = json.loads(Path(ns.honest_odiff).read_text())
    hs = sorted(float(r["score"]) for r in hon["rows"] if r.get("outcome") == "scored" and r.get("score") is not None)
    cs = sorted(float(x["score"]) for x in rows)
    alarm = sorted(float(x["score"]) for x in res["regimes"]["alarming"]["O_diff"]["rows"])
    sham = sorted(float(x["score"]) for x in res["regimes"]["sham"]["O_diff"]["rows"])
    curve = []
    for cand in sorted(set(hs) | set(cs)):
        curve.append({"t": cand, "honest_exceedance_at_or_above": round(sum(1 for s in hs if s >= cand) / len(hs), 4),
                      "conforming_recall": round(sum(1 for s in cs if s >= cand) / len(cs), 4),
                      "alarming_recall": round(sum(1 for s in alarm if s >= cand) / len(alarm), 4),
                      "sham_rate": round(sum(1 for s in sham if s >= cand) / len(sham), 4)})
    out["exploratory_curve"] = curve
    out["conforming_score_quantiles"] = {q: cs[int(q * (len(cs) - 1))] for q in (0.1, 0.25, 0.5, 0.75, 0.9)}
    out["honest_score_quantiles"] = {q: hs[int(q * (len(hs) - 1))] for q in (0.5, 0.75, 0.9, 0.95)}
    Path(ns.out + ".json").write_text(json.dumps(out, indent=1))
    L = [f"# Row 3 material (brief 07h; $0; `stage3_t1v2_row3_material.py`)\n",
         f"Conforming O_diff at the sealed pooled rule (t = {t}): {out['n_flagged']} of {out['n_composed']} flagged, {out['n_missed']} missed. "
         f"Misses on judge-limited documents: {on_jl} of {len(misses)} (on informative documents: {len(misses) - on_jl}; {dict(by_doc)}). "
         f"Informative documents: {informative} (at least two: {out['at_least_two_informative']}). Every miss on a judge-limited document: {out['every_miss_on_a_judge_limited_document']}.\n",
         f"Miss scores by band: {out['miss_score_bands']}; misses by kind {out['misses_by_kind']}; by arm {out['misses_by_arm']}. "
         f"Payloads never flagged in any arm: {len(out['payloads_never_flagged'])} of {len(per_pay)}; flagged in every arm: {len(out['payloads_flagged_in_every_arm'])}.\n",
         "| t | honest exceedance (at or above) | conforming recall | alarming recall | sham rate |", "|---|---|---|---|---|"]
    for c in curve:
        if c["t"] in (50, 55, 60, 62, 65, 68, 70, 72, 75, 78, 82, 85, 88, 92) or c["t"] == t:
            L.append(f"| {c['t']} | {c['honest_exceedance_at_or_above']} | {c['conforming_recall']} | {c['alarming_recall']} | {c['sham_rate']} |")
    L.append("\nExploratory and post hoc: no threshold is changed; the sealed rule stands. The curve says what a different honest cost would buy on these placeholders.\n")
    L.append("## Miss rationales (blue's synthetic placeholders; the judge's words, first 400 characters)\n")
    for r in rats:
        L.append(f"- **{r['payload_id']} {r['arm']}** ({r['document']}, {r['kind']}, score {r['score']}): {r['rationale']}")
    Path(ns.out + ".md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
