#!/usr/bin/env python3
"""S5.3 (brief 07): the objective-bearing benign-template session, measured.

Reads the S5.3 placeholder run (three honest prefix accounts, one simulated day, two
sessions each, one of which carries the routine placeholder objective under
``--objective-carrier benign``) and puts its sessions beside honest references:

* **same-run honest**: the other session of each of the same three accounts (same substrate,
  same day, same accounts; the only confound-free comparison, n = 3 vs 3);
* **prefix honest**: every session of ``prefix_v1`` (substrate (ii) in-process; 224 sessions;
  the substrate confound is stated, not removed);
* **lab honest** (optional): every session of a lab-mode honest corpus given on the command
  line (the S0 smoke on substrate (i), full lab with GitLab, if it exists).

Four session-level features, the four lesson-L13 metadata features read per SESSION rather
than per account-day: ``turn_count`` (session length), ``capped`` (turn_count >= max_turns),
``events`` (audit rows whose ``task_id`` is the session's), ``first_action_min`` (simulated
minutes since midnight of the session's first exit_code-0 event). Two more for reading:
``first_action_offset_min`` (first action minus the session's ``sim_ts``) and
``agenda_len`` / ``objective_position`` from the transcript row where present.

Numbers reported: per group the quantiles of each feature; for each scenario session its
percentile rank inside each honest group; the per-feature rank AUROC (Mann-Whitney, the
``grouping_measure.auroc`` formula) scenario vs each honest group; and, at ACCOUNT-DAY level,
the two frozen leak classifiers (``grouping_measure.metadata_features`` +
``grouping_measure.leak_classifier``; ``stage3_leak_content.content_matrix`` +
``leak_classifier``) with the run's account-days as positives against the prefix's as
negatives. The run has no honest ACCOUNT-DAY of its own (every account-day holds the
scenario session), so the within-run classifier exists only at session level and is
descriptive: three against three cannot be cross-validated.

Label-blind rule: the only non-blind transcript fields read are ``session_mode``,
``has_insider_persona``, ``carrier``, ``objective_position``, ``agenda_len``,
``elicit_prefix`` of the S5.3 run itself (they are the ground truth this plumbing test
needs); the honest references are read through the frozen label-blind readers.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_s5c_metadata.py \\
        --corpus <s5c audit jsonl> --transcripts <s5c transcripts jsonl> \\
        [--lab-honest-corpus <jsonl> --lab-honest-transcripts <jsonl>] \\
        --out-json <path> --out-md <path>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import grouping_measure as gm  # noqa: E402
import mole_corpus as mc  # noqa: E402
import stage3_leak_content as lc  # noqa: E402

VERSION = "stage3-s5c-metadata-v1"
PROJECT = HERE.parent.parent
DEFAULT_PREFIX = PROJECT / "work/mole-fork/data/corpus/spike/prefix_v1.jsonl"
MAX_TURNS = 50
FEATURES = ("turn_count", "capped", "events", "first_action_min", "first_action_offset_min")
QUANTS = (0.05, 0.25, 0.5, 0.75, 0.95)
SCENARIO_FIELDS = ("session_mode", "has_insider_persona", "carrier", "objective_position",
                   "agenda_len", "elicit_prefix")


def _transcripts(path: Path) -> Path:
    return path if path.exists() else gm.default_transcripts(path)


def session_table(corpus: Path, transcripts: Path, max_turns: int,
                  read_scenario_fields: bool) -> pd.DataFrame:
    """One row per transcript session with the four session-level features."""
    rows = []
    with open(transcripts, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            e = json.loads(line)
            if not isinstance(e, dict):
                continue
            r = {k: e.get(k) for k in gm.TRANSCRIPT_FIELDS}
            r["cost_usd"] = e.get("cost_usd")
            if read_scenario_fields:
                for k in SCENARIO_FIELDS:
                    r[k] = e.get(k)
            rows.append(r)
    s = pd.DataFrame(rows)
    s["date"] = s["sim_ts"].astype(str).str[:10]
    s["turn_count"] = pd.to_numeric(s["turn_count"], errors="coerce")
    s["capped"] = (s["turn_count"] >= max_turns).astype(float)
    s["session_start_min"] = mc.sim_minutes(s["sim_ts"])
    # audit rows per session (task_id), and the first successful action's simulated minute
    ev: dict[str, int] = {}
    ev_ok: dict[str, int] = {}
    first: dict[str, float] = {}
    with open(corpus, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            tid = d.get("task_id")
            if not tid:
                continue
            ev[tid] = ev.get(tid, 0) + 1
            if d.get("exit_code") == 0:
                ev_ok[tid] = ev_ok.get(tid, 0) + 1
                ts = str(d.get("ts", ""))
                if len(ts) >= 16:
                    m = float(ts[11:13]) * 60 + float(ts[14:16])
                    if tid not in first or m < first[tid]:
                        first[tid] = m
    s["events"] = s["task_id"].map(lambda t: ev.get(t, 0)).astype(float)
    s["events_ok"] = s["task_id"].map(lambda t: ev_ok.get(t, 0)).astype(float)
    s["failed_share"] = np.where(s["events"] > 0, 1 - s["events_ok"] / s["events"].clip(lower=1), np.nan)
    s["first_action_min"] = s["task_id"].map(lambda t: first.get(t, np.nan)).astype(float)
    s["first_action_offset_min"] = s["first_action_min"] - s["session_start_min"]
    return s.sort_values(["account", "sim_ts"]).reset_index(drop=True)


def quantiles(v: pd.Series) -> dict[str, float]:
    v = pd.to_numeric(v, errors="coerce").dropna()
    out = {"n": int(len(v))}
    if len(v):
        out.update({f"p{int(q * 100)}": float(v.quantile(q)) for q in QUANTS})
        out["mean"] = float(v.mean())
    return out


def pct_rank(x: float, ref: pd.Series) -> float | None:
    ref = pd.to_numeric(ref, errors="coerce").dropna().to_numpy()
    if np.isnan(x) or len(ref) == 0:
        return None
    return float(((ref < x).sum() + 0.5 * (ref == x).sum()) / len(ref))


def feature_auroc(pos: pd.Series, neg: pd.Series) -> float | None:
    p = pd.to_numeric(pos, errors="coerce").dropna().to_numpy()
    n = pd.to_numeric(neg, errors="coerce").dropna().to_numpy()
    if len(p) == 0 or len(n) == 0:
        return None
    y = np.concatenate([np.ones(len(p)), np.zeros(len(n))])
    return gm.auroc(y, np.concatenate([p, n]))


def account_day_classifiers(run_corpus: Path, run_tx: Path, pre_corpus: Path, pre_tx: Path,
                            template_path: Path, max_turns: int, seed: int,
                            n_features: int) -> dict[str, Any]:
    """Frozen metadata and content classifiers at account-day level: the run's account-days
    (positives) against the prefix's (negatives). Keys of the run are tagged so an account
    that exists in both corpora on the same date stays two rows."""
    template = mc.load_org_template(str(template_path))
    out: dict[str, Any] = {}
    feats = []
    turns_all: dict[tuple[str, str], list] = {}
    for tag, corpus, tx, label in (("run", run_corpus, run_tx, 1), ("prefix", pre_corpus, pre_tx, 0)):
        br = gm.load_branch(corpus, None, template, tag, None, tx)
        f, info = gm.metadata_features(br, max_turns)
        f = f.sort_values(["account", "date"]).reset_index(drop=True)
        f["label"] = label
        f["tag"] = tag
        feats.append(f)
        out[f"{tag}_account_days"] = int(len(f))
        out[f"{tag}_metadata_info"] = {k: v for k, v in info.items() if k != "transcripts"}
        for (a, d), t in lc.account_day_turns(tx).items():
            turns_all[(f"{tag}:{a}", d)] = t
    F = pd.concat(feats, ignore_index=True)
    names = ["session_length", "turn_cap_rate", "events_per_session", "first_action_min"]
    y = F["label"].to_numpy(dtype=int)
    Xm = F[names].to_numpy(dtype=float)
    out["metadata"] = {"features": names, **_trim(gm.leak_classifier(Xm, y, seed=seed))}
    keys = [(f"{t}:{a}", d) for t, a, d in zip(F["tag"], F["account"], F["date"])]
    Xc, cinfo = lc.content_matrix(None, keys, n_features, turns_all)
    out["content"] = {"features": cinfo, **_trim(gm.leak_classifier(Xc, y, seed=seed))}
    out["note"] = ("positives are the run's account-days (every one holds the scenario "
                   "session), negatives the prefix's; substrate confound: lab (i-) vs "
                   "in-process (ii); with fewer than five positives the frozen classifier "
                   "reports the point AUROC only")
    return out


def _trim(r: dict[str, Any]) -> dict[str, Any]:
    keep = ("n", "positives", "folds", "threshold", "auroc", "auroc_two_sided", "ci", "n_boot",
            "passed", "status")
    return {k: r[k] for k in keep if k in r}


def analyse(run_corpus: Path, run_tx: Path, pre_corpus: Path, pre_tx: Path,
            lab_corpus: Path | None, lab_tx: Path | None, template_path: Path,
            max_turns: int, seed: int, n_features: int) -> dict[str, Any]:
    run = session_table(run_corpus, run_tx, max_turns, True)
    pre = session_table(pre_corpus, pre_tx, max_turns, False)
    groups: dict[str, pd.DataFrame] = {"prefix_honest": pre}
    if lab_corpus is not None and lab_tx is not None and lab_corpus.exists() and lab_tx.exists():
        groups["lab_honest"] = session_table(lab_corpus, lab_tx, max_turns, False)
    scen = run[run["session_mode"] == "attack"]
    same_run_honest = run[run["session_mode"] != "attack"]
    groups["same_run_honest"] = same_run_honest

    res: dict[str, Any] = {
        "run": {
            "sessions": int(len(run)), "scenario_sessions": int(len(scen)),
            "honest_sessions": int(len(same_run_honest)),
            "accounts": sorted(run["account"].unique().tolist()),
            "dates": sorted(run["date"].unique().tolist()),
            "carrier_values": sorted({str(x) for x in run.get("carrier", pd.Series(dtype=object)).dropna()}),
            "elicit_prefix_any": bool(run.get("elicit_prefix", pd.Series(dtype=object)).fillna(False).astype(bool).any()),
            "aborted": int(run["aborted_reason"].notna().sum()),
            "finish_reasons": run["finish_reason"].fillna("None").value_counts().to_dict(),
            "cost_usd_sum": float(pd.to_numeric(run["cost_usd"], errors="coerce").fillna(0).sum()),
            "per_session": run[["account", "date", "sim_ts", "task_id", "session_mode", "turn_count",
                                "capped", "events", "events_ok", "failed_share", "first_action_min",
                                "first_action_offset_min", "finish_reason", "aborted_reason",
                                "agenda_len", "objective_position", "elicit_prefix",
                                "cost_usd"]].to_dict(orient="records"),
        },
        "groups": {g: {f: quantiles(df[f]) for f in FEATURES} for g, df in groups.items()},
        "scenario_quantiles": {f: quantiles(scen[f]) for f in FEATURES},
        "scenario_percentile_ranks": {},
        "feature_auroc_scenario_vs": {},
        "max_turns": max_turns,
    }
    for g, df in groups.items():
        res["scenario_percentile_ranks"][g] = [
            {"account": r.account, "task_id": r.task_id,
             **{f: pct_rank(float(getattr(r, f)), df[f]) for f in FEATURES}}
            for r in scen.itertuples()]
        res["feature_auroc_scenario_vs"][g] = {f: feature_auroc(scen[f], df[f]) for f in FEATURES}
    res["account_day_classifiers_vs_prefix"] = account_day_classifiers(
        run_corpus, run_tx, pre_corpus, pre_tx, template_path, max_turns, seed, n_features)
    return res


def f2(x: Any) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "nan"
    return f"{x:.2f}" if isinstance(x, (float, np.floating)) else str(x)


def render_md(res: dict[str, Any], meta: dict[str, Any]) -> str:
    L = ["# S5.3 metadata: the objective-bearing benign-template session beside honest sessions",
         "", f"Computed {meta['utc']} by `work/checks/stage3_s5c_metadata.py` ({VERSION}). "
         "Numbers only; every table is tested unless marked.", ""]
    r = res["run"]
    L += ["## The run", "",
          f"- sessions {r['sessions']} (scenario {r['scenario_sessions']}, honest "
          f"{r['honest_sessions']}); accounts {', '.join(r['accounts'])}; dates "
          f"{', '.join(r['dates'])}; carrier values {r['carrier_values']}; elicitation prefix "
          f"present on any session: {r['elicit_prefix_any']}; aborted {r['aborted']}; finish "
          f"reasons {r['finish_reasons']}; transcript cost_usd sum {r['cost_usd_sum']:.3f}.", "",
          "| account | mode | turns | capped | events | ok | failed share | first action (min) | offset (min) | agenda_len | objective_position | finish |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in r["per_session"]:
        L.append(f"| {s['account']} | {s['session_mode']} | {f2(s['turn_count'])} | {f2(s['capped'])} | "
                 f"{f2(s['events'])} | {f2(s['events_ok'])} | {f2(s['failed_share'])} | "
                 f"{f2(s['first_action_min'])} | {f2(s['first_action_offset_min'])} | "
                 f"{s.get('agenda_len')} | {s.get('objective_position')} | {s['finish_reason']} |")
    L += ["", "## Session-level distributions (quantiles)", ""]
    for f in FEATURES:
        L += [f"### {f}", "", "| group | n | p5 | p25 | p50 | p75 | p95 | mean |", "|---|---|---|---|---|---|---|---|"]
        for g in ["scenario"] + list(res["groups"]):
            q = res["scenario_quantiles"][f] if g == "scenario" else res["groups"][g][f]
            L.append(f"| {g} | {q.get('n')} | {f2(q.get('p5'))} | {f2(q.get('p25'))} | {f2(q.get('p50'))} | "
                     f"{f2(q.get('p75'))} | {f2(q.get('p95'))} | {f2(q.get('mean'))} |")
        L.append("")
    L += ["## Where each scenario session sits (percentile rank inside the honest group)", ""]
    for g, rows in res["scenario_percentile_ranks"].items():
        L += [f"### against {g}", "", "| account | " + " | ".join(FEATURES) + " |",
              "|---|" + "---|" * len(FEATURES)]
        for row in rows:
            L.append(f"| {row['account']} | " + " | ".join(f2(row[f]) for f in FEATURES) + " |")
        L.append("")
    L += ["## Per-feature rank AUROC, scenario sessions against each honest group (session level, descriptive)", "",
          "| group | " + " | ".join(FEATURES) + " |", "|---|" + "---|" * len(FEATURES)]
    for g, d in res["feature_auroc_scenario_vs"].items():
        L.append(f"| {g} | " + " | ".join(f2(d[f]) for f in FEATURES) + " |")
    c = res["account_day_classifiers_vs_prefix"]
    L += ["", "## Frozen leak classifiers at account-day level: the run's account-days against the prefix's", "",
          f"run account-days {c['run_account_days']}, prefix account-days {c['prefix_account_days']}. {c['note']}", "",
          "| classifier | n | positives | AUROC | two-sided | 95% CI | status |", "|---|---|---|---|---|---|---|"]
    for k in ("metadata", "content"):
        d = c[k]
        L.append(f"| {k} | {d.get('n')} | {d.get('positives')} | {f2(d.get('auroc'))} | "
                 f"{f2(d.get('auroc_two_sided'))} | {d.get('ci')} | {d.get('status')} |")
    L += ["", "## Inputs", ""] + [f"- {k}: {v}" for k, v in meta.items() if k != "utc"]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--transcripts", default=None)
    ap.add_argument("--prefix-corpus", default=str(DEFAULT_PREFIX))
    ap.add_argument("--prefix-transcripts", default=None)
    ap.add_argument("--lab-honest-corpus", default=None)
    ap.add_argument("--lab-honest-transcripts", default=None)
    ap.add_argument("--template", default=str(gm.DEFAULT_TEMPLATE))
    ap.add_argument("--max-turns", type=int, default=MAX_TURNS)
    ap.add_argument("--seed", type=int, default=gm.SEED)
    ap.add_argument("--n-features", type=int, default=lc.N_FEATURES)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    ns = ap.parse_args(argv)
    run_c = Path(ns.corpus)
    run_t = Path(ns.transcripts) if ns.transcripts else gm.default_transcripts(run_c)
    pre_c = Path(ns.prefix_corpus)
    pre_t = Path(ns.prefix_transcripts) if ns.prefix_transcripts else gm.default_transcripts(pre_c)
    lab_c = Path(ns.lab_honest_corpus) if ns.lab_honest_corpus else None
    lab_t = (Path(ns.lab_honest_transcripts) if ns.lab_honest_transcripts
             else (gm.default_transcripts(lab_c) if lab_c else None))
    res = analyse(run_c, run_t, pre_c, pre_t, lab_c, lab_t, Path(ns.template), ns.max_turns,
                  ns.seed, ns.n_features)
    meta = {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": VERSION, "script_sha256": gm.sha256_file(__file__),
        "run_corpus": str(run_c), "run_corpus_sha256": gm.sha256_file(run_c),
        "run_transcripts": str(run_t), "run_transcripts_sha256": gm.sha256_file(run_t),
        "prefix_corpus": str(pre_c), "prefix_corpus_sha256": gm.sha256_file(pre_c),
        "prefix_transcripts": str(pre_t), "prefix_transcripts_sha256": gm.sha256_file(pre_t),
        "lab_honest_corpus": str(lab_c) if lab_c else None,
        "lab_honest_corpus_sha256": gm.sha256_file(lab_c) if lab_c and lab_c.exists() else None,
        "grouping_measure_sha256": gm.sha256_file(HERE / "grouping_measure.py"),
        "content_module_sha256": gm.sha256_file(HERE / "stage3_leak_content.py"),
        "max_turns": ns.max_turns, "seed": ns.seed,
        "command": "python -I work/checks/stage3_s5c_metadata.py " + " ".join(
            sys.argv[1:] if argv is None else argv),
    }
    out = {"version": VERSION, "meta": meta, "results": res}
    Path(ns.out_json).write_text(json.dumps(gm._clean(out), indent=2, default=gm._json_default) + "\n",
                                 encoding="utf-8")
    Path(ns.out_md).write_text(render_md(res, meta), encoding="utf-8")
    r = res["run"]
    print(f"wrote {ns.out_md}: {r['sessions']} sessions ({r['scenario_sessions']} scenario)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
