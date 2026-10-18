# Density anchor: honest pair-interaction density of a human ticket tracker

Order-of-magnitude anchor for the B1 write co-touch density (TRACK-B part 1, section 5; `work/checks/haystack.py`, `L1_mean`), measured on four weeks of the Apache Software Foundation Jira. Script: `work/checks/external_density_anchor.py`. Machine-readable output: `work/stage2/density-anchor.json` (per-day rows included). Raw tables: `work/stage2/density-anchor.tables.md`.

## Headline

| population | N | w = 1 L1 > 0 (mean over days) | w = 7 L1 > 0 | active / day (w = 1) | writes / account-day mean (p50, p90) |
|---|---:|---:|---:|---:|---|
| ASF Jira, all human accounts | 1,168 | 0.0026 | 0.0020 | 166.4 | 5.73 (2, 11) |
| ASF Jira, top-50 humans | 50 | 0.0073 | 0.0169 | 31.3 | 16.23 (7, 36) |
| ASF Jira, top-150 humans | 150 | 0.0041 | 0.0088 | 71.8 | 9.91 (4, 20) |
| SPARK project only, all humans | 142 | 0.0146 | 0.0107 | 18.5 | 6.25 (3, 12.3) |
| SPARK project only, top-50 humans | 50 | 0.0224 | 0.0221 | 13.9 | 7.80 (3, 16) |
| fork prefix_v1 (simulated, 50 accounts), any type / ticket | 50 | 0.562 / 0.256 | n/a (w = 2: 0.733 / 0.432) | n/a | 26.20 (25, 40) |
| gpt53_single_day (released), any / ticket | 142 | 0.010 / 0.009 | 0.073 / 0.065 | n/a | 4.53 (4, 8) |
| kimi_k26_single_day (released), any / ticket | 142 | 0.068 / 0.044 | 0.301 / 0.216 | n/a | 13.35 (12, 24) |

_Caption: Jira rows are this run with bots filtered; simulated rows are from `b1-haystack.prefix_v1.md` (F-T3), `b1-haystack.md` (B1-T2) and `honest-churn.prefix_v1.md`._

Released corpora at N = 50 (B1-T5, induced random sub-orgs, any type, w = 1): gpt53_single_day 0.009, kimi_k26_single_day 0.068. The human top-50 figure (0.0073) is on the order of gpt53 and about 77 times below the fork prefix (0.562 any type; 35 times below on tickets alone, 0.256).

## Dataset provenance

- Source: ASF Jira, https://issues.apache.org/jira, public REST API `GET /rest/api/2/search`, anonymous, JQL `updated >= "2026-08-30" ORDER BY key ASC`, `fields=project,created,reporter,creator,comment,status,issuetype`, `expand=changelog`, 100 issues per page, 1 s between pages.
- Relation to the approved candidate: this is the Apache instance of the Public Jira Dataset (Montgomery, Lüders, Maalej, MSR 2022), read from the same API the dataset was crawled from. The current Zenodo release (record 15719919, `2025-06-23 ThePublicJiraDataset.zip`, CC BY 4.0) is one 5.8 GB MongoDB-dump zip and holds nothing after June 2025, so a four-week window was crawled directly instead.
- Fetched 2026-10-18 14:56 to 15:10 UTC: 164 pages, 16,385 issues (every issue updated since 2026-08-30, so every issue with an event in the window). Size 22,811,053 bytes gzip (331,038,994 bytes JSON). Location `work/external-data/apache-jira-2026-09/page_0000.json.gz` to `page_0163.json.gz`; per-file sha256 in `work/stage2/density-anchor.sha256`; sha256 of the concatenated pages in name order `c8dd4c8e699d448dfdfcaad5adfa2a1e15ca6c335c739cfdffd5997942eccbc4`. Fetch log: `work/stage2/density-anchor.fetch-log.json`.
- Licence: public issue-tracker content of the ASF. The crawl carries no separate dataset licence (the Zenodo release of the same source is CC BY 4.0). Raw pages stay local and are not redistributed. Outputs hold only aggregates and the names of the filtered bot accounts.
- No comment list or changelog was truncated in the export (comment `total` = returned comments, changelog `total` = returned histories, for all 16,385 issues).

