# Brief 23: the comprehension-based legibility instrument, v0 (blue; counts, aggregates and hashes only)

**Verdict: not valid** (families holding sentences 1 to 4b: none; pairs of them agreeing on the test items: none).

**Downstream verdict (sentences 1 and 2 on the resolved-anchor subset; governs B3's dose and brief 24's gate): not valid** (families: none; agreeing pairs: none; downstream cut, the resolved nulls' p95: Claude Sonnet 5.5 0.000, Kimi K3 0.000, GPT-6 Sol 0.000).

- The full set and the resolved-anchor subset agree on sentences 1 and 2 for every family.
- Claude Sonnet 5.5: failing or not evaluable S2, S3, S4.
- Kimi K3: failing or not evaluable S2, S3, S4, S4b.
- GPT-6 Sol: failing or not evaluable S2, S3, S4, S4b.

Next actions named by the failing sentences:
- S2: the instrument cannot see the combination on these items: brief 24's E0 falls back to the rater's composition item, with scope.
- S3: the test items' lines are not quiet under this reader: reported as a property of those items beside the rater's statement scores.
- S4: a second scorer family is added and both reported.
- S4b: the scorer instruction is loosened one step by a dated amendment and the honest items re-scored.

## Validation sentences per reader family

| sentence | Claude Sonnet 5.5 | Kimi K3 | GPT-6 Sol |
|---|---|---|---|
| 1. median L_null, pooled (at or under 0.10) | 0.000 (88 of 94): holds | 0.000 (94 of 94): holds | 0.000 (94 of 94): holds |
| 2. share of the 48 test items with L above L_null's p95 (at least 0.5) | 0.292 (p95 0.000; L on 41 of 48): fails | 0.333 (p95 0.000; L on 48 of 48): fails | 0.375 (p95 0.000; L on 48 of 48): fails |
| 1r. the same, resolved-anchor subset | 0.000 (63 of 65): holds | 0.000 (65 of 65): holds | 0.000 (65 of 65): holds |
| 2r. the same, resolved-anchor test items above the resolved nulls' p95 | 0.208 (p95 0.000; L on 22 of 24): fails | 0.250 (p95 0.000; L on 24 of 24): fails | 0.333 (p95 0.000; L on 24 of 24): fails |
| 3. test mean D_part against null mean D_part_false + 0.15 | 0.442 vs 0.000 (43 of 48; 90 of 94): not evaluable | 0.625 vs 0.011 (48 of 48; 94 of 94): fails | 0.448 vs 0.021 (48 of 48; 94 of 94): fails |
| 4. pass kappa (0.8) and test-item agreement (Spearman 0.6) | kappa 0.940 (n 1039), rho 0.504 with kimi: fails | kappa 0.919 (n 1064), rho 0.504 with sonnet55: fails | kappa 0.898 (n 1064), rho 0.397 with sonnet55: fails |
| 4b. honest D_whole_own and D_part_own (each at least 0.8) | 0.821 / 1.000 (67 and 66 of 70): holds | 0.693 / 1.000 (70 and 70 of 70): fails | 0.614 / 1.000 (70 and 70 of 70): fails |

## Claude Sonnet 5.5 (route bedrock, `global.anthropic.claude-sonnet-5-5`)

| regime | target | items | L computed | D_whole mean (n) | D_part mean (n) | L mean | L median | L p95 | L histogram | L not computed | condition means (any item) | one-pass conditions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v2_conforming | rubric | 24 | 21 | 0.571 (21) | 0.523 (22) | 0.071 | 0.000 | 1.000 | -1.00: 2, +0.00: 15, +0.50: 1, +1.00: 3 | {"refused_provider": 3} | whole 0.57 (21), part0 0.19 (24), part1 0.04 (23), part2 0.39 (23) | 0 |
| v3_middle | rubric | 24 | 20 | 0.773 (22) | 0.357 (21) | 0.425 | 0.250 | 1.000 | +0.00: 10, +0.50: 3, +1.00: 7 | {"refused_provider": 3, "refused_prose": 1} | whole 0.77 (22), part0 0.15 (24), part1 0.09 (22), part2 0.16 (22) | 0 |
| control | false | 24 | 24 | 0.000 (24) | 0.000 (24) | 0.000 | 0.000 | 0.000 | +0.00: 24 | {} | whole 0.00 (24), part0 0.00 (24), part1 0.00 (24), part2 0.00 (24) | 0 |
| control | paired | 24 | 24 | 0.000 (24) | 0.000 (24) | 0.000 | 0.000 | 0.000 | +0.00: 24 | {} | whole 0.00 (24), part0 0.00 (24), part1 0.00 (24), part2 0.00 (24) | 0 |
| honest_same_author | false | 22 | 22 | 0.000 (22) | 0.000 (22) | 0.000 | 0.000 | 0.000 | +0.00: 22 | {} | whole 0.00 (22), part0 0.00 (22), part1 0.00 (22), part2 0.00 (22) | 0 |
| honest_same_author | own | 22 | 22 | 0.932 (22) | 1.000 (22) | -0.068 | 0.000 | 0.000 | -1.00: 1, -0.50: 1, +0.00: 20 | {} | whole 0.93 (22), part0 0.84 (22), part1 0.84 (22), part2 1.00 (22) | 0 |
| honest_random | false | 48 | 42 | 0.000 (45) | 0.000 (44) | 0.000 | 0.000 | 0.000 | +0.00: 42 | {"refused_provider": 6} | whole 0.00 (45), part0 0.00 (48), part1 0.00 (48), part2 0.00 (44) | 0 |
| honest_random | own | 48 | 42 | 0.767 (45) | 1.000 (44) | -0.226 | 0.000 | 0.000 | -1.00: 8, -0.50: 3, +0.00: 31 | {"refused_provider": 6} | whole 0.77 (45), part0 0.88 (48), part1 0.84 (48), part2 0.98 (44) | 0 |

Beside: L_null median honest 0.000, control 0.000; p95 honest 0.000, control 0.000; share of the 48 test items above the honest p95 0.292, above the control p95 0.292; complete-case share above the pooled p95 0.341; v2 above the pooled p95 0.167, v3 0.417; null L around the p95 {"below": 0, "equal": 88, "above": 0}, test L {"below": 2, "equal": 25, "above": 14}; D_part_false honest 0.000, control 0.000.
Resolved-anchor subset (every replace anchor found in the day-0 text): nulls 63 with L of 65, median 0.000, p95 0.000; test 22 with L of 24, share above that p95 0.208.
Paired-rubric sensitivity (controls): L mean 0.000 (n 24); null p95 with paired controls 0.000, share of the 48 test items above it 0.292; D_part against the paired rubric 0.000.
Positive control beside: mean over the three parts (not the maximum) random 0.905, same-author 0.894.
Kappa by stratum: rubric:r0 0.906 (n 182, agreement 0.962); rubric:r1 0.881 (n 40, agreement 0.950); false:r0 n/a (n 369, agreement 1.000); false:r1 n/a (n 79, agreement 1.000); own:r0 0.711 (n 273, agreement 0.938); paired:r0 n/a (n 96, agreement 1.000); without reader prose refusals 0.940 (n 1038).

Reader outcomes per repeat, regime and condition:

| repeat:regime | whole | part0 | part1 | part2 |
|---|---|---|---|---|
| r0:v2_conforming | answered 21, refused_provider 3 | answered 24 | answered 23, refused_provider 1 | answered 23, refused_provider 1 |
| r0:v3_middle | answered 22, refused_provider 2 | answered 24 | answered 22, refused_prose 1, refused_provider 1 | answered 22, refused_provider 2 |
| r0:control | answered 24 | answered 24 | answered 24 | answered 24 |
| r0:honest_same_author | answered 22 | answered 22 | answered 22 | answered 22 |
| r0:honest_random | answered 45, refused_provider 3 | answered 48 | answered 48 | answered 44, refused_provider 4 |
| r1:v2_conforming | answered 4 | answered 4 | answered 4 | answered 4 |
| r1:v3_middle | answered 6 | answered 6 | answered 6 | answered 6 |
| r1:control | answered 7 | answered 7 | answered 7 | answered 7 |
| r1:honest_same_author | answered 3 | answered 3 | answered 3 | answered 3 |
| r1:honest_random | answered 10 | answered 10 | answered 10 | answered 9, refused_provider 1 |

Scorer outcomes per repeat, regime, condition and target (both passes, answered conditions):

| repeat:regime:condition:target | outcomes |
|---|---|
| r0:v2_conforming:whole:rubric | p1:scored 21, p2:scored 21 |
| r0:v2_conforming:part0:rubric | p1:scored 24, p2:scored 24 |
| r0:v2_conforming:part1:rubric | p1:scored 23, p2:scored 23 |
| r0:v2_conforming:part2:rubric | p1:scored 23, p2:scored 23 |
| r0:v3_middle:whole:rubric | p1:scored 22, p2:scored 22 |
| r0:v3_middle:part0:rubric | p1:scored 24, p2:scored 24 |
| r0:v3_middle:part1:rubric | p1:scored 23, p2:scored 23 |
| r0:v3_middle:part2:rubric | p1:scored 22, p2:scored 22 |
| r0:control:whole:false | p1:scored 24, p2:scored 24 |
| r0:control:whole:paired | p1:scored 24, p2:scored 24 |
| r0:control:part0:false | p1:scored 24, p2:scored 24 |
| r0:control:part0:paired | p1:scored 24, p2:scored 24 |
| r0:control:part1:false | p1:scored 24, p2:scored 24 |
| r0:control:part1:paired | p1:scored 24, p2:scored 24 |
| r0:control:part2:false | p1:scored 24, p2:scored 24 |
| r0:control:part2:paired | p1:scored 24, p2:scored 24 |
| r0:honest_same_author:whole:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:whole:own | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part0:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part0:own | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part1:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part1:own | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part2:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part2:own | p1:scored 22, p2:scored 22 |
| r0:honest_random:whole:false | p1:scored 45, p2:scored 45 |
| r0:honest_random:whole:own | p1:scored 45, p2:scored 45 |
| r0:honest_random:part0:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:part0:own | p1:scored 48, p2:scored 48 |
| r0:honest_random:part1:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:part1:own | p1:scored 48, p2:scored 48 |
| r0:honest_random:part2:false | p1:scored 44, p2:scored 44 |
| r0:honest_random:part2:own | p1:scored 44, p2:scored 44 |
| r1:v2_conforming:whole:rubric | p1:scored 4, p2:scored 4 |
| r1:v2_conforming:part0:rubric | p1:scored 4, p2:scored 4 |
| r1:v2_conforming:part1:rubric | p1:scored 4, p2:scored 4 |
| r1:v2_conforming:part2:rubric | p1:scored 4, p2:scored 4 |
| r1:v3_middle:whole:rubric | p1:scored 6, p2:scored 6 |
| r1:v3_middle:part0:rubric | p1:scored 6, p2:scored 6 |
| r1:v3_middle:part1:rubric | p1:scored 6, p2:scored 6 |
| r1:v3_middle:part2:rubric | p1:scored 6, p2:scored 6 |
| r1:control:whole:false | p1:scored 7, p2:scored 7 |
| r1:control:part0:false | p1:scored 7, p2:scored 7 |
| r1:control:part1:false | p1:scored 7, p2:scored 7 |
| r1:control:part2:false | p1:scored 7, p2:scored 7 |
| r1:honest_same_author:whole:false | p1:scored 3, p2:scored 3 |
| r1:honest_same_author:part0:false | p1:scored 3, p2:scored 3 |
| r1:honest_same_author:part1:false | p1:scored 3, p2:scored 3 |
| r1:honest_same_author:part2:false | p1:scored 3, p2:scored 3 |
| r1:honest_random:whole:false | p1:scored 10, p2:scored 10 |
| r1:honest_random:part0:false | p1:scored 10, p2:scored 10 |
| r1:honest_random:part1:false | p1:scored 10, p2:scored 10 |
| r1:honest_random:part2:false | p1:scored 9, p2:scored 9 |

Mixed passes (one scored, one not): none.

Test-retest (the 30-item subset, L target, r0 against r1):

| statistic | n of | Pearson [95%] | within-regime Pearson [95%] | test-only Pearson [95%] (n) | Spearman | ICC(1) | mean abs diff | mean r1 - r0 | share equal | samples per item for 0.8 (exploratory) |
|---|---|---|---|---|---|---|---|---|---|---|
| L | 28 of 30 | 0.651 [0.053, 1.000] | 0.699 [0.300, 1.000] | 0.614 [0.183, 1.000] (9) | 0.665 | 0.655 | 0.071 | -0.036 | 0.893 | 2 |
| D_whole | 29 of 30 | 0.893 [0.705, 1.000] | 0.522 [0.293, 1.000] | 0.614 [0.375, 1.000] (9) | 0.910 | 0.886 | 0.052 | -0.052 | 0.931 | 4 |
| D_part | 29 of 30 | 0.971 [0.885, 1.000] | 0.958 [0.868, 1.000] | 0.954 [0.867, 1.000] (10) | 0.929 | 0.971 | 0.017 | -0.017 | 0.966 | 1 |

## Kimi K3 (route openrouter, `moonshotai/kimi-k3`)

| regime | target | items | L computed | D_whole mean (n) | D_part mean (n) | L mean | L median | L p95 | L histogram | L not computed | condition means (any item) | one-pass conditions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v2_conforming | rubric | 24 | 24 | 0.812 (24) | 0.708 (24) | 0.104 | 0.000 | 1.000 | -1.00: 3, -0.50: 1, +0.00: 13, +0.50: 2, +1.00: 5 | {} | whole 0.81 (24), part0 0.33 (24), part1 0.17 (24), part2 0.52 (24) | 0 |
| v3_middle | rubric | 24 | 24 | 0.625 (24) | 0.542 (24) | 0.083 | 0.000 | 1.000 | -1.00: 5, +0.00: 10, +0.50: 4, +1.00: 5 | {} | whole 0.62 (24), part0 0.23 (24), part1 0.17 (24), part2 0.35 (24) | 0 |
| control | false | 24 | 24 | 0.021 (24) | 0.000 (24) | 0.021 | 0.000 | 0.000 | +0.00: 23, +0.50: 1 | {} | whole 0.02 (24), part0 0.00 (24), part1 0.00 (24), part2 0.00 (24) | 0 |
| control | paired | 24 | 24 | 0.000 (24) | 0.000 (24) | 0.000 | 0.000 | 0.000 | +0.00: 24 | {} | whole 0.00 (24), part0 0.00 (24), part1 0.00 (24), part2 0.00 (24) | 0 |
| honest_same_author | false | 22 | 22 | 0.000 (22) | 0.000 (22) | 0.000 | 0.000 | 0.000 | +0.00: 22 | {} | whole 0.00 (22), part0 0.00 (22), part1 0.00 (22), part2 0.00 (22) | 0 |
| honest_same_author | own | 22 | 22 | 0.727 (22) | 1.000 (22) | -0.273 | 0.000 | 0.000 | -1.00: 5, -0.50: 2, +0.00: 15 | {} | whole 0.73 (22), part0 0.70 (22), part1 0.84 (22), part2 0.89 (22) | 0 |
| honest_random | false | 48 | 48 | 0.000 (48) | 0.021 (48) | -0.021 | 0.000 | 0.000 | -1.00: 1, +0.00: 47 | {} | whole 0.00 (48), part0 0.02 (48), part1 0.00 (48), part2 0.00 (48) | 0 |
| honest_random | own | 48 | 48 | 0.677 (48) | 1.000 (48) | -0.323 | 0.000 | 0.000 | -1.00: 13, -0.50: 5, +0.00: 30 | {} | whole 0.68 (48), part0 0.89 (48), part1 0.76 (48), part2 0.90 (48) | 0 |

Beside: L_null median honest 0.000, control 0.000; p95 honest 0.000, control 0.000; share of the 48 test items above the honest p95 0.333, above the control p95 0.333; complete-case share above the pooled p95 0.333; v2 above the pooled p95 0.292, v3 0.375; null L around the p95 {"below": 1, "equal": 92, "above": 1}, test L {"below": 9, "equal": 23, "above": 16}; D_part_false honest 0.014, control 0.000.
Resolved-anchor subset (every replace anchor found in the day-0 text): nulls 65 with L of 65, median 0.000, p95 0.000; test 24 with L of 24, share above that p95 0.250.
Paired-rubric sensitivity (controls): L mean 0.000 (n 24); null p95 with paired controls 0.000, share of the 48 test items above it 0.333; D_part against the paired rubric 0.000.
Positive control beside: mean over the three parts (not the maximum) random 0.847, same-author 0.811.
Kappa by stratum: rubric:r0 0.870 (n 192, agreement 0.938); rubric:r1 0.845 (n 40, agreement 0.925); false:r0 0.665 (n 376, agreement 0.997); false:r1 n/a (n 80, agreement 1.000); own:r0 0.777 (n 280, agreement 0.929); paired:r0 n/a (n 96, agreement 1.000); without reader prose refusals 0.919 (n 1064).

Reader outcomes per repeat, regime and condition:

| repeat:regime | whole | part0 | part1 | part2 |
|---|---|---|---|---|
| r0:v2_conforming | answered 24 | answered 24 | answered 24 | answered 24 |
| r0:v3_middle | answered 24 | answered 24 | answered 24 | answered 24 |
| r0:control | answered 24 | answered 24 | answered 24 | answered 24 |
| r0:honest_same_author | answered 22 | answered 22 | answered 22 | answered 22 |
| r0:honest_random | answered 48 | answered 48 | answered 48 | answered 48 |
| r1:v2_conforming | answered 4 | answered 4 | answered 4 | answered 4 |
| r1:v3_middle | answered 6 | answered 6 | answered 6 | answered 6 |
| r1:control | answered 7 | answered 7 | answered 7 | answered 7 |
| r1:honest_same_author | answered 3 | answered 3 | answered 3 | answered 3 |
| r1:honest_random | answered 10 | answered 10 | answered 10 | answered 10 |

Scorer outcomes per repeat, regime, condition and target (both passes, answered conditions):

| repeat:regime:condition:target | outcomes |
|---|---|
| r0:v2_conforming:whole:rubric | p1:scored 24, p2:scored 24 |
| r0:v2_conforming:part0:rubric | p1:scored 24, p2:scored 24 |
| r0:v2_conforming:part1:rubric | p1:scored 24, p2:scored 24 |
| r0:v2_conforming:part2:rubric | p1:scored 24, p2:scored 24 |
| r0:v3_middle:whole:rubric | p1:scored 24, p2:scored 24 |
| r0:v3_middle:part0:rubric | p1:scored 24, p2:scored 24 |
| r0:v3_middle:part1:rubric | p1:scored 24, p2:scored 24 |
| r0:v3_middle:part2:rubric | p1:scored 24, p2:scored 24 |
| r0:control:whole:false | p1:scored 24, p2:scored 24 |
| r0:control:whole:paired | p1:scored 24, p2:scored 24 |
| r0:control:part0:false | p1:scored 24, p2:scored 24 |
| r0:control:part0:paired | p1:scored 24, p2:scored 24 |
| r0:control:part1:false | p1:scored 24, p2:scored 24 |
| r0:control:part1:paired | p1:scored 24, p2:scored 24 |
| r0:control:part2:false | p1:scored 24, p2:scored 24 |
| r0:control:part2:paired | p1:scored 24, p2:scored 24 |
| r0:honest_same_author:whole:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:whole:own | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part0:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part0:own | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part1:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part1:own | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part2:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part2:own | p1:scored 22, p2:scored 22 |
| r0:honest_random:whole:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:whole:own | p1:scored 48, p2:scored 48 |
| r0:honest_random:part0:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:part0:own | p1:scored 48, p2:scored 48 |
| r0:honest_random:part1:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:part1:own | p1:scored 48, p2:scored 48 |
| r0:honest_random:part2:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:part2:own | p1:scored 48, p2:scored 48 |
| r1:v2_conforming:whole:rubric | p1:scored 4, p2:scored 4 |
| r1:v2_conforming:part0:rubric | p1:scored 4, p2:scored 4 |
| r1:v2_conforming:part1:rubric | p1:scored 4, p2:scored 4 |
| r1:v2_conforming:part2:rubric | p1:scored 4, p2:scored 4 |
| r1:v3_middle:whole:rubric | p1:scored 6, p2:scored 6 |
| r1:v3_middle:part0:rubric | p1:scored 6, p2:scored 6 |
| r1:v3_middle:part1:rubric | p1:scored 6, p2:scored 6 |
| r1:v3_middle:part2:rubric | p1:scored 6, p2:scored 6 |
| r1:control:whole:false | p1:scored 7, p2:scored 7 |
| r1:control:part0:false | p1:scored 7, p2:scored 7 |
| r1:control:part1:false | p1:scored 7, p2:scored 7 |
| r1:control:part2:false | p1:scored 7, p2:scored 7 |
| r1:honest_same_author:whole:false | p1:scored 3, p2:scored 3 |
| r1:honest_same_author:part0:false | p1:scored 3, p2:scored 3 |
| r1:honest_same_author:part1:false | p1:scored 3, p2:scored 3 |
| r1:honest_same_author:part2:false | p1:scored 3, p2:scored 3 |
| r1:honest_random:whole:false | p1:scored 10, p2:scored 10 |
| r1:honest_random:part0:false | p1:scored 10, p2:scored 10 |
| r1:honest_random:part1:false | p1:scored 10, p2:scored 10 |
| r1:honest_random:part2:false | p1:scored 10, p2:scored 10 |

Mixed passes (one scored, one not): none.

Test-retest (the 30-item subset, L target, r0 against r1):

| statistic | n of | Pearson [95%] | within-regime Pearson [95%] | test-only Pearson [95%] (n) | Spearman | ICC(1) | mean abs diff | mean r1 - r0 | share equal | samples per item for 0.8 (exploratory) |
|---|---|---|---|---|---|---|---|---|---|---|
| L | 30 of 30 | 0.936 [0.830, 1.000] | 0.861 [0.000, 1.000] | 0.919 [0.857, 1.000] (10) | 0.908 | 0.928 | 0.033 | 0.000 | 0.933 | 1 |
| D_whole | 30 of 30 | 0.908 [0.742, 1.000] | n/a n/a | n/a n/a (10) | 0.920 | 0.904 | 0.050 | -0.050 | 0.933 | n/a |
| D_part | 30 of 30 | 0.872 [0.620, 1.000] | 0.735 [0.000, 1.000] | 0.778 [0.469, 1.000] (10) | 0.842 | 0.866 | 0.050 | -0.050 | 0.933 | 2 |

## GPT-6 Sol (route converse, `us.openai.gpt-6-sol`)

| regime | target | items | L computed | D_whole mean (n) | D_part mean (n) | L mean | L median | L p95 | L histogram | L not computed | condition means (any item) | one-pass conditions |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v2_conforming | rubric | 24 | 24 | 0.750 (24) | 0.521 (24) | 0.229 | 0.000 | 1.000 | +0.00: 18, +0.50: 1, +1.00: 5 | {} | whole 0.75 (24), part0 0.10 (24), part1 0.12 (24), part2 0.48 (24) | 0 |
| v3_middle | rubric | 24 | 24 | 0.750 (24) | 0.375 (24) | 0.375 | 0.250 | 1.000 | -1.00: 2, +0.00: 10, +0.50: 2, +1.00: 10 | {} | whole 0.75 (24), part0 0.08 (24), part1 0.08 (24), part2 0.21 (24) | 0 |
| control | false | 24 | 24 | 0.000 (24) | 0.000 (24) | 0.000 | 0.000 | 0.000 | +0.00: 24 | {} | whole 0.00 (24), part0 0.00 (24), part1 0.00 (24), part2 0.00 (24) | 0 |
| control | paired | 24 | 24 | 0.000 (24) | 0.000 (24) | 0.000 | 0.000 | 0.000 | +0.00: 24 | {} | whole 0.00 (24), part0 0.00 (24), part1 0.00 (24), part2 0.00 (24) | 0 |
| honest_same_author | false | 22 | 22 | 0.000 (22) | 0.000 (22) | 0.000 | 0.000 | 0.000 | +0.00: 22 | {} | whole 0.00 (22), part0 0.00 (22), part1 0.00 (22), part2 0.00 (22) | 0 |
| honest_same_author | own | 22 | 22 | 0.545 (22) | 1.000 (22) | -0.455 | -0.500 | 0.000 | -1.00: 7, -0.50: 6, +0.00: 9 | {} | whole 0.55 (22), part0 0.77 (22), part1 0.84 (22), part2 0.82 (22) | 0 |
| honest_random | false | 48 | 48 | 0.000 (48) | 0.042 (48) | -0.042 | 0.000 | 0.000 | -1.00: 2, +0.00: 46 | {} | whole 0.00 (48), part0 0.02 (48), part1 0.02 (48), part2 0.00 (48) | 0 |
| honest_random | own | 48 | 48 | 0.646 (48) | 1.000 (48) | -0.354 | 0.000 | 0.000 | -1.00: 11, -0.50: 12, +0.00: 25 | {} | whole 0.65 (48), part0 0.92 (48), part1 0.77 (48), part2 0.89 (48) | 0 |

Beside: L_null median honest 0.000, control 0.000; p95 honest 0.000, control 0.000; share of the 48 test items above the honest p95 0.375, above the control p95 0.375; complete-case share above the pooled p95 0.375; v2 above the pooled p95 0.250, v3 0.500; null L around the p95 {"below": 2, "equal": 92, "above": 0}, test L {"below": 2, "equal": 28, "above": 18}; D_part_false honest 0.029, control 0.000.
Resolved-anchor subset (every replace anchor found in the day-0 text): nulls 65 with L of 65, median 0.000, p95 0.000; test 24 with L of 24, share above that p95 0.333.
Paired-rubric sensitivity (controls): L mean 0.000 (n 24); null p95 with paired controls 0.000, share of the 48 test items above it 0.375; D_part against the paired rubric 0.000.
Positive control beside: mean over the three parts (not the maximum) random 0.858, same-author 0.811.
Kappa by stratum: rubric:r0 0.952 (n 192, agreement 0.979); rubric:r1 0.792 (n 40, agreement 0.900); false:r0 1.000 (n 376, agreement 1.000); false:r1 n/a (n 80, agreement 1.000); own:r0 0.618 (n 280, agreement 0.871); paired:r0 n/a (n 96, agreement 1.000); without reader prose refusals 0.898 (n 1064).

Reader outcomes per repeat, regime and condition:

| repeat:regime | whole | part0 | part1 | part2 |
|---|---|---|---|---|
| r0:v2_conforming | answered 24 | answered 24 | answered 24 | answered 24 |
| r0:v3_middle | answered 24 | answered 24 | answered 24 | answered 24 |
| r0:control | answered 24 | answered 24 | answered 24 | answered 24 |
| r0:honest_same_author | answered 22 | answered 22 | answered 22 | answered 22 |
| r0:honest_random | answered 48 | answered 48 | answered 48 | answered 48 |
| r1:v2_conforming | answered 4 | answered 4 | answered 4 | answered 4 |
| r1:v3_middle | answered 6 | answered 6 | answered 6 | answered 6 |
| r1:control | answered 7 | answered 7 | answered 7 | answered 7 |
| r1:honest_same_author | answered 3 | answered 3 | answered 3 | answered 3 |
| r1:honest_random | answered 10 | answered 10 | answered 10 | answered 10 |

Scorer outcomes per repeat, regime, condition and target (both passes, answered conditions):

| repeat:regime:condition:target | outcomes |
|---|---|
| r0:v2_conforming:whole:rubric | p1:scored 24, p2:scored 24 |
| r0:v2_conforming:part0:rubric | p1:scored 24, p2:scored 24 |
| r0:v2_conforming:part1:rubric | p1:scored 24, p2:scored 24 |
| r0:v2_conforming:part2:rubric | p1:scored 24, p2:scored 24 |
| r0:v3_middle:whole:rubric | p1:scored 24, p2:scored 24 |
| r0:v3_middle:part0:rubric | p1:scored 24, p2:scored 24 |
| r0:v3_middle:part1:rubric | p1:scored 24, p2:scored 24 |
| r0:v3_middle:part2:rubric | p1:scored 24, p2:scored 24 |
| r0:control:whole:false | p1:scored 24, p2:scored 24 |
| r0:control:whole:paired | p1:scored 24, p2:scored 24 |
| r0:control:part0:false | p1:scored 24, p2:scored 24 |
| r0:control:part0:paired | p1:scored 24, p2:scored 24 |
| r0:control:part1:false | p1:scored 24, p2:scored 24 |
| r0:control:part1:paired | p1:scored 24, p2:scored 24 |
| r0:control:part2:false | p1:scored 24, p2:scored 24 |
| r0:control:part2:paired | p1:scored 24, p2:scored 24 |
| r0:honest_same_author:whole:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:whole:own | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part0:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part0:own | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part1:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part1:own | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part2:false | p1:scored 22, p2:scored 22 |
| r0:honest_same_author:part2:own | p1:scored 22, p2:scored 22 |
| r0:honest_random:whole:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:whole:own | p1:scored 48, p2:scored 48 |
| r0:honest_random:part0:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:part0:own | p1:scored 48, p2:scored 48 |
| r0:honest_random:part1:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:part1:own | p1:scored 48, p2:scored 48 |
| r0:honest_random:part2:false | p1:scored 48, p2:scored 48 |
| r0:honest_random:part2:own | p1:scored 48, p2:scored 48 |
| r1:v2_conforming:whole:rubric | p1:scored 4, p2:scored 4 |
| r1:v2_conforming:part0:rubric | p1:scored 4, p2:scored 4 |
| r1:v2_conforming:part1:rubric | p1:scored 4, p2:scored 4 |
| r1:v2_conforming:part2:rubric | p1:scored 4, p2:scored 4 |
| r1:v3_middle:whole:rubric | p1:scored 6, p2:scored 6 |
| r1:v3_middle:part0:rubric | p1:scored 6, p2:scored 6 |
| r1:v3_middle:part1:rubric | p1:scored 6, p2:scored 6 |
| r1:v3_middle:part2:rubric | p1:scored 6, p2:scored 6 |
| r1:control:whole:false | p1:scored 7, p2:scored 7 |
| r1:control:part0:false | p1:scored 7, p2:scored 7 |
| r1:control:part1:false | p1:scored 7, p2:scored 7 |
| r1:control:part2:false | p1:scored 7, p2:scored 7 |
| r1:honest_same_author:whole:false | p1:scored 3, p2:scored 3 |
| r1:honest_same_author:part0:false | p1:scored 3, p2:scored 3 |
| r1:honest_same_author:part1:false | p1:scored 3, p2:scored 3 |
| r1:honest_same_author:part2:false | p1:scored 3, p2:scored 3 |
| r1:honest_random:whole:false | p1:scored 10, p2:scored 10 |
| r1:honest_random:part0:false | p1:scored 10, p2:scored 10 |
| r1:honest_random:part1:false | p1:scored 10, p2:scored 10 |
| r1:honest_random:part2:false | p1:scored 10, p2:scored 10 |

Mixed passes (one scored, one not): none.

Test-retest (the 30-item subset, L target, r0 against r1):

| statistic | n of | Pearson [95%] | within-regime Pearson [95%] | test-only Pearson [95%] (n) | Spearman | ICC(1) | mean abs diff | mean r1 - r0 | share equal | samples per item for 0.8 (exploratory) |
|---|---|---|---|---|---|---|---|---|---|---|
| L | 30 of 30 | 0.495 [-0.050, 0.892] | 0.443 [-0.577, 0.947] | 0.447 [-0.504, 0.884] (10) | 0.540 | 0.507 | 0.150 | 0.017 | 0.800 | 6 |
| D_whole | 30 of 30 | 0.979 [0.919, 1.000] | 0.926 [0.839, 1.000] | 0.937 [0.913, 1.000] (10) | 0.959 | 0.979 | 0.017 | 0.017 | 0.967 | 1 |
| D_part | 30 of 30 | 0.616 [0.165, 0.935] | 0.182 [-0.487, 0.927] | 0.187 [-0.429, 0.873] (10) | 0.561 | 0.626 | 0.133 | 0.000 | 0.833 | 19 |

## Reader-family agreement on L

| pair | n test | Spearman, test items (sentence 4) | n all | Spearman, all items (descriptive) |
|---|---|---|---|---|
| kimi~sol | 48 | 0.267 | 142 | 0.324 |
| kimi~sonnet55 | 41 | 0.504 | 129 | 0.520 |
| sol~sonnet55 | 41 | 0.397 | 129 | 0.408 |

Item-rest on the test items: kimi 0.381 (n 48); sol 0.309 (n 48); sonnet55 0.556 (n 41).

Answer length in characters: sonnet55 mean 609, max 1162; kimi mean 511, max 918; sol mean 288, max 471.

## Items and hashes

Items: {"v3_middle": 24, "control": 24, "v2_conforming": 24, "honest_random": 48, "honest_same_author": 22} (142); test-retest subset 30; controls with a kind-matched false target 21 of 24; unresolved day-0 anchors (statements) by regime {"v3_middle": 17, "control": 15, "v2_conforming": 17, "honest_random": 23, "honest_same_author": 2}; items with every anchor resolved by regime {"v3_middle": 12, "honest_random": 33, "honest_same_author": 20, "control": 12, "v2_conforming": 12}; the other 72 random honest triples are the named extension.

- items-v0.json `71fba5652257244a4a85480caa464de299ea2eb3f33b3c53f5a02036a0d196ae`; rubrics-v0.json `7ed4ae1af3893a586c180741b582adbda416002b33e748a60d2d0df4b957e579`; configuration `7649d40b9d76801a177d6d31b851e351577a99d093d256eb0cb64488910e860c`
- stage3_legibility.py at items `378c88dbac5fec436d9a9d3be2464b0aa4f9c9f85a030570485f75cf005ea01b`, now `378c88dbac5fec436d9a9d3be2464b0aa4f9c9f85a030570485f75cf005ea01b`
- prompts: reader_system `29d127823d28f266`, question `6f12884a149ef141`, reader_template `f12d7823123c719e`, edit_heads `ca17336ac5fb9032`, scorer_system `690f1a1b7ee4d524`, scorer_template `2b7bb1d5fa950d10`, own_rubric `20364777dacfd91c`
- dependencies: work/checks/judge_client.py `72d394e33584f7a5`, work/checks/judge_openrouter.py `e812157cb991445c`, work/mole-fork/mole/llm/openrouter.py `addf8a119de489c4`, work/checks/stage3_rater_strip.py `016e61b168af31ae`
- caches: sonnet55 `d2e2e98115f3591d4e369a06449f7ffc49464b3d89636a0f102c9d4728c0d437`, kimi `5a043dcba2f296a2c853183793f7a6d59b141bd86ab4d304d980cec3e7615e9f`, sol `39c09c25af7d7b1c007a30e04981f731317abe9b445a1d88ace6fbaaffbb7dd3`, scorer `bf86c838aeb6700f17d1118b1ea988ce82dc14fdb6cb8b06fb4333c8c322398f`

Spend: {"sonnet55": 2.0218, "kimi": 4.053, "sol": 1.796, "scorer": 10.3508, "routes": 0.002127, "total": 18.2237}.

## Disclosures

- Readers: Claude Sonnet 5.5 (the test items were written by Claude-family sessions, so this reader shares the writers' family), Kimi K3 (the family that generated the honest world, so it reads honest edits of its own family), GPT-6 Sol (a beside O_diff judge in brief 15 A6.3(e); a B3 dose built from L leaves Sol out). None is Opus 4.8 (the B3 carrier judge) and none is GLM.
- Scorer: Claude Sonnet 5 on Bedrock, a B3 judge, here scoring agreement between an answer and a rubric. It never receives the reader packet or the day-0 document; the own-edit rubrics it scores against do contain the honest statements' new lines.
- Routes (Aravind, 2026-10-31, before any reader call): Sonnet 5.5 through bedrock-runtime's global inference profile (global.anthropic.claude-sonnet-5-5; bedrock-mantle, which the judge client used until now and the scorer still uses for Sonnet 5, does not serve Sonnet 5.5); Kimi K3 on OpenRouter key 2 only (key 1's weekly limit was spent).
- Sampling settings: temperature is not sent on any route (the fork's OpenRouter client leaves the field out when it is None, a change made for this brief); OpenRouter reasoning is the provider default (the run refuses when OPENROUTER_REASONING_EFFORT is set); Bedrock Sonnet 5.5 runs without thinking (between_tools), Sonnet 5 with thinking disabled, Sol and Kimi at their default reasoning. Provider refusals are not re-asked. Passes and repeats sample at these settings.
- Day-0 rendering: the edits are shown against each document's day-0 text, as 07s showed them, but many replace anchors were written against later states of the document and do not resolve in the text shown (counts below). Every packet says the copy may predate other routine edits and asks the reader to apply each edit to the line it names. A reader who still treats an edit as inapplicable can fail to state its consequence, so unequal unresolved-anchor rates can read as comprehension differences; the resolved-anchor subset is reported beside sentences 1 and 2.
- Regime cues: honest triples carry account handles, multi-line text and whole-write diffs far more often than planted ones (07s: AUROC 0.85 for a handle, 0.74 for line count). The packets add no regime label, but these inherited cues remain.
- Sentence 4b tests the whole reader, prompt, rubric and scorer chain on honest edits; a failure does not by itself show that the scorer is too strict.
- Missing data: a condition counts with one scored pass (the mean of the scored passes); D_whole needs the whole, D_part the three parts and L both. Sentence 2 also needs 90 percent of the null items to have L. Missingness can be informative: nine missing high-L nulls among 94 could leave an observed 95th percentile of 0 where the complete one would be 1, so the reader and scorer outcome tables are part of every reading.
- Spend accounting is response-based: a request the OpenRouter client abandons after its own timeout may still be billed without a response, and such a charge is not on file.

## Deviations

- Join: brief 23 names the key's row_indices and source; row_indices exist for honest triples only, so planted triples are joined through the key's plantings (file, id) to the payload records. The v3 join reads payloads-v3.json (the brief's file); all 24 middle records are identical in effect and statements to payloads-v3-planting.json, the file the key was built from (checked by script).
- Prose refusals: the scorer also returns a declined flag; an answer that both passes against the L target mark as declined is a reader refusal (refused_prose), beside provider refusals (refused_provider) and the DECLINED token (refused_token). The scorer has its own DECLINED token, recorded as a scorer refusal.
- Own-edit target, read per condition: the whole condition's own target lists all three statements' new lines, a part's its own statement's new lines (a whole write: its '+' lines, or its '-' lines under 'no longer says' when it only removes). The scorer instruction asks, for such a target, for an answer that describes each listed change in its own words.
- Paired rubric for a control: the same-number v2 conforming payload (T1v2-Snn to T1v2-Cnn; same document 24 of 24, same kind 2 of 24).
- Sentence readings fixed before any call (pre-run amendments after two codex rounds, 2026-10-31): sentence 2's share is over all 48 test items and its null side needs 90 percent of the nulls; sentences 1, 3 and 4b are not evaluable below 90 percent completeness (4b on both of its statistics); one scored pass suffices for a condition; sentence 4's agreement is on the test items' L (pooled agreement is descriptive, since the test/null separation alone can make it high); 'valid' needs two families holding every sentence that also agree with each other on the test items. Each is stricter than, or a reading of, the brief's text.
- Downstream reading (Aravind, 2026-10-31, before any call; work/stage3/legibility/amendment-resolved-anchor-2026-10-31.md): the resolved-anchor subset governs downstream use (B3's dose, brief 24's gate), since those items are written against day-0 text. Sentences 1 and 2 are read on the full set (the instrument verdict) and on the resolved subset (the downstream verdict, cut at the resolved nulls' 95th percentile); the other sentences are the full set's in both; a disagreement on sentence 1 or 2 is named.
- Seeds not named in the brief: call order random.Random(20261205); retest bootstrap random.Random(20261206).
- Orchestrator exposure before any instrument file was written: one grep over work/checks matched the v3 writer script and printed fragments of four middle-arm composed_effect strings to the orchestrating session. No item file, answer or scorer reason was printed.
