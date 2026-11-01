# Gate reachability and null safety at two samples (brief 29 E0-5, session 29-B; blue; counts, aggregates and hashes only)

Script `work/checks/stage3_elicitation_gate_reachability.py` c7a95ec2; no call made. The gates, readers and classes are `certification-protocol-v0.md` (3a071bd0) sections 4 to 6, recomputed from brief 23's and brief 25's existing readings by id and aggregate. Item ids are in the JSON; no item text, rubric or answer was read.

## Verdict

- **Reachable at two samples: yes.** On brief 25's B3 candidates under Kimi K3 (mixed providers) and Sol's mean rule, 11 of 78 pass all three gates (gate (i) single session; gate (iii) per reader on any sample); 10 under the same-sample reading and 5 with both readers crediting the whole on both samples. Under Sonnet 5.5's every-sample rule (the strict second reader, on the 37 GLM-written candidates): 4 certified.
- **Null-safe at two samples: yes.** Brief 25's 46 nulls (22 controls and 24 same-shape comparison items, against their false targets): 0 of 46 certified under either rule; every null passes gate (ii) and no null's whole is credited on any sample, so all 46 fall in the quiet-but-illegible class: that class does not separate quiet-but-illegible items from honest ones, and the certified class does.
- **Under the pinned reader (Wafer at MXFP4) at two samples: null-safe on the subset the proxy covers; reachability not shown.** Part 3's join (reproduced exactly) puts both samples' four Kimi conditions on Wafer for 11 B3 candidates and 5 nulls (Part 3's pairing; 6 and 3 with a determined provider). Of those 11 candidates 1 passes gate (ii) and none is certified; of the 5 nulls, none. Wafer-served cells credit a part far more often than the other cells (0.818 of 22 candidate cells against 0.448 of 134; A6.18 (m)'s 'about twice as often'), so gate (ii) under the pin will pass far fewer items than brief 25's 28 of 78. These are small and possibly time-clustered cells, an orientation only: whether certification is reachable under the pinned reader at two samples is not shown by the existing readings, and E2 answers it.
- **Not computed (each needs a new reading; estimates below, nothing run):** gate (i) at two certification rater sessions (one session on file; E3); T1 items at two samples for the 38 items read once (E1); the pinned reader at two samples beyond the Wafer-served cells (E2).

## Gate (i), one rater session

