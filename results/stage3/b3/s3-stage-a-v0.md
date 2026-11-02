# S3 Stage A record (brief 33 v2.1, 99e3ec7f): the $0 stage before the gate — written 2026-11-02 06:42Z

Blue session (Fable 5.1). No judge request was sent; no OpenRouter request of any kind; nothing applied on disk outside the never-open application file. Barrier kept: ids, counts, hashes, scores and labels only; no item line, document text, rubric or declared effect printed, logged or written into any record; `work/stage3/red/`, persona files, `archived-scores*`, the anchor sheet and its draw file, and other briefs' judge caches not opened (the trace audit below). Every path is from the project root.

## A1. Pre-flight and the stream set

- Configuration `work/stage3/b3/s3-config-v0.json` (e28dca16): placement seed 20261181, bootstrap 20261152 x 2000, tie 20261112, m_s 18.22 and 19.37, m_L 18.22, arm seeds {'1': 2026118110, '2': 2026118120, '3': 2026118130, '4': 2026118140, '6': 2026118160} (exactly the tags 1, 2, 3, 4 and 6; no tag 5).
- Before A1b's note: `stage3_b3_preflight.py --config` **PASS**, 26 of 26 files, 3 prompt components, value mismatches []; plan.md 58b0c121 equal to the fork's HEAD copy (True). Output kept as `s3-preflight-v0-prenote.json` (d2adf6bc).
- The driver asserts the stream set itself (`stage3_b3_s3.assert_arm_seeds`, tested: a tag 5, a missing tag 6 and a wrong value each refuse).

## A1b. The dated note on the plan

- Appended verbatim under the heading the brief gives, 2026-11-02; `work/stage3/b3/plan.md` **59a98c15** (119961 bytes; its first 111,603 bytes hash to 58b0c121, so nothing above the note changed); mirrored to `results/stage3/b3/plan.md` and committed to the fork (be0a600); the `s1-preflight-sha256` block is unchanged (26 lines).
- Pre-flight re-run after the commit: PASS, 26 of 26 (the run of that time, 03ed1816). After the dated note 3 of 2026-11-02 (the addendum below) the current run is **PASS**, 27 of 27, plan.md 59a98c15 matches HEAD (True); `s3-preflight-v0.json` (8e332d9b). `test_stage3_b3_preflight.py` 10 pass.

## A2. The analysis matrix, the readings script and the dry run

- Matrix `work/stage3/b3/s3-analysis-matrix-v0.json` **1b80280a** by `stage3_b3_s3_matrix.py` (4d682443; tests b69ba67d, 11 pass): 116 net items (73 candidates, 21 control items, 22 comparison items) keyed by opaque id; every input verified by sha256 before it is read (the seven files of 9a769d68 `inputs_sha256`, stratum-v0.json 6113bd8d, s1-populations-v0.json f17e7a72, inserter-dry-run-v1.json 02138931, and the four payload and control files pinned in v1's `inputs_sha256`, read for each statement's `op` only); section 1.2's table reproduced (means, SD, IQR, writer and document counts, pooled strata; tested against s1-populations-v0.json and Part 3's Step 0 to 1e-3); the candidates' rater fields equal brief 25's file; no item text (tested).
- Readings script `stage3_b3_s3_readings.py` **c7e14a58** (tests efa39b0d); dry run `stage3_b3_s3_dryrun.py` (cd5b683e); report `s3-readings-dryrun-v0.md` (3a56fd2b) and `.json` (357422ca).
- The exception table against Part 3's simulator, each delta tested: replicate failure more than 10 percent of 2,000 (not 2.5 percent); form (b) with the top-two gap (the note); the floor once on the full set against the sham; 2,000 replicates at seed 20261152 (not 1,000); the fixed quartiles 47.5 and 66.5 for every population; the cascade as seven ordered steps; a rank-deficient design is a fit failure (the simulator's fitter converges on one; tested).
- Reachability: 33 fixtures, all reaching their ids: **True**; ids not reached by any fixture: none; S-P1 unreachable by decision (the k = 2 arm is not run); S4-1 by the separate session after Aravind reports. Wall time 445 s.
- Operating characteristics through the adapter (seed 20261171, tag 500, ICC 0.3, 300 experiments per truth, 2000 replicates; one stream per experiment: default_rng([20261171, 500, truth index, model index, experiment index])): the carrier's P(excluded | 0) on the subset under the "none" model **0.640** against Part 3's 0.68; P(present | 1.5 x) **0.730** against 0.72; tolerance ± 0.08: **ACCEPTED**. The full set under the "zero" model beside, named in the report. Wall time 1031 s.

