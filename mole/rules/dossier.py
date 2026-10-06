"""Release dossier: one production deployment, with its provenance.

`build_release_dossier(events, state, deployment)` gathers, for the checkpoint
that `deployment` put into production: the checkpoint record, the release-gate
attestation, the eval job the gate relied on, the gate config's version
history (with diffs against the previous version and against the immutable
`reference-suite`), the Plane tickets cited in config-change reasons, the
audit events that touch any of these, the accounts in each role, and the
previous production release under the same config.

`state` is either a live context (with `.model_registry`, `.eval_server`,
`.plane`) or a loaded `managers.json` dict (keys `model_registry`,
`eval_server`, `plane`, holding the managers' `_`-prefixed fields). A live
context is first snapshotted into the managers.json shape, so both inputs go
through the same code and yield equal dossiers. Everything returned is plain,
JSON-serialisable data with deterministic ordering.
"""
from __future__ import annotations

import json
import re
from typing import Any, Iterable

from ..sandbox.state_export import _STATE_FIELDS
from ..state.eval_server.manager import REFERENCE_SUITE
from ..state.model_registry.manager import PRODUCTION_ENVIRONMENTS

TICKET_RE = re.compile(r"\b[A-Z]{2,6}-\d+\b")
_MANAGERS = ("model_registry", "eval_server", "plane")


# ── state accessors (live ctx or managers.json dict) ───────────────────

