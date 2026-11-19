# Harm needs no collusion: the honest agent is the accomplice

*In AI agent fleets that share documents, an attacker needs one quiet change and no accomplice. An honest agent whose work needs the changed line acts on it four times in five, and a third of the time it acts on a change the monitor missed.*

This branch (`stage3`) of a fork of [MOLE](https://github.com/aashiqmuhamed/mole) (Muhamed and Smith, [arXiv 2609.06966](https://arxiv.org/abs/2609.06966)) carries the code and the count-level records behind the post above. The front page is [README.md](README.md); this file is the fuller guide.

- **The post:** [the published post](https://docs.google.com/document/d/14BTLdAXSXc7dqLPPDqhLPtD32f2yBQ-L8-iCx739Udk/)
- **This state:** the tag `note-v1` names the state of this repository that the post's figures were checked against. The branch may move on; the tag does not.

Upstream's code is unchanged on `master`, the fork's default branch; everything the study added is listed in [What changed from upstream](#what-changed-from-upstream).

## What was run

- **An organisation.** MOLE in lab mode: fifty AI-operated accounts, one generator model (Kimi K2.6), three days of honest work on six shared documents.
- **Plants.** Small false changes to one item of one document, made by one account in ordinary-looking edits and inserted by script into sessions that had read the document. 56 plants: 48 quiet (24 routine, 24 middle) and 8 alarming.
- **A monitor.** A judge model reads a document's combined changes over a window and is held to a fixed share of honest work it may flag (10 percent), with the threshold fitted on 254 honest units.
- **Followers.** Fresh agents (Kimi K2.6 and GPT-6 Sol) given the frozen documents, a search tool, the edit history, a colleague to ask and a task that needs the changed item, beside a clean copy. A script scores whether planted content reached a logged action; two audits read the runs.
- **Further blocks.** Topic-only tasks, honest tasks from the organisation's bank, a single planted line instead of the whole plant, a warned follower, an explain-first judge, other judges, and the honest-deviance tables on MOLE's released corpora.
- **The two addenda of 19 Nov.** A monitor on the agent that acts: the recorded follower runs scored a second time, each run's task and whole logged run read by one judge (check AM; no new follower runs). And the document monitor told what to look for: one paragraph added to its prompt, scored against a fresh baseline at the same budget (check TP).

The design of each block was filed before its runs; the filed designs and results are in `results/stage3/v5/` (`FT/`, `P0/` to `P3/`, `ETJ/`, `S3/`, `SS/`, `AM/`, `TP/`).

Main code, in `scripts/stage3/`:

| what | module |
|---|---|
| follower harness and runners | `stage3_ft_harness.py`, `stage3_ft_run.py`, `stage3_p2_harness.py`, `stage3_p2_run.py` |
| joins and results | `stage3_ft_join.py`, `stage3_p2_d_join.py`, `stage3_p2_w.py`, `stage3_p2_h.py`, `stage3_p2_completion.py` |
| explain-first judge and the frozen-state score | `stage3_etj.py`, `stage3_p0_frozen_score.py` |
| honest deviance on MOLE's corpora | `stage3_s3_deviance.py`, `stage3_s3_run.py`, `stage3_s3_upstream.py` |
| single planted line, and its post hoc audit | `stage3_ss_neg.py`, `stage3_ss_neg_run.py`, `stage3_ss_repeat.py` |
| the 19 Nov addenda | `stage3_am.py` (monitor on the agent that acts), `stage3_tp.py` (the document monitor told what to look for) |

Each module except the S3 driver `stage3_s3_run.py` has its test beside it (`test_<module>.py`), run by module name: `cd scripts/stage3 && python -m pytest -q test_stage3_ft_join.py`. On a fresh clone, the tests of the joins and results pass: `stage3_ft_join`, `stage3_p2_d_join`, `stage3_p2_w`, `stage3_p2_h`, `stage3_p0_frozen_score` and `stage3_s3_deviance`. So do all 150 of upstream's test modules. Many other stage-3 tests were written in the project's own layout. They read files that are not in this repository, such as the planted stock still unused and the scorers written by the side that planted, so they fail outside it. That does not affect the note's numbers, which are reproduced from the records below.

## Reproducing the note's numbers

Every figure in the published post maps to a record: [`note/NUMBERS-v1.md`](note/NUMBERS-v1.md) is the table, `note/numbers-v1.json` the machine-readable map. Each row names the record, the line that holds the figure and the trace row it comes from. The post rounds to two decimals; the records keep more places, and the checker accepts a record figure that rounds to the post's.

```bash
python note/numbermap.py --map note/numbers-v1.json check --no-pytest   # every row: record present, line found, figure in it (standard library only)
python note/numbermap.py --map note/numbers-v1.json show T617           # print the record lines behind one row
```

A few rows are not records of this repository, and the table says which and why:
- figures from external sources (other papers' budgets, citation years and section numbers);
- FakeLab's figures, published with its authors' agreement, whose source files are not released;
- one count whose record belongs to the live run's planning files.

The figures are drawn from the same records. Each plotted value is listed with its record and exact string in `note/figures/figure_data_v10.py` (with the v0.9 and v0.8 layers it builds on):

```bash
pip install matplotlib pytest
cd note/figures && python make_figures_v10.py && python -m pytest -q test_figures_v10.py
```

`python note/numbermap.py --map note/numbers-v1.json check` runs both. `note/numbers-v0.json` and `note/NUMBERS.md` are the map of an earlier draft, kept as they were. This reproduces the note from its count-level records. Re-running the model calls is not part of it: they need paid model access and give a fresh draw, not the recorded one.

Thresholds, tie shares and scores in the records are reported results of finished runs.

## What is here and what is not

This repository holds the code, the count-level records behind every figure in the note, and the planted changes used in this and the earlier rounds, including the 56 the note's headline rests on. It withholds the planted stock that has not been used yet, the agents' transcripts, and a collaborator's unpublished material. Records keep the file paths they were written with.

FakeLab's figures in the post are published with its authors' agreement; its code and files are not in this repository, so the number map lists those figures as held. No API key is in the repository or its history; `.env` files are ignored.

## A map of `results/stage3/`

**The note's records.** The number-to-record table cites only these:

| path | what it holds |
|---|---|
| `v5/FT/` | the follower test: design, harness checks, outcomes, results |
| `v5/P0/` | the audit tables, the consequence classes and the frozen-state score |
| `v5/P1/` | the joins of follower outcomes with monitor flags, and the paired judge comparison |
| `v5/P2/` | blocks D (topic-only tasks), W (warned follower), H (honest tasks) and Z (dose): designs, seals, outcomes, results |
| `v5/P3/` | how long plants live and how often honest work uses an item |
| `v5/ETJ/` | the explain-first judge against a fresh baseline |
| `v5/S3/` | honest deviance on MOLE's released corpora (public table) |
| `v5/SS/` | the single planted line, its post hoc audit and the repeat table |
| `v5/AM/` | addendum 1: a monitor on the agent that acts (design, frozen prompts, scores, analysis, result) |
| `v5/TP/` | addendum 2: the document monitor told what to look for (design, frozen prompts, scores, analysis, result) |
| `v5/NOTE/` | the post's computations and the fact files it cites |
| `b0/frozen-tables.json` | the frozen manifest: every record the paper draws on, with its hash and tag |
| `phase-a/a2-tail-v*.md` | honest writes outside their tasks, and the honest tail under each judge |
| `rater-07s/rater-honest-reference.md` | how a rater scores honest edits against routine and middle plants |

**Earlier rounds, kept for the record.** Names and the manifest's tags only:

| path | earlier round | manifest tags |
|---|---|---|
| `t1/`, `t1v2/`, `t1v3/`, `t1-replant/` | the T1 rounds of plants and monitor scores, and their re-plant | confirmatory |
| `t1k-rater/` | a rater check on the T1 plants | confirmatory, exploratory |
| `b0/` (other files) | the B0 round's results | exploratory |
| `b1/` | the B1 judge round | confirmatory |
| `b3/` | the B3 round on splitting a plant across agents | methods, instrument, design, pre-registration, confirmatory, exploratory |
| `b4/`, `b4r/` | the B4 design and its B4-R world | design; confirmatory |
| `phase-a/` (other files), `phase-b/` | phases A and B of the earlier plan | descriptive, prior art; methods, pre-registration, descriptive, sensitivity |
| `q1q2-synthetic/` | the Q1 and Q2 judge studies on synthetic plants | exploratory, confirmatory, sensitivity, methods |
| `rater-07s/` (other files) | a rater-composition study | exploratory, sensitivity |
| `legibility/` | a legibility instrument | instrument |
| `pilot/` | a pilot | exploratory, sensitivity |
| `prefix/` | prefix units used by the S3 tables | methods |
| `elicitation/` | the elicitation and rating of plants | not in the manifest |
| `cohort-examples/`, `find-the-plant/` | examples built for a demonstration | exploratory |
| `bank-reweight/`, `s5c/`, `views/`, `scores/`, `rehearsal/`, `gitlab-smoke-logs/`, `review-07f/`, `paper/` | smaller earlier checks, rehearsals, logs and early drafts | not in the manifest |
| 44 loose files | earlier rungs | one is in the manifest (exploratory) |
| `v5/LIVE/` | readiness checks for a later live run; nothing from that run is reported | not in the manifest |

`results/stage0/` to `results/stage2b/` are earlier stages from before this study's design.

## Licence and upstream

MOLE is Apache-2.0. Upstream's `LICENSE` and `CITATION.cff` are kept unchanged, and upstream's README is kept byte for byte as [README-MOLE.md](README-MOLE.md) (renamed, with its history); `README.md` is this study's front page. Upstream ships no `NOTICE` file. If you use the benchmark, cite MOLE as `CITATION.cff` says; to cite the post, see [README.md](README.md#how-to-cite).

### What changed from upstream

`master` is a pristine copy of upstream (`2a4765b`). `stage3` adds the study's code and records and modifies some upstream files (lab mode, the audit log, the generator and state backends, and their tests). To list every changed upstream file, as Apache-2.0 section 4(b) asks:

```bash
git diff --name-status 2a4765b note-v1 -- . ':!results' ':!scripts/stage3' ':!note' ':!NOTE.md'
```
