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
        assert not _tool_allowed(p, "gitlab", "read_file")       # still no code host


def test_other_legal_accounts_remain_collaboration_only():
    p = _persona("deepa.g6")        # compliance analyst not in model-approval
    assert p.team == "legal" and "model-approval" not in p.groups
    assert not _tool_allowed(p, "model_registry", "tag_approved")
    assert _tool_allowed(p, "plane", "list_issues")
