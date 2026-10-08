"""--attack-rate 0.0 / --no-insiders must yield an HONEST world in every planning mode.

Regression: the deterministic planners (single / scripted) built attack schedules for
insiders regardless of attack_session_rate (the rate was only read on the legacy
coin-flip path), so a run launched with --attack-rate 0.0 still had one attack session
per insider per scheduled day. With rate <= 0 every insider must get an explicit empty
schedule [] (NOT None, which routes to the coin-flip) and the agentic planner must not
author one over it.
"""
from __future__ import annotations

import asyncio
import logging
import random
import sys
from datetime import date
from pathlib import Path

import pytest

from mole.generator.run import _weekday_dates, campaign_schedule_for

REPO = Path(__file__).resolve().parents[1]

DATES = _weekday_dates(date(2026, 4, 6), 10)

# A solo insider, a shadow insider and a collusion-role insider. Shadow and solo are
# indistinguishable to the planner (no role); collusion carries a role.
PERSONAS = {"bob.li": "solo", "shadow.x": "shadow", "colluder.y": "collusion"}
THREATS = {"bob.li": "01_ip_theft", "shadow.x": "06_weight_exfil",
           "colluder.y": "c1_release_bypass"}
ROLES = {"colluder.y": "approver_1"}
LEVELS = {"bob.li": "s0", "shadow.x": "s1", "colluder.y": "s0"}


def _sched(account_id: str, planning: str, rate: float):
    return campaign_schedule_for(
        account_id, 3, planning=planning, persona_map=PERSONAS, threat_map=THREATS,
        role_map=ROLES, level_map=LEVELS, sim_dates=DATES, seed=0, campaign_days=4,
        attack_session_rate=rate)


@pytest.mark.parametrize("planning", ["single", "scripted", "agentic", "coinflip"])
@pytest.mark.parametrize("account_id", list(PERSONAS))
@pytest.mark.parametrize("rate", [0.0, -1.0])
def test_rate_zero_gives_every_insider_an_explicit_empty_schedule(account_id, planning, rate):
    assert _sched(account_id, planning, rate) == []


def test_default_rate_behaviour_unchanged():
    # solo + shadow get a non-empty schedule in both deterministic modes ...
    for acct in ("bob.li", "shadow.x"):
        assert _sched(acct, "single", 0.20), acct
        assert _sched(acct, "scripted", 0.20), acct
    # ... collusion is disabled ([]) in single-day mode but scheduled in scripted mode,
    assert _sched("colluder.y", "single", 0.20) == []
    assert _sched("colluder.y", "scripted", 0.20)
    # agentic / coinflip defer to the member (None); benign members always get None.
    for planning in ("agentic", "coinflip"):
        assert _sched("bob.li", planning, 0.20) is None
    assert _sched("not.an.insider", "single", 0.20) is None
    assert _sched("not.an.insider", "single", 0.0) is None


def test_default_rate_schedules_match_the_builders():
    from mole.generator.campaign import build_campaign, build_single_day
    assert _sched("bob.li", "single", 0.2) == build_single_day(DATES, random.Random(3), k=4)
    assert _sched("bob.li", "scripted", 0.2) == build_campaign(
        "01_ip_theft", DATES, random.Random(3), role=None, stealth_level="s0")


