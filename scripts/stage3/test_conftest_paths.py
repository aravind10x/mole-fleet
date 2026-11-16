"""The fork's conftest makes the helpers outside scripts/stage3/ importable, without shadowing stage3's own modules."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_helpers_outside_stage3_are_importable():
    for name in ("first_cut_monitors", "prefix_personas", "grouping_measure", "generators"):
        assert importlib.util.find_spec(name) is not None, name


def test_stage3_modules_win_over_same_named_helpers():
    for name in ("judge_client", "score_fork_corpus"):
        spec = importlib.util.find_spec(name)
        assert spec is not None and Path(spec.origin).resolve().parent == HERE, name
