"""The frozen-script rule for scripts/track_b/grouping_measure.py is "changed only as the S5.2
record (results/stage3/s5-plumbing.md) says". The branch review (2026-10-20, Standards 2;
prep-report erratum 7) found additive outputs the record did not name. The record must list
every addition by name, and each name must exist in the script."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RECORD = REPO / "results" / "stage3" / "s5-plumbing.md"
SCRIPT = REPO / "scripts" / "track_b" / "grouping_measure.py"

ADDITIONS = ("walk", "equal_volume", "volume_by_day", "volume_mean", "volume_means",
             "g6_equal_volume")


def _additions_block(text: str) -> str:
    m = re.search(r"\*\*Additive changes to the frozen script.*?\n\n", text, flags=re.S)
    assert m, "s5-plumbing.md has no 'Additive changes to the frozen script' block"
    return m.group(0)


def test_record_names_every_addition_to_grouping_measure():
    block = _additions_block(RECORD.read_text(encoding="utf-8"))
    for name in ADDITIONS:
        assert f"`{name}`" in block or f"`{name}()`" in block, name
    assert "render_md" in block                     # the rendered paragraph and table


def test_every_named_addition_exists_in_the_script():
    src = SCRIPT.read_text(encoding="utf-8")
    assert "def walk(" in src
    for key in ("volume_by_day", "volume_mean", "volume_means", "g6_equal_volume", "equal_volume"):
        assert re.search(rf'["\']{key}["\']', src), key
