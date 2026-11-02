# S3 readings script: the dry run before any draw (brief 33 A2; counts only)

Readings script `work/checks/stage3_b3_s3_readings.py` e31d8fba; matrix 1b80280a. Fixtures run in 393 s.

## 1. Reachability by constructed fixtures

| fixture | knobs | expected ids | reached | missing |
|---|---|---|---|---|
| baseline | beta 0 on every instrument: excluded, holds, confirmed | S-A1, S-A5, S-D3, S-E1, S-F1, S-Fs1, S-G1, S-I1, S-J1, S-K3, S-K4, S-L1, S-M1, S-M2, S-M3, S-M4, S-N1, S-N2, S-O1, S-O2, S-P0, S-Q2, S-R1, S-S0, S4-2 | yes (107 sentences) | — |
| present | beta 1.2 per point (30 points over the span): present, falsified | S-D1, S-F3, S-Fs1 | yes (91 sentences) | — |
| attenuated | beta 0.35 per point (about 9 points): attenuated, partly missed | S-D2, S-F2, S-G1 | yes (103 sentences) | — |
| inconclusive | beta 0.35 per point with wide noise: the interval cannot tell zero from m_s (inconclusive) | S-D4, S-F4 | yes (102 sentences) | — |
| two_step_within | form (a) excluded with form (b) present (bias-net lower bound above 0) on the carrier: the two-step conflict within an instrument | S-E2, S-F5 | yes (92 sentences) | — |
| two_step_across | the carrier excluded, the second named instrument present: a two-step conflict across instruments | S-F6 | yes (99 sentences) | — |
| one_step_across | the carrier excluded, the second attenuated: differs by one step, beside | S-F1, S-Fs2 | yes (103 sentences) | — |
| floor_carrier | the carrier's sham drawn from the quiet distribution: the carrier at floor (a) issues only its floor sentence (G3), the second leads as the fallback carrier | S-A1, S-A2, S-F1, S-Fs3 | yes (81 sentences) | — |
| floor_both | both named instruments at floor: no verdict | S-A2, S-A3 | yes (48 sentences) | — |
| floor_b | form (b)'s floor failed: the quiet lone recall does not clear the sham's | S-A4, S-E3, S-L2, S-R2 | yes (88 sentences) | — |
| ceiling | quiet lone recall above 0.85: form (b) past the ceiling | S-B1, S-E3, S-L2, S-R2 | yes (90 sentences) | — |
| fit_i_constant | fit failure (i): the writer constant on the subset; the reading steps down to the stratum | S-C1 | yes (93 sentences) | — |
| subset_stratum_disagree | the nine unresolved members carry a strong effect, the subset none: the subset and the stratum disagree (S-I2) | S-I2 | yes (102 sentences) | — |
| fit_ii_replicates | fit failure (ii): a factor level held by one item on the subset, so more than 10 percent of the 2,000 replicates are singular (property asserted) | S-C1 | yes (94 sentences) | — |
| fit_iii_empty_stratum | fit failure (iii): every item of one pooled stratum of the subset refused under the carrier (an empty pooled stratum; the loss is above 10 percent) | A1b-provisional, S-C1 | yes (100 sentences) | — |
| stratum_too | the writer constant on the whole stratum: the carrier unfit on 17 and 26, the second takes the lead (S-C3), is unfit too, the third branch (S-H1) | S-C1, S-C2, S-C3, S-H1 | yes (86 sentences) | — |
| third_present | as above with a full-set present: S-H2 | S-H2 | yes (76 sentences) | — |
| nothing_fits | the writer and the replace share constant on the full set: nothing fits on any population (S-C3b, S-C4) | S-C3b, S-C4 | yes (71 sentences) | — |
| c5_form_b_singular | the judge's singleton maximum constant: form (b)'s design singular (S-C5) | S-C5 | yes (74 sentences) | — |
| c6_other_unfit | the second named instrument loses a pooled stratum of the subset to refusals: unfit there while the carrier reads (S-C6) | S-C6, S-Fs3 | yes (103 sentences) | — |
| refused_component | one lone-line application refused under the carrier: that item not evaluable (n = 16 on the subset) | S-F1 | yes (103 sentences) | — |
| stopped_lead | the carrier's row not scored at a stop: treated as not passing its floor; the second leads | A1b-d, S-A2, S-F1, S-Fs3 | yes (81 sentences) | — |
| stopped_second | the second named instrument's row not scored at a stop: it drops out, named | A1b-d, S-A2, S-F1, S-Fs3 | yes (81 sentences) | — |
| g1_fails | Opus 4.8's composed share below 0.65: G1 fails | S-N3 | yes (103 sentences) | — |
| sq1 | flags driven by the rater's section-2 maximum: S-Q1 | S-Q1 | yes (99 sentences) | — |
| k1 | the composition contrast falls with Kimi K3's D_part: S-K1 | S-K1 | yes (103 sentences) | — |
| k2 | the composition contrast rises with D_part: S-K2 | S-K2 | yes (103 sentences) | — |
| g6_clean | G6: three subset items and one more stratum item touched by a broken honest edit; form (a) on the rest, beside, descriptive | S-G6 | yes (107 sentences) | — |
| g6_too_small | G6: fifteen of the subset's seventeen touched: the restricted sets too small for the fit (the subset singular, the stratum with an empty pooled stratum); the sentence says so with the counts | S-G6b | yes (107 sentences) | — |
| own_drops | one own drop recorded: S-S1 | S-S1 | yes (103 sentences) | — |

