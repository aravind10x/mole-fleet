"""Blue runner for brief 15 A5.4's trace audit (B3 writers), written 2026-10-29 by the bookkeeping session.

`work/checks/stage3_b3_trace_audit.py` exists only in the main checkout, was never committed, and is
truncated (4423 bytes, sha256 243677a7...; the file stops inside main()'s argparse). Every function above
main() is complete. This runner executes that source up to `def main(` unchanged and supplies the CLI its
docstring describes (--trace, --writer-dir, --format, --allow; exit 0 PASS, 2 FAIL), writing the audit's
own result to --out-raw. It then adds, per flagged path, provenance (tool-call ordinals, tool and field,
the shell programs of the command from a fixed list) and a mechanical class, and writes --out-json. It
never reproduces candidate text: a token that is not a file and occurs in the writer's candidate file, or
occurs only inside a heredoc body, is counted and its path left null.

Usage:
    python3 -I trace_audit_run_b3.py --audit-script work/checks/stage3_b3_trace_audit.py \
        --trace <jsonl> --writer-dir <dir> --format claude-jsonl --candidates <payload json> \
        --out-raw <json outside the repo> --out-json <json>
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys

OWN_OUTPUTS = ("payloads-b3-candidates", "checklist-b3", "writer-record", "checks-b3")
INPUTS = ("work/stage3/b3/writer-spec-b3.md", "work/stage3/b3/routine-reference-b3.json",
          "work/stage3/t1k-rater/rubric.md", "work/stage3/t1k-rater/doc-states-day0.md")
SHELL_SEP = re.compile(r"&&|\|\||[;|\n]")
KNOWN_PROGRAMS = {"ls", "cat", "head", "tail", "sed", "grep", "find", "git", "python", "cd", "echo", "wc",
                  "shasum", "sha256sum", "cut", "sort", "uniq", "mkdir", "cp", "mv", "rm", "diff", "cmp", "jq",
                  "awk", "tr", "xargs", "test", "stat", "du", "file", "od", "for", "do", "done", "while", "if",
                  "then", "fi", "else", "true", "false", "printf", "basename", "dirname", "touch", "tee", "env",
                  "export", "pwd", "date", "realpath", "readlink", "(cd"}


def sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_audit(script: str) -> dict:
    src = open(script, encoding="utf-8").read()
    cut = src.index("\ndef main(")
    ns: dict = {"__name__": "stage3_b3_trace_audit_functions"}
    exec(compile(src[:cut], script, "exec"), ns)
    return ns


def strip_heredocs(cmd: str) -> str:
    """The command with every heredoc body removed (the << line and the terminator kept)."""
    out, lines, i = [], (cmd or "").split("\n"), 0
    while i < len(lines):
        m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", lines[i])
        out.append(lines[i])
        i += 1
        if m:
            while i < len(lines) and lines[i].strip() != m.group(1):
                i += 1
    return "\n".join(out)


def programs(cmd: str) -> list[str]:
    out = []
    for seg in SHELL_SEP.split(cmd or ""):
        words = seg.strip().split()
        while words and "=" in words[0] and not words[0].startswith(("/", ".")):
            words = words[1:]  # leading VAR=value assignments
        if words:
            w = os.path.basename(words[0])
            w = "python" if w.startswith("python") else w
            out.append(w if w in KNOWN_PROGRAMS else "<other>")
    return out


def tool_uses(trace: str):
    i = 0
    with open(trace, encoding="utf-8", errors="replace") as fh:
        for line in fh:
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
                    i += 1
                    yield i, block.get("name", "?"), block.get("input") or {}


def provenance(trace: str, ns: dict, writer_dir: str) -> tuple[dict, dict]:
    """Normalised path -> list of uses; plus tool-use counts by name."""
    prov: dict = {}
    tools: dict = {}
    for i, name, inp in tool_uses(trace):
        tools[name] = tools.get(name, 0) + 1
        for key in ("file_path", "path", "pattern", "command", "notebook_path"):
            v = inp.get(key)
            if not isinstance(v, str):
                continue
            toks = set(ns["tokens_from_text"](v))
            if key in ("file_path", "path", "notebook_path"):
                toks.add(v)
            stripped = strip_heredocs(v) if key == "command" else v
            outside_bodies = set(ns["tokens_from_text"](stripped)) if key == "command" else toks
            progs = sorted(set(programs(stripped))) if key == "command" else []
            for t in toks:
                prefix = None  # a shell variable or relative directory the token is a suffix of
                if key == "command" and t.startswith("/"):
                    m = re.search(r"([\w.${}-]+)" + re.escape(t), stripped)
                    prefix = m.group(1) if m else None
                p = ns["normalise"](t, writer_dir)
                prov.setdefault(p, []).append({"call": i, "tool": name, "field": key, "programs": progs,
                                               "heredoc_body_only": t not in outside_bodies, "prefix": prefix})
    return prov, tools


def candidate_strings(d: dict) -> list[str]:
    """Every string in the payload records except the structural fields (statements, justifications,
    tokens, composed effects); the file header and the class-document paths are left out."""
    skip = {"id", "arm", "document", "kind", "op", "anchor"}
    out: list[str] = []

    def walk(o, k=None):
        if isinstance(o, dict):
            for kk, v in o.items():
                if kk not in skip:
                    walk(v, kk)
        elif isinstance(o, list):
            for v in o:
                walk(v, k)
        elif isinstance(o, str):
            out.append(o)
    for p in d.get("payloads", []):
        walk(p)
    return out


def classify(p: str, writer_dir: str, pv: list, cand_text: str, raw_tokens: set, scratch: tuple) -> str:
    wd = os.path.normpath(writer_dir)
    rel = os.path.relpath(p, wd) if p.startswith(wd + os.sep) or p == wd else None
    if rel is not None:
        if rel in INPUTS:
            return "input"
        if rel.startswith("work/stage3/b3/"):
            return "own output" if os.path.basename(rel).startswith(OWN_OUTPUTS) else "other file under work/stage3/b3/"
        if rel in (".", "work", "work/stage3", "work/stage3/b3"):
            return "directory of the allowed tree"
        if rel == "work/checks/stage3_t1v2_checks.py" or rel.startswith("work/mole-fork/.venv/"):
            return "checks run: script or interpreter"
        if rel == "work/mole-fork":
            return "fork root (checks --fork argument; git -C)"
        if rel.startswith("work/mole-fork/results/stage3/b3"):
            return "fork results/stage3/b3"
        return "other repository path"
    if p.startswith(scratch):
        return "session scratchpad"
    if pv and all(x["prefix"] for x in pv):
        return "path suffix (after a shell variable or relative directory)"
    if os.path.exists(p):
        return "existing path outside the repository"
    if any(t in cand_text for t in raw_tokens):
        return "candidate-text token (not a file; not reproduced)"
    if pv and all(x["heredoc_body_only"] for x in pv):
        return "heredoc-body fragment (not a file; not reproduced)"
    return "other non-file token"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audit-script", required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--writer-dir", required=True)
    ap.add_argument("--format", choices=("claude-jsonl", "paths"), default="claude-jsonl")
    ap.add_argument("--allow", action="append", default=[])
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--scratch-prefix", action="append", default=["/private/tmp/claude-501/", "/tmp/claude-501/"])
    ap.add_argument("--out-raw", required=True)
    ap.add_argument("--out-json", required=True)
    a = ap.parse_args(argv)

    ns = load_audit(a.audit_script)
    reader = ns["paths_from_claude_jsonl"] if a.format == "claude-jsonl" else ns["paths_from_list"]
    opened = reader(a.trace)
    res = ns["audit"](opened, a.writer_dir, ns["DEFAULT_ALLOW"] + a.allow)
    with open(a.out_raw, "w") as fh:
        json.dump(res, fh, indent=2)

    cand_text = "\n".join(candidate_strings(json.load(open(a.candidates, encoding="utf-8"))))
    raw_by_norm: dict = {}
    for t in opened:
        raw_by_norm.setdefault(ns["normalise"](t, a.writer_dir), set()).add(t)
    prov, tools = provenance(a.trace, ns, a.writer_dir)

    rows, hidden, seen = [], 0, set()
    for verdict, lst in (("outside", res["opened_outside"]), ("ok", res["opened_ok"])):
        for p in lst:
            if (verdict, p) in seen:
                continue
            seen.add((verdict, p))
            pv = prov.get(p, [])
            cls = classify(p, a.writer_dir, pv, cand_text, raw_by_norm.get(p, {p}), tuple(a.scratch_prefix))
            row = {"audit": verdict, "class": cls, "path": p,
                   "prefixes": sorted({x["prefix"] for x in pv if x["prefix"]}),
                   "calls": sorted({x["call"] for x in pv}),
                   "tools": sorted({f"{x['tool']}.{x['field']}" for x in pv}),
                   "programs": sorted({q for x in pv for q in x["programs"] if q != "<other>"})}
            if "not reproduced" in cls:
                hidden += 1
                row["path"] = None
            rows.append(row)

    out = {"version": "b3-trace-audit/1", "audit_script": a.audit_script, "audit_script_sha256": sha(a.audit_script),
           "audit_script_note": "truncated in the main checkout; the functions above main() ran unchanged via this runner",
           "runner_sha256": sha(__file__), "trace": a.trace, "trace_sha256": sha(a.trace),
           "trace_bytes": os.path.getsize(a.trace), "writer_dir": res["writer_dir"],
           "candidates": a.candidates, "candidates_sha256": sha(a.candidates),
           "raw_audit_sha256": sha(a.out_raw), "verdict_script": res["verdict"],
           "n_tokens": len(opened), "n_ok": len(res["opened_ok"]), "n_outside": len(res["opened_outside"]),
           "n_rows_deduplicated": len(rows), "n_tokens_not_reproduced": hidden, "tool_uses": tools, "paths": rows}
    with open(a.out_json, "w") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(json.dumps({k: out[k] for k in ("verdict_script", "n_tokens", "n_ok", "n_outside", "n_rows_deduplicated",
                                          "n_tokens_not_reproduced", "tool_uses")}))
    return 0 if res["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
