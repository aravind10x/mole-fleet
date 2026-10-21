"""Tests for scripts/launch_line.py (coalition launch-line generator, L15 rule 2).

Fixtures use prefix accounts and placeholder persona text only; no attack content."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
for _p in (REPO, REPO / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import launch_line as ll  # noqa: E402


ROSTER = ["ben.c11", "elena.r13", "maya.h96", "noah.g102", "omar.s34", "raj.k48",
          "zoe.c36", "tom.k51", "deepa.a1", "liam.w65"]


def _doc(**over):
    doc = {
        "schema": "coalitions-v2", "threat": "f4_shared_doc", "variant": "k3",
        "reserved_honest_accounts": ["liam.w65"],
        "generation": {
            "parent_snapshot": "data/corpus/spike/prefix_v1.jsonl",
            "personas": ",".join(ROSTER), "days": 5, "sessions_per_day": 2,
            "concurrency": 14, "mode": "rules", "seed": 20260,
            "out": "data/corpus/spike/f4_rehearsal_rules.jsonl",
            "personas_dir": "../stage3/rehearsal/personas",
            "extra_flags": ["--multi-day", "--no-docker"],
        },
        "branches": {"R": {"instances": [
            {"id": "R1", "variant": "k2",
             "document": {"service": "owncloud", "path": "/shared/runbooks/README.md"},
             "roles": {"editor_1": "ben.c11", "editor_2": "elena.r13"},
             "campaign_window": {"first_day": 1, "last_day": 3}},
            {"id": "R2", "variant": "k3",
             "document": {"service": "plane", "path": "/team/plan.md"},
             "roles": {"editor_1": "omar.s34", "editor_2": "raj.k48", "editor_3": "zoe.c36"},
             "campaign_window": {"first_day": 1, "last_day": 5}},
        ]}},
    }
    doc.update(over)
    return doc


def _write(tmp_path, doc, name="coalitions_f4.yaml"):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return p


def test_expected_plan(tmp_path):
    p = _write(tmp_path, _doc())
    plan = ll.build_expected_plan(p, "R")
    assert plan["roster_size"] == len(ROSTER)
    assert plan["sessions_per_day"] == 2
    assert plan["planned_sessions_per_day"] == len(ROSTER) * 2
    assert plan["roster_contains_reserved"] == ["liam.w65"]        # honest reader, allowed
    r1, r2 = plan["instances"]
    assert r1["id"] == "R1" and r1["document"]["path"] == "/shared/runbooks/README.md"
    # k2 over a 3-day window: editor_1 days 1-2, editor_2 day 3
    assert [r["day_range"] for r in r1["roles"]] == [[1, 2], [3, 3]]
    # k3 over a 5-day window: editor_1 1-2, editor_2 3-4, editor_3 5
    assert [r["day_range"] for r in r2["roles"]] == [[1, 2], [3, 4], [5, 5]]
    assert len(plan["persona_files"]) == 5


def test_refuses_duplicate_roster_names_and_counts_the_set(tmp_path):
    """Branch review 2026-10-20, erratum 3: roster_size counted the list, so a duplicated
    name in generation.personas failed a correct run's roster check. A duplicate is refused
    with a clear error naming it; the size is the set's."""
    doc = _doc()
    doc["generation"]["personas"] = ",".join(ROSTER + ["ben.c11"])      # ben.c11 twice
    p = _write(tmp_path, doc)
    with pytest.raises(ll.LaunchError, match=r"duplicate.*ben\.c11"):
        ll.build_expected_plan(p, "R")
    with pytest.raises(ll.LaunchError, match="duplicate"):
        ll.build_command(p, "R")
    # a roster given as a YAML list with a duplicate is refused the same way
    doc["generation"]["personas"] = ROSTER + ["tom.k51"]
    p2 = _write(tmp_path, doc, "dup_list.yaml")
    with pytest.raises(ll.LaunchError, match=r"duplicate.*tom\.k51"):
        ll.build_expected_plan(p2, "R")
    # and a clean roster's size is the number of distinct names
    assert ll.build_expected_plan(_write(tmp_path, _doc(), "clean.yaml"), "R")["roster_size"] \
        == len(set(ROSTER))


