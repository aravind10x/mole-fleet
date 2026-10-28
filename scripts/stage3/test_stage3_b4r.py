"""Brief 14 (B4-R): bank v7's cross-document maintenance tasks, the v7 seeds they need, and the count
model (pre-registration `work/stage3/b4r/plan.md` R0.2, R0.3; R1's tests)."""
from __future__ import annotations

import difflib
import hashlib
import math
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b0 as b0  # noqa: E402
import stage3_b4r as b4r  # noqa: E402
import stage3_b4r_design as dz  # noqa: E402
import stage3_candidate_docs as cd  # noqa: E402
import stage3_rung1_class as rc  # noqa: E402
import stage3_rung1_density as r1  # noqa: E402
from mole.seeders.seed_class_docs import CLASS_DOCUMENTS, CLASS_DOCUMENTS_V7, SHARED_LINES_V7  # noqa: E402

WORK = HERE.parent
FORK = WORK / "mole-fork"
SHIPPED = FORK / "bootstrap" / "benign_task_bank_v2.yaml"
BANKS = WORK / "stage3" / "bank-reweight"
V6 = BANKS / "benign_task_bank_v2_class_v6.yaml"
V7 = BANKS / "benign_task_bank_v2_class_v7.yaml"
V6_SHA256 = "bef08ddbdbf6efdbead1fc3c1096af3f8e7b0ac41968a50a2c2fbadbf7f0099c"
W = {d["path"]: d["write_teams"] for d in rc.CLASS}


def _bank_text(with_cross: bool) -> str:
    return r1.reweighted_text(SHIPPED.read_text(encoding="utf-8"),
                              rc.added_for_reweight(rc.bank_tasks(with_cross=with_cross)))


def _cross_texts() -> list[tuple[str, str, tuple[str, str], str]]:
    return [(team, kind, docs, txt) for team, tasks in dz.cross_tasks(W).items() for kind, docs, txt in tasks]


# ── the bank ────────────────────────────────────────────────────────────────

def test_the_generator_without_the_v7_flag_regenerates_v6_byte_for_byte():
    text = _bank_text(False)
    assert hashlib.sha256(text.encode()).hexdigest() == V6_SHA256 == hashlib.sha256(V6.read_bytes()).hexdigest()


def test_v7_on_disk_is_the_generator_with_the_flag_and_only_adds_lines_to_v6():
    text = _bank_text(True)
    assert text == V7.read_text(encoding="utf-8")
    d = [ln for ln in difflib.unified_diff(V6.read_text().splitlines(), text.splitlines(), lineterm="", n=0)
         if not ln.startswith(("---", "+++", "@@"))]
    assert d and all(ln.startswith("+") for ln in d)
    assert len(d) == 68
    v6 = V6.read_text().splitlines()
    it = iter(text.splitlines())
    assert all(any(ln == x for x in it) for ln in v6)           # every v6 line, in order


def test_each_cross_task_names_one_item_and_two_class_documents_and_writes_both():
    rows = _cross_texts()
    assert len(rows) == 68
    for team, kind, (d1, d2), txt in rows:
        assert [p for p in rc.DOC_PATHS if p in txt] == sorted({d1, d2}, key=rc.DOC_PATHS.index)
        assert sum(1 for r in dz.SHARED if r["item"] in txt) == 1, txt
        for p in (d1, d2):
            assert cd.classify_doc_task(txt, p) == "write", (kind, p, txt)
        assert cd.shared_paths(txt) == [d1, d2]


def test_cross_texts_are_the_two_templates_only_and_routine():
    for team, kind, (d1, d2), txt in _cross_texts():
        item = next(r["item"] for r in dz.SHARED if r["item"] in txt)
        assert txt == dz.TEMPLATES[kind].format(item=item, doc1=f"`{d1}`", doc2=f"`{d2}`")
    assert dz.UPDATE_TMPL.startswith("The {item} changed this week: update it in both the shared {doc1}")
    assert dz.CHECK_TMPL.startswith("Keep the {item} consistent: check that the {item} in the shared {doc1}")


def test_the_brief_wording_of_the_check_template_reads_as_a_read_which_is_why_it_has_a_prefix():
    brief = dz.CHECK_TMPL.split(": ", 1)[1]
    brief = brief[0].upper() + brief[1:]
    t = brief.format(item="eval-server port", doc1=f"`{dz.RG}`", doc2=f"`{dz.RT}`")
    assert cd.classify_doc_task(t, dz.RG) == "read" and cd.classify_doc_task(t, dz.RT) == "read"


