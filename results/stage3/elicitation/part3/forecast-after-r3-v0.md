# Forecast after writer round 3's certification (brief 30 note 12 and its addendum)

Written by the Part 3 session (Sonnet 5.5). $0, no model call, no item, no B3 file. Module `stage3_elicitation_forecast.py` 2a937c38, seed 20261216, 40000 runs per all-matched cell and 20000 per matched cell. Counts and aggregates only.

## What is computed

The remaining rounds (4 to 6) at the cap of 96 per writer, for the writers who wrote: `gpt61sol` (216 written, 207 valid, 79 certified, 0 illegible); `muse_wonder` (96 written, 70 valid, 30 certified, 7 illegible). **Yields** are Jeffreys posteriors on each writer's own observed counts (per valid item, the valid share as observed), no drift. **The statistic** is the matched effective n at the 10-point band within writer x document, on the observed strata (each writer's own valid items' (document, composition) pairs resampled for the future items), against 26. The cases beside it: the all-matched statistic (course A's), and the illegible rate falling linearly to half over the next three rounds (`halving`). **P(stop by success)** is the share of simulated courses reaching 26 at some remaining round, with the floor rule applied after rounds before the last (the course as governed); the same without the floor rule is printed beside. **A value on the margin of the bar (its 95 percent Monte Carlo interval holds 0.5) reads as below 0.5.**

## The reading for the bar

**P(stop by success within the remaining rounds), matched on the observed strata, no drift: 0.96; it reads: at or above 0.5.** The bar for opening rounds 4 to 6 is at least 0.5.

| case | statistic | P(stop by success), floor rule on | floor rule off | P(floor rule ends it) | reading |
|---|---|---|---|---|---|
| none | matched, observed strata | 0.96 | 0.96 | 0.00 | at or above 0.5 |
| none | every certified item matched (course A's) | 0.99 | 0.99 | 0.00 | at or above 0.5 |
| halving | matched, observed strata | 0.82 | 0.82 | 0.00 | at or above 0.5 |
| halving | every certified item matched (course A's) | 0.94 | 0.94 | 0.00 | at or above 0.5 |

**The floor rule now** (rules v0.2: stop if the projected effective n at round 6 is below 12; the cumulative counts scaled by the planned items, every certified item counted as matched): projected 37.4, so it **does not fire**.

## Counts if every remaining round were run (mean [p10, p90], matched case, no drift)

| after round | certified | quiet-but-illegible | matched effective n |
|---|---|---|---|
| 3 | 109.0 [109, 109] | 7.0 [7, 7] | as certified |
| 4 | 173.9 [163, 185] | 14.6 [10, 19] | 18.5 [13, 25] |
| 5 | 238.9 [221, 257] | 22.2 [15, 31] | 31.7 [21, 43] |
| 6 | 304.0 [279, 329] | 29.8 [19, 42] | 44.6 [30, 60] |

## Phase E: the expected certified count per further round

Certified items are what the paper needs first (roadmap v4; note 12 item 2). Added per round, all writers and by writer, mean [p10, p90], no drift:

| round | all writers (certified) | `gpt61sol` certified | `muse_wonder` certified | all writers (illegible) |
|---|---|---|---|---|
| 4 | 65.0 [54, 76] | 35.0 [28, 42] | 29.9 [22, 38] | 7.6 [3, 13] |
| 5 | 65.0 [54, 76] | 35.0 [28, 42] | 30.0 [22, 38] | 7.6 [3, 13] |
| 6 | 65.0 [54, 76] | 35.1 [28, 42] | 29.9 [22, 38] | 7.6 [3, 12] |

## Reproduce

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_forecast.py after --part3 work/stage3/elicitation/part3 --rounds-done 3 --writer gpt61sol:1,2,3 [--writer muse_wonder:3]
```

