#!/usr/bin/env python3
"""External density anchor: honest pair-interaction density of a real human ticket tracker.

The metric is the B1 "honest pair-interaction density" of `haystack.py` (TRACK-B part 1,
section 5), restricted to the single artefact type a tracker export has (the issue):
for each calendar day d (UTC), among the accounts active in the trailing window
[d - w + 1, d], the share of unordered pairs (a, b) that both made a WRITE touch on the
same issue inside that window (L1 > 0). The tracker export has no read events, so the
any-touch density (W > 0) equals the write co-touch density and is not reported apart.

Dataset: the Apache Software Foundation Jira (https://issues.apache.org/jira), the
Apache instance of the Public Jira Dataset (Montgomery, Lueders, Maalej, MSR 2022), read
through its public REST API for one four-week window (the full Zenodo dump is 5.8 GB).

Adapter (one write touch per row, artefact = issue key):
- create:        issue `creator` at `created`;
- comment:       comment `author` at comment `created`;
- comment_edit:  comment `updateAuthor` at comment `updated`, when updated - created > 60 s
                 and the edit is not part of an admin bulk operation (below);
- change:        one changelog history entry (status, resolution, assignee, any field
                 edit, link, attachment ...) by its `author` at its `created`; entries
                 without an author, and admin bulk operations (every item an
                 `Admin-*` field), are dropped, with comment edits stamped by the
                 same account within 5 minutes of such an operation. `change_status` marks entries that touch
                 the `status` field.
Votes and watches carry no timestamp in the export and are not counted.

Two modes (the data directory is untrusted: absolute paths, run with -I, never from it):

    # fetch (one sequential crawl, ~165 pages of 100 issues; gzip JSON per page)
    work/mole-fork/.venv/bin/python -I work/checks/external_density_anchor.py fetch \\
        --since 2026-08-30 --out-dir /abs/work/external-data/apache-jira-2026-09 \\
        --log-file /abs/work/stage2/density-anchor.fetch-log.json

    # measure
    work/mole-fork/.venv/bin/python -I work/checks/external_density_anchor.py measure \\
        --inputs /abs/work/external-data/apache-jira-2026-09/page_*.json.gz \\
        --start 2026-08-31 --end 2026-09-27 \\
        --out-json /abs/work/stage2/density-anchor.json \\
        --out-md /abs/work/stage2/density-anchor.tables.md
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

import numpy as np

SEARCH_URL = "https://issues.apache.org/jira/rest/api/2/search"
FIELDS = "project,created,reporter,creator,comment,status,issuetype"
SEED = 20261014
#: Accounts treated as automation. Matched (case-insensitive) on the account name and on
#: the display name. Curated from the top of the activity ranking of the crawl.
BOT_RE = re.compile(
    r"(\bbot\b|bot$|^bot|hudson|jenkins|githubbot|asf subversion|git services|"
    r"automation|jira-?bot|\bci\b|buildbot|sonar|dependabot|renovate|"
    r"infra-?jira|jiraadmin|^qa$|\bgit\b)", re.I)
TOPN = (50, 100, 150, 300)


# ----------------------------------------------------------------------------- fetch
def fetch(args: argparse.Namespace) -> None:
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    jql = f'updated >= "{args.since}" ORDER BY key ASC'
    start, page, total = 0, 0, None
    log = []
    while total is None or start < total:
        q = urllib.parse.urlencode({"jql": jql, "startAt": start, "maxResults": args.page_size,
                                    "fields": FIELDS, "expand": "changelog"})
        url = f"{SEARCH_URL}?{q}"
        for attempt in range(6):
            try:
                req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                           "User-Agent": "density-anchor/1"})
                with urllib.request.urlopen(req, timeout=180) as r:
                    raw = r.read()
                d = json.loads(raw)
                break
            except Exception as e:  # noqa: BLE001
                print(f"page {page} attempt {attempt}: {e}", file=sys.stderr)
                time.sleep(10 * (attempt + 1))
        else:
            raise SystemExit(f"giving up at startAt={start}")
        total = d["total"]
        p = out / f"page_{page:04d}.json.gz"
        with gzip.open(p, "wb") as f:
            f.write(raw)
        n = len(d["issues"])
        log.append({"page": page, "startAt": start, "n": n, "total": total,
                    "bytes": len(raw), "at": datetime.now(timezone.utc).isoformat()})
        print(f"page {page} startAt {start} n {n} total {total} {len(raw)} B", flush=True)
        if n == 0:
            break
        start += n
        page += 1
        time.sleep(args.sleep)
    meta = {"url": SEARCH_URL, "jql": jql, "fields": FIELDS, "expand": "changelog",
            "pages": log, "fetched_at": datetime.now(timezone.utc).isoformat()}
    Path(args.log_file).resolve().write_text(json.dumps(meta, indent=1))


# ----------------------------------------------------------------------------- adapter
def ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone(timezone.utc)


def acct(u: dict | None) -> tuple[str, str] | None:
    if not u:
        return None
    nm = u.get("name") or u.get("key")
    return (nm, u.get("displayName") or "") if nm else None


def events_of_issue(it: dict) -> Iterable[tuple[str, str, str, datetime, str]]:
    """Yield (account, display, issue_key, utc_ts, kind) write touches of one issue."""
    f, key = it["fields"], it["key"]
    # (account, time) of admin bulk operations on this issue: comment edits stamped by the
    # same account within 5 minutes are part of the bulk operation and are dropped too.
    admin = [(h["author"].get("name"), ts(h["created"]))
             for h in (it.get("changelog") or {}).get("histories", [])
             if h.get("author") and h.get("items") and
             all(str(x.get("field", "")).startswith("Admin-") for x in h["items"])]
    a = acct(f.get("creator")) or acct(f.get("reporter"))
    if a and f.get("created"):
        yield a[0], a[1], key, ts(f["created"]), "create"
    for c in (f.get("comment") or {}).get("comments", []):
        a = acct(c.get("author"))
        if a:
            yield a[0], a[1], key, ts(c["created"]), "comment"
        u = acct(c.get("updateAuthor"))
        if u and c.get("updated") and \
                (ts(c["updated"]) - ts(c["created"])).total_seconds() > 60 and \
                not any(n == u[0] and abs((ts(c["updated"]) - t).total_seconds()) < 300
                        for n, t in admin):
            yield u[0], u[1], key, ts(c["updated"]), "comment_edit"
    for h in (it.get("changelog") or {}).get("histories", []):
        a = acct(h.get("author"))
        items = h.get("items", [])
        if not a or (items and all(str(x.get("field", "")).startswith("Admin-") for x in items)):
            continue  # no author, or a Jira admin bulk operation ("Admin-Comment-Bulk ...")
        kind = "change_status" if any(x.get("field") == "status" for x in h.get("items", [])) \
            else "change"
        yield a[0], a[1], key, ts(h["created"]), kind


def load(paths: list[str]) -> tuple[list[tuple], dict[str, Any]]:
    seen: set[str] = set()
    ev: list[tuple] = []
    trunc = {"comment": 0, "changelog": 0}
    proj: dict[str, str] = {}
    for p in sorted(paths):
        with gzip.open(p, "rb") as fh:
            d = json.loads(fh.read())
        for it in d["issues"]:
            if it["key"] in seen:
                continue
            seen.add(it["key"])
            cm = (it["fields"].get("comment") or {})
            if cm.get("total", 0) != len(cm.get("comments", [])):
                trunc["comment"] += 1
            ch = it.get("changelog") or {}
            if ch.get("total", 0) != len(ch.get("histories", [])):
                trunc["changelog"] += 1
            proj[it["key"]] = it["fields"]["project"]["key"]
            ev.extend(events_of_issue(it))
    return ev, {"issues": len(seen), "truncated": trunc, "project_of": proj}


# ----------------------------------------------------------------------------- metric
def pct(x, q):
    return float(np.percentile(x, q)) if len(x) else float("nan")


def density(by_day: dict[date, list[tuple[str, str]]], days: list[date], w: int,
            members: set[str] | None, first_day_idx: int) -> dict[str, Any]:
    """Per-day write co-touch pair density at window w over days[first_day_idx:].
    `by_day[d]` = list of (account, issue). `members` restricts to an induced
    sub-population (events among them only)."""
    shares, nact, npos = [], [], []
    for i in range(first_day_idx, len(days)):
        win_days = days[max(0, i - w + 1): i + 1]
        art: dict[str, set[str]] = defaultdict(set)
        act: set[str] = set()
        for dd in win_days:
            for a, k in by_day.get(dd, ()):
                if members is not None and a not in members:
                    continue
                act.add(a)
                art[k].add(a)
        pairs: set[tuple[str, str]] = set()
        for s in art.values():
            if len(s) > 1:
                pairs.update(combinations(sorted(s), 2))
        na = len(act)
        npairs = na * (na - 1) / 2
        shares.append(len(pairs) / npairs if npairs else np.nan)
        nact.append(na)
        npos.append(len(pairs))
    sh = np.array(shares, dtype=float)
    return {"w": w, "n_days": len(shares), "L1_mean": float(np.nanmean(sh)) if np.isfinite(sh).any()
            else float("nan"), "L1_p50": float(np.nanmedian(sh)) if np.isfinite(sh).any()
            else float("nan"), "L1_min": float(np.nanmin(sh)) if np.isfinite(sh).any()
            else float("nan"), "L1_max": float(np.nanmax(sh)) if np.isfinite(sh).any()
            else float("nan"),
            "days_with_pairs_defined": int(np.isfinite(sh).sum()),
            "active_mean": float(np.mean(nact)), "active_p50": pct(nact, 50),
            "pairs_pos_mean": float(np.mean(npos)),
            "per_day": [{"day": days[first_day_idx + j].isoformat(), "active": nact[j],
                         "pairs_pos": npos[j], "share": None if not np.isfinite(sh[j])
                         else float(sh[j])} for j in range(len(shares))]}


def churn(by_day, days, members) -> dict[str, Any]:
    per = []
    for d in days:
        c = Counter(a for a, _ in by_day.get(d, ()) if members is None or a in members)
        per.extend(c.values())
    return {"account_days": len(per), "writes": int(sum(per)),
            "writes_per_account_day_mean": float(np.mean(per)) if per else float("nan"),
            "p50": pct(per, 50), "p90": pct(per, 90)}


def measure(args: argparse.Namespace) -> None:
    t0 = time.time()
    ev, info = load(args.inputs)
    d0, d1 = date.fromisoformat(args.start), date.fromisoformat(args.end)
    days = [d0 + timedelta(i) for i in range((d1 - d0).days + 1)]
    dayset = set(days)
    ev = [e for e in ev if e[3].date() in dayset]
    disp = {}
    for a, dn, *_ in ev:
        disp[a] = dn
    bots = sorted(a for a, dn in disp.items() if BOT_RE.search(a) or BOT_RE.search(dn))
    kinds_all = Counter(e[4] for e in ev)
    bot_writes = sum(1 for e in ev if e[0] in set(bots))
    proj_of = info["project_of"]

    def build(evs):
        bd: dict[date, list] = defaultdict(list)
        for a, _, k, t, _ in evs:
            bd[t.date()].append((a, k))
        return bd

    def block(evs, label):
        bd = build(evs)
        cnt = Counter(e[0] for e in evs)
        ranked = [a for a, _ in sorted(cnt.items(), key=lambda x: (-x[1], x[0]))]
        accts = sorted(cnt)
        rnd = set(random.Random(SEED).sample(accts, 50)) if len(accts) >= 50 else set(accts)
        pops: list[tuple[str, set | None]] = [("all", None)]
        pops += [(f"top{n}", set(ranked[:n])) for n in TOPN if n < len(ranked)]
        pops += [("random50", rnd)]
        res = {"label": label, "events": len(evs), "accounts": len(accts),
               "issues_touched": len({e[2] for e in evs}),
               "kinds": dict(Counter(e[4] for e in evs)), "pops": {}}
        for nm, mem in pops:
            res["pops"][nm] = {
                "size": len(accts) if mem is None else len(mem),
                "w1": density(bd, days, 1, mem, 0),
                "w7": density(bd, days, 7, mem, 6),
                "churn": churn(bd, days, mem)}
        return res

    ev_h = [e for e in ev if e[0] not in set(bots)]
    out: dict[str, Any] = {
        "dataset": "ASF Jira (issues.apache.org), public REST API",
        "inputs": [str(Path(p).resolve()) for p in sorted(args.inputs)],
        "range": [args.start, args.end], "timezone": "UTC", "n_days": len(days),
        "issues_in_crawl": info["issues"], "truncated": info["truncated"],
        "events_in_range": len(ev), "kinds_in_range": dict(kinds_all),
        "bots": [{"name": b, "display": disp[b]} for b in bots], "bot_writes": bot_writes,
        "humans": block(ev_h, "bots filtered"),
        "with_bots": block(ev, "bots kept"),
    }
    pc = Counter(proj_of[e[2]] for e in ev_h)
    top_proj = pc.most_common(1)[0][0]
    out["busiest_project"] = block([e for e in ev_h if proj_of[e[2]] == top_proj],
                                   f"project {top_proj} (bots filtered)")
    out["busiest_project"]["project"] = top_proj
    out["top_projects"] = pc.most_common(15)
    out["seconds"] = round(time.time() - t0, 1)
    out["command"] = " ".join(sys.argv)
    Path(args.out_json).write_text(json.dumps(out, indent=1, default=str))
    Path(args.out_md).write_text(render(out))
    print(render(out))


def f(x, nd=4):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n/a"
    if isinstance(x, (int, np.integer)):
        return f"{x:,}"
    return f"{x:.{nd}f}"


def render(o: dict[str, Any]) -> str:
    L = []
    for key in ("humans", "with_bots", "busiest_project"):
        b = o[key]
        L.append(f"#### {b['label']}: {b['accounts']:,} accounts, {b['events']:,} write "
                 f"touches, {b['issues_touched']:,} issues")
        L.append("")
        L.append("| population | N | w | days (defined/all) | active / day (mean) | L1 > 0 density, "
                 "mean over days | p50 | min | max |")
        L.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
        for nm, p in b["pops"].items():
            for wk in ("w1", "w7"):
                r = p[wk]
                L.append(f"| {nm} | {p['size']:,} | {r['w']} | {r['days_with_pairs_defined']}/{r['n_days']} | "
                         f"{f(r['active_mean'], 1)} | {f(r['L1_mean'])} | {f(r['L1_p50'])} | "
                         f"{f(r['L1_min'])} | {f(r['L1_max'])} |")
        L.append("")
        L.append("| population | account-days | writes | writes / account-day mean | p50 | p90 |")
        L.append("|---|---:|---:|---:|---:|---:|")
        for nm, p in b["pops"].items():
            c = p["churn"]
            L.append(f"| {nm} | {c['account_days']:,} | {c['writes']:,} | "
                     f"{f(c['writes_per_account_day_mean'], 2)} | {f(c['p50'], 1)} | "
                     f"{f(c['p90'], 1)} |")
        L.append("")
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    fa = sub.add_parser("fetch")
    fa.add_argument("--since", required=True)
    fa.add_argument("--out-dir", required=True)
    fa.add_argument("--log-file", required=True, help="fetch log JSON (outside the data dir)")
    fa.add_argument("--page-size", type=int, default=100)
    fa.add_argument("--sleep", type=float, default=1.0)
    ma = sub.add_parser("measure")
    ma.add_argument("--inputs", nargs="+", required=True)
    ma.add_argument("--start", required=True, help="first UTC day, YYYY-MM-DD")
    ma.add_argument("--end", required=True, help="last UTC day, inclusive")
    ma.add_argument("--out-json", required=True)
    ma.add_argument("--out-md", required=True)
    a = ap.parse_args()
    fetch(a) if a.mode == "fetch" else measure(a)


if __name__ == "__main__":
    main()
