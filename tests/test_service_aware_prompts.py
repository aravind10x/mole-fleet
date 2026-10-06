"""Benign prompt text mentions only services present in the context.

With every service present the text is byte-identical to the pre-change render
(golden fixture); with only the in-process services there is no email / chat /
GitLab / ownCloud wording and the opener points at Plane, the registry, eval
jobs and the org directory.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

from mole.agent.prompts import render_prompt
from mole.generator import agentic_member as am
from mole.generator.run import INPROCESS_ENVS
from mole.state.org.manager import OrgManager

FIXTURE = Path(__file__).parent / "fixtures" / "benign_prompts_full_services_alice.txt"
ALL_NINE = {"org", "gitlab", "owncloud", "email", "rocketchat", "plane",
            "model_registry", "eval_server", "secrets_store"}
NAMES = ("_BENIGN_SYSTEM", "_BENIGN_SYSTEM_GENERIC", "_BENIGN_SYSTEM_BLOCK", "_BENIGN_USER")


@pytest.fixture(scope="module")
def org():
    m = OrgManager()
    asyncio.run(m.setup(sandbox=None))
    return m


def _render_all(org, services):
    tools = ["org.lookup_person", "plane.list_issues", "gitlab.list_projects"]
    tmpl = am._benign_templates(services)
    parts = []
    for name in NAMES:
        kw = dict(focal_account="alice.kim", org_manager=org,
                  sim_start_iso="2026-04-06T09:00:00Z", available_tools=tools,
                  metadata={"task": "Do the thing."})
        if services is not None:
            kw["services"] = services
        parts.append(f"=== {name}\n" + render_prompt(tmpl[name], **kw))
    return "\n".join(parts) + "\n"


@pytest.mark.parametrize("services", [None, ALL_NINE])
def test_full_service_set_is_byte_identical(org, services):
    assert _render_all(org, services) == FIXTURE.read_text(encoding="utf-8")
    if services is not None:
        assert am._benign_templates(services)["_BENIGN_USER"] is am._BENIGN_USER


def test_inprocess_set_drops_docker_service_wording(org):
    out = _render_all(org, set(INPROCESS_ENVS))
    banned = re.compile(r"gitlab|owncloud|e-?mail|inbox|chat|channel|merge request|"
                        r"@agentlab|file-storage|mailbox|commit code", re.IGNORECASE)
    # The tool list is caller-supplied (the fixture passes a gitlab tool name), so
    # check the prose only.
    prose = "\n".join(l for l in out.splitlines() if not l.startswith("  - "))
    assert not banned.search(prose), banned.findall(prose)
    user = am._benign_templates(set(INPROCESS_ENVS))["_BENIGN_USER"]
    for phrase in ("Plane tickets", "model registry", "eval jobs", "org directory"):
        assert phrase in user
    assert "look colleagues up with org.list_directory" in prose
