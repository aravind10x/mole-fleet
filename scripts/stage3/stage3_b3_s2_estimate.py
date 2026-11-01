#!/usr/bin/env python3
"""Brief 32 v3 (B3's S2): the estimate on the plan's units, the control items' lone-line check and the k = 2 arm's
cleanness test, from files on disk only ($0, no API call; no packet built, no token counted, no position drawn).

H1. Each view and judge is priced as units times Part 2's per-unit dollar basis (`power-simulation-v3b.json` 031795d5,
`unit_costs[cell]["used"]`, unchanged), as Part 2 did. The units are read from the rows of `plan.md` §2.6 (4c677dee)
and summed here. The gap to Part 2's T2+S2 figure is reproduced from Part 2's own `estimate` rows in two steps (net
counts, then the live rows' lone-line units stripped). Part 2's keys are read by the plan's names: in its `estimate`
rows `lone_units` are the item units and `singleton_units` the lone-line units.

H2 step 2. S1's enumeration (`lone_line_feasibility()` of `stage3_b3_s1_populations.py` 9ea7d687, pinned, imported and
called, never edited) applied to the net control items on brief 32's table `inserter-dry-run-v1.json`: the function is
called on a copy of the table in which the net control items carry the regime it reads ("candidate") and the
candidates do not, once for all of them and once per control item; its predicate `_two_by_different_authors` is reused
here for the per-pair counts the function does not return (per line, the number of the item's valid pairs under which
the line keeps two valid draws by different authors once both of the pair's authors are excluded), and the two are
checked against each other. Each net control item is then *all pairs pass*, *some fall short* or *none*. The add-on is
priced on the four per-agent views (plan §2.6's lone-line rows).

H3. A6.3 (d)'s k = 2 arm (plan §4.6) is priced by H1's method and tested against A6.22 (3)'s three conditions, read
from the application module (`stage3_t1.py` 240f4ed9) and brief 26's method (`stage3_b3_inserter_dry_run.py`), not run.

Ids, counts, dollars and hashes only: no item line, document text or rubric is read into the output.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s2_estimate.py
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_inserter_dry_run as dr  # noqa: E402  (brief 26's script: read, never changed or run here)
import stage3_b3_s1_populations as sp  # noqa: E402  (S1's enumeration: called, never changed)
import stage3_t1 as t1  # noqa: E402  (the application module: read, never changed)

ROOT = HERE.parents[1]
VERSION = "b3-s2-estimate/v0"
PLAN = "work/stage3/b3/plan.md"
V3B = "work/stage3/b3/power-simulation-v3b.json"
V0 = "work/stage3/b3/inserter-dry-run-v0.json"
V1 = "work/stage3/b3/inserter-dry-run-v1.json"
POPS = "work/stage3/b3/s1-populations-v0.json"
SHA = {PLAN: "4c677dee2e825e7250e1bb94893011d7b8464c967cc9b22817b39a204ed8d507",
       V3B: "031795d5f6ae160e4f55cc21bc8cc1594df9cd39015214f8843f22c4d538664c",
       V0: "edd289ce14eae1be6d131562600b482539d0f7f3903fcdb33e524565c15af5e8",
       POPS: "f17e7a72430fc320f490340ddb3fb3dd741957d7dc098db00eff50c1e18f1ecf",
       "work/checks/stage3_b3_s1_populations.py": "9ea7d6879471eacbad1d2f85cc86ccf957bb864ac7882ae603c8ac3e848b7541",
       "work/checks/stage3_b3_inserter_dry_run.py": "999cb7375cdefe212335e307cef6120c702436be1c6d5270f621844750b3ddf5",
       "work/checks/stage3_t1.py": "240f4ed9465bf61c021e1c993371ef74f3167bd1ce7378c251da73a5196ac4b5",
       "work/checks/test_stage3_t1_line_arm.py": "0ee5057bcb59037a3fa16e821bda495f810e38e189ab79e0a1eda8917c94559f"}
COPY_SCRIPT = "work/checks/stage3_b3_inserter_dry_run_v1.py"
PER_AGENT = ("dossier_iso:opus48", "P_author:opus48", "dossier_iso:sonnet", "P_author:sonnet")
LIVE = ("dossier_live:opus48", "dossier_live:sonnet")
PLACEMENTS = 2                 # T2+S2: two placements per item and per lone line
GROSS_ITEM, GROSS_LONE = 248, 468   # Part 2's P4 units per view at T2+S2 (gross 124 items, 234 lone lines)
PART2_LAYOUT = "T2+S2"
# the review session's and the coordinator's figures, checked here and never adopted
CHECK = {"part2": 98.17, "net_counts": 91.86, "h1": 68.17, "addon_max": 8.45, "part2_addon": 15.99, "k2": 3.06}
K2_TAG = 5
CONTROL_TAG = 6


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ids_sha256(ids) -> str:
    return sp.ids_sha256(ids)


# ── H1 ────────────────────────────────────────────────────────────────────────────────────────────

def cell_of(view: str) -> str:
    """Plan §2.6's view and judge -> Part 2's cell name (`dossier_iso` = `P_author_doc` isolated, `dossier_live` =
    `P_author_doc` live, `P_author` = `P_author` zero-context; opus48, sonnet, sol)."""
    v = view.replace("*", "")
    if "`P_author_doc`" in v and "isolated" in v:
        kind = "dossier_iso"
    elif "`P_author_doc`" in v and "live" in v:
        kind = "dossier_live"
    elif "`P_author`" in v and "zero-context" in v:
        kind = "P_author"
    elif "`O_diff`" in v:
        kind = "O_diff"
    else:
        raise ValueError(f"unmapped view: {view!r}")
    judges = [j for s, j in (("Opus 4.8", "opus48"), ("Sonnet 5", "sonnet"), ("GPT-6 Sol", "sol")) if s in v]
    if len(judges) != 1:
        raise ValueError(f"no single judge in: {view!r}")
    return f"{kind}:{judges[0]}"


def _units(cell: str) -> int:
    m = re.match(r"\s*\**\s*([\d,]+)", cell)
    if not m:
        raise ValueError(f"no unit count in {cell!r}")
    return int(m.group(1).replace(",", ""))


def plan_units(text: str) -> dict:
    """The rows of plan §2.6's table, and its stated totals."""
    sec = text.split("### 2.6 Units per view (net)", 1)[1].split("\n## ", 1)[0]
    rows, stated = [], None
    for ln in sec.splitlines():
        if not ln.startswith("| ") or ln.startswith("| view") or set(ln) <= set("|- "):
            continue
        c = [x.strip() for x in ln.strip().strip("|").split("|")]
        if c[0].strip("*").strip() == "total":
            stated = {"item_units": _units(c[1]), "lone_units": _units(c[2]), "units": _units(c[3])}
            continue
        rows.append({"view": c[0], "cell": cell_of(c[0]), "item_units": _units(c[1]), "lone_units": _units(c[2]),
                     "lone_units_cell": c[2], "role": c[3]})
    return {"rows": rows, "stated_totals": stated}


