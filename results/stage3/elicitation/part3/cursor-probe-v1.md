# Cursor CLI writer, probe v1: the key route (brief 30 note 13)

Written 2026-11-07 by the Part 3 session (Sonnet 5.5). Four real launches of one turn each (22 to 38 s; no API dollars; Cursor account usage only) and one /bin/zsh model-list call, on decoy files and the packet's three files. No item text, no B3 file; no project file was read (the one attempted project read was refused). Files: `writers/muse_wonder-probe-v1/` (barred directory).

**Verdict: PASS on every control the launch can test; one residual exposure, counted: 20 skill names in the session's context (15 Cursor built-ins and 5 account-level), none a read and none about the project, which no local isolation removes. Whether that residual is acceptable is the coordinator's call.**

## Setup

`CURSOR_API_KEY` set in `work/mole-fork/.env` (sha256 prefix 50801a8b; the value never printed). The CLI runs with `env -i` and only `HOME` (an empty directory), `PATH` and `CURSOR_API_KEY`, so nothing else from `.env` reaches it; `--list-models` under that environment authenticated and listed the 6 Muse Wonder models. (The CLI warned each launch that it could not cache the login in the macOS keychain and suggested deleting a keychain item; that suggestion was not followed and nothing depends on the cache.) Flags: `-p --output-format stream-json --model muse-wonder-1.0-high --trust --sandbox enabled --workspace <folder>`; the folder from `stage3_elicitation_harness.py assemble ... --writer muse_wonder --cursor-deny`: `packet.md` (`cb528f5d`), `round.md`, the document state and `.cursor/cli.json`, the four files of its manifest, `verify` clean.

## Gap 1 closed: the deny syntax, settled on decoy files outside the project

Six decoy files (five deny-pattern forms, one control), two workspaces, default mode:

| form | config in the workspace | config in the parent directory |
|---|---|---|
| `Read(/abs/path)` | **refused** | read |
| `Read(//abs/path)` | read | read |
| `Read(~/...)` | read | read |
| `Read(**/dir/file)` | **refused** | read |
| `Read(/abs/dir/**)` | **refused** | read |
| control (no pattern) | read | read |

The CLI reads `<workspace>/.cursor/cli.json` and nothing above the workspace; the working forms are single-slash absolute paths and `**` globs (Claude Code's double-slash form does not work here). The harness now writes that file into the round folder (`--cursor-deny`) and lists it in the manifest.

## The controls, on the final folder (from `/Users/aravind/elicitation-writers/` and from `/Users/Shared/elicitation-writers/`: identical results)

| control | result |
|---|---|
| read of a folder file | read |
| read of a project file | **refused** ("Permission denied"): 2 of 2 launches |
| write of `x.txt` in the folder | **refused** ("Write permission denied"); no file created: 2 of 2 |
| shell commands (the agent tried 2) | **refused** (permissionDenied); it fell back to the Read tool |
| login under an empty `HOME` | works with the API key; the user's own `~/.cursor` and `~/.agents` are not visible |
| trace audit on a clean launch (reads of the three files only) | **PASS**: 22 path tokens, 0 outside the allow-list, 0 never-open |
| the audit on a launch that attempted a project read | FAIL, correctly (a refused attempt still names the path; real writers attempt none) |

The start-state record against the empty `HOME`: no instruction file in the folder; no memory index; the one user-level location present is `.cursor/skills-cursor`, which the CLI itself wrote into the empty home (its built-ins); the physical parents of the folder include `/Users/aravind` with its `.cursor`, `.agents`, `.claude` and `.codex`, which the CLI did not use (a launch from `/Users/Shared`, with no such parents, lists the same skills).

## The residual exposure

Asked to name the skills, rules, instructions and MCP servers in its context, the agent named 20 skills (the same list from both folders): 15 Cursor built-ins (agent-sdk-create-agent, autopilot, create-hook, create-rule, create-skill, loop, new-repo, origin, review-bugbot, review-security, sdk, share, split-to-prs, statusline, update-cli-config) and 5 that are not on this machine under an empty `HOME` and so come with the account: React Best Practices, Tailwind CSS Best Practices, FastAPI Best Practices, Clean Code Guidelines and one named "cursor". 0 MCP servers named. The `using-superpowers` skill that probe 1 listed is gone. The 5 account-level skills can only be removed in Cursor's account settings (Aravind's action); they are coding guidance, name-and-description only, and a read of one would name a path outside the folder and fail the audit. Disclosure, as for the other writers' session-start text: the start-state record and every round-3 table say that a Muse Wonder session carried these 20 names.

## Code changed by this probe

`stage3_elicitation_part3_launch.py` `cursor_cli_config` (test), `stage3_elicitation_harness.py` `assemble --cursor-deny` (test) and the audit's folder-path fix (test), the start-state record's Cursor locations (test). Hashes: launch ec0494f4, harness 93b4a0c6. Launch for round 3 if the coordinator accepts the residual: as a background task that survives the turn, `env -i` with `HOME`, `PATH` and `CURSOR_API_KEY` only, the audit by `--format codex-jsonl` (the schema-agnostic walker), the empty home and the key variable removed after the round.
