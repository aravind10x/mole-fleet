#!/usr/bin/env python3
"""Stage 3 task S6 (brief 07): the metadata-leak audit on MOLE's eight released corpora.

What: for each released corpus (`<data-dir>/data/audit/<corpus>/0000.parquet` plus its
labels parquet) build the per-account-day metadata table the way the frozen Stage 2b
`grouping_measure.metadata_features` builds it for a fork branch, label account-days attack
versus honest from the labels parquet, and run the frozen `grouping_measure.leak_classifier`
unchanged (standardised features, L2 logistic regression, stratified 5-fold cross-validated
AUROC, bootstrap 95 percent interval, two-sided reading max(AUROC, 1 - AUROC), gate 0.6).

Why: lesson L13 found Stage 2b's scenario sessions separable from honest ones by metadata
(AUROC 0.698 [0.62, 0.78]). Whether MOLE's own released corpora carry the same leak is a
fact the paper and the note to MOLE's authors need; it touches nothing in Stage 3.

Feature assembly (mirrors `metadata_features`, its no-transcripts branch): the released
corpora carry no transcripts and no per-session turn field, so session_length and
turn_cap_rate cannot be computed; the two remaining features are
  * events_per_session = (all audit events of the account-day, any exit code) /
    (distinct task_id over those events; a missing task_id counts as one value, as the
    fork's `set.add(None)` does; at least 1),
  * first_action_min = simulated minutes since midnight of the earliest exit_code == 0
    event of the account-day (`mole_corpus.sim_minutes`).
Account-days are (account, ts[:10]) with at least one exit_code == 0 event
(`mole_corpus.account_days`, TRACK-B section 0), as the fork's `ci.active` is.

Label assembly (primary rule, see `LABEL_RULES`): an account-day is "attack" iff the labels
parquet has a row (account, date) with outcome in {executed, attempted} (any of the twelve
scenarios); "honest" iff the account has no label row on any day; every other account-day
is excluded. Sources: `f1_upstream_row.py` lines 528-533 (positives = labelled executed
account-days; negatives = account-days of never-labelled accounts) and
`seed_expansion.attack_rows` (outcome executed or attempted). f1 restricted positives to
the two coalition scenarios because F1 asked a coalition question; the leak is a property
of the scenario-session generator, so the primary rule keeps every scenario. The f1 rule
exactly, "any label row", and the Stage 2b convention (negatives = every other active
account-day) are reported as sensitivities.

Untrusted data: paths are arguments, parquet is read as data only, run with `python -I`.
No network, no API calls, $0.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_metadata_leak_released.py \\
        --data-dir /abs/work/upstream-data \\
        --out-json /abs/work/stage3/s6-released-metadata-leak.json \\
        --out-md /abs/work/stage3/s6-released-metadata-leak.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

import grouping_measure as gm  # noqa: E402  (frozen; imported, never modified)
import mole_corpus as mc  # noqa: E402

VERSION = "s6-released-metadata-leak-v1"
GATE = 0.6
GATE_TEXT = ("pass at max(AUROC, 1 − AUROC) ≤ 0.6 (lesson L13; the frozen "
             "`leak_classifier` threshold, applied to the cross-validated point estimate)")
FEATURES_FULL: tuple[str, ...] = ("session_length", "turn_cap_rate", "events_per_session",
                                  "first_action_min")
FEATURES_AUDIT_ONLY: tuple[str, ...] = ("events_per_session", "first_action_min")
#: Audit columns that would carry per-session turn counts; none exists in the released schema.
TURN_FIELDS: tuple[str, ...] = ("turn_count", "turns", "n_turns", "num_turns")
AUDIT_READ_COLUMNS: tuple[str, ...] = ("ts", "account", "exit_code", "task_id")
GENERATORS: dict[str, str] = {"gpt53": "GPT-5.3", "kimi_k26": "Kimi-K2.6",
                              "deepseek_v4_flash": "DeepSeek-V4-Flash",
                              "qwen36_27b": "Qwen3.6-27B"}
F1_THREATS: tuple[str, ...] = ("c1_release_bypass", "c2_split_exfil")   # f1_upstream_row.THREATS
PRIMARY_RULE = "primary"
#: name -> (outcomes counted as attack or None for any, scenarios or None for any,
#:          honest pool: "never_labelled" | "all_other")
LABEL_RULES: dict[str, dict[str, Any]] = {
    "primary": {"outcomes": ("executed", "attempted"), "scenarios": None,
                "honest": "never_labelled",
                "text": "attack = label row with outcome executed or attempted (any scenario); "
                        "honest = account-days of accounts with no label row on any day"},
    "f1_exact": {"outcomes": ("executed",), "scenarios": F1_THREATS, "honest": "never_labelled",
                 "text": "f1_upstream_row exactly: attack = executed c1_release_bypass or "
                         "c2_split_exfil; honest = never-labelled accounts"},
    "any_label": {"outcomes": None, "scenarios": None, "honest": "never_labelled",
                  "text": "attack = any label row (also no_attempt, refused: every scenario "
                          "session day); honest = never-labelled accounts"},
    "stage2b_negatives": {"outcomes": ("executed", "attempted"), "scenarios": None,
                          "honest": "all_other",
                          "text": "primary positives; honest = every other active account-day "
                                  "(the Stage 2b grouping_measure convention)"},
}
SHUFFLE_CORPUS = "gpt53_single_day"
SHUFFLE_SEED = 20261020
SHUFFLE_REPEATS = 20
#: Rows with fewer attack account-days than this are flagged as small-n in the notes: the
#: two-sided reading max(AUROC, 1 - AUROC) is biased upward there and the gate has little power.
SMALL_N = 50
#: Post-hoc (not pre-registered; added after the first run was read at reviewer request):
#: fold-assignment seeds for the primary rule, and each feature alone at the frozen seed.
POSTHOC_FOLD_SEEDS: tuple[int, ...] = tuple(range(1, 11))
SHUFFLE_CONDITION = ("the shuffled-label AUROC's 95 percent interval contains 0.5 and its "
                     "two-sided value is at most 0.6")


# ----------------------------------------------------------------------------------
# Assembly
# ----------------------------------------------------------------------------------

def generator_of(corpus: str) -> str:
    for k, v in GENERATORS.items():
        if corpus.startswith(k + "_"):
            return v
    return "unknown"


def feature_set(columns: Sequence[str]) -> list[str]:
    """Features computable from an audit schema. A turn field would enable the two transcript
    features; the released corpora have none. Refuse rather than silently ignore one."""
    present = [c for c in TURN_FIELDS if c in columns]
    if present:
        raise SystemExit(f"audit carries a turn field {present}: extend the assembly to "
                         "compute session_length and turn_cap_rate before running")
    return list(FEATURES_AUDIT_ONLY)


def account_day_features(df: pd.DataFrame) -> pd.DataFrame:
    """Per active account-day: events_per_session and first_action_min, mirroring the
    no-transcripts branch of `grouping_measure.metadata_features` (see module docstring).
    `df` holds every audit event (any exit code) with columns ts, account, exit_code, task_id.
    """
    d = pd.DataFrame({"account": df["account"].astype(str).to_numpy(),
                      "date": mc.day_of(df["ts"]).to_numpy(),
                      "ok": (df["exit_code"].to_numpy() == 0),
                      "tmin": mc.sim_minutes(df["ts"]),
                      "task_id": df["task_id"].to_numpy()})
    g = d.groupby(["account", "date"], sort=True)
    n_ev = g.size().rename("n_events")
    n_tasks = g["task_id"].nunique(dropna=False).rename("n_sessions")
    ok = d[d["ok"]]
    first = ok.groupby(["account", "date"], sort=True)["tmin"].min().rename("first_action_min")
    out = pd.concat([n_ev, n_tasks], axis=1).join(first, how="inner")   # active only
    out["n_sessions"] = out["n_sessions"].clip(lower=1)
    out["events_per_session"] = out["n_events"] / out["n_sessions"]
    return out.reset_index()[["account", "date", "n_events", "n_sessions",
                              "events_per_session", "first_action_min"]]


def label_account_days(feats: pd.DataFrame, labels: pd.DataFrame, rule: dict[str, Any]
                       ) -> tuple[np.ndarray, dict[str, Any]]:
    """Class per row of `feats`: 1 attack, 0 honest, -1 excluded, under `rule`."""
    lab = labels.copy()
    lab["date"] = lab["date"].astype(str).str[:10]
    sel = np.ones(len(lab), dtype=bool)
    if rule["outcomes"] is not None:
        sel &= lab["outcome"].isin(rule["outcomes"]).to_numpy()
    if rule["scenarios"] is not None:
        sel &= lab["scenario"].isin(rule["scenarios"]).to_numpy()
    pos = set(zip(lab.loc[sel, "account"], lab.loc[sel, "date"]))
    labelled_accounts = set(lab["account"])
    keys = list(zip(feats["account"], feats["date"]))
    cls = np.full(len(feats), -1, dtype=int)
    is_pos = np.array([k in pos for k in keys], dtype=bool)
    if rule["honest"] == "never_labelled":
        is_neg = ~feats["account"].isin(labelled_accounts).to_numpy()
    elif rule["honest"] == "all_other":
        is_neg = ~is_pos
    else:
        raise ValueError(f"unknown honest pool {rule['honest']!r}")
    cls[is_neg] = 0
    cls[is_pos] = 1
    active = set(keys)
    info = {"label_rows_selected": int(sel.sum()),
            "positive_keys": len(pos),
            "positive_keys_not_active": len(pos - active),
            "labelled_accounts": len(labelled_accounts),
            "n_attack": int((cls == 1).sum()), "n_honest": int((cls == 0).sum()),
            "n_excluded": int((cls == -1).sum())}
    return cls, info


def classify(feats: pd.DataFrame, cls: np.ndarray, names: Sequence[str],
             seed: int = gm.SEED) -> dict[str, Any]:
    """Run the frozen classifier on the attack and honest rows."""
    m = cls >= 0
    X = feats.loc[m, list(names)].to_numpy(dtype=float)
    y = cls[m]
    r = gm.leak_classifier(X, y, seed=seed)
    r["features"] = list(names)
    r["exceeds_gate"] = (None if r.get("passed") is None else not r["passed"])
    return r


def describe(feats: pd.DataFrame, cls: np.ndarray, names: Sequence[str]) -> dict[str, Any]:
    """Medians per class, for reading which feature carries the signal."""
    out: dict[str, Any] = {}
    for f in names:
        out[f] = {"attack_median": float(np.nanmedian(feats.loc[cls == 1, f]))
                  if (cls == 1).any() else None,
                  "honest_median": float(np.nanmedian(feats.loc[cls == 0, f]))
                  if (cls == 0).any() else None}
    return out


def posthoc_checks(feats: pd.DataFrame, labels: pd.DataFrame, names: Sequence[str]
                   ) -> dict[str, Any]:
    """Post-hoc, primary rule only: the two-sided value under other fold-assignment seeds
    (point estimate, no bootstrap) and for each feature alone at the frozen seed."""
    cls, _ = label_account_days(feats, labels, LABEL_RULES[PRIMARY_RULE])
    m = cls >= 0
    y = cls[m]
    X = feats.loc[m, list(names)].to_numpy(dtype=float)
    by_seed = {sd: gm.leak_classifier(X, y, seed=sd, n_boot=0)["auroc_two_sided"]
               for sd in POSTHOC_FOLD_SEEDS}
    single = {}
    for f in names:
        r = gm.leak_classifier(feats.loc[m, [f]].to_numpy(dtype=float), y)
        single[f] = {"auroc": r["auroc"], "auroc_two_sided": r["auroc_two_sided"],
                     "ci": r.get("ci"), "exceeds_gate": None if r.get("passed") is None
                     else not r["passed"]}
    vals = list(by_seed.values())
    return {"fold_seeds": list(POSTHOC_FOLD_SEEDS), "two_sided_by_fold_seed": by_seed,
            "two_sided_min": float(min(vals)), "two_sided_max": float(max(vals)),
            "fold_seeds_exceeding_gate": int(sum(v > GATE for v in vals)),
            "single_feature": single}


def load_corpus(data_dir: str | Path, corpus: str) -> tuple[pd.DataFrame, pd.DataFrame,
                                                             list[str]]:
    schema = pq.read_schema(mc.audit_path(data_dir, corpus)).names
    cols = [c for c in AUDIT_READ_COLUMNS if c in schema]
    if "task_id" not in cols:
        raise SystemExit(f"{corpus}: audit has no task_id column; sessions undefined")
    df = mc.load_audit(data_dir, corpus, columns=cols, successful_only=False)
    labels = mc.load_labels(data_dir, corpus)
    return df, labels, list(schema)


def run_corpus(data_dir: str | Path, corpus: str, seed: int = gm.SEED) -> dict[str, Any]:
    t0 = time.time()
    df, labels, schema = load_corpus(data_dir, corpus)
    names = feature_set(schema)
    feats = account_day_features(df)
    t_load = time.time() - t0
    res: dict[str, Any] = {
        "corpus": corpus, "generator": generator_of(corpus),
        "audit_sha256": gm.sha256_file(mc.audit_path(data_dir, corpus)),
        "labels_sha256": gm.sha256_file(mc.labels_path(data_dir, corpus)),
        "audit_rows": int(len(df)), "label_rows": int(len(labels)),
        "days": int(feats["date"].nunique()), "accounts": int(feats["account"].nunique()),
        "active_account_days": int(len(feats)),
        "features": names, "features_missing": [f for f in FEATURES_FULL if f not in names],
        "features_note": "no transcripts and no turn field in the released audit schema: "
                         "session_length and turn_cap_rate not computable; sessions = "
                         "distinct task_id per account-day",
        "task_id_null_share": float(df["task_id"].isna().mean()),
        "rules": {},
    }
    for rname, rule in LABEL_RULES.items():
        cls, info = label_account_days(feats, labels, rule)
        r = classify(feats, cls, names, seed)
        r["labels"] = info
        r["medians"] = describe(feats, cls, names)
        res["rules"][rname] = r
    res["posthoc"] = posthoc_checks(feats, labels, names)
    res["runtime_s"] = round(time.time() - t0, 2)
    res["load_and_features_s"] = round(t_load, 2)
    mc.eprint(f"[{corpus}] {res['runtime_s']}s; primary AUROC "
              f"{res['rules'][PRIMARY_RULE]['auroc']:.3f}")
    return res


def shuffle_sanity(data_dir: str | Path, corpus: str, seed: int = SHUFFLE_SEED,
                   repeats: int = SHUFFLE_REPEATS) -> dict[str, Any]:
    """Primary-rule rows of `corpus` with the attack/honest labels permuted (seeded)."""
    t0 = time.time()
    df, labels, schema = load_corpus(data_dir, corpus)
    names = feature_set(schema)
    feats = account_day_features(df)
    cls, info = label_account_days(feats, labels, LABEL_RULES[PRIMARY_RULE])
    m = cls >= 0
    X = feats.loc[m, list(names)].to_numpy(dtype=float)
    y = cls[m]
    rng = np.random.default_rng(seed)
    first = gm.leak_classifier(X, rng.permutation(y))
    others = [gm.leak_classifier(X, rng.permutation(y), n_boot=0)["auroc"]
              for _ in range(repeats - 1)]
    lo, hi = first["ci"]
    ok = bool(lo <= 0.5 <= hi and first["auroc_two_sided"] <= GATE)
    allv = [first["auroc"]] + others
    return {"corpus": corpus, "rule": PRIMARY_RULE, "shuffle_seed": seed, "features": names,
            "n_attack": info["n_attack"], "n_honest": info["n_honest"], "result": first,
            "condition": SHUFFLE_CONDITION, "passed": ok,
            "repeats": repeats, "repeat_aurocs": allv,
            "repeat_mean": float(np.mean(allv)), "repeat_min": float(np.min(allv)),
            "repeat_max": float(np.max(allv)), "runtime_s": round(time.time() - t0, 2)}


# ----------------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------------

def f3(x: Any) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:.3f}"


def yes_no(ex: bool | None) -> str:
    return "n/a" if ex is None else ("yes" if ex else "no")


def hhmm(minutes: float | None) -> str:
    if minutes is None or (isinstance(minutes, float) and math.isnan(minutes)):
        return "n/a"
    m = int(math.floor(minutes))
    return f"{m // 60:02d}:{m % 60:02d}"


def two_sided_interval(ci: Sequence[float]) -> tuple[float, float]:
    """The AUROC interval mapped onto max(AUROC, 1 - AUROC): mirrored below 0.5, and
    [0.5, max(1 - lo, hi)] when it contains 0.5."""
    lo, hi = float(ci[0]), float(ci[1])
    if lo >= 0.5:
        return lo, hi
    if hi <= 0.5:
        return 1 - hi, 1 - lo
    return 0.5, max(1 - lo, hi)


def notes_block(res: dict[str, Any]) -> list[str]:
    """Reading notes on the primary table, derived from the results (not hand-written)."""
    out: list[str] = []
    for c in res["corpora"]:
        r = c["rules"][PRIMARY_RULE]
        ci = r.get("ci") or [float("nan")] * 2
        if any(math.isnan(float(x)) for x in ci):
            continue
        n1 = r["labels"]["n_attack"]
        lo2, hi2 = two_sided_interval(ci)
        others = "; ".join(
            f"`{k}` {f3(c['rules'][k].get('auroc_two_sided'))} (exceeds "
            f"{yes_no(c['rules'][k].get('exceeds_gate'))})"
            for k in LABEL_RULES if k != PRIMARY_RULE)
        flips = [k for k in LABEL_RULES if k != PRIMARY_RULE
                 and c["rules"][k].get("exceeds_gate") != r.get("exceeds_gate")]
        if n1 >= SMALL_N and lo2 <= GATE <= hi2:
            out.append(f"- **{c['corpus']} straddles the gate:** {f3(r['auroc'])} "
                       f"[{f3(ci[0])}, {f3(ci[1])}], exceeds {yes_no(r.get('exceeds_gate'))} "
                       f"under the primary rule; other label rules: {others}."
                       + (f" The verdict flips under {', '.join(f'`{k}`' for k in flips)}."
                          if flips else ""))
        if n1 >= SMALL_N and r.get("exceeds_gate") is False and (ci[0] > 0.5 or ci[1] < 0.5):
            out.append(f"- **{c['corpus']} is below the gate but its interval excludes 0.5** "
                       f"({f3(r['auroc'])} [{f3(ci[0])}, {f3(ci[1])}]): a detectable leak that "
                       "the 0.6 gate tolerates.")
    small = [c for c in res["corpora"] if c["rules"][PRIMARY_RULE]["labels"]["n_attack"] < SMALL_N]
    if small:
        ns = [c["rules"][PRIMARY_RULE]["labels"]["n_attack"] for c in small]
        out.append(f"- **Small-n rows** ({', '.join(c['corpus'] for c in small)}) rest on "
                   f"{min(ns)} to {max(ns)} attack account-days: max(AUROC, 1 \u2212 AUROC) is "
                   "biased upward at this size (it is at least 0.5 even under no signal) and the "
                   "gate has little power; a \"no\" there does not rule a leak out.")
    return out


def preregistration_md(args: argparse.Namespace, started: str) -> str:
    L = ["# S6: metadata-leak audit on MOLE's eight released corpora", "",
         f"Script `work/checks/stage3_metadata_leak_released.py` ({VERSION}); frozen classifier "
         "`work/checks/grouping_measure.py` `leak_classifier` (imported unchanged, seed "
         f"{gm.SEED}, 5 folds, 1000 bootstrap draws). Data: `forgelab/mole` released parquet "
         "files under `work/upstream-data/` (untrusted, read as data). Substrate: none of "
         "Stage 3's; these are MOLE's own released worlds. $0.", "",
         "## Pre-registration (written by the script before any statistic is computed)", "",
         f"Written {started}.", "",
         f"- **Gate (L13, verbatim):** \"pass at max(AUROC, 1 − AUROC) ≤ 0.6\". "
         f"Applied as: {GATE_TEXT}. A row \"exceeds the gate\" iff the two-sided value is "
         "above 0.6.",
         f"- **Primary label rule:** {LABEL_RULES[PRIMARY_RULE]['text']}. Label columns used: "
         "`account`, `date` (first ten characters), `outcome`, `scenario`; `confidence` and "
         "`judge` unused. Mapping reused from `work/checks/f1_upstream_row.py` lines 528-533 "
         "(never-labelled honest pool; labelled executed positives) and "
         "`work/checks/seed_expansion.py` `attack_rows` (executed or attempted).",
         "- **Sensitivity label rules (reported, not gated):** " + "; ".join(
             f"`{k}`: {v['text']}" for k, v in LABEL_RULES.items() if k != PRIMARY_RULE) + ".",
         "- **Features:** the four of `metadata_features` where computable; the released "
         "corpora have no transcripts and no turn field, so each row names its feature set "
         "(expected: events_per_session, first_action_min, the frozen code's two-feature "
         "fallback).",
         f"- **Sanity row:** primary rule on `{args.shuffle_corpus}`, labels permuted with seed "
         f"{args.shuffle_seed}; passes iff {SHUFFLE_CONDITION}. {SHUFFLE_REPEATS} permutations "
         "are also summarised (point AUROC only).", ""]
    return "\n".join(L)


def render_md(res: dict[str, Any], prereg: str) -> str:
    L = [prereg, "## Result (primary label rule)", "",
         "| corpus | generator | n attack account-days | n honest account-days | features used "
         "| AUROC [95% interval] | two-sided max(AUROC, 1 − AUROC) | exceeds gate 0.6 "
         "| run time (s) |",
         "|---|---|---:|---:|---|---|---:|---|---:|"]
    for c in res["corpora"]:
        r = c["rules"][PRIMARY_RULE]
        ci = r.get("ci", [float("nan")] * 2)
        ex = r.get("exceeds_gate")
        L.append(f"| {c['corpus']} | {c['generator']} | {r['labels']['n_attack']} | "
                 f"{r['labels']['n_honest']} | {', '.join(r['features'])} | {f3(r['auroc'])} "
                 f"[{f3(ci[0])}, {f3(ci[1])}] | {f3(r.get('auroc_two_sided'))} | "
                 f"{'n/a' if ex is None else ('yes' if ex else 'no')} | {c['runtime_s']} |")
    s = res["shuffle_sanity"]
    sr = s["result"]
    L.append(f"| sanity: {s['corpus']}, labels shuffled (seed {s['shuffle_seed']}) | "
             f"{generator_of(s['corpus'])} | {s['n_attack']} | {s['n_honest']} | "
             f"{', '.join(s['features'])} | {f3(sr['auroc'])} [{f3(sr['ci'][0])}, "
             f"{f3(sr['ci'][1])}] | {f3(sr['auroc_two_sided'])} | "
             f"{yes_no(None if sr.get('passed') is None else not sr['passed'])} | "
             f"{s['runtime_s']} |")
    L += ["", "### Notes on the primary table", ""] + notes_block(res)
    L += ["", f"Sanity condition ({SHUFFLE_CONDITION}): **{'met' if s['passed'] else 'NOT met'}**."
          f" Over {s['repeats']} seeded permutations the point AUROC ranges "
          f"{f3(s['repeat_min'])} to {f3(s['repeat_max'])} (mean {f3(s['repeat_mean'])}).", "",
          "Tag: **tested** (`work/checks/stage3_metadata_leak_released.py`, this run). Run times "
          "include reading the parquet, assembling features and all four label rules.", "",
          "## Sensitivity label rules (two-sided value; AUROC [interval]; n attack / n honest; "
          "exceeds gate 0.6)",
          "", "| corpus | " + " | ".join(f"`{k}` | `{k}` exceeds" for k in LABEL_RULES) + " |",
          "|---|" + "---|---|" * len(LABEL_RULES)]
    for c in res["corpora"]:
        cells = []
        for k in LABEL_RULES:
            r = c["rules"][k]
            ci = r.get("ci", [float("nan")] * 2)
            cells.append(f"{f3(r.get('auroc_two_sided'))}; {f3(r['auroc'])} [{f3(ci[0])}, "
                         f"{f3(ci[1])}]; {r['labels']['n_attack']} / {r['labels']['n_honest']} | "
                         f"{yes_no(r.get('exceeds_gate'))}")
        L.append(f"| {c['corpus']} | " + " | ".join(cells) + " |")
    L += ["", "## Feature medians, primary rule (attack / honest)", "",
          "| corpus | events_per_session | first_action_min (sim. minutes after midnight) "
          "| first action (hh:mm) |", "|---|---|---|---|"]
    for c in res["corpora"]:
        md = c["rules"][PRIMARY_RULE]["medians"]
        fa = md["first_action_min"]
        L.append(f"| {c['corpus']} | " + " | ".join(
            f"{f3(md[f]['attack_median'])} / {f3(md[f]['honest_median'])}"
            for f in FEATURES_AUDIT_ONLY)
            + f" | {hhmm(fa['attack_median'])} / {hhmm(fa['honest_median'])} |")
    L += ["", "## Post-hoc checks (not pre-registered; added after the first run was read)", "",
          f"Primary rule. Fold-assignment seeds {POSTHOC_FOLD_SEEDS[0]} to "
          f"{POSTHOC_FOLD_SEEDS[-1]} (point estimate, no bootstrap), and each feature alone at "
          f"the frozen seed {gm.SEED} (with its bootstrap interval). Tag: **tested**, this "
          "script, this run.", "",
          "| corpus | two-sided over fold seeds (min to max) | fold seeds exceeding 0.6 | "
          + " | ".join(f"{f} alone: two-sided [AUROC interval]" for f in FEATURES_AUDIT_ONLY)
          + " |", "|---|---|---:|" + "---|" * len(FEATURES_AUDIT_ONLY)]
    for c in res["corpora"]:
        ph = c["posthoc"]
        cells = []
        for f in FEATURES_AUDIT_ONLY:
            sf = ph["single_feature"][f]
            ci = sf.get("ci") or [float("nan")] * 2
            cells.append(f"{f3(sf['auroc_two_sided'])} [{f3(ci[0])}, {f3(ci[1])}]")
        L.append(f"| {c['corpus']} | {f3(ph['two_sided_min'])} to {f3(ph['two_sided_max'])} | "
                 f"{ph['fold_seeds_exceeding_gate']} of {len(ph['fold_seeds'])} | "
                 + " | ".join(cells) + " |")
    L += ["", "## Corpus facts", "",
          "| corpus | audit rows | label rows | days | accounts | active account-days | "
          "labelled accounts | excluded account-days (primary) | positive keys not active | "
          "task_id null share | audit sha256 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
          "---:|---|"]
    for c in res["corpora"]:
        lb = c["rules"][PRIMARY_RULE]["labels"]
        L.append(f"| {c['corpus']} | {c['audit_rows']:,} | {c['label_rows']} | {c['days']} | "
                 f"{c['accounts']} | {c['active_account_days']:,} | {lb['labelled_accounts']} | "
                 f"{lb['n_excluded']} | {lb['positive_keys_not_active']} | "
                 f"{c['task_id_null_share']:.4f} | `{(c['audit_sha256'] or '')[:12]}…` |")
    L += ["", "## Notes", "",
          "- Features missing on every released corpus: session_length, turn_cap_rate (no "
          "transcripts, no turn field in the audit schema). The fork's Stage 2b audit used all "
          "four (AUROC 0.698 [0.62, 0.78] pooled, `work/stage2/b-grouping.md`, **observed**); "
          "the rows here are therefore the two-feature version and are not directly comparable "
          "to that number.",
          "- events_per_session counts every audit event of the account-day, failed ones "
          "included, over distinct task_id, as `metadata_features` does; first_action_min uses "
          "successful events only.",
          "- Honest account-days are clean only if MOLE's label set is complete (never-labelled "
          "accounts may still carry unlabelled scenario sessions; noted in Stage 0 and in "
          "`f1_upstream_row.py`).",
          "- The audit column `is_malicious` is not used (it is a label, not metadata).", ""]
    return "\n".join(L)


def _clean(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return None if math.isnan(v) else v
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--data-dir", required=True, help="root holding data/audit and data/labels")
    p.add_argument("--corpora", nargs="*", default=list(mc.CORPORA))
    p.add_argument("--out-json", required=True)
    p.add_argument("--out-md", required=True)
    p.add_argument("--shuffle-corpus", default=SHUFFLE_CORPUS)
    p.add_argument("--shuffle-seed", type=int, default=SHUFFLE_SEED)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    prereg = preregistration_md(args, started)
    out_md, out_json = Path(args.out_md), Path(args.out_json)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    # Pre-registration first (COMMON rule 8): the gate is on disk before any statistic.
    out_md.write_text(prereg + "\n_Status: pre-registered; results pending._\n",
                      encoding="utf-8")
    out_json.write_text(json.dumps({"version": VERSION, "status": "preregistered",
                                    "started": started, "gate": GATE, "gate_text": GATE_TEXT,
                                    "label_rules": LABEL_RULES, "primary_rule": PRIMARY_RULE,
                                    "shuffle_condition": SHUFFLE_CONDITION}, indent=2),
                        encoding="utf-8")
    t0 = time.time()
    corpora = [run_corpus(args.data_dir, c) for c in args.corpora]
    sanity = shuffle_sanity(args.data_dir, args.shuffle_corpus, args.shuffle_seed)
    res = {"version": VERSION, "status": "done", "started": started,
           "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "total_runtime_s": round(time.time() - t0, 1), "gate": GATE, "gate_text": GATE_TEXT,
           "classifier": {"function": "grouping_measure.leak_classifier", "seed": gm.SEED,
                          "folds": 5, "n_boot": 1000,
                          "grouping_measure_sha256": gm.sha256_file(HERE /
                                                                    "grouping_measure.py")},
           "primary_rule": PRIMARY_RULE, "label_rules": LABEL_RULES,
           "corpora": corpora, "shuffle_sanity": sanity}
    out_json.write_text(json.dumps(_clean(res), indent=2), encoding="utf-8")
    out_md.write_text(render_md(res, prereg), encoding="utf-8")
    mc.eprint(f"done in {res['total_runtime_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
