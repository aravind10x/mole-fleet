# Rater record, brief 07s part R with amendment B2 (second rater session)

**Session:** `local_a2747ac3-da65-4bf6-8f65-ff71add49e74`, started from `local_ccf09658-1bff-4a7b-bb7e-ca8d8a3a5570`, 2026-10-28.
**Model and effort (from the app's session metadata):** `claude-opus-5-5`, effort `xhigh`.
**Rating passes:** four fresh-context sub-agents, `model: "fable"`, `effort: "high"` (to match 07k's passes on claude-fable-5-1 at high effort). This session rates nothing itself.
**Cost:** $0 (no API calls; sub-agents only).

## Files read

1. `README.md` (whole).
2. `PLAN.md`: section headings (grep), then section 1 only (lines 1 to 26, which include the status preamble above section 1).
3. `work/stage3-research-design-2026-10-19.md`: section headings (grep), then section 3 only (lines 32 to 45).
4. `work/stage3/t1k-rater/rubric.md` (sha256 `81fc6e0e5c66decf674b0b069c47b3c42dc56372f73a6f2223866a15fbc07bc8`, checked, matches) and `work/stage3/t1k-rater/rubric-passes.md` (sha256 `985fe0b2545e83a7c26b0e6851f202de5142bf0ee7041efad27bc89ac1341405`, checked, matches).
5. `work/stage3/t1k-rater/doc-states-day0.md` (whole; sha256 `d0f3fbae0e1b67125196263395edcd658c000458dc54b8460e9a691e4edf31e0`).
6. `briefs/07k-stage3-blind-rater-2026-10-26.md`: section headings (grep), then part R only (line 17 to the end).
7. `STATUS.md`: `tail -n 1` only, to copy the line format.
8. Directory listings (file names only) of `work/stage3/t1k-rater/` and `work/mole-fork/results/stage3/t1k-rater/`; `git log --oneline -3` and `git status` on the fork.
9. The app's session metadata (for model and effort).
10. The shared notes folder for this session group: listed, empty.

Not opened: any `key*.json`; `ratings.json`, `ratings-summary.md`, `rater-record.md`, `passes/` (the 07k files), `human-anchor*`, `stripped-payloads.json`, `stripped-statements.json`; anything under `work/stage3/rater-07s/`, `t1/`, `t1v2/`, `t1v3/`, `t1-replant/`, `q1q2-synthetic/`, `b0/`; the prep report; any other brief; decision memos, roadmaps, proposals, the sealed file, persona files, memory files.

**Disclosure.** The last line of `STATUS.md` (the blue session's part 0 line, read for its format as permitted) states the pool's make-up: the single-edit file mixes 116 edits from the honest null with 60 of 07k's 348 statements, and the triple file mixes 104 distinct planted triples with 120 random and 22 same-author honest triples; it also states that the two kinds are partly identifiable by form (account handle, multi-line text). It does not say which id is which. This session rates nothing, and no pass prompt mentions origin or form; the passes see only their prompt, the rubric file, the day-0 states and their input file.

The two stripped files were hashed (no content printed) at the start of the session, with the rubric hashes, before step B; their structure was not inspected until after the step-B commit.

## Rubric (step B, before either input file was opened)

- `rubric.md`: sections 1 to 4 unchanged (the first 11,564 bytes still hash to `81fc6e0e5c66decf674b0b069c47b3c42dc56372f73a6f2223866a15fbc07bc8`); section **2b, the composition item** (dated 2026-10-28) appended after section 4, with the brief's text verbatim, section 2's five bands restated for the combination (same boundaries and meanings) and a one-line reason rule (at most 25 words). New sha256: `20962e5a008a00535e36a17ad888268e11f1d756473c345e1147e00c1ebc1662`.
- `rubric-passes-2.md`: a two-line header, then sections 1 and 2 (lines 5 to 45 of `rubric.md`, byte-identical) and section 2b (byte-identical to `rubric.md`'s); no section 3 or 4. sha256: `8354e3bfd32875a0f0b82d1aa5364bb5dba624c52e7431565db1e59855331477`.
- Word check on `rubric-passes-2.md` (case-insensitive: monitor, suspic, detect, planted, honest, synthetic, placeholder, attack, red.team, harm): three lines hit, all verbatim text: "red-team checklist" as a document name in section 1 (line 7) and section 2 rule 1 (line 36), both unchanged from 07k, and "harm" in 2b's own wording (line 48). No other hit. The pass prompts are checked separately before launch.

## Order of events (local time, IST)

1. 14:06 to 14:09. Read the files above; checked the rubric and rubric-passes hashes (both match) and the stripped files' hashes (both match `8492196e…` and `f005d5eb…`); confirmed the fork is on `stage3` at `834e1e3` and that the fork copies of `rubric.md`, `rubric-passes.md`, `doc-states-day0.md` and both stripped files are byte-identical to the project copies.
2. 14:10. Created this record.
3. 14:11. Appended section 2b to `rubric.md`; checked the unchanged prefix hash; wrote `rubric-passes-2.md` from the verbatim line ranges and checked both copies of sections 1, 2 and 2b by diff; hashed both; ran the word check.
4. 14:12. Copied `rubric.md`, `rubric-passes-2.md` and this record to `work/mole-fork/results/stage3/t1k-rater/` (byte-identical) and committed them on `stage3` (hash in event 5).
