"""Scripted-scenario injection into a live generated day (Track B plumbing).

The C3 fixture (`mole/scenarios/release_sabotage.py`) is a chain of single-actor
PHASES. This module schedules those phases inside `generator.run.simulate()`:

* `parse_inject_spec` / `build_injection_plan` turn CLI specs such as
  ``attack:s0:self@day0`` or ``legit@day1`` into one plan entry per phase:
  {inject_id, variant, level, ticket, ablate, phase, actor, day_index, slot,
  live_approval}. Slots are spread across the day from a random morning start
  (``--inject-seed``), consecutive phases at least ``max(60, 2*bucket_minutes)``
  sim-minutes apart so two phases never share a bucket (a bucket is gathered
  concurrently; the chain must stay causal).
* `finalize_injection_plan` (called by simulate, which knows the run's real
  start date, e.g. after a branch) adds the sim date and a stable task_id
  (uuid5 of start_date, inject_id and phase) to every entry.
* `InjectionRunner` is a member-shaped object (``persona.id``, ``plan_day``,
  ``run_at``) per ACTOR, so the generator's day plan, bucketing and per-account
  sequencing treat a phase like one more session of that account: it runs in the
  same `asyncio.gather` as the live sessions of its bucket, on its own per-task
  clock (`SimClock.at(slot)` -> `ctx.advance_clock`), under its stable task_id,
  and writes a transcript stub row (``session_mode="attack"`` for a colluder's
  phase, ``"legit"`` otherwise) so `eval_matrix.attack_session_task_ids` and the
  C3 intent labels see the scripted steps.

Timestamps are never backfilled: a phase's events are stamped from its live slot
forward, and `wall_ts` is the real wall clock at emission, like any session.
"""
from __future__ import annotations

import logging
import random
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable

from ..scenarios.release_sabotage import (
    DEPLOY_IF_QUORUM, PHASE_CHAIN, PHASES, VARIANTS, SimClock, Trace, cast, colluders,
    run_phase,
)

logger = logging.getLogger(__name__)

INJECT_KEY_PREFIX = "inject:"
KIND = "background_llm_agent"
TICKETS = ("self", "honest", "none")
ABLATIONS = ("editor", "runner", "approver_routine", "approver_diligent", "no_cosign")
# Phases scheduled with a LIVE honest approver: stop after the colluding approval,
# then a conditional deploy in a later bucket (only if a live approver co-signed).
LIVE_APPROVAL_CHAIN = ("ticket", "editor", "runner", "approval", DEPLOY_IF_QUORUM)
# Phases that run on the second day of a two-day spec ("@day0-day1").
LATE_PHASES = ("approval", "cosign", "deploy", DEPLOY_IF_QUORUM)
WORKDAY_START_MIN = 9 * 60
WORKDAY_END_MIN = 17 * 60
LATEST_START_MIN = 11 * 60 + 30
_NS = uuid.UUID("5a3d8c1e-6b7f-4a0e-9c2d-1f4e7b8a9c0d")

_SPEC_RE = re.compile(
    r"^(?P<variant>attack|legit)"
    r"(?::(?P<level>s[01]))?"
    r"(?::(?P<ticket>self|honest|none))?"
    r"(?::(?P<ablate>editor|runner|approver_routine|approver_diligent|no_cosign|none))?"
    r"@day(?P<day>\d+)(?:-day(?P<day2>\d+))?"
    r"(?:/(?P<phases>[a-z_+]+))?$")


@dataclass(frozen=True)
class InjectSpec:
    """One ``--inject`` argument, parsed. `phases` None = the default chain."""
    variant: str
    level: str = "s0"
    ticket: str | None = "self"
    ablate: str | None = None
    day_index: int = 0
    late_day_index: int | None = None
    phases: tuple[str, ...] | None = None

    @property
    def inject_id(self) -> str:
        parts = [self.variant, self.level]
        if self.variant == "attack":
            parts.append(self.ticket or "none")
            if self.ablate:
                parts.append(self.ablate)
        days = f"day{self.day_index}"
        if self.late_day_index is not None and self.late_day_index != self.day_index:
            days += f"-day{self.late_day_index}"
        return ":".join(parts) + "@" + days


