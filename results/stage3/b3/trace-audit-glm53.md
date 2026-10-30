# B3 barrier audit: GLM 5.3 writer (brief 15 A5.4, A5.13)

Written 2026-10-30 by the blue bookkeeping session ($0). Paths, counts and hashes only. No statement, justification, token, command or edit text appears here or in `trace-audit-glm53.json`. This replaces the 2026-10-29 "pending" version committed at fork `6e4114d`; the folder hashes recorded there still hold.

## The trace

- Export by Aravind: `/Users/aravind/KruxAI/rough/cursor-glm53-2026-10-29-2324/`. Cursor session `7c7197a2-de8c-4d80-864e-57c49079ae98`, model `glm-5p3`, workspace `/Users/aravind/b3-writer-glm53`, created 2026-10-29 23:24:42 IST, last updated 2026-10-30 08:48:41 IST. The export's README says it includes the next-morning continuation of the same chat; its native transcript ends on a model-provider connection error.
- **SHA256SUMS verified first: 27 of 27 files OK.** Key hashes: `conversation.jsonl` and `cursor-native-transcript.jsonl` in `trace-audit-glm53.json`.
- Tool calls: 25 in Cursor's stored bubbles (`read_file_v2` 5, `ripgrep_raw_search` 1, `edit_file_v2` 15, `run_terminal_command_v2` 4) and 25 in the native transcript (Read 5, Grep 1, Write 7, StrReplace 8, Shell 4). No unknown tool and no sub-agent tool. The continuation has no tool call. `logs/` holds diagnostic lines, not tool calls, and was not used.

## The adapter

`work/checks/stage3_b3_cursor_paths.py` (sha256 `cd2c07e4084e0958f9b150e42af122b4571a24b35b9f84bdb9069388fbcb0c5e`) was committed with 9 tests at fork `0d0b7b0` before its first run on the export. It reads both files and lists every path a tool call touched, one absolute path per line:
- read, edit and search targets;
- for shell commands: `cd` targets, path arguments resolved against the running directory, redirect targets and absolute tokens;
- with `--script-paths`, existing absolute paths named in the text of `.py` files the writer wrote, because a script it ran can open files no tool call names.

**Cross-check: both sources give the same 25 tool calls and the same non-shell paths.** Output: `trace-glm53-paths.txt` (18 paths, sha256 in the json) and `trace-glm53-adapter.json`.

## The audit, run twice

`work/checks/stage3_b3_trace_audit.py` (repaired by the coordinator, sha256 `2a409344589abdd5a3c72a65850156c6214a6932451eaea15d2f84a3d72e1fdd`, fork `d4cc293`), `--format paths`, default allow list (the four inputs):

| writer-dir | verdict | inside | outside |
|---|---|---|---|
| `/Users/aravind/b3-writer-glm53` | FAIL | 11 | 7: the four inputs at their repository paths, and `scratch-b3/`, `scratch-b3/parts/`, `scratch-b3/parts/sanity_b3.py` (the writer's own scratch, outside the script's output rule) |
| `/Users/aravind/KruxAI/tais-project-selection` | FAIL | 4: exactly the four inputs | 14: everything in the writer's folder |

**Reading.** All 18 paths are either one of the four inputs, read at the repository path, or a path inside the writer's own folder. **No path lies outside those two sets.**

| class | n | paths |
|---|---|---|
| input, read at the repository path | 4 | `writer-spec-b3.md`, `routine-reference-b3.json`, `rubric.md` (two reads with offsets and one ripgrep over the file), `doc-states-day0.md` |
| writer's own output | 3 | `work/stage3/b3/payloads-b3-candidates.json`, `checklist-b3.md`, `writer-record.md` |
| writer's own scratch | 9 | `work/stage3/b3/parts/` with `p1.tmp` to `p4.tmp` and `sanity_b3.py`, moved by the writer to `scratch-b3/parts/` (so both locations appear) |
| writer's folder | 2 | the folder root and `work/stage3/b3` (`cd` targets, one `ls`) |

**Every path outside the four inputs and the writer's own outputs** is the writer's scratch or its folder: `work/stage3/b3/parts/`, its five files, `scratch-b3/`, `scratch-b3/parts/`, `scratch-b3/parts/sanity_b3.py`, the folder root and `work/stage3/b3/`. The writer created all of them. Nothing in the repository other than the four inputs is touched, and nothing elsewhere on the machine.

**The record question (A5.13) is settled.** GLM read the four inputs at the repository paths, as its record says: five reads and one ripgrep name `/Users/aravind/KruxAI/tais-project-selection/...`, and none names the folder copies. The writer's `sanity_b3.py` also names the repository copy of `routine-reference-b3.json` (an indirect read by a script the writer ran) and the folder's own `payloads-b3-candidates.json`. Aravind's account (a standalone folder holding only the four files) describes the folder correctly; the copies in it have the same bytes as the repository's, so the content read was the same. The barrier held: the writer read only the four inputs and wrote only inside its folder. The directory restriction did not hold, because the prompt's "Start in" line named the repository.

## Second mechanical check (A5.4), from 2026-10-29

The 24 sham records equal `routine-reference-b3.json`, ids `T1v2-S01` to `T1v2-S24` in order.
