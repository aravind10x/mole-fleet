#!/usr/bin/env python3
"""Brief 30, Part 1 item 4 (decision 7, made enforceable by the cold read's item 3): the clean
harness for the elicitation study's writer sessions. Blue side; run by a non-Anthropic executor
under L25; harness: GLM 5.3 on Cursor. No model call; prints counts, hashes and ids only.

`assemble` builds one writer's round folder outside /Users/aravind/KruxAI from the four hash-pinned
files (the writer packet, the launch notes, the taxonomy, the arm's document state), following the
folder table of the launch notes section 1 and the packet's own "never sent" header: the writer sees
`packet.md` (the sent body, cb528f5d…), `round.md`, the arm's document file(s) and, from round 2,
its own `previous/`. The full packet file, the launch notes and the taxonomy file are the harness's
verified INPUTS and are never placed in the folder (their blue-side sections say so themselves). A
manifest beside the folder records every hash; `verify` re-checks a folder against its manifest; a
Claude Code permission deny-list is written beside it as defence in depth.

Enforcement (the cold read's item 3, adopted by brief 30's dated note): writers run as sessions under
the deny-list, and `audit` runs the pinned trace-audit script (2a409344) on the writer's transcript
against an allow-list built from the manifest (the round folder's files, the session's own scratchpad
and the harness's state directories). The converter refuses any real writer file without an audit
record whose verdict is PASS for exactly that manifest (stage3_elicitation_convert's gate); the
record and the trace, not the directory, are the control (the launch notes section 3).

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_harness.py assemble \
        --packet work/stage3/elicitation/writer-packet-v0.md --launch-notes .../writer-launch-notes-v0.md \
        --taxonomy .../taxonomy-v0.md --doc-state work/stage3/t1k-rater/doc-states-day0.md \
        [--doc-state-cross .../doc-states-day0-v7.md] --arm one-document --round 1 --items-count 24 \
        --dest <a new folder outside the project> --writer opus55 [--previous <dir>]
    ... verify --dest D --manifest M
    ... audit --trace <transcript> --manifest M [--format claude-jsonl|codex-jsonl|paths] --out A
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_trace_audit as ta  # noqa: E402  (the pinned script, used, not edited)
import stage3_elicitation_convert as cv  # noqa: E402
import stage3_elicitation_packet_check as pc  # noqa: E402
import stage3_elicitation_part3_launch as pl  # noqa: E402

VERSION = "elicitation-harness/v0"
PROJECT = HERE.parent.parent
FORBIDDEN_ROOT = PROJECT.parent.resolve()          # /Users/aravind/KruxAI
SHA_PACKET = "486ac7f96c77401438100707bc9a069b2c87bc8e1d0df52c13068ce41e29cc79"
SHA_NOTES = "147dae26126f870467e89d44382c59e0668f57e715c76c66c095b10d5f567fba"
SHA_TAXONOMY = "ec195e238e64c9db65fff7f35e279b32e6733a13b22321ba34851d6a71d2a687"
SHA_TRACE_AUDIT = "2a409344"
ARM_STATES = {"one-document": cv.SHA_STATE_ONE, "cross-document": cv.SHA_STATE_CROSS}
SHELL_BINARIES = frozenset({"/bin/zsh", "/bin/bash", "/bin/sh", "/usr/bin/env"})   # the CLIs' own command wrapper (codex: `/bin/zsh -lc ...`)
STATE_DIRS = ("/Users/aravind/.claude/projects/", "/Users/aravind/.codex/", "/private/var/folders/",
               "/tmp/", "/dev/null")


class UsageError(SystemExit):
    """A caller error (a wrong hash, an unclean destination, a failed gate)."""


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _check(path: Path, sha: str, what: str) -> None:
    got = _sha(path)
    if got != sha:
        raise UsageError(f"refusing: {what} is {got[:8]}, not the pinned {sha[:8]}")


def launch_notes_conventions(notes_path: Path) -> tuple[str, tuple[str, str, str]]:
    """(the preface, the round.md line prefixes), parsed from the launch notes' own section 2 (L26:
    the convention is read from the record that owns it, and the assembled round.md must match it)."""
    text = Path(notes_path).read_text(encoding="utf-8")
    lines = text.split("\n")
    block = None
    for i, ln in enumerate(lines):
        if ln.startswith("## 2."):
            block = i
            break
    if block is None:
        raise UsageError("the launch notes hold no section 2")
    template: list[str] = []
    preface: list[str] = []
    in_fence = in_quote = False
    for ln in lines[block + 1:]:
        if ln.startswith("## "):
            break
        if ln.strip() == "```":
            in_fence = not in_fence
            continue
        if in_fence and ln.strip():
            template.append(ln.strip())
        if ln.startswith("> "):
            in_quote = True
            preface.append(ln[2:].strip())
        elif in_quote and ln.strip() == "":
            in_quote = False
    if len(template) != 3 or not preface:
        raise UsageError("the launch notes' round.md template or preface did not parse")
    prefixes = tuple(re.match(r"^([A-Za-z ]+?: )", t).group(1) for t in template)
    return " ".join(preface), prefixes


def assemble(*, packet: Path, launch_notes: Path, taxonomy: Path, doc_state: Path,
             doc_state_cross: Path | None = None, arm: str, round_no: int, items_count: int, dest: Path,
             writer: str, previous: Path | None = None, prepare_config: Path | None = None, cursor_deny: bool = False) -> dict:
    """Build the writer's round folder; returns the manifest (also written beside it)."""
    if arm not in ("one-document", "cross-document", "both"):
        raise UsageError(f"unknown arm {arm!r}")
    _check(packet, SHA_PACKET, "the writer packet")
    _check(launch_notes, SHA_NOTES, "the launch notes")
    _check(taxonomy, SHA_TAXONOMY, "the taxonomy")
    body = pc.between(Path(packet).read_text(encoding="utf-8"), pc.PACKET_B, pc.PACKET_E)
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != cv.PACKET_BODY_SHA256:
        raise UsageError("refusing: the packet's sent body is not cb528f5d")
    embedded = pc.between(body, pc.TAX_B, pc.TAX_E)
    marked = pc.between(Path(taxonomy).read_text(encoding="utf-8"), pc.TAX_B, pc.TAX_E)
    if embedded != marked:
        raise UsageError("refusing: the packet's embedded taxonomy differs from the taxonomy file")
    states = {s: (doc_state_cross if s == "cross-document" else doc_state) for s in
              (("one-document", "cross-document") if arm == "both" else (arm,))}
    for s, p in states.items():
        _check(p, ARM_STATES[s], f"the {s} document state")
    preface, prefixes = launch_notes_conventions(launch_notes)
    if prefixes != ("Round: ", "Arm: ", "Items to write per arm: "):
        raise UsageError("refusing: the launch notes' round.md template is not the one this harness writes")
    dest = Path(dest).resolve()
    if FORBIDDEN_ROOT in dest.parents or dest == PROJECT:
        raise UsageError("refusing: the round folder must sit outside /Users/aravind/KruxAI")
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        raise UsageError(f"refusing: {dest} already holds a file")
    files: dict[str, str] = {}
    (dest / "packet.md").write_text(body, encoding="utf-8")
    files["packet.md"] = _sha(dest / "packet.md")
    round_md = f"{prefixes[0]}{round_no}\n{prefixes[1]}{arm}\n{prefixes[2]}{items_count}\n"
    (dest / "round.md").write_text(round_md, encoding="utf-8")
    files["round.md"] = _sha(dest / "round.md")
    for s, p in states.items():
        name = f"documents-{s}.md"
        (dest / name).write_bytes(Path(p).read_bytes())
        files[name] = _sha(dest / name)
    if cursor_deny:
        # a Cursor CLI writer reads its deny-list from <workspace>/.cursor/cli.json only; the file is in the manifest, so the
        # folder stays exactly what the manifest says and the audit allows reading it
        others = [p for p in dest.parent.parent.iterdir() if p.is_dir() and p != dest.parent] if dest.parent.parent.is_dir() else []
        (dest / ".cursor").mkdir()
        (dest / ".cursor" / "cli.json").write_text(json.dumps(pl.cursor_cli_config(dest, others), indent=1), encoding="utf-8")
        files[".cursor/cli.json"] = _sha(dest / ".cursor" / "cli.json")
    prev_rec: dict[str, Any] = {}
    if previous is not None:
        pv = Path(previous)
        (dest / "previous").mkdir()
        for f in sorted(pv.iterdir()):
            if f.name not in ("items.json", "results.json") or not f.is_file():
                raise UsageError("refusing: previous/ holds only items.json and results.json")
            (dest / "previous" / f.name).write_bytes(f.read_bytes())
            files[f"previous/{f.name}"] = _sha(dest / "previous" / f.name)
            prev_rec[f.name] = files[f"previous/{f.name}"]
    # the Claude Code settings for this writer's session (brief 30 note 9 item 5): `permissions.deny` with `//`-absolute
    # Read patterns, the other writers' trees denied, the writer's own folder not; the flat fragment this replaces was not
    # Claude Code's schema and refused nothing
    others = [p for p in dest.parent.parent.iterdir() if p.is_dir() and p != dest.parent] if dest.parent.parent.is_dir() else []
    perm = pl.writer_settings(dest, others)
    manifest = {"manifest_version": VERSION, "round_dir": str(dest), "writer": writer,
                "round": round_no, "arm": arm, "items_count": items_count,
                "packet_body_sha256": files["packet.md"],
                "preface_sha256": hashlib.sha256(preface.encode("utf-8")).hexdigest(),
                "sources": {"packet": {"path": str(packet), "sha256": SHA_PACKET},
                            "launch_notes": {"path": str(launch_notes), "sha256": SHA_NOTES},
                            "taxonomy": {"path": str(taxonomy), "sha256": SHA_TAXONOMY},
                            "doc_state": {"path": str(states.get("one-document", states.get("cross-document"))),
                                          "sha256": ARM_STATES.get("one-document" if "one-document" in states
                                                                    else "cross-document")},
                            "doc_state_cross": ({"path": str(doc_state_cross), "sha256": cv.SHA_STATE_CROSS}
                                                if doc_state_cross else None)},
                "trace_audit": {"script": "work/checks/stage3_b3_trace_audit.py", "sha256": SHA_TRACE_AUDIT,
                                "gate": "the converter refuses a real writer file without a PASS audit "
                                        "record for exactly this manifest"},
                "files": files, "previous": prev_rec,
                "deny_list": {"settings": str(dest.parent / f"permissions-{dest.name}.json"),
                              "schema": "claude-code permissions.deny",
                              "deny": perm["permissions"]["deny"],
                              "note": "Claude Code only (codex runs -s read-only, which does not stop reads); the trace "
                                      "audit with its PASS record is the control"}}
    (dest.parent / f"permissions-{dest.name}.json").write_text(json.dumps(perm, indent=1), encoding="utf-8")
    if prepare_config is not None:
        cfg = Path(prepare_config)
        (cfg / "claude-config").mkdir(parents=True, exist_ok=True)          # empty: CLAUDE_CONFIG_DIR
        codex = cfg / "codex-home"
        codex.mkdir(parents=True, exist_ok=True)
        auth = Path.home() / ".codex" / "auth.json"
        if auth.exists():
            (codex / "auth.json").write_bytes(auth.read_bytes())            # the login only
            manifest["clean_config"] = {"claude_config_dir": str(cfg / "claude-config"),
                                        "codex_home": str(codex), "login_copied": True}
        else:
            manifest["clean_config"] = {"claude_config_dir": str(cfg / "claude-config"),
                                        "codex_home": str(codex), "login_copied": False}
    man_path = dest.parent / f"manifest-{dest.name}.json"
    man_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    return manifest


