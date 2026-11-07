You are reviewing one research pipeline step, read-only. Do not modify any file, do not make network calls, do not run any model or judge call, and do not run the scorer.

**What to review.** The Phase B readings code and its report:
- `work/checks/stage3_phase_b_readings.py` and its tests `work/checks/test_stage3_phase_b_readings.py` (you may run `work/mole-fork/.venv/bin/python -m pytest work/checks/test_stage3_phase_b_readings.py -q -p no:cacheprovider`);
- the report `work/stage3/phase-b/phase-b-results.md` and its record `work/stage3/phase-b/phase-b-results.json`;
- the rules they must implement: `work/stage3/phase-b/preregistration-v1.2.md` §2, §5 and §6 (committed by hash 414cecc3), and `briefs/38-phase-b-kill-test-2026-11-07.md` dated notes 3 and 4;
- the helpers they reuse: `fit`, `rec`, `recorded` and `names_in_headers` in `work/checks/stage3_phase_b_dryrun.py`; the threshold rule in `work/checks/stage3_thresholds.py`.
You may read the scorer `work/checks/stage3_phase_b_score.py`, the B1-all module `work/checks/stage3_phase_b_b1all.py`, and the inputs `work/stage3/phase-b/nulls-v0.json`, `applications-v0.json`, `dryrun-v1.json`.

**Do not open** (barred inputs): anything under `work/stage3/red/`, `work/stage3/elicitation/part3/`, `find-the-plant/`; any file whose name starts with `judge-cache`, `archived-scores`, `stripped-` or `key`; `cache-s3/`; any `.env`; the T1 payload, plant and planting-list files (`payloads-*.json`, `plants-*.json`); the corpus transcripts. No statement, task or rationale text may be printed.

**Questions.**
1. Does `verdict()` implement v1.2 §6 exactly: the fixed order (kill, context, separability, survives, inconclusive), kill on U(D_h) < m_kill, separability's first branch L(c_net) > 0 and U(c_net) ≥ D_net, its judge-side branch, the not-calibratable fallback, and survives' four conjuncts?
2. Are the intervals what §4 and §6 say: 2,000 replicates on one shared index set across arms, the 18 (document, boundary) chains resampled with their null units and applications together, each arm's threshold re-fitted on its own resampled null, 95 percent percentile bounds? Any arm or population read on a different index set?
3. Are D_h, D, D_net, r − r′, B4 − B1, c, s_c, c_net, B5′ and B5-applied computed on the right populations (the 96 routine-and-middle, the 96 comparison, the 64 conforming) and the right arms?
4. Are refused or errored units handled as stated (excluded from the null's threshold; not flagged on applications; counted for D1 at 5 percent)?
5. Are the drift check (fresh r₀ against the recorded r₀, δ) and the test–retest row (SD of fresh − recorded scores, nearest dry-run row) computed as v1.2 §2 says?
6. Does every figure in `phase-b-results.md` match `phase-b-results.json`, with its label right? Is anything claimed that the record does not support?
7. Anything else that would change a reading or the verdict.

**Answer format.** For each finding: severity (required / advisory), the file and line, what is wrong, and the concrete fix. End with one line: "Verdict: the readings stand" or "Verdict: the readings change" and why.
