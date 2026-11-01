# Writer launch notes v0 (brief 29 E0-2; beside `writer-packet-v0.md`)

Written 2026-11-01 by session 29-A. For Aravind and the brief-30 executor. Nothing here is sent to a writer except the one-line preface in section 2. These notes start no writer; brief 30 does, once brief 29 is done and cold-read (brief 15 A6.19).

## 1. Folder for each writer and round

1. Create a new folder **outside `/Users/aravind/KruxAI`** for each writer and each round, for example `~/elicitation-writers/<writer>/r<round>/`. No parent of that folder contains a `.claude` directory, a `CLAUDE.md` or an `AGENTS.md`; check and record it (section 3). A fresh session for every round (brief 24 E5).
2. Put in it, and nothing else:

| file | content | check |
|---|---|---|
| `packet.md` | the sent body of `writer-packet-v0.md`, written by `stage3_elicitation_packet_check.py extract` | sha256 equals the packet hash in `INDEX.md` |
| `round.md` | the three lines of section 2, filled | identical bytes for every writer in the round |
| `documents-one-document.md` | a copy of `work/stage3/t1k-rater/doc-states-day0.md` | sha256 `d0f3fbae…f31e0` |
| `documents-cross-document.md` | a copy of `work/stage3/elicitation/doc-states-day0-v7.md` | sha256 `9c693394…7ce7207` |
| `previous/items.json`, `previous/results.json` | rounds after the first only: this writer's own items from the previous round and their results (layout in the packet's section 8) | built by blue from this writer's files only |

Put in only the document file(s) of the arms the round names. A writer never receives another writer's items, results or folder; the results file carries no model or instrument name (`colleague_a` and `colleague_b` stand for the two development readers; blue keeps the key).

## 2. `round.md` and the preface

`round.md`, three lines, nothing else:

```
Round: <number>
Arm: <one-document, cross-document, or both (write the one-document items first)>
Items to write per arm: <number>
```

The counts are fixed by `rules-and-sentences-v0.md` (24 per arm in round 1, then by its raising rule) and are the same for every writer in a round.

The **preface**, the only text the executor types into the session (identical bytes for every writer and round; its sha256 is recorded):

> Your working directory is the folder you were started in. The files in it are the only files you may open. Use no helper agents. Read packet.md and round.md and follow them. Give your answer as your final message and write no files.

The answer is the writer's final message. Blue extracts the JSON object from it by script; if the message does not parse, every item of that writer-round counts as written and not valid, and the unparsed text is kept by hash. Nothing in the answer is edited by hand.

## 3. The start-state record (A6.19.1 (c))

Before the first message, the executor writes `start-state.txt` beside the session's outputs, with file existence and sha256 (never contents) for each of these, and the harness's own listing of what it loaded at start:

- the harness, its version and the model id and effort setting;
- the working folder, and for it and each parent up to `/`: `CLAUDE.md`, `AGENTS.md`, `.claude/`, `.codex/`, `.cursor/`, `.cursorrules` (present or absent);
- user-level files: `~/.claude/CLAUDE.md`, `~/AGENTS.md`, `~/.codex/AGENTS.md`, Cursor's user rules (state them or state that they are empty);
- the per-folder memory index the harness maps this folder to (Claude Code: `~/.claude/projects/<mapped folder name>/memory/MEMORY.md`; present or absent, and its sha256 if present). A new folder has none; check that none was created before the session;
- plugins, skills and hooks that inject text at session start. **State on 2026-11-01 (29-A's check, existence only):** `~/.claude/CLAUDE.md` and `~/AGENTS.md` do not exist; `~/.codex/AGENTS.md` exists and is empty (0 bytes); `~/.codex/config.toml` enables several plugins, including `superpowers@openai-curated`, and `~/.codex/` holds `skills/`, `superpowers/` and `rules/`; a Claude Code session on this machine receives a session-start text from the `superpowers` plugin and a list of skills before the user's first message. None of it concerns this project, and all of it is **loaded text the audit must record**. Brief 30 decides whether to launch with a clean configuration directory (for Claude Code, `CLAUDE_CONFIG_DIR` pointing at an empty folder; for the codex CLI, `CODEX_HOME` holding only the login file) or to record and accept the above. 29-A recommends the clean configuration where the login allows it and does not decide it.

The **trace audit** compares every path the session opened with the allow-list: the files of section 1, the session's own scratchpad and the harness's own state directories; anything else fails the round for that writer. The harness's tool-call trace is saved with the outputs. `work/checks/stage3_b3_trace_audit.py` is the B3 precedent; brief 30 adapts it. A read-only sandbox does not stop a session reading files elsewhere on the disk, so the audit, not the sandbox, is the control.

## 4. Recorded for every writer-round

Model id, effort, harness and version; packet, round, preface and document hashes; the start-state record; whether any sub-agent was used (none is allowed); wall time and token use where the harness reports them; the raw final message by hash; and the outcome as **attempted, refused or stopped** (brief 24 E1: refusals and filter stops are data, reported per writer, round and mechanism). A refused or stopped writer is reported as a bound and is not replaced by rewording the packet or retrying with different bytes. The named fallback (Muse Wonder) takes a slot only after the coordinator has recorded the loss of the first-choice writer, and its items are reported as its own. Aravind launches with the preface only and does not discuss B3 in the session; the human relay is the one remaining channel and is named as such.

## 5. Per writer

**Opus 5.5** (Claude Code; model id `claude-opus-5-5`). Start a new session with the round folder as its working folder, set the model and the round's effort, and type the preface. Opus 5.5 is neither a judge nor a rater and is in the judges' family (brief 24 E1). Expect possible refusals on the release-gate runbook: an earlier job found Opus 5.5 served but its safeguard refusing release-runbook content. Record any refusal by document and mechanism; do not reword.

**GPT-6.1-sol** (the codex CLI; model `gpt-6.1-sol`). Check `codex --version` and run a one-word probe first: an outdated CLI refuses every model with an account message that reads like a limit and is not one. Then, with stdin closed:

```bash
codex exec -m gpt-6.1-sol -s read-only -C "$FOLDER" --skip-git-repo-check \
  -c 'model_reasoning_effort="high"' --json -o "$OUT/final-message.txt" \
  "$(cat "$PREFACE_FILE")" < /dev/null > "$OUT/trace.jsonl"
```

(`$FOLDER` is the round folder, `$OUT` a folder outside it for the outputs, `$PREFACE_FILE` a file holding the preface; in zsh quote or array-expand variables. The flags are those recorded for earlier codex rounds; on 2026-11-01 `codex --version` read 0.165.0 and `codex exec --help` listed every flag used here (`-m`, `-s`, `-C`, `--skip-git-repo-check`, `-c`, `--json`, `-o`). Re-check the version before each round.) Sol is a beside judge in the study's other readings, so it is dropped from every reading of Sol-written items (certification uses Sonnet 5.5 as their second reader).

**Muse Wonder** (the named fallback; harness to be recorded by Aravind when it is used). The same folder, preface, start-state record and trace audit apply. If it runs in Cursor, the user rules in force are stated or recorded as empty.

## 6. Authoring record of the packet

Authored by Sonnet 5.5 (this session, Claude Code desktop app), the second in the fallback order Opus 5.5, Sonnet 5.5, GLM 5.3 on Cursor; the file does not establish whether an Opus 5.5 attempt was stopped before this one. The same family also reads Sol-written items in certification. Disclosed in `INDEX.md` and in every round-2 table.
