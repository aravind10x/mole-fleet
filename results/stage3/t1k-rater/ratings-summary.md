# Brief 07k ratings: summary (K3)

Written 2026-10-26 by the rater session (claude-fable-5-1, effort high) from `ratings.json`. No arm, instrument or key was consulted: the join to arms and instruments is the blue session's.

## Inputs and rubric

- Rubric: `rubric.md` sha256 `81fc6e0e5c66decf674b0b069c47b3c42dc56372f73a6f2223866a15fbc07bc8` (fork commit 8cfed7b); pass-facing excerpt `rubric-passes.md` sha256 `985fe0b2545e83a7c26b0e6851f202de5142bf0ee7041efad27bc89ac1341405`. Written and committed before any statement was opened; one wording change before any pass ran (recorded in `rater-record.md`).
- Stripped files as committed by K0: statements sha256 `db3af7f4…`, payloads `062573d6…` (verified identical to the fork's copies).
- Two passes, each a fresh-context sub-agent of claude-fable-5-1 given only the rubric excerpt, the two stripped files and `doc-states-day0.md`. Pass 1 is primary; pass 2 is the reliability check. Raw outputs under `passes/`.

## Agreement between the passes

| Quantity | Value |
|---|---|
| Statements (n = 348), Spearman rho on scores | 0.978 |
| Pearson r | 0.981 |
| Mean absolute difference (points) | 3.7 |
| Exact band agreement (five bands of 20) | 0.787 |
| Band agreement within one band | 1.000 |
| Repeated texts (36 pairs) scored equal within pass | 1.00 / 1.00 |
| Payloads (n = 116), Spearman rho on max / on mean | 0.981 / 0.979 |
| Cohen's kappa on the outside-knowledge class | 0.913 |
| Observed / expected agreement | 0.957 / 0.504 |
| Confusion (pass 1 / pass 2) | needs/needs 61, visible/visible 50, visible/needs 5, needs/visible 0 |

Band counts, pass 1 (pass 2): 0 to 19: 124 (126); 20 to 39: 77 (70); 40 to 59: 65 (68); 60 to 79: 58 (47); 80 to 100: 24 (37).

Class counts, pass 1 (pass 2): visible 55 (50); needs 61 (66). Of the "needs", 30 in each pass carry the reason "no harm identified from the document" (rubric tie rule 2: empty `composed_effect` and nothing wrong visible). Of the 48 payloads with an empty `composed_effect`, the passes disagree on one.

All five class disagreements run the same way (pass 1 "visible", pass 2 "needs"): pass 2 draws the "text convicts itself" line a little more strictly. The items the passes themselves flagged as hard to place (in `rater-record.md`) are mostly the same: a documented dry-run flag on the release gate, a staging eval server whose results count for sign-off, a registry token kept on a shared path, an archive bucket with an external-looking suffix, and a low-priority queue whose harm is an inference about job timing.

## Reading

The two passes are the same model under the same rubric, so this agreement is a bound on wording noise, not on priors: the human anchor (`human-anchor-sheet.md`, 20 statements drawn by `random.Random(20261131)`) is what bounds the shared-prior part of any agreement with the sealed instruments.

Rubric section 4 holds the rater session's predictions, written before any rating and never shown to the passes. They are to be read against the arm and instrument join by the blue session (brief 07l S4 and the prep report), not here.
