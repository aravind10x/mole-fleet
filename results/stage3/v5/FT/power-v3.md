# Follower test: power simulation v3, the final decision tree of pre-registration v1.2 (blue harness; $0)

Record: `power-v3.json` (sha256 `8610b69cdadfdffa…`), by `work/checks/stage3_ft_power.py` (`simulate_tree`). Each simulated study is decided by the analysis's own `stage3_ft_join.decide_reading` and `decide_final`: the reading on the 50:50 mixture, and the same tree on each follower's own quantities for the followers-differ rate. 1000 studies per scenario, 500 bootstrap replicates (the analysis uses 2,000), seed 20261113.

## Assumptions (labelled)

- 56 payloads (routine 24, middle 24, alarming 8), r = 3, two followers. Per follower and payload, true uptake ~ Beta(u x 4.0, (1 - u) x 4.0), independent across followers.
- A clean-arm false-positive rate f fires on clean runs, and on planted runs that would not otherwise satisfy the predicate.
- Missed by the composed view at the governing applications' recorded shares (routine 0.5833, middle 0.2917, alarming 0.0). Identical states on 0.833 of RM payloads (40 of 48). Both independent of uptake.
- Unresolved runs at rate rho. Gate 2 as v1.2 section 4: the whole pipeline, gate 1 included, under each completion of every unresolved run, clean and planted. Gate 1: 3 or more of a follower's 144 RM clean runs, or 2 or more of its 24 AL clean runs, withhold. Every block complete.

## The three figures section 3 needs (reading (a) on the mixture; equal followers; no unresolved runs)

| clean false-positive rate f | (a) at true uptake 0.05 | power of (a) at 0.20 | power of (a) at 0.30 |
|---|---|---|---|
| 0.00 | 0.000 | 0.832 | 0.989 |
| 0.01 | 0.000 | 0.594 | 0.652 |
| 0.02 | 0.000 | 0.163 | 0.184 |
| 0.05 | 0.000 | 0.000 | 0.000 |

## The rate of every branch, every scenario

`clean bounded: no` rows are a labelled sensitivity, not the rule: planted runs completed both ways, gate 1 on resolved clean runs.

