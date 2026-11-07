# Writer round 2, one-document arm, the feedback round: record (brief 30 Part 3; the Part 3 session, Sonnet 5.5, Claude Code desktop app; 2026-11-07 to 08)

Counts, aggregates and hashes only. No item text, statement, rubric text, answer or key appears here or in any file named here outside the barred directory `part3/writers/` and the caches. No B3 result, score or item was opened; STATUS.md was not read (L30). Spend: about $27.6 outside GPT-6.1-sol's own tokens (section 8). Cites: the pinned launch notes `147dae26` and their addendum `4d12978b`; protocol v0.2 `2130c7b7`.

## 1. Outcome in one table (writer round 2 at the cap of 96 per writer; GPT-6.1-sol alone, Opus 5.5 lost in round 1)

| writer | outcome | written | valid | quiet (gate i) | gate (ii) pass | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |
|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6.1-sol | attempted (run 3 of 3) | 96 | 91 | 91 | 35 | **30** | **0** | 5 | 52 | 0 | 4 |

**Yields per valid item written:** p_c = 30/91 = 0.330 (round 1: 0.100), p_i = 0/91 = 0.000. **Cumulative over rounds 1 and 2:** 32 certified of 111 valid (0.288), **0 quiet-but-illegible of 111**. The certified count is above brief 24's target of 26; the illegible arm is empty against its floor of 12 and target of 26. **The raising count for writer round 3 by rule 3 at the cap:** a pooled illegible yield of 0 gives the cap, so **96 per writer**.

The yield curve (this writer, by writer round): round 1, 24 written, 20 valid, 13 quiet, 2 certified, 0 illegible; round 2, 96 written, 91 valid, 91 quiet, 30 certified, 0 illegible. The outcome sentence is chosen at the end of the last writer round and is not chosen now.

## 2. The three runs of round 2 (identical bytes: folder, manifest `verify` clean each time, packet `cb528f5d`, `round.md` Round 2 / 96, preface `15a98bde`, effort high)

| run | what happened | audit |
|---|---|---|
| 1 | finished (exit 0, 9.6 min, 65 KB final message; input 372,614 tokens, output 27,564). The agent ran `cat` on one user-level skill file under `~/.agents/skills`, on its own initiative. **Void:** the final message is held by hash `253a6dab9390`, unread, never extracted or converted (the converter's gate refuses it too). | **FAIL**: `outside_existing` 1, `never_open` 0 (54 path tokens, 52 not files); the path is a user-level skill file; nothing of the project was opened (`b7dbd30d`). The coordinator's ruling (2026-11-07): the PASS condition was fixed before the run and is applied mechanically; accepting the read after the verdict would be a post-look relaxation |
| 2 | **killed by my launch, not a writer outcome:** started with a bare shell `&`, and the process died when the launching turn ended, about two minutes in: no final message, no exit record, no audit. Cause and fix: the launch-survival rule (addendum item 4): a long run is a background task of the orchestrating tool that survives the turn. The coordinator ruled it a launch failure, not a sample. | none (no exit) |
| 3 | **the attempt:** a background task that survives turns, `HOME` pointed at an empty directory and the clean `CODEX_HOME`; exit 0, 10.5 min; input 140,440 tokens (91,904 cached), output 30,631 (6,481 reasoning); five commands, all `cat` of the folder's files. | **PASS**: 46 path tokens, 45 not files, `outside_existing` 0, `never_open` 0 (`8ec053a5`) |

**The gap and its fix, recorded in the addendum and the start-state code:** `~/.agents/skills` was not on the launch notes' list of user-level instruction locations, so run 1's start-state record did not name it and the launch did not hide it; round 1's writer had the same exposure and did not read it. Fixed: the start-state record lists `.agents` (test), a codex writer runs with `HOME` on an empty directory (a probe showed `~/.agents` absent), and the launch-survival rule. The audit rule is unchanged.

## 3. The funnel by mechanism (valid items) and the five items the converter rejected

| mechanism | valid | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |
|---|---|---|---|---|---|---|---|
| composed-permission | 24 | 11 | 0 | 0 | 13 | 0 | 0 |
| conjunction | 19 | 0 | 0 | 0 | 17 | 0 | 2 |
| default-exception-schedule | 24 | 16 | 0 | 3 | 5 | 0 | 0 |
| indirection | 24 | 3 | 0 | 2 | 17 | 0 | 2 |

**The mechanisms of the lost items (the question of note 9 item 5):** all five rejected items are `conjunction` (4 failed the token check, 1 the wording check): 5 of its 24 written, against 0 of 24 for each of the other three mechanisms. In round 1, three of the four lost items were `default-exception-schedule` (3 of its 6) and one `conjunction`. The loss is concentrated again, in a different mechanism: `default-exception-schedule` lost 0 of 24 this round and `conjunction` is under-represented in the valid pool (19 of 24), where it certified 0 of 19 (17 part-derivable, 2 not evaluable). So this round's losses removed items from a mechanism that is not yielding certified items, and do not bias the certified yield upward; `composed-permission` certified 11 of 24, `default-exception-schedule` 16 of 24 (the mechanism whose round-1 items were all loud), `indirection` 3 of 24.

**Where the third gate (ii) item of round 1 went** (note 9 item 5): to **mixed**: Kimi K3 credited the whole on one of its two samples, Sonnet 5.5 on neither. (Round 1: gate (ii) passed 3 of 20: 2 certified and that one.)

**Round 2's gate (ii) and (iii) breakdown:** part-derivable 52: both readers credited a part in 34, Kimi only in 6, Sonnet 5.5 only in 12. Mixed 5: the whole credited by Sonnet 5.5 only in 4, by Kimi only in 1. Not evaluable 4: all Sonnet 5.5 (8 of its 728 reads refused). Certified 30 by (Kimi samples crediting the whole, Sonnet 5.5 samples crediting the whole): (2, 2) 15, (1, 2) 11, (1, 1) 3, (2, 1) 1.

## 4. Gate (i), composition and the strata

All 91 valid items pass gate (i) (round 1: 13 of 20); no statement mean of the 273 is above 60. Composition (two-session mean): minimum 44.0, median 48.5, maximum 66.5, and bimodal: 61 items in the 40 to 49 band, 6 in 50 to 59, 24 in 60 to 69. The certified items: 11 in the 40s, 3 in the 50s, 16 in the 60s; in all six documents (8, 4, 6, 7, 2 and 3). **Matched strata** (writer x document x 10-point band): n_c 0, n_i 0 (certified 30, illegible 0); matched effective n 0.0, because no illegible item exists. The certified arm's composition spread (the slope reading's IQR of at least 20) is not computed here.

