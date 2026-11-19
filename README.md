# Harm needs no collusion: the honest agent is the accomplice

**Code and records behind [the published post](https://docs.google.com/document/d/14BTLdAXSXc7dqLPPDqhLPtD32f2yBQ-L8-iCx739Udk/).** MOLE's own README, unchanged: [README-MOLE.md](README-MOLE.md).

This repository is a fork of [MOLE](https://github.com/aashiqmuhamed/mole), an open benchmark of insider threats in AI agents. Branch `stage3` carries the code and the count-level records behind a post about planted changes in shared documents. The post finds that in a simulated organisation of fifty AI agents sharing six documents, an honest agent whose work needs a quietly changed line acts on it four times in five, and a third of the time it acts on a change the document monitor missed.

## Who did what

- **This study** is by Aravind ([aravind10x](https://github.com/aravind10x)).
- **MOLE** is the benchmark of Aashiq Muhamed and Virginia Smith, Carnegie Mellon University ([arXiv 2609.06966](https://arxiv.org/abs/2609.06966), [code](https://github.com/aashiqmuhamed/mole), [data](https://huggingface.co/datasets/forgelab/mole)). Their code as first copied into this fork is commit `050d07f` (their commit `702199e`), an ancestor of every branch here; everything above it is this project's, and [NOTE.md](NOTE.md#what-changed-from-upstream) gives the command that lists what changed. MOLE is Apache-2.0 ([LICENSE](LICENSE)), and [CITATION.cff](CITATION.cff) is theirs.

## What is here

| what | where |
|---|---|
| the study's code: the harness, the monitors, the joins and their tests | `scripts/stage3/` |
| the count-level records behind the post's figures | `results/stage3/v5/`; `results/stage3/b0/frozen-tables.json` is the manifest of the records the study draws on, each with its hash |
| the planted changes used in this and the earlier rounds, including the 56 the post rests on | earlier rounds' folders under `results/stage3/` |
| the map from every figure in the post to its record, and the figures' script | `note/` |
| the full method: every filed computation, the audit rules and their completions | [note/methods-v1.0.md](note/methods-v1.0.md) |
| the full guide: what was run, a map of the folders, what changed from upstream | [NOTE.md](NOTE.md) |

**Check the post's figures from a fresh clone** (Python 3.9 or later; the check itself needs nothing else):

```bash
git clone --branch note-v1 https://github.com/aravind10x/mole-fleet.git && cd mole-fleet
python note/numbermap.py --map note/numbers-v1.json check --no-pytest
pip install matplotlib pytest
cd note/figures && python make_figures_v10.py && python -m pytest -q test_figures_v10.py
```

`numbermap.py` checks that each figure's record is present and that the record holds the figure. The last two lines redraw the post's figures from the records and check every plotted value. [note/NUMBERS-v1.md](note/NUMBERS-v1.md) lists every figure with its record. It marks the few whose source is not in this repository: other papers' figures and FakeLab's files.

## What is not here

The repository withholds the planted stock that has not been used yet, the agents' transcripts, and a collaborator's unpublished material. FakeLab's figures in the post are published with its authors' agreement; its code is not released here, at their request. No API key is in the repository or its history. Records keep the file paths they were written with.

## Which version matches the post

The tag [`note-v1`](https://github.com/aravind10x/mole-fleet/tree/note-v1) names the state of this repository that the post's figures were checked against. Branch `stage3` may move on; the tag does not.

## How to cite

The post:

```bibtex
@misc{aravind2026harm,
  author       = {Aravind},
  title        = {Harm needs no collusion: the honest agent is the accomplice},
  year         = {2026},
  howpublished = {\url{https://docs.google.com/document/d/14BTLdAXSXc7dqLPPDqhLPtD32f2yBQ-L8-iCx739Udk/}},
  note         = {Code and records: \url{https://github.com/aravind10x/mole-fleet}, tag note-v1}
}
```

If you use the benchmark itself, cite MOLE as [CITATION.cff](CITATION.cff) and [README-MOLE.md](README-MOLE.md) give it (Muhamed and Smith, 2026).
