#!/usr/bin/env python3
"""Track A cheap tier c(a, d): label-blind scores for every account-day of a released
MOLE corpus (pre-registration: work/mole-fork/protocol/TRACK-A.md sections 1 and 2).

Unit: an account-day is (account, ts[:10]) with at least one exit_code == 0 event.
Day index 1 is the corpus's first date; the index is the rank of the date among the
corpus's distinct dates (gpt53 has 30 weekday dates, so calendar offsets would differ).
Days 1..5 are calibration, days 6..30 evaluation.

Columns written to --out (one row per unit account-day, days 1..30):

  account, date, day_index, is_eval_day, n_events, n_ok_events
  c_z       ZScoreAnomalyMonitor score, monitor fit on the rollup rows of all unit
            account-days of days 1..d-1 (refit per day), scoring the row of (a, d).
            Null on days 1..5.
  c_z_cal   days 1..5 only: in-sample score, monitor fit on days 1..5 pooled.
            Null on days 6..30.
  l1_any, l1_nonnoisy, l1_variants
            Stage 0 STRUCTURAL matchers (work/checks/upstream_matchers_as_detectors.py)
            over the account-day's exit_code == 0 events at stealth levels s0 and s1.
  is_positive_executed, is_positive_attempted, scenario, labelled_account
            written ONLY by read_label_columns() (the single label-reading function).

Scoring path (documented choice): the whole corpus is rolled up ONCE with
mole.audit.rollup.rollup over AuditEvents built from every parquet row (failed calls
included, as the rollup and MOLE's classical baseline consume the full event stream);
each day's fit takes the precomputed UserDayFeatures rows of the earlier unit
account-days, and each account-day is scored with the monitor's `_row_score` on its
single precomputed row (no re-rolling; identical to score_episode on that
account-day's events because score_episode rolls up to that same single row).
`is_malicious` is forced False on every AuditEvent (the monitor never sees labels).

Labels: read_label_columns() is the only code that touches the label file. Its output
never feeds c_z or c_z_cal. It does define the never-labelled account-days used for the
layer-1 noisy-variant set (Stage 1's definition), so l1_nonnoisy's variant list is
label-dependent, exactly as in Stage 1; l1_any is not.

Usage (data dir is untrusted: -I and absolute paths):

    work/mole-fork/.venv/bin/python -I /abs/work/checks/score_cheap_tier.py \\
        --data-dir /abs/work/upstream-data --corpus gpt53_single_day \\
        --out /abs/work/stage2/scores/gpt53_single_day.cheap.parquet

Also writes <out minus .parquet>.meta.json and prints the baseline rows (cheap-tier
AUROC and recall at k per day on the original schedule).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

HERE = Path(__file__).resolve().parent                       # work/checks
PROJECT = HERE.parent.parent                                 # tais-project-selection
FORK = PROJECT / "work" / "mole-fork"
MATCHERS_PATH = HERE / "upstream_matchers_as_detectors.py"

N_CAL_DAYS = 5                 # days 1..5 calibration
FIRST_EVAL_DAY = 6             # days 6..30 evaluation
LEVELS = ("s0", "s1")
NOISY_RATE = 0.05              # variant noisy if it fires on > 5% of never-labelled account-days
RECALL_KS = (2, 5, 10, 15, 20)
MOLE_BEST_CLASSICAL_AUROC = 0.694

AUDIT_COLS = ["event_id", "ts", "real_ts", "account", "account_kind", "service", "action",
              "resource_id", "args", "exit_code", "bytes", "is_external", "dest_domain"]


def _setup_paths() -> None:
    # python -I adds neither the script dir nor user site; the fork is imported as a
    # package from its root (mole/__init__ only registers state backends).
    if str(FORK) not in sys.path:
        sys.path.insert(0, str(FORK))


def load_matchers_module(path: Path = MATCHERS_PATH):
    """Load the Stage 0 STRUCTURAL matcher module by file path."""
    spec = importlib.util.spec_from_file_location("upstream_matchers_as_detectors", str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_args_json(s: Any) -> dict:
    if not isinstance(s, str) or not s:
        return {}
    try:
        v = json.loads(s)
    except Exception:
        return {}
    return v if isinstance(v, dict) else {}


# ── days ─────────────────────────────────────────────────────────────────

def day_index_map(dates: Iterable[str]) -> dict[str, int]:
    """Date -> 1-based index by rank among the corpus's distinct dates."""
    return {d: i + 1 for i, d in enumerate(sorted(set(dates)))}


