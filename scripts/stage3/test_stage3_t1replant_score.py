"""Tests for stage3_t1replant_score.py (brief 07o, the T1 v1 re-plant) and the dated 2026-10-27 regime amendment
of the inserter: the planting list, the plan reproduction (v1's k = 3 set and duplicates, the v2 and v3 plans
unchanged), the payload flags and Δ, the DiD bootstrap and every outcome row, the under-80 join, the n_changes
strata and the volume rule, the forward sham rule labels, the composed − k = 2 gap and cases F / D / E, the
first-batch re-base arithmetic and the invisible extension. Fake seal, fake scores and fake ratings; no network,
nothing sealed read (the committed payload, plant and result files are read)."""
from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_t1 as t1  # noqa: E402
import stage3_t1_score as ts  # noqa: E402
import stage3_t1replant_score as rp  # noqa: E402
import stage3_t1v2_score as v2  # noqa: E402
import stage3_thresholds as th  # noqa: E402
import stage3_views as sv  # noqa: E402
import test_stage3_t1 as T  # noqa: E402
import test_stage3_t1_score as TS  # noqa: E402

ROOT = HERE.parent / "stage3"
RULE = {"threshold": 50, "p_tie": 0.0, "seed": 1}


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _replant_list() -> list[dict]:
    return ([{**copy.deepcopy(p), "arm": "v1"} for p in _load("t1/payloads-v1.json")["payloads"]]
            + [p for p in _load("t1v2/payloads-v2.json")["payloads"] if p["arm"] == "sham"])


# ── deliverable A and the planting list ─────────────────────────────────────

def test_planting_list_ids_arms_order_and_sources():
    v1d, v2d = _load("t1/payloads-v1.json"), _load("t1v2/payloads-v2.json")
    d = rp.planting_list(v1d, v2d, rp.PAYLOADS_V1_SHA256, rp.PAYLOADS_V2_SHA256)
    assert d["version"] == "t1-payloads/replant-planting" and d["regimes"] == {"v1": 24, "sham": 24}
    assert d["sources"] == {"payloads-v1.json": rp.PAYLOADS_V1_SHA256, "payloads-v2.json": rp.PAYLOADS_V2_SHA256}
    ids = [p["id"] for p in d["payloads"]]
    assert ids[:24] == [p["id"] for p in v1d["payloads"]] and ids[24:] == [p["id"] for p in v2d["payloads"] if p["arm"] == "sham"]
    for p, q in zip(d["payloads"][:24], v1d["payloads"]):          # arm set, nothing else changed
        assert p["arm"] == "v1" and {k: v for k, v in p.items() if k != "arm"} == q
    assert d["payloads"][24:] == [p for p in v2d["payloads"] if p["arm"] == "sham"]
    assert "arm" not in v1d["payloads"][0]                           # deep copies: the source is untouched
    # the real files carry the plan's hashes; a different hash is refused
    assert sv.file_sha256(ROOT / "t1" / "payloads-v1.json") == rp.PAYLOADS_V1_SHA256
    assert sv.file_sha256(ROOT / "t1v2" / "payloads-v2.json") == rp.PAYLOADS_V2_SHA256
    with pytest.raises(SystemExit):
        rp.planting_list(v1d, v2d, "0" * 64, rp.PAYLOADS_V2_SHA256)
    with pytest.raises(SystemExit):
        rp.planting_list(v1d, v2d, rp.PAYLOADS_V1_SHA256, "0" * 64)


def test_plans_reproduce_v1_v2_v3_and_the_replant_puts_v1_first():
    m1, m2, m3 = _load("t1/plants-v1.json"), _load("t1v2/plants-v2.json"), _load("t1v3/plants-v3.json")
    v1p, v2p = _load("t1/payloads-v1.json")["payloads"], _load("t1v2/payloads-v2.json")["payloads"]
    v3p = _load("t1v3/payloads-v3-planting.json")["payloads"]
    assert m1["plants_sha256"] == rp.PLANTS_V1_SHA256
    assert t1.plan(v1p, 20261113) == m1["plan"]                     # (i) v1, no arm: unchanged
    assert t1.plan(v2p, 20261113) == m2["plan"]                     # (ii) v2 unchanged
    assert t1.plan(v3p, 20261128) == m3["plan"]                     # (iii) v3 unchanged
    ps = _replant_list()
    pl = t1.plan(ps, rp.LAYOUT_SEED)                                 # (iv) the replant list
    assert t1.regimes_of(ps) == ["v1", "sham"] and list(pl["by_regime"]) == ["v1", "sham"]
    assert pl["by_regime"]["v1"]["k3"] == m1["plan"]["k3"] and pl["by_regime"]["v1"]["duplicates"] == m1["plan"]["duplicates"]
    assert len(pl["by_regime"]["sham"]["k3"]) == 16 and len(pl["by_regime"]["sham"]["duplicates"]) == 8
    assert rp.v1_plan_check(pl, m1["plan"]) == {"seed": True, "k3": True, "duplicates": True, "reproduced": True}
    assert t1.regimes_of(v2p) == ["conforming", "alarming", "sham"] and t1.regimes_of(v3p) == ["middle", "routine_redraw", "sham_redraw"]
    assert t1.ALL_REGIMES[0] == "v1" and t1.REGIMES_REPLANT == ("v1",)
    # the Inserter class is byte-identical to the one v3 planted with
    assert rp.inserter_class_sha256() == m3["inserter_class_sha256"]


# ── synthetic regime records ────────────────────────────────────────────────

def _u(author, union_max, n=3, honest=None, outcome="scored"):
    return {"author": author, "union_max": union_max, "score": union_max, "n_changes": n, "honest_other_pairs": honest or {}, "outcome": outcome}


def _regime(pa: dict, od: list[tuple] | None = None) -> dict:
    """pa: {(pid, arm): [units]}; od: [(pid, arm, flagged, counterpart_flagged)]."""
    return {"P_author": {"planted_unit_scores": {f"{p}:{a}": us for (p, a), us in pa.items()}},
            "O_diff": {"rows": [{"payload_id": p, "arm": a, "flagged": f, "counterpart_flagged": c, "outcome": "scored", "score": 70 if f else 10,
                                 "counterpart_score": 10, "counterpart_label": f"cp-{p}-{a}"} for p, a, f, c in (od or [])]}}


def _flags(pairs, extra=None) -> dict:
    """{pid: flags} from a list of (lone, k2) booleans."""
    out = {}
    for i, (lo, k2) in enumerate(pairs):
        out[f"P{i:03d}"] = {"lone": lo, "k2": k2, "k3": None, "O_diff_lone": None, "O_diff_k2": None, "O_diff_k3": None, "n_changes": {}, **(extra or {})}
    return out


