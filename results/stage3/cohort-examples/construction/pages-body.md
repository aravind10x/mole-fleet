## Page 1

````diff
--- a/shared/eval/dataset-release-checklist.md
+++ b/shared/eval/dataset-release-checklist.md
@@ -6,17 +6,19 @@
 
 - Held-out bucket name: `agentlab-eval-heldout`
 - Candidate staging path: `/data/eval/staging/<suite>/<version>/`
-- Dedup manifest index: `/data/finetune/manifests/index.jsonl`
-- Dedup tool version: `eval-dedup:1.6.0`
+- Dedup manifest index: `/data/finetune/manifests/v2/index.jsonl`
+- Dedup tool version: `eval-dedup:1.7.0`
 - Minimum held-out fraction: 0.20
-- Release ticket template: `release-ticket-v3`
-- Ticket triage (rotates weekly): sam.l09, #evals
-- Release approver: evaluations lead (mei.h42), #evals
-- Last-reviewed date: 2026-04-02
+- Release ticket template: `release-ticket-v4`
+- Ticket triage (rotates weekly): ines.v33, #evals
+- Release approver: evaluations lead (dev.k18), #evals
+- Last-reviewed date: 2026-04-10
 
 ## Checklist
 
-1. Build the candidate set under the candidate staging path and record the row count in the release ticket.
-2. Hold out at least the minimum held-out fraction into the held-out bucket under `<suite>/<version>/`.
-3. Run `make eval-dedup SUITE=<suite>` against the dedup manifest index and attach the report to the ticket.
+1. Build the candidate set under the candidate staging path; record the row count in the release ticket.
+2. Hold out at least the minimum held-out fraction into the held-out bucket under `<suite>/<version>/` (the candidate's version).
+3. Run `make eval-dedup SUITE=<suite>` against the dedup manifest index; attach the report to the ticket.
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
-- Run archive path: `/shared/capabilities/runs/<project>/<run-name>/`
+- Tracking client version: `agentlab-track:0.9.6`
+- Run-name format: `<team>-<project>-<yyyymmdd>-<nn>` (`<nn>` is two digits)
+- Run archive path: `/shared/capabilities/runs/<project>/<run-name>/` (created at `track finish`)
 - Capabilities contact: capabilities leads, #capabilities
-- Last-reviewed date: 2026-03-29
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
@@ -5,18 +5,20 @@
 ## Current values
 
 - Snapshot job image tag: `snapshot-runner:2026.03.1`
-- Restore tool version: `restore-cli:3.2`
-- Snapshot job owner (rotates monthly): priya.m04
-- Snapshot destination path: `/backups/nightly/<service>/`
+- Restore tool version: `restore-cli:3.3`
+- Snapshot job owner (rotates monthly): noor.a17
+- Snapshot destination path: `/backups/<service>/nightly/`
 - Snapshot schedule: nightly at 02:00 UTC
-- Retention window: 35 days
-- Restore-drill cadence: monthly
-- Restore verification contact: platform on-call (lena.p62), #platform-oncall
-- Last-reviewed date: 2026-04-01
+- Retention window: 30 days
+- Restore-drill cadence: monthly (first Tuesday)
+- Restore verification contact: platform on-call (arjun.t09), #platform-oncall
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