# ── events (label-blind) ─────────────────────────────────────────────────

def load_audit(data_dir: Path, corpus: str):
    import pandas as pd
    p = data_dir / "data" / "audit" / corpus / "0000.parquet"
    df = pd.read_parquet(p, columns=AUDIT_COLS)       # is_malicious column NOT read
    return df


def prepare(df):
    """Sort deterministically and add the `day` column (ts[:10])."""
    df = df.copy()
    df["day"] = df["ts"].str.slice(0, 10)
    return df.sort_values(["ts", "event_id"], kind="stable").reset_index(drop=True)


def _s(v) -> str:
    return v if isinstance(v, str) else ""


def build_audit_events(df) -> tuple[list, list[dict]]:
    """AuditEvent per row (is_malicious ALWAYS False) and the parsed args per row."""
    _setup_paths()
    from mole.audit.schema import AuditEvent
    cols = {c: df[c].to_numpy() for c in AUDIT_COLS if c in df.columns}
    n = len(df)
    parsed = [parse_args_json(a) for a in cols["args"]]
    rts = cols.get("real_ts")
    byt = cols.get("bytes")
    dd = cols.get("dest_domain")
    out = []
    for i in range(n):
        out.append(AuditEvent(
            event_id=_s(cols["event_id"][i]),
            ts=cols["ts"][i],
            real_ts=float(rts[i]) if rts is not None and rts[i] == rts[i] else 0.0,
            account=cols["account"][i],
            account_kind=_s(cols["account_kind"][i]),
            service=_s(cols["service"][i]),
            action=_s(cols["action"][i]),
            resource_id=_s(cols["resource_id"][i]),
            args=parsed[i],
            exit_code=int(cols["exit_code"][i]),
            bytes=int(byt[i]) if byt is not None and byt[i] == byt[i] else 0,
            dest_domain=dd[i] if dd is not None and isinstance(dd[i], str) else None,
            is_external=bool(cols["is_external"][i]),
            is_malicious=False,                      # never let a label reach the monitor
        ))
    return out, parsed


def unit_account_days(df) -> list[tuple[str, str]]:
    ok = df[df["exit_code"] == 0]
    return sorted(ok.groupby(["account", "day"], sort=True).indices)


def rollup_rows(events: Sequence) -> dict[tuple[str, str], Any]:
    """Roll up the whole corpus once; key (account, date)."""
    _setup_paths()
    from mole.audit.rollup import rollup
    return {(r.account, r.date): r for r in rollup(events)}


# ── cheap tier c_z (label-blind) ─────────────────────────────────────────

def _new_monitor():
    _setup_paths()
    from mole.monitors.classical.anomaly import ZScoreAnomalyMonitor
    return ZScoreAnomalyMonitor()


