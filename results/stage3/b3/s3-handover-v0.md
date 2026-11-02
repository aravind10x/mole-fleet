# S3 handover note (2026-11-02; the S3 session stops here on Aravind's instruction, relayed by the coordinator; $0, counts and hashes only)

## 1. The state as committed

- Fork `work/mole-fork` branch `stage3`: the S3 session's commits are be0a600 (plan.md's A1b note), 948865b (A1 to A2 and A4's code), 4545b48 (Stage A done), 151e69b (A3b), 1fafa57 (plan.md's dated note 3, the 27-entry block), 8f816e2 (the Stage A addendum under brief 33's dated notes 2 and 3). HEAD at writing: 457f66c (the coordinator's brief 33 dated note 4). The fork working tree was clean before this note.
- Stage A's record: `work/stage3/b3/s3-stage-a-v0.md` **e2166be2** (mirror equal), with its Hashes section as the authority for every Stage A file; rulings `s3-stage-a-rulings.md` (committed 2aad47b4; changed on disk, item 2).
- As committed, the pinned chain holds: plan.md 59a98c15 (27 entries), pre-flight PASS 27 of 27 (`s3-preflight-v0.json` 8e332d9b), readings script e31d8fba, dry run fd6eaedb (30 fixtures, operating characteristics accepted, identical to the first run), driver 4adc0716, clean-items file 21e7ede2, trace audit 5e232276 PASS.
- Brief 33's dated note 4 (G7 to G9 and the three adopted items) is **not** done as committed; the work started on it is listed in item 2 and is uncommitted.

## 2. Uncommitted files on disk from the dated-note-4 pass (not committed, not mirrored; a fresh session takes or discards them)

