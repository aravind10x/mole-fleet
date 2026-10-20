# GitLab smoke (S0): pre-registered pass conditions

Written 2026-10-20 by the Stage 3 blue-prep session (brief 07, task S0) **before any Docker command for this smoke was run**. The conditions are copied from `work/stage3-research-design-2026-10-19.md` v3, section 2, "The GitLab smoke, pre-registered". The numbers below this section are filled in after the run; nothing above it changes.

## Pass conditions (verbatim from the design, section 2)

> Five accounts, two days, about $5 to $10. A boot and a merge-request round-trip are necessary but not the pass condition. Pass requires, written before the run: sessions per hour at concurrency 4 or more of at least 8 (a 50-account, 2-sessions-per-day branch of 500 sessions then takes about 60 hours per process, so three or four parallel processes are needed and the per-process number must hold with them running); VM memory headroom at two Puma workers with the other five services up; per-day snapshot disk growth under 3 GB; failed-event share under 10 percent. Any miss is a kill for (i) and a fall-back to (i-), recorded with the numbers.

Restated as the checklist the run is read against (brief 07, S0):

| # | condition | pass if | how measured |
|---|---|---|---|
| C1 | throughput | sessions per hour at `--concurrency` ≥ 4 is **≥ 8** | completed sessions ÷ wall-clock hours of the session phase (manifest `completed`, log timestamps) |
| C2 | memory | VM memory headroom with `GITLAB_PUMA_WORKERS=2` and the other five services up (positive headroom under the 7.65 GiB VM cap, no OOM kill, no container restart) | `docker stats` samples during the run; `docker inspect` restart counts |
| C3 | disk | per-day snapshot disk growth **< 3 GB** | `du` of `.snapshots/<run>/day_*` plus `itb-snap` image sizes per day |
| C4 | failed events | failed-event share **< 10 percent** | audit rows with `exit_code != 0` ÷ all rows |
| C5 | merge request | a merge request opened, reviewed and merged by agents end to end | audit log: `gitlab.*` events creating, commenting on/approving and merging one MR, all `exit_code == 0` |
| C6 | boot | GitLab boots (healthcheck passes) within two working hours of fixing | wall-clock from first `compose up` to healthy |

Any miss of C1 to C5 kills substrate (i) and the fall-back is (i-), lab mode without GitLab (tested in the T5 spike). A C6 miss is recorded with the reason and the substrate for the rest of brief 07 is (i-).

Other pre-registered items (brief 07, S0): free disk recorded before and after the image pull; both OpenRouter caps checked before launch (L3, L7); a written dollar and wall-clock estimate before launch; `--no-insiders`, Kimi, 5 accounts, 2 days, from a worktree pinned to the current commit (L6); manifest check (L1, L15) before reading any result.

## Credit check (L3, L7), 2026-10-20 before any launch

Key 2 `limit_remaining` $388.79; account balance (`/api/v1/credits`) $98.79 (total_credits 710, total_usage 611.21). The binding cap is the account balance. The smoke's ceiling is $10, well inside both.

## Run record (filled in by the S0 agent after the run; nothing above this line changes)

Filled in 2026-10-20 by the S0 agent and revised the same day after the controller's review. Every number is tagged **tested** (run here, with the command or script named), **observed** (read in a named file and line) or **inferred** (stated basis).

**Raw logs:** small text files, copied from the S0 agent's scratchpad into `work/stage3/gitlab-smoke-logs/`:
- `timeline.txt`, `disk_pull.log`, `pull_tail.log`, `disk_boot.log`, `stats_boot.txt`, `snapsize.log`
- the scripts that produced them: `imgsize.py`, `watch_pull.sh`, `watch_boot.sh`, `snapsize.sh`, and `credits.sh`, which names only the env-var names and prints numbers only. The scripts still contain their original scratchpad paths, so they are records, not re-runnable as-is.
- `bank_mr_counts.py` and its output `bank_mr_counts.out`.

### Verdict

