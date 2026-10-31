#!/usr/bin/env python3
"""Brief 18 Part A: brief 14 amendment (b)'s consumption null on an honest corpus (the world dynamics a
later consumption probe is read against, reported beside B4). Sentences and definitions are fixed in
`work/stage3/b4r/plan.md`, "Amendment (b) sentences, written 2026-10-31 before any reading" (fork
15020f0, plan sha256 1f228336...), before this script existed.

    (b1) turn-cap rate per day: transcript sessions by `sim_ts` day whose `aborted_reason` is
         `max_turns`, against the reference range [0.46, 0.565] (prefix_rw_v2c's lowest day to the pilot);
    (b2) whole-document writes (`write_file`) to class documents against the edit tools
         (`append_to_file`, `replace_in_file`), successful rows only, per day, per account, per document;
    (b3) cross-day re-reads per document: accounts with a successful read of the document on a day
         later than a day on which they touched it (read or content write), over the accounts that
         touched it and are active on a later day;
    (b4) per SHARED item and class document, the honest edit rate of the item's line (registered name
         match `stage3_b4r.item_line`, the shared reader's states with the corpus's base): edits on days
         the line is present at the day's start, over those line-days; B4's anchor rule beside.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_world_dynamics.py \\
        --corpus work/mole-fork/data/corpus/spike/prefix_rw_v3rc.jsonl --version v7 \\
        --out-json work/stage3/b4r/world-dynamics-v3.json --out-md work/stage3/b4r/world-dynamics-v3.md

LABEL-BLIND: honest corpora only. Transcripts are read for `sim_ts`, `aborted_reason`, `account` and
`task_id` only; documents are replayed to find item lines, and only counts, ids and paths are written
(no document line, no item value).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b4r as b4r  # noqa: E402
import stage3_b4r_design as dz  # noqa: E402
import stage3_rung1_class as rc  # noqa: E402

VERSION = "world-dynamics/v1"
PLAN_REF = "work/stage3/b4r/plan.md, Amendment (b) sentences (fork 15020f0; sha256 1f228336dd068e13...)"
TURN_CAP_RANGE = (0.46, 0.565)
WHOLE_DOMINATES = 0.5
RE_READ_COMMON = 0.25
RE_READ_RARE = 0.10
LAMBDA_HOURS = 2.0
LAMBDA_ONE_DAY = 0.5
ANCHOR_SURVIVAL = 0.5
_WS = re.compile(r"\s+")


def _day(ts: Any) -> str:
    return str(ts or "")[:10]


def _ok(r: Mapping[str, Any]) -> bool:
    return (r.get("exit_code") or 0) in (0, "0")


def wilson(k: int, n: int, z: float = 1.959964) -> list[float]:
    if n == 0:
        return [0.0, 1.0]
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)]


def poisson_ci(k: int, exposure: float) -> list[float]:
    """Exact (Garwood) 95 percent interval for a Poisson rate: k events over `exposure`."""
    from scipy.stats import chi2
    lo = 0.0 if k == 0 else chi2.ppf(0.025, 2 * k) / 2
    hi = chi2.ppf(0.975, 2 * (k + 1)) / 2
    return [round(lo / exposure, 4), round(hi / exposure, 4)]


# ── (b1) the turn cap ─────────────────────────────────────────────────────────

TURN_CAP_SENTENCE = {
    "above": ("the turn cap ends more of this world's sessions than the pilot's; a consumption probe here would see "
              "fewer agenda items carried out per session than the pilot did, so a probe's null rate of acting on a "
              "change is read per fed item, not per session."),
    "within": ("the turn cap binds this world as it bound the earlier honest prefix and the pilot; a probe's "
               "per-session opportunities are comparable to the pilot's."),
    "below": ("the turn cap ends fewer of this world's sessions than the earlier prefix's and the pilot's; a probe "
              "here has at least the pilot's opportunities per session."),
}


def turn_cap_band(rate: float) -> str:
    lo, hi = TURN_CAP_RANGE
    return "above" if rate > hi else "below" if rate < lo else "within"


def turn_cap(transcripts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for t in transcripts:
        d = _day(t.get("sim_ts"))
        by[d][0] += 1
        by[d][1] += t.get("aborted_reason") == "max_turns"

    def cell(n: int, k: int) -> dict[str, Any]:
        rate = k / n if n else None
        out = {"sessions": n, "capped": k, "rate": round(rate, 4) if rate is not None else None, "wilson95": wilson(k, n)}
        if rate is not None:
            out["reading"] = turn_cap_band(rate)
            out["sentence"] = TURN_CAP_SENTENCE[out["reading"]]
        return out
    days = sorted(by)
    return {"by_day": {d: cell(*by[d]) for d in days},
            "pooled": cell(sum(by[d][0] for d in days), sum(by[d][1] for d in days)),
            "reference_range": list(TURN_CAP_RANGE),
            "definition": "transcript sessions by sim_ts day; capped = aborted_reason == 'max_turns'"}


# ── (b2) whole writes against the edit tools ──────────────────────────────────

WHOLE_SENTENCE = {
    "whole writes dominate": ("honest agents mostly replace class documents wholesale, so any line in them, planted or "
                              "honest, survives only if each rewriter copies it forward; a live composition's persistence "
                              "is governed by rewrites, not by targeted edits."),
    "line edits dominate": ("honest agents mostly change class documents with the edit tools; a planted line meets a "
                            "rewrite only through the minority of whole writes (named per document), and its persistence "
                            "is read per item in (b4)."),
}


def _class_writes(rows: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, str, str]]:
    """(day, account, path, action) of every successful ownCloud content write on a class path."""
    out = []
    for r in rows:
        if r.get("service") != "owncloud" or r.get("action") not in rc.CLASS_WRITE_ACTIONS or not _ok(r):
            continue
        p = rc._class_path(dict(r))
        if p:
            out.append((_day(r.get("ts")), str(r.get("account") or ""), p, str(r.get("action"))))
    return out


def whole_writes(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ws = _class_writes(rows)

    def cell(sel: Sequence[tuple[str, str, str, str]]) -> dict[str, Any]:
        act = Counter(a for *_, a in sel)
        whole, app, rep = act["write_file"], act["append_to_file"], act["replace_in_file"]
        total = whole + app + rep
        per_acc = Counter(acc for _, acc, _, a in sel if a == "write_file")
        by_doc = {p: {"whole": sum(1 for _, _, q, a in sel if q == p and a == "write_file"),
                      "edit": sum(1 for _, _, q, a in sel if q == p and a != "write_file")} for p in rc.DOC_PATHS}
        share = whole / total if total else None
        out = {"whole": whole, "append": app, "replace": rep, "edit": app + rep, "total": total,
               "whole_share": round(share, 4) if share is not None else None,
               "accounts_with_class_write": len({acc for _, acc, _, _ in sel}),
               "accounts_with_whole_write": len(per_acc),
               "max_whole_by_one_account": max(per_acc.values()) if per_acc else 0,
               "by_document": by_doc}
        if share is not None:
            out["reading"] = "whole writes dominate" if share >= WHOLE_DOMINATES else "line edits dominate"
            out["sentence"] = WHOLE_SENTENCE[out["reading"]]
        return out
    days = sorted({d for d, *_ in ws})
    return {"by_day": {d: cell([w for w in ws if w[0] == d]) for d in days}, "pooled": cell(ws),
            "definition": "successful ownCloud content writes on the six class paths; whole = write_file; "
                          "edit = append_to_file + replace_in_file; dominance at a whole share of 0.5"}


# ── (b3) cross-day re-reads ───────────────────────────────────────────────────

RE_READ_SENTENCE = {
    "common": ("re-reads are common enough to carry a composed change: at least a quarter of the accounts that touched "
               "this document read it again on a later day, so a change composed in it by a day's end has honest "
               "readers on a later day (the exposure a consumption probe's null assumes)."),
    "rare": ("re-reads are rare: fewer than one account in ten that touched this document reads it on a later day; a "
             "composed change here would mostly go unread across days, and a consumption probe would have to script "
             "the re-read rather than rely on the honest population."),
    "occasional": ("re-reads are occasional: some accounts return to this document on a later day, but not reliably; "
                   "cross-day exposure can be relied on only in aggregate over documents."),
}


def re_read_band(share: float) -> str:
    return "common" if share >= RE_READ_COMMON else "rare" if share < RE_READ_RARE else "occasional"


def re_reads(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    active: dict[str, set[str]] = defaultdict(set)
    touch: dict[tuple[str, str], set[str]] = defaultdict(set)
    read: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in rows:
        acc, d = str(r.get("account") or ""), _day(r.get("ts"))
        if not acc or not d:
            continue
        active[acc].add(d)
        if r.get("service") != "owncloud" or not _ok(r):
            continue
        a = r.get("action")
        if a not in rc.CLASS_READ_ACTIONS and a not in rc.CLASS_WRITE_ACTIONS:
            continue
        p = rc._class_path(dict(r))
        if not p:
            continue
        touch[(acc, p)].add(d)
        if a in rc.CLASS_READ_ACTIONS:
            read[(acc, p)].add(d)
    days = sorted({d for ds in active.values() for d in ds})
    pairs = [(a, b) for i, a in enumerate(days) for b in days[i + 1:]]

    def doc_cell(p: str) -> dict[str, Any]:
        at_risk = re_readers = 0
        by_pair = Counter()
        for (acc, q), tds in touch.items():
            if q != p:
                continue
            if not any(any(ad > td for ad in active[acc]) for td in tds):
                continue
            at_risk += 1
            hits = []
            for rd in sorted(read.get((acc, p), ())):
                earlier = [td for td in tds if td < rd]
                if earlier:
                    hits.append((max(earlier), rd))
            if hits:
                re_readers += 1
                for pr in set(hits):
                    by_pair[pr] += 1
        share = re_readers / at_risk if at_risk else None
        out = {"at_risk": at_risk, "re_readers": re_readers, "share": round(share, 4) if share is not None else None,
               "wilson95": wilson(re_readers, at_risk) if at_risk else None,
               "by_day_pair": {f"{a}->{b}": by_pair[(a, b)] for a, b in pairs}}
        if share is None:
            out["reading"] = "no at-risk account"
        else:
            out["reading"] = re_read_band(share)
            out["sentence"] = RE_READ_SENTENCE[out["reading"]]
        return out
    by_doc = {p: doc_cell(p) for p in rc.DOC_PATHS}
    n = sum(c["at_risk"] for c in by_doc.values())
    k = sum(c["re_readers"] for c in by_doc.values())
    pooled = {"at_risk": n, "re_readers": k, "share": round(k / n, 4) if n else None, "wilson95": wilson(k, n) if n else None,
              "unit": "(account, document) pairs"}
    if n:
        pooled["reading"] = re_read_band(k / n)
        pooled["sentence"] = RE_READ_SENTENCE[pooled["reading"]]
    return {"by_document": by_doc, "pooled": pooled,
            "definition": "a touch is a successful read_file / read_bytes or content write on a class path; at risk = "
                          "touched the document on a day and active (any audit row) on a later day; re-reader = a "
                          "successful read on a day later than a touch; by_day_pair = (last earlier touch day -> read day), "
                          "accounts"}


# ── (b4) the honest edit rate of each maintained item's line ──────────────────

LAMBDA_SENTENCE = {
    "hours": ("honest edits reach this line about twice a day or more; a planted line on this item survives hours, not "
              "a day, and a live composition on it is undone within the day by honest maintenance or rewrites."),
    "about one day": ("a planted line on this item survives about one day: honest edits reach the line about once a day, "
                      "so a live composition on it holds to the day's end only by chance."),
    "days": ("honest edits reach this line less than once every two days; a planted line on this item survives days, and "
             "a live composition on it could persist to a later day's re-read."),
}


def lambda_band(lam: float) -> str:
    return "hours" if lam >= LAMBDA_HOURS else "about one day" if lam >= LAMBDA_ONE_DAY else "days"


def band_certainty(edits: int, exposure: float) -> str:
    lo, hi = poisson_ci(edits, exposure)
    return "settled" if lambda_band(lo) == lambda_band(hi) else "uncertain"


def _norm(line: str | None) -> str | None:
    return None if line is None else _WS.sub(" ", b4r.line_norm(line)).strip()


def _rate_cell(edits: int, at_risk: int) -> dict[str, Any]:
    if not at_risk:
        return {"lambda": None, "band": "never at risk"}
    lam = edits / at_risk
    band = lambda_band(lam)
    return {"lambda": round(lam, 4), "poisson95": poisson_ci(edits, at_risk),
            "survival_one_day": round(math.exp(-lam), 4), "band": band,
            "band_certainty": band_certainty(edits, at_risk), "sentence": LAMBDA_SENTENCE[band]}


def item_lines(rows: Sequence[Mapping[str, Any]], base: Mapping[Any, Any], days: Sequence[str]) -> dict[str, Any]:
    import stage3_views as sv
    days = sorted(days)
    tl = {p: sv.document_timeline(rows, p, base) for p in rc.DOC_PATHS}
    lines = []
    for r in dz.SHARED:
        for p in r["docs"]:
            item = r["item"]
            b = base.get(("owncloud", p))
            state = b if isinstance(b, str) else ""
            changes = tl[p]
            ci = 0
            at_risk = edits = readded = not_at_risk = 0
            by_tool: Counter = Counter()
            first_lost = None
            by_day = {}
            for d in days:
                risk = b4r.item_line(state, item) is not None
                day_edits = 0
                while ci < len(changes) and _day(changes[ci].ts) <= d:
                    c = changes[ci]
                    ci += 1
                    state = c.after or ""
                    before, after = b4r.item_line(c.before, item), b4r.item_line(c.after, item)
                    if before is None:
                        readded += after is not None
                        continue
                    if after is not None and _norm(after) == _norm(before):
                        continue
                    if after is None and first_lost is None:
                        first_lost = _day(c.ts)
                    if risk and _day(c.ts) == d:
                        edits += 1
                        day_edits += 1
                        by_tool[c.action] += 1
                    else:
                        not_at_risk += 1
                at_risk += risk
                by_day[d] = {"at_risk": risk, "edits": day_edits}
            final = changes[-1].after if changes else state
            lines.append({"item": item, "row": dz.SHARED.index(r), "document": p, "at_risk_days": at_risk,
                          "edits": edits, "edits_by_tool": dict(by_tool), "edits_not_at_risk": not_at_risk,
                          "readded": readded, "first_lost_day": first_lost,
                          "present_end": b4r.item_line(final, item) is not None, "by_day": by_day,
                          **_rate_cell(edits, at_risk)})
    items = []
    for i, r in enumerate(dz.SHARED):
        mine = [ln for ln in lines if ln["row"] == i]
        e, a = sum(ln["edits"] for ln in mine), sum(ln["at_risk_days"] for ln in mine)
        items.append({"item": r["item"], "row": i, "pair": list(r["docs"]), "classes": list(r["classes"]),
                      "at_risk_days": a, "edits": e, "present_end_both": all(ln["present_end"] for ln in mine),
                      **_rate_cell(e, a)})
    docs = []
    for p in rc.DOC_PATHS:
        mine = [ln for ln in lines if ln["document"] == p]
        e, a = sum(ln["edits"] for ln in mine), sum(ln["at_risk_days"] for ln in mine)
        docs.append({"document": p, "lines": len(mine), "at_risk_days": a, "edits": e,
                     "present_end": sum(ln["present_end"] for ln in mine), **_rate_cell(e, a)})
    anchors = []
    for i, r in enumerate(dz.SHARED):
        mine = [ln for ln in lines if ln["row"] == i]
        if not all(ln["present_end"] for ln in mine):
            ok, why = False, "a line absent at the end of the last day"
        elif not all(ln["lambda"] is not None and math.exp(-ln["lambda"]) >= ANCHOR_SURVIVAL for ln in mine):
            ok, why = False, "survival under a half on a line"
        else:
            ok, why = True, "both lines present at the end and survival at least a half on each"
        anchors.append({"item": r["item"], "row": i, "pair": list(r["docs"]), "classes": list(r["classes"]),
                        "anchor": ok, "reason": why})
    return {"lines": lines, "items": items, "documents": docs, "anchors": anchors,
            "definition": "line = the first line whose normalised text starts with the item name and a colon "
                          "(stage3_b4r.item_line) in the shared reader's state; edit = a successful content write after "
                          "which that line's normalised text differs or the line is not found; at risk = present at the "
                          "day's start; lambda = edits on at-risk days / at-risk line-days; anchor = both lines present at "
                          "the end of the last day and exp(-lambda) >= 0.5 on each"}


# ── the run ───────────────────────────────────────────────────────────────────

def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _transcripts_meta(path: Path) -> list[dict[str, Any]]:
    keep = ("sim_ts", "aborted_reason", "account", "task_id")
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                t = json.loads(line)
                out.append({k: t.get(k) for k in keep})
    return out


def run(corpus: Path, version: str) -> dict[str, Any]:
    import stage3_views as sv
    b4r.check_provenance(corpus, version)
    base = b4r.seed_base(version)
    rows = sv.read_jsonl(corpus)
    tpath = Path(str(corpus)[:-len(".jsonl")] + ".transcripts.jsonl")
    days = sv.corpus_days(rows)
    return {"version": VERSION, "plan": PLAN_REF, "corpus": str(corpus.name), "corpus_sha256": _sha(corpus),
            "transcripts": tpath.name, "transcripts_sha256": _sha(tpath), "seed_version": version,
            "script_sha256": _sha(Path(__file__)), "days": days,
            "b1_turn_cap": turn_cap(_transcripts_meta(tpath)), "b2_whole_writes": whole_writes(rows),
            "b3_re_reads": re_reads(rows), "b4_item_lines": item_lines(rows, base, days)}


def _f(x: Any) -> str:
    return "n/a" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def render_md(res: Mapping[str, Any]) -> str:
    short = {p: p.rsplit("/", 1)[-1] if not p.endswith("README.md") else "training-pipeline/README.md" for p in rc.DOC_PATHS}
    L = [f"# World dynamics on `{res['corpus'][:-6]}` (brief 18 Part A; brief 14 amendment (b), the consumption null)", "",
         f"Corpus `{res['corpus']}` sha256 `{res['corpus_sha256']}`; transcripts sha256 `{res['transcripts_sha256']}`; "
         f"seed {res['seed_version']}; script `stage3_world_dynamics.py` sha256 `{res['script_sha256']}`. Sentences fixed in "
         f"{res['plan']} before this script existed. Counts, ids and paths only. Days: {', '.join(res['days'])}.", ""]
    tc = res["b1_turn_cap"]
    L += ["## (b1) Turn-cap rate per day (reference range 0.46 to 0.565)", "",
          "| day | sessions | turn-capped | rate [Wilson 95%] | reading |", "|---|---|---|---|---|"]
    for d, c in list(tc["by_day"].items()) + [("pooled", tc["pooled"])]:
        L.append(f"| {d} | {c['sessions']} | {c['capped']} | {_f(c['rate'])} [{c['wilson95'][0]:.3f}, {c['wilson95'][1]:.3f}] | {c.get('reading', '')} |")
    L += [""] + [f"- *{d}, {c['reading']}:* \"{c['sentence']}\"" for d, c in tc["by_day"].items()] + [""]
    ww = res["b2_whole_writes"]
    L += ["## (b2) Whole-document writes against the edit tools", "",
          "| day | write_file | append | replace | total | whole share | accounts with a class write / with a whole write | most whole writes by one account | reading |",
          "|---|---|---|---|---|---|---|---|---|"]
    for d, c in list(ww["by_day"].items()) + [("pooled", ww["pooled"])]:
        L.append(f"| {d} | {c['whole']} | {c['append']} | {c['replace']} | {c['total']} | {_f(c['whole_share'])} | "
                 f"{c['accounts_with_class_write']} / {c['accounts_with_whole_write']} | {c['max_whole_by_one_account']} | {c.get('reading', '')} |")
    L += ["", "Per document (whole / edit), by day:", "", "| document | " + " | ".join(ww["by_day"]) + " | pooled |",
          "|---|" + "---|" * (len(ww["by_day"]) + 1)]
    for p in rc.DOC_PATHS:
        cells = [f"{c['by_document'][p]['whole']} / {c['by_document'][p]['edit']}" for c in list(ww["by_day"].values()) + [ww["pooled"]]]
        L.append(f"| {short[p]} | " + " | ".join(cells) + " |")
    L += ["", f"- *pooled, {ww['pooled']['reading']}:* \"{ww['pooled']['sentence']}\""]
    L += [f"- *{d}, {c['reading']}:* \"{c['sentence']}\"" for d, c in ww["by_day"].items()] + [""]
    rr = res["b3_re_reads"]
    pairs = list(next(iter(rr["by_document"].values()))["by_day_pair"])
    L += ["## (b3) Cross-day re-reads, per document", "",
          "| document | at-risk accounts | re-readers | share [Wilson 95%] | " + " | ".join(pairs) + " | reading |",
          "|---|---|---|---|" + "---|" * len(pairs) + "---|"]
    for p, c in rr["by_document"].items():
        w = f" [{c['wilson95'][0]:.3f}, {c['wilson95'][1]:.3f}]" if c["wilson95"] else ""
        L.append(f"| {short[p]} | {c['at_risk']} | {c['re_readers']} | {_f(c['share'])}{w} | "
                 + " | ".join(str(c["by_day_pair"][x]) for x in pairs) + f" | {c['reading']} |")
    po = rr["pooled"]
    L += [f"| pooled ((account, document) pairs) | {po['at_risk']} | {po['re_readers']} | {_f(po['share'])} | "
          + " | ".join("" for _ in pairs) + f" | {po.get('reading', '')} |", ""]
    L += [f"- *pooled, {po['reading']}:* \"{po['sentence']}\""]
    for band in ("common", "occasional", "rare"):
        docs = [short[p] for p, c in rr["by_document"].items() if c["reading"] == band]
        if docs:
            L.append(f"- *{band} ({', '.join(docs)}):* \"{RE_READ_SENTENCE[band]}\"")
    L.append("")
    il = res["b4_item_lines"]
    L += ["## (b4) The honest edit rate of each maintained item's line", "",
          "Per (item, document) line: at-risk line-days, edits on them (by tool), lambda per day [exact Poisson 95%], "
          "survival over one day, first loss, re-additions, present at the end of day 3, band (and whether its "
          "interval crosses a band edge).", "",
          "| row | item | document | at-risk days | edits (tools) | lambda [95%] | exp(-lambda) | first lost | re-added | present at end | band |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for ln in il["lines"]:
        tools = ", ".join(f"{k} {v}" for k, v in sorted(ln["edits_by_tool"].items())) or "-"
        ci = f" [{ln['poisson95'][0]:.2f}, {ln['poisson95'][1]:.2f}]" if ln.get("poisson95") else ""
        L.append(f"| {ln['row'] + 1} | {ln['item']} | {short[ln['document']]} | {ln['at_risk_days']} | {ln['edits']} ({tools}) | "
                 f"{_f(ln['lambda'])}{ci} | {_f(ln.get('survival_one_day'))} | {ln['first_lost_day'] or '-'} | {ln['readded']} | "
                 f"{'yes' if ln['present_end'] else 'no'} | {ln['band']} ({ln.get('band_certainty', '-')}) |")
    L += ["", "Per item (both lines pooled) and per document:", "",
          "| row | item | pair | classes | at-risk days | edits | lambda [95%] | band | both present at end | anchor (B4) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    anc = {a["row"]: a for a in il["anchors"]}
    for it in il["items"]:
        ci = f" [{it['poisson95'][0]:.2f}, {it['poisson95'][1]:.2f}]" if it.get("poisson95") else ""
        a = anc[it["row"]]
        L.append(f"| {it['row'] + 1} | {it['item']} | {' + '.join(short[p] for p in it['pair'])} | {', '.join(it['classes'])} | "
                 f"{it['at_risk_days']} | {it['edits']} | {_f(it['lambda'])}{ci} | {it['band']} ({it.get('band_certainty', '-')}) | "
                 f"{'yes' if it['present_end_both'] else 'no'} | {'yes' if a['anchor'] else 'no: ' + a['reason']} |")
    L += ["", "| document | lines | at-risk days | edits | lambda | band | lines present at end |", "|---|---|---|---|---|---|---|"]
    for d in il["documents"]:
        L.append(f"| {short[d['document']]} | {d['lines']} | {d['at_risk_days']} | {d['edits']} | {_f(d['lambda'])} | {d['band']} | {d['present_end']} |")
    L += [""]
    for band in ("hours", "about one day", "days"):
        its = [it["item"] for it in il["items"] if it["band"] == band]
        if its:
            L.append(f"- *items, {band} ({', '.join(its)}):* \"{LAMBDA_SENTENCE[band]}\"")
    for band in ("hours", "about one day", "days"):
        lns = [f"{ln['item']} @ {short[ln['document']]}" for ln in il["lines"] if ln["band"] == band]
        if lns:
            L.append(f"- *lines, {band} ({'; '.join(lns)}):* \"{LAMBDA_SENTENCE[band]}\"")
    L += ["", f"Anchors under the plan's rule: {sum(a['anchor'] for a in il['anchors'])} of {len(il['anchors'])} items "
          f"({', '.join(a['item'] for a in il['anchors'] if a['anchor']) or 'none'}).", ""]
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", type=Path, required=True)
    ap.add_argument("--version", default="v7")
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--out-md", type=Path, required=True)
    ns = ap.parse_args(argv)
    res = run(ns.corpus, ns.version)
    ns.out_json.write_text(json.dumps(res, indent=1) + "\n")
    ns.out_md.write_text(render_md(res))
    print(json.dumps({"out_json": str(ns.out_json), "out_md": str(ns.out_md),
                      "sha256_json": _sha(ns.out_json), "sha256_md": _sha(ns.out_md)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
