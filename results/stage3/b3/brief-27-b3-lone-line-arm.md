# Brief 27 (blue; a fresh session on Opus 5.5 or Sonnet 5.5; $0, no API call; after brief 20 Part 3, before S3): the lone-line arm and the valid-draw restriction in the application module

Written 2026-11-01 by the coordinator from brief 26's result (`work/stage3/b3/inserter-dry-run-v0.json` edd289ce; findings M1, M4, M5) and brief 15 A6.8, A6.17.10 (c) and A6.17.11. Working directory: the project root `/Users/aravind/KruxAI/tais-project-selection`; the fork is `work/mole-fork` (branch `stage3`); every path below is from the root. Nothing here places anything in a live document: the work is code, tests and an in-memory re-run of brief 26's check.

**Why.** Brief 26 found that the application module (`work/checks/stage3_t1.py` 52a79312; its placement class equals the T1 v3 manifest's) has no arm for a single line applied alone: its arms are lone, k2 and k3 over three statements, and three statement indices are asserted (lines 572, 793, 929). Brief 15 A6.8's lone-line arm, 468 units at T2+S2, therefore has no code. Brief 26 also found that the module's draw rule does not restrict to valid positions (M5: 462 of 7,179 drawable placements are not valid; M1: 7 lines with a non-unique target at some reachable state). S3 cannot open before both are fixed and tested.

## E0. Orientation ($0)

Read brief 26 v2 and its outputs (`inserter-dry-run-v0.{md,json}`; the `rule`, `s1_restriction`, `module_findings`, `lone_lines` and per-item `valid_draws` blocks), brief 15's Part S layout line, A6.5 (iii), A6.8 and A6.17.11, and the module's placement code at the lines brief 26 names. Record the module's sha256 and its placement class hash before any change.

## E1. The lone-line arm ($0)

Add an arm that applies **one line of an item alone**, on its own author (A6.5 (iii)), under the same position-draw rule, the same team template, floor, read-before-edit, redundant-delivery and touching-session rules as the three-line arms (brief 15's layout line), with the line's role index recorded. The three existing arms must behave byte-identically after the change: a test replays each on the T1 v3 manifest's items and compares the produced documents and records to the pre-change module's output (hash equality), and the placement class hash is reported before and after with the diff confined to the new arm.

## E2. The valid-draw restriction ($0)

Enforce, in code, that every seeded draw for an item or a lone line is taken from the valid (day, author) pairs brief 26 lists per item and per lone line (`valid_draws` in `inserter-dry-run-v0.json`, keyed by opaque id), and that the module checks, at the drawn state, a unique target, the exact application and that the line is not already present, refusing a draw that fails any check rather than returning a last layout (brief 26 names the return at line 567). Tests: a draw outside the valid set is refused; a non-unique target is refused; each of the 8 items brief 26 dropped is refused under the pair rule; each of the nine unresolved-anchor stratum members is accepted on both days.

## E3. Brief 26's check re-run ($0)

Re-run `work/checks/stage3_b3_inserter_dry_run.py` unchanged against the new module on the 234 lone lines through the new arm and on the 124 items under the restriction: the drop list must equal brief 26's (8 under the pair rule), the lone-line counts must be reproduced (233 of 234 with two valid draws by different authors), and the item and lone-line valid-draw sets must be identical to brief 26's. Any difference is reported as a count by reason, not reconciled by hand.

## E4. Review and outputs

- A read-only review round (Codex, under the same information barrier as brief 20's rounds, or the review session) on the diff and the tests, with every required fix made and the round recorded.
- `work/stage3/b3/lone-line-arm-v0.md`: the module hashes before and after, the placement class hashes, the test counts, E3's reproduction table, the review record.
- The module and tests mirrored to the fork under `scripts/stage3/`; the record mirrored under `results/stage3/b3/`; one STATUS line with hashes; this brief's row in `briefs/INDEX.md`.

**Do not:** print any item line, document text, rubric or declared effect; call any judge, reader or review view; modify any document state, bank, corpus, item file or frozen file; change the three existing arms' behaviour; run anything against the live world.

**Done means:** E1 and E2 are in the module with tests passing; E3 reproduces brief 26's drop list and counts exactly; the review round is recorded with its fixes made; the record file exists with its hash in STATUS; the fork mirror is committed (not pushed; the coordinator pushes). S3 does not open before this brief is done.

---
Changelog: 2026-11-01, written by the coordinator from brief 26's result and the review session's proposal (brief 27 for the lone-line arm after Part 3, before S3).
