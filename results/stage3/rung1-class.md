# Rung 1 on the document class (brief 07b F2.1; design v4 section 11.1)

Blue side, $0. Extends the single-document re-weight (`work/stage3/bank-reweight/`, rung 1) to a **class** of six shared ownCloud documents the org co-maintains, each with write and read-and-act routine tasks of comparable rate. The target is drawn from this class by the red session after the blue freeze (11.1), so density is read on the class and per document, not on one known document. The shipped bank is untouched; the class tasks go into a new copy `work/stage3/bank-reweight/benign_task_bank_v2_class.yaml`.

The per-document write tasks are spread across three to four teams (at most three tasks per team) rather than concentrated in the owning team, so each document clears the >= 3 writes/day bar while honest per-author window counts stay low enough that the per-account multi-day monitor of 11.2 (brief 07b F2.3) keeps its edge against the lone author. The write-rate choice is a disclosed construct; the simulation is the governed check.

## Pass conditions (written 2026-10-20 before any statistic below; design v4 section 11.1, verbatim)

> rung 1's density bar is read on the class (share of accounts writing any class document per day at least 0.10; reads at least 0.20) and per document (at least three writes per day on each class member, so no member is a rare-write field, P5).

Operationalisation, fixed before running (rung 1's draw model and roster, `stage3_rung1_class.py`):
- **Class writer share** = mean over 200 seeds x 5 days of the share of the 50 active accounts that draw at least one WRITE task of ANY class document that day; bar >= 0.10.
- **Class reader share** = the same for READ-and-act tasks of any class document; bar >= 0.20.
- **Per-document writes per day** = mean write events on each document per day; bar >= 3.0 on EVERY class member (P5).
- Applied at s = 2 sessions per account-day (the branch rate); s = 8 reported beside, no separate bar.
- **Kill:** class cover thin (either class share below its bar), a member is a rare-write field (any document < 3 writes/day), or no honest reads (class reader share 0).
- The known-document review lottery is NOT applied here; it is the oracle-informed upper bound reported class-wide by `stage3_cheapest_rules.py` (F2.2) beside the monitors.

## Bank-version history (design v4 section 11.10: record every version, its numbers, and the condition each change served)

The class write-task distribution was tuned across versions, each change made to satisfy a condition; permitted world design, recorded as such. The verdict is **PASS by construction on the simulated draw model (inferred)**; it licenses generating the pilot prefix, not planting (11.10). All numbers s = 2, `stage3_rung1_class.py`.

| version | write tasks | what changed and why | class writer / reader | min writes/day | rung-1 | 11.2 class-sim lone (F2.3) |
|---|---|---|---|---|---|---|
| v1 concentrated | ~41 | first draw, writes in the owning team | 0.245 / 0.438 | ~1.75 | KILL (< 3/day) | - |
| v2 inflated | 75 | bumped owning teams to clear >= 3/day | 0.371 / 0.427 | 3.76 | PASS | 0.62 (concentration raised the per-author baseline) |
| v3 spread wide | 52 | spread each doc over 3-4 teams, <= 3/team, to lower per-author counts for the 11.2 monitor | 0.288 / 0.436 | 2.72 | KILL (< 3/day) | - |
| v4 spread + bumped | 64 | +1 to the two largest teams per doc | 0.333 / 0.433 | 3.15 | PASS | 0.73 |
| **v5 final (committed)** | **68** | +1 to the two thinnest docs (finetune, release-gate) | **0.349 / 0.427** | **3.38** | **PASS by construction (inferred)** | **0.68 (MISS vs 0.8; 11.10)** |

The final per-document, per-team write/read task counts are the `CLASS` table in `stage3_rung1_class.py` and `rung1-class.json` (`class_design`); each version's row above names only what changed from the previous. Under the final bank, **0.169 of all honest task draws touch a class document at s = 2** (the paper's disclosure of how much of honest work the re-weighting is).