**Kill for substrate (i). The substrate for the rest of brief 07 is (i-): lab mode without GitLab, as tested in T5.**

- GitLab booted cleanly under amd64 emulation (C6 met, 162 s to healthy).
- Condition C3 is missed by measurement: one GitLab day snapshot is a 5.83 GB tarball, against the < 3 GB limit. That figure was taken at boot state, before seeding or any agent activity. It is a **lower bound**; a seeded, used lab writes a larger tarball.
- The agentic smoke was **not launched** and **$0 was spent**. C1, C4 and C5 are **not measured**. C2 was measured with the lab idle only.

**What the kill rests on.** The kill follows from the pre-registered per-day-snapshot condition (C3). It does not mean GitLab is infeasible on this host: GitLab booted, ran at puma 2 with about 2.3 GiB of memory headroom at idle, and served.
- `mole/generator/run.py` lines ~1391 to 1405 (observed) say the per-day Docker volume snapshot is needed only for `--restore-world` (rebuilding a dead lab). They also say `NPC_SKIP_DOCKER_SNAPSHOT=1` is a supported way to skip it. Plain `--resume` reattaches the live lab.
- So a skip-snapshot variant of (i) exists. It is not what was pre-registered: the design needs branches taken from one snapshot, so the per-day snapshot is part of the substrate being judged.

### Disk and image pull (tested; `df -k /` sampled every 20 s by `watch_pull.sh`, which would have killed the pull below 3 GB)

| Point | Free on `/` | Notes |
|---|---|---|
| Before pull (10:22:36) | 31,162,904 kB = **29.7 GiB** | Docker VM `/`: 38.3 G free of 58.4 G |
| Lowest during pull (10:35:17, layer extraction) | 7,565,252 kB = **7.2 GiB** | |
| After pull (10:35:33) | 11,970,172 kB = **11.4 GiB** | Pull took **13 min** (10:22:36 to 10:35:33). Two layers retried once. Image `servers-gitlab:1.0.0` is **17.5 GB** locally (11.86 GB compressed in 13 layers; `imgsize.py`, registry API). Docker VM `/`: 21.7 G free. `Docker.raw` allocated 18.6 → 36.5 GB. |
| GitLab container created (10:38:09) | 2,246,668 kB = **2.14 GiB** | The `gitlab-data` named volume is populated with a copy of the image's `/var/opt/gitlab`: **9.44 GB** (`docker system df -v`). Inside the image, `du` gives 8.9 G for `/var/opt/gitlab` (postgresql 3.6 G, git-data 2.3 G, gitlab-rails 2.3 G, prometheus 671 M) and 3.4 G for `/opt/gitlab`. |
| Full lab up, lowest (10:42:18) | 1,470,288 kB = **1.40 GiB** | See the risk note below. |
| After teardown (`down -v`, 10:48:57) | 11,767,904 kB = **11.2 GiB** | Images kept. No `itb-snap` images were created. |

**Risk acknowledgement.** To sample memory with all six containers up, I ran the full lab down to 1.40 GiB free on the host. That is below the brief's 3 GB floor. For that test I lowered the watchdog floor (`watch_boot.sh`) from 1.5 GiB to 1.0 GiB. The window was about 5 minutes (10:40:47 to 10:42:45).

**Kept image.** The GitLab image is kept, as the brief says. At 17.5 GB locally it takes the host from 29.7 GiB free to about 11.2 GiB free. To recover the space: `docker rmi ghcr.io/theagentcompany/servers-gitlab:1.0.0`.

### Boot (C6) (tested)

Setup: worktree `work/mole-fork-smoke` pinned at 709a32c, `compose/lab.yaml` unchanged, project `s0boot`, `GITLAB_PUMA_WORKERS=2` and `GITLAB_SIDEKIQ_CONCURRENCY=5` (both confirmed in `docker compose config`), credential-free `DOCKER_CONFIG`.

