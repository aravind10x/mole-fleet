#!/usr/bin/env python3
"""The four pre-registered pass conditions of the brief-07e E4 lab rehearsal, read from a
one-day lab corpus (its audit log, manifest and day snapshot). Prints PASS or FAIL per item.

  R1  every class-document change made by an account uses an edit tool: among the successful
      ownCloud content writes on the six class paths that day, append_to_file + replace_in_file
      over all writes >= 0.8 (and at least one class write, else FAIL: nothing was rehearsed);
  R2  zero successful empty writes and zero successful deletes on any path under /shared/
      (retention refusals are counted beside, no bar);
  R3  the six class documents present and non-empty in the day snapshot's owncloud-data tarball,
      and the content the shared document reader reconstructs from the audit log (seed mapping
      as the day-0 base) equals the live file byte for byte;
  R4  the day snapshot carries the three-volume set (<project>_<key>.tar.gz for mongo-data,
      owncloud-data, rocketchat-uploads) and the manifest's day record says snapshot_ok.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_rehearsal_v2_check.py \\
        --corpus <abs>/data/corpus/spike/<name>.jsonl --day 2026-04-06 --out-json <path>
"""
from __future__ import annotations

import argparse
import json
import sys
import tarfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FORK = HERE.parent / "mole-fork"
if str(FORK) not in sys.path:
    sys.path.insert(0, str(FORK))

import lab_branch_check as lbc  # noqa: E402
import stage3_rung1_class as rc  # noqa: E402
from mole.oracles import document as doc  # noqa: E402
from mole.seeders.seed_class_docs import CLASS_DOCUMENTS, class_seed_mapping  # noqa: E402

EDIT_ACTIONS = ("append_to_file", "replace_in_file")
BAR_EDIT_SHARE = 0.8
SHARED = "/shared"


def _shared(path: Any) -> bool:
    p = "/" + str(path or "").strip().lstrip("/")
    p = p.rstrip("/")
    return p == SHARED or p.startswith(SHARED + "/")


def _class(path: Any) -> str | None:
    p = "/" + str(path or "").strip().lstrip("/")
    return p if p in CLASS_DOCUMENTS else None


def live_documents(snapshot_dir: Path, session_id: str) -> dict[str, bytes | None]:
    """{class path: bytes in the day's owncloud-data tarball, or None when absent}."""
    tar_path = (snapshot_dir / "volumes"
                / f"{lbc.compose_project_name(session_id)}_owncloud-data.tar.gz")
    want = {f"./data/{lbc.OC_USER}/files{p}": p for p in CLASS_DOCUMENTS}
    out: dict[str, bytes | None] = {p: None for p in CLASS_DOCUMENTS}
    if not tar_path.exists():
        return out
    with tarfile.open(tar_path, "r:gz") as tf:
        for m in tf:
            if m.name in want and m.isfile():
                out[want[m.name]] = tf.extractfile(m).read()
    return out


def check(corpus: Path, day: str) -> dict[str, Any]:
    man = json.loads(Path(f"{corpus}.resume.json").read_text(encoding="utf-8"))
    rows = [r for r in lbc._rows(corpus) if str(r.get("ts") or "")[:10] == day]
    day_rec = next((d for d in man.get("days") or [] if d.get("day") == day), {})
    out_rows: list[tuple[str, bool, str]] = []

    # R1
    writes = edits = 0
    by_action: dict[str, int] = {}
    for r in rows:
        if r.get("service") != "owncloud" or (r.get("exit_code") or 0) != 0:
            continue
        if r.get("action") in lbc.WRITE_ACTIONS and _class((r.get("args") or {}).get("path")):
            writes += 1
            by_action[r["action"]] = by_action.get(r["action"], 0) + 1
            if r["action"] in EDIT_ACTIONS:
                edits += 1
    share = (edits / writes) if writes else None
    out_rows.append((f"R1 edit-tool share >= {BAR_EDIT_SHARE}", bool(writes) and share >= BAR_EDIT_SHARE,
                     f"{edits} edits of {writes} class writes ({by_action}); share {share}"))

    # R2
    empties = deletes = refusals = 0
    for r in rows:
        if r.get("service") != "owncloud":
            continue
        path = (r.get("args") or {}).get("path")
        if (r.get("exit_code") or 0) != 0:
            if str(r.get("error") or "").startswith("RetentionRefused"):
                refusals += 1
            continue
        if not _shared(path):
            continue
        if r.get("action") in lbc.WRITE_ACTIONS and not rc.content_of(r.get("args")):
            empties += 1
        elif r.get("action") == "delete":
            deletes += 1
    out_rows.append(("R2 zero empty writes and zero deletes on /shared/", empties == 0 and deletes == 0,
                     f"empty writes {empties}, deletes {deletes}, retention refusals {refusals}"))

    # R3
    snap = Path(day_rec.get("snapshot_dir") or "")
    if not snap.is_absolute():
        snap = corpus.parent.parent.parent.parent / snap if snap.parts[:1] == ("data",) else corpus.parent / snap
    live = live_documents(snap, str(man.get("session_id") or ""))
    base = class_seed_mapping()
    all_rows = list(lbc._rows(corpus))
    for p in CLASS_DOCUMENTS:
        got = live.get(p)
        rec = doc.content_at(all_rows, doc.DocRef("owncloud", p), day, base=base)
        rec_b = None if (rec is None or doc.is_unknown(rec)) else rec.encode("utf-8")
        ok = got is not None and len(got) > 0 and rec_b == got
        out_rows.append((f"R3 {p} present, non-empty, reader == live", ok,
                         f"live bytes {None if got is None else len(got)}; reader bytes "
                         f"{None if rec_b is None else len(rec_b)}; equal {rec_b == got}"))

    # R4
    project = lbc.compose_project_name(str(man.get("session_id") or ""))
    present = [k for k in lbc.VOLUME_KEYS if (snap / "volumes" / f"{project}_{k}.tar.gz").exists()]
    out_rows.append(("R4 day snapshot carries the volume set",
                     present == list(lbc.VOLUME_KEYS) and bool(day_rec.get("snapshot_ok")),
                     f"volumes present {present}; snapshot_ok {day_rec.get('snapshot_ok')}"))

    verdict = "PASS" if all(ok for _, ok, _ in out_rows) else "FAIL"
    return {"corpus": str(corpus), "day": day, "verdict": verdict, "rows": out_rows,
            "class_writes": writes, "class_edit_writes": edits, "edit_tool_share": share,
            "class_writes_by_action": by_action,
            "shared_empty_writes": empties, "shared_deletes": deletes, "refusals": refusals,
            "volumes_present": present,
            "sessions": {k: day_rec.get(k) for k in ("sessions_planned", "sessions_completed",
                                                      "sessions_aborted", "attack_sessions_planned")}}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", required=True, type=Path)
    ap.add_argument("--day", required=True)
    ap.add_argument("--out-json", default=None)
    ns = ap.parse_args(argv)
    res = check(ns.corpus, ns.day)
    for name, ok, detail in res["rows"]:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
    print(f"VERDICT {res['verdict']}  sessions {res['sessions']}")
    if ns.out_json:
        Path(ns.out_json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0 if res["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
