#!/usr/bin/env python3
"""Permutation leak gate for rungs 2, 3 and 4 (Stage 3 design v4 section 11.4; brief 07b
F2.4). Replaces the fixed two-sided band [0.4, 0.6] of `stage3_leak_null.py`, which rung 2
showed kills a clean honest prefix 13 percent of the time at n = 118 and 39 to 61 percent of
the time at pilot size.

The gate, per leak classifier (metadata features from `grouping_measure.metadata_features`;
content features from `stage3_leak_content.content_matrix`), both with the frozen feature
definitions:

* Labels are ACCOUNT-LEVEL: a planted account is positive on every one of its account-days
  (a pilot plants whole accounts), so the null permutes which accounts are positive, with
  the observed number of positive accounts, never which rows.
* Cross-validation is GROUPED BY ACCOUNT (all of an account's rows in one fold; positive
  accounts spread over folds), which removes the identity shortcut rung 2 found under
  ungrouped folds (content classifier null mean AUROC 0.634 with account-clustered labels).
  Fold-wise standardisation and the L2 logistic regression are `grouping_measure`'s own
  (`_logreg_fit`, `auroc`), unchanged.
* The FOLD seed is decoupled from the LABEL seed by a fixed offset (`FOLD_SEED_OFFSET`),
  so the label draw and the fold permutation are independent streams (rung 2 post hoc).
* The gate is the 95th percentile of the two-sided value max(AUROC, 1 - AUROC) over
  `N_PERMS` permutations of account-level labels on the run's OWN features. A run whose
  observed two-sided value lies at or below the gate is "inside the band" (no leak at the
  5 percent level); above it, "above the band" (the rung-3/4 world kill).

Two label units: `account-day` (the default; the prefix and a pilot) and `session` (a run
where every account is a coalition account with one scenario session, such as S5.3, where
the only honest contrast is the account's own other session; there the null permutes the
label WITHIN each account, keeping one positive session per account).

Honest-null check (rung 2 restated): on the prefix, positives are a random draw of accounts
(`--random-accounts K --label-seed S`); pass iff the observed value is inside the band.

Outputs carry numbers, feature names and account ids only. Run with `python -I`; paths are
arguments.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_leak_gate.py \\
        --corpus /abs/prefix_v1.jsonl --random-accounts 10 --label-seed 20261020 \\
        --out-json /abs/out.json --out-md /abs/out.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

VERSION = "stage3-leak-gate-v1"
N_PERMS = 200
PERM_SEED0 = 20261100
FOLD_SEED_OFFSET = 777777
FOLDS = 5
MAX_TURNS = 50
GATE_QUANTILE = 95.0
UNITS = ("account-day", "session")


def prereg_block() -> str:
    """The pass condition, written before any statistic (copied verbatim into every output)."""
    return (
        "## Pass condition (written before the statistic it governs)\n\n"
        "Design v4 section 11.4, verbatim: \"Rungs 2, 3 and 4 gate each leak classifier at the "
        "95th percentile of its permutation null drawn with account-level labels on the run's own "
        "features, with grouped-by-account cross-validation and the fold seed decoupled from the "
        "label seed. The rung-2 honest-null check becomes 'the observed value lies inside the "
        "permutation band', which the prefix passes.\"\n\n"
        f"Operationalisation: per classifier, {N_PERMS} permutations of ACCOUNT-level labels "
        "(the observed number of positive accounts; every account-day of a positive account "
        "positive) on the run's own features; grouped-by-account {FOLDS}-fold cross-validated "
        "logistic regression (grouping_measure's _logreg_fit and auroc, fold-wise "
        "standardisation); fold seed = label seed + FOLD_SEED_OFFSET (777777); the gate is the "
        "95th percentile of the two-sided value max(AUROC, 1 - AUROC) over the permutations. "
        "Verdict per classifier: INSIDE the band iff the observed two-sided value <= gate; "
        "ABOVE otherwise (a rung-3/4 world kill). Session unit: labels permuted within each "
        "account, one positive session per account."
    ).replace("{FOLDS}", str(FOLDS))


# ── classifier with grouped folds ────────────────────────────────────────────────────────

def grouped_folds(groups: Sequence[str], y: np.ndarray, seed: int, folds: int = FOLDS
                  ) -> np.ndarray:
    """Fold id per row; every row of one account in one fold; positive accounts dealt round
    the folds first (a random order), then the negative accounts, so each fold holds a
    share of the positives whenever there are at least `folds` of them."""
    y = np.asarray(y, dtype=int)
    rng = np.random.default_rng(seed)
    accs = sorted(set(groups))
    pos_acc = sorted({g for g, v in zip(groups, y) if v})
    neg_acc = [a for a in accs if a not in set(pos_acc)]
    order = [pos_acc[i] for i in rng.permutation(len(pos_acc))] + \
            [neg_acc[i] for i in rng.permutation(len(neg_acc))]
    fold_of = {a: i % folds for i, a in enumerate(order)}
    return np.array([fold_of[g] for g in groups], dtype=int)


def classify_grouped(X: np.ndarray, y: np.ndarray, groups: Sequence[str], seed: int,
                     folds: int = FOLDS) -> dict[str, Any]:
    """Grouped-by-account cross-validated AUROC with grouping_measure's fit and AUROC."""
    import grouping_measure as gm
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    n1 = int(y.sum())
    out: dict[str, Any] = {"n": int(len(y)), "positives": n1, "negatives": int(len(y) - n1),
                           "positive_accounts": len({g for g, v in zip(groups, y) if v}),
                           "accounts": len(set(groups)), "folds": folds, "grouped": True}
    if n1 < 1 or n1 == len(y):
        out.update(auroc=float("nan"), auroc_two_sided=float("nan"), folds_used=0,
                   status="no positives or no negatives")
        return out
    fold = grouped_folds(groups, y, seed, folds)
    pred = np.full(len(y), np.nan)
    used = 0
    for k in range(folds):
        te = fold == k
        tr = ~te
        if te.sum() == 0 or len(set(y[tr].tolist())) < 2:
            continue
        mu = np.nanmean(X[tr], axis=0)
        mu = np.where(np.isnan(mu), 0.0, mu)
        sd = np.nanstd(X[tr], axis=0)
        sd = np.where((sd == 0) | np.isnan(sd), 1.0, sd)

        def z(A: np.ndarray) -> np.ndarray:
            Z = (A - mu) / sd
            return np.where(np.isnan(Z), 0.0, Z)

        w, b = gm._logreg_fit(z(X[tr]), y[tr])
        pred[te] = z(X[te]) @ w + b
        used += 1
    m = ~np.isnan(pred)
    a = gm.auroc(y[m], pred[m]) if m.any() and len(set(y[m].tolist())) == 2 else float("nan")
    two = max(a, 1 - a) if not np.isnan(a) else float("nan")
    out.update(auroc=float(a), auroc_two_sided=float(two), folds_used=used,
               status="ok" if used else "no fold had both classes in training")
    return out


