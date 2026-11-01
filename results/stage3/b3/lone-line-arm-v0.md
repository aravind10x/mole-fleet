# Brief 27: the lone-line arm and the valid-draw restriction in the edit-application module (blue; ids, counts and hashes only)

**Done, $0, no API call.** The lone-line arm (E1) and the opt-in valid-draw restriction (E2) are in `work/checks/stage3_t1.py`, together with application isolation, stated and tested (E3). The three existing arms are byte-identical in default mode: the T1 v3 replay matches on 128 of 128 applications, by records and by produced documents. E4 reproduces brief 26 exactly. (a) Brief 26's script, unchanged, run against the final module gives 0 differences: drop lists 8 and 2, and all 124 item and 234 lone-line valid-draw sets equal. (b) Through the new arm, all 4,537 listed lone-line draws are accepted, and 233 of 234 lines have two valid draws by different authors. A6.17.11's Step 0 is therefore **not** re-triggered. Three Codex review rounds produced 5 required fixes and 2 optional ones, all made. No item line, anchor, rubric, declared effect or document text appears in this file or any output (brief 26's guard refused any output containing one).

Executed: brief 27 v3 (c2bbf0af at the start; the coordinator added a dated note during the session, now c418550e: the per-item pairs are `items[].draws.valid_draws` (`valid_by_day` holds counts), and "3 of the 8" is corrected to 6 with valid draws on one day only plus 2 with none, the figures this session's tests assert). Session: Opus 5.5 in Claude Code. One reply in the session was cut by a safety-classifier stop while it was taking in the round-1 findings. No file or run was affected; the work resumed from the findings.

## Module hashes (E0, E1)

| | before | after |
|---|---|---|
| `work/checks/stage3_t1.py` sha256 | `52a79312b1e2ce4618451e620c766c1e5aabe6b93cbde0f59a22aa72ed0d96e2` (fork `scripts/stage3/stage3_t1.py` at e3409b9, identical) | `240f4ed9465bf61c021e1c993371ef74f3167bd1ce7378c251da73a5196ac4b5` (fork copy identical) |
| application class `Inserter` sha256 (`inspect.getsource`, the T1 v3 manifest's rule) | `24d3d147d6f5e6a052820714dfefebe2442aaeaf5f796cf299fe319c41027b4a` | `24d3d147…` **unchanged** (= T1 v3 manifest; `test_stage3_t1replant_score.py:81` still passes) |
| `PartSInserter` (new subclass: the lone-line arm and the restriction) | none | `5e6371ee019f749e87053dea22033d9a2a5c69e874ac038b856cd93770c71451` |
| `PlantResult` | `453f661c5b93ff3167ca5c426c0efd0c197569860b0d6bbda6a76b07b613e252` | `b538711bbf71c281eba4bfe7c7aa7bc2259874a033af8f475ec3164463c0c3ee` |
| `ValidDraws` / `Refused` (new) | none | `47496d1b…` / `64c2c5ea…` |

**The diff is confined to the new arm and the opt-in restriction:** 412 lines added and 3 removed, in 9 difflib hunks, none inside `Inserter` (a test asserts this). By hunk:
- **Module docstring:** a paragraph for brief 27, which states the isolation assumption.
- **Constants:** `LINE_ARMS` and `TIME_SAMPLES`.
- **`PlantResult`:** a `refused_draws` field and a `line_index` property. `delivered` uses n = 1 for a line arm, and `record()` adds `line_index` for a line arm and `refused_draws` when non-empty. For the three arms the records are unchanged.
- **New section after `Inserter`:** the refusal codes, `intended_document`, `application_reason`, `compatible_pairs`, `ValidDraws`, `Refused` and `PartSInserter`.
- **New function:** `build_parts_inserter`.

The three removed lines are `delivered`'s docstring and return line, and `record()`'s `return {` (now `rec = {`). All 17 module lines that brief 26's `module_line` cites are still unique; they moved (M1 to 364, 366 and 684, M4 to 607, 828 and 1329, M5 to 535 to 602).

## What the module now has

- **Lone-line arm (E1).** `LINE_ARMS = ("line0", "line1", "line2")`, one arm per line role index. `_plant_once` runs on the item's full three-line list with `_roles(line_i) = [[i]]`. The line's role index is therefore its statement index, recorded as `line_index`, and the event ids carry the arm. Every rule of the three-line arms applies through the same code: the lone arm's day draw `rng.choice(days[:2])`, `draw_author`'s pool (team template, managers excluded, F4 anchored sessions, F3 touching sessions first), the whole-write floor, F1 read before edit, F2 redundant delivery only where it re-lands, and `Inserter.plant`'s re-draw rule. A test shows the line arm's layout equals the lone arm's layout of a payload made of that line alone, for 25 seeds and each line, with the draw log included. The line is placed on its own author (A6.5 (iii)): the triple's authors are a **required** argument of every line-arm call (`exclude`; `None` raises, `()` states there are none). Composition for a line means the line is present at its time and at the end of its day.
- **Valid-draw restriction (E2), active only when a valid-draws table is passed** (`ValidDraws`: brief 26's `items[].draws.valid_draws` pairs, with `valid_by_day` checked as per-day counts, and `items[].lone_lines[i].valid_draws`, keyed by opaque id). In restricted mode:
  - **(i) Draws:** every seeded draw comes from the listed pairs (minus excluded authors), sorted and drawn by `rng.choice`. A listed author must also be in the module's own pool for that day.
  - **(ii) Checks at the drawn state:** every delivered edit, redundant deliveries included, is checked against the document just before its row. The target must be found exactly once (one line starting with the anchor, and that line occurring once in the text), the line must not already be present, and the row's document must equal `intended_document` (line in place by line index, brief 26's rule). Then the lines must compose.
  - **(iii) Refusal:** a draw outside the list, an excluded author, an author outside the pool, a failed check, a session with no time left after 12 samples, or an edit the manager's rule rejects each raise `Refused` (reason codes only). No restricted path returns a delivered or last layout. `plant` keeps `Inserter.plant`'s re-draw and clean-draw rule over listed draws, removes a refused draw from the candidates, and refuses when none passes. `plant_pair` is Part S's pair: for an item, two draws on different days by different authors; for a lone line, two by different authors, none of them excluded. It enumerates every compatible pair and draws one, and it is refused outright when the list cannot supply a pair, even where single draws are valid. k = 2 and k = 3 have no listed draws and are refused.

  In default mode (no table) the module draws exactly as before, which is what E1's replay relies on. S1 and S3 must always pass the file (`build_parts_inserter(corpus, template, valid_draws)`).
- **Limitation, by design:** restricted mode checks the state actually drawn. Brief 26's validity also covered every state the drawn sessions can reach, and the list carries that. The list was built without excluding the triple's authors, so under an exclusion restricted mode can have fewer candidates than default mode. Brief 26 counts 3 lone lines with at most three valid authors, where that can bite. `PlantResult.record()` contains line text: hash records, never export them (Codex, round 1).

## E3: application isolation

**The assumption:** each application is made on its own copy of the document state, so no two applications of an item share a state. **The code:** `Inserter._plant_once`, `rows = copy.deepcopy(self.rows)` (`stage3_t1.py` line 610), on the null's rows. Every edit, read row and rebuilt routine edit goes into that copy. `PartSInserter` adds no shared state besides the read-only table, and its exclusion attribute is reset after each call. `_anchored_cache` and the session tables are computed from the null only. **Finding: the module makes its own copy, so no fix was needed.**

**Tests:**
- **Fixture:** the triple, then each of its three lines alone, on the same day in one instance. Each produced document carries only its own lines, and no check reports "already present". The five row lists are distinct objects with disjoint row dicts, the null rows hash the same before and after, and the applications run in reverse order give identical documents and records.
- **B3 candidate:** one candidate's triple and its three lines alone on one day, at listed draws, the lines on authors other than the triple's. Each document carries only its own lines.

## E1: the default-mode replay (T1 v3 manifest)

`plant_all` ran on `work/stage3/t1v3/payloads-v3-planting.json` with seed 20261128, the manifest's plan seed; the corpus and payloads were checked against the manifest's hashes. Three variants were run:
- the pre-change module (`git show e3409b9:scripts/stage3/stage3_t1.py`, sha256 verified as 52a79312), class `Inserter`;
- the new module's `Inserter`;
- the new module's `PartSInserter` with no table.

| | pre-change | new `Inserter` | new `PartSInserter` (default) |
|---|---|---|---|
| applications (lone / k2 / k3) | 128 (48 / 48 / 32) | 128 | 128 |
| records' sha256 (`plants_sha256`) | `152fa709…` | `152fa709…` | `152fa709…` (= manifest) |
| per-application record and rows (every document state) hashes equal | | 128 / 128 | 128 / 128 |

The pytest version (`test_full_replay_of_the_t1v3_manifest`, run when `STAGE3_FULL_REPLAY=1`) passes; see Tests.

## E4: reproduction of brief 26

| check | brief 26 (edd289ce) | brief 27 | differences |
|---|---|---|---|
| (a) drop list, pair rule | 8 ids | the same 8 | 0 |
| (a) drop list, literal count | 2 ids | the same 2 | 0 |
| (a) net n's (78 / 28 / 19 / 21 / controls / comparison) | 73 / 26 / 17 / 20 / 21 / 22 | 73 / 26 / 17 / 20 / 21 / 22 | 0 |
| (a) item valid-draw sets | 124 | 124 equal | 0 |
| (a) lone-line valid-draw sets | 234 | 234 equal | 0 |
| (a) every other section (items, aggregates, totals, lone_lines, reverse case, nine members, rule, inputs, script) | | equal | 0 (only module hash, date and cited line numbers differ; finding counts equal) |
| (b) listed lone-line draws accepted by the new arm (restricted, 2 samples each) | 4,537 listed | 4,537 accepted, 0 refused | 0 |
| (b) lone lines with two valid draws by different authors | 233 of 234 | 233 of 234 (the one short: `80040659…` line 1, 0 listed) | 0 |
| (b) literal two valid | 233 | 233 | 0 |
| (b) drawable draws per line | 4,692 | 4,692 | 0 |
| (b) first sample identical to default mode at the same draw and seed | | 4,537 / 4,537 | 0 |
| beside: listed item draws accepted by the restricted lone arm (2 samples) | 2,180 listed | 2,180 accepted, 0 refused; identical to default 2,180 / 2,180 | 0 |
| beside: Part S's pair selection (`plant_pair`) on all 124 | 8 drops | refused for exactly the 8 ("the valid set cannot supply the pair"), accepted for 116 | 0 |

- (a): `work/checks/stage3_b3_inserter_dry_run.py` 999cb737, unchanged, run with `--out-dir work/stage3/b3/lone-line-arm/dryrun` on 11 processes (839 s). Output `inserter-dry-run-v0.json` 988d965c, `.md` 2a6e3e9e; brief 26's edd289ce is untouched. An earlier run on the intermediate module 0d5a0e05 also gave 0 differences.
- (b) beside: the drawable draws brief 26 did not list (155 for lines, 307 for items) were applied in default mode and read by the arm's own check at the drawn state.
  - Lines: 154 refused (81 no time left, 58 target found more than once, 15 an applied line changed before the composition check) and 1 passing.
  - Items: 306 refused (185, 96 and 25 for the same three reasons) and 1 passing.
  - Each passing draw fails brief 26's stronger enumeration at another reachable state or sample. These are diagnostics, not differences.
- **No dead end (A6.17.11):** (a) changed neither the drop list nor any valid-draw set, so Step 0 is not re-run.

## E2 tests named in the brief

- a draw outside the valid set is refused: `test_a_draw_outside_the_valid_set_is_refused`, `test_every_restricted_draw_comes_from_the_valid_set`;
- a non-unique target is refused, where default mode applies it: `test_a_non_unique_target_is_refused_where_default_mode_lands`, plus a re-landed redundant delivery at a non-unique state;
- each of the 8 dropped items is refused at the pair selection: by the table alone (`test_brief_26s_file_loads_and_the_eight_dropped_items_are_refused_at_the_pair_selection`, which also asserts 6 with valid draws on one day only and 2 with none) and by the restricted module (`test_the_eight_dropped_items_are_refused_by_the_restricted_inserter`);
- each of the nine `anchors_resolve`-false stratum members is accepted on both days, and as a pair: `test_the_nine_unresolved_anchor_members_are_accepted_on_both_days`;
- restricted mode at a valid draw gives the identical document and record: `test_restricted_mode_at_a_valid_draw_is_default_mode` (default and restricted `apply_at`, dup on and off, 80+ draws) and `test_a_restricted_record_carries_the_draw_log_of_its_own_draw` (default layout then application, against restricted application with the same rng state; the draw log included); on the B3 data, 6,717 of 6,717 listed draws (E4 above).

## Tests

- **`test_stage3_t1_line_arm.py`:** 29 tests. 24 run on the fixture, 4 on brief 26's file and the B3 items (skipped when absent), and 1 is the gated full replay. All pass, the full replay included (`STAGE3_FULL_REPLAY=1`).
  - Every test that drives a new behaviour was written first and seen to fail.
  - `test_a_line_changed_later_the_same_day_is_refused` was added during the final runs as coverage of existing behaviour, so it passed on first run.
- **`test_stage3_b3_lone_line_check.py`:** 7 tests, all pass.
  - They cover differences counted by reason, duplicate ids, the pre-change source, the diff staying outside `Inserter`, and the provenance checks.
  - The harness was written before its tests, which were added after it.
- **Related suites, unchanged and passing:** `test_stage3_t1.py`, `test_stage3_b3_inserter_dry_run.py`, `test_stage3_t1replant_score.py` and the fork-copy test (with the three new files added to its list).
- **Full `work/checks` suite on the final code:** 1,024 passed, 1 skipped (the gated full replay, which passes on its own: 1 passed in 227 s), 2 failed. Both failures predate this brief and do not involve the module: `test_stage3_t1v3_score.py::test_binding_check_accepts_only_the_disclosed_judge_client_hashes` (`judge_client.py` changed on 31 Oct, fork 3ac319a, and its hash is not in the accepted list) and `test_stage3_write_yield.py::test_propose_raises_write_counts_until_every_document_clears_the_target_and_keeps_reads` (imports only `stage3_rung1_class` and `stage3_write_yield`). Both are left for the coordinator.

## Review record (E5)

Codex gpt-6.1-sol, reasoning effort high, read-only. Brief 20's information barrier applied: no item, rater, red, cache or T1 directories were read, and the tests that load item files were deselected. Prompts and answers are in `work/stage3/b3/review/codex-brief27-{prompt-,}round{1,2,3}.md`.

| round | findings | fixes made (each test-first) |
|---|---|---|
| 1 | 4 required, 2 optional; design decisions 1 to 6 and 8 to 12 right or partial, 7 wrong | (1) every delivered edit is checked, redundant deliveries included; (2) `apply_at` requires the exclusion for a line arm; (3) `apply_at` records its own draw's log (read through `draw_author` with a stand-in that draws nothing), and restricted mode requires the author to be in the module's pool; (4) every harness part carries a fingerprint (module, harness, table, brief 26 script) that `report` checks; optional: duplicate ids counted as a difference; the manager's rule rejecting an edit is a refusal in restricted mode |
| 2 | 1 required: the fingerprint was taken after the run | the fingerprint is taken at import; `main` refuses if the inputs changed before the start, `write_part` refuses to save if they changed by the end |
| 3 | none required; residual noted: an input changed and changed back mid-run is undetected | inputs were held fixed during the final runs; their hashes were compared before and after the chain ("inputs unchanged") |

Round 3's verdict: "safe to commit and use for S1 and S3 once the final-module replay and E4 runs pass, with inputs held unchanged throughout those runs". They passed.

## Outputs and hashes

- Module `work/checks/stage3_t1.py` `240f4ed9465bf61c021e1c993371ef74f3167bd1ce7378c251da73a5196ac4b5`; tests `test_stage3_t1_line_arm.py` `0ee5057bcb59037a3fa16e821bda495f810e38e189ab79e0a1eda8917c94559f`.
- Harness `work/checks/stage3_b3_lone_line_check.py` `070212f7dfb417d808b242df4aa7900ed11a6be27cb0042609291d37332f03f6`; tests `test_stage3_b3_lone_line_check.py` `46dbee10a40380ae9c78f495b4114b2ae598d3d64b6b54c4f72ece224f8aceba`.
- Record data `work/stage3/b3/lone-line-arm-v0.json` `ebfb7c6dbc6b896d3b6c4d3f2bbc9a85c44bd06780e81d8b00e8078bcc5125dd`; parts `work/stage3/b3/lone-line-arm/{replay,dryrun,lines,items}.json` `00297994…`, `10b934ae…`, `4cc080cc…`, `06db9d45…`, all fingerprinted with the hashes above, the table `edd289ce…` and brief 26's script `999cb737…`.
- Seeds: the check's timestamp samples use `b27-lone-line-check-20261101`. This is not Part S's stream; S1 writes that.
- Mirrors: code under the fork's `scripts/stage3/`, this record, its data, the parts and the review files under `results/stage3/b3/`.
