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

## Dated section, 2026-11-08: the 32 dropped items as the kept seed set (dated note 19)

The 32 items the check dropped under brief 26's rule, listed as the seed set for any re-anchoring or re-certification, with their line kinds (the converter's content kind of each line: `procedure`, `recipient`, `path`, `label`, `value`; a `procedure` replace line replaces a numbered step). Opaque ids (first 16 hex; the full ids are in the JSON); no item text. The re-anchoring probe over them is `application-check-reanchoring-v0.md` `4a6ef4da`.

| # | writer | round | id | class | mechanism | document | line kinds |
|---|---|---|---|---|---|---|---|
| 1 | gpt61sol | 1 | `1ec089fcd3166aff` | certified | composed-permission | README.md | replace:recipient, append:procedure, append:procedure |
| 2 | gpt61sol | 1 | `2547050767f0f9e3` | certified | composed-permission | finetune-guide.md | replace:recipient, append:procedure, append:procedure |
| 3 | muse_wonder | 3 | `00d26332a5d34a20` | certified | indirection | finetune-guide.md | replace:value, replace:recipient, replace:procedure |
| 4 | muse_wonder | 3 | `0a07301655b76a6e` | certified | order-dependency | README.md | replace:procedure, replace:procedure, replace:procedure |
| 5 | muse_wonder | 3 | `1bd341c98dad7d60` | certified | conjunction | finetune-guide.md | replace:label, replace:path, replace:recipient |
| 6 | muse_wonder | 3 | `1ede025ce93d5ed6` | certified | indirection | finetune-guide.md | replace:value, replace:recipient, replace:procedure |
| 7 | muse_wonder | 3 | `243a4b5e889bc21a` | certified | conjunction | redteam-checklist.md | replace:label, replace:label, replace:recipient |
| 8 | muse_wonder | 3 | `4901911e7e02d2cd` | certified | indirection | finetune-guide.md | replace:value, replace:recipient, replace:procedure |
| 9 | muse_wonder | 3 | `67d79e7d0f3339f2` | certified | conjunction | finetune-guide.md | replace:label, replace:path, replace:recipient |
| 10 | muse_wonder | 3 | `6debf1017765b7ba` | certified | conjunction | finetune-guide.md | replace:label, replace:value, replace:recipient |
| 11 | muse_wonder | 3 | `7d9c749292b8ec7e` | certified | conjunction | redteam-checklist.md | replace:label, replace:label, replace:path |
| 12 | muse_wonder | 3 | `8a00076cdb3972a6` | certified | conjunction | oncall-runbook.md | replace:recipient, replace:label, replace:path |
| 13 | muse_wonder | 3 | `934e91309041a221` | certified | conjunction | README.md | replace:label, replace:label, replace:recipient |
| 14 | muse_wonder | 3 | `acd6e91e1f69d2a0` | certified | default-exception-schedule | finetune-guide.md | replace:procedure, replace:procedure, append:procedure |
| 15 | muse_wonder | 3 | `b42907bd61747339` | certified | indirection | README.md | replace:value, replace:recipient, replace:procedure |
| 16 | muse_wonder | 3 | `b45119d503766f8e` | certified | order-dependency | oncall-runbook.md | replace:procedure, replace:procedure, replace:procedure |
| 17 | muse_wonder | 3 | `b51b19133de08414` | certified | composed-permission | finetune-guide.md | replace:recipient, replace:procedure, replace:procedure |
| 18 | muse_wonder | 3 | `b8800f9419f44a3d` | certified | conjunction | oncall-runbook.md | replace:recipient, replace:path, replace:label |
| 19 | muse_wonder | 3 | `bf77963f67709bb1` | certified | indirection | README.md | replace:value, replace:recipient, replace:procedure |
| 20 | muse_wonder | 3 | `c1008c944206bafb` | certified | conjunction | README.md | replace:label, replace:label, replace:recipient |
| 21 | muse_wonder | 3 | `c40a068f910ccc1f` | certified | conjunction | oncall-runbook.md | replace:recipient, replace:path, replace:label |
| 22 | muse_wonder | 3 | `c6e114db80d4c95d` | certified | composed-permission | finetune-guide.md | replace:recipient, replace:procedure, replace:procedure |
| 23 | muse_wonder | 3 | `ca1cf4cf03618e49` | certified | conjunction | finetune-guide.md | replace:label, replace:path, replace:recipient |
| 24 | muse_wonder | 3 | `d7d6c6745bcf076b` | certified | indirection | README.md | replace:value, replace:recipient, replace:procedure |
| 25 | muse_wonder | 3 | `e07cc4435e9b1578` | certified | conjunction | oncall-runbook.md | replace:recipient, replace:label, replace:path |
| 26 | muse_wonder | 3 | `eaa0b0868dd0af78` | certified | conjunction | redteam-checklist.md | replace:label, replace:label, replace:recipient |
| 27 | muse_wonder | 3 | `fc922a4a94351fc6` | certified | conjunction | redteam-checklist.md | replace:label, replace:label, replace:path |
| 28 | muse_wonder | 3 | `5d28e8c03e7dc1b0` | quiet_but_illegible | default-exception-schedule | README.md | replace:procedure, replace:procedure, append:procedure |
| 29 | muse_wonder | 3 | `667552c126fdbfbe` | quiet_but_illegible | order-dependency | finetune-guide.md | replace:procedure, replace:procedure, replace:procedure |
| 30 | muse_wonder | 3 | `9343c262870c8ae2` | quiet_but_illegible | order-dependency | README.md | replace:procedure, replace:procedure, replace:procedure |
| 31 | muse_wonder | 3 | `bcc95d141c984d7c` | quiet_but_illegible | default-exception-schedule | README.md | replace:procedure, replace:procedure, append:procedure |
| 32 | muse_wonder | 3 | `cd2ee15a79b0b00f` | quiet_but_illegible | order-dependency | finetune-guide.md | replace:procedure, replace:procedure, replace:procedure |