## Adapter: field mapping

Artefact = issue key (one artefact type, `ticket`). Every event is a write touch. The export has **no read events**, so the any-touch density (W > 0) equals the write co-touch density and is not reported separately.

| event kind | account | timestamp | count in window (all accounts) |
|---|---|---|---:|
| create | issue `creator` (fallback `reporter`) | issue `created` | 4,371 |
| comment | comment `author` | comment `created` | 9,401 |
| comment_edit | comment `updateAuthor`, when `updated` − `created` > 60 s | comment `updated` | 282 |
| change_status | changelog history entry touching `status` | history `created` | 6,333 |
| change | any other changelog history entry (resolution, assignee, fix version, link, remote link, worklog, labels, description, attachment, ...) | history `created` | 47,984 |

_Caption: one changelog history entry (one save in Jira, possibly several fields) is one write._

Dropped: changelog entries without an author; admin bulk operations (every item an `Admin-*` field; 599 such items, all from one infrastructure administrator), plus that account's comment edits within 5 minutes of such an operation. Votes and watches carry no timestamp in the export and are not counted. Days are UTC calendar days, 2026-08-31 (Mon) to 2026-09-27 (Sun), 28 days.

Bots: accounts matching the regex `BOT_RE` in the script, checked by hand against the top 45 accounts. Filtered: `githubbot` (ASF GitHub Bot, 39,010 writes; remote links and worklogs mirrored from GitHub pull requests), `jira-bot` (ASF subversion and git services), `hudson`, `jenkinsjira`, `ignitetcbot`, `ci-cassandra.apache.org`. Together 41,660 of 68,371 writes (61%). Human set: 26,711 writes by 1,168 accounts on 8,316 issues.

## Metric

