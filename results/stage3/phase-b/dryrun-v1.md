# Phase B dry run v1 (brief 38 Part 1 re-run under dated note 3; pre-registration v1 sections 3, 4, 6; L17)

Record: `dryrun-v1.json` (sha256 `3ebf4066c09c251a…`). Script `stage3_phase_b_dryrun.py` sha256 `2d03a887e3be698c…`; renderers `stage3_phase_b_grounded.py` sha256 `d8767e7ca1807038…` (phase-b-grounded/v2), tests sha256 `97aa81d0d5219da4…`. Seed 20261107; 400 outer replicates per noise level, each with 2000 inner replicates on one shared cluster index set; 200 fixed-world replicates; $0, no model call, no judge cache opened. Inputs: corpus `ffc1f6cd423cae68…`, transcripts `9f6b641efa3f1323…`, bank v6 `bef08ddbdbf6efdb…`.

**What changed from v0 (note 3):** every arm Part 2 scores is a fresh paired draw, B0 included, so r₀ is the fresh B0 reading; the header gain h enters B0h and every grounded arm alike (B3's options are h and h + g); kill reads U(D_h) < m_kill with D = r − r₀ and D_net beside; separability's first branch is L(c_net) > 0 and U(c_net) ≥ D_net; headers name no account and B0h carries the in-force flag (renderers v2). All other conventions are v0's (`dryrun-v0.md`, executor's notes 1 to 12).

## The line

**kill decidable on this null.** m_kill = **0.23** on D_h (the largest value, floored to 0.01, with P(kill | g = 0.20, h = 0) ≤ 0.10 at every noise level; per-SD maxima {'5': 0.2642, '10': 0.2421, '15': 0.2302}). σ = **0.11**; δ = **0.16**.

### Opus 4.8: P(kill) at m_kill = 0.23 (kill on U(D_h); U(D) < m beside)

| SD | g=0, h=0 | g=0, h=0.05 | g=0.10 | g=0.20 | g=0.30 | mean D_h at g=0 | mean D at g=0 | U(D) < m at g=0 / g=0.20 | fixed world: g=0 / g=0.20 |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 0.97 | 0.98 | 0.41 | 0.04 | 0.01 | -0.003 | -0.004 | 0.96 / 0.04 | 1.00 / 0.00 |
| 10 | 0.87 | 0.86 | 0.42 | 0.07 | 0.01 | 0.004 | 0.005 | 0.85 / 0.06 | 0.96 / 0.02 |
| 15 | 0.78 | 0.79 | 0.45 | 0.10 | 0.01 | -0.004 | -0.000 | 0.76 / 0.11 | 0.89 / 0.03 |

Own m_kill for this judge (not used): 0.23.

### Sonnet 5: P(kill) at m_kill = 0.23 (kill on U(D_h); U(D) < m beside)

| SD | g=0, h=0 | g=0, h=0.05 | g=0.10 | g=0.20 | g=0.30 | mean D_h at g=0 | mean D at g=0 | U(D) < m at g=0 / g=0.20 | fixed world: g=0 / g=0.20 |
|---|---|---|---|---|---|---|---|---|---|
| 5 | 0.96 | 0.95 | 0.62 | 0.14 | 0.01 | -0.002 | -0.003 | 0.96 / 0.11 | 1.00 / 0.04 |
| 10 | 0.85 | 0.83 | 0.49 | 0.12 | 0.01 | 0.003 | 0.002 | 0.86 / 0.14 | 0.92 / 0.03 |
| 15 | 0.78 | 0.77 | 0.40 | 0.10 | 0.01 | 0.008 | 0.000 | 0.81 / 0.11 | 0.91 / 0.04 |

Own m_kill for this judge (not used): 0.21.

## Every verdict: reachable, and where

| judge | verdict | reachable | max rate | at SD | cell (h, g, B3, B4 extra, sham gain) |
|---|---|---|---|---|---|
| Opus 4.8 | kill | yes | 0.98 | 5 | 0.05, 0.0, none, 0.0, 0.0 |
| Opus 4.8 | context | yes | 0.94 | 5 | 0.0, 0.3, full, 0.0, 0.0 |
| Opus 4.8 | separability | yes | 0.09 | 15 | 0.05, 0.2, none, 0.1, 0.0 |
| Opus 4.8 | survives | yes | 0.94 | 5 | 0.0, 0.3, none, 0.0, 0.0 |
| Opus 4.8 | inconclusive | yes | 0.83 | 5 | 0.0, 0.2, none, 0.0, 0.1 |
| Sonnet 5 | kill | yes | 0.96 | 5 | 0.0, 0.0, none, 0.0, 0.0 |
| Sonnet 5 | context | yes | 0.95 | 5 | 0.05, 0.3, full, 0.0, 0.0 |
| Sonnet 5 | separability | yes | 0.10 | 10 | 0.05, 0.2, none, 0.1, 0.0 |
| Sonnet 5 | survives | yes | 0.91 | 5 | 0.05, 0.3, none, 0.0, 0.0 |
| Sonnet 5 | inconclusive | yes | 0.68 | 10 | 0.0, 0.2, none, 0.0, 0.1 |

