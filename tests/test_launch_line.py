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
    # the key is a placeholder, never a value
    assert "OPENROUTER_API_KEY=<from .env key 2>" in cmd
    assert "sk-" not in cmd


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
