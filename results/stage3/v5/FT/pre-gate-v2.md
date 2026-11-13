# FT pre-gate v2: hashes and launch lines for pre-registration v1.3 (blue harness session, Opus 5.5, 2026-11-13; $0)

Supersedes `pre-gate-v1.md` for hashes and launch lines only; v1's results stand. Governing file: `preregistration-v1.3.md` (sha256 ac73fd1fc24f7aa0d0080b023a0e684b39b7164c63d5fdb4a1828b719f03c575).

**Code commit:** `43bbcad` on the fork's `stage3` (not pushed). It holds the runner and join below. The harness, power and smoke modules are unchanged since `346559b`. This file is committed separately on top of it.

## The two v1.3 changes ($0, test-first)

- **Retry pass (gate 2).** `--resume --retry-unresolved` re-asks, once, every run whose latest code is an infrastructure error (`infra_error`, `throttle_error`). Selection reads only the error code and the retry mark, never a verdict. Provider refusals are never re-asked, and a run is re-asked at most once. Re-asked records carry `retry_pass: true`, and each pass writes a start line and an end line (candidates, re-asked) to `outcomes-<block>-v0.passes.jsonl`. *(tests: `test_retry_unresolved_reasks_infra_errors_once_and_never_refusals`, `test_a_run_is_reasked_at_most_once`, `test_refusals_are_not_reasked`, `test_retry_needs_resume`)*
- **When the followers differ.** The join reports `follower_difference`: the Kimi-minus-Sol RM uptake difference, paired by payload (one resample serves both followers), with its 95 percent percentile bootstrap interval, in each completion. `followers_differ_supported` is true only when the interval excludes zero, on the same side, in both completions. *(tests: `test_follower_difference_paired_by_payload`, `test_identical_followers_are_not_said_to_differ`, `test_follower_difference_must_exclude_zero_in_both_completions`)*

## Modules and tests (sha256; by module name under `work/mole-fork/.venv/bin/python -m pytest -q`, exit codes kept)

| file | sha256 | test module | sha256 | result |
|---|---|---|---|---|
| `stage3_ft_harness.py` | 16bd3a3985b3c97ca900696cbf358dd45e2a380f78ace805bfcef11dee067a6a | `test_stage3_ft_harness.py` | ea4f6a0c13a8218d0032b8fa3cf713d60a747e733475444aaf0670ae2430037b | 45 passed |
| `stage3_ft_run.py` | e9b11a2053c3c76aba2d74cc5d3d75cdd68e54901823937450176279a34e7e80 | `test_stage3_ft_run.py` | 6160793496e0e5630eb07610b708a4643076311e86cf456533826ccbf8c4e42b | 41 passed |
| `stage3_ft_join.py` | b8a158eb74ac4b179d949a8c478b4f1342a1c60f331b46cc75cd9982ced79e0d | `test_stage3_ft_join.py` | f98bf8294a701c8e177f6d922dda9b057130b1a9739b39245a90d6e34ecb5ee2 | 38 passed |
| `stage3_ft_power.py` | 48993834a9ea155577762589193df0dba9a66af290fe27899aa85a0a42ef04f9 | `test_stage3_ft_power.py` | 1b89c9df25f3ff52ce05726c54f34e7fc8c4214aa9d04090f92248670fec10cb | 26 passed |
| `stage3_ft_smoke.py` | e06e5a7bdb31bb2ec4231cd6c4b4b852afd5f12ca9375fb3afd741ee7536d5df | `test_stage3_ft_smoke.py` | 992abbd074c8cfa19ded8432900da42090fb27c08230ec4c9c60c8af768bde82 | 5 passed |

All 155 tests pass. Canonical copies are in `work/checks/`; the fork copies in `scripts/stage3/` are byte-identical.

## Fresh dry run (no model call, nothing written; every expected hash checked and matching)

| block | runs | workspaces | predicates | manifest / predicates / documents tree |
|---|---|---|---|---|
| core | **672** | 112 of 112 load (six `/shared/` documents, history present) | 56 of 56 resolve | 7f44e41c / 4737b1ca / 543ab3ec |
| verification | **96** | 16 of 16, 16 benign revisions placed | 16 of 16 | 7f44e41c / 4737b1ca / 543ab3ec |
| dose | **576** | 96 of 96 | 12 of 12 | 5e4a1dbf / 4737b1ca / 543ab3ec |

No outcomes file exists for any block. The retry-pass form of the core line also parses and dry-runs (672).

## Launch lines (from the project root)

Each block runs its launch line, then its retry-pass line once, before any analysis. The launch line refuses an existing outcomes file. The retry-pass line needs that file and re-asks only infrastructure failures, once.

**Core** (cap $9.57):

```bash
cd work/checks && ( set -a; source ../mole-fork/.env; set +a; ../mole-fork/.venv/bin/python -I stage3_ft_run.py --manifest ../stage3/red/ft/cells-manifest.json --block core --arms planted,clean --followers kimi,sol --repeats 3 --cap-usd 9.57 --concurrency 4 --expect-manifest-sha256 7f44e41c9e26eac479c1349b8c950701a32ed7e67de130c589ddab540c177e9d --expect-predicates-sha256 4737b1caa0823fe0fab1cb3f5446c94db6cdbf88782f847668c65adcc77afb38 --expect-docs-tree-sha256 543ab3ecc6480107f0f59ef4a39470f54684e92b1e161143cc565f0a5b495dc5 )
```

