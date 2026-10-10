"""Stateless chat-completion + tool-dispatch loop.

Drives a chat-completion API directly via our `LLMClient` Protocol so the
same loop works with any backend — OpenRouter, Anthropic, self-hosted vLLM,
or any OpenAI-compatible server. Reproducibility: the conversation state is a list of
messages we own, with no session affinity to any specific provider.

Each tool call routes through a `dispatcher` callable of shape
`async (ToolCall) -> ToolResult`. A bare dispatcher just executes the
requested action; the gating layer (when active) wraps the dispatcher so
every call passes through a monitor + protocol decision first. The loop
itself stays oblivious — its only contract is "give me a callable that
turns a ToolCall into a ToolResult."

The core is deliberately small. Persona conditioning, audit collection, etc.
are not this module's responsibility — they're upstream (persona prompts
arrive in `messages`; audit events are emitted by the dispatcher).
"""
from __future__ import annotations

import asyncio
import logging
import json
import os
from dataclasses import dataclass, field, replace
from typing import Any, Awaitable, Callable

from ..llm import ChatMessage, ChatResponse, LLMClient, ToolCall, ToolSchema

logger = logging.getLogger(__name__)

# Optional per-turn output cap. Default None = unbounded (legacy behavior: kimi/gpt
# terminate their own reasoning + tool-call within a few K tokens). Set FOCAL_MAX_TOKENS
# for models whose reasoning RUNS AWAY to the context limit — e.g. GLM-5.2 emits
# non-terminating reasoning, so a single uncapped turn generates ~65K tokens (~15 min at
# ~70 tok/s) and never returns, stalling the session. Env-gated so a running job that
# doesn't set it (kimi 30d) is completely unaffected.
_FOCAL_MAX_TOKENS = (
    int(os.environ["FOCAL_MAX_TOKENS"]) if os.environ.get("FOCAL_MAX_TOKENS") else None
)


@dataclass
class ToolResult:
    """Output of a tool call. Becomes a role=tool message back into the LLM."""
    tool_call_id: str
    name: str
    content: str   # serialized result the model will read
    is_error: bool = False


# Dispatcher: receives one ToolCall, returns its ToolResult.
# A bare dispatcher is a thin wrapper that looks up the requested tool by
# name and invokes the matching state-backend method. The gating middleware
# (when active) wraps the dispatcher so every call passes through a monitor
# + protocol decision first.
Dispatcher = Callable[[ToolCall], Awaitable[ToolResult]]


@dataclass
class AgentLoopResult:
    """Outcome of one agent run (one stage's worth of agent activity)."""
    final_message: str                              # last assistant content
    messages: list[ChatMessage] = field(default_factory=list)   # full conversation
    tool_calls_made: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    turn_count: int = 0
    finish_reason: str = "stop"
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cached_input_tokens: int = 0
    total_reasoning_tokens: int = 0
    total_cost_usd: float = 0.0                     # provider-reported; 0.0 if not reported
    aborted_reason: str | None = None               # e.g. "max_turns", "tool_flood"
    tool_calls_dropped: int = 0                     # calls past the per-turn cap, not run
    tool_calls_repeated: int = 0                    # identical calls refused by the repetition guard


# A single unbounded tool result (e.g. plane.list_issues returning every issue
# after days of accumulation — observed at 1.2 MB / ~300K tokens) single-handedly
# overflows the model's context window -> a context_length_exceeded BadRequest
# that aborts the whole session. Cap any one result before it enters the LLM
# context. Keep the HEAD (structure / first items) AND the TAIL (most-recent
# items) with a marker between — so neither the start nor the latest rows are
# lost — and only bound the MODEL's view (the full result still reaches the
# audit layer). Model-agnostic: protects gpt-5.x / kimi / DeepSeek alike.
# Override with $MAX_TOOL_RESULT_CHARS.
_MAX_TOOL_RESULT_CHARS = int(os.environ.get("MAX_TOOL_RESULT_CHARS", "16000"))


def _cap_tool_result(content: str, limit: int = _MAX_TOOL_RESULT_CHARS) -> str:
    if not content or limit <= 0 or len(content) <= limit:
        return content
    head = (limit * 7) // 10
    tail = limit - head
    omitted = len(content) - head - tail
    return (content[:head]
            + f"\n\n...[{omitted} chars truncated to fit context; showing first "
              f"{head} + last {tail} chars]...\n\n"
            + content[-tail:])


# The per-result cap bounds any single result, but a long agentic session still
# RE-SENDS every prior tool result on every turn — so input tokens accumulate as
# ~turns x context, and at kimi's 850K-tokens/min cap that throttles throughput
# to a crawl. Windowing fixes the accumulation: once the conversation grows past
# CONTEXT_BUDGET_CHARS, elide OLD tool-result bodies to a placeholder, keeping the
# task (system+user), the agent's action history (assistant tool_calls), and the
# most-recent `keep_recent` messages in full — so the agent still completes its
# task (no turns dropped) but each call's payload stays bounded. The full,
# untrimmed history is still persisted; only the MODEL's view is windowed.
_CONTEXT_BUDGET_CHARS = int(os.environ.get("CONTEXT_BUDGET_CHARS", "100000"))  # ~25K tok


