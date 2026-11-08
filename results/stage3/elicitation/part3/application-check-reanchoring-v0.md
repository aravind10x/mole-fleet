# Placement-adaptive anchoring: a $0 probe on the 32 dropped items (brief 30 Part 3, 8 Nov 2026; dated note 19)

Written 2026-11-08T13:17:37+05:30 by the Part 3 session (Sonnet 5.5). $0, no API call, no reader, no re-certification, no launch, no B3 file; counts, opaque ids, mechanism labels, content kinds, document names and reason codes only. Module `stage3_elicitation_reanchor.py` `dc090476` over the application check `application-check-round2-states-v0.json` `d6ac10eb` and brief 26's draw machinery (`stage3_t1.py` `240f4ed9`).

## The question and the method

For each dropped item: does a re-anchoring of its replace lines to the text as it stands in a placement session's document state exist that keeps the statement (the anchor changes; the replacement line, the operation and the kind do not) and meets brief 26's rule unchanged (two valid draws on different days by different authors for the item; two valid draws by different authors for each of its three lines as a lone line), with the same rule on the clean draws beside? For every (day, author) the lone layout can draw (the document's write-team members active that day, not managers) and every session of that author that day, the document states a plant in the session can see (from the later of its opening and the day's last whole rewrite of the document) are read from the null corpus. Each replace statement's day-0 target line is matched to its counterpart in that state: the unique line of the best character similarity (difflib ratio), at or above a threshold; the anchor becomes that line's own beginning (the original anchor where it still resolves to that line alone, else the shortest prefix of at least ten characters that starts one line). Brief 26's `run_draw` then runs on the rewritten statements (the module's `_plant_once`, every reachable state in the session, the joint check); a (day, author) draw is valid when some session's re-anchoring passes. **The threshold is the probe's one free choice: 0.7 is the primary, the others are beside.** A match at a low threshold may be a line of a different meaning; whether an item's composed effect survives the move is not something this probe can tell, which is what re-certification would read.

## The churn, as the corpus has it

Whole-document rewrites by the corpus's honest agents, by day (the module cannot plant before a day's last whole rewrite of the document, and a rewrite replaces the text the items were written against): README.md: 2026-04-06 x1; engineering-setup.md: none; finetune-guide.md: 2026-04-06 x2; oncall-runbook.md: 2026-04-06 x1; redteam-checklist.md: none; release-gate-runbook.md: none. The draw days are 2026-04-06, 2026-04-07.

**Best similarity of each dropped replace statement's day-0 target line to any line of any document state on the draw days at or after the whole-write floor (statements):**

| document | >= 0.9 | 0.7 to 0.9 | 0.5 to 0.7 | < 0.5 |
|---|---|---|---|---|
| README.md | 0 | 0 | 0 | 26 |
| finetune-guide.md | 0 | 1 | 7 | 28 |
| oncall-runbook.md | 0 | 0 | 0 | 15 |
| redteam-checklist.md | 12 | 0 | 0 | 0 |

Over all 89 dropped replace statements: >= 0.9 12, 0.7 to 0.9 1, 0.5 to 0.7 7, < 0.5 69. No item changes class between the thresholds 0.7, 0.5, 0.9: the statements in the middle bands belong to items that have another target with no counterpart.

## Result

| threshold | items | re-anchorable (rule) | re-anchorable on the clean draws | not: a target has no counterpart | not: counterparts never together in one session | not: too few valid draws |
|---|---|---|---|---|---|---|
| 0.7 | 32 | 2 | 0 | 28 | 0 | 2 |
| 0.5 | 32 | 2 | 0 | 28 | 0 | 2 |
| 0.9 | 32 | 2 | 0 | 28 | 0 | 2 |

**At the primary threshold (0.7), re-anchorable by writer and class:** muse_wonder certified: 2.

**By document and mechanism (primary threshold; items / re-anchorable / re-anchorable on the clean draws):**

| document | mechanism | items | re-anchorable | clean |
|---|---|---|---|---|
| README.md | composed-permission | 1 | 0 | 0 |
| README.md | conjunction | 2 | 0 | 0 |
| README.md | default-exception-schedule | 2 | 0 | 0 |
| README.md | indirection | 3 | 0 | 0 |
| README.md | order-dependency | 2 | 0 | 0 |
| finetune-guide.md | composed-permission | 3 | 0 | 0 |
| finetune-guide.md | conjunction | 4 | 0 | 0 |
| finetune-guide.md | default-exception-schedule | 1 | 0 | 0 |
| finetune-guide.md | indirection | 3 | 0 | 0 |
| finetune-guide.md | order-dependency | 2 | 0 | 0 |
| oncall-runbook.md | conjunction | 4 | 0 | 0 |
| oncall-runbook.md | order-dependency | 1 | 0 | 0 |
| redteam-checklist.md | conjunction | 4 | 2 | 0 |

## What re-certification would cost

A re-anchored item is placed in the evolved text, so the instruments would read it there: the certification stage again (the certification rater sessions, the two readers at two samples, the scorer). At round 3's realised per-item rates; the development stage beside.

| threshold | items to re-certify | certification stage | with the development stage |
|---|---|---|---|
| 0.7 | 2 (muse_wonder 2) | 0.34 USD | 0.51 USD |
| 0.5 | 2 (muse_wonder 2) | 0.34 USD | 0.51 USD |
| 0.9 | 2 (muse_wonder 2) | 0.34 USD | 0.51 USD |

Per item: gpt61sol 0.184 USD (certification stage); muse_wonder 0.172 USD (certification stage). Basis: round 3's realised spend (`round-3-v0.md` section 9), certification raters over the items rated and certification reads over the items read (for Muse Wonder the gate (i) passers).

## Reproduce

```
work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_reanchor.py run
```
