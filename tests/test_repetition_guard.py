"""Same-call repetition guard in the agent loop (brief T1 i): the (limit+1)-th
identical tool call (name + normalised arguments) in a session is answered with an
error tool message instead of being executed, and counted."""
from __future__ import annotations

import asyncio

import pytest

from mole.agent.loop import ToolResult, run_agent_loop, resolve_max_identical_calls
from mole.llm import ChatMessage, ChatResponse, TokenUsage, ToolCall, ToolSchema


class _LLM:
    backend = model_id = "scripted"

    def __init__(self, turns):
        self._turns = list(turns)

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None, seed=None):
        if not self._turns:
            return ChatResponse(content="done", tool_calls=[], usage=TokenUsage(), backend="s",
                                model_id="s", finish_reason="stop")
        calls = self._turns.pop(0)
        return ChatResponse(content="", tool_calls=calls, usage=TokenUsage(), backend="s",
                            model_id="s", finish_reason="tool_calls")


def _tc(i, name, **args):
    return ToolCall(id=f"c{i}", name=name, arguments=args)


def _run(turns, **kw):
    executed = []

    async def dispatcher(tc):
        executed.append((tc.name, dict(tc.arguments)))
        return ToolResult(tool_call_id=tc.id, name=tc.name, content="ok")

    res = asyncio.run(run_agent_loop(
        llm=_LLM(turns), initial_messages=[ChatMessage(role="system", content="s"),
                                           ChatMessage(role="user", content="u")],
        tools=[ToolSchema(name="model_registry.tag_approved", description="", parameters={"type": "object"})],
        dispatcher=dispatcher, max_turns=20, **kw))
    return res, executed


def test_fourth_identical_call_is_refused_and_counted():
    approve = dict(checkpoint_id="ckpt-prometheus-v0.3", eval_job_id="job-1")
    turns = [[_tc(i, "model_registry.tag_approved", **approve)] for i in range(6)]
    res, executed = _run(turns)
    assert len(executed) == 3 and res.tool_calls_repeated == 3
    tool_msgs = [m for m in res.messages if m.role == "tool"]
    assert [m.content.startswith("repeated call refused") for m in tool_msgs] == [False] * 3 + [True] * 3
    assert "already been called 3 times" in tool_msgs[3].content
    assert "re-read the earlier result" in tool_msgs[3].content
    assert res.aborted_reason is None and res.finish_reason == "stop"


def test_argument_order_and_formatting_do_not_evade_the_guard():
    a = dict(checkpoint_id="x", eval_job_id="j")
    b = dict(eval_job_id="j", checkpoint_id="x")          # same call, different key order
    turns = [[_tc(1, "t", **a)], [_tc(2, "t", **b)], [_tc(3, "t", **a)], [_tc(4, "t", **b)]]
    res, executed = _run(turns)
    assert len(executed) == 3 and res.tool_calls_repeated == 1


def test_different_arguments_or_names_are_not_repeats():
    turns = [[_tc(i, "t", n=i)] for i in range(6)] + [[_tc(10 + i, f"t{i}", n=0)] for i in range(4)]
    res, executed = _run(turns)
    assert len(executed) == 10 and res.tool_calls_repeated == 0


def test_guard_applies_within_one_turn_and_can_be_disabled(monkeypatch):
    same = [_tc(i, "t", k=1) for i in range(5)]
    res, executed = _run([same])
    assert len(executed) == 3 and res.tool_calls_repeated == 2
    res, executed = _run([same], max_identical_calls=0)
    assert len(executed) == 5 and res.tool_calls_repeated == 0
    monkeypatch.setenv("MOLE_MAX_IDENTICAL_CALLS", "1")
    assert resolve_max_identical_calls() == 1
    res, executed = _run([same])
    assert len(executed) == 1 and res.tool_calls_repeated == 4
    monkeypatch.setenv("MOLE_MAX_IDENTICAL_CALLS", "nope")
    assert resolve_max_identical_calls() == 3