def test_refuses_when_roster_missing_coalition_account(tmp_path):
    doc = _doc()
    doc["generation"]["personas"] = "ben.c11,elena.r13"            # omits R2's accounts
    p = _write(tmp_path, doc)
    with pytest.raises(ll.LaunchError, match="missing"):
        ll.build_expected_plan(p, "R")


def test_refuses_when_coalition_account_is_reserved(tmp_path):
    doc = _doc()
    doc["reserved_honest_accounts"] = ["ben.c11"]                  # ben.c11 is a colluder
    p = _write(tmp_path, doc)
    # the loader refuses first ("in reserved_honest_accounts"); launch_line surfaces it.
    with pytest.raises(ll.LaunchError, match="reserved"):
        ll.build_expected_plan(p, "R")


def test_refuses_on_draw_excluded_account(tmp_path):
    doc = _doc()
    doc["draw"] = {"excluded": {"team_managers": ["zoe.c36"]}}     # zoe.c36 is a colluder
    p = _write(tmp_path, doc)
    with pytest.raises(ll.LaunchError, match="reserved-honest"):
        ll.build_expected_plan(p, "R")


def test_command_has_flags_and_key_placeholder_only(tmp_path):
    p = _write(tmp_path, _doc())
    cmd = ll.build_command(p, "R")
    assert "scripts/sim_runner.py" in cmd
    assert "--mode rules" in cmd
    assert "--coalitions" in cmd and "--branch-id R" in cmd
    assert "--branch-from data/corpus/spike/prefix_v1.jsonl" in cmd
    assert "--multi-day" in cmd and "--no-docker" in cmd
    assert "--days 5" in cmd and "--sessions-per-day 2" in cmd
    assert "--personas-dir ../stage3/rehearsal/personas" in cmd
    assert "--seed 20260" in cmd
    assert ",".join(ROSTER) in cmd                                 # full roster, not a count
    # the key is selected by VARIABLE NAME from the sourced .env, never a value
    assert 'OPENROUTER_API_KEY="${OPENROUTER_API_KEY_2}"' in cmd
    assert "sk-" not in cmd


