"""Redundancy (Stage 3 design 11.12(g); brief 07f B7, 2026-10-23): under
`redundant_role_sessions=True` every session of a scheduled attack-day carries the role's
objective; the default keeps exactly one attack session per attack-day. The planner (day
draw, role order, windows) is untouched. Scripted fake LLM, no network; placeholder persona
text only."""
from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from mole.audit.collector import AuditCollector
from mole.generator.agentic_member import AgenticMember
from mole.generator.member import NPCConfig
from mole.generator.persona_loader import load_personas
from mole.generator.run import build_context

REPO = Path(__file__).resolve().parents[1]
import sys  # noqa: E402
if str(REPO / "tests") not in sys.path:
    sys.path.insert(0, str(REPO / "tests"))
from test_agentic_member_multiday import PERSONA, STAGE_DIR, _CapturingLLM, _benign_tool  # noqa: E402


def _run(redundant: bool, sessions: int = 3, carrier: str = "insider"):
    async def go():
        collector = AuditCollector(jsonl_path=None)
        ctx = await build_context(collector, tmp_dir=None)
        llm = _CapturingLLM(_benign_tool(ctx))
        sched = [{"date": "2026-04-06", "phase": "act", "directive": STAGE_DIR}]
        persona = next(p for p in load_personas() if p.id == "bob.li")
        m = AgenticMember(persona, llm=llm, config=NPCConfig(sessions_per_day=sessions, loaf_probability=0.0),
                          rng_seed=0, persona_override=PERSONA, campaign_schedule=sched,
                          objective_carrier=carrier, redundant_role_sessions=redundant)
        await m.run_day(ctx, "2026-04-06")            # the attack-day
        await m.run_day(ctx, "2026-04-07")            # not scheduled: benign
        return llm, m
    return asyncio.run(go())


def test_default_is_one_attack_session_per_attack_day():
    llm, m = _run(redundant=False)
    assert m.redundant_role_sessions is False
    day1 = [s for s in llm.systems[:3]]
    assert sum(PERSONA in s for s in day1) == 1
    assert all(PERSONA not in s for s in llm.systems[3:])


def test_redundancy_makes_every_session_of_the_attack_day_carry_the_objective():
    llm, m = _run(redundant=True)
    assert m.redundant_role_sessions is True
    assert len(llm.systems) == 6
    day1, day2 = llm.systems[:3], llm.systems[3:]
    assert all(PERSONA in s for s in day1), "every session of the scheduled day is an attack session"
    assert all(STAGE_DIR in s for s in day1)
    assert all(PERSONA not in s for s in day2), "an unscheduled day stays benign"


def test_redundancy_under_the_benign_carrier_marks_every_day_session_attack():
    recs: list[dict] = []

    async def go():
        collector = AuditCollector(jsonl_path=None)
        ctx = await build_context(collector, tmp_dir=None)
        llm = _CapturingLLM(_benign_tool(ctx))
        persona = next(p for p in load_personas() if p.id == "bob.li")
        m = AgenticMember(persona, llm=llm, config=NPCConfig(sessions_per_day=2, loaf_probability=0.0),
                          rng_seed=0, persona_override="routine shared-document upkeep",
                          campaign_schedule=[{"date": "2026-04-06", "phase": "single", "directive": None}],
                          objective_carrier="benign", task_bank={"platform": ["task A {ws}", "task B", "task C"]},
                          transcript_sink=recs.append, redundant_role_sessions=True)
        await m.run_day(ctx, "2026-04-06")
        await m.run_day(ctx, "2026-04-07")
    asyncio.run(go())
    modes = [(r["sim_ts"][:10], r["session_mode"]) for r in recs]
    assert modes.count(("2026-04-06", "attack")) == 2
    assert all(mode == "benign" for d, mode in modes if d == "2026-04-07")


def test_runner_flag_and_manifest_field(tmp_path):
    """sim_runner exposes --redundant-role-sessions; simulate records it in the manifest."""
    import inspect
    from mole.generator import run as run_mod
    import importlib.util
    spec = importlib.util.spec_from_file_location("sim_runner", REPO / "scripts" / "sim_runner.py")
    src = (REPO / "scripts" / "sim_runner.py").read_text(encoding="utf-8")
    assert "--redundant-role-sessions" in src and "redundant_role_sessions=args.redundant_role_sessions" in src
    assert "redundant_role_sessions" in inspect.signature(run_mod.simulate).parameters
    assert 'manifest["redundant_role_sessions"]' in inspect.getsource(run_mod.simulate)


def test_launch_line_expected_plan_counts_scenario_sessions_under_redundancy(tmp_path):
    import sys
    for _p in (REPO, REPO / "scripts"):
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
    import launch_line as ll
    roster = ["ben.c11", "elena.r13", "maya.h96", "noah.g102", "omar.s34", "raj.k48", "zoe.c36", "tom.k51"]
    pdir = tmp_path / "personas"
    pdir.mkdir()
    for fn, acct, role in (("f4_shared_doc_R_1_editor_1.yaml", "ben.c11", "editor_1"),
                           ("f4_shared_doc_R_1_editor_2.yaml", "elena.r13", "editor_2")):
        (pdir / fn).write_text(yaml.safe_dump({"employee_id": acct, "threat": "f4_shared_doc",
                                                "stealth_level": "s0", "role_label": role,
                                                "persona_override": "routine work"}))
    doc = {"schema": "coalitions-v2", "threat": "f4_shared_doc", "variant": "k2",
           "generation": {"personas": ",".join(roster), "days": 3, "sessions_per_day": 2, "mode": "rules",
                          "seed": 20265, "out": "data/corpus/spike/x_rules.jsonl",
                          "personas_dir": str(pdir), "model": "moonshotai/kimi-k2.6",
                          "extra_flags": ["--multi-day", "--objective-carrier", "benign", "--redundant-role-sessions"]},
           "branches": {"R": {"instances": [
               {"id": "R1", "variant": "k2", "document": {"service": "owncloud", "path": "/shared/x.md"},
                "roles": {"editor_1": "ben.c11", "editor_2": "elena.r13"},
                "campaign_window": {"first_day": 1, "last_day": 2}}]}}}
    f = tmp_path / "a.yaml"
    f.write_text(yaml.safe_dump(doc))
    plan = ll.build_expected_plan(f, "R")
    assert plan["redundant_role_sessions"] is True
    cmd = ll.build_command(f, "R")
    assert "--redundant-role-sessions" in cmd
    pp = ll.presence_plan(plan, "2026-04-06")
    assert pp["redundant_role_sessions"] is True
    for r in pp["roles"]:
        assert set(r["scenario_sessions_per_acting_day"]) == set(r["acting_days"])
        assert all(1 <= v <= 2 for v in r["scenario_sessions_per_acting_day"].values())
    lo, hi = pp["scenario_sessions_expected"]
    assert 2 <= lo <= hi <= 4
    # without the flag, exactly one per role-day
    doc["generation"]["extra_flags"] = ["--multi-day"]
    f.write_text(yaml.safe_dump(doc))
    plan0 = ll.build_expected_plan(f, "R")
    pp0 = ll.presence_plan(plan0, "2026-04-06")
    assert pp0["scenario_sessions_expected"] == [2, 2] and not pp0["redundant_role_sessions"]
