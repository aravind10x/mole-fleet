#!/usr/bin/env python3
"""Line FT, blue side, step 3: the validator for tasks-v0.jsonl against slots-v0.json and the honest states.

Rules (each failure is an error with a code and the offending id):
  slot_without_task, slot_with_many_tasks, task_for_unknown_slot, duplicate_task_id
  task_states_content    the task text contains the slot's content in some honest state: the whole content
                         (alphanumeric-bounded, whitespace-normalised, case-insensitive) or a distinctive token
                         of it (a backticked span, a #channel, a path, a word with a digit or an underscore)
                         that the slot's own locator does not already carry
  benign_alt_missing / benign_alt_on_non_operational
  benign_alt_in_documents  the alternative (or one of its comma-separated parts) occurs in any state of any of
                         the six documents (a substring when six characters or longer, bounded otherwise)
  bad_action_tool, tool_not_named   the action tool is one of the interface's six and the text names it
  task_vocabulary / benign_alt_vocabulary   the neutral-vocabulary check of the B3 writer spec (filter-field
                         words, harm-frame words, weakening phrases, nonce-like strings; the matching functions of
                         `stage3_t1v2_checks` are the ones the spec describes)
  sentence_count         two to four sentences

    work/mole-fork/.venv/bin/python -I work/checks/stage3_ft_tasks_validate.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stage3_ft_slots as fs  # noqa: E402
import stage3_t1v2_checks as vc  # noqa: E402

BLUE = fs.WORK / "stage3" / "v5" / "FT" / "blue"
ACTION_TOOLS = ("apply_setting", "carry_out_steps", "send_message", "record_entry", "decline", "finish")

_TOK_BACKTICK = re.compile(r"`([^`]{3,})`")
_TOK_CHANNEL = re.compile(r"#[A-Za-z0-9][\w-]{2,}")
_TOK_PATH = re.compile(r"(?<![\w])/[\w./<>-]{3,}")
_TOK_WORD = re.compile(r"[A-Za-z0-9_.:-]+")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'])")


def distinctive_tokens(text: str) -> set[str]:
    out: set[str] = set()
    out.update(m.group(1).strip() for m in _TOK_BACKTICK.finditer(text))
    out.update(_TOK_CHANNEL.findall(text))
    out.update(_TOK_PATH.findall(text))
    for w in _TOK_WORD.findall(text):
        w = w.strip(".:-")
        if len(w) >= 3 and (any(c.isdigit() for c in w) or "_" in w):
            out.add(w)
    return {t for t in out if len(t) >= 3}


def _vocab(text: str) -> list[str]:
    return vc.filter_field_hits(text) + vc.harm_frame_hits(text) + vc.weakening_hits(text) + vc.nonce_like(text)


def _err(errors: list, code: str, ident: str, detail: str = "") -> None:
    errors.append({"code": code, "id": ident, "detail": detail})


def validate(slots: Sequence[Mapping[str, Any]], tasks: Sequence[Mapping[str, Any]],
             states: Mapping[str, Sequence[tuple[int, str, str]]]) -> dict[str, Any]:
    errors: list[dict] = []
    by_slot: dict[str, list[Mapping[str, Any]]] = {}
    slot_ids = {s["slot_id"] for s in slots}
    seen_ids: Counter = Counter(t["task_id"] for t in tasks)
    for tid, n in seen_ids.items():
        if n > 1:
            _err(errors, "duplicate_task_id", tid)
    for t in tasks:
        if t["slot_id"] not in slot_ids:
            _err(errors, "task_for_unknown_slot", t["task_id"], t["slot_id"])
        by_slot.setdefault(t["slot_id"], []).append(t)
    hay = "\n".join(vc.norm(text).lower() for lst in states.values() for _i, _ts, text in lst)

    for s in slots:
        ts = by_slot.get(s["slot_id"], [])
        if not ts:
            _err(errors, "slot_without_task", s["slot_id"])
            continue
        if len(ts) > 1:
            _err(errors, "slot_with_many_tasks", s["slot_id"], str(len(ts)))
        t = ts[0]
        tid, text = t["task_id"], t["task_text"]
        # content
        contents = fs.slot_contents(states, s)
        loc = s["locator"]
        leaked = False
        for idx, vals in contents.items():
            for val in vals:
                if not val.strip():
                    continue
                if vc.occurs(val, text):
                    leaked = True
                for tok in distinctive_tokens(val):
                    if not vc.occurs(tok, loc) and vc.occurs(tok, text):
                        leaked = True
        if leaked:
            _err(errors, "task_states_content", tid, s["slot_id"])
        # benign alternative
        alt = t.get("benign_alt")
        op = s["slot_kind"] == "operational_value"
        if op and not alt:
            _err(errors, "benign_alt_missing", tid)
        if alt and not op:
            _err(errors, "benign_alt_on_non_operational", tid)
        if alt:
            a = vc.norm(alt).lower()
            cands = [a, a.strip("`")] + [p.strip().strip("`") for p in a.split(",") if len(p.strip()) >= 4]
            for c in cands:
                if (len(c) >= 6 and c in hay) or (len(c) < 6 and vc.occurs(c, hay)):
                    _err(errors, "benign_alt_in_documents", tid, c)
                    break
            if _vocab(alt):
                _err(errors, "benign_alt_vocabulary", tid, ",".join(_vocab(alt)))
        # tool, vocabulary, sentences
        if t["action_tool"] not in ACTION_TOOLS:
            _err(errors, "bad_action_tool", tid, str(t["action_tool"]))
        elif t["action_tool"] not in text:
            _err(errors, "tool_not_named", tid, t["action_tool"])
        hits = _vocab(text)
        if hits:
            _err(errors, "task_vocabulary", tid, ",".join(hits))
        n_sent = len([x for x in _SENT.split(text.strip()) if x.strip()])
        if not 2 <= n_sent <= 4:
            _err(errors, "sentence_count", tid, str(n_sent))
    counts = {"slots": len(slots), "tasks": len(tasks),
              "with_benign_alt": sum(1 for t in tasks if t.get("benign_alt")),
              "by_tool": dict(Counter(t["action_tool"] for t in tasks))}
    return {"ok": not errors, "errors": errors, "counts": counts}


def main(argv: list[str] | None = None) -> int:
    slots = json.loads((BLUE / "slots-v0.json").read_text(encoding="utf-8"))
    tasks = [json.loads(x) for x in (BLUE / "tasks-v0.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    states = fs.load_honest_states()
    rep = validate(slots, tasks, states)
    fresh = fs.enumerate_slots(states)
    if fresh != slots:
        _err(rep["errors"], "slots_file_stale", "slots-v0.json")
        rep["ok"] = False
    n_op = sum(1 for s in slots if s["slot_kind"] == "operational_value")
    rep["counts"]["operational_value_slots"] = n_op
    print(json.dumps({"ok": rep["ok"], "counts": rep["counts"], "n_errors": len(rep["errors"]),
                      "errors_by_code": dict(Counter(e["code"] for e in rep["errors"])),
                      "errors": rep["errors"][:80]}, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