def _run_lines(cmd: str) -> list[str]:
    return [ln for ln in cmd.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def test_command_is_runnable_verbatim_no_placeholder(tmp_path):
    """Branch review 2026-10-20, erratum 4 (L15 rule 2): the emitted line had a `<...>`
    placeholder (a shell redirect) and an assignment that would override the sourced key, so
    the operator hand-edited it. The emitted text must contain no placeholder, select the key
    by variable name after sourcing .env, unset the other key so the client cannot fall back
    to another account's key (L3: a 402 is a stop), name the model, and parse as bash."""
    import shutil
    import subprocess
    p = _write(tmp_path, _doc())
    cmd = ll.build_command(p, "R")
    body = "\n".join(_run_lines(cmd))
    assert "<" not in body and ">" not in body, body
    assert "set -a && source .env && set +a" in body
    assert 'export OPENROUTER_API_KEY="${OPENROUTER_API_KEY_2}"' in body
    assert "unset OPENROUTER_API_KEY_2" in body
    assert "OPENROUTER_MODEL=moonshotai/kimi-k2.6" in body          # the default generator
    # the key export happens AFTER sourcing and BEFORE the runner line
    i_src = body.index("source .env"); i_key = body.index("export OPENROUTER_API_KEY")
    i_run = body.index("scripts/sim_runner.py")
    assert i_src < i_key < i_run
    bash = shutil.which("bash")
    assert bash, "bash needed for the syntax check"
    r = subprocess.run([bash, "-n"], input=cmd, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr


def test_command_key_and_model_come_from_the_assignment(tmp_path):
    doc = _doc()
    doc["generation"]["key"] = 1
    doc["generation"]["model"] = "moonshotai/kimi-k2.6"
    p = _write(tmp_path, doc)
    cmd = ll.build_command(p, "R")
    assert 'export OPENROUTER_API_KEY="${OPENROUTER_API_KEY}"' in cmd       # key 1 by name
    assert "unset OPENROUTER_API_KEY_2" in cmd
    assert "${OPENROUTER_API_KEY_2}" not in cmd
    doc["generation"]["key"] = 3
    with pytest.raises(ll.LaunchError, match="key"):
        ll.build_command(_write(tmp_path, doc, "k3.yaml"), "R")


def test_agentic_mode_emits_agentic(tmp_path):
    doc = _doc()
    doc["generation"]["mode"] = "agentic"
    p = _write(tmp_path, doc)
    assert "--mode agentic" in ll.build_command(p, "R")


def _manifest(tmp_path, role_days: dict, **over):
    """A synthetic resume manifest + audit log for check_manifest, matching _doc()'s plan.
    `role_days` maps account -> planned_role_day iso."""
    from mole.generator.coalitions import coalition_maps, load_coalitions, manifest_entry
    p = _write(tmp_path, _doc())
    instances = load_coalitions(p, "R")
    pdir = tmp_path / "personas"
    pdir.mkdir(exist_ok=True)
    from mole.generator.coalitions import persona_file_name
    for inst in instances:
        for role, acct in inst.roles.items():
            (pdir / persona_file_name(inst.threat, inst.id, role)).write_text(
                yaml.safe_dump({"employee_id": acct, "threat": inst.threat,
                                "stealth_level": inst.stealth_level, "role_label": role,
                                "persona_override": "placeholder persona for rehearsal, "
                                                    "routine work only"}), encoding="utf-8")
    maps = coalition_maps(instances, pdir)
    block = manifest_entry(p, "R", instances, maps, None, assignment_cells_skipped="all",
                           role_days=role_days)
    audit = tmp_path / "f4.jsonl"
    # one event per roster account per branch day (so the roster count = len(ROSTER))
    dates = ["2026-04-08", "2026-04-09", "2026-04-10", "2026-04-13", "2026-04-14"]
    with audit.open("w", encoding="utf-8") as f:
        for a in ROSTER:
            for d in dates:
                f.write(json.dumps({"account": a, "ts": f"{d}T10:00:00Z"}) + "\n")
    manifest = {"schema_version": 1, "audit_path": str(audit), "start_date": "2026-04-08",
                "n_days": 5, "coalitions": block}
    manifest.update(over)
    rj = tmp_path / "f4.jsonl.resume.json"
    rj.write_text(json.dumps(manifest), encoding="utf-8")
    return p, rj


def test_check_manifest_all_pass(tmp_path):
    # role days inside each slice and strictly ordered
    p, rj = _manifest(tmp_path, {"ben.c11": "2026-04-09", "elena.r13": "2026-04-10",
                                 "omar.s34": "2026-04-08", "raj.k48": "2026-04-13",
                                 "zoe.c36": "2026-04-14"})
    plan = ll.build_expected_plan(p, "R")
    rows = ll.check_manifest(plan, rj)
    assert not [item for item, ok, _ in rows if ok is False], \
        [r for r in rows if r[1] is False]
    # roster size is a real per-branch-day PASS; planned sessions/day is an explicit SKIP.
    assert ("roster_size per branch day", True) in [(i, o) for i, o, _ in rows]
    assert any(i == "planned_sessions_per_day" and o is None for i, o, _ in rows)
    rc = ll.main([str(p), "--branch-id", "R", "--check-manifest", str(rj)])
    assert rc == 0                                       # SKIP does not fail the run


def test_check_manifest_reads_planned_attack_dates_on_an_agentic_manifest(tmp_path):
    """Branch review 2026-10-20, erratum 2: the agentic path writes planned_attack_dates (no
    planned_role_day); a correct agentic run must PASS every role-day item."""
    from mole.generator.coalitions import coalition_maps, load_coalitions, manifest_entry
    p = _write(tmp_path, _doc())
    instances = load_coalitions(p, "R")
    maps = coalition_maps(instances, tmp_path)           # no persona files: found=False is fine here
    sched = {"ben.c11": [{"date": "2026-04-09", "phase": "act", "directive": None}],
             "elena.r13": [{"date": "2026-04-10", "phase": "act", "directive": None}],
             "omar.s34": [{"date": "2026-04-08", "phase": "act", "directive": None}],
             "raj.k48": [{"date": "2026-04-13", "phase": "act", "directive": None}],
             "zoe.c36": [{"date": "2026-04-14", "phase": "act", "directive": None}]}
    block = manifest_entry(p, "R", instances, maps, sched, assignment_cells_skipped="all")
    assert all("planned_role_day" not in r for i in block["instances"] for r in i["roles"])
    manifest = {"schema_version": 1, "audit_path": str(tmp_path / "none.jsonl"),
                "start_date": "2026-04-08", "n_days": 5, "coalitions": block}
    rj = tmp_path / "agentic.resume.json"
    rj.write_text(json.dumps(manifest), encoding="utf-8")
    plan = ll.build_expected_plan(p, "R")
    rows = ll.check_manifest(plan, rj)
    day_rows = [(i, o) for i, o, _ in rows if i.endswith(" day") or "role order" in i]
    assert day_rows and all(o is True for _, o in day_rows), [r for r in rows if r[1] is False]


def test_check_manifest_fails_on_out_of_window_day(tmp_path):
    # editor_2 of R1 (slice day 3) placed on day 1 -> out of window AND breaks order
    p, rj = _manifest(tmp_path, {"ben.c11": "2026-04-09", "elena.r13": "2026-04-08",
                                 "omar.s34": "2026-04-08", "raj.k48": "2026-04-13",
                                 "zoe.c36": "2026-04-14"})
    plan = ll.build_expected_plan(p, "R")
    rows = ll.check_manifest(plan, rj)
    fails = [item for item, ok, _ in rows if ok is False]
    assert any("R1 editor_2 day" in f for f in fails)
    assert any("R1 role order" in f for f in fails)
    assert ll.main([str(p), "--branch-id", "R", "--check-manifest", str(rj)]) == 1


def test_check_manifest_fails_on_missing_persona(tmp_path):
    p, rj = _manifest(tmp_path, {"ben.c11": "2026-04-09", "elena.r13": "2026-04-10",
                                 "omar.s34": "2026-04-08", "raj.k48": "2026-04-13",
                                 "zoe.c36": "2026-04-14"})
    manifest = json.loads(rj.read_text())
    manifest["coalitions"]["instances"][0]["roles"][0]["persona_found"] = False
    rj.write_text(json.dumps(manifest), encoding="utf-8")
    plan = ll.build_expected_plan(p, "R")
    fails = [item for item, ok, _ in ll.check_manifest(plan, rj) if ok is False]
    assert any("R1 persona files" in f for f in fails)


def test_cli_refusal_exit_code(tmp_path, capsys):
    doc = _doc()
    doc["generation"]["personas"] = "ben.c11"
    p = _write(tmp_path, doc)
    assert ll.main([str(p), "--branch-id", "R"]) == 2
    assert "REFUSED" in capsys.readouterr().err


# ── honest generations, env exports and the agentic manifest items (brief 07c) ──────────


def _honest(tmp_path, **gen_over):
    gen = {"personas": "deepa.a1,wei.n2,zoe.c36", "days": 1, "sessions_per_day": 1,
           "concurrency": 3, "mode": "agentic", "seed": 7,
           "out": "data/corpus/spike/h.jsonl", "key": 2,
           "extra_flags": ["--multi-day", "--no-insiders", "--task-bank", "bank.yaml",
                           "--class-documents"],
           "env": {"LAB_COMPOSE": "$PWD/data/corpus/spike/lab.nogitlab.yaml",
                   "LLM_RETRY_MAX_ATTEMPTS": 40}}
    gen.update(gen_over)
    p = tmp_path / "honest.yaml"
    p.write_text(yaml.safe_dump({"schema": "generation-v1", "generation": gen}))
    return p


def test_honest_generation_has_no_coalition_flags_and_exports_env(tmp_path):
    p = _honest(tmp_path)
    cmd = ll.build_command(p, None)
    assert "--coalitions" not in cmd and "--branch-id" not in cmd
    assert 'export LAB_COMPOSE="$PWD/data/corpus/spike/lab.nogitlab.yaml"' in cmd
    assert 'export LLM_RETRY_MAX_ATTEMPTS="40"' in cmd
    plan = ll.build_expected_plan(p, None)
    assert plan["honest"] and plan["instances"] == [] and plan["class_documents"]
    assert plan["task_bank"] == "bank.yaml"


def test_env_values_with_shell_syntax_are_refused(tmp_path):
    p = _honest(tmp_path, env={"X": "a;rm"})
    with pytest.raises(ll.LaunchError, match="shell syntax"):
        ll.build_command(p, None)


def test_coalition_file_still_needs_a_branch_id(tmp_path):
    p = tmp_path / "a.yaml"
    p.write_text(yaml.safe_dump(_doc()))
    with pytest.raises(ll.LaunchError, match="--branch-id is required"):
        ll.build_expected_plan(p, None)


def _agentic_manifest(tmp_path, bank: Path, **day_over):
    import hashlib
    audit = tmp_path / "h.jsonl"
    audit.write_text("".join(json.dumps({"account": a, "ts": "2026-04-06T09:00:00Z"}) + "\n"
                             for a in ("deepa.a1", "wei.n2", "zoe.c36")))
    day = {"day": "2026-04-06", "sessions_planned": 3, "sessions_completed": 3,
           "sessions_aborted": 0, "attack_sessions_planned": 0, "snapshot_ok": True,
           "managers_ok": True}
    day.update(day_over)
    man = {"audit_path": str(audit), "start_date": "2026-04-06", "n_days": 1,
           "sandbox_mode": "lab", "days": [day],
           "task_bank": {"sha256": hashlib.sha256(bank.read_bytes()).hexdigest()},
           "class_documents": [{"path": f"/d{i}"} for i in range(6)]}
    mp = tmp_path / "h.jsonl.resume.json"
    mp.write_text(json.dumps(man))
    return mp


def test_check_manifest_reads_the_agentic_items(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bank = tmp_path / "bank.yaml"
    bank.write_text("x: 1\n")
    plan = ll.build_expected_plan(_honest(tmp_path), None)
    rows = {r[0]: r[1] for r in ll.check_manifest(plan, _agentic_manifest(tmp_path, bank))}
    assert all(ok is not False for ok in rows.values()), rows
    assert rows["task bank"] and rows["class documents seeded"]
    assert rows["no coalitions block (honest generation)"]
    bad = {r[0]: r[1] for r in ll.check_manifest(
        plan, _agentic_manifest(tmp_path, bank, sessions_aborted=1, attack_sessions_planned=2))}
    assert bad["day 2026-04-06 sessions aborted"] is False
    assert bad["day 2026-04-06 attack sessions planned"] is False


def test_check_manifest_reads_the_lab_branch_lineage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bank = tmp_path / "bank.yaml"
    bank.write_text("x: 1\n")
    plan = ll.build_expected_plan(_honest(tmp_path, parent_snapshot="p.jsonl",
                                          extra_flags=["--no-insiders"]), None)
    mp = _agentic_manifest(tmp_path, bank)
    man = json.loads(mp.read_text())
    man["branch_from"] = {"parent": "p.jsonl", "snapshot_dir": "/s",
                          "volumes": [{"key": "owncloud-data", "restored_as": "b_owncloud-data"}],
                          "class_documents_at_start": [{"present": True}] * 6}
    mp.write_text(json.dumps(man))
    rows = {r[0]: r[1] for r in ll.check_manifest(plan, mp)}
    assert rows["branch parent"] and rows["branch volumes restored"]
    assert rows["branch class documents at start"]
    man["branch_from"]["class_documents_at_start"][0] = {"present": False}
    mp.write_text(json.dumps(man))
    rows = {r[0]: r[1] for r in ll.check_manifest(plan, mp)}
    assert rows["branch class documents at start"] is False


# ── presence-aware roster (brief 07d, C1 close-out) ──────────────────────────────────────
# The runner's presence draw (mole/generator/presence.py) loafs or absents an account on a
# day, so "every roster account appears every branch day" is the wrong expectation: the C1
# rehearsal's parent planned 1 session for 3 accounts and its branch 2 then 3, all correct.
# The check now expects, per day, exactly the accounts the presence predicate says act
# (member seed = run seed + roster index in load_personas order), and reports the
# all-present reading as an informational line.

def _presence_roster(seed, roster, sessions, days):
    from mole.generator.member import NPCConfig
    from mole.generator.persona_loader import load_personas
    from mole.generator.presence import acts_predicate
    order = [p.id for p in load_personas() if p.id in set(roster)]
    pred = acts_predicate(seed, {a: i for i, a in enumerate(order)}, NPCConfig(
        sessions_per_day=sessions), sessions)
    return {d: {a for a in roster if pred(a, d)} for d in days}


def _seed_with_a_loafer(roster, sessions, days):
    for seed in range(1, 500):
        acting = _presence_roster(seed, roster, sessions, days)
        if any(len(acting[d]) < len(roster) for d in days):
            return seed, acting
    raise AssertionError("no seed under 500 loafs an account; presence defaults changed?")


def _presence_manifest(tmp_path, roster, run_seed, sessions, days, acting, **man_over):
    audit = tmp_path / "pr.jsonl"
    with audit.open("w", encoding="utf-8") as f:
        for d in days:
            for a in sorted(acting[d]):
                f.write(json.dumps({"account": a, "ts": f"{d}T10:00:00Z"}) + "\n")
    man = {"schema_version": 1, "audit_path": str(audit), "start_date": days[0],
           "n_days": len(days), "seed": run_seed, "sandbox_mode": "lab",
           "days": [{"day": d, "sessions_planned": len(acting[d]) * sessions,
                     "sessions_completed": len(acting[d]) * sessions, "sessions_aborted": 0,
                     "attack_sessions_planned": 0, "snapshot_ok": True, "managers_ok": True}
                    for d in days]}
    man.update(man_over)
    mp = tmp_path / "pr.jsonl.resume.json"
    mp.write_text(json.dumps(man), encoding="utf-8")
    return mp


def test_roster_check_expects_the_presence_aware_roster_per_day(tmp_path):
    roster = ["wei.n2", "ben.c11", "zoe.c36"]
    days = ["2026-04-06", "2026-04-07"]
    seed, acting = _seed_with_a_loafer(roster, 1, days)
    p = _honest(tmp_path, personas=",".join(roster), days=2, sessions_per_day=1, seed=seed,
                extra_flags=["--multi-day", "--no-insiders"])
    plan = ll.build_expected_plan(p, None)
    assert plan["seed"] == seed
    rows = {r[0]: r for r in ll.check_manifest(plan, _presence_manifest(
        tmp_path, roster, seed, 1, days, acting))}
    assert rows["roster_size per branch day"][1] is True, rows["roster_size per branch day"]
    # the all-present reading survives as information (never a FAIL)
    info = rows["roster all-present reading (informational)"]
    assert info[1] is None and "expected 3 each" in info[2]
    assert rows["seed"][1] is True
    # the exact per-day planned-session count follows the same draw
    for d in days:
        assert rows[f"day {d} sessions planned (presence-aware)"][1] is True


def test_roster_check_fails_when_a_loafed_account_acts_or_an_acting_one_is_missing(tmp_path):
    roster = ["wei.n2", "ben.c11", "zoe.c36"]
    days = ["2026-04-06", "2026-04-07"]
    seed, acting = _seed_with_a_loafer(roster, 1, days)
    p = _honest(tmp_path, personas=",".join(roster), days=2, sessions_per_day=1, seed=seed,
                extra_flags=["--multi-day", "--no-insiders"])
    plan = ll.build_expected_plan(p, None)
    # every account every day (the old expectation) is now a FAIL on a loafing seed
    everyone = {d: set(roster) for d in days}
    rows = {r[0]: r for r in ll.check_manifest(plan, _presence_manifest(
        tmp_path, roster, seed, 1, days, everyone))}
    assert rows["roster_size per branch day"][1] is False
    # an acting account missing from the log is a FAIL too
    short = {d: set(list(sorted(acting[d]))[1:]) for d in days}
    rows = {r[0]: r for r in ll.check_manifest(plan, _presence_manifest(
        tmp_path, roster, seed, 1, days, short))}
    assert rows["roster_size per branch day"][1] is False
    # a manifest seed that differs from the plan's is a FAIL
    rows = {r[0]: r for r in ll.check_manifest(plan, _presence_manifest(
        tmp_path, roster, seed, 1, days, acting, **{"seed": seed + 1}))}
    assert rows["seed"][1] is False


def test_rules_mode_roster_check_is_absence_aware_only(tmp_path):
    """Rules-mode members draw more slots than the agentic member (sessions x touch-points),
    so an account the agentic draw loafs can still appear in a rules log: rules manifests
    are checked against the absence draw (PTO) only: every present account, no absent one."""
    roster = ["wei.n2", "ben.c11", "zoe.c36"]
    days = ["2026-04-06"]
    for seed in range(1, 500):                        # a seed with a present-but-loafed account
        p = _honest(tmp_path, personas=",".join(roster), days=1, sessions_per_day=1, seed=seed,
                    mode="rules", extra_flags=["--multi-day", "--no-insiders"])
        plan = ll.build_expected_plan(p, None)
        pres = ll.expected_presence(plan, seed, days)[days[0]]
        if pres["acts"] < pres["present"]:
            break
    else:
        raise AssertionError("no seed under 500 loafs a present account")
    mp = _presence_manifest(tmp_path, roster, seed, 1, days, {days[0]: pres["present"]})
    man = json.loads(mp.read_text())
    del man["days"]                                   # rules manifests carry no day records
    mp.write_text(json.dumps(man))
    rows = {r[0]: r for r in ll.check_manifest(plan, mp)}
    assert rows["roster_size per branch day"][1] is True, rows["roster_size per branch day"]
    assert rows["agentic day records"][1] is None
    # a present account missing from the rules log is still a FAIL
    mp = _presence_manifest(tmp_path, roster, seed, 1, days, {days[0]: pres["acts"]})
    man = json.loads(mp.read_text()); del man["days"]; mp.write_text(json.dumps(man))
    rows = {r[0]: r for r in ll.check_manifest(plan, mp)}
    assert rows["roster_size per branch day"][1] is False


def test_rules_mode_is_read_from_the_manifest_not_the_assignment(tmp_path):
    """The L15 rehearsal runs the AGENTIC assignment's line with --mode rules: the manifest
    (no per-day session records) decides the absence-aware reading, not the plan's mode."""
    roster = ["wei.n2", "ben.c11", "zoe.c36"]
    days = ["2026-04-06"]
    for seed in range(1, 500):
        p = _honest(tmp_path, personas=",".join(roster), days=1, sessions_per_day=1, seed=seed,
                    extra_flags=["--multi-day", "--no-insiders"])      # mode: agentic
        plan = ll.build_expected_plan(p, None)
        pres = ll.expected_presence(plan, seed, days)[days[0]]
        if pres["acts"] < pres["present"]:
            break
    mp = _presence_manifest(tmp_path, roster, seed, 1, days, {days[0]: pres["present"]})
    man = json.loads(mp.read_text()); del man["days"]; mp.write_text(json.dumps(man))
    rows = {r[0]: r for r in ll.check_manifest(plan, mp)}
    assert rows["roster_size per branch day"][1] is True, rows["roster_size per branch day"]
    assert "rules mode" in rows["roster_size per branch day"][2]
