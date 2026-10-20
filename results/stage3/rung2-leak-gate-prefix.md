# Permutation leak gate: honest prefix, 10 of 50 accounts drawn positive (honest-null check, rung 2 restated)

Computed 2026-10-20T13:24:04+00:00 by `work/checks/stage3_leak_gate.py` (stage3-leak-gate-v1); corpus `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/prefix_v1.jsonl` (sha256 c39bf9f86d89), transcripts sha256 cc9e0de51684; unit account-day; positives: random draw of 10 accounts (honest-null check); label seed 20261020; 200 permutations (seeds 20261100..); fold seed offset 777777; grouped-by-account 5-fold CV. $0, no LLM calls. Tag: **tested**.

## Pass condition (written before the statistic it governs)

Design v4 section 11.4, verbatim: "Rungs 2, 3 and 4 gate each leak classifier at the 95th percentile of its permutation null drawn with account-level labels on the run's own features, with grouped-by-account cross-validation and the fold seed decoupled from the label seed. The rung-2 honest-null check becomes 'the observed value lies inside the permutation band', which the prefix passes."

Operationalisation: per classifier, 200 permutations of ACCOUNT-level labels (the observed number of positive accounts; every account-day of a positive account positive) on the run's own features; grouped-by-account 5-fold cross-validated logistic regression (grouping_measure's _logreg_fit and auroc, fold-wise standardisation); fold seed = label seed + FOLD_SEED_OFFSET (777777); the gate is the 95th percentile of the two-sided value max(AUROC, 1 - AUROC) over the permutations. Verdict per classifier: INSIDE the band iff the observed two-sided value <= gate; ABOVE otherwise (a rung-3/4 world kill). Session unit: labels permuted within each account, one positive session per account.

## Result

Rows 118, accounts 50, positive rows 22, positive accounts 10.

| classifier | observed AUROC | observed two-sided | gate (p95 of null two-sided) | null two-sided p50 / p97.5 | null AUROC mean [min, max] | false-kill rate of the fixed 0.6 gate | verdict |
|---|---|---|---|---|---|---|---|
| metadata | 0.503 | 0.503 | 0.704 | 0.573 / 0.713 | 0.494 [0.257, 0.831] | 0.325 | **inside the band (no leak at the 5 percent level)** |
| content | 0.422 | 0.578 | 0.737 | 0.594 / 0.739 | 0.472 [0.209, 0.740] | 0.460 | **inside the band (no leak at the 5 percent level)** |

**Verdict: PASS (every classifier inside its band).**

Features: metadata ['session_length', 'turn_cap_rate', 'events_per_session', 'first_action_min']; content: assistant turns only; word unigrams + within-turn bigrams ([a-z0-9_]+, lowercased) and tool-call names (not arguments), CRC32-hashed into 4096 columns, sublinear TF x smoothed IDF over the classified rows (label-free), rows L2-normalised; plus style features mean_turn_chars, tool_call_turn_share, vocab_per_1k_tokens