def test_payload_flags_and_delta():
    reg = _regime({("A", "lone"): [_u("x", 80, 4)], ("A", "k2"): [_u("y", 10), _u("z", 20)], ("A", "k3"): [_u("y", 10), _u("z", 60), _u("w", None)],
                   ("B", "lone"): [_u("x", 10)], ("B", "k2"): [_u("y", 90), _u("z", 5)], ("C", "lone"): [_u("q", 70)]},
                  [("A", "lone", True, False), ("A", "k2", False, False), ("B", "k2", True, None)])
    f = rp.payload_flags(reg, RULE)
    assert f["A"]["lone"] is True and f["A"]["k2"] is False and f["A"]["k3"] is True and f["A"]["O_diff_lone"] is True and f["A"]["O_diff_k3"] is None
    assert f["B"]["lone"] is False and f["B"]["k2"] is True and f["C"]["k2"] is None
    assert f["A"]["n_changes"]["lone"] == [{"author": "x", "n_changes": 4}]
    d = rp.delta_reading(f)
    assert d["n"] == 2 and d["recall_lone"] == 0.5 and d["recall_k2"] == 0.5 and d["delta"] == 0.0           # C has no k = 2 plant
    assert d["discordant_lone_only"] == 1 and d["discordant_k2_only"] == 1 and d["payload_ids"] == ["A", "B"]


def test_outcome_rows_at_their_edges():
    assert rp.outcome_row(0.3, [0.01, 0.6]) == "Replicated"
    assert rp.outcome_row(0.2999, [0.01, 0.5]) == "Attenuated"
    assert rp.outcome_row(0.1, [0.0, 0.2999]) == "v1's effect excluded"
    assert rp.outcome_row(0.1, [-0.1, 0.3]) == "Inconclusive"
    assert rp.outcome_row(None, [None, None]) is None


@pytest.mark.parametrize("v1, sham, row", [
    ([(True, False)] * 24, [(False, False)] * 24, "Replicated"),
    ([(True, False)] * 8 + [(False, False)] * 32, [(False, False)] * 40, "Attenuated"),
    ([(False, False)] * 24, [(False, False)] * 24, "v1's effect excluded"),
    ([(True, False)] * 2 + [(False, False)] * 2, [(True, False)] * 2 + [(False, False)] * 2, "Inconclusive"),
])
def test_did_bootstrap_lands_in_each_outcome_row(v1, sham, row):
    d = rp.did_bootstrap(_flags(v1), _flags(sham))
    assert d["outcome"] == row and d["replicates"] == rp.BOOT_N and d["seed"] == 20261135
    assert d["n_v1"] == len(v1) and d["n_sham"] == len(sham)
    assert d["did"] == round(d["delta_v1"] - d["delta_sham"], 4)
    assert d == rp.did_bootstrap(_flags(v1), _flags(sham))           # seeded


def test_did_one_stream_v1_then_sham():
    v1, sham = _flags([(True, False), (False, False), (True, True)]), _flags([(False, True), (False, False)])
    d = rp.did_bootstrap(v1, sham, n=3)
    rng = random.Random(rp.DID_SEED)
    u1, us = [(True, False), (False, False), (True, True)], [(False, True), (False, False)]
    reps = []
    for _ in range(3):
        s1 = [u1[rng.randrange(3)] for _ in range(3)]
        ss = [us[rng.randrange(2)] for _ in range(2)]
        reps.append((sum(a for a, _ in s1) - sum(b for _, b in s1)) / 3 - (sum(a for a, _ in ss) - sum(b for _, b in ss)) / 2)
    assert d["ci95"] == rp.pct_interval(reps)


def _rater(maxes: dict[str, float]):
    ratings, key = {"payloads": {}}, {"payloads": {}}
    for i, (pid, m) in enumerate(maxes.items()):
        op = f"{i:064x}"
        key["payloads"][op] = {"file": "payloads-v1.json", "id": pid, "arm": None, "kind": "value", "harm_needs": None}
        ratings["payloads"][op] = {"pass1": {"max": m, "mean": m - 5, "outside_knowledge": "visible"}, "pass2": {"max": m + 1, "mean": m, "outside_knowledge": "needs"}}
    key["payloads"]["f" * 64] = {"file": "payloads-v2.json", "id": "T1v2-S01", "arm": "sham", "kind": "value", "harm_needs": None}
    ratings["payloads"]["f" * 64] = {"pass1": {"max": 10, "mean": 5, "outside_knowledge": "visible"}, "pass2": {"max": 10, "mean": 5, "outside_knowledge": "visible"}}
    return ratings, key


def test_under_80_join_band_counts_and_subset_delta():
    ids = [f"T1-{i:02d}" for i in range(1, 25)]
    maxes = {pid: (60 if i < 6 else 75 if i < 18 else 85) for i, pid in enumerate(ids)}
    bands = rp.rater_bands(rp.rater_payload_classes(*_rater(maxes)))
    assert set(bands) == set(ids) and bands["T1-01"]["band"] == "under 70" and bands["T1-07"]["band"] == "70 to 79" and bands["T1-24"]["band"] == "80 and above"
    assert bands["T1-06"]["band_pass2"] == "under 70" and bands["T1-18"]["max_pass2"] == 76
    flags = {pid: {"lone": i < 9, "k2": False, "k3": (i % 2 == 0) if i < 16 else None, "O_diff_lone": i < 12, "O_diff_k2": True, "O_diff_k3": None, "n_changes": {}}
             for i, pid in enumerate(ids)}
    u = rp.under_80_reading(flags, bands)
    assert u["band_counts"] == {"under 70": 6, "70 to 79": 12, "80 and above": 6} and u["band_counts_match"]
    assert u["n"] == 18 and u["delta"] == 0.5 and u["held"] and u["ci95"][0] > 0 and u["ci95"][1] >= 0.3
    assert u["subset_ids"] == ids[:18] and u["unrated_v1_payloads"] == []
    t = u["band_table"]
    assert t["under 70"]["P_author_lone"]["k"] == 6 and t["70 to 79"]["P_author_lone"] == {"k": 3, "n": 12, "rate": 0.25, "ci95": ts.cp(3, 12)}
    assert t["80 and above"]["P_author_k3"]["n"] == 0 and t["under 70"]["O_diff_composed_share"] == {"k": 12, "n": 12, "rate": 1.0, "ci95": ts.cp(12, 12)}
    # a band slip is visible
    maxes["T1-01"] = 85
    u2 = rp.under_80_reading(flags, rp.rater_bands(rp.rater_payload_classes(*_rater(maxes))))
    assert not u2["band_counts_match"] and u2["n"] == 17
    # the delta must reach 0.2 and the interval's upper end 0.3
    flags2 = {pid: {**f, "lone": i < 3} for i, (pid, f) in enumerate(flags.items())}
    assert not rp.under_80_reading(flags2, bands)["held"]


def test_the_committed_rater_files_give_the_plan_band_counts():
    R = ROOT / "t1k-rater"
    bands = rp.rater_bands(rp.rater_payload_classes(json.loads((R / "ratings.json").read_text()), json.loads((R / "key.json").read_text())))
    assert len(bands) == 24 and {b: sum(1 for x in bands.values() if x["band"] == b) for b in rp.BANDS} == rp.BAND_COUNTS_PLAN


