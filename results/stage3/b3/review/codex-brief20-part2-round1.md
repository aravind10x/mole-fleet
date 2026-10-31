Three required fixes remain. **46 tests passed; three data-dependent tests were deselected to preserve the information barrier.** I made no edits and ran no simulation subcommands.

1. **Required fix — Firth iteration can oscillate despite a finite optimum.** [stage3_b3_power_v3.py:528](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:528)

   The frequency-weighted hat diagonal and adjusted score are correct. The problem is the undamped Fisher-scoring update: component clipping does not ensure convergence.

   Reproduction: 78 observations, an intercept and a document indicator present only on observation 78; outcomes are 20 ones, 57 zeros, then one. Starting from zero, `irls(..., firth=True)` returns coefficients approximately `[-1.03136, -0.313799]`, unconverged, after both 30 and 200 iterations. The analytic Firth optimum is `[-1.03136, 2.129972]`.

   A sparse document—or bootstrap weights leaving one effective observation in a document—can therefore cause an unnecessary document-factor fallback or unfit result, changing supporting labels and operating characteristics. Add penalised-likelihood step halving or another safeguarded optimiser, with this regression case. Increasing the iteration limit alone does not fix it.

2. **Required fix — adoption and joint reporting can use different carriers.** [stage3_b3_power_v3.py:1817](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1817), [stage3_b3_power_v3.py:1913](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1913)

   Adoption promotes `P_author` to “fallback carrier” whenever the isolated dossier has no readable layout. The joint run always retains the isolated dossier as carrier, falling back only when its experiment-level label is floor or unfit.

   Failure scenario: the isolated dossier fails the gate but produces *excluded*; readable `P_author` produces *present*. Adoption names `P_author` as carrier, while the joint rule returns *inconclusive*. The report’s first line then pairs one carrier with another policy’s operating characteristics.

   A6.13.4 authorises fallback on **floor or unfit**, not merely unreadability. Keep that distinction consistent across adoption, joint simulation and reporting.

3. **Required fix — a failed bias-triggered move prematurely ends layout selection.** [stage3_b3_power_v3.py:1830](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1830)

   After moving the best S1 layout to S2, adoption immediately returns, even if that destination is unreadable and another eligible layout remains readable.

   Reproduced scenario: carrier `T1+S1` scores 1.9 and triggers on (b)’s bias; `T1+S2` fails the gate; carrier `T2+S2` scores 1.8, passes, and has non-material (a) bias. The function nevertheless adopts descriptive `T1+S2`.

   Complete selection among eligible readable alternatives before taking the descriptive route. This also needs a test beyond the current successful-trigger case.

The requested design decisions check out as follows:

| Decision | Assessment |
|---|---|
| β* fixed per instrument at ICC 0.3, noise 5 | **Right:** matches the quoted calibration cell and is documented. |
| β* and 1.5β* used for both forms | **Right:** these are latent-effect multiples; nonlinear observed contrasts need not equal 0.3 and 0.45 elsewhere. |
| New m_s from the existing error-free (a) helper at β*, Q=1 | **Right:** old values remain labelled superseded; drift is retained in JSON. |
| Each gate probability evaluated at its adverse ICC | **Right:** inequalities and unconditional treatment of not-read outcomes match A6.13.1. |
| Carrier score and residual-bias thresholds | **Right in their arithmetic:** the selection defects above remain. |
| Joint sharing and seeding | **Right:** composition, sham latent draws and standardised line deviations are shared; placement/call draws remain independent. Seeds are deterministic and worker-independent. |
| Same instrument/layout/ICC null bias for (b) downgrade | **Right.** |
| Second-instrument unreadability drop-out | **Right.** |
| Ceiling applied per experiment to observed quiet recall | **Right under the stated operational interpretation:** strictly above 0.85. |

`instrument_label` and `combine` themselves implement A6.13.4 correctly: only excluded/present conflicts cause a downgrade, one-step conflicts preserve (a), and (b)’s positive labels require the bias-corrected LB to remain positive. Crucially, the code correctly retains (b)’s original label after that eligibility check. The carrier inconsistency arises in integration with adoption.

Two optional reporting corrections:

- **Live-view (a) eligibility:** [stage3_b3_power_v3.py:1732](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1732) simulates live-view singletons as independent and the report calls some such cells readable. Label these explicitly counterfactual/not applicable to the live layout: A6.13.3 says sibling visibility prevents that reading. Otherwise a reader could mistake numerical gate clearance for operational eligibility.
- **Table descriptions:** [stage3_b3_power_v3.py:2090](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:2090) promises Monte Carlo SE but prints none. The Markdown drift table also shows only 5-point noise despite broader wording; identify the remaining drift grid as JSON-only.

The smoke JSON’s provenance check passes, and its P4 estimates are exactly identical to the first-run report. Its numerical results were not treated as evidence of power.

**Verdict: the extension is not safe to commit and run until the three required fixes are addressed.**