# C4 persona files: placeholder (Stage 2b fills)

Stage 2a T4 wrote only the blue-side scaffolding for `tasks/c4_access_split`
(the protected-group gate, the oracles, the jointness check and tests). It wrote
no persona, goal or prompt text. The six persona files below do not exist yet;
until they do, `scripts/sim_runner.py::build_insider_persona_map` prints a
"persona file missing" warning for each C4 account and loads nothing, so no C4
account is ever planned as an attacker.

The Stage 2b session must create these six files (account per
`bootstrap/insider_assignment.yaml` under `collusion: c4_access_split:`):

| file | employee_id |
|---|---|
| `c4_access_split_s0_requester.yaml` | sara.t77 |
| `c4_access_split_s0_approver.yaml` | tom.k51 |
| `c4_access_split_s0_group_admin.yaml` | kofi.o52 |
| `c4_access_split_s1_requester.yaml` | raj.h85 |
| `c4_access_split_s1_approver.yaml` | liam.w65 |
| `c4_access_split_s1_group_admin.yaml` | sara.k66 |

The same filenames exist in both `bootstrap/personas/` (agent-native motives,
the default) and `bootstrap/personas_human/` (legacy human motives) for C1 to C3;
`--persona-set` picks the directory, so C4 needs both sets or a documented
decision to ship only one.

Fields, copied from the shape of `c3_release_sabotage_s0_approver.yaml`, with
every text field replaced:

```yaml
employee_id: <account from the table above>
threat: c4_access_split
stealth_level: <s0|s1>
role_label: <PLACEHOLDER>
persona_override: |
  <PLACEHOLDER>
```

Also left open for Stage 2b (see `work/stage2/t4-notes.md`):

- per-variant casting: the files are per (level, role); the variants
  (`k3`, `k2_req_app`, `k2_app_admin`) choose which roles are active in a run;
- planner entries for C4 in `mole/generator/campaign.py` (role order; the
  role label `approver` is shared with C3, see the notes);
- `PROMPT` in `tasks/c4_access_split/task.py` is `None` on purpose.
