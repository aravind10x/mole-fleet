# Gate reachability under the pinned reader (brief 30 Part 2: E1 and E2; blue; counts, aggregates and hashes only)

Script `work/checks/stage3_elicitation_gate_reachability_v1.py` 7347b34d, importing E0-5's `stage3_elicitation_gate_reachability.py` c7a95ec2 unchanged; the runs by `stage3_elicitation_e1e2.py` 7aac0157. Decision 8 is `work/stage3/elicitation/review/reconcile-e2-rule-2026-11-02.md` (cb9f626e). Item ids are in the JSON; no item text, rubric or answer was read.

## Decision 8's trigger

- **The trigger FIRES.** On the pair Kimi K3 pinned (E2) + Sol (mean; brief 25's samples), gate (iii) per reader on any of its own samples (protocol section 4): **12 of 78 certified** (fires if fewer than 5) and **2 of 78 quiet-but-illegible** (fires if fewer than 3), at cap 96 (432 candidates over three writer rounds: expected 66.5 certified against 26 and 11.1 quiet-but-illegible against 12). Certified fires: False; illegible fires: True.
- Beside, never a trigger: at cap 48 (240 candidates) the lines are fewer than 9 and fewer than 4 (the rules file's 0.108 and 0.050): certified at or above, illegible below. Same-sample reading 12, both readers on both samples 5. E2 pairs the pinned reader's new sample s with Sol's brief 25 sample s; the index pairing is arbitrary (protocol section 4: samples are independent calls), so the same-sample count is beside only.
- Wilson 95 % intervals: certified 12/78 [0.090, 0.250]; quiet-but-illegible 2/78 [0.007, 0.089]; mixed 11/78 [0.081, 0.235]. The lines are point expectations per rater-quiet candidate (B3's 78 candidates are rater-quiet by selection), made optimistic by the new writers' validity and rater-quiet losses; counts this small carry wide intervals.
- Orientation beside (E0-5, brief 25's readers, Kimi K3 on mixed providers): certified 11, same sample 10, both-both 5, quiet-but-illegible 7, of 78.
- **If it fires** (rule file): Part 2 stops and the choice goes to Aravind by dated note before writer round 1.

## The nulls under the pinned reader

- 46 nulls (22 controls, 24 same-shape comparison items, against their false targets), Kimi K3 pinned at two samples: 46 evaluable; **whole credit on 0 items** (0 of 92 cells), part credit on 0 items (0 cells).
- Class under Kimi pinned + Sol (mean): certified 0 of 46 (holds by construction, since Sol's brief 25 samples credit no null's whole; not the finding).

## The gate at two samples under the pin (E2)

| set | pair (second reader's rule) | k | items | pass (ii) | certified (iii, any) | same sample | both, both | quiet-but-illegible | mixed | part-derivable | not evaluable | loud |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B3 candidates | Kimi K3 pinned + Sol (mean): the trigger | 2 | 78 | 25 | 12 | 12 | 5 | 2 | 11 | 53 | 0 | 0 |
| B3 candidates | Kimi K3 pinned + Sol (every, beside) | 2 | 78 | 19 | 10 | 10 | 3 | 1 | 8 | 59 | 0 | 0 |
| B3 candidates, glm53-written | Kimi K3 pinned + Sol (mean) | 2 | 37 | 13 | 6 | 6 | 1 | 1 | 6 | 24 | 0 | 0 |
| B3 candidates, sonnet55-written | Kimi K3 pinned + Sol (mean) | 2 | 41 | 12 | 6 | 6 | 4 | 1 | 5 | 29 | 0 | 0 |
| B3 candidates, GLM-written | Kimi K3 pinned + Sonnet 5.5 (every), beside | 2 | 37 | 13 | 3 | 3 | 1 | 2 | 8 | 24 | 0 | 0 |
| B3 candidates, GLM-written | Kimi K3 pinned + Sol (mean) | 2 | 37 | 13 | 6 | 6 | 1 | 1 | 6 | 24 | 0 | 0 |
| nulls (46) | Kimi K3 pinned + Sol (mean) | 2 | 46 | 46 | 0 | 0 | 0 | 46 | 0 | 0 | 0 | 0 |
| nulls (46) | Kimi K3 pinned + Sol (every) | 2 | 46 | 46 | 0 | 0 | 0 | 46 | 0 | 0 | 0 | 0 |
| nulls, 10 controls read by Sonnet 5.5 | Kimi K3 pinned + Sonnet 5.5 (every) | 2 | 10 | 10 | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 |
| nulls, control | Kimi K3 pinned + Sol (mean) | 2 | 22 | 22 | 0 | 0 | 0 | 22 | 0 | 0 | 0 | 0 |
| nulls, sham | Kimi K3 pinned + Sol (mean) | 2 | 24 | 24 | 0 | 0 | 0 | 24 | 0 | 0 | 0 | 0 |
| T1 items (48), beside | Kimi K3 pinned + Sol (mean) | 2 | 48 | 11 | 7 | 7 | 5 | 2 | 2 | 32 | 0 | 5 |
| T1 items (48), beside | Kimi K3 pinned + Sonnet 5.5 (every) | 2 | 48 | 8 | 4 | 4 | 4 | 1 | 3 | 27 | 8 | 5 |
| T1 v2 conforming | Kimi K3 pinned + Sol (mean) | 2 | 24 | 3 | 2 | 2 | 1 | 1 | 0 | 19 | 0 | 2 |
| T1 v3 middle | Kimi K3 pinned + Sol (mean) | 2 | 24 | 8 | 5 | 5 | 4 | 1 | 2 | 13 | 0 | 3 |

Gate (i) is E0-5's single session (brief 25's `rater_top_line` for the candidates, 07k's two-pass line mean for the T1 items, not applied to nulls). The second readers' samples are brief 25's for its items and, for the T1 items, brief 23's r0 with brief 23's r1 (10 retest items) or E1's r1 (38 items).

## Gate (ii) by rule under the pin

| items | rule | pass |
|---|---|---|
| b3 candidates 78 | kimi_pin every | 27 |
| b3 candidates 78 | kimi (brief 25) every, beside | 30 |
| b3 candidates 78 | sol sol_mean | 50 |
| b3 candidates 78 | kimi_pin every + sol sol_mean | 25 |
| b3 candidates 78 | kimi_pin every + sol every | 19 |
| b3 candidates glm 37 | kimi_pin every | 14 |
| b3 candidates glm 37 | sonnet55 every | 23 |
| b3 candidates glm 37 | kimi_pin every + sonnet55 every | 13 |
| b3 candidates glm 37 | kimi_pin every + sol sol_mean | 13 |

Kimi K3's cell rates (a cell is one item and sample with all four conditions scored):

| items | reader | cells | D_part > 0 | D_whole > 0 |
|---|---|---|---|---|
| b3 candidates | kimi_pin (E2) | 156 | 0.494 | 0.699 |
| b3 candidates | kimi (brief 25, mixed), beside | 156 | 0.500 | 0.667 |
| nulls 46 | kimi_pin (E2) | 92 | 0.000 | 0.000 |
| t1 items | kimi_pin (E2) | 96 | 0.656 | 0.812 |
| t1 items | kimi (brief 23 r0, mixed), beside | 48 | 0.667 | 0.750 |

Pinned reads not answered (by source, regime, condition and status): none.

## E1: the T1 items at two samples under brief 23's three readers

| set | pair (second reader's rule) | k | items | pass (ii) | certified (iii, any) | same sample | both, both | quiet-but-illegible | mixed | part-derivable | not evaluable | loud |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 items (48) | Kimi K3 + Sol (mean) | 2 | 48 | 13 | 10 | 10 | 7 | 1 | 2 | 30 | 0 | 5 |
| T1 items (48) | Kimi K3 + Sonnet 5.5 (every) | 2 | 48 | 10 | 6 | 6 | 5 | 1 | 3 | 25 | 8 | 5 |
| T1 v2 conforming | Kimi K3 + Sol (mean) | 2 | 24 | 4 | 3 | 3 | 2 | 0 | 1 | 18 | 0 | 2 |
| T1 v3 middle | Kimi K3 + Sol (mean) | 2 | 24 | 9 | 7 | 7 | 5 | 1 | 1 | 12 | 0 | 3 |

Items with two samples per reader: {"kimi": 48, "sol": 48, "sonnet55": 39} of 48; E1 read 38 items; not evaluable at E1's r1: {"kimi": 0, "sol": 0, "sonnet55": 7}. Kimi K3's second sample on the 38 items read once is E1's, through the pin; on the 10 retest items it is brief 23's r1 (mixed providers). Sol and Sonnet 5.5 are brief 23's routes (Bedrock).

## Served provider and precision

- E2, Kimi K3: 1376 final records, by provider|precision|pin {"Wafer|mxfp4|on_pin": 1376}; attempts served off the pin 0 (each recorded errored and re-issued); final records off the pin 0.
- E1, Kimi K3: 152 final records, {"Wafer|mxfp4|on_pin": 152}; attempts off the pin 0; final off the pin 0.
- E1, Sol: converse `us.openai.gpt-6-sol`; Sonnet 5.5: bedrock `global.anthropic.claude-sonnet-5-5`; scorer: `anthropic.claude-sonnet-5` (Bedrock; no provider choice). Every Kimi record's provider and precision is in the JSON (`served.*.per_record`, by label).

## Spend and key 2

- E1: $4.22 (kimi $1.95, sol $0.40, sonnet55 $0.43, scorer $1.45); stop $6.50; stopped False; outcomes {"kimi": {"scored": 152}, "sol": {"scored": 152}, "sonnet55": {"refused": 9, "scored": 143}, "scorer": {"scored": 894}}.
- E2: $21.13 (kimi $16.63, scorer $4.49); stop $28.60; stopped False; outcomes {"kimi": {"scored": 1376}, "scorer": {"scored": 2752}}.
- Both runs: $25.35 against the approved $17.52 (pause $23.36, hard stop $35.04).
- E2 stopped at the pause (2026-11-03T07:02:58+00:00): stop $19.14, spent $19.14, every read done, scorer 1536 of 2752; it resumed from cache past the pause on Aravind's word in this session (`--past-pause`: E2's stop at its $28.60 cap, under the hard stop over both runs).
- Runner hash at each plan: E1 50b1dd98, E2 7aac0157, now 7aac0157 (E1's run ended at its summary print, after every call and the summary file; the change since adds the print-safe summary and nothing else).
- Key 2 before E1 (2026-11-03T05:42:51+00:00): limit remaining $306.24, account remaining $116.24, headroom $116.24.
- Key 2 before E2 (2026-11-03T05:57:47+00:00): limit remaining $303.82, account remaining $113.82, headroom $113.82.
- Key 2 before E2 (2026-11-03T09:49:36+00:00): limit remaining $279.79, account remaining $89.79, headroom $89.79.
- Key 2's usage from 2026-11-03T05:42:51+00:00 to 2026-11-03T05:57:47+00:00 (the window E1 opened): $2.42, against $1.95 of OpenRouter calls in E1's records; $0.47 is not in this run's records (Sol, Sonnet 5.5 and the scorer are Bedrock, not key 2).
- Key 2's usage from 2026-11-03T05:57:47+00:00 to 2026-11-03T09:49:36+00:00 (the window E2 opened): $24.03, against $16.63 of OpenRouter calls in E2's records; $7.40 is not in this run's records (Sol, Sonnet 5.5 and the scorer are Bedrock, not key 2).

## Inputs

- `work/stage3/b3/comprehension/stratum-v0.json` 6113bd8d
- `work/stage3/b3/comprehension/t1-per-part-v0.json` 143c5d79
- `work/stage3/b3/comprehension/t1-join-v0.json` 90ef9867
- `work/stage3/legibility/items-v0.json` 71fba565
- `work/stage3/legibility/routes-v0.json` 6c18d7a9
- `work/stage3/b3/comprehension/items-v0.json` 064225b4
- `work/stage3/elicitation/review/reconcile-e2-rule-2026-11-02.md` cb9f626e
- `work/stage3/elicitation/e1e2/e1/cache/judge-cache.legibility.read.kimi.moonshotai_kimi-k3.jsonl` eb43647d
- `work/stage3/elicitation/e1e2/e1/cache/judge-cache.legibility.read.sol.us-openai-gpt-6-sol.jsonl` 4be6e485
- `work/stage3/elicitation/e1e2/e1/cache/judge-cache.legibility.read.sonnet55.global-anthropic-claude-sonnet-5-5.jsonl` e30fa372
- `work/stage3/elicitation/e1e2/e1/cache/judge-cache.legibility.score.anthropic-claude-sonnet-5.jsonl` 02add3ca
- `work/stage3/elicitation/e1e2/e2/cache/judge-cache.legibility.read.kimi.moonshotai_kimi-k3.jsonl` 71cfd9ed
- `work/stage3/elicitation/e1e2/e2/cache/judge-cache.legibility.score.anthropic-claude-sonnet-5.jsonl` c0ef77c5
- `work/stage3/elicitation/e1e2/e1/plan-v0.json` ec42b0b8
- `work/stage3/elicitation/e1e2/e1/run-summary.json` 341fafc5
- `work/stage3/elicitation/e1e2/e1/models-v0.json` 45f2fa8a
- `work/stage3/elicitation/e1e2/e1/kimi-endpoints.json` 71dcdf8e
- `work/stage3/elicitation/e1e2/e2/plan-v0.json` 2b1785dd
- `work/stage3/elicitation/e1e2/e2/run-summary.json` 3b84becf
- `work/stage3/elicitation/e1e2/e2/models-v0.json` 1c1be39a
- `work/stage3/elicitation/e1e2/e2/kimi-endpoints.json` 003fd23c
- `work/stage3/elicitation/e1e2/e2/run-summary-00-pause.json` 4242b565
- `work/stage3/elicitation/e1e2/e1/limits-00.json` 7f0cd9af
- `work/stage3/elicitation/e1e2/e2/limits-00.json` c1cdfd19
- `work/stage3/elicitation/e1e2/e2/limits-01.json` 2aa6c266

