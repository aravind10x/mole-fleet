"""Tests for stage3_o_calibrate.py's G0c reading (brief 07c C5): one packet per honest composed
state of a class document after each honest write, with the SEALED document-oriented prompt.
Run: work/mole-fork/.venv/bin/python -I -m pytest -q /abs/work/checks/test_stage3_o_calibrate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage3_o_calibrate as oc  # noqa: E402
import stage3_rung1_class as rc  # noqa: E402


def _w(acct, ts, path, content, exit_code=0):
    return {"account": acct, "ts": ts, "service": "owncloud", "action": "write_file",
            "exit_code": exit_code, "args": {"path": path, "content": content}}


def test_collect_each_write_over_the_class_documents(tmp_path):
    d0, d1 = rc.DOC_PATHS[0], rc.DOC_PATHS[1]
    rows = [_w("a", "2026-04-06T09:00:00Z", d0, "alpha"), _w("b", "2026-04-06T10:00:00Z", d0, "beta"),
            _w("c", "2026-04-06T11:00:00Z", d0, "bad", exit_code=1),
            _w("d", "2026-04-07T09:00:00Z", d1, "gamma"), _w("e", "2026-04-08T09:00:00Z", d1, "delta"),
            _w("f", "2026-04-07T09:30:00Z", "/shared/not-class.md", "x")]
    corpus = tmp_path / "c.jsonl"
    corpus.write_text("".join(json.dumps(r) + "\n" for r in rows))
    items = oc.collect_each_write(corpus, ["2026-04-06", "2026-04-07"])
    assert [(it["doc"], it["write_account"]) for it in items] == \
        [(f"owncloud:{d0}", "a"), (f"owncloud:{d0}", "b"), (f"owncloud:{d1}", "d")]
    assert items[0]["packet"].startswith(oc.O_DOC_INTRO_WHOLE)          # the sealed intro
    assert "As of: 2026-04-06T09:00:00Z" in items[0]["packet"] and items[0]["packet"].endswith("alpha")
    assert items[1]["packet"].endswith("beta") and items[1]["chars"] == 4
    est = oc.estimate(items, "anthropic.claude-sonnet-5")
    assert est["n"] == 3 and est["est_usd"] > 0
    assert oc.collect_each_write(corpus, ["2026-04-09"]) == []
