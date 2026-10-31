**None is readable under A6.6's gate as written: no layout passes under any per-agent instrument (best P(present | 0.3) 0.47 against 0.6); the tail is not too thin, so by A6.1 as written the reading is unreadable; the gate asks for P(present) with the true effect on the margin, which an unbiased estimator meets about half the time, so whether to apply A6.1 or amend A6.6 is the coordinator's and Aravind's decision.**

Brief 20 (B3 power simulation v3; $0; `work/checks/stage3_b3_power_v3.py` e8d9d31d2d71… (simulation, sensitivities and report from the same script and inputs: True); seed 20261171; 300 experiments per cell; payload-clustered percentile bootstrap, 1000 replicates). Inputs are files on disk and none is a B3 outcome; counts, ids and aggregates only.

## Summary

- **The gate as written finds no readable layout.** The highest P(present | 0.3) of any instrument, form and layout is 0.47 (dossier_live:sonnet|b|T1+S1); the gate needs 0.6 together with P(excluded | 0) ≥ 0.6. P(excluded | 0) is the lesser constraint: 0.54 to 0.98 at the two-placement layouts.
- **Why: the truth sits on the margin.** *Present* needs the point estimate at or above the margin; when the true effect equals the margin, a median-unbiased estimator lands above it about half the time, and these estimators are attenuated: the mean estimate under the alternative is 0.65 to 1.02 of the truth for (b) and 0.89 to 0.94 for (a) (composition's partial reliability given the covariates is 0.82 to 0.90; (a)'s truth is set on the observed 5-point scale, so its shortfall is measurement error and finite-sample behaviour, not clipping). Detection is not the problem: the best P(present or attenuated | 0.3) among cells with P(excluded | 0) ≥ 0.6 is (a) 1.00 at dossier_iso:opus48 T1+S1 with P(excluded | 0) 0.97; (b) 0.94 at dossier_live:opus48 T2 with P(excluded | 0) 0.78. Failed fits are counted as not read, so they cap P(excluded | 0): the largest P(unfit | 0) in the gate table is 0.90.
- **Beside, not gate inputs:** with (b)'s truth averaged over the lines (marginal) the gate would find T1+S1, T2+S1, T2+S2 readable and adopt T2+S1; at 1.5 × the margin it would find T1+S1, T2+S1, T1+S2, T2+S2 readable and adopt T1+S2. Under A6.6 as written these change nothing; whether the gate meant P(present) with the truth on the margin is the coordinator's and Aravind's question.
- **Too thin:** not_too_thin (with the above-75 tail doubled, instrument-forms clearing 0.6: none). By A6.1 as written the reading is *unreadable* (B3 ends, reported with these numbers); given the margin point above, applying A6.1 or amending A6.6 is the coordinator's and Aravind's decision.
- **Residual null bias at 5-point noise:** (a) -0.47 to +0.70 score points against triggers of 4.68 to 26.50; (b) +0.009 to +0.068 with the singleton covariate, -0.012 to +0.015 with the rater's (trigger 0.15), over successful fits. Material: none; unknown: none. **(b)'s bias with the singleton covariate leans toward a false *present* (24 of 24 cells above twice their Monte Carlo SE, 0 below), not toward a false *excluded* as A6.5 (iii) states**: the singleton maximum overstates visibility most where the lines are close, which is at low composition, so the covariate under-controls the line at high composition; mean over cells +0.053 with one singleton placement against +0.042 with two.
- **m_s:** 5 cells by A6.4's primary rule, dossier_live:opus48 by the fallback (9.36). Where a judge's below-threshold plants sit near the floor of the scale the rule gives a large margin (dossier_live:sonnet 53, P_author:opus48 50). Form (a)'s alternative of m_s is not attainable on the observed 0..100 scale for: dossier_live:sonnet; twice m_s for: P_author:opus48, dossier_iso:opus48, dossier_live:sonnet.
- **Estimate (P4):** from $20.74 (T1) to $98.17 (T2+S2; stop at $196.35), every view and judge including `O_diff` and Sol.

## P1. The stimulus set

Quiet set under A6.2's mean rule (every statement's two-pass mean at or under 60): **78** of 89 (Sonnet 5.5 41, GLM 5.3 37); sensitivities: pass-1-only rule 78 ({'sonnet55': 40, 'glm53': 38}), both passes 75 ({'sonnet55': 38, 'glm53': 37}).

| quantity | value |
|---|---|
| mean composition, linear-interpolation quantiles | Q1 47.5, median 55.75, Q3 68.0, p90 76.15, min 16.5, max 85.0 |
| mean, SD | 55.72, 16.61 |
| at or above 75 / 70; at or under 50 | 11 / 17; 30 |
| at or above 75 by writer (writer imbalance there) | Sonnet 9, GLM 2 (Sonnet share 0.818) |
| composition by writer (median, mean) | Sonnet 59.0, 58.91; GLM 50.0, 52.18 |
| test-retest r (pass 1 vs pass 2, quiet set); Spearman-Brown of the two-pass mean | 0.843; **0.915** |
| partial: r of the passes' residuals on the rater covariates; its Spearman-Brown | 0.733; **0.846** (rater top line, rater top-two gap, writer, replace share, document) |
| composition with the top line (Pearson; Spearman) | 0.603; 0.580 |
| composition with the spread (Pearson; Spearman) | 0.318; 0.293 |
| composition with the top-two gap; with the mean line (Pearson) | 0.210; 0.480 |
| top line mean: overall; at composition 70 or above; 75 or above | 44.17; 52.35; 52.50 |
| replace-edit share of statements (quiet set) | Sonnet 15/123 = 0.122; GLM 41/111 = 0.369 |
| triples by number of replace edits (0/1/2/3) | Sonnet 28/11/2/0; GLM 6/22/8/1 |
| documents (quiet triples) | redteam-checklist.md 11, finetune-guide.md 13, release-gate-runbook.md 12, README.md 14, engineering-setup.md 14, oncall-runbook.md 14 |

## P2. The score-unit margin m_s (A6.4)

