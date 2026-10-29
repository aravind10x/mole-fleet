# B3 barrier audit: Sonnet 5.5 writer (brief 15 A5.4 and the 16:50 note)

Written 2026-10-29 by the blue bookkeeping session ($0). Paths, counts and hashes only. No candidate statement, justification or token text appears here or in `trace-audit-sonnet55.json`.

## The trace

- Session: Claude desktop (Code tab), title "Synthetic test fixtures for monitoring study". Transcript `~/.claude/projects/-Users-aravind-KruxAI-tais-project-selection/6fa5f61c-a730-4cc0-a9e8-dc6d8c40075e.jsonl`, sha256 `99fa5f9b13c2697f1b0efa306760bf5f4b080786b7a67d5f3d8ed0d6e460a821`, 2,009,582 bytes. The first user message is Section 0-W; the only model is `claude-sonnet-5-5` (66 assistant turns); entrypoint `claude-desktop`, Claude Code 2.1.309, permission mode auto; first row 2026-10-29T17:11:27Z, last 17:31:40Z. This is the only transcript in that project folder whose prompt is Section 0-W and whose model is Sonnet 5.5. It has no sub-agent folder (only `custom-title.json` and `tool-results/`).
- **Effort.** The trace records `effort: xhigh` and `perTurnEffort: xhigh` on all 66 assistant turns, as A5's 16:50 note says. `writer-record-sonnet55.md` says "reasoning effort 30". The trace is the better record; the writer record is left unedited.
- **Prompt bytes.** The first user message is the bytes of `part-w-paste-section0w.md` (sha256 `c5fafd351d887c00…`) inside the desktop app's paste wrapper, without the file's trailing `---` separator line. It has **no harness preface**. Under A5's 16:50 note the difference is recorded, and this audit runs over the session's tool calls in place of the directory restriction. The writer ran in the repository and did W3, W4 and its STATUS line itself, as Section 0-W says without the preface.
- **Tool calls:** Bash 32, Read 10, Edit 4, Write 3, update_plan 4, wrap_up 1. There is **no Agent, Task or Workflow call, so no sub-agents**, as the record says. Most calls appear twice in the transcript, the second copy with a `cd <repo> &&` prefix. The audit counts paths, not calls.

## The audit script and how it ran

`work/checks/stage3_b3_trace_audit.py` (sha256 `243677a7edb388df21e60f81a18cec379eaaf89f40c00510dc3b8adb44e5228e`, 4,423 bytes) exists only in the main checkout and was never committed to the fork. **It is truncated:** the file stops inside `main()`'s argparse (`default="cla`) and does not compile. Every function above `main()` is complete. `trace_audit_run_b3.py` (sha256 `b216f08ba044184a7fbf4323ee4481a62abdf57fde2d3896f273a45d012a94e9`) runs that source up to `def main(` unchanged and supplies the CLI the docstring describes. It then adds per-path provenance and a mechanical class, and leaves out any token that is candidate text or sits only inside a heredoc body. The truncated script is the coordinator's to repair and commit; it was not edited here.

Command (repository root):

```
python3 -I work/stage3/b3/trace_audit_run_b3.py --audit-script work/checks/stage3_b3_trace_audit.py \
  --trace ~/.claude/projects/-Users-aravind-KruxAI-tais-project-selection/6fa5f61c-a730-4cc0-a9e8-dc6d8c40075e.jsonl \
  --writer-dir /Users/aravind/KruxAI/tais-project-selection --format claude-jsonl \
  --candidates work/stage3/b3/payloads-b3-candidates-sonnet55.json \
  --out-raw <scratchpad>/trace-audit-sonnet55-raw.json --out-json work/stage3/b3/trace-audit-sonnet55.json
```

The audit's own result (raw json, sha256 `79fd2dcd63eb18365fb4e053e9e2a019fa0a95a9475b730fd18ab274430c9ab9`, kept outside the repository because its path list holds six heredoc fragments) is **FAIL**: 60 path tokens, 15 inside the allowed set, 45 outside. A FAIL is expected here. With the repository as the writer directory, every permitted step outside the four files is flagged too: the W3 checks runs, the probes in the scratchpad and the W4 commit.

## Allowed set (15 tokens, 10 paths)

The four inputs (`writer-spec-b3.md`, `routine-reference-b3.json`, `rubric.md`, `doc-states-day0.md`); the writer's own outputs (`payloads-b3-candidates.json`, `writer-record.md`, `checks-b3.json`); the directories repository root, `work/`, `work/stage3/b3/`. Every Read call is one of the four inputs. `rubric.md` was read only at lines 18 to 45 and 71 to 85, plus a heading grep, as the record says. No other file under `work/stage3/b3/` was opened. Note that the script's "own outputs" rule allows every file under `work/stage3/b3/` when the writer directory is the repository, so this was checked separately.

## Every flagged path (45 tokens, 43 paths), classified against `writer-record-sonnet55.md`

