"""Slotted arc steps (release arcs) and pinned tasks in AgenticMember -- scripted fake
LLM, in-process world, no network."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from mole.audit.collector import AuditCollector
from mole.generator import agentic_member as am
from mole.generator.agentic_member import ARC_KEY_PREFIX, AgenticMember
from mole.generator.member import NPCConfig
from mole.generator.persona_loader import load_personas
from mole.generator.run import INPROCESS_ENVS, build_context
from mole.llm.base import ChatResponse, ToolCall

DAY = "2026-04-06"
STEP1 = "ARC_STEP_ONE_MARKER register the candidate"
STEP2 = "ARC_STEP_TWO_MARKER approve the candidate"


class _CapturingLLM:
    backend = "fake"
    model_id = "fake-npc"

    def __init__(self):
        self.systems: list[str] = []

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None,
                       seed=None):
        if len(messages) == 2:
            self.systems.append(messages[0].content)
            return ChatResponse(content="", tool_calls=[ToolCall(
                id="c1", name="model_registry.list_checkpoints", arguments={})])
        return ChatResponse(content="done", tool_calls=[])


def _persona(pid="paul.s20"):
    return next(p for p in load_personas(include_holdouts=True) if p.id == pid)


def _sched():
    return [
        {"date": DAY, "step_idx": 0, "directive": STEP1, "slot": "12:04:10",
         "step_id": "release-arc-01:register", "arc_id": "release-arc-01", "role": "release_owner"},
        {"date": DAY, "step_idx": 1, "directive": STEP2, "slot": "13:31:00",
         "step_id": "release-arc-01:approve_a", "arc_id": "release-arc-01", "role": "approver_a"},
    ]


def _member(llm, config=None, **kw):
    return AgenticMember(_persona(), llm=llm, rng_seed=0,
                         config=config or NPCConfig(sessions_per_day=2, loaf_probability=0.0,
                                                    absent_probability=0.0),
                         **kw)


def test_plan_day_adds_dedicated_arc_sessions_at_their_slots():
    m = _member(_CapturingLLM(), benign_arc_schedule=_sched())
    plan = m.plan_day(DAY)
    arc = [(t, k) for t, k in plan if k.startswith(ARC_KEY_PREFIX)]
    assert [k for _, k in arc] == [ARC_KEY_PREFIX + "release-arc-01:register",
                                   ARC_KEY_PREFIX + "release-arc-01:approve_a"]
    assert [t.strftime("%H:%M:%S") for t, _ in arc] == ["12:04:10", "13:31:00"]
    assert all(t.strftime("%Y-%m-%d") == DAY for t, _ in arc)
    # The arc keys never enter the attack / legacy-arc slot pool.
    assert m._today_keys == ["session_0", "session_1"]
    # No arc step on another day.
    assert not [k for _, k in m.plan_day("2026-04-07") if k.startswith(ARC_KEY_PREFIX)]


def test_arc_sessions_survive_pto_and_loafing_and_draw_no_rng():
    # PTO day: the regular sessions go, the arc steps stay.
    m = _member(_CapturingLLM(), config=NPCConfig(sessions_per_day=3, absent_probability=1.0),
                benign_arc_schedule=_sched())
    assert [k for _, k in m.plan_day(DAY)] == [ARC_KEY_PREFIX + "release-arc-01:register",
                                              ARC_KEY_PREFIX + "release-arc-01:approve_a"]
    assert m._today_keys == []
    # Loafing never drops an arc step.
    m = _member(_CapturingLLM(), config=NPCConfig(sessions_per_day=3, loaf_probability=1.0,
                                                  absent_probability=0.0),
                benign_arc_schedule=_sched())
    assert len(m.plan_day(DAY)) == 2
    # The regular plan (and RNG stream) is the same with and without arc steps.
    a = _member(_CapturingLLM())
    b = _member(_CapturingLLM(), benign_arc_schedule=_sched())
    for d in (DAY, "2026-04-07", "2026-04-08"):
        pa = a.plan_day(d)
        pb = [x for x in b.plan_day(d) if not x[1].startswith(ARC_KEY_PREFIX)]
        assert pa == pb
    assert a.rng.random() == b.rng.random()


def test_arc_session_runs_its_step_at_its_slot_and_is_recorded(tmp_path: Path):
    records: list[dict] = []

    async def _run():
        collector = AuditCollector(jsonl_path=tmp_path / "a.jsonl")
        ctx = await build_context(collector, tmp_dir=tmp_path, envs=INPROCESS_ENVS,
                                  seed_world=True)
        llm = _CapturingLLM()
        m = _member(llm, benign_arc_schedule=_sched(), transcript_sink=records.append)
        plan = sorted(m.plan_day(DAY), key=lambda x: x[0])
        for t, key in plan:
            await m.run_at(ctx, t.strftime("%Y-%m-%dT%H:%M:%SZ"), key)
        collector.close()
        return llm, collector

    llm, collector = asyncio.run(_run())
    assert len(llm.systems) == 4
    regular = llm.systems[:2]
    assert all(STEP1 not in s and STEP2 not in s for s in regular)
    assert STEP1 in llm.systems[2] and STEP2 not in llm.systems[2]
    assert STEP2 in llm.systems[3]
    arc_recs = [r for r in records if "release_arc" in r]
    assert [r["release_arc"]["step_id"] for r in arc_recs] == [
        "release-arc-01:register", "release-arc-01:approve_a"]
    assert all(r["session_mode"] == "benign" for r in records)
    assert all("release_arc" not in r for r in records[:2])
    # Each arc session's events carry timestamps from its own slot, not the day-chain.
    by_task = {r["task_id"]: r for r in arc_recs}
    for e in collector.events:
        rec = by_task.get(e.task_id)
        if rec is not None:
            assert e.ts[:16] >= f"{DAY}T{rec['release_arc']['slot'][:5]}", (e.ts, rec)


def test_failing_arc_step_is_logged_and_later_steps_still_run(tmp_path: Path, monkeypatch,
                                                              caplog):
    real_loop = am.run_agent_loop
    calls = {"n": 0}

    async def flaky_loop(**kw):
        calls["n"] += 1
        if STEP1 in kw["initial_messages"][0].content:
            raise RuntimeError("agent crashed mid-step")
        return await real_loop(**kw)

    monkeypatch.setattr(am, "run_agent_loop", flaky_loop)
    records: list[dict] = []

    async def _run():
        collector = AuditCollector(jsonl_path=tmp_path / "a.jsonl")
        ctx = await build_context(collector, tmp_dir=tmp_path, envs=INPROCESS_ENVS,
                                  seed_world=True)
        llm = _CapturingLLM()
        m = _member(llm, config=NPCConfig(sessions_per_day=1, absent_probability=0.0,
                                          loaf_probability=1.0),
                    benign_arc_schedule=_sched(), transcript_sink=records.append)
        for t, key in sorted(m.plan_day(DAY), key=lambda x: x[0]):
            await m.run_at(ctx, t.strftime("%Y-%m-%dT%H:%M:%SZ"), key)   # must not raise
        collector.close()
        return llm

    with caplog.at_level(logging.ERROR, logger="mole.generator.agentic_member"):
        llm = asyncio.run(_run())
    assert calls["n"] == 2
    assert any("release arc step release-arc-01:register FAILED" in r.getMessage()
               for r in caplog.records)
    assert [r["release_arc"]["step_id"] for r in records] == ["release-arc-01:approve_a"]
    assert STEP2 in llm.systems[-1]


def test_unslotted_benign_arc_entries_keep_the_legacy_path():
    legacy = [{"date": DAY, "step_idx": 0, "directive": "LEGACY_ARC_STEP"}]
    m = _member(_CapturingLLM(), benign_arc_schedule=legacy)
    plan = m.plan_day(DAY)
    assert not [k for _, k in plan if k.startswith(ARC_KEY_PREFIX)]
    assert m._slotted_arc_steps == {}


def test_pinned_task_is_the_first_benign_session_of_its_day_only(tmp_path: Path):
    records: list[dict] = []
    pins = {DAY: {"task_id": "legal/14", "task": "PIN_MARKER review ws={ws}"}}

    async def _run():
        collector = AuditCollector(jsonl_path=tmp_path / "a.jsonl")
        ctx = await build_context(collector, tmp_dir=tmp_path, envs=INPROCESS_ENVS,
                                  seed_world=True)
        llm = _CapturingLLM()
        m = _member(llm, config=NPCConfig(sessions_per_day=3, loaf_probability=0.0,
                                          absent_probability=0.0),
                    pinned_tasks=pins, transcript_sink=records.append)
        for d in (DAY, "2026-04-07"):
            for t, key in sorted(m.plan_day(d), key=lambda x: x[0]):
                await m.run_at(ctx, t.strftime("%Y-%m-%dT%H:%M:%SZ"), key)
        collector.close()
        return llm

    llm = asyncio.run(_run())
    assert len(llm.systems) == 6
    assert "PIN_MARKER review ws=paul-s20" in llm.systems[0]
    assert all("PIN_MARKER" not in s for s in llm.systems[1:])
    assert records[0]["pinned_task_id"] == "legal/14"
    assert all("pinned_task_id" not in r for r in records[1:])


def test_pinned_day_overrides_pto():
    pins = {DAY: {"task_id": "legal/14", "task": "PIN"}}
    m = _member(_CapturingLLM(), config=NPCConfig(sessions_per_day=2, absent_probability=1.0,
                                                  loaf_probability=0.0),
                pinned_tasks=pins)
    assert [k for _, k in m.plan_day(DAY)] == ["session_0", "session_1"]
    assert m.plan_day("2026-04-07") == []
