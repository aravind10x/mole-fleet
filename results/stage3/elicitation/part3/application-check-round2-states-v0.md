# Edit-application check of the certified and quiet-but-illegible items, against the states round 2 uses (brief 30 Part 3)

Written 2026-11-08T03:28:53+05:30 by the Part 3 session (Sonnet 5.5, Claude Code desktop app). $0, no API call, no reader. Counts, ids, reason codes and honest account names only; no item line, anchor, region, declared effect or document text is in this file or its JSON (a guard refuses to write one). No B3 file was opened: brief 26's script is imported for its draw machinery and none of its loaders is called. STATUS.md was not read.

## What was run

Module: `stage3_elicitation_application.py` `5d6beb5d` over brief 26's `stage3_b3_inserter_dry_run.py` `999cb737` and the application module `stage3_t1.py` `240f4ed9` (Inserter class `24d3d147`, equal to the t1v3 manifest: True). States: the null corpus `work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl` `ffc1f6cd` rebuilt in memory (equal to brief 26's and t1v3's: True), bank days 2026-04-06, 2026-04-07, 2026-04-08, the lone layout's draw days 2026-04-06, 2026-04-07; day-0 snapshot `bade5fab`. Items: 116 (certified and quiet-but-illegible of every writer round that has a record), 1728 item draws and 5283 lone-line draws, 18817 module runs.

**The rule (brief 26's, unchanged).** An item needs two valid placements on different days by different authors; each of its three lines, as a lone line, needs two valid draws by different authors. An item short of either leaves both arms. The literal count (two valid draws, any days and authors) is beside. **Beside it, for round 2's plan (brief 33 note 5):** the same rule on the draws that break no later honest edit ("clean" draws: none of the draw's module runs broke one).

## Result by writer, round and class

| writer | round | class | items | dropped (rule) | dropped (literal) | dropped (clean rule) | kept |
|---|---|---|---|---|---|---|---|
| gpt61sol | 1 | certified | 2 | 2 | 2 | 2 | 0 |
| gpt61sol | 2 | certified | 30 | 0 | 0 | 0 | 30 |
| gpt61sol | 3 | certified | 47 | 0 | 0 | 0 | 47 |
| muse_wonder | 3 | certified | 30 | 25 | 21 | 30 | 5 |
| muse_wonder | 3 | quiet_but_illegible | 7 | 5 | 5 | 5 | 2 |

**Totals:** 116 items; dropped by the rule 32; by the literal count 28; by the clean rule 37. Day-0 joint check passes for 116 of 116; every line found at day 0 in 116 of 116.

## The matching statistic before and after the drops

| | n_c matched | n_i matched | matched effective n | certified total | illegible total | strata with both arms |
|---|---|---|---|---|---|---|
| all items | 7 | 5 | 5.83 | 109 | 7 | 3 |
| after the rule's drops | 0 | 0 | 0.00 | 82 | 2 | 0 |
| after the clean rule's drops | 0 | 0 | 0.00 | 77 | 2 | 0 |

## Why items were dropped (first-named reason of each short placement)

- lone line: other: no author the module can draw (no session in which every target resolves): 77
- item: other: no author the module can draw (no session in which every target resolves): 28
- item: target found more than once: 4

## Where the drops are (counts)

**By the pattern of operations in the item:**

| writer | operations | items | dropped (rule) | dropped (clean rule) |
|---|---|---|---|---|
| gpt61sol | 2 append + 1 replace | 2 | 2 | 2 |
| gpt61sol | 3 append | 77 | 0 | 0 |
| muse_wonder | 1 append + 2 replace | 3 | 3 | 3 |
| muse_wonder | 3 replace | 34 | 27 | 32 |

**By mechanism:**

| writer | mechanism | items | dropped (rule) | dropped (clean rule) |
|---|---|---|---|---|
| gpt61sol | composed-permission | 31 | 2 | 2 |
| gpt61sol | default-exception-schedule | 38 | 0 | 0 |
| gpt61sol | indirection | 10 | 0 | 0 |
| muse_wonder | composed-permission | 2 | 2 | 2 |
| muse_wonder | conjunction | 19 | 14 | 19 |
| muse_wonder | default-exception-schedule | 3 | 3 | 3 |
| muse_wonder | indirection | 6 | 6 | 6 |
| muse_wonder | order-dependency | 7 | 5 | 5 |

**By document:**

| writer | document | items | dropped (rule) | dropped (clean rule) |
|---|---|---|---|---|
| gpt61sol | README.md | 19 | 1 | 1 |
| gpt61sol | engineering-setup.md | 13 | 0 | 0 |
| gpt61sol | finetune-guide.md | 14 | 1 | 1 |
| gpt61sol | oncall-runbook.md | 13 | 0 | 0 |
| gpt61sol | redteam-checklist.md | 9 | 0 | 0 |
| gpt61sol | release-gate-runbook.md | 11 | 0 | 0 |
| muse_wonder | README.md | 9 | 9 | 9 |
| muse_wonder | engineering-setup.md | 3 | 0 | 3 |
| muse_wonder | finetune-guide.md | 12 | 12 | 12 |
| muse_wonder | oncall-runbook.md | 5 | 5 | 5 |
| muse_wonder | redteam-checklist.md | 6 | 4 | 4 |
| muse_wonder | release-gate-runbook.md | 2 | 0 | 2 |

**Lone lines with no author the module can draw, by operation:**

| writer | operation | lines | no author |
|---|---|---|---|
| gpt61sol | append | 235 | 0 |
| gpt61sol | replace | 2 | 2 |
| muse_wonder | append | 3 | 0 |
| muse_wonder | replace | 108 | 75 |

## Draws

Item draws: 1728 drawable, 1539 valid, of which 1428 clean (111 valid but breaking a later honest edit). Lone-line draws: 5283 drawable, 5114 valid, of which 4773 clean (341 valid but breaking a later honest edit). Largest number of honest edits broken by one draw: 10.

## Reproduce

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_application.py run
```