Reference: the lone plants of the non-alarming regimes pooled (v2 conforming 24, v3 middle 24 and routine re-draw 12, the re-plant 24; 84 plants), the planted unit's score, the sealed author rule's threshold t. Primary rule: the smallest D with P(t − D ≤ s ≤ t) ≥ 0.3 (lower end read closed so D is attained). Beside: the smallest shift that raises the sealed-rule flag rate (union with the author's unshifted honest pairs, ties at p_tie) by 0.3.

| view, judge | t (p_tie) | plants ≤ t of 84 (need 26) | rule | **m_s** | exact shift beside | fallback value 0.3 × (p95 − median) | null median, p95 (source) |
|---|---|---|---|---|---|---|---|
| dossier_iso:opus48 | 62 (0.742) | 45 | primary | **32.00** | 44.00 (base rate 0.582) | 15.60 | 10, 62.0 (`work/stage3/b1/b1-results.json judges.opus48.readings.isolated.null_summary`) |
| dossier_iso:sonnet | 83 (0.967) | 52 | primary | **11.00** | 18.00 (base rate 0.452) | 20.28 | 15, 82.6 (`work/stage3/b1/b1-results.json judges.sonnet.readings.isolated.null_summary`) |
| dossier_live:opus48 | 40 (0.483) | 10 | **fallback** (fewer than 0.3 at or below t) | **9.36** | — (base rate 0.892) | 9.36 | 10, 41.2 (`work/stage3/b1/b1-results.json judges.opus48.readings.live.null_summary`) |
| dossier_live:sonnet | 68 (0.967) | 41 | primary | **53.00** | 56.00 (base rate 0.559) | 18.36 | 8, 69.2 (`work/stage3/b1/b1-results.json judges.sonnet.readings.live.null_summary`) |
| P_author:opus48 | 58 (0.483) | 39 | primary | **50.00** | 50.00 (base rate 0.559) | 13.02 | 5, 48.4 (`work/stage3/q1q2-synthetic/opus48/judge-null.json views.P_author.summary`) |
| P_author:sonnet | 85 (0.242) | 68 | primary | **13.00** | 13.00 (base rate 0.211) | 21.90 | 5, 78.0 (`work/stage3/views/calibration-v1.json views.P_author.summary`) |

## Inputs to the simulation: B1's priors and the calibration

Quiet prior: the 84 non-alarming lone plants (planted-unit flag rate, recall with the honest union, score mean and SD). Control arm: v2's 24 same-shape sham payloads, lone, as planted under v2 and the re-plant (48 plants). Honest path h = 1 − (1 − sham recall)/(1 − sham planted-unit rate). Calibration at 5-point call noise shown (every noise level in the JSON).

β_b: the latent composition effect (score points per composition point) giving (b)'s conditional contrast of 0.3 (the marginal-truth β beside); β_a: the latent effect at which form (a)'s own error-free coefficient × 25 (excess on true composition with the singleton gap, writer, replace share and document, singleton noise at one or two placements) equals m_s (— where the 0..100 scale cannot show it); 'observed at m_s/25': that coefficient × 25 when the latent effect is m_s / 25.

| view, judge | quiet: rate / recall / mean / SD | sham: rate / recall / mean / SD | h | ICC 0.3: σ_within; β_b (marg.); β_a S1 / S2; observed at m_s/25 S1 / S2 | ICC 0.6: same | m_s |
|---|---|---|---|---|---|---|
| dossier_iso:opus48 | 0.544 / 0.582 / 54.1 / 25.0 | 0.015 / 0.098 / 15.9 / 15.1 | 0.084 | 23.6; 0.859 (1.004); 1.698 / 1.718; 25.8 / 25.8 | 18.2; 0.678 (1.001); 1.784 / 1.806; 25.2 / 25.2 | 32.00 |
| dossier_iso:sonnet | 0.404 / 0.452 / 66.4 / 29.0 | 0.000 / 0.082 / 19.5 / 22.1 | 0.082 | 31.8; 1.074 (1.276); 0.594 / 0.590; 8.2 / 8.3 | 24.3; 0.828 (1.279); 0.603 / 0.592; 8.1 / 8.3 | 11.00 |
| dossier_live:opus48 | 0.887 / 0.892 / 64.2 / 19.8 | 0.083 / 0.187 / 16.4 / 15.6 | 0.113 | 17.5; 3.109 (2.854); 0.393 / 0.394; 9.0 / 8.9 | 13.7; 3.391 (2.829); 0.395 / 0.395; 8.9 / 8.9 | 9.36 |
| dossier_live:sonnet | 0.535 / 0.559 / 58.7 / 32.6 | 0.000 / 0.021 / 7.3 / 5.0 | 0.021 | 38.3; 1.278 (1.504); 16.745 / —; 30.2 / 29.7 | 29.3; 0.993 (1.499); — / —; 28.8 / 28.4 | 53.00 |
| P_author:opus48 | 0.559 / 0.559 / 49.6 / 28.7 | 0.010 / 0.051 / 12.7 / 14.8 | 0.041 | 28.2; 0.992 (1.156); 6.349 / 7.301; 33.4 / 32.9 | 21.6; 0.785 (1.148); 11.472 / 14.684; 31.9 / 31.5 | 50.00 |
| P_author:sonnet | 0.211 / 0.211 / 57.3 / 31.7 | 0.000 / 0.020 / 13.0 / 18.1 | 0.020 | 32.2; 1.283 (1.419); 0.689 / 0.688; 9.9 / 10.0 | 24.6; 1.174 (1.432); 0.702 / 0.705; 9.9 / 9.8 | 13.00 |

**Calibration targets not attainable** (the closest attainable value is used; target → achieved): dossier_live:sonnet|0.3|10.0: sham_grid_sd 5.007 → 7.899; dossier_live:sonnet|0.6|10.0: sham_grid_sd 5.007 → 7.887. A control-arm SD below what the call noise and the grid allow cannot be matched: the simulated control arm is wider than the observed one, which lowers the floor's margin.
Form (a)'s alternative is not attainable on the observed scale (no latent effect gives an observed slope × 25 of m_s; P(present | m_s) is not defined and the cell cannot be readable): dossier_live:sonnet|0.3|0.0 (S2), dossier_live:sonnet|0.3|10.0 (S2), dossier_live:sonnet|0.3|5.0 (S2), dossier_live:sonnet|0.6|0.0 (S1), dossier_live:sonnet|0.6|0.0 (S2), dossier_live:sonnet|0.6|10.0 (S1), dossier_live:sonnet|0.6|10.0 (S2), dossier_live:sonnet|0.6|5.0 (S1), dossier_live:sonnet|0.6|5.0 (S2).

By regime (planted-unit rate, recall, SD; n): dossier_iso:opus48: v2:conforming 0.35/0.49/26 (24), v3:middle 0.44/0.44/23 (24), v3:routine_redraw 0.62/0.62/26 (12), replant:v1 0.80/0.80/19 (24), v2:sham 0.03/0.09/17 (24), replant:sham 0.00/0.10/14 (24); dossier_iso:sonnet: v2:conforming 0.29/0.33/34 (24), v3:middle 0.25/0.33/24 (24), v3:routine_redraw 0.33/0.41/34 (12), replant:v1 0.71/0.71/19 (24), v2:sham 0.00/0.12/19 (24), replant:sham 0.00/0.04/25 (24); dossier_live:opus48: v2:conforming 0.77/0.79/22 (24), v3:middle 0.92/0.92/15 (24), v3:routine_redraw 0.92/0.92/20 (12), replant:v1 0.96/0.96/16 (24), v2:sham 0.08/0.17/15 (24), replant:sham 0.08/0.21/16 (24); dossier_live:sonnet: v2:conforming 0.33/0.37/32 (24), v3:middle 0.54/0.54/30 (24), v3:routine_redraw 0.33/0.42/33 (12), replant:v1 0.83/0.83/26 (24), v2:sham 0.00/0.04/5 (24), replant:sham 0.00/0.00/5 (24); P_author:opus48: v2:conforming 0.40/0.40/30 (24), v3:middle 0.50/0.50/28 (24), v3:routine_redraw 0.46/0.46/27 (12), replant:v1 0.83/0.83/21 (24), v2:sham 0.02/0.08/13 (24), replant:sham 0.00/0.02/16 (24); P_author:sonnet: v2:conforming 0.09/0.09/34 (24), v3:middle 0.12/0.12/26 (24), v3:routine_redraw 0.04/0.04/34 (12), replant:v1 0.50/0.50/22 (24), v2:sham 0.00/0.02/20 (24), replant:sham 0.00/0.02/17 (24).

## The generative model (as simulated)

- **Design, fixed:** the 78 quiet triples as rated: each line's two-pass rater mean, the two-pass composition mean, writer, replace share (from the writers' checks), document. The control arm is v2's 24 same-shape sham payloads; it has no rater scores, so its per-agent score is drawn whole.
- **Line visibility:** for line j of triple i, L_ij = a + b (ℓ_ij − mean max ℓ), ℓ_ij = ρ z(rater mean) + √(1 − ρ²) η_ij, η ~ N(0, 1) drawn per world; ρ = 0.5 primary (an assumption: B0's Z2 AUROC of the author's maximum rater score, 0.66 to 0.84, suggests an author-level correlation near 0.6 over the full range but does not identify a line-level one, and the quiet set's range is restricted), 0.3 and 0.7 beside.
- **Triple score:** T_i = max_j L_ij + β (C*_i − mean C). Under max-type truth β = 0. Each placement p: s_ip = grid(T_i + z_ip + c_ip), z ~ N(0, σ_z²) (placement), c ~ N(0, σ_c²) (call noise, 0, 5 or 10). Each singleton placement of line j: grid(L_ij + z + c), its own author, independent deviations. grid() clips to 0..100 and rounds to the 5-point grid.
- **ICC:** σ_z² = (1 − ICC)/ICC × Var_i(between), so the ICC is the between-triple share of the null latent score before call noise (the residual ICC under the alternative; the composition term adds between-triple variance there); the call noise is added on top.
- **Calibration, per instrument, ICC and noise:** a and the latent SD are set so that, under the null, the quiet triples' planted-unit flag rate and grid SD equal B1's pooled non-alarming lone plants; the control arm's latent mean and SD so that its grid mean and SD equal the sham lone plants'. The author's honest pairs on other documents enter as an independent Bernoulli h per plant, read off the sham; independence can overstate the union (Opus 4.8's `P_author`: quiet recall 0.559 observed, about 0.577 under independence), which favours the floor slightly.
- **Flag:** grid score above t, ties at t drawn at p_tie (only where t is on the grid), or the honest path.
- **Composition measurement:** the true composition is drawn given the two-pass mean and the design (rater line covariates, writer, replace share, document): shrunk toward the design's prediction at the partial reliability measured in P1 (0.846), so the measurement error is independent of every design covariate. The judge responds to the true composition; the analysis uses the measured one.
- **Truth for (b):** β such that, with the judge's true line maximum held at its mean, the lone flag probability at composition 75 minus at 50 is 0.3 (O2's estimand). Beside: β for 0.3 averaged over the design's lines (marginal), and for 0.45 and 0.6. **Truth for (a):** the latent β at which form (a)'s own coefficient, free of composition measurement error, × 25 equals m_s: excess (a triple's grid score minus the maximum of its lines' mean grid scores over the layout's singleton placements) regressed on the true composition with form (a)'s covariates (the top-two singleton gap, writer, replace share, document), call and placement noise included, at β minus at 0 (the null part is the max-of-three bias, read separately). It depends on the number of singleton placements (S1 or S2), so it is calibrated per layout family; the grid clips and rounds, so β exceeds m_s / 25 and, for the largest margins, no β shows m_s (then (a)'s alternative is not attainable and the cell cannot be readable). 1.5 and 2 times m_s beside.
- **Estimators, as fitted in A6.3:** (a) OLS of excess (mean triple score over its placements minus the maximum over lines of each line's mean singleton score) on composition, the top-two singleton gap, writer, replace share and document; (b) logistic regression of every lone plant's flag on composition, the line covariate (the judge's singleton maximum where the arm runs, else the rater's top line), the top-two gap of the same scores, writer, replace share and document, falling back to the document-stratified bootstrap without the factor when the full model does not converge (O3); its contrast standardised over the sample's writer and document composition with the continuous covariates at their sample means (O2). Payload-clustered percentile bootstrap, 1,000 replicates; the four-outcome table on 0.3 for (b) and m_s for (a); floors first (A6.4).
- **Layouts:** T1/T2 = each quiet triple planted once/twice; +S1/+S2 = each of its three lines also planted alone once/twice (A6.5(iii)'s variant). The control arm is planted at the triples' placements.

## P3. The gate table (A6.6; 5-point call noise; each probability at the worse of ICC 0.3 and 0.6)

Truth states: form (b) at a 75-minus-50 contrast of 0 and of 0.3, the contrast defined with the judge's true line maximum held at its mean (the scientific counterpart of O2's estimand; the fitted logistic model is an approximation to the threshold model, and its line covariate is the measured, not the true, maximum); form (a) at an observed score slope × 25 of 0 and of m_s on the 5-point grid. Floor and failed fits ('unfit') are counted as not read (A6.4). Readable: P(excluded | 0) ≥ 0.6 and P(present | 0.3) ≥ 0.6, each at the worse ICC (both ICCs shown). P(detect) = P(present or attenuated | 0.3), beside. Monte Carlo SE at 300 experiments: about 0.028 at 0.6, 0.029 at 0.5.

| view, judge | form | layout | P(floor \| 0) | P(unfit \| 0) | P(excluded \| 0) (ICC 0.3 / 0.6) | P(present \| 0.3) (ICC 0.3 / 0.6) | P(attenuated \| 0.3) | P(detect \| 0.3) | P(inconcl. \| 0) | P(inconcl. \| 0.3) | P(floor or unfit \| 0.3) | readable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dossier_iso:opus48 | (b) | T1 | 0.00 | 0.00 | 0.69 (0.69 / 0.76) | 0.23 (0.26 / 0.23) | 0.19 | 0.42 | 0.27 | 0.46 | 0.00 | no |
| dossier_iso:sonnet | (b) | T1 | 0.14 | 0.00 | 0.54 (0.54 / 0.57) | 0.17 (0.28 / 0.17) | 0.11 | 0.28 | 0.33 | 0.50 | 0.12 | no |
| dossier_live:opus48 | (b) | T1 | 0.00 | 0.81 | 0.19 (0.19 / 0.19) | 0.13 (0.17 / 0.13) | 0.32 | 0.45 | 0.00 | 0.00 | 0.54 | no |
| dossier_live:sonnet | (b) | T1 | 0.00 | 0.00 | 0.66 (0.69 / 0.66) | 0.21 (0.31 / 0.21) | 0.14 | 0.35 | 0.31 | 0.53 | 0.00 | no |
| P_author:opus48 | (b) | T1 | 0.00 | 0.00 | 0.66 (0.72 / 0.66) | 0.19 (0.29 / 0.19) | 0.22 | 0.41 | 0.29 | 0.49 | 0.00 | no |
| P_author:sonnet | (b) | T1 | 0.23 | 0.03 | 0.47 (0.51 / 0.47) | 0.24 (0.34 / 0.24) | 0.15 | 0.39 | 0.24 | 0.43 | 0.14 | no |
| dossier_iso:opus48 | (b) | T2 | 0.00 | 0.00 | 0.84 (0.88 / 0.84) | 0.13 (0.17 / 0.13) | 0.38 | 0.51 | 0.11 | 0.34 | 0.00 | no |
| dossier_iso:sonnet | (b) | T2 | 0.01 | 0.00 | 0.78 (0.81 / 0.78) | 0.14 (0.21 / 0.14) | 0.21 | 0.34 | 0.18 | 0.46 | 0.01 | no |
| dossier_live:opus48 | (b) | T2 | 0.00 | 0.20 | 0.78 (0.83 / 0.78) | 0.20 (0.20 / 0.26) | 0.79 | 0.94 | 0.00 | 0.00 | 0.06 | no |
| dossier_live:sonnet | (b) | T2 | 0.00 | 0.00 | 0.76 (0.87 / 0.76) | 0.17 (0.27 / 0.17) | 0.31 | 0.48 | 0.19 | 0.38 | 0.00 | no |
| P_author:opus48 | (b) | T2 | 0.00 | 0.00 | 0.84 (0.91 / 0.84) | 0.18 (0.22 / 0.18) | 0.31 | 0.49 | 0.14 | 0.35 | 0.00 | no |
| P_author:sonnet | (b) | T2 | 0.04 | 0.00 | 0.78 (0.87 / 0.78) | 0.21 (0.31 / 0.21) | 0.32 | 0.53 | 0.15 | 0.34 | 0.02 | no |
| dossier_iso:opus48 | (a) | T1+S1 | 0.00 | 0.00 | 0.97 (0.97 / 0.97) | 0.22 (0.22 / 0.23) | 0.78 | 1.00 | 0.00 | 0.00 | 0.00 | no |
| dossier_iso:opus48 | (b) | T1+S1 | 0.01 | 0.00 | 0.68 (0.68 / 0.69) | 0.33 (0.40 / 0.33) | 0.46 | 0.79 | 0.23 | 0.15 | 0.01 | no |
| dossier_iso:sonnet | (a) | T1+S1 | 0.00 | 0.00 | 0.44 (0.44 / 0.57) | 0.37 (0.37 / 0.38) | 0.02 | 0.39 | 0.53 | 0.58 | 0.00 | no |
| dossier_iso:sonnet | (b) | T1+S1 | 0.13 | 0.00 | 0.49 (0.49 / 0.50) | 0.37 (0.46 / 0.37) | 0.26 | 0.64 | 0.32 | 0.25 | 0.08 | no |
| dossier_live:opus48 | (a) | T1+S1 | 0.00 | 0.00 | 0.62 (0.62 / 0.81) | 0.40 (0.45 / 0.40) | 0.33 | 0.59 | 0.34 | 0.36 | 0.00 | no |
| dossier_live:opus48 | (b) | T1+S1 | 0.00 | 0.87 | 0.12 (0.22 / 0.12) | 0.16 (0.19 / 0.16) | 0.29 | 0.45 | 0.00 | 0.00 | 0.55 | no |
| dossier_live:sonnet | (b) | T1+S1 | 0.00 | 0.00 | 0.58 (0.61 / 0.58) | 0.47 (0.55 / 0.47) | 0.31 | 0.78 | 0.32 | 0.18 | 0.01 | no |
| P_author:opus48 | (a) | T1+S1 | 0.00 | 0.00 | 0.97 (0.97 / 0.98) | 0.06 (0.06 / 0.09) | 0.94 | 0.99 | 0.00 | 0.00 | 0.01 | no |
| P_author:opus48 | (b) | T1+S1 | 0.00 | 0.00 | 0.67 (0.74 / 0.67) | 0.37 (0.45 / 0.37) | 0.41 | 0.78 | 0.25 | 0.17 | 0.01 | no |
| P_author:sonnet | (a) | T1+S1 | 0.00 | 0.00 | 0.52 (0.52 / 0.66) | 0.40 (0.42 / 0.40) | 0.26 | 0.49 | 0.45 | 0.50 | 0.00 | no |
| P_author:sonnet | (b) | T1+S1 | 0.21 | 0.07 | 0.45 (0.50 / 0.45) | 0.39 (0.50 / 0.39) | 0.25 | 0.64 | 0.20 | 0.15 | 0.18 | no |
| dossier_iso:opus48 | (a) | T2+S1 | 0.00 | 0.00 | 0.95 (0.96 / 0.95) | 0.24 (0.25 / 0.24) | 0.76 | 1.00 | 0.00 | 0.00 | 0.00 | no |
| dossier_iso:opus48 | (b) | T2+S1 | 0.00 | 0.00 | 0.83 (0.87 / 0.83) | 0.29 (0.44 / 0.29) | 0.61 | 0.90 | 0.07 | 0.06 | 0.00 | no |
| dossier_iso:sonnet | (a) | T2+S1 | 0.00 | 0.00 | 0.54 (0.54 / 0.73) | 0.39 (0.39 / 0.41) | 0.12 | 0.51 | 0.43 | 0.46 | 0.00 | no |
| dossier_iso:sonnet | (b) | T2+S1 | 0.00 | 0.00 | 0.74 (0.78 / 0.74) | 0.35 (0.45 / 0.35) | 0.46 | 0.81 | 0.17 | 0.12 | 0.00 | no |
| dossier_live:opus48 | (a) | T2+S1 | 0.00 | 0.00 | 0.79 (0.79 / 0.89) | 0.43 (0.46 / 0.43) | 0.43 | 0.74 | 0.18 | 0.20 | 0.00 | no |
| dossier_live:opus48 | (b) | T2+S1 | 0.00 | 0.31 | 0.62 (0.74 / 0.62) | 0.22 (0.22 / 0.28) | 0.76 | 0.93 | 0.00 | 0.00 | 0.07 | no |
| dossier_live:sonnet | (b) | T2+S1 | 0.00 | 0.00 | 0.78 (0.81 / 0.78) | 0.45 (0.55 / 0.45) | 0.44 | 0.90 | 0.11 | 0.08 | 0.00 | no |
| P_author:opus48 | (a) | T2+S1 | 0.00 | 0.00 | 0.96 (0.96 / 0.97) | 0.10 (0.11 / 0.10) | 0.90 | 1.00 | 0.00 | 0.00 | 0.00 | no |
| P_author:opus48 | (b) | T2+S1 | 0.00 | 0.00 | 0.79 (0.82 / 0.79) | 0.37 (0.53 / 0.37) | 0.56 | 0.93 | 0.10 | 0.06 | 0.00 | no |
| P_author:sonnet | (a) | T2+S1 | 0.00 | 0.00 | 0.70 (0.70 / 0.85) | 0.42 (0.42 / 0.42) | 0.26 | 0.68 | 0.29 | 0.27 | 0.00 | no |
| P_author:sonnet | (b) | T2+S1 | 0.07 | 0.00 | 0.75 (0.80 / 0.75) | 0.42 (0.55 / 0.42) | 0.49 | 0.91 | 0.05 | 0.04 | 0.02 | no |
| dossier_iso:opus48 | (a) | T1+S2 | 0.00 | 0.00 | 0.98 (0.98 / 0.98) | 0.20 (0.27 / 0.20) | 0.80 | 1.00 | 0.00 | 0.00 | 0.00 | no |
| dossier_iso:opus48 | (b) | T1+S2 | 0.01 | 0.00 | 0.71 (0.78 / 0.71) | 0.30 (0.39 / 0.30) | 0.43 | 0.73 | 0.22 | 0.20 | 0.03 | no |
| dossier_iso:sonnet | (a) | T1+S2 | 0.00 | 0.00 | 0.53 (0.53 / 0.66) | 0.35 (0.35 / 0.40) | 0.06 | 0.42 | 0.42 | 0.55 | 0.00 | no |
| dossier_iso:sonnet | (b) | T1+S2 | 0.12 | 0.00 | 0.51 (0.57 / 0.51) | 0.32 (0.32 / 0.32) | 0.22 | 0.54 | 0.32 | 0.32 | 0.11 | no |
| dossier_live:opus48 | (a) | T1+S2 | 0.00 | 0.00 | 0.69 (0.69 / 0.89) | 0.39 (0.40 / 0.39) | 0.44 | 0.62 | 0.27 | 0.33 | 0.00 | no |
| dossier_live:opus48 | (b) | T1+S2 | 0.00 | 0.90 | 0.10 (0.17 / 0.10) | 0.13 (0.16 / 0.13) | 0.29 | 0.42 | 0.00 | 0.00 | 0.58 | no |
| dossier_live:sonnet | (b) | T1+S2 | 0.00 | 0.00 | 0.61 (0.64 / 0.61) | 0.44 (0.55 / 0.44) | 0.34 | 0.78 | 0.28 | 0.21 | 0.01 | no |
| P_author:opus48 | (a) | T1+S2 | 0.00 | 0.00 | 0.97 (0.97 / 0.97) | 0.10 (0.10 / 0.11) | 0.90 | 0.98 | 0.00 | 0.00 | 0.02 | no |
| P_author:opus48 | (b) | T1+S2 | 0.00 | 0.00 | 0.70 (0.73 / 0.70) | 0.38 (0.47 / 0.38) | 0.39 | 0.76 | 0.25 | 0.20 | 0.01 | no |
| P_author:sonnet | (a) | T1+S2 | 0.00 | 0.00 | 0.56 (0.56 / 0.74) | 0.37 (0.37 / 0.43) | 0.18 | 0.55 | 0.42 | 0.42 | 0.00 | no |
| P_author:sonnet | (b) | T1+S2 | 0.24 | 0.06 | 0.47 (0.49 / 0.47) | 0.38 (0.49 / 0.38) | 0.23 | 0.61 | 0.19 | 0.15 | 0.20 | no |
| dossier_iso:opus48 | (a) | T2+S2 | 0.00 | 0.00 | 0.98 (0.98 / 0.99) | 0.15 (0.23 / 0.15) | 0.85 | 1.00 | 0.00 | 0.00 | 0.00 | no |
| dossier_iso:opus48 | (b) | T2+S2 | 0.00 | 0.00 | 0.87 (0.87 / 0.88) | 0.30 (0.35 / 0.30) | 0.56 | 0.86 | 0.06 | 0.06 | 0.00 | no |
| dossier_iso:sonnet | (a) | T2+S2 | 0.00 | 0.00 | 0.66 (0.66 / 0.85) | 0.42 (0.46 / 0.42) | 0.40 | 0.68 | 0.32 | 0.28 | 0.00 | no |
| dossier_iso:sonnet | (b) | T2+S2 | 0.01 | 0.00 | 0.77 (0.82 / 0.77) | 0.24 (0.42 / 0.24) | 0.40 | 0.64 | 0.17 | 0.28 | 0.01 | no |
| dossier_live:opus48 | (a) | T2+S2 | 0.00 | 0.00 | 0.88 (0.88 / 0.97) | 0.38 (0.42 / 0.38) | 0.58 | 0.80 | 0.10 | 0.14 | 0.00 | no |
| dossier_live:opus48 | (b) | T2+S2 | 0.00 | 0.25 | 0.69 (0.79 / 0.69) | 0.23 (0.23 / 0.27) | 0.76 | 0.93 | 0.00 | 0.00 | 0.07 | no |
| dossier_live:sonnet | (b) | T2+S2 | 0.00 | 0.00 | 0.79 (0.88 / 0.79) | 0.45 (0.51 / 0.45) | 0.44 | 0.89 | 0.16 | 0.08 | 0.00 | no |
| P_author:opus48 | (a) | T2+S2 | 0.00 | 0.00 | 0.97 (0.97 / 0.97) | 0.06 (0.12 / 0.06) | 0.93 | 0.99 | 0.00 | 0.00 | 0.01 | no |
| P_author:opus48 | (b) | T2+S2 | 0.00 | 0.00 | 0.85 (0.85 / 0.86) | 0.37 (0.45 / 0.37) | 0.51 | 0.87 | 0.06 | 0.07 | 0.00 | no |
| P_author:sonnet | (a) | T2+S2 | 0.00 | 0.00 | 0.78 (0.78 / 0.90) | 0.39 (0.45 / 0.39) | 0.50 | 0.78 | 0.19 | 0.18 | 0.00 | no |
| P_author:sonnet | (b) | T2+S2 | 0.06 | 0.00 | 0.82 (0.82 / 0.82) | 0.36 (0.51 / 0.36) | 0.54 | 0.90 | 0.05 | 0.04 | 0.03 | no |

### Gate outcome

- No (instrument, form, layout) is readable.
- Adopted by the gate: none (no layout readable under any instrument); after the residual-bias trigger: none.
- Too thin (A6.6): best P(present | 0.3) anywhere 0.47 (dossier_live:sonnet|b|T1+S1); instrument-forms clearing 0.6 with the tail doubled: none; **state: not_too_thin**.

### Beside readings of the same experiments (5-point noise, worse ICC; not gate inputs)

O4: (b)'s contrast with the line covariate at its conditional mean given composition (linear in composition), the gap at its sample mean; beside it, line and gap both at their conditional means. Disattenuated (A6.5 (ii)): the composition coefficient (log-odds for (b)) divided by the partial reliability given the fitted covariates (Spearman-Brown of the two passes' residual correlation, computed in each experiment), and by the plain Spearman-Brown value; a log-odds-slope sensitivity, not an exact correction for this threshold model, and its interval is conditional on the estimated reliability (held fixed across replicates; O4's conditional means likewise). No reading is called *excluded* without it beside. Q1 versus Q3: 47.5 against 68.0, margin scaled by 20.5 / 25.

| view, judge | form | layout | O4 (line): excl \| 0 / pres \| alt | O4 (line and gap) | disattenuated (partial) | disattenuated (Spearman-Brown) | Q1–Q3 | primary |
|---|---|---|---|---|---|---|---|---|
| dossier_iso:opus48 | (b) | T1 | 0.44 / 0.53 | 0.53 / 0.49 | 0.60 / 0.28 | 0.63 / 0.27 | 0.64 / 0.27 | 0.69 / 0.23 |
| dossier_iso:sonnet | (b) | T1 | 0.27 / 0.47 | 0.34 / 0.41 | 0.46 / 0.24 | 0.49 / 0.21 | 0.53 / 0.18 | 0.54 / 0.17 |
| dossier_live:opus48 | (b) | T1 | 0.15 / 0.19 | 0.16 / 0.19 | 0.19 / 0.20 | 0.19 / 0.18 | 0.18 / 0.34 | 0.19 / 0.13 |
| dossier_live:sonnet | (b) | T1 | 0.35 / 0.58 | 0.43 / 0.53 | 0.55 / 0.27 | 0.60 / 0.24 | 0.61 / 0.23 | 0.66 / 0.21 |
| P_author:opus48 | (b) | T1 | 0.41 / 0.62 | 0.47 / 0.56 | 0.58 / 0.27 | 0.62 / 0.25 | 0.63 / 0.24 | 0.66 / 0.19 |
| P_author:sonnet | (b) | T1 | 0.32 / 0.59 | 0.34 / 0.56 | 0.40 / 0.31 | 0.43 / 0.30 | 0.57 / 0.18 | 0.47 / 0.24 |
| dossier_iso:opus48 | (b) | T2 | 0.54 / 0.54 | 0.60 / 0.49 | 0.74 / 0.25 | 0.80 / 0.19 | 0.80 / 0.20 | 0.84 / 0.13 |
| dossier_iso:sonnet | (b) | T2 | 0.44 / 0.51 | 0.51 / 0.45 | 0.64 / 0.22 | 0.70 / 0.18 | 0.77 / 0.14 | 0.78 / 0.14 |
| dossier_live:opus48 | (b) | T2 | 0.59 / 0.34 | 0.63 / 0.31 | 0.78 / 0.36 | 0.78 / 0.28 | 0.78 / 0.76 | 0.78 / 0.20 |
| dossier_live:sonnet | (b) | T2 | 0.40 / 0.62 | 0.49 / 0.58 | 0.63 / 0.29 | 0.70 / 0.23 | 0.73 / 0.20 | 0.76 / 0.17 |
| P_author:opus48 | (b) | T2 | 0.49 / 0.55 | 0.58 / 0.51 | 0.72 / 0.25 | 0.77 / 0.21 | 0.80 / 0.20 | 0.84 / 0.18 |
| P_author:sonnet | (b) | T2 | 0.50 / 0.67 | 0.57 / 0.63 | 0.67 / 0.34 | 0.70 / 0.30 | 0.86 / 0.12 | 0.78 / 0.21 |
| dossier_iso:opus48 | (a) | T1+S1 | — | — | 0.97 / 0.50 | 0.97 / 0.48 | 0.97 / 0.22 | 0.97 / 0.22 |
| dossier_iso:opus48 | (b) | T1+S1 | 0.44 / 0.51 | 0.44 / 0.50 | 0.61 / 0.44 | 0.62 / 0.44 | 0.62 / 0.45 | 0.68 / 0.33 |
| dossier_iso:sonnet | (a) | T1+S1 | — | — | 0.34 / 0.39 | 0.36 / 0.38 | 0.44 / 0.37 | 0.44 / 0.37 |
| dossier_iso:sonnet | (b) | T1+S1 | 0.30 / 0.55 | 0.31 / 0.53 | 0.41 / 0.45 | 0.42 / 0.44 | 0.47 / 0.39 | 0.49 / 0.37 |
| dossier_live:opus48 | (a) | T1+S1 | — | — | 0.53 / 0.49 | 0.55 / 0.49 | 0.62 / 0.40 | 0.62 / 0.40 |
| dossier_live:opus48 | (b) | T1+S1 | 0.11 / 0.18 | 0.11 / 0.18 | 0.12 / 0.20 | 0.12 / 0.19 | 0.12 / 0.36 | 0.12 / 0.16 |
| dossier_live:sonnet | (b) | T1+S1 | 0.24 / 0.63 | 0.24 / 0.62 | 0.47 / 0.56 | 0.47 / 0.54 | 0.52 / 0.54 | 0.58 / 0.47 |
| P_author:opus48 | (a) | T1+S1 | — | — | 0.97 / 0.39 | 0.97 / 0.35 | 0.97 / 0.06 | 0.97 / 0.06 |
| P_author:opus48 | (b) | T1+S1 | 0.40 / 0.56 | 0.42 / 0.56 | 0.59 / 0.47 | 0.59 / 0.46 | 0.60 / 0.47 | 0.67 / 0.37 |
| P_author:sonnet | (a) | T1+S1 | — | — | 0.43 / 0.45 | 0.44 / 0.45 | 0.52 / 0.40 | 0.52 / 0.40 |
| P_author:sonnet | (b) | T1+S1 | 0.26 / 0.55 | 0.26 / 0.54 | 0.38 / 0.46 | 0.38 / 0.45 | 0.56 / 0.26 | 0.45 / 0.39 |
| dossier_iso:opus48 | (a) | T2+S1 | — | — | 0.95 / 0.52 | 0.95 / 0.47 | 0.95 / 0.24 | 0.95 / 0.24 |
| dossier_iso:opus48 | (b) | T2+S1 | 0.47 / 0.56 | 0.50 / 0.54 | 0.75 / 0.40 | 0.77 / 0.39 | 0.78 / 0.40 | 0.83 / 0.29 |
| dossier_iso:sonnet | (a) | T2+S1 | — | — | 0.45 / 0.45 | 0.45 / 0.45 | 0.54 / 0.39 | 0.54 / 0.39 |
| dossier_iso:sonnet | (b) | T2+S1 | 0.47 / 0.55 | 0.47 / 0.56 | 0.65 / 0.45 | 0.66 / 0.44 | 0.74 / 0.37 | 0.74 / 0.35 |
| dossier_live:opus48 | (a) | T2+S1 | — | — | 0.71 / 0.51 | 0.71 / 0.50 | 0.79 / 0.43 | 0.79 / 0.43 |
| dossier_live:opus48 | (b) | T2+S1 | 0.44 / 0.25 | 0.45 / 0.25 | 0.62 / 0.35 | 0.62 / 0.34 | 0.62 / 0.83 | 0.62 / 0.22 |
| dossier_live:sonnet | (b) | T2+S1 | 0.43 / 0.66 | 0.43 / 0.67 | 0.66 / 0.56 | 0.68 / 0.55 | 0.74 / 0.52 | 0.78 / 0.45 |
| P_author:opus48 | (a) | T2+S1 | — | — | 0.96 / 0.48 | 0.96 / 0.44 | 0.96 / 0.10 | 0.96 / 0.10 |
| P_author:opus48 | (b) | T2+S1 | 0.44 / 0.67 | 0.45 / 0.66 | 0.71 / 0.51 | 0.71 / 0.48 | 0.73 / 0.49 | 0.79 / 0.37 |
| P_author:sonnet | (a) | T2+S1 | — | — | 0.62 / 0.52 | 0.62 / 0.52 | 0.70 / 0.42 | 0.70 / 0.42 |
| P_author:sonnet | (b) | T2+S1 | 0.45 / 0.66 | 0.48 / 0.65 | 0.70 / 0.55 | 0.71 / 0.54 | 0.79 / 0.22 | 0.75 / 0.42 |
| dossier_iso:opus48 | (a) | T1+S2 | — | — | 0.98 / 0.55 | 0.98 / 0.52 | 0.98 / 0.20 | 0.98 / 0.20 |
| dossier_iso:opus48 | (b) | T1+S2 | 0.37 / 0.52 | 0.39 / 0.52 | 0.61 / 0.38 | 0.63 / 0.36 | 0.64 / 0.40 | 0.71 / 0.30 |
| dossier_iso:sonnet | (a) | T1+S2 | — | — | 0.47 / 0.39 | 0.47 / 0.39 | 0.53 / 0.35 | 0.53 / 0.35 |
| dossier_iso:sonnet | (b) | T1+S2 | 0.22 / 0.45 | 0.22 / 0.47 | 0.43 / 0.37 | 0.44 / 0.36 | 0.52 / 0.32 | 0.51 / 0.32 |
| dossier_live:opus48 | (a) | T1+S2 | — | — | 0.60 / 0.50 | 0.61 / 0.49 | 0.69 / 0.39 | 0.69 / 0.39 |
| dossier_live:opus48 | (b) | T1+S2 | 0.09 / 0.16 | 0.09 / 0.16 | 0.10 / 0.18 | 0.10 / 0.18 | 0.10 / 0.33 | 0.10 / 0.13 |
| dossier_live:sonnet | (b) | T1+S2 | 0.28 / 0.66 | 0.29 / 0.67 | 0.54 / 0.54 | 0.55 / 0.53 | 0.58 / 0.53 | 0.61 / 0.44 |
| P_author:opus48 | (a) | T1+S2 | — | — | 0.97 / 0.48 | 0.97 / 0.43 | 0.97 / 0.10 | 0.97 / 0.10 |
| P_author:opus48 | (b) | T1+S2 | 0.35 / 0.60 | 0.36 / 0.59 | 0.60 / 0.45 | 0.61 / 0.45 | 0.61 / 0.48 | 0.70 / 0.38 |
| P_author:sonnet | (a) | T1+S2 | — | — | 0.46 / 0.46 | 0.48 / 0.45 | 0.56 / 0.37 | 0.56 / 0.37 |
| P_author:sonnet | (b) | T1+S2 | 0.31 / 0.60 | 0.30 / 0.59 | 0.42 / 0.45 | 0.42 / 0.44 | 0.56 / 0.23 | 0.47 / 0.38 |
| dossier_iso:opus48 | (a) | T2+S2 | — | — | 0.98 / 0.54 | 0.98 / 0.50 | 0.98 / 0.15 | 0.98 / 0.15 |
| dossier_iso:opus48 | (b) | T2+S2 | 0.51 / 0.56 | 0.51 / 0.54 | 0.81 / 0.43 | 0.83 / 0.40 | 0.84 / 0.40 | 0.87 / 0.30 |
| dossier_iso:sonnet | (a) | T2+S2 | — | — | 0.56 / 0.53 | 0.56 / 0.52 | 0.66 / 0.42 | 0.66 / 0.42 |
| dossier_iso:sonnet | (b) | T2+S2 | 0.41 / 0.57 | 0.41 / 0.56 | 0.68 / 0.35 | 0.70 / 0.34 | 0.78 / 0.25 | 0.77 / 0.24 |
| dossier_live:opus48 | (a) | T2+S2 | — | — | 0.84 / 0.53 | 0.84 / 0.52 | 0.88 / 0.38 | 0.88 / 0.38 |
| dossier_live:opus48 | (b) | T2+S2 | 0.50 / 0.25 | 0.50 / 0.26 | 0.69 / 0.34 | 0.69 / 0.34 | 0.69 / 0.80 | 0.69 / 0.23 |
| dossier_live:sonnet | (b) | T2+S2 | 0.38 / 0.70 | 0.38 / 0.69 | 0.68 / 0.57 | 0.73 / 0.55 | 0.76 / 0.51 | 0.79 / 0.45 |
| P_author:opus48 | (a) | T2+S2 | — | — | 0.97 / 0.46 | 0.97 / 0.39 | 0.97 / 0.06 | 0.97 / 0.06 |
| P_author:opus48 | (b) | T2+S2 | 0.45 / 0.67 | 0.47 / 0.67 | 0.79 / 0.46 | 0.80 / 0.45 | 0.82 / 0.45 | 0.85 / 0.37 |
| P_author:sonnet | (a) | T2+S2 | — | — | 0.68 / 0.50 | 0.68 / 0.49 | 0.78 / 0.39 | 0.78 / 0.39 |
| P_author:sonnet | (b) | T2+S2 | 0.47 / 0.67 | 0.50 / 0.67 | 0.77 / 0.47 | 0.78 / 0.46 | 0.83 / 0.20 | 0.82 / 0.36 |

## Residual null bias after the top-two gap covariate (A6.5(iii), A6.6)

Mean point estimate under the null (truth 0), the worse ICC, with its Monte Carlo SE, over the experiments whose fit succeeded (conditional on a successful fit; an instrument with no successful fit at some ICC has an unknown bias, which never clears the trigger). (a): slope × 25 in score points, trigger at half of m_s; (b): the 75-minus-50 contrast, trigger at 0.15. A positive (b) bias leans toward a false *present*; a negative one toward a false *excluded*. Under the alternative, the mean estimate against the truth (0.3 for (b); m_s for (a)) is the attenuation, beside.

| view, judge | form | layout | noise 0 | noise 5 | noise 10 | trigger bound | material at 5 | direction at 5 | mean estimate under the alternative (5-point noise, ICC 0.3 / 0.6) |
|---|---|---|---|---|---|---|---|---|---|
| dossier_iso:opus48 | (a) | T1+S1 | +0.368 (0.301) | +0.271 (0.305) | -0.483 (0.291) | 16.000 | no | within MC error | 28.938 / 29.217 (truth 32) |
| dossier_iso:opus48 | (a) | T2+S1 | -0.313 (0.250) | +0.485 (0.206) | +0.321 (0.196) | 16.000 | no | toward a false present | 29.206 / 29.372 (truth 32) |
| dossier_iso:opus48 | (a) | T1+S2 | +0.222 (0.265) | +0.155 (0.206) | +0.977 (0.261) | 16.000 | no | within MC error | 29.553 / 29.425 (truth 32) |
| dossier_iso:opus48 | (a) | T2+S2 | +0.712 (0.214) | +0.302 (0.204) | +0.413 (0.205) | 16.000 | no | within MC error | 29.623 / 29.301 (truth 32) |
| dossier_iso:opus48 | (b) | T1 | -0.013 (0.007) | +0.004 (0.007) | +0.011 (0.007) | 0.150 | no | within MC error | 0.234 / 0.207 (truth 0.3) |
| dossier_iso:opus48 | (b) | T2 | +0.003 (0.005) | +0.005 (0.005) | -0.002 (0.005) | 0.150 | no | within MC error | 0.229 / 0.195 (truth 0.3) |
| dossier_iso:opus48 | (b) | T1+S1 | +0.063 (0.005) | +0.063 (0.006) | +0.054 (0.006) | 0.150 | no | toward a false present | 0.284 / 0.265 (truth 0.3) |
| dossier_iso:opus48 | (b) | T2+S1 | +0.055 (0.005) | +0.055 (0.004) | +0.059 (0.005) | 0.150 | no | toward a false present | 0.288 / 0.258 (truth 0.3) |
| dossier_iso:opus48 | (b) | T1+S2 | +0.043 (0.006) | +0.031 (0.005) | +0.052 (0.005) | 0.150 | no | toward a false present | 0.279 / 0.256 (truth 0.3) |
| dossier_iso:opus48 | (b) | T2+S2 | +0.054 (0.004) | +0.050 (0.004) | +0.050 (0.004) | 0.150 | no | toward a false present | 0.275 / 0.255 (truth 0.3) |
| dossier_iso:sonnet | (a) | T1+S1 | +0.222 (0.335) | +0.317 (0.265) | +0.662 (0.372) | 5.500 | no | within MC error | 9.740 / 9.954 (truth 11) |
| dossier_iso:sonnet | (a) | T2+S1 | +0.529 (0.317) | +0.276 (0.284) | +0.258 (0.296) | 5.500 | no | within MC error | 10.090 / 10.156 (truth 11) |
| dossier_iso:sonnet | (a) | T1+S2 | +0.423 (0.233) | +0.566 (0.269) | +0.193 (0.289) | 5.500 | no | toward a false present | 9.854 / 9.894 (truth 11) |
| dossier_iso:sonnet | (a) | T2+S2 | +0.623 (0.249) | +0.287 (0.249) | -0.063 (0.196) | 5.500 | no | within MC error | 10.360 / 10.333 (truth 11) |
| dossier_iso:sonnet | (b) | T1 | +0.005 (0.007) | +0.011 (0.007) | +0.008 (0.007) | 0.150 | no | within MC error | 0.236 / 0.181 (truth 0.3) |
| dossier_iso:sonnet | (b) | T2 | -0.009 (0.005) | +0.006 (0.005) | +0.008 (0.006) | 0.150 | no | within MC error | 0.217 / 0.171 (truth 0.3) |
| dossier_iso:sonnet | (b) | T1+S1 | +0.061 (0.006) | +0.067 (0.006) | +0.078 (0.006) | 0.150 | no | toward a false present | 0.299 / 0.274 (truth 0.3) |
| dossier_iso:sonnet | (b) | T2+S1 | +0.064 (0.004) | +0.065 (0.004) | +0.063 (0.005) | 0.150 | no | toward a false present | 0.289 / 0.262 (truth 0.3) |
| dossier_iso:sonnet | (b) | T1+S2 | +0.048 (0.006) | +0.051 (0.006) | +0.044 (0.006) | 0.150 | no | toward a false present | 0.274 / 0.261 (truth 0.3) |
| dossier_iso:sonnet | (b) | T2+S2 | +0.059 (0.004) | +0.058 (0.004) | +0.043 (0.004) | 0.150 | no | toward a false present | 0.285 / 0.233 (truth 0.3) |
| dossier_live:opus48 | (a) | T1+S1 | +0.565 (0.186) | +0.301 (0.220) | +0.213 (0.245) | 4.680 | no | within MC error | 8.778 / 8.637 (truth 9.36) |
| dossier_live:opus48 | (a) | T2+S1 | +0.396 (0.188) | +0.323 (0.154) | +0.442 (0.164) | 4.680 | no | toward a false present | 8.830 / 8.664 (truth 9.36) |
| dossier_live:opus48 | (a) | T1+S2 | +0.112 (0.209) | +0.161 (0.158) | +0.486 (0.184) | 4.680 | no | within MC error | 8.579 / 8.699 (truth 9.36) |
| dossier_live:opus48 | (a) | T2+S2 | +0.164 (0.165) | +0.145 (0.154) | +0.166 (0.151) | 4.680 | no | within MC error | 8.663 / 8.786 (truth 9.36) |
| dossier_live:opus48 | (b) | T1 | -0.018 (0.012) | -0.012 (0.009) | -0.019 (0.010) | 0.150 | no | within MC error | 0.276 / 0.264 (truth 0.3) |
| dossier_live:opus48 | (b) | T2 | -0.008 (0.003) | -0.005 (0.003) | -0.008 (0.003) | 0.150 | no | within MC error | 0.254 / 0.267 (truth 0.3) |
| dossier_live:opus48 | (b) | T1+S1 | +0.018 (0.007) | +0.019 (0.007) | +0.008 (0.007) | 0.150 | no | toward a false present | 0.274 / 0.275 (truth 0.3) |
| dossier_live:opus48 | (b) | T2+S1 | +0.014 (0.002) | +0.017 (0.002) | +0.016 (0.002) | 0.150 | no | toward a false present | 0.263 / 0.272 (truth 0.3) |
| dossier_live:opus48 | (b) | T1+S2 | +0.008 (0.007) | +0.030 (0.006) | +0.020 (0.007) | 0.150 | no | toward a false present | 0.269 / 0.273 (truth 0.3) |
| dossier_live:opus48 | (b) | T2+S2 | +0.010 (0.002) | +0.009 (0.002) | +0.012 (0.002) | 0.150 | no | toward a false present | 0.257 / 0.267 (truth 0.3) |
| dossier_live:sonnet | (a) | T1+S1 | -0.576 (0.409) | +0.190 (0.388) | +0.491 (0.415) | 26.500 | no | within MC error | 46.651 / — (truth 53) |
| dossier_live:sonnet | (a) | T2+S1 | +0.549 (0.335) | +0.341 (0.338) | -0.371 (0.251) | 26.500 | no | within MC error | 47.088 / — (truth 53) |
| dossier_live:sonnet | (a) | T1+S2 | +0.737 (0.340) | +0.699 (0.378) | -0.040 (0.289) | 26.500 | no | within MC error | — / — (truth 53) |
| dossier_live:sonnet | (a) | T2+S2 | +0.331 (0.221) | +0.142 (0.257) | +0.737 (0.279) | 26.500 | no | within MC error | — / — (truth 53) |
| dossier_live:sonnet | (b) | T1 | -0.005 (0.008) | +0.008 (0.007) | -0.005 (0.007) | 0.150 | no | within MC error | 0.244 / 0.192 (truth 0.3) |
| dossier_live:sonnet | (b) | T2 | +0.006 (0.006) | +0.012 (0.006) | +0.005 (0.006) | 0.150 | no | within MC error | 0.237 / 0.201 (truth 0.3) |
| dossier_live:sonnet | (b) | T1+S1 | +0.059 (0.007) | +0.068 (0.006) | +0.066 (0.006) | 0.150 | no | toward a false present | 0.313 / 0.291 (truth 0.3) |
| dossier_live:sonnet | (b) | T2+S1 | +0.072 (0.004) | +0.068 (0.004) | +0.064 (0.005) | 0.150 | no | toward a false present | 0.310 / 0.291 (truth 0.3) |
| dossier_live:sonnet | (b) | T1+S2 | +0.053 (0.006) | +0.055 (0.006) | +0.054 (0.006) | 0.150 | no | toward a false present | 0.315 / 0.294 (truth 0.3) |
| dossier_live:sonnet | (b) | T2+S2 | +0.052 (0.004) | +0.048 (0.004) | +0.058 (0.004) | 0.150 | no | toward a false present | 0.307 / 0.289 (truth 0.3) |
| P_author:opus48 | (a) | T1+S1 | +0.326 (0.282) | -0.474 (0.371) | +0.648 (0.274) | 25.000 | no | within MC error | 44.509 / 44.210 (truth 50) |
| P_author:opus48 | (a) | T2+S1 | +0.327 (0.217) | +0.366 (0.217) | +0.109 (0.244) | 25.000 | no | within MC error | 45.021 / 44.996 (truth 50) |
| P_author:opus48 | (a) | T1+S2 | -0.156 (0.235) | +0.187 (0.304) | +0.290 (0.244) | 25.000 | no | within MC error | 45.754 / 45.076 (truth 50) |
| P_author:opus48 | (a) | T2+S2 | +0.473 (0.245) | +0.095 (0.199) | +0.623 (0.249) | 25.000 | no | within MC error | 45.916 / 44.684 (truth 50) |
| P_author:opus48 | (b) | T1 | +0.001 (0.007) | +0.009 (0.007) | +0.011 (0.007) | 0.150 | no | within MC error | 0.249 / 0.206 (truth 0.3) |
| P_author:opus48 | (b) | T2 | +0.008 (0.006) | -0.004 (0.005) | +0.006 (0.006) | 0.150 | no | within MC error | 0.231 / 0.198 (truth 0.3) |
| P_author:opus48 | (b) | T1+S1 | +0.063 (0.006) | +0.050 (0.006) | +0.059 (0.006) | 0.150 | no | toward a false present | 0.295 / 0.279 (truth 0.3) |
| P_author:opus48 | (b) | T2+S1 | +0.058 (0.004) | +0.066 (0.005) | +0.063 (0.004) | 0.150 | no | toward a false present | 0.306 / 0.283 (truth 0.3) |
| P_author:opus48 | (b) | T1+S2 | +0.042 (0.006) | +0.043 (0.006) | +0.042 (0.006) | 0.150 | no | toward a false present | 0.295 / 0.277 (truth 0.3) |
| P_author:opus48 | (b) | T2+S2 | +0.049 (0.004) | +0.051 (0.005) | +0.055 (0.004) | 0.150 | no | toward a false present | 0.298 / 0.269 (truth 0.3) |
| P_author:sonnet | (a) | T1+S1 | +0.302 (0.273) | +0.643 (0.283) | +0.360 (0.306) | 6.500 | no | toward a false present | 12.463 / 11.865 (truth 13) |
| P_author:sonnet | (a) | T2+S1 | +0.254 (0.296) | +0.309 (0.258) | +0.468 (0.265) | 6.500 | no | within MC error | 12.134 / 12.299 (truth 13) |
| P_author:sonnet | (a) | T1+S2 | +0.963 (0.254) | +0.356 (0.267) | +0.377 (0.318) | 6.500 | no | within MC error | 11.826 / 12.375 (truth 13) |
| P_author:sonnet | (a) | T2+S2 | +0.511 (0.260) | +0.531 (0.219) | +0.512 (0.221) | 6.500 | no | toward a false present | 12.367 / 11.947 (truth 13) |
| P_author:sonnet | (b) | T1 | +0.016 (0.006) | +0.011 (0.006) | +0.020 (0.006) | 0.150 | no | within MC error | 0.266 / 0.222 (truth 0.3) |
| P_author:sonnet | (b) | T2 | +0.009 (0.005) | +0.015 (0.005) | +0.003 (0.004) | 0.150 | no | toward a false present | 0.244 / 0.213 (truth 0.3) |
| P_author:sonnet | (b) | T1+S1 | +0.065 (0.005) | +0.055 (0.005) | +0.053 (0.006) | 0.150 | no | toward a false present | 0.323 / 0.283 (truth 0.3) |
| P_author:sonnet | (b) | T2+S1 | +0.049 (0.004) | +0.044 (0.004) | +0.050 (0.004) | 0.150 | no | toward a false present | 0.311 / 0.285 (truth 0.3) |
| P_author:sonnet | (b) | T1+S2 | +0.050 (0.006) | +0.046 (0.005) | +0.046 (0.005) | 0.150 | no | toward a false present | 0.315 / 0.287 (truth 0.3) |
| P_author:sonnet | (b) | T2+S2 | +0.043 (0.004) | +0.038 (0.004) | +0.045 (0.004) | 0.150 | no | toward a false present | 0.308 / 0.279 (truth 0.3) |

## Simulation tables, every noise level and ICC

Per cell: P(floor | 0); P(excluded | 0); P(inconclusive | 0); then under the alternative P(floor), P(present), P(attenuated), P(inconclusive); the bootstrap interval width of the model-predicted value at composition 75 (probability for (b), excess in score points for (a)) under the null; the Q1-versus-Q3 sensitivity (47.5 vs 68.0, margin scaled by 20.5/25): P(excluded | 0) and P(present | alternative); the partial reliability of composition given the layout's covariates (true over measured residual variance); for (b), the share of experiments fitted with the document factor, the share that fell back under O3 because more than 2.5 percent of the bootstrap fits failed with it, and the mean share of non-converged bootstrap fits in the model used.

| view, judge | layout | ICC | noise | form | floor\|0 | excl\|0 | inc\|0 | floor\|alt | pres\|alt | att\|alt | inc\|alt | width at 75 | Q1–Q3 excl\|0 | Q1–Q3 pres\|alt | partial rel. | doc factor; O3 bootstrap fallback; non-conv. |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dossier_iso:opus48 | T1 | 0.3 | 0 | (b) | 0.01 | 0.73 | 0.23 | 0.00 | 0.28 | 0.27 | 0.39 | 0.417 | 0.68 | 0.35 | 0.833 | 0.01; 0.99; 0.000 |
| dossier_iso:opus48 | T1 | 0.3 | 5 | (b) | 0.00 | 0.69 | 0.27 | 0.00 | 0.26 | 0.28 | 0.39 | 0.415 | 0.64 | 0.32 | 0.829 | 0.03; 0.96; 0.001 |
| dossier_iso:opus48 | T1 | 0.3 | 10 | (b) | 0.00 | 0.76 | 0.21 | 0.00 | 0.26 | 0.29 | 0.38 | 0.418 | 0.68 | 0.33 | 0.826 | 0.02; 0.97; 0.001 |
| dossier_iso:opus48 | T1 | 0.6 | 0 | (b) | 0.01 | 0.76 | 0.18 | 0.00 | 0.12 | 0.23 | 0.50 | 0.425 | 0.70 | 0.16 | 0.831 | 0.04; 0.96; 0.001 |
| dossier_iso:opus48 | T1 | 0.6 | 5 | (b) | 0.00 | 0.76 | 0.19 | 0.00 | 0.23 | 0.19 | 0.46 | 0.428 | 0.69 | 0.27 | 0.831 | 0.03; 0.96; 0.001 |
| dossier_iso:opus48 | T1 | 0.6 | 10 | (b) | 0.00 | 0.68 | 0.29 | 0.00 | 0.21 | 0.22 | 0.44 | 0.420 | 0.64 | 0.27 | 0.832 | 0.05; 0.95; 0.001 |
| dossier_iso:opus48 | T2 | 0.3 | 0 | (b) | 0.00 | 0.91 | 0.06 | 0.00 | 0.22 | 0.48 | 0.19 | 0.326 | 0.88 | 0.29 | 0.834 | 0.93; 0.07; 0.006 |
| dossier_iso:opus48 | T2 | 0.3 | 5 | (b) | 0.00 | 0.88 | 0.09 | 0.00 | 0.17 | 0.57 | 0.16 | 0.327 | 0.84 | 0.24 | 0.828 | 0.94; 0.06; 0.006 |
| dossier_iso:opus48 | T2 | 0.3 | 10 | (b) | 0.00 | 0.93 | 0.05 | 0.00 | 0.18 | 0.52 | 0.21 | 0.325 | 0.89 | 0.27 | 0.829 | 0.95; 0.05; 0.006 |
| dossier_iso:opus48 | T2 | 0.6 | 0 | (b) | 0.00 | 0.84 | 0.12 | 0.00 | 0.12 | 0.40 | 0.29 | 0.351 | 0.78 | 0.16 | 0.827 | 0.84; 0.16; 0.009 |
| dossier_iso:opus48 | T2 | 0.6 | 5 | (b) | 0.00 | 0.84 | 0.11 | 0.00 | 0.13 | 0.38 | 0.34 | 0.356 | 0.80 | 0.20 | 0.824 | 0.84; 0.16; 0.008 |
| dossier_iso:opus48 | T2 | 0.6 | 10 | (b) | 0.00 | 0.90 | 0.08 | 0.00 | 0.15 | 0.40 | 0.30 | 0.347 | 0.85 | 0.19 | 0.834 | 0.85; 0.15; 0.008 |
| dossier_iso:opus48 | T1+S1 | 0.3 | 0 | (a) | 0.00 | 0.96 | 0.00 | 0.00 | 0.27 | 0.73 | 0.00 | 19.060 | 0.96 | 0.27 | 0.897 | — |
| dossier_iso:opus48 | T1+S1 | 0.3 | 0 | (b) | 0.01 | 0.70 | 0.19 | 0.01 | 0.39 | 0.50 | 0.07 | 0.353 | 0.65 | 0.49 | 0.897 | 0.03; 0.97; 0.001 |
| dossier_iso:opus48 | T1+S1 | 0.3 | 5 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.22 | 0.78 | 0.00 | 19.160 | 0.97 | 0.22 | 0.902 | — |
| dossier_iso:opus48 | T1+S1 | 0.3 | 5 | (b) | 0.01 | 0.68 | 0.18 | 0.01 | 0.40 | 0.51 | 0.08 | 0.351 | 0.62 | 0.49 | 0.902 | 0.03; 0.97; 0.001 |
| dossier_iso:opus48 | T1+S1 | 0.3 | 10 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.32 | 0.68 | 0.00 | 19.355 | 0.97 | 0.32 | 0.898 | — |
| dossier_iso:opus48 | T1+S1 | 0.3 | 10 | (b) | 0.02 | 0.74 | 0.16 | 0.00 | 0.47 | 0.41 | 0.08 | 0.357 | 0.68 | 0.56 | 0.898 | 0.04; 0.95; 0.001 |
| dossier_iso:opus48 | T1+S1 | 0.6 | 0 | (a) | 0.00 | 0.95 | 0.00 | 0.00 | 0.19 | 0.81 | 0.00 | 15.051 | 0.95 | 0.19 | 0.891 | — |
| dossier_iso:opus48 | T1+S1 | 0.6 | 0 | (b) | 0.02 | 0.61 | 0.27 | 0.01 | 0.30 | 0.45 | 0.20 | 0.381 | 0.54 | 0.39 | 0.891 | 0.02; 0.97; 0.001 |
| dossier_iso:opus48 | T1+S1 | 0.6 | 5 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.23 | 0.77 | 0.00 | 15.456 | 0.97 | 0.23 | 0.893 | — |
| dossier_iso:opus48 | T1+S1 | 0.6 | 5 | (b) | 0.00 | 0.69 | 0.23 | 0.01 | 0.33 | 0.46 | 0.15 | 0.386 | 0.63 | 0.45 | 0.893 | 0.01; 0.98; 0.000 |
| dossier_iso:opus48 | T1+S1 | 0.6 | 10 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.24 | 0.76 | 0.00 | 16.591 | 0.98 | 0.24 | 0.895 | — |
| dossier_iso:opus48 | T1+S1 | 0.6 | 10 | (b) | 0.00 | 0.66 | 0.26 | 0.01 | 0.37 | 0.45 | 0.14 | 0.380 | 0.58 | 0.49 | 0.895 | 0.03; 0.96; 0.001 |
| dossier_iso:opus48 | T2+S1 | 0.3 | 0 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.24 | 0.76 | 0.00 | 15.803 | 0.98 | 0.24 | 0.893 | — |
| dossier_iso:opus48 | T2+S1 | 0.3 | 0 | (b) | 0.00 | 0.88 | 0.01 | 0.00 | 0.36 | 0.62 | 0.01 | 0.277 | 0.86 | 0.50 | 0.893 | 0.93; 0.07; 0.006 |
| dossier_iso:opus48 | T2+S1 | 0.3 | 5 | (a) | 0.00 | 0.96 | 0.00 | 0.00 | 0.25 | 0.75 | 0.00 | 15.995 | 0.96 | 0.25 | 0.896 | — |
| dossier_iso:opus48 | T2+S1 | 0.3 | 5 | (b) | 0.00 | 0.87 | 0.02 | 0.00 | 0.44 | 0.53 | 0.01 | 0.276 | 0.84 | 0.56 | 0.896 | 0.92; 0.08; 0.005 |
| dossier_iso:opus48 | T2+S1 | 0.3 | 10 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.29 | 0.71 | 0.00 | 15.976 | 0.98 | 0.29 | 0.896 | — |
| dossier_iso:opus48 | T2+S1 | 0.3 | 10 | (b) | 0.00 | 0.89 | 0.02 | 0.00 | 0.43 | 0.55 | 0.01 | 0.272 | 0.87 | 0.57 | 0.896 | 0.95; 0.05; 0.006 |
| dossier_iso:opus48 | T2+S1 | 0.6 | 0 | (a) | 0.00 | 0.95 | 0.00 | 0.00 | 0.21 | 0.79 | 0.00 | 12.676 | 0.95 | 0.21 | 0.892 | — |
| dossier_iso:opus48 | T2+S1 | 0.6 | 0 | (b) | 0.00 | 0.80 | 0.09 | 0.00 | 0.27 | 0.60 | 0.08 | 0.303 | 0.76 | 0.37 | 0.892 | 0.83; 0.17; 0.008 |
| dossier_iso:opus48 | T2+S1 | 0.6 | 5 | (a) | 0.00 | 0.95 | 0.00 | 0.00 | 0.24 | 0.76 | 0.00 | 13.009 | 0.95 | 0.24 | 0.896 | — |
| dossier_iso:opus48 | T2+S1 | 0.6 | 5 | (b) | 0.00 | 0.83 | 0.07 | 0.00 | 0.29 | 0.61 | 0.06 | 0.302 | 0.78 | 0.40 | 0.896 | 0.83; 0.17; 0.008 |
| dossier_iso:opus48 | T2+S1 | 0.6 | 10 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.20 | 0.80 | 0.00 | 13.719 | 0.97 | 0.20 | 0.901 | — |
| dossier_iso:opus48 | T2+S1 | 0.6 | 10 | (b) | 0.00 | 0.82 | 0.07 | 0.00 | 0.32 | 0.62 | 0.03 | 0.299 | 0.78 | 0.45 | 0.901 | 0.87; 0.13; 0.008 |
| dossier_iso:opus48 | T1+S2 | 0.3 | 0 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.23 | 0.77 | 0.00 | 17.731 | 0.97 | 0.23 | 0.905 | — |
| dossier_iso:opus48 | T1+S2 | 0.3 | 0 | (b) | 0.02 | 0.75 | 0.17 | 0.01 | 0.44 | 0.42 | 0.10 | 0.362 | 0.69 | 0.56 | 0.905 | 0.02; 0.97; 0.000 |
| dossier_iso:opus48 | T1+S2 | 0.3 | 5 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.27 | 0.73 | 0.00 | 17.730 | 0.98 | 0.27 | 0.891 | — |
| dossier_iso:opus48 | T1+S2 | 0.3 | 5 | (b) | 0.01 | 0.78 | 0.16 | 0.01 | 0.39 | 0.46 | 0.11 | 0.360 | 0.72 | 0.49 | 0.891 | 0.02; 0.97; 0.001 |
| dossier_iso:opus48 | T1+S2 | 0.3 | 10 | (a) | 0.00 | 0.96 | 0.00 | 0.00 | 0.28 | 0.72 | 0.00 | 17.978 | 0.96 | 0.28 | 0.891 | — |
| dossier_iso:opus48 | T1+S2 | 0.3 | 10 | (b) | 0.00 | 0.71 | 0.21 | 0.00 | 0.44 | 0.43 | 0.08 | 0.362 | 0.64 | 0.53 | 0.891 | 0.03; 0.96; 0.001 |
| dossier_iso:opus48 | T1+S2 | 0.6 | 0 | (a) | 0.00 | 0.95 | 0.00 | 0.00 | 0.20 | 0.80 | 0.00 | 13.812 | 0.95 | 0.20 | 0.893 | — |
| dossier_iso:opus48 | T1+S2 | 0.6 | 0 | (b) | 0.02 | 0.68 | 0.22 | 0.00 | 0.34 | 0.37 | 0.22 | 0.403 | 0.61 | 0.41 | 0.893 | 0.01; 0.98; 0.001 |
| dossier_iso:opus48 | T1+S2 | 0.6 | 5 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.20 | 0.80 | 0.00 | 14.273 | 0.98 | 0.20 | 0.895 | — |
| dossier_iso:opus48 | T1+S2 | 0.6 | 5 | (b) | 0.01 | 0.71 | 0.22 | 0.02 | 0.30 | 0.43 | 0.20 | 0.401 | 0.64 | 0.40 | 0.895 | 0.03; 0.97; 0.001 |
| dossier_iso:opus48 | T1+S2 | 0.6 | 10 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.28 | 0.72 | 0.00 | 15.025 | 0.97 | 0.28 | 0.892 | — |
| dossier_iso:opus48 | T1+S2 | 0.6 | 10 | (b) | 0.02 | 0.71 | 0.23 | 0.01 | 0.25 | 0.44 | 0.22 | 0.392 | 0.65 | 0.35 | 0.892 | 0.03; 0.97; 0.001 |
| dossier_iso:opus48 | T2+S2 | 0.3 | 0 | (a) | 0.00 | 0.95 | 0.00 | 0.00 | 0.21 | 0.79 | 0.00 | 13.886 | 0.95 | 0.21 | 0.897 | — |
| dossier_iso:opus48 | T2+S2 | 0.3 | 0 | (b) | 0.00 | 0.84 | 0.01 | 0.00 | 0.33 | 0.63 | 0.01 | 0.274 | 0.83 | 0.46 | 0.897 | 0.93; 0.07; 0.006 |
| dossier_iso:opus48 | T2+S2 | 0.3 | 5 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.23 | 0.77 | 0.00 | 13.792 | 0.98 | 0.23 | 0.893 | — |
| dossier_iso:opus48 | T2+S2 | 0.3 | 5 | (b) | 0.00 | 0.87 | 0.03 | 0.00 | 0.35 | 0.62 | 0.00 | 0.278 | 0.86 | 0.46 | 0.893 | 0.96; 0.04; 0.006 |
| dossier_iso:opus48 | T2+S2 | 0.3 | 10 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.22 | 0.78 | 0.00 | 14.084 | 0.98 | 0.22 | 0.895 | — |
| dossier_iso:opus48 | T2+S2 | 0.3 | 10 | (b) | 0.00 | 0.88 | 0.02 | 0.00 | 0.39 | 0.57 | 0.02 | 0.277 | 0.87 | 0.52 | 0.895 | 0.94; 0.06; 0.006 |
| dossier_iso:opus48 | T2+S2 | 0.6 | 0 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.17 | 0.83 | 0.00 | 11.152 | 0.98 | 0.17 | 0.893 | — |
| dossier_iso:opus48 | T2+S2 | 0.6 | 0 | (b) | 0.00 | 0.89 | 0.05 | 0.00 | 0.27 | 0.60 | 0.09 | 0.308 | 0.85 | 0.37 | 0.893 | 0.84; 0.16; 0.008 |
| dossier_iso:opus48 | T2+S2 | 0.6 | 5 | (a) | 0.00 | 0.99 | 0.00 | 0.00 | 0.15 | 0.85 | 0.00 | 11.433 | 0.99 | 0.15 | 0.899 | — |
| dossier_iso:opus48 | T2+S2 | 0.6 | 5 | (b) | 0.00 | 0.88 | 0.06 | 0.00 | 0.30 | 0.56 | 0.06 | 0.313 | 0.84 | 0.40 | 0.899 | 0.85; 0.15; 0.008 |
| dossier_iso:opus48 | T2+S2 | 0.6 | 10 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.16 | 0.84 | 0.00 | 11.773 | 0.97 | 0.16 | 0.893 | — |
| dossier_iso:opus48 | T2+S2 | 0.6 | 10 | (b) | 0.00 | 0.89 | 0.05 | 0.00 | 0.28 | 0.61 | 0.05 | 0.302 | 0.85 | 0.43 | 0.893 | 0.85; 0.15; 0.008 |
| dossier_iso:sonnet | T1 | 0.3 | 0 | (b) | 0.11 | 0.57 | 0.27 | 0.10 | 0.28 | 0.13 | 0.44 | 0.421 | 0.58 | 0.31 | 0.840 | 0.04; 0.96; 0.001 |
| dossier_iso:sonnet | T1 | 0.3 | 5 | (b) | 0.14 | 0.54 | 0.30 | 0.09 | 0.28 | 0.17 | 0.41 | 0.427 | 0.53 | 0.29 | 0.833 | 0.06; 0.94; 0.001 |
| dossier_iso:sonnet | T1 | 0.3 | 10 | (b) | 0.13 | 0.52 | 0.33 | 0.10 | 0.28 | 0.13 | 0.44 | 0.422 | 0.52 | 0.29 | 0.826 | 0.02; 0.98; 0.000 |
| dossier_iso:sonnet | T1 | 0.6 | 0 | (b) | 0.14 | 0.50 | 0.33 | 0.10 | 0.20 | 0.13 | 0.46 | 0.440 | 0.49 | 0.22 | 0.830 | 0.07; 0.93; 0.002 |
| dossier_iso:sonnet | T1 | 0.6 | 5 | (b) | 0.09 | 0.57 | 0.33 | 0.12 | 0.17 | 0.11 | 0.50 | 0.434 | 0.56 | 0.18 | 0.825 | 0.06; 0.93; 0.001 |
| dossier_iso:sonnet | T1 | 0.6 | 10 | (b) | 0.13 | 0.55 | 0.29 | 0.11 | 0.16 | 0.13 | 0.52 | 0.434 | 0.55 | 0.17 | 0.831 | 0.03; 0.96; 0.001 |
| dossier_iso:sonnet | T2 | 0.3 | 0 | (b) | 0.01 | 0.86 | 0.11 | 0.00 | 0.21 | 0.33 | 0.34 | 0.335 | 0.86 | 0.22 | 0.830 | 0.98; 0.02; 0.005 |
| dossier_iso:sonnet | T2 | 0.3 | 5 | (b) | 0.00 | 0.81 | 0.15 | 0.01 | 0.21 | 0.34 | 0.32 | 0.336 | 0.81 | 0.22 | 0.824 | 0.98; 0.02; 0.005 |
| dossier_iso:sonnet | T2 | 0.3 | 10 | (b) | 0.01 | 0.87 | 0.10 | 0.00 | 0.21 | 0.35 | 0.31 | 0.333 | 0.87 | 0.22 | 0.826 | 0.97; 0.03; 0.005 |
| dossier_iso:sonnet | T2 | 0.6 | 0 | (b) | 0.01 | 0.76 | 0.21 | 0.01 | 0.13 | 0.16 | 0.48 | 0.362 | 0.74 | 0.13 | 0.827 | 0.94; 0.06; 0.008 |
| dossier_iso:sonnet | T2 | 0.6 | 5 | (b) | 0.01 | 0.78 | 0.18 | 0.00 | 0.14 | 0.21 | 0.46 | 0.362 | 0.77 | 0.14 | 0.827 | 0.94; 0.06; 0.008 |
| dossier_iso:sonnet | T2 | 0.6 | 10 | (b) | 0.01 | 0.72 | 0.26 | 0.01 | 0.15 | 0.21 | 0.47 | 0.357 | 0.72 | 0.15 | 0.829 | 0.94; 0.06; 0.007 |
| dossier_iso:sonnet | T1+S1 | 0.3 | 0 | (a) | 0.00 | 0.44 | 0.54 | 0.00 | 0.35 | 0.02 | 0.60 | 22.473 | 0.44 | 0.35 | 0.897 | — |
| dossier_iso:sonnet | T1+S1 | 0.3 | 0 | (b) | 0.13 | 0.54 | 0.27 | 0.13 | 0.43 | 0.27 | 0.16 | 0.375 | 0.54 | 0.46 | 0.897 | 0.04; 0.96; 0.001 |
| dossier_iso:sonnet | T1+S1 | 0.3 | 5 | (a) | 0.00 | 0.44 | 0.53 | 0.00 | 0.37 | 0.02 | 0.58 | 22.184 | 0.44 | 0.37 | 0.902 | — |
| dossier_iso:sonnet | T1+S1 | 0.3 | 5 | (b) | 0.13 | 0.49 | 0.25 | 0.08 | 0.46 | 0.33 | 0.11 | 0.373 | 0.47 | 0.47 | 0.902 | 0.05; 0.94; 0.001 |
| dossier_iso:sonnet | T1+S1 | 0.3 | 10 | (a) | 0.00 | 0.37 | 0.60 | 0.00 | 0.42 | 0.02 | 0.51 | 22.776 | 0.37 | 0.42 | 0.904 | — |
| dossier_iso:sonnet | T1+S1 | 0.3 | 10 | (b) | 0.14 | 0.45 | 0.28 | 0.08 | 0.44 | 0.34 | 0.13 | 0.374 | 0.44 | 0.45 | 0.904 | 0.05; 0.95; 0.001 |
| dossier_iso:sonnet | T1+S1 | 0.6 | 0 | (a) | 0.00 | 0.60 | 0.38 | 0.00 | 0.41 | 0.13 | 0.41 | 18.014 | 0.60 | 0.41 | 0.898 | — |
| dossier_iso:sonnet | T1+S1 | 0.6 | 0 | (b) | 0.14 | 0.44 | 0.35 | 0.11 | 0.29 | 0.28 | 0.28 | 0.416 | 0.45 | 0.29 | 0.898 | 0.04; 0.96; 0.001 |
| dossier_iso:sonnet | T1+S1 | 0.6 | 5 | (a) | 0.00 | 0.57 | 0.41 | 0.00 | 0.38 | 0.14 | 0.40 | 18.117 | 0.57 | 0.38 | 0.896 | — |
| dossier_iso:sonnet | T1+S1 | 0.6 | 5 | (b) | 0.10 | 0.50 | 0.32 | 0.08 | 0.37 | 0.26 | 0.25 | 0.416 | 0.50 | 0.39 | 0.896 | 0.04; 0.96; 0.001 |
| dossier_iso:sonnet | T1+S1 | 0.6 | 10 | (a) | 0.00 | 0.55 | 0.42 | 0.00 | 0.39 | 0.12 | 0.44 | 18.548 | 0.55 | 0.39 | 0.891 | — |
| dossier_iso:sonnet | T1+S1 | 0.6 | 10 | (b) | 0.13 | 0.45 | 0.33 | 0.09 | 0.34 | 0.27 | 0.27 | 0.410 | 0.44 | 0.35 | 0.891 | 0.05; 0.95; 0.001 |
| dossier_iso:sonnet | T2+S1 | 0.3 | 0 | (a) | 0.00 | 0.54 | 0.43 | 0.00 | 0.41 | 0.12 | 0.42 | 18.395 | 0.54 | 0.41 | 0.896 | — |
| dossier_iso:sonnet | T2+S1 | 0.3 | 0 | (b) | 0.01 | 0.79 | 0.09 | 0.01 | 0.47 | 0.49 | 0.02 | 0.292 | 0.78 | 0.48 | 0.896 | 0.97; 0.03; 0.005 |
| dossier_iso:sonnet | T2+S1 | 0.3 | 5 | (a) | 0.00 | 0.54 | 0.43 | 0.00 | 0.39 | 0.12 | 0.46 | 18.527 | 0.54 | 0.39 | 0.899 | — |
| dossier_iso:sonnet | T2+S1 | 0.3 | 5 | (b) | 0.00 | 0.78 | 0.08 | 0.00 | 0.45 | 0.49 | 0.03 | 0.291 | 0.77 | 0.47 | 0.899 | 0.97; 0.03; 0.004 |
| dossier_iso:sonnet | T2+S1 | 0.3 | 10 | (a) | 0.00 | 0.56 | 0.41 | 0.00 | 0.46 | 0.10 | 0.38 | 18.300 | 0.56 | 0.46 | 0.897 | — |
| dossier_iso:sonnet | T2+S1 | 0.3 | 10 | (b) | 0.00 | 0.77 | 0.10 | 0.00 | 0.43 | 0.51 | 0.03 | 0.289 | 0.79 | 0.46 | 0.897 | 0.97; 0.03; 0.005 |
| dossier_iso:sonnet | T2+S1 | 0.6 | 0 | (a) | 0.00 | 0.68 | 0.29 | 0.00 | 0.45 | 0.29 | 0.23 | 15.191 | 0.68 | 0.45 | 0.892 | — |
| dossier_iso:sonnet | T2+S1 | 0.6 | 0 | (b) | 0.00 | 0.77 | 0.14 | 0.01 | 0.28 | 0.46 | 0.18 | 0.326 | 0.77 | 0.28 | 0.892 | 0.94; 0.06; 0.007 |
| dossier_iso:sonnet | T2+S1 | 0.6 | 5 | (a) | 0.00 | 0.73 | 0.24 | 0.00 | 0.41 | 0.27 | 0.29 | 15.099 | 0.73 | 0.41 | 0.892 | — |
| dossier_iso:sonnet | T2+S1 | 0.6 | 5 | (b) | 0.00 | 0.74 | 0.17 | 0.00 | 0.35 | 0.46 | 0.12 | 0.326 | 0.74 | 0.37 | 0.892 | 0.94; 0.06; 0.007 |
| dossier_iso:sonnet | T2+S1 | 0.6 | 10 | (a) | 0.00 | 0.76 | 0.20 | 0.00 | 0.49 | 0.21 | 0.27 | 15.937 | 0.76 | 0.49 | 0.888 | — |
| dossier_iso:sonnet | T2+S1 | 0.6 | 10 | (b) | 0.01 | 0.74 | 0.15 | 0.01 | 0.25 | 0.51 | 0.17 | 0.318 | 0.75 | 0.26 | 0.888 | 0.94; 0.06; 0.007 |
| dossier_iso:sonnet | T1+S2 | 0.3 | 0 | (a) | 0.00 | 0.49 | 0.49 | 0.00 | 0.42 | 0.05 | 0.50 | 20.591 | 0.49 | 0.42 | 0.897 | — |
| dossier_iso:sonnet | T1+S2 | 0.3 | 0 | (b) | 0.11 | 0.59 | 0.22 | 0.07 | 0.43 | 0.30 | 0.18 | 0.380 | 0.59 | 0.44 | 0.897 | 0.05; 0.95; 0.001 |
| dossier_iso:sonnet | T1+S2 | 0.3 | 5 | (a) | 0.00 | 0.53 | 0.42 | 0.00 | 0.35 | 0.06 | 0.55 | 20.530 | 0.53 | 0.35 | 0.896 | — |
| dossier_iso:sonnet | T1+S2 | 0.3 | 5 | (b) | 0.11 | 0.57 | 0.24 | 0.09 | 0.32 | 0.35 | 0.22 | 0.380 | 0.58 | 0.34 | 0.896 | 0.06; 0.93; 0.001 |
| dossier_iso:sonnet | T1+S2 | 0.3 | 10 | (a) | 0.00 | 0.48 | 0.51 | 0.00 | 0.42 | 0.04 | 0.50 | 20.888 | 0.48 | 0.42 | 0.893 | — |
| dossier_iso:sonnet | T1+S2 | 0.3 | 10 | (b) | 0.14 | 0.56 | 0.26 | 0.10 | 0.41 | 0.32 | 0.15 | 0.379 | 0.58 | 0.43 | 0.893 | 0.06; 0.94; 0.001 |
| dossier_iso:sonnet | T1+S2 | 0.6 | 0 | (a) | 0.00 | 0.65 | 0.33 | 0.00 | 0.42 | 0.19 | 0.34 | 16.459 | 0.65 | 0.42 | 0.893 | — |
| dossier_iso:sonnet | T1+S2 | 0.6 | 0 | (b) | 0.12 | 0.50 | 0.31 | 0.11 | 0.34 | 0.20 | 0.32 | 0.430 | 0.50 | 0.34 | 0.893 | 0.04; 0.96; 0.001 |
| dossier_iso:sonnet | T1+S2 | 0.6 | 5 | (a) | 0.00 | 0.66 | 0.29 | 0.00 | 0.40 | 0.20 | 0.36 | 16.504 | 0.66 | 0.40 | 0.896 | — |
| dossier_iso:sonnet | T1+S2 | 0.6 | 5 | (b) | 0.12 | 0.51 | 0.32 | 0.11 | 0.32 | 0.22 | 0.32 | 0.427 | 0.52 | 0.32 | 0.896 | 0.03; 0.96; 0.001 |
| dossier_iso:sonnet | T1+S2 | 0.6 | 10 | (a) | 0.00 | 0.66 | 0.33 | 0.00 | 0.41 | 0.17 | 0.39 | 17.131 | 0.66 | 0.41 | 0.898 | — |
| dossier_iso:sonnet | T1+S2 | 0.6 | 10 | (b) | 0.11 | 0.49 | 0.34 | 0.12 | 0.36 | 0.23 | 0.27 | 0.416 | 0.50 | 0.37 | 0.898 | 0.04; 0.96; 0.001 |
| dossier_iso:sonnet | T2+S2 | 0.3 | 0 | (a) | 0.00 | 0.62 | 0.36 | 0.00 | 0.38 | 0.25 | 0.31 | 16.257 | 0.62 | 0.38 | 0.893 | — |
| dossier_iso:sonnet | T2+S2 | 0.3 | 0 | (b) | 0.00 | 0.82 | 0.10 | 0.00 | 0.37 | 0.53 | 0.06 | 0.294 | 0.82 | 0.39 | 0.893 | 0.98; 0.02; 0.005 |
| dossier_iso:sonnet | T2+S2 | 0.3 | 5 | (a) | 0.00 | 0.66 | 0.32 | 0.00 | 0.46 | 0.22 | 0.28 | 16.178 | 0.66 | 0.46 | 0.893 | — |
| dossier_iso:sonnet | T2+S2 | 0.3 | 5 | (b) | 0.00 | 0.82 | 0.07 | 0.01 | 0.42 | 0.49 | 0.06 | 0.293 | 0.82 | 0.43 | 0.893 | 0.98; 0.02; 0.005 |
| dossier_iso:sonnet | T2+S2 | 0.3 | 10 | (a) | 0.00 | 0.69 | 0.29 | 0.00 | 0.42 | 0.20 | 0.34 | 16.367 | 0.69 | 0.42 | 0.897 | — |
| dossier_iso:sonnet | T2+S2 | 0.3 | 10 | (b) | 0.00 | 0.86 | 0.06 | 0.00 | 0.40 | 0.52 | 0.05 | 0.290 | 0.86 | 0.42 | 0.897 | 0.97; 0.03; 0.005 |
| dossier_iso:sonnet | T2+S2 | 0.6 | 0 | (a) | 0.00 | 0.87 | 0.11 | 0.00 | 0.42 | 0.38 | 0.16 | 13.115 | 0.87 | 0.42 | 0.894 | — |
| dossier_iso:sonnet | T2+S2 | 0.6 | 0 | (b) | 0.00 | 0.78 | 0.16 | 0.00 | 0.27 | 0.46 | 0.21 | 0.334 | 0.80 | 0.26 | 0.894 | 0.90; 0.10; 0.007 |
| dossier_iso:sonnet | T2+S2 | 0.6 | 5 | (a) | 0.00 | 0.85 | 0.11 | 0.00 | 0.42 | 0.40 | 0.15 | 13.135 | 0.85 | 0.42 | 0.896 | — |
| dossier_iso:sonnet | T2+S2 | 0.6 | 5 | (b) | 0.01 | 0.77 | 0.17 | 0.00 | 0.24 | 0.40 | 0.28 | 0.331 | 0.78 | 0.25 | 0.896 | 0.96; 0.04; 0.007 |
| dossier_iso:sonnet | T2+S2 | 0.6 | 10 | (a) | 0.00 | 0.85 | 0.12 | 0.00 | 0.39 | 0.38 | 0.18 | 13.566 | 0.85 | 0.39 | 0.896 | — |
| dossier_iso:sonnet | T2+S2 | 0.6 | 10 | (b) | 0.00 | 0.82 | 0.10 | 0.00 | 0.27 | 0.46 | 0.18 | 0.321 | 0.82 | 0.27 | 0.896 | 0.92; 0.08; 0.007 |
| dossier_live:opus48 | T1 | 0.3 | 0 | (b) | 0.00 | 0.18 | 0.00 | 0.01 | 0.13 | 0.41 | 0.00 | 0.276 | 0.18 | 0.35 | 0.830 | 0.00; 0.15; 0.198 |
| dossier_live:opus48 | T1 | 0.3 | 5 | (b) | 0.00 | 0.19 | 0.00 | 0.01 | 0.17 | 0.36 | 0.00 | 0.277 | 0.18 | 0.43 | 0.832 | 0.00; 0.17; 0.183 |
| dossier_live:opus48 | T1 | 0.3 | 10 | (b) | 0.00 | 0.16 | 0.00 | 0.00 | 0.10 | 0.36 | 0.00 | 0.290 | 0.16 | 0.31 | 0.832 | 0.00; 0.19; 0.180 |
| dossier_live:opus48 | T1 | 0.6 | 0 | (b) | 0.00 | 0.15 | 0.00 | 0.02 | 0.13 | 0.33 | 0.00 | 0.288 | 0.15 | 0.33 | 0.832 | 0.00; 0.14; 0.199 |
| dossier_live:opus48 | T1 | 0.6 | 5 | (b) | 0.00 | 0.19 | 0.00 | 0.01 | 0.13 | 0.32 | 0.00 | 0.288 | 0.19 | 0.34 | 0.826 | 0.00; 0.17; 0.180 |
| dossier_live:opus48 | T1 | 0.6 | 10 | (b) | 0.00 | 0.18 | 0.00 | 0.01 | 0.14 | 0.36 | 0.00 | 0.288 | 0.17 | 0.35 | 0.827 | 0.00; 0.16; 0.191 |
| dossier_live:opus48 | T2 | 0.3 | 0 | (b) | 0.00 | 0.81 | 0.00 | 0.00 | 0.19 | 0.79 | 0.00 | 0.173 | 0.81 | 0.78 | 0.837 | 0.00; 0.64; 0.016 |
| dossier_live:opus48 | T2 | 0.3 | 5 | (b) | 0.00 | 0.83 | 0.00 | 0.00 | 0.20 | 0.79 | 0.00 | 0.172 | 0.83 | 0.76 | 0.831 | 0.00; 0.61; 0.019 |
| dossier_live:opus48 | T2 | 0.3 | 10 | (b) | 0.00 | 0.84 | 0.00 | 0.00 | 0.17 | 0.80 | 0.00 | 0.175 | 0.84 | 0.73 | 0.830 | 0.00; 0.62; 0.018 |
| dossier_live:opus48 | T2 | 0.6 | 0 | (b) | 0.00 | 0.73 | 0.00 | 0.00 | 0.28 | 0.66 | 0.00 | 0.181 | 0.73 | 0.77 | 0.835 | 0.00; 0.55; 0.030 |
| dossier_live:opus48 | T2 | 0.6 | 5 | (b) | 0.00 | 0.78 | 0.00 | 0.00 | 0.26 | 0.68 | 0.00 | 0.171 | 0.78 | 0.80 | 0.827 | 0.00; 0.57; 0.032 |
| dossier_live:opus48 | T2 | 0.6 | 10 | (b) | 0.00 | 0.76 | 0.00 | 0.00 | 0.24 | 0.72 | 0.00 | 0.174 | 0.76 | 0.76 | 0.836 | 0.00; 0.63; 0.028 |
| dossier_live:opus48 | T1+S1 | 0.3 | 0 | (a) | 0.00 | 0.63 | 0.35 | 0.00 | 0.40 | 0.17 | 0.39 | 15.066 | 0.63 | 0.40 | 0.898 | — |
| dossier_live:opus48 | T1+S1 | 0.3 | 0 | (b) | 0.00 | 0.15 | 0.00 | 0.01 | 0.12 | 0.33 | 0.00 | 0.235 | 0.15 | 0.33 | 0.898 | 0.00; 0.16; 0.187 |
| dossier_live:opus48 | T1+S1 | 0.3 | 5 | (a) | 0.00 | 0.62 | 0.34 | 0.00 | 0.45 | 0.14 | 0.36 | 15.226 | 0.62 | 0.45 | 0.898 | — |
| dossier_live:opus48 | T1+S1 | 0.3 | 5 | (b) | 0.00 | 0.22 | 0.00 | 0.02 | 0.19 | 0.35 | 0.00 | 0.217 | 0.22 | 0.44 | 0.898 | 0.00; 0.15; 0.169 |
| dossier_live:opus48 | T1+S1 | 0.3 | 10 | (a) | 0.00 | 0.59 | 0.39 | 0.00 | 0.43 | 0.13 | 0.41 | 15.657 | 0.59 | 0.43 | 0.900 | — |
| dossier_live:opus48 | T1+S1 | 0.3 | 10 | (b) | 0.00 | 0.18 | 0.00 | 0.02 | 0.14 | 0.42 | 0.00 | 0.237 | 0.18 | 0.44 | 0.900 | 0.00; 0.14; 0.185 |
| dossier_live:opus48 | T1+S1 | 0.6 | 0 | (a) | 0.00 | 0.77 | 0.20 | 0.00 | 0.45 | 0.33 | 0.20 | 11.894 | 0.77 | 0.45 | 0.895 | — |
| dossier_live:opus48 | T1+S1 | 0.6 | 0 | (b) | 0.00 | 0.11 | 0.00 | 0.01 | 0.09 | 0.29 | 0.00 | 0.189 | 0.11 | 0.29 | 0.895 | 0.00; 0.16; 0.223 |
| dossier_live:opus48 | T1+S1 | 0.6 | 5 | (a) | 0.00 | 0.81 | 0.16 | 0.00 | 0.40 | 0.33 | 0.24 | 12.353 | 0.81 | 0.40 | 0.891 | — |
| dossier_live:opus48 | T1+S1 | 0.6 | 5 | (b) | 0.00 | 0.12 | 0.00 | 0.02 | 0.16 | 0.29 | 0.00 | 0.200 | 0.12 | 0.36 | 0.891 | 0.00; 0.17; 0.207 |
| dossier_live:opus48 | T1+S1 | 0.6 | 10 | (a) | 0.00 | 0.75 | 0.24 | 0.00 | 0.40 | 0.27 | 0.30 | 13.598 | 0.75 | 0.40 | 0.891 | — |
| dossier_live:opus48 | T1+S1 | 0.6 | 10 | (b) | 0.00 | 0.15 | 0.00 | 0.01 | 0.17 | 0.29 | 0.00 | 0.210 | 0.15 | 0.36 | 0.891 | 0.00; 0.20; 0.193 |
| dossier_live:opus48 | T2+S1 | 0.3 | 0 | (a) | 0.00 | 0.77 | 0.19 | 0.00 | 0.42 | 0.34 | 0.21 | 12.358 | 0.77 | 0.42 | 0.898 | — |
| dossier_live:opus48 | T2+S1 | 0.3 | 0 | (b) | 0.00 | 0.81 | 0.00 | 0.00 | 0.24 | 0.73 | 0.00 | 0.127 | 0.81 | 0.86 | 0.898 | 0.00; 0.63; 0.017 |
| dossier_live:opus48 | T2+S1 | 0.3 | 5 | (a) | 0.00 | 0.79 | 0.18 | 0.00 | 0.46 | 0.28 | 0.20 | 12.419 | 0.79 | 0.46 | 0.897 | — |
| dossier_live:opus48 | T2+S1 | 0.3 | 5 | (b) | 0.00 | 0.74 | 0.00 | 0.00 | 0.22 | 0.76 | 0.00 | 0.128 | 0.74 | 0.90 | 0.897 | 0.00; 0.68; 0.017 |
| dossier_live:opus48 | T2+S1 | 0.3 | 10 | (a) | 0.00 | 0.76 | 0.20 | 0.00 | 0.43 | 0.29 | 0.24 | 12.761 | 0.76 | 0.43 | 0.899 | — |
| dossier_live:opus48 | T2+S1 | 0.3 | 10 | (b) | 0.00 | 0.79 | 0.00 | 0.00 | 0.26 | 0.72 | 0.00 | 0.135 | 0.79 | 0.86 | 0.899 | 0.00; 0.63; 0.017 |
| dossier_live:opus48 | T2+S1 | 0.6 | 0 | (a) | 0.00 | 0.93 | 0.04 | 0.00 | 0.41 | 0.50 | 0.05 | 9.854 | 0.93 | 0.41 | 0.896 | — |
| dossier_live:opus48 | T2+S1 | 0.6 | 0 | (b) | 0.00 | 0.66 | 0.00 | 0.00 | 0.31 | 0.61 | 0.00 | 0.110 | 0.66 | 0.83 | 0.896 | 0.00; 0.60; 0.038 |
| dossier_live:opus48 | T2+S1 | 0.6 | 5 | (a) | 0.00 | 0.89 | 0.08 | 0.00 | 0.43 | 0.43 | 0.09 | 10.442 | 0.89 | 0.43 | 0.896 | — |
| dossier_live:opus48 | T2+S1 | 0.6 | 5 | (b) | 0.00 | 0.62 | 0.00 | 0.00 | 0.28 | 0.65 | 0.00 | 0.114 | 0.62 | 0.83 | 0.896 | 0.00; 0.61; 0.040 |
| dossier_live:opus48 | T2+S1 | 0.6 | 10 | (a) | 0.00 | 0.85 | 0.13 | 0.00 | 0.46 | 0.39 | 0.14 | 11.124 | 0.85 | 0.46 | 0.903 | — |
| dossier_live:opus48 | T2+S1 | 0.6 | 10 | (b) | 0.00 | 0.75 | 0.00 | 0.00 | 0.30 | 0.67 | 0.00 | 0.111 | 0.75 | 0.87 | 0.903 | 0.00; 0.63; 0.021 |
| dossier_live:opus48 | T1+S2 | 0.3 | 0 | (a) | 0.00 | 0.72 | 0.24 | 0.00 | 0.47 | 0.23 | 0.27 | 13.905 | 0.72 | 0.47 | 0.895 | — |
| dossier_live:opus48 | T1+S2 | 0.3 | 0 | (b) | 0.00 | 0.17 | 0.00 | 0.00 | 0.15 | 0.36 | 0.00 | 0.243 | 0.17 | 0.40 | 0.895 | 0.00; 0.15; 0.191 |
| dossier_live:opus48 | T1+S2 | 0.3 | 5 | (a) | 0.00 | 0.69 | 0.27 | 0.00 | 0.40 | 0.22 | 0.33 | 14.096 | 0.69 | 0.40 | 0.895 | — |
| dossier_live:opus48 | T1+S2 | 0.3 | 5 | (b) | 0.00 | 0.17 | 0.00 | 0.01 | 0.16 | 0.36 | 0.00 | 0.200 | 0.17 | 0.41 | 0.895 | 0.00; 0.15; 0.206 |
| dossier_live:opus48 | T1+S2 | 0.3 | 10 | (a) | 0.00 | 0.67 | 0.29 | 0.00 | 0.41 | 0.16 | 0.40 | 14.407 | 0.67 | 0.41 | 0.903 | — |
| dossier_live:opus48 | T1+S2 | 0.3 | 10 | (b) | 0.00 | 0.15 | 0.00 | 0.01 | 0.15 | 0.38 | 0.00 | 0.214 | 0.15 | 0.44 | 0.903 | 0.00; 0.15; 0.190 |
| dossier_live:opus48 | T1+S2 | 0.6 | 0 | (a) | 0.00 | 0.88 | 0.10 | 0.00 | 0.42 | 0.43 | 0.12 | 10.940 | 0.88 | 0.42 | 0.893 | — |
| dossier_live:opus48 | T1+S2 | 0.6 | 0 | (b) | 0.00 | 0.08 | 0.00 | 0.00 | 0.12 | 0.25 | 0.00 | 0.194 | 0.08 | 0.29 | 0.893 | 0.00; 0.16; 0.242 |
| dossier_live:opus48 | T1+S2 | 0.6 | 5 | (a) | 0.00 | 0.89 | 0.08 | 0.00 | 0.39 | 0.44 | 0.14 | 11.289 | 0.89 | 0.39 | 0.891 | — |
| dossier_live:opus48 | T1+S2 | 0.6 | 5 | (b) | 0.00 | 0.10 | 0.00 | 0.00 | 0.13 | 0.29 | 0.00 | 0.221 | 0.10 | 0.33 | 0.891 | 0.00; 0.14; 0.241 |
| dossier_live:opus48 | T1+S2 | 0.6 | 10 | (a) | 0.00 | 0.73 | 0.21 | 0.00 | 0.40 | 0.37 | 0.19 | 12.536 | 0.73 | 0.40 | 0.900 | — |
| dossier_live:opus48 | T1+S2 | 0.6 | 10 | (b) | 0.00 | 0.16 | 0.00 | 0.00 | 0.11 | 0.31 | 0.00 | 0.212 | 0.16 | 0.35 | 0.900 | 0.00; 0.20; 0.210 |
| dossier_live:opus48 | T2+S2 | 0.3 | 0 | (a) | 0.00 | 0.88 | 0.07 | 0.00 | 0.43 | 0.42 | 0.13 | 10.885 | 0.88 | 0.43 | 0.893 | — |
| dossier_live:opus48 | T2+S2 | 0.3 | 0 | (b) | 0.00 | 0.74 | 0.00 | 0.00 | 0.24 | 0.73 | 0.00 | 0.129 | 0.74 | 0.86 | 0.893 | 0.00; 0.63; 0.019 |
| dossier_live:opus48 | T2+S2 | 0.3 | 5 | (a) | 0.00 | 0.88 | 0.10 | 0.00 | 0.42 | 0.38 | 0.14 | 11.093 | 0.88 | 0.42 | 0.894 | — |
| dossier_live:opus48 | T2+S2 | 0.3 | 5 | (b) | 0.00 | 0.79 | 0.00 | 0.00 | 0.23 | 0.76 | 0.00 | 0.133 | 0.79 | 0.82 | 0.894 | 0.00; 0.64; 0.017 |
| dossier_live:opus48 | T2+S2 | 0.3 | 10 | (a) | 0.00 | 0.86 | 0.12 | 0.00 | 0.42 | 0.41 | 0.15 | 11.359 | 0.86 | 0.42 | 0.896 | — |
| dossier_live:opus48 | T2+S2 | 0.3 | 10 | (b) | 0.00 | 0.79 | 0.00 | 0.00 | 0.23 | 0.77 | 0.00 | 0.129 | 0.79 | 0.83 | 0.896 | 0.00; 0.63; 0.016 |
| dossier_live:opus48 | T2+S2 | 0.6 | 0 | (a) | 0.00 | 0.96 | 0.01 | 0.00 | 0.33 | 0.61 | 0.02 | 8.772 | 0.96 | 0.33 | 0.895 | — |
| dossier_live:opus48 | T2+S2 | 0.6 | 0 | (b) | 0.00 | 0.64 | 0.00 | 0.00 | 0.24 | 0.67 | 0.00 | 0.106 | 0.64 | 0.80 | 0.895 | 0.00; 0.58; 0.046 |
| dossier_live:opus48 | T2+S2 | 0.6 | 5 | (a) | 0.00 | 0.97 | 0.01 | 0.00 | 0.38 | 0.58 | 0.02 | 9.026 | 0.97 | 0.38 | 0.891 | — |
| dossier_live:opus48 | T2+S2 | 0.6 | 5 | (b) | 0.00 | 0.69 | 0.00 | 0.00 | 0.27 | 0.66 | 0.00 | 0.106 | 0.69 | 0.80 | 0.891 | 0.00; 0.58; 0.029 |
| dossier_live:opus48 | T2+S2 | 0.6 | 10 | (a) | 0.00 | 0.91 | 0.05 | 0.00 | 0.43 | 0.48 | 0.06 | 9.957 | 0.91 | 0.43 | 0.900 | — |
| dossier_live:opus48 | T2+S2 | 0.6 | 10 | (b) | 0.00 | 0.75 | 0.00 | 0.00 | 0.26 | 0.69 | 0.00 | 0.119 | 0.75 | 0.83 | 0.900 | 0.00; 0.59; 0.028 |
| dossier_live:sonnet | T1 | 0.3 | 0 | (b) | 0.00 | 0.71 | 0.27 | 0.00 | 0.36 | 0.21 | 0.39 | 0.427 | 0.66 | 0.39 | 0.832 | 0.05; 0.95; 0.001 |
| dossier_live:sonnet | T1 | 0.3 | 5 | (b) | 0.00 | 0.69 | 0.28 | 0.00 | 0.31 | 0.25 | 0.39 | 0.422 | 0.63 | 0.36 | 0.839 | 0.06; 0.94; 0.001 |
| dossier_live:sonnet | T1 | 0.3 | 10 | (b) | 0.00 | 0.68 | 0.26 | 0.00 | 0.30 | 0.21 | 0.43 | 0.422 | 0.65 | 0.35 | 0.833 | 0.05; 0.95; 0.001 |
| dossier_live:sonnet | T1 | 0.6 | 0 | (b) | 0.00 | 0.65 | 0.31 | 0.00 | 0.23 | 0.18 | 0.50 | 0.429 | 0.62 | 0.26 | 0.826 | 0.05; 0.95; 0.001 |
| dossier_live:sonnet | T1 | 0.6 | 5 | (b) | 0.00 | 0.66 | 0.31 | 0.00 | 0.21 | 0.14 | 0.53 | 0.432 | 0.61 | 0.23 | 0.826 | 0.05; 0.95; 0.001 |
| dossier_live:sonnet | T1 | 0.6 | 10 | (b) | 0.00 | 0.70 | 0.27 | 0.00 | 0.24 | 0.18 | 0.50 | 0.434 | 0.67 | 0.28 | 0.830 | 0.04; 0.96; 0.001 |
| dossier_live:sonnet | T2 | 0.3 | 0 | (b) | 0.00 | 0.86 | 0.11 | 0.00 | 0.26 | 0.42 | 0.25 | 0.339 | 0.83 | 0.30 | 0.835 | 0.98; 0.02; 0.005 |
| dossier_live:sonnet | T2 | 0.3 | 5 | (b) | 0.00 | 0.87 | 0.10 | 0.00 | 0.27 | 0.39 | 0.26 | 0.333 | 0.82 | 0.33 | 0.830 | 0.96; 0.04; 0.005 |
| dossier_live:sonnet | T2 | 0.3 | 10 | (b) | 0.00 | 0.86 | 0.12 | 0.00 | 0.27 | 0.39 | 0.28 | 0.335 | 0.81 | 0.29 | 0.831 | 0.98; 0.02; 0.005 |
| dossier_live:sonnet | T2 | 0.6 | 0 | (b) | 0.00 | 0.78 | 0.19 | 0.00 | 0.19 | 0.29 | 0.40 | 0.367 | 0.75 | 0.22 | 0.827 | 0.90; 0.10; 0.008 |
| dossier_live:sonnet | T2 | 0.6 | 5 | (b) | 0.00 | 0.76 | 0.19 | 0.00 | 0.17 | 0.31 | 0.38 | 0.367 | 0.73 | 0.20 | 0.828 | 0.87; 0.13; 0.008 |
| dossier_live:sonnet | T2 | 0.6 | 10 | (b) | 0.00 | 0.80 | 0.17 | 0.00 | 0.19 | 0.32 | 0.36 | 0.362 | 0.77 | 0.25 | 0.828 | 0.90; 0.10; 0.008 |
| dossier_live:sonnet | T1+S1 | 0.3 | 0 | (a) | 0.00 | 0.97 | 0.00 | 0.09 | 0.11 | 0.80 | 0.00 | 25.130 | 0.97 | 0.11 | 0.900 | — |
| dossier_live:sonnet | T1+S1 | 0.3 | 0 | (b) | 0.00 | 0.69 | 0.24 | 0.00 | 0.55 | 0.37 | 0.08 | 0.366 | 0.65 | 0.59 | 0.900 | 0.06; 0.94; 0.001 |
| dossier_live:sonnet | T1+S1 | 0.3 | 5 | (a) | 0.00 | 0.98 | 0.00 | 0.08 | 0.09 | 0.83 | 0.00 | 25.197 | 0.98 | 0.09 | 0.898 | — |
| dossier_live:sonnet | T1+S1 | 0.3 | 5 | (b) | 0.00 | 0.61 | 0.28 | 0.00 | 0.55 | 0.35 | 0.08 | 0.367 | 0.55 | 0.64 | 0.898 | 0.07; 0.93; 0.002 |
| dossier_live:sonnet | T1+S1 | 0.3 | 10 | (a) | 0.00 | 0.95 | 0.00 | 0.01 | 0.08 | 0.91 | 0.00 | 25.412 | 0.95 | 0.08 | 0.891 | — |
| dossier_live:sonnet | T1+S1 | 0.3 | 10 | (b) | 0.00 | 0.63 | 0.25 | 0.00 | 0.47 | 0.44 | 0.07 | 0.364 | 0.58 | 0.55 | 0.891 | 0.08; 0.92; 0.002 |
| dossier_live:sonnet | T1+S1 | 0.6 | 0 | (b) | 0.00 | 0.57 | 0.30 | 0.00 | 0.45 | 0.37 | 0.16 | 0.414 | 0.55 | 0.53 | 0.894 | 0.04; 0.95; 0.001 |
| dossier_live:sonnet | T1+S1 | 0.6 | 5 | (b) | 0.00 | 0.58 | 0.32 | 0.00 | 0.47 | 0.31 | 0.18 | 0.409 | 0.52 | 0.54 | 0.888 | 0.04; 0.96; 0.001 |
| dossier_live:sonnet | T1+S1 | 0.6 | 10 | (b) | 0.00 | 0.59 | 0.30 | 0.00 | 0.39 | 0.40 | 0.19 | 0.402 | 0.55 | 0.46 | 0.897 | 0.02; 0.97; 0.001 |
| dossier_live:sonnet | T2+S1 | 0.3 | 0 | (a) | 0.00 | 0.97 | 0.00 | 0.06 | 0.12 | 0.82 | 0.00 | 20.583 | 0.97 | 0.12 | 0.894 | — |
| dossier_live:sonnet | T2+S1 | 0.3 | 0 | (b) | 0.00 | 0.79 | 0.06 | 0.00 | 0.53 | 0.45 | 0.01 | 0.285 | 0.75 | 0.62 | 0.894 | 0.97; 0.03; 0.006 |
| dossier_live:sonnet | T2+S1 | 0.3 | 5 | (a) | 0.00 | 0.97 | 0.00 | 0.02 | 0.10 | 0.88 | 0.00 | 20.876 | 0.97 | 0.10 | 0.892 | — |
| dossier_live:sonnet | T2+S1 | 0.3 | 5 | (b) | 0.00 | 0.81 | 0.05 | 0.00 | 0.55 | 0.43 | 0.02 | 0.285 | 0.79 | 0.62 | 0.892 | 0.97; 0.03; 0.005 |
| dossier_live:sonnet | T2+S1 | 0.3 | 10 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.11 | 0.89 | 0.00 | 20.888 | 0.98 | 0.11 | 0.903 | — |
| dossier_live:sonnet | T2+S1 | 0.3 | 10 | (b) | 0.00 | 0.81 | 0.06 | 0.00 | 0.55 | 0.42 | 0.01 | 0.285 | 0.78 | 0.63 | 0.903 | 0.98; 0.02; 0.006 |
| dossier_live:sonnet | T2+S1 | 0.6 | 0 | (b) | 0.00 | 0.74 | 0.16 | 0.00 | 0.42 | 0.45 | 0.10 | 0.326 | 0.70 | 0.47 | 0.895 | 0.92; 0.08; 0.008 |
| dossier_live:sonnet | T2+S1 | 0.6 | 5 | (b) | 0.00 | 0.78 | 0.11 | 0.00 | 0.45 | 0.44 | 0.08 | 0.325 | 0.74 | 0.52 | 0.896 | 0.90; 0.10; 0.009 |
| dossier_live:sonnet | T2+S1 | 0.6 | 10 | (b) | 0.00 | 0.73 | 0.17 | 0.00 | 0.46 | 0.42 | 0.09 | 0.326 | 0.69 | 0.54 | 0.895 | 0.96; 0.04; 0.008 |
| dossier_live:sonnet | T1+S2 | 0.3 | 0 | (b) | 0.00 | 0.66 | 0.23 | 0.00 | 0.55 | 0.36 | 0.07 | 0.373 | 0.61 | 0.61 | 0.898 | 0.05; 0.95; 0.001 |
| dossier_live:sonnet | T1+S2 | 0.3 | 5 | (b) | 0.00 | 0.64 | 0.27 | 0.00 | 0.55 | 0.32 | 0.11 | 0.373 | 0.62 | 0.60 | 0.896 | 0.05; 0.95; 0.001 |
| dossier_live:sonnet | T1+S2 | 0.3 | 10 | (b) | 0.00 | 0.67 | 0.25 | 0.00 | 0.48 | 0.42 | 0.09 | 0.373 | 0.61 | 0.53 | 0.896 | 0.06; 0.94; 0.001 |
| dossier_live:sonnet | T1+S2 | 0.6 | 0 | (b) | 0.00 | 0.62 | 0.31 | 0.00 | 0.44 | 0.30 | 0.22 | 0.428 | 0.57 | 0.50 | 0.895 | 0.03; 0.97; 0.001 |
| dossier_live:sonnet | T1+S2 | 0.6 | 5 | (b) | 0.00 | 0.61 | 0.28 | 0.00 | 0.44 | 0.34 | 0.21 | 0.427 | 0.58 | 0.53 | 0.892 | 0.03; 0.97; 0.001 |
| dossier_live:sonnet | T1+S2 | 0.6 | 10 | (b) | 0.00 | 0.59 | 0.32 | 0.00 | 0.43 | 0.32 | 0.23 | 0.418 | 0.55 | 0.51 | 0.898 | 0.04; 0.96; 0.001 |
| dossier_live:sonnet | T2+S2 | 0.3 | 0 | (b) | 0.00 | 0.89 | 0.03 | 0.00 | 0.51 | 0.48 | 0.00 | 0.286 | 0.87 | 0.61 | 0.888 | 0.98; 0.02; 0.005 |
| dossier_live:sonnet | T2+S2 | 0.3 | 5 | (b) | 0.00 | 0.88 | 0.02 | 0.00 | 0.51 | 0.47 | 0.01 | 0.286 | 0.86 | 0.58 | 0.893 | 0.96; 0.04; 0.005 |
| dossier_live:sonnet | T2+S2 | 0.3 | 10 | (b) | 0.00 | 0.83 | 0.05 | 0.00 | 0.49 | 0.50 | 0.00 | 0.285 | 0.81 | 0.59 | 0.895 | 0.97; 0.03; 0.005 |
| dossier_live:sonnet | T2+S2 | 0.6 | 0 | (b) | 0.00 | 0.81 | 0.12 | 0.00 | 0.37 | 0.50 | 0.09 | 0.333 | 0.77 | 0.43 | 0.896 | 0.88; 0.12; 0.008 |
| dossier_live:sonnet | T2+S2 | 0.6 | 5 | (b) | 0.00 | 0.79 | 0.16 | 0.00 | 0.45 | 0.44 | 0.08 | 0.334 | 0.76 | 0.51 | 0.897 | 0.89; 0.11; 0.008 |
| dossier_live:sonnet | T2+S2 | 0.6 | 10 | (b) | 0.00 | 0.81 | 0.11 | 0.00 | 0.46 | 0.41 | 0.11 | 0.325 | 0.78 | 0.51 | 0.894 | 0.93; 0.07; 0.008 |
| P_author:opus48 | T1 | 0.3 | 0 | (b) | 0.00 | 0.72 | 0.25 | 0.00 | 0.33 | 0.27 | 0.34 | 0.421 | 0.64 | 0.38 | 0.833 | 0.02; 0.98; 0.000 |
| P_author:opus48 | T1 | 0.3 | 5 | (b) | 0.00 | 0.72 | 0.24 | 0.00 | 0.29 | 0.29 | 0.38 | 0.416 | 0.68 | 0.38 | 0.832 | 0.03; 0.97; 0.001 |
| P_author:opus48 | T1 | 0.3 | 10 | (b) | 0.00 | 0.73 | 0.23 | 0.00 | 0.30 | 0.28 | 0.36 | 0.417 | 0.66 | 0.36 | 0.827 | 0.05; 0.95; 0.001 |
| P_author:opus48 | T1 | 0.6 | 0 | (b) | 0.00 | 0.68 | 0.27 | 0.00 | 0.17 | 0.26 | 0.43 | 0.425 | 0.62 | 0.23 | 0.837 | 0.03; 0.96; 0.001 |
| P_author:opus48 | T1 | 0.6 | 5 | (b) | 0.00 | 0.66 | 0.29 | 0.00 | 0.19 | 0.22 | 0.49 | 0.427 | 0.63 | 0.24 | 0.832 | 0.04; 0.96; 0.001 |
| P_author:opus48 | T1 | 0.6 | 10 | (b) | 0.00 | 0.66 | 0.31 | 0.00 | 0.21 | 0.22 | 0.47 | 0.423 | 0.61 | 0.25 | 0.836 | 0.04; 0.96; 0.001 |
| P_author:opus48 | T2 | 0.3 | 0 | (b) | 0.00 | 0.90 | 0.07 | 0.00 | 0.25 | 0.46 | 0.20 | 0.335 | 0.88 | 0.34 | 0.833 | 0.92; 0.08; 0.006 |
| P_author:opus48 | T2 | 0.3 | 5 | (b) | 0.00 | 0.91 | 0.08 | 0.00 | 0.22 | 0.49 | 0.19 | 0.330 | 0.87 | 0.30 | 0.832 | 0.94; 0.06; 0.006 |
| P_author:opus48 | T2 | 0.3 | 10 | (b) | 0.00 | 0.89 | 0.08 | 0.00 | 0.23 | 0.54 | 0.16 | 0.329 | 0.85 | 0.33 | 0.829 | 0.95; 0.05; 0.006 |
| P_author:opus48 | T2 | 0.6 | 0 | (b) | 0.00 | 0.83 | 0.13 | 0.00 | 0.12 | 0.41 | 0.33 | 0.358 | 0.78 | 0.18 | 0.835 | 0.81; 0.19; 0.008 |
| P_author:opus48 | T2 | 0.6 | 5 | (b) | 0.00 | 0.84 | 0.14 | 0.00 | 0.18 | 0.31 | 0.35 | 0.359 | 0.80 | 0.20 | 0.829 | 0.86; 0.14; 0.009 |
| P_author:opus48 | T2 | 0.6 | 10 | (b) | 0.00 | 0.86 | 0.11 | 0.00 | 0.18 | 0.38 | 0.28 | 0.351 | 0.83 | 0.24 | 0.828 | 0.88; 0.12; 0.009 |
| P_author:opus48 | T1+S1 | 0.3 | 0 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.11 | 0.89 | 0.00 | 21.793 | 0.98 | 0.11 | 0.899 | — |
| P_author:opus48 | T1+S1 | 0.3 | 0 | (b) | 0.00 | 0.72 | 0.17 | 0.00 | 0.50 | 0.43 | 0.06 | 0.357 | 0.63 | 0.61 | 0.899 | 0.03; 0.96; 0.001 |
| P_author:opus48 | T1+S1 | 0.3 | 5 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.06 | 0.94 | 0.00 | 21.963 | 0.97 | 0.06 | 0.900 | — |
| P_author:opus48 | T1+S1 | 0.3 | 5 | (b) | 0.00 | 0.74 | 0.16 | 0.00 | 0.45 | 0.48 | 0.05 | 0.354 | 0.67 | 0.56 | 0.900 | 0.02; 0.97; 0.001 |
| P_author:opus48 | T1+S1 | 0.3 | 10 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.09 | 0.91 | 0.00 | 22.303 | 0.97 | 0.09 | 0.895 | — |
| P_author:opus48 | T1+S1 | 0.3 | 10 | (b) | 0.00 | 0.71 | 0.18 | 0.00 | 0.52 | 0.41 | 0.06 | 0.355 | 0.67 | 0.62 | 0.895 | 0.03; 0.97; 0.001 |
| P_author:opus48 | T1+S1 | 0.6 | 0 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.11 | 0.89 | 0.00 | 17.767 | 0.97 | 0.11 | 0.888 | — |
| P_author:opus48 | T1+S1 | 0.6 | 0 | (b) | 0.00 | 0.62 | 0.23 | 0.00 | 0.38 | 0.38 | 0.21 | 0.386 | 0.56 | 0.44 | 0.888 | 0.01; 0.99; 0.000 |
| P_author:opus48 | T1+S1 | 0.6 | 5 | (a) | 0.00 | 0.98 | 0.00 | 0.01 | 0.09 | 0.91 | 0.00 | 17.806 | 0.98 | 0.09 | 0.893 | — |
| P_author:opus48 | T1+S1 | 0.6 | 5 | (b) | 0.00 | 0.67 | 0.25 | 0.00 | 0.37 | 0.41 | 0.17 | 0.391 | 0.60 | 0.47 | 0.893 | 0.03; 0.97; 0.001 |
| P_author:opus48 | T1+S1 | 0.6 | 10 | (a) | 0.00 | 0.95 | 0.00 | 0.00 | 0.08 | 0.92 | 0.00 | 18.429 | 0.95 | 0.08 | 0.899 | — |
| P_author:opus48 | T1+S1 | 0.6 | 10 | (b) | 0.00 | 0.65 | 0.26 | 0.00 | 0.41 | 0.44 | 0.12 | 0.381 | 0.60 | 0.55 | 0.899 | 0.03; 0.96; 0.001 |
| P_author:opus48 | T2+S1 | 0.3 | 0 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.11 | 0.89 | 0.00 | 18.301 | 0.97 | 0.11 | 0.894 | — |
| P_author:opus48 | T2+S1 | 0.3 | 0 | (b) | 0.00 | 0.85 | 0.03 | 0.00 | 0.57 | 0.41 | 0.01 | 0.282 | 0.84 | 0.68 | 0.894 | 0.95; 0.05; 0.006 |
| P_author:opus48 | T2+S1 | 0.3 | 5 | (a) | 0.00 | 0.96 | 0.00 | 0.00 | 0.11 | 0.89 | 0.00 | 18.258 | 0.96 | 0.11 | 0.894 | — |
| P_author:opus48 | T2+S1 | 0.3 | 5 | (b) | 0.00 | 0.82 | 0.02 | 0.00 | 0.53 | 0.46 | 0.01 | 0.276 | 0.80 | 0.62 | 0.894 | 0.93; 0.07; 0.007 |
| P_author:opus48 | T2+S1 | 0.3 | 10 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.11 | 0.89 | 0.00 | 18.270 | 0.98 | 0.11 | 0.896 | — |
| P_author:opus48 | T2+S1 | 0.3 | 10 | (b) | 0.00 | 0.85 | 0.04 | 0.00 | 0.50 | 0.49 | 0.01 | 0.275 | 0.82 | 0.61 | 0.896 | 0.92; 0.08; 0.006 |
| P_author:opus48 | T2+S1 | 0.6 | 0 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.07 | 0.93 | 0.00 | 14.557 | 0.98 | 0.07 | 0.900 | — |
| P_author:opus48 | T2+S1 | 0.6 | 0 | (b) | 0.00 | 0.79 | 0.10 | 0.00 | 0.36 | 0.57 | 0.04 | 0.312 | 0.75 | 0.47 | 0.900 | 0.82; 0.18; 0.008 |
| P_author:opus48 | T2+S1 | 0.6 | 5 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.10 | 0.90 | 0.00 | 14.896 | 0.97 | 0.10 | 0.891 | — |
| P_author:opus48 | T2+S1 | 0.6 | 5 | (b) | 0.00 | 0.79 | 0.10 | 0.00 | 0.37 | 0.56 | 0.06 | 0.304 | 0.73 | 0.49 | 0.891 | 0.83; 0.17; 0.008 |
| P_author:opus48 | T2+S1 | 0.6 | 10 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.08 | 0.92 | 0.00 | 15.301 | 0.97 | 0.08 | 0.892 | — |
| P_author:opus48 | T2+S1 | 0.6 | 10 | (b) | 0.00 | 0.81 | 0.07 | 0.00 | 0.36 | 0.55 | 0.06 | 0.304 | 0.73 | 0.45 | 0.892 | 0.88; 0.12; 0.008 |
| P_author:opus48 | T1+S2 | 0.3 | 0 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.08 | 0.92 | 0.00 | 20.279 | 0.98 | 0.08 | 0.898 | — |
| P_author:opus48 | T1+S2 | 0.3 | 0 | (b) | 0.00 | 0.75 | 0.18 | 0.00 | 0.49 | 0.41 | 0.07 | 0.364 | 0.67 | 0.58 | 0.898 | 0.03; 0.96; 0.001 |
| P_author:opus48 | T1+S2 | 0.3 | 5 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.10 | 0.90 | 0.00 | 20.242 | 0.97 | 0.10 | 0.896 | — |
| P_author:opus48 | T1+S2 | 0.3 | 5 | (b) | 0.00 | 0.73 | 0.17 | 0.00 | 0.47 | 0.41 | 0.09 | 0.369 | 0.65 | 0.56 | 0.896 | 0.03; 0.97; 0.001 |
| P_author:opus48 | T1+S2 | 0.3 | 10 | (a) | 0.00 | 0.98 | 0.00 | 0.00 | 0.12 | 0.88 | 0.00 | 20.551 | 0.98 | 0.12 | 0.904 | — |
| P_author:opus48 | T1+S2 | 0.3 | 10 | (b) | 0.00 | 0.75 | 0.17 | 0.00 | 0.46 | 0.43 | 0.09 | 0.357 | 0.68 | 0.57 | 0.904 | 0.01; 0.98; 0.000 |
| P_author:opus48 | T1+S2 | 0.6 | 0 | (a) | 0.00 | 0.99 | 0.00 | 0.02 | 0.07 | 0.91 | 0.00 | 16.018 | 0.99 | 0.07 | 0.892 | — |
| P_author:opus48 | T1+S2 | 0.6 | 0 | (b) | 0.00 | 0.71 | 0.25 | 0.00 | 0.38 | 0.37 | 0.19 | 0.412 | 0.61 | 0.48 | 0.892 | 0.02; 0.98; 0.001 |
| P_author:opus48 | T1+S2 | 0.6 | 5 | (a) | 0.00 | 0.97 | 0.00 | 0.02 | 0.11 | 0.87 | 0.00 | 16.188 | 0.97 | 0.11 | 0.892 | — |
| P_author:opus48 | T1+S2 | 0.6 | 5 | (b) | 0.00 | 0.70 | 0.25 | 0.00 | 0.38 | 0.39 | 0.20 | 0.409 | 0.61 | 0.48 | 0.892 | 0.02; 0.98; 0.001 |
| P_author:opus48 | T1+S2 | 0.6 | 10 | (a) | 0.00 | 0.96 | 0.00 | 0.00 | 0.13 | 0.87 | 0.00 | 17.002 | 0.96 | 0.13 | 0.897 | — |
| P_author:opus48 | T1+S2 | 0.6 | 10 | (b) | 0.00 | 0.67 | 0.27 | 0.00 | 0.43 | 0.37 | 0.15 | 0.399 | 0.61 | 0.55 | 0.897 | 0.02; 0.97; 0.001 |
| P_author:opus48 | T2+S2 | 0.3 | 0 | (a) | 0.00 | 0.96 | 0.00 | 0.00 | 0.10 | 0.90 | 0.00 | 15.986 | 0.96 | 0.10 | 0.890 | — |
| P_author:opus48 | T2+S2 | 0.3 | 0 | (b) | 0.00 | 0.90 | 0.01 | 0.00 | 0.43 | 0.54 | 0.02 | 0.282 | 0.86 | 0.53 | 0.890 | 0.93; 0.07; 0.006 |
| P_author:opus48 | T2+S2 | 0.3 | 5 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.12 | 0.88 | 0.00 | 16.036 | 0.97 | 0.12 | 0.896 | — |
| P_author:opus48 | T2+S2 | 0.3 | 5 | (b) | 0.00 | 0.85 | 0.04 | 0.00 | 0.45 | 0.53 | 0.01 | 0.281 | 0.83 | 0.60 | 0.896 | 0.95; 0.05; 0.007 |
| P_author:opus48 | T2+S2 | 0.3 | 10 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.10 | 0.90 | 0.00 | 16.030 | 0.97 | 0.10 | 0.899 | — |
| P_author:opus48 | T2+S2 | 0.3 | 10 | (b) | 0.00 | 0.83 | 0.05 | 0.00 | 0.45 | 0.53 | 0.02 | 0.275 | 0.81 | 0.56 | 0.899 | 0.94; 0.06; 0.006 |
| P_author:opus48 | T2+S2 | 0.6 | 0 | (a) | 0.00 | 0.96 | 0.00 | 0.01 | 0.09 | 0.90 | 0.00 | 12.714 | 0.96 | 0.09 | 0.892 | — |
| P_author:opus48 | T2+S2 | 0.6 | 0 | (b) | 0.00 | 0.84 | 0.08 | 0.00 | 0.34 | 0.58 | 0.05 | 0.319 | 0.79 | 0.46 | 0.892 | 0.81; 0.19; 0.008 |
| P_author:opus48 | T2+S2 | 0.6 | 5 | (a) | 0.00 | 0.97 | 0.00 | 0.01 | 0.06 | 0.93 | 0.00 | 13.010 | 0.97 | 0.06 | 0.894 | — |
| P_author:opus48 | T2+S2 | 0.6 | 5 | (b) | 0.00 | 0.86 | 0.06 | 0.00 | 0.37 | 0.51 | 0.07 | 0.317 | 0.82 | 0.45 | 0.894 | 0.86; 0.14; 0.009 |
| P_author:opus48 | T2+S2 | 0.6 | 10 | (a) | 0.00 | 0.97 | 0.00 | 0.00 | 0.11 | 0.89 | 0.00 | 13.346 | 0.97 | 0.11 | 0.890 | — |
| P_author:opus48 | T2+S2 | 0.6 | 10 | (b) | 0.00 | 0.87 | 0.08 | 0.00 | 0.40 | 0.51 | 0.05 | 0.309 | 0.83 | 0.51 | 0.890 | 0.89; 0.11; 0.009 |
| P_author:sonnet | T1 | 0.3 | 0 | (b) | 0.20 | 0.55 | 0.19 | 0.13 | 0.34 | 0.13 | 0.34 | 0.353 | 0.60 | 0.23 | 0.826 | 0.00; 0.82; 0.006 |
| P_author:sonnet | T1 | 0.3 | 5 | (b) | 0.21 | 0.51 | 0.22 | 0.13 | 0.34 | 0.18 | 0.31 | 0.354 | 0.58 | 0.26 | 0.830 | 0.00; 0.80; 0.005 |
| P_author:sonnet | T1 | 0.3 | 10 | (b) | 0.18 | 0.52 | 0.25 | 0.10 | 0.29 | 0.13 | 0.41 | 0.362 | 0.60 | 0.20 | 0.837 | 0.00; 0.82; 0.004 |
| P_author:sonnet | T1 | 0.6 | 0 | (b) | 0.23 | 0.43 | 0.27 | 0.11 | 0.22 | 0.13 | 0.46 | 0.356 | 0.54 | 0.17 | 0.833 | 0.00; 0.79; 0.005 |
| P_author:sonnet | T1 | 0.6 | 5 | (b) | 0.23 | 0.47 | 0.24 | 0.10 | 0.24 | 0.15 | 0.43 | 0.354 | 0.57 | 0.18 | 0.826 | 0.00; 0.79; 0.006 |
| P_author:sonnet | T1 | 0.6 | 10 | (b) | 0.18 | 0.50 | 0.27 | 0.11 | 0.29 | 0.12 | 0.40 | 0.356 | 0.59 | 0.20 | 0.828 | 0.00; 0.82; 0.004 |
| P_author:sonnet | T2 | 0.3 | 0 | (b) | 0.04 | 0.84 | 0.08 | 0.02 | 0.30 | 0.39 | 0.18 | 0.264 | 0.89 | 0.18 | 0.834 | 0.03; 0.96; 0.001 |
| P_author:sonnet | T2 | 0.3 | 5 | (b) | 0.03 | 0.87 | 0.06 | 0.01 | 0.31 | 0.37 | 0.23 | 0.264 | 0.90 | 0.20 | 0.835 | 0.06; 0.93; 0.001 |
| P_author:sonnet | T2 | 0.3 | 10 | (b) | 0.05 | 0.87 | 0.04 | 0.01 | 0.31 | 0.37 | 0.19 | 0.259 | 0.90 | 0.19 | 0.833 | 0.05; 0.95; 0.001 |
| P_author:sonnet | T2 | 0.6 | 0 | (b) | 0.05 | 0.77 | 0.13 | 0.02 | 0.24 | 0.30 | 0.31 | 0.285 | 0.85 | 0.17 | 0.832 | 0.01; 0.98; 0.000 |
| P_author:sonnet | T2 | 0.6 | 5 | (b) | 0.04 | 0.78 | 0.15 | 0.02 | 0.21 | 0.32 | 0.34 | 0.287 | 0.86 | 0.12 | 0.828 | 0.02; 0.95; 0.001 |
| P_author:sonnet | T2 | 0.6 | 10 | (b) | 0.05 | 0.83 | 0.09 | 0.02 | 0.24 | 0.37 | 0.28 | 0.276 | 0.89 | 0.16 | 0.831 | 0.02; 0.96; 0.000 |
| P_author:sonnet | T1+S1 | 0.3 | 0 | (a) | 0.00 | 0.53 | 0.45 | 0.00 | 0.37 | 0.10 | 0.51 | 24.359 | 0.53 | 0.37 | 0.900 | — |
| P_author:sonnet | T1+S1 | 0.3 | 0 | (b) | 0.20 | 0.45 | 0.20 | 0.12 | 0.50 | 0.28 | 0.08 | 0.341 | 0.52 | 0.35 | 0.900 | 0.00; 0.85; 0.004 |
| P_author:sonnet | T1+S1 | 0.3 | 5 | (a) | 0.00 | 0.52 | 0.45 | 0.00 | 0.42 | 0.07 | 0.50 | 24.537 | 0.52 | 0.42 | 0.892 | — |
| P_author:sonnet | T1+S1 | 0.3 | 5 | (b) | 0.21 | 0.50 | 0.17 | 0.12 | 0.50 | 0.25 | 0.09 | 0.339 | 0.59 | 0.39 | 0.892 | 0.00; 0.83; 0.006 |
| P_author:sonnet | T1+S1 | 0.3 | 10 | (a) | 0.00 | 0.51 | 0.46 | 0.00 | 0.40 | 0.06 | 0.49 | 24.615 | 0.51 | 0.40 | 0.899 | — |
| P_author:sonnet | T1+S1 | 0.3 | 10 | (b) | 0.18 | 0.49 | 0.21 | 0.11 | 0.48 | 0.29 | 0.08 | 0.329 | 0.59 | 0.36 | 0.899 | 0.00; 0.77; 0.005 |
| P_author:sonnet | T1+S1 | 0.6 | 0 | (a) | 0.00 | 0.73 | 0.23 | 0.00 | 0.42 | 0.27 | 0.28 | 19.536 | 0.73 | 0.42 | 0.892 | — |
| P_author:sonnet | T1+S1 | 0.6 | 0 | (b) | 0.20 | 0.50 | 0.20 | 0.11 | 0.45 | 0.26 | 0.13 | 0.333 | 0.61 | 0.31 | 0.892 | 0.00; 0.84; 0.008 |
| P_author:sonnet | T1+S1 | 0.6 | 5 | (a) | 0.00 | 0.66 | 0.31 | 0.00 | 0.40 | 0.26 | 0.29 | 19.733 | 0.66 | 0.40 | 0.898 | — |
| P_author:sonnet | T1+S1 | 0.6 | 5 | (b) | 0.20 | 0.45 | 0.20 | 0.12 | 0.39 | 0.25 | 0.15 | 0.339 | 0.56 | 0.26 | 0.898 | 0.00; 0.80; 0.011 |
| P_author:sonnet | T1+S1 | 0.6 | 10 | (a) | 0.00 | 0.62 | 0.35 | 0.00 | 0.47 | 0.18 | 0.32 | 19.983 | 0.62 | 0.47 | 0.894 | — |
| P_author:sonnet | T1+S1 | 0.6 | 10 | (b) | 0.20 | 0.48 | 0.15 | 0.11 | 0.38 | 0.29 | 0.15 | 0.341 | 0.56 | 0.29 | 0.894 | 0.00; 0.83; 0.008 |
| P_author:sonnet | T2+S1 | 0.3 | 0 | (a) | 0.00 | 0.66 | 0.31 | 0.00 | 0.45 | 0.21 | 0.29 | 20.053 | 0.66 | 0.45 | 0.901 | — |
| P_author:sonnet | T2+S1 | 0.3 | 0 | (b) | 0.06 | 0.78 | 0.04 | 0.00 | 0.52 | 0.46 | 0.02 | 0.243 | 0.80 | 0.38 | 0.901 | 0.04; 0.94; 0.001 |
| P_author:sonnet | T2+S1 | 0.3 | 5 | (a) | 0.00 | 0.70 | 0.29 | 0.00 | 0.42 | 0.26 | 0.27 | 20.121 | 0.70 | 0.42 | 0.902 | — |
| P_author:sonnet | T2+S1 | 0.3 | 5 | (b) | 0.07 | 0.80 | 0.02 | 0.02 | 0.55 | 0.41 | 0.01 | 0.242 | 0.82 | 0.35 | 0.902 | 0.05; 0.95; 0.001 |
| P_author:sonnet | T2+S1 | 0.3 | 10 | (a) | 0.00 | 0.67 | 0.31 | 0.00 | 0.40 | 0.22 | 0.34 | 20.173 | 0.67 | 0.40 | 0.899 | — |
| P_author:sonnet | T2+S1 | 0.3 | 10 | (b) | 0.04 | 0.79 | 0.01 | 0.00 | 0.51 | 0.46 | 0.01 | 0.241 | 0.80 | 0.34 | 0.899 | 0.04; 0.94; 0.001 |
| P_author:sonnet | T2+S1 | 0.6 | 0 | (a) | 0.00 | 0.84 | 0.14 | 0.00 | 0.45 | 0.41 | 0.11 | 16.411 | 0.84 | 0.45 | 0.899 | — |
| P_author:sonnet | T2+S1 | 0.6 | 0 | (b) | 0.04 | 0.81 | 0.04 | 0.01 | 0.43 | 0.50 | 0.03 | 0.254 | 0.84 | 0.25 | 0.899 | 0.03; 0.95; 0.001 |
| P_author:sonnet | T2+S1 | 0.6 | 5 | (a) | 0.00 | 0.85 | 0.11 | 0.00 | 0.42 | 0.43 | 0.13 | 16.459 | 0.85 | 0.42 | 0.892 | — |
| P_author:sonnet | T2+S1 | 0.6 | 5 | (b) | 0.06 | 0.75 | 0.05 | 0.02 | 0.42 | 0.49 | 0.04 | 0.250 | 0.79 | 0.22 | 0.892 | 0.01; 0.98; 0.000 |
| P_author:sonnet | T2+S1 | 0.6 | 10 | (a) | 0.00 | 0.81 | 0.16 | 0.00 | 0.47 | 0.38 | 0.12 | 16.857 | 0.81 | 0.47 | 0.890 | — |
| P_author:sonnet | T2+S1 | 0.6 | 10 | (b) | 0.07 | 0.75 | 0.03 | 0.00 | 0.43 | 0.50 | 0.04 | 0.254 | 0.78 | 0.23 | 0.890 | 0.01; 0.98; 0.000 |
| P_author:sonnet | T1+S2 | 0.3 | 0 | (a) | 0.00 | 0.59 | 0.37 | 0.00 | 0.43 | 0.13 | 0.39 | 22.474 | 0.59 | 0.43 | 0.896 | — |
| P_author:sonnet | T1+S2 | 0.3 | 0 | (b) | 0.25 | 0.46 | 0.17 | 0.13 | 0.46 | 0.27 | 0.09 | 0.338 | 0.53 | 0.36 | 0.896 | 0.00; 0.81; 0.004 |
| P_author:sonnet | T1+S2 | 0.3 | 5 | (a) | 0.00 | 0.56 | 0.42 | 0.00 | 0.37 | 0.18 | 0.42 | 22.345 | 0.56 | 0.37 | 0.894 | — |
| P_author:sonnet | T1+S2 | 0.3 | 5 | (b) | 0.24 | 0.49 | 0.15 | 0.10 | 0.49 | 0.30 | 0.09 | 0.329 | 0.56 | 0.37 | 0.894 | 0.00; 0.77; 0.005 |
| P_author:sonnet | T1+S2 | 0.3 | 10 | (a) | 0.00 | 0.55 | 0.43 | 0.00 | 0.46 | 0.12 | 0.40 | 22.714 | 0.55 | 0.46 | 0.898 | — |
| P_author:sonnet | T1+S2 | 0.3 | 10 | (b) | 0.25 | 0.49 | 0.15 | 0.10 | 0.46 | 0.29 | 0.12 | 0.332 | 0.57 | 0.34 | 0.898 | 0.00; 0.82; 0.004 |
| P_author:sonnet | T1+S2 | 0.6 | 0 | (a) | 0.00 | 0.73 | 0.24 | 0.00 | 0.46 | 0.35 | 0.15 | 17.640 | 0.73 | 0.46 | 0.888 | — |
| P_author:sonnet | T1+S2 | 0.6 | 0 | (b) | 0.21 | 0.45 | 0.21 | 0.11 | 0.36 | 0.23 | 0.18 | 0.329 | 0.57 | 0.22 | 0.888 | 0.00; 0.81; 0.010 |
| P_author:sonnet | T1+S2 | 0.6 | 5 | (a) | 0.00 | 0.74 | 0.22 | 0.00 | 0.43 | 0.32 | 0.20 | 17.930 | 0.74 | 0.43 | 0.892 | — |
| P_author:sonnet | T1+S2 | 0.6 | 5 | (b) | 0.21 | 0.47 | 0.19 | 0.09 | 0.38 | 0.23 | 0.15 | 0.328 | 0.56 | 0.23 | 0.892 | 0.00; 0.80; 0.013 |
| P_author:sonnet | T1+S2 | 0.6 | 10 | (a) | 0.00 | 0.75 | 0.23 | 0.00 | 0.40 | 0.31 | 0.23 | 18.644 | 0.75 | 0.40 | 0.892 | — |
| P_author:sonnet | T1+S2 | 0.6 | 10 | (b) | 0.20 | 0.51 | 0.19 | 0.16 | 0.30 | 0.25 | 0.21 | 0.334 | 0.59 | 0.22 | 0.892 | 0.00; 0.84; 0.007 |
| P_author:sonnet | T2+S2 | 0.3 | 0 | (a) | 0.00 | 0.77 | 0.20 | 0.00 | 0.43 | 0.35 | 0.20 | 17.576 | 0.77 | 0.43 | 0.901 | — |
| P_author:sonnet | T2+S2 | 0.3 | 0 | (b) | 0.03 | 0.84 | 0.03 | 0.01 | 0.47 | 0.50 | 0.00 | 0.241 | 0.86 | 0.32 | 0.901 | 0.07; 0.90; 0.001 |
| P_author:sonnet | T2+S2 | 0.3 | 5 | (a) | 0.00 | 0.78 | 0.19 | 0.00 | 0.45 | 0.33 | 0.18 | 17.731 | 0.78 | 0.45 | 0.895 | — |
| P_author:sonnet | T2+S2 | 0.3 | 5 | (b) | 0.06 | 0.82 | 0.02 | 0.03 | 0.51 | 0.45 | 0.01 | 0.238 | 0.83 | 0.31 | 0.895 | 0.03; 0.96; 0.001 |
| P_author:sonnet | T2+S2 | 0.3 | 10 | (a) | 0.00 | 0.77 | 0.21 | 0.00 | 0.45 | 0.35 | 0.17 | 17.718 | 0.77 | 0.45 | 0.901 | — |
| P_author:sonnet | T2+S2 | 0.3 | 10 | (b) | 0.06 | 0.81 | 0.03 | 0.01 | 0.51 | 0.44 | 0.02 | 0.242 | 0.83 | 0.33 | 0.901 | 0.04; 0.95; 0.001 |
| P_author:sonnet | T2+S2 | 0.6 | 0 | (a) | 0.00 | 0.92 | 0.05 | 0.00 | 0.42 | 0.50 | 0.05 | 14.128 | 0.92 | 0.42 | 0.896 | — |
| P_author:sonnet | T2+S2 | 0.6 | 0 | (b) | 0.06 | 0.85 | 0.03 | 0.01 | 0.38 | 0.57 | 0.03 | 0.231 | 0.87 | 0.19 | 0.896 | 0.01; 0.97; 0.000 |
| P_author:sonnet | T2+S2 | 0.6 | 5 | (a) | 0.00 | 0.90 | 0.04 | 0.00 | 0.39 | 0.50 | 0.07 | 14.204 | 0.90 | 0.39 | 0.897 | — |
| P_author:sonnet | T2+S2 | 0.6 | 5 | (b) | 0.05 | 0.82 | 0.05 | 0.02 | 0.36 | 0.54 | 0.04 | 0.237 | 0.86 | 0.20 | 0.897 | 0.01; 0.97; 0.000 |
| P_author:sonnet | T2+S2 | 0.6 | 10 | (a) | 0.00 | 0.90 | 0.07 | 0.00 | 0.41 | 0.47 | 0.05 | 14.667 | 0.90 | 0.41 | 0.893 | — |
| P_author:sonnet | T2+S2 | 0.6 | 10 | (b) | 0.05 | 0.83 | 0.02 | 0.01 | 0.40 | 0.55 | 0.02 | 0.238 | 0.85 | 0.19 | 0.893 | 0.01; 0.97; 0.000 |

## Beside the gate (not gate inputs)

- **Form (b)'s truth defined marginally** (the 0.3 contrast averaged over the design's lines rather than at the mean line): readable layouts ['T1+S1', 'T2+S1', 'T2+S2']; would adopt T2+S1.
- **Effect at 1.5 × the margin** (contrast 0.45 for (b); slope × 25 = 1.5 × m_s for (a)), reading still against the margin: readable layouts ['T1+S1', 'T2+S1', 'T1+S2', 'T2+S2']; would adopt T1+S2.
- **Effect at 2.0 × the margin** (contrast 0.60 for (b); slope × 25 = 2.0 × m_s for (a)), reading still against the margin: readable layouts ['T1', 'T2', 'T1+S1', 'T2+S1', 'T1+S2', 'T2+S2']; would adopt T2+S2.

P(present) at the reference noise, the worse ICC, by truth state (primary 0.3 / m_s; (b) marginal; 1.5 ×; 2 ×):

| view, judge | form | layout | P(excl \| 0) | primary | (b) marginal | 1.5 × | 2 × |
|---|---|---|---|---|---|---|---|
| dossier_iso:opus48 | (b) | T1 | 0.69 | 0.23 | 0.36 | 0.53 | 0.79 |
| dossier_iso:sonnet | (b) | T1 | 0.54 | 0.17 | 0.33 | 0.38 | 0.61 |
| dossier_live:opus48 | (b) | T1 | 0.19 | 0.13 | 0.08 | 0.23 | 0.32 |
| dossier_live:sonnet | (b) | T1 | 0.66 | 0.21 | 0.48 | 0.57 | 0.89 |
| P_author:opus48 | (b) | T1 | 0.66 | 0.19 | 0.41 | 0.57 | 0.86 |
| P_author:sonnet | (b) | T1 | 0.47 | 0.24 | 0.40 | 0.46 | 0.69 |
| dossier_iso:opus48 | (b) | T2 | 0.84 | 0.13 | 0.35 | 0.49 | 0.86 |
| dossier_iso:sonnet | (b) | T2 | 0.78 | 0.14 | 0.27 | 0.35 | 0.65 |
| dossier_live:opus48 | (b) | T2 | 0.78 | 0.20 | 0.10 | 0.57 | 0.78 |
| dossier_live:sonnet | (b) | T2 | 0.76 | 0.17 | 0.38 | 0.57 | 0.93 |
| P_author:opus48 | (b) | T2 | 0.84 | 0.18 | 0.32 | 0.57 | 0.95 |
| P_author:sonnet | (b) | T2 | 0.78 | 0.21 | 0.39 | 0.48 | 0.79 |
| dossier_iso:opus48 | (a) | T1+S1 | 0.97 | 0.22 | — | 1.00 | — |
| dossier_iso:opus48 | (b) | T1+S1 | 0.68 | 0.33 | 0.59 | 0.67 | 0.90 |
| dossier_iso:sonnet | (a) | T1+S1 | 0.44 | 0.37 | — | 0.75 | 0.93 |
| dossier_iso:sonnet | (b) | T1+S1 | 0.49 | 0.37 | 0.53 | 0.60 | 0.82 |
| dossier_live:opus48 | (a) | T1+S1 | 0.62 | 0.40 | — | 0.84 | 0.98 |
| dossier_live:opus48 | (b) | T1+S1 | 0.12 | 0.16 | 0.05 | 0.25 | 0.28 |
| dossier_live:sonnet | (b) | T1+S1 | 0.58 | 0.47 | 0.67 | 0.80 | 0.95 |
| P_author:opus48 | (a) | T1+S1 | 0.97 | 0.06 | — | — | — |
| P_author:opus48 | (b) | T1+S1 | 0.67 | 0.37 | 0.61 | 0.80 | 0.92 |
| P_author:sonnet | (a) | T1+S1 | 0.52 | 0.40 | — | 0.78 | 0.98 |
| P_author:sonnet | (b) | T1+S1 | 0.45 | 0.39 | 0.50 | 0.64 | 0.77 |
| dossier_iso:opus48 | (a) | T2+S1 | 0.95 | 0.24 | — | 1.00 | — |
| dossier_iso:opus48 | (b) | T2+S1 | 0.83 | 0.29 | 0.59 | 0.78 | 0.99 |
| dossier_iso:sonnet | (a) | T2+S1 | 0.54 | 0.39 | — | 0.79 | 0.96 |
| dossier_iso:sonnet | (b) | T2+S1 | 0.74 | 0.35 | 0.57 | 0.67 | 0.92 |
| dossier_live:opus48 | (a) | T2+S1 | 0.79 | 0.43 | — | 0.87 | 1.00 |
| dossier_live:opus48 | (b) | T2+S1 | 0.62 | 0.22 | 0.09 | 0.66 | 0.77 |
| dossier_live:sonnet | (b) | T2+S1 | 0.78 | 0.45 | 0.76 | 0.90 | 1.00 |
| P_author:opus48 | (a) | T2+S1 | 0.96 | 0.10 | — | — | — |
| P_author:opus48 | (b) | T2+S1 | 0.79 | 0.37 | 0.68 | 0.89 | 1.00 |
| P_author:sonnet | (a) | T2+S1 | 0.70 | 0.42 | — | 0.85 | 0.99 |
| P_author:sonnet | (b) | T2+S1 | 0.75 | 0.42 | 0.64 | 0.80 | 0.97 |
| dossier_iso:opus48 | (a) | T1+S2 | 0.98 | 0.20 | — | 1.00 | — |
| dossier_iso:opus48 | (b) | T1+S2 | 0.71 | 0.30 | 0.52 | 0.69 | 0.87 |
| dossier_iso:sonnet | (a) | T1+S2 | 0.53 | 0.35 | — | 0.78 | 0.96 |
| dossier_iso:sonnet | (b) | T1+S2 | 0.51 | 0.32 | 0.56 | 0.59 | 0.75 |
| dossier_live:opus48 | (a) | T1+S2 | 0.69 | 0.39 | — | 0.85 | 0.99 |
| dossier_live:opus48 | (b) | T1+S2 | 0.10 | 0.13 | 0.07 | 0.19 | 0.28 |
| dossier_live:sonnet | (b) | T1+S2 | 0.61 | 0.44 | 0.60 | 0.86 | 0.87 |
| P_author:opus48 | (a) | T1+S2 | 0.97 | 0.10 | — | — | — |
| P_author:opus48 | (b) | T1+S2 | 0.70 | 0.38 | 0.57 | 0.78 | 0.87 |
| P_author:sonnet | (a) | T1+S2 | 0.56 | 0.37 | — | 0.86 | 1.00 |
| P_author:sonnet | (b) | T1+S2 | 0.47 | 0.38 | 0.51 | 0.63 | 0.68 |
| dossier_iso:opus48 | (a) | T2+S2 | 0.98 | 0.15 | — | 1.00 | — |
| dossier_iso:opus48 | (b) | T2+S2 | 0.87 | 0.30 | 0.53 | 0.74 | 0.98 |
| dossier_iso:sonnet | (a) | T2+S2 | 0.66 | 0.42 | — | 0.81 | 0.99 |
| dossier_iso:sonnet | (b) | T2+S2 | 0.77 | 0.24 | 0.56 | 0.61 | 0.87 |
| dossier_live:opus48 | (a) | T2+S2 | 0.88 | 0.38 | — | 0.91 | 1.00 |
| dossier_live:opus48 | (b) | T2+S2 | 0.69 | 0.23 | 0.08 | 0.60 | 0.76 |
| dossier_live:sonnet | (b) | T2+S2 | 0.79 | 0.45 | 0.68 | 0.91 | 1.00 |
| P_author:opus48 | (a) | T2+S2 | 0.97 | 0.06 | — | — | — |
| P_author:opus48 | (b) | T2+S2 | 0.85 | 0.37 | 0.66 | 0.88 | 0.99 |
| P_author:sonnet | (a) | T2+S2 | 0.78 | 0.39 | — | 0.90 | 1.00 |
| P_author:sonnet | (b) | T2+S2 | 0.82 | 0.36 | 0.59 | 0.76 | 0.95 |

### Sensitivities (5-point noise, worse ICC; primary truth states)

| variant | view, judge | form | layout | P(floor \| 0) | P(excl \| 0) | P(present \| 0.3) | P(detect \| 0.3) | readable |
|---|---|---|---|---|---|---|---|---|
| regime_high=replant:v1 | dossier_iso:opus48 | (b) | T1 | 0.00 | 0.79 | 0.25 | 0.69 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (b) | T1 | 0.00 | 0.91 | 0.21 | 0.85 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (b) | T1 | 0.00 | 0.00 | 0.07 | 0.29 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (b) | T1 | 0.00 | 0.68 | 0.26 | 0.49 | no |
| regime_high=replant:v1 | P_author:opus48 | (b) | T1 | 0.00 | 0.60 | 0.31 | 0.58 | no |
| regime_high=replant:v1 | P_author:sonnet | (b) | T1 | 0.00 | 0.62 | 0.25 | 0.41 | no |
| regime_high=replant:v1 | dossier_iso:opus48 | (b) | T2 | 0.00 | 0.95 | 0.20 | 1.00 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (b) | T2 | 0.00 | 0.97 | 0.12 | 0.97 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (b) | T2 | 0.00 | 0.03 | 0.16 | 0.82 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (b) | T2 | 0.00 | 0.95 | 0.41 | 0.96 | no |
| regime_high=replant:v1 | P_author:opus48 | (b) | T2 | 0.00 | 0.95 | 0.32 | 0.95 | no |
| regime_high=replant:v1 | P_author:sonnet | (b) | T2 | 0.00 | 0.79 | 0.14 | 0.42 | no |
| regime_high=replant:v1 | dossier_iso:opus48 | (a) | T1+S1 | 0.00 | 0.97 | 0.20 | 1.00 | no |
| regime_high=replant:v1 | dossier_iso:opus48 | (b) | T1+S1 | 0.00 | 0.73 | 0.27 | 0.62 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (a) | T1+S1 | 0.00 | 0.68 | 0.46 | 0.72 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (b) | T1+S1 | 0.00 | 0.86 | 0.40 | 0.90 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (a) | T1+S1 | 0.00 | 0.76 | 0.42 | 0.74 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (b) | T1+S1 | 0.00 | 0.00 | 0.07 | 0.32 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (a) | T1+S1 | 0.00 | 0.92 | 0.14 | 1.00 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (b) | T1+S1 | 0.00 | 0.21 | 0.16 | 0.29 | no |
| regime_high=replant:v1 | P_author:opus48 | (a) | T1+S1 | 0.00 | 0.97 | 0.06 | 1.00 | no |
| regime_high=replant:v1 | P_author:opus48 | (b) | T1+S1 | 0.00 | 0.55 | 0.27 | 0.41 | no |
| regime_high=replant:v1 | P_author:sonnet | (a) | T1+S1 | 0.00 | 0.75 | 0.43 | 0.71 | no |
| regime_high=replant:v1 | P_author:sonnet | (b) | T1+S1 | 0.00 | 0.52 | 0.45 | 0.78 | no |
| regime_high=replant:v1 | dossier_iso:opus48 | (a) | T2+S1 | 0.00 | 0.96 | 0.20 | 1.00 | no |
| regime_high=replant:v1 | dossier_iso:opus48 | (b) | T2+S1 | 0.00 | 0.86 | 0.34 | 0.98 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (a) | T2+S1 | 0.00 | 0.83 | 0.42 | 0.85 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (b) | T2+S1 | 0.00 | 0.87 | 0.32 | 1.00 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (a) | T2+S1 | 0.00 | 0.89 | 0.40 | 0.88 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (b) | T2+S1 | 0.00 | 0.03 | 0.30 | 0.85 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (a) | T2+S1 | 0.00 | 0.92 | 0.14 | 1.00 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (b) | T2+S1 | 0.00 | 0.64 | 0.46 | 0.75 | no |
| regime_high=replant:v1 | P_author:opus48 | (a) | T2+S1 | 0.00 | 0.95 | 0.06 | 1.00 | no |
| regime_high=replant:v1 | P_author:opus48 | (b) | T2+S1 | 0.00 | 0.86 | 0.43 | 0.94 | no |
| regime_high=replant:v1 | P_author:sonnet | (a) | T2+S1 | 0.00 | 0.86 | 0.39 | 0.86 | no |
| regime_high=replant:v1 | P_author:sonnet | (b) | T2+S1 | 0.00 | 0.71 | 0.45 | 0.84 | no |
| regime_high=replant:v1 | dossier_iso:opus48 | (a) | T1+S2 | 0.00 | 0.96 | 0.23 | 1.00 | no |
| regime_high=replant:v1 | dossier_iso:opus48 | (b) | T1+S2 | 0.00 | 0.69 | 0.26 | 0.54 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (a) | T1+S2 | 0.00 | 0.74 | 0.42 | 0.67 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (b) | T1+S2 | 0.00 | 0.88 | 0.33 | 0.87 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (a) | T1+S2 | 0.00 | 0.86 | 0.39 | 0.77 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (b) | T1+S2 | 0.00 | 0.00 | 0.08 | 0.27 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (a) | T1+S2 | 0.00 | 0.97 | 0.11 | 0.97 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (b) | T1+S2 | 0.00 | 0.52 | 0.28 | 0.38 | no |
| regime_high=replant:v1 | P_author:opus48 | (a) | T1+S2 | 0.00 | 0.95 | 0.08 | 1.00 | no |
| regime_high=replant:v1 | P_author:opus48 | (b) | T1+S2 | 0.00 | 0.49 | 0.22 | 0.35 | no |
| regime_high=replant:v1 | P_author:sonnet | (a) | T1+S2 | 0.00 | 0.76 | 0.40 | 0.74 | no |
| regime_high=replant:v1 | P_author:sonnet | (b) | T1+S2 | 0.00 | 0.53 | 0.43 | 0.69 | no |
| regime_high=replant:v1 | dossier_iso:opus48 | (a) | T2+S2 | 0.00 | 0.99 | 0.23 | 1.00 | no |
| regime_high=replant:v1 | dossier_iso:opus48 | (b) | T2+S2 | 0.00 | 0.91 | 0.31 | 0.97 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (a) | T2+S2 | 0.00 | 0.90 | 0.34 | 0.89 | no |
| regime_high=replant:v1 | dossier_iso:sonnet | (b) | T2+S2 | 0.00 | 0.90 | 0.26 | 1.00 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (a) | T2+S2 | 0.00 | 0.94 | 0.35 | 0.97 | no |
| regime_high=replant:v1 | dossier_live:opus48 | (b) | T2+S2 | 0.00 | 0.01 | 0.26 | 0.84 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (a) | T2+S2 | 0.00 | 0.94 | 0.12 | 0.99 | no |
| regime_high=replant:v1 | dossier_live:sonnet | (b) | T2+S2 | 0.00 | 0.88 | 0.52 | 0.86 | no |
| regime_high=replant:v1 | P_author:opus48 | (a) | T2+S2 | 0.00 | 0.96 | 0.05 | 1.00 | no |
| regime_high=replant:v1 | P_author:opus48 | (b) | T2+S2 | 0.00 | 0.89 | 0.40 | 0.93 | no |
| regime_high=replant:v1 | P_author:sonnet | (a) | T2+S2 | 0.00 | 0.95 | 0.33 | 0.90 | no |
| regime_high=replant:v1 | P_author:sonnet | (b) | T2+S2 | 0.00 | 0.78 | 0.49 | 0.83 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (b) | T1 | 0.22 | 0.47 | 0.18 | 0.29 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (b) | T1 | 0.00 | 0.84 | 0.16 | 0.79 | no |
| regime_low=v2:conforming | dossier_live:sonnet | (b) | T1 | 0.05 | 0.55 | 0.28 | 0.36 | no |
| regime_low=v2:conforming | P_author:opus48 | (b) | T1 | 0.05 | 0.61 | 0.21 | 0.30 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (b) | T2 | 0.01 | 0.77 | 0.11 | 0.32 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (b) | T2 | 0.00 | 0.95 | 0.15 | 0.99 | no |
| regime_low=v2:conforming | dossier_live:sonnet | (b) | T2 | 0.00 | 0.77 | 0.19 | 0.41 | no |
| regime_low=v2:conforming | P_author:opus48 | (b) | T2 | 0.00 | 0.74 | 0.17 | 0.35 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (a) | T1+S1 | 0.00 | 0.96 | 0.21 | 1.00 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (b) | T1+S1 | 0.20 | 0.40 | 0.30 | 0.55 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (a) | T1+S1 | 0.00 | 0.57 | 0.40 | 0.49 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (b) | T1+S1 | 0.00 | 0.82 | 0.21 | 0.73 | no |
| regime_low=v2:conforming | dossier_live:sonnet | (b) | T1+S1 | 0.04 | 0.49 | 0.51 | 0.76 | no |
| regime_low=v2:conforming | P_author:opus48 | (a) | T1+S1 | 0.00 | 0.97 | 0.08 | 0.94 | no |
| regime_low=v2:conforming | P_author:opus48 | (b) | T1+S1 | 0.07 | 0.49 | 0.48 | 0.71 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (a) | T2+S1 | 0.00 | 0.96 | 0.21 | 1.00 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (b) | T2+S1 | 0.05 | 0.74 | 0.33 | 0.71 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (a) | T2+S1 | 0.00 | 0.71 | 0.38 | 0.64 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (b) | T2+S1 | 0.00 | 0.87 | 0.21 | 1.00 | no |
| regime_low=v2:conforming | dossier_live:sonnet | (b) | T2+S1 | 0.00 | 0.74 | 0.42 | 0.85 | no |
| regime_low=v2:conforming | P_author:opus48 | (a) | T2+S1 | 0.00 | 0.96 | 0.09 | 0.98 | no |
| regime_low=v2:conforming | P_author:opus48 | (b) | T2+S1 | 0.00 | 0.69 | 0.38 | 0.81 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (a) | T1+S2 | 0.00 | 0.97 | 0.23 | 1.00 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (b) | T1+S2 | 0.19 | 0.50 | 0.30 | 0.53 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (a) | T1+S2 | 0.00 | 0.62 | 0.43 | 0.53 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (b) | T1+S2 | 0.00 | 0.72 | 0.19 | 0.66 | no |
| regime_low=v2:conforming | dossier_live:sonnet | (b) | T1+S2 | 0.04 | 0.48 | 0.48 | 0.67 | no |
| regime_low=v2:conforming | P_author:opus48 | (a) | T1+S2 | 0.00 | 0.94 | 0.11 | 0.93 | no |
| regime_low=v2:conforming | P_author:opus48 | (b) | T1+S2 | 0.04 | 0.51 | 0.43 | 0.59 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (a) | T2+S2 | 0.00 | 0.95 | 0.20 | 1.00 | no |
| regime_low=v2:conforming | dossier_iso:opus48 | (b) | T2+S2 | 0.02 | 0.76 | 0.27 | 0.68 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (a) | T2+S2 | 0.00 | 0.82 | 0.41 | 0.75 | no |
| regime_low=v2:conforming | dossier_live:opus48 | (b) | T2+S2 | 0.00 | 0.91 | 0.22 | 1.00 | no |
| regime_low=v2:conforming | dossier_live:sonnet | (b) | T2+S2 | 0.00 | 0.77 | 0.40 | 0.83 | no |
| regime_low=v2:conforming | P_author:opus48 | (a) | T2+S2 | 0.00 | 0.97 | 0.10 | 0.97 | no |
| regime_low=v2:conforming | P_author:opus48 | (b) | T2+S2 | 0.00 | 0.79 | 0.37 | 0.77 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (b) | T1 | 0.52 | 0.30 | 0.16 | 0.22 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (b) | T2 | 0.24 | 0.61 | 0.14 | 0.35 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (a) | T1+S1 | 0.00 | 0.61 | 0.38 | 0.64 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (b) | T1+S1 | 0.50 | 0.29 | 0.24 | 0.42 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (a) | T2+S1 | 0.00 | 0.73 | 0.42 | 0.72 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (b) | T2+S1 | 0.24 | 0.58 | 0.28 | 0.70 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (a) | T1+S2 | 0.00 | 0.66 | 0.41 | 0.62 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (b) | T1+S2 | 0.51 | 0.31 | 0.22 | 0.39 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (a) | T2+S2 | 0.00 | 0.88 | 0.38 | 0.84 | no |
| regime_low=v3:middle | dossier_iso:sonnet | (b) | T2+S2 | 0.24 | 0.67 | 0.24 | 0.62 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (b) | T1 | 0.61 | 0.01 | 0.07 | 0.12 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (b) | T2 | 0.69 | 0.07 | 0.19 | 0.52 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (a) | T1+S1 | 1.00 | 0.00 | 0.00 | 0.00 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (b) | T1+S1 | 0.59 | 0.00 | 0.02 | 0.03 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (a) | T2+S1 | 1.00 | 0.00 | 0.00 | 0.00 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (b) | T2+S1 | 0.66 | 0.01 | 0.08 | 0.16 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (a) | T1+S2 | 1.00 | 0.00 | 0.00 | 0.00 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (b) | T1+S2 | 0.61 | 0.00 | 0.00 | 0.01 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (a) | T2+S2 | 1.00 | 0.00 | 0.00 | 0.00 | no |
| regime_low=v3:routine_redraw | P_author:sonnet | (b) | T2+S2 | 0.69 | 0.00 | 0.03 | 0.05 | no |
| rho=0.3 | dossier_iso:opus48 | (b) | T1 | 0.02 | 0.74 | 0.16 | 0.42 | no |
| rho=0.3 | dossier_iso:sonnet | (b) | T1 | 0.11 | 0.52 | 0.17 | 0.30 | no |
| rho=0.3 | dossier_live:opus48 | (b) | T1 | 0.00 | 0.20 | 0.16 | 0.53 | no |
| rho=0.3 | dossier_live:sonnet | (b) | T1 | 0.00 | 0.69 | 0.16 | 0.38 | no |
| rho=0.3 | P_author:opus48 | (b) | T1 | 0.00 | 0.72 | 0.16 | 0.39 | no |
| rho=0.3 | P_author:sonnet | (b) | T1 | 0.23 | 0.47 | 0.20 | 0.33 | no |
| rho=0.3 | dossier_iso:opus48 | (b) | T2 | 0.00 | 0.88 | 0.12 | 0.48 | no |
| rho=0.3 | dossier_iso:sonnet | (b) | T2 | 0.01 | 0.79 | 0.09 | 0.29 | no |
| rho=0.3 | dossier_live:opus48 | (b) | T2 | 0.00 | 0.73 | 0.23 | 0.95 | no |
| rho=0.3 | dossier_live:sonnet | (b) | T2 | 0.00 | 0.82 | 0.16 | 0.45 | no |
| rho=0.3 | P_author:opus48 | (b) | T2 | 0.00 | 0.85 | 0.14 | 0.52 | no |
| rho=0.3 | P_author:sonnet | (b) | T2 | 0.07 | 0.79 | 0.18 | 0.54 | no |
| rho=0.3 | dossier_iso:opus48 | (a) | T1+S1 | 0.00 | 0.96 | 0.22 | 1.00 | no |
| rho=0.3 | dossier_iso:opus48 | (b) | T1+S1 | 0.01 | 0.75 | 0.27 | 0.72 | no |
| rho=0.3 | dossier_iso:sonnet | (a) | T1+S1 | 0.00 | 0.46 | 0.35 | 0.37 | no |
| rho=0.3 | dossier_iso:sonnet | (b) | T1+S1 | 0.14 | 0.59 | 0.32 | 0.66 | no |
| rho=0.3 | dossier_live:opus48 | (a) | T1+S1 | 0.00 | 0.62 | 0.40 | 0.59 | no |
| rho=0.3 | dossier_live:opus48 | (b) | T1+S1 | 0.00 | 0.15 | 0.14 | 0.42 | no |
| rho=0.3 | dossier_live:sonnet | (a) | T1+S1 | 0.00 | 0.98 | 0.11 | 0.99 | no |
| rho=0.3 | dossier_live:sonnet | (b) | T1+S1 | 0.00 | 0.69 | 0.40 | 0.79 | no |
| rho=0.3 | P_author:opus48 | (a) | T1+S1 | 0.00 | 0.96 | 0.13 | 1.00 | no |
| rho=0.3 | P_author:opus48 | (b) | T1+S1 | 0.00 | 0.73 | 0.33 | 0.81 | no |
| rho=0.3 | P_author:sonnet | (a) | T1+S1 | 0.00 | 0.48 | 0.43 | 0.49 | no |
| rho=0.3 | P_author:sonnet | (b) | T1+S1 | 0.25 | 0.48 | 0.31 | 0.60 | no |
| rho=0.3 | dossier_iso:opus48 | (a) | T2+S1 | 0.00 | 0.96 | 0.21 | 1.00 | no |
| rho=0.3 | dossier_iso:opus48 | (b) | T2+S1 | 0.00 | 0.93 | 0.21 | 0.91 | no |
| rho=0.3 | dossier_iso:sonnet | (a) | T2+S1 | 0.00 | 0.56 | 0.43 | 0.53 | no |
| rho=0.3 | dossier_iso:sonnet | (b) | T2+S1 | 0.02 | 0.84 | 0.24 | 0.69 | no |
| rho=0.3 | dossier_live:opus48 | (a) | T2+S1 | 0.00 | 0.84 | 0.36 | 0.71 | no |
| rho=0.3 | dossier_live:opus48 | (b) | T2+S1 | 0.00 | 0.67 | 0.26 | 0.92 | no |
| rho=0.3 | dossier_live:sonnet | (a) | T2+S1 | 0.00 | 0.97 | 0.09 | 1.00 | no |
| rho=0.3 | dossier_live:sonnet | (b) | T2+S1 | 0.00 | 0.85 | 0.34 | 0.89 | no |
| rho=0.3 | P_author:opus48 | (a) | T2+S1 | 0.00 | 0.96 | 0.08 | 1.00 | no |
| rho=0.3 | P_author:opus48 | (b) | T2+S1 | 0.00 | 0.87 | 0.31 | 0.93 | no |
| rho=0.3 | P_author:sonnet | (a) | T2+S1 | 0.00 | 0.71 | 0.41 | 0.63 | no |
| rho=0.3 | P_author:sonnet | (b) | T2+S1 | 0.07 | 0.84 | 0.35 | 0.90 | no |
| rho=0.3 | dossier_iso:opus48 | (a) | T1+S2 | 0.00 | 0.97 | 0.21 | 1.00 | no |
| rho=0.3 | dossier_iso:opus48 | (b) | T1+S2 | 0.01 | 0.73 | 0.27 | 0.79 | no |
| rho=0.3 | dossier_iso:sonnet | (a) | T1+S2 | 0.00 | 0.44 | 0.41 | 0.45 | no |
| rho=0.3 | dossier_iso:sonnet | (b) | T1+S2 | 0.10 | 0.58 | 0.26 | 0.52 | no |
| rho=0.3 | dossier_live:opus48 | (a) | T1+S2 | 0.00 | 0.72 | 0.37 | 0.61 | no |
| rho=0.3 | dossier_live:opus48 | (b) | T1+S2 | 0.00 | 0.08 | 0.12 | 0.39 | no |
| rho=0.3 | dossier_live:sonnet | (a) | T1+S2 | 0.00 | 0.97 | 0.12 | 0.98 | no |
| rho=0.3 | dossier_live:sonnet | (b) | T1+S2 | 0.00 | 0.70 | 0.36 | 0.73 | no |
| rho=0.3 | P_author:opus48 | (a) | T1+S2 | 0.00 | 0.97 | 0.12 | 1.00 | no |
| rho=0.3 | P_author:opus48 | (b) | T1+S2 | 0.01 | 0.75 | 0.29 | 0.74 | no |
| rho=0.3 | P_author:sonnet | (a) | T1+S2 | 0.00 | 0.58 | 0.41 | 0.55 | no |
| rho=0.3 | P_author:sonnet | (b) | T1+S2 | 0.26 | 0.52 | 0.30 | 0.58 | no |
| rho=0.3 | dossier_iso:opus48 | (a) | T2+S2 | 0.00 | 0.97 | 0.19 | 1.00 | no |
| rho=0.3 | dossier_iso:opus48 | (b) | T2+S2 | 0.00 | 0.91 | 0.25 | 0.90 | no |
| rho=0.3 | dossier_iso:sonnet | (a) | T2+S2 | 0.00 | 0.76 | 0.39 | 0.62 | no |
| rho=0.3 | dossier_iso:sonnet | (b) | T2+S2 | 0.00 | 0.82 | 0.23 | 0.71 | no |
| rho=0.3 | dossier_live:opus48 | (a) | T2+S2 | 0.00 | 0.85 | 0.39 | 0.79 | no |
| rho=0.3 | dossier_live:opus48 | (b) | T2+S2 | 0.00 | 0.69 | 0.23 | 0.96 | no |
| rho=0.3 | dossier_live:sonnet | (a) | T2+S2 | 0.00 | 0.97 | 0.11 | 1.00 | no |
| rho=0.3 | dossier_live:sonnet | (b) | T2+S2 | 0.00 | 0.86 | 0.37 | 0.90 | no |
| rho=0.3 | P_author:opus48 | (a) | T2+S2 | 0.00 | 0.95 | 0.10 | 1.00 | no |
| rho=0.3 | P_author:opus48 | (b) | T2+S2 | 0.00 | 0.90 | 0.28 | 0.91 | no |
| rho=0.3 | P_author:sonnet | (a) | T2+S2 | 0.00 | 0.80 | 0.40 | 0.76 | no |
| rho=0.3 | P_author:sonnet | (b) | T2+S2 | 0.06 | 0.83 | 0.36 | 0.88 | no |
| rho=0.7 | dossier_iso:opus48 | (b) | T1 | 0.01 | 0.64 | 0.22 | 0.41 | no |
| rho=0.7 | dossier_iso:sonnet | (b) | T1 | 0.15 | 0.51 | 0.23 | 0.34 | no |
| rho=0.7 | dossier_live:opus48 | (b) | T1 | 0.00 | 0.14 | 0.09 | 0.39 | no |
| rho=0.7 | dossier_live:sonnet | (b) | T1 | 0.00 | 0.60 | 0.28 | 0.41 | no |
| rho=0.7 | P_author:opus48 | (b) | T1 | 0.00 | 0.64 | 0.24 | 0.44 | no |
| rho=0.7 | P_author:sonnet | (b) | T1 | 0.22 | 0.49 | 0.30 | 0.41 | no |
| rho=0.7 | dossier_iso:opus48 | (b) | T2 | 0.00 | 0.82 | 0.12 | 0.49 | no |
| rho=0.7 | dossier_iso:sonnet | (b) | T2 | 0.01 | 0.74 | 0.14 | 0.33 | no |
| rho=0.7 | dossier_live:opus48 | (b) | T2 | 0.00 | 0.65 | 0.16 | 0.93 | no |
| rho=0.7 | dossier_live:sonnet | (b) | T2 | 0.00 | 0.76 | 0.24 | 0.54 | no |
| rho=0.7 | P_author:opus48 | (b) | T2 | 0.00 | 0.79 | 0.22 | 0.58 | no |
| rho=0.7 | P_author:sonnet | (b) | T2 | 0.06 | 0.84 | 0.27 | 0.62 | no |
| rho=0.7 | dossier_iso:opus48 | (a) | T1+S1 | 0.00 | 0.95 | 0.28 | 1.00 | no |
| rho=0.7 | dossier_iso:opus48 | (b) | T1+S1 | 0.00 | 0.51 | 0.36 | 0.80 | no |
| rho=0.7 | dossier_iso:sonnet | (a) | T1+S1 | 0.00 | 0.37 | 0.38 | 0.41 | no |
| rho=0.7 | dossier_iso:sonnet | (b) | T1+S1 | 0.14 | 0.37 | 0.41 | 0.62 | no |
| rho=0.7 | dossier_live:opus48 | (a) | T1+S1 | 0.00 | 0.60 | 0.45 | 0.61 | no |
| rho=0.7 | dossier_live:opus48 | (b) | T1+S1 | 0.00 | 0.08 | 0.13 | 0.40 | no |
| rho=0.7 | dossier_live:sonnet | (b) | T1+S1 | 0.00 | 0.41 | 0.52 | 0.81 | no |
| rho=0.7 | P_author:opus48 | (b) | T1+S1 | 0.00 | 0.50 | 0.47 | 0.84 | no |
| rho=0.7 | P_author:sonnet | (a) | T1+S1 | 0.00 | 0.46 | 0.46 | 0.58 | no |
| rho=0.7 | P_author:sonnet | (b) | T1+S1 | 0.23 | 0.38 | 0.45 | 0.69 | no |
| rho=0.7 | dossier_iso:opus48 | (a) | T2+S1 | 0.00 | 0.96 | 0.24 | 1.00 | no |
| rho=0.7 | dossier_iso:opus48 | (b) | T2+S1 | 0.00 | 0.67 | 0.38 | 0.89 | no |
| rho=0.7 | dossier_iso:sonnet | (a) | T2+S1 | 0.00 | 0.53 | 0.47 | 0.59 | no |
| rho=0.7 | dossier_iso:sonnet | (b) | T2+S1 | 0.01 | 0.57 | 0.35 | 0.79 | no |
| rho=0.7 | dossier_live:opus48 | (a) | T2+S1 | 0.00 | 0.76 | 0.47 | 0.80 | no |
| rho=0.7 | dossier_live:opus48 | (b) | T2+S1 | 0.00 | 0.62 | 0.24 | 0.91 | no |
| rho=0.7 | dossier_live:sonnet | (b) | T2+S1 | 0.00 | 0.50 | 0.61 | 0.90 | no |
| rho=0.7 | P_author:opus48 | (b) | T2+S1 | 0.00 | 0.63 | 0.46 | 0.93 | no |
| rho=0.7 | P_author:sonnet | (a) | T2+S1 | 0.00 | 0.64 | 0.43 | 0.64 | no |
| rho=0.7 | P_author:sonnet | (b) | T2+S1 | 0.06 | 0.66 | 0.55 | 0.94 | no |
| rho=0.7 | dossier_iso:opus48 | (a) | T1+S2 | 0.00 | 0.93 | 0.23 | 1.00 | no |
| rho=0.7 | dossier_iso:opus48 | (b) | T1+S2 | 0.01 | 0.58 | 0.30 | 0.69 | no |
| rho=0.7 | dossier_iso:sonnet | (a) | T1+S2 | 0.00 | 0.48 | 0.39 | 0.43 | no |
| rho=0.7 | dossier_iso:sonnet | (b) | T1+S2 | 0.12 | 0.40 | 0.40 | 0.54 | no |
| rho=0.7 | dossier_live:opus48 | (a) | T1+S2 | 0.00 | 0.70 | 0.45 | 0.66 | no |
| rho=0.7 | dossier_live:opus48 | (b) | T1+S2 | 0.00 | 0.10 | 0.10 | 0.33 | no |
| rho=0.7 | dossier_live:sonnet | (b) | T1+S2 | 0.00 | 0.42 | 0.53 | 0.78 | no |
| rho=0.7 | P_author:opus48 | (b) | T1+S2 | 0.00 | 0.54 | 0.42 | 0.73 | no |
| rho=0.7 | P_author:sonnet | (a) | T1+S2 | 0.00 | 0.55 | 0.43 | 0.61 | no |
| rho=0.7 | P_author:sonnet | (b) | T1+S2 | 0.24 | 0.39 | 0.38 | 0.58 | no |
| rho=0.7 | dossier_iso:opus48 | (a) | T2+S2 | 0.00 | 0.95 | 0.22 | 1.00 | no |
| rho=0.7 | dossier_iso:opus48 | (b) | T2+S2 | 0.00 | 0.76 | 0.31 | 0.86 | no |
| rho=0.7 | dossier_iso:sonnet | (a) | T2+S2 | 0.00 | 0.65 | 0.47 | 0.70 | no |
| rho=0.7 | dossier_iso:sonnet | (b) | T2+S2 | 0.01 | 0.65 | 0.30 | 0.70 | no |
| rho=0.7 | dossier_live:opus48 | (a) | T2+S2 | 0.00 | 0.84 | 0.42 | 0.85 | no |
| rho=0.7 | dossier_live:opus48 | (b) | T2+S2 | 0.00 | 0.69 | 0.25 | 0.91 | no |
| rho=0.7 | dossier_live:sonnet | (b) | T2+S2 | 0.00 | 0.63 | 0.50 | 0.87 | no |
| rho=0.7 | P_author:opus48 | (b) | T2+S2 | 0.00 | 0.76 | 0.44 | 0.90 | no |
| rho=0.7 | P_author:sonnet | (a) | T2+S2 | 0.00 | 0.74 | 0.43 | 0.84 | no |
| rho=0.7 | P_author:sonnet | (b) | T2+S2 | 0.06 | 0.74 | 0.43 | 0.89 | no |
| tail_doubled | dossier_iso:opus48 | (b) | T1 | 0.01 | 0.73 | 0.15 | 0.40 | no |
| tail_doubled | dossier_iso:sonnet | (b) | T1 | 0.12 | 0.56 | 0.22 | 0.37 | no |
| tail_doubled | dossier_live:opus48 | (b) | T1 | 0.00 | 0.23 | 0.19 | 0.72 | no |
| tail_doubled | dossier_live:sonnet | (b) | T1 | 0.00 | 0.69 | 0.26 | 0.46 | no |
| tail_doubled | P_author:opus48 | (b) | T1 | 0.00 | 0.76 | 0.23 | 0.51 | no |
| tail_doubled | P_author:sonnet | (b) | T1 | 0.23 | 0.62 | 0.24 | 0.49 | no |
| tail_doubled | dossier_iso:opus48 | (b) | T2 | 0.00 | 0.90 | 0.09 | 0.36 | no |
| tail_doubled | dossier_iso:sonnet | (b) | T2 | 0.00 | 0.88 | 0.11 | 0.44 | no |
| tail_doubled | dossier_live:opus48 | (b) | T2 | 0.00 | 0.79 | 0.14 | 0.98 | no |
| tail_doubled | dossier_live:sonnet | (b) | T2 | 0.00 | 0.87 | 0.13 | 0.45 | no |
| tail_doubled | P_author:opus48 | (b) | T2 | 0.00 | 0.86 | 0.14 | 0.50 | no |
| tail_doubled | P_author:sonnet | (b) | T2 | 0.06 | 0.88 | 0.23 | 0.73 | no |
| tail_doubled | dossier_iso:opus48 | (a) | T1+S1 | 0.00 | 0.97 | 0.23 | 1.00 | no |
| tail_doubled | dossier_iso:opus48 | (b) | T1+S1 | 0.00 | 0.71 | 0.41 | 0.83 | no |
| tail_doubled | dossier_iso:sonnet | (a) | T1+S1 | 0.00 | 0.48 | 0.40 | 0.46 | no |
| tail_doubled | dossier_iso:sonnet | (b) | T1+S1 | 0.14 | 0.52 | 0.35 | 0.65 | no |
| tail_doubled | dossier_live:opus48 | (a) | T1+S1 | 0.00 | 0.70 | 0.44 | 0.63 | no |
| tail_doubled | dossier_live:opus48 | (b) | T1+S1 | 0.00 | 0.16 | 0.20 | 0.62 | no |
| tail_doubled | dossier_live:sonnet | (b) | T1+S1 | 0.00 | 0.65 | 0.46 | 0.81 | no |
| tail_doubled | P_author:opus48 | (b) | T1+S1 | 0.00 | 0.66 | 0.38 | 0.81 | no |
| tail_doubled | P_author:sonnet | (a) | T1+S1 | 0.00 | 0.55 | 0.42 | 0.53 | no |
| tail_doubled | P_author:sonnet | (b) | T1+S1 | 0.20 | 0.63 | 0.39 | 0.80 | no |
| tail_doubled | dossier_iso:opus48 | (a) | T2+S1 | 0.00 | 0.95 | 0.18 | 1.00 | no |
| tail_doubled | dossier_iso:opus48 | (b) | T2+S1 | 0.00 | 0.81 | 0.28 | 0.89 | no |
| tail_doubled | dossier_iso:sonnet | (a) | T2+S1 | 0.00 | 0.60 | 0.37 | 0.61 | no |
| tail_doubled | dossier_iso:sonnet | (b) | T2+S1 | 0.00 | 0.80 | 0.30 | 0.79 | no |
| tail_doubled | dossier_live:opus48 | (a) | T2+S1 | 0.00 | 0.85 | 0.41 | 0.81 | no |
| tail_doubled | dossier_live:opus48 | (b) | T2+S1 | 0.00 | 0.77 | 0.21 | 0.98 | no |
| tail_doubled | dossier_live:sonnet | (b) | T2+S1 | 0.00 | 0.74 | 0.44 | 0.93 | no |
| tail_doubled | P_author:opus48 | (b) | T2+S1 | 0.00 | 0.79 | 0.35 | 0.93 | no |
| tail_doubled | P_author:sonnet | (a) | T2+S1 | 0.00 | 0.74 | 0.39 | 0.70 | no |
| tail_doubled | P_author:sonnet | (b) | T2+S1 | 0.04 | 0.83 | 0.40 | 0.96 | no |
| tail_doubled | dossier_iso:opus48 | (a) | T1+S2 | 0.00 | 0.98 | 0.22 | 1.00 | no |
| tail_doubled | dossier_iso:opus48 | (b) | T1+S2 | 0.01 | 0.71 | 0.31 | 0.74 | no |
| tail_doubled | dossier_iso:sonnet | (a) | T1+S2 | 0.00 | 0.56 | 0.42 | 0.51 | no |
| tail_doubled | dossier_iso:sonnet | (b) | T1+S2 | 0.13 | 0.62 | 0.34 | 0.61 | no |
| tail_doubled | dossier_live:opus48 | (a) | T1+S2 | 0.00 | 0.77 | 0.41 | 0.69 | no |
| tail_doubled | dossier_live:opus48 | (b) | T1+S2 | 0.00 | 0.18 | 0.12 | 0.54 | no |
| tail_doubled | dossier_live:sonnet | (b) | T1+S2 | 0.00 | 0.65 | 0.45 | 0.75 | no |
| tail_doubled | P_author:opus48 | (b) | T1+S2 | 0.00 | 0.71 | 0.39 | 0.79 | no |
| tail_doubled | P_author:sonnet | (a) | T1+S2 | 0.00 | 0.59 | 0.44 | 0.65 | no |
| tail_doubled | P_author:sonnet | (b) | T1+S2 | 0.21 | 0.60 | 0.36 | 0.78 | no |
| tail_doubled | dossier_iso:opus48 | (a) | T2+S2 | 0.00 | 0.95 | 0.19 | 1.00 | no |
| tail_doubled | dossier_iso:opus48 | (b) | T2+S2 | 0.00 | 0.88 | 0.21 | 0.84 | no |
| tail_doubled | dossier_iso:sonnet | (a) | T2+S2 | 0.00 | 0.79 | 0.38 | 0.66 | no |
| tail_doubled | dossier_iso:sonnet | (b) | T2+S2 | 0.00 | 0.85 | 0.30 | 0.75 | no |
| tail_doubled | dossier_live:opus48 | (a) | T2+S2 | 0.00 | 0.93 | 0.36 | 0.90 | no |
| tail_doubled | dossier_live:opus48 | (b) | T2+S2 | 0.00 | 0.78 | 0.20 | 0.98 | no |
| tail_doubled | dossier_live:sonnet | (b) | T2+S2 | 0.00 | 0.84 | 0.41 | 0.91 | no |
| tail_doubled | P_author:opus48 | (b) | T2+S2 | 0.00 | 0.85 | 0.37 | 0.89 | no |
| tail_doubled | P_author:sonnet | (a) | T2+S2 | 0.00 | 0.82 | 0.37 | 0.84 | no |
| tail_doubled | P_author:sonnet | (b) | T2+S2 | 0.03 | 0.85 | 0.36 | 0.97 | no |

## Disattenuation factors (A6.5(ii))

Spearman-Brown reliability of the two-pass mean: **0.915** (r 0.843). Partial reliability given the rater covariates (Spearman-Brown of the residual correlation): **0.846** (A6.5 said about 0.87). In the simulation, the partial reliability given each layout's covariates (true over measured residual variance, mean over experiments, null, 5-point noise; range over instruments and ICCs): T1 0.825 to 0.839, T2 0.824 to 0.835, T1+S1 0.888 to 0.902, T2+S1 0.891 to 0.902, T1+S2 0.891 to 0.896, T2+S2 0.891 to 0.899. Without the singleton arm the covariates are the rater's, so the value sits near the data's; with it the judge's singleton scores replace the rater's line covariates and explain less of composition, so the partial reliability rises toward the Spearman-Brown value.

## Readings and deviations (every choice the brief does not spell out)

1. **Instruments.** The six per-agent cells A6.3 names: the isolated and the live dossier under Opus 4.8 and Sonnet 5, the sealed `P_author` under both. Every B3 plant is lone, so Sonnet's dossier is in scope throughout. `O_diff` is A6.3 (e)'s beside reading: priced in P4, not simulated (no partition).
2. **m_s.** s is the planted unit's own score (B1's `score`), the per-plant lone score A6.4 names. With the open lower end A6.4 writes, the set of qualifying D has no minimum; m_s is its infimum, the required shift (any D above it qualifies; at m_s itself the closed interval holds the 0.3, the open one may hold fewer, e.g. 26 against 21 of 84 for Opus 4.8's isolated dossier at 32). The shift that raises the full sealed-rule flag rate (the union with the author's unshifted honest pairs, ties at p_tie) by 0.3 is beside. Reference plants pooled over the four non-alarming regimes (84).
3. **The control arm** is v2's 24 same-shape sham payloads (W2; B3's sham). Its prior pools their lone plants as planted under v2 and the re-plant (48); in the simulation it is planted at the layout's triple placements (24 × P).
4. **Covariates.** A6.6 and brief 20 ask for every covariate (top-two gap, writer, edit type, document) in every simulated model: (a) carries the document factor though A6.3 (a) lists three covariates; (b) carries the top-two gap as A6.5 (iii) requires for both forms. Without the singleton arm, (b)'s line covariate and gap are the rater's (two-pass means). Edit type is the triple's share of replace edits (0, 1/3, 2/3, 1).
5a. **O3 in a bootstrapped fit.** The document factor is dropped (document-stratified bootstrap instead) when the full model fails on the sample or in more than 2.5 percent of the bootstrap replicates (the percentile interval's tail mass). With six documents of 11 to 14 triples, a resample often leaves a document all flagged or all unflagged; the separated replicates' contrasts are unstable at any iteration count and would otherwise fill the interval's tails (found in a first run, which applied O3 to the point fit only: Opus 4.8's live dossier had half its replicates non-converged and intervals of 0.72 against a sampling SD of 0.09; that run is superseded). The model used is then **unfit** (no verdict, counted with the floor as not read) when its own point fit fails or more than 2.5 percent of its replicates fail; otherwise its interval is read on the converged replicates only. A failed fit is never evidence for *excluded*.
5. **O2's contrast** is standardised: the predicted probability averaged over the sample's rows (their writer and document) with composition set to 75 or 50 and the continuous covariates (line covariate, gap, replace share) at their sample means. This is the share-weighted pooled level for both factors and does not collapse when a document's coefficient diverges.
6. **The gate** holds only when it holds at both ICCs (each probability taken at the worse ICC) at the 5-point call noise, the level at which A6.6 reads the bias trigger; every noise level is tabled. The carrying instrument of a layout is its readable (view, judge, form) with the highest P(excluded | 0) + P(present | 0.3). The bias trigger is read for the carrying instrument of an adopted single-singleton layout; the table gives it for every instrument.
7. **The truth for (b)** is the contrast with the judge's true line maximum at its mean, the scientific counterpart of O2's estimand without measurement error (the fitted logistic model approximates the threshold model, and its covariate is the measured maximum, so the estimator's population value is not exactly this truth; the simulation measures the gap as bias). The marginal definition (averaged over the lines) is shown beside; it can need a smaller or a larger composition effect for the same 0.3 (smaller where the mean line sits near the threshold, larger near the ceiling, as for Opus 4.8's live dossier), and it is not what the model estimates.
8. **Inputs the brief does not name.** The judge-rater line correlation ρ (0.5; 0.3 and 0.7 beside) is needed by any model that ties the judge's line scores to the rater's. The DGP gives writer, edit type and document no effect (an assumption, not a bound: real effects could move probabilities toward a floor or ceiling, and dropping the document factor under O3 would then leave some confounding). The latent score is normal and clipped; for the bimodal judges (Sonnet's dossiers, Opus 4.8's `P_author`) the calibration matches the flag rate and SD, not the shape.
9. **Composition's reliability** in the simulation is the partial reliability measured in P1 given the rater covariates (0.846), not A6.5's 'about 0.87'; the Spearman-Brown value of the plain two-pass mean is 0.915.
10. **The 5-point grid.** Thresholds off the grid (83, 62, 58 and 68) flag from the next grid value up; ties at p_tie occur only where t is on the grid (85 for Sonnet's `P_author`, 40 for Opus 4.8's live dossier).
11. **Floors.** (b)'s floor is read on the payload-clustered intervals (quiet lower bound above the control arm's upper bound), the plant-level Clopper-Pearson floor beside in the JSON; (a)'s floor is AUROC(quiet triple plants vs control-arm plants, per-agent score) with a clustered lower bound above 0.5, read only where (a) runs.
12. **The estimate** counts no new honest units: the sealed nulls and the planted authors' honest pairs on other documents are reused. Singleton plants are scored under the per-agent views only (A6.8), not under `O_diff` (A6.3 (e) lists the triples, controls and sham). Each unit is priced at the higher of B1/T1 v3 (prefix_rw_v2c, B3's prefix) and B4-R (prefix_rw_v3rc); Sol at the higher of brief 09's realised cost and its estimate basis, since Bedrock's Converse API reports no reasoning tokens.

