"""Tests for stage3_elicitation_harness.py (brief 30, Part 1 item 4; decision 7 and the cold read's
item 3): the clean harness assembles a writer's round folder outside the project from the four
hash-pinned files, writes a manifest, refuses any other file, and is made enforceable by a permission
deny-list plus the trace audit whose PASS gates the converter. No item text appears here."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_convert as cv  # noqa: E402
import stage3_elicitation_harness as hs  # noqa: E402

ROOT = HERE.parent.parent
PACKET = ROOT / "work/stage3/elicitation/writer-packet-v0.md"
NOTES = ROOT / "work/stage3/elicitation/writer-launch-notes-v0.md"
TAXONOMY = ROOT / "work/stage3/elicitation/taxonomy-v0.md"
STATE_ONE = ROOT / "work/stage3/t1k-rater/doc-states-day0.md"
STATE_CROSS = ROOT / "work/stage3/elicitation/doc-states-day0-v7.md"


def _assemble(tmp_path: Path, dest_name="w1", arm="one-document", count=24, round_no=1, **kw):
    dest = tmp_path / "rounds" / dest_name
    man = hs.assemble(packet=PACKET, launch_notes=NOTES, taxonomy=TAXONOMY,
                      doc_state=STATE_ONE if arm in ("one-document", "both") else STATE_CROSS,
                      doc_state_cross=STATE_CROSS if arm in ("cross-document", "both") else None,
                      arm=arm, round_no=round_no, items_count=count, dest=dest, writer="opus55", **kw)
    return dest, man


# ── assembly ──────────────────────────────────────────────────────────────────────────────────────

def test_assemble_verifies_the_four_sources_by_hash(tmp_path):
    bad = tmp_path / "packet.md"
    bad.write_text(PACKET.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(hs.UsageError):
        hs.assemble(packet=bad, launch_notes=NOTES, taxonomy=TAXONOMY, doc_state=STATE_ONE,
                    arm="one-document", round_no=1, items_count=24,
                    dest=tmp_path / "r", writer="w")
    with pytest.raises(hs.UsageError):
        hs.assemble(packet=PACKET, launch_notes=NOTES, taxonomy=TAXONOMY, doc_state=STATE_CROSS,
                    arm="one-document", round_no=1, items_count=24,
                    dest=tmp_path / "r2", writer="w")


def test_assemble_writes_exactly_the_round_folder(tmp_path):
    dest, man = _assemble(tmp_path)
    names = sorted(p.name for p in dest.iterdir())
    assert names == ["documents-one-document.md", "packet.md", "round.md"]
    body = (dest / "packet.md").read_bytes()
    import hashlib
    assert hashlib.sha256(body).hexdigest().startswith("cb528f5d")
    assert (dest / "documents-one-document.md").read_bytes() == STATE_ONE.read_bytes()
    assert (dest / "round.md").read_text(encoding="utf-8").splitlines() == [
        "Round: 1", "Arm: one-document", "Items to write per arm: 24"]
    assert man["round"] == 1 and man["arm"] == "one-document" and man["writer"] == "opus55"
    assert man["sources"]["packet"]["sha256"].startswith("486ac7f9")
    assert man["sources"]["launch_notes"]["sha256"].startswith("147dae26")
    assert man["sources"]["taxonomy"]["sha256"].startswith("ec195e23")
    assert man["sources"]["doc_state"]["sha256"].startswith("d0f3fbae")
    assert man["packet_body_sha256"].startswith("cb528f5d")
    assert set(man["files"]) == {"packet.md", "round.md", "documents-one-document.md"}
    assert Path(man["round_dir"]) == dest and man["manifest_version"] == hs.VERSION
    assert not (dest / "manifest.json").exists()      # the manifest stays outside the writer's folder


def test_assemble_both_arms_and_previous(tmp_path):
    prev = tmp_path / "prev"
    prev.mkdir()
    (prev / "items.json").write_text('{"items": []}', encoding="utf-8")
    (prev / "results.json").write_text('{"results": []}', encoding="utf-8")
    dest, man = _assemble(tmp_path, arm="both", dest_name="w2", count=96, round_no=2, previous=prev)
    names = sorted(p.name for p in dest.iterdir())
    assert names == ["documents-cross-document.md", "documents-one-document.md", "packet.md",
                     "previous", "round.md"]
    assert (dest / "previous" / "items.json").read_bytes() == (prev / "items.json").read_bytes()
    assert man["files"]["previous/items.json"] == man["previous"]["items.json"]


def test_assemble_refuses_a_non_empty_or_project_inside_destination(tmp_path):
    dest = tmp_path / "rounds" / "full"
    dest.mkdir(parents=True)
    (dest / "stray.txt").write_text("x", encoding="utf-8")
    with pytest.raises(hs.UsageError):
        _assemble(tmp_path, dest_name="full")
    with pytest.raises(hs.UsageError):
        hs.assemble(packet=PACKET, launch_notes=NOTES, taxonomy=TAXONOMY, doc_state=STATE_ONE,
                    arm="one-document", round_no=1, items_count=24,
                    dest=ROOT / "work" / "stage3" / "no-writer-here", writer="w")


def test_verify_detects_any_change(tmp_path):
    dest, man = _assemble(tmp_path)
    man_path = tmp_path / "manifest.json"
    man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
    assert hs.verify(dest, man_path) == []
    (dest / "round.md").write_text("Round: 2\n", encoding="utf-8")
    errs = hs.verify(dest, man_path)
    assert errs and errs[0].startswith("round.md")
    (dest / "stray.txt").write_text("x", encoding="utf-8")
    assert any(e.startswith("stray") for e in hs.verify(dest, man_path))


def test_the_preface_and_round_template_come_from_the_launch_notes():
    preface, template = hs.launch_notes_conventions(NOTES)
    assert preface.startswith("Your working directory is the folder you were started in.")
    assert preface.endswith("write no files.")
    assert template == ("Round: ", "Arm: ", "Items to write per arm: ")


def test_deny_list_is_written_beside_the_manifest_in_claude_codes_own_schema(tmp_path):
    """Brief 30 note 9 item 5: the fragment the harness wrote (flat `deny`, single-slash patterns) was not Claude Code's
    schema and refused nothing. It is now `permissions.deny` with `//`-absolute Read patterns, the same settings
    stage3_elicitation_part3_launch.writer_settings gives (a probe on 2026-11-07 showed a project read refused)."""
    dest, man = _assemble(tmp_path)
    perm = dest.parent / "permissions-w1.json"
    assert perm.exists()
    rules = json.loads(perm.read_text(encoding="utf-8"))
    assert set(rules) == {"permissions"} and set(rules["permissions"]) == {"deny"}
    deny = rules["permissions"]["deny"]
    assert "Read(//Users/aravind/KruxAI/**)" in deny and "Read(//Users/aravind/.claude/**)" in deny
    assert all(d.startswith("Read(//") for d in deny), "every pattern is `//`-absolute; a single slash is project-relative"
    assert man["deny_list"]["settings"] == str(perm) and man["deny_list"]["schema"] == "claude-code permissions.deny"


def test_deny_list_denies_a_sibling_writers_tree_but_never_the_writers_own_folder(tmp_path):
    other = tmp_path / "rounds" / "gpt61sol"
    other.mkdir(parents=True)
    dest, man = _assemble(tmp_path, dest_name="opus55/r1")   # tmp_path/rounds/opus55/r1, beside the other writer's tree
    deny = json.loads((dest.parent / "permissions-r1.json").read_text(encoding="utf-8"))["permissions"]["deny"]
    assert any(str(other).lstrip("/") in d for d in deny)
    assert not any(d == f"Read(/{str(dest).lstrip('/')}/**)" for d in deny)


# ── the trace audit (the pinned script, wrapped) and the converter gate ────────────────────────────

def _trace(tmp_path: Path, paths: list[str]) -> Path:
    t = tmp_path / "trace.paths"
    t.write_text("\n".join(paths) + "\n", encoding="utf-8")
    return t


def test_audit_passes_on_the_round_files_only(tmp_path):
    dest, man = _assemble(tmp_path)
    man_path = tmp_path / "manifest.json"
    man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
    trace = _trace(tmp_path, ["packet.md", "round.md", "documents-one-document.md", "./packet.md"])
    rec = hs.audit(trace, man_path, format="paths", out=tmp_path / "audit.json")
    assert rec["verdict"] == "PASS"
    assert json.loads((tmp_path / "audit.json").read_text(encoding="utf-8"))["verdict"] == "PASS"


def test_audit_fails_on_the_project_and_other_writers(tmp_path):
    dest, man = _assemble(tmp_path)
    man_path = tmp_path / "manifest.json"
    man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
    other = tmp_path / "rounds" / "w2"
    other.mkdir(parents=True)
    (other / "packet.md").write_text("x", encoding="utf-8")
    for bad in [str(ROOT / "work/stage3/b3/b3-results.md"), str(other / "packet.md"),
                str(ROOT / "work/mole-fork/scripts/stage3/stage3_t1.py")]:
        rec = hs.audit(_trace(tmp_path, ["packet.md", bad]), man_path, format="paths")
        assert rec["verdict"] == "FAIL", bad


def test_audit_allows_the_sessions_own_state_dirs(tmp_path):
    dest, man = _assemble(tmp_path)
    man_path = tmp_path / "manifest.json"
    man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
    slug = hs.session_slug(dest)
    scratch = Path.home() / ".claude" / "projects" / slug
    rec = hs.audit(_trace(tmp_path, ["packet.md", f"{scratch}/session.jsonl",
                                     "/private/var/folders/xx/scratch", "/tmp/scratch"]),
                   man_path, format="paths")
    assert rec["verdict"] == "PASS"


def test_converter_gate_needs_a_passing_audit_for_the_manifest(tmp_path):
    dest, man = _assemble(tmp_path)
    man_path = tmp_path / "manifest.json"
    man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
    trace = _trace(tmp_path, ["packet.md", "round.md"])
    rec = hs.audit(trace, man_path, format="paths", out=tmp_path / "audit.json")
    assert rec["verdict"] == "PASS"
    answer = tmp_path / "answer.json"
    answer.write_text(json.dumps(cv.synthetic_writer_file(), indent=1), encoding="utf-8")
    out = tmp_path / "converted"
    # no gate -> refused; a failing audit -> refused; a foreign manifest -> refused
    with pytest.raises(cv.UsageError):
        cv.convert_file(answer, STATE_ONE, out_dir=out, writer="opus55", state_cross=STATE_CROSS)
    fail_rec = tmp_path / "audit-fail.json"
    hs.audit(_trace(tmp_path, ["packet.md", str(ROOT / "STATUS.md")]), man_path, format="paths",
             out=fail_rec)
    with pytest.raises(cv.UsageError):
        cv.convert_file(answer, STATE_ONE, out_dir=out, writer="opus55", state_cross=STATE_CROSS,
                        manifest=man_path, audit=fail_rec)
    other_man = tmp_path / "manifest2.json"
    m2 = dict(man, round_dir=str(tmp_path / "rounds" / "w9"))
    other_man.write_text(json.dumps(m2, indent=1), encoding="utf-8")
    with pytest.raises(cv.UsageError):
        cv.convert_file(answer, STATE_ONE, out_dir=out, writer="opus55", state_cross=STATE_CROSS,
                        manifest=other_man, audit=tmp_path / "audit.json")
    # the passing audit for exactly this manifest opens the gate
    rep = cv.convert_file(answer, STATE_ONE, out_dir=out, writer="opus55", state_cross=STATE_CROSS,
                          manifest=man_path, audit=tmp_path / "audit.json")
    assert rep["funnel"]["written"] == 8

def test_audit_passes_when_the_round_folder_is_outside_every_state_tree(tmp_path):
    """Found at the first real audit (brief 30 Part 3, 2026-11-07): the allow-list was computed and never applied, so a
    trace that opened exactly the round folder's files failed whenever the folder was not under a state tree. pytest's
    tmp_path sits under /private/var/folders (a state tree), which hid it; this folder is under the home directory."""
    import shutil
    import tempfile
    base = Path(tempfile.mkdtemp(prefix=".audit-test-", dir=Path.home()))
    try:
        dest, man = _assemble(base, dest_name="opus55/r1")
        man_path = base / "manifest.json"
        man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
        files = [str(dest / n) for n in ("packet.md", "round.md", "documents-one-document.md")]
        rec = hs.audit(_trace(tmp_path, files), man_path, format="paths")
        assert rec["verdict"] == "PASS", rec
        assert rec["outside_existing"] == 0 and rec["never_open"] == 0 and rec["opened"] == 3
        bad = hs.audit(_trace(tmp_path, files + [str(base / "manifest.json")]), man_path, format="paths")
        assert bad["verdict"] == "FAIL" and bad["outside_existing"] == 1, "a file beside the folder is still outside it"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _codex_trace(path: Path, commands: list[str], output: str = "") -> Path:
    """A minimal codex --json trace: one completed command_execution item per command (the shape of a real trace),
    plus a non-command event that nests a string, so the adapter's walk over nested values is exercised."""
    rows = [{"type": "thread.started", "thread_id": "t"}, {"type": "turn.started"}]
    for c in commands:
        rows.append({"type": "item.completed", "item": {"id": "i", "type": "command_execution", "command": c,
                                                           "aggregated_output": output, "exit_code": 0, "status": "completed"}})
    rows.append({"type": "turn.completed", "usage": {"input_tokens": 1}})
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_codex_adapter_reads_nested_events_and_does_not_count_the_shell_wrapper_as_a_file(tmp_path):
    """Found at the first real codex audit (brief 30 Part 3, 2026-11-07): the adapter's nested walk assigned to a name
    it had not bound (UnboundLocalError), and every codex command starts with /bin/zsh -lc, an existing file outside
    the allow-list. A trace whose commands only cat the round folder's files must pass."""
    import shutil
    import tempfile
    base = Path(tempfile.mkdtemp(prefix=".audit-test-", dir=Path.home()))
    try:
        dest, man = _assemble(base, dest_name="gpt61sol/r1")
        man_path = base / "manifest.json"
        man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
        tr = _codex_trace(tmp_path / "t.jsonl", ["/bin/zsh -lc 'cat packet.md round.md'",
                                                  "/bin/zsh -lc 'cat documents-one-document.md'"],
                          output="see and/or the shared notes")
        rec = hs.audit(tr, man_path, format="codex-jsonl")
        assert rec["verdict"] == "PASS", rec
        bad = _codex_trace(tmp_path / "bad.jsonl", [f"/bin/zsh -lc 'cat {ROOT / 'STATUS.md'}'"])
        r2 = hs.audit(bad, man_path, format="codex-jsonl")
        assert r2["verdict"] == "FAIL" and r2["never_open"] >= 1, r2
        other = _codex_trace(tmp_path / "other.jsonl", [f"/bin/zsh -lc 'cat {base / 'manifest.json'}'"])
        r3 = hs.audit(other, man_path, format="codex-jsonl")
        assert r3["verdict"] == "FAIL" and r3["outside_existing"] >= 1, r3
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_audit_does_not_count_the_round_folder_itself_as_never_open(tmp_path):
    """Found by the Cursor probe (brief 30 note 12): Cursor's init event names the session's working folder, a path equal to the
    round folder. The never-open rule excluded paths inside the folder but not the folder itself."""
    import shutil
    import tempfile
    base = Path(tempfile.mkdtemp(prefix=".audit-test-", dir=Path.home()))
    try:
        dest, man = _assemble(base, dest_name="muse_wonder/r3")
        mp = base / "manifest.json"
        mp.write_text(json.dumps(man, indent=1), encoding="utf-8")
        files = [str(dest), str(dest / "round.md"), str(dest / "packet.md")]
        rec = hs.audit(_trace(tmp_path, files), mp, format="paths")
        assert rec["verdict"] == "PASS" and rec["never_open"] == 0, rec
        other = hs.audit(_trace(tmp_path, files + [str(dest.parent.parent / "someone-else" / "r1" / "packet.md")]), mp, format="paths")
        assert other["verdict"] == "FAIL" and other["never_open"] == 1, "another writer's tree is still never-open"
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_cursor_deny_puts_the_config_inside_the_round_folder_and_in_the_manifest(tmp_path):
    """A Cursor CLI writer reads its deny-list from <workspace>/.cursor/cli.json only (probe 2, 2026-11-07), so the folder carries
    that one extra file, named in the manifest; without the option the folder is exactly as before."""
    import shutil
    import tempfile
    base = Path(tempfile.mkdtemp(prefix=".audit-test-", dir=Path.home()))
    try:
        plain, plain_man = _assemble(base, dest_name="a/r1")
        assert ".cursor/cli.json" not in plain_man["files"] and not (plain / ".cursor").exists()
        dest, man = _assemble(base, dest_name="muse_wonder/r3", cursor_deny=True)
        cfg = dest / ".cursor" / "cli.json"
        assert cfg.is_file() and ".cursor/cli.json" in man["files"]
        deny = json.loads(cfg.read_text(encoding="utf-8"))["permissions"]["deny"]
        assert "Read(/Users/aravind/KruxAI/**)" in deny and any("/a/" in d for d in deny), "the sibling writer's tree is denied"
        mp = base / "m.json"
        mp.write_text(json.dumps(man), encoding="utf-8")
        assert hs.verify(dest, mp) == []
        tr = _trace(tmp_path, [str(dest / "round.md"), str(cfg)])
        assert hs.audit(tr, mp, format="paths")["verdict"] == "PASS"
    finally:
        shutil.rmtree(base, ignore_errors=True)
