**Four fixes are required before use.** The permitted tests passed with in-memory capture: **23 passed, 1 skipped, 3 deselected**. The original command failed before collection because the read-only sandbox prevented pytest’s temporary-file capture. I did not run either expensive script, access barred data, or modify files.

1. **Required fix — redundant deliveries bypass validity checks.**  
   [stage3_t1.py:1157](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:1157) filters duplicates out of `check_application`. F2 checks whether another delivery would re-land the line; it does **not** establish target uniqueness or intended-document equality.

   Reproduced using the routine fixture: a midday honest edit creates two matching target lines before the second session. Restricted `apply_at(..., duplicate=True)` returns `composed=True`, and `check_application` returns `None`; checking the duplicate’s actual preceding state returns **“target found more than once.”** Validate every delivered edit, including redundant deliveries that F2 permits.

2. **Required fix — explicit line applications bypass mandatory author exclusions.**  
   [stage3_t1.py:1113](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:1113) defaults `apply_at`’s `exclude` to `()`. Unlike `plant` and `plant_pair`, it cannot distinguish an omitted argument from an explicitly acknowledged empty exclusion.

   Reproduced: a listed line application succeeds without `exclude`, on the same author as the triple. Require the exclusion argument for line arms here too; the harness can explicitly pass `()` when enumerating independent applications.

3. **Required fix — restricted records differ from default records at an otherwise identical valid draw.**  
   [stage3_t1.py:614](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:614) copies `last_draw_log`, but restricted [application at line 1131](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:1131) never establishes that draw’s log.

   Reproduced: run default `layout`, preserve the resulting timestamp RNG state, then apply the same valid draw through default and restricted paths. The rows are identical and validation passes, but `author_pool_sizes` and `author_draw_restricted` differ. A previous layout can instead supply stale metadata. Populate draw metadata consistently without consuming extra randomness.

   [The equality test:279](/Users/aravind/KruxAI/tais-project-selection/work/checks/test_stage3_t1_line_arm.py:279) misses this because its default comparison calls bare `_plant_once`, without first populating the log through `layout`.

4. **Required fix — the report can attach current hashes to stale successful results.**  
   [stage3_b3_lone_line_check.py:437](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_lone_line_check.py:437) loads saved parts, then records the current module, table and harness hashes without checking that those inputs produced those parts.

   Failure scenario: run successful checks, change the module, then run `report`. The report retains the old success claims alongside the new module hash. Store fingerprints with every part and reject incompatible parts when assembling the report.

Two optional defensive fixes:

- **Reject duplicate IDs during comparison.** [stage3_b3_lone_line_check.py:173](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_lone_line_check.py:173) collapses duplicate item records into dictionaries. Using the harness’s synthetic fixture, inserting a changed duplicate before the original produces `reproduced=True` despite `sections_equal["items"] == False`. Ordinary differences between uniquely keyed valid-draw sets are detected correctly.
- **Translate expected application failures into refusal codes.** [stage3_t1.py:1131](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:1131) can propagate a raw `ValueError`, for example for a whitespace-only append in a changed payload. That aborts selection instead of refusing the candidate. This concerns malformed or changed inputs; I did not establish such an input in the certified data.

The twelve design decisions assess as follows:

| Decision | Assessment |
|---|---|
| **1. Subclass and `PlantResult` changes** | **Right.** The `Inserter` class hash remains `24d3d147…`. For existing arms in default mode, the overrides delegate without additional RNG consumption; the conditional record fields preserve existing output. I found no changed execution path for those arms. |
| **2. `line0..line2` through `_roles`** | **Right**, subject to the duplicate-validation hole above. Statement indices and event IDs distinguish the line arms. `line_index` records the statement index; the sole author’s role slot remains `0`. |
| **3. Line layout and temporary exclusion attribute** | **Right for default selection.** The day draw, team/manager filtering, line-specific anchors, touching-author preference and `finally` reset are coherent. |
| **4. Line composition check** | **Right.** It checks the line at its first delivery timestamp and day end. |
| **5. Restricted selection and refusals** | **Mostly right.** Candidates come from the whitelist, exclusions apply, rejected draws are removed, and restricted selection does not enter `Inserter.plant`’s delivered/last-layout fallback. However, duplicate validation is incomplete and some application errors escape as exceptions. |
| **6. Timestamp resampling** | **Right.** It keeps the day and author fixed, retries only no-time samples, and has a deterministic bound. |
| **7. Checking only first deliveries** | **Wrong.** Its first-delivery checks match brief 26’s target uniqueness, substring occurrence, existing-line and intended-result checks at the drawn state. F2 does not justify omitting delivered duplicates. |
| **8. Enumerating compatible pairs** | **Right.** It avoids an unusable first choice and deterministically samples eligible pairs. Its distribution differs from sequential selection, but the supplied requirements permit this. |
| **9. Mandatory triple-author exclusions** | **Partial.** Enforced by `plant` and `plant_pair`, bypassed by `apply_at`. |
| **10. `ValidDraws` interpretation** | **Right for the stated shape.** It reads pairs from `valid_draws`, checks `valid_by_day` as counts, refuses missing entries and rejects document mismatch. |
| **11. Isolation** | **Right.** [The deep copy:610](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:610) isolates applications. [The synthetic test:335](/Users/aravind/KruxAI/tais-project-selection/work/checks/test_stage3_t1_line_arm.py:335) checks disjoint row identities, unchanged null state, only each application’s own lines, and reverse-order repeatability; it would catch shared state. |
| **12. Harness** | **Sound core checks, incomplete provenance.** Replay verifies the old source hash and compares complete row/record hashes across three variants. E4(a) detects ordinary set differences. E4(b) checks two seeded applications for each listed drawable draw and detects missing listed draws. Reporting needs fix 4. |

The inherited one-line mechanics are appropriate: `n_need=1`, a later eligible session for redundancy, unchanged floor and F1/F3 rules, the existing pre-window boundary, empty adjacency, and author-role indexing. Candidate sorting and seeded choices introduce no apparent nondeterminism. The metadata problem above affects record reproducibility.

E4(b) validates the whitelist at sampled drawn states; it does **not** independently recompute brief 26’s stronger validity over every reachable state. Unlisted successes are therefore useful diagnostics, not automatically discrepancies. All **17** brief-26 `module_line` needles remain unique. Full replay, the nine-member acceptance checks and E4 reproduction remain unverified in this review because their execution was excluded.

Normal harness reports select metadata and pass the text guard. **`PlantResult.record()` is not text-safe:** [line 353](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:353) includes edit arguments and `line_text`; inherited default-mode reasons can also include an anchor. Hashing those records internally is safe, but exporting them would disclose item text.

**Verdict: No—the extension is not safe to commit and use for S1 and S3 until the four required fixes are addressed.**