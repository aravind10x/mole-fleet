"""One planner for a coalition role's day (brief 07b F1.7; branch review 2026-10-20 "two
planners"). L15 rule 4: a planner that schedules an account on a day checks the account acts
that day. Before: rules mode re-drew a role's day inside its rank slice from the generated
corpus, while the agentic path kept the drawn day and FORCED a session, so the rehearsal
rehearsed a different schedule. Now both paths draw the day with `campaign.build_campaign`
against the same presence predicate (`mole.generator.presence`), re-draw inside the slice and
fail loudly when no slice day works; the agentic member no longer forces a session.

Fixtures: placeholder persona text only ("routine work"); no attack content."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from mole.generator import presence
from mole.generator.agentic_member import AgenticMember
from mole.generator.campaign import _role_day_range
from mole.generator.member import Member, NPCConfig
from mole.generator.persona_loader import load_personas
from mole.generator.run import _weekday_dates, campaign_schedule_for

REPO = Path(__file__).resolve().parents[1]
DATES = _weekday_dates(__import__("datetime").date.fromisoformat("2026-04-06"), 4)
CFG = NPCConfig(sessions_per_day=2, absent_probability=0.5, loaf_probability=0.05)
ROLES = ["editor_1", "editor_2"]


class _NoLLM:
    backend = model_id = "none"


def _member(persona, seed: int, cfg: NPCConfig = CFG, schedule=None) -> AgenticMember:
    return AgenticMember(persona, llm=_NoLLM(), rng_seed=seed, config=cfg,
                         persona_override="routine work only" if schedule else None,
                         campaign_schedule=schedule, planning_mode="scripted", sim_dates=DATES)


def _acting_days(m) -> set[str]:
    return {d for d in DATES if m.plan_day(d)}


def test_presence_is_per_day_so_one_days_slot_count_never_shifts_another_day():
    seed = 11
    a = [presence.day_presence(seed, d, CFG, 1) is None for d in DATES]      # 1 slot per day
    b = [presence.day_presence(seed, d, CFG, 8) is None for d in DATES]      # 8 slots per day
    assert a == b                                     # the absence draw per day is the same
    assert presence.day_presence(seed, DATES[0], CFG, 3) == presence.day_presence(seed, DATES[0], CFG, 3)
    assert any(presence.day_presence(s, DATES[0], CFG, 2) is None for s in range(40))    # absence happens


def test_member_classes_and_the_predicate_agree_on_acting_days():
    """The predicate the planner uses IS what both member classes do in plan_day: the agentic
    member acts on a day iff the predicate says so, and the rules member is present on every
    day the predicate says the agentic member acts (same per-day absence draw)."""
    persona = next(p for p in load_personas(include_holdouts=True) if p.id == "priya.h18")
    for seed in range(60):
        pred = {d for d in DATES if presence.acts_on_day(seed, d, CFG, CFG.sessions_per_day)}
        assert _acting_days(_member(persona, seed)) == pred, seed
        rules = Member(persona, config=CFG, rng_seed=seed)
        assert pred <= {d for d in DATES if rules.plan_day(d)}, seed


def test_agentic_planner_redraws_inside_the_slice_or_fails_loudly_and_the_member_acts():
    persona = next(p for p in load_personas(include_holdouts=True) if p.id == "priya.h18")
    maps = {"persona_map": {persona.id: "routine work only"},
            "threat_map": {persona.id: "f4_shared_doc"}, "role_map": {persona.id: "editor_1"},
            "level_map": {persona.id: "s0"}, "window_map": {persona.id: (1, 4)},
            "role_order_map": {persona.id: ROLES}, "instance_map": {persona.id: "T1"}}
    redrawn = failed = kept = 0
    lo, hi = _role_day_range(0, 2, 4)                 # editor_1's slice: day indices 0..1
    for seed in range(200):
        pred = presence.acts_predicate(seed, {persona.id: 0}, CFG, CFG.sessions_per_day)
        kw = dict(planning="scripted", persona_map=maps["persona_map"], threat_map=maps["threat_map"],
                  role_map=maps["role_map"], level_map=maps["level_map"], sim_dates=DATES, seed=seed,
                  campaign_days=4, attack_session_rate=0.2, window_map=maps["window_map"],
                  role_order_map=maps["role_order_map"], instance_map=maps["instance_map"])
        legacy = campaign_schedule_for(persona.id, 0, **kw)            # no predicate: the raw draw
        acting = _acting_days(_member(persona, seed))
        try:
            sched = campaign_schedule_for(persona.id, 0, acts_on_day=pred, **kw)
        except ValueError as exc:
            assert "T1" in str(exc) and "editor_1" in str(exc)
            assert not (acting & set(DATES[lo:hi + 1])), (seed, acting)     # no slice day acts
            failed += 1
            continue
        day = sched[0]["date"]
        assert day in DATES[lo:hi + 1] and day in acting, (seed, day, acting)
        if day == legacy[0]["date"]:
            kept += 1
        else:
            redrawn += 1
        # the member given this schedule plans at least one session that day WITHOUT forcing
        m = _member(persona, seed, schedule=sched)
        assert _acting_days(m) == acting                         # byte-identical to no schedule
        assert m.plan_day(day)
    assert kept and redrawn and failed, (kept, redrawn, failed)


# ── the brief's test: rules-mode manifest == agentic plan, same seed and roster ─────────────

ROSTER = ["deepa.a1", "aisha.n16", "marco.s5"]        # inprocess-bank accounts (dryrun rules)


def _assignment(tmp_path: Path) -> Path:
    doc = {"schema": "coalitions-v2", "threat": "f4_shared_doc", "variant": "k2",
           "branches": {"T": {"instances": [
               {"id": "T1", "document": {"service": "owncloud", "path": "/shared/x.md"},
                "roles": {"editor_1": "deepa.a1", "editor_2": "aisha.n16"},
                "campaign_window": {"first_day": 1, "last_day": 4}}]}}}
    p = tmp_path / "f4_one_planner.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    pdir = tmp_path / "personas"
    pdir.mkdir()
    for role, acct in (("editor_1", "deepa.a1"), ("editor_2", "aisha.n16")):
        (pdir / f"f4_shared_doc_T_1_{role}.yaml").write_text(yaml.safe_dump(
            {"employee_id": acct, "threat": "f4_shared_doc", "stealth_level": "s0",
             "role_label": role, "persona_override": "placeholder persona for rehearsal, routine work only"}),
            encoding="utf-8")
    return p


def _import_sim_runner():
    for p in (REPO, REPO / "scripts"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import sim_runner
    return sim_runner


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6])
def test_rules_manifest_equals_agentic_plan_for_the_same_seed_and_roster(monkeypatch, tmp_path, seed):
    from mole.generator import resume_state
    from mole.generator import run as run_mod
    sim_runner = _import_sim_runner()
    real = run_mod.simulate

    async def _with_absence(**kw):                    # the rules run at the test's absence rate
        kw["absent_probability"] = CFG.absent_probability
        return await real(**kw)

    monkeypatch.setattr(sim_runner, "simulate", _with_absence)
    p = _assignment(tmp_path)
    out = tmp_path / "f4_one_planner_rules.jsonl"
    argv = ["--smoke", "--no-docker", "--mode", "rules", "--multi-day", "--days", "4",
            "--sessions-per-day", str(CFG.sessions_per_day), "--personas", ",".join(ROSTER),
            "--seed", str(seed), "--coalitions", str(p), "--branch-id", "T",
            "--personas-dir", str(tmp_path / "personas"), "--out", str(out)]
    # the agentic path's plan for the same seed and roster (persona index = roster position)
    personas = {q.id: q for q in load_personas(include_holdouts=True)}
    cfg = NPCConfig(sessions_per_day=CFG.sessions_per_day, absent_probability=CFG.absent_probability)
    # the run's roster order is load_personas order filtered by --personas (run.simulate), and
    # member i gets rng_seed = seed + i; the test derives the index the same way
    index = {q.id: i for i, q in enumerate(q for q in load_personas(include_holdouts=True)
                                           if q.id in set(ROSTER))}
    maps = {"persona_map": {"deepa.a1": "x", "aisha.n16": "x"},
            "threat_map": {a: "f4_shared_doc" for a in ("deepa.a1", "aisha.n16")},
            "role_map": {"deepa.a1": "editor_1", "aisha.n16": "editor_2"},
            "level_map": {a: "s0" for a in ("deepa.a1", "aisha.n16")},
            "window_map": {a: (1, 4) for a in ("deepa.a1", "aisha.n16")},
            "role_order_map": {a: ROLES for a in ("deepa.a1", "aisha.n16")},
            "instance_map": {a: "T1" for a in ("deepa.a1", "aisha.n16")}}
    pred = presence.acts_predicate(seed, index, cfg, cfg.sessions_per_day)
    agentic: dict[str, str | None] = {}
    agentic_error = None
    try:
        for acct in ("deepa.a1", "aisha.n16"):
            s = campaign_schedule_for(acct, index[acct], planning="scripted", sim_dates=DATES,
                                      seed=seed, campaign_days=4, attack_session_rate=0.2,
                                      acts_on_day=pred, **maps)
            agentic[acct] = s[0]["date"]
    except ValueError as exc:
        agentic_error = str(exc)

    try:
        rc = sim_runner.main(argv)
    except ValueError as exc:                        # the loud failure: no slice day acts
        assert agentic_error is not None and "T1" in str(exc), (str(exc), agentic_error)
        return
    assert rc == 0 and agentic_error is None, agentic_error
    block = resume_state.load(out)["coalitions"]
    rules_days = {r["account"]: r["planned_role_day"] for r in block["instances"][0]["roles"]}
    assert rules_days == agentic, (rules_days, agentic)
    # and the agentic member of that seed really acts on the planned day (rule 4, end to end)
    for acct, day in agentic.items():
        m = _member(personas[acct], seed + index[acct], cfg)
        assert m.plan_day(day), (acct, day)
    assert DATES.index(agentic["deepa.a1"]) < DATES.index(agentic["aisha.n16"])
