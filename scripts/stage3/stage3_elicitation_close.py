#!/usr/bin/env python3
"""Brief 30 Part 3: the closing record (`part3/part3-close-v0.md`). Counts, aggregates and hashes only; every figure is read from the
round records, the application check, the re-anchoring probe, the limits records and the anchor record; none is typed here except
the rules file's own sentence rows and the list of what is not done.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_close.py run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

PROJECT = HERE.parent.parent
PART3 = PROJECT / "work" / "stage3" / "elicitation" / "part3"
CLASS_KEYS = ("certified", "quiet_but_illegible", "mixed", "part_derivable", "loud", "not_evaluable")
FUNNEL_KEYS = ("written", "valid", "quiet", "gate_ii_pass", "certified", "quiet_but_illegible", "mixed", "part_derivable", "loud", "not_evaluable")
FLOOR_C, FLOOR_I, TARGET_C, TARGET_I = 12, 12, 26, 12


def _read(p: Path) -> Any:
    return json.loads(Path(p).read_text(encoding="utf-8"))


def _sha8(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:8]


# ── the rules file's outcome sentence (section 3, one-document arm) ───────────────────────────────

def select_outcome(n_c: int, n_i: int, best: int | None = None) -> dict:
    """The one-document row of `rules-and-sentences-v0.md` section 3 that the counts select, with its sentence and next action."""
    if n_c >= TARGET_C and n_i >= TARGET_I:
        b = "" if best is None else f"; the best writer produced {best}"
        return {"row": "Target reached", "sentence": f"Capable writers with feedback produced {n_c} certified and {n_i} quiet-but-illegible one-document items by writer round 3{b}.",
                "next": "B3's round 2 runs on the committed design (level contrast at m_L 18.22, slope beside) once the edit-application check has run and its plan commits."}
    if n_c >= FLOOR_C and n_i >= FLOOR_I:
        return {"row": "Floor reached, target short", "sentence": f"{n_c} certified and {n_i} quiet-but-illegible items, above the floor of 12 and 12 and short of 26 and 12.",
                "next": "B3's round 2 runs at the achieved n, matched on writer, document and composition band; its operating characteristics at that n are disclosed (A6.18 (n)); "
                        "the slope beside is descriptive below 26 certified; B3's combination sentence is scoped to that n."}
    b = "" if best is None else f" (the best writer produced {best})"
    return {"row": "Below the floor on either arm", "sentence": f"Writers produced {n_c} certified and {n_i} quiet-but-illegible items, short of the floor of 12 and 12.{b}".replace(".  ", ". ").replace(".(", ". ("),
            "next": "A6.15 (g): B3's round 2 runs at the achieved n, with Part 3's operating characteristics at that n; where the illegible arm is short, the level contrast is descriptive "
                    "and the slope carries the combination sentence, scoped to \"with these writers, at n = [n]\". The attacker-side round is designed from the taxonomy regardless."}


# ── the tables ───────────────────────────────────────────────────────────────────────────────────

def cumulative(rows: Sequence[Mapping[str, Any]]) -> dict:
    out: dict[str, dict] = {}
    for r in rows:
        for key in (r["writer"], "all"):
            c = out.setdefault(key, {k: 0 for k in FUNNEL_KEYS})
            for k in FUNNEL_KEYS:
                c[k] += int(r[k])
    return out


def stock_tables(check_rows: Sequence[Mapping[str, Any]]) -> dict:
    """The placeable stock (rows the application check kept) and the seed set (the dropped), by writer and class and by document and
    mechanism."""
    def dm() -> dict:
        return defaultdict(lambda: defaultdict(lambda: {"certified": 0, "quiet_but_illegible": 0}))

    p_wc: dict[str, int] = defaultdict(int)
    s_wc: dict[str, int] = defaultdict(int)
    p_dm, s_dm = dm(), dm()
    for r in check_rows:
        wc = f"{r['writer']} {r['class']}"
        doc = str(r["document"]).rsplit("/", 1)[-1]
        if r["drop"]:
            s_wc[wc] += 1
            s_dm[doc][r["mechanism"]][r["class"]] += 1
        else:
            p_wc[wc] += 1
            p_dm[doc][r["mechanism"]][r["class"]] += 1
    conv = lambda d: {k: {m: dict(c) for m, c in v.items()} for k, v in sorted(d.items())}  # noqa: E731
    return {"placeable_by_writer_class": dict(sorted(p_wc.items())), "seed_by_writer_class": dict(sorted(s_wc.items())),
            "placeable_by_document_mechanism": conv(p_dm), "seed_by_document_mechanism": conv(s_dm)}


def ledger(rounds: Mapping[int, Mapping[str, Any]]) -> dict:
    """Per OpenRouter key number, the fall of the key's limit and of the account balance across the rounds that used it."""
    k1 = [rounds[n]["key1"] for n in sorted(rounds) if rounds[n].get("key1")]
    k2 = [rounds[n]["key2"] for n in sorted(rounds) if rounds[n].get("key2") and "limit_remaining_before" in rounds[n]["key2"]]
    out: dict[str, dict] = {}
    if k1:
        first, last = k1[0], k1[-1]
        a0 = first.get("before_dev") or first.get("start")
        a1 = last.get("after_cert") or last.get("end")
        out["key1"] = {"limit_before": a0["limit_remaining"], "limit_after": a1["limit_remaining"], "limit_fall": a0["limit_remaining"] - a1["limit_remaining"],
                       "account_before": a0["account"], "account_after": a1["account"], "account_fall": a0["account"] - a1["account"]}
    if k2:
        f, l = k2[0], k2[-1]
        out["key2"] = {"limit_before": f["limit_remaining_before"], "limit_after": l["limit_remaining_after"], "limit_fall": f["limit_remaining_before"] - l["limit_remaining_after"],
                       "account_before": f["account_remaining_before"], "account_after": l["account_remaining_after"],
                       "account_fall": f["account_remaining_before"] - l["account_remaining_after"]}
    return out