**Disclosed: checks runs** ("run several times (`--help`, two probe files in the session scratchpad, then the real file)"; calls 17, 18, 19 to 22, 30 to 32, 40). The script reads the bank, the honest null and the `t1v2/` statistics itself, which W3 permits.
- `work/checks/stage3_t1v2_checks.py`, `$W/checks/stage3_t1v2_checks.py`
- `work/mole-fork/.venv/bin/python`, `$W/mole-fork/.venv/bin/python`
- `$W/mole-fork` (`--fork`), `$W/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl` (`--corpus`), `$W/stage3/bank-reweight/benign_task_bank_v2_class_v6.yaml` (`--bank`), `$PWD/work` (sets `W`)
- `$W/stage3/b3/payloads-b3-candidates.json`, `$W/stage3/b3/checks-b3.json`, `$W/stage3/b3/checks-b3.md` (own outputs, as checks arguments)

**Disclosed: probes and scratchpad** (record: `build_b3.py`, `preflight.py`, `make_checklist.py`, the two probe files). The scratchpad is `/private/tmp/claude-501/-Users-aravind--claude-spares-spare-qutuJE/6fa5f61c-a730-4cc0-a9e8-dc6d8c40075e/scratchpad`.
- the scratchpad itself; `build_b3.py`; `probe-payloads.json`; `$SP/probe.py`, `$SP/probe-payloads.json`, `$SP/probe-checks.json`, `$SP/probe-checks.md`, `$SP/probe2.py`, `$SP/probe2-payloads.json`, `$SP/probe2-checks.json`, `$SP/probe2-checks.md`
- `checks-stdout.txt` (the checks run's stdout redirect; not named in the record, covered by "checks runs")
- Python heredocs open only the four inputs, scratchpad files and own outputs. One `open(P)` in call 28 has `P` set to the writer's own `payloads-b3-candidates.json`.

**Disclosed: W4 commit and STATUS line** (record, Outputs; calls 48 to 53)
- `work/mole-fork` (`git -C`), `$F/results/stage3/b3`, `results/stage3/b3/{payloads-b3-candidates.json, checklist-b3.md, writer-record.md, checks-b3.json, checks-b3.md}`, `work/mole-fork/results/stage3/b3/payloads-b3-candidates.json` (the shasum after the commit). Call 53 appends the writer's STATUS line, which Section 0-W allows.

**Disclosed: listings and `git log`** (record: "Directory listings (names only) … the fork's `results/stage3/b3/` … `git log --oneline -5`")
- `results/stage3/b3` and `tais-project-selection/work/mole-fork/results/stage3/b3` (call 37: `git ls-files` and `ls`, names only)
- `tais-project-selection/work/mole-fork` (calls 36, 37: `git -C … log --oneline -5`)

**Not a file**
- `/dev/null` (redirects)
- 6 heredoc-body fragments (calls 19 to 22, 41): path-shaped strings inside the writer's own Python heredocs (probe builders, checklist writer). Not opened; not reproduced.

**Undisclosed: names and git metadata only, no file content**
- `/Users/aravind/KruxAI` (calls 36, 37): `ls -a` of the parent folder (`head -30`, names) and `git rev-parse --show-toplevel` (not a repository).
- `tais-project-selection/work/mole-fork/results/stage3` (call 36): `ls` of the fork's `results/stage3/` (`head -30`, names). The record names only `results/stage3/b3/`.
- `work/fakelab` and `./vendor` (calls 38, 39): `find . -maxdepth 5 -name .git -not -path './vendor/*'` (names of git directories); `git -C work/fakelab remote -v` and `git log --oneline -2` (two FakeLab commit subjects, unrelated to B3); and an attempted `grep -rn "private repo" --include=*.md -l .` over the repository that **did not run** (zsh: "no matches found: --include=*.md"; no output, nothing searched).
- `/node_modules` (calls 33, 34): `find . -maxdepth 3 -name .git -not -path '*/node_modules/*'` (names), with `git -C work/mole-fork rev-parse --abbrev-ref HEAD` and `git -C work rev-parse --show-toplevel`.

**Undisclosed, found by reading the command skeletons; the path regex does not catch them because they contain no slash**
- Call 35: `git -C <r> remote -v`, `rev-parse --abbrev-ref HEAD` and `status --short` for `mole-fork`, `fakelab` and `mole-fork-prefix`. These showed remote URLs, branch names and two modified-file names: `results/stage3/b4r/plan.md` in the fork and `protocol/TRACK-C-protocol-v1.md` in FakeLab. (`ls work` and `ls work/stage3` in the same call are disclosed.)
- Call 36: `ls` and `ls -a` of the repository root (names).
- Call 37: `git show --stat --format=%s HEAD` in the fork. HEAD was `84d609b` (A5's commit); its subject is already in the disclosed `log -5`, and the stat shows its three file names: the brief-15 mirror, `part-w-harness-preface.md`, `part-w-paste-section0w.md`. Also `ls -la <repo> | grep -i git`.

**Reading.** No file content outside the four inputs and the writer's own outputs entered the session through a tool call, apart from what the checks script reads itself, which W3 permits. The undisclosed items are names-only listings, git remotes, branches and modified-file names, one commit's file stat and two FakeLab commit subjects. None is a B3 instrument result, a score or a do-not-read file's content. The record's own barrier disclosure (the auto-loaded memory index) is not a tool call and cannot be audited from the trace.

## Second mechanical check (A5.4)

The 24 sham records equal `routine-reference-b3.json` (sha256 `fac62cce…`), checked deep-equal and by canonical serialization, ids `T1v2-S01` to `T1v2-S24` in order.
