#!/usr/bin/env python3
"""Brief 30 Part 3: the launch-side record of a writer round. Blue side; standard library only; no model call.

Two things the Part 1 harness leaves to the launcher:

1. `writer_settings` : the Claude Code settings that make the writer session's Read tool refuse the project
   tree, the harness's and the CLIs' state trees and every other writer's folder. The Part 1 harness writes a
   flat `{"deny": [...]}` fragment with single-slash patterns; that is not Claude Code's settings schema
   (`permissions.deny`) and a single-slash path is read relative to the session's folder. The probe of
   2026-11-07 showed `Read(//Users/...)` refuses an absolute path and a folder file still reads. The harness
   (6eca0f14) is not edited: its fragment stays beside the manifest as written and this file is what the
   launch uses. The trace audit, with its PASS record, remains the control.
2. `start_state` : launch notes section 3's start-state record: existence and sha256 (never contents) of the
   instruction files in the writer's folder and each parent up to the root, of the user-level files, of the
   per-folder memory index the harness maps the folder to, and of the files placed in the folder, with what
   the harness reported loading.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_part3_launch.py start-state \
        --folder F --out O.json [--harness-json '{"tool": ...}']
    ... settings --folder F --other-tree T [--other-tree T2] --out S.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

VERSION = "elicitation-part3-launch/v0"
PROJECT_TREE = "/Users/aravind/KruxAI"
INSTRUCTION_NAMES = ("CLAUDE.md", "AGENTS.md", ".claude", ".codex", ".cursor", ".cursorrules")
USER_LEVEL = ("CLAUDE.md", "AGENTS.md", ".claude/CLAUDE.md", ".codex/AGENTS.md", ".cursor/rules", ".cursorrules")


def _entry(p: Path) -> dict:
    if p.is_file():
        return {"present": True, "kind": "file", "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    if p.is_dir():
        return {"present": True, "kind": "dir"}
    return {"present": False}


def session_slug(folder: Path) -> str:
    """The folder name Claude Code's per-folder state is mapped to: every character outside A-Z, a-z, 0-9 becomes '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(Path(folder).resolve()))


def writer_settings(folder: Path, other_trees: Sequence[Path] = (), home: Path | None = None) -> dict:
    home = Path(home) if home is not None else Path.home()
    own = str(Path(folder)).rstrip("/")
    trees = [PROJECT_TREE, str(home / ".claude"), str(home / ".codex"), str(home / ".cursor"), str(home / ".config"),
             "/private/var/folders", "/tmp"]
    trees += [str(Path(t)).rstrip("/") for t in other_trees]
    trees = [t for t in dict.fromkeys(trees) if t != own and not own.startswith(t + "/")] or []
    # a tree that contains the writer's own folder cannot be denied without blinding the writer: refuse it loudly
    for t in [PROJECT_TREE, str(home / ".claude"), str(home / ".codex")]:
        if own == t or own.startswith(t + "/"):
            raise ValueError(f"the writer's folder {own} sits inside the denied tree {t}")
    deny = [f"Read(/{t}/**)" for t in trees]
    deny += [f"Read(/{home}/CLAUDE.md)", f"Read(/{home}/AGENTS.md)"]
    return {"permissions": {"deny": deny}}


def rater_settings(folder: Path, other_trees: Sequence[Path] = (), home: Path | None = None) -> dict:
    """A rater session reads and writes in its own folder only: the writer settings' Read denies, and a Write deny for
    every tree they name (the instruction files excepted: Write to them is moot beside the Read deny)."""
    base = writer_settings(folder, other_trees, home)["permissions"]["deny"]
    trees = [d for d in base if d.endswith("/**)")]
    return {"permissions": {"deny": base + [d.replace("Read(", "Write(", 1) for d in trees]}}


def start_state(folder: Path, home: Path | None = None, harness: Mapping[str, Any] | None = None) -> dict:
    home = Path(home) if home is not None else Path.home()
    folder = Path(folder).resolve()
    ancestors = []
    cur = folder
    while True:
        ancestors.append({"dir": str(cur), "entries": {n: _entry(cur / n) for n in INSTRUCTION_NAMES}})
        if cur == cur.parent:
            break
        cur = cur.parent
    mem = home / ".claude" / "projects" / session_slug(folder) / "memory" / "MEMORY.md"
    files = {}
    if folder.is_dir():
        for p in sorted(folder.rglob("*")):
            if p.is_file():
                files[p.relative_to(folder).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return {"version": VERSION, "folder": str(folder),
            "harness": dict(harness or {}),
            "ancestors": ancestors,
            "user_level": {n: _entry(home / n) for n in USER_LEVEL},
            "memory_index": {"path": str(mem), **_entry(mem)},
            "folder_files": files,
            "note": "existence and sha256 only; no file content is read into this record"}


def render(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("start-state")
    a.add_argument("--folder", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--harness-json", default="{}")
    b = sub.add_parser("settings")
    b.add_argument("--folder", required=True)
    b.add_argument("--other-tree", action="append", default=[])
    b.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    if ns.cmd == "start-state":
        rec = start_state(Path(ns.folder), harness=json.loads(ns.harness_json))
    else:
        rec = writer_settings(Path(ns.folder), [Path(t) for t in ns.other_tree])
    Path(ns.out).write_text(render(rec), encoding="utf-8")
    print(f"wrote {ns.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