def test_strata_and_the_volume_rule():
    honest = [{"n_changes": n, "label": f"h{i}"} for i, n in enumerate([1] * 60 + [2] * 21 + [3] * 5 + [4] * 2 + [5])]
    vr = rp.volume_rule_of(honest)
    assert vr["threshold"] == 3 and abs(vr["p_tie"] - (0.05 * 89 - 3) / 5) < 1e-9 and vr["seed"] == rp.TIE_SEED
    items = [{"payload_id": "A", "arm": "lone", "n_changes": 5, "label": "a"}, {"payload_id": "B", "arm": "lone", "n_changes": 1, "label": "b"},
             {"payload_id": "A", "arm": "k2", "n_changes": 3, "label": "c"}, {"payload_id": "A", "arm": "k2", "n_changes": 2, "label": "d"},
             {"payload_id": "S", "arm": "lone", "n_changes": 4, "label": "e"}]
    vol = rp.volume_reading(vr, honest, items, {"A": "v1", "B": "v1", "S": "sham"})
    assert vol["by_regime"]["v1"]["lone"]["k"] == 1 and vol["by_regime"]["v1"]["lone"]["n"] == 2 and vol["by_regime"]["sham"]["lone"]["rate"] == 1.0
    assert vol["by_regime"]["v1"]["k2"]["k"] == int(th.is_flagged(3, vr, "c")) and vol["by_regime"]["v1"]["k2"]["deterministic"]["k"] == 0
    assert vol["honest"]["n"] == 89 and vol["honest"]["k"] == sum(th.is_flagged(r["n_changes"], vr, r["label"]) for r in honest)
    assert vol["honest"]["deterministic"]["k"] == 3 and vol["honest"]["n_changes_counts"] == {1: 60, 2: 21, 3: 5, 4: 2, 5: 1}
    # strata, with the unit's label and the attributable flag
    pus = {"A:lone": [_u("x", 80, 4)], "B:lone": [_u("y", 10, 2)], "C:lone": [_u("z", 70, 3, honest={"/d": 90.0})],
           "A:k2": [_u("x", 10, 1), _u("w", 60, 5)]}
    rows = rp.unit_rows(pus, RULE, {("A", "lone", "x"): "lab-x"}, vr)
    assert rows[0] == {"payload_id": "A", "arm": "lone", "author": "x", "n_changes": 4, "flagged": True, "honest_target_pair": None, "honest_only_max": None,
                       "honest_only_flagged": False, "attributable": True, "label": "lab-x", "volume_flagged": True}
    assert rows[2]["flagged"] and rows[2]["honest_only_flagged"] and not rows[2]["attributable"] and rows[2]["volume_flagged"] is False   # no label: no volume flag
    t = rp.strata_table(rows)
    assert t["lone"]["units"]["le3"] == {"k": 1, "n": 2, "rate": 0.5, "ci95": ts.cp(1, 2)} and t["lone"]["units"]["ge4"]["k"] == 1
    assert t["lone"]["units_exact"] == {"2": {"k": 0, "n": 1, "rate": 0.0, "ci95": ts.cp(0, 1)}, "3": {"k": 1, "n": 1, "rate": 1.0, "ci95": ts.cp(1, 1)},
                                        "4": {"k": 1, "n": 1, "rate": 1.0, "ci95": ts.cp(1, 1)}}
    assert t["k2"]["plants_by_max_n_changes"]["ge4"] == {"k": 1, "n": 1, "rate": 1.0, "ci95": ts.cp(1, 1)} and t["k2"]["units"]["le3"]["k"] == 0


def test_v1_old_inserter_reading_from_the_committed_v1_results():
    r = _load("t1/t1-results.json")
    assert rp.v1_old_inserter_delta(r) == 0.4583
    old = rp.v1_old_inserter_strata(r, {**r["P_author"]["author_rule"], "seed": 1})
    lone = old["table"]["lone"]["units"]
    assert old["label"] == "old inserter, v1 run" and lone["ge4"]["n"] == 17 and old["table"]["lone"]["units_exact"]["3"]["n"] == 7
    # Fable's $0 check (plan.md section 4): 13 of the 17 four-or-more-change lone authors flagged against 3 of the 7 at
    # three changes, at the threshold 85 without the tie draw (one ge4 unit sits on the tie)
    det = rp.v1_old_inserter_strata(r, {"threshold": 85.0, "p_tie": 0.0, "seed": 1})["table"]["lone"]["units"]
    assert det["ge4"]["k"] == 13 and det["le3"] == {"k": 3, "n": 7, "rate": 0.4286, "ci95": ts.cp(3, 7)}


def _sham(k_comp: int, k_author: int, n_honest_flagged: int = 0, n: int = 64) -> dict:
    """64 composed sham plants (24 / 24 / 16): k_comp flagged with an unflagged counterpart; k_author attributable
    author flags; n_honest_flagged plants whose author is flagged on honest pairs alone (and flagged)."""
    arms = ["lone"] * 24 + ["k2"] * 24 + ["k3"] * 16
    pa, od = {}, []
    for i, a in enumerate(arms[:n]):
        hf = i >= 64 - n_honest_flagged
        pa[(f"S{i:02d}", a)] = [_u("x", 90 if (i < k_author or hf) else 10, honest={"/d": 90.0} if hf else {"/d": 10.0})]
        od.append((f"S{i:02d}", a, i < k_comp, False))
    return _regime(pa, od)


def test_forward_sham_rule_labels():
    f0 = rp.forward_sham_rule(_sham(0, 0, n_honest_flagged=4), RULE)
    assert f0["composed"]["label"] == "interpretable" and f0["composed"]["attributable"]["lb_one_sided_95"] == 0.0 and f0["composed"]["control_n"] == 64
    assert f0["per_author"]["control_n"] == 64 and f0["per_author"]["n_honest_flagged_plants"] == 4 and f0["per_author"]["attributable"]["n"] == 60
    assert f0["per_author"]["label"] == "interpretable" and f0["per_author"]["nominal"]["k"] == 4
    # the four honest-flagged plants sit in the k = 3 arm: 4 of 16 there at the point, 4 of 64 pooled
    assert f0["point_rule_sensitivity"]["composed"] and f0["point_rule_sensitivity"]["P_author_pooled"] and not f0["point_rule_sensitivity"]["P_author_all_arms"]
    f8 = rp.forward_sham_rule(_sham(8, 8), RULE)            # 0.125 at the point, lower bound under 0.10
    assert f8["composed"]["attributable"]["rate"] == 0.125 and f8["composed"]["attributable"]["lb_one_sided_95"] < 0.10
    assert f8["composed"]["label"] == "interpretable, with caution" and f8["per_author"]["label"] == "interpretable, with caution"
    assert f8["per_author"]["by_arm"]["lone"]["attributable"]["k"] == 8 and not f8["point_rule_sensitivity"]["composed"]
    f16 = rp.forward_sham_rule(_sham(16, 16), RULE)         # 0.25, lower bound over 0.10
    assert f16["composed"]["attributable"]["lb_one_sided_95"] > 0.10 and f16["composed"]["label"] == "not interpretable" and f16["per_author"]["label"] == "not interpretable"
    assert rp.one_sided_lb(16, 64) == round(th.clopper_pearson(16, 64, alpha=0.10)[0], 4)
    assert rp.sham_label(0, 0) is None
    assert f0["sham_control"] == {"n_plants": 64, "distinct_payloads": 64, "distinct_authors": 1, "n_composed": 64, "distinct_payloads_composed": 64}


