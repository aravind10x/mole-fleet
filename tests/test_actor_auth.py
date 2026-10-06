"""Actor authentication at the tool dispatcher (mole/agent/tools.py).

Identity params (account/user/sender/actor/from_user) come from the session;
an explicit different value is rejected as an identity spoof, audited, and the
manager is never invoked. Target-param exemptions pass through untouched.
"""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from mole.agent.tools import build_tools_for
from mole.audit.collector import AuditCollector
from mole.generator.account_context import set_account
from mole.llm import ToolCall


class _Svc:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def submit(self, *, account: str | None = None, item: str = "") -> dict:
        """Submit an item as the acting account."""
        self.calls.append({"account": account, "item": item})
        return {"account": account, "item": item}


class _Org:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def lookup_person(self, *, account: str | None = None, id: str | None = None) -> dict:
        """Look up a colleague."""
        self.calls.append({"account": account})
        return {"id": account}


def _ctx(**managers) -> object:
    ctx = SimpleNamespace()
    ctx._managers = managers
    for name, mgr in managers.items():
        setattr(ctx, name, mgr)
    return ctx


@pytest.fixture(autouse=True)
def _alice_session():
    set_account("alice", "agent")
    yield
    set_account("system", "system")   # don't leak into other tests


def _call(dispatcher, name, args):
    return asyncio.run(dispatcher(ToolCall(id="t", name=name, arguments=args)))


def test_spoofed_account_rejected_and_audited():
    svc = _Svc()
    ctx = _ctx(svc=svc)
    ctx.audit = AuditCollector()
    _, dispatcher = build_tools_for(ctx)
    r = _call(dispatcher, "svc.submit", {"account": "bob", "item": "x"})
    assert r.is_error is True
    assert "you are 'alice'" in r.content and "'account'" in r.content
    assert svc.calls == []                         # manager NOT invoked
    assert len(ctx.audit.events) == 1
    ev = ctx.audit.events[0]
    assert ev.exit_code == 1
    assert ev.error.startswith("identity_spoof_rejected")
    assert ev.account == "alice" and ev.account_kind == "agent"
    assert ev.service == "svc" and ev.action == "submit"
    assert ev.resource_id == "bob"
    assert ev.args == {"account": "bob", "item": "x"}


def test_spoof_rejected_without_audit_attached():
    svc = _Svc()
    _, dispatcher = build_tools_for(_ctx(svc=svc))
    r = _call(dispatcher, "svc.submit", {"account": "bob", "item": "x"})
    assert r.is_error is True and svc.calls == []


def test_omitted_actor_is_filled_with_session():
    svc = _Svc()
    _, dispatcher = build_tools_for(_ctx(svc=svc))
    r = _call(dispatcher, "svc.submit", {"item": "x"})
    assert r.is_error is False
    assert json.loads(r.content)["account"] == "alice"


def test_explicit_self_identity_allowed():
    svc = _Svc()
    _, dispatcher = build_tools_for(_ctx(svc=svc))
    r = _call(dispatcher, "svc.submit", {"account": "alice", "item": "x"})
    assert r.is_error is False
    assert svc.calls == [{"account": "alice", "item": "x"}]


def test_lookup_person_target_param_passes_through():
    org = _Org()
    tools, dispatcher = build_tools_for(_ctx(org=org))
    r = _call(dispatcher, "org.lookup_person", {"account": "bob"})
    assert r.is_error is False
    assert org.calls == [{"account": "bob"}]
    # exempt params are not filled either, and not described as actor params
    org.calls.clear()
    _call(dispatcher, "org.lookup_person", {"id": "carol"})
    assert org.calls == [{"account": None}]
    schema = next(t for t in tools if t.name == "org.lookup_person")
    assert "do not pass" not in schema.parameters["properties"]["account"].get("description", "")


def test_actor_schema_description():
    tools, _ = build_tools_for(_ctx(svc=_Svc()))
    schema = next(t for t in tools if t.name == "svc.submit")
    assert schema.parameters["properties"]["account"]["description"] == (
        "the acting user; set automatically from your session — do not pass")