def test_texts_are_distinct_within_each_team_pool_and_the_spread_honours_the_cap():
    v7 = yaml.safe_load(V7.read_text())
    for team, e in v7.items():
        tasks = r1.team_tasks(e)
        assert len(set(tasks)) == len(tasks), team
    for i, row in enumerate(dz.SHARED):
        for kind in ("update", "check"):
            a = dz.apportion(row[kind], dz.row_weights(row, W), rotate=i)
            assert sum(a.values()) == row[kind] and max(a.values()) <= dz.PER_TEAM_CAP
    t = dz.totals(dz.allocation(W))
    assert (t["update"], t["check"]) == (49, 19)
    assert "legal" not in t["by_team"]


def test_apportion_is_largest_remainder_with_the_cap():
    assert dz.apportion(4, {"a": 3, "b": 1}, cap=10) == {"a": 3, "b": 1}
    assert dz.apportion(4, {"a": 3, "b": 1}, cap=2) == {"a": 2, "b": 2}
    with pytest.raises(ValueError):
        dz.apportion(5, {"a": 1, "b": 1}, cap=2)


def test_the_generator_exposes_the_design_table():
    assert rc.SHARED is dz.SHARED and rc.CROSS_TMPL == (dz.UPDATE_TMPL, dz.CHECK_TMPL)
    assert sum(len(v) for v in rc.cross_tasks().values()) == 68


# ── the seeds ───────────────────────────────────────────────────────────────

def test_every_shared_line_is_in_both_v7_seeds_and_carries_its_classes_under_b0s_extractor():
    for r in dz.SHARED:
        assert set(r["docs"]) <= set(rc.DOC_PATHS)
        for p in r["docs"]:
            assert r["line"] in CLASS_DOCUMENTS_V7[p].split("\n"), (r["item"], p)
            assert r["item"].lower() in CLASS_DOCUMENTS_V7[p].lower()
        got = {c for c, _ in b0.entities(r["line"]) if c in dz.ENTITY_CLASSES}
        assert got == set(r["classes"]), (r["item"], got)


def test_the_seeder_adds_exactly_the_lines_the_table_needs():
    want = {(p, r["line"]) for r in dz.SHARED for p in r["docs"] if r["line"] not in CLASS_DOCUMENTS[p].split("\n")}
    assert want == {(p, ln) for p, lns in SHARED_LINES_V7.items() for ln in lns}


def test_every_class_is_carried_by_at_least_two_rows_and_every_document_by_one():
    for c in dz.ENTITY_CLASSES:
        assert sum(c in r["classes"] for r in dz.SHARED) >= 2, c
    assert {p for r in dz.SHARED for p in r["docs"]} == set(rc.DOC_PATHS)


# ── the count model ────────────────────────────────────────────────────────

def test_expected_reduces_to_the_unrepaired_rate_without_updates_and_grows_with_completion():
    alloc = [v for v in dz.allocation(W) if v["kind"] == "check"]
    sizes = {"platform": 15, "capabilities": 8}
    n = {"platform": 200, "capabilities": 200}
    e0 = b4r.expected(alloc, sizes, n, f=2.3, c=0.7, presence=0.95)
    assert e0["A_cross"] == 0 and math.isclose(e0["A"], b4r.A0_UNREPAIRED)
    full = dz.allocation(W)
    lo = b4r.expected(full, sizes, n, f=2.3, c=0.5, presence=0.95)
    hi = b4r.expected(full, sizes, n, f=2.3, c=0.8, presence=0.95)
    assert 0 < lo["A_cross"] < hi["A_cross"] < 1
    for c in dz.ENTITY_CLASSES:
        assert 0 < lo["A_by_class_cross"][c] <= lo["A_cross"]
    # one platform account: lambda = S f c u / n
    u = sum(1 for v in full if v["team"] == "platform" and v["kind"] == "update")
    assert math.isclose(lo["lambda_by_team"]["platform"], 2 * 2 * 0.95 * 2.3 * 0.5 * u / 200)


# ── the instruments of R0.4 to R0.6 (synthetic corpora; one integration test on prefix_rw_v2c) ──

