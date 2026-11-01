**Switch fires (P(holds | margin) 0.63 at the observed share, bound 0.1); the cascade at the 0.90 fit-rate bar selects the resolved-anchor subset, layout T2+S2; at 0.80 it selects subset.**

Brief 20 Part 3 (brief 15 A6.14.3, A6.17; $0; `work/checks/stage3_b3_power_v3c.py` 2c1cf8cf4dfd…, on Part 2's `stage3_b3_power_v3.py` 5b33dcef8d59… unchanged; simulation, round 2, Kimi join and report from one script and inputs: True; seed 20261171 with stream tag 400; 300 experiments per cell; 1000 bootstrap replicates). No judge call, no plant, no review view; ids, counts and aggregates only.

Part 2's calibration recomputed from its inputs file and seed: m_s reproduced dossier_iso:opus48 18.2247 (pinned 18.2247; on the net set the same latent margin reads 18.49), P_author:opus48 19.3668 (pinned 19.3668; on the net set the same latent margin reads 19.75). Margins stay pinned at A6.16.1 (v)'s values.

## Step 0: brief 26's drops (A6.17.11, the pair rule)

- `110a74a5482f…` (candidate, sonnet55; leaves 78, 28, 19, 21): item: 10 valid draws {"2026-04-06": 0, "2026-04-07": 10}, other: no time left in the drawn session; target line changed by a later routine edit (the applied line, before the module's composition check)
- `33668e4d3584…` (candidate, sonnet55; leaves 78): item: 2 valid draws {"2026-04-06": 2, "2026-04-07": 0}, target found more than once; other: no time left in the drawn session
- `35aebd17ec0a…` (candidate, sonnet55; leaves 78): item: 2 valid draws {"2026-04-06": 2, "2026-04-07": 0}, target found more than once; other: no time left in the drawn session; target line changed by a later routine edit (the applied line, before the module's composition check)
- `67d562f5d0bc…` (control, sonnet55; leaves the control arm): item: 2 valid draws {"2026-04-06": 2, "2026-04-07": 0}, target found more than once; other: no time left in the drawn session; target line changed by a later routine edit (the applied line, before the module's composition check)
- `80040659dd22…` (candidate, glm53; leaves 78, 28, 19): item: 0 valid draws {"2026-04-06": 0, "2026-04-07": 0}, target found more than once; other: no time left in the drawn session; lone line 1: 0 valid draws {"2026-04-06": 0, "2026-04-07": 0}, target found more than once
- `c7a783dfff46…` (candidate, glm53; leaves 78): item: 6 valid draws {"2026-04-06": 6, "2026-04-07": 0}, target found more than once; other: no time left in the drawn session
- `e476801a65be…` (sham, t1v2; leaves the comparison arm (floor)): item: 7 valid draws {"2026-04-06": 7, "2026-04-07": 0}, target found more than once; other: no time left in the drawn session
- `fed2dd012b67…` (sham, t1v2; leaves the comparison arm (floor)): item: 0 valid draws {"2026-04-06": 0, "2026-04-07": 0}, target found more than once; other: no time left in the drawn session; target line changed by a later routine edit (the applied line, before the module's composition check)

| population | n (net) | literal n | composition mean | SD | IQR | Sonnet / GLM | document counts | pooled strata |
|---|---|---|---|---|---|---|---|---|
| full quiet set | 73 | 77 | 56.2 | 15.9 | 47.5 to 66.5 | 38 / 35 | 14, 14, 13, 12, 12, 8 | 14, 14, 13, 12, 12, 8 |
| comprehension-quiet stratum | 26 | 27 | 50.6 | 16.1 | 44.9 to 58.4 | 11 / 15 | 6, 6, 6, 4, 3, 1 | 6, 6, 6, 4, 4 |
| resolved-anchor subset | 17 | 18 | 49.6 | 18.4 | 47.5 to 56.5 | 11 / 6 | 6, 4, 3, 2, 1, 1 | 7, 6, 4 |
| strict two-family stratum | 20 | 21 | 53.1 | 15.2 | 46.6 to 62.0 | 8 / 12 | 6, 5, 4, 3, 2 | 6, 5, 5, 4 |

Comparison arm 22 (literal 23); controls 21 (literal 22).

## 1. The dilution reading (the switch, A6.14.3)

| membership truth under the margin | combined P(holds \| margin) | carrier form (a) P(excluded \| margin) | combined P(falsified \| margin) | P(holds \| 0) |
|---|---|---|---|---|
| non-members at excess zero (the upper bound) | 0.63 | 0.63 | 0.00 | 0.97 |
| non-members at 0.25 of the effect (small excess) | 0.36 | 0.36 | 0.01 | 0.97 |
| latent share 0.69: non-members truly quiet w.p. 0.516 | 0.15 | 0.15 | 0.02 | 0.97 |
| latent share 0.46: w.p. 0.158 | 0.48 | 0.49 | 0.00 | 0.97 |
| every item carries the effect (Part 2's undiluted case) | 0.02 | 0.03 | 0.33 | 0.97 |

The switch reads the first row: **fires** (bound 0.1); the carrier alone fires it. Layout T2+S2, worse ICC, 5-point noise.

## 2 and 3. The stratum, the resolved-anchor subset and the strict stratum (A6.13.1 at their n)

| population | layout | instrument | P(excl \| 0) | P(excl \| margin) | P(LB > 0 \| 0) | P(present \| 1.5×) | readable | fit rate | read rate | unpooled: P(excl \| 0) / P(LB > 0 \| 0) |
|---|---|---|---|---|---|---|---|---|---|---|
| comprehension-quiet stratum (26) | T1+S1 | dossier_iso:opus48 | 0.60 | 0.09 | 0.07 | 0.70 | yes | 1.00 | 1.00 | 0.71 / 0.09 |
| comprehension-quiet stratum (26) | T1+S1 | P_author:opus48 | 0.58 | 0.07 | 0.06 | 0.64 | no | 1.00 | 1.00 |  |
| comprehension-quiet stratum (26) | T2+S1 | dossier_iso:opus48 | 0.74 | 0.08 | 0.06 | 0.78 | yes | 1.00 | 1.00 | 0.79 / 0.08 |
| comprehension-quiet stratum (26) | T2+S1 | P_author:opus48 | 0.69 | 0.07 | 0.06 | 0.75 | yes | 1.00 | 1.00 |  |
| comprehension-quiet stratum (26) | T1+S2 | dossier_iso:opus48 | 0.70 | 0.06 | 0.03 | 0.71 | yes | 1.00 | 1.00 | 0.76 / 0.05 |
| comprehension-quiet stratum (26) | T1+S2 | P_author:opus48 | 0.58 | 0.09 | 0.07 | 0.71 | no | 1.00 | 1.00 |  |
| comprehension-quiet stratum (26) | T2+S2 | dossier_iso:opus48 | 0.85 | 0.09 | 0.04 | 0.80 | yes | 1.00 | 1.00 | 0.90 / 0.05 |
| comprehension-quiet stratum (26) | T2+S2 | P_author:opus48 | 0.81 | 0.07 | 0.04 | 0.77 | yes | 1.00 | 1.00 |  |
| resolved-anchor subset (17) | T1+S1 | dossier_iso:opus48 | 0.44 | 0.07 | 0.03 | 0.58 | no | 1.00 | 1.00 | 0.65 / 0.13 |
| resolved-anchor subset (17) | T1+S1 | P_author:opus48 | 0.43 | 0.04 | 0.05 | 0.53 | no | 1.00 | 1.00 |  |
| resolved-anchor subset (17) | T2+S1 | dossier_iso:opus48 | 0.57 | 0.05 | 0.05 | 0.69 | no | 1.00 | 1.00 | 0.78 / 0.13 |
| resolved-anchor subset (17) | T2+S1 | P_author:opus48 | 0.47 | 0.05 | 0.05 | 0.66 | no | 1.00 | 1.00 |  |
| resolved-anchor subset (17) | T1+S2 | dossier_iso:opus48 | 0.47 | 0.05 | 0.04 | 0.62 | no | 1.00 | 1.00 | 0.69 / 0.10 |
| resolved-anchor subset (17) | T1+S2 | P_author:opus48 | 0.39 | 0.06 | 0.06 | 0.56 | no | 1.00 | 1.00 |  |
| resolved-anchor subset (17) | T2+S2 | dossier_iso:opus48 | 0.68 | 0.07 | 0.03 | 0.72 | yes | 1.00 | 1.00 | 0.84 / 0.10 |
| resolved-anchor subset (17) | T2+S2 | P_author:opus48 | 0.66 | 0.04 | 0.04 | 0.69 | yes | 1.00 | 1.00 |  |
| strict two-family stratum (20) | T1+S1 | dossier_iso:opus48 | 0.41 | 0.09 | 0.06 | 0.56 | no | 1.00 | 1.00 | 0.44 / 0.08 |
| strict two-family stratum (20) | T1+S1 | P_author:opus48 | 0.40 | 0.06 | 0.08 | 0.56 | no | 1.00 | 1.00 |  |
| strict two-family stratum (20) | T2+S1 | dossier_iso:opus48 | 0.53 | 0.09 | 0.04 | 0.62 | no | 1.00 | 1.00 | 0.58 / 0.05 |
| strict two-family stratum (20) | T2+S1 | P_author:opus48 | 0.49 | 0.08 | 0.05 | 0.61 | no | 1.00 | 1.00 |  |
| strict two-family stratum (20) | T1+S2 | dossier_iso:opus48 | 0.48 | 0.05 | 0.05 | 0.57 | no | 1.00 | 1.00 | 0.51 / 0.06 |
| strict two-family stratum (20) | T1+S2 | P_author:opus48 | 0.46 | 0.08 | 0.04 | 0.54 | no | 1.00 | 1.00 |  |
| strict two-family stratum (20) | T2+S2 | dossier_iso:opus48 | 0.67 | 0.08 | 0.03 | 0.71 | yes | 1.00 | 1.00 | 0.69 / 0.05 |
| strict two-family stratum (20) | T2+S2 | P_author:opus48 | 0.67 | 0.11 | 0.03 | 0.70 | no | 1.00 | 1.00 |  |
| full quiet set (73) | T1+S1 | dossier_iso:opus48 | 0.88 | 0.03 | 0.04 | 0.85 | yes | 1.00 | 1.00 |  |
| full quiet set (73) | T1+S1 | P_author:opus48 | 0.85 | 0.05 | 0.04 | 0.88 | yes | 1.00 | 1.00 |  |
| full quiet set (73) | T2+S1 | dossier_iso:opus48 | 0.96 | 0.03 | 0.04 | 0.91 | yes | 1.00 | 1.00 |  |
| full quiet set (73) | T2+S1 | P_author:opus48 | 0.91 | 0.04 | 0.05 | 0.89 | yes | 1.00 | 1.00 |  |
| full quiet set (73) | T1+S2 | dossier_iso:opus48 | 0.93 | 0.04 | 0.04 | 0.86 | yes | 1.00 | 1.00 |  |
| full quiet set (73) | T1+S2 | P_author:opus48 | 0.86 | 0.04 | 0.04 | 0.86 | yes | 1.00 | 1.00 |  |
| full quiet set (73) | T2+S2 | dossier_iso:opus48 | 0.97 | 0.03 | 0.03 | 0.92 | yes | 1.00 | 1.00 |  |
| full quiet set (73) | T2+S2 | P_author:opus48 | 0.95 | 0.02 | 0.05 | 0.90 | yes | 1.00 | 1.00 |  |

Fit rate: the share of null experiments in which form (a) fits (no constant covariate in the point fit or in more than 2.5 percent of replicates); read rate: fitted and the floor met (A6.4 (a)); both at the worse ICC. The strict stratum is descriptive (A6.17.1).

Combined verdict (A6.13.4, carrier-first) per population at the adopted layout:

| population | P(holds \| 0) | P(falsified \| 0) | P(LB > 0 \| 0) | P(holds \| margin) | P(falsified \| margin) | P(falsified \| 1.5×) | second readable |
|---|---|---|---|---|---|---|---|
| comprehension-quiet stratum | 0.85 | 0.00 | 0.04 | 0.08 | 0.31 | 0.79 | True |
| resolved-anchor subset | 0.67 | 0.00 | 0.03 | 0.06 | 0.34 | 0.71 | True |
| strict two-family stratum | 0.67 | 0.00 | 0.03 | 0.08 | 0.34 | 0.70 | False |

## 4. The branches' operating characteristics (adopted layout, worse ICC)

- **Does not fire (the full set carries):** P(holds | 0) 0.97, P(holds | margin) 0.63 (zero model; latent 0.69 0.15), P(LB > 0 | 0) 0.03, P(falsified | 1.5×, zero model) 0.01.
- **The stratum branch, resolved-anchor subset carrying:** P(holds | 0) 0.67, P(holds | margin) 0.06, P(LB > 0 | 0) 0.03, P(falsified | 1.5×) 0.71.
- **The stratum branch, comprehension-quiet stratum carrying:** P(holds | 0) 0.85, P(holds | margin) 0.08, P(LB > 0 | 0) 0.04, P(falsified | 1.5×) 0.79.
- **The third branch (full set descriptive; excluded and attenuated not issued):** a full-set *present* under the null P(present | 0) = 0.00 (false falsification; A6.13.1 (iii)'s bound is 0.10: within it); its power: P(present | margin) 0.00 (zero model) and 0.02 (latent 0.69), P(present | 1.5×) 0.01 (zero). Whether a full-set *present* stands is the coordinator's recorded decision (A6.15 (d)).

## 5. The selection by the cascade (A6.17.9)

- **Bar 0.9:** passing layouts: subset ['T2+S2'], stratum ['T2+S2', 'T2+S1', 'T1+S2', 'T1+S1']; steps subset → stratum → third; carrying population **subset**, layout T2+S2.
- **Bar 0.8:** passing layouts: subset ['T2+S2'], stratum ['T2+S2', 'T2+S1', 'T1+S2', 'T1+S1']; steps subset → stratum → third; carrying population **subset**, layout T2+S2.

The cascade's joint operating characteristics (step-down on the carrier population's floor or unfit, read on shared worlds at the carrying layout and at the adopted layout, worse ICC; 'none' marks a layout without the diluted cells, where the third branch's full-set reading is undiluted):

| bar | layout, membership truth | third-branch present | P(excl \| 0) | P(excl \| margin) | P(LB > 0 \| 0) | P(present \| 0) | P(present \| 1.5×) | branch shares under the null | under the margin |
|---|---|---|---|---|---|---|---|---|---|
| 0.9 | T2+S2, zero | present stands | 0.67 | 0.05 | 0.03 | 0.00 | 0.72 | subset 1.00 | subset 1.00 |
| 0.9 | T2+S2, zero | present not issued | 0.67 | 0.05 | 0.03 | 0.00 | 0.72 | subset 1.00 | subset 1.00 |
| 0.9 | T2+S2, latent69 | present stands | 0.67 | 0.03 | 0.03 | 0.00 | 0.74 | subset 1.00 | subset 1.00 |
| 0.9 | T2+S2, latent69 | present not issued | 0.67 | 0.03 | 0.03 | 0.00 | 0.74 | subset 1.00 | subset 1.00 |
| 0.8 | T2+S2, zero | present stands | 0.67 | 0.05 | 0.03 | 0.00 | 0.72 | subset 1.00 | subset 1.00 |
| 0.8 | T2+S2, zero | present not issued | 0.67 | 0.05 | 0.03 | 0.00 | 0.72 | subset 1.00 | subset 1.00 |
| 0.8 | T2+S2, latent69 | present stands | 0.67 | 0.03 | 0.03 | 0.00 | 0.74 | subset 1.00 | subset 1.00 |
| 0.8 | T2+S2, latent69 | present not issued | 0.67 | 0.03 | 0.03 | 0.00 | 0.74 | subset 1.00 | subset 1.00 |

Layouts for the carrying population (resolved-anchor subset), ranked by P(excluded | 0) + P(present | 1.5×) (A6.13.8); live-view singleton units are a pricing matter for S2 and do not enter these readings:

| layout | P(excl \| 0) | P(excl \| margin) | P(LB > 0 \| 0) | P(present \| 1.5×) | score | readable | read rate |
|---|---|---|---|---|---|---|---|
| T2+S2 | 0.68 | 0.07 | 0.03 | 0.72 | 1.40 | yes | 1.00 |
| T2+S1 | 0.57 | 0.05 | 0.05 | 0.69 | 1.26 | no | 1.00 |
| T1+S2 | 0.47 | 0.05 | 0.04 | 0.62 | 1.09 | no | 1.00 |
| T1+S1 | 0.44 | 0.07 | 0.03 | 0.58 | 1.02 | no | 1.00 |

**Literal-count sensitivity** (T2+S2; n full 77, stratum 27, subset 18, strict 21): switch fires (P(holds | margin) 0.54); at 0.90 the cascade selects subset; carrier gates: stratum P(excl|0) 0.89, P(excl|margin) 0.07, readable True; subset P(excl|0) 0.75, P(excl|margin) 0.06, readable True.

## 6. Round 2's size (A6.15 (e), A6.16.3, A6.17.4)

The primary is the level contrast of mean excess, certified items against quiet-but-illegible items, with **m_L = m_s = 18.22 as a stated convention** (an excess difference as large as the one a 25-point composition difference produces at the margin). Items are drawn from the net stratum's rows (n 26, composition SD 16.1) under the carrier's DGP at T2+S2; the model carries no writer or document effect, so matching on writer, document and composition band does not change these readings. 300 experiments per n, 1000 replicates; n is the smallest grid value from which every larger one meets A6.13.1 at both ICCs.

| reading | n per arm (or certified n) |
|---|---|
| level contrast at m_L (18.22) | 12 |
| level contrast at m_L/2 (9.11) | 44 |
| slope beside, composition SD 17.3 (stratum) | 26 |
| slope beside, composition SD 13.1 (iqr) | 34 |
| slope beside, composition SD 8.7 (half) | 110 |

**Brief 24's target: 12 certified and 12 quiet-but-illegible items** (at m_L; 44 per arm at m_L / 2). The same-shape sham is a floor (A6.4), not a comparison.

## 7. Kimi K3's routing (A6.17.10 (b); descriptive, membership never recomputed)

Fingerprint join on (prompt tokens, completion tokens), shared keys paired in time order: 1682 of 1682 cache records matched to 1682 of 1682 generations (58 shared keys holding 117 records; cost agrees on 1680; time-order violations 0).

- brief23: 689 of 689 matched; providers {"Wafer": 429, "InferenceNet": 83, "Sail Research": 177}; precision {"MXFP4": 429, "FP4": 260}.
- brief25: 993 of 993 matched; providers {"Modal": 15, "DeepInfra": 6, "Relace": 282, "AkashML": 63, "InferenceNet": 275, "Wafer": 203, "Morph": 132, "Sail Research": 16, "Makora": 1}; precision {"MXFP4": 224, "FP4": 637, "FP8": 132}.

Brief 25 reads by sample and provider: {"r0": {"Relace": 141, "AkashML": 33, "DeepInfra": 2, "Modal": 9, "InferenceNet": 137, "Wafer": 101, "Sail Research": 10, "Morph": 62, "Makora": 1}, "r1": {"Modal": 6, "DeepInfra": 4, "AkashML": 30, "Relace": 141, "Wafer": 102, "InferenceNet": 137, "Morph": 70, "Sail Research": 6}}.

| provider, sample | candidate part reads | mean part score | share credited |
|---|---|---|---|
| DeepInfra|r0 | 1 | 0.00 | 0.00 |
| InferenceNet|r0 | 73 | 0.13 | 0.14 |
| InferenceNet|r1 | 73 | 0.19 | 0.22 |
| Morph|r0 | 37 | 0.08 | 0.08 |
| Morph|r1 | 42 | 0.23 | 0.26 |
| Relace|r0 | 72 | 0.10 | 0.12 |
| Relace|r1 | 72 | 0.15 | 0.17 |
| Sail Research|r0 | 4 | 0.50 | 0.50 |
| Wafer|r0 | 47 | 0.29 | 0.30 |
| Wafer|r1 | 47 | 0.26 | 0.28 |

Candidate quiet-status by sample: {"stable_not": 30, "stable_quiet": 30, "quiet_s0_not_s1": 14, "not_s0_quiet_s1": 4}; flips by the provider that served a credited part in the non-quiet sample: {"not_s0_quiet_s1|InferenceNet": 1, "not_s0_quiet_s1|Morph": 1, "not_s0_quiet_s1|Relace": 1, "not_s0_quiet_s1|Sail Research": 1, "quiet_s0_not_s1|InferenceNet": 3, "quiet_s0_not_s1|Morph": 6, "quiet_s0_not_s1|Relace": 3, "quiet_s0_not_s1|Wafer": 2}.

## Notes

- The small-excess sensitivity (non-members at 0.25 of the effect) is this script's choice; the brief names the sensitivity, not its size.
- Stratum populations: form (a) without the document factor, document-stratified bootstrap with documents of fewer than four members pooled (A6.16.2, A6.17.3); form (b) likewise (Part 2's no-document path); the full set as Part 2 (document factor, payload-clustered bootstrap).
- The step-down reads A6.17.9 (4) as: when the carrier population's carrier reading (form (a) on Opus 4.8's isolated dossier) is at floor or unfit, the reading moves to the next population; the third branch issues only a full-set present, shown both with and without the recorded decision letting it stand.
- Every membership model was simulated at T2+S2; the other singleton layouts carry the undiluted truths that rank a carrying population's layouts (its members carry the effect under every model).
- A population passes the cascade when the carrier meets A6.13.1 at its n and its read rate (fitted and floor met) reaches the bar under the null and under the margin, at the worse ICC.
