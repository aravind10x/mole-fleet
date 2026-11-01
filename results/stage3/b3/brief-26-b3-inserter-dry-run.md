# Brief 26 v2 (blue; a fresh session on Opus 5.5 or Sonnet 5.5; GLM 5.3 on Cursor as the fallback; $0, no API call): the edit-application check on every B3 item, before brief 20 Part 3

Written 2026-11-01 by the coordinator from brief 15 (Part S's layout line, A6.8, A6.17.2, A6.17.9 (6), A6.17.10 (c)) and the review session's proposal of the same day on brief 25's result (`work/stage3/b3/review/review-brief25-2026-11-01.md`). Working directory: the project root `/Users/aravind/KruxAI/tais-project-selection`; the fork is `work/mole-fork` (branch `stage3`); every path below is from the root. This is a reproducibility check of the study's own tooling: it reads pre-registered test items and document snapshots, applies edits in memory, and compares; it changes nothing.

**Why.** B3's test items are edit sets (three lines each) written by two model writers under brief 15, with their line positions keyed to a document text. Brief 25 rendered each item against its document's day-0 snapshot for the comprehension readers; for nine of the 28 stratum members, a line's target position was not found in that snapshot (`anchors_resolve` false in `stratum-v0.json`), and brief 15 A6.17.2 records that such lines read as illegible for that reason. The later measurement (Part S) applies each item to the document states it will use, so whether application succeeds is a property of the data and the tooling, decided here, before Part 3 sizes anything.

## D0. Orientation ($0)

Read brief 15's Part S layout line (the v3-amended application module, one seed stream, the position-draw rule, the lone-line arm of A6.8) and A6.17.2, A6.17.9 and A6.17.10. Locate the application module brief 15 names (the T1 module with brief 07h's fixes, under `scripts/stage3/` in the fork) and record its path and sha256; if more than one candidate module exists, name them all and say which Part S would use and why.

Inputs: `work/stage3/b3/payloads-b3-candidates-sonnet55.json` and `payloads-b3-candidates-glm53.json` (the 78 quiet candidates, keyed by writer file and id), `work/stage3/b3/controls-b3-sonnet55.json` and `controls-b3-glm53.json` (the 22 controls), brief 25's `work/stage3/b3/comprehension/items-v0.json` (the 24 comparison items of brief 23's v2 regime, and the opaque ids), `stratum-v0.json` (membership, `anchors_resolve`). Document states: the day-0 snapshots as briefs 23 and 25 rendered them, and the states Part S will use, rebuilt in memory through `mole/oracles/document.py` as brief 07h did.

## D1. The check ($0)

For every item (78 candidates, 22 controls, 24 comparison items) and every line of it, against (i) the day-0 snapshot and (ii) the state at the day Part S will use (if that day is not yet fixed, every day of the current bank, saying so), with the seeded position stream brief 15's layout names (if the stream is not yet written, every position the layout can draw, saying so), report:
- whether the line's target position is found (replace lines) or the append position exists (append lines), and whether it is found exactly once;
- whether the document after application equals the intended result exactly (a byte comparison against the intended lines in place);
- failures by reason: target absent, target found more than once, line already present, target line changed by a later routine edit, other (named);
- for each item, whether its three lines can be applied at one position draw without affecting one another; and each lone line of the A6.8 arm likewise.

The application module is not changed. A defect is reported as a count and a line number of the module, never fixed here; the coordinator decides.

## D2. Outputs

- `work/stage3/b3/inserter-dry-run-v0.json` and `.md`: per item by opaque id (brief 25's ids), per line: found, unique, diff_equal, reason; aggregates by regime (candidates, controls, comparison), by writer, by population (78, 28, 19, 21) and by `anchors_resolve`; **the drop list** (ids of items with too few valid position draws under the rule below, with reasons; possibly empty); **the reverse-case count** (lines found at day 0 but not in the Part S state); the module's path and hash; the document-state source and day; which position case applied (the seeded stream, or every draw enumerated).
- The script with tests, mirrored to the fork under `scripts/stage3/`; the outputs mirrored under `results/stage3/b3/`.
- One STATUS line with hashes and the drop count; this brief's row in `briefs/INDEX.md`.

**Do not:** print any item line, document text, rubric or declared effect; call any judge, reader or review view; modify any document state, bank, corpus or frozen file; change the application module or the item files.

**Rule (brief 15 A6.17.10 (c)).** A position draw is *valid* for an item when every line's target is found exactly once there, the document after application equals the intended result exactly, and the item's lines do not affect one another (for a lone line: that line alone). An item has **too few valid draws** when, under Part S's position-draw rule, it has fewer than the adopted layout needs: at T2+S2 (brief 20 Part 2: 248 item units per view, 468 lone-line units) **two** valid draws for the item and **two** for each of its lone lines (candidates only; the lone-line arm is the 78 × 3 lines). Such an item is dropped from every population it belongs to: a candidate from the 78, 28, 19 and 21; a control from the control arm; a comparison item from the floor, each with its reason named, before Part 3, which sizes every population and arm on the net n's. S1 then restricts its seeded draws to valid positions, or states that the draw rule already does so, citing the module's code by line.

**Done means:** the two output files exist with their hashes in STATUS; the drop list is explicit, even if empty; the module's path and hash are recorded; each of the nine stratum members with `anchors_resolve` false is accounted for (enough valid draws, or dropped with its reason); the reverse-case count is reported; tests pass; the fork mirror is committed (not pushed; the coordinator pushes).

---
Changelog: 2026-11-01, written by the coordinator; revised the same day after the review session's cold read (the drop rule made exact: valid draws against the layout's need, two per item and two per lone line at T2+S2; controls and comparison items included; the reverse-case count). **v2 the same evening** after a safeguard stop on the first session: the same task reworded as an edit-application check (apply, target position, position draw, comparison regime), with the rendering-artefact reasoning kept and the later-measurement framing removed; nothing in the task changed. v1 kept at `work/stage3/b3/brief-26-v1-superseded.md`. Fallback if v2 stops again: GLM 5.3 on Cursor, with the harness disclosed and the outputs verified by tests and hashes as for every executor.
