**Not yet safe to hand over as a decision-ready report.** Several fixes work, but the revised form (a) calibration still targets a different estimand, and the bias-switch logic can still declare an unsuitable layout adopted.

The script hash matches `742dd6b2…`. The permitted tests passed: **31 passed, 3 deselected** because they read barred inputs. I made no changes, opened no barred content, and ran no network, judge, Docker, `simulate` or `sensitivity` commands. I used the smoke report only to inspect structure and accounting, not to infer power.

All script references below are to `work/checks/stage3_b3_power_v3.py`.

1. **Required fix — form (a)’s observed-slope calibration still does not match form (a)’s estimator.**  
   [Calibration:473](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:473), [null subtraction:479](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:479), [estimator:655](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:655).

   Calibration regresses the **triple grid score** on true composition, controlling for the **true maximum**, but omitting the gap. It then subtracts the null coefficient. The fitted form regresses **excess** on composition and the **singleton gap**, without controlling for the maximum. Clipping makes the composition response depend on line visibility, so these are different population coefficients.

   **Reproduced failure:** with correlated composition and line visibility, but **no composition, call or placement noise**, calibration to slope × 25 = 25 returned approximately **25.09**; the actual error-free excess regression returned **20.32**. Thus the [summary’s claim:1202](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1202) that the remaining shortfall is measurement error and finite-sample behaviour, rather than clipping, is unsupported.

   Calibrate the error-free coefficient of the actual form (a), or explicitly retain this different scientific estimand and quantify its gap from the fitted estimand. “Unattainable” currently refers only to the calibration’s estimand.

2. **Required fix — rereading the fallback’s probabilities does not make the adoption logic correct.**  
   [Switch:974](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:974), [eligibility:983](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:983), [adoption:992](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:992), [first line:1244](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1244).

   Three failures remain:

   - An unreadable S2 fallback remains in `adopted`; the first line still calls it **“Adopted layout (A6.6 gate)”**, albeit with a coordinator caveat.
   - If **both** forms retain material bias, `or ["a", "b"]` makes both eligible again. I reproduced `final_readable=True` with both forms material.
   - If the gate selects S2 **directly**, the S1-only branch skips residual-bias eligibility entirely.

   **Failure scenario:** S2 form (a) passes 0.8/0.8 but has material bias; the clean form (b) fails 0.2/0.2. The code still lets (a) carry.

   Apply materiality eligibility to every final carrier. If no eligible form is readable, report an unresolved fallback decision rather than an adopted readable layout. The [new test:370](/Users/aravind/KruxAI/tais-project-selection/work/checks/test_stage3_b3_power_v3.py:370) currently preserves the unreadable-adoption behaviour.

3. **Required fix — failed-fit handling is substantially improved, but its boundary and missing-bias handling are wrong.**  
   [Failure threshold:602](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:602), [final acceptance:609](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:609), [summary:781](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:781), [bias trigger:958](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:958).

   Failed point fits now correctly produce `unfit`; accepted intervals use converged replicates only. The exclusion denominator remains **all experiments**, correctly preventing failed fits from becoming evidence for exclusion.

   However, exactly **25 failures out of 1,000** produce `1 - cb.mean() = 0.025000000000000022`, which exceeds `0.025`. This violates the stated **more than 2.5%** policy. Compare integer failure counts instead.

   Separately, when no point fits survive, `point_mean` becomes NaN. `residual_bias` then evaluates `abs(NaN) > bound` as false, recording **`material=False`**. Applying the current function to the smoke artifact reproduces this.

   **Failure scenario:** an unavailable bias estimate is treated as clearance from the bias trigger. Represent it as unknown, not nonmaterial.

   The policy can also substantially reduce \(P(\text{excluded}\mid0)\): that probability cannot exceed the share receiving valid verdicts. This is correct conservative accounting, but the report should distinguish fitting failure from inadequate statistical precision. Its point means and bias estimates are **conditional on successful fits**, which should be stated.

4. **Required fix — “too thin” distinguishes a wholly missing run, but not an incomplete run or a nonapplicable check.**  
   [Check:1001](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1001), [summary:1207](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1207), [first line:1248](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1248).

   Any nonempty tail table counts as available. A partial table with no passing row yields `too_thin=False`, even if an omitted instrument or relevant layout would pass.

   **Reproduced failure:** supplying one failing tail row returns “not too thin,” with no coverage check.

   There is another conflation: if primary \(P(\text{present})\ge0.6\), the function returns `None`. If exclusion power prevents adoption, the renderer interprets that `None` as **missing tail sensitivity**, even when the run exists.

   Use explicit states for complete/pending/not-applicable, and verify coverage before a negative tail verdict.

