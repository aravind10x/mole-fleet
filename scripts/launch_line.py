#!/usr/bin/env python
"""Generate the exact `sim_runner.py` launch line for a coalition assignment file.

Lesson L15 (rule 2) forbids hand-typed launch lines: one dropped account or a header
that counts the persona list instead of the roster has already cost a coalition. This
script is the single source of a launch command. It reads an assignment file's
`generation` block (the launch flags the controller recorded beside the draw) and prints:

  1. the env-export prefix (a PLACEHOLDER for the key, never its value) + the full
     `sim_runner.py` command for a named branch, in `--mode rules` or `--mode agentic`;
  2. the EXPECTED PLAN (roster size, planned sessions/day = roster x sessions/day, the
     coalition instances with each role's allowed day-range inside its window, the shared
     document per F4 instance, and the persona files that must exist) so L15 rule 1's
     "compare the manifest to a written plan" is mechanical.

`--check-manifest <resume.json>` loads a produced run manifest and prints PASS/FAIL per
item of that expected plan (roster size from the audit log, each coalition instance's
accounts and document, each role's planned day in-window and strictly ordered, the
persona files found).

It REFUSES (non-zero exit, nothing printed to run) when the roster is missing any
coalition account, or when a coalition (colluder) account is a reserved honest account.
Note: the roster legitimately CONTAINS reserved honest accounts -- they are the honest
workforce F4 relies on to read the poisoned document -- so the refusal is on a colluder
BEING reserved, not on a reserved account appearing in the roster (see the report).

The `generation` block this reads:

    generation:
      parent_snapshot: data/corpus/spike/prefix_v1.jsonl   # optional -> --branch-from
      personas: a,b,c            # colluders + honest roster; comma str OR a YAML list
      days: 5
      sessions_per_day: 2
      concurrency: 14
      mode: rules                # -> --mode rules | --mode agentic
      smoke: true                # -> pass --smoke (optional, default true)
      seed: 20260                # OR seeds: {R: 20260}
      out: data/corpus/spike/f4_rehearsal_rules.jsonl
      personas_dir: work/stage3/rehearsal/personas   # optional -> --personas-dir
      extra_flags: [--multi-day, --no-docker]        # optional, verbatim

No persona, objective or directive text anywhere.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import yaml  # noqa: E402

from mole.generator.campaign import _role_day_range  # noqa: E402
from mole.generator.coalitions import load_coalitions  # noqa: E402
from mole.generator.run import _weekday_dates  # noqa: E402

#: Printed, never a real secret -- the operator substitutes it by sourcing .env.
KEY_PLACEHOLDER = "OPENROUTER_API_KEY=<from .env key 2>"
MODEL_PLACEHOLDER = "OPENROUTER_MODEL=<from .env>"


class LaunchError(Exception):
    """A refusal: the assignment and roster cannot be launched safely."""


def _personas_list(gen: dict) -> list[str]:
    raw = gen.get("personas")
    if raw is None:
        raise LaunchError("generation.personas is required (comma string or list)")
    if isinstance(raw, str):
        names = [x.strip() for x in raw.split(",") if x.strip()]
    elif isinstance(raw, (list, tuple)):
        names = [str(x).strip() for x in raw if str(x).strip()]
    else:
        raise LaunchError(f"generation.personas must be a string or list, got {type(raw).__name__}")
    # A duplicated name would make the runner's roster smaller than the list and fail the
    # roster-size check against a correct run (branch review 2026-10-20, erratum 3): refuse
    # it here, naming the duplicates, so the assignment file is fixed before any launch.
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        raise LaunchError(f"generation.personas has duplicate name(s): {dups} "
                          f"(each account once; the roster is a set)")
    return names


def _reserved_accounts(doc: dict) -> set[str]:
    """Accounts that may never be colluders: reserved_honest_accounts plus every
    name under the draw's `excluded` block (team managers, upstream colluders, etc.)."""
    reserved = set(doc.get("reserved_honest_accounts") or [])
    excluded = (doc.get("draw") or {}).get("excluded") or {}
    for names in excluded.values():
        reserved.update(names or [])
    return reserved


def _coalition_accounts(instances) -> dict[str, str]:
    """{account: instance id} over every role of every instance."""
    out: dict[str, str] = {}
    for inst in instances:
        for acct in inst.roles.values():
            out[acct] = inst.id
    return out