def _plain(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def snapshot(state: Any) -> dict[str, Any]:
    """managers.json-shaped dict for the three managers the dossier reads."""
    if isinstance(state, dict):
        return {name: state.get(name) or {} for name in _MANAGERS}
    out: dict[str, Any] = {}
    for name in _MANAGERS:
        mgr = getattr(state, name, None)
        out[name] = ({f: _plain(getattr(mgr, f)) for f in _STATE_FIELDS[name] if hasattr(mgr, f)}
                     if mgr is not None else {})
    return out


def checkpoints(snap: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """{checkpoint_id: record} without private (`_`-prefixed) keys."""
    raw = snap["model_registry"].get("_checkpoints") or {}
    return {cid: {k: v for k, v in rec.items() if not k.startswith("_")}
            for cid, rec in raw.items()}


def approvals(snap: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return dict(snap["model_registry"].get("_approvals") or {})


def deployments(snap: dict[str, Any]) -> list[dict[str, Any]]:
    return list(snap["model_registry"].get("_deployments") or [])


def eval_jobs(snap: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return dict(snap["eval_server"].get("_jobs") or {})


def configs(snap: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """{config_id: {config_id, name, immutable, versions: [...]}}."""
    return dict(snap["eval_server"].get("_configs") or {})


def plane_issues(snap: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """{issue_id: issue} across all Plane workspaces."""
    out: dict[str, dict[str, Any]] = {}
    for ws in (snap["plane"].get("_state") or {}).values():
        out.update((ws or {}).get("issues") or {})
    return out


# ── config diffs ─────────────────────────────────────────────────────

def _tests(cfg: dict[str, Any]) -> list[str]:
    return list(cfg.get("redteam_categories") or []) + list(cfg.get("capability_datasets") or [])


def config_diff(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    """{added_tests, removed_tests, threshold_changes: {name: {from, to}}}."""
    old = old or {}
    before, after = _tests(old), _tests(new)
    t_old = old.get("thresholds") or {}
    t_new = new.get("thresholds") or {}
    return {
        "added_tests": sorted(set(after) - set(before)),
        "removed_tests": sorted(set(before) - set(after)),
        "threshold_changes": {k: {"from": t_old.get(k), "to": t_new.get(k)}
                              for k in sorted(set(t_old) | set(t_new))
                              if t_old.get(k) != t_new.get(k)},
    }


def cited_tickets(text: Any) -> list[str]:
    return sorted(set(TICKET_RE.findall(str(text or ""))))


# ── dossier ──────────────────────────────────────────────────────────

def _job_summary(job: dict[str, Any] | None) -> dict[str, Any] | None:
    if job is None:
        return None
    keys = ("job_id", "checkpoint_id", "kind", "status", "account", "config_id",
            "config_version", "config_hash", "results", "passed", "cost_units")
    return {k: job.get(k) for k in keys}


def _previous_release(deps: list[dict[str, Any]], deployment: dict[str, Any],
                      jobs: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    cfg_id = (deployment.get("gate") or {}).get("config_id")
    ids = [d.get("deployment_id") for d in deps]
    end = ids.index(deployment.get("deployment_id")) if deployment.get("deployment_id") in ids else len(deps)
    for dep in reversed(deps[:end]):
        gate = dep.get("gate") or {}
        env = str(dep.get("environment") or "").strip().lower()
        if env not in PRODUCTION_ENVIRONMENTS or cfg_id is None or gate.get("config_id") != cfg_id:
            continue
        job = jobs.get(gate.get("eval_job_id") or "") or {}
        return {
            "deployment_id": dep.get("deployment_id"),
            "checkpoint_id": dep.get("checkpoint_id"),
            "environment": dep.get("environment"),
            "deployed_by": dep.get("deployed_by"),
            "eval_job_id": gate.get("eval_job_id"),
            "config_version": job.get("config_version", gate.get("config_version")),
        }
    return None


def _mentions(event: Any, patterns: list[re.Pattern[str]]) -> bool:
    blobs = (
        str(getattr(event, "resource_id", "") or ""),
        json.dumps(getattr(event, "args", {}) or {}, sort_keys=True, default=str),
        json.dumps(getattr(event, "result_meta", {}) or {}, sort_keys=True, default=str),
    )
    return any(p.search(b) for p in patterns for b in blobs)


def _id_pattern(ident: str) -> re.Pattern[str]:
    # whole-identifier match: "ckpt-x-v1.1" must not match inside "ckpt-x-v1.1-rc1"
    return re.compile(r"(?<![\w.-])" + re.escape(ident) + r"(?![\w.-])")


def build_release_dossier(events: Iterable[Any], state: Any,
                          deployment: dict[str, Any]) -> dict[str, Any]:
    snap = snapshot(state)
    deployment = _plain(deployment)
    gate = deployment.get("gate") or None
    ckpt_id = deployment.get("checkpoint_id")
    jobs = eval_jobs(snap)
    cfgs = configs(snap)
    issues = plane_issues(snap)

    job = jobs.get((gate or {}).get("eval_job_id") or "")
    cfg_id = (gate or {}).get("config_id") or (job or {}).get("config_id")
    used_version = (job or {}).get("config_version", (gate or {}).get("config_version"))

    # Config history of the gate config, with per-version diffs.
    rec = cfgs.get(cfg_id or "") or {}
    versions: list[dict[str, Any]] = []
    prev_cfg: dict[str, Any] | None = None
    for ver in rec.get("versions") or []:
        versions.append({
            "version": ver.get("version"),
            "updated_by": ver.get("updated_by"),
            "reason": ver.get("reason"),
            "content_hash": ver.get("content_hash"),
            "cited_tickets": cited_tickets(ver.get("reason")),
            "config": ver.get("config"),
            "diff_vs_prev": config_diff(prev_cfg, ver.get("config") or {}) if prev_cfg is not None else None,
        })
        prev_cfg = ver.get("config") or {}
    ref_rec = cfgs.get(REFERENCE_SUITE) or {}
    ref_v1 = next((v for v in ref_rec.get("versions") or [] if v.get("version") == 1), None)
    used = next((v for v in versions if v["version"] == used_version), None)
    reference = ({"config_id": REFERENCE_SUITE, "version": 1,
                  "content_hash": ref_v1.get("content_hash"), "config": ref_v1.get("config")}
                 if ref_v1 else None)
    config_history = {
        "config_id": cfg_id,
        "used_version": used_version,
        "versions": versions,
        "reference": reference,
        "diff_vs_reference": (config_diff(ref_v1.get("config") or {}, used["config"] or {})
                              if ref_v1 and used else None),
    }

    # Change window for authorisation checks: after the previous release's
    # config version (or v1), through the version this release used.
    previous = _previous_release(deployments(snap), deployment, jobs)
    after = (previous or {}).get("config_version") or 1
    window = [v for v in versions
              if isinstance(v["version"], int) and isinstance(used_version, int)
              and after < v["version"] <= used_version]

    # Tickets cited in any reason string (config versions + the eval job).
    cited = set(cited_tickets((job or {}).get("reason")))
    for v in versions:
        cited.update(v["cited_tickets"])
    tickets = []
    for tid in sorted(cited):
        iss = issues.get(tid)
        tickets.append({"id": tid, "found": iss is not None,
                        "name": (iss or {}).get("name"),
                        "created_by": (iss or {}).get("created_by"),
                        "state": (iss or {}).get("state")})

    # Audit events touching the checkpoint, the gate config, the job or a ticket.
    idents = [x for x in (ckpt_id, cfg_id, (job or {}).get("job_id")) if x] + sorted(cited)
    patterns = [_id_pattern(x) for x in idents]
    touched = [e for e in events if patterns and _mentions(e, patterns)]
    touched = sorted(touched, key=lambda e: str(getattr(e, "ts", "")))
    ev_rows = [{"ts": getattr(e, "ts", None), "account": getattr(e, "account", None),
                "service": getattr(e, "service", None), "action": getattr(e, "action", None),
                "exit_code": getattr(e, "exit_code", None)} for e in touched]

    ckpt = checkpoints(snap).get(ckpt_id or "")
    return {
        "deployment": deployment,
        "checkpoint": ckpt,
        "gate": gate,
        "eval_job": _job_summary(job),
        "config_history": config_history,
        "change_window": {"after_version": after, "through_version": used_version,
                          "versions": [v["version"] for v in window]},
        "tickets": tickets,
        "events": ev_rows,
        "accounts": {
            "config_editors": [v["updated_by"] for v in window],
            "eval_submitter": (job or {}).get("account"),
            "approvers": list((gate or {}).get("approvers") or []),
            "deployer": deployment.get("deployed_by"),
            "ticket_filers": {t["id"]: t["created_by"] for t in tickets},
        },
        "previous_release": previous,
    }
