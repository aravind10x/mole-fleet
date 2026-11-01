#!/usr/bin/env python3
"""Brief 31 G4 (2026-11-01): S3's pre-flight check, run before anything else in S3.

Reads the fenced `s1-preflight-sha256` block from the committed `work/stage3/b3/plan.md` (the plan's dated note of
2026-11-01 night; `shasum -a 256 -c` format, hash, two spaces, path from the project root), recomputes every listed
file's sha256 and refuses to start on any mismatch, printing every hash it found. The block is read from the working
plan.md only when it is byte-identical to the fork's committed copy (`results/stage3/b3/plan.md` at HEAD). When the
plan holds more than one block, the last one is the list: a dated note that moves a pin restates the whole block
(brief 31's rule: an opt-in change with its defaults unchanged and tested, and brief 31's G1 request comparison and G2
check repeated against the new file, before the note).

Also refused: a listed script under work/checks whose fork copy (`work/mole-fork/scripts/stage3/`) differs, and, once
every file matches, a prompt component of the pinned `stage3_views.py` that no longer reproduces the one sealed in
`views/calibration-v1.json` (shared-harm/v1, the P_author and O_diff system prompts; plan.md's consistency check).
With `--config`, S3's own values (seeds, replicates, margins) are checked against the plan's. With `--out`, the hashes
it ran on are written for S3's record. Prints hashes, paths and counts only.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_preflight.py [--config S3.json] [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent                 # work/checks
ROOT = HERE.parents[1]                                 # tais-project-selection
FORK = ROOT / "work" / "mole-fork"
PLAN = "work/stage3/b3/plan.md"
PLAN_IN_FORK = "results/stage3/b3/plan.md"
FENCE = "s1-preflight-sha256"
VERSION = "b3-preflight/v0"
CALIBRATION = "work/stage3/views/calibration-v1.json"
# plan.md's "Values the pre-flight checks against its own configuration (not files)", transcribed; the test reads them
# back out of the plan's paragraph.
PLACEMENT_SEED = 20261181
PLAN_VALUES: dict[str, Any] = {"placement_seed": PLACEMENT_SEED, "bootstrap_seed": 20261152, "bootstrap_replicates": 2000,
                               "tie_seed": 20261112, "m_s_carrier": 18.22, "m_s_second": 19.37, "m_L": 18.22}
ARMS_REQUIRED, ARMS_IF_APPROVED = (1, 2, 3, 4), (5, 6)
LINE = re.compile(r"^([0-9a-f]{64})  (\S.*)$")


class Malformed(Exception):
    pass


def arm_seed(t: int) -> int:
    """plan.md section 3: one random.Random(20261181 × 100 + 10 t) per arm."""
    return PLACEMENT_SEED * 100 + 10 * t


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def parse_blocks(text: str) -> list[tuple[int, list[tuple[str, str]]]]:
    """Every fenced FENCE block: [(first line number, [(sha256, path)])]. Refuses a malformed line, a duplicate path,
    an absolute path or one that leaves the project root, an empty or unclosed block."""
    blocks: list[tuple[int, list[tuple[str, str]]]] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip() == f"```{FENCE}":
            start, entries, seen = i + 1, [], set()
            i += 1
            while i < len(lines) and lines[i].strip() != "```":
                m = LINE.match(lines[i])
                if not m:
                    raise Malformed(f"plan.md line {i + 1}: not '<sha256>  <path>'")
                h, path = m.group(1), m.group(2)
                if path.startswith("/") or ".." in Path(path).parts:
                    raise Malformed(f"plan.md line {i + 1}: path must be relative to the project root")
                if path in seen:
                    raise Malformed(f"plan.md line {i + 1}: {path} listed twice")
                seen.add(path)
                entries.append((h, path))
                i += 1
            if i >= len(lines):
                raise Malformed(f"plan.md line {start}: the {FENCE} block is not closed")
            if not entries:
                raise Malformed(f"plan.md line {start}: the {FENCE} block is empty")
            blocks.append((start + 1, entries))
        i += 1
    if not blocks:
        raise Malformed(f"plan.md holds no {FENCE} block")
    return blocks


def committed_plan(root: Path, fork: Path) -> bytes | None:
    try:
        return subprocess.run(["git", "-C", str(fork), "show", f"HEAD:{PLAN_IN_FORK}"], check=True, capture_output=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def check_files(root: Path, entries: Sequence[tuple[str, str]], fork_scripts: Path | None) -> list[dict]:
    rows = []
    for want, path in entries:
        p = root / path
        got = sha256_file(p) if p.is_file() else None
        row = {"path": path, "expected": want, "found": got, "status": "OK" if got == want else ("MISSING" if got is None else "MISMATCH")}
        if fork_scripts is not None and path.startswith("work/checks/") and path.endswith(".py"):
            fp = fork_scripts / Path(path).name
            row["fork_copy"] = sha256_file(fp) if fp.is_file() else None
            if row["status"] == "OK" and row["fork_copy"] != want:
                row["status"] = "FORK COPY DIFFERS"
        rows.append(row)
    return rows


def check_prompts(root: Path) -> list[dict]:
    """The pinned stage3_views.py's prompt components against the ones sealed in calibration-v1.json."""
    if str(root / "work" / "checks") not in sys.path:
        sys.path.insert(0, str(root / "work" / "checks"))
    import stage3_views as sv
    seal = json.loads((root / CALIBRATION).read_text(encoding="utf-8"))
    sha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()   # noqa: E731
    pairs = [("shared-harm/v1", seal["shared_harm_sha256"], sv.SHARED_HARM_SHA256),
             ("P_author system prompt", seal["views"]["P_author"]["prompt"]["system_sha256"], sha(sv.system_prompt("P_author", 0))),
             ("O_diff system prompt", seal["views"]["O_diff"]["prompt"]["system_sha256"], sha(sv.system_prompt("O_diff", 0)))]
    return [{"component": n, "sealed": a, "found": b, "status": "OK" if a == b else "MISMATCH"} for n, a, b in pairs]