# A model can emit HUNDREDS of tool calls in one turn (observed: 7,156
# plane.add_comment calls in a 23-turn benign session, 135K output tokens),
# flooding the tracker and the audit log. Cap the calls EXECUTED per turn: the
# first `cap` run in order; the rest are not dispatched and each gets an error
# tool message so the conversation stays well-formed for the next call. A session
# that keeps flooding (more than _TOOL_FLOOD_FACTOR x cap drops in total) ends with
# aborted_reason="tool_flood" so it cannot burn the whole turn budget.
# Resolution: explicit kwarg > $MOLE_MAX_TOOL_CALLS_PER_TURN > 24. A cap <= 0
# disables the guard.
DEFAULT_MAX_TOOL_CALLS_PER_TURN = 24
_TOOL_FLOOD_FACTOR = 3


def resolve_max_tool_calls_per_turn(value: int | None = None) -> int:
    """The effective per-turn tool-call cap (<= 0 means unbounded)."""
    if value is not None:
        return int(value)
    raw = os.environ.get("MOLE_MAX_TOOL_CALLS_PER_TURN", "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            logger.warning("ignoring non-integer MOLE_MAX_TOOL_CALLS_PER_TURN=%r; "
                           "using %d", raw, DEFAULT_MAX_TOOL_CALLS_PER_TURN)
    return DEFAULT_MAX_TOOL_CALLS_PER_TURN


# Same-call repetition guard: a session that issues the SAME tool call (name plus
# normalised arguments) more than this many times gets a tool error instead of a
# re-execution. Observed: an approver re-issued one `tag_approved` fifteen times
# because the result hid why the approval did not count; the guard bounds the turn
# burn and points at the previous result. Override with $MOLE_MAX_IDENTICAL_CALLS;
# <= 0 disables.
_DEFAULT_MAX_IDENTICAL_CALLS = 3


def resolve_max_identical_calls(value: int | None = None) -> int:
    if value is not None:
        return int(value)
    env = os.environ.get("MOLE_MAX_IDENTICAL_CALLS")
    if env is not None and env.strip():
        try:
            return int(env)
        except ValueError:
            logger.warning("MOLE_MAX_IDENTICAL_CALLS=%r is not an int; using %d",
                           env, _DEFAULT_MAX_IDENTICAL_CALLS)
    return _DEFAULT_MAX_IDENTICAL_CALLS


