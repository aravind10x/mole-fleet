# Authoring note for brief 32 v2 (a fresh blue session on Opus 5.5 or Sonnet 5.5; $0): what to load, what to write

Written 2026-11-01 night by the coordinator, after two safeguard stops while the coordinator authored v2 itself. The review session's reading of the stops: v1's own text is clean (686 words; its vocabulary scan finds only a repository path and a directory name), so the stops more likely came from what the authoring session had loaded than from brief 32's wording. This session therefore loads only what is listed here.

**Load only these:**
1. `briefs/32-b3-s2-estimate-2026-11-01.md` (v1, 2164f9b3), the text to revise;
2. the last two lines of `STATUS.md` that begin "BRIEF 32 v2 NOT WRITTEN" and this note's line, which hold the review session's four items;
3. `work/stage3/b3/plan.md` §2.6 (the unit table) and the plan's hash (4c677dee) for citation;
4. `work/stage3/b3/power-simulation-v3b.md` (5f6b0eae) and `power-simulation-v3b.json` (031795d5), **keys `unit_costs` and `estimate` only**, for Part 2's per-unit token bases per view and judge;
5. the function `lone_line_feasibility()` in `work/checks/stage3_b3_s1_populations.py` (9ea7d687, about lines 90 to 120; it reads `items[].draws.valid_draws` and each line's `valid_draws`), **source only, do not run the script** (it reads `stratum-v0.json`), so that v2's H2 can say "the same function, applied to the control items"; `s1-populations-v0.json` (f17e7a72) by structure only if a field name is needed;
6. `briefs/26-b3-inserter-dry-run-2026-11-01.md` (v2) for vocabulary: application, target position, position draw, control items, same-shape comparison items.

**Do not load:** brief 15's Part W or Part R text, any writer or rater file, any account-level scenario material, candidate or control item files, judge caches, `work/stage3/red/`, and **v3b's input files (the rater key, the ratings and the judge-result files listed in its `inputs_sha256`)**.

**Write:** brief 32 v2 as one clean file replacing v1 (history in the changelog), carrying the four items from the STATUS line: (1) H1 priced by Part 2's method with no position draw; (2) H2's check of the control items as the same enumeration over every valid pair, with the tag-6 re-draw rule and the "all pass / some short (how many) / none" report; (3) unit counts recomputed from §2.6's rows, lone lines not priced on the live views or `O_diff`; (4) the stop at twice the confirmed total, add-on and any approved k = 2 line included. Everything else in v1 stands (H0's pre-flight, H3's cleanness test, H4's outputs). Cite v1 (2164f9b3) and `plan.md` (4c677dee). Report the new hash in one STATUS line; commit the fork mirror (`results/stage3/b3/brief-32-b3-s2-estimate.md`), do not push.

The review session cold-reads v2 before Aravind opens it.

Changelog: 2026-11-01 night, written; revised the same night after the review session's cold read (load item 4 narrowed to two keys of v3b's JSON, since v3b's inputs list barrier files; item 5 cites `lone_line_feasibility()` by source; v3b's inputs added to the do-not list).