def cheap_scores(units: list[tuple[str, str]], rows: dict, day_idx: dict[str, int]) -> dict:
    """c_z (rolling fit on days 1..d-1, days >= 6) and c_z_cal (pooled days 1..5,
    in-sample, days 1..5). Uses only the rollup rows; never labels."""
    by_day: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for k in units:
        by_day[day_idx[k[1]]].append(k)
    n_days = max(day_idx.values())
    c_z: dict[tuple[str, str], float] = {}
    c_cal: dict[tuple[str, str], float] = {}
    fit_info: dict[int, dict] = {}

    cal_keys = [k for d in range(1, N_CAL_DAYS + 1) for k in by_day.get(d, [])]
    if cal_keys:
        m = _new_monitor().fit([rows[k] for k in cal_keys])
        for k in cal_keys:
            c_cal[k] = m._row_score(rows[k])
        fit_info[0] = {"fit_days": [1, N_CAL_DAYS], "n_fit_rows": len(cal_keys),
                       "med": list(m._med), "scale": list(m._scale)}

    history: list[tuple[str, str]] = [k for d in range(1, FIRST_EVAL_DAY) for k in by_day.get(d, [])]
    for d in range(FIRST_EVAL_DAY, n_days + 1):
        # fit strictly on days 1..d-1
        assert all(day_idx[k[1]] < d for k in history)
        m = _new_monitor().fit([rows[k] for k in history])
        for k in by_day.get(d, []):
            c_z[k] = m._row_score(rows[k])
        fit_info[d] = {"fit_days": [1, d - 1], "n_fit_rows": len(history),
                       "med": list(m._med), "scale": list(m._scale)}
        history.extend(by_day.get(d, []))
    return {"c_z": c_z, "c_z_cal": c_cal, "fits": fit_info}


# ── layer 1 (matchers are label-blind; the noisy set is not) ─────────────

def layer1_fired(st_mod, df, parsed: list[dict], units: list[tuple[str, str]]) -> dict:
    """Variants fired per unit account-day over its exit_code == 0 events (s0 or s1)."""
    ok_mask = (df["exit_code"] == 0).to_numpy()
    ok_idx = [i for i in range(len(df)) if ok_mask[i]]
    sub = df.iloc[ok_idx]
    groups = sub.groupby(["account", "day"], sort=True).indices
    svc = df["service"].to_numpy(); act = df["action"].to_numpy(); ec = df["exit_code"].to_numpy()
    acc = df["account"].to_numpy(); tsv = df["ts"].to_numpy(); eid = df["event_id"].to_numpy()
    fired: dict[tuple[str, str], set] = {}
    for k in units:
        evs = [st_mod.Event(svc[j], act[j], parsed[j], int(ec[j]), acc[j], tsv[j], eid[j])
               for j in (ok_idx[p] for p in groups.get(k, []))]
        hits = set()
        if evs:
            for name, fn in st_mod.STRUCTURAL.items():
                for lvl in LEVELS:
                    if fn(evs, lvl):
                        hits.add(name)
                        break
        fired[k] = hits
    return fired


def noisy_variants(fired: dict, never_labelled_keys: list, variants: Iterable[str],
                   threshold: float = NOISY_RATE) -> tuple[list[str], dict[str, float]]:
    """Variants firing on MORE than `threshold` of the never-labelled account-days."""
    n = len(never_labelled_keys)
    rate = {v: (sum(1 for k in never_labelled_keys if v in fired[k]) / n if n else 0.0)
            for v in variants}
    return sorted(v for v, r in rate.items() if r > threshold), rate


# ── LABELS: the only function that reads the label file ──────────────────

def read_label_columns(data_dir: Path, corpus: str, units: list[tuple[str, str]]) -> dict:
    """##### LABEL READ #####  Returns the label columns per unit account-day and the
    labelled-account set. Nothing returned here may feed c_z / c_z_cal."""
    import pandas as pd
    lab = pd.read_parquet(data_dir / "data" / "labels" / corpus / "0000.parquet")
    labelled_accounts = set(lab["account"])
    by_ad = {(r.account, r.date): (r.scenario, r.outcome) for r in lab.itertuples(index=False)}
    unit_set = set(units)
    cols = {"is_positive_executed": [], "is_positive_attempted": [], "scenario": [],
            "labelled_account": []}
    for k in units:
        sc, oc = by_ad.get(k, (None, None))
        cols["is_positive_executed"].append(oc == "executed")
        cols["is_positive_attempted"].append(oc == "attempted")
        cols["scenario"].append(sc)
        cols["labelled_account"].append(k[0] in labelled_accounts)
    missing = sorted(f"{a}/{d}:{oc}" for (a, d), (_, oc) in by_ad.items() if (a, d) not in unit_set)
    return {"cols": cols, "labelled_accounts": labelled_accounts,
            "n_label_rows": int(len(lab)), "label_rows_not_units": missing}


