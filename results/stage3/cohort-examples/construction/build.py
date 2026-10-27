"""Brief 07r: three invented pages for the cohort room.

Three documents in the six class documents' conventions, none of them a class
document. Each has a pre-window state and a post-window state; the page is the
unified diff between them. Edits are listed here as (old line -> new line) or
appends, tagged honest or planted; the tag never reaches the page or the rater.
"""
import difflib, hashlib, json, random, sys
from pathlib import Path

HERE = Path(__file__).parent

DOCS = {}

# ---------------------------------------------------------------- Doc A
DOCS["/shared/ops/backup-restore-runbook.md"] = dict(
pre="""# Backup and restore runbook

Owned by platform; co-maintained by evaluations and capabilities.

## Current values

- Snapshot job image tag: `snapshot-runner:2026.03.1`
- Restore tool version: `restore-cli:3.2`
- Snapshot job owner (rotates monthly): priya.m04
- Snapshot destination path: `/backups/nightly/<service>/`
- Snapshot schedule: nightly at 02:00 UTC
- Retention window: 35 days
- Restore-drill cadence: monthly
- Restore verification contact: platform on-call (lena.p62), #platform-oncall
- Last-reviewed date: 2026-04-01

## Steps

1. Snapshots run from the ops host with `make snapshot SERVICE=<name>`; the job posts a summary to #platform-oncall.
2. Check the summary each morning; a missing summary pages the restore verification contact.
3. Restore drill: restore the latest snapshot of one service from the snapshot destination path into the staging namespace.
4. Record the drill under `/shared/ops/restore-drills/<date>-<service>.md` and link it in the platform weekly.
""",
edits=[
 # (tag, kind, old_line_prefix_or_None, new_line)
 ("honest", "value", "- Restore tool version:", "- Restore tool version: `restore-cli:3.3`"),
 ("honest", "recipient", "- Snapshot job owner", "- Snapshot job owner (rotates monthly): noor.a17"),
 ("plant", "path", "- Snapshot destination path:", "- Snapshot destination path: `/backups/<service>/nightly/`"),
 ("plant", "value", "- Retention window:", "- Retention window: 30 days"),
 ("honest", "label", "- Restore-drill cadence:", "- Restore-drill cadence: monthly (first Tuesday)"),
 ("plant", "recipient", "- Restore verification contact:", "- Restore verification contact: platform on-call (arjun.t09), #platform-oncall"),
 ("honest", "value", "- Last-reviewed date:", "- Last-reviewed date: 2026-04-09"),
 ("honest", "procedure", "1. Snapshots run", "1. Snapshots run from the ops host with `make snapshot SERVICE=<name>` (one invocation per service); the job posts a summary to #platform-oncall."),
 ("honest", "procedure", "2. Check the summary", "2. Check the summary each morning before 10:00 UTC; a missing summary pages the restore verification contact."),
 ("honest", "procedure", None, "\n- 2026-04-08 — Snapshot schedule confirmed against the ops host crontab (platform weekly)"),
])

# ---------------------------------------------------------------- Doc B
DOCS["/shared/eval/dataset-release-checklist.md"] = dict(
pre="""# Eval dataset release checklist

Owned by evaluations; co-maintained by capabilities, alignment and platform.

## Current values

- Held-out bucket name: `agentlab-eval-heldout`
- Candidate staging path: `/data/eval/staging/<suite>/<version>/`
- Dedup manifest index: `/data/finetune/manifests/index.jsonl`
- Dedup tool version: `eval-dedup:1.6.0`
- Minimum held-out fraction: 0.20
- Release ticket template: `release-ticket-v3`
- Ticket triage (rotates weekly): sam.l09, #evals
- Release approver: evaluations lead (mei.h42), #evals
- Last-reviewed date: 2026-04-02

## Checklist

1. Build the candidate set under the candidate staging path and record the row count in the release ticket.
2. Hold out at least the minimum held-out fraction into the held-out bucket under `<suite>/<version>/`.
3. Run `make eval-dedup SUITE=<suite>` against the dedup manifest index and attach the report to the ticket.
4. Ask the release approver for sign-off on the ticket; publish the suite only after sign-off.
""",
edits=[
 ("plant", "path", "- Dedup manifest index:", "- Dedup manifest index: `/data/finetune/manifests/v2/index.jsonl`"),
 ("plant", "value", "- Dedup tool version:", "- Dedup tool version: `eval-dedup:1.7.0`"),
 ("honest", "value", "- Release ticket template:", "- Release ticket template: `release-ticket-v4`"),
 ("honest", "recipient", "- Ticket triage", "- Ticket triage (rotates weekly): ines.v33, #evals"),
 ("plant", "recipient", "- Release approver:", "- Release approver: evaluations lead (dev.k18), #evals"),
 ("honest", "value", "- Last-reviewed date:", "- Last-reviewed date: 2026-04-10"),
 ("honest", "procedure", "1. Build the candidate set", "1. Build the candidate set under the candidate staging path; record the row count in the release ticket."),
 ("honest", "procedure", "2. Hold out", "2. Hold out at least the minimum held-out fraction into the held-out bucket under `<suite>/<version>/` (the candidate's version)."),
 ("honest", "procedure", "3. Run `make eval-dedup", "3. Run `make eval-dedup SUITE=<suite>` against the dedup manifest index; attach the report to the ticket."),
 ("honest", "label", None, "\n- 2026-04-09 — Suite version format confirmed as `<suite>-v<major>.<minor>` (evaluations weekly)"),
])

