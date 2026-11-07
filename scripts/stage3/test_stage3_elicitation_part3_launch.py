"""Tests for stage3_elicitation_part3_launch.py (brief 30 Part 3: the launch-side record of a writer round).
Two pure functions: the working Claude Code deny-list settings for a writer session (the harness's flat
fragment is not Claude Code's schema and its single-slash patterns are project-relative; the probe of
2026-11-07 showed `permissions.deny` with `//` absolute patterns is what refuses a read), and the start-state
record of launch notes section 3 (existence and sha256 of files, never their contents). Temporary folders only."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_part3_launch as pl  # noqa: E402


def test_settings_use_claude_codes_schema_and_absolute_double_slash_patterns(tmp_path):
    folder = tmp_path / "w" / "opus55" / "r1"
    s = pl.writer_settings(folder, other_trees=[tmp_path / "w" / "gpt61sol"], home=Path("/Users/someone"))
    assert set(s) == {"permissions"} and set(s["permissions"]) == {"deny"}
    deny = s["permissions"]["deny"]
    assert all(d.startswith("Read(//") for d in deny), deny
    trees = [d for d in deny if not d.endswith(".md)")]
    assert trees and all(d.endswith("/**)") for d in trees), deny
    assert {"Read(//Users/someone/CLAUDE.md)", "Read(//Users/someone/AGENTS.md)"} <= set(deny)
    assert "Read(//Users/aravind/KruxAI/**)" in deny, "the project tree is always denied"
    assert any(str(tmp_path / "w" / "gpt61sol").lstrip("/") in d for d in deny), "the other writer's tree is denied"
    assert not any(str(folder).lstrip("/") + "/**" in d for d in deny), "the writer's own folder is not denied"


def test_settings_deny_the_harness_state_and_instruction_trees():
    s = pl.writer_settings(Path("/Users/aravind/elicitation-writers/opus55/r1"), other_trees=[], home=Path("/Users/aravind"))
    deny = " ".join(s["permissions"]["deny"])
    for t in ("/Users/aravind/.claude/", "/Users/aravind/.codex/", "/Users/aravind/.cursor/", "/tmp/"):
        assert t.lstrip("/") in deny, t


def test_start_state_records_existence_and_hashes_but_never_contents(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / "AGENTS.md").write_text("SECRET-LINE-ONE\n")
    folder = home / "elicitation-writers" / "opus55" / "r1"
    folder.mkdir(parents=True)
    (folder / "packet.md").write_text("body")
    rec = pl.start_state(folder, home=home, harness={"tool": "t", "version": "1", "model": "m", "effort": "high"})
    text = pl.render(rec)
    assert "SECRET-LINE-ONE" not in text, "file contents must never appear"
    assert rec["user_level"]["AGENTS.md"]["present"] is True and len(rec["user_level"]["AGENTS.md"]["sha256"]) == 64
    assert rec["user_level"]["CLAUDE.md"]["present"] is False
    assert rec["user_level"][".claude/CLAUDE.md"]["present"] is False
    assert rec["harness"]["effort"] == "high"
    assert rec["memory_index"]["present"] is False and rec["memory_index"]["path"].endswith(
        "-elicitation-writers-opus55-r1/memory/MEMORY.md"), rec["memory_index"]


def test_start_state_walks_every_parent_to_the_root_for_instruction_files(tmp_path):
    home = tmp_path / "home"
    folder = home / "a" / "b" / "r1"
    folder.mkdir(parents=True)
    (home / "a" / "CLAUDE.md").write_text("x")
    (home / "a" / ".claude").mkdir()
    rec = pl.start_state(folder, home=home, harness={})
    found = {(p["dir"], n) for p in rec["ancestors"] for n, v in p["entries"].items() if v["present"]}
    assert (str(home / "a"), "CLAUDE.md") in found and (str(home / "a"), ".claude") in found
    assert rec["ancestors"][-1]["dir"] == "/"
    assert rec["ancestors"][0]["dir"] == str(folder)


def test_start_state_reports_a_memory_index_that_exists(tmp_path):
    home = tmp_path / "home"
    folder = home / "w" / "r1"
    folder.mkdir(parents=True)
    slug = pl.session_slug(folder)
    mem = home / ".claude" / "projects" / slug / "memory"
    mem.mkdir(parents=True)
    (mem / "MEMORY.md").write_text("- a line\n")
    rec = pl.start_state(folder, home=home, harness={})
    assert rec["memory_index"]["present"] is True and len(rec["memory_index"]["sha256"]) == 64


def test_the_folder_listing_is_recorded_by_name_and_hash(tmp_path):
    home = tmp_path / "home"
    folder = home / "w" / "r1"
    (folder / "previous").mkdir(parents=True)
    (folder / "packet.md").write_text("p")
    (folder / "previous" / "items.json").write_text("{}")
    rec = pl.start_state(folder, home=home, harness={})
    assert sorted(rec["folder_files"]) == ["packet.md", "previous/items.json"]


def test_render_is_deterministic_and_json_round_trips(tmp_path):
    home = tmp_path / "home"
    folder = home / "w" / "r1"
    folder.mkdir(parents=True)
    a = pl.render(pl.start_state(folder, home=home, harness={"k": 1}))
    b = pl.render(pl.start_state(folder, home=home, harness={"k": 1}))
    assert a == b and json.loads(a)["harness"] == {"k": 1}


def test_rater_settings_add_write_denies_for_the_same_trees_but_never_for_the_raters_own_folder():
    s = pl.rater_settings(Path("/Users/aravind/elicitation-raters/dev-s/p1"), other_trees=[Path("/Users/aravind/elicitation-writers")],
                          home=Path("/Users/aravind"))
    deny = s["permissions"]["deny"]
    assert "Read(//Users/aravind/KruxAI/**)" in deny and "Write(//Users/aravind/KruxAI/**)" in deny
    assert "Write(//Users/aravind/elicitation-writers/**)" in deny and "Write(//Users/aravind/.claude/**)" in deny
    assert not any("elicitation-raters/dev-s/p1" in d for d in deny)
    assert not any(d.startswith("Write(") and d.endswith(".md)") for d in deny)


def test_start_state_records_the_user_level_agents_skills_directory(tmp_path):
    """Found at writer round 2 (2026-11-07): codex read a skill file under ~/.agents/skills on its own initiative; the notes'
    list of user-level instruction locations did not name it, so the start-state record did not either."""
    home = tmp_path / "home"
    (home / ".agents" / "skills").mkdir(parents=True)
    folder = home / "w" / "r2"
    folder.mkdir(parents=True)
    rec = pl.start_state(folder, home=home, harness={})
    assert rec["user_level"][".agents/skills"] == {"present": True, "kind": "dir"}
    assert any(p["dir"] == str(home) and p["entries"][".agents"]["present"] for p in rec["ancestors"])


def test_start_state_records_cursors_user_level_skills_mcp_plugins_and_agents(tmp_path):
    """A Cursor CLI writer (brief 30 note 12) loads these from the real home; the record names each so an exposure is counted."""
    home = tmp_path / "home"
    for d in (".cursor/skills", ".cursor/skills-cursor", ".cursor/plugins", ".cursor/agents"):
        (home / d).mkdir(parents=True)
    (home / ".cursor" / "mcp.json").write_text('{"mcpServers": {}}')
    folder = home / "w" / "r3"
    folder.mkdir(parents=True)
    rec = pl.start_state(folder, home=home, harness={})
    for name in (".cursor/skills", ".cursor/skills-cursor", ".cursor/plugins", ".cursor/agents", ".cursor/mcp.json"):
        assert rec["user_level"][name]["present"] is True, name
    assert len(rec["user_level"][".cursor/mcp.json"]["sha256"]) == 64 and "mcpServers" not in json.dumps(rec)


def test_cursor_config_uses_cursors_working_pattern_forms_only():
    """Cursor probe 2 (2026-11-07): inside the workspace `Read(/abs/path)`, `Read(**/x)` and `Read(/abs/dir/**)` refuse; the
    double-slash and tilde forms do not, and a config in a parent directory is not read. So: single-slash absolute patterns."""
    c = pl.cursor_cli_config(Path("/Users/aravind/elicitation-writers/muse_wonder/r3"), other_trees=[Path("/Users/aravind/elicitation-writers/opus55")],
                             home=Path("/Users/aravind"))
    assert set(c) == {"permissions"} and c["permissions"]["allow"] == []
    deny = c["permissions"]["deny"]
    assert "Read(/Users/aravind/KruxAI/**)" in deny and "Read(/Users/aravind/.agents/**)" in deny and "Read(/Users/aravind/.cursor/**)" in deny
    assert "Read(/Users/aravind/elicitation-writers/opus55/**)" in deny
    assert {"Write(**)", "Shell(**)", "WebFetch(**)"} <= set(deny)
    reads = [d for d in deny if d.startswith("Read(")]
    assert reads and all(d.startswith("Read(/") and not d.startswith("Read(//") and "~" not in d for d in reads)
    assert not any("muse_wonder/r3" in d for d in deny), "the writer's own folder is never denied"