def basis(unit_costs: Mapping[str, Mapping[str, float]], cell: str) -> dict:
    uc = unit_costs[cell]
    src = [k for k, v in uc.items() if k != "used" and v == uc["used"]]
    return {"used": uc["used"], "source": src[0] if len(src) == 1 else src,
            "listed": {k: v for k, v in uc.items() if k != "used"}}


def price(rows: Sequence[Mapping[str, Any]], unit_costs: Mapping[str, Any]) -> dict:
    out = []
    for r in rows:
        b = basis(unit_costs, r["cell"])
        out.append({**{k: r[k] for k in ("view", "cell", "item_units", "lone_units")}, "basis": b["used"],
                    "basis_source": b["source"], "bases_listed": b["listed"],
                    "dollars": (r["item_units"] + r["lone_units"]) * b["used"]})
    return {"rows": out, "item_units": sum(r["item_units"] for r in out), "lone_units": sum(r["lone_units"] for r in out),
            "units": sum(r["item_units"] + r["lone_units"] for r in out), "dollars": sum(r["dollars"] for r in out)}


def part2_gap(est: Mapping[str, Any], unit_costs: Mapping[str, Any], net_item: int, net_lone: int) -> dict:
    """Part 2's T2+S2 figure, then (1) net counts on every cell Part 2 priced, then (2) the live rows' lone-line units
    stripped; each step from Part 2's own rows, its keys read by the plan's names."""
    rows = est["rows"]
    item = {c: r["lone_units"] for c, r in rows.items()}          # Part 2's `lone_units` are the item units
    lone = {c: r["singleton_units"] for c, r in rows.items()}     # Part 2's `singleton_units` are the lone-line units
    used = {c: unit_costs[c]["used"] for c in rows}
    p2 = sum((item[c] + lone[c]) * used[c] for c in rows)
    s1 = sum((net_item * (item[c] > 0) + net_lone * (lone[c] > 0)) * used[c] for c in rows)
    s2 = sum((net_item * (item[c] > 0) + net_lone * (lone[c] > 0 and c not in LIVE)) * used[c] for c in rows)
    strip_gross = sum(lone[c] * used[c] for c in LIVE if c in rows)
    return {"part2_dollars_file": est["dollars"], "part2_dollars_recomputed": p2,
            "part2_item_units_per_cell": sorted(set(item.values())), "part2_lone_units_per_cell": dict(Counter(lone.values())),
            "step1_net_counts": s1, "step1_less": p2 - s1,
            "step2_live_lone_stripped": s2, "step2_less": s1 - s2,
            "plan9_remainder_after_live_strip_gross": p2 - strip_gross,
            "plan9_pro_rata_73_of_78": (p2 - strip_gross) * 73 / 78,
            "ratios": {"item": net_item / GROSS_ITEM, "lone": net_lone / GROSS_LONE}}


# ── H2 step 2 ─────────────────────────────────────────────────────────────────────────────────────

def item_pairs(item: Mapping[str, Any]) -> list[tuple[tuple[str, str], tuple[str, str]]]:
    """Every pair the pair rule can draw, as `lone_line_feasibility()` builds it (two valid item draws on different
    days by different authors)."""
    ip = [tuple(x) for x in item["draws"]["valid_draws"]]
    return [(p, q) for k, p in enumerate(ip) for q in ip[k + 1:] if p[0] != q[0] and p[1] != q[1]]


def line_ok(draws: Sequence[tuple[str, str]], pair, different_days: bool) -> bool:
    """The line keeps two valid draws by different authors with both of the pair's authors excluded (A6.5 (iii))."""
    p, q = pair
    return sp._two_by_different_authors([x for x in draws if x[1] not in (p[1], q[1])], different_days)


def classify(n_pairs: int, pairs_all_ok: int) -> str:
    if n_pairs == 0:
        return "none: no valid pair"
    if pairs_all_ok == 0:
        return "none: no pair meets the need"
    return "all pairs pass" if pairs_all_ok == n_pairs else "some fall short"


def control_check(item: Mapping[str, Any]) -> dict:
    pairs = item_pairs(item)
    lines = [[tuple(x) for x in ln["valid_draws"]] for ln in item["lone_lines"]]
    if len(lines) != 3:
        raise ValueError(f"{item['item_id']}: {len(lines)} lone lines, not three")
    out: dict[str, Any] = {"item_id": item["item_id"], "writer": item["writer"], "n_pairs": len(pairs),
                           "lines": [], "variants": {}}
    for variant, days in (("different_authors", False), ("beside_different_days_too", True)):
        ok = [[line_ok(dl, pr, days) for pr in pairs] for dl in lines]
        all_ok = [all(ok[i][k] for i in range(3)) for k in range(len(pairs))]
        out["variants"][variant] = {
            "pairs_meeting_need_per_line": [sum(x) for x in ok],
            "pairs_all_three_lines_met": sum(all_ok),
            "pairs_short": len(pairs) - sum(all_ok),
            "lines_short_under_some_pair": [i + 1 for i in range(3) if not all(ok[i])],
            "class": classify(len(pairs), sum(all_ok))}
    for i, (dl, ln) in enumerate(zip(lines, item["lone_lines"])):
        out["lines"].append({"role": i + 1, "valid_draws": ln["n_valid"], "drawable": ln["n_drawable"],
                             "two_valid_by_different_authors": sp._two_by_different_authors(dl, False)})
    return out


def as_function_reads(dry: Mapping[str, Any], ids: set[str]) -> dict:
    """A copy of the table in which only the items in `ids` carry the regime `lone_line_feasibility()` reads."""
    c = copy.deepcopy(dict(dry))
    for it in c["items"]:
        it["regime"] = "candidate" if it["item_id"] in ids else f"{it['regime']} (not read in this call)"
    return c


def function_fields(dry: Mapping[str, Any], ids: Sequence[str]) -> dict:
    return {"all": sp.lone_line_feasibility(as_function_reads(dry, set(ids)), set()),
            "per_item": {i: sp.lone_line_feasibility(as_function_reads(dry, {i}), set()) for i in ids}}