def test_agentic_member_does_not_author_over_an_explicit_empty_schedule(tmp_path):
    from mole.agent.tools import build_tools_for
    from mole.audit.collector import AuditCollector
    from mole.generator.agentic_member import AgenticMember
    from mole.generator.member import NPCConfig
    from mole.generator.persona_loader import load_personas
    from mole.generator.run import build_context
    from mole.llm.base import ChatResponse, ToolCall

    class _LLM:
        backend = "fake"
        model_id = "fake"

        def __init__(self, tool_name):
            self.tool_name = tool_name
            self.planning_calls = 0
            self.systems: list[str] = []

        async def complete(self, messages, *, tools=None, **kw):
            if tools is None:                       # the agentic planning call
                self.planning_calls += 1
                return ChatResponse(content="2026-04-06", tool_calls=[])
            if len(messages) == 2:                  # session start
                self.systems.append(messages[0].content)
                return ChatResponse(content="", tool_calls=[
                    ToolCall(id="c1", name=self.tool_name, arguments={})])
            return ChatResponse(content="done", tool_calls=[])

    async def _run():
        collector = AuditCollector(jsonl_path=tmp_path / "npc.jsonl")
        ctx = await build_context(collector, tmp_dir=tmp_path)
        tools, _ = build_tools_for(ctx)
        name = next(t.name for t in tools if t.name in (
            "model_registry.list_checkpoints", "eval_server.baseline", "secrets_store.list_keys"))
        llm = _LLM(name)
        persona = next(p for p in load_personas(include_holdouts=True) if p.id == "bob.li")
        m = AgenticMember(persona, llm=llm,
                          config=NPCConfig(sessions_per_day=1, loaf_probability=0.0),
                          rng_seed=0, persona_override="OBJECTIVE_MARKER",
                          attack_session_rate=0.0, campaign_schedule=[],
                          planning_mode="agentic", campaign_days=1,
                          sim_dates=["2026-04-06"])
        await m.run_day(ctx, "2026-04-06")
        collector.close()
        return llm, m

    llm, m = asyncio.run(_run())
    assert llm.planning_calls == 0
    assert m.campaign_schedule == []
    assert llm.systems and all("OBJECTIVE_MARKER" not in s for s in llm.systems)


def _sim_runner_kwargs(monkeypatch, tmp_path, extra):
    for p in (REPO, REPO / "scripts"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import sim_runner
    seen: dict = {}

    async def _fake_simulate(**kw):
        seen.update(kw)

        class _C:
            events: list = []
        return _C()

    monkeypatch.setattr(sim_runner, "simulate", _fake_simulate)
    rc = sim_runner.main(["--smoke", "--mode", "rules", "--no-docker", "--days", "1",
                          "--out", str(tmp_path / "x.jsonl"), *extra])
    assert rc == 0
    return seen


def test_sim_runner_no_insiders_forces_rate_zero(monkeypatch, tmp_path):
    kw = lambda extra: _sim_runner_kwargs(monkeypatch, tmp_path, extra)  # noqa: E731
    assert kw(["--no-insiders"])["attack_session_rate"] == 0.0
    assert kw(["--no-insiders", "--attack-rate", "0.5"])["attack_session_rate"] == 0.0
    assert kw([])["attack_session_rate"] == 0.20
    assert kw(["--attack-rate", "0.0"])["attack_session_rate"] == 0.0


def test_simulate_rate_zero_logs_once_and_plans_no_attack(tmp_path, caplog, monkeypatch):
    """Through simulate() (dryrun, fake LLM, no network): with rate 0 the INFO line fires
    once and every insider member receives the explicit empty schedule."""
    from mole.generator import run as run_mod
    from mole.llm.base import ChatResponse

    class _Stop:
        backend = "fake"
        model_id = "fake"

        async def complete(self, messages, **kw):
            return ChatResponse(content="done", tool_calls=[])

    captured: list = []
    orig = run_mod.campaign_schedule_for

    def _spy(account_id, *a, **kw):
        out = orig(account_id, *a, **kw)
        captured.append((account_id, out))
        return out

    monkeypatch.setattr(run_mod, "campaign_schedule_for", _spy)
    with caplog.at_level(logging.INFO, logger=run_mod.logger.name):
        asyncio.run(run_mod.simulate(
            mode="agentic", sandbox_mode="dryrun", llm=_Stop(), n_personas=1, n_days=1,
            out_path=tmp_path / "o.jsonl", seed=0, sessions_per_day=1, max_turns=2,
            insider_persona_map={"bob.li": "X"},
            insider_threat_map={"bob.li": "01_ip_theft"},
            allowed_persona_ids={"bob.li"}, attack_session_rate=0.0))
    msgs = [r.getMessage() for r in caplog.records
            if r.levelno == logging.INFO and "running BENIGN" in r.getMessage()]
    assert len(msgs) == 1, msgs
    assert ("bob.li", []) in captured
