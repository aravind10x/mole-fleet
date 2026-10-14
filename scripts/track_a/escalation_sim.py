#!/usr/bin/env python3
"""Track A policy simulator: budget-paced escalation across a fleet.

Transcription of work/mole-fork/protocol/TRACK-A.md sections 1 and 4 to 8 (pre-registration),
with PACE as restated by that file's Amendment 1 (section 4's original PACE survives as
PacePolicyV0, run only under --pace-v0 as a post hoc comparison row).
Every resolution of an ambiguity in that text is marked `# RESOLVED:` below and listed in
RESOLUTIONS (written into the results JSON and markdown).

Inputs
  --cheap      <corpus>.cheap.parquet (work/checks/score_cheap_tier.py). Read by load_cheap(),
               which reads ONLY label-free columns: account, date, day_index, is_eval_day, c_z,
               c_z_cal, l1_nonnoisy.
  --expensive  <corpus>.expensive.parquet (work/checks/score_expensive_tier.py) and its sibling
               <...>.expensive.meta.json; refused unless meta `complete` is true, or
               --allow-incomplete.
  --labels     upstream labels parquet (account, date, scenario, outcome).

LABELS: read_labels() is the ONLY function that touches label data (the labels parquet and,
for a cross-check, the cheap table's is_positive_* / labelled_account columns). Its output
never feeds a policy except ORACLE (labels known by definition) and the metrics.

Policies are classes with `choose(day_rows, state) -> set of account-day ids` (ids are integer
row indices into the World) and `observe(day_rows, chosen, results, state)` (results =
{id: surfaced} for the policy's own calls of the day, the only expensive information a policy
ever receives). The deployed call count is the sum of the sizes of the chosen sets.

    work/mole-fork/.venv/bin/python -I work/checks/escalation_sim.py \\
      --cheap work/stage2/scores/gpt53_single_day.cheap.parquet \\
      --expensive work/stage2/scores/gpt53_single_day.expensive.parquet \\
      --labels work/upstream-data/data/labels/gpt53_single_day/0000.parquet \\
      --out-md work/stage2/a-track-a-results.md --out-json work/stage2/a-track-a-results.json \\
      --fig work/stage2/fig-phase-diagram.png

    work/mole-fork/.venv/bin/python -I work/checks/escalation_sim.py --synthetic-selftest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = Path(__file__).resolve()
PROJECT = HERE.parent.parent.parent

# ── pre-registered constants (TRACK-A.md) ────────────────────────────────
SEED = 20261014
CAL_DAYS = tuple(range(1, 6))                 # section 1
EVAL_DAYS = tuple(range(6, 31))               # section 1
KS = (2, 5, 10, 15, 20)                       # section 4
PRIMARY_K = 10
THETA = 50.0                                  # section 3
ETA = 0.2                                     # PACE controller gain
Y_STAR0 = 0.5
Y_CLAMP = (0.05, 0.95)                 # Amendment 1 step 3
PACE_V0_KEY = "PACE-v0(w=3, r=0.2)"     # post hoc comparison row (--pace-v0)
C_LAMBDAS = (0.8, 0.9, 0.95)
PACE_W = (3, 5)
PACE_R = (0.0, 0.2, 0.4)
PRIMARY_PACE = ("PACE", (("w", 3), ("r", 0.2)))
N_BUCKETS = 10
BURST_HISTORY = 5
N_BURST_DAYS = 5                              # section 6 burstiness / adversarial
RATES = (1.0, 0.5, 0.25)
PLACEMENTS = ("original", "burst5", "uniform", "adversarial")
SURF_DEFS = ("theta50", "refusal_as_zero", "theta95")
DEPLOYABLE = ("U", "S", "C", "PACE", "NP")
CAPTION = "tested: work/checks/escalation_sim.py"

RESOLUTIONS = [
    "R1 positives: an account-day is an executed positive if any label row for it has outcome "
    "'executed'; attempted if it has an 'attempted' row and no 'executed' row. Labelled account = "
    "any label row on any day (all 38, including accounts whose only rows are attempted or on "
    "days 1..5). Positives are counted on evaluation days 6..30 only.",
    "R2 expensive outcomes: surfaced = called and (outcome refused, or outcome scored with "
    "score >= theta). Errored rows and account-days with no expensive record (only possible "
    "with --allow-incomplete) are called-but-not-surfaced; a call to them still counts as a "
    "deployed call. The policies' feedback uses the same surfaced definition as the metric "
    "under each sensitivity (refusal-as-zero and theta95 re-run every policy).",
    "R3 AUROC of e: refused = 100 (sensitivity refused = 0); errored/missing = 0 (conservative, "
    "consistent with 'errored = not surfaced'); a version excluding errored/missing rows is "
    "also reported. Ties count one half. K2 is decided on the point estimates "
    "(AUROC(e) > AUROC(c)); the cluster-bootstrap interval of the difference is informative.",
    "R4 theta95: numpy linear-interpolation 95th percentile of e over never-labelled "
    "account-days of days 6..10, refused counted as 100, errored/missing excluded.",
    "R5 within-day percentile rank q = (average rank - 1)/(n - 1) over all account-days "
    "scheduled on the day (q = 1 when n = 1). PACE bucket = min(9, floor(10 q)).",
    "R6 tie-breaks: every top-n ordering is by the policy score descending, then c descending, "
    "then account-day id ascending (ids are integer positions in the (account, date)-sorted "
    "table; c_z has exact ties). U samples with random.Random(seed + d).sample over the day's "
    "ids in that ascending order.",
    "R7 C: an account with no account-day on day d keeps pi_a unchanged (no decay); if an "
    "account has several account-days on one day (re-timed regimes only) each row gets "
    "pi = lambda pi_a(d-1) + (1 - lambda) q_row, the stored pi_a(d) is the maximum over its "
    "rows, then set to 1 if any of its called rows surfaced, else halved if any was called.",
    "R8 PACE window: calls made on days before day 6 are 0. A_d is never negative (proved in "
    "pace_call_bound). Spendable n_d is floored to an integer (r K is fractional for some k).",
    "R9 PACE burst: mass = sum of c over the account-days scheduled on the day (re-timed "
    "positives included, removed ones excluded); days 1..5 use c_z_cal; 'standard deviation' "
    "is the population SD (ddof = 0) of the five previous daily masses; strict '>'.",
    "R10 PACE controller: 'calls made so far' = calls on days 6..d-1 (today's set is not yet "
    "chosen) compared with plan-to-date k (d - 5); the update runs before today's call set "
    "is chosen; 'short by more than k' = plan - so_far > k (strict).",
    "R11 PACE call set: ranked by Y[bucket] desc then c desc then id; only rows with "
    "Y[bucket] >= y* are eligible; at most n_d are called. Y[b] = surfaced/(surfaced + not) "
    "with the pseudo-counts; a result updates the bucket the row had on the day it was called.",
    "R12 NP: tau = the (5k + 1)-th largest c_z_cal over all account-days of days 1..5, so "
    "exactly 5k exceed it absent ties; every evaluation account-day with c_z > tau is called. "
    "The realised calibration mean per day is reported.",
    "R13 ORACLE knows the executed positives present in the regime; positives first (by c), "
    "then the rest by c, cut at k. It bounds only policies spending at most k per day; PACE "
    "(up to 2k per day) and NP (unbounded) can exceed it on allocation recall.",
    "R14 regimes act on the executed evaluation-day positives only; attempted positives and "
    "every non-positive account-day stay on their own day; calibration days are untouched. "
    "Rate and placement are crossed (3 x 4 grid, the phase-diagram axes): subsample first "
    "(random.Random(seed).sample, n_keep = floor(rate n + 0.5)), then re-time the kept set.",
    "R15 burst5: days = sorted(Random(seed).sample(days 6..30, 5)); the positives (sorted by id) "
    "are shuffled with the same generator and dealt round-robin over those days (even, not "
    "multinomial). uniform: a fresh Random(seed) shuffle dealt round-robin over days 6..30.",
    "R16 adversarial: the 5 evaluation days with the highest never-labelled c mass (ties by "
    "earlier day), positives sorted by (original day, id) dealt round-robin in descending "
    "order of that mass (5 days to match the burst regime's concentration).",
    "R17 bootstrap: one (B x 38) multinomial weight matrix from np.random.default_rng(seed) "
    "over the sorted labelled accounts, shared by every cell so differences are paired; "
    "percentile intervals (2.5, 97.5); recall = weighted positives hit / weighted positives. "
    "Honest flag rate and call counts are point values (no interval; honest accounts are not "
    "the resampled unit).",
    "R18 'every policy difference' = each policy-parameter cell minus S, and minus "
    "PACE(w=3, r=0.2), on detection recall, at every k, regime and sensitivity (JSON); the "
    "markdown shows the difference to S.",
    "R19 row labels: primary = PACE(w=3, r=0.2) and S at k = 10, original schedule, theta = 50, "
    "detection recall; secondary = every other pre-registered policy-parameter cell on theta = "
    "50 (all k, all regimes), budget-AUC, ORACLE, K2 and expensive-tier quality; exploratory = "
    "the refusal-as-zero and theta95 sensitivities, the attempted-positive set and the layer-1 "
    "ceiling row.",
    "R20 dollars = deployed calls x the expensive meta's summary.mean_cost_usd (mean over every "
    "record, errored included); fallback the mean of the table's cost_usd.",
    "R21 figure: winner = the policy family (U, S, C, PACE, NP; ORACLE excluded) owning the best "
    "parameter cell by detection recall at k = 10; exact ties are drawn grey and named. Panel 2 "
    "is the same by allocation recall; panel 3 shows the deployed calls of panel 1's winner "
    "(cell colour = that policy, text = calls and calls / 25k).",
    "R22 seeds: --seed is the base of all three pre-registered seeds (U: seed + d; regimes: "
    "seed; bootstrap: seed); default 20261014.",
    "R8-R11 describe PACE v0 (section 4 as first written), now run only post hoc under "
    "--pace-v0. For amended PACE (Amendment 1), R5, R6 and R9's burst conventions carry over "
    "unchanged and A1-A7 below apply.",
    "A1 PAV: weighted pool-adjacent-violators over the 10 buckets in index order, weights = "
    "surfaced + not surfaced counts including the prior pseudo-counts, refit before every "
    "day's choice from the counts at that moment.",
    "A2 carry (per Amendment 1's erratum, FIFO ledger consumed once): day j deposits "
    "max(0, (1 - r) k - calls_j) after its calls; the deposit is live on days j + 1 .. j + w - 1 "
    "(so C_6 = 0) and expires after; a day's calls above (1 - r) k are paid from the ledger "
    "first (oldest live deposits first) and only the remainder from the reserve pool (burst "
    "days); deposits and draws are reals. The cap (w - 1)(1 - r) k cannot bind.",
    "A3 reserve pool: P starts at 0 before day 6; on every evaluation day the gain r k is added "
    "(capped at r k w) before the day's cap is computed, so P_6 = r k. Reserve used on a burst "
    "day = min(P_d, max(0, calls_d - ((1 - r) k + C_d))); nothing is drawn on non-burst days. "
    "Fractional amounts are kept as reals; only n_d is floored.",
    "A4 controller: 'calls so far' = calls on days 6..d-1 (as R10), plan = (1 - r) k (d - 5) "
    "(literal; the factor d - 5 includes today, so steady spending at the base rate sits "
    "(1 - r) k <= k below plan, inside the dead band); both band tests strict (> k); update "
    "before today's choice.",
    "A5 call set: rows are ranked by isotonic Y[bucket] desc, then c desc, then id; qualifying "
    "rows (Y >= y*) form a prefix of that ranking; the spend floor calls the top floor(n_d / 2) "
    "by that ranking (capped by the rows available) when fewer than floor(n_d / 2) qualify.",
    "A6 deployed-call bound for amended PACE (selftest): calls_d <= n_d <= 2k, and total <= "
    "25 (1 - r) k + reserve used <= 25 k (proof in pace_total_bound: each deposit is drawn at "
    "most once and the pool gains at most 25 r k).",
    "A7 --pace-v0 adds one post hoc row, PACE-v0(w=3, r=0.2), on the original schedule at "
    "theta = 50 for every k (per-k tables, budget-AUC, attempted), labelled 'exploratory (post "
    "hoc)'; it is excluded from the regime grid, the sensitivities and the figure, and is not "
    "a comparator in any difference column.",
]


# ── small utilities ──────────────────────────────────────────────────────

def sha256_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sibling(out: Path, suffix: str) -> Path:
    """Same rule as score_expensive_tier.sibling: x.expensive.parquet -> x.expensive.meta.json."""
    out = Path(out)
    stem = out.name[: -len(".parquet")] if out.name.endswith(".parquet") else out.stem
    return out.with_name(stem + suffix)


def within_day_rank(c: np.ndarray) -> np.ndarray:
    """q in [0, 1]: (average rank - 1) / (n - 1); q = 1 for a single row (R5)."""
    n = len(c)
    if n == 0:
        return np.zeros(0)
    if n == 1:
        return np.ones(1)
    return (rankdata(c, method="average") - 1.0) / (n - 1.0)


def bucket_of(q: np.ndarray) -> np.ndarray:
    return np.minimum(N_BUCKETS - 1, np.floor(N_BUCKETS * q).astype(int))


def order_desc(score: np.ndarray, c: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """Positions sorted by score desc, then c desc, then id asc (R6)."""
    return np.lexsort((ids, -c, -score))


def auroc(pos: np.ndarray, neg: np.ndarray) -> float:
    pos, neg = np.asarray(pos, float), np.sort(np.asarray(neg, float))
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float(win_fractions(pos, neg).mean())


def win_fractions(pos: np.ndarray, neg_sorted: np.ndarray) -> np.ndarray:
    """Per positive: P(neg < x) + 0.5 P(neg == x)."""
    lo = np.searchsorted(neg_sorted, pos, side="left")
    hi = np.searchsorted(neg_sorted, pos, side="right")
    return (lo + 0.5 * (hi - lo)) / len(neg_sorted)


# ── surfaced / theta (section 3, R2-R4) ──────────────────────────────────

def surfaced_vector(outcome: np.ndarray, score: np.ndarray, theta: float,
                    refusal_as_zero: bool = False) -> np.ndarray:
    """surfaced = refused (unless refusal-as-zero) or (scored and score >= theta).
    errored / missing -> False."""
    outcome = np.asarray(outcome, dtype=object)
    score = np.asarray(score, dtype=float)
    scored = (outcome == "scored") & np.isfinite(score)
    s = scored & (np.where(np.isfinite(score), score, -np.inf) >= theta)
    if not refusal_as_zero:
        s = s | (outcome == "refused")
    return s


def e_for_auroc(outcome: np.ndarray, score: np.ndarray, refused_value: float = 100.0,
                errored_value: float | None = 0.0) -> np.ndarray:
    """e with refused -> refused_value; errored/missing -> errored_value (NaN if None)."""
    outcome = np.asarray(outcome, dtype=object)
    e = np.asarray(score, dtype=float).copy()
    e[outcome == "refused"] = refused_value
    bad = ~np.isin(outcome, ["scored", "refused"]) | ((outcome == "scored") & ~np.isfinite(e))
    e[bad] = np.nan if errored_value is None else errored_value
    return e


def theta95(outcome, score, honest_mask, day, days=(6, 10)) -> float:
    e = e_for_auroc(outcome, score, refused_value=100.0, errored_value=None)
    sel = honest_mask & (day >= days[0]) & (day <= days[1]) & np.isfinite(e)
    return float(np.percentile(e[sel], 95)) if sel.any() else float("nan")


# ── loaders ──────────────────────────────────────────────────────────────

CHEAP_COLS = ["account", "date", "day_index", "is_eval_day", "c_z", "c_z_cal"]
CHEAP_OPTIONAL = ["l1_nonnoisy"]
EXP_COLS = ["account", "date", "day_index", "outcome", "score", "cost_usd", "model"]


def load_cheap(path: Path) -> pd.DataFrame:
    """Label-free columns only (no is_positive_*, scenario, labelled_account)."""
    import pyarrow.parquet as pq
    names = set(pq.read_schema(path).names)
    cols = CHEAP_COLS + [c for c in CHEAP_OPTIONAL if c in names]
    df = pd.read_parquet(path, columns=cols)
    if "l1_nonnoisy" not in df:
        df["l1_nonnoisy"] = False
    df = df.sort_values(["account", "date"], kind="stable").reset_index(drop=True)
    if df.duplicated(["account", "date"]).any():
        raise SystemExit("cheap table has duplicate (account, date) rows")
    ev = df["day_index"].isin(EVAL_DAYS)
    if not (ev == df["is_eval_day"].astype(bool)).all():
        raise SystemExit("cheap table is_eval_day disagrees with day_index in 6..30")
    if df.loc[ev, "c_z"].isna().any():
        raise SystemExit("cheap table has null c_z on an evaluation day")
    if df.loc[df["day_index"].isin(CAL_DAYS), "c_z_cal"].isna().any():
        raise SystemExit("cheap table has null c_z_cal on a calibration day")
    return df


def load_expensive(path: Path, allow_incomplete: bool) -> tuple[pd.DataFrame, dict]:
    meta_path = sibling(Path(path), ".meta.json")
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else None
    if meta is None and not allow_incomplete:
        raise SystemExit(f"refusing: no meta {meta_path} (use --allow-incomplete to override)")
    if meta is not None and meta.get("complete") is not True and not allow_incomplete:
        raise SystemExit(f"refusing: expensive table meta says complete={meta.get('complete')!r} "
                         f"(use --allow-incomplete to override)")
    import pyarrow.parquet as pq
    names = set(pq.read_schema(path).names)
    df = pd.read_parquet(path, columns=[c for c in EXP_COLS if c in names])
    if df.duplicated(["account", "date"]).any():
        raise SystemExit("expensive table has duplicate (account, date) rows")
    bad = set(df["outcome"]) - {"scored", "refused", "errored"}
    if bad:
        raise SystemExit(f"expensive table has unknown outcomes {bad}")
    return df, (meta or {})


def read_labels(labels_path: Path, units: list[tuple[str, str]],
                cheap_path: Path | None = None) -> dict:
    """##### LABEL READ #####  The only function that reads label data. Returns the executed
    and attempted positive account-day sets, the labelled-account set and consistency info.
    If cheap_path is given and carries is_positive_* columns, they must agree."""
    lab = pd.read_parquet(labels_path, columns=["account", "date", "outcome"])
    labelled = sorted(set(lab["account"]))
    executed, attempted, other = set(), set(), {}
    for a, d, oc in zip(lab["account"], lab["date"], lab["outcome"]):
        if oc == "executed":
            executed.add((a, d))
        elif oc == "attempted":
            attempted.add((a, d))
        else:
            other[str(oc)] = other.get(str(oc), 0) + 1
    attempted -= executed                                          # R1
    uset = set(units)
    not_units = sorted(f"{a}/{d}" for a, d in (executed | attempted) - uset)
    info = {"n_label_rows": int(len(lab)), "n_labelled_accounts": len(labelled),
            "other_outcomes": other, "label_rows_not_units": not_units[:20],
            "n_label_rows_not_units": len(not_units)}
    if cheap_path is not None:
        import pyarrow.parquet as pq
        names = set(pq.read_schema(cheap_path).names)
        if {"is_positive_executed", "is_positive_attempted", "labelled_account"} <= names:
            ch = pd.read_parquet(cheap_path, columns=["account", "date", "is_positive_executed",
                                                      "is_positive_attempted", "labelled_account"])
            keys = list(zip(ch["account"], ch["date"]))
            mm_ex = sum(1 for k, v in zip(keys, ch["is_positive_executed"]) if bool(v) != (k in executed))
            mm_at = sum(1 for k, v in zip(keys, ch["is_positive_attempted"]) if bool(v) != (k in attempted))
            ls = set(labelled)
            mm_la = sum(1 for k, v in zip(keys, ch["labelled_account"]) if bool(v) != (k[0] in ls))
            info["cheap_crosscheck"] = {"mismatch_executed": mm_ex, "mismatch_attempted": mm_at,
                                        "mismatch_labelled_account": mm_la}
            if mm_ex or mm_la:
                raise SystemExit(f"refusing: labels disagree with the cheap table {info['cheap_crosscheck']}")
    return {"executed": executed, "attempted": attempted, "labelled_accounts": labelled, "info": info}


# ── the world ────────────────────────────────────────────────────────────

@dataclass
class World:
    account: np.ndarray            # str per row
    date: np.ndarray
    day: np.ndarray                # original day index
    c: np.ndarray                  # c_z on eval days, c_z_cal on calibration days
    c_cal: np.ndarray
    l1: np.ndarray
    outcome: np.ndarray            # scored / refused / errored / missing / '' (calibration)
    score: np.ndarray
    is_exec: np.ndarray
    is_att: np.ndarray
    labelled: np.ndarray           # row's account is labelled
    honest: np.ndarray             # eval-day row of a never-labelled account
    acc_idx: np.ndarray            # index into labelled_accounts, -1 if not labelled
    labelled_accounts: list
    eval_mask: np.ndarray
    mean_cost: float
    meta: dict = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.day)


def build_world(cheap: pd.DataFrame, exp: pd.DataFrame, labels: dict, exp_meta: dict,
                allow_incomplete: bool) -> World:
    df = cheap.copy()
    ex = exp.set_index(["account", "date"])
    ev = df["day_index"].isin(EVAL_DAYS).to_numpy()
    keys = list(zip(df["account"], df["date"]))
    ex_keys = set(ex.index)
    eval_keys = {k for k, e in zip(keys, ev) if e}
    extra = ex_keys - eval_keys
    if extra:
        raise SystemExit(f"expensive table has {len(extra)} rows that are not evaluation "
                         f"account-days of the cheap table, e.g. {sorted(extra)[:3]}")
    missing = eval_keys - ex_keys
    if missing and not allow_incomplete:
        raise SystemExit(f"refusing: {len(missing)} evaluation account-days have no expensive "
                         f"record (use --allow-incomplete)")
    oc_map = ex["outcome"].to_dict()
    sc_map = ex["score"].to_dict()
    outcome = np.array([oc_map.get(k, "missing") if e else "" for k, e in zip(keys, ev)], dtype=object)
    score = np.array([float(sc_map.get(k, np.nan)) if e else np.nan for k, e in zip(keys, ev)])
    c = np.where(ev, df["c_z"].to_numpy(float), df["c_z_cal"].to_numpy(float))
    executed, attempted = labels["executed"], labels["attempted"]
    lab_accts = list(labels["labelled_accounts"])
    aidx = {a: i for i, a in enumerate(lab_accts)}
    acc_idx = np.array([aidx.get(a, -1) for a in df["account"]])
    labelled = acc_idx >= 0
    mc = None
    if exp_meta.get("summary", {}).get("mean_cost_usd") is not None:
        mc = float(exp_meta["summary"]["mean_cost_usd"])
    elif "cost_usd" in exp and len(exp):
        mc = float(exp["cost_usd"].mean())
    return World(
        account=df["account"].to_numpy(object), date=df["date"].to_numpy(object),
        day=df["day_index"].to_numpy(int), c=c, c_cal=df["c_z_cal"].to_numpy(float),
        l1=df["l1_nonnoisy"].fillna(False).to_numpy(bool), outcome=outcome, score=score,
        is_exec=np.array([k in executed for k in keys]) & ev,
        is_att=np.array([k in attempted for k in keys]) & ev,
        labelled=labelled, honest=(~labelled) & ev, acc_idx=acc_idx,
        labelled_accounts=lab_accts, eval_mask=ev, mean_cost=mc if mc is not None else float("nan"),
        meta={"n_missing_expensive": len(missing), "allow_incomplete": allow_incomplete},
    )


# ── regimes (section 6) ──────────────────────────────────────────────────

def subsample_positives(pos_ids: list[int], rate: float, seed: int) -> list[int]:
    pos_ids = sorted(pos_ids)
    if rate >= 1.0:
        return pos_ids
    n_keep = int(math.floor(rate * len(pos_ids) + 0.5))
    return sorted(random.Random(seed).sample(pos_ids, n_keep))


def place_burst(pos_ids: list[int], seed: int, days=EVAL_DAYS, n_days=N_BURST_DAYS) -> dict[int, int]:
    rng = random.Random(seed)
    chosen = sorted(rng.sample(list(days), n_days))
    order = sorted(pos_ids)
    rng.shuffle(order)
    return {p: chosen[i % n_days] for i, p in enumerate(order)}


def place_uniform(pos_ids: list[int], seed: int, days=EVAL_DAYS) -> dict[int, int]:
    rng = random.Random(seed)
    order = sorted(pos_ids)
    rng.shuffle(order)
    days = list(days)
    return {p: days[i % len(days)] for i, p in enumerate(order)}


def adversarial_days(honest_mass: dict[int, float], n_days=N_BURST_DAYS) -> list[int]:
    return [d for d, _ in sorted(honest_mass.items(), key=lambda kv: (-kv[1], kv[0]))[:n_days]]


def place_adversarial(pos_ids: list[int], orig_day: dict[int, int], honest_mass: dict[int, float],
                      n_days=N_BURST_DAYS) -> dict[int, int]:
    days = adversarial_days(honest_mass, n_days)
    order = sorted(pos_ids, key=lambda p: (orig_day[p], p))
    return {p: days[i % len(days)] for i, p in enumerate(order)}


@dataclass
class Schedule:
    name: str
    rate: float
    placement: str
    sim_day: np.ndarray            # per row: simulated day (0 = removed); calibration rows keep theirs
    pos_ids: np.ndarray            # executed positives present
    att_ids: np.ndarray            # attempted positives present (never re-timed)
    by_day: dict                   # d -> ids (sorted) for every day 1..30
    mass: dict                     # d -> c mass (c_z_cal on 1..5)


def make_schedule(w: World, rate: float, placement: str, seed: int = SEED) -> Schedule:
    ids = np.arange(w.n)
    pos0 = [int(i) for i in ids[w.is_exec]]
    kept = subsample_positives(pos0, rate, seed)
    sim_day = w.day.copy()
    removed = set(pos0) - set(kept)
    if removed:
        sim_day[list(removed)] = 0
    if placement == "original":
        newday = {}
    elif placement == "burst5":
        newday = place_burst(kept, seed)
    elif placement == "uniform":
        newday = place_uniform(kept, seed)
    elif placement == "adversarial":
        hm = {d: float(w.c[w.honest & (w.day == d)].sum()) for d in EVAL_DAYS}
        newday = place_adversarial(kept, {p: int(w.day[p]) for p in kept}, hm)
    else:
        raise ValueError(placement)
    for p, d in newday.items():
        sim_day[p] = d
    by_day = {d: ids[sim_day == d] for d in range(1, 31)}
    mass = {d: float(w.c[by_day[d]].sum()) for d in range(1, 31)}
    name = f"rate{int(round(rate * 100))}/{placement}"
    return Schedule(name=name, rate=rate, placement=placement, sim_day=sim_day,
                    pos_ids=np.array(sorted(kept), dtype=int), att_ids=ids[w.is_att],
                    by_day=by_day, mass=mass)


# ── policies (section 4) ─────────────────────────────────────────────────

@dataclass
class DayRows:
    d: int
    ids: np.ndarray
    c: np.ndarray
    acct: np.ndarray


@dataclass
class SimState:
    k: int
    mass: dict                      # d -> daily c mass (today and the past are what policies read)
    calls: dict = field(default_factory=dict)    # d -> calls made by this policy

    def calls_between(self, lo: int, hi: int) -> int:
        return sum(self.calls.get(x, 0) for x in range(lo, hi + 1))


class Policy:
    family = "?"
    params: tuple = ()

    @property
    def key(self) -> str:
        if not self.params:
            return self.family
        return f"{self.family}(" + ", ".join(f"{k}={v:g}" for k, v in self.params) + ")"

    def choose(self, day_rows: DayRows, state: SimState) -> set:
        raise NotImplementedError

    def observe(self, day_rows: DayRows, chosen: set, results: dict, state: SimState) -> None:
        pass


class UniformPolicy(Policy):
    family = "U"

    def __init__(self, seed: int = SEED):
        self.seed = seed

    def choose(self, day_rows, state):
        pool = sorted(int(i) for i in day_rows.ids)
        return set(random.Random(self.seed + day_rows.d).sample(pool, min(state.k, len(pool))))


class SelectivePolicy(Policy):
    family = "S"

    def choose(self, day_rows, state):
        o = order_desc(day_rows.c, day_rows.c, day_rows.ids)
        return {int(i) for i in day_rows.ids[o[: state.k]]}


class CredencePolicy(Policy):
    family = "C"

    def __init__(self, lam: float):
        self.lam = lam
        self.params = (("lambda", lam),)
        self.pi: dict = {}
        self._pending = None

    def choose(self, day_rows, state):
        q = within_day_rank(day_rows.c)
        prev = np.array([self.pi.get(a, 0.5) for a in day_rows.acct])
        pi_row = self.lam * prev + (1.0 - self.lam) * q
        prio = pi_row * q
        self._pending = pi_row
        o = order_desc(prio, day_rows.c, day_rows.ids)
        return {int(i) for i in day_rows.ids[o[: state.k]]}

    def observe(self, day_rows, chosen, results, state):
        pi_row = self._pending
        new: dict = {}
        for a, p in zip(day_rows.acct, pi_row):
            new[a] = max(new.get(a, -1.0), float(p))
        hit, called = set(), set()
        for i, a in zip(day_rows.ids, day_rows.acct):
            if int(i) in chosen:
                called.add(a)
                if results[int(i)]:
                    hit.add(a)
        for a, p in new.items():
            if a in hit:
                p = 1.0
            elif a in called:
                p = 0.5 * p
            self.pi[a] = p


def is_burst(mass_today: float, prev_masses: list[float]) -> bool:
    """Shared by both PACE versions: today's c mass > mean + population SD of the previous
    five daily masses (strict)."""
    prev = np.asarray(prev_masses, float)
    return bool(mass_today > prev.mean() + prev.std(ddof=0))


# ── PACE as restated by Amendment 1 (primary) ────────────────────────────

def pav_increasing(y: np.ndarray, wts: np.ndarray) -> np.ndarray:
    """Weighted pool-adjacent-violators fit, non-decreasing in index."""
    blocks: list[list[float]] = []            # [weighted mean, weight, n members]
    for yi, wi in zip(np.asarray(y, float), np.asarray(wts, float)):
        blocks.append([yi, wi, 1])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            m2, w2, n2 = blocks.pop()
            m1, w1, n1 = blocks.pop()
            wt = w1 + w2
            blocks.append([(m1 * w1 + m2 * w2) / wt, wt, n1 + n2])
    out = []
    for m, _, n in blocks:
        out += [m] * n
    return np.array(out)


def pace_prior(n_buckets: int = N_BUCKETS) -> tuple[np.ndarray, np.ndarray]:
    """Amendment 1 step 1: surfaced = 2 (b + 1) / 10, not surfaced = 2 - 2 (b + 1) / 10."""
    b = np.arange(n_buckets)
    s = 2.0 * (b + 1) / n_buckets
    return s, 2.0 - s


class CarryLedger:
    """Amendment 1 step 2 as corrected by its erratum: a FIFO ledger consumed once. Each
    evaluation day j deposits max(0, base - calls_j); a deposit is live on days j + 1 ..
    j + w - 1 and then expires; calls above base draw down the oldest live deposits first;
    C_d = sum of the live, undrawn deposits (<= (w - 1) base by construction)."""

    def __init__(self, w: int):
        self.w = w
        self.deposits: list[list] = []          # [day, remaining amount], oldest first

    def expire(self, d: int) -> None:
        self.deposits = [x for x in self.deposits if x[0] >= d - (self.w - 1) and x[1] > 1e-12]

    def total(self, d: int) -> float:
        self.expire(d)
        return float(sum(x[1] for x in self.deposits))

    def draw(self, amount: float) -> float:
        """Draw up to `amount` from the oldest live deposits; returns the amount drawn."""
        got = 0.0
        for x in self.deposits:
            if got >= amount - 1e-12:
                break
            take = min(x[1], amount - got)
            x[1] -= take
            got += take
        self.deposits = [x for x in self.deposits if x[1] > 1e-12]
        return got

    def deposit(self, d: int, amount: float) -> None:
        if amount > 1e-12:
            self.deposits.append([d, float(amount)])


def pace_pool_add(pool: float, r: float, k: int, w: int) -> float:
    """Amendment 1 step 2: the reserve pool gains r k per evaluation day, capped at r k w."""
    return min(pool + r * k, r * k * w)


def pace_daily_cap(base: float, carry: float, pool: float, k: int, burst: bool) -> int:
    """Amendment 1 step 2: n_d = min(2k, floor(base + C_d [+ P_d on a burst day]))."""
    x = base + carry + (pool if burst else 0.0)
    return int(min(2 * k, max(0, math.floor(x + 1e-9))))


def pace_reserve_used(calls: int, base: float, carry: float, pool: float, burst: bool) -> float:
    """Reserve actually used on the day: the calls beyond base + C_d (only on burst days)."""
    if not burst:
        return 0.0
    return min(pool, max(0.0, calls - (base + carry)))


def pace_controller(y: float, so_far: float, plan: float, k: int, eta: float = ETA,
                    lo: float = Y_CLAMP[0], hi: float = Y_CLAMP[1]) -> float:
    """Amendment 1 step 3: dead band of k on both sides of the plan; clamp [0.05, 0.95]."""
    if so_far - plan > k:
        y = y * (1.0 + eta)
    elif plan - so_far > k:
        y = y * (1.0 - eta)
    return min(hi, max(lo, y))


def pace_call_set(order: np.ndarray, eligible_in_order: np.ndarray, n_d: int) -> np.ndarray:
    """Amendment 1 step 4: call the qualifying rows (Y >= y*) in rank order, at most n_d; if
    fewer than floor(n_d / 2) qualify, call the top floor(n_d / 2) by rank anyway."""
    elig = order[eligible_in_order][:n_d]
    floor_n = n_d // 2
    if len(elig) < floor_n:
        return order[:floor_n]
    return elig


def pace_total_bound(k: int, r: float, reserve_used: float) -> float:
    """Upper bound on amended PACE's deployed calls under the FIFO carry ledger. With base
    b = (1 - r) k, u_d = max(0, b - x_d) (the day's deposit) and o_d = max(0, x_d - b):
    x_d <= n_d <= b + C_d (+ P_d on a burst day), and o_d is paid by ledger draws D_d (carry
    first) and reserve R_d, so o_d = D_d + R_d. Each deposit is drawn at most once:
    sum D <= sum u. Total = 25 b + sum o - sum u <= 25 b + sum R <= 25 b + 25 r k = 25 k."""
    return len(EVAL_DAYS) * (1 - r) * k + reserve_used


class PacePolicy(Policy):
    """PACE as restated by Amendment 1 of TRACK-A.md (supersedes section 4's paragraph)."""
    family = "PACE"

    def __init__(self, w: int, r: float, eta: float = ETA):
        self.w, self.r, self.eta = w, r, eta
        self.params = (("w", w), ("r", r))
        self.s, self.f = pace_prior()
        self.y = Y_STAR0
        self.pool = 0.0
        self.ledger = CarryLedger(w)
        self.reserve_used_total = 0.0
        self.carry_drawn_total = 0.0
        self.trace: list = []
        self._pending = None

    def yields(self) -> np.ndarray:
        return pav_increasing(self.s / (self.s + self.f), self.s + self.f)

    def choose(self, day_rows, state):
        d, k, w, r = day_rows.d, state.k, self.w, self.r
        base = (1.0 - r) * k
        carry = min(self.ledger.total(d), (w - 1) * base)
        self.pool = pace_pool_add(self.pool, r, k, w)
        prev = [state.mass[x] for x in range(d - BURST_HISTORY, d)]
        burst = is_burst(state.mass[d], prev)
        n_d = pace_daily_cap(base, carry, self.pool, k, burst)
        so_far = state.calls_between(EVAL_DAYS[0], d - 1)
        plan = base * (d - 5)
        self.y = pace_controller(self.y, so_far, plan, k, self.eta)
        q = within_day_rank(day_rows.c)
        b = bucket_of(q)
        Yb = self.yields()[b]
        elig = Yb >= self.y
        o = order_desc(Yb, day_rows.c, day_rows.ids)
        sel = pace_call_set(o, elig[o], n_d)
        excess = max(0.0, len(sel) - base)
        drawn = self.ledger.draw(min(carry, excess))                 # carry first, FIFO
        used = pace_reserve_used(len(sel), base, carry, self.pool, burst)
        pool_before = self.pool
        self.pool -= used
        self.reserve_used_total += used
        self.carry_drawn_total += drawn
        self.ledger.deposit(d, max(0.0, base - len(sel)))
        self._pending = dict(zip((int(i) for i in day_rows.ids), b))
        self.trace.append({"d": d, "carry": carry, "pool": pool_before, "burst": burst,
                           "n_d": n_d, "y_star": self.y, "n_eligible": int(elig.sum()),
                           "floor_applied": bool(int(elig.sum()) < n_d // 2),
                           "calls": int(len(sel)), "carry_drawn": drawn,
                           "reserve_used": used})
        return {int(i) for i in day_rows.ids[sel]}

    def observe(self, day_rows, chosen, results, state):
        for i in chosen:
            b = self._pending[i]
            if results[i]:
                self.s[b] += 1
            else:
                self.f[b] += 1


# ── PACE v0: section 4 as originally written (post hoc comparison only, --pace-v0) ──

def pace_controller_v0(y: float, so_far: int, plan: float, k: int, eta: float = ETA) -> float:
    if so_far > plan:
        y = y * (1.0 + eta)
    elif plan - so_far > k:
        y = y * (1.0 - eta)
    return min(0.99, max(0.01, y))


def pace_spendable_v0(A: int, k: int, K: int, r: float, burst: bool) -> int:
    n = min(A, 2 * k) if burst else min(A - r * K, 2 * k)
    return int(max(0, math.floor(n + 1e-9)))


def pace_call_bound_v0(k: int, w: int, n_days: int = len(EVAL_DAYS)) -> int:
    """Upper bound on PACE v0's deployed calls over the evaluation days. Every window of w
    consecutive days spends at most K = k w: on the window's last day n_d <= A_d = K - (calls
    on the previous w - 1 days), and A_d >= 0 by induction (those w - 1 days lie inside the
    previous window, which spent <= K). Cut days 6..30 into floor(25 / w) full windows plus a
    remainder of m = 25 mod w days, each of which spends at most 2k:
    bound = k w floor(25 / w) + min(k w, 2 k m)  (= 26k for w = 3, 25k for w = 5)."""
    m = n_days % w
    return k * w * (n_days // w) + min(k * w, 2 * k * m)


class PacePolicyV0(Policy):
    """Section 4's original PACE (superseded by Amendment 1). Post hoc comparison row only."""
    family = "PACE-v0"

    def __init__(self, w: int, r: float, eta: float = ETA):
        self.w, self.r, self.eta = w, r, eta
        self.params = (("w", w), ("r", r))
        self.s = np.ones(N_BUCKETS)       # pseudo-count 1 surfaced
        self.f = np.ones(N_BUCKETS)       # pseudo-count 1 not surfaced
        self.y = Y_STAR0
        self.trace: list = []
        self._pending = None

    def yields(self) -> np.ndarray:
        return self.s / (self.s + self.f)

    def choose(self, day_rows, state):
        d, k = day_rows.d, state.k
        K = k * self.w
        A = K - state.calls_between(d - self.w + 1, d - 1)                     # step 1
        prev = [state.mass[x] for x in range(d - BURST_HISTORY, d)]
        burst = is_burst(state.mass[d], prev)                                   # step 2
        n_d = pace_spendable_v0(A, k, K, self.r, burst)                         # step 3
        so_far = state.calls_between(EVAL_DAYS[0], d - 1)                       # step 4
        plan = k * (d - 5)
        self.y = pace_controller_v0(self.y, so_far, plan, k, self.eta)
        q = within_day_rank(day_rows.c)                                         # step 5
        b = bucket_of(q)
        Yb = self.yields()[b]
        elig = Yb >= self.y
        o = order_desc(Yb, day_rows.c, day_rows.ids)
        o = o[elig[o]][:n_d]
        self._pending = dict(zip((int(i) for i in day_rows.ids), b))
        self.trace.append({"d": d, "A": int(A), "burst": burst, "n_d": n_d, "y_star": self.y,
                           "n_eligible": int(elig.sum()), "calls": int(len(o))})
        return {int(i) for i in day_rows.ids[o]}

    def observe(self, day_rows, chosen, results, state):
        for i in chosen:
            b = self._pending[i]
            if results[i]:
                self.s[b] += 1
            else:
                self.f[b] += 1


def np_threshold(c_cal_values: np.ndarray, k: int, n_days: int = len(CAL_DAYS)) -> float:
    v = np.sort(np.asarray(c_cal_values, float))[::-1]
    m = n_days * k
    return float(v[m]) if m < len(v) else float("-inf")


class NPPolicy(Policy):
    family = "NP"

    def __init__(self, tau: float):
        self.tau = tau

    def choose(self, day_rows, state):
        return {int(i) for i in day_rows.ids[day_rows.c > self.tau]}


class OraclePolicy(Policy):
    family = "ORACLE"

    def __init__(self, positive_ids):
        self.pos = set(int(i) for i in positive_ids)

    def choose(self, day_rows, state):
        isp = np.array([int(i) in self.pos for i in day_rows.ids], dtype=float)
        o = np.lexsort((day_rows.ids, -day_rows.c, -isp))
        return {int(i) for i in day_rows.ids[o[: state.k]]}


def policy_factories(w: World, k: int, sched: Schedule, seed: int, pace_v0: bool = False) -> list:
    """Fresh policy objects for one (k, regime) run, in report order. pace_v0 adds the
    superseded section-4 PACE (w = 3, r = 0.2) as a post hoc comparison row."""
    cal = w.c_cal[np.isin(w.day, CAL_DAYS)]
    out = [UniformPolicy(seed), SelectivePolicy()]
    out += [CredencePolicy(l) for l in C_LAMBDAS]
    out += [PacePolicy(wi, r) for wi in PACE_W for r in PACE_R]
    if pace_v0:
        out += [PacePolicyV0(3, 0.2)]
    out += [NPPolicy(np_threshold(cal, k)), OraclePolicy(sched.pos_ids)]
    return out


# ── simulation ───────────────────────────────────────────────────────────

def simulate(policy: Policy, w: World, sched: Schedule, k: int, surf: np.ndarray):
    state = SimState(k=k, mass=sched.mass)
    called = np.zeros(w.n, bool)
    for d in EVAL_DAYS:
        ids = sched.by_day[d]
        rows = DayRows(d=d, ids=ids, c=w.c[ids], acct=w.account[ids])
        chosen = policy.choose(rows, state)
        idset = set(int(i) for i in ids)
        if not chosen <= idset:
            raise AssertionError(f"{policy.key} chose ids not on day {d}")
        results = {i: bool(surf[i]) for i in chosen}
        policy.observe(rows, chosen, results, state)
        state.calls[d] = len(chosen)
        if chosen:
            called[list(chosen)] = True
    return called, dict(state.calls)


# ── bootstrap (section 5, R17) ───────────────────────────────────────────

def cluster_weights(n_accounts: int, B: int, seed: int) -> np.ndarray:
    """(B x n_accounts) counts: each replicate draws n_accounts accounts with replacement;
    an account's positives always enter together with its weight."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_accounts, size=(B, n_accounts))
    W = np.zeros((B, n_accounts), dtype=np.int32)
    for b in range(B):
        W[b] = np.bincount(idx[b], minlength=n_accounts)
    return W


def per_account(acc_idx: np.ndarray, ids: np.ndarray, weights: np.ndarray, A: int) -> np.ndarray:
    return np.bincount(acc_idx[ids], weights=weights.astype(float), minlength=A)


def boot_ratio(W: np.ndarray, num: np.ndarray, den: np.ndarray) -> np.ndarray:
    d = W @ den
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(d > 0, (W @ num) / np.where(d > 0, d, 1), np.nan)


def ci(x: np.ndarray) -> list:
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return [None, None]
    lo, hi = np.percentile(x, [2.5, 97.5])
    return [float(lo), float(hi)]


def est(num: np.ndarray, den: np.ndarray, W: np.ndarray) -> dict:
    tot = den.sum()
    pt = float(num.sum() / tot) if tot > 0 else float("nan")
    return {"pt": pt, "ci": ci(boot_ratio(W, num, den))}


# ── metrics for one cell ─────────────────────────────────────────────────

def cell_metrics(w: World, sched: Schedule, called: np.ndarray, surf: np.ndarray, W: np.ndarray,
                 attempted: bool = False) -> dict:
    A = len(w.labelled_accounts)
    pos = sched.pos_ids
    npos = per_account(w.acc_idx, pos, np.ones(len(pos)), A)
    alloc = per_account(w.acc_idx, pos, called[pos], A)
    det = per_account(w.acc_idx, pos, called[pos] & surf[pos], A)
    hon = np.where(w.honest)[0]
    out = {"n_pos": int(len(pos)), "_npos": npos, "_alloc": alloc, "_det": det,
           "alloc": est(alloc, npos, W), "det": est(det, npos, W),
           "honest_flag_rate": float((called[hon] & surf[hon]).mean()) if len(hon) else float("nan"),
           "n_honest": int(len(hon)), "calls": int(called.sum())}
    if attempted:
        at = sched.att_ids
        na = per_account(w.acc_idx, at, np.ones(len(at)), A)
        out["attempted"] = {"n_pos": int(len(at)),
                            "alloc": est(per_account(w.acc_idx, at, called[at], A), na, W),
                            "det": est(per_account(w.acc_idx, at, called[at] & surf[at], A), na, W)}
    return out


def diff_est(a: dict, b: dict, key: str, W: np.ndarray) -> dict:
    num = a["_" + key] - b["_" + key]
    return est(num, a["_npos"], W)


# ── expensive-tier quality and K2 (sections 5, 7) ────────────────────────

def expensive_quality(w: World, W: np.ndarray, surf_defs: dict) -> dict:
    A = len(w.labelled_accounts)
    pos = np.where(w.is_exec)[0]
    hon = np.where(w.honest)[0]
    npos = per_account(w.acc_idx, pos, np.ones(len(pos)), A)
    out = {"n_pos": int(len(pos)), "n_honest": int(len(hon))}

    def au(vals, name):
        neg = np.sort(vals[hon][np.isfinite(vals[hon])])
        pmask = np.isfinite(vals[pos])
        wf = np.zeros(len(pos))
        wf[pmask] = win_fractions(vals[pos][pmask], neg)
        npm = per_account(w.acc_idx, pos, pmask.astype(float), A)
        num = per_account(w.acc_idx, pos, wf, A)
        out[name] = {"pt": float(num.sum() / npm.sum()) if npm.sum() else float("nan"),
                     "ci": ci(boot_ratio(W, num, npm)), "n_pos": int(pmask.sum()),
                     "n_neg": int(len(neg))}
        return num, npm

    e100 = e_for_auroc(w.outcome, w.score, 100.0, 0.0)
    e0 = e_for_auroc(w.outcome, w.score, 0.0, 0.0)
    eex = e_for_auroc(w.outcome, w.score, 100.0, None)
    ne, de = au(e100, "auroc_e")
    au(e0, "auroc_e_refused_as_0")
    au(eex, "auroc_e_errored_excluded")
    nc, dc = au(w.c.astype(float), "auroc_c")
    # difference e - c on the same positives (de == dc here: errored are 0, not excluded)
    out["auroc_diff_e_minus_c"] = {"pt": out["auroc_e"]["pt"] - out["auroc_c"]["pt"],
                                   "ci": ci(boot_ratio(W, ne, de) - boot_ratio(W, nc, dc))}
    out["full_coverage_detection_recall"] = {}
    for name, s in surf_defs.items():
        out["full_coverage_detection_recall"][name] = est(per_account(w.acc_idx, pos, s[pos], A), npos, W)
        out.setdefault("full_coverage_honest_flag_rate", {})[name] = float(s[hon].mean()) if len(hon) else None
    ev = w.eval_mask
    out["outcomes_eval"] = {k: int(((w.outcome == k) & ev).sum())
                            for k in ("scored", "refused", "errored", "missing")}
    return out


def k2_verdict(q: dict) -> dict:
    e, c = q["auroc_e"]["pt"], q["auroc_c"]["pt"]
    passed = bool(e > c)
    if passed:
        text = (f"K2 not triggered: the expensive tier at full coverage beats the cheap tier on "
                f"AUROC (executed positives vs never-labelled account-days, days 6-30): "
                f"e {e:.4f} > c {c:.4f}. Pacing results are read as planned.")
    else:
        text = (f"K2 TRIGGERED: the expensive tier at full coverage does not beat the cheap tier on "
                f"AUROC (e {e:.4f} <= c {c:.4f}). Pacing is a null result on this corpus and is "
                f"reported as one; the regime grid below is run for completeness; the second corpus "
                f"(kimi_k26_single_day) is recommended at Checkpoint 2.")
    return {"auroc_e": e, "auroc_c": c, "expensive_beats_cheap": passed, "triggered": not passed,
            "text": text}


# ── labels for rows (R19) ────────────────────────────────────────────────

def row_label(policy_key: str, k: int, regime: str, surf_def: str) -> str:
    if policy_key.startswith("PACE-v0"):
        return "exploratory (post hoc)"
    if surf_def != "theta50":
        return "exploratory"
    if k == PRIMARY_K and regime == "rate100/original" and policy_key in ("S", primary_pace_key()):
        return "primary"
    return "secondary"


def primary_pace_key() -> str:
    return "PACE(w=3, r=0.2)"


# ── driver ───────────────────────────────────────────────────────────────

def run(cheap_path: Path, exp_path: Path, labels_path: Path, out_md: Path, out_json: Path,
        fig_path: Path, B: int = 1000, seed: int = SEED, allow_incomplete: bool = False,
        crosscheck_cheap_labels: bool = True, pace_v0: bool = False) -> dict:
    t0 = time.time()
    cheap = load_cheap(cheap_path)
    exp, exp_meta = load_expensive(exp_path, allow_incomplete)
    units = list(zip(cheap["account"], cheap["date"]))
    labels = read_labels(labels_path, units, cheap_path if crosscheck_cheap_labels else None)
    w = build_world(cheap, exp, labels, exp_meta, allow_incomplete)
    W = cluster_weights(len(w.labelled_accounts), B, seed)
    hon_mask = w.honest
    th95 = theta95(w.outcome, w.score, hon_mask, w.day)
    surf = {"theta50": surfaced_vector(w.outcome, w.score, THETA, False),
            "refusal_as_zero": surfaced_vector(w.outcome, w.score, THETA, True),
            "theta95": surfaced_vector(w.outcome, w.score, th95, False)}
    quality = expensive_quality(w, W, surf)
    k2 = k2_verdict(quality)

    schedules = {}
    for rate in RATES:
        for pl in PLACEMENTS:
            s = make_schedule(w, rate, pl, seed)
            schedules[s.name] = s

    cells: list[dict] = []
    raw: dict = {}                 # (surf, regime, k, key) -> metrics with per-account arrays
    traces: dict = {}
    cal_mask = np.isin(w.day, CAL_DAYS)
    np_info = {}
    for k in KS:
        tau = np_threshold(w.c_cal[cal_mask], k)
        np_info[k] = {"tau": tau, "cal_mean_calls_per_day": float((w.c_cal[cal_mask] > tau).sum() / len(CAL_DAYS))}
    plan = [("theta50", name) for name in schedules] + \
           [(sd, "rate100/original") for sd in SURF_DEFS if sd != "theta50"]
    for sd, rname in plan:
        sched = schedules[rname]
        for k in KS:
            v0_here = pace_v0 and sd == "theta50" and rname == "rate100/original"
            for pol in policy_factories(w, k, sched, seed, pace_v0=v0_here):
                called, calls_by_day = simulate(pol, w, sched, k, surf[sd])
                m = cell_metrics(w, sched, called, surf[sd], W,
                                 attempted=(rname == "rate100/original" and sd == "theta50"))
                m.update({"policy": pol.family, "key": pol.key, "params": dict(pol.params), "k": k,
                          "regime": rname, "surf": sd, "calls_by_day": calls_by_day,
                          "dollars": m["calls"] * w.mean_cost,
                          "label": row_label(pol.key, k, rname, sd)})
                if pol.family == "NP":
                    m["np"] = np_info[k]
                if pol.family == "PACE":
                    m["pace_bound"] = pace_total_bound(k, pol.r, pol.reserve_used_total)
                    m["pace_max_day"] = max(calls_by_day.values()) if calls_by_day else 0
                    m["pace_reserve_used"] = pol.reserve_used_total
                    if pol.key == primary_pace_key() and k == PRIMARY_K and rname == "rate100/original":
                        traces[sd] = pol.trace
                if pol.family == "PACE-v0":
                    m["pace_bound"] = pace_call_bound_v0(k, pol.w)
                    if k == PRIMARY_K:
                        traces["v0_theta50"] = pol.trace
                raw[(sd, rname, k, pol.key)] = m
    # differences vs S and vs primary PACE, budget-AUC
    for (sd, rname, k, key), m in raw.items():
        s = raw[(sd, rname, k, "S")]
        p = raw[(sd, rname, k, primary_pace_key())]
        m["d_det_vs_S"] = diff_est(m, s, "det", W)
        m["d_alloc_vs_S"] = diff_est(m, s, "alloc", W)
        m["d_det_vs_PACE_primary"] = diff_est(m, p, "det", W)
    bauc = {}
    keys_seen = sorted({(sd, rn, key) for (sd, rn, k, key) in raw})
    for sd, rn, key in keys_seen:
        rec_pt = [raw[(sd, rn, k, key)]["det"]["pt"] for k in KS]
        rec_b = np.stack([boot_ratio(W, raw[(sd, rn, k, key)]["_det"], raw[(sd, rn, k, key)]["_npos"])
                          for k in KS], axis=1)
        s_b = np.stack([boot_ratio(W, raw[(sd, rn, k, "S")]["_det"], raw[(sd, rn, k, "S")]["_npos"])
                        for k in KS], axis=1)
        pt = float(np.trapezoid(rec_pt, KS) / 18.0)
        bt = np.trapezoid(rec_b, KS, axis=1) / 18.0
        s_pt = float(np.trapezoid([raw[(sd, rn, k, "S")]["det"]["pt"] for k in KS], KS) / 18.0)
        sb = np.trapezoid(s_b, KS, axis=1) / 18.0
        bauc[(sd, rn, key)] = {"pt": pt, "ci": ci(bt), "d_vs_S": {"pt": pt - s_pt, "ci": ci(bt - sb)}}

    prim_p = raw[("theta50", "rate100/original", PRIMARY_K, primary_pace_key())]
    prim_s = raw[("theta50", "rate100/original", PRIMARY_K, "S")]
    primary = {"comparison": "PACE(w=3, r=0.2) vs S, k = 10, original schedule, detection recall, "
                             "theta = 50",
               "PACE": prim_p["det"], "S": prim_s["det"], "diff_PACE_minus_S": prim_p["d_det_vs_S"],
               "PACE_calls": prim_p["calls"], "S_calls": prim_s["calls"], "n_pos": prim_p["n_pos"]}
    l1 = {"recall": est(per_account(w.acc_idx, np.where(w.is_exec)[0], w.l1[w.is_exec],
                                    len(w.labelled_accounts)),
                        per_account(w.acc_idx, np.where(w.is_exec)[0], np.ones(int(w.is_exec.sum())),
                                    len(w.labelled_accounts)), W),
          "honest_flag_rate": float(w.l1[w.honest].mean()) if w.honest.any() else None}
    runtime = time.time() - t0
    res = {
        "inputs": {"cheap": str(cheap_path), "cheap_sha256": sha256_file(cheap_path),
                   "expensive": str(exp_path), "expensive_sha256": sha256_file(exp_path),
                   "expensive_meta_complete": exp_meta.get("complete"),
                   "expensive_models": sorted(set(map(str, exp.get("model", pd.Series(dtype=str)).dropna()))),
                   "labels": str(labels_path), "labels_sha256": sha256_file(labels_path),
                   "allow_incomplete": allow_incomplete},
        "config": {"B": B, "seed": seed, "theta": THETA, "theta95": th95, "ks": list(KS),
                   "eta": ETA, "C_lambdas": list(C_LAMBDAS), "PACE_w": list(PACE_W),
                   "PACE_r": list(PACE_R), "PACE_version": "Amendment 1 (TRACK-A.md)",
                   "y_star_clamp": list(Y_CLAMP), "pace_v0_row": pace_v0,
                   "mean_cost_per_call_usd": w.mean_cost},
        "data": {"n_account_days": w.n, "n_eval_account_days": int(w.eval_mask.sum()),
                 "n_accounts": int(len(set(w.account))),
                 "n_labelled_accounts": len(w.labelled_accounts),
                 "n_exec_pos_eval": int(w.is_exec.sum()), "n_att_pos_eval": int(w.is_att.sum()),
                 "n_honest_eval": int(w.honest.sum()), "labels_info": labels["info"],
                 "n_missing_expensive": w.meta["n_missing_expensive"]},
        "primary": primary, "k2": k2, "expensive_quality": quality, "layer1": l1,
        "np_calibration": {str(k): v for k, v in np_info.items()},
        "pace_primary_trace": traces,
        "regimes": {n: {"n_pos": int(len(s.pos_ids)), "rate": s.rate, "placement": s.placement,
                        "pos_per_day": {str(d): int((s.sim_day[s.pos_ids] == d).sum()) for d in EVAL_DAYS}}
                    for n, s in schedules.items()},
        "adversarial_days": adversarial_days({d: float(w.c[w.honest & (w.day == d)].sum()) for d in EVAL_DAYS}),
        "cells": [{k_: v for k_, v in m.items() if not k_.startswith("_")} for m in raw.values()],
        "budget_auc": [{"surf": sd, "regime": rn, "key": key, **v} for (sd, rn, key), v in bauc.items()],
        "resolutions": RESOLUTIONS,
        "script": str(HERE), "script_sha256": sha256_file(HERE),
        "runtime_s": round(runtime, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    out_json = Path(out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(res, indent=1, default=_json_default), encoding="utf-8")
    write_markdown(res, raw, bauc, Path(out_md))
    draw_figure(raw, schedules, Path(fig_path))
    res["_raw"] = raw
    res["_schedules"] = schedules
    res["_world"] = w
    return res


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# ── markdown ─────────────────────────────────────────────────────────────

def f3(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and not math.isfinite(x)) else f"{x:.3f}"


def fe(e: dict) -> str:
    lo, hi = e["ci"]
    return f"{f3(e['pt'])} [{f3(lo)}, {f3(hi)}]"


def fd(e: dict) -> str:
    lo, hi = e["ci"]
    sg = lambda x: "n/a" if x is None or not math.isfinite(x) else f"{x:+.3f}"
    return f"{sg(e['pt'])} [{sg(lo)}, {sg(hi)}]"


def policy_order(raw, sd, rn, k) -> list[str]:
    return [key for (s, r, kk, key) in raw if s == sd and r == rn and kk == k]


def write_markdown(res: dict, raw: dict, bauc: dict, path: Path) -> None:
    P, K2, Q, D = res["primary"], res["k2"], res["expensive_quality"], res["data"]
    L = []
    a = L.append
    a("# Track A results: budget-paced escalation (`escalation_sim.py`)\n")
    a(f"Pre-registration: `work/mole-fork/protocol/TRACK-A.md`. Generated {res['timestamp']} by "
      f"`work/checks/escalation_sim.py` (sha256 `{res['script_sha256'][:12]}`), B = "
      f"{res['config']['B']} cluster-bootstrap resamples over {D['n_labelled_accounts']} labelled "
      f"accounts, seed {res['config']['seed']}. Intervals are 95 percent percentile intervals.\n")
    a(f"Inputs: cheap `{res['inputs']['cheap']}`; expensive `{res['inputs']['expensive']}` (meta "
      f"complete = {res['inputs']['expensive_meta_complete']}, models {res['inputs']['expensive_models']}, "
      f"{D['n_missing_expensive']} evaluation account-days without a record); labels "
      f"`{res['inputs']['labels']}`.\n")
    a(f"Evaluation days 6-30: {D['n_eval_account_days']} account-days, {D['n_exec_pos_eval']} executed "
      f"positives, {D['n_att_pos_eval']} attempted positives, {D['n_honest_eval']} never-labelled "
      f"account-days. Mean cost per call ${res['config']['mean_cost_per_call_usd']:.4f}.\n")

    a("## 1. Primary comparison (pre-registered, section 7)\n")
    a(f"Table 1. {CAPTION}\n")
    a("| label | quantity | value [95% CI] |")
    a("|---|---|---|")
    a(f"| primary | PACE(w=3, r=0.2) detection recall, k = 10, original | {fe(P['PACE'])} |")
    a(f"| primary | S detection recall, k = 10, original | {fe(P['S'])} |")
    a(f"| primary | **difference PACE - S** | **{fd(P['diff_PACE_minus_S'])}** |")
    a(f"| secondary | deployed calls PACE / S (budget 25 k = {25 * PRIMARY_K}) | {P['PACE_calls']} / {P['S_calls']} |")
    a(f"| secondary | executed positives on days 6-30 | {P['n_pos']} |")
    a("")
    a("### K2 (expensive tier vs cheap tier, full coverage)\n")
    a(f"Table 2. {CAPTION}\n")
    a("| label | quantity | value [95% CI] |")
    a("|---|---|---|")
    a(f"| secondary | AUROC of e (refused = 100, errored = 0) | {fe(Q['auroc_e'])} |")
    a(f"| secondary | AUROC of c (c_z) | {fe(Q['auroc_c'])} |")
    a(f"| secondary | AUROC difference e - c | {fd(Q['auroc_diff_e_minus_c'])} |")
    a(f"| exploratory | AUROC of e, refused = 0 | {fe(Q['auroc_e_refused_as_0'])} |")
    a(f"| exploratory | AUROC of e, errored excluded | {fe(Q['auroc_e_errored_excluded'])} |")
    fc = Q["full_coverage_detection_recall"]
    a(f"| secondary | expensive full-coverage detection recall (theta = 50) | {fe(fc['theta50'])} |")
    a(f"| exploratory | ... refusal-as-zero | {fe(fc['refusal_as_zero'])} |")
    a(f"| exploratory | ... theta95 = {res['config']['theta95']:.2f} | {fe(fc['theta95'])} |")
    hf = Q["full_coverage_honest_flag_rate"]
    a(f"| secondary | expensive full-coverage honest flag rate (theta = 50) | {f3(hf['theta50'])} |")
    a(f"| secondary | evaluation-day outcomes | {Q['outcomes_eval']} |")
    a("")
    a(f"**{K2['text']}**\n")

    a("## 2. Per-budget tables (original schedule, theta = 50)\n")
    a("Allocation recall = share of executed positives called; detection recall = share called and "
      "surfaced (e >= 50 or refused); honest flag rate = share of never-labelled account-days surfaced; "
      "deployed calls over days 6-30 (budget 25 k); dollars = calls x mean cost per call. "
      "Delta = detection recall minus S's, paired cluster bootstrap. S's allocation recall is the "
      "cheap tier's recall at k (baseline row). The L1 row is the layer-1 non-noisy structural "
      "matcher flag: upstream's own labelling matchers, written knowing the threats, a ceiling for "
      "layer 1 and never a protocol-compliant rule set; it makes no judge calls. PACE is the policy "
      "as restated by Amendment 1 of TRACK-A.md. A `PACE-v0` row, if present, is section 4's "
      "superseded PACE, run post hoc for comparison only (`--pace-v0`): it is not a pre-registered "
      "policy, is excluded from the figure and from every comparison.\n")
    tn = 3
    for k in KS:
        a(f"### k = {k}\n")
        a(f"Table {tn}. {CAPTION}\n")
        tn += 1
        a("| label | policy | alloc. recall | det. recall | delta det. vs S | honest flag | calls | dollars |")
        a("|---|---|---|---|---|---|---|---|")
        for key in policy_order(raw, "theta50", "rate100/original", k):
            m = raw[("theta50", "rate100/original", k, key)]
            extra = ""
            if m["policy"] == "PACE-v0":
                extra = f" (bound {m['pace_bound']})"
            if m["policy"] == "PACE":
                extra = f" (max {m['pace_max_day']}/day)"
            if m["policy"] == "NP":
                extra = f" (tau {m['np']['tau']:.3f})"
            a(f"| {m['label']} | {key} | {fe(m['alloc'])} | {fe(m['det'])} | {fd(m['d_det_vs_S'])} | "
              f"{f3(m['honest_flag_rate'])} | {m['calls']}{extra} | {m['dollars']:.2f} |")
        l1 = res["layer1"]
        a(f"| exploratory | L1 non-noisy (ceiling) | n/a | {fe(l1['recall'])} (flag recall) | n/a | "
          f"{f3(l1['honest_flag_rate'])} (flag rate) | 0 | 0.00 |")
        a("")

    a("### Budget-AUC (detection recall over k, trapezoid / 18, original schedule)\n")
    a(f"Table {tn}. {CAPTION}\n")
    tn += 1
    a("| label | policy | budget-AUC | delta vs S |")
    a("|---|---|---|---|")
    for key in policy_order(raw, "theta50", "rate100/original", PRIMARY_K):
        b = bauc[("theta50", "rate100/original", key)]
        lab = "exploratory (post hoc)" if key.startswith("PACE-v0") else "secondary"
        a(f"| {lab} | {key} | {fe(b)} | {fd(b['d_vs_S'])} |")
    a("")

    a("### Attempted positives (secondary positive set, k = 10, original)\n")
    a(f"Table {tn}. {CAPTION}\n")
    tn += 1
    a("| label | policy | n | alloc. recall | det. recall |")
    a("|---|---|---|---|---|")
    for key in policy_order(raw, "theta50", "rate100/original", PRIMARY_K):
        at = raw[("theta50", "rate100/original", PRIMARY_K, key)]["attempted"]
        a(f"| exploratory{' (post hoc)' if key.startswith('PACE-v0') else ''} | {key} | {at['n_pos']} | {fe(at['alloc'])} | {fe(at['det'])} |")
    a("")

    a("## 3. Regime grid at k = 10 (theta = 50)\n")
    a("Cells: detection recall [95% CI] / allocation recall / deployed calls. Rate subsamples the "
      "executed positives; placement re-times the kept ones (burst5: 5 random evaluation days; "
      "uniform: spread over 25 days; adversarial: the 5 days of highest never-labelled c mass, "
      f"days {res['adversarial_days']}). C's and PACE's multi-day context is broken by re-timing; "
      "the original schedule is C's only headline.\n")
    for rate in RATES:
        a(f"### rate {int(rate * 100)} percent\n")
        a(f"Table {tn}. {CAPTION}\n")
        tn += 1
        names = [f"rate{int(round(rate * 100))}/{pl}" for pl in PLACEMENTS]
        a("| label | policy | " + " | ".join(f"{pl} (n = {res['regimes'][n]['n_pos']})"
                                           for pl, n in zip(PLACEMENTS, names)) + " |")
        a("|---|---|" + "---|" * len(names))
        for key in policy_order(raw, "theta50", names[0], PRIMARY_K):
            if key.startswith("PACE-v0"):
                continue
            cells = []
            lab = "secondary"
            for n in names:
                m = raw[("theta50", n, PRIMARY_K, key)]
                if m["label"] == "primary":
                    lab = "primary (original col.) / secondary"
                cells.append(f"{fe(m['det'])} / {f3(m['alloc']['pt'])} / {m['calls']}")
            a(f"| {lab} | {key} | " + " | ".join(cells) + " |")
        a("")

    a("## 4. Sensitivities (original schedule, every policy re-run)\n")
    for sd, title in (("refusal_as_zero", "refusal counted as not surfaced (refusal-as-zero)"),
                      ("theta95", f"theta = {res['config']['theta95']:.2f}, the 95th percentile of e "
                                  f"over never-labelled account-days of days 6-10")):
        a(f"### {title}\n")
        a(f"Table {tn}. {CAPTION}\n")
        tn += 1
        a("| label | policy | det. recall k = 10 | delta vs S | honest flag | calls | budget-AUC |")
        a("|---|---|---|---|---|---|---|")
        for key in policy_order(raw, sd, "rate100/original", PRIMARY_K):
            m = raw[(sd, "rate100/original", PRIMARY_K, key)]
            b = bauc[(sd, "rate100/original", key)]
            a(f"| exploratory | {key} | {fe(m['det'])} | {fd(m['d_det_vs_S'])} | "
              f"{f3(m['honest_flag_rate'])} | {m['calls']} | {fe(b)} |")
        a("")
    a("## 5. NP calibration\n")
    a(f"Table {tn}. {CAPTION}\n")
    tn += 1
    a("| k | tau (c_z_cal) | calibration mean calls/day | evaluation calls (25 days) |")
    a("|---|---|---|---|")
    for k in KS:
        npi = res["np_calibration"][str(k)]
        m = raw[("theta50", "rate100/original", k, "NP")]
        a(f"| {k} | {npi['tau']:.4f} | {npi['cal_mean_calls_per_day']:.2f} | {m['calls']} |")
    a("")
    a("## 6. Resolutions of ambiguities in the pre-registration (to be recorded as errata)\n")
    for r in res["resolutions"]:
        a(f"- {r}")
    a("")
    a(f"Runtime {res['runtime_s']:.1f} s.\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L), encoding="utf-8")


# ── figure (section 8) ───────────────────────────────────────────────────

# Okabe-Ito (colour-blind safe), fixed order per policy family
POLICY_COLOURS = {"U": "#E69F00", "S": "#56B4E9", "C": "#009E73", "PACE": "#0072B2",
                  "NP": "#D55E00", "tie": "#BBBBBB"}


def regime_winner(raw: dict, regime: str, metric: str, k: int = PRIMARY_K):
    best, fams, keys = -1.0, set(), []
    for (sd, rn, kk, key), m in raw.items():
        if sd != "theta50" or rn != regime or kk != k or m["policy"] not in DEPLOYABLE:
            continue
        v = m[metric]["pt"]
        if not math.isfinite(v):
            continue
        if v > best + 1e-12:
            best, fams, keys = v, {m["policy"]}, [key]
        elif abs(v - best) <= 1e-12:
            fams.add(m["policy"])
            keys.append(key)
    fam = next(iter(fams)) if len(fams) == 1 else "tie"
    return fam, keys, best


def draw_figure(raw: dict, schedules: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle
    rates = list(RATES)
    fig, axes = plt.subplots(1, 3, figsize=(17, 5.2), constrained_layout=True)
    titles = ["Winner by detection recall (k = 10)", "Winner by allocation recall (k = 10)",
              "Deployed calls of the detection winner (k = 10)"]
    for pi_, ax in enumerate(axes):
        ax.set_xlim(0, len(PLACEMENTS))
        ax.set_ylim(0, len(rates))
        ax.invert_yaxis()
        for i, rate in enumerate(rates):
            for j, pl in enumerate(PLACEMENTS):
                rn = f"rate{int(round(rate * 100))}/{pl}"
                fam, keys, val = regime_winner(raw, rn, "alloc" if pi_ == 1 else "det")
                if pi_ == 2:
                    m = [raw[("theta50", rn, PRIMARY_K, kk)] for kk in keys]
                    calls = "/".join(str(x["calls"]) for x in m[:2])
                    who = keys[0] if len(keys) == 1 else (f"{fam} ({len(keys)} cells tie)" if fam != "tie" else "tie")
                    txt = f"{who}\n{calls} calls\n" \
                          f"({m[0]['calls'] / (25 * PRIMARY_K):.2f} x 25k)"
                else:
                    if len(keys) == 1:
                        nm = keys[0]
                    elif fam != "tie":
                        nm = f"{fam} ({len(keys)} cells tie)"
                    else:
                        nm = "tie: " + ", ".join(sorted({k_.split('(')[0] for k_ in keys}))
                    txt = f"{nm}\n{val:.3f}"
                ax.add_patch(Rectangle((j + 0.03, i + 0.03), 0.94, 0.94,
                                       facecolor=POLICY_COLOURS[fam], edgecolor="white", lw=2,
                                       hatch="//" if fam == "tie" else None))
                light = fam in ("U", "S", "tie")
                ax.text(j + 0.5, i + 0.5, txt, ha="center", va="center", fontsize=7.5,
                        color="black" if light else "white")
        ax.axvline(3, color="black", lw=2.5)
        ax.set_xticks([x + 0.5 for x in range(len(PLACEMENTS))])
        ax.set_xticklabels(["original", "burst (5 days)", "uniform", "ADVERSARIAL\n(top honest c)"],
                           fontsize=8)
        ax.set_yticks([y + 0.5 for y in range(len(rates))])
        ax.set_yticklabels([f"rate {int(r * 100)}%" for r in rates], fontsize=8)
        ax.set_title(titles[pi_], fontsize=10)
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
    handles = [Patch(facecolor=POLICY_COLOURS[f], label=lab) for f, lab in
               (("U", "U uniform"), ("S", "S selective (top-k by c)"), ("C", "C per-account credence"),
                ("PACE", "PACE pacing"), ("NP", "NP static threshold"))]
    handles.append(Patch(facecolor=POLICY_COLOURS["tie"], hatch="//", label="tie"))
    fig.legend(handles=handles, loc="outside lower center", ncol=6, fontsize=8, frameon=False)
    fig.suptitle("Track A phase diagram: rate x burstiness, adversarial placement marked "
                 "(ORACLE excluded)", fontsize=11)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


# ── synthetic world and self-test ────────────────────────────────────────

def weekdays(start: date, n: int) -> list[str]:
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def make_synthetic(outdir: Path, seed: int = 1, n_accounts: int = 150, n_days: int = 30,
                   n_labelled: int = 38) -> dict:
    """Synthetic cheap / expensive (+ meta) / labels files shaped like the real ones. Honest c
    ~ 0.1 + Gamma(3, 0.17) (real c_z: mean 0.63, sd 0.32); positives' c moderately high
    (0.1 + Gamma(6, 0.17)); e honest ~ 100 Beta(1.2, 8), executed ~ 100 Beta(6, 2.5)."""
    rng = np.random.default_rng(seed)
    outdir.mkdir(parents=True, exist_ok=True)
    dates = weekdays(date(2026, 4, 6), n_days)
    accts = [f"user{i:03d}@synthetic.test" for i in range(n_accounts)]
    active = rng.random((n_accounts, n_days)) < 0.982
    labelled = sorted(rng.choice(n_accounts, size=n_labelled, replace=False).tolist())
    executed, attempted = set(), set()
    for a in labelled:
        days_a = np.where(active[a])[0]
        n_ex = min(len(days_a), 1 + rng.poisson(4.0))
        centre = rng.uniform(0, n_days - 1)
        wts = np.exp(-np.abs(days_a - centre) / 3.0)
        pick = rng.choice(days_a, size=n_ex, replace=False, p=wts / wts.sum())
        executed |= {(a, int(d)) for d in pick}
    lab_days = [(a, int(d)) for a in labelled for d in np.where(active[a])[0] if (a, int(d)) not in executed]
    for j in rng.choice(len(lab_days), size=19, replace=False):
        attempted.add(lab_days[j])
    rows, erows, lrows = [], [], []
    for a in range(n_accounts):
        for di in range(n_days):
            if not active[a, di]:
                continue
            d = di + 1
            isx, isa = (a, di) in executed, (a, di) in attempted
            if isx:
                c = 0.1 + rng.gamma(6.0, 0.17)
                e = 100 * rng.beta(6, 2.5)
                p_ref, l1 = 0.03, rng.random() < 0.4
            elif isa:
                c = 0.1 + rng.gamma(4.5, 0.17)
                e = 100 * rng.beta(3, 3)
                p_ref, l1 = 0.02, rng.random() < 0.2
            else:
                c = 0.1 + rng.gamma(3.0, 0.17)
                e = 100 * rng.beta(1.2, 8)
                p_ref, l1 = 0.003, rng.random() < 0.01
            ev = d >= 6
            rows.append({"account": accts[a], "date": dates[di], "day_index": d, "is_eval_day": ev,
                         "n_events": int(rng.integers(5, 400)), "n_ok_events": 0,
                         "c_z": c if ev else np.nan, "c_z_cal": np.nan if ev else c,
                         "l1_any": l1, "l1_nonnoisy": l1, "l1_variants": "",
                         "is_positive_executed": isx, "is_positive_attempted": isa,
                         "scenario": "synthetic" if (isx or isa) else None,
                         "labelled_account": a in labelled})
            if isx or isa:
                lrows.append({"account": accts[a], "date": dates[di], "scenario": "synthetic",
                              "outcome": "executed" if isx else "attempted"})
            if ev:
                u = rng.random()
                if u < p_ref:
                    oc, sc = "refused", np.nan
                elif u < p_ref + 0.01:
                    oc, sc = "errored", np.nan
                else:
                    oc, sc = "scored", float(int(round(e)))
                erows.append({"account": accts[a], "date": dates[di], "day_index": d, "outcome": oc,
                              "score": sc, "cost_usd": float(max(0.01, rng.normal(0.053, 0.01))),
                              "model": "synthetic"})
    # labelled accounts with no positive at all would not be labelled; ensure every labelled
    # account has a label row (true by construction: n_ex >= 1)
    cheap = pd.DataFrame(rows)
    exp = pd.DataFrame(erows)
    labs = pd.DataFrame(lrows)
    p = {"cheap": outdir / "synthetic.cheap.parquet", "expensive": outdir / "synthetic.expensive.parquet",
         "labels": outdir / "synthetic.labels.parquet"}
    cheap.to_parquet(p["cheap"], index=False)
    exp.to_parquet(p["expensive"], index=False)
    labs.to_parquet(p["labels"], index=False)
    meta = {"corpus": "synthetic", "complete": True, "model": "synthetic",
            "summary": {"n": len(exp), "mean_cost_usd": float(exp["cost_usd"].mean())},
            "n_rows": len(exp)}
    sibling(p["expensive"], ".meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    p["n_rows"] = len(cheap)
    p["n_exec"] = len(executed)
    return p


def selftest(outdir: Path, B: int = 1000, seed: int = SEED, pace_v0: bool = False) -> int:
    t0 = time.time()
    files = make_synthetic(outdir, seed=1)
    print(f"synthetic world: {files['n_rows']} account-days, {files['n_exec']} executed positives "
          f"(all days) -> {outdir}")
    res = run(files["cheap"], files["expensive"], files["labels"], outdir / "a-track-a-results.md",
              outdir / "a-track-a-results.json", outdir / "fig-phase-diagram.png", B=B, seed=seed,
              pace_v0=pace_v0)
    raw, scheds, w = res["_raw"], res["_schedules"], res["_world"]
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, bool(ok), detail))

    info = []
    for (sd, rn, k, key), m in raw.items():
        orc = raw[(sd, rn, k, "ORACLE")]["alloc"]["pt"]
        ok = orc >= m["alloc"]["pt"] - 1e-12
        if m["policy"] in ("U", "S", "C"):          # policies spending <= k per day (R13)
            check(f"ORACLE >= {key} alloc [{sd} {rn} k={k}]", ok, f"{orc:.3f} vs {m['alloc']['pt']:.3f}")
        elif not ok:
            info.append(f"{key} exceeds ORACLE on allocation recall [{sd} {rn} k={k}]: "
                        f"{m['alloc']['pt']:.3f} > {orc:.3f} (allowed: spends > k on some days)")
    for (sd, rn, k, key), m in raw.items():
        if m["policy"] in ("U", "S"):
            check(f"{key} calls = 25k [{sd} {rn} k={k}]", m["calls"] == 25 * k, str(m["calls"]))
        if m["policy"] == "PACE":
            r_ = m["params"]["r"]
            check(f"{key} 0 <= calls <= 25(1-r)k + reserve used <= 25k [{sd} {rn} k={k}]",
                  0 <= m["calls"] <= m["pace_bound"] + 1e-9 and m["pace_bound"] <= 25 * k + 1e-9,
                  f"{m['calls']} <= {m['pace_bound']:.1f}")
            check(f"{key} max calls/day <= 2k [{sd} {rn} k={k}]", m["pace_max_day"] <= 2 * k,
                  str(m["pace_max_day"]))
            check(f"{key} reserve used <= 25 r k [{sd} {rn} k={k}]",
                  m["pace_reserve_used"] <= 25 * r_ * k + 1e-9, f"{m['pace_reserve_used']:.2f}")
        if m["policy"] == "PACE-v0":
            check(f"{key} 0 <= calls <= v0 window bound [{sd} {rn} k={k}]",
                  0 <= m["calls"] <= m["pace_bound"] <= round(25 * k * (1 + 0.04)),
                  f"{m['calls']} <= {m['pace_bound']}")
        for e in ("alloc", "det", "d_det_vs_S", "d_det_vs_PACE_primary", "d_alloc_vs_S"):
            pt, (lo, hi) = m[e]["pt"], m[e]["ci"]
            if lo is not None and math.isfinite(pt):
                check(f"CI contains pt {e} {key} [{sd} {rn} k={k}]", lo - 1e-12 <= pt <= hi + 1e-12,
                      f"{lo:.3f} <= {pt:.3f} <= {hi:.3f}")
    for k in KS:
        npi = res["np_calibration"][str(k)]
        check(f"NP calibration mean calls/day = k (k={k})", abs(npi["cal_mean_calls_per_day"] - k) <= 0.2 + 1e-9,
              f"{npi['cal_mean_calls_per_day']:.2f}")
    n0 = len(scheds["rate100/original"].pos_ids)
    for name, s in scheds.items():
        want = int(math.floor(s.rate * n0 + 0.5))
        base = scheds[f"rate{int(round(s.rate * 100))}/original"]
        on_eval = np.isin(s.sim_day[s.pos_ids], EVAL_DAYS).all()
        check(f"regime {name} keeps {want} positives on evaluation days",
              len(s.pos_ids) == want and on_eval and set(s.pos_ids) == set(base.pos_ids),
              f"{len(s.pos_ids)}")
        nd = len({int(s.sim_day[p]) for p in s.pos_ids})
        if s.placement in ("burst5", "adversarial"):
            check(f"regime {name} uses 5 days", nd == 5, str(nd))
    q = res["expensive_quality"]
    for nm in ("auroc_e", "auroc_c", "auroc_diff_e_minus_c"):
        lo, hi = q[nm]["ci"]
        check(f"CI contains pt {nm}", lo - 1e-12 <= q[nm]["pt"] <= hi + 1e-12)
    bad = [c for c in checks if not c[1]]
    for line in info:
        print(f"INFO {line}")
    for name, ok, det in bad:
        print(f"FAIL {name}: {det}")
    print(f"selftest: {len(checks) - len(bad)}/{len(checks)} checks passed; "
          f"K2: {res['k2']['text']}")
    P = res["primary"]
    print(f"primary (synthetic): PACE {fe(P['PACE'])}  S {fe(P['S'])}  diff {fd(P['diff_PACE_minus_S'])}"
          f"  calls PACE {P['PACE_calls']} / S {P['S_calls']}")
    if pace_v0:
        v = raw[("theta50", "rate100/original", PRIMARY_K, PACE_V0_KEY)]
        print(f"post hoc PACE-v0(w=3, r=0.2): det {fe(v['det'])}  diff vs S {fd(v['d_det_vs_S'])}  "
              f"calls {v['calls']}")
    print(f"run time {res['runtime_s']:.1f} s; selftest total {time.time() - t0:.1f} s")
    return 0 if not bad else 1


# ── CLI ──────────────────────────────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cheap")
    ap.add_argument("--expensive")
    ap.add_argument("--labels")
    ap.add_argument("--out-md", default=str(PROJECT / "work/stage2/a-track-a-results.md"))
    ap.add_argument("--out-json", default=str(PROJECT / "work/stage2/a-track-a-results.json"))
    ap.add_argument("--fig", default=str(PROJECT / "work/stage2/fig-phase-diagram.png"))
    ap.add_argument("--bootstrap", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--allow-incomplete", action="store_true")
    ap.add_argument("--synthetic-selftest", action="store_true")
    ap.add_argument("--pace-v0", action="store_true",
                    help="add section 4's superseded PACE (w=3, r=0.2) as a post hoc comparison row")
    ap.add_argument("--synthetic-dir", default=str(PROJECT / "work/stage2/synthetic"))
    ns = ap.parse_args(argv)
    if ns.synthetic_selftest:
        return selftest(Path(ns.synthetic_dir), B=ns.bootstrap, seed=ns.seed, pace_v0=ns.pace_v0)
    if not (ns.cheap and ns.expensive and ns.labels):
        ap.error("--cheap, --expensive and --labels are required (or --synthetic-selftest)")
    res = run(Path(ns.cheap), Path(ns.expensive), Path(ns.labels), Path(ns.out_md), Path(ns.out_json),
              Path(ns.fig), B=ns.bootstrap, seed=ns.seed, allow_incomplete=ns.allow_incomplete,
              pace_v0=ns.pace_v0)
    P = res["primary"]
    print(f"PRIMARY PACE(w=3, r=0.2) {fe(P['PACE'])} vs S {fe(P['S'])}: diff {fd(P['diff_PACE_minus_S'])}")
    print(res["k2"]["text"])
    print(f"wrote {ns.out_md}, {ns.out_json}, {ns.fig} in {res['runtime_s']:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
