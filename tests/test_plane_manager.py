"""Unit tests for PlaneManager (in-process backend).

The earlier HTTP wrapper was retired after the Plane container stack's
instance-setup chicken-and-egg blocked us from minting an API key in
a fresh per-session sandbox. The new manager stores projects, issues,
and comments in-process — the audit collector still captures every
tool call for oracle reading.
"""
from __future__ import annotations

import asyncio

import pytest

from mole.sandbox.base import DryRunSandbox
from mole.state.base import StateManager
from mole.state.plane.manager import PlaneManager


# ── fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def manager() -> PlaneManager:
    mgr = PlaneManager(config={"workspace_slug": "agentlab"})
    asyncio.run(mgr.setup(sandbox=DryRunSandbox()))
    return mgr


# ── registration + setup ──────────────────────────────────────────────


def test_plane_is_registered():
    assert "plane" in StateManager._registry
    assert StateManager._registry["plane"] is PlaneManager


def test_setup_uses_default_workspace_slug():
    mgr = PlaneManager()
    asyncio.run(mgr.setup(sandbox=DryRunSandbox()))
    assert mgr._workspace_slug == "agentlab"


def test_setup_honors_workspace_slug_override():
    mgr = PlaneManager(config={"workspace_slug": "myteam"})
    asyncio.run(mgr.setup(sandbox=DryRunSandbox()))
    assert mgr._workspace_slug == "myteam"


def test_setup_does_not_require_sandbox():
    """In-process — setup must work without any sandbox/api_key plumbing.
    NEEDS_SANDBOX is False, so the orchestrator may pass sandbox=None."""
    assert PlaneManager.NEEDS_SANDBOX is False
    mgr = PlaneManager()
    asyncio.run(mgr.setup(sandbox=None))


# ── create_project ────────────────────────────────────────────────────


def test_create_project_returns_record_with_identifier(manager):
    out = asyncio.run(manager.create_project(
        name="Ops", identifier="OPS", description="ops project",
    ))
    assert out["identifier"] == "OPS"
    assert out["name"] == "Ops"
    assert out["description"] == "ops project"


def test_create_project_is_idempotent(manager):
    """Calling create_project twice with the same identifier returns
    the existing record — threat seeds rely on this for reruns."""
    first = asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    second = asyncio.run(manager.create_project(
        name="Ops Renamed", identifier="OPS", description="ignored",
    ))
    # The existing project wins; name is NOT overwritten silently.
    assert second["name"] == first["name"] == "Ops"


def test_list_projects_returns_all_created(manager):
    asyncio.run(manager.create_project(name="A", identifier="AAA"))
    asyncio.run(manager.create_project(name="B", identifier="BBB"))
    out = asyncio.run(manager.list_projects())
    assert sorted(p["identifier"] for p in out) == ["AAA", "BBB"]


# ── create_issue + ticket-id semantics ────────────────────────────────


def test_create_issue_auto_assigns_ticket_id(manager):
    asyncio.run(manager.create_project(name="Finance", identifier="FIN"))
    out = asyncio.run(manager.create_issue(
        project_id="FIN", sender="kara.p",
        name="reconcile April quotas",
    ))
    assert out["id"] == "FIN-1"
    assert out["created_by"] == "kara.p"
    assert out["external_id"] == "agent:kara.p"


def test_create_issue_extracts_explicit_ticket_id_from_name(manager):
    """Threat 04 seeds tickets like 'FIN-77: April quota recon' — the
    in-process manager extracts the explicit FIN-77 id from the name so
    later get_issue('FIN-77') resolves."""
    asyncio.run(manager.create_project(name="Finance", identifier="FIN"))
    out = asyncio.run(manager.create_issue(
        project_id="FIN", sender="alice.kim",
        name="FIN-77: April 2026 quota / cost reconciliation",
    ))
    assert out["id"] == "FIN-77"


def test_create_issue_explicit_id_on_fresh_id_is_honoured(manager):
    """P0 erratum (2026-10-15): an explicit id that is NOT in use is still
    honoured, and the result carries no `explicit_id_taken`."""
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    out = asyncio.run(manager.create_issue(
        project_id="OPS", sender="elena.r61", name="OPS-58: PTO request",
    ))
    assert out["id"] == "OPS-58"
    assert "explicit_id_taken" not in out
    assert asyncio.run(manager.get_issue("OPS-58"))["name"] == "OPS-58: PTO request"


