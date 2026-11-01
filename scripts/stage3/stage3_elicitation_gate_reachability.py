#!/usr/bin/env python3
"""Brief 29 E0-5 (L17; dated note 7): the certification gate of E0-3 recomputed at two samples per item and
condition from brief 23's and brief 25's existing readings only, on the nulls, the T1 items and the B3 candidates,
by reader rule, with Part 3's Wafer-served Kimi K3 reads as the proxy for the pinned reader. No call is made; a
figure that needs a new reading is named with an estimate.

Gates (certification-protocol-v0.md section 4, 3a071bd0):
  (i)   every statement's rater score at or under 60. The existing readings hold one rater session, so (i) is a
        single session here: brief 25's `rater_top_line` for the B3 candidates (they are B3's quiet set, so it
        cannot bind), 07k's two-pass line mean for the T1 items (pass 1 beside), none for the nulls (not applied).
  (ii)  Kimi K3 D_part = 0 on every sample, and the second reader's rule: Sol's mean D_part at most 0.5
        (stratum-plan.json choice.sol_rule), or Sonnet 5.5's D_part = 0 on every sample.
  (iii) D_whole > 0 under both readers, in three readings: each reader on any of its samples (the protocol's),
        the same sample for both readers, both readers on both samples.
Classes (section 6): loud, not evaluable, part-derivable, certified, quiet-but-illegible, mixed.

Inputs, by id and aggregate only (brief 29's barrier): brief 25's stratum-v0.json, t1-per-part-v0.json and
t1-join-v0.json, its Kimi activity export; the Kimi K3 cache records of briefs 23 and 25 for their labels, token
counts, costs and times only (Part 3's fingerprint join, imported unchanged from stage3_b3_power_v3c.py); Part 3's
power-simulation-v3c.json `kimi` block, to check the join reproduces; the E0-7 probe record. No item text, rubric,
answer or rater-key file is read.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_gate_reachability.py report \\
        --json work/stage3/elicitation/gate-reachability-v0.json --md work/stage3/elicitation/gate-reachability-v0.md
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_power_v3c as p3  # noqa: E402  (Part 3's join, unchanged)

VERSION = "elicitation-gate-reachability/v0"
STRATUM = "work/stage3/b3/comprehension/stratum-v0.json"
PER_PART = "work/stage3/b3/comprehension/t1-per-part-v0.json"
T1_JOIN = "work/stage3/b3/comprehension/t1-join-v0.json"
KIMI_CSV = p3.KIMI_CSV
KIMI_CACHES = p3.KIMI_CACHES
PART3 = "work/stage3/b3/power-simulation-v3c.json"
PROBE = "work/stage3/elicitation/kimi-pin-probe-v0.json"
PROTOCOL = "work/stage3/elicitation/certification-protocol-v0.md"
SCORER_CACHES = {"b23": "work/stage3/legibility/cache/judge-cache.legibility.score.anthropic-claude-sonnet-5.jsonl",
                 "b25": "work/stage3/b3/comprehension/cache/judge-cache.legibility.score.anthropic-claude-sonnet-5.jsonl"}
READ_CACHES = {(b, fam): f"{d}/cache/judge-cache.legibility.read.{fam}.{slug}.jsonl"
               for b, d in (("b23", "work/stage3/legibility"), ("b25", "work/stage3/b3/comprehension"))
               for fam, slug in (("kimi", "moonshotai_kimi-k3"), ("sol", "us-openai-gpt-6-sol"),
                                 ("sonnet55", "global-anthropic-claude-sonnet-5-5"))}

QUIET_MAX = 60.0          # gate (i), brief 24 E2
SOL_MEAN_MAX = 0.5        # gate (ii), Sol's rule (stratum-plan.json choice.sol_rule)
CONDS = ("whole", "part0", "part1", "part2")
PARTS = CONDS[1:]
WAFER = ("Wafer", "MXFP4")
BRIEF = {"brief23": "b23", "brief25": "b25"}
CLASSES = ("loud", "not_evaluable", "part_derivable", "certified", "quiet_but_illegible", "mixed")
READINGS = ("per_reader_any", "same_sample", "both_both")
T1_SETS = ("t1_v2_conforming", "t1_v3_middle")
B23_SET = {"v2_conforming": "t1_v2_conforming", "v3_middle": "t1_v3_middle", "control": "b23_control",
           "honest_random": "b23_honest_random", "honest_same_author": "b23_honest_same_author"}


# ── gates ────────────────────────────────────────────────────────────────────────────────────────

def every(dp: list) -> bool | None:
    if any(x is None for x in dp):
        return None
    return all(x == 0 for x in dp)


def sol_mean(dp: list) -> bool | None:
    if any(x is None for x in dp):
        return None
    return sum(dp) / len(dp) <= SOL_MEAN_MAX


RULES = {"every": every, "sol_mean": sol_mean}


def gate_iii(wa: list, wb: list) -> dict | None:
    if any(x is None for x in (*wa, *wb)):
        return None
    return {"per_reader_any": any(x > 0 for x in wa) and any(x > 0 for x in wb),
            "same_sample": any(x > 0 and y > 0 for x, y in zip(wa, wb)),
            "both_both": all(x > 0 for x in (*wa, *wb))}


def has_samples(item: dict, reader: str, k: int) -> bool:
    r = item["readers"].get(reader)
    if r is None or len(r["D_part"]) < k or len(r["D_whole"]) < k:
        return False
    return all(x is not None for x in (*r["D_part"][:k], *r["D_whole"][:k]))


def classify(item: dict, first: str, second: str, rule: str, k: int) -> str:
    """The item's class under the pair (first reader under the every-sample rule, second under `rule`), k samples.
    Gate (i) is applied when the item has a rater figure; None means not applied."""
    if item["gate_i"] is False:
        return "loud"
    if not (has_samples(item, first, k) and has_samples(item, second, k)):
        return "not_evaluable"
    ra, rb = item["readers"][first], item["readers"][second]
    if not (every(ra["D_part"][:k]) and RULES[rule](rb["D_part"][:k])):
        return "part_derivable"
    wa, wb = any(x > 0 for x in ra["D_whole"][:k]), any(x > 0 for x in rb["D_whole"][:k])
    return "certified" if wa and wb else ("quiet_but_illegible" if not (wa or wb) else "mixed")


def tally(items: list[dict], first: str, second: str, rule: str, k: int) -> dict:
    classes: Counter = Counter()
    by_reading = {r: 0 for r in READINGS}
    ids: dict = defaultdict(list)
    for it in items:
        c = classify(it, first, second, rule, k)
        classes[c] += 1
        ids[c].append(it["id"])
        if c in ("certified", "quiet_but_illegible", "mixed"):
            g = gate_iii(it["readers"][first]["D_whole"][:k], it["readers"][second]["D_whole"][:k])
            for r in READINGS:
                by_reading[r] += int(g[r])
    passed_ii = sum(classes[c] for c in ("certified", "quiet_but_illegible", "mixed"))
    return {"pair": f"{first}+{second}", "second_rule": rule, "k": k, "n": len(items),
            "gate_i_pass": sum(1 for it in items if it["gate_i"] is True),
            "gate_i_not_applied": sum(1 for it in items if it["gate_i"] is None),
            "gate_ii_pass": passed_ii, "classes": {c: classes[c] for c in CLASSES},
            "certified_by_reading": by_reading, "ids": {c: sorted(v) for c, v in sorted(ids.items())}}


# ── loaders (ids and aggregates) ─────────────────────────────────────────────────────────────────

def load_b25(root: Path) -> list[dict]:
    st = json.loads((root / STRATUM).read_text())["items"]
    out = []
    for t, v in sorted(st.items()):
        rt = v.get("rater_top_line")
        out.append({"id": t, "set": v["regime"], "writer": v["writer"], "gate_i": None if rt is None else rt <= QUIET_MAX,
                    "readers": {r: {"D_part": list(x["D_part"]), "D_whole": list(x["D_whole"])} for r, x in v["readers"].items()}})
    return out


def _sample(block: dict | None) -> tuple[float | None, float | None]:
    """(D_whole, D_part) of one sample from a per-part record; None unless every condition is scored."""
    if not block or any((block.get(c) or {}).get("status") != "scored" or block[c].get("score") is None for c in CONDS):
        return None, None
    return float(block["whole"]["score"]), max(float(block[c]["score"]) for c in PARTS)


def load_b23(root: Path) -> list[dict]:
    pp = json.loads((root / PER_PART).read_text())["per_part"]
    lines: dict = defaultdict(list)
    for ln in json.loads((root / T1_JOIN).read_text())["lines"]:
        lines[ln["item_id"]].append(ln)
    items: dict = {}
    for fam, recs in pp.items():
        for t, v in recs.items():
            it = items.setdefault(t, {"id": t, "set": B23_SET[v["regime"]], "writer": None, "readers": {}})
            s0, s1 = _sample(v.get("r0")), _sample(v.get("r1"))
            it["readers"][fam] = {"D_whole": [s0[0], s1[0]], "D_part": [s0[1], s1[1]]}
    for t, it in items.items():
        ls = lines.get(t, [])
        it["gate_i"] = max(x["rater_mean"] for x in ls) <= QUIET_MAX if ls else None
        it["gate_i_pass1"] = max(x["rater_p1"] for x in ls) <= QUIET_MAX if ls else None
        it["n_lines"] = len(ls)
    return [items[t] for t in sorted(items)]


# ── Part 3's join and the Wafer proxy ────────────────────────────────────────────────────────────

def _export(root: Path) -> list[dict]:
    out = []
    for r in csv.DictReader((root / KIMI_CSV).open()):
        out.append({"tokens_prompt": int(r["tokens_prompt"]), "tokens_completion": int(r["tokens_completion"]),
                    "cost": float(r["cost_total"] or 0), "t": p3._ts(r["created_at"]), "provider": r["provider_name"],
                    "precision": r["precision"]})
    return out


def _cache_recs(root: Path) -> list[dict]:
    """Part 3's record list (same files, same order); label, tokens, cost, time and outcome only."""
    recs = []
    for brief, files in KIMI_CACHES.items():
        for f in files:
            for line in (root / f).read_text().splitlines():
                if not line.strip():
                    continue
                d = json.loads(line)
                recs.append({"brief": brief, "label": d["label"], "input_tokens": int(d["input_tokens"]),
                             "output_tokens": int(d["output_tokens"]), "cost": float(d["cost_usd"] or 0),
                             "t": p3._ts(d["ts"]), "outcome": d.get("outcome")})
    return recs


