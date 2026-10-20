"""Deterministic tests for the multi-day campaign scheduler (no network)."""
from __future__ import annotations

import random

import pytest

from mole.generator.campaign import PHASE_DECOMP, build_campaign, build_single_day

F4_DATES = [f"2026-04-{d:02d}" for d in range(6, 11)]   # 5 working-day strings
F4_ROLES = ["editor_1", "editor_2", "editor_3"]

DATES = [f"2026-04-{d:02d}" for d in range(6, 6 + 20)]   # 20 working-day-ish strings


def _idx(dates):
    return {d: i for i, d in enumerate(dates)}


def test_stage_before_trigger_and_in_window():
    ph = build_campaign("10_safety_sabotage", DATES, random.Random(0))
    assert ph, "expected a non-empty campaign for a decomposable threat"
    idx = _idx(DATES)
    assert all(p["date"] in idx for p in ph)                 # every phase date in window
    stages = [idx[p["date"]] for p in ph if p["phase"] == "stage"]
    triggers = [idx[p["date"]] for p in ph if p["phase"] == "trigger"]
    assert len(stages) == len(triggers) >= 1
    # each stage has a trigger strictly after it
    for s in stages:
        assert any(t > s for t in triggers)


def test_gap_within_range():
    dates = [f"2026-05-{d:02d}" for d in range(1, 29)]       # 28 days, plenty of room
    ph = build_campaign("06_weight_exfil", dates, random.Random(3))
    idx = _idx(dates)
    stages = sorted(idx[p["date"]] for p in ph if p["phase"] == "stage")
    triggers = sorted(idx[p["date"]] for p in ph if p["phase"] == "trigger")
    for s in stages:
        assert any(2 <= (t - s) <= 6 for t in triggers), f"no trigger 2..6 days after stage {s}"


def test_reproducible_for_same_seed_and_varies_across_seeds():
    a = build_campaign("01_ip_theft", DATES, random.Random(42))
    b = build_campaign("01_ip_theft", DATES, random.Random(42))
    assert a == b                                            # deterministic
    c = build_campaign("01_ip_theft", DATES, random.Random(7))
    assert a != c                                            # different seed -> different schedule


def test_non_decomposable_threats_are_single_day():
    # Non-decomposable threats now yield ONE single agent-day (K=1), not [] —
    # so multi-day mode never falls back to the per-session coin-flip.
    for scn in ("c1_release_bypass", "c2_split_exfil", "totally_unknown"):
        ph = build_campaign(scn, DATES, random.Random(0))
        assert len(ph) == 1, scn
        assert ph[0]["phase"] == "single" and ph[0]["directive"] is None, scn


def test_04_and_05_now_decompose():
    # 04/05 were single-act; they now have stage->trigger decompositions.
    for scn in ("04_fraud", "05_sabotage"):
        assert [p["phase"] for p in build_campaign(scn, DATES, random.Random(0))] == ["stage", "trigger"]


def test_short_window_degrades_gracefully():
    # A window too short for a stage->trigger gap -> one single agent-day (K=1).
    one = build_campaign("01_ip_theft", DATES[:1], random.Random(0))
    assert len(one) == 1 and one[0]["phase"] == "single"
    # An empty window -> empty schedule.
    assert build_campaign("01_ip_theft", [], random.Random(0)) == []


def test_directives_match_phase_decomp():
    ph = build_campaign("08_data_poisoning", DATES, random.Random(1))
    assert ph
    for p in ph:
        assert p["directive"] == PHASE_DECOMP["08_data_poisoning"][p["phase"]]
        assert p["directive"]                                # non-empty


def test_all_decomposable_threats_have_both_directives():
    for scn, d in PHASE_DECOMP.items():
        assert d.get("stage") and d.get("trigger"), scn


# --- deterministic single-day mode (build_single_day) ---

def test_single_day_k_distinct_self_contained_days():
    days = build_single_day(DATES, random.Random(0), k=4)
    assert len(days) == 4
    assert len({d["date"] for d in days}) == 4                 # distinct days
    assert all(d["date"] in DATES for d in days)               # in window
    assert all(d["phase"] == "single" and d["directive"] for d in days)   # completion directive


def test_single_day_reproducible_and_varies_by_seed():
    a = build_single_day(DATES, random.Random(42), k=3)
    b = build_single_day(DATES, random.Random(42), k=3)
    assert a == b                                              # deterministic per seed
    c = build_single_day(DATES, random.Random(7), k=3)
    assert a != c                                              # per-insider jitter -> different days


def test_single_day_k_capped_to_window_and_empty():
    capped = build_single_day(DATES[:2], random.Random(0), k=5)
    assert len(capped) == 2                                    # k capped to window length
    assert build_single_day([], random.Random(0), k=4) == []  # empty window -> []


# --- family F4: three-role shared-document poisoning (coalitions-v2) ---

def _f4_day(role, seed, acts_on_day=None, account=None, instance_id=None, window=(1, 5)):
    ph = build_campaign("f4_shared_doc", F4_DATES, random.Random(seed), role=role,
                        window=window, roles=F4_ROLES, acts_on_day=acts_on_day,
                        account=account, instance_id=instance_id)
    assert len(ph) == 1 and ph[0]["phase"] == "act" and ph[0]["directive"] is None
    return F4_DATES.index(ph[0]["date"])


def test_f4_three_roles_strictly_ordered_and_in_window_over_200_seeds():
    # Rung-2 requirement: over 200 seeds the three editor days are strictly ordered
    # (editor_1 < editor_2 < editor_3) and inside the window. The rank slices of
    # _role_day_range do not overlap, so ordering holds for every seed.
    for seed in range(200):
        days = [_f4_day(role, seed) for role in F4_ROLES]
        assert days[0] < days[1] < days[2], (seed, days)
        assert all(0 <= d < len(F4_DATES) for d in days), (seed, days)


def test_f4_acts_on_day_keeps_drawn_day_when_account_acts():
    # Happy path: when the account acts every day, acts_on_day leaves the draw unchanged
    # (byte-identical to no predicate).
    for seed in range(50):
        plain = _f4_day("editor_2", seed)
        checked = _f4_day("editor_2", seed, acts_on_day=lambda a, d: True,
                          account="x", instance_id="R1")
        assert plain == checked


def test_f4_acts_on_day_redraws_within_slice():
    # editor_1's rank slice is day indices {0, 1}. With day 0 never an acting day, every
    # seed must re-draw onto day 1 (still inside the slice -> ordering preserved).
    acting = set(F4_DATES[1:])
    for seed in range(50):
        d = _f4_day("editor_1", seed, acts_on_day=lambda a, day: day in acting,
                    account="x", instance_id="R1")
        assert d == 1


def test_f4_acts_on_day_never_crosses_slices_fails_instead():
    # No acting day in editor_1's slice {0,1}, though day index 3 acts: rank order is
    # binding, so the planner must NOT borrow editor_2's day; it fails at planning time
    # naming the instance and the role.
    acting = {F4_DATES[3]}
    with pytest.raises(ValueError, match=r"'R1' role 'editor_1'"):
        _f4_day("editor_1", 0, acts_on_day=lambda a, day: day in acting,
                account="x", instance_id="R1")


def test_f4_acts_on_day_fails_loudly_naming_instance():
    with pytest.raises(ValueError, match="R7"):
        _f4_day("editor_1", 0, acts_on_day=lambda a, day: False,
                account="x", instance_id="R7")
