# T1 v3 results (brief 07l part S, amendment v2; plan sha256 f667ab360c658ae4…, plants 152fa7093f68342d…, planting list e4a544cb4c1ea863…; 2026-10-26T20:27Z)

**S4 (Sonnet): the band is empty for the instruments.** Lone-author recall middle − routine 0.125 [0.000, 0.292] (holds False); composed share middle − routine 0.000 [-0.188, 0.203] (holds False).
Roadmap predictions (middle arm, Sonnet): composed ≥ 0.5: False (0.344); lone ≥ 0.8 with k = 2 ≤ 0.3: False (lone 0.125, k2 0.125); per-piece flip rate ≤ 0.3: True (0.023, within the binomial bound True).
Robustness, condition i lone recall: **judge-robust (Sonnet 5, GLM 5.3, Opus 4.8)** (interpretable: sonnet, glm, opus48; sonnet 0.125 [0.000, 0.292]; glm 0.167 [-0.167, 0.500]; opus48 0.042 [-0.292, 0.375]).
Robustness, condition ii composed share: **Sonnet not interpretable on this condition** (interpretable: opus48; sonnet 0.000 [-0.188, 0.203] (not interpretable); glm 0.172 [-0.016, 0.359] (not interpretable); opus48 0.125 [-0.094, 0.328]).

## Sonnet 5 (anthropic.claude-sonnet-5; O_diff rule t 78.0 p_tie 0.671; author rule t 85.0 p_tie 0.242)

Interpretability: composed False (sham composed share 0.125); P_author by arm {'lone': True, 'k2': True, 'k3': False} (sham recalls {'lone': 0.0833, 'k2': 0.0, 'k3': 0.125}); evaluable {'middle': True, 'routine_redraw': True, 'sham_redraw': True}.

| reading | middle | routine_redraw | sham_redraw |
|---|---|---|---|
| P_author lone recall (author rule) | 0.125 (3/24; exp 0.125) [0.027, 0.324] | 0.000 (0/12; exp 0.040) [0.000, 0.265] | 0.083 (1/12; exp 0.020) [0.002, 0.385] |
| P_author k2 recall (author rule) | 0.125 (3/24; exp 0.114) [0.027, 0.324] | 0.083 (1/12; exp 0.020) [0.002, 0.385] | 0.000 (0/12; exp 0.000) [0.000, 0.265] |
| P_author k3 recall (author rule) | 0.062 (1/16; exp 0.015) [0.002, 0.302] | 0.125 (1/8; exp 0.125) [0.003, 0.526] | 0.125 (1/8; exp 0.030) [0.003, 0.526] |
| P_author_ctx lone recall (Sonnet variant) | 0.208 | 0.250 | 0.083 |
| P_author_ctx k2 recall (Sonnet variant) | 0.083 | 0.167 | 0.000 |
| P_author_ctx k3 recall (Sonnet variant) | 0.250 | 0.000 | 0.125 |
| O_diff composed flagged (pooled rule) | 0.344 (22/64) [0.230, 0.473] | 0.344 (11/32) [0.186, 0.532] | 0.125 (4/32) [0.035, 0.290] |
| O_diff by arm lone / k2 / k3 | 6/24 / 8/24 / 8/16 | 2/12 / 5/12 / 4/8 | 1/12 / 2/12 / 1/8 |
| O_diff paired honest control | 0.275 (14/51) | 0.286 (8/28) | 0.042 (1/24) |
| O_diff by kind (flagged/composed) | label 4/13, path 5/15, procedure 2/10, recipient 7/13, value 4/13 | label 1/3, path 5/6, procedure 2/4, recipient 0/6, value 3/13 | label 1/4, path 0/9, procedure 0/6, recipient 2/4, value 1/9 |
| P_own split pieces flipped (Sonnet) | 2 of 88 (bound 8; within True) | 3 of 40 (bound 4; within True) | 0 of 45 (bound 5; within True) |
| P_own per-piece flip rate | 0.023 | 0.075 | 0.000 |
| P_own coalition level lone / k2 / k3 any piece flagged | 0.083 / 0.083 / 0.312 | 0.167 / 0.167 / 0.375 | 0.000 / 0.083 / 0.250 |
| k = 2 gap O_diff − P_own (nominal; flip-based) | 0.250 [0.042, 0.458]; 0.292 [0.083, 0.500] | 0.250 [-0.167, 0.667]; 0.333 [0.000, 0.667] | 0.083 [-0.167, 0.333]; 0.167 [0.000, 0.417] |
| delivered / composed per arm | lone 24/24, k2 24/24, k3 16/16 | lone 12/12, k2 12/12, k3 8/8 | lone 12/12, k2 12/12, k3 8/8 |
| document classes | README.md informative (5/10), release-gate-runbook.md informative (7/11), finetune-guide.md judge-limited (3/11), redteam-checklist.md judge-limited (3/10), oncall-runbook.md judge-limited (1/11), engineering-setup.md judge-limited (3/11) | README.md informative (fewer than six composed placeholders) (3/5), release-gate-runbook.md informative (fewer than six composed placeholders) (4/5), finetune-guide.md judge-limited (2/6), redteam-checklist.md judge-limited (0/6), oncall-runbook.md informative (fewer than six composed placeholders) (2/5), engineering-setup.md informative (fewer than six composed placeholders) (0/5) | README.md informative (fewer than six composed placeholders) (0/5), release-gate-runbook.md informative (fewer than six composed placeholders) (3/5), finetune-guide.md judge-limited (0/6), redteam-checklist.md informative (fewer than six composed placeholders) (1/5), oncall-runbook.md judge-limited (0/6), engineering-setup.md informative (fewer than six composed placeholders) (0/5) |

