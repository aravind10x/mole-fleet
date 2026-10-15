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


# ── runner: coalitions-only semantics (brief 05b) ───────────────────
#
# With --coalitions the instance file is the ONLY source of scenario accounts: every
# cell of insider_assignment.yaml (solo, collusion, shadow) is skipped, not just C4.
# The committed draw (bootstrap/coalitions_stage2b.yaml) contains accounts that hold a
# cell for another threat (paul.k53 is C3 config_editor; deepa.t9 is a solo insider);
# before 05b the runner planned those cells too and refused every branch on the clash.

import sys

REPO = Path(__file__).resolve().parents[1]
DRAW = REPO / "bootstrap" / "coalitions_stage2b.yaml"
ASSIGNMENT_ACCOUNTS_IN_PREFIX = {
    "alice.kim", "ben.c11", "dan.r", "deepa.a7", "deepa.t9", "elena.r13", "frank.s",
    "julian.x", "kara.p", "nina.l27", "paul.k53", "wei.n2",
}


def _import_sim_runner():
    for p in (REPO, REPO / "scripts"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import sim_runner
    return sim_runner


def _launch_kwargs(monkeypatch, tmp_path, branch_id: str) -> tuple[dict, str]:
    """Run sim_runner.main with the real launch flags of coalitions_stage2b.yaml
    (generation.flags, agentic mode, the 50 prefix personas) against a fake simulate;
    return the kwargs simulate received and the runner's stdout."""
    sim_runner = _import_sim_runner()
    gen = yaml.safe_load(DRAW.read_text(encoding="utf-8"))["generation"]
    seen: dict = {}

    async def _fake_simulate(**kw):
        seen.update(kw)

        class _C:
            events: list = []
        return _C()

    monkeypatch.setattr(sim_runner, "simulate", _fake_simulate)
    import io
    import contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = sim_runner.main([
            "--smoke", "--personas", gen["personas"], "--no-docker", "--multi-day",
            "--days", str(gen["days"]), "--sessions-per-day", str(gen["sessions_per_day"]),
            "--concurrency", str(gen["concurrency"]),
            "--branch-from", "data/corpus/spike/prefix_v1.jsonl",
            "--coalitions", str(DRAW), "--branch-id", branch_id,
            "--seed", str(gen["seeds"][branch_id]),
            "--out", str(tmp_path / f"branch_{branch_id}.jsonl")])
    assert rc == 0
    return seen, buf.getvalue()


def _branch_accounts(branch_id: str) -> dict[str, str]:
    """{account -> role} over the committed draw's instances of one branch."""
    doc = yaml.safe_load(DRAW.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for inst in doc["branches"][branch_id]["instances"]:
        for role, acct in inst["roles"].items():
            out[acct] = role
    return out


@pytest.mark.parametrize("branch_id, clashing", [
    ("A", {"paul.k53": "requester"}),
    ("B", {"deepa.t9": "approver"}),
    ("C", {"deepa.a7": "requester", "deepa.t9": "approver", "wei.n2": "approver"}),
])
def test_runner_coalitions_only_plans_coalition_roles_and_nothing_else(monkeypatch, tmp_path,
                                                                       branch_id, clashing):
    kw, out = _launch_kwargs(monkeypatch, tmp_path, branch_id)
    expected = _branch_accounts(branch_id)
    assert len(expected) == 10
    # an account that holds a cell for another threat is planned only as its coalition role
    for acct, role in clashing.items():
        assert expected[acct] == role
        assert kw["insider_threat_map"][acct] == "c4_access_split"
        assert kw["insider_role_map"][acct] == role
    # no other prefix account is planned at all
    assert set(kw["insider_threat_map"]) == set(expected)
    assert set(kw["insider_role_map"]) == set(expected)
    assert set(kw["insider_level_map"]) == set(expected)
    assert set(kw["insider_persona_map"]) <= set(expected)       # no persona files yet
    assert not (ASSIGNMENT_ACCOUNTS_IN_PREFIX - set(expected)) & set(kw["insider_threat_map"])
    assert kw["coalition_meta"]["assignment_cells_skipped"] == "all"
    assert kw["attack_session_rate"] == 0.20                      # launch flags: default rate
    assert "insider_assignment.yaml: all cells ignored" in out
    assert out.count("warn: persona file missing") == 10


def test_runner_no_insiders_with_coalitions_unchanged(monkeypatch, tmp_path):
    """--no-insiders still makes every account honest, coalition accounts included."""
    sim_runner = _import_sim_runner()
    seen: dict = {}

    async def _fake_simulate(**kw):
        seen.update(kw)

        class _C:
            events: list = []
        return _C()

    monkeypatch.setattr(sim_runner, "simulate", _fake_simulate)
    rc = sim_runner.main(["--smoke", "--no-docker", "--no-insiders", "--multi-day", "--days", "5",
                          "--coalitions", str(DRAW), "--branch-id", "A",
                          "--out", str(tmp_path / "x.jsonl")])
    assert rc == 0
    assert seen["attack_session_rate"] == 0.0
    assert set(seen["insider_threat_map"]) == set(_branch_accounts("A"))


def test_runner_without_coalitions_still_loads_every_assignment_cell(monkeypatch, tmp_path):
    """The coalitions-only flag is per invocation: a plain launch keeps the assignment."""
    sim_runner = _import_sim_runner()
    seen: dict = {}

    async def _fake_simulate(**kw):
        seen.update(kw)

        class _C:
            events: list = []
        return _C()

    monkeypatch.setattr(sim_runner, "simulate", _fake_simulate)
    _launch_kwargs(monkeypatch, tmp_path, "A")                     # sets the flag ...
    monkeypatch.setattr(sim_runner, "simulate", _fake_simulate)
    rc = sim_runner.main(["--smoke", "--no-docker", "--mode", "rules", "--days", "1",
                          "--out", str(tmp_path / "plain.jsonl")])
    assert rc == 0                                                  # ... and a plain run clears it
    assert "paul.k53" in seen["insider_threat_map"]
    assert seen["insider_threat_map"]["paul.k53"] == "c3_release_sabotage"
    assert seen["coalition_meta"] is None


def test_flatten_assignment_returns_nothing_in_coalitions_only_mode(monkeypatch):
    sim_runner = _import_sim_runner()
    assignment = {"solo": {"01_ip_theft": {"s1": "a"}},
                  "collusion": {"c3_release_sabotage": {"s0": {"approver": "z"}},
                                "c4_access_split": {"s0": {"requester": "x"}}},
                  "shadow": {"05_sabotage": {"s0": "s"}}}
    monkeypatch.setattr(sim_runner, "_COALITIONS_ONLY", False)
    assert len(sim_runner._flatten_assignment(assignment)) == 4
    monkeypatch.setattr(sim_runner, "_COALITIONS_ONLY", True)
    assert sim_runner._flatten_assignment(assignment) == []


def test_manifest_records_assignment_skip_in_rules_mode(tmp_path):
    """End to end (rules mode, dryrun, no LLM): the run starts and the manifest's
    coalitions block records assignment_cells_skipped: all."""
    from mole.generator import resume_state
    sim_runner = _import_sim_runner()
    out = tmp_path / "p3b.jsonl"
    rc = sim_runner.main(["--smoke", "--no-docker", "--mode", "rules", "--multi-day",
                          "--days", "2", "--sessions-per-day", "1",
                          "--personas", "deepa.a1,aisha.n16,marco.s5", "--seed", "1",
                          "--coalitions", str(REPO / "tests" / "fixtures" / "coalitions_smoke.yaml"),
                          "--branch-id", "A", "--out", str(out)])
    assert rc == 0
    manifest = resume_state.load(out)
    block = manifest["coalitions"]
    assert block["assignment_cells_skipped"] == "all"
    assert block["branch_id"] == "A" and len(block["instances"]) == 1
    assert [r["account"] for r in block["instances"][0]["roles"]] == ["deepa.a1", "tom.k51"]


def test_manifest_entry_carries_assignment_skip(tmp_path):
    p = _write(tmp_path, _doc())
    pdir = tmp_path / "personas"
    pdir.mkdir()
    inst = load_coalitions(p, "A")
    maps = coalition_maps(inst, pdir)
    rec = manifest_entry(p, "A", inst, maps, None, assignment_cells_skipped="all")
    assert rec["assignment_cells_skipped"] == "all"
    assert "assignment_cells_skipped" not in manifest_entry(p, "A", inst, maps, None)
