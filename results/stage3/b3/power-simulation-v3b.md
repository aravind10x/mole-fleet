**Adopted layout (A6.13): T2+S2, readable.** Carried by form (a) on dossier_iso:opus48 (the carrier); P(excluded | 0) 0.96, P(excluded | margin) 0.00, P(LB > 0 | 0) 0.04, P(present | 1.5 × margin) 0.96 (worse ICC, 5-point noise); combined verdict P(holds | 0) 0.96, P(falsified | 0) 0.00, P(holds | margin) 0.00, P(falsified | margin) 0.24.

Brief 20 Part 2 (brief 15 A6.13; $0; `work/checks/stage3_b3_power_v3.py` 5b33dcef8d59…, simulation, joint run and report from one script and inputs: True; seed 20261171; 300 experiments per cell; payload-clustered percentile bootstrap, 1000 replicates). The first run under A6.6's original gate stays in the record: `work/stage3/b3/power-simulation-v3.md` a2ca0044…, `work/stage3/b3/power-simulation-v3.json` 953e91b9…. Inputs are files on disk and none is a B3 outcome; counts, ids and aggregates only.

## Summary

- **Adoption:** the carrier dossier_iso:opus48|a is readable at T2+S2, T2+S1, T1+S2, T1+S1 (the second named instrument at T1+S1, T2+S1, T1+S2, T2+S2; it never carries at adoption, only in an experiment where the carrier is at floor or unfit). Candidates in order of P(excluded | 0) + P(present | 1.5 × margin), with A6.6's residual-bias trigger: T2+S2: eligible. Final: T2+S2, readable.
- **Readable cells under A6.13.1 (5-point noise, worse ICC; form (a) on the live dossiers left out, not applicable under A6.13.3):** T1: dossier_live:sonnet (b, descriptive); T2: P_author:sonnet (b, descriptive); T1+S1: P_author:opus48 (a, second), P_author:opus48 (b, supporting), P_author:sonnet (a, descriptive), dossier_iso:opus48 (a, carrier), dossier_iso:opus48 (b, supporting), dossier_iso:sonnet (a, descriptive); T2+S1: P_author:opus48 (a, second), P_author:sonnet (a, descriptive), P_author:sonnet (b, descriptive), dossier_iso:opus48 (a, carrier), dossier_iso:sonnet (a, descriptive); T1+S2: P_author:opus48 (a, second), P_author:opus48 (b, supporting), P_author:sonnet (a, descriptive), dossier_iso:opus48 (a, carrier), dossier_iso:opus48 (b, supporting), dossier_iso:sonnet (a, descriptive), dossier_iso:sonnet (b, descriptive), dossier_live:sonnet (b, descriptive); T2+S2: P_author:opus48 (a, second), P_author:opus48 (b, supporting), P_author:sonnet (a, descriptive), P_author:sonnet (b, descriptive), dossier_iso:opus48 (a, carrier), dossier_iso:opus48 (b, supporting), dossier_iso:sonnet (a, descriptive), dossier_live:sonnet (b, descriptive).
- **One latent margin (A6.13.2):** m_s for the carrier 18.22 (was 32.00); second 19.37 (was 50.00). Full table below.
- **Residual null bias (5-point noise):** (b) above 0.05 at: P_author:opus48|b|T1+S1, P_author:opus48|b|T2+S1, P_author:sonnet|b|T1+S1, P_author:sonnet|b|T2+S1, dossier_iso:opus48|b|T1+S1, dossier_iso:opus48|b|T2+S1, dossier_iso:sonnet|b|T1+S1, dossier_iso:sonnet|b|T2+S1, dossier_live:sonnet|b|T1+S1, dossier_live:sonnet|b|T2+S1; (a) above half of m_s at: none.
- **Ceiling clause:** (b) not read in most experiments (quiet lone recall above 0.85) for: dossier_live:opus48|b.
- **Estimate (P4, unchanged):** T2+S2 $98.17 (stop at $196.35); every layout in the P4 table below.

## m_s under A6.13.2 (old rule beside, superseded)

