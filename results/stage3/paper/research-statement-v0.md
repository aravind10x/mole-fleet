# Research statement v0: which fleet monitors does splitting a change across agents defeat?

*For Aravind's conversations. Derived from the paper's outline v1 (`work/paper/outline-v1.md`, with its dated note). Every number is in the frozen manifest (`work/stage3/b0/frozen-tables.json`, 88 files) and carries its tag and file. Tags: confirmatory and exploratory as the producing plan set them; instrument means a measurement of an instrument, never an outcome; methods means the rater's certification aggregates. Two items are pending the coordinator and carry no number here: the generator's exact model id, and Part J's lift and rank-correlation figures.*

## The question

Which fleet monitors does splitting a harm across agents actually defeat, and what unit of review survives either way?

Our setting is fifty AI-operated accounts sharing an organisation's documents: runbooks, guides, a checklist and a README. Per-agent monitors score an account's day, or an author's own changes to a document. A composed view reviews a document's whole diff. The deployer has a fixed review budget. A group of accounts splits a harmful change into parts, and each part is meant to look routine.

## The theory

Write a per-agent monitor's score over an agent's actions as s. Splitting the actions into parts gains the attacker s(whole) minus the largest s(part).
- **Max-type signals** score a set by its most visible element. Splitting cannot help against them.
- **Superadditive signals** respond to combination, to volume, or to both ends of a dependency. Splitting helps against them.
- **Sub-additive signals** are diluted by honest cover. Against them the attacker's lever is cover, not splitting.

The claim follows from this: collusion pays exactly against superadditive per-agent signals; content judges on this substrate look max-type; and the defence that survives either way is review at the unit where the harm composes. One agent spreading a change across documents or days is a different case, fragmentation across artifacts, and is named as such wherever it appears.

## What we have measured

**1. A change is caught when it holds the most visible statement.** An author's highest rater score predicts the per-author flag in 11 of 12 judge, view and planting cells. Volume adds ΔAUC 0.005 to 0.067 beyond it (exploratory, in-sample; `b0-results.md`, Z2). This is to be confirmed prospectively in B3.

**2. It is not caught on how many agents applied it.** The earlier splitting effect, v1's, was excluded as an artefact of the old inserter's edit volume: DiD 0.083 [−0.125, 0.292] under Sonnet 5, against the old inserter's 0.458 (confirmatory; `replant-results.md`). Under the theory's own headroom clause there is no reading at headroom yet. The Sonnet re-plant margin is 0.080 against 0.3. The one stratum at headroom, Opus 4.8 on the re-plant, reads DiD 0.250 [0.000, 0.500], inconclusive (exploratory; `b0-results.md`, Z2). These two findings have different standing and are stated separately.

**3. The composed view's level is the judge-robust quantity.** On routine changes, four judges from three families recall 0.344, 0.328, 0.406 and 0.391 of composed documents at their own 10 percent honest rule (Sonnet 5, GLM 5.3, Opus 4.8, GPT-6 Sol). Their sham rate is at or under 0.078 (exploratory; `extra-judge-results.md`, R1). The per-author view is not judge-stable.

**4. Splitting pays against superadditive signals, as seen in rules.**
- On the repaired world, a rule that flags one account changing the same entity in two documents costs 0.20 [0.11, 0.30] of honest account-windows. A cross-account version costs 0.40 [0.27, 0.53] (confirmatory world readouts; `z5-v3.md`).
- The first rule catches a one-account, two-document change by construction. Two accounts evade it.
- The judge-free edit-count rule's recall on the same-shape sham arm falls from lone to two to three authors: 0.708 [0.489, 0.874], 0.458 [0.256, 0.672], 0.250 [0.073, 0.524] (exploratory, not a pre-registered contrast; `replant-results.md`, volume rule).

**5. The top of the honest null is honest non-compliance.** Under Sonnet 5, the composed honest units at or above threshold are mostly retroactive approvals and contact or host moves, 0.633 of them (exploratory; `b0-results.md`, Z4). Opus 5.5 refused 43 of 254 honest composed units. Forty of those were on the release-gate runbook, which carries agents' records of their own release-policy bypasses (exploratory; `judge-results.md`). That is outcome separability seen from the defender's side: a monitor at a realistic honest cost cannot be more suspicious of a routine change than of honest non-compliance.

**6. The synthetic recovery test measures artifact monitoring, not collusion detection.** The document layer's gain over the per-account view is 0.075 [−0.050, 0.200] at a 10 percent budget. The gain is no larger at k = 2 than for a lone author (confirmatory; `q1q2-synthetic/results.md`).

**7. Measuring combination is the hard part.** Every figure here is an instrument look.
- Two capable writers were asked for triples whose lines are quiet alone and harmful together. One of 89 was certified, on pass 1 only; none on both passes (methods; `certification-b3.md`, J2).
- On the earlier test items, a comprehension reader can often state a change's consequence from one line alone: mean part credit 0.625 (Kimi K3) and 0.448 (GPT-6 Sol), against null credit of 0.021 or less (instrument; `instrument-v0.md`).
- A conservative comprehension-quiet stratum holds 28 of the 78 quiet candidates (instrument; `stratum-v0.md`).
- The rater's composition score appears to track the loudest line. This is a hypothesis about the max-type pattern in the rater itself, not a result about judges; its figures wait for the coordinator's methods record.

## What is running or pending

- **B3, round 1.** The pre-registered test of whether a per-agent view responds to combination beyond its loudest line. It reads 17 resolved-anchor items (design; `power-simulation-v3c.md`), with the full quiet set descriptive. Under a true max-type null the carrier reads *holds* about two times in three (pre-registration; `plan.md` §7), so round 1 is weak evidence either way.
- **B3, round 2.** The confirmatory test, on items certified by the elicitation study and never pooled with round 1.
- **B4.** A conditional design whose gate reads from B3. It asks whether content views behave superadditively across documents, and whether a workspace view recovers the split.
- **TRACK-C.** The live fragmentation test on FakeLab's commit stream, not a live collusion test. Its pre-registered size-matched test predicts that the per-commit drop from one author to three is a size effect.

## The unit of review: where the boundary is

- **A harm composed in one document:** the document is the unit.
- **A harm combined by a reader across documents:** the unit is the honest group that reads them together (B4's workspace view).
- **A harm combined by a system that no reader joins:** the unit is the dependency graph. This needs provenance monitoring, which is not built.

Recovering the coalition from interaction structure is the last resort, needed only where the composing unit cannot be observed. Our earlier grouping stages are the evidence that it is not the first layer here.

## What we do not claim

- That content judges are max-type in general; that is a hypothesis until B3 reports.
- That detection scales with judge capability, or is independent of the number of agents.
- That honest readers act on these changes; consumption is not read here.
- Any live collusion result.
- Every sentence about how narrow the middle band is, or how little splitting buys, holds "with these writers" until the elicitation study has run.