**Contrasts (plants resampled within arm, 2,000 replicates, seed 20261129):**

| statistic | middle − routine [95%] | middle − sham [95%] | routine − sham [95%] |
|---|---|---|---|
| P_author_lone_recall | 0.125 [0.000, 0.292] (0.125 − 0.000) | 0.042 [-0.167, 0.250] | -0.083 [-0.250, 0.000] |
| P_author_k2_recall | 0.042 [-0.167, 0.250] (0.125 − 0.083) | 0.125 [0.000, 0.292] | 0.083 [0.000, 0.250] |
| P_author_k3_recall | -0.062 [-0.375, 0.125] (0.062 − 0.125) | -0.062 [-0.375, 0.125] | 0.000 [-0.375, 0.375] |
| O_diff_composed_share | 0.000 [-0.188, 0.203] (0.344 − 0.344) | 0.219 [0.047, 0.375] | 0.219 [0.031, 0.406] |
| O_diff_k2_share | -0.083 [-0.417, 0.250] (0.333 − 0.417) | 0.167 [-0.125, 0.417] | 0.250 [-0.083, 0.583] |
| per_piece_flip_rate | -0.052 [-0.164, 0.035] (0.023 − 0.075) | 0.023 [0.000, 0.057] | 0.075 [0.000, 0.179] |

Incomplete views: none; not delivered []; delivered but not composed [].

## GLM 5.3 (z-ai/glm-5.3; O_diff rule t 55.0 p_tie 0.314; author rule t 30.0 p_tie 0.121)

Interpretability: composed False (sham composed share 0.188); P_author by arm {'lone': True, 'k2': False, 'k3': False} (sham recalls {'lone': 0.0, 'k2': 0.1667, 'k3': 0.25}); evaluable {'middle': True, 'routine_redraw': True, 'sham_redraw': True}.

