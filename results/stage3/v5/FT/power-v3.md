# Follower test: power simulation v3, the final decision tree (blue harness; $0)

Record: `power-v3.json` (sha256 `3885f5437c5ed4b4…`), by `work/checks/stage3_ft_power.py` (`simulate_tree`), which decides each simulated study with the analysis's own `stage3_ft_join.decide_reading` and `decide_final`. 1000 studies per scenario, 500 bootstrap replicates (the analysis uses 2,000), seed 20261113.

## Assumptions (labelled)

- 56 payloads (routine 24, middle 24, alarming 8), r = 3, two followers. Per follower and payload, true uptake ~ Beta(u x 4.0, (1 - u) x 4.0), independent across followers.
- A clean-arm false-positive rate f fires on clean runs, and on planted runs that would not otherwise satisfy the predicate.
- Missed by the composed view at the governing applications' recorded shares (routine 0.5833, middle 0.2917, alarming 0.0); identical states on 0.833 of RM payloads (40 of 48, from v1.1 section 2); both independent of uptake.
- Unresolved runs at rate rho, bounded both ways (gate 2). Gate 1 as section 4: 3 or more of a follower's 144 RM clean runs, or 2 or more of its 24 AL clean runs, withhold the reading. Every block complete.

## The three figures section 3 needs (reading (a) exactly; all (a) forms beside)

| clean false-positive rate f | (a) at true uptake 0.05 | any (a) form at 0.05 | power of (a) at 0.20 | at 0.30 |
|---|---|---|---|---|
| 0.00 | 0.000 | 0.000 | 0.829 | 0.989 |
| 0.01 | 0.000 | 0.000 | 0.593 | 0.652 |
| 0.02 | 0.000 | 0.000 | 0.163 | 0.184 |
| 0.05 | 0.000 | 0.000 | 0.000 | 0.000 |

## Every scenario