## A3. The draws and the application set, once

- (i) Payload and control files verified against v1's `inputs_sha256` before the draw; the applied id sets hash to section 1.1's values (full 73 (5dbd067d), controls 21 (3db4d199), sham 22 (27909dc2)).
- (ii) Brief 27's harness copied with an opt-in (`stage3_b3_lone_line_check_s3.py` 80e35721; tests f0f5f3eb, 28 pass with the gated reproduction): default mode reproduces the candidates' 4537 of 4537 (True); the control items through v1: net 21 items, 63 lines, **1231 of 1231 listed draws accepted**, refused none; gross 22: 1271 of 1271; record `s3-lone-line-check-v0.json` (8f64fb7e).
- The draw: module 240f4ed9 in restricted mode on `inserter-dry-run-v1.json` 02138931, corpus ffc1f6cd, template 294d59d2; arm seeds {'1': 2026118110, '2': 2026118120, '3': 2026118130, '4': 2026118140, '6': 2026118160}; window ['2026-04-06', '2026-04-07', '2026-04-08'] (the corpus span (build_world); units as planted_items). Units: items 232 (expected 232), lines 564 (expected 564); by regime: candidate items 146, control items 42, comparison items 44, candidate lines 438, control lines 126; counts equal the plan's: **True**; by stream tag {'tag1': 146, 'tag2': 438, 'tag3': 42, 'tag4': 44, 'tag6': 126}; by day {'2026-04-06': 319, '2026-04-07': 477}; by writer {'glm53:items': 90, 'glm53:lines': 270, 'sonnet55:items': 98, 'sonnet55:lines': 294, 't1v2:items': 44}.
- Refused draws at application time (section 2.4 (3), the next draw of the same stream): none; re-draws per application {'0': 748, '2': 4, '4': 2, '5': 2, '7': 2, '9': 2, '10': 36} (the module's own rule, section 2.3: a draw that broke no honest edit is preferred for the first 10 re-draws; 36 applications reached 10 and 31 applications in all carry a broken honest edit, rebuilt by the module as T1 v3 did). Every application delivered and composed: True. Items whose two applications are by different authors on different days: 116 of 116. S3's own drops: **0** ; control items leaving the add-on: **0**.
- `s3-applications-v0.json` **02edac2a** (never-open: applied document states and packets; 796 units); record `s3-applications-v0.md` (d8778718). Wall time 626 s.

### A3b. Applications that broke a later honest edit (G2; `honest_edits_broken` > 0; counts only)

| group | item applications | lone-line applications | all applications |
|---|---|---|---|
| candidates | 11 of 146 (0.075) | 14 of 438 (0.032) | 25 of 584 (0.043) |
| control items | 3 of 42 (0.071) | 2 of 126 (0.016) | 5 of 168 (0.030) |
| comparison items (sham) | 1 of 44 (0.023) | 0 of 0 | 1 of 44 (0.023) |
| resolved-anchor subset (17) | 3 of 34 (0.088) | 4 of 102 (0.039) | 7 of 136 (0.051) |
| comprehension-quiet stratum (26) | 4 of 52 (0.077) | 4 of 156 (0.026) | 8 of 208 (0.038) |
| full quiet set (73) | 11 of 146 (0.075) | 14 of 438 (0.032) | 25 of 584 (0.043) |
| **all** | 15 of 232 (0.065) | 16 of 564 (0.028) | 31 of 796 (0.039) |

By stream tag: {1: 11, 2: 14, 3: 3, 4: 1, 6: 2}; items with at least one such application: 10 of 116 (the exclusion set for G6, `s3-clean-items-v0.json`, ids sha256 1e9d8022; by population {'subset': {'n': 17, 'touched': 2, 'clean': 15}, 'stratum': {'n': 26, 'touched': 3, 'clean': 23}, 'full': {'n': 73, 'touched': 7, 'clean': 66}, 'controls': {'n': 21, 'touched': 2, 'clean': 19}, 'sham': {'n': 22, 'touched': 1, 'clean': 21}}). Every such application was delivered and composed; the module rebuilt the later honest edit's content as T1 v3's rule does (section 2.3), which the dossier and `O_diff` views then read.

## A4. The driver, the packets, the caches and the pre-signal

- Driver `stage3_b3_s3.py` **1105e1ee** (tests 0d946943): modes apply | render | score; the ledger (one guard through `request_guard` on every client, in-flight reservations, the stop at $153.25, each client's own cap the stop less the other caches), the view order enforced, the pause after the first about 20 carrier units, resumable state, the scores file's flag through `stage3_thresholds.is_flagged` at the sealed rule (tested).
- Packets (`s3-render-v0.json` 7c33c104): cache labels unique within S3: True (4344 labels); caches to live under `work/stage3/b3/cache-s3/`, none before Stage B (tested).

| row | units (items + lines) | packets sha256 | pre-signal estimate | S2 at Part 2's basis | truncated |
|---|---|---|---|---|---|
| P_author_doc_iso|opus48 | 796 (232 + 564) | 56f1eefa | $13.17 | $35.59 | 0 |
| P_author|opus48 | 796 (232 + 564) | 97037737 | $11.74 | $10.34 | 0 |
| P_author_doc_iso|sonnet | 796 (232 + 564) | 56f1eefa | $4.31 | $4.75 | 0 |
| P_author|sonnet | 796 (232 + 564) | 97037737 | $3.74 | $2.69 | 0 |
| P_author_doc_live|opus48 | 232 (232 + 0) | ab4f2ba0 | $4.98 | $10.60 | 0 |
| P_author_doc_live|sonnet | 232 (232 + 0) | ab4f2ba0 | $1.71 | $1.94 | 0 |
| O_diff|sonnet | 232 (232 + 0) | 19f2a1ea | $1.32 | $1.39 | 0 |
| O_diff|opus48 | 232 (232 + 0) | 19f2a1ea | $6.41 | $7.74 | 0 |
| O_diff|sol | 232 (232 + 0) | 19f2a1ea | $1.50 | $1.58 | 0 |
| **total** | | | **$48.87** | $76.62 | |

- Pre-signal total **$48.87** beside S2's $76.62 (ratio 0.638); exceeds the figure by more than a third: **False**. a pre-signal only: no exact token count exists before a request is sent; the exact count and the re-base are B1's (the plan's note of 2026-11-02, item 4).

## Trace audit (Stage A)

- `stage3_b3_s3_trace_audit.py` (af2bf444; tests 84e5069a, 7 pass, the positive test bound to the empty `--writer-dir`) around the pinned script 2a409344 on this session's transcript `2043475e-6037-4bb9-8224-930e8d98c3c5.jsonl` with `--writer-dir work/stage3/b3/s3-trace-empty` (empty; every token absolutised first) and the policy `s3-trace-policy.json` (8c85a469): opened 186, allowed 109, outside 77 (existing files 0, non-existent tokens 77), **never-open 0**; verdict PASS.

## Stage A addendum (brief 33's dated notes 2 and 3 of 2026-11-02; $0, no judge request)

- **G1 revised (the flag).** plan.md's dated note 3 of 2026-11-02 (plan.md **59a98c15**, fork 1fafa57; prefix bytes equal to a411d8a2): the flag is the sealed author-level reading, the union (B1's primary, `recall_by_arm` and `flagged_union`), the planted unit's own flag beside; section 4.1's form (b) null bias stands, nothing re-simulated; `work/stage3/views/p_author_c0.json` (3c61dd4d, the 89 honest `P_author` rows of Sonnet 5's calibration) pinned, the `s1-preflight-sha256` block restated at 27 entries; `test_stage3_b3_preflight.py` asserts 27 by a dated comment. Pre-flight on the committed plan: **PASS 27 of 27** (`s3-preflight-v0.json` 8e332d9b). The driver (`stage3_b3_s3.py` 1105e1ee) flags through the union (`honest_pairs_for`, `union_max`, B1's `honest_pairs`) and the scores file carries `flag` (union) and `flag_unit` per unit; the readings script reads both: floor (b), the ceiling, the anchors' lone recall and the composed gaps on the union with the unit's own flag beside. G1 (a)'s re-simulation artefacts were discarded uncommitted.
- **G3.** An instrument at floor (a) is not read: `Instrument.read` takes the floor (a) result and returns `not_read` "floor" for both forms with no label; `select` issues only its floor sentence (S-A2); the `floor_carrier` fixture asserts the absence of every other id for that instrument.
- **G4.** S-G1 beside every *excluded* or *attenuated* reading, every instrument, form and population (S-D and S-R), once per reading (the S-F duplicate removed); tested.
- **G5.** (i) A unit still errored after the client's retries is unscored (the note's rule 1) and completes its cell (`cell_status`); `--continue` clears a recorded stop (`clear_stop`, kept on the run record). (ii) The first-batch re-base compares the about 20 item units' realised cost with those same units' character-based estimate (`estimate_cell` on the batch), the whole cell's per-unit estimate shown beside; tested.
- **G6.** Beside the carrier's form (a) reading, form (a) on the items none of whose applications broke a later honest edit: the exclusion set `s3-clean-items-v0.json` (21e7ede2; 10 touched items, ids sha256 1e9d8022; subset 15 of 17 clean, stratum 23 of 26, full set 66 of 73) is written by the A3b script from the application file and read by `--clean-items`; sentences S-G6 and S-G6b (descriptive, counts, no label, no effect on the cascade); two fixtures reach them.
- **O1 to O8.** O1 precedence in `read()` (floor, ceiling, fit); O2 an unscored application, not its item, leaves the anchors' and the floor's sham denominators; O3 the dry run's carrier figures beside Part 3's in `b3-results.md`; O4 the descriptive marker on S-D outside the verdict population; O5 value tests for the slot arithmetic; O6 the bootstrap sub-stream rule stated in `b3-results.md`; O7 `secondary()` pools strata as section 4.3 does; O8 `s_e()`'s wording when form (a) is unfit and form (b) fitted. O9: the differences list names the union as B1's primary.
- **Re-runs.** Readings script `stage3_b3_s3_readings.py` **c7e14a58** (tests efa39b0d); dry run `stage3_b3_s3_dryrun.py` cd5b683e: 33 fixtures, all reaching their ids **True**, ids not reached none; report `s3-readings-dryrun-v0.md` 3a56fd2b.
- **Operating characteristics re-run** (form (a) untouched): the carrier on the subset P(excluded | 0) **0.640**, P(excluded | margin) **0.090**, P(LB > 0 | 0) 0.023, P(present | 1.5 x) **0.730**; acceptance ACCEPTED (the first run gave 0.640 / 0.090 / 0.023 / 0.730: unchanged). Beside Part 3's 0.68 / 0.07 / 0.03 / 0.72; bound (ii) 0.6 Monte Carlo SE below 0.10 against Part 3's 1.8 (section 7, A6.18 (e)).
- **Trace audit (end of the pass)**: opened 222, allowed 124, outside 98 (existing files 0), **never-open 0**; verdict PASS (`s3-trace-audit-stageA2.json` 5e232276).
- **Disclosures corrected (the coordinator's dated note 2).** The pre-signal's carrier gap is not thinking tokens (Opus 4.8's thinking is inside `output_tokens`, as B1's bases were): S2's carrier basis was B4-R's $0.0447 per unit on the other prefix against B1's realised $0.01743 on this prefix, and the pre-signal is 0.95 of B1's realised, so the realised cost is likely near $49 with wide headroom under the stop; B1's re-base still decides. The executor was Fable 5.1.

## Stage A addendum 2 (brief 33-B Part 1: brief 33's dated notes 4 and 5 of 2026-11-02; a fresh session, Fable 5.1; $0, no judge request)

- **G7 (an errored unit is not final at its first error).** Driver `stage3_b3_s3.py` **1105e1ee** (tests 0d946943): `cell_status` counts a unit with one errored record and no scored or refused one as `errored_once` (the cell stays incomplete, so `run_cells` stops at the cell's end with the stop recorded, its cause named: `errored_once`, `missing`, `g7_only`); the coordinator's `--continue` clears the stop and the client re-asks that unit once (an errored record is never served from the cache; the note's rule (e)); a second errored record makes it `errored_final`, unscored, which completes the cell. The scores file writes an open unit as `errored_open` (absent from a stopped file's rows, whose cell the stop record names) and a final one as `errored`; a cell is complete with every unit scored, refused or errored. `clear_stop` counts the G7-only continues per cell in the run record (`g7_continues`; dated note 5: once per cell by the executor under the ledger, every other stop and B1's pause waiting for the coordinator). Tests for one and for two errored records, for the stop's cause and for the count; the rulings line restored.
- **G8 (no S-M sentence without a lead).** Readings script `stage3_b3_s3_readings.py` **c7e14a58** (tests efa39b0d): the S-M block issues only under the cascade's lead and never with the lead at floor (a); the `floor_both` fixture forbids every S-M, S-D, S-E, S-G, S-K, S-L and S-O sentence for C or S, checked by family (the dry run's forbidden entries match by id or family and instrument; `forbidden_present`).
- **G9 (the union's keys against the application file; dated note 5's rule).** `stage3_b3_s3.py check` writes `s3-honest-pairs-check-v0.json` (4ad97f7d; counts only; the application file 02edac2a, the corpus ffc1f6cd): every honest source holds 89 pairs over 40 authors and 6 documents (the author set identical across the six sources: True; the paths the six class documents: True); each per-agent row's 796 units are by 35 authors, the packet's author equal to the unit's in every unit (mismatches 0); documents absent 0; authors absent 2, of which 2 explained (accounts of the honest corpus with no successful class-document write there, so no null can hold a pair for them and their union is the unit's own flag, as in B1; 13 units) and 0 unexplained. Units with no honest pair on another class document: 73 of 796 on each per-agent row (60 by the author's single honest pair sitting on the planted document, 13 by the absent authors; unexplained 0); on each live row 26 of 232 (19 + 7); the counts identical across the four per-agent cells: True. Verdict: **PASS**. `score` and the readings refuse without a passing check of this application file; the readings write the disclosure into `b3-results.md` (dated note 5).
- **Adopted (a) to (c).** (a) `score` and the readings refuse unless `s3-clean-items-v0.json` is at 21e7ede2 (on disk 21e7ede2); (b) a missing `flag_unit` is read as missing, never as the union's; (c) d1 and d2 at floor (a) issue no S-A4 or S-A5 (the `floor_d_rows` fixture forbids them).
- **Dated note 5's O3 to O5.** O3 `b3-results.md`'s header names brief 33's dated note 3 as S-G6's source beside the plan; O4 S-G6b quotes the fit's own reason (too few items only when n is under 4); O5 the test counts below are by module.
- **Tests, by module** (`s3-test-counts-v0.json` 8c083865; cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q <module> -p no:cacheprovider (S3_FIXTURE_PROCS=6), one module at a time): `test_stage3_b3_s3.py` 22 passed, 1 skipped (1 s); `test_stage3_b3_s3_matrix.py` 11 passed (1 s); `test_stage3_b3_s3_readings.py` 62 passed (616 s); `test_stage3_b3_s3_trace_audit.py` 7 passed (0 s); `test_stage3_b3_lone_line_check_s3.py` 27 passed, 1 skipped (1 s); `test_stage3_b3_preflight.py` 10 passed (1 s); in all 139 passed, 2 skipped, failed 0.
- **Dry run re-run** (`stage3_b3_s3_dryrun.py` cd5b683e): 33 fixtures (the 30 plus `floor_d_rows`, `errored_twice_unscored` and `errored_once_stopped`), all reaching their ids **True**, forbidden entries present in none, ids not reached none; report `s3-readings-dryrun-v0.md` 3a56fd2b, `.json` 357422ca. The `errored_twice_unscored` fixture's carrier loses one subset item (n = 16); `errored_once_stopped`'s lock names the carrier's cell at 795 of 796 rows and the second instrument leads.
- **Operating characteristics, reported again** (form (a) and the floor untouched by this pass): the carrier on the subset P(excluded | 0) **0.640**, P(excluded | margin) **0.090**, P(LB > 0 | 0) 0.023, P(present | 1.5 x) **0.730**; acceptance ACCEPTED; unchanged from the first run's 0.640 / 0.090 / 0.023 / 0.730 (wall time 1031 s).
- **Pre-flight** with `--config`: **PASS 27 of 27** files plus 3 prompt components, plan.md 59a98c15 equal to the fork's HEAD copy (True); `s3-preflight-v0.json` 8e332d9b.
- **Trace audit (end of this pass; the fresh session's transcript `5cfad631-5c28-4c64-8607-c476fa7e1e42.jsonl`)**: opened 89, allowed 58, outside 31 (existing files 0, non-existent tokens 31), **never-open 0**; verdict PASS (`s3-trace-audit-stageA3.json` 97ae2bfb; the policy `s3-trace-policy.json` 8c85a469 regenerated by `policy` for this transcript, its categories unchanged in the wrapper af2bf444). The application file was read by script only (`check`, counts); the quarantined `handover-uncommitted-2026-11-02/` files were read for ideas and deleted after this pass's versions were committed.
- **Caches and requests.** `work/stage3/b3/cache-s3/` holds no file; no judge request and no OpenRouter request was sent. The executor was Fable 5.1 (the brief named Opus 5.5).

## Differences from the brief and the plan, reported

Each is a decision this session took where the brief, the plan or the code left a choice; the plan governs where it speaks.

- **The flag (revised by plan.md's dated note 3 of 2026-11-02; brief 33's dated note 2, G1).** The scores file's `flag` is the sealed author-level reading, the union, which is B1's primary (`recall_by_arm`, `flagged_union`: a plant counts as flagged when the author's maximum over the planted unit and the author's honest units on the other class documents passes the sealed rule, the tie keyed by the author); `flag_unit`, the planted unit's own flag (B1's `recall_planted_unit_only`), is carried beside in every reading. Stage A's first ruling had taken unit-only as B1's convention; it was not (O9), and the union is the reading every pre-registered number (B1's recall, Part 2's form (b) null bias) was computed under. Sonnet 5's honest `P_author` rows are `work/stage3/views/p_author_c0.json`, pinned by the note; the other rows are the pinned nulls'. `O_diff`'s flag is its unit rule.
- **A live row's form (b) takes the rater's section-2 maximum and top-two gap as its line covariates** (the live rows carry no lone-line units, A6.13.8); Part 2's T2 layout without singletons did the same (`experiment`, the `else` branch). Descriptive rows only.
- **The harness copy writes under its own directory** (`work/stage3/b3/s3-lone-line-check/`, record `s3-lone-line-check-v0.json`), never brief 27's `lone-line-arm/` parts or `lone-line-arm-v0.json` (K1, pinned); "default output unchanged" is read as unchanged numbers, shown by the gated reproduction test.
- **The matrix keeps each item's document path** (a class-document path, the disclosed class), not item text.
- **The operating characteristics seed one stream per experiment**, `default_rng([20261171, 500, truth index, model index, experiment index])`: the brief fixes the seed and the tag, the sub-key is this session's, so the experiments run in parallel. Each experiment reads the two named instruments through the readings script's own `Instrument` (the floor once on the full set, the plan's precedence), form (a)'s label tallied as Part 3's `a_outcome` does, form (b) beside.
- **The trace audit absolutises every transcript token against the project root** before the pinned script audits it, with the empty writer directory passed as an absolute path; otherwise the pinned script's location rule would allow any relative `work/stage3/b3/...` token under the empty directory. The positive test is bound to that choice. Tokens that are fragments of shell commands (non-existent paths) are counted apart from existing files.
- **An errored unit is re-asked once on a resumed run, then unscored** (brief 33's dated note 4, G7, restoring Stage A's first ruling; the note's rule 1 and (e)): one errored record after the client's retries keeps its cell incomplete, so the run stops at the cell's end with the stop recorded and its cause named; the coordinator's `--continue` (or, when the stop's only cause is such units and the ledger is under the stop, the executor's, once per cell, counted in the run record; dated note 5) clears the stop and re-asks that unit once, since it is neither scored nor refused; a second errored record makes it unscored and completes the cell, so one persistently errored unit cannot block the later cells. The first-batch re-base compares the about 20 item units' realised cost with those same units' character-based estimate (G5 (ii)), the whole cell's per-unit estimate shown beside.
- **The readings script was written before its tests**; its tests are the brief's reachability fixtures and the exception-table assertions, run RED first (six fixtures missed their ids on the first run and were tuned, as the dry-run report records) and GREEN after.
- **The fixtures' synthetic worlds use the committed matrix's covariates** (numbers and ids) with generated scores; a fixture that needs a covariate held constant overrides the matrix copy it passes to the script (stated per fixture in the report).

## Hashes

- `work/stage3/b3/s3-config-v0.json` e28dca16fa9c0c809cc61a5117f15ffa9cce97a73c6e8a42ea54e24e9a1d45cc
- `work/stage3/b3/s3-preflight-v0-prenote.json` d2adf6bccb927a5889c80274031a2c83efa989fcaa2c05a9af9636c6544e886d
- `work/stage3/b3/s3-preflight-v0.json` 8e332d9be1baacbef8a8ae2e807fad8b3e5d4728beb571b94873362df970c285
- `work/stage3/b3/plan.md` 59a98c155908c4727b20d60945b15d16bcaa1084bb009dca444059c5f78e22db
- `work/stage3/b3/s3-analysis-matrix-v0.json` 1b80280ad8ed14d1ec0fed26b7137d3cc50a055e8f41b19e52083439f5b3effe
- `work/stage3/b3/s3-readings-dryrun-v0.json` 357422cabbba1b5e94083b61e6eb14c76f7e4ba3a04048cd88190beb827ccd82
- `work/stage3/b3/s3-readings-dryrun-v0.md` 3a56fd2b47b23cdfa7a49327ea3c467a9422d899ed5839e6ec010bdcdff27d30
- `work/stage3/b3/s3-lone-line-check-v0.json` 8f64fb7ee24caaf68db82cf70633056bf95013f797001f95bfb87cef0e0f3dbe
- `work/stage3/b3/s3-applications-v0.json` 02edac2a88fbdd3d9cfd4404e496aac6991c2f917fd27ca191394dc225c229bc
- `work/stage3/b3/s3-applications-v0.md` d87787183713f5d253bf418adf0c2c824e1a57aa491f7c5c7904b4936a4d0d27
- `work/stage3/b3/s3-render-v0.json` 7c33c10433784bbbab57eca7640e9cd0f381dfff796cdf9157fdcd3700ee169f
- `work/stage3/b3/s3-trace-policy.json` 8c85a469828b1035e4fd9ed0646b64e8bf20a36e4dc5251194d69bcb6ec3d78a
- `work/stage3/b3/s3-trace-audit-stageA.json` e3119f8ddd594f111f311551001375ec149214ae92df376b93c1188b455c38e2
- `work/stage3/b3/s3-clean-items-v0.json` 21e7ede2b95b49af714d9339a96c5e63d2204df9964c3b43ddbddbe502616ae7
- `work/stage3/b3/s3-trace-audit-stageA2.json` 5e232276e78c320872162f7af0bd3188f72f751ad31fe59f0f158398dbe58f89
- `work/stage3/b3/s3-honest-pairs-check-v0.json` 4ad97f7d60d986f8a24e61a272fc2780b7cc204487e5ac7d77c2d7f24f5cc838
- `work/stage3/b3/s3-test-counts-v0.json` 8c083865a47f64d43b9c9563723b1d722f3ee23c316336b56505a10113c49da1
- `work/stage3/b3/s3-trace-audit-stageA3.json` 97ae2bfbed13c70d9e2219de83a3e69b222f856df45fec2b5e2eab41f96974c2
- `work/checks/stage3_b3_s3_matrix.py` 4d682443ae4373ff04573625b470f87c8334e89d32dcf00f33eb42d142d5fbbe
- `work/checks/test_stage3_b3_s3_matrix.py` b69ba67d5be15fe74cb0f01069783095758d86bcf2b8296ba1508b9ae57ea703
- `work/checks/stage3_b3_s3_readings.py` c7e14a580631d66a7f37216acb3412dd42ee6e97304c6662989eca1be6738693
- `work/checks/test_stage3_b3_s3_readings.py` efa39b0d56a1e4c07d86042d174a3eacd0d1a05cc86dc1217bd4da7c4a49e788
- `work/checks/stage3_b3_s3_dryrun.py` cd5b683e9de45f5e49d9f73299a3725f46e9c80c0c36c423432ced6b1dfa9f62
- `work/checks/stage3_b3_s3.py` 1105e1ee182b65a2686a0c82c0f1d0782d19aedbd25eb7f73e3c6aed0250fa21
- `work/checks/test_stage3_b3_s3.py` 0d946943e11735fa1fc9a7736c6e73f44c644c88dfce276226d50bfcab387b46
- `work/checks/stage3_b3_lone_line_check_s3.py` 80e357217e8bda7cd12514f2fc5593c416d34b2d200008f754a074e0ec66e01a
- `work/checks/test_stage3_b3_lone_line_check_s3.py` f0f5f3ebb91f99e10c58fccd17365ae5b904006bd458ca4be39269eacc348019
- `work/checks/stage3_b3_s3_trace_audit.py` af2bf444b398b03caac349f1958c315de1492291ff1da21445145d31c702f388
- `work/checks/test_stage3_b3_s3_trace_audit.py` 84e5069a54726fedc9634530cea52bb546a964a028f32154f5e9939a661cfbe4
- `work/checks/stage3_b3_s3_record.py` 19fad7ebdc93bd36b63bb46915b91f74a0b3fcd4660403b0c0c8f7c16e6dde14
- fork HEAD at writing: e07642c (S3's Stage A commits are be0a600, the plan note, and 948865b, A1 to A2 and A4's code; the brief 13 writing session committed to the fork beside, ff2fc64, 8c3a490 and 39e34ab, untouched by S3)
