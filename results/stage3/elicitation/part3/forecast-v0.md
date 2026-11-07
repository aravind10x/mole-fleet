# Forecast of the six-round course with round 1's yields folded in (brief 30 dated note 9 item 2)

Written 2026-11-07 by the Part 3 session (Sonnet 5.5). $0, no model call, no item, no B3 file. Module `stage3_elicitation_forecast.py` 0817b6b2, seed 20261216, 40000 runs per all-matched cell and 4000 per matched cell. Counts and aggregates only.

## What is forecast

One writer (GPT-6.1-sol), writer rounds 2 to 6 at the cap of 96 items written, round 1 as observed (24 written, 20 valid, 2 certified, 0 quiet-but-illegible). The course is note 8's: rounds continue while the matched effective n is below 26 and fewer than six rounds have run; the floor rule stops it after rounds 3 to 5 when the projected effective n at round 6 is below 12 (the cumulative counts scaled by the planned items, all certified items counted as matched, the reconcile's definition). **P(stop by success)** is the share of simulated courses that reach an effective n of 26 at some round up to 6 before the floor rule stops them. Matching is note 7's rule at the 10-point band within writer x document (`stage3_elicitation_matching.py`).

**Yield scenarios** (Beta posteriors, per valid item written; the valid share per round from round 1's 20 of 24): `round1_only` is Jeffreys on round 1's counts (certified 2 of 20, illegible 0 of 20); `e2_prior_plus_round1` adds round 1 to E2's rates for the Kimi pinned + Sonnet 5.5 pair (3 and 2 of 37 per rater-quiet candidate, scaled to per valid item by round 1's quiet share of 13 of 20, weight 37 items; the reconcile's flat 0.8 would double-count validity beside the valid share); `e2_prior_only` leaves round 1 out (one writer at E2's rates, round 1 sampled) to show how much of the fall from course A's figure is the lost second writer and how much is round 1's evidence. **Drift:** `none`, or the illegible rate falling linearly to half by round 4 (my reading of the reconcile's 'halving by round 4'). **Strata** of future items: `invented` (6 documents uniform, composition a clipped normal of spread 17.3 from plan section 8) or `empirical` (resampled from round 1's own 20 observed (document, composition) pairs). **Not modelled:** any change of yield with feedback (round 1 had none; round 2 is the feedback round), any association of class with document or composition, any change of the valid share.

## The replication check: this code on course A's own model

| | course A as reconciled (two writers, all certified items matched) | this code, same model |
|---|---|---|
| P(n_eff of 26), rates hold | 0.93 | 0.93 |
| P(n_eff of 26), illegible rate halves | 0.70 | 0.77 |
| mean extra rounds beyond 3, rates hold / halve | 1.07 / 1.73 | 1.06 / 1.65 |
| median certified and illegible at the stop, rates hold / halve | 58 and 21 / 72 and 17 | 58 and 22 / 70 and 18 |

The rates-hold case reproduces the reconcile (0.93, 1.07, 58 and 21); the halving case is milder here (0.77 against 0.70) because the reconcile's drift schedule is not written down and this is my reading of it. A step to half at round 2 gives 0.67 and at round 4 gives 0.83, so the reconcile's schedule lies between the linear reading and the round-2 step. The new forecast uses the linear reading throughout.

## The forecast

### round1_only

