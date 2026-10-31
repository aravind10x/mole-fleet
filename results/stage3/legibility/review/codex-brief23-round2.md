**Do not run yet.** Most round-1 fixes are implemented, but five required fixes remain. One can produce a false sentence-3 pass.

I made no network/model calls, ran no instrument mode, and modified no files. Pytest failed before collection because no writable temporary directory exists; **no tests ran here**, including the fork test. The orchestrator’s reported 94 passes remain external evidence. Isolated in-memory checks reproduced the failures below.

References use `stage3_legibility.py` for `work/checks/stage3_legibility.py`.

1. **Required fix — sentence 3 discards observed parts when the whole is missing.**  
   [stage3_legibility.py:728](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:728), [stage3_legibility.py:799](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:799).

   `item_stat` clears **both** D measures whenever any condition is unavailable. Consequently, S3 selects on whole-answer availability, although D_part requires only the three parts.

   Reproduced scenario: all 48 test items have complete parts; ten have D_part=1. Four of those ten lack whole answers. The script reports **6/44=0.136**, passes the 90% completeness check, and passes S3 against a zero null reference. The defined part mean is **10/48=0.208**, which fails.

   Calculate D_whole, D_part and L using their separate necessary conditions. Update their report/retest denominators accordingly. When decoupling them, gate **both** own-statistic denominators in S4b; its single completeness check currently works only because their availability is forced equal.

2. **Required fix — the revised within-regime correlation is biased, and its bootstrap freezes the fitted means.**  
   [stage3_legibility.py:925](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:925), [stage3_legibility.py:932](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:932).

   Subtracting each regime’s **pooled r0/r1 mean** retains opposing regime-specific repeat offsets. Estimating that shared mean also couples the two repeats’ errors.

   Reproduced half-point-grid example: for `x=(-0.5,0,0.5)`, regime A has `(r0,r1)=(x+0.5,x−0.5)`; regime B reverses those offsets. Each regime’s correlation is **1**, but the reported within-regime correlation is **−0.2**, producing no sampling recommendation.

   For within-regime Pearson association, centre each regime **separately by repeat**. Preserve absolute shifts through ICC and difference statistics. Bootstrap original labelled pairs and refit the centring in each resample; resampling fixed residuals does not bootstrap the implemented estimator. This leaves round-1’s reliability correction incomplete.

3. **Required fix — malformed enclosing JSON can still supply an inner score.**  
   [stage3_legibility.py:458](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:458).

   After decoding fails, scanning restarts one character later. Thus:

   ```text
   {"outer": {"score":1,"declined":false}
   ```

   is accepted as score 1 despite the incomplete outer object. An array containing a score object is also accepted. This retains round-1’s inner-object failure under malformed enclosing structures.

   Track enclosing structures and reject ambiguous/malformed envelopes rather than rescuing their nested score objects. Ordinary braces inside valid strings, valid nesting, and unrelated surrounding objects are fixed.

4. **Required fix — current OpenRouter prices are not bound to the approved estimate.**  
   [stage3_legibility.py:1554](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:1554), [stage3_legibility.py:1573](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:1573).

   `models-v0.json` has no checked identity in the estimate/manifest. Scenario: `prices` refreshes Kimi’s rates after approval; `run --approved-usd 28.23` still passes, using the old estimate with the new accounting rates.

   Pin the price snapshot used by the estimate and verify it before requests, or recompute the estimate and require approval of any change. Route/model choices are compared with the estimate; the **routes file itself is not hash-pinned**. Its operative selection is therefore covered semantically, but not its complete provenance.

5. **Required fix — the actual day-0 rendering source remains unpinned.**  
   [stage3_legibility.py:1016](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:1016), [stage3_legibility.py:164](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:164).

   Packets use `stage3_views.seed_base()`, backed by the seeder. Neither that resolved text nor its source dependencies are pinned. The hashed day-0 Markdown is a different input, and `mode_run` ignores the returned `day0_in_md` check.

   Scenario: the seeder changes while the Markdown and four pinned dependencies remain unchanged. Manifest validation passes, but readers receive different context. Pin and verify the resolved document mapping—or the rendered packets—before requests.

The remaining requested checks largely pass:

- **Guard and abort accounting:** all three clients set `abort` when `request_guard` trips. Async lock/semaphore contexts release correctly; I found no guard-induced deadlock. Requests already admitted before throttling may still send, within the disclosed concurrency allowance under normal completion.
- **Paid abort records:** they persist as `errored`; their charges enter `dollars_cached` on restart, while the records are excluded from reusable responses and re-asked.
- **Refusal resumes:** parsed refusal records are served from cache. That preserves the original refused measurement opportunity, which is appropriate here. `Records.answer` returns no answer for token refusals; `reader_status` distinguishes token/provider refusals correctly.
- **Outcome tables:** repeat/regime/condition/target/pass keys and counts are correct. Mixed-pass counts intentionally aggregate conditions. Available condition means/counts survive incomplete L, although finding 1 still affects the derived D statistics.
- **Gates:** S2 uses all 48 test items and gates its null denominator; missing test L counts as not above. S3 supplies both completeness denominators, subject to finding 1. Ties use average ranks. Missing partners and undefined correlations cannot pass S4. `verdict` requires an actual agreeing pair among families holding every sentence.
- **Run plumbing:** preflight checks precede paid requests; `--resume` is required for nonempty reader/scorer caches; route caches are intentionally excluded. Failed/refused probes are rejected. OpenRouter settles sibling calls before raising, and scorer abort stops the next phase.
- **Round-1 corrections:** own-edit semantic coverage, day-0 limitation/subset, refusal retry policy, temperature omission, reasoning override rejection, expanded reports and JSON disclosures are implemented. Regression coverage was added, but the cases above remain uncovered.

Optional findings and disclosures:

- **Optional — tighten parser schema consistency.** [stage3_legibility.py:484](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:484). Objects scoring `1` and `1.0` are rejected as disagreement; explicit `reason:null` is accepted despite “optional string”; an invalid earlier reason is ignored when the final agreeing object is valid. Normalize numeric scores and validate every candidate consistently.
- **Optional — exclude reader prose refusals from a kappa sensitivity.** [stage3_legibility.py:734](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:734). Scorer records marking `declined:true` still contribute binary scores even when `reader_status` calls the condition `refused_prose`. Numerous agreeing refusal scores can raise kappa. Provider/token scorer refusals are correctly excluded.
- **Optional — finish the statistical disclosures.** [stage3_legibility.py:1277](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:1277). The report should explicitly name S2’s **null-side** 90% gate and the one-scored-pass policy. Also name informative missingness: nine missing high-L nulls among 94 can leave an observed p95 of 0 where the complete-data p95 would be 1. The response’s promised test-only bootstrap interval is absent at [stage3_legibility.py:933](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:933).
- **Optional — qualify spend guarantees and reconcile the stop figure.** [openrouter.py:336](/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/mole/llm/openrouter.py:336) abandons a timed-out daemon HTTP thread, which may remain billable while a retry proceeds. Those charges cannot be captured by response-based accounting. Separately, [stage3_legibility.py:1571](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:1571) stops at **$56.46**, doubling rounded $28.23; the estimate’s **$56.47** doubles the unrounded central value. This discrepancy is one cent stricter.

The fixed sentence readings are defensible **pre-run amendments**, rather than literal restatements of every brief clause. The report should name the added 90% tolerance, one-pass sufficiency, test-only agreement and mutually agreeing-pair requirement. S2’s fixed denominator faithfully implements “half of the test items”; test-only agreement and the pair rule strengthen downstream certification. Finding 1 is an unintended selection change, not a defensible reading.

The permitted metadata checks passed: **142 unique sorted items**, the 48-item honest draw, false-target draw, 30-item retest draw, pool hash, script hash, configuration hash and four dependency hashes all agree. The rubric file is covered by its canonical hash check in `rows_and_triples`; I did not open it.

The **$28.23 central/$54.02 upper** arithmetic includes 688 reads per family, 6,384 scorer calls, the 1.10 re-ask allowance, longer scorer answers and $0.05 for probes. I found no further ordinary call-count omission. “Upper” remains an assumption-based estimate, not a worst-case bound. Cached route probes are acceptable historical discovery, but a rerun does not establish fresh availability.

**Verdict: fix findings 1–5, add their regressions, rebuild and commit the affected hashes/estimate, then obtain Aravind’s approval before running.** Brief 24 must also retain its separate cross-document validation and writer-family exclusion requirements; this run alone cannot satisfy those.