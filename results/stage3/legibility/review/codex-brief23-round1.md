**Do not run yet.** The item selection is reproducible, and the pass/repeat cache labels address the original cache trap. Required fixes remain in refusal handling, validation denominators, provenance, spending, and error output.

I read only the permitted files and made no network or model calls. The approved pytest command failed during startup because the sandbox has no writable temporary directory; **no tests ran**. In-memory checks reproduced all three committed draws and confirmed several parser/statistical failure cases.

References below use `stage3_legibility.py` for `work/checks/stage3_legibility.py`; other paths are explicit.

1. **Fidelity to brief 23**

   The selection logic checks out: pools are built in sorted opaque-id order; the 48 honest items use `sample` on the sorted 120-item pool, then the selected ids are sorted; false targets use one `choice` stream over null items in sorted id order, with sorted same-document candidates and kind matching for controls where possible; retest uses `sample` over all sorted selected ids. I reproduced the committed selections from permitted metadata. The paired sensitivity correctly uses same-number conforming ids, separately from the primary false-target draw. References: `stage3_legibility.py:259`, `:279`, `:301`, `:315`, `:321`.

   The question is verbatim. There are four reader units per item per family, two scoring passes per target, and four additional reader units for each retest item. Retests use only the L target, with both scoring passes, for every family (`:104`, `:449`, `:457`, `:461`, `:977`).

   **Required fix — operationalize the own-edit control explicitly.** The condition-specific reading is appropriate: whole targets all three statements’ new content; a part targets its own statement. Comparing a part with the entire triple would manufacture failure. But the same consequence-only scorer instruction is applied to these literal document-state targets without explaining the distinction (`:115`, `:240`, `:387`). A reader’s concise semantic summary could be rejected for omitting literal details, while accepting any one listed element would make whole-control success too easy. Specify semantic coverage for the own target while retaining strict combined-consequence credit for L.

   **Optional — strengthen its diagnosis.** `D_part_own` is the maximum over parts, faithfully following the brief, but can pass when only one part is understood. Report individual-part sensitivity beside it. Failure of 4b implicates the reader–prompt–rubric–scorer chain; it does not establish scorer strictness alone (`:629`, `:690`, `:95`).

2. **Rendering**

   `reader_packet`, `edit_head`, and `cond_statements` preserve the stripped statement text and ordering. Replace anchors, appended content, and unified-diff whole writes follow the helper’s conventions. Each part gets the same day-0 document and exactly one **statement**, which can contain multiple physical lines (`stage3_legibility.py:349`, `:361`, `:369`; `work/checks/stage3_rater_strip.py:129`, `:162`, `:236`).

   No explicit regime, target, source id, or account metadata is added. Handles, multiline content, and whole-write syntax remain potential regime cues inherited from the inputs. The packet therefore preserves the disclosed confounding; it does not remove it.

   **Required fix — explain the day-0 validity limitation, beyond counts.** The report merely lists unresolved anchors (`stage3_legibility.py:1096`). A reader can correctly conclude that a replacement cannot apply to the displayed document and consequently fail to state the intended consequence. Unequal unresolved-anchor rates can then appear as comprehension differences. State this threat and provide a resolved-anchor sensitivity. Preserving day-0 rendering is faithful to the brief; silently repairing anchors would change the experiment.

   **Optional — clarify interpretation uniformly.** If readers should reason about proposed replacement content despite revision mismatches, add a neutral instruction to *every* packet through a dated amendment. Avoid item-specific hints that introduce another regime cue.

3. **Scorer and parser**

   The main instruction implements overall-consequence scoring and explicitly denies component-only credit (`stage3_legibility.py:113`). The `declined` flag describes reader refusal; it does not itself change the requested binary scoring rule.

   The scorer receives no separate document context or edit packet. However, own-edit rubrics contain the honest statements’ new content. “Never sees the item” should therefore read “never receives the reader packet or day-0 context” (`:240`, `:374`, `:999`).

   **Required fix — replace brace-regex extraction with JSON-aware parsing.** At `stage3_legibility.py:403`, valid JSON containing braces in its reason is lost; a trailing unrelated object can veto a preceding valid score; an inner object can be mistaken for the response. I reproduced the valid-response loss offline. Parse a complete JSON object and validate its schema.

   **Optional — make accepted syntax deliberate.** The parser accepts `1.0`, trailing prose, and a missing/non-string reason despite its docstring (`:407`, `:417`). Accepting numeric `1.0` is harmless mathematically. Ambiguous multiple objects and ignored trailing content are more consequential; document or reject them consistently.

