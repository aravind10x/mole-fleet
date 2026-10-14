"""PlaneManager — in-process project/issue tracker backend.

Earlier versions were a thin httpx wrapper around a real Plane (Django
+ Postgres + Redis) container stack. We retired that integration after
hitting an instance-setup chicken-and-egg in Plane 0.22: the API
blocks regular signup on `INSTANCE_NOT_CONFIGURED`, and the only path
to flip `is_setup_done` is a successful first signup, which the same
flag blocks. Even a working bootstrap would pull in 11 containers per
session for what is, in our threats, a thin ticket-tracking surface.

The in-process backend keeps the public method surface identical so
per-threat seed code and oracles don't have to change. State lives
in `self._state` (workspace → {projects, issues, comments}) and is
fully reset on `setup()` / `reset()`. We do NOT record an audit log
inside this manager — the AuditCollector wraps every tool call by the
orchestrator, which is the source of truth oracles read.

Method surface (covers threats 02 credential-exfil ticket workflow,
03 priv-esc access-request queue, 04 fraud reimbursement filings,
plus general background workflow for benign trajectories):

  list_projects()                                → [project, ...]
  create_project(name, identifier, description)  → project dict
  list_issues(project_id)                        → [issue, ...]
  get_issue(ticket_id)                           → issue dict | None
  create_issue(project_id, sender, name, ...)    → issue dict
  update_issue(project_id, issue_id, sender,
               patch)                            → issue dict
  transition_issue(project_id, issue_id, sender,
                   state)                        → issue dict
  add_comment(project_id, issue_id, sender,
              body)                              → comment dict
  list_comments(project_id, issue_id)            → [comment, ...]
  snapshot()                                     → {ticket_id: issue} flat dict
                                                   for threat 04 pre/post diff
"""
from __future__ import annotations

import copy
import logging
import re
from typing import Any

from ..base import StateManager
from ..org.policy import (
    MANAGER_SIGNOFF_BY_FIELD, MANAGER_SIGNOFF_FIELD, apply_ticket_update, requested_pair,
)

logger = logging.getLogger(__name__)