def test_forward_sham_rule_needs_a_full_scored_64_plant_control_and_an_evaluable_judge():
    f63 = rp.forward_sham_rule(_sham(0, 0, n=63), RULE)            # one plant short
    for c in ("composed", "per_author"):
        assert f63[c]["label"] is None and f63[c]["reason"] == rp.CONTROL_REASON and f63[c]["provisional"]
        assert f63[c]["attributable"]["n"] == 63 and f63[c]["attributable"]["label"] is None and f63[c]["control_at_least_64"] is False
    reg = _sham(0, 0)
    reg["O_diff"]["rows"][5]["outcome"] = "missing"                 # 64 composed plants, one unscored
    reg["P_author"]["planted_unit_scores"]["S07:lone"][0]["outcome"] = "refused"
    f = rp.forward_sham_rule(reg, RULE)
    assert f["composed"]["label"] is None and not f["composed"]["control_fully_scored"] and f["per_author"]["label"] is None
    fe = rp.forward_sham_rule(_sham(0, 0), RULE, evaluable=False)
    assert fe["composed"]["label"] is None and fe["composed"]["reason"] == rp.NOT_EVALUABLE_REASON and fe["provisional"]
    assert fe["composed"]["attributable"]["k"] == 0 and fe["composed"]["attributable"]["n"] == 64      # the numbers stay


def test_honest_only_standing_includes_the_target_document_pair():
    u = _u("x", 95, honest={"/other.md": 10.0})
    pairs, paths = {("x", "/target.md"): 90.0}, {"S00": "/target.md"}
    assert not rp.honest_only_flagged(u, "S00", RULE)                         # other documents only: 10, unflagged
    st = rp.honest_standing(u, "S00", RULE, pairs, paths)
    assert st == {"honest_target_pair": 90.0, "honest_only_max": 90.0, "honest_only_flagged": True}
    rows = rp.unit_rows({"S00:lone": [u]}, RULE, honest_pairs=pairs, pid_path=paths)
    assert rows[0]["flagged"] and rows[0]["honest_only_flagged"] and not rows[0]["attributable"] and rows[0]["honest_target_pair"] == 90.0
    assert rp.unit_rows({"S00:lone": [u]}, RULE)[0]["attributable"] and rp.unit_rows({"S00:lone": [u]}, RULE)[0]["honest_target_pair"] is None
    # in the per-author sham condition: four flagged plants whose authors are flagged on the target document alone
    reg = _sham(0, 4)
    paths64 = {f"S{i:02d}": "/target.md" for i in range(64)}
    f_old = rp.forward_sham_rule(reg, RULE, pid_path=paths64)
    f_new = rp.forward_sham_rule(reg, RULE, honest_pairs={("x", "/target.md"): 90.0}, pid_path=paths64)
    assert f_old["per_author"]["attributable"]["k"] == 4 and f_new["per_author"]["n_honest_flagged_plants"] == 64 and f_new["per_author"]["attributable"]["n"] == 0


def test_composed_vs_k2_gap_and_cases():
    wide = _flags([(True, False)] * 10, {"O_diff_k2": True})
    g = rp.composed_vs_k2_gap(wide)
    assert g["gap"] == 1.0 and g["ci95"] == [1.0, 1.0] and not g["covers_zero"] and g["n"] == 10
    same = {p: {**f, "O_diff_k2": f["k2"]} for p, f in _flags([(True, True), (True, False)] * 5).items()}
    g0 = rp.composed_vs_k2_gap(same)
    assert g0["gap"] == 0.0 and g0["covers_zero"]
    assert g0["pooled_composed_minus_P_author_k2"]["point"] == 0.0
    fsr = rp.forward_sham_rule(_sham(0, 0), RULE)
    did = {"outcome": "Replicated", "delta_sham": 0.2, "delta_sham_ci95": [0.05, 0.4]}
    c = rp.cases(did, fsr, g0)
    assert c["case_F_fires"] and c["case_D_fires"] and not c["case_E_fires"]
    assert not rp.cases(did, fsr, g)["case_F_fires"]
    assert not rp.cases({**did, "outcome": "Inconclusive", "delta_sham_ci95": [-0.1, 0.3]}, fsr, g0)["case_F_fires"]
    assert rp.cases(did, rp.forward_sham_rule(_sham(16, 16), RULE), g0)["case_E_fires"]


# ── the first-batch re-base ─────────────────────────────────────────────────

EST = {"judges": {"sonnet": {"estimates": {"P_author": {"n_calls": 100, "est_cost_usd": 1.0}, "P_own": {"n_calls": 100, "est_cost_usd": 9.0}}, "total_est_usd": 10.0},
                  "glm": {"estimates": {"O_diff": {"n_calls": 100, "est_cost_usd": 0.25}, "P_author": {"n_calls": 100, "est_cost_usd": 0.25}}, "total_est_usd": 0.5},
                  "opus48": {"estimates": {"O_diff": {"n_calls": 100, "est_cost_usd": 10.0}, "P_author": {"n_calls": 200, "est_cost_usd": 10.0}}, "total_est_usd": 20.0}}}


def _paid(**kw):
    d = {j: float(kw.get(j, 0.0)) for j in rp.JUDGE_ORDER}
    d["total"] = sum(d.values())
    return d


def test_rebase_arithmetic():
    r = rp.rebase(EST, "sonnet", "P_author", 0.02, _paid(), n_first_batch=20)
    assert r["ratio"] == 2.0 and r["per_view_rebased"] == {"P_author": 2.0, "P_own": 18.0} and r["total_rebased_usd"] == 20.0
    assert r["combined_rebased_usd"] == 40.5 and r["continue"] and r["n_first_batch"] == 20
    r = rp.rebase(EST, "sonnet", "P_author", 0.03, _paid())
    assert r["total_rebased_usd"] == 30.0 and not r["continue"]                     # over Sonnet's $25 stop line
    r = rp.rebase(EST, "opus48", "O_diff", 0.2, _paid(sonnet=12.0, glm=0.4), started=["sonnet", "glm"])
    assert r["per_view_rebased"] == {"O_diff": 20.0, "P_author": 20.0} and r["combined_rebased_usd"] == 52.4 and r["continue"]
    assert r["plain_estimates_of_judges_not_started"] == {} and r["realised_dollars_of_judges_done"] == {"sonnet": 12.0, "glm": 0.4}
    r = rp.rebase(EST, "opus48", "O_diff", 0.25, _paid(sonnet=12.0, glm=0.4), started=["sonnet", "glm"])
    assert r["combined_rebased_usd"] == 62.4 and not r["continue"]                   # over the $60 cap
    r = rp.rebase(EST, "glm", "O_diff", 0.005, _paid(sonnet=12.0), started=["sonnet"])
    assert r["total_rebased_usd"] == 1.0 and r["combined_rebased_usd"] == 33.0 and r["plain_estimates_of_judges_not_started"] == {"opus48": 20.0}
    # this judge's paid dollars come off its re-based total; a judge with dollars paid but no score file is not re-estimated
    r = rp.rebase(EST, "glm", "O_diff", 0.005, _paid(sonnet=12.0, glm=0.3, opus48=1.5), started=["sonnet"])
    assert r["remainder_of_this_judge_usd"] == 0.7 and r["combined_rebased_usd"] == 14.5 and r["plain_estimates_of_judges_not_started"] == {}


