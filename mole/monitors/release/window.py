"""Release deadline and campaign window, from the audit log (sim time only).

deadline  the sim ts of the audited `deploy` call that created the deployment: the row
          whose result_meta.deployment_id matches, else the latest successful deploy row
          with the same checkpoint and environment, else the last ts in the log.
window    (previous release's deadline, this release's deadline]: the previous release is
          the dossier's `previous_release` (the last earlier production deployment under the
          same gate config); with none, the window opens at the start of the log.
"""
from __future__ import annotations

from typing import Any


def deploy_ts(rows: list[dict], deployment: dict[str, Any] | None) -> tuple[str, str]:
    """(deadline ts, source) with source in {"deployment_id", "checkpoint_env", "log_end"}."""
    dep = deployment or {}
    dep_id = dep.get("deployment_id")
    if dep_id:
        for r in rows:
            if r.get("action") == "deploy" and (r.get("result_meta") or {}).get("deployment_id") == dep_id:
                return str(r.get("ts")), "deployment_id"
    cands = [str(r.get("ts")) for r in rows
             if r.get("action") == "deploy" and (r.get("exit_code") or 0) == 0
             and (r.get("args") or {}).get("checkpoint_id") == dep.get("checkpoint_id")
             and (r.get("args") or {}).get("environment") == dep.get("environment")]
    if cands:
        return max(cands), "checkpoint_env"
    return max((str(r.get("ts") or "") for r in rows), default=""), "log_end"


def release_window(rows: list[dict], dossier: dict[str, Any]) -> dict[str, Any]:
    """{"start": exclusive ts or None, "end": inclusive deadline, "end_source", "previous"}."""
    end, src = deploy_ts(rows, dossier.get("deployment"))
    prev = dossier.get("previous_release")
    start = None
    if prev:
        start, _ = deploy_ts(rows, prev)
        if start >= end:                      # a previous release we cannot place before this one
            start = None
    return {"start": start, "end": end, "end_source": src,
            "previous_deployment_id": (prev or {}).get("deployment_id")}


def in_window(ts: Any, window: dict[str, Any]) -> bool:
    t = str(ts or "")
    return (window.get("start") is None or t > window["start"]) and t <= window["end"]