@StateManager.register("plane")
class PlaneManager(StateManager):
    DEFAULT_WORKSPACE = "agentlab"

    NEEDS_SANDBOX = False     # in-process, no docker service required

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._workspace_slug: str = ""
        # workspace_slug → {"projects": {pid: project}, "issues": {iid: issue},
        #                   "comments": {iid: [comment, ...]}}
        self._state: dict[str, dict[str, Any]] = {}
        self._next_issue_seq: int = 1

    async def setup(self, *, sandbox=None) -> None:
        self._workspace_slug = (
            self.config.get("workspace_slug")
            or self.DEFAULT_WORKSPACE
        )
        self._state.setdefault(self._workspace_slug, {
            "projects": {},
            "issues": {},
            "comments": {},
        })
        logger.info(
            "plane manager (in-process) up; workspace=%s",
            self._workspace_slug,
        )

    async def cleanup(self) -> None:
        self._state.clear()
        self._next_issue_seq = 1

    async def reset(self) -> None:
        await self.cleanup()
        await self.setup()

    # ── workspace helpers ─────────────────────────────────────────────

    def _ws(self) -> dict[str, Any]:
        return self._state.setdefault(self._workspace_slug, {
            "projects": {},
            "issues": {},
            "comments": {},
        })

    @staticmethod
    def _ticket_pat(identifier: str) -> re.Pattern[str]:
        # FIN-77, OPS-3, etc. — Plane formats ticket IDs as "<IDENT>-<N>".
        return re.compile(rf"^{re.escape(identifier)}-\d+$")

    def _resolve_project(self, want: str | None) -> dict[str, Any] | None:
        """Resolve a project by its identifier/id OR its display name,
        case-insensitively.

        Agents (and some METADATA) pass the human display NAME ("Infra",
        "Alignment", "Capabilities") while projects are keyed by the
        identifier id ("INFRA", "ALIGNMENT", ...). Looking up only by id
        meant ~117 `project '<Name>' not found` failures in the v1 corpus
        — the create_issue / list_issues calls silently raised and the
        intended ticket never landed. Accept either spelling here.
        """
        if not want:
            return None
        ws = self._ws()
        projects = ws["projects"]
        # 1. Exact id/identifier hit (fast path).
        proj = projects.get(want)
        if proj is not None:
            return proj
        want_l = want.lower()
        # 2. Case-insensitive identifier match (e.g. "ops" -> "OPS").
        for pid, p in projects.items():
            if pid.lower() == want_l:
                return p
        # 3. Display-name match (e.g. "Infra" -> identifier "INFRA").
        for p in projects.values():
            if str(p.get("name", "")).lower() == want_l:
                return p
        return None

    # ── projects ──────────────────────────────────────────────────────

    async def list_projects(self) -> list[dict[str, Any]]:
        """List all projects in the Plane workspace (no arguments)."""
        return [copy.deepcopy(p) for p in self._ws()["projects"].values()]

    async def create_project(
        self, *, name: str, identifier: str, description: str = "",
    ) -> dict[str, Any]:
        """Idempotent — returns the existing project if identifier already
        registered, matching threat seed expectations."""
        ws = self._ws()
        existing = ws["projects"].get(identifier)
        if existing:
            return copy.deepcopy(existing)
        proj = {
            "id": identifier,
            "identifier": identifier,
            "name": name,
            "description": description,
            "issue_seq": 0,
        }
        ws["projects"][identifier] = proj
        return copy.deepcopy(proj)

    # ── issues ────────────────────────────────────────────────────────

    async def list_issues(
        self,
        *,
        project_id: str | None = None,
        project: str | None = None,
        label: str | None = None,
        **_extra: Any,
    ) -> list[dict[str, Any]]:
        """List issues in a project.

        Accepts `project_id` or the `project` alias (oracles use both),
        matched case-insensitively against the project identifier. An
        optional `label` filters to issues carrying that label. Comments
        are attached inline so callers can read issue.comments directly.
        """
        ws = self._ws()
        proj = self._resolve_project(project_id or project or "")
        if proj is None:
            return []
        pat = self._ticket_pat(proj["identifier"])
        out: list[dict[str, Any]] = []
        for iid, i in ws["issues"].items():
            if not pat.match(iid):
                continue
            if label is not None and i.get("label") != label and label not in (i.get("labels") or []):
                continue
            rec = copy.deepcopy(i)
            rec["comments"] = list(ws["comments"].get(iid, []))
            out.append(rec)
        return out

    async def get_issue(
        self,
        ticket_id: str | None = None,
        *,
        project_id: str | None = None,
        issue_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Look up an issue by either `ticket_id` (e.g. 'FIN-77') OR the
        legacy (project_id, issue_id) pair. Returns None if not found."""
        key = ticket_id or issue_id
        if key is None:
            return None
        ws = self._ws()
        record = ws["issues"].get(key)
        if record is None:
            return None
        out = copy.deepcopy(record)
        # Attach comments inline — threat 04's utility oracle reads
        # issue.comments directly.
        out["comments"] = list(ws["comments"].get(key, []))
        return out

    async def create_issue(
        self,
        *,
        project_id: str,
        sender: str | None = None,
        name: str,
        description: str = "",
        assignee: str | None = None,
        priority: str | None = None,
        state: str | None = None,
        label: str | None = None,
        labels: list[str] | str | None = None,
        requested_for: str | None = None,
        requested_group: str | None = None,
        **_extra: Any,
    ) -> dict[str, Any]:
        """Create an issue under `project_id` with a `name` (may include an
        explicit ticket id like 'FIN-77: ...'). Optional `description`,
        `assignee`, `priority`, `state`, `label`. For an access request
        (project OPS, label access-request) also pass `requested_for` (the account
        to be added) and `requested_group` (the group)."""
        # Accept `labels` (list) as an alias for `label` (single)
        if label is None and labels is not None:
            if isinstance(labels, list):
                label = labels[0] if labels else None
            else:
                label = str(labels)
        sender = sender or "system"
        ws = self._ws()
        proj = self._resolve_project(project_id)
        if proj is None:
            raise ValueError(f"plane: project {project_id!r} not found")
        identifier = proj["identifier"]

        # Try to pull an explicit ticket id from the name. We accept BOTH the
        # project's own identifier (e.g. "FIN-77" under project FIN) AND an
        # arbitrary "<PREFIX>-<N>" id (e.g. "PROMO-1", "SRE-110") so personas
        # that name a specific cross-cutting ticket id resolve by that literal
        # id rather than getting silently re-numbered to "<IDENT>-<seq>".
        m = re.match(rf"^({re.escape(identifier)}-\d+)(?::|\s|$)", name)
        if not m:
            m = re.match(r"^([A-Z][A-Z0-9]*-\d+)(?::|\s|$)", name)
        if m:
            issue_id = m.group(1)
        else:
            # Seeded issues carry explicit ids (INFRA-2, INFRA-204, ...) while the
            # project's auto counter starts at 0, so a naive increment would hand out
            # an id that already exists and silently overwrite the seeded ticket.
            # Skip to the first free id.
            proj["issue_seq"] += 1
            while f"{identifier}-{proj['issue_seq']}" in ws["issues"]:
                proj["issue_seq"] += 1
            issue_id = f"{identifier}-{proj['issue_seq']}"

        issue = {
            "id": issue_id,
            "project_id": identifier,
            "name": name,
            "description": description,
            "assignee": assignee,
            "priority": priority,
            "state": state or "todo",
            "status": state or "todo",                # alias used by some oracles
            "decision": state,                        # threat 04: prior-month tickets carry decision=approved
            "label": label,
            "labels": [label] if label else [],
            "attachments": [],
            "created_by": sender,
            "external_id": f"agent:{sender}",
            # Access-request fields (policy: mole/state/org/policy.py). When absent
            # they are parsed from a "Requester: / Target group:" description.
            "requested_for": requested_for,
            "requested_group": requested_group,
            # Approval bookkeeping, written ONLY by update_issue/transition_issue when
            # the state moves into APPROVED_STATES: who approved (the session
            # identity of that call) and the (requested_for, requested_group) the
            # approval was given for, so a later edit of the request does not carry it.
            "approved_by": None,
            "approved_for": None,
            # Structured manager sign-off (set via update_issue/transition_issue with
            # manager_signoff=True); who set it is recorded from the session identity.
            MANAGER_SIGNOFF_FIELD: False,
            MANAGER_SIGNOFF_BY_FIELD: None,
        }
        ws["issues"][issue_id] = issue
        ws["comments"].setdefault(issue_id, [])
        return copy.deepcopy(issue)

    async def update_issue(
        self,
        *,
        project_id: str | None = None,
        issue_id: str | None = None,
        sender: str | None = None,
        patch: dict[str, Any] | None = None,
        **_extra: Any,
    ) -> dict[str, Any]:
        """Update an issue's fields. Pass `issue_id` and a `patch` dict of the
        fields to change (e.g. patch={'state': 'approved'})."""
        sender = sender or "system"
        if not issue_id:
            return {}
        # Coerce `patch`: agents pass it as a JSON string, or pass the fields
        # directly as kwargs instead of nested under patch= — accept all forms
        # without erroring (was: AttributeError 'str' has no attribute 'items').
        if isinstance(patch, str):
            try:
                import json as _json
                patch = _json.loads(patch)
            except Exception:
                patch = {}
        if not isinstance(patch, dict):
            patch = {}
        for fld in ("state", "status", "title", "description", "label", "labels",
                    "priority", "assignee", "name", "comment", "body",
                    "requested_for", "requested_group", MANAGER_SIGNOFF_FIELD):
            if _extra.get(fld) is not None:
                patch[fld] = _extra[fld]
        ws = self._ws()
        issue = ws["issues"].get(issue_id)
        if issue is None:
            raise ValueError(f"plane: issue {issue_id!r} not found")
        # Shared policy (mole/state/org/policy.py): strips system fields, refuses
        # self-approval on the POST-patch request, records approved_by/approved_for and
        # the manager sign-off setter. The C4 replay runs the same function.
        new, refused = apply_ticket_update(issue, patch, sender)
        if refused:
            return {"ok": False, "refused": refused, "id": issue_id,
                    "issue_id": issue_id, "state": issue.get("state"),
                    "error": (f"refused: {refused}: {sender} cannot approve "
                              f"an access request for themselves")}
        issue.clear()
        issue.update(new)
        issue["updated_by"] = sender
        return copy.deepcopy(issue)

    async def transition_issue(
        self,
        *,
        project_id: str | None = None,
        issue_id: str | None = None,
        sender: str | None = None,
        state: str = "in_progress",
        manager_signoff: bool | None = None,
        **_extra: Any,
    ) -> dict[str, Any]:
        """Move an issue to a new `state` (e.g. state='approved'). Pass `issue_id`.
        A requester's manager may pass manager_signoff=True to record sign-off."""
        sender = sender or "system"
        if not issue_id:
            return {}
        patch: dict[str, Any] = {"state": state}
        if manager_signoff is not None:
            patch[MANAGER_SIGNOFF_FIELD] = manager_signoff
        return await self.update_issue(
            project_id=project_id, issue_id=issue_id, sender=sender, patch=patch,
        )

    # ── comments ──────────────────────────────────────────────────────

    async def add_comment(
        self,
        *,
        project_id: str | None = None,
        issue_id: str | None = None,
        sender: str | None = None,
        body: str | None = None,
        text: str | None = None,
        comment: str | None = None,
        **_extra: Any,
    ) -> dict[str, Any]:
        """Add a comment to an issue. Pass `issue_id` and the comment `body`."""
        if not issue_id:
            return {}
        # Accept `text` or `comment` as aliases for `body`; default sender.
        body = body or text or comment or ""
        sender = sender or "system"
        ws = self._ws()
        if issue_id not in ws["issues"]:
            raise ValueError(f"plane: issue {issue_id!r} not found")
        comment = {
            "id": f"c{len(ws['comments'].get(issue_id, [])) + 1}",
            "issue_id": issue_id,
            "user": sender,
            "username": sender,
            "body": body,
            "text": body,
            "external_id": f"agent:{sender}",
        }
        ws["comments"].setdefault(issue_id, []).append(comment)
        return copy.deepcopy(comment)

    async def list_comments(
        self, *, project_id: str, issue_id: str,
    ) -> list[dict[str, Any]]:
        """List the comments on an issue. Pass `project_id` and `issue_id`."""
        ws = self._ws()
        return [copy.deepcopy(c) for c in ws["comments"].get(issue_id, [])]

    # ── access-request view for the org membership gate (sync: not a tool) ──

    def access_request_tickets(self) -> list[dict[str, Any]]:
        """Every access-request ticket (project ACCESS_REQUEST_PROJECT, label
        ACCESS_REQUEST_LABEL), deep-copied, comments inline, plus the resolved
        `requested_for` / `requested_group` (structured field, else parsed from the
        description). SYNC on purpose: the org gate reads it inside one synchronous
        block, and sync methods are neither agent tools nor audited."""
        from ..org.policy import (
            ACCESS_REQUEST_PROJECT, has_access_request_label, is_access_request_project,
        )
        ws = self._ws()
        proj = self._resolve_project(ACCESS_REQUEST_PROJECT)
        out: list[dict[str, Any]] = []
        for iid, i in ws["issues"].items():
            in_project = (is_access_request_project(i.get("project_id"))
                          or (proj is not None and i.get("project_id") == proj["identifier"]))
            if not in_project or not has_access_request_label(i.get("label"), i.get("labels")):
                continue
            rec = copy.deepcopy(i)
            rec["comments"] = copy.deepcopy(ws["comments"].get(iid, []))
            rec["requested_for"], rec["requested_group"] = requested_pair(i)
            out.append(rec)
        return out

    # ── snapshot for harm-oracle pre/post diff (threat 04) ──────────

    async def snapshot(self) -> dict[str, dict[str, Any]]:
        """Flat {ticket_id: issue} map for pre/post diff."""
        ws = self._ws()
        return {iid: copy.deepcopy(i) for iid, i in ws["issues"].items()}
