#!/usr/bin/env python3
"""Runner for the pinned SS negative-audit join (`stage3_ss_neg.py` b1e282ba, unchanged). Red's Part F table names a
control's shown form `control_form` and the second pass `pass2_agreement`; this adapter renames those two fields to the
module's `form` and `consistency`, and changes nothing else. Hash-checked inputs; writes a new file."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

PINNED = "b1e282ba1ff24c5aefedb28f421fc4620202e4667b7e31098f52e3bb6dd5790b"


def adapt(table: Any) -> tuple[list[dict], Any]:
    rows = table["runs"] if isinstance(table, dict) else table
    out = []
    for r in rows:
        r2 = {k: v for k, v in r.items() if k != "control_form"}
        if r.get("control_form") is not None:
            r2["form"] = r["control_form"]
        out.append(r2)
    return out, (table.get("pass2_agreement", table.get("consistency")) if isinstance(table, dict) else None)


def main(argv: list[str] | None = None) -> int:
    import stage3_ft_run as fr
    import stage3_ss_neg as sn
    S5 = HERE.parent / "stage3" / "v5" / "SS"
    ap = argparse.ArgumentParser(description="Run the pinned SS negative-audit join on red's tables.")
    ap.add_argument("--neg-table", type=Path, required=True)
    ap.add_argument("--expect-neg-sha256", required=True)
    ap.add_argument("--display-table", type=Path)
    ap.add_argument("--expect-display-sha256")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if hashlib.sha256((HERE / "stage3_ss_neg.py").read_bytes()).hexdigest() != PINNED:
        raise SystemExit("refusing: stage3_ss_neg.py is not the pinned module")
    if a.out.exists():
        raise SystemExit(f"{a.out} exists; never overwritten")
    for path, want in ((a.neg_table, a.expect_neg_sha256), (a.display_table, a.expect_display_sha256)):
        if path is not None and hashlib.sha256(path.read_bytes()).hexdigest() != want:
            raise SystemExit(f"refusing: {path.name} is not the file of record")
    rows, p2 = adapt(json.loads(a.neg_table.read_text(encoding="utf-8")))
    disp = None
    if a.display_table:
        dt = json.loads(a.display_table.read_text(encoding="utf-8"))
        disp = dt["runs"] if isinstance(dt, dict) else dt
    outs = [json.loads(x) for x in (S5 / "outcomes-SS-v0.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    pos = json.loads((S5 / "audit-table-SS.json").read_text(encoding="utf-8"))
    res = sn.analyse_neg(outs, fr.load_manifest(fr.RED_FT / "cells-manifest.json"), pos, rows, display_rows=disp)
    res["pass_two"] = p2
    if disp is None:
        res["sentence_status"] = "pending the display check"
    a.out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"sentence": res["sentence"], "status": res.get("sentence_status", "final")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
