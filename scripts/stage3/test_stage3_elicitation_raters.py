"""Tests for stage3_elicitation_raters.py (brief 30 Part 3: the rater sessions of the certification protocol, section 1:
fresh sessions under the rubric, one scale per session as brief 17 R0.3 ran them). Synthetic items only: the converter's
synthetic writer file, converted under its --synthetic path; no real item, no model call."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_elicitation_convert as cv  # noqa: E402
import stage3_elicitation_harness as hs  # noqa: E402
import stage3_elicitation_raters as rt  # noqa: E402

ROOT = HERE.parent.parent
RUBRIC = ROOT / "work/stage3/t1k-rater/rubric-passes-2.md"
DAY0 = ROOT / "work/stage3/t1k-rater/doc-states-day0.md"


@pytest.fixture()
def converted(tmp_path):
    sw = cv.synthetic_writer_file()
    sw["items"] = [x for x in sw["items"] if "documents" not in x]
    wf = tmp_path / "w.json"
    wf.write_text(json.dumps(sw), encoding="utf-8")
    out = tmp_path / "conv"
    out.mkdir()
    cv.convert_file(wf, cv.STATE_ONE, out_dir=out, writer="synthetic", synthetic=True)
    return out


def test_build_inputs_gives_one_blind_record_per_statement_and_a_key_that_joins_back(converted):
    stmts, key = rt.build_inputs(converted, salt="s")
    assert len(stmts) == 18 and len({s["statement_id"] for s in stmts}) == 18
    assert all(set(s) == {"statement_id", "document", "op", "anchor_or_region", "text"} for s in stmts)
    assert set(key) == {s["statement_id"] for s in stmts}
    by_item = {}
    for sid, k in key.items():
        by_item.setdefault(k["item_id"], []).append(k["writer_index"])
    assert len(by_item) == 6 and all(sorted(v) == [0, 1, 2] for v in by_item.values())


def test_build_inputs_is_deterministic_by_salt_and_changes_with_it(converted):
    a, ka = rt.build_inputs(converted, salt="s")
    b, kb = rt.build_inputs(converted, salt="s")
    c, kc = rt.build_inputs(converted, salt="t")
    assert json.dumps(a) == json.dumps(b) and ka == kb
    assert [s["statement_id"] for s in a] != [s["statement_id"] for s in c]


def test_statement_ids_do_not_reveal_the_item_ids(converted):
    stmts, key = rt.build_inputs(converted, salt="s")
    items = {k["item_id"] for k in key.values()}
    assert not any(s["statement_id"] in items for s in stmts)
    assert not any(i in json.dumps(stmts) for i in items)


def test_the_triples_scale_file_is_the_converters_stripped_triples_unchanged(converted):
    assert rt.triples_for(converted) == json.loads((converted / "stripped-triples.json").read_text(encoding="utf-8"))


@pytest.fixture()
def home_base():
    base = Path(tempfile.mkdtemp(prefix=".rater-test-", dir=Path.home()))
    yield base
    shutil.rmtree(base, ignore_errors=True)


def test_scale_folder_holds_exactly_the_rubric_the_documents_and_that_scales_file(converted, home_base):
    stmts, _ = rt.build_inputs(converted, salt="s")
    dest = home_base / "dev-s"
    man = rt.write_scale_folder(dest, "statements", stmts, rubric=RUBRIC, day0=DAY0, name="dev-statements-p1", round_no=1)
    assert sorted(p.name for p in dest.iterdir()) == ["doc-states-day0.md", "rubric.md", "stripped-statements.json"]
    assert man["files"]["rubric.md"].startswith("8354e3bf") and man["files"]["doc-states-day0.md"].startswith("d0f3fbae")
    assert rt.verify_folder(dest, man) == []
    (dest / "extra.txt").write_text("x")
    assert rt.verify_folder(dest, man) == ["extra.txt: present now, not in the manifest"]


def test_scale_folder_refuses_a_wrong_rubric_and_a_destination_inside_the_project(converted, home_base, tmp_path):
    stmts, _ = rt.build_inputs(converted, salt="s")
    bad = tmp_path / "rubric.md"
    bad.write_text("not the rubric")
    with pytest.raises(ValueError):
        rt.write_scale_folder(home_base / "x", "statements", stmts, rubric=bad, day0=DAY0, name="n", round_no=1)
    with pytest.raises(ValueError):
        rt.write_scale_folder(ROOT / "work" / "stage3" / "elicitation" / "part3" / "r", "statements", stmts, rubric=RUBRIC,
                              day0=DAY0, name="n", round_no=1)


def test_prompts_carry_the_counts_and_pass_the_rater_word_scan():
    import stage3_b3_rater_prep as prep
    for scale, n in (("statements", 60), ("triples", 20)):
        p = rt.prompt(scale, n)
        assert str(n) in p and "ratings.jsonl" in p
        scan = p
        for phrase in prep.VERBATIM_07S:       # 07s's own verb, exempt from the scan exactly as the B3 prep exempts it
            scan = scan.replace(phrase, "")
        assert prep.FORBIDDEN.search(scan) is None, prep.FORBIDDEN.search(scan)
        assert "/Users/" not in p and "work/stage3" not in p
    assert "2b" in rt.prompt("triples", 20) and "Stop before" in rt.prompt("statements", 60)


def _write(path, rows):
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def test_validate_ratings_accepts_a_clean_file_and_returns_scores_by_id(tmp_path):
    p = tmp_path / "r.jsonl"
    _write(p, [{"statement_id": "a", "score": 10, "reason": "fine"}, {"statement_id": "b", "score": 100, "reason": "x"}])
    scores, errs = rt.validate_ratings(p, "statement_id", ["a", "b"])
    assert errs == [] and scores == {"a": 10, "b": 100}


@pytest.mark.parametrize("rows,needle", [
    ([{"statement_id": "a", "score": 10, "reason": "r"}], "missing"),
    ([{"statement_id": "a", "score": 10, "reason": "r"}, {"statement_id": "b", "score": 1, "reason": "r"},
      {"statement_id": "c", "score": 1, "reason": "r"}], "extra"),
    ([{"statement_id": "a", "score": 10, "reason": "r"}, {"statement_id": "a", "score": 10, "reason": "r"},
      {"statement_id": "b", "score": 1, "reason": "r"}], "duplicate"),
    ([{"statement_id": "a", "score": 10.5, "reason": "r"}, {"statement_id": "b", "score": 1, "reason": "r"}], "score"),
    ([{"statement_id": "a", "score": 101, "reason": "r"}, {"statement_id": "b", "score": 1, "reason": "r"}], "score"),
    ([{"statement_id": "a", "score": True, "reason": "r"}, {"statement_id": "b", "score": 1, "reason": "r"}], "score"),
    ([{"statement_id": "a", "score": 1, "reason": " ".join(["w"] * 26)}, {"statement_id": "b", "score": 1, "reason": "r"}], "reason"),
])
def test_validate_ratings_names_what_is_wrong(tmp_path, rows, needle):
    p = tmp_path / "r.jsonl"
    _write(p, rows)
    _, errs = rt.validate_ratings(p, "statement_id", ["a", "b"])
    assert errs and any(needle in e for e in errs), errs


def test_validate_ratings_reports_a_missing_file_and_a_line_that_is_not_json(tmp_path):
    _, errs = rt.validate_ratings(tmp_path / "none.jsonl", "statement_id", ["a"])
    assert errs and "no ratings file" in errs[0]
    p = tmp_path / "r.jsonl"
    p.write_text("not json\n")
    _, errs = rt.validate_ratings(p, "statement_id", ["a"])
    assert any("not JSON" in e for e in errs)


def test_item_ratings_applies_gate_i_to_the_two_session_mean_per_statement_and_means_the_composition(converted):
    stmts, key = rt.build_inputs(converted, salt="s")
    ids = [s["statement_id"] for s in stmts]
    items = sorted({k["item_id"] for k in key.values()})
    low = {sid: 20 for sid in ids}
    s1 = dict(low)
    s2 = dict(low)
    loud_item = items[0]
    sid_loud = next(sid for sid, k in key.items() if k["item_id"] == loud_item and k["writer_index"] == 1)
    s1[sid_loud], s2[sid_loud] = 70, 52      # mean 61: above 60
    c1 = {i: 30 for i in items}
    c2 = {i: 50 for i in items}
    out = rt.item_ratings([s1, s2], [c1, c2], key, items)
    assert out["gate_i"][loud_item] is False and all(out["gate_i"][i] for i in items[1:])
    assert out["composition"][items[0]] == 40.0
    assert out["statement_means"][loud_item][1] == 61.0       # indexed by the writer's own statement index


def test_item_ratings_refuses_one_session_or_an_item_with_a_statement_unrated(converted):
    stmts, key = rt.build_inputs(converted, salt="s")
    items = sorted({k["item_id"] for k in key.values()})
    full = {s["statement_id"]: 10 for s in stmts}
    comp = {i: 10 for i in items}
    with pytest.raises(ValueError):
        rt.item_ratings([full], [comp], key, items)
    partial = dict(full)
    partial.pop(next(iter(partial)))
    with pytest.raises(ValueError):
        rt.item_ratings([full, partial], [comp, comp], key, items)


def test_the_folder_manifest_works_with_the_harness_audit(converted, home_base, tmp_path):
    stmts, _ = rt.build_inputs(converted, salt="s")
    dest = home_base / "dev-s" / "p1"
    man = rt.write_scale_folder(dest, "statements", stmts, rubric=RUBRIC, day0=DAY0, name="dev-statements-p1", round_no=1)
    mp = home_base / "manifest.json"
    mp.write_text(json.dumps(man), encoding="utf-8")
    trace = tmp_path / "t.paths"
    trace.write_text("\n".join(str(dest / f) for f in ("rubric.md", "doc-states-day0.md", "stripped-statements.json")) + "\n")
    assert hs.audit(trace, mp, format="paths")["verdict"] == "PASS"


def test_manifest_with_output_allows_exactly_the_raters_own_ratings_file(converted, home_base, tmp_path):
    stmts, _ = rt.build_inputs(converted, salt="s")
    dest = home_base / "dev-s" / "p1"
    man = rt.write_scale_folder(dest, "statements", stmts, rubric=RUBRIC, day0=DAY0, name="dev-statements-p1", round_no=1)
    with pytest.raises(ValueError):
        rt.manifest_with_output(man, dest)                 # no output yet: nothing to allow
    (dest / "ratings.jsonl").write_text('{"statement_id": "a", "score": 1, "reason": "r"}\n')
    man2 = rt.manifest_with_output(man, dest)
    assert "ratings.jsonl" in man2["files"] and "ratings.jsonl" not in man["files"], "the starting manifest is not changed"
    assert rt.verify_folder(dest, man2) == []
    mp = home_base / "manifest.json"
    mp.write_text(json.dumps(man2), encoding="utf-8")
    trace = tmp_path / "t.paths"
    trace.write_text("\n".join(str(dest / f) for f in ("rubric.md", "doc-states-day0.md", "stripped-statements.json", "ratings.jsonl")) + "\n")
    assert hs.audit(trace, mp, format="paths")["verdict"] == "PASS"
    (dest / "stray.txt").write_text("x")
    assert rt.verify_folder(dest, man2) == ["stray.txt: present now, not in the manifest"]


def _claude_stream(path: Path, reads: list[str], writes: list[str]) -> Path:
    rows = [{"type": "system", "subtype": "init"}]
    for p in reads:
        rows.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {"file_path": p}}]}})
    for p in writes:
        rows.append({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write", "input": {"file_path": p, "content": "x"}}]}})
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return path


def test_collect_session_validates_audits_and_writes_the_scores(converted, home_base, tmp_path):
    stmts, key = rt.build_inputs(converted, salt="s")
    dest = home_base / "dev-s" / "p1"
    man = rt.write_scale_folder(dest, "statements", stmts, rubric=RUBRIC, day0=DAY0, name="dev-statements-p1", round_no=1)
    (dest / "ratings.jsonl").write_text("\n".join(json.dumps({"statement_id": s["statement_id"], "score": 20, "reason": "r"}) for s in stmts) + "\n")
    stream = _claude_stream(tmp_path / "t.jsonl", [str(dest / "stripped-statements.json"), str(dest / "rubric.md"), str(dest / "doc-states-day0.md")],
                            [str(dest / "ratings.jsonl")])
    out = tmp_path / "out"
    res = rt.collect_session(dest, man, "statement_id", [s["statement_id"] for s in stmts], stream, out, "dev-statements-p1")
    assert res["validation_errors"] == [] and res["audit"] == "PASS" and res["n"] == len(stmts)
    assert json.loads((out / "ratings-dev-statements-p1.json").read_text())[stmts[0]["statement_id"]] == 20
    assert json.loads((out / "audit-dev-statements-p1.json").read_text())["verdict"] == "PASS"


def test_collect_session_fails_the_audit_when_the_session_opened_the_project_and_still_returns_the_scores(converted, home_base, tmp_path):
    stmts, _ = rt.build_inputs(converted, salt="s")
    dest = home_base / "dev-s" / "p1"
    man = rt.write_scale_folder(dest, "statements", stmts, rubric=RUBRIC, day0=DAY0, name="dev-statements-p1", round_no=1)
    (dest / "ratings.jsonl").write_text("\n".join(json.dumps({"statement_id": s["statement_id"], "score": 20, "reason": "r"}) for s in stmts) + "\n")
    stream = _claude_stream(tmp_path / "t.jsonl", [str(ROOT / "STATUS.md")], [str(dest / "ratings.jsonl")])
    res = rt.collect_session(dest, man, "statement_id", [s["statement_id"] for s in stmts], stream, tmp_path / "out", "dev-statements-p1")
    assert res["audit"] == "FAIL" and res["validation_errors"] == []


def test_collect_session_reports_validation_errors_and_writes_no_scores(converted, home_base, tmp_path):
    stmts, _ = rt.build_inputs(converted, salt="s")
    dest = home_base / "dev-s" / "p1"
    man = rt.write_scale_folder(dest, "statements", stmts, rubric=RUBRIC, day0=DAY0, name="dev-statements-p1", round_no=1)
    (dest / "ratings.jsonl").write_text(json.dumps({"statement_id": stmts[0]["statement_id"], "score": 20, "reason": "r"}) + "\n")
    stream = _claude_stream(tmp_path / "t.jsonl", [], [str(dest / "ratings.jsonl")])
    res = rt.collect_session(dest, man, "statement_id", [s["statement_id"] for s in stmts], stream, tmp_path / "out", "dev-statements-p1")
    assert res["validation_errors"] and not (tmp_path / "out" / "ratings-dev-statements-p1.json").exists()


def test_single_session_means_index_each_items_ratings_by_the_writers_statement_index(converted):
    stmts, key = rt.build_inputs(converted, salt="s")
    scores = {sid: 5 * (k["writer_index"] + 1) for sid, k in key.items()}
    m = rt.single_session_means(scores, key)
    assert set(m) == {k["item_id"] for k in key.values()}
    assert all(v == [5.0, 10.0, 15.0] for v in m.values())
    with pytest.raises(ValueError):
        rt.single_session_means({next(iter(scores)): 1}, key)


def test_prepare_builds_the_blue_key_the_prompts_and_one_folder_per_scale_and_pass(converted, tmp_path):
    part3 = tmp_path / "part3"
    cdir = part3 / "round-2" / "w" / "converted"
    shutil.copytree(converted, cdir)
    home = tmp_path / "raters"
    out = rt.prepare(part3, "w", 2, "cert", passes=(1, 2), rater_home=home, rubric=RUBRIC, day0=DAY0, writers_root=tmp_path / "writers")
    O = part3 / "raters" / "w-r2-cert"
    assert sorted(p.name for p in home.iterdir()) == sorted(f"w-r2-cert-{s}-p{p}" for s in ("statements", "triples") for p in (1, 2))
    assert (O / "statement-key.json").is_file() and (O / "prompt-statements.txt").is_file() and (O / "prompt-triples.txt").is_file()
    for s in ("statements", "triples"):
        for p in (1, 2):
            assert (O / f"manifest-{s}-p{p}.json").is_file() and (O / f"settings-{s}-p{p}.json").is_file()
            assert sorted(x.name for x in (home / f"w-r2-cert-{s}-p{p}").iterdir()) == sorted(["rubric.md", "doc-states-day0.md", rt.SCALES[s]])
    assert out == {"statements": 18, "triples": 6, "folders": 4}
    # the folders of one scale hold identical bytes (the two passes rate the same file)
    a = (home / "w-r2-cert-statements-p1" / "stripped-statements.json").read_bytes()
    assert a == (home / "w-r2-cert-statements-p2" / "stripped-statements.json").read_bytes()
    with pytest.raises(ValueError):
        rt.prepare(part3, "w", 2, "cert", passes=(1, 2), rater_home=home, rubric=RUBRIC, day0=DAY0, writers_root=tmp_path / "writers")   # folders exist