As `haystack.py`: for each day d, the accounts active in [d − w + 1, d]; the share of their unordered pairs that both wrote on at least one common issue inside the window; mean over days where at least two accounts are active. An account-day is an account with at least one event on a UTC day; here every event is a write, so active = write-active. w = 7 is reported on days 7 to 28 only (22 full windows; `haystack.py` instead truncates windows at the corpus's first day). Induced sub-populations: the N most active accounts of the four weeks by write count (N = 50, 100, 150, 300) and a random 50 (`random.Random(20261014).sample(sorted(accounts), 50)`), counting only their own events.

## Per-day density, bots filtered (primary)

| population | N | w | days | active / day mean | L1 > 0 mean | p50 | min | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 1,168 | 1 | 28 | 166.4 | 0.0026 | 0.0023 | 0.0016 | 0.0048 |
| all | 1,168 | 7 | 22 | 575.3 | 0.0020 | 0.0020 | 0.0017 | 0.0023 |
| top50 | 50 | 1 | 28 | 31.3 | 0.0073 | 0.0074 | 0.0000 | 0.0158 |
| top50 | 50 | 7 | 22 | 46.8 | 0.0169 | 0.0167 | 0.0115 | 0.0222 |
| top100 | 100 | 1 | 28 | 55.1 | 0.0048 | 0.0048 | 0.0000 | 0.0100 |
| top100 | 100 | 7 | 22 | 94.4 | 0.0116 | 0.0118 | 0.0088 | 0.0143 |
| top150 | 150 | 1 | 28 | 71.8 | 0.0041 | 0.0042 | 0.0015 | 0.0093 |
| top150 | 150 | 7 | 22 | 137.4 | 0.0088 | 0.0089 | 0.0076 | 0.0101 |
| top300 | 300 | 1 | 28 | 103.6 | 0.0035 | 0.0034 | 0.0018 | 0.0064 |
| top300 | 300 | 7 | 22 | 244.9 | 0.0050 | 0.0051 | 0.0041 | 0.0057 |
| random50 | 50 | 1 | 27 | 7.4 | 0.0040 | 0.0000 | 0.0000 | 0.0667 |
| random50 | 50 | 7 | 22 | 24.8 | 0.0040 | 0.0038 | 0.0000 | 0.0109 |

_Caption: weekday vs weekend at w = 1: all 0.0023 (20 days) vs 0.0035 (8); top50 0.0073 vs 0.0071._

## Per-day density, bots kept (sensitivity)

| population | N | w = 1 L1 > 0 mean | w = 7 L1 > 0 mean | active / day (w = 1) |
|---|---:|---:|---:|---:|
| all | 1,174 | 0.0117 | 0.0048 | 170.9 |
| top50 | 50 | 0.0701 | 0.0679 | 33.0 |
| top150 | 150 | 0.0287 | 0.0248 | 75.1 |
| random50 | 50 | 0.0015 | 0.0046 | 8.0 |

_Caption: the GitHub mirror bot co-touches most issues, so keeping it inflates density, mostly through pairs that include the bot._

## Single project (SPARK, the busiest human project in the window, bots filtered)

| population | N | w = 1 L1 > 0 mean | w = 7 L1 > 0 mean | active / day (w = 1) |
|---|---:|---:|---:|---:|
| all | 142 | 0.0146 | 0.0107 | 18.5 |
| top50 | 50 | 0.0224 | 0.0221 | 13.9 |
| top100 | 100 | 0.0184 | 0.0134 | 17.0 |
| random50 | 50 | 0.0229 | 0.0248 | 8.9 |

_Caption: one project is closer to one team; the instance-wide top 50 spans many unrelated projects (Camel, Spark, Flink, Cassandra, Ozone, ...)._

## Churn (writes per account-day, bots filtered)

| population | account-days | writes | mean | p50 | p90 |
|---|---:|---:|---:|---:|---:|
| all | 4,659 | 26,711 | 5.73 | 2 | 11 |
| top50 | 877 | 14,235 | 16.23 | 7 | 36 |
| top150 | 2,010 | 19,929 | 9.91 | 4 | 20 |
| SPARK, all | 518 | 3,237 | 6.25 | 3 | 12.3 |

_Caption: beside fork prefix_v1 26.20 (p50 25, p90 40), gpt53 4.53 (4, 8), kimi 13.35 (12, 24) from `honest-churn.prefix_v1.md`; with bots kept, all-account mean is 14.29._

## Caveats

- The metric is scale-dependent. With 1,168 accounts the share of co-writing pairs is 0.0026; restricting to the 50 most active raises it to 0.0073 at w = 1 and 0.017 at w = 7, and one project gives 0.015 to 0.022. The comparable simulated number is the 50-account fork world, so the top-50 and single-project rows are the anchor, not the all-account row.
- Humans, not agents; one tracker, not a whole organisation. Much ASF collaboration (code review, discussion) happens on GitHub pull requests and mailing lists, which this export sees only through the filtered mirror bot. The density is therefore a lower bound for the organisation's interaction density, and a fair one only for its ticket tracker.
- The simulated corpora have reads and several artefact types; here there is one type and no reads, so the like-for-like comparison is the simulated `ticket` row (fork 0.256, gpt53 0.009, kimi 0.044 at w = 1); the `any` row (fork 0.562) sums over six types.
- Simulated "days" are corpus days of an agent run, not calendar days; w = 7 here uses full windows, while released-corpus w = 7 values truncate early windows.
- Bot filtering is a name regex checked against the top accounts; low-volume automation accounts below the top 45 may remain. Release-time bulk edits by humans (fix-version and status changes across many issues) are kept as honest writes.
- Days are UTC; contributors span many time zones, so one local working day can straddle two UTC days.

## Command

```
work/mole-fork/.venv/bin/python -I work/checks/external_density_anchor.py fetch \
    --since 2026-08-30 \
    --out-dir /Users/aravind/KruxAI/tais-project-selection/work/external-data/apache-jira-2026-09 \
    --log-file /Users/aravind/KruxAI/tais-project-selection/work/stage2/density-anchor.fetch-log.json

work/mole-fork/.venv/bin/python -I work/checks/external_density_anchor.py measure \
    --inputs /Users/aravind/KruxAI/tais-project-selection/work/external-data/apache-jira-2026-09/page_*.json.gz \
    --start 2026-08-31 --end 2026-09-27 \
    --out-json /Users/aravind/KruxAI/tais-project-selection/work/stage2/density-anchor.json \
    --out-md /Users/aravind/KruxAI/tais-project-selection/work/stage2/density-anchor.tables.md
```