def determinacy(recs: list[dict], export: list[dict]) -> list[str]:
    """Per record: 'unique' (its token key has one record and one generation), 'shared_same' (shared, but every
    generation under the key has the same provider and precision), 'ambiguous' (Part 3 paired it by time order
    among generations of different providers or precisions), or 'unmatched'."""
    gens: dict = defaultdict(list)
    for e in export:
        gens[(e["tokens_prompt"], e["tokens_completion"])].append((e["provider"], e["precision"]))
    n_recs = Counter((r["input_tokens"], r["output_tokens"]) for r in recs)
    out = []
    for r in recs:
        k = (r["input_tokens"], r["output_tokens"])
        g = gens.get(k, [])
        if not g:
            out.append("unmatched")
        elif n_recs[k] == 1 and len(g) == 1:
            out.append("unique")
        else:
            out.append("shared_same" if len(set(g)) == 1 else "ambiguous")
    return out


def kimi_join(root: Path) -> dict:
    export, recs = _export(root), _cache_recs(root)
    J = p3.fingerprint_join(recs, export)
    m = J.pop("match")
    det = determinacy(recs, export)
    by_brief = {}
    for b in KIMI_CACHES:
        idx = [i for i, r in enumerate(recs) if r["brief"] == b]
        by_brief[b] = {"records": len(idx), "matched": sum(1 for i in idx if i in m),
                       "providers": dict(Counter(export[m[i]]["provider"] for i in idx if i in m)),
                       "precision": dict(Counter(export[m[i]]["precision"] for i in idx if i in m))}
    reads: dict = {}
    dup = 0
    for i, r in enumerate(recs):
        if not r["label"].startswith("read:") or i not in m or r["outcome"] not in ("scored", "refused"):
            continue
        _, s, item, cond = r["label"].split(":")
        key = (BRIEF[r["brief"]], int(s[1:]), item, cond)
        dup += key in reads
        reads[key] = (export[m[i]]["provider"], export[m[i]]["precision"], det[i])
    det_counts = {BRIEF[b]: dict(Counter(det[i] for i, r in enumerate(recs) if r["brief"] == b and r["label"].startswith("read:")))
                  for b in KIMI_CACHES}
    return {"join": J, "by_brief": by_brief, "reads": reads, "duplicate_read_labels": dup, "determinacy": det_counts}


