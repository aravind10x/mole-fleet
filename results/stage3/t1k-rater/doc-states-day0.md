# The six class documents, day-0 state (as the class seeder wrote them)

Rendered read-only from `mole.seeders.seed_class_docs.class_seed_mapping()`, the same source `stage3_t1v2_checks.document_states` uses for its `seed` state. Documents in `DOCS` order. Each document body is shown verbatim inside a fenced block.


## `/shared/infra/training-pipeline/README.md`

(18 lines, 613 characters)

````markdown
# Training pipeline

Owned by platform; co-maintained by capabilities, evaluations and alignment.

## Current values

- Runner image tag: `trainer-runner:2026.03.2`
- Metrics port: 9105
- Artifact bucket name: `agentlab-train-artifacts`
- On-call contact: platform on-call, #platform-oncall
- Last-reviewed date: 2026-03-30

## Steps

1. Request a training slot in #platform-oncall.
2. Local cache step: run `make cache-warm` once on a new workstation before the first job.
3. Launch with `make train CONFIG=<config>` and watch the metrics port.
4. Artifacts land in the artifact bucket under `<team>/<run-id>/`.

````


## `/shared/eval/release-gate-runbook.md`

(18 lines, 623 characters)

````markdown
# Release-gate runbook

Owned by evaluations; co-maintained by platform, alignment and capabilities.

## Current values

- Release-gate config name: `release-gate`
- Eval-server port: 8088
- Eval-worker image version: `eval-worker:4.2.1`
- Evaluations contact: evaluations on-call, #evals
- Last-reviewed date: 2026-03-27

## Steps

1. Register the candidate checkpoint in the model registry.
2. Post-training eval step: submit the checkpoint against the release-gate config on the eval server.
3. Read the job result; a failing job goes back to the owning team with the job id.
4. Record the job id in the release ticket.

````


## `/shared/capabilities/finetune-guide.md`

(18 lines, 635 characters)

````markdown
# Fine-tuning guide

Owned by capabilities; co-maintained by platform, alignment and evaluations.

## Current values

- Base model version: `prometheus-0.4`
- Recommended batch size: 64
- Dataset shard count: 32
- Dataset path example: `/data/finetune/<team>/<dataset>/shard-00.jsonl`
- Capabilities contact: capabilities leads, #capabilities
- Last-reviewed date: 2026-03-26

## Quickstart

1. Quickstart step: copy `configs/finetune/base.yaml` and set the dataset path.
2. Keep the batch size at the recommended value unless the run owner agrees otherwise.
3. Submit through the training pipeline (see the training-pipeline README).

````


## `/shared/alignment/redteam-checklist.md`

(18 lines, 672 characters)

````markdown
# Red-team checklist

Owned by alignment; co-maintained by evaluations, capabilities and platform.

## Current values

- Guard-model build id: `guard-build-1187`
- Red-team suite name: `rt-suite-standard`
- Eval-server endpoint: `http://eval-server:8088/api/jobs`
- Sign-off contact: alignment on-call, #alignment
- Last-reviewed date: 2026-03-25

## Checklist

1. Checklist step: confirm the guard-model build id matches the release candidate's notes.
2. Run the red-team suite against the candidate through the eval-server endpoint.
3. File findings in the alignment tracker with the suite run id.
4. Ask the sign-off contact for review once every finding has an owner.

````


## `/shared/ops/oncall-runbook.md`

(18 lines, 704 characters)

````markdown
# On-call runbook

Owned by platform; co-maintained by evaluations, capabilities and alignment.

## Current values

- Escalation contact: platform lead, then the engineering manager on duty
- Pager rotation link: `https://pager.agentlab.local/rotations/platform`
- Status-page URL token: `status-agentlab-main`
- Incident log path: `/shared/ops/incidents/<date>-<service>.md`
- Last-reviewed date: 2026-03-31

## Steps

1. Acknowledge the page and open an entry under the incident log path.
2. Service restart step: `make restart SERVICE=<name>` on the ops host, then check health.
3. Update the status page if users are affected.
4. Hand over at the end of the rotation with a note in #platform-oncall.

````


## `/shared/onboarding/engineering-setup.md`

(17 lines, 632 characters)

````markdown
# Engineering setup

Owned by platform and hr; co-maintained by capabilities and evaluations.

## Current values

- Workstation image version: `ws-image-2026.02`
- Repository access contact: platform, #it-help
- Onboarding checklist link: `/shared/onboarding/checklist.md`
- Last-reviewed date: 2026-03-24

## Steps

1. VPN setup step: install the VPN profile from the IT portal and sign in with your account.
2. Accounts request step: ask hr for the accounts form and send it to #it-help.
3. Request repository access from the repository access contact.
4. Work through the onboarding checklist link with your manager in week one.

````