4. **Refusals**

   Provider refusal, the token, and unanimous L-target `declined` flags exclude the reader condition from L; complete-case exclusion itself is reasonable (`stage3_legibility.py:594`, `:608`).

   **Required fix — preserve the first Bedrock refusal.** `work/checks/judge_client.py:598` re-asks provider refusals. A refusal followed by an answer becomes a scored reader/scorer outcome, with the refusal retained only inside attempts. Instrument tables omit it. This differs from the Converse/OpenRouter paths and violates refusal accounting. Disable refusal re-asks for this instrument, or explicitly retain and report attempt-level refusal outcomes without converting the refused measurement opportunity into an ordinary score.

   **Required fix — distinguish scorer refusal from parser failure.** A scorer’s prose refusal becomes unparseable, is retried, and eventually becomes `errored`/missing (`work/checks/judge_client.py:264`; `stage3_legibility.py:406`). The `declined` flag detects refusal in the *reader answer*, not refusal by the scorer. Give the scorer its own refusal outcome.

   **Required fix — report every refusal dimension.** Scorer outcomes collapse conditions, targets, and repeats; reader outcomes cover only r0 (`stage3_legibility.py:718`, `:722`, `:1080`). One refused scorer pass plus one scored pass also disappears from the item’s summary status because available scores take precedence (`:613`). Retain counts by family, regime, condition, target, pass/repeat, including mixed scored/refused cases and denominators beside metric tables.

5. **Cache independence and provenance**

   Pass, family, repeat, item, condition, and target distinguish scorer labels. Reader repeats differ, and reader families use separate cache files (`stage3_legibility.py:425`, `:429`, `:915`). Identical answers across families therefore do not collide in the scorer cache. Re-running the same experiment intentionally resumes cached records; it is not another independent replication.

   **Required fix — enforce the committed configuration.** `rows_and_triples` checks the rubric hash only; `mode_run` does not compare current inputs, prompts, routes, or estimate configuration with their committed versions (`stage3_legibility.py:826`, `:1218`). Cache loaders check model and prompt-version strings, but not system hashes or settings (`work/checks/judge_client.py:443`; `work/checks/judge_openrouter.py:140`). Changing a system instruction without changing its version can reuse old responses, while the report prints the old manifest’s prompt hashes (`stage3_legibility.py:1285`).

   Pin and verify a run manifest covering inputs, actual prompts, dependencies/settings, routes, and estimate. Separate a new experiment from a resume. The present script hash matches the committed manifest, but the existing distinct-key tests do not protect future configuration changes.

6. **Temperature and effective settings**

   Bedrock omits temperature. OpenRouter’s fork explicitly serializes it, so `None` becomes JSON null (`work/mole-fork/mole/llm/openrouter.py:239`).

   **Required fix — omit the field when `None`.** The allowed offline evidence does not establish that null means provider default for Kimi K3 or fallback Sonnet 5.5. Omission directly implements I2 and avoids depending on provider-specific null normalization. Remove the unsupported equivalence claim at `stage3_legibility.py:1000`, and test the actual serialized HTTP body.

   **Required fix — control hidden reasoning settings.** The fork reads `OPENROUTER_REASONING_EFFORT` on every call, while the judge record always says “provider default” (`work/mole-fork/mole/llm/openrouter.py:262`; `work/checks/judge_openrouter.py:286`). An inherited setting changes cost and measurement behavior without appearing in the record. Explicitly reject overrides or record and pin the effective setting.

7. **Statistics and validation gates**

   Type-7 quantiles, average tie ranks, Spearman, binary Cohen’s kappa, and the two-measurement ICC(1) formula are implemented correctly for their stated definitions (`stage3_legibility.py:467–547`).

   **Required fix — make incomplete measurements visible to the gates.** A single scored pass suffices, and all validation summaries use surviving complete-case items (`:613`, `:625`, `:667`). For example, if most test items refuse and the few survivors separate well, sentence 2 can pass using those survivors as its denominator, despite saying “at least half of the test items.” Use the fixed 48-item denominator for that claim or report missing-outcome bounds and an inconclusive result. Predeclare the one-pass policy and report pass completeness. Also retain available condition statistics even when another condition prevents computing L; currently they are all erased.

   **Required fix — prevent pooled separation from certifying agreement.** Sentence 4 selects each family’s best correlation over all test and null items (`:749`, `:774`). An offline example with the actual 94-null/48-test sizes gave **ρ = 0.917 pooled and −1.0 on test items**. Thus families can agree on the test/null distinction while ranking test stimuli oppositely. For downstream item certification, test-only agreement should be primary through a dated pre-run amendment; pooled agreement should remain descriptive. Require the families supporting “valid” to agree with one another, rather than each finding a different qualifying partner.

   **Required fix — do not use pooled Pearson/Spearman–Brown as a definitive sampling prescription.** `samples_for_reliability` is algebraically correct, but `retest_analysis` applies it to pooled Pearson correlation (`:730`, `:745`). Between-regime separation or systematic repeat shifts can produce high correlation without reliable item-level certification. Use test-relevant agreement/reliability with uncertainty and explicit assumptions; label the current sample calculation exploratory.

   **Optional — expose threshold ties and stratified kappa.** Strict `>` matches “above”; retain it. Current single-reader L lies on a **0.5 grid**, not a 0.25 grid. With 94 null items, changing the number of null L=1 values from four to five to six changes type-7 p95 from 0 to 0.35 to 1. Report counts below/equal/above the cutoff and uncertainty; do not adjust the threshold after observing results (`:651`, `:674`). Pooled kappa is a legitimate mixture summary, but easy own/false targets and repeated observations can mask disagreement on test targets. Report strata and exclude refusal outcomes from binary reliability calculations (`:633`).

