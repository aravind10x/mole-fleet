# Brief 26 (blue; a fresh session on Opus 5.5, or brief 25's session; $0, no API call): the inserter dry run on every B3 item, before brief 20 Part 3

Written 2026-11-01 by the coordinator from brief 15 (Part S's layout line, A6.8, A6.17.2, A6.17.9 (6), A6.17.10 (c)) and the review session's proposal of the same day, after Aravind's advisor, on brief 25's result (`work/stage3/b3/review/review-brief25-2026-11-01.md`). Working directory: the project root `/Users/aravind/KruxAI/tais-project-selection`; the fork is `work/mole-fork` (branch `stage3`); every path below is from the root.

**Why.** Brief 25 found that the nine stratum members whose replace anchors do not resolve in the day-0 document text look illegible to comprehension readers, while S3's judges will see whatever the inserter actually plants (brief 15 A6.17.2). Whether the inserter plants each item as intended is a mechanical question, and it must be answered before Part 3, because an item that cannot be planted leaves every population and changes the n's Part 3 sizes.

## D0. Orientation ($0)

Read brief 15's Part S layout line (the v3-amended inserter, one seed stream, the placement rule, the singleton arm of A6.8) and A6.17.2, A6.17.9 and A6.17.10. Locate the inserter brief 15 names (the T1 inserter with brief 07h's fixes, under `scripts/stage3/` in the fork) and record its path and sha256; if more than one candidate module exists, name them all and say which S3 would use and why.

Inputs: `work/stage3/b3/payloads-b3-candidates-sonnet55.json` and `payloads-b3-candidates-glm53.json` (the 78 quiet candidates, keyed by writer file and id), `work/stage3/b3/controls-b3-sonnet55.json` and `controls-b3-glm53.json` (the 22 controls), brief 25's `work/stage3/b3/comprehension/items-v0.json` (the sham's 24 and the opaque ids), `stratum-v0.json` (membership, `anchors_resolve`). Document states: the day-0 texts as briefs 23 and 25 rendered them, and the live states S3's planting will use, rebuilt through `mole/oracles/document.py` as brief 07h did.

## D1. The dry run ($0)

For every item (78 candidates, 22 controls, 24 sham) and every line of it, against (i) the day-0 text and (ii) the live state at the planting day S3 will use (if S3's day is not yet fixed, every day of the current bank, saying so), with the seeded placement stream brief 15's layout names (if the stream is not yet written, every placement the layout can draw, saying so), report:
- whether the anchor resolves (replace lines) or the append position exists (append lines), and whether it resolves uniquely;
- whether the post-insertion document equals the intended result exactly (a byte comparison of the rebuilt document against the intended lines in place);
- failures by reason: anchor absent, anchor ambiguous, line already present, line overwritten by a later honest edit, other (named);
- for each triple, whether its three lines can be planted in one placement without interfering with each other; and the singleton arm's lone plants (A6.8) likewise.

The inserter is not changed. A defect is reported as a count and a line number of the module, never fixed here; the coordinator decides.

## D2. Outputs

- `work/stage3/b3/inserter-dry-run-v0.json` and `.md`: per item by opaque id (brief 25's ids), per line: resolves, unique, diff_equal, reason; aggregates by regime (candidates, controls, sham), by writer, by population (78, 28, 19, 21) and by `anchors_resolve`; **the drop list** (ids of items that cannot be planted as intended under A6.17.10 (c), with reasons; possibly empty); the inserter's path and hash; the document-state source and day; the placement stream used.
- The script with tests, mirrored to the fork under `scripts/stage3/`; the outputs mirrored under `results/stage3/b3/`.
- One STATUS line with hashes and the drop count; this brief's row in `briefs/INDEX.md`.

**Do not:** print any item line, document text, rubric or declared effect; call any judge, reader or review view; write to the live world, the bank or `data/corpus/`; change the inserter, the candidate files or any frozen file.

**Rule (brief 15 A6.17.10 (c), made exact after the review session's cold read).** A placement is *valid* for an item when every line's anchor resolves uniquely there, the post-insertion document equals the intended result exactly, and the triple's lines do not interfere with one another (for a lone line of the singleton arm: that line alone). An item **cannot be planted as intended** when, under S3's placement rule, it has fewer valid placements than the adopted layout needs: at T2+S2 (brief 20 Part 2: 248 lone plants per view, 468 singleton plants), **two** valid placements for the item's triple and **two** for each of its lone lines (candidates only; the singleton arm is the 78 × 3 lines). Such an item is dropped from every population it belongs to: a candidate from the 78, 28, 19 and 21; a control from the control arm; a sham item from the floor, each with its reason named, before Part 3, which sizes every population and arm on the net n's. The brief states which case applied: the seeded stream exists and was used, or every placement the layout can draw was enumerated. S1 then restricts its seeded draws to valid placements, or states that the placement rule already does so, citing the inserter's code by line.

**Also report, by count:** the reverse case, items whose anchors resolve at day 0 but not at the live planting state (a later honest edit overwrote or moved the line); these read cleanly in brief 25 and may still be misplanted. Both directions appear in the aggregates.

**Done means:** the two output files exist with their hashes in STATUS; the drop list is explicit, even if empty; the inserter's path and hash are recorded; each of the nine unresolved-anchor stratum members is accounted for (enough valid placements, or dropped with its reason); the reverse-case count is reported; tests pass; the fork mirror is committed (not pushed; the coordinator pushes).

---
Changelog: 2026-11-01, written by the coordinator. Revised the same day after the review session's cold read: the drop rule made exact (valid placements against the layout's need: two per triple and two per lone line at T2+S2), extended to controls and the sham, the reverse-case count added.