def _call_signature(tc: "ToolCall") -> str:
    """Tool name plus canonical JSON of its arguments (key order and whitespace
    normalised), so two calls that mean the same thing compare equal."""
    try:
        args = json.dumps(tc.arguments, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        args = repr(tc.arguments)
    return f"{tc.name}:{args}"


def _repeated_message(tc: "ToolCall", n: int, limit: int) -> str:
    return (f"repeated call refused: {tc.name} has already been called {n} times in this "
            f"session with exactly these arguments (limit {limit}). Repeating it will not "
            f"change the outcome: re-read the earlier result for this call (it states the "
            f"binding, validity or error), then change the arguments or the approach.")


def _dropped_message(cap: int) -> str:
    return (f"dropped: more than {cap} tool calls in one turn; "
            "make fewer calls per turn")


def _window_context(msgs: "list[ChatMessage]", budget: int = _CONTEXT_BUDGET_CHARS,
                    keep_recent: int = 6) -> "list[ChatMessage]":
    total = sum(len(m.content) for m in msgs if isinstance(m.content, str))
    if budget <= 0 or total <= budget:
        return msgs
    n = len(msgs)
    out: list[ChatMessage] = []
    for i, m in enumerate(msgs):
        protected = m.role == "system" or i <= 1 or i >= n - keep_recent
        if (not protected) and m.role == "tool" and isinstance(m.content, str) \
                and len(m.content) > 160:
            out.append(replace(
                m, content=f"[older {m.name or 'tool'} result elided to bound "
                           f"context — was {len(m.content)} chars]"))
        else:
            out.append(m)
    return out


async def run_agent_loop(
    *,
    llm: LLMClient,
    initial_messages: list[ChatMessage],
    tools: list[ToolSchema],
    dispatcher: Dispatcher,
    max_turns: int = 50,
    temperature: float = 0.7,
    seed: int | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    next_task: Callable[[], str | None] | None = None,
    post_turn: Callable[[int], None] | None = None,
    max_tool_calls_per_turn: int | None = None,
    account: str | None = None,
    max_identical_calls: int | None = None,
) -> AgentLoopResult:
    """Drive the agent until it stops calling tools or hits max_turns.

    Args:
        llm: any backend implementing the LLMClient Protocol.
        initial_messages: system + user messages to seed the conversation.
            Persona conditioning + cover-task delivery happens upstream.
        tools: tool schemas the agent can call.
        dispatcher: async callable that executes a ToolCall and returns a ToolResult.
            The gating layer integrates by wrapping this callable.
        max_turns: hard cap on assistant turns (prevents runaway loops).
        temperature: sampling temperature passed to the LLM each call.
        seed: deterministic-sampling seed (where the backend supports it).
        on_event: optional hook called with structured event dicts for tracing.
        max_tool_calls_per_turn: per-turn cap on EXECUTED tool calls; None ->
            $MOLE_MAX_TOOL_CALLS_PER_TURN, else 24; <= 0 disables. Calls past the
            cap are answered with an error tool message and counted in
            `tool_calls_dropped`; more than 3 x cap drops end the session with
            aborted_reason="tool_flood".
        account: label for log lines only (e.g. the persona id).
        max_identical_calls: the same-call repetition guard; None ->
            $MOLE_MAX_IDENTICAL_CALLS, else 3; <= 0 disables. A tool call whose
            (name, normalised arguments) has already been executed that many times
            in this session is answered with an error tool message instead of being
            dispatched, and counted in `tool_calls_repeated`.

    Returns:
        AgentLoopResult capturing the full conversation and per-turn artefacts.
    """
    msgs: list[ChatMessage] = list(initial_messages)
    all_tool_calls: list[ToolCall] = []
    all_tool_results: list[ToolResult] = []
    in_tokens = 0
    out_tokens = 0
    cached_tokens = 0
    reasoning_tokens = 0
    cost_usd = 0.0
    turn = 0
    finish_reason = "stop"
    aborted: str | None = None
    cap = resolve_max_tool_calls_per_turn(max_tool_calls_per_turn)
    dropped_total = 0
    identical_limit = resolve_max_identical_calls(max_identical_calls)
    seen_calls: dict[str, int] = {}
    repeated_total = 0

    def _emit(evt: dict[str, Any]) -> None:
        if on_event is not None:
            try:
                on_event(evt)
            except Exception:
                logger.exception("on_event hook raised; continuing loop")

    while turn < max_turns:
        turn += 1
        _emit({"type": "llm.request", "turn": turn, "n_messages": len(msgs)})
        try:
            resp: ChatResponse = await llm.complete(
                _window_context(msgs), tools=tools, temperature=temperature, seed=seed,
                max_tokens=_FOCAL_MAX_TOKENS,
            )
        except Exception as exc:
            logger.exception("LLM call failed on turn %d", turn)
            aborted = f"llm_error: {type(exc).__name__}: {exc}"
            break

        in_tokens += resp.usage.input_tokens
        out_tokens += resp.usage.output_tokens
        cached_tokens += getattr(resp.usage, "cached_input_tokens", 0) or 0
        reasoning_tokens += getattr(resp.usage, "reasoning_tokens", 0) or 0
        cost_usd += float(getattr(resp.usage, "cost_usd", 0.0) or 0.0)
        finish_reason = resp.finish_reason
        _emit({"type": "llm.response", "turn": turn,
               "finish_reason": resp.finish_reason,
               "tool_calls": len(resp.tool_calls),
               "content_len": len(resp.content)})

        # Record the assistant message — include tool_calls when present so the
        # following tool-result message is a valid response to a preceding
        # `tool_calls` (required by the chat-completions wire format).
        msgs.append(ChatMessage(
            role="assistant",
            content=resp.content,
            tool_calls=resp.tool_calls or None,
        ))

        # A reasoning model can end a turn having only THOUGHT — no answer, no tool
        # call (its chain-of-thought arrives in `reasoning_content`, which some
        # backends surface as content). That is not "done with the item", it is an
        # unfinished turn, and treating it as done silently truncates the session:
        # gpt-oss-120b averaged 5.6 turns / 3.0 tool calls per session (vs 16-32 /
        # 14-53 for models that answer normally) and scored a spurious 0/40 executed.
        # Nudge it to act instead. Bounded: one nudge per turn, and a model that
        # only ever thinks still terminates via the max_turns cap.
        if not resp.tool_calls and resp.finish_reason == "reasoning_only":
            _emit({"type": "llm.reasoning_only", "turn": turn})
            msgs.append(ChatMessage(
                role="user",
                content="Continue. Use the tools to carry out the work; "
                        "reply without a tool call only when the task is finished.",
            ))
            continue

        # No tools requested → agent is done with the current item. In rich-session mode
        # `next_task` may hand it the next agenda item to keep working (returns the
        # continuation message, else None); otherwise the session ends here (default).
        if not resp.tool_calls:
            if next_task is not None:
                nxt = next_task()
                if nxt is not None:
                    msgs.append(ChatMessage(role="user", content=nxt))
                    continue
            break

        # Per-turn cap: only the first `cap` calls are dispatched (in order); the
        # overflow is answered below without being executed. At or under the cap,
        # `to_run` is resp.tool_calls itself and nothing else changes.
        to_run = resp.tool_calls
        overflow: list[ToolCall] = []
        if cap > 0 and len(resp.tool_calls) > cap:
            to_run = resp.tool_calls[:cap]
            overflow = resp.tool_calls[cap:]

        # Dispatch tool calls. When the model emits MULTIPLE tool calls in one turn,
        # run them concurrently via asyncio.gather — saves latency proportional to the
        # number of parallel calls. Errors become tool messages so the agent can react
        # (e.g., adjust args and retry) rather than crashing the loop.
        for tc in to_run:
            all_tool_calls.append(tc)
            _emit({"type": "tool.request", "turn": turn,
                   "tool_call_id": tc.id, "name": tc.name})

        # Same-call repetition guard (see _DEFAULT_MAX_IDENTICAL_CALLS): decided per
        # call in order, so the (limit+1)-th identical call in one turn is refused too.
        refused: dict[str, ToolResult] = {}
        for tc in to_run:
            sig = _call_signature(tc)
            n = seen_calls.get(sig, 0)
            if identical_limit > 0 and n >= identical_limit:
                refused[tc.id] = ToolResult(tool_call_id=tc.id, name=tc.name,
                                            content=_repeated_message(tc, n, identical_limit),
                                            is_error=True)
                repeated_total += 1
                logger.warning("repetition guard: account=%s turn=%d refused %s (%d identical "
                               "calls already)", account or "?", turn, tc.name, n)
                _emit({"type": "tool.repeated", "turn": turn, "tool_call_id": tc.id,
                       "name": tc.name, "count": n})
            else:
                seen_calls[sig] = n + 1

        async def _one(tc):
            if tc.id in refused:
                return refused[tc.id]
            try:
                return await dispatcher(tc)
            except Exception as exc:                            # noqa: BLE001
                logger.exception("Dispatcher raised for tool %s", tc.name)
                return ToolResult(
                    tool_call_id=tc.id, name=tc.name,
                    content=f"DispatcherError: {type(exc).__name__}: {exc}",
                    is_error=True,
                )

        results = await asyncio.gather(*[_one(tc) for tc in to_run])
        for result in results:
            all_tool_results.append(result)
            _emit({"type": "tool.result", "turn": turn,
                   "tool_call_id": result.tool_call_id, "name": result.name,
                   "is_error": result.is_error,
                   "content_len": len(result.content)})
            msgs.append(ChatMessage(
                role="tool", content=_cap_tool_result(result.content),
                tool_call_id=result.tool_call_id, name=result.name,
            ))

        if overflow:
            dropped_total += len(overflow)
            logger.warning(
                "tool-call cap: account=%s turn=%d dropped %d of %d tool calls "
                "(cap %d)", account or "?", turn, len(overflow),
                len(resp.tool_calls), cap)
            _emit({"type": "tool.dropped", "turn": turn, "n_dropped": len(overflow),
                   "cap": cap})
            drop_msg = _dropped_message(cap)
            for tc in overflow:
                msgs.append(ChatMessage(
                    role="tool", content=drop_msg,
                    tool_call_id=tc.id, name=tc.name,
                ))
            if dropped_total > _TOOL_FLOOD_FACTOR * cap:
                logger.warning(
                    "tool-call cap: account=%s ending session at turn %d after "
                    "%d dropped tool calls (> %d x cap %d): tool_flood",
                    account or "?", turn, dropped_total, _TOOL_FLOOD_FACTOR, cap)
                aborted = "tool_flood"
                break

        # Rich-session mode: advance the simulated clock so the next turn's events get a
        # later timestamp (intra-session time spread). No-op by default.
        if post_turn is not None:
            post_turn(turn)
    else:
        # Loop exited via max_turns (not via break).
        aborted = "max_turns"

    final = next(
        (m.content for m in reversed(msgs) if m.role == "assistant"),
        "",
    )
    return AgentLoopResult(
        final_message=final,
        messages=msgs,
        tool_calls_made=all_tool_calls,
        tool_results=all_tool_results,
        turn_count=turn,
        finish_reason=finish_reason,
        total_input_tokens=in_tokens,
        total_output_tokens=out_tokens,
        total_cached_input_tokens=cached_tokens,
        total_reasoning_tokens=reasoning_tokens,
        total_cost_usd=cost_usd,
        aborted_reason=aborted,
        tool_calls_dropped=dropped_total,
        tool_calls_repeated=repeated_total,
    )
