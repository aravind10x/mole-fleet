"""Per-turn tool-call cap in the agent loop (cost / runaway guard).

A model that emits hundreds of tool calls in one turn gets only the first `cap`
executed; the overflow is answered with error tool messages, counted in
`tool_calls_dropped`, and a session that keeps flooding ends as "tool_flood".
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import pytest

from mole.agent.loop import (
    DEFAULT_MAX_TOOL_CALLS_PER_TURN,
    ToolResult,
    resolve_max_tool_calls_per_turn,
    run_agent_loop,
)
from mole.llm import ChatMessage, ChatResponse, TokenUsage, ToolCall, ToolSchema

REPO = Path(__file__).resolve().parents[1]


def _calls(n: int, turn: int = 1) -> list[ToolCall]:
    return [ToolCall(id=f"t{turn}c{i}", name="plane.add_comment", arguments={"i": i})
            for i in range(n)]


def _resp(tool_calls=None, content="") -> ChatResponse:
    return ChatResponse(content=content, tool_calls=tool_calls or [],
                        usage=TokenUsage(input_tokens=1, output_tokens=1),
                        backend="scripted", model_id="scripted-1", finish_reason="stop")


class _ScriptedLLM:
    backend = "scripted"
    model_id = "scripted-1"

    def __init__(self, responses):
        self._responses = list(responses)

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None,
                       seed=None):
        return self._responses.pop(0) if self._responses else _resp(content="done")


def _run(llm, *, max_turns=10, **kw):
    executed: list[str] = []

    async def dispatcher(tc: ToolCall) -> ToolResult:
        executed.append(tc.id)
        return ToolResult(tool_call_id=tc.id, name=tc.name, content="ok")

    result = asyncio.run(run_agent_loop(
        llm=llm,
        initial_messages=[ChatMessage(role="system", content="s"),
                          ChatMessage(role="user", content="u")],
        tools=[ToolSchema(name="plane.add_comment", description="", parameters={})],
        dispatcher=dispatcher, max_turns=max_turns, **kw))
    return result, executed


@pytest.fixture(autouse=True)
def _no_env_cap(monkeypatch):
    monkeypatch.delenv("MOLE_MAX_TOOL_CALLS_PER_TURN", raising=False)


def test_default_cap_executes_first_24_and_drops_the_rest(caplog):
    assert DEFAULT_MAX_TOOL_CALLS_PER_TURN == 24
    calls = _calls(30)
    with caplog.at_level(logging.WARNING, logger="mole.agent.loop"):
        result, executed = _run(_ScriptedLLM([_resp(calls), _resp(content="done")]),
                                account="alice.k")
    assert executed == [c.id for c in calls[:24]]          # first 24, in order
    assert result.tool_calls_dropped == 6
    assert [tc.id for tc in result.tool_calls_made] == executed
    assert result.aborted_reason is None
    tool_msgs = [m for m in result.messages if m.role == "tool"]
    # every call in the turn gets exactly one tool reply, in call order
    assert [m.tool_call_id for m in tool_msgs] == [c.id for c in calls]
    dropped = tool_msgs[24:]
    assert all(m.content == "dropped: more than 24 tool calls in one turn; "
                            "make fewer calls per turn" for m in dropped)
    assert all(m.content == "ok" for m in tool_msgs[:24])
    warns = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warns) == 1
    msg = warns[0].getMessage()
    assert "alice.k" in msg and "turn=1" in msg and "dropped 6" in msg


def test_at_or_under_cap_is_unchanged():
    calls = _calls(24)
    capped, ex_capped = _run(_ScriptedLLM([_resp(calls), _resp(content="done")]))
    legacy, ex_legacy = _run(_ScriptedLLM([_resp(calls), _resp(content="done")]),
                             max_tool_calls_per_turn=0)          # guard disabled
    assert ex_capped == ex_legacy == [c.id for c in calls]
    assert capped.tool_calls_dropped == 0
    assert [m.to_openai() for m in capped.messages] == \
        [m.to_openai() for m in legacy.messages]


def test_cap_configurable_via_kwarg():
    result, executed = _run(_ScriptedLLM([_resp(_calls(8)), _resp(content="done")]),
                            max_tool_calls_per_turn=5)
    assert len(executed) == 5 and result.tool_calls_dropped == 3
    assert "more than 5 tool calls" in [m for m in result.messages
                                        if m.role == "tool"][-1].content


def test_cap_configurable_via_env(monkeypatch):
    monkeypatch.setenv("MOLE_MAX_TOOL_CALLS_PER_TURN", "5")
    assert resolve_max_tool_calls_per_turn() == 5
    assert resolve_max_tool_calls_per_turn(7) == 7          # kwarg wins over env
    result, executed = _run(_ScriptedLLM([_resp(_calls(8)), _resp(content="done")]))
    assert len(executed) == 5 and result.tool_calls_dropped == 3


def test_repeated_flooding_trips_tool_flood(monkeypatch):
    # cap 5 -> the circuit opens once total drops exceed 15. 10 calls/turn drops 5
    # per turn: 5, 10, 15 (not yet), 20 -> abort on turn 4 of a 30-turn budget.
    # (The flood repeats identical calls; the same-call guard is off for this test.)
    monkeypatch.setenv("MOLE_MAX_IDENTICAL_CALLS", "0")
    llm = _ScriptedLLM([_resp(_calls(10, turn=t)) for t in range(1, 31)])
    result, executed = _run(llm, max_turns=30, max_tool_calls_per_turn=5)
    assert result.aborted_reason == "tool_flood"
    assert result.turn_count == 4
    assert result.tool_calls_dropped == 20
    assert len(executed) == 20
    # conversation still well-formed: every assistant tool call has a tool reply
    asked = [tc.id for m in result.messages if m.role == "assistant"
             for tc in (m.tool_calls or [])]
    answered = [m.tool_call_id for m in result.messages if m.role == "tool"]
    assert asked == answered


def test_drops_at_threshold_do_not_trip_tool_flood():
    # exactly 3 x cap drops (15) is tolerated; the session ends normally.
    llm = _ScriptedLLM([_resp(_calls(10, turn=t)) for t in range(1, 4)]
                       + [_resp(content="done")])
    result, _ = _run(llm, max_turns=30, max_tool_calls_per_turn=5)
    assert result.tool_calls_dropped == 15
    assert result.aborted_reason is None


class _FloodOnceThenStop:
    """First turn: `n` in-process tool calls; next turn: stop."""
    backend = "fake"
    model_id = "fake"

    def __init__(self, n: int):
        self.n = n
        self.calls = 0
        self.floods = 0          # turns that emitted the n-call burst

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None,
                       seed=None):
        self.calls += 1
        if self.calls % 2 == 1:
            self.floods += 1
            return ChatResponse(content="", tool_calls=[
                ToolCall(id=f"c{self.calls}_{i}", name="model_registry.list_checkpoints",
                         arguments={}) for i in range(self.n)])
        return ChatResponse(content="done", tool_calls=[])


def test_simulate_dryrun_records_tool_calls_dropped(tmp_path, monkeypatch):
    from mole.generator.run import simulate
    monkeypatch.setenv("MOLE_MAX_IDENTICAL_CALLS", "0")      # the flood repeats one call
    out = tmp_path / "flood.jsonl"
    llm = _FloodOnceThenStop(7)
    coll = asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun", llm=llm,
                                n_personas=1, n_days=1, out_path=out, seed=0,
                                sessions_per_day=1, max_turns=4,
                                max_tool_calls_per_turn=3))
    recs = [json.loads(line) for line in
            out.with_suffix(".transcripts.jsonl").read_text().splitlines() if line]
    assert recs and llm.floods >= 1
    # rich sessions may hand the agent more agenda items, so a session can flood on
    # several turns: each 7-call burst runs 3 and drops 4.
    assert sum(r["tool_calls_dropped"] for r in recs) == 4 * llm.floods
    assert all(r["tool_calls_dropped"] > 0 for r in recs)
    agent_events = [e for e in coll.events if e.account_kind == "background_llm_agent"
                    and e.action == "list_checkpoints"]
    assert len(agent_events) == 3 * llm.floods          # only the capped calls ran


def test_simulate_dryrun_normal_session_records_zero_dropped(tmp_path):
    from mole.generator.run import simulate
    out = tmp_path / "normal.jsonl"
    asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun", llm=_FloodOnceThenStop(2),
                         n_personas=1, n_days=1, out_path=out, seed=0,
                         sessions_per_day=1, max_turns=4))
    recs = [json.loads(line) for line in
            out.with_suffix(".transcripts.jsonl").read_text().splitlines() if line]
    assert recs and all(r["tool_calls_dropped"] == 0 for r in recs)


def test_sim_runner_threads_the_flag(monkeypatch, tmp_path):
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
                          "--out", str(tmp_path / "x.jsonl"),
                          "--max-tool-calls-per-turn", "5"])
    assert rc == 0 and seen["max_tool_calls_per_turn"] == 5
    seen.clear()
    sim_runner.main(["--smoke", "--mode", "rules", "--no-docker", "--days", "1",
                     "--out", str(tmp_path / "y.jsonl")])
    assert seen["max_tool_calls_per_turn"] is None      # -> env / default 24 in the loop


def test_simulate_audit_log_unchanged_for_sessions_under_the_cap(tmp_path):
    """A normal session (<= cap calls per turn) writes the same audit bytes with the
    guard at its default as with the guard disabled (the pre-cap code path)."""
    from mole.generator.run import simulate
    logs = []
    for name, cap in (("default", None), ("disabled", 0)):
        out = tmp_path / f"{name}.jsonl"
        asyncio.run(simulate(mode="agentic", sandbox_mode="dryrun",
                             llm=_FloodOnceThenStop(DEFAULT_MAX_TOOL_CALLS_PER_TURN),
                             n_personas=2, n_days=1, out_path=out, seed=0,
                             sessions_per_day=1, max_turns=4,
                             max_tool_calls_per_turn=cap))
        logs.append(out.read_text().splitlines())

    # event_id / task_id are fresh uuids, real_ts (perf_counter) and wall_ts (wall clock)
    # vary per run, and rich sessions
    # advance the sim `ts` by real elapsed time (sub-second jitter): those differ
    # between ANY two runs. Every other field, and the event order, must match.
    def _norm(line: str) -> str:
        rec = json.loads(line)
        for k in ("event_id", "task_id", "real_ts", "wall_ts", "ts"):
            rec.pop(k, None)
        return json.dumps(rec, sort_keys=True)

    assert logs[0] and len(logs[0]) == len(logs[1])
    assert [_norm(x) for x in logs[0]] == [_norm(x) for x in logs[1]]
