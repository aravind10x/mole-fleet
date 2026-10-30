# B3 barrier audit: Sonnet 5.5 same-writer controls session (brief 15 A5.8, A5.13)

Written 2026-10-30 by the blue bookkeeping session ($0). Paths, counts and hashes only. **Aravind asked that this session's transcript not be read by any model.** The audit script read it; this session saw only the script's path lists and filesystem metadata (sizes, times, hashes).

## The session and its outputs

- Folder `/Users/aravind/b3-controls-sonnet55`. It holds the four inputs and the writer's candidates file, all byte-identical to the repository's (`payloads-b3-candidates.json` = `ebce93e8…`), plus the session's two outputs: `controls-b3.json` (sha256 `75fed7d0cfa3bad2e083e264f735074af1f73513a0a7b77bc25a728a6c90631e`) and `writer-record.md` (`d3d2eea9d3017af2e4fc4595b06e63620b24fb0e7858baa058477e294bbbe46a`, one line). Imported unchanged as `controls-b3-sonnet55.json` and `writer-record-sonnet55-controls.md`.
- The record line names model `claude-sonnet-5-5`, harness Claude Code desktop app, "reasoning effort 30", no sub-agents. (The candidates session's trace showed xhigh where its record said 30; this session's effort was not read from its transcript, by the instruction above.)
- Two transcripts sit in `~/.claude/projects/-Users-aravind-b3-controls-sonnet55/`:
  - `2c281827-a6fc-4419-be0e-ed95e92519f6.jsonl` (sha256 `4a490ea17b1886e6…`, 1,198,244 bytes): created 12:06:26, last written 12:11:22 IST. **This is the writer:** `controls-b3.json` was written at 12:10:50 and `writer-record.md` at 12:11:10. It is presumably the session the safeguard stopped near its end. Its scratchpad holds `build_controls.py` (`60a6234e…`) and `validate_controls.py` (`5d5f996e…`), hashed, not opened.
  - `049c4545-c7d1-421b-be0f-52f07088c9a4.jsonl` (sha256 `a3c04142872f7bff…`, 804,809 bytes): created 12:22:45, last written 12:23:59 IST. **It began after both outputs were written** and changed neither (their times are earlier). Its purpose is not known here.

## The audit

`work/checks/stage3_b3_trace_audit.py` (sha256 `2a409344…`, fork `d4cc293`), `--format claude-jsonl --writer-dir /Users/aravind/b3-controls-sonnet55`, allow list: the four inputs, `work/stage3/b3/payloads-b3-candidates.json`, `work/stage3/b3/controls-b3.json`, `work/stage3/b3/writer-record.md`. The full path lists are in `trace-audit-sonnet55-controls.json`.

| transcript | verdict | inside | outside |
|---|---|---|---|
| `2c281827` (the writer) | FAIL | 8 | 6 |
| `049c4545` (later) | FAIL | 7 | 1 |

**Paths outside the allow list:**
- `work/stage3/t1k-rater/` in the controls folder (both transcripts): the directory holding two inputs (a listing or search scope). It is inside the folder; the script allows only the folder, `work/stage3/b3/` and its parents as directories.
- The writer session's scratchpad `/private/tmp/claude-501/-Users-aravind--claude-spares-spare-fX1wGD/2c281827-…/scratchpad`, with `build_controls.py` and `validate_controls.py`, and the same two names again as `$VAR`-relative fragments (`/build_controls.py`, `/validate_controls.py`). These are the session's own temporary scripts.

**Reading.** No tool call in either transcript touches anything outside the controls folder and the writer session's own scratchpad. Nothing in the repository, nothing in the candidates session's or GLM's folders, no memory file. Inside the folder, the tool calls name the spec, the rubric, the day-0 text, the writer record and the directories; neither transcript's tool calls name `routine-reference-b3.json` or `payloads-b3-candidates.json`. `controls-b3.json` was written by the session's scratch script, as the tool calls name no direct write to it. What that script read cannot be seen from tool calls, and the script was not opened.
