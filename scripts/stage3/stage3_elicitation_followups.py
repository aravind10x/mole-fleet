#!/usr/bin/env python3
"""Brief 30 Part 3: the two $0 follow-ups the coordinator asked for after the edit-application check (message of 8 Nov).

(1) The retention-adjusted forecast: `stage3_elicitation_forecast.forecast_retained` on the placeable stock, with the cases
    B (Muse Wonder's rounds 4 to 6 as planned, its observed placeable retention), A1 (an append-only constraint: Sol-like
    retention, yields as observed), A2 (A1 with the illegible yield scaled by the share of the illegible items whose
    mechanism has an append-only precedent) and A3 (A1 with the illegible rate of the append-only items written so far),
    beside C (no round 4: the placeable stock alone). GPT-6.1-sol writes no further round (note 16).
(2) The line forms: for every valid item, its pattern of operations and each line's content kind; the table of valid items by
    writer, form (append-only or replace-bearing) and class; and, for the quiet-but-illegible items, how many could have been
    written as three append lines (a mechanism with an append-only precedent among the valid items) and how many need a
    replaced line (no such precedent).

Counts, classes, mechanism labels and content kinds only: no statement, anchor or document text is read into an output.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_followups.py run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_elicitation_forecast as fc  # noqa: E402
import stage3_elicitation_matching as mt  # noqa: E402

VERSION = "elicitation-followups/v0"
PROJECT = HERE.parent.parent
PART3 = PROJECT / "work" / "stage3" / "elicitation" / "part3"
CHECK = PART3 / "application-check-round2-states-v0.json"
CLASS_KEYS = (mt.CERTIFIED, mt.ILLEGIBLE)


def _read(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _ops_label(lines: Sequence[tuple[str, str]]) -> str:
    c = Counter(op for op, _k in lines)
    return " + ".join(f"{c[op]} {op}" for op in ("append", "replace") if c.get(op))


# ── (2) the line forms ───────────────────────────────────────────────────────────────────────────

def line_forms(part3: Path, pairs: Sequence[tuple[str, int]]) -> list[dict]:
    """Every valid item of the given writer rounds: its class, mechanism, the (operation, content kind) of each of its lines, the
    pattern of operations and its form (append-only: three append lines; replace-bearing: at least one replaced line)."""
    out: list[dict] = []
    for writer, rnd in pairs:
        base = Path(part3) / f"round-{rnd}" / writer
        rec = _read(base / "round-record.json")["ids_by_class"]
        cls = {i: c for c, ids in rec.items() for i in ids}
        key = _read(base / "converted" / "key.json")["triples"]
        pays = {p["id"]: p for p in _read(base / "converted" / "payloads.json")["payloads"]}
        for iid in sorted(key):
            pay = pays[key[iid]["plantings"][0]["id"]]
            lines = [(str(s["op"]), str(s["kind"])) for s in pay["statements"]]
            out.append({"item_id": iid, "writer": writer, "round": rnd, "class": cls[iid], "mechanism": key[iid]["mechanism"],
                        "lines": lines, "ops": _ops_label(lines),
                        "form": "append-only" if all(op == "append" for op, _k in lines) else "replace-bearing"})
    return out


def _cell() -> dict:
    return {"valid": 0, "certified": 0, "quiet_but_illegible": 0, "other": 0}


def _add(cell: dict, cls: str) -> None:
    cell["valid"] += 1
    cell[cls if cls in CLASS_KEYS else "other"] += 1


def form_table(forms: Sequence[Mapping[str, Any]]) -> dict:
    """Valid items by writer, form and class (certified, quiet-but-illegible, every other class as `other`)."""
    out: dict[str, dict] = {}
    for f in forms:
        _add(out.setdefault(f["writer"], {}).setdefault(f["form"], _cell()), f["class"])
    return out


def mechanism_table(forms: Sequence[Mapping[str, Any]]) -> dict:
    """Valid items by mechanism, form and class, across writers, with the writers who wrote each form."""
    out: dict[str, dict] = {}
    for f in forms:
        c = out.setdefault(f["mechanism"], {}).setdefault(f["form"], dict(_cell(), writers=[]))
        _add(c, f["class"])
        if f["writer"] not in c["writers"]:
            c["writers"] = sorted(c["writers"] + [f["writer"]])
    return out


def illegible_feasibility(forms: Sequence[Mapping[str, Any]]) -> dict:
    """For the quiet-but-illegible items: by mechanism, how many items, the content kinds of their replaced lines, the
    append-only precedent (valid items of that mechanism written as three append lines, any writer, by class), and whether the
    items could have been written as three append lines, read as: the mechanism has such a precedent. An item of a mechanism
    with no append-only precedent needs a replaced line by that reading; the packet's definition of the mechanism is beside."""
    mt_tab = mechanism_table(forms)
    by: dict[str, dict] = {}
    for f in forms:
        if f["class"] != mt.ILLEGIBLE:
            continue
        m = by.setdefault(f["mechanism"], {"items": 0, "replace_lines": Counter(), "append_lines": Counter(), "ops": Counter()})
        m["items"] += 1
        m["ops"][f["ops"]] += 1
        for op, k in f["lines"]:
            (m["replace_lines"] if op == "replace" else m["append_lines"])[k] += 1
    could = 0
    for name, m in by.items():
        prec = mt_tab.get(name, {}).get("append-only")
        pr = {"valid": prec["valid"], "certified": prec["certified"], "quiet_but_illegible": prec["quiet_but_illegible"]} if prec else \
            {"valid": 0, "certified": 0, "quiet_but_illegible": 0}
        m["append_only_precedent"] = pr
        m["could_be_three_appends"] = pr["valid"] > 0
        m["replace_lines"], m["append_lines"], m["ops"] = dict(m["replace_lines"]), dict(m["append_lines"]), dict(m["ops"])
        could += m["items"] if m["could_be_three_appends"] else 0
    total = sum(m["items"] for m in by.values())
    return {"items": total, "could_be_three_appends": could, "need_a_replaced_line": total - could,
            "rule": "an item could have been written as three append lines when its mechanism has an append-only precedent among the valid items; "
                    "it needs a replaced line when none does",
            "by_mechanism": by}


