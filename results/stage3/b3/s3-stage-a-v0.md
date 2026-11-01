# S3 Stage A record (brief 33 v2.1, 99e3ec7f): the $0 stage before the gate — written 2026-11-01 20:19Z

Blue session (Fable 5.1). No judge request was sent; no OpenRouter request of any kind; nothing applied on disk outside the never-open application file. Barrier kept: ids, counts, hashes, scores and labels only; no item line, document text, rubric or declared effect printed, logged or written into any record; `work/stage3/red/`, persona files, `archived-scores*`, the anchor sheet and its draw file, and other briefs' judge caches not opened (the trace audit below). Every path is from the project root.

## A1. Pre-flight and the stream set

- Configuration `work/stage3/b3/s3-config-v0.json` (e28dca16): placement seed 20261181, bootstrap 20261152 x 2000, tie 20261112, m_s 18.22 and 19.37, m_L 18.22, arm seeds {'1': 2026118110, '2': 2026118120, '3': 2026118130, '4': 2026118140, '6': 2026118160} (exactly the tags 1, 2, 3, 4 and 6; no tag 5).
- Before A1b's note: `stage3_b3_preflight.py --config` **PASS**, 26 of 26 files, 3 prompt components, value mismatches []; plan.md 58b0c121 equal to the fork's HEAD copy (True). Output kept as `s3-preflight-v0-prenote.json` (d2adf6bc).
- The driver asserts the stream set itself (`stage3_b3_s3.assert_arm_seeds`, tested: a tag 5, a missing tag 6 and a wrong value each refuse).

## A1b. The dated note on the plan

- Appended verbatim under the heading the brief gives, 2026-11-02; `work/stage3/b3/plan.md` **a411d8a2** (114196 bytes; its first 111,603 bytes hash to 58b0c121, so nothing above the note changed); mirrored to `results/stage3/b3/plan.md` and committed to the fork (be0a600); the `s1-preflight-sha256` block is unchanged (26 lines).
- Pre-flight re-run after the commit: **PASS**, 26 of 26, plan.md a411d8a2 matches HEAD (True); `s3-preflight-v0.json` (03ed1816). `test_stage3_b3_preflight.py` 10 pass.

## A2. The analysis matrix, the readings script and the dry run

- Matrix `work/stage3/b3/s3-analysis-matrix-v0.json` **1b80280a** by `stage3_b3_s3_matrix.py` (4d682443; tests b69ba67d, 11 pass): 116 net items (73 candidates, 21 control items, 22 comparison items) keyed by opaque id; every input verified by sha256 before it is read (the seven files of 9a769d68 `inputs_sha256`, stratum-v0.json 6113bd8d, s1-populations-v0.json f17e7a72, inserter-dry-run-v1.json 02138931, and the four payload and control files pinned in v1's `inputs_sha256`, read for each statement's `op` only); section 1.2's table reproduced (means, SD, IQR, writer and document counts, pooled strata; tested against s1-populations-v0.json and Part 3's Step 0 to 1e-3); the candidates' rater fields equal brief 25's file; no item text (tested).
- Readings script `stage3_b3_s3_readings.py` **a39f6f52** (tests 567f4048); dry run `stage3_b3_s3_dryrun.py` (bd726ae5); report `s3-readings-dryrun-v0.md` (2ed8f91e) and `.json` (2809a5ab).
- The exception table against Part 3's simulator, each delta tested: replicate failure more than 10 percent of 2,000 (not 2.5 percent); form (b) with the top-two gap (the note); the floor once on the full set against the sham; 2,000 replicates at seed 20261152 (not 1,000); the fixed quartiles 47.5 and 66.5 for every population; the cascade as seven ordered steps; a rank-deficient design is a fit failure (the simulator's fitter converges on one; tested).
- Reachability: 28 fixtures, all reaching their ids: **True**; ids not reached by any fixture: none; S-P1 unreachable by decision (the k = 2 arm is not run); S4-1 by the separate session after Aravind reports. Wall time 412 s.
- Operating characteristics through the adapter (seed 20261171, tag 500, ICC 0.3, 300 experiments per truth, 2000 replicates; one stream per experiment: default_rng([20261171, 500, truth index, model index, experiment index])): the carrier's P(excluded | 0) on the subset under the "none" model **0.640** against Part 3's 0.68; P(present | 1.5 x) **0.730** against 0.72; tolerance ± 0.08: **ACCEPTED**. The full set under the "zero" model beside, named in the report. Wall time 1533 s.

## A3. The draws and the application set, once

