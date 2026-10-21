"""Line-level edit tools for ownCloud (brief 07e E1).

E1: `append_to_file(path, text)` and `replace_in_file(path, find, replace)` are read-modify-write
against the live ownCloud; each is ONE audit event whose recorded args carry the full resulting
content under the key `write_file` uses (`content`) plus `edit` metadata, so the document reader,
the P and O packet renderers and the Stage 3 scripts see the document as they see a whole write.

The pyocclient client is replaced by an in-memory fake (a dict of path -> bytes) so the tests
exercise the real manager, the real audit wrapper and the real reader together.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from mole.agent.tools import build_tools_for
from mole.audit import AuditCollector
from mole.oracles import document as doc
from mole.sandbox.base import DryRunSandbox
from mole.state.owncloud.manager import OwnCloudManager


class _MemoryClient:
    """The slice of pyocclient the manager uses, over an in-memory file dict."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}
        self.dirs: set[str] = set()

    def login(self, user, pw):
        pass

    def logout(self):
        pass

    def file_info(self, path):
        if path in self.files or path.rstrip("/") in self.dirs:
            return SimpleNamespace(name=path)
        raise Exception("HTTP error: 404")

    def get_file_contents(self, path):
        if path not in self.files:
            raise Exception("HTTP error: 404")
        return self.files[path]

    def put_file_contents(self, path, blob):
        self.files[path] = bytes(blob)

    def mkdir(self, path):
        self.dirs.add(path.rstrip("/"))

    def delete(self, path):
        p = path.rstrip("/")
        if path in self.files:
            del self.files[path]
            return
        if p in self.dirs:
            self.dirs.discard(p)
            for f in [f for f in self.files if f.startswith(p + "/")]:
                del self.files[f]
            return
        raise Exception("HTTP error: 404")


def _manager() -> tuple[OwnCloudManager, _MemoryClient]:
    mgr = OwnCloudManager(config={"endpoint": "http://oc.test", "user": "u", "password": "p"})
    client = _MemoryClient()
    fake = SimpleNamespace(Client=MagicMock(return_value=client))
    with patch.dict("sys.modules", {"owncloud": fake}):
        asyncio.run(mgr.setup(sandbox=DryRunSandbox(ports={80: 1})))
    return mgr, client


def _audited() -> tuple[OwnCloudManager, _MemoryClient, AuditCollector]:
    mgr, client = _manager()
    col = AuditCollector()
    col.wrap_manager(service_name="owncloud", manager=mgr,
                     account_getter=lambda: ("ana.b", "agent"))
    return mgr, client, col


README = "/shared/infra/training-pipeline/README.md"
SEED = "# Training pipeline\n\n- Runner image tag: `trainer-runner:2026.03.2`\n- Metrics port: 9105\n"


# ── E1: the tools on the manager ─────────────────────────────────────

def test_append_adds_the_text_as_a_new_line_at_the_end():
    mgr, client = _manager()
    client.files[README] = SEED.encode()
    out = asyncio.run(mgr.append_to_file(path=README, text="- Last-reviewed date: 2026-04-06"))
    assert client.files[README].decode() == SEED + "- Last-reviewed date: 2026-04-06\n"
    assert out["before_len"] == len(SEED) and out["after_len"] == len(client.files[README])


def test_append_starts_a_new_line_when_the_file_has_no_trailing_newline():
    mgr, client = _manager()
    client.files["/work/a/notes.md"] = b"first line"
    asyncio.run(mgr.append_to_file(path="/work/a/notes.md", text="second line\n"))
    assert client.files["/work/a/notes.md"] == b"first line\nsecond line\n"


def test_append_creates_a_missing_file_outside_shared():
    mgr, client = _manager()
    asyncio.run(mgr.append_to_file(path="/work/a/new.md", text="hello"))
    assert client.files["/work/a/new.md"] == b"hello\n"


def test_append_refuses_empty_text():
    mgr, client = _manager()
    client.files[README] = SEED.encode()
    with pytest.raises(ValueError, match="text is empty"):
        asyncio.run(mgr.append_to_file(path=README, text="   "))
    assert client.files[README] == SEED.encode()


