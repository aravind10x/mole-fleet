#!/usr/bin/env python3
"""Brief 25 C3: the comprehension-quiet stratum's report and the T1 join (A6.14.5).

Script-only, as stage3_b3_comprehension (kept apart so that report changes never move the run's script hash). Prints
counts, ids, hashes and dollars through stage3_legibility's `emit`; no item line, declared effect, answer or reason is
read into any output (scores, statuses and costs only).

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_comprehension_report.py report
        stratum-v0.json (per item by opaque id) and stratum-v0.md (aggregates)
    ... stage3_b3_comprehension_report.py t1-join
        t1-join-v0.json and t1-join-v0.md: brief 23's per-line D_part (re-emitted through stage3_legibility.py's report
        mode, t1-per-part-v0.json) joined to 07k's section-2 line scores by key

Statistics. Per reader, item and sample: D_whole (the whole condition's mean over scored passes), D_part (the maximum
over the three parts), against the L target (a candidate's own rubric; a null item's same-document false target). An
item is evaluable under a reader when D_part was computed on every sample; otherwise it is not evaluable under that
reader, with the first failing part's status named (a refusal is never 0). Comprehension-quiet (A6.14.2, C1's rule):
Kimi K3's D_part = 0 on every sample and Sol's mean D_part at or under the plan's threshold (or its majority rule);
an item is not quiet when either reader's rule fails on an evaluable reading, and not evaluable otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_comprehension as bc  # noqa: E402
import stage3_legibility as lg  # noqa: E402

VERSION = "b3-comprehension/report-v0"
OUT = bc.OUT
REFUSED = ("refused_provider", "refused_token", "refused_prose")
RATER_BAR = 60.0
T1_RATER = bc.S3 / "t1k-rater"
T1_FILE = {"v2_conforming": "payloads-v2.json", "v3_middle": "payloads-v3.json"}
T1_ARM = {"v2_conforming": "conforming", "v3_middle": "middle"}


# ── per item ────────────────────────────────────────────────────────────────────────────────────────

def rule_holds(values: Sequence[float], rule: Mapping[str, Any]) -> bool:
    """A reader's quiet rule over its per-sample D_part values (all computed)."""
    kind = rule["kind"]
    if kind == "every":
        return all(v == 0 for v in values)
    if kind == "majority":
        return sum(1 for v in values if v == 0) > len(values) / 2
    if kind == "mean":
        return sum(values) / len(values) <= float(rule["threshold"]) + 1e-9
    raise ValueError(kind)


def reader_rules(items: Mapping[str, Any]) -> dict[str, dict]:
    sol = items["config"]["sol_rule"]
    return {bc.ANCHOR: {"kind": "every", "threshold": None}, bc.SECOND: {"kind": sol["kind"], "threshold": sol["threshold"]},
            bc.BESIDE: {"kind": "every", "threshold": None}}


def reader_item(rec: Any, fam: str, row: Mapping[str, Any], k: int, rule: Mapping[str, Any], target: str | None = None) -> dict:
    t = target or bc.l_target(row["regime"])
    samples = []
    for s in range(k):
        x = rec.item_stat(fam, s, row, t)
        samples.append({"D_whole": x["D_whole"], "D_part": x["D_part"], "parts": [x["cond_scores"][c] for c in bc.PARTS],
                        "D_part_status": x["D_part_status"], "D_whole_status": x["D_whole_status"]})
    dps = [x["D_part"] for x in samples]
    dws = [x["D_whole"] for x in samples if x["D_whole"] is not None]
    evaluable = all(v is not None for v in dps)
    reason = None if evaluable else next(x["D_part_status"] for x in samples if x["D_part"] is None)
    return {"samples": samples, "evaluable": evaluable, "not_evaluable_reason": reason,
            "refused_part": any(x["D_part_status"] in REFUSED for x in samples),
            "D_part_mean": sum(dps) / len(dps) if evaluable else None,
            "D_whole_mean": sum(dws) / len(dws) if dws else None, "n_D_whole": len(dws),
            "quiet": rule_holds(dps, rule) if evaluable else None,
            "any_part_credited": any(v > 0 for v in dps if v is not None) if any(v is not None for v in dps) else None}


def membership(per_reader: Mapping[str, Mapping[str, Any]], readers: Sequence[str]) -> str:
    vals = [per_reader[f]["quiet"] for f in readers]
    if any(v is False for v in vals):
        return "not_quiet"
    if all(v is True for v in vals):
        return "quiet"
    return "not_evaluable"


def composition_by_id(key_b3: Mapping[str, Any], quiet: Sequence[Mapping[str, Any]]) -> dict[str, dict]:
    """Each quiet candidate's composition (two-pass mean of the composition item), rater line means, top line and
    top-two gap, by opaque id (for brief 20 Part 3)."""
    tid = {(v["writer"], v["id"]): t for t, v in key_b3["triples"].items() if str(v.get("source", "")).startswith("candidates-")}
    out = {}
    for q in quiet:
        lines = sorted(((a + b) / 2 for a, b in zip(q["p1"], q["p2"])), reverse=True)
        out[tid[(q["writer"], q["id"])]] = {"composition": (q["c1"] + q["c2"]) / 2, "composition_p1": q["c1"], "composition_p2": q["c2"],
                                            "rater_top_line": lines[0], "rater_top_two_gap": lines[0] - lines[1],
                                            "replace_share": sum(q["replace"]) / 3}
    return out


