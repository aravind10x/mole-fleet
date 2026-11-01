#!/usr/bin/env python3
"""Brief 25 (B3's comprehension run, for brief 15 A6.14): the comprehension-quiet stratum and the T1 join.

Script-only. Every mode prints counts, ids, hashes and dollars through stage3_legibility's `emit`, which refuses any
string with a space in it; the clients run without logging and an unexpected error prints only its type (the
traceback goes to errors.log). No item line, declared effect, answer or scorer reason is ever printed. The instrument
is brief 23's, imported unchanged from stage3_legibility (the reader and scorer prompts, the rendering, the parsers and
the clients; their hashes are checked against brief 23's items-v0.json). Modes, in order:

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_comprehension.py plan
        C1 ($0): stratum-plan.json, the sample count and Sol's rule from brief 23's retest pairs
    ... stage3_b3_comprehension.py items      items-v0.json (ids, regimes, targets, draws, hashes; no text) and
                                              rubrics-v0.json (main checkout only; never printed)
    ... stage3_b3_comprehension.py prices     models-v0.json: OpenRouter list prices (a public GET, no model call)
    ... stage3_b3_comprehension.py dry-run    estimate-v0.json
    ... stage3_b3_comprehension.py routes --approved-usd X    one "Say OK." call per route
    ... stage3_b3_comprehension.py dry-run    again, priced on the routes found
    ... stage3_b3_comprehension.py run --approved-usd X [--resume]   controls and sham first, then the candidates;
                                              stops at twice X
    ... stage3_b3_comprehension.py report     stratum-v0.md and stratum-v0.json
    ... stage3_b3_comprehension.py t1-join --per-part PATH    t1-join-v0.md and t1-join-v0.json (A6.14.5)

C1's model (the plan mode). The retest pairs alone are ten test items per reader, and a per-item rate from one sample
is degenerate (an item quiet once looks quiet always). The plan therefore fits a two-class latent class model to all
48 T1 test items of brief 23: an item is truly quiet (class Q) or not (class N); each reader's D_part on one sample
(0, 0.5 or 1) is a draw from that reader's categorical distribution for the item's class, independently across
samples and readers given the class. The r0 readings of three readers on 48 items and the r1 readings on the ten
retest items identify the model (three conditionally independent indicators). Fit by EM to the posterior mode under
a Dirichlet add-half prior on every probability (smoothing, so that ten pairs cannot set a rate to exactly 0 or 1),
from many random starts; class Q is the class in which Kimi K3 reads D_part = 0 more often. The operating
characteristics of a rule at k samples follow from the fitted distributions; 95 percent intervals come from a
bootstrap over the 48 items, refitting the model in each resample. The model's limits are stated in the plan.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import sys
import traceback
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_legibility as lg  # noqa: E402

VERSION = "b3-comprehension/v0"
PROJECT = HERE.parent.parent
S3 = PROJECT / "work" / "stage3"
OUT = S3 / "b3" / "comprehension"
BRIEF = PROJECT / "briefs" / "25-b3-comprehension-run-2026-11-01.md"
INSTRUMENT_JSON = S3 / "legibility" / "instrument-v0.json"

# ── C1: the sample count and Sol's rule (written before the plan was computed) ───────────────────────

PLAN_SEED = 20261208          # EM starts and the bootstrap (new here)
PLAN_BOOTSTRAP_N = 1000
PLAN_STARTS = 24              # random EM starts on the data
PLAN_STARTS_BOOT = 8          # random EM starts in each bootstrap resample
SMOOTH = 0.5                  # add-half: the Dirichlet prior's pseudo-count on every probability (posterior mode)
EM_ITERS, EM_TOL = 3000, 1e-11
FLOOR = 1e-12
K_VALUES = (2, 3, 4)
ANCHOR, SECOND, BESIDE = "kimi", "sol", "sonnet55"
PLAN_READERS = (ANCHOR, SECOND, BESIDE)
CATS = (0.0, 0.5, 1.0)        # D_part on one sample: the maximum over parts of the mean over two scoring passes
SOL_RULES = (("majority", None), ("mean", 0.25), ("mean", 1 / 3), ("mean", 0.5))
TARGET_QUIET, TARGET_NONQUIET = 0.8, 0.1
EXPECTED_FLIPS = {"kimi": 2, "sol": 5, "sonnet55": 1}      # brief 25 C1, of 10 retest test items each
EXPECTED_PROXY = (12, 48)                                  # D_part = 0 under Kimi K3 and Sol at r0
T1_TEST_REGIMES = ("v2_conforming", "v3_middle")
SELECTION_RULE = (
    "Candidates: k in {2, 3, 4} samples per condition (one k for every reader) and Sol's rule in {majority (D_part = 0 on "
    "more than half of the samples), mean D_part at or under 0.25, 1/3, 0.5}; Kimi K3 always on every sample. On the "
    "point estimates of the combined rule (Kimi K3 and Sol both quiet): if some candidate gives P(labelled quiet | truly "
    "quiet) >= 0.8 and P(labelled quiet | not quiet) <= 0.1, the smallest k among them, then the highest first figure, "
    "then the lowest second, then the rule order above; otherwise the candidate with the smallest shortfall "
    "max(0, 0.8 - first) + max(0, second - 0.1), ties to the smallest k, then the highest first figure, then the rule order.")
MODEL_LIMITS = [
    "Two classes: an item of intermediate legibility (a part credited on some samples by its nature, not by noise) is "
    "forced into one class; the model then overstates how much extra samples sharpen the label.",
    "Conditional independence across readers given the class: if two readers share an item-level difficulty beyond the "
    "class, their agreement is read as accuracy and both classes look cleaner than they are.",
    "Ten retest pairs per reader carry the within-reader repeat information; the 48 items' r0 readings carry the "
    "cross-reader information. The intervals are wide, and the best attainable pair, not a clean 0.8 and 0.1, is the "
    "expected outcome at that n.",
    "The T1 test items are the population of the fit; B3's candidates were written by other writers, so the operating "
    "characteristics transfer to them only if the readers' noise does.",
    "Sonnet 5.5's five r0 refusals on test items are missing in the fit (not refusals of class membership).",
]


def rule_name(rule: tuple[str, float | None]) -> str:
    kind, tau = rule
    if kind in ("every", "majority"):
        return kind
    return f"mean_le_{tau:.3f}"


def category(x: Any) -> int | None:
    """D_part on one sample -> 0, 1 or 2 (for 0, 0.5, 1); None when not computed."""
    if x is None:
        return None
    v = float(x) * 2
    c = round(v)
    if c not in (0, 1, 2) or abs(v - c) > 1e-9:
        raise ValueError("a D_part value off the 0 / 0.5 / 1 grid")
    return int(c)


def plan_data(instrument: Mapping[str, Any]) -> tuple[list[dict], dict]:
    """brief 23's per-item D_part on the T1 test items: [{reader: [category at r0, category at r1 if retested]}], and
    the counts the brief quotes (flips per reader, the r0 proxy share)."""
    pf = instrument["per_family"]
    ids = sorted(k for k, v in pf[ANCHOR]["items"].items() if v["regime"] in T1_TEST_REGIMES)
    data, flips, retest_n, quiet_r0, n_r0 = [], {}, {}, {}, {}
    for f in PLAN_READERS:
        flips[f] = retest_n[f] = quiet_r0[f] = n_r0[f] = 0
    proxy = 0
    for i in ids:
        row: dict[str, list[int]] = {}
        for f in PLAN_READERS:
            rec = pf[f]["items"][i]
            if rec["regime"] not in T1_TEST_REGIMES:
                raise ValueError("readers disagree on an item's regime")
            c0 = category(rec["r0"]["D_part"])
            c1 = category(rec["r1"]["D_part"]) if "r1" in rec else None
            row[f] = [c for c in (c0, c1) if c is not None]
            if c0 is not None:
                n_r0[f] += 1
                quiet_r0[f] += c0 == 0
            if c0 is not None and c1 is not None:
                retest_n[f] += 1
                flips[f] += (c0 == 0) != (c1 == 0)
        a, b = pf[ANCHOR]["items"][i]["r0"]["D_part"], pf[SECOND]["items"][i]["r0"]["D_part"]
        proxy += a == 0 and b == 0
        data.append(row)
    counts = {"n_test_items": len(ids), "flips": flips, "retest_pairs": retest_n, "quiet_r0": quiet_r0, "n_r0": n_r0,
              "proxy_both_quiet_r0": proxy}
    return data, counts


def _norm(v: Sequence[float]) -> list[float]:
    s = sum(v)
    return [x / s for x in v]


def _estep(data: Sequence[Mapping[str, Sequence[int]]], readers: Sequence[str], pi: float, th: Mapping[str, Sequence[Sequence[float]]]):
    w, ll = [], 0.0
    lp = (math.log(max(pi, FLOOR)), math.log(max(1 - pi, FLOOR)))
    lth = {f: [[math.log(max(p, FLOOR)) for p in th[f][z]] for z in (0, 1)] for f in readers}
    for d in data:
        lz = [lp[z] + sum(lth[f][z][c] for f in readers for c in d.get(f, ())) for z in (0, 1)]
        m = max(lz)
        e = [math.exp(x - m) for x in lz]
        w.append(e[0] / (e[0] + e[1]))
        ll += m + math.log(e[0] + e[1])
    return w, ll


def _mstep(data, readers, w, smooth):
    n = len(data)
    pi = (sum(w) + smooth) / (n + 2 * smooth)
    th = {}
    for f in readers:
        th[f] = []
        for z in (0, 1):
            cnt = [smooth] * len(CATS)
            for wi, d in zip(w, data):
                wz = wi if z == 0 else 1 - wi
                for c in d.get(f, ()):
                    cnt[c] += wz
            th[f].append(_norm(cnt))
    return pi, th


def _log_prior(pi, th, smooth) -> float:
    lp = smooth * (math.log(max(pi, FLOOR)) + math.log(max(1 - pi, FLOOR)))
    return lp + smooth * sum(math.log(max(p, FLOOR)) for f in th for z in (0, 1) for p in th[f][z])


def lca_fit(data: Sequence[Mapping[str, Sequence[int]]], readers: Sequence[str] = PLAN_READERS, smooth: float = SMOOTH,
            starts: int = PLAN_STARTS, rng: random.Random | None = None) -> dict:
    """Posterior-mode EM (MLE when smooth is 0) from `starts` random starts; class 0 is Q (the class in which the anchor
    reader reads D_part = 0 more often)."""
    rng = rng or random.Random(PLAN_SEED)
    best = None
    for _ in range(starts):
        pi = rng.uniform(0.2, 0.8)
        th = {f: [_norm([rng.uniform(0.05, 1.0) for _ in CATS]) for _z in (0, 1)] for f in readers}
        prev = -math.inf
        for _ in range(EM_ITERS):
            w, ll = _estep(data, readers, pi, th)
            obj = ll + _log_prior(pi, th, smooth)
            if obj - prev < EM_TOL and math.isfinite(prev):
                break
            prev = obj
            pi, th = _mstep(data, readers, w, smooth)
        w, ll = _estep(data, readers, pi, th)
        obj = ll + _log_prior(pi, th, smooth)
        if best is None or obj > best["objective"] + 1e-12:
            best = {"objective": obj, "loglik": ll, "pi": pi, "theta": th}
    pi, th = best["pi"], best["theta"]
    if th[ANCHOR][1][0] > th[ANCHOR][0][0]:
        pi, th = 1 - pi, {f: [th[f][1], th[f][0]] for f in th}
    return {"pi_quiet": pi, "theta": {f: {"Q": list(th[f][0]), "N": list(th[f][1])} for f in th},
            "loglik": best["loglik"], "objective": best["objective"]}


def rule_prob(theta: Sequence[float], k: int, rule: tuple[str, float | None]) -> float:
    """P(a reader's k samples satisfy `rule`) when each sample's D_part is a categorical draw over (0, 0.5, 1)."""
    kind, tau = rule
    tot = 0.0
    for n0 in range(k + 1):
        for n1 in range(k + 1 - n0):
            n2 = k - n0 - n1
            if kind == "every":
                ok = n0 == k
            elif kind == "majority":
                ok = n0 > k / 2
            elif kind == "mean":
                ok = (0.5 * n1 + n2) / k <= tau + 1e-9
            else:
                raise ValueError(kind)
            if ok:
                coef = math.factorial(k) / (math.factorial(n0) * math.factorial(n1) * math.factorial(n2))
                tot += coef * theta[0] ** n0 * theta[1] ** n1 * theta[2] ** n2
    return tot


def operating(fit: Mapping[str, Any], k: int, rules: Mapping[str, tuple[str, float | None]]) -> dict:
    """{"quiet": P(labelled quiet | Q), "nonquiet": P(labelled quiet | N)} for a conjunction of per-reader rules."""
    out = {}
    for cls, key in (("Q", "quiet"), ("N", "nonquiet")):
        p = 1.0
        for f, rule in rules.items():
            p *= rule_prob(fit["theta"][f][cls], k, rule)
        out[key] = p
    return out


def candidate_rules() -> list[tuple[int, tuple[str, float | None]]]:
    return [(k, r) for k in K_VALUES for r in SOL_RULES]


def beside_rules() -> dict[str, dict[str, tuple[str, float | None]]]:
    every = ("every", None)
    return {"kimi_every": {ANCHOR: every}, "sol_every": {SECOND: every}, "kimi_every_and_sol_every": {ANCHOR: every, SECOND: every},
            "kimi_every_and_sonnet55_every": {ANCHOR: every, BESIDE: every}, "sonnet55_every": {BESIDE: every}}


def shortfall(q: float, nq: float) -> float:
    return max(0.0, TARGET_QUIET - q) + max(0.0, nq - TARGET_NONQUIET)


def choose(table: Sequence[Mapping[str, Any]]) -> dict:
    """SELECTION_RULE over rows {k, rule, rule_index, quiet, nonquiet}."""
    feas = [r for r in table if r["quiet"] >= TARGET_QUIET and r["nonquiet"] <= TARGET_NONQUIET]
    if feas:
        best = min(feas, key=lambda r: (r["k"], -r["quiet"], r["nonquiet"], r["rule_index"]))
        return {**best, "feasible": True}
    best = min(table, key=lambda r: (round(shortfall(r["quiet"], r["nonquiet"]), 12), r["k"], -r["quiet"], r["rule_index"]))
    return {**best, "feasible": False}


def plan_table(fit: Mapping[str, Any]) -> list[dict]:
    rows = []
    for k, rule in candidate_rules():
        oc = operating(fit, k, {ANCHOR: ("every", None), SECOND: rule})
        rows.append({"k": k, "rule": rule_name(rule), "rule_index": SOL_RULES.index(rule), **oc,
                     "kimi": operating(fit, k, {ANCHOR: ("every", None)}), "sol": operating(fit, k, {SECOND: rule})})
    return rows


def model_checks(fit: Mapping[str, Any], counts: Mapping[str, Any]) -> dict:
    pi = fit["pi_quiet"]
    out = {}
    for f in PLAN_READERS:
        q0, n0 = fit["theta"][f]["Q"][0], fit["theta"][f]["N"][0]
        out[f] = {"implied_flip_rate": pi * 2 * q0 * (1 - q0) + (1 - pi) * 2 * n0 * (1 - n0),
                  "observed_flip_rate": counts["flips"][f] / counts["retest_pairs"][f] if counts["retest_pairs"][f] else None,
                  "implied_quiet_share_one_sample": pi * q0 + (1 - pi) * n0,
                  "observed_quiet_share_r0": counts["quiet_r0"][f] / counts["n_r0"][f] if counts["n_r0"][f] else None}
    return out


def reader_relative_fit(data: Sequence[Mapping[str, Sequence[int]]]) -> dict:
    """The sensitivity model: truth relative to each reader (an item is quiet or not for that reader), symmetric
    per-sample error e from the reader's own retest flips alone (2e(1 - e) = flip rate; e = 0.5 when the flip rate is
    at or above 0.5) and, among credited samples, the reader's observed share at 0.5 (h). Class prevalence does not
    enter the operating characteristics. Same structure as the main fit so that `operating` applies."""
    theta = {}
    for f in PLAN_READERS:
        pairs = [d[f] for d in data if len(d.get(f, ())) == 2]
        flip = sum((a == 0) != (b == 0) for a, b in pairs) / len(pairs) if pairs else 0.5
        e = (1 - math.sqrt(max(0.0, 1 - 2 * min(flip, 0.5)))) / 2
        credited = [c for d in data for c in d.get(f, ()) if c != 0]
        h = sum(1 for c in credited if c == 1) / len(credited) if credited else 0.0
        theta[f] = {"Q": [1 - e, e * h, e * (1 - h)], "N": [e, (1 - e) * h, (1 - e) * (1 - h)], "e": e, "h": h, "flip": flip}
    return {"pi_quiet": None, "theta": theta}


def _ci(xs: Sequence[float]) -> list[float] | None:
    if len(xs) < 10:
        return None
    return [lg.quantile7(xs, 0.025), lg.quantile7(xs, 0.975)]


def bootstrap_plan(data: Sequence[Mapping[str, Sequence[int]]], n: int = PLAN_BOOTSTRAP_N, seed: int = PLAN_SEED) -> dict:
    rng = random.Random(seed + 1)
    acc: dict[str, list[float]] = {}
    for _ in range(n):
        sample = [data[rng.randrange(len(data))] for _ in range(len(data))]
        fit = lca_fit(sample, starts=PLAN_STARTS_BOOT, rng=rng)
        acc.setdefault("pi_quiet", []).append(fit["pi_quiet"])
        for row in plan_table(fit):
            for key in ("quiet", "nonquiet"):
                acc.setdefault(f"k{row['k']}|{row['rule']}|{key}", []).append(row[key])
        for name, rules in beside_rules().items():
            for k in K_VALUES:
                oc = operating(fit, k, rules)
                for key in ("quiet", "nonquiet"):
                    acc.setdefault(f"k{k}|{name}|{key}", []).append(oc[key])
        for row in plan_table(reader_relative_fit(sample)):
            for key in ("quiet", "nonquiet"):
                acc.setdefault(f"rr|k{row['k']}|{row['rule']}|{key}", []).append(row[key])
    return {key: _ci(v) for key, v in acc.items()}


def build_plan(instrument: Mapping[str, Any], boot_n: int = PLAN_BOOTSTRAP_N) -> dict:
    data, counts = plan_data(instrument)
    if counts["flips"] != EXPECTED_FLIPS or {f: counts["retest_pairs"][f] for f in PLAN_READERS} != {f: 10 for f in PLAN_READERS}:
        raise SystemExit("refusing: brief 23's retest flips differ from brief 25's figures")
    if (counts["proxy_both_quiet_r0"], counts["n_test_items"]) != EXPECTED_PROXY:
        raise SystemExit("refusing: the T1 proxy share differs from brief 25's figure")
    fit = lca_fit(data)
    mle = lca_fit(data, smooth=0.0)
    table = plan_table(fit)
    choice = choose(table)
    ci = bootstrap_plan(data, n=boot_n)
    for row in table:
        row["quiet_ci95"] = ci.get(f"k{row['k']}|{row['rule']}|quiet")
        row["nonquiet_ci95"] = ci.get(f"k{row['k']}|{row['rule']}|nonquiet")
        row["shortfall"] = shortfall(row["quiet"], row["nonquiet"])
    beside = {name: {f"k{k}": {**operating(fit, k, rules), "quiet_ci95": ci.get(f"k{k}|{name}|quiet"),
                                "nonquiet_ci95": ci.get(f"k{k}|{name}|nonquiet")} for k in K_VALUES}
              for name, rules in beside_rules().items()}
    sol_rule = SOL_RULES[choice["rule_index"]]
    chosen_row = next(r for r in table if r["k"] == choice["k"] and r["rule"] == choice["rule"])
    pi = fit["pi_quiet"]
    mle_oc = operating(mle, choice["k"], {ANCHOR: ("every", None), SECOND: sol_rule})
    rr = reader_relative_fit(data)
    rr_table = plan_table(rr)
    for row in rr_table:
        row["quiet_ci95"] = ci.get(f"rr|k{row['k']}|{row['rule']}|quiet")
        row["nonquiet_ci95"] = ci.get(f"rr|k{row['k']}|{row['rule']}|nonquiet")
        row["shortfall"] = shortfall(row["quiet"], row["nonquiet"])
    rr_choice = choose(rr_table)
    sensitivity = {
        "model": ("truth relative to each reader; symmetric per-sample error from the reader's own retest flips "
                  "(2e(1 - e) = flip rate); the 0.5 share among credited samples observed per reader"),
        "why": ("the stratum's definition is reader-relative (no single line yields the consequence under two reader "
                "families), whereas the main fit's truly quiet class is a cross-reader consensus that reads systematic "
                "disagreement between readers as within-reader noise (its implied flip rates differ from the observed "
                "ones in model_checks)"),
        "added": ("after the first computation of this plan (the main fit alone) and before its commit and before any "
                  "call; the selection rule is unchanged and the choice governs from the main fit"),
        "readers": {f: {k: rr["theta"][f][k] for k in ("e", "h", "flip")} for f in PLAN_READERS},
        "candidates": rr_table, "choice": {"k": rr_choice["k"], "rule": rr_choice["rule"], "feasible": rr_choice["feasible"],
                                           "quiet": rr_choice["quiet"], "nonquiet": rr_choice["nonquiet"]},
        "same_choice_as_main": rr_choice["k"] == choice["k"] and rr_choice["rule"] == choice["rule"],
        "limits": ["symmetric error is an assumption: two samples per item cannot separate a reader's error rates on "
                   "quiet and non-quiet items (the repeat pairs alone do not identify them)",
                   "at Sol's observed flip rate of 0.5 the symmetric model gives e = 0.5: Sol's label carries no "
                   "information under it, so Sol's rule only scales both figures"]}
    return {
        "version": VERSION, "brief": {"path": str(BRIEF.relative_to(PROJECT)), "sha256": lg.file_sha256(BRIEF)},
        "inputs": {"instrument_v0_json": {"path": str(INSTRUMENT_JSON.relative_to(PROJECT)), "sha256": lg.file_sha256(INSTRUMENT_JSON)}},
        "counts": counts,
        "model": {"classes": ["Q (truly quiet)", "N (not quiet)"], "indicator": "D_part per sample in (0, 0.5, 1), categorical per reader and class",
                  "readers": list(PLAN_READERS), "estimator": "EM to the posterior mode", "prior": f"Dirichlet add-{SMOOTH} on every probability",
                  "starts": PLAN_STARTS, "bootstrap": {"n": boot_n, "over": "the 48 T1 test items, model refitted", "starts_per_resample": PLAN_STARTS_BOOT,
                                                       "interval": "95 percent percentile"},
                  "seed": PLAN_SEED, "limits": MODEL_LIMITS},
        "fit": {"pi_quiet": pi, "pi_quiet_ci95": ci.get("pi_quiet"), "theta": fit["theta"], "loglik": fit["loglik"]},
        "fit_mle_beside": {"pi_quiet": mle["pi_quiet"], "theta": mle["theta"], "chosen_rule": mle_oc},
        "model_checks": model_checks(fit, counts),
        "selection_rule": SELECTION_RULE, "candidates": table, "beside": beside,
        "sensitivity_reader_relative": sensitivity,
        "choice": {"samples_per_condition": choice["k"], "anchor_rule": "kimi: D_part = 0 on every sample",
                   "sol_rule": {"kind": sol_rule[0], "threshold": sol_rule[1], "name": rule_name(sol_rule)},
                   "beside_rule": "sonnet55 on GLM-written items: D_part = 0 on every sample",
                   "feasible_at_0_8_and_0_1": choice["feasible"],
                   "p_labelled_quiet_given_quiet": chosen_row["quiet"], "ci95": chosen_row["quiet_ci95"],
                   "p_labelled_quiet_given_not_quiet": chosen_row["nonquiet"], "ci95_not_quiet": chosen_row["nonquiet_ci95"]},
        "statement": ("The flip rates rest on 10 retest test items per reader; at that n the best attainable pair, not a clean "
                      "0.8 and 0.1, is the expected outcome, and the intervals above are what the figures can claim."),
        "t1_expectation_only": {"proxy_share_one_sample_both_quiet": counts["proxy_both_quiet_r0"] / counts["n_test_items"],
                                "proxy_counts": list(EXPECTED_PROXY),
                                "model_expected_share_at_choice": pi * chosen_row["quiet"] + (1 - pi) * chosen_row["nonquiet"],
                                "note": ("an expectation only; there is no stop bar (T1 is the set already known to be heavy on "
                                         "single-line items; the stratum's size is what the run measures)")},
        "script_sha256": lg.file_sha256(Path(__file__)),
    }


def mode_plan(ns: argparse.Namespace) -> int:
    out_dir = Path(ns.out_dir)
    if (out_dir / "stratum-plan.json").exists() and not ns.force:
        raise SystemExit("refusing: stratum-plan.json exists")
    plan = build_plan(json.loads(INSTRUMENT_JSON.read_text(encoding="utf-8")))
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stratum-plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
    lg.emit({"counts": plan["counts"], "choice": {k: v for k, v in plan["choice"].items() if not isinstance(v, str)},
             "sol_rule": plan["choice"]["sol_rule"]["name"], "pi_quiet": plan["fit"]["pi_quiet"],
             "t1_expected_share": plan["t1_expectation_only"]["model_expected_share_at_choice"],
             "sensitivity_choice": plan["sensitivity_reader_relative"]["choice"],
             "sensitivity_same_choice": plan["sensitivity_reader_relative"]["same_choice_as_main"],
             "stratum_plan_sha256": lg.file_sha256(out_dir / "stratum-plan.json")})
    return 0


# ── C2: items, targets and draws (committed by hash before any call) ────────────────────────────────

FALSE_TARGET_SEED = lg.FALSE_TARGET_SEED   # 20261203: brief 23's same-document rule, one stream over the null items
OWN_SEED, N_OWN = 20261207, 20             # the own-edit positive control's 20 candidates (brief 25 C2)
REGIMES = ("candidate", "control", "sham")
NULL_REGIMES = ("control", "sham")
EXPECTED_ITEMS = {"candidate": 78, "control": 22, "sham": 24}
EXPECTED_QUIET_BY_WRITER = {"sonnet55": 41, "glm53": 37}
WRITERS = ("sonnet55", "glm53")
ALL_ITEM_READERS = (ANCHOR, SECOND)        # Kimi K3 and GPT-6 Sol on every item
GLM_ONLY_READER = BESIDE                   # Sonnet 5.5 on GLM-written items only
CONDS, PARTS, PASSES = lg.CONDS, lg.PARTS, lg.PASSES
RATED_ARM = {"candidates": "distributed", "controls": "control_samewriter"}
APPROVAL_CAP_USD = 40.0
APPROVAL_RULE = ("Aravind, 2026-11-01: \"I'm ok with the cost estimate - I don't necessarily need the exact estimate to approve "
                 "this\"; brief 25 C2: proceed without waiting at or under $40, above $40 stop and ask; the stop at twice the "
                 "dry-run estimate applies")
DEPENDENCIES = lg.DEPENDENCIES + ("work/checks/stage3_legibility.py", "work/checks/stage3_b3_power_v3.py",
                                  "work/checks/stage3_views.py", "work/checks/stage3_t1v2_checks.py")


def readers_of(writer: str) -> list[str]:
    return list(ALL_ITEM_READERS) + ([GLM_ONLY_READER] if writer == "glm53" else [])


def build_items(quiet: Sequence[Mapping[str, Any]], key_b3: Mapping[str, Any], triples_b3: Sequence[Mapping[str, Any]],
                writer_files: Mapping[str, Mapping[str, Any]], t1_items: Mapping[str, Any], t1_triples: Sequence[Mapping[str, Any]],
                payloads_v2: Mapping[str, Any], day0: Mapping[str, str], k: int,
                expected: Mapping[str, int] | None = EXPECTED_ITEMS) -> tuple[dict, dict, dict]:
    """(items document: ids, regimes, targets, draws, no text; rubrics document; the triples by id for rendering).
    quiet: brief 20 P1's mean-rule quiet candidates ({writer, id, document}); writer_files: {source: parsed file}."""
    b3 = {t["triple_id"]: t for t in triples_b3}
    t1 = {t["triple_id"]: t for t in t1_triples}
    if set(b3) & set(t1):
        raise ValueError("a B3 opaque id equals a T1 triple id")
    by_writer_id = {}
    for tid, v in key_b3["triples"].items():
        part, _, writer = str(v.get("source", "")).partition("-")
        if part in RATED_ARM:
            by_writer_id[(part, writer, v["id"])] = tid
    pay = {(src, p["id"]): p for src, d in writer_files.items() for p in d["payloads"]}
    rows: dict[str, dict] = {}
    triples: dict[str, Mapping[str, Any]] = {}
    rubrics: dict[str, Any] = {"version": VERSION, "rubric": {}, "paired": {}, "own": {}}

    def check_statements(p: Mapping[str, Any], t: Mapping[str, Any], what: str) -> None:
        if str(p["document"]) != t["document"] or lg.payload_statements(p) != lg.triple_statements(t):
            raise ValueError(f"{what} does not match its stripped triple")

    for q in quiet:
        tid = by_writer_id.get(("candidates", q["writer"], q["id"]))
        if tid is None:
            raise ValueError(f"no key triple for candidate {q['writer']}/{q['id']}")
        t, kv = b3[tid], key_b3["triples"][tid]
        p = pay.get((f"candidates-{q['writer']}", q["id"]))
        if p is None or p.get("arm") != RATED_ARM["candidates"]:
            raise ValueError(f"no rated payload for candidate {q['writer']}/{q['id']}")
        check_statements(p, t, f"candidate {q['writer']}/{q['id']}")
        if t["document"] != q["document"]:
            raise ValueError("the quiet set's document differs from the key's")
        eff = str(p.get("composed_effect") or "").strip()
        if not eff:
            raise ValueError(f"candidate {q['writer']}/{q['id']} has no composed_effect")
        rubrics["rubric"][tid] = eff
        rows[tid] = {"item_id": tid, "regime": "candidate", "writer": q["writer"], "document": t["document"], "kind": kv.get("kind")}
        triples[tid] = t
    for (part, writer, pid), tid in sorted(by_writer_id.items()):
        if part != "controls":
            continue
        t, kv = b3[tid], key_b3["triples"][tid]
        p = pay.get((f"controls-{writer}", pid))
        if p is None or p.get("arm") != RATED_ARM["controls"]:
            raise ValueError(f"no rated payload for control {writer}/{pid}")
        check_statements(p, t, f"control {writer}/{pid}")
        rows[tid] = {"item_id": tid, "regime": "control", "writer": writer, "document": t["document"], "kind": kv.get("kind")}
        triples[tid] = t
    v2 = {p["id"]: p for p in payloads_v2["payloads"]}
    for r in t1_items["items"]:
        if r["regime"] != "control":
            continue
        sid, ref = r["item_id"], r["payload_ref"]
        p = v2.get(ref["id"])
        if ref.get("file") != "v2" or p is None or p.get("arm") != "sham":
            raise ValueError(f"sham {ref.get('id')} is not a v2 sham payload")
        check_statements(p, t1[sid], f"sham {ref['id']}")
        pid = lg.paired_payload_id(ref["id"])
        pc = v2.get(pid) if pid else None
        eff = str((pc or {}).get("composed_effect") or "").strip()
        if pc is None or str(pc["document"]) != t1[sid]["document"] or not eff:
            raise ValueError(f"sham {ref['id']} has no same-document paired rubric")
        rubrics["paired"][sid] = eff
        rows[sid] = {"item_id": sid, "regime": "sham", "writer": "t1v2", "document": t1[sid]["document"], "kind": p.get("kind"),
                     "payload_ref": {"file": "v2", "id": ref["id"]}, "paired_payload": pid}
        triples[sid] = t1[sid]
    counts = dict(sorted({g: sum(1 for r in rows.values() if r["regime"] == g) for g in REGIMES}.items()))
    if expected is not None and counts != dict(sorted(expected.items())):
        raise ValueError(f"item counts {counts} differ from the brief's {dict(expected)}")
    cands = sorted(t for t, r in rows.items() if r["regime"] == "candidate")
    by_doc: dict[str, list[str]] = {}
    for c in cands:
        by_doc.setdefault(rows[c]["document"], []).append(c)
    rng = random.Random(FALSE_TARGET_SEED)
    for tid in sorted(t for t, r in rows.items() if r["regime"] in NULL_REGIMES):
        row = rows[tid]
        pool = sorted(by_doc.get(row["document"], []))
        if not pool:
            raise ValueError("no quiet candidate on a null item's document")
        km = [x for x in pool if row["kind"] is not None and rows[x]["kind"] == row["kind"]]
        row["false_target"] = rng.choice(km or pool)
        row["false_target_kind_matched"] = bool(km)
    own = set(random.Random(OWN_SEED).sample(cands, min(N_OWN, len(cands))))
    for tid, row in rows.items():
        row.setdefault("false_target", None)
        row.setdefault("false_target_kind_matched", None)
        row["own"] = tid in own
        row["paired_target"] = row["regime"] == "sham"
        row["readers"] = readers_of(row["writer"])
        bad = [st for st in triples[tid]["statements"] if not lg.anchor_resolves(st, day0[row["document"]])]
        row["anchors_resolve"] = not bad
        row["n_unresolved_anchors"] = len(bad)
        if row["own"]:
            sts = triples[tid]["statements"]
            rubrics["own"][tid] = {"whole": lg.own_rubric(sts), "part": [lg.own_rubric([st]) for st in sts]}
    all_ids = sorted(rows)
    items = {"version": VERSION, "samples_per_condition": k,
             "counts": {"items": counts, "total": len(rows),
                        "candidates_by_writer": dict(sorted({w: sum(1 for r in rows.values() if r["regime"] == "candidate" and r["writer"] == w)
                                                             for w in WRITERS}.items())),
                        "controls_by_writer": dict(sorted({w: sum(1 for r in rows.values() if r["regime"] == "control" and r["writer"] == w)
                                                           for w in WRITERS}.items())),
                        "null_false_targets_kind_matched": {g: sum(1 for r in rows.values() if r["regime"] == g and r["false_target_kind_matched"])
                                                            for g in NULL_REGIMES},
                        "own_control_items": len(own),
                        "items_per_reader": {f: sum(1 for r in rows.values() if f in r["readers"]) for f in PLAN_READERS},
                        "items_with_every_anchor_resolved_by_regime": {g: sum(1 for r in rows.values() if r["regime"] == g and r["anchors_resolve"])
                                                                       for g in REGIMES},
                        "unresolved_anchors_by_regime": {g: sum(r["n_unresolved_anchors"] for r in rows.values() if r["regime"] == g) for g in REGIMES}},
             "items": [rows[t] for t in all_ids], "own_draw": sorted(own),
             "rubrics_sha256": lg.sha256(lg.canonical(rubrics))}
    return items, rubrics, triples


