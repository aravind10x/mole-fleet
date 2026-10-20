#!/usr/bin/env python3
"""Run-level summary of the S5.3 placeholder run (numbers only; no transcript text printed).

    python3 -I summarise_run.py <audit jsonl> [<transcripts jsonl>] [<manifest json>]

Prints: manifest fields of interest; session_mode and carrier counts; per-session
wall-clock span (from the audit rows' real wall_ts grouped by task_id), the session-phase
wall-clock (first to last audit wall_ts) and sessions per hour; failed-event share; the
placeholder's effect on state (owncloud writes to /shared/README.md per session, exit code 0).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def _wall(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def main(argv: list[str]) -> int:
    audit = Path(argv[1])
    tx = Path(argv[2]) if len(argv) > 2 else audit.with_name(audit.name.replace(".jsonl", ".transcripts.jsonl"))
    man = Path(argv[3]) if len(argv) > 3 else audit.with_name(audit.name + ".resume.json")
    out: dict = {}
    if man.exists():
        m = json.loads(man.read_text())
        keys = ("sandbox_mode", "session_id", "objective_carrier", "elicit_share", "start_date", "n_days")
        out["manifest"] = {k: m.get(k) for k in keys}
        out["manifest_days"] = [{k: d.get(k) for k in ("date", "sessions_planned", "completed", "aborted",
                                                        "attack_sessions_planned", "attack_sessions_completed",
                                                        "sessions_ok", "snapshot_ok", "managers_ok")}
                                for d in m.get("days", [])]
        co = m.get("coalitions") or {}
        out["manifest_coalitions"] = [{"id": i.get("id"), "roles": [(r.get("role"), r.get("account"),
                                                                     r.get("planned_role_day"), r.get("persona_found"))
                                                                    for r in i.get("roles", [])]}
                                      for i in co.get("instances", [])]
    rows = [json.loads(l) for l in audit.read_text().splitlines() if l.strip()]
    out["audit_rows"] = len(rows)
    out["failed_rows"] = sum(1 for r in rows if r.get("exit_code") != 0)
    out["failed_share"] = round(out["failed_rows"] / max(1, len(rows)), 4)
    out["events_by_service"] = dict(Counter(r.get("service") for r in rows).most_common())
    walls = defaultdict(list)
    for r in rows:
        if r.get("wall_ts") and r.get("task_id"):
            walls[r["task_id"]].append(_wall(r["wall_ts"]))
    spans = {t: (min(v), max(v)) for t, v in walls.items()}
    if spans:
        t0 = min(a for a, _ in spans.values())
        t1 = max(b for _, b in spans.values())
        phase_h = (t1 - t0).total_seconds() / 3600
        out["session_phase"] = {"first_event_wall": t0.isoformat(), "last_event_wall": t1.isoformat(),
                                "hours": round(phase_h, 3)}
    readme = defaultdict(lambda: {"writes_ok": 0, "writes_failed": 0, "reads_ok": 0})
    for r in rows:
        if r.get("service") != "owncloud":
            continue
        args = r.get("args") or {}
        path = str(args.get("path") or args.get("remote_path") or args.get("file_path") or r.get("resource_id") or "")
        if "README" not in path:
            continue
        act = str(r.get("action") or "")
        key = r.get("task_id")
        if "write" in act or "upload" in act or "put" in act or "create" in act:
            readme[key]["writes_ok" if r.get("exit_code") == 0 else "writes_failed"] += 1
        else:
            readme[key]["reads_ok"] += r.get("exit_code") == 0
    sessions = []
    if tx.exists():
        for l in tx.read_text().splitlines():
            if not l.strip():
                continue
            e = json.loads(l)
            t = e.get("task_id")
            a, b = spans.get(t, (None, None))
            sessions.append({
                "account": e.get("account"), "task_id": t, "sim_ts": e.get("sim_ts"),
                "session_mode": e.get("session_mode"), "carrier": e.get("carrier"),
                "elicit_prefix": e.get("elicit_prefix"), "agenda_len": e.get("agenda_len"),
                "objective_position": e.get("objective_position"),
                "turn_count": e.get("turn_count"), "finish_reason": e.get("finish_reason"),
                "aborted_reason": e.get("aborted_reason"), "cost_usd": e.get("cost_usd"),
                "input_tokens": e.get("input_tokens"), "output_tokens": e.get("output_tokens"),
                "events": len(walls.get(t, [])),
                "wall_minutes": round((b - a).total_seconds() / 60, 1) if a and b else None,
                "readme": dict(readme.get(t, {})) or None,
            })
        out["sessions"] = sessions
        out["session_mode_counts"] = dict(Counter(s["session_mode"] for s in sessions))
        out["carrier_counts"] = dict(Counter(str(s["carrier"]) for s in sessions))
        out["cost_usd_sum"] = round(sum(s["cost_usd"] or 0 for s in sessions), 4)
        if "session_phase" in out and out["session_phase"]["hours"] > 0:
            out["sessions_per_hour"] = round(len(sessions) / out["session_phase"]["hours"], 2)
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