def form_risk(forms: Sequence[Mapping[str, Any]]) -> dict:
    """What an append-only constraint risks, as counts: the append-only valid items and how many of them are quiet-but-illegible
    (and which writers wrote any), the replace-bearing valid items and their illegible ones per writer, and each writer's append
    lines of all its lines."""
    ao_valid = ao_ill = 0
    ao_writers: set[str] = set()
    rb: dict[str, dict] = {}
    lines: dict[str, dict] = {}
    for f in forms:
        w = f["writer"]
        ln = lines.setdefault(w, {"append": 0, "lines": 0})
        ln["lines"] += len(f["lines"])
        ln["append"] += sum(1 for op, _k in f["lines"] if op == "append")
        if f["form"] == "append-only":
            ao_valid += 1
            ao_ill += int(f["class"] == mt.ILLEGIBLE)
            ao_writers.add(w)
        else:
            c = rb.setdefault(w, {"valid": 0, "quiet_but_illegible": 0})
            c["valid"] += 1
            c["quiet_but_illegible"] += int(f["class"] == mt.ILLEGIBLE)
    return {"append_only": {"valid": ao_valid, "quiet_but_illegible": ao_ill, "writers": sorted(ao_writers)},
            "replace_bearing": rb, "append_lines": lines}


# ── (1) the cases ────────────────────────────────────────────────────────────────────────────────

def cases(check: Mapping[str, Any], writer: str, sol: str, feasible_share: float, append_only_valid: int, append_only_illegible: int) -> list[dict]:
    """B: the writer's rounds as planned, its observed placeable retention. A1: an append-only constraint, retention like the
    other writer's (both classes), yields as observed. A2: A1 with the illegible yield scaled by `feasible_share`. A3: A1 with the
    illegible rate of the append-only items written so far (Jeffreys on `append_only_illegible` of `append_only_valid`)."""
    own = fc.retention_from_check(check, writer)
    sol_r = fc.retention_from_check(check, sol)
    sol_like = {"c": list(sol_r["c"]), "i": list(sol_r["c"])}
    return [
        {"name": "B", "writing": [writer], "retention": {writer: {"c": own["c"], "i": own["i"]}}, "i_scale": None, "i_post": None},
        {"name": "A1", "writing": [writer], "retention": {writer: sol_like}, "i_scale": None, "i_post": None},
        {"name": "A2", "writing": [writer], "retention": {writer: sol_like}, "i_scale": {writer: feasible_share}, "i_post": None},
        {"name": "A3", "writing": [writer], "retention": {writer: sol_like}, "i_scale": None,
         "i_post": {writer: [0.5 + append_only_illegible, 0.5 + append_only_valid - append_only_illegible]}},
    ]


