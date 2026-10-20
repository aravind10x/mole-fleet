#!/usr/bin/env python3
"""Post-run measures for the funded GitLab smoke (run2), 2026-10-20.

Computes C1 (throughput), C4 (failed-event share) and C5 (merge-request round
trip) from the run's audit jsonl, plus per-day snapshot sizes (C3) from the
worktree's snapshot dir. Pre-registered definitions are in
work/stage3/gitlab-smoke-agentic-2026-10-20.md; this script only reports
numbers, it never edits anything. Session rows are account_kind ==
'background_llm_agent' (verified against this run's schema, tested 14:4x IST).

Usage: python3 run2_measures.py <worktree> <audit_jsonl_rel_or_abs>
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

SESSION_KIND = "background_llm_agent"
MR_VERBS = ("open_mr", "approve_mr", "merge_mr", "comment_mr", "get_mr", "list_mrs")


def main() -> int:
    wt = Path(sys.argv[1]).resolve()
    audit = Path(sys.argv[2])
    if not audit.is_absolute():
        audit = wt / audit
    rows = [json.loads(l) for l in audit.read_text().splitlines() if l.strip()]
    n = len(rows)

    # C4: failed-event share over all audit rows with an exit code
    coded = [r for r in rows if r.get("exit_code") is not None]
    failed = [r for r in coded if r["exit_code"] != 0]
    print(f"audit rows: {n} (with exit_code: {len(coded)})")
    if coded:
        print(f"C4 failed-event share: {len(failed)}/{len(coded)} = {len(failed)/len(coded):.4f}")

    # C1: session-phase wall-clock from session rows' wall_ts
    sess = [r for r in rows if r.get("account_kind") == SESSION_KIND]
    wall = [datetime.fromisoformat(r["wall_ts"].replace("Z", "+00:00"))
            for r in sess if r.get("wall_ts")]
    if wall:
        span_h = (max(wall) - min(wall)).total_seconds() / 3600
        print(f"session rows: {len(sess)}; wall span {min(wall)} -> {max(wall)} = {span_h:.3f} h")

    # C5: gitlab MR lifecycle events
    git = [r for r in rows if r.get("service") == "gitlab"]
    print(f"gitlab events: {len(git)}")
    print("gitlab action/exit counts:", Counter((r.get("action"), r.get("exit_code")) for r in git).most_common())
    mr = [r for r in git if r.get("action") in MR_VERBS]
    for r in mr:
        print(f"  MR {r.get('account')} {r.get('action')} exit={r.get('exit_code')} "
              f"ts={r.get('ts')} args={json.dumps(r.get('args', {}))[:180]}")

    # C3: snapshot dirs per day
    for cand in (wt / "data/corpus/spike/.snapshots", wt / "data/.snapshots", wt / "data/snapshots"):
        if cand.exists():
            for d in sorted(cand.rglob("day_*")):
                if d.is_dir():
                    total = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
                    print(f"snapshot {d.relative_to(wt)}: {total:,} bytes = {total/1e9:.2f} GB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
