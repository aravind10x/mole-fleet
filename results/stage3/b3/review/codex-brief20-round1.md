**The gate outcome is not yet safe to use to end B3 or adopt a layout.** I found bugs that survive the document-fallback fix, plus a structural problem in the preregistered gate.

I made no changes and ran no network, judge, Docker, simulation or sensitivity commands. The permitted tests passed: **25 passed, 3 deselected** because those three would open barred inputs. I treated the supplied output numbers as superseded diagnostics.

1. **Required fix — the gate penalizes an unbiased estimator at the stated alternative.**  
   [brief 15:210](/Users/aravind/KruxAI/tais-project-selection/briefs/15-b3-distributed-visibility-2026-10-28.md:210), [stage3_b3_power_v3.py:807](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:807).

   “Present” requires both LB > 0 and point ≥ 0.3. At truth exactly 0.3, a regular, median-unbiased estimator therefore has P(present) approximately **0.5**, even with excellent precision. Attenuation pushes it lower, potentially toward zero as precision increases. Requiring ≥ 0.6 can reward upward bias and reject an otherwise informative experiment.

   **Failure scenario:** doubling placements narrows intervals and reliably detects a positive effect, yet the layout remains “unreadable” because estimates fall just below 0.3. Tail doubling does not resolve this structural problem.

   This faithfully implements A6; it requires a **coordinator-level specification decision**, not a silent code adjustment. Consider detection probability, or power at an alternative strictly above the decision margin. The supplied report does **not** explain this boundary problem.

2. **Required fix — failed calibration searches silently return invalid parameters.**  
   [stage3_b3_power_v3.py:340](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:340), particularly the call at line 406.

   `_bisect` never checks that its endpoints bracket the target. An unattainable SD can therefore send the search toward the upper endpoint instead of reporting failure.

   **Observed scenario:** Sonnet live dossier’s sham SD target is **5.007**. At 5-point noise, the supplied calibration achieves **22.127** at ICC 0.3 and **22.102** at ICC 0.6. Its simulated planted-unit sham flag rate becomes about **0.052**, versus the empirical **0**. The report nevertheless says calibration matches the sham moments.

   This changes the floor and can suppress readability. Check brackets and achieved tolerances; explicitly handle incompatible noise/moment combinations. This code is unaffected by the subsequent O3 fix.

3. **Required fix — non-converged reduced fits still produce partition verdicts.**  
   [stage3_b3_power_v3.py:528](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:528), [stage3_b3_power_v3.py:553](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:553).

   The new fallback addresses excessive failures **with** the document factor. After dropping it, however, `point_converged=False` and failed bootstrap replicates remain eligible for percentile intervals and four-outcome classification. Even with the factor retained, up to 2.5% failed fits remain in the interval calculation.

   **Reproduced scenario:** 78 all-flagged observations returned:

   - `point_converged=False`
   - `boot_nonconverged=1.0`
   - interval width approximately \(10^{-12}\)
   - outcome **“excluded”**

   A failed fit must not become evidence for exclusion. Define the final failure policy and test separation and bootstrap failures after fallback. The existing ordinary-MLE agreement test does not cover this.

4. **Required fix — form (a)’s alternative is a latent coefficient, not necessarily its stated observable slope.**  
   [stage3_b3_power_v3.py:609](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:609), [stage3_b3_power_v3.py:719](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:719).

   The code sets β = m_s/25 **before clipping and rounding**, but classifies the fitted slope of observed excess against m_s. Clipping changes that population slope independently of composition measurement error.

   **Reproduced scenario:** with no composition or call noise, a constant true line score of 50, compositions spanning 16.5–85, and latent slope × 25 = **53**, the observable population OLS slope × 25 is only **46.11**.

   Thus low P(present) partly reflects a different observable truth from the advertised alternative. Calibrate or report the error-free observable estimand after the score transformation; distinguish clipping from measurement attenuation. If “latent shift” is intentionally the truth, label it accordingly rather than calling it the fitted score-level slope.

