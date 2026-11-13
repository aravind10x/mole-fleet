# Follower test, offline tier: gate (coordinator, 2026-11-13)

The core may run. This file is the only authority for it.

## What governs
- Pre-registration: `preregistration-v1.3.md`, sha256 `ac73fd1fc24f7aa0d0080b023a0e684b39b7164c63d5fdb4a1828b719f03c575`.
- Launch rehearsal, module hashes and launch lines: `pre-gate-v2.md`, sha256 `b5d0c57719559f5ef07d0d4e753c25836d06153f2b21f3bb183f009adf87b4f9`.
- Both are in the frozen manifest (`work/stage3/b0/frozen-tables.json`, e7bb1562, 137 files) and pushed on the fork at `b267852`, before any run on a planted document.
- Reviews: two rounds, every point decided (`review/dispositions-round1.md`, `review/dispositions-round2.md`); decisions log D11 to D13.
- Spend authority: Aravind's decision 5 (13 Nov) and the standing approval for an ungated line inside its band after its read. The band is $50 to $400; this launch is about $13.

## What runs, in this order
1. **Core:** 672 runs, estimate $6.38, cap $9.57. Then its retry pass, once.
2. **Verification control:** 96 runs, estimate $0.91, cap $1.37. Then its retry pass, once.
3. **Dose:** 576 runs, estimate $5.47, cap $8.20, **only if the core landed at or under $7.66** (1.2 times its estimate). Then its retry pass, once.

Use the launch lines of `pre-gate-v2.md` exactly, with their expected-hash arguments. Total estimate $12.76, total cap $19.14. Offline-tier spend before this launch: $0.68.

## Rules
- Record `credits_both.sh` before the core and after the last block. Key 1 for Kimi; key 2 only by the client's rotation on a 402.
- A block that passes its cap stops. More than 10 provider refusals in a block stop it. A 402 on the last key stops it. On any stop: do not resume, do not analyse; write what happened and wait.
- No retry pass is run twice. No outcome is read to decide anything about a run.
- The red side is frozen: nothing under `work/stage3/red/ft/` changes except the runner's own transcripts and logs.
- The blue executor opens no transcript, planted document or predicate source.

## After the blocks land
1. Run the join line of `pre-gate-v2.md` and write `work/stage3/v5/FT/ft-results-v0.md`: the gates' verdicts, the reading on the mixture as the code returns it, the two per-follower readings and `followers_differ_supported`, uptake by group and follower with intervals, S, S_same and S_other, the clean arm's counts, the copying baseline, the checking table, the dose table, unresolved and refused counts, realised cost per block against its estimate, and the hashes of the three outcomes files and `analysis-v0.json`. Counts, rates and readings only.
2. The reading is provisional until the red-side audit has been joined (pre-registration section 6). Say so in the first line.
3. Append one ledger line to `BOARD.md`. Commit your own paths on the fork, do not push. Tell the coordinator.
