#!/usr/bin/env python3
"""Brief 28 (B3's S1 draft): the populations of the plan by sorted-id sha256 and count, from files on disk only.

Reads brief 25's `stratum-v0.json` (per item by opaque id: regime, writer, document, anchor status, membership,
composition, the readers' D_part and D_whole) and brief 26's `inserter-dry-run-v0.json` (the drop lists under the pair
rule and the literal count), checks both by hash, and writes `work/stage3/b3/s1-populations-v0.json`: every population
S1 names, gross, net of A6.17.11's pair-rule drops and net of the literal count, each with its sorted ids, their sha256
(newline-joined, brief 25's convention), writer and document counts, A6.17.3's pooled strata and, for rated items, the
composition mean, SD (ddof 1) and IQR (linear interpolation, A6.11 (4)). Ids, counts and aggregates only: no item line,
rubric, declared effect, document name or document text is read into the output. No draw is computed.

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_b3_s1_populations.py [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STRATUM = "work/stage3/b3/comprehension/stratum-v0.json"
DRYRUN = "work/stage3/b3/inserter-dry-run-v0.json"
OUT = "work/stage3/b3/s1-populations-v0.json"
SHA = {STRATUM: "6113bd8d4cd16768c5cfc83a2db3a109b2a0e0a81403341a88361787f3ca9932",
       DRYRUN: "edd289ce14eae1be6d131562600b482539d0f7f3903fcdb33e524565c15af5e8"}
VERSION = "b3-s1-populations/v0"
POOL_MIN = 4          # A6.17.3: documents with fewer than four members pool into one stratum
CERT_BAR = 75.0       # A6.2 and its wording note: mean composition at or above 75
CANDIDATE_POPS = ("full", "stratum", "subset", "strict", "subset_and_strict", "certified",
                  "preview_credited", "preview_illegible", "unresolved_stratum")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ids_sha256(ids: Iterable[str]) -> str:
    """Brief 25's convention: the sorted ids, newline-joined, sha256."""
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()


def _zero(values) -> bool:
    return [float(v) for v in values] == [0.0, 0.0]


def is_strict(r: Mapping[str, Any]) -> bool:
    """A6.17.1: Kimi K3 and Sol both at D_part 0 on both samples."""
    return r["membership"] == "quiet" and _zero(r["readers"]["kimi"]["D_part"]) and _zero(r["readers"]["sol"]["D_part"])


def whole_credited_both(r: Mapping[str, Any]) -> bool:
    """A6.17.5's first arm: the whole credited under both readers on any sample."""
    return all(any(float(v) > 0 for v in r["readers"][k]["D_whole"]) for k in ("kimi", "sol"))


def whole_never_credited(r: Mapping[str, Any]) -> bool:
    """A6.17.5's second arm: the whole credited on no sample under either reader."""
    return all(float(v) == 0 for k in ("kimi", "sol") for v in r["readers"][k]["D_whole"])


def gross_populations(items: Mapping[str, Mapping[str, Any]]) -> dict[str, list[str]]:
    cand = {i: r for i, r in items.items() if r["regime"] == "candidate"}
    stratum = {i for i, r in cand.items() if r["membership"] == "quiet"}
    strict = {i for i, r in cand.items() if is_strict(r)}
    subset = {i for i in stratum if cand[i]["anchors_resolve"]}
    pops = {"full": set(cand), "stratum": stratum, "subset": subset, "strict": strict,
            "subset_and_strict": subset & strict,
            "certified": {i for i, r in cand.items() if float(r["composition"]) >= CERT_BAR},
            "preview_credited": {i for i in stratum if whole_credited_both(cand[i])},
            "preview_illegible": {i for i in stratum if whole_never_credited(cand[i])},
            "unresolved_stratum": stratum - subset,
            "controls": {i for i, r in items.items() if r["regime"] == "control"},
            "sham": {i for i, r in items.items() if r["regime"] == "sham"}}
    return {k: sorted(v) for k, v in pops.items()}


def pooled_strata(docs: list[str], pool_min: int = POOL_MIN) -> list[int]:
    """A6.17.3: stratum sizes after every document with fewer than pool_min members is merged into one stratum."""
    c = Counter(docs)
    s = Counter(d if c[d] >= pool_min else "\0pooled" for d in docs)
    return sorted(s.values(), reverse=True)


def _two_by_different_authors(draws: list[tuple[str, str]], different_days: bool) -> bool:
    return any(a1 != a2 and (d1 != d2 or not different_days)
               for k, (d1, a1) in enumerate(draws) for (d2, a2) in draws[k + 1:])


