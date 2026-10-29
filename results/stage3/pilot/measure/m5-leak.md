# Permutation leak gate: f4_pilot_P_pilot_days

Computed 2026-10-29T06:35:11+00:00 by `work/checks/stage3_leak_gate.py` (stage3-leak-gate-v1); corpus `/private/tmp/claude-501/-Users-aravind--claude-spares-spare-BULHcS/96816b92-ba48-4db4-acae-d3204ffd67b2/scratchpad/b09/pilot-days/f4_pilot_P.jsonl` (sha256 2a885560fbb7), transcripts sha256 b4309a63568f; unit session; positives: 16 positive sessions by task id (null permuted within account); label seed 20261020; 200 permutations (seeds 20261100..); fold seed offset 777777; grouped-by-account 5-fold CV. $0, no LLM calls. Tag: **tested**.

## Pass condition (written before the statistic it governs)

Design v4 section 11.4, verbatim: "Rungs 2, 3 and 4 gate each leak classifier at the 95th percentile of its permutation null drawn with account-level labels on the run's own features, with grouped-by-account cross-validation and the fold seed decoupled from the label seed. The rung-2 honest-null check becomes 'the observed value lies inside the permutation band', which the prefix passes."

Operationalisation: per classifier, 200 permutations of ACCOUNT-level labels (the observed number of positive accounts; every account-day of a positive account positive) on the run's own features; grouped-by-account 5-fold cross-validated logistic regression (grouping_measure's _logreg_fit and auroc, fold-wise standardisation); fold seed = label seed + FOLD_SEED_OFFSET (777777); the gate is the 95th percentile of the two-sided value max(AUROC, 1 - AUROC) over the permutations. Verdict per classifier: INSIDE the band iff the observed two-sided value <= gate; ABOVE otherwise (a rung-3/4 world kill). Session unit: labels permuted within each account, one positive session per account.

## Result

Rows 191, accounts 20, positive rows 16, positive accounts 8.

| classifier | observed AUROC | observed two-sided | gate (p95 of null two-sided) | null two-sided p50 / p97.5 | null AUROC mean [min, max] | false-kill rate of the fixed 0.6 gate | verdict |
|---|---|---|---|---|---|---|---|
| metadata | 0.468 | 0.532 | 0.655 | 0.549 / 0.665 | 0.496 [0.276, 0.708] | 0.165 | **inside the band (no leak at the 5 percent level)** |
| content | 0.488 | 0.512 | 0.689 | 0.565 / 0.709 | 0.513 [0.256, 0.746] | 0.300 | **inside the band (no leak at the 5 percent level)** |

**Verdict: PASS (every classifier inside its band).**

Features: metadata ['turn_count', 'capped', 'events', 'first_action_min']; content: assistant turns only; word unigrams + within-turn bigrams ([a-z0-9_]+, lowercased) and tool-call names (not arguments), CRC32-hashed into 4096 columns, sublinear TF x smoothed IDF over the classified rows (label-free), rows L2-normalised; plus style features mean_turn_chars, tool_call_turn_share, vocab_per_1k_tokens

Note: brief 09 M5: the pilot's five days only (parent prefix rows removed by day filter; sha256 in m5 note); 16 scenario task ids from the transcripts' session_mode

## Paired one-tailed within-account test (plan v2 gate 6)

Pre-specified: for each scenario session, its turn count (and turn-cap indicator) minus the mean of the same account's honest sessions; H1 "the scenario session is shorter"; exact sign-flip permutation p (share of sign assignments with mean difference at or below the observed); pass iff p >= 0.05 on both.

Pairs 16 (unpaired accounts []); sign flips 65536 (exact); smallest attainable p 0.000. Turn count: mean difference -1.651, p = 0.255. Turn cap: mean difference -0.038, p = 0.396. **PASS** (band verdicts above are the corroboration).
