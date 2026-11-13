# P2 power-v0: block D's whole rule (blue harness session, Opus 5.5, 2026-11-14; $0)

**With no unresolved Sol runs, D reads sentence 1 in about 90 percent of draws once true RM uptake is 0.3 or more, and sentence 2 in 96 percent at zero uptake. Between 0.08 and 0.2 it is mostly inconclusive at 46 payloads. Gate 1 makes D fragile to unresolved Sol runs, because v1.1 section B counts an unresolved clean run as a firing. At Sol's block-Z rate (2.1 percent of runs unresolved after the retry pass), the sentence is withheld in about 70 percent of draws whatever the uptake; at 1 percent, in about a third.** Sol had no unresolved run in the core's 672 runs on the same documents D uses. Z's errors came from the dose workspaces, so D's own rate is the smoke's to show.

By `work/checks/stage3_p2_power.py` (`power-v0.json` sha256 5ff63e1cdfe877a7…); 1,000 simulated blocks per cell, 1,000 bootstrap replicates each, seeds 20261114 + offset.

## Assumptions
- **Payloads and runs:** 46 RM payloads (23 routine, 23 middle), 2 followers, 3 planted repeats; bootstrap within regime, as the join does.
- **True carry rate:** a payload's rate q ~ Beta(mean p, concentration 0.49), shared by both followers. That matches the core's spread on these 46: mixture uptake sd 0.332 at mean 0.793, with 63 percent of payloads at 1 and 9 percent at 0. This spread makes the interval wide; a less dispersed truth would narrow the inconclusive band.
- **Audit:** the acts weight scales each payload by the core's factors (upper 0.875, lower 0.809 of raw). The six computations are raw, upper and lower, each with unresolved planted runs not carried and carried.
- **Gate 1 per follower:** 138 RM and 24 AL clean runs. Each fires with probability 1/276 (the core's pooled RM clean firing) or is unresolved with the follower's rate (Kimi 0, Sol u_sol). Withhold at 3 or 2.
- **What this checks:** the registered rule and nothing else. It assumes D's uptake behaves like the core's across payloads, which D exists to test.

## Probability of each result, by true RM uptake p (rows) and Sol's unresolved rate (column groups)

| p | u_sol 0.0: 1 / 2 / inc / withheld | u_sol 0.005: 1 / 2 / inc / withheld | u_sol 0.01: 1 / 2 / inc / withheld | u_sol 0.021: 1 / 2 / inc / withheld |
|---|---|---|---|---|
| 0.0 | 0.00 / 0.95 / 0.00 / 0.04 | 0.00 / 0.86 / 0.00 / 0.14 | 0.00 / 0.69 / 0.00 / 0.31 | 0.00 / 0.27 / 0.00 / 0.73 |
| 0.05 | 0.00 / 0.48 / 0.48 / 0.03 | 0.00 / 0.39 / 0.48 / 0.14 | 0.00 / 0.29 / 0.38 / 0.33 | 0.00 / 0.12 / 0.17 / 0.71 |
| 0.08 | 0.00 / 0.16 / 0.80 / 0.04 | 0.00 / 0.13 / 0.74 / 0.13 | 0.00 / 0.07 / 0.57 / 0.36 | 0.00 / 0.04 / 0.28 / 0.68 |
| 0.1 | 0.00 / 0.07 / 0.91 / 0.03 | 0.00 / 0.04 / 0.82 / 0.13 | 0.00 / 0.04 / 0.64 / 0.32 | 0.00 / 0.01 / 0.26 / 0.72 |
| 0.12 | 0.01 / 0.03 / 0.92 / 0.04 | 0.01 / 0.02 / 0.82 / 0.15 | 0.01 / 0.02 / 0.64 / 0.33 | 0.00 / 0.00 / 0.28 / 0.71 |
| 0.15 | 0.05 / 0.01 / 0.91 / 0.03 | 0.06 / 0.00 / 0.80 / 0.14 | 0.05 / 0.00 / 0.61 / 0.34 | 0.02 / 0.00 / 0.30 / 0.68 |
| 0.2 | 0.34 / 0.00 / 0.63 / 0.04 | 0.29 / 0.00 / 0.57 / 0.14 | 0.22 / 0.00 / 0.43 / 0.35 | 0.09 / 0.00 / 0.20 / 0.71 |
| 0.25 | 0.67 / 0.00 / 0.30 / 0.03 | 0.59 / 0.00 / 0.26 / 0.14 | 0.48 / 0.00 / 0.21 / 0.31 | 0.20 / 0.00 / 0.08 / 0.72 |
| 0.3 | 0.89 / 0.00 / 0.06 / 0.04 | 0.77 / 0.00 / 0.07 / 0.16 | 0.63 / 0.00 / 0.05 / 0.33 | 0.26 / 0.00 / 0.03 / 0.71 |
| 0.5 | 0.96 / 0.00 / 0.00 / 0.04 | 0.84 / 0.00 / 0.00 / 0.16 | 0.65 / 0.00 / 0.00 / 0.35 | 0.31 / 0.00 / 0.00 / 0.69 |
| 0.8 | 0.96 / 0.00 / 0.00 / 0.04 | 0.86 / 0.00 / 0.00 / 0.14 | 0.64 / 0.00 / 0.00 / 0.36 | 0.30 / 0.00 / 0.00 / 0.70 |

## What it implies for D
- **The cause of most withholding:** at 3 of 138, gate 1 has little slack. The core's own clean firing is 1 in 276 runs, and each unresolved Sol clean run adds to the count.
- **What the smoke reports:** Sol's re-asked turns and unresolved runs. If D's clean arm shows Sol runs ending `infra_error`, the coordinator hears before the launch.
- **W:** its power is not here; it comes with W's build as `power-v1`.