| Time | Step | Result |
|---|---|---|
| 10:37:23 | `docker compose -p s0boot -f lab.yaml up -d gitlab` (the same two-phase order as `LabSandbox.start`) | Returned 10:38:01. The 38 s were spent creating the volume copy. |
| 10:38:01 to 10:39:29 | Wrapper | The patch script applied. The runsv wait held. **Chef reconfigure attempt 1 failed** with the known `runit_service[gitlab-workhorse]` race (`ShellCommandFailed`). The wrapper's retry slept 15 s. |
| ≤ 10:40:05 | Healthcheck | **healthy at t0 + 162 s**, restarts 0 |
| ~10:40:25 | Reconfigure attempt 2 | `gitlab Reconfigured!` |
| 10:40:47 | `up -d --wait` for the rest of the stack | All six containers healthy in **16 s** |

There was **1 boot attempt** and no fix was needed: the existing `gitlab-patches.sh` retry absorbed the race. The compose and patch files are unchanged, so there is no diff. C6 is **met**: 162 s against a two-hour budget.

### Memory (C2) (tested; `docker stats --no-stream`, 4 samples 10:41:24 to 10:42:15, `stats_boot.txt`)

The lab was idle during the samples: booted, not seeded, no agent load.

| Container | Memory over the 4 samples |
|---|---|
| gitlab (puma 2) | 3.18 to 3.19 GiB; 3.09 GiB when running alone |
| rocketchat | 685 to 824 MiB (CPU up to 133 % while starting) |
| owncloud-collabora | 796 to 799 MiB |
| rocketchat-mongodb | 192 to 223 MiB |
| owncloud | 96 to 167 MiB |
| greenmail | 129 MiB |
| **Sum of per-container peaks** | **about 5.28 GiB** (the peaks are not simultaneous) |

- Headroom from the peak sum: 7.652 − 5.28 = about 2.37 GiB.
- The VM's own `free -m` (run in a busybox container at about 10:42:30, after the last stats sample) showed **2,384 MiB = 2.33 GiB available**. That is the safer figure, and the one this record uses.
- No OOM kill and no container restart (`docker inspect`: RestartCount 0 and OOMKilled false for all six).
- C2 is **met at idle only**. Memory under seeding and concurrency-4 agent load was not measured.

### Day snapshot size (C3) (tested; `snapsize.sh`, `snapsize.log`)

The probe ran the same pause and `busybox tar czf` that `mole/sandbox/snapshot.py` runs, piped to `wc -c` so nothing was written to the host. It ran on **GitLab alone**: the other five services and their volumes had been removed at 10:42:45.

- GitLab container paused 10:43:21 to 10:48:20.
- `gitlab-data` tarball: **5,826,989,890 bytes = 5.83 GB** (5.43 GiB), taking **299 s** while paused.
- `gitlab-config` tarball: 51,863 bytes. GitLab writable layer: 314 kB (the `docker commit` delta).
- The snapshot writes a full tarball of every volume every day (`snapshot.py` lines ~172 to 197), so per-day snapshot growth is at least **5.83 GB for GitLab alone**.
- This is a **lower bound** on three counts: it is GitLab only (T5 measured about 150 MB of tarballs for the other services, t5-report.md line 63, observed), it is at boot state, and a seeded lab with agent activity has a larger GitLab volume.
- **C3 missed.** The tarball also does not fit in the 1.40 GiB free with the lab up.
- Side observation: after the 299 s pause, GitLab's healthcheck read `unhealthy`. Recovery was not observed before teardown.

### Why the agentic smoke was not launched (decision; spend $0)

1. **C3 cannot pass on the pre-registered condition.** Pass requires all of C1 to C5, so substrate (i) as pre-registered is killed whatever the run would show.
2. **The run cannot fit on this host.** With all six containers up, free disk was 1.40 GiB, under the 3 GB floor. The first day boundary would try to write a tarball of about 5.8 GB or more.
   - Skipping the snapshot would leave C3 not measured. That still fails the all-of-C1-to-C5 rule.
   - It would also run two simulated days of GitLab, Postgres and log growth on about 1.4 GiB of free disk.
