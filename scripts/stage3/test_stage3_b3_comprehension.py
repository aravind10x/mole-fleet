"""Offline tests for stage3_b3_comprehension (brief 25): synthetic fixtures only, no item file, no network.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_comprehension.py
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_comprehension as bc  # noqa: E402


# ── C1: the model ──

def test_rule_prob_every_majority_and_mean_on_known_cases():
    th = [0.7, 0.1, 0.2]
    assert bc.rule_prob(th, 2, ("every", None)) == pytest.approx(0.49)
    assert bc.rule_prob(th, 2, ("majority", None)) == pytest.approx(0.49)          # strict majority of two is both
    assert bc.rule_prob(th, 3, ("majority", None)) == pytest.approx(3 * 0.7 ** 2 * 0.3 + 0.7 ** 3)
    # mean <= 0.25 at k = 2: (0, 0) or (0, 0.5) in either order
    assert bc.rule_prob(th, 2, ("mean", 0.25)) == pytest.approx(0.49 + 2 * 0.7 * 0.1)
    # mean <= 0.5 at k = 2: adds (0.5, 0.5) and (0, 1) in either order
    assert bc.rule_prob(th, 2, ("mean", 0.5)) == pytest.approx(0.49 + 2 * 0.07 + 0.01 + 2 * 0.14)
    assert bc.rule_prob(th, 4, ("mean", 1.0)) == pytest.approx(1.0)
    assert bc.rule_prob([1.0, 0.0, 0.0], 3, ("every", None)) == pytest.approx(1.0)


def test_mean_one_third_at_three_samples_includes_the_boundary():
    th = [0.5, 0.25, 0.25]
    # (0, 0, 1) has mean exactly 1/3 and is included; (0, 0.5, 0.5) too
    p = bc.rule_prob(th, 3, ("mean", 1 / 3))
    want = 0.5 ** 3 + 3 * 0.5 ** 2 * 0.25 + 3 * 0.5 ** 2 * 0.25 + 3 * 0.5 * 0.25 ** 2
    assert p == pytest.approx(want)


def _synthetic(n, pi, theta, rng, retest_share=0.25):
    data = []
    for _ in range(n):
        z = "Q" if rng.random() < pi else "N"
        row = {}
        reps = 2 if rng.random() < retest_share else 1
        for f, t in theta.items():
            row[f] = [rng.choices((0, 1, 2), weights=t[z])[0] for _ in range(reps)]
        data.append(row)
    return data


def test_em_recovers_well_separated_classes_and_orients_q_on_the_anchor():
    rng = random.Random(7)
    theta = {"kimi": {"Q": [0.95, 0.03, 0.02], "N": [0.1, 0.1, 0.8]},
             "sol": {"Q": [0.8, 0.1, 0.1], "N": [0.3, 0.1, 0.6]},
             "sonnet55": {"Q": [0.9, 0.05, 0.05], "N": [0.15, 0.05, 0.8]}}
    data = _synthetic(1500, 0.35, theta, rng)
    fit = bc.lca_fit(data, starts=6, rng=random.Random(1))
    assert fit["pi_quiet"] == pytest.approx(0.35, abs=0.04)
    for f in theta:
        for z in ("Q", "N"):
            assert fit["theta"][f][z][0] == pytest.approx(theta[f][z][0], abs=0.05)
    assert fit["theta"]["kimi"]["Q"][0] > fit["theta"]["kimi"]["N"][0]


def test_em_label_is_stable_when_the_start_lands_on_the_swapped_mode():
    rng = random.Random(3)
    theta = {"kimi": {"Q": [0.9, 0.05, 0.05], "N": [0.1, 0.1, 0.8]},
             "sol": {"Q": [0.7, 0.1, 0.2], "N": [0.4, 0.1, 0.5]},
             "sonnet55": {"Q": [0.9, 0.05, 0.05], "N": [0.2, 0.1, 0.7]}}
    data = _synthetic(400, 0.6, theta, rng)
    fits = [bc.lca_fit(data, starts=3, rng=random.Random(s)) for s in range(5)]
    for fit in fits:
        assert fit["theta"]["kimi"]["Q"][0] > 0.7 and fit["theta"]["kimi"]["N"][0] < 0.3
        assert fit["pi_quiet"] == pytest.approx(fits[0]["pi_quiet"], abs=1e-4)


def test_smoothing_keeps_rates_off_the_boundary():
    data = [{"kimi": [0, 0], "sol": [0], "sonnet55": [0]} for _ in range(5)] + [{"kimi": [2], "sol": [2], "sonnet55": [2]} for _ in range(5)]
    fit = bc.lca_fit(data, starts=4, rng=random.Random(0))
    assert 0 < fit["theta"]["kimi"]["Q"][2] < 0.2 and 0 < fit["theta"]["kimi"]["N"][0] < 0.2
    mle = bc.lca_fit(data, smooth=0.0, starts=4, rng=random.Random(0))
    assert mle["theta"]["kimi"]["Q"][0] == pytest.approx(1.0, abs=1e-6)


def test_operating_characteristics_multiply_across_readers():
    fit = {"pi_quiet": 0.5, "theta": {"kimi": {"Q": [0.9, 0.05, 0.05], "N": [0.2, 0.1, 0.7]},
                                      "sol": {"Q": [0.6, 0.2, 0.2], "N": [0.3, 0.2, 0.5]}}}
    oc = bc.operating(fit, 2, {"kimi": ("every", None), "sol": ("mean", 0.5)})
    assert oc["quiet"] == pytest.approx(0.81 * bc.rule_prob([0.6, 0.2, 0.2], 2, ("mean", 0.5)))
    assert oc["nonquiet"] == pytest.approx(0.04 * bc.rule_prob([0.3, 0.2, 0.5], 2, ("mean", 0.5)))


def _row(k, ri, q, nq):
    return {"k": k, "rule": bc.rule_name(bc.SOL_RULES[ri]), "rule_index": ri, "quiet": q, "nonquiet": nq}


def test_choose_prefers_the_smallest_feasible_k_then_the_highest_first_figure():
    t = [_row(2, 0, 0.79, 0.01), _row(2, 3, 0.85, 0.09), _row(2, 1, 0.82, 0.05), _row(3, 3, 0.95, 0.01)]
    c = bc.choose(t)
    assert c["feasible"] and c["k"] == 2 and c["rule_index"] == 3


def test_choose_falls_back_to_the_smallest_shortfall():
    t = [_row(2, 0, 0.6, 0.02), _row(2, 3, 0.75, 0.12), _row(3, 3, 0.75, 0.12), _row(4, 2, 0.5, 0.0)]
    c = bc.choose(t)
    assert not c["feasible"] and c["k"] == 2 and c["rule_index"] == 3
    assert bc.shortfall(0.75, 0.12) == pytest.approx(0.07)


def _instrument(values):
    """values: {item: {reader: (r0, r1 or None)}} -> an instrument-v0.json-like structure."""
    pf = {f: {"items": {}} for f in bc.PLAN_READERS}
    for i, per in values.items():
        for f in bc.PLAN_READERS:
            r0, r1 = per[f]
            rec = {"regime": "v2_conforming", "r0": {"D_part": r0}}
            if r1 is not None or per.get("retest"):
                rec["r1"] = {"D_part": r1}
            pf[f]["items"][i] = rec
    pf["kimi"]["items"]["n0"] = {"regime": "honest_random", "r0": {"D_part": 0.0}}
    for f in ("sol", "sonnet55"):
        pf[f]["items"]["n0"] = {"regime": "honest_random", "r0": {"D_part": 0.0}}
    return {"per_family": pf}


def test_plan_data_counts_flips_and_the_proxy_on_test_items_only():
    vals = {"a": {"kimi": (0.0, 0.0), "sol": (0.0, 0.5), "sonnet55": (None, 0.0), "retest": True},
            "b": {"kimi": (1.0, 0.0), "sol": (0.0, 0.0), "sonnet55": (1.0, 1.0)},
            "c": {"kimi": (0.5, None), "sol": (1.0, None), "sonnet55": (0.0, None)}}
    data, counts = bc.plan_data(_instrument(vals))
    assert counts["n_test_items"] == 3
    assert counts["flips"] == {"kimi": 1, "sol": 1, "sonnet55": 0}
    assert counts["retest_pairs"] == {"kimi": 2, "sol": 2, "sonnet55": 1}
    assert counts["proxy_both_quiet_r0"] == 1
    assert counts["quiet_r0"] == {"kimi": 1, "sol": 2, "sonnet55": 1} and counts["n_r0"]["sonnet55"] == 2
    assert data[0]["sonnet55"] == [0] and data[0]["sol"] == [0, 1] and data[2]["kimi"] == [1]


def test_category_refuses_off_grid_values():
    assert bc.category(0.5) == 1 and bc.category(None) is None
    with pytest.raises(ValueError):
        bc.category(0.25)


def test_build_plan_refuses_figures_other_than_the_briefs():
    vals = {"a": {"kimi": (0.0, 0.0), "sol": (0.0, 0.0), "sonnet55": (0.0, 0.0)}}
    with pytest.raises(SystemExit):
        bc.build_plan(_instrument(vals), boot_n=5)


def test_model_checks_report_implied_and_observed_rates():
    fit = {"pi_quiet": 0.5, "theta": {f: {"Q": [1.0, 0.0, 0.0], "N": [0.0, 0.0, 1.0]} for f in bc.PLAN_READERS}}
    counts = {"flips": {f: 0 for f in bc.PLAN_READERS}, "retest_pairs": {f: 10 for f in bc.PLAN_READERS},
              "quiet_r0": {f: 24 for f in bc.PLAN_READERS}, "n_r0": {f: 48 for f in bc.PLAN_READERS}}
    mc = bc.model_checks(fit, counts)
    assert mc["kimi"]["implied_flip_rate"] == 0 and mc["kimi"]["implied_quiet_share_one_sample"] == pytest.approx(0.5)
    assert math.isclose(mc["sol"]["observed_quiet_share_r0"], 0.5)


def test_reader_relative_fit_takes_symmetric_error_from_the_flip_rate():
    # kimi: 10 pairs, 2 flips; sol: 10 pairs, 5 flips; sonnet: none paired (e at 0.5)
    data = [{"kimi": [0, 2] if i < 2 else [0, 0], "sol": [0, 1] if i < 5 else [2, 2], "sonnet55": [0]} for i in range(10)]
    rr = bc.reader_relative_fit(data)
    e = (1 - math.sqrt(1 - 0.4)) / 2
    assert rr["theta"]["kimi"]["e"] == pytest.approx(e) and rr["theta"]["kimi"]["Q"][0] == pytest.approx(1 - e)
    assert rr["theta"]["sol"]["e"] == pytest.approx(0.5)
    assert rr["theta"]["sol"]["h"] == pytest.approx(5 / 15)   # credited sol samples: 5 at 0.5, 10 at 1
    assert rr["theta"]["sonnet55"]["e"] == pytest.approx(0.5)
    assert sum(rr["theta"]["kimi"]["N"]) == pytest.approx(1.0)


# ── C2: items, targets, units and a fake run ──

import asyncio  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402

import judge_client as jc  # noqa: E402
import stage3_legibility as lg  # noqa: E402
import test_stage3_legibility as tl  # noqa: E402

DOCS, DAY0 = tl.DOCS, tl.DAY0
TOK = re.compile(r"TOK-T1v\d-[A-Z]\d+")


def _pst(op, anchor, text):
    return tl.pst(op, anchor, text)


def b3_fixture():
    """Per document and writer: two candidates (B3-Dnn; odd n leak through statement 0) and one control (C-nn); per
    document one T1 sham with its same-number conforming payload. One candidate per writer is not in the quiet set."""
    key, triples, files, quiet = {"triples": {}}, [], {f"{p}-{w}": {"payloads": []} for p in ("candidates", "controls") for w in bc.WRITERS}, []
    n = c = 0
    for d, doc in enumerate(DOCS):
        anchor = "- Owner:" if d == 0 else "- Host:"
        for w in bc.WRITERS:
            for j in range(2):
                n += 1
                pid = f"B3-D{n:02d}"
                kind = tl.KINDS[j]
                sts = [_pst("replace", anchor, f"{anchor} TOK-T1v9-D{n:02d}"), _pst("append", "", f"TOK-T1v8-D{n:02d}"),
                       _pst("append", "", f"TOK-T1v7-D{n:02d}")]
                eff = f"EFFECT TOK-T1v9-D{n:02d}" + (" LEAKY" if n % 2 else "")
                files[f"candidates-{w}"]["payloads"].append({"id": pid, "arm": "distributed", "document": doc, "kind": kind,
                                                            "composed_effect": eff, "statements": [s for s, _ in sts]})
                tid = lg.sha256(f"b3|{w}|{pid}")
                triples.append({"triple_id": tid, "document": doc, "statements": [t for _, t in reversed(sts)]})
                key["triples"][tid] = {"source": f"candidates-{w}", "writer": w, "id": pid, "arm": "distributed", "kind": kind, "document": doc}
                if j == 0 or n > 4:
                    quiet.append({"writer": w, "id": pid, "document": doc})
            c += 1
            cid = f"C-{c:02d}"
            sts = [_pst("replace", anchor, f"{anchor} TOK-T1v9-K{c:02d}"), _pst("append", "", f"TOK-T1v8-K{c:02d}"), _pst("append", "", f"TOK-T1v7-K{c:02d}")]
            files[f"controls-{w}"]["payloads"].append({"id": cid, "arm": "control_samewriter", "document": doc, "kind": tl.KINDS[1],
                                                      "composed_effect": None, "statements": [s for s, _ in sts]})
            tid = lg.sha256(f"b3|ctl|{w}|{cid}")
            triples.append({"triple_id": tid, "document": doc, "statements": [t for _, t in sts]})
            key["triples"][tid] = {"source": f"controls-{w}", "writer": w, "id": cid, "arm": "control_samewriter", "kind": tl.KINDS[1], "document": doc}
    key["triples"][lg.sha256("ref")] = {"source": "honest-triple-random", "ref_triple_id": "x"}
    t1_items, t1_triples, v2 = {"items": [{"item_id": "ee" * 32, "regime": "v2_conforming"}]}, [], {"payloads": []}
    for d, doc in enumerate(DOCS):
        s = d + 1
        sts = [_pst("append", "", f"TOK-T1v6-S{s:02d}"), _pst("append", "", f"TOK-T1v6-S{s + 10:02d}"), _pst("append", "", f"TOK-T1v6-S{s + 20:02d}")]
        sid = lg.sha256(f"t1|sham|{s}")
        v2["payloads"].append({"id": f"T1v2-S{s:02d}", "arm": "sham", "document": doc, "kind": tl.KINDS[0], "statements": [x for x, _ in sts]})
        v2["payloads"].append({"id": f"T1v2-C{s:02d}", "arm": "conforming", "document": doc, "kind": tl.KINDS[0],
                               "composed_effect": f"PAIRED TOK-T1v5-C{s:02d}", "statements": []})
        t1_triples.append({"triple_id": sid, "document": doc, "statements": [t for _, t in sts]})
        t1_items["items"].append({"item_id": sid, "regime": "control", "document": doc, "kind": tl.KINDS[0],
                                  "payload_ref": {"file": "v2", "id": f"T1v2-S{s:02d}"}})
    return quiet, key, triples, files, t1_items, t1_triples, v2


SMALL = {"candidate": 6, "control": 4, "sham": 2}


@pytest.fixture
def b3(monkeypatch):
    monkeypatch.setattr(bc, "N_OWN", 2)
    quiet, key, triples, files, t1_items, t1_triples, v2 = b3_fixture()
    items, rubrics, tr = bc.build_items(quiet, key, triples, files, t1_items, t1_triples, v2, DAY0, 2, expected=SMALL)
    return items, rubrics, tr


def test_build_items_counts_readers_targets_and_no_text(b3):
    items, rubrics, tr = b3
    rows = {r["item_id"]: r for r in items["items"]}
    assert items["counts"]["items"] == {"candidate": 6, "control": 4, "sham": 2}
    assert items["counts"]["candidates_by_writer"] == {"glm53": 3, "sonnet55": 3}
    for r in rows.values():
        assert r["readers"] == (["kimi", "sol", "sonnet55"] if r["writer"] == "glm53" else ["kimi", "sol"])
        if r["regime"] in bc.NULL_REGIMES:
            ft = rows[r["false_target"]]
            assert ft["regime"] == "candidate" and ft["document"] == r["document"]
            can_match = any(x["regime"] == "candidate" and x["document"] == r["document"] and x["kind"] == r["kind"] for x in rows.values())
            assert r["false_target_kind_matched"] == can_match and (ft["kind"] == r["kind"]) == can_match
        else:
            assert r["false_target"] is None
        assert r["paired_target"] == (r["regime"] == "sham")
    assert sum(r["own"] for r in rows.values()) == 2 and all(rows[i]["regime"] == "candidate" for i in items["own_draw"])
    assert set(rubrics["rubric"]) == {i for i, r in rows.items() if r["regime"] == "candidate"}
    assert set(rubrics["paired"]) == {i for i, r in rows.items() if r["regime"] == "sham"} and set(rubrics["own"]) == set(items["own_draw"])
    dumped = json.dumps(items)
    assert "TOK-" not in dumped and "EFFECT" not in dumped and "PAIRED" not in dumped
    assert items["rubrics_sha256"] == lg.sha256(lg.canonical(rubrics))
    assert set(tr) == set(rows)


def test_quiet_set_governs_which_candidates_enter(b3):
    items, _r, _t = b3
    quiet, key, *_ = b3_fixture()
    ids = {i["item_id"] for i in items["items"] if i["regime"] == "candidate"}
    want = {tid for tid, v in key["triples"].items() if v.get("arm") == "distributed" and {"writer": v["writer"], "id": v["id"], "document": v["document"]} in quiet}
    assert ids == want and len(ids) == 6


def test_draws_are_reproducible_and_seeded(b3, monkeypatch):
    items, _r, _t = b3
    monkeypatch.setattr(bc, "N_OWN", 2)
    again = bc.build_items(*b3_fixture(), DAY0, 2, expected=SMALL)[0]
    assert again["items"] == items["items"] and again["own_draw"] == items["own_draw"]
    cands = sorted(r["item_id"] for r in items["items"] if r["regime"] == "candidate")
    assert items["own_draw"] == sorted(random.Random(bc.OWN_SEED).sample(cands, 2))


def test_a_mismatched_payload_or_count_refuses():
    quiet, key, triples, files, t1_items, t1_triples, v2 = b3_fixture()
    files["candidates-glm53"]["payloads"][0]["statements"][1]["text"] = "TOK-T1v1-X99"
    with pytest.raises(ValueError, match="does not match"):
        bc.build_items(quiet, key, triples, files, t1_items, t1_triples, v2, DAY0, 2, expected=SMALL)
    with pytest.raises(ValueError, match="counts"):
        bc.build_items(*b3_fixture(), DAY0, 2, expected={"candidate": 7, "control": 4, "sham": 2})
    quiet, key, triples, files, t1_items, t1_triples, v2 = b3_fixture()
    files["candidates-sonnet55"]["payloads"][0]["composed_effect"] = " "
    with pytest.raises(ValueError, match="composed_effect"):
        bc.build_items(quiet, key, triples, files, t1_items, t1_triples, v2, DAY0, 2, expected=SMALL)


def test_scoring_targets_put_sensitivities_on_sample_zero_only():
    cand = {"regime": "candidate", "own": True}
    assert bc.scoring_targets(cand, 0) == ("rubric", "own") and bc.scoring_targets(cand, 1) == ("rubric",)
    assert bc.scoring_targets({"regime": "candidate", "own": False}, 0) == ("rubric",)
    sham = {"regime": "sham", "paired_target": True}
    assert bc.scoring_targets(sham, 0) == ("false", "paired") and bc.scoring_targets(sham, 1) == ("false",)
    assert bc.scoring_targets({"regime": "control", "paired_target": False}, 0) == ("false",)
    assert len(bc.scorer_units(cand, 0)) == 4


def test_sample_and_pass_indices_give_distinct_cache_keys():
    iid, pkt = "ab" * 32, "same packet"
    keys = {jc.cache_key(lg.SCORE_VIEW, lg.score_label(p, "kimi", s, iid, "part1", "rubric"), pkt) for p in bc.PASSES for s in (0, 1)}
    assert len(keys) == 4
    reads = {jc.cache_key(lg.READ_VIEW, lg.read_label(s, iid, "part1"), pkt) for s in (0, 1, 2)}
    assert len(reads) == 3
    assert lg.parse_label(lg.score_label(2, "sonnet55", 1, iid, "whole", "false"))["r"] == 1


def test_estimate_counts_calls_per_reader_and_scorer(b3):
    items, rubrics, tr = b3
    rows = items["items"]
    models = {"models": {m: {"pricing": {"prompt": "0.000001", "completion": "0.000004"}} for m in
                         (lg.FAMILIES["kimi"]["openrouter"], lg.FAMILIES["sonnet55"]["openrouter"])}}
    routes = {"chosen": {"sonnet55": {"route": "openrouter", "model": lg.FAMILIES["sonnet55"]["openrouter"]},
                         "kimi": {"route": "openrouter", "model": lg.FAMILIES["kimi"]["openrouter"]},
                         "sol": {"route": "converse", "model": lg.FAMILIES["sol"]["converse"]}}}
    est = bc.estimate(rows, tr, DAY0, rubrics, models, routes, 2)
    assert est["families"]["kimi"]["calls"] == est["families"]["sol"]["calls"] == 12 * 2 * 4
    assert est["families"]["sonnet55"]["calls"] == 5 * 2 * 4       # three GLM candidates and two GLM controls
    by_id = {r["item_id"]: r for r in rows}
    want = sum(len(bc.scorer_units(by_id[i], s)) for f in lg.FAMILIES for s, i, _c in bc.reader_units(rows, f, 2))
    assert est["scorer"]["calls"] == want and est["stop_at_usd"] == round(2 * est["total_usd"], 2)


def fake_reader(declined_item_token=None):
    def fn(kw):
        sec = tl.change_section(kw["messages"][0]["content"])
        if declined_item_token and declined_item_token in sec:
            return tl.msg("DECLINED")
        toks = sorted(set(TOK.findall(sec)))
        return tl.msg(("WHOLE " if sec.startswith("3 edits") else "PART ") + " ".join(toks))
    return fn


def fake_scorer(kw):
    pkt = kw["messages"][0]["content"]
    rubric = pkt.split("Target:\n<<<\n", 1)[1].split("\n>>>", 1)[0]
    answer = pkt.split("Answer:\n<<<\n", 1)[1].split("\n>>>", 1)[0]
    rt, at = set(TOK.findall(rubric)), set(TOK.findall(answer))
    if rubric.startswith("The document"):
        hit = bool(rt) and rt <= at
    else:
        hit = bool(rt & at) and (answer.startswith("WHOLE") or "LEAKY" in rubric)
    return tl.msg(json.dumps({"reason": "r", "declined": False, "score": int(hit)}))


def fake_run(tmp_path, b3, declined_item_token=None, k=2):
    items, rubrics, tr = b3
    rows = items["items"]
    packets = lg.all_packets(rows, tr, DAY0)
    readers, fcs = {}, {}
    for f in lg.FAMILIES:
        readers[f], fcs[f] = tl.client(fake_reader(declined_item_token if f == "kimi" else None), tmp_path / f"read-{f}.jsonl",
                                       lg.READER_SYSTEM, lg.READER_PROMPT_VERSION, lg.parse_answer)
    scorer, sfc = tl.client(fake_scorer, tmp_path / "score.jsonl", lg.SCORER_SYSTEM, lg.SCORER_PROMPT_VERSION, lg.parse_score)
    guard = lg.SpendGuard(1e9)
    guard.clients = list(readers.values()) + [scorer]
    log = tmp_path / "batches.jsonl"

    async def both():
        a = await bc.run_phase("nulls", [r for r in rows if r["regime"] in bc.NULL_REGIMES], packets, readers, scorer, rubrics, guard, log, 0, k)
        b = await bc.run_phase("candidates", [r for r in rows if r["regime"] == "candidate"], packets, readers, scorer, rubrics, guard, log, 10, k)
        return a, b
    a, b = asyncio.run(both())
    rec = bc.B3Records({f: lg.read_jsonl(tmp_path / f"read-{f}.jsonl") for f in readers}, lg.read_jsonl(tmp_path / "score.jsonl"))
    return rows, rec, a, b, fcs, sfc


def test_fake_run_calls_every_reader_on_its_items_and_scores_every_target(tmp_path, b3):
    rows, rec, a, b, fcs, sfc = fake_run(tmp_path, b3)
    assert len(fcs["kimi"].messages.calls) == len(fcs["sol"].messages.calls) == 12 * 2 * 4
    assert len(fcs["sonnet55"].messages.calls) == 5 * 2 * 4
    for call in fcs["sonnet55"].messages.calls:
        assert "TOK-T1v6-S" not in call["messages"][0]["content"]          # the sham is not GLM-written
    want = sum(len(bc.scorer_units(r, s)) * 4 for f in lg.FAMILIES for r in rows if f in r["readers"] for s in range(2))
    assert a["score"]["done"] + b["score"]["done"] == want == len(sfc.messages.calls)
    for call in sfc.messages.calls:
        assert "The change (" not in call["messages"][0]["content"] and "Current values" not in call["messages"][0]["content"]
    for r in rows:
        for f in r["readers"]:
            for s in range(2):
                x = rec.item_stat(f, s, r, bc.l_target(r["regime"]))
                assert x["status"] == "computed"
                if r["regime"] == "candidate":
                    assert x["D_whole"] == 1.0
                else:
                    assert x["D_whole"] == 0.0 and x["D_part"] == 0.0
    leaks = {r["item_id"] for r in rows if r["regime"] == "candidate" and "LEAKY" in b3[1]["rubric"][r["item_id"]]}
    for r in rows:
        if r["regime"] == "candidate":
            assert rec.item_stat("kimi", 1, r, "rubric")["D_part"] == (1.0 if r["item_id"] in leaks else 0.0)
            if r["own"]:
                own = rec.item_stat("sol", 0, r, "own")
                assert own["D_whole"] == 1.0 and own["D_part"] == 1.0
        if r["regime"] == "sham":
            assert rec.item_stat("kimi", 0, r, "paired")["D_part"] == 0.0


def test_a_declined_part_is_a_refusal_for_that_reader_only(tmp_path, b3):
    rows, rec, *_ = fake_run(tmp_path, b3, declined_item_token="TOK-T1v8-D01")
    target = next(r for r in rows if r["regime"] == "candidate" and "D01" in b3[1]["rubric"][r["item_id"]])
    for s in range(2):
        x = rec.item_stat("kimi", s, target, "rubric")
        assert x["D_part"] is None and x["D_part_status"] == "refused_token"
        assert rec.item_stat("sol", s, target, "rubric")["D_part"] is not None
