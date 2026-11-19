# Check AM: pre-registration, addition 2: the analysis code frozen (blue harness session, 19 Nov 2026, 13:28 IST by `date`)

**Frozen before any score of the run exists.** The only scores so far are the two smokes, which are never read.

- **Module:** `work/checks/stage3_am.py` **de0057237780b4c52d42bcfa393c544f0e030fe53c677e5ff67bff15adff179a**.
- **Tests:** `test_stage3_am.py` cf931480…, 14 pass.
- **Fork commit:** 1d6617d (local, branch stage3, not pushed).

**What it holds:**
- the views and the join;
- the passes and the seeded order;
- the threshold, flags and sentences;
- `quantities` (R, the two-way and three-way shares, by follower, with the headline's bootstrap);
- the driver `analyse_pass`. For each pass and each rule (10, 5 and 2 percent) it gives:
  - per block, quiet and alarming quantities;
  - realised clean flag rates, quiet and alarming apart;
  - unscored counts and the unscored-flagged bound;
  - core: the positive, negative and combined audit weightings, and the questioning runs' flagged shares;
  - D: the positive weighting and questioning;
  - by consequence class (reader A);
  - the harmless arm against the planted carried runs and the clean runs on the same 16 payloads;
  - the two sentences (core and D, view T with prompt G, at the 10 percent rule).

**Inputs:** each is checked against its hash before use (`INPUT_SHA`).

**Checks on the real inputs:**
- with no action flags, the two-way share on the core reproduces the headline's 0.295 [0.188, 0.413];
- a dry run of every pass on hash-generated synthetic scores (not judge output) built every reading.

**What it does not change:** nothing in the pre-registration (21841e8b) or addition 1 (1da6168a).
