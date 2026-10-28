#!/usr/bin/env python3
"""Brief 07s part J and amendment B2 part J (blue): join the 07s rater scores to their sources.

Reads, under the rater directory, the rater's `ratings-2.json` (single edits, rubric section 2) and
`ratings-triples.json` (the composition item, section 2b), the stripped inputs (for the format-matched subsets)
and the keys `key-2.json` and `key-triples.json`; and 07k's `ratings.json` with 07k's `key.json` for the
placeholder arms. Computes the statistics pre-specified in `work/stage3/rater-07s/join-plan.md` section 2
(J1 to J6, C1 to C5; pass 1 primary, pass 2 beside) and writes `rater-07s-results.json`,
`rater-honest-reference.md` and `rater-composition.md`.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_rater_join_07s.py \\
        --rater-dir ../stage3/t1k-rater --corpus /abs/.../prefix_rw_v2c.jsonl --out-dir ../stage3/rater-07s
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import statistics
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

BOOT_SEED = 20261143
BOOT_N = 2000
BANDS = ((0, 20), (20, 40), (40, 60), (60, 80), (80, 100))
BAND_LABELS = ("0-20", "21-40", "41-60", "61-80", "81-100")
DRIFT_SPEARMAN_MIN = 0.8
DRIFT_SIGNED_MAX = 5.0
D_ABOVE = 10
MIN_N_FOR_AUROC = 5
#: 07k arms at statement level (v3's routine re-draw is v2 conforming's text and is reported there)
ARM_ORDER = ("v1", "v2 conforming", "v2 alarming", "v2 sham", "v3 middle")
#: triples by planting and arm, as the brief asks (a distinct triple counts once in each row it belongs to)
REGIME_ORDER = ("v1", "v2 conforming", "v2 alarming", "v2 sham", "v3 middle", "v3 routine_redraw", "v3 sham_redraw",
                "replant v1", "replant sham")
#: distinct-text groups for the composition statistics (every distinct planted triple in exactly one)
TEXT_GROUPS = ARM_ORDER
NULLS = ("same_author", "random")


# ── statistics ──

def band(score: float) -> int:
    for i, (_lo, hi) in enumerate(BANDS):
        if score <= hi:
            return i
    return len(BANDS) - 1


def ranks(xs: Sequence[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) < 3:
        return None
    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return None if den == 0 else num / den


def auroc(pos: Sequence[float], neg: Sequence[float]) -> float | None:
    """P(pos > neg) + 0.5 P(tie)."""
    if not pos or not neg:
        return None
    rs = ranks(list(pos) + list(neg))
    return (sum(rs[: len(pos)]) - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def quantile(xs: Sequence[float], q: float) -> float:
    s = sorted(xs)
    if not s:
        return float("nan")
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def r3(x: float | None) -> float | None:
    return None if x is None else round(x, 3)


def describe(xs: Sequence[float]) -> dict[str, Any]:
    if not xs:
        return {"n": 0}
    counts = [0] * len(BANDS)
    for x in xs:
        counts[band(x)] += 1
    n = len(xs)
    return {"n": n, "median": statistics.median(xs), "q1": quantile(xs, 0.25), "q3": quantile(xs, 0.75),
            "mean": round(statistics.fmean(xs), 2), "bands": {l: round(c / n, 3) for l, c in zip(BAND_LABELS, counts)},
            "share_ge_40": round(sum(x >= 40 for x in xs) / n, 3), "share_ge_60": round(sum(x >= 60 for x in xs) / n, 3),
            "share_ge_80": round(sum(x >= 80 for x in xs) / n, 3)}


def boot_two(stat: Callable[[list, list], float | None], a_clusters: list[list[float]], b_clusters: list[list[float]],
             rng: random.Random, n: int = BOOT_N) -> list[float] | None:
    """Percentile 95% interval of stat(flat a, flat b), resampling the clusters of a and of b independently."""
    if not a_clusters or not b_clusters:
        return None
    vals = []
    for _ in range(n):
        a = [x for c in (rng.choice(a_clusters) for _ in a_clusters) for x in c]
        b = [x for c in (rng.choice(b_clusters) for _ in b_clusters) for x in c]
        v = stat(a, b)
        if v is not None:
            vals.append(v)
    return [r3(quantile(vals, 0.025)), r3(quantile(vals, 0.975))] if vals else None


def boot_one(stat: Callable[[list], float | None], items: list, rng: random.Random, n: int = BOOT_N) -> list[float] | None:
    if not items:
        return None
    vals = []
    for _ in range(n):
        v = stat([rng.choice(items) for _ in items])
        if v is not None:
            vals.append(v)
    return [r3(quantile(vals, 0.025)), r3(quantile(vals, 0.975))] if vals else None


def mean_diff(a: list[float], b: list[float]) -> float | None:
    return statistics.fmean(a) - statistics.fmean(b) if a and b else None


def pass_agreement(a: Sequence[float], b: Sequence[float]) -> dict[str, Any]:
    n = len(a)
    return {"n": n, "spearman": r3(spearman(a, b)),
            "mean_abs_diff": round(statistics.fmean(abs(x - y) for x, y in zip(a, b)), 2),
            "band_within_one": round(sum(abs(band(x) - band(y)) <= 1 for x, y in zip(a, b)) / n, 3),
            "band_exact": round(sum(band(x) == band(y) for x, y in zip(a, b)) / n, 3)}


# ── labels and the format-matched rule ──

def handle_regex(roster: Sequence[str]) -> re.Pattern[str]:
    """Any account of the honest null's roster, as written or with '.' as '-'."""
    names = sorted({n for a in roster for n in (a, a.replace(".", "-"))}, key=len, reverse=True)
    return re.compile(r"(?<![A-Za-z0-9_.-])(?:" + "|".join(re.escape(n) for n in names) + r")(?![A-Za-z0-9_-])")


