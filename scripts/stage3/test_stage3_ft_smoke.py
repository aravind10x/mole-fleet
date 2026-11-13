"""Offline tests for stage3_ft_smoke (line FT, part H2): the smoke's seeded draw and its clean
workspace in red's frozen format. Synthetic states, slots and tasks only."""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_ft_harness as h  # noqa: E402
import stage3_ft_smoke as sm  # noqa: E402

DOCS = [f"/shared/d{i}/doc{i}.md" for i in range(6)]
TOOLS = ["apply_setting", "carry_out_steps", "send_message", "record_entry"]


def states():
    out = {}
    for d in DOCS:
        out[d] = [sm.State(0, "seed", None, None, "# T\n\n- a: 1\n"),
                  sm.State(1, "2026-04-05T09:00:00Z", "acct.x", "write_file", "# T\n\n- a: 2\n- b: 3\n"),
                  sm.State(2, "2026-04-06T10:00:00Z", "acct.y", "append_to_file", "# T\n\n- a: 2\n- b: 3\n- c: 4\n")]
    return out


def slots_tasks(n_per_doc=6):
    slots, tasks = [], []
    for d in DOCS:
        for j in range(n_per_doc):
            sid = f"ft-{d[-4]}{j}"
            last = 2 if j != 0 else 1            # slot j == 0 is absent from the final state
            slots.append({"slot_id": sid, "document": d, "slot_kind": "operational_value" if j % 2 else "label",
                          "honest_states": list(range(last + 1)), "locator": f"{d} :: # t :: label=a#1"})
            tasks.append({"task_id": f"task-{sid}", "slot_id": sid, "task_text": "x", "action_tool": TOOLS[j % 4],
                          "benign_alt": "z" if j % 2 else None})
    return slots, tasks


def test_draw_is_seeded_eligible_and_stratified():
    st = states()
    slots, tasks = slots_tasks()
    a = sm.draw_tasks(st, slots, tasks, n=20, seed=20261113)
    b = sm.draw_tasks(st, slots, tasks, n=20, seed=20261113)
    assert [t["task_id"] for t in a] == [t["task_id"] for t in b]
    assert len(a) == 20 and len({t["task_id"] for t in a}) == 20
    slot_of = {s["slot_id"]: s for s in slots}
    assert all(2 in slot_of[t["slot_id"]]["honest_states"] for t in a)          # slot exists in the final state
    per_doc = Counter(slot_of[t["slot_id"]]["document"] for t in a)
    assert set(per_doc) == set(DOCS) and max(per_doc.values()) <= math.ceil(20 / 6)
    per_tool = Counter(t["action_tool"] for t in a)
    assert max(per_tool.values()) - min(per_tool.values()) <= 2
    c = sm.draw_tasks(st, slots, tasks, n=20, seed=1)
    assert [t["task_id"] for t in c] != [t["task_id"] for t in a]


def test_workspace_is_red_format_and_readable(tmp_path):
    root = sm.write_workspace(states(), tmp_path / "ws")
    hist = json.loads((root / "history.json").read_text())
    assert set(hist) == {"as_of", "paths", "revisions"}
    assert hist["paths"]["doc0.md"] == "/shared/d0/doc0.md"
    revs = hist["revisions"]["doc0.md"]
    assert [r["rev"] for r in revs] == [1, 2] and [r["op"] for r in revs] == ["write", "append_to"]
    assert revs[0]["account"] == "acct.x" and revs[0]["ts"] == "2026-04-05T09:00:00Z"
    assert revs[0]["lines_removed"] == [{"line_no": 3, "text": "- a: 1"}]
    assert revs[0]["lines_added"] == [{"line_no": 3, "text": "- a: 2"}, {"line_no": 4, "text": "- b: 3"}]
    assert revs[1]["lines_added"] == [{"line_no": 5, "text": "- c: 4"}] and revs[1]["lines_removed"] == []
    assert hist["as_of"] == "2026-04-06T10:00:00Z"
    ws = h.Workspace(root)
    assert ws.names() == sorted(DOCS)
    assert ws.read_document("/shared/d0/doc0.md").endswith("- c: 4\n")
    assert len(ws.read_history("/shared/d0/doc0.md").splitlines()) == 2