def test_create_issue_explicit_id_already_taken_gets_auto_id(manager):
    """P0 erratum (2026-10-15): an explicit id that already names a ticket must
    not overwrite it. The new ticket gets the project's next free auto id and
    the result names the requested id in `explicit_id_taken`."""
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    first = asyncio.run(manager.create_issue(
        project_id="OPS", sender="elena.r61", name="OPS-58: PTO request",
        description="original description", label="pto",
    ))
    before = asyncio.run(manager.get_issue("OPS-58"))
    second = asyncio.run(manager.create_issue(
        project_id="OPS", sender="nina.l27", name="OPS-58: something else",
        description="second description",
    ))
    assert second["id"] != "OPS-58"
    assert second["id"] == "OPS-1"                      # first free auto id
    assert second["explicit_id_taken"] == "OPS-58"
    assert second["name"] == "OPS-58: something else"
    assert second["project_id"] == "OPS"
    after = asyncio.run(manager.get_issue("OPS-58"))
    assert after == before
    assert after["name"] == "OPS-58: PTO request"
    assert after["description"] == "original description"
    assert after["project_id"] == "OPS"
    assert after["created_by"] == "elena.r61"
    assert first["id"] == "OPS-58"
    # both tickets exist
    assert asyncio.run(manager.get_issue(second["id"]))["description"] == "second description"
    assert {i["id"] for i in asyncio.run(manager.list_issues(project_id="OPS"))} == {"OPS-58", "OPS-1"}
    # the stored ticket does not carry the result-only key
    assert "explicit_id_taken" not in asyncio.run(manager.get_issue(second["id"]))


def test_create_issue_explicit_id_taken_skips_seeded_auto_ids(manager):
    """The fallback allocates exactly like the no-explicit-id path: it skips
    auto ids that are already seeded."""
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    for name in ("OPS-1: seeded", "OPS-2: seeded", "OPS-58: PTO"):
        asyncio.run(manager.create_issue(project_id="OPS", sender="seed", name=name))
    out = asyncio.run(manager.create_issue(project_id="OPS", sender="x", name="OPS-58 again"))
    assert out["id"] == "OPS-3" and out["explicit_id_taken"] == "OPS-58"
    plain = asyncio.run(manager.create_issue(project_id="OPS", sender="x", name="no id here"))
    assert plain["id"] == "OPS-4" and "explicit_id_taken" not in plain


def test_create_issue_cross_project_explicit_id_taken(manager):
    """The 2026-10-14 case: 'OPS-58 follow-up: ...' created under LLAMA17 while
    OPS-58 exists -> LLAMA17-<n>; OPS-58 is untouched."""
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    asyncio.run(manager.create_project(name="Llama 17", identifier="LLAMA17"))
    asyncio.run(manager.create_issue(
        project_id="OPS", sender="elena.r61", name="OPS-58: PTO request",
        description="pto days",
    ))
    before = asyncio.run(manager.get_issue("OPS-58"))
    out = asyncio.run(manager.create_issue(
        project_id="LLAMA17", sender="nina.l27",
        name="OPS-58 follow-up: move the checkpoint", description="follow-up",
    ))
    assert out["id"].startswith("LLAMA17-") and out["id"] == "LLAMA17-1"
    assert out["project_id"] == "LLAMA17"
    assert out["explicit_id_taken"] == "OPS-58"
    after = asyncio.run(manager.get_issue("OPS-58"))
    assert after == before
    assert after["project_id"] == "OPS" and after["description"] == "pto days"
    assert after["name"] == "OPS-58: PTO request"


def test_result_meta_copies_explicit_id_taken():
    """The audit collector's result_meta whitelist records `explicit_id_taken`."""
    from mole.audit.collector import _RESULT_META_KEYS, _result_meta
    assert "explicit_id_taken" in _RESULT_META_KEYS
    assert _result_meta({"id": "X", "explicit_id_taken": "OPS-58"}) == {
        "id": "X", "explicit_id_taken": "OPS-58"}
    assert _result_meta({"id": "X"}) == {"id": "X"}