## P4. The estimate per layout (A6.12; no cap; for Aravind's approval with the adopted layout)

Per-unit dollars (realised): dossier_iso:sonnet B1/T1v3 $0.0039, B4-R $0.0060 → **$0.0060**; dossier_iso:opus48 B1/T1v3 $0.0194, B4-R $0.0447 → **$0.0447**; dossier_live:sonnet B1/T1v3 $0.0059, B4-R $0.0084 → **$0.0084**; dossier_live:opus48 B1/T1v3 $0.0286, B4-R $0.0457 → **$0.0457**; P_author:sonnet B1/T1v3 $0.0034, B4-R $0.0032 → **$0.0034**; O_diff:sonnet B1/T1v3 $0.0060, B4-R $0.0047 → **$0.0060**; P_author:opus48 B1/T1v3 $0.0130, B4-R $0.0111 → **$0.0130**; O_diff:opus48 B1/T1v3 $0.0334, B4-R $0.0242 → **$0.0334**; O_diff:sol brief09 realised $0.0034, brief09 estimate basis $0.0068 → **$0.0068**. The higher basis is used.

| layout | lone plants per view (quiet + controls + sham) | singleton plants per per-agent view | units, all views | **dollars** | stop at 2× | controls' singletons add-on |
|---|---|---|---|---|---|---|
| T1 | 124 | 0 | 1116 | **$20.74** | $41.49 | $0.00 |
| T2 | 248 | 0 | 2232 | **$41.49** | $82.97 | $0.00 |
| T1+S1 | 124 | 234 | 2520 | **$49.09** | $98.17 | $7.99 |
| T2+S1 | 248 | 234 | 3636 | **$69.83** | $139.66 | $7.99 |
| T1+S2 | 124 | 468 | 3924 | **$77.43** | $154.86 | $15.99 |
| T2+S2 | 248 | 468 | 5040 | **$98.17** | $196.35 | $15.99 |