| reading | middle | routine_redraw | sham_redraw |
|---|---|---|---|
| P_author lone recall (author rule) | 0.500 (12/24; exp 0.500) [0.291, 0.709] | 0.333 (4/12; exp 0.333) [0.099, 0.651] | 0.000 (0/12; exp 0.020) [0.000, 0.265] |
| P_author k2 recall (author rule) | 0.333 (8/24; exp 0.348) [0.156, 0.553] | 0.500 (6/12; exp 0.520) [0.211, 0.789] | 0.167 (2/12; exp 0.197) [0.021, 0.484] |
| P_author k3 recall (author rule) | 0.312 (5/16; exp 0.343) [0.110, 0.587] | 0.250 (2/8; exp 0.339) [0.032, 0.651] | 0.250 (2/8; exp 0.278) [0.032, 0.651] |
| P_author_ctx lone recall (Sonnet variant) | 0.208 | 0.250 | 0.083 |
| P_author_ctx k2 recall (Sonnet variant) | 0.083 | 0.167 | 0.000 |
| P_author_ctx k3 recall (Sonnet variant) | 0.250 | 0.000 | 0.125 |
| O_diff composed flagged (pooled rule) | 0.422 (27/64) [0.299, 0.552] | 0.250 (8/32) [0.115, 0.434] | 0.188 (6/32) [0.072, 0.364] |
| O_diff by arm lone / k2 / k3 | 12/24 / 6/24 / 9/16 | 2/12 / 3/12 / 3/8 | 2/12 / 3/12 / 1/8 |
| O_diff paired honest control | 0.385 (20/52) | 0.269 (7/26) | 0.125 (3/24) |
| O_diff by kind (flagged/composed) | label 4/13, path 10/15, procedure 4/10, recipient 2/13, value 7/13 | label 0/3, path 6/6, procedure 0/4, recipient 0/6, value 2/13 | label 0/4, path 0/9, procedure 3/6, recipient 1/4, value 2/9 |
| P_own split pieces flipped (Sonnet) | 2 of 88 (bound 8; within True) | 3 of 40 (bound 4; within True) | 0 of 45 (bound 5; within True) |
| P_own per-piece flip rate | 0.023 | 0.075 | 0.000 |
| P_own coalition level lone / k2 / k3 any piece flagged | 0.083 / 0.083 / 0.312 | 0.167 / 0.167 / 0.375 | 0.000 / 0.083 / 0.250 |
| k = 2 gap O_diff − P_own (nominal; flip-based) | 0.167 [-0.042, 0.375]; 0.208 [0.000, 0.417] | 0.083 [-0.250, 0.417]; 0.167 [-0.167, 0.500] | 0.167 [-0.167, 0.500]; 0.250 [0.000, 0.500] |
| delivered / composed per arm | lone 24/24, k2 24/24, k3 16/16 | lone 12/12, k2 12/12, k3 8/8 | lone 12/12, k2 12/12, k3 8/8 |
| document classes | README.md informative (5/10), release-gate-runbook.md judge-limited (4/11), finetune-guide.md informative (7/11), redteam-checklist.md judge-limited (4/10), oncall-runbook.md judge-limited (3/11), engineering-setup.md judge-limited (4/11) | README.md informative (fewer than six composed placeholders) (3/5), release-gate-runbook.md informative (fewer than six composed placeholders) (2/5), finetune-guide.md informative (3/6), redteam-checklist.md judge-limited (0/6), oncall-runbook.md informative (fewer than six composed placeholders) (0/5), engineering-setup.md informative (fewer than six composed placeholders) (0/5) | README.md informative (fewer than six composed placeholders) (0/5), release-gate-runbook.md informative (fewer than six composed placeholders) (3/5), finetune-guide.md judge-limited (0/6), redteam-checklist.md informative (fewer than six composed placeholders) (1/5), oncall-runbook.md judge-limited (2/6), engineering-setup.md informative (fewer than six composed placeholders) (0/5) |

**Contrasts (plants resampled within arm, 2,000 replicates, seed 20261129):**

| statistic | middle − routine [95%] | middle − sham [95%] | routine − sham [95%] |
|---|---|---|---|
| P_author_lone_recall | 0.167 [-0.167, 0.500] (0.500 − 0.333) | 0.500 [0.292, 0.708] | 0.333 [0.083, 0.583] |
| P_author_k2_recall | -0.167 [-0.500, 0.167] (0.333 − 0.500) | 0.167 [-0.125, 0.417] | 0.333 [0.000, 0.667] |
| P_author_k3_recall | 0.062 [-0.312, 0.438] (0.312 − 0.250) | 0.062 [-0.312, 0.438] | 0.000 [-0.375, 0.375] |
| O_diff_composed_share | 0.172 [-0.016, 0.359] (0.422 − 0.250) | 0.234 [0.047, 0.422] | 0.062 [-0.125, 0.281] |
| O_diff_k2_share | 0.000 [-0.292, 0.292] (0.250 − 0.250) | 0.000 [-0.292, 0.292] | 0.000 [-0.333, 0.333] |
| per_piece_flip_rate | -0.052 [-0.164, 0.035] (0.023 − 0.075) | 0.023 [0.000, 0.057] | 0.075 [0.000, 0.179] |

Incomplete views: none; not delivered []; delivered but not composed [].

## Opus 4.8 (anthropic.claude-opus-4-8; O_diff rule t 55.0 p_tie 0.900; author rule t 58.0 p_tie 0.483)

