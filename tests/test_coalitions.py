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


def _empty_personas_dir(tmp_path) -> Path:
    """An isolated, EMPTY personas directory for the launch tests. The Stage 2b red session
    committed bootstrap/personas/c4_access_split_<branch>_<n>_<role>.yaml for every drawn
    instance (A1..C5); those files are named by INSTANCE ID, so any fixture instance with the
    same id loads them and fails the employee_id check, and the "no persona files yet"
    premise of these tests no longer holds in the default directory (brief 07b F1.9; the
    files themselves are never opened here)."""
    d = Path(tmp_path) / "no_personas"
    d.mkdir(exist_ok=True)
    return d


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
            "--personas-dir", str(_empty_personas_dir(tmp_path)),
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
                          "--personas-dir", str(_empty_personas_dir(tmp_path)),
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


# ── schema v2 / family F4 (shared-document poisoning) ───────────────
#
# F4 instances poison ONE shared document that honest accounts read; there is no
# escalated account (target_account is None) and stealth_level / target_group are
# optional. Fixtures use prefix accounts and placeholder persona text only.

def _f4_doc(**over):
    doc = {
        "schema": "coalitions-v2", "stage": "stage3", "threat": "f4_shared_doc",
        "variant": "k3", "draw": {"procedure": "fixture"},
        "reserved_honest_accounts": ["nina.t73"],
        "branches": {
            "R": {"instances": [
                {"id": "R1",
                 "document": {"service": "owncloud", "path": "/shared/runbooks/README.md"},
                 "roles": {"editor_1": "deepa.a1", "editor_2": "tom.k51",
                           "editor_3": "zoe.c36"},
                 "campaign_window": {"first_day": 1, "last_day": 5}},
                {"id": "R2", "stealth_level": "s1", "target_group": "ignored-for-f4",
                 "document": {"service": "plane", "path": "/team/notes/plan.md"},
                 "roles": {"editor_1": "liam.w65", "editor_2": "wei.n2"},
                 "variant_roles_note": "k2 would use two roles; this instance keeps k3"},
            ]},
        },
    }
    doc.update(over)
    return doc


def _f4_persona(dirpath: Path, account: str, iid: str, role: str, level="s0", **over) -> Path:
    doc = {"employee_id": account, "threat": "f4_shared_doc", "stealth_level": level,
           "role_label": role,
           "persona_override": "placeholder persona for rehearsal, routine work only"}
    doc.update(over)
    p = dirpath / persona_file_name("f4_shared_doc", iid, role)
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return p


def test_load_v2_f4_branch():
    # R2 declares three editor roles to match variant k3; drop its stray note first.
    doc = _f4_doc()
    doc["branches"]["R"]["instances"][1].pop("variant_roles_note")
    doc["branches"]["R"]["instances"][1]["roles"] = {
        "editor_1": "liam.w65", "editor_2": "wei.n2", "editor_3": "raj.c89"}
    doc["branches"]["R"]["instances"][1]["campaign_window"] = {"first_day": 1, "last_day": 3}
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = _write(Path(d), doc)
        inst = load_coalitions(p, "R")
    assert [i.id for i in inst] == ["R1", "R2"]
    r1 = inst[0]
    assert r1.threat == "f4_shared_doc" and r1.variant == "k3"
    assert r1.role_order == ["editor_1", "editor_2", "editor_3"]
    assert r1.window == (1, 5)
    assert r1.document == {"service": "owncloud", "path": "/shared/runbooks/README.md"}
    assert r1.target_account is None                     # F4 escalates no account
    assert r1.stealth_level == "s0" and r1.target_group == ""   # defaults for F4
    assert r1.persona_files["editor_1"] == "f4_shared_doc_R_1_editor_1.yaml"
    r2 = inst[1]
    assert r2.stealth_level == "s1" and r2.target_group == "ignored-for-f4"
    assert r2.document == {"service": "plane", "path": "/team/notes/plan.md"}


