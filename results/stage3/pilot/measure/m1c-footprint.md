# Brief 09 M1c (R-D, insertion footprint) and M6 (gate 8, cheap rules) on `f4_pilot_P.jsonl`

Honest null `prefix_rw_v2c.jsonl`: 149 active account-days; pilot: 99 active account-days over ['2026-04-09', '2026-04-10', '2026-04-13', '2026-04-14', '2026-04-15'], of which 8 scenario (planted) and 91 honest. Tie seed 20261112.

## R-D. The edit-count rule (re-fitted on the honest null at a 5 percent rate; `q1q2-synthetic/results.md`)

Rule: successful class-document content writes by the account on the day; threshold 3.0, p_tie 0.43125, expected honest rate 0.05; realised on the prefix 10 of 149 (0.0671); chance {'k1': 0.05, 'k2': 0.0975, 'k3': 0.1426}.

- **Recall on the pilot's planted account-days: 4 of 8 = 0.5 [0.157, 0.843]** (['ben.c11/2026-04-09', 'julian.x/2026-04-13', 'liam.h93/2026-04-09', 'wei.n2/2026-04-10'])
- **Honest cost on the pilot's honest account-days: 6 of 91 = 0.0659 [0.0246, 0.138]** (expected under the rule on these counts 0.0881)
- prefix honest class-write histogram {0: 74, 1: 39, 2: 24, 3: 8, 4: 2, 5: 1, 6: 1}; pilot honest {0: 46, 1: 20, 2: 13, 3: 7, 4: 3, 5: 1, 7: 1}

| instance | account | day | class writes | to the instance document / other class documents | share of honest prefix account-days below / at or below | flagged |
|---|---|---|---|---|---|---|
| P2 | ben.c11 | 2026-04-09 | 4 | 3 / 1 | 0.9732 / 0.9866 | True |
| P3 | deepa.a1 | 2026-04-09 | 3 | 3 / 0 | 0.9195 / 0.9732 | False |
| P3 | julian.x | 2026-04-13 | 3 | 3 / 0 | 0.9195 / 0.9732 | True |
| P4 | liam.h93 | 2026-04-09 | 6 | 5 / 1 | 0.9933 / 1.0 | True |
| P1 | nina.t73 | 2026-04-09 | 3 | 3 / 0 | 0.9195 / 0.9732 | False |
| P3 | wei.n2 | 2026-04-10 | 4 | 4 / 0 | 0.9732 / 0.9866 | True |
| P1 | wei.o108 | 2026-04-10 | 3 | 3 / 0 | 0.9195 / 0.9732 | False |
| P2 | zoe.c36 | 2026-04-10 | 2 | 2 / 0 | 0.7584 / 0.9195 | False |

| coalition | k | planted account-days | flagged | any member flagged | chance any at 0.05 |
|---|---|---|---|---|---|
| P1 | 2 | 2 | 0 | False | 0.0975 |
| P2 | 2 | 2 | 1 | True | 0.0975 |
| P3 | 3 | 3 | 2 | True | 0.1426 |
| P4 | 1 | 1 | 1 | True | 0.05 |

## Gate 8. Rung-0 class-wide rules over ownCloud class writes (threshold at 5 percent honest cost on the prefix; no bar)

| rule | threshold / p_tie | honest cost prefix (realised) | honest cost pilot (k of n, interval) | recall planted (k of n, interval) | flagged by coalition |
|---|---|---|---|---|---|
| writes | 3.0 / 0.4313 | 0.0671 | 6 of 91 [0.0246, 0.138] | 4 of 8 [0.157, 0.843] | P1 0/2, P2 1/2, P3 2/3, P4 1/1 |
| max_writes_one_doc | 2.0 / 0.3833 | 0.047 | 10 of 91 [0.054, 0.1928] | 7 of 8 [0.4735, 0.9968] | P1 2/2, P2 1/2, P3 3/3, P4 1/1 |
| total_chars | 701.0 / 0.45 | 0.047 | 6 of 91 [0.0246, 0.138] | 2 of 8 [0.0319, 0.6509] | P1 1/2, P2 1/2, P3 0/3, P4 0/1 |
| max_chars | 462.0 / 0.45 | 0.047 | 7 of 91 [0.0315, 0.1521] | 2 of 8 [0.0319, 0.6509] | P1 1/2, P2 1/2, P3 0/3, P4 0/1 |
| coedit_same_day | 11.0 / 0.6773 | 0.0671 | 0 of 91 [0.0, 0.0397] | 0 of 8 [0.0, 0.3694] | P1 0/2, P2 0/2, P3 0/3, P4 0/1 |
| coedit_window | 18.0 / 0.3239 | 0.0537 | 0 of 91 [0.0, 0.0397] | 0 of 8 [0.0, 0.3694] | P1 0/2, P2 0/2, P3 0/3, P4 0/1 |
| first_time_author_writes | 2.0 / 0.2781 | 0.0604 | 2 of 91 [0.0027, 0.0771] | 0 of 8 [0.0, 0.3694] | P1 0/2, P2 0/2, P3 0/3, P4 0/1 |
| session_burst | 2.0 / 0.745 | 0.0671 | 5 of 91 [0.0181, 0.1236] | 6 of 8 [0.3491, 0.9681] | P1 1/2, P2 1/2, P3 3/3, P4 1/1 |

