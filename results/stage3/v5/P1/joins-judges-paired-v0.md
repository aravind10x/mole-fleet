# P1: paired differences between monitors on the core (blue harness session, 2026-11-16; $0)

**Descriptive, post hoc.** Added 2026-11-16 at the coordinator's request, from recorded scores only.

- **Base:** the composed view under Opus 4.8 (the record's monitor), on the 48 routine and middle plants of the core.
- **Each other monitor:** at its own recorded 10 percent rule, paired by payload.
- **Carried and missed:** missed × uptake at the 50:50 follower mixture.
- **Miss share:** the share of the 48 the monitor did not flag.
- **Intervals:** 95 percent payload bootstrap within regime, 2,000 replicates, seed 20261113 (as `joins-v0`), with the same resamples for both members of each pair.
- **Record:** `joins-judges-paired-v0.json` and `work/checks/stage3_p1_paired.py`.

| monitor | carried and missed | minus Opus 4.8 composed [95%] | miss share | minus Opus 4.8 composed [95%] |
|---|---|---|---|---|
| Opus 4.8, composed view (base) | 0.295 | | 0.438 | |
| GPT-6 Sol, composed view | 0.431 | +0.135 [+0.003, +0.271] | 0.562 | +0.125 [-0.021, +0.271] |
| GLM 5.3, composed view | 0.455 | +0.160 [+0.045, +0.271] | 0.604 | +0.167 [+0.042, +0.292] |
| Sonnet 5, composed view | 0.615 | +0.319 [+0.177, +0.462] | 0.729 | +0.292 [+0.125, +0.458] |
| Opus 4.8, per-agent view | 0.431 | +0.135 [+0.021, +0.257] | 0.583 | +0.146 [+0.021, +0.271] |

The levels equal `joins-v0.md`'s raw figures for the same monitors.

**What the table supports:**
- **Carried and missed:** each of the other three judges, and the per-agent view, is higher than the composed view under Opus 4.8. All four intervals exclude zero, GPT-6 Sol's only just (lower end +0.003).
- **Miss share alone:** GLM 5.3, Sonnet 5 and the per-agent view miss more. GPT-6 Sol's difference, +0.125 [−0.021, +0.271], does not exclude zero, so on misses alone "Sol misses more" is not shown at this size.