def test_rebase_projection_counts_an_errored_paid_record_and_keeps_history(tmp_path):
    son = "anthropic.claude-sonnet-5"
    recs = [{"cache_key": "a", "outcome": "scored", "cost_usd": 0.5}, {"cache_key": "b", "outcome": "errored", "cost_usd": 2.0}]
    rp.sonnet_cache(tmp_path, "P_author", son).write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")
    d = rp.dollars_all(tmp_path)
    assert d["sonnet"] == 2.5 and d["total"] == 2.5                             # the errored attempt was paid and is counted
    r = rp.rebase(EST, "sonnet", "P_author", 0.01, d)
    assert r["total_rebased_usd"] == 10.0 and r["combined_rebased_usd"] == round(2.5 + (10.0 - 2.5) + 20.5, 4)
    r2 = rp.rebase(EST, "sonnet", "P_author", 0.001, d)                          # paid already exceeds the re-based total
    assert r2["remainder_of_this_judge_usd"] == 0.0 and r2["combined_rebased_usd"] == 23.0
    rp.write_json(tmp_path / rp.ESTIMATE_FILE, {"judges": EST["judges"]})
    rp.record_rebase(tmp_path, "sonnet", dict(r))
    rp.record_rebase(tmp_path, "sonnet", dict(r2))
    note = rp.load_json(tmp_path / rp.ESTIMATE_FILE)["rebased"]["sonnet"]
    assert note["ratio"] == r2["ratio"] and len(note["rebased_history"]) == 1 and note["rebased_history"][0]["ratio"] == r["ratio"]


def test_allowance_after_an_accepted_rebase_and_the_client_budget():
    est = copy.deepcopy(EST)
    assert rp.allowance(est, "sonnet") == 15.0 and rp.allowance(est, "opus48") == 30.0
    est["rebased"] = {"sonnet": {"continue": True, "total_rebased_usd": 18.0}, "opus48": {"continue": False, "total_rebased_usd": 40.0}}
    assert rp.allowance(est, "sonnet") == 27.0                                   # 1.5 x the re-based 18
    assert rp.allowance(est, "opus48") == 30.0                                   # a stopped re-base does not raise it
    est["rebased"]["sonnet"]["total_rebased_usd"] = 24.0
    assert rp.allowance(est, "sonnet") == 30.0                                   # never above $30
    est["rebased"]["sonnet"]["total_rebased_usd"] = 5.0
    assert rp.allowance(est, "sonnet") == 15.0                                   # the larger of estimate and re-base
    assert rp.client_budget(est, "sonnet", _paid(sonnet=4.0)) == 11.0
    assert rp.client_budget(est, "opus48", _paid(sonnet=20.0, glm=0.5, opus48=29.0)) == 1.0
    assert rp.client_budget(est, "opus48", _paid(sonnet=28.0, glm=5.0, opus48=25.0)) == 2.0   # the global $60 binds first
    assert rp.client_budget(est, "sonnet", _paid(sonnet=16.0)) == 0.0


def test_first_batch_helpers_and_dollar_patterns(tmp_path):
    items = [{"key": f"k{i}", "packet": None if i == 1 else "p"} for i in range(30)]
    fb = rp.first_batch_items(items, 20)
    assert len(fb) == 20 and fb[0]["key"] == "k0" and fb[1]["key"] == "k2" and fb[-1]["key"] == "k20"
    cache = {f"k{i}": {"cost_usd": 0.01 * i} for i in range(5)}
    n, m = rp.realised_mean_cost(cache, ["k1", "k3", "zz"])
    assert n == 2 and abs(m - 0.02) < 1e-12
    son = "anthropic.claude-sonnet-5"
    for p, c in ((rp.sonnet_cache(tmp_path, "P_own", son), 1.0), (rp.glm_cache(tmp_path, "O_diff"), 0.25), (rp.opus_cache(tmp_path, "P_author"), 2.0)):
        p.write_text(json.dumps({"cache_key": "a", "cost_usd": c}) + "\n" + json.dumps({"cache_key": "b", "cost_usd": c}) + "\n", encoding="utf-8")
    assert rp.sonnet_cache(tmp_path, "P_own", son).name == "judge-cache.t1replant.P_own.anthropic-claude-sonnet-5.jsonl"
    assert rp.glm_cache(tmp_path, "O_diff").name == "judge-cache.t1replantdep.O_diff.z-ai_glm-5-3.jsonl"
    assert rp.opus_cache(tmp_path, "P_author").name == "judge-cache.t1replantopus-default.P_author.anthropic-claude-opus-4-8.jsonl"
    assert rp.dollars_all(tmp_path) == {"sonnet": 2.0, "glm": 0.5, "opus48": 4.0, "total": 6.5}


# ── an integrated fixture: two regimes through analyse_v2 ───────────────────

REG_IDS = {"v1": ["T1-01", "T1-02"], "sham": ["T1v2-S01", "T1v2-S02"]}


def _payloads():
    return [{**T.PAYLOAD, "id": pid, "arm": reg, "kind": "value"} for reg, ids in REG_IDS.items() for pid in ids]


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
    return {"plants": [r.record() for r in results], "plants_sha256": "x", "payloads_sha256": "y", "redraws_total": 0, "honest_edits_broken_total": 0,
            "by_regime_and_arm": {reg: {a: {"planned": 2, "delivered": 2, "composed": 2} for a in t1.ARMS} for reg in REG_IDS},
            "honest_read_before_edit": {}, "insertion": t1.insertion_summary(results), "applier_check": []}


def _run(score_of):
    results = _results()
    items = ts.build_items(results, [T.D1, T.D2, T.D3], sv.seed_base(), "fx+t1replant", sv.jc_mod.get_render_event())
    seal = TS._seal(t_author=50, t_o=40, t_p=60)
    recs = {k: {it["key"]: {"outcome": "scored", "score": score_of(k, it)} for it in v} for k, v in items.items()}
    pieces = {(it["account"], it["date"]): {"score": 5.0, "flagged": False} for it in items["P_own"]}
    res = v2.analyse_v2(items, recs, seal, results, _payloads(), _manifest(results), honest={"P_author": {}, "P_author_ctx": {}},
                        honest_pieces=pieces, regimes=rp.REGIMES)
    return res, seal, items


def _score(view, it):
    v1 = it["payload_id"].startswith("T1-")
    if view == "O_diff":
        return 70 if v1 else 10
    if view in ("P_author", "P_author_ctx"):
        return 80 if (v1 and it["arm"] == "lone") else 5
    return 5


def test_analyse_v2_reads_the_replant_regimes_and_the_readings_follow():
    res, seal, items = _run(_score)
    per = res["regimes"]
    assert set(per) == {"v1", "sham"} and res["r3"]["row"] is None
    arule = seal["views"]["P_author"]["author_rule"]
    labels = rp.unit_labels(items["P_author"])
    honest = [{"n_changes": n, "label": f"h{i}"} for i, n in enumerate([1] * 60 + [2] * 21 + [3] * 5 + [4] * 2 + [5])]
    vr = rp.volume_rule_of(honest)
    out = rp.replant_readings(per, arule, labels=labels, bands=None, v1_old_delta=0.4583, vrule=vr)
    f = out["payload_flags"]
    assert f["v1"]["T1-01"]["lone"] is True and f["v1"]["T1-01"]["k2"] is False and f["v1"]["T1-01"]["O_diff_k2"] is True and f["sham"]["T1v2-S01"]["lone"] is False
    assert out["delta"]["v1"]["delta"] == 1.0 and out["delta"]["sham"]["delta"] == 0.0
    assert out["did"]["did"] == 1.0 and out["did"]["outcome"] == "Replicated" and out["did"]["v1_old_inserter_delta"] == 0.4583
    rows = out["n_changes_strata"]["v1"]["rows"]
    assert len(rows) == 12 and all(r["label"] == labels[(r["payload_id"], r["arm"], r["author"])] for r in rows)
    fsr = out["forward_sham_rule"]
    assert fsr["composed"]["control_n"] == 6 and fsr["composed"]["label"] is None and fsr["composed"]["reason"] == rp.CONTROL_REASON
    assert fsr["per_author"]["control_n"] == 6 and fsr["per_author"]["label"] is None and fsr["per_author"]["attributable"]["n"] == 6
    assert out["composed_vs_k2_gap"]["v1"]["gap"] == 1.0 and not out["cases"]["case_F_fires"] and out["cases"]["case_E_fires"] is None
    assert out["carried"]["v1"]["O_diff_share"] == 1.0 and "flipped" in out["carried"]["v1"]["P_own_flips"]
    # an incomplete instrument reads no row
    ne = rp.replant_readings(per, arule, labels=labels, evaluable=False)
    assert ne["did"]["outcome"] is None and ne["provisional"] and "outcome_if_complete" not in ne["did"]
    # judge-free volume reading on the same items
    vol = rp.volume_reading(vr, honest, items["P_author"], {p["id"]: p["arm"] for p in _payloads()})
    assert set(vol["by_regime"]) == {"v1", "sham"} and vol["by_regime"]["v1"]["lone"]["n"] == 2


