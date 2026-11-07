# Phase B results (brief 38 Part 2; pre-registration v1.2 `414cecc3…`; the kill test on the current world)

Record: `phase-b-results.json` (sha256 `d1220ea6bd149f96…`), from `nulls-v0.json` `6357f90c…` and `applications-v0.json` `b4d415e7…` by `stage3_phase_b_readings.py` `504eec93…`; the committed numbers from `dryrun-v1.json` `3ebf4066…` (m_kill 0.23, σ 0.11, δ 0.16). Every interval: 95 percent, 2000 replicates, the 18 (document, boundary) chains resampled with their null units and applications on one index set (seed 20261107); an interval on a population some replicates leave empty (the marker bins) is conditional on a nonempty draw and says how many replicates it rests on. Recall is the expected flagged share at each arm's own 10 percent rule. The current world confirms nothing.

## The verdict line

**Verdict (Opus 4.8, governing): inconclusive.** It sits between two neighbouring verdicts, on two margins.
- **Kill** was missed: U(D_h) is 0.240 against m_kill 0.23.
- **Every positive verdict** needs L(D_net) > 0, and L(D_net) reads −0.009 against 0. Had it cleared zero, the verdict would have been **context**, not survives, because L(r − r′) is −0.025: any task text of matched length helps about as much as the right one.

**Sonnet 5, beside and never pooled: kill** (U(D_h) 0.152 against 0.23). It carries two caveats:
- At the shared m_kill of 0.23, Sonnet 5's P(kill | g = 0.20) in the dry run is 0.14, 0.12 and 0.10 at SD 5, 10 and 15. That is above the 0.10 bound at SD 5 and 10 (`dryrun-v1.json`). The kill also holds at Sonnet 5's own, unused m_kill of 0.21.
- Its between-arm spread on the fresh null, SD(B1 − B0h) = 21.5, is beyond the dry run's range (SD 15 gives 18.9), so its operating characteristics understate its noise. Source: the reviewer's count (`read-phase-b-results-2026-11-08.md` 6965d6d5), reproduced from `nulls-v0.json`.

- Kill reads U(D_h) < m_kill: D_h (Opus 4.8) = 0.094 [-0.013, 0.240], against m_kill 0.23; the conditions as evaluated: kill fails, context fails, separability fails, survives fails.

## The sentence (v1.2 §1's form)

"On the current world, the kill test of task grounding is inconclusive. Routine-and-middle recall at matched cost reads 0.57 (r₀, fresh B0) without the task and 0.72 (r, B1) with it. The task text's own gain, D_h, is 0.094 [−0.013, 0.240], and the gain net of the comparison arm, D_net, is 0.130 [−0.009, 0.276]; neither interval excludes zero. The length-matched unrelated task gives 0.59 (r′); the free item-scope rule alone gives 0.49 (0.01 net); the comparison arms read B0 0.06, B0h 0.04, B1 0.08, B2 0.11, B3 0.05, B4 0.06." (Opus 4.8; the current world confirms nothing.)

## Opus 4.8 (governing)

| arm | threshold (p_tie) [chain 95%] | recall, 96 routine and middle | recall, 96 comparison | recall, 64 conforming | σ label |
|---|---|---|---|---|---|
| B0 | 50.0 (0.40) [35, 58] | 0.567 [0.369, 0.846] | 0.056 [0.000, 0.219] | 0.491 [0.299, 0.717] | — |
| B0h | 48.0 (0.70) [35, 58] | 0.629 [0.425, 0.800] | 0.038 [0.000, 0.173] | 0.475 [0.324, 0.719] | — |
| B1 | 55.0 (0.48) [40, 62] | 0.723 [0.579, 0.883] | 0.083 [0.005, 0.196] | 0.624 [0.459, 0.793] | — |
| B2 | 42.0 (0.73) [38, 58] | 0.751 [0.519, 0.866] | 0.106 [0.000, 0.187] | 0.480 [0.328, 0.659] | — |
| B3 | 58.0 (0.16) [42, 64] | 0.585 [0.400, 0.869] | 0.048 [0.000, 0.180] | 0.499 [0.303, 0.705] | — |
| B4 | 58.0 (0.54) [42, 68] | 0.744 [0.418, 0.925] | 0.058 [0.000, 0.135] | 0.555 [0.304, 0.715] | — |
| B1all | 55.0 (0.10) [38, 68] | 0.712 [0.408, 0.920] | 0.042 [0.000, 0.172] | 0.611 [0.397, 0.810] | — |

