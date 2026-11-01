# Brief 25 (B3's comprehension-quiet stratum): review and next steps (review session, Opus 5.5, 2026-11-01)

Blue side. Aggregates and per-item numeric values by opaque id only. Section 1 was written before the independent Fable read returned. Section 3 reconciles the two.

## 1. My read, written first

### Verified (`stratum-v0.json` 6113bd8d, `stratum-v0.md`, `errors.log`, the run script)
- **The stratum.** It holds 28 of 78 (0.359): GLM 16, Sonnet 12. None is not evaluable and there are no refusals.
- **The rule** (C1): Kimi K3 D_part = 0 on both samples, and Sol's mean D_part ≤ 0.5. C1 found no rule reaching 0.8/0.1. Its best attainable pair is P(labelled quiet | truly quiet) 0.52 [0.13, 0.74] and P(labelled quiet | not quiet) 0.005 [0.000, 0.03].
- **The nulls are clean.** All 46 controls and sham have D_part > 0 at 0.000 and D_whole at 0.000 under every reader, with the paired sham at 0.000.
- **The positive control** gives D_part_own 1.00 and D_whole_own 0.85 to 1.00. Scorer kappa is 0.91 to 0.92.
- **The exit code 1 is benign.** After the run, the print guard refused to echo the approval rule's free text to stdout (`$.approval.rule`). Every output file was written.
- **The stratum against the rest:**

  | | n | composition mean | composition SD | composition IQR | top line | top-two gap |
  |---|---|---|---|---|---|---|
  | stratum | 28 | 48.6 | 17.0 | 19.0 | 43.1 | 10.8 |
  | rest | 50 | 59.7 | 14.8 | 22.5 | 44.7 | 13.1 |
  | all 78 | 78 | | 16.5 | | | |

- **Within the stratum,** the whole is credited under both readers on 11 items, on no sample under either on 7, and mixed on 10.
- **Sample symmetry.** Kimi K3's two samples are not alike: 44 items quiet on sample 0 against 34 on sample 1. Of its quiet-status flips, 14 went quiet → not and 4 not → quiet (two-sided sign p 0.03), and mean D_part was 0.40 against 0.51. Sol is symmetric (7 against 9). Sonnet 5.5 leans the same way as Kimi (5 against 2, p 0.45). The run script shuffles both samples into one seeded call order and sends the same packet for both (`reader_units`, `ordered`), so I find no pipeline cause.

