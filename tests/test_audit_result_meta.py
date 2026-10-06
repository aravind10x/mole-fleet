"""AuditEvent.result_meta + failure-envelope marking in the collector wrapper."""
from __future__ import annotations

import asyncio
import json

from mole.audit.collector import AuditCollector
from mole.audit.schema import AuditEvent


class _Stub:
    async def refuse(self, *, key: str = "") -> dict:
        """Returns a failure envelope."""
        return {"ok": False, "error": "nope"}

    async def run(self, *, name: str = "") -> dict:
        """Returns a job-like record."""
        return {"job_id": "j1", "passed": True, "eval_config": {"big": "ignored"}}

    async def deploy(self) -> dict:
        """Returns a record with a long list."""
        return {"deployment_id": "d1", "approvers": [f"u{i}" for i in range(30)],
                "environment": "prod", "gate": {"x": 1}}

    async def blank_error(self) -> dict:
        """Success record with an empty error string."""
        return {"status": "complete", "error": ""}

    async def listing(self) -> list:
        """Non-dict result."""
        return [{"ok": False}]


def _wrapped():
    audit = AuditCollector()
    stub = _Stub()
    audit.wrap_manager("svc", stub, account_getter=lambda: ("alice", "agent"))
    return audit, stub


def test_failure_envelope_marks_exit_code():
    audit, stub = _wrapped()
    out = asyncio.run(stub.refuse(key="k"))
    assert out == {"ok": False, "error": "nope"}      # result unchanged
    ev = audit.events[-1]
    assert ev.exit_code == 1 and ev.error == "nope"
    assert ev.result_meta == {"ok": False, "error": "nope"}


def test_result_meta_copies_whitelisted_keys_only():
    audit, stub = _wrapped()
    asyncio.run(stub.run(name="x"))
    ev = audit.events[-1]
    assert ev.exit_code == 0
    assert ev.result_meta == {"job_id": "j1", "passed": True}


def test_result_meta_caps_lists():
    audit, stub = _wrapped()
    asyncio.run(stub.deploy())
    ev = audit.events[-1]
    assert ev.result_meta["approvers"] == [f"u{i}" for i in range(20)]
    assert ev.result_meta["deployment_id"] == "d1"
    assert "gate" not in ev.result_meta


def test_empty_error_string_is_not_a_failure():
    audit, stub = _wrapped()
    asyncio.run(stub.blank_error())
    assert audit.events[-1].exit_code == 0


def test_non_dict_result_has_empty_meta():
    audit, stub = _wrapped()
    asyncio.run(stub.listing())
    ev = audit.events[-1]
    assert ev.exit_code == 0 and ev.result_meta == {}


def test_result_meta_round_trips_through_jsonl():
    audit, stub = _wrapped()
    asyncio.run(stub.run())
    row = json.loads(audit.events[-1].to_jsonl())
    assert row["result_meta"] == {"job_id": "j1", "passed": True}
    assert AuditEvent.from_row(row).result_meta == {"job_id": "j1", "passed": True}
