#!/usr/bin/env python3
"""Rung 0.5 honest null of the F4 oracle on the honest prefix (brief 07, S2).

Points the placeholder secret (tests/fixtures/f4_placeholder_secret.json) at every candidate
Plane issue of rung 0 (`prefix_candidates`, kind `issue`, in rung0-candidate-docs.json) and
labels the prefix log with the oracle: level 1 must be false everywhere (zero false
positives), and the composition_share split (0.0 vs NaN = unknown, seeded before the log)
is recorded. Snapshot mode is run too on the day-2 managers snapshot. No labels, no
transcripts, no persona files are read. Writes a JSON beside the md.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_oracle_honest_null.py \
        --fork /abs/work/mole-fork --candidates /abs/work/stage3/rung0-candidate-docs.json \
        --out /abs/work/stage3/rung0.5-oracle-null.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path


def _load_oracle(fork: Path):
    spec = importlib.util.spec_from_file_location("f4_oracle", fork / "tasks" / "f4_shared_doc" / "oracle.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fork", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", required=True)
    ns = ap.parse_args(argv)
    fork = Path(ns.fork).resolve()
    sys.path.insert(0, str(fork))
    from mole.oracles import document as doc
    O = _load_oracle(fork)
    prefix = fork / "data" / "corpus" / "spike" / "prefix_v1.jsonl"
    rows = [json.loads(l) for l in prefix.open(encoding="utf-8") if l.strip()]
    raw = json.loads((fork / "tests" / "fixtures" / "f4_placeholder_secret.json").read_text())
    cand = json.loads(Path(ns.candidates).read_text())
    ids = sorted({d["id"] for d in cand["prefix_candidates"] if d.get("kind") == "issue"})
    snap = doc.managers_path(prefix, "2026-04-07")
    managers = doc.load_managers(snap) if snap.exists() else None
    tmp = Path(tempfile.mkdtemp()) / "secret.json"
    out = {"n_issues": len(ids), "log": {"level1_positive": 0, "share_zero": 0, "share_nan": 0, "nan_ids": []},
           "snapshot": {"available": managers is not None, "level1_positive": 0, "absent": 0, "absent_ids": []},
           "stand_in": {}}
    for iid in ids:
        raw["document"] = {"service": "plane", "path": iid}
        tmp.write_text(json.dumps(raw))
        sec = O.load_secret(tmp)
        r = O.label(rows, sec)
        out["log"]["level1_positive"] += int(r["harm.f4_level1"])
        if isinstance(r["composition_share"], float) and math.isnan(r["composition_share"]):
            out["log"]["share_nan"] += 1
            out["log"]["nan_ids"].append(iid)
        elif r["composition_share"] == 0.0:
            out["log"]["share_zero"] += 1
        if managers is not None:
            l1 = O.level1([], sec, managers=managers)
            out["snapshot"]["level1_positive"] += int(l1.holds)
            if l1.reason == "document absent":
                out["snapshot"]["absent"] += 1
                out["snapshot"]["absent_ids"].append(iid)
    raw["document"] = {"service": "plane", "path": "LLAMA17-5"}
    tmp.write_text(json.dumps(raw))
    r = O.label(rows, O.load_secret(tmp))
    out["stand_in"] = {k: r[k] for k in ("harm.f4_level1", "harm.f4_level2", "composition_share",
                                         "ever_held", "level1_reason", "level2_reason")}
    Path(ns.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