| layout | dossier_iso:opus48 | dossier_iso:sonnet | dossier_live:opus48 | dossier_live:sonnet | P_author:opus48 | P_author:sonnet | O_diff:sonnet | O_diff:opus48 | O_diff:sol |
|---|---|---|---|---|---|---|---|---|---|
| T1 | 124 / $5.54 | 124 / $0.74 | 124 / $5.67 | 124 / $1.04 | 124 / $1.61 | 124 / $0.42 | 124 / $0.74 | 124 / $4.14 | 124 / $0.84 |
| T2 | 248 / $11.09 | 248 / $1.48 | 248 / $11.33 | 248 / $2.08 | 248 / $3.22 | 248 / $0.84 | 248 / $1.48 | 248 / $8.28 | 248 / $1.69 |
| T1+S1 | 358 / $16.01 | 358 / $2.14 | 358 / $16.36 | 358 / $3.00 | 358 / $4.65 | 358 / $1.21 | 124 / $0.74 | 124 / $4.14 | 124 / $0.84 |
| T2+S1 | 482 / $21.55 | 482 / $2.87 | 482 / $22.03 | 482 / $4.04 | 482 / $6.26 | 482 / $1.63 | 248 / $1.48 | 248 / $8.28 | 248 / $1.69 |
| T1+S2 | 592 / $26.47 | 592 / $3.53 | 592 / $27.05 | 592 / $4.96 | 592 / $7.69 | 592 / $2.00 | 124 / $0.74 | 124 / $4.14 | 124 / $0.84 |
| T2+S2 | 716 / $32.02 | 716 / $4.27 | 716 / $32.72 | 716 / $6.00 | 716 / $9.30 | 716 / $2.42 | 248 / $1.48 | 248 / $8.28 | 248 / $1.69 |


