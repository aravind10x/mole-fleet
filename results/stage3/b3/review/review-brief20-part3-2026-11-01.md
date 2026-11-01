# Brief 20 Part 3 (power-simulation-v3c): review and next steps (review session, Opus 5.5, 2026-11-01)

Blue side. Aggregates and per-item numeric values by opaque id only. Section 1 was written before the independent Fable read returned. Section 3 reconciles the two.

## 1. My read, written first

### Verified (`power-simulation-v3c.md` ffd16e23, `.json` 2086e72f; `stratum-v0.json`; `inserter-dry-run-v0.json`)

**Step 0.** The pair-rule net counts are 73, 26, 17 and 20. My own join of the drop list with the stratum file reproduces 26 and 17.

**The switch fires.** The full set's combined P(holds | margin) under the dilution upper bound is 0.63, well above 0.10. It still fires under every sensitivity:

| membership model | P(holds \| margin) |
|---|---|
| upper bound: non-members carry no effect | 0.63 |
| non-members carry a small effect | 0.36 |
| latent share 0.69 | 0.15 |
| latent share 0.46 | 0.48 |
| undiluted | 0.02 |

**The carriers at T2+S2** (worse ICC):

| population | n | P(excluded \| 0) | P(excluded \| margin) | P(LB > 0 \| 0) | other | readable |
|---|---|---|---|---|---|---|
| subset (resolved anchors) | 17 | 0.68 | 0.07 | 0.03 | P(present \| 1.5×) 0.72 | at T2+S2 only (T2+S1: 0.57) |
| stratum | 26 | 0.85 | 0.09 | 0.04 | | at all four layouts |
| strict (two families) | 20 | 0.67 | 0.08 | 0.03 | | descriptive |

**Fit rates are 1.00 because the stratum populations drop form (a)'s document factor** and use the document-stratified bootstrap with small documents pooled (A6.16.2, A6.17.3). This is as recorded, not an anomaly.

**The cascade selects the subset at T2+S2 in every simulated world**, at both fit-rate bars (0.90 and 0.80). Its joint operating characteristics: P(excluded | 0) 0.67, P(excluded | margin) 0.05 (0.03 at latent 0.69), P(LB > 0 | 0) 0.03, P(present | 1.5×) 0.72. The 0.68 is about 3 Monte Carlo SE above 0.60, since the SE at 300 experiments is about 0.027.

**The third branch.** A full-set *present* has P(present | 0) 0.00, within A6.13.1 (iii), but its power is only 0.00 to 0.02 at the margin. Since the cascade never reaches the third branch in simulation, the decision is moot in practice.

**Round 2.** The level contrast needs 12 per arm at m_L = 18.22 and 44 at m_L/2. The slope beside needs 26, 34 or 110 at a composition SD of 17.3, 13.1 or 8.7. The model has no writer or document effect.

**Kimi K3's routing.** The fingerprint join matched 1,682 of 1,682 calls, and the two samples were served by near-identical provider counts. So routing does not explain the 14-against-4 asymmetry. The rise in credit from sample 0 to sample 1 appears *within* providers:

| provider | sample 0 | sample 1 |
|---|---|---|
| InferenceNet | 0.14 | 0.22 |
| Relace | 0.12 | 0.17 |
| Morph (FP8) | 0.08 | 0.26 |
| Wafer | 0.30 | 0.28 |

Providers also differ in how readily they credit a part (Wafer about 0.29 against Relace about 0.15), which adds noise to membership.

**Subset purity (my join).** Of the 17 in the subset, 11 are also in the strict two-family set, where Sol credited no part on either sample. The other 6 passed under Sol's mean rule with a part credited on one sample. Writers in the subset: Sonnet 11, GLM 6.

### Reading and proposals

