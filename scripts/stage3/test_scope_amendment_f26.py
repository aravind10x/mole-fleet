"""Dated addendum 2026-10-23 (brief 07f B4; design v4 section 11.6, F2.6) to the scope
amendment `stage3-shared-documents-2026-10-20`: the two ownCloud line-level edit actions the
fork added on 2026-10-22 (`append_to_file`, `replace_in_file`) are file write touches on
`path`, like `write_file`, when the amendment is on, and are not touches at all when it is off
(the default, the only mode Stage 2b ran). Stage 2b numbers are not recomputed.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_scope_amendment_f26.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import grouping_measure as gm  # noqa: E402
import mole_corpus as mc  # noqa: E402

PROJECT = HERE.parent.parent
FORK_COPY = PROJECT / "work" / "mole-fork" / "scripts" / "track_b" / "mole_corpus.py"
AMENDMENT = "stage3-shared-documents-2026-10-20"
D1 = "2026-04-06"
X = "/shared/x.md"
EDITS = ("append_to_file", "replace_in_file")


def ev(i, ts, account, action, args, code=0):
    return {"event_id": f"e{i}", "ts": ts, "account": account, "service": "owncloud",
            "action": action, "resource_id": args["path"], "args": args, "exit_code": code,
            "result_meta": {}, "task_id": "t"}


EVENTS = [
    ev(0, f"{D1}T09:00:00Z", "ana.b", "append_to_file", {"path": X, "text": "line\n"}),
    ev(1, f"{D1}T10:00:00Z", "ben.c", "replace_in_file",
       {"path": X, "find": "line", "replace": "LINE"}),
    ev(2, f"{D1}T11:00:00Z", "cy.d", "write_file", {"path": "/shared/y.md", "content": "y\n"}),
    ev(3, f"{D1}T12:00:00Z", "cy.d", "append_to_file", {"path": "/shared/z.md", "text": "z"},
       code=1),
]


@pytest.fixture()
def corpus(tmp_path) -> Path:
    p = tmp_path / "synth_edits.jsonl"
    p.write_text("".join(json.dumps(e) + "\n" for e in EVENTS), encoding="utf-8")
    return p


def _touches(corpus: Path):
    df = mc.load_fork_audit(corpus)
    parsed, _ = mc.parse_args_column(df["args"])
    return mc.touches(df, parsed, include_fork_only=True, fork_erratum=True)


def _g1(corpus: Path):
    br = gm.load_branch(corpus, None, mc.load_org_template(str(gm.DEFAULT_TEMPLATE)))
    spec = gm.GenSpec("G1", "G1", 1)
    return br, [gm.day_groups(br, spec, d) for d in br.bdays]


def test_amendment_off_edit_actions_are_not_touches(corpus):
    assert mc.scope_amendment() is None
    for a in EDITS:
        assert mc.rule_for("owncloud", a) is None
        assert mc.rules_for("owncloud", a) == () == mc.rules_for("owncloud", a, True)
    t = _touches(corpus)
    assert not t["action"].isin(EDITS).any()
    w = t[(t.action == "write_file") & (t.kind == "write")]
    assert list(zip(w.type, w.artefact)) == [("file", "/shared/y.md")]
    _, days = _g1(corpus)
    assert [len(g.sets) for g in days] == [0]


def test_amendment_on_edit_actions_are_file_writes_and_g1_finds_the_pair(corpus):
    with mc.scope_amendment_context(AMENDMENT):
        wf = mc.rule_for("owncloud", "write_file")
        for a in EDITS:
            r = mc.rule_for("owncloud", a)
            assert (r.kind, r.keys, r.type, r.mode, r.sub) == (
                wf.kind, wf.keys, wf.type, wf.mode, wf.sub) == ("write", ("path",), "file",
                                                                "first", "")
        t = _touches(corpus)
        e = t[t.action.isin(EDITS)]
        assert sorted(zip(e.account, e.type, e.kind, e.artefact)) == [
            ("ana.b", "file", "write", X), ("ben.c", "file", "write", X)]
        assert ((t.action == "write_file") & (t.artefact == "/shared/y.md")).sum() == 1
        br, days = _g1(corpus)
        names = [{frozenset(br.ci.accounts[i] for i in s) for s in g.sets} for g in days]
    assert names == [{frozenset({"ana.b", "ben.c"})}]
    assert mc.scope_amendment() is None                          # restored
    assert not _touches(corpus)["action"].isin(EDITS).any()


def test_failed_edit_row_is_not_a_touch(corpus):
    with mc.scope_amendment_context(AMENDMENT):
        t = _touches(corpus)
    assert "/shared/z.md" not in set(t.artefact)
    assert 3 not in set(t.ev)


def test_fork_copy_is_byte_identical():
    assert subprocess.run(["cmp", str(HERE / "mole_corpus.py"), str(FORK_COPY)]).returncode == 0