| drift | statistic | P(stop by success) by round 6 | P(floor rule stops it) | P(reaches round 6 without either) | certified after round 3 | after round 6 | illegible after round 3 | after round 6 | effective n after round 6 |
|---|---|---|---|---|---|---|---|---|---|
| none | every certified item matched (course A's) | 0.14 | 0.68 | 0.18 | 20.8 [8, 37] | 48.9 [17, 87] | 3.8 [0, 11] | 9.4 [0, 26] | 12.0 |
| none | matched, invented strata | 0.06 | 0.68 | 0.27 | 20.7 [7, 36] | 48.8 [17, 88] | 3.8 [0, 11] | 9.6 [0, 27] | 6.8 |
| none | matched, round 1's strata | 0.12 | 0.67 | 0.20 | 20.9 [7, 37] | 49.2 [17, 88] | 3.8 [0, 11] | 9.6 [0, 27] | 10.6 |
| halving | every certified item matched (course A's) | 0.07 | 0.76 | 0.17 | 20.8 [8, 37] | 48.9 [17, 88] | 2.8 [0, 8] | 5.6 [0, 16] | 8.2 |
| halving | matched, invented strata | 0.02 | 0.76 | 0.22 | 20.8 [8, 37] | 49.1 [18, 87] | 2.8 [0, 8] | 5.6 [0, 16] | 4.1 |
| halving | matched, round 1's strata | 0.06 | 0.76 | 0.18 | 20.7 [8, 37] | 48.8 [17, 87] | 2.9 [0, 8] | 5.7 [0, 16] | 6.8 |

### e2_prior_only

| drift | statistic | P(stop by success) by round 6 | P(floor rule stops it) | P(reaches round 6 without either) | certified after round 3 | after round 6 | illegible after round 3 | after round 6 | effective n after round 6 |
|---|---|---|---|---|---|---|---|---|---|
| none | every certified item matched (course A's) | 0.10 | 0.61 | 0.29 | 9.3 [2, 19] | 21.7 [5, 43] | 6.2 [0, 14] | 14.5 [2, 32] | 13.1 |
| none | matched, invented strata | 0.02 | 0.62 | 0.37 | 9.2 [2, 18] | 21.6 [5, 42] | 6.2 [0, 14] | 14.5 [2, 31] | 5.6 |
| none | matched, round 1's strata | 0.07 | 0.62 | 0.31 | 9.4 [2, 19] | 21.9 [5, 44] | 6.3 [0, 14] | 14.7 [2, 32] | 10.1 |
| halving | every certified item matched (course A's) | 0.04 | 0.71 | 0.25 | 9.3 [2, 19] | 21.8 [5, 43] | 4.8 [0, 11] | 9.0 [1, 20] | 9.8 |
| halving | matched, invented strata | 0.00 | 0.72 | 0.28 | 9.3 [2, 19] | 21.7 [5, 43] | 4.7 [0, 11] | 8.8 [1, 19] | 3.6 |
| halving | matched, round 1's strata | 0.02 | 0.71 | 0.27 | 9.3 [2, 19] | 21.7 [5, 43] | 4.8 [0, 11] | 8.9 [1, 20] | 7.0 |

### e2_prior_plus_round1

| drift | statistic | P(stop by success) by round 6 | P(floor rule stops it) | P(reaches round 6 without either) | certified after round 3 | after round 6 | illegible after round 3 | after round 6 | effective n after round 6 |
|---|---|---|---|---|---|---|---|---|---|
| none | every certified item matched (course A's) | 0.06 | 0.67 | 0.27 | 12.9 [6, 21] | 29.3 [13, 49] | 3.6 [0, 8] | 9.0 [1, 20] | 11.5 |
| none | matched, invented strata | 0.00 | 0.67 | 0.33 | 13.0 [6, 21] | 29.4 [13, 49] | 3.6 [0, 8] | 8.9 [1, 20] | 4.5 |
| none | matched, round 1's strata | 0.04 | 0.66 | 0.30 | 12.9 [6, 21] | 29.4 [13, 48] | 3.6 [0, 8] | 9.0 [1, 20] | 8.8 |
| halving | every certified item matched (course A's) | 0.01 | 0.80 | 0.19 | 13.0 [6, 21] | 29.4 [13, 49] | 2.7 [0, 7] | 5.4 [0, 12] | 7.8 |
| halving | matched, invented strata | 0.00 | 0.79 | 0.21 | 13.0 [6, 22] | 29.4 [13, 50] | 2.7 [0, 6] | 5.3 [0, 12] | 2.8 |
| halving | matched, round 1's strata | 0.01 | 0.80 | 0.20 | 13.0 [6, 22] | 29.5 [12, 49] | 2.7 [0, 7] | 5.4 [0, 12] | 5.6 |

Counts are cumulative, round 1 included, mean [p10, p90], and are what the writer would hold if every round were run (the course may stop earlier). P(floor rule stops it) is the share of courses the floor rule ends after round 3, 4 or 5; the three shares per cell are in the JSON.

## Reading

- **The success stop is now unlikely.** Course A was chosen on 0.93 and 0.70. With one writer and round 1 folded in, and rates holding, the matched statistic reaches 26 by round 6 in 0.00 to 0.12 of simulated courses across the two yield scenarios and the two strata models (course A's own all-matched statistic: 0.06 to 0.14); with the illegible rate falling to half it is 0.00 to 0.06.
- **The floor rule governs.** It ends 0.66 to 0.68 of courses under no drift (matched statistic), and 0.60 to 0.63 of all courses end by it right after round 3, because the illegible count is still small then; of the courses it does not end, most run to the sixth round without reaching 26 (0.20 to 0.33 of all courses).
- **Where the fall from 0.93 comes from** (P(stop by success), rates holding):

| step | P |
|---|---|
| course A as reconciled (two writers, losses 0.8, all certified items matched) | 0.93 |
| the same with the second writer removed (one writer, the Sonnet 5.5 pair's rates, losses 0.8) | 0.47 |
| with round 1's validity and quiet shares (20 of 24 valid, 13 of 20 quiet: about 0.54 combined, against 0.8) in place of the flat 0.8 (`e2_prior_only`) | 0.10 |
| with round 1's counts folded in (`e2_prior_plus_round1`) | 0.06 |
| and matched at the 10-point band on round 1's strata | 0.04 |

- **What the writer is expected to hold** (rates holding, every round run, round 1 included; the two yield scenarios): after round 3, 13 to 21 certified and 4 quiet-but-illegible; after round 6, 29 to 49 certified and 9 to 10 illegible (the p10 to p90 spread is in the table). The certified side reaches the floor of 12 by round 6; the illegible mean stays below the floor of 12 even after round 6, so the floor of 12 + 12 is not expected to be reached and brief 24's target of 26 + 26 is out of reach on the illegible side.
- **What would change it.** A second writer (Muse Wonder, once Aravind names its harness) joining at round 3 starts its own feedback course and is matched within writer; the forecast above does not include it. Feedback may raise the illegible yield, which is what round 2 measures (round 1 had none); nothing here is evidence that it will not. The forecast is re-run on round 2's counts before any round beyond the third.

## Reproduce

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_forecast.py --part3 work/stage3/elicitation/part3 --writer gpt61sol --round 1
```

