**All five round-2 fixes are correct in code. One required closure gap remains: finding 4 has no regression test.** I found no new required runtime defect.

I modified no files, made no network/model calls, and ran no instrument mode. Both approved pytest commands failed before collection because the sandbox has no writable temporary directory; **no tests ran here**. The orchestrator’s reported 94 passes remain external evidence.

| Round-2 finding | Implementation and regression |
|---|---|
| 1. Decouple D measures | Fixed. S3, regime means, paired sensitivity and retest use each metric’s available denominator; S4b gates both. Tests at `test_stage3_legibility.py:655` and `:665`, with the coverage limitation below. |
| 2. Retest/bootstrap | Fixed. Separate repeat means are removed; each bootstrap resample refits centring. All three production call sites use the new signature. Regression at `:681`; test-only intervals and repeat shifts are reported. |
| 3. JSON envelopes | Fixed. Malformed envelopes cannot supply nested scores; arrays supply no candidates; every candidate is validated and numeric scores normalized. Regression at `:691`; fenced JSON remains covered at `:209`. |
| 4. Prices/routes | Fixed in code, **regression absent**. |
| 5. Rendering | Fixed. Resolved day-0 text and packets are pinned; both `dry-run` and `run` reject drift and failed Markdown checks. Helper regression at `:701`. |

Findings:

1. **Required fix — add the price/routes pinning regression.**  
   [stage3_legibility.py:1648](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:1648), [test_stage3_legibility.py:653](/Users/aravind/KruxAI/tais-project-selection/work/checks/test_stage3_legibility.py:653).  
   No test exercises the new price/routes hashes or their preflight wiring. Removing either check would let refreshed Kimi prices or changed route provenance accompany an old approved estimate while this suite still passed. Add synthetic unchanged-snapshot and independent price/routes-drift cases, asserting rejection before client construction or requests. This leaves the earlier required regression-coverage requirement partially open.

2. **Optional — the S3 regression stops before S3.**  
   [test_stage3_legibility.py:655](/Users/aravind/KruxAI/tais-project-selection/work/checks/test_stage3_legibility.py:655).  
   Despite its name, the test checks only `item_stat`. A future S3 filter based on L availability could restore the original **6/44 false pass instead of 10/48 failure** without failing this test. Exercise that scenario through `family_analysis`; partial-data regime/retest/paired checks would also protect the downstream consumers.

3. **Optional — stray opening brackets in prose reject otherwise valid scores.**  
   [stage3_legibility.py:465](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:465).  
   An isolated check confirms that `Note [draft` followed by valid score JSON returns `None`; fenced JSON succeeds. This follows the documented “malformed structure anywhere” policy, but ordinary prose can therefore trigger paid re-asks and eventual missing scores. Document this tradeoff in a regression or distinguish prose brackets from JSON envelopes.

4. **Optional — item JSON drops the new metric-specific statuses.**  
   [stage3_legibility.py:961](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:961).  
   With a missing whole and complete parts, exported JSON contains `D_part=1` alongside generic `status:"missing"`, omitting `D_part_status:"computed"`. Condition statuses permit reconstruction, so statistics remain correct. Export both metric statuses.

5. **Optional — retest documentation describes the superseded centring.**  
   [stage3_legibility.py:967](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_legibility.py:967).  
   The docstring still says the mean “over both repeats” is removed. The implementation correctly removes separate repeat means; following the docstring during maintenance could restore the old bias.

All `mode_run` validation checks precede client construction and paid requests. The permitted metadata checks passed: **142 unique sorted items**, honest/false-target/retest draws, pool hash, script/configuration/dependency hashes, and the estimate’s price-snapshot hash. The rendering pins are present; recomputing them would require barred inputs. The current **$28.23 central / $54.02 upper / $56.47 stop** estimate remains explicitly pre-routing.

**Verdict: add the price/routes regression and pass the offline suite first. Then the instrument is safe to run once Aravind approves the final route-priced estimate.**