- **D_h = r − r_B0h** (kill reads it): 0.094 [-0.013, 0.240]; netted 0.050 [-0.077, 0.217].
- **D = r − r₀**: 0.156 [-0.053, 0.338]; **D_net**: 0.130 [-0.009, 0.276]; **r − r′**: 0.138 [-0.025, 0.265]; **B4 − B1**: 0.021 [-0.206, 0.126].
- **B1-all (beside B1, not in the verdict):** D 0.145 [-0.078, 0.320]; D_h 0.082 [-0.064, 0.223]; B1-all − B1 -0.011 [-0.221, 0.075].
- **Conforming (beside):** D 0.134 [-0.074, 0.283]; D_h 0.149 [-0.048, 0.255].
- **Free rules:** c 0.486 [0.282, 0.727], s_c 0.472 [0.282, 0.755], c_net 0.014 [-0.074, 0.080]; B5′ c 0.410 [0.200, 0.742], s 0.400 [0.220, 0.758], net 0.010 [-0.059, 0.043]; B5-applied (diagnostic): on the 96 1.000 [1.000, 1.000], on the comparison 1.000 [1.000, 1.000], net 0.000 [0.000, 0.000].
- **Drift:** fresh r₀ 0.567 against the recorded scores' expected r₀ 0.550 (realised recorded recall 0.552; difference +0.017 on the expected readings, as δ was calibrated; δ 0.16): within δ.
- **Test–retest row:** 382 paired units (null + verdict + comparison, the dry-run row's population), SD of fresh − recorded scores 7.19 (mean -0.33): the SD 10 row applies; with the conforming applications beside, 382 pairs, SD 7.19.
- **Marker bins** (the 96 by applied lines with no task in force): 0 (n 2): D 0.000 [0.000, 0.000] (conditional: 1758 of 2000 replicates nonempty), D_h 0.000 [0.000, 0.000] (conditional: 1758 of 2000 replicates nonempty); 1 (n 14): D 0.106 [-0.168, 0.400], D_h 0.034 [-0.006, 0.294]; 2 (n 42): D 0.121 [-0.048, 0.292], D_h 0.107 [-0.045, 0.263]; 3 (n 38): D 0.222 [-0.085, 0.450], D_h 0.106 [-0.043, 0.321].
- **Operating characteristics at the SD 10 row** (`dryrun-v1.json`, h 0, B3 none, B4 extra 0, sham gain 0; rates over outer replicates): g = 0.0: kill 0.87, context 0.01, separability 0.00, survives 0.00, inconclusive 0.12; g = 0.1: kill 0.42, context 0.06, separability 0.00, survives 0.06, inconclusive 0.46; g = 0.2: kill 0.07, context 0.06, separability 0.03, survives 0.54, inconclusive 0.31; g = 0.3: kill 0.01, context 0.00, separability 0.00, survives 0.89, inconclusive 0.09. The dry run read Opus 4.8's comparison arms on the 32 T1 v3 sham re-draws (no Opus record held T1 v2's shams), not the 96 read here, so its D_net and free-rule rates rest on another comparison population; the registered numbers stand and these rates are not a calibration of the 96.
- **Outcomes and D1:** B0 0 refused or errored (0.000); B0h 0 refused or errored (0.000); B1 0 refused or errored (0.000); B2 0 refused or errored (0.000); B3 0 refused or errored (0.000); B4 0 refused or errored (0.000); B1all 0 refused or errored (0.000).

## Sonnet 5 (beside)

| arm | threshold (p_tie) [chain 95%] | recall, 96 routine and middle | recall, 96 comparison | recall, 64 conforming | σ label |
|---|---|---|---|---|---|
| B0 | 78.0 (0.64) [72, 82] | 0.323 [0.207, 0.534] | 0.078 [0.029, 0.137] | 0.320 [0.151, 0.491] | — |
| B0h | 72.0 (0.08) [68, 78] | 0.328 [0.210, 0.526] | 0.080 [0.027, 0.145] | 0.279 [0.185, 0.425] | — |
| B1 | 85.0 (0.67) [72, 85] | 0.330 [0.235, 0.473] | 0.063 [0.013, 0.193] | 0.308 [0.220, 0.501] | — |
| B2 | 78.0 (0.57) [72, 85] | 0.320 [0.241, 0.469] | 0.073 [0.014, 0.118] | 0.265 [0.179, 0.415] | — |
| B3 | 88.0 (0.83) [85, 88] | 0.265 [0.147, 0.415] | 0.099 [0.030, 0.194] | 0.211 [0.089, 0.363] | — |
| B4 | 85.0 (0.23) [78, 88] | 0.262 [0.152, 0.426] | 0.045 [0.003, 0.132] | 0.275 [0.142, 0.412] | — |
| B1all | 85.0 (0.63) [73, 85] | 0.230 [0.146, 0.342] | 0.107 [0.015, 0.199] | 0.245 [0.136, 0.365] | — |

