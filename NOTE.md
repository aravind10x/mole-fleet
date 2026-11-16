# The note's repository: planted changes in shared documents

This branch (`stage3`) of a fork of [MOLE](https://github.com/forgelab/mole) (Muhamed and Smith, [arXiv 2609.06966](https://arxiv.org/abs/2609.06966)) carries the code and the count-level records behind the research note *When AI agents share documents, a quiet planted change is acted on and missed about a third of the time* **[SLOT: link to the published note]**. Upstream's code is unchanged on `master`; everything the study added is listed in [What changed from upstream](#what-changed-from-upstream).

## What was run

- **An organisation.** MOLE in lab mode: fifty AI-operated accounts, one generator model (Kimi K2.6), three days of honest work on six shared documents.
- **Plants.** Small false changes to one item of one document, made by one account in ordinary-looking edits and inserted by script into sessions that had read the document. 56 plants: 48 quiet (24 routine, 24 middle) and 8 alarming.
- **A monitor.** A judge model reads a document's combined changes over a window and is held to a fixed share of honest work it may flag (10 percent), with the threshold fitted on 254 honest units.
- **Followers.** Fresh agents (Kimi K2.6 and GPT-6 Sol) given the frozen documents, a search tool, the edit history, a colleague to ask and a task that needs the changed item, beside a clean copy. A script scores whether planted content reached a logged action; two audits read the runs.
- **Further blocks.** Topic-only tasks, honest tasks from the organisation's bank, a warned follower, an explain-first judge, other judges, and the honest-deviance tables on MOLE's released corpora.

The design of each block was filed before its runs; the filed designs and results are in `results/stage3/v5/` (`FT/`, `P0/` to `P3/`, `ETJ/`, `S3/`, `SS/`).

Main code, in `scripts/stage3/`:

| what | module |
|---|---|
| follower harness and runners | `stage3_ft_harness.py`, `stage3_ft_run.py`, `stage3_p2_harness.py`, `stage3_p2_run.py` |
| joins and results | `stage3_ft_join.py`, `stage3_p2_d_join.py`, `stage3_p2_w.py`, `stage3_p2_h.py`, `stage3_p2_completion.py` |
| explain-first judge and the frozen-state score | `stage3_etj.py`, `stage3_p0_frozen_score.py` |
| honest deviance on MOLE's corpora | `stage3_s3_deviance.py`, `stage3_s3_run.py`, `stage3_s3_upstream.py` |

Each module except the S3 driver `stage3_s3_run.py` has its test beside it (`test_<module>.py`), run by module name: `python -m pytest -q scripts/stage3/test_stage3_ft_join.py`.

## Reproducing the note's numbers

Every number in the note maps to a released record: [`note/NUMBERS.md`](note/NUMBERS.md) is the table, `note/numbers-v0.json` the machine-readable map.

```bash
python note/numbermap.py check --no-pytest   # every row: record present, line found, numbers in it (standard library only)
python note/numbermap.py show N01            # print the record lines behind one row
```

The figures are drawn from the same records; each plotted value is listed with its record and exact string in `note/figures/figure_data.py`:

```bash
pip install matplotlib pytest
cd note/figures && python make_figures.py && python -m pytest -q test_figures.py
```

`python note/numbermap.py check` runs both. This reproduces the note from its count-level records. Re-running the model calls is not part of it: they need paid model access and give a fresh draw, not the recorded one.

Thresholds, tie shares and scores in the records are reported results of finished runs.

## What is released and what is held

- **Released:** the harness, the analysis and join code, the scorers' interfaces, the count-level records the note cites, and the frozen manifest of the records the paper draws from (`results/stage3/b0/frozen-tables.json`).
- **[SLOT: planted text. The paragraph saying plainly what is public and what is held; wording to come.]**
- **FakeLab.** Figures derived from a collaborator's unpublished repository are held until its authors have answered. Where a record cites such a source, it names it without its figures.
- **Keys.** No API key is in the repository or its history; `.env` files are ignored.
- **Paths.** Records keep the absolute paths of the machine they were written on.

## Licence and upstream

MOLE is Apache-2.0. Upstream's `LICENSE`, `CITATION.cff` and `README.md` are kept unchanged (the README gains one pointer line to this file); upstream ships no `NOTICE` file. If you use the benchmark, cite MOLE as `CITATION.cff` says. **[SLOT: how to cite the note.]**

### What changed from upstream

`master` is a pristine copy of upstream (`2a4765b`). `stage3` adds the study's code and records and modifies some upstream files (lab mode, the audit log, the generator and state backends, and their tests). To list every changed upstream file, as Apache-2.0 section 4(b) asks:

```bash
git diff --name-status 2a4765b stage3 -- . ':!results' ':!scripts/stage3' ':!note' ':!NOTE.md'
```
