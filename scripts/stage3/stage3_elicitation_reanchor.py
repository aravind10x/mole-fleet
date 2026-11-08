#!/usr/bin/env python3
"""Brief 30 Part 3: the placement-adaptive anchoring probe (the coordinator's message of 8 Nov, brief 30 dated note 19).

The 32 items the edit-application check dropped are a kept seed set. The probe asks, per item: does a re-anchoring of its
replace lines to the text as it stands in a placement session's document state exist that keeps the statement (the anchor
changes; the replacement line, the operation and the kind do not) and yields brief 26's rule unchanged: two valid draws on
different days by different authors for the item, and two valid draws by different authors for each of its three lines as a
lone line (and the same on the draws that break no later honest edit, beside)?

Method. For every (day, author) the lone layout can draw (the authors in the document's write-teams, active that day, not
managers: the pool before the module's anchored filter) and every session of that author that day that ends after the day's
last whole rewrite of the document (the module cannot plant before it), every distinct document state a plant in that session
can see (from the later of the session's opening and that rewrite) is read from the null corpus (the same states as the
edit-application check). Each replace statement's
day-0 target line is matched to its counterpart in that state: the line of the best character similarity (difflib ratio) when
it is at or above a threshold and is the only line at that value. The statement's anchor becomes the counterpart's own
beginning (the original anchor where it still resolves to that line; else the shortest prefix of at least ten characters that
starts one line only). Brief 26's own `run_draw` then runs on the rewritten statements: the module's `_plant_once`, the line
checks on every state the session can reach and the joint check. A (day, author) draw counts as valid when some session's
re-anchoring passes. The threshold is the probe's one free choice (0.7 is the primary; 0.5 and 0.9 are beside).

Counts, opaque ids, mechanism labels, content kinds, document names and reason codes only. No item text is read into any output.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_reanchor.py run
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
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

import stage3_b3_inserter_dry_run as dry  # noqa: E402
import stage3_elicitation_application as ap  # noqa: E402
import stage3_t1 as t1  # noqa: E402

VERSION = "elicitation-reanchor/v0"
PART3 = ap.PART3
ANCHOR_MIN = 10
RHOS = (0.7, 0.5, 0.9)
PRIMARY_RHO = 0.7
# the realised costs of writer round 3 (round-3-v0.md section 9): (rater $, reads $, items rated, items read) per stage and writer
RATES = {"gpt61sol": {"cert_rater": 4.84, "cert_reads": 12.85, "dev_rater": 2.43, "dev_reads": 6.40, "rated": 96, "read": 96},
         "muse_wonder": {"cert_rater": 4.32, "cert_reads": 6.72, "dev_rater": 1.93, "dev_reads": 3.81, "rated": 70, "read": 61}}
RATES_DEV_READ = {"gpt61sol": 96, "muse_wonder": 70}      # the development reads cover every valid item


# ── the counterpart and the anchor ───────────────────────────────────────────────────────────────

def counterpart(target: str, state_lines: Sequence[str], rho: float) -> str | None:
    """The line of `state_lines` that is the target as it stands: the unique line of the best similarity ratio when that ratio
    is at least `rho`; None on a tie (so also when the exact line occurs twice) and below the threshold."""
    best, hits = -1.0, []
    for ln in state_lines:
        r = difflib.SequenceMatcher(None, target, ln, autojunk=False).ratio()
        if r > best + 1e-12:
            best, hits = r, [ln]
        elif abs(r - best) <= 1e-12:
            hits.append(ln)
    if best < rho or len(hits) != 1:
        return None
    return hits[0]


def adaptive_anchor(cand: str, original_anchor: str, state: str) -> str | None:
    """The anchor that starts the counterpart's line only: the original anchor where it still resolves to that line alone, else
    the shortest prefix of at least ten characters that starts one line of the state; None when the line occurs twice."""
    lines = state.splitlines()
    if state.count(cand) != 1 or lines.count(cand) != 1:
        return None
    starts = lambda a: [ln for ln in lines if ln.startswith(a)]  # noqa: E731
    if starts(original_anchor) == [cand]:
        return original_anchor
    for n in range(min(ANCHOR_MIN, len(cand)), len(cand) + 1):
        if starts(cand[:n]) == [cand]:
            return cand[:n]
    return None


def rewrite(stmts: Sequence[Mapping[str, Any]], anchors: Sequence[str | None]) -> list[dict]:
    """The statements with the new anchors of their replace lines; nothing else changes, and the input is not touched."""
    out = []
    for st, a in zip(stmts, anchors):
        out.append(dict(st, anchor=a) if st["op"] == "replace" and a is not None else dict(st))
    return out


# ── the draws ────────────────────────────────────────────────────────────────────────────────────

def _anchors_for(stmts: Sequence[Mapping[str, Any]], targets: Mapping[int, str | None], state: str, rho: float) -> tuple[list[str | None] | None, list[bool]]:
    """The per-statement anchors at a state (None for an append) and whether each replace statement has a counterpart there;
    the list is None when some replace statement has none."""
    lines = state.splitlines()
    anchors: list[str | None] = []
    have: list[bool] = []
    for i, st in enumerate(stmts):
        if st["op"] != "replace":
            anchors.append(None)
            have.append(True)
            continue
        t = targets.get(i)
        cand = counterpart(t, lines, rho) if t is not None else None
        a = adaptive_anchor(cand, st["anchor"], state) if cand is not None else None
        anchors.append(a)
        have.append(a is not None)
    return (anchors if all(have) else None), have


def _pool(ins: Any, path: str, day: str) -> list[str]:
    return sorted(a for a in ins.active.get(day, []) if ins.team.get(a) in t1.WRITE_TEAMS[path] and a not in ins.managers)


def adaptive_enumerate(ins: Any, states: Any, key: str, payload: Mapping[str, Any], stmts: Sequence[Mapping[str, Any]], single: bool,
                       found_day0: Sequence[bool], day0_text: str, rho: float) -> dict:
    """brief 26's enumeration over (day, author) with the statements re-anchored per session (see the module's header). The keys
    are those of `stage3_elicitation_application.enumerate_with_clean`, plus the counterpart counts."""
    path = payload["document"]
    d0 = day0_text.splitlines()
    targets = {i: next((ln for ln in d0 if ln.startswith(st["anchor"])), None) for i, st in enumerate(stmts) if st["op"] == "replace"}
    stmt_cp = [st["op"] != "replace" for st in stmts]
    draws: list[dict] = []
    without = 0
    for day in ins.days[:2]:
        for acct in _pool(ins, path, day):
            attempts: list[dict] = []
            floor = ins.whole_write_floor(path, day)
            tried: set[tuple] = set()
            for s in ins.sessions.get((acct, day), []):
                if floor is not None and floor > s.last_ts:        # the module cannot plant before the day's last whole rewrite
                    continue
                t0 = s.first_ts if floor is None or floor <= s.first_ts else floor
                for state in states.reachable(path, s, t0):       # every distinct state a plant in this session can see
                    if not isinstance(state, str):
                        continue
                    anchors, have = _anchors_for(stmts, targets, state, rho)
                    for i, h in enumerate(have):
                        stmt_cp[i] = stmt_cp[i] or h
                    if anchors is None or tuple(anchors) in tried:
                        continue
                    tried.add(tuple(anchors))
                    st2 = rewrite(stmts, anchors)
                    attempts.append(dry.run_draw(ins, states, key, dict(payload, statements=st2), st2, day, acct, single, found_day0))
            if not attempts:
                without += 1
                continue
            valid = [d for d in attempts if d["valid"]]
            reasons: Counter = Counter()
            if not valid:
                for d in attempts:
                    reasons.update(d["reasons"])
            draws.append({"day": day, "author": acct, "valid": bool(valid),
                          "clean": any(d["honest_edits_broken_max"] == 0 for d in valid),
                          "broken": bool(valid) and not any(d["honest_edits_broken_max"] == 0 for d in valid), "reasons": reasons})
    v = [(d["day"], d["author"]) for d in draws if d["valid"]]
    c = [(d["day"], d["author"]) for d in draws if d["clean"]]
    inv: Counter = Counter()
    for d in draws:
        inv.update(d["reasons"])
    return {"n_drawable": len(draws), "n_without_counterpart": without, "n_valid": len(v),
            "valid_by_day": {day: sum(1 for x, _a in v if x == day) for day in ins.days[:2]}, "valid_draws": [list(x) for x in v],
            "pair_ok_distinct_days": dry.pair_ok(v, True), "pair_ok_distinct_authors": dry.pair_ok(v, False), "literal_ok": len(v) >= 2,
            "invalid_reasons": dict(inv), "clean_valid": len(c), "clean_pair_ok_distinct_days": dry.pair_ok(c, True),
            "clean_pair_ok_distinct_authors": dry.pair_ok(c, False), "valid_with_broken_honest_edit": sum(1 for d in draws if d["broken"]),
            "statements_with_counterpart": stmt_cp}


def classify(item: Mapping[str, Any], lone: Sequence[Mapping[str, Any]]) -> dict:
    """re-anchorable (brief 26's rule met) or why not; `clean`: the rule also met on the clean draws."""
    dec = ap.decide_row(item, lone)
    if not dec["drop"]:
        return {"class": "re-anchorable", "clean": not dec["drop_clean"]}
    if not all(item["statements_with_counterpart"]):
        return {"class": "not: a target has no counterpart", "clean": False}
    if item["n_drawable"] == 0:
        return {"class": "not: counterparts never together in one placement session", "clean": False}
    return {"class": "not: too few valid draws", "clean": False}


# ── the corpus's churn, as counts ────────────────────────────────────────────────────────────────

def whole_write_days(ins: Any, paths: Sequence[str]) -> dict:
    """Whole rewrites of each document by day, from the module's own record of them."""
    out: dict[str, dict] = {}
    for p in paths:
        out[str(p).rsplit("/", 1)[-1]] = dict(sorted(Counter(t[:10] for t in ins.whole_writes.get(p, [])).items()))
    return out


def similarity_bin(r: float) -> str:
    return ">= 0.9" if r >= 0.9 else "0.7 to 0.9" if r >= 0.7 else "0.5 to 0.7" if r >= 0.5 else "< 0.5"


def best_similarity(target: str, state_texts: Sequence[Any]) -> float:
    """The best character-similarity ratio of the target to any line of any of the states."""
    best = 0.0
    for x in state_texts:
        if isinstance(x, str):
            for ln in x.splitlines():
                best = max(best, difflib.SequenceMatcher(None, target, ln, autojunk=False).ratio())
    return best


# ── the tables ───────────────────────────────────────────────────────────────────────────────────

def by_document_and_mechanism(rows: Sequence[Mapping[str, Any]]) -> dict:
    out: dict[str, dict] = {}
    for r in rows:
        c = out.setdefault(str(r["document"]).rsplit("/", 1)[-1], {}).setdefault(str(r["mechanism"]), {"items": 0, "re_anchorable": 0, "re_anchorable_clean": 0})
        c["items"] += 1
        ok = r["reanchor"] == "re-anchorable"
        c["re_anchorable"] += int(ok)
        c["re_anchorable_clean"] += int(ok and bool(r["clean"]))
    return out


def recertification_price(counts: Mapping[str, int]) -> dict:
    """The price of re-certifying `counts[writer]` items at round 3's realised per-item rates: the certification stage (the
    certification rater sessions, the two readers at two samples and the scorer) and, beside it, the development stage as well."""
    by: dict[str, dict] = {}
    for w, n in counts.items():
        r = RATES[w]
        per = r["cert_rater"] / r["rated"] + r["cert_reads"] / r["read"]
        per_dev = per + r["dev_rater"] / r["rated"] + r["dev_reads"] / RATES_DEV_READ[w]
        by[w] = {"items": int(n), "per_item": per, "per_item_with_development": per_dev, "usd": per * n, "usd_with_development": per_dev * n}
    return {"by_writer": by, "certification_stage_usd": sum(v["usd"] for v in by.values()),
            "with_development_usd": sum(v["usd_with_development"] for v in by.values()),
            "basis": "round 3's realised spend per item: certification raters over the items rated, certification reads over the items read "
                     "(gate (i) passers for Muse Wonder); the development stage beside"}


def seed_set(rows: Sequence[Mapping[str, Any]], kinds: Mapping[str, Sequence[tuple[str, str]]]) -> list[dict]:
    """The dropped items as the kept seed set: opaque id, writer, round, class, mechanism, document name and the line kinds."""
    out = []
    for r in rows:
        if not r["drop"]:
            continue
        out.append({"uid": r["uid"], "item_id": r["item_id"], "writer": r["writer"], "round": r["round"], "class": r["class"],
                    "mechanism": r["mechanism"], "document": str(r["document"]).rsplit("/", 1)[-1],
                    "line_kinds": ", ".join(f"{op}:{k}" for op, k in kinds[r["uid"]])})
    out.sort(key=lambda x: (x["writer"], x["round"], x["class"], x["item_id"]))
    return out


def append_dated_section(md_path: Path, date: str, text: str) -> None:
    """Append a dated section to a record; a section of the same date is replaced, not repeated."""
    p = Path(md_path)
    body = p.read_text(encoding="utf-8")
    marker = f"\n## Dated section, {date}"
    i = body.find(marker)
    if i >= 0:
        body = body[:i].rstrip("\n") + "\n"
    p.write_text(body.rstrip("\n") + "\n\n" + text.lstrip("\n"), encoding="utf-8")


# ── the run ──────────────────────────────────────────────────────────────────────────────────────

def _task(task: tuple) -> tuple:
    kind, rho, key, payload, stmts, f0, d0 = task
    return kind, rho, key, adaptive_enumerate(dry._G["ins"], dry._G["states"], key, payload, stmts, kind == "line", f0, d0, rho)


def run(part3: Path, out_dir: Path, procs: int = 12, rhos: Sequence[float] = RHOS, limit: int | None = None) -> dict:
    import stage3_views as sv
    from stage3_t1v2_checks import DOCS
    P = Path(part3)
    check = json.loads((P / "application-check-round2-states-v0.json").read_text(encoding="utf-8"))
    dropped = {r["uid"] for r in check["items"] if r["drop"]}
    items = [it for it in ap.load_items(P, ap.discover(P)) if it["uid"] in dropped]
    if limit:
        items = items[:limit]
    kinds = {it["uid"]: [(s["op"], s["kind"]) for s in it["statements"]] for it in items}
    seed = sv.seed_base()
    day0 = {path: text for (_svc, path), text in seed.items() if path in DOCS}
    template = Path(sv.jc_mod.FORK) / "bootstrap" / "org_template.yaml"
    dry._init_globals(dry.CORPUS, template)
    tasks = []
    for rho in rhos:
        for it in items:
            payload = {"id": it["payload_id"], "document": it["document"], "statements": it["statements"], "arm": dry.RATED_ARM["candidate"]}
            tasks.append(("item", rho, it["uid"], payload, it["statements"], [True] * 3, day0[it["document"]]))
            for i, st in enumerate(it["statements"]):
                single = {"id": f"{it['payload_id']}#L{i + 1}", "document": it["document"], "statements": [st], "arm": "singleton"}
                tasks.append(("line", rho, f"{it['uid']}:{i + 1}", single, [st], [True], day0[it["document"]]))
    with mp.get_context("fork").Pool(procs) as pool:
        results = pool.map(_task, tasks, chunksize=1)
    by = {(k, rho, key): r for k, rho, key, r in results}
    per_rho: dict[str, dict] = {}
    for rho in rhos:
        rows = []
        for it in items:
            u = it["uid"]
            item = by[("item", rho, u)]
            lone = [by[("line", rho, f"{u}:{i + 1}")] for i in range(3)]
            cl = classify(item, lone)
            rows.append({"uid": u, "item_id": it["item_id"], "writer": it["writer"], "round": it["round"], "class_": it["class"],
                         "mechanism": it["mechanism"], "document": it["document"], "reanchor": cl["class"], "clean": cl["clean"],
                         "statements_with_counterpart": item["statements_with_counterpart"],
                         "item": {k: item[k] for k in ("n_drawable", "n_without_counterpart", "n_valid", "valid_by_day", "pair_ok_distinct_days", "clean_valid",
                                                       "clean_pair_ok_distinct_days", "valid_with_broken_honest_edit")},
                         "lone_lines": [{k: ld[k] for k in ("n_drawable", "n_valid", "pair_ok_distinct_authors", "clean_valid", "clean_pair_ok_distinct_authors")} for ld in lone]})
        ok = [r for r in rows if r["reanchor"] == "re-anchorable"]
        counts_w: Counter = Counter(r["writer"] for r in ok)
        per_rho[str(rho)] = {
            "rows": rows, "re_anchorable": len(ok), "re_anchorable_clean": sum(1 for r in ok if r["clean"]), "items": len(rows),
            "by_class": dict(Counter(r["reanchor"] for r in rows)),
            "by_writer_class": {f"{w} {c}": n for (w, c), n in sorted(Counter((r["writer"], r["class_"]) for r in ok).items())},
            "by_document_mechanism": by_document_and_mechanism([dict(r, class_=r["class_"]) for r in rows]),
            "recertification": recertification_price(dict(counts_w)) if counts_w else recertification_price({}),
            "replace_statements_with_a_counterpart": {str(n): None for n in ()},
        }
    ins0, states0 = dry._G["ins"], dry._G["states"]
    days0 = list(ins0.days)[:2]
    sim: dict[str, dict] = {}
    for it in items:
        d0 = day0[it["document"]].splitlines()
        sts = [x for d in days0 for x in states0.day_states(it["document"], d)]
        for st in it["statements"]:
            if st["op"] != "replace":
                continue
            t = next((ln for ln in d0 if ln.startswith(st["anchor"])), None)
            b = similarity_bin(best_similarity(t, sts)) if t is not None else "target absent at day 0"
            c = sim.setdefault(it["document"].rsplit("/", 1)[-1], {})
            c[b] = c.get(b, 0) + 1
    churn = {"whole_rewrites_by_day": whole_write_days(ins0, sorted(DOCS)), "draw_days": days0,
             "target_best_similarity_by_document": {k: dict(sorted(v.items())) for k, v in sorted(sim.items())}}
    seed_rows = [r for r in check["items"] if r["uid"] in kinds]
    res = {"version": VERSION, "written": datetime.now().astimezone().isoformat(timespec="seconds"),
           "script": {"path": "work/checks/stage3_elicitation_reanchor.py", "sha256": dry.file_sha256(Path(__file__))},
           "check_sha256": dry.file_sha256(P / "application-check-round2-states-v0.json"), "primary_rho": PRIMARY_RHO, "rhos": list(rhos),
           "module": ap.module_record(), "churn": churn, "seed_set": seed_set(seed_rows, kinds), "by_rho": per_rho}
    return res


def render_md(res: Mapping[str, Any]) -> str:
    L = ["# Placement-adaptive anchoring: a $0 probe on the 32 dropped items (brief 30 Part 3, 8 Nov 2026; dated note 19)", ""]
    L.append(f"Written {res['written']} by the Part 3 session (Sonnet 5.5). $0, no API call, no reader, no re-certification, no launch, no B3 file; counts, opaque ids, "
             f"mechanism labels, content kinds, document names and reason codes only. Module `stage3_elicitation_reanchor.py` `{res['script']['sha256'][:8]}` over the "
             f"application check `application-check-round2-states-v0.json` `{res['check_sha256'][:8]}` and brief 26's draw machinery (`stage3_t1.py` `{res['module']['sha256'][:8]}`).")
    L.append("")
    L.append("## The question and the method")
    L.append("")
    L.append("For each dropped item: does a re-anchoring of its replace lines to the text as it stands in a placement session's document state exist that keeps the statement "
             "(the anchor changes; the replacement line, the operation and the kind do not) and meets brief 26's rule unchanged (two valid draws on different days by different "
             "authors for the item; two valid draws by different authors for each of its three lines as a lone line), with the same rule on the clean draws beside? "
             "For every (day, author) the lone layout can draw (the document's write-team members active that day, not managers) and every session of that author that day, the "
             "document states a plant in the session can see (from the later of its opening and the day's last whole rewrite of the document) are read from the null corpus. Each replace statement's day-0 target line is matched to its counterpart in that state: the "
             "unique line of the best character similarity (difflib ratio), at or above a threshold; the anchor becomes that line's own beginning (the original anchor where it "
             "still resolves to that line alone, else the shortest prefix of at least ten characters that starts one line). Brief 26's `run_draw` then runs on the rewritten "
             "statements (the module's `_plant_once`, every reachable state in the session, the joint check); a (day, author) draw is valid when some session's re-anchoring passes. "
             f"**The threshold is the probe's one free choice: {res['primary_rho']} is the primary, the others are beside.** A match at a low threshold may be a line of a different "
             "meaning; whether an item's composed effect survives the move is not something this probe can tell, which is what re-certification would read.")
    L.append("")
    P = res["by_rho"][str(res["primary_rho"])]
    ch = res["churn"]
    L.append("## The churn, as the corpus has it")
    L.append("")
    L.append("Whole-document rewrites by the corpus's honest agents, by day (the module cannot plant before a day's last whole rewrite of the document, and a rewrite replaces the text the items were written against): "
             + "; ".join(f"{d}: " + (", ".join(f"{day} x{n}" for day, n in sorted(v.items())) or "none") for d, v in sorted(ch["whole_rewrites_by_day"].items())) + f". The draw days are {', '.join(ch['draw_days'])}.")
    L.append("")
    L.append("**Best similarity of each dropped replace statement's day-0 target line to any line of any document state on the draw days at or after the whole-write floor (statements):**")
    L.append("")
    bins = [">= 0.9", "0.7 to 0.9", "0.5 to 0.7", "< 0.5"]
    L.append("| document | " + " | ".join(bins) + " |")
    L.append("|---|" + "---|" * len(bins))
    for d, c in ch["target_best_similarity_by_document"].items():
        L.append(f"| {d} | " + " | ".join(str(c.get(b, 0)) for b in bins) + " |")
    L.append("")
    tot = Counter()
    for c in ch["target_best_similarity_by_document"].values():
        tot.update(c)
    same = len({json.dumps(d["by_class"], sort_keys=True) for d in res["by_rho"].values()}) == 1
    L.append(f"Over all {sum(tot.values())} dropped replace statements: " + ", ".join(f"{b} {tot.get(b, 0)}" for b in bins) + ". "
             + ("No item changes class between the thresholds " + ", ".join(str(r) for r in res["rhos"]) + ": the statements in the middle bands belong to items that have another target with no counterpart."
                if same else "The classes differ between the thresholds (see the table below)."))
    L.append("")
    L.append("## Result")
    L.append("")
    L.append("| threshold | items | re-anchorable (rule) | re-anchorable on the clean draws | not: a target has no counterpart | not: counterparts never together in one session | not: too few valid draws |")
    L.append("|---|---|---|---|---|---|---|")
    for rho in res["rhos"]:
        d = res["by_rho"][str(rho)]
        bc = d["by_class"]
        L.append(f"| {rho} | {d['items']} | {d['re_anchorable']} | {d['re_anchorable_clean']} | {bc.get('not: a target has no counterpart', 0)} | "
                 f"{bc.get('not: counterparts never together in one placement session', 0)} | {bc.get('not: too few valid draws', 0)} |")
    L.append("")
    L.append(f"**At the primary threshold ({res['primary_rho']}), re-anchorable by writer and class:** " + (", ".join(f"{k}: {v}" for k, v in P["by_writer_class"].items()) or "none") + ".")
    L.append("")
    L.append("**By document and mechanism (primary threshold; items / re-anchorable / re-anchorable on the clean draws):**")
    L.append("")
    L.append("| document | mechanism | items | re-anchorable | clean |")
    L.append("|---|---|---|---|---|")
    for doc_, ms in sorted(P["by_document_mechanism"].items()):
        for m, c in sorted(ms.items()):
            L.append(f"| {doc_} | {m} | {c['items']} | {c['re_anchorable']} | {c['re_anchorable_clean']} |")
    L.append("")
    L.append("## What re-certification would cost")
    L.append("")
    L.append("A re-anchored item is placed in the evolved text, so the instruments would read it there: the certification stage again (the certification rater sessions, the "
             "two readers at two samples, the scorer). At round 3's realised per-item rates; the development stage beside.")
    L.append("")
    L.append("| threshold | items to re-certify | certification stage | with the development stage |")
    L.append("|---|---|---|---|")
    for rho in res["rhos"]:
        d = res["by_rho"][str(rho)]
        rc = d["recertification"]
        L.append(f"| {rho} | {d['re_anchorable']} ({', '.join(f'{w} {v['items']}' for w, v in rc['by_writer'].items()) or 'none'}) | "
                 f"{rc['certification_stage_usd']:.2f} USD | {rc['with_development_usd']:.2f} USD |")
    L.append("")
    L.append("Per item: " + "; ".join(f"{w} {r['cert_rater'] / r['rated'] + r['cert_reads'] / r['read']:.3f} USD (certification stage)" for w, r in RATES.items()) +
             ". Basis: round 3's realised spend (`round-3-v0.md` section 9), certification raters over the items rated and certification reads over the items read (for Muse Wonder the gate (i) passers).")
    L.append("")
    L.append("## Reproduce")
    L.append("")
    L.append("```")
    L.append("work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_reanchor.py run")
    L.append("```")
    L.append("")
    return "\n".join(L)


def render_seed_section(seed: Sequence[Mapping[str, Any]], date: str, probe_md_sha: str) -> str:
    L = [f"## Dated section, {date}: the 32 dropped items as the kept seed set (dated note 19)", ""]
    L.append(f"The {len(seed)} items the check dropped under brief 26's rule, listed as the seed set for any re-anchoring or re-certification, with their line kinds (the converter's content "
             f"kind of each line: `procedure`, `recipient`, `path`, `label`, `value`; a `procedure` replace line replaces a numbered step). Opaque ids (first 16 hex; the full ids are in the JSON); no item text. "
             f"The re-anchoring probe over them is `application-check-reanchoring-v0.md` `{probe_md_sha[:8]}`.")
    L.append("")
    L.append("| # | writer | round | id | class | mechanism | document | line kinds |")
    L.append("|---|---|---|---|---|---|---|---|")
    for n, s in enumerate(seed, 1):
        L.append(f"| {n} | {s['writer']} | {s['round']} | `{s['item_id'][:16]}` | {s['class']} | {s['mechanism']} | {s['document']} | {s['line_kinds']} |")
    L.append("")
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap_ = argparse.ArgumentParser(description="brief 30 Part 3: the placement-adaptive anchoring probe")
    ap_.add_argument("mode", choices=("run",))
    ap_.add_argument("--part3", default=str(PART3))
    ap_.add_argument("--out-dir", default=str(PART3))
    ap_.add_argument("--procs", type=int, default=12)
    ap_.add_argument("--limit", type=int, default=None, help="smoke runs only")
    ns = ap_.parse_args(argv)
    P, out = Path(ns.part3), Path(ns.out_dir)
    res = run(P, out, ns.procs, RHOS, ns.limit)
    md = render_md(res)
    guard_items = [it for it in ap.load_items(P, ap.discover(P))]
    import stage3_views as sv
    from stage3_t1v2_checks import DOCS
    day0 = {path: text for (_svc, path), text in sv.seed_base().items() if path in DOCS}
    guard = ap.guard_texts(guard_items, day0)
    js = json.dumps(res, indent=1, ensure_ascii=False) + "\n"
    ap.assert_clean(js, guard)
    ap.assert_clean(md, guard)
    out.mkdir(parents=True, exist_ok=True)
    pj, pm = out / "application-check-reanchoring-v0.json", out / "application-check-reanchoring-v0.md"
    pj.write_text(js, encoding="utf-8")
    pm.write_text(md, encoding="utf-8")
    sha_md = hashlib.sha256(pm.read_bytes()).hexdigest()
    section = render_seed_section(res["seed_set"], "2026-11-08", sha_md)
    ap.assert_clean(section, guard)
    if not ns.limit:
        append_dated_section(P / "application-check-round2-states-v0.md", "2026-11-08", section)
    print(json.dumps({"files": {"json": hashlib.sha256(pj.read_bytes()).hexdigest(), "md": sha_md},
                      "by_rho": {k: {"items": v["items"], "re_anchorable": v["re_anchorable"], "clean": v["re_anchorable_clean"], "by_class": v["by_class"]} for k, v in res["by_rho"].items()}},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