def mechanism_totals(part3: Path, pairs: Sequence[tuple[str, int]]) -> dict:
    out: dict[str, dict] = {}
    for w, n in pairs:
        bm = _read(Path(part3) / f"round-{n}" / w / "round-record.json")["by_mechanism"]
        for m, c in bm.items():
            t = out.setdefault(m, {k: 0 for k in ("valid", "certified", "quiet_but_illegible", "mixed", "part_derivable", "loud", "not_evaluable")})
            for k in t:
                t[k] += int(c.get(k, 0))
    return dict(sorted(out.items()))


# ── the record ───────────────────────────────────────────────────────────────────────────────────

def render_md(d: Mapping[str, Any]) -> str:
    L = ["# Brief 30 Part 3, closing record: the writer course of the one-document arm (the Part 3 session, Sonnet 5.5, 2026-11-08)", ""]
    L.append("Counts, aggregates and hashes only. No item text, statement or rubric text appears here or in any file named here outside the barred directories and files "
             "(`part3/writers/`, the caches, the human anchor's sheet and draw file). No B3 result, score or item was opened; STATUS.md was not read (L30). Every figure below is "
             "read by `stage3_elicitation_close.py` from the round records, the application check, the re-anchoring probe, the limits records and the anchor record.")
    L.append("")
    L.append("## 1. How the course ended")
    L.append("")
    L.append("Three writer rounds ran: GPT-6.1-sol rounds 1 to 3, Opus 5.5 round 1 (stopped by its provider safeguard: a recorded loss, not retried), Muse Wonder round 3 (its first, "
             "through the Cursor CLI). GPT-6.1-sol's rounds 4 to 6 were not run (brief 30 dated note 16: no quiet-but-illegible item in 303 valid, matching within writer). The "
             "edit-application check (dated note 17) then took Muse Wonder's matched effective n from 5.83 to 0, the follow-ups (note 18) put round 4 to Aravind as three options, "
             "and **the writer course ended on option C** (no round 4): the coordinator's message of 8 Nov relays Aravind's words, \"Let's proceed with C, ending the writer course, with "
             "the seed set kept and the re-anchoring probe.\" Nothing else launches under brief 30.")
    L.append("")
    L.append("## 2. The yield curve, by writer and round")
    L.append("")
    L.append("| writer | round | written | valid | quiet (gate i) | gate (ii) pass | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in d["yield_rows"]:
        L.append(f"| {r['writer']} | {r['round']} | " + " | ".join(str(r[k]) for k in FUNNEL_KEYS) + " |")
    L.append(f"| opus55 | 1 | {d['opus']['written']} | stopped | | | | | | | | |")
    L.append("")
    c = d["cumulative"]
    L.append("**Cumulative (before the placement check):** " + "; ".join(
        f"`{w}` written {v['written']}, valid {v['valid']}, certified {v['certified']}, quiet-but-illegible {v['quiet_but_illegible']}" for w, v in sorted(c.items()) if w != "all")
        + f"; **both writers: {c['all']['certified']} certified and {c['all']['quiet_but_illegible']} quiet-but-illegible of {c['all']['valid']} valid** "
        f"(certified per valid {c['all']['certified'] / c['all']['valid']:.3f}, illegible per valid {c['all']['quiet_but_illegible'] / c['all']['valid']:.3f}). "
        "Yields per valid item by writer and round are in each round record. Certified per valid item, by round: "
        + "; ".join(f"{w}: " + ", ".join(f"{r['certified']} of {r['valid']}" for r in d["yield_rows"] if r["writer"] == w) for w in sorted({r["writer"] for r in d["yield_rows"]}))
        + ". Quiet-but-illegible per valid item, by round: "
        + "; ".join(f"{w}: " + ", ".join(f"{r['quiet_but_illegible']} of {r['valid']}" for r in d["yield_rows"] if r["writer"] == w) for w in sorted({r["writer"] for r in d["yield_rows"]})) + ".")
    L.append("")
    L.append("## 3. The funnel by mechanism (valid items, both writers, rounds 1 to 3)")
    L.append("")
    L.append("| mechanism | valid | certified | quiet-but-illegible | mixed | part-derivable | loud | not evaluable |")
    L.append("|---|---|---|---|---|---|---|---|")
    for m, v in d["mechanisms"].items():
        L.append(f"| {m} | " + " | ".join(str(v[k]) for k in ("valid", "certified", "quiet_but_illegible", "mixed", "part_derivable", "loud", "not_evaluable")) + " |")
    L.append("")
    L.append("## 4. The placeable stock (the edit-application check, brief 26's rule unchanged)")
    L.append("")
    t = d["stock"]
    ck = d["check_totals"]
    L.append(f"Of {ck['items']} certified and quiet-but-illegible items, **{ck['kept']} are placeable and {ck['dropped']} are not** (`application-check-round2-states-v0.md` `{d['hashes']['application-check-round2-states-v0.md']}`). "
             "By writer and class, placeable: " + ", ".join(f"{k} {v}" for k, v in t["placeable_by_writer_class"].items()) + ". **By document and mechanism (placeable):**")
    L.append("")
    L.append("| document | mechanism | certified | quiet-but-illegible |")
    L.append("|---|---|---|---|")
    for doc_, ms in t["placeable_by_document_mechanism"].items():
        for m, cc in sorted(ms.items()):
            L.append(f"| {doc_} | {m} | {cc['certified']} | {cc['quiet_but_illegible']} |")
    L.append("")
    L.append(f"Matched effective n (note 7's rule, the 10-point band): {d['matched']['before']['n_eff']:.2f} on all {ck['items']} items; {d['matched']['after']['n_eff']:.2f} on the placeable stock "
             f"({d['matched']['after']['n_c_total']} certified and {d['matched']['after']['n_i_total']} illegible, no stratum holding both arms).")
    L.append("")
    L.append("## 5. The seed set and the re-anchoring probe")
    L.append("")
    s = d["probe"]
    L.append(f"The {ck['dropped']} dropped items are kept as the **certified seed set**, listed by id with their line kinds in a dated section of the application-check record (2026-11-08). By writer and class: "
             + ", ".join(f"{k} {v}" for k, v in t["seed_by_writer_class"].items()) + ". By document and mechanism:")
    L.append("")
    L.append("| document | mechanism | certified | quiet-but-illegible |")
    L.append("|---|---|---|---|")
    for doc_, ms in t["seed_by_document_mechanism"].items():
        for m, cc in sorted(ms.items()):
            L.append(f"| {doc_} | {m} | {cc['certified']} | {cc['quiet_but_illegible']} |")
    L.append("")
    L.append(f"**Placement-adaptive anchoring, the $0 probe** (`application-check-reanchoring-v0.md` `{d['hashes']['application-check-reanchoring-v0.md']}`): a re-anchoring of the replace lines to the text as it stands in a placement session's "
             f"state, keeping the statement, that meets brief 26's rule unchanged exists for **{s['re_anchorable']} of {s['items']}** items ({s['clean']} on the clean draws), the same at the thresholds 0.5, 0.7 and 0.9; "
             f"{s['no_counterpart']} have no counterpart (their target text is gone after the day's whole-document rewrite of the README, the fine-tuning guide and the on-call runbook, all on 2026-04-06), "
             f"{s['too_few']} have counterparts but too few valid draws. Re-certifying the {s['re_anchorable']} would cost about {s['price_cert']:.2f} USD at round 3's realised per-item rates "
             f"({s['price_dev']:.2f} USD with the development stage). The seed set is for re-checking on any later world by the same module (dated note 19).")
    L.append("")
    L.append("## 6. The outcome sentence (`rules-and-sentences-v0.md` section 3, one-document arm)")
    L.append("")
    o = d["outcome"]
    L.append(f"On the placeable stock ({d['stock_counts']['certified']} certified, {d['stock_counts']['illegible']} quiet-but-illegible, with these writers, under brief 26's placement rule) the counts select the row "
             f"**\"{o['row']}\"**, and the sentence the rules file fixes for it, brackets filled from the counts:")
    L.append("")
    L.append(f"> {o['sentence']}")
    L.append("")
    L.append("Scope, which the rules file requires and the counts need: with these writers (GPT-6.1-sol and Muse Wonder; Opus 5.5 stopped), one packet, one world, at n = "
             f"({d['stock_counts']['certified']}, {d['stock_counts']['illegible']}); the certified count is above the floor of 12 and the illegible count below it. Best writer beside: "
             f"GPT-6.1-sol {d['best']['gpt61sol']} placeable certified and no illegible item; Muse Wonder {d['best']['muse_certified']} placeable certified and {d['best']['muse_illegible']} placeable illegible. "
             f"Before the placement check the same counts were {d['cumulative']['all']['certified']} and {d['cumulative']['all']['quiet_but_illegible']}, which select the row "
             f"\"{select_outcome(d['cumulative']['all']['certified'], d['cumulative']['all']['quiet_but_illegible'])['row']}\". The writer course ended by Aravind's choice after round 3, not by the futility rule.")
    L.append("")
    L.append(f"**Next action by the rules file:** {o['next']} The no-dead-end sentence stands: work continues. The round-2 plan brief is the coordinator's.")
    L.append("")
    L.append("## 7. The human anchor (protocol section 9; drawn once, seed 20261211)")
    L.append("")
    a = d["anchor"]
    L.append(f"Drawn from every item of rounds 1 to 3 that passes gate (i) and was read to a class (pools: {', '.join(f'{k} {v}' for k, v in a['pools'].items())}; their ids hash `{a['pool_sha256'][:8]}`), "
             f"half from the certified and half from the others, 20 in all: " + ", ".join(f"{k} {v}" for k, v in a['draw']['by_class'].items()) + "; by writer "
             + ", ".join(f"{k} {v}" for k, v in a['draw']['by_writer'].items()) + ". Of the drawn certified items " + f"{a['placeability_of_the_drawn']['certified_placeable']} are placeable and "
             f"{a['placeability_of_the_drawn']['certified_not_placeable']} not (placeability was not a condition of the draw: the anchor measures the readers against a person, not the placement). "
             "**The sheet** (`human-anchor-sheet-v0.md`, `" + a['files']['human-anchor-sheet-v0.md']['sha256'][:8] + "`) shows Aravind, in Block A, each item's whole change as the readers see it and, in Block B, one edit of each item, "
             "with the fixed question, opaque salted ids, no class, no writer, no mechanism. **The draw file and key** (`human-anchor-draw-v0.json`, `" + a['files']['human-anchor-draw-v0.json']['sha256'][:8] + "`) hold the "
             "classes by sheet id and the salt. Both were written by `stage3_elicitation_anchor.py` and **have not been opened by this session**; they stay closed to everyone, Aravind included, until he has finished (the S4 precedent, A6.18 (q)). "
             "The date is set when he scores; his answers are scored by the same scorer against the same rubric in a later step. The draw is never repeated (the script refuses).")
    L.append("")
    L.append("## 8. Spend and the key ledger")
    L.append("")
    L.append("| round | spend outside the writers' own tokens, USD (about) |")
    L.append("|---|---|")
    for n, v in d["spend"].items():
        L.append(f"| {n} | {v:.1f} |")
    L.append(f"| **total, rounds 1 to 3** | **{sum(d['spend'].values()):.1f}** |")
    L.append("")
    L.append("The edit-application check, the follow-ups, the probe and the anchor draw cost $0. The two writers' own cost is on their subscriptions (ChatGPT billing, the Cursor account). "
             "Round 3's failed rater attempt ($3.11) is inside round 3's figure. **Kimi K3 reads on OpenRouter, by key number** (limit remaining and account balance, USD):")
    L.append("")
    L.append("| key | used in | limit before | limit after | limit fall | account before | account after | account fall |")
    L.append("|---|---|---|---|---|---|---|---|")
    for k, v in sorted(d["ledger"].items()):
        used = "round 1" if k == "key2" else "rounds 2 and 3"
        L.append(f"| {k[-1]} | {used} | {v['limit_before']:.2f} | {v['limit_after']:.2f} | {v['limit_fall']:.2f} | {v['account_before']:.2f} | {v['account_after']:.2f} | {v['account_fall']:.2f} |")
    L.append("")
    L.append("Key 2 was the fallback and was not rotated to after round 1 (note 11); key 1's weekly limit resets Monday 2026-11-09 00:00 UTC. The account falls exceed the limit falls by other use of the account.")
    L.append("")
    L.append("## 9. What is not done")
    L.append("")
    for x in d["not_done"]:
        L.append(f"- {x}")
    L.append("")
    L.append("## 10. Files (first 8 hex of sha256)")
    L.append("")
    L.append("Records under `part3/`: " + "; ".join(f"`{k}` {v}" for k, v in d["hashes"].items()) + ".")
    L.append("")
    L.append("Barrier audit: no B3 result, score or item opened; the S3 caches and `s3-applications-v0.json` never opened; STATUS.md not read; the writers' answers, traces and final messages and the human anchor's sheet and draw file "
             "never opened by this session after writing (by script only, counts and hashes); no key or `.env` value printed.")
    L.append("")
    return "\n".join(L)


NOT_DONE = [
    "**The pair pilot and the cross-document arm** (decision 6; `cross-document-items-v0.md`, `b4-constraints-v0.md`): held by the coordinator; not started.",
    "**Writer rounds 4 to 6**: GPT-6.1-sol's were not run (dated note 16); Muse Wonder's round 4 was not run (option C).",
    "**Scoring of the human anchor**: Aravind's answers, the same scorer and rubric, and the counts by class and agreement with the readers' classes (protocol section 9); the date is set when he scores.",
    "**Re-certification of any re-anchored item**: not run (dated note 19: a priced option, not free).",
    "**The round-2 plan brief** (the coordinator's): the draw, the arms matched on writer, document and composition band, the level contrast; it carries the additions of note 19.",
    "**A replacement for Opus 5.5** (a recorded loss): not run.",
]


def build(part3: Path) -> dict:
    P = Path(part3)
    import stage3_elicitation_application as ap
    rows, opus = [], {}
    rounds: dict[int, dict] = {}
    spend: dict[int, float] = {}
    for n in (1, 2, 3):
        r = _read(P / f"round-{n}-v0.json")
        rounds[n] = {"key1": r.get("key1"), "key2": r.get("key2")}
        spend[n] = float(r["spend_usd_approx"])
        for w, v in sorted(r["writers"].items()):
            if "funnel" in v:
                rows.append(dict(writer=w, round=n, **{k: v["funnel"][k] for k in FUNNEL_KEYS}))
            else:
                opus = {"written": v.get("written"), "outcome": v.get("outcome")}
    cum = cumulative(rows)
    check = _read(P / "application-check-round2-states-v0.json")
    stock = stock_tables(check["items"])
    probe = _read(P / "application-check-reanchoring-v0.json")
    p7 = probe["by_rho"]["0.7"]
    rc = p7["recertification"]
    kept = [r for r in check["items"] if not r["drop"]]
    sc = {"certified": sum(1 for r in kept if r["class"] == "certified"), "illegible": sum(1 for r in kept if r["class"] == "quiet_but_illegible")}
    anchor = _read(P / "human-anchor-record-v0.json")
    hash_names = ["round-1-v0.md", "round-2-v0.md", "round-3-v0.md", "forecast-after-r3-v0.md", "application-check-round2-states-v0.md", "application-check-round2-states-v0.json",
                  "application-check-followups-v0.md", "application-check-reanchoring-v0.md", "application-check-reanchoring-v0.json", "human-anchor-record-v0.json"]
    return {"yield_rows": rows, "opus": opus, "cumulative": cum, "mechanisms": mechanism_totals(P, ap.discover(P)), "stock": stock,
            "check_totals": {"items": len(check["items"]), "kept": len(kept), "dropped": len(check["items"]) - len(kept)},
            "matched": check["matched"], "probe": {"items": p7["items"], "re_anchorable": p7["re_anchorable"], "clean": p7["re_anchorable_clean"],
                                                   "no_counterpart": p7["by_class"].get("not: a target has no counterpart", 0), "too_few": p7["by_class"].get("not: too few valid draws", 0),
                                                   "price_cert": rc["certification_stage_usd"], "price_dev": rc["with_development_usd"]},
            "stock_counts": sc, "outcome": select_outcome(sc["certified"], sc["illegible"]),
            "best": {"gpt61sol": sum(1 for r in kept if r["writer"] == "gpt61sol" and r["class"] == "certified"),
                     "muse_certified": sum(1 for r in kept if r["writer"] == "muse_wonder" and r["class"] == "certified"),
                     "muse_illegible": sum(1 for r in kept if r["writer"] == "muse_wonder" and r["class"] == "quiet_but_illegible")},
            "anchor": anchor, "spend": spend, "ledger": ledger(rounds), "not_done": NOT_DONE,
            "hashes": {n: _sha8(P / n) for n in hash_names}}


def main(argv: list[str] | None = None) -> int:
    ap_ = argparse.ArgumentParser(description="brief 30 Part 3: the closing record")
    ap_.add_argument("mode", choices=("run",))
    ap_.add_argument("--part3", default=str(PART3))
    ns = ap_.parse_args(argv)
    P = Path(ns.part3)
    d = build(P)
    md = render_md(d)
    (P / "part3-close-v0.md").write_text(md, encoding="utf-8")
    out = {k: d[k] for k in ("cumulative", "stock_counts", "outcome", "best", "spend", "ledger", "check_totals", "probe")}
    out["written"] = datetime.now().astimezone().isoformat(timespec="seconds")
    (P / "part3-close-v0.json").write_text(json.dumps(out, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"md": hashlib.sha256(md.encode("utf-8")).hexdigest()[:8], "outcome": d["outcome"]["sentence"], "stock": d["stock_counts"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