# ── labels ───────────────────────────────────────────────────────────────────────────────

def account_labels(groups: Sequence[str], n_positive_accounts: int, seed: int) -> np.ndarray:
    """Account-level labels: `n_positive_accounts` accounts drawn uniformly without
    replacement (sorted account ids, default_rng(seed)); every row of a drawn account is 1."""
    accs = sorted(set(groups))
    k = min(max(int(n_positive_accounts), 1), len(accs) - 1)
    pos = {accs[i] for i in np.random.default_rng(seed).permutation(len(accs))[:k]}
    return np.array([int(g in pos) for g in groups], dtype=int)


def permute_within_account(groups: Sequence[str], y: np.ndarray, seed: int) -> np.ndarray:
    """Session unit: shuffle each account's labels among its own rows (the count of positive
    sessions per account is kept)."""
    y = np.asarray(y, dtype=int)
    rng = np.random.default_rng(seed)
    out = y.copy()
    for g in sorted(set(groups)):
        idx = [i for i, gg in enumerate(groups) if gg == g]
        vals = y[idx]
        out[idx] = vals[rng.permutation(len(idx))]
    return out


# ── the band and the verdict ─────────────────────────────────────────────────────────────

def permutation_band(draw: Callable[[int], dict[str, np.ndarray]], groups: Sequence[str],
                     n_positive_accounts: int, seeds: Iterable[int],
                     fold_seed_offset: int = FOLD_SEED_OFFSET, *,
                     within_account_of: np.ndarray | None = None) -> dict[str, Any]:
    """Per classifier (the keys of ``draw(seed)``, one feature matrix each on the same rows):
    the distribution of the two-sided value over permuted labels. Account-level labels by
    default; with ``within_account_of`` (the observed label vector) the labels are permuted
    within each account instead (session unit)."""
    seeds = list(seeds)
    two: dict[str, list[float]] = {}
    one: dict[str, list[float]] = {}
    for seed in seeds:
        Xs = draw(seed)
        if within_account_of is not None:
            y = permute_within_account(groups, within_account_of, seed)
        else:
            y = account_labels(groups, n_positive_accounts, seed)
        for name, X in Xs.items():
            r = classify_grouped(X, y, groups, seed + fold_seed_offset)
            one.setdefault(name, []).append(r["auroc"])
            two.setdefault(name, []).append(r["auroc_two_sided"])
    out: dict[str, Any] = {"n_perms": len(seeds), "seeds": [int(seeds[0]), int(seeds[-1])] if seeds else [],
                           "fold_seed_offset": int(fold_seed_offset),
                           "label_unit": "session (within account)" if within_account_of is not None
                           else "account", "positive_accounts": int(n_positive_accounts),
                           "classifiers": {}}
    for name in two:
        t = np.asarray(two[name], dtype=float)
        a = np.asarray(one[name], dtype=float)
        t_ok, a_ok = t[~np.isnan(t)], a[~np.isnan(a)]
        out["classifiers"][name] = {
            "gate_p95": float(np.percentile(t_ok, GATE_QUANTILE)) if len(t_ok) else float("nan"),
            "two_sided_p50": float(np.percentile(t_ok, 50)) if len(t_ok) else float("nan"),
            "two_sided_p975": float(np.percentile(t_ok, 97.5)) if len(t_ok) else float("nan"),
            "auroc_mean": float(a_ok.mean()) if len(a_ok) else float("nan"),
            "auroc_min": float(a_ok.min()) if len(a_ok) else float("nan"),
            "auroc_max": float(a_ok.max()) if len(a_ok) else float("nan"),
            "false_kill_rate_of_fixed_0_6_gate": float((t_ok > 0.6).mean()) if len(t_ok) else float("nan"),
            "n_valid": int(len(t_ok)),
            "two_sided_values": [float(x) for x in t]}
    return out


