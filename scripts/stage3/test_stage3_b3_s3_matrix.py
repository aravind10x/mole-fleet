"""Tests for stage3_b3_s3_matrix.py (brief 33 A2): the analysis matrix is built from hash-verified inputs only, holds every
net item by opaque id with numbers, ids and population names and no item text, reproduces plan section 1.2's table
(means, SD, IQR, writer and document counts, pooled strata) from `s1-populations-v0.json` and Part 3's Step 0, and its
rater fields equal brief 25's stratum file for the candidates.

Run: cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_s3_matrix.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_s3_matrix as mx  # noqa: E402

ROOT = HERE.parents[1]
CLASS_DOCS = {"/shared/alignment/redteam-checklist.md", "/shared/capabilities/finetune-guide.md", "/shared/eval/release-gate-runbook.md",
              "/shared/infra/training-pipeline/README.md", "/shared/onboarding/engineering-setup.md", "/shared/ops/oncall-runbook.md"}
FORBIDDEN_KEYS = {"text", "anchor", "replace", "region", "justification", "composed_effect", "statements", "reason", "rationale"}


@pytest.fixture(scope="module")
def matrix():
    return mx.build(ROOT)


def test_every_input_is_verified_by_hash_before_it_is_read(tmp_path, monkeypatch):
    bad = dict(mx.INPUT_SHA256)
    k = next(iter(bad))
    bad[k] = "0" * 64
    monkeypatch.setattr(mx, "INPUT_SHA256", bad)
    with pytest.raises(SystemExit, match="sha256"):
        mx.build(ROOT)


def test_the_pinned_inputs_are_the_plan_and_power_simulation_files():
    paths = set(mx.INPUT_SHA256)
    assert {"work/stage3/b3/rater/key-b3.json", "work/stage3/b3/rater/ratings-b3-statements-p1.jsonl",
            "work/stage3/b3/rater/ratings-b3-statements-p2.jsonl", "work/stage3/b3/rater/ratings-b3-triples-p1.jsonl",
            "work/stage3/b3/rater/ratings-b3-triples-p2.jsonl", "work/stage3/b3/checks-b3-sonnet55-rerun.json",
            "work/stage3/b3/checks-b3-glm53.json"} <= paths
    assert {"work/stage3/b3/comprehension/stratum-v0.json", "work/stage3/b3/s1-populations-v0.json",
            "work/stage3/b3/inserter-dry-run-v1.json"} <= paths
    pinned = json.loads((ROOT / "work/stage3/b3/power-simulation-v3-inputs.json").read_text())["inputs_sha256"]
    for p in paths:
        if p in pinned:
            assert mx.INPUT_SHA256[p] == pinned[p]
    assert mx.INPUT_SHA256["work/stage3/b3/comprehension/stratum-v0.json"].startswith("6113bd8d")
    assert mx.INPUT_SHA256["work/stage3/b3/s1-populations-v0.json"].startswith("f17e7a72")
    assert mx.INPUT_SHA256["work/stage3/b3/inserter-dry-run-v1.json"].startswith("02138931")


def test_every_net_item_is_present_with_its_regime_and_nothing_else(matrix):
    items = matrix["items"]
    assert Counter(r["regime"] for r in items.values()) == {"candidate": 73, "control": 21, "sham": 22}
    s1 = json.loads((ROOT / "work/stage3/b3/s1-populations-v0.json").read_text())
    drops = set(s1["drops"]["pair"]["ids"])
    assert not (set(items) & drops)
    for pop, name in (("full", "full"), ("controls", "controls"), ("sham", "sham")):
        assert sorted(i for i, r in items.items() if name in r["populations"]) == s1["populations"][pop]["net_pair"]["ids"]


def test_the_matrix_holds_numbers_ids_and_names_only(matrix):
    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                assert k not in FORBIDDEN_KEYS, path + "/" + k
                walk(v, path + "/" + str(k))
        elif isinstance(o, list):
            for v in o:
                walk(v, path + "[]")
        elif isinstance(o, str):
            assert len(o) <= 64 or o.startswith("/shared/"), (path, o[:40])
    walk({k: v for k, v in matrix.items() if k != "conventions"})   # the conventions are this file's own documentation
    for r in matrix["items"].values():
        assert r["document"] in CLASS_DOCS and r["writer"] in ("sonnet55", "glm53", "t1v2")


def test_population_memberships_equal_s1s_net_ids(matrix):
    s1 = json.loads((ROOT / "work/stage3/b3/s1-populations-v0.json").read_text())
    for pop in mx.POPULATIONS:
        got = sorted(i for i, r in matrix["items"].items() if pop in r["populations"])
        assert got == s1["populations"][pop]["net_pair"]["ids"], pop
        assert matrix["populations"][pop]["n"] == len(got)
        assert matrix["populations"][pop]["ids_sha256"] == s1["populations"][pop]["net_pair"]["ids_sha256"]


def test_section_1_2_reproduces_s1_and_part_3s_step_0(matrix):
    s1 = json.loads((ROOT / "work/stage3/b3/s1-populations-v0.json").read_text())
    for pop in mx.POPULATIONS:
        got, want = matrix["section_1_2"][pop], s1["populations"][pop]["net_pair"]
        assert got["n"] == want["n"] and got["by_writer"] == want["by_writer"] and got["document_counts"] == want["document_counts"]
        assert got["n_documents"] == want["n_documents"] and got["strata_pooled"] == want["strata_pooled"]
        if want.get("composition"):
            assert got["mean"] == pytest.approx(want["composition"]["mean"], abs=1e-9)
            assert got["sd"] == pytest.approx(want["composition"]["sd"], abs=1e-9)
            assert got["iqr"] == pytest.approx(want["composition"]["iqr"], abs=1e-9)
    v3c = json.loads((ROOT / "work/stage3/b3/power-simulation-v3c.json").read_text())["step0"]["populations"]
    for pop in ("full", "stratum", "subset", "strict"):
        assert matrix["section_1_2"][pop]["mean"] == pytest.approx(v3c[pop]["composition_mean"], abs=1e-3)
        assert matrix["section_1_2"][pop]["sd"] == pytest.approx(v3c[pop]["composition_sd"], abs=1e-3)
        assert matrix["section_1_2"][pop]["n"] == v3c[pop]["n"]
    assert matrix["section_1_2"]["full"]["iqr"] == [47.5, 66.5]


def test_candidate_rater_fields_equal_brief_25s_stratum_file(matrix):
    st = json.loads((ROOT / "work/stage3/b3/comprehension/stratum-v0.json").read_text())["items"]
    n = 0
    for i, r in matrix["items"].items():
        if r["regime"] != "candidate":
            continue
        s = st[i]
        assert r["composition"] == pytest.approx(s["composition"], abs=1e-9)
        assert r["composition_p1"] == pytest.approx(s["composition_p1"]) and r["composition_p2"] == pytest.approx(s["composition_p2"])
        assert r["line_max"] == pytest.approx(s["rater_top_line"]) and r["top_two_gap"] == pytest.approx(s["rater_top_two_gap"])
        assert r["replace_share"] == pytest.approx(s["replace_share"])
        assert r["anchors_resolve"] == s["anchors_resolve"] and r["membership"] == s["membership"] and r["writer"] == s["writer"]
        for rd in ("kimi", "sol"):
            assert r["readers"][rd]["D_part_mean"] == pytest.approx(s["readers"][rd]["D_part_mean"])
            assert r["readers"][rd]["D_whole_mean"] == pytest.approx(s["readers"][rd]["D_whole_mean"])
        assert len(r["line_scores"]) == 3 and max(r["line_scores"]) == pytest.approx(r["line_max"])
        assert r["composition"] == pytest.approx((r["composition_p1"] + r["composition_p2"]) / 2)
        n += 1
    assert n == 73


def test_control_items_carry_composition_lines_and_replace_share(matrix):
    ctrl = [r for r in matrix["items"].values() if r["regime"] == "control"]
    assert len(ctrl) == 21
    for r in ctrl:
        assert len(r["line_scores"]) == 3 and 0 <= r["composition"] <= 100 and 0 <= r["replace_share"] <= 1
        assert r["top_two_gap"] == pytest.approx(sorted(r["line_scores"])[-1] - sorted(r["line_scores"])[-2])
        assert "readers" in r
    sham = [r for r in matrix["items"].values() if r["regime"] == "sham"]
    assert len(sham) == 22 and all(r["composition"] is None and r["line_scores"] is None for r in sham)


def test_replace_share_from_the_payload_ops_equals_the_checks_method_on_the_candidates(matrix):
    sys.path.insert(0, str(HERE))
    import stage3_b3_power_v3 as pv
    key = json.loads((ROOT / "work/stage3/b3/rater/key-b3.json").read_text())["triples"]
    stim = {(t["writer"], t["id"]): t for t in pv.load_stimuli(ROOT)}
    for i, r in matrix["items"].items():
        if r["regime"] == "candidate":
            k = key[i]
            assert r["replace_share"] == pytest.approx(sum(stim[(k["writer"], k["id"])]["replace"]) / 3)


def test_pooled_strata_follow_a6_17_3_on_the_stratum_populations(matrix):
    for pop in ("stratum", "subset", "strict", "subset_and_strict", "certified", "preview_credited", "preview_illegible", "unresolved_stratum"):
        strata = matrix["pooled_strata"][pop]
        ids = [i for i, r in matrix["items"].items() if pop in r["populations"]]
        docs = Counter(matrix["items"][i]["document"] for i in ids)
        for d, c in docs.items():
            assert (strata[d] == "pooled") == (c < 4)
        sizes = sorted(Counter(strata[matrix["items"][i]["document"]] for i in ids).values(), reverse=True)
        assert sizes == matrix["section_1_2"][pop]["strata_pooled"]
    assert "full" not in matrix["pooled_strata"]


def test_the_written_file_is_deterministic(tmp_path):
    a = mx.render(mx.build(ROOT))
    b = mx.render(mx.build(ROOT))
    assert a == b and hashlib.sha256(a.encode()).hexdigest() == hashlib.sha256(b.encode()).hexdigest()
    d = json.loads(a)
    assert d["version"] == mx.VERSION and set(d["inputs_sha256"]) == set(mx.INPUT_SHA256)
