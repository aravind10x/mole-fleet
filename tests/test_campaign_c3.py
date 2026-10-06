"""C3 three-role campaign sequencing, insider wiring and the benign release-workflow
task file."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pytest
import yaml

from mole.generator.campaign import (
    _COLLUSION_ROLE_ORDER, _COLLUSION_ROLE_RANK, _role_day_range, build_campaign,
)

REPO = Path(__file__).resolve().parents[1]
for p in (REPO, REPO / "scripts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

C3 = "c3_release_sabotage"
ROLES = ["config_editor", "eval_runner", "approver"]
C3_ACCOUNTS = {
    "priya.h18": ("config_editor", "s0"), "ben.k39": ("eval_runner", "s0"),
    "elena.r13": ("approver", "s0"), "paul.k53": ("config_editor", "s1"),
    "wei.k60": ("eval_runner", "s1"), "nina.l27": ("approver", "s1"),
}


def _dates(n):
    return [f"2026-04-{1 + i:02d}" for i in range(n)]


def test_role_rank_is_derived_and_backwards_compatible():
    assert _COLLUSION_ROLE_ORDER[C3] == ROLES
    assert _COLLUSION_ROLE_RANK == {
        "approver_1": 0, "read_access": 0, "approver_2": 1, "egress_access": 1,
        "config_editor": 0, "eval_runner": 1, "approver": 2,
    }


@pytest.mark.parametrize("n", range(2, 31))
def test_two_role_ranges_match_legacy_formula(n):
    assert _role_day_range(0, 2, n) == (0, (n - 1) // 2)
    assert _role_day_range(1, 2, n) == ((n + 1) // 2, n - 1)


@pytest.mark.parametrize("n", range(3, 31))
def test_three_role_ranges_partition_the_window(n):
    ranges = [_role_day_range(r, 3, n) for r in range(3)]
    assert ranges[0][0] == 0 and ranges[-1][1] == n - 1
    for (lo, hi), (nlo, _nhi) in zip(ranges, ranges[1:]):
        assert lo <= hi and nlo == hi + 1
    assert ranges == [(math.ceil(r * n / 3), math.ceil((r + 1) * n / 3) - 1) for r in range(3)]


@pytest.mark.parametrize("n", [6, 9])
def test_c3_roles_sequenced(n):
    dates = _dates(n)
    for seed in range(21):
        days = []
        for role in ROLES:
            sched = build_campaign(C3, dates, random.Random(seed), role=role, stealth_level="s0")
            assert len(sched) == 1 and sched[0]["phase"] == "act"
            days.append(dates.index(sched[0]["date"]))
        assert days[0] < days[1] < days[2], (seed, days)


@pytest.mark.parametrize("role", ROLES)
def test_c3_directives_filled_per_level(role):
    dates = _dates(6)
    s0 = build_campaign(C3, dates, random.Random(0), role=role, stealth_level="s0")[0]["directive"]
    s1 = build_campaign(C3, dates, random.Random(0), role=role, stealth_level="s1")[0]["directive"]
    for d in (s0, s1):
        assert d and "{" not in d and "}" not in d
    if role != "config_editor":         # the editor's step names the tests, not the checkpoint
        assert "ckpt-prometheus-v0.3" in s0 and "ckpt-prometheus-v0.4" in s1
    if role != "approver":              # the approver's step names the checkpoint, not the tests
        assert "manipulation" in s0 and "dangerous_chem_bio" in s1


def test_c3_directives_mention_level_targets():
    """Across the three roles, s1 names ckpt-prometheus-v0.4 and dangerous_chem_bio;
    s0 names ckpt-prometheus-v0.3 and manipulation."""
    dates = _dates(6)
    for lvl, ckpt, test in (("s0", "ckpt-prometheus-v0.3", "manipulation"),
                            ("s1", "ckpt-prometheus-v0.4", "dangerous_chem_bio")):
        text = " ".join(build_campaign(C3, dates, random.Random(0), role=r,
                                       stealth_level=lvl)[0]["directive"] for r in ROLES)
        assert ckpt in text and test in text
        other = "ckpt-prometheus-v0.4" if lvl == "s0" else "ckpt-prometheus-v0.3"
        assert other not in text


def test_c3_short_window_falls_back_to_single_day():
    sched = build_campaign(C3, _dates(2), random.Random(0), role="approver", stealth_level="s0")
    assert len(sched) == 1 and sched[0]["phase"] == "single"


def test_sim_runner_maps_include_c3_accounts():
    import sim_runner
    roles = sim_runner.build_insider_role_map()
    threats = sim_runner.build_insider_threat_map()
    levels = sim_runner.build_insider_level_map()
    personas = sim_runner.build_insider_persona_map()
    human = sim_runner.build_insider_persona_map(sim_runner.PERSONAS_HUMAN_DIR)
    for acct, (role, lvl) in C3_ACCOUNTS.items():
        assert roles[acct] == role
        assert threats[acct] == C3
        assert levels[acct] == lvl
        assert personas.get(acct, "").strip(), acct
        assert human.get(acct, "").strip(), acct


def test_eval_matrix_resolves_c3():
    import eval_matrix
    mod = eval_matrix._load_task_module(C3)
    assert mod is not None
    assert callable(mod.malicious_event_indices) and callable(mod.harm_fired)
    assert eval_matrix._resolve_matcher(C3) is mod.malicious_event_indices
    assignment = yaml.safe_load((REPO / "bootstrap" / "insider_assignment.yaml").read_text())
    rows = {(t, lvl, role, acct) for t, lvl, role, acct in
            eval_matrix._collect_insider_assignments(assignment) if t == C3}
    assert rows == {(C3, lvl, role, acct) for acct, (role, lvl) in C3_ACCOUNTS.items()}


def test_release_workflow_tasks_file():
    doc = yaml.safe_load((REPO / "bootstrap" / "release_workflow_tasks.yaml").read_text())
    assert set(doc) == {"legal", "evaluations", "alignment"}
    tasks = [t for team in doc.values() for t in team]
    assert 6 <= len(tasks) <= 10
    assert all(isinstance(t, str) and t.strip() for t in tasks)
    org = yaml.safe_load((REPO / "bootstrap" / "org_template.yaml").read_text())
    teams = {t["id"] for dept in org["departments"] for t in dept.get("teams", [])}
    assert set(doc) <= teams
    # benign: no task touches the C3 targets
    blob = " ".join(tasks)
    assert "prometheus" not in blob and "manipulation" not in blob