def item_table(rec: Any, rows: Sequence[Mapping[str, Any]], items: Mapping[str, Any], comp: Mapping[str, Mapping[str, Any]]) -> dict:
    k = int(items["samples_per_condition"])
    rules = reader_rules(items)
    out = {}
    for row in rows:
        per = {f: reader_item(rec, f, row, k, rules[f]) for f in row["readers"]}
        d: dict[str, Any] = {"regime": row["regime"], "writer": row["writer"], "document": row["document"],
                             "anchors_resolve": row["anchors_resolve"], "readers": per,
                             "membership": membership(per, bc.ALL_ITEM_READERS)}
        if bc.GLM_ONLY_READER in per:
            d["membership_kimi_sonnet55_beside"] = membership(per, (bc.ANCHOR, bc.GLM_ONLY_READER))
            d["membership_all_three_beside"] = membership(per, (bc.ANCHOR, bc.SECOND, bc.GLM_ONLY_READER))
        d["sample0_both_quiet"] = (all(per[f]["samples"][0]["D_part"] == 0 for f in bc.ALL_ITEM_READERS)
                                   if all(per[f]["samples"][0]["D_part"] is not None for f in bc.ALL_ITEM_READERS) else None)
        if row["regime"] == "candidate":
            d.update(comp[row["item_id"]])
            if row.get("own"):
                d["own"] = {f: reader_item(rec, f, row, 1, rules[f], target="own") for f in row["readers"]}
        if row["regime"] == "sham":
            d["paired"] = {f: reader_item(rec, f, row, 1, rules[f], target="paired") for f in row["readers"]}
        out[row["item_id"]] = d
    return out


# ── aggregates ──────────────────────────────────────────────────────────────────────────────────────

