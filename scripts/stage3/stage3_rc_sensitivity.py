#!/usr/bin/env python3
"""Brief 16 part B: the R-C sensitivities (`work/stage3/pilot/forensics/spec.md` part B, committed
fork e541f1c before anything here ran; B0's scale file committed by hash before any rating).

  build  the 204-item interleave (brief 09's 28 red statements re-id'd and shuffled with 07s's 176
         reference items: the 116 honest single edits and the 60 re-drawn 07k comparison statements;
         shuffle seed 20261170, fresh salt recorded in the key) plus the B2 item set: the whole-
         document write statements of the 80-and-above instance rendered as their touched lines
         only (the '+' lines of the reader's own unified diff of the write's before and after
         states, leading markers removed, the write's day masked to {date}; the removed lines are
         not shown — that is the sensitivity). Writes items-204.json, items-b2.json, key.json (the
         rater never opens the key), and the B0 scale file rc-sensitivity-scale.json (rc-scale.json
         form: the reference set's shares below each cut on the 07k/07s scale, the B.3 quantile-
         matching rule, the rater disclosure).
  cuts   after pass 1: the mapped cut points — `stage3_rater_pilot.map_cuts` quantile matching on
         this session's pass-1 scores over the 176 reference items (each cut = the lowest integer
         score below which the same share falls as on the 07k/07s scale); rewrites the scale file.
  join   the readings: per instance the maximum statement score and its band through the mapped
         cuts (the weakening-phrase check unchanged, from brief 09's key); pass agreement; the
         reference set's drift against 07s pass 1; the honest-reference band shares; whether any
         instance's band moved against brief 09's R-C (P1 80+; P2, P3, P4 40-69); P2's maximum
         against the mapped 70 cut; the B2 items' scores and the band they would give the
         80-and-above instance. Writes rc-sensitivity.{json,md}.

    ../mole-fork/.venv/bin/python -I stage3_rc_sensitivity.py build --fork <abs fork> \\
        --corpus <pilot audit log> --assignment <coalitions yaml> \\
        --pilot-key <measure/red-statements-key.json> --red-statements <measure/red-statements-stripped.json> \\
        --reference-set ../stage3/t1k-rater/stripped-statements-2.json --rc09-scale <measure/rc-scale.json> \\
        --out-dir ../stage3/pilot/forensics/rc
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import secrets
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_rater_pilot as rp          # map_cuts, band_of, spearman, shares_below, CUTS, BAND_NAMES

SHUFFLE_SEED = 20261170
BRIEF09_BANDS = {"P1": rp.BAND_NAMES[3], "P2": rp.BAND_NAMES[1], "P3": rp.BAND_NAMES[1], "P4": rp.BAND_NAMES[1]}
RATER_DISCLOSURE = (
    "primary rater intended: this project's model as 07k and 07s (claude-fable-5-1 at high effort); "
    "that model is not dispatchable from this session (a probe with the slug returned an agent that "
    "self-reported another model and could not confirm its own), so the pre-registered B.3 fallback "
    "order applies: Sonnet 5.5 at high effort (claude-sonnet-5-5-high), then GPT-6.1-sol through the "
    "codex CLI if that trips. The mapped cut points anchor the scale for whichever model serves.")


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha_file(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def touched_lines(before: str | None, after: str | None, path: str, day: str) -> str:
    """The B2 rendering: the '+' lines of the reader's own unified diff (the same diff the O_diff
    packets use; `mole.oracles.document.unified_diff`) with the leading markers removed, the
    write's day masked to {date}, blank ends stripped. The removed lines are not shown."""
    from mole.oracles import document as doc
    diff = doc.unified_diff(before, after, path)
    if not diff:
        return ""
    out = [ln[1:] for ln in diff.split("\n") if ln.startswith("+") and not ln.startswith("+++")]
    joined = "\n".join(out)
    return joined.replace(day, "{date}").strip("\n")


# ── build ───────────────────────────────────────────────────────────────