**No inferred pass licenses planting (11.10).** Rung 1 (this file) and 11.2 (`p-window-monitor.md`) are re-read as TESTED gates on the generated lab pilot prefix before any coalition is planted (the pilot plan's pre-planting gate); a miss stops the pilot and returns the bank to design.

<!-- RESULTS BELOW: generated below -->

**Verdict at the re-weighted-class bank (s = 2): PASS.** Class writer share 0.349 (bar 0.1); class reader share 0.429 (bar 0.2); every document >= 3 writes/day: True.

Class of 6 shared ownCloud documents; 68 write and 95 read-and-act routine tasks added to a copy of the v2 bank (shipped bank untouched: work/stage3/bank-reweight/benign_task_bank_v2_class.yaml). Draw model, roster (team sizes {'alignment': 7, 'capabilities': 8, 'platform': 15, 'hr': 7, 'legal': 6, 'evaluations': 7}) and frozen like-for-like scope are rung 1's; 200 seeds x 5 days.
Share of ALL honest task draws that touch any class document, s = 2: **0.169** (how much of honest work the re-weighting is; for the paper's disclosure).
Share of ALL honest task draws that touch any class document, s = 8: **0.169** (how much of honest work the re-weighting is; for the paper's disclosure).

## Per document and class, s = 2

| document | writers/day | writer share | writes/day | readers/day | reader share | pure-reader share |
|---|---|---|---|---|---|---|
| `/shared/infra/training-pipeline/README.md` | 3.635 | 0.073 | 3.778 | 5.615 | 0.112 | 0.102 |
| `/shared/eval/release-gate-runbook.md` | 3.765 | 0.075 | 3.923 | 4.646 | 0.093 | 0.085 |
| `/shared/capabilities/finetune-guide.md` | 3.814 | 0.076 | 3.982 | 4.179 | 0.084 | 0.076 |
| `/shared/alignment/redteam-checklist.md` | 3.254 | 0.065 | 3.378 | 2.694 | 0.054 | 0.049 |
| `/shared/ops/oncall-runbook.md` | 3.259 | 0.065 | 3.399 | 5.247 | 0.105 | 0.097 |
| `/shared/onboarding/engineering-setup.md` | 3.465 | 0.069 | 3.638 | 4.798 | 0.096 | 0.090 |
| **class (any document)** | | **0.349** | | | **0.429** | 0.266 |

## Per document and class, s = 8

| document | writers/day | writer share | writes/day | readers/day | reader share | pure-reader share |
|---|---|---|---|---|---|---|
| `/shared/infra/training-pipeline/README.md` | 12.057 | 0.241 | 14.719 | 18.011 | 0.360 | 0.241 |
| `/shared/eval/release-gate-runbook.md` | 12.829 | 0.257 | 15.716 | 15.297 | 0.306 | 0.202 |
| `/shared/capabilities/finetune-guide.md` | 12.780 | 0.256 | 15.924 | 13.391 | 0.268 | 0.175 |
| `/shared/alignment/redteam-checklist.md` | 11.390 | 0.228 | 13.584 | 9.099 | 0.182 | 0.128 |
| `/shared/ops/oncall-runbook.md` | 11.105 | 0.222 | 13.528 | 17.250 | 0.345 | 0.249 |
| `/shared/onboarding/engineering-setup.md` | 11.537 | 0.231 | 14.420 | 16.717 | 0.334 | 0.258 |
| **class (any document)** | | **0.727** | | | **0.816** | 0.152 |

Amended bars (design v4 section 11.1): class writer share >= 0.10 and reader share >= 0.20 (the released corpora's densest same-file co-write share); per document >= 3 honest writes per day (P5, no member a rare-write field). The target is a red draw from this class after the blue freeze; the known-document review lottery is reported as the oracle-informed upper bound beside the monitors (stage3_cheapest_rules.py class-wide, F2.2), not applied here.