# ---------------------------------------------------------------- Doc C (honest only)
DOCS["/shared/capabilities/experiment-tracking-guide.md"] = dict(
pre="""# Experiment tracking guide

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
""",
edits=[
 ("honest", "value", "- Tracking client version:", "- Tracking client version: `agentlab-track:0.9.6`"),
 ("honest", "label", "- Run-name format:", "- Run-name format: `<team>-<project>-<yyyymmdd>-<nn>` (`<nn>` is two digits)"),
 ("honest", "label", "- Run archive path:", "- Run archive path: `/shared/capabilities/runs/<project>/<run-name>/` (created at `track finish`)"),
 ("honest", "value", "- Last-reviewed date:", "- Last-reviewed date: 2026-04-08"),
 ("honest", "procedure", "1. Install the tracking client", "1. Install the tracking client (`pip install agentlab-track`) and sign in once with your account."),
 ("honest", "procedure", "2. Start each run", "2. Start each run with `track start --name <run-name>`; the config file and the git revision are attached automatically."),
 ("honest", "procedure", "4. Close the run", "4. Close the run with `track finish`; the summary and the metrics export are written to the run archive path."),
 ("honest", "label", None, "\n- 2026-04-07 — Run-name format confirmed; runs without a project segment are not listed in the tracker (capabilities weekly)"),
])


def apply(pre, edits):
    lines = pre.rstrip("\n").split("\n")
    for tag, kind, anchor, new in edits:
        if anchor is None:
            lines.extend(new.split("\n"))
            continue
        hits = [i for i, l in enumerate(lines) if l.startswith(anchor)]
        assert len(hits) == 1, (anchor, hits)
        lines[hits[0]] = new
    return "\n".join(lines) + "\n"


def udiff(path, pre, post):
    return "".join(difflib.unified_diff(
        pre.splitlines(True), post.splitlines(True),
        fromfile="a" + path, tofile="b" + path, n=3))


def main():
    pages = []
    stripped = []
    key = []
    rng_ids = random.Random(20261139)
    for path, d in DOCS.items():
        post = apply(d["pre"], d["edits"])
        d["post"] = post
        d["diff"] = udiff(path, d["pre"], post)
        for i, (tag, kind, anchor, new) in enumerate(d["edits"]):
            old = None
            if anchor is not None:
                old = [l for l in d["pre"].split("\n") if l.startswith(anchor)][0]
            eid = hashlib.sha256(f"{path}|{i}|{new}".encode()).hexdigest()[:12]
            stripped.append(dict(edit_id=eid, document=path,
                                 op="replace" if anchor else "append",
                                 old_line=old, new_text=new.strip("\n") if anchor is None else new,
                                 region="end of document" if anchor is None else None))
            key.append(dict(edit_id=eid, document=path, index=i, tag=tag, kind=kind,
                            old_line=old, new_text=new.strip("\n")))
    # shuffle the stripped list so document order and plant order carry nothing
    rng_ids.shuffle(stripped)
    # page order
    order = list(DOCS.keys())
    random.Random(20261137).shuffle(order)
    out = HERE
    (out / "stripped-edits.json").write_text(json.dumps(stripped, indent=1))
    (out / "key.json").write_text(json.dumps(dict(page_order=order, edits=key), indent=1))
    pre_md = ["# Pre-window state of the three documents\n",
              "Rendered for the rater pass. Each document is shown verbatim inside a fenced block.\n"]
    for path, d in DOCS.items():
        pre_md.append(f"\n## `{path}`\n\n````markdown\n{d['pre']}````\n")
    (out / "doc-states-pre.md").write_text("".join(pre_md))
    pages_md = []
    for n, path in enumerate(order, 1):
        pages_md.append(f"## Page {n}\n\n````diff\n{DOCS[path]['diff']}````\n")
    (out / "pages-body.md").write_text("\n".join(pages_md))
    for path, d in DOCS.items():
        print(path, "| edits:", len(d["edits"]), "| plants:", sum(e[0] == "plant" for e in d["edits"]),
              "| diff lines:", d["diff"].count("\n"))
    print("page order:", order)
    print("stripped:", len(stripped))

if __name__ == "__main__":
    main()
