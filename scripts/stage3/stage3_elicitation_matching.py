#!/usr/bin/env python3
"""Brief 30 Part 3 (dated notes 7 and 8): round 2's matching rule, fixed before writer round 1, and its $0
dry run on synthetic strata. Blue side; standard library only; reads no file and no item.

The rule (reconcile-part2-trigger-2026-11-03.md section 4, item 4; plan.md section 8): many-to-one within
writer x document x composition band. Every certified item in a stratum that holds a quiet-but-illegible item
is used and the certified arm is never cut to the comparison arm's size; a quiet-but-illegible item in a
stratum with no certified item has no match and is dropped, and so is a certified item in a stratum with no
quiet-but-illegible item. The effective n is 2 / (1/n_c + 1/n_i) on the matched strata. Items of the other
four classes join neither arm. The band is a half-open interval of `width` points on the 0 to 100
composition scale (gate (i)'s two-session mean), the top band closed at 100.

The dry run uses invented strata: composition drawn from a clipped normal (spread 17.3, the stratum spread of
plan section 8; mean an assumption), writers and documents assigned at random, classes assigned by count. It
touches no B3 item, score or result and the simulator's world loader (which opens the B3 candidates) is not
imported.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_matching.py dry-run --out FILE.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

VERSION = "elicitation-matching/v0"
SEED = 20261214  # unused by any earlier brief or script (checked by grep, 2026-11-07)
CERTIFIED = "certified"
ILLEGIBLE = "quiet_but_illegible"
CLASSES = ("loud", "not_evaluable", "part_derivable", CERTIFIED, ILLEGIBLE, "mixed")
SCALE = 100.0
BAND_WIDTH = 10.0           # note 7, item 4: the coordinator's width; it moves only by dated note
COMP_SD = 17.3              # plan.md section 8: the stratum's composition spread
COMP_MEAN = 50.0            # an assumption of the dry run, not a measurement
SCENARIOS = ((26, 12), (40, 16), (58, 21), (72, 17))  # certified, illegible: target and the reconcile table's medians
WIDTHS = (5, 10, 20, 25)


def band_index(composition: float, width: float) -> int:
    if not (isinstance(width, (int, float)) and width > 0 and abs(SCALE / width - round(SCALE / width)) < 1e-9):
        raise ValueError(f"a band width must tile the 0 to 100 scale, got {width!r}")
    if not (isinstance(composition, (int, float)) and 0.0 <= composition <= SCALE):
        raise ValueError(f"a composition score must lie on 0 to 100, got {composition!r}")
    n = int(round(SCALE / width))
    return min(int(composition // width), n - 1)


def effective_n(n_c: int, n_i: int) -> float:
    if n_c <= 0 or n_i <= 0:
        return 0.0
    return 2.0 / (1.0 / n_c + 1.0 / n_i)


def match(items: Iterable[Mapping[str, Any]], width: float = BAND_WIDTH) -> dict:
    """items: mappings with `writer`, `document`, `composition` and `class`. Returns the matched counts."""
    cells: dict[tuple, list[int]] = defaultdict(lambda: [0, 0])
    for item in items:
        cls = item["class"]
        if cls not in CLASSES:
            raise ValueError(f"unknown class {cls!r}")
        if cls not in (CERTIFIED, ILLEGIBLE):
            continue
        key = (item["writer"], item["document"], band_index(item["composition"], width))
        cells[key][0 if cls == CERTIFIED else 1] += 1
    c_total = sum(c for c, _ in cells.values())
    i_total = sum(i for _, i in cells.values())
    used = [(c, i) for c, i in cells.values() if c > 0 and i > 0]
    n_c = sum(c for c, _ in used)
    n_i = sum(i for _, i in used)
    return {"n_c": n_c, "n_i": n_i, "n_c_total": c_total, "n_i_total": i_total, "strata_used": len(used),
            "unmatched_certified": c_total - n_c, "unmatched_illegible": i_total - n_i,
            "n_eff": effective_n(n_c, n_i), "width": width}


def _synthetic(rng: random.Random, n_c: int, n_i: int, writers: int, documents: int, mean: float, sd: float) -> list[dict]:
    items = []
    for k in range(n_c + n_i):
        comp = min(SCALE, max(0.0, rng.gauss(mean, sd)))
        items.append({"writer": f"w{k % writers}", "document": f"d{rng.randrange(documents)}", "composition": comp,
                      "class": CERTIFIED if k < n_c else ILLEGIBLE})
    return items


def _rank(sorted_vals: Sequence[float], q: float) -> float:
    return sorted_vals[min(len(sorted_vals) - 1, max(0, int(math.ceil(q * len(sorted_vals))) - 1))]


def dry_run(seed: int = SEED, reps: int = 2000, scenarios: Sequence[tuple[int, int]] = SCENARIOS,
            widths: Sequence[float] = WIDTHS, writers: int = 2, documents: int = 6,
            mean: float = COMP_MEAN, sd: float = COMP_SD) -> dict:
    rows = []
    for (n_c, n_i) in scenarios:
        for width in widths:
            rng = random.Random(f"{seed}/{n_c}/{n_i}/{width}")
            neffs, rc, ri, zero = [], 0.0, 0.0, 0
            for _ in range(reps):
                m = match(_synthetic(rng, n_c, n_i, writers, documents, mean, sd), width)
                neffs.append(m["n_eff"])
                rc += m["n_c"] / n_c
                ri += m["n_i"] / n_i
                zero += m["strata_used"] == 0
            s = sorted(neffs)
            rows.append({"n_certified": n_c, "n_illegible": n_i, "width": width,
                         "retained_certified": round(rc / reps, 6), "retained_illegible": round(ri / reps, 6),
                         "n_eff_mean": round(sum(neffs) / reps, 6), "n_eff_p10": round(_rank(s, 0.10), 6),
                         "n_eff_p90": round(_rank(s, 0.90), 6),
                         "share_with_no_matched_stratum": round(zero / reps, 6),
                         "n_eff_unmatched_ceiling": round(effective_n(n_c, n_i), 6)})
    return {"version": VERSION, "seed": seed, "reps": reps, "writers": writers, "documents": documents,
            "composition": {"mean": mean, "sd": sd, "clipped_to": [0, 100], "mean_is": "an assumption",
                            "sd_is": "plan.md section 8's stratum spread"},
            "rule": "many-to-one within writer x document x composition band; certified arm never cut; n_eff harmonic",
            "rows": rows}


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, indent=1, ensure_ascii=False) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dry-run")
    d.add_argument("--out", required=True)
    d.add_argument("--reps", type=int, default=2000)
    d.add_argument("--writers", type=int, default=2)
    d.add_argument("--documents", type=int, default=6)
    d.add_argument("--sd", type=float, default=COMP_SD)
    d.add_argument("--mean", type=float, default=COMP_MEAN)
    a = ap.parse_args(argv)
    res = dry_run(reps=a.reps, writers=a.writers, documents=a.documents, sd=a.sd, mean=a.mean)
    Path(a.out).write_text(canonical(res), encoding="utf-8")
    print(f"wrote {a.out}: {len(res['rows'])} rows, seed {res['seed']}, reps {res['reps']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