## Operating characteristics, selected cells (Opus 4.8, the verdict's judge)

Rates of each verdict over outer replicates, in the fixed order. B3 'none' = the unrelated task gains the header's h only; 'full' = it gains h + g. The full grid (64 cells per SD per judge) is in the JSON under `judges.<judge>.by_sd.<sd>.oc`.

| SD | h | g | B3 | B4 extra | sham | kill | context | separability | survives | inconclusive | mean D_h | mean D | mean D_net |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 0.0 | 0.0 | none | 0.0 | 0.0 | 0.97 | 0.00 | 0.00 | 0.00 | 0.03 | -0.003 | -0.004 | 0.000 |
| 5 | 0.0 | 0.0 | none | 0.0 | 0.1 | 0.97 | 0.00 | 0.00 | 0.00 | 0.03 | -0.003 | -0.004 | -0.113 |
| 5 | 0.0 | 0.0 | full | 0.0 | 0.0 | 0.97 | 0.00 | 0.00 | 0.00 | 0.03 | -0.003 | -0.004 | 0.000 |
| 5 | 0.0 | 0.1 | none | 0.0 | 0.0 | 0.41 | 0.07 | 0.02 | 0.18 | 0.32 | 0.117 | 0.117 | 0.121 |
| 5 | 0.0 | 0.1 | none | 0.0 | 0.1 | 0.41 | 0.01 | 0.00 | 0.01 | 0.57 | 0.117 | 0.117 | 0.008 |
| 5 | 0.0 | 0.1 | full | 0.0 | 0.0 | 0.41 | 0.31 | 0.00 | 0.00 | 0.27 | 0.117 | 0.117 | 0.121 |
| 5 | 0.0 | 0.2 | none | 0.0 | 0.0 | 0.04 | 0.01 | 0.00 | 0.81 | 0.15 | 0.206 | 0.205 | 0.209 |
| 5 | 0.0 | 0.2 | none | 0.0 | 0.1 | 0.04 | 0.00 | 0.00 | 0.13 | 0.83 | 0.206 | 0.205 | 0.096 |
| 5 | 0.0 | 0.2 | full | 0.0 | 0.0 | 0.04 | 0.84 | 0.00 | 0.00 | 0.12 | 0.206 | 0.205 | 0.209 |
| 5 | 0.0 | 0.3 | none | 0.0 | 0.0 | 0.01 | 0.00 | 0.00 | 0.94 | 0.06 | 0.292 | 0.291 | 0.295 |
| 5 | 0.0 | 0.3 | none | 0.0 | 0.1 | 0.01 | 0.00 | 0.00 | 0.28 | 0.71 | 0.292 | 0.291 | 0.182 |
| 5 | 0.0 | 0.3 | full | 0.0 | 0.0 | 0.01 | 0.94 | 0.00 | 0.00 | 0.06 | 0.292 | 0.291 | 0.295 |
| 10 | 0.0 | 0.0 | none | 0.0 | 0.0 | 0.87 | 0.01 | 0.00 | 0.00 | 0.12 | 0.004 | 0.005 | 0.005 |
| 10 | 0.0 | 0.0 | none | 0.0 | 0.1 | 0.87 | 0.00 | 0.00 | 0.00 | 0.13 | 0.004 | 0.005 | -0.102 |
| 10 | 0.0 | 0.0 | full | 0.0 | 0.0 | 0.87 | 0.01 | 0.00 | 0.00 | 0.12 | 0.004 | 0.005 | 0.005 |
| 10 | 0.0 | 0.1 | none | 0.0 | 0.0 | 0.42 | 0.06 | 0.00 | 0.06 | 0.46 | 0.105 | 0.105 | 0.106 |
| 10 | 0.0 | 0.1 | none | 0.0 | 0.1 | 0.42 | 0.01 | 0.00 | 0.01 | 0.55 | 0.105 | 0.105 | -0.002 |
| 10 | 0.0 | 0.1 | full | 0.0 | 0.0 | 0.42 | 0.14 | 0.00 | 0.01 | 0.43 | 0.105 | 0.105 | 0.106 |
| 10 | 0.0 | 0.2 | none | 0.0 | 0.0 | 0.07 | 0.06 | 0.03 | 0.54 | 0.31 | 0.206 | 0.207 | 0.207 |
| 10 | 0.0 | 0.2 | none | 0.0 | 0.1 | 0.07 | 0.01 | 0.01 | 0.16 | 0.75 | 0.206 | 0.207 | 0.100 |
| 10 | 0.0 | 0.2 | full | 0.0 | 0.0 | 0.07 | 0.62 | 0.00 | 0.02 | 0.28 | 0.206 | 0.207 | 0.207 |
| 10 | 0.0 | 0.3 | none | 0.0 | 0.0 | 0.01 | 0.00 | 0.00 | 0.89 | 0.09 | 0.304 | 0.305 | 0.306 |
| 10 | 0.0 | 0.3 | none | 0.0 | 0.1 | 0.01 | 0.00 | 0.00 | 0.45 | 0.54 | 0.304 | 0.305 | 0.198 |
| 10 | 0.0 | 0.3 | full | 0.0 | 0.0 | 0.01 | 0.88 | 0.00 | 0.02 | 0.09 | 0.304 | 0.305 | 0.306 |
| 15 | 0.0 | 0.0 | none | 0.0 | 0.0 | 0.78 | 0.00 | 0.00 | 0.00 | 0.21 | -0.004 | -0.000 | -0.001 |
| 15 | 0.0 | 0.0 | none | 0.0 | 0.1 | 0.78 | 0.00 | 0.00 | 0.00 | 0.22 | -0.004 | -0.000 | -0.105 |
| 15 | 0.0 | 0.0 | full | 0.0 | 0.0 | 0.78 | 0.00 | 0.00 | 0.00 | 0.21 | -0.004 | -0.000 | -0.001 |
| 15 | 0.0 | 0.1 | none | 0.0 | 0.0 | 0.45 | 0.07 | 0.01 | 0.03 | 0.45 | 0.091 | 0.095 | 0.094 |
| 15 | 0.0 | 0.1 | none | 0.0 | 0.1 | 0.45 | 0.01 | 0.00 | 0.01 | 0.54 | 0.091 | 0.095 | -0.010 |
| 15 | 0.0 | 0.1 | full | 0.0 | 0.0 | 0.45 | 0.10 | 0.00 | 0.01 | 0.43 | 0.091 | 0.095 | 0.094 |
| 15 | 0.0 | 0.2 | none | 0.0 | 0.0 | 0.10 | 0.10 | 0.02 | 0.29 | 0.48 | 0.193 | 0.196 | 0.195 |
| 15 | 0.0 | 0.2 | none | 0.0 | 0.1 | 0.10 | 0.02 | 0.01 | 0.09 | 0.79 | 0.193 | 0.196 | 0.091 |
| 15 | 0.0 | 0.2 | full | 0.0 | 0.0 | 0.10 | 0.43 | 0.00 | 0.02 | 0.45 | 0.193 | 0.196 | 0.195 |
| 15 | 0.0 | 0.3 | none | 0.0 | 0.0 | 0.01 | 0.02 | 0.03 | 0.75 | 0.19 | 0.293 | 0.297 | 0.296 |
| 15 | 0.0 | 0.3 | none | 0.0 | 0.1 | 0.01 | 0.01 | 0.01 | 0.37 | 0.59 | 0.293 | 0.297 | 0.192 |
| 15 | 0.0 | 0.3 | full | 0.0 | 0.0 | 0.01 | 0.79 | 0.00 | 0.03 | 0.17 | 0.293 | 0.297 | 0.296 |