- B3 candidates: 78 of 78 at or under 60 (brief 25's `rater_top_line`; they are B3's quiet set, selected by this gate, so it cannot bind here).
- T1 v2 conforming: 22 of 24 items have every line at or under 60 (07k's two-pass line mean; pass 1 alone 22).
- T1 v3 middle: 21 of 24 items have every line at or under 60 (07k's two-pass line mean; pass 1 alone 22).
- Nulls: no rater line on file for brief 25's controls and shams or brief 23's nulls; gate (i) not applied to them (gate iii binds a null, whose whole is read against a false target).
- one rater session (two passes) on file; the protocol's gate (i) is the mean of two sessions (E3 below).

## Gate (ii) by second-reader rule (brief 25, two samples)

| items | rule | pass |
|---|---|---|
| b3 candidates 78 | kimi every | 30 |
| b3 candidates 78 | sol sol_mean | 50 |
| b3 candidates 78 | sol every | 33 |
| b3 candidates 78 | kimi every + sol sol_mean | 28 |
| b3 candidates 78 | kimi every + sol every | 21 |
| b3 candidates glm 37 | kimi every | 17 |
| b3 candidates glm 37 | sonnet55 every | 23 |
| b3 candidates glm 37 | sol sol_mean | 25 |
| b3 candidates glm 37 | kimi every + sonnet55 every | 15 |
| b3 candidates glm 37 | kimi every + sol sol_mean | 16 |

Given Kimi K3's every-sample rule, the second reader removes 2 of 30 under Sol's mean rule (78 items; 9 under Sol's every-sample rule, beside). On the 37 GLM-written items Sol's mean rule removes 1 of 17 and Sonnet 5.5's every-sample rule 2: on these data the two second-reader rules differ little at gate (ii) once Kimi's rule applies. They differ at gate (iii): with Sonnet 5.5 as the second reader 4 of the 37 are certified, with Sol 7, because Sonnet 5.5 credits the whole less often (protocol section 10, item 6: every pooled yield carries its rule).

## The gate at two samples

| set | pair (second reader's rule) | k | items | pass (ii) | certified (iii, any) | same sample | both, both | quiet-but-illegible | mixed | part-derivable | not evaluable | loud |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B3 candidates | Kimi K3 + Sol (mean) | 2 | 78 | 28 | 11 | 10 | 5 | 7 | 10 | 50 | 0 | 0 |
| B3 candidates | Kimi K3 + Sol (every, beside) | 2 | 78 | 21 | 9 | 8 | 4 | 5 | 7 | 57 | 0 | 0 |
| B3 candidates, glm53-written | Kimi K3 + Sol (mean) | 2 | 37 | 16 | 7 | 6 | 3 | 4 | 5 | 21 | 0 | 0 |
| B3 candidates, sonnet55-written | Kimi K3 + Sol (mean) | 2 | 41 | 12 | 4 | 4 | 2 | 3 | 5 | 29 | 0 | 0 |
| B3 candidates, GLM-written | Kimi K3 + Sonnet 5.5 (every) | 2 | 37 | 15 | 4 | 4 | 2 | 4 | 7 | 22 | 0 | 0 |
| B3 candidates, GLM-written | Kimi K3 + Sol (mean) | 2 | 37 | 16 | 7 | 6 | 3 | 4 | 5 | 21 | 0 | 0 |
| nulls (46) | Kimi K3 + Sol (mean) | 2 | 46 | 46 | 0 | 0 | 0 | 46 | 0 | 0 | 0 | 0 |
| nulls (46) | Kimi K3 + Sol (every) | 2 | 46 | 46 | 0 | 0 | 0 | 46 | 0 | 0 | 0 | 0 |
| nulls, 10 controls read by Sonnet 5.5 | Kimi K3 + Sonnet 5.5 (every) | 2 | 10 | 10 | 0 | 0 | 0 | 10 | 0 | 0 | 0 | 0 |
| nulls, control | Kimi K3 + Sol (mean) | 2 | 22 | 22 | 0 | 0 | 0 | 22 | 0 | 0 | 0 | 0 |
| nulls, sham | Kimi K3 + Sol (mean) | 2 | 24 | 24 | 0 | 0 | 0 | 24 | 0 | 0 | 0 | 0 |
| T1 retest items | Kimi K3 + Sol (mean) | 2 | 10 | 2 | 2 | 2 | 1 | 0 | 0 | 8 | 0 | 0 |
| T1 retest items | Kimi K3 + Sonnet 5.5 (every) | 2 | 10 | 1 | 1 | 1 | 1 | 0 | 0 | 8 | 1 | 0 |
| brief 23 nulls, retest items | Kimi K3 + Sol (mean) | 2 | 20 | 20 | 0 | 0 | 0 | 20 | 0 | 0 | 0 | 0 |

Gate (i) is applied where a rater figure exists (B3 candidates, T1 items) and not applied to nulls. Brief 23 read every T1 item with all three families, so no family exclusion is applied to the T1 rows.

## Beside: one sample (sample 0)

| set | pair (second reader's rule) | k | items | pass (ii) | certified (iii, any) | same sample | both, both | quiet-but-illegible | mixed | part-derivable | not evaluable | loud |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 items | Kimi K3 + Sol (mean) | 1 | 48 | 12 | 7 | 7 | 7 | 3 | 2 | 31 | 0 | 5 |
| T1 items | Kimi K3 + Sonnet 5.5 (every) | 1 | 48 | 11 | 6 | 6 | 6 | 3 | 2 | 26 | 6 | 5 |
| T1 v2 conforming | Kimi K3 + Sol (mean) | 1 | 24 | 4 | 3 | 3 | 3 | 1 | 0 | 18 | 0 | 2 |
| T1 v3 middle | Kimi K3 + Sol (mean) | 1 | 24 | 8 | 4 | 4 | 4 | 2 | 2 | 13 | 0 | 3 |
| brief 23 nulls | Kimi K3 + Sol (mean) | 1 | 94 | 92 | 0 | 0 | 0 | 91 | 1 | 2 | 0 | 0 |
| brief 23 nulls | Kimi K3 + Sonnet 5.5 (every) | 1 | 94 | 87 | 0 | 0 | 0 | 86 | 1 | 1 | 6 | 0 |
| brief 23 nulls, control | Kimi K3 + Sol (mean) | 1 | 24 | 24 | 0 | 0 | 0 | 23 | 1 | 0 | 0 | 0 |
| brief 23 nulls, honest random | Kimi K3 + Sol (mean) | 1 | 48 | 46 | 0 | 0 | 0 | 46 | 0 | 2 | 0 | 0 |
| brief 23 nulls, honest same author | Kimi K3 + Sol (mean) | 1 | 22 | 22 | 0 | 0 | 0 | 22 | 0 | 0 | 0 | 0 |
| B3 candidates, sample 0 | Kimi K3 + Sol (mean) | 1 | 78 | 34 | 12 | 12 | 12 | 9 | 13 | 44 | 0 | 0 |

A second sample can only remove items from gate (ii) under an every-sample rule; under Sol's mean rule it can also admit one (a part credited on one sample only); it can only add items to gate (iii)'s per-reader reading. On the B3 candidates sample 0 alone certifies 12, two samples 11.

## The Wafer-served proxy for the pinned reader (Part 3's join)

- Join: 1682 of 1682 Kimi records matched; reproduces Part 3's `kimi` block: True. Read records by provider determinacy: {"b23": {"unique": 649, "ambiguous": 20, "shared_same": 19}, "b25": {"unique": 914, "ambiguous": 45, "shared_same": 33}} ('ambiguous' = paired by time order among generations of different providers; 'strict' below drops those).
- Wafer-served Kimi reads (loose / strict): brief 23 r0: 365 / 356; brief 23 r1: 64 / 63; brief 25 r0: 101 / 92; brief 25 r1: 102 / 99.

| | mode | Wafer cells | Kimi D_part > 0 | Kimi D_whole > 0 | other cells | D_part > 0 | D_whole > 0 |
|---|---|---|---|---|---|---|---|
| B3 candidates, both samples | loose | 22 | 0.818 | 0.636 | 134 | 0.448 | 0.672 |
| nulls (46), both samples | loose | 12 | 0.000 | 0.000 | 80 | 0.000 | 0.000 |
| T1 items, r0 | loose | 24 | 0.667 | 0.625 | 24 | 0.667 | 0.875 |
| brief 23 nulls, r0 | loose | 42 | 0.024 | 0.000 | 52 | 0.000 | 0.019 |
| B3 candidates, both samples | strict | 17 | 0.765 | 0.647 | 139 | 0.468 | 0.669 |
| nulls (46), both samples | strict | 9 | 0.000 | 0.000 | 83 | 0.000 | 0.000 |
| T1 items, r0 | strict | 22 | 0.727 | 0.591 | 26 | 0.615 | 0.885 |
| brief 23 nulls, r0 | strict | 37 | 0.027 | 0.000 | 57 | 0.000 | 0.018 |

Under the proxy (Kimi's values from Wafer-served cells only; the second reader's from the same samples):

| set | pair (second reader's rule) | k | items | pass (ii) | certified (iii, any) | same sample | both, both | quiet-but-illegible | mixed | part-derivable | not evaluable | loud |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| b3 candidates (11 with both cells on Wafer) | Kimi K3 Wafer + Sol (mean), loose | 2 | 11 | 1 | 0 | 0 | 0 | 1 | 0 | 10 | 0 | 0 |
| nulls 46 (5 with both cells on Wafer) | Kimi K3 Wafer + Sol (mean), loose | 2 | 5 | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| b3 candidates, r0 (11 Wafer cells) | Kimi K3 Wafer + Sol (mean), loose | 1 | 11 | 2 | 1 | 1 | 1 | 0 | 1 | 9 | 0 | 0 |
| b3 candidates, r1 (11 Wafer cells) | Kimi K3 Wafer + Sol (mean), loose | 1 | 11 | 1 | 0 | 0 | 0 | 1 | 0 | 10 | 0 | 0 |
| nulls 46, r0 (7 Wafer cells) | Kimi K3 Wafer + Sol (mean), loose | 1 | 7 | 7 | 0 | 0 | 0 | 7 | 0 | 0 | 0 | 0 |
| nulls 46, r1 (5 Wafer cells) | Kimi K3 Wafer + Sol (mean), loose | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| T1 retest items (2 both on Wafer) | Kimi K3 Wafer + Sol (mean), loose | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |
| T1 items, r0 (24 Wafer cells) | Kimi K3 Wafer + Sol (mean), loose | 1 | 24 | 6 | 3 | 3 | 3 | 2 | 1 | 15 | 0 | 3 |
| T1 items, r0 (24 Wafer cells) | Kimi K3 Wafer + Sonnet 5.5 (every), loose | 1 | 24 | 5 | 3 | 3 | 3 | 2 | 0 | 12 | 4 | 3 |
| b3 candidates (6 with both cells on Wafer) | Kimi K3 Wafer + Sol (mean), strict | 2 | 6 | 1 | 0 | 0 | 0 | 1 | 0 | 5 | 0 | 0 |
| nulls 46 (3 with both cells on Wafer) | Kimi K3 Wafer + Sol (mean), strict | 2 | 3 | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 |
| b3 candidates, r0 (7 Wafer cells) | Kimi K3 Wafer + Sol (mean), strict | 1 | 7 | 2 | 1 | 1 | 1 | 0 | 1 | 5 | 0 | 0 |
| b3 candidates, r1 (10 Wafer cells) | Kimi K3 Wafer + Sol (mean), strict | 1 | 10 | 1 | 0 | 0 | 0 | 1 | 0 | 9 | 0 | 0 |
| nulls 46, r0 (5 Wafer cells) | Kimi K3 Wafer + Sol (mean), strict | 1 | 5 | 5 | 0 | 0 | 0 | 5 | 0 | 0 | 0 | 0 |
| nulls 46, r1 (4 Wafer cells) | Kimi K3 Wafer + Sol (mean), strict | 1 | 4 | 4 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 0 |
| T1 retest items (1 both on Wafer) | Kimi K3 Wafer + Sol (mean), strict | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| T1 items, r0 (22 Wafer cells) | Kimi K3 Wafer + Sol (mean), strict | 1 | 22 | 5 | 2 | 2 | 2 | 2 | 1 | 14 | 0 | 3 |
| T1 items, r0 (22 Wafer cells) | Kimi K3 Wafer + Sonnet 5.5 (every), strict | 1 | 22 | 4 | 2 | 2 | 2 | 2 | 0 | 11 | 4 | 3 |

Kimi part credit by provider and precision (brief 23, part reads on both samples; the scorer's pass mean > 0):

| provider | T1 part reads (rubric) | credited | share | brief 23 null part reads (false target) | credited |
|---|---|---|---|---|---|
| InferenceNet|FP4 | 16 | 3 | 0.188 | 28 | 0 |
| Sail Research|FP4 | 57 | 13 | 0.228 | 89 | 0 |
| Wafer|MXFP4 | 101 | 40 | 0.396 | 225 | 1 |

Brief 25's candidates by provider and sample are Part 3's table (in the JSON); every brief 25 null cell has D_part = 0, so no provider gives false credit there. In brief 23's nulls Wafer credited 1 of 225 part reads against the false target, so Wafer's false credit is not exactly zero across both briefs; the zero-false-credit clause of E0-7's rule governs only the fallback, which is not needed.

**Pin (E0-7):** Wafer at MXFP4 if available, else the deployment with the highest part credit at zero false credit in Part 3's join (brief 29 E0-7). Wafer at MXFP4 is listed (True); the probe was served by Wafer at mxfp4 (on the pin: True), so the pin is **Wafer at MXFP4** and the fallback ranking is not needed.

## Figures that need a new reading (estimates; nothing run)

- **E1, T1 at two samples:** brief 23's r1 on the T1 items that have one sample, under brief 23's three readers: 38 items, 152 reads per reader; reads kimi $0.90, sol $0.40, sonnet55 $0.45, scoring $1.49; about **$3.23**.
- **E2, the pinned reader at two samples:** Kimi K3 pinned to Wafer at MXFP4 (E0-7), two samples per item and condition, on the B3 candidates, the 46 nulls and the T1 items; the second readers' existing two samples stand for brief 25's sets: 172 items, 1376 Kimi reads $9.98, scoring $4.30; about **$14.29** (the T1 rows also need E1's second-reader samples).
- **E3, gate (i)'s second session:** gate (i)'s second certification rater session (a fresh Sonnet 5 session under the rubric); a session, not priced from these files; 378 statements (144 T1, 234 candidates).
- Basis: per-read and per-score means from the caches ({"b23:kimi": 0.005891, "b23:sol": 0.002611, "b23:sonnet55": 0.002939, "b25:kimi": 0.007255, "b25:sol": 0.0026, "b25:sonnet55": 0.002817}; scorer {"b23": 0.001634, "b25": 0.001564}), 2 scorer passes per read; means over the caches' recorded costs; Kimi's pinned per-read cost taken at brief 25's mean (Wafer's standard endpoint lists $15/M completion, the same list price brief 25's models file holds).

## Inputs

- `work/stage3/b3/comprehension/stratum-v0.json` 6113bd8d
- `work/stage3/b3/comprehension/t1-per-part-v0.json` 143c5d79
- `work/stage3/b3/comprehension/t1-join-v0.json` 90ef9867
- `work/stage3/b3/comprehension/openrouter-kimi-activity.csv` 7b0b0b7e
- `work/stage3/b3/power-simulation-v3c.json` 2086e72f
- `work/stage3/elicitation/certification-protocol-v0.md` 3a071bd0
- `work/stage3/legibility/cache/judge-cache.legibility.read.kimi.moonshotai_kimi-k3.jsonl` 5a043dcb
- `work/stage3/legibility/cache/judge-cache.legibility.route.kimi.moonshotai_kimi-k3.jsonl` 8458b468
- `work/stage3/b3/comprehension/cache/judge-cache.legibility.read.kimi.moonshotai_kimi-k3.jsonl` c53dcae0
- `work/stage3/b3/comprehension/cache/judge-cache.legibility.route.kimi.moonshotai_kimi-k3.jsonl` 1ef299cc
- `work/stage3/legibility/cache/judge-cache.legibility.score.anthropic-claude-sonnet-5.jsonl` bf86c838
- `work/stage3/b3/comprehension/cache/judge-cache.legibility.score.anthropic-claude-sonnet-5.jsonl` 7462ac06
- `work/stage3/legibility/cache/judge-cache.legibility.read.sol.us-openai-gpt-6-sol.jsonl` 39c09c25
- `work/stage3/legibility/cache/judge-cache.legibility.read.sonnet55.global-anthropic-claude-sonnet-5-5.jsonl` d2e2e981
- `work/stage3/b3/comprehension/cache/judge-cache.legibility.read.sol.us-openai-gpt-6-sol.jsonl` 8f8f157a
- `work/stage3/b3/comprehension/cache/judge-cache.legibility.read.sonnet55.global-anthropic-claude-sonnet-5-5.jsonl` 2ff6bb9c
- `work/stage3/elicitation/kimi-pin-probe-v0.json` 1c5dbeab
- Part 3's script `work/checks/stage3_b3_power_v3c.py` 2c1cf8cf (its `fingerprint_join`, imported unchanged)

