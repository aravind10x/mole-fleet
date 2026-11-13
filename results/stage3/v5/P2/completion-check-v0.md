# Completion scorer against readers' labels (blue side; counts only)

The 60 runs: 40 clean-arm core runs and 20 benign-arm verification runs; no planted-arm run. Readers label `completed`, `not_completed` or `unclear` under `P2/completion-reader-rule.md`; the scorer is `stage3_p2_completion.completed` with its defaults. Agreement is over the items not labelled unclear.

**All:** 60 items, 6 unclear, 54 decided, 54 agree (agreement 1.0); reader completed but scorer false: 0; reader not_completed but scorer true: 0.

## 3 x 2 table: reader class against scorer result (all)

| reader class | scorer true | scorer false |
|---|---|---|
| completed | 52 | 0 |
| not_completed | 0 | 2 |
| unclear | 6 | 0 |

## By arm

| group | completed (scorer true / false) | not_completed (scorer true / false) | unclear (scorer true / false) | decided | agree | agreement | reader completed, scorer false | reader not_completed, scorer true |
|---|---|---|---|---|---|---|---|---|
| benign | 20 / 0 | 0 / 0 | 0 / 0 | 20 | 20 | 1.0 | 0 | 0 |
| clean | 32 / 0 | 0 / 2 | 6 / 0 | 34 | 34 | 1.0 | 0 | 0 |

## By follower

| group | completed (scorer true / false) | not_completed (scorer true / false) | unclear (scorer true / false) | decided | agree | agreement | reader completed, scorer false | reader not_completed, scorer true |
|---|---|---|---|---|---|---|---|---|
| kimi | 24 / 0 | 0 / 2 | 4 / 0 | 26 | 26 | 1.0 | 0 | 0 |
| sol | 28 / 0 | 0 / 0 | 2 / 0 | 28 | 28 | 1.0 | 0 | 0 |

## By arm and follower

| group | completed (scorer true / false) | not_completed (scorer true / false) | unclear (scorer true / false) | decided | agree | agreement | reader completed, scorer false | reader not_completed, scorer true |
|---|---|---|---|---|---|---|---|---|
| benign|kimi | 10 / 0 | 0 / 0 | 0 / 0 | 10 | 10 | 1.0 | 0 | 0 |
| benign|sol | 10 / 0 | 0 / 0 | 0 / 0 | 10 | 10 | 1.0 | 0 | 0 |
| clean|kimi | 14 / 0 | 0 / 2 | 4 / 0 | 16 | 16 | 1.0 | 0 | 0 |
| clean|sol | 18 / 0 | 0 / 0 | 2 / 0 | 18 | 18 | 1.0 | 0 | 0 |
