#!/usr/bin/env python3
"""The day-1 instrument stop of `prefix_rw_v2` (brief 07e E5; lesson L11: an instrument look with
a threshold written before the run). Read at the day-1 boundary, on day 1's rows only:

  * writes per class document: successful ownCloud content writes (write_file, append_to_file,
    replace_in_file) on each of the six class paths;
  * empty writes and deletes that REACHED a path under /shared/ (successful rows; a retention
    refusal is a failed row and is counted beside as `refusals`).

Decision: STOP (exit 2) if any class document has fewer than THREE writes, or any empty write or
delete reached a shared document; otherwise CONTINUE (exit 0). Exit 1 on an error. The supervisor
kills the runner at the boundary on exit 2 and the brief returns to E3 with the numbers.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_day1_stop.py \\
        --corpus <abs>/data/corpus/spike/prefix_rw_v2.jsonl --day 2026-04-06 --out-json <path>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_rung1_class as rc  # noqa: E402

BAR_WRITES = 3
SHARED = "/shared"


def _shared(path: Any) -> bool:
    p = ("/" + str(path or "").strip().lstrip("/")).rstrip("/")
    return p == SHARED or p.startswith(SHARED + "/")


def decide(rows: Sequence[dict[str, Any]], day: str) -> dict[str, Any]:
    writes = {p: 0 for p in rc.DOC_PATHS}
    by_action: dict[str, int] = {}
    empties = deletes = refusals = 0
    empty_paths: list[str] = []
    deleted_paths: list[str] = []
    n_rows = 0
    for r in rows:
        if str(r.get("ts") or "")[:10] != day:
            continue
        n_rows += 1
        if r.get("service") != "owncloud":
            continue
        path = (r.get("args") or {}).get("path")
        if (r.get("exit_code") or 0) != 0:
            if str(r.get("error") or "").startswith(rc.REFUSAL_PREFIX):
                refusals += 1
            continue
        cp = rc._class_path(r)
        if cp is not None and r.get("action") in rc.CLASS_WRITE_ACTIONS:
            writes[cp] += 1
            by_action[r["action"]] = by_action.get(r["action"], 0) + 1
        if _shared(path):
            if r.get("action") in rc.CLASS_WRITE_ACTIONS and not str((r.get("args") or {}).get("content") or ""):
                empties += 1
                empty_paths.append(str(path))
            elif r.get("action") == "delete":
                deletes += 1
                deleted_paths.append(str(path))
    thin = [p for p in rc.DOC_PATHS if writes[p] < BAR_WRITES]
    stop = bool(thin) or empties > 0 or deletes > 0
    return {"day": day, "rows_on_day": n_rows, "writes_per_document": writes,
            "writes_by_action": by_action, "bar_writes": BAR_WRITES, "thin_documents": thin,
            "empty_writes": empties, "empty_write_paths": empty_paths,
            "deletes": deletes, "deleted_paths": deleted_paths, "refusals": refusals,
            "decision": "STOP" if stop else "CONTINUE",
            "reason": ("; ".join(([f"fewer than {BAR_WRITES} writes on {thin}"] if thin else [])
                                 + ([f"{empties} empty write(s) reached /shared/"] if empties else [])
                                 + ([f"{deletes} delete(s) reached /shared/"] if deletes else []))
                       or "every document >= 3 writes; no empty write or delete on /shared/")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--day", required=True)
    ap.add_argument("--out-json", default=None)
    ns = ap.parse_args(argv)
    rows = []
    with open(ns.corpus, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    v = decide(rows, ns.day)
    v["corpus"] = ns.corpus
    print(f"DAY-1 INSTRUMENT STOP {v['decision']}: {v['reason']}; writes per document "
          f"{ {p.split('/')[-1]: n for p, n in v['writes_per_document'].items()} } by action {v['writes_by_action']}; "
          f"empty writes on /shared/ {v['empty_writes']}; deletes on /shared/ {v['deletes']}; refusals {v['refusals']}")
    if ns.out_json:
        Path(ns.out_json).write_text(json.dumps(v, indent=1), encoding="utf-8")
    return 2 if v["decision"] == "STOP" else 0


if __name__ == "__main__":
    raise SystemExit(main())
