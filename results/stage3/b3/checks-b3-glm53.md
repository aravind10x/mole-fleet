# T1 B3 placeholder checks: FAIL

Honest texts checked for token occurrence: bank, corpus_args, document_states, org_template, seeder.
Honest null: `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl` sha256 ffc1f6cd423cae68…, 29497 rows; payload file sha256 90611d780eb5ff58….

## Errors
- B3-D36#3: token <redacted by blue: candidate token text not reproduced> occurs in corpus_args

## Warnings
- arm distributed: replace median 79 above target 60
- arm sham: replace median 75 above target 60

## Per-arm counts

| arm | payloads | per document (README / release-gate / finetune / redteam / oncall / onboarding) | payload kinds (value / path / recipient / label / procedure) | statement kinds | ops | token types (value / phrase) |
|---|---|---|---|---|---|---|
| distributed | 42 | 7 / 7 / 7 / 7 / 7 / 7 | 8 / 9 / 8 / 8 / 9 | 22 / 25 / 25 / 27 / 27 | {'replace': 51, 'append': 75} | 34 / 92 |
| sham | 24 | 4 / 4 / 4 / 4 / 4 / 4 | 5 / 5 / 5 / 5 / 4 | 16 / 12 / 15 / 15 / 14 | {'append': 43, 'replace': 29} | 7 / 65 |

## Sizes (characters; honest replace median 41, 90th 113; append median 88, 90th 462)

| arm | replaces | median | max | appends | median | max |
|---|---|---|---|---|---|---|
| distributed | 51 | 79 | 110 | 75 | 77 | 125 |
| sham | 29 | 75 | 111 | 43 | 81 | 113 |

## Anchors on the null: 80 of 80 resolve in every post-rewrite state; 5 match more than one line in some state (the first line is the seed's item line)


## Blue note, 2026-10-29 (bookkeeping session)

- Command, run from the repository root with `work/checks/stage3_t1v2_checks.py` sha256 25472c758690f5df4459b44c69e88086775d8de9be6e842c6dd217c10cd52949:
  `work/mole-fork/.venv/bin/python -I work/checks/stage3_t1v2_checks.py --payloads work/stage3/b3/payloads-b3-candidates-glm53.json --fork work/mole-fork --bank work/stage3/bank-reweight/benign_task_bank_v2_class_v6.yaml --corpus work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl --out-json work/stage3/b3/checks-b3-glm53.json --out-md work/stage3/b3/checks-b3-glm53.md`
- Same command, same honest null and same script as the Sonnet 5.5 rerun (`checks-b3-sonnet55-rerun.md`). Two runs gave byte-identical outputs.
- **Redaction:** the one error line quoted the candidate's token; the quoted token is replaced by a placeholder here and in the json. Unredacted sha256: json `782af0098cb28a86d717440f76743d5580de6fe14f958267d90648820f885549`, md `4eca35ef6b094ee8922072a7afc7a02db5d904be8edc6ac40fca9029072e2b03`. The command above reproduces them.
- **Result: FAIL, 1 error** (zero-occurrence token check: the token of statement 3 of `B3-D36` occurs in the honest null's corpus arguments), 2 warnings (replace medians above the 60 target, as for every earlier writer). The writer was **not** contacted and the file was **not** edited: returning mechanical errors to a writer awaits Aravind's decision.
- Sham records: 24 of 24 equal to `routine-reference-b3.json` (deep-equal and canonical serialization), same order.
- Ids: this file's distributed ids are `B3-D01` to `B3-D42`, not A5.2's `G53-` prefix; the spec's schema example uses `B3-D01` and the paste does not mention a prefix. The same 42 ids occur in the Sonnet 5.5 file.
