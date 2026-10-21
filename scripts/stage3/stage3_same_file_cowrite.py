#!/usr/bin/env python3
"""Same-file honest co-write density on MOLE's eight released corpora (brief 07, task S3).

What: for each released corpus, per simulated day, over honest accounts only:
  * the max over files of the share of honest active accounts that wrote that file
    (median over days = the round-1 "median daily max share of active accounts writing the
    same file", recomputed here so the number is tested, not only observed);
  * writes on that day's hottest file; the max share of honest active accounts reading one file;
  * the share of honest writer account-days that have a same-day co-writer on the same file
    (the round-1 co-write share);
  * files with at least two honest writers that day (the G1 file groups at w = 1, all-services
    scope: the released-corpus analogue of the rung-1 room statistic), and whether the hottest
    file's writer count exceeds budget_cap(B, N_active) at B = 0.05 and 0.10.
Each by file type (commit = GitLab `commit` by (project, path); owncloud = `write_file` by path)
and pooled (a commit file and an ownCloud file are different documents).

Why: rung 1's density bar is set at the released corpora's densest same-file co-write share;
the rung-1 comparison table needs that number recomputed with a saved script (lesson L8: the
honest world's routes are measured, not assumed).

Honest = an account with no row in the labels parquet on any day (the S6 primary rule).
Active = an account with at least one exit_code == 0 event that day (any service).
Reads: GitLab `read_file` by (project, path); ownCloud `read_file` and `read_bytes` by path.
Successful events only. Days are ts[:10].

Untrusted data: the parquet files are read as data only; paths are arguments; run with
`python -I`. No network, no API calls, $0.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_same_file_cowrite.py \\
        --data-dir /abs/work/upstream-data --out-json /abs/work/stage3/rung1-released-cowrite.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

CORPORA: tuple[str, ...] = tuple(
    f"{m}_{k}" for m in ("gpt53", "kimi_k26", "deepseek_v4_flash", "qwen36_27b")
    for k in ("single_day", "multiday"))
BUDGETS: tuple[float, ...] = (0.05, 0.10)

#: (service, action) -> (file type, role); the file key is built by `file_key`.
DOC_ACTIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("gitlab", "commit"): ("commit", "write"),
    ("gitlab", "read_file"): ("commit", "read"),
    ("owncloud", "write_file"): ("owncloud", "write"),
    ("owncloud", "append_to_file"): ("owncloud", "write"),     # brief 07e E1: line-level edits
    ("owncloud", "replace_in_file"): ("owncloud", "write"),    # (full content in the row's args)
    ("owncloud", "read_file"): ("owncloud", "read"),
    ("owncloud", "read_bytes"): ("owncloud", "read"),
}

#: Round-1 numbers (work/stage3-opus-review-2026-10-20.md lines 120-126), observed:
#: corpus family -> {"cowrite": (commit, owncloud), "median_daily_max": (commit, owncloud)}.
ROUND1: dict[str, dict[str, tuple[float, float]]] = {
    "kimi": {"cowrite": (0.52, 0.46), "median_daily_max": (0.099, 0.111)},
    "gpt53": {"cowrite": (0.28, 0.095), "median_daily_max": (0.051, 0.034)},
    "deepseek": {"cowrite": (0.87, 0.91), "median_daily_max": (0.236, 0.357)},
    "qwen": {"cowrite": (0.49, 0.25), "median_daily_max": (0.070, 0.064)},
}


def budget_cap(B: float, n_active: int) -> int:
    """max(1, floor(B * N_active)): the grouping_measure / generators convention."""
    return max(1, int(math.floor(B * n_active + 1e-9)))


def family(corpus: str) -> str:
    return {"kimi": "kimi", "gpt53": "gpt53", "deepseek": "deepseek", "qwen36": "qwen"}[corpus.split("_")[0]]


def parse_args(s: Any) -> dict[str, Any]:
    """The args cell as a dict (JSON string or dict); {} when unparseable (data, not code)."""
    if isinstance(s, dict):
        return s
    try:
        v = json.loads(s) if isinstance(s, str) else {}
    except (json.JSONDecodeError, TypeError):
        return {}
    return v if isinstance(v, dict) else {}


def file_key(service: str, args: dict[str, Any]) -> str | None:
    """Document identity: GitLab (project, path); ownCloud path. None if the path is missing."""
    path = args.get("path")
    if not isinstance(path, str) or not path.strip():
        return None
    if service == "gitlab":
        proj = args.get("project")
        return f"{proj}:{path.strip()}" if isinstance(proj, (str, int)) else None
    return path.strip()


def day_stats(writes: pd.DataFrame, reads: pd.DataFrame, active: dict[str, set[str]]
              ) -> list[dict[str, Any]]:
    """Per-day statistics for one file type (or pooled). `writes`/`reads` have columns
    day, account, file (honest, successful). `active[day]` = honest active accounts."""
    out = []
    wg = {d: g for d, g in writes.groupby("day")} if len(writes) else {}
    rg = {d: g for d, g in reads.groupby("day")} if len(reads) else {}
    for d in sorted(active):
        n_act = len(active[d])
        if n_act == 0:
            continue
        w = wg.get(d)
        r = rg.get(d)
        row: dict[str, Any] = {"day": d, "n_active": n_act}
        if w is not None and len(w):
            writers_per_file = w.groupby("file")["account"].nunique()
            writes_per_file = w.groupby("file").size()
            hot = writers_per_file.sort_values(ascending=False, kind="stable").index[0]
            row["max_writers_one_file"] = int(writers_per_file.max())
            row["max_writer_share"] = float(writers_per_file.max() / n_act)
            row["writes_on_hottest_file"] = int(writes_per_file[hot])
            row["files_with_2plus_writers"] = int((writers_per_file >= 2).sum())
            # writer account-days with a same-day co-writer on the same file
            multi = set(writers_per_file[writers_per_file >= 2].index)
            wad = w.drop_duplicates(["account", "file"])
            co = wad[wad["file"].isin(multi)]["account"].nunique()
            row["writer_account_days"] = int(w["account"].nunique())
            row["writer_ad_with_cowriter"] = int(co)
            for B in BUDGETS:
                row[f"hottest_exceeds_cap_B{B:.2f}"] = bool(writers_per_file.max() > budget_cap(B, n_act))
        else:
            row.update({"max_writers_one_file": 0, "max_writer_share": 0.0, "writes_on_hottest_file": 0,
                        "files_with_2plus_writers": 0, "writer_account_days": 0,
                        "writer_ad_with_cowriter": 0})
            for B in BUDGETS:
                row[f"hottest_exceeds_cap_B{B:.2f}"] = False
        if r is not None and len(r):
            row["max_reader_share"] = float(r.groupby("file")["account"].nunique().max() / n_act)
        else:
            row["max_reader_share"] = 0.0
        out.append(row)
    return out


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Medians over days and the pooled co-write share (sum over days)."""
    if not rows:
        return {}
    def med(k: str) -> float:
        return float(np.median([r[k] for r in rows]))
    wad = sum(r["writer_account_days"] for r in rows)
    co = sum(r["writer_ad_with_cowriter"] for r in rows)
    s = {"days": len(rows),
         "median_daily_max_writer_share": med("max_writer_share"),
         "median_daily_max_writers_one_file": med("max_writers_one_file"),
         "median_writes_on_hottest_file": med("writes_on_hottest_file"),
         "median_daily_max_reader_share": med("max_reader_share"),
         "median_files_with_2plus_writers": med("files_with_2plus_writers"),
         "mean_files_with_2plus_writers": float(np.mean([r["files_with_2plus_writers"] for r in rows])),
         "cowrite_share": (co / wad) if wad else float("nan"),
         "writer_account_days": wad,
         "median_n_active": med("n_active")}
    for B in BUDGETS:
        s[f"share_days_hottest_exceeds_cap_B{B:.2f}"] = float(np.mean([r[f"hottest_exceeds_cap_B{B:.2f}"] for r in rows]))
    return s