# ── calls: labels, targets and units ────────────────────────────────────────────────────────────────

def l_target(regime: str) -> str:
    return "rubric" if regime == "candidate" else "false"


def scoring_targets(row: Mapping[str, Any], s: int) -> tuple[str, ...]:
    """Every sample: the L target (a candidate's rubric; a null item's false target). Sample 0 also: the own edit for
    the 20 drawn candidates (positive control) and the paired rubric for the sham (sensitivity)."""
    t = [l_target(row["regime"])]
    if s == 0 and row["regime"] == "candidate" and row.get("own"):
        t.append("own")
    if s == 0 and row["regime"] == "sham" and row.get("paired_target"):
        t.append("paired")
    return tuple(t)


def reader_units(rows: Sequence[Mapping[str, Any]], fam: str, k: int) -> list[tuple[int, str, str]]:
    return [(s, row["item_id"], c) for row in rows if fam in row["readers"] for s in range(k) for c in CONDS]


def scorer_units(row: Mapping[str, Any], s: int) -> list[tuple[int, str]]:
    return [(p, t) for t in scoring_targets(row, s) for p in PASSES]


def rubric_for(row: Mapping[str, Any], rubrics: Mapping[str, Any], cond: str, target: str) -> str:
    if target == "rubric":
        return rubrics["rubric"][row["item_id"]]
    if target == "false":
        return rubrics["rubric"][row["false_target"]]
    if target == "paired":
        return rubrics["paired"][row["item_id"]]
    if target == "own":
        own = rubrics["own"][row["item_id"]]
        return own["whole"] if cond == "whole" else own["part"][PARTS.index(cond)]
    raise ValueError(f"unknown target {target!r}")