8. **Estimate, spending, routes, and aborts**

   The committed arithmetic is consistent: **688 reads per family, 2,064 total; 6,384 scorer calls; $26.97 central/$46.21 upper assumptions**. Rendered context and rubric lengths enter the estimate. The brief’s rough scorer-call arithmetic is less complete than the implementation.

   **Required fix — bind approval to the actual route/configuration.** The estimate assumes Bedrock Sonnet; route discovery can choose OpenRouter, yet `mode_run` checks only that the approved dollar number matches the old estimate (`stage3_legibility.py:854`, `:1223`). Reprice after routing and bind approval to that estimate. Route probes themselves lack an approval prerequisite.

   **Required fix — reject failed route probes.** `mode_routes.one` returns `accepted=True` whenever `score()` returns, including exhausted retries producing `errored` (`:1194`). A route with no successful response can be approved. Distinguish route availability, usable output, refusal, and transport failure.

   **Required fix — make the spend limit shared and durable.** Global checks occur once per 32-unit chunk, while each client receives the entire global cap (`:952`, `:1232`). Up to three reader chunks—96 logical units, plus re-asks—can remain admitted after crossing the limit. This is not merely concurrency-sized overshoot. Furthermore, an abort during a later retry can leave earlier paid responses unpersisted because saving happens only after the logical unit returns (`work/checks/judge_client.py:562`, `:568`, `:591`). A restart then forgets those charges. Persist attempt-level spend and enforce a shared admission budget; disclose the bounded in-flight allowance. Route-check spend must join the ledger. The “upper” estimate also needs explicit treatment of re-asks, answer-length uncertainty, and route probes.

   Nulls precede tests, families run concurrently, and the main run uses one event loop. Continuing healthy families after one reader-family failure is reasonable.

   **Required fix — stop future phases after scorer failure and settle outstanding calls.** A scorer abort is returned as data, after which `mode_run` starts test readers anyway (`stage3_legibility.py:989`, `:1242`). OpenRouter’s `score_many` also raises immediately on one failure without settling siblings (`work/checks/judge_openrouter.py:292`). Pending calls can overlap later phases or be cancelled at shutdown while underlying requests continue. Settle calls and preserve records before transitioning; halt further reader spending when the shared scorer cannot proceed.

9. **Output discipline**

   **Required fix — protect stderr and exception paths, not just `emit`.** `check_safe` validates string syntax, not a semantic allow-list; a one-word answer passes it (`stage3_legibility.py:158`). More concretely, Bedrock’s non-aborting HTTP error body can enter `c["error"]` and be printed by retry logging (`work/checks/judge_client.py:539`, `:607`). Such bodies can echo submitted content. Unexpected exceptions also escape `main` with unsanitized tracebacks (`stage3_legibility.py:1312`).

   Disable free-text client logging for this instrument and emit fixed error codes plus safe identifiers. Handle unexpected exceptions without exposing their messages/chains. Normal OpenRouter key-rotation logs contain key labels, not values; they are not the principal leak here.

10. **Report completeness and claims**

   The report includes most requested aggregate metrics, distributions, positive controls, paired sensitivity, agreement, prompt/script hashes, cache hashes, and Markdown deviations (`stage3_legibility.py:1030`).

   **Required fix — complete the auditable outputs.** Add scorer refusals by condition, r1 reader outcomes, metric-specific exclusions/pass completeness, and per-item paired r0/r1 L values and statuses. Currently retest output is aggregate only, and `L_by_item` retains only r0 (`:725`, `:730`). Include disclosures/deviations in JSON too; they currently appear only in Markdown (`:1289`, `:1104`).

   Revise the fixed claims about null temperature, universal provider-default sampling, the scorer never seeing item content, and 4b identifying strict scoring. Explain unresolved anchors and inherited regime cues, rather than reporting counts alone.

   I4’s report mirror and STATUS update are not performed by `mode_report`; they remain explicit completion steps.

11. **Important missing tests**

   **Required fix — add regression coverage for the failure scenarios above.** Existing tests do not exercise serialized OpenRouter requests, environment overrides, refusal-then-success, scorer prose refusal, mixed refused/scored passes, braces in JSON strings, incomplete-data validation, pooled-versus-test disagreement, configuration drift, failed route acceptance, concurrent budget overshoot, paid-attempt persistence, or abort settlement.

   The end-to-end fake scorer uses token overlap and accepts any intersecting own-target token (`work/checks/test_stage3_legibility.py:377`). It therefore cannot establish all-three coverage or consequence-only scoring. Existing cache-key tests are useful, but insufficient for configuration identity (`:210`, `:253`).

**Verdict:** The script can support a run after these fixes and pre-run statistical clarifications, but it is not ready for approval now. First repair refusal/output/spend/provenance paths, amend the gate and positive-control interpretations, rerun the offline suite in a writable test environment, and obtain PI approval for the route-specific revised estimate.