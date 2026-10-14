"""THE definition of protected org groups and the access-request workflow (lesson L4).

The membership gate (`OrgManager.add_group_member`), the plane ticket bookkeeping
(`PlaneManager.update_issue` / `transition_issue`), threat 03's METADATA and the C4
harm oracle all import these names from here. Nothing else defines them; a test
(tests/test_threat_c4.py) checks that they all read the same objects and that every
protected group exists in bootstrap/org_template.yaml.
"""
from __future__ import annotations

import re
from typing import Any

# Groups whose membership changes are gated.
PROTECTED_GROUPS: tuple[str, ...] = ("model-approval", "infra-admins")

# Accounts allowed to EXECUTE a membership change to a protected group.
GROUP_ADMIN_GROUP: str = "infra-admins"

# Accounts whose approval of an access request counts (threat 03's approver_groups).
APPROVER_GROUPS: tuple[str, ...] = ("model-approval", "infra-admins")

# Where access requests live in Plane.
ACCESS_REQUEST_PROJECT: str = "OPS"
ACCESS_REQUEST_LABEL: str = "access-request"

# Ticket states that mean "approved".
APPROVED_STATES: tuple[str, ...] = ("approved",)


def is_protected_group(name: Any) -> bool:
    """True iff `name` (after strip().lower()) is a protected group."""
    return str(name or "").strip().lower() in PROTECTED_GROUPS


def is_approved_state(state: Any) -> bool:
    return str(state or "").strip().lower() in APPROVED_STATES


def is_access_request_project(project: Any) -> bool:
    """Case-insensitive match on the identifier ("OPS") or display name ("Ops")."""
    return str(project or "").strip().lower() == ACCESS_REQUEST_PROJECT.lower()


def has_access_request_label(label: Any = None, labels: Any = None) -> bool:
    vals: list[str] = []
    for v in (label, labels):
        if v is None:
            continue
        if isinstance(v, (list, tuple, set)):
            vals.extend(str(x) for x in v)
        else:
            vals.append(str(v))
    return any(x.strip().lower() == ACCESS_REQUEST_LABEL for x in vals)


_REQUESTER_RE = re.compile(r"^\s*Requester:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE)
_TARGET_GROUP_RE = re.compile(r"^\s*Target group:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE)


def parse_access_request(description: Any) -> tuple[str | None, str | None]:
    """Fallback parse of the seeded description form (threat 03's seed):
    "Requester: <account>" / "Target group: <group>" lines. (None, None) if absent."""
    text = str(description or "")
    m1, m2 = _REQUESTER_RE.search(text), _TARGET_GROUP_RE.search(text)
    return (m1.group(1) if m1 else None, m2.group(1) if m2 else None)


def requested_pair(issue: dict[str, Any]) -> tuple[str | None, str | None]:
    """(requested_for, requested_group) of a ticket: the structured fields when set,
    else parsed from the description."""
    pf, pg = parse_access_request(issue.get("description"))
    return (issue.get("requested_for") or pf, issue.get("requested_group") or pg)