def _seed_for(gen: dict, branch_id: str) -> int | None:
    if "seeds" in gen and gen["seeds"] is not None:
        return gen["seeds"].get(branch_id)
    return gen.get("seed")


def build_expected_plan(assignment: str | Path, branch_id: str) -> dict:
    """The expected plan for a branch: roster, sessions, and per-instance role-day
    windows + document + persona files. Raises LaunchError on an unlaunchable roster."""
    p = Path(assignment)
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    gen = doc.get("generation") or {}
    try:
        instances = load_coalitions(p, branch_id)    # already refuses a reserved colluder
    except ValueError as exc:
        raise LaunchError(str(exc)) from None
    roster = _personas_list(gen)
    roster_set = set(roster)
    reserved = _reserved_accounts(doc)
    coalition = _coalition_accounts(instances)

    missing = sorted(set(coalition) - roster_set)
    if missing:
        raise LaunchError(f"roster is missing {len(missing)} coalition account(s): {missing}")
    bad_reserved = sorted(a for a in coalition if a in reserved)
    if bad_reserved:
        raise LaunchError(f"coalition account(s) are reserved-honest and may not collude: "
                          f"{bad_reserved}")

    sessions_per_day = int(gen.get("sessions_per_day") or 0)
    inst_plan = []
    persona_files: list[str] = []
    for inst in instances:
        roles = inst.role_order
        n = inst.window[1] - inst.window[0] + 1
        role_rows = []
        for rank, role in enumerate(roles):
            lo, hi = _role_day_range(rank, len(roles), n)
            role_rows.append({
                "role": role, "account": inst.roles[role],
                "day_range": [inst.window[0] + lo, inst.window[0] + hi],  # branch day numbers
                "persona_file": inst.persona_files[role],
            })
            persona_files.append(inst.persona_files[role])
        inst_plan.append({
            "id": inst.id, "document": inst.document,
            "window": [inst.window[0], inst.window[1]], "roles": role_rows,
        })

    return {
        "assignment": str(p), "branch_id": branch_id,
        "roster_size": len(roster_set), "sessions_per_day": sessions_per_day,
        "planned_sessions_per_day": len(roster_set) * sessions_per_day,
        "days": int(gen.get("days") or 0),
        "mode": str(gen.get("mode") or "agentic"),
        "roster_contains_reserved": sorted(roster_set & reserved),
        "instances": inst_plan, "persona_files": persona_files,
    }


def build_command(assignment: str | Path, branch_id: str) -> str:
    """The exact `sim_runner.py` command (with the env-export placeholder prefix)."""
    p = Path(assignment)
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    gen = doc.get("generation") or {}
    roster = _personas_list(gen)
    mode = str(gen.get("mode") or "agentic")
    args: list[str] = [".venv/bin/python", "scripts/sim_runner.py"]
    if gen.get("smoke", True):
        args.append("--smoke")
    args += ["--personas", ",".join(roster)]
    if gen.get("parent_snapshot"):
        args += ["--branch-from", str(gen["parent_snapshot"])]
    for flag in (gen.get("extra_flags") or []):
        args.append(str(flag))
    if gen.get("days") is not None:
        args += ["--days", str(gen["days"])]
    if gen.get("sessions_per_day") is not None:
        args += ["--sessions-per-day", str(gen["sessions_per_day"])]
    if gen.get("concurrency") is not None:
        args += ["--concurrency", str(gen["concurrency"])]
    args += ["--mode", mode]
    args += ["--coalitions", str(p), "--branch-id", branch_id]
    seed = _seed_for(gen, branch_id)
    if seed is not None:
        args += ["--seed", str(seed)]
    if gen.get("personas_dir"):
        args += ["--personas-dir", str(gen["personas_dir"])]
    if gen.get("out"):
        args += ["--out", str(gen["out"])]

    # One working directory throughout: the fork. Every path in the command (and the
    # .env the operator sources for the real key/model) is relative to it. Comments sit
    # on their own lines, never after a backslash continuation.
    lines = ["# Run from the project root. All paths below are relative to work/mole-fork."]
    if mode == "rules":
        lines.append("# Rules mode makes no LLM calls; the key placeholder is not consumed.")
    lines.append("# Substitute the placeholders by sourcing .env; never paste a key here.")
    lines.append("cd work/mole-fork")
    lines.append("set -a && source .env && set +a")
    lines.append(f"{KEY_PLACEHOLDER} {MODEL_PLACEHOLDER} \\")
    lines.append("  " + " ".join(args))
    return "\n".join(lines)


