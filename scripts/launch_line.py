#!/usr/bin/env python
"""Generate the exact `sim_runner.py` launch line for a coalition assignment file.

Lesson L15 (rule 2) forbids hand-typed launch lines: one dropped account or a header
that counts the persona list instead of the roster has already cost a coalition. This
script is the single source of a launch command. It reads an assignment file's
`generation` block (the launch flags the controller recorded beside the draw) and prints:

  1. the env prefix (source .env; export the key selected BY VARIABLE NAME, never a value
     and never a placeholder; name the model) + the full `sim_runner.py` command for a
     named branch, in `--mode rules` or `--mode agentic`, runnable verbatim;
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
      key: 2                     # optional: .env key number, 1 or 2 (default 2)
      fallback_key: 2            # optional, only with key 1: keep key 2 set as the client's
                                 # rotation target on a 402 / key-limit 403 (never unset)
      model: moonshotai/kimi-k2.6   # optional: OPENROUTER_MODEL slug (default as shown)
      env:                       # optional: exported before the runner, verbatim
        LAB_COMPOSE: $PWD/data/corpus/spike/lab.nogitlab.yaml
        LLM_RETRY_MAX_ATTEMPTS: 40

A file with a `generation` block and NO `branches` block is an honest generation (a
prefix or a branch parent): the command has no `--coalitions` / `--branch-id`, the expected
plan has no instances, and `--branch-id` may be omitted.

The roster check is PRESENCE-AWARE (brief 07d): the runner's presence draw
(mole/generator/presence.py; member seed = run seed + roster index in load_personas order)
absents or loafs an account on a day, so each branch day is expected to show exactly the
accounts the predicate says act (agentic) or the accounts not absent (rules mode, whose
members draw more slots); the all-present reading stays as an informational line, and the
manifest's seed must equal the plan's.

`--check-manifest` on an AGENTIC manifest also checks, per day, sessions planned (at most
roster x sessions/day, and exactly the presence draw's kept slots), none aborted, the attack sessions
planned (0 for an honest run), the day's snapshot and managers export; the task bank's
sha256 against `--task-bank`; the six class documents under `--class-documents`; and, for a
lab branch, the lineage (snapshot directory, every volume restored, the class documents
present at start). Rules-mode manifests SKIP these (rules mode records none of them).

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

#: The key is selected by VARIABLE NAME from the sourced .env (never a value, never a
#: placeholder the operator must edit: L15 rule 2). `generation.key` is 1 or 2 (default 2,
#: the project account's key). The other key is unset so the OpenRouter client cannot fall
#: back to another account's key on a 402 (L3: a 402 is a stop, never a retry).
KEY_ENV_BY_NUMBER = {1: "OPENROUTER_API_KEY", 2: "OPENROUTER_API_KEY_2"}
DEFAULT_KEY = 2
#: The generator model slug (`generation.model`); the Stage 2b and Stage 3 generator.
DEFAULT_MODEL = "moonshotai/kimi-k2.6"


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


def _is_honest(doc: dict) -> bool:
    """A generation with no coalition branches (a prefix or a branch parent)."""
    return not doc.get("branches")


def _flag_value(gen: dict, flag: str) -> str | None:
    flags = [str(f) for f in (gen.get("extra_flags") or [])]
    if flag in flags and flags.index(flag) + 1 < len(flags):
        return flags[flags.index(flag) + 1]
    return None


def build_expected_plan(assignment: str | Path, branch_id: str | None) -> dict:
    """The expected plan for a branch: roster, sessions, and per-instance role-day
    windows + document + persona files. Raises LaunchError on an unlaunchable roster."""
    p = Path(assignment)
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    gen = doc.get("generation") or {}
    if _is_honest(doc):
        instances = []
    elif branch_id is None:
        raise LaunchError("this assignment has coalition branches; --branch-id is required")
    else:
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
        "honest": _is_honest(doc),
        "task_bank": _flag_value(gen, "--task-bank"),
        "class_documents": "--class-documents" in [str(f) for f in gen.get("extra_flags") or []],
        "parent": gen.get("parent_snapshot"),
        "roster": roster,
        "seed": _seed_for(gen, branch_id),
        "absent_probability": float(_flag_value(gen, "--absent-prob") or 0.01),
    }


def _key_export(gen: dict) -> str:
    """`export OPENROUTER_API_KEY="${<var>}" && unset OPENROUTER_API_KEY_2` for the key the
    assignment names (1 or 2); refuses anything else."""
    raw = gen.get("key", DEFAULT_KEY)
    try:
        num = int(raw)
    except (TypeError, ValueError):
        num = None
    if num not in KEY_ENV_BY_NUMBER:
        raise LaunchError(f"generation.key must be one of {sorted(KEY_ENV_BY_NUMBER)} "
                          f"(the .env variable number), got {raw!r}")
    var = KEY_ENV_BY_NUMBER[num]
    fb = gen.get("fallback_key")
    if fb is None:
        return f'export OPENROUTER_API_KEY="${{{var}}}" && unset OPENROUTER_API_KEY_2'
    # A declared fallback (Aravind, 2026-10-21, for the world-one prefix: key 1 first, key 2
    # as it exhausts): the client rotates to OPENROUTER_API_KEY_2 on a 402 or a key-limit 403
    # and re-issues the call (mole/llm/openrouter.py _retire_key; tests
    # test_openrouter_key_fallback.py), so no session dies at key 1's weekly cap. Only key 2
    # may be the fallback of key 1; a 402 on the last key is still a stop (L3, L7).
    try:
        fbn = int(fb)
    except (TypeError, ValueError):
        fbn = None
    if num != 1 or fbn != 2:
        raise LaunchError(f"generation.fallback_key must be 2 with generation.key 1, got "
                          f"key {raw!r} fallback {fb!r}")
    return ('export OPENROUTER_API_KEY="${OPENROUTER_API_KEY}" && '
            'export OPENROUTER_API_KEY_2="${OPENROUTER_API_KEY_2}"   '
            '# key 1 active, key 2 the declared fallback (client rotation on 402)')


def _model(gen: dict) -> str:
    model = str(gen.get("model") or DEFAULT_MODEL)
    if not model or any(ch in model for ch in " <>\"'$`;&|"):
        raise LaunchError(f"generation.model must be a plain model slug, got {model!r}")
    return model


def _env_exports(gen: dict) -> list[str]:
    """`export NAME="value"` per `generation.env` entry; names are shell identifiers and
    values may use $VAR but no placeholder or command syntax."""
    out = []
    for name, value in (gen.get("env") or {}).items():
        name, value = str(name), str(value)
        if not name.replace("_", "").isalnum() or not name[0].isalpha():
            raise LaunchError(f"generation.env name {name!r} is not a shell identifier")
        if any(ch in value for ch in "<>\"'`;&|"):
            raise LaunchError(f"generation.env {name} value {value!r} has shell syntax")
        out.append(f'export {name}="{value}"')
    return out


def build_command(assignment: str | Path, branch_id: str | None) -> str:
    """The exact `sim_runner.py` command, runnable verbatim: sources .env, selects the key by
    variable name, names the model, then the runner line. No placeholder anywhere."""
    p = Path(assignment)
    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    gen = doc.get("generation") or {}
    roster = _personas_list(gen)
    mode = str(gen.get("mode") or "agentic")
    key_line = _key_export(gen)
    model = _model(gen)
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
    if not _is_honest(doc):
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
        lines.append("# Rules mode makes no LLM calls; the exported key is not consumed.")
    lines.append("# The key is selected by variable name from .env (generation.key); nothing "
                 "here is edited by hand.")
    lines.append("cd work/mole-fork")
    lines.append("set -a && source .env && set +a")
    lines.append(key_line)
    lines.extend(_env_exports(gen))
    lines.append(f"OPENROUTER_MODEL={model} \\")
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


def expected_presence(expected: dict, seed: int | None, dates: list[str]) -> dict[str, dict]:
    """Per branch day, what the runner's presence draw plans for this roster and seed
    (mole/generator/presence.py, the one stream the members and the coalition planner read):
    `acts` = accounts with at least one kept session that day (the agentic member's slots),
    `present` = accounts not absent (PTO) that day, `planned_sessions` = the kept slots
    summed over the roster (= the manifest's sessions_planned on an agentic run). Member i's
    presence seed is `seed + i` with i the account's index in load_personas order restricted
    to the roster (`run.simulate`); a None seed is unseeded and nothing can be expected."""
    from mole.generator.member import NPCConfig
    from mole.generator.persona_loader import load_personas
    from mole.generator.presence import day_presence
    roster = set(expected["roster"])
    sessions = max(1, int(expected["sessions_per_day"] or 0))
    config = NPCConfig(sessions_per_day=sessions,
                       absent_probability=float(expected.get("absent_probability", 0.01)))
    order = [p.id for p in load_personas() if p.id in roster]
    out: dict[str, dict] = {}
    for d in dates:
        acts, present, planned = set(), set(), 0
        if seed is not None:
            for i, acct in enumerate(order):
                mask = day_presence(int(seed) + i, d, config, sessions)
                if mask is None:
                    continue
                present.add(acct)
                kept = sum(1 for k in mask if k)
                planned += kept
                if kept:
                    acts.add(acct)
        out[d] = {"acts": acts, "present": present, "planned_sessions": planned}
    return out


def check_manifest(expected: dict, manifest_path: str | Path) -> list[tuple[str, bool | None, str]]:
    """Compare a produced manifest with the expected plan. Returns (item, PASS/FAIL/None,
    detail) rows; None = SKIP (could not be checked) or an informational line."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    rows: list[tuple[str, bool | None, str]] = []

    # 0. the seed the run used is the seed the plan names (the presence expectation below
    #    is computed from the plan's seed and is meaningless if the run drew another).
    plan_seed, man_seed = expected.get("seed"), manifest.get("seed")
    if plan_seed is None or man_seed is None:
        rows.append(("seed", None, f"plan seed {plan_seed}, manifest seed {man_seed}; "
                                   f"presence expectation uses the plan's seed"))
    else:
        rows.append(("seed", int(plan_seed) == int(man_seed),
                     f"manifest seed {man_seed} vs plan seed {plan_seed}"))

    # 1. roster per BRANCH day (not over the whole log, which also holds the parent prefix
    #    copied in by --branch-from), against the presence draw: an agentic day must show
    #    exactly the accounts the draw lets act; a rules-mode day (members draw more slots,
    #    so loafing differs) must show every account not absent and no absent one. The
    #    all-present count is kept as information: it is what the roster size would be if
    #    nobody loafed, never a pass or a fail by itself.
    by_day = _branch_day_accounts(manifest)
    exp_n = expected["roster_size"]
    presence = None
    if by_day is None:
        rows.append(("roster_size", None, "audit log not found; cannot count the roster"))
    elif not by_day:
        rows.append(("roster_size", None, "no branch dates (start_date/n_days missing)"))
    else:
        counts = {d: len(a) for d, a in sorted(by_day.items())}
        rows.append(("roster all-present reading (informational)", None,
                     f"distinct accounts/day {counts} vs expected {exp_n} each if nobody "
                     f"loafed or was absent (the presence draw decides; see the next row)"))
        if plan_seed is None:
            rows.append(("roster_size per branch day", None,
                         "no seed in the plan: the presence draw cannot be reproduced"))
        else:
            presence = expected_presence(expected, plan_seed, sorted(by_day))
            # Rules mode is read from the MANIFEST (no per-day session records), not from
            # the assignment: the L15 rehearsal runs the agentic assignment's line with
            # `--mode rules`, so the plan says agentic while the run was rules.
            # Rules mode: the plan says so, or the manifest has no sandbox session id and no
            # per-day session records (an agentic lab run has a session id from its start).
            rules = (str(expected.get("mode") or "agentic") == "rules"
                     or (not manifest.get("session_id")
                         and not any(d.get("sessions_planned") is not None
                                     for d in (manifest.get("days") or []))))
            detail, ok = [], True
            recorded = {d.get("day") for d in (manifest.get("days") or [])}
            for d in sorted(by_day):
                want = presence[d]["present"] if rules else presence[d]["acts"]
                got = by_day[d]
                if not got and d not in recorded:
                    # a mid-run check: this day has no audit row and no day record yet
                    detail.append(f"{d}: not run yet ({len(want)} expected)")
                    continue
                if d not in recorded and not rules:
                    # the day is in progress: rows so far, no day record yet (read again at
                    # its boundary); an account outside the draw would still be unexpected
                    extra = sorted(got - want)
                    ok = ok and not extra
                    detail.append(f"{d}: in progress, {len(got)} of {len(want)} expected acting so far"
                                  + (f", unexpected {extra}" if extra else ""))
                    continue
                extra, missing = sorted(got - want), sorted(want - got)
                ok = ok and not extra and not missing
                detail.append(f"{d}: {len(got)} acting vs {len(want)} expected"
                              + (f", unexpected {extra}" if extra else "")
                              + (f", missing {missing}" if missing else ""))
            rows.append(("roster_size per branch day", ok,
                         ("rules mode, absence-aware" if rules else "presence-aware")
                         + ": " + "; ".join(detail)))

    # 2. planned sessions per day = roster x sessions/day. Rules-mode audit rows carry a
    #    per-ACTION task_id (not a session id) and rules mode writes no transcript, so the
    #    session count cannot be derived from the manifest's artifacts -> explicit SKIP
    #    (never silently omitted). The expected arithmetic is reported for the operator.
    rows.append(("planned_sessions_per_day", None,
                 f"expected {expected['planned_sessions_per_day']} "
                 f"(= roster {exp_n} x sessions/day {expected['sessions_per_day']}); not "
                 f"verifiable from a rules-mode manifest (per-action task_id, no transcript)"))

    rows.extend(_agentic_rows(expected, manifest, presence))

    # 3. coalition block present for this branch (absent for an honest generation).
    block = manifest.get("coalitions")
    if expected.get("honest"):
        rows.append(("no coalitions block (honest generation)", not block,
                     "absent" if not block else f"present: {sorted(block)}"))
        return rows
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


def _agentic_rows(expected: dict, manifest: dict,
                  presence: dict[str, dict] | None = None) -> list[tuple[str, bool | None, str]]:
    """The agentic-only items (SKIP on a rules-mode manifest, which records none of them).
    `presence` (from expected_presence, keyed by branch day) makes the planned-session count
    exact: the draw's kept slots summed over the roster."""
    rows: list[tuple[str, bool | None, str]] = []
    days = manifest.get("days") or []
    agentic = any(d.get("sessions_planned") is not None for d in days)
    if not agentic:
        rows.append(("agentic day records", None,
                     "rules-mode manifest: no per-day session counts recorded"))
        return rows
    cap = expected["planned_sessions_per_day"]
    for d in days:
        day = d.get("day")
        planned = d.get("sessions_planned")
        rows.append((f"day {day} sessions planned", planned is not None and 0 < planned <= cap,
                     f"{planned} planned (at most roster x sessions/day = {cap})"))
        if presence is not None and day in presence:
            want = presence[day]["planned_sessions"]
            rows.append((f"day {day} sessions planned (presence-aware)", planned == want,
                         f"{planned} planned vs {want} kept slots in the presence draw for "
                         f"seed {expected.get('seed')}"))
        rows.append((f"day {day} sessions aborted", d.get("sessions_aborted") == 0,
                     f"{d.get('sessions_aborted')} aborted of {planned}; "
                     f"{d.get('sessions_completed')} completed"))
        if expected.get("honest"):
            rows.append((f"day {day} attack sessions planned",
                         d.get("attack_sessions_planned") == 0,
                         f"{d.get('attack_sessions_planned')} (honest generation: 0)"))
        rows.append((f"day {day} snapshot and managers", bool(d.get("snapshot_ok"))
                     and bool(d.get("managers_ok")),
                     f"snapshot_ok {d.get('snapshot_ok')}, managers_ok {d.get('managers_ok')}"))
    if expected.get("task_bank"):
        import hashlib
        bank = Path(expected["task_bank"])
        want = hashlib.sha256(bank.read_bytes()).hexdigest() if bank.exists() else None
        got = (manifest.get("task_bank") or {}).get("sha256")
        rows.append(("task bank", want is not None and got == want,
                     f"manifest sha256 {got} vs {bank} {want}"))
    if expected.get("class_documents"):
        docs = manifest.get("class_documents") or []
        rows.append(("class documents seeded", len(docs) == 6,
                     f"{len(docs)} recorded: {[d.get('path') for d in docs]}"))
    if expected.get("parent"):
        lin = manifest.get("branch_from") or {}
        rows.append(("branch parent", lin.get("parent") == str(expected["parent"]),
                     f"{lin.get('parent')} vs {expected['parent']}"))
        if manifest.get("sandbox_mode") == "lab":
            vols = lin.get("volumes") or []
            rows.append(("branch volumes restored", bool(vols) and bool(lin.get("snapshot_dir"))
                         and all(v.get("restored_as") for v in vols),
                         f"snapshot_dir {lin.get('snapshot_dir')}; "
                         f"{[(v.get('key'), v.get('restored_as')) for v in vols]}"))
            at_start = lin.get("class_documents_at_start") or []
            rows.append(("branch class documents at start",
                         len(at_start) == 6 and all(r.get("present") for r in at_start),
                         f"{sum(bool(r.get('present')) for r in at_start)} of "
                         f"{len(at_start)} present before the first session"))
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


def derive_start_date(plan: dict, start_date: str | None = None) -> str:
    """The run's first working day: `--start-date` if given; else the next weekday after the
    parent's last complete day (the branch rule, `run._prepare_branch`); else the runner's
    DEFAULT_START_DATE."""
    from mole.generator.run import DEFAULT_START_DATE, _next_weekday
    if start_date:
        return start_date
    parent = plan.get("parent")
    if parent and Path(f"{parent}.resume.json").exists():
        from mole.generator import resume_state
        rec = resume_state.last_completed_record(resume_state.load(Path(parent)))
        if rec and rec.get("managers_ok"):      # the branch rule of run._prepare_branch
            return _next_weekday(rec["day"])
    return DEFAULT_START_DATE


def presence_plan(plan: dict, start_date: str) -> dict:
    """The presence-aware expected plan: per day the acting accounts and the planned session
    count, and per coalition role the slice days on which its account acts (the planner
    keeps the drawn day when the account acts, re-draws inside the slice otherwise, and
    fails loudly when no slice day works, L15 rule 4). An empty `acting_days` for a role is
    the loud failure predicted before the run."""
    dates = _weekday_dates(_date(start_date), int(plan.get("days") or 0))
    pres = expected_presence(plan, plan.get("seed"), dates)
    days = {d: {"acting": sorted(pres[d]["acts"]), "absent": sorted(set(plan["roster"]) - pres[d]["present"]),
                "planned_sessions": pres[d]["planned_sessions"]} for d in dates}
    roles = []
    for inst in plan["instances"]:
        for r in inst["roles"]:
            lo, hi = r["day_range"]
            slice_dates = dates[lo - 1: hi]
            roles.append({"instance": inst["id"], "role": r["role"], "account": r["account"],
                          "slice": slice_dates,
                          "acting_days": [d for d in slice_dates if r["account"] in pres[d]["acts"]]})
    return {"start_date": start_date, "dates": dates, "days": days, "roles": roles,
            "total_planned_sessions": sum(v["planned_sessions"] for v in days.values())}


def _print_presence(plan: dict, start_date: str) -> None:
    if plan.get("seed") is None:
        print("  presence-aware plan: no seed in the assignment; cannot be computed")
        return
    pp = presence_plan(plan, start_date)
    print(f"  PRESENCE-AWARE PLAN (seed {plan['seed']}, start {start_date}; the presence draw "
          f"of mole/generator/presence.py): {pp['total_planned_sessions']} sessions in all")
    for d, v in pp["days"].items():
        print(f"    {d}: {len(v['acting'])} of {plan['roster_size']} accounts act, "
              f"{v['planned_sessions']} sessions planned"
              + (f"; absent {v['absent']}" if v["absent"] else "")
              + (f"; loafed {sorted(set(plan['roster']) - set(v['acting']) - set(v['absent']))}"
                 if len(v["acting"]) + len(v["absent"]) < plan["roster_size"] else ""))
    for r in pp["roles"]:
        tag = "OK" if r["acting_days"] else "NO ACTING DAY IN SLICE: the planner will refuse"
        print(f"    {r['instance']} {r['role']:<9} {r['account']:<12} slice {r['slice']} "
              f"acts on {r['acting_days']}  [{tag}]")


def _print_expected(plan: dict, start_date: str | None = None) -> None:
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
    _print_presence(plan, derive_start_date(plan, start_date))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="launch_line",
                                 description="Generate a coalition launch line from an "
                                             "assignment file (L15 rule 2).")
    ap.add_argument("assignment", help="Coalition assignment YAML (schema v1 or v2).")
    ap.add_argument("--branch-id", default=None,
                    help="Which branch to launch (e.g. R); omitted for an honest generation "
                         "(a file with no branches block).")
    ap.add_argument("--check-manifest", default=None, metavar="RESUME_JSON",
                    help="Compare a produced run manifest (<out>.resume.json) with the "
                         "expected plan and print PASS/FAIL per item.")
    ap.add_argument("--start-date", default=None, metavar="YYYY-MM-DD",
                    help="First working day for the presence-aware expected plan (default: "
                         "the day after the parent's last complete day, else the runner's).")
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
    _print_expected(plan, args.start_date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
