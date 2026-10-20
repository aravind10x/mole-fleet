# Stage 3 blue-prep scripts (brief 07)

Verbatim copies of `work/checks/stage3_*.py` and their tests at the commit named in
`results/stage3/prep-report.md`. The canonical copies live in `work/checks/` (project root,
outside this repository) and import their siblings (`grouping_measure.py`, `mole_corpus.py`,
`judge_client.py`) from there; run them from `work/checks/` with `-I`. The sha256 of each
file is recorded beside its numbers in the prep report. `testpaths = ["tests"]` keeps pytest
from collecting the test copies here.