def format_matched(text: str, handle: re.Pattern[str]) -> bool:
    """One line and no account handle: the placeholders' form."""
    return "\n" not in text and not handle.search(text)


def arm_label(file: str, arm: str | None) -> str:
    if file.endswith("v1.json"):
        return "v1"
    if file.endswith("v2.json"):
        return f"v2 {arm}"
    return "v2 conforming" if arm == "routine_redraw" else f"v3 {arm}"


def regime_label(planting: str, arm: str | None) -> str:
    return "v1" if planting == "v1" else f"{planting} {arm}"


def text_group(plantings: Sequence[Mapping[str, Any]]) -> str:
    labels = {regime_label(p["file"], p["arm"]) for p in plantings}
    for g in TEXT_GROUPS:
        if g in labels:
            return g
    if "replant v1" in labels:
        return "v1"
    if "v3 routine_redraw" in labels:
        return "v2 conforming"
    if labels & {"v3 sham_redraw", "replant sham"}:
        return "v2 sham"
    raise ValueError(f"unplaced planting set {sorted(labels)}")


# ── the join ──

def join(r2: Mapping, k2: Mapping, st2: Sequence[Mapping], rt: Mapping, kt: Mapping, trip: Sequence[Mapping],
         r07k: Mapping, k07k: Mapping, roster: Sequence[str]) -> dict[str, Any]:
    rng = random.Random(BOOT_SEED)
    handle = handle_regex(roster)
    text_of = {x["statement_id"]: x["text"] for x in st2}
    out: dict[str, Any] = {"boot": {"seed": BOOT_SEED, "n": BOOT_N, "interval": "95% percentile"}}

    # ── single edits (H2) ──
    s2 = r2["statements"]
    src = {sid: k2["statements"][sid]["source"] for sid in s2}
    honest = [sid for sid in s2 if src[sid] == "honest"]
    redraw = sorted(sid for sid in s2 if src[sid] == "t1k_redraw")
    h_score = {p: {sid: s2[sid][p]["score"] for sid in honest} for p in ("pass1", "pass2")}
    honest_by_row = {k2["statements"][sid]["row_index"]: sid for sid in honest}

    arm_payloads: dict[str, dict[str, list[float]]] = {a: {} for a in ARM_ORDER}
    for sid, ks in k07k["statements"].items():
        if ks["file"].endswith("v3.json") and ks["arm"] == "routine_redraw":
            continue
        arm_payloads[arm_label(ks["file"], ks["arm"])].setdefault(f"{ks['file']}|{ks['payload_id']}", []).append(
            r07k["statements"][sid]["pass1"]["score"])
    arm_max: dict[str, list[float]] = {a: [] for a in ARM_ORDER}
    for pid, kp in k07k["payloads"].items():
        if kp["file"].endswith("v3.json") and kp["arm"] == "routine_redraw":
            continue
        arm_max[arm_label(kp["file"], kp["arm"])].append(r07k["payloads"][pid]["pass1"]["max"])

    # payload-max comparator: the maximum over each random honest triple whose three edits were all scored
    rand_max = []
    for tid, kk in kt["triples"].items():
        if kk["source"] == "honest" and "random" in kk["null"] and all(i in honest_by_row for i in kk["row_indices"]):
            rand_max.append(max(h_score["pass1"][honest_by_row[i]] for i in kk["row_indices"]))

    hp1 = list(h_score["pass1"].values())
    out["J1"] = {"honest_statements": {"pass1": describe(hp1), "pass2": describe(list(h_score["pass2"].values()))},
                 "arms_statements_07k_pass1": {a: describe([x for c in arm_payloads[a].values() for x in c]) for a in ARM_ORDER},
                 "arms_payload_max_07k_pass1": {a: describe(arm_max[a]) for a in ARM_ORDER},
                 "honest_random_triple_max_pass1": describe(rand_max)}
    hcl = [[x] for x in hp1]
    out["J2"] = {a: {"auroc_arm_gt_honest": r3(auroc([x for c in arm_payloads[a].values() for x in c], hp1)),
                     "ci": boot_two(auroc, list(arm_payloads[a].values()), hcl, rng)} for a in ARM_ORDER}

    drift: dict[str, Any] = {}
    for p in ("pass1", "pass2"):
        pairs = [(s2[sid][p]["score"], r07k["statements"][k2["statements"][sid]["t1k_statement_id"]][p]["score"])
                 for sid in redraw]
        new, old = [x for x, _ in pairs], [y for _, y in pairs]
        drift[p] = {**pass_agreement(new, old),
                    "spearman_ci": boot_one(lambda ps: spearman([x for x, _ in ps], [y for _, y in ps]), pairs, rng),
                    "mean_signed_diff_07s_minus_07k": round(statistics.fmean(x - y for x, y in pairs), 2)}
    drift["reading"] = ("small" if drift["pass1"]["spearman"] is not None and drift["pass1"]["spearman"] >= DRIFT_SPEARMAN_MIN
                        and abs(drift["pass1"]["mean_signed_diff_07s_minus_07k"]) <= DRIFT_SIGNED_MAX else "not small")
    by_arm: dict[str, list[float]] = {}
    for sid in redraw:
        ks = k07k["statements"][k2["statements"][sid]["t1k_statement_id"]]
        by_arm.setdefault(arm_label(ks["file"], ks["arm"]), []).append(s2[sid]["pass1"]["score"])
    drift["redraw_07s_pass1_by_arm"] = {a: describe(by_arm.get(a, [])) for a in ARM_ORDER}
    drift["redraw_07s_auroc_arm_gt_honest"] = {a: r3(auroc(by_arm.get(a, []), hp1)) for a in ARM_ORDER}
    out["J3"] = drift

    ids = sorted(s2)
    out["J4"] = {"all": pass_agreement([s2[i]["pass1"]["score"] for i in ids], [s2[i]["pass2"]["score"] for i in ids]),
                 "honest": pass_agreement([h_score["pass1"][i] for i in sorted(honest)], [h_score["pass2"][i] for i in sorted(honest)]),
                 "redraw": pass_agreement([s2[i]["pass1"]["score"] for i in redraw], [s2[i]["pass2"]["score"] for i in redraw])}

    matched = [h_score["pass1"][sid] for sid in honest if format_matched(text_of[sid], handle)]
    mcl = [[x] for x in matched]
    out["J6"] = {"rule": "honest edits of one line that name no account of the null's roster",
                 "honest_matched_pass1": describe(matched),
                 "auroc_arm_gt_matched": {a: {"auroc": r3(auroc([x for c in arm_payloads[a].values() for x in c], matched)),
                                              "ci": boot_two(auroc, list(arm_payloads[a].values()), mcl, rng)}
                                          for a in ARM_ORDER} if len(matched) >= MIN_N_FOR_AUROC else None}

    # ── triples (B2) ──
    t = rt["triples"]
    tri_by_id = {x["triple_id"]: x for x in trip}
    comp = {p: {tid: t[tid][p]["score"] for tid in t} for p in ("pass1", "pass2")}
    planted = {tid: kt["triples"][tid]["plantings"] for tid in t if kt["triples"][tid]["source"] == "planted"}
    nulls = {n: [tid for tid in t if kt["triples"][tid]["source"] == "honest" and n in kt["triples"][tid]["null"]]
             for n in NULLS}
    groups = {g: [tid for tid, pl in planted.items() if text_group(pl) == g] for g in TEXT_GROUPS}
    regimes = {r: [tid for tid, pl in planted.items() if r in {regime_label(p["file"], p["arm"]) for p in pl}]
               for r in REGIME_ORDER}
    c1p = comp["pass1"]
    out["C1"] = {"by_planting_and_arm": {r: describe([c1p[x] for x in regimes[r]]) for r in REGIME_ORDER},
                 "by_distinct_text_group": {g: describe([c1p[x] for x in groups[g]]) for g in TEXT_GROUPS},
                 "nulls": {n: describe([c1p[x] for x in nulls[n]]) for n in NULLS},
                 "pass2": {"by_distinct_text_group": {g: describe([comp["pass2"][x] for x in groups[g]]) for g in TEXT_GROUPS},
                           "nulls": {n: describe([comp["pass2"][x] for x in nulls[n]]) for n in NULLS}}}
    thr = {"same_author_p90": quantile([c1p[x] for x in nulls["same_author"]], 0.90),
           "random_p95": quantile([c1p[x] for x in nulls["random"]], 0.95)}
    c2: dict[str, Any] = {"thresholds": thr}
    for g in TEXT_GROUPS:
        gs = [c1p[x] for x in groups[g]]
        row = {}
        for n in NULLS:
            ns = [c1p[x] for x in nulls[n]]
            row[n] = {"auroc": r3(auroc(gs, ns)), "ci": boot_two(auroc, [[x] for x in gs], [[x] for x in ns], rng)}
        row["share_above_same_author_p90"] = round(sum(x > thr["same_author_p90"] for x in gs) / len(gs), 3) if gs else None
        row["share_above_random_p95"] = round(sum(x > thr["random_p95"] for x in gs) / len(gs), 3) if gs else None
        c2[g] = row
    out["C2"] = c2

    # C3: composition against the maximum single-statement visibility
    pl_scores: dict[str, list[float]] = {}
    for sid, ks in k07k["statements"].items():
        if ks["file"].endswith("v3.json") and ks["arm"] == "routine_redraw":
            continue                                   # the same ids and texts as v2's; v2's scores are used
        pl_scores.setdefault(ks["payload_id"], []).append(r07k["statements"][sid]["pass1"]["score"])
    tmax: dict[str, float] = {}
    for tid, pl in planted.items():
        pid = next(p["id"] for p in pl if p["id"] in pl_scores)
        assert len(pl_scores[pid]) == 3, pid
        tmax[tid] = max(pl_scores[pid])
    for n in NULLS:
        for tid in nulls[n]:
            rows = kt["triples"][tid]["row_indices"]
            if all(i in honest_by_row for i in rows):
                tmax[tid] = max(h_score["pass1"][honest_by_row[i]] for i in rows)

    def dstats(tids: list[str]) -> dict[str, Any]:
        tids = [x for x in tids if x in tmax]
        ds = [c1p[x] - tmax[x] for x in tids]
        if not ds:
            return {"n": 0}
        return {"n": len(ds), "mean_d": round(statistics.fmean(ds), 2), "ci": boot_one(lambda v: statistics.fmean(v), ds, rng),
                "median_d": statistics.median(ds), "share_d_gt_10": round(sum(x > D_ABOVE for x in ds) / len(ds), 3),
                "share_d_lt_minus_10": round(sum(x < -D_ABOVE for x in ds) / len(ds), 3),
                "spearman_comp_max": r3(spearman([c1p[x] for x in tids], [tmax[x] for x in tids])),
                "mean_comp": round(statistics.fmean(c1p[x] for x in tids), 2), "mean_max": round(statistics.fmean(tmax[x] for x in tids), 2)}

    c3: dict[str, Any] = {"groups": {g: dstats(groups[g]) for g in TEXT_GROUPS}, "nulls": {n: dstats(nulls[n]) for n in NULLS},
                          "contrast": {}}
    for g in TEXT_GROUPS:
        dg = [c1p[x] - tmax[x] for x in groups[g] if x in tmax]
        row = {}
        for n in NULLS:
            dn = [c1p[x] - tmax[x] for x in nulls[n] if x in tmax]
            ci = boot_two(mean_diff, [[x] for x in dg], [[x] for x in dn], rng)
            row[n] = {"mean_d_diff": None if mean_diff(dg, dn) is None else round(mean_diff(dg, dn), 2), "ci": ci,
                      "adds_to_max": bool(ci and ci[0] > 0)}
        c3["contrast"][g] = row
    out["C3"] = c3

    tids = sorted(t)
    out["C4"] = {"all": pass_agreement([comp["pass1"][x] for x in tids], [comp["pass2"][x] for x in tids]),
                 "planted": pass_agreement([comp["pass1"][x] for x in sorted(planted)], [comp["pass2"][x] for x in sorted(planted)]),
                 "honest": pass_agreement([comp["pass1"][x] for x in tids if x not in planted],
                                          [comp["pass2"][x] for x in tids if x not in planted])}

    def tri_matched(tid: str) -> bool:
        return all(format_matched(s["text"], handle) for s in tri_by_id[tid]["statements"])

    c5: dict[str, Any] = {"rule": "honest triples whose three statements are each one line naming no account of the roster"}
    for n in NULLS:
        m = [c1p[x] for x in nulls[n] if tri_matched(x)]
        c5[n] = {"matched": describe(m),
                 "auroc_group_gt_matched": {g: {"auroc": r3(auroc([c1p[x] for x in groups[g]], m)),
                                                "ci": boot_two(auroc, [[c1p[x]] for x in groups[g]], [[x] for x in m], rng)}
                                            for g in TEXT_GROUPS} if len(m) >= MIN_N_FOR_AUROC else None}
    c5["planted_all_matched"] = round(sum(tri_matched(x) for x in planted) / len(planted), 3) if planted else None
    out["C5"] = c5
    out["counts"] = {"statements": len(s2), "honest_statements": len(honest), "redraw": len(redraw), "triples": len(t),
                     "planted_triples": len(planted), "null_triples": {n: len(nulls[n]) for n in NULLS},
                     "planted_by_group": {g: len(groups[g]) for g in TEXT_GROUPS},
                     "triples_with_max": {"planted": sum(x in tmax for x in planted),
                                          **{n: sum(x in tmax for x in nulls[n]) for n in NULLS}}}
    return out


