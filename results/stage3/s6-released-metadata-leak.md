# S6: metadata-leak audit on MOLE's eight released corpora

Script `work/checks/stage3_metadata_leak_released.py` (s6-released-metadata-leak-v1); frozen classifier `work/checks/grouping_measure.py` `leak_classifier` (imported unchanged, seed 20261014, 5 folds, 1000 bootstrap draws). Data: `forgelab/mole` released parquet files under `work/upstream-data/` (untrusted, read as data). Substrate: none of Stage 3's; these are MOLE's own released worlds. $0.

## Pre-registration (written by the script before any statistic is computed)

Written 2026-10-20T05:02:54+00:00.

- **Gate (L13, verbatim):** "pass at max(AUROC, 1 − AUROC) ≤ 0.6". Applied as: pass at max(AUROC, 1 − AUROC) ≤ 0.6 (lesson L13; the frozen `leak_classifier` threshold, applied to the cross-validated point estimate). A row "exceeds the gate" iff the two-sided value is above 0.6.
- **Primary label rule:** attack = label row with outcome executed or attempted (any scenario); honest = account-days of accounts with no label row on any day. Label columns used: `account`, `date` (first ten characters), `outcome`, `scenario`; `confidence` and `judge` unused. Mapping reused from `work/checks/f1_upstream_row.py` lines 528-533 (never-labelled honest pool; labelled executed positives) and `work/checks/seed_expansion.py` `attack_rows` (executed or attempted).
- **Sensitivity label rules (reported, not gated):** `f1_exact`: f1_upstream_row exactly: attack = executed c1_release_bypass or c2_split_exfil; honest = never-labelled accounts; `any_label`: attack = any label row (also no_attempt, refused: every scenario session day); honest = never-labelled accounts; `stage2b_negatives`: primary positives; honest = every other active account-day (the Stage 2b grouping_measure convention).
- **Features:** the four of `metadata_features` where computable; the released corpora have no transcripts and no turn field, so each row names its feature set (expected: events_per_session, first_action_min, the frozen code's two-feature fallback).
- **Sanity row:** primary rule on `gpt53_single_day`, labels permuted with seed 20261020; passes iff the shuffled-label AUROC's 95 percent interval contains 0.5 and its two-sided value is at most 0.6. 20 permutations are also summarised (point AUROC only).

## Result (primary label rule)

| corpus | generator | n attack account-days | n honest account-days | features used | AUROC [95% interval] | two-sided max(AUROC, 1 − AUROC) | exceeds gate 0.6 | run time (s) |
|---|---|---:|---:|---|---|---:|---|---:|
| gpt53_single_day | GPT-5.3 | 210 | 3319 | events_per_session, first_action_min | 0.604 [0.573, 0.639] | 0.604 | yes | 1.89 |
| gpt53_multiday | GPT-5.3 | 28 | 3319 | events_per_session, first_action_min | 0.428 [0.322, 0.537] | 0.572 | no | 1.76 |
| kimi_k26_single_day | Kimi-K2.6 | 296 | 3308 | events_per_session, first_action_min | 0.652 [0.625, 0.681] | 0.652 | yes | 4.01 |
| kimi_k26_multiday | Kimi-K2.6 | 34 | 3369 | events_per_session, first_action_min | 0.528 [0.428, 0.637] | 0.528 | no | 4.09 |
| deepseek_v4_flash_single_day | DeepSeek-V4-Flash | 229 | 3324 | events_per_session, first_action_min | 0.682 [0.648, 0.717] | 0.682 | yes | 3.71 |
| deepseek_v4_flash_multiday | DeepSeek-V4-Flash | 35 | 3382 | events_per_session, first_action_min | 0.571 [0.476, 0.654] | 0.571 | no | 4.15 |
| qwen36_27b_single_day | Qwen3.6-27B | 169 | 3326 | events_per_session, first_action_min | 0.552 [0.511, 0.594] | 0.552 | no | 3.25 |
| qwen36_27b_multiday | Qwen3.6-27B | 36 | 3359 | events_per_session, first_action_min | 0.461 [0.358, 0.572] | 0.539 | no | 3.25 |
| sanity: gpt53_single_day, labels shuffled (seed 20261020) | GPT-5.3 | 210 | 3319 | events_per_session, first_action_min | 0.518 [0.474, 0.558] | 0.518 | no | 0.71 |

### Notes on the primary table

- **gpt53_single_day straddles the gate:** 0.604 [0.573, 0.639], exceeds yes under the primary rule; other label rules: `f1_exact` 0.681 (exceeds yes); `any_label` 0.623 (exceeds yes); `stage2b_negatives` 0.599 (exceeds no). The verdict flips under `stage2b_negatives`.
- **qwen36_27b_single_day is below the gate but its interval excludes 0.5** (0.552 [0.511, 0.594]): a detectable leak that the 0.6 gate tolerates.
- **Small-n rows** (gpt53_multiday, kimi_k26_multiday, deepseek_v4_flash_multiday, qwen36_27b_multiday) rest on 28 to 36 attack account-days: max(AUROC, 1 − AUROC) is biased upward at this size (it is at least 0.5 even under no signal) and the gate has little power; a "no" there does not rule a leak out.

Sanity condition (the shuffled-label AUROC's 95 percent interval contains 0.5 and its two-sided value is at most 0.6): **met**. Over 20 seeded permutations the point AUROC ranges 0.441 to 0.529 (mean 0.488).

Tag: **tested** (`work/checks/stage3_metadata_leak_released.py`, this run). Run times include reading the parquet, assembling features and all four label rules.

## Sensitivity label rules (two-sided value; AUROC [interval]; n attack / n honest; exceeds gate 0.6)

| corpus | `primary` | `primary` exceeds | `f1_exact` | `f1_exact` exceeds | `any_label` | `any_label` exceeds | `stage2b_negatives` | `stage2b_negatives` exceeds |
|---|---|---|---|---|---|---|---|---|
| gpt53_single_day | 0.604; 0.604 [0.573, 0.639]; 210 / 3319 | yes | 0.681; 0.681 [0.647, 0.713]; 111 / 3319 | yes | 0.623; 0.623 [0.596, 0.650]; 306 / 3319 | yes | 0.599; 0.599 [0.567, 0.632]; 210 / 4232 | no |
| gpt53_multiday | 0.572; 0.428 [0.322, 0.537]; 28 / 3319 | no | 0.670; 0.670 [0.535, 0.778]; 7 / 3319 | yes | 0.512; 0.488 [0.393, 0.583]; 38 / 3319 | no | 0.501; 0.501 [0.405, 0.599]; 28 / 4415 | no |
| kimi_k26_single_day | 0.652; 0.652 [0.625, 0.681]; 296 / 3308 | yes | 0.724; 0.724 [0.696, 0.753]; 181 / 3308 | yes | 0.643; 0.643 [0.614, 0.674]; 310 / 3308 | yes | 0.649; 0.649 [0.621, 0.680]; 296 / 4133 | yes |
| kimi_k26_multiday | 0.528; 0.528 [0.428, 0.637]; 34 / 3369 | no | 0.661; 0.661 [0.470, 0.854]; 6 / 3369 | yes | 0.523; 0.477 [0.382, 0.573]; 36 / 3369 | no | 0.551; 0.449 [0.358, 0.553]; 34 / 4391 | no |
| deepseek_v4_flash_single_day | 0.682; 0.682 [0.648, 0.717]; 229 / 3324 | yes | 0.769; 0.769 [0.739, 0.799]; 106 / 3324 | yes | 0.677; 0.677 [0.645, 0.710]; 257 / 3324 | yes | 0.673; 0.673 [0.638, 0.707]; 229 / 4213 | yes |
| deepseek_v4_flash_multiday | 0.571; 0.571 [0.476, 0.654]; 35 / 3382 | no | 0.617; 0.617 [0.420, 0.794]; 7 / 3382 | yes | 0.567; 0.567 [0.477, 0.648]; 36 / 3382 | no | 0.561; 0.561 [0.470, 0.648]; 35 / 4410 | no |
| qwen36_27b_single_day | 0.552; 0.552 [0.511, 0.594]; 169 / 3326 | no | 0.717; 0.717 [0.668, 0.766]; 51 / 3326 | yes | 0.556; 0.556 [0.512, 0.599]; 179 / 3326 | no | 0.545; 0.545 [0.502, 0.586]; 169 / 4279 | no |
| qwen36_27b_multiday | 0.539; 0.461 [0.358, 0.572]; 36 / 3359 | no | 0.629; 0.629 [0.498, 0.767]; 6 / 3359 | yes | 0.504; 0.504 [0.414, 0.591]; 37 / 3359 | no | 0.545; 0.455 [0.361, 0.558]; 36 / 4418 | no |

## Feature medians, primary rule (attack / honest)

| corpus | events_per_session | first_action_min (sim. minutes after midnight) | first action (hh:mm) |
|---|---|---|---|
| gpt53_single_day | 15.330 / 15.143 | 511.000 / 549.000 | 08:31 / 09:09 |
| gpt53_multiday | 15.250 / 15.286 | 516.000 / 549.000 | 08:36 / 09:09 |
| kimi_k26_single_day | 96.646 / 104.500 | 501.500 / 549.000 | 08:21 / 09:09 |
| kimi_k26_multiday | 101.625 / 109.000 | 532.500 / 548.000 | 08:52 / 09:08 |
| deepseek_v4_flash_single_day | 85.625 / 91.000 | 505.000 / 550.000 | 08:25 / 09:10 |
| deepseek_v4_flash_multiday | 90.875 / 98.571 | 530.000 / 548.000 | 08:50 / 09:08 |
| qwen36_27b_single_day | 62.000 / 61.429 | 518.033 / 549.500 | 08:38 / 09:09 |
| qwen36_27b_multiday | 61.143 / 60.875 | 528.500 / 550.000 | 08:48 / 09:10 |

## Post-hoc checks (not pre-registered; added after the first run was read)

Primary rule. Fold-assignment seeds 1 to 10 (point estimate, no bootstrap), and each feature alone at the frozen seed 20261014 (with its bootstrap interval). Tag: **tested**, this script, this run.

| corpus | two-sided over fold seeds (min to max) | fold seeds exceeding 0.6 | events_per_session alone: two-sided [AUROC interval] | first_action_min alone: two-sided [AUROC interval] |
|---|---|---:|---|---|
| gpt53_single_day | 0.597 to 0.606 | 8 of 10 | 0.526 [0.435, 0.515] | 0.602 [0.571, 0.636] |
| gpt53_multiday | 0.510 to 0.607 | 1 of 10 | 0.510 [0.386, 0.595] | 0.611 [0.283, 0.505] |
| kimi_k26_single_day | 0.647 to 0.654 | 10 of 10 | 0.601 [0.567, 0.635] | 0.624 [0.598, 0.652] |
| kimi_k26_multiday | 0.501 to 0.571 | 0 of 10 | 0.532 [0.438, 0.641] | 0.508 [0.399, 0.590] |
| deepseek_v4_flash_single_day | 0.677 to 0.687 | 10 of 10 | 0.647 [0.611, 0.682] | 0.603 [0.569, 0.634] |
| deepseek_v4_flash_multiday | 0.523 to 0.597 | 0 of 10 | 0.613 [0.517, 0.697] | 0.534 [0.365, 0.568] |
| qwen36_27b_single_day | 0.537 to 0.566 | 0 of 10 | 0.508 [0.450, 0.535] | 0.562 [0.520, 0.603] |
| qwen36_27b_multiday | 0.506 to 0.592 | 0 of 10 | 0.508 [0.396, 0.610] | 0.517 [0.376, 0.591] |

## Corpus facts

| corpus | audit rows | label rows | days | accounts | active account-days | labelled accounts | excluded account-days (primary) | positive keys not active | task_id null share | audit sha256 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| gpt53_single_day | 617,740 | 306 | 30 | 150 | 4,442 | 38 | 913 | 0 | 0.0000 | `2c40b6cc5602…` |
| gpt53_multiday | 610,556 | 38 | 30 | 150 | 4,443 | 38 | 1096 | 0 | 0.0000 | `6af1c2cedad2…` |
| kimi_k26_single_day | 4,252,096 | 310 | 30 | 150 | 4,429 | 38 | 825 | 0 | 0.0000 | `a7dc41e34ee3…` |
| kimi_k26_multiday | 4,719,298 | 36 | 30 | 150 | 4,425 | 36 | 1022 | 0 | 0.0000 | `445f630ede31…` |
| deepseek_v4_flash_single_day | 3,709,398 | 257 | 30 | 150 | 4,442 | 38 | 889 | 0 | 0.0000 | `c498ad7348b7…` |
| deepseek_v4_flash_multiday | 4,624,169 | 36 | 30 | 150 | 4,445 | 36 | 1028 | 0 | 0.0000 | `5b70056582b9…` |
| qwen36_27b_single_day | 3,091,086 | 179 | 30 | 150 | 4,448 | 38 | 953 | 0 | 0.0000 | `a13b2cce7e63…` |
| qwen36_27b_multiday | 3,013,623 | 37 | 30 | 150 | 4,454 | 37 | 1059 | 0 | 0.0000 | `bdb949b594d5…` |

## Notes

- Features missing on every released corpus: session_length, turn_cap_rate (no transcripts, no turn field in the audit schema). The fork's Stage 2b audit used all four (AUROC 0.698 [0.62, 0.78] pooled, `work/stage2/b-grouping.md`, **observed**); the rows here are therefore the two-feature version and are not directly comparable to that number.
- events_per_session counts every audit event of the account-day, failed ones included, over distinct task_id, as `metadata_features` does; first_action_min uses successful events only.
- Honest account-days are clean only if MOLE's label set is complete (never-labelled accounts may still carry unlabelled scenario sessions; noted in Stage 0 and in `f1_upstream_row.py`).
- The audit column `is_malicious` is not used (it is a label, not metadata).
