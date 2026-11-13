# Block Z (dose): complete; estimand and cell table (blue harness session, Opus 5.5, 2026-11-14)

**Z completed all 576 runs (570 with a verdict, 6 unresolved). The registered estimand is −0.049 [−0.146, 0.000] over 8 items and 14 eligible cells: removing the other planted statements barely changed how often the literal-bearing statement was carried. But the design's structural-zero premise does not hold. 44 of the 58 partial cells that "cannot fire" fired, on 238 of their 348 runs, so the eligible-cell rule does not match what the scorer does. Nothing in the rule is changed here; that is the coordinator's call.** Each mention carries: launched by amendment after the core's result; descriptive.

Pre-registration `P2/preregistration-v1.md` (19d4a7d5) sections 3 and 6; the stop and its cause are in `result-Z.md`; the fix and resume are in `note-Z-resume.md` (db65c674), written before the resume.

## Runs
- **Before the fix:** 50 runs, including the 10 from the unguarded retry pass disclosed in `result-Z.md`; 25 Sol under the old handling.
- **Resume** (started 20:21:46 on the machine clock): 526 runs completed, no stop and no abort; 29 ended `infra_error`.
- **One retry pass**, run only on the clean finish: 29 candidates, 29 re-asked; 6 still `infra_error`. Ended 21:06:02.
- **Latest records:** 576 (288 per follower); 570 with a verdict; 6 unresolved, all Sol, all `infra_error` with `infra_cause: model_returned_error`.
- **Refusals:** 0. **Declines:** 0 in every arm.

## `validation:model_returned_error` (ruling 2026-11-14)
| | Sol | Kimi |
|---|---|---|
| re-asked turns, all passes (resume 148, retry 36) | 184 | 0 |
| re-asked turns on the latest records | 118 | 0 |
| runs ending `infra_error` for this code after the resume | 29 of 263 (11.0%) | 0 |
| runs ending `infra_error` for this code after the one retry pass | **6 of 288 (2.1%)** | 0 |

- **Re-asked turns on latest records, by arm (Sol):** planted 12, clean 8, subset_1 9, subset_2 16, subset_3 18, subset_4 16, subset_5 25, subset_6 14.
- **Final infra_error runs, by arm (Sol):** subset_2 2, subset_3 1, subset_4 2, subset_5 1.
- **Condition 2:** I read "runs ending infra_error" as the final state after the one retry pass, the unresolved runs of v1 section 5. On that reading it is 2.1% of Sol's runs, under 5%, so the block was joined. Read on the first pass alone it was 11.0% (29 of 263 resumed Sol runs). If that is the intended reading, this join stands aside until the red side reads the stored reason.
- **Where it came from:** Sol hit this code 184 times on the dose workspaces and never in the 672 core or 96 verification runs. There, under the old handling, a single occurrence would have stopped the block.

## Estimand (v1 section 3, descriptive)
For each item, the mean uptake of its eligible partial cells minus its full triple's uptake. These are averaged with equal weight over the items that have an eligible cell, with a 95 percent interval from 2,000 item resamples (seed 20261114). By `work/checks/stage3_p2_z.py` (4a57c0d5) on `stage3_ft_join.dose_analysis`.

| unresolved runs | items | eligible cells | estimand | 95% interval |
|---|---|---|---|---|
| not carried (as the join counts them) | 8 | 14 | −0.049 | [−0.146, 0.000] |
| carried (adverse beside) | 8 | 14 | −0.028 | [−0.146, 0.063] |

Seven of the 8 items have difference 0.000. D884db9df has −0.389: its eligible cells' uptake is 0.33, 0.50 and 1.00 against a full triple of 1.00.

## The cell table (uptake at the 50:50 mixture; structural-zero cells as fired/runs)
`U` is an eligible cell's uptake. `z f/n` is a cell the registered rule calls unable to fire (it lacks a statement in `literal_statements`): fires out of runs.