### What it means
1. **The stratum is a high-purity subset, not the whole quiet population.**
   - At the chosen rule, about half of truly quiet items are labelled quiet, and almost no non-quiet item is (C1's T1-fitted model; wide interval).
   - The implied true quiet share is roughly (0.36 − 0.005) / (0.52 − 0.005) ≈ 0.69, but the interval is wide.
   - So Part 3's "non-members at excess zero" really is an upper bound on dilution, as labelled, and conservative for the switch.
   - The stratum itself should be read as "items where two readers never found a giveaway line", which is the purity A6.14 wants.
2. **The likely branch is the second: the stratum carries round 1's verdict** (toy, argued; Part 3 decides).
   - q = 0.36 is below the switch's 0.58 to 0.72, so the switch fires.
   - The stratum keeps the full set's composition spread (SD 17.0 against 16.5). At that spread, Fable's toy from Part 2's review makes n ≥ 17 readable, so n = 28 is plausibly readable at about 0.8.
   - The open risk is form (a)'s fit rate with about ten parameters at n = 28 under the payload-clustered bootstrap, and with 16 against 12 by writer. A6.16's document-stratified bootstrap applies below n = 30, which covers 28.
3. **The stratum sits about 11 composition points lower than the rest.** Items with no giveaway line are the ones the rater also sees as less combined. This is not a defect, because form (a) reads a slope. But the stratum's verdict is on a lower-composition population, and S1's sentence should say so.
4. **Kimi K3's sample asymmetry: report it, don't act on it.** It is one significant result among three readers, found by looking, with no mechanism in the code. It does not change membership, since the rule needs both samples. Kimi's per-item flip rate (0.23) also matches T1's (2 of 10). Two cheap checks, by script, counts only:
   - whether the OpenRouter upstream provider differed by sample. The cache records it; the coordinator or a blue session reads that field only;
   - whether a third Kimi sample on the 28 shifts membership, as a sensitivity. It is not required.
5. **The T1 join (exploratory, P4).**
   - 27 of 138 lines (20%) that the rater scored as routine (≤ 60) let readers from two families state the declared consequence from that line alone (v2 17 of 70, v3 10 of 68). The line score correlates only weakly with that (Spearman 0.28 to 0.35).
   - **May be said:** on these items, about one routine-scored line in five lets a reader derive the planted consequence when asked what follows.
   - **May not be said:** anything about what the per-account judges perceive. The readers are not the judges, and "derivable when asked" is not "flagged". The coordinator's hypothesis of 2026-11-01 (the 'middle band' as derivable-but-unalarming) is supported in part on T1 lines and stays a hypothesis for the judges.
   - A "consequence question" view would test it directly. That is a candidate for the adaptive round, not for B3.
6. **The coordinator's m_L question.**
   - If round 2's level contrast matches its arms on composition band, as A6.16 says, the composition-slope model predicts no level difference between the arms. m_L therefore cannot be derived from β*.
   - m_L = m_s is then a stated convention: "the level contrast should detect an excess difference as large as a 25-point composition difference produces at the margin". It is not a calibration, and that is acceptable if written as such.
   - Part 3 should report power at m_L = m_s and at m_s/2, and use the stratum's observed spread (SD 17, IQR 19) as the round-2 dose-spread anchor. Using that spread is an instrument look at items, not an outcome.
7. **The round-1 preview of the level contrast** (11 items whole-credited against 7 not, within the stratum).
   - It may be reported descriptively, written in S1 before S3, as "descriptive, not a test; round 2 is the test".
   - Round 2's n and m_L are fixed by Part 3 before S3, so no round-1 outcome can size round 2.

### Next steps (in order)
1. Brief 20 Part 3 on `stratum-v0.json`: the branch, the stratum's composition SD and fit rate, the stratified bootstrap check, the third-branch note if needed, and round 2's n and m_L as a stated convention with the stratum's spread as the anchor.
2. The dated notes and S1, with the lower-composition scope sentence and the descriptive level-contrast preview.
3. S2. Aravind confirms the layout and the estimate of about $73 after the live singletons are stripped.
4. S3.
5. Brief 24, aimed at both round-2 arms, then round 2.

## 2. Fable's independent read (Fable 5.1, high; briefed with files and a barrier list, without section 1)

Summary, not verbatim. Fable reproduced membership by script with 0 mismatches and the id hash 410e7461.

- **Q1. Sol's rule is close to vacuous.**
  - At two samples, "Sol mean ≤ 0.5" rejects only the sample pairs (1,1), (1,½) and (½,1). It removed 2 of Kimi K3's 30.
  - So the stratum is, in practice, **Kimi K3 at two samples**. A6.14.4's phrase "under two reader families" overstates it.
  - The sensitivity of 0.52 implies a latent quiet share of about 0.69 (interval 0.46 to unidentified). The stratum is pure, but the rest is roughly half truly quiet.
  - Part 3 should run the latent share as a named sensitivity beside the observed 0.36. The latent-class model is fitted on T1, and Sol's flip rate on B3 (0.205) is half its T1 rate, so the transfer is imperfect.
- **Q2. The stratum against the rest.**
  - Composition: 48.6 / 17.3 / [39.4, 57.1] against 59.7 / 14.9 / [49.5, 71.0]. Items at ≥ 60: 6 against 26.
  - Writers balanced (Fisher p 0.24). Documents 8, 6, 6, 4, 3, **1**.
  - **Unresolved day-0 anchors are over-represented:** 9 of 16 unresolved items against 19 of 62 resolved ones (OR 2.9, p 0.08). The rendering may make parts look illegible.
  - Toy model: P(excluded | 0) ≈ 0.59 to 0.64, or about 0.53 after the loss of degrees of freedom, so readability sits on the gate. A six-level document factor with a one-item level will not be identified. Branch 3 may be the most likely outcome. Carry the resolved-anchor subset (19) beside.
- **Q3. The within-stratum preview** (11 against 7) is unreadable (toy 0.33). Report it descriptively, with one fixed definition (the whole credited under both readers on any sample), the ids hashed and no verdict label. Round-1 judge outcomes never feed round 2's n.
- **Q4. The T1 join.**
  - **May say:** 27 of 138 rater-quiet lines yield the consequence alone under two families (v2 0.24, v3 0.15). Spearman is 0.28 to 0.35 pooled (v2 0.48 to 0.53, v3 0.18 to 0.27).
  - **May not say:** anything about lines above 60, about B3's items, a validity verdict on the rater, or a stable magnitude (one sample, restricted range).
- **Q5. Fragile points.**
  - Exit 1 is benign. Store the approval rule as a key next time.
  - C1's script hash (3f26f0e3) differs from the run's (57d80170). Record the change as a deviation.
  - The one-item document needs a merge-or-drop rule before Part 3.
- **The most important next step:** Part 3 with two membership inputs (the observed 28/50 and the latent 0.69), the fit rate at the actual document counts and the resolved-anchor subset beside it.

## 3. Reconciliation (review session)

**Agreed and verified:**
- membership, the hash and every count above;
- the stratum is pure, and Part 3's dilution null is an upper bound;
- the switch fires at the observed share;
- the within-stratum preview is descriptive only;
- the T1 join's may and may-not;
- exit 1 is benign.

**The readability disagreement, settled by recomputation.** Fable's 0.59 to 0.64 starts from the m/se of 3.5 to 3.7 in my first Part 2 toy, which that review's reconciliation had already set aside. I recomputed from the simulation's own figures for the carrier at T2+S2, 5-point noise: the point SD and the mean CI half-width. That toy reproduces the full set at q = 1 (0.979 against the simulation's 0.977 at ICC 0.3). Scaling SD and half-width by the stratum's standard-error ratio of 1.60 (composition SD 17.3, n = 28) gives P(excluded | 0) ≈ **0.85 at ICC 0.3 and 0.95 at ICC 0.6, before the loss of degrees of freedom**. The gate arithmetic probably passes, and we agree that **the fit (a one-item document level, about ten parameters, clustered bootstrap) decides between branches 2 and 3.** Part 3 is the real computation.

**Adopted from Fable:**
- Sol's near-vacuity and the softened wording in A6.14.4;
- the latent-share sensitivity;
- the resolved-anchor subset (19) beside the stratum, because of the anchor imbalance;
- the one-item-document rule before Part 3;
- the fixed preview definition;
- the deviation note on the script hash.

**Kept from section 1:**
- Kimi K3's sample asymmetry (14 against 4, p 0.03, no pipeline cause), reported with an optional check of the upstream provider;
- m_L = m_s written as a convention, because arms matched on composition band cannot take m_L from β*;
- the stratum's spread as the anchor for round 2's dose spread;
- the S1 scope sentence on the stratum's lower composition.

**Joint next steps:**
1. **Notes before Part 3:** the one-item-document rule; A6.14.4's wording; the resolved-anchor subset beside; the preview definition; brief 25's deviations.
2. **Part 3** with two membership inputs, the fit rate at the actual document counts and the resolved-anchor subset beside. It also covers m_L as a convention with power at m_s and m_s/2, the round-2 spread anchor, and the third-branch note on A6.14.3.
3. **S1**, with the scope sentences.
4. **S2:** Aravind confirms the layout and about $73.
5. **S3.**
6. **Brief 24**, then round 2.
