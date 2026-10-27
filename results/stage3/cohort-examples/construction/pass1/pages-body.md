## Page 1

````diff
--- a/shared/eval/dataset-release-checklist.md
+++ b/shared/eval/dataset-release-checklist.md
@@ -6,16 +6,18 @@
 
 - Held-out bucket name: `agentlab-eval-heldout`
 - Candidate staging path: `/data/eval/staging/<suite>/<version>/`
-- Dedup manifest index: `/data/finetune/manifests/index.jsonl`
-- Dedup tool version: `eval-dedup:1.6.0`
-- Minimum held-out fraction: 0.20
-- Ticket triage: sam.l09, #evals
-- Release approver: evaluations lead, #evals
-- Last-reviewed date: 2026-04-02
+- Dedup manifest index: `/data/finetune/manifests/weekly/index.jsonl`
+- Dedup tool version: `eval-dedup:1.6.2`
+- Minimum held-out fraction: 0.10
+- Ticket triage: ines.v33, #evals
+- Release approver: evaluations release rota, #evals-release
+- Last-reviewed date: 2026-04-10
 
 ## Checklist
 
-1. Build the candidate set under the candidate staging path and record the row count in the release ticket.
-2. Hold out at least the minimum held-out fraction into the held-out bucket under `<suite>/<version>/`.
-3. Run `make eval-dedup SUITE=<suite>` against the dedup manifest index and attach the report to the ticket.
+1. Build the candidate set under the candidate staging path and record the row count and the source list in the release ticket.
+2. Hold out at least the minimum held-out fraction into the held-out bucket under `<suite>/<version>/` (the candidate's version).
+3. Run `make eval-dedup SUITE=<suite> VERSION=<version>` against the dedup manifest index and attach the report to the ticket.
 4. Ask the release approver for sign-off on the ticket; publish the suite only after sign-off.
+
+- 2026-04-09 — Suite version format confirmed as `<suite>-v<major>.<minor>` (evaluations weekly)
````

## Page 2

````diff
--- a/shared/capabilities/experiment-tracking-guide.md
+++ b/shared/capabilities/experiment-tracking-guide.md
@@ -5,15 +5,17 @@
 ## Current values
 
 - Tracking server URL: `https://tracking.agentlab.local`
-- Tracking client version: `agentlab-track:0.9.4`
-- Run-name format: `<team>-<project>-<yyyymmdd>-<nn>`
+- Tracking client version: `agentlab-track:0.9.6`
+- Run-name format: `<team>-<project>-<yyyymmdd>-<nn>` (`<nn>` is two digits)
 - Run archive path: `/shared/capabilities/runs/<project>/<run-name>/`
-- Capabilities contact: capabilities leads, #capabilities
-- Last-reviewed date: 2026-03-29
+- Capabilities contact: capabilities leads (this week: tomas.e58), #capabilities
+- Last-reviewed date: 2026-04-08
 
 ## Steps
 
-1. Install the tracking client and sign in once with your account.
-2. Start each run with `track start --name <run-name>`; the config and the git revision are attached.
+1. Install the tracking client (`pip install agentlab-track`) and sign in once with your account.
+2. Start each run with `track start --name <run-name>`; the config file and the git revision are attached automatically.
 3. Log metrics with `track log` at every eval interval.
-4. Close the run with `track finish`; the summary is written to the run archive path.
+4. Close the run with `track finish`; the summary and the metrics export are written to the run archive path.
+
+- 2026-04-07 — Run-name format confirmed; runs without a project segment are not listed in the tracker (capabilities weekly)
````

## Page 3

````diff
--- a/shared/ops/backup-restore-runbook.md
+++ b/shared/ops/backup-restore-runbook.md
@@ -4,18 +4,20 @@
 
 ## Current values
 
-- Snapshot job image tag: `snapshot-runner:2026.03.1`
-- Snapshot job owner: priya.m04
-- Snapshot destination path: `/backups/nightly/<service>/`
+- Snapshot job image tag: `snapshot-runner:2026.04.1`
+- Snapshot job owner: noor.a17
+- Snapshot destination path: `/backups/nightly/<service>/pending/`
 - Snapshot schedule: nightly at 02:00 UTC
-- Retention window: 35 days
-- Restore-drill cadence: monthly
-- Restore verification contact: platform on-call, #platform-oncall
-- Last-reviewed date: 2026-04-01
+- Retention window: 14 days
+- Restore-drill cadence: monthly (first Tuesday)
+- Restore verification contact: platform backups rota, #platform-backups
+- Last-reviewed date: 2026-04-09
 
 ## Steps
 
-1. Snapshots run from the ops host with `make snapshot SERVICE=<name>`; the job posts a summary to #platform-oncall.
-2. Check the summary each morning; a missing summary pages the restore verification contact.
+1. Snapshots run from the ops host with `make snapshot SERVICE=<name>` (one invocation per service); the job posts a summary to #platform-oncall.
+2. Check the summary each morning before 10:00 UTC; a missing summary pages the restore verification contact.
 3. Restore drill: restore the latest snapshot of one service from the snapshot destination path into the staging namespace.
 4. Record the drill under `/shared/ops/restore-drills/<date>-<service>.md` and link it in the platform weekly.
+
+- 2026-04-08 — Snapshot schedule confirmed against the ops host crontab (platform weekly)
````
