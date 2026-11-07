# Matching dry run at the 10-point band (brief 30 Part 3, note 7 item 4, note 8's first act)

Written 2026-11-07 by the Part 3 session (Sonnet 5.5, Claude Code desktop app). $0, no API call, no item. Counts and aggregates only.

**What was run.** `work/checks/stage3_elicitation_matching.py` (`5697de9d`, tests `34407f6f`, 24 by module) implements round 2's matching rule as note 7 item 4 fixes it: many-to-one within writer x document x composition band; every certified item in a stratum that holds a quiet-but-illegible item is used and the certified arm is never cut; a stratum with only one arm contributes to neither; the effective n is 2 / (1/n_c + 1/n_i) on the matched strata. The dry run draws invented strata: 2 writers, composition from a normal clipped to 0 to 100 (spread 17.3 from plan.md section 8's stratum spread; the mean, 50, is an assumption, and the retention depends on the spread, not the mean), class by count. It **does not call the simulator's world loader**, which opens the B3 candidates' item-level rows; no B3 file was opened. Seed 20261214 (unused elsewhere, by grep), 2,000 repetitions per row. Scenarios are the target (26, 12) and the reconcile table's medians for the six-round course (58, 21) and (72, 17), certified against quiet-but-illegible.

**The finding.** At 10-point bands within writer x document, the matched effective n is a fraction of the figure the sequential rule's simulation used. That simulation counted every certified item as matched, "an upper bound" in its own words (reconcile-part2-trigger-2026-11-03.md, section 3). Under the rule as written, with documents spread evenly over the arm's six documents, 15 percent of 26 certified items and 29 percent of 12 illegible items find a partner, and a draw of 58 + 21 gives a matched n_eff of about 12 against 30.8 unmatched. **At the 10-point band the stop trigger "n_eff of 26 on the matched strata" is not reached at the expected counts in any of the three strata models run (the best mean is 19.0, at 58 + 21 with three documents, p90 22.3); at 20 and 25 points it comes within reach (a mean of 24.9 and 26.2) only in the three-document model.** On these strata the course would run to its sixth round or stop by its floor rule, each extra round being Aravind's to confirm by STATUS line. This changes the forecast, not the rule: the reconcile's P(n_eff of 26) of 0.93 and 0.70 are for the all-matched figure. Writers' real documents and composition spreads will be more concentrated than the invented ones (the sensitivity runs below), which raises retention; the first certification gives the real strata.

**What this does not settle.** Whether harmonic n_eff on matched counts is the right statistic for a many-to-one stratified contrast (weights by stratum would keep more information than counts), and whether the band width should move, are the coordinator's decisions (note 7: the width moves only by dated note before writer round 1's certification). The module's width is a parameter; nothing here changes it.


## 6 documents, spread 17.3 (the base run) (`matching-dry-run-v0.json` `3c13cb17`)

| certified + illegible | width | certified retained | illegible retained | matched n_eff mean [p10, p90] | unmatched ceiling | share with no matched stratum |
|---|---|---|---|---|---|---|
| 26 + 12 | 5 | 0.08 | 0.16 | 2.0 [0.0, 4.0] | 16.4 | 0.115 |
| 26 + 12 | 10 | 0.15 | 0.29 | 3.6 [1.3, 5.5] | 16.4 | 0.015 |
| 26 + 12 | 20 | 0.26 | 0.48 | 6.1 [3.8, 8.6] | 16.4 | 0.001 |
| 26 + 12 | 25 | 0.31 | 0.54 | 7.1 [4.4, 9.6] | 16.4 | 0.000 |
| 40 + 16 | 5 | 0.10 | 0.24 | 3.9 [2.0, 6.2] | 22.9 | 0.012 |
| 40 + 16 | 10 | 0.20 | 0.41 | 7.1 [4.4, 9.9] | 22.9 | 0.000 |
| 40 + 16 | 20 | 0.33 | 0.62 | 11.2 [8.2, 14.2] | 22.9 | 0.000 |
| 40 + 16 | 25 | 0.39 | 0.69 | 12.8 [9.6, 15.8] | 22.9 | 0.000 |
| 58 + 21 | 5 | 0.13 | 0.32 | 7.2 [4.4, 10.0] | 30.8 | 0.000 |
| 58 + 21 | 10 | 0.24 | 0.52 | 12.1 [8.6, 15.8] | 30.8 | 0.000 |
| 58 + 21 | 20 | 0.41 | 0.74 | 18.7 [15.4, 21.9] | 30.8 | 0.000 |
| 58 + 21 | 25 | 0.48 | 0.80 | 20.7 [17.1, 24.0] | 30.8 | 0.000 |
| 72 + 17 | 5 | 0.11 | 0.38 | 7.1 [4.4, 9.9] | 27.5 | 0.001 |
| 72 + 17 | 10 | 0.20 | 0.59 | 11.8 [8.6, 15.1] | 27.5 | 0.000 |
| 72 + 17 | 20 | 0.35 | 0.80 | 17.5 [14.3, 20.4] | 27.5 | 0.000 |
| 72 + 17 | 25 | 0.41 | 0.84 | 19.2 [16.3, 22.0] | 27.5 | 0.000 |

