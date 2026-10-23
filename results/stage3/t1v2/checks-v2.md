# T1 v2 placeholder checks: PASS

Honest texts checked for token occurrence: bank, corpus_args, document_states, org_template, seeder.
Honest null: `work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl` sha256 ffc1f6cd423cae68…, 29497 rows; payload file sha256 b2fe230bc2b3111e….

## Warnings
- arm conforming: replace median 88.5 above target 60
- arm alarming: replace median 88 above target 60
- arm sham: replace median 75 above target 60

## Per-arm counts

| arm | payloads | per document (README / release-gate / finetune / redteam / oncall / onboarding) | payload kinds (value / path / recipient / label / procedure) | statement kinds | ops | token types (value / phrase) |
|---|---|---|---|---|---|---|
| conforming | 24 | 4 / 4 / 4 / 4 / 4 / 4 | 5 / 5 / 5 / 5 / 4 | 9 / 13 / 5 / 21 / 24 | {'replace': 40, 'append': 32} | 36 / 36 |
| alarming | 8 | 1 / 2 / 1 / 2 / 1 / 1 | 2 / 0 / 0 / 1 / 5 | 3 / 0 / 0 / 3 / 18 | {'replace': 15, 'append': 9} | 0 / 24 |
| sham | 24 | 4 / 4 / 4 / 4 / 4 / 4 | 5 / 5 / 5 / 5 / 4 | 16 / 12 / 15 / 15 / 14 | {'append': 43, 'replace': 29} | 7 / 65 |

## Sizes (characters; honest replace median 41, 90th 113; append median 88, 90th 462)

| arm | replaces | median | max | appends | median | max |
|---|---|---|---|---|---|---|
| conforming | 40 | 88.5 | 113 | 32 | 92.0 | 126 |
| alarming | 15 | 88 | 112 | 9 | 78 | 93 |
| sham | 29 | 75 | 111 | 43 | 81 | 113 |

## Anchors on the null: 84 of 84 resolve in every post-rewrite state; 4 match more than one line in some state (the first line is the seed's item line)

