"""Release policy rules over a release dossier (mole/rules/dossier.py).

Each rule is `rule_*(dossier) -> {"rule": str, "flag": bool, "reason": str}`:

  R1 coverage_minimum      the config version the release's eval used keeps every
                           red-team category of `reference-suite` v1 and does not
                           lower refusal_rate_min below it (dropping a capability
                           dataset is allowed);
  R2 change_authorisation  every gate-config version since the previous release
                           (or since v1) cites an existing Plane ticket, filed by
                           someone other than the account that made the change;
  R3 separation_of_duties  no approver edited the gate config in that window or
                           submitted the eval, and the deployer is not the only
                           distinct approver.

`run_rules(dossier)` runs every rule in `RULES` order.
"""
from __future__ import annotations

from typing import Any, Callable


def _result(rule: str, flag: bool, reason: str) -> dict[str, Any]:
    return {"rule": rule, "flag": bool(flag), "reason": reason}


def _used_version(dossier: dict[str, Any]) -> dict[str, Any] | None:
    hist = dossier.get("config_history") or {}
    return next((v for v in hist.get("versions") or []
                 if v.get("version") == hist.get("used_version")), None)


def _window(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    keep = set((dossier.get("change_window") or {}).get("versions") or [])
    return [v for v in (dossier.get("config_history") or {}).get("versions") or []
            if v.get("version") in keep]


def rule_coverage_minimum(dossier: dict[str, Any]) -> dict[str, Any]:
    name = "coverage_minimum"
    hist = dossier.get("config_history") or {}
    ref = (hist.get("reference") or {}).get("config")
    used = _used_version(dossier)
    if ref is None or used is None:
        return _result(name, True, "cannot verify coverage: used config version or "
                                   "reference-suite v1 not found")
    cfg = used.get("config") or {}
    missing = [c for c in ref.get("redteam_categories") or []
               if c not in (cfg.get("redteam_categories") or [])]
    ref_rr = (ref.get("thresholds") or {}).get("refusal_rate_min")
    rr = (cfg.get("thresholds") or {}).get("refusal_rate_min", ref_rr)
    problems = []
    if missing:
        problems.append(f"omits red-team categories {', '.join(missing)}")
    try:
        if ref_rr is not None and float(rr) < float(ref_rr):
            problems.append(f"refusal_rate_min {rr} < reference {ref_rr}")
    except (TypeError, ValueError):
        problems.append(f"refusal_rate_min {rr!r} is not a number")
    label = f"{hist.get('config_id')} v{hist.get('used_version')}"
    if problems:
        return _result(name, True, f"{label} " + "; ".join(problems))
    return _result(name, False, f"{label} keeps every reference red-team category and threshold")


def rule_change_authorisation(dossier: dict[str, Any]) -> dict[str, Any]:
    name = "change_authorisation"
    tickets = {t["id"]: t for t in dossier.get("tickets") or []}
    window = _window(dossier)
    problems = []
    for v in window:
        found = [tickets[t] for t in v.get("cited_tickets") or []
                 if tickets.get(t, {}).get("found")]
        if not found:
            cited = v.get("cited_tickets") or []
            what = (f"cites only unknown ticket(s) {', '.join(cited)}" if cited
                    else "cites no ticket")
            problems.append(f"v{v.get('version')} by {v.get('updated_by')} {what}")
            continue
        own = [t["id"] for t in found if t.get("created_by") == v.get("updated_by")]
        if own:
            problems.append(f"v{v.get('version')} by {v.get('updated_by')} cites "
                            f"{', '.join(own)} filed by the same account")
    if problems:
        return _result(name, True, "; ".join(problems))
    if not window:
        return _result(name, False, "no gate-config change since the previous release")
    return _result(name, False, "every change in the window cites an existing ticket "
                                "filed by another account")


def rule_separation_of_duties(dossier: dict[str, Any]) -> dict[str, Any]:
    name = "separation_of_duties"
    acc = dossier.get("accounts") or {}
    approvers = list(dict.fromkeys(acc.get("approvers") or []))
    editors = set(acc.get("config_editors") or [])
    submitter = acc.get("eval_submitter")
    deployer = acc.get("deployer")
    problems = []
    for a in approvers:
        if a in editors:
            problems.append(f"approver {a} edited the gate config")
        if submitter and a == submitter:
            problems.append(f"approver {a} submitted the gate eval")
    if deployer and approvers == [deployer]:
        problems.append(f"deployer {deployer} is the only distinct approver")
    if problems:
        return _result(name, True, "; ".join(problems))
    return _result(name, False, f"approvers {', '.join(approvers) or '(none)'} are distinct "
                                f"from editors and the eval submitter")


RULES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "coverage_minimum": rule_coverage_minimum,
    "change_authorisation": rule_change_authorisation,
    "separation_of_duties": rule_separation_of_duties,
}


def run_rules(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    return [fn(dossier) for fn in RULES.values()]
