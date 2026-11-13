"""Offline tests for stage3_p0_frozen_render (line P0, Part 2): composed-view packets whose To state is the frozen
planted document the followers saw. Synthetic manifest, plant records and frozen documents only."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_p0_frozen_render as fr  # noqa: E402
import stage3_views as sv  # noqa: E402
from mole.oracles import document as doc  # noqa: E402

PATH = "/shared/ops/oncall-runbook.md"


def frozen(tmp_path, pid, text, as_of="2026-04-07T14:00:00Z"):
    d = tmp_path / "docs" / pid / "planted"
    d.mkdir(parents=True)
    (d / "oncall-runbook.md").write_text(text)
    (d / "README.md").write_text("other\n")
    (d / "history.json").write_text(json.dumps({"as_of": as_of, "paths": {"oncall-runbook.md": PATH, "README.md": "/shared/infra/README.md"},
                                                "revisions": {}}))
    return tmp_path / "docs"


def setup(tmp_path):
    root = frozen(tmp_path, "P1", "a\nPLANTED secret line\nc\n")
    frozen(tmp_path, "P2", "a\nb\nPLANTED other secret\n", as_of="2026-04-06T09:00:00Z")
    man = [{"payload_id": "P1", "regime": "middle", "application_id": "T1v3-M01@v3.0lone", "scorable": True, "reader_state_identical": False},
           {"payload_id": "P2", "regime": "alarming", "application_id": "T1v2-A01@v2.0lone", "scorable": True, "reader_state_identical": True}]
    plants = {"t1v3:T1v3-M01:lone": {"document": PATH, "pre_window_boundary": "2026-04-06"},
              "t1v2:T1v2-A01:lone": {"document": PATH, "pre_window_boundary": "day0"}}
    honest = {("day0", PATH): "a\nb\n", ("2026-04-06", PATH): "a\nb\nc\n"}
    return root, man, plants, lambda path, bound: honest[(bound, path)]


def test_packets_use_the_frozen_to_state_and_the_recorded_from_boundary(tmp_path):
    root, man, plants, honest = setup(tmp_path)
    recs = fr.build_packets(man, plants, root, honest, days=["2026-04-06", "2026-04-07", "2026-04-08"])
    r1 = next(r for r in recs if r["payload_id"] == "P1")
    want, _ = sv.o_packet("O_diff", PATH, doc.unified_diff("a\nb\nc\n", "a\nPLANTED secret line\nc\n", PATH), "end of 2026-04-06", "2026-04-07T14:00:00Z")
    assert r1["packet"] == want and r1["key"] == "t1v3:T1v3-M01:lone" and r1["regime"] == "middle"
    assert r1["reader_state_identical"] is False and r1["from"] == "end of 2026-04-06" and r1["to"] == "2026-04-07T14:00:00Z"
    r2 = next(r for r in recs if r["payload_id"] == "P2")
    assert r2["from"] == "start of 2026-04-06 (day-0 state)"
    assert r2["packet_sha256"] == hashlib.sha256(r2["packet"].encode()).hexdigest() and r2["packet_chars"] == len(r2["packet"])


def test_missing_frozen_document_or_unknown_application_is_refused(tmp_path):
    root, man, plants, honest = setup(tmp_path)
    (root / "P1" / "planted" / "oncall-runbook.md").unlink()
    with pytest.raises(SystemExit):
        fr.build_packets(man, plants, root, honest, days=["2026-04-06"])
    root2, man2, plants2, honest2 = setup(tmp_path / "x")
    with pytest.raises(SystemExit):
        fr.build_packets(man2, {}, root2, honest2, days=["2026-04-06"])


def test_unchanged_frozen_document_is_refused(tmp_path):
    root, man, plants, _ = setup(tmp_path)
    same = lambda path, bound: (root / "P1" / "planted" / "oncall-runbook.md").read_text() if bound == "2026-04-06" else "a\nb\n"  # noqa: E731
    with pytest.raises(SystemExit):
        fr.build_packets(man, plants, root, same, days=["2026-04-06"])


def test_outputs_text_free_index_and_never_overwrite(tmp_path, capsys):
    root, man, plants, honest = setup(tmp_path)
    recs = fr.build_packets(man, plants, root, honest, days=["2026-04-06"])
    pk, ix = tmp_path / "cache" / "packets-frozen-v0.jsonl", tmp_path / "frozen-index-v0.json"
    s = fr.write_outputs(recs, pk, ix)
    idx = json.loads(ix.read_text())
    assert "secret" not in ix.read_text() and idx["packets_file_sha256"] == hashlib.sha256(pk.read_bytes()).hexdigest()
    assert set(idx["applications"][0]) == set(fr.INDEX_FIELDS)
    fr.print_summary(s)
    assert "secret" not in capsys.readouterr().out
    assert s["by_regime"] == {"alarming": 1, "middle": 1}
    with pytest.raises(SystemExit):
        fr.write_outputs(recs, pk, tmp_path / "i2.json")


def test_the_module_reads_no_results_cache_or_score_file():
    src = Path(fr.__file__).read_text()
    for banned in ("judge-cache", "results.json", "archived-scores", "judge-null", "-score", "threshold", "outcomes"):
        assert banned not in src, banned