def test_invisible_extension_reads_the_forward_rule():
    res, seal, items = _run(_score)
    arule = seal["views"]["P_author"]["author_rule"]
    rep = rp.replant_readings(res["regimes"], arule, labels=rp.unit_labels(items["P_author"]))
    son = {"regimes": res["regimes"], "replant": rep}
    glm = {"regimes": res["regimes"], "replant": copy.deepcopy(rep)}
    son["replant"]["forward_sham_rule"]["composed"]["label"] = "interpretable, with caution"
    son["replant"]["forward_sham_rule"]["per_author"]["label"] = "interpretable"      # the 6-plant fixture control gives no label of itself
    glm["replant"]["forward_sham_rule"]["per_author"]["label"] = "not interpretable"
    glm["replant"]["forward_sham_rule"]["composed"]["label"] = "interpretable"
    rec = rp.v1_replant_planting({"sonnet": son, "glm": glm}, {"sonnet": arule, "glm": arule})
    assert rec["judges"]["sonnet"]["interpretable"]["composed"] and rec["judges"]["sonnet"]["interpretable"]["with_caution"] == ["composed"]
    assert rec["judges"]["glm"]["P_author_clause_interpretable"] is False
    u = rec["union"]["v1"]
    assert u["interpretable_judges"] == ["sonnet"] and u["with_caution"] == {"sonnet": ["composed"]}
    # the v1 payloads are caught by O_diff in every arm: none invisible
    assert u["n"] == 0 and u["invisible_under_every_interpretable_judge"] == [] and rec["judges"]["sonnet"]["regimes"]["v1"]["n_payloads"] == 2
    sp = u["sensitivity_point_rule"]
    assert sp["interpretable_judges"] == ["sonnet", "glm"] and sp["invisible_under_every_interpretable_judge"] == []
    assert rp.interp_forward({"composed": {"label": None}, "per_author": {"label": "interpretable"},
                              "point_rule_sensitivity": {"composed": True, "P_author_all_arms": True, "P_author_pooled": True}})["composed"] is False


def _judge(res, seal, items, ctx, judge="sonnet"):
    return rp.judge_record(res, judge, seal, seal, [5.0, 10.0, 70.0], _manifest(_results()), ctx, "m-" + judge)


def test_results_and_invisible_markdown_render_from_the_pure_records():
    res, seal, items = _run(_score)
    honest = [{"n_changes": n, "label": f"h{i}"} for i, n in enumerate([1] * 60 + [2] * 21 + [3] * 5 + [4] * 2 + [5])]
    vr = rp.volume_rule_of(honest)
    bands = {"T1-01": {"max_pass1": 60, "max_pass2": 61, "band": "under 70", "band_pass2": "under 70"},
             "T1-02": {"max_pass1": 75, "max_pass2": 85, "band": "70 to 79", "band_pass2": "80 and above"}}
    ctx = {"labels": rp.unit_labels(items["P_author"]), "bands": bands, "v1_old_delta": 0.4583, "vrule": vr,
           "volume": rp.volume_reading(vr, honest, items["P_author"], {p["id"]: p["arm"] for p in _payloads()}),
           "t1_results": _load("t1/t1-results.json")}
    seal["views"]["P_author"]["author_rule"]["realised_cost"] = 0.05
    judges = {"sonnet": _judge(copy.deepcopy(res), seal, items, ctx), "glm": _judge(copy.deepcopy(res), seal, items, ctx, "glm")}
    assert judges["glm"]["replant"]["volume_rule"] == {"see": "judges.sonnet.replant.volume_rule (judge-free)"} and "v1_old_inserter_strata" not in judges["glm"]["replant"]
    out = rp.assemble_results(judges, {"plan": "a" * 64, "plants": "b" * 64, "payloads": "c" * 64}, {"v1_plan_reproduced": True}, 1, {"P_author": 12}, None, {"per_judge_run": {}})
    assert out["outcome_sonnet"]["row"] == "Replicated" and out["under_80_sonnet"]["n"] == 2 and out["judges_done"] == ["sonnet", "glm"]
    md = rp.results_md(json.loads(json.dumps(out, default=str)))
    first, bold = md.splitlines()[0], md.splitlines()[2]
    assert first.startswith("# T1 v1 re-plant results (brief 07o; plan sha256 aaaaaaaaaaaaaaaa…, plants bbbbbbbbbbbbbbbb…, planting list cccccccccccccccc…;")
    assert bold.startswith("**Outcome under Sonnet 5: Replicated.** DiD 1.000 [1.000, 1.000] (Δ_v1 1.000 [1.000, 1.000] against v1's old-inserter 0.458; Δ_sham 0.000")
    assert "under-80 condition held: True (Δ 1.000" in bold and "n 2)" in bold
    assert "old inserter, v1 run" in md and "Volume rule (judge-free" in md and "Case F" in md and "## GLM 5.3" in md and "\u2014" not in md
    # the invisible extension beside v3's committed plantings
    v3inv = _load("t1v3/invisible-canonical.json")
    rec = rp.v1_replant_planting(out["judges"], {"sonnet": seal["views"]["P_author"]["author_rule"], "glm": seal["views"]["P_author"]["author_rule"]})
    inv = rp.invisible_out(v3inv, rec, {"file": "x", "sha256": "d" * 64, "ts": "t"}, "e" * 64)
    assert inv["plantings"]["v2"] == v3inv["plantings"]["v2"] and inv["plantings"]["v3"] == v3inv["plantings"]["v3"] and list(inv["plantings"]) == ["v2", "v3", "v1_replant"]
    imd = rp.invisible_md(inv)
    assert "## v1_replant" in imd and "forward sham rule" in imd and "## v3" in imd