def agrees_with_function(chk: Mapping[str, Any], f: Mapping[str, Any]) -> bool:
    v, vd = chk["variants"]["different_authors"], chk["variants"]["beside_different_days_too"]
    n = chk["n_pairs"]
    return (f["net_candidate_lines"] == 3
            and f["two_valid_by_different_authors"] == sum(x["two_valid_by_different_authors"] for x in chk["lines"])
            and f["every_item_pair_leaves_two_by_different_authors"] == sum(c == n for c in v["pairs_meeting_need_per_line"])
            and f["beside_every_item_pair_leaves_two_on_different_days_by_different_authors"]
            == sum(c == n for c in vd["pairs_meeting_need_per_line"])
            and f["beside_item_pair_cases"] == 3 * n
            and f["beside_item_pair_cases_short_with_different_days"] == sum(n - c for c in vd["pairs_meeting_need_per_line"]))


def compare_items(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict:
    """`items[]` of the two tables, field by field: the differing (item, field) pairs."""
    a = {it["item_id"]: it for it in old["items"]}
    b = {it["item_id"]: it for it in new["items"]}
    diffs = []
    if set(a) != set(b):
        diffs.append({"item_id": None, "field": "item ids"})
    for k in sorted(set(a) & set(b)):
        for f in sorted(set(a[k]) | set(b[k])):
            if a[k].get(f) != b[k].get(f):
                diffs.append({"item_id": k, "regime": b[k]["regime"], "field": f})
    return {"items": len(b), "diffs": diffs,
            "only_control_lone_lines": all(d["field"] == "lone_lines" and d.get("regime") == "control" for d in diffs)}


# ── H3 ────────────────────────────────────────────────────────────────────────────────────────────

def k2_cleanness() -> dict:
    """A6.22 (3)'s three conditions, read from the module and brief 26's method; nothing is applied."""
    src_vd = inspect.getsource(t1.ValidDraws.__init__)
    src_enum = inspect.getsource(dr.enumerate_draws)
    src_run = inspect.getsource(dr.run)
    which_k2 = t1.PartSInserter._which("k2")
    reads = sorted(set(re.findall(r'it\["(\w+)"\]', src_vd)) | set(re.findall(r'it\.get\("(\w+)"\)', src_vd)))
    i_ok = which_k2 is not None
    ii_ok = True
    iii_ok = ("k2" in src_enum) or ("k2" in src_run)
    return {
        "(i) no new application code": {
            "passes": i_ok,
            "finding": ("restricted mode maps an arm to the table's draws through `PartSInserter._which`, which returns "
                        f"{which_k2!r} for k2 (\"item\" for the lone arm, a role index for a line arm); `plant` and "
                        "`apply_at` then refuse k2 with RF_ARM (\"" + t1.RF_ARM + "\"), and brief 27's test "
                        "`test_every_restricted_draw_comes_from_the_valid_set` asserts that refusal for k2 and k3. "
                        "`apply_at` places one (day, author); a k = 2 placement is two roles on two days and two "
                        "authors. `ValidDraws` reads only the keys " + ", ".join(f"`{k}`" for k in reads) + " per item "
                        "(no k = 2 split). Default mode has the k2 arm (`Inserter._roles`: lines [0, 1] on one author, "
                        "[2] on another; `layout` draws days i, i + 1 for i in {0, 1}) but without the valid-draw "
                        "restriction, which A6.17.11 requires in code; so the arm needs new code in restricted mode.")},
        "(ii) no new arm or stream beyond tag 5": {
            "passes": ii_ok,
            "finding": f"plan §3 reserves tag {K2_TAG} for the k = 2 arm; no further tag or stream change is needed for it."},
        "(iii) valid draws at $0 by brief 26's method, read by restricted mode unchanged": {
            "passes": iii_ok,
            "finding": ("brief 26's `enumerate_draws` enumerates the lone arm's (day, author) draws over `days[:2]` with one "
                        "author per draw, and `run` adds one-statement lone lines; neither enumerates a k = 2 split (two roles, "
                        "two authors, days i and i + 1, the third bank day included, with the roles' interference). A k = 2 "
                        "table would need new enumeration code, and restricted mode has no key to read it by (i).")},
        "clean": i_ok and ii_ok and iii_ok}


# ── build ─────────────────────────────────────────────────────────────────────────────────────────

def build(root: Path = ROOT) -> dict:
    for rel, want in SHA.items():
        got = sha256_file(root / rel)
        if got != want:
            raise SystemExit(f"{rel}: sha256 {got[:8]} is not the pinned {want[:8]}")
    plan_text = (root / PLAN).read_text(encoding="utf-8")
    v3b = json.loads((root / V3B).read_text(encoding="utf-8"))
    unit_costs, est = v3b["unit_costs"], v3b["estimate"][PART2_LAYOUT]
    pops = json.loads((root / POPS).read_text(encoding="utf-8"))["populations"]
    v0 = json.loads((root / V0).read_text(encoding="utf-8"))
    v1_raw = (root / V1).read_bytes()
    v1 = json.loads(v1_raw)

    # H1
    pu = plan_units(plan_text)
    h1 = price(pu["rows"], unit_costs)
    st = pu["stated_totals"]
    sums_equal = (h1["item_units"], h1["lone_units"], h1["units"]) == (st["item_units"], st["lone_units"], st["units"])
    net_item = {r["item_units"] for r in pu["rows"]}
    net_lone = {r["lone_units"] for r in pu["rows"] if r["lone_units"]}
    if len(net_item) != 1 or len(net_lone) != 1:
        raise SystemExit(f"plan §2.6: item units {net_item}, lone-line units {net_lone}: not one value each")
    gap = part2_gap(est, unit_costs, net_item.pop(), net_lone.pop())
    lone_cells = sorted(r["cell"] for r in pu["rows"] if r["lone_units"])

    # H2 step 1 (recorded): the table, against brief 26's, and S1's candidate figures from it
    cmp = compare_items(v0, v1)
    drops = set(v1["drop_list"]["ids"])
    cand = sp.lone_line_feasibility(v1, drops)
    s1_lone = json.loads((root / POPS).read_text(encoding="utf-8"))["lone_lines"]
    if cand != s1_lone:
        raise SystemExit(f"the candidates' figures do not reproduce from {V1}: {cand} against {s1_lone}")

    # H2 step 2
    controls = sorted((it for it in v1["items"] if it["regime"] == "control" and it["item_id"] not in drops),
                      key=lambda it: it["item_id"])
    ids = [it["item_id"] for it in controls]
    plan_controls = pops["controls"]["net_pair"]
    if (len(ids), ids_sha256(ids)) != (plan_controls["n"], plan_controls["ids_sha256"]):
        raise SystemExit("the net control items are not the plan's (§1.1)")
    checks = [control_check(it) for it in controls]
    ff = function_fields(v1, ids)
    agree = {c["item_id"]: agrees_with_function(c, ff["per_item"][c["item_id"]]) for c in checks}
    if not all(agree.values()):
        raise SystemExit(f"the per-pair enumeration and the function disagree: {[k for k, v in agree.items() if not v]}")
    agg_keys = ("net_candidate_lines", "two_valid_by_different_authors", "every_item_pair_leaves_two_by_different_authors",
                "beside_every_item_pair_leaves_two_on_different_days_by_different_authors", "beside_item_pair_cases",
                "beside_item_pair_cases_short_with_different_days")
    if any(ff["all"][k] != sum(ff["per_item"][i][k] for i in ids) for k in agg_keys):
        raise SystemExit("the function's figures over all control items are not the sum of its per-item figures")
    classes = {v: dict(Counter(c["variants"][v]["class"] for c in checks))
               for v in ("different_authors", "beside_different_days_too")}
    none_ids = [c["item_id"] for c in checks if c["variants"]["different_authors"]["class"].startswith("none")]
    remaining = len(ids) - len(none_ids)
    pa_basis = sum(unit_costs[c]["used"] for c in PER_AGENT)
    addon_units = remaining * 3 * PLACEMENTS
    addon = addon_units * pa_basis
    addon_max = len(ids) * 3 * PLACEMENTS * pa_basis
    six = PER_AGENT + LIVE
    part2_addon = est["controls_singleton_addon_dollars"]
    gross_controls = sum(1 for it in v1["items"] if it["regime"] == "control")
    addon_gap = {"part2_gross": part2_addon,
                 "part2_recomputed": gross_controls * 3 * PLACEMENTS * sum(unit_costs[c]["used"] for c in six),
                 "net_pro_rata": part2_addon * len(ids) / gross_controls,
                 "live_cells_stripped": len(ids) * 3 * PLACEMENTS * sum(unit_costs[c]["used"] for c in LIVE),
                 "units_part2": gross_controls * 3 * PLACEMENTS, "cells_part2": len(six), "cells_here": len(PER_AGENT)}

    # H3
    cert = pops["certified"]["net_pair"]
    k2_cells = [c for c in unit_costs if c not in ("dossier_iso:sonnet", "dossier_live:sonnet")]
    k2_units = cert["n"] * PLACEMENTS
    k2 = k2_units * sum(unit_costs[c]["used"] for c in k2_cells)
    k2_both_authors = k2 + k2_units * sum(unit_costs[c]["used"] for c in k2_cells if not c.startswith("O_diff"))
    clean = k2_cleanness()

    forms = [{"form": "H1 + H2", "dollars": h1["dollars"] + addon, "stop_2x": 2 * (h1["dollars"] + addon)}]
    if addon != addon_max:
        forms.append({"form": "H1 + H2 at its most (all net control items)", "dollars": h1["dollars"] + addon_max,
                      "stop_2x": 2 * (h1["dollars"] + addon_max)})
    if clean["clean"]:
        forms.append({"form": "H1 + H2 + H3", "dollars": h1["dollars"] + addon + k2, "stop_2x": 2 * (h1["dollars"] + addon + k2)})

    return {
        "version": VERSION, "brief": "32 v3 (S2)", "written": datetime.now().astimezone().isoformat(timespec="seconds"),
        "inputs_sha256": {**dict(SHA), V1: hashlib.sha256(v1_raw).hexdigest(), COPY_SCRIPT: sha256_file(root / COPY_SCRIPT)},
        "script": {"path": "work/checks/stage3_b3_s2_estimate.py", "sha256": sha256_file(Path(__file__))},
        "h1": {"method": "units times Part 2's per-unit basis (`unit_costs[cell].used`), as Part 2 did; no packet, token or draw",
               "rows": h1["rows"], "item_units": h1["item_units"], "lone_units": h1["lone_units"], "units": h1["units"],
               "dollars": h1["dollars"], "plan_stated_totals": st, "sums_equal_plan": sums_equal,
               "lone_line_cells": lone_cells, "gap": gap, "checks": {k: CHECK[k] for k in ("part2", "net_counts", "h1")}},
        "h2": {"table": {"path": V1, "sha256": hashlib.sha256(v1_raw).hexdigest(), "version": v1.get("version"),
                         "script": v1.get("script"), "compare_to_v0": cmp, "candidates_reproduced": cand},
               "how": ("the pinned `lone_line_feasibility()` called on a copy of the table in which the net control items carry "
                       "the regime it reads and the candidates do not (all at once and per item); the per-pair counts by this "
                       "script with the function's own predicate `_two_by_different_authors`; the two agree on every item"),
               "function_fields_all_controls": ff["all"], "function_fields_per_item": ff["per_item"],
               "agrees_with_function": agree, "controls": checks, "net_controls": {"n": len(ids), "ids_sha256": ids_sha256(ids)},
               "classes": classes, "none_ids": none_ids,
               "addon": {"remaining_items": remaining, "units_per_view": addon_units, "views": list(PER_AGENT),
                         "basis_sum_per_unit": pa_basis, "dollars": addon, "dollars_max_all_net": addon_max,
                         "check_max": CHECK["addon_max"], "gap_to_part2": addon_gap}},
        "h3": {"price": {"items": cert["n"], "ids_sha256": cert["ids_sha256"], "placements": PLACEMENTS,
                         "views": k2_cells, "units_per_view": k2_units, "dollars": k2, "check": CHECK["k2"],
                         "beside_both_authors_scored_on_per_agent_views": k2_both_authors},
               "cleanness": clean, "skipped": not clean["clean"]},
        "confirmation": forms,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 32: B3's S2 estimate and $0 checks")
    ap.add_argument("--out", default=str(ROOT / "work" / "stage3" / "b3" / "s2-estimate-v0.json"))
    ns = ap.parse_args(argv)
    res = build()
    Path(ns.out).write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"h1": res["h1"]["dollars"], "addon": res["h2"]["addon"]["dollars"],
                      "classes": res["h2"]["classes"], "k2_clean": res["h3"]["cleanness"]["clean"],
                      "confirmation": res["confirmation"], "sha256": sha256_file(Path(ns.out))}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