def check_values(config: Mapping[str, Any]) -> list[str]:
    """S3's own values against the plan's: every PLAN_VALUES key equal; arm seeds by plan section 3's formula, arms
    1 to 4 required, 5 and 6 allowed (only if approved at S2, which this check cannot see and S3's record states)."""
    bad = [f"{k}: plan {v!r}, config {config.get(k)!r}" for k, v in PLAN_VALUES.items() if config.get(k) != v]
    arms = {int(t): s for t, s in (config.get("arm_seeds") or {}).items()}
    for t in ARMS_REQUIRED:
        if t not in arms:
            bad.append(f"arm_seeds: arm {t} missing")
    for t, s in sorted(arms.items()):
        if t not in ARMS_REQUIRED + ARMS_IF_APPROVED:
            bad.append(f"arm_seeds: arm {t} is not one of the plan's")
        elif s != arm_seed(t):
            bad.append(f"arm_seeds: arm {t} plan {arm_seed(t)}, config {s}")
    return bad


def run(root: Path = ROOT, fork: Path = FORK, config: Mapping[str, Any] | None = None, prompts: bool = True) -> dict:
    plan_path = root / PLAN
    text_bytes = plan_path.read_bytes()
    out: dict[str, Any] = {"version": VERSION, "plan": PLAN, "plan_sha256": hashlib.sha256(text_bytes).hexdigest(), "refusals": []}
    committed = committed_plan(root, fork)
    out["plan_matches_fork_head"] = committed == text_bytes
    if not out["plan_matches_fork_head"]:
        out["refusals"].append(f"{PLAN} differs from the fork's committed {PLAN_IN_FORK} at HEAD"
                               + (" (no committed copy found)" if committed is None else ""))
    try:
        blocks = parse_blocks(text_bytes.decode("utf-8"))
    except Malformed as exc:
        out["refusals"].append(f"malformed: {exc}")
        out["files"], out["pass"] = [], False
        return out
    line, entries = blocks[-1]
    out["blocks"], out["block_used_at_line"], out["n_files"] = len(blocks), line, len(entries)
    out["files"] = check_files(root, entries, fork / "scripts" / "stage3")
    out["refusals"] += [f"{r['status']}: {r['path']}" for r in out["files"] if r["status"] != "OK"]
    if prompts and not out["refusals"]:   # the views module is imported only once it is the pinned one
        out["prompts"] = check_prompts(root)
        out["refusals"] += [f"prompt component {r['component']} does not reproduce the sealed one" for r in out["prompts"] if r["status"] != "OK"]
    if config is not None:
        out["values"] = {"config": dict(config), "mismatches": check_values(config)}
        out["refusals"] += [f"value {m}" for m in out["values"]["mismatches"]]
    out["pass"] = not out["refusals"]
    return out


def report(out: Mapping[str, Any]) -> list[str]:
    L = [f"plan {out['plan']} sha256 {out['plan_sha256']} (matches the fork's committed copy: {out['plan_matches_fork_head']})"]
    if "blocks" in out:
        L.append(f"block at line {out['block_used_at_line']} ({out['blocks']} block(s) in the plan; the last is read): {out['n_files']} files")
    for r in out.get("files", []):
        fork = f"  fork {r['fork_copy']}" if "fork_copy" in r else ""
        L.append(f"{r['status']:<18} expected {r['expected']}  found {r['found']}  {r['path']}{fork}")
    for r in out.get("prompts", []):
        L.append(f"{r['status']:<18} sealed   {r['sealed']}  found {r['found']}  {r['component']}")
    for m in (out.get("values") or {}).get("mismatches", []):
        L.append(f"VALUE MISMATCH     {m}")
    L.append("PRE-FLIGHT PASS" if out["pass"] else f"PRE-FLIGHT REFUSED ({len(out['refusals'])}): " + "; ".join(out["refusals"]))
    return L


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", help="S3's values as JSON (PLAN_VALUES keys and arm_seeds {t: seed})")
    ap.add_argument("--out", help="write the hashes the check ran on (for S3's record)")
    ns = ap.parse_args(argv)
    config = json.loads(Path(ns.config).read_text(encoding="utf-8")) if ns.config else None
    out = run(config=config)
    print("\n".join(report(out)))
    if ns.out:
        Path(ns.out).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
