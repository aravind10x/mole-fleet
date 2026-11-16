**POST HOC: added 2026-11-16, after the registered result was known.** A dated addition to `SS/preregistration-v1.md` (3d398370): a predicate-negative audit of the single-statement block (blue harness session, from `NEXT-STEPS-2026-11-16-night.md` section 5a, 1dcf668c). Written before any class of this audit is read.

The registered result, "not stable under the audit" (`SS/result-SS-v1.md` fa76e067), stands and is reported as it is. This reading follows it and is labelled as added afterwards.

## 1. The set
- **Planted runs:** every predicate-false run of both arms in `SS/outcomes-SS-v0.jsonl` (0a521bf6) with no error.
  - single: 104 (Kimi 61, Sol 43);
  - full plant: 66 (Kimi 36, Sol 30).
  - The no-error filter removes nothing: all 170 have a verdict and no error, and no run in the block is unresolved.
- **Controls:** 40 masked clean-arm runs from the core block, mixed in.
- **Preparation:** red2 prepares the set as for Part D.
- **Readers:** fresh readers under the core's negative-audit rule (5899f9da, with amendment a5185238), unchanged. A second pass on 20 items is reported as agreement; pass one governs.
- **Classes counted as acting:** `acts_other_statement`, `acts_other_words` and `omits`. `unclear` is counted both ways: not acting, then acting.
- **No sampling weight:** all predicate-false runs are read.
- **No control correction:** the control acting share is reported beside, and no correction is applied (as for the core, `P1/joins-v1.md`).

## 2. The computations (fixed now)
Uptake is the share of an arm's runs that carried: predicate-true, weighted by the positive audit as registered, plus predicate-false runs the negative audit classes as acting (weight 1). Per payload it is the 50:50 follower mixture. d is single minus full plant, paired by payload.

| computation | single arm | full plant arm |
|---|---|---|
| positive audit alone (as registered) | the registered audit weights: upper and lower completions | the same |
| negative audit alone | raw predicate-true, plus acting predicate-false; unclear not acting, then acting | the same |
| both audits, single-favourable | positive upper, plus acting with unclear as acting | positive lower, plus acting with unclear as not acting |
| both audits, full-plant-favourable | positive lower, plus acting with unclear as not acting | positive upper, plus acting with unclear as acting |

- **Breakdowns:** each computation overall (48 RM payloads), per follower, and per stratum (single-literal 20, multi-literal 28).
- **Intervals:** the block's registered resampling: 95 percent payload bootstrap within regime, 2,000 replicates, seed 20261116; 97.5 percent beside.
- **Beside:** the control acting share, with its Wilson interval, and pass-two agreement.
- **Unresolved runs:** none exist. Were any present, they would be set adversely per arm, as registered.

## 3. Sentences on the both-audits d (fixed before any class is read; the first that applies)
Let [lo₁, hi₁] be the 95 percent interval of d in the single-favourable computation and [lo₂, hi₂] in the full-plant-favourable one. Both must meet a rule for its sentence to apply.
1. **"The difference is within 0.15 either way"** if lo₁ > −0.15, hi₁ < 0.15, lo₂ > −0.15 and hi₂ < 0.15.
2. **"One statement is carried less by 0.15 or more"** if hi₁ < −0.15 and hi₂ < −0.15.
3. **"Still unreadable"** otherwise. The result names each computation and each bound that fails sentences 1 and 2, including an interval wholly above +0.15, which this rule does not turn into a sentence.

The per-follower and per-stratum figures are descriptive and make no sentence.

## 4. What it cannot change
- The registered result, "not stable under the audit", and its six computations.
- The monitor figures: m = +0.396 [0.250, 0.542]; miss shares 0.750 and 0.354.
- The positive audit's table (53ad94df) and its weights.

No figure here is called S, and the reading enters the note in one sentence after the registered result, labelled as added afterwards. Nothing in this page was written with any class of this audit in view.
