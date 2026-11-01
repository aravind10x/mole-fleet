#!/usr/bin/env python3
"""Brief 33 A2 (S3, 2026-11-02): the analysis matrix, `work/stage3/b3/s3-analysis-matrix-v0.json`.

One record per net item (plan section 1.1: the 73 candidates, the 21 control items and the 22 same-shape comparison items,
net of A6.17.11's pair-rule drops), keyed by brief 25's opaque id, holding what the readings script needs and nothing
else: regime, writer, document, the composition (the two-pass mean, A6.2) with both passes, the rater's section-2 line
scores (the three statements' two-pass means) and their maximum (S-Q), the rater's top-two gap, the replace share
(A5.12), `anchors_resolve`, the stratum membership, the population memberships of section 1.1 and the readers' D_part and
D_whole means per reader (S-K; brief 25). It reproduces section 1.2's table (means, SD, IQR, writer and document counts,
A6.17.3's pooled strata) from the same records.

Sources, each verified by sha256 before it is read (score and id fields only; no item line, document text, rubric or
declared effect is read into the output): the rater key, the four ratings files and the two checks files pinned in
`power-simulation-v3-inputs.json` (9a769d68) `inputs_sha256`, read through brief 20's own loader for the candidates
(`stage3_b3_power_v3.load_stimuli`); `comprehension/stratum-v0.json` (6113bd8d); `s1-populations-v0.json` (f17e7a72);
`inserter-dry-run-v1.json` (02138931), whose `inputs_sha256` pins the four payload and control files, read here for one
field only, each statement's `op` (the control items' replace share; the candidates' from the checks files as Part 3).

The matrix and the scores file are the readings script's only inputs. `render()` is deterministic (no timestamp).

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s3_matrix.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_b3_power_v3 as pv  # noqa: E402  (brief 20's loader: candidates' scores by the key; the checks' replace anchors)

VERSION = "b3-s3-analysis-matrix/v0"
OUT = "work/stage3/b3/s3-analysis-matrix-v0.json"
STRATUM = "work/stage3/b3/comprehension/stratum-v0.json"
S1 = "work/stage3/b3/s1-populations-v0.json"
V1 = "work/stage3/b3/inserter-dry-run-v1.json"
KEY = "work/stage3/b3/rater/key-b3.json"
RATINGS = {"s1": "work/stage3/b3/rater/ratings-b3-statements-p1.jsonl", "s2": "work/stage3/b3/rater/ratings-b3-statements-p2.jsonl",
           "t1": "work/stage3/b3/rater/ratings-b3-triples-p1.jsonl", "t2": "work/stage3/b3/rater/ratings-b3-triples-p2.jsonl"}
PAYLOADS = {"candidates-sonnet55": "work/stage3/b3/payloads-b3-candidates-sonnet55.json",
            "candidates-glm53": "work/stage3/b3/payloads-b3-candidates-glm53.json",
            "controls-sonnet55": "work/stage3/b3/controls-b3-sonnet55.json",
            "controls-glm53": "work/stage3/b3/controls-b3-glm53.json"}
#: every file this script reads, at the hash the plan's pre-flight block, power-simulation-v3-inputs.json (9a769d68)
#: `inputs_sha256` and inserter-dry-run-v1.json (02138931) `inputs_sha256` pin
INPUT_SHA256: dict[str, str] = {
    KEY: "04b1ca30582eafd7b7e58515b23a4f1df3932e43ede7daf2080f9a3547237335",
    RATINGS["s1"]: "8aca72f45d19b41b2df523fc932388f19d13f75e62efc6308f2c7969e8626d38",
    RATINGS["s2"]: "aa2421e917f4a178879eed258c3809b3c6782b6405fdc1e623755eb02f6694e6",
    RATINGS["t1"]: "7d8f4dfb2122b66707360e70584cd6f9c2bad4acbcaef86eecefd15fa501ede8",
    RATINGS["t2"]: "f70e55278e11b6c20417f998bebcf1d5c1b2862a4daf9dbca18b8f3589d1ee00",
    "work/stage3/b3/checks-b3-sonnet55-rerun.json": "e36cae53bce6f8ec85e8c5ddfa1d34a4468ce50a7787742a63c90a7dbbed7331",
    "work/stage3/b3/checks-b3-glm53.json": "35018bec6d301e15a0bcdbeed9aad2884c65f6841d6446f78a44221f46dc5dac",
    STRATUM: "6113bd8d4cd16768c5cfc83a2db3a109b2a0e0a81403341a88361787f3ca9932",
    S1: "f17e7a72430fc320f490340ddb3fb3dd741957d7dc098db00eff50c1e18f1ecf",
    V1: "021389311e33658884cf316778dc19a39b880ff9f884f9bb85598857c3260a47",
    PAYLOADS["candidates-sonnet55"]: "ebce93e8f913e890a5af21eecdff3321d499d455dae23617d56d083a405b85f0",
    PAYLOADS["candidates-glm53"]: "90611d780eb5ff585ee9bb94d04794cec862202d2dc29b220f2691923528da91",
    PAYLOADS["controls-sonnet55"]: "75fed7d0cfa3bad2e083e264f735074af1f73513a0a7b77bc25a728a6c90631e",
    PAYLOADS["controls-glm53"]: "0d1d418b26c98dee007195938b8571dbca50d6b5cdac0561095875ff7a09566e",
}
POPULATIONS = ("full", "stratum", "subset", "strict", "subset_and_strict", "certified", "preview_credited", "preview_illegible",
               "unresolved_stratum", "controls", "sham")
RATED = ("full", "stratum", "subset", "strict", "subset_and_strict", "certified", "preview_credited", "preview_illegible",
         "unresolved_stratum", "controls")
STRATUM_POPS = ("stratum", "subset", "strict", "subset_and_strict", "certified", "preview_credited", "preview_illegible", "unresolved_stratum")
POOL_MIN = 4          # A6.17.3
READERS = ("kimi", "sol")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ids_sha256(ids) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def verify_inputs(root: Path) -> dict[str, str]:
    """Every input at its pinned sha256, before anything is read; refuses on the first mismatch."""
    got = {}
    for rel, want in INPUT_SHA256.items():
        p = root / rel
        if not p.is_file():
            raise SystemExit(f"{rel}: missing (sha256 {want[:8]} expected)")
        h = sha256_file(p)
        if h != want:
            raise SystemExit(f"{rel}: sha256 {h[:8]} is not the pinned {want[:8]}")
        got[rel] = h
    return got


def _scores(root: Path, rel: str, idk: str) -> dict[str, float]:
    out = {}
    for line in (root / rel).read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out[d[idk]] = float(d["score"])        # the score and its id: nothing else is read
    return out


def _ops(root: Path) -> dict[tuple[str, str], list[str]]:
    """Each payload's statement ops by (source, id), the one field read from the payload and control files."""
    out = {}
    for src, rel in PAYLOADS.items():
        for p in json.loads((root / rel).read_text(encoding="utf-8"))["payloads"]:
            out[(src, p["id"])] = [str(s.get("op")) for s in p["statements"]]
    return out


