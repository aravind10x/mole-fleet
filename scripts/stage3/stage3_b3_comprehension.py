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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 25: B3's comprehension run and the T1 join")
    ap.add_argument("mode", choices=("plan",))
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--force", action="store_true")
    ns = ap.parse_args(argv)
    fn = {"plan": mode_plan}[ns.mode]
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