## 3 documents, spread 17.3 (`matching-dry-run-v0-docs3.json` `53183ecc`)

| certified + illegible | width | certified retained | illegible retained | matched n_eff mean [p10, p90] | unmatched ceiling | share with no matched stratum |
|---|---|---|---|---|---|---|
| 26 + 12 | 5 | 0.15 | 0.29 | 3.7 [1.5, 6.0] | 16.4 | 0.022 |
| 26 + 12 | 10 | 0.28 | 0.49 | 6.4 [4.0, 8.9] | 16.4 | 0.000 |
| 26 + 12 | 20 | 0.46 | 0.71 | 9.8 [7.2, 12.3] | 16.4 | 0.000 |
| 26 + 12 | 25 | 0.53 | 0.78 | 11.0 [8.5, 13.4] | 16.4 | 0.000 |
| 40 + 16 | 5 | 0.20 | 0.41 | 7.1 [4.4, 9.9] | 22.9 | 0.000 |
| 40 + 16 | 10 | 0.35 | 0.64 | 11.7 [8.6, 14.7] | 22.9 | 0.000 |
| 40 + 16 | 20 | 0.55 | 0.83 | 16.4 [13.5, 18.9] | 22.9 | 0.000 |
| 40 + 16 | 25 | 0.63 | 0.87 | 17.7 [15.1, 20.1] | 22.9 | 0.000 |
| 58 + 21 | 5 | 0.25 | 0.53 | 12.4 [8.9, 15.8] | 30.8 | 0.000 |
| 58 + 21 | 10 | 0.43 | 0.74 | 19.0 [15.4, 22.3] | 30.8 | 0.000 |
| 58 + 21 | 20 | 0.65 | 0.90 | 24.9 [22.3, 27.3] | 30.8 | 0.000 |
| 58 + 21 | 25 | 0.72 | 0.92 | 26.2 [23.6, 28.6] | 30.8 | 0.000 |
| 72 + 17 | 5 | 0.21 | 0.60 | 12.0 [8.9, 15.1] | 27.5 | 0.000 |
| 72 + 17 | 10 | 0.36 | 0.81 | 17.8 [14.9, 20.8] | 27.5 | 0.000 |
| 72 + 17 | 20 | 0.58 | 0.93 | 22.7 [20.3, 24.8] | 27.5 | 0.000 |
| 72 + 17 | 25 | 0.65 | 0.94 | 23.6 [21.3, 25.6] | 27.5 | 0.000 |

## 6 documents, spread 10 (`matching-dry-run-v0-sd10.json` `319cfeee`)

| certified + illegible | width | certified retained | illegible retained | matched n_eff mean [p10, p90] | unmatched ceiling | share with no matched stratum |
|---|---|---|---|---|---|---|
| 26 + 12 | 5 | 0.13 | 0.26 | 3.2 [1.0, 5.5] | 16.4 | 0.025 |
| 26 + 12 | 10 | 0.24 | 0.44 | 5.6 [3.0, 8.0] | 16.4 | 0.001 |
| 26 + 12 | 20 | 0.40 | 0.63 | 8.6 [5.9, 11.2] | 16.4 | 0.000 |
| 26 + 12 | 25 | 0.40 | 0.66 | 8.9 [6.2, 11.3] | 16.4 | 0.000 |
| 40 + 16 | 5 | 0.17 | 0.36 | 6.2 [3.4, 8.9] | 22.9 | 0.001 |
| 40 + 16 | 10 | 0.30 | 0.58 | 10.4 [7.5, 13.3] | 22.9 | 0.000 |
| 40 + 16 | 20 | 0.48 | 0.75 | 14.6 [11.5, 17.4] | 22.9 | 0.000 |
| 40 + 16 | 25 | 0.49 | 0.81 | 15.5 [12.6, 18.2] | 22.9 | 0.000 |
| 58 + 21 | 5 | 0.22 | 0.48 | 11.1 [7.9, 14.4] | 30.8 | 0.000 |
| 58 + 21 | 10 | 0.37 | 0.69 | 17.2 [13.5, 20.6] | 30.8 | 0.000 |
| 58 + 21 | 20 | 0.57 | 0.83 | 22.7 [19.5, 25.5] | 30.8 | 0.000 |
| 58 + 21 | 25 | 0.59 | 0.91 | 24.4 [21.6, 26.9] | 30.8 | 0.000 |
| 72 + 17 | 5 | 0.18 | 0.55 | 10.7 [7.5, 13.8] | 27.5 | 0.000 |
| 72 + 17 | 10 | 0.32 | 0.76 | 16.3 [13.0, 19.5] | 27.5 | 0.000 |
| 72 + 17 | 20 | 0.50 | 0.87 | 20.8 [17.9, 23.5] | 27.5 | 0.000 |
| 72 + 17 | 25 | 0.51 | 0.94 | 22.2 [19.8, 24.2] | 27.5 | 0.000 |

## Reproduce

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_matching.py dry-run --out FILE            # base
work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_matching.py dry-run --out FILE --documents 3
work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_matching.py dry-run --out FILE --sd 10
```
