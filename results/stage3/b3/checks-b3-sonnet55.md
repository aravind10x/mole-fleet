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

