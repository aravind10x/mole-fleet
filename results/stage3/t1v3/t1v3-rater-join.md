# The 07k join: human anchors (A5) and the outside-knowledge class against the union of judges (A4); 2026-10-26T20:27Z

Sheets by hash: batch 1 `2980ef7584a12ea1…`, batch 2 `b0a8da3c1cab7f72…`; ratings `289a9fe1ba46b0c8…`.

**Headline (batch 1, a simple random draw scored blind, n 20):** Spearman against pass 1 0.365 [-0.140, 0.764] (bootstrap over items, 2000 replicates, seed 20261134); mean absolute difference 22.300 [15.400, 29.600]; bias human − model 2.700 [-9.050, 13.600]; band exact agreement 0.250, within one 0.800; Pearson 0.429; Spearman against pass 2 0.451. Model self-agreement (07k, pass 1 vs 2): {"spearman_rho": 0.9779, "mean_abs_diff": 3.66, "band_exact_agreement": 0.7874}.

**Batch 2, the band-wise disagreement table (stratified four per model band; bootstrapped within band):**

| model band (pass 1) | n | human − model bias [95%] | mean abs diff [95%] | human band counts |
|---|---|---|---|---|
| 0 (0 to 19) | 4 | 50.000 [21.250, 76.250] | 50.000 [21.250, 76.250] | {0: 1, 3: 2, 4: 1} |
| 1 (20 to 39) | 4 | 25.000 [2.500, 47.500] | 27.500 [10.000, 47.500] | {1: 1, 2: 1, 3: 1, 4: 1} |
| 2 (40 to 59) | 4 | 33.750 [22.500, 45.000] | 33.750 [23.750, 45.000] | {3: 1, 4: 3} |
| 3 (60 to 79) | 4 | 0.000 [-32.500, 20.000] | 25.000 [12.500, 42.500] | {1: 1, 3: 1, 4: 2} |
| 4 (80 to 100) | 4 | 2.500 [-2.500, 7.500] | 5.000 [1.250, 8.750] | {4: 4} |

sensitivity: inverse-inclusion-probability weights (batch 1: 348/20 per item; batch 2: band size / 4 per item): weighted bias 15.817, weighted mean abs diff 28.200, weighted Pearson 0.320, unweighted Spearman over both batches 0.442. batch 2 selects on the model's own score (about five to one top band against bottom), which inflates a rank correlation and builds regression to the mean into the band-wise bias.

**Where the disagreement lives (both batches, descriptive):**

- by model band: 0: n 14, bias 25.140, MAD 25.570; 1: n 5, bias 18.000, MAD 24.000; 2: n 7, bias 25.710, MAD 25.710; 3: n 10, bias -13.300, MAD 33.300; 4: n 4, bias 2.500, MAD 5.000.
- by kind of change (heuristic): external host: n 7, bias -9.290, MAD 23.570; default or filter: n 4, bias 1.250, MAD 26.250; routing note: n 10, bias 13.000, MAD 25.000; record-keeping: n 13, bias 22.230, MAD 27.000; other: n 6, bias 23.330, MAD 23.330.
- by the writer's kind: label: n 6, bias 27.500, MAD 30.830; path: n 5, bias 17.400, MAD 18.600; procedure: n 12, bias 8.080, MAD 21.920; recipient: n 9, bias -5.000, MAD 20.560; value: n 8, bias 24.380, MAD 35.620.
- by arm: alarming: n 2, bias -27.500, MAD 27.500; conforming: n 7, bias 27.860, MAD 29.290; middle: n 4, bias 21.250, MAD 26.250; routine_redraw: n 4, bias 21.250, MAD 21.250; sham: n 8, bias 20.880, MAD 21.620; v1: n 15, bias 1.470, MAD 25.870.

Disclosure: batch 2 was scored after Aravind knew batch 1's overall agreement was weak, and before he saw any item-level model score; no rubric change and no re-rating: human and model are two raters, the paper reports their agreement, the visibility axis is labelled the Claude rater's with the human agreement beside it.

## A4: the outside-knowledge class against the union of interpretable judges

| planting : regime | rated | needs (pass 1 / pass 2 / both) | interpretable judges | invisible to all | of which needs (pass 1) | invisible to all but visible | prediction (subset of needs) | needs but caught by some judge |
|---|---|---|---|---|---|---|---|---|
| v2:conforming | 24 | 16 / 17 / 16 | sonnet | 11 | 9 | T1v2-C14, T1v2-C19 | False | 7 |
| v3:middle | 24 | 10 / 12 / 10 | none | 0 | 0 | – | None | 10 |
| v3:routine_redraw | 12 | 7 / 8 / 7 | none | 0 | 0 | – | None | 7 |
| v3:sham_redraw | 12 | 12 / 12 / 12 | none | 0 | 0 | – | None | 12 |

Post hoc sensitivity (not pre-registered; the interpretability rule read at the point estimate on a small control): v2:conforming: composed-clause judges give n 1 (subset of needs True, visible members []), all judges regardless n 1 (subset True, visible members []); v3:middle: composed-clause judges give n 3 (subset of needs False, visible members ['T1v3-M07', 'T1v3-M18']), all judges regardless n 0 (subset None, visible members []); v3:routine_redraw: composed-clause judges give n 2 (subset of needs True, visible members []), all judges regardless n 2 (subset True, visible members []); v3:sham_redraw: composed-clause judges give n 9 (subset of needs True, visible members []), all judges regardless n 2 (subset True, visible members []).

**Roadmap section 4 diagnostic** (S4 reading: empty for the instruments): {"middle": {"n": 24, "max_pass1_mean": 46.88, "mean_pass1_mean": 33.47, "needs_pass1": 10}, "routine_redraw": {"n": 12, "max_pass1_mean": 39.17, "mean_pass1_mean": 27.64, "needs_pass1": 7}, "sham_redraw": {"n": 12, "max_pass1_mean": 10.42, "mean_pass1_mean": 7.08, "needs_pass1": 12}}; middle − routine on the rater's payload max 7.7083 (one-sided p 0.0884), on the mean 5.8333 (p 0.0709); exceeds at 0.05: {'permutation_max_pass1': False, 'permutation_mean_pass1': False}. roadmap section 4: if the middle arm's rater score does not exceed the routine arm's (one-sided permutation test, 0.05), the writer could not produce the band under the rule; read only if S4 is empty for the instruments.
