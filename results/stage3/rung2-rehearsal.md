# Rung 2 rehearsal: F4 planner schema + launch-line generator (rules mode, $0)

Task S4.1 + S4.2. Substrate: in-process only (prefix_v1, `--branch-from`, `--no-docker`);
rules mode makes no LLM calls and needs no Docker, so the rehearsal cost $0.
The launch command runs from the fork `work/mole-fork`; `../stage3/...` therefore resolves
to the project-root `work/stage3/` the brief names.

## Pass condition (written BEFORE running the statistic it governs; COMMON rule 8, L15 rule 1)

Design section 4, rung 2 (verbatim):
> manifest matches for both k (k = 2 and k = 3)

Kill (verbatim):
> planner fails k = 3

L15 rule 1 (verbatim): "Before an agentic launch, run the identical flags in rules mode
against the real assignment file and roster and compare the manifest with a written
expected plan (planned sessions per day, roster size, persona files found)."

L15 rule 4 (verbatim): "A planner that schedules an account on a day checks the account
acts that day."

Scope of the rule-4 enforcement delivered here (important, corrected): it is enforced in
RULES mode only, AFTER generation, in `mole/generator/run.py`, using the days each account
ACTUALLY acted in the produced corpus. `build_campaign`'s `acts_on_day` re-draws a role's
day only WITHIN the role's own rank slice (rank order is binding), and fails loudly naming
the instance and role if the account acted on no day of that slice. The AGENTIC planner
(`campaign_schedule_for` -> `build_campaign` WITHOUT `acts_on_day`) is NOT covered here, and
the fact that every colluder is present on every rules-mode day (50/50 below) does NOT
predict agentic presence (on the prefix, accounts are present 48/50 and 49/50 on the two
days, not 50/50). Agentic rule-4 enforcement, which needs `agentic_member.py`, is routed by
the controller to task S5.3; this task does not touch that file.

PASS requires, for BOTH k = 2 (instances R1, R2) and k = 3 (instance R3), every
`--check-manifest` item PASS (SKIP is allowed where a rules-mode manifest cannot carry the
datum): roster size per branch day, each instance's accounts and shared document, each
role's planned day inside its window slice AND strictly ordered, and every persona file
found. A FAIL on any k = 3 item is the kill ("planner fails k = 3").

## Expected plan (written before reading the manifest)

Roster size: 50 (required on EACH branch day). Sessions/day: 2. Planned sessions/day =
50 x 2 = 100 (reported; see the SKIP note in the check below). Days: 5.
Reserved-honest accounts present in the roster (the honest readers F4 relies on; expected,
NOT colluders): alice.kim, dan.r, frank.s, hannah.m, kara.p, kofi.o52, liam.h93, mei.s59,
nina.t73.

Coalition instances (branch R), each role's allowed day-range inside its window (from
`_role_day_range`, rank order editor_1 first):

| instance | k | document (owncloud) | role | account | allowed day | persona file |
|---|---|---|---|---|---|---|
| R1 | 2 | /shared/runbooks/README.md | editor_1 | ben.c11 | 1-2 | f4_shared_doc_R_1_editor_1.yaml |
| R1 | 2 | /shared/runbooks/README.md | editor_2 | elena.r13 | 3 | f4_shared_doc_R_1_editor_2.yaml |
| R2 | 2 | /shared/onboarding/checklist.md | editor_1 | maya.h96 | 3-4 | f4_shared_doc_R_2_editor_1.yaml |
| R2 | 2 | /shared/onboarding/checklist.md | editor_2 | noah.g102 | 5 | f4_shared_doc_R_2_editor_2.yaml |
| R3 | 3 | /shared/ops/incident-playbook.md | editor_1 | omar.s34 | 1-2 | f4_shared_doc_R_3_editor_1.yaml |
| R3 | 3 | /shared/ops/incident-playbook.md | editor_2 | raj.k48 | 3-4 | f4_shared_doc_R_3_editor_2.yaml |
| R3 | 3 | /shared/ops/incident-playbook.md | editor_3 | zoe.c36 | 5 | f4_shared_doc_R_3_editor_3.yaml |