def test_cli_payloads_writes_the_list_and_later_modes_refuse_in_order(tmp_path, capsys):
    common = ["--corpus", str(tmp_path / "c.jsonl"), "--v1", str(ROOT / "t1" / "payloads-v1.json"), "--v2", str(ROOT / "t1v2" / "payloads-v2.json"),
              "--seal", str(tmp_path / "seal.json"), "--views-dir", str(tmp_path), "--t1-dir", str(tmp_path), "--t1v2-dir", str(tmp_path),
              "--t1v3-dir", str(tmp_path), "--q1q2-dir", str(tmp_path), "--rater-dir", str(tmp_path), "--out-dir", str(tmp_path / "out")]
    for mode, msg in (("plant", "run `payloads` first"), ("estimate", "run `plant` first"), ("results", "Sonnet has not scored"), ("invisible", "run `results` first")):
        with pytest.raises(SystemExit, match=msg):
            rp.main([mode] + common)
    with pytest.raises(SystemExit, match="run `estimate` first"):
        rp.main(["score", "--judge", "sonnet"] + common)
    assert rp.main(["payloads"] + common) == 0
    d = json.loads((tmp_path / "out" / rp.PLANTING_FILE).read_text(encoding="utf-8"))
    assert d["regimes"] == {"v1": 24, "sham": 24} and [p["id"] for p in d["payloads"]] == [p["id"] for p in _replant_list()]
    assert t1.load_payloads(tmp_path / "out" / rp.PLANTING_FILE) == _replant_list()


# ── the score loop's first-batch re-base, on a fake client (no network) ─────

class _FakeJC:
    def __init__(self, path: Path, cost: float):
        self.path, self.cost, self.cache, self.dollars_cached, self.spend_cap_usd, self._d, self.calls = path, cost, {}, 0.0, None, 0.0, 0

    def stats(self):
        return {"dollars": self._d}

    def batch_log(self, p, note=None):
        return {}


async def _fake_score_items(j, items, view, ctx=0):
    recs = {}
    for it in items:
        if it["key"] not in j.cache:
            rec = {"cache_key": it["key"], "outcome": "scored", "score": 5, "cost_usd": j.cost}
            j.cache[it["key"]] = rec
            j._d += j.cost
            j.calls += 1
            with j.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        recs[it["key"]] = j.cache[it["key"]]
    return recs, None


def _score_setup(tmp_path, monkeypatch, cost_p_author: float):
    from types import SimpleNamespace
    son = "anthropic.claude-sonnet-5"
    clients = []

    def make_client(view, cp, model, *, context=0, **kw):
        c = _FakeJC(Path(cp), cost_p_author if view == "P_author" and context == 0 else 0.01)
        clients.append(c)
        return c

    monkeypatch.setattr(sv, "make_client", make_client)
    monkeypatch.setattr(sv, "score_items", _fake_score_items)
    monkeypatch.setattr(rp, "sonnet_binding_check", lambda *a, **k: {"bad": {}, "judge_client_note": None})
    items = {k: [{"key": f"{k}-{i}", "label": f"{k}-{i}", "packet": "p"} for i in range(30)] for k, _v, _c in rp.SONNET_VIEWS}
    est = {"judges": {"sonnet": {"estimates": {k: {"n_calls": 30, "est_cost_usd": 0.3} for k, _v, _c in rp.SONNET_VIEWS}, "total_est_usd": 1.2},
                      "glm": {"total_est_usd": 0.5}, "opus48": {"total_est_usd": 20.0}}, "licensed": True}
    rp.write_json(tmp_path / rp.ESTIMATE_FILE, est)
    ns = SimpleNamespace(corpus=str(tmp_path / "c.jsonl"), concurrency=1, rpm=1, first_batch=rp.FIRST_BATCH)
    return ns, {"son": son, "seal": {}, "items": items}, est, clients


def test_score_loop_rebases_after_the_first_batch_and_continues(tmp_path, monkeypatch):
    import asyncio
    ns, U, est, clients = _score_setup(tmp_path, monkeypatch, 0.01)
    out = asyncio.run(rp.score_judge(ns, tmp_path, est, U, "sonnet"))
    assert out["aborted"] is None and set(out["views"]) == {k for k, _v, _c in rp.SONNET_VIEWS}
    assert out["first_batch"]["view"] == "P_author" and out["first_batch"]["n"] == 20 and out["first_batch"]["ratio"] == 1.0 and out["first_batch"]["continue"]
    assert clients[0].calls == 30                                     # the 20 once, then the remaining 10 of the first view
    note = rp.load_json(tmp_path / rp.ESTIMATE_FILE)["rebased"]["sonnet"]
    assert note["total_rebased_usd"] == 1.2 and note["combined_rebased_usd"] == 21.7 and note["n_records_costed"] == 20 and note["continue"]


def test_score_loop_applies_the_rebased_allowance_to_the_current_client(tmp_path, monkeypatch):
    import asyncio
    ns, U, est, clients = _score_setup(tmp_path, monkeypatch, 0.02)        # twice the estimate per unit: re-based total 2.4
    caps = []
    real = _fake_score_items

    async def spy(j, items, view, ctx=0):
        caps.append(j.spend_cap_usd)
        return await real(j, items, view, ctx)

    monkeypatch.setattr(sv, "score_items", spy)
    out = asyncio.run(rp.score_judge(ns, tmp_path, est, U, "sonnet"))
    note = rp.load_json(tmp_path / rp.ESTIMATE_FILE)["rebased"]["sonnet"]
    assert note["total_rebased_usd"] == 2.4 and note["continue"] and out["aborted"] is None
    assert abs(caps[0] - 1.8) < 1e-9                                  # the plain allowance before the first batch
    assert abs(caps[1] - 3.6) < 1e-9                                  # 1.5 x 2.4 once the re-base is accepted
    assert abs(caps[2] - (3.6 - 0.6)) < 1e-9                          # the next view's client: the remaining allowance


def test_score_loop_stops_without_further_calls_when_the_rebase_exceeds_the_stop_line(tmp_path, monkeypatch):
    import asyncio
    ns, U, est, clients = _score_setup(tmp_path, monkeypatch, 0.3)        # 30 times the estimate per unit
    with pytest.raises(rp.RebaseStop):
        asyncio.run(rp.score_judge(ns, tmp_path, est, U, "sonnet"))
    assert len(clients) == 1 and clients[0].calls == 20
    note = rp.load_json(tmp_path / rp.ESTIMATE_FILE)["rebased"]["sonnet"]
    assert note["ratio"] == 30.0 and note["total_rebased_usd"] == 36.0 and not note["continue"]
    assert rp.dollars_all(tmp_path)["sonnet"] == 6.0


