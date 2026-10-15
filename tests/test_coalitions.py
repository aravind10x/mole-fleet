"""Coalition instances per threat (mole/generator/coalitions.py; Stage 2b planner).

Fixtures use prefix accounts and placeholder persona text only; no attack content."""
from __future__ import annotations

import random
from pathlib import Path

import pytest
import yaml

from mole.generator import campaign as cp
from mole.generator.coalitions import (
    Instance, check_windows, coalition_maps, load_coalitions, manifest_entry, persona_file_name,
)
from mole.generator.run import _weekday_dates, campaign_schedule_for

BRANCH_DATES = _weekday_dates(__import__("datetime").date.fromisoformat("2026-04-08"), 5)
assert BRANCH_DATES == ["2026-04-08", "2026-04-09", "2026-04-10", "2026-04-13", "2026-04-14"]


def _doc(**over):
    doc = {
        "schema": "coalitions-v1", "stage": "stage2b", "threat": "c4_access_split",
        "variant": "k2_req_app", "draw": {"seed_sha256": "deadbeef", "procedure": "fixture"},
        "reserved_honest_accounts": ["nina.t73"],
        "branches": {
            "A": {"corpus": "branch_A", "instances": [
                {"id": "A1", "stealth_level": "s0", "target_group": "model-approval",
                 "roles": {"requester": "deepa.a1", "approver": "tom.k51"},
                 "campaign_window": {"first_day": 1, "last_day": 3}},
                {"id": "A2", "stealth_level": "s1", "target_group": "infra-admins",
                 "roles": {"requester": "zoe.c36", "approver": "liam.w65"},
                 "campaign_window": {"first_day": 1, "last_day": 3}},
            ]},
            "B": {"corpus": "branch_B", "instances": [
                {"id": "B1", "stealth_level": "s0", "target_group": "model-approval",
                 "roles": {"requester": "deepa.a1", "approver": "liam.w65"},
                 "campaign_window": {"first_day": 2, "last_day": 4}},
            ]},
        },
    }
    doc.update(over)
    return doc


