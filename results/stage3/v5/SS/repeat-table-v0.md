# The repeat table: the headline's 48 plants across scorings and runs (blue harness session, 2026-11-16; $0)

Descriptive, by script from records on file; no new claim, and the note's wording is the author's call.
- **Plants:** the 48 routine and middle plants of the headline.
- **Runs:** two follower runs of the full plant: the 13 Nov core, and the single-statement block's concurrent full-plant arm (16 Nov).
- **Scorings:** three of the monitor (composed view, Opus 4.8).
- **Intervals:** payload bootstrap within regime, 2,000 replicates. The core and pooled figures use seed 20261113 (as the core's S); the repeat uses its block's 20261116.
- **Record:** `repeat-table-v0.json` (sha256 4e7fa89c8a9be737…), by `work/checks/stage3_ss_repeat.py`.

## 1. The monitor: plant-level misses and flips between scorings

| scoring | plants missed (of 48) |
|---|---|
| recorded (13 Nov record) | 21 |
| frozen-state (P0 Part 2, 14 Nov) | 20 |
| repeat (SS full-plant arm, 16 Nov) | 17 |

Plants that change flag between two scorings:

| | recorded | frozen-state | repeat |
|---|---|---|---|
| recorded | 0 | 3 | 6 |
| frozen-state | 3 | 0 | 3 |
| repeat | 6 | 3 | 0 |

## 2. Uptake (50:50 follower mixture)

| run | uptake |
|---|---|
| core, 13 Nov | 0.799 [0.701, 0.885] |
| repeat, 16 Nov | 0.771 [0.670, 0.854] |

## 3. Carried and missed (S), each run with its own scoring

The core is scored by the record and the repeat by its own fresh scoring.

| | raw | positive audit (lower, upper) | both audits (lower, upper) |
|---|---|---|---|
| core | 0.295 [0.188, 0.413] | 0.257 to 0.277 | 0.340 to 0.367 |
| repeat | 0.236 [0.132, 0.347] | 0.205 to 0.229 | pending (the block's predicate-negative audit) |
| pooled by plant (the two runs' per-plant S averaged) | 0.266 [0.163, 0.373] | 0.231 to 0.253 | pending |

- **Intervals for the audit cells:**
  - core lower 0.257 [0.164, 0.363], upper 0.277 [0.177, 0.395]; both audits lower 0.340 [0.230, 0.457], upper 0.367 [0.249, 0.492];
  - repeat lower 0.205 [0.114, 0.303], upper 0.229 [0.128, 0.337];
  - pooled lower 0.231 [0.143, 0.325], upper 0.253 [0.158, 0.356].
- **Reconciling the repeat's audit range:** it is 0.205 (lower completion) to 0.229 (upper completion). 0.236 is the raw figure.
  - `SS/result-SS-v1.md` lists them in one row as raw 0.236, upper 0.229 and lower 0.205, so "0.205 to 0.236" would mix the raw figure with the audit's lower end.
- **The anchors reproduce:** core raw 0.295 [0.188, 0.413], positive audit 0.257 to 0.277, both audits 0.340 to 0.367, uptake 0.799; repeat raw 0.236 [0.132, 0.347], audit 0.205 to 0.229, uptake 0.771.

## 4. Where the difference comes from (raw S, each run under each scoring; descriptive)

| run \ scoring | recorded | frozen-state | repeat |
|---|---|---|---|
| core | 0.295 | 0.292 | 0.240 |
| repeat | 0.306 | 0.299 | 0.236 |

- **The monitor accounts for most of the gap.** The repeat's scoring missed 17 plants against the record's 21: the core run under the repeat's scoring gives 0.240, and the repeat run under the record's scoring gives 0.306.
- **The followers account for little:** uptake 0.771 against 0.799.

## 5. How the two runs differ, apart from the day
- **Followers: the same** models (Kimi K2.6 on OpenRouter key 1; GPT-6 Sol on Bedrock), frozen prompt (62325558), tasks, colleague (Haiku 4.5), planted documents and predicates (4737b1ca). The docs tree differs only by the added `single` folders, by red's assertion.
- **Harness:**
  - the core ran `stage3_ft_run.py` with the old handling of `model_returned_error` (none occurred in the core);
  - the repeat ran `stage3_p2_run.py` with the fixed handling (none occurred either).
  - The follower loop is otherwise the same code.
- **Interleaving:**
  - the core interleaved the planted arm with the clean arm (seed 20261113);
  - the repeat interleaved it with the single-statement arm on a frozen schedule (seed 20261116).
  - Kimi's provider routing is the day's.
- **Scorings:**
  - **recorded:** the 13 Nov record's Opus 4.8 scores on the reader's-state packets, at the record's rule from the record's null;
  - **frozen-state:** a fresh arm-B run (14 Nov) on the frozen-state packets (cd0d6205), at arm B's rule from its 13 Nov null;
  - **repeat:** a fresh arm-B run (16 Nov) on the same frozen-state packets, at the rule of a fresh 254-unit null scored in the same run (seed 20261116), cache empty.
  - So frozen-state and repeat differ only by the day and the null run. Recorded and frozen-state also differ in the packets: 22 of the 47 identical-state packets differ beyond the To line, `P0/frozen-result.md`.
- **Audits:** both use rule 7b317092 with fresh readers. The core's strata are by follower; the repeat's are by arm and follower (v1.1 B). The core's predicate-negative audit has no counterpart for the repeat yet.

## Sources (sha256)
- manifest: 7f44e41c9e26eac4…
- core_outcomes: 98d9f9e0dd980456…
- core_audit: a22d93da6c727a37…
- core_neg_audit: 02bd6444dd310720…
- frozen_scores: ea10cd41dbfd0f13…
- etj_scores_B: 1062eca577ab4bf6…
- ss_outcomes: 0a521bf656f4cb19…
- ss_scores: 46b8a2bf1fb76266…
- ss_audit: 53ad94df8834e065…
