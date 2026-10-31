**All three required fixes are fixed.** **48 tests passed; 3 data-dependent tests were deselected** to preserve the information barrier.

| Check | Result |
|---|---|
| Firth convergence | **Fixed.** Penalised-likelihood step halving is present. The sparse-document regression passes and independently matches the analytic optimum within `4.4e-8`. |
| Adoption/joint carrier consistency | **Fixed.** Adoption retains the isolated-dossier carrier; the second instrument supplies the verdict only through experiment-level floor/unfit fallback. |
| Failed trigger move | **Fixed.** Selection continues to the next candidate before the descriptive rule. The new regression test passes. |
| Live-view (a) reporting | **Partly fixed.** Rows have an n/a role and the 5-point readable summary excludes them. The **0/10-point readable lists still include them** when their numerical gates pass ([line 2108](/Users/aravind/KruxAI/tais-project-selection/work/checks/stage3_b3_power_v3.py:2108)). This is a nonblocking reporting nit. |
| MC SE and drift wording | **Fixed.** The bias table prints MC SE; the drift text identifies the 0/10-point cells as JSON-only. |

No new blocking code error found. Tests required cached NumPy 1.26.4 with SciPy 1.13.1 because the default NumPy 2 environment has an ABI mismatch. No files were changed, and no prohibited subcommands, network, judge or Docker operations ran.

**Verdict: safe to commit and run in a compatible Python environment; one optional reporting nit remains.**