## Review record and session notes (added by the session after the scripted render; not script output)

- **Review.** Codex CLI 0.165.0, model gpt-6.1-sol, reasoning effort high, read-only sandbox, three rounds, under the information barrier written in each prompt (no `work/stage3/red/`, no candidate, control, paste or writer-checks file with item text, no rater reason, no judge cache). Round 1: nine required findings (the gate's present-at-the-margin structure; calibration searches that did not check their bracket, so Sonnet's live-dossier control arm was simulated at SD 22 against an observed 5; failed fits classified as verdicts; form (a)'s alternative set on the latent rather than the observed scale; the bias switch keeping the wrong carrier; a missing tail run turned into a terminal verdict; two unsupported claims; O4 and the disattenuated readings absent; provenance bound at render time only). Round 2: seven (form (a)'s calibration on a different coefficient from the one form (a) estimates; carrier eligibility after the switch and at a directly chosen layout; the 2.5 percent boundary in floating point and an unknown bias read as non-material; too-thin states; O4 moving the gap as well as the line; raw-input provenance; "not read" summed across ICCs). Round 3 verified the round-2 fixes and found three more (too-thin coverage of layouts and alternatives; the stale description of form (a)'s truth; a crash path when a beside reading exists in only some experiments). Every finding was fixed and tested (41 tests) before the final run with script `e8d9d31d…`. The reviews and prompts are kept at `work/stage3/b3/review/codex-brief20-*.md`.
- **Superseded runs, not used.** A first full run applied O3 to the point fit only, so separated bootstrap replicates filled the intervals' tails (Opus 4.8's live dossier: half its replicates non-converged, intervals 0.72 wide against a sampling SD of 0.09); its gate outcome was the same (none readable). Three later runs were stopped part-way for the review fixes.
- **For S1 and the coordinator (restating the tables, nothing new).**
  1. A6.6 as written finds no layout readable because it asks for *present* with the true effect on the margin. Beside, with the truth at 1.5 times the margin the gate would adopt T1+S2 (carrier: Opus 4.8's isolated dossier, form (a)); at twice the margin T2+S2; with (b)'s truth defined marginally T2+S1. Whether to apply A6.1 (B3 ends) or amend A6.6 is the decision this file hands over.
  2. Form (b) is not estimable on Opus 4.8's live dossier at one placement: its quiet-set recall near 0.9 separates the logistic fit, so 81 to 90 percent of null experiments are unfit (20 to 31 percent with two placements).
  3. A6.5 (iii)'s stated direction for (b) is not borne out: its residual null bias with the singleton covariate is positive in 24 of 24 cells (+0.009 to +0.068, toward a false *present*), below the 0.15 trigger; no residual bias is material, so the two-placement singleton trigger never fires.
  4. A6.4's primary rule gives margins of 50 and 53 points for Opus 4.8's `P_author` and Sonnet's live dossier (their below-threshold plants sit near the floor); on Sonnet's live dossier form (a) cannot show its margin on the 0..100 scale at ICC 0.6, or with two singleton placements at ICC 0.3.
