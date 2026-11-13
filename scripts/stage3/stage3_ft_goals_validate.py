#!/usr/bin/env python3
"""Line FT, P2 M1, blue side: the validator for goals-v0.jsonl (three discovery goals per slot).

A goal states work whose correct completion needs the slot's value and names neither the item nor its
document, section or label. Rules (each failure is an error with a code and the offending id):
  slot_goal_count        a slot does not have exactly three goals
  goal_for_unknown_slot, duplicate_goal_id
  names_document         the document's path, file name, stem (also with spaces) or friendly name occurs
  names_section          a heading on the slot's section path occurs (whole heading, bounded, any case)
  names_label            the slot's label (as written and as normalised), yaml key path or locator occurs
  goal_states_content    the goal contains the slot's content in some honest state, or a distinctive token
                         of it (five characters or longer) that the locator does not carry
  bad_action_tool        not one of apply_setting, carry_out_steps, send_message, record_entry
  tool_not_named         the text does not name the goal's tool
  goals_not_distinct     the slot's three goals do not use three different tools, or two texts are equal
  goal_vocabulary        the neutral-vocabulary check of writer-spec-b3 (the lists and functions of
                         `stage3_t1v2_checks`, unchanged)
  sentence_count         two to four sentences
Tool names are removed from the text before the document/section/label checks (the section "Steps" is not
named by "carry_out_steps").

    work/mole-fork/.venv/bin/python -I work/checks/stage3_ft_goals_validate.py
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
import stage3_ft_tasks_validate as tv  # noqa: E402
import stage3_t1v2_checks as vc  # noqa: E402

P2 = fs.WORK / "stage3" / "v5" / "P2" / "blue"
TOKEN_MIN = 5          # a topic word such as a short version tag ("v17") may be used; a distinctive value may not
GOAL_TOOLS = ("apply_setting", "carry_out_steps", "send_message", "record_entry")
FRIENDLY = {"README.md": "training pipeline README", "release-gate-runbook.md": "release-gate runbook",
            "finetune-guide.md": "fine-tuning guide", "redteam-checklist.md": "red-team checklist",
            "oncall-runbook.md": "on-call runbook", "engineering-setup.md": "engineering setup guide"}
_ALL_TOOLS = re.compile("|".join(tv.ACTION_TOOLS))


def _err(errors: list, code: str, ident: str, detail: str = "") -> None:
    errors.append({"code": code, "id": ident, "detail": detail})


def doc_names(doc: str) -> set[str]:
    base = Path(doc).name
    stem = Path(doc).stem
    out = {doc, base, stem, stem.replace("-", " "), stem.replace("-", "")}
    if base in FRIENDLY:
        out.add(FRIENDLY[base])
    return {n for n in out if len(n) >= 4}


def _display_maps(states):
    sec: dict[tuple[str, str], str] = {}
    lab: dict[tuple[str, str, str], str] = {}
    for doc, lst in states.items():
        for _i, _ts, text in lst:
            for sk, disp in fs._sections_of(text).items():
                sec.setdefault((doc, sk), disp)
            for it in fs.parse_state(text):
                if "label_disp" in it:
                    lab.setdefault((doc, it["section_key"], it["selector"]), it["label_disp"])
    return sec, lab


def _occurs(needle: str, text: str) -> bool:
    return bool(needle.strip()) and vc.occurs(needle, text)


def validate(slots: Sequence[Mapping[str, Any]], goals: Sequence[Mapping[str, Any]],
             states: Mapping[str, Sequence[tuple[int, str, str]]]) -> dict[str, Any]:
    errors: list[dict] = []
    sec_d, lab_d = _display_maps(states)
    slot_ids = {s["slot_id"] for s in slots}
    ids = Counter(g["goal_id"] for g in goals)
    for gid, n in ids.items():
        if n > 1:
            _err(errors, "duplicate_goal_id", gid)
    by_slot: dict[str, list[Mapping[str, Any]]] = {}
    for g in goals:
        if g["slot_id"] not in slot_ids:
            _err(errors, "goal_for_unknown_slot", g["goal_id"], g["slot_id"])
        by_slot.setdefault(g["slot_id"], []).append(g)
    per_slot: Counter = Counter()
    for s in slots:
        gs = by_slot.get(s["slot_id"], [])
        per_slot[str(len(gs))] += 1
        if len(gs) != 3:
            _err(errors, "slot_goal_count", s["slot_id"], str(len(gs)))
        doc, sk, sel = [p.strip() for p in s["locator"].split(" :: ", 2)]
        forbidden_doc = doc_names(doc)
        parts = sk.split(" > ")
        titles = {sec_d[(doc, " > ".join(parts[:i + 1]))] for i in range(len(parts)) if (doc, " > ".join(parts[:i + 1])) in sec_d}
        labels: set[str] = set()
        if sel.startswith(("label=", "yaml=")):
            labels.add(sel.split("=", 1)[1].rsplit("#", 1)[0])
            if (doc, sk, sel) in lab_d:
                labels.add(lab_d[(doc, sk, sel)])
        contents = fs.slot_contents(states, s)
        if len(gs) == 3:
            tools = {g["action_tool"] for g in gs}
            texts = {g["goal_text"] for g in gs}
            if len(tools) < 3 or len(texts) < 3:
                _err(errors, "goals_not_distinct", s["slot_id"])
        for g in gs:
            gid, text, tool = g["goal_id"], g["goal_text"], g["action_tool"]
            bare = _ALL_TOOLS.sub(" ", text)
            hit = [n for n in forbidden_doc if _occurs(n, bare)]
            if hit:
                _err(errors, "names_document", gid, hit[0])
            hit = [t for t in titles if _occurs(t, bare)]
            if hit:
                _err(errors, "names_section", gid, hit[0])
            hit = [l for l in labels if _occurs(l, bare)] + ([s["locator"]] if _occurs(s["locator"], bare) else [])
            if hit:
                _err(errors, "names_label", gid, hit[0])
            leaked = False
            for vals in contents.values():
                for val in vals:
                    if val.strip() and vc.occurs(val, text):
                        leaked = True
                    for tok in tv.distinctive_tokens(val):
                        if len(tok) >= TOKEN_MIN and not vc.occurs(tok, s["locator"]) and vc.occurs(tok, text):
                            leaked = True
            if leaked:
                _err(errors, "goal_states_content", gid)
            if tool not in GOAL_TOOLS:
                _err(errors, "bad_action_tool", gid, str(tool))
            elif tool not in text:
                _err(errors, "tool_not_named", gid, tool)
            hits = tv._vocab(text)
            if hits:
                _err(errors, "goal_vocabulary", gid, ",".join(hits))
            n_sent = len([x for x in tv._SENT.split(text.strip()) if x.strip()])
            if not 2 <= n_sent <= 4:
                _err(errors, "sentence_count", gid, str(n_sent))
    counts = {"slots": len(slots), "goals": len(goals), "goals_per_slot": dict(per_slot),
              "by_tool": dict(Counter(g["action_tool"] for g in goals))}
    return {"ok": not errors, "errors": errors, "counts": counts}


def main(argv: list[str] | None = None) -> int:
    slots = json.loads((fs.WORK / "stage3/v5/FT/blue/slots-v0.json").read_text(encoding="utf-8"))
    goals = [json.loads(x) for x in (P2 / "goals-v0.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    states = fs.load_honest_states()
    rep = validate(slots, goals, states)
    print(json.dumps({"ok": rep["ok"], "counts": rep["counts"], "n_errors": len(rep["errors"]),
                      "errors_by_code": dict(Counter(e["code"] for e in rep["errors"])),
                      "errors": rep["errors"][:120]}, indent=1))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
