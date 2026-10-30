# Rater record, B3 (brief 17)

The blue session started this record at R0 on 2026-10-30 and completed it at J4 the same evening. Everything below was established by script from the four session transcripts, the pass files and the key, and gives counts, ids and hashes only. No transcript, reason or item text was read by eye; the exceptions are disclosed in the last section.

## R0 deviations from brief 17

The review session approved all four on 2026-10-30 ("approved as built, no rebuild"). Hashes are in the STATUS line "BRIEF 17 R0 DONE" and in `hashes.txt`.

1. **Each rater folder holds three files, not two.** The brief said `rubric.md` plus the stripped file.
   - The rubric copied in is `rubric-passes-2.md` (8354e3bf…). It is sections 1, 2 and 2b of `rubric.md` verbatim, the file 07s's passes read. `rubric.md` itself was not used because its section 4 states the study's prediction and is marked "not shown to the rating passes".
   - `doc-states-day0.md` (d0f3fbae…) is added. Section 1 and 2b score each edit against the day-0 text, which is how 07s's passes worked.
   - The preface line names three files.
   - J4's trace-audit allow-list names all three files, plus the session's own output in its folder.
2. **The outputs are `.jsonl`, not `.json`.** The files are `ratings-b3-<scale>-p<n>.jsonl`, in 07s's one-object-per-line format.
3. **A scale's two pastes also differ in the folder name**, on the preface line. The four-folder design needs this. Apart from that, they differ only in the output name.
4. **The paste files and `stage3_b3_rater_prep.py` (with its test) are also mirrored to the fork**, next to `hashes.txt`. The fork commit is `a341a56`.

## The four rater sessions

Aravind opened all four on 2026-10-30, each as a fresh session in its own folder. They ran in parallel between 13:42 and 13:59 UTC.

| Session | Folder | Transcript | Model (every assistant message) | Harness | Effort (every turn) | UTC | Tool calls | Stop or refusal | Fallback |
|---|---|---|---|---|---|---|---|---|---|
| statements p1 | /Users/aravind/b3-rater-statements-p1 | bed6399a… (d08d1da9…) | claude-fable-5-1, 67 messages | Claude desktop app, Code tab (entrypoint claude-desktop), Claude Code 2.1.309, permission mode auto | high | 13:42:34 to 13:53:15 | Bash 62, update_plan 6, wrap_up 1 | none: 66 tool_use, 1 end_turn, 0 API errors | not used |
| statements p2 | /Users/aravind/b3-rater-statements-p2 | 8818a68c… (5b13661c…) | claude-fable-5-1, 66 messages | same | high | 13:43:39 to 13:53:05 | Bash 38, update_plan 6, wrap_up 2 | none: 65 tool_use, 1 end_turn, 0 API errors | not used |
| triples p1 | /Users/aravind/b3-rater-triples-p1 | 645e6523… (b215ac48…) | claude-fable-5-1, 61 messages | same | high | 13:44:26 to 13:53:55 | Bash 56, update_plan 6, wrap_up 2 | none: 60 tool_use, 1 end_turn, 0 API errors | not used |
| triples p2 | /Users/aravind/b3-rater-triples-p2 | debe87f2… (04ee322f…) | claude-fable-5-1, 60 messages | same | high | 13:46:12 to 13:58:51 | Bash 56, update_plan 6, wrap_up 1 | none: 59 tool_use, 1 end_turn, 0 API errors | not used |

How the sessions ran:
- **Prompt.** Each session got one user message: its paste body (from line 3), byte-identical after stripping. The app wrapped it in `pasted_content` tags, and the two note lines were not pasted.
- **Other models.** `requestedModel` and `advisorModel` are `claude-fable-5-1` throughout, so no other model was involved.
- **Tools.** No sub-agent, Read, Glob, Grep, web or skill tool was used.
- **Context beyond the paste.** No memory or `CLAUDE.md` attachment was loaded, and each session's project memory directory is empty. The context held the app's standard environment, tool, MCP and skill listings, plus the SessionStart hook's "superpowers" preamble (the same block this blue session receives).

