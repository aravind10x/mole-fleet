# P2 power-v1: block W's uptake class and work clause (blue harness session, Opus 5.5, 2026-11-14; $0)

**On the core's structure, W tells a fall in RM uptake of 0.25 or more as U1 in 88 percent of draws or more, and a true fall of 0.15 mostly as U2b. A true zero reads U3 ("a fall of 0.15 is excluded") in 93 percent. The work clause excludes a fall of 0.10 in completion in 89 percent of draws when there is none, and calls a true fall of 0.05 "lowered" in 89 percent.** Raw results only; the audit and unresolved-run settings, which the class must survive, are not simulated, so these are upper bounds on stability.

By `work/checks/stage3_p2_power_w.py` (`power-v1.json` sha256 547b8ffe3bd15496…); 1,000 simulated blocks per cell, 1,000 bootstrap replicates each.

## Assumptions
- **d:** 48 RM payloads (24 routine, 24 middle), 2 followers, 3 planted repeats per prompt.
  - Unwarned rate per payload q ~ Beta(mean 0.8, concentration 0.49), the core's spread. Warned = q x (1 - r), with r set so the mean fall is the row's delta. Both followers share the rates.
  - The model only lowers uptake, so the +0.10 row is the same as no change; U5 there is chance.
- **Work:** completion on the clean arm (56 payloads) and the benign arm (16).
  - Unwarned per payload ~ Beta(mean 0.96, concentration 4), from the 13 Nov clean-arm level 0.964. Warned = unwarned + delta, clipped.
  - The registered clause: lowered if either measure's upper bound is below 0; excluded if both lower bounds are above -0.10; otherwise not resolved.

## Uptake class by true mean change in RM uptake (delta)

| delta | U1 | U2a | U2b | U3 | U4 | U5 |
|---|---|---|---|---|---|---|
| 0.0 | 0.000 | 0.037 | 0.000 | 0.933 | 0.000 | 0.030 |
| -0.05 | 0.000 | 0.598 | 0.014 | 0.388 | 0.000 | 0.000 |
| -0.1 | 0.000 | 0.503 | 0.458 | 0.038 | 0.001 | 0.000 |
| -0.15 | 0.025 | 0.040 | 0.934 | 0.001 | 0.000 | 0.000 |
| -0.2 | 0.376 | 0.000 | 0.624 | 0.000 | 0.000 | 0.000 |
| -0.25 | 0.878 | 0.000 | 0.122 | 0.000 | 0.000 | 0.000 |
| -0.3 | 0.989 | 0.000 | 0.011 | 0.000 | 0.000 | 0.000 |
| -0.4 | 1.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 0.1 | 0.000 | 0.039 | 0.000 | 0.918 | 0.000 | 0.043 |

## Work clause by true change in completion (delta, both arms)

| delta | lowered | 0.10 fall excluded | not resolved |
|---|---|---|---|
| 0.0 | 0.049 | 0.893 | 0.058 |
| -0.02 | 0.395 | 0.530 | 0.075 |
| -0.05 | 0.893 | 0.074 | 0.033 |
| -0.1 | 0.999 | 0.000 | 0.001 |
| -0.15 | 1.000 | 0.000 | 0.000 |
| -0.2 | 1.000 | 0.000 | 0.000 |

With no true change, "lowered" comes up in 4.9 percent of draws: two measures, each with a 2.5 percent upper tail.