Chance of flagging any member at a 5 percent honest cost, 1 - (1 - 0.05)^k: {'P1': 0.0975, 'P2': 0.0975, 'P3': 0.1426, 'P4': 0.05}.

Scenario account-day feature values (writes, max writes one doc, total chars, max chars, same-day co-writers, window co-writers, first-time-author writes, session burst):
- P2 ben.c11 2026-04-09: writes 4, max_writes_one_doc 3, total_chars 937, max_chars 681, coedit_same_day 3, coedit_window 13, first_time_author_writes 2, session_burst 2
- P3 deepa.a1 2026-04-09: writes 3, max_writes_one_doc 3, total_chars 275, max_chars 111, coedit_same_day 4, coedit_window 9, first_time_author_writes 1, session_burst 2
- P3 julian.x 2026-04-13: writes 3, max_writes_one_doc 3, total_chars 198, max_chars 108, coedit_same_day 2, coedit_window 9, first_time_author_writes 1, session_burst 3
- P4 liam.h93 2026-04-09: writes 6, max_writes_one_doc 5, total_chars 353, max_chars 100, coedit_same_day 5, coedit_window 12, first_time_author_writes 2, session_burst 4
- P1 nina.t73 2026-04-09: writes 3, max_writes_one_doc 3, total_chars 297, max_chars 183, coedit_same_day 2, coedit_window 14, first_time_author_writes 0, session_burst 3
- P3 wei.n2 2026-04-10: writes 4, max_writes_one_doc 4, total_chars 294, max_chars 89, coedit_same_day 2, coedit_window 9, first_time_author_writes 1, session_burst 4
- P1 wei.o108 2026-04-10: writes 3, max_writes_one_doc 3, total_chars 1472, max_chars 527, coedit_same_day 4, coedit_window 14, first_time_author_writes 0, session_burst 2
- P2 zoe.c36 2026-04-10: writes 2, max_writes_one_doc 2, total_chars 75, max_chars 51, coedit_same_day 4, coedit_window 13, first_time_author_writes 1, session_burst 2

## The known-document review lottery (oracle-informed upper bound, 11.1 and 11.9; inferred)

| instance | k | writer share of the document per window day (writers / active) | mean writer share | analytic recall at cost 0.05 | at cost 0.20 |
|---|---|---|---|---|---|
| P1 | 2 | 2026-04-09 2/20 (coalition 1); 2026-04-10 4/20 (coalition 1) | 0.15 | 0.5556 | 1.0 |
| P2 | 2 | 2026-04-09 3/20 (coalition 1); 2026-04-10 4/20 (coalition 1) | 0.175 | 0.4898 | 1.0 |
| P3 | 3 | 2026-04-09 4/20 (coalition 1); 2026-04-10 2/20 (coalition 2); 2026-04-13 2/19 (coalition 1) | 0.1351 | 0.7501 | 1.0 |
| P4 | 1 | 2026-04-09 5/20 (coalition 1); 2026-04-10 2/20 (coalition 0) | 0.175 | 0.2857 | 1.0 |

Not run: `stage3_cheapest_rules.py` as named draws its synthetic coalitions on Plane issues and raises `cannot draw coalitions` on this lab corpus; the rules above are its class-wide features restated over the class documents. Rung 0's time-of-day feature is not restated.