5. **Required fix — the bias-trigger switch can adopt an unreadable fallback layout and retain the wrong carrier.**  
   [stage3_b3_power_v3.py:872](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:872), [stage3_b3_power_v3.py:1045](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1045).

   The switch simply replaces `S1` with `S2`. It does not re-establish readability or implement A6’s instruction that the other form carries the partition when residual bias remains material. The first line then quotes the **original layout’s** carrier and probabilities.

   **Reproduced scenario:** a readable T1+S1 with exclusion/presence probabilities 0.8/0.8 was switched to T1+S2 whose probabilities were 0.1/0.1. The final adopted layout was still T1+S2.

   Recompute the final carrier, readability and quoted probabilities after the switch, accounting for forms whose residual bias remains material.

6. **Required fix — missing tail sensitivity becomes a terminal verdict.**  
   [stage3_b3_power_v3.py:975](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:975), [stage3_b3_power_v3.py:1052](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1052).

   An unavailable tail-doubling run produces `too_thin=False`, followed by “B3 ends.”

   **Observed scenario:** the supplied JSON says `tail_doubled_available=False`; the report nevertheless declares termination. A later tail result could license A6.7’s writing round.

   Represent this as **pending**, and withhold the terminal first line until the required branch is evaluated. The first line meets brief 20’s literal “names layout or none” format, but currently overstates completion.

7. **Required fix — two interpretive claims are unsupported or contradicted by the output.**  
   [stage3_b3_power_v3.py:1030](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1030).

   The renderer says marginal truth is flatter and needs a larger β. That is not universal: for Opus live dossier at ICC 0.6, conditional β is **3.391**, while marginal β is **2.829**. At the conditional calibration, the marginal contrast is **0.352**.

   Line 1031 also calls zero writer/edit/document effects “conservative” because real effects would add power. There is no such guarantee: they can move probabilities toward a ceiling or floor, and dropping the document factor can leave confounding.

   **Failure scenario:** the coordinator dismisses a sensitivity as artificially favorable, or treats the primary assumptions as a lower bound on power. State these as modeling assumptions, without those guarantees.

8. **Required fix for full A6 fidelity — two beside readings are absent.**  
   [stage3_b3_power_v3.py:552](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:552), [stage3_b3_power_v3.py:1204](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1204).

   The implementation supplies the mean-covariate and Q1–Q3 contrasts, but not A6.4/O4’s contrast using the line covariate’s **conditional mean at each composition point**. It reports reliabilities, but does not calculate A6.5’s **disattenuated sensitivity**.

   **Failure scenario:** exclusion is attributed to an absent composition effect without showing how much changes under the mandated correction. Brief 20 P3’s narrower numeric inventory is substantially present; these remain gaps against the broader A6 requirements.

9. **Required fix — output provenance does not bind results to their generating code.**  
   [stage3_b3_power_v3.py:983](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:983), [stage3_b3_power_v3.py:1261](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1261).

   The report records the script hash **at rendering time**. The simulation artifact does not carry and validate its generating script/input hashes.

   **Failure scenario:** rendering the first-run simulation with today’s renderer gives it today’s code hash and current-method wording, although its fits used the superseded fallback. Record provenance when generating each simulation/sensitivity artifact and validate compatibility before reporting.

The following checks otherwise support the implementation:

- **Models and clustering:** both forms include the requested covariates; form (b) uses the judge’s continuous singleton maximum with the arm and the rater’s top line without it. Payload weights correctly keep placements and singleton measurements together. The AUROC bootstrap correctly resamples both payload groups, retains placements, and handles ties.
- **Floors and partition:** floor failures replace outcomes with “floor,” so they do not count as excluded. The four-outcome inequalities and Q1–Q3 scaled margins are implemented correctly. Singleton preference and the documented worse-ICC selection are implemented.
- **P3 output inventory:** floors, exclusion/presence/attenuation/inconclusive probabilities, residual bias, widths at 75, writer imbalance, Q1–Q3 results and reliability values are present. I found no numeric transcription discrepancy in the checked report tables. All **35,858 numeric JSON entries** were finite; that does not establish their statistical validity.