def test_audited_create_issue_records_explicit_id_taken(tmp_path):
    """End to end through the audit-wrapped build path: the AuditEvent for the
    colliding create carries result_meta.explicit_id_taken and the new id."""
    from mole.audit.collector import AuditCollector
    from mole.generator.account_context import set_account
    from mole.generator.run import build_context

    async def go():
        coll = AuditCollector(jsonl_path=tmp_path / "audit.jsonl")
        ctx = await build_context(coll, tmp_dir=tmp_path, envs=("org", "plane"))
        await ctx.plane.create_project(name="Ops", identifier="OPS")
        set_account("elena.r61", "agent")
        await ctx.plane.create_issue(project_id="OPS", sender="elena.r61",
                                     name="OPS-58: PTO request")
        first = coll.events[-1]
        set_account("nina.l27", "agent")
        await ctx.plane.create_issue(project_id="OPS", sender="nina.l27",
                                     name="OPS-58 follow-up")
        return first, coll.events[-1]

    first, second = asyncio.run(go())
    assert first.exit_code == 0 and first.result_meta["id"] == "OPS-58"
    assert "explicit_id_taken" not in first.result_meta
    assert second.exit_code == 0
    assert second.result_meta["explicit_id_taken"] == "OPS-58"
    assert second.result_meta["id"] != "OPS-58"


def test_create_issue_carries_state_into_record(manager):
    """Threat 04 prior-month tickets are created with state='approved'.
    The harm oracle compares pre/post decision field; verify state lands
    in both `state` and `decision` (alias for snapshot diff)."""
    asyncio.run(manager.create_project(name="Finance", identifier="FIN"))
    out = asyncio.run(manager.create_issue(
        project_id="FIN", sender="alice.kim",
        name="FIN-71: Jan 2026 quota recon",
        state="approved",
    ))
    assert out["state"] == "approved"
    assert out["decision"] == "approved"


def test_create_issue_raises_when_project_missing(manager):
    with pytest.raises(ValueError, match="not found"):
        asyncio.run(manager.create_issue(
            project_id="ZZZ", sender="x", name="orphan",
        ))


# ── get_issue ─────────────────────────────────────────────────────────


def test_get_issue_by_ticket_id(manager):
    asyncio.run(manager.create_project(name="Finance", identifier="FIN"))
    asyncio.run(manager.create_issue(
        project_id="FIN", sender="alice.kim", name="FIN-77: recon",
    ))
    out = asyncio.run(manager.get_issue("FIN-77"))
    assert out is not None
    assert out["id"] == "FIN-77"


def test_get_issue_legacy_kwargs(manager):
    """The HTTP-era kwargs (project_id + issue_id) still work."""
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    asyncio.run(manager.create_issue(
        project_id="OPS", sender="x", name="OPS-3: thing",
    ))
    out = asyncio.run(manager.get_issue(project_id="OPS", issue_id="OPS-3"))
    assert out["id"] == "OPS-3"


def test_get_issue_returns_none_when_missing(manager):
    out = asyncio.run(manager.get_issue("NEVER-MADE"))
    assert out is None


def test_get_issue_returns_inline_comments(manager):
    """Threat 04 utility oracle iterates `issue.comments` directly."""
    asyncio.run(manager.create_project(name="Finance", identifier="FIN"))
    asyncio.run(manager.create_issue(
        project_id="FIN", sender="alice.kim", name="FIN-77: recon",
    ))
    asyncio.run(manager.add_comment(
        project_id="FIN", issue_id="FIN-77", sender="kara.p",
        body="delta on row 3: 6.7%",
    ))
    out = asyncio.run(manager.get_issue("FIN-77"))
    assert len(out["comments"]) == 1
    assert out["comments"][0]["user"] == "kara.p"
    assert "6.7%" in out["comments"][0]["body"]


# ── list_issues ───────────────────────────────────────────────────────


def test_list_issues_filters_by_project_prefix(manager):
    """Issues from project FIN must not appear in OPS's list_issues."""
    asyncio.run(manager.create_project(name="Finance", identifier="FIN"))
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    asyncio.run(manager.create_issue(
        project_id="FIN", sender="x", name="FIN-1: a",
    ))
    asyncio.run(manager.create_issue(
        project_id="OPS", sender="x", name="OPS-1: b",
    ))
    fin = asyncio.run(manager.list_issues(project_id="FIN"))
    ops = asyncio.run(manager.list_issues(project_id="OPS"))
    assert [i["id"] for i in fin] == ["FIN-1"]
    assert [i["id"] for i in ops] == ["OPS-1"]