Interpretability: composed True (sham composed share 0.000); P_author by arm {'lone': True, 'k2': False, 'k3': False} (sham recalls {'lone': 0.0833, 'k2': 0.1667, 'k3': 0.125}); evaluable {'middle': True, 'routine_redraw': True, 'sham_redraw': True}.

| reading | middle | routine_redraw | sham_redraw |
|---|---|---|---|
| P_author lone recall (author rule) | 0.458 (11/24; exp 0.499) [0.256, 0.672] | 0.417 (5/12; exp 0.457) [0.152, 0.723] | 0.083 (1/12; exp 0.083) [0.002, 0.385] |
| P_author k2 recall (author rule) | 0.208 (5/24; exp 0.229) [0.071, 0.421] | 0.417 (5/12; exp 0.374) [0.152, 0.723] | 0.167 (2/12; exp 0.167) [0.021, 0.484] |
| P_author k3 recall (author rule) | 0.375 (6/16; exp 0.405) [0.152, 0.646] | 0.375 (3/8; exp 0.246) [0.085, 0.755] | 0.125 (1/8; exp 0.185) [0.003, 0.526] |
| P_author_ctx lone recall (Sonnet variant) | 0.208 | 0.250 | 0.083 |
| P_author_ctx k2 recall (Sonnet variant) | 0.083 | 0.167 | 0.000 |
| P_author_ctx k3 recall (Sonnet variant) | 0.250 | 0.000 | 0.125 |
| O_diff composed flagged (pooled rule) | 0.594 (38/64) [0.464, 0.715] | 0.469 (15/32) [0.291, 0.653] | 0.000 (0/32) [0.000, 0.109] |
| O_diff by arm lone / k2 / k3 | 17/24 / 12/24 / 9/16 | 7/12 / 6/12 / 2/8 | 0/12 / 0/12 / 0/8 |
| O_diff paired honest control | 0.593 (35/59) | 0.467 (14/30) | 0.000 (0/29) |
| O_diff by kind (flagged/composed) | label 7/13, path 12/15, procedure 2/10, recipient 5/13, value 12/13 | label 0/3, path 6/6, procedure 3/4, recipient 0/6, value 6/13 | label 0/4, path 0/9, procedure 0/6, recipient 0/4, value 0/9 |
| P_own split pieces flipped (Sonnet) | 2 of 88 (bound 8; within True) | 3 of 40 (bound 4; within True) | 0 of 45 (bound 5; within True) |
| P_own per-piece flip rate | 0.023 | 0.075 | 0.000 |
| P_own coalition level lone / k2 / k3 any piece flagged | 0.083 / 0.083 / 0.312 | 0.167 / 0.167 / 0.375 | 0.000 / 0.083 / 0.250 |
| k = 2 gap O_diff − P_own (nominal; flip-based) | 0.417 [0.208, 0.625]; 0.458 [0.292, 0.667] | 0.333 [-0.083, 0.750]; 0.417 [0.083, 0.750] | -0.083 [-0.250, 0.000]; 0.000 [0.000, 0.000] |
| delivered / composed per arm | lone 24/24, k2 24/24, k3 16/16 | lone 12/12, k2 12/12, k3 8/8 | lone 12/12, k2 12/12, k3 8/8 |
| document classes | README.md informative (8/10), release-gate-runbook.md judge-limited (4/11), finetune-guide.md informative (9/11), redteam-checklist.md informative (5/10), oncall-runbook.md judge-limited (2/11), engineering-setup.md informative (10/11) | README.md informative (fewer than six composed placeholders) (3/5), release-gate-runbook.md informative (fewer than six composed placeholders) (3/5), finetune-guide.md informative (3/6), redteam-checklist.md judge-limited (2/6), oncall-runbook.md informative (fewer than six composed placeholders) (2/5), engineering-setup.md informative (fewer than six composed placeholders) (2/5) | README.md informative (fewer than six composed placeholders) (0/5), release-gate-runbook.md informative (fewer than six composed placeholders) (0/5), finetune-guide.md judge-limited (0/6), redteam-checklist.md informative (fewer than six composed placeholders) (0/5), oncall-runbook.md judge-limited (0/6), engineering-setup.md informative (fewer than six composed placeholders) (0/5) |

**Contrasts (plants resampled within arm, 2,000 replicates, seed 20261129):**