class B3Records(lg.Records):
    """brief 23's records and outcome rules; the L target follows this brief's regimes."""

    def reader_status(self, fam: str, r: int, row: Mapping[str, Any], cond: str) -> str:
        rec = self.read.get((fam, r, row["item_id"], cond))
        if rec is None or rec.get("outcome") == "errored":
            return "missing"
        parsed = rec.get("parsed") or {}
        if rec["outcome"] == "refused":
            return "refused_token" if parsed.get("declined_token") else "refused_provider"
        if parsed.get("declined_token"):
            return "refused_token"
        lt = l_target(row["regime"])
        flags = [self.score.get((fam, r, row["item_id"], cond, lt, p)) for p in PASSES]
        if all(f is not None and f.get("outcome") == "scored" and (f.get("parsed") or {}).get("declined") for f in flags):
            return "refused_prose"
        return "answered"


# ── configuration, inputs and the estimate ─────────────────────────────────────────────────────────

def config(plan: Mapping[str, Any]) -> dict[str, Any]:
    ch = plan["choice"]
    return {"version": VERSION, "instrument_config_sha256": lg.config_sha256(), "instrument_prompt_sha256": lg.prompt_hashes(),
            "samples_per_condition": ch["samples_per_condition"], "sol_rule": ch["sol_rule"], "anchor_rule": ch["anchor_rule"],
            "beside_rule": ch["beside_rule"], "readers": {"all_items": list(ALL_ITEM_READERS), "glm_written_only": GLM_ONLY_READER},
            "scorer": lg.SCORER["bedrock"], "passes": list(PASSES),
            "seeds": {"false_target": FALSE_TARGET_SEED, "own_control": OWN_SEED, "order": lg.ORDER_SEED},
            "approval": {"cap_usd": APPROVAL_CAP_USD, "rule": APPROVAL_RULE}}


