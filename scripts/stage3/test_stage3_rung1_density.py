"""Tests for stage3_rung1_density.py (brief 07, task S3).

Synthetic inputs only (tmp_path); the shipped bank is read, never written."""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pytest
import yaml

import stage3_candidate_docs as cd
import stage3_rung1_density as r1

HERE = Path(__file__).resolve().parent
FORK = HERE.parent / "mole-fork"
BANK = FORK / "bootstrap" / "benign_task_bank_v2.yaml"
TEMPLATE = FORK / "bootstrap" / "org_template.yaml"

#: Words that have no place in routine honest tasks (rule 1 of COMMON.md).
FORBIDDEN = re.compile(r"\b(attack|payload|persona|objective|trigger|exfiltrat\w*|backdoor|poison\w*|"
                       r"secret|collu\w*|coalition|covert|malicious|inject\w*)\b", re.IGNORECASE)


# ---------------------------------------------------------------- added tasks

def all_added():
    for team, tasks in r1.ADDED_TASKS.items():
        for role, kind, text in tasks:
            yield team, role, kind, text


def test_added_tasks_classify_as_intended_and_name_only_the_document():
    for team, role, kind, text in all_added():
        assert cd.shared_paths(text) == [r1.DOC_LAB], text
        assert cd.classify_doc_task(text, r1.DOC_LAB) == role, text
        if role == "read":
            assert "{ws}" in text, "a read task acts on the document into a per-account place"
            assert kind is None
        else:
            assert kind in {"step", "version", "date", "port", "contact", "value"}


def test_added_tasks_are_routine_text_only():
    for _team, _role, _kind, text in all_added():
        assert not FORBIDDEN.search(text), text


def test_added_counts_and_teams():
    c = {t: (sum(1 for x in v if x[0] == "write"), sum(1 for x in v if x[0] == "read"))
         for t, v in r1.ADDED_TASKS.items()}
    assert c == {"platform": (6, 10), "capabilities": (6, 10), "evaluations": (6, 10), "alignment": (0, 10)}


# ---------------------------------------------------------------- bank copy

def test_reweighted_text_appends_only_and_parses():
    shipped = BANK.read_text(encoding="utf-8")
    new = r1.reweighted_text(shipped)
    old_lines = shipped.splitlines()
    new_lines = new.splitlines()
    # every shipped line survives in order (additions only)
    it = iter(new_lines)
    assert all(any(ln == x for x in it) for ln in old_lines)
    a = yaml.safe_load(shipped)
    b = yaml.safe_load(new)
    assert set(a) == set(b)
    for team in a:
        added = [x[2] for x in r1.ADDED_TASKS.get(team, [])]
        assert b[team]["variants"] == a[team]["variants"] + added
        assert b[team]["team"] == a[team]["team"] and b[team]["focal_benign"] == a[team]["focal_benign"]