def test_replace_changes_the_first_exact_occurrence_only():
    mgr, client = _manager()
    client.files[README] = b"port 9105\nport 9105\n"
    out = asyncio.run(mgr.replace_in_file(path=README, find="port 9105", replace="port 9106"))
    assert client.files[README] == b"port 9106\nport 9105\n"
    assert out["before_len"] == 20 and out["after_len"] == 20


def test_replace_errors_naming_the_path_when_find_is_absent():
    mgr, client = _manager()
    client.files[README] = SEED.encode()
    with pytest.raises(ValueError, match=r"not found in /shared/infra/training-pipeline/README.md"):
        asyncio.run(mgr.replace_in_file(path=README, find="no such text", replace="x"))
    assert client.files[README] == SEED.encode()


def test_replace_errors_when_the_file_is_missing():
    mgr, _client = _manager()
    with pytest.raises(ValueError, match="/work/a/missing.md"):
        asyncio.run(mgr.replace_in_file(path="/work/a/missing.md", find="a", replace="b"))


# ── E1: the audit event ──────────────────────────────────────────────

def test_append_is_one_audit_event_carrying_the_full_content_and_edit_metadata():
    mgr, client, col = _audited()
    client.files[README] = SEED.encode()
    asyncio.run(mgr.append_to_file(path=README, text="- Last-reviewed date: 2026-04-06"))
    # the parent mkdir is the audited call write_file has always made before a put; the
    # internal read is NOT an event (it goes through the raw client)
    assert [e.action for e in col.events] == ["mkdir", "append_to_file"]
    e = col.events[1]
    assert e.exit_code == 0 and e.resource_id == README
    assert e.args["path"] == README and e.args["text"] == "- Last-reviewed date: 2026-04-06"
    assert e.args["content"] == client.files[README].decode()
    assert e.args["edit"] == {"op": "append", "text": "- Last-reviewed date: 2026-04-06",
                              "before_len": len(SEED), "after_len": len(client.files[README])}
    from mole.audit.schema import _stable_hash
    assert e.args_hash == _stable_hash(e.args)                        # the hash covers the amended args


def test_replace_audit_event_carries_find_replace_and_the_full_content():
    mgr, client, col = _audited()
    client.files[README] = SEED.encode()
    asyncio.run(mgr.replace_in_file(path=README, find="Metrics port: 9105", replace="Metrics port: 9106"))
    e = col.events[-1]
    assert e.action == "replace_in_file" and e.exit_code == 0
    assert e.args["content"] == SEED.replace("9105", "9106")
    assert e.args["edit"] == {"op": "replace", "find": "Metrics port: 9105", "replace": "Metrics port: 9106",
                              "before_len": len(SEED), "after_len": len(SEED)}


def test_a_failed_replace_is_a_failed_event_without_content():
    mgr, client, col = _audited()
    client.files[README] = SEED.encode()
    with pytest.raises(ValueError):
        asyncio.run(mgr.replace_in_file(path=README, find="absent", replace="x"))
    e = col.events[0]
    assert e.action == "replace_in_file" and e.exit_code == 1 and "not found" in e.error
    assert "content" not in e.args


def test_whole_write_audit_row_is_unchanged():
    mgr, client, col = _audited()
    asyncio.run(mgr.write_file(path="/work/a/x.md", content="hello"))
    assert [e.action for e in col.events] == ["mkdir", "write_file"]     # as before E1
    e = col.events[1]
    assert e.args == {"path": "/work/a/x.md", "content": "hello"}


# ── E1: the tool descriptions the accounts see ───────────────────────

def _catalog() -> dict[str, str]:
    mgr, _client = _manager()
    ctx = SimpleNamespace(_managers={"owncloud": mgr})
    tools, _dispatch = build_tools_for(ctx)
    return {t.name: t.description for t in tools}


def test_edit_tools_are_in_the_catalog_and_point_at_line_level_changes():
    cat = _catalog()
    assert "owncloud.append_to_file" in cat and "owncloud.replace_in_file" in cat
    assert "add a line" in cat["owncloud.append_to_file"].lower()
    assert "one line" in cat["owncloud.replace_in_file"].lower() or "one value" in cat["owncloud.replace_in_file"].lower()
    assert "append_to_file(path=" in cat["owncloud.append_to_file"]
    assert "replace_in_file(path=" in cat["owncloud.replace_in_file"]


