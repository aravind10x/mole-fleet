#!/usr/bin/env python3
"""Brief 30 Part 3: the development feedback of the certification protocol (section 2), in the layout of the writer
packet's section 8. Blue side; pure; reads no file except through the functions that name one.

A writer sees, for its own items only: whether each was valid (and the failed check classes), the development rater's
rating of each statement and whether it is within target, and how often two development readers recovered the composed
effect from the whole and from each statement alone. It never sees a composition score, a certification figure, a class,
another writer's item, or the name of a reader or model.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

VERSION = "elicitation-feedback/v0"
WITHIN_TARGET_MAX = 60.0


def build_results(skeleton: Mapping[str, Any], key: Mapping[str, Any], statement_means: Mapping[str, Sequence[float]],
                  collected: Mapping[str, Mapping[str, Any]], fams: Sequence[str]) -> dict:
    """skeleton: the converter's results-mechanical.json; key: its key.json; statement_means: {item_id: [rating by the
    writer's own statement index]} from the development rater; collected: the development reads' per-item, per-reader
    statistics (sample 0's `cond_scores`); fams: (colleague_a's reader, colleague_b's reader)."""
    by_writer_id = {e["writer_id"]: (tid, e) for tid, e in key["triples"].items()}
    out = []
    for r in skeleton["results"]:
        r = json.loads(json.dumps(r))     # a copy
        if r["valid"] and r["id"] in by_writer_id:
            tid, e = by_writer_id[r["id"]]
            means = statement_means[tid]
            for st in r["statements"]:
                i = st["index"]
                st["rating"] = float(means[i])
                st["within_target"] = bool(means[i] <= WITHIN_TARGET_MAX)
            order = e["document_order"]               # document position j holds the writer's statement order[j]
            for name, fam in zip(("colleague_a", "colleague_b"), fams):
                cs = collected[tid][fam]["cond_scores"][0]
                parts: list[float | None] = [None] * len(order)
                for j, writer_index in enumerate(order):
                    parts[writer_index] = cs[f"part{j}"]
                r["recovery"][name] = {"whole": cs["whole"], "parts": parts}
        out.append(r)
    return {"results": out}


def write_previous(dest: Path, answer_file: Path, results: Mapping[str, Any]) -> Path:
    """The `previous/` folder the harness takes for the writer's next round: its own items as it wrote them, unchanged,
    and the results above; nothing else."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "items.json").write_bytes(Path(answer_file).read_bytes())
    (dest / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return dest


def main(argv: Sequence[str] | None = None) -> int:
    """`build`: the writer's `previous/` for its next round from the converted round, the development rater's validated
    ratings and the development reads' collected statistics (all under part3/)."""
    import argparse
    import sys
    HERE = Path(__file__).resolve().parent
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import stage3_elicitation_classes as cl
    import stage3_elicitation_raters as rt
    import stage3_elicitation_reads as rd
    ap = argparse.ArgumentParser(description="brief 30 Part 3: development feedback")
    ap.add_argument("--writer", required=True)
    ap.add_argument("--round", type=int, required=True)
    ns = ap.parse_args(argv)
    P = rt.PART3
    conv = P / f"round-{ns.round}" / ns.writer / "converted"
    O = P / "raters" / f"{ns.writer}-r{ns.round}-dev"
    key = json.loads((conv / "key.json").read_text(encoding="utf-8"))
    skeleton = json.loads((conv / "results-mechanical.json").read_text(encoding="utf-8"))
    skey = json.loads((O / "statement-key.json").read_text(encoding="utf-8"))
    scores = json.loads((O / "collected" / "ratings-dev-statements-p1.json").read_text(encoding="utf-8"))
    means = rt.single_session_means(scores, skey)
    collected = json.loads((rd.phase_dir(rd.READS_ROOT, ns.writer, ns.round, "dev") / "collected.json").read_text(encoding="utf-8"))
    res = build_results(skeleton, key, means, collected, rd.reader_names(ns.writer))
    out = write_previous(P / f"round-{ns.round}" / ns.writer / "feedback" / "previous", P / "writers" / f"{ns.writer}-r{ns.round}" / "answer.json", res)
    n_valid = sum(1 for r in res["results"] if r["valid"])
    print(json.dumps({"results": len(res["results"]), "valid": n_valid, "previous": str(out.relative_to(P))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