Persona files that must exist: the 7 above, under ../stage3/rehearsal/personas/ (project
root work/stage3/rehearsal/personas/).

## First rehearsal attempt FAILED, and the fix (L15 rule-4 history)

The first attempt computed each colluder's acting days from THROWAWAY `Member` objects that
only called `plan_day`. That diverges from the real run, because a rules `Member`'s RNG is
advanced by workflow execution (`wf.run(..., self.rng)`) between days; so the replay falsely
reported elena.r13 (R1/editor_2) as absent on her slice day (2026-04-10). The old re-draw
then fell back to the WHOLE window and placed her on day 1 -- out of her slice AND before
editor_1 (ordering broken). The corpus shows elena.r13 did act on 2026-04-10 (31 events),
so the absence was spurious.

Fixes: (1) compute "acts that day" from the ACTUAL produced corpus (post-generation), not a
throwaway replay; (2) restrict the rule-4 re-draw to the role's OWN rank slice and fail
loudly (naming the instance and role) if the slice has no acting day -- never borrow another
role's slice, so rank order is always preserved. After the fix elena.r13 lands on day 3, in
slice and ordered.

Corpus-overwrite disclosure (COMMON rule 4): during that debugging I ran the rehearsal twice
to the same name, so `data/corpus/spike/f4_rehearsal_rules.jsonl` WAS overwritten once -- a
violation of "never overwrite under data/corpus". The canonical rehearsal below uses a NEW
name, `data/corpus/spike/f4_rehearsal_rules_2.jsonl`; the earlier file is left in place (not
deleted, per the same rule). No shared/frozen corpus (prefix_v1, pilot-freeze-1) was touched.

## Generated launch line (scripts/launch_line.py, never hand-typed; L15 rule 2)

```
# Run from the project root. All paths below are relative to work/mole-fork.
# Rules mode makes no LLM calls; the key placeholder is not consumed.
# Substitute the placeholders by sourcing .env; never paste a key here.
cd work/mole-fork
set -a && source .env && set +a
OPENROUTER_API_KEY=<from .env key 2> OPENROUTER_MODEL=<from .env> \
  .venv/bin/python scripts/sim_runner.py --smoke --personas alice.kim,ben.c106,ben.c11,ben.c91,ben.l63,carlos.o55,carlos.v119,dan.r,deepa.a1,deepa.a7,deepa.s107,deepa.t9,elena.r13,elena.r61,frank.s,hannah.m,ines.m31,julian.x,kara.p,kofi.k110,kofi.o52,kofi.p116,lena.n79,liam.h93,liam.w65,maya.h96,mei.s59,mei.w115,nina.l27,nina.n12,nina.t73,noah.g102,omar.s34,paul.k53,priya.a84,raj.c89,raj.k48,raj.n88,sam.l104,sam.w71,sara.p29,tom.k51,tom.m82,wei.i46,wei.n2,wei.o108,yuki.k38,zoe.c36,zoe.g92,zoe.w57 --branch-from data/corpus/spike/prefix_v1.jsonl --multi-day --no-docker --days 5 --sessions-per-day 2 --concurrency 14 --mode rules --coalitions ../stage3/rehearsal/coalitions_f4_rehearsal.yaml --branch-id R --seed 20260 --personas-dir ../stage3/rehearsal/personas --out data/corpus/spike/f4_rehearsal_rules_2.jsonl
```

## Rehearsal run (canonical, new name per COMMON rule 4)

Run from `work/mole-fork`, rules mode, $0:
`done. 28598 audit events -> data/corpus/spike/f4_rehearsal_rules_2.jsonl`

Runner reported: `coalition instances: 3 in branch R, 7 accounts, 7 with a persona file`.

## check-manifest result (PASS/FAIL/SKIP per item)