def _mean(xs: Sequence[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def stratum_summary(table: Mapping[str, Mapping[str, Any]]) -> dict:
    cands = {i: d for i, d in table.items() if d["regime"] == "candidate"}
    ids = sorted(i for i, d in cands.items() if d["membership"] == "quiet")
    by = lambda key, val: dict(sorted(Counter(d["writer"] for d in cands.values() if d[key] == val).items()))  # noqa: E731
    glm = {i: d for i, d in cands.items() if d["writer"] == "glm53"}
    out = {"ids": ids, "ids_sha256": lg.sha256("\n".join(ids)), "n": len(ids), "of_quiet_set": len(cands),
           "share_of_quiet_set": len(ids) / len(cands) if cands else None,
           "by_writer": by("membership", "quiet"),
           "membership_counts": dict(sorted(Counter(d["membership"] for d in cands.values()).items())),
           "not_quiet_by_writer": by("membership", "not_quiet"), "not_evaluable_by_writer": by("membership", "not_evaluable"),
           "share_of_evaluable": None,
           "resolved_anchor_subset": {"n_items": sum(1 for d in cands.values() if d["anchors_resolve"]),
                                      "n_quiet": sum(1 for d in cands.values() if d["anchors_resolve"] and d["membership"] == "quiet")},
           "whole_credit_among_quiet": {"D_whole_zero_every_sample_both_readers": sum(
               1 for i in ids if all(cands[i]["readers"][f]["D_whole_mean"] == 0 for f in bc.ALL_ITEM_READERS)),
               "D_whole_positive_both_readers": sum(1 for i in ids if all((cands[i]["readers"][f]["D_whole_mean"] or 0) > 0
                                                                          for f in bc.ALL_ITEM_READERS))},
           "beside": {
               "kimi_alone_quiet": sum(1 for d in cands.values() if d["readers"][bc.ANCHOR]["quiet"] is True),
               "sol_alone_quiet": sum(1 for d in cands.values() if d["readers"][bc.SECOND]["quiet"] is True),
               "sample0_both_quiet": sum(1 for d in cands.values() if d["sample0_both_quiet"] is True),
               "glm_written": {"n": len(glm), "stratum_rule": sum(1 for d in glm.values() if d["membership"] == "quiet"),
                               "kimi_and_sonnet55": sum(1 for d in glm.values() if d.get("membership_kimi_sonnet55_beside") == "quiet"),
                               "all_three": sum(1 for d in glm.values() if d.get("membership_all_three_beside") == "quiet"),
                               "sonnet55_alone_quiet": sum(1 for d in glm.values() if d["readers"][bc.GLM_ONLY_READER]["quiet"] is True),
                               "sonnet55_not_evaluable": sum(1 for d in glm.values() if not d["readers"][bc.GLM_ONLY_READER]["evaluable"])}}}
    ev = sum(1 for d in cands.values() if d["membership"] != "not_evaluable")
    out["share_of_evaluable"] = len(ids) / ev if ev else None
    return out


def not_evaluable(table: Mapping[str, Mapping[str, Any]]) -> dict:
    out: dict[str, Any] = {}
    for f in bc.PLAN_READERS:
        rows = [(i, d) for i, d in table.items() if f in d["readers"] and not d["readers"][f]["evaluable"]]
        out[f] = {"n": len(rows), "by_regime": dict(sorted(Counter(d["regime"] for _i, d in rows).items())),
                  "by_reason": dict(sorted(Counter(d["readers"][f]["not_evaluable_reason"] for _i, d in rows).items())),
                  "ids": sorted(i for i, _d in rows)}
    return out


def by_reader_regime(table: Mapping[str, Mapping[str, Any]]) -> dict:
    out: dict[str, Any] = {}
    for f in bc.PLAN_READERS:
        out[f] = {}
        for g in bc.REGIMES:
            ds = [d["readers"][f] for d in table.values() if d["regime"] == g and f in d["readers"]]
            if not ds:
                continue
            k = len(ds[0]["samples"])
            out[f][g] = {"n_items": len(ds), "n_evaluable": sum(1 for x in ds if x["evaluable"]),
                         "D_part_mean": _mean([x["D_part_mean"] for x in ds]), "D_whole_mean": _mean([x["D_whole_mean"] for x in ds]),
                         "share_quiet_under_reader_rule": _mean([1.0 if x["quiet"] else 0.0 for x in ds if x["quiet"] is not None]),
                         "per_sample": {f"s{s}": {"D_part_mean": _mean([x["samples"][s]["D_part"] for x in ds]),
                                                  "D_whole_mean": _mean([x["samples"][s]["D_whole"] for x in ds]),
                                                  "share_D_part_zero": _mean([1.0 if x["samples"][s]["D_part"] == 0 else 0.0
                                                                              for x in ds if x["samples"][s]["D_part"] is not None])}
                                        for s in range(k)},
                         "D_part_mean_histogram": dict(sorted(Counter(f"{x['D_part_mean']:.2f}" for x in ds if x["D_part_mean"] is not None).items()))}
    return out


def null_figures(table: Mapping[str, Mapping[str, Any]]) -> dict:
    """P(D_part > 0 | false target) for the controls and the sham, per reader: over (item, sample) cells, over items
    (any sample), and the reader's quiet rule failing; D_whole false credit beside; the sham's paired rubric (sample 0)."""
    out: dict[str, Any] = {}
    for f in bc.PLAN_READERS:
        out[f] = {}
        for g in bc.NULL_REGIMES + ("pooled",):
            ds = [d for d in table.values() if d["regime"] in (bc.NULL_REGIMES if g == "pooled" else (g,)) and f in d["readers"]]
            if not ds:
                continue
            cells = [x["D_part"] for d in ds for x in d["readers"][f]["samples"] if x["D_part"] is not None]
            whole = [x["D_whole"] for d in ds for x in d["readers"][f]["samples"] if x["D_whole"] is not None]
            items_any = [d["readers"][f]["any_part_credited"] for d in ds if d["readers"][f]["any_part_credited"] is not None]
            rule_fail = [not d["readers"][f]["quiet"] for d in ds if d["readers"][f]["quiet"] is not None]
            r = {"n_items": len(ds), "n_cells": len(cells), "P_D_part_pos_per_cell": _mean([1.0 if v > 0 else 0.0 for v in cells]),
                 "P_D_part_pos_any_sample": _mean([1.0 if v else 0.0 for v in items_any]), "n_items_with_a_reading": len(items_any),
                 "P_reader_rule_not_quiet": _mean([1.0 if v else 0.0 for v in rule_fail]),
                 "P_D_whole_pos_per_cell": _mean([1.0 if v > 0 else 0.0 for v in whole]), "n_whole_cells": len(whole)}
            if g in ("sham", "pooled"):
                sh = [d for d in ds if d["regime"] == "sham"]
                pp = [d["paired"][f]["samples"][0] for d in sh if f in d.get("paired", {})]
                r["paired_sample0"] = {"n": len(pp), "P_D_part_pos": _mean([1.0 if x["D_part"] > 0 else 0.0 for x in pp if x["D_part"] is not None]),
                                       "P_D_whole_pos": _mean([1.0 if x["D_whole"] > 0 else 0.0 for x in pp if x["D_whole"] is not None])}
            out[f][g] = r
    stratum = [d for d in table.values() if d["regime"] in bc.NULL_REGIMES]
    out["stratum_rule_on_nulls"] = {"n": len(stratum), "membership_counts": dict(sorted(Counter(d["membership"] for d in stratum).items()))}
    return out


def positive_control(table: Mapping[str, Mapping[str, Any]]) -> dict:
    out = {}
    for f in bc.PLAN_READERS:
        ds = [d["own"][f]["samples"][0] for d in table.values() if "own" in d and f in d["own"]]
        out[f] = {"n": len(ds), "D_whole_own": _mean([x["D_whole"] for x in ds]), "D_part_own": _mean([x["D_part"] for x in ds]),
                  "mean_over_parts_own": _mean([_mean(x["parts"]) for x in ds if all(p is not None for p in x["parts"])]),
                  "n_D_whole": sum(1 for x in ds if x["D_whole"] is not None), "n_D_part": sum(1 for x in ds if x["D_part"] is not None)}
    return out


def sample_agreement(table: Mapping[str, Mapping[str, Any]]) -> dict:
    """Observed s0 against s1 on the candidates, per reader: quiet-status flips (C1's model input, now on B3)."""
    out = {}
    for f in bc.PLAN_READERS:
        pairs = [(d["readers"][f]["samples"][0]["D_part"], d["readers"][f]["samples"][1]["D_part"]) for d in table.values()
                 if d["regime"] == "candidate" and f in d["readers"] and len(d["readers"][f]["samples"]) > 1]
        pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
        out[f] = {"n": len(pairs), "quiet_flips": sum(1 for a, b in pairs if (a == 0) != (b == 0)),
                  "flip_rate": _mean([1.0 if (a == 0) != (b == 0) else 0.0 for a, b in pairs]),
                  "share_equal": _mean([1.0 if a == b else 0.0 for a, b in pairs]),
                  "spearman": lg.spearman([a for a, _ in pairs], [b for _, b in pairs]) if len(pairs) >= 3 else None}
    return out


def outcome_tables(rec: Any, rows: Sequence[Mapping[str, Any]], k: int) -> dict:
    reader: dict[str, Any] = {}
    scorer: dict[str, Any] = {}
    for f in bc.PLAN_READERS:
        for g in bc.REGIMES:
            rr = [r for r in rows if r["regime"] == g and f in r["readers"]]
            if not rr:
                continue
            for s in range(k):
                reader[f"{f}:s{s}:{g}"] = {c: dict(sorted(Counter(rec.reader_status(f, s, r, c) for r in rr).items())) for c in bc.CONDS}
                cnt: Counter = Counter()
                for r in rr:
                    for c in bc.CONDS:
                        if rec.answer(f, s, r["item_id"], c) is None:
                            continue
                        for p, t in bc.scorer_units(r, s):
                            cnt[f"{t}:p{p}:{rec.score_outcome(f, s, r['item_id'], c, t, p)}"] += 1
                scorer[f"{f}:s{s}:{g}"] = dict(sorted(cnt.items()))
    return {"reader": reader, "scorer": scorer}


def kappas(rec: Any) -> dict:
    out = {}
    for f in bc.PLAN_READERS:
        a, b = rec.pass_pairs(f)
        out[f] = {"kappa": lg.cohen_kappa(a, b), "n_pass_pairs": len(a), "agreement": _mean([1.0 if x == y else 0.0 for x, y in zip(a, b)])}
    return out


def per_item_json(table: Mapping[str, Mapping[str, Any]]) -> dict:
    """Per item by opaque id: membership, composition and gap (candidates), and per reader the per-sample D_whole and
    D_part, the continuous D_part (mean over samples), the rule's label and evaluability."""
    out = {}
    for i, d in sorted(table.items()):
        e = {k: v for k, v in d.items() if k not in ("readers", "own", "paired")}
        e["readers"] = {f: {"D_whole": [x["D_whole"] for x in r["samples"]], "D_part": [x["D_part"] for x in r["samples"]],
                            "D_part_mean": r["D_part_mean"], "D_whole_mean": r["D_whole_mean"], "quiet": r["quiet"],
                            "evaluable": r["evaluable"], "not_evaluable_reason": r["not_evaluable_reason"],
                            "D_part_status": [x["D_part_status"] for x in r["samples"]]} for f, r in d["readers"].items()}
        if "own" in d:
            e["own"] = {f: {"D_whole": r["samples"][0]["D_whole"], "D_part": r["samples"][0]["D_part"]} for f, r in d["own"].items()}
        if "paired" in d:
            e["paired"] = {f: {"D_whole": r["samples"][0]["D_whole"], "D_part": r["samples"][0]["D_part"]} for f, r in d["paired"].items()}
        out[i] = e
    return out


# ── the report ──────────────────────────────────────────────────────────────────────────────────────

DISCLOSURES = [
    "Readers: Kimi K3 (OpenRouter key 2) and GPT-6 Sol (Bedrock Converse) on every item; Claude Sonnet 5.5 (Bedrock global profile) "
    "on the GLM-written items only, beside, so that no reader reads its own family's items (the Sonnet-written candidates are not read "
    "by Sonnet 5.5). Sol is allowed here because the stratum feeds the per-agent readings under Opus 4.8; A6.3(e)'s Sol O_diff is never "
    "reported on this stratum.",
    "Scorer: Claude Sonnet 5 on Bedrock, two passes, brief 23's consequence-only instruction unchanged (prompt hashes checked against "
    "brief 23's items-v0.json before the items were written). The scorer never sees the item.",
    "Sampling: temperature not sent on any route; OpenRouter reasoning at the provider default; samples and passes sample at these "
    "settings, with the sample and pass indices in every cache label.",
    "Rendering as brief 23: each edit against its document's day-0 text with the note that the copy may predate other routine edits; "
    "replace anchors that do not resolve in the day-0 text are counted per regime, and the resolved-anchor subset is reported beside.",
    "The sham items are brief 23's control regime (v2's 24 same-shape sham triples), re-read here; their false targets are drawn from "
    "B3's quiet candidates on the same document, so their null figure is the false-credit rate against B3's rubrics.",
    "The positive control reads the own-edit target ('the document now says ...') on 20 candidates at sample 0; it checks the scorer "
    "chain's sensitivity on B3's edits and is not a null.",
    "Spend accounting is response-based (an abandoned OpenRouter request may be billed without a response on file).",
]
DEVIATIONS = [
    "C1's model: the plan fits a cross-reader two-class latent class model (the main fit, which governs) and reports a reader-relative "
    "sensitivity (symmetric error from each reader's own flips) added after the first computation of the plan and before its commit "
    "and before any call; both give the same choice (stratum-plan.json).",
    "No candidate in C1 reaches 0.8 and 0.1; the run uses the best attainable pair, as the brief expects at 10 retest items per reader.",
    "Controls (B3's same-writer controls) carry no pairing in their records, so they have no paired-rubric sensitivity; the sham's "
    "paired rubric is brief 23's (T1v2-Snn to T1v2-Cnn), read at sample 0.",
    "The own-edit and paired targets are scored at sample 0 only; the L target (rubric or false target) on every sample.",
    "Seeds not named in the brief: C1's EM starts and bootstrap random.Random(20261208); call order brief 23's random.Random(20261205).",
    "The run mode exited 1 after every call had finished: its final print refused the approval rule's free text in the summary "
    "(the print guard working); run-summary.json was written before the print, with every phase complete and none aborted. The run "
    "script was left unchanged so that its hash stays the one the items manifest pinned.",
]


def _f(x: Any, nd: int = 3) -> str:
    return lg._f(x, nd)


def render_md(res: Mapping[str, Any]) -> str:
    st, plan = res["stratum"], res["plan"]
    L: list[str] = ["# Brief 25: B3's comprehension-quiet stratum, v0 (blue; counts, aggregates and hashes only)\n"]
    L.append(f"**Comprehension-quiet stratum (A6.14.2): {st['n']} of the {st['of_quiet_set']} quiet candidates ({_f(st['share_of_quiet_set'])})**; "
             f"by writer {', '.join(f'{w} {n}' for w, n in st['by_writer'].items()) or 'none'}. Rule: Kimi K3 D_part = 0 on every one of "
             f"{res['samples_per_condition']} samples and Sol's mean D_part at or under {_f(plan['sol_rule']['threshold'], 2)} "
             f"({plan['sol_rule']['kind']} rule; stratum-plan.json, C1).\n")
    L.append(f"- Stratum ids sha256 `{st['ids_sha256']}` (the sorted ids joined by newlines; the ids are in stratum-v0.json).")
    L.append(f"- Membership of the 78: {', '.join(f'{k} {v}' for k, v in st['membership_counts'].items())}; share of the evaluable "
             f"{_f(st['share_of_evaluable'])}. Not quiet by writer: {st['not_quiet_by_writer']}; not evaluable by writer: {st['not_evaluable_by_writer']}.")
    L.append(f"- Resolved-anchor subset: {st['resolved_anchor_subset']['n_quiet']} of {st['resolved_anchor_subset']['n_items']} candidates whose "
             f"every replace anchor resolves in the day-0 text are in the stratum.")
    w = st["whole_credit_among_quiet"]
    L.append(f"- Within the stratum, the whole is credited (D_whole > 0 under both readers) on {w['D_whole_positive_both_readers']} items and "
             f"on no sample under either reader on {w['D_whole_zero_every_sample_both_readers']} (quiet-but-illegible, A6.16.3's by-product).")
    b = st["beside"]
    g = b["glm_written"]
    L.append(f"- Beside: Kimi K3's rule alone {b['kimi_alone_quiet']}; Sol's rule alone {b['sol_alone_quiet']}; both quiet at sample 0 alone "
             f"{b['sample0_both_quiet']} (the T1 proxy's form; T1 at one sample: 12 of 48). GLM-written candidates ({g['n']}): stratum rule "
             f"{g['stratum_rule']}, Kimi K3 and Sonnet 5.5 (every sample) {g['kimi_and_sonnet55']}, all three {g['all_three']}, Sonnet 5.5 alone "
             f"{g['sonnet55_alone_quiet']} (not evaluable under Sonnet 5.5: {g['sonnet55_not_evaluable']}).")
    L.append(f"- C1's expectation (not a bar): at the chosen rule, P(labelled quiet | truly quiet) {_f(plan['p_quiet'])} {_f(plan['p_quiet_ci95'])} "
             f"and P(labelled quiet | not quiet) {_f(plan['p_nonquiet'])} {_f(plan['p_nonquiet_ci95'])}; the T1 model expectation "
             f"{_f(plan['t1_expected_share'])}.\n")
    L.append("## Per reader and regime (mean over items of the per-item mean over samples)\n")
    L.append("| reader | regime | items | evaluable | D_part | D_whole | quiet under the reader's rule | D_part = 0, s0 / s1 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for f, per in res["by_reader_regime"].items():
        for gname, x in per.items():
            ps = " / ".join(_f(x["per_sample"][s]["share_D_part_zero"]) for s in sorted(x["per_sample"]))
            L.append(f"| {lg.FAMILIES[f]['name']} | {gname} | {x['n_items']} | {x['n_evaluable']} | {_f(x['D_part_mean'])} | {_f(x['D_whole_mean'])} | "
                     f"{_f(x['share_quiet_under_reader_rule'])} | {ps} |")
    L.append("\n## Not evaluable (a refused or missing part on some sample; never 0)\n")
    for f, x in res["not_evaluable"].items():
        L.append(f"- {lg.FAMILIES[f]['name']}: {x['n']} items ({x['by_regime'] or 'none'}; reasons {x['by_reason'] or 'none'}).")
    L.append("\n## Nulls: P(D_part > 0 | false target), controls and sham\n")
    L.append("| reader | set | items | per cell | any sample | reader's rule not quiet | D_whole > 0 per cell | paired s0: D_part > 0 / D_whole > 0 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for f in bc.PLAN_READERS:
        for gname, x in res["nulls"].get(f, {}).items():
            pp = x.get("paired_sample0")
            pps = f"{_f(pp['P_D_part_pos'])} / {_f(pp['P_D_whole_pos'])} (n {pp['n']})" if pp else "n/a"
            L.append(f"| {lg.FAMILIES[f]['name']} | {gname} | {x['n_items']} | {_f(x['P_D_part_pos_per_cell'])} | {_f(x['P_D_part_pos_any_sample'])} | "
                     f"{_f(x['P_reader_rule_not_quiet'])} | {_f(x['P_D_whole_pos_per_cell'])} | {pps} |")
    L.append(f"\nThe stratum rule applied to the 46 nulls against their false targets: {res['nulls']['stratum_rule_on_nulls']['membership_counts']}.\n")
    L.append("## Positive control (own edit, 20 candidates, sample 0)\n")
    for f, x in res["positive_control"].items():
        L.append(f"- {lg.FAMILIES[f]['name']}: D_whole_own {_f(x['D_whole_own'])} (n {x['n_D_whole']}), D_part_own {_f(x['D_part_own'])} "
                 f"(n {x['n_D_part']}), mean over parts {_f(x['mean_over_parts_own'])}.")
    L.append("\n## Reliability\n")
    for f, x in res["kappa"].items():
        sa = res["sample_agreement"][f]
        L.append(f"- {lg.FAMILIES[f]['name']}: scorer pass kappa {_f(x['kappa'])} (n {x['n_pass_pairs']}, agreement {_f(x['agreement'])}); candidates' "
                 f"quiet status flips between samples {sa['quiet_flips']} of {sa['n']} ({_f(sa['flip_rate'])}; T1 retest: "
                 f"{bc.EXPECTED_FLIPS[f]} of 10), D_part equal on both samples {_f(sa['share_equal'])}.")
    L.append("\n## Reader and scorer outcomes\n")
    L.append("Reader refusals (provider, DECLINED token or prose) and missing readings, summed over samples, per reader, regime and condition:\n")
    L.append("| reader | regime | " + " | ".join(bc.CONDS) + " |")
    L.append("|---|---|" + "---|" * len(bc.CONDS))
    agg: dict[tuple[str, str], Counter] = {}
    for key, per_cond in res["outcomes"]["reader"].items():
        f, _s, g = key.split(":")
        for c, cnt in per_cond.items():
            a = agg.setdefault((f, g), Counter())
            a[c] += sum(n for st, n in cnt.items() if st in REFUSED)
            a[c + ":missing"] += cnt.get("missing", 0)
    for (f, g), a in agg.items():
        L.append(f"| {lg.FAMILIES[f]['name']} | {g} | " + " | ".join(f"{a[c]} ({a[c + ':missing']} missing)" for c in bc.CONDS) + " |")
    L.append("\nScorer outcomes per target and pass are in stratum-v0.json (`outcomes`). Refused part readings: "
             + "; ".join(f"{lg.FAMILIES[f]['name']} {res['refusal_counts'][f]}" for f in bc.PLAN_READERS) + ".\n")
    L.append("## For brief 20 Part 3\n")
    L.append("stratum-v0.json `items` carries, per candidate by opaque id: membership, composition (two-pass mean, both passes), the rater top "
             "line and top-two gap, the replace share, and per reader the per-sample D_whole and D_part and the continuous D_part (mean over "
             "samples) for the interaction sensitivity.\n")
    L.append("## Hashes and spend\n")
    h = res["hashes"]
    L.append(f"- items-v0.json `{h['items_v0']}`; rubrics `{h['rubrics']}`; stratum-plan.json `{h['stratum_plan']}`; config `{h['config']}`; "
             f"run script at items `{h['script_at_items']}`; report script `{h['report_script']}`.")
    L.append(f"- Caches (main checkout only): " + "; ".join(f"{k} `{v}`" for k, v in res["cache_sha256"].items()) + ".")
    L.append(f"- Spend: " + ", ".join(f"{k} ${v:.2f}" for k, v in res["dollars"].items()) + f" (dry run ${res['estimate_usd']:.2f}).\n")
    L.append("## Disclosures\n")
    L += [f"- {x}" for x in DISCLOSURES]
    L.append("\n## Deviations\n")
    L += [f"- {x}" for x in DEVIATIONS]
    return "\n".join(L) + "\n"


def caches(out_dir: Path, routes: Mapping[str, Any]) -> tuple[dict[str, Path], Path]:
    return ({f: lg.reader_cache(out_dir, f, routes["chosen"][f]["model"]) for f in lg.FAMILIES}, lg.scorer_cache(out_dir))


def build_report(rec: Any, items: Mapping[str, Any], plan: Mapping[str, Any], comp: Mapping[str, Mapping[str, Any]]) -> dict:
    rows = items["items"]
    k = int(items["samples_per_condition"])
    table = item_table(rec, rows, items, comp)
    ch = plan["choice"]
    return {"version": VERSION, "samples_per_condition": k, "stratum": stratum_summary(table), "not_evaluable": not_evaluable(table),
            "by_reader_regime": by_reader_regime(table), "nulls": null_figures(table), "positive_control": positive_control(table),
            "sample_agreement": sample_agreement(table), "kappa": kappas(rec), "outcomes": outcome_tables(rec, rows, k),
            "refusal_counts": {f: sum(1 for d in table.values() if f in d["readers"] for x in d["readers"][f]["samples"]
                                      if x["D_part_status"] in REFUSED) for f in bc.PLAN_READERS},
            "plan": {"sol_rule": ch["sol_rule"], "p_quiet": ch["p_labelled_quiet_given_quiet"], "p_quiet_ci95": ch["ci95"],
                     "p_nonquiet": ch["p_labelled_quiet_given_not_quiet"], "p_nonquiet_ci95": ch["ci95_not_quiet"],
                     "t1_expected_share": plan["t1_expectation_only"]["model_expected_share_at_choice"]},
            "items": per_item_json(table)}


def mode_report(ns: argparse.Namespace) -> int:
    out_dir = Path(ns.out_dir)
    items, rows, _rub = bc.load_items(out_dir)
    plan = bc.load_plan(out_dir)
    if items["stratum_plan_sha256"] != lg.file_sha256(out_dir / "stratum-plan.json"):
        raise SystemExit("refusing: stratum-plan.json differs from the one the items were built on")
    routes = json.loads((out_dir / "routes-v0.json").read_text())
    rfiles, sfile = caches(out_dir, routes)
    rec = bc.B3Records({f: lg.read_jsonl(p) for f, p in rfiles.items()}, lg.read_jsonl(sfile))
    quiet, quiet_inputs = bc.quiet_set()
    if quiet_inputs != items["quiet_set_inputs_sha256"]:
        raise SystemExit("refusing: the quiet set's inputs changed since the items were built")
    key_b3 = json.loads(Path(ns.key_b3).read_text(encoding="utf-8"))
    res = build_report(rec, items, plan, composition_by_id(key_b3, quiet))
    res["cache_sha256"] = {**{f: lg.file_sha256(p) if p.exists() else None for f, p in rfiles.items()},
                           "scorer": lg.file_sha256(sfile) if sfile.exists() else None}
    res["dollars"] = {**{f: round(sum(float(x.get("cost_usd") or 0) for x in lg.read_jsonl(p)), 4) for f, p in rfiles.items()},
                      "scorer": round(sum(float(x.get("cost_usd") or 0) for x in lg.read_jsonl(sfile)), 4), "routes": lg.route_ledger_usd(out_dir)}
    res["dollars"]["total"] = round(sum(res["dollars"].values()), 4)
    est = json.loads((out_dir / "estimate-v0.json").read_text())
    res["estimate_usd"] = est["total_usd"]
    res["hashes"] = {"items_v0": lg.file_sha256(out_dir / "items-v0.json"), "rubrics": items["rubrics_sha256"],
                     "stratum_plan": items["stratum_plan_sha256"], "config": items["config_sha256"], "script_at_items": items["script_sha256"],
                     "run_script_now": lg.file_sha256(HERE / "stage3_b3_comprehension.py"), "report_script": lg.file_sha256(Path(__file__)),
                     "prompt_sha256": lg.prompt_hashes()}
    res["routes"] = routes["chosen"]
    res["disclosures"], res["deviations"] = DISCLOSURES, DEVIATIONS
    (out_dir / "stratum-v0.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (out_dir / "stratum-v0.md").write_text(render_md(res), encoding="utf-8")
    st = res["stratum"]
    lg.emit({"stratum_n": st["n"], "of": st["of_quiet_set"], "by_writer": st["by_writer"], "membership": st["membership_counts"],
             "stratum_ids_sha256": st["ids_sha256"], "stratum_json_sha256": lg.file_sha256(out_dir / "stratum-v0.json"),
             "stratum_md_sha256": lg.file_sha256(out_dir / "stratum-v0.md"), "dollars": res["dollars"]})
    return 0


# ── the T1 join (A6.14.5, exploratory) ─────────────────────────────────────────────────────────────

def t1_line_join(per_part: Mapping[str, Any], t1_items: Mapping[str, Any], t1_triples: Sequence[Mapping[str, Any]],
                 key07k: Mapping[str, Any], ratings07k: Mapping[str, Any], statements07k: Sequence[Mapping[str, Any]]) -> list[dict]:
    """One record per T1 test line: regime, the rater's two passes, and each family's D_part_line at r0 (None when the
    part was not scored). A line is matched to 07k's statement of the same payload by (op, anchor_or_region, text)."""
    tri = {t["triple_id"]: t for t in t1_triples}
    st07 = {s["statement_id"]: (s["op"], s["anchor_or_region"], s["text"]) for s in statements07k}
    by_payload: dict[tuple[str, str, str], list[str]] = {}
    for sid, v in key07k["statements"].items():
        by_payload.setdefault((Path(v["file"]).name, str(v.get("arm")), v["payload_id"]), []).append(sid)
    out = []
    for row in t1_items["items"]:
        g = row["regime"]
        if g not in T1_FILE:
            continue
        ref = row["payload_ref"]
        cands = by_payload.get((T1_FILE[g], T1_ARM[g], ref["id"]), [])
        for j, st in enumerate(tri[row["item_id"]]["statements"]):
            want = (st["op"], st["anchor_or_region"], st["text"])
            hits = [sid for sid in cands if st07.get(sid) == want]
            if len(hits) != 1:
                raise ValueError(f"line {j} of a {g} item matches {len(hits)} rated statements")
            r = ratings07k["statements"][hits[0]]
            p1, p2 = float(r["pass1"]["score"]), float(r["pass2"]["score"])
            cond = bc.PARTS[j]
            dl = {f: per_part[f][row["item_id"]]["r0"][cond]["score"] for f in per_part}
            out.append({"item_id": row["item_id"], "regime": g, "part": cond, "rater_p1": p1, "rater_p2": p2, "rater_mean": (p1 + p2) / 2,
                        "D_part_line": dl, "status": {f: per_part[f][row["item_id"]]["r0"][cond]["status"] for f in per_part}})
    return out


def join_summary(lines: Sequence[Mapping[str, Any]], families: Sequence[str], score_key: str = "rater_mean") -> dict:
    out: dict[str, Any] = {}
    for g in tuple(T1_FILE) + ("pooled",):
        ls = [x for x in lines if g == "pooled" or x["regime"] == g]
        quiet = [x for x in ls if x[score_key] <= RATER_BAR]
        loud = [x for x in ls if x[score_key] > RATER_BAR]

        def yields(xs):
            ok = [x for x in xs if sum(1 for f in families if x["D_part_line"][f] is not None) >= 2]
            hit = [x for x in ok if sum(1 for f in families if (x["D_part_line"][f] or 0) > 0) >= 2]
            return {"n_lines": len(xs), "n_with_two_families": len(ok), "n_yield_alone": len(hit), "share": len(hit) / len(ok) if ok else None}
        sp = {}
        for f in families:
            pr = [(x[score_key], x["D_part_line"][f]) for x in ls if x["D_part_line"][f] is not None]
            sp[f] = {"n": len(pr), "spearman": lg.spearman([a for a, _ in pr], [b for _, b in pr]) if len(pr) >= 3 else None}
        pm = [(x[score_key], sum(v for v in x["D_part_line"].values() if v is not None) / sum(1 for v in x["D_part_line"].values() if v is not None))
              for x in ls if sum(1 for v in x["D_part_line"].values() if v is not None) >= 2]
        sp["mean_over_families"] = {"n": len(pm), "spearman": lg.spearman([a for a, _ in pm], [b for _, b in pm]) if len(pm) >= 3 else None}
        out[g] = {"n_lines": len(ls), "at_or_under_60": yields(quiet), "over_60": yields(loud), "spearman_line_score_vs_D_part_line": sp}
    return out


def render_join_md(res: Mapping[str, Any]) -> str:
    L = ["# Brief 25: the T1 join (A6.14.5, exploratory; counts only)\n",
         "Brief 23's per-line D_part (r0, one sample, the item's own rubric; re-emitted through stage3_legibility.py's report mode) joined "
         "to 07k's section-2 line scores (the rater's standalone visibility, two-pass mean primary, pass 1 beside). A line yields the "
         "consequence alone when its D_part_line is above 0 under at least two of the three reader families (lines with fewer than two "
         "families scored are left out and counted). A hypothesis for the paper, never a sentence, until it is weighed.\n"]
    for label, key in (("two-pass mean", "primary"), ("pass 1", "pass1_beside")):
        L.append(f"## Rater line score: {label}\n")
        L.append("| regime | lines | at or under 60: yield alone / with two families | over 60: yield alone / with two families | "
                 "Spearman (Kimi K3, Sol, Sonnet 5.5, mean) |")
        L.append("|---|---|---|---|---|")
        for g, x in res[key].items():
            q, o, sp = x["at_or_under_60"], x["over_60"], x["spearman_line_score_vs_D_part_line"]
            L.append(f"| {g} | {x['n_lines']} | {q['n_yield_alone']} / {q['n_with_two_families']} ({_f(q['share'])}) | "
                     f"{o['n_yield_alone']} / {o['n_with_two_families']} ({_f(o['share'])}) | "
                     f"{_f(sp['kimi']['spearman'])}, {_f(sp['sol']['spearman'])}, {_f(sp['sonnet55']['spearman'])}, {_f(sp['mean_over_families']['spearman'])} |")
        L.append("")
    L.append(f"Line statuses (r0, per family): {res['statuses']}.\n")
    L.append("## Hashes\n")
    L += [f"- {k}: `{v}`" for k, v in res["hashes"].items()]
    L.append("\n## Deviations\n")
    L.append("- None from A6.14.5's route: the per-line scores came through the report mode's re-emit (`--per-part-out`), checked against "
             "instrument-v0.json's per-item D_part on every item, repeat and family, and the cache hashes equal brief 23's recorded ones.")
    L.append("- The join is on r0 only (one sample per line), as brief 23 ran; 07k's statement for a line is found within the line's own "
             "payload by its rendered fields.")
    return "\n".join(L) + "\n"


def mode_t1_join(ns: argparse.Namespace) -> int:
    out_dir = Path(ns.out_dir)
    pp_path = Path(ns.per_part)
    per_part_doc = json.loads(pp_path.read_text(encoding="utf-8"))
    instrument = json.loads(bc.INSTRUMENT_JSON.read_text(encoding="utf-8"))
    if per_part_doc["cache_sha256"] != instrument["cache_sha256"]:
        raise SystemExit("refusing: the re-emit was not made from brief 23's recorded caches")
    per_part = per_part_doc["per_part"]
    bad = 0
    for f, per in per_part.items():   # the re-emit's maxima are brief 23's recorded D_part
        for i, d in per.items():
            for r in ("r0", "r1"):
                if r in d:
                    parts = [d[r][c]["score"] for c in bc.PARTS]
                    dp = None if any(x is None for x in parts) else max(parts)
                    bad += dp != instrument["per_family"][f]["items"][i][r]["D_part"]
    if bad:
        raise SystemExit(f"refusing: the re-emit differs from instrument-v0.json on {bad} readings")
    load = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))  # noqa: E731
    t1_items = load(bc.S3 / "legibility" / "items-v0.json")
    files = {"key": T1_RATER / "key.json", "ratings": T1_RATER / "ratings.json", "statements": T1_RATER / "stripped-statements.json",
             "triples": T1_RATER / "stripped-triples.json"}
    lines = t1_line_join(per_part, t1_items, load(files["triples"]), load(files["key"]), load(files["ratings"]), load(files["statements"]))
    fams = sorted(per_part)
    res = {"version": f"{VERSION}/t1-join", "n_lines": len(lines), "families": fams,
           "primary": join_summary(lines, fams), "pass1_beside": join_summary(lines, fams, "rater_p1"),
           "statuses": {f: dict(sorted(Counter(x["status"][f] for x in lines).items())) for f in fams},
           "lines": [{k: v for k, v in x.items()} for x in lines],
           "hashes": {"per_part": lg.file_sha256(pp_path), "instrument_v0_json": lg.file_sha256(bc.INSTRUMENT_JSON),
                      "t1_items_v0": lg.file_sha256(bc.S3 / "legibility" / "items-v0.json"),
                      **{f"07k_{k}": lg.file_sha256(p) for k, p in files.items()}, "report_script": lg.file_sha256(Path(__file__)),
                      "stage3_legibility": lg.file_sha256(HERE / "stage3_legibility.py")}}
    (out_dir / "t1-join-v0.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    (out_dir / "t1-join-v0.md").write_text(render_join_md(res), encoding="utf-8")
    p = res["primary"]["pooled"]
    lg.emit({"n_lines": len(lines), "pooled_at_or_under_60": p["at_or_under_60"], "pooled_over_60": p["over_60"],
             "t1_join_json_sha256": lg.file_sha256(out_dir / "t1-join-v0.json"), "t1_join_md_sha256": lg.file_sha256(out_dir / "t1-join-v0.md")})
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 25 C3: the stratum report and the T1 join")
    ap.add_argument("mode", choices=("report", "t1-join"))
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--key-b3", default=str(bc.S3 / "b3" / "rater" / "key-b3.json"))
    ap.add_argument("--per-part", default=str(OUT / "t1-per-part-v0.json"))
    ns = ap.parse_args(argv)
    fn = {"report": mode_report, "t1-join": mode_t1_join}[ns.mode]
    try:
        return fn(ns)
    except SystemExit:
        raise
    except Exception as exc:   # print the type only; the traceback (which may quote a value) goes to a file
        out = Path(ns.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        with (out / "errors.log").open("a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
        print(json.dumps({"error": type(exc).__name__, "mode": ns.mode, "traceback": "errors.log"}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