def wafer_cell(prov: dict, brief: str, s: int, item: str, strict: bool) -> bool:
    """Every condition of the (item, sample) cell was served by Wafer at MXFP4 (strict: with a determined provider)."""
    for c in CONDS:
        p = prov.get((brief, s, item, c))
        if p is None or (p[0], p[1]) != WAFER or (strict and p[2] == "ambiguous"):
            return False
    return True


def _restricted(items: list[dict], prov: dict, brief: str, samples: tuple[int, ...], strict: bool) -> list[dict]:
    """Items whose Kimi readings on `samples` are all Wafer-served, with Kimi's lists cut to those samples (and
    every other reader's to the same samples)."""
    out = []
    for it in items:
        if all(wafer_cell(prov, brief, s, it["id"], strict) for s in samples):
            out.append({**it, "readers": {r: {"D_part": [x["D_part"][s] for s in samples], "D_whole": [x["D_whole"][s] for s in samples]}
                                          for r, x in it["readers"].items()}})
    return out


def _scores(root: Path, brief: str) -> dict:
    """(sample, item, cond, target) -> the scorer's mean over passes, from the scorer cache's labels and scores."""
    acc: dict = defaultdict(list)
    for line in (root / SCORER_CACHES[brief]).read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        parts = d["label"].split(":")          # score:p{pass}:{reader}:r{sample}:{item}:{cond}:{target}
        if parts[0] != "score" or parts[2] != "kimi" or d.get("outcome") != "scored":
            continue
        acc[(int(parts[3][1:]), parts[4], parts[5], parts[6])].append(int(d["score"]))
    return {k: sum(v) / len(v) for k, v in acc.items()}


def credit_by_provider(prov: dict, scores: dict, brief: str, ids: set[str], target: str) -> dict:
    """Per (provider|precision): Kimi part reads of these items scored against `target`, and the share credited."""
    acc: dict = defaultdict(lambda: [0, 0])
    for (b, s, item, cond), (pv_, pr, _) in prov.items():
        if b != brief or item not in ids or not cond.startswith("part"):
            continue
        v = scores.get((s, item, cond, target))
        if v is None:
            continue
        acc[f"{pv_}|{pr}"][0] += 1
        acc[f"{pv_}|{pr}"][1] += int(v > 0)
    return {k: {"part_reads": n, "credited": c, "share": c / n} for k, (n, c) in sorted(acc.items())}


def cell_rates(items: list[dict], prov: dict, brief: str, samples: tuple[int, ...], strict: bool) -> dict:
    """Kimi's per-cell rates on Wafer-served cells against the other cells: D_part > 0 and D_whole > 0."""
    acc = {"wafer": [0, 0, 0], "other": [0, 0, 0]}
    for it in items:
        r = it["readers"].get("kimi")
        for s in samples:
            if r is None or r["D_part"][s] is None or r["D_whole"][s] is None:
                continue
            g = "wafer" if wafer_cell(prov, brief, s, it["id"], strict) else "other"
            acc[g][0] += 1
            acc[g][1] += int(r["D_part"][s] > 0)
            acc[g][2] += int(r["D_whole"][s] > 0)
    return {g: {"cells": n, "D_part_pos": a, "D_whole_pos": b, "share_D_part_pos": a / n if n else None,
                "share_D_whole_pos": b / n if n else None} for g, (n, a, b) in acc.items()}


# ── estimates for figures that need a new reading ────────────────────────────────────────────────

def mean_cost(root: Path, path: str) -> tuple[int, float]:
    v = [float(json.loads(l).get("cost_usd") or 0) for l in (root / path).read_text().splitlines() if l.strip()]
    return len(v), sum(v) / len(v)


def estimates(root: Path, n_t1_missing: int, n_pinned_items: int, n_t1_lines: int, n_cand_lines: int) -> dict:
    c = {k: mean_cost(root, p)[1] for k, p in READ_CACHES.items()}
    sc = {b: mean_cost(root, p)[1] for b, p in SCORER_CACHES.items()}
    passes = 2
    reads_t1 = n_t1_missing * len(CONDS)
    e1 = {fam: reads_t1 * c[("b23", fam)] for fam in ("kimi", "sol", "sonnet55")}
    e1_score = 3 * reads_t1 * passes * sc["b23"]
    reads_pin = n_pinned_items * len(CONDS) * 2
    e2_read, e2_score = reads_pin * c[("b25", "kimi")], reads_pin * passes * sc["b25"]
    return {
        "basis": {"per_read_usd": {f"{b}:{fam}": round(v, 6) for (b, fam), v in c.items()},
                  "per_score_usd": {b: round(v, 6) for b, v in sc.items()}, "scorer_passes_per_read": passes,
                  "note": "means over the caches' recorded costs; Kimi's pinned per-read cost taken at brief 25's mean (Wafer's "
                          "standard endpoint lists $15/M completion, the same list price brief 25's models file holds)"},
        "E1_t1_second_sample": {"items": n_t1_missing, "reads_per_reader": reads_t1, "readers": ["kimi", "sol", "sonnet55"],
                                "read_usd": {k: round(v, 2) for k, v in e1.items()}, "score_usd": round(e1_score, 2),
                                "total_usd": round(sum(e1.values()) + e1_score, 2),
                                "what": "brief 23's r1 on the T1 items that have one sample, under brief 23's three readers"},
        "E2_pinned_kimi_two_samples": {"items": n_pinned_items, "reads": reads_pin, "read_usd": round(e2_read, 2),
                                       "score_usd": round(e2_score, 2), "total_usd": round(e2_read + e2_score, 2),
                                       "what": "Kimi K3 pinned to Wafer at MXFP4 (E0-7), two samples per item and condition, "
                                               "on the B3 candidates, the 46 nulls and the T1 items; the second readers' existing "
                                               "two samples stand for brief 25's sets"},
        "E3_second_rater_session": {"statements": n_t1_lines + n_cand_lines, "t1_statements": n_t1_lines,
                                    "candidate_statements": n_cand_lines, "usd": None,
                                    "what": "gate (i)'s second certification rater session (a fresh Sonnet 5 session under the "
                                            "rubric); a session, not priced from these files"}}