def analyse_corpus(data_dir: Path, corpus: str) -> dict[str, Any]:
    audit = data_dir / "data" / "audit" / corpus / "0000.parquet"
    labels = data_dir / "data" / "labels" / corpus / "0000.parquet"
    lab = pd.read_parquet(labels, columns=["account"])
    labelled = set(lab["account"].astype(str))
    act = pd.read_parquet(audit, columns=["ts", "account"], filters=[("exit_code", "==", 0)])
    act["day"] = act["ts"].astype(str).str[:10]
    act = act[~act["account"].astype(str).isin(labelled)]
    active: dict[str, set[str]] = defaultdict(set)
    for d, a in zip(act["day"], act["account"].astype(str)):
        active[d].add(a)
    del act
    df = pd.read_parquet(audit, columns=["ts", "account", "service", "action", "args"],
                         filters=[("exit_code", "==", 0), ("service", "in", ["gitlab", "owncloud"])])
    keep = [(s, a) in DOC_ACTIONS for s, a in zip(df["service"], df["action"])]
    df = df[keep]
    df = df[~df["account"].astype(str).isin(labelled)]
    recs = []
    for ts, acc, svc, actn, args in zip(df["ts"].astype(str), df["account"].astype(str), df["service"],
                                        df["action"], df["args"]):
        ftype, role = DOC_ACTIONS[(svc, actn)]
        k = file_key(svc, parse_args(args))
        if k is None:
            continue
        recs.append((ts[:10], acc, ftype, role, f"{ftype}|{k}"))
    ev = pd.DataFrame(recs, columns=["day", "account", "ftype", "role", "file"])
    out: dict[str, Any] = {"corpus": corpus, "labelled_accounts": len(labelled),
                           "honest_active_account_days": int(sum(len(v) for v in active.values())),
                           "doc_events": {f"{t}.{r}": int(((ev["ftype"] == t) & (ev["role"] == r)).sum())
                                          for t in ("commit", "owncloud") for r in ("write", "read")},
                           "by_type": {}, "per_day": {}}
    for t in ("commit", "owncloud", "pooled"):
        sel = ev if t == "pooled" else ev[ev["ftype"] == t]
        rows = day_stats(sel[sel["role"] == "write"], sel[sel["role"] == "read"], active)
        out["by_type"][t] = summarise(rows)
        out["per_day"][t] = rows
    fam = family(corpus)
    out["round1_observed"] = {"cowrite_commit": ROUND1[fam]["cowrite"][0],
                              "cowrite_owncloud": ROUND1[fam]["cowrite"][1],
                              "median_daily_max_commit": ROUND1[fam]["median_daily_max"][0],
                              "median_daily_max_owncloud": ROUND1[fam]["median_daily_max"][1],
                              "note": "round 1 reported one number per model family; corpus split not stated"}
    return out


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", required=True, type=Path)
    ap.add_argument("--corpus", action="append", help="limit to these corpora (default all eight)")
    ap.add_argument("--out-json", required=True, type=Path)
    ns = ap.parse_args(list(argv) if argv is not None else None)
    res: dict[str, Any] = {"script": "work/checks/stage3_same_file_cowrite.py",
                           "definitions": {"honest": "no labels row on any day",
                                           "documents": "gitlab.commit by (project, path); owncloud.write_file by path",
                                           "reads": "gitlab.read_file by (project, path); owncloud.read_file/read_bytes by path",
                                           "active": "honest account with any exit_code==0 event that day"},
                           "corpora": {}}
    for c in ns.corpus or CORPORA:
        t0 = time.time()
        res["corpora"][c] = analyse_corpus(ns.data_dir, c)
        s = res["corpora"][c]["by_type"]
        print(f"{c}: {time.time()-t0:.0f}s commit {json.dumps(s['commit'])[:160]} | owncloud "
              f"{json.dumps(s['owncloud'])[:160]}", file=sys.stderr)
    ns.out_json.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