def parse_inject_spec(spec: str) -> InjectSpec:
    """``VARIANT[:LEVEL[:TICKET[:ABLATE]]]@dayN[-dayM][/PHASE+PHASE...]``.

    attack:s0:self@day0      the s0 attack, editor files the ticket, all on sim-day 0
    attack:s0:none@day0-day1 no ticket; approvals and deploy on sim-day 1
    legit@day1               the matched legitimate release on sim-day 1
    attack:s0:self@day0/cosign   only the honest co-sign phase (e.g. to add a scripted
                             second approval to a --inject-live-approval run)"""
    m = _SPEC_RE.match(spec.strip())
    if m is None:
        raise ValueError(
            f"bad --inject spec {spec!r}; expected VARIANT[:LEVEL[:TICKET[:ABLATE]]]@dayN"
            f"[-dayM][/PHASE+...] with VARIANT in {VARIANTS}, TICKET in {TICKETS}, "
            f"ABLATE in {ABLATIONS}, PHASE in {PHASES}")
    g = m.groupdict()
    variant = g["variant"]
    ticket = g["ticket"]
    ablate = None if g["ablate"] in (None, "none") else g["ablate"]
    if variant == "legit" and (ticket or ablate):
        raise ValueError(f"--inject {spec!r}: legit takes no ticket/ablate")
    phases = None
    if g["phases"]:
        phases = tuple(p for p in g["phases"].split("+") if p)
        bad = [p for p in phases if p not in PHASES]
        if bad:
            raise ValueError(f"--inject {spec!r}: unknown phase(s) {bad}; choose from {PHASES}")
    day, day2 = int(g["day"]), (int(g["day2"]) if g["day2"] is not None else None)
    if day2 is not None and day2 < day:
        raise ValueError(f"--inject {spec!r}: dayM must not precede dayN")
    return InjectSpec(variant=variant, level=g["level"] or "s0",
                      ticket=(None if variant == "legit" else
                              (None if ticket == "none" else (ticket or "self"))),
                      ablate=ablate, day_index=day, late_day_index=day2, phases=phases)


def _hhmmss(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}:00"


def build_injection_plan(specs: list[str | InjectSpec], *, n_days: int,
                         bucket_minutes: int = 30, seed: int | None = 0,
                         live_approval: bool = False) -> list[dict[str, Any]]:
    """Phase entries for `specs`, with default slot timings. Deterministic in
    `seed` (the random morning start of each chain); the phase order within a
    chain is fixed. Raises on a day index outside [0, n_days)."""
    rng = random.Random(seed)
    gap = max(60, 2 * max(1, int(bucket_minutes)))
    plan: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for raw in specs:
        spec = parse_inject_spec(raw) if isinstance(raw, str) else raw
        for d in (spec.day_index, spec.late_day_index):
            if d is not None and not (0 <= d < n_days):
                raise ValueError(f"--inject {spec.inject_id}: day index {d} outside the run's "
                                 f"{n_days} day(s)")
        inject_id = spec.inject_id
        seen[inject_id] = seen.get(inject_id, 0) + 1
        if seen[inject_id] > 1:
            inject_id = f"{inject_id}#{seen[inject_id]}"
        actors = cast(spec.variant, spec.level, ticket=spec.ticket, ablate=spec.ablate)
        chain = spec.phases or (LIVE_APPROVAL_CHAIN if (live_approval and spec.variant == "attack")
                                else PHASE_CHAIN)
        phases = [p for p in chain if actors.get(p)]
        late_day = spec.late_day_index if spec.late_day_index is not None else spec.day_index
        groups: list[tuple[int, list[str]]] = []
        if late_day != spec.day_index:
            early = [p for p in phases if p not in LATE_PHASES]
            late = [p for p in phases if p in LATE_PHASES]
            groups = [(spec.day_index, early), (late_day, late)]
        else:
            groups = [(spec.day_index, phases)]
        for day_index, group in groups:
            if not group:
                continue
            latest = max(WORKDAY_START_MIN, min(LATEST_START_MIN,
                                                WORKDAY_END_MIN - (len(group) - 1) * gap))
            start = WORKDAY_START_MIN + rng.randrange(0, latest - WORKDAY_START_MIN + 1)
            for i, phase in enumerate(group):
                plan.append({
                    "inject_id": inject_id, "variant": spec.variant, "level": spec.level,
                    "ticket": spec.ticket, "ablate": spec.ablate, "phase": phase,
                    "actor": actors[phase], "day_index": day_index,
                    "slot": _hhmmss(start + i * gap),
                    "live_approval": bool(live_approval and spec.variant == "attack"),
                })
    for day, ids in _gate_chains_by_day(plan).items():
        if len(ids) > 1:
            logger.warning(
                "injections %s all edit release-gate on sim-day %d; a later chain's gate edit "
                "invalidates the earlier chain's approvals (its deploy is then refused). Put "
                "them on different days (e.g. legit@day1) or in separate branches.", ids, day)
    return plan


