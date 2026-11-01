"""Tests for brief 32's copy of brief 26's dry-run script (H2 step 1): the copy keeps brief 26's method, refuses to write
over the pinned v0 files, and, on its outputs, (a) the default run reproduces edd289ce's `items[]`, (b) the new table
differs from it only in the control items' `lone_lines`, (c) its provenance states its own run, (d) its summary fields
are recomputed or marked; then S1's candidate figures reproduce from the new table and brief 27's restricted mode reads
it unchanged. Counts, ids and hashes only.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_inserter_dry_run_v1.py
    (S2_SLOW=1 adds the role-order spot check, which re-runs brief 26's enumeration on one control item's lines)
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_inserter_dry_run as dr  # noqa: E402  (brief 26's pinned script)
import stage3_b3_inserter_dry_run_v1 as d1  # noqa: E402
import stage3_b3_s1_populations as sp  # noqa: E402
import stage3_t1 as t1  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
V0 = ROOT / "work/stage3/b3/inserter-dry-run-v0.json"
V1 = ROOT / "work/stage3/b3/inserter-dry-run-v1.json"
DEFAULT = ROOT / "work/stage3/b3/s2/dryrun-default/inserter-dry-run-v0.json"
POPS = ROOT / "work/stage3/b3/s1-populations-v0.json"
MODULE_SHA = "240f4ed9465bf61c021e1c993371ef74f3167bd1ce7378c251da73a5196ac4b5"
UNCHANGED = ("intended", "sent_of", "check_line", "line_ok", "joint_check", "statement_named", "map_module_reason",
             "drawable_authors", "chosen_sessions", "States", "_rng", "module_run", "run_draw", "pair_ok", "enumerate_draws",
             "static_checks", "_init_globals", "_task", "input_paths", "load_items", "guard_texts", "assert_clean",
             "module_line", "module_record", "decide", "top_reasons", "_agg", "aggregates", "reverse_case", "findings",
             "render_md")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _items(d: dict) -> dict:
    return {it["item_id"]: it for it in d["items"]}


def _diffs(old: dict, new: dict) -> list[tuple[str, str, str]]:
    a, b = _items(old), _items(new)
    assert set(a) == set(b)
    return [(k, b[k]["regime"], f) for k in sorted(a) for f in sorted(set(a[k]) | set(b[k])) if a[k].get(f) != b[k].get(f)]


# ── the copy itself ─────────────────────────────────────────────────────────────────────────────────

def test_the_pinned_script_is_unchanged_and_the_copy_names_it():
    assert _sha(Path(dr.__file__)) == d1.B26_SCRIPT_SHA256
    assert d1.B26_JSON_SHA256 == _sha(V0)


@pytest.mark.parametrize("name", UNCHANGED)
def test_the_copy_keeps_brief_26s_method(name):
    assert inspect.getsource(getattr(d1, name)) == inspect.getsource(getattr(dr, name))


def test_constants_are_brief_26s():
    for k in ("RUN_SEED", "RUNS_PER_DRAW", "MAX_SAMPLES", "NEED_ITEM", "NEED_LINE", "EXPECTED", "EXPECTED_POPS",
              "RATED_ARM", "V3_INSERTER_CLASS_SHA256", "OUT", "CORPUS", "VERSION"):
        assert getattr(d1, k) == getattr(dr, k), k


def test_the_lone_line_summary_defaults_to_the_candidates():
    rows = [{"regime": "candidate", "lone_lines": [{"n_drawable": 3, "n_valid": 2, "invalid_reasons": {}, "valid_authors": 2,
                                                    "pair_ok_distinct_authors": True, "literal_ok": True, "pair_ok_distinct_days": False}]},
            {"regime": "control", "lone_lines": [{"n_drawable": 5, "n_valid": 0, "invalid_reasons": {d1.R_MULTI: 5}, "valid_authors": 0,
                                                  "pair_ok_distinct_authors": False, "literal_ok": False, "pair_ok_distinct_days": False}]}]
    assert d1.lone_line_summary(rows) == dr.lone_line_summary(rows)
    c = d1.lone_line_summary(rows, "control")
    assert (c["lines"], c["drawable_draws"], c["valid_draws"], c["two_valid_distinct_authors"]) == (1, 5, 0, 0)


def test_the_copy_never_writes_over_the_pinned_v0_files(tmp_path):
    with pytest.raises(SystemExit):
        d1.output_paths(d1.OUT, False)
    pj, pm = d1.output_paths(d1.OUT, True)
    assert (pj.name, pm.name) == ("inserter-dry-run-v1.json", "inserter-dry-run-v1.md")
    pj, _pm = d1.output_paths(tmp_path, False)
    assert pj == tmp_path / "inserter-dry-run-v0.json"


# ── its outputs ─────────────────────────────────────────────────────────────────────────────────────

needs_default = pytest.mark.skipif(not DEFAULT.exists(), reason="the default-mode run has not been written")
needs_v1 = pytest.mark.skipif(not V1.exists(), reason="inserter-dry-run-v1.json has not been written")


@needs_default
def test_a_the_default_run_reproduces_brief_26s_items():
    v0, df = _load(V0), _load(DEFAULT)
    assert len(df["items"]) == 124 and _diffs(v0, df) == []
    assert df["drop_list"]["ids"] == v0["drop_list"]["ids"] and df["drop_list"]["net_n"] == v0["drop_list"]["net_n"]
    assert df["lone_lines"] == v0["lone_lines"] and df["totals"] == v0["totals"]
    assert df["lone_lines_controls"] is None and df["script"]["controls_lone_lines"] is False


@needs_v1
def test_b_only_the_control_items_lone_lines_differ():
    v0, v1 = _load(V0), _load(V1)
    diffs = _diffs(v0, v1)
    controls = sorted(i for i, it in _items(v1).items() if it["regime"] == "control")
    assert len(controls) == 22
    assert diffs == [(i, "control", "lone_lines") for i in controls]
    for i in controls:
        old, new = _items(v0)[i], _items(v1)[i]
        assert old["lone_lines"] == [] and len(new["lone_lines"]) == 3
        assert all(ln["lone_line"] is None for ln in new["lines"])      # brief 26's per-line field stays the candidates'
        assert new["drop"] == old["drop"]                                # the control arm's need is the item pair alone


@needs_v1
def test_c_the_new_table_states_its_own_run():
    v1 = _load(V1)
    s = v1["script"]
    assert v1["version"] == d1.VERSION_V1 and "32 v3" in v1["brief"]
    assert s["path"] == "work/checks/stage3_b3_inserter_dry_run_v1.py" and s["sha256"] == _sha(Path(d1.__file__))
    assert s["copy_of"]["sha256"] == s["copy_of"]["sha256_now"] == d1.B26_SCRIPT_SHA256
    assert s["controls_lone_lines"] is True and s["table_of_shape"]["sha256"] == _sha(V0)
    assert v1["module"]["sha256"] == MODULE_SHA and v1["module"]["fork_copy_identical"] is True
    assert v1["written"] != _load(V0)["written"] and v1["written"].startswith("2026-11-")


@needs_v1
def test_d_summary_fields_are_recomputed_or_marked():
    v0, v1 = _load(V0), _load(V1)
    rows = v1["items"]
    assert v1["lone_lines"] == v0["lone_lines"] == d1.lone_line_summary(rows)
    assert "candidates only" in v1["summary_scope"]["lone_lines"]
    assert v1["lone_lines_controls"] == d1.lone_line_summary(rows, "control") and v1["lone_lines_controls"]["lines"] == 66
    lone = [ld for r in rows for ld in r["lone_lines"]]
    assert v1["totals"]["lone_line_draws"] == sum(ld["n_drawable"] for ld in lone)
    assert v1["totals"]["lone_line_draws"] == v0["totals"]["lone_line_draws"] + v1["lone_lines_controls"]["drawable_draws"]
    assert v1["totals"]["item_draws"] == v0["totals"]["item_draws"]
    for k in ("aggregates", "drop_list", "reverse_case", "unresolved_stratum_members"):
        assert v1[k] == v0[k], k
    assert set(v1["summary_scope"]) >= {"lone_lines", "lone_lines_controls", "totals", "s1_restriction", "module_findings"}


@needs_v1
def test_the_candidates_figures_reproduce_from_the_new_table():
    v1 = _load(V1)
    got = sp.lone_line_feasibility(v1, set(v1["drop_list"]["ids"]))
    assert got == _load(POPS)["lone_lines"]
    assert list(got.values()) == [219, 219, 219, 177, 18018, 462]


@needs_v1
def test_restricted_mode_reads_the_new_table_unchanged():
    v1 = _load(V1)
    vd = t1.ValidDraws.load(V1)
    assert vd.sha256 == _sha(V1)
    for it in v1["items"]:
        e = vd.entries[it["item_id"]]
        assert e["item"] == [tuple(x) for x in it["draws"]["valid_draws"]]
        assert e["lines"] == [[tuple(x) for x in ln["valid_draws"]] for ln in it["lone_lines"]]
        if it["regime"] == "control":
            assert len(e["lines"]) == 3
            for i in range(3):
                assert vd.draws(it["item_id"], i) == e["lines"][i]
    v0d = t1.ValidDraws.load(V0)
    c0 = next(it["item_id"] for it in v1["items"] if it["regime"] == "control")
    with pytest.raises(t1.Refused):
        v0d.draws(c0, 0)                 # on edd289ce the restricted mode refuses every control line


@needs_v1
@pytest.mark.skipif(os.environ.get("S2_SLOW") != "1", reason="set S2_SLOW=1: re-runs brief 26's enumeration on one item's lines")
def test_role_order_spot_check_on_one_control_item():
    from stage3_t1v2_checks import DOCS
    v1 = _load(V1)
    d1._init_globals(d1.CORPUS, d1.sv.jc_mod.FORK / "bootstrap" / "org_template.yaml")
    ins, states = d1._G["ins"], d1._G["states"]
    items, _meta = d1.load_items(d1.input_paths())
    it = min((x for x in items if x["regime"] == "control"), key=lambda x: x["item_id"])
    day0 = {path: text for (_svc, path), text in d1.sv.seed_base().items() if path in DOCS}
    f0 = d1.static_checks(states, list(ins.days), it, day0)["found_day0"]
    want = _items(v1)[it["item_id"]]["lone_lines"]
    for i, st in enumerate(it["statements"]):
        single = {"id": f"{it['payload_id']}#L{i + 1}", "document": it["document"], "statements": [st], "arm": "singleton"}
        got = d1.enumerate_draws(ins, states, f"{it['item_id']}:{i + 1}", single, [st], True, [f0[i]])
        assert json.loads(json.dumps({k: v for k, v in got.items() if k != "per_line"})) == want[i], f"role {i + 1}"
