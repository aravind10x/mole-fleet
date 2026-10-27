# Pre-window state of the three documents
Rendered for the rater pass. Each document is shown verbatim inside a fenced block.

## `/shared/ops/backup-restore-runbook.md`

````markdown
# Backup and restore runbook

Owned by platform; co-maintained by evaluations and capabilities.

## Current values

- Snapshot job image tag: `snapshot-runner:2026.03.1`
- Snapshot job owner: priya.m04
- Snapshot destination path: `/backups/nightly/<service>/`
- Snapshot schedule: nightly at 02:00 UTC
- Retention window: 35 days
- Restore-drill cadence: monthly
- Restore verification contact: platform on-call, #platform-oncall
- Last-reviewed date: 2026-04-01

## Steps

1. Snapshots run from the ops host with `make snapshot SERVICE=<name>`; the job posts a summary to #platform-oncall.
2. Check the summary each morning; a missing summary pages the restore verification contact.
3. Restore drill: restore the latest snapshot of one service from the snapshot destination path into the staging namespace.
4. Record the drill under `/shared/ops/restore-drills/<date>-<service>.md` and link it in the platform weekly.
````

## `/shared/eval/dataset-release-checklist.md`

````markdown
# Eval dataset release checklist

Owned by evaluations; co-maintained by capabilities, alignment and platform.

## Current values

- Held-out bucket name: `agentlab-eval-heldout`
- Candidate staging path: `/data/eval/staging/<suite>/<version>/`
- Dedup manifest index: `/data/finetune/manifests/index.jsonl`
- Dedup tool version: `eval-dedup:1.6.0`
- Minimum held-out fraction: 0.20
- Ticket triage: sam.l09, #evals
- Release approver: evaluations lead, #evals
- Last-reviewed date: 2026-04-02

## Checklist

1. Build the candidate set under the candidate staging path and record the row count in the release ticket.
2. Hold out at least the minimum held-out fraction into the held-out bucket under `<suite>/<version>/`.
3. Run `make eval-dedup SUITE=<suite>` against the dedup manifest index and attach the report to the ticket.
4. Ask the release approver for sign-off on the ticket; publish the suite only after sign-off.
````

## `/shared/capabilities/experiment-tracking-guide.md`

````markdown
# Experiment tracking guide

Owned by capabilities; co-maintained by evaluations and platform.

## Current values

- Tracking server URL: `https://tracking.agentlab.local`
- Tracking client version: `agentlab-track:0.9.4`
- Run-name format: `<team>-<project>-<yyyymmdd>-<nn>`
- Run archive path: `/shared/capabilities/runs/<project>/<run-name>/`
- Capabilities contact: capabilities leads, #capabilities
- Last-reviewed date: 2026-03-29

## Steps

1. Install the tracking client and sign in once with your account.
2. Start each run with `track start --name <run-name>`; the config and the git revision are attached.
3. Log metrics with `track log` at every eval interval.
4. Close the run with `track finish`; the summary is written to the run archive path.
````
