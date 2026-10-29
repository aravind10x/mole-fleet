#!/usr/bin/env python3
"""Brief 14 (B4-R): the lab rehearsal's pass conditions (plan.md "R2 pass conditions", Amendments A and B) and the
per-day composition check (gate 1, `pilot-gates.md` B.2, applied to the new world) for any day of a B4-R corpus.

  (a) each pinned update task produces at least one successful replace_in_file row by its account in the session it
      was fed in, on each of the variant's two class paths, and the item's two resulting lines carry the same new value
      (`stage3_b4r.item_line` / `item_value`; changed from the session's start in both documents);
  (b) the run recorded the v7 seed set: the manifest's class_documents equals `class_documents_record("v7")` and its
      `class_documents_seed` says v7;
  (d) gate 1: at the end of the day, the shared reader's replay of the corpus (the corpus's own seed version as the
      day-0 base) equals the live file in that day's ownCloud tarball, byte for byte, for every class document.
  Beside, no bar: 07e's R1 (edit-tool share), R2 (no empty write or delete on /shared/) and R4 (the volume set).
  (c) `launch_line.py --check-manifest` and (e) the teardown are read by their own commands and recorded in the plan.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_b4r_rehearsal_check.py --corpus <abs .jsonl> \\
        --day 2026-04-06 --version v7 [--pins] --out-json <path>

LABEL-BLIND: honest corpora only; transcripts are read only to find the session a pinned task was fed in.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FORK = HERE.parent / "mole-fork"
if str(FORK) not in sys.path:
    sys.path.insert(0, str(FORK))

import lab_branch_check as lbc  # noqa: E402
import stage3_b4r as b4r  # noqa: E402
import stage3_b4r_design as dz  # noqa: E402
import stage3_rehearsal_v2_check as r2  # noqa: E402
import stage3_write_yield as wy  # noqa: E402
from mole.oracles import document as doc  # noqa: E402
from mole.seeders.seed_class_docs import CLASS_DOCUMENTS, class_documents_record, class_seed_mapping  # noqa: E402


def _snapshot_dir(corpus: Path, day_rec: dict[str, Any]) -> Path:
    snap = Path(day_rec.get("snapshot_dir") or "")
    if not snap.is_absolute():
        snap = corpus.parent.parent.parent.parent / snap if snap.parts[:1] == ("data",) else corpus.parent / snap
    return snap


def gate1(corpus: Path, day: str, version: str) -> list[tuple[str, bool, str]]:
    """Per class document: the reader's state at the end of `day` (base = the seed version) == the live file."""
    man = json.loads(Path(f"{corpus}.resume.json").read_text(encoding="utf-8"))
    day_rec = next((d for d in man.get("days") or [] if d.get("day") == day), {})
    live = r2.live_documents(_snapshot_dir(corpus, day_rec), str(man.get("session_id") or ""))
    rows = list(lbc._rows(corpus))
    base = class_seed_mapping(version)
    out = []
    for p in CLASS_DOCUMENTS:
        got = live.get(p)
        rec = doc.content_at(rows, doc.DocRef("owncloud", p), day, base=base)
        rec_b = None if (rec is None or doc.is_unknown(rec)) else rec.encode("utf-8")
        ok = got is not None and len(got) > 0 and rec_b == got
        out.append((f"gate 1 {day} {p}: reader == live", ok,
                    f"live bytes {None if got is None else len(got)}; reader bytes {None if rec_b is None else len(rec_b)}"))
    return out