def verify(dest: Path, manifest_path: Path) -> list[str]:
    """Every file of the round folder against the manifest; [] when the folder is exactly as assembled."""
    man = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    dest = Path(man["round_dir"])
    errs = []
    seen = set()
    for p in sorted(dest.rglob("*")):
        rel = p.relative_to(dest).as_posix()
        if p.is_dir():
            continue
        seen.add(rel)
        if rel not in man["files"]:
            errs.append(f"{rel}: present now, not in the manifest")
        elif _sha(p) != man["files"][rel]:
            errs.append(f"{rel}: sha256 differs from the manifest")
    for rel in man["files"]:
        if rel not in seen:
            errs.append(f"{rel}: in the manifest, absent now")
    return errs


def session_slug(dest: Path) -> str:
    """The folder name the Claude Code CLI maps a working folder to ('/' and '.' become '-')."""
    return re.sub(r"[/.]", "-", str(Path(dest).resolve()).strip("/"))


def _paths_from_codex_jsonl(trace: Path) -> set[str]:
    """The codex --json adapter: path tokens from every string value of every event (schema-agnostic,
    over-collecting on purpose; the pinned script's regex does the matching)."""
    out: set[str] = set()

    def walk(o: Any) -> None:
        if isinstance(o, str):
            out.update(ta.tokens_from_text(o))
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for line in Path(trace).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            walk(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def audit(trace: Path, manifest_path: Path, format: str = "claude-jsonl", out: Path | None = None) -> dict:
    """The trace audit on a writer transcript against the manifest's allow-list: the round folder's
    files, the session's own scratchpad under the mapped project dir, and the harness's state dirs.
    PASS only when nothing outside them was opened; the project tree and every other writer's folder
    are never-open. The pinned script is verified by hash first."""
    script = HERE / "stage3_b3_trace_audit.py"
    got = _sha(script)
    if got[:8] != SHA_TRACE_AUDIT:
        raise UsageError(f"refusing: the trace-audit script is {got[:8]}, not the pinned {SHA_TRACE_AUDIT}")
    man = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    dest = Path(man["round_dir"]).resolve()
    if format == "claude-jsonl":
        opened = ta.paths_from_claude_jsonl(str(trace))
    elif format == "codex-jsonl":
        opened = _paths_from_codex_jsonl(Path(trace))
    else:
        opened = ta.paths_from_list(str(trace))
    norm: set[str] = set()
    for t in opened:
        t = t.strip()
        if t.startswith("./"):
            t = t[2:]
        norm.add(os.path.normpath(t if os.path.isabs(t) else os.path.join(str(dest), t)))
    allow = {str((dest / rel).resolve()) for rel in man["files"]}
    allow |= {str(dest), str(dest / "previous")}
    # never-open first: the project tree (every B3 file, the fork, the red tree) and every other
    # writer's folder (the round folders' common parent, minus this round's own folder)
    writers_root = str(dest.parent.parent.resolve())
    never = sorted(p for p in norm if p.startswith(FORBIDDEN_ROOT.as_posix())
                   or (p.startswith(writers_root + os.sep) and p != str(dest) and not p.startswith(str(dest) + os.sep)))
    rest = [p for p in norm if p not in set(never) and p not in allow]
    # the session's own scratchpad under the mapped project dir, and the harness's state dirs
    slug = session_slug(dest)
    scratch = "/Users/aravind/.claude/projects/" + slug
    rest = [p for p in rest if not p.startswith(scratch)]
    for base in ("/Users/aravind/.codex/", "/private/var/folders/", "/tmp/"):
        rest = [p for p in rest if not p.startswith(base)]
    rest = [p for p in rest if p != "/dev/null" and p not in SHELL_BINARIES]
    outside_existing = sorted(p for p in rest if os.path.exists(p))
    tokens = sorted(p for p in rest if not os.path.exists(p))
    verdict = "PASS" if not never and not outside_existing else "FAIL"
    rec = {"version": f"{VERSION}/audit", "verdict": verdict, "format": format,
           "trace_sha256": _sha(Path(trace)), "manifest_sha256": _sha(Path(manifest_path)),
           "writer": man["writer"], "round": man["round"], "round_dir": str(dest),
           "pinned_script_sha256": got[:8], "opened": len(norm), "allowed_files": len(man["files"]),
           "outside_existing": len(outside_existing), "non_existent_tokens": len(tokens),
           "never_open": len(never)}
    if out is not None:
        Path(out).write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 30 part 1: the clean writer harness")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("assemble")
    a.add_argument("--packet", required=True)
    a.add_argument("--launch-notes", required=True)
    a.add_argument("--taxonomy", required=True)
    a.add_argument("--doc-state", required=True)
    a.add_argument("--doc-state-cross", default=None)
    a.add_argument("--arm", required=True, choices=("one-document", "cross-document", "both"))
    a.add_argument("--round", type=int, required=True)
    a.add_argument("--items-count", type=int, required=True)
    a.add_argument("--dest", required=True)
    a.add_argument("--writer", required=True)
    a.add_argument("--previous", default=None)
    a.add_argument("--prepare-config", default=None)
    a.add_argument("--cursor-deny", action="store_true", help="write <folder>/.cursor/cli.json (a Cursor CLI writer's deny-list) and list it in the manifest")
    v = sub.add_parser("verify")
    v.add_argument("--dest", required=True)
    v.add_argument("--manifest", required=True)
    u = sub.add_parser("audit")
    u.add_argument("--trace", required=True)
    u.add_argument("--manifest", required=True)
    u.add_argument("--format", choices=("claude-jsonl", "codex-jsonl", "paths"), default="claude-jsonl")
    u.add_argument("--out", default=None)
    ns = ap.parse_args(argv)
    if ns.cmd == "assemble":
        man = assemble(packet=Path(ns.packet), launch_notes=Path(ns.launch_notes), taxonomy=Path(ns.taxonomy),
                       doc_state=Path(ns.doc_state), doc_state_cross=Path(ns.doc_state_cross)
                       if ns.doc_state_cross else None, arm=ns.arm, round_no=ns.round,
                       items_count=ns.items_count, dest=Path(ns.dest), writer=ns.writer,
                       previous=Path(ns.previous) if ns.previous else None,
                       prepare_config=Path(ns.prepare_config) if ns.prepare_config else None, cursor_deny=ns.cursor_deny)
        print(json.dumps({"round_dir": man["round_dir"], "writer": man["writer"], "round": man["round"],
                          "arm": man["arm"], "files": sorted(man["files"]),
                          "packet_body_sha256": man["packet_body_sha256"][:8],
                          "preface_sha256": man["preface_sha256"][:8]}))
        return 0
    if ns.cmd == "verify":
        errs = verify(Path(ns.dest), Path(ns.manifest))
        print(json.dumps({"errors": errs, "clean": not errs}))
        return 0 if not errs else 2
    rec = audit(Path(ns.trace), Path(ns.manifest), ns.format, Path(ns.out) if ns.out else None)
    print(json.dumps({k: rec[k] for k in ("verdict", "writer", "round", "opened", "outside_existing",
                                           "never_open", "non_existent_tokens")}))
    return 0 if rec["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
