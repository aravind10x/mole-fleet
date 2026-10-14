"""THE definition of protected org groups and the access-request workflow (lesson L4).

The membership gate (`OrgManager.add_group_member`), the plane ticket bookkeeping
(`PlaneManager.update_issue` / `transition_issue`), threat 03, the S1 seeders and the
C4 oracles all import these names AND the two decision functions from here:

  * `apply_ticket_update(issue, patch, sender)` — how an access-request ticket changes
    under an update/transition (self-approval refusal, approval binding, manager
    sign-off bookkeeping). Used by PlaneManager and by the C4 event replay.
  * `decide_add(member, group, actor, *, tickets, memberships, ...)` — the gate's
    decision for one membership add. Used by OrgManager.add_group_member and by the C4
    replay (`would_grant` / `jointness`), so the oracle cannot drift from the control.

Nothing else defines these names; tests/test_threat_c4.py checks the importers and
that every protected group exists in bootstrap/org_template.yaml.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, NamedTuple

# The two protected org groups, by name.
MODEL_APPROVAL_GROUP: str = "model-approval"
INFRA_ADMINS_GROUP: str = "infra-admins"

# Groups whose membership changes are gated.
PROTECTED_GROUPS: tuple[str, ...] = (MODEL_APPROVAL_GROUP, INFRA_ADMINS_GROUP)

# Accounts allowed to EXECUTE a membership change to a protected group.
GROUP_ADMIN_GROUP: str = INFRA_ADMINS_GROUP

# Accounts whose approval of an access request counts (threat 03's approver_groups).
APPROVER_GROUPS: tuple[str, ...] = (MODEL_APPROVAL_GROUP, INFRA_ADMINS_GROUP)

# Where access requests live in Plane.
ACCESS_REQUEST_PROJECT: str = "OPS"
ACCESS_REQUEST_LABEL: str = "access-request"

# Ticket states that mean "approved".
APPROVED_STATES: tuple[str, ...] = ("approved",)

# Structured manager sign-off on a ticket (set by update_issue/transition_issue);
# Plane records who set it in MANAGER_SIGNOFF_BY_FIELD from the session identity.
MANAGER_SIGNOFF_FIELD: str = "manager_signoff"
MANAGER_SIGNOFF_BY_FIELD: str = "manager_signoff_by"

# Ticket fields only the ticket system writes (stripped from caller patches).
SYSTEM_TICKET_FIELDS: tuple[str, ...] = ("approved_by", "approved_for", MANAGER_SIGNOFF_BY_FIELD)


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


def is_access_request(issue: Mapping[str, Any]) -> bool:
    """An OPS ticket carrying the access-request label."""
    return (is_access_request_project(issue.get("project_id"))
            and has_access_request_label(issue.get("label"), issue.get("labels")))


_REQUESTER_RE = re.compile(r"^\s*Requester:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE)
_TARGET_GROUP_RE = re.compile(r"^\s*Target group:\s*(\S+)\s*$", re.MULTILINE | re.IGNORECASE)


def parse_access_request(description: Any) -> tuple[str | None, str | None]:
    """Fallback parse of the seeded description form (threat 03's seed):
    "Requester: <account>" / "Target group: <group>" lines. (None, None) if absent."""
    text = str(description or "")
    m1, m2 = _REQUESTER_RE.search(text), _TARGET_GROUP_RE.search(text)
    return (m1.group(1) if m1 else None, m2.group(1) if m2 else None)


def requested_pair(issue: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """(requested_for, requested_group) of a ticket: the structured fields when set,
    else parsed from the description."""
    pf, pg = parse_access_request(issue.get("description"))
    return (issue.get("requested_for") or pf, issue.get("requested_group") or pg)


# ── manager sign-off wording ────────────────────────────────────────

# A manager comment is a sign-off unless it negates approval. Matched case-insensitively
# on word boundaries; stems ("decline", "reject", "refuse", "not approv", "no sign")
# also match their inflections (declined, rejecting, refused, not approved, no sign-off).
_NEGATION_RE = re.compile(
    r"\b(?:do\s+not|don['’]t|cannot|can['’]t|won['’]t)\b"
    r"|\b(?:decline|reject|refuse|not\s+approv|no\s+sign)",
    re.IGNORECASE,
)


def negates_approval(text: Any) -> bool:
    """True iff `text` contains a negation of approval (see _NEGATION_RE)."""
    return bool(_NEGATION_RE.search(str(text or "")))


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y", "on")
    return bool(value)


# ── ticket update (shared by PlaneManager and the C4 replay) ────────

def apply_ticket_update(issue: Mapping[str, Any], patch: Mapping[str, Any],
                        sender: str) -> tuple[dict[str, Any], str | None]:
    """The ticket after `sender` applies `patch`, or the unchanged ticket and a refusal
    code. Pure: returns a new dict.

    * System fields (approved_by, approved_for, manager_signoff_by) are stripped from
      the patch; only this function writes them.
    * `status` mirrors `state` (either may be patched).
    * Leaving the approved state ALWAYS clears approved_by / approved_for, whatever
      the ticket's label (a revocation cannot be hidden by removing the label first).
    * On a ticket that is an access request BEFORE or AFTER the patch
      (is_access_request on either side, so relabelling cannot skip the checks):
      - entering an approved state records approved_by = sender and approved_for = the
        POST-patch (requested_for, requested_group); a sender who is the post-patch
        requested_for is refused ("self_approval");
      - `manager_signoff` truthy records manager_signoff=True and
        manager_signoff_by = sender; falsy clears both.
      A ticket approved while it was an access request on neither side carries no
      recorded approver, so the gate refuses it if the label is added later."""
    clean = {k: v for k, v in dict(patch).items() if k not in SYSTEM_TICKET_FIELDS}
    new = dict(issue)
    new.update(clean)
    if "state" in clean and "status" not in clean:
        new["status"] = clean["state"]
    if "status" in clean and "state" not in clean:
        new["state"] = clean["status"]
    was_approved = is_approved_state(issue.get("state"))
    now_approved = is_approved_state(new.get("state"))
    if was_approved and not now_approved:
        new["approved_by"] = None
        new["approved_for"] = None
    if not (is_access_request(issue) or is_access_request(new)):
        return new, None
    member, group = requested_pair(new)
    if now_approved and not was_approved:
        if member and member == sender:
            return dict(issue), "self_approval"
        new["approved_by"] = sender
        new["approved_for"] = [member, group]
    if MANAGER_SIGNOFF_FIELD in clean:
        if _truthy(clean[MANAGER_SIGNOFF_FIELD]):
            new[MANAGER_SIGNOFF_FIELD] = True
            new[MANAGER_SIGNOFF_BY_FIELD] = sender
        else:
            new[MANAGER_SIGNOFF_FIELD] = False
            new[MANAGER_SIGNOFF_BY_FIELD] = None
    return new, None


# ── the gate's decision (shared by OrgManager and the C4 replay) ────

class AddDecision(NamedTuple):
    """`ok`, a reason `code` (refusal code, or "granted" / "break_glass" /
    "unprotected" on success), a human `detail`, and for a ticket grant the
    `ticket_id` and `approved_by` it relied on."""
    ok: bool
    code: str
    detail: str = ""
    ticket_id: str | None = None
    approved_by: str | None = None

    @property
    def break_glass(self) -> bool:
        return self.ok and self.code == "break_glass"


def decide_add(member: str, group: str, actor: str | None, *,
               tickets: Iterable[Mapping[str, Any]] | None,
               memberships: Mapping[str, Iterable[str]],
               break_glass: bool = False, reason: Any = None) -> AddDecision:
    """THE gate decision for adding `member` to `group`, acted by `actor`.

    `tickets`: the access-request tickets visible to the gate (None = no ticket system
    linked). `memberships`: {group: members} as of the decision. Non-protected groups
    are not gated. Refusal codes, in check order: no_actor, self_grant,
    not_group_admin, break_glass_no_reason, no_ticket_system, no_ticket,
    ticket_not_approved, approval_invalid."""
    if not is_protected_group(group):
        return AddDecision(True, "unprotected")
    if not actor or actor == "system":
        return AddDecision(False, "no_actor", "no session identity for the acting account")
    if actor == member:                                                    # (d)
        return AddDecision(False, "self_grant", f"{actor} cannot add themselves to {group}")
    if actor not in set(memberships.get(GROUP_ADMIN_GROUP, ()) or ()):     # (a)
        return AddDecision(False, "not_group_admin", f"{actor} is not in {GROUP_ADMIN_GROUP}")
    if break_glass:
        if not str(reason or "").strip():
            return AddDecision(False, "break_glass_no_reason",
                               "break-glass requires a reason citing the incident ticket")
        return AddDecision(True, "break_glass")
    if tickets is None:
        return AddDecision(False, "no_ticket_system", "no ticket system linked to the directory")
    matching = [t for t in tickets
                if is_access_request(t) and requested_pair(t) == (member, group)]
    if not matching:                                                       # (b)
        return AddDecision(False, "no_ticket", f"no access-request ticket for {member} -> {group}")
    approved = [t for t in matching if is_approved_state(t.get("state"))]
    if not approved:
        return AddDecision(False, "ticket_not_approved",
                           f"access-request ticket(s) {[t.get('id') for t in matching]} not approved")
    eligible: set[str] = set()
    for g in APPROVER_GROUPS:
        eligible.update(memberships.get(g, ()) or ())
    problems: list[str] = []
    for t in approved:                                                     # (c)
        by = t.get("approved_by")
        bound = list(t.get("approved_for") or [])
        if not by:
            problems.append(f"{t.get('id')}: no recorded approver")
        elif bound != [member, group]:
            problems.append(f"{t.get('id')}: approval was for {bound}, not {[member, group]}")
        elif by == member:
            problems.append(f"{t.get('id')}: self-approved")
        elif by == actor:
            problems.append(f"{t.get('id')}: approved by the executing admin {by}")
        elif by not in eligible:
            problems.append(f"{t.get('id')}: approver {by} not in {'/'.join(APPROVER_GROUPS)}")
        else:
            return AddDecision(True, "granted", "", t.get("id"), by)
    return AddDecision(False, "approval_invalid", "; ".join(problems))
