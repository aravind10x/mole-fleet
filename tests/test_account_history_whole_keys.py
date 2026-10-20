"""The renderer's per-argument cap can be lifted for one document content key
(mole/monitors/release/account_history.py: whole_key_set, _capped_args, render_event).

Stage 3 design section 5: P (the per-account packet) and the composed-document O view must
see the same document text, so a scorer registers the target document's content key and
that key is rendered whole; every other key, and the default call, keep the 4,000-char cap.
Fixture content is a routine placeholder edit.
"""
from __future__ import annotations

import json

import pytest

from mole.monitors.release import account_history as ah

LINE = "Add one line noting today's date to the shared README.\n"
BIG = (LINE * (10_000 // len(LINE) + 1))[:10_000]


def _row(content: str = BIG, **extra) -> dict:
    return {"ts": "2026-04-07T10:00:00Z", "account": "a", "service": "owncloud",
            "action": "write_file", "resource_id": "/shared/README.md", "exit_code": 0,
            "args": {"path": "/shared/README.md", "content": content, **extra}}


def _rendered_content(line: str) -> str:
    """The `content` value as it appears in the rendered JSON args."""
    args_json = line.split("  ", 3)[3].rsplit("  -> ", 1)[0]
    return json.loads(args_json)["content"]


def test_registered_key_is_rendered_whole():
    assert len(BIG) == 10_000
    line = ah.render_event(_row(), "a", whole_keys=["content"])
    assert _rendered_content(line) == BIG
    assert "chars]" not in line


def test_unregistered_key_is_capped_at_4000():
    line = ah.render_event(_row(), "a")
    got = _rendered_content(line)
    assert got == BIG[: ah.ARG_CAP_CHARS] + f"…[+{10_000 - ah.ARG_CAP_CHARS} chars]"
    # registering a different key does not lift this one
    assert ah.render_event(_row(), "a", whole_keys=["description"]) == line


def test_default_behaviour_unchanged():
    row = _row(reason="r" * 9000)
    assert ah.render_event(row, "a") == ah.render_event(row, "a", whole_keys=None) \
        == ah.render_event(row, "a", whole_keys=())
    assert ah.whole_key_set() == ah.WHOLE_ARG_KEYS == frozenset({"config", "eval_config"})
    assert ah._capped_args(row["args"], "a") == ah._capped_args(row["args"], "a", ())
    # lifting `content` leaves every other key capped
    line = ah.render_event(row, "a", whole_keys=["content"])
    assert "r" * 4000 in line and "r" * 4001 not in line
    # config payloads stay whole with or without registered keys
    cfg = {"redteam_categories": ["x" * 50] * 200}
    row2 = {**_row(), "args": {"config_id": "release-gate", "config": cfg}}
    for wk in (None, ["content"]):
        assert json.dumps(cfg, ensure_ascii=False) in ah.render_event(row2, "a", whole_keys=wk)


def test_whole_key_set_rejects_a_bare_string():
    with pytest.raises(TypeError):
        ah.whole_key_set("content")
    assert ah.whole_key_set(["content", "body"]) == ah.WHOLE_ARG_KEYS | {"content", "body"}
