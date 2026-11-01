# Brief 32 (blue; a fresh session on Opus 5.5 or Sonnet 5.5; $0, no judge call): B3's S2, the estimate and the $0 checks before S3

Written 2026-11-01 night by the coordinator from brief 15 (S2; A6.8, A6.12, A6.13.8, A6.18, A6.21, A6.22), the committed plan `work/stage3/b3/plan.md` (4c677dee) and brief 27's record. Working directory: the project root `/Users/aravind/KruxAI/tais-project-selection`; the fork is `work/mole-fork` (branch `stage3`). S2 prices and checks; it applies nothing to any live document and sends no judge request (pricing is by token count from the packets each view would send, as Part 2 did).

**Aravind's decisions in force (A6.22):** T2+S2 confirmed; the controls' lone-line add-on approved; the k = 2 descriptive arm only if executionally clean; the $4 re-read approved as a sensitivity (not S2's).

## H0. Orientation ($0)
Read `plan.md` in full (it is the plan; where it and this brief differ, the plan governs and the difference is reported), brief 15 A6.8, A6.12, A6.13.8, A6.18 (b), A6.21 and A6.22, Part 2's estimate tables (`work/stage3/b3/power-simulation-v3b.md`, the layouts table) and brief 27's record (`lone-line-arm-v0.md`). Verify the plan's `s1-preflight-sha256` block with `shasum -c` from the project root and report the count (expected 24 OK); a mismatch is reported and S2 stops.

## H1. The estimate, re-based on the plan's units ($0)
For the committed layout (T2+S2; per view 232 item applications and 438 lone-line applications, net of brief 26's drops; live-view lone-line units stripped per A6.13.8), build the packets each view and judge would send (the per-agent views and `O_diff` under the judges the plan names), count tokens, and price them at the current rates by the same method as Part 2, per view and judge and in total; state the rates used and their source. Report the figure Aravind confirms, and **the stop at twice that figure** (A6.12). Compare with Part 2's $98.17 gross and the pro-rata $68 and explain any gap.

## H2. The controls' lone-line add-on, approved ($0 here)
Check at $0, through brief 27's harness in restricted mode (`build_parts_inserter(prefix_rw_v2c.jsonl, org_template.yaml, inserter-dry-run-v0.json)`), each of the 21 controls' three lines under the candidates' lone-line need (two valid draws by different authors, the control's own authors excluded) on **stream tag 6**; report per control by opaque id how many lines meet the need; a control short of its need leaves the add-on only (not the control arm), with its reason. Price the add-on's units (expected about $15) and add them to H1's total as a separate line.

## H3. The k = 2 descriptive arm, priced and tested for cleanness ($0 here)
Price A6.3 (d)'s k = 2 arm as the plan describes it, and apply the **cleanness test of A6.22 (3)**: (i) no new application code is needed (the module as at 240f4ed9 can produce the arm); (ii) no new arm or seed-stream change beyond **tag 5**; (iii) its valid draws can be checked at $0 through brief 27's harness as in H2, and are. If any of (i) to (iii) fails, the arm is skipped by a dated note in the S2 record citing Aravind's words ("only if it's executionally clean i.e. if it complicates the run, let's skip it"); if all pass, report its price as a separate line for his decision.

## H4. Outputs
`work/stage3/b3/s2-estimate-v0.{md,json}`: the pre-flight count; H1's table per view and judge with rates and totals, the confirmation figure and the stop; H2's per-control check and the add-on's price; H3's cleanness test and price or skip note; the plan's hash cited. One STATUS line; the fork mirror under `results/stage3/b3/`; this brief's row in `briefs/INDEX.md`. S3 opens only after Aravind confirms H1's figure, brief 31 is done, and the S3 brief is written.

**Do not:** send any judge request; apply anything to a live document; change any pinned file; print any item line, document text or rubric (counts, ids and hashes only); open red/, persona, rater-key or sealed pilot files.

**Done means:** the pre-flight verifies; the estimate and stop are stated with their rates; H2 and H3 are reported as above; the record exists with its hash in STATUS.

---
Changelog: 2026-11-01 night, written by the coordinator from A6.22.