1. **The recorded cascade should stand: the 17 carry round 1 at T2+S2.** Re-reading the 16 unresolved-anchor items on a rendering where their anchors resolve could recover the 26's power (0.85). It would also be another rule change after the cascade has already selected. Round 1 is not the confirmatory test (A6.15(c)), and the 17 are readable. I would not reopen it (argued). The 26 and the strict 20 stay beside.
2. **The dated note on A6.14.3 (before S1).** A full-set *present* stands if issued (P(present | 0) 0.00 ≤ 0.10). Its power at the margin is at most 0.02, and the cascade did not reach the third branch in any simulated world.
3. **S1's sentences need three disclosures.**
   - The carrier's P(excluded | 0) is 0.67. Under a true max-type null, round 1 says *holds* only about two times in three. A non-*holds* reading at round 1 is therefore weak evidence, and round 2 is the test.
   - The subset is Sonnet-heavy (11 against 6) and lower in composition. 6 of the 17 are admitted on Sol's weak rule. Report the subset ∩ strict count (11) beside, descriptively.
   - Kimi K3's routing and per-provider credit differences, and the within-provider asymmetry between samples, which remains unexplained.
4. **Round 2 and brief 24's target (argued, not tested).** 12 per arm is the gate minimum in a model without writer or document effects. Brief 24 plans for **24 certified and 24 quiet-but-illegible items** as its target: a factor of two for unmodelled variance and for losses at certification and planting (brief 26 dropped 8 of 124). 12 + 12 is the floor that makes round 2 readable, and the m_L/2 figure (44 + 44) is beside. If the round-2 items' composition spread is narrow, the slope reading beside needs far more; it stays descriptive.

### Sequencing (Aravind's question)
- **Brief 24's E0 can be prepared now, in parallel with S1 to S3.** E0 is design and instrument preparation, and touches no B3 outcome. Brief 24's own E7 already allows running sooner "unless Aravind has the capacity sooner". Conditions:
  - no brief 24 session reads any B3 judge output;
  - Kimi K3 is pinned to one provider and precision (A6.17.10 (d));
  - the round-2 design (comparison, m_L, n) stays as Part 3 fixed it.

  Writer rounds could also start before S3: the writers are isolated from B3 results either way, and running earlier only makes the isolation easier. A6.15(b)'s "after S3" placement was about capacity, not rigor. If Aravind wants it, that is a one-line amendment to A6.15(b).
- **S1 can be drafted while brief 27 is in review.** Commit it only after brief 27's reproduction step (E4) passes, since a mismatch re-runs Part 3's Step 0 and changes the counts. S1 must be committed before S2 and S3. The A6.14.3 note precedes S1's commit.

## 2. Fable's independent read (Fable 5.1, high; briefed with files and a barrier list, without section 1)

Summary, not verbatim. Every headline figure was verified against the JSON.

**Flags**
- **The fit-rate bar cannot bind.** Form (a) on the stratum populations has 5 parameters once A6.16.2 dropped the document factor, so a fit rate of 1.00 holds by construction. The 0.90 bar of A6.17.9 (2) cannot bind; the selection rests on A6.13.1 alone. The note must say so.
- **Monte Carlo margins.** For the subset, P(excluded | 0) is 3.1 SE above 0.60, but P(excluded | margin) is only 1.8 SE below 0.10, so the result is sensitive to the seed on bound (ii). The stratum is 12 SE clear.
- **Pooling.** The unpooled bootstrap reads the subset narrower (0.84 / 0.08 / 0.10). The pooled rule is the conservative one and stands.
- **A6.17.9's expectation is reversed.** It expected that "the 19 can carry when the 28 fail"; the simulation shows the 17 readable at one layout and the 26 at four. Correct it.
- **The latent share used gross rather than net counts** (78/28, not 73/26). The effect is immaterial.
- **Scale of m_L.** m_L = 18.22 is on the observed excess scale; the matching shift in the latent effect is 23.6 to 23.9. State it.