def _branch_dates(manifest: dict) -> list[str]:
    """The run's branch working days, from start_date / n_days."""
    sd = manifest.get("start_date")
    if not sd:
        return []
    return _weekday_dates(_date(sd), int(manifest.get("n_days") or 0))


def _branch_day_accounts(manifest: dict) -> dict[str, set[str]] | None:
    """{branch_day: set(accounts active that day)} from the audit log, restricted to the
    BRANCH working days (excludes the parent prefix copied in by --branch-from). None if
    the log cannot be read."""
    ap = manifest.get("audit_path")
    if not ap or not Path(ap).exists():
        return None
    dates = set(_branch_dates(manifest))
    by_day: dict[str, set[str]] = {d: set() for d in dates}
    with Path(ap).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            a, ts = rec.get("account"), rec.get("ts", "")
            if a and ts[:10] in by_day:
                by_day[ts[:10]].add(a)
    return by_day


def check_manifest(expected: dict, manifest_path: str | Path) -> list[tuple[str, bool | None, str]]:
    """Compare a produced manifest with the expected plan. Returns (item, PASS/FAIL/None,
    detail) rows; None = SKIP (could not be checked)."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    rows: list[tuple[str, bool | None, str]] = []

    # 1. roster size, counted per BRANCH day (not over the whole log, which also holds the
    #    parent prefix copied in by --branch-from): every branch day must show the full
    #    roster of distinct accounts.
    by_day = _branch_day_accounts(manifest)
    exp_n = expected["roster_size"]
    if by_day is None:
        rows.append(("roster_size", None, "audit log not found; cannot count the roster"))
    elif not by_day:
        rows.append(("roster_size", None, "no branch dates (start_date/n_days missing)"))
    else:
        counts = {d: len(a) for d, a in sorted(by_day.items())}
        ok = all(c == exp_n for c in counts.values())
        rows.append(("roster_size per branch day", ok,
                     f"distinct accounts/day {counts} vs expected {exp_n} each"))

    # 2. planned sessions per day = roster x sessions/day. Rules-mode audit rows carry a
    #    per-ACTION task_id (not a session id) and rules mode writes no transcript, so the
    #    session count cannot be derived from the manifest's artifacts -> explicit SKIP
    #    (never silently omitted). The expected arithmetic is reported for the operator.
    rows.append(("planned_sessions_per_day", None,
                 f"expected {expected['planned_sessions_per_day']} "
                 f"(= roster {exp_n} x sessions/day {expected['sessions_per_day']}); not "
                 f"verifiable from a rules-mode manifest (per-action task_id, no transcript)"))

    # 3. coalition block present for this branch.
    block = manifest.get("coalitions")
    if not block:
        rows.append(("coalitions_block", False, "manifest has no coalitions block"))
        return rows
    rows.append(("coalitions_branch", block.get("branch_id") == expected["branch_id"],
                 f"branch_id {block.get('branch_id')!r} vs {expected['branch_id']!r}"))

    by_id = {i["id"]: i for i in block.get("instances", [])}
    dates = _branch_dates(manifest)

    for exp_inst in expected["instances"]:
        iid = exp_inst["id"]
        got = by_id.get(iid)
        if got is None:
            rows.append((f"instance {iid}", False, "absent from the manifest"))
            continue
        # accounts per role
        got_roles = {r["role"]: r["account"] for r in got.get("roles", [])}
        exp_roles = {r["role"]: r["account"] for r in exp_inst["roles"]}
        rows.append((f"instance {iid} accounts", got_roles == exp_roles,
                     f"{got_roles} vs {exp_roles}"))
        # shared document
        rows.append((f"instance {iid} document", got.get("document") == exp_inst["document"],
                     f"{got.get('document')} vs {exp_inst['document']}"))
        # role days: in the role's window slice and strictly ordered across roles
        day_nums: list[int | None] = []
        for exp_role in exp_inst["roles"]:
            gr = next((r for r in got.get("roles", []) if r["role"] == exp_role["role"]), None)
            day_iso = _planned_day(gr)
            num = (dates.index(day_iso) + 1) if (day_iso in dates) else None
            day_nums.append(num)
            lo, hi = exp_role["day_range"]
            ok = num is not None and lo <= num <= hi
            rows.append((f"instance {iid} {exp_role['role']} day", ok,
                         f"day {num} (iso {day_iso}) vs allowed {lo}-{hi}"))
        ordered = all(a is not None and b is not None and a < b
                      for a, b in zip(day_nums, day_nums[1:]))
        rows.append((f"instance {iid} role order", ordered if len(day_nums) > 1 else True,
                     f"day numbers {day_nums} strictly increasing"))
        # persona files present (found flag in the manifest)
        found = {r["persona_file"]: r.get("persona_found") for r in got.get("roles", [])}
        rows.append((f"instance {iid} persona files", all(found.values()) if found else False,
                     f"persona_found: {found}"))
    return rows


def _planned_day(role_rec: dict | None) -> str | None:
    """The day a role is planned to act. Rules mode records it as `planned_role_day`; the
    agentic path records the campaign in `planned_attack_dates` (one date per F4 role day),
    which is read when the other field is absent (branch review 2026-10-20, erratum 2). More
    than one planned date is not a single role day and yields None (a FAIL, never a pass)."""
    if not role_rec:
        return None
    if role_rec.get("planned_role_day") is not None:
        return role_rec["planned_role_day"]
    dates = role_rec.get("planned_attack_dates")
    if isinstance(dates, list) and len(dates) == 1:
        return dates[0]
    return None


def _date(iso: str):
    from datetime import date
    return date.fromisoformat(iso)


def _print_expected(plan: dict) -> None:
    print("EXPECTED PLAN")
    print(f"  assignment       : {plan['assignment']}")
    print(f"  branch           : {plan['branch_id']}   mode: {plan['mode']}   days: {plan['days']}")
    print(f"  roster size      : {plan['roster_size']}")
    print(f"  sessions/day     : {plan['sessions_per_day']}")
    print(f"  planned sess/day : {plan['planned_sessions_per_day']}  (roster x sessions/day)")
    if plan["roster_contains_reserved"]:
        print(f"  reserved-honest accounts in roster (honest readers, expected): "
              f"{plan['roster_contains_reserved']}")
    print(f"  coalition instances ({len(plan['instances'])}):")
    for inst in plan["instances"]:
        print(f"    {inst['id']}  window {inst['window'][0]}-{inst['window'][1]}  "
              f"document={inst['document']}")
        for r in inst["roles"]:
            print(f"      {r['role']:<9} {r['account']:<14} day {r['day_range'][0]}-"
                  f"{r['day_range'][1]}   persona: {r['persona_file']}")
    print(f"  persona files that must exist: {len(plan['persona_files'])}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="launch_line",
                                 description="Generate a coalition launch line from an "
                                             "assignment file (L15 rule 2).")
    ap.add_argument("assignment", help="Coalition assignment YAML (schema v1 or v2).")
    ap.add_argument("--branch-id", required=True, help="Which branch to launch (e.g. R).")
    ap.add_argument("--check-manifest", default=None, metavar="RESUME_JSON",
                    help="Compare a produced run manifest (<out>.resume.json) with the "
                         "expected plan and print PASS/FAIL per item.")
    args = ap.parse_args(argv)

    try:
        plan = build_expected_plan(args.assignment, args.branch_id)
    except LaunchError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    if args.check_manifest:
        rows = check_manifest(plan, args.check_manifest)
        print(f"CHECK-MANIFEST {args.check_manifest} (branch {args.branch_id})")
        failed = 0
        for item, ok, detail in rows:
            tag = "PASS" if ok else ("SKIP" if ok is None else "FAIL")
            if ok is False:
                failed += 1
            print(f"  [{tag}] {item}: {detail}")
        print(f"  => {failed} FAIL, {sum(1 for _, o, _ in rows if o)} PASS, "
              f"{sum(1 for _, o, _ in rows if o is None)} SKIP")
        return 1 if failed else 0

    print(build_command(args.assignment, args.branch_id))
    print()
    _print_expected(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
