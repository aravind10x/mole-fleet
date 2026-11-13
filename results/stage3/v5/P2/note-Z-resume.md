# Block Z: resume note (blue harness session, 2026-11-14), written before the resume and without reading any outcome

**What failed.** Both aborts (subset_2 and subset_5, GPT-6 Sol, repeat 2) carry the code `validation:model_returned_error`. Bedrock relayed an error from the model's own turn and named no request field. I derived the code by script from the red-side error log: the two stored messages were complete (63 characters each, identical) and matched a fixed list of patterns. No text was printed.

**What changed** (coordinator ruling, 2026-11-14). This code no longer aborts the block:
- The same turn is re-asked with the same history, at most 2 times. Each re-ask is counted per run (`n_model_error_reasks`).
- A run still failing ends `infra_error` with `infra_cause: model_returned_error`, and the block continues. Such runs are unresolved and fall under v1 and v1.1's adverse missing-run rules.
- Every other ValidationException code still aborts, with a content-free `abort_code` on the blue side and the full provider message in the red-side error log.
- `--retry-unresolved` now refuses a block whose latest records show a stop. The one retry pass therefore runs only after a clean finish.

The change applies to every arm and follower. Hashes:
- harness `stage3_ft_harness.py` 8dbcaec1930f634a18800af3c0e1e24be939688c055c3d50de2ecc89b20d8665 (test cafb6012…, 52 pass);
- runner `stage3_ft_run.py` 46968e3f523f5a82a688b0ac6ffa9d443ad84d5b30f52544a6dda96aeafd7a52 (test 201850cc…, 46 pass);
- fork commit 7b0756f.

A fresh dry run of the dose line passed: 576 planned, 96 of 96 workspaces, 12 of 12 predicates, and expected hashes 5e4a1dbf / 4737b1ca / 543ab3ec.

**What stands.** The 50 runs finished before the fix stand: 25 Kimi and 25 Sol, the Sol runs under the old handling. That includes the 10 from the unguarded retry pass disclosed in `result-Z.md`. The 526 runs without a verdict (1 `aborted`, 525 `not_run_stopped`) run now under the fixed modules, with one guarded retry pass after a clean finish.

**What Z's result will report:**
- re-asked turns and runs ending `infra_error` for this code, by arm and follower;
- if such runs exceed 5 percent of one follower's runs, the block is finished but not joined, and the coordinator is told.

**Same handling for D, W and H.** The fixed harness and runner are the ones D, W and H will use.