**Raw overlaps of the conditions before the order is applied** (maximum rate over cells, Opus 4.8, each SD):

- SD 5: kill&context 0.44; kill&separability 0.21; kill&survives 0.15; context&separability 0.29; context&survives 0.00; separability&survives 0.00
- SD 10: kill&context 0.15; kill&separability 0.11; kill&survives 0.02; context&separability 0.23; context&survives 0.00; separability&survives 0.00
- SD 15: kill&context 0.11; kill&separability 0.09; kill&survives 0.01; context&separability 0.17; context&survives 0.00; separability&survives 0.00

## The no-task-in-force marker at the unit the judge scores (note 3, B)

Units by their count of edits with no task in force (every edit in the window; 5+ pooled); for applications also by the count among their three applied lines.

| population | units | any edit: 0 / 1 / 2 / 3 / 4 / 5+ | applied lines: 0 / 1 / 2 / 3 |
|---|---|---|---|
| null | 254 | 51 / 83 / 17 / 41 / 27 / 35 | — |
| middle | 64 | 0 / 4 / 12 / 11 / 9 / 28 | 1 / 11 / 29 / 23 |
| routine_redraw | 32 | 0 / 1 / 6 / 5 / 7 / 13 | 1 / 3 / 13 / 15 |
| conforming | 64 | 2 / 4 / 10 / 14 / 7 / 27 | 6 / 6 / 32 / 20 |
| sham_redraw | 32 | 0 / 1 / 8 / 8 / 1 / 14 | 1 / 6 / 18 / 7 |
| sham | 64 | 0 / 1 / 12 / 17 / 10 / 24 | 0 / 7 / 36 / 21 |

