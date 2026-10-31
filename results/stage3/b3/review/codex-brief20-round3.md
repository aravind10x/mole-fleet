**The main computational fixes check out, but completion alone will not make the report ready to hand over.** The too-thin coverage check remains incomplete, the model description is stale, and reliability rejection introduces an aggregation error.

Verified SHA-256: `f78e68cf371f020ca66e38c829417147ddbcd670846987e36653a83354b5d435`. **36 tests passed; 3 were deselected because they read barred inputs.** No files changed; no network, judge, Docker, `simulate` or `sensitivity` commands ran. The information barrier was respected.

All source references below are to `work/checks/stage3_b3_power_v3.py`.

1. **Fixed — form (a)’s calibration computation.**  
   [460–483](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:460) constructs excess using singleton means over Q placements and regresses it on true composition with form (a)’s covariates, subtracting the null coefficient. Alternatives are calibrated separately for Q=1 and Q=2 at [878](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:878). The recovery test at [test:414](/Users/aravind/KruxAI/tais-project-selection/work/checks/test_stage3_b3_power_v3.py:414) passes.

   **Report description still wrong:** [1194](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1194) describes the old regression of triple score with the true maximum held fixed. This contradicts both the implementation and the corrected calibration-table description at [1371](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1371). It should describe the excess coefficient, its null subtraction and its dependence on Q.

2. **Fixed — final-carrier eligibility.**  
   [1020–1032](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1020) requires a readable carrier whose bias is explicitly nonmaterial, including directly selected layouts and S1→S2 fallbacks. No eligible carrier produces `unresolved`, and the first line reflects that. The corresponding regression tests pass.

3. **Fixed — failure boundary, unknown bias and conditional reporting.**  
   [564](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:564) counts whole failed replicates. [983](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:983) represents unavailable bias as `material=None`; it cannot clear eligibility. [1444](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1444) explicitly labels the means as conditional on successful fits.

4. **Not fully fixed — too-thin coverage.**  
   The five states exist, but [1052–1057](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1052) skips layouts absent from `sens_layouts` and checks only null-cell coverage.

   **Reproduced:** primary T1 and T2 both have P(present)=0.4; the tail run contains only T1 with 0.5 and its null cells. Passing `sens_layouts=["T1"]` returns **`not_too_thin`, missing=[]**, although T2’s tail result is unknown. Likewise, complete null cells plus a missing alternative produce `not_too_thin`. A negative verdict therefore still needs an independent completeness check before it licenses termination.

5. **Fixed — exact O4 reading.**  
   [633–655](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:633) separates line-only from joint line-and-gap movement. A synthetic check with flat conditional line visibility and composition-dependent gap left line-only O4 unchanged while the joint reading changed. Both are correctly labelled at [1431](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1431).

6. **Fixed — requested provenance binding.**  
   [1559–1568](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1559) checks every raw file listed in the inputs record and returns script/input hashes before computation. Both execution paths call it before loading the design. A synthetic mismatch test stops correctly. I did not execute the real raw-file audit because those files are barred. The smoke report’s provenance failure is expected.

7. **Fixed — “not read” arithmetic.**  
   [927–930](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:927) sums floor and unfit within each ICC before taking the maximum; [1410](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:1410) renders that value.

The optional improvements are implemented: reliability validity checks, separate plain Spearman–Brown readings, and conditional-interval labels. **One new error accompanies reliability rejection:** [805–815](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:805) assumes optional corrected readings exist in every experiment whenever they exist in the first. Using actual `form_a` outputs with one valid and one invalid reliability, I reproduced:

- Valid experiment first: `summarise_cell` raises **`KeyError: '75v50_disatt'`**.
- Invalid experiment first: the corrected reading is silently omitted for the entire cell.

This is a possible failure path, not a claim that the final empirical run encounters it.

**Verdict: not automatically safe after completion—verify full tail coverage and corrected-reading availability, and attach a correction to the stale estimand description before handoff; leave the margin-boundary gate explicitly with the coordinator.**