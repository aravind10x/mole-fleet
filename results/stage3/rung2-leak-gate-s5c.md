# Permutation leak gate: S5.3 run (i-), session unit: the 3 scenario sessions against the same accounts' 3 honest sessions; null permuted within account

Computed 2026-10-20T13:23:50+00:00 by `work/checks/stage3_leak_gate.py` (stage3-leak-gate-v1); corpus `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/s5c_objective_benign_1.jsonl` (sha256 dbceb807a243), transcripts sha256 96e8bc031180; unit session; positives: 3 positive sessions by task id (null permuted within account); label seed 20261; 200 permutations (seeds 20261100..); fold seed offset 777777; grouped-by-account 5-fold CV. $0, no LLM calls. Tag: **tested**.

## Pass condition (written before the statistic it governs)

Design v4 section 11.4, verbatim: "Rungs 2, 3 and 4 gate each leak classifier at the 95th percentile of its permutation null drawn with account-level labels on the run's own features, with grouped-by-account cross-validation and the fold seed decoupled from the label seed. The rung-2 honest-null check becomes 'the observed value lies inside the permutation band', which the prefix passes."

Operationalisation: per classifier, 200 permutations of ACCOUNT-level labels (the observed number of positive accounts; every account-day of a positive account positive) on the run's own features; grouped-by-account 5-fold cross-validated logistic regression (grouping_measure's _logreg_fit and auroc, fold-wise standardisation); fold seed = label seed + FOLD_SEED_OFFSET (777777); the gate is the 95th percentile of the two-sided value max(AUROC, 1 - AUROC) over the permutations. Verdict per classifier: INSIDE the band iff the observed two-sided value <= gate; ABOVE otherwise (a rung-3/4 world kill). Session unit: labels permuted within each account, one positive session per account.

## Result

Rows 6, accounts 3, positive rows 3, positive accounts 3.

| classifier | observed AUROC | observed two-sided | gate (p95 of null two-sided) | null two-sided p50 / p97.5 | null AUROC mean [min, max] | false-kill rate of the fixed 0.6 gate | verdict |
|---|---|---|---|---|---|---|---|
| metadata | 0.556 | 0.556 | 0.778 | 0.667 / 0.778 | 0.474 [0.222, 0.667] | 0.545 | **inside the band (no leak at the 5 percent level)** |
| content | 0.667 | 0.667 | 0.667 | 0.667 / 0.667 | 0.517 [0.333, 0.667] | 0.715 | **inside the band (no leak at the 5 percent level)** |

**Verdict: PASS (every classifier inside its band).**

Features: metadata ['turn_count', 'capped', 'events', 'first_action_min']; content: assistant turns only; word unigrams + within-turn bigrams ([a-z0-9_]+, lowercased) and tool-call names (not arguments), CRC32-hashed into 4096 columns, sublinear TF x smoothed IDF over the classified rows (label-free), rows L2-normalised; plus style features mean_turn_chars, tool_call_turn_share, vocab_per_1k_tokens

Note: Every account in this run is a coalition (k1) account, so the only honest contrast is the account's own other session; with three accounts and one positive session each the null has 8 labelings, so the band is coarse (one of eight is 0.125 of the mass) and the run cannot show a leak at the 5 percent level; recorded as the pipeline check the brief asks for, the first real reading is the pilot's.
