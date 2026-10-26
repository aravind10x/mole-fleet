# The panel judge at matched honest cost (brief 07l amendment A6; 2026-10-26T20:15Z)

Rule: per unit, the mean over Sonnet 5, GLM 5.3 and Opus 4.8 of the judge's mid-rank percentile within its own honest null (fraction strictly below plus half the fraction equal; above the maximum maps to 1.0); the panel's threshold on its own honest values by the seal's randomised rule at the sealed rates (O_diff 0.10, P_author 0.05 author level), tie seed 20261112. Comparator: the best single interpretable judge's composed recall at its own 10 percent rule, identified after scoring (conservative). Prediction: the panel's conforming composed recall exceeds the comparator's by at least 0.05 with the panel's sham share at or under 0.1.

## v2 (post hoc (the per-judge v2 results were known when A6 was written))

**Prediction held: False** (panel conforming composed recall 0.438 against the best single interpretable judge opus48 0.406; panel sham share 0.078; evaluable True).

| judge / panel | conforming | alarming | sham | rule (O_diff t, p_tie) |
|---|---|---|---|---|
| Sonnet 5 | 0.344 | – | 0.031 | own |
| GLM 5.3 | 0.328 | – | 0.078 | own |
| Kimi K3 (not interpretable) | 0.484 | – | 0.125 | own |
| Opus 4.8 | 0.406 | – | 0.031 | own |
| panel mean-rank (primary) | 0.438 [0.314, 0.567] | 1.000 [0.858, 1.000] | 0.078 [0.026, 0.173] | 0.824, 0.400 |
| panel max_rank | 0.406 [0.285, 0.536] | 1.000 [0.858, 1.000] | 0.031 [0.004, 0.108] | 0.967, 0.733 |
| panel median_rank | 0.422 [0.299, 0.552] | 1.000 [0.858, 1.000] | 0.047 [0.010, 0.131] | 0.852, 0.467 |
| panel panel_with_kimi | 0.484 [0.357, 0.613] | 1.000 [0.858, 1.000] | 0.078 [0.026, 0.173] | 0.810, 0.400 |

P_author under the panel (author rule): conforming lone 0.208, k2 0.292; alarming lone 1.000, k2 1.000; sham lone 0.042, k2 0.042.
Cost of three calls per unit (realised per-unit, USD): {"O_diff": {"sonnet": 0.005799, "glm": 0.00035, "opus48": 0.029369, "sum": 0.035518}, "P_author": {"sonnet": 0.003453, "glm": 0.000227, "opus48": 0.013877, "sum": 0.017557}}.

## v3 (pre-registered (t1v3-plan.md section 7))

**Prediction held: False** (panel routine_redraw composed recall 0.312 against the best single interpretable judge opus48 0.469; panel sham_redraw share 0.125; evaluable True).

| judge / panel | middle | routine_redraw | sham_redraw | rule (O_diff t, p_tie) |
|---|---|---|---|---|
| Sonnet 5 (not interpretable) | 0.344 | 0.344 | 0.125 | own |
| GLM 5.3 (not interpretable) | 0.422 | 0.250 | 0.188 | own |
| Opus 4.8 | 0.594 | 0.469 | 0.000 | own |
| panel mean-rank (primary) | 0.531 [0.402, 0.657] | 0.312 [0.161, 0.500] | 0.125 [0.035, 0.290] | 0.824, 0.400 |
| panel max_rank | 0.594 [0.464, 0.715] | 0.438 [0.264, 0.623] | 0.125 [0.035, 0.290] | 0.967, 0.733 |
| panel median_rank | 0.547 [0.417, 0.672] | 0.344 [0.186, 0.532] | 0.094 [0.020, 0.250] | 0.852, 0.467 |

P_author under the panel (author rule): middle lone 0.333, k2 0.208; routine_redraw lone 0.333, k2 0.167; sham_redraw lone 0.000, k2 0.000.
Middle arm beside: panel 0.531 against the best single ('opus48', 0.5938); panel middle − routine contrasts {"P_author_lone_recall": {"difference": 0.0, "ci95": [-0.3333, 0.2917]}, "P_author_k2_recall": {"difference": 0.0417, "ci95": [-0.25, 0.2917]}, "P_author_k3_recall": {"difference": 0.125, "ci95": [0.0, 0.3125]}, "O_diff_composed_share": {"difference": 0.2188, "ci95": [0.0156, 0.4219]}, "O_diff_k2_share": {"difference": 0.125, "ci95": [-0.2083, 0.4583]}, "per_piece_flip_rate": {"difference": -0.0523, "ci95": [-0.1635, 0.0345]}}.
Cost of three calls per unit (realised per-unit, USD): {"O_diff": {"sonnet": 0.005978, "glm": 0.000356, "opus48": 0.033367, "sum": 0.039701}, "P_author": {"sonnet": 0.003376, "glm": 0.000231, "opus48": 0.012989, "sum": 0.016596}}.

Paper claim: {"a_panel_at_matched_cost": false, "basis": "the v3 prediction (routine_redraw against sham_redraw); the middle arm reported beside"}.