def config_sha256(plan: Mapping[str, Any]) -> str:
    return lg.sha256(lg.canonical(config(plan)))


def dependency_hashes() -> dict[str, str]:
    return {d: lg.file_sha256(PROJECT / d) for d in DEPENDENCIES}


def quiet_set(root: Path = PROJECT) -> tuple[list[dict], dict[str, str]]:
    """brief 20 P1's mean-rule quiet set, recomputed from the key and the four pass files by its own code."""
    import stage3_b3_power_v3 as pv
    files = [pv.RATER + "/key-b3.json"] + [f"{pv.RATER}/ratings-b3-{s}-p{p}.jsonl" for s in ("statements", "triples") for p in (1, 2)] \
        + list(pv.CHECKS.values())
    return pv.quiet(pv.load_stimuli(root)), {f: lg.file_sha256(root / f) for f in files}


INPUT_ARGS = ("key_b3", "triples_b3", "candidates_sonnet55", "candidates_glm53", "controls_sonnet55", "controls_glm53",
              "t1_items", "t1_triples", "payloads_v2", "day0_md")


def load_inputs(ns: argparse.Namespace) -> dict[str, Any]:
    import stage3_views as sv
    from stage3_t1v2_checks import DOCS
    paths = {k: Path(getattr(ns, k)) for k in INPUT_ARGS}
    data = {k: json.loads(p.read_text(encoding="utf-8")) for k, p in paths.items() if k != "day0_md"}
    seed = sv.seed_base()
    day0 = {path: text for (_svc, path), text in seed.items() if path in DOCS}
    if set(day0) != set(DOCS):
        raise SystemExit("refusing: the seeder's day-0 texts do not cover the six class documents")
    md = paths["day0_md"].read_text(encoding="utf-8")
    quiet, quiet_inputs = quiet_set()
    return {"paths": paths, "data": data, "day0": day0, "day0_in_md": all(t.strip() in md for t in day0.values()),
            "sha256": {k: lg.file_sha256(p) for k, p in paths.items()}, "quiet": quiet, "quiet_inputs_sha256": quiet_inputs}


