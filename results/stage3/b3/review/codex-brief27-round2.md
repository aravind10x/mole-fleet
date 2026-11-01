**One required fix remains: the fingerprint check still permits stale results when inputs change during a run.** The application fixes and both optional fixes look correct.

**Required fix — bind fingerprints to the inputs used by the run.** At [stage3_b3_lone_line_check.py:454](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_lone_line_check.py:454), `write_part` computes the fingerprint **after** the calculation finishes. Failure scenario: the harness imports module A, starts a long check, then the module file changes to B. The completed A result receives B’s fingerprint, and [check_parts:465](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_lone_line_check.py:465) accepts it alongside current B inputs.

I reproduced that acceptance with mocked file reads and output writes. Capture the input fingerprint before loading/running the inputs, carry it with the result, and reject changes before saving. The present fix correctly rejects changes made **after a part was saved**, but does not close this remaining path.

| Change | Assessment |
|---|---|
| Every delivered edit checked | **Fixed.** [stage3_t1.py:1195](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:1195) includes delivered duplicates, uses the duplicate bit in the event ID, and checks each row’s own preceding state. The round-1 ambiguity scenario is now refused. |
| Explicit line exclusions | **Fixed.** [stage3_t1.py:1133](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:1133) distinguishes omitted exclusions from `()`. [The harness:277](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_lone_line_check.py:277) explicitly acknowledges independent applications. |
| Draw-log metadata | **Fixed.** [stage3_t1.py:1150](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:1150) resets the log and inspects the pool with the correct anchors, exclusions and day. `_PoolOf` consumes no seeded randomness; restricted applications reject authors outside that pool. |
| Part fingerprints | **Partial:** saved stale parts are rejected; the during-run scenario above remains. |
| Duplicate item IDs | **Fixed.** [Harness:188](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_lone_line_check.py:188) counts duplicates on either side before dictionary collapse, preventing the previous false reproduction claim. |
| Manager rejection | **Fixed.** [stage3_t1.py:1159](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:1159) translates application `ValueError` into restricted refusal; default mode still raises. |
| Record text safety | **Correctly handled.** Records remain unsuitable for export; [the replay:135](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_lone_line_check.py:135) exports their hashes. I found no new text-export path. |

The permitted tests passed: **30 passed, 1 skipped, 3 deselected**. Additional fixture checks established:

- **120 applications:** pre-change module versus default `PartSInserter`, with identical records, rows and final RNG states.
- **45 applications with nonempty exclusions:** default layout/application versus restricted application, again identical on all three measures.
- All **17** brief-26 `module_line` needles remain unique; brief 26’s script hash is unchanged.

I found no default-mode three-arm regression, unintended restricted-selection RNG consumption, unchecked successful restricted return, or E3 isolation regression. [The per-application deep copy:610](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_t1.py:610) remains intact, and the isolation test still checks distinct row objects, unchanged null state and order independence.

No files were modified, no network was used, and no barred inputs or expensive harness modes were accessed. Final-module replay and E4 reproduction remain pending; the reported round-1 reproduction does not establish those final results.

**Verdict: Not yet safe to commit and use for S1/S3—the during-run fingerprint gap remains, and final-module replay/E4 evidence is pending.**