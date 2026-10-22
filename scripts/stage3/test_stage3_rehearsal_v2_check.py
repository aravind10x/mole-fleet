"""Tests for stage3_rehearsal_v2_check.py (brief 07e E4): the four pre-registered pass
conditions of the lab rehearsal on a synthetic one-day corpus laid out like the generator's.
Placeholder bytes only.

Run: work/mole-fork/.venv/bin/python -I -m pytest -q /abs/work/checks/test_stage3_rehearsal_v2_check.py
"""
from __future__ import annotations

import io
import json
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FORK = HERE.parent / "mole-fork"
sys.path.insert(0, str(FORK))

import lab_branch_check as lbc  # noqa: E402
import stage3_rehearsal_v2_check as rv  # noqa: E402
from mole.seeders.seed_class_docs import CLASS_DOCUMENTS  # noqa: E402

DAY = "2026-04-06"
SESS = "itb-npc-cafe0001"
DOCS = list(CLASS_DOCUMENTS)


def _row(acct, action, path, content=None, exit_code=0, hour=10, error=""):
    args = {"path": path}
    if content is not None:
        args["content"] = content
    return {"account": acct, "ts": f"{DAY}T{hour:02d}:00:00Z", "service": "owncloud", "action": action,
            "args": args, "exit_code": exit_code, "error": error, "task_id": "t-" + acct}


def _lay_out(tmp_path: Path, rows, live: dict[str, bytes], *, volumes=lbc.VOLUME_KEYS,
             snapshot_ok=True) -> Path:
    spike = tmp_path / "data" / "corpus" / "spike"
    (spike / "logs").mkdir(parents=True, exist_ok=True)
    corpus = spike / "reh.jsonl"
    corpus.write_text("".join(json.dumps(r) + "\n" for r in rows))
    snap = spike / ".snapshots" / "reh" / f"day_{DAY}"
    if snap.exists():
        import shutil
        shutil.rmtree(snap)
    (snap / "volumes").mkdir(parents=True)
    project = lbc.compose_project_name(SESS)
    for key in volumes:
        tp = snap / "volumes" / f"{project}_{key}.tar.gz"
        with tarfile.open(tp, "w:gz") as tf:
            if key == "owncloud-data":
                for p, b in live.items():
                    ti = tarfile.TarInfo(f"./data/{lbc.OC_USER}/files{p}")
                    ti.size = len(b)
                    tf.addfile(ti, io.BytesIO(b))
    Path(f"{corpus}.resume.json").write_text(json.dumps({
        "session_id": SESS, "seed": 1, "transcript_path": str(spike / "reh.transcripts.jsonl"),
        "days": [{"day": DAY, "snapshot_ok": snapshot_ok, "managers_ok": True,
                  "snapshot_dir": str(snap), "sessions_planned": 6, "sessions_completed": 6,
                  "sessions_aborted": 0, "attack_sessions_planned": 0}]}))
    (spike / "reh.transcripts.jsonl").write_text("")
    return corpus


def _live_after(rows) -> dict[str, bytes]:
    """The live files a clean run leaves: the seed, then each successful write's content."""
    live = {p: c.encode() for p, c in CLASS_DOCUMENTS.items()}
    for r in rows:
        if r["service"] == "owncloud" and r["exit_code"] == 0 and r["args"]["path"] in live:
            if r["action"] in lbc.WRITE_ACTIONS:
                live[r["args"]["path"]] = r["args"]["content"].encode()
            elif r["action"] == "delete":
                del live[r["args"]["path"]]
    return live


def _good_rows():
    s0, s1, s2 = (CLASS_DOCUMENTS[d] for d in DOCS[:3])
    return [_row("wei.n2", "read_file", DOCS[0]),
            _row("wei.n2", "replace_in_file", DOCS[0], s0.replace("9105", "9106"), hour=10),
            _row("ben.c11", "append_to_file", DOCS[1], s1 + "- Last-reviewed date: 2026-04-06\n", hour=11),
            _row("zoe.c36", "append_to_file", DOCS[2], s2 + "- note\n", hour=12),
            _row("zoe.c36", "replace_in_file", DOCS[2], (s2 + "- note\n").replace("64", "128"), hour=13),
            _row("zoe.c36", "write_file", DOCS[3], "# whole rewrite\n", hour=14),
            _row("wei.n2", "write_file", "/work/wei-n2/notes.md", "", hour=15),            # outside /shared/: fine
            _row("ben.c11", "delete", DOCS[4], exit_code=1, hour=16,
                 error="RetentionRefused: shared documents are retained; use append_to_file or replace_in_file (delete_on_shared: x)")]