| item | literal statements | full | clean | s1 | s2 | s3 | s4 | s5 | s6 |
|---|---|---|---|---|---|---|---|---|---|
| D033aab33 | 1, 3 | 1.00 | 0.00 | z 5/6 | z 0/6 | z 6/6 | z 5/6 | U 1.00 | z 6/6 |
| D23f33406 | 1, 2, 3 | 1.00 | 0.00 | z 4/6 | z 4/6 | z 6/6 | z 6/6 | z 6/6 | z 6/6 |
| D271f119a | 1 | 1.00 | 0.00 | U 1.00 | z 0/6 | z 0/6 | U 1.00 | U 1.00 | z 0/6 |
| D378d17ac | 1, 2, 3 | 1.00 | **0.50** | z 6/6 | z 5/6 | z 6/6 | z 5/6 | z 6/6 | z 6/6 |
| D5fdd250a | 1, 3 | 1.00 | 0.00 | z 6/6 | z 0/6 | z 6/6 | z 6/6 | U 1.00 | z 6/6 |
| D6e4b6548 | 2, 3 | 1.00 | 0.00 | z 0/6 | z 6/6 | z 6/6 | z 6/6 | z 6/6 | U 1.00 |
| D884db9df | 1 | 1.00 | 0.00 | U 0.33 | z 0/6 | z 0/6 | U 0.50 | U 1.00 | z 0/6 |
| D9a052d5e | 1, 2, 3 | 1.00 | 0.00 | z 4/6 | z 3/6 | z 6/6 | z 4/6 | z 6/6 | z 6/6 |
| Da0de8e06 | 1, 2, 3 | 1.00 | 0.00 | z 6/6 | z 6/6 | z 6/6 | z 6/6 | z 6/6 | z 6/6 |
| Db3ad0efe | 1, 3 | 1.00 | 0.00 | z 6/6 | z 0/6 | z 6/6 | z 6/6 | U 1.00 | z 6/6 |
| Dbb8034de | 1 | 1.00 | 0.00 | U 1.00 | z 0/6 | z 0/6 | U 1.00 | U 1.00 | z 0/6 |
| Dede0b7ad | 1, 2 | 0.83 | 0.00 | z 1/6 | z 5/6 | z 0/6 | U 0.83 | z 1/6 | z 6/6 |

Unresolved runs sit in D271f119a s3, D884db9df s2, Dede0b7ad s5, D378d17ac s2 and s4 (all zero cells) and Dede0b7ad s4 (eligible).

- **The structural-zero premise fails.** 44 of the 58 "cannot fire" cells fired, on 238 of their 348 runs. In every item, a partial cell holding at least one literal-bearing statement fires, and one holding none does not (at most one stray fire, as in Dede0b7ad s1 and s5). That looks like the scorer firing on any one literal statement, where the eligible-cell rule required all of them. On that reading, 14 of the registered 72 partial cells were eligible where many more should have been. I have not recomputed under any other rule: the rule is registered, and changing it is the coordinator's decision.
- **Clean firing:** D378d17ac's clean arm fired on 3 of 6 runs. No other item's clean arm fired.
- **Checking share by arm:** planted 0.125, clean 0.069, subset_1 0.153, subset_2 0.129, subset_3 0.155, subset_4 0.129, subset_5 0.183, subset_6 0.097. Declines are 0 everywhere.

## Cost
- **Block ledger:** $5.710 against the estimate of $7.1 and the cap of $10.7. That is $0.456 before the fix, $4.842 for the resume and $0.412 for the retry pass.
- **By follower (latest records):** Kimi $1.062 on key 1; Sol $4.408, a Bedrock upper bound with cached tokens priced at the input rate.
- **Credits after:** key 1 limit remaining 137.7490, usage_daily 12.2510; key 2 unchanged (limit remaining 271.2788, balance 81.2788). No key rotation.

## Hashes
- **Outcomes and join:** `outcomes-dose-v0.jsonl` b4004b67…; `analysis-Z-v0.json` b26ca2ae… (the join with core, verification and dose arguments).
- **Modules:** harness 8dbcaec1; runner 46968e3f; join `stage3_ft_join.py` b8a158eb (unchanged since FT); estimand `stage3_p2_z.py` 4a57c0d5.
- **Expected hashes at the resume:** manifest 5e4a1dbf, predicates 4737b1ca, documents tree 543ab3ec.