For **m_s**, I independently recovered these B1 cells:

| Instrument | n | Scores ≤ t | 26th descending eligible score | Reported m_s |
|---|---:|---:|---:|---:|
| Opus isolated | 84 | 45 | 30, with t = 62 | 32 |
| Sonnet isolated | 84 | 52 | 72, with t = 83 | 11 |
| Opus live | 84 | 10 | Insufficient eligible scores | 9.36 fallback |
| Sonnet live | 84 | 41 | 15, with t = 68 | 53 |

**Optional clarification — endpoint convention:** [stage3_b3_power_v3.py:277](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:277) implements a closed lower endpoint, not the literal open interval. At D = 32, Opus isolated contains **26** plants under the closed rule but **21** under the open rule. This is defensible as the **infimum required shift**, with an arbitrarily small additional shift; label it that way. Using the planted unit’s score follows the specified score pool. The union-and-ties shift is appropriately shown beside: **44** and **18** for the two isolated cells, rather than 32 and 11.

For **form (b)’s truth**, I would retain the **conditional-at-mean true-line definition** as primary because it follows O2 more closely than averaging over line heterogeneity. I would keep marginal truth beside and avoid choosing it because it passes the gate. However, the Gaussian-threshold DGP with an honest-path mixture is not exactly logistic, and the measured singleton maximum is not the true maximum. The report should distinguish its scientific truth from the fitted model’s population approximation.

The generative assumptions have mixed effects:

- The ICC algebra is correct for the **null latent score before call noise**. Adding the composition term changes total alternative-state ICC; label the supplied ICC as the null/residual ICC.
- Matching quiet flag rate and SD, and sham mean and SD, is intentional; matching those moments does not preserve score shape or ceiling behavior.
- The independent honest path can favor the floor. For example, Opus `P_author` quiet recall is **0.559** empirically but approximately **0.577** under that independence construction.
- ρ = 0.5 is an assumption; an author-level AUROC does not uniquely identify a line-level correlation. The pending sensitivities matter before interpreting robustness.

On **residual-bias direction**, the supplied simulation generally disagrees with A6.5(iii)’s prediction for form (b): singleton layouts mostly have **positive null bias**, approximately +0.02 to +0.075 across the instruments and ICCs at 5-point noise. The report correctly labels these rows “toward a false present.” Alternative-state attenuation does not establish that singleton-max inflation caused a false-excluded bias. State that disagreement explicitly; no old-run 5-point residual triggered the specified bounds.

For **P4**, the accounting is internally consistent: each view gets \(124P\) triple/control/sham units; each of six per-agent instruments additionally gets \(234Q\) singleton units. Three `O_diff` judges receive the lone units, including Sol. The six layout totals are **1,116; 2,232; 2,520; 3,636; 3,924; 5,040** units, costing **$20.74; $41.49; $49.09; $69.83; $77.43; $98.17**. The control-singleton add-on is separate, and no cap is applied. B1 dossier cost bases matched their source accounting. I did not reopen barred T1 v3 score files to independently validate those cost bases.

Two further **optional** report improvements are worthwhile:

- [stage3_b3_power_v3.py:1114](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1114): headers emit two backslashes before internal pipes; use one Markdown escape so the tables render correctly.
- [stage3_b3_power_v3.py:804](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:804): identify ICCs alongside worst-case summaries and show Monte Carlo uncertainty. At 300 experiments, a probability near 0.6 has SE about **0.028**; the combined worst-case columns are not one outcome distribution.

**Verdict:** withhold adoption or termination. First resolve the boundary gate with the coordinator, fix calibration and failed-fit handling, align observable truth and fallback selection, then complete the sensitivities and regenerate a provenance-bound report. The supplied “B3 ends” sentence is premature.