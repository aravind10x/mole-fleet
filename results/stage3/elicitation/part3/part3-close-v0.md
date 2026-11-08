# Brief 30 Part 3, closing record: the writer course of the one-document arm (the Part 3 session, Sonnet 5.5, 2026-11-08)

Counts, aggregates and hashes only. No item text, statement or rubric text appears here or in any file named here outside the barred directories and files (`part3/writers/`, the caches, the human anchor's sheet and draw file). No B3 result, score or item was opened; STATUS.md was not read (L30). Every figure below is read by `stage3_elicitation_close.py` from the round records, the application check, the re-anchoring probe, the limits records and the anchor record.

## 1. How the course ended

Three writer rounds ran: GPT-6.1-sol rounds 1 to 3, Opus 5.5 round 1 (stopped by its provider safeguard: a recorded loss, not retried), Muse Wonder round 3 (its first, through the Cursor CLI). GPT-6.1-sol's rounds 4 to 6 were not run (brief 30 dated note 16: no quiet-but-illegible item in 303 valid, matching within writer). The edit-application check (dated note 17) then took Muse Wonder's matched effective n from 5.83 to 0, the follow-ups (note 18) put round 4 to Aravind as three options, and **the writer course ended on option C** (no round 4): the coordinator's message of 8 Nov relays Aravind's words, "Let's proceed with C, ending the writer course, with the seed set kept and the re-anchoring probe." Nothing else launches under brief 30.

## 2. The yield curve, by writer and round

| writer | round | written | valid | quiet (gate i) | gate (ii) pass | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt61sol | 1 | 24 | 20 | 13 | 3 | 2 | 0 | 1 | 9 | 7 | 1 |
| gpt61sol | 2 | 96 | 91 | 91 | 35 | 30 | 0 | 5 | 52 | 0 | 4 |
| gpt61sol | 3 | 96 | 96 | 96 | 58 | 47 | 0 | 11 | 32 | 0 | 6 |
| muse_wonder | 3 | 96 | 70 | 61 | 43 | 30 | 7 | 6 | 17 | 9 | 1 |
| opus55 | 1 | 0 | stopped | | | | | | | | |

**Cumulative (before the placement check):** `gpt61sol` written 216, valid 207, certified 79, quiet-but-illegible 0; `muse_wonder` written 96, valid 70, certified 30, quiet-but-illegible 7; **both writers: 109 certified and 7 quiet-but-illegible of 277 valid** (certified per valid 0.394, illegible per valid 0.025). Yields per valid item by writer and round are in each round record. Certified per valid item, by round: gpt61sol: 2 of 20, 30 of 91, 47 of 96; muse_wonder: 30 of 70. Quiet-but-illegible per valid item, by round: gpt61sol: 0 of 20, 0 of 91, 0 of 96; muse_wonder: 7 of 70.

## 3. The funnel by mechanism (valid items, both writers, rounds 1 to 3)

| mechanism | valid | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |
|---|---|---|---|---|---|---|---|
| composed-permission | 78 | 33 | 0 | 2 | 43 | 0 | 0 |
| conjunction | 44 | 19 | 0 | 0 | 22 | 0 | 3 |
| default-exception-schedule | 80 | 39 | 2 | 13 | 14 | 12 | 0 |
| indirection | 60 | 16 | 0 | 6 | 26 | 4 | 8 |
| order-dependency | 15 | 2 | 5 | 2 | 5 | 0 | 1 |

## 4. The placeable stock (the edit-application check, brief 26's rule unchanged)

Of 116 certified and quiet-but-illegible items, **84 are placeable and 32 are not** (`application-check-round2-states-v0.md` `d63d2696`). By writer and class, placeable: gpt61sol certified 77, muse_wonder certified 5, muse_wonder quiet_but_illegible 2. **By document and mechanism (placeable):**

| document | mechanism | certified | quiet-but-illegible |
|---|---|---|---|
| README.md | composed-permission | 8 | 0 |
| README.md | default-exception-schedule | 9 | 0 |
| README.md | indirection | 1 | 0 |
| engineering-setup.md | composed-permission | 5 | 0 |
| engineering-setup.md | conjunction | 3 | 0 |
| engineering-setup.md | default-exception-schedule | 7 | 0 |
| engineering-setup.md | indirection | 1 | 0 |
| finetune-guide.md | composed-permission | 5 | 0 |
| finetune-guide.md | default-exception-schedule | 6 | 0 |
| finetune-guide.md | indirection | 2 | 0 |
| oncall-runbook.md | composed-permission | 5 | 0 |
| oncall-runbook.md | default-exception-schedule | 7 | 0 |
| oncall-runbook.md | indirection | 1 | 0 |
| redteam-checklist.md | composed-permission | 3 | 0 |
| redteam-checklist.md | default-exception-schedule | 4 | 0 |
| redteam-checklist.md | indirection | 2 | 0 |
| redteam-checklist.md | order-dependency | 0 | 2 |
| release-gate-runbook.md | composed-permission | 3 | 0 |
| release-gate-runbook.md | conjunction | 2 | 0 |
| release-gate-runbook.md | default-exception-schedule | 5 | 0 |
| release-gate-runbook.md | indirection | 3 | 0 |

Matched effective n (note 7's rule, the 10-point band): 5.83 on all 116 items; 0.00 on the placeable stock (82 certified and 2 illegible, no stratum holding both arms).

## 5. The seed set and the re-anchoring probe

The 32 dropped items are kept as the **certified seed set**, listed by id with their line kinds in a dated section of the application-check record (2026-11-08). By writer and class: gpt61sol certified 2, muse_wonder certified 25, muse_wonder quiet_but_illegible 5. By document and mechanism:

| document | mechanism | certified | quiet-but-illegible |
|---|---|---|---|
| README.md | composed-permission | 1 | 0 |
| README.md | conjunction | 2 | 0 |
| README.md | default-exception-schedule | 0 | 2 |
| README.md | indirection | 3 | 0 |
| README.md | order-dependency | 1 | 1 |
| finetune-guide.md | composed-permission | 3 | 0 |
| finetune-guide.md | conjunction | 4 | 0 |
| finetune-guide.md | default-exception-schedule | 1 | 0 |
| finetune-guide.md | indirection | 3 | 0 |
| finetune-guide.md | order-dependency | 0 | 2 |
| oncall-runbook.md | conjunction | 4 | 0 |
| oncall-runbook.md | order-dependency | 1 | 0 |
| redteam-checklist.md | conjunction | 4 | 0 |

**Placement-adaptive anchoring, the $0 probe** (`application-check-reanchoring-v0.md` `4a6ef4da`): a re-anchoring of the replace lines to the text as it stands in a placement session's state, keeping the statement, that meets brief 26's rule unchanged exists for **2 of 32** items (0 on the clean draws), the same at the thresholds 0.5, 0.7 and 0.9; 28 have no counterpart (their target text is gone after the day's whole-document rewrite of the README, the fine-tuning guide and the on-call runbook, all on 2026-04-06), 2 have counterparts but too few valid draws. Re-certifying the 2 would cost about 0.34 USD at round 3's realised per-item rates (0.51 USD with the development stage). The seed set is for re-checking on any later world by the same module (dated note 19).

## 6. The outcome sentence (`rules-and-sentences-v0.md` section 3, one-document arm)

On the placeable stock (82 certified, 2 quiet-but-illegible, with these writers, under brief 26's placement rule) the counts select the row **"Below the floor on either arm"**, and the sentence the rules file fixes for it, brackets filled from the counts:

> Writers produced 82 certified and 2 quiet-but-illegible items, short of the floor of 12 and 12.

Scope, which the rules file requires and the counts need: with these writers (GPT-6.1-sol and Muse Wonder; Opus 5.5 stopped), one packet, one world, at n = (82, 2); the certified count is above the floor of 12 and the illegible count below it. Best writer beside: GPT-6.1-sol 77 placeable certified and no illegible item; Muse Wonder 5 placeable certified and 2 placeable illegible. Before the placement check the same counts were 109 and 7, which select the row "Below the floor on either arm". The writer course ended by Aravind's choice after round 3, not by the futility rule.

**Next action by the rules file:** A6.15 (g): B3's round 2 runs at the achieved n, with Part 3's operating characteristics at that n; where the illegible arm is short, the level contrast is descriptive and the slope carries the combination sentence, scoped to "with these writers, at n = [n]". The attacker-side round is designed from the taxonomy regardless. The no-dead-end sentence stands: work continues. The round-2 plan brief is the coordinator's.

## 7. The human anchor (protocol section 9; drawn once, seed 20261211)

Drawn from every item of rounds 1 to 3 that passes gate (i) and was read to a class (pools: certified 109, quiet_but_illegible 7, mixed 23, part_derivable 110; their ids hash `cdbddedd`), half from the certified and half from the others, 20 in all: certified 10, mixed 2, part_derivable 7, quiet_but_illegible 1; by writer gpt61sol 14, muse_wonder 6. Of the drawn certified items 8 are placeable and 2 not (placeability was not a condition of the draw: the anchor measures the readers against a person, not the placement). **The sheet** (`human-anchor-sheet-v0.md`, `cd0b8d4e`) shows Aravind, in Block A, each item's whole change as the readers see it and, in Block B, one edit of each item, with the fixed question, opaque salted ids, no class, no writer, no mechanism. **The draw file and key** (`human-anchor-draw-v0.json`, `94830358`) hold the classes by sheet id and the salt. Both were written by `stage3_elicitation_anchor.py` and **have not been opened by this session**; they stay closed to everyone, Aravind included, until he has finished (the S4 precedent, A6.18 (q)). The date is set when he scores; his answers are scored by the same scorer against the same rubric in a later step. The draw is never repeated (the script refuses).

## 8. Spend and the key ledger

| round | spend outside the writers' own tokens, USD (about) |
|---|---|
| 1 | 5.6 |
| 2 | 27.6 |
| 3 | 46.4 |
| **total, rounds 1 to 3** | **79.6** |

The edit-application check, the follow-ups, the probe and the anchor draw cost $0. The two writers' own cost is on their subscriptions (ChatGPT billing, the Cursor account). Round 3's failed rater attempt ($3.11) is inside round 3's figure. **Kimi K3 reads on OpenRouter, by key number** (limit remaining and account balance, USD):

| key | used in | limit before | limit after | limit fall | account before | account after | account fall |
|---|---|---|---|---|---|---|---|
| 1 | rounds 2 and 3 | 150.00 | 128.26 | 21.74 | 308.73 | 277.54 | 31.19 |
| 2 | round 1 | 279.79 | 278.45 | 1.34 | 89.79 | 88.45 | 1.34 |

Key 2 was the fallback and was not rotated to after round 1 (note 11); key 1's weekly limit resets Monday 2026-11-09 00:00 UTC. The account falls exceed the limit falls by other use of the account.

## 9. What is not done

- **The pair pilot and the cross-document arm** (decision 6; `cross-document-items-v0.md`, `b4-constraints-v0.md`): held by the coordinator; not started.
- **Writer rounds 4 to 6**: GPT-6.1-sol's were not run (dated note 16); Muse Wonder's round 4 was not run (option C).
- **Scoring of the human anchor**: Aravind's answers, the same scorer and rubric, and the counts by class and agreement with the readers' classes (protocol section 9); the date is set when he scores.
- **Re-certification of any re-anchored item**: not run (dated note 19: a priced option, not free).
- **The round-2 plan brief** (the coordinator's): the draw, the arms matched on writer, document and composition band, the level contrast; it carries the additions of note 19.
- **A replacement for Opus 5.5** (a recorded loss): not run.

## 10. Files (first 8 hex of sha256)

Records under `part3/`: `round-1-v0.md` 8f43f41e; `round-2-v0.md` 8c38a768; `round-3-v0.md` 23b93bd6; `forecast-after-r3-v0.md` 8287d5cd; `application-check-round2-states-v0.md` d63d2696; `application-check-round2-states-v0.json` d6ac10eb; `application-check-followups-v0.md` 17835343; `application-check-reanchoring-v0.md` 4a6ef4da; `application-check-reanchoring-v0.json` 9926e3a2; `human-anchor-record-v0.json` a53ec751.

Barrier audit: no B3 result, score or item opened; the S3 caches and `s3-applications-v0.json` never opened; STATUS.md not read; the writers' answers, traces and final messages and the human anchor's sheet and draw file never opened by this session after writing (by script only, counts and hashes); no key or `.env` value printed.
