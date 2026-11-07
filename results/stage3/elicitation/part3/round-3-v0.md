# Writer round 3, one-document arm: record (brief 30 Part 3; the Part 3 session, Sonnet 5.5, Claude Code desktop app; 2026-11-08, runs of 2026-11-07 UTC)

Counts, aggregates and hashes only. No item text, statement, rubric text, answer or key appears here or in any file named here outside the barred directory `part3/writers/` and the caches. No B3 result, score or item was opened; STATUS.md was not read (L30). Spend: about $46.4 outside the writers' own tokens (section 9). Cites: the pinned launch notes `147dae26` and their addendum `4d12978b`; brief 30 notes 12 to 15.

## 1. Outcome in one table (writer round 3 at the cap of 96 per writer)

| writer | course round | feedback | outcome | written | valid | quiet (gate i) | gate (ii) pass | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-6.1-sol | its 3rd | round 2's | attempted (run 1 of 1) | 96 | 96 | 96 | 58 | **47** | **0** | 11 | 32 | 0 | 6 |
| Muse Wonder | its 1st | none | attempted (run 1 of 1), Cursor CLI | 96 | 70 | 61 | 43 | **30** | **7** | 6 | 17 | 9 | 1 |

**Yields per valid item written:** GPT-6.1-sol p_c = 47/96 = 0.490, p_i = 0/96; Muse Wonder p_c = 30/70 = 0.429, p_i = 7/70 = 0.100. **Cumulative, both writers, rounds 1 to 3:** 109 certified (GPT-6.1-sol 79 of 207 valid, Muse Wonder 30 of 70) and **7 quiet-but-illegible, all Muse Wonder's** (GPT-6.1-sol 0 of 207). The certified target of 26 is passed four times over; the illegible arm holds 7 of its floor of 12 and target of 26. Opus 5.5 remains a recorded loss (round 1). **The raising count for the next writer round by rule 3 at the cap:** the pooled illegible yield (7 of 277 valid) needs about 750 items over two writers and three rounds, so **96 per writer**.

The yield curve by writer and round: GPT-6.1-sol round 1: 24 written, 20 valid, 13 quiet, 2 certified, 0 illegible; round 2: 96, 91, 91, 30, 0; round 3: 96, 96, 96, 47, 0. Muse Wonder round 3: 96, 70, 61, 30, 7. The outcome sentence is chosen at the end of the last writer round and is not chosen now. **Rule 1 for Muse Wonder** (note 15): its feedback round, course round 4, runs outside note 12's bar and the floor rule, on Aravind's STATUS line for its spend; its futility test (rule 1) is read on its own two rounds before any third; none of that is read here.

## 2. How each writer ran, and what each could see

Both folders came from `assemble` (packet `cb528f5d`, `round.md` `ca6a3049` for Round 3 / one-document / 96: identical bytes; the document state `d0f3fbae`; the preface `15a98bde`; effort high). Start-state records (existence and sha256 only) are `part3/writers/<writer>-r3/start-state.json`: no instruction file in either folder; no memory index mapped to either; each writer ran with `HOME` on its own empty directory, so no user-level location was present for either.

- **GPT-6.1-sol:** `codex exec` as in round 2 (empty `HOME`, clean `CODEX_HOME`), a background task that survives the turn; 10.75 min; input 349,304 tokens (296,960 cached), output 30,983; its folder holds round 2's items and development feedback in `previous/`. Audit **PASS**: 49 path tokens, 48 not files, 0 outside, 0 never-open (`558e8cb2`). Its commands were `cat` of the folder's files, one `ls -a` and one `python3` over the `previous/` files.
- **Muse Wonder (note 14's Cursor harness):** `cursor-agent -p --output-format stream-json --model muse-wonder-1.0-high --trust --sandbox enabled --workspace <folder>` under `env -i` with `HOME` (empty), `PATH` and `CURSOR_API_KEY` only; the deny-list is the folder's own `.cursor/cli.json` (in the manifest, `verify` clean). 127 s; input 11,337 tokens, output 26,687 (7,865 reasoning). Four tool calls, all on the folder's files. Audit **PASS**: 40 path tokens, 36 not files, 0 outside, 0 never-open (`1e5371e5`).

**Muse Wonder's exposures, re-recorded at launch** (a separate one-turn launch from the same folder with the same flags and environment, asked for names only; no tool call; before the round's launch): **19 skills in context: 15 Cursor built-ins** (agent-sdk-create-agent, autopilot, create-hook, create-rule, create-skill, loop, new-repo, origin, review-bugbot, review-security, sdk, share, split-to-prs, statusline, update-cli-config) **and 4 account-level** (React Best Practices, Tailwind CSS Best Practices, FastAPI Best Practices, Clean Code Guidelines); **0 rules, 0 instruction files, 0 MCP servers**. Probe v1 counted 20 (it also named one called "cursor"); this launch did not. They are name-and-description coding guidance; a read of one would name a path outside the folder and fail the audit, and the writer made none. The five names Aravind may still remove from his account are the four above and "cursor". GPT-6.1-sol's session was not asked to list its context.