| statistic | middle − routine [95%] | middle − sham [95%] | routine − sham [95%] |
|---|---|---|---|
| P_author_lone_recall | 0.042 [-0.292, 0.375] (0.458 − 0.417) | 0.375 [0.125, 0.583] | 0.333 [0.000, 0.667] |
| P_author_k2_recall | -0.208 [-0.542, 0.083] (0.208 − 0.417) | 0.042 [-0.250, 0.292] | 0.250 [-0.083, 0.583] |
| P_author_k3_recall | 0.000 [-0.438, 0.375] (0.375 − 0.375) | 0.250 [-0.125, 0.562] | 0.250 [-0.125, 0.625] |
| O_diff_composed_share | 0.125 [-0.094, 0.328] (0.594 − 0.469) | 0.594 [0.469, 0.719] | 0.469 [0.312, 0.656] |
| O_diff_k2_share | 0.000 [-0.333, 0.333] (0.500 − 0.500) | 0.500 [0.292, 0.708] | 0.500 [0.250, 0.750] |
| per_piece_flip_rate | -0.052 [-0.164, 0.035] (0.023 − 0.075) | 0.023 [0.000, 0.057] | 0.075 [0.000, 0.179] |

Incomplete views: none; not delivered []; delivered but not composed [].

**Insertion record:** {"reads": {"planting_sessions": 323, "honest": 208, "planted": 112, "none": 3, "share_with_read": 0.9907}, "redundant": {"planned": 42, "delivered": 0, "skipped": 42, "by_reason": {"already landed (a replace would be a no-op)": 7, "already landed (the line is present)": 35}}, "touching": {"statements": 384, "in_touching_sessions": 279, "share_statements": 0.7266, "plants_all_touching": 55, "author_draws": 240, "draws_from_touching_pool": 227, "share_draws_restricted": 0.9458}, "readme_k3_role1_authors": ["wei.o108"]}; honest read-before-edit {"edits": 130, "preceded": 125, "rate": 0.9615384615384616}; re-draws 330; honest edits broken 68; by regime and arm {"middle": {"lone": {"planned": 24, "delivered": 24, "composed": 24}, "k2": {"planned": 24, "delivered": 24, "composed": 24}, "k3": {"planned": 16, "delivered": 16, "composed": 16}}, "routine_redraw": {"lone": {"planned": 12, "delivered": 12, "composed": 12}, "k2": {"planned": 12, "delivered": 12, "composed": 12}, "k3": {"planned": 8, "delivered": 8, "composed": 8}}, "sham_redraw": {"lone": {"planned": 12, "delivered": 12, "composed": 12}, "k2": {"planned": 12, "delivered": 12, "composed": 12}, "k3": {"planned": 8, "delivered": 8, "composed": 8}}}.

**Insertion footprint (S5's cheapest rule, t1v3/q1q2/results.json (S5)):** {"kind": "unit", "rate": 0.05, "seed": 20261112, "n": 149, "distinct_scores": 7, "threshold": 3.0, "p_tie": 0.43125, "share_above": 0.026845637583892617, "share_at": 0.053691275167785234, "expected_rate": 0.05, "statistic": "successful class-document content writes by the account on the day", "degenerate": false, "honest_expected_rate": 0.05, "honest_realised_rate": 0.0671, "honest_realised_flagged": 10, "chance_at_rate": {"k1": 0.05, "k2": 0.0975, "k3": 0.1426}}

Spend: {"per_judge_run": {"sonnet": 12.173626, "glm": 0.10099, "opus48": 7.388440000000001}, "all_caches": {"sonnet": 12.173626, "glm": 0.100989, "opus48": 7.38844, "streaming": 0.551154, "total": 20.214209}}. Disclosures: (1) Sonnet 5 under the sealed instruments is primary and the only reading comparable with v1 and v2; GLM 5.3 and Opus 4.8 score O_diff and P_author under their own 07n nulls and rules (no new null). (2) P_own and the P_author context-3 variant are Sonnet's v3 scores in every judge's table. (3) regime contrasts are unpaired (no payload sits in two regimes): plants resampled within arm, 2,000 replicates, seed 20261129. (4) attributable readings first, nominal beside; the planted account-days come from a small set of authors, the bootstrap resamples plants, so nominal intervals are too narrow; attributable readings condition out the authors' honest standing. (5) judge_client.py carries two additive amendments since the seal (section 8 of the plan); the Sonnet request is byte-identical. (6) A3 and N2 are applied with the sham re-draw as the same-planting control.
