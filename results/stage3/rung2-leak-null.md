# Rung 2: honest-null leak classifiers on the prefix (metadata and content)

Pass condition pre-registered 2026-10-20T04:53:31Z (this file's first version, written before any statistic was computed); results computed 2026-10-20T04:57:33+00:00. Substrate: (ii) in-process only (prefix_v1: org, plane, model_registry, eval_server, secrets_store).

## Pass condition (verbatim)
- Design section 4, rung 2 pass: "honest-null AUROC inside [0.4, 0.6]"; kill: "null classifier off".
- Brief 07 S4.3: "Pass if the two-sided value is inside [0.4, 0.6] for the representative seed and the 20-seed mean is inside it."

## Operationalisation (fixed before running)
For each classifier (metadata, content) at each positive share (0.2, 0.5): random labels drawn with seeds 20261020..20261039 (20 seeds); representative seed = 20261020 (declared before running). Two-sided value = max(AUROC, 1 - AUROC) from grouping_measure.leak_classifier (5-fold cross-validated AUROC). Pass for a classifier-share cell iff (a) the representative seed's two-sided value <= 0.6 (equivalently AUROC in [0.4, 0.6]) AND (b) the mean over the 20 seeds of the two-sided value <= 0.6. The mean AUROC (one-sided) is also reported and must lie in [0.4, 0.6]. Rung 2 leak line passes iff all four cells pass; otherwise kill 'null classifier off'.

## Verdict: **KILL (null classifier off)**

Failing primary cells: metadata@0.2, content@0.2. Sensitivity (complete days) failing cells: metadata@0.2.

## Results (tested, `work/checks/stage3_leak_null.py`)

### Primary: every prefix day as grouping_measure loads it

118 account-days (2026-04-06, 2026-04-07, 2026-04-08: 48, 49, 21), 50 accounts; account-days without transcript sessions: 0.

| classifier | share | n1/n0 | rep. seed AUROC [95% CI] | rep. two-sided | 20-seed AUROC mean (min, max) | 20-seed two-sided mean (max) | seeds with two-sided <= 0.6 | pass |
|---|---|---|---|---|---|---|---|---|
| metadata | 0.2 | 24/94 | 0.469 [0.342, 0.604] | 0.531 | 0.436 (0.280, 0.612) | 0.603 (0.720) | 0.50 | FAIL |
| content | 0.2 | 24/94 | 0.656 [0.516, 0.782] | 0.656 | 0.503 (0.381, 0.656) | 0.563 (0.656) | 0.75 | FAIL |
| metadata | 0.5 | 59/59 | 0.469 [0.365, 0.579] | 0.531 | 0.475 (0.332, 0.606) | 0.558 (0.668) | 0.75 | PASS |
| content | 0.5 | 59/59 | 0.498 [0.403, 0.602] | 0.502 | 0.479 (0.358, 0.616) | 0.559 (0.642) | 0.70 | PASS |

Post hoc diagnostics (added after the verdict; they do not change it): an ideal null scorer (uniform random scores, no fit, no cross-validation) on the same labels, and the classifier's spread against it.

| classifier | share | Hanley-McNeil SE | ideal-null two-sided mean | ideal-null share <= 0.6 | ideal-null two-sided q95 | classifier SD / ideal SD | classifier mean - 0.5 (in SE of mean) |
|---|---|---|---|---|---|---|---|
| metadata | 0.2 | 0.066 | 0.553 | 0.87 | 0.628 | 1.56 | -2.8 |
| content | 0.2 | 0.066 | 0.553 | 0.87 | 0.628 | 1.23 | +0.2 |
| metadata | 0.5 | 0.053 | 0.543 | 0.95 | 0.602 | 1.31 | -1.6 |
| content | 0.5 | 0.053 | 0.543 | 0.95 | 0.602 | 1.38 | -1.3 |

### Sensitivity: the two complete days

97 account-days (2026-04-06, 2026-04-07: 48, 49), 50 accounts; account-days without transcript sessions: 0.

| classifier | share | n1/n0 | rep. seed AUROC [95% CI] | rep. two-sided | 20-seed AUROC mean (min, max) | 20-seed two-sided mean (max) | seeds with two-sided <= 0.6 | pass |
|---|---|---|---|---|---|---|---|---|
| metadata | 0.2 | 19/78 | 0.638 [0.497, 0.763] | 0.638 | 0.482 (0.227, 0.638) | 0.585 (0.773) | 0.50 | FAIL |
| content | 0.2 | 19/78 | 0.530 [0.404, 0.657] | 0.530 | 0.511 (0.367, 0.708) | 0.579 (0.708) | 0.65 | PASS |
| metadata | 0.5 | 48/49 | 0.485 [0.369, 0.598] | 0.515 | 0.467 (0.348, 0.568) | 0.558 (0.652) | 0.80 | PASS |
| content | 0.5 | 48/49 | 0.557 [0.432, 0.685] | 0.557 | 0.498 (0.380, 0.686) | 0.562 (0.686) | 0.85 | PASS |

Post hoc diagnostics (added after the verdict; they do not change it): an ideal null scorer (uniform random scores, no fit, no cross-validation) on the same labels, and the classifier's spread against it.

| classifier | share | Hanley-McNeil SE | ideal-null two-sided mean | ideal-null share <= 0.6 | ideal-null two-sided q95 | classifier SD / ideal SD | classifier mean - 0.5 (in SE of mean) |
|---|---|---|---|---|---|---|---|
| metadata | 0.2 | 0.074 | 0.560 | 0.83 | 0.639 | 1.50 | -0.7 |
| content | 0.2 | 0.074 | 0.560 | 0.83 | 0.639 | 1.30 | +0.5 |
| metadata | 0.5 | 0.059 | 0.546 | 0.92 | 0.612 | 1.21 | -2.1 |
| content | 0.5 | 0.059 | 0.546 | 0.92 | 0.612 | 1.37 | -0.1 |

## Features
- Metadata: session_length, turn_cap_rate, events_per_session, first_action_min (`grouping_measure.metadata_features`, max_turns 50 from argument).
- Content: assistant turns only; word unigrams + within-turn bigrams ([a-z0-9_]+, lowercased) and tool-call names (not arguments), CRC32-hashed into 4096 columns, sublinear TF x smoothed IDF over the classified rows (label-free), rows L2-normalised; plus style features mean_turn_chars, tool_call_turn_share, vocab_per_1k_tokens; nonzero hashed columns 4096 of 4096.
- Classifier: `grouping_measure.leak_classifier` unchanged (fold-wise standardisation, L2 logistic regression C = 1, stratified 5-fold, 1,000-draw bootstrap 95% interval; fold and bootstrap seed = label seed).

## Inputs and command
- corpus `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/prefix_v1.jsonl` sha256 c39bf9f86d89b4c9e79ef6049499c7e9986f67e4c5bc38ffd0e2c1a84820dad4
- transcripts `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/prefix_v1.transcripts.jsonl` sha256 cc9e0de51684da07377376241737f24397402c596740a459096779573d87dcf4
- script sha256 8a6a30300512d65b5bc61af20b4a1bae512907098eebb0650bd82ea62489ca39; content module sha256 95d32c67c75757278f1984ccf74c7f0c51add77c90aeb0c7b0868f6de9f794bd; grouping_measure sha256 59f9b5d46ad1936abddfff1079d44de62b91fce37a9d98dfc20f2192a9e1fe37
- seeds 20261020..20261039; representative 20261020

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_leak_null.py --out-json /Users/aravind/KruxAI/tais-project-selection/work/stage3/rung2-leak-null.json --out-md /Users/aravind/KruxAI/tais-project-selection/work/stage3/rung2-leak-null.md
```


## POST-HOC analyses (added after the pre-registered verdict; none of them changes it)

Note on intervals: The representative-seed 95% intervals in the pre-registered tables are bootstraps over account-days of that seed's out-of-fold predictions: they describe the sampling uncertainty of one AUROC, not a null test (the null distribution is the permutation band below).

### POST-HOC: permutation band, labels per account-day (tested, `work/checks/stage3_leak_null.py --permutation-band`)

Random labels, 200 seeds (20261100..20261299), `grouping_measure.leak_classifier` unchanged, fold seed = label seed (the pre-registered coupling). Pilot rows draw the accounts per seed from the 20 prefix accounts with an account-day on every prefix day (2026-04-06, 2026-04-07, 2026-04-08; the third is partial). Calibrated gate = 95th percentile of the two-sided value under the null; false-kill rate = share of null seeds with two-sided value above the fixed 0.6 gate.

| unit | share | n1/n0 | classifier | two-sided p2.5 | p97.5 | calibrated gate (p95) | false-kill rate of 0.6 gate | AUROC mean (SE units from 0.5) | AUROC min, max | share of seeds AUROC > 0.6 |
|---|---|---|---|---|---|---|---|---|---|---|
| prefix (all account-days) | 0.2 | 24/94 | metadata | 0.508 | 0.665 | 0.654 | 0.31 | 0.489 (-1.7) | 0.315, 0.656 | 0.135 |
| prefix (all account-days) | 0.2 | 24/94 | content | 0.502 | 0.661 | 0.655 | 0.25 | 0.501 (+0.2) | 0.271, 0.738 | 0.145 |
| pilot draw: 9 accounts x 3 days | 0.2 | 5/22 | metadata | 0.509 | 0.891 | 0.874 | 0.61 | 0.468 (-2.3) | 0.055, 0.964 | 0.240 |
| pilot draw: 9 accounts x 3 days | 0.2 | 5/22 | content | 0.509 | 0.873 | 0.837 | 0.56 | 0.483 (-1.4) | 0.009, 0.918 | 0.260 |
| pilot draw: 12 accounts x 3 days | 0.2 | 7/29 | metadata | 0.507 | 0.848 | 0.823 | 0.56 | 0.476 (-2.1) | 0.079, 0.901 | 0.235 |
| pilot draw: 12 accounts x 3 days | 0.2 | 7/29 | content | 0.507 | 0.852 | 0.804 | 0.55 | 0.459 (-3.9) | 0.084, 0.837 | 0.180 |
| prefix (all account-days) | 0.5 | 59/59 | metadata | 0.504 | 0.660 | 0.643 | 0.19 | 0.484 (-3.1) | 0.254, 0.643 | 0.040 |
| prefix (all account-days) | 0.5 | 59/59 | content | 0.505 | 0.648 | 0.628 | 0.12 | 0.497 (-0.6) | 0.327, 0.675 | 0.040 |
| pilot draw: 9 accounts x 3 days | 0.5 | 14/13 | metadata | 0.505 | 0.830 | 0.797 | 0.56 | 0.465 (-3.2) | 0.060, 0.769 | 0.215 |
| pilot draw: 9 accounts x 3 days | 0.5 | 14/13 | content | 0.505 | 0.814 | 0.781 | 0.47 | 0.473 (-2.7) | 0.077, 0.791 | 0.170 |
| pilot draw: 12 accounts x 3 days | 0.5 | 18/18 | metadata | 0.506 | 0.778 | 0.765 | 0.45 | 0.471 (-3.1) | 0.127, 0.787 | 0.160 |
| pilot draw: 12 accounts x 3 days | 0.5 | 18/18 | content | 0.503 | 0.753 | 0.738 | 0.39 | 0.478 (-2.6) | 0.207, 0.802 | 0.140 |

Metadata bias: The metadata classifier's mean AUROC at share 0.2 sits 2.8 standard errors below 0.5 over the 20 pre-registered seeds (0.436) and 1.7 standard errors below 0.5 over the 200 band seeds (0.489), the known negative bias of cross-validated AUROC under random labels: in each of the 5 stratified folds the held-out positives are removed from the training positives, so the fitted positive direction is estimated from the other positives only and points away from the held-out ones (and the fold-specific intercepts are pooled into one ranking), which pushes held-out positives below held-out negatives on average; the effect grows as positives per fold shrink (about 5 per fold at 24 positives).

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_leak_null.py --permutation-band --out-json /Users/aravind/KruxAI/tais-project-selection/work/stage3/rung2-leak-null.json --out-md /Users/aravind/KruxAI/tais-project-selection/work/stage3/rung2-leak-null.md
```

### POST-HOC: permutation band, labels per account (clustered), fold seed = label seed + 777777 (tested, `work/checks/stage3_leak_null.py --permutation-band`)

200 seeds (20261100..20261299), 50 accounts, cross-validation not grouped by account (the Stage 2b protocol).

| unit | share | n1/n0 | classifier | two-sided p2.5 | p97.5 | calibrated gate (p95) | false-kill rate of 0.6 gate | AUROC mean (SE units from 0.5) | AUROC min, max | share of seeds AUROC > 0.6 |
|---|---|---|---|---|---|---|---|---|---|---|
| prefix, labels per account (10 of 50 accounts, all their days) | 0.2 | 19-28/n=118 | metadata | 0.501 | 0.706 | 0.690 | 0.33 | 0.525 (+3.8) | 0.248, 0.850 | 0.225 |
| prefix, labels per account (10 of 50 accounts, all their days) | 0.2 | 19-28/n=118 | content | 0.510 | 0.804 | 0.782 | 0.62 | 0.634 (+19.0) | 0.407, 0.852 | 0.625 |
| prefix, labels per account (25 of 50 accounts, all their days) | 0.5 | 53-65/n=118 | metadata | 0.504 | 0.652 | 0.645 | 0.22 | 0.514 (+2.6) | 0.318, 0.743 | 0.140 |
| prefix, labels per account (25 of 50 accounts, all their days) | 0.5 | 53-65/n=118 | content | 0.508 | 0.734 | 0.721 | 0.65 | 0.614 (+22.0) | 0.391, 0.815 | 0.640 |

Caveat: with labels per account and ungrouped folds, the content classifier is biased upward by account identity (an account's other days are in training), so this band is the null for account-level plants under the Stage 2b protocol, not evidence of a leak.

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_leak_null.py --permutation-band --cluster-by-account --fold-seed-offset 777777 --out-json /Users/aravind/KruxAI/tais-project-selection/work/stage3/rung2-leak-null.json --out-md /Users/aravind/KruxAI/tais-project-selection/work/stage3/rung2-leak-null.md
```

### POST-HOC: fold-seed sensitivity, fold seed = label seed + 777777 (tested, `work/checks/stage3_leak_null.py --fold-seed-offset 777777`)

Same labels, units, features and pre-registered rule; only the fold and bootstrap seed differ. In the pre-registered run the label draw and the fold permutation both start from default_rng(seed), so they are coupled.

Unit: every prefix day.

| classifier | share | rep. seed AUROC [95% CI] | rep. two-sided | 20-seed AUROC mean (min, max) | 20-seed two-sided mean | pass under the pre-registered rule |
|---|---|---|---|---|---|---|
| metadata | 0.2 | 0.449 [0.319, 0.600] | 0.551 | 0.456 (0.281, 0.591) | 0.591 | PASS |
| content | 0.2 | 0.547 [0.422, 0.688] | 0.547 | 0.487 (0.292, 0.637) | 0.583 | PASS |
| metadata | 0.5 | 0.486 [0.386, 0.594] | 0.514 | 0.492 (0.415, 0.638) | 0.549 | PASS |
| content | 0.5 | 0.515 [0.402, 0.619] | 0.515 | 0.494 (0.414, 0.601) | 0.548 | PASS |

Unit: the two complete days.

| classifier | share | rep. seed AUROC [95% CI] | rep. two-sided | 20-seed AUROC mean (min, max) | 20-seed two-sided mean | pass under the pre-registered rule |
|---|---|---|---|---|---|---|
| metadata | 0.2 | 0.641 [0.501, 0.774] | 0.641 | 0.488 (0.376, 0.641) | 0.570 | FAIL |
| content | 0.2 | 0.427 [0.286, 0.570] | 0.573 | 0.502 (0.368, 0.676) | 0.579 | PASS |
| metadata | 0.5 | 0.559 [0.437, 0.676] | 0.559 | 0.465 (0.290, 0.573) | 0.569 | PASS |
| content | 0.5 | 0.559 [0.441, 0.671] | 0.559 | 0.508 (0.388, 0.673) | 0.558 | PASS |

Under an arbitrary change of the fold seed (label seed + 777777, labels unchanged) the same pre-registered rule passes all four primary cells, so the pre-registered KILL sits at the noise floor of the gate rather than signalling a broken classifier.

Residue on the two-complete-days unit at this offset: metadata@0.2 (representative seed 0.641, 20-seed mean 0.488, mean two-sided 0.570) still fails the pre-registered rule.

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_leak_null.py --fold-seed-offset 777777 --out-json /Users/aravind/KruxAI/tais-project-selection/work/stage3/rung2-leak-null.json --out-md /Users/aravind/KruxAI/tais-project-selection/work/stage3/rung2-leak-null.md
```

### POST-HOC: implications for rungs 3 and 4 (inferred from the tables above)

- Future runs: draw folds and bootstrap from seed + a fixed offset (for example `--fold-seed-offset 777777`), never from the label seed itself, so the label draw and the fold permutation are independent streams.
- At pilot size (n = 27 to 36 account-days) the fixed 0.6 gate kills a clean world 0.39 to 0.61 of the time under per-row labels; a calibrated 5 percent gate there is a two-sided value of 0.738 to 0.874, so only a strong leak is detectable at that size.
- With labels per account (whole accounts positive across days, as a pilot plants them) and cross-validation not grouped by account, the content classifier's null mean AUROC is 0.634 (metadata 0.525): the content classifier is biased upward by account identity, because the same account's other days sit in the training folds. Any calibrated gate for rungs 3 and 4 must therefore be drawn either (a) with account-level labels under the same ungrouped protocol, or (b) with grouped-by-account cross-validation (all of an account's days in one fold), which removes the identity shortcut; the controller chooses.
