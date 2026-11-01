# Authoring note: 29-A v0.1 (a fresh Sonnet 5.5 session; $0; no writer called, no item written)

Written 2026-11-02 by the coordinator (Fable 5.1) after the review session's cold read of 29-A and brief 29's dated notes of 2026-11-02. The session revises the six 29-A files to v0.1 with the cold read's fixes and nothing else. Working directory: the project root `/Users/aravind/KruxAI/tais-project-selection`; the fork is `work/mole-fork` (branch `stage3`).

## Load list (and nothing else)

- `briefs/29-elicitation-e0-2026-11-01.md` (its dated notes of 2026-11-02, items 1 to 7, govern).
- `work/stage3/elicitation/review/cold-read-29a-2026-11-02.md` (43b2f01b): the reconciled verdicts table and the fixes under each file; `fable-read-29a-2026-11-02.md` (3f4a413c): the per-file fix lists.
- The six 29-A files and `INDEX.md` in `work/stage3/elicitation/`, and `work/checks/stage3_elicitation_packet_check.py` with its test.
- `work/stage3/b4r/b4r-results.md` **lines 25 to 33 only** (the seven constraints), for the extraction in step 5.
- Not loaded: brief 15 beyond what the dated notes cite; any result file; `plan*.md`; `work/stage3/b3/comprehension/`; `work/stage3/legibility/`; any item, candidate, control, comparison or paste file; red/, persona or rater-key files.

## Steps

1. **The writer packet:** change the header's schema sentence only (the reader and application paths need a converter; the field names occur in the reader code). The packet body between the `PACKET` markers is not touched: `stage3_elicitation_packet_check.py extract` must still give cb528f5d.
2. **The certification protocol:** cite `stratum-plan.json` → `choice.sol_rule`; add the development-reader note (dated note 3); add the gate-(ii) strictness disclosure (Sonnet 5.5's every-sample rule for Sol-written items against Sol's mean rule; E0-5 reports pass rates by rule); rename "round" to "writer round" where it means a writer round; reword "reads items in the output schema of E0-2 unchanged" to say a converter supplies the reader's inputs; the human anchor's size is left as written with a line that Aravind confirms 20 or 20 per arm.
3. **The rules and sentences:** define p over valid items written in writer round 1 and say the orientation (brief 25's counts) understates yield's denominator; state that n_r is the quantity rounded up to a multiple of 6; "writer round" throughout; add the cold read's cap table (quoted, with the cap named as Aravind's capacity call).
4. **The cross-document items:** the pair extension is needed in four places (the legibility reader, the rater-sheet builder, the application module, the inserter dry run), named by file; constraint 5's reading (per pair, three lines; per cell, six) flagged for the coordinator's confirmation; a six-pair development pilot before 24 per cell is priced; the honest-pair null's N is brief 30's.
5. **`b4-constraints-v0.md`** (new): the seven constraints copied verbatim from lines 25 to 33 of the B4-R results file with that provenance line, so later sessions open no result file.
6. **INDEX:** the fork commit (712e23a) in place of the stale line; "eleven lines (eight shared items)"; the open list gains the converter, the `kind` collision (mechanism to its own field), the token decision and the four-place pair extension; a v0.1 table of hashes.
7. **The packet check:** add a load smoke test that builds one synthetic triple, payload and key from the placeholder item and calls the reader's loader (names only; no item text), or rename the printed claim of `check_fields` to what it proves. Tests pass.
8. Re-run `stage3_elicitation_packet_check.py check` (PASS, 0 hits) and the tests; record every v0.1 hash in INDEX; mirror to the fork (`results/stage3/elicitation/`, `scripts/stage3/`), commit, do not push; one STATUS line listing the v0.1 hashes.

**Do not:** write or edit any item; call any writer, reader, rater or judge; change the packet body; save anything to memory; print any item or document text.

**Done means:** the six files and INDEX are at v0.1 with their hashes in STATUS; the packet body as sent is still cb528f5d; the checks and tests pass; the mirror is committed.