## D and D_h by an application's lines with no task in force (0 to 3), pre-registered descriptive reading

Point readings over outer replicates at h = 0 (mean [2.5th, 97.5th percentile]); the gain is injected uniformly, so any slope across bins here is noise. In Part 2, a D concentrated at high counts is read as the judge reading the marker.

- **Opus 4.8, SD 5** (applications per bin [2, 14, 42, 38]):
  - D at g = 0.0: 0: -0.00 [0.00, 0.00]; 1: 0.00 [-0.25, 0.32]; 2: -0.00 [-0.14, 0.16]; 3: -0.01 [-0.20, 0.18]
  - D at g = 0.1: 0: 0.00 [0.00, 0.00]; 1: 0.12 [-0.08, 0.40]; 2: 0.10 [-0.03, 0.31]; 3: 0.14 [-0.02, 0.35]
  - D at g = 0.2: 0: 0.00 [0.00, 0.00]; 1: 0.19 [0.00, 0.50]; 2: 0.17 [0.03, 0.37]; 3: 0.27 [0.07, 0.51]
  - D at g = 0.3: 0: 0.00 [0.00, 0.00]; 1: 0.23 [0.00, 0.57]; 2: 0.25 [0.10, 0.47]; 3: 0.38 [0.18, 0.59]
  - Dh at g = 0.0: 0: -0.00 [0.00, 0.00]; 1: 0.00 [-0.23, 0.25]; 2: -0.00 [-0.16, 0.13]; 3: -0.00 [-0.17, 0.18]
  - Dh at g = 0.1: 0: 0.00 [0.00, 0.00]; 1: 0.12 [-0.05, 0.37]; 2: 0.10 [-0.03, 0.26]; 3: 0.14 [-0.01, 0.37]
  - Dh at g = 0.2: 0: 0.00 [0.00, 0.00]; 1: 0.19 [0.00, 0.50]; 2: 0.17 [0.03, 0.33]; 3: 0.27 [0.10, 0.49]
  - Dh at g = 0.3: 0: 0.00 [0.00, 0.00]; 1: 0.23 [0.00, 0.56]; 2: 0.25 [0.10, 0.44]; 3: 0.38 [0.18, 0.60]
- **Opus 4.8, SD 10** (applications per bin [2, 14, 42, 38]):
  - D at g = 0.0: 0: -0.03 [-0.57, 0.00]; 1: 0.01 [-0.35, 0.40]; 2: 0.00 [-0.22, 0.21]; 3: 0.01 [-0.26, 0.25]
  - D at g = 0.1: 0: 0.00 [0.00, 0.00]; 1: 0.10 [-0.19, 0.47]; 2: 0.09 [-0.10, 0.30]; 3: 0.12 [-0.13, 0.37]
  - D at g = 0.2: 0: 0.01 [0.00, 0.00]; 1: 0.20 [-0.08, 0.58]; 2: 0.18 [0.00, 0.38]; 3: 0.25 [0.02, 0.49]
  - D at g = 0.3: 0: 0.01 [0.00, 0.03]; 1: 0.27 [0.00, 0.67]; 2: 0.27 [0.07, 0.50]; 3: 0.38 [0.14, 0.61]
  - Dh at g = 0.0: 0: -0.01 [-0.70, 0.57]; 1: -0.00 [-0.33, 0.33]; 2: 0.01 [-0.21, 0.22]; 3: 0.00 [-0.24, 0.23]
  - Dh at g = 0.1: 0: 0.02 [0.00, 0.57]; 1: 0.09 [-0.18, 0.40]; 2: 0.10 [-0.10, 0.32]; 3: 0.12 [-0.12, 0.34]
  - Dh at g = 0.2: 0: 0.03 [0.00, 0.57]; 1: 0.19 [-0.13, 0.51]; 2: 0.18 [0.03, 0.41]; 3: 0.24 [0.00, 0.46]
  - Dh at g = 0.3: 0: 0.03 [0.00, 0.57]; 1: 0.26 [0.00, 0.59]; 2: 0.27 [0.09, 0.52]; 3: 0.37 [0.13, 0.59]