def _gate_chains_by_day(plan: list[dict[str, Any]]) -> dict[int, list[str]]:
    """{day_index: [inject_id, ...]} of the chains whose "editor" phase (a release-gate
    edit) falls on that day, in plan order."""
    out: dict[int, list[str]] = {}
    for e in plan:
        if e["phase"] == "editor" and e["inject_id"] not in out.setdefault(e["day_index"], []):
            out[e["day_index"]].append(e["inject_id"])
    return out


def phase_task_id(start_date: str, inject_id: str, phase: str, salt: str = "") -> str:
    """Stable per-phase task id: the same plan in the same corpus (`salt` = the corpus
    stem) on the same start date gives the same ids, so a --resume reuses them; two
    branches of one parent with the same spec get different ids."""
    return uuid.uuid5(_NS, f"mole-inject:{salt}:{start_date}:{inject_id}:{phase}").hex


def finalize_injection_plan(plan: list[dict[str, Any]], *, start_date: str,
                            dates: list[str], salt: str = "") -> list[dict[str, Any]]:
    """Copy of `plan` with `date` (from `dates[day_index]`) and `task_id` filled in,
    in run order (date, slot, chain position). Raises if a day index is outside `dates`."""
    out: list[dict[str, Any]] = []
    for pos, e in enumerate(plan):
        d = int(e["day_index"])
        if not (0 <= d < len(dates)):
            raise ValueError(f"injection {e['inject_id']}/{e['phase']}: day index {d} outside "
                             f"the run's {len(dates)} day(s)")
        out.append({**e, "date": dates[d],
                    "task_id": phase_task_id(start_date, e["inject_id"], e["phase"], salt),
                    "_pos": pos})
    out.sort(key=lambda e: (e["date"], e["slot"], e["_pos"]))
    for e in out:
        e.pop("_pos", None)
    return out


def entry_key(e: dict[str, Any]) -> str:
    return f"{INJECT_KEY_PREFIX}{e['inject_id']}:{e['phase']}"


def slot_datetime(date_iso: str, slot: str) -> datetime:
    base = datetime.fromisoformat(date_iso[:10]).replace(tzinfo=timezone.utc)
    hh, mm, ss = (int(x) for x in (slot.split(":") + ["0", "0"])[:3])
    return base.replace(hour=hh, minute=mm, second=ss)


def transcript_stub(e: dict[str, Any], *, sim_ts: str, trace: Trace, state: dict[str, Any],
                    ok: bool, error: str | None) -> dict[str, Any]:
    """The transcript row of one injected phase: the agentic session record shape with
    no messages, so every transcript reader (attack ids, tallies, cost) works unchanged.
    `session_mode` is "attack" only for a colluder's phase of the attack variant; the
    honest co-signer's phase and every legit phase are "legit"."""
    is_attack = e["variant"] == "attack" and e["actor"] in set(colluders(e["level"]).values())
    return {
        "injection": {
            **{k: e.get(k) for k in ("inject_id", "variant", "level", "ticket", "ablate",
                                     "phase", "day_index", "slot", "live_approval")},
            "ok": ok, "error": error, "steps": len(trace.steps),
            "stopped": state.get("stopped"), "job_id": state.get("job_id"),
            "ticket_id": state.get("ticket_id")},
        "account": e["actor"],
        "account_kind": KIND,
        "task_id": e["task_id"],
        "sim_ts": sim_ts,
        "turn_count": 0,
        "finish_reason": "scripted",
        "aborted_reason": None if ok else f"scripted_error: {error}",
        "input_tokens": 0, "output_tokens": 0, "cached_input_tokens": 0,
        "reasoning_tokens": 0, "cost_usd": 0.0, "tool_calls_dropped": 0,
        "model": "scripted",
        "has_insider_persona": is_attack,
        "session_mode": "attack" if is_attack else "legit",
        "messages": [],
    }