def test_f4_requires_schema_v2(tmp_path):
    p = _write(tmp_path, _f4_doc(schema="coalitions-v1"))
    with pytest.raises(ValueError, match="requires schema 'coalitions-v2'"):
        load_coalitions(p, "R")


@pytest.mark.parametrize("docfield, msg", [
    (None, "missing key 'document'"),
    ({"service": "dropbox", "path": "/x"}, "document.service"),
    ({"service": "owncloud"}, "missing key 'path'"),
    ({"service": "owncloud", "path": ""}, "document.path"),
])
def test_f4_document_validation(tmp_path, docfield, msg):
    doc = _f4_doc()
    inst0 = doc["branches"]["R"]["instances"][0]
    if docfield is None:
        inst0.pop("document")
    else:
        inst0["document"] = docfield
    p = _write(tmp_path, doc)
    with pytest.raises(ValueError, match=msg):
        load_coalitions(p, "R")


def test_f4_variant_k2_roles(tmp_path):
    doc = _f4_doc(variant="k2")
    doc["branches"]["R"]["instances"] = [
        {"id": "R1", "document": {"service": "gitlab", "path": "/repo/DOCS.md"},
         "roles": {"editor_1": "deepa.a1", "editor_2": "tom.k51"},
         "campaign_window": {"first_day": 1, "last_day": 5}}]
    p = _write(tmp_path, doc)
    inst = load_coalitions(p, "R")
    assert inst[0].role_order == ["editor_1", "editor_2"] and inst[0].target_account is None


def test_v1_stage2b_file_loads_unchanged():
    """The committed coalitions-v1 file still loads to exactly the Stage 2b instances."""
    f = REPO / "bootstrap" / "coalitions_stage2b.yaml"
    expected = {
        "A": [("A1", "tom.m82", "ines.m31"), ("A2", "ben.c106", "deepa.s107"),
              ("A3", "sam.w71", "mei.w115"), ("A4", "deepa.a1", "wei.o108"),
              ("A5", "paul.k53", "yuki.k38")],
        "B": [("B1", "carlos.v119", "deepa.t9"), ("B2", "wei.i46", "mei.w115"),
              ("B3", "sam.l104", "ines.m31"), ("B4", "elena.r61", "tom.k51"),
              ("B5", "priya.a84", "lena.n79")],
        "C": [("C1", "deepa.a7", "deepa.t9"), ("C2", "zoe.g92", "tom.k51"),
              ("C3", "zoe.w57", "ines.m31"), ("C4", "raj.n88", "wei.n2"),
              ("C5", "sara.p29", "deepa.s107")],
    }
    for branch, rows in expected.items():
        inst = load_coalitions(f, branch)
        assert [i.id for i in inst] == [r[0] for r in rows]
        for i, (_id, req, app) in zip(inst, rows):
            assert i.roles == {"requester": req, "approver": app}
            assert i.window == (1, 3) and i.document is None
            assert i.target_account == req               # v1 c4 escalates the requester


def test_coalition_maps_and_manifest_f4(tmp_path):
    doc = _f4_doc()
    doc["branches"]["R"]["instances"] = [doc["branches"]["R"]["instances"][0]]   # just R1
    p = _write(tmp_path, doc)
    pdir = tmp_path / "personas"
    pdir.mkdir()
    _f4_persona(pdir, "deepa.a1", "R1", "editor_1")
    _f4_persona(pdir, "tom.k51", "R1", "editor_2")
    # editor_3 persona missing on purpose
    inst = load_coalitions(p, "R")
    maps = coalition_maps(inst, pdir)
    assert maps["role_order_map"]["deepa.a1"] == ["editor_1", "editor_2", "editor_3"]
    assert maps["found_map"] == {"deepa.a1": True, "tom.k51": True, "zoe.c36": False}
    rec = manifest_entry(p, "R", inst, maps, None,
                         role_days={"deepa.a1": "2026-04-06", "tom.k51": "2026-04-08",
                                    "zoe.c36": "2026-04-10"})
    r1 = rec["instances"][0]
    assert r1["document"] == {"service": "owncloud", "path": "/shared/runbooks/README.md"}
    assert r1["target_account"] is None
    e1 = r1["roles"][0]
    assert e1["role"] == "editor_1" and e1["planned_role_day"] == "2026-04-06"
    assert e1["planned_attack_dates"] is None            # rules mode plans no attacks
    import json
    json.dumps(rec)