- **Opus 4.8, SD 15** (applications per bin [2, 14, 42, 38]):
  - D at g = 0.0: 0: 0.01 [-1.00, 1.00]; 1: -0.01 [-0.47, 0.45]; 2: -0.01 [-0.26, 0.25]; 3: 0.01 [-0.31, 0.31]
  - D at g = 0.1: 0: 0.08 [-1.00, 1.00]; 1: 0.09 [-0.38, 0.54]; 2: 0.08 [-0.18, 0.33]; 3: 0.12 [-0.17, 0.42]
  - D at g = 0.2: 0: 0.13 [-0.02, 1.00]; 1: 0.18 [-0.23, 0.62]; 2: 0.18 [-0.04, 0.42]; 3: 0.23 [-0.04, 0.51]
  - D at g = 0.3: 0: 0.15 [0.00, 1.00]; 1: 0.27 [-0.08, 0.67]; 2: 0.27 [0.06, 0.52]; 3: 0.34 [0.09, 0.62]
  - Dh at g = 0.0: 0: -0.00 [-1.00, 1.00]; 1: -0.01 [-0.47, 0.45]; 2: -0.00 [-0.28, 0.29]; 3: -0.01 [-0.27, 0.26]
  - Dh at g = 0.1: 0: 0.07 [-1.00, 1.00]; 1: 0.09 [-0.40, 0.56]; 2: 0.09 [-0.19, 0.36]; 3: 0.10 [-0.17, 0.37]
  - Dh at g = 0.2: 0: 0.12 [-0.33, 1.00]; 1: 0.19 [-0.21, 0.65]; 2: 0.18 [-0.07, 0.44]; 3: 0.21 [-0.08, 0.49]
  - Dh at g = 0.3: 0: 0.14 [0.00, 1.00]; 1: 0.27 [-0.07, 0.67]; 2: 0.28 [0.01, 0.55]; 3: 0.33 [0.06, 0.57]
- **Sonnet 5, SD 5** (applications per bin [2, 14, 42, 38]):
  - D at g = 0.0: 0: 0.02 [-1.00, 1.00]; 1: 0.00 [-0.27, 0.30]; 2: -0.01 [-0.18, 0.16]; 3: -0.00 [-0.23, 0.19]
  - D at g = 0.1: 0: 0.10 [0.00, 1.00]; 1: 0.09 [-0.18, 0.43]; 2: 0.08 [-0.07, 0.27]; 3: 0.12 [-0.09, 0.33]
  - D at g = 0.2: 0: 0.12 [0.00, 1.00]; 1: 0.18 [-0.03, 0.50]; 2: 0.17 [0.00, 0.38]; 3: 0.23 [0.01, 0.41]
  - D at g = 0.3: 0: 0.12 [0.00, 1.00]; 1: 0.25 [0.00, 0.60]; 2: 0.27 [0.07, 0.47]; 3: 0.33 [0.11, 0.53]
  - Dh at g = 0.0: 0: 0.01 [-1.00, 0.67]; 1: -0.01 [-0.31, 0.29]; 2: -0.00 [-0.17, 0.15]; 3: -0.00 [-0.20, 0.17]
  - Dh at g = 0.1: 0: 0.09 [-0.02, 1.00]; 1: 0.08 [-0.24, 0.40]; 2: 0.09 [-0.09, 0.28]; 3: 0.12 [-0.08, 0.32]
  - Dh at g = 0.2: 0: 0.10 [0.00, 1.00]; 1: 0.17 [-0.10, 0.54]; 2: 0.18 [0.00, 0.37]; 3: 0.23 [0.03, 0.43]
  - Dh at g = 0.3: 0: 0.10 [0.00, 1.00]; 1: 0.24 [0.00, 0.60]; 2: 0.28 [0.08, 0.48]; 3: 0.33 [0.11, 0.54]
- **Sonnet 5, SD 10** (applications per bin [2, 14, 42, 38]):
  - D at g = 0.0: 0: -0.03 [-1.00, 1.00]; 1: 0.00 [-0.33, 0.34]; 2: 0.00 [-0.22, 0.24]; 3: 0.00 [-0.27, 0.25]
  - D at g = 0.1: 0: 0.12 [-1.00, 1.00]; 1: 0.09 [-0.27, 0.46]; 2: 0.09 [-0.14, 0.35]; 3: 0.11 [-0.16, 0.35]
  - D at g = 0.2: 0: 0.21 [-1.00, 1.00]; 1: 0.19 [-0.17, 0.57]; 2: 0.18 [-0.06, 0.44]; 3: 0.21 [-0.07, 0.50]
  - D at g = 0.3: 0: 0.27 [-0.27, 1.00]; 1: 0.29 [-0.00, 0.68]; 2: 0.28 [0.06, 0.54]; 3: 0.32 [0.05, 0.59]
  - Dh at g = 0.0: 0: 0.01 [-1.00, 1.00]; 1: 0.01 [-0.39, 0.34]; 2: 0.00 [-0.21, 0.22]; 3: 0.00 [-0.26, 0.24]
  - Dh at g = 0.1: 0: 0.16 [-1.00, 1.00]; 1: 0.10 [-0.25, 0.46]; 2: 0.09 [-0.11, 0.35]; 3: 0.11 [-0.18, 0.35]
  - Dh at g = 0.2: 0: 0.25 [-0.76, 1.00]; 1: 0.19 [-0.18, 0.56]; 2: 0.18 [-0.04, 0.45]; 3: 0.21 [-0.08, 0.47]
  - Dh at g = 0.3: 0: 0.31 [-0.04, 1.00]; 1: 0.29 [-0.06, 0.62]; 2: 0.28 [0.03, 0.56]; 3: 0.32 [0.02, 0.56]