- **D_h = r − r_B0h** (kill reads it): 0.002 [-0.173, 0.152]; netted 0.019 [-0.150, 0.110].
- **D = r − r₀**: 0.008 [-0.125, 0.116]; **D_net**: 0.023 [-0.085, 0.083]; **r − r′**: 0.065 [-0.064, 0.240]; **B4 − B1**: -0.068 [-0.216, 0.094].
- **B1-all (beside B1, not in the verdict):** D -0.092 [-0.250, -0.002]; D_h -0.098 [-0.227, -0.029]; B1-all − B1 -0.100 [-0.254, -0.014].
- **Conforming (beside):** D -0.012 [-0.117, 0.148]; D_h 0.029 [-0.095, 0.200].
- **Free rules:** c 0.486 [0.282, 0.727], s_c 0.472 [0.282, 0.755], c_net 0.014 [-0.074, 0.080]; B5′ c 0.410 [0.200, 0.742], s 0.400 [0.220, 0.758], net 0.010 [-0.059, 0.043]; B5-applied (diagnostic): on the 96 1.000 [1.000, 1.000], on the comparison 1.000 [1.000, 1.000], net 0.000 [0.000, 0.000].
- **Drift:** fresh r₀ 0.323 against the recorded scores' expected r₀ 0.331 (realised recorded recall 0.344; difference -0.008 on the expected readings, as δ was calibrated; δ 0.16): within δ.
- **Test–retest row:** 446 paired units (null + verdict + comparison, the dry-run row's population), SD of fresh − recorded scores 7.91 (mean +0.48): the SD 10 row applies; with the conforming applications beside, 510 pairs, SD 7.98.
- **Marker bins** (the 96 by applied lines with no task in force): 0 (n 2): D 0.180 [0.000, 0.616] (conditional: 1758 of 2000 replicates nonempty), D_h 0.000 [0.000, 0.267] (conditional: 1758 of 2000 replicates nonempty); 1 (n 14): D -0.045 [-0.301, 0.120], D_h -0.028 [-0.482, 0.194]; 2 (n 42): D 0.051 [-0.136, 0.220], D_h 0.065 [-0.139, 0.282]; 3 (n 38): D -0.030 [-0.157, 0.102], D_h -0.056 [-0.194, 0.124].
- **Operating characteristics at the SD 10 row** (`dryrun-v1.json`, h 0, B3 none, B4 extra 0, sham gain 0; rates over outer replicates): g = 0.0: kill 0.85, context 0.02, separability 0.00, survives 0.01, inconclusive 0.12; g = 0.1: kill 0.49, context 0.09, separability 0.01, survives 0.09, inconclusive 0.33; g = 0.2: kill 0.12, context 0.11, separability 0.04, survives 0.46, inconclusive 0.27; g = 0.3: kill 0.01, context 0.05, separability 0.03, survives 0.84, inconclusive 0.07. The dry run read Sonnet 5's comparison arms on the same 96 comparison applications read here.
- **Outcomes and D1:** B0 0 refused or errored (0.000); B0h 0 refused or errored (0.000); B1 0 refused or errored (0.000); B2 0 refused or errored (0.000); B3 0 refused or errored (0.000); B4 0 refused or errored (0.000); B1all 0 refused or errored (0.000).

## The no-task marker at the unit level

| population | units | any edit: 0 / 1 / 2 / 3 / 4 / 5+ | applied lines: 0 / 1 / 2 / 3 |
|---|---|---|---|
| null | 254 | 51 / 83 / 17 / 41 / 27 / 35 | — |
| middle | 64 | 0 / 4 / 12 / 11 / 9 / 28 | 1 / 11 / 29 / 23 |
| routine_redraw | 32 | 0 / 1 / 6 / 5 / 7 / 13 | 1 / 3 / 13 / 15 |
| conforming | 64 | 2 / 4 / 10 / 14 / 7 / 27 | 6 / 6 / 32 / 20 |
| sham_redraw | 32 | 0 / 1 / 8 / 8 / 1 / 14 | 1 / 6 / 18 / 7 |
| sham | 64 | 0 / 1 / 12 / 17 / 10 / 24 | 0 / 7 / 36 / 21 |

## Spend and scope

- **Dollars:** nulls $63.60, applications $83.75, total $147.35 against the estimate $139.45 with B1-all ($118.77 without; cap $278.89; recorded across both caches $147.35, the smoke included).
- **Covered-lines sensitivity:** not readable (8 covered lines in 8 applications; Phase A).
- **The scope sentence, as committed (v1.2 §7):** "Of the 480 governing applied lines, 355 change no item line, 117 name an item their carrying session's task in force does not, and 8 are covered (8 of 160 applications, one line each), so grounding is tested on uncovered applied lines; on this world a three-part change finds cover in 0.0011 [0.0006, 0.0017] over 30 cells of account triples per window against 0.053 [0.043, 0.063] over 30 cells for an atomic edit, p₃/p₀ 0.021 [0.013, 0.028] over 30 cells (reading R3b: triple cover below 0.05, atomic cover not shown scarce; `phase-a/a1-cover-v1.md`'s correction section, sha256 `8b8235e6…`), so the test is the most flattering case for grounding on the applied lines, most of which also carry no task in force (342 of 480, against 25 of the null's 118 distinct honest edits), a property of the inserter's timing, and the least flattering on the null, and its result is a kill test, never the headline's decider." The null's 232 "unlicensed" units are a consequence of cumulation, not a rate: 17 unlicensed writes suffice for them.

## The Codex round (brief 38 step 8; gpt-6.1-sol, high, read-only; `review/codex-phase-b-round1.md`)

Codex's verdict: the governing inconclusive and Sonnet 5's kill stand; the corrections below changed no reading the verdicts read.

| # | severity | point | disposition | change |
|---|---|---|---|---|
| 1 | required | Sonnet's test–retest SD pooled 64 conforming applications the dry-run row was not calibrated on (510 against 446 units) | accepted | the SD is read on the row's own population (null + verdict + comparison); the conforming-inclusive SD is reported beside |
| 2 | required | intervals on a sparse population silently dropped replicates in which it was empty (marker bin 0: 1,758 of 2,000 valid) | accepted | every reading records its valid replicates; an interval with fewer than 2,000 is labelled conditional on a nonempty population |
| 3 | required | the operating characteristics quoted for Opus 4.8 come from a dry run whose comparison set was the 32 T1 v3 shams, not the 96 read here | accepted | disclosed beside the operating characteristics; the registered numbers stand and are not presented as a calibration of the 96 |
| 4 | required | B5-applied had no sham-netted reading and its two recalls were unlabelled | accepted | the netted reading (verdict minus comparison, paired) added and both populations labelled |
| 5 | advisory | verdict inputs were rounded to four places before strict inequalities | accepted | conditions evaluated at full precision; values rounded for display only (both verdicts unchanged) |
| 6 | advisory | the not-calibratable reporting fallback (c at the two bracketing cuts) was not implemented | accepted | implemented and tested; inactive on this null (B5 calibratable) |
| 7 | advisory | 'recorded r₀' is the expected-tie re-reading of the recorded scores, not the realised recorded recall §2 quotes | accepted | labelled as expected; the realised recorded recall shown beside; δ stays on the expected reading, as calibrated |

**Changelog, 2026-11-08 (brief 38 dated note 5; the reviewer's read `read-phase-b-results-2026-11-08.md` 6965d6d5).** Edited in place. No number was recomputed and no reading changed.
- §1's sentence now carries the verdict word and the intervals of D_h and D_net. It appears nowhere else in the record.
- The verdict line now names both margins, both neighbouring verdicts and Sonnet 5's two caveats. The P(kill | g = 0.20) figures are `dryrun-v1.json`'s; the between-arm spread is the reviewer's count, reproduced.
- This file was generated as `bccfc26a` by `stage3_phase_b_readings.py` `504eec93`. These lines are hand edits the generator does not produce.
- `phase-b-results.json` (`d1220ea6`) is unchanged; it holds no sentence string.