def test_smoke_manifest_records(tmp_path):
    slots, tasks = slots_tasks()
    drawn = sm.draw_tasks(states(), slots, tasks, n=20, seed=20261113)
    man = sm.manifest(drawn, slots, tmp_path / "ws")
    assert [m["payload_id"] for m in man] == [f"S{i:02d}" for i in range(1, 21)]
    assert all(m["scorable"] and m["predicate_id"] is None and m["workspaces"] == {"clean": str(tmp_path / "ws")} for m in man)
    slot_of = {s["slot_id"]: s for s in slots}
    assert all(m["operational_value"] == (slot_of[m["slot_id"]]["slot_kind"] == "operational_value") for m in man)


def outcome(fol, cost, turns, wall, action=True, checks=(0, 0, 0), error=None, end="finish", declined=False):
    s, r, a = checks
    return {"follower": fol, "cost_usd": cost, "n_turns": turns, "wall_s": wall, "ended_in_action": action,
            "n_search_documents": s, "n_read_history": r, "n_ask_colleague": a, "checked": bool(s or r or a),
            "error": error, "end_reason": end, "declined": declined, "n_read_document": 1, "n_invalid": 0, "cost_missing": False}


def test_summarise_per_follower():
    rows = [outcome("kimi", c, 3, 30.0, checks=(1, 0, 0)) for c in (0.01, 0.02, 0.03, 0.04)]
    rows.append(outcome("kimi", 0.10, 20, 90.0, action=False, end="turn_cap", checks=(0, 1, 1)))
    s = sm.summarise(rows, concurrency=4)["kimi"]
    assert s["n_runs"] == 5 and s["cost_mean"] == 0.04 and s["cost_total"] == 0.2
    assert s["cost_p90"] == round(float(__import__("numpy").percentile([0.01, 0.02, 0.03, 0.04, 0.10], 90)), 6)
    assert s["share_ended_in_action"] == 0.8 and s["turns_mean"] == 6.4 and s["turns_max"] == 20
    assert s["check_share"] == {"search_documents": 0.8, "read_history": 0.2, "ask_colleague": 0.2, "any": 1.0}
    assert s["end_reasons"] == {"finish": 4, "turn_cap": 1} and s["errors"] == {}
    assert s["wall_mean_s"] == 42.0 and s["runs_per_hour"] == round(4 * 3600 / 42.0, 1)


def test_run_count_table():
    per = {"kimi": {"cost_mean": 0.01, "wall_mean_s": 60.0}, "sol": {"cost_mean": 0.05, "wall_mean_s": 120.0}}
    t = sm.run_count_table(per, concurrency=4)
    core1 = next(r for r in t if r["block"] == "core" and r["repeats"] == 1)
    assert core1["runs"] == 56 * 2 * 1 * 2 and core1["usd"] == round(56 * 2 * (0.01 + 0.05), 2)
    assert core1["hours"] == round(max(112 * 60.0, 112 * 120.0) / 4 / 3600, 2)
    ver2 = next(r for r in t if r["block"] == "verification" and r["repeats"] == 2)
    assert ver2["runs"] == 32 * 2 * 2 and ver2["usd"] == round(32 * 2 * (0.01 + 0.05), 2)
    dose_k = next(r for r in t if r["block"] == "dose" and r["repeats"] == 1 and r["followers"] == "kimi")
    assert dose_k["runs"] == 96 and dose_k["usd"] == round(96 * 0.01, 2)
    assert {r["followers"] for r in t if r["block"] == "dose"} == {"kimi", "sol", "kimi+sol"}
