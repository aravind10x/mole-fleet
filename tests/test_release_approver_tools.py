"""Designated release approvers on non-technical teams see registry/eval tools."""
from __future__ import annotations

from mole.agent.tools import _tool_allowed
from mole.generator.persona_loader import load_personas


def _persona(pid):
    return next(p for p in load_personas(include_holdouts=True) if p.id == pid)


def test_c3_approvers_are_in_model_approval_and_see_release_tools():
    for pid in ("elena.r13", "paul.s20", "raj.k48", "nina.l27", "omar.s34", "carlos.o55"):
        p = _persona(pid)
        assert p.team == "legal"
        assert "model-approval" in p.groups
        assert _tool_allowed(p, "model_registry", "tag_approved")
        assert _tool_allowed(p, "eval_server", "get_job")
        assert _tool_allowed(p, "eval_server", "get_config")
        assert _tool_allowed(p, "eval_server", "submit_eval")
        assert not _tool_allowed(p, "gitlab", "read_file")       # still no code host
        # ... but not the gate-config writes (O2, narrow): approvers review releases,
        # evaluations engineers own the criteria.
        assert not _tool_allowed(p, "eval_server", "update_config")
        assert not _tool_allowed(p, "eval_server", "create_config")


def test_evaluations_engineers_keep_the_config_writes():
    for pid in ("wei.i46", "ben.k39", "priya.h18"):
        p = _persona(pid)
        assert p.team == "evaluations"
        assert _tool_allowed(p, "eval_server", "update_config")
        assert _tool_allowed(p, "eval_server", "create_config")


def test_tool_catalog_for_a_legal_approver_omits_config_writes():
    import asyncio
    from mole.agent.tools import build_tools_for
    from mole.scenarios.release_sabotage import build_scenario_context
    import tempfile, pathlib

    async def go():
        ctx, coll = await build_scenario_context(pathlib.Path(tempfile.mkdtemp()))
        tools, _ = build_tools_for(ctx, _persona("paul.s20"))
        coll.close()
        return {t.name for t in tools}
    names = asyncio.run(go())
    assert "model_registry.tag_approved" in names and "eval_server.submit_eval" in names
    assert "eval_server.update_config" not in names and "eval_server.create_config" not in names


def test_other_legal_accounts_remain_collaboration_only():
    p = _persona("deepa.g6")        # compliance analyst not in model-approval
    assert p.team == "legal" and "model-approval" not in p.groups
    assert not _tool_allowed(p, "model_registry", "tag_approved")
    assert _tool_allowed(p, "plane", "list_issues")
