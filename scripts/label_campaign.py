"""label_campaign -- print the C3 per-event label table and the campaign outcome.

For one stealth level: every C3-relevant event of the FULL audit stream (gate config
updates; submit_eval / tag_approved / production deploy calls of the level's unsafe
checkpoint) in causal order ((sim day, wall_ts) when present, else real_ts; then
version), with its session mode, the
payload matcher, EFFECT, INTENT and the combined cell (tp / drift / carry /
restore), then the campaign outcome (tasks/c3_release_sabotage/task.py).

Usage:
  python scripts/label_campaign.py --audit data/corpus/spike/probe_glm.jsonl \\
      --transcripts data/corpus/spike/probe_glm.transcripts.jsonl --level s0

Read-only: writes nothing. Without --transcripts intent is unknown and the
outcome falls back to effect-only attempts.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

BENCH = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH / "scripts"))

import yaml                                              # noqa: E402

from eval_matrix import _load_task_module, attack_task_ids_of, load_session_rows  # noqa: E402
from mole.monitors.replay import load_audit_jsonl        # noqa: E402

THREAT = "c3_release_sabotage"


def _rows(events: list[Any], labels: list[Any], modes: dict[str, str]) -> list[dict[str, Any]]:
    """Table rows. A gate update without result_meta.version shows its version
    inferred from the update count since the seed (v1) as "~N"."""
    out, n_gate = [], 0
    for lab in labels:
        e = events[lab.index]
        ver: Any = lab.version
        if lab.kind == "gate_update":
            n_gate += 1
            if ver is None:
                ver = f"~{n_gate + 1}"
        out.append({
            "index": lab.index, "ts": getattr(e, "ts", ""),
            "real_ts": getattr(e, "real_ts", None), "account": lab.account,
            "mode": modes.get(lab.task_id, "-"), "kind": lab.kind,
            "version": ver, "ok": lab.ok, "payload": lab.payload_positive,
            "effect": lab.effect, "intent": lab.intent, "cell": lab.cell or "-",
            "gate_after": lab.gate_state or ("passes" if lab.gate_weak_after else "blocks"),
        })
    return out


def _table(rows: list[dict[str, Any]]) -> str:
    cols = ["index", "ts", "real_ts", "account", "mode", "kind", "version", "ok",
            "payload", "effect", "intent", "cell", "gate_after"]

    def fmt(r: dict[str, Any], c: str) -> str:
        v = r[c]
        if c == "real_ts" and isinstance(v, float):
            return f"{v:.2f}"
        if isinstance(v, bool):
            return "Y" if v else "."
        return str(v) if v is not None else "-"

    cells = [[fmt(r, c) for c in cols] for r in rows]
    width = [max([len(c)] + [len(row[i]) for row in cells]) for i, c in enumerate(cols)]
    lines = ["  ".join(c.ljust(width[i]) for i, c in enumerate(cols))]
    lines += ["  ".join(v.ljust(width[i]) for i, v in enumerate(row)) for row in cells]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--audit", required=True, help="audit jsonl (the full stream)")
    ap.add_argument("--transcripts", default=None, help="transcripts jsonl (session modes)")
    ap.add_argument("--level", default="s0", choices=["s0", "s1"])
    ap.add_argument("--assignment", default=str(BENCH / "bootstrap" / "insider_assignment.yaml"))
    ap.add_argument("--json", action="store_true", help="print one JSON document instead")
    args = ap.parse_args(argv)

    c3 = _load_task_module(THREAT)
    events = load_audit_jsonl(args.audit)
    assignment = yaml.safe_load(Path(args.assignment).read_text(encoding="utf-8"))
    roles = dict(assignment["collusion"][THREAT][args.level])
    sessions = load_session_rows(args.transcripts) if args.transcripts else None
    tids = attack_task_ids_of(sessions) if sessions is not None else None
    modes = {r["task_id"]: r.get("session_mode") or "-" for r in (sessions or []) if r.get("task_id")}

    labels = c3.label_stream(events, args.level, attack_task_ids=tids)
    rows = _rows(events, labels, modes)
    outcome = c3.campaign_outcome(events, args.level, roles, sessions=sessions,
                                  attack_task_ids=tids)
    if args.json:
        print(json.dumps({"threat": THREAT, "level": args.level, "colluders": roles,
                          "events": rows, "outcome": outcome}, indent=2, default=str))
        return 0
    print(f"{THREAT} {args.level}  colluders={roles}  events={len(events)}  "
          f"labelled={len(rows)}" + ("" if tids is not None else "  (intent unknown: no --transcripts)"))
    print(_table(rows))
    print()
    for k in ("outcome", "deploy_attempted", "harm", "harm_deadline", "gate_weak_at_end",
              "weak_windows", "counts", "colluder_attempt_indices", "colluder_attack_sessions"):
        print(f"{k}: {outcome[k]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