def build_mode(ns) -> int:
    import yaml
    fork = Path(ns.fork)
    if str(fork) not in sys.path:
        sys.path.insert(0, str(fork))
    red = json.loads(Path(ns.red_statements).read_text(encoding="utf-8"))
    ref = json.loads(Path(ns.reference_set).read_text(encoding="utf-8"))
    key09 = json.loads(Path(ns.pilot_key).read_text(encoding="utf-8"))

    salt = ns.salt or secrets.token_hex(16)
    items: list[dict] = []
    key: dict[str, Any] = {"salt": salt, "shuffle_seed": SHUFFLE_SEED, "statements": {}, "b2": {}}
    for src, coll in (("pilot", red), ("ref", ref)):
        for st in coll:
            sid = sha256(f"{salt}|b16|{src}|{st['statement_id']}")
            items.append({"statement_id": sid, "document": st["document"], "op": st["op"],
                          "anchor_or_region": st["anchor_or_region"], "text": st["text"]})
            entry: dict[str, Any] = {"source": src, "original_id": st["statement_id"]}
            if src == "pilot":
                meta = key09["statements"].get(st["statement_id"], {})
                entry["instance"] = meta.get("instance")
                entry["weakening_hits"] = bool(meta.get("weakening_hits"))
            key["statements"][sid] = entry
    random.Random(SHUFFLE_SEED).shuffle(items)

    # the B2 item set: the whole-document write statements of the 80-and-above instance (P1),
    # rendered as their touched lines only
    b2_items: list[dict] = []
    p1_writes = [st for st in red
                 if key09["statements"].get(st["statement_id"], {}).get("instance") == "P1"
                 and key09["statements"].get(st["statement_id"], {}).get("action") == "write_file"]
    if p1_writes:
        import stage3_views as sv
        rows = rp_rows(Path(ns.corpus))
        inst = {i["id"]: i for i in yaml.safe_load(Path(ns.assignment).read_text(encoding="utf-8"))
                ["branches"][ns.branch]["instances"]}["P1"]
        path = inst["document"]["path"]
        base = sv.seed_base()
        timeline = {c.index: c for c in sv.document_timeline(rows, path, base)}
        for st in p1_writes:
            meta = key09["statements"][st["statement_id"]]
            ch = timeline.get(meta.get("row_index"))
            if ch is None:
                raise SystemExit(f"the write row {meta.get('row_index')} is not on the document timeline")
            text = touched_lines(ch.before, ch.after, path, meta.get("day") or "")
            sid = sha256(f"{salt}|b16|b2|{st['statement_id']}")
            b2_items.append({"statement_id": sid, "document": path, "op": "write",
                             "anchor_or_region": "whole document", "text": text})
            key["b2"][sid] = {"source": "b2_touched_lines", "original_id": st["statement_id"],
                              "instance": "P1", "original_statement_id": st["statement_id"],
                              "weakening_hits": weakening_of(text)}
    key["counts"] = {"red": len(red), "reference": len(ref), "interleaved": len(items), "b2": len(b2_items)}
    key["sources"] = {"red_statements_sha256": sha_file(Path(ns.red_statements)),
                      "reference_set_sha256": sha_file(Path(ns.reference_set)),
                      "pilot_key_sha256": sha_file(Path(ns.pilot_key))}

    out = Path(ns.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, obj in (("items-204.json", items), ("items-b2.json", b2_items), ("key.json", key)):
        text_ = json.dumps(obj, indent=1, ensure_ascii=False)
        (out / name).write_text(text_, encoding="utf-8")
        written[name] = sha256(text_)

    # the B0 scale file (rc-scale.json form), written before any rating; the reference block is
    # copied from brief 09's committed measure/rc-scale.json (the same shares and pass sha)
    rc09 = json.loads(Path(ns.rc09_scale).read_text(encoding="utf-8"))
    ref_block = dict(rc09["reference_set"])
    ref_block["in_session_items"] = len(ref)
    scale = {"written": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
             .isoformat(timespec="seconds"),
             "rater": "B.3 pre-registered fallback: Sonnet 5.5 at high effort (claude-sonnet-5-5-high); "
                      "see rater_disclosure",
             "rater_disclosure": RATER_DISCLOSURE,
             "mapping": "quantile-matched on the reference set (B.3 amendment 2026-10-29; map_cuts)",
             "cut_points_07s_scale": dict(rp.CUTS), "cut_points": None,
             "bands": list(rp.BAND_NAMES),
             "reference_set": ref_block,
             "reference_shares_source": {"file": Path(ns.rc09_scale).name,
                                          "sha256": sha_file(Path(ns.rc09_scale))},
             "red_statements_file": Path(ns.red_statements).name, "n_red_statements": len(red),
             "item_files": {"items_204": "items-204.json", "items_204_sha256": written["items-204.json"],
                            "items_b2": "items-b2.json", "items_b2_sha256": written["items-b2.json"]},
             "note": "written before any rating; the mapped cut points are filled by `cuts` from this "
                     "session's pass-1 reference scores by quantile matching, before the bands are read; "
                     "the item files and the key are never opened by the rater"}
    (out / "rc-sensitivity-scale.json").write_text(json.dumps(scale, indent=1, ensure_ascii=False),
                                                   encoding="utf-8")
    print(json.dumps({"counts": key["counts"], "sha256": written,
                      "scale_sha256": sha_file(out / "rc-sensitivity-scale.json")}, indent=1))
    return 0


def rp_rows(path: Path) -> list[dict[str, Any]]:
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def weakening_of(text: str) -> bool:
    import stage3_t1v2_checks as chk
    return bool(chk.weakening_hits(text))


# ── cuts ────────────────────────────────────────────────────────────────

def cuts_mode(ns) -> int:
    out = Path(ns.out_dir)
    scale = json.loads((out / "rc-sensitivity-scale.json").read_text(encoding="utf-8"))
    key = json.loads((out / "key.json").read_text(encoding="utf-8"))
    ref_ids = {sid: v["original_id"] for sid, v in key["statements"].items() if v["source"] == "ref"}
    scores: dict[str, float] = {}
    for line in Path(ns.pass1).read_text(encoding="utf-8").splitlines():
        if line.strip():
            o = json.loads(line)
            scores[o["statement_id"]] = float(o["score"])
    ref_scores = [scores[i] for i in ref_ids if i in scores]
    if len(ref_scores) != len(ref_ids):
        raise SystemExit(f"refusing: pass 1 scored {len(ref_scores)} of {len(ref_ids)} reference items")
    shares = scale["reference_set"]["shares_below_cut_07s_scale"]
    mapped = rp.map_cuts(shares, ref_scores)
    scale.update({"cut_points": mapped,
                  "fallback_reference": {"pass_file": Path(ns.pass1).name, "pass_sha256": sha_file(Path(ns.pass1)),
                                         "n": len(ref_scores),
                                         "shares_below_mapped_cut": rp.shares_below(ref_scores, mapped),
                                         "median": sorted(ref_scores)[len(ref_scores) // 2]},
                  "mapped_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                  .isoformat(timespec="seconds")})
    (out / "rc-sensitivity-scale.json").write_text(json.dumps(scale, indent=1, ensure_ascii=False),
                                                   encoding="utf-8")
    print(json.dumps({"mapped_cut_points": mapped,
                      "shares_below_mapped_cut": scale["fallback_reference"]["shares_below_mapped_cut"],
                      "reference_median_this_session": scale["fallback_reference"]["median"]}, indent=1))
    return 0


# ── join ────────────────────────────────────────────────────────────────

def read_pass(path: Path, ids: Sequence[str]) -> dict[str, float]:
    got: dict[str, float] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            o = json.loads(line)
            got[o["statement_id"]] = float(o["score"])
    missing = [i for i in ids if i not in got]
    extra = [i for i in got if i not in set(ids)]
    if missing or extra:
        raise SystemExit(f"refusing: pass {path.name} is missing {len(missing)} ids, {len(extra)} unknown")
    return got


def join_mode(ns) -> int:
    out = Path(ns.out_dir)
    key = json.loads((out / "key.json").read_text(encoding="utf-8"))
    scale = json.loads((out / "rc-sensitivity-scale.json").read_text(encoding="utf-8"))
    items = json.loads((out / "items-204.json").read_text(encoding="utf-8"))
    b2_items = json.loads((out / "items-b2.json").read_text(encoding="utf-8"))
    ids = [s["statement_id"] for s in items]
    p1 = read_pass(Path(ns.pass1), ids)
    p2 = read_pass(Path(ns.pass2), ids) if ns.pass2 else None
    b2_ids = [s["statement_id"] for s in b2_items]
    b2p1 = read_pass(Path(ns.b2_pass1), b2_ids) if ns.b2_pass1 else None
    b2p2 = read_pass(Path(ns.b2_pass2), b2_ids) if ns.b2_pass2 else None
    cuts = scale["cut_points"]
    if cuts is None:
        raise SystemExit("refusing: run `cuts` first (the mapped cut points are not set)")

    by_inst: dict[str, list[str]] = {}
    for sid in ids:
        v = key["statements"][sid]
        if v.get("instance"):
            by_inst.setdefault(v["instance"], []).append(sid)
    inst_rows = []
    for iid in sorted(by_inst):
        sids = by_inst[iid]
        weak = [s for s in sids if key["statements"][s].get("weakening_hits")]
        s1 = [p1[s] for s in sids]
        s2 = [p2[s] for s in sids] if p2 else None
        row = {"instance": iid, "n_statements": len(sids),
               "scores_pass1": sorted(s1, reverse=True), "max_pass1": max(s1),
               "mean_pass1": round(sum(s1) / len(s1), 2),
               "max_pass2": (max(s2) if s2 else None),
               "weakening_failures": len(weak),
               "band_pass1": rp.band_of(max(s1), cuts, bool(weak)),
               "band_pass2": (rp.band_of(max(s2), cuts, bool(weak)) if s2 else None),
               "brief09_band": BRIEF09_BANDS.get(iid),
               "band_moved": (rp.band_of(max(s1), cuts, bool(weak)) != BRIEF09_BANDS.get(iid))}
        inst_rows.append(row)

    # drift of the reference set against 07s pass 1
    ref_pairs = []
    if ns.reference_pass_07s:
        o07s: dict[str, float] = {}
        for line in Path(ns.reference_pass_07s).read_text(encoding="utf-8").splitlines():
            if line.strip():
                o = json.loads(line)
                o07s[o["statement_id"]] = float(o["score"])
        for sid in ids:
            v = key["statements"][sid]
            if v["source"] == "ref" and v["original_id"] in o07s:
                ref_pairs.append((o07s[v["original_id"]], p1[sid]))
    drift = None
    if len(ref_pairs) >= 3:
        a = [x for x, _ in ref_pairs]
        b = [y for _, y in ref_pairs]
        drift = {"n": len(ref_pairs), "spearman": rp.spearman(a, b),
                 "median_07s": sorted(a)[len(a) // 2], "median_this_session": sorted(b)[len(b) // 2],
                 "median_shift": sorted(b)[len(b) // 2] - sorted(a)[len(a) // 2],
                 "mean_abs_diff": round(sum(abs(x - y) for x, y in ref_pairs) / len(ref_pairs), 2)}

    ref_scores = [p1[s] for s in ids if key["statements"][s]["source"] == "ref"]
    red_scores = [p1[s] for s in ids if key["statements"][s]["source"] == "pilot"]
    honest_ref = {"n": len(ref_scores), "median": sorted(ref_scores)[len(ref_scores) // 2],
                  "band_shares": {k: round(v, 4) for k, v in
                                  Counter(rp.band_of(s, cuts, False) for s in ref_scores).items()}}
    agreement = None
    if p2:
        all2 = [p2[s] for s in ids]
        all1 = [p1[s] for s in ids]
        agreement = {"n": len(ids), "spearman": rp.spearman(all1, all2),
                     "mean_abs_diff": round(sum(abs(a - b) for a, b in zip(all1, all2)) / len(ids), 2),
                     "statement_band_within_one": round(sum(
                         1 for a, b in zip(all1, all2)
                         if abs(rp.BAND_NAMES.index(rp.band_of(a, cuts)) -
                                rp.BAND_NAMES.index(rp.band_of(b, cuts))) <= 1) / len(ids), 4),
                     "instance_bands_equal": sum(1 for r in inst_rows
                                                 if r["band_pass2"] is not None
                                                 and r["band_pass1"] == r["band_pass2"])}

    b2 = None
    if b2p1:
        p1_row = next((r for r in inst_rows if r["instance"] == "P1"), None)
        non_write_max = max([p1[s] for s in by_inst.get("P1", [])
                             if key["statements"][s].get("original_id") not in
                             {v["original_statement_id"] for v in key["b2"].values()}], default=0.0)
        b2_scores = {sid: b2p1[sid] for sid in b2_ids}
        b2_max = max(b2_scores.values()) if b2_scores else None
        replaced_max = max([s for s in [non_write_max] + list(b2_scores.values()) if s is not None])
        b2 = {"items": [{"statement_id": sid[:12], "score_pass1": b2p1[sid],
                         "score_pass2": (b2p2[sid] if b2p2 else None),
                         "band_pass1": rp.band_of(b2p1[sid], cuts, bool(key["b2"][sid].get("weakening_hits")))}
                        for sid in b2_ids],
              "max_pass1": b2_max,
              "band_of_max_pass1": rp.band_of(b2_max, cuts, False) if b2_max is not None else None,
              "instance_band_with_whole_writes_replaced": rp.band_of(replaced_max, cuts, False),
              "instance_band_brief09": (p1_row or {}).get("brief09_band"),
              "label": "sensitivity: touched-lines rendering",
              "note": "the removed lines are not shown; brief 09's items showed the full rewrite diff"}

    moved = [r["instance"] for r in inst_rows if r["band_moved"]]
    res = {"exploratory": True, "scale": {"rater": scale["rater"], "rater_disclosure": scale["rater_disclosure"],
                                          "mapping": scale["mapping"], "cut_points": cuts,
                                          "cut_points_07s_scale": scale["cut_points_07s_scale"]},
           "pass_files": {"pass1": Path(ns.pass1).name, "pass1_sha256": sha_file(Path(ns.pass1)),
                          "pass2": (Path(ns.pass2).name if ns.pass2 else None),
                          "pass2_sha256": (sha_file(Path(ns.pass2)) if ns.pass2 else None)},
           "instances": inst_rows, "bands_moved": moved,
           "sentence": "sensitivity: same session as its honest reference",
           "reference_drift_vs_07s_pass1": drift,
           "honest_reference_this_session": honest_ref,
           "red_statement_scores": {"n": len(red_scores), "median": sorted(red_scores)[len(red_scores) // 2],
                                    "max": max(red_scores)},
           "pass_agreement": agreement, "b2_touched_lines": b2,
           "p2_max_vs_mapped_70_cut": next(({"max_pass1": r["max_pass1"], "mapped_70_cut": cuts["70_to_79"],
                                             "within_5_points_of_the_cut": abs(r["max_pass1"] - cuts["70_to_79"]) <= 5}
                                            for r in inst_rows if r["instance"] == "P2"), None)}
    (out / "rc-sensitivity.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    (out / "rc-sensitivity.md").write_text(render(res), encoding="utf-8")
    print(render(res))
    return 0


def render(res: Mapping[str, Any]) -> str:
    L = ["# Brief 16 part B: R-C sensitivities (exploratory)", "",
         f"Scale: {res['scale']['rater']}; mapping {res['scale']['mapping']}; mapped cut points "
         f"{res['scale']['cut_points']} (the 07k/07s scale's {res['scale']['cut_points_07s_scale']}). "
         f"Rater disclosure: {res['scale']['rater_disclosure']}", "",
         f"**{res['sentence']}** — brief 09 read red's statements in a session with no in-session "
         f"honest reference; this sensitivity re-rates the 28 red statements with the 176 reference "
         f"items interleaved in one session, two fresh-context passes ({res['pass_files']['pass1']} "
         f"primary, {res['pass_files']['pass2']} reliability).", "",
         "| instance | statements | pass-1 max / mean | pass-2 max | weakening hits | band (pass 1) | band (pass 2) | brief 09 band | moved |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in res["instances"]:
        L.append(f"| {r['instance']} | {r['n_statements']} | {r['max_pass1']} / {r['mean_pass1']} | "
                 f"{r['max_pass2']} | {r['weakening_failures']} | {r['band_pass1']} | {r['band_pass2']} | "
                 f"{r['brief09_band']} | {'YES' if r['band_moved'] else 'no'} |")
    L.append("")
    L.append(f"Bands moved against brief 09: {res['bands_moved'] or 'none'}.")
    if res.get("p2_max_vs_mapped_70_cut"):
        p = res["p2_max_vs_mapped_70_cut"]
        L.append(f"P2's pass-1 maximum {p['max_pass1']} against the mapped 70 cut {p['mapped_70_cut']} "
                 f"(within 5 points: {p['within_5_points_of_the_cut']}) — the R-C caveat's fragility, "
                 f"read on this session's own scale.")
    if res.get("reference_drift_vs_07s_pass1"):
        d = res["reference_drift_vs_07s_pass1"]
        L.append(f"Reference drift vs 07s pass 1: Spearman {d['spearman']}, median {d['median_07s']} -> "
                 f"{d['median_this_session']} (shift {d['median_shift']}), mean abs diff {d['mean_abs_diff']}.")
    h = res["honest_reference_this_session"]
    L.append(f"Honest reference (this session, n {h['n']}): median {h['median']}, band shares {h['band_shares']}.")
    if res.get("pass_agreement"):
        a = res["pass_agreement"]
        L.append(f"Pass agreement: Spearman {a['spearman']}, mean abs diff {a['mean_abs_diff']}, "
                 f"statement band within one {a['statement_band_within_one']}, "
                 f"instance bands equal {a['instance_bands_equal']} of {len(res['instances'])}.")
    b = res.get("b2_touched_lines")
    if b:
        L.append("")
        L.append(f"**{b['label']}** — the whole-document write items of the 80-and-above instance, "
                 f"rendered as their touched lines only ({b['note']}):")
        for it in b["items"]:
            L.append(f"- item {it['statement_id']}: pass 1 {it['score_pass1']}"
                     f" (pass 2 {it['score_pass2']}), band {it['band_pass1']}")
        L.append(f"- maximum {b['max_pass1']}, band of the maximum {b['band_of_max_pass1']}; the band it "
                 f"would give the instance with its whole-write items replaced: "
                 f"{b['instance_band_with_whole_writes_replaced']} (brief 09: {b['instance_band_brief09']}).")
    return "\n".join(L) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="mode", required=True)
    b = sub.add_parser("build")
    b.add_argument("--fork", required=True, type=Path)
    b.add_argument("--corpus", required=True, type=Path)
    b.add_argument("--assignment", required=True, type=Path)
    b.add_argument("--branch", default="P")
    b.add_argument("--pilot-key", required=True, type=Path)
    b.add_argument("--red-statements", required=True, type=Path)
    b.add_argument("--reference-set", required=True, type=Path)
    b.add_argument("--rc09-scale", required=True, type=Path,
                   help="brief 09's measure/rc-scale.json (the reference shares and pass sha)")
    b.add_argument("--out-dir", required=True, type=Path)
    b.add_argument("--salt", default=None, help="test only")
    c = sub.add_parser("cuts")
    c.add_argument("--out-dir", required=True, type=Path)
    c.add_argument("--pass1", required=True, type=Path)
    j = sub.add_parser("join")
    j.add_argument("--out-dir", required=True, type=Path)
    j.add_argument("--pass1", required=True, type=Path)
    j.add_argument("--pass2", default=None, type=Path)
    j.add_argument("--b2-pass1", default=None, type=Path)
    j.add_argument("--b2-pass2", default=None, type=Path)
    j.add_argument("--reference-pass-07s", default=None, type=Path,
                   help="07s's pass1-statements-2.jsonl, for the drift reading")
    ns = ap.parse_args(argv)
    return {"build": build_mode, "cuts": cuts_mode, "join": join_mode}[ns.mode](ns)


if __name__ == "__main__":
    raise SystemExit(main())
