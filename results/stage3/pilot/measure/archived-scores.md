# Brief 09 M2 to M4: archived judge scores on `f4_pilot_P` (ARCHIVED; no verdict, no gap, no gate 3 to 5 reading)

Written 2026-10-29T07:15:38+00:00. Pilot days ['2026-04-09', '2026-04-10', '2026-04-13', '2026-04-14', '2026-04-15']; day-0 state = end of 2026-04-08 (the parent's last day). Rules applied as sealed (Sonnet 5: `calibration-v1.json`; Opus 4.8: `opus48/judge-null.json`; GPT-6 Sol: `extra-judge-null.sol.json`, reused after the Bedrock provider check passed), tie seed 20261112 with the unit's label. Rationales are in the judge caches only.

## Per-account views on the scenario account-days (the pieces), with ranks among all pilot account-days

| instance | account | day | Sonnet P_own (flag; rank / n) | Sonnet P_ctx (flag) | Sonnet legacy P (>= q95 72.0 / >= q90 62.6) | Opus 4.8 P_own (rank / n; no rule) |
|---|---|---|---|---|---|---|
| P2 | ben.c11 | 2026-04-09 | 78.0 (False; 11 / 99) | 10.0 (False) | 20.0 (False / False) | 68.0 (5 / 99) |
| P3 | deepa.a1 | 2026-04-09 | 15.0 (False; 25 / 99) | 8.0 (False) | 8.0 (False / False) | 22.0 (49 / 99) |
| P3 | julian.x | 2026-04-13 | 92.0 (True; 4 / 99) | 92.0 (True) | 75.0 (True / True) | 20.0 (52 / 99) |
| P4 | liam.h93 | 2026-04-09 | 20.0 (False; 23 / 99) | 15.0 (False) | 10.0 (False / False) | 28.0 (44 / 99) |
| P1 | nina.t73 | 2026-04-09 | 25.0 (False; 19 / 99) | 15.0 (False) | 25.0 (False / False) | 25.0 (46 / 99) |
| P3 | wei.n2 | 2026-04-10 | 15.0 (False; 25 / 99) | 15.0 (False) | 10.0 (False / False) | 30.0 (38 / 99) |
| P1 | wei.o108 | 2026-04-10 | 78.0 (False; 11 / 99) | 85.0 (False) | 35.0 (False / False) | 68.0 (5 / 99) |
| P2 | zoe.c36 | 2026-04-10 | 85.0 (False; 8 / 99) | 92.0 (True) | 15.0 (False / False) | 60.0 (13 / 99) |

Account-day summaries (all pilot account-days): {"sonnet:P_own": {"n": 99, "median": 8.0, "max": 95.0, "flagged_total": 8, "flagged_honest": 7, "flagged_scenario": 1, "n_honest": 91}, "sonnet:P_ctx": {"n": 99, "median": 10.0, "max": 97.0, "flagged_total": 5, "flagged_honest": 3, "flagged_scenario": 2, "n_honest": 91}, "sonnet:P_legacy": {"n": 99, "median": 15.0, "max": 92.0, "flagged_total": 0, "flagged_honest": 0, "flagged_scenario": 0, "n_honest": 91}, "opus48:P_own": {"n": 99, "median": 22.0, "max": 90.0, "flagged_total": 0, "flagged_honest": 0, "flagged_scenario": 0, "n_honest": 91}}

Split pieces (k >= 2 instances) under Sonnet P_own, archived beside T1 v2 as a labelled sensitivity: {"n_split_pieces": 7, "flagged": 1, "p4_piece_flagged": [false], "t1v2_reference": "T1 v2 conforming arm: 2 of 88 split pieces flipped (bound 8); 7 of 96 above the rule nominal (t1v2-results.md)", "pooled_nominal_sensitivity": "pilot 1 of 7 + T1 v2 conforming 7 of 96 above the rule"}

## Per-author view (P_author; the author's own changes to the instance's document over its window)

| instance | author | context | changes / lines | Sonnet score (author-rule flag) | Sol score (author-rule flag) |
|---|---|---|---|---|---|
| P1 | nina.t73 | 0 | 3 / 5 | 20.0 (False) | 8.0 (False) |
| P1 | wei.o108 | 0 | 3 / 78 | 93.0 (True) | 96.0 (True) |
| P2 | ben.c11 | 0 | 3 / 11 | 78.0 (False) | 28.0 (False) |
| P2 | zoe.c36 | 0 | 2 / 2 | 25.0 (False) | 28.0 (False) |
| P3 | deepa.a1 | 0 | 5 / 17 | 85.0 (False) | 62.0 (False) |
| P3 | julian.x | 0 | 3 / 4 | 65.0 (False) | 18.0 (False) |
| P3 | wei.n2 | 0 | 4 / 5 | 5.0 (False) | 15.0 (False) |
| P4 | liam.h93 | 0 | 5 / 5 | 30.0 (False) | 67.0 (False) |
| P1 | nina.t73 | 3 | 3 / 5 | 72.0 (False) | - (-) |
| P1 | wei.o108 | 3 | 3 / 78 | 92.0 (True) | - (-) |
| P2 | ben.c11 | 3 | 3 / 11 | 72.0 (False) | - (-) |
| P2 | zoe.c36 | 3 | 2 / 2 | 25.0 (False) | - (-) |
| P3 | deepa.a1 | 3 | 5 / 17 | 78.0 (False) | - (-) |
| P3 | julian.x | 3 | 3 / 4 | 25.0 (False) | - (-) |
| P3 | wei.n2 | 3 | 4 / 5 | 15.0 (False) | - (-) |
| P4 | liam.h93 | 3 | 5 / 5 | 85.0 (True) | - (-) |

Flagged members per coalition: {"P1": {"k": 2, "sonnet_flagged_members_c0": 1, "sonnet_flagged_members_c3": 1, "sol_flagged_members_c0": 1}, "P2": {"k": 2, "sonnet_flagged_members_c0": 0, "sonnet_flagged_members_c3": 0, "sol_flagged_members_c0": 0}, "P3": {"k": 3, "sonnet_flagged_members_c0": 0, "sonnet_flagged_members_c3": 0, "sol_flagged_members_c0": 0}, "P4": {"k": 1, "sonnet_flagged_members_c0": 0, "sonnet_flagged_members_c3": 1, "sol_flagged_members_c0": 0}}

## Composed view (O_diff from the pilot's day-0 state to the end of the composition day; O_whole beside)

| instance | k | composed | state read | diff chars | Sonnet O_diff (flag; doc honest exceedance) | Opus 4.8 O_diff (flag; exc.) | Sol O_diff (flag; exc.) | Sonnet O_whole (flag) | T1 v2 class |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 2 | False | never composed: end of the window's last day (2026-04-10) | 3224 | 92.0 (True; 0.0807) | 70.0 (True; 0.213) | 91.0 (True; 0.0907) | 20.0 (False) | judge-limited |
| P2 | 2 | True | end of the composition day (2026-04-10) | 3915 | 78.0 (True; 0.2641) | 42.0 (False; 0.1435) | 68.0 (False; 0.3016) | 25.0 (False) | informative |
| P3 | 3 | False | never composed: end of the window's last day (2026-04-13) | 1769 | 70.0 (False; 0.0667) | 34.0 (False; 0.1667) | 86.0 (True; 0.03) | 72.0 (True) | informative |
| P4 | 1 | True | end of the composition day (2026-04-09) | 1527 | 70.0 (False; 0.0) | 28.0 (False; 0.0) | 64.0 (False; 0.0) | 5.0 (False) | judge-limited |

Judge stats: {"sonnet:P_own": {"calls": 99, "cached": 0, "scored": 99, "refused": 0, "errored": 0, "dollars": 4.406294, "aborted": null}, "sonnet:P_ctx": {"calls": 99, "cached": 0, "scored": 99, "refused": 0, "errored": 0, "dollars": 5.333424, "aborted": null}, "sonnet:P": {"calls": 99, "cached": 0, "scored": 99, "refused": 0, "errored": 0, "dollars": 5.490906, "aborted": null}, "sonnet:P_author": {"calls": 8, "cached": 0, "scored": 8, "refused": 0, "errored": 0, "dollars": 0.038242, "aborted": null}, "sonnet:P_author_ctx": {"calls": 8, "cached": 0, "scored": 8, "refused": 0, "errored": 0, "dollars": 0.048168, "aborted": null}, "sonnet:O_diff": {"calls": 4, "cached": 0, "scored": 4, "refused": 0, "errored": 0, "dollars": 0.025996, "aborted": null}, "sonnet:O_whole": {"calls": 4, "cached": 0, "scored": 4, "refused": 0, "errored": 0, "dollars": 0.02059, "aborted": null}, "opus48:P_own": {"calls": 99, "cached": 0, "scored": 99, "refused": 0, "errored": 0, "dollars": 14.414785, "aborted": null}, "opus48:O_diff": {"calls": 4, "cached": 0, "scored": 4, "refused": 0, "errored": 0, "dollars": 0.13229, "aborted": null}, "sol:P_author": {"calls": 8, "cached": 0, "scored": 8, "refused": 0, "errored": 0, "dollars": 0.031706, "aborted": null}, "sol:O_diff": {"calls": 4, "cached": 0, "scored": 4, "refused": 0, "errored": 0, "dollars": 0.016139, "aborted": null}}

_ARCHIVED: no verdict, no gap, no gate 3 to 5 reading (pilot-gates.md B.3)_