## 3. The funnel by mechanism (valid items) and the rejected items

GPT-6.1-sol (96 written, 96 valid, **0 rejected**; it wrote three mechanisms: composed-permission 36, default-exception-schedule 36, indirection 24, and dropped conjunction, which had certified 0 of 19 in round 2):

| mechanism | valid | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |
|---|---|---|---|---|---|---|---|
| composed-permission | 36 | 18 | 0 | 1 | 17 | 0 | 0 |
| default-exception-schedule | 36 | 22 | 0 | 6 | 8 | 0 | 0 |
| indirection | 24 | 7 | 0 | 4 | 7 | 0 | 6 |

Muse Wonder (96 written, 70 valid; **26 rejected**: 20 token check, 3 schema, 3 size; it wrote five mechanisms, including order-dependency, which GPT-6.1-sol has not used; written: conjunction 24, composed-permission 18, default-exception-schedule 18, indirection 18, order-dependency 18):

| mechanism | valid | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |
|---|---|---|---|---|---|---|---|
| composed-permission | 12 | 2 | 0 | 0 | 10 | 0 | 0 |
| conjunction | 20 | 19 | 0 | 0 | 1 | 0 | 0 |
| default-exception-schedule | 17 | 1 | 2 | 4 | 1 | 9 | 0 |
| indirection | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| order-dependency | 15 | 2 | 5 | 2 | 5 | 0 | 1 |

**Rejected items by mechanism (Muse Wonder):** indirection 12 of 18 (all token check), composed-permission 6 of 18 (3 token, 3 size), conjunction 4 of 24 (token), order-dependency 3 of 18 (schema), default-exception-schedule 1 of 18 (token). The loss is concentrated in indirection (12 of 26), where it removed two thirds of the mechanism's items, so indirection is under-represented in the valid pool (6 of 18) and certified 6 of those 6; what the removed twelve would have yielded is unknown. All 9 loud items are default-exception-schedule.

**Where the illegible items are:** all 7 are Muse Wonder's: order-dependency 5, default-exception-schedule 2; in the README (3), the fine-tuning guide (2) and the red-team checklist (2); composition bands 30 to 39 (3), 40 to 49 (2) and 50 to 59 (2). **Matched strata** (writer x document x 10-point band): n_c 7, n_i 5, matched effective n 5.8, in three strata that hold both arms (README 30s: 1 certified and 1 illegible; README 50s: 3 and 2; fine-tuning guide 30s: 3 and 2); 23 of Muse Wonder's 30 certified items and 2 of its 7 illegible items sit in strata with no partner. The two arms' compositions are close (certified mean 42.9, illegible mean 42.6). GPT-6.1-sol's 47 certified items have no partner by construction (no illegible item of its own): matched n_c 0, n_i 0.

## 4. Gate (ii) and (iii), composition, and the readers