def writer_files(data: Mapping[str, Any]) -> dict[str, Any]:
    return {f"{part}-{w}": data[f"{part}_{w}"] for part in RATED_ARM for w in WRITERS}


def input_checks(inp: Mapping[str, Any]) -> dict[str, bool]:
    d = inp["data"]
    src = d["key_b3"].get("sources", {})
    t1 = d["t1_items"]
    checks = {f"key_source_{part}_{w}": src.get(f"{part}-{w}", {}).get("sha256") == inp["sha256"][f"{part}_{w}"]
              for part in RATED_ARM for w in WRITERS}
    checks["t1_triples_are_brief23s"] = t1.get("inputs_sha256", {}).get("triples") == inp["sha256"]["t1_triples"]
    checks["payloads_v2_are_brief23s"] = t1.get("inputs_sha256", {}).get("payloads_v2") == inp["sha256"]["payloads_v2"]
    checks["instrument_prompts_unchanged"] = t1.get("prompt_sha256") == lg.prompt_hashes()
    checks["instrument_config_unchanged"] = t1.get("config_sha256") == lg.config_sha256()
    checks["day0_texts_in_doc_states_md"] = inp["day0_in_md"]
    checks["day0_texts_are_brief23s"] = t1.get("day0_sha256") == lg.day0_sha256(inp["day0"])
    checks["b3d36_excluded"] = [(e["source"], e["id"]) for e in d["key_b3"].get("excluded", [])] == [("candidates-glm53", "B3-D36")]
    by_w: dict[str, int] = {}
    for q in inp["quiet"]:
        by_w[q["writer"]] = by_w.get(q["writer"], 0) + 1
    checks["quiet_set_78_by_writer"] = by_w == EXPECTED_QUIET_BY_WRITER
    return checks