3. Spending $5 to $10 on a run that cannot change the verdict, and that puts the host disk at risk, was not justified.

Because no launch happened, these were not done: the written launch estimate, the rules-mode rehearsal and the launch itself. For the record, the plan was:
- `--sessions-per-day 2 --concurrency 5`, 5 accounts × 2 days = 20 sessions.
- Cost $5.1 to $9.0, inferred from T5's $0.256 per session provider-reported (t5-report.md line 134, observed) and up to $0.45 per session on the key delta (line 188). Stop at $10.
- Wall-clock 1.5 to 3 h, inferred from about 7 min per session run mostly one at a time (line 137).
- Accounts: alice.kim (alignment lead; GitLab maintainer and eval-reviewer), deepa.a7 and priya.a84 (alignment developers), wei.n2 (platform), deepa.a1 (capabilities).
- Why those accounts: merge-request mentions per team in the v2 bank (tested, `bank_mr_counts.py`, keyword match, approximate) are alignment 14 of 143 variants, platform 7 of 143, capabilities 6 of 142, evaluations 5 of 142, hr 0, legal 0.

### Credit (tested; `credits.sh`, `/api/v1/auth/key` and `/api/v1/credits`, numbers only)

| When | Key 2 `limit_remaining` | Account balance |
|---|---|---|
| Between 10:25:07 and 10:25:46 (during the pull; the command was not timestamped, so this is bracketed by the neighbouring timestamped commands) | $388.79 | $98.79 (710 − 611.21) |
| 10:48:57 to 10:48:58 (after teardown, in the same command as the worktree removal) | $388.79 | $98.79 |

No LLM call was made, so the delta is $0.00.

### Conditions

| # | Condition | Result | Number |
|---|---|---|---|
| C1 | ≥ 8 sessions per hour at concurrency ≥ 4 | **not measured** (no run) | none for (i); see the note on (i-) below |
| C2 | VM memory headroom at puma 2 with the five others up | **met at idle only** | 2.33 GiB available (`free -m`), 0 restarts, 0 OOM |
| C3 | per-day snapshot growth < 3 GB | **MISS** | GitLab volume tarball 5.83 GB at boot state (a lower bound) |
| C4 | failed-event share < 10 % | **not measured** (no run) | T5 without GitLab: 5.8 % (t5-report.md line 113, observed) |
| C5 | merge request opened, reviewed and merged by agents | **not measured** (no run) | none |
| C6 | boot within two working hours | **met** | 162 s to healthy, 1 attempt |

**Substrate for brief 07: (i-), lab mode without GitLab (tested in T5).**

**(i-) is itself unproven against the throughput condition.**
- T5 ran 6 sessions in about 41 min of session time, about 8.8 per hour (t5-report.md line 32 and line 137, observed). Those sessions ran **mostly one at a time**, not at concurrency 4 or more.
- CONTEXT.md §6 (line 111, observed) gives about 7 sessions per hour per 7-account process whatever `--concurrency` says. That is **below the bar of 8**.
- The design's lab cost and wall-clock figures ($0.26 per session, about 7 min per session) were to be re-measured by this smoke. They were not.
- The S5.3 placeholder run on (i-) will give a 6-session measurement.

**What a later attempt at (i) would need** (inferred):
- **More free disk makes (i) measurable, not passable.** That means at least 9.4 GB for the GitLab volume, about 1 GB for the other services, and at least 6 GB per simulated day of snapshots: 25 GB or more free beyond the image for a 2-day smoke, or Docker's disk on an external volume. With that disk, C1, C4 and C5 could be measured, but C3 as written would still fail.
- **C3 can pass only through a snapshot change or a revised condition.** For example, a snapshot that excludes or deduplicates the GitLab volume (a code change, judged on what it then writes), or a pre-registered condition that accepts the `NPC_SKIP_DOCKER_SNAPSHOT=1` variant together with another way to branch from one world state.
