# GitLab smoke, the funded agentic run: C1, C2-load, C3-run-state, C4, C5

Written 2026-10-20 (14:1x IST) **before any Docker command for this run**, as the pre-registration for the funded 5-account, 2-day agentic smoke that the first S0 sitting could not launch (disk), run at Aravind's direction after he freed about 35 GB. This file's conditions section is fixed before the run; the run record below it is filled in after; nothing above the record changes. Companion records: `work/stage3/gitlab-smoke.md` (the first sitting: C6, C2-at-idle, C3-at-boot-state, the pre-registered 3 GB conditions) and `work/stage3/s0-lenient-reread-2026-10-20.md` (the lenient bar this run is judged under).

## Pass conditions (the lenient set, fixed before this run)

From `work/stage3-research-design-2026-10-19.md` v3 section 2 as amended by Aravind on 20 Oct: **C3 at 7 GB per simulated day instead of 3 GB** ("some more flexibility if required" — Aravind's call, exercised only by him and only after the run-state number is recorded, not by this session). Everything else unchanged:

| # | condition | pass if | how measured (fixed now) |
|---|---|---|---|
| C1 | throughput | sessions per hour at concurrency ≥ 4 is **≥ 8** | manifest `completed` ÷ wall-clock hours of the session phase, from the timestamped runner log (first session-start to last session-end, seeding and day-boundary pauses excluded) |
| C2 | memory | VM memory headroom with `GITLAB_PUMA_WORKERS=2` and the other five services up, **under load**: positive headroom, no OOM kill, no container restart | `docker stats --no-stream` samples every 60 s through the run; `docker exec <gitlab> free -m` samples; `docker inspect` restart counts and OOMKilled at the end |
| C3 | disk | per-day snapshot disk growth **< 7 GB** at run state (seeded, agent-active) | `du` of the day-boundary snapshot tarballs per simulated day plus the `itb-snap` commit image sizes per day |
| C4 | failed events | failed-event share **< 10 percent** | audit rows with `exit_code != 0` ÷ all rows in the run's audit jsonl |
| C5 | merge request | a merge request opened, reviewed and merged by agents end to end | audit log `gitlab.*` events creating, commenting on or approving, and merging one MR, all `exit_code == 0` |

Pass requires all of C1 to C5. Any miss kills substrate (i) and the fall-back is (i-), recorded with the numbers. C6 (boot within two working hours) was met by the first sitting (162 s) and is not re-measured unless this boot fails.

## Pre-run state (tested, 2026-10-20)

- Host free disk: **34 GiB** on `/` and the Data volume (`df -h`, 14:0x IST), after Aravind freed about 35 GB. Docker.raw: 34 GB actual of the 60 GB VM cap, so about 26 GB of VM headroom.
- GitLab image kept locally: `ghcr.io/theagentcompany/servers-gitlab:1.0.0`, 17.5 GB. Other five lab images present.
- No `sim_runner.py` process running (`pgrep`). Docker Desktop started for this run.
- Credit (L3, L7; `credits.sh`, numbers only, 14:0x IST): key 2 `limit_remaining` **$388.79** (usage 611.21); account balance **$98.79** (total_credits 710 − total_usage 611.21). The binding cap is the account balance. The `.env`'s plain `OPENROUTER_API_KEY` is a **different** key (limit 100, untouched) and is NOT used: the launch line overrides `OPENROUTER_API_KEY` from key 2 (the `launch_line.py` convention, `<from .env key 2>`).

## Launch plan (fixed now; the command is recorded, never retyped)

- Worktree `work/mole-fork-smoke2` pinned at the current `stage3` tip **b6a252f** (L6), with `.env` copied in; code and data resolve from the worktree.
- Accounts (the first sitting's recorded plan, chosen by team merge-request mention density in the v2 bank, `bank_mr_counts.py`): `alice.kim` (alignment lead; GitLab maintainer and eval-reviewer), `deepa.a7`, `priya.a84` (alignment developers), `wei.n2` (platform), `deepa.a1` (capabilities). All five verified present in the 150-account roster (**tested**).
- Command (from the worktree, `set -a && source .env && set +a` first):

  `OPENROUTER_API_KEY="$OPENROUTER_API_KEY_2" OPENROUTER_MODEL=moonshotai/kimi-k2.6 GITLAB_PUMA_WORKERS=2 GITLAB_SIDEKIQ_CONCURRENCY=5 nohup ../mole-fork/.venv/bin/python scripts/sim_runner.py --smoke --mode agentic --days 2 --sessions-per-day 2 --concurrency 5 --personas alice.kim,deepa.a7,priya.a84,wei.n2,deepa.a1 --seed 1 --no-insiders --out data/corpus/spike/s0_gitlab_agentic.jsonl > data/corpus/spike/logs/s0_gitlab_agentic.log 2>&1 &`

  (stdout timestamped by the wrapper script `work/stage3/gitlab-smoke-logs/run2_wrap.sh` so C1's session-phase wall-clock is measurable; the manifest is at the audit path's manifest location; the day-boundary snapshots go under the worktree's snapshot dir.)
- No pinned tasks: the five accounts draw honestly from the v2 bank. **Disclosed risk, written before the run:** 20 honest sessions may draw no merge-request task, in which case C5 fails as "not achieved in 20 honest sessions" — an honest miss, not a measurement of infeasibility; a pinned follow-up would isolate the capability. No pins are used in this run so the smoke stays an honest draw.
- Seed 1 (T5's seed; the first sitting's plan named no seed).

## Estimates (written before launch)

- **Dollars:** 20 sessions at T5's $0.256 per session provider-reported = **$5.1**; at the key-delta ceiling $0.45 = **$9.0**. Stop rule: if the account-balance delta exceeds **$10**, kill the run and tear down (L3). Both caps re-checked above; balance $98.79 covers the ceiling.
- **Wall-clock:** boot about 5 min (162 s to healthy plus the rest of the stack) + seeding about 3 min + 20 sessions: at about 7 min per session with real 5-way concurrency, 40 to 90 min of session time; if per-process throughput saturates near T5's 8.8/hour, up to about 2.3 h. Two day-boundary snapshot pauses (about 5 min each with GitLab's 5.8 GB volume). Teardown about 2 min. **Total estimate 1.5 to 3 h.**
- **Disk budget:** Docker.raw grows by about 10.4 GB of live volumes plus GitLab runtime growth (call it 1 to 3 GB over two seeded days) plus `itb-snap` commit deltas; the snapshot tarballs (about 6 GB per day, the C3 quantity) land in the worktree's data dir on the host. Expected total draw about 19 to 25 GB of the 34 GiB free. **Watchdog floor 4 GiB** (samples every 20 s): below it, the watchdog SIGTERMs the runner and runs `compose down -v` on the run's project (the first sitting's `watch_boot.sh` pattern, floor raised because the budget is larger).

## Run record (filled in 2026-10-20 16:2x IST; nothing above this line changed)

### Attempt history (disclosed, all before any LLM spend)

- **Attempt 1** (14:08, $0, no containers created): died at the first `compose up` — the credential-free `DOCKER_CONFIG` hid the compose CLI plugin ("docker: unknown command: docker compose"; inside the runner it surfaced as "unknown shorthand flag: 'p'"). Fixed by symlinking `~/.docker/cli-plugins/docker-compose` into the scratch config.
- **Attempt 2** (14:08:32, sandbox `itb-npc-b8337ab7`, $0): killed about 14:10 when the launching tool shell reaped its backgrounded children on exit; the half-booted lab (GitLab up, rest never started) was torn down with `down -v` at 14:11 to 14:12. Fixed by running attempt 3 under `screen -dmS s0run` (screen owns the process tree; supervisor `run2_supervisor.sh`).
- Attempts 1 and 2's empty corpus files are preserved under `gitlab-smoke-logs/run2/attempt1-bootfail/`. No LLM call was made before attempt 3.

### The run (**tested**; scripts named; raw logs under `gitlab-smoke-logs/run2/`)

Sandbox `itb-npc-b737445d`, launched 14:12:26, runner exited **rc=0 at 16:18:00** (2 h 6 min; estimate 1.5 to 3 h). Manifest (`s0_gitlab_agentic.jsonl.resume.json`): day 2026-04-06 planned 10, completed 10, aborted 0; day 2026-04-07 planned 9, completed 9, aborted 0 (one planned session fewer on day 2, the loaf draw); `snapshot_ok` both days; `attack_sessions_planned 0` (`--no-insiders` held: "all 44 insiders running BENIGN"). 1,324 audit events. World seeded: org, email 166, owncloud 4, rocketchat 180, **gitlab 263**, plus the threat worlds and S1 variants (the honest seed).

**Cost** (**tested**, `credits.sh`): key 2 `limit_remaining` 388.79 → 384.37; balance 98.79 → 94.37: **$4.43** (estimate $5.1 to $9.0; under it because day 2 planned 9, not 10). No 402, no 429 (case-sensitive grep; the 60 case-insensitive hits were `roomName` matching "oom"). Two empty-body-200 LLM retries, each recovered on attempt 1; the retry log line reads "attempt 1/**unlimited**" — the retry loop reports no finite cap, an L15 erratum in the fork, pre-existing, not fixed here.

**Disk** (**tested**, `watch.log`, every 20 s): 34 GiB free at 14:07 → minimum **13.1 GB at 16:17** (the 4 GiB watchdog floor was never approached). Draw: Docker.raw 34 → 35 GB actual (live volumes + deltas; the `itb-snap` commit images were removed after measuring), snapshot tarballs 11.9 GB (removed with the worktree after the record was copied out). Free after full cleanup: **22 GiB**.

### The conditions

| # | result | number (**tested**; script) |
|---|---|---|
| C1 throughput | **MET** | 19 completed ÷ 1.691 session-phase hours = **11.24 per hour at `--concurrency 5`** (day 1 08:50:55→09:42:10Z = 0.854 h; day 2 09:50:06→10:40:18Z = 0.836 h; the day-boundary pause excluded as pre-registered; `run2_measures.py` + the per-day wall computation). Unadjusted across the whole session-event span including the pause: 19 ÷ 1.823 = 10.4/h, also ≥ 8 |
| C2 memory under load | **MET** | GitLab peak **4.251 GiB** at puma 2 (idle: 3.18 to 3.19); VM minimum available **1,233 MB = 1.21 GiB** (`free -m` in the gitlab container every 10 min, `stats.log` every 60 s); swap 94 MB in use at the tightest reading; no OOM, restart or 402/429 line in the runner log. Caveat (disclosed): teardown removed the containers, so `docker inspect` restart counts could not be read post-hoc; restarts are excluded indirectly (zero error lines; all six containers healthy through 131 sampler readings) |
| C3 disk, run state | **MET** | day 2026-04-06: **5,974,630,328 B = 5.97 GB** (gitlab-data 5.800, owncloud 0.155, greenmail 0.017, mongo 0.003, gitlab-config 0.00005); day 2026-04-07: **5,967,066,645 B = 5.97 GB** (gitlab-data 5.791). Both < 7 GB. The run-state gitlab-data tarball (5.79 to 5.80 GB) is **≤ the boot-state probe (5.83 GB)**: seeding (263 GitLab items) and a day of agent activity did not grow the compressed tarball; the first sitting's lower-bound concern is resolved by measurement. `itb-snap` commit images add about 314 kB per day of container-layer delta (the docker image listing's 17.5 GB double-counts base layers shared with the original image) |
| C4 failed events | **MET** | **47 of 1,324 rows `exit_code != 0` = 3.55 percent** < 10 (`run2_measures.py`; T5 without GitLab: 5.8). Failures include one `merge_mr`, two `read_file`, two `commit`, two `list_mrs` exit 1 — routine agent errors, no service-outage pattern |
| C5 merge request | **MET** | end-to-end by agents, all `exit_code == 0`: priya.a84 `open_mr` (eval/red-team-suite, source `priya/eval-logger-refactor` → main, "refactor: eval_logger structured logging + aligned categories", sim 07:46), alice.kim `get_mr` + `approve_mr` (mr_iid 1, 08:21), alice.kim `merge_mr` (mr_iid 1, 08:21). Plus across the run: 7 `open_mr`, 21 `approve_mr`, 7 `merge_mr` exit 0 |
| C6 boot | met (first sitting, 162 s) | this boot: all six containers healthy in about 5 min, no fix needed; the known chef race is absorbed inside the runner's boot |

**Verdict: all of C1 to C5 MET at the lenient bar (C3 < 7 GB). Substrate (i) passes the GitLab smoke on this host.**

### Concurrent-run disclosure (**observed**)

Another session started the owed S5.3 placeholder run (`itb-npc-0b41786c`, screen `s5crun`, `s5c_objective_benign_1.jsonl`, the no-GitLab compose) at 16:19:33 IST — one minute after this runner exited (16:18:00). This run's final credit read (16:14, balance 94.365) predates its first LLM call, so the $4.43 and the C1 hours are unaffected. Its lab was up while this record's worktree and `itb-snap` images were removed; nothing of its project was touched.

### Substrate implications (for Aravind's design amendment; **inferred** where forward-looking)

- (i) is measured viable at 5-account scale: 11.24 sessions/hour at one process. The design's "three or four parallel processes" for a 50-account branch is **not** measured here: one Docker VM hosting several full labs at concurrency 4+ each, under amd64 emulation, is the open question, and so is GitLab's memory (peak 4.25 GiB of the 7.65 GiB VM at 5 accounts).
- Per-day snapshots on this host run about **6 GB per simulated day** at this GitLab state; a 50-account world grows `gitlab-data` somewhat more. Branch-from-one-snapshot storage must be budgeted at about 6 GB × days × branches — the cost the 3 GB bar was written to cap, and the number Aravind's 7 GB bar accepts.
- What this does not change: brief 07's sections 2 to 9 ran on (i-) and stand; the rung-0 REDESIGN verdict and its three amendments are untouched; the lenient bar remains Aravind's to fix in the design before any 50-account (i) run — this record supplies the run-state numbers to fix it with.

### Record inventory

`gitlab-smoke-logs/run2/`: `s0_gitlab_agentic.jsonl` (1,324 events), `s0_gitlab_agentic.transcripts.jsonl`, `s0_gitlab_agentic.jsonl.resume.json` (manifest), `s0_gitlab_agentic.raw.log`, `measures.out`, `watch.log`, `stats.log`, `credits.log`, `supervisor.log`, `attempt1-bootfail/` (attempts 1-2). Scripts: `run2_wrap.sh`, `run2_supervisor.sh`, `run2_watchdog.sh`, `run2_stats.sh`, `run2_credits.sh`, `run2_measures.py` (in `gitlab-smoke-logs/`). The worktree `mole-fork-smoke2` and the `itb-snap` images were removed after the record was copied out; the GitLab image is kept.