### Every sentence id of section 6 and the fixture that reaches it

| id | reached by |
|---|---|
| S-G6 | g6_clean |
| S-G6b | g6_too_small |
| S-S0 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small |
| S-S1 | own_drops |
| S-A1 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-A2 | floor_carrier, floor_both, stopped_lead, stopped_second |
| S-A3 | floor_both |
| S-A4 | floor_b |
| S-A5 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-B1 | ceiling |
| S-C1 | fit_i_constant, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular |
| S-C2 | stratum_too, third_present, nothing_fits, c5_form_b_singular |
| S-C3 | stratum_too, third_present, nothing_fits, c5_form_b_singular |
| S-C3b | nothing_fits, c5_form_b_singular |
| S-C4 | nothing_fits, c5_form_b_singular |
| S-C5 | fit_i_constant, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, sq1 |
| S-C6 | c6_other_unfit |
| S-D1 | present, inconclusive, two_step_within, two_step_across, third_present |
| S-D2 | attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-D3 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-D4 | baseline, present, attenuated, inconclusive, two_step_across, one_step_across, floor_carrier, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-E1 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-E2 | present, two_step_within, two_step_across |
| S-E3 | floor_b, ceiling, fit_i_constant, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, sq1 |
| S-F1 | baseline, one_step_across, floor_carrier, floor_b, ceiling, subset_stratum_disagree, fit_iii_empty_stratum, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k2, g6_clean, g6_too_small, own_drops |
| S-F2 | attenuated, fit_i_constant, fit_ii_replicates, k1 |
| S-F3 | present |
| S-F4 | inconclusive |
| S-F5 | two_step_within |
| S-F6 | two_step_across |
| S-Fs1 | baseline, present, attenuated, two_step_within, floor_b, ceiling, subset_stratum_disagree, fit_iii_empty_stratum, refused_component, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-Fs2 | inconclusive, one_step_across, fit_i_constant, fit_ii_replicates |
| S-Fs3 | floor_carrier, c6_other_unfit, stopped_lead, stopped_second |
| S-G1 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-H1 | stratum_too |
| S-H2 | third_present |
| S-I1 | baseline, present, attenuated, floor_carrier, k1 |
| S-I2 | inconclusive, two_step_within, two_step_across, one_step_across, floor_b, ceiling, subset_stratum_disagree, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k2, g6_clean, g6_too_small, own_drops |
| S-J1 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-K1 | subset_stratum_disagree, k1 |
| S-K2 | k2 |
| S-K3 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_b, ceiling, fit_i_constant, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, g6_clean, g6_too_small, own_drops |
| S-K4 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-L1 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-L2 | floor_b, ceiling, fit_i_constant, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, sq1 |
| S-M1 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-M2 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-M3 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-M4 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_b, ceiling, subset_stratum_disagree, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-N1 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-N2 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-N3 | g1_fails |
| S-O1 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-O2 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_b, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-P0 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-Q1 | present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c6_other_unfit, refused_component, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-Q2 | baseline, present, attenuated, inconclusive, two_step_across, one_step_across, floor_b, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, k1, k2, g6_clean, g6_too_small, own_drops |
| S-R1 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| S-R2 | two_step_within, floor_both, floor_b, ceiling, fit_i_constant, fit_ii_replicates, stratum_too, third_present, nothing_fits, c5_form_b_singular, sq1 |
| S4-2 | baseline, present, attenuated, inconclusive, two_step_within, two_step_across, one_step_across, floor_carrier, floor_both, floor_b, ceiling, fit_i_constant, subset_stratum_disagree, fit_ii_replicates, fit_iii_empty_stratum, stratum_too, third_present, nothing_fits, c5_form_b_singular, c6_other_unfit, refused_component, stopped_lead, stopped_second, g1_fails, sq1, k1, k2, g6_clean, g6_too_small, own_drops |
| A1b-d | stopped_lead, stopped_second |
| A1b-provisional | fit_iii_empty_stratum |
| S-P1 | unreachable by decision: the k = 2 arm is not run (plan section 4.6, S2's note) |
| S-I3 | no sentence (S-C1 names the case) |
| S4-1 | written by a separate $0 session after Aravind reports his scores (brief 33 B3) |
| S-Fscope | a clause attached to S-F1 (reached with it) |

All fixtures reach their ids: True. Ids not reached by any fixture: none.

## 2. Operating characteristics from Part 3's simulator through the adapter

Seed 20261171 with stream tag 500; ICC 0.3; layout T2+S2; 300 experiments per truth; 2000 replicates per fit; wall time 1451 s.

| truth | population | membership model | instrument | form (a): excluded / attenuated / present / inconclusive / floor / unfit | form (b): excluded / attenuated / present / inconclusive / floor / ceiling / unfit |
|---|---|---|---|---|---|
| null | subset | none | C | 0.64 / 0.02 / 0.00 / 0.34 / 0.00 / 0.00 | 0.54 / 0.02 / 0.01 / 0.41 / 0.00 / 0.00 / 0.02 |
| null | subset | none | S | 0.62 / 0.01 / 0.01 / 0.36 / 0.00 / 0.00 | 0.51 / 0.03 / 0.01 / 0.42 / 0.00 / 0.00 / 0.03 |
| null | full | zero | C | 0.97 / 0.03 / 0.00 / 0.00 / 0.00 / 0.00 | 0.90 / 0.06 / 0.00 / 0.04 / 0.00 / 0.00 / 0.00 |
| null | full | zero | S | 0.95 / 0.03 / 0.00 / 0.02 / 0.00 / 0.00 | 0.86 / 0.10 / 0.00 / 0.05 / 0.00 / 0.00 / 0.00 |
| margin | subset | none | C | 0.09 / 0.23 / 0.35 / 0.33 / 0.00 / 0.00 | 0.09 / 0.12 / 0.13 / 0.62 / 0.00 / 0.00 / 0.04 |
| margin | subset | none | S | 0.04 / 0.20 / 0.32 / 0.43 / 0.00 / 0.00 | 0.04 / 0.12 / 0.16 / 0.62 / 0.00 / 0.00 / 0.05 |
| margin | full | zero | C | 0.57 / 0.35 / 0.00 / 0.08 / 0.00 / 0.00 | 0.59 / 0.31 / 0.01 / 0.09 / 0.00 / 0.00 / 0.00 |
| margin | full | zero | S | 0.61 / 0.27 / 0.01 / 0.11 / 0.00 / 0.00 | 0.55 / 0.31 / 0.02 / 0.12 / 0.00 / 0.00 / 0.00 |
| x1.5 | subset | none | C | 0.00 / 0.15 / 0.73 / 0.12 / 0.00 / 0.00 | 0.03 / 0.11 / 0.27 / 0.48 / 0.00 / 0.00 / 0.11 |
| x1.5 | subset | none | S | 0.00 / 0.13 / 0.69 / 0.18 / 0.00 / 0.00 | 0.01 / 0.08 / 0.28 / 0.51 / 0.00 / 0.00 / 0.11 |
| x1.5 | full | zero | C | 0.35 / 0.48 / 0.01 / 0.16 / 0.00 / 0.00 | 0.44 / 0.38 / 0.03 / 0.15 / 0.00 / 0.00 / 0.00 |
| x1.5 | full | zero | S | 0.32 / 0.50 / 0.01 / 0.17 / 0.00 / 0.00 | 0.37 / 0.46 / 0.03 / 0.14 / 0.00 / 0.00 / 0.00 |

Acceptance (brief 33 A2, fixed before the run; three Monte Carlo SE at 300): the carrier's P(excluded | 0) on the subset 0.640 against Part 3's 0.68 (ICC 0.3), P(present | 1.5 x) 0.730 against 0.72; tolerance ± 0.08: **ACCEPTED**.
