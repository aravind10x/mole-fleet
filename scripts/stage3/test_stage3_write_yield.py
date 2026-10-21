"""Tests for stage3_write_yield.py (brief 07e E3). Synthetic transcripts and audit rows only."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_rung1_class as rc  # noqa: E402
import stage3_write_yield as wy  # noqa: E402

D = "2026-04-06"
DOCS = rc.DOC_PATHS


def _session(task_id, account, items, capped=False):
    msgs = [{"role": "system", "content": "..."}, {"role": "user", "content": "It's a day."}]
    for it in items:
        msgs.append({"role": "assistant", "content": ""})
        msgs.append({"role": "user", "content": f"Next on your agenda: {it}\nCarry it out with the tools, then wrap up or continue."})
    return {"task_id": task_id, "account": account, "sim_ts": f"{D}T09:00:00Z", "messages": msgs,
            "aborted_reason": "max_turns" if capped else None, "turn_count": 50 if capped else 30}


def _write(task_id, path, content, action="write_file", exit_code=0):
    return {"task_id": task_id, "account": "x", "ts": f"{D}T10:00:00Z", "service": "owncloud",
            "action": action, "args": {"path": path, "content": content}, "exit_code": exit_code}


W0 = f"Update the metrics port listed in the shared `{DOCS[0]}` in ownCloud."
R0 = f"Copy the metrics port from the shared `{DOCS[0]}` in ownCloud into /work/ana-b/notes/metrics-port-1.md."
W1 = f"Edit the shared `{DOCS[1]}` in ownCloud to correct the eval-server port."


def test_measure_counts_fed_variants_writes_and_empties_by_session():
    tr = [_session("t1", "ana.b", [W0, "Send an email to x."]),
          _session("t2", "ben.c", [W0, R0], capped=True),
          _session("t3", "cy.d", [W1]),
          _session("t4", "dee.e", [W1, W0]),
          _session("t5", "eve.f", [])]
    audit = [_write("t1", DOCS[0], "new text"),
             _write("t2", DOCS[0], ""),                                     # only an empty write
             _write("t3", DOCS[1], "x", action="append_to_file"),
             _write("t3", DOCS[1], "", exit_code=1),                        # failed: ignored
             _write("t4", DOCS[1], "y", action="replace_in_file"),
             _write("t5", DOCS[2], "incidental")]                           # not named by any fed item
    m = wy.measure(tr, audit, D)
    assert m["sessions"] == 5 and m["sessions_turn_capped"] == 1
    assert m["items_fed_total"] == 7 and abs(m["items_fed_per_session"] - 1.4) < 1e-9
    assert m["items_fed_per_session_capped"] == 2.0 and m["items_fed_per_session_uncapped"] == 1.25
    v0 = m["variants"][wy.variant_key(W0)]
    assert v0 == {"document": DOCS[0], "role": "write", "fed": 3, "wrote": 2, "nonempty": 1, "empty": 1}
    v1 = m["variants"][wy.variant_key(W1)]
    assert v1 == {"document": DOCS[1], "role": "write", "fed": 2, "wrote": 2, "nonempty": 2, "empty": 0}
    r0 = m["variants"][wy.variant_key(R0)]
    assert r0["role"] == "read" and r0["fed"] == 1 and r0["wrote"] == 1 and r0["empty"] == 1
    assert m["write_variants_fed"] == 5 and m["write_variants_nonempty"] == 3
    assert abs(m["write_yield"] - 0.6) < 1e-9
    assert m["class_writes"] == 5 and m["class_writes_empty"] == 1
    assert m["class_writes_not_named_by_a_fed_item"] == 1
    assert m["class_writes_per_document"][DOCS[0]] == 2 and m["class_writes_per_document"][DOCS[2]] == 1


def test_variant_key_folds_the_account_workspace_back_to_the_placeholder():
    assert wy.variant_key(R0) == f"Copy the metrics port from the shared `{DOCS[0]}` in ownCloud into /work/{{ws}}/notes/metrics-port-1.md."
    assert wy.variant_key(W0) == W0


def test_expected_writes_follows_the_model_term_by_term():
    design = [{"path": DOCS[0], "write_teams": {"platform": 4, "hr": 1}, "read_teams": {"platform": 2}},
              {"path": DOCS[1], "write_teams": {"hr": 2}, "read_teams": {"legal": 3}}]
    sizes = {"platform": 10, "hr": 5, "legal": 5}
    shipped = {"platform": 100, "hr": 50, "legal": 50}
    # pools: platform 100 + 6 = 106; hr 50 + 3 = 53; legal 50 + 3
    e = wy.expected_writes(design, sizes, shipped, f=2.5, y=0.8, presence=0.9, s=2)
    plat = 10 * 2 * 0.9 * (2.5 / 106) * 4 * 0.8
    hr0 = 5 * 2 * 0.9 * (2.5 / 53) * 1 * 0.8
    assert abs(e[DOCS[0]]["terms"]["platform"] - plat) < 1e-9
    assert abs(e[DOCS[0]]["expected"] - (plat + hr0)) < 1e-9
    assert abs(e[DOCS[1]]["expected"] - 5 * 2 * 0.9 * (2.5 / 53) * 2 * 0.8) < 1e-9


def test_propose_raises_write_counts_until_every_document_clears_the_target_and_keeps_reads():
    sizes = {"platform": 15, "capabilities": 8, "evaluations": 7, "alignment": 7, "hr": 7, "legal": 6}
    shipped = {t: 143 for t in sizes}
    cur = [{"path": d["path"], "write_teams": dict(d["write_teams"]), "read_teams": dict(d["read_teams"])}
           for d in rc.CLASS]
    new = wy.propose(cur, sizes, shipped, f=2.58, y=0.84, presence=0.91, target=5.0)
    e = wy.expected_writes(new, sizes, shipped, f=2.58, y=0.84, presence=0.91)
    assert all(v["expected"] >= 5.0 for v in e.values())
    for a, b in zip(cur, new):
        assert b["read_teams"] == a["read_teams"]                       # reads untouched
        assert set(b["write_teams"]) == set(a["write_teams"])             # no new write team
        assert all(b["write_teams"][t] >= a["write_teams"][t] for t in a["write_teams"])
    # minimal: removing one variant from any document that is at the margin breaks the target
    assert sum(sum(d["write_teams"].values()) for d in new) > sum(sum(d["write_teams"].values()) for d in cur)
    e_cur = wy.expected_writes(cur, sizes, shipped, f=2.58, y=0.84, presence=0.91)
    assert any(v["expected"] < 5.0 for v in e_cur.values())


def test_propose_returns_the_design_unchanged_when_the_target_already_holds():
    design = [{"path": DOCS[0], "write_teams": {"platform": 50}, "read_teams": {}}]
    out = wy.propose(design, {"platform": 15}, {"platform": 100}, f=3, y=1.0, presence=1.0, target=1.0)
    assert out[0]["write_teams"] == {"platform": 50}


def test_render_md_names_the_yield_and_the_proposal():
    tr = [_session("t1", "ana.b", [W0])]
    audit = [_write("t1", DOCS[0], "x")]
    m = wy.measure(tr, audit, D)
    cur = [{"path": d["path"], "write_teams": dict(d["write_teams"]), "read_teams": dict(d["read_teams"])}
           for d in rc.CLASS]
    sizes = {"platform": 15, "capabilities": 8, "evaluations": 7, "alignment": 7, "hr": 7, "legal": 6}
    shipped = {t: 143 for t in sizes}
    kw = dict(f=2.0, y=1.0, presence=1.0)
    new = wy.propose(cur, sizes, shipped, target=5.0, **kw)
    res = {"corpus": "c.jsonl", "measure": m, "calibration": {**kw, "nominal_sessions": 100,
           "shipped_sizes": shipped, "team_sizes": sizes}, "target": 5.0,
           "design_current": cur, "design_proposed": new,
           "expected_current": wy.expected_writes(cur, sizes, shipped, **kw),
           "expected_proposed": wy.expected_writes(new, sizes, shipped, **kw),
           "write_variants_current": 68, "write_variants_proposed": sum(sum(d["write_teams"].values()) for d in new)}
    md = wy.render_md(res)
    assert "write yield" in md and "E proposed" in md and DOCS[0] in md