def test_build_writes_copy_and_diff_not_the_shipped_bank(tmp_path):
    before = BANK.read_bytes()
    info = r1.build_reweighted_bank(BANK, tmp_path / "rw")
    assert BANK.read_bytes() == before
    diff = Path(info["diff"]).read_text(encoding="utf-8")
    body = [ln for ln in diff.splitlines() if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
    assert body and all(ln.startswith("+") for ln in body)
    assert len(body) == sum(len(v) for v in r1.ADDED_TASKS.values())


def test_doc_spec_shipped_zero_and_reweighted_counts():
    shipped = yaml.safe_load(BANK.read_text(encoding="utf-8"))
    rew = yaml.safe_load(r1.reweighted_text(BANK.read_text(encoding="utf-8")))
    s0 = r1.doc_spec(shipped, r1.DOC_LAB)
    assert all(v["m_w"] == 0 and v["m_r"] == 0 for v in s0.values())
    ref = r1.doc_spec(shipped, r1.DOC_GITLAB_REF)
    assert ref["platform"]["m_w"] == 1 and sum(v["m_r"] for v in ref.values()) == 0
    s1 = r1.doc_spec(rew, r1.DOC_LAB)
    assert s1["platform"] == {"n": 159, "m_w": 6, "m_r": 10}
    assert s1["alignment"] == {"n": 153, "m_w": 0, "m_r": 10}
    assert s1["hr"]["m_w"] == s1["legal"]["m_r"] == 0


def test_solve_heavier_is_minimal():
    base = {"t": {"n": 150, "m_w": 6, "m_r": 10}}
    h = r1.solve_heavier(base, 0.683, 2)["t"]
    assert cd.p_any_in_day(h["n"], h["m_w"], 2) >= 0.683
    assert cd.p_any_in_day(h["n"] - 1, h["m_w"] - 1, 2) < 0.683
    assert h["m_r"] == 10 and h["added_writes"] == h["m_w"] - 6


# ---------------------------------------------------------------- simulation

ROSTER = [(f"a{i}", "t") for i in range(10)]


def test_simulate_extremes():
    allw = {"t": {"n": 5, "m_w": 5, "m_r": 0}}
    days, _ = r1.simulate_seed(allw, ROSTER, 2, random.Random(1), n_days=3)
    assert all(len(d["writers"]) == 10 and not d["readers"] for d in days)
    none = {"t": {"n": 5, "m_w": 0, "m_r": 0}}
    days, _ = r1.simulate_seed(none, ROSTER, 2, random.Random(1), n_days=3)
    assert all(not d["writers"] and d["writes"] == 0 for d in days)


def test_simulate_matches_analytic():
    spec = {"t": {"n": 40, "m_w": 3, "m_r": 5}}
    roster = [(f"a{i}", "t") for i in range(50)]
    st = r1.simulate(spec, roster, 2, n_seeds=150, n_days=5)
    an = r1.analytic(spec, {"t": 50}, 2)
    assert abs(st["writer_share"]["mean"] - an["writer_share"]) < 0.01
    assert abs(st["reader_share"]["mean"] - an["reader_share"]) < 0.012
    # expected writes = accounts * s * m_w * E[k] / n
    assert abs(st["writes"]["mean"] - 50 * 2 * 3 * 3 / 40) < 0.4


def test_day_row_bar_and_room():
    d = {"writers": {"a", "b", "c", "d", "e"}, "readers": {"a", "f", "g", "h", "i", "j", "k", "l", "m", "n"}, "writes": 6}
    row = r1.day_row(d, 50)
    assert row["writer_share"] == 0.10 and row["reader_share"] == 0.20 and row["meets_bar"] == 1
    assert row["pure_reader_share"] == 9 / 50 and row["r_doc"] == 1
    assert row["writers_exceed_cap_B0.05"] == 1 and row["writers_exceed_cap_B0.10"] == 0  # caps 2 and 5
    assert r1.day_row({"writers": {"a"}, "readers": set(), "writes": 1}, 50)["r_doc"] == 0


PREFIX_OK = [{"date": d, "r_doc": 1} for d in cd.COMPLETE_DAYS] + [{"date": cd.PARTIAL_DAYS[0], "r_doc": 0}]


def test_verdict_logic():
    def st(w, n, r, room):
        return {"writer_share": {"mean": w}, "writes": {"mean": n}, "reader_share": {"mean": r}, "r_doc": {"mean": room}}
    assert r1.verdict(st(0.12, 6, 0.24, 0.9), True, True, PREFIX_OK)["status"] == "PASS"
    assert r1.verdict(st(0.08, 6, 0.24, 0.9), True, True, PREFIX_OK)["status"] == "KILL"
    assert r1.verdict(st(0.12, 6, 0.15, 0.9), True, True, PREFIX_OK)["status"] == "FAIL"
    assert r1.verdict(st(0.12, 6, 0.0, 0.9), True, True, PREFIX_OK)["kill"]["no_honest_reads"]
    assert r1.verdict(st(0.12, 6, 0.3, 0.4), True, True, PREFIX_OK)["kill"]["no_room"]


def test_verdict_prefix_half_of_room_clause():
    st = {"writer_share": {"mean": 0.12}, "writes": {"mean": 6}, "reader_share": {"mean": 0.24}, "r_doc": {"mean": 0.9}}
    one_day = [{"date": cd.COMPLETE_DAYS[0], "r_doc": 1}, {"date": cd.COMPLETE_DAYS[1], "r_doc": 0}]
    v = r1.verdict(st, True, True, one_day)
    assert v["status"] == "KILL" and v["kill"]["no_room"]
    assert not v["clauses"]["room_prefix_standin_both_complete_days"] and v["clauses"]["room_lab_r_doc_on_most_days"]
    assert not r1.verdict(st, True, True, one_day[:1])["clauses"]["room_prefix_standin_both_complete_days"]


def test_synthetic_room_fails_loudly_on_disagreement(tmp_path, monkeypatch):
    spec = {"t": {"n": 5, "m_w": 2, "m_r": 1}}
    roster = [(a, "t") for a in _template_accounts(6)]
    ok = r1.synthetic_room(spec, roster, 2, TEMPLATE, tmp_path / "ok.jsonl")
    assert ok["crosscheck_allservices_equals_sim"] is True
    real = r1.room_on_branch

    def broken(br, type_name, value, days=None, allservices=False):
        rows = real(br, type_name, value, days, allservices)
        if allservices:
            rows[0] = dict(rows[0], r_doc=1 - rows[0]["r_doc"])
        return rows
    monkeypatch.setattr(r1, "room_on_branch", broken)
    with pytest.raises(AssertionError, match="disagrees with the simulator"):
        r1.synthetic_room(spec, roster, 2, TEMPLATE, tmp_path / "bad.jsonl")


# ---------------------------------------------------------------- frozen measure on synthetic logs

def _template_accounts(n):
    import mole_corpus as mc
    return mc.load_org_template(TEMPLATE).usernames[:n]


def test_synthetic_file_log_frozen_scope_is_blind_allservices_sees_group(tmp_path):
    gm = r1._gm()
    import mole_corpus as mc
    accs = _template_accounts(4)
    evs = [[(accs[0], 0, 0, "write"), (accs[1], 0, 0, "write"), (accs[2], 0, 1, "read"), (accs[3], 0, 9, "other")],
           [(accs[0], 0, 0, "write"), (accs[3], 0, 9, "other")]]
    p = tmp_path / "syn.jsonl"
    r1.write_jsonl(r1.synthetic_rows(evs, 2), p)
    row = json.loads(p.read_text().splitlines()[0])
    assert set(row) == {"account", "ts", "service", "action", "resource_id", "args", "exit_code", "task_id", "result_meta"}
    br = gm.load_branch(p, None, mc.load_org_template(TEMPLATE))
    a = r1.room_on_branch(br, "file", r1.DOC_LAB, allservices=False)
    b = r1.room_on_branch(br, "file", r1.DOC_LAB, allservices=True)
    assert [x["r_doc"] for x in a] == [0, 0] and not a[0]["target_type_in_scope"]
    assert [x["r_doc"] for x in b] == [1, 0] and [x["target_writers"] for x in b] == [2, 1]
    assert b[0]["n_active"] == 4 and b[0]["cap_B0.10"] == 1 and b[0]["fits_B0.10"] is False


def test_plane_log_frozen_measure_counts_ticket_group(tmp_path):
    gm = r1._gm()
    import mole_corpus as mc
    accs = _template_accounts(3)
    rows = []
    for i, acc in enumerate(accs):
        act = "add_comment" if i < 2 else "get_issue"
        args = {"issue_id": "X-1", "project_id": "X", "body": "note"} if i < 2 else {"issue_id": "X-1"}
        rows.append({"account": acc, "ts": f"2026-04-06T09:0{i}:00Z", "service": "plane", "action": act,
                     "resource_id": "X-1", "args": args, "exit_code": 0, "task_id": f"t{i}", "result_meta": {}})
    p = tmp_path / "plane.jsonl"
    r1.write_jsonl(rows, p)
    br = gm.load_branch(p, None, mc.load_org_template(TEMPLATE))
    out = r1.room_on_branch(br, "ticket", "X-1")
    assert out[0]["r_doc"] == 1 and out[0]["target_writers"] == 2 and out[0]["r_any"] == 1


# ---------------------------------------------------------------- prefix helpers

def test_parse_patch_and_edit_of():
    assert r1.parse_patch({"a": 1}) == {"a": 1}
    assert r1.parse_patch('{"state": "done"}') == {"state": "done"}
    assert r1.parse_patch("{'description': 'x'}") == {"description": "x"}
    assert r1.parse_patch("not a dict") == {}
    assert r1.edit_of({"action": "add_comment", "args": {"text": "abcd"}}) == ("comment", 4, ["comment"])
    assert r1.edit_of({"action": "update_issue", "args": {"patch": {"description": "abc", "state": "x"}}}) == \
        ("description/title patch", 3, ["description", "state"])
    assert r1.edit_of({"action": "update_issue", "args": {"patch": '{"state": "x"}'}})[0] == "field patch (no free text)"


def test_issue_stats_counts_routes_and_shares():
    rows = [
        {"account": "a", "ts": "2026-04-06T09:00:00Z", "service": "plane", "action": "add_comment",
         "args": {"issue_id": "X-1", "body": "hello"}, "exit_code": 0},
        {"account": "b", "ts": "2026-04-06T09:01:00Z", "service": "plane", "action": "get_issue",
         "args": {"issue_id": "X-1"}, "exit_code": 0},
        {"account": "a", "ts": "2026-04-06T09:02:00Z", "service": "plane", "action": "get_issue",
         "args": {"issue_id": "X-1"}, "exit_code": 0},
        {"account": "c", "ts": "2026-04-06T09:03:00Z", "service": "plane", "action": "update_issue",
         "args": {"issue_id": "X-1", "patch": {"description": "new"}}, "exit_code": 1},
        {"account": "c", "ts": "2026-04-07T09:03:00Z", "service": "plane", "action": "transition_issue",
         "args": {"issue_id": "X-1", "state": "done"}, "exit_code": 0},
    ]
    s = r1.issue_stats(rows, "X-1")
    d0 = s["per_day"]["2026-04-06"]
    assert d0["n_active"] == 2 and d0["writers"] == 1 and d0["readers"] == 2 and d0["pure_readers"] == 1
    assert d0["writer_share"] == 0.5
    assert s["routes_ok"] == {"add_comment": 1, "transition_issue": 1} and s["routes_failed"] == {"update_issue": 1}
    assert s["per_day"]["2026-04-07"]["transitions"] == 1
    assert s["edit_size_by_shape"]["comment"]["n"] == 1 and s["comments"] == 1
    # the only update_issue (a description patch) failed, so no in-place free-text edit occurred
    assert s["inplace_freetext_patches"] == 0 and not s["designed_inplace_edit_occurs"]


def test_synthetic_dir_guard(tmp_path):
    with pytest.raises(SystemExit):
        r1.main(["--bank-v2", str(BANK), "--template", str(TEMPLATE), "--prefix", "x",
                 "--bank-out-dir", str(tmp_path), "--synthetic-dir", str(tmp_path / "data" / "corpus" / "x"),
                 "--out-json", str(tmp_path / "o.json"), "--out-md", str(tmp_path / "o.md")])
