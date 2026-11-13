"""Offline tests for stage3_etj_render (line ETJ): the planted composed-view packets, rendered by the recorded
scorers' own functions, for the red side to run. Synthetic plant results and items only; no payload, plants,
results or judge-cache file is read."""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_etj_render as er  # noqa: E402


@dataclass
class FakeResult:
    payload_id: str
    arm: str
    regime: str
    delivered: bool = True
    composed: bool = True


def fake_world():
    calls = {"regenerate": [], "build": []}
    results = {
        "v2": [FakeResult("T1v2-C01", "lone", "conforming"), FakeResult("T1v2-C01", "k2", "conforming"),
               FakeResult("T1v2-A01", "lone", "alarming"), FakeResult("T1v2-S01", "lone", "sham")],
        "v3": [FakeResult("T1v3-M01", "lone", "middle"), FakeResult("T1v2-C01", "lone", "routine_redraw"),
               FakeResult("T1v2-S02", "lone", "sham_redraw")],
    }

    def regenerate(corpus, payloads, template, manifest):
        calls["regenerate"].append((str(payloads), manifest["tag"]))
        return results[manifest["tag"]]

    def build_items(res, days, base, stem, render):
        calls["build"].append(stem)
        return {"O_diff": [{"payload_id": r.payload_id, "arm": r.arm, "label": f"{stem}+{r.payload_id}-{r.arm}:O_diff",
                            "packet": f"PACKET {stem} {r.payload_id} {r.arm} secret-text", "text_chars": 10 + len(r.arm),
                            "truncated": False} for r in res if r.composed and r.delivered],
                "P_own": [], "P_author": [], "P_author_ctx": []}
    return results, calls, regenerate, build_items


def run(tmp_path, **kw):
    results, calls, regen, build = fake_world()
    specs = [er.Planting("t1v2", tmp_path / "payloads-v2.json", {"tag": "v2"}),
             er.Planting("t1v3", tmp_path / "payloads-v3-planting.json", {"tag": "v3"})]
    recs = er.render(specs, corpus=tmp_path / "c.jsonl", template=tmp_path / "t.yaml", regenerate=regen, build_items=build,
                     days=["d1"], base={}, stem="prefix", render_event=None, **kw)
    return recs, calls


def test_render_keeps_in_scope_composed_applications_with_the_join_keys(tmp_path):
    recs, calls = run(tmp_path)
    assert [r["key"] for r in recs] == ["t1v2:T1v2-C01:lone", "t1v2:T1v2-C01:k2", "t1v2:T1v2-A01:lone",
                                        "t1v3:T1v3-M01:lone", "t1v3:T1v2-C01:lone"]
    reg = {r["key"]: (r["recorded_regime"], r["regime"]) for r in recs}
    assert reg["t1v2:T1v2-C01:lone"] == ("conforming", "routine") and reg["t1v3:T1v2-C01:lone"] == ("routine_redraw", "routine")
    assert reg["t1v2:T1v2-A01:lone"] == ("alarming", "alarming") and reg["t1v3:T1v3-M01:lone"] == ("middle", "middle")
    assert calls["build"] == ["prefix+t1v2", "prefix+t1v3"]               # the recorded scorers' stem tags
    assert [c[1] for c in calls["regenerate"]] == ["v2", "v3"]
    r0 = recs[0]
    assert r0["packet_sha256"] == hashlib.sha256(r0["packet"].encode("utf-8")).hexdigest()
    assert r0["packet_chars"] == len(r0["packet"]) and r0["text_chars"] == 14


def test_duplicate_application_keys_are_refused(tmp_path):
    results, calls, regen, build = fake_world()

    def build_dup(res, days, base, stem, render):
        out = build(res, days, base, stem, render)
        out["O_diff"] = out["O_diff"] + out["O_diff"][:1]
        return out
    with pytest.raises(ValueError):
        er.render([er.Planting("t1v2", tmp_path / "p.json", {"tag": "v2"})], corpus=tmp_path / "c", template=tmp_path / "t",
                  regenerate=regen, build_items=build_dup, days=["d1"], base={}, stem="s", render_event=None)


def test_outputs_packets_and_a_text_free_index_never_overwritten(tmp_path, capsys):
    recs, _ = run(tmp_path)
    pk, ix = tmp_path / "cache" / "packets-planted-v0.jsonl", tmp_path / "render-index-v0.json"
    summary = er.write_outputs(recs, pk, ix)
    lines = [json.loads(x) for x in pk.read_text().splitlines()]
    assert [x["key"] for x in lines] == [r["key"] for r in recs] and all("packet" in x for x in lines)
    idx = json.loads(ix.read_text())
    assert set(idx) >= {"n_applications", "by_planting_and_regime", "applications", "packets_file_sha256"}
    assert idx["packets_file_sha256"] == hashlib.sha256(pk.read_bytes()).hexdigest()
    row = idx["applications"][0]
    assert set(row) == {"key", "planting", "recorded_regime", "regime", "packet_chars", "text_chars", "packet_sha256", "truncated"}
    assert "secret-text" not in ix.read_text()
    er.print_summary(summary)
    out = capsys.readouterr().out
    assert "secret-text" not in out and "PACKET" not in out
    assert summary["by_planting_and_regime"] == {"t1v2|alarming": 1, "t1v2|conforming": 2, "t1v3|middle": 1, "t1v3|routine_redraw": 1}
    with pytest.raises(SystemExit):
        er.write_outputs(recs, pk, tmp_path / "other-index.json")
    with pytest.raises(SystemExit):
        er.write_outputs(recs, tmp_path / "other.jsonl", ix)


def test_the_module_reads_no_results_cache_or_score_file():
    src = Path(er.__file__).read_text()
    for banned in ("judge-cache", "results.json", "archived-scores", "judge-null", "t1v3-score", "seal", "thresholds"):
        assert banned not in src, banned


def test_cli_requires_every_input_and_output_path():
    with pytest.raises(SystemExit):
        er.parse_args(["--payloads-v2", "a"])
    a = er.parse_args(["--payloads-v2", "a", "--plants-v2", "b", "--payloads-v3", "c", "--plants-v3", "d",
                       "--packets-out", "e", "--index-out", "f"])
    assert a.payloads_v2 == Path("a") and a.index_out == Path("f")
