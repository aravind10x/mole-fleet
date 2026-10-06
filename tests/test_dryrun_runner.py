"""Docker-free runner (simulate(sandbox_mode="dryrun")).

Everything here runs with no LLM, no Docker and no network: rules mode drives
the in-process managers (org, plane, model_registry, eval_server,
secrets_store) through the same day loop, day-boundary managers.json export and
resume manifest the agentic runner uses.
"""
from __future__ import annotations

import asyncio
import json
import socket
from types import SimpleNamespace

import pytest

from mole.audit.collector import AuditCollector
from mole.generator import resume_state
from mole.generator.run import INPROCESS_ENVS, build_context, simulate


@pytest.fixture
def no_network_no_docker(monkeypatch):
    """Fail loudly if anything opens a network connection or a LabSandbox."""
    def _no_connect(self, *a, **k):
        raise AssertionError(f"network connection attempted: {a!r}")
    monkeypatch.setattr(socket.socket, "connect", _no_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _no_connect)
    import mole.sandbox.lab as lab

    class _NoLab:
        def __init__(self, *a, **k):
            raise AssertionError("LabSandbox constructed in a dryrun run")
    monkeypatch.setattr(lab, "LabSandbox", _NoLab)


def test_rules_dryrun_runs_end_to_end(tmp_path, no_network_no_docker):
    out = tmp_path / "dry.jsonl"
    coll = asyncio.run(simulate(mode="rules", sandbox_mode="dryrun", n_personas=5,
                                n_days=1, out_path=out, seed=0, sessions_per_day=3))
    inproc = [e for e in coll.events if e.service in INPROCESS_ENVS]
    assert len({e.account for e in inproc}) >= 2
    assert len({e.service for e in inproc}) >= 2
    assert out.exists() and out.stat().st_size > 0

    manifest = resume_state.load(out)
    assert manifest["sandbox_mode"] == "dryrun"
    [day] = manifest["days"]
    assert day["managers_ok"] is True and day["snapshot_ok"] is False
    managers = json.loads(open(day["managers_path"], encoding="utf-8").read())
    assert {"org", "plane", "model_registry", "eval_server", "secrets_store"} <= set(managers)


def test_rules_dryrun_release_workflow_approves_without_errors(tmp_path):
    """The rules release workflow evaluates an unapproved RC under release-gate
    and approvers only approve checkpoints with a passing verdict, so
    tag_approved never fails with "no eval record"."""
    out = tmp_path / "rel.jsonl"
    coll = asyncio.run(simulate(mode="rules", sandbox_mode="dryrun", n_personas=10,
                                n_days=2, out_path=out, seed=0, sessions_per_day=3))
    tags = [e for e in coll.events if e.action == "tag_approved"]
    submits = [e for e in coll.events if e.action == "submit_eval"]
    assert submits and all(e.exit_code == 0 for e in submits)
    assert all(e.exit_code == 0 for e in tags), [e.error for e in tags if e.exit_code]
    assert tags, "expected at least one approval in 2 days x 10 personas"


def test_build_context_inprocess_seeds_world(tmp_path):
    coll = AuditCollector(jsonl_path=tmp_path / "a.jsonl")
    ctx = asyncio.run(build_context(coll, tmp_dir=tmp_path, envs=INPROCESS_ENVS,
                                    seed_world=True))
    reg = ctx._managers["model_registry"]
    ev = ctx._managers["eval_server"]
    assert "ckpt-prometheus-v0.4" in reg._checkpoints        # seed_s1_variants
    assert ev.current_config("release-gate") is not None
    assert ctx._managers["plane"]._state                       # threat plane seeds ran
    coll.close()


def test_seed_company_skips_absent_managers_cleanly():
    """With only some managers present every step skips instead of raising and
    the counts cover only what ran."""
    from mole.seeders.seed_company import seed_company
    from mole.seeders.seed_s1_variants import seed_s1_variants
    counts = asyncio.run(seed_company(SimpleNamespace()))
    assert counts["org"] == {}
    assert asyncio.run(seed_s1_variants(SimpleNamespace())) == {}


class _OneToolThenStop:
    """Calls one in-process tool on its first turn, then stops; records the tool
    names it was offered and the system prompts it saw."""
    backend = "fake"
    model_id = "fake"

    def __init__(self):
        self.calls = 0
        self.offered: set[str] = set()

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None,
                       seed=None):
        from mole.llm.base import ChatResponse, ToolCall
        self.calls += 1
        for t in tools or []:
            self.offered.add(getattr(t, "name", None) or t.get("name", ""))
        if self.calls % 2 == 1:
            return ChatResponse(content="", tool_calls=[ToolCall(
                id=f"c{self.calls}", name="model_registry.list_checkpoints", arguments={})])
        return ChatResponse(content="done", tool_calls=[])


def test_agentic_dryrun_without_docker(tmp_path, no_network_no_docker):
    """Agentic mode with sandbox_mode="dryrun" never touches Docker and only
    offers the agent tools on the in-process services."""
    llm = _OneToolThenStop()
    out = tmp_path / "agentic_dry.jsonl"
    coll = asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun", llm=llm,
                                n_personas=2, n_days=1, out_path=out, seed=0,
                                sessions_per_day=1, max_turns=4))
    agent_events = [e for e in coll.events if e.account_kind == "background_llm_agent"]
    assert agent_events
    assert {e.service for e in agent_events} <= set(INPROCESS_ENVS)
    services_offered = {n.split(".", 1)[0] for n in llm.offered if "." in n}
    assert services_offered and services_offered <= set(INPROCESS_ENVS), services_offered
    manifest = resume_state.load(out)
    assert manifest["sandbox_mode"] == "dryrun"
    assert manifest["days"][0]["managers_ok"] and not manifest["days"][0]["snapshot_ok"]