def gate_verdict(observed_two_sided: float, gate_p95: float) -> dict[str, Any]:
    above = bool(not np.isnan(observed_two_sided) and not np.isnan(gate_p95)
                 and observed_two_sided > gate_p95)
    return {"observed_two_sided": float(observed_two_sided), "gate_p95": float(gate_p95),
            "above_band": above, "verdict": "ABOVE the band (leak at the 5 percent level)" if above
            else "inside the band (no leak at the 5 percent level)"}


# ── features for a run ───────────────────────────────────────────────────────────────────

def run_features(corpus: Path, transcripts: Path, template_path: Path, max_turns: int,
                 n_features: int, unit: str) -> dict[str, Any]:
    """Rows (keys), groups (account per row), and the two feature matrices for a run."""
    import grouping_measure as gm
    import mole_corpus as mc
    import stage3_leak_content as lc
    if unit == "account-day":
        template = mc.load_org_template(str(template_path))
        br = gm.load_branch(corpus, None, template, "run", None, transcripts)
        feats, minfo = gm.metadata_features(br, max_turns)
        names = list(minfo["features"])
        feats = feats.sort_values(["account", "date"]).reset_index(drop=True)
        keys = list(zip(feats["account"], feats["date"]))
        Xm = feats[names].to_numpy(dtype=float)
        turns = lc.account_day_turns(transcripts)
        Xc, cinfo = lc.content_matrix(transcripts, keys, n_features, turns)
        groups = [a for a, _ in keys]
        return {"keys": [list(k) for k in keys], "groups": groups, "metadata": Xm, "content": Xc,
                "metadata_features": names, "content_info": cinfo, "unit": unit}
    if unit == "session":
        import stage3_s5c_metadata as sm
        s = sm.session_table(corpus, transcripts, max_turns, read_scenario_fields=False)
        names = ["turn_count", "capped", "events", "first_action_min"]
        Xm = s[names].to_numpy(dtype=float)
        # content per session: the assistant turns of that session's transcript row
        turns_by_session: dict[tuple[str, str], list[tuple[str, list[str]]]] = {}
        with open(transcripts, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                e = json.loads(line)
                if not isinstance(e, dict):
                    continue
                key = (str(e.get("account")), str(e.get("task_id")))
                tl = turns_by_session.setdefault(key, [])
                for m in e.get("messages") or []:
                    if isinstance(m, dict) and m.get("role") == "assistant":
                        c = m.get("content")
                        tl.append((c if isinstance(c, str) else "", lc._tool_names(m)))
        keys = list(zip(s["account"].astype(str), s["task_id"].astype(str)))
        Xc, cinfo = lc.content_matrix(transcripts, keys, n_features, turns_by_session)
        groups = [a for a, _ in keys]
        return {"keys": [list(k) for k in keys], "groups": groups, "metadata": Xm, "content": Xc,
                "metadata_features": names, "content_info": cinfo, "unit": unit,
                "session_task_ids": list(s["task_id"].astype(str)),
                "session_turn_count": [float(x) for x in s["turn_count"]],
                "session_capped": [float(x) for x in s["capped"]]}
    raise ValueError(unit)


def positives_from_manifest(manifest_path: Path) -> set[str]:
    """Coalition accounts of a run manifest's coalitions block."""
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    accs: set[str] = set()
    for inst in (m.get("coalitions") or {}).get("instances", []):
        for r in inst.get("roles", []):
            accs.add(str(r["account"]))
    return accs


def gate_run(feats: dict[str, Any], y: np.ndarray, label_seed: int, n_perms: int,
             perm_seed0: int, fold_seed_offset: int, within_account: bool) -> dict[str, Any]:
    """Observed grouped-CV AUROC per classifier, the permutation band, the verdicts."""
    groups = feats["groups"]
    n_pos_acc = len({g for g, v in zip(groups, y) if v})
    Xs = {"metadata": feats["metadata"], "content": feats["content"]}
    observed = {name: classify_grouped(X, y, groups, label_seed + fold_seed_offset)
                for name, X in Xs.items()}
    band = permutation_band(lambda s: Xs, groups, n_pos_acc, range(perm_seed0, perm_seed0 + n_perms),
                            fold_seed_offset, within_account_of=(y if within_account else None))
    verdicts = {name: gate_verdict(observed[name]["auroc_two_sided"],
                                   band["classifiers"][name]["gate_p95"]) for name in Xs}
    return {"observed": observed, "band": band, "verdicts": verdicts,
            "all_inside": all(not v["above_band"] for v in verdicts.values())}


def paired_onetailed(accounts: Sequence[str], task_ids: Sequence[str], turn_counts: Sequence[float],
                     capped: Sequence[float], positive_task_ids: set[str]) -> dict[str, Any]:
    """Plan v2 gate 6 (brief 07c C3): the pre-specified WITHIN-ACCOUNT one-tailed test. For
    each scenario session (a positive task id) the pair difference is its value minus the
    mean of the SAME account's honest (non-positive) sessions, on turn count and on the
    turn-cap indicator; H1 is "the scenario session is shorter" (mean difference < 0). The
    p-value is the exact sign-flip permutation p: under H0 each pair's sign is exchangeable,
    so p = share of the 2^n sign assignments whose mean difference is <= the observed one
    (all 2^n when n <= 16, else 20,000 random flips, seeded). Pass iff p >= 0.05 on BOTH
    statistics. An account with no honest session yields no pair and is listed. The smallest
    attainable p is 2^-n, so n < 5 pairs cannot reach 0.05 (reported as min_attainable_p)."""
    by_acc: dict[str, dict[str, list[tuple[float, float]]]] = {}
    for a, t, tc, cp in zip(accounts, task_ids, turn_counts, capped):
        d = by_acc.setdefault(str(a), {"pos": [], "hon": []})
        d["pos" if str(t) in positive_task_ids else "hon"].append((float(tc), float(cp)))
    diffs_t, diffs_c, unpaired = [], [], []
    for a in sorted(by_acc):
        d = by_acc[a]
        if not d["pos"]:
            continue
        if not d["hon"]:
            unpaired.append(a)
            continue
        mt = sum(x for x, _ in d["hon"]) / len(d["hon"])
        mc = sum(y for _, y in d["hon"]) / len(d["hon"])
        for tc, cp in d["pos"]:
            diffs_t.append(tc - mt)
            diffs_c.append(cp - mc)
    n = len(diffs_t)

    def _p(diffs: list[float]) -> tuple[float, int, bool]:
        if not diffs:
            return float("nan"), 0, True
        obs = sum(diffs) / len(diffs)
        d = np.asarray(diffs, dtype=float)
        if len(d) <= 16:
            k = len(d)
            signs = ((np.arange(2 ** k)[:, None] >> np.arange(k)) & 1) * 2 - 1
            means = (signs * d).mean(axis=1)
            return float((means <= obs + 1e-12).mean()), int(2 ** k), True
        rng = np.random.default_rng(PERM_SEED0)
        signs = rng.choice([-1.0, 1.0], size=(20000, len(d)))
        means = (signs * d).mean(axis=1)
        return float((means <= obs + 1e-12).mean()), 20000, False

    pt, nf, exact = _p(diffs_t)
    pc, _, _ = _p(diffs_c)
    ok = n > 0 and pt >= 0.05 and pc >= 0.05
    return {"n_pairs": n, "unpaired_accounts": unpaired, "n_sign_flips": nf, "exact": exact,
            "min_attainable_p": (2.0 ** -n) if n else float("nan"),
            "turns": {"mean_diff": (sum(diffs_t) / n) if n else float("nan"), "p_one_tailed": pt,
                      "diffs": diffs_t},
            "capped": {"mean_diff": (sum(diffs_c) / n) if n else float("nan"), "p_one_tailed": pc,
                       "diffs": diffs_c},
            "alternative": "scenario session shorter (mean difference < 0)", "alpha": 0.05,
            "pass": bool(ok)}


def _f3(x: Any) -> str:
    return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.3f}"


