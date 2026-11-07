#!/usr/bin/env python3
"""B1-all (pre-registration v1.2 §3: "every item fed before the edit, beside B1"; confirmed by Aravind on 7 Nov through
the coordinator's gate amendment). Beside B1; never in the verdict.

Built on the committed renderers (`stage3_phase_b_grounded.py`, imported unchanged, its hash the one v1.2 commits): the
packet is B0 (`stage3_views.o_packet`) with one header block after the "To:" line, the same title line as every grounded
arm, and one line per edit: "- <timestamp>; tasks fed before this edit, oldest first: <t1> | <t2> | ...", each task
scrubbed exactly as B1's (no account named), or "- <timestamp>; no task in force" when none was fed before the edit.
The last listed task is B1's task in force (checked: `last_is_in_force`).
"""
from __future__ import annotations

import hashlib
from typing import Iterable, Mapping, Sequence

import stage3_phase_b_grounded as g
import stage3_views as sv
from judge_client import PACKET_CAP_CHARS

ARM = "B1all"
VERSION = "phase-b-b1all/v1"
LEAD = "; tasks fed before this edit, oldest first: "
SEP = " | "


def fed_before(feeds: Mapping[str, Sequence[g.TaskInfo]], e: g.Edit) -> list[g.TaskInfo]:
    """Every agenda item fed before the edit's position (the edit's key is session id | segment)."""
    tid, s = e.key.rsplit("|", 1)
    return list(feeds.get(tid) or [])[: int(s)]


def last_is_in_force(feeds: Mapping[str, Sequence[g.TaskInfo]], e: g.Edit) -> bool:
    items = fed_before(feeds, e)
    return (items[-1] if items else None) == e.task


def suffix(e: g.Edit, feeds: Mapping[str, Sequence[g.TaskInfo]], roster: Iterable[str] = ()) -> str:
    items = fed_before(feeds, e)
    if not items:
        return f"; {g.NO_TASK}"
    names = tuple(set(roster) | {e.account})
    return LEAD + SEP.join(g.scrub(t.text, names) for t in items)


def packet(path: str, frm: str, to: str, diff_text: str, edits: Sequence[g.Edit], feeds: Mapping[str, Sequence[g.TaskInfo]],
           roster: Iterable[str] = (), cap: int = PACKET_CAP_CHARS) -> dict:
    b0, trunc = sv.o_packet("O_diff", path, diff_text, frm, to, cap)
    head = g.sealed_head(path, frm, to)
    if not b0.startswith(head):
        raise AssertionError("the sealed packet's head changed")
    roster = tuple(roster)
    lines = [g.HEADER_TITLE.format(n=len(edits))] + [f"- {e.ts}{suffix(e, feeds, roster)}" for e in edits]
    pk = head + "".join(ln + "\n" for ln in lines) + b0[len(head):]
    return {"packet": pk, "truncated": bool(trunc), "over_cap": len(pk) > cap, "chars": len(pk),
            "sha256": hashlib.sha256(pk.encode("utf-8")).hexdigest()}
