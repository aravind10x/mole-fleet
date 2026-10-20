# S0 lenient re-read: the GitLab smoke under a revised C3 threshold

**VERDICT UNDER THE LENIENT BAR: substrate (i) is UNDECIDED — the pre-registered kill is withdrawn, but (i) is not passed either: C1, C4 and C5 are still unmeasured, and the funded 5-account, 2-day smoke that would decide them does not fit today's host disk (about 10 GiB free against the about 25 GB the record says it needs beyond the image).**

Written 2026-10-20 at Aravind's request, after the brief-07 report. This is a **post-hoc re-reading of the recorded numbers under a threshold Aravind set** (C3: 7 GB instead of 3 GB, "some more flexibility if required"). It is not a re-run and not a re-registration: no Docker command and no LLM call were made for it, $0 was spent, and the pre-registered record (`work/stage3/gitlab-smoke.md`) stands unchanged. Nothing here retroactively changes any other section of the prep report, all of which ran on substrate (i-), lab mode without GitLab. Tags as in the record: **tested** (run, command named), **observed** (read in a named file), **inferred** (stated basis).

## The conditions under the lenient bar

C1 (sessions per hour at concurrency ≥ 4 ≥ 8), C2 (VM memory headroom at `GITLAB_PUMA_WORKERS=2` with the other five services up), C4 (failed-event share < 10 percent), C5 (a merge request opened, reviewed and merged by agents) and C6 (boot within two working hours) are unchanged. Only C3 changes: **per-day snapshot disk growth under 7 GB** (Aravind, 20 Oct; flexibility beyond 7 GB noted but not fixed — see the closing ask). The all-of-C1-to-C5 pass rule is unchanged: a pass still requires every one of them.

## Condition by condition, under the lenient bar

| # | condition | under the 3 GB bar (record) | under the 7 GB bar (this re-read) |
|---|---|---|---|
| C3 | per-day snapshot growth < 7 GB | MISS (5.83 GB GitLab alone) | **pass at the measured lower bound, unproven at run state** (below) |
| C6 | boot within two working hours | met | met, unchanged (162 s, one attempt, **tested**) |
| C2 | memory headroom, puma 2, six services up | met at idle only | met at idle only, unchanged (2.33 GiB available, 0 restarts, 0 OOM, **tested**); under seeding or concurrency-4 load still unmeasured |
| C1 | throughput ≥ 8/hour at concurrency ≥ 4 | not measured | **not measured** — needs the funded run |
| C4 | failed-event share < 10 percent | not measured | **not measured** — needs the funded run (T5 without GitLab: 5.8 percent, **observed**, `work/stage2/t5-report.md`) |
| C5 | merge request round trip by agents | not measured | **not measured** — needs the funded run |

**C3 arithmetic.** The only measured figure is the `gitlab-data` tarball at boot state, unseeded: 5.83 GB (**tested**, `snapsize.sh`, recorded in `gitlab-smoke.md`). The other five services' tarballs were about 150 MB in T5 (**observed**, `t5-report.md` line 63). Full-lab per-day growth at boot state is therefore about **5.98 GB per simulated day** (**inferred**), passing 7 GB with about 1 GB of margin. It remains a lower bound on three counts: the 5.83 GB is GitLab only and at boot state, and a seeded lab with two days of agent activity (merge requests, comments, repository and Postgres growth) writes more. Whether the run-state figure stays under 7 GB is exactly what the funded smoke would measure; the boot-state margin is about 1 GB, so the "flexibility if required" may be needed.

## Why the verdict is undecided, not pass

The original kill rested wholly on C3 ("any miss is a kill for (i)", and C3 was the only measured miss). At 7 GB that leg is withdrawn. But pass requires all of C1 to C5, and three of them were never measured because the agentic smoke was not launched. So substrate (i) moves from **killed** to **open, pending the funded smoke** — the same place it was before the C3 measurement, minus the disk-design objection.

## What finishing S0 would now take (the binding constraint is host disk, not the bar)

