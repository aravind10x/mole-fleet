# Writer round 1, one-document arm: record (brief 30 Part 3; the Part 3 session, Sonnet 5.5, Claude Code desktop app; 2026-11-07)

Counts, aggregates and hashes only. No item text, statement, rubric, answer or key appears here or in any file named here outside the barred directory `part3/writers/` (never opened by the coordinator or the review session) and the caches. No B3 result, score or item was opened; the S3 caches and `s3-applications-v0.json` were not touched. Spend: about $5.6 outside GPT-6.1-sol's own tokens (section 7).

## 1. Outcome in one table (writer round 1 at the floor of 24 per arm per writer)

| writer | outcome | written | valid | quiet (gate i) | gate (ii) pass | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Opus 5.5 | **stopped** (the harness's safety-stop counter 1; its final message did not parse) | 0 | 0 | n/a | n/a | 0 | 0 | 0 | 0 | 0 | 0 |
| GPT-6.1-sol | attempted | 24 | 20 | 13 | 3 | 2 | 0 | 1 | 9 | 7 | 1 |

**Yields per valid item written (rules file rule 3):** p_c = 2/20 = 0.100, p_i = 0/20 = 0.000. The four invalid items all failed the token check (decision 4: the converter extracts each statement's token under the carrier-matching rule; it extracted 60 tokens and 4 statements failed, each in a different item, so 4 items were lost: a yield cost of 4 of 24 = 17 percent at the floor, against 0 failures in 22 statements on Part 1's synthetic set). **The raising count for writer round 2** by rule 3 at the cap of 96: a pooled yield of 0 on the illegible arm gives the cap, so **96 per writer** whether one writer or two are asked (the coordinator names W; section 8).

## 2. What each writer saw and how each ran

Both folders were assembled by `stage3_elicitation_harness.py assemble` (2e4b4e96 after this session's two fixes, section 6): `packet.md` (the sent body, `cb528f5d`), `round.md` (`Round: 1`, `Arm: one-document`, `Items to write per arm: 24`; `aeb7f40b`, identical bytes for both writers), the one-document day-0 state (`d0f3fbae`); nothing else. The preface (`15a98bde`, parsed from the launch notes) is identical for both and is the only text typed. Effort high for both. Start-state records (existence and sha256 only) are `part3/writers/<writer>-r1/start-state.json`: no instruction file in either folder or any parent to `/`; `~/.claude/CLAUDE.md` and `~/AGENTS.md` absent; `~/.codex/AGENTS.md` present and empty (0 bytes; not loaded under the clean `CODEX_HOME`); no per-folder memory index for either folder.

- **Opus 5.5:** `claude -p` (Claude Code 2.1.316, a child of this desktop session) in the round folder with `--tools Read --allowedTools Read --setting-sources project --disable-slash-commands --strict-mcp-config --no-session-persistence`, the corrected deny-list `claude-settings.json` (section 6) and `--max-budget-usd 12`; the init event listed one tool (Read), no MCP server, no skill, no slash command, only the three built-in plugins. Five turns, $0.16, 47.8 s; it read `packet.md`, `round.md` and the document file and nothing else (audit PASS, 3 paths, 0 outside). Its final message (881 characters, hash `9f2a1e6d2bad`, kept unread) did not parse and the run's safety-stop counter read 1. **Reported as a bound**, as the launch notes say: not retried, not reworded, no fallback launched. The coordinator records the writer's loss before Muse Wonder takes a slot.
- **GPT-6.1-sol:** `codex exec -m gpt-6.1-sol -s read-only -C <folder> --skip-git-repo-check -c model_reasoning_effort=high --json -o <final message>`, stdin closed, `CODEX_HOME` a clean directory holding only the login file (made by the harness's `--prepare-config`; to be deleted). codex-cli 0.166.0; the one-word probe answered. 6 min; input 151,581 tokens (124,672 cached), output 16,856 (7,127 reasoning). Four commands, all `cat` of the three folder files; audit PASS (18 path tokens, 17 of them not files, 0 outside, 0 never-open).

## 3. Funnel and classes (GPT-6.1-sol; counts)

By mechanism (valid items):

| mechanism | valid | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |
|---|---|---|---|---|---|---|---|
| composed-permission | 6 | 2 | 0 | 1 | 3 | 0 | 0 |
| conjunction | 5 | 0 | 0 | 0 | 4 | 0 | 1 |
| default-exception-schedule | 3 | 0 | 0 | 0 | 0 | 3 | 0 |
| indirection | 6 | 0 | 0 | 0 | 2 | 4 | 0 |

Gate (i) (two certification rater sessions, mean per statement at or under 60): 13 of 20 pass. Composition (two-session mean) over the 20 valid items: minimum 47.5, median 59.0, maximum 75.5. Readers for Sol-written items: Kimi K3 pinned (Wafer at MXFP4; 104 of 104 certification reads on the pin, 80 of 80 development reads) and Sonnet 5.5, gate (ii) by the every-sample rule; one Sonnet 5.5 read was refused (one item not evaluable). The yield curve so far is one row: round 1, 24 written, 20 valid, 13 quiet, 2 certified, 0 illegible. Both arms are far below the floor of 12 + 12; the outcome sentence is chosen at the end of the last writer round and is not chosen now.

## 4. Matching (round 2's rule, note 7 item 4)

Matched strata (writer x document x 10-point composition band): n_c = 0, n_i = 0 (certified in the arm 2, illegible 0); matched effective n = 0.0. The first act's dry run (`part3/matching-dry-run-v0.md`, bd1742d3) forecast this shape: on invented strata at the 10-point band the matched n_eff at 58 + 21 is about 12 against 30.8 unmatched; the stop statistic "n_eff of 26 on the matched strata" is not reached at expected counts in any of the three strata models run. Flagged to the coordinator in the STATUS line; the width and the statistic are the coordinator's.

## 5. Proxy agreement, development against certification (protocol section 1; counts)

- **Rater** (the development session's 60 statement ratings against the two certification sessions' means): Spearman 0.937; within-target (at or under 60) agreement 0.90.
- **Readers** (items certification read, 13): Kimi K3 pinned: whole-credited agreement 0.92 (n 13), part-credited 0.77 (n 13); Sonnet 5.5: whole 0.92 (n 13), part 0.75 (n 12). No gap named: the development and certification instruments agree closely on this round (small n).

## 6. Defects found in Part 1's harness at its first real use, and the launch-side files

1. **The audit's allow-list was computed and never applied** (`stage3_elicitation_harness.py audit`): a trace that opened exactly the round folder's files failed whenever the folder was not under a state tree; the Part 1 test hid it because pytest's temporary folder sits under `/private/var/folders`, which the audit treats as state. Test added (round folder under the home directory), one line fixed. The first Opus audit record, FAIL for this reason, is kept as `audit-00-defect-allowlist-unapplied.json`.
2. **The codex-trace adapter raised `UnboundLocalError`** on its nested walk (never tested; Part 1's tests used the paths format only) **and counted `/bin/zsh`**, the first token of every codex command, as an opened file. Tests added with a codex-shaped trace; the walk fixed; the shell interpreters the CLIs invoke themselves are not counted as opened files.
3. **The deny-list the harness writes is not Claude Code's schema** (a flat `{"deny": [...]}` with single-slash patterns, which Claude Code reads as project-relative). It stays beside the manifest as written (defence in depth that does not work). The launch used `claude-settings.json` from `stage3_elicitation_part3_launch.py` (b587eb29): `permissions.deny` with `Read(//Users/...)` patterns for the project tree, the `.claude`, `.codex`, `.cursor` and `.config` trees, `/tmp`, `/private/var/folders` and the other writer's tree. A probe on a harmless project file showed the read refused and the folder file read.
4. **Not fixed, noted:** `session_slug` in the harness strips the leading slash, so the audit's allowance for the session's own state directory would not match Claude Code's mapped folder name (which begins with a dash). No run opened that directory (one tool, no session persistence), so nothing here depends on it.

The harness is now 2e4b4e96 (was 6eca0f14); its test module has 13 tests (was 11). Every other Part 1 and Part 2 file is at its recorded hash.

## 7. Spend and the key ledger

| item | $ |
|---|---|
| Opus 5.5 writer (stopped) | 0.16 |
| GPT-6.1-sol writer | not billed in dollars (ChatGPT login; tokens in section 2) |
| development reads (20 items, one sample; Kimi 0.58, Sonnet 5.5 0.21, scorer 0.51), cap 4.63 | 1.29 |
| certification reads (13 items, two samples; Kimi 0.76, Sonnet 5.5 0.27, scorer 0.65), cap 6.02 | 1.68 |
| rater sessions (Sonnet 5; 2 development, 4 certification) | 2.21 |
| probes (model-id and login probes of Claude Code, about; the codex probe is tokens) | 0.23 |
| **total** | **about 5.6** |

The caps follow note 4 item 3 scaled to the items read: development 20 of 192 (twice the point price $4.35, the upper bound plus five percent $4.63), certification 13 of 192 ($5.67 and $6.02). **Realised Kimi cost per read: $0.0072 (development) and $0.0073 (certification)**, against the dry run's $0.0166 and E2's $0.0128 on its items (shorter outputs on these items, 80 and 104 reads).

**Key ledger (OpenRouter key 2; Kimi K3 through the pin, the only OpenRouter use this round):** before development reads (2026-11-07T11:54:27Z): key limit remaining $279.79, **account balance $89.79** (the binding figure by lesson L7); after certification reads (12:13:03Z): $278.45 and **$88.45**; key usage rose $1.3373, equal to the Kimi records' $0.5776 + $0.7596 to four decimals, so no use outside this record. Bedrock (Sol, Sonnet 5.5, the scorer) is not on this key. **Planning figure for later rounds:** a full round at the cap (192 one-document items) reads about $29 in Kimi at E2's realised cost ($0.0128; 2,304 reads), so the account balance covers about three such rounds at that cost, or about five at this round's $0.0072, before the cross-document arm and any extra round; whether to top the account up is Aravind's call.

## 8. Items for the coordinator, with what I did and did not do

1. **Opus 5.5 stopped on writer round 1.** Record the loss, or name a retry on identical bytes, or release Muse Wonder (harness to be named by Aravind). I did none of these. Writer round 2 for GPT-6.1-sol is not launched: the review session reads this record first (brief 30 section 4 item 7). The raising rule gives 96 per writer.
2. **The matching statistic** (section 4 and the dry run): n_eff of 26 on matched strata is far from reachable at 10-point bands within writer x document; the course's probabilities (0.93 and 0.70) were for the all-matched figure. Decision on the band width or the statistic is the coordinator's by dated note before writer round 1's certification is read (this round's certification is done; no score was drawn from it).
3. **Token extraction cost 4 of 24 items** (17 percent of the floor round): decision 4 changes the packet only if extraction is impossible for a statement class; it was possible here. Reported for the coordinator's reading of the yield.
4. **Rater sessions** were run as brief 17 R0.3 ran B3's (one fresh session per scale and pass, each in its own folder under `/Users/aravind/elicitation-raters/` holding the rubric, the day-0 text and that scale's file, nothing else; model `claude-sonnet-5`, effort high, tools Read and Write; prompt of 07s with relative paths and one Write call; every session audited, 6 of 6 PASS, 6 of 6 ratings files valid). The protocol says each session rates both scales; this keeps a statement's rating independent of its triple, at twice the session count. A pass here is its two scale sessions.
5. **Not done in this round and why:** the check of certified and illegible items against the states round 2 uses (the round-2 brief names them; against the day-0 state no valid item fails, 0 of 20); the anchor draw (after the last certification, protocol section 9); the pair pilot and the cross-document arm (the pair extension of the reader and the pair rubric file are prerequisites not yet built; the one-document arm has priority).
6. **Writer round 1 is below the floor on both arms** (2 certified, 0 illegible); the next two rounds at the cap decide the curve; nothing in this round was read as a reason to stop.

## 9. Files (hashes are the first 8 hex of sha256)

Code (all by module, tests green): matching 5697de9d, classes 343be36f, reads bdc00a74, raters 70e04d35, feedback 5d8d67a3, round 1a516047, launch b587eb29, harness 2e4b4e96. Notes: protocol v0.2 section 80a814bf, rules v0.2 section 74d6185c. Under `part3/`: `matching-dry-run-v0.{json,md}` (and the two sensitivity runs), `limits/`, `writers/` (barred), `round-1/gpt61sol/converted/` (the converter's outputs, ids opaque), `round-1/gpt61sol/round-record.json` (cbae8230), `round-1/gpt61sol/feedback/previous/` (results e372bd7b), `reads/`, `raters/`. Writer audit records: Opus fddbf648, Sol 4d5534b0.

## 10. Barrier audit (brief 30 section 5)

**Opened, whole or in part:** brief 30 (with its dated notes), the part of brief 29 holding its dated notes, plan.md section 8 (the pre-registered round-2 text, not a result), the elicitation files (protocol, rules, converter-v0, gate-reachability-v1, the reconciled proposal, the cold read of brief 30, INDEX), the code of the harness, converter, reader, E2's runner and the pinned trace audit, the roadmap's lines on this brief, the writer packet's section 8 only (the feedback layout), the T1 rater's two pass prompts (instructions) and the headings of the rubric file (`grep` of its `## ` lines; no rubric text). **Incidentally seen:** two `grep` and `tail` reads of STATUS.md, cut at 400 to 4,200 characters, showed coordinator-written lines that quote B3 round 1's gate figures and Part 2's counts; none was used, quoted or written into any file or memory by this session. **Not opened:** any b3-results file, any S3 cache, `s3-applications-v0.json`, any item text, the rubric's text, the writers' answers, final messages and traces (GPT-6.1-sol's answer reached only the converter's `extract` and `convert` by script; Opus 5.5's final message is held unread by hash), the converted payloads and stripped files other than by script and by structure on the synthetic set, the rater sessions' reasons (validated by script), the caches. `stage3_b3_rater_prep.py` is imported by one test for its word-scan regex only. Keys and `.env` values were never printed; `.env` was sourced in the shell for the Kimi and Bedrock runs. No item line, statement or rubric text is in any message, STATUS line, memory or global instruction file written by this session.