| scenario | Kimi RM | Sol RM | AL | f | rho | clean bounded | (a) | (e) | (d) | (b) | (c) | inconclusive | withheld: gate 1 | withheld: gate 2 | followers differ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| equal | 0.05 | 0.05 | 0.05 | 0.00 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.37 | 0.63 | 0.00 | 0.00 | 0.33 |
| equal | 0.05 | 0.05 | 0.05 | 0.01 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.16 | 0.49 | 0.35 | 0.00 | 0.47 |
| equal | 0.05 | 0.05 | 0.05 | 0.02 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 0.13 | 0.84 | 0.00 | 0.51 |
| equal | 0.05 | 0.05 | 0.05 | 0.05 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 |
| equal, 2% unresolved | 0.05 | 0.05 | 0.05 | 0.00 | 0.020 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.09 | 0.00 | 0.90 | 0.45 |
| equal, unresolved, clean not bounded | 0.05 | 0.05 | 0.05 | 0.00 | 0.005 | no | 0.00 | 0.00 | 0.00 | 0.00 | 0.35 | 0.59 | 0.00 | 0.06 | 0.38 |
| equal, unresolved, clean not bounded | 0.05 | 0.05 | 0.05 | 0.00 | 0.020 | no | 0.00 | 0.00 | 0.00 | 0.00 | 0.12 | 0.60 | 0.00 | 0.28 | 0.39 |
| equal | 0.10 | 0.10 | 0.10 | 0.00 | 0.000 | yes | 0.01 | 0.01 | 0.00 | 0.00 | 0.00 | 0.97 | 0.00 | 0.00 | 0.05 |
| equal | 0.10 | 0.10 | 0.10 | 0.01 | 0.000 | yes | 0.03 | 0.01 | 0.01 | 0.00 | 0.00 | 0.61 | 0.35 | 0.00 | 0.37 |
| equal | 0.10 | 0.10 | 0.10 | 0.02 | 0.000 | yes | 0.01 | 0.00 | 0.01 | 0.00 | 0.00 | 0.15 | 0.83 | 0.00 | 0.49 |
| equal | 0.10 | 0.10 | 0.10 | 0.05 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.03 |
| equal, 2% unresolved | 0.10 | 0.10 | 0.10 | 0.00 | 0.020 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.14 | 0.00 | 0.85 | 0.47 |
| equal, unresolved, clean not bounded | 0.10 | 0.10 | 0.10 | 0.00 | 0.005 | no | 0.01 | 0.00 | 0.01 | 0.00 | 0.00 | 0.95 | 0.00 | 0.03 | 0.09 |
| equal, unresolved, clean not bounded | 0.10 | 0.10 | 0.10 | 0.00 | 0.020 | no | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.84 | 0.00 | 0.14 | 0.17 |
| equal | 0.20 | 0.20 | 0.20 | 0.00 | 0.000 | yes | 0.83 | 0.10 | 0.04 | 0.00 | 0.00 | 0.02 | 0.00 | 0.00 | 0.51 |
| equal | 0.20 | 0.20 | 0.20 | 0.01 | 0.000 | yes | 0.59 | 0.05 | 0.02 | 0.00 | 0.00 | 0.01 | 0.33 | 0.00 | 0.56 |
| equal | 0.20 | 0.20 | 0.20 | 0.02 | 0.000 | yes | 0.16 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.82 | 0.00 | 0.52 |
| equal | 0.20 | 0.20 | 0.20 | 0.05 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.04 |
| equal, 2% unresolved | 0.20 | 0.20 | 0.20 | 0.00 | 0.020 | yes | 0.13 | 0.02 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.85 | 0.51 |
| equal, unresolved, clean not bounded | 0.20 | 0.20 | 0.20 | 0.00 | 0.005 | no | 0.84 | 0.10 | 0.03 | 0.00 | 0.00 | 0.01 | 0.00 | 0.02 | 0.50 |
| equal, unresolved, clean not bounded | 0.20 | 0.20 | 0.20 | 0.00 | 0.020 | no | 0.82 | 0.06 | 0.02 | 0.00 | 0.00 | 0.00 | 0.00 | 0.09 | 0.53 |
| equal | 0.30 | 0.30 | 0.30 | 0.00 | 0.000 | yes | 0.99 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.07 |
| equal | 0.30 | 0.30 | 0.30 | 0.01 | 0.000 | yes | 0.65 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.34 | 0.00 | 0.35 |
| equal | 0.30 | 0.30 | 0.30 | 0.02 | 0.000 | yes | 0.18 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.82 | 0.00 | 0.48 |
| equal | 0.30 | 0.30 | 0.30 | 0.05 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 1.00 | 0.00 | 0.02 |
| equal, 2% unresolved | 0.30 | 0.30 | 0.30 | 0.00 | 0.020 | yes | 0.17 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.83 | 0.48 |
| equal, unresolved, clean not bounded | 0.30 | 0.30 | 0.30 | 0.00 | 0.005 | no | 0.99 | 0.01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.06 |
| equal, unresolved, clean not bounded | 0.30 | 0.30 | 0.30 | 0.00 | 0.020 | no | 0.99 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.07 |
| followers differ | 0.10 | 0.30 | 0.10 | 0.00 | 0.000 | yes | 0.84 | 0.11 | 0.04 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.99 |
| followers differ | 0.10 | 0.30 | 0.10 | 0.01 | 0.000 | yes | 0.58 | 0.06 | 0.02 | 0.00 | 0.00 | 0.00 | 0.34 | 0.00 | 0.95 |
| followers differ | 0.30 | 0.10 | 0.30 | 0.00 | 0.000 | yes | 0.84 | 0.12 | 0.03 | 0.00 | 0.00 | 0.01 | 0.00 | 0.00 | 0.99 |
| followers differ | 0.30 | 0.10 | 0.30 | 0.01 | 0.000 | yes | 0.58 | 0.06 | 0.02 | 0.00 | 0.00 | 0.00 | 0.34 | 0.00 | 0.94 |
| followers differ | 0.05 | 0.30 | 0.05 | 0.00 | 0.000 | yes | 0.70 | 0.15 | 0.07 | 0.00 | 0.00 | 0.09 | 0.00 | 0.00 | 1.00 |
| followers differ | 0.05 | 0.30 | 0.05 | 0.01 | 0.000 | yes | 0.50 | 0.08 | 0.04 | 0.00 | 0.00 | 0.03 | 0.35 | 0.00 | 0.96 |
| alarming only | 0.05 | 0.05 | 0.80 | 0.00 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.82 | 0.00 | 0.18 | 0.00 | 0.00 | 0.50 |
| alarming only | 0.05 | 0.05 | 0.80 | 0.01 | 0.000 | yes | 0.00 | 0.00 | 0.00 | 0.41 | 0.00 | 0.24 | 0.36 | 0.00 | 0.64 |

## Limits

- A calibration at these points, not over the whole decision boundary.
- Followers' payload effects are independent here; if the same payloads are hard for both, per-follower intervals are wider.
- Missed, identical state and uptake are independent here.