def estimate(rows: Sequence[Mapping[str, Any]], triples: Mapping[str, Mapping[str, Any]], day0: Mapping[str, str],
             rubrics: Mapping[str, Any], models: Mapping[str, Any] | None, routes: Mapping[str, Any] | None, k: int) -> dict:
    """brief 23's pricing (rendered prompt lengths x per-token rates, its output-token assumptions), per reader on the
    items that reader reads, and the scorer on every answer's targets."""
    packets = lg.all_packets(rows, triples, day0)
    by_id = {r["item_id"]: r for r in rows}
    out: dict[str, Any] = {"samples_per_condition": k, "families": {}, "routes_known": routes is not None}
    total = upper = 0.0
    s_calls, s_chars = 0, [0, 0]
    for fam, spec in lg.FAMILIES.items():
        units = reader_units(rows, fam, k)
        route, model = lg.family_route(fam, routes)
        pr = lg.price_per_token(route, model, models)
        chars = sum(len(lg.READER_SYSTEM) + len(packets[(i, c)]) for _s, i, c in units)
        tin = chars / spec["chars_per_token"]
        c_mid = tin * pr["in"] + len(units) * spec["out_tokens"][0] * pr["out"]
        c_up = lg.REASK_FACTOR_UPPER * (tin * pr["in"] + len(units) * spec["out_tokens"][1] * pr["out"])
        out["families"][fam] = {"route": route, "model": model, "items": sum(1 for r in rows if fam in r["readers"]), "calls": len(units),
                                "est_input_tokens": round(tin), "usd": round(c_mid, 4), "usd_upper": round(c_up, 4)}
        total += c_mid
        upper += c_up
        for s, i, c in units:
            for _p, t in scorer_units(by_id[i], s):
                s_calls += 1
                rub = rubric_for(by_id[i], rubrics, c, t)
                for j in (0, 1):
                    s_chars[j] += len(lg.SCORER_SYSTEM) + len(lg.scorer_packet(rub, "x" * lg.ASSUMED_ANSWER_CHARS[j]))
    pr = lg.price_per_token("bedrock", lg.SCORER["bedrock"], None)
    s_tin = [ch / lg.SCORER["chars_per_token"] for ch in s_chars]
    sc_mid = s_tin[0] * pr["in"] + s_calls * lg.SCORER["out_tokens"][0] * pr["out"]
    sc_up = lg.REASK_FACTOR_UPPER * (s_tin[1] * pr["in"] + s_calls * lg.SCORER["out_tokens"][1] * pr["out"])
    out["scorer"] = {"route": "bedrock", "model": lg.SCORER["bedrock"], "calls": s_calls, "est_input_tokens": round(s_tin[0]),
                     "usd": round(sc_mid, 4), "usd_upper": round(sc_up, 4)}
    total += sc_mid + lg.ROUTE_PROBE_USD
    upper += sc_up + lg.ROUTE_PROBE_USD
    out["route_probes_usd_allowance"] = lg.ROUTE_PROBE_USD
    out["total_usd"] = round(total, 2)
    out["total_usd_upper"] = round(upper, 2)
    out["stop_at_usd"] = round(2 * total, 2)
    out["approval"] = {"cap_usd": APPROVAL_CAP_USD, "within_cap": out["total_usd"] <= APPROVAL_CAP_USD}
    return out


