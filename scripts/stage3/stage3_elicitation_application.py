#!/usr/bin/env python3
"""Brief 30 Part 3: brief 26's edit-application check on the elicitation study's certified and quiet-but-illegible items,
against the document states round 2 uses (protocol section 7; the coordinator's message of 8 Nov, dated note 16).

$0, no API call, no reader. It reuses brief 26's dry run unchanged (`stage3_b3_inserter_dry_run.py`: its `States`,
`static_checks`, `enumerate_draws`, `decide` and the inserter of `stage3_t1.py`, the v3-amended module), but never its
loaders: that script's `load_items` opens B3's item files, and no B3 item is opened here. The items come from this
study's own converted payloads (`part3/round-N/<writer>/converted/`), picked by the round records' class lists.

Per item the check enumerates every (day, author) the lone layout can draw (the null corpus rebuilt in memory, the same
states as brief 26's part ii), runs the module's own `_plant_once` at each, and checks every line and the item as a whole;
and the same for each of the item's three lines as a lone line (the lone-line arm: Phase E's k = 1 reading). The drop
rule is brief 26's: two valid placements for the item (different days, different authors) and two valid draws for each
lone line (different authors); the literal count is reported beside. Beside it, for round 2's plan (brief 33 note 5): the
same rule on the draws that break no later honest edit ("clean" draws). The matching statistic of the round records is
recomputed before and after the drops (note 7's rule, the 10-point band).

Outputs carry opaque ids, booleans, counts, reason codes, days, documents and honest account names only. A guard refuses
to write a file that would contain any item line, anchor, region or declared effect, or a long line of a day-0 document.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_application.py run
"""
from __future__ import annotations

import argparse
import inspect
import json
import multiprocessing as mp
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_inserter_dry_run as dry  # noqa: E402  (brief 26's script, imported; its B3 loaders are never called)
import stage3_elicitation_matching as mt  # noqa: E402
import stage3_t1 as t1  # noqa: E402

VERSION = "elicitation-application-check/v0"
PROJECT = HERE.parent.parent
PART3 = PROJECT / "work" / "stage3" / "elicitation" / "part3"
CLASSES_CHECKED = (mt.CERTIFIED, mt.ILLEGIBLE)


# ── the items ────────────────────────────────────────────────────────────────────────────────────

def discover(part3: Path) -> list[tuple[str, int]]:
    """The (writer, round) pairs that have a round record."""
    out = []
    for rd in sorted(Path(part3).glob("round-*")):
        if not rd.is_dir():
            continue
        try:
            n = int(rd.name.split("-", 1)[1])
        except ValueError:
            continue
        for wd in sorted(rd.iterdir()):
            if (wd / "round-record.json").is_file():
                out.append((wd.name, n))
    return sorted(out)


