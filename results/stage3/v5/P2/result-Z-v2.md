# Block Z: post hoc table (blue harness session, Opus 5.5, 2026-11-14)

**Post hoc, after the registered premise failed; descriptive. No sentence about composition.**

What the table shows: a partial cell that held at least one of the item's literal-bearing statements carried the literal almost as often as the full triple (0.87 with one, 0.97 with two, 0.98 for the full triple); a cell that held none never fired (0 of 84 runs); and within item, removing the other statements lowered carriage by 0.090 [0.026, 0.168].

The registered result is unchanged and is in `result-Z-v1.md` (7e724ebd): the estimand is −0.049 [−0.146, 0.000] on 14 cells. Of the 58 cells the registration called unable to fire, 44 fired, on 238 of 348 runs. The registration's eligible-cell rule did not describe the scorer, and no sentence is made from it.

## Method
- **Inputs:** the dose manifest's `literal_statements` and the outcomes only. The statements each partial cell holds come from the join's registered `SUBSET_STATEMENTS` (FT v1.3 section 6; the manifest has no such field). No red file was opened, and no rule of the scorer is assumed.
- **k:** for each partial cell, how many of the item's literal-bearing statements it holds (0, 1 or 2).
- **Uptake:** the 50:50 follower mixture of a cell's carried share, with unresolved runs not carried.
  - By k: the mean over an item's cells with that k, averaged with equal weight over the items that have such a cell.
  - Intervals: 95 percent, from 2,000 item resamples, seed 20261114.
- **Corrected within-item contrast:** the full triple's uptake minus the mean uptake of the item's partial cells with k of 1 or more, averaged over items. The adverse completion sets unresolved runs carried in the partial cells and not in the full triple.
- **D378d17ac:** shown, and left out of every average, because its clean arm fired on 3 of 6 runs.
- **Record:** `P2/posthoc-Z-v0.json` (sha256 e919c605f93dd3e3…), by `work/checks/stage3_p2_z.py` `posthoc`.

## Averages (11 items; D378d17ac left out)

| quantity | items | value [95% interval] |
|---|---|---|
| partial cells, k = 0 | 8 | 0.000 [0.000, 0.000] |
| partial cells, k = 1 | 11 | 0.870 [0.769, 0.958] |
| partial cells, k = 2 | 8 | 0.965 [0.917, 1.000] |
| full triple | 11 | 0.985 [0.955, 1.000] |
| clean arm | 11 | 0.000 [0.000, 0.000] |
| contrast: full minus partial (k ≥ 1), raw | 11 | 0.090 [0.026, 0.168] |
| contrast, adverse (unresolved carried in partial, not in full) | 11 | 0.084 [0.025, 0.160] |
| contrast, the other setting | 11 | 0.090 [0.026, 0.168] |

**Stray rate (k = 0 cells, D378d17ac left out):** 0 fires in 84 runs over 14 cells.

## Per item (fires/runs per partial cell, with k)

| item | literal statements | full | clean fires | contrast | s1 | s2 | s3 | s4 | s5 | s6 |
|---|---|---|---|---|---|---|---|---|---|---|
| D033aab33 | 1, 3 | 1.00 | 0 of 6 | 0.067 | k1 5/6 | k0 0/6 | k1 6/6 | k1 5/6 | k2 6/6 | k1 6/6 |
| D23f33406 | 1, 2, 3 | 1.00 | 0 of 6 | 0.111 | k1 4/6 | k1 4/6 | k1 6/6 | k2 6/6 | k2 6/6 | k2 6/6 |
| D271f119a | 1 | 1.00 | 0 of 6 | 0.000 | k1 6/6 | k0 0/6 | k0 0/6 | k1 6/6 | k1 6/6 | k0 0/6 |
| D378d17ac | 1, 2, 3 | 1.00 | 3 of 6 | left out | k1 6/6 | k1 5/6 | k1 6/6 | k2 5/6 | k2 6/6 | k2 6/6 |
| D5fdd250a | 1, 3 | 1.00 | 0 of 6 | 0.000 | k1 6/6 | k0 0/6 | k1 6/6 | k1 6/6 | k2 6/6 | k1 6/6 |
| D6e4b6548 | 2, 3 | 1.00 | 0 of 6 | 0.000 | k0 0/6 | k1 6/6 | k1 6/6 | k1 6/6 | k1 6/6 | k2 6/6 |
| D884db9df | 1 | 1.00 | 0 of 6 | 0.389 | k1 2/6 | k0 0/6 | k0 0/6 | k1 3/6 | k1 6/6 | k0 0/6 |
| D9a052d5e | 1, 2, 3 | 1.00 | 0 of 6 | 0.194 | k1 4/6 | k1 3/6 | k1 6/6 | k2 4/6 | k2 6/6 | k2 6/6 |
| Da0de8e06 | 1, 2, 3 | 1.00 | 0 of 6 | 0.000 | k1 6/6 | k1 6/6 | k1 6/6 | k2 6/6 | k2 6/6 | k2 6/6 |
| Db3ad0efe | 1, 3 | 1.00 | 0 of 6 | 0.000 | k1 6/6 | k0 0/6 | k1 6/6 | k1 6/6 | k2 6/6 | k1 6/6 |
| Dbb8034de | 1 | 1.00 | 0 of 6 | 0.000 | k1 6/6 | k0 0/6 | k0 0/6 | k1 6/6 | k1 6/6 | k0 0/6 |
| Dede0b7ad | 1, 2 | 0.83 | 0 of 6 | 0.233 | k1 1/6 | k1 5/6 | k0 0/6 | k2 5/6 | k1 1/6 | k1 6/6 |

## Correction to `result-Z-v1.md`
v1 wrote that a cell holding no literal-bearing statement fires "at most one stray fire, as in Dede0b7ad s1 and s5". Both of those cells hold statement 1 (k = 1), so they were not stray. No cell with k = 0 fired.