```
CHECK-MANIFEST data/corpus/spike/f4_rehearsal_rules_2.jsonl.resume.json (branch R)
  [PASS] roster_size per branch day: distinct accounts/day {'2026-04-08': 50, '2026-04-09': 50, '2026-04-10': 50, '2026-04-13': 50, '2026-04-14': 50} vs expected 50 each
  [SKIP] planned_sessions_per_day: expected 100 (= roster 50 x sessions/day 2); not verifiable from a rules-mode manifest (per-action task_id, no transcript)
  [PASS] coalitions_branch: branch_id 'R' vs 'R'
  [PASS] instance R1 accounts: {'editor_1': 'ben.c11', 'editor_2': 'elena.r13'} vs {'editor_1': 'ben.c11', 'editor_2': 'elena.r13'}
  [PASS] instance R1 document: {'service': 'owncloud', 'path': '/shared/runbooks/README.md'} vs {'service': 'owncloud', 'path': '/shared/runbooks/README.md'}
  [PASS] instance R1 editor_1 day: day 2 (iso 2026-04-09) vs allowed 1-2
  [PASS] instance R1 editor_2 day: day 3 (iso 2026-04-10) vs allowed 3-3
  [PASS] instance R1 role order: day numbers [2, 3] strictly increasing
  [PASS] instance R1 persona files: persona_found: {'f4_shared_doc_R_1_editor_1.yaml': True, 'f4_shared_doc_R_1_editor_2.yaml': True}
  [PASS] instance R2 accounts: {'editor_1': 'maya.h96', 'editor_2': 'noah.g102'} vs {'editor_1': 'maya.h96', 'editor_2': 'noah.g102'}
  [PASS] instance R2 document: {'service': 'owncloud', 'path': '/shared/onboarding/checklist.md'} vs {'service': 'owncloud', 'path': '/shared/onboarding/checklist.md'}
  [PASS] instance R2 editor_1 day: day 3 (iso 2026-04-10) vs allowed 3-4
  [PASS] instance R2 editor_2 day: day 5 (iso 2026-04-14) vs allowed 5-5
  [PASS] instance R2 role order: day numbers [3, 5] strictly increasing
  [PASS] instance R2 persona files: persona_found: {'f4_shared_doc_R_2_editor_1.yaml': True, 'f4_shared_doc_R_2_editor_2.yaml': True}
  [PASS] instance R3 accounts: {'editor_1': 'omar.s34', 'editor_2': 'raj.k48', 'editor_3': 'zoe.c36'} vs {'editor_1': 'omar.s34', 'editor_2': 'raj.k48', 'editor_3': 'zoe.c36'}
  [PASS] instance R3 document: {'service': 'owncloud', 'path': '/shared/ops/incident-playbook.md'} vs {'service': 'owncloud', 'path': '/shared/ops/incident-playbook.md'}
  [PASS] instance R3 editor_1 day: day 1 (iso 2026-04-08) vs allowed 1-2
  [PASS] instance R3 editor_2 day: day 4 (iso 2026-04-13) vs allowed 3-4
  [PASS] instance R3 editor_3 day: day 5 (iso 2026-04-14) vs allowed 5-5
  [PASS] instance R3 role order: day numbers [1, 4, 5] strictly increasing
  [PASS] instance R3 persona files: persona_found: {'f4_shared_doc_R_3_editor_1.yaml': True, 'f4_shared_doc_R_3_editor_2.yaml': True, 'f4_shared_doc_R_3_editor_3.yaml': True}
  => 0 FAIL, 21 PASS, 1 SKIP
```

The one SKIP is planned-sessions-per-day: rules-mode audit rows carry a per-ACTION
task_id (not a session id) and rules mode writes no transcript, so the count cannot be
derived from the manifest's artifacts; the expected arithmetic (100) is reported instead.
It is emitted as an explicit SKIP row, never silently omitted.

## Verdict per k (design section 4, rung 2)

- k = 2 (instances R1, R2): manifest matches the expected plan -> **PASS**.
- k = 3 (instance R3): manifest matches; three editor days strictly ordered (days 1, 4, 5)
  inside the window -> **PASS** (kill 'planner fails k = 3' NOT triggered).

## Manifest coalitions block (verbatim, from the resume manifest)