CASE_TEXT = {
    "B": "B, as planned: Muse Wonder's rounds 4 to 6 at the cap, yields as observed times its observed placeable retention",
    "A1": "A1, append-only constraint: retention like GPT-6.1-sol's, yields as observed",
    "A2": "A2, as A1 with the illegible yield scaled by the share of illegible items whose mechanism has an append-only precedent",
    "A3": "A3, as A1 with the illegible rate of the append-only items written so far (Jeffreys)",
}


def render_md(res: Mapping[str, Any]) -> str:
    f = lambda x: f"{x:.2f}"  # noqa: E731
    st = lambda d: f"{d['mean']:.1f} [{d['p10']:.0f}, {d['p90']:.0f}]"  # noqa: E731
    L = ["# The edit-application check's follow-ups: the retention-adjusted forecast and the line forms of the illegible items (brief 30 Part 3, 8 Nov 2026)", ""]
    L.append(f"Written {res['written']} by the Part 3 session (Sonnet 5.5). $0, no API call, no reader, no B3 file; counts, classes, mechanism labels and content "
             "kinds only (no statement, anchor or document text is read into this file). Module `stage3_elicitation_followups.py` "
             f"`{res['script']['sha256'][:8]}` over `stage3_elicitation_forecast.py` `{res['forecast_module_sha256'][:8]}` (the round-3 forecast reproduces "
             f"byte for byte through it: {res['forecast_regression']}) and the application check `application-check-round2-states-v0.json` "
             f"`{res['check_sha256'][:8]}`. Companion to `application-check-round2-states-v0.md` `65f132a5`, which is unchanged.")
    L.append("")
    fr = res["forecast"]
    risk = res["forms"]["form_risk"]
    L.append("## 1. The retention-adjusted forecast")
    L.append("")
    stock, m0 = fr["stock"], fr["stock_matched"]
    L.append(f"**What is computed.** The after-round-3 forecast (note 12's addendum) on the items that can be placed: the stock is the {sum(s['certified'] for s in stock.values())} "
             f"certified and {sum(s['illegible'] for s in stock.values())} quiet-but-illegible items that pass the application check "
             f"({', '.join(f'`{w}` {s['certified']} and {s['illegible']}' for w, s in stock.items())}); its matched effective n is **{f(m0['n_eff'])}** "
             f"({m0['n_c']} and {m0['n_i']} matched, {m0['strata_used']} strata with both arms). Each case has Muse Wonder write rounds 4 to 6 at the cap of "
             f"{fr['cap_per_writer_round']} (GPT-6.1-sol writes none, note 16), the statistic matched on the observed strata (writer x document x {fr['width']:.0f}-point band; "
             f"each writer's own valid items' strata resampled), its Jeffreys yields from the observed rounds, no drift, the floor rule on and off, a value on the margin of 0.5 reading as below; "
             f"{fr['runs_all_matched']} runs for the all-matched statistic and {fr['runs_matched']} for the matched one, seed {fr['seed']}.")
    L.append("")
    L.append("**C, no round 4:** the stock alone. Matched effective n " + f"{f(fr['no_further_round']['matched_n_eff'])} against the stop of {fr['stop_n_eff']:.0f}: "
             + ("reached." if fr["no_further_round"]["reaches_stop"] else "not reached; no later round is run, so the course ends at that value."))
    L.append("")
    L.append("| case | P(stop by success), floor rule on | floor rule off | P(floor rule ends it) | reading | by round 4 alone | by round 5 | all-matched statistic, floor on |")
    L.append("|---|---|---|---|---|---|---|---|")
    for name, row in fr["cases"].items():
        m, a = row["matched_observed"], row["all_matched"]
        L.append(f"| {name} | {f(m['with_floor_rule']['p_success'])} | {f(m['without_floor_rule']['p_success'])} | {f(m['with_floor_rule']['p_floor'])} | {m['bar_reading']} | "
                 f"{f(m['p_success_by_round']['4'])} | {f(m['p_success_by_round']['5'])} | {f(a['with_floor_rule']['p_success'])} |")
    L.append("")
    for name, text in CASE_TEXT.items():
        if name in fr["cases"]:
            L.append(f"- {text}.")
    L.append("")
    L.append("Retention used (Jeffreys on the kept share): " + "; ".join(
        f"{k}: certified {v['certified'][0]} of {v['certified'][1]}, illegible {v['illegible'][0]} of {v['illegible'][1]}"
        for k, v in res["retention_counts"].items()) + ".")
    L.append("")
    L.append("**Counts after each round, the matched case (mean [p10, p90]): certified, illegible, matched effective n.**")
    L.append("")
    L.append("| case | after round 4 | after round 5 | after round 6 |")
    L.append("|---|---|---|---|")
    for name, row in fr["cases"].items():
        m = row["matched_observed"]
        cells = []
        for r in ("4", "5", "6"):
            cells.append(f"{st(m['certified_after'][r])}; {st(m['illegible_after'][r])}; n_eff {st(m['n_eff_after'][r])}")
        L.append(f"| {name} | " + " | ".join(cells) + " |")
    L.append("")
    L.append("**Weak points.** (a) The illegible side rests on one Muse Wonder round (7 of 70 valid), and its retention on the same round (2 of 7): both posteriors are wide, which the intervals carry. "
             "(b) Retention is a global factor, yet it is concentrated by document (the README, fine-tuning guide and on-call runbook items all drop), and the future items' strata are resampled "
             "from all the writer's valid items, so a case where the surviving documents are the ones that match is not modelled. (c) A1 to A3 assume an append-only constraint leaves the certified yield "
             f"as observed; the only append-only items are GPT-6.1-sol's, and Muse Wonder has written {risk['append_lines']['muse_wonder']['append']} append lines of its "
             f"{risk['append_lines']['muse_wonder']['lines']}, one in each of its default-exception-schedule items, never an append-only item. (d) The packet is pinned: the constraint would live in the per-round "
             "round.md. (e) Yields are held constant though round 4 is Muse Wonder's first feedback round.")
    L.append("")
    fo = res["forms"]
    risk = fo["form_risk"]
    L.append("## 2. The line forms: what an append-only constraint risks")
    L.append("")
    L.append("**Valid items by writer, form and class** (all valid items of rounds 1 to 3; `other` is every class but certified and quiet-but-illegible):")
    L.append("")
    L.append("| writer | form | valid | certified | quiet-but-illegible | other |")
    L.append("|---|---|---|---|---|---|")
    for w, forms in fo["form_table"].items():
        for form, c in sorted(forms.items()):
            L.append(f"| {w} | {form} | {c['valid']} | {c['certified']} | {c['quiet_but_illegible']} | {c['other']} |")
    L.append("")
    L.append("**By mechanism and form, both writers** (the append-only precedent for each mechanism):")
    L.append("")
    L.append("| mechanism | form | valid | certified | quiet-but-illegible | other | writers |")
    L.append("|---|---|---|---|---|---|---|")
    for m, forms in sorted(fo["mechanism_table"].items()):
        for form, c in sorted(forms.items()):
            L.append(f"| {m} | {form} | {c['valid']} | {c['certified']} | {c['quiet_but_illegible']} | {c['other']} | {', '.join(c['writers'])} |")
    L.append("")
    fe = fo["illegible_feasibility"]
    L.append(f"**The {fe['items']} quiet-but-illegible items.** Rule: {fe['rule']}. **{fe['could_be_three_appends']} could have been written as three append lines; "
             f"{fe['need_a_replaced_line']} need a replaced line.**")
    L.append("")
    L.append("| mechanism | illegible items | operations as written | replaced lines by content kind | append-only precedent (valid, certified, illegible) | could be three appends |")
    L.append("|---|---|---|---|---|---|")
    for m, d in sorted(fe["by_mechanism"].items()):
        p = d["append_only_precedent"]
        L.append(f"| {m} | {d['items']} | {', '.join(f'{k}: {v}' for k, v in sorted(d['ops'].items()))} | {', '.join(f'{k} {v}' for k, v in sorted(d['replace_lines'].items()))} | "
                 f"{p['valid']}, {p['certified']}, {p['quiet_but_illegible']} | {'yes' if d['could_be_three_appends'] else 'no'} |")
    L.append("")
    L.append("In the converter's content kinds a replaced line is `procedure` when the line it replaces is a numbered step, so a `procedure` replaced line is a step of a sequence reworded or renumbered in place. "
             "The packet defines order-dependency by statements that \"add, move, renumber or relabel steps\"; an append can add a step at the end of a document or a named region but cannot move or renumber one. "
             "**What option A risks, in the study's own record:** no append-only item has been quiet-but-illegible (" + f"{risk['append_only']['quiet_but_illegible']} of {risk['append_only']['valid']} valid append-only items, "
             f"written by {', '.join(risk['append_only']['writers'])}) "
             "and the mechanism that yielded most of the illegible items has never been written append-only; the replace-bearing items hold "
             + ", ".join(f"{c['quiet_but_illegible']} of {c['valid']} valid ({w})" for w, c in sorted(risk['replace_bearing'].items()))
             + ", so form and writer are not separated by these data.")
    L.append("")
    L.append("## Reproduce")
    L.append("")
    L.append("```")
    L.append("work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_followups.py run")
    L.append("```")
    L.append("")
    return "\n".join(L)