# ── metrics ──────────────────────────────────────────────────────────────

def auroc(pos: Sequence[float], neg: Sequence[float]) -> float | None:
    """Rank-based (Mann-Whitney) AUROC, ties counted one half."""
    if not pos or not neg:
        return None
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg], key=lambda t: t[0])
    ranks = [0.0] * len(allv)
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for t in range(i, j + 1):
            ranks[t] = r
        i = j + 1
    rsum = sum(r for r, (_, y) in zip(ranks, allv) if y == 1)
    n1, n0 = len(pos), len(neg)
    return (rsum - n1 * (n1 + 1) / 2) / (n1 * n0)


def recall_at_k(day_of: dict, score: dict, positives: set, ks: Iterable[int]) -> dict:
    """Per day, top-k by score (ties broken by account name); recall = share of
    positives that fall in the top-k of their own day."""
    by_day: dict[str, list] = defaultdict(list)
    for k in score:
        by_day[day_of[k]].append(k)
    out = {}
    n_pos = sum(1 for k in positives if k in score)
    for kk in ks:
        hit = 0
        for d, keys in by_day.items():
            top = sorted(keys, key=lambda x: (-score[x], x[0]))[:kk]
            hit += sum(1 for x in top if x in positives)
        out[kk] = {"caught": hit, "n_pos": n_pos, "recall": (hit / n_pos) if n_pos else None}
    return out


# ── pipeline ─────────────────────────────────────────────────────────────