- **Disk.** Live volumes about 10.4 GB (`gitlab-data` 9.44 GB plus about 1 GB for the others) plus two day-snapshots at about 6 GB each: about 25 GB free beyond the 17.5 GB image (**inferred**, the record's own "what a later attempt would need"). Measured today, 2026-10-20 13:40 IST: **10 GiB free** on `/` and the Data volume, Docker.raw at 60 GB (**tested**, `df -h`). The run does not fit; with the lab merely up, free disk was already 1.40 GiB. Options: free about 25 GB (the 25.41 GB of reclaimable Docker images is mostly other projects — Aravind's call), put Docker's disk on an external volume, or run with `NPC_SKIP_DOCKER_SNAPSHOT=1` — but the skip leaves C3 unmeasured, which re-fails the all-of rule, so it is not a route to a pass.
- **Money and wall-clock**, unchanged from the record's plan: 5 accounts × 2 days = 20 sessions, $5.1 to $9.0 at T5's $0.256 per session (up to $0.45 on the key delta), stop at $10; 1.5 to 3 hours; Kimi, `--no-insiders`, worktree pinned to the current commit (L6); both OpenRouter caps checked before launch (L3, L7; at the last check key 2 `limit_remaining` $388.79, account balance $98.79, **observed**); rules-mode rehearsal and launch-line generation first (L15).

## What changes downstream if (i) is later revived

- Brief 07's executed substrate stays (i-); every later section of the prep report names (i-) and is unaffected.
- The rung-1 table's GitLab README row, labelled "for reference (substrate (i), killed)", reads "for reference (substrate (i), undecided)".
- The design's branch-from-one-snapshot plan was sized against the 3 GB bar. At about 6 GB per day, a 5-day, 50-account branch holds about 30 GB of day snapshots per branch, roughly 2.3 times the bar the design was written around. Accepting that is Aravind's call (the threshold is his) and belongs in the design amendment beside the three amendments the prep report's section 2 already names.
- The `docker rmi ghcr.io/theagentcompany/servers-gitlab:1.0.0` recovery advice in the prep report's section 1 stands **unless** (i) is pursued.

## One ask before any funded run (pre-registration discipline, L8/L10)

The 7 GB bar passes today only at a boot-state lower bound. Before the funded smoke is launched, the final C3 number — 7 GB, or the flexible figure — should be fixed in writing and the seeded, run-state measurement judged against that fixed number, not adjusted after seeing it.

## After the funded run (appended 2026-10-20 16:2x IST; everything above is the pre-run record and stands)

Aravind freed about 35 GB and directed the funded run; it was launched under the 7 GB bar as written above (no flexibility exercised) and **passed every condition**. Full record: `work/stage3/gitlab-smoke-agentic-2026-10-20.md` (pre-registered before any Docker command, filled after). In brief: 5 accounts × 2 days, 19 of 19 planned sessions completed, $4.43, 2 h 6 min, host disk 34 GiB → min 13.1 GB.

| # | verdict | number (**tested**) |
|---|---|---|
| C1 | MET | 11.24 sessions/hour at concurrency 5 (19 ÷ 1.691 session-phase hours) |
| C2 under load | MET | VM minimum available 1.21 GiB; GitLab peak 4.251 GiB at puma 2; no OOM/restart observed |
| C3 run state | MET | 5.97 GB per simulated day (both days; run-state gitlab-data 5.79 to 5.80 GB ≤ the boot-state 5.83 GB) |
| C4 | MET | 47 of 1,324 events failed = 3.55 percent |
| C5 | MET | MR !1 on `eval/red-team-suite`: opened by priya.a84, approved and merged by alice.kim, all exit 0 |

**The verdict above moves from undecided to: substrate (i) passes the GitLab smoke at 5-account scale on this host.** The caveats that survive: multi-process parallelism for a 50-account branch, GitLab's memory at 50 accounts, and the ~6 GB/day branch-from-snapshot storage are unmeasured (the run record's "substrate implications" section); brief 07's other sections ran on (i-) and stand; the rung-0 REDESIGN and its three amendments are untouched by this result.