- (i) Payload and control files verified against v1's `inputs_sha256` before the draw; the applied id sets hash to section 1.1's values (full 73 (5dbd067d), controls 21 (3db4d199), sham 22 (27909dc2)).
- (ii) Brief 27's harness copied with an opt-in (`stage3_b3_lone_line_check_s3.py` 80e35721; tests f0f5f3eb, 28 pass with the gated reproduction): default mode reproduces the candidates' 4537 of 4537 (True); the control items through v1: net 21 items, 63 lines, **1231 of 1231 listed draws accepted**, refused none; gross 22: 1271 of 1271; record `s3-lone-line-check-v0.json` (8f64fb7e).
- The draw: module 240f4ed9 in restricted mode on `inserter-dry-run-v1.json` 02138931, corpus ffc1f6cd, template 294d59d2; arm seeds {'1': 2026118110, '2': 2026118120, '3': 2026118130, '4': 2026118140, '6': 2026118160}; window ['2026-04-06', '2026-04-07', '2026-04-08'] (the corpus span (build_world); units as planted_items). Units: items 232 (expected 232), lines 564 (expected 564); by regime: candidate items 146, control items 42, comparison items 44, candidate lines 438, control lines 126; counts equal the plan's: **True**; by stream tag {'tag1': 146, 'tag2': 438, 'tag3': 42, 'tag4': 44, 'tag6': 126}; by day {'2026-04-06': 319, '2026-04-07': 477}; by writer {'glm53:items': 90, 'glm53:lines': 270, 'sonnet55:items': 98, 'sonnet55:lines': 294, 't1v2:items': 44}.
- Refused draws at application time (section 2.4 (3), the next draw of the same stream): none; re-draws per application {'0': 748, '2': 4, '4': 2, '5': 2, '7': 2, '9': 2, '10': 36} (the module's own rule, section 2.3: a draw that broke no honest edit is preferred for the first 10 re-draws; 36 applications reached 10 and 31 applications in all carry a broken honest edit, rebuilt by the module as T1 v3 did). Every application delivered and composed: True. Items whose two applications are by different authors on different days: 116 of 116. S3's own drops: **0** ; control items leaving the add-on: **0**.
- `s3-applications-v0.json` **02edac2a** (never-open: applied document states and packets; 796 units); record `s3-applications-v0.md` (d8778718). Wall time 626 s.

## A4. The driver, the packets, the caches and the pre-signal

- Driver `stage3_b3_s3.py` **5d0e0899** (tests 487caf57): modes apply | render | score; the ledger (one guard through `request_guard` on every client, in-flight reservations, the stop at $153.25, each client's own cap the stop less the other caches), the view order enforced, the pause after the first about 20 carrier units, resumable state, the scores file's flag through `stage3_thresholds.is_flagged` at the sealed rule (tested).
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

- `stage3_b3_s3_trace_audit.py` (af2bf444; tests 84e5069a, 7 pass, the positive test bound to the empty `--writer-dir`) around the pinned script 2a409344 on this session's transcript `2043475e-6037-4bb9-8224-930e8d98c3c5.jsonl` with `--writer-dir work/stage3/b3/s3-trace-empty` (empty; every token absolutised first) and the policy `s3-trace-policy.json` (9d739792): opened 186, allowed 109, outside 77 (existing files 0, non-existent tokens 77), **never-open 0**; verdict PASS.

## Differences from the brief and the plan, reported

Each is a decision this session took where the brief, the plan or the code left a choice; the plan governs where it speaks.

- **The scores file's flag is the planted unit's own flag.** `th.is_flagged(score, sealed rule, tie label)` with the tie keyed by the author under an author rule (the per-agent views) and by the cache label under a unit rule (`O_diff`): B1's `recall_planted_unit_only` and T1's `O_diff` convention. It is not the union with the author's honest pairs on other documents (B1's union reading, Part 2's `honest_path`). Reasons: plan section 4.2 names "each item application's lone-author per-agent flag at the sealed rule"; brief 33 A0 names that code path; and the honest-pair rows for Sonnet's `P_author` are not among the pinned inputs. If the reviewer reads the plan the other way, form (b), the floor (b), the anchors' lone recall and the composed gaps are recomputed on the union; form (a), the carrier, is unchanged.
- **A live row's form (b) takes the rater's section-2 maximum and top-two gap as its line covariates** (the live rows carry no lone-line units, A6.13.8); Part 2's T2 layout without singletons did the same (`experiment`, the `else` branch). Descriptive rows only.
- **The harness copy writes under its own directory** (`work/stage3/b3/s3-lone-line-check/`, record `s3-lone-line-check-v0.json`), never brief 27's `lone-line-arm/` parts or `lone-line-arm-v0.json` (K1, pinned); "default output unchanged" is read as unchanged numbers, shown by the gated reproduction test.
- **The matrix keeps each item's document path** (a class-document path, the disclosed class), not item text.
- **The operating characteristics seed one stream per experiment**, `default_rng([20261171, 500, truth index, model index, experiment index])`: the brief fixes the seed and the tag, the sub-key is this session's, so the experiments run in parallel. Each experiment reads the two named instruments through the readings script's own `Instrument` (the floor once on the full set, the plan's precedence), form (a)'s label tallied as Part 3's `a_outcome` does, form (b) beside.
- **The trace audit absolutises every transcript token against the project root** before the pinned script audits it, with the empty writer directory passed as an absolute path; otherwise the pinned script's location rule would allow any relative `work/stage3/b3/...` token under the empty directory. The positive test is bound to that choice. Tokens that are fragments of shell commands (non-existent paths) are counted apart from existing files.
- **An errored unit is re-asked once on a resumed run**, by the client's own policy (an errored record is never served from the cache); the run record counts them. The note's rule (e) forbids scoring a scored unit twice and re-asking a refused unit outside the client's retry policy, which this respects.
- **The readings script was written before its tests**; its tests are the brief's reachability fixtures and the exception-table assertions, run RED first (six fixtures missed their ids on the first run and were tuned, as the dry-run report records) and GREEN after.
- **The fixtures' synthetic worlds use the committed matrix's covariates** (numbers and ids) with generated scores; a fixture that needs a covariate held constant overrides the matrix copy it passes to the script (stated per fixture in the report).

## Hashes

- `work/stage3/b3/s3-config-v0.json` e28dca16fa9c0c809cc61a5117f15ffa9cce97a73c6e8a42ea54e24e9a1d45cc
- `work/stage3/b3/s3-preflight-v0-prenote.json` d2adf6bccb927a5889c80274031a2c83efa989fcaa2c05a9af9636c6544e886d
- `work/stage3/b3/s3-preflight-v0.json` 03ed1816cdeb473e18c07664b52ff344caf6b12fe80959c86d69d4496e756109
- `work/stage3/b3/plan.md` a411d8a296fc9436b827dc97560a05f9db2496903da34e8ee75c46a06728b0a0
- `work/stage3/b3/s3-analysis-matrix-v0.json` 1b80280ad8ed14d1ec0fed26b7137d3cc50a055e8f41b19e52083439f5b3effe
- `work/stage3/b3/s3-readings-dryrun-v0.json` 2809a5ab5f0b59bf9dcf45aeeed445db1a685adcb06d2182b773795f007c239a
- `work/stage3/b3/s3-readings-dryrun-v0.md` 2ed8f91efbe99e842fc71d79a0bc26ead6fefc375b099809788a2e7a445e5689
- `work/stage3/b3/s3-lone-line-check-v0.json` 8f64fb7ee24caaf68db82cf70633056bf95013f797001f95bfb87cef0e0f3dbe
- `work/stage3/b3/s3-applications-v0.json` 02edac2a88fbdd3d9cfd4404e496aac6991c2f917fd27ca191394dc225c229bc
- `work/stage3/b3/s3-applications-v0.md` d87787183713f5d253bf418adf0c2c824e1a57aa491f7c5c7904b4936a4d0d27
- `work/stage3/b3/s3-render-v0.json` 7c33c10433784bbbab57eca7640e9cd0f381dfff796cdf9157fdcd3700ee169f
- `work/stage3/b3/s3-trace-policy.json` 9d73979243605dbd96be914314721e44cb2c514371184e5e8b30c8566b95a6de
- `work/stage3/b3/s3-trace-audit-stageA.json` e3119f8ddd594f111f311551001375ec149214ae92df376b93c1188b455c38e2
- `work/checks/stage3_b3_s3_matrix.py` 4d682443ae4373ff04573625b470f87c8334e89d32dcf00f33eb42d142d5fbbe
- `work/checks/test_stage3_b3_s3_matrix.py` b69ba67d5be15fe74cb0f01069783095758d86bcf2b8296ba1508b9ae57ea703
- `work/checks/stage3_b3_s3_readings.py` a39f6f52e9f9493e496563212660031e2278bcff842f7b3d1795b2cbfcf3e8e0
- `work/checks/test_stage3_b3_s3_readings.py` 567f4048e20130809ebfcd6912edd13e736e88c5d56a4aecb0fb3ca71bf5970a
- `work/checks/stage3_b3_s3_dryrun.py` bd726ae505fc6cec78ee49d3bdeb377e89842125bb93747c1ab8dc5a4cb0074e
- `work/checks/stage3_b3_s3.py` 5d0e08994c7235b5863b29a14e60b130dd617f45ead653faa798fa1a53638ce0
- `work/checks/test_stage3_b3_s3.py` 487caf577f00a14295be6a95a70edd639934373023498a0d401eeb091128137b
- `work/checks/stage3_b3_lone_line_check_s3.py` 80e357217e8bda7cd12514f2fc5593c416d34b2d200008f754a074e0ec66e01a
- `work/checks/test_stage3_b3_lone_line_check_s3.py` f0f5f3ebb91f99e10c58fccd17365ae5b904006bd458ca4be39269eacc348019
- `work/checks/stage3_b3_s3_trace_audit.py` af2bf444b398b03caac349f1958c315de1492291ff1da21445145d31c702f388
- `work/checks/test_stage3_b3_s3_trace_audit.py` 84e5069a54726fedc9634530cea52bb546a964a028f32154f5e9939a661cfbe4
- `work/checks/stage3_b3_s3_record.py` 20bd61d340d684ebb6c26c2e31a2d6eede3a4489615e1fe7a62a10f8d8f1b373
- fork HEAD at writing: 39e34ab (S3's Stage A commits are be0a600, the plan note, and 948865b, A1 to A2 and A4's code; the brief 13 writing session committed to the fork beside, ff2fc64, 8c3a490 and 39e34ab, untouched by S3)