- **Sonnet 5, SD 15** (applications per bin [2, 14, 42, 38]):
  - D at g = 0.0: 0: 0.01 [-1.00, 1.00]; 1: 0.01 [-0.44, 0.49]; 2: 0.00 [-0.24, 0.22]; 3: -0.00 [-0.26, 0.25]
  - D at g = 0.1: 0: 0.14 [-1.00, 1.00]; 1: 0.11 [-0.31, 0.56]; 2: 0.10 [-0.13, 0.34]; 3: 0.10 [-0.16, 0.37]
  - D at g = 0.2: 0: 0.25 [-1.00, 1.00]; 1: 0.20 [-0.18, 0.64]; 2: 0.19 [-0.07, 0.43]; 3: 0.20 [-0.09, 0.49]
  - D at g = 0.3: 0: 0.34 [-1.00, 1.00]; 1: 0.31 [-0.12, 0.71]; 2: 0.28 [-0.00, 0.51]; 3: 0.31 [0.04, 0.56]
  - Dh at g = 0.0: 0: 0.01 [-1.00, 1.00]; 1: 0.03 [-0.36, 0.46]; 2: 0.00 [-0.24, 0.24]; 3: 0.00 [-0.25, 0.24]
  - Dh at g = 0.1: 0: 0.15 [-1.00, 1.00]; 1: 0.13 [-0.29, 0.50]; 2: 0.10 [-0.16, 0.35]; 3: 0.11 [-0.17, 0.37]
  - Dh at g = 0.2: 0: 0.25 [-1.00, 1.00]; 1: 0.22 [-0.20, 0.61]; 2: 0.19 [-0.06, 0.44]; 3: 0.21 [-0.07, 0.48]
  - Dh at g = 0.3: 0: 0.34 [-0.67, 1.00]; 1: 0.33 [-0.05, 0.71]; 2: 0.28 [0.04, 0.51]; 3: 0.32 [0.05, 0.56]

## Structure from data (counts only)

- **Null:** 254 units, labels equal to the sealed rows: True; edits per unit {'min': 1, 'max': 25, 'mean': 9.24}; 118 distinct edits (no-ops dropped: 53 unit-edit occurrences); roster 50 accounts.
- **Positions of the null's distinct edits:** {'bracketed': 4, 'matched': 114}.
- **Licence cases, the null's distinct edits:** {'no_task': 6, 'non_class+no_item_line': 4, 'class_write_this_document': 70, 'class_write_this_document+no_item_line': 18, 'class_read_this_document': 1, 'no_task+no_item_line': 19}; no task in force by session feed: {'fed_only_after': 25}.
- **B3 length match, the null's distinct edits:** {'no_task': 25, 'matched': 93}.
- **T1 v3 applications:** 128 units {'middle': 64, 'routine_redraw': 32, 'sham_redraw': 32} on 12 (document, boundary) groups; 384 applied lines, 1663 honest edits in their windows; positions {'at_or_before:matched': 341, 'at_or_before:bracketed': 40, 'at_or_before:ambiguous': 3}; within item scope 0; no task in force by session feed {'fed_only_after': 255, 'session_fed_nothing': 20}.
  - licence cases of the applied lines: {'no_task+no_item_line': 179, 'non_class+no_item_line': 41, 'class_read_other_document+no_item_line': 6, 'non_class': 30, 'no_task': 96, 'class_read_this_document+no_item_line': 6, 'class_write_this_document+no_item_line': 9, 'class_write_other_document+no_item_line': 9, 'class_write_this_document': 2, 'class_read_other_document': 4, 'class_read_this_document': 1, 'class_write_other_document': 1}; B3 length match: {'honest:no_task': 375, 'honest:matched': 1288, 'applied:no_task': 275, 'applied:matched': 109}.