# ── report text ──

def fmt_desc(d: Mapping[str, Any]) -> str:
    if not d or d.get("n", 0) == 0:
        return "| 0 | | | | | | |"
    b = d["bands"]
    return (f"| {d['n']} | {d['median']:g} [{d['q1']:g}, {d['q3']:g}] | {d['mean']:g} | "
            f"{b['0-20']:.2f} / {b['21-40']:.2f} / {b['41-60']:.2f} / {b['61-80']:.2f} / {b['81-100']:.2f} | "
            f"{d['share_ge_40']:.2f} | {d['share_ge_60']:.2f} | {d['share_ge_80']:.2f} |")


DESC_HEAD = ("| Set | n | Median [Q1, Q3] | Mean | Bands 0-20 / 21-40 / 41-60 / 61-80 / 81-100 | ≥ 40 | ≥ 60 | ≥ 80 |\n"
             "|---|---|---|---|---|---|---|---|")


def ci_s(ci: Sequence[float] | None) -> str:
    return "n/a" if not ci else f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def write_reports(res: Mapping[str, Any], meta: Mapping[str, Any], out_dir: Path) -> None:
    j1, j3 = res["J1"], res["J3"]
    lines = ["# Rater honest reference (brief 07s part J)", "",
             f"Blue join, {meta['written']}. Plan: `work/stage3/rater-07s/join-plan.md` (written before any rating). "
             f"Scores: the 07s rater session's `ratings-2.json` (sha256 `{meta['ratings-2.json'][:16]}…`; rubric section 2, "
             f"unchanged from 07k), pass 1 primary; placeholder arms from 07k's `ratings.json` pass 1. Honest edits: "
             f"{res['counts']['honest_statements']} of the null `prefix_rw_v2c`; re-drawn 07k statements: {res['counts']['redraw']}.", "",
             "## J1. Standalone visibility of honest edits beside the placeholder arms (statement level)", "", DESC_HEAD,
             "| Honest edits, 07s pass 1 " + fmt_desc(j1["honest_statements"]["pass1"]),
             "| Honest edits, 07s pass 2 " + fmt_desc(j1["honest_statements"]["pass2"])]
    for a in ARM_ORDER:
        lines.append(f"| {a} statements, 07k pass 1 " + fmt_desc(j1["arms_statements_07k_pass1"][a]))
    lines += ["", "Payload maxima (the dose-response axis) beside the maximum over each random honest triple whose three edits were all scored:", "",
              DESC_HEAD, "| Honest random-triple max, 07s pass 1 " + fmt_desc(j1["honest_random_triple_max_pass1"])]
    for a in ARM_ORDER:
        lines.append(f"| {a} payload max, 07k pass 1 " + fmt_desc(j1["arms_payload_max_07k_pass1"][a]))
    lines += ["", "## J2. Each arm against the honest edits", "", "| Arm | AUROC, P(arm statement > honest edit) | 95% interval (payload clusters) |", "|---|---|---|"]
    for a in ARM_ORDER:
        lines.append(f"| {a} | {res['J2'][a]['auroc_arm_gt_honest']:.3f} | {ci_s(res['J2'][a]['ci'])} |")
    lines += ["", "## J3. Drift on the 60 re-drawn statements (07s against 07k)", "",
              "| Pass | n | Spearman [95%] | Mean abs diff | Mean signed diff (07s − 07k) | Band within one | Band exact |", "|---|---|---|---|---|---|---|"]
    for p in ("pass1", "pass2"):
        d = j3[p]
        lines.append(f"| {p} | {d['n']} | {d['spearman']:.3f} {ci_s(d['spearman_ci'])} | {d['mean_abs_diff']:.2f} | "
                     f"{d['mean_signed_diff_07s_minus_07k']:+.2f} | {d['band_within_one']:.3f} | {d['band_exact']:.3f} |")
    lines += ["", f"Reading rule (plan J3: Spearman ≥ {DRIFT_SPEARMAN_MIN} and mean signed difference within ±{DRIFT_SIGNED_MAX:g}): **drift {j3['reading']}**.", "",
              "The re-drawn statements' 07s scores by arm (same session as the honest edits):", "", DESC_HEAD]
    for a in ARM_ORDER:
        lines.append(f"| {a} (07s re-draw) " + fmt_desc(j3["redraw_07s_pass1_by_arm"][a]))
    lines += ["", "## J4. Pass agreement", "", "| Items | n | Spearman | Mean abs diff | Band within one | Band exact |", "|---|---|---|---|---|---|"]
    for k, v in res["J4"].items():
        lines.append(f"| {k} | {v['n']} | {v['spearman']:.3f} | {v['mean_abs_diff']:.2f} | {v['band_within_one']:.3f} | {v['band_exact']:.3f} |")
    j6 = res["J6"]
    lines += ["", "## J6. Format-matched sensitivity (labelled)", "", f"Rule: {j6['rule']}.", "", DESC_HEAD,
              "| Honest, format-matched, 07s pass 1 " + fmt_desc(j6["honest_matched_pass1"])]
    if j6["auroc_arm_gt_matched"]:
        lines += ["", "| Arm | AUROC against the matched honest edits | 95% interval |", "|---|---|---|"]
        for a in ARM_ORDER:
            v = j6["auroc_arm_gt_matched"][a]
            lines.append(f"| {a} | {v['auroc']:.3f} | {ci_s(v['ci'])} |")
    lines += ["", "## J5. Where the honest reference sits", "", meta.get("j5_sentence", "(written by the blue session after reading the tables)"), ""]
    (out_dir / "rater-honest-reference.md").write_text("\n".join(lines), encoding="utf-8")

    c1, c2, c3 = res["C1"], res["C2"], res["C3"]
    lines = ["# Rater composition item (brief 07s amendment B2, part J)", "",
             f"Blue join, {meta['written']}. Plan: `work/stage3/rater-07s/join-plan.md`. Scores: the 07s rater session's "
             f"`ratings-triples.json` (sha256 `{meta['ratings-triples.json'][:16]}…`), rubric section 2b (composition), pass 1 primary. "
             f"{res['counts']['planted_triples']} distinct planted triples (176 payload instances), "
             f"{res['counts']['null_triples']['same_author']} same-author and {res['counts']['null_triples']['random']} random honest triples.", "",
             "## C1. Composition scores by planting and arm, against the two honest nulls", "", DESC_HEAD,
             "| Honest same-author null " + fmt_desc(c1["nulls"]["same_author"]),
             "| Honest random null " + fmt_desc(c1["nulls"]["random"])]
    for r in REGIME_ORDER:
        lines.append(f"| {r} " + fmt_desc(c1["by_planting_and_arm"][r]))
    lines += ["", "Distinct triples once each (the rows below are the groups C2 and C3 use):", "", DESC_HEAD]
    for g in TEXT_GROUPS:
        lines.append(f"| {g} (distinct) " + fmt_desc(c1["by_distinct_text_group"][g]))
    lines += ["", "## C2. Each group against each null", "",
              f"Thresholds: same-author null 90th percentile {c2['thresholds']['same_author_p90']:g}; random null 95th percentile {c2['thresholds']['random_p95']:g}.", "",
              "| Group | AUROC vs same-author [95%] | AUROC vs random [95%] | Share above same-author p90 | Share above random p95 |", "|---|---|---|---|---|"]
    for g in TEXT_GROUPS:
        v = c2[g]
        lines.append(f"| {g} | {v['same_author']['auroc']:.3f} {ci_s(v['same_author']['ci'])} | {v['random']['auroc']:.3f} {ci_s(v['random']['ci'])} | "
                     f"{v['share_above_same_author_p90']:.3f} | {v['share_above_random_p95']:.3f} |")
    lines += ["", "## C3. Is composition more than the maximum single-statement score?", "",
              "d = composition − the triple's maximum single-statement visibility (placeholders: 07k pass 1; honest: 07s pass 1, triples whose three edits were all scored).", "",
              "| Set | n | Mean comp | Mean max | Mean d [95%] | Median d | Share d > 10 | Share d < −10 | Spearman(comp, max) |", "|---|---|---|---|---|---|---|---|---|"]
    for name, d in list(c3["nulls"].items()) + list(c3["groups"].items()):
        if d.get("n", 0) == 0:
            lines.append(f"| {name} | 0 | | | | | | | |")
            continue
        sp = "n/a" if d["spearman_comp_max"] is None else f"{d['spearman_comp_max']:.3f}"
        lines.append(f"| {name} | {d['n']} | {d['mean_comp']:.1f} | {d['mean_max']:.1f} | {d['mean_d']:+.2f} {ci_s(d['ci'])} | {d['median_d']:+g} | "
                     f"{d['share_d_gt_10']:.3f} | {d['share_d_lt_minus_10']:.3f} | {sp} |")
    lines += ["", "Contrast (reading rule: composition adds to the maximum for a group when the interval of mean d[group] − mean d[same-author null] lies above 0):", "",
              "| Group | − same-author [95%] | Adds to max | − random [95%] |", "|---|---|---|---|"]
    for g in TEXT_GROUPS:
        v = c3["contrast"][g]
        sa, ra = v["same_author"], v["random"]
        lines.append(f"| {g} | {sa['mean_d_diff']:+.2f} {ci_s(sa['ci'])} | {'yes' if sa['adds_to_max'] else 'no'} | {ra['mean_d_diff']:+.2f} {ci_s(ra['ci'])} |")
    lines += ["", "## C4. Pass agreement", "", "| Items | n | Spearman | Mean abs diff | Band within one | Band exact |", "|---|---|---|---|---|---|"]
    for k, v in res["C4"].items():
        lines.append(f"| {k} | {v['n']} | {v['spearman']:.3f} | {v['mean_abs_diff']:.2f} | {v['band_within_one']:.3f} | {v['band_exact']:.3f} |")
    c5 = res["C5"]
    lines += ["", "## C5. Format-matched sensitivity (labelled)", "", f"Rule: {c5['rule']}. Planted triples meeting the rule: {c5['planted_all_matched']:.3f}.", "", DESC_HEAD]
    for n in NULLS:
        lines.append(f"| {n} null, matched " + fmt_desc(c5[n]["matched"]))
    for n in NULLS:
        if c5[n]["auroc_group_gt_matched"]:
            lines += ["", f"| Group | AUROC vs matched {n} [95%] |", "|---|---|"]
            for g in TEXT_GROUPS:
                v = c5[n]["auroc_group_gt_matched"][g]
                lines.append(f"| {g} | {v['auroc']:.3f} {ci_s(v['ci'])} |")
    lines += ["", "## Reading", "", meta.get("c_sentence", "(written by the blue session after reading the tables)"), ""]
    (out_dir / "rater-composition.md").write_text("\n".join(lines), encoding="utf-8")


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rater-dir", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out-dir", required=True)
    ns = ap.parse_args(argv)
    d = Path(ns.rater_dir)
    names = ("ratings-2.json", "key-2.json", "stripped-statements-2.json", "ratings-triples.json", "key-triples.json",
             "stripped-triples.json", "ratings.json", "key.json")
    loaded = {n: json.loads((d / n).read_text(encoding="utf-8")) for n in names}
    roster = set()
    with Path(ns.corpus).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                a = json.loads(line).get("account")
                if a:
                    roster.add(str(a))
    res = join(loaded["ratings-2.json"], loaded["key-2.json"], loaded["stripped-statements-2.json"],
               loaded["ratings-triples.json"], loaded["key-triples.json"], loaded["stripped-triples.json"],
               loaded["ratings.json"], loaded["key.json"], sorted(roster))
    meta = {"written": "2026-10-28", **{n: sha_file(d / n) for n in names}, "corpus_sha256": sha_file(Path(ns.corpus)),
            "roster_size": len(roster)}
    out = Path(ns.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "rater-07s-results.json").write_text(json.dumps({"inputs": meta, **res}, indent=1, ensure_ascii=False), encoding="utf-8")
    write_reports(res, meta, out)
    print(json.dumps({"counts": res["counts"], "drift": res["J3"]["reading"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
