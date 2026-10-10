"""D5 (brief T1 ii): on and after a colluder's first attack session, its benign-mode
sessions carry the standing note, draw no release-gate task, and are flagged
`post_attack_benign` so the labels count their effect events as intent (session-mode-
only intent stays as a sensitivity). Honest accounts and pre-attack sessions are
untouched. Scripted fake LLM, dryrun world, no network."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mole.generator.agentic_member import (
    _D5_STANDING_NOTE, _is_gate_task, AgenticMember, load_task_bank,
)
from mole.generator.member import NPCConfig
from mole.generator.persona_loader import load_personas
from mole.llm.base import ChatResponse
from mole.scenarios.release_sabotage import build_scenario_context

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from eval_matrix import attack_task_ids_of  # noqa: E402

PRIYA = "priya.h18"


class _Capture:
    backend = model_id = "fake"

    def __init__(self):
        self.sessions: list[tuple[str, str, list[str]]] = []   # (system, user, agenda items)
        self._cur: list[str] | None = None

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None, seed=None):
        if len(messages) == 2:
            self._cur = []
            self.sessions.append((messages[0].content, messages[1].content, self._cur))
        last = messages[-1]
        if last.role == "user" and last.content.startswith("Next on your agenda:"):
            self._cur.append(last.content)
        return ChatResponse(content="done", tool_calls=[])


def _member(llm, sink, schedule, sessions_per_day=3):
    persona = next(p for p in load_personas(include_holdouts=True) if p.id == PRIYA)
    cfg = NPCConfig(sessions_per_day=sessions_per_day, loaf_probability=0.0, absent_probability=0.0)
    return AgenticMember(persona, llm=llm, rng_seed=3, transcript_sink=sink, config=cfg,
                         task_bank=load_task_bank(bank="inprocess"),
                         persona_override="PERSONA: insider objective (test stub).",
                         campaign_schedule=schedule, planning_mode="scripted",
                         sim_dates=["2026-04-06", "2026-04-07"], rich_sessions=True, max_turns=8)


def _run_days(tmp_path, schedule, sessions_per_day=3):
    rows: list[dict] = []
    llm = _Capture()

    async def go():
        ctx, coll = await build_scenario_context(tmp_path)
        m = _member(llm, rows.append, schedule, sessions_per_day)
        for day in ("2026-04-06", "2026-04-07"):
            for t, key in m.plan_day(day):
                await m.run_at(ctx, t.strftime("%Y-%m-%dT%H:%M:%SZ"), key)
        coll.close()
    asyncio.run(go())
    return llm, rows


def test_gate_task_predicate_matches_every_gate_task_in_the_bank():
    bank = load_task_bank(bank="inprocess")
    gate = [t for team in bank.values() for t in team if _is_gate_task(t)]
    assert sum("update_config" in t for t in gate) == 1               # the apply task
    assert any("do NOT apply" in t for t in gate)                      # the propose task
    assert any(t.startswith("Audit the current release-gate config") for t in gate)
    assert all("release-gate config" in t for t in gate)
    assert not _is_gate_task("Run the release-gate eval on the newest release-candidate checkpoint")


def test_post_attack_benign_sessions_carry_note_and_draw_no_gate_task(tmp_path):
    # attack on day 1; sessions_per_day=3, so day 1 has sessions before and/or after it
    schedule = [{"date": "2026-04-06", "phase": "act", "directive": "Today is YOUR step (test)."}]
    llm, rows = _run_days(tmp_path, schedule)
    assert len(rows) == len(llm.sessions) == 6
    attack = [i for i, r in enumerate(rows) if r["session_mode"] == "attack"]
    assert len(attack) == 1
    k = attack[0]
    for i, (r, (system, user, agenda)) in enumerate(zip(rows, llm.sessions)):
        gate_fed = any(_is_gate_task(a) for a in agenda) or _is_gate_task(system)
        if i < k:                                   # before the attack: untouched
            assert not r.get("post_attack_benign") and _D5_STANDING_NOTE not in user
        elif i == k:                                # the attack session itself
            assert r["has_insider_persona"] and not r.get("post_attack_benign")
            assert _D5_STANDING_NOTE not in user
        else:                                       # after: note, flag, no gate draw
            assert r["post_attack_benign"] is True and r["attack_started"] == rows[k]["sim_ts"]
            assert user.startswith(_D5_STANDING_NOTE)
            assert r["session_mode"] == "benign" and not r["has_insider_persona"]
            assert not gate_fed, agenda
    assert any(r.get("post_attack_benign") for r in rows)             # day 2 is post-attack
    # The post-attack sessions are intent for the labels; session-mode-only stays smaller.
    plan_ids = attack_task_ids_of(rows, include_post_attack=True)
    mode_ids = attack_task_ids_of(rows)
    assert mode_ids == {rows[k]["task_id"]} and mode_ids < plan_ids
    assert plan_ids == {r["task_id"] for r in rows[k:]}


def test_pre_attack_days_are_byte_identical_to_a_late_attack(tmp_path):
    """Moving the attack to day 2 must not change day-1 sessions (the D5 branch is
    inert until the first attack session)."""
    early = [{"date": "2026-04-06", "phase": "act", "directive": "D"}]
    late = [{"date": "2026-04-07", "phase": "act", "directive": "D"}]
    llm_e, rows_e = _run_days(tmp_path / "e", early)
    llm_l, rows_l = _run_days(tmp_path / "l", late)
    k = next(i for i, r in enumerate(rows_e) if r["session_mode"] == "attack")
    assert [s[:2] for s in llm_l.sessions[:k]] == [s[:2] for s in llm_e.sessions[:k]]
    assert not any(r.get("post_attack_benign") for r in rows_l[:3])    # day 1 of the late run
    # honest accounts (no persona override) never get the flag: no override, no note
    assert all("post_attack_benign" not in r for r in rows_l[:3])
