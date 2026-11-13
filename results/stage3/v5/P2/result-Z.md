# Block Z (dose): stopped by a harness abort; not analysed (blue harness session, Opus 5.5, 2026-11-14)

**Z stopped after 50 of 576 runs on a Bedrock `ValidationException` on GPT-6 Sol. Per the gate's stop rule, nothing is analysed and nothing is resumed; this note records what happened. It waits for the coordinator.**

Pre-registration `P2/preregistration-v1.md` (hash of record 19d4a7d5a3e839397f4416c6d2c5bc8ab6687f5ed66a728a6cbfff1f5bec39af), section 6 amendment (D31).

## What ran
- **Before launch:**
  - All five module hashes matched `pre-gate-v2.md`.
  - A dry run of both dose lines: 576 planned runs, 96 of 96 workspaces loaded, 12 of 12 predicates resolved, expected hashes matched (manifest 5e4a1dbf, predicates 4737b1ca, documents tree 543ab3ec).
  - Credits: key 1 limit remaining 138.8006, usage_daily 11.1994; key 2 limit remaining 271.2788, balance 81.2788.
- **Launch line:** `pre-gate-v2.md`'s dose line, with absolute paths, `--cap-usd 10.7` (v1 section 6) and `--out-dir` set to `P2/`.
  - Started 20:05:00 UTC.
  - Stopped 20:07:50 UTC with `stop: aborted` after 40 completed runs, $0.385.
- **My error:** I had chained the one retry pass to run after the launch line regardless of its outcome. It ran at once (20:07:50 to 20:08:42 UTC). A resume re-asks `aborted` and not-run runs, so it completed **10 more runs**, then aborted the same way ($0.071). The gate says not to resume after a stop. The retry pass should have been guarded on a clean finish. It was not, and that is my mistake.

## Counts (outcome codes and error-log codes only)
- **Outcomes:** 576 planned run ids. Latest records: 50 with a verdict (25 Kimi, 25 Sol), 1 `aborted`, 525 `not_run_stopped`. The file holds 1,112 lines because each pass wrote not-run records.
- **Finished runs by arm:** planted 6, clean 6, subset_1 8, subset_2 to subset_6 6 each.
- **Spend:** $0.456 (Sol $0.382 Bedrock upper bound; Kimi $0.074 on key 1; no key rotation). Credits after: key 1 limit remaining 138.7262, usage_daily 11.2738; key 2 unchanged.
- **Cause:** the red-side error log holds 2 lines, both `aborted` / `HarnessAborted`, both on Sol, in cells subset_2 and subset_5, both an AWS `ValidationException` on the Converse call.
  - The stored detail is cut at 200 characters, before AWS names the offending field, so the specific cause is not known on the blue side.
  - No document in any dose workspace is empty: a blank tool result from an empty file is ruled out.
  - Sol had no such error in the 672 core runs or the 96 verification runs.

## What would be needed to continue (the coordinator's call)
1. **Diagnose:** the full AWS message (the runner keeps only 200 characters), or a red-side look at Sol's transcripts of those two runs, to name the field Bedrock rejected. Likely candidates: a blank text block echoed back in Sol's own assistant content, or a tool-use input that is not an object.
2. **Fix test-first:**
   - The Converse adapter would drop or repair what Bedrock rejects.
   - The runner would refuse `--retry-unresolved` on a block whose latest records show a stop.
   - The fix would come with a fresh dry run.
3. **Then resume Z** under a dated note written without reading an outcome. The 50 finished runs would stand, and the 526 runs without a verdict would run.

Until then Z has no result, and the same adapter would face the same risk on Sol in D, W and H.
