"""The shared document reader (mole/oracles/document.py).

Two kinds of evidence:

* the honest prefix (data/corpus/spike/prefix_v1.jsonl, read only, label-blind): for every
  plane issue and eval config with a content write by the end of 2026-04-07, the log replay
  from the day-1 managers snapshot equals the day-2 snapshot, and the log-only replay equals
  the snapshot for every document whose first write is in the log (create_issue /
  create_config); the same holds for day 1 alone;
* a synthetic ownCloud log and a synthetic GitLab log (routine placeholder edits only): last
  successful write at or before a time, failures ignored, argument aliases, folder deletes.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mole.oracles import document as doc

FORK = Path(__file__).resolve().parent.parent
PREFIX = FORK / "data" / "corpus" / "spike" / "prefix_v1.jsonl"
D1, D2 = "2026-04-06", "2026-04-07"

needs_prefix = pytest.mark.skipif(
    not (PREFIX.exists() and doc.managers_path(PREFIX, D2).exists()),
    reason="honest prefix or its managers snapshots not on disk")


# ── pure helpers ─────────────────────────────────────────────────────

def test_coerce_text():
    assert doc.coerce_text("a\nb") == "a\nb"
    assert doc.coerce_text(b"caf\xc3\xa9") == "café"
    assert doc.coerce_text(b"\xff") == "�"
    assert doc.coerce_text(None) == "" and doc.coerce_text(3) == "3"
    a = doc.coerce_text({"b": 1, "a": [2, {"d": 1, "c": "é"}]})
    b = doc.coerce_text({"a": [2, {"c": "é", "d": 1}], "b": 1})
    assert a == b and json.loads(a) == {"a": [2, {"c": "é", "d": 1}], "b": 1} and "é" in a
    assert doc.coerce_text([1, "x"]) == json.dumps([1, "x"], indent=2)


def test_unified_diff():
    before = "line one\nline two\n"
    after = "line one\nline two\nToday's date: 2026-04-07\n"
    d = doc.unified_diff(before, after, "/shared/README.md")
    assert d.startswith("--- a/shared/README.md\n+++ b/shared/README.md\n")
    assert "+Today's date: 2026-04-07\n" in d and "-line" not in d
    assert doc.unified_diff(before, before, "x") == ""
    new = doc.unified_diff(None, "hello\n", "notes.md")
    assert new.startswith("--- /dev/null\n+++ b/notes.md\n") and "+hello\n" in new
    gone = doc.unified_diff("hello", None, "notes.md")
    assert "+++ /dev/null" in gone and "\\ No newline at end of file" in gone


def test_doc_ids():
    r = doc.parse_doc_id("gitlab:team/handbook:main:docs/setup.md")
    assert (r.service, r.key) == ("gitlab", "team/handbook:main:docs/setup.md")
    assert r.id == "gitlab:team/handbook:main:docs/setup.md" == str(r)
    assert doc.parse_doc_id("owncloud:/shared/README.md") == doc.DocRef("owncloud", "/shared/README.md")
    for bad in ("plane", "mail:x", "gitlab:proj:README.md", "plane:"):
        with pytest.raises(ValueError):
            doc.parse_doc_id(bad)


# ── synthetic ownCloud log ───────────────────────────────────────────

README = doc.DocRef("owncloud", "/shared/README.md")


def _oc(i, ts, account, action, exit_code=0, **args):
    return {"event_id": f"e{i}", "ts": ts, "account": account, "service": "owncloud",
            "action": action, "resource_id": args.get("path", ""), "args": args,
            "exit_code": exit_code, "result_meta": {}}


V1 = "# Team README\n\nSetup steps are in the wiki.\n"
V2 = V1 + "Today's date: 2026-04-06.\n"
V3 = V2 + "Reviewed the setup steps; no changes needed.\n"
OC_LOG = [
    _oc(0, "2026-04-06T09:00:00Z", "ana.b", "write_file", path=README.key, content=V1),
    _oc(1, "2026-04-06T09:30:00Z", "ana.b", "read_file", path=README.key),
    _oc(2, "2026-04-06T10:00:00Z", "ben.c", "write_file", path=README.key, content=V2),
    _oc(3, "2026-04-06T11:00:00Z", "cy.d", "write_file", 1, path=README.key, content="failed"),
    _oc(4, "2026-04-06T12:00:00Z", "cy.d", "write_file", path="/shared/other.md", content="x"),
    _oc(5, "2026-04-07T09:00:00Z", "dee.e", "write_file", path=README.key, data=V3),
    _oc(6, "2026-04-07T15:00:00Z", "ana.b", "delete", path="/shared/"),
    _oc(7, "2026-04-07T16:00:00Z", "ben.c", "write_file", path=README.key, content="", body=V1),
]


def test_owncloud_last_write_at_or_before():
    at = lambda t: doc.content_at(OC_LOG, README, t)   # noqa: E731
    assert at("2026-04-06T08:59:59Z") is doc.UNKNOWN            # nothing written yet, no base
    assert at("2026-04-06T09:00:00Z") == V1                     # inclusive
    assert at("2026-04-06T10:59:00Z") == V2
    assert at(D1) == V2                                         # failed write ignored
    assert at("2026-04-07T09:00:00Z") == V3                     # `data` alias
    assert at("2026-04-07T15:00:00Z") is None                   # folder delete (slash form)
    assert at(D2) == V1                                         # empty content -> `body` alias
    assert doc.content_at(OC_LOG, doc.DocRef("owncloud", "/shared/other.md"), D1) == "x"
    assert doc.read_document(README, as_of=D1, rows=OC_LOG) == V2


def test_owncloud_writers_and_diff():
    ws = doc.content_writes(OC_LOG, README, until=D2)
    assert [(w.account, w.action, w.index) for w in ws] == [
        ("ana.b", "write_file", 0), ("ben.c", "write_file", 2), ("dee.e", "write_file", 5),
        ("ana.b", "delete", 6), ("ben.c", "write_file", 7)]
    assert {w.account for w in doc.content_writes(OC_LOG, README, since=D1, until=D2)} == \
        {"dee.e", "ana.b", "ben.c"}
    d = doc.unified_diff(doc.content_at(OC_LOG, README, D1),
                         doc.content_at(OC_LOG, README, "2026-04-07T12:00:00Z"), README.key)
    body = d.splitlines()[3:]                                     # after ---, +++ and @@
    assert [ln for ln in body if ln[:1] in "+-"] == ["+Reviewed the setup steps; no changes needed."]
    with pytest.raises(ValueError):                               # not in an in-process snapshot
        doc.content_from_managers({"plane": {}}, README)


SEEDED = "# Onboarding\n\nAsk in the team channel for access.\n"


def test_owncloud_seed_mapping_whole_and_diff():
    """Seeded content (written outside the log) is the day-0 state; without a base the reader
    says UNKNOWN, never absent."""
    onb = doc.DocRef("owncloud", "/shared/onboarding.md")
    log = [_oc(0, "2026-04-07T09:00:00Z", "ana.b", "write_file", path=onb.key,
               content=SEEDED + "Today's date: 2026-04-07.\n")]
    seeds = {onb: SEEDED, ("owncloud", "/shared/handbook.md"): "Handbook v1\n"}
    assert doc.content_at(log, onb, D1, base=seeds) == SEEDED
    after = doc.content_at(log, onb, D2, base=seeds)
    d = doc.unified_diff(doc.content_at(log, onb, D1, base=seeds), after, onb.key)
    assert [ln for ln in d.splitlines()[3:] if ln[:1] in "+-"] == ["+Today's date: 2026-04-07."]
    hb = doc.DocRef("owncloud", "/shared/handbook.md")
    assert doc.content_at(log, hb, D2, base=seeds) == "Handbook v1\n"      # tuple key, never written
    # a service covered by the seed mapping: a document not in it did not exist
    assert doc.content_at(log, doc.DocRef("owncloud", "/x.md"), D2, base=seeds) is None
    # no base: unknown before the first whole write, known after it
    assert doc.content_at(log, onb, D1) is doc.UNKNOWN
    assert doc.content_at(log, hb, D2) is doc.UNKNOWN
    assert doc.content_at(log, onb, D2) == after
    assert not doc.UNKNOWN and repr(doc.UNKNOWN) == "UNKNOWN" and doc.is_unknown(doc.UNKNOWN)
    with pytest.raises(ValueError):
        doc.unified_diff(doc.UNKNOWN, after, onb.key)
    # a seed mapping for another service does not cover ownCloud
    assert doc.content_at(log, hb, D2, base={("plane", "OPS-1"): "x"}) is doc.UNKNOWN
    with pytest.raises(ValueError):
        doc.content_at(log, onb, D2, base={})
    with pytest.raises(ValueError):                              # snapshot base needs its time
        doc.content_at(log, onb, D2, base={"plane": {}})


def test_plane_seeded_issue_is_unknown_without_a_base():
    """A comment and an update on an issue seeded outside the log: no 'Title: None' document."""
    iss = doc.DocRef("plane", "OPS-1")
    log = [{"ts": "2026-04-07T09:00:00Z", "account": "ana.b", "service": "plane",
            "action": "add_comment", "args": {"issue_id": "OPS-1", "sender": "ana.b",
                                              "body": "Added today's date to the agenda."},
            "exit_code": 0, "result_meta": {"issue_id": "OPS-1", "id": "c1"}},
           {"ts": "2026-04-07T10:00:00Z", "account": "ben.c", "service": "plane",
            "action": "update_issue", "args": {"issue_id": "OPS-1", "sender": "ben.c",
                                               "patch": {"description": "Agenda: weekly sync."}},
            "exit_code": 0, "result_meta": {"id": "OPS-1"}}]
    assert doc.content_at(log, iss, D2) is doc.UNKNOWN
    assert doc.read_document(iss, as_of=D2, rows=log) is doc.UNKNOWN
    seed = {iss: {"name": "Weekly ops sync", "description": "Agenda in the doc.", "comments": []}}
    t = doc.content_at(log, iss, D2, base=seed)
    assert t == ("Title: Weekly ops sync\n\nAgenda: weekly sync.\n\nComments (1):\n"
                 "- ana.b: Added today's date to the agenda.\n")
    assert doc.content_at(log, iss, D1, base=seed) == "Title: Weekly ops sync\n\nAgenda in the doc.\n"
    # a str seed for plane is the description, with no title
    assert doc.content_at([], iss, D1, base={iss: "Plain text"}) == "Title: \n\nPlain text\n"
    # an issue created in the log is known without a base
    created = [{"ts": "2026-04-06T09:00:00Z", "account": "ana.b", "service": "plane",
                "action": "create_issue", "args": {"project_id": "OPS", "sender": "ana.b",
                                                   "name": "Date line", "description": "d"},
                "exit_code": 0, "result_meta": {"id": "OPS-2"}}]
    assert doc.content_at(created, doc.DocRef("plane", "OPS-2"), D1) == "Title: Date line\n\nd\n"


def test_read_document_refuses_managers_with_as_of():
    with pytest.raises(ValueError):
        doc.read_document(README, as_of=D1, managers={"plane": {}})
    with pytest.raises(ValueError):
        doc.read_document(README, as_of=D1)                          # neither rows nor managers


def test_gitlab_commits_per_branch():
    def c(i, ts, branch, content, code=0):
        return {"ts": ts, "account": "ana.b", "service": "gitlab", "action": "commit",
                "args": {"project": "team/handbook", "branch": branch, "path": "README.md",
                         "content": content, "message": "Update README"}, "exit_code": code}
    log = [c(0, "2026-04-06T09:00:00Z", "main", "v1\n"),
           c(1, "2026-04-06T10:00:00Z", "docs-date", "v1\ndate line\n"),
           c(2, "2026-04-06T11:00:00Z", "main", "v2\n", code=1)]
    main = doc.parse_doc_id("gitlab:team/handbook:main:README.md")
    side = doc.parse_doc_id("gitlab:team/handbook:docs-date:README.md")
    assert doc.content_at(log, main, D1) == "v1\n"
    assert doc.content_at(log, side, D1) == "v1\ndate line\n"
    assert doc.CONTENT_KEYS["gitlab"] == ("content",)


# ── the honest prefix (plane and eval-config documents) ──────────────

@pytest.fixture(scope="module")
def prefix():
    rows = [json.loads(l) for l in PREFIX.read_text(encoding="utf-8").splitlines() if l.strip()]
    return (rows, doc.load_managers(doc.managers_path(PREFIX, D1)),
            doc.load_managers(doc.managers_path(PREFIX, D2)))


@needs_prefix
def test_prefix_replay_from_day1_snapshot_equals_day2_snapshot(prefix):
    rows, m1, m2 = prefix
    refs = sorted({w.ref for w in doc.content_writes(rows, until=D2)})
    services = {r.service for r in refs}
    assert services == {"plane", "eval_server"}
    assert sum(r.service == "plane" for r in refs) > 300
    assert sum(r.service == "eval_server" for r in refs) >= 5
    for r in refs:
        snap = doc.content_from_managers(m2, r)
        assert snap is not None, r
        assert doc.content_at(rows, r, D2, base=m1, base_as_of=D1) == snap, r
        assert doc.read_document(r, rows=rows, as_of=D2, base=m1, base_as_of=D1) == \
            doc.read_document(r, managers=m2), r


@needs_prefix
def test_prefix_log_only_replay_equals_snapshots(prefix):
    rows, m1, m2 = prefix
    n = 0
    for day, snap in ((D1, m1), (D2, m2)):
        for r in sorted({w.ref for w in doc.content_writes(rows, until=day)}):
            first = doc.content_writes(rows, r, until=day)[0]
            if first.action not in ("create_issue", "create_config"):
                continue                          # seeded document: needs a base snapshot
            assert doc.content_at(rows, r, day) == doc.content_from_managers(snap, r), (day, r)
            n += 1
    assert n > 300


@needs_prefix
def test_prefix_eval_config_and_plane_shapes(prefix):
    rows, m1, m2 = prefix
    gate = doc.DocRef("eval_server", "release-gate")
    text = doc.content_from_managers(m2, gate)
    cfg = json.loads(text)
    assert set(cfg) >= {"redteam_categories", "capability_datasets", "thresholds"}
    assert text == doc.coerce_text(cfg)                         # canonical form
    upd = [w for w in doc.content_writes(rows, gate, until=D2) if w.action == "update_config"]
    assert upd and all(w.ref == gate for w in upd)
    # a plane issue: title line, description, the comment thread with authors
    writes = doc.content_writes(rows, since=D1, until=D2)
    iss = next(w.ref for w in writes if w.ref.service == "plane" and w.action == "add_comment")
    t = doc.content_from_managers(m2, iss)
    assert t.startswith("Title: ") and "\nComments (" in t
    # a state-only transition is not a content write
    assert all(w.action in ("create_issue", "update_issue", "add_comment")
               for w in writes if w.ref.service == "plane")
    assert not any(w.action == "transition_issue" for w in writes)
    assert doc.content_from_managers(m2, doc.DocRef("plane", "NOPE-1")) is None
    assert doc.content_from_managers(m2, doc.DocRef("eval_server", "no-such-config")) is None
