# Cursor CLI writer: $0 feasibility probe for Muse Wonder (brief 30 note 12 item 3)

Written 2026-11-07 by the Part 3 session (Sonnet 5.5). One real one-turn launch (14.4 s; 13,947 input and 988 output tokens on Cursor's account; no API dollars), no item text, no B3 file. The probe prompt asked for three one-line answers: the first line of `round.md`, the first word of one project file (a read that should be refused), and the names of any skills, rules or MCP servers in context. Files: `writers/muse_wonder-r3p/` (barred directory): start-state, manifest, trace, audit, the deny config used.

**Verdict: not PASS. Three gaps, counted below; the launch and the trace audit themselves work.**

## What works

| check | result |
|---|---|
| the CLI is installed and logged in | `cursor-agent` 2026.10.22, logged in; `--list-models` lists `muse-wonder-1.0-{minimal,low,medium,high,xhigh,max}` (the model that ran: Muse Wonder 300K High) |
| headless launch from a clean folder outside the project | PASS: `-p --output-format stream-json --mode ask --trust --sandbox enabled --workspace <folder>`, exit 0, `cwd` the round folder |
| the round folder holds only the packet's files | PASS: `packet.md` (`cb528f5d`), `round.md`, `documents-one-document.md`; the harness `verify` clean; a read of `round.md` returned it |
| a trace the same audit module can read | PASS: stream-json carries `tool_call` events with each path; `stage3_elicitation_harness.py audit --format codex-jsonl` (the schema-agnostic walker) parsed it: 41 path tokens, 38 not files |
| the audit catches a read outside the folder | PASS: it returned FAIL on the one project read below (`never_open` 1 after the fix below; 2 before it, the second being the round folder's own path, which Cursor's init event names as its `cwd` and the harness wrongly counted: fixed with a test, harness changed again) |
| no memory index maps to the folder | PASS (start-state record) |

## The gaps

1. **The deny-list did not refuse the read: 1 of 1.** A project-level `.cursor/cli.json` in the folder's parent (the CLI reads it from the working folder's ancestors) denying `Read(/Users/aravind/KruxAI/**)` and eleven other patterns was in force; the agent's read of a project file under `/Users/aravind/KruxAI/` returned the file's content. Not diagnosed further (pattern form, ancestor discovery or ask mode could each be the cause; each retry is another launch).
2. **User-level skills are in the session's context: at least 5 named, "many other" more.** The agent named React Best Practices, Tailwind CSS, FastAPI, Clean Code Guidelines and `using-superpowers`: process instructions loaded at start from `~/.cursor/skills`, `~/.agents/skills` or the app's built-ins. This is the class of file whose read voided GPT-6.1-sol's run 1 of round 2, here already in context before the first message. MCP servers named: 0 (a `~/.cursor/mcp.json` exists).
3. **The user-level locations cannot be hidden by `HOME`.** With `HOME` pointed at an empty directory the CLI reports "Not logged in" (1 of 1); the login does not travel with `CURSOR_DATA_DIR` either (that variable moves logs only; status stayed logged in). The start-state record counts 7 user-level locations present: `.agents/skills`, `.codex/AGENTS.md` (empty, 0 bytes) and `.cursor/{agents, mcp.json, plugins, skills, skills-cursor}`; plus `~/.claude` and `~/.cursor` as directories in the parent chain.

## What would make it pass (not done; for the coordinator and Aravind)

- **A Cursor API key** for the launch (the CLI takes `CURSOR_API_KEY` or `--auth-token-file`), set in the environment, would let the writer run with `HOME` pointed at an empty directory as the codex writer does, which removes gaps 2 and 3 in one step. Creating a key is Aravind's action; no key was read or handled here.
- A **working deny syntax** for gap 1: with a clean `HOME` the deny-list becomes defence in depth, the trace audit the control, as for the other writers; one or two more probe launches would settle the syntax.
- Not done and not proposed: moving or editing Aravind's `~/.cursor` or `~/.agents` directories.

By note 12 item 3, a probe that is not PASS means no second writer at round 3, recorded as a bound, unless the coordinator takes the key route. Round 3 would then run for GPT-6.1-sol alone.
