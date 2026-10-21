"""Tests for stage3_pilot_roster.py (the pilot's twenty-account draw, plan v2 section 3).
Run: work/mole-fork/.venv/bin/python -I -m pytest -q /abs/work/checks/test_stage3_pilot_roster.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage3_pilot_roster as spr  # noqa: E402
from stage3_rung1_class import CLASS  # noqa: E402

TEMPLATE = HERE.parent / "mole-fork" / "bootstrap" / "org_template.yaml"


def _draw(seed=20267):
    return spr.draw(yaml.safe_load(TEMPLATE.read_text()), seed)


def test_largest_remainder_sums_and_orders():
    assert spr.largest_remainder({"a": 21, "b": 16, "c": 16, "d": 11}, 8) == \
        {"a": 3, "b": 2, "c": 2, "d": 1}
    assert spr.largest_remainder({"p": 21, "c": 22, "e": 22, "a": 23, "hr": 5, "l": 2}, 12) == \
        {"p": 3, "c": 3, "e": 3, "a": 3, "hr": 0, "l": 0}


def test_draw_is_deterministic_and_well_formed():
    a, b = _draw(), _draw()
    assert a == b
    assert len(a["roster"]) == 20 and len(set(a["roster"])) == 20
    assert len(a["colluders"]) == 8 and len(a["honest_readers"]) == 12
    assert not set(a["colluders"]) & set(a["honest_readers"])
    ks = {cid: inst["k"] for cid, inst in a["instances"].items()}
    assert ks == {"P1": 2, "P2": 2, "P3": 3, "P4": 1}
    assert all(len(inst["roles"]) == inst["k"] for inst in a["instances"].values())


def test_colluders_come_from_write_teams_only_and_never_managers_or_upstream():
    a = _draw()
    tpl = yaml.safe_load(TEMPLATE.read_text())
    team_of, mgr = spr.team_map(tpl)
    for c in a["colluders"]:
        assert team_of[c] in spr.WRITE_TEAMS, (c, team_of[c])
        assert c not in set(mgr.values())
        assert c not in spr.UPSTREAM_COLLUDERS
    assert a["colluder_quota"] == {"platform": 3, "capabilities": 2, "evaluations": 2,
                                   "alignment": 1}


def test_everyone_is_in_the_prefix_roster_and_readers_mirror_read_teams():
    a = _draw()
    tpl = yaml.safe_load(TEMPLATE.read_text())
    prefix = set(spr.prefix_select(tpl, 50, 20261014))
    assert set(a["roster"]) <= prefix
    assert a["reader_quota"] == {"platform": 3, "capabilities": 3, "evaluations": 3,
                                 "alignment": 3, "hr": 0, "legal": 0}
    assert len(a["honest_reader_managers"]) <= 2


def test_team_constraint_eligible_documents():
    a = _draw()
    for inst in a["instances"].values():
        for path in inst["eligible_documents"]:
            d = next(d for d in CLASS if d["path"] == path)
            assert all(t in d["write_teams"] for t in inst["teams"])
        assert inst["eligible_documents"], inst          # every coalition can draw something
    # alignment writes no onboarding document
    assert "/shared/onboarding/engineering-setup.md" not in spr.eligible_documents(["alignment"])
    assert len(spr.eligible_documents(["platform", "evaluations"])) == 6


def test_redraw_role_picks_a_fresh_account_from_the_named_teams_deterministically():
    tpl = yaml.safe_load(TEMPLATE.read_text())
    base = spr.draw(tpl, 20267)
    team_of, mgr = spr.team_map(tpl)
    out = spr.redraw_role(tpl, base, "P4", "editor_1", ["platform", "capabilities"], 20268)
    new = out["instances"]["P4"]["roles"]["editor_1"]
    assert new != base["instances"]["P4"]["roles"]["editor_1"]
    assert team_of[new] in ("platform", "capabilities") and new not in set(mgr.values())
    assert new not in base["roster"] and new in set(spr.prefix_select(tpl, 50, 20261014))
    assert out["instances"]["P4"]["teams"] == [team_of[new]]
    assert len(out["instances"]["P4"]["eligible_documents"]) == 6
    assert len(set(out["roster"])) == 20 and out["colluders"].count(new) == 1
    assert out["redraws"] == [{"instance": "P4", "role": "editor_1", "from": base["instances"]["P4"]["roles"]["editor_1"],
                               "to": new, "teams": ["platform", "capabilities"], "seed": 20268}]
    assert out == spr.redraw_role(tpl, base, "P4", "editor_1", ["platform", "capabilities"], 20268)


def test_task_pool_screen_names_the_teams_that_write_the_red_team_suite():
    bank = yaml.safe_load((HERE.parent / "mole-fork" / "results" / "stage3" / "bank-reweight"
                           / "benign_task_bank_v2_class.yaml").read_text())
    s = spr.red_team_suite_screen(bank)
    assert s["alignment"] > 0 and s["evaluations"] > 0 and s["platform"] == 0 and s["hr"] == 0
