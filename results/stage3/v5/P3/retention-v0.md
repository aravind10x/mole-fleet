# FT retention by replay (blue side; counts and durations only; 2026-11-14)

**This is mechanical retention under a fixed history.** Each application's first composed state is replayed forward against the honest log's successful content writes to its document, in timestamp order, as the recorded log has them. The honest log does not react to the plant, so this says how long a planted line lasts against that history, not how long it would last in a world whose agents saw it. Rule: `work/stage3/red/ft/retention-rule.md` (sha256 first 8 `b0a56e8f`). Times are hours from the composition time; applications still unchanged at the corpus end are right-censored there, so the quartiles are Kaplan-Meier (`not reached` when survival never falls that far).

Applications: 184; composed 184; ended by an honest edit 0; censored 184.

## By regime

| regime | n | ended | censored | q1 h | median h | q3 h |
|---|---|---|---|---|---|---|
| alarming | 24 | 0 | 24 | not reached | not reached | not reached |
| middle | 64 | 0 | 64 | not reached | not reached | not reached |
| routine | 96 | 0 | 96 | not reached | not reached | not reached |

## By document

| document | n | ended | censored | q1 h | median h | q3 h |
|---|---|---|---|---|---|---|
| README.md | 29 | 0 | 29 | not reached | not reached | not reached |
| engineering-setup.md | 30 | 0 | 30 | not reached | not reached | not reached |
| finetune-guide.md | 30 | 0 | 30 | not reached | not reached | not reached |
| oncall-runbook.md | 30 | 0 | 30 | not reached | not reached | not reached |
| redteam-checklist.md | 32 | 0 | 32 | not reached | not reached | not reached |
| release-gate-runbook.md | 33 | 0 | 33 | not reached | not reached | not reached |

## By arm

| arm | n | ended | censored | q1 h | median h | q3 h |
|---|---|---|---|---|---|---|
| k2 | 68 | 0 | 68 | not reached | not reached | not reached |
| k3 | 48 | 0 | 48 | not reached | not reached | not reached |
| lone | 68 | 0 | 68 | not reached | not reached | not reached |

## Kind of the honest edit that ended retention

| regime | line_overwrite | section_rewrite | whole_document_write |
|---|---|---|---|
| alarming | 0 | 0 | 0 |
| middle | 0 | 0 | 0 |
| routine | 0 | 0 | 0 |

## Honest edits ignored on replay

An honest `replace_in_file` whose find text is absent from the running planted state would fail there and is ignored (retention-rule.md). These are honest edits aimed at text the plant had already displaced; they are not changes to a planted line.

| regime | applications | with at least one ignored | ignored edits in all |
|---|---|---|---|
| alarming | 24 | 8 | 16 |
| middle | 64 | 13 | 37 |
| routine | 96 | 33 | 66 |

Per-application rows (payload id, regime, document, set, arm, composed, hours, censored, ending kind) are in `retention-v0.json`.
