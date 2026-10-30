"""Brief 15 A5.4 and A5.13: the `paths` adapter for a Cursor chat export (the GLM 5.3 writer's session).

Reads the export's `conversation.jsonl` (Cursor's stored bubbles, tool calls in `toolFormerData`) and,
optionally, `cursor-native-transcript.jsonl` (Cursor's own transcript, tool calls as `tool_use` blocks),
and writes every path a tool call touched, one absolute path per line, for
`stage3_b3_trace_audit.py --format paths`. It prints and reports paths and counts only, never file
contents, command text or edit text. Written 2026-10-30 by the blue bookkeeping session, committed with
its test before its first run on the export.

What counts as touched, per tool (conversation.jsonl name / native name):
  read_file_v2 / Read                 params.targetFile, params.effectiveUri, rawArgs.path / input.path
  edit_file_v2 / Write, StrReplace    params.relativeWorkspacePath / input.path
  ripgrep_raw_search / Grep, Glob     params.path, rawArgs.path / input.path (the search scope)
  run_terminal_command_v2 / Shell     every `cd` target; every path argument of each command (flags,
                                      numbers, a grep or sed pattern and a `python -c` code string
                                      skipped); redirect targets; every absolute path token in the
                                      command text; inside a `python -c` string or a heredoc body,
                                      absolute paths and quoted file names that exist on disk. Relative paths resolve
                                      against the running directory, which starts at params.cwd or the
                                      workspace in each call. /dev/null and the other /dev streams are
                                      sinks, not files, and are left out.
  any other tool                      every string parameter that is an absolute path (the tool is reported)
With --script-paths, the text of every .py file the writer wrote (native Write contents and StrReplace
new_string) is scanned for absolute paths that exist on disk, shebang lines skipped: a script the writer
ran can open files that no tool call names.

Usage:
    python3 -I stage3_b3_cursor_paths.py --conversation <export>/conversation.jsonl \
        --native <export>/cursor-native-transcript.jsonl --workspace /Users/aravind/b3-writer-glm53 \
        --script-paths --out <paths.txt> [--report <report.json>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import sys
from collections import Counter

ABS_TOKEN = re.compile(r"(?:^|(?<=[\s'\"=(:,]))(/[\w.@%+~-][\w./@%+~-]*)")
QUOTED_FILE = re.compile(r"""['"]([\w./~-]*\.(?:json|jsonl|md|py|tmp|txt|yaml|yml|csv))['"]""")
SINKS = {"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/stdin", "/dev/tty"}
NO_PATH_PROGRAMS = {"echo", "printf", "export", "true", "false", "test", "[", "sleep", "date", "pwd", "env"}
PATTERN_FIRST = {"grep", "egrep", "fgrep", "rg", "sed", "awk"}
OPERATORS = {"&&", "||", ";", "|", "&", ";;"}
REDIRECTS = {">", ">>", "<", ">|", "&>", "<>"}
READ_TOOLS = {"read_file_v2", "read_file", "Read"}
EDIT_TOOLS = {"edit_file_v2", "edit_file", "Write", "StrReplace", "Edit", "MultiEdit", "Delete", "delete_file"}
SEARCH_TOOLS = {"ripgrep_raw_search", "grep_search", "file_search", "list_dir", "Grep", "Glob", "LS"}
SHELL_TOOLS = {"run_terminal_command_v2", "run_terminal_cmd", "Shell", "Bash"}


def sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def resolve(p: str, cwd: str) -> str:
    p = os.path.expanduser(p.strip())
    return os.path.normpath(p if os.path.isabs(p) else os.path.join(cwd, p))


