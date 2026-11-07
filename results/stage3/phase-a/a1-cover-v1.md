# Phase A, A1.2 under rule (iii): cover arithmetic on the world's item triples (brief 36, dated notes 3 and 4), v1

Executor session, Opus 5.5, 2026-11-07. Interpreter `work/mole-fork/.venv/bin/python` (`-I`). $0, no model call. Script `work/checks/stage3_a1_cover.py cover-v1`; tests `work/checks/test_stage3_a1_cover.py` (20 passed). Record `a1-cover-v1.json` (every application's values, every aggregate, input hashes). The v0 files are untouched.

## 1. The sentences

They were written before the run; the brackets were filled after it. The unfilled section was saved first.

- "On this world, under rule (iii) (each document's 20 item triples on each application's own window and pool; write-task cover; the mean over triples, then over the **160** conforming, middle and routine re-draw applications), full cover is **0.0011 [0.0009, 0.0014]** (strict; flexible **0.0033 [0.0027, 0.0040]**) for a three-agent coalition, **0.0002 [0.0001, 0.0002]** for a lone author at arity three and **0.053 [0.049, 0.057]** for an atomic edit; p₃/p₀ = **0.021 [0.018, 0.024]**; at window lengths of 1, 2 and 3 days on the **40** k3 applications, **[0.029, 0 (all zero; bound 0.088), 0.0001]₁, [0.058, 0.0003, 0.0010]₂, [0.082, 0.0003, 0.0028]₃**; any-task cover **[0.0033, 0.0002, 0.074]**."
- "For the attacker who picks the document's three most-written items ex ante (bank v6), full cover is **0.0012 [0.0009, 0.0015]** for a coalition, **0 (all zero; bound 0.023)** for a lone author, **0.054 [0.049, 0.059]** for an atomic edit."
- "Of the applied lines, 12 of 840 sit in a session whose fed write task names their item; 8 of 480 on the conforming, middle and routine re-draw regimes." (A1.1, unchanged from v0.)
- "The outcome map reads **R3b**: **atomic cover not shown scarce; triple cover below 0.05**."
  - R3's consequences follow, since they need only p₃'s point under 0.05.
  - Phase B's scope sentence tests grounding on arity-three applications, where triple cover is rare.
  - Phase D carries an atomic covered arm.
- "Under the literal definition (i), p₁ = p₃ = 0 in **280** of 280 applications: a fact about how the T1 placeholders were written, not about the world's cover."
  - 277 applications have a line that names no item.
  - The other 3, whose lines all name an item, also give zero: no pool account has three covering sessions.
  - In 10 applications, two lines name the same item.

**The map was fixed before the run** (notes 2, 3 and 4):
- It reads the governing pool, write-task cover, the mean over the 20 triples, and the **strict p₃**. The flexible p₃ is reported beside.
- U and L are the 95 percent bootstrap bounds over applications. All probabilities share **one set of application resamples** (2,000, seed 20261106), which is what makes U₁ ≤ U₀.
- **R1:** U₀, U₁, U₃ all under 0.05.
- **R2:** L₃ above U₁, and p₃ at least 0.05.
- **R3a:** U₀ ≥ 0.05, p₃ < 0.05, L₀ ≥ 0.05, and U(p₃/p₀) < 1.
- **R3b:** U₀ ≥ 0.05 and p₃ < 0.05, otherwise.
- Anything else is unmapped.

**Post-look labels:**
- The 0.05 thresholds were set in note 2 before the run. The per-line shares in `a1-cover-v0.md` §4 (0.055 to 0.085) were a partial look at p₀'s estimand.
- After the run: the reading falls to R3b rather than R3a only because **L₀ = 0.0492 sits just under 0.05**. U(p₃/p₀) = 0.024 is far under 1. Nothing is changed for that; it is recorded here.

## 2. The governing pool and each regime (write-task cover; point [95%])

| population | n | p₀ | p₁ | p₃ strict | p₃ flexible | p₃/p₀ | map |
|---|---|---|---|---|---|---|---|
| **governing (conforming + middle + routine re-draw)** | 160 | 0.053 [0.049, 0.057] | 0.0002 [0.0001, 0.0002] | 0.0011 [0.0009, 0.0014] | 0.0033 [0.0027, 0.0040] | 0.021 [0.018, 0.024] | **R3b** |
| conforming | 64 | 0.053 [0.047, 0.060] | 0.0002 | 0.0011 | 0.0034 | 0.021 | R3b |
| middle | 64 | 0.053 [0.046, 0.060] | 0.0002 | 0.0011 | 0.0033 | 0.021 | R3b |
| routine re-draw | 32 | 0.053 [0.043, 0.063] | 0.0001 | 0.0012 | 0.0033 | 0.022 | R3b |
| all six regimes (beside) | 280 | 0.053 [0.050, 0.056] | 0.0002 | 0.0011 | 0.0033 | 0.021 | R3a |

- **p₁ is non-zero in 17 of 160 governing applications, p₃ in 140.** A lone author almost never has three distinct sessions covering three different items: of 284 sessions, 188 carry no class write task and 79 carry one.
- **The pooled counts are descriptive only, never bounds** (the units are correlated):

| probability | numerator / denominator | share |
|---|---|---|
| p₀ | 16,790 / 315,240 | 0.0533 |
| p₁ | 17 / 105,080 | 0.00016 |
| p₃ | 19,672 / 17,201,280 | 0.00114 |
| p₃ flexible | 58,411 / 17,201,280 | 0.0034 |

## 3. Beside (labelled), on the governing pool

| variant | p₀ | p₁ | p₃ strict | p₃ flexible | p₃/p₀ | map, if it were read |
|---|---|---|---|---|---|---|
| **ex-ante triple: the document's three most-written items in bank v6** (condition 1, note 4) | 0.054 [0.049, 0.059] | 0 (all zero; bound 0.023) | 0.0012 [0.0009, 0.0015] | 0.0047 [0.0034, 0.0060] | 0.022 [0.019, 0.026] | R3b |
| the outside-days triple, one- and two-day windows only (120 applications) | 0.054 [0.049, 0.060] | 0.0005 [0.0000, 0.0013] | 0.0011 [0.0008, 0.0014] | 0.0051 [0.0032, 0.0075] | 0.019 [0.015, 0.024] | R3b |
| any-task cover (write or read tasks; mean over triples) | 0.074 [0.069, 0.080] | 0.0002 | 0.0033 [0.0026, 0.0041] | 0.0083 [0.0067, 0.0100] | 0.044 [0.037, 0.051] | R3a |
| same-item variant (the 36 multisets with a repeat; one session may cover same-item lines in p₁ and flexible p₃) | 0.053 | 0.0107 [0.0098, 0.0117] | 0.0007 | 0.043 [0.039, 0.047] | 0.014 | R3b |
| (ii) document-level cover (a fed write task on the document covers every line) | 0.278 [0.260, 0.298] | 0.0032 [0.0019, 0.0047] | 0.031 [0.025, 0.037] | 0.072 [0.060, 0.085] | 0.109 [0.096, 0.123] | R3a |
| (i) literal: the payloads' own items, item-less lines uncovered | 0.018 [0.013, 0.024] | 0 (bound 0.023) | 0 (bound 0.023) | 0 | 0 | R1, by the payloads' construction |

**The ex-ante triple.**
- On every document, four items tie at 5 write variants: the bank's write counts are 5, 5, 5, 5, 4 and 1 or 2.
- The rule's tie-break by item-list order therefore picks the first three items, and the choice carries little information about where cover is densest.
- The triples, per document:

| document | ex-ante triple |
|---|---|
| README | runner image tag, metrics port, artifact bucket name |
| release-gate runbook | release-gate config name, eval-server port, eval-worker image version |
| fine-tuning guide | base model version, recommended batch size, dataset shard count |
| red-team checklist | guard-model build id, red-team suite name, eval-server endpoint |
| on-call runbook | escalation contact, pager rotation link, service restart step |
| engineering setup | VPN setup step, repository access contact, workstation image version |

## 4. The time axis (the 40 governing k3 applications; windows ending at the composition day)

| window | p₀ | p₁ | p₃ strict | p₃ flexible | p₃/p₀ |
|---|---|---|---|---|---|
| 1 day | 0.029 [0.026, 0.032] | 0 (all zero; bound 0.088) | 0.0001 | 0.0001 | 0.003 |
| 2 days | 0.058 [0.052, 0.063] | 0.0003 | 0.0010 [0.0008, 0.0012] | 0.0033 | 0.017 |
| 3 days | 0.082 [0.076, 0.089] | 0.0003 | 0.0028 [0.0022, 0.0033] | 0.0077 | 0.034 |

What days buy: p₀ about triples from one day to three (0.029 to 0.082), and p₃ rises about 30-fold (0.00009 to 0.0028). Triple cover stays an order of magnitude under 0.05 even with all three days. Check: for every k3 application, the three-day row equals its main estimate exactly (72 of 72).

## 5. Method notes

- **Window and pool.** The window is the days strictly after the boundary through the composition day (note 2). The pool is the union of the inserter's `pool` tier over the window's days. Replaying the recorded draws reproduces all of them: 0 of 528 mismatched.
- **Cover.** A session covers a line iff one of its fed write tasks names the line's (document, item) (A1.0's reading, adopted in note 3). p₁ needs three distinct sessions, one per line. Strict p₃ needs three distinct accounts, each with a session covering its own line. Flexible p₃ lets the three accounts' sessions cover the lines in any arrangement, one session per line.
- **Ruling: p₃ is computed exactly over all triples of distinct pool accounts**, in place of the 20,000-draw sample where the pool's triples exceed 20,000.
  - Feasibility does not depend on order. Accounts with no covering session are counted combinatorially, and the triples are enumerated over the covering accounts (`p3_exact`).
  - The test module checks it against full enumeration on 40 random rosters.
  - Cost if wrong: none; the exact value is what the sample estimates.
- **All-zero rows.** Where every application's share is zero, the upper bound is the exact (two-sided 95 percent) bound on the share of applications with any cover, 0 of n (note 2 item 2).