def lone_line_feasibility(dry: Mapping[str, Any], drops: set[str]) -> dict[str, Any]:
    """S1's lone-line rule against brief 26's valid draws, enumerated over every item pair the pair rule can draw
    (two valid item draws on different days by different authors), no draw computed: does each net candidate's lone
    line keep two valid draws by different authors once both of the pair's authors are excluded (A6.5 (iii), 'not the
    triple's author')? Beside: the same with different days also required."""
    n_lines = by_authors = after_excl = after_excl_days = cases = cases_short_days = 0
    for it in dry["items"]:
        if it["regime"] != "candidate" or it["item_id"] in drops:
            continue
        ip = [tuple(x) for x in it["draws"]["valid_draws"]]
        pairs = [(p, q) for k, p in enumerate(ip) for q in ip[k + 1:] if p[0] != q[0] and p[1] != q[1]]
        for line in it["lone_lines"]:
            dr = [tuple(x) for x in line["valid_draws"]]
            n_lines += 1
            by_authors += _two_by_different_authors(dr, False)
            ok = [_two_by_different_authors([x for x in dr if x[1] not in (p[1], q[1])], False) for p, q in pairs]
            okd = [_two_by_different_authors([x for x in dr if x[1] not in (p[1], q[1])], True) for p, q in pairs]
            after_excl += all(ok)
            after_excl_days += all(okd)
            cases += len(pairs)
            cases_short_days += sum(not x for x in okd)
    return {"net_candidate_lines": n_lines, "two_valid_by_different_authors": by_authors,
            "every_item_pair_leaves_two_by_different_authors": after_excl,
            "beside_every_item_pair_leaves_two_on_different_days_by_different_authors": after_excl_days,
            "beside_item_pair_cases": cases, "beside_item_pair_cases_short_with_different_days": cases_short_days}


def describe(ids: list[str], items: Mapping[str, Mapping[str, Any]], rated: bool) -> dict[str, Any]:
    rec = [items[i] for i in ids]
    docs = [r["document"] for r in rec]
    out: dict[str, Any] = {"n": len(ids), "ids_sha256": ids_sha256(ids), "ids": ids,
                           "by_writer": dict(sorted(Counter(r["writer"] for r in rec).items())),
                           "n_documents": len(set(docs)),
                           "document_counts": sorted(Counter(docs).values(), reverse=True),
                           "strata_pooled": pooled_strata(docs)}
    comp = [r.get("composition") for r in rec]
    if rated and ids and all(c is not None for c in comp):
        c = np.array(comp, dtype=float)
        out["composition"] = {"mean": float(c.mean()), "sd": float(c.std(ddof=1)) if len(c) > 1 else None,
                              "iqr": [float(np.quantile(c, .25)), float(np.quantile(c, .75))]}
    return out


def build(root: Path = ROOT) -> dict[str, Any]:
    for rel, want in SHA.items():
        got = sha256_file(root / rel)
        if got != want:
            raise SystemExit(f"{rel}: sha256 {got[:8]} is not the pinned {want[:8]}")
    st = json.loads((root / STRATUM).read_text())
    dry = json.loads((root / DRYRUN).read_text())
    items = st["items"]
    if sorted(d["item_id"] for d in dry["items"]) != sorted(items):
        raise SystemExit("brief 26's items and brief 25's items differ")
    gross = gross_populations(items)
    if gross["stratum"] != sorted(st["stratum"]["ids"]) or ids_sha256(gross["stratum"]) != st["stratum"]["ids_sha256"]:
        raise SystemExit("the stratum does not reproduce brief 25's ids")
    # brief 26's population labels against the ones derived here
    labels = {"78": "full", "28": "stratum", "19": "subset", "21": "strict"}
    for d in dry["items"]:
        for lab in d["populations"]:
            if lab in labels and d["item_id"] not in gross[labels[lab]]:
                raise SystemExit(f"population {lab} of brief 26 is not {labels[lab]} here")
    drops = {"pair": sorted(dry["drop_list"]["ids"]), "literal": sorted(dry["drop_list"]["ids_literal"])}
    out: dict[str, Any] = {"version": VERSION, "brief": "28 v2.1", "inputs_sha256": dict(SHA),
                           "conventions": {"ids_sha256": "sha256 of the sorted ids joined by newlines (brief 25)",
                                           "composition": "the two-pass mean (A6.2); SD ddof 1; IQR by linear interpolation (A6.11 (4))",
                                           "pooled_strata": f"documents with fewer than {POOL_MIN} members pool into one stratum (A6.17.3)",
                                           "certified": f"mean composition at or above {CERT_BAR:g} (A6.2 wording note)",
                                           "strict": "Kimi K3 and Sol both at D_part 0 on both samples (A6.17.1)",
                                           "preview": "A6.17.5: whole credited under both readers on any sample, against no sample under either"},
                           "drops": {}, "populations": {}}
    for rule, ids in drops.items():
        out["drops"][rule] = {"n": len(ids), "ids_sha256": ids_sha256(ids), "ids": ids,
                              "by_regime": dict(sorted(Counter(items[i]["regime"] for i in ids).items()))}
    for name, ids in gross.items():
        rated = name in CANDIDATE_POPS or name == "controls"
        out["populations"][name] = {"gross": describe(ids, items, rated)}
        for rule, dl in drops.items():
            kept = [i for i in ids if i not in set(dl)]
            out["populations"][name]["net_" + rule] = describe(kept, items, rated)
    out["lone_lines"] = lone_line_feasibility(dry, set(drops["pair"]))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT)
    ns = ap.parse_args(argv)
    res = build()
    text = json.dumps(res, indent=1, sort_keys=False) + "\n"
    out = ROOT / ns.out
    out.write_text(text)
    print(f"wrote {ns.out} sha256 {hashlib.sha256(text.encode()).hexdigest()}")
    for name, p in res["populations"].items():
        g, n, l = p["gross"], p["net_pair"], p["net_literal"]
        print(f"  {name}: gross {g['n']} ({g['ids_sha256'][:8]}), net {n['n']} ({n['ids_sha256'][:8]}), "
              f"literal {l['n']} ({l['ids_sha256'][:8]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