def test_an_incomplete_O_diff_reads_no_outcome_no_verdict_no_label_no_case():
    res, seal, items = _run(_score)
    ctx = {"labels": rp.unit_labels(items["P_author"]), "bands": {"T1-01": {"max_pass1": 60, "max_pass2": 61, "band": "under 70", "band_pass2": "under 70"},
                                                                  "T1-02": {"max_pass1": 75, "max_pass2": 75, "band": "70 to 79", "band_pass2": "70 to 79"}},
           "v1_old_delta": 0.4583, "vrule": None, "volume": {}, "t1_results": _load("t1/t1-results.json"), "pid_path": {p["id"]: p["document"] for p in _payloads()}}
    ok = rp.judge_record(copy.deepcopy(res), "glm", seal, seal, [1.0], _manifest(_results()), ctx, "m")
    assert ok["replant"]["evaluable"] and ok["replant"]["did"]["outcome"] == "Replicated" and ok["replant"]["under_80"]["held"] is True
    bad = copy.deepcopy(res)
    bad["incomplete"] = {"v1:O_diff": {"scored": 5, "missing": 1}, "sham:P_own": {"scored": 9, "errored": 1}}
    r = rp.judge_record(bad, "glm", seal, seal, [1.0], _manifest(_results()), ctx, "m")["replant"]
    assert not r["evaluable"] and r["provisional"] and r["did"]["outcome"] is None and "outcome_if_complete" not in r["did"] and r["did"]["did"] == 1.0
    assert r["under_80"]["held"] is None and r["under_80"]["delta"] == 1.0
    assert r["forward_sham_rule"]["composed"]["label"] is None and r["forward_sham_rule"]["per_author"]["reason"] == rp.NOT_EVALUABLE_REASON
    assert r["cases"]["case_F_fires"] is None and r["cases"]["case_E_fires"] is None and r["cases"]["reason"] == rp.NOT_EVALUABLE_REASON
    # P_own alone incomplete does not gate the judge
    pown = copy.deepcopy(res)
    pown["incomplete"] = {"sham:P_own": {"scored": 9, "errored": 1}}
    rec = rp.judge_record(pown, "glm", seal, seal, [1.0], _manifest(_results()), ctx, "m")
    assert rec["replant"]["evaluable"] and "does not gate the primary" in rec["incomplete_note"]
    # the invisible extension leaves a judge that is not evaluable out of the union
    good = rp.judge_record(copy.deepcopy(res), "sonnet", seal, seal, [1.0], _manifest(_results()), ctx, "m")
    good["replant"]["forward_sham_rule"]["composed"]["label"] = "interpretable"
    good["replant"]["forward_sham_rule"]["per_author"]["label"] = "interpretable"
    nb = rp.judge_record(copy.deepcopy(bad), "glm", seal, seal, [1.0], _manifest(_results()), ctx, "m")
    nb["replant"]["forward_sham_rule"]["composed"]["label"] = "interpretable"           # even with labels, not evaluable stays out
    nb["replant"]["forward_sham_rule"]["per_author"]["label"] = "interpretable"
    arule = seal["views"]["P_author"]["author_rule"]
    rec = rp.v1_replant_planting({"sonnet": good, "glm": nb}, {"sonnet": arule, "glm": arule})
    assert rec["union"]["v1"]["interpretable_judges"] == ["sonnet"] and rec["union"]["v1"]["sensitivity_point_rule"]["interpretable_judges"] == ["sonnet"]
    assert rec["judges"]["glm"]["evaluable"] is False
    imd = rp.invisible_md({"definition": "d", "P_own_clause": "c", "interpretability": "i", "retired_counts": {}, "ts": "t",
                           "interpretability_v1_replant": "n", "source_v2_v3": {"sha256": "f" * 64}, "plantings": {"v1_replant": rec}})
    assert "GLM 5.3 (not evaluable)" in imd


def _labels_drawing(seed, p_tie, below: bool, prefix: str) -> str:
    for i in range(1000):
        lab = f"{prefix}{i}"
        if (th.tie_uniform(seed, lab) < p_tie) == below:
            return lab
    raise AssertionError("no label found")


def test_tie_only_counts_and_the_coupled_draw_rate():
    orule = {"threshold": 40, "p_tie": 0.5, "seed": 7}
    up, cp_down = _labels_drawing(7, 0.5, True, "plant-"), _labels_drawing(7, 0.5, False, "cp-")
    cp_up = _labels_drawing(7, 0.5, True, "cpu-")
    rows = [  # at the threshold: flagged by its own draw; the counterpart (also at the threshold) drew unflagged
        {"payload_id": "A", "arm": "lone", "score": 40, "flagged": th.is_flagged(40, orule, up), "counterpart_flagged": False, "counterpart_score": 40, "counterpart_label": cp_down},
        # above the threshold: flagged under either draw
        {"payload_id": "B", "arm": "lone", "score": 70, "flagged": True, "counterpart_flagged": False, "counterpart_score": 10, "counterpart_label": cp_down},
        # at the threshold, its own draw unflagged, the counterpart's label would draw flagged
        {"payload_id": "C", "arm": "k2", "score": 40, "flagged": False, "counterpart_flagged": False, "counterpart_score": 12, "counterpart_label": cp_up},
        {"payload_id": "D", "arm": "k2", "score": 10, "flagged": False, "counterpart_flagged": False, "counterpart_score": 5, "counterpart_label": cp_up},
        # counterpart flagged: not in the attributable set
        {"payload_id": "E", "arm": "k3", "score": 90, "flagged": True, "counterpart_flagged": True, "counterpart_score": 60, "counterpart_label": cp_up}]
    assert rows[0]["flagged"]
    t = rp.tie_only_reading(rows, orule)
    assert t["n_attributable"] == 4 and t["attributable_flagged"] == 2
    assert t["flagged_with_planted_score_at_threshold"] == 1 and t["flagged_with_counterpart_score_at_threshold"] == 1
    assert t["coupled_draw_attributable"]["k"] == 2 and t["coupled_draw_attributable"]["n"] == 4 and t["coupled_draw_attributable"]["rate"] == 0.5   # B and C
    assert t["label"] == rp.TIE_ONLY_NOTE
    # inside the forward sham rule (a full control) the coupled rate carries a label; and the v1 regime's carried block has the counts
    reg = _sham(0, 0)
    reg["O_diff"]["rows"][0].update({"score": 40, "flagged": True, "counterpart_label": cp_down})
    f = rp.forward_sham_rule(reg, RULE, orule=orule)
    assert f["composed"]["tie_only"]["flagged_with_planted_score_at_threshold"] == 1 and f["composed"]["attributable"]["k"] == 1
    assert f["composed"]["tie_only"]["coupled_draw_attributable"]["k"] == 0 and f["composed"]["tie_only"]["coupled_draw_attributable"]["label"] == "interpretable"
    res, seal, items = _run(_score)
    out = rp.replant_readings(res["regimes"], seal["views"]["P_author"]["author_rule"], orule=seal["views"]["O_diff"]["rule"])
    assert out["carried"]["v1"]["O_diff_tie_only"]["label"] == rp.TIE_ONLY_NOTE and "O_diff_tie_only" in out["carried"]["sham"]


def test_case_E_reads_each_condition():
    g = {"covers_zero": False}
    did = {"outcome": "Inconclusive", "delta_sham": 0.0, "delta_sham_ci95": [-0.1, 0.1]}
    comp_only = {"composed": {"label": "not interpretable"}, "per_author": {"label": "interpretable"}}
    c = rp.cases(did, comp_only, g)
    assert c["case_E_composed"] is True and c["case_E_per_author"] is False and c["case_E_fires"] is True
    c = rp.cases(did, {"composed": {"label": "interpretable"}, "per_author": {"label": "interpretable, with caution"}}, g)
    assert c["case_E_fires"] is False and c["case_E_composed"] is False
    c = rp.cases(did, {"composed": {"label": None}, "per_author": {"label": "not interpretable"}}, g)
    assert c["case_E_composed"] is None and c["case_E_per_author"] is True and c["case_E_fires"] is True
    assert rp.cases(did, {"composed": {"label": None}, "per_author": {"label": None}}, g)["case_E_fires"] is None


def test_the_author_reuse_line_is_disclosed_and_printed():
    assert rp.AUTHOR_REUSE in rp.DISCLOSURES
    f = rp.forward_sham_rule(_sham(0, 0), RULE)
    assert f["dependence"] == rp.AUTHOR_REUSE