def run(part3: Path, out_dir: Path, runs_all: int = 40000, runs_matched: int = 8000) -> dict:
    P = Path(part3)
    check = _read(P / "application-check-round2-states-v0.json")
    pairs = [(w, n) for w, n in [tuple(x) for x in check["writer_rounds"]]]
    forms = line_forms(P, pairs)
    ft, mtab, feas = form_table(forms), mechanism_table(forms), illegible_feasibility(forms)
    ao = ft.get("gpt61sol", {}).get("append-only", _cell())
    append_only = {"valid": sum(t.get("append-only", _cell())["valid"] for t in ft.values()),
                   "illegible": sum(t.get("append-only", _cell())["quiet_but_illegible"] for t in ft.values())}
    share = feas["could_be_three_appends"] / feas["items"]
    writers = {"gpt61sol": [1, 2, 3], "muse_wonder": [3]}
    observed = fc.load_observed(P, writers, 3)
    stock = fc.stock_from_check(check, list(writers))
    cs = cases(check, "muse_wonder", "gpt61sol", share, append_only["valid"], append_only["illegible"])
    res_f = fc.forecast_retained(observed, stock, cs, runs_all=runs_all, runs_matched=runs_matched)
    # the round-3 forecast must still reproduce byte for byte through the modified module
    want = (P / "forecast-after-r3-v0.json").read_text(encoding="utf-8")
    got = fc.canonical(fc.forecast_after(observed, 40000, 20000))
    regress = "identical" if got == want else "DIFFERENT"
    if regress != "identical":
        raise SystemExit("refusing: the modified forecast module no longer reproduces the round-3 forecast")
    res = {"version": VERSION, "written": datetime.now().astimezone().isoformat(timespec="seconds"),
           "script": {"path": "work/checks/stage3_elicitation_followups.py", "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
           "forecast_module_sha256": hashlib.sha256(Path(fc.__file__).read_bytes()).hexdigest(),
           "forecast_regression": regress, "check_sha256": hashlib.sha256((P / "application-check-round2-states-v0.json").read_bytes()).hexdigest(),
           "forecast": res_f, "retention_counts": {w: fc.retention_from_check(check, w)["counts"] for w in writers},
           "append_only": append_only, "append_only_gpt61sol": ao,
           "forms": {"form_table": ft, "mechanism_table": mtab, "illegible_feasibility": feas, "form_risk": form_risk(forms), "n_valid_items": len(forms)}}
    js = json.dumps(res, indent=1, ensure_ascii=False) + "\n"
    md = render_md(res)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pj, pm = out_dir / "application-check-followups-v0.json", out_dir / "application-check-followups-v0.md"
    pj.write_text(js, encoding="utf-8")
    pm.write_text(md, encoding="utf-8")
    res["_files"] = {"json": hashlib.sha256(pj.read_bytes()).hexdigest(), "md": hashlib.sha256(pm.read_bytes()).hexdigest()}
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 30 Part 3: the application check's two follow-ups")
    ap.add_argument("mode", choices=("run",))
    ap.add_argument("--part3", default=str(PART3))
    ap.add_argument("--out-dir", default=str(PART3))
    ap.add_argument("--runs-all", type=int, default=40000)
    ap.add_argument("--runs-matched", type=int, default=8000)
    ns = ap.parse_args(argv)
    res = run(Path(ns.part3), Path(ns.out_dir), ns.runs_all, ns.runs_matched)
    print(json.dumps({"files": res["_files"], "stock_matched": res["forecast"]["stock_matched"]["n_eff"],
                      "could": res["forms"]["illegible_feasibility"]["could_be_three_appends"],
                      "cases": {k: [v["matched_observed"]["with_floor_rule"]["p_success"], v["matched_observed"]["bar_reading"]]
                                for k, v in res["forecast"]["cases"].items()}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