## 5. Proxy agreement, development against certification (counts)

- **Rater** (the development session's 273 statement ratings against the two certification sessions' means): Spearman 0.892; within-target (at or under 60) agreement 1.00: the development rater put every statement within target and so did the certification sessions' means.
- **Readers** (the 91 items certification read; development one sample against certification's two): Kimi K3: whole-credited agreement 0.79 (n 91), part-credited 0.76 (n 91); Sonnet 5.5: whole 0.91 (n 88), part 0.68 (n 85). The part-credit agreement (0.68 to 0.76) is the lowest figure and is what one sample against the maximum of two predicts; no Goodhart gap is named, and the writer's feedback came from the development readers, the certifying pair, as the protocol discloses.

## 6. The edit-application check and the harness

The application path's validation at the day-0 state (brief 33 A3's path): 0 of 91 valid items fail (the check against round 2's states waits for the round-2 brief). **The harness's own deny-list is fixed** (note 9 item 5): `assemble` now writes Claude Code's `permissions.deny` with `//`-absolute `Read` patterns and denies sibling writers' trees (tests), and `--cursor-deny` writes a Cursor writer's `<folder>/.cursor/cli.json` (single-slash patterns; the form found by probe, `cursor-probe-v1.md`); the harness is 93b4a0c6. Defects found and fixed in this round, each with a test: the folder's own path counted as never-open (Cursor's init event names the cwd); the run summary's key labels refused by the reader's print guard (keys are numbers now).

## 7. Round 3: what is ready

- **Sol's feedback folder** is built (`round-2/gpt61sol/feedback/previous/`, results 677befa2): 96 results, 91 valid, 273 statements within target by the development rater; Kimi K3 and Sonnet 5.5 recovery figures with 7 refused Sonnet 5.5 values kept as `None`.
- **Muse Wonder** (Cursor CLI; probe v1 PASS, the five account-level skills a disclosed exposure by note 14): launch only on the coordinator's line; at launch the skills in context are re-counted by name beside the start-state record (the probe's count: 20 names, 15 built-ins and 5 account-level). Its round 3 is a first round for feedback purposes and its items are matched within writer.
- **The forecast after round 3's certification** is a command (`stage3_elicitation_forecast.py after`, the matched statistic on the observed strata, per-writer Jeffreys yields, the halving case and the all-matched statistic beside, a value on the margin reading as below 0.5, and Phase E's expected certified per further round); it was not run now because the bar is read after round 3. With 0 of 111 illegible so far, the forecast's illegible side will be set by round 3.