| scenario | Kimi RM | Sol RM | AL | f | rho | clean bounded | (a) | (a) K | (a) S | (a) unset. | (d) | (b) | (c) | inc. | inc. unres. | withheld (gate 1) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| equal | 0.05 | 0.05 | 0.05 | 0.00 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 | 0.95 | 0.00 | 0.00 |
| equal | 0.05 | 0.05 | 0.05 | 0.01 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.64 | 0.00 | 0.35 |
| equal | 0.05 | 0.05 | 0.05 | 0.02 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.16 | 0.00 | 0.84 |
| equal | 0.05 | 0.05 | 0.05 | 0.05 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| equal, 2% unresolved | 0.05 | 0.05 | 0.05 | 0.00 | 0.020 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.13 | 0.87 | 0.00 |
| equal, unresolved, clean not bounded | 0.05 | 0.05 | 0.05 | 0.00 | 0.005 | no | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 0.95 | 0.02 | 0.00 |
| equal, unresolved, clean not bounded | 0.05 | 0.05 | 0.05 | 0.00 | 0.020 | no | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.94 | 0.06 | 0.00 |
| equal | 0.10 | 0.10 | 0.10 | 0.00 | 0.000 | yes | 0.01 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.00 | 0.97 | 0.00 | 0.00 |
| equal | 0.10 | 0.10 | 0.10 | 0.01 | 0.000 | yes | 0.03 | 0.00 | 0.00 | 0.01 | 0.01 | 0.00 | 0.00 | 0.61 | 0.00 | 0.35 |
| equal | 0.10 | 0.10 | 0.10 | 0.02 | 0.000 | yes | 0.01 | 0.00 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.15 | 0.00 | 0.83 |
| equal | 0.10 | 0.10 | 0.10 | 0.05 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| equal, 2% unresolved | 0.10 | 0.10 | 0.10 | 0.00 | 0.020 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.14 | 0.85 | 0.00 |
| equal, unresolved, clean not bounded | 0.10 | 0.10 | 0.10 | 0.00 | 0.005 | no | 0.01 | 0.00 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.95 | 0.03 | 0.00 |
| equal, unresolved, clean not bounded | 0.10 | 0.10 | 0.10 | 0.00 | 0.020 | no | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.85 | 0.13 | 0.00 |
| equal | 0.20 | 0.20 | 0.20 | 0.00 | 0.000 | yes | 0.83 | 0.00 | 0.00 | 0.10 | 0.04 | 0.00 | 0.00 | 0.02 | 0.00 | 0.00 |
| equal | 0.20 | 0.20 | 0.20 | 0.01 | 0.000 | yes | 0.59 | 0.00 | 0.00 | 0.05 | 0.02 | 0.00 | 0.00 | 0.01 | 0.00 | 0.33 |
| equal | 0.20 | 0.20 | 0.20 | 0.02 | 0.000 | yes | 0.16 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.82 |
| equal | 0.20 | 0.20 | 0.20 | 0.05 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| equal, 2% unresolved | 0.20 | 0.20 | 0.20 | 0.00 | 0.020 | yes | 0.13 | 0.00 | 0.00 | 0.02 | 0.00 | 0.00 | 0.00 | 0.00 | 0.85 | 0.00 |
| equal, unresolved, clean not bounded | 0.20 | 0.20 | 0.20 | 0.00 | 0.005 | no | 0.84 | 0.00 | 0.00 | 0.10 | 0.03 | 0.00 | 0.00 | 0.01 | 0.03 | 0.00 |
| equal, unresolved, clean not bounded | 0.20 | 0.20 | 0.20 | 0.00 | 0.020 | no | 0.82 | 0.00 | 0.00 | 0.06 | 0.02 | 0.00 | 0.00 | 0.00 | 0.10 | 0.00 |
| equal | 0.30 | 0.30 | 0.30 | 0.00 | 0.000 | yes | 0.99 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| equal | 0.30 | 0.30 | 0.30 | 0.01 | 0.000 | yes | 0.65 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.34 |
| equal | 0.30 | 0.30 | 0.30 | 0.02 | 0.000 | yes | 0.18 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.82 |
| equal | 0.30 | 0.30 | 0.30 | 0.05 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 |
| equal, 2% unresolved | 0.30 | 0.30 | 0.30 | 0.00 | 0.020 | yes | 0.17 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.83 | 0.00 |
| equal, unresolved, clean not bounded | 0.30 | 0.30 | 0.30 | 0.00 | 0.005 | no | 0.99 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| equal, unresolved, clean not bounded | 0.30 | 0.30 | 0.30 | 0.00 | 0.020 | no | 0.99 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.00 |
| followers differ | 0.10 | 0.30 | 0.10 | 0.00 | 0.000 | yes | 0.40 | 0.00 | 0.45 | 0.11 | 0.04 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 |
| followers differ | 0.10 | 0.30 | 0.10 | 0.01 | 0.000 | yes | 0.36 | 0.00 | 0.21 | 0.06 | 0.02 | 0.00 | 0.00 | 0.00 | 0.00 | 0.34 |
| followers differ | 0.30 | 0.10 | 0.30 | 0.00 | 0.000 | yes | 0.41 | 0.43 | 0.00 | 0.12 | 0.03 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 |
| followers differ | 0.30 | 0.10 | 0.30 | 0.01 | 0.000 | yes | 0.36 | 0.22 | 0.00 | 0.06 | 0.02 | 0.00 | 0.00 | 0.00 | 0.00 | 0.34 |
| followers differ | 0.05 | 0.30 | 0.05 | 0.00 | 0.000 | yes | 0.01 | 0.00 | 0.68 | 0.15 | 0.07 | 0.00 | 0.00 | 0.09 | 0.00 | 0.00 |
| followers differ | 0.05 | 0.30 | 0.05 | 0.01 | 0.000 | yes | 0.03 | 0.00 | 0.48 | 0.08 | 0.04 | 0.00 | 0.00 | 0.03 | 0.00 | 0.35 |
| alarming only | 0.05 | 0.05 | 0.80 | 0.00 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.82 | 0.00 | 0.18 | 0.00 | 0.00 |
| alarming only | 0.05 | 0.05 | 0.80 | 0.01 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.41 | 0.00 | 0.24 | 0.00 | 0.36 |

## Limits

- A calibration at these points, not over the whole decision boundary.
- Followers' payload effects are independent here; if the same payloads are hard for both, per-follower intervals are wider.
- Missed, identical state and uptake are independent here.
