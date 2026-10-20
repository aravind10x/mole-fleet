"""The objective-bearing benign-template session (Stage 3, brief 07 S5.3; lesson L13 repair).

Under `objective_carrier="benign"` a scenario session uses the honest rich template with the
override text as ONE standing agenda item; under the default carrier nothing changes. The
override text in these tests is a routine placeholder ("add one line noting today's date"),
never an objective of any other kind.
"""
from __future__ import annotations

import asyncio
import collections
import random
from pathlib import Path

from mole.generator.agentic_member import (
    _ELICITATION_PREFIX, AgenticMember, load_task_bank,
)
from mole.generator.member import NPCConfig
from mole.generator.persona_loader import load_personas
from mole.llm.base import ChatResponse
from mole.scenarios.release_sabotage import build_scenario_context

REPO = Path(__file__).resolve().parents[1]
PRIYA = "priya.h18"
PLACEHOLDER = "Add one line to the shared README noting today's date."
DAYS = ["2026-04-06", "2026-04-07"]
SCHEDULE = [{"date": "2026-04-06", "phase": "act", "directive": ""}]


class _Capture:
    backend = model_id = "fake"

    def __init__(self):
        self.sessions: list[tuple[str, str, list[str]]] = []   # (system, user, fed items)
        self._cur: list[str] | None = None

    async def complete(self, messages, *, tools=None, temperature=0.0, max_tokens=None, seed=None):
        if len(messages) == 2:
            self._cur = []
            self.sessions.append((messages[0].content, messages[1].content, self._cur))
        last = messages[-1]
        if last.role == "user" and last.content.startswith("Next on your agenda:"):
            self._cur.append(last.content)
        return ChatResponse(content="done", tool_calls=[])


def _member(llm, sink, *, carrier="insider", elicit_share=None, override=PLACEHOLDER,
            schedule=SCHEDULE, seed=3, sessions_per_day=3):
    persona = next(p for p in load_personas(include_holdouts=True) if p.id == PRIYA)
    cfg = NPCConfig(sessions_per_day=sessions_per_day, loaf_probability=0.0, absent_probability=0.0)
    return AgenticMember(persona, llm=llm, rng_seed=seed, transcript_sink=sink, config=cfg,
                         task_bank=load_task_bank(bank="inprocess"),
                         persona_override=override, campaign_schedule=schedule,
                         planning_mode="scripted", sim_dates=DAYS, rich_sessions=True,
                         max_turns=8, objective_carrier=carrier, elicit_share=elicit_share)


def _run(tmp_path, **kw):
    rows: list[dict] = []
    llm = _Capture()

    async def go():
        ctx, coll = await build_scenario_context(tmp_path)
        m = _member(llm, rows.append, **kw)
        for day in DAYS:
            for t, key in m.plan_day(day):
                await m.run_at(ctx, t.strftime("%Y-%m-%dT%H:%M:%SZ"), key)
        coll.close()
    asyncio.run(go())
    return llm, rows


def test_flag_absent_is_byte_identical_to_the_legacy_path(tmp_path):
    llm_a, rows_a = _run(tmp_path / "a")
    llm_b, rows_b = _run(tmp_path / "b", carrier="insider", elicit_share=None)
    assert [s[:2] for s in llm_a.sessions] == [s[:2] for s in llm_b.sessions]
    assert [r["session_mode"] for r in rows_a] == [r["session_mode"] for r in rows_b]
    assert all("carrier" not in r for r in rows_a)
    k = [r["session_mode"] for r in rows_a].index("attack")
    assert "do the work described in your persona above" in llm_a.sessions[k][0]   # legacy template
    assert llm_a.sessions[k][0].startswith(_ELICITATION_PREFIX[:40])


def test_benign_carrier_uses_the_honest_template_and_feeds_the_objective_once(tmp_path):
    llm, rows = _run(tmp_path, carrier="benign")
    modes = [r["session_mode"] for r in rows]
    assert modes.count("attack") == 1
    k = modes.index("attack")
    system, user, fed = llm.sessions[k]
    honest_system = llm.sessions[(k + 1) % len(llm.sessions)][0]
    assert "This session has several things to handle" in system           # _BENIGN_SYSTEM_BLOCK
    assert system == honest_system                                           # identical to an honest session
    assert not system.startswith(_ELICITATION_PREFIX[:40])
    assert "do the work described in your persona above" not in system
    r = rows[k]
    assert r["carrier"] == "benign" and r["has_insider_persona"] and r["elicit_prefix"] is False
    assert 2 <= r["agenda_len"] <= 4 and 0 <= r["objective_position"] < r["agenda_len"]
    # every item is fed through next_task (the first is fed too: the capture records them all)
    assert len(fed) == r["agenda_len"]
    assert sum(PLACEHOLDER in f for f in fed) == 1
    assert PLACEHOLDER in fed[r["objective_position"]]
    assert PLACEHOLDER not in system and PLACEHOLDER not in user
    # the other items come from the account's own pool
    pool = set(_member(_Capture(), lambda _r: None, carrier="benign")._tasks)
    others = [f for f in fed if PLACEHOLDER not in f]
    assert all(any(t in f for t in pool) for f in others)
    # honest sessions of the same account carry the carrier tag and no objective
    for i, (s, u, f) in enumerate(llm.sessions):
        if i != k:
            assert rows[i]["carrier"] == "benign" and "objective_position" not in rows[i]
            assert all(PLACEHOLDER not in x for x in f)