def _paired_md(paired: dict[str, Any] | None) -> str:
    if not paired:
        return ""
    return (
        "\n## Paired one-tailed within-account test (plan v2 gate 6)\n\n"
        "Pre-specified: for each scenario session, its turn count (and turn-cap indicator) minus "
        "the mean of the same account's honest sessions; H1 \"the scenario session is shorter\"; "
        "exact sign-flip permutation p (share of sign assignments with mean difference at or below "
        "the observed); pass iff p >= 0.05 on both.\n\n"
        f"Pairs {paired['n_pairs']} (unpaired accounts {paired['unpaired_accounts']}); sign flips "
        f"{paired['n_sign_flips']} ({'exact' if paired['exact'] else 'sampled'}); smallest attainable p "
        f"{_f3(paired['min_attainable_p'])}. Turn count: mean difference {_f3(paired['turns']['mean_diff'])}, "
        f"p = {_f3(paired['turns']['p_one_tailed'])}. Turn cap: mean difference "
        f"{_f3(paired['capped']['mean_diff'])}, p = {_f3(paired['capped']['p_one_tailed'])}. "
        f"**{'PASS' if paired['pass'] else 'FAIL'}** (band verdicts above are the corroboration).\n")


def _render_md_core(res: dict[str, Any]) -> str:
    m = res["meta"]
    lines = [f"# Permutation leak gate: {m['label']}", "",
             f"Computed {m['utc']} by `work/checks/stage3_leak_gate.py` ({VERSION}); corpus "
             f"`{m['corpus']}` (sha256 {m['corpus_sha256'][:12]}), transcripts sha256 "
             f"{m['transcripts_sha256'][:12]}; unit {m['unit']}; positives: {m['positives_source']}; "
             f"label seed {m['label_seed']}; {m['n_perms']} permutations (seeds {m['perm_seed0']}..); "
             f"fold seed offset {m['fold_seed_offset']}; grouped-by-account {FOLDS}-fold CV. "
             f"$0, no LLM calls. Tag: **tested**.", "", prereg_block(), "",
             "## Result", "",
             f"Rows {res['n_rows']}, accounts {res['n_accounts']}, positive rows {res['n_positive_rows']}, "
             f"positive accounts {res['n_positive_accounts']}.", "",
             "| classifier | observed AUROC | observed two-sided | gate (p95 of null two-sided) | "
             "null two-sided p50 / p97.5 | null AUROC mean [min, max] | false-kill rate of the fixed 0.6 gate | verdict |",
             "|---|---|---|---|---|---|---|---|"]
    for name, v in res["gate"]["verdicts"].items():
        o = res["gate"]["observed"][name]
        b = res["gate"]["band"]["classifiers"][name]
        lines.append(f"| {name} | {_f3(o['auroc'])} | {_f3(o['auroc_two_sided'])} | {_f3(b['gate_p95'])} | "
                     f"{_f3(b['two_sided_p50'])} / {_f3(b['two_sided_p975'])} | {_f3(b['auroc_mean'])} "
                     f"[{_f3(b['auroc_min'])}, {_f3(b['auroc_max'])}] | {_f3(b['false_kill_rate_of_fixed_0_6_gate'])} | "
                     f"**{v['verdict']}** |")
    lines += ["", f"**Verdict: {'PASS (every classifier inside its band)' if res['gate']['all_inside'] else 'ABOVE THE BAND on ' + ', '.join(n for n, v in res['gate']['verdicts'].items() if v['above_band'])}.**", "",
              f"Features: metadata {res['metadata_features']}; content: {res['content_info']['feature_description']}", ""]
    if res.get("note"):
        lines += ["Note: " + res["note"], ""]
    return "\n".join(lines)