def pinned_update_rows(man: dict[str, Any], bank_ids: dict[str, str], transcripts: list[dict], rows: list[dict],
                       day: str, base: dict) -> list[tuple[str, bool, str]]:
    """(a): one row per pinned task that is an update variant of bank v7 (a check pin is reported, no bar)."""
    import stage3_views as sv
    texts = b4r.cross_variant_texts()
    tl = {p: sv.document_timeline(rows, p, base) for p in CLASS_DOCUMENTS}
    out = []
    for pin in man.get("pinned_tasks") or []:
        acct, tid_bank = pin.get("account"), pin.get("task_id")
        text = bank_ids.get(str(tid_bank))
        v = texts.get(b4r._norm_text(text or ""))
        if v is None:
            out.append((f"(a) pin {acct} {tid_bank}", False, "not a bank-v7 cross-document variant"))
            continue
        sess = [t for t in transcripts if str(t.get("account")) == acct and str(t.get("sim_ts") or "")[:10] == day
                and any(isinstance(m.get("content"), str) and b4r._norm_text(text) in b4r._norm_text(m["content"])
                        for m in t.get("messages") or [])]
        if not sess:
            out.append((f"(a) pin {acct} {v['kind']} {v['item']}", v["kind"] != "update", "the pinned task was not found in any session of the day"))
            continue
        sid = str(sess[0].get("task_id"))
        reps = {p: sum(1 for r in rows if r.get("account") == acct and str(r.get("task_id")) == sid
                       and r.get("action") == "replace_in_file" and (r.get("exit_code") or 0) == 0
                       and b4r._ok_write(r) == p) for p in (v["doc1"], v["doc2"])}
        vals = []
        for p in (v["doc1"], v["doc2"]):
            cs = [c for c in tl[p] if str(c.task_id or "") == sid and c.account == acct]
            before = cs[0].before if cs else None
            after = cs[-1].after if cs else None
            vals.append((b4r.item_value(b4r.item_line(before, v["item"])), b4r.item_value(b4r.item_line(after, v["item"]))))
        changed = all(a is not None and a != b for b, a in vals)
        same = vals[0][1] is not None and vals[0][1] == vals[1][1]
        detail = f"session {sid}: replace_in_file rows {reps}; values before/after {vals}"
        if v["kind"] == "update":
            out.append((f"(a) pinned update {acct} {v['item']}", all(n >= 1 for n in reps.values()) and changed and same, detail))
        else:
            out.append((f"(report) pinned check {acct} {v['item']}", True, detail))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--day", required=True)
    ap.add_argument("--version", required=True, choices=("v6", "v7"))
    ap.add_argument("--pins", action="store_true", help="the rehearsal: read (a) and (b) too")
    ap.add_argument("--bank", default=str(FORK / "results/stage3/bank-reweight/benign_task_bank_v2_class_v7.yaml"))
    ap.add_argument("--out-json", required=True)
    ns = ap.parse_args(argv)
    corpus = Path(ns.corpus)
    version = b4r.check_provenance(corpus, ns.version)
    man = json.loads(Path(f"{corpus}.resume.json").read_text(encoding="utf-8"))
    rows_out: list[tuple[str, bool, str]] = []
    beside = r2.check(corpus, ns.day) if ns.pins else None   # 07e's R1, R2, R4 (its R3 reads the v6 base: not used)
    if ns.pins:
        from mole.generator.agentic_member import load_task_bank_ids
        ids = load_task_bank_ids(ns.bank, rich=True)
        tr = wy._load_jsonl(str(corpus.with_suffix(".transcripts.jsonl")))
        rows = list(lbc._rows(corpus))
        rows_out += pinned_update_rows(man, ids, tr, rows, ns.day, class_seed_mapping(version))
        rec_ok = man.get("class_documents") == class_documents_record("v7")
        seed_v = (man.get("class_documents_seed") or {}).get("version")
        rows_out.append(("(b) the v7 seed set recorded at world start", rec_ok and seed_v == "v7",
                         f"record == v7 record {rec_ok}; class_documents_seed.version {seed_v}"))
    rows_out += gate1(corpus, ns.day, version)
    verdict = "PASS" if all(ok for _, ok, _ in rows_out) else "FAIL"
    res = {"corpus": str(corpus), "day": ns.day, "seed_version": version, "verdict": verdict, "rows": rows_out,
           "beside_07e": None if beside is None else
           {"rows": [r for r in beside["rows"] if not r[0].startswith("R3")], "class_writes_by_action": beside["class_writes_by_action"],
            "sessions": beside["sessions"]}}
    Path(ns.out_json).write_text(json.dumps(res, indent=1) + "\n")
    for name, ok, det in rows_out:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {det}")
    if beside:
        for name, ok, det in res["beside_07e"]["rows"]:
            print(f"  (beside) [{'PASS' if ok else 'FAIL'}] {name}: {det}")
    print("VERDICT", verdict)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