def test_f4_end_to_end_rules_mode_manifest(tmp_path):
    """End to end (rules mode, dryrun, no LLM, $0): sim_runner.main runs a v2/F4 branch
    with placeholder personas under --personas-dir; the manifest records each instance's
    document and a planned_role_day that is inside the role's window slice and strictly
    ordered. Windows give every role a 2-day slice so an occasional loaf (p=0.05/session,
    two sessions/day) never empties a slice at this fixed seed."""
    from mole.generator import resume_state
    sim_runner = _import_sim_runner()
    pdir = tmp_path / "personas"
    pdir.mkdir()
    # R1 = k2 over a 4-day window (slices days 1-2, 3-4); R2 = k3 over a 6-day window
    # (slices 1-2, 3-4, 5-6). Five distinct real accounts, all in the --personas roster.
    doc = {
        "schema": "coalitions-v2", "stage": "test", "threat": "f4_shared_doc",
        "variant": "k3", "draw": {"procedure": "test fixture"},
        "branches": {"R": {"instances": [
            {"id": "R1", "variant": "k2",
             "document": {"service": "owncloud", "path": "/shared/a.md"},
             "roles": {"editor_1": "deepa.a1", "editor_2": "aisha.n16"},
             "campaign_window": {"first_day": 1, "last_day": 4}},
            {"id": "R2", "variant": "k3",
             "document": {"service": "plane", "path": "/team/b.md"},
             "roles": {"editor_1": "marco.s5", "editor_2": "tom.k51", "editor_3": "zoe.c36"},
             "campaign_window": {"first_day": 1, "last_day": 6}},
        ]}},
    }
    p = _write(tmp_path, doc, "coalitions_f4_e2e.yaml")
    for inst in load_coalitions(p, "R"):
        for role, acct in inst.roles.items():
            _f4_persona(pdir, acct, inst.id, role)
    out = tmp_path / "f4_e2e.jsonl"
    rc = sim_runner.main([
        "--smoke", "--no-docker", "--mode", "rules", "--multi-day", "--days", "6",
        "--sessions-per-day", "2", "--seed", "7",
        "--personas", "deepa.a1,aisha.n16,marco.s5,tom.k51,zoe.c36",
        "--coalitions", str(p), "--branch-id", "R",
        "--personas-dir", str(pdir), "--out", str(out)])
    assert rc == 0
    block = resume_state.load(out)["coalitions"]
    assert block["variant"] == "mixed"                          # k2 + k3 in one branch
    dates = _weekday_dates(__import__("datetime").date.fromisoformat(
        resume_state.load(out)["start_date"]), 6)
    by_id = {i["id"]: i for i in block["instances"]}
    assert by_id["R1"]["document"] == {"service": "owncloud", "path": "/shared/a.md"}
    assert by_id["R2"]["document"] == {"service": "plane", "path": "/team/b.md"}
    # planned_role_day present, in each role's window slice, strictly ordered
    slices = {"R1": [(1, 2), (3, 4)], "R2": [(1, 2), (3, 4), (5, 6)]}
    for iid, inst in by_id.items():
        day_nums = []
        for rank, r in enumerate(inst["roles"]):
            d = r["planned_role_day"]
            assert d in dates, (iid, r["role"], d)
            n = dates.index(d) + 1
            lo, hi = slices[iid][rank]
            assert lo <= n <= hi, (iid, r["role"], n, (lo, hi))
            assert r["planned_attack_dates"] is None            # rules plans no attacks
            day_nums.append(n)
        assert day_nums == sorted(day_nums) and len(set(day_nums)) == len(day_nums), day_nums
