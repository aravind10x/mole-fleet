"""Honest churn / entropy statistics per corpus (fork audit JSONL or released parquet).

For each corpus, over successful events only (exit_code == 0), restricted to a service set
(default: the fork's five in-process services, so fork and released corpora compare like for
like) and with an optional account exclusion list (e.g. the eight upstream colluders).

Unit: account-day = (account, ts[:10]).

Read/write rule (documented, checkable via the printed action table):
    An action is a READ if it matches one of the prefixes list_, get_, lookup_, find_, read
    (so read_inbox, read_file, readme... all count), or is one of
        whoami, baseline, recent_logs, exists, latest_approved, download_weights,
        channel_history, im_history, read_inbox, find_emails, project_exists, dir_size.
    Every other action is a WRITE. The rule is a name rule, not a semantic audit; the full
    list of actions seen, with the classification and counts, is printed so a reader can check.

Event order inside an account-day (for write-action sequences): file/row order. In every
corpus used here ts is non-decreasing in file order within an account-day (checked), whereas
real_ts is not (it is non-monotone in 72% of fork account-days), so real_ts is not used.

Usage:
    python honest_churn.py --corpus a.jsonl --corpus b.parquet [--services s1,s2]
        [--exclude acc1,acc2] --out out.json [--md out.md]
Prints a markdown table (one column per corpus) to stdout. Data paths are arguments only;
nothing from the data is executed. No network, no LLM calls.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_SERVICES = "org,plane,model_registry,eval_server,secrets_store"

READ_PREFIXES = ("list_", "get_", "lookup_", "find_", "read")
READ_EXACT = frozenset({
    "whoami", "baseline", "recent_logs", "exists", "latest_approved", "download_weights",
    "channel_history", "im_history", "read_inbox", "find_emails", "project_exists", "dir_size",
})
COLUMNS = ["account", "ts", "service", "action", "exit_code"]


def is_read(action: str) -> bool:
    a = str(action)
    return a in READ_EXACT or a.startswith(READ_PREFIXES)


def is_write(action: str) -> bool:
    return not is_read(action)


# ----------------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------------

def corpus_label(path: str) -> str:
    p = Path(path)
    if p.suffix == ".parquet":
        return p.parent.name if p.stem.isdigit() else p.stem
    return p.stem


def _finish(df: pd.DataFrame, services: set[str], exclude: set[str]) -> pd.DataFrame:
    df = df[(df["exit_code"] == 0) & df["service"].isin(services)]
    if exclude:
        df = df[~df["account"].isin(exclude)]
    df = df.copy()
    df["day"] = df["ts"].astype(str).str[:10]
    df["ord"] = np.arange(len(df))
    return df.drop(columns=["ts"]).reset_index(drop=True)


def load_jsonl(path: str, services: set[str], exclude: set[str]) -> pd.DataFrame:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            if e.get("exit_code") != 0 or e.get("service") not in services:
                continue
            rows.append((e.get("account"), e.get("ts") or "", e.get("service"),
                         e.get("action"), 0))
    df = pd.DataFrame(rows, columns=COLUMNS)
    return _finish(df, services, exclude)


def load_parquet(path: str, services: set[str], exclude: set[str]) -> pd.DataFrame:
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    cols = [c for c in COLUMNS if c in pf.schema_arrow.names]
    parts = []
    for i in range(pf.num_row_groups):
        d = pf.read_row_group(i, columns=cols).to_pandas()
        d = d[(d["exit_code"] == 0) & d["service"].isin(services)]
        if exclude:
            d = d[~d["account"].isin(exclude)]
        for c in ("account", "service", "action"):
            d[c] = d[c].astype("category")
        parts.append(d)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=cols)
    for c in ("account", "service", "action"):
        df[c] = df[c].astype(object)
    return _finish(df, services, exclude)


def load_corpus(path: str, services: set[str], exclude: set[str]) -> pd.DataFrame:
    if str(path).endswith(".parquet"):
        return load_parquet(path, services, exclude)
    return load_jsonl(path, services, exclude)


# ----------------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------------

def shannon_bits(counts) -> float:
    c = np.asarray(list(counts), dtype=float)
    c = c[c > 0]
    if c.size == 0:
        return 0.0
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def dist(x) -> dict:
    x = np.asarray(list(x), dtype=float)
    if x.size == 0:
        return {"mean": None, "p50": None, "p90": None}
    return {"mean": float(x.mean()), "p50": float(np.percentile(x, 50)),
            "p90": float(np.percentile(x, 90))}


def compute(df: pd.DataFrame) -> dict:
    """Metrics for a frame with columns account, day, service, action, ord
    (already filtered to successful in-scope events)."""
    out: dict = {"n_events": int(len(df))}
    if df.empty:
        return out
    df = df.copy()
    df["write"] = df["action"].map(is_write)
    df["sa"] = df["service"].astype(str) + "." + df["action"].astype(str)
    key = ["account", "day"]
    ad_events = df.groupby(key, sort=False).size()
    n_ad = int(len(ad_events))
    out.update({
        "n_account_days": n_ad,
        "n_accounts": int(df["account"].nunique()),
        "n_days": int(df["day"].nunique()),
        "events_per_account_day": dist(ad_events.values),
    })

    # ---- churn: writes per account-day (account-days with zero writes count as 0)
    w = df[df["write"]]
    ad_writes = w.groupby(key, sort=False).size().reindex(ad_events.index, fill_value=0)
    out["n_writes"] = int(len(w))
    out["write_share_of_events"] = float(len(w) / len(df))
    out["writes_per_account_day"] = dist(ad_writes.values)
    by_service = {}
    for svc, g in df.groupby("service"):
        gw = g[g["write"]]
        per_ad = gw.groupby(key, sort=False).size().reindex(ad_events.index, fill_value=0)
        by_service[svc] = {
            "events": int(len(g)), "writes": int(len(gw)),
            "event_share": float(len(g) / len(df)),
            "write_share": float(len(gw) / len(w)) if len(w) else 0.0,
            "writes_per_account_day_mean": float(per_ad.mean()),
            "writes_per_account_day_p50": float(np.percentile(per_ad.values, 50)),
            "writes_per_account_day_p90": float(np.percentile(per_ad.values, 90)),
        }
    out["by_service"] = by_service
    wa = w.groupby(["service", "action"]).size()
    out["writes_per_account_day_by_action"] = {
        f"{s}.{a}": {"count": int(n), "per_account_day": float(n / n_ad)}
        for (s, a), n in wa.sort_values(ascending=False).items()}

    # ---- entropy (a): distinct write-action sequences per account-day
    wsort = w.sort_values(key + ["ord"], kind="stable")
    seqs = wsort.groupby(key, sort=False)["sa"].agg(tuple)
    seq_counter = Counter(seqs.values)
    n_empty = n_ad - int(len(seqs))
    if n_empty:
        seq_counter[()] += n_empty
    out["write_seq_distinct"] = int(len(seq_counter))
    out["write_seq_distinct_share"] = float(len(seq_counter) / n_ad)
    out["write_seq_entropy_bits"] = shannon_bits(seq_counter.values())
    out["write_seq_entropy_max_bits"] = float(math.log2(n_ad)) if n_ad > 1 else 0.0
    out["write_seq_empty_account_days"] = int(n_empty)
    out["write_seq_singleton_share_of_distinct"] = float(
        sum(1 for v in seq_counter.values() if v == 1) / len(seq_counter))

    # ---- entropy (b): distinct (service, action) per account over the run
    per_acct = df.groupby("account")["sa"].nunique()
    out["distinct_pairs_per_account"] = dist(per_acct.values)

    # ---- entropy (c): over all successful events
    pair_counts = df["sa"].value_counts()
    out["distinct_pairs_total"] = int(len(pair_counts))
    out["pair_entropy_bits"] = shannon_bits(pair_counts.values)
    out["pair_entropy_max_bits"] = float(math.log2(len(pair_counts))) if len(pair_counts) > 1 else 0.0

    # ---- classification table
    ac = df.groupby(["service", "action"]).size()
    out["actions_seen"] = [
        {"service": s, "action": a, "class": "write" if is_write(a) else "read", "count": int(n)}
        for (s, a), n in ac.items()]
    return out


# ----------------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------------

def _f(x, nd=2):
    if x is None:
        return "-"
    return f"{x:.{nd}f}"


def render(results: dict[str, dict], services: list[str]) -> str:
    labels = list(results)
    lines: list[str] = []

    def table(title, rows):
        lines.append(f"### {title}")
        lines.append("")
        lines.append("| metric | " + " | ".join(labels) + " |")
        lines.append("|---|" + "---:|" * len(labels))
        for name, fn in rows:
            cells = []
            for lb in labels:
                try:
                    cells.append(fn(results[lb]))
                except (KeyError, TypeError):
                    cells.append("-")
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines.append("")

    d3 = lambda key: [
        (f"{key} mean", lambda r, k=key: _f(r[k]["mean"])),
        (f"{key} p50", lambda r, k=key: _f(r[k]["p50"], 1)),
        (f"{key} p90", lambda r, k=key: _f(r[k]["p90"], 1)),
    ]
    table("Volume", [
        ("successful in-scope events", lambda r: f"{r['n_events']:,}"),
        ("active account-days", lambda r: f"{r['n_account_days']:,}"),
        ("accounts", lambda r: f"{r['n_accounts']:,}"),
        ("days", lambda r: f"{r['n_days']:,}"),
    ] + [(n.replace("events_per_account_day", "events / account-day"), f)
         for n, f in d3("events_per_account_day")])
    table("Churn (successful writes per account-day)", [
        ("writes", lambda r: f"{r['n_writes']:,}"),
        ("write share of events", lambda r: _f(r["write_share_of_events"], 3)),
    ] + [(n.replace("writes_per_account_day", "writes / account-day"), f)
         for n, f in d3("writes_per_account_day")] + [
        (f"{s}: writes / account-day (mean)",
         lambda r, s=s: _f(r["by_service"][s]["writes_per_account_day_mean"], 3))
        for s in services])
    table("Entropy", [
        ("distinct write sequences / account-day", lambda r: _f(r["write_seq_distinct_share"], 3)),
        ("distinct write sequences", lambda r: f"{r['write_seq_distinct']:,}"),
        ("write-sequence entropy (bits)", lambda r: _f(r["write_seq_entropy_bits"], 2)),
        ("  max possible = log2(account-days)", lambda r: _f(r["write_seq_entropy_max_bits"], 2)),
        ("  share of distinct sequences seen once", lambda r: _f(r["write_seq_singleton_share_of_distinct"], 3)),
        ("account-days with no write", lambda r: f"{r['write_seq_empty_account_days']:,}"),
    ] + [(n.replace("distinct_pairs_per_account", "distinct (service, action) / account"), f)
         for n, f in d3("distinct_pairs_per_account")] + [
        ("distinct (service, action) pairs, all", lambda r: f"{r['distinct_pairs_total']}"),
        ("(service, action) entropy over events (bits)", lambda r: _f(r["pair_entropy_bits"], 2)),
        ("  max possible = log2(pairs)", lambda r: _f(r["pair_entropy_max_bits"], 2)),
    ])
    table("Per-service share of events", [
        (s, lambda r, s=s: _f(r["by_service"][s]["event_share"], 3)) for s in services])
    table("Per-service share of writes", [
        (s, lambda r, s=s: _f(r["by_service"][s]["write_share"], 3)) for s in services])

    # writes per account-day by (service, action)
    keys: list[str] = []
    for lb in labels:
        for k in results[lb].get("writes_per_account_day_by_action", {}):
            if k not in keys:
                keys.append(k)
    tot = {k: sum(results[lb].get("writes_per_account_day_by_action", {}).get(k, {}).get("per_account_day", 0)
                  for lb in labels) for k in keys}
    keys.sort(key=lambda k: -tot[k])
    table("Writes per account-day by (service, action)", [
        (k, lambda r, k=k: _f(r["writes_per_account_day_by_action"].get(k, {}).get("per_account_day", 0.0), 3))
        for k in keys])

    # classification table
    acts: dict[tuple[str, str], dict] = {}
    for lb in labels:
        for a in results[lb].get("actions_seen", []):
            e = acts.setdefault((a["service"], a["action"]), {"class": a["class"]})
            e[lb] = a["count"]
    lines.append("### Actions seen and their classification (event counts)")
    lines.append("")
    lines.append("| service | action | class | " + " | ".join(labels) + " |")
    lines.append("|---|---|---|" + "---:|" * len(labels))
    for (s, a), e in sorted(acts.items(), key=lambda kv: (kv[1]["class"], kv[0])):
        lines.append(f"| {s} | {a} | {e['class']} | " + " | ".join(f"{e.get(lb, 0):,}" for lb in labels) + " |")
    lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", action="append", required=True)
    ap.add_argument("--services", default=DEFAULT_SERVICES)
    ap.add_argument("--exclude", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", default=None, help="also write the markdown table to this path")
    a = ap.parse_args(argv)
    services = [s.strip() for s in a.services.split(",") if s.strip()]
    exclude = {x.strip() for x in a.exclude.split(",") if x.strip()}

    results: dict[str, dict] = {}
    for path in a.corpus:
        lb = corpus_label(path)
        if lb in results:
            lb = f"{lb}#{len(results)}"
        print(f"[honest_churn] loading {path}", file=sys.stderr)
        df = load_corpus(path, set(services), exclude)
        results[lb] = compute(df)
        results[lb]["path"] = str(path)
        del df
    payload = {
        "services": services, "excluded_accounts": sorted(exclude),
        "read_rule": {"prefixes": list(READ_PREFIXES), "exact": sorted(READ_EXACT)},
        "corpora": results,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(payload, indent=1))
    md = render(results, services)
    if a.md:
        Path(a.md).write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