5. **Required fix for exact O4 fidelity — the new reading moves both line visibility and gap.**  
   [Conditional means:617](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:617), [prediction:624](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:624), [A6.4:204](/Users/aravind/KruxAI/tais-project-selection/briefs/15-b3-distributed-visibility-2026-10-28.md:204).

   O4 requests the same contrast with the **line covariate** at its conditional mean. The implementation also moves the gap to its conditional mean.

   **Failure scenario:** conditional line visibility is flat, but gap rises with composition and has a positive coefficient. The implemented sensitivity changes while the requested line-only sensitivity would not.

   Supply the line-only reading; the jointly moving line-and-gap reading can remain separately labelled. The linear conditional-mean approximation is disclosed.

6. **Required fix — provenance checks still do not bind the actual design read by the simulation.**  
   [Live design read:1490](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1490), [hash capture:1497](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1497), [report comparison:1104](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1104).

   The new simulation/input hashes and mismatch warning address the original render-time-only defect. But simulation reloads the design from raw files without checking them against `inputs["inputs_sha256"]`.

   **Failure scenario:** a pass file changes after the inputs JSON is created. Simulation uses the changed design, while the report successfully compares the unchanged inputs-JSON hash.

   Script and inputs-file hashes are also captured **after** the long computation. Editing either during execution can label results with files different from those loaded into memory.

   Capture provenance before computation and validate the raw files actually consumed. The smoke report’s internal consistency refers to its earlier `9bd1…` script, not the current `742dd…` script; that is expected for this supplied sample.

7. **Required reporting fix — the displayed “floor or unfit” probability adds maxima from potentially different ICCs.**  
   [Aggregation:905](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:905), [display:1342](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1342).

   The report adds `max(P_floor)` and `max(P_unfit)`.

   **Reproduced failure:** ICC 0.3 has floor/unfit = 0.7/0; ICC 0.6 has 0/0.8. The displayed probability is **1.5**, although the worst union probability is **0.8**.

   Add within each ICC first, then take the maximum.

The remaining round-one fixes check out as follows:

| Round-one finding | Verification |
|---|---|
| Margin-boundary gate | The structural problem remains, intentionally. The revised first line and summary expose the coordinator decision; detection and 1.5×/2× readings are present. This is adequate disclosure, not a repaired gate. |
| Calibration search | **Fixed for the reported defect.** Brackets, endpoint status, achieved values, tolerances and misses are recorded at [340](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:340) and [417](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:417); misses are rendered at [1315](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1315). |
| Failed fits | Core fix verified; remaining issues are finding 3. |
| Form (a) truth | Partial fix; finding 1 remains a blocker. |
| Bias switch | Correct final-layout numbers are reread, but finding 2 remains. |
| Missing tail | Completely absent run correctly becomes pending; finding 4 remains. |
| Interpretive wording | Marginal-truth direction, removal of “conservative,” residual ICC, honest-path independence, assumed ρ, and scientific truth versus fitted logistic approximation are now disclosed. |
| Beside readings | Both forms now have partial-reliability disattenuation. O4 remains incomplete as described above. |
| Provenance | Basic artifact comparisons and warnings work; actual-input binding remains incomplete. |

For **logistic disattenuation**, dividing the composition coefficient by reliability and recomputing endpoint probabilities is a sensible **log-odds-slope sensitivity**. It avoids the incorrect operation of dividing a probability difference by reliability. It is not an exact measurement-error correction for this threshold-mixture DGP, especially after averaging probabilities over factor levels.

Two **optional** improvements remain:

- At [634](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:634) and [668](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:668), reliability is held fixed across bootstrap draws; O4 likewise holds its estimated conditional-mean regression fixed. Label these intervals conditional on those estimated quantities, or propagate their uncertainty. Also reject nonfinite/nonpositive reliability explicitly; `if rel` accepts negative values and can reverse the corrected effect.
- The plain Spearman–Brown factor is reported but has no separate corrected reading; adding that beside the partial correction would make A6.5’s interpretation clearer.

The earlier optional endpoint clarification, Markdown pipe escaping, ICC identification and Monte Carlo uncertainty have been addressed. I found no new issue in the unchanged cost arithmetic, clustering or four-outcome inequalities.

**Verdict: completion of the final run alone will not make the report safe for adoption or termination.** Fix the estimand, carrier eligibility, missing-state and provenance issues, correct the reporting arithmetic, and regenerate affected artifacts. The margin-boundary gate should then remain an explicit coordinator decision.