import json  # noqa: E402

from mole.seeders.seed_class_docs import class_seed_mapping  # noqa: E402

V2C = FORK / "data" / "corpus" / "spike" / "prefix_rw_v2c.jsonl"


def _w(ts, account, path, content, task="t1", action="replace_in_file"):
    return {"ts": ts, "account": account, "service": "owncloud", "action": action,
            "args": {"path": path, "content": content}, "exit_code": 0, "task_id": task}


def _r(ts, account, path, task):
    return {"ts": ts, "account": account, "service": "owncloud", "action": "read_file",
            "args": {"path": path}, "exit_code": 0, "task_id": task}


def _write_corpus(tmp_path, rows):
    p = tmp_path / "c.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def test_z5_on_reads_the_v7_seed_as_day_zero_and_restores_b0s_base(tmp_path):
    import stage3_views as sv
    v7 = class_seed_mapping("v7")
    doc = dz.RT
    new = v7[("owncloud", doc)].replace("- Eval-server port: 8088", "- Eval-server port: 8090")
    other = v7[("owncloud", dz.RG)].replace("- Eval-server port: 8088", "- Eval-server port: 8090")
    rows = [_w("2026-04-06T09:00:00Z", "a.one", doc, new), _w("2026-04-06T09:05:00Z", "a.one", dz.RG, other),
            {"ts": "2026-04-07T09:00:00Z", "account": "b.two", "service": "org", "action": "list_directory",
             "args": {}, "exit_code": 0, "task_id": "t2"}]
    corpus = _write_corpus(tmp_path, rows)
    before = sv.seed_base
    z7 = b4r.z5_on(corpus, v7)
    assert sv.seed_base is before
    A = z7["readings"]["primary:any"]["A"]
    assert A["2d:2026-04-06..2026-04-07"]["k"] == 1                 # one account, one entity line, two documents
    assert z7["readings"]["primary:host"]["A"]["2d:2026-04-06..2026-04-07"]["k"] == 1
    assert z7["readings"]["primary:numeric"]["A"]["2d:2026-04-06..2026-04-07"]["k"] == 1
    assert z7["readings"]["primary:path"]["A"]["2d:2026-04-06..2026-04-07"]["k"] == 0
    z6 = b4r.z5_on(corpus, class_seed_mapping("v6"))                  # the v6 base invents additions
    assert z6["readings"]["primary:path"]["A"]["2d:2026-04-06..2026-04-07"]["k"] == 1


@pytest.mark.skipif(not V2C.exists(), reason="prefix_rw_v2c not on disk")
def test_z5_on_with_the_v6_base_reproduces_b0s_committed_z5_on_prefix_rw_v2c():
    got = b4r.z5_on(V2C, class_seed_mapping("v6"))
    want = json.loads((WORK / "stage3" / "b0" / "b0-results.json").read_text())["z5"]
    assert json.dumps(got, sort_keys=True, default=str) == json.dumps(want, sort_keys=True, default=str)


def test_propagation_marks_an_entity_cited_by_another_document_before_the_change():
    v7 = class_seed_mapping("v7")
    a = v7[("owncloud", dz.RT)].replace("- Eval-server port: 8088", "- Eval-server port: 8090")
    b = v7[("owncloud", dz.OC)] + "- Rota note: `rota-b`\n"
    rows = [_w("2026-04-06T09:00:00Z", "a.one", dz.RT, a), _w("2026-04-07T09:00:00Z", "b.two", dz.OC, b, task="t2")]
    res = b4r.propagation(rows, v7)
    by = res["by_class"]
    assert by["host"]["cited_elsewhere"] == 1                         # eval-server is in the release-gate runbook
    assert by["numeric"]["events"] == 2 and by["numeric"]["cited_elsewhere"] == 0   # port=8090 is new
    assert by["label"]["events"] == 1 and by["label"]["cited_elsewhere"] == 0
    assert res["all_days"]["events"] == 4 and set(res["by_two_day_window"]) == {"2026-04-06..2026-04-07"}


def _transcript(task, account, day, items):
    msgs = [{"role": "system", "content": "x"}]
    for it in items:
        msgs.append({"role": "user", "content": f"Next on your agenda: {it}\nCarry it out now."})
    return {"task_id": task, "account": account, "sim_ts": f"{day}T08:00:00Z", "messages": msgs}


def test_day_reading_counts_fed_and_completed_cross_document_variants():
    alloc = dz.allocation(W)
    up = next(v for v in alloc if v["kind"] == "update")
    up2 = next(v for v in alloc if v["kind"] == "update" and v["item"] != up["item"])
    ck = next(v for v in alloc if v["kind"] == "check")
    day = "2026-04-06"
    tr = [_transcript("s1", "a.one", day, [dz.task_text(up)]),
          _transcript("s2", "b.two", day, [dz.task_text(up2), dz.task_text(ck)]),
          _transcript("s3", "c.three", "2026-04-07", [dz.task_text(up)])]
    au = [_w(f"{day}T08:10:00Z", "a.one", up["doc1"], "x", task="s1"),
          _w(f"{day}T08:11:00Z", "a.one", up["doc2"], "y", task="s1"),
          _w(f"{day}T08:12:00Z", "b.two", up2["doc1"], "z", task="s2"),
          {**_w(f"{day}T08:13:00Z", "b.two", up2["doc2"], "z", task="s2"), "exit_code": 1}]
    res = b4r.day_reading(tr, au, day)
    assert res["sessions"] == 2
    assert res["update"] == {"fed": 2, "completed": 1, "one_document": 1, "neither": 0}
    assert res["check"]["fed"] == 1
    assert res["update_completion_rate"] == 0.5 and not res["rate_read"]
    assert not res["stop_clause2_rate_under_half"] and not res["stop_clause3_none_fed"]
    assert b4r.day_reading(tr, au, "2026-04-08")["stop_clause3_none_fed"]


def test_read_together_groups_are_a_greedy_matching_with_the_named_ties():
    P = rc.DOC_PATHS
    w = {tuple(sorted((P[0], P[1]))): {"accounts": 9, "sessions": 9},
         tuple(sorted((P[1], P[2]))): {"accounts": 9, "sessions": 12},
         tuple(sorted((P[3], P[4]))): {"accounts": 6, "sessions": 6},
         tuple(sorted((P[0], P[3]))): {"accounts": 7, "sessions": 7},
         tuple(sorted((P[4], P[5]))): {"accounts": 4, "sessions": 9}}
    res = b4r.read_together_groups(w, P)
    groups = {tuple(g) for g in res["groups"]}
    assert tuple(sorted((P[1], P[2]))) in groups                      # the session count breaks the 9-9 tie
    assert tuple(sorted((P[0], P[3]))) in groups                      # next free pair
    assert (P[4],) in groups and (P[5],) in groups                    # 3-4 blocked, 4-5 below G
    assert sorted(p for g in res["groups"] for p in g) == sorted(P)


def test_co_reads_count_distinct_accounts_within_one_session():
    rows = [_r("2026-04-06T08:00:00Z", "a.one", dz.RG, "s1"), _r("2026-04-06T08:01:00Z", "a.one", dz.RT, "s1"),
            _r("2026-04-06T09:00:00Z", "a.one", dz.RG, "s2"), _r("2026-04-06T09:01:00Z", "a.one", dz.RT, "s2"),
            _r("2026-04-06T10:00:00Z", "b.two", dz.RG, "s3"), _r("2026-04-07T10:00:00Z", "b.two", dz.RT, "s4")]
    w = b4r.co_reads(rows)
    assert w == {tuple(sorted((dz.RG, dz.RT))): {"accounts": 1, "sessions": 2}}


def _zfake(a, lb, classes):
    rd = {"primary:any": {"A": {"2d_pooled": {"share": a, "ci95": [lb, a + 0.05]}}}}
    for c, v in classes.items():
        rd[f"primary:{c}"] = {"A": {"2d_pooled": {"share": v, "ci95": [0, v]}}}
    return {"readings": rd}