The latent margin β* is form (b)'s β_b at the reference cell (ICC 0.3, 5-point call noise): the latent composition effect at which (b)'s 75-minus-50 contrast, with the judge's true line maximum at its mean, is 0.3. m_s is form (a)'s error-free coefficient × 25 at β* (excess on true composition with form (a)'s covariates, one singleton placement). Both forms' alternatives are this same latent effect. Beside: each form's error-free reading of β* in the other ICC and singleton cells at 5-point noise (the drift from the reference; the 0- and 10-point drift is in the JSON, `margins.<instrument>.drift`).

| view, judge | β* × 25 | **m_s (A6.13.2)** | m_s old (A6.4, superseded) | old rule | (a) × 25 at β*: ICC 0.3 S2; ICC 0.6 S1 / S2 | (b) contrast at β*: ICC 0.6; at 1.5 β*: ICC 0.3 / 0.6 |
|---|---|---|---|---|---|---|
| dossier_iso:opus48 | 21.5 | **18.22** | 32.00 | primary | 18.30; 17.93 / 18.07 | 0.363; 0.415 / 0.482 |
| dossier_iso:sonnet | 26.8 | **19.07** | 11.00 | primary | 19.12; 18.72 / 18.80 | 0.384; 0.434 / 0.542 |
| dossier_live:opus48 | 77.7 | **46.76** | 9.36 | fallback | 46.06; 44.99 / 44.48 | 0.263; 0.473 / 0.481 |
| dossier_live:sonnet | 31.9 | **20.23** | 53.00 | primary | 20.21; 19.73 / 19.62 | 0.371; 0.420 / 0.498 |
| P_author:opus48 | 24.8 | **19.37** | 50.00 | primary | 19.41; 19.01 / 18.94 | 0.362; 0.415 / 0.480 |
| P_author:sonnet | 32.1 | **22.47** | 13.00 | primary | 22.32; 21.69 / 21.58 | 0.335; 0.469 / 0.544 |

## The gate under A6.13.1 (5-point call noise; worse of ICC 0.3 and 0.6, both shown)

Readable: P(excluded | 0) ≥ 0.6 (power to confirm P-max), P(excluded | margin) ≤ 0.10 (false confirmation), P(LB > 0 | 0) ≤ 0.10 (false refutation). P(present | 1.5 × margin) beside: the ability to label a large effect. Readings not read (floor, unfit, (b)'s ceiling) count as neither *excluded* nor LB > 0; their share is shown. Form (b): Firth fit and the ceiling clause. Role from A6.13.3; descriptive cells carry no verdict. Monte Carlo SE at 300 experiments: about 0.017 at 0.10, 0.028 at 0.6.

| view, judge | form | role | layout | P(excl \| 0) (0.3 / 0.6) | P(excl \| margin) (0.3 / 0.6) | P(LB > 0 \| 0) (0.3 / 0.6) | P(present \| 1.5×) | not read \| 0 / \| margin | readable |
|---|---|---|---|---|---|---|---|---|---|
| dossier_iso:opus48 | (a) | carrier | T1+S1 | 0.93 (0.93 / 0.96) | 0.04 (0.04 / 0.01) | 0.04 (0.02 / 0.04) | 0.91 | 0.00 / 0.00 | **yes** |
| dossier_iso:opus48 | (a) | carrier | T2+S1 | 0.96 (0.96 / 0.97) | 0.01 (0.01 / 0.00) | 0.04 (0.04 / 0.03) | 0.93 | 0.00 / 0.00 | **yes** |
| dossier_iso:opus48 | (a) | carrier | T1+S2 | 0.95 (0.95 / 0.99) | 0.04 (0.04 / 0.01) | 0.02 (0.02 / 0.01) | 0.91 | 0.00 / 0.00 | **yes** |
| dossier_iso:opus48 | (a) | carrier | T2+S2 | 0.96 (0.98 / 0.96) | 0.00 (0.00 / 0.00) | 0.04 (0.02 / 0.04) | 0.96 | 0.00 / 0.00 | **yes** |
| P_author:opus48 | (a) | second | T1+S1 | 0.85 (0.85 / 0.97) | 0.05 (0.05 / 0.02) | 0.04 (0.04 / 0.02) | 0.87 | 0.00 / 0.00 | **yes** |
| P_author:opus48 | (a) | second | T2+S1 | 0.95 (0.95 / 0.98) | 0.01 (0.01 / 0.00) | 0.04 (0.04 / 0.02) | 0.87 | 0.00 / 0.00 | **yes** |
| P_author:opus48 | (a) | second | T1+S2 | 0.94 (0.94 / 0.97) | 0.02 (0.02 / 0.01) | 0.03 (0.03 / 0.03) | 0.89 | 0.00 / 0.00 | **yes** |
| P_author:opus48 | (a) | second | T2+S2 | 0.96 (0.97 / 0.96) | 0.01 (0.01 / 0.00) | 0.04 (0.03 / 0.04) | 0.94 | 0.00 / 0.00 | **yes** |
| P_author:opus48 | (b) | supporting | T1 | 0.71 (0.71 / 0.80) | 0.11 (0.11 / 0.08) | 0.05 (0.05 / 0.01) | 0.52 | 0.00 / 0.00 | no |
| P_author:opus48 | (b) | supporting | T2 | 0.88 (0.90 / 0.88) | 0.13 (0.10 / 0.13) | 0.03 (0.03 / 0.03) | 0.42 | 0.00 / 0.00 | no |
| P_author:opus48 | (b) | supporting | T1+S1 | 0.71 (0.76 / 0.71) | 0.04 (0.04 / 0.01) | 0.09 (0.08 / 0.09) | 0.72 | 0.00 / 0.01 | **yes** |
| P_author:opus48 | (b) | supporting | T2+S1 | 0.86 (0.86 / 0.88) | 0.01 (0.01 / 0.00) | 0.13 (0.13 / 0.08) | 0.79 | 0.00 / 0.00 | no |
| P_author:opus48 | (b) | supporting | T1+S2 | 0.75 (0.78 / 0.75) | 0.04 (0.04 / 0.03) | 0.08 (0.08 / 0.05) | 0.70 | 0.00 / 0.01 | **yes** |
| P_author:opus48 | (b) | supporting | T2+S2 | 0.86 (0.92 / 0.86) | 0.01 (0.01 / 0.00) | 0.09 (0.07 / 0.09) | 0.80 | 0.00 / 0.00 | **yes** |
| dossier_iso:opus48 | (b) | supporting | T1 | 0.71 (0.76 / 0.71) | 0.11 (0.11 / 0.10) | 0.04 (0.03 / 0.04) | 0.43 | 0.01 / 0.01 | no |
| dossier_iso:opus48 | (b) | supporting | T2 | 0.90 (0.93 / 0.90) | 0.16 (0.15 / 0.16) | 0.02 (0.02 / 0.02) | 0.39 | 0.00 / 0.00 | no |
| dossier_iso:opus48 | (b) | supporting | T1+S1 | 0.74 (0.75 / 0.74) | 0.07 (0.07 / 0.04) | 0.08 (0.07 / 0.08) | 0.65 | 0.01 / 0.02 | **yes** |
| dossier_iso:opus48 | (b) | supporting | T2+S1 | 0.83 (0.83 / 0.88) | 0.03 (0.03 / 0.03) | 0.15 (0.15 / 0.09) | 0.74 | 0.00 / 0.00 | no |
| dossier_iso:opus48 | (b) | supporting | T1+S2 | 0.78 (0.80 / 0.78) | 0.05 (0.05 / 0.05) | 0.06 (0.05 / 0.06) | 0.60 | 0.00 / 0.01 | **yes** |
| dossier_iso:opus48 | (b) | supporting | T2+S2 | 0.92 (0.92 / 0.93) | 0.03 (0.03 / 0.03) | 0.07 (0.07 / 0.05) | 0.64 | 0.00 / 0.00 | **yes** |
| P_author:sonnet | (a) | descriptive | T1+S1 | 0.94 (0.94 / 0.98) | 0.03 (0.03 / 0.01) | 0.02 (0.02 / 0.02) | 0.81 | 0.00 / 0.00 | **yes** |
| P_author:sonnet | (a) | descriptive | T2+S1 | 0.97 (0.97 / 0.97) | 0.00 (0.00 / 0.00) | 0.03 (0.02 / 0.03) | 0.81 | 0.00 / 0.00 | **yes** |
| P_author:sonnet | (a) | descriptive | T1+S2 | 0.96 (0.96 / 0.96) | 0.02 (0.02 / 0.01) | 0.04 (0.03 / 0.04) | 0.84 | 0.00 / 0.00 | **yes** |
| P_author:sonnet | (a) | descriptive | T2+S2 | 0.96 (0.96 / 0.97) | 0.00 (0.00 / 0.00) | 0.04 (0.04 / 0.03) | 0.88 | 0.00 / 0.00 | **yes** |
| P_author:sonnet | (b) | descriptive | T1 | 0.47 (0.47 / 0.54) | 0.09 (0.09 / 0.07) | 0.03 (0.03 / 0.02) | 0.50 | 0.24 / 0.14 | no |
| P_author:sonnet | (b) | descriptive | T2 | 0.72 (0.80 / 0.72) | 0.09 (0.09 / 0.07) | 0.04 (0.04 / 0.02) | 0.58 | 0.04 / 0.02 | **yes** |
| P_author:sonnet | (b) | descriptive | T1+S1 | 0.47 (0.47 / 0.50) | 0.04 (0.04 / 0.04) | 0.08 (0.08 / 0.06) | 0.67 | 0.26 / 0.13 | no |
| P_author:sonnet | (b) | descriptive | T2+S1 | 0.74 (0.77 / 0.74) | 0.01 (0.01 / 0.00) | 0.10 (0.10 / 0.09) | 0.81 | 0.07 / 0.02 | **yes** |
| P_author:sonnet | (b) | descriptive | T1+S2 | 0.50 (0.50 / 0.56) | 0.02 (0.02 / 0.02) | 0.07 (0.07 / 0.05) | 0.60 | 0.25 / 0.19 | no |
| P_author:sonnet | (b) | descriptive | T2+S2 | 0.77 (0.80 / 0.77) | 0.03 (0.03 / 0.03) | 0.09 (0.09 / 0.04) | 0.78 | 0.07 / 0.01 | **yes** |
| dossier_iso:sonnet | (a) | descriptive | T1+S1 | 0.89 (0.89 / 0.96) | 0.04 (0.04 / 0.03) | 0.03 (0.03 / 0.03) | 0.87 | 0.00 / 0.00 | **yes** |
| dossier_iso:sonnet | (a) | descriptive | T2+S1 | 0.95 (0.95 / 0.98) | 0.03 (0.03 / 0.01) | 0.03 (0.03 / 0.02) | 0.89 | 0.00 / 0.00 | **yes** |
| dossier_iso:sonnet | (a) | descriptive | T1+S2 | 0.92 (0.92 / 0.97) | 0.04 (0.04 / 0.03) | 0.03 (0.03 / 0.03) | 0.90 | 0.00 / 0.00 | **yes** |
| dossier_iso:sonnet | (a) | descriptive | T2+S2 | 0.96 (0.96 / 0.98) | 0.02 (0.02 / 0.00) | 0.04 (0.04 / 0.02) | 0.90 | 0.00 / 0.00 | **yes** |
| dossier_iso:sonnet | (b) | descriptive | T1 | 0.55 (0.61 / 0.55) | 0.12 (0.09 / 0.12) | 0.04 (0.03 / 0.04) | 0.32 | 0.12 / 0.10 | no |
| dossier_iso:sonnet | (b) | descriptive | T2 | 0.84 (0.88 / 0.84) | 0.15 (0.15 / 0.13) | 0.03 (0.03 / 0.02) | 0.39 | 0.01 / 0.01 | no |
| dossier_iso:sonnet | (b) | descriptive | T1+S1 | 0.53 (0.63 / 0.53) | 0.04 (0.04 / 0.03) | 0.07 (0.07 / 0.06) | 0.54 | 0.13 / 0.11 | no |
| dossier_iso:sonnet | (b) | descriptive | T2+S1 | 0.81 (0.86 / 0.81) | 0.04 (0.04 / 0.03) | 0.12 (0.12 / 0.07) | 0.70 | 0.01 / 0.01 | no |
| dossier_iso:sonnet | (b) | descriptive | T1+S2 | 0.60 (0.60 / 0.60) | 0.04 (0.02 / 0.04) | 0.06 (0.06 / 0.06) | 0.53 | 0.10 / 0.10 | **yes** |
| dossier_iso:sonnet | (b) | descriptive | T2+S2 | 0.84 (0.84 / 0.84) | 0.05 (0.05 / 0.04) | 0.11 (0.11 / 0.06) | 0.62 | 0.01 / 0.01 | no |
| dossier_live:opus48 | (a) | n/a (live view, A6.13.3) | T1+S1 | 0.96 (0.96 / 0.98) | 0.00 (0.00 / 0.00) | 0.04 (0.04 / 0.02) | 0.20 | 0.00 / 0.00 | **yes** |
| dossier_live:opus48 | (a) | n/a (live view, A6.13.3) | T2+S1 | 0.97 (0.97 / 0.98) | 0.00 (0.00 / 0.00) | 0.03 (0.03 / 0.02) | 0.20 | 0.00 / 0.00 | **yes** |
| dossier_live:opus48 | (a) | n/a (live view, A6.13.3) | T1+S2 | 0.97 (0.97 / 0.97) | 0.00 (0.00 / 0.00) | 0.03 (0.03 / 0.03) | 0.16 | 0.00 / 0.00 | **yes** |
| dossier_live:opus48 | (a) | n/a (live view, A6.13.3) | T2+S2 | 0.94 (0.94 / 0.97) | 0.00 (0.00 / 0.00) | 0.06 (0.06 / 0.03) | 0.19 | 0.00 / 0.00 | **yes** |
| dossier_live:opus48 | (b) | descriptive | T1 | 0.07 (0.09 / 0.07) | 0.00 (0.00 / 0.00) | 0.01 (0.01 / 0.00) | 0.31 | 0.93 / 0.52 | no |
| dossier_live:opus48 | (b) | descriptive | T2 | 0.03 (0.03 / 0.03) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.65 | 0.97 / 0.02 | no |
| dossier_live:opus48 | (b) | descriptive | T1+S1 | 0.08 (0.09 / 0.08) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.31 | 0.92 / 0.58 | no |
| dossier_live:opus48 | (b) | descriptive | T2+S1 | 0.01 (0.01 / 0.01) | 0.00 (0.00 / 0.00) | 0.01 (0.00 / 0.01) | 0.72 | 0.98 / 0.02 | no |
| dossier_live:opus48 | (b) | descriptive | T1+S2 | 0.05 (0.10 / 0.05) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.26 | 0.95 / 0.66 | no |
| dossier_live:opus48 | (b) | descriptive | T2+S2 | 0.03 (0.03 / 0.04) | 0.00 (0.00 / 0.00) | 0.00 (0.00 / 0.00) | 0.75 | 0.97 / 0.04 | no |
| dossier_live:sonnet | (a) | n/a (live view, A6.13.3) | T1+S1 | 0.80 (0.80 / 0.97) | 0.04 (0.04 / 0.04) | 0.04 (0.04 / 0.02) | 0.82 | 0.00 / 0.00 | **yes** |
| dossier_live:sonnet | (a) | n/a (live view, A6.13.3) | T2+S1 | 0.93 (0.93 / 0.98) | 0.04 (0.04 / 0.02) | 0.02 (0.02 / 0.02) | 0.84 | 0.00 / 0.00 | **yes** |
| dossier_live:sonnet | (a) | n/a (live view, A6.13.3) | T1+S2 | 0.87 (0.87 / 0.96) | 0.06 (0.06 / 0.04) | 0.04 (0.04 / 0.03) | 0.81 | 0.00 / 0.00 | **yes** |
| dossier_live:sonnet | (a) | n/a (live view, A6.13.3) | T2+S2 | 0.96 (0.98 / 0.96) | 0.02 (0.02 / 0.00) | 0.04 (0.01 / 0.04) | 0.88 | 0.00 / 0.00 | **yes** |
| dossier_live:sonnet | (b) | descriptive | T1 | 0.73 (0.75 / 0.73) | 0.05 (0.05 / 0.05) | 0.03 (0.02 / 0.03) | 0.50 | 0.00 / 0.00 | **yes** |
| dossier_live:sonnet | (b) | descriptive | T2 | 0.84 (0.91 / 0.84) | 0.14 (0.14 / 0.08) | 0.04 (0.03 / 0.04) | 0.47 | 0.00 / 0.00 | no |
| dossier_live:sonnet | (b) | descriptive | T1+S1 | 0.63 (0.72 / 0.63) | 0.04 (0.04 / 0.02) | 0.12 (0.12 / 0.10) | 0.74 | 0.00 / 0.00 | no |
| dossier_live:sonnet | (b) | descriptive | T2+S1 | 0.80 (0.84 / 0.80) | 0.02 (0.01 / 0.02) | 0.13 (0.13 / 0.10) | 0.84 | 0.00 / 0.00 | no |
| dossier_live:sonnet | (b) | descriptive | T1+S2 | 0.67 (0.75 / 0.67) | 0.06 (0.06 / 0.03) | 0.08 (0.07 / 0.08) | 0.72 | 0.00 / 0.01 | **yes** |
| dossier_live:sonnet | (b) | descriptive | T2+S2 | 0.84 (0.91 / 0.84) | 0.01 (0.01 / 0.00) | 0.08 (0.08 / 0.07) | 0.83 | 0.00 / 0.00 | **yes** |

### The gate at 0 and 10 points of call noise (readable cells; worse ICC: P(excl | 0) / P(excl | margin) / P(LB > 0 | 0))

- 0 points: readable P_author:opus48|a|T1+S1 0.91 / 0.05 / 0.03, P_author:opus48|a|T1+S2 0.94 / 0.03 / 0.03, P_author:opus48|a|T2+S1 0.97 / 0.03 / 0.03, P_author:opus48|a|T2+S2 0.97 / 0.01 / 0.03, P_author:opus48|b|T1+S1 0.72 / 0.04 / 0.08, P_author:opus48|b|T1+S2 0.77 / 0.05 / 0.06, P_author:opus48|b|T2+S2 0.87 / 0.03 / 0.07, P_author:sonnet|a|T1+S1 0.94 / 0.05 / 0.04, P_author:sonnet|a|T1+S2 0.95 / 0.02 / 0.05, P_author:sonnet|a|T2+S1 0.96 / 0.00 / 0.04, P_author:sonnet|a|T2+S2 0.97 / 0.01 / 0.03, P_author:sonnet|b|T2 0.73 / 0.06 / 0.04, P_author:sonnet|b|T2+S1 0.74 / 0.04 / 0.09, P_author:sonnet|b|T2+S2 0.79 / 0.02 / 0.07, dossier_iso:opus48|a|T1+S1 0.93 / 0.04 / 0.04, dossier_iso:opus48|a|T1+S2 0.95 / 0.03 / 0.03, dossier_iso:opus48|a|T2+S1 0.96 / 0.03 / 0.03, dossier_iso:opus48|a|T2+S2 0.96 / 0.00 / 0.04, dossier_iso:opus48|b|T1+S1 0.70 / 0.07 / 0.09, dossier_iso:opus48|b|T1+S2 0.77 / 0.06 / 0.06, dossier_iso:opus48|b|T2+S2 0.89 / 0.04 / 0.10, dossier_iso:sonnet|a|T1+S1 0.87 / 0.04 / 0.03, dossier_iso:sonnet|a|T1+S2 0.90 / 0.03 / 0.04, dossier_iso:sonnet|a|T2+S1 0.95 / 0.02 / 0.05, dossier_iso:sonnet|a|T2+S2 0.96 / 0.01 / 0.04, dossier_iso:sonnet|b|T2+S2 0.82 / 0.06 / 0.09, dossier_live:sonnet|b|T1+S1 0.65 / 0.01 / 0.09, dossier_live:sonnet|b|T1+S2 0.67 / 0.04 / 0.07; the carrier at T2+S2: 0.96 / 0.00 / 0.04.
- 10 points: readable P_author:opus48|a|T1+S1 0.85 / 0.03 / 0.04, P_author:opus48|a|T1+S2 0.92 / 0.02 / 0.03, P_author:opus48|a|T2+S1 0.97 / 0.02 / 0.03, P_author:opus48|a|T2+S2 0.96 / 0.01 / 0.04, P_author:opus48|b|T1 0.76 / 0.10 / 0.04, P_author:opus48|b|T1+S2 0.75 / 0.04 / 0.07, P_author:opus48|b|T2+S1 0.87 / 0.02 / 0.09, P_author:sonnet|a|T1+S1 0.93 / 0.04 / 0.02, P_author:sonnet|a|T1+S2 0.96 / 0.02 / 0.03, P_author:sonnet|a|T2+S1 0.96 / 0.01 / 0.04, P_author:sonnet|a|T2+S2 0.96 / 0.01 / 0.04, P_author:sonnet|b|T2 0.73 / 0.10 / 0.04, P_author:sonnet|b|T2+S2 0.81 / 0.05 / 0.08, dossier_iso:opus48|a|T1+S1 0.93 / 0.04 / 0.05, dossier_iso:opus48|a|T1+S2 0.92 / 0.02 / 0.04, dossier_iso:opus48|a|T2+S1 0.96 / 0.02 / 0.04, dossier_iso:opus48|a|T2+S2 0.97 / 0.00 / 0.03, dossier_iso:opus48|b|T1+S1 0.69 / 0.04 / 0.10, dossier_iso:opus48|b|T1+S2 0.79 / 0.05 / 0.08, dossier_iso:opus48|b|T2+S2 0.92 / 0.04 / 0.06, dossier_iso:sonnet|a|T1+S1 0.84 / 0.04 / 0.04, dossier_iso:sonnet|a|T1+S2 0.91 / 0.05 / 0.04, dossier_iso:sonnet|a|T2+S1 0.95 / 0.03 / 0.04, dossier_iso:sonnet|a|T2+S2 0.97 / 0.01 / 0.03, dossier_iso:sonnet|b|T2+S2 0.83 / 0.05 / 0.09, dossier_live:sonnet|b|T1 0.68 / 0.10 / 0.02, dossier_live:sonnet|b|T1+S2 0.71 / 0.04 / 0.08; the carrier at T2+S2: 0.97 / 0.00 / 0.03.

## Residual null bias (A6.13.5: (b) trigger 0.05; (a) half of the new m_s)

Mean point estimate under the null over successful fits, the worse ICC; the Monte Carlo SE at 5 points beside. Positive (b) leans toward a false *present*.

| view, judge | form | layout | noise 0 | noise 5 (MC SE) | noise 10 | bound | material at 5 |
|---|---|---|---|---|---|---|---|
| dossier_iso:opus48 | (a) | T1+S1 | +0.582 | +0.738 (0.234) | +0.499 | 9.112 | no |
| dossier_iso:opus48 | (a) | T2+S1 | -0.229 | +0.414 (0.238) | +0.341 | 9.112 | no |
| dossier_iso:opus48 | (a) | T1+S2 | +0.480 | +0.164 (0.212) | +0.449 | 9.112 | no |
| dossier_iso:opus48 | (a) | T2+S2 | +0.298 | +0.402 (0.161) | +0.274 | 9.112 | no |
| dossier_iso:opus48 | (b) | T1 | +0.003 | +0.008 (0.007) | -0.008 | 0.050 | no |
| dossier_iso:opus48 | (b) | T2 | +0.007 | +0.003 (0.005) | -0.010 | 0.050 | no |
| dossier_iso:opus48 | (b) | T1+S1 | +0.054 | +0.058 (0.005) | +0.056 | 0.050 | **yes** |
| dossier_iso:opus48 | (b) | T2+S1 | +0.053 | +0.057 (0.004) | +0.058 | 0.050 | **yes** |
| dossier_iso:opus48 | (b) | T1+S2 | +0.034 | +0.039 (0.005) | +0.045 | 0.050 | no |
| dossier_iso:opus48 | (b) | T2+S2 | +0.043 | +0.040 (0.004) | +0.035 | 0.050 | no |
| dossier_iso:sonnet | (a) | T1+S1 | +0.370 | -0.508 (0.348) | +0.707 | 9.533 | no |
| dossier_iso:sonnet | (a) | T2+S1 | +0.557 | +0.514 (0.280) | +0.250 | 9.533 | no |
| dossier_iso:sonnet | (a) | T1+S2 | +0.782 | +0.716 (0.279) | +0.790 | 9.533 | no |
| dossier_iso:sonnet | (a) | T2+S2 | +0.035 | +0.460 (0.243) | +0.334 | 9.533 | no |
| dossier_iso:sonnet | (b) | T1 | +0.004 | +0.007 (0.007) | +0.006 | 0.050 | no |
| dossier_iso:sonnet | (b) | T2 | +0.002 | +0.003 (0.005) | +0.003 | 0.050 | no |
| dossier_iso:sonnet | (b) | T1+S1 | +0.057 | +0.054 (0.006) | +0.064 | 0.050 | **yes** |
| dossier_iso:sonnet | (b) | T2+S1 | +0.062 | +0.060 (0.004) | +0.059 | 0.050 | **yes** |
| dossier_iso:sonnet | (b) | T1+S2 | +0.055 | +0.049 (0.005) | +0.053 | 0.050 | no |
| dossier_iso:sonnet | (b) | T2+S2 | +0.044 | +0.050 (0.004) | +0.047 | 0.050 | no |
| dossier_live:opus48 | (a) | T1+S1 | +0.315 | +0.332 (0.232) | +0.117 | 23.382 | no |
| dossier_live:opus48 | (a) | T2+S1 | +0.445 | +0.214 (0.189) | +0.519 | 23.382 | no |
| dossier_live:opus48 | (a) | T1+S2 | +0.352 | +0.107 (0.222) | +0.261 | 23.382 | no |
| dossier_live:opus48 | (a) | T2+S2 | +0.197 | +0.164 (0.184) | +0.268 | 23.382 | no |
| dossier_live:opus48 | (b) | T1 | -0.013 | -0.016 (0.005) | -0.011 | 0.050 | no |
| dossier_live:opus48 | (b) | T2 | -0.001 | -0.004 (0.003) | -0.003 | 0.050 | no |
| dossier_live:opus48 | (b) | T1+S1 | +0.022 | +0.025 (0.004) | +0.019 | 0.050 | no |
| dossier_live:opus48 | (b) | T2+S1 | +0.018 | +0.018 (0.002) | +0.022 | 0.050 | no |
| dossier_live:opus48 | (b) | T1+S2 | +0.013 | +0.012 (0.004) | +0.012 | 0.050 | no |
| dossier_live:opus48 | (b) | T2+S2 | +0.010 | +0.011 (0.002) | +0.018 | 0.050 | no |
| dossier_live:sonnet | (a) | T1+S1 | +0.558 | -0.362 (0.335) | +0.648 | 10.117 | no |
| dossier_live:sonnet | (a) | T2+S1 | -0.110 | +0.221 (0.329) | -0.352 | 10.117 | no |
| dossier_live:sonnet | (a) | T1+S2 | +0.221 | +0.317 (0.282) | +0.150 | 10.117 | no |
| dossier_live:sonnet | (a) | T2+S2 | +0.396 | -0.205 (0.269) | +0.298 | 10.117 | no |
| dossier_live:sonnet | (b) | T1 | -0.012 | -0.007 (0.007) | +0.009 | 0.050 | no |
| dossier_live:sonnet | (b) | T2 | +0.009 | +0.006 (0.005) | +0.009 | 0.050 | no |
| dossier_live:sonnet | (b) | T1+S1 | +0.061 | +0.063 (0.005) | +0.070 | 0.050 | **yes** |
| dossier_live:sonnet | (b) | T2+S1 | +0.060 | +0.064 (0.004) | +0.061 | 0.050 | **yes** |
| dossier_live:sonnet | (b) | T1+S2 | +0.035 | +0.045 (0.005) | +0.051 | 0.050 | no |
| dossier_live:sonnet | (b) | T2+S2 | +0.051 | +0.047 (0.004) | +0.047 | 0.050 | no |
| P_author:opus48 | (a) | T1+S1 | -0.139 | +0.468 (0.341) | +0.741 | 9.683 | no |
| P_author:opus48 | (a) | T2+S1 | -0.286 | +0.314 (0.294) | +0.423 | 9.683 | no |
| P_author:opus48 | (a) | T1+S2 | +0.270 | +0.486 (0.289) | +0.956 | 9.683 | no |
| P_author:opus48 | (a) | T2+S2 | +0.319 | +0.191 (0.191) | +0.283 | 9.683 | no |
| P_author:opus48 | (b) | T1 | -0.004 | -0.016 (0.006) | -0.014 | 0.050 | no |
| P_author:opus48 | (b) | T2 | -0.003 | -0.006 (0.005) | -0.002 | 0.050 | no |
| P_author:opus48 | (b) | T1+S1 | +0.047 | +0.057 (0.005) | +0.063 | 0.050 | **yes** |
| P_author:opus48 | (b) | T2+S1 | +0.057 | +0.061 (0.004) | +0.059 | 0.050 | **yes** |
| P_author:opus48 | (b) | T1+S2 | +0.046 | +0.046 (0.005) | +0.053 | 0.050 | no |
| P_author:opus48 | (b) | T2+S2 | +0.038 | +0.036 (0.004) | +0.041 | 0.050 | no |
| P_author:sonnet | (a) | T1+S1 | +0.243 | +0.503 (0.294) | +0.363 | 11.233 | no |
| P_author:sonnet | (a) | T2+S1 | +1.042 | +0.439 (0.248) | +0.589 | 11.233 | no |
| P_author:sonnet | (a) | T1+S2 | +0.836 | +0.602 (0.335) | +0.358 | 11.233 | no |
| P_author:sonnet | (a) | T2+S2 | +0.304 | +0.618 (0.263) | +0.398 | 11.233 | no |
| P_author:sonnet | (b) | T1 | +0.015 | +0.014 (0.006) | +0.013 | 0.050 | no |
| P_author:sonnet | (b) | T2 | +0.007 | +0.013 (0.005) | +0.013 | 0.050 | no |
| P_author:sonnet | (b) | T1+S1 | +0.053 | +0.053 (0.005) | +0.047 | 0.050 | **yes** |
| P_author:sonnet | (b) | T2+S1 | +0.042 | +0.050 (0.004) | +0.049 | 0.050 | **yes** |
| P_author:sonnet | (b) | T1+S2 | +0.037 | +0.038 (0.005) | +0.026 | 0.050 | no |
| P_author:sonnet | (b) | T2+S2 | +0.037 | +0.045 (0.004) | +0.033 | 0.050 | no |

## The combined verdict's operating characteristics (A6.13.4; 5-point noise)

The carrier (form (a), Opus 4.8 isolated dossier) and the second named instrument (form (a), Opus 4.8 zero-context `P_author`) read the same simulated plants: the same true composition, the same control-arm triples and, primary, the same judge line deviations (shared η); placement and call noise are each view's own. Under 'margin' both instruments sit at their own latent margins. Per instrument (b) changes (a)'s label only on a two-step conflict and counts as *present* or *attenuated* only when its lower bound minus the cell's simulated null bias stays above 0; the second instrument drops out where it is not readable at the layout. P-max: *holds* on *excluded*, *falsified* on *present*, *partly missed* on *attenuated*, *inconclusive* otherwise. Beside: the line deviations drawn independently for the two views (η independent).

| layout | ICC | η | second readable | P(holds \| 0) | P(falsified \| 0) | P(partly \| 0) | P(inconcl. \| 0) | P(holds \| margin) | P(falsified \| margin) | P(partly \| margin) | P(inconcl. \| margin) | confirmed \| 0 / \| margin | fallback \| 0 / \| margin |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1+S1 | 0.3 | shared | True | 0.93 | 0.00 | 0.03 | 0.03 | 0.02 | 0.36 | 0.52 | 0.10 | 0.82 / 0.42 | 0.00 / 0.00 |
| T1+S1 | 0.3 | independent | True | 0.92 | 0.00 | 0.04 | 0.04 | 0.01 | 0.40 | 0.49 | 0.10 | 0.81 / 0.38 | 0.00 / 0.00 |
| T1+S1 | 0.6 | shared | True | 0.97 | 0.00 | 0.01 | 0.01 | 0.01 | 0.35 | 0.62 | 0.02 | 0.94 / 0.61 | 0.00 / 0.00 |
| T1+S1 | 0.6 | independent | True | 0.94 | 0.00 | 0.05 | 0.00 | 0.00 | 0.32 | 0.67 | 0.01 | 0.93 / 0.57 | 0.00 / 0.00 |
| T2+S1 | 0.3 | shared | True | 0.96 | 0.00 | 0.04 | 0.01 | 0.01 | 0.41 | 0.56 | 0.02 | 0.93 / 0.49 | 0.00 / 0.00 |
| T2+S1 | 0.3 | independent | True | 0.97 | 0.00 | 0.02 | 0.01 | 0.01 | 0.36 | 0.61 | 0.02 | 0.94 / 0.48 | 0.00 / 0.00 |
| T2+S1 | 0.6 | shared | True | 0.97 | 0.00 | 0.03 | 0.00 | 0.00 | 0.29 | 0.69 | 0.01 | 0.92 / 0.60 | 0.00 / 0.00 |
| T2+S1 | 0.6 | independent | True | 0.95 | 0.00 | 0.05 | 0.00 | 0.00 | 0.31 | 0.68 | 0.00 | 0.94 / 0.54 | 0.00 / 0.00 |
| T1+S2 | 0.3 | shared | True | 0.94 | 0.00 | 0.05 | 0.01 | 0.02 | 0.37 | 0.58 | 0.03 | 0.87 / 0.43 | 0.00 / 0.00 |
| T1+S2 | 0.3 | independent | True | 0.97 | 0.00 | 0.01 | 0.02 | 0.03 | 0.34 | 0.57 | 0.06 | 0.89 / 0.42 | 0.00 / 0.00 |
| T1+S2 | 0.6 | shared | True | 0.99 | 0.00 | 0.01 | 0.00 | 0.00 | 0.34 | 0.64 | 0.02 | 0.97 / 0.52 | 0.00 / 0.00 |
| T1+S2 | 0.6 | independent | True | 0.96 | 0.00 | 0.04 | 0.00 | 0.00 | 0.31 | 0.68 | 0.01 | 0.90 / 0.52 | 0.00 / 0.00 |
| T2+S2 | 0.3 | shared | True | 0.96 | 0.00 | 0.04 | 0.00 | 0.00 | 0.34 | 0.66 | 0.00 | 0.94 / 0.57 | 0.00 / 0.00 |
| T2+S2 | 0.3 | independent | True | 0.97 | 0.00 | 0.03 | 0.00 | 0.00 | 0.41 | 0.58 | 0.01 | 0.95 / 0.48 | 0.00 / 0.00 |
| T2+S2 | 0.6 | shared | True | 0.97 | 0.00 | 0.03 | 0.00 | 0.00 | 0.24 | 0.76 | 0.00 | 0.93 / 0.61 | 0.00 / 0.00 |
| T2+S2 | 0.6 | independent | True | 0.97 | 0.00 | 0.03 | 0.00 | 0.00 | 0.32 | 0.68 | 0.00 | 0.94 / 0.56 | 0.00 / 0.00 |

## P4. The estimate per layout (unchanged from the first run)

| layout | lone plants per view | singleton plants per per-agent view | units, all views | **dollars** | stop at 2× |
|---|---|---|---|---|---|
| T1 | 124 | 0 | 1116 | **$20.74** | $41.49 |
| T2 | 248 | 0 | 2232 | **$41.49** | $82.97 |
| T1+S1 | 124 | 234 | 2520 | **$49.09** | $98.17 |
| T2+S1 | 248 | 234 | 3636 | **$69.83** | $139.66 |
| T1+S2 | 124 | 468 | 3924 | **$77.43** | $154.86 |
| T2+S2 | 248 | 468 | 5040 | **$98.17** | $196.35 |

## Readings and deviations (Part 2)

1. **The latent margin's reference cell.** β_b depends on the ICC and the call noise (they set the within-triple spread the conditional contrast is read against). A6.13.2's verified figures (β_b × 25 of 21.5 and 24.8 for the two Opus 4.8 instruments) are the ICC 0.3, 5-point cell, so β* is fixed there for each instrument and S1 pre-registers one m_s per instrument; the other cells' readings of the same β* are tabled as drift.
2. **Truth states.** 'margin' is β* and '1.5 × margin' is 1.5 β*, the same latent effect for both forms in every ICC and noise cell; each form is read against its own margin (0.3 for (b), m_s for (a)).
3. **The gate** holds only at the worse ICC (the smaller P(excluded | 0), the larger P(excluded | margin) and P(LB > 0 | 0)) at 5-point noise; the 0- and 10-point gates are listed. A reading not read counts as neither *excluded* nor LB > 0, so its share is shown beside: a cell that is often not read can meet the two upper bounds without information.
4. **Adoption** follows A6.6 restricted to the named readings (A6.13.3): the carrier's readable layouts (every form-(a) layout carries the singleton arm) in order of P(excluded | 0) + P(present | 1.5 × margin) ('power first'); for each, A6.6's residual-bias trigger at a single-singleton layout ((a) above half of the new m_s, (b) above 0.05, for the carrier's instrument) moves it to the two-placement singleton variant, which is adopted only if the carrier is readable there with a non-material (a) bias, else the next candidate is tried. The second named instrument does not carry at adoption: A6.13.4 makes it the verdict only in an experiment where the carrier is at floor or unfit, and the joint run simulates that. With no eligible layout, Part 2's item 3 rule applies (the layout maximising min(P(excluded | 0), 1 − P(excluded | margin)) for the carrier, labelled descriptive); A6.13.6's text says the highest P(excluded | 0), and Part 2's neutral rule is used as the later instruction.
4a. **Form (a) on the live dossiers** is simulated with independent singleton plants, but A6.13.3 rules it out (a live reading of a singleton would show its co-planted siblings); those rows are labelled not applicable and left out of the readable list.
5. **The joint run** shares the true composition, the control-arm triple draws and the judge's standardised line deviations between the two Opus 4.8 views (the same judge reading the same lines); placement and call noise are independent. The fully independent line deviations are the other bound. The second instrument's readability is read from this file's gate table; (b)'s downgrade subtracts the null bias of the same instrument, layout and ICC at 5-point noise.
6. **Form (b)** now uses the Firth penalised fit (A6.13.5) in the point fit and every bootstrap replicate, by Fisher scoring with step halving on the penalised log-likelihood (undamped scoring can oscillate on a sparse document); O3's document-factor fallback and the unfit rule are kept and now rarely bite. The ceiling clause is applied per experiment on the observed quiet lone recall (above 0.85: (b) is not read).
7. **m_s's old values** (A6.4's rule on B1's reference plants) are kept beside as the superseded calibration; the first run's file is unchanged.
8. **The estimate** is P4's, unchanged (same units, same per-unit bases).


## Review record and session notes (added by the session after the scripted render; not script output)

- **Sequence.** The extension (script `5b33dcef…`, tests `bb8bfbe0…`, 51 pass) was committed to the fork as `932b134` before the run; the simulation, the joint run and this report come from that script and the first run's inputs file (provenance check above). Two first-run cells were re-run with the extended script and reproduced value for value, so the first run's file stays the outcome of A6.6's original gate.
- **Review.** Codex CLI 0.165.0, gpt-6.1-sol, reasoning effort high, read-only, under the same information barrier as brief 20's rounds. Three required fixes, all made and verified in a second pass: (1) the Firth fit's undamped scoring could oscillate on a sparse document (now step-halved on the penalised log-likelihood; Codex's case is a test and matches the analytic optimum); (2) adoption could promote the second instrument to carrier while the joint run kept the isolated dossier (now only the carrier's readability counts at adoption; the second carries only in an experiment where the carrier is at floor or unfit, as A6.13.4 says); (3) a trigger move to an unreadable two-placement variant ended selection (now the next eligible layout is tried first). Optional items made: live-view form (a) rows marked not applicable; the bias table's Monte Carlo SE printed. The reviews are kept at `work/stage3/b3/review/codex-brief20-part2-*.md`.
- **For S1 (restating the tables).** T2+S2 is adopted because it has the carrier's highest P(excluded | 0) + P(present | 1.5 × margin) (0.96 + 0.96); T2+S1, the layout both reads expected, is readable for the carrier too (0.96 + 0.93), but form (b)'s residual bias there is above 0.05 on both Opus 4.8 instruments, so A6.6's trigger would have moved it to T2+S2 anyway. At a margin-sized effect the combined verdict reads *partly missed* or *falsified* (never *holds* above 0.02), so a *holds* reading excludes an effect of that size.
