# Part J lift record (v0)

Brief 34, $0, no request sent. Script `stage3_b3_partj_lift.py` `aed28cb41ba892fb1d33f9233b4ea9c795054b7e40dbbdf348bf543d1c42288b`. Numbers and fixed labels only: no ids, no item text, no rater `reason`.

## Agreement with the review notes

All six review-note values reproduce at the precision the notes printed (lift to two decimals, Spearman to three).

| value | review note | recomputed | difference | match at printed precision |
|---|---|---|---|---|
| lift_pass1_overall_mean | 13.46 | 13.461 | 0.0007 | yes |
| lift_pass1_sonnet55_mean | 16.17 | 16.167 | -0.0033 | yes |
| lift_pass1_glm53_mean | 10.29 | 10.293 | 0.0027 | yes |
| spearman_pass1_composition_vs_max_statement | 0.628 | 0.6279 | -0.00008 | yes |
| spearman_pass1_composition_vs_mean_statement | 0.456 | 0.4564 | 0.00041 | yes |
| spearman_pass1_composition_vs_spread | 0.376 | 0.3763 | 0.00025 | yes |

Tie handling: average ranks, as scipy.stats.spearmanr.

## Counts (reproduce J2 before anything else is reported)

- Candidate triples: 89 (Sonnet 5.5 48, GLM 5.3 41). Controls, by count only: 22 (Sonnet 5.5 12, GLM 5.3 10).
- Certified, recomputed from the bars: pass 1 1, pass 2 0, both passes 0, pass 1 only 1. J2 agrees: True.

## Bars used (`certification-bars.json`)

| bar | value |
|---|---|
| composition_bar | 75 |
| statement_bar | 60 |
| spread_bar | 10 |
| composition_floor | 75 |
| composition_margin | 5 |
| control_statement_bar | 60 |
| control_composition_bar | 60 |
| honest_max_pass1 | 70 |

## Minimum lift needed

**16** = (composition_bar + 1) - statement_bar = (75 + 1) - 60. J1: a candidate's composition score must be above the composition bar and scores are integers; with the loudest statement at the statement bar a triple needs composition_bar + 1. A quieter loudest line needs more. The count of triples reaching it is necessary, not sufficient: the statement and spread bars also apply.

## Lift = composition - loudest statement

| pass | group | n | mean | sd | median | q1 | q3 | reaching min lift (16) |
|---|---|---|---|---|---|---|---|---|
| pass 1 (primary) | all | 89 | 13.46 | 13.71 | 13.00 | 5.00 | 20.00 | 33 |
| pass 1 (primary) | Sonnet 5.5 | 48 | 16.17 | 14.65 | 15.00 | 7.25 | 23.50 | 23 |
| pass 1 (primary) | GLM 5.3 | 41 | 10.29 | 11.93 | 10.00 | 5.00 | 15.00 | 10 |
| pass 2 (secondary) | all | 89 | 9.52 | 13.63 | 10.00 | 0.00 | 20.00 | 26 |
| pass 2 (secondary) | Sonnet 5.5 | 48 | 12.88 | 13.90 | 12.00 | 5.00 | 20.00 | 19 |
| pass 2 (secondary) | GLM 5.3 | 41 | 5.59 | 12.34 | 5.00 | -3.00 | 12.00 | 7 |
| mean of the two passes (secondary) | all | 89 | 11.49 | 12.68 | 11.50 | 4.00 | 18.50 | - |
| mean of the two passes (secondary) | Sonnet 5.5 | 48 | 14.52 | 12.92 | 14.00 | 6.12 | 22.50 | - |
| mean of the two passes (secondary) | GLM 5.3 | 41 | 7.94 | 11.57 | 10.00 | 0.00 | 15.00 | - |

No interval was computed for the lift summaries.

## Spearman, over the candidate triples

| pass | pair | rho | 95% bootstrap interval | n | resamples | seed | degenerate resamples |
|---|---|---|---|---|---|---|---|
| pass1 | composition_vs_max_statement | 0.628 | [0.469, 0.756] | 89 | 2000 | 20261102 | 0 |
| pass1 | composition_vs_mean_statement | 0.456 | [0.257, 0.623] | 89 | 2000 | 20261102 | 0 |
| pass1 | composition_vs_spread | 0.376 | [0.188, 0.542] | 89 | 2000 | 20261102 | 0 |
| pass2 | composition_vs_max_statement | 0.663 | [0.509, 0.787] | 89 | 2000 | 20261102 | 0 |
| pass2 | composition_vs_mean_statement | 0.475 | [0.286, 0.639] | 89 | 2000 | 20261102 | 0 |
| pass2 | composition_vs_spread | 0.469 | [0.284, 0.634] | 89 | 2000 | 20261102 | 0 |

## Inputs (sha256)

| file | sha256 |
|---|---|
| key-b3.json | `04b1ca30582eafd7b7e58515b23a4f1df3932e43ede7daf2080f9a3547237335` |
| ratings-b3-statements-p1.jsonl | `8aca72f45d19b41b2df523fc932388f19d13f75e62efc6308f2c7969e8626d38` |
| ratings-b3-statements-p2.jsonl | `aa2421e917f4a178879eed258c3809b3c6782b6405fdc1e623755eb02f6694e6` |
| ratings-b3-triples-p1.jsonl | `7d8f4dfb2122b66707360e70584cd6f9c2bad4acbcaef86eecefd15fa501ede8` |
| ratings-b3-triples-p2.jsonl | `f70e55278e11b6c20417f998bebcf1d5c1b2862a4daf9dbca18b8f3589d1ee00` |
| certification-bars.json | `815de53887992023407b832a8ced5d884b56f6ddc064063b9ae5ea4f08dbcc6b` |
| certification-b3.json | `bec5b02fd657ba046a2fb0e77486949e802c504d7c3e0b8c8f2b01c0d193c485` |
| certification-b3.md | `f7f112303abc20a845a69bc618c5a1977dcca799244521a375581c28897b31a7` |

`key-b3.json` is the review run's file (04b1ca30): True. The key and the pass-1 triple file match the hashes recorded in `certification-bars.json`.

## Method

- candidates: triples whose key source label marks a candidate set; the writer split follows that label
- lift: composition - max(three statement scores), per triple and pass
- mean_of_passes: per triple, the mean of its two per-pass lifts
- sd: sample standard deviation (n - 1)
- quartiles: linear interpolation (numpy default)
- spearman: average ranks for ties; percentile bootstrap over triples, 95%, one generator per row seeded with the seed, so every row uses the same resampled triples
- free_text: each rating record's reason field is dropped at load; no id and no item text is written
