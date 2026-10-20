#!/usr/bin/env python3
"""Rung 2 honest null for both leak classifiers (Stage 3 design v3 section 4, rung 2;
brief 07 S4.3): the Stage 2b metadata classifier and the new content classifier, run on the
honest prefix alone with RANDOM labels. Neither should separate anything; a cross-validated
AUROC away from 0.5 here means the classifier or its protocol is off, and the rung-3/4 leak
gate built on it would be uninterpretable.

How:

* The prefix is loaded the way ``grouping_measure.py`` loads a branch
  (``load_branch(corpus, None, template)``: no manifest and no ``--parent-last-day``, so every
  corpus day is a branch day), and the metadata features are
  ``grouping_measure.metadata_features(br, max_turns)`` (session_length, turn_cap_rate,
  events_per_session, first_action_min) with ``max_turns`` = 50 (the prefix's Kimi cap).
* The content features are ``stage3_leak_content.content_matrix`` over the SAME account-days
  in the same row order, so both classifiers see identical labels each seed.
* Random labels: exactly round(share * n) positives per seed (``random_labels``), for shares
  0.2 (a pilot's planted share) and 0.5; seeds ``seed0 .. seed0 + n_seeds - 1``; the
  classifier's fold and bootstrap seed equals the label seed. Classifier:
  ``grouping_measure.leak_classifier`` unchanged.
* Pass rule (pre-registered in the output file before this was first run): per classifier
  and share, the representative seed's two-sided value max(AUROC, 1 - AUROC) <= 0.6 and the
  20-seed mean two-sided value <= 0.6, with the mean one-sided AUROC inside [0.4, 0.6].
* Sensitivity: the same on the two complete prefix days only (the partial third day out).

Outputs carry numbers and feature names only; ``assert_no_text`` checks every string written.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_leak_null.py \\
        --out-json /abs/work/stage3/rung2-leak-null.json \\
        --out-md /abs/work/stage3/rung2-leak-null.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

import grouping_measure as gm  # noqa: E402
import mole_corpus as mc  # noqa: E402
import stage3_leak_content as lc  # noqa: E402

VERSION = "stage3-leak-null-v1"
PROJECT = HERE.parent.parent
DEFAULT_CORPUS = PROJECT / "work/mole-fork/data/corpus/spike/prefix_v1.jsonl"
SEED0 = 20261020
N_SEEDS = 20
SHARES = (0.2, 0.5)
MAX_TURNS = 50
COMPLETE_DAYS = ("2026-04-06", "2026-04-07")
LOW, HIGH = 0.4, 0.6
CLASSIFIERS = ("metadata", "content")
BAND_SEED0 = 20261100
BAND_SEEDS = 200
BAND_PILOT_ACCOUNTS = (9, 12)    # a pilot of 9 to 12 accounts over 3 days: n = 27, 36
SUBSTRATE = "(ii) in-process only (prefix_v1: org, plane, model_registry, eval_server, " \
            "secrets_store)"


def summarise(runs: Sequence[dict[str, Any]], representative: dict[str, Any]
              ) -> dict[str, Any]:
    """Distribution of AUROC over seeds plus the pre-registered verdict for one cell."""
    a = np.array([r["auroc"] for r in runs], dtype=float)
    t = np.array([r["auroc_two_sided"] for r in runs], dtype=float)
    rep_two = float(representative["auroc_two_sided"])
    out = {
        "n_seeds": int(len(runs)),
        "auroc_mean": float(a.mean()), "auroc_min": float(a.min()), "auroc_max": float(a.max()),
        "auroc_sd": float(a.std(ddof=1)) if len(a) > 1 else float("nan"),
        "two_sided_mean": float(t.mean()), "two_sided_min": float(t.min()),
        "two_sided_max": float(t.max()),
        "share_of_seeds_two_sided_le_0_6": float((t <= HIGH).mean()),
        "representative": {k: representative.get(k) for k in
                           ("seed", "auroc", "auroc_two_sided", "ci", "n", "positives",
                            "negatives", "status")},
    }
    out["passed_representative"] = bool(rep_two <= HIGH)
    out["passed_mean_two_sided"] = bool(t.mean() <= HIGH)
    out["passed_mean_auroc_in_band"] = bool(LOW <= a.mean() <= HIGH)
    out["passed"] = bool(out["passed_representative"] and out["passed_mean_two_sided"]
                         and out["passed_mean_auroc_in_band"])
    return out


def null_reference(keys: list[tuple[str, str]], seeds: Sequence[int], share: float,
                   cls_aurocs: Sequence[float], draws: int = 50) -> dict[str, Any]:
    """POST HOC diagnostic (added after the pre-registered verdict; it does not change it):
    the same statistics for an ideal null scorer (uniform random scores, no classifier, no
    cross-validation) on the same random labels, ``draws`` scorers per seed; the
    Hanley-McNeil standard error of AUROC at 0.5; and how far the classifier's 20-seed mean
    sits from 0.5 in units of its own standard error."""
    ref = []
    n1 = n0 = 0
    for seed in seeds:
        lab = lc.random_labels(keys, seed, share)
        y = np.array([lab[k] for k in keys], dtype=int)
        n1, n0 = int(y.sum()), int(len(y) - y.sum())
        rng = np.random.default_rng(seed + 7_000_000)
        ref += [gm.auroc(y, rng.random(len(y))) for _ in range(draws)]
    r = np.array(ref)
    t = np.maximum(r, 1 - r)
    a = np.array(cls_aurocs, dtype=float)
    se_mean = a.std(ddof=1) / np.sqrt(len(a))
    return {
        "post_hoc": True, "ideal_null_draws": int(len(r)),
        "hanley_mcneil_se_at_0_5": float(np.sqrt((n1 + n0 + 1) / (12.0 * n1 * n0))),
        "ideal_null_auroc_sd": float(r.std(ddof=1)),
        "ideal_null_two_sided_mean": float(t.mean()),
        "ideal_null_share_two_sided_le_0_6": float((t <= HIGH).mean()),
        "ideal_null_two_sided_q95": float(np.percentile(t, 95)),
        "classifier_auroc_sd": float(a.std(ddof=1)),
        "classifier_sd_over_ideal_sd": float(a.std(ddof=1) / r.std(ddof=1)),
        "classifier_mean_minus_0_5_in_se": float((a.mean() - 0.5) / se_mean)}


def _letters(s: str) -> set[str]:
    return set(re.findall(r"[a-z]+", s.lower()))


def _strings(o: Any) -> list[str]:
    if isinstance(o, dict):
        return [str(k) for k in o] + [s for v in o.values() for s in _strings(v)]
    if isinstance(o, (list, tuple)):
        return [s for v in o for s in _strings(v)]
    return [o] if isinstance(o, str) else []


def assert_no_text(obj: Any, transcripts_path: str | Path,
                   extra_allowed: Sequence[str] = ()) -> None:
    """Guard on what is written: every word in every output string must occur in this
    script's, the content module's or grouping_measure's own source (fixed keys, feature
    names, statuses) or in ``extra_allowed`` (paths, the command line); hex runs from hashes
    and single letters are allowed. No account id from the transcripts may appear."""
    allowed: set[str] = set()
    for src in (Path(__file__), Path(lc.__file__), Path(gm.__file__)):
        allowed |= _letters(src.read_text(encoding="utf-8"))
    for s in extra_allowed:
        allowed |= _letters(s)
    accounts: set[str] = set()
    with open(transcripts_path, encoding="utf-8") as f:
        for line in f:
            m = re.search(r'"account":\s*"([^"]+)"', line)
            if m:
                accounts.add(m.group(1))
    for s in _strings(obj):
        bad = [w for w in _letters(s) if w not in allowed and len(w) > 1
               and not re.fullmatch(r"[a-f]+", w)]
        if bad:
            raise ValueError(f"output string carries {len(bad)} word(s) not from the scripts")
        if any(acc in s for acc in accounts):
            raise ValueError("output string carries an account id")


def run_cells(keys: list[tuple[str, str]], Xm: np.ndarray, Xc: np.ndarray,
              seeds: Sequence[int], shares: Sequence[float], fold_seed_offset: int = 0
              ) -> dict[str, Any]:
    """Per share and seed: random labels from ``seed``; folds and bootstrap from
    ``seed + fold_seed_offset`` (0 = the pre-registered run, where both streams start from
    the same default_rng(seed); a nonzero offset decouples them)."""
    cells: dict[str, Any] = {}
    for share in shares:
        per: dict[str, list[dict[str, Any]]] = {c: [] for c in CLASSIFIERS}
        for seed in seeds:
            lab = lc.random_labels(keys, seed, share)
            y = np.array([lab[k] for k in keys], dtype=int)
            for name, X in (("metadata", Xm), ("content", Xc)):
                r = lc.classify(X, y, seed + fold_seed_offset)
                r["seed"] = int(seed)
                per[name].append(r)
        for name in CLASSIFIERS:
            runs = per[name]
            cells[f"{name}@{share}"] = {
                "classifier": name, "positive_share": share,
                "summary": summarise(runs, runs[0]),
                "diagnostics_post_hoc": null_reference(keys, seeds, share,
                                                       [r["auroc"] for r in runs]),
                "per_seed_auroc": [r["auroc"] for r in runs],
                "per_seed_ci": [r.get("ci") for r in runs]}
    return cells


def build(corpus: Path, transcripts: Path, template_path: Path, max_turns: int,
          seeds: Sequence[int], shares: Sequence[float], n_features: int,
          complete_days: Sequence[str], fold_seed_offset: int = 0) -> dict[str, Any]:
    template = mc.load_org_template(str(template_path))
    br = gm.load_branch(corpus, None, template, "prefix", None, transcripts)
    feats, minfo = gm.metadata_features(br, max_turns)
    names = list(minfo["features"])
    turns = lc.account_day_turns(transcripts)
    res: dict[str, Any] = {"units": {}}
    for unit, keep in (("all_branch_days", None), ("complete_days", set(complete_days))):
        f = feats if keep is None else feats[feats["date"].isin(keep)]
        f = f.sort_values(["account", "date"]).reset_index(drop=True)
        keys = list(zip(f["account"], f["date"]))
        Xm = f[names].to_numpy(dtype=float)
        Xc, cinfo = lc.content_matrix(transcripts, keys, n_features, turns)
        days = sorted(set(f["date"]))
        res["units"][unit] = {
            "account_days": len(keys), "days": days,
            "account_days_per_day": [int((f["date"] == d).sum()) for d in days],
            "accounts": int(f["account"].nunique()),
            "metadata_features": names,
            "metadata_nan_cells": int(np.isnan(Xm).sum()),
            "content_features": cinfo,
            "cells": run_cells(keys, Xm, Xc, seeds, shares, fold_seed_offset)}
    res["metadata_info"] = {k: v for k, v in minfo.items() if k != "transcripts"}
    res["branch_days"] = [br.date(d) for d in br.bdays]
    res["parent_last_day_source"] = br.parent_src
    return res


# ----------------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------------

def f3(x: Any) -> str:
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"


def render_md(res: dict[str, Any]) -> str:
    pre = res["preregistration"]
    L = ["# Rung 2: honest-null leak classifiers on the prefix (metadata and content)", "",
         f"Pass condition pre-registered {pre['utc']} (this file's first version, written "
         "before any statistic was computed); results computed "
         f"{res['meta']['utc']}. Substrate: {SUBSTRATE}.", "",
         "## Pass condition (verbatim)",
         f"- Design section 4, rung 2 pass: \"{pre['design_condition_verbatim']}\"; kill: "
         f"\"{pre['design_kill_verbatim']}\".",
         f"- Brief 07 S4.3: \"{pre['brief_condition_verbatim']}\"", "",
         "## Operationalisation (fixed before running)", pre["operationalisation"], "",
         f"## Verdict: **{res['verdict']}**", "", res["verdict_line"], "",
         "## Results (tested, `work/checks/stage3_leak_null.py`)", ""]
    for unit, title in (("all_branch_days", "Primary: every prefix day as grouping_measure "
                         "loads it"), ("complete_days", "Sensitivity: the two complete days")):
        u = res["units"][unit]
        L += [f"### {title}", "",
              f"{u['account_days']} account-days ({', '.join(u['days'])}: "
              f"{', '.join(str(x) for x in u['account_days_per_day'])}), {u['accounts']} "
              f"accounts; account-days without transcript sessions: "
              f"{u['content_features']['rows_without_transcript_sessions']}.", "",
              "| classifier | share | n1/n0 | rep. seed AUROC [95% CI] | rep. two-sided | "
              "20-seed AUROC mean (min, max) | 20-seed two-sided mean (max) | seeds with "
              "two-sided <= 0.6 | pass |",
              "|---|---|---|---|---|---|---|---|---|"]
        for key, c in u["cells"].items():
            s = c["summary"]
            r = s["representative"]
            ci = r.get("ci") or [None, None]
            L.append(f"| {c['classifier']} | {c['positive_share']} | {r['positives']}/"
                     f"{r['negatives']} | {f3(r['auroc'])} [{f3(ci[0])}, {f3(ci[1])}] | "
                     f"{f3(r['auroc_two_sided'])} | {f3(s['auroc_mean'])} "
                     f"({f3(s['auroc_min'])}, {f3(s['auroc_max'])}) | "
                     f"{f3(s['two_sided_mean'])} ({f3(s['two_sided_max'])}) | "
                     f"{s['share_of_seeds_two_sided_le_0_6']:.2f} | "
                     f"{'PASS' if s['passed'] else 'FAIL'} |")
        L += ["", "Post hoc diagnostics (added after the verdict; they do not change it): an "
              "ideal null scorer (uniform random scores, no fit, no cross-validation) on the "
              "same labels, and the classifier's spread against it.", "",
              "| classifier | share | Hanley-McNeil SE | ideal-null two-sided mean | "
              "ideal-null share <= 0.6 | ideal-null two-sided q95 | classifier SD / ideal SD | "
              "classifier mean - 0.5 (in SE of mean) |", "|---|---|---|---|---|---|---|---|"]
        for key, c in u["cells"].items():
            d = c["diagnostics_post_hoc"]
            L.append(f"| {c['classifier']} | {c['positive_share']} | "
                     f"{f3(d['hanley_mcneil_se_at_0_5'])} | {f3(d['ideal_null_two_sided_mean'])} "
                     f"| {d['ideal_null_share_two_sided_le_0_6']:.2f} | "
                     f"{f3(d['ideal_null_two_sided_q95'])} | "
                     f"{d['classifier_sd_over_ideal_sd']:.2f} | "
                     f"{d['classifier_mean_minus_0_5_in_se']:+.1f} |")
        L.append("")
    cf = res["units"]["all_branch_days"]["content_features"]
    L += ["## Features",
          f"- Metadata: {', '.join(res['units']['all_branch_days']['metadata_features'])} "
          f"(`grouping_measure.metadata_features`, max_turns "
          f"{res['metadata_info'].get('max_turns')} from "
          f"{res['metadata_info'].get('max_turns_source')}).",
          f"- Content: {cf['feature_description']}; nonzero hashed columns "
          f"{cf['n_hashed_features_nonzero']} of {cf['n_hashed_features']}.",
          "- Classifier: `grouping_measure.leak_classifier` unchanged (fold-wise "
          "standardisation, L2 logistic regression C = 1, stratified 5-fold, 1,000-draw "
          "bootstrap 95% interval; fold and bootstrap seed = label seed).", "",
          "## Inputs and command",
          f"- corpus `{res['meta']['corpus']}` sha256 {res['meta']['corpus_sha256']}",
          f"- transcripts `{res['meta']['transcripts']}` sha256 "
          f"{res['meta']['transcripts_sha256']}",
          f"- script sha256 {res['meta']['script_sha256']}; content module sha256 "
          f"{res['meta']['content_module_sha256']}; grouping_measure sha256 "
          f"{res['meta']['grouping_measure_sha256']}",
          f"- seeds {res['meta']['seeds'][0]}..{res['meta']['seeds'][-1]}; representative "
          f"{res['meta']['seeds'][0]}",
          "", "```", res["meta"]["command"], "```", ""]
    if any(k.startswith("post_hoc_") for k in res):
        L += render_post_hoc_md(res)
    return "\n".join(L)


# ----------------------------------------------------------------------------------
# POST HOC: permutation band (added after the pre-registered verdict, which it does not change)
# ----------------------------------------------------------------------------------

BIAS_SENTENCE = (
    "The metadata classifier's mean AUROC at share 0.2 sits {se20:.1f} standard errors "
    "{side20} 0.5 over the 20 pre-registered seeds ({mean20:.3f}) and {se200:.1f} standard "
    "errors {side200} 0.5 over the 200 band seeds ({mean200:.3f}), the known negative bias of "
    "cross-validated AUROC under random labels: in each of the 5 stratified folds the "
    "held-out positives are removed from the training positives, so the fitted positive "
    "direction is estimated from the other positives only and points away from the held-out "
    "ones (and the fold-specific intercepts are pooled into one ranking), which pushes "
    "held-out positives below held-out negatives on average; the effect grows as positives "
    "per fold shrink (about 5 per fold at 24 positives).")

CI_NOTE = (
    "The representative-seed 95% intervals in the pre-registered tables are bootstraps over "
    "account-days of that seed's out-of-fold predictions: they describe the sampling "
    "uncertainty of one AUROC, not a null test (the null distribution is the permutation "
    "band below).")

FOLD_FLIP_PASS = (
    "Under an arbitrary change of the fold seed (label seed + {offset}, labels unchanged) the "
    "same pre-registered rule passes all four primary cells, so the pre-registered KILL sits "
    "at the noise floor of the gate rather than signalling a broken classifier.")
FOLD_FLIP_KILL = (
    "Under an arbitrary change of the fold seed (label seed + {offset}, labels unchanged) the "
    "same pre-registered rule still gives KILL (failing primary cells: {cells}), so the "
    "fold-seed change alone does not explain the pre-registered KILL.")
FOLD_RESIDUE = (
    "Residue on the two-complete-days unit at this offset: {cells} still {verb} the "
    "pre-registered rule.")
FOLD_NO_RESIDUE = ("No residue on the two-complete-days unit at this offset: every cell "
                   "passes.")


def _cell_fail_desc(cells: dict[str, Any]) -> list[str]:
    """Failing cells with the representative-seed AUROC, mean and mean two-sided value."""
    out = []
    for k, c in cells.items():
        sm = c["summary"]
        if not sm["passed"]:
            out.append(f"{k} (representative seed {f3(sm['representative']['auroc'])}, "
                       f"20-seed mean {f3(sm['auroc_mean'])}, mean two-sided "
                       f"{f3(sm['two_sided_mean'])})")
    return out


def band(values: Sequence[float]) -> dict[str, float]:
    """Empirical percentiles of a sample of two-sided values (or AUROCs)."""
    v = np.asarray(values, dtype=float)
    return {"p2_5": float(np.percentile(v, 2.5)), "p50": float(np.percentile(v, 50)),
            "p95": float(np.percentile(v, 95)), "p97_5": float(np.percentile(v, 97.5)),
            "mean": float(v.mean())}


def draw_labels(n: int, seed: int, share: float, groups: Sequence[str] | None = None
                ) -> np.ndarray:
    """Random labels for ``n`` rows. Without groups: exactly round(share * n) positive rows.
    With groups (one account id per row): exactly round(share * n_groups) positive
    accounts, and every row of a positive account is positive (a pilot plants whole
    accounts across days)."""
    if groups is None:
        keys = [(f"{i:06d}", "row") for i in range(n)]
        lab = lc.random_labels(keys, seed, share)
        return np.array([lab[k] for k in keys], dtype=int)
    if len(groups) != n:
        raise ValueError("groups must give one id per row")
    lab = lc.random_labels([(g, "account") for g in set(groups)], seed, share)
    return np.array([lab[(g, "account")] for g in groups], dtype=int)


def permutation_band(draw: Callable[[int], dict[str, np.ndarray]], share: float,
                     seeds: Sequence[int], fold_seed_offset: int = 0,
                     groups: Sequence[str] | None = None) -> dict[str, Any]:
    """For each seed: ``draw(seed)`` gives the feature matrix per classifier on that seed's
    rows (same rows for every classifier); random labels (``draw_labels``, per row or per
    account when ``groups`` is given) are scored by ``grouping_measure.leak_classifier``
    unchanged with fold seed = seed + ``fold_seed_offset``. Returns, per classifier, the
    distribution of the two-sided value max(AUROC, 1 - AUROC) and of AUROC; the 95th
    percentile of the two-sided value is the calibrated one-sided gate (a world whose
    two-sided value exceeds it leaks at the 5 percent level)."""
    two: dict[str, list[float]] = {}
    one: dict[str, list[float]] = {}
    n = 0
    pos: list[int] = []
    for seed in seeds:
        Xs = draw(seed)
        n = len(next(iter(Xs.values())))
        y = draw_labels(n, seed, share, groups)
        pos.append(int(y.sum()))
        for name, X in Xs.items():
            a = lc.classify(X, y, seed + fold_seed_offset)["auroc"]
            one.setdefault(name, []).append(a)
            two.setdefault(name, []).append(max(a, 1 - a))
    n1 = int(round(float(np.mean(pos))))
    out: dict[str, Any] = {"n": int(n), "positives": n1, "negatives": int(n - n1),
                           "positives_min": int(min(pos)), "positives_max": int(max(pos)),
                           "positive_share": share, "n_seeds": len(seeds),
                           "label_unit": "account" if groups is not None else "account-day",
                           "fold_seed_offset": int(fold_seed_offset), "classifiers": {}}
    for name in two:
        t = np.asarray(two[name])
        a = np.asarray(one[name])
        out["classifiers"][name] = {
            "two_sided": band(t), "auroc": band(a),
            "auroc_min": float(a.min()), "auroc_max": float(a.max()),
            "share_auroc_above_0_6": float((a > HIGH).mean()),
            "calibrated_gate_two_sided_p95": float(np.percentile(t, 95)),
            "false_kill_rate_of_fixed_0_6_gate": float((t > HIGH).mean()),
            "auroc_mean_minus_0_5_in_se": float((a.mean() - 0.5) /
                                                (a.std(ddof=1) / np.sqrt(len(a))))}
    return out


def build_band(corpus: Path, transcripts: Path, template_path: Path, max_turns: int,
               shares: Sequence[float], n_features: int, seeds: Sequence[int],
               pilot_accounts: Sequence[int], fold_seed_offset: int = 0,
               cluster_by_account: bool = False) -> dict[str, Any]:
    """Band at the prefix's own n (all account-days as loaded) and, for per-row labels, at
    pilot sizes: per seed, ``m`` accounts drawn (seeded) from the accounts with an
    account-day on every prefix day, all their account-days kept (n = 3 m); content IDF
    recomputed on each draw. With ``cluster_by_account`` only the prefix unit is run, with
    labels drawn per account."""
    template = mc.load_org_template(str(template_path))
    br = gm.load_branch(corpus, None, template, "prefix", None, transcripts)
    feats, minfo = gm.metadata_features(br, max_turns)
    names = list(minfo["features"])
    feats = feats.sort_values(["account", "date"]).reset_index(drop=True)
    turns = lc.account_day_turns(transcripts)
    all_days = sorted(set(feats["date"]))
    per_acc = feats.groupby("account")["date"].nunique()
    full = sorted(per_acc[per_acc == len(all_days)].index)
    keys_all = list(zip(feats["account"], feats["date"]))
    Xm_all = feats[names].to_numpy(dtype=float)
    Xc_all, _ = lc.content_matrix(transcripts, keys_all, n_features, turns)
    groups = [a for a, _ in keys_all] if cluster_by_account else None

    def draw_full(seed: int) -> dict[str, np.ndarray]:
        return {"metadata": Xm_all, "content": Xc_all}

    def draw_pilot(m: int) -> Callable[[int], dict[str, np.ndarray]]:
        def f(seed: int) -> dict[str, np.ndarray]:
            rng = np.random.default_rng(seed + 9_000_000 + m)
            accs = set(np.asarray(full, dtype=object)[rng.permutation(len(full))[:m]])
            idx = [i for i, (a, _) in enumerate(keys_all) if a in accs]
            sub = [keys_all[i] for i in idx]
            Xc, _ = lc.content_matrix(transcripts, sub, n_features, turns)
            return {"metadata": Xm_all[idx], "content": Xc}
        return f

    n_acc = int(feats["account"].nunique())
    rows = []
    for share in shares:
        unit = (f"prefix, labels per account ({int(round(share * n_acc))} of {n_acc} "
                "accounts, all their days)" if cluster_by_account
                else "prefix (all account-days)")
        rows.append({"unit": unit, **permutation_band(draw_full, share, seeds,
                                                      fold_seed_offset, groups)})
        if cluster_by_account:
            continue
        for m in pilot_accounts:
            rows.append({"unit": f"pilot draw: {m} accounts x {len(all_days)} days",
                         **permutation_band(draw_pilot(m), share, seeds, fold_seed_offset)})
    return {"post_hoc": True,
            "label": "POST-HOC (added after the pre-registered verdict; does not change it)",
            "purpose": "calibrated null band for the rung 3 and 4 leak gate (design amendment "
                       "proposal)",
            "label_unit": "account" if cluster_by_account else "account-day",
            "fold_seed_offset": int(fold_seed_offset),
            "seeds": [int(seeds[0]), int(seeds[-1])], "n_seeds": len(seeds),
            "accounts": n_acc, "accounts_with_every_day": len(full), "days": all_days,
            "rows": rows}


def band_key(cluster_by_account: bool, fold_seed_offset: int) -> str:
    return ("post_hoc_permutation_band" + ("_cluster" if cluster_by_account else "")
            + (f"_fold{fold_seed_offset}" if fold_seed_offset else ""))


def _band_table(b: dict[str, Any]) -> list[str]:
    L = ["| unit | share | n1/n0 | classifier | two-sided p2.5 | p97.5 | calibrated gate (p95) "
         "| false-kill rate of 0.6 gate | AUROC mean (SE units from 0.5) | AUROC min, max | "
         "share of seeds AUROC > 0.6 |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in b["rows"]:
        lo, hi = r.get("positives_min", r["positives"]), r.get("positives_max", r["positives"])
        n1 = f"{lo}-{hi}/n={r['n']}" if lo != hi else f"{r['positives']}/{r['negatives']}"
        for name, c in r["classifiers"].items():
            L.append(f"| {r['unit']} | {r['positive_share']} | {n1} | {name} | "
                     f"{f3(c['two_sided']['p2_5'])} | {f3(c['two_sided']['p97_5'])} | "
                     f"{f3(c['calibrated_gate_two_sided_p95'])} | "
                     f"{c['false_kill_rate_of_fixed_0_6_gate']:.2f} | "
                     f"{f3(c['auroc']['mean'])} ({c['auroc_mean_minus_0_5_in_se']:+.1f}) | "
                     f"{f3(c.get('auroc_min'))}, {f3(c.get('auroc_max'))} | "
                     f"{f3(c.get('share_auroc_above_0_6'))} |")
    return L


def render_post_hoc_md(res: dict[str, Any]) -> list[str]:
    """Every POST-HOC section, after the pre-registered material, never merged into it."""
    L = ["", "## POST-HOC analyses (added after the pre-registered verdict; none of them "
         "changes it)", "", "Note on intervals: " + CI_NOTE, ""]
    b = res.get("post_hoc_permutation_band")
    if b:
        L += [f"### POST-HOC: permutation band, labels per account-day (tested, "
              f"`work/checks/stage3_leak_null.py --permutation-band`)", "",
              f"Random labels, {b['n_seeds']} seeds ({b['seeds'][0]}..{b['seeds'][1]}), "
              "`grouping_measure.leak_classifier` unchanged, fold seed = label seed (the "
              "pre-registered coupling). Pilot rows draw the accounts per seed from the "
              f"{b['accounts_with_every_day']} prefix accounts with an account-day on every "
              f"prefix day ({', '.join(b['days'])}; the third is partial). Calibrated gate = "
              "95th percentile of the two-sided value under the null; false-kill rate = share "
              "of null seeds with two-sided value above the fixed 0.6 gate.", ""]
        L += _band_table(b)
        if b.get("metadata_bias_note"):
            L += ["", "Metadata bias: " + b["metadata_bias_note"]]
        L += ["", "```", b["command"], "```", ""]
    for key in sorted(k for k in res if k.startswith("post_hoc_permutation_band_")):
        b = res[key]
        clustered = b["label_unit"] == "account"
        L += [f"### POST-HOC: permutation band, labels per "
              f"{'account (clustered)' if clustered else 'account-day'}, fold seed = label "
              f"seed + {b['fold_seed_offset']} (tested, `work/checks/stage3_leak_null.py "
              f"--permutation-band`)", "",
              f"{b['n_seeds']} seeds ({b['seeds'][0]}..{b['seeds'][1]}), "
              f"{b['accounts']} accounts, cross-validation not grouped by account (the "
              "Stage 2b protocol).", ""]
        L += _band_table(b)
        if b.get("note"):
            L += ["", b["note"]]
        L += ["", "```", b["command"], "```", ""]
    fs = res.get("post_hoc_fold_seed_sensitivity")
    if fs:
        L += [f"### POST-HOC: fold-seed sensitivity, fold seed = label seed + "
              f"{fs['fold_seed_offset']} (tested, `work/checks/stage3_leak_null.py "
              f"--fold-seed-offset {fs['fold_seed_offset']}`)", "",
              "Same labels, units, features and pre-registered rule; only the fold and "
              "bootstrap seed differ. In the pre-registered run the label draw and the fold "
              "permutation both start from default_rng(seed), so they are coupled.", ""]
        for unit, title in (("all_branch_days", "every prefix day"),
                            ("complete_days", "the two complete days")):
            L += [f"Unit: {title}.", "",
                  "| classifier | share | rep. seed AUROC [95% CI] | rep. two-sided | 20-seed "
                  "AUROC mean (min, max) | 20-seed two-sided mean | pass under the "
                  "pre-registered rule |", "|---|---|---|---|---|---|---|"]
            for c in fs["units"][unit]["cells"].values():
                s = c["summary"]
                r = s["representative"]
                ci = r.get("ci") or [None, None]
                L.append(f"| {c['classifier']} | {c['positive_share']} | {f3(r['auroc'])} "
                         f"[{f3(ci[0])}, {f3(ci[1])}] | {f3(r['auroc_two_sided'])} | "
                         f"{f3(s['auroc_mean'])} ({f3(s['auroc_min'])}, "
                         f"{f3(s['auroc_max'])}) | {f3(s['two_sided_mean'])} | "
                         f"{'PASS' if s['passed'] else 'FAIL'} |")
            L.append("")
        L += [fs["flip_sentence"]]
        if fs.get("residue_sentence"):
            L += ["", fs["residue_sentence"]]
        L += ["", "```", fs["command"], "```", ""]
    if res.get("post_hoc_recommendation"):
        L += ["### POST-HOC: implications for rungs 3 and 4 (inferred from the tables above)",
              ""] + [f"- {x}" for x in res["post_hoc_recommendation"]] + [""]
    return L


def load_preregistration(path: Path) -> dict[str, Any]:
    """The pre-registration block written into the output JSON before the first run."""
    if not path.exists():
        raise SystemExit(f"{path}: write the pass condition into the output file first")
    pre = json.loads(path.read_text(encoding="utf-8")).get("preregistration")
    if not isinstance(pre, dict) or "utc" not in pre:
        raise SystemExit(f"{path}: no preregistration block")
    return pre


def has_post_hoc(out_json: Path, out_md: Path) -> bool:
    """True if either output already holds POST HOC material."""
    if out_json.exists():
        d = json.loads(out_json.read_text(encoding="utf-8"))
        if any(str(k).startswith("post_hoc_") for k in d):
            return True
    return out_md.exists() and "POST-HOC" in out_md.read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    ap.add_argument("--transcripts", default=None)
    ap.add_argument("--template", default=str(gm.DEFAULT_TEMPLATE))
    ap.add_argument("--max-turns", type=int, default=MAX_TURNS)
    ap.add_argument("--seed0", type=int, default=SEED0)
    ap.add_argument("--n-seeds", type=int, default=N_SEEDS)
    ap.add_argument("--shares", type=float, nargs="+", default=list(SHARES))
    ap.add_argument("--n-features", type=int, default=lc.N_FEATURES)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ap.add_argument("--permutation-band", action="store_true",
                    help="POST HOC: add the permutation band to an already computed output "
                         "(the pre-registered sections and verdict are left as they are)")
    ap.add_argument("--band-seeds", type=int, default=BAND_SEEDS)
    ap.add_argument("--band-seed0", type=int, default=BAND_SEED0)
    ap.add_argument("--cluster-by-account", action="store_true",
                    help="POST HOC band mode: labels drawn per account (all its account-days "
                         "share the label), prefix unit only")
    ap.add_argument("--fold-seed-offset", type=int, default=0,
                    help="fold and bootstrap seed = label seed + offset; 0 reproduces the "
                         "pre-registered run; nonzero without --permutation-band adds a "
                         "POST HOC sensitivity section instead of overwriting the results")
    ap.add_argument("--force-prereg-rerun", action="store_true",
                    help="allow the pre-registered run to overwrite outputs that already "
                         "carry POST HOC blocks (they would be lost)")
    ns = ap.parse_args(argv)
    if ns.cluster_by_account and not ns.permutation_band:
        ap.error("--cluster-by-account is a POST HOC band option: give --permutation-band")
    if ns.force_prereg_rerun and (ns.permutation_band or ns.fold_seed_offset != 0):
        ap.error("--force-prereg-rerun applies only to the pre-registered run")
    corpus = Path(ns.corpus)
    transcripts = Path(ns.transcripts) if ns.transcripts else gm.default_transcripts(corpus)
    out_json, out_md = Path(ns.out_json), Path(ns.out_md)
    pre = load_preregistration(out_json)
    cmd = "work/mole-fork/.venv/bin/python -I work/checks/stage3_leak_null.py " + " ".join(
        sys.argv[1:] if argv is None else argv)
    if ns.permutation_band:
        return main_band(ns, corpus, transcripts, out_json, out_md, pre, cmd)
    if ns.fold_seed_offset != 0:
        return main_fold_sensitivity(ns, corpus, transcripts, out_json, out_md, pre, cmd)
    if not ns.force_prereg_rerun and has_post_hoc(out_json, out_md):
        ap.error(f"{out_json} or {out_md} already carries POST HOC blocks; the pre-registered "
                 "run would overwrite them (use --force-prereg-rerun to do so deliberately)")
    seeds = list(range(ns.seed0, ns.seed0 + ns.n_seeds))
    res = build(corpus, transcripts, Path(ns.template), ns.max_turns, seeds, ns.shares,
                ns.n_features, COMPLETE_DAYS)
    res["schema"] = "stage3-rung2-leak-null-v1"
    res["status"] = "computed"
    res["preregistration"] = pre
    res["meta"] = {
        "version": VERSION, "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": cmd, "corpus": str(corpus), "corpus_sha256": gm.sha256_file(corpus),
        "transcripts": str(transcripts), "transcripts_sha256": gm.sha256_file(transcripts),
        "template": ns.template, "script_sha256": gm.sha256_file(__file__),
        "content_module_sha256": gm.sha256_file(lc.__file__),
        "grouping_measure_sha256": gm.sha256_file(gm.__file__),
        "seeds": seeds, "representative_seed": seeds[0], "shares": ns.shares,
        "substrate": SUBSTRATE, "llm_calls": 0, "cost_usd": 0.0}
    prim = res["units"]["all_branch_days"]["cells"]
    sens = res["units"]["complete_days"]["cells"]
    ok = all(c["summary"]["passed"] for c in prim.values())
    res["verdict"] = "PASS" if ok else "KILL (null classifier off)"
    failing = [k for k, c in prim.items() if not c["summary"]["passed"]]
    sens_fail = [k for k, c in sens.items() if not c["summary"]["passed"]]
    res["verdict_line"] = (
        ("All four primary cells (2 classifiers x 2 shares) pass." if ok else
         "Failing primary cells: " + ", ".join(failing) + ".")
        + (" Sensitivity (complete days): all cells pass." if not sens_fail else
           " Sensitivity (complete days) failing cells: " + ", ".join(sens_fail) + "."))
    md = render_md(res)
    clean = gm._clean(res)
    extra = [str(corpus), str(transcripts), ns.template, cmd, str(out_json), str(out_md),
             *(str(v) for v in pre.values())]  # the pre-registered text is ours, verbatim
    assert_no_text(clean, transcripts, extra)
    assert_no_text(md, transcripts, extra)
    out_json.write_text(json.dumps(clean, indent=1, default=gm._json_default) + "\n",
                        encoding="utf-8")
    out_md.write_text(md, encoding="utf-8")
    for k, c in prim.items():
        s = c["summary"]
        print(f"{k}: rep AUROC {f3(s['representative']['auroc'])} two-sided "
              f"{f3(s['representative']['auroc_two_sided'])}; mean AUROC {f3(s['auroc_mean'])} "
              f"[{f3(s['auroc_min'])}, {f3(s['auroc_max'])}] mean two-sided "
              f"{f3(s['two_sided_mean'])} -> {'PASS' if s['passed'] else 'FAIL'}")
    print(f"verdict: {res['verdict']}; wrote {out_json} and {out_md}")
    return 0


def recommendation(res: dict[str, Any]) -> list[str]:
    """Implications for the rung 3 and 4 gate, filled from whatever POST-HOC blocks exist."""
    out = ["Future runs: draw folds and bootstrap from seed + a fixed offset (for example "
           "`--fold-seed-offset 777777`), never from the label seed itself, so the label draw "
           "and the fold permutation are independent streams."]
    b = res.get("post_hoc_permutation_band")
    if b:
        gates = [c["calibrated_gate_two_sided_p95"] for r in b["rows"] if r["n"] < 60
                 for c in r["classifiers"].values()]
        fk = [c["false_kill_rate_of_fixed_0_6_gate"] for r in b["rows"] if r["n"] < 60
              for c in r["classifiers"].values()]
        if gates:
            out.append(f"At pilot size (n = 27 to 36 account-days) the fixed 0.6 gate kills a "
                       f"clean world {min(fk):.2f} to {max(fk):.2f} of the time under per-row "
                       f"labels; a calibrated 5 percent gate there is a two-sided value of "
                       f"{min(gates):.3f} to {max(gates):.3f}, so only a strong leak is "
                       "detectable at that size.")
    cb = [res[k] for k in res if k.startswith("post_hoc_permutation_band_cluster")]
    if cb:
        c = cb[0]["rows"][0]["classifiers"]
        out.append(
            f"With labels per account (whole accounts positive across days, as a pilot "
            f"plants them) and cross-validation not grouped by account, the content "
            f"classifier's null mean AUROC is {c['content']['auroc']['mean']:.3f} "
            f"(metadata {c['metadata']['auroc']['mean']:.3f}): the content classifier is "
            "biased upward by account identity, because the same account's other days sit "
            "in the training folds. Any calibrated gate for rungs 3 and 4 must therefore be "
            "drawn either (a) with account-level labels under the same ungrouped protocol, "
            "or (b) with grouped-by-account cross-validation (all of an account's days in "
            "one fold), which removes the identity shortcut; the controller chooses.")
    return out


def _write_post_hoc(res: dict[str, Any], before: dict[str, Any], corpus: Path,
                    transcripts: Path, ns: argparse.Namespace, cmd: str, out_json: Path,
                    out_md: Path, pre: dict[str, Any]) -> None:
    """Rewrite both files with one POST-HOC block added; asserts that every pre-registered
    field, result and the verdict are unchanged."""
    res["post_hoc_recommendation"] = recommendation(res)
    after = {k: v for k, v in res.items() if not k.startswith("post_hoc_")}
    if after != before:
        raise RuntimeError("a POST-HOC write would change pre-registered content")
    md = render_md(res)
    clean = gm._clean(res)
    commands = [res["meta"]["command"]] + [v.get("command", "") for k, v in res.items()
                                           if k.startswith("post_hoc_") and isinstance(v, dict)]
    extra = [str(corpus), str(transcripts), ns.template, cmd, *commands, str(out_json),
             str(out_md), *(str(v) for v in pre.values())]
    assert_no_text(clean, transcripts, extra)
    assert_no_text(md, transcripts, extra)
    out_json.write_text(json.dumps(clean, indent=1, default=gm._json_default) + "\n",
                        encoding="utf-8")
    out_md.write_text(md, encoding="utf-8")


def _load_computed(out_json: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    res = json.loads(out_json.read_text(encoding="utf-8"))
    if res.get("status") != "computed" or "verdict" not in res:
        raise SystemExit(f"{out_json}: run the pre-registered null first")
    return res, {k: v for k, v in res.items() if not k.startswith("post_hoc_")}


def main_band(ns: argparse.Namespace, corpus: Path, transcripts: Path, out_json: Path,
              out_md: Path, pre: dict[str, Any], cmd: str) -> int:
    """POST HOC mode: read the computed output, add one band block, rewrite both files.
    Every pre-registered field, the results and the verdict are carried over unchanged."""
    res, before = _load_computed(out_json)
    seeds = list(range(ns.band_seed0, ns.band_seed0 + ns.band_seeds))
    b = build_band(corpus, transcripts, Path(ns.template), ns.max_turns, ns.shares,
                   ns.n_features, seeds, BAND_PILOT_ACCOUNTS, ns.fold_seed_offset,
                   ns.cluster_by_account)
    key = band_key(ns.cluster_by_account, ns.fold_seed_offset)
    if key == "post_hoc_permutation_band":
        cell = res["units"]["all_branch_days"]["cells"]["metadata@0.2"]
        z20 = cell["diagnostics_post_hoc"]["classifier_mean_minus_0_5_in_se"]
        row = next(r for r in b["rows"] if r["unit"].startswith("prefix")
                   and r["positive_share"] == 0.2)
        m200 = row["classifiers"]["metadata"]
        z200 = m200["auroc_mean_minus_0_5_in_se"]
        b["metadata_bias_note"] = BIAS_SENTENCE.format(
            se20=abs(z20), side20="below" if z20 < 0 else "above",
            mean20=cell["summary"]["auroc_mean"], se200=abs(z200),
            side200="below" if z200 < 0 else "above", mean200=m200["auroc"]["mean"])
    if ns.cluster_by_account:
        b["note"] = ("Caveat: with labels per account and ungrouped folds, the content "
                     "classifier is biased upward by account identity (an account's other "
                     "days are in training), so this band is the null for account-level "
                     "plants under the Stage 2b protocol, not evidence of a leak.")
    b["utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    b["command"] = cmd
    b["script_sha256"] = gm.sha256_file(__file__)
    res[key] = b
    _write_post_hoc(res, before, corpus, transcripts, ns, cmd, out_json, out_md, pre)
    for r in b["rows"]:
        for name, c in r["classifiers"].items():
            print(f"{r['unit']} share {r['positive_share']} n={r['n']} {name}: AUROC mean "
                  f"{f3(c['auroc']['mean'])} [{f3(c['auroc_min'])}, {f3(c['auroc_max'])}] "
                  f">0.6 {c['share_auroc_above_0_6']:.2f}; two-sided "
                  f"[{f3(c['two_sided']['p2_5'])}, {f3(c['two_sided']['p97_5'])}] gate p95 "
                  f"{f3(c['calibrated_gate_two_sided_p95'])} false-kill@0.6 "
                  f"{c['false_kill_rate_of_fixed_0_6_gate']:.2f}")
    print(f"POST-HOC {key} added to {out_json} and {out_md}; verdict unchanged: "
          f"{res['verdict']}")
    return 0


def main_fold_sensitivity(ns: argparse.Namespace, corpus: Path, transcripts: Path,
                          out_json: Path, out_md: Path, pre: dict[str, Any], cmd: str) -> int:
    """POST HOC mode: the pre-registered computation with fold seed = label seed + offset,
    stored beside (never over) the pre-registered results, with the same rule applied."""
    res, before = _load_computed(out_json)
    seeds = list(range(ns.seed0, ns.seed0 + ns.n_seeds))
    fs = build(corpus, transcripts, Path(ns.template), ns.max_turns, seeds, ns.shares,
               ns.n_features, COMPLETE_DAYS, ns.fold_seed_offset)
    prim = fs["units"]["all_branch_days"]["cells"]
    ok = all(c["summary"]["passed"] for c in prim.values())
    verdict = "PASS" if ok else "KILL (null classifier off)"
    flip = (FOLD_FLIP_PASS.format(offset=ns.fold_seed_offset) if ok else
            FOLD_FLIP_KILL.format(offset=ns.fold_seed_offset,
                                  cells="; ".join(_cell_fail_desc(prim))))
    res_fail = _cell_fail_desc(fs["units"]["complete_days"]["cells"])
    residue = (FOLD_RESIDUE.format(cells="; ".join(res_fail),
                                   verb="fails" if len(res_fail) == 1 else "fail")
               if res_fail else FOLD_NO_RESIDUE)
    res["post_hoc_fold_seed_sensitivity"] = {
        "post_hoc": True,
        "label": "POST-HOC (added after the pre-registered verdict; does not change it)",
        "fold_seed_offset": int(ns.fold_seed_offset), "seeds": seeds,
        "units": {u: {"cells": v["cells"]} for u, v in fs["units"].items()},
        "verdict_under_preregistered_rule": verdict,
        "flip_sentence": flip, "residue_sentence": residue,
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "command": cmd,
        "script_sha256": gm.sha256_file(__file__)}
    _write_post_hoc(res, before, corpus, transcripts, ns,
                    cmd, out_json, out_md, pre)
    for k, c in prim.items():
        s = c["summary"]
        print(f"[offset {ns.fold_seed_offset}] {k}: rep AUROC "
              f"{f3(s['representative']['auroc'])} two-sided "
              f"{f3(s['representative']['auroc_two_sided'])}; mean AUROC "
              f"{f3(s['auroc_mean'])} mean two-sided {f3(s['two_sided_mean'])} -> "
              f"{'PASS' if s['passed'] else 'FAIL'}")
    print(f"POST-HOC fold-seed sensitivity: {verdict}; pre-registered verdict unchanged: "
          f"{res['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
