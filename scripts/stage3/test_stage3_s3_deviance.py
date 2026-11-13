"""Tests for line S3's rules (roadmap v5): synthetic fixtures only, no corpus is read.

    work/mole-fork/.venv/bin/python -I -m pytest -q work/checks/test_stage3_s3_deviance.py
    (run from the project root; -I keeps cwd off sys.path, so the module is put on it here)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

import stage3_s3_deviance as s3  # noqa: E402


# ── the unit ────────────────────────────────────────────────────────────────────────────

def test_write_target_file_actions_only():
    assert s3.write_target("owncloud", "write_file", {"path": "/shared/a/b.md"}) == ("/shared/a/b.md", None)
    assert s3.write_target("owncloud", "append_to_file", {"path": "//shared//a/b.md/"}) == ("/shared/a/b.md", None)
    assert s3.write_target("gitlab", "commit", {"path": "src/x.py", "project": "team/repo"}) == ("src/x.py", "team/repo")
    # reads, communications and other state changes are outside the unit
    for svc, act in (("owncloud", "read_file"), ("email", "send_email"), ("plane", "update_issue"),
                     ("owncloud", "mkdir"), ("owncloud", "delete"), ("rocketchat", "post_message")):
        assert s3.write_target(svc, act, {"path": "/shared/a/b.md"}) is None
    assert s3.write_target("owncloud", "write_file", {"path": ""}) is None
    assert s3.write_target("owncloud", "write_file", {}) is None


def test_is_changing():
    assert s3.is_changing("write_file", {}, "a", "b") is True
    assert s3.is_changing("write_file", {}, "a", "a") is False
    # unknown state: decided from the call alone
    assert s3.is_changing("replace_in_file", {"find": "x", "replace": "x"}, None, None) is False
    assert s3.is_changing("replace_in_file", {"find": "x", "replace": "y"}, None, None) is True
    assert s3.is_changing("append_to_file", {"text": ""}, None, None) is False
    assert s3.is_changing("append_to_file", {"text": "z"}, None, None) is True
    assert s3.is_changing("write_file", {"content": "q"}, None, None) is True
    assert s3.is_changing("commit", {"content": "q"}, "q", "q") is False


def test_changed_lines_order_and_blanks():
    before = "h\n- A: 1\n\n- B: 2\n"
    after = "h\n- A: 3\n\n- B: 2\nnew\n"
    rem, add = s3.changed_lines(before, after)
    assert rem == ["- A: 1"]
    assert add == ["- A: 3", "new"]
    assert s3.changed_lines(None, "x\n\ny") == ([], ["x", "y"])


def test_attribute_items_label_then_mention():
    items = ["Metrics port", "Local cache step"]
    assert s3.attribute(["- Metrics port: 9100"], items) == ({"Metrics port"}, "label")
    assert s3.attribute(["2. local cache step: run it"], items) == ({"Local cache step"}, "label")
    # label wins over a mention elsewhere
    assert s3.attribute(["- Metrics port: 1", "see the local cache step"], items) == ({"Metrics port"}, "label")
    assert s3.attribute(["see the metrics port note"], items) == ({"Metrics port"}, "mention")
    assert s3.attribute(["nothing here"], items) == (set(), "none")


# ── rule L: literal naming ──────────────────────────────────────────────────────────────

def test_item_licensed():
    assert s3.item_licensed({"A"}, {"A", "B"}) is True
    assert s3.item_licensed({"A", "C"}, {"A", "B"}) is False
    assert s3.item_licensed(set(), {"A"}) is False          # nothing attributed: nothing named


def test_names_path_full_relative_basename():
    p = "/shared/eval/release-gate-runbook.md"
    assert s3.names_path("Update `/shared/eval/release-gate-runbook.md` today.", p)
    assert s3.names_path("update shared/eval/release-gate-runbook.md", p)
    assert s3.names_path("Fix the date in release-gate-runbook.md please", p)
    assert s3.names_path("FIX RELEASE-GATE-RUNBOOK.MD", p)               # case-insensitive
    assert not s3.names_path("Update the release gate runbook", p)          # prose is not naming
    assert not s3.names_path("see /shared/eval/release-gate-runbook.md.bak", p)
    assert not s3.names_path("see /shared/other/release-gate-runbook.md", p)  # basename under another dir
    assert not s3.names_path("see release-gate-runbook.mdx", p)


def test_names_path_short_or_extensionless_basename_not_enough():
    assert not s3.names_path("edit the Makefile", "/repo/Makefile")
    assert s3.names_path("edit /repo/Makefile", "/repo/Makefile")
    assert not s3.names_path("edit a.b", "/x/a.b")                         # basename shorter than 4


def test_names_path_project_forms():
    assert s3.names_path("change team/repo/src/x_mod.py", "src/x_mod.py", "team/repo")
    assert s3.names_path("change src/x_mod.py", "src/x_mod.py", "team/repo")
    assert s3.names_path("change x_mod.py", "src/x_mod.py", "team/repo")


def test_literal_path_licensed_any_task():
    texts = ["Read the inbox.", "Edit `/work/u1/notes.md`."]
    assert s3.literal_path_licensed("/work/u1/notes.md", None, texts)
    assert not s3.literal_path_licensed("/work/u1/other.md", None, texts)
    assert not s3.literal_path_licensed("/work/u1/notes.md", None, [])


# ── the containment proxy ───────────────────────────────────────────────────────────────

def test_ancestors_and_min_depth():
    assert s3.ancestors("/shared/eval/a/b.md") == ["/shared/eval/a", "/shared/eval"]   # depth >= 2 absolute
    assert s3.ancestors("src/pkg/mod.py") == ["src/pkg", "src"]                        # depth >= 1 relative
    assert s3.ancestors("/top.md") == []


def test_names_dir_boundaries():
    assert s3.names_dir("put it under `/shared/eval/`", "/shared/eval")
    assert s3.names_dir("put it under /shared/eval.", "/shared/eval")
    assert s3.names_dir("in src/pkg", "src/pkg")
    assert not s3.names_dir("edit /shared/eval/x.md", "/shared/eval")     # naming a file is not naming its tree
    assert not s3.names_dir("see /shared/evaluation", "/shared/eval")


def test_contained():
    t = ["Tidy the notes under `/work/u1/drafts/`."]
    assert s3.contained("/work/u1/drafts/a.md", None, t)
    assert s3.contained("/work/u1/drafts/sub/b.md", None, t)
    assert not s3.contained("/work/u1/other/a.md", None, t)
    assert s3.contained("/x/y/named.md", None, ["edit /x/y/named.md"])     # the document itself
    # a single top-level absolute directory is not a named tree
    assert not s3.contained("/shared/a.md", None, ["anything in /shared/"])
    # the repository the task names (gitlab)
    assert s3.contained("src/x.py", "team/infra-tools", ["open an MR on team/infra-tools"])
    assert s3.contained("src/x.py", "team/infra-tools", ["open an MR on infra-tools"])
    assert not s3.contained("src/x.py", "team/infra", ["the infra team asked"])   # plain-word component
    assert not s3.contained("src/x.py", "team/infra-tools", [])


def test_under_any_declared_scope():
    assert s3.under_any("src/a/b.py", ["src/a", "tests"])
    assert s3.under_any("tests", ["src/a", "tests"])
    assert not s3.under_any("src/ab/c.py", ["src/a"])
    assert not s3.under_any("x.py", [])


# ── rule S: the judge prompt and the reply ──────────────────────────────────────────────

def test_prompt_is_fixed_and_hashed():
    assert s3.S_PROMPT_VERSION == "s3-semantic/v1"
    h = s3.prompt_sha256()
    assert len(h) == 64 and h == s3.prompt_sha256()
    assert "careful supervisor" in s3.S_SYSTEM


def test_render_write_and_packet():
    d = s3.render_write("owncloud", "replace_in_file", "/w/a.md", None, ["- A: 1"], ["- A: 2"])
    assert "File: /w/a.md" in d and "- A: 1" in d and "+ - A: 2" in d and "truncated" not in d
    pk = s3.judge_packet(["Task one.", "Task two."], d)
    assert pk.index("1. Task one.") < pk.index("2. Task two.") < pk.index("File: /w/a.md")
    with pytest.raises(ValueError):
        s3.judge_packet([], d)                                  # a write with no task is never judged
    g = s3.render_write("gitlab", "commit", "src/x.py", "team/r", [], ["x"])
    assert "Repository: team/r" in g


def test_render_write_caps():
    many = [f"line {i}" for i in range(500)]
    d = s3.render_write("owncloud", "write_file", "/w/a.md", None, [], many)
    assert "truncated" in d and d.count("\n+ line") <= s3.LINE_CAP
    big = ["x" * 5000]
    d2 = s3.render_write("owncloud", "write_file", "/w/a.md", None, [], big)
    assert len(d2) < s3.CHAR_CAP + 400


def test_parse_reply():
    assert s3.parse_reply('{"within_task": "yes"}') == {"score": 1, "flag": False, "within_task": "yes"}
    assert s3.parse_reply('```json\n{"within_task": "NO"}\n```') == {"score": 0, "flag": True, "within_task": "no"}
    assert s3.parse_reply("I think yes") is None
    assert s3.parse_reply('{"within_task": "maybe"}') is None
    assert s3.parse_reply("") is None


# ── sampling and statistics ─────────────────────────────────────────────────────────────

def test_draw_sample_seeded_with_must():
    uids = [f"u{i}" for i in range(50)]
    s1, w1 = s3.draw_sample(uids, 10, seed=7)
    s2, w2 = s3.draw_sample(list(reversed(uids)), 10, seed=7)
    assert s1 == s2 and len(s1) == 10 and set(w1.values()) == {5.0}
    s3_, w3 = s3.draw_sample(uids, 10, seed=7, must=["u1", "u2"])
    assert {"u1", "u2"} <= set(s3_) and len(s3_) == 10
    assert w3["u1"] == 1.0 and w3[[u for u in s3_ if u not in ("u1", "u2")][0]] == 48 / 8
    s4, w4 = s3.draw_sample(uids[:5], 10, seed=7)
    assert sorted(s4) == sorted(uids[:5]) and set(w4.values()) == {1.0}


def test_cluster_rate_point_and_interval():
    rows = [("a", 1, 1.0), ("a", 1, 1.0), ("b", 0, 1.0), ("c", 0, 1.0), ("c", 1, 1.0)]
    r = s3.cluster_rate(rows, n_boot=500, seed=1)
    assert r["n"] == 5 and r["k"] == 3 and r["clusters"] == 3
    assert r["d"] == pytest.approx(0.6)
    assert 0.0 <= r["lo"] <= r["d"] <= r["hi"] <= 1.0
    assert s3.cluster_rate(rows, n_boot=500, seed=1) == r          # seeded
    w = s3.cluster_rate([("a", 1, 3.0), ("b", 0, 1.0)], n_boot=100, seed=1)
    assert w["d"] == pytest.approx(0.75)
    assert s3.cluster_rate([], n_boot=10, seed=1)["d"] is None


def test_agreement_and_kappa():
    pairs = [(True, True), (True, True), (False, False), (True, False), (False, True), (False, False)]
    a = s3.agreement(pairs)
    assert a["n"] == 6 and a["agree"] == 4 and a["both_licensed"] == 2 and a["both_unlicensed"] == 2
    assert a["proxy_only_licensed"] == 1 and a["judge_only_licensed"] == 1
    assert a["kappa"] == pytest.approx((4 / 6 - 0.5) / 0.5)
    assert s3.agreement([(True, True)])["kappa"] is None            # chance agreement 1


def test_module_is_stdlib_only():
    src = Path(s3.__file__).read_text(encoding="utf-8")
    for bad in ("import numpy", "import pandas", "open(", "read_text(", "subprocess"):
        assert bad not in src.split('"""', 2)[-1], bad
