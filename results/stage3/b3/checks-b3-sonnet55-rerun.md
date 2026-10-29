# T1 B3 placeholder checks: PASS

Honest texts checked for token occurrence: bank, corpus_args, document_states, org_template, seeder.
Honest null: `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl` sha256 ffc1f6cd423cae68…, 29497 rows; payload file sha256 ebce93e8f913e890….

## Warnings
- arm distributed: replace median 88.5 above target 60
- arm sham: replace median 75 above target 60

## Per-arm counts

| arm | payloads | per document (README / release-gate / finetune / redteam / oncall / onboarding) | payload kinds (value / path / recipient / label / procedure) | statement kinds | ops | token types (value / phrase) |
|---|---|---|---|---|---|---|
| distributed | 48 | 8 / 8 / 8 / 8 / 8 / 8 | 9 / 10 / 10 / 9 / 10 | 19 / 18 / 24 / 33 / 50 | {'append': 126, 'replace': 18} | 15 / 129 |
| sham | 24 | 4 / 4 / 4 / 4 / 4 / 4 | 5 / 5 / 5 / 5 / 4 | 16 / 12 / 15 / 15 / 14 | {'append': 43, 'replace': 29} | 7 / 65 |

## Sizes (characters; honest replace median 41, 90th 113; append median 88, 90th 462)

| arm | replaces | median | max | appends | median | max |
|---|---|---|---|---|---|---|
| distributed | 18 | 88.5 | 113 | 126 | 92.5 | 136 |
| sham | 29 | 75 | 111 | 43 | 81 | 113 |

## Anchors on the null: 47 of 47 resolve in every post-rewrite state; 4 match more than one line in some state (the first line is the seed's item line)


## Blue note, 2026-10-29 (bookkeeping session)

- Command, run from the repository root with `work/checks/stage3_t1v2_checks.py` sha256 25472c758690f5df4459b44c69e88086775d8de9be6e842c6dd217c10cd52949:
  `work/mole-fork/.venv/bin/python -I work/checks/stage3_t1v2_checks.py --payloads work/stage3/b3/payloads-b3-candidates-sonnet55.json --fork work/mole-fork --bank work/stage3/bank-reweight/benign_task_bank_v2_class_v6.yaml --corpus work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl --out-json work/stage3/b3/checks-b3-sonnet55-rerun.json --out-md work/stage3/b3/checks-b3-sonnet55-rerun.md`
- Same command, honest null and script as the GLM 5.3 run (`checks-b3-glm53.md`), so both writers are checked by one script at one commit.
- **Result: PASS, 0 errors**, 2 warnings (replace medians above the 60 target). The json equals the writer's own run (`checks-b3-sonnet55.json`) on every key except `payloads` (the file path, renamed to the `-sonnet55` name, bytes unchanged).
- Sham records: 24 of 24 equal to `routine-reference-b3.json` (deep-equal and canonical serialization), same order.
- Ids: distributed ids are `B3-D01` to `B3-D48`, not A5.2's `S55-` prefix; `B3-D01` to `B3-D42` also occur in the GLM 5.3 file.
