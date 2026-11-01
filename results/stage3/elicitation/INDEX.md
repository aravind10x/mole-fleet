# work/stage3/elicitation index (brief 29, session 29-A, 2026-11-01)

Brief 24's E0, part A: the taxonomy, the writer packet, the certification protocol, the rules and sentences, and the cross-document items. Session 29-B (E0-5 gate reachability, E0-7 pinning in the client) has not opened. No writer has been called, no item written. Hashes are full sha256 in the table; the short form (first 8 hex) is what STATUS carries.

## Files

| id | file | sha256 | bytes |
|---|---|---|---|
| E0-1 | `taxonomy-v0.md` | `ec195e238e64c9db65fff7f35e279b32e6733a13b22321ba34851d6a71d2a687` | 7960 |
| E0-2 | `writer-packet-v0.md` | `4b5d6027b4700ba385f4491ef54893e97e952ded6ea62ff5ae95ebec9564eac6` | 19871 |
| E0-2 | **the packet as sent** (text between its `PACKET` markers; `stage3_elicitation_packet_check.py extract`) | `cb528f5d4cf0875b00f5351ccbafd29ce1777968543e102fb4fdccfde1192886` | 13541 |
| E0-2 | `writer-launch-notes-v0.md` | `147dae26126f870467e89d44382c59e0668f57e715c76c66c095b10d5f567fba` | 8090 |
| E0-3 | `certification-protocol-v0.md` | `57ec87e707713cb90c997cd04525cbbc50fc48a2d7e8a587f109a120e10d69ce` | 13460 |
| E0-4 | `rules-and-sentences-v0.md` | `b666cb32113fd27dc3e1ca7bdcfe666294bf6acfe1d473e6c3dc4e7380aa4a4a` | 10076 |
| E0-6 | `cross-document-items-v0.md` | `941524292f5bad9bcea751faf6e3fd6125fe73951d0d288df36180dd25ac6ba0` | 12254 |
| input | `doc-states-day0-v7.md` (the cross-document arm's document state, seed version v7) | `9c6933940d19a3dddd606cec08cef3324bb404b2a74cd4abc6b42c60f4ce7207` | 5454 |
| input | `work/stage3/t1k-rater/doc-states-day0.md` (the one-document arm's state, seed version v6; existing) | `d0f3fbae0e1b67125196263395edcd658c000458dc54b8460e9a691e4edf31e0` | 4753 |
| code | `work/checks/stage3_elicitation_render_docs.py` | `33607749140f8dc4e8c254c944d8663c8db63313c0247864bfff392b9ccfefeb` | 3533 |
| code | `work/checks/stage3_elicitation_packet_check.py` | `f00ac28068485e34ec68e6949c70df1f6d8b4a0e14139ca59e450cd5c47889fe` | 10255 |
| code | `work/checks/test_stage3_elicitation_packet_check.py` | `f57efe01b83dcbe6431d51f3be7a513b9e98f54010f48fcc40b371655cc079d0` | 2944 |

Referenced, not changed: `work/stage3/t1k-rater/rubric.md` `20962e5a…c1662`; `work/checks/stage3_legibility.py` `1ba39b96…bc281`; `work/checks/stage3_t1v2_checks.py` `c0fe68c5…e023e`; `work/mole-fork/mole/seeders/seed_class_docs.py` `43eb1cae…8ae8344`.

## Checks run (all $0, no API call)

- `stage3_elicitation_packet_check.py check`: **PASS**. The taxonomy text embedded in the packet equals the taxonomy file's marked region byte for byte; zero hits in every scan class (filter-field, framing and weakening vocabulary from `stage3_t1v2_checks.py`; brief and amendment numbers; repository paths; model, vendor and instrument names; the words brief 26 v2 replaced; nonce-like strings); the three schema blocks parse once placeholders are filled and carry exactly the key sets below.
- `stage3_elicitation_packet_check.py fields`: `document`, `kind`, `composed_effect`, `statements`, `op`, `anchor_or_region` and `text` are all indexed by `stage3_legibility.py`. `id` is the writer's own and is mapped to an opaque id before any reading. **Brief 25's items file was not opened** (it is barred to 29-A); its field names are verified through the reader code that consumes it.
- `test_stage3_elicitation_packet_check.py`: 6 passed.
- `stage3_elicitation_render_docs.py v6 --check` reproduces `doc-states-day0.md` byte for byte (the test that the renderer is the rendering briefs 23 and 25 used); the v7 render differs from it only by the eight shared lines of `SHARED_LINES_V7` (checked by `diff`).
- Seeds chosen (`20261211` human anchor, `20261212` null pairs, `20261213` false targets): no earlier brief or script in `briefs/`, `work/checks/` or `work/stage3/` uses them.

Schema (E0-2): item `id, document, statements, composed_effect, kind`; statement `op, anchor_or_region, text`. Cross-document pairs use `documents` on the item and `document` on each statement (an extension for that arm only). `kind` carries the mechanism label (see "Readings adopted", 1).

## Authoring record (brief 29, addition of 2026-11-01 night)

- **Author:** Sonnet 5.5 (`claude-sonnet-5-5`), Claude Code desktop app, on the project root. In the fallback order Opus 5.5, Sonnet 5.5, GLM 5.3 on Cursor this is the second; this session did not establish whether an Opus 5.5 attempt was stopped first. Not Cursor, so there are no Cursor user rules to state.
- **Also writes or reads in round 2?** Sonnet 5.5 is the second reader of GPT-6.1-sol-written items (certification protocol, section 5), so the author's family reads. Disclosed in every round-2 table; not blocked.
- **Loaded at start:** the auto-memory index for this project (`MEMORY.md`, 29 lines), which lists prior states by title and one line each, among them lines that mention earlier rater, judge and pilot findings; and the `superpowers` plugin's session-start text with the skill list. No `CLAUDE.md` or `AGENTS.md` was loaded (neither exists at `~/.claude/CLAUDE.md`, `~/AGENTS.md` or in the project). **Nothing from those lines was used to define a mechanism, a gate or a rule;** the taxonomy's mechanisms are brief 24 E3's list, and the counts quoted in `rules-and-sentences-v0.md` are marked as orientation from the amendments.
- **Written to memory:** nothing.

## Barrier audit: what 29-A read

Read: briefs 29, 24 (with its three amendments), 22, 23, 25, 26, 32's authoring note, 08e, 07s's composition amendment; brief 15 lines 33 to 62 (Part W), 128, 238 to 243, 248 to 269, 271, 273 to 294 and 300 (A5.4, A6.14.2 to A6.21; not A6.17.9); `work/stage3/INDEX.md`; the first 60 lines of `STATUS.md`; `work/stage3/b3/writer-spec-b3.md`; `work/stage3/t1k-rater/rubric.md` sections 1, 2 and 2b and `doc-states-day0.md`; the codex and zsh memory notes; code only for names and constants (`stage3_legibility.py` by grep and lines 322 to 346; `stage3_t1v2_checks.py` by grep; `stage3_b3_trace_audit.py` first 40 lines; `seed_class_docs.py` lines 155 to 210; `stage3_b4r_design.py` lines 1 to 100); `codex --version` and `codex exec --help`; the existence (never contents) of `~/.codex` and `~/.claude` instruction files, and the section headers of `~/.codex/config.toml`.

**One result file was opened:** `work/stage3/b4r/b4r-results.md`, **lines 1 to 34**, because brief 29 E0-2 names its "Constraints this world puts on B4" section as the source. That span also contains the world-repair summary and Z5 figures (lines 1 to 24). None of those figures is used anywhere in these files; the constraints (lines 25 to 33) are cited in `cross-document-items-v0.md`. The cold read should decide whether that reading, which the brief's "reads no result file at all" does not strictly allow, matters.

Not opened: S3's outputs, any judge cache, `work/stage3/b3/b3-results.*`, `plan*.md`, the anchor sheet and its draw file, `work/stage3/red/`, persona and rater-key files, brief 23's and brief 25's result files (`work/stage3/legibility/`, `work/stage3/b3/comprehension/`, including `stratum-plan.json`, whose `sol_rule` is quoted from brief 15 A6.17.1), any candidate, control or paste file, and any item text.

## Readings adopted by 29-A (for the cold read; each is marked where it is used)

1. **`kind` carries the mechanism label.** Brief 29's schema has one categorical field, brief 24 E3 asks for yield by mechanism, and the reader code only compares `kind` for equality when it matches false targets. The earlier content kinds (value, path, recipient, label, procedure) are not asked of writers. (`taxonomy-v0.md`, notes 1 and 3.)
2. **Cross-document spread.** "At least three mechanisms per round" is applied to the one-document arm as written. For pairs the constraints admit one mechanism, so it becomes "at least two of the three eligible shared lines per round". (`taxonomy-v0.md`, note 1; packet section 7.)
3. **Eligible shared lines** are three: the red-team suite config and the sign-off contact (red-team checklist with release-gate runbook) and the on-call contact (README with on-call runbook), from constraints 1, 4 and 5 read together. This is narrow. (`cross-document-items-v0.md`, section 3.)
4. **Gate (iii)** is read per reader on at least one of its own two samples, from brief 29's arms sentence. E0-5 should also report the same-sample reading. (`certification-protocol-v0.md`, section 4.)
5. **Quiet-but-illegible includes gate (ii).** Brief 29 E0-3's shorthand omits it; A6.16.3 and A6.17.5 include it. (Section 6.)
6. **The comparison arm also passes the edit-application check,** since round 2 plants both arms. Brief 29 names certified items. (Section 7.)
7. **Readers run only on items that pass gate (i)** (a saving of calls; the arithmetic is an upper bound); development reads every valid item. (Section 3.)
8. **Mechanical status in the feedback.** Brief 29 lists the rater score and the comprehension rates; the results file also carries `valid` and `failed_checks`, because a writer cannot repair a draft that was never rated. The packet states the rating's direction and a `within_target` flag, not the number 60 or any band. (Protocol section 2; packet section 8.)
9. **Raising rule, cap of 48 and rounding to 6** for the counts per round, and the definition of "development mean L" for the futility test. (`rules-and-sentences-v0.md`, rules 1 and 3.)
10. **The yield orientation** in the rules file uses brief 25's counts as quoted in A6.17.5 (11 and 7 of 78); it shows the certified count binding the target (about 31 per writer-round) and the illegible count binding the floor.
11. **Human anchor:** per arm, once, after the last certification reading; 20 items, half certified and half other items passing gate (i); seed 20261211. (Protocol section 9.)
12. **Statement-shape rule paraphrased** in neutral words (no "harm", no "safeguard"); the constraints are the same. The header of the packet records the mapping.

## Open for brief 30 (and 29-B)

- **A per-statement `token` is not in the schema.** B3's application step carries a consequence token per statement for carrier matching (B3 spec: distinct, six characters or more, zero occurrences in the documents and the corpus). Either writers are asked for it, or blue extracts and checks one by script. Not decided here.
- **Reader-code extension for pairs** (`stage3_legibility.py` requires exactly three statements and one document per item), the same for the rater-sheet builder, and the amended composition wording for pairs. A named prerequisite of any pair reading.
- **Harness configuration at start.** Both CLIs on this machine load plugin and skill text at start (launch notes, section 3). Clean `CLAUDE_CONFIG_DIR` / `CODEX_HOME` or record-and-accept is brief 30's decision; 29-A recommends the clean configuration where the login allows.
- **Counts and cost:** the dry-run price of development and certification, the cap of 48, which arm each round writes, the pair null's N.
- **Muse Wonder's harness** is unknown; Aravind records it when it is used.
- **29-B:** E0-5 (gate reachability and null safety at two samples, with both readings of gate iii) and E0-7 (provider pinning in `judge_openrouter.py`, opt-in, defaults unchanged under A6.21, one cents probe). The rule that Kimi K3 is pinned (Wafer at MXFP4 if available) is carried into the protocol by reference to E0-7.

## Records not done by this session

The fork mirror (`results/stage3/elicitation/`, `scripts/stage3/`) is not written and nothing is committed or pushed; `briefs/INDEX.md` has no row for brief 29 from this session. One `STATUS.md` line is appended (see the log).
