"""Brief 15 amendment A5.4: audit a writer harness's tool-call trace for the files it opened.

Fixed before any writer's output is read. Usage:
    python3 -I stage3_b3_trace_audit.py --trace <file> --writer-dir <dir> [--format claude-jsonl|paths] \
        [--allow <relative path>]... [--out <json>]
Exit 0 when every path opened lies inside the allowed set (the four input files at their relative
paths under --writer-dir, plus anything under <writer-dir>/work/stage3/b3/ that is not one of the two
inputs there, i.e. the writer's own outputs); exit 2 otherwise, listing the offending paths.

Formats:
  claude-jsonl  a Claude Code session transcript: every tool_use input's file_path / path / pattern /
                command fields are scanned for path tokens;
  paths         one path per line (an adapter for another harness writes this list).
Path tokens are absolute paths or paths starting with work/ or ./; shell commands are scanned for both.
The audit never prints file contents, only paths.
"""
from __future__ import annotations
import argparse, json, os, re, sys

DEFAULT_ALLOW = [
    "work/stage3/b3/writer-spec-b3.md",
    "work/stage3/b3/routine-reference-b3.json",
    "work/stage3/t1k-rater/rubric.md",
    "work/stage3/t1k-rater/doc-states-day0.md",
]
OUTPUT_DIR = "work/stage3/b3"
PATH_RE = re.compile(r"(?:/[\w.@%+-][\w./@%+-]*|(?:\./)?work/[\w./@%+-]+)")

def tokens_from_text(text: str) -> set[str]:
    return {t.rstrip(".,;:)\"'`") for t in PATH_RE.findall(text or "")}

def paths_from_claude_jsonl(trace: str) -> set[str]:
    found: set[str] = set()
    with open(trace, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = row.get("message", row)
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    inp = block.get("input") or {}
                    for key in ("file_path", "path", "pattern", "command", "notebook_path"):
                        v = inp.get(key)
                        if isinstance(v, str):
                            if key in ("file_path", "path", "notebook_path"):
                                found.add(v)
                            found |= tokens_from_text(v)
    return found

def paths_from_list(trace: str) -> set[str]:
    with open(trace, encoding="utf-8") as fh:
        return {l.strip() for l in fh if l.strip()}

def normalise(p: str, writer_dir: str) -> str:
    p = p.strip()
    if p.startswith("./"):
        p = p[2:]
    if not os.path.isabs(p):
        p = os.path.join(writer_dir, p)
    return os.path.normpath(p)

def audit(opened: set[str], writer_dir: str, allow: list[str]) -> dict:
    wd = os.path.normpath(writer_dir)
    allowed = {os.path.normpath(os.path.join(wd, a)) for a in allow}
    out_dir = os.path.normpath(os.path.join(wd, OUTPUT_DIR))
    inputs_in_out = {a for a in allowed if a.startswith(out_dir + os.sep)}
    ok, bad = [], []
    for raw in sorted(opened):
        p = normalise(raw, writer_dir)
        if p in allowed:
            ok.append(p)
        elif p == wd or (p.startswith(wd + os.sep) and not any(p.startswith(d + os.sep) or p == d for d in [])):
            # inside the writer dir: allowed only if it is the writer's own output area, not another file
            if p.startswith(out_dir + os.sep) and p not in inputs_in_out:
                ok.append(p)
            elif p == wd or p == out_dir or p == os.path.dirname(out_dir) or p == os.path.dirname(os.path.dirname(out_dir)):
                ok.append(p)  # directory listings of the allowed tree
            else:
                bad.append(p)
        else:
            bad.append(p)
    return {"writer_dir": wd, "allowed_inputs": sorted(allowed), "opened_ok": ok, "opened_outside": bad,
            "verdict": "PASS" if not bad else "FAIL"}

def main(argv=None) -> int:
    """CLI as the module docstring describes.

    Repaired 2026-10-30 (coordinator): the b3-writer-checks session found this file truncated inside
    main()'s argparse on 2026-10-29/30 (4423 bytes, sha256 243677a7...; never committed) and ran every
    function above main() unchanged through work/stage3/b3/trace_audit_run_b3.py for the Sonnet 5.5
    audit. This main() completes the CLI; nothing above it changed (byte-identical to the source the
    runner executed up to "def main(").
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", required=True)
    ap.add_argument("--writer-dir", required=True)
    ap.add_argument("--format", choices=("claude-jsonl", "paths"), default="claude-jsonl")
    ap.add_argument("--allow", action="append", default=None,
                    help="relative path allowed (repeatable); default: the four inputs")
    ap.add_argument("--out", default=None, help="write the audit result as JSON")
    ns = ap.parse_args(argv)
    opened = paths_from_claude_jsonl(ns.trace) if ns.format == "claude-jsonl" else paths_from_list(ns.trace)
    res = audit(opened, ns.writer_dir, ns.allow or DEFAULT_ALLOW)
    if ns.out:
        with open(ns.out, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1)
    print(f"trace audit: {res['verdict']}; opened inside the allowed set {len(res['opened_ok'])}; "
          f"outside {len(res['opened_outside'])}")
    for b in res["opened_outside"]:
        print("  outside:", b)
    return 0 if res["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