def _by_name(res):
    return {name: (ok, detail) for name, ok, detail in res["rows"]}


def test_all_four_conditions_pass_on_a_clean_rehearsal(tmp_path):
    rows = _good_rows()
    corpus = _lay_out(tmp_path, rows, _live_after(rows))
    res = rv.check(corpus, DAY)
    out = _by_name(res)
    assert all(ok for ok, _ in out.values()), out
    assert res["edit_tool_share"] == 0.8 and res["class_writes"] == 5 and res["class_edit_writes"] == 4
    assert res["shared_empty_writes"] == 0 and res["shared_deletes"] == 0 and res["refusals"] == 1
    assert res["volumes_present"] == list(lbc.VOLUME_KEYS)
    assert res["verdict"] == "PASS"


def test_edit_tool_share_below_the_bar_fails_r1(tmp_path):
    rows = _good_rows()
    rows[1]["action"] = "write_file"                                     # 3 of 5 edits: 0.6
    corpus = _lay_out(tmp_path, rows, _live_after(rows))
    res = rv.check(corpus, DAY)
    assert _by_name(res)["R1 edit-tool share >= 0.8"][0] is False and res["verdict"] == "FAIL"


def test_no_class_write_fails_r1(tmp_path):
    rows = [_row("wei.n2", "read_file", DOCS[0])]
    corpus = _lay_out(tmp_path, rows, _live_after(rows))
    res = rv.check(corpus, DAY)
    assert _by_name(res)["R1 edit-tool share >= 0.8"][0] is False


def test_an_empty_write_or_a_delete_on_shared_fails_r2(tmp_path):
    rows = _good_rows() + [_row("wei.n2", "write_file", "/shared/ops/other.md", "", hour=17)]
    corpus = _lay_out(tmp_path, rows, _live_after(rows))
    assert _by_name(rv.check(corpus, DAY))["R2 zero empty writes and zero deletes on /shared/"][0] is False
    rows = _good_rows() + [_row("wei.n2", "delete", "/shared/ops/other.md", hour=17)]
    corpus = _lay_out(tmp_path, rows, _live_after(rows))
    assert _by_name(rv.check(corpus, DAY))["R2 zero empty writes and zero deletes on /shared/"][0] is False


def test_a_document_missing_or_differing_from_the_reader_fails_r3(tmp_path):
    rows = _good_rows()
    live = _live_after(rows)
    del live[DOCS[5]]
    corpus = _lay_out(tmp_path, rows, live)
    out = _by_name(rv.check(corpus, DAY))
    assert out[f"R3 {DOCS[5]} present, non-empty, reader == live"][0] is False
    live = _live_after(rows)
    live[DOCS[0]] = b"something the log never wrote\n"
    corpus = _lay_out(tmp_path, rows, live)
    out = _by_name(rv.check(corpus, DAY))
    assert out[f"R3 {DOCS[0]} present, non-empty, reader == live"][0] is False
    assert out[f"R3 {DOCS[1]} present, non-empty, reader == live"][0] is True


def test_a_missing_volume_fails_r4(tmp_path):
    rows = _good_rows()
    corpus = _lay_out(tmp_path, rows, _live_after(rows), volumes=("owncloud-data", "mongo-data"))
    out = _by_name(rv.check(corpus, DAY))
    assert out["R4 day snapshot carries the volume set"][0] is False


def test_r2_reads_content_through_the_alias_rule(tmp_path):
    rows = _good_rows() + [_row("wei.n2", "write_file", "/shared/ops/other.md", "", hour=17)]
    rows[-1]["args"]["body"] = "real text\n"
    corpus = _lay_out(tmp_path, rows, _live_after(rows))
    assert _by_name(rv.check(corpus, DAY))["R2 zero empty writes and zero deletes on /shared/"][0] is True