- **T1 v2 applications:** 128 units {'conforming': 64, 'sham': 64} on 12 (document, boundary) groups; 384 applied lines, 1667 honest edits in their windows; positions {'at_or_before:matched': 335, 'at_or_before:bracketed': 44, 'at_or_before:end': 2, 'at_or_before:ambiguous': 3}; within item scope 0; no task in force by session feed {'fed_only_after': 250, 'session_fed_nothing': 22}.
  - licence cases of the applied lines: {'no_task+no_item_line': 174, 'non_class+no_item_line': 51, 'class_read_this_document+no_item_line': 5, 'no_task': 98, 'non_class': 31, 'class_write_this_document': 4, 'class_write_this_document+no_item_line': 4, 'class_write_other_document+no_item_line': 5, 'class_read_other_document+no_item_line': 7, 'class_read_other_document': 1, 'class_write_other_document': 1, 'class_read_this_document': 3}; B3 length match: {'honest:no_task': 362, 'honest:matched': 1305, 'applied:no_task': 272, 'applied:matched': 112}.
- **B5 on the null:** t = 9, p_tie = 0.5500, expected rate 0.100, realised flagged 26 of 254 (tie seed `20261107|B5`); units above the cut 21 on 4 chains, at the cut 8 on 5; calibratable at 10 percent: **True**; bracketing cuts {'ge_lo': 9, 'units_ge_lo': 29, 'ge_hi': 10, 'units_ge_hi': 21}.
- **B5p on the null:** t = 6, p_tie = 0.3400, expected rate 0.100, realised flagged 25 of 254 (tie seed `20261107|B5p`); units above the cut 22 on 3 chains, at the cut 10 on 3; calibratable at 10 percent: **True**; bracketing cuts {'ge_lo': 6, 'units_ge_lo': 32, 'ge_hi': 7, 'units_ge_hi': 22}.

## Recorded no-task readings reproduced, and the free rules on the applications

| judge | rule (t, p_tie) refit equal | flags reproduced | recorded r₀ (expected / realised) | recorded s_B0 (expected / realised) | comparison set | c | s_c | c_net | B5-applied (diagnostic) | B5′ c / s / net |
|---|---|---|---|---|---|---|---|---|---|---|
| Opus 4.8 | 55.0, 0.9000; True | 128/128 | 0.550 / 0.552 | 0.000 / 0.000 | v3:sham_redraw (32) | 0.486 | 0.478 | 0.008 | 1.000 | 0.410 / 0.417 / -0.007 |
| Sonnet 5 | 78.0, 0.6714; True | 256/256 | 0.331 / 0.344 | 0.077 / 0.062 | v3:sham_redraw, v2:sham (96) | 0.486 | 0.472 | 0.014 | 1.000 | 0.410 / 0.400 / 0.010 |

## Calibrated shifts (score points added to the planted units; per SD)

- Opus 4.8, SD 5: +0.05 → 4.07, +0.1 → 7.82, +0.15 → 11.25, +0.2 → 14.51, +0.25 → 17.95, +0.3 → 22.04, +0.35 → 27.59, +0.4 → 43.62, +0.45 → 100.00 (not attained); sham +0.10 → 8.80; noise alone moves the unshifted share to 0.585.
- Opus 4.8, SD 10: +0.05 → 3.06, +0.1 → 6.25, +0.15 → 9.56, +0.2 → 13.18, +0.25 → 16.99, +0.3 → 21.32, +0.35 → 26.40, +0.4 → 33.91, +0.45 → 55.90; sham +0.10 → 8.45; noise alone moves the unshifted share to 0.546.
- Opus 4.8, SD 15: +0.05 → 3.07, +0.1 → 6.15, +0.15 → 9.38, +0.2 → 12.90, +0.25 → 16.63, +0.3 → 20.78, +0.35 → 25.47, +0.4 → 30.94, +0.45 → 38.60; sham +0.10 → 10.06; noise alone moves the unshifted share to 0.484.
- Sonnet 5, SD 5: +0.05 → 1.96, +0.1 → 3.81, +0.15 → 5.63, +0.2 → 7.54, +0.25 → 9.53, +0.3 → 11.78, +0.35 → 14.33, +0.4 → 17.61, +0.45 → 22.58; sham +0.10 → 6.68; noise alone moves the unshifted share to 0.303.
- Sonnet 5, SD 10: +0.05 → 2.37, +0.1 → 4.74, +0.15 → 7.10, +0.2 → 9.49, +0.25 → 11.87, +0.3 → 14.55, +0.35 → 17.49, +0.4 → 21.15, +0.45 → 25.89; sham +0.10 → 9.68; noise alone moves the unshifted share to 0.273.
- Sonnet 5, SD 15: +0.05 → 3.16, +0.1 → 6.22, +0.15 → 9.12, +0.2 → 12.08, +0.25 → 15.06, +0.3 → 18.24, +0.35 → 21.72, +0.4 → 25.77, +0.45 → 30.38; sham +0.10 → 12.67; noise alone moves the unshifted share to 0.247.

