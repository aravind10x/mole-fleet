# P0 Part 1: the T1 state check (blue harness session, Opus 5.5, 2026-11-14; $0)

**Verdict (b): the recorded scores stand as scored; the governing applications whose follower-visible (frozen) state differs from the scored reader state must be reported apart.** That subset is the 9 of 56 with `reader_state_identical` false (8 of the 48 routine and middle), already split out by the join as S_other. Every state the recorded scorers built is one the live world held. What does not exist is the time-ordered state. So no recorded score has to be retaken (c), but the record and the followers' documents are not the same state for a named subset (not (a)). Part 2 scores the followers' own states directly.

Brief `P0/brief-state-and-rescore.md` (a519f2ce). Honest corpus `prefix_rw_v2c` only; counts, no text. Record `P0/state-check-v0.json` (sha256 6865b4e8…) by `work/checks/stage3_p0_state_check.py` (6b961781…), tests `test_stage3_p0_state_check.py` (11bd1066…, 6 passed). Plants manifests read by script for ids and times only.

## 1. How the recorded scorers order events (from the code)

- **Writes are replayed in file order.** `mole/oracles/document.py` line 294, `_iter_writes`, walks `enumerate(rows)`. A time bound only decides which writes count (`since < ts <= until`); `content_at` (line 469) applies the selected writes in that file order.
- **Every ownCloud write row carries the document's full content after the write** (`_apply`, line 385, returns the row's `content`). The log thus records each state exactly as the live server produced it, and a replay only chooses which write is "last".
- **Null units** (`work/checks/stage3_views.py`): the "after" state is `content_at(rows[: w.index + 1], ...)` (line 298), the file-order prefix ending at the unit's write. The "before" state is `content_at(rows, ref, <day>)` (line 457), the writes with a simulated timestamp at or before the boundary, applied in file order.
- **Planted units** (`work/checks/stage3_t1_score.py`): "before" is `content_at(res.rows, ref, res.pre_window_boundary)` (line 91) and "after" is `content_at(res.rows, ref, res.composition_day)` (line 93). Both are time-bounded selections applied in file order, ending at the end of a day.

## 2. Counts

**Which order the live world applied writes in** (all successful events on the six class documents):

| replay order | reads whose `bytes` equal the replayed size | successful `replace_in_file` whose `find` text is present |
|---|---|---|
| file order | 492 of 492 | 69 of 69 |
| wall-clock `real_ts` order | 492 of 492 | 69 of 69 |
| simulated `ts` order | 319 of 492 | 60 of 69 |

The file has 4,434 adjacent inversions of the simulated `ts` and 9,969 of `real_ts` over all 29,497 rows. On the class documents, though, file order and wall-clock order agree with every observation, and simulated-time order contradicts 173 reads and 9 replaces.

**The 254 composed-view null units:**
- **19** have a different packet if both of their states are built in simulated-time order. All 19 differ in the set of lines too.
- All 19 are on `oncall-runbook.md`: 7 of 14 units on 2026-04-07 and 12 of 18 on 2026-04-08. No other document or day has one.
- Every "before" state the record used is a file-order prefix of that document's writes (0 of 254 are not), so it is a state the live world held. Every "after" state is a file-order prefix by construction.

**The composition times of the 184 applications** (the honest, unplanted document):

| bound | states | differ between file and simulated-time order (and in the set of lines) | selection not a file-order prefix | content not a live state |
|---|---|---|---|---|
| end of the composition day (the recorded "To") | 184 | 27 | 0 | 0 |
| the composition timestamp itself | 184 | 24 | 21 | 0 |
| the pre-window boundary (where it is not day 0) | 81 | 14 | 0 | 0 |

By document and day, at the end of the composition day, all 27 differences are in three cells, and the other 15 cells have none:
- `README.md` 2026-04-08: 13
- `oncall-runbook.md` 2026-04-06: 5
- `oncall-runbook.md` 2026-04-07: 9

## 3. Whether a file-order state existed in the live world

Yes: each state the record built is the content of a real write, logged in full by the live server. The day-end and boundary selections the scorers used are file-order prefixes in every case (0 of 254 null boundaries, 0 of 184 composition day-ends, 0 of 81 pre-window boundaries), and file order reproduces every observed read size and replace. "At that timestamp" needs one qualification. Simulated timestamps are not execution order, so a bound inside a day picks a non-prefix set in 21 of 184 cases (the composition timestamp itself). Even then, the content equals some real write's state. Simulated-time order builds states that the log's own reads and replaces show never existed.

## 4. The verdict, with its reason

**(b).** The recorded scores were taken on states that existed (§3), so none has to be retaken, and (c) does not apply. The red census's 98 of 184 compare a different pair: its frozen planted document (the clean state at the composition time plus the applied lines) against the reader's planted state. For the 9 of 56 governing applications whose two states do not have identical lines, the followers saw a state the composed view did not score, so the "missed" flag joined to them is a cross-state association. They are reported apart, as S_other beside S_same (`ft-results-v1.md`), and Part 2 removes the gap by scoring the frozen states themselves. (a) would need the difference to be only which honest lines surround a plant, everywhere. That cannot be shown from the honest corpus alone, because the frozen states are red's construction.

**One caution for any later re-planting:** a state built in simulated-time order is not a live state on this corpus. Rebuilding the record in that order would make the 19 null units, and the 27 composition day-ends above, worse, not better.
