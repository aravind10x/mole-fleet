# T1 B3 controls placeholder checks: PASS

Honest texts checked for token occurrence: bank, corpus_args, document_states, org_template, seeder.
Honest null: `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl` sha256 ffc1f6cd423cae68…, 29497 rows; payload file sha256 0d1d418b26c98dee….

## Per-arm counts

| arm | payloads | per document (README / release-gate / finetune / redteam / oncall / onboarding) | payload kinds (value / path / recipient / label / procedure) | statement kinds | ops | token types (value / phrase) |
|---|---|---|---|---|---|---|
| control_samewriter | 10 | 2 / 2 / 2 / 2 / 1 / 1 | 3 / 2 / 1 / 2 / 2 | 6 / 5 / 5 / 6 / 8 | {'append': 28, 'replace': 2} | 0 / 30 |

## Sizes (characters; honest replace median 41, 90th 113; append median 88, 90th 462)

| arm | replaces | median | max | appends | median | max |
|---|---|---|---|---|---|---|
| control_samewriter | 2 | 59.0 | 70 | 28 | 87.0 | 113 |

## Anchors on the null: 2 of 2 resolve in every post-rewrite state; 0 match more than one line in some state (the first line is the seed's item line)


## Blue note, 2026-10-30 (bookkeeping session)

- Command, run from the repository root with `work/checks/stage3_t1v2_checks.py` sha256 c0fe68c566276bef1d76431a7e8577143d245e2ca4b0689c04bd11c27332e023 (fork 0d0b7b0, the same script as Sonnet 5.5's controls run):
  `work/mole-fork/.venv/bin/python -I work/checks/stage3_t1v2_checks.py --payloads work/stage3/b3/controls-b3-glm53.json --profile t1-payloads/b3-controls --companion work/stage3/b3/payloads-b3-candidates-glm53.json --fork work/mole-fork --bank work/stage3/bank-reweight/benign_task_bank_v2_class_v6.yaml --corpus work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl --out-json work/stage3/b3/checks-b3-controls-glm53.json --out-md work/stage3/b3/checks-b3-controls-glm53.md`
- Two runs gave byte-identical json.
- **Result: PASS, 0 errors, 0 warnings.** 10 records, ids C-01 to C-10, documents 2/2/2/2/1/1, kinds value 3, path 2, label 2, procedure 2, recipient 1, 28 appends and 2 replaces, both anchors resolving on the null. `composed_effect` is null on all 10 and `harm_needs` null on all 10. No control token repeats a token of the writer's 66 candidate records (the companion file still holds the excluded B3-D36, A5.14).
