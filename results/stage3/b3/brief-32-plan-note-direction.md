# Direction for the one post-S2 dated note on `work/stage3/b3/plan.md` (the brief 32 session, Opus 5.5, or a fresh Sonnet 5.5 session; $0, no API call; after S2, before the S3 brief)

Written 2026-11-02 by the coordinator (Fable 5.1) under brief 15 A6.23 and A6.24 (2). The note is the only change to `plan.md` between S2 and S3; the S3 brief cites the hash this note produces. Working directory: the project root `/Users/aravind/KruxAI/tais-project-selection`; the fork is `work/mole-fork` (branch `stage3`).

## Load list (and nothing else)

- `work/stage3/b3/plan.md` (4c677dee): §2.2, §2.6, §3, §4.6, §4.10, §9, and the dated note at the end with its `s1-preflight-sha256` block.
- `briefs/32-b3-s2-estimate-2026-11-01.md` (58df6ec1): H1's departure paragraph and H2's rule for S3 (tag 6), whose wording the note copies.
- `work/stage3/b3/s2-estimate-v0.md` (8254bc4f) and `.json` (46d2e153): H1's total, H2's table and add-on, H3's skip note.
- `work/stage3/b3/judge-client-equivalence-v0.md` (a657e7e6): G2's "by construction" statement, the fdce438b sentence, the one named default-path change.
- `briefs/15-b3-distributed-visibility-2026-10-28.md`: A6.21 to A6.24 only. **Do not read Part W, Part R, or any writer, rater, candidate, control, comparison or paste file.** Ids, counts and hashes only; no item line or document text.

## The note's content (one dated note, appended after the existing one)

Heading: "Dated note, 2026-11-02: S2's record; the control items' valid-draws table; one procedural change to §9; brief 31's disclosures; the pre-flight hash list restated". It states, in this order:

1. **The valid-draws file.** §2.2's `valid_draws` argument for S3 is `work/stage3/b3/inserter-dry-run-v1.json` (full sha256 of 02138931…), written by S2 from a copy of brief 26's script (`work/checks/stage3_b3_inserter_dry_run_v1.py`, full sha256 of 825a82f0…); its `items[]` equal edd289ce's except the control items' `lone_lines`, tested (S2's tests (a) to (d)); edd289ce stays as brief 26's record and the candidates' source. The restricted mode reads v1 unchanged.
2. **The control items' lone-line add-on (A6.22 (2)) runs.** Stream tag 6 is in. The rule for S3, in brief 32 v3 H2's words: S3 draws a control item's lone lines on tag 6 once, after every control pair of tag 3 is drawn, with `exclude` set to that control item's two authors as drawn; a control item any of whose lines cannot then supply two draws by different authors leaves the add-on whole (all three lines), stays in the control arm, and is counted; §2.4 (3) applies to an application-time refusal; the control arm's pairs never depend on the add-on. S2's check: all 21 net control items pass under every valid pair. §2.6 gains 126 lone-line units on each of the four per-agent rows (the live rows and `O_diff` stay at 0), so the totals read 2,088 item units and 2,256 lone-line units, 4,344 in all; the units are added to the table or stated beside it, whichever keeps §2.6's rows intact.
3. **The k = 2 arm is not run** (§4.6's "not run" branch; A6.22 (3); S2's H3: it fails cleanness tests (i) and (iii)). Stream tag 5 is unused.
4. **§9, one procedural change.** S2's figure was computed by Part 2's method on §2.6's units (per-unit bases times units), not by `--dry-run`, because a dry run needs the position draws, which §3 leaves to S3. The exact token count and the re-base happen in S3's first batch (about 20 Opus 4.8 units) and are reported before the rest of S3 runs. The figure for Aravind: H1 $68.17 plus the add-on $8.45 = $76.62; the stop is twice the figure he confirms, $153.25, unless he re-confirms. Wording: **"No analysis rule changes; one procedural change"** (§9's dry run replaced by Part 2's method; the re-base moved to S3's first batch). A6.22 (4)'s $4 re-read is unchanged (after 29-B's E0-7).
5. **Brief 31's disclosures, carried into S3's record (§4.10):** G2 holds by construction, not by re-parse (no cache holds a raw reply); Sonnet's sealed nulls were produced by client fdce438b, which is not on disk, and the match of the current client's built requests against the nulls' recorded request fields is the evidence; the one default-path change (an errored cache line written after an aborted paid attempt; no request or returned value changes) is read as no difference. The pin of §4.10 does not move: brief 29-B's E0-7 adds its option in a new module and leaves `judge_openrouter.py` at e812157c (A6.24 (3)).
6. **The `s1-preflight-sha256` block, restated in full** as a new fenced block of the same name (the pre-flight reads the last one): the 24 lines unchanged, plus one line for `work/stage3/b3/inserter-dry-run-v1.json` and one for `work/checks/stage3_b3_inserter_dry_run_v1.py`, in `shasum -a 256 -c` format. The configuration values below the old block are restated with tag 6 added and tag 5 marked unused.

The note changes no analysis rule, no population, no seed, no view, no instrument and no outcome sentence; it says so in one sentence.

## Steps

1. Run `work/checks/stage3_b3_preflight.py` first (expected PASS, 24 of 24 plus the three sealed prompt components) and verify by `shasum -a 256` the hashes the note will cite (02138931, 825a82f0, 8254bc4f, 46d2e153, a657e7e6, e812157c, 72d394e3).
2. Append the note; change nothing above it.
3. Mirror `plan.md` to the fork at `results/stage3/b3/plan.md` and commit (the pre-flight accepts the block only when `plan.md` equals the fork's HEAD copy); then run the pre-flight again (expected PASS, 26 of 26 plus the three components). Do not push.
4. Report: the new sha256 of `plan.md`, the fork commit, both pre-flight outputs (counts), and one STATUS line.

**Do not:** send any request; compute or draw any position; print any item line, document text or rubric; change any file other than `plan.md`, its mirror, and STATUS; open red/, persona, rater-key, candidate, control, comparison or paste files.

**Done means:** the note is on `plan.md` with the six items above; the restated block verifies 26 of 26; the mirror is committed; the hash is in STATUS.
