# Block H (honest bank): complete (blue harness session, Opus 5.5, 2026-11-14)

**No sentence (v1 section 4). On this world's own runnable tasks, a task needs a planted item rarely: the rule-defined need share has a mean of 0.0013 of all arrival weight, or 0.0030 of runnable weight, and 35 of the 54 payloads have no runnable task that needs their slot. When a drawn task does need or may touch the slot, the follower almost always reads the planted line before acting, and carries it in half of those runs. A task that neither needs nor may touch the slot never carried it, and no clean run fired.** This is an instance for this bank, these states and the runnable 0.438 of arrival weight; descriptive throughout. No product of need and carry is formed.

Design: `P2/preregistration-v1.md` (19d4a7d5) section 3, as amended by `preregistration-v1.1.md` (ab171917) section D. Seal: `P2/pre-gate-p2.md`, H section and the dated caps section.

## Runs
- **Smoke** (`H-smoke`, kept, not analysed): 40 runs, $1.020, 22:02 to 22:12 on the machine clock.
- **Launch:** 864 of 864 runs (216 draws × planted and clean × 2 followers), 22:13:35 to about 01:19. No stop, no errors, no refusals, no aborts, no re-asked turns.
- **The one retry pass:** 0 candidates. It finished at 01:19:43.
- **Latest records:** 864, all with a verdict.
- **Overlap:** D from H's start to 23:55, about 1 hour 42 minutes; W for all of H's run, about 3 hours 6 minutes.

## Need (exact, rule-defined, at each payload's clean state; `need-table-v1.json` 040b6592)
- **Mean share:** 0.0013 of all weight and 0.0030 of runnable weight; may-touch 0.0021 and 0.0049.
- **Empty strata:** 35 of 54 payloads have an empty need stratum, and 33 an empty may-touch stratum.
- **The draws:** 216 draws, 4 per payload, give planted runs of 78 needs, 42 may-touch and 312 no-need, by each draw's actual class.

## Joint table: need class × access × carry, planted arm (432 runs; equal weight per draw; 95 percent intervals resampling payloads, all of a payload's draws and both followers together; 2,000 replicates, seed 20261114)
Access means the slot's line was returned before the run's last action.

| need class | access | carried | share of draws [95%] | runs |
|---|---|---|---|---|
| needs | yes | yes | 0.090 [0.049, 0.137] | 39 |
| needs | yes | no | 0.083 [0.044, 0.130] | 36 |
| needs | no | no | 0.007 [0.000, 0.014] | 3 |
| may touch | yes | yes | 0.049 [0.028, 0.072] | 21 |
| may touch | yes | no | 0.049 [0.028, 0.074] | 21 |
| no | yes | no | 0.174 [0.132, 0.215] | 75 |
| no | no | no | 0.549 [0.463, 0.627] | 237 |

Every other cell is 0, including every carried cell without access and every carried no-need cell.

**Clean arm** (432 runs): needs with access 0.176, needs without access 0.005, may touch with access 0.097, no-need with access 0.181, no-need without access 0.542. Not one carried.

## By stratum (planted; carry among runs with a verdict)
| stratum | carry [95%] | access before the last action [95%] | runs |
|---|---|---|---|
| need | 0.500 [0.329, 0.684] | 0.961 [0.921, 1.000] | 76 |
| may touch | 0.500 [0.333, 0.667] | 1.000 [1.000, 1.000] | 42 |
| any | 0.003 [0.000, 0.012] | 0.245 [0.197, 0.299] | 314 |

The single carried run in the "any" stratum was a draw whose task needs the slot. In the clean arm the strata's carry is 0, with access 0.974, 1.000 and 0.255.

## Beside
- **Access at the first firing action:** in all 60 planted runs that carried, the line had been returned before the first action at which the scorer fires (60 of 60).
- **Clean firings by pair:** none.
- **By follower:**
  - Carried planted runs: Sol 25 needs and 12 may-touch; Kimi 14 and 9.
  - Cost per run: Kimi $0.0157, Sol $0.0264.

## Cost
- **Spend:** $18.194 for the launch and $1.020 for the smoke, $19.21 in all, against v1.1's estimate of $16.0 and a smoke-priced $22.0.
- **Cap:** $24.9 (D45); the launch line ran at $23.88.

## Hashes
- **Records:** `outcomes-H-v0.jsonl` ee13e3ba1f5d54b6…; `analysis-H-v0.json` 87b4b97576eef889….
- **Runner and harness:** `stage3_p2_run.py` 10fbc1e2, `stage3_p2_harness.py` acb83e9d.
- **Join:** `stage3_p2_h.py` 3b5fcb1f.
- **Draws and scorers:** `draws-H-tasks-v1.json` 8a5e52c3; `evaluate_any` 42fa156e; `access` 0cb79fb7.
