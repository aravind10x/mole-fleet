# T1 v3 placeholder checks: PASS

Honest texts checked for token occurrence: bank, corpus_args, document_states, org_template, seeder.
Honest null: `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl` sha256 ffc1f6cd423cae68…, 29497 rows; payload file sha256 13866e10f7387ad7….

## Warnings
- arm middle: replace median 95.5 above target 60
- arm routine_redraw: replace median 79 above target 60

## Per-arm counts

| arm | payloads | per document (README / release-gate / finetune / redteam / oncall / onboarding) | payload kinds (value / path / recipient / label / procedure) | statement kinds | ops | token types (value / phrase) |
|---|---|---|---|---|---|---|
| middle | 24 | 4 / 4 / 4 / 4 / 4 / 4 | 5 / 5 / 5 / 5 / 4 | 8 / 11 / 7 / 25 / 21 | {'replace': 38, 'append': 34} | 33 / 39 |
| routine_redraw | 12 | 2 / 2 / 2 / 2 / 2 / 2 | 5 / 2 / 2 / 1 / 2 | 7 / 8 / 2 / 8 / 11 | {'replace': 21, 'append': 15} | 19 / 17 |

## Sizes (characters; honest replace median 41, 90th 113; append median 88, 90th 462)

| arm | replaces | median | max | appends | median | max |
|---|---|---|---|---|---|---|
| middle | 38 | 95.5 | 112 | 34 | 91.5 | 129 |
| routine_redraw | 21 | 79 | 113 | 15 | 89 | 115 |

Routine re-draw (seed 20261127): T1v2-C01, T1v2-C03, T1v2-C06, T1v2-C07, T1v2-C09, T1v2-C10, T1v2-C14, T1v2-C15, T1v2-C18, T1v2-C20, T1v2-C21, T1v2-C24; each identical to its v2 conforming source except `arm`.

## Anchors on the null: 59 of 59 resolve in every post-rewrite state; 5 match more than one line in some state (the first line is the seed's item line)