- **GPT-6.1-sol (readers Kimi K3 pinned and Sonnet 5.5, every-sample rule):** part-derivable 32: Kimi only 10, Sonnet 5.5 only 17, both 5. Mixed 11: Sonnet 5.5 credited the whole in 6, Kimi in 5. Not evaluable 6, all Sonnet 5.5 (14 of its 768 reads refused). Certified 47 by (Kimi samples crediting the whole, Sonnet 5.5 samples crediting the whole): (2, 2) 27, (1, 2) 13, (1, 1) 5, (2, 1) 2. All 96 pass gate (i); composition 39.0 to 63.5, median 50.0; certified in all six documents (10, 9, 7, 6, 7, 8) and in bands 30 to 39 (7), 40 to 49 (14), 50 to 59 (4), 60 to 69 (22).
- **Muse Wonder (readers Kimi K3 pinned and GPT-6 Sol on Bedrock, Sol's mean rule):** part-derivable 17: both readers 11, Kimi only 4, Sol only 2. Mixed 6: Kimi credited the whole in 4, Sol in 2. Not evaluable 1 (a Sol value missing). Gate (i): 61 of 70 pass; composition 16.0 to 75.0, median 42.0; certified in all six documents (6, 3, 10, 5, 4, 2) and bands 10 to 19 (3), 30 to 39 (7), 40 to 49 (10), 50 to 59 (10).

## 5. Proxy agreement, development against certification (counts)

| writer | rater Spearman | rater within-target agreement | Kimi whole | Kimi part | second reader whole | second reader part |
|---|---|---|---|---|---|---|
| GPT-6.1-sol | 0.928 | 1.00 | 0.71 | 0.82 | 0.90 (n 91) | 0.87 (n 90) |
| Muse Wonder | 0.881 | 0.96 | 0.84 | 0.87 | 0.93 (n 60) | 0.90 (n 61) |

The lowest figure is Kimi's whole-credited agreement for GPT-6.1-sol, 0.71: one development sample against the any-of-two certification reading. No Goodhart gap is named for either writer. Muse Wonder's development feedback was not shown to it in this round (it has none until its next); GPT-6.1-sol's came from round 2's development readers, the certifying pair.

## 6. The rater instrument in round 3 (events; ratified form: one pass is its two scale sessions)

- **Audit fix applied after the verdict was seen (the coordinator's ruling, 2026-11-08):** GPT-6.1-sol's certification statements pass 2 read its own empty auto-memory index (`~/.claude/projects/<its mapped folder>/memory/MEMORY.md`); the read was refused by the session's deny-list and the directory holds no file, so no content was read. The audit counted it never-open (`never_open` 1, record kept as `audit-00-cert-statements-p2-before-fix.json`). Two harness bugs caused that: `session_slug` dropped the leading dash of Claude Code's folder mapping, and a rater folder's never-open root resolved to all of `/Users/aravind`. They were fixed with tests, after the verdict was seen. **It is not a widening:** the audit's design already allows a session's own mapped state directory, so the bugs made it stricter than its own allow-list; the project tree and the other rater folders stay never-open (tested). Re-audit: PASS, 5 path tokens, 0 outside, 0 never-open. The remaining rater sessions' audits (11 of 12 first-pass PASS before the fix) are unchanged.
- **An API failure, not a rater outcome:** GPT-6.1-sol's certification statements pass 1, first attempt, ended with "response exceeded the 64000 output token maximum" after 44 minutes and **$3.11**, with no ratings file; its trace, times and stderr are archived (`*-attempt1*`). The pass was re-run on identical inputs as a fresh session (15 minutes, 288 ratings valid, audit PASS). Both attempts are in the record; the $3.11 is in the spend.
- All 12 rater sessions' ratings files validated strictly (nothing repaired): Sol 288 and 96 per session, Muse 210 and 70.

## 7. The forecast after round 3 (note 12's addendum; `forecast-after-r3-v0.md` 8287d5cd)

Both writers at the cap for rounds 4 to 6, each on its own Jeffreys yields from its observed counts, the statistic matched on the observed strata at the 10-point band within writer x document, a value on the margin reading as below 0.5. **P(stop by success within the remaining rounds): 0.96, which reads at or above 0.5** (floor rule off: 0.96); beside it: the halving case 0.82 (at or above 0.5), the all-matched statistic 0.99, and its halving case 0.94. **The floor rule now:** projected effective n 37.4 against 12, so it does not fire. Counts if every remaining round were run (mean [p10, p90]): after round 4, 174 certified and 14.6 illegible, matched effective n 18.5 [13, 25]; after round 5, matched effective n 31.7 [21, 43]. **Phase E: the expected certified count per further round, both writers: 65.0 [54, 76]** (GPT-6.1-sol 35.0, Muse Wonder 29.9); illegible 7.6 [3, 13].

**Reading it with its weak points:** (a) the illegible side rests on one Muse Wonder round of 70 valid items (7 illegible), so its posterior is wide, which the intervals carry; (b) the forecast holds each writer's yield constant, and Muse Wonder's round 4 is the first round with feedback for it, which may move its yields either way; (c) class is modelled as independent of document and composition, though Muse Wonder's illegible items cluster in three documents and its matched strata are 3 of its cells; (d) future items' strata are resampled from each writer's own valid items; (e) GPT-6.1-sol's certified items cannot match anything while it writes no illegible item. The 0.96 reads above the bar by the margin rule; the bar's decision and Aravind's STATUS line on round 4's spend are the coordinator's.

## 8. The edit-application check and the feedback folders

At the day-0 state (brief 33 A3's path): 0 of 96 (GPT-6.1-sol) and 0 of 70 (Muse Wonder) valid items fail (the check against round 2's states waits for the round-2 brief). **Feedback folders for the next round are built:** GPT-6.1-sol (`round-3/gpt61sol/feedback/previous/`, results 663def0b): 96 valid, 288 of 288 statements within target; Muse Wonder (`round-3/muse_wonder/feedback/previous/`, results 66db5c2e): 70 valid, 210 of 210 statements within target by the development rater; one Kimi part value missing and 10 Sonnet 5.5 and 2 scorer refusals kept as `None`, never zero.

## 9. Spend and the key ledger

| item | $ |
|---|---|
| GPT-6.1-sol development reads (96 items; Kimi 3.05, Sonnet 5.5 0.96, scorer 2.38), cap 22.23 | 6.40 |
| GPT-6.1-sol certification reads (96 items, two samples; Kimi 6.14, Sonnet 5.5 1.93, scorer 4.79), cap 44.46 | 12.85 |
| Muse Wonder development reads (70 items; Kimi 1.54, Sol 0.60, scorer 1.66), cap 16.21 | 3.81 |
| Muse Wonder certification reads (61 items, two samples; Kimi 2.76, Sol 1.06, scorer 2.89), cap 28.25 | 6.72 |
| rater sessions: GPT-6.1-sol dev 2.43 and certification 4.84, Muse Wonder dev 1.93 and certification 4.32 | 13.52 |
| the failed rater attempt (API error, no file) | 3.11 |
| **total** | **about 46.4** |

The two writers' own cost is not in dollars here: GPT-6.1-sol on ChatGPT billing (349,304 tokens in, 30,983 out), Muse Wonder on the Cursor account (11,337 in, 26,687 out). Realised Kimi cost per read: $0.0079 to $0.0080 against the dry run's $0.0166.

**Key ledger (note 11: key 1, key 2 the fallback; no rotation, key 2 unused; Kimi K3 through the pin, all 1,920 round-3 Kimi reads served by Wafer at MXFP4):** the four batches overlapped in time, so the readings are by window. Key 1, limit remaining and account balance (UTC, 2026-11-07): 19:21:48 end of round 2 $141.76 and $296.55; 19:36:00 before Muse Wonder's development reads $141.76 and $296.18; 19:43:26 before GPT-6.1-sol's $140.21 and $294.48; 19:50:03 after Muse Wonder's $137.61 and $291.45; 19:52:44 before Muse Wonder's certification reads $137.16 and $290.98; 20:03:22 after GPT-6.1-sol's development reads $134.40 and $287.17; 20:18:08 after Muse Wonder's certification reads $134.40 and $286.15; 20:42:59 before GPT-6.1-sol's certification reads $134.40 and $285.96; 21:23:16 after them $128.26 and $277.54. **Over the whole round the key's limit fell $13.50, equal to the four Kimi totals ($1.5433 + $3.0512 + $2.7624 + $6.1410 = $13.4979); the account fell $19.01, so $5.51 was other use of that account.** Key 2 stayed at $278.45 and $88.45. Key 1's weekly limit resets on Monday 2026-11-09 00:00 UTC by OpenRouter's rule. **Planning figure:** a full writer round at 96 reads about $19 (GPT-6.1-sol) or $10.5 (Muse Wonder, 70 valid) in the reads and $7.3 or $6.3 in the raters.

## 10. Disclosures and not done

- **Not done in this round:** the human anchor draw (after the last certification); the pair pilot and the cross-document arm; the check of certified and illegible items against round 2's states; the outcome sentence; round 4 (Muse Wonder's feedback round waits on Aravind's STATUS line; the other writer's rounds 4 to 6 wait on the bar's reading and the coordinator).
- **Barrier audit:** opened or run this round: brief 30 notes 12 to 15, the code, the writers' answers only by script (labels and counts), the raters' files only by script; Cursor's final message only by script. Not opened: STATUS.md (L30), any b3-results file, any S3 cache, `s3-applications-v0.json`, any item text, the rubric's text. The Cursor API key was not read or printed; its sha256 prefix `50801a8b` was recorded in round 2's probe.

## 11. Files (hashes are the first 8 hex of sha256)

Code: harness 4ad2ede9, launch ec0494f4, reads d15d4f6a, raters 548a1639, feedback 372f6a95, round 1a516047, forecast 2a937c38. Records under `part3/`: this file; `round-3-v0.json`; `round-3/gpt61sol/round-record.json` (18cddc42) and `round-3/muse_wonder/round-record.json` (8ea1793e); `forecast-after-r3-v0.md` 8287d5cd (.json 44a6265f); `cursor-probe-v1.md` 6f17afef.