What each session reported at the end, with the blue session's check by script:
- **statements p1 and p2.** Each wrote 509 lines and its final check passed. Each repaired one identical-text pair under rubric rule 6: `9afc8b47…` and `b8ac0b8f…`, two honest single edits with the same document and text, one a replace and one an append. They score equal in both passes, by script. Both said their context held no project notes. These two replies overlapped item or reason text under the guard, so they were not displayed; the facts above were taken from them by pattern.
- **triples p1.** It wrote 357 lines, its final check passed, and it made no repair. Its one identical pair (`ef9886e8…` and `55fcb537…`) scored equal from the start. It reported only the standard tooling and the hook in its context.
- **triples p2.** It wrote 357 lines and its final check passed. It shortened two reasons that were over 25 words (`9432f6e5…` and `9d2837a0…`) without changing their scores. Its identical pair is equal. It reported the app's tooling, the memory-directory guidance and the "superpowers" preamble, and three helper scripts in its own scratchpad.

Check of the four pass files by script (07s's checks):
- Every input id appears exactly once, in file order.
- Every score is an integer from 0 to 100.
- No reason runs over 25 words.
- Identical groups score equal: 11 groups for statements and 1 for triples, with 0 unequal in any pass.

## Trace audits (J4)

Each audit ran `work/checks/stage3_b3_trace_audit.py` (2a409344…) with `--format claude-jsonl` against the session's folder. `--allow` named `rubric-passes-2.md`, `doc-states-day0.md`, the scale's stripped file and the session's output.

| Session | Strict verdict | Opened inside the folder | Own scratchpad | Withheld tokens | Reading |
|---|---|---|---|---|---|
| statements p1 | FAIL | 1 (the folder) | 0 | 8 | Every file opened is inside the folder. The 8 entries are path-shaped tokens in command text, not opens. |
| statements p2 | FAIL | 3 | 2 (add.py, show.py) | 5 | Same reading, plus helper scripts in its own app scratchpad. |
| triples p1 | FAIL | 5 | 3 (the scratchpad, show.py, write.py) | 3 | Same reading. Two of the tokens are the session's own path-building for `stripped-triples-b3.json` (a string `replace` and an `os.path` join), and both resolve to its own input. |
| triples p2 | FAIL | 3 | 3 (append.py, check.py, show.py) | 9 | Same reading. |

Notes on the audits:
- **Strict verdict.** The audit script reports FAIL because its allow-list cannot express two things: the session's own app scratchpad, and path-shaped fragments inside commands.
- **Folder.** Every `cd` in every session targets the session's own folder.
- **Escape patterns.** Pattern counts over all Bash commands found no `..`, `~`, `$HOME`, KruxAI, `.claude` or STATUS path. The "key" and "brief" hits were words inside reasons ("key-rotation", "briefly").
- **Helper scripts.** The seven helper scripts open only their own session's stripped file and output. They take scores from the command line and contain no `random` and no score literal, so none produces a score.
- **Redaction.** The committed audit JSONs withhold the path-shaped tokens, giving a 12-character hash for each. The unredacted outputs stay in the main checkout as `trace-audit-rater-<session>-unredacted.json`, and their hashes are in `hashes.txt`.

## Blue-session exposure (disclosed)

1. **Rater reasons.** While classifying the audits, a guarded print showed three rater reason lines from triples p1's commands. They are one-line paraphrases written by the rater and passed the 20-character verbatim-overlap guard against the item texts. No further command lines were printed; later prints were limited to counts, ids, paths, and two closing replies that passed a guard that also covered the reasons.
2. **Aravind's earlier answer.** While reading the format of `human-anchor-2-sheet.md`, one line of Aravind's own earlier anchor answer (a "Why" line from batch 2) was printed.
3. **No item text.** No candidate, control or reference statement text was printed.