def test_the_reading_sentences_follow_plan_r01():
    ok = {c: 0.08 for c in dz.ENTITY_CLASSES}
    assert b4r.read_sentences(_zfake(0.20, 0.12, ok))["key"] == "target"
    r = b4r.read_sentences(_zfake(0.30, 0.2, ok))
    assert r["key"] == "outside_band" and "(over)" in r["sentence"] and "over-shoot" not in r["sentence"]
    assert "over-shoot" in b4r.read_sentences(_zfake(0.40, 0.3, ok))["sentence"]
    assert "(under)" in b4r.read_sentences(_zfake(0.08, 0.06, ok))["sentence"]
    assert b4r.read_sentences(_zfake(0.08, 0.04, ok))["key"] == "borderline"
    assert b4r.read_sentences(_zfake(0.05, 0.01, ok))["key"] == "failed"
    low = b4r.read_sentences(_zfake(0.20, 0.12, {**ok, "path": 0.05}))
    assert low["classes_not_lifted"] == ["path"] and low["class_sentences"][0].startswith("path: a B4 payload")


# ── O_ws (plan R0.6 items 4 and 4b) ─────────────────────────────────────────

import stage3_b4r_views as wv  # noqa: E402
import stage3_views as sv  # noqa: E402


def test_the_o_ws_prompt_carries_the_shared_harm_text_and_answer_format_verbatim():
    s = wv.system_prompt()
    assert s == wv.FRAMING + "\n\n" + sv.SHARED_HARM_TEXT + "\n\n" + sv.ANSWER_FORMAT
    assert wv.FRAMING.startswith(sv._OPEN)
    rec = wv.prompt_record()
    assert rec["prompt_version"] == "shared-harm/v1+b4r/v1:O_ws"
    assert rec["shared_harm_sha256"] == sv.SHARED_HARM_SHA256


def test_o_ws_on_a_two_document_group_shows_both_diffs_from_the_boundary():
    v7 = class_seed_mapping("v7")
    a1 = v7[("owncloud", dz.RG)].replace("- Eval-server port: 8088", "- Eval-server port: 8090")
    b1 = v7[("owncloud", dz.RT)].replace("- Eval-server port: 8088", "- Eval-server port: 8090")
    rows = [_w("2026-04-06T09:00:00Z", "a.one", dz.RG, a1), _w("2026-04-06T09:05:00Z", "a.one", dz.RT, b1),
            _w("2026-04-07T09:00:00Z", "b.two", dz.RG, a1 + "- Note: `n1`\n", task="t2")]
    days = ["2026-04-06", "2026-04-07"]
    units = wv.ws_units(rows, [[dz.RT, dz.RG]], days, v7, "x")
    by = {(u["boundary_index"], u["write_index"]): u for u in units}
    assert set(by) == {(0, 0), (0, 1), (0, 2), (1, 2)}
    u = by[(0, 0)]
    assert u["group"] == sorted([dz.RG, dz.RT]) and u["docs_changed"] == [dz.RG]
    assert "(no change in this window)" in u["packet"] and "+- Eval-server port: 8090" in u["packet"]
    assert by[(0, 1)]["docs_changed"] == sorted([dz.RG, dz.RT])
    assert by[(1, 2)]["docs_changed"] == [dz.RG] and "+- Note: `n1`" in by[(1, 2)]["packet"]
    assert by[(1, 2)]["boundary"] == "end of 2026-04-06" and "8090" not in by[(1, 2)]["packet"]
    assert by[(0, 2)]["packet"].index("owncloud:" + dz.RT) > by[(0, 2)]["packet"].index("Documents (2)")


@pytest.mark.skipif(not V2C.exists(), reason="prefix_rw_v2c not on disk")
def test_o_ws_with_singleton_groups_is_o_diff_on_prefix_rw_v2c():
    rows = sv.read_jsonl(V2C)
    days = sv.corpus_days(rows)
    base = class_seed_mapping("v6")
    paths = sv.class_doc_paths()
    tl = {p: sv.document_timeline(rows, p, base) for p in paths}
    od = sv.cumulative_diff_units(rows, paths, days, base, "s", timelines=tl)
    ws = wv.ws_units(rows, [[p] for p in paths], days, base, "s", timelines=tl)
    key = lambda u, p: (p, u["boundary_index"], u["write_index"])  # noqa: E731
    o = {key(u, u["path"]): u for u in od}
    w = {key(u, u["group"][0]): u for u in ws}
    assert set(o) == set(w) and len(o) == 254
    for k, u in o.items():
        assert (u["skip"] is None) == (w[k]["skip"] is None)
        if u["packet"]:
            diff_o = u["packet"].split(" chars):\n", 1)[1]
            diff_w = w[k]["packet"].split(" chars) ===\n", 1)[1]
            assert diff_o == diff_w