def _json(s):
    if isinstance(s, dict):
        return s
    if isinstance(s, str) and s.strip():
        try:
            v = json.loads(s)
            return v if isinstance(v, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def code_paths(code: str, cwd: str) -> set[str]:
    """Paths named in code (a `python -c` string or a script's text) that exist on disk: absolute tokens
    and quoted file names resolved against cwd; shebang lines skipped."""
    out = set()
    for line in (code or "").splitlines():
        if line.startswith("#!"):
            continue
        for t in ABS_TOKEN.findall(line):
            t = t.rstrip(".,;:)")
            if os.path.exists(t) and t not in SINKS:
                out.add(os.path.normpath(t))
        for t in QUOTED_FILE.findall(line):
            p = resolve(t, cwd)
            if os.path.exists(p):
                out.add(p)
    return out


def _words(command: str) -> list[str]:
    lex = shlex.shlex(command, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        return list(lex)
    except ValueError:  # unbalanced quotes: fall back to whitespace words
        return command.split()


def shell_paths(command: str, cwd: str) -> set[str]:
    """Every path a shell command touches (see the module docstring); `cwd` is where it starts."""
    out: set[str] = set()
    text, _, body = command.partition("<<")      # a heredoc body is data: only paths in it that exist count
    for t in ABS_TOKEN.findall(text):
        t = t.rstrip(".,;:)")
        if t not in SINKS:
            out.add(os.path.normpath(t))
    if body:
        out |= code_paths(body, cwd)
    segs: list[list[str]] = [[]]
    redirect_next = False
    for w in _words(text):
        if redirect_next:
            redirect_next = False
            if w not in SINKS:
                segs[-1].append(("__redirect__", w))
            continue
        if w in OPERATORS or w in ("(", ")"):
            segs.append([])
        elif w in REDIRECTS or (w.endswith(">") and w.rstrip(">&").isdigit()):
            redirect_next = True
        else:
            segs[-1].append(w)
    for seg in segs:
        redirects = [x[1] for x in seg if isinstance(x, tuple)]
        words = [x for x in seg if not isinstance(x, tuple)]
        while words and re.fullmatch(r"\w+=.*", words[0]):
            words = words[1:]                                  # leading VAR=value assignments
        for r in redirects:
            out.add(resolve(r, cwd))
        if not words:
            continue
        prog, args = os.path.basename(words[0]), words[1:]
        if prog == "cd":
            cwd = resolve(args[0], cwd) if args else os.path.expanduser("~")
            out.add(cwd)
            continue
        if prog in NO_PATH_PROGRAMS:
            continue
        if prog.startswith("python"):
            if "-c" in args:
                i = args.index("-c")
                if i + 1 < len(args):
                    out |= code_paths(args[i + 1], cwd)
                continue
            if "-m" in args:
                continue
            args = [a for a in args if not a.startswith("-")]
            if args:
                out.add(resolve(args[0], cwd))
                args = [a for a in args[1:] if "/" in a or re.search(r"\.\w{1,6}$", a)]
            for a in args:
                out.add(resolve(a, cwd))
            continue
        plain = [a for a in args if not a.startswith("-") and not re.fullmatch(r"\d+", a)]
        if prog in PATTERN_FIRST:
            plain = plain[1:] if "-e" not in args else plain
        elif prog == "find":
            plain = []
            for a in args:
                if a.startswith(("-", "(", "!")):
                    break
                plain.append(a)
        elif not re.fullmatch(r"(cat|ls|mv|cp|mkdir|rm|rmdir|touch|shasum|sha256sum|wc|head|tail|diff|cmp|stat|file|"
                              r"chmod|jq|less|more|tee|ln|du|tar|zip|unzip|open|realpath|readlink|source|\.|bash|sh|zsh)",
                              prog):
            plain = [a for a in plain if "/" in a or re.search(r"\.\w{1,6}$", a)]
        for a in plain:
            if a not in SINKS:
                out.add(resolve(a, cwd))
    return {p for p in out if p not in SINKS}


def from_conversation(path: str, workspace: str) -> tuple[list[dict], Counter, list[str]]:
    """(uses, tool counts, unknown tool names) from Cursor's stored bubbles."""
    uses: list[dict] = []
    tools: Counter = Counter()
    unknown: list[str] = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            if not line.strip():
                continue
            t = json.loads(line).get("toolFormerData")
            if not t:
                continue
            name = t.get("name", "?")
            tools[name] += 1
            params, raw = _json(t.get("params")), _json(t.get("rawArgs"))

            def add(p, field):
                if isinstance(p, str) and p.strip():
                    uses.append({"source": "conversation", "entry": i, "tool": name, "field": field,
                                 "path": resolve(p, workspace)})
            if name in READ_TOOLS:
                add(params.get("targetFile"), "params.targetFile")
                add(params.get("effectiveUri"), "params.effectiveUri")
                add(raw.get("path"), "rawArgs.path")
            elif name in EDIT_TOOLS:
                add(params.get("relativeWorkspacePath"), "params.relativeWorkspacePath")
                add(raw.get("path"), "rawArgs.path")
            elif name in SEARCH_TOOLS:
                add(params.get("path"), "params.path")
                add(raw.get("path"), "rawArgs.path")
                for d in params.get("targetDirectories") or []:
                    add(d, "params.targetDirectories")
            elif name in SHELL_TOOLS:
                cwd = resolve(params["cwd"], workspace) if params.get("cwd") else workspace
                for p in sorted(shell_paths(params.get("command", ""), cwd)):
                    uses.append({"source": "conversation", "entry": i, "tool": name, "field": "params.command",
                                 "path": p})
            else:
                unknown.append(name)
                for k, v in list(params.items()) + list(raw.items()):
                    if isinstance(v, str) and v.startswith("/"):
                        add(v, f"params.{k}")
    return uses, tools, unknown


def from_native(path: str, workspace: str, script_paths: bool) -> tuple[list[dict], Counter, list[dict]]:
    """(uses, tool counts, script-text uses) from Cursor's native transcript."""
    uses: list[dict] = []
    scripts: list[dict] = []
    tools: Counter = Counter()
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = row.get("message") if isinstance(row, dict) else None
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                    continue
                name, inp = b.get("name", "?"), b.get("input") or {}
                tools[name] += 1
                if name in SHELL_TOOLS:
                    cwd = resolve(inp["cwd"], workspace) if isinstance(inp.get("cwd"), str) and inp["cwd"] else workspace
                    for p in sorted(shell_paths(inp.get("command", ""), cwd)):
                        uses.append({"source": "native", "entry": i, "tool": name, "field": "input.command", "path": p})
                    continue
                for k in ("path", "file_path", "target_file", "notebook_path"):
                    if isinstance(inp.get(k), str) and inp[k].strip():
                        uses.append({"source": "native", "entry": i, "tool": name, "field": f"input.{k}",
                                     "path": resolve(inp[k], workspace)})
                target = inp.get("path") or inp.get("file_path") or ""
                if script_paths and name in EDIT_TOOLS and str(target).endswith(".py"):
                    code = inp.get("contents") or inp.get("content") or inp.get("new_string") or ""
                    for p in sorted(code_paths(code, os.path.dirname(resolve(target, workspace)))):
                        scripts.append({"source": "native", "entry": i, "tool": name, "field": "script text",
                                        "script": resolve(target, workspace), "path": p})
    return uses, tools, scripts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--conversation", required=True)
    ap.add_argument("--native", default=None)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--script-paths", action="store_true")
    ap.add_argument("--out", required=True)
    ap.add_argument("--report", default=None)
    a = ap.parse_args(argv)
    ws = os.path.normpath(os.path.expanduser(a.workspace))

    conv_uses, conv_tools, unknown = from_conversation(a.conversation, ws)
    nat_uses, nat_tools, scripts = (from_native(a.native, ws, a.script_paths) if a.native else ([], Counter(), []))
    every = conv_uses + nat_uses + scripts
    paths = sorted({u["path"] for u in every})
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write("".join(p + "\n" for p in paths))

    def non_shell(us):
        return {u["path"] for u in us if u["field"] not in ("params.command", "input.command")}
    conv_ns, nat_ns = non_shell(conv_uses), non_shell(nat_uses)
    rep = {"version": "b3-cursor-paths/1", "adapter_sha256": sha(__file__), "workspace": ws,
           "conversation": {"path": a.conversation, "sha256": sha(a.conversation)},
           "native": {"path": a.native, "sha256": sha(a.native)} if a.native else None,
           "tool_calls_conversation": dict(conv_tools), "tool_calls_native": dict(nat_tools),
           "unknown_tools": sorted(set(unknown)), "n_paths": len(paths),
           "cross_check": None if not a.native else {
               "tool_call_totals_equal": sum(conv_tools.values()) == sum(nat_tools.values()),
               "non_shell_paths_equal": conv_ns == nat_ns,
               "only_in_conversation": sorted(conv_ns - nat_ns), "only_in_native": sorted(nat_ns - conv_ns)},
           "script_paths": sorted({(s["script"], s["path"]) for s in scripts}),
           "paths": [{"path": p, "uses": sorted({(u["source"], u["entry"], u["tool"], u["field"]) for u in every
                                                 if u["path"] == p})} for p in paths]}
    if a.report:
        with open(a.report, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=1, default=list)
            fh.write("\n")
    print(json.dumps({k: rep[k] for k in ("tool_calls_conversation", "tool_calls_native", "unknown_tools",
                                          "n_paths", "cross_check")}, default=list))
    return 0


if __name__ == "__main__":
    sys.exit(main())