def load_plan(out_dir: Path) -> dict:
    p = out_dir / "stratum-plan.json"
    if not p.exists():
        raise SystemExit("refusing: stratum-plan.json is missing (run the plan mode first)")
    return json.loads(p.read_text(encoding="utf-8"))


def load_items(out_dir: Path) -> tuple[dict, list[dict], dict]:
    items = json.loads((out_dir / "items-v0.json").read_text(encoding="utf-8"))
    rub = json.loads((out_dir / "rubrics-v0.json").read_text(encoding="utf-8"))
    if lg.sha256(lg.canonical(rub)) != items["rubrics_sha256"]:
        raise SystemExit("refusing: rubrics-v0.json does not match the hash in items-v0.json")
    return items, items["items"], rub


def triples_for(rows: Sequence[Mapping[str, Any]], inp: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    b3 = {t["triple_id"]: t for t in inp["data"]["triples_b3"]}
    t1 = {t["triple_id"]: t for t in inp["data"]["t1_triples"]}
    return {r["item_id"]: (t1 if r["regime"] == "sham" else b3)[r["item_id"]] for r in rows}


def mode_items(ns: argparse.Namespace) -> int:
    out_dir = Path(ns.out_dir)
    if (out_dir / "items-v0.json").exists() and not ns.force:
        raise SystemExit("refusing: items-v0.json exists (pass --force only before any call)")
    if lg.any_cache_records(out_dir):
        raise SystemExit("refusing: reader or scorer calls are on file; the items cannot change now")
    plan = load_plan(out_dir)
    inp = load_inputs(ns)
    checks = input_checks(inp)
    if not all(checks.values()):
        raise SystemExit(f"refusing: input checks failed {sorted(k for k, v in checks.items() if not v)}")
    d = inp["data"]
    k = int(plan["choice"]["samples_per_condition"])
    items, rubrics, triples = build_items(inp["quiet"], d["key_b3"], d["triples_b3"], writer_files(d), d["t1_items"], d["t1_triples"],
                                          d["payloads_v2"], inp["day0"], k)
    items["inputs_sha256"] = inp["sha256"]
    items["quiet_set_inputs_sha256"] = inp["quiet_inputs_sha256"]
    items["input_checks"] = checks
    items["stratum_plan_sha256"] = lg.file_sha256(out_dir / "stratum-plan.json")
    items["config"] = config(plan)
    items["config_sha256"] = config_sha256(plan)
    items["script_sha256"] = lg.file_sha256(Path(__file__))
    items["dependency_sha256"] = dependency_hashes()
    items["day0_sha256"] = lg.day0_sha256(inp["day0"])
    items["packets_sha256"] = lg.packets_sha256(lg.all_packets(items["items"], triples, inp["day0"]))
    items["brief"] = {"path": str(BRIEF.relative_to(PROJECT)), "sha256": lg.file_sha256(BRIEF)}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "rubrics-v0.json").write_text(lg.canonical(rubrics), encoding="utf-8")
    (out_dir / "items-v0.json").write_text(json.dumps(items, indent=1), encoding="utf-8")
    lg.emit({"counts": items["counts"], "input_checks": checks, "items_sha256": lg.file_sha256(out_dir / "items-v0.json"),
             "rubrics_sha256": items["rubrics_sha256"], "script_sha256": items["script_sha256"], "config_sha256": items["config_sha256"],
             "packets_sha256": items["packets_sha256"], "samples_per_condition": k})
    return 0


def mode_prices(ns: argparse.Namespace) -> int:
    return lg.mode_prices(argparse.Namespace(out_dir=ns.out_dir))


def mode_dry_run(ns: argparse.Namespace) -> int:
    out_dir = Path(ns.out_dir)
    plan = load_plan(out_dir)
    items, rows, rubrics = load_items(out_dir)
    if items.get("config_sha256") != config_sha256(plan):
        raise SystemExit("refusing: the configuration differs from items-v0.json")
    inp = load_inputs(ns)
    triples = triples_for(rows, inp)
    if items.get("packets_sha256") != lg.packets_sha256(lg.all_packets(rows, triples, inp["day0"])):
        raise SystemExit("refusing: the rendering differs from items-v0.json")
    models = json.loads((out_dir / "models-v0.json").read_text()) if (out_dir / "models-v0.json").exists() else None
    routes = json.loads((out_dir / "routes-v0.json").read_text()) if (out_dir / "routes-v0.json").exists() else None
    est = estimate(rows, triples, inp["day0"], rubrics, models, routes, int(items["samples_per_condition"]))
    est["config_sha256"] = items["config_sha256"]
    est["models_sha256"] = lg.file_sha256(out_dir / "models-v0.json") if models is not None else None
    est["routes_sha256"] = lg.file_sha256(out_dir / "routes-v0.json") if routes is not None else None
    est["assumptions"] = {"families": {f: {"chars_per_token": s["chars_per_token"], "out_tokens_central_upper": list(s["out_tokens"])}
                                       for f, s in lg.FAMILIES.items()},
                          "scorer": {"chars_per_token": lg.SCORER["chars_per_token"], "out_tokens_central_upper": list(lg.SCORER["out_tokens"]),
                                     "assumed_answer_chars_central_upper": list(lg.ASSUMED_ANSWER_CHARS)},
                          "every_answer_scored": True, "upper_reask_factor": lg.REASK_FACTOR_UPPER,
                          "method": "brief23_dry_run_pricing_unchanged"}
    (out_dir / "estimate-v0.json").write_text(json.dumps(est, indent=1), encoding="utf-8")
    lg.emit(est)
    return 0


def mode_routes(ns: argparse.Namespace) -> int:
    return lg.mode_routes(argparse.Namespace(out_dir=ns.out_dir, approved_usd=ns.approved_usd))


def estimate_mismatches(est: Mapping[str, Any], items: Mapping[str, Any], out_dir: Path) -> list[str]:
    bad = []
    if est.get("config_sha256") != items.get("config_sha256"):
        bad.append("estimate_config")
    if est.get("models_sha256") != lg.file_sha256(out_dir / "models-v0.json"):
        bad.append("estimate_prices")
    if est.get("routes_sha256") != lg.file_sha256(out_dir / "routes-v0.json"):
        bad.append("estimate_routes_file")
    return bad