@dataclass
class InjectionRunner:
    """Member-shaped runner for one ACTOR's injected phases. `states` is shared by all
    runners of a run ({inject_id: chain state}); `on_result` receives
    (entry, result) after each phase (simulate records it in the manifest)."""
    actor: str
    entries: list[dict[str, Any]]
    states: dict[str, dict[str, Any]]
    on_result: Callable[[dict[str, Any], dict[str, Any]], None] | None = None
    transcript_sink: Callable[[dict[str, Any]], None] | None = None
    persona: Any = field(init=False)

    def __post_init__(self) -> None:
        self.persona = SimpleNamespace(id=self.actor)
        self._by_key = {entry_key(e): e for e in self.entries}

    def plan_day(self, sim_date_iso: str) -> list[tuple[datetime, str]]:
        day = sim_date_iso[:10]
        return sorted((slot_datetime(day, e["slot"]), entry_key(e))
                      for e in self.entries if e["date"] == day)

    async def run_at(self, ctx: Any, sim_now: str, action_key: str) -> None:
        e = self._by_key[action_key]
        state = self.states.setdefault(e["inject_id"], {})
        clock = SimClock.at(sim_now)
        trace = Trace()
        ok, error = True, None
        try:
            await run_phase(ctx, variant=e["variant"], phase=e["phase"], clock=clock,
                            state=state, level=e["level"], ticket=e["ticket"],
                            ablate=e["ablate"], trace=trace, task_id=e["task_id"])
        except Exception as exc:                                   # noqa: BLE001
            ok, error = False, f"{type(exc).__name__}: {exc}"
            state["stopped"] = f"phase_error:{e['phase']}"
            logger.exception("injection %s/%s (%s) raised", e["inject_id"], e["phase"], e["actor"])
        if self.transcript_sink is not None:
            self.transcript_sink(transcript_stub(e, sim_ts=sim_now, trace=trace, state=state,
                                                 ok=ok, error=error))
        result = {"ok": ok, "error": error, "task_id": e["task_id"], "actor": e["actor"],
                  "sim_ts": sim_now, "end_ts": clock.iso(), "steps": len(trace.steps),
                  "stopped": state.get("stopped"), "state": dict(state)}
        logger.info("injection %s/%s by %s at %s: ok=%s stopped=%s", e["inject_id"],
                    e["phase"], e["actor"], sim_now, ok, state.get("stopped"))
        if self.on_result is not None:
            self.on_result(e, result)


def build_runners(plan: list[dict[str, Any]], *, states: dict[str, dict[str, Any]],
                  on_result: Callable[[dict[str, Any], dict[str, Any]], None] | None,
                  transcript_sink: Callable[[dict[str, Any]], None] | None,
                  ) -> list[InjectionRunner]:
    by_actor: dict[str, list[dict[str, Any]]] = {}
    for e in plan:
        by_actor.setdefault(e["actor"], []).append(e)
    return [InjectionRunner(actor, entries, states, on_result, transcript_sink)
            for actor, entries in by_actor.items()]


def restore_states(results: dict[str, dict[str, Any]], plan: list[dict[str, Any]],
                   ) -> dict[str, dict[str, Any]]:
    """Chain states from a manifest's recorded phase results (for --resume): the
    state snapshot of the LAST phase recorded for each inject_id, in plan order."""
    states: dict[str, dict[str, Any]] = {}
    for e in plan:
        r = (results.get(e["inject_id"]) or {}).get(e["phase"])
        if r and isinstance(r.get("state"), dict):
            states[e["inject_id"]] = dict(r["state"])
    return states


def spec_dicts(specs: list[str | InjectSpec]) -> list[dict[str, Any]]:
    return [asdict(parse_inject_spec(s) if isinstance(s, str) else s) for s in specs]