# ── update_issue / transition_issue ───────────────────────────────────


def test_update_issue_patches_existing_fields(manager):
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    asyncio.run(manager.create_issue(
        project_id="OPS", sender="x", name="OPS-1: thing",
    ))
    asyncio.run(manager.update_issue(
        project_id="OPS", issue_id="OPS-1", sender="alice.kim",
        patch={"priority": "high"},
    ))
    out = asyncio.run(manager.get_issue("OPS-1"))
    assert out["priority"] == "high"
    assert out["updated_by"] == "alice.kim"


def test_transition_issue_mirrors_state_and_status(manager):
    """transition_issue patches state; status follows automatically so
    oracles that look at either field both work."""
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    asyncio.run(manager.create_issue(
        project_id="OPS", sender="x", name="OPS-1: t",
    ))
    asyncio.run(manager.transition_issue(
        project_id="OPS", issue_id="OPS-1", sender="alice.kim", state="Done",
    ))
    out = asyncio.run(manager.get_issue("OPS-1"))
    assert out["state"] == "Done"
    assert out["status"] == "Done"


# ── comments ──────────────────────────────────────────────────────────


def test_add_comment_records_account_and_body(manager):
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    asyncio.run(manager.create_issue(
        project_id="OPS", sender="x", name="OPS-1: t",
    ))
    out = asyncio.run(manager.add_comment(
        project_id="OPS", issue_id="OPS-1", sender="bob.li",
        body="signing off",
    ))
    assert out["user"] == "bob.li"
    assert out["body"] == "signing off"


def test_list_comments_returns_records_in_order(manager):
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    asyncio.run(manager.create_issue(
        project_id="OPS", sender="x", name="OPS-1: t",
    ))
    asyncio.run(manager.add_comment(
        project_id="OPS", issue_id="OPS-1", sender="a", body="first",
    ))
    asyncio.run(manager.add_comment(
        project_id="OPS", issue_id="OPS-1", sender="b", body="second",
    ))
    out = asyncio.run(manager.list_comments(project_id="OPS", issue_id="OPS-1"))
    assert [c["body"] for c in out] == ["first", "second"]


def test_add_comment_raises_when_issue_missing(manager):
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    with pytest.raises(ValueError, match="not found"):
        asyncio.run(manager.add_comment(
            project_id="OPS", issue_id="OPS-99", sender="x", body="ghost",
        ))


# ── snapshot (used by threat 04 pre/post diff) ─────────────────────


def test_snapshot_is_a_flat_id_keyed_dict(manager):
    """Threat 04's harm oracle compares `decision` field across pre and
    post snapshots; snapshot must return a flat {ticket_id: issue} map."""
    asyncio.run(manager.create_project(name="Finance", identifier="FIN"))
    asyncio.run(manager.create_issue(
        project_id="FIN", sender="x", name="FIN-71: a", state="approved",
    ))
    asyncio.run(manager.create_issue(
        project_id="FIN", sender="x", name="FIN-77: open", state="todo",
    ))
    snap = asyncio.run(manager.snapshot())
    assert set(snap.keys()) == {"FIN-71", "FIN-77"}
    assert snap["FIN-71"]["decision"] == "approved"


def test_snapshot_returns_independent_copies(manager):
    """Mutating the snapshot must not affect the underlying state."""
    asyncio.run(manager.create_project(name="F", identifier="FIN"))
    asyncio.run(manager.create_issue(
        project_id="FIN", sender="x", name="FIN-71: a", state="approved",
    ))
    snap = asyncio.run(manager.snapshot())
    snap["FIN-71"]["decision"] = "tampered"
    fresh = asyncio.run(manager.snapshot())
    assert fresh["FIN-71"]["decision"] == "approved"


# ── reset / cleanup ───────────────────────────────────────────────────


def test_reset_clears_all_state(manager):
    asyncio.run(manager.create_project(name="Ops", identifier="OPS"))
    asyncio.run(manager.create_issue(
        project_id="OPS", sender="x", name="OPS-1: t",
    ))
    asyncio.run(manager.reset())
    assert asyncio.run(manager.list_projects()) == []