def pooled_strata(docs: list[str], pool_min: int = POOL_MIN) -> dict[str, str]:
    """A6.17.3: a document with fewer than pool_min members of the population pools into one stratum."""
    c = Counter(docs)
    return {d: (d if c[d] >= pool_min else "pooled") for d in sorted(c)}


def describe(ids: list[str], items: Mapping[str, Mapping[str, Any]], rated: bool) -> dict[str, Any]:
    rec = [items[i] for i in ids]
    docs = [r["document"] for r in rec]
    strata = pooled_strata(docs)
    out: dict[str, Any] = {"n": len(ids), "by_writer": dict(sorted(Counter(r["writer"] for r in rec).items())),
                           "n_documents": len(set(docs)), "document_counts": sorted(Counter(docs).values(), reverse=True),
                           "strata_pooled": sorted(Counter(strata[d] for d in docs).values(), reverse=True)}
    comp = [r.get("composition") for r in rec]
    if rated and ids and all(c is not None for c in comp):
        c = np.array(comp, dtype=float)
        out.update({"mean": float(c.mean()), "sd": float(c.std(ddof=1)) if len(c) > 1 else None,
                    "iqr": [float(np.quantile(c, .25)), float(np.quantile(c, .75))]})
    else:
        out.update({"mean": None, "sd": None, "iqr": None})
    return out


