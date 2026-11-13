# Realised use of each item in the honest log (`prefix_rw_v2c`, p3-use/v1)

Counts only; no document text. **This is realised use on this task bank, not need, and it is not to be multiplied by any uptake rate.** Blue side, $0, no model call, no planted file. v0 (`use-v0.*`, timestamp order) is untouched.

## What was counted

- **Order:** file order governs. It is the order the live world applied writes in; `P0/state-check-v0.md` (b9b8fce0) finds that on the six class documents file order reproduces all 492 read sizes and all 69 successful replaces, and simulated-timestamp order contradicts 173 reads and 9 replaces. Timestamp order is the labelled sensitivity at the end.
- **Unit:** a successful state-changing action by a session that is not the one that last wrote the slot.
- **Carries (any):** the slot's value as of the action (read through its locator) appears in the action's content by the validator's matching: the whole value, bounded, normalised, case-insensitive; or a distinctive token of it that the locator does not already carry.
- **Specific:** leaves out matches that rest only on a date, a bare number or a token under six characters.
- **Specific, no near-copies:** also leaves out any action whose content holds half or more of the current non-empty lines of the document it carries from (line share, by whitespace-normalised, case-insensitive substring).
- **Excluded, counted apart:** `edits` (a write to the slot's document that changes the slot), `copies` (a write of the whole document), `same_session` (the session that last wrote the slot).
- **Log:** 29,497 rows on 3 days (2026-04-06, 2026-04-07, 2026-04-08). Successful state-changing actions: **4,926**, of which 2,186 have content; **1,564** carry at least one slot (any), **944** specifically, **944** specifically and not as near-copies.

## Totals

| group | slots | never carried: any | never carried: specific | never carried: specific, no near-copies | slot-action pairs (units) | carrying | carrying, specific | carrying, specific, no near-copies | carrying, whole value | edits | copies | same session | slot-days carried | sessions carrying |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **all slots** | 296 | 94 (31.8%) | 136 (45.9%) | 136 (45.9%) | 830,205 | 27,137 | 6,572 | 6,572 | 3,400 | 225 | 35 | 2,251 | 368 / 888 | 275 |

### By document

| group | slots | never carried: any | never carried: specific | never carried: specific, no near-copies | slot-action pairs (units) | carrying | carrying, specific | carrying, specific, no near-copies | carrying, whole value | edits | copies | same session | slot-days carried | sessions carrying |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| README.md | 24 | 7 (29.2%) | 12 (50.0%) | 12 (50.0%) | 63,095 | 2,340 | 109 | 109 | 889 | 46 | 0 | 144 | 20 / 72 | 223 |
| release-gate-runbook.md | 69 | 17 (24.6%) | 22 (31.9%) | 22 (31.9%) | 191,713 | 6,884 | 3,737 | 3,737 | 801 | 34 | 0 | 751 | 86 / 207 | 263 |
| finetune-guide.md | 44 | 16 (36.4%) | 33 (75.0%) | 33 (75.0%) | 99,339 | 2,835 | 87 | 87 | 859 | 48 | 35 | 238 | 51 / 132 | 242 |
| redteam-checklist.md | 34 | 10 (29.4%) | 13 (38.2%) | 13 (38.2%) | 108,605 | 3,815 | 702 | 702 | 464 | 32 | 0 | 241 | 52 / 102 | 239 |
| oncall-runbook.md | 107 | 40 (37.4%) | 51 (47.7%) | 51 (47.7%) | 289,988 | 6,881 | 1,584 | 1,584 | 51 | 33 | 0 | 757 | 125 / 321 | 248 |
| engineering-setup.md | 18 | 4 (22.2%) | 5 (27.8%) | 5 (27.8%) | 77,465 | 4,382 | 353 | 353 | 336 | 32 | 0 | 120 | 34 / 54 | 248 |

### By slot kind

| group | slots | never carried: any | never carried: specific | never carried: specific, no near-copies | slot-action pairs (units) | carrying | carrying, specific | carrying, specific, no near-copies | carrying, whole value | edits | copies | same session | slot-days carried | sessions carrying |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| other | 136 | 36 (26.5%) | 58 (42.6%) | 58 (42.6%) | 358,501 | 18,529 | 4,722 | 4,722 | 2,741 | 129 | 16 | 1,423 | 182 / 408 | 274 |
| procedure_step | 60 | 30 (50.0%) | 30 (50.0%) | 30 (50.0%) | 228,361 | 2,887 | 1,031 | 1,031 | 16 | 33 | 4 | 295 | 67 / 180 | 260 |
| operational_value | 50 | 11 (22.0%) | 22 (44.0%) | 22 (44.0%) | 132,203 | 3,025 | 420 | 420 | 640 | 57 | 14 | 208 | 70 / 150 | 244 |
| label | 50 | 17 (34.0%) | 26 (52.0%) | 26 (52.0%) | 111,140 | 2,696 | 399 | 399 | 3 | 6 | 1 | 325 | 49 / 150 | 222 |

### By granularity

| group | slots | never carried: any | never carried: specific | never carried: specific, no near-copies | slot-action pairs (units) | carrying | carrying, specific | carrying, specific, no near-copies | carrying, whole value | edits | copies | same session | slot-days carried | sessions carrying |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| section | 62 | 17 (27.4%) | 20 (32.3%) | 20 (32.3%) | 182,662 | 10,459 | 2,829 | 2,829 | 31 | 120 | 11 | 752 | 88 / 186 | 272 |
| item | 234 | 77 (32.9%) | 116 (49.6%) | 116 (49.6%) | 647,543 | 16,678 | 3,743 | 3,743 | 3,369 | 105 | 24 | 1,499 | 280 / 702 | 275 |

## The near-copies

Every carrying action (any), by how much of the document it carries from it holds (the largest line share over the documents it carries from). 1,564 carrying actions; **1,024** carry 10 or more slots, of which 350 rest only on dates, bare numbers or short tokens and 674 include a specific match. One shared literal (a date, a handle, a token) accounts for half or more of the slots carried by 740 of them; the other 284 carry their slots through many different literals.

| line share | <0.10 | 0.10-0.25 | 0.25-0.50 | 0.50-0.90 | >=0.90 |
|---|---|---|---|---|---|
| all carrying actions | 1553 | 7 | 4 | 0 | 0 |
| carrying 10+ slots | 1013 | 7 | 4 | 0 | 0 |

By action type (near-copy: holds half or more of a document it carries from):

| action | carrying | carrying 10+ slots | of which weak only | of which with a specific match | near-copies |
|---|---|---|---|---|---|
| add_comment | 301 | 224 | 70 | 154 | 0 |
| add_group_member | 1 | 0 | 0 | 0 | 0 |
| append_to_file | 377 | 310 | 123 | 187 | 0 |
| create_config | 7 | 2 | 0 | 2 | 0 |
| create_issue | 46 | 22 | 5 | 17 | 0 |
| create_project | 1 | 0 | 0 | 0 | 0 |
| ensure_checkpoint | 12 | 2 | 0 | 2 | 0 |
| post_message | 261 | 129 | 23 | 106 | 0 |
| register_checkpoint | 6 | 3 | 2 | 1 | 0 |
| replace_in_file | 129 | 79 | 36 | 43 | 0 |
| rotate | 1 | 1 | 0 | 1 | 0 |
| run_reference_suite | 17 | 3 | 1 | 2 | 0 |
| send_direct_message | 36 | 11 | 0 | 11 | 0 |
| send_email | 65 | 18 | 7 | 11 | 0 |
| set_access_policy | 9 | 9 | 0 | 9 | 0 |
| submit_eval | 5 | 0 | 0 | 0 | 0 |
| update_config | 2 | 0 | 0 | 0 | 0 |
| update_issue | 48 | 10 | 4 | 6 | 0 |
| write_file | 240 | 201 | 79 | 122 | 0 |

The near-copies by action and where they write (`same_document`: the document they carry from; `other_class_document`: another of the six; `other_path`: any other path; `no_path`: not a file write):

| action \| target | near-copies |
|---|---|

## By day

| day | state-changing actions | with content | carrying at least one slot | specific | specific, no near-copies |
|---|---|---|---|---|---|
| 2026-04-06 | 1,519 | 673 | 411 | 219 | 219 |
| 2026-04-07 | 1,644 | 703 | 541 | 325 | 325 |
| 2026-04-08 | 1,763 | 810 | 612 | 400 | 400 |

## By action

| action | state-changing | with content | carrying | specific | specific, no near-copies |
|---|---|---|---|---|---|
| add_comment | 368 | 364 | 301 | 195 | 195 |
| add_group_member | 6 | 1 | 1 | 1 | 1 |
| append_to_file | 435 | 435 | 377 | 199 | 199 |
| cancel_job | 3 | 0 | 0 | 0 | 0 |
| create_channel | 7 | 7 | 0 | 0 | 0 |
| create_config | 9 | 9 | 7 | 2 | 2 |
| create_issue | 87 | 87 | 46 | 26 | 26 |
| create_project | 6 | 6 | 1 | 1 | 1 |
| delete | 17 | 0 | 0 | 0 | 0 |
| deploy | 24 | 0 | 0 | 0 | 0 |
| ensure_checkpoint | 35 | 15 | 12 | 3 | 3 |
| mkdir | 1,685 | 0 | 0 | 0 | 0 |
| post_message | 368 | 367 | 261 | 190 | 190 |
| public_link | 5 | 0 | 0 | 0 | 0 |
| redeploy | 2 | 2 | 0 | 0 | 0 |
| register_checkpoint | 16 | 16 | 6 | 3 | 3 |
| replace_in_file | 200 | 200 | 129 | 71 | 71 |
| reply_email | 2 | 1 | 0 | 0 | 0 |
| rotate | 5 | 1 | 1 | 1 | 1 |
| run_reference_suite | 23 | 23 | 17 | 3 | 3 |
| send_direct_message | 78 | 76 | 36 | 27 | 27 |
| send_email | 306 | 130 | 65 | 32 | 32 |
| set_access_policy | 31 | 31 | 9 | 9 | 9 |
| share | 7 | 0 | 0 | 0 | 0 |
| submit_eval | 79 | 16 | 5 | 2 | 2 |
| tag_approved | 37 | 0 | 0 | 0 | 0 |
| transition_issue | 126 | 0 | 0 | 0 | 0 |
| update_config | 2 | 2 | 2 | 1 | 1 |
| update_issue | 161 | 133 | 48 | 42 | 42 |
| write_file | 796 | 264 | 240 | 136 | 136 |

## Carrying actions per slot, whole log

| carrying actions | 0 | 1 | 2-5 | 6-20 | 21+ |
|---|---|---|---|---|---|
| slots | 94 | 10 | 36 | 26 | 130 |

## Ordering

Per class document: writes, adjacent pairs out of simulated-timestamp order in the file, and whether the final state is the same in both orders.

| document | writes | out of order in the file | final state the same |
|---|---|---|---|
| README.md | 19 | 2 | False |
| release-gate-runbook.md | 28 | 6 | True |
| finetune-guide.md | 18 | 1 | True |
| redteam-checklist.md | 24 | 5 | True |
| oncall-runbook.md | 22 | 4 | True |
| engineering-setup.md | 19 | 1 | True |

Sensitivity, simulated-timestamp order instead of file order (same rule, labelled; file order governs):

| order | slots carried (any / specific / specific, no near-copies) | carrying (any / specific / specific, no near-copies) | actions carrying (any / specific / specific, no near-copies) | edits | copies | same session |
|---|---|---|---|---|---|---|
| file (governing) | 202 / 160 / 160 | 27,137 / 6,572 / 6,572 | 1,564 / 944 / 944 | 225 | 35 | 2,251 |
| timestamp | 204 / 163 / 163 | 25,669 / 6,135 / 6,135 | 1,546 / 916 / 916 | 327 | 35 | 2,405 |
