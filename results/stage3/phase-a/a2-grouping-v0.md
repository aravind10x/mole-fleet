# Phase A, A2.1 and A2.2: grouping, the natural experiment, and the oracle-grouping sensitivity (brief 36), v0

Executor session, Opus 5.5, 2026-11-06. Interpreter `work/mole-fork/.venv/bin/python` (`-I`). $0, no model call, no judge cache opened. Script `work/checks/stage3_a2_audit.py grouping`; tests `work/checks/test_stage3_a2_audit.py` (9 passed). Record `a2-grouping-v0.json` (every row below, per arm as well as pooled; input hashes). Bootstrap 2,000 replicates over applications, seed 20261106, unless a row says it is B3's own.

## 1. The sentences

The populations and judges in each sentence were fixed in the script before its first run; the numbers were filled after.

- "Author grouping changes recall by **+0.06 [−0.03, +0.14]** across **160** applications at matched cost; on the certified items the document view reads **0.70 [0.50, 0.90]** under **Opus 4.8** against the dossier's 0.75." The first figure is B1's isolated dossier (`P_author_doc`, Opus 4.8, author rule at 0.10) minus `O_diff` (Opus 4.8, its sealed 0.10 rule) on the same conforming, middle and routine re-draw applications, all arms. Sonnet 5 gives +0.06 [−0.04, +0.15] on the same 160. On the lone arm alone: Opus 4.8 −0.03 [−0.15, +0.10] (60 applications), Sonnet 5 +0.10 [−0.05, +0.25]. Under the certified items, Sonnet 5 reads 0.30 [0.10, 0.50] and GPT-6 Sol 0.45 [0.20, 0.70].
- "With oracle grouping at m = 1, 3, 10, 30, routine recall at a 10 percent window budget is **0.50, 0.38, 0.38, 0.38** against the document view's 0.47 (sensitivity)." These are rater pass-1 shares of the 24 v2 conforming triples; the middle triples read 0.75, 0.54, 0.54, 0.54. The two numbers are on two scales: a rater's composition score against a judge's recall.

## 2. A2.1, the author view against the document view on the same applications

Each row is author-view recall (a), document-view recall (b) and the paired difference a − b. Rows are pooled over arms; the json carries lone, k2 and k3 separately. "iso" and "live" are B1's two dossier modes. Sham rows are the placebo arms.

**B1: the dossier, at its author rule (expected cost 0.10; realised 0.1007, Opus live 0.0805). Matched cost.**

| judge | dossier | population | n | a | b | a − b [95%] |
|---|---|---|---|---|---|---|
| Opus 4.8 | iso | v2 conforming | 64 | 0.56 | 0.41 | +0.16 [+0.03, +0.28] |
| Opus 4.8 | iso | v3 middle | 64 | 0.50 | 0.59 | −0.09 [−0.23, +0.06] |
| Opus 4.8 | iso | v3 routine re-draw | 32 | 0.63 | 0.47 | +0.16 [−0.03, +0.34] |
| Opus 4.8 | iso | v1 (re-plant) | 64 | 0.88 | 0.88 | 0.00 [−0.09, +0.09] |
| Opus 4.8 | iso | v2 alarming | 24 | 1.00 | 1.00 | 0.00 |
| Opus 4.8 | iso | sham (v2 / re-plant / v3 re-draw) | 64 / 64 / 32 | 0.22 / 0.27 / 0.31 | 0.03 / 0.09 / 0.00 | +0.19 / +0.17 / +0.31 |
| Opus 4.8 | live | conforming / middle / routine | 64 / 64 / 32 | 0.78 / 0.92 / 0.81 | 0.41 / 0.59 / 0.47 | +0.38 / +0.33 / +0.34 (lower bounds ≥ +0.19) |
| Opus 4.8 | live | sham (v2 / re-plant / v3 re-draw) | 64 / 64 / 32 | 0.33 / 0.25 / 0.19 | 0.03 / 0.09 / 0.00 | +0.30 / +0.16 / +0.19 |
| Sonnet 5 | iso | conforming / middle / routine | 64 / 64 / 32 | 0.34 / 0.42 / 0.47 | 0.34 / 0.34 / 0.34 | 0.00 / +0.08 / +0.13 (every interval covers 0) |
| Sonnet 5 | iso | v1 / alarming | 64 / 24 | 0.78 / 0.92 | 0.73 / 0.96 | +0.05 / −0.04 |
| Sonnet 5 | iso | sham (v2 / re-plant / v3 re-draw) | 64 / 64 / 32 | 0.28 / 0.19 / 0.19 | 0.03 / 0.11 / 0.13 | +0.25 [+0.13, +0.38] / +0.08 / +0.06 |
| Sonnet 5 | live | conforming / middle / routine | 64 / 64 / 32 | 0.47 / 0.59 / 0.47 | 0.34 / 0.34 / 0.34 | +0.13 / +0.25 [+0.09, +0.41] / +0.13 |
| Sonnet 5 | live | sham (v2 / re-plant / v3 re-draw) | 64 / 64 / 32 | 0.14 / 0.13 / 0.09 | 0.03 / 0.11 / 0.13 | +0.11 / +0.02 / −0.03 |