def test_agenda_length_distribution_matches_the_honest_draw():
    """The carrier draws k = randint(2, 4) with the same RNG calls as an honest rich session."""
    honest = collections.Counter()
    carrier = collections.Counter()
    for seed in range(2000):
        rng = random.Random(seed)
        honest[min(10, rng.randint(2, 4))] += 1
        rng2 = random.Random(seed)
        k = min(10, rng2.randint(2, 4))
        rng2.sample(list(range(10)), k)
        rng2.randrange(k)
        carrier[k] += 1
    assert honest == carrier
    assert set(honest) == {2, 3, 4} and min(honest.values()) > 500


def test_elicit_share_is_matched_between_scenario_and_honest_sessions(tmp_path):
    used = collections.Counter()      # (is_attack, prefix) -> count
    for seed in range(12):
        llm, rows = _run(tmp_path / str(seed), carrier="benign", elicit_share=0.5, seed=seed)
        for r, (system, _u, _f) in zip(rows, llm.sessions):
            flag = system.startswith(_ELICITATION_PREFIX[:40])
            assert flag == r["elicit_prefix"]
            used[(r["session_mode"] == "attack", flag)] += 1
    for attack in (True, False):
        n = used[(attack, True)] + used[(attack, False)]
        share = used[(attack, True)] / n
        assert 0.2 <= share <= 0.8, (attack, share, n)        # both populations draw at p = 0.5


def test_rule_4_role_day_keeps_at_least_one_session_and_leaves_other_days_unchanged():
    persona = next(p for p in load_personas(include_holdouts=True) if p.id == PRIYA)
    cfg = NPCConfig(sessions_per_day=2, loaf_probability=0.9, absent_probability=0.5)
    schedule = [{"date": "2026-04-07", "phase": "act", "directive": ""}]
    kept = 0
    for seed in range(300):
        with_role = AgenticMember(persona, llm=_Capture(), rng_seed=seed, config=cfg,
                                  persona_override=PLACEHOLDER, campaign_schedule=schedule,
                                  planning_mode="scripted", sim_dates=DAYS)
        without = AgenticMember(persona, llm=_Capture(), rng_seed=seed, config=cfg,
                                persona_override=PLACEHOLDER, campaign_schedule=[],
                                planning_mode="scripted", sim_dates=DAYS)
        day1_a, day1_b = with_role.plan_day("2026-04-06"), without.plan_day("2026-04-06")
        day2_a, day2_b = with_role.plan_day("2026-04-07"), without.plan_day("2026-04-07")
        assert day1_a == day1_b                       # a non-role day is byte-identical
        assert len(day2_a) >= 1                       # the role day always has a session
        assert day2_a == day2_b or len(day2_b) == 0   # it differs only where rule 4 bit
        kept += len(day2_b) == 0
        # the RNG stream after both days is identical, so later days stay unchanged
        assert with_role.rng.random() == without.rng.random()
    assert kept > 50                                  # the exemption was exercised


def test_k1_variant_loads_and_plans_one_role(tmp_path):
    from mole.generator import coalitions as co
    assert co.VARIANT_ROLES["f4_shared_doc"]["k1"] == ["editor_1"]
    doc = f"""schema: coalitions-v2
threat: f4_shared_doc
variant: k1
branches:
  T:
    instances:
      - id: T1
        variant: k1
        document: {{service: owncloud, path: /shared/README.md}}
        roles: {{editor_1: {PRIYA}}}
        campaign_window: {{first_day: 1, last_day: 1}}
"""
    p = tmp_path / "c.yaml"
    p.write_text(doc)
    inst = co.load_coalitions(p, "T")
    assert len(inst) == 1 and inst[0].roles == {"editor_1": PRIYA} and inst[0].window == (1, 1)
