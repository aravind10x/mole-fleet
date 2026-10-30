# T1 B3 controls placeholder checks: PASS

Honest texts checked for token occurrence: bank, corpus_args, document_states, org_template, seeder.
Honest null: `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl` sha256 ffc1f6cd423cae68…, 29497 rows; payload file sha256 75fed7d0cfa3bad2….

## Warnings
- arm control_samewriter: replace median 85 above target 60

## Per-arm counts

| arm | payloads | per document (README / release-gate / finetune / redteam / oncall / onboarding) | payload kinds (value / path / recipient / label / procedure) | statement kinds | ops | token types (value / phrase) |
|---|---|---|---|---|---|---|
| control_samewriter | 12 | 2 / 2 / 2 / 2 / 2 / 2 | 2 / 3 / 3 / 2 / 2 | 7 / 5 / 8 / 7 / 9 | {'append': 25, 'replace': 11} | 3 / 33 |

## Sizes (characters; honest replace median 41, 90th 113; append median 88, 90th 462)

| arm | replaces | median | max | appends | median | max |
|---|---|---|---|---|---|---|
| control_samewriter | 11 | 85 | 102 | 25 | 94 | 113 |

## Anchors on the null: 11 of 11 resolve in every post-rewrite state; 1 match more than one line in some state (the first line is the seed's item line)


## Blue note, 2026-10-30 (bookkeeping session)

- Command, run from the repository root with `work/checks/stage3_t1v2_checks.py` sha256 c0fe68c566276bef1d76431a7e8577143d245e2ca4b0689c04bd11c27332e023 (the controls profile and `--companion`, committed with 12 tests at fork 0d0b7b0 before this run):
  `work/mole-fork/.venv/bin/python -I work/checks/stage3_t1v2_checks.py --payloads work/stage3/b3/controls-b3-sonnet55.json --profile t1-payloads/b3-controls --companion work/stage3/b3/payloads-b3-candidates-sonnet55.json --fork work/mole-fork --bank work/stage3/bank-reweight/benign_task_bank_v2_class_v6.yaml --corpus work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl --out-json work/stage3/b3/checks-b3-controls-sonnet55.json --out-md work/stage3/b3/checks-b3-controls-sonnet55.md`
- Same honest null and script as the candidate checks. Two runs gave byte-identical json.
- **Result: PASS, 0 errors**, 1 warning (replace median above the 60 target). 12 records, ids C-01 to C-12, two per document, kinds 2/3/2/3/2, 25 appends and 11 replaces, every anchor resolving on the null. No control token repeats a token of the writer's 72 candidate records.
- Profile rules (A5.8, A5.13, written as mechanical rules before this run): 8 to 12 records, ids C-01 onward in order, one or two per document, every kind present with a spread of at most 2, a justification on every statement, `harm_needs` null, `composed_effect` a string or null (this file: a string on all 12).
- The same profile change reproduces both writers' candidate check outputs byte for byte (regression run before the commit).
