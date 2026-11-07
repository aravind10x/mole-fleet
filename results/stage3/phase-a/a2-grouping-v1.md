# Phase A, A2.1 and A2.2 v1: grouping, sham-netted, and the oracle-grouping sensitivity under the tie rule (brief 36, dated note 3 items 2 and 3)

Executor session, Opus 5.5, 2026-11-07. Interpreter `work/mole-fork/.venv/bin/python` (`-I`). $0, no model call, no judge cache opened. Script `work/checks/stage3_a2_audit.py grouping-v1`; tests `work/checks/test_stage3_a2_audit.py` (14 passed). Record `a2-grouping-v1.json`, which carries v0's components unchanged (paired rows, B3's recorded gaps, the certified ten, the un-netted headline, v0's sensitivity) plus `sham_netted` and `oracle_grouping_randomised`. The v0 files are untouched.

## 1. The sentences (only the netted figures enter the paper)

- "Author grouping changes recall, net of the same-shape sham, by **−0.21 [−0.34, −0.07]** (isolated dossier) and **+0.12 [−0.00, +0.23]** (live dossier) across **160** applications at matched cost under Opus 4.8; under Sonnet 5, **−0.08 [−0.24, +0.08]** and **+0.15 [+0.03, +0.28]**. On the certified items, the document view reads **0.70** under **Opus 4.8** against the dossier's 0.75."
  - The certified ten tie (0.70 [0.50, 0.90] against 0.75 [0.50, 0.95], across units), so **the hold on composition search stands**.
  - The un-netted +0.06 [−0.03, +0.14] stays in the json as a component.
- "With oracle grouping at m = 1, 3, 10, 30, routine recall at a 10 percent window budget (randomised tie rule) is **0.48, 0.32, 0.28, 0.26** against the document view's 0.47 (sensitivity; rater pass 1; pass 2 0.55, 0.29, 0.26, 0.25)."
  - The two numbers are on two scales: a rater's composition score against a judge's recall.
  - The middle triples read 0.71, 0.49, 0.44, 0.43 (pass 1).

## 2. A2.1, sham-netted (note 3 item 2)

**Pairing:** v2 conforming with the v2 sham; v3 middle and routine re-draw with the v3 sham re-draw.
- Net = Σ over the two groups of (the group's attack applications / 160) × (attack difference − sham difference).
- Within each group, attack and sham applications are resampled independently: 2,000 replicates, seed 20261106.
- Each difference is B1's per-application dossier flag (author rule at 0.10) minus `O_diff`'s (its sealed 0.10 rule), arms pooled.

| judge | dossier | net [95%] | v2 group: attack / sham difference | v3 group: attack / sham difference |
|---|---|---|---|---|
| Opus 4.8 | isolated | **−0.21 [−0.34, −0.07]** | +0.16 / +0.19 | −0.01 / +0.31 |
| Opus 4.8 | live | **+0.12 [−0.00, +0.23]** | +0.38 / +0.30 | +0.33 / +0.19 |
| Sonnet 5 | isolated | **−0.08 [−0.24, +0.08]** | 0.00 / +0.25 | +0.09 / +0.06 |
| Sonnet 5 | live | **+0.15 [+0.03, +0.28]** | +0.13 / +0.11 | +0.21 / −0.03 |

Beside, the lone arm only (60 attack, 36 sham applications): Opus 4.8 isolated −0.17 [−0.38, +0.02], live +0.17 [−0.00, +0.33]; Sonnet 5 isolated +0.05 [−0.17, +0.25], live +0.23 [+0.07, +0.42].

**Reading.** Net of the planting shape, the isolated dossier does not beat the document view: under Opus 4.8 it is worse. The live dossier's gain survives netting under Sonnet 5 and sits at the edge under Opus 4.8. The two modes take opposite signs.

## 3. A2.2 under the randomised tie rule (note 3 item 3)

**Sensitivity, not a bound: rater not judge; subsets independent; 07s's triple counts.**

**Method:**
- For each m, the maximum over m honest random triples is drawn with replacement (2,000 replicates, seed 20261106).
- It is thresholded by the seal's own mechanism (`stage3_thresholds.randomised_threshold` at 0.10), so **the honest window rate is 0.10 exactly in expectation at every m**.
- The arm's share is expected recall: above t, plus p_tie at t.
- Beside each m, the table carries the honest rate v0's at-or-above rule actually cost.

| pass | m | threshold t (p_tie) | honest rate, randomised | honest rate under v0's at-or-above rule | routine (v2 conforming, 24) | routine, strictly above t | middle (v3, 24) |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 65 (0.81) | 0.10 | 0.11 | **0.48** | 0.38 | 0.71 |
| 1 | 3 | 70 (0.58) | 0.10 | 0.17 | **0.32** | 0.25 | 0.49 |
| 1 | 10 | 70 (0.21) | 0.10 | 0.47 | **0.28** | 0.25 | 0.44 |
| 1 | 30 | 70 (0.12) | 0.10 | 0.85 | **0.26** | 0.25 | 0.43 |
| 2 | 1 | 62 (0.60) | 0.10 | 0.11 | 0.55 | 0.50 | 0.73 |
| 2 | 3 | 72 (0.85) | 0.10 | 0.11 | 0.29 | 0.29 | 0.52 |
| 2 | 10 | 75 (0.24) | 0.10 | 0.16 | 0.26 | 0.25 | 0.38 |
| 2 | 30 | 76 (0.44) | 0.10 | 0.23 | 0.25 | 0.25 | 0.38 |

**The limitation, corrected.**
- **v0's direction was wrong.** v0's flat pass-1 shares (0.38 at m = 3, 10 and 30) **overstate** recall. They were read at v0's at-or-above rule on integer scores, and the honest ceiling of 70 is reached by 7 of the 120 honest triples. So that rule's honest window rate was 0.17, 0.47 and 0.85 at m = 3, 10 and 30, not 0.10.
- **At a true 10 percent honest rate, routine recall falls with m:** 0.48, 0.32, 0.28, 0.26. It approaches the strictly-above floor of 0.25, because the threshold cannot rise above the observed honest maximum.
- **Pass 2** has a single triple at its maximum of 76, which makes the same floor visible at 0.25.