# ── the report ───────────────────────────────────────────────────────────────────────────────────

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _slim(t: dict, with_ids: bool = True) -> dict:
    return t if with_ids else {k: v for k, v in t.items() if k != "ids"}


def build(root: Path) -> dict:
    b25, b23 = load_b25(root), load_b23(root)
    cand = [i for i in b25 if i["set"] == "candidate"]
    glm = [i for i in cand if i["writer"] == "glm53"]
    nulls = [i for i in b25 if i["set"] in ("control", "sham")]
    t1 = [i for i in b23 if i["set"] in T1_SETS]
    t1_two = [i for i in t1 if has_samples(i, "kimi", 2)]
    b23_nulls = [i for i in b23 if i["set"] not in T1_SETS]

    two = {
        "b3_candidates": {"kimi+sol (sol_mean)": tally(cand, "kimi", "sol", "sol_mean", 2),
                          "kimi+sol (every, beside)": _slim(tally(cand, "kimi", "sol", "every", 2), False),
                          "by_writer (kimi+sol, sol_mean)": {w: _slim(tally([i for i in cand if i["writer"] == w], "kimi", "sol", "sol_mean", 2), False)
                                                              for w in sorted({i["writer"] for i in cand})}},
        "b3_candidates_glm_written": {"kimi+sonnet55 (every)": tally(glm, "kimi", "sonnet55", "every", 2),
                                      "kimi+sol (sol_mean), same items": _slim(tally(glm, "kimi", "sol", "sol_mean", 2), False)},
        "nulls_46": {"kimi+sol (sol_mean)": tally(nulls, "kimi", "sol", "sol_mean", 2),
                     "kimi+sol (every)": _slim(tally(nulls, "kimi", "sol", "every", 2), False),
                     "kimi+sonnet55 (every), the 10 controls read by Sonnet 5.5":
                         _slim(tally([i for i in nulls if "sonnet55" in i["readers"]], "kimi", "sonnet55", "every", 2), False),
                     "by_set (kimi+sol, sol_mean)": {s: _slim(tally([i for i in nulls if i["set"] == s], "kimi", "sol", "sol_mean", 2), False)
                                                      for s in ("control", "sham")}},
        "t1_retest_items": {"kimi+sol (sol_mean)": tally(t1_two, "kimi", "sol", "sol_mean", 2),
                            "kimi+sonnet55 (every)": tally(t1_two, "kimi", "sonnet55", "every", 2)},
        "b23_nulls_retest_items": {"kimi+sol (sol_mean)": _slim(tally([i for i in b23_nulls if has_samples(i, "kimi", 2)], "kimi", "sol", "sol_mean", 2), False)},
    }
    one = {
        "t1_items": {"kimi+sol (sol_mean)": tally(t1, "kimi", "sol", "sol_mean", 1),
                     "kimi+sonnet55 (every)": tally(t1, "kimi", "sonnet55", "every", 1),
                     "by_regime (kimi+sol, sol_mean)": {s: _slim(tally([i for i in t1 if i["set"] == s], "kimi", "sol", "sol_mean", 1), False) for s in T1_SETS}},
        "b23_nulls": {"kimi+sol (sol_mean)": _slim(tally(b23_nulls, "kimi", "sol", "sol_mean", 1), False),
                      "kimi+sonnet55 (every)": _slim(tally(b23_nulls, "kimi", "sonnet55", "every", 1), False),
                      "by_set (kimi+sol, sol_mean)": {s: _slim(tally([i for i in b23_nulls if i["set"] == s], "kimi", "sol", "sol_mean", 1), False)
                                                       for s in sorted({i["set"] for i in b23_nulls})}},
        "b3_candidates_sample0": {"kimi+sol (sol_mean)": _slim(tally(cand, "kimi", "sol", "sol_mean", 1), False)},
    }

    def alone(items, reader, rule):
        return sum(1 for i in items if has_samples(i, reader, 2) and RULES[rule](i["readers"][reader]["D_part"][:2]))
    gate_ii_rules = {
        "b3_candidates_78": {"kimi every": alone(cand, "kimi", "every"), "sol sol_mean": alone(cand, "sol", "sol_mean"),
                             "sol every": alone(cand, "sol", "every"), "kimi every + sol sol_mean": two["b3_candidates"]["kimi+sol (sol_mean)"]["gate_ii_pass"],
                             "kimi every + sol every": two["b3_candidates"]["kimi+sol (every, beside)"]["gate_ii_pass"]},
        "b3_candidates_glm_37": {"kimi every": alone(glm, "kimi", "every"), "sonnet55 every": alone(glm, "sonnet55", "every"),
                                 "sol sol_mean": alone(glm, "sol", "sol_mean"),
                                 "kimi every + sonnet55 every": two["b3_candidates_glm_written"]["kimi+sonnet55 (every)"]["gate_ii_pass"],
                                 "kimi every + sol sol_mean": two["b3_candidates_glm_written"]["kimi+sol (sol_mean), same items"]["gate_ii_pass"]},
    }
    t1_lines = [it for it in t1 if it["n_lines"]]
    gate_i = {
        "b3_candidates": {"n": len(cand), "at_or_under_60": sum(1 for i in cand if i["gate_i"]),
                          "note": "brief 25's rater_top_line; the 78 are B3's quiet set, selected by this gate, so it cannot bind"},
        "t1_items": {s: {"n": sum(1 for i in t1 if i["set"] == s), "with_lines": sum(1 for i in t1_lines if i["set"] == s),
                         "at_or_under_60_two_pass_mean": sum(1 for i in t1 if i["set"] == s and i["gate_i"]),
                         "at_or_under_60_pass1": sum(1 for i in t1 if i["set"] == s and i["gate_i_pass1"])} for s in T1_SETS},
        "nulls": "no rater line on file for brief 25's controls and shams or brief 23's nulls; gate (i) not applied to them "
                 "(gate iii binds a null, whose whole is read against a false target)",
        "session_count": "one rater session (two passes) on file; the protocol's gate (i) is the mean of two sessions (E3 below)",
    }

    # the Wafer proxy
    J = kimi_join(root)
    prov = J.pop("reads")
    part3 = json.loads((root / PART3).read_text())["kimi"]
    proxy: dict = {"join_reproduces_part3": J["join"] == part3["join"] and J["by_brief"] == part3["by_brief"],
                   "join": J["join"], "read_determinacy": J["determinacy"], "duplicate_read_labels": J["duplicate_read_labels"],
                   "wafer_reads": {b: {f"r{s}": {"loose": sum(1 for (bb, ss, _, _), p in prov.items() if bb == b and ss == s and p[:2] == WAFER),
                                                 "strict": sum(1 for (bb, ss, _, _), p in prov.items() if bb == b and ss == s and p[:2] == WAFER and p[2] != "ambiguous")}
                                       for s in (0, 1)} for b in ("b23", "b25")}}
    for mode, strict in (("loose", False), ("strict", True)):
        sets = {"b3_candidates": cand, "nulls_46": nulls}
        proxy[mode] = {
            "b25_two_samples": {name: {"items_both_cells_wafer": len(r := _restricted(items, prov, "b25", (0, 1), strict)),
                                       "kimi+sol (sol_mean)": _slim(tally(r, "kimi", "sol", "sol_mean", 2))}
                                for name, items in sets.items()},
            "b25_one_sample": {name: {f"r{s}": {"items_cell_wafer": len(r := _restricted(items, prov, "b25", (s,), strict)),
                                                "kimi+sol (sol_mean)": _slim(tally(r, "kimi", "sol", "sol_mean", 1), False)}
                                      for s in (0, 1)} for name, items in sets.items()},
            "b25_cell_rates_candidates": cell_rates(cand, prov, "b25", (0, 1), strict),
            "b25_cell_rates_nulls": cell_rates(nulls, prov, "b25", (0, 1), strict),
            "t1_two_samples": {"items_both_cells_wafer": len(r := _restricted(t1_two, prov, "b23", (0, 1), strict)),
                               "kimi+sol (sol_mean)": _slim(tally(r, "kimi", "sol", "sol_mean", 2)),
                               "kimi+sonnet55 (every)": _slim(tally(r, "kimi", "sonnet55", "every", 2))},
            "t1_one_sample_r0": {"items_cell_wafer": len(r := _restricted(t1, prov, "b23", (0,), strict)),
                                 "kimi+sol (sol_mean)": _slim(tally(r, "kimi", "sol", "sol_mean", 1)),
                                 "kimi+sonnet55 (every)": _slim(tally(r, "kimi", "sonnet55", "every", 1))},
            "t1_cell_rates_r0": cell_rates(t1, prov, "b23", (0,), strict),
            "b23_nulls_cell_rates_r0": cell_rates(b23_nulls, prov, "b23", (0,), strict),
        }
    s23 = _scores(root, "b23")
    proxy["b23_part_credit_by_provider"] = {
        "t1_items_rubric": credit_by_provider(prov, s23, "b23", {i["id"] for i in t1}, "rubric"),
        "b23_nulls_false_target": credit_by_provider(prov, s23, "b23", {i["id"] for i in b23_nulls}, "false"),
        "note": "Kimi part reads, both samples, the scorer's mean over passes > 0; per-cell rates for brief 25's candidates "
                "by provider are Part 3's (`kimi.brief25.part_credit_by_provider_and_sample`); every brief 25 null cell has "
                "D_part = 0, so every provider's false credit there is 0"}
    proxy["part3_b25_part_credit_by_provider_and_sample"] = part3["brief25"]["part_credit_by_provider_and_sample"]

    probe = json.loads((root / PROBE).read_text()) if (root / PROBE).exists() else None
    served = (probe or {}).get("record", {}).get("served") or [{}]
    pin_choice = {"rule": "Wafer at MXFP4 if available, else the deployment with the highest part credit at zero false credit "
                          "in Part 3's join (brief 29 E0-7)",
                  "wafer_mxfp4_listed": (probe or {}).get("wafer_mxfp4_listed"),
                  "probe_served": served[-1].get("provider"), "probe_precision": served[-1].get("precision"),
                  "probe_on_pin": served[-1].get("on_pin"),
                  "pin": "Wafer at MXFP4" if served[-1].get("on_pin") else "not established by the probe"}

    t1_missing = len(t1) - len(t1_two)
    est = estimates(root, t1_missing, len(cand) + len(nulls) + len(t1), sum(i["n_lines"] for i in t1), 3 * len(cand))

    main = two["b3_candidates"]["kimi+sol (sol_mean)"]
    strict2 = two["b3_candidates_glm_written"]["kimi+sonnet55 (every)"]
    nul = two["nulls_46"]["kimi+sol (sol_mean)"]
    verdict = {
        "reachable_at_two_samples": main["classes"]["certified"] > 0,
        "reachable_under_each_second_reader_rule": {"sol_mean": main["classes"]["certified"] > 0, "sonnet55_every": strict2["classes"]["certified"] > 0},
        "null_safe_at_two_samples": nul["classes"]["certified"] == 0 and nul["n"] == 46,
        "pinned_reader_proxy_computable_at_two_samples": {m: {k: proxy[m]["b25_two_samples"][k]["items_both_cells_wafer"] for k in ("b3_candidates", "nulls_46")}
                                                          for m in ("loose", "strict")},
        "not_computed": ["gate (i) at two certification rater sessions (one session on file; E3)",
                         f"T1 items at two samples for the {t1_missing} items read once (E1)",
                         "the pinned reader at two samples beyond the Wafer-served cells (E2)"],
    }
    inputs = {p: sha256(root / p) for p in (STRATUM, PER_PART, T1_JOIN, KIMI_CSV, PART3, PROTOCOL, *[f for fs in KIMI_CACHES.values() for f in fs],
                                            *SCORER_CACHES.values(), *READ_CACHES.values()) if (root / p).exists()}
    if probe:
        inputs[PROBE] = sha256(root / PROBE)
    return {"version": VERSION, "script_sha256": sha256(Path(__file__)), "part3_script_sha256": sha256(HERE / "stage3_b3_power_v3c.py"),
            "inputs_sha256": inputs, "constants": {"quiet_max": QUIET_MAX, "sol_mean_max": SOL_MEAN_MAX, "classes": CLASSES, "readings": READINGS},
            "verdict": verdict, "gate_i_single_session": gate_i, "gate_ii_pass_by_rule": gate_ii_rules,
            "two_samples": two, "one_sample_beside": one, "wafer_proxy": proxy, "pin_choice": pin_choice, "estimates": est}