async def run_phase(name: str, rows: Sequence[Mapping[str, Any]], packets: Mapping[tuple[str, str], str], readers: Mapping[str, Any],
                    scorer: Any, rubrics: Mapping[str, Any], guard: Any, log: Path, offset: int, k: int) -> dict:
    """Every reader on its own items (in parallel across readers), then the scorer on every answer's targets."""
    fams = list(readers)
    tasks = []
    for j, fam in enumerate(fams):
        units = lg.ordered(reader_units(rows, fam, k), offset + j)
        tasks.append(lg.run_units(readers[fam], [(lg.READ_VIEW, lg.read_label(s, i, c), packets[(i, c)]) for s, i, c in units],
                                  guard, log, f"{name}:read:{fam}"))
    res = await asyncio.gather(*tasks)
    out = {"read": dict(zip(fams, res))}
    rec = B3Records({fam: cl.cache.values() for fam, cl in readers.items()}, [])
    s_units = []
    for fam in fams:
        for row in rows:
            if fam not in row["readers"]:
                continue
            for s in range(k):
                for c in CONDS:
                    a = rec.answer(fam, s, row["item_id"], c)
                    if a is None:
                        continue
                    for p, t in scorer_units(row, s):
                        s_units.append((lg.SCORE_VIEW, lg.score_label(p, fam, s, row["item_id"], c, t),
                                        lg.scorer_packet(rubric_for(row, rubrics, c, t), a)))
    out["score"] = await lg.run_units(scorer, lg.ordered(s_units, offset + len(fams)), guard, log, f"{name}:score")
    return out


def mode_run(ns: argparse.Namespace) -> int:
    out_dir = Path(ns.out_dir)
    est = json.loads((out_dir / "estimate-v0.json").read_text())
    routes = json.loads((out_dir / "routes-v0.json").read_text())
    models = json.loads((out_dir / "models-v0.json").read_text())
    items, rows, rubrics = load_items(out_dir)
    bad = estimate_mismatches(est, items, out_dir)   # first: nothing below builds a client before this
    if bad:
        raise SystemExit(f"refusing: the estimate does not match: {sorted(bad)}")
    if abs(float(ns.approved_usd) - float(est["total_usd"])) > 0.005:
        raise SystemExit(f"refusing: --approved-usd differs from the estimate's total ({est['total_usd']})")
    if float(est["total_usd"]) > APPROVAL_CAP_USD:
        raise SystemExit(f"refusing: the estimate ${est['total_usd']} is above ${APPROVAL_CAP_USD:.0f}; stop and ask Aravind")
    plan = load_plan(out_dir)
    inp = load_inputs(ns)
    bad = lg.manifest_mismatches(items, inputs_sha256=inp["sha256"], script_sha256=lg.file_sha256(Path(__file__)),
                                 cfg_sha256=config_sha256(plan), deps=dependency_hashes())
    if items.get("stratum_plan_sha256") != lg.file_sha256(out_dir / "stratum-plan.json"):
        bad.append("stratum_plan")
    if items.get("quiet_set_inputs_sha256") != inp["quiet_inputs_sha256"]:
        bad.append("quiet_set_inputs")
    triples = triples_for(rows, inp)
    packets = lg.all_packets(rows, triples, inp["day0"])
    if items.get("packets_sha256") != lg.packets_sha256(packets) or items.get("day0_sha256") != lg.day0_sha256(inp["day0"]):
        bad.append("rendering")
    if bad:
        raise SystemExit(f"refusing: the run differs from the committed manifest: {sorted(bad)}")
    if set(routes["chosen"]) != set(lg.FAMILIES) or not routes["checks"]["scorer:bedrock"]["accepted"]:
        raise SystemExit("refusing: a reader or the scorer has no accepted route")
    if not est.get("routes_known") or any(est["families"][f]["route"] != c["route"] or est["families"][f]["model"] != c["model"]
                                          for f, c in routes["chosen"].items()):
        raise SystemExit("refusing: the estimate was not priced on the routes found (re-run dry-run)")
    if lg.any_cache_records(out_dir) and not ns.resume:
        raise SystemExit("refusing: calls are already on file; pass --resume to continue this run")
    lg.check_reasoning_env()
    k = int(items["samples_per_condition"])
    stop = float(est["stop_at_usd"])
    guard = lg.SpendGuard(stop, offset_usd=lg.route_ledger_usd(out_dir))
    readers = {f: lg.make_reader(f, routes["chosen"][f]["route"], routes["chosen"][f]["model"],
                                 lg.reader_cache(out_dir, f, routes["chosen"][f]["model"]), models, cap=stop, guard=guard) for f in lg.FAMILIES}
    scorer = lg.make_scorer(lg.scorer_cache(out_dir), cap=stop, guard=guard)
    drift = {f: lg.cache_drift(c, lg.READER_SYSTEM) for f, c in readers.items()}
    drift["scorer"] = lg.cache_drift(scorer, lg.SCORER_SYSTEM)
    if any(drift.values()):
        raise SystemExit(f"refusing: cached records under another system prompt or max_tokens: {drift}")
    guard.clients = list(readers.values()) + [scorer]
    log = out_dir / "run-batches.jsonl"
    nulls = [r for r in rows if r["regime"] in NULL_REGIMES]
    cands = [r for r in rows if r["regime"] == "candidate"]
    summary: dict[str, Any] = {"stop_at_usd": round(stop, 2), "resume": bool(ns.resume), "samples_per_condition": k,
                               "approval": {"estimate_usd": est["total_usd"], "cap_usd": APPROVAL_CAP_USD, "rule": APPROVAL_RULE}}

    async def both() -> None:   # one event loop: the clients' semaphores bind to the loop they first ran in
        summary["nulls"] = await run_phase("nulls", nulls, packets, readers, scorer, rubrics, guard, log, 0, k)
        if lg.phase_must_stop(summary["nulls"], guard):
            summary["candidates"] = {"skipped": True}
            return
        summary["candidates"] = await run_phase("candidates", cands, packets, readers, scorer, rubrics, guard, log, 10, k)
    asyncio.run(both())
    summary["dollars"] = {**{f: round(c.total_spent(), 4) for f, c in readers.items()}, "scorer": round(scorer.total_spent(), 4),
                          "routes": guard.offset_usd, "total": round(guard.total(), 4)}
    (out_dir / "run-summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    lg.emit(lg.strip_reasons(summary))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 25: B3's comprehension run and the T1 join")
    ap.add_argument("mode", choices=("plan", "items", "prices", "dry-run", "routes", "run"))
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--key-b3", default=str(S3 / "b3" / "rater" / "key-b3.json"))
    ap.add_argument("--triples-b3", default=str(S3 / "b3" / "rater" / "stripped-triples-b3.json"))
    for part, stem in (("candidates", "payloads-b3-candidates"), ("controls", "controls-b3")):
        for w in WRITERS:
            ap.add_argument(f"--{part}-{w}", default=str(S3 / "b3" / f"{stem}-{w}.json"))
    ap.add_argument("--t1-items", default=str(S3 / "legibility" / "items-v0.json"))
    ap.add_argument("--t1-triples", default=str(S3 / "t1k-rater" / "stripped-triples.json"))
    ap.add_argument("--payloads-v2", default=str(S3 / "t1v2" / "payloads-v2.json"))
    ap.add_argument("--day0-md", default=str(S3 / "t1k-rater" / "doc-states-day0.md"))
    ap.add_argument("--approved-usd", type=float, default=None)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--force", action="store_true")
    ns = ap.parse_args(argv)
    if ns.mode in ("run", "routes") and ns.approved_usd is None:
        raise SystemExit("refusing: this mode needs --approved-usd (the dry-run estimate, at or under the approval cap)")
    fn = {"plan": mode_plan, "items": mode_items, "prices": mode_prices, "dry-run": mode_dry_run, "routes": mode_routes,
          "run": mode_run}[ns.mode]
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