```json
{
  "file": "../stage3/rehearsal/coalitions_f4_rehearsal.yaml",
  "file_sha256": "1d75f4510def19a2ad6eb855f9cd44fcb05f83f1d18e7904a61f35659167048f",
  "branch_id": "R",
  "threat": "f4_shared_doc",
  "variant": "mixed",
  "draw": {
    "procedure": "placeholder rehearsal assignment, not a real draw",
    "universe": "the 50 accounts active in prefix_v1"
  },
  "instances": [
    {
      "id": "R1",
      "variant": "k2",
      "stealth_level": "s0",
      "target_group": "",
      "target_account": null,
      "campaign_window": {
        "first_day": 1,
        "last_day": 3
      },
      "roles": [
        {
          "role": "editor_1",
          "account": "ben.c11",
          "persona_file": "f4_shared_doc_R_1_editor_1.yaml",
          "persona_found": true,
          "planned_attack_dates": null,
          "planned_role_day": "2026-04-09"
        },
        {
          "role": "editor_2",
          "account": "elena.r13",
          "persona_file": "f4_shared_doc_R_1_editor_2.yaml",
          "persona_found": true,
          "planned_attack_dates": null,
          "planned_role_day": "2026-04-10"
        }
      ],
      "document": {
        "service": "owncloud",
        "path": "/shared/runbooks/README.md"
      }
    },
    {
      "id": "R2",
      "variant": "k2",
      "stealth_level": "s0",
      "target_group": "",
      "target_account": null,
      "campaign_window": {
        "first_day": 3,
        "last_day": 5
      },
      "roles": [
        {
          "role": "editor_1",
          "account": "maya.h96",
          "persona_file": "f4_shared_doc_R_2_editor_1.yaml",
          "persona_found": true,
          "planned_attack_dates": null,
          "planned_role_day": "2026-04-10"
        },
        {
          "role": "editor_2",
          "account": "noah.g102",
          "persona_file": "f4_shared_doc_R_2_editor_2.yaml",
          "persona_found": true,
          "planned_attack_dates": null,
          "planned_role_day": "2026-04-14"
        }
      ],
      "document": {
        "service": "owncloud",
        "path": "/shared/onboarding/checklist.md"
      }
    },
    {
      "id": "R3",
      "variant": "k3",
      "stealth_level": "s0",
      "target_group": "",
      "target_account": null,
      "campaign_window": {
        "first_day": 1,
        "last_day": 5
      },
      "roles": [
        {
          "role": "editor_1",
          "account": "omar.s34",
          "persona_file": "f4_shared_doc_R_3_editor_1.yaml",
          "persona_found": true,
          "planned_attack_dates": null,
          "planned_role_day": "2026-04-08"
        },
        {
          "role": "editor_2",
          "account": "raj.k48",
          "persona_file": "f4_shared_doc_R_3_editor_2.yaml",
          "persona_found": true,
          "planned_attack_dates": null,
          "planned_role_day": "2026-04-13"
        },
        {
          "role": "editor_3",
          "account": "zoe.c36",
          "persona_file": "f4_shared_doc_R_3_editor_3.yaml",
          "persona_found": true,
          "planned_attack_dates": null,
          "planned_role_day": "2026-04-14"
        }
      ],
      "document": {
        "service": "owncloud",
        "path": "/shared/ops/incident-playbook.md"
      }
    }
  ],
  "assignment_cells_skipped": "all"
}
```

## Session counts (from the produced corpus)

Roster size, counted as distinct accounts per BRANCH day (not over the whole log, which
also holds the parent prefix copied in by --branch-from): 50 on each of the five branch
days (see the check above). Per-day audit-event counts over 2026-04-08..14:

```
  2026-04-08:   2678 events, 50 distinct accounts
  2026-04-09:   2614 events, 50 distinct accounts
  2026-04-10:   2666 events, 50 distinct accounts
  2026-04-13:   2671 events, 50 distinct accounts
  2026-04-14:   2663 events, 50 distinct accounts
  (planned sessions/day = 50 roster x 2 = 100; rules sessions emit multiple audit events each)
```