# ── markdown ─────────────────────────────────────────────────────────────────────────────────────

def _cls(t: dict) -> str:
    c = t["classes"]
    r = t["certified_by_reading"]
    return (f"| {t['n']} | {t['gate_ii_pass']} | {c['certified']} | {r['same_sample']} | {r['both_both']} | {c['quiet_but_illegible']} "
            f"| {c['mixed']} | {c['part_derivable']} | {c['not_evaluable']} | {c['loud']} |")


HEAD = ("| set | pair (second reader's rule) | k | items | pass (ii) | certified (iii, any) | same sample | both, both | "
        "quiet-but-illegible | mixed | part-derivable | not evaluable | loud |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|")


def _row(name: str, label: str, t: dict) -> str:
    return f"| {name} | {label} | {t['k']} " + _cls(t)


def _pct(x):
    return "n/a" if x is None else f"{x:.3f}"


def render_md(R: dict) -> str:
    V, T, O, P, E = R["verdict"], R["two_samples"], R["one_sample_beside"], R["wafer_proxy"], R["estimates"]
    main = T["b3_candidates"]["kimi+sol (sol_mean)"]
    px2 = P["loose"]["b25_two_samples"]["b3_candidates"]["kimi+sol (sol_mean)"]
    pn2 = P["loose"]["b25_two_samples"]["nulls_46"]["kimi+sol (sol_mean)"]
    cr_ = P["loose"]["b25_cell_rates_candidates"]
    L = [f"# Gate reachability and null safety at two samples (brief 29 E0-5, session 29-B; blue; counts, aggregates and hashes only)",
         "",
         f"Script `work/checks/stage3_elicitation_gate_reachability.py` {R['script_sha256'][:8]}; no call made. The gates, readers and "
         f"classes are `certification-protocol-v0.md` ({R['inputs_sha256'][PROTOCOL][:8]}) sections 4 to 6, recomputed from brief 23's and "
         "brief 25's existing readings by id and aggregate. Item ids are in the JSON; no item text, rubric or answer was read.",
         "",
         "## Verdict",
         "",
         f"- **Reachable at two samples: {'yes' if V['reachable_at_two_samples'] else 'no'}.** On brief 25's B3 candidates under Kimi K3 "
         f"(mixed providers) and Sol's mean rule, {main['classes']['certified']} of {main['n']} pass all three gates "
         f"(gate (i) single session; gate (iii) per reader on any sample); {main['certified_by_reading']['same_sample']} under the same-sample "
         f"reading and {main['certified_by_reading']['both_both']} with both readers crediting the whole on both samples. Under Sonnet 5.5's "
         f"every-sample rule (the strict second reader, on the {T['b3_candidates_glm_written']['kimi+sonnet55 (every)']['n']} GLM-written "
         f"candidates): {T['b3_candidates_glm_written']['kimi+sonnet55 (every)']['classes']['certified']} certified.",
         f"- **Null-safe at two samples: {'yes' if V['null_safe_at_two_samples'] else 'no'}.** Brief 25's 46 nulls (22 controls and 24 "
         f"same-shape comparison items, against their false targets): {T['nulls_46']['kimi+sol (sol_mean)']['classes']['certified']} of 46 "
         f"certified under either rule; every null passes gate (ii) and no null's whole is credited on any sample, so all 46 fall in the "
         "quiet-but-illegible class: that class does not separate quiet-but-illegible items from honest ones, and the certified class does.",
         f"- **Under the pinned reader (Wafer at MXFP4) at two samples: null-safe on the subset the proxy covers; reachability not "
         f"shown.** Part 3's join ({'reproduced exactly' if P['join_reproduces_part3'] else 'NOT reproduced'}) puts both samples' four "
         f"Kimi conditions on Wafer for {px2['n']} B3 candidates and {pn2['n']} nulls (Part 3's pairing; "
         f"{V['pinned_reader_proxy_computable_at_two_samples']['strict']['b3_candidates']} and "
         f"{V['pinned_reader_proxy_computable_at_two_samples']['strict']['nulls_46']} with a determined provider). Of those "
         f"{px2['n']} candidates {px2['gate_ii_pass'] or 'none'} passes gate (ii) and {px2['classes']['certified'] or 'none'} is "
         f"certified; of the {pn2['n']} nulls, {pn2['classes']['certified'] or 'none'}. Wafer-served cells credit a part far more often than the other cells "
         f"({_pct(cr_['wafer']['share_D_part_pos'])} of {cr_['wafer']['cells']} candidate cells against {_pct(cr_['other']['share_D_part_pos'])} "
         f"of {cr_['other']['cells']}; A6.18 (m)'s 'about twice as often'), so gate (ii) under the pin will pass far fewer items than "
         f"brief 25's {main['gate_ii_pass']} of {main['n']}. These are small and possibly time-clustered cells, an orientation only: "
         "whether certification is reachable under the pinned reader at two samples is not shown by the existing readings, and E2 "
         "answers it.",
         "- **Not computed (each needs a new reading; estimates below, nothing run):** " + "; ".join(V["not_computed"]) + ".",
         "",
         "## Gate (i), one rater session",
         "",
         f"- B3 candidates: {R['gate_i_single_session']['b3_candidates']['at_or_under_60']} of {R['gate_i_single_session']['b3_candidates']['n']} "
         "at or under 60 (brief 25's `rater_top_line`; they are B3's quiet set, selected by this gate, so it cannot bind here)."]
    for s, g in R["gate_i_single_session"]["t1_items"].items():
        L.append(f"- T1 {s[3:].replace('_', ' ')}: {g['at_or_under_60_two_pass_mean']} of {g['n']} items have every line at or under 60 "
                 f"(07k's two-pass line mean; pass 1 alone {g['at_or_under_60_pass1']}).")
    L += [f"- Nulls: {R['gate_i_single_session']['nulls']}.", f"- {R['gate_i_single_session']['session_count']}.", "",
          "## Gate (ii) by second-reader rule (brief 25, two samples)", "",
          "| items | rule | pass |", "|---|---|---|"]
    for name, d in R["gate_ii_pass_by_rule"].items():
        for rule, n in d.items():
            L.append(f"| {name.replace('_', ' ')} | {rule} | {n} |")
    g78, g37 = R["gate_ii_pass_by_rule"]["b3_candidates_78"], R["gate_ii_pass_by_rule"]["b3_candidates_glm_37"]
    s37, m37 = T["b3_candidates_glm_written"]["kimi+sonnet55 (every)"], T["b3_candidates_glm_written"]["kimi+sol (sol_mean), same items"]
    L += ["", f"Given Kimi K3's every-sample rule, the second reader removes {g78['kimi every'] - g78['kimi every + sol sol_mean']} of "
          f"{g78['kimi every']} under Sol's mean rule (78 items; {g78['kimi every'] - g78['kimi every + sol every']} under Sol's every-sample "
          f"rule, beside). On the 37 GLM-written items Sol's mean rule removes {g37['kimi every'] - g37['kimi every + sol sol_mean']} of "
          f"{g37['kimi every']} and Sonnet 5.5's every-sample rule {g37['kimi every'] - g37['kimi every + sonnet55 every']}: on these data the "
          "two second-reader rules differ little at gate (ii) once Kimi's rule applies. They differ at gate (iii): with Sonnet 5.5 as the "
          f"second reader {s37['classes']['certified']} of the 37 are certified, with Sol {m37['classes']['certified']}, because Sonnet 5.5 "
          "credits the whole less often (protocol section 10, item 6: every pooled yield carries its rule).", "",
          "## The gate at two samples", "", HEAD,
          _row("B3 candidates", "Kimi K3 + Sol (mean)", main),
          _row("B3 candidates", "Kimi K3 + Sol (every, beside)", T["b3_candidates"]["kimi+sol (every, beside)"])]
    for w, t in T["b3_candidates"]["by_writer (kimi+sol, sol_mean)"].items():
        L.append(_row(f"B3 candidates, {w}-written", "Kimi K3 + Sol (mean)", t))
    L += [_row("B3 candidates, GLM-written", "Kimi K3 + Sonnet 5.5 (every)", T["b3_candidates_glm_written"]["kimi+sonnet55 (every)"]),
          _row("B3 candidates, GLM-written", "Kimi K3 + Sol (mean)", T["b3_candidates_glm_written"]["kimi+sol (sol_mean), same items"]),
          _row("nulls (46)", "Kimi K3 + Sol (mean)", T["nulls_46"]["kimi+sol (sol_mean)"]),
          _row("nulls (46)", "Kimi K3 + Sol (every)", T["nulls_46"]["kimi+sol (every)"]),
          _row("nulls, 10 controls read by Sonnet 5.5", "Kimi K3 + Sonnet 5.5 (every)", T["nulls_46"]["kimi+sonnet55 (every), the 10 controls read by Sonnet 5.5"])]
    for s, t in T["nulls_46"]["by_set (kimi+sol, sol_mean)"].items():
        L.append(_row(f"nulls, {s}", "Kimi K3 + Sol (mean)", t))
    L += [_row("T1 retest items", "Kimi K3 + Sol (mean)", T["t1_retest_items"]["kimi+sol (sol_mean)"]),
          _row("T1 retest items", "Kimi K3 + Sonnet 5.5 (every)", T["t1_retest_items"]["kimi+sonnet55 (every)"]),
          _row("brief 23 nulls, retest items", "Kimi K3 + Sol (mean)", T["b23_nulls_retest_items"]["kimi+sol (sol_mean)"]),
          "", "Gate (i) is applied where a rater figure exists (B3 candidates, T1 items) and not applied to nulls. Brief 23 read every "
          "T1 item with all three families, so no family exclusion is applied to the T1 rows.", "",
          "## Beside: one sample (sample 0)", "", HEAD,
          _row("T1 items", "Kimi K3 + Sol (mean)", O["t1_items"]["kimi+sol (sol_mean)"]),
          _row("T1 items", "Kimi K3 + Sonnet 5.5 (every)", O["t1_items"]["kimi+sonnet55 (every)"])]
    for s, t in O["t1_items"]["by_regime (kimi+sol, sol_mean)"].items():
        L.append(_row(f"T1 {s[3:].replace('_', ' ')}", "Kimi K3 + Sol (mean)", t))
    L += [_row("brief 23 nulls", "Kimi K3 + Sol (mean)", O["b23_nulls"]["kimi+sol (sol_mean)"]),
          _row("brief 23 nulls", "Kimi K3 + Sonnet 5.5 (every)", O["b23_nulls"]["kimi+sonnet55 (every)"])]
    for s, t in O["b23_nulls"]["by_set (kimi+sol, sol_mean)"].items():
        L.append(_row(f"brief 23 nulls, {s[4:].replace('_', ' ')}", "Kimi K3 + Sol (mean)", t))
    L += [_row("B3 candidates, sample 0", "Kimi K3 + Sol (mean)", O["b3_candidates_sample0"]["kimi+sol (sol_mean)"]),
          "", "A second sample can only remove items from gate (ii) under an every-sample rule; under Sol's mean rule it can also "
          "admit one (a part credited on one sample only); it can only add items to gate (iii)'s per-reader reading. On the B3 "
          f"candidates sample 0 alone certifies {O['b3_candidates_sample0']['kimi+sol (sol_mean)']['classes']['certified']}, two samples "
          f"{main['classes']['certified']}.", "",
          "## The Wafer-served proxy for the pinned reader (Part 3's join)", "",
          f"- Join: {P['join']['matched']} of {P['join']['records']} Kimi records matched; reproduces Part 3's `kimi` block: "
          f"{P['join_reproduces_part3']}. Read records by provider determinacy: {json.dumps(P['read_determinacy'])} ('ambiguous' = "
          "paired by time order among generations of different providers; 'strict' below drops those).",
          "- Wafer-served Kimi reads (loose / strict): " + "; ".join(f"brief {b[1:]} r{s}: {v['loose']} / {v['strict']}"
                                                                    for b, d in P["wafer_reads"].items() for s, v in ((k[1:], x) for k, x in d.items())) + ".",
          "", "| | mode | Wafer cells | Kimi D_part > 0 | Kimi D_whole > 0 | other cells | D_part > 0 | D_whole > 0 |", "|---|---|---|---|---|---|---|---|"]
    for mode in ("loose", "strict"):
        for name, key in (("B3 candidates, both samples", "b25_cell_rates_candidates"), ("nulls (46), both samples", "b25_cell_rates_nulls"),
                          ("T1 items, r0", "t1_cell_rates_r0"), ("brief 23 nulls, r0", "b23_nulls_cell_rates_r0")):
            c = P[mode][key]
            L.append(f"| {name} | {mode} | {c['wafer']['cells']} | {_pct(c['wafer']['share_D_part_pos'])} | {_pct(c['wafer']['share_D_whole_pos'])} "
                     f"| {c['other']['cells']} | {_pct(c['other']['share_D_part_pos'])} | {_pct(c['other']['share_D_whole_pos'])} |")
    L += ["", "Under the proxy (Kimi's values from Wafer-served cells only; the second reader's from the same samples):", "", HEAD]
    for mode in ("loose", "strict"):
        for name, d in P[mode]["b25_two_samples"].items():
            L.append(_row(f"{name.replace('_', ' ')} ({d['items_both_cells_wafer']} with both cells on Wafer)", f"Kimi K3 Wafer + Sol (mean), {mode}", d["kimi+sol (sol_mean)"]))
        for name, d in P[mode]["b25_one_sample"].items():
            for s, x in d.items():
                L.append(_row(f"{name.replace('_', ' ')}, {s} ({x['items_cell_wafer']} Wafer cells)", f"Kimi K3 Wafer + Sol (mean), {mode}", x["kimi+sol (sol_mean)"]))
        d = P[mode]["t1_two_samples"]
        L.append(_row(f"T1 retest items ({d['items_both_cells_wafer']} both on Wafer)", f"Kimi K3 Wafer + Sol (mean), {mode}", d["kimi+sol (sol_mean)"]))
        d = P[mode]["t1_one_sample_r0"]
        L.append(_row(f"T1 items, r0 ({d['items_cell_wafer']} Wafer cells)", f"Kimi K3 Wafer + Sol (mean), {mode}", d["kimi+sol (sol_mean)"]))
        L.append(_row(f"T1 items, r0 ({d['items_cell_wafer']} Wafer cells)", f"Kimi K3 Wafer + Sonnet 5.5 (every), {mode}", d["kimi+sonnet55 (every)"]))
    L += ["", "Kimi part credit by provider and precision (brief 23, part reads on both samples; the scorer's pass mean > 0):", "",
          "| provider | T1 part reads (rubric) | credited | share | brief 23 null part reads (false target) | credited |", "|---|---|---|---|---|---|"]
    cr = P["b23_part_credit_by_provider"]
    for k in sorted(set(cr["t1_items_rubric"]) | set(cr["b23_nulls_false_target"])):
        a, b = cr["t1_items_rubric"].get(k, {}), cr["b23_nulls_false_target"].get(k, {})
        L.append(f"| {k} | {a.get('part_reads', 0)} | {a.get('credited', 0)} | {_pct(a.get('share'))} | {b.get('part_reads', 0)} | {b.get('credited', 0)} |")
    pc = R["pin_choice"]
    wf = cr["b23_nulls_false_target"].get("|".join(WAFER), {})
    L += ["", f"Brief 25's candidates by provider and sample are Part 3's table (in the JSON); every brief 25 null cell has D_part = 0, "
          f"so no provider gives false credit there. In brief 23's nulls Wafer credited {wf.get('credited', 0)} of {wf.get('part_reads', 0)} "
          "part reads against the false target, so Wafer's false credit is not exactly zero across both briefs; the zero-false-credit "
          "clause of E0-7's rule governs only the fallback, which is not needed.", "",
          f"**Pin (E0-7):** {pc['rule']}. Wafer at MXFP4 is listed ({pc['wafer_mxfp4_listed']}); the probe was served by "
          f"{pc['probe_served']} at {pc['probe_precision']} (on the pin: {pc['probe_on_pin']}), so the pin is **{pc['pin']}** and the "
          "fallback ranking is not needed.", "",
          "## Figures that need a new reading (estimates; nothing run)", ""]
    e1, e2, e3 = E["E1_t1_second_sample"], E["E2_pinned_kimi_two_samples"], E["E3_second_rater_session"]
    L += [f"- **E1, T1 at two samples:** {e1['what']}: {e1['items']} items, {e1['reads_per_reader']} reads per reader; reads "
          f"{', '.join(f'{k} ${v:.2f}' for k, v in e1['read_usd'].items())}, scoring ${e1['score_usd']:.2f}; about **${e1['total_usd']:.2f}**.",
          f"- **E2, the pinned reader at two samples:** {e2['what']}: {e2['items']} items, {e2['reads']} Kimi reads ${e2['read_usd']:.2f}, "
          f"scoring ${e2['score_usd']:.2f}; about **${e2['total_usd']:.2f}** (the T1 rows also need E1's second-reader samples).",
          f"- **E3, gate (i)'s second session:** {e3['what']}; {e3['statements']} statements ({e3['t1_statements']} T1, "
          f"{e3['candidate_statements']} candidates).",
          f"- Basis: per-read and per-score means from the caches ({json.dumps(E['basis']['per_read_usd'])}; scorer "
          f"{json.dumps(E['basis']['per_score_usd'])}), {E['basis']['scorer_passes_per_read']} scorer passes per read; {E['basis']['note']}.",
          "", "## Inputs", ""]
    L += [f"- `{p}` {h[:8]}" for p, h in R["inputs_sha256"].items()]
    L += [f"- Part 3's script `work/checks/stage3_b3_power_v3c.py` {R['part3_script_sha256'][:8]} (its `fingerprint_join`, imported unchanged)", ""]
    return "\n".join(L) + "\n"


def cmd_report(a: argparse.Namespace) -> int:
    root = Path(a.root)
    R = build(root)
    Path(a.json).write_text(json.dumps(R, indent=1) + "\n")
    Path(a.md).write_text(render_md(R))
    V = R["verdict"]
    print(f"reachable {V['reachable_at_two_samples']}; null-safe {V['null_safe_at_two_samples']}; "
          f"join reproduces Part 3 {R['wafer_proxy']['join_reproduces_part3']}; wrote {a.json} and {a.md}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("report")
    p.add_argument("--root", default=str(HERE.parent.parent))
    p.add_argument("--json", required=True)
    p.add_argument("--md", required=True)
    a = ap.parse_args(argv)
    return {"report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