def render_md(res: dict[str, Any]) -> str:
    return _render_md_core(res) + _paired_md(res.get("paired_onetailed"))


def main(argv: list[str] | None = None) -> int:
    import grouping_measure as gm
    import stage3_leak_content as lc
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--transcripts", default=None)
    ap.add_argument("--template", default=str(gm.DEFAULT_TEMPLATE))
    ap.add_argument("--unit", choices=UNITS, default="account-day")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--positive-accounts", default=None, help="comma-separated account ids")
    g.add_argument("--manifest", default=None, help="run manifest: coalition accounts are positive")
    g.add_argument("--random-accounts", type=int, default=None,
                   help="honest-null check: this many accounts drawn positive by --label-seed")
    g.add_argument("--positive-task-ids", default=None,
                   help="session unit: comma-separated task ids of the positive sessions")
    ap.add_argument("--label-seed", type=int, default=20261020)
    ap.add_argument("--n-perms", type=int, default=N_PERMS)
    ap.add_argument("--perm-seed0", type=int, default=PERM_SEED0)
    ap.add_argument("--fold-seed-offset", type=int, default=FOLD_SEED_OFFSET)
    ap.add_argument("--max-turns", type=int, default=MAX_TURNS)
    ap.add_argument("--n-features", type=int, default=lc.N_FEATURES)
    ap.add_argument("--paired-onetailed", action="store_true",
                    help="plan v2 gate 6: the within-account one-tailed paired test (scenario "
                         "session shorter) on turn count and turn-cap; needs --unit session "
                         "and --positive-task-ids")
    ap.add_argument("--label", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ns = ap.parse_args(argv)
    corpus = Path(ns.corpus)
    transcripts = Path(ns.transcripts) if ns.transcripts else gm.default_transcripts(corpus)
    feats = run_features(corpus, transcripts, Path(ns.template), ns.max_turns, ns.n_features, ns.unit)
    groups = feats["groups"]
    within = False
    if ns.random_accounts is not None:
        y = account_labels(groups, ns.random_accounts, ns.label_seed)
        src = f"random draw of {ns.random_accounts} accounts (honest-null check)"
    elif ns.positive_task_ids is not None:
        if ns.unit != "session":
            ap.error("--positive-task-ids needs --unit session")
        pos = set(x.strip() for x in ns.positive_task_ids.split(",") if x.strip())
        y = np.array([int(t in pos) for t in feats["session_task_ids"]], dtype=int)
        src = f"{len(pos)} positive sessions by task id (null permuted within account)"
        within = True
    else:
        pos = (positives_from_manifest(Path(ns.manifest)) if ns.manifest
               else set(x.strip() for x in ns.positive_accounts.split(",") if x.strip()))
        y = np.array([int(g in pos) for g in groups], dtype=int)
        src = f"{len(pos)} positive accounts ({'manifest' if ns.manifest else 'given'})"
    gate = gate_run(feats, y, ns.label_seed, ns.n_perms, ns.perm_seed0, ns.fold_seed_offset, within)
    paired = None
    if ns.paired_onetailed:
        if ns.unit != "session" or ns.positive_task_ids is None:
            ap.error("--paired-onetailed needs --unit session and --positive-task-ids")
        paired = paired_onetailed(feats["groups"], feats["session_task_ids"],
                                  feats["session_turn_count"], feats["session_capped"], pos)
    res = {
        "meta": {"version": VERSION, "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "label": ns.label or corpus.stem, "corpus": str(corpus),
                 "corpus_sha256": gm.sha256_file(corpus), "transcripts": str(transcripts),
                 "transcripts_sha256": gm.sha256_file(transcripts), "unit": ns.unit,
                 "positives_source": src, "label_seed": ns.label_seed, "n_perms": ns.n_perms,
                 "perm_seed0": ns.perm_seed0, "fold_seed_offset": ns.fold_seed_offset,
                 "script_sha256": gm.sha256_file(__file__), "llm_calls": 0, "cost_usd": 0.0,
                 "command": " ".join(sys.argv[1:] if argv is None else argv)},
        "preregistration": prereg_block(),
        "n_rows": len(groups), "n_accounts": len(set(groups)), "n_positive_rows": int(y.sum()),
        "n_positive_accounts": len({g for g, v in zip(groups, y) if v}),
        "positive_accounts": sorted({g for g, v in zip(groups, y) if v}),
        "metadata_features": feats["metadata_features"], "content_info": feats["content_info"],
        "gate": gate, "paired_onetailed": paired, "note": ns.note,
    }
    out_json, out_md = Path(ns.out_json), Path(ns.out_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(gm._clean(res), indent=1, default=gm._json_default) + "\n", encoding="utf-8")
    out_md.write_text(render_md(res), encoding="utf-8")
    for name, v in gate["verdicts"].items():
        print(f"{name}: observed two-sided {_f3(v['observed_two_sided'])} vs gate {_f3(v['gate_p95'])} -> {v['verdict']}")
    if paired is not None:
        print(f"paired one-tailed (within account, scenario shorter): n_pairs {paired['n_pairs']}, "
              f"turns mean diff {_f3(paired['turns']['mean_diff'])} p {_f3(paired['turns']['p_one_tailed'])}, "
              f"capped mean diff {_f3(paired['capped']['mean_diff'])} p {_f3(paired['capped']['p_one_tailed'])}, "
              f"min attainable p {_f3(paired['min_attainable_p'])} -> {'PASS' if paired['pass'] else 'FAIL'}")
    print(f"wrote {out_json} and {out_md}")
    return 0 if (gate["all_inside"] and (paired is None or paired["pass"])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