| path | sha256 | fork copy | contents |
|---|---|---|---|
| `work/checks/stage3_b3_s3.py` | 3159c540 | 4adc0716 | G7: `cell_status` counts `errored_once` (one errored record, the cell stays incomplete) and `errored_final` (two or more, unscored, the cell complete); `build_scores` writes an open unit as `errored_open` (left out of a stopped file's rows) and a final one as `errored`; `mode_score` refuses unless `s3-clean-items-v0.json` is at 21e7ede2; new mode `check` (G9: every per-agent unit's author and document against each honest source, an absent author explained only when the honest corpus holds no successful class-document write by that account; the zero-pair counts). The driver's 18 tests pass. |
| `work/checks/test_stage3_b3_s3.py` | 036a531c | 709fd4e7 | the G7 test (one record keeps the cell open, two complete it as unscored); the sealed-rule test updated for `errored_open`. |
| `work/checks/stage3_b3_s3_readings.py` | 98f875fc | e31d8fba | (b) a missing `flag_unit` is read as missing, never as the union's; the analysis lock honours every cell the stop record names even when its rows are present; (c) d1 and d2 at floor (a) join `at_floor_a` (no S-A4/S-A5); G8: the S-M block only under a lead that is not at floor (a); (a) `main` refuses unless the clean-items file is at 21e7ede2. Not re-tested by the full module (the run was stopped). |
| `work/checks/stage3_b3_s3_dryrun.py` | da9e0b90 | fd6eaedb | forbidden entries by id prefix and instrument, or by family alone; `floor_both` forbids S-M, S-D, S-E, S-G, S-K, S-L, S-O for C and S; two G7 fixtures (`errored_twice_unscored`, `errored_once_stopped`) with the spec knobs `errored` and `stopped_named`. Smoke-run of `floor_both`, both G7 fixtures and `floor_carrier`: all ok. The full 32-fixture run and the report were started and stopped before completion; `s3-dryrun-parts/` and `s3-readings-dryrun-v0.{md,json}` on disk are still the committed ones (equal to the fork). |
| `work/checks/stage3_b3_s3_record.py` | e2f6bb35 | 88abf367 | the addendum extended with a "Dated note 4" section (G7, G8, G9 from `s3-honest-pairs-check-v0.json`, the adopted items) and a third trace-audit line; not yet run. |
| `work/stage3/b3/s3-stage-a-rulings.md` | a11b9186 | 2aad47b4 | the G7 line restored to "re-asked once on a resumed run, then unscored". |
| `work/stage3/b3/s3-honest-pairs-check-v0.json` | 167d8b81 | none (new) | G9's result: PASS. Every honest source holds 89 pairs over 40 authors and 6 documents (the same author set in all five); the per-agent rows' 796 units are by 35 authors; documents absent 0; authors absent 2, both explained (no successful class-document write by either account in the honest corpus; 13 units); units with no other honest pair 73 of 796 per per-agent row (60 with the author's single pair on the planted document, 13 by the two authors), the live rows 26 of 232 (19 + 7); unexplained 0. |

## 3. How to run things (not in brief 33 or the record)

Interpreter: `work/mole-fork/.venv/bin/python` (3.12.9), always with `-I`, from `work/checks` (several scripts resolve paths from their own location; `stage3_b3_power_v3.bind_inputs` takes a path relative to the cwd).

| what | command (from `work/checks`) | time |
|---|---|---|
| pre-flight with the configuration | `../mole-fork/.venv/bin/python -I stage3_b3_preflight.py --config ../stage3/b3/s3-config-v0.json --out ../stage3/b3/s3-preflight-v0.json` | seconds |
| tests, fast modules | `../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_s3_matrix.py test_stage3_b3_s3.py test_stage3_b3_s3_trace_audit.py test_stage3_b3_lone_line_check_s3.py test_stage3_b3_preflight.py -p no:cacheprovider` | under 10 s |
| tests, readings (runs every fixture once, in parallel; `S3_FIXTURE_PROCS`, default 5) | `../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_s3_readings.py -p no:cacheprovider` | about 9 min |
| gated slow tests | `S3_SLOW=1 ...pytest -q test_stage3_b3_lone_line_check_s3.py test_stage3_b3_s3.py` (the reproduction compares to `s3-lone-line-check/lines.json`; the render test loads the corpus) | about 1 min |
| dry run, fixtures | `../mole-fork/.venv/bin/python -I stage3_b3_s3_dryrun.py fixtures --procs 5` (writes `s3-dryrun-parts/fixtures.json`) | about 7 min |
| dry run, operating characteristics (only if form (a) or the floor changes) | `... stage3_b3_s3_dryrun.py oc --procs 5` (writes `s3-dryrun-parts/oc.json`) | about 26 min |
| dry run, report (merges the two parts into `s3-readings-dryrun-v0.{md,json}`) | `... stage3_b3_s3_dryrun.py report` | seconds |
| G9's check | `... stage3_b3_s3.py check` (writes `s3-honest-pairs-check-v0.json`) | about 30 s |
| the packets and the pre-signal (no request) | `... stage3_b3_s3.py render` | about 1 min |
| the record (regenerates `s3-stage-a-v0.md`; also rewrites `s3-clean-items-v0.json` deterministically from the application file) | `... stage3_b3_s3_record.py` | seconds |
| the trace audit (the session's transcript; an empty `--writer-dir`) | `T=~/.claude/projects/-Users-aravind-KruxAI-tais-project-selection/<session id>.jsonl; ... stage3_b3_s3_trace_audit.py policy --trace $T; ... stage3_b3_s3_trace_audit.py audit --trace $T --out ../stage3/b3/s3-trace-audit-<stage>.json` | seconds |
| Stage B, first batch (after the gate line only) | `... stage3_b3_s3.py score` (pauses by itself after about 20 carrier item units; then `score --continue` on the coordinator's STATUS line) | B1 minutes; the rest hours |

Stage B needs the Bedrock environment the other scorers used (`AWS_REGION`, `AWS_BEARER_TOKEN_BEDROCK`, from `work/mole-fork/.env`; never print its values). `score` refuses without the render record of the current application file, with a stale clean-items file, with a cache before Stage B started, with a stop not cleared by `--continue`, or with a cell out of order.

## 4. The caches

`work/stage3/b3/cache-s3/` does not exist; `s3-run-v0.json` does not exist; no judge request and no OpenRouter request was sent by this session at any point. The application file `s3-applications-v0.json` (02edac2a) is the one draw and is never-open for the coordinator and the reviewer.

## 5. What would trip a fresh session

- The shell's cwd changes with any `cd` in a compound command and persists; use absolute paths or start every command with `cd /Users/aravind/KruxAI/tais-project-selection/work/checks &&`. In zsh, a bare `===` is parsed as a glob and fails: quote such echoes.
- The fork checkout is shared with other sessions (the brief 13 writing session and the coordinator commit there); mirror by copying to `scripts/stage3/` and `results/stage3/b3/`, `git add` by path, commit, never push.
- The matrix, the readings script, the driver and the dry run read the pinned files by hash; `s3-clean-items-v0.json` is pinned at 21e7ede2 by the uncommitted driver and readings script, and the record generator rewrites it with the same bytes.
- The readings test module's fixtures take about 9 minutes because each fixture runs the whole pipeline with 2,000-replicate bootstraps; `S3_FIXTURE_PROCS` sets the pool.
- The fixture generator is synthetic: a fixture's labels depend on its seed and knobs (six were tuned to reach their ids, as the dry-run report records); the `floor_both` and `floor_carrier` fixtures also carry forbidden families.
- `stage3_b3_power_v3.form_a` returns `fit_ok` on a rank-deficient design and `irls` ridges through one: the readings script checks rank itself; the simulator's fitters are used as numerical primitives only.
- Opus 4.8's thinking tokens are inside `output_tokens`, so the pre-signal's carrier gap is the B4-R basis, not thinking tokens (the coordinator's dated note 2).
- Never save a B3 number to memory (A6.19.1); the session's own memory note carries state only.

This session's ledger (rulings in order) is in its scratchpad, not in the project; every ruling that mattered is in `s3-stage-a-rulings.md` and the record.