**Drift (δ):** a fresh re-score of B0 on the fixed world moves r₀ from the record by {"opus48": {"5": {"mean": 0.0357, "abs_q95": 0.0792}, "10": {"mean": -0.0019, "abs_q95": 0.0834}, "15": {"mean": -0.065, "abs_q95": 0.1573}}, "sonnet": {"5": {"mean": -0.0268, "abs_q95": 0.0818}, "10": {"mean": -0.0585, "abs_q95": 0.1326}, "15": {"mean": -0.0802, "abs_q95": 0.1597}}} (mean, |·| 95th percentile).

**The test–retest row:** the standard deviation of the paired score differences (fresh B0 − recorded B0, after rounding and clipping) that each SD row produces, mean [2.5th, 97.5th percentile]: {"opus48": {"5": [4.83, 4.5, 5.17], "10": [9.39, 8.75, 10.11], "15": [13.64, 12.75, 14.72], "n_units": 382}, "sonnet": {"5": [4.83, 4.52, 5.16], "10": [9.26, 8.64, 9.88], "15": [13.35, 12.46, 14.2], "n_units": 446}}. Part 2's realised value names the row that applies.

## Executor's notes on v1 (written by hand after the run; figures are quoted from `dryrun-v1.json` or `estimate-v1.json` unless marked)

- **1. The header scrub is my reading of note 3, A; the coordinator can confirm or reverse it.** Fed task texts carry their session's workspace slug, which is the account name with "." replaced by "-". A separate $0 count, not in the record: 396 of 667 fed items carry it, 210 of them outside a `/work/` path, and one fed item names another roster account. Showing the task as fed would therefore name the author in B1 to B4. So the renderers replace the bank's `{ws}`, every roster account and every roster workspace slug with `<workspace>` or `<account>`. B3's draws are scrubbed the same way and length-matched on the scrubbed texts. The sizing pass finds 0 grounded headers naming a roster account or slug. Keeping the slugs would only need `scrub` to become the identity.
- **2. E's sentence as note 3 words it does not hold under v1.** At h = 0 and B3 none, under Opus 4.8, the modal outcome at g = 0.20 and SD 10 is survives (0.54), and at g = 0.10 and SD 15 it is kill (0.45). Inconclusive is modal only at g = 0.10 with SD 10 (0.46) and at g = 0.20 with SD 15 (0.48). A sham gain of 0.10 holds survives to 0.56 or below, not 0.25 (v0's figure, before B0 was fresh). `preregistration-v1.1.md` §6 carries the sentence generated from this record.
- **3. Kill catches a real 0.10 gain about 40 percent of the time.** At m_kill 0.23, P(kill | g = 0.10) is 0.41, 0.42 and 0.45 under Opus 4.8 at SD 5, 10 and 15 (Sonnet 5: 0.62, 0.49, 0.40). That is the decoupled margin doing what v0.1 §6 says: a gain below about 0.2 reads as the headline's form failing, with the gain reported beside. Stated so the reader of a kill knows its reach.
- **4. Sonnet 5 at Opus 4.8's m_kill** reads P(kill | g = 0.20) 0.14, 0.12 and 0.10 at SD 5, 10 and 15, above the 0.10 bound at SD 5 and 10; its own m_kill would be 0.21. Sonnet is beside and never pooled, so the rule stands, but a Sonnet kill sentence should carry this.
- **5. Separability is now rare:** at most 0.09 (Opus 4.8) and 0.10 (Sonnet 5) in any cell, all through the judge-side branch. With c_net at 0.008 its lower bound is not above zero, so branch 1 cannot fire on this world's free rule.
- **6. The D-by-marker bins: read this note, not the generated caption.** The gain is injected uniformly in score points, so the bins' baselines differ through their own score distributions as well as through noise. Example: Opus 4.8, SD 10, g = 0.30, bins 1, 2 and 3 read 0.27, 0.27 and 0.38. The caption's "any slope across bins here is noise" is too strong. Part 2 reads its bins against these baselines; bin 0 holds 2 of the 96.
- **7. The test–retest rows.** The paired-difference SD reads 4.83, 9.39 and 13.64 at SD 5, 10 and 15 under Opus 4.8 (382 units with a record) and 4.83, 9.26 and 13.35 under Sonnet 5 (446 units). The nearest row applies.
- **8. Spend.** $118.77 for 6,120 calls (null $49.15, applications $69.62; the fresh B0 arm $17.31). The cap is $237.54 ($278.89 with B1-all, which costs at least $20.68). Part 2 opens on Aravind's spend line.
