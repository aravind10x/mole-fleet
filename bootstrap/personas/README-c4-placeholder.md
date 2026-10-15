# C4 persona files: one file per coalition instance and role

Threat `c4_access_split` (privilege escalation split across a requester and an approver)
runs as several coalition INSTANCES per generated branch. The instances are listed in
`bootstrap/coalitions_stage2b.yaml` (one block per branch; each instance names its
accounts per role, its stealth level, the protected group the request targets, and its
campaign window). The simulator reads that file with `--coalitions <file> --branch-id <A|B|C>`
and loads one persona file per (instance, role).

## File names and location

`bootstrap/personas/c4_access_split_<branch>_<n>_<role>.yaml`, where `<branch>_<n>` is the
instance id split into its letter and number (instance `A1` → `c4_access_split_A_1_requester.yaml`
and `c4_access_split_A_1_approver.yaml`; instance `C5` → `c4_access_split_C_5_requester.yaml`
and `c4_access_split_C_5_approver.yaml`).

The files live in `bootstrap/personas/` only. The legacy `bootstrap/personas_human/` set is
not used for C4: `--coalitions` runs with the default `--persona-set agent`, and no
`personas_human` file is needed or read for these accounts.

## Fields

Copy the shape of the existing collusion personas (for example
`bootstrap/personas/c3_release_sabotage_s0_approver.yaml`), not their content:

```yaml
employee_id: <the account named for this role in coalitions_stage2b.yaml>
threat: c4_access_split
stealth_level: <s0 | s1, as given for the instance in coalitions_stage2b.yaml>
role_label: <requester | approver>
persona_override: |
  <free text>
```

The loader checks `employee_id`, `threat`, `stealth_level` and `role_label` against the
assignment file and stops with an error on any mismatch, or on an empty `persona_override`.
For an instance role with no file it prints `warn: persona file missing for <account> ...`
and that account is never planned as an attacker; there must be no such warning for a
drawn account when a branch is launched.

## What the simulator does with them

Each role's account runs its routine work as any other account does. On its scheduled day
inside the instance's campaign window, one of its sessions runs with `persona_override`
in place of the account's routine persona; the account decides what to do within that
session. Nothing else about the account's prompt changes, and nothing is appended.

## History

Stage 2a T4 (2026-10-14) wrote the blue-side scaffolding for this threat and left six
per-(level, role) placeholder files unwritten (`c4_access_split_<s0|s1>_<requester|approver|group_admin>.yaml`).
Those placeholders are superseded by the instance files above. The `c4_access_split` block
of `bootstrap/insider_assignment.yaml` is kept for the task module's seeded METADATA
targets only; when `--coalitions` is given, that block is ignored by the runner.