def test_the_three_descriptions_are_not_truncated_so_the_example_shows():
    cat = _catalog()
    for name in ("owncloud.write_file", "owncloud.append_to_file", "owncloud.replace_in_file"):
        assert len(cat[name]) < 600 and not cat[name].endswith("…"), name


def test_write_file_description_reserves_it_for_creating_or_replacing_whole():
    cat = _catalog()
    d = cat["owncloud.write_file"].lower()
    assert "whole" in d or "entire" in d
    assert "append_to_file" in d and "replace_in_file" in d


# ── E1: the reader ───────────────────────────────────────────────────

def test_reader_reconstructs_a_document_through_a_mix_of_edits_and_whole_writes():
    mgr, client, col = _audited()
    ref = doc.DocRef("owncloud", README)
    asyncio.run(mgr.write_file(path=README, content=SEED))
    asyncio.run(mgr.append_to_file(path=README, text="- Artifact bucket name: `b1`"))
    asyncio.run(mgr.replace_in_file(path=README, find="9105", replace="9106"))
    asyncio.run(mgr.append_to_file(path=README, text="- On-call contact: #platform-oncall"))
    asyncio.run(mgr.write_file(path=README, content="# Rewritten\n"))
    asyncio.run(mgr.replace_in_file(path=README, find="Rewritten", replace="Rewritten twice"))
    rows = [e.to_dict() if hasattr(e, "to_dict") else e.__dict__ for e in col.events]
    live = client.files[README].decode()
    assert doc.content_at(rows, ref, None) == live == "# Rewritten twice\n"
    # and at an earlier time: after the third content write (the replace), before the rewrite
    for i, r in enumerate(rows):
        r["ts"] = f"2026-04-06T{10 + i:02d}:00:00Z"
    writes_so_far = [r for r in rows if r["action"] != "mkdir"]
    as_of = writes_so_far[2]["ts"]
    assert doc.content_at(rows, ref, as_of) == SEED.replace("9105", "9106") + "- Artifact bucket name: `b1`\n"
    writes = doc.content_writes(rows, ref)
    assert [w.action for w in writes] == ["write_file", "append_to_file", "replace_in_file",
                                          "append_to_file", "write_file", "replace_in_file"]


def test_reader_treats_an_edit_row_as_a_whole_content_write():
    """A log that starts with an edit (the seed is outside the log) is KNOWN from that row on,
    because the row carries the full resulting content."""
    ref = doc.DocRef("owncloud", README)
    rows = [{"ts": "2026-04-06T09:00:00Z", "account": "ana.b", "service": "owncloud",
             "action": "append_to_file", "exit_code": 0, "result_meta": {},
             "args": {"path": README, "text": "x", "content": SEED + "x\n",
                      "edit": {"op": "append", "text": "x", "before_len": len(SEED), "after_len": len(SEED) + 2}}}]
    assert doc.content_at(rows, ref, None) == SEED + "x\n"
    assert doc.is_unknown(doc.content_at(rows, ref, "2026-04-06T08:00:00Z"))


# ── E1: the classical monitors' export tables count an edit as a file write ──

def test_rollup_and_export_tables_count_edit_tools_as_file_writes():
    import importlib
    rollup = importlib.import_module("mole.audit.rollup")
    from mole.audit.cert_export import _ACTIVITY_BY_ACTION, _SERVICE_ACTION_TO_CSV
    from mole.audit.facade_export import _ACTION_KIND
    for action in ("append_to_file", "replace_in_file"):
        assert _ACTION_KIND[("owncloud", action)] == ("file_write", "write")
        assert _SERVICE_ACTION_TO_CSV[("owncloud", action)] == "file"
        assert _ACTIVITY_BY_ACTION[("owncloud", action)] == "Write"
    assert "append_to_file" in rollup._FILE_WRITE_ACTIONS and "replace_in_file" in rollup._FILE_WRITE_ACTIONS
