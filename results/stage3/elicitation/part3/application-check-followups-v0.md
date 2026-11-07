# The edit-application check's follow-ups: the retention-adjusted forecast and the line forms of the illegible items (brief 30 Part 3, 8 Nov 2026)

Written 2026-11-08T03:38:15+05:30 by the Part 3 session (Sonnet 5.5). $0, no API call, no reader, no B3 file; counts, classes, mechanism labels and content kinds only (no statement, anchor or document text is read into this file). Module `stage3_elicitation_followups.py` `0de5edd9` over `stage3_elicitation_forecast.py` `db4eb86c` (the round-3 forecast reproduces byte for byte through it: identical) and the application check `application-check-round2-states-v0.json` `d6ac10eb`. Companion to `application-check-round2-states-v0.md` `65f132a5`, which is unchanged.

## 1. The retention-adjusted forecast

**What is computed.** The after-round-3 forecast (note 12's addendum) on the items that can be placed: the stock is the 82 certified and 2 quiet-but-illegible items that pass the application check (`gpt61sol` 77 and 0, `muse_wonder` 5 and 2); its matched effective n is **0.00** (0 and 0 matched, 0 strata with both arms). Each case has Muse Wonder write rounds 4 to 6 at the cap of 96 (GPT-6.1-sol writes none, note 16), the statistic matched on the observed strata (writer x document x 10-point band; each writer's own valid items' strata resampled), its Jeffreys yields from the observed rounds, no drift, the floor rule on and off, a value on the margin of 0.5 reading as below; 40000 runs for the all-matched statistic and 8000 for the matched one, seed 20261216.

**C, no round 4:** the stock alone. Matched effective n 0.00 against the stop of 26: not reached; no later round is run, so the course ends at that value.

| case | P(stop by success), floor rule on | floor rule off | P(floor rule ends it) | reading | by round 4 alone | by round 5 | all-matched statistic, floor on |
|---|---|---|---|---|---|---|---|
| B | 0.00 | 0.00 | 0.64 | below 0.5 | 0.00 | 0.00 | 0.11 |
| A1 | 0.72 | 0.73 | 0.08 | at or above 0.5 | 0.00 | 0.23 | 0.84 |
| A2 | 0.01 | 0.01 | 0.69 | below 0.5 | 0.00 | 0.00 | 0.04 |
| A3 | 0.00 | 0.00 | 1.00 | below 0.5 | 0.00 | 0.00 | 0.00 |

- B, as planned: Muse Wonder's rounds 4 to 6 at the cap, yields as observed times its observed placeable retention.
- A1, append-only constraint: retention like GPT-6.1-sol's, yields as observed.
- A2, as A1 with the illegible yield scaled by the share of illegible items whose mechanism has an append-only precedent.
- A3, as A1 with the illegible rate of the append-only items written so far (Jeffreys).

Retention used (Jeffreys on the kept share): gpt61sol: certified 77 of 79, illegible 0 of 0; muse_wonder: certified 5 of 30, illegible 2 of 7.

**Counts after each round, the matched case (mean [p10, p90]): certified, illegible, matched effective n.**

| case | after round 4 | after round 5 | after round 6 |
|---|---|---|---|
| B | 87.3 [84, 91]; 4.3 [2, 7]; n_eff 1.2 [0, 3] | 92.7 [86, 100]; 6.6 [3, 11]; n_eff 3.3 [0, 7] | 98.0 [89, 108]; 8.9 [3, 16]; n_eff 5.8 [1, 11] |
| A1 | 111.0 [103, 119]; 9.1 [5, 14]; n_eff 8.7 [4, 14] | 140.0 [126, 154]; 16.2 [9, 24]; n_eff 20.9 [12, 31] | 168.9 [149, 189]; 23.4 [13, 35]; n_eff 33.0 [20, 48] |
| A2 | 111.0 [103, 119]; 4.0 [2, 6]; n_eff 3.6 [1, 7] | 140.1 [127, 154]; 6.1 [3, 9]; n_eff 8.1 [4, 13] | 169.2 [150, 189]; 8.1 [4, 13]; n_eff 12.4 [6, 19] |
| A3 | 111.1 [103, 119]; 2.2 [2, 3]; n_eff 1.5 [0, 3] | 140.3 [127, 154]; 2.4 [2, 3]; n_eff 2.6 [1, 4] | 169.3 [150, 189]; 2.6 [2, 4]; n_eff 3.4 [2, 6] |

**Weak points.** (a) The illegible side rests on one Muse Wonder round (7 of 70 valid), and its retention on the same round (2 of 7): both posteriors are wide, which the intervals carry. (b) Retention is a global factor, yet it is concentrated by document (the README, fine-tuning guide and on-call runbook items all drop), and the future items' strata are resampled from all the writer's valid items, so a case where the surviving documents are the ones that match is not modelled. (c) A1 to A3 assume an append-only constraint leaves the certified yield as observed; the only append-only items are GPT-6.1-sol's, and Muse Wonder has written 17 append lines of its 210, one in each of its default-exception-schedule items, never an append-only item. (d) The packet is pinned: the constraint would live in the per-round round.md. (e) Yields are held constant though round 4 is Muse Wonder's first feedback round.

## 2. The line forms: what an append-only constraint risks

**Valid items by writer, form and class** (all valid items of rounds 1 to 3; `other` is every class but certified and quiet-but-illegible):

| writer | form | valid | certified | quiet-but-illegible | other |
|---|---|---|---|---|---|
| gpt61sol | append-only | 168 | 77 | 0 | 91 |
| gpt61sol | replace-bearing | 39 | 2 | 0 | 37 |
| muse_wonder | replace-bearing | 70 | 30 | 7 | 33 |

**By mechanism and form, both writers** (the append-only precedent for each mechanism):

| mechanism | form | valid | certified | quiet-but-illegible | other | writers |
|---|---|---|---|---|---|---|
| composed-permission | append-only | 60 | 29 | 0 | 31 | gpt61sol |
| composed-permission | replace-bearing | 18 | 4 | 0 | 14 | gpt61sol, muse_wonder |
| conjunction | replace-bearing | 44 | 19 | 0 | 25 | gpt61sol, muse_wonder |
| default-exception-schedule | append-only | 60 | 38 | 0 | 22 | gpt61sol |
| default-exception-schedule | replace-bearing | 20 | 1 | 2 | 17 | gpt61sol, muse_wonder |
| indirection | append-only | 48 | 10 | 0 | 38 | gpt61sol |
| indirection | replace-bearing | 12 | 6 | 0 | 6 | gpt61sol, muse_wonder |
| order-dependency | replace-bearing | 15 | 2 | 5 | 8 | muse_wonder |

**The 7 quiet-but-illegible items.** Rule: an item could have been written as three append lines when its mechanism has an append-only precedent among the valid items; it needs a replaced line when none does. **2 could have been written as three append lines; 5 need a replaced line.**

| mechanism | illegible items | operations as written | replaced lines by content kind | append-only precedent (valid, certified, illegible) | could be three appends |
|---|---|---|---|---|---|
| default-exception-schedule | 2 | 1 append + 2 replace: 2 | procedure 4 | 60, 38, 0 | yes |
| order-dependency | 5 | 3 replace: 5 | procedure 15 | 0, 0, 0 | no |

In the converter's content kinds a replaced line is `procedure` when the line it replaces is a numbered step, so a `procedure` replaced line is a step of a sequence reworded or renumbered in place. The packet defines order-dependency by statements that "add, move, renumber or relabel steps"; an append can add a step at the end of a document or a named region but cannot move or renumber one. **What option A risks, in the study's own record:** no append-only item has been quiet-but-illegible (0 of 168 valid append-only items, written by gpt61sol) and the mechanism that yielded most of the illegible items has never been written append-only; the replace-bearing items hold 0 of 39 valid (gpt61sol), 7 of 70 valid (muse_wonder), so form and writer are not separated by these data.

## Reproduce

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_followups.py run
```