def _read(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def load_items(part3: Path, pairs: Sequence[tuple[str, int]]) -> list[dict]:
    """Every certified and quiet-but-illegible item of the given writer rounds with its own payload statements,
    document and composition (gate (i)'s mean). The converter's payload is the application form's."""
    items: list[dict] = []
    seen: set[str] = set()
    for writer, rnd in pairs:
        base = Path(part3) / f"round-{rnd}" / writer
        rec = _read(base / "round-record.json")
        key = _read(base / "converted" / "key.json")["triples"]
        pays = {p["id"]: p for p in _read(base / "converted" / "payloads.json")["payloads"]}
        comp = _read(Path(part3) / "raters" / f"{writer}-r{rnd}-cert" / "gate-i.json")["composition"]
        for cls in CLASSES_CHECKED:
            for iid in sorted(rec["ids_by_class"].get(cls, [])):
                # the converter's `_opaque` ignores its salt, so the same writer numbering gives the same id in every
                # round: an item is keyed by writer, round and id
                uid = f"{writer}:r{rnd}:{iid}"
                if uid in seen:
                    raise ValueError(f"item {iid[:8]} appears twice")
                seen.add(uid)
                plantings = key[iid]["plantings"]
                if len(plantings) != 1:
                    raise ValueError(f"item {iid[:8]}: {len(plantings)} plantings, one payload expected")
                p = pays.get(plantings[0]["id"])
                if p is None:
                    raise ValueError(f"item {iid[:8]}: its payload is not in the converted payloads")
                if len(p["statements"]) != 3:
                    raise ValueError(f"item {iid[:8]}: not three statements")
                if p["document"] != key[iid]["document"]:
                    raise ValueError(f"item {iid[:8]}: the payload's document differs from the key's")
                items.append({"item_id": iid, "uid": uid, "writer": writer, "round": rnd, "class": cls, "document": p["document"],
                              "mechanism": key[iid].get("mechanism"), "composition": float(comp[iid]),
                              "payload_id": p["id"], "statements": p["statements"],
                              "composed_effect": p.get("composed_effect")})
    items.sort(key=lambda it: (it["writer"], it["round"], it["class"], it["item_id"]))
    return items


# ── the draws (brief 26's enumeration, with the clean-draw count beside) ───────────────────────────

def enumerate_with_clean(ins: Any, states: Any, key: str, payload: Mapping[str, Any], stmts: Sequence[Mapping[str, Any]],
                         single: bool, found_day0: Sequence[bool]) -> dict:
    """`enumerate_draws` as brief 26 wrote it, plus: of the valid draws, how many break no later honest edit (a draw is
    clean when none of its module runs did) and whether the need is still met on the clean draws alone."""
    seen: list[tuple[str, str, bool, int]] = []
    orig = dry.run_draw

    def recording(*a: Any, **k: Any) -> dict:
        d = orig(*a, **k)
        seen.append((d["day"], d["author"], bool(d["valid"]), int(d["honest_edits_broken_max"])))
        return d

    dry.run_draw = recording
    try:
        out = dry.enumerate_draws(ins, states, key, payload, stmts, single, found_day0)
    finally:
        dry.run_draw = orig
    clean = [(d, a) for d, a, v, b in seen if v and b == 0]
    out["clean_valid"] = len(clean)
    out["clean_pair_ok_distinct_days"] = dry.pair_ok(clean, True)
    out["clean_pair_ok_distinct_authors"] = dry.pair_ok(clean, False)
    out["valid_with_broken_honest_edit"] = sum(1 for _d, _a, v, b in seen if v and b > 0)
    return out


def decide_row(item_draws: Mapping[str, Any], lone: Sequence[Mapping[str, Any]]) -> dict:
    """Brief 26's rule (`decide`) and the same rule on the clean draws."""
    dec = dry.decide({}, item_draws, list(lone))
    clean_short = (not item_draws["clean_pair_ok_distinct_days"]) or any(not ld["clean_pair_ok_distinct_authors"] for ld in lone)
    return {**dec, "drop_clean": bool(clean_short)}


# ── counts ───────────────────────────────────────────────────────────────────────────────────────

def summarise(rows: Sequence[Mapping[str, Any]]) -> dict:
    """items, drops (brief 26's rule; the literal count; the clean rule) and kept, by writer, round and class."""
    out: dict[str, dict] = {}
    for r in rows:
        cell = out.setdefault(r["writer"], {}).setdefault(str(r["round"]), {}).setdefault(
            r["class"], {"items": 0, "dropped": 0, "dropped_literal": 0, "dropped_clean": 0, "kept": 0})
        cell["items"] += 1
        cell["dropped"] += int(bool(r["drop"]))
        cell["dropped_literal"] += int(bool(r["drop_literal"]))
        cell["dropped_clean"] += int(bool(r["drop_clean"]))
        cell["kept"] += int(not r["drop"])
    return out


def _ops_label(lines: Sequence[Mapping[str, Any]]) -> str:
    c = Counter(ln["op"] for ln in lines)
    return " + ".join(f"{c[op]} {op}" for op in ("append", "replace") if c.get(op))


def breakdown(rows: Sequence[Mapping[str, Any]]) -> dict:
    """Items and drops by the pattern of operations (append lines land at the end of a document; replace lines need
    their anchor to resolve in a session's state), by mechanism and by document name; and the lone lines for which no
    author can be drawn, by operation. Counts only."""
    def cell() -> dict:
        return {"items": 0, "dropped": 0, "dropped_clean": 0}

    out: dict[str, dict] = {"by_operations": {}, "by_mechanism": {}, "by_document": {}, "lone_lines_by_operation": {}}
    for r in rows:
        w = r["writer"]
        for name, k in (("by_operations", _ops_label(r["lines"])), ("by_mechanism", str(r["mechanism"])),
                        ("by_document", str(r["document"]).rsplit("/", 1)[-1])):
            c = out[name].setdefault(w, {}).setdefault(k, cell())
            c["items"] += 1
            c["dropped"] += int(bool(r["drop"]))
            c["dropped_clean"] += int(bool(r["drop_clean"]))
        for ln, ld in zip(r["lines"], r["lone_lines"]):
            lc = out["lone_lines_by_operation"].setdefault(w, {}).setdefault(ln["op"], {"lines": 0, "no_author": 0})
            lc["lines"] += 1
            lc["no_author"] += int(ld["n_drawable"] == 0)
    return out


def matched_before_after(rows: Sequence[Mapping[str, Any]]) -> dict:
    """The round records' matching statistic (note 7: writer x document x 10-point band, many-to-one) on all the items
    and on the items that survive the drop rule, and on the items that survive the clean rule."""
    def m(sel: Sequence[Mapping[str, Any]]) -> dict:
        return mt.match([{"writer": r["writer"], "document": r["document"], "composition": r["composition"], "class": r["class"]}
                         for r in sel], mt.BAND_WIDTH)
    return {"before": m(rows), "after": m([r for r in rows if not r["drop"]]), "after_clean": m([r for r in rows if not r["drop_clean"]])}


# ── the guard ────────────────────────────────────────────────────────────────────────────────────

def guard_texts(items: Sequence[Mapping[str, Any]], day0: Mapping[str, str]) -> list[str]:
    """Strings that must never appear in an output: every line, anchor and region of every item (any day), the declared
    effects, and every line of the day-0 documents of at least 25 characters."""
    out: set[str] = set()
    for it in items:
        for st in it["statements"]:
            for k in ("anchor", "replace", "text", "region", "justification"):
                v = st.get(k)
                if isinstance(v, str) and v != "end of document":
                    out.update(f for f in v.split("{date}") if len(f.strip()) >= 12)
        v = it.get("composed_effect")
        if isinstance(v, str) and len(v.strip()) >= 8:
            out.add(v)
    for txt in day0.values():
        out.update(ln for ln in txt.splitlines() if len(ln.strip()) >= 25)
    return sorted(out)


def assert_clean(text: str, guard: Sequence[str]) -> None:
    bad = sum(1 for g in guard if g in text)
    if bad:
        raise SystemExit(f"refusing to write: {bad} guarded strings would appear in the output")


# ── the run ──────────────────────────────────────────────────────────────────────────────────────

def _task(task: tuple) -> tuple:
    kind, key, payload, stmts, found_day0 = task
    ins, states = dry._G["ins"], dry._G["states"]
    return kind, key, enumerate_with_clean(ins, states, key, payload, stmts, kind == "line", found_day0)


def module_record() -> dict:
    p = Path(t1.__file__).resolve()
    return {"path": "work/checks/stage3_t1.py", "sha256": dry.file_sha256(p),
            "inserter_class_sha256": dry.sha256_bytes(inspect.getsource(t1.Inserter).encode("utf-8")),
            "inserter_class_equals_t1v3_manifest": dry.sha256_bytes(inspect.getsource(t1.Inserter).encode("utf-8")) == dry.V3_INSERTER_CLASS_SHA256,
            "dry_run_script_sha256": dry.file_sha256(Path(dry.__file__).resolve()),
            "functions_called": ["stage3_b3_inserter_dry_run.States / static_checks / enumerate_draws / run_draw / decide / pair_ok"]}


def build_rows(items: Sequence[Mapping[str, Any]], corpus: Path, template: Path, procs: int) -> tuple[list[dict], dict, list[str]]:
    import stage3_views as sv
    from stage3_t1v2_checks import DOCS
    seed = sv.seed_base()
    day0 = {path: text for (_svc, path), text in seed.items() if path in DOCS}
    dry._init_globals(corpus, template)
    ins, states = dry._G["ins"], dry._G["states"]
    days = list(ins.days)
    static = {it["uid"]: dry.static_checks(states, days, it, day0) for it in items}
    tasks = []
    for it in items:
        f0 = static[it["uid"]]["found_day0"]
        payload = {"id": it["payload_id"], "document": it["document"], "statements": it["statements"], "arm": dry.RATED_ARM["candidate"]}
        tasks.append(("item", it["uid"], payload, it["statements"], f0))
        for i, st in enumerate(it["statements"]):
            single = {"id": f"{it['payload_id']}#L{i + 1}", "document": it["document"], "statements": [st], "arm": "singleton"}
            tasks.append(("line", f"{it['uid']}:{i + 1}", single, [st], [f0[i]]))
    ctx = mp.get_context("fork")
    with ctx.Pool(procs) as pool:
        results = pool.map(_task, tasks, chunksize=1)
    by = {(k, key): r for k, key, r in results}
    rows = []
    for it in items:
        tid = it["uid"]
        dr = by[("item", tid)]
        lone = [by[("line", f"{tid}:{i + 1}")] for i in range(3)]
        st = static[tid]
        dec = decide_row(dr, lone)
        lines = [{"index": i + 1, "op": sm["op"], "day0_found": st["day0"]["lines"][i]["found"],
                  "lone_n_valid": lone[i]["n_valid"], "lone_pair_ok": lone[i]["pair_ok_distinct_authors"]}
                 for i, sm in enumerate(it["statements"])]
        rows.append({"item_id": it["item_id"], "uid": tid, "writer": it["writer"], "round": it["round"], "class": it["class"], "document": it["document"],
                     "mechanism": it["mechanism"], "composition": it["composition"], "lines": lines,
                     "day0_joint_ok": st["day0"]["joint_ok"], "day0_joint_reason": st["day0"]["joint_reason"],
                     "draws": {k: v for k, v in dr.items() if k != "per_line"},
                     "lone_lines": [{k: v for k, v in ld.items() if k != "per_line"} for ld in lone], **dec})
    meta = {"days": days, "day0_sha256": __import__("stage3_legibility").day0_sha256(day0)}
    return rows, meta, guard_texts(items, day0)


def reason_counts(rows: Sequence[Mapping[str, Any]]) -> dict:
    """Why items were dropped: the first-named reasons of each short placement, counted by what was short."""
    c: Counter = Counter()
    for r in rows:
        for d in r["drop_reasons"]:
            for why in d["why"][:1]:
                c[f"{'item' if d['what'] == 'item' else 'lone line'}: {why}"] += 1
    return dict(c.most_common())


def render_md(res: Mapping[str, Any]) -> str:
    L = []
    L.append("# Edit-application check of the certified and quiet-but-illegible items, against the states round 2 uses (brief 30 Part 3)")
    L.append("")
    L.append(f"Written {res['written']} by the Part 3 session (Sonnet 5.5, Claude Code desktop app). $0, no API call, no reader. "
             "Counts, ids, reason codes and honest account names only; no item line, anchor, region, declared effect or document text is in this file "
             "or its JSON (a guard refuses to write one). No B3 file was opened: brief 26's script is imported for its draw machinery and none of its "
             "loaders is called. STATUS.md was not read.")
    L.append("")
    L.append("## What was run")
    L.append("")
    L.append(f"Module: `stage3_elicitation_application.py` `{res['script']['sha256'][:8]}` over brief 26's `stage3_b3_inserter_dry_run.py` "
             f"`{res['module']['dry_run_script_sha256'][:8]}` and the application module `stage3_t1.py` `{res['module']['sha256'][:8]}` "
             f"(Inserter class `{res['module']['inserter_class_sha256'][:8]}`, equal to the t1v3 manifest: {res['module']['inserter_class_equals_t1v3_manifest']}). "
             f"States: the null corpus `{res['states']['corpus']}` `{res['states']['corpus_sha256'][:8]}` rebuilt in memory (equal to brief 26's and t1v3's: "
             f"{res['states']['corpus_equals_t1v3']}), bank days {', '.join(res['states']['bank_days'])}, the lone layout's draw days {', '.join(res['states']['drawable_days'])}; "
             f"day-0 snapshot `{res['states']['day0_sha256'][:8]}`. Items: {res['totals']['items']} "
             f"(certified and quiet-but-illegible of every writer round that has a record), {res['totals']['item_draws']} item draws and "
             f"{res['totals']['lone_line_draws']} lone-line draws, {res['totals']['module_runs']} module runs.")
    L.append("")
    L.append("**The rule (brief 26's, unchanged).** An item needs two valid placements on different days by different authors; each of its three lines, "
             "as a lone line, needs two valid draws by different authors. An item short of either leaves both arms. The literal count (two valid draws, any "
             "days and authors) is beside. **Beside it, for round 2's plan (brief 33 note 5):** the same rule on the draws that break no later honest edit "
             "(\"clean\" draws: none of the draw's module runs broke one).")
    L.append("")
    L.append("## Result by writer, round and class")
    L.append("")
    L.append("| writer | round | class | items | dropped (rule) | dropped (literal) | dropped (clean rule) | kept |")
    L.append("|---|---|---|---|---|---|---|---|")
    for w, rs in res["summary"].items():
        for rnd, cs in rs.items():
            for cls, c in cs.items():
                L.append(f"| {w} | {rnd} | {cls} | {c['items']} | {c['dropped']} | {c['dropped_literal']} | {c['dropped_clean']} | {c['kept']} |")
    L.append("")
    t = res["totals"]
    L.append(f"**Totals:** {t['items']} items; dropped by the rule {t['dropped']}; by the literal count {t['dropped_literal']}; by the clean rule {t['dropped_clean']}. "
             f"Day-0 joint check passes for {t['day0_joint_ok']} of {t['items']}; every line found at day 0 in {t['day0_all_lines_found']} of {t['items']}.")
    L.append("")
    L.append("## The matching statistic before and after the drops")
    L.append("")
    L.append("| | n_c matched | n_i matched | matched effective n | certified total | illegible total | strata with both arms |")
    L.append("|---|---|---|---|---|---|---|")
    for name in ("before", "after", "after_clean"):
        m = res["matched"][name]
        label = {"before": "all items", "after": "after the rule's drops", "after_clean": "after the clean rule's drops"}[name]
        L.append(f"| {label} | {m['n_c']} | {m['n_i']} | {m['n_eff']:.2f} | {m['n_c_total']} | {m['n_i_total']} | {m['strata_used']} |")
    L.append("")
    L.append("## Why items were dropped (first-named reason of each short placement)")
    L.append("")
    if res["reasons"]:
        for k, v in res["reasons"].items():
            L.append(f"- {k}: {v}")
    else:
        L.append("- no item was dropped")
    L.append("")
    L.append("## Where the drops are (counts)")
    L.append("")
    b = res["breakdown"]
    for title, name in (("By the pattern of operations in the item", "by_operations"), ("By mechanism", "by_mechanism"), ("By document", "by_document")):
        L.append(f"**{title}:**")
        L.append("")
        L.append("| writer | " + name.replace("by_", "") + " | items | dropped (rule) | dropped (clean rule) |")
        L.append("|---|---|---|---|---|")
        for w, cs in b[name].items():
            for k, c in sorted(cs.items()):
                L.append(f"| {w} | {k} | {c['items']} | {c['dropped']} | {c['dropped_clean']} |")
        L.append("")
    L.append("**Lone lines with no author the module can draw, by operation:**")
    L.append("")
    L.append("| writer | operation | lines | no author |")
    L.append("|---|---|---|---|")
    for w, cs in b["lone_lines_by_operation"].items():
        for op, c in sorted(cs.items()):
            L.append(f"| {w} | {op} | {c['lines']} | {c['no_author']} |")
    L.append("")
    L.append("## Draws")
    L.append("")
    d = res["draw_totals"]
    L.append(f"Item draws: {d['item_drawable']} drawable, {d['item_valid']} valid, of which {d['item_clean']} clean ({d['item_broken']} valid but breaking a later honest edit). "
             f"Lone-line draws: {d['lone_drawable']} drawable, {d['lone_valid']} valid, of which {d['lone_clean']} clean ({d['lone_broken']} valid but breaking a later honest edit). "
             f"Largest number of honest edits broken by one draw: {d['broken_max']}.")
    L.append("")
    L.append("## Reproduce")
    L.append("")
    L.append("```")
    L.append("work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_application.py run")
    L.append("```")
    L.append("")
    return "\n".join(L)


def run(part3: Path, out_dir: Path, corpus: Path, template: Path, procs: int, limit: int | None = None, tag: str = "") -> dict:
    pairs = discover(part3)
    items = load_items(part3, pairs)
    if limit:
        items = items[:limit]
    rows, meta, guard = build_rows(items, corpus, template, procs)
    drop = [r for r in rows if r["drop"]]
    days = meta["days"]
    res = {
        "version": VERSION, "written": datetime.now().astimezone().isoformat(timespec="seconds"),
        "writer_rounds": [[w, n] for w, n in pairs],
        "module": module_record(),
        "script": {"path": "work/checks/stage3_elicitation_application.py", "sha256": dry.file_sha256(Path(__file__))},
        "states": {"source": "the null corpus rebuilt in memory through mole/oracles/document.py (brief 26's part ii; the module's whole-write floor applied)",
                   "corpus": str(corpus.relative_to(PROJECT)), "corpus_sha256": dry.file_sha256(corpus),
                   "corpus_equals_t1v3": dry.file_sha256(corpus) == dry.V2C_CORPUS_SHA256,
                   "bank_days": days, "drawable_days": days[:2], "day0_sha256": meta["day0_sha256"]},
        "rule": {"item need": "two valid placements on different days by different authors", "lone-line need": "two valid draws by different authors, for each of the three lines",
                 "literal count beside": "two valid draws, any days and authors", "clean rule beside": "the same needs on draws that break no later honest edit"},
        "totals": {"items": len(rows), "dropped": len(drop), "dropped_literal": sum(1 for r in rows if r["drop_literal"]),
                   "dropped_clean": sum(1 for r in rows if r["drop_clean"]),
                   "day0_joint_ok": sum(1 for r in rows if r["day0_joint_ok"]),
                   "day0_all_lines_found": sum(1 for r in rows if all(ln["day0_found"] for ln in r["lines"])),
                   "item_draws": sum(r["draws"]["n_drawable"] for r in rows),
                   "lone_line_draws": sum(ld["n_drawable"] for r in rows for ld in r["lone_lines"]),
                   "module_runs": sum(r["draws"]["module_runs"] for r in rows) + sum(ld["module_runs"] for r in rows for ld in r["lone_lines"])},
        "draw_totals": {"item_drawable": sum(r["draws"]["n_drawable"] for r in rows), "item_valid": sum(r["draws"]["n_valid"] for r in rows),
                        "item_clean": sum(r["draws"]["clean_valid"] for r in rows),
                        "item_broken": sum(r["draws"]["valid_with_broken_honest_edit"] for r in rows),
                        "lone_drawable": sum(ld["n_drawable"] for r in rows for ld in r["lone_lines"]),
                        "lone_valid": sum(ld["n_valid"] for r in rows for ld in r["lone_lines"]),
                        "lone_clean": sum(ld["clean_valid"] for r in rows for ld in r["lone_lines"]),
                        "lone_broken": sum(ld["valid_with_broken_honest_edit"] for r in rows for ld in r["lone_lines"]),
                        "broken_max": max([r["draws"]["honest_edits_broken_max"] for r in rows]
                                          + [ld["honest_edits_broken_max"] for r in rows for ld in r["lone_lines"]] + [0])},
        "summary": summarise(rows), "matched": matched_before_after(rows), "reasons": reason_counts(rows),
        "breakdown": breakdown(rows),
        "drop_list": {"uids": [r["uid"] for r in drop], "uids_literal": [r["uid"] for r in rows if r["drop_literal"]],
                      "uids_clean": [r["uid"] for r in rows if r["drop_clean"]]},
        "items": rows,
    }
    js = json.dumps(res, indent=1, ensure_ascii=False) + "\n"
    md = render_md(res)
    assert_clean(js, guard)
    assert_clean(md, guard)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pj, pm = out_dir / f"application-check-round2-states-v0{tag}.json", out_dir / f"application-check-round2-states-v0{tag}.md"
    pj.write_text(js, encoding="utf-8")
    pm.write_text(md, encoding="utf-8")
    res["_files"] = {"json": dry.file_sha256(pj), "md": dry.file_sha256(pm)}
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="brief 30 Part 3: the edit-application check of the certified and illegible items")
    ap.add_argument("mode", choices=("run",))
    ap.add_argument("--part3", default=str(PART3))
    ap.add_argument("--out-dir", default=str(PART3))
    ap.add_argument("--corpus", default=str(dry.CORPUS))
    ap.add_argument("--template", default=None)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--limit", type=int, default=None, help="smoke runs only: the first N items")
    ap.add_argument("--tag", default="", help="a suffix for the output names (smoke runs)")
    ns = ap.parse_args(argv)
    import stage3_views as sv
    template = Path(ns.template) if ns.template else Path(sv.jc_mod.FORK) / "bootstrap" / "org_template.yaml"
    res = run(Path(ns.part3), Path(ns.out_dir), Path(ns.corpus), template, ns.procs, ns.limit, ns.tag)
    print(json.dumps({"totals": res["totals"], "matched": {k: {x: v[x] for x in ("n_c", "n_i", "n_eff")} for k, v in res["matched"].items()},
                      "summary": res["summary"], "files": res["_files"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