```bash
cd work/checks && ( set -a; source ../mole-fork/.env; set +a; ../mole-fork/.venv/bin/python -I stage3_ft_run.py --resume --retry-unresolved --manifest ../stage3/red/ft/cells-manifest.json --block core --arms planted,clean --followers kimi,sol --repeats 3 --cap-usd 9.57 --concurrency 4 --expect-manifest-sha256 7f44e41c9e26eac479c1349b8c950701a32ed7e67de130c589ddab540c177e9d --expect-predicates-sha256 4737b1caa0823fe0fab1cb3f5446c94db6cdbf88782f847668c65adcc77afb38 --expect-docs-tree-sha256 543ab3ecc6480107f0f59ef4a39470f54684e92b1e161143cc565f0a5b495dc5 )
```

**Verification** (cap $1.37):

```bash
cd work/checks && ( set -a; source ../mole-fork/.env; set +a; ../mole-fork/.venv/bin/python -I stage3_ft_run.py --manifest ../stage3/red/ft/cells-manifest.json --block verification --arms benign --followers kimi,sol --repeats 3 --cap-usd 1.37 --concurrency 4 --expect-manifest-sha256 7f44e41c9e26eac479c1349b8c950701a32ed7e67de130c589ddab540c177e9d --expect-predicates-sha256 4737b1caa0823fe0fab1cb3f5446c94db6cdbf88782f847668c65adcc77afb38 --expect-docs-tree-sha256 543ab3ecc6480107f0f59ef4a39470f54684e92b1e161143cc565f0a5b495dc5 )
```

```bash
cd work/checks && ( set -a; source ../mole-fork/.env; set +a; ../mole-fork/.venv/bin/python -I stage3_ft_run.py --resume --retry-unresolved --manifest ../stage3/red/ft/cells-manifest.json --block verification --arms benign --followers kimi,sol --repeats 3 --cap-usd 1.37 --concurrency 4 --expect-manifest-sha256 7f44e41c9e26eac479c1349b8c950701a32ed7e67de130c589ddab540c177e9d --expect-predicates-sha256 4737b1caa0823fe0fab1cb3f5446c94db6cdbf88782f847668c65adcc77afb38 --expect-docs-tree-sha256 543ab3ecc6480107f0f59ef4a39470f54684e92b1e161143cc565f0a5b495dc5 )
```

**Dose** (cap $8.20; launched only when the core has landed at or under 1.2 times its estimate):

```bash
cd work/checks && ( set -a; source ../mole-fork/.env; set +a; ../mole-fork/.venv/bin/python -I stage3_ft_run.py --manifest ../stage3/red/ft/cells-manifest-dose.json --block dose --arms planted,clean,subset_1,subset_2,subset_3,subset_4,subset_5,subset_6 --followers kimi,sol --repeats 3 --cap-usd 8.20 --concurrency 4 --expect-manifest-sha256 5e4a1dbf4fd7e926d42371da4d4a70166d65a95aaa88da2c97591a5593349797 --expect-predicates-sha256 4737b1caa0823fe0fab1cb3f5446c94db6cdbf88782f847668c65adcc77afb38 --expect-docs-tree-sha256 543ab3ecc6480107f0f59ef4a39470f54684e92b1e161143cc565f0a5b495dc5 )
```

```bash
cd work/checks && ( set -a; source ../mole-fork/.env; set +a; ../mole-fork/.venv/bin/python -I stage3_ft_run.py --resume --retry-unresolved --manifest ../stage3/red/ft/cells-manifest-dose.json --block dose --arms planted,clean,subset_1,subset_2,subset_3,subset_4,subset_5,subset_6 --followers kimi,sol --repeats 3 --cap-usd 8.20 --concurrency 4 --expect-manifest-sha256 5e4a1dbf4fd7e926d42371da4d4a70166d65a95aaa88da2c97591a5593349797 --expect-predicates-sha256 4737b1caa0823fe0fab1cb3f5446c94db6cdbf88782f847668c65adcc77afb38 --expect-docs-tree-sha256 543ab3ecc6480107f0f59ef4a39470f54684e92b1e161143cc565f0a5b495dc5 )
```

**The join**, after the retry passes (counts, rates and readings only; add `--audit-table <path>` once red's audit table exists):

```bash
cd work/checks && ../mole-fork/.venv/bin/python -I stage3_ft_join.py --manifest ../stage3/red/ft/cells-manifest.json --core ../stage3/v5/FT/outcomes-core-v0.jsonl --verification ../stage3/v5/FT/outcomes-verification-v0.jsonl --dose ../stage3/v5/FT/outcomes-dose-v0.jsonl --dose-manifest ../stage3/red/ft/cells-manifest-dose.json --out ../stage3/v5/FT/analysis-v0.json
```

The cap is the same in a block's launch and retry-pass lines: the ledger carries the block's whole spend, so a retry pass draws on what the launch left of the cap.