**Q2 (which population carries).** The recorded cascade stands. Brief 26 strengthens the case for the 17: readers never saw the nine's lines in context, so their D_part = 0 measures a missing line, not a quiet one. All nine are also in the strict 20, because Sol read the same broken rendering, so the strict set does not test rendering. Subset ∩ strict is 11, the only items that pass both purity checks. Optionally, re-read the 16 unresolved-anchor items on a correct rendering (about $4) as a named sensitivity, never as a carrier change.

**Q3 (Kimi K3).**
- Routing is ruled out: providers were near-identical by sample.
- Credit rose from 0.162 to 0.222 at every FP4 and FP8 provider, while Wafer held at 0.30 against 0.28. This is a sample-level effect of unknown cause.
- The real provider signal: **Wafer (MXFP4) credits 0.287 against FP4's 0.162 (z 2.67).**
- Brief 23's calibration mix was 62% Wafer; brief 25's was 20%. Brief 25's reader was therefore weaker than C1's, and C1's false-quiet figure of 0.005 is probably optimistic.
- Pin brief 24 to the strongest-reading deployment (MXFP4).

**Q4 (round 2 and brief 24).**
- Power at m_L by n per arm: 10 gives 0.57, 12 gives 0.72 / 0.82, 22 gives 0.87, 26 gives 0.94. The implied per-item SD is about 17.6.
- The model has no writer or document variance and assumes certification is perfectly pure.
- Brief 25's yields suggest the illegible arm binds: about 0.09 per candidate, so 12 items need about 130 candidates.
- Proposal: a floor of 12 + 12 and a **target of 26 certified + 12 illegible**. Decide whether round 1's illegible stratum items may fill round 2's comparison arm.

**Q5 (the A6.14.3 note).** The switch values; the carrier (17 at T2+S2) and the step-down; a full-set *present* stands, with its power disclosed (about 0.01 under the zero model, 0.36 at 1.5× under the latent model); the fit bar vacuous; the Monte Carlo margins; pooling; the literal count selects alike; the nine excluded because they were unread, not unplaceable; A6.17.9's expectation corrected; the shares net 26/73 = 0.36 and carrier 17/73 = 0.23.

## 3. Reconciliation (review session)

**Agreed on every verified figure.** The recorded cascade stands: the 17 carry round 1 at T2+S2, with the 26 and the strict 20 beside.

**Adopted from Fable**
- the fit-bar vacuity;
- the Monte Carlo margins, including bound (ii) at 1.8 SE;
- the corrected A6.17.9 expectation;
- the m_L scale statement;
- the point that the strict 20 does not test rendering, with subset ∩ strict (11) as the doubly-pure count;
- the re-read of the 16 as an optional named sensitivity only;
- the Kimi K3 analysis, with the pin set to the strongest-reading deployment (MXFP4) and C1's false-quiet figure called probably optimistic;
- the full content list for the A6.14.3 note.

**Round 2's target, reconciled.** My section-1 target was 24 + 24, argued as a factor of two. Fable's is 26 certified + 12 illegible, computed from the round-2 table: 26 makes the slope readable at the stratum's spread and gives the level contrast 0.94. Adopted:
- **floor 12 + 12** (A6.15(g) runs at the achieved n);
- **target 26 certified and at least 12 illegible, more if the yield allows.**

The power figures are computed; the choice of target is argued.

**Fable's open question, answered: no.** Round 1's illegible stratum items may not fill round 2's comparison arm. A6.15 (b) and (c) say the rounds are never pooled, and those items' round-1 judge readings would be known before round 2 is analysed. Round 2's arms come only from brief 24.

**Kept from section 1**
- S1 discloses that the carrier says *holds* only about two times in three under a true max-type null (P(excluded | 0) 0.67), so a non-*holds* reading in round 1 is weak evidence.
- 6 of the 17 entered on Sol's weak rule.
- The subset is Sonnet-heavy (11 against 6) and lower in composition.
- The sequencing answers.
