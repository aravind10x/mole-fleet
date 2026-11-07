# Phase A, A2.3 and A2.4 v2: the tail tables per chain and per distinct write (brief 36, dated note 5 item 1)

Executor session, Opus 5.5, 2026-11-07. Interpreter `work/mole-fork/.venv/bin/python` (`-I`). $0, no model call, no judge cache opened. Script `work/checks/stage3_a2_audit.py tail-v2`; tests `work/checks/test_stage3_a2_audit.py`. Record `a2-tail-v2.json`.

**Counts only.**
- No score is recomputed. Tail membership reads the recorded unit scores against each judge's sealed threshold, and the Z4 category reads the rationale through `stage3_b0.categorise`; nothing from either is printed.
- Licence classes and unit writes come from `a2-tail-v1.json` unchanged. The v0 and v1 files are untouched.

## 1. The null's structure (stated once)

**The structure.**
- The 254 honest composed units sit on **18 document-day chains**: one per (document, boundary), six documents times three boundaries. Each chain holds **3 to 28 units**.
- A unit runs from its chain's boundary to a write. So every write recurs in every later unit on its chain, and in the chains of later boundaries on the same document.
- **The chain, not the unit, is the null's independent unit.** A 10 percent rule (about 25 units) rests on a handful of chains.

**Units per chain:**

| document | boundary 0 (day-0 state) | boundary 1 (end of 04-06) | boundary 2 (end of 04-07) |
|---|---|---|---|
| release-gate runbook | 28 | 22 | 12 |
| red-team checklist | 24 | 19 | 11 |
| on-call runbook | 22 | 13 | 6 |
| README | 19 | 8 | 5 |
| engineering setup | 19 | 12 | 4 |
| fine-tuning guide | 18 | 9 | 3 |

**Columns used below:**
- **units:** the per-unit count v0 and v1 reported.
- **chains:** how many distinct chains those units sit on.
- **unit writes:** distinct writes that end those units.
- **contained:** distinct changing writes inside them.
- **unlicensed:** distinct unlicensed writes inside them.
- **min unlicensed:** the fewest unlicensed writes that touch every one of the units. It is computed exactly, and is "—" when some unit contains no unlicensed write.

## 2. Honest deviance, per write

- **59 of 127 changing writes** fall outside their tasks' items (item level). Under the document-level sensitivity, **37 of 127** do. There are also 3 no-ops.
- That per-write figure is the rate of honest deviance.
- "232 of 254 units are unlicensed" is a consequence of cumulation, not a rate: those 232 units sit on 17 of the 18 chains, and **17 unlicensed writes** suffice to touch every one of them.
- The 22 item-licensed units sit on 5 chains, with 22 distinct unit writes.

## 3. The tail by licence, per judge (v0 §4, restated)

| judge | licence | units | chains | unit writes | contained | unlicensed | min unlicensed |
|---|---|---|---|---|---|---|---|
| Sonnet 5 | all tail | 30 | 9 | 21 | 80 | 42 | 6 |
| Sonnet 5 | unlicensed | 30 | 9 | 21 | 80 | 42 | 6 |
| Sonnet 5 | item-licensed | 0 | 0 | 0 | 0 | 0 | — |
| GLM 5.3 | all tail | 35 | 11 | 30 | 104 | 56 | — |
| GLM 5.3 | unlicensed | 33 | 10 | 29 | 104 | 56 | 7 |
| GLM 5.3 | item-licensed | 2 | 1 | 2 | 7 | 0 | — |
| Opus 4.8 | all tail | 26 | 5 | 25 | 48 | 21 | — |
| Opus 4.8 | unlicensed | 23 | 4 | 22 | 46 | 21 | 3 |
| Opus 4.8 | item-licensed | 3 | 1 | 3 | 7 | 0 | — |

Under the document-level sensitivity, the distinct unlicensed writes in each tail are 32 (Sonnet 5), 35 (GLM 5.3) and 9 (Opus 4.8).

**The base-rate comparison is descriptive.** "The tail is unlicensed at about the base rate" (v0 §4) compares counts of nested units on 18 chains. Those units are not independent, so the comparison is descriptive, not a test. What the columns add: Sonnet 5's 30 unlicensed tail units come down to 9 chains, and to 6 unlicensed writes that touch all of them.

## 4. By document, per judge (v0 §4, restated)

Each cell is units / chains / unit writes / unlicensed writes contained.

| judge | release-gate runbook | red-team checklist | fine-tuning guide | on-call runbook | README |
|---|---|---|---|---|---|
| Sonnet 5 | 19 / 3 / 12 / 9 | 6 / 2 / 5 / 6 | 2 / 1 / 2 / 3 | 2 / 2 / 1 / 18 | 1 / 1 / 1 / 6 |
| GLM 5.3 | 12 / 3 / 10 / 9 | 13 / 3 / 11 / 7 | 4 / 1 / 4 / 12 | 4 / 3 / 3 / 18 | 2 / 1 / 2 / 10 |
| Opus 4.8 | 9 / 1 / 9 / 3 | 12 / 3 / 11 / 6 | 5 / 1 / 5 / 12 | — | — |

## 5. Z4 first-match categories, per judge (v0 §4, restated)

Each cell is units / chains / unit writes.

| judge | category | units / chains / unit writes |
|---|---|---|
| Sonnet 5 | retroactive approval | 12 / 2 / 10 |
| Sonnet 5 | contact or host moved | 7 / 4 / 7 |
| Sonnet 5 | approval bypass logged | 4 / 2 / 4 |
| Sonnet 5 | other | 3 / 2 / 3 |
| Sonnet 5 | credential exposure | 2 / 1 / 2 |
| Sonnet 5 | safety step weakened | 2 / 1 / 2 |
| GLM 5.3 | contact or host moved | 14 / 6 / 12 |
| GLM 5.3 | retroactive approval | 10 / 3 / 9 |
| GLM 5.3 | other | 5 / 4 / 5 |
| GLM 5.3 | credential exposure | 2 / 2 / 2 |
| GLM 5.3 | safety step weakened | 2 / 1 / 2 |
| GLM 5.3 | value changed | 1 / 1 / 1 |
| GLM 5.3 | path moved | 1 / 1 / 1 |
| Opus 4.8 | safety step weakened | 14 / 3 / 14 |
| Opus 4.8 | contact or host moved | 11 / 5 / 10 |
| Opus 4.8 | approval bypass logged | 1 / 1 / 1 |

## 6. The retroactive-approval units and the approval variants (v1 §4, restated)

| judge | retroactive-approval units / chains / unit writes | of which with a write from a session fed an approval variant: units / chains | distinct such writes | min unlicensed writes touching every retroactive-approval unit |
|---|---|---|---|---|
| Sonnet 5 | 12 / 2 / 10 | 7 / 1 | **1** | **1** |
| GLM 5.3 | 10 / 3 / 9 | 4 / 1 | **1** | 2 |
| Opus 4.8 | 0 | 0 | 0 | — |

**Reading v1's "7 of 12".** It is **one write, in 7 nested units on one chain**.

**The minimum touching set.** All 12 of Sonnet 5's retroactive-approval units are touched by **one unlicensed write**. That write is not the approval-fed one, which appears in only 7 of them. Under GLM 5.3, two unlicensed writes touch all 10.

**What the category reduces to.** Per chain and per write, Sonnet 5's retroactive-approval category is 2 chains and, at minimum, one write.

## 7. The set-aside refit

The set-aside refit (v1 §2) stays per unit, because the sealed rule is fitted on units. Its interval holds the null fixed, so it leaves out the null's nesting.