## 8. Spend and the key ledger

| item | $ |
|---|---|
| development reads (91 items, one sample; Kimi 2.74, Sonnet 5.5 0.92, scorer 2.25), cap 21.07 | 5.91 |
| development rater sessions (2) | 3.51 |
| certification reads (91 items, two samples; Kimi 5.51, Sonnet 5.5 1.84, scorer 4.50), cap 42.14 | 11.84 |
| certification rater sessions (4) | 6.38 |
| Cursor probes (model list and launches; Cursor account, no API dollars) | 0 |
| **total** | **about 27.6** |

GPT-6.1-sol is ChatGPT-billed: run 1 372,614 tokens in and 27,564 out (void), run 3 140,440 and 30,631; run 2 died partway. The caps follow note 4 item 3 scaled to the items read (development 91 of 192: the upper bound plus five percent $21.07; certification: $42.14). Realised Kimi cost per read: $0.0075 (development) and $0.0076 (certification), against the dry run's $0.0166.

**Key ledger (note 11: Kimi through the pin on key 1; key 2 the fallback, never used this round; no rotation):**

| time (UTC, 2026-11-07) | key | limit remaining | account balance | event |
|---|---|---|---|---|
| 18:00:20 | key 1 | 150.00 | 311.19 | before; the first live reading |
| 18:12:49 | key 1 | 150.00 | 308.73 | before the development reads ($2.46 of account use by another key since 18:00; the limit untouched) |
| 18:32:09 | key 1 | 147.26 | 305.71 | after the development reads: limit down $2.74, equal to Kimi's $2.7357; account down $3.02, so $0.28 of other use |
| 18:43:57 | key 1 | 147.26 | 305.48 | before the certification reads ($0.23 of other use since) |
| 19:21:48 | key 1 | 141.76 | 296.55 | after the certification reads: limit down $5.50, equal to Kimi's $5.5065; account down $8.93, so $3.42 of other use |
| 18:00:21 | key 2 | 278.45 | 88.45 | unchanged since round 1; not used |

The account balance is the binding figure (L7) and has $296.55 left on key 1's account. Key 1's weekly limit resets on Monday 2026-11-09 00:00 UTC by OpenRouter's rule (computed from the limit's "weekly" setting, not returned by the API); a round launched after that finds the limit back at $150. **Planning figure:** a full round at the cap reads about $17.75 for the reads and $9.9 for the raters (this round: 91 valid items).

## 9. Disclosures and not done

- **Cursor probes:** probe 1 (v0) let a probe agent read the project's README (a project description, no item and no result; the trace is in the barred directory) because the deny-list had not taken effect; probe v1 refused the same read. No writer saw the project.
- **Not done in this round:** the human anchor draw (after the last certification, protocol section 9); the pair pilot and the cross-document arm (the pair extension of the reader and the pair rubric file are not built; the one-document arm has priority); the check of certified items against round 2's states; the outcome sentence; the round-3 launch (coordinator's line).
- **Barrier audit:** opened or run this round: briefs 30 notes 9 to 14 and the notes' referenced records, the converter's, reader's, runner's and harness code, the Cursor CLI's help, version and a search of its bundled files for option and variable names, the writers' answers only by script (labels and counts), the raters' files only by script. Not opened: STATUS.md (L30), any b3-results file, any S3 cache, `s3-applications-v0.json`, any item text, the rubric's text, Opus 5.5's and run 1's final messages (held by hash). The Cursor API key was never read or printed; its sha256 prefix `50801a8b` was.

## 10. Files (hashes are the first 8 hex of sha256)

Code: harness 93b4a0c6, launch ec0494f4, reads d15d4f6a, raters 77b06761, feedback 372f6a95, round 1a516047, forecast 2a937c38. Records under `part3/`: this file; `round-2-v0.json`; `round-2/gpt61sol/round-record.json` (64a0f134); `cursor-probe-v0.md` 0f4a6f3a and `cursor-probe-v1.md` 6f17afef; `forecast-v0.md` 1348ce81 (written after round 1, unchanged).
