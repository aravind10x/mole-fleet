"""Tests for stage3_elicitation_packet_check.py (brief 29 E0-2). Synthetic strings only; no packet text."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage3_elicitation_packet_check as pc  # noqa: E402


def wrap(inner: str, b: str = pc.PACKET_B, e: str = pc.PACKET_E) -> str:
    return f"header\n{b}\n{inner}\n{e}\ntrailer"


def test_between_returns_text_strictly_between_markers():
    assert pc.between(wrap("a\nb"), pc.PACKET_B, pc.PACKET_E) == "a\nb"


def test_between_rejects_missing_or_repeated_markers():
    with pytest.raises(ValueError):
        pc.between("no markers", pc.PACKET_B, pc.PACKET_E)
    with pytest.raises(ValueError):
        pc.between(wrap("x") + "\n" + pc.PACKET_B, pc.PACKET_B, pc.PACKET_E)


def test_scan_counts_each_class_and_clean_text_has_none():
    clean = "A colleague edits a line under Current values and describes where the value goes."
    assert sum(pc.scan(clean).values()) == 0
    dirty = "This is for a judge named Kimi, see brief 12 and work/stage3 and the word hidden, skip and payload."
    hits = pc.scan(dirty)
    assert hits["model_and_instrument_names"] >= 2
    assert hits["brief_and_amendment_numbers"] >= 1
    assert hits["repository_paths"] >= 1
    assert hits["framing"] >= 1 and hits["weakening"] >= 1 and hits["filter_field"] >= 1


def test_scan_does_not_flag_substrings_of_ordinary_words():
    assert pc.scan("The solution is considered resolved.")["model_and_instrument_names"] == 0


def test_schema_blocks_fill_placeholders_and_check_keys():
    answer = {"items": [{"id": "0", "document": "d", "kind": "k", "composed_effect": "e",
                         "statements": [{"op": "o", "anchor_or_region": "a", "text": "t"}] * 3}]}
    pair = {"id": "0", "documents": ["a", "b"], "kind": "cross-document", "composed_effect": "e",
            "statements": [{"document": "a", "op": "replace", "anchor_or_region": "a", "text": "t"}] * 2}
    res = {"results": [{"id": "i", "valid": True, "failed_checks": ["x"],
                        "statements": [{"index": 0, "rating": 0, "within_target": True}],
                        "recovery": {"colleague_a": {"whole": 0, "parts": [0]}, "colleague_b": {"whole": 0, "parts": [0]}}}]}
    text = "\n".join(json.dumps(x, indent=2) for x in (answer, pair, res))
    text = text.replace("true", "<true or false>").replace(": 0,", ": <0 to 1>,", 1)
    blocks = pc.schema_blocks(text)
    assert pc.check_schema(blocks) == []
    bad = json.loads(json.dumps(blocks))
    bad[0]["items"][0]["extra"] = 1
    assert pc.check_schema(bad)


def test_fields_command_states_only_that_names_occur_in_the_source(tmp_path, capsys):
    src = tmp_path / "reader.py"
    src.write_text('x = st["op"]; y = t["document"]; z = p.get("composed_effect"); w = st["text"]; v = st["anchor_or_region"]; '
                   'u = t["kind"]; s = t["statements"]', encoding="utf-8")
    assert pc.main(["fields", "--legibility", str(src)]) == 0
    out = capsys.readouterr().out
    assert "occurs in the reader source" in out and "not a load test" in out
    assert "indexed" not in out and "verified" not in out
    src.write_text('x = st["op"]', encoding="utf-8")
    assert pc.main(["fields", "--legibility", str(src)]) == 1
    assert "NOT FOUND in the reader source" in capsys.readouterr().out


def test_check_fields_finds_indexed_names_and_misses_absent_ones():
    src = 'x = st["op"]; y = t["document"]; z = p.get("composed_effect"); w = st["text"]'
    res = pc.check_fields(src)
    assert res["op"] and res["document"] and res["composed_effect"] and res["text"]
    assert not res["anchor_or_region"]
