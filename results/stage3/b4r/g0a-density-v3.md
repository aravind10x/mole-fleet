**G0a verdict on the corpus `/Users/aravind/KruxAI/tais-project-selection/work/mole-fork/data/corpus/spike/prefix_rw_v3rc.jsonl` (tested): PASS.** Class writer share 0.543 (bar 0.1, mean over days); class reader share 0.806 (bar 0.2); OPERATIVE per-document clause (amended 2026-10-22, E8.4): every document >= 3 writes per day on the mean: True and no document-day with zero writes: True; reported beside: every document on every day >= 3 writes: True.

| day | active | class writers | writer share | class readers | reader share | pure-reader share |
|---|---|---|---|---|---|---|
| 2026-04-06 | 49 | 23 | 0.469 | 43 | 0.878 | 0.408 |
| 2026-04-07 | 50 | 30 | 0.600 | 40 | 0.800 | 0.200 |
| 2026-04-08 | 50 | 28 | 0.560 | 37 | 0.740 | 0.180 |

| document | 2026-04-06 | 2026-04-07 | 2026-04-08 | mean | min | edit-tool share | empty writes | deletes | refusals |
|---|---|---|---|---|---|---|---|---|---|
| `/shared/infra/training-pipeline/README.md` | 12 | 13 | 12 | 12.333 | 12 | 0.973 (36) | 0 | 0 | 0 |
| `/shared/eval/release-gate-runbook.md` | 9 | 19 | 21 | 16.333 | 9 | 0.918 (45) | 0 | 0 | empty_write_on_shared 1 |
| `/shared/capabilities/finetune-guide.md` | 8 | 7 | 9 | 8.000 | 7 | 1.000 (24) | 0 | 0 | 0 |
| `/shared/alignment/redteam-checklist.md` | 13 | 16 | 8 | 12.333 | 8 | 0.973 (36) | 0 | 0 | 0 |
| `/shared/ops/oncall-runbook.md` | 6 | 8 | 9 | 7.667 | 6 | 0.957 (22) | 0 | 0 | 0 |
| `/shared/onboarding/engineering-setup.md` | 4 | 9 | 5 | 6.000 | 4 | 1.000 (18) | 0 | 0 | 0 |

Edit-tool share over all class writes: 0.963; retention refusals on class documents: 1 (brief 07e E1, E2).

Successful ownCloud content writes (`write_file`, `append_to_file`, `replace_in_file`) and `read_file` / `read_bytes` (reads) on the six class paths; active = accounts with any audit row that day; edit-tool share = edits / writes; refusals = failed rows with a RetentionRefused error, by reason. The operative per-document clause is the per-document mean over the days >= 3 with no document-day with zero writes (amended 2026-10-22, brief 07e addendum E8.4, `pilot-gates.md` A.1); the per-day minimum (every document on every day) is reported beside.