def _write(tmp_path: Path, doc: dict, name="coalitions.yaml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return p


def _persona(dirpath: Path, account: str, iid: str, role: str, level="s0", **over) -> Path:
    doc = {"employee_id": account, "threat": "c4_access_split", "stealth_level": level,
           "role_label": role, "persona_override": "PLACEHOLDER persona text"}
    doc.update(over)
    p = dirpath / persona_file_name("c4_access_split", iid, role)
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return p


# ── loader ──────────────────────────────────────────────────────────

def test_persona_file_name():
    assert persona_file_name("c4_access_split", "A1", "requester") == "c4_access_split_A_1_requester.yaml"
    assert persona_file_name("c4_access_split", "C12", "approver") == "c4_access_split_C_12_approver.yaml"
    with pytest.raises(ValueError):
        persona_file_name("c4_access_split", "1A", "requester")


def test_load_branch(tmp_path):
    p = _write(tmp_path, _doc())
    inst = load_coalitions(p, "A")
    assert [i.id for i in inst] == ["A1", "A2"]
    a1 = inst[0]
    assert a1.roles == {"requester": "deepa.a1", "approver": "tom.k51"}
    assert a1.role_order == ["requester", "approver"]
    assert a1.window == (1, 3) and a1.target_account == "deepa.a1"
    assert a1.persona_files == {"requester": "c4_access_split_A_1_requester.yaml",
                                "approver": "c4_access_split_A_1_approver.yaml"}
    assert load_coalitions(p, "B")[0].window == (2, 4)


@pytest.mark.parametrize("bad, msg", [
    ({"schema": "x"}, "schema"),
    ({"variant": "k9"}, "unknown threat/variant"),
    ({"branches": {"A": {"instances": [{"id": "A1", "stealth_level": "s0", "target_group": "g",
                                        "roles": {"approver": "tom.k51", "requester": "deepa.a1"},
                                        "campaign_window": {"first_day": 1, "last_day": 3}}]}}},
     "roles"),
    ({"branches": {"A": {"instances": [
        {"id": "A1", "stealth_level": "s0", "target_group": "g",
         "roles": {"requester": "deepa.a1", "approver": "tom.k51"},
         "campaign_window": {"first_day": 1, "last_day": 3}},
        {"id": "A2", "stealth_level": "s0", "target_group": "g",
         "roles": {"requester": "tom.k51", "approver": "liam.w65"},
         "campaign_window": {"first_day": 1, "last_day": 3}}]}}}, "already used"),
    ({"branches": {"A": {"instances": [{"id": "A1", "stealth_level": "s0", "target_group": "g",
                                        "roles": {"requester": "nina.t73", "approver": "tom.k51"},
                                        "campaign_window": {"first_day": 1, "last_day": 3}}]}}},
     "reserved"),
    ({"branches": {"A": {"instances": [{"id": "A1", "stealth_level": "s0", "target_group": "g",
                                        "roles": {"requester": "deepa.a1", "approver": "tom.k51"},
                                        "campaign_window": {"first_day": 2, "last_day": 2}}]}}},
     "shorter"),
    ({"branches": {"A": {"instances": [{"id": "A1", "stealth_level": "s2", "target_group": "g",
                                        "roles": {"requester": "deepa.a1", "approver": "tom.k51"},
                                        "campaign_window": {"first_day": 1, "last_day": 3}}]}}},
     "stealth_level"),
])
def test_validation_errors(tmp_path, bad, msg):
    p = _write(tmp_path, _doc(**bad))
    with pytest.raises(ValueError, match=msg):
        load_coalitions(p, "A")


def test_unknown_branch(tmp_path):
    p = _write(tmp_path, _doc())
    with pytest.raises(ValueError, match="branch 'Z'"):
        load_coalitions(p, "Z")


def test_check_windows():
    inst = Instance("A1", "A", "c4_access_split", "k2_req_app", "s0", "g",
                    {"requester": "a", "approver": "b"}, (1, 6))
    with pytest.raises(ValueError, match="6"):
        check_windows([inst], 5)
    check_windows([inst], 6)


# ── maps ────────────────────────────────────────────────────────────

def test_maps_with_and_without_persona_files(tmp_path, capsys):
    p = _write(tmp_path, _doc())
    pdir = tmp_path / "personas"
    pdir.mkdir()
    _persona(pdir, "deepa.a1", "A1", "requester")
    # A1 approver and all of A2 missing on purpose
    inst = load_coalitions(p, "A")
    maps = coalition_maps(inst, pdir)
    out = capsys.readouterr().out
    assert "warn: persona file missing for tom.k51" in out
    assert "warn: persona file missing for zoe.c36" in out
    assert maps["persona_map"] == {"deepa.a1": "PLACEHOLDER persona text"}
    assert maps["threat_map"] == {a: "c4_access_split" for a in ("deepa.a1", "tom.k51", "zoe.c36", "liam.w65")}
    assert maps["role_map"]["tom.k51"] == "approver" and maps["role_map"]["deepa.a1"] == "requester"
    assert maps["level_map"]["zoe.c36"] == "s1"
    assert maps["window_map"]["liam.w65"] == (1, 3)
    assert maps["instance_map"] == {"deepa.a1": "A1", "tom.k51": "A1", "zoe.c36": "A2", "liam.w65": "A2"}
    assert maps["role_order_map"]["tom.k51"] == ["requester", "approver"]
    assert maps["found_map"] == {"deepa.a1": True, "tom.k51": False, "zoe.c36": False, "liam.w65": False}


def test_persona_file_mismatch_is_an_error(tmp_path):
    p = _write(tmp_path, _doc())
    pdir = tmp_path / "personas"
    pdir.mkdir()
    _persona(pdir, "someone.else", "A1", "requester")
    with pytest.raises(ValueError, match="employee_id"):
        coalition_maps(load_coalitions(p, "A"), pdir)
    _persona(pdir, "deepa.a1", "A1", "requester", level="s1")
    with pytest.raises(ValueError, match="stealth_level"):
        coalition_maps(load_coalitions(p, "A"), pdir)


# ── planner ─────────────────────────────────────────────────────────

def test_role_order_registered_and_c3_unchanged():
    assert cp._COLLUSION_ROLE_ORDER["c4_access_split"] == ["requester", "approver", "group_admin"]
    assert "requester" not in cp._COLLUSION_ROLE_RANK          # flat view stays C1..C3
    assert cp._COLLUSION_ROLE_RANK["approver"] == 2             # C3's approver rank
    assert cp._role_slot("c3_release_sabotage", "approver") == (2, 3)
    assert cp._role_slot("c4_access_split", "approver") == (1, 3)
    assert "c4_access_split" not in cp.COLLUSION_DECOMP        # persona-only, no directive


def test_two_roles_three_day_window_on_five_day_branch():
    req_days, app_days = set(), set()
    for seed in range(200):
        r = cp.build_campaign("c4_access_split", BRANCH_DATES, random.Random(seed), role="requester",
                              stealth_level="s0", window=(1, 3), roles=["requester", "approver"])
        a = cp.build_campaign("c4_access_split", BRANCH_DATES, random.Random(seed + 1), role="approver",
                              stealth_level="s0", window=(1, 3), roles=["requester", "approver"])
        assert len(r) == 1 and len(a) == 1
        assert r[0]["phase"] == "act" and r[0]["directive"] is None
        req_days.add(BRANCH_DATES.index(r[0]["date"]) + 1)
        app_days.add(BRANCH_DATES.index(a[0]["date"]) + 1)
    assert req_days == {1, 2}
    assert app_days == {3}


def test_window_offsets_and_three_roles():
    for seed in range(50):
        r = cp.build_campaign("c4_access_split", BRANCH_DATES, random.Random(seed), role="requester",
                              window=(2, 4), roles=["requester", "approver"])[0]["date"]
        a = cp.build_campaign("c4_access_split", BRANCH_DATES, random.Random(seed), role="approver",
                              window=(2, 4), roles=["requester", "approver"])[0]["date"]
        assert BRANCH_DATES.index(r) + 1 in (2, 3) and BRANCH_DATES.index(a) + 1 == 4
        days = [BRANCH_DATES.index(cp.build_campaign(
            "c4_access_split", BRANCH_DATES, random.Random(seed), role=role, window=(1, 3),
            roles=["requester", "approver", "group_admin"])[0]["date"]) + 1
            for role in ("requester", "approver", "group_admin")]
        assert days == [1, 2, 3]


def test_window_validation_and_determinism():
    with pytest.raises(ValueError):
        cp.build_campaign("c4_access_split", BRANCH_DATES, random.Random(0), role="requester",
                          window=(0, 3), roles=["requester", "approver"])
    with pytest.raises(ValueError):
        cp.build_campaign("c4_access_split", BRANCH_DATES, random.Random(0), role="requester",
                          window=(4, 6), roles=["requester", "approver"])
    a = cp.build_campaign("c4_access_split", BRANCH_DATES, random.Random(7), role="requester",
                          window=(1, 3), roles=["requester", "approver"])
    b = cp.build_campaign("c4_access_split", BRANCH_DATES, random.Random(7), role="requester",
                          window=(1, 3), roles=["requester", "approver"])
    assert a == b


def test_existing_callers_unaffected_by_new_kwargs():
    dates = [f"2026-05-{d:02d}" for d in range(1, 11)]
    for seed in range(20):
        legacy = cp.build_campaign("c3_release_sabotage", dates, random.Random(seed), role="approver",
                                   stealth_level="s0")
        same = cp.build_campaign("c3_release_sabotage", dates, random.Random(seed), role="approver",
                                 stealth_level="s0", window=None, roles=None)
        assert legacy == same


def _maps():
    return {
        "persona_map": {"deepa.a1": "P", "tom.k51": "P"},
        "threat_map": {"deepa.a1": "c4_access_split", "tom.k51": "c4_access_split"},
        "role_map": {"deepa.a1": "requester", "tom.k51": "approver"},
        "level_map": {"deepa.a1": "s0", "tom.k51": "s0"},
        "window_map": {"deepa.a1": (1, 3), "tom.k51": (1, 3)},
        "role_order_map": {"deepa.a1": ["requester", "approver"], "tom.k51": ["requester", "approver"]},
    }


def test_campaign_schedule_for_coalition_accounts():
    m = _maps()
    for i, acct in enumerate(("deepa.a1", "tom.k51")):
        s = campaign_schedule_for(acct, i, planning="scripted", persona_map=m["persona_map"],
                                  threat_map=m["threat_map"], role_map=m["role_map"],
                                  level_map=m["level_map"], sim_dates=BRANCH_DATES, seed=2026,
                                  campaign_days=4, attack_session_rate=0.2,
                                  window_map=m["window_map"], role_order_map=m["role_order_map"])
        assert len(s) == 1 and s[0]["phase"] == "act" and s[0]["directive"] is None
        day = BRANCH_DATES.index(s[0]["date"]) + 1
        assert day in (1, 2) if acct == "deepa.a1" else day == 3
    # honest world: explicit empty schedule
    s = campaign_schedule_for("deepa.a1", 0, planning="scripted", persona_map=m["persona_map"],
                              threat_map=m["threat_map"], role_map=m["role_map"], level_map=m["level_map"],
                              sim_dates=BRANCH_DATES, seed=2026, campaign_days=4, attack_session_rate=0.0,
                              window_map=m["window_map"], role_order_map=m["role_order_map"])
    assert s == []
    # single-day planning never plans a collusion role
    s = campaign_schedule_for("deepa.a1", 0, planning="single", persona_map=m["persona_map"],
                              threat_map=m["threat_map"], role_map=m["role_map"], level_map=m["level_map"],
                              sim_dates=BRANCH_DATES, seed=2026, campaign_days=4, attack_session_rate=0.2,
                              window_map=m["window_map"], role_order_map=m["role_order_map"])
    assert s == []
    # an account without a persona is never planned
    assert campaign_schedule_for("zoe.c36", 0, planning="scripted", persona_map=m["persona_map"],
                                 threat_map=m["threat_map"], role_map=m["role_map"],
                                 level_map=m["level_map"], sim_dates=BRANCH_DATES, seed=2026,
                                 campaign_days=4, attack_session_rate=0.2) is None


# ── manifest ────────────────────────────────────────────────────────

def test_manifest_entry(tmp_path):
    p = _write(tmp_path, _doc())
    pdir = tmp_path / "personas"
    pdir.mkdir()
    _persona(pdir, "deepa.a1", "A1", "requester")
    inst = load_coalitions(p, "A")
    maps = coalition_maps(inst, pdir)
    rec = manifest_entry(p, "A", inst, maps, {"deepa.a1": [{"date": "2026-04-09", "phase": "act",
                                                            "directive": None}]})
    assert rec["branch_id"] == "A" and rec["variant"] == "k2_req_app"
    assert rec["draw"] == {"seed_sha256": "deadbeef", "procedure": "fixture"}
    assert len(rec["file_sha256"]) == 64
    a1 = rec["instances"][0]
    assert a1["id"] == "A1" and a1["target_account"] == "deepa.a1"
    assert a1["campaign_window"] == {"first_day": 1, "last_day": 3}
    req, app = a1["roles"]
    assert req == {"role": "requester", "account": "deepa.a1",
                   "persona_file": "c4_access_split_A_1_requester.yaml", "persona_found": True,
                   "planned_attack_dates": ["2026-04-09"]}
    assert app["persona_found"] is False and app["planned_attack_dates"] is None
    import json
    json.dumps(rec)   # JSON-serialisable for the manifest


# ── runner flags (argument plumbing only; no simulation) ────────────

def test_sim_runner_skips_instance_threats_when_coalitions_given():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "sim_runner_under_test", Path(__file__).resolve().parents[1] / "scripts" / "sim_runner.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assignment = {"collusion": {"c4_access_split": {"s0": {"requester": "x", "approver": "y"}},
                                "c3_release_sabotage": {"s0": {"approver": "z"}}}}
    assert ("c4_access_split", "s0", "requester", "x") in mod._flatten_assignment(assignment)
    mod._SKIP_THREATS.update(mod._INSTANCE_THREATS)
    try:
        flat = mod._flatten_assignment(assignment)
        assert all(t != "c4_access_split" for t, *_ in flat)
        assert ("c3_release_sabotage", "s0", "approver", "z") in flat
    finally:
        mod._SKIP_THREATS.clear()