def score_corpus(df, st_mod) -> dict:
    """Everything label-blind: units, day index, rollup, c_z, c_z_cal, L1 fired sets."""
    df = prepare(df)
    t = time.time()
    events, parsed = build_audit_events(df)
    assert not any(e.is_malicious for e in events)
    rows = rollup_rows(events)
    t_roll = time.time() - t
    units = unit_account_days(df)
    missing_rows = [k for k in units if k not in rows]
    assert not missing_rows, f"unit account-days without a rollup row: {missing_rows[:5]}"
    day_idx = day_index_map(df["day"])
    t = time.time()
    cs = cheap_scores(units, rows, day_idx)
    t_score = time.time() - t
    t = time.time()
    fired = layer1_fired(st_mod, df, parsed, units)
    t_l1 = time.time() - t
    n_ev = df.groupby(["account", "day"]).size().to_dict()
    n_ok = df[df["exit_code"] == 0].groupby(["account", "day"]).size().to_dict()
    return {"df": df, "events": events, "rows": rows, "units": units, "day_idx": day_idx,
            "c_z": cs["c_z"], "c_z_cal": cs["c_z_cal"], "fits": cs["fits"], "fired": fired,
            "n_ev": n_ev, "n_ok": n_ok,
            "seconds": {"events_and_rollup": round(t_roll, 1), "cheap_scores": round(t_score, 2),
                        "layer1": round(t_l1, 1)}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args()
    t0 = time.time()
    import pandas as pd
    _setup_paths()
    from mole.monitors.classical.anomaly import NUMERIC_FEATURES, RATIO_FEATURES, ZScoreAnomalyMonitor

    data_dir = Path(ns.data_dir)
    out = Path(ns.out)
    meta_path = out.with_name(out.name[: -len(".parquet")] + ".meta.json") if out.name.endswith(".parquet") \
        else out.with_suffix(".meta.json")

    st_mod = load_matchers_module()
    df = load_audit(data_dir, ns.corpus)
    print(f"loaded {len(df)} events in {time.time()-t0:.1f}s", file=sys.stderr)
    S = score_corpus(df, st_mod)
    units, day_idx = S["units"], S["day_idx"]
    print(f"{len(units)} unit account-days, {len(day_idx)} dates; timings {S['seconds']}", file=sys.stderr)

    # ── labels (single marked function) ──
    L = read_label_columns(data_dir, ns.corpus, units)
    labelled = L["labelled_accounts"]
    never_labelled = [k for k in units if k[0] not in labelled]
    noisy, rates = noisy_variants(S["fired"], never_labelled, st_mod.STRUCTURAL.keys())

    frame = pd.DataFrame({
        "account": [k[0] for k in units],
        "date": [k[1] for k in units],
        "day_index": [day_idx[k[1]] for k in units],
        "is_eval_day": [day_idx[k[1]] >= FIRST_EVAL_DAY for k in units],
        "n_events": [int(S["n_ev"].get(k, 0)) for k in units],
        "n_ok_events": [int(S["n_ok"].get(k, 0)) for k in units],
        "c_z": [S["c_z"].get(k) for k in units],
        "c_z_cal": [S["c_z_cal"].get(k) for k in units],
        "l1_any": [bool(S["fired"][k]) for k in units],
        "l1_nonnoisy": [any(v not in noisy for v in S["fired"][k]) for k in units],
        "l1_variants": [",".join(sorted(S["fired"][k])) for k in units],
        **L["cols"],
    })
    frame["c_z"] = frame["c_z"].astype("float64")
    frame["c_z_cal"] = frame["c_z_cal"].astype("float64")
    out.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out, index=False)

    # ── baseline rows ──
    ev = frame[frame["is_eval_day"]]
    pos_ex = ev[ev["is_positive_executed"]]
    pos_at = ev[ev["is_positive_attempted"]]
    neg = ev[~ev["labelled_account"]]
    au_ex = auroc(pos_ex["c_z"].tolist(), neg["c_z"].tolist())
    au_at = auroc(pos_at["c_z"].tolist(), neg["c_z"].tolist())
    keys = list(zip(ev["account"], ev["date"]))
    score = dict(zip(keys, ev["c_z"]))
    day_of = {k: k[1] for k in keys}
    pos_set = set(zip(pos_ex["account"], pos_ex["date"]))
    rec = recall_at_k(day_of, score, pos_set, RECALL_KS)
    rec_at = recall_at_k(day_of, score, set(zip(pos_at["account"], pos_at["date"])), RECALL_KS)
    l1_ev = {
        "l1_any": {"recall_executed": float(pos_ex["l1_any"].mean()) if len(pos_ex) else None,
                   "honest_flag_rate": float(neg["l1_any"].mean()) if len(neg) else None},
        "l1_nonnoisy": {"recall_executed": float(pos_ex["l1_nonnoisy"].mean()) if len(pos_ex) else None,
                        "honest_flag_rate": float(neg["l1_nonnoisy"].mean()) if len(neg) else None},
    }
    rows_per_day = {int(d): int(n) for d, n in frame.groupby("day_index").size().items()}

    print(f"\naccount-days total {len(frame)}; days 1-5 {int((~frame.is_eval_day).sum())}; "
          f"days 6-30 {len(ev)}")
    print(f"eval-day executed positives {len(pos_ex)}, attempted {len(pos_at)}, never-labelled {len(neg)}")
    print(f"cheap-tier AUROC (executed vs never-labelled, days 6-30): {au_ex:.4f}   "
          f"[MOLE best classical baseline: {MOLE_BEST_CLASSICAL_AUROC}]")
    print(f"cheap-tier AUROC (attempted vs never-labelled): {au_at if au_at is None else round(au_at, 4)}")
    print("recall@k per day (executed): " + ", ".join(f"k={k}: {v['caught']}/{v['n_pos']}={v['recall']:.3f}"
                                                       for k, v in rec.items()))
    print(f"noisy L1 variants: {noisy}")
    print(f"L1 eval days: {l1_ev}")

    day30 = S["fits"].get(max(day_idx.values()), {})
    runtime = round(time.time() - t0, 1)
    meta = {
        "corpus": ns.corpus,
        "out": str(out),
        "dates": sorted(day_idx),
        "day_index": day_idx,
        "first_date": min(day_idx),
        "n_dates": len(day_idx),
        "calibration_days": [1, N_CAL_DAYS],
        "evaluation_days": [FIRST_EVAL_DAY, len(day_idx)],
        "n_events": int(len(S["df"])),
        "n_account_days": int(len(frame)),
        "n_account_days_calibration": int((~frame.is_eval_day).sum()),
        "n_account_days_evaluation": int(len(ev)),
        "account_days_per_day_index": rows_per_day,
        "scoring": {
            "monitor": f"{ZScoreAnomalyMonitor.__module__}.{ZScoreAnomalyMonitor.__name__}",
            "row_scoring": "ZScoreAnomalyMonitor._row_score on the single precomputed UserDayFeatures row",
            "rollup_input": "AuditEvents from every parquet row (failed calls included); rolled up once",
            "is_malicious": "forced False on every AuditEvent; the audit is_malicious column is not read",
            "fit_rows": "unit account-days (>=1 exit_code==0 event) only",
            "c_z": "fit on days 1..d-1, scored on day d, d = 6..30; null on days 1..5",
            "c_z_cal": "fit on days 1..5 pooled, in-sample score on days 1..5; null on days 6..30",
            "feature_names": list(NUMERIC_FEATURES),
            "n_features": len(NUMERIC_FEATURES),
            "ratio_features_unnormalised": sorted(RATIO_FEATURES),
            "z_clip": ZScoreAnomalyMonitor.Z_CLIP,
        },
        "fit_day30": {"fit_days": day30.get("fit_days"), "n_fit_rows": day30.get("n_fit_rows"),
                      "median": dict(zip(NUMERIC_FEATURES, day30.get("med", []))),
                      "scale": dict(zip(NUMERIC_FEATURES, day30.get("scale", [])))},
        "fit_calibration": {"n_fit_rows": S["fits"].get(0, {}).get("n_fit_rows"),
                            "median": dict(zip(NUMERIC_FEATURES, S["fits"].get(0, {}).get("med", []))),
                            "scale": dict(zip(NUMERIC_FEATURES, S["fits"].get(0, {}).get("scale", [])))},
        "layer1": {
            "matchers": str(MATCHERS_PATH), "matchers_sha256": sha256_file(MATCHERS_PATH),
            "levels": list(LEVELS), "noisy_rule": "rate > 0.05 over never-labelled account-days of days 1..30",
            "n_never_labelled_account_days": len(never_labelled),
            "noisy_variants": noisy,
            "rate_per_variant": {v: round(r, 5) for v, r in rates.items()},
            "eval_days": l1_ev,
        },
        "labels": {"n_label_rows": L["n_label_rows"], "n_labelled_accounts": len(labelled),
                   "label_rows_not_unit_account_days": L["label_rows_not_units"]},
        "baseline": {
            "auroc_executed_vs_never_labelled_eval_days": au_ex,
            "auroc_attempted_vs_never_labelled_eval_days": au_at,
            "n_pos_executed_eval": int(len(pos_ex)), "n_pos_attempted_eval": int(len(pos_at)),
            "n_never_labelled_eval": int(len(neg)),
            "recall_at_k_per_day_executed": {str(k): v for k, v in rec.items()},
            "recall_at_k_per_day_attempted": {str(k): v for k, v in rec_at.items()},
            "recall_tie_break": "score desc, then account name asc",
            "mole_best_classical_auroc": MOLE_BEST_CLASSICAL_AUROC,
        },
        "timings_seconds": {**S["seconds"], "total": runtime},
        "script": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "python": sys.version.split()[0],
    }
    meta_path.write_text(json.dumps(meta, indent=1))
    print(f"wrote {out} and {meta_path} in {runtime}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