def build(root: Path) -> dict[str, Any]:
    hashes = verify_inputs(root)
    key = json.loads((root / KEY).read_text(encoding="utf-8"))
    st = json.loads((root / STRATUM).read_text(encoding="utf-8"))["items"]
    s1 = json.loads((root / S1).read_text(encoding="utf-8"))
    v1 = json.loads((root / V1).read_text(encoding="utf-8"))
    for src, want in (("candidates_sonnet55", PAYLOADS["candidates-sonnet55"]), ("candidates_glm53", PAYLOADS["candidates-glm53"]),
                      ("controls_sonnet55", PAYLOADS["controls-sonnet55"]), ("controls_glm53", PAYLOADS["controls-glm53"])):
        if v1["inputs_sha256"][src] != INPUT_SHA256[want]:
            raise SystemExit(f"{want}: the pinned sha256 differs from inserter-dry-run-v1.json's inputs_sha256")
    if v1["inputs_sha256"]["stratum_v0"] != INPUT_SHA256[STRATUM] or v1["inputs_sha256"]["key_b3"] != INPUT_SHA256[KEY]:
        raise SystemExit("the stratum file or the rater key differ from inserter-dry-run-v1.json's inputs_sha256")
    s1_s, s2_s = _scores(root, RATINGS["s1"], "statement_id"), _scores(root, RATINGS["s2"], "statement_id")
    t1_s, t2_s = _scores(root, RATINGS["t1"], "triple_id"), _scores(root, RATINGS["t2"], "triple_id")
    ops = _ops(root)
    stim = {(t["writer"], t["id"]): t for t in pv.load_stimuli(root)}   # candidates: brief 20's loader (checks' replace anchors)
    lines: dict[tuple[str, str, str], dict[int, tuple[float, float]]] = {}
    for sid, v in key["statements"].items():
        if v["source"].startswith(("candidates-", "controls-")):
            lines.setdefault((v["source"], v["writer"], v["id"]), {})[int(v["statement_index"])] = (s1_s[sid], s2_s[sid])
    net_ids: dict[str, list[str]] = {p: list(s1["populations"][p]["net_pair"]["ids"]) for p in POPULATIONS}
    all_ids = sorted(set(net_ids["full"]) | set(net_ids["controls"]) | set(net_ids["sham"]))
    drops = set(s1["drops"]["pair"]["ids"])
    if set(all_ids) & drops:
        raise SystemExit("a dropped item is in a net population")
    items: dict[str, dict[str, Any]] = {}
    for tid in all_ids:
        s = st[tid]
        reg = s["regime"]
        rec: dict[str, Any] = {"regime": reg, "writer": s["writer"], "document": s["document"],
                               "anchors_resolve": bool(s["anchors_resolve"]), "membership": s["membership"],
                               "populations": [p for p in POPULATIONS if tid in set(net_ids[p])],
                               "readers": {rd: {"D_part_mean": float(s["readers"][rd]["D_part_mean"]), "D_whole_mean": float(s["readers"][rd]["D_whole_mean"])}
                                           for rd in READERS if rd in s.get("readers", {})}}
        if reg in ("candidate", "control"):
            kv = key["triples"][tid]
            src, w, pid = kv["source"], kv["writer"], kv["id"]
            if w != s["writer"] or kv["document"] != s["document"]:
                raise SystemExit(f"{tid}: the key's writer or document differs from the stratum file's")
            L = lines[(src, w, pid)]
            if sorted(L) != [0, 1, 2]:
                raise SystemExit(f"{tid}: statements {sorted(L)}")
            p1, p2 = [L[j][0] for j in range(3)], [L[j][1] for j in range(3)]
            ls = [(a + b) / 2 for a, b in zip(p1, p2)]
            if reg == "candidate":
                t = stim[(w, pid)]
                if t["p1"] != p1 or t["p2"] != p2 or (t["c1"], t["c2"]) != (t1_s[tid], t2_s[tid]):
                    raise SystemExit(f"{tid}: the key's scores differ from brief 20's loader")
                replace = sum(t["replace"]) / 3
            else:
                replace = sum(1 for o in ops[(src, pid)] if o == "replace") / 3
            top2 = sorted(ls)
            rec.update({"composition_p1": t1_s[tid], "composition_p2": t2_s[tid], "composition": (t1_s[tid] + t2_s[tid]) / 2,
                        "line_scores_p1": p1, "line_scores_p2": p2, "line_scores": ls, "line_max": max(ls),
                        "top_two_gap": top2[-1] - top2[-2], "replace_share": replace})
        else:
            rec.update({"composition_p1": None, "composition_p2": None, "composition": None, "line_scores_p1": None,
                        "line_scores_p2": None, "line_scores": None, "line_max": None, "top_two_gap": None, "replace_share": None})
        items[tid] = rec
    pops = {p: {"n": len(net_ids[p]), "ids_sha256": ids_sha256(net_ids[p]), "ids": sorted(net_ids[p])} for p in POPULATIONS}
    for p in POPULATIONS:
        if pops[p]["ids_sha256"] != s1["populations"][p]["net_pair"]["ids_sha256"]:
            raise SystemExit(f"population {p}: the id hash differs from s1-populations-v0.json")
    sec = {p: describe(pops[p]["ids"], items, p in RATED) for p in POPULATIONS}
    strata = {p: pooled_strata([items[i]["document"] for i in pops[p]["ids"]]) for p in STRATUM_POPS}
    return {"version": VERSION, "brief": "33 v2.1", "inputs_sha256": hashes,
            "conventions": {"ids_sha256": "sha256 of the sorted ids joined by newlines (brief 25)",
                            "composition": "the two-pass mean (A6.2); SD ddof 1; IQR by linear interpolation (A6.11 (4))",
                            "line_scores": "the rater's section-2 scores of the three statements, each the two-pass mean, in statement order; line_max is their maximum (S-Q); top_two_gap the largest minus the second largest",
                            "replace_share": "A5.12: the share of the item's three statements whose op is replace (candidates by brief 20's checks-file method, control items by the payload op)",
                            "pooled_strata": f"A6.17.3: documents with fewer than {POOL_MIN} members pool into one stratum, on the stratum populations only; the full set keeps its document factor",
                            "net": "net of A6.17.11's pair-rule drops (s1-populations-v0.json net_pair)",
                            "readers": "brief 25's D_part and D_whole means over the two samples per reader (stratum-v0.json)"},
            "populations": pops, "section_1_2": sec, "pooled_strata": strata, "items": items}


def render(m: Mapping[str, Any]) -> str:
    return json.dumps(m, indent=1, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT)
    ns = ap.parse_args(argv)
    root = HERE.parents[1]
    text = render(build(root))
    out = root / ns.out
    out.write_text(text, encoding="utf-8")
    m = json.loads(text)
    print(f"wrote {ns.out} sha256 {hashlib.sha256(text.encode()).hexdigest()}")
    print(f"  items {len(m['items'])} by regime {dict(Counter(r['regime'] for r in m['items'].values()))}")
    for p, d in m["section_1_2"].items():
        print(f"  {p}: n {d['n']} mean {d['mean'] if d['mean'] is None else round(d['mean'], 2)} sd {d['sd'] if d['sd'] is None else round(d['sd'], 2)} "
              f"iqr {d['iqr']} writers {d['by_writer']} documents {d['document_counts']} pooled {d['strata_pooled']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