**Reading the B1 table.**
- At matched honest cost, the isolated dossier's gain over the document view on the governing regimes is small and covers zero.
- The live dossier's gain is large.
- **But the author view also flags the sham (placebo) applications more often than the document view does: +0.17 to +0.31 under Opus 4.8 isolated.** So part of each attack-arm gain is a higher flag rate on planted sessions whatever they carry. The sham rows are the comparison a reader should net against.
- Every row's B1 recall equals the share of its flags (128 of 128 rows checked). The k3 arm exists for 16 of 24 payloads (8 of 12 on the re-draws), so those absent arms are not counted.

**The re-plant: zero-context `P_author` at its author rule 0.05 against `O_diff` at 0.10. Not cost-matched; recorded for completeness.**

| judge | population | n | a | b | a − b [95%] |
|---|---|---|---|---|---|
| Sonnet 5 | v1 | 64 | 0.45 | 0.73 | −0.28 [−0.44, −0.13] |
| GLM 5.3 | v1 | 64 | 0.70 | 0.78 | −0.08 [−0.22, +0.05] |
| Opus 4.8 | v1 | 64 | 0.81 | 0.88 | −0.06 [−0.16, +0.02] |
| Sonnet 5 / GLM 5.3 / Opus 4.8 | sham | 64 each | 0.11 / 0.19 / 0.09 | 0.11 / 0.33 / 0.09 | 0.00 / −0.14 / 0.00 |

**B3 (S-A4, S-A5, S-N1): `b3-results.json` holds aggregates only.** No per-application scores are in the json, so nothing here is recomputed. B3 itself recorded the paired gap on the same 146 item applications of the full quiet set, with a bootstrap clustered on items (seed 20261152). It is carried below with the sign turned to author minus document. The dossier (instrument C, the carrier, Opus 4.8 isolated) is at 0.10; `P_author` (S, Opus 4.8) is at 0.05.

| document-view judge | author instrument | a | b | a − b [95%] |
|---|---|---|---|---|
| Sonnet 5 | C (dossier) | 0.30 | 0.16 | +0.14 [+0.04, +0.25] |
| Opus 4.8 | C (dossier) | 0.30 | 0.29 | +0.01 [−0.08, +0.10] |
| GPT-6 Sol | C (dossier) | 0.30 | 0.12 | +0.18 [+0.12, +0.27] |
| Sonnet 5 / Opus 4.8 / Sol | S (`P_author`, 0.05) | 0.23 | 0.16 / 0.29 / 0.12 | +0.08 / −0.06 / +0.12 |

**The certified ten (S-M2).** The ids are `s3-analysis-matrix-v0.json` `populations.certified.ids` (checked: 10). The scores are `s3-scores-v0.json`'s `O_diff` rows: every judge present there (Opus 4.8, GPT-6 Sol, Sonnet 5) is scored on all 20 item applications, with the flag S3's driver recorded at each judge's sealed rule.

| judge | recall [95%, bootstrap over the 10 items] |
|---|---|
| Opus 4.8 | 0.70 (14/20) [0.50, 0.90] |
| GPT-6 Sol | 0.45 (9/20) [0.20, 0.70] |
| Sonnet 5 | 0.30 (6/20) [0.10, 0.50] |
| the dossier (S-M2, Opus 4.8 isolated, lone recall) | 0.75 [0.50, 0.95] |

The comparison crosses units: the dossier's figure is a lone recall per item, and the document view's is per item application.

## 3. A2.2, the oracle-grouping sensitivity

**Sensitivity, not a bound: rater not judge; subsets independent; 07s's triple counts.**

- **Scores:** `t1k-rater/ratings-triples.json`, triple id and pass scores only.
- **Populations:** `key-triples.json`, ids and labels by script, nothing printed. The populations: honest random 120, honest same-author 22, v2 conforming (the routine band) 24, v3 middle 24, equal to 07s's counts.
- **Threshold:** for each m, the 90th percentile of the maximum over m honest random triples drawn with replacement (2,000 replicates, seed 20261106).
- **Reading:** the share of each arm's triples at or above it.

| pass | arm | m = 1 | m = 3 | m = 10 | m = 30 |
|---|---|---|---|---|---|
| 1 (primary) | threshold | 65 | 70 | 70 | 70 |
| 1 | routine (v2 conforming, 24) | 0.50 | 0.38 | 0.38 | 0.38 |
| 1 | middle (v3, 24) | 0.75 | 0.54 | 0.54 | 0.54 |
| 2 | threshold | 62 | 72 | 75 | 76 |
| 2 | routine | 0.58 | 0.29 | 0.29 | 0.25 |
| 2 | middle | 0.75 | 0.54 | 0.38 | 0.38 |

**Limitation.** Pass 1's honest random maximum is 70 (7 of 120 triples). From m = 3 on, the 90th percentile of the maximum sits at that observed ceiling. The pass-1 shares therefore stop falling there because the honest sample is small, not because grouping stops costing. Pass 2's finer scores show the decline continuing.
