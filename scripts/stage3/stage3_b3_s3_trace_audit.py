#!/usr/bin/env python3
"""Brief 33 A4 (S3, 2026-11-02): the trace audit adapted to S3. A counts-only wrapper around brief 15 A5.4's
`stage3_b3_trace_audit.py` (2a409344; not edited), run on the S3 session's transcript at the end of each stage.

How it closes the location hole: the pinned script allows, by location, any path under `--writer-dir`'s
`work/stage3/b3/` and joins every relative token under the writer directory. S3 therefore (1) passes an empty directory
made for the purpose, `work/stage3/b3/s3-trace-empty/`, as an absolute path, and (2) normalises every token the script
extracts from the transcript against the project root before the audit (the `paths` format), so that every opened path is
absolute, none lies under the empty writer directory, and every allowed path comes from the policy's `--allow` entries
(absolute too; the script joins an absolute entry unchanged). A relative token such as `work/stage3/b3/x` is thus never
allowed by location.

The policy `work/stage3/b3/s3-trace-policy.json` lists the allowed categories (the pre-flight's 26 files, A2's inputs,
the payload and control files, the briefs and records A0 names, S3's own outputs and cache directory, the code under
`work/checks/` and its fork copies, the session's scratchpad and task files) as path prefixes and exact paths, and the
never-open patterns (`work/stage3/red/`, persona files, `archived-scores*`, the anchor sheet and its draw file, another
brief's judge cache, the writer paste files). `policy` writes it; `audit` prints the counts: opened, allowed, outside
(split into existing files and non-existent tokens, since the script's path regex also matches fragments of shell
commands), and the never-open count. Outside paths are printed only when none is in the never-open set.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s3_trace_audit.py audit --trace <transcript.jsonl>
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_trace_audit as ta  # noqa: E402  (the pinned script, 2a409344; used, not edited)

VERSION = "b3-s3-trace-audit/v0"
PROJECT = HERE.parents[1]
EMPTY_DIR = PROJECT / "work/stage3/b3/s3-trace-empty"
POLICY = PROJECT / "work/stage3/b3/s3-trace-policy.json"
PINNED_SCRIPT_SHA256 = "2a409344"
NEVER_OPEN = ["work/stage3/red/*", "*/personas/*", "*archived-scores*", "work/stage3/b3/rater/human-anchor-*", "*/judge-cache*.jsonl",
              "work/stage3/b3/part-w-*", "work/stage3/b3/p2-glm53-message.md", "work/stage3/b3/writer-record-*", "work/stage3/b3/checklist-b3-*"]
NEVER_OPEN_EXCEPT = ["work/stage3/b3/cache-s3/*"]          # S3's own caches are its outputs
ALLOW_PREFIXES = ["work/checks/", "work/mole-fork/scripts/stage3/", "work/mole-fork/results/stage3/b3/", "work/mole-fork/.venv/", "work/mole-fork/.git",
                  "work/mole-fork/bootstrap/org_template.yaml", "work/mole-fork/data/corpus/spike/prefix_rw_v2c.jsonl", "work/mole-fork/results/stage3/",
                  "work/stage3/b3/s3-", "work/stage3/b3/cache-s3/", "work/stage3/b3/b3-results", "work/stage3/b3/comprehension/", "work/stage3/b3/rater/key-b3.json",
                  "work/stage3/b3/rater/ratings-b3-", "work/stage3/b3/rater/stripped-triples-b3.json", "work/stage3/b3/checks-b3-", "work/stage3/b3/controls-b3-",
                  "work/stage3/b3/payloads-b3-", "work/stage3/b3/power-simulation", "work/stage3/b3/inserter-dry-run-", "work/stage3/b3/s1-populations-v0.json",
                  "work/stage3/b3/s2-estimate-v0", "work/stage3/b3/judge-client-equivalence-v0", "work/stage3/b3/lone-line-arm", "work/stage3/b3/plan.md",
                  "work/stage3/b3/plan-draft.md", "work/stage3/b3/review/", "work/stage3/b3/s2/", "work/stage3/b3/prestep-", "work/stage3/b3/brief-",
                  "work/stage3/b1/", "work/stage3/b0/", "work/stage3/q1q2-synthetic/", "work/stage3/views/", "work/stage3/t1v3/", "work/stage3/t1v2/payloads-v2.json",
                  "work/stage3/t1k-rater/stripped-triples.json", "work/stage3/pilot/measure/sol-provider-check.json", "work/stage3/INDEX.md", "work/stage3/prep-report.md",
                  "work/stage3/legibility/", "work/stage3/elicitation/", "briefs/", "STATUS.md", "CONTEXT.md", "PLAN.md", "README.md", "archive/", "pick1/",
                  "work/stage3/", "work/upstream-data/", "work/lessons.md", "work/"]
ALLOW_ABSOLUTE_PREFIXES = ["/private/tmp/claude-501/", "/Users/aravind/.claude/", "/tmp/", "/private/var/folders/", "/dev/null", "/usr/bin/", "/bin/"]


def sha256_file(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def absolutise(token: str, root: Path = PROJECT) -> str:
    t = token.strip()
    if t.startswith("./"):
        t = t[2:]
    if not os.path.isabs(t):
        t = os.path.join(str(root), t)
    return os.path.normpath(t)


def rel(p: str, root: Path = PROJECT) -> str | None:
    try:
        return str(Path(p).relative_to(root))
    except ValueError:
        return None


def is_never_open(p: str, root: Path = PROJECT) -> bool:
    r = rel(p, root)
    if r is None:
        return any(fnmatch.fnmatch(p, pat) for pat in NEVER_OPEN if pat.startswith("*"))
    if any(fnmatch.fnmatch(r, pat) for pat in NEVER_OPEN_EXCEPT):
        return False
    return any(fnmatch.fnmatch(r, pat) or fnmatch.fnmatch(r, pat.rstrip("*") + "*") for pat in NEVER_OPEN)


def is_allowed_category(p: str, root: Path = PROJECT) -> bool:
    if is_never_open(p, root):
        return False
    r = rel(p, root)
    if r is None:
        return any(p.startswith(x) or p == x.rstrip("/") for x in ALLOW_ABSOLUTE_PREFIXES)   # a directory token is its own prefix
    return r == "." or any(r == x.rstrip("/") or r.startswith(x) for x in ALLOW_PREFIXES)


def opened_tokens(trace: Path, fmt: str = "claude-jsonl") -> set[str]:
    raw = ta.paths_from_claude_jsonl(str(trace)) if fmt == "claude-jsonl" else ta.paths_from_list(str(trace))
    return {absolutise(t) for t in raw if t and t not in ("/", ".")}


def build_policy(trace: Path) -> dict[str, Any]:
    """The allow list: every opened token that an allowed category admits, as an absolute path; the categories recorded."""
    opened = opened_tokens(trace)
    allow = sorted(p for p in opened if is_allowed_category(p))
    return {"version": VERSION, "pinned_script": {"path": "work/checks/stage3_b3_trace_audit.py", "sha256": sha256_file(HERE / "stage3_b3_trace_audit.py")},
            "writer_dir": str(EMPTY_DIR), "writer_dir_rule": "an empty directory made for the purpose; every token is absolutised against the project root first, so nothing is allowed by location",
            "allow_prefixes": ALLOW_PREFIXES, "allow_absolute_prefixes": ALLOW_ABSOLUTE_PREFIXES, "never_open": NEVER_OPEN, "never_open_except": NEVER_OPEN_EXCEPT,
            "allow": allow, "n_opened_at_policy_time": len(opened)}


def run_audit(trace: Path, policy: Mapping[str, Any], fmt: str = "claude-jsonl", writer_dir: Path | None = None) -> dict[str, Any]:
    wd = Path(writer_dir or policy.get("writer_dir") or EMPTY_DIR)
    wd.mkdir(parents=True, exist_ok=True)
    if any(wd.iterdir()):
        raise SystemExit(f"refusing: the writer directory {wd} is not empty")
    opened = opened_tokens(trace, fmt)
    res = ta.audit(opened, str(wd.resolve()), list(policy["allow"]))
    outside = res["opened_outside"]
    never = [p for p in outside if is_never_open(p)]
    existing = [p for p in outside if os.path.exists(p) and p not in never]
    tokens = [p for p in outside if not os.path.exists(p) and p not in never]
    return {"version": VERSION, "trace": str(trace), "format": fmt, "writer_dir": str(wd), "writer_dir_empty": True, "pinned_script_sha256": sha256_file(HERE / "stage3_b3_trace_audit.py"),
            "opened": len(opened), "allowed": len(res["opened_ok"]), "outside": len(outside), "outside_existing_files": len(existing),
            "outside_non_existent_tokens": len(tokens), "never_open": len(never), "verdict": "PASS" if not never and not existing else ("NEVER-OPEN" if never else "OUTSIDE"),
            "outside_paths": None if never else {"existing": sorted(existing), "tokens": sorted(tokens)[:200]}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mode", choices=("policy", "audit"))
    ap.add_argument("--trace", required=True)
    ap.add_argument("--format", choices=("claude-jsonl", "paths"), default="claude-jsonl")
    ap.add_argument("--policy", default=str(POLICY))
    ap.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    if sha256_file(HERE / "stage3_b3_trace_audit.py")[:8] != PINNED_SCRIPT_SHA256:
        raise SystemExit("refusing: stage3_b3_trace_audit.py is not the pinned 2a409344")
    if ns.mode == "policy":
        pol = build_policy(Path(ns.trace))
        Path(ns.policy).write_text(json.dumps(pol, indent=1) + "\n")
        print(json.dumps({"policy": ns.policy, "allow": len(pol["allow"]), "opened": pol["n_opened_at_policy_time"]}))
        return 0
    pol = json.loads(Path(ns.policy).read_text())
    res = run_audit(Path(ns.trace), pol, ns.format)
    if ns.out:
        Path(ns.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "outside_paths"}, indent=1))
    if res["outside_paths"]:
        print(json.dumps(res["outside_paths"], indent=1))
    return 0 if res["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
