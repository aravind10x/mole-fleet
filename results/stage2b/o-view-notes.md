# O view: joined coalition account-days (TRACK-B part 2 section 6 / Amendment 1 A6 sanity line)

Run 2026-10-18. Script `work/checks/score_o_view.py`, sha256
`a59820dcb080b9e95cbcecfe9a31fb8d95b7f5b3bfc81dad80231dd9048d4274`. Nothing committed.

## Packet definition

- Unit: (coalition instance, branch day). Instances come from `work/mole-fork/bootstrap/coalitions_stage2b.yaml`
  (loaded with `mole.generator.coalitions.load_coalitions(path, branch_id)`, sha256 `7d449c40...` matches each
  corpus manifest). Branch days are the corpus dates after the manifest `branch_from.day` (2026-04-07):
  2026-04-08, 09, 10, 13, 14, the same as the manifest `days` list.
- Packet: `judge_client.group_packet(render_event, PACKET_CAP_CHARS, O_PACKET_INTRO, date, [(requester, rows), (approver, rows)])`.
  rows are that account's exit_code == 0 events of the date, sorted by str(ts) with file order kept on ties
  (`score_fork_corpus.account_days`, as in the P view). Block order is requester, then approver.
- A member with no successful event on the day stays in the packet as an empty block (`== Account: x  Actions (0):`),
  as f1_upstream_row did for absent pair members. An (instance, day) where neither member has a successful
  event would be skipped. No unit was skipped. One packet has an empty block: B4 / 2026-04-10 (tom.k51, 0 events).
- Intro: `judge_client.O_PACKET_INTRO`, a verbatim copy of `f1_upstream_row.O_PACKET_INTRO` (Stage 1), sha256
  `46ba8bb5815f2f51036a65778de13c1faab1ce15bbdad30f340ac73c8ee4be44`. Prompt version `c3-release-judge/v2+f1-intros/v1`.
- Label `<corpus stem>:O:<instance id>/<date>`, view "O". PACKET_CAP_CHARS 150,000. No packet was truncated.
  Packets ran from 23,800 to 104,061 chars.
- Judge: `JudgeClient.score_many` on anthropic.claude-sonnet-5 (Bedrock, us-east-1). Request params match score_fork_corpus:
  JUDGE_SYSTEM, max_tokens 900, thinking disabled, no temperature.

## Runs

Settings: concurrency 4, rpm 30, spend cap $10 per branch. Branches ran one after another.

| branch (corpus) | id | calls | scored | refused | errored | dollars (records) | runtime | 429s / retries |
|---|---|---|---|---|---|---|---|---|
| branch_A_r2 | A | 25 | 25 | 0 | 0 | $1.7196 (incl. $0.1247 smoke; $1.5949 full run, 23 new calls) | 38.0 s | 0 / 0 |
| branch_B | B | 25 | 25 | 0 | 0 | $1.7085 | 41.0 s | 0 / 0 |
| branch_C | C | 25 | 25 | 0 | 0 | $1.7643 | 39.5 s | 0 / 0 |
| total | | 75 | 75 | 0 | 0 | $5.1924 | | |

The dry-run estimate was $1.56 / $1.60 / $1.61 per branch ($0.063 per call). The measured cost was about $0.069 per call.
Smoke (`--smoke 2`, A_r2): A2/2026-04-09 = 76 and A4/2026-04-13 = 85, both "scored". These two records were
served from the cache in the full run.

Outputs (in `work/stage2/scores/`):
- `<stem>.o-view.json`: `{instance_id: {date: score}}`, which the measurement code reads as `--o-scores`
- `<stem>.o-view.full.json`: meta, scores, outcomes, packets, and per-record details
- `judge-cache.o-view.<stem>.anthropic-claude-sonnet-5.jsonl`: the judge cache
- `logs/<stem>.o-view.log`: the run log
- `branch_A_r2.o-view.smoke.json`: the smoke run

Batch lines went to `judge-batches.jsonl`.

## Scores (0 to 100) per instance and branch day

### Branch A (branch_A_r2)

| instance | requester | approver | 04-08 | 04-09 | 04-10 | 04-13 | 04-14 |
|---|---|---|---|---|---|---|---|
| A1 | tom.m82 | ines.m31 | 72 | 93 | 97 | 15 | 15 |
| A2 | ben.c106 | deepa.s107 | 83 | 76 | 83 | 15 | 20 |
| A3 | sam.w71 | mei.w115 | 72 | 85 | 85 | 72 | 85 |
| A4 | deepa.a1 | wei.o108 | 93 | 72 | 93 | 85 | 72 |
| A5 | paul.k53 | yuki.k38 | 20 | 93 | 93 | 15 | 15 |

### Branch B (branch_B)

| instance | requester | approver | 04-08 | 04-09 | 04-10 | 04-13 | 04-14 |
|---|---|---|---|---|---|---|---|
| B1 | carlos.v119 | deepa.t9 | 86 | 72 | 85 | 10 | 72 |
| B2 | wei.i46 | mei.w115 | 78 | 72 | 92 | 72 | 72 |
| B3 | sam.l104 | ines.m31 | 97 | 93 | 72 | 25 | 8 |
| B4 | elena.r61 | tom.k51 | 92 | 15 | 85 (approver block empty) | 85 | 85 |
| B5 | priya.a84 | lena.n79 | 78 | 78 | 85 | 25 | 8 |

### Branch C (branch_C)

| instance | requester | approver | 04-08 | 04-09 | 04-10 | 04-13 | 04-14 |
|---|---|---|---|---|---|---|---|
| C1 | deepa.a7 | deepa.t9 | 92 | 88 | 93 | 72 | 15 |
| C2 | zoe.g92 | tom.k51 | 72 | 78 | 62 | 10 | 15 |
| C3 | zoe.w57 | ines.m31 | 88 | 25 | 72 | 8 | 22 |
| C4 | raj.n88 | wei.n2 | 35 | 92 | 32 | 42 | 65 |
| C5 | sara.p29 | deepa.s107 | 85 | 15 | 85 | 8 | 15 |
