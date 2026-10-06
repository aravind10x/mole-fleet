"""Filter the benign task bank down to tasks a Docker-free run can actually do.

    .venv/bin/python scripts/filter_inprocess_tasks.py

Reads `bootstrap/benign_task_bank_v2.yaml` (shape `{key: {team, focal_benign,
variants: [str]}}`) and keeps only tasks that reference the in-process services
(Plane, model registry, eval server, secrets store, org directory) and NOTHING
that needs a Docker service (GitLab, ownCloud, email, RocketChat) or a service
the lab does not have at all. Writes `bootstrap/benign_task_bank_inprocess.yaml`
in the same shape (every key of the v2 bank is kept, possibly with zero
variants) and prints a per-team table.

If `bootstrap/release_workflow_tasks.yaml` exists (shape `{team: [str, ...]}`),
its tasks are merged into the matching team's variants (the entry is created if
missing). They pass through the same classifier, so the output never contains
a task that matches a drop rule.

Classification is deliberately conservative: a task is dropped if it matches ANY
drop rule, and kept only if it also matches at least one keep rule.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
BOOTSTRAP = REPO / "bootstrap"
SRC = BOOTSTRAP / "benign_task_bank_v2.yaml"
DST = BOOTSTRAP / "benign_task_bank_inprocess.yaml"
RELEASE_TASKS = BOOTSTRAP / "release_workflow_tasks.yaml"

_I = re.IGNORECASE

# (regex, reason). Any match drops the task. Order only affects which reason
# is reported first; every matching reason is counted.
DROP_RULES: list[tuple[re.Pattern[str], str]] = [
    # GitLab / code hosting
    (re.compile(r"git\s?lab|github", _I), "gitlab"),
    (re.compile(r"\bMRs?\b|!\d+"), "gitlab: MR"),
    (re.compile(r"merge request|pull request|\bPRs?\b", _I), "gitlab: MR"),
    (re.compile(r"\bcommit|\bbranch|\brepo(s|sitory|sitories)?\b|\bpush(ed|ing)?\b|\bfork",
                _I), "gitlab: commit/branch/repo"),
    (re.compile(r"\bCI\b|\.gitlab-ci|pipeline config", _I), "gitlab: CI"),
    (re.compile(r"\b(refactor|unit tests?|lint|code review|codebase|scripts?|cli)\b", _I),
     "gitlab: code work"),
    (re.compile(r"(?<!eval )(?<!gate )\bconfigs?\b", _I), "config file"),
    (re.compile(r"\b(eval/red-team-suite|models/|training-data/|infra/|data/|monitors/|"
                r"weights/|eval-data|cold-storage|safety-reports|customer-data)", _I),
     "repo/owncloud path"),
    # ownCloud / files
    (re.compile(r"own\s?cloud", _I), "owncloud"),
    (re.compile(r"\bupload|\bdownload|\bfolders?\b|\bshared drive|\bdirectory listing", _I),
     "owncloud: upload/folder"),
    (re.compile(r"(^|[\s`'\"(])/[\w{}.-]+/"), "owncloud: path"),
    (re.compile(r"[\w{}/-]+\.(py|ya?ml|md|json|jsonl|csv|tsv|txt|ipynb|sh|toml|cfg|ini|pdf|"
                r"docx?|xlsx?|pptx?|parquet|log|env|go|ckpt|pt|bin|safetensors|js|ts|rs|sql|html)\b",
                _I), "file path"),
    (re.compile(r"\battach", _I), "attachment (no file service)"),
    (re.compile(r"\b(files?|docs?|document|spreadsheet|wiki|notebook|slides?|deck|"
                r"runbook|readme|memo)\b", _I), "owncloud: document"),
    # email
    (re.compile(r"e-?mail|\bmail\b|\binbox\b|\bcc\b", _I), "email"),
    (re.compile(r"\brepl(y|ies|ied)\b|send (a |an |the )?(note|message|memo|summary|update|"
                r"reminder|follow-up) to|\bwrite to\b|\bnotify\b|\bping\b", _I),
     "email: reply/send to"),
    # RocketChat / chat
    (re.compile(r"rocket\s?chat|\bslack\b|\bchat\b", _I), "rocketchat"),
    (re.compile(r"\bchannels?\b|(^|[\s`'\"(])#[A-Za-z][\w-]*", _I), "rocketchat: channel"),
    (re.compile(r"\bDMs?\b|direct message|\bmessage\b", _I), "rocketchat: DM/message"),
    (re.compile(r"\bpost(s|ed|ing)?\b|\bannounce|\bstand-?up\b|\bthread\b", _I),
     "rocketchat: post"),
    # services the lab does not have at all
    (re.compile(r"\b(jira|confluence|notion|google (doc|sheet|drive)s?|jupyter|grafana|"
                r"datadog|splunk|s3|slurm|kubernetes|kubectl|airflow|tableau|looker|"
                r"salesforce|workday|greenhouse|docusign|zoom|calendar|meeting|"
                r"dashboard|w&b)\b", _I), "service not in the lab"),
]

# (regex, service). At least one must match for a task to be kept.
KEEP_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bplane\b|\btickets?\b|\bissues?\b", _I), "plane"),
    (re.compile(r"model[- ]registry|\bregistry\b|\bcheckpoints?\b|\bregister", _I),
     "model_registry"),
    (re.compile(r"eval[- ]?server|\beval(uation)?s? (run|job|suite|config)|\bsubmit|"
                r"release[- ]gate|reference[- ]suite", _I), "eval_server"),
    (re.compile(r"secrets?[- ]store|\brotat(e|ion|ing)\b|\btokens?\b|\bsecrets?\b|"
                r"access polic", _I), "secrets_store"),
    (re.compile(r"org (directory|chart)|\bdirectory\b|look up|\bcolleague", _I), "org"),
]


def classify(task: str) -> tuple[bool, list[str]]:
    """(keep?, reasons). Reasons are the matching drop rules, or a single
    "no in-process service mentioned" when nothing keeps it."""
    reasons = [reason for rx, reason in DROP_RULES if rx.search(task)]
    if reasons:
        return False, list(dict.fromkeys(reasons))
    if not any(rx.search(task) for rx, _svc in KEEP_RULES):
        return False, ["no in-process service mentioned"]
    return True, []


def filter_bank(bank: dict, extra: dict[str, list[str]] | None = None
                ) -> tuple[dict, dict[str, dict]]:
    """Return (filtered bank in the v2 shape, per-key stats)."""
    out: dict = {}
    stats: dict[str, dict] = {}
    extra = dict(extra or {})
    for key, entry in bank.items():
        entry = entry or {}
        team = entry.get("team") or key
        st = {"team": team, "total": 0, "kept": 0, "dropped": 0, "reasons": Counter(),
              "merged": 0}
        focal = entry.get("focal_benign")
        if focal:
            st["total"] += 1
            ok, why = classify(focal)
            if ok:
                st["kept"] += 1
            else:
                st["dropped"] += 1
                st["reasons"].update(why)
                focal = None
        variants: list[str] = []
        merged = extra.pop(key, []) + (extra.pop(team, []) if team != key else [])
        for i, task in enumerate(list(entry.get("variants") or []) + merged):
            from_merge = i >= len(entry.get("variants") or [])
            st["total"] += 1
            ok, why = classify(task)
            if ok and task not in variants:
                variants.append(task)
                st["kept"] += 1
                st["merged"] += int(from_merge)
            elif not ok:
                st["dropped"] += 1
                st["reasons"].update(why)
        out[key] = {"team": team, "focal_benign": focal, "variants": variants}
        stats[key] = st
    # Teams only present in the release-workflow file get a fresh entry.
    for team, tasks in extra.items():
        st = {"team": team, "total": 0, "kept": 0, "dropped": 0, "reasons": Counter(),
              "merged": 0}
        variants = []
        for task in tasks or []:
            st["total"] += 1
            ok, why = classify(task)
            if ok and task not in variants:
                variants.append(task)
                st["kept"] += 1
                st["merged"] += 1
            elif not ok:
                st["dropped"] += 1
                st["reasons"].update(why)
        out[team] = {"team": team, "focal_benign": None, "variants": variants}
        stats[team] = st
    return out, stats


def format_table(stats: dict[str, dict]) -> str:
    lines = [f"{'team':<14} {'total':>5} {'kept':>5} {'dropped':>7} {'merged':>6}  top dropped reasons"]
    tot = Counter()
    for key, st in stats.items():
        top = ", ".join(f"{r} ({n})" for r, n in st["reasons"].most_common(3))
        lines.append(f"{key:<14} {st['total']:>5} {st['kept']:>5} {st['dropped']:>7} "
                     f"{st['merged']:>6}  {top}")
        tot.update({k: st[k] for k in ("total", "kept", "dropped", "merged")})
    lines.append(f"{'ALL':<14} {tot['total']:>5} {tot['kept']:>5} {tot['dropped']:>7} "
                 f"{tot['merged']:>6}")
    zero = [k for k, st in stats.items() if st["kept"] == 0]
    lines.append(f"teams with zero in-process tasks: {', '.join(zero) if zero else 'none'}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="filter_inprocess_tasks")
    ap.add_argument("--src", type=Path, default=SRC)
    ap.add_argument("--dst", type=Path, default=DST)
    ap.add_argument("--release-tasks", type=Path, default=RELEASE_TASKS)
    args = ap.parse_args(argv)

    bank = yaml.safe_load(args.src.read_text(encoding="utf-8")) or {}
    extra = None
    if args.release_tasks.exists():
        extra = yaml.safe_load(args.release_tasks.read_text(encoding="utf-8")) or {}
        print(f"merging {sum(len(v or []) for v in extra.values())} release-workflow "
              f"tasks from {args.release_tasks.name}")
    else:
        print(f"({args.release_tasks.name} not present; nothing to merge)")
    out, stats = filter_bank(bank, extra)
    header = ("# GENERATED by scripts/filter_inprocess_tasks.py from "
              f"{args.src.name} -- do not edit by hand.\n"
              "# Only tasks that use the in-process services (plane, model_registry,\n"
              "# eval_server, secrets_store, org); loaded by load_task_bank(bank=\"inprocess\").\n")
    args.dst.write_text(header + yaml.safe_dump(out, sort_keys=False, allow_unicode=True,
                                                width=100), encoding="utf-8")
    print(f"wrote {args.dst.relative_to(REPO) if args.dst.is_relative_to(REPO) else args.dst}")
    print(format_table(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
