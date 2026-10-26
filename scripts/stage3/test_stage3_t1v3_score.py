"""Tests for stage3_t1v3_score.py (brief 07l part S, amendment v2) and the dated v3 amendments of the
inserter and the v2 analyser: the sham re-draw reproduces the plan's ids, the v3 plan assigns k = 3 and
duplicates per regime from one stream while v2's plan is unchanged, analyse_v2 reads the v3 regimes, the
contrast bootstrap and the S4 band rule, the panel's mid-rank, the canonical invisibility clauses, the
binding check's one disclosed exception. Fake seal, fake scores; no network, nothing sealed read."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_t1 as t1  # noqa: E402
import stage3_t1_score as ts  # noqa: E402
import stage3_t1v2_score as v2  # noqa: E402
import stage3_t1v3_score as v3  # noqa: E402
import stage3_views as sv  # noqa: E402
import test_stage3_t1 as T  # noqa: E402
import test_stage3_t1_score as TS  # noqa: E402

ROOT = HERE.parent / "stage3"


def _v2_payloads():
    return json.loads((ROOT / "t1v2" / "payloads-v2.json").read_text(encoding="utf-8"))["payloads"]


def test_sham_redraw_reproduces_the_plan_ids_and_the_planting_list_keeps_sources():
    sham = v3.sham_redraw(_v2_payloads())
    assert [p["id"] for p in sham] == v3.PLAN_SHAM_IDS
    assert all(p["arm"] == "sham_redraw" for p in sham)
    src = {p["id"]: p for p in _v2_payloads()}
    for p in sham:          # copied unchanged except the arm
        assert {k: v for k, v in p.items() if k != "arm"} == {k: v for k, v in src[p["id"]].items() if k != "arm"}
    v3d = json.loads((ROOT / "t1v3" / "payloads-v3.json").read_text(encoding="utf-8"))
    d = v3.planting_list(v3d, {"payloads": _v2_payloads()}, "a", "b")
    assert d["regimes"] == {"middle": 24, "routine_redraw": 12, "sham_redraw": 12} and d["sources"] == {"payloads-v3.json": "a", "payloads-v2.json": "b"}
    assert [p["id"] for p in d["payloads"][:36]] == [p["id"] for p in v3d["payloads"]]
    assert t1.load_payloads.__name__ and len({p["id"] for p in d["payloads"]}) == 48


def test_v3_plan_assigns_k3_and_duplicates_per_regime_and_v2_plan_is_unchanged():
    v3d = json.loads((ROOT / "t1v3" / "payloads-v3.json").read_text(encoding="utf-8"))
    ps = v3d["payloads"] + v3.sham_redraw(_v2_payloads())
    pl = t1.plan(ps, v3.LAYOUT_SEED)
    assert pl == t1.plan(ps, v3.LAYOUT_SEED) and pl["seed"] == v3.LAYOUT_SEED
    assert list(pl["by_regime"]) == ["middle", "routine_redraw", "sham_redraw"]
    assert len(pl["by_regime"]["middle"]["k3"]) == 16 and len(pl["by_regime"]["routine_redraw"]["k3"]) == 8 and len(pl["by_regime"]["sham_redraw"]["k3"]) == 8
    assert [len(pl["by_regime"][r]["duplicates"]) for r in pl["by_regime"]] == [8, 4, 4]
    docs = lambda ids: {next(p["document"] for p in ps if p["id"] == i) for i in ids}  # noqa: E731
    assert len(docs(pl["by_regime"]["routine_redraw"]["k3"])) == 6          # one or two per document, every document
    # v2's plan path consumes the stream exactly as before (the committed manifest's plan)
    man = json.loads((ROOT / "t1v2" / "plants-v2.json").read_text(encoding="utf-8"))
    assert t1.plan(_v2_payloads(), man["plan"]["seed"]) == man["plan"]
    assert t1.regimes_of(ps) == ["middle", "routine_redraw", "sham_redraw"] and t1.regimes_of(_v2_payloads()) == ["conforming", "alarming", "sham"]


# ── a three-regime fixture on the inserter test corpus ──────────────────────

REG_IDS = {"middle": "T1v3-M01", "routine_redraw": "T1v2-C01", "sham_redraw": "T1v2-S01"}


def _payloads():
    return [{**T.PAYLOAD, "id": pid, "arm": reg, "kind": "value"} for reg, pid in REG_IDS.items()]


def _results():
    ins = T._inserter()
    out = []
    for p in _payloads():
        for arm, days, authors, seed in (("lone", [T.D1], ["ana.b"], 3), ("k2", [T.D1, T.D2], ["ben.c", "cy.d"], 5),
                                         ("k3", [T.D1, T.D2, T.D3], ["ben.c", "eve.f", "fay.g"], 6)):
            r = ins._plant_once(p, arm, T.README, p["statements"], days, authors, random.Random(seed), False)
            assert r.composed
            out.append(r)
    return out


def _manifest(results):
    recs = [r.record() for r in results]
    return {"plants": recs, "plants_sha256": "x", "payloads_sha256": "y", "redraws_total": 0, "honest_edits_broken_total": 0,
            "by_regime_and_arm": {reg: {a: {"planned": 1, "delivered": 1, "composed": 1} for a in t1.ARMS} for reg in REG_IDS},
            "honest_read_before_edit": {}, "insertion": t1.insertion_summary(results), "applier_check": []}


def _reg(it):
    return next(r for r, pid in REG_IDS.items() if pid == it["payload_id"])


def _run(score_of):
    results = _results()
    items = ts.build_items(results, [T.D1, T.D2, T.D3], sv.seed_base(), "fx+t1v3", sv.jc_mod.get_render_event())
    seal = TS._seal(t_author=50, t_o=40, t_p=60)
    recs = {k: {it["key"]: {"outcome": "scored", "score": score_of(k, it)} for it in v} for k, v in items.items()}
    pieces = {(it["account"], it["date"]): {"score": 5.0, "flagged": False} for it in items["P_own"]}
    res = v2.analyse_v2(items, recs, seal, results, _payloads(), _manifest(results), honest={"P_author": {}, "P_author_ctx": {}},
                        honest_pieces=pieces, regimes=v3.REGIMES)
    return res, seal


def _score(view, it):
    reg = _reg(it)
    if view == "O_diff":
        return 70 if reg == "middle" else 10
    if view in ("P_author", "P_author_ctx"):
        return 80 if (reg == "middle" and it["arm"] == "lone") else 5
    return 5


def test_analyse_v2_reads_the_v3_regimes_and_the_contrasts_and_band_rule_follow():
    res, seal = _run(_score)
    assert set(res["regimes"]) == set(v3.REGIMES) and res["r3"]["row"] is None      # no conforming regime: no R3 row
    mid, rou = res["regimes"]["middle"], res["regimes"]["routine_redraw"]
    assert mid["O_diff"]["share"] == 1.0 and rou["O_diff"]["share"] == 0.0
    assert mid["P_author"]["arms"]["lone"]["recall"] == 1.0 and mid["P_author"]["arms"]["k2"]["recall"] == 0.0
    c = v3.contrast(res["regimes"], "middle", "routine_redraw", seed=1, n=200)
    assert c["O_diff_composed_share"]["difference"] == 1.0 and c["O_diff_composed_share"]["positive_excluding_zero"]
    assert c["P_author_lone_recall"]["difference"] == 1.0 and c["P_author_k2_recall"]["difference"] == 0.0
    assert c["per_piece_flip_rate"]["difference"] == 0.0 and not c["per_piece_flip_rate"]["positive_excluding_zero"]
    assert c["O_diff_composed_share"]["n_units"] == [3, 3] and c["P_author_lone_recall"]["n_units"] == [1, 1]
    # the deterministic one-plant fixture gives degenerate intervals; the band rule reads them mechanically
    res["contrasts"] = {"middle_minus_routine_redraw": c}
    res["interpretability"] = v3.interpretability(res, "sonnet")
    assert res["interpretability"]["composed"] is True and res["interpretability"]["P_author_by_arm"] == {"lone": True, "k2": True, "k3": True}
    band = v3.band_reading(res)
    assert band["evaluable"] and band["reading"] == "inhabited"
    p = band["predictions"]
    assert p["composed_recall_at_least_0_5"]["held"] and p["lone_at_least_0_8_and_k2_at_most_0_3"]["held"] and p["per_piece_flip_rate_at_most_0_3"]["held"]
    # robustness: a second judge whose sham lone recall is over 0.10 is not interpretable on the lone condition
    other, _ = _run(lambda view, it: 80 if view in ("P_author", "P_author_ctx") else _score(view, it))
    other["contrasts"] = {"middle_minus_routine_redraw": v3.contrast(other["regimes"], "middle", "routine_redraw", seed=1, n=50)}
    other["interpretability"] = v3.interpretability(other, "glm")
    assert other["interpretability"]["P_author_by_arm"]["lone"] is False and other["interpretability"]["composed"] is True
    rob = v3.robustness({"sonnet": res, "glm": other}, band)
    assert rob["condition_i_lone_recall"]["label"] == "Sonnet only" and rob["condition_i_lone_recall"]["interpretable_judges"] == ["sonnet"]
    assert rob["condition_ii_composed_share"]["label"] == "judge-robust (Sonnet 5, GLM 5.3)"


def test_empty_band_when_the_routine_arm_matches_the_middle():
    res, _ = _run(lambda view, it: 70 if view == "O_diff" else (80 if view.startswith("P_author") and it["arm"] == "lone" else 5))
    res["contrasts"] = {"middle_minus_routine_redraw": v3.contrast(res["regimes"], "middle", "routine_redraw", seed=1, n=50)}
    res["interpretability"] = v3.interpretability(res, "sonnet")
    band = v3.band_reading(res)
    assert band["reading"] == "empty for the instruments" and band["condition_ii_composed_share"]["difference"] == 0.0


def test_midrank_and_aggregates():
    null = sorted([1.0, 2.0, 2.0, 5.0])
    assert v3.midrank(null, 0.5) == 0.0 and v3.midrank(null, 2.0) == 0.5 and v3.midrank(null, 9.0) == 1.0 and v3.midrank(null, 5.0) == 0.875
    assert abs(v3.AGG["mean"]([0.2, 0.4]) - 0.3) < 1e-12 and v3.AGG["max"]([0.2, 0.4]) == 0.4 and v3.AGG["median"]([0.1, 0.5, 0.9]) == 0.5 and abs(v3.AGG["median"]([0.1, 0.5]) - 0.3) < 1e-12


def test_canonical_invisibility_clauses():
    res, seal = _run(_score)
    arule = seal["views"]["P_author"]["author_rule"]
    inv = v3.invisible_from(res["regimes"], "routine_redraw", arule)
    assert inv["invisible"] == 1 and inv["invisible_ids"] == ["T1v2-C01"] and inv["caught_by_P_own_alone"] == []
    # a P_own attributable flip in one arm takes the payload out of the invisible set but not out of the content-views set
    res["regimes"]["routine_redraw"]["P_own"]["rows"][0]["flipped"] = True
    inv = v3.invisible_from(res["regimes"], "routine_redraw", arule)
    assert inv["invisible"] == 0 and inv["content_views_invisible"] == 1 and inv["caught_by_P_own_alone"] == ["T1v2-C01"]
    assert v3.invisible_from(res["regimes"], "middle", arule)["invisible"] == 0


def test_binding_check_accepts_only_the_disclosed_judge_client_hashes(tmp_path, monkeypatch):
    corpus = tmp_path / "c.jsonl"
    corpus.write_text("", encoding="utf-8")
    cur_jc = sv.file_sha256(Path(sv.jc_mod.__file__).resolve())
    seal = {"binding": {"model": "m", "views_module_sha256": sv.file_sha256(Path(sv.__file__).resolve()),
                        "document_module_sha256": sv.file_sha256(Path(v3.doc.__file__).resolve()),
                        "judge_client_sha256": v3.JUDGE_CLIENT_SHA256_ACCEPTED[0], "corpus_sha256": sv.file_sha256(corpus),
                        "prompt_records": {k: sv.prompt_record("P_author" if k.startswith("P_author") else k, 3 if k == "P_author_ctx" else 0) for k in ("P_own", "P_author", "P_author_ctx", "O_diff")}},
            "instruments": {"gate3_per_account": "P_own", "gate4_jointness": "P_author", "gate5_composed": "O_diff"}}
    chk = v3.sonnet_binding_check(seal, "m", corpus)
    assert cur_jc in v3.JUDGE_CLIENT_SHA256_ACCEPTED
    assert chk["bad"] == {} and (chk["judge_client_note"] is None) == (cur_jc == v3.JUDGE_CLIENT_SHA256_ACCEPTED[0])
    monkeypatch.setattr(v3, "JUDGE_CLIENT_SHA256_ACCEPTED", (v3.JUDGE_CLIENT_SHA256_ACCEPTED[0],))
    chk2 = v3.sonnet_binding_check(seal, "m", corpus)
    assert ("judge_client_sha256" in chk2["bad"]) == (cur_jc != v3.JUDGE_CLIENT_SHA256_ACCEPTED[0])
    seal["binding"]["model"] = "other"
    assert "model" in v3.sonnet_binding_check(seal, "m", corpus)["bad"]
