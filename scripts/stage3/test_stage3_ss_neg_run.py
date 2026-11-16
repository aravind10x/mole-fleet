"""Offline test for stage3_ss_neg_run (adapter from red's table layout to the pinned stage3_ss_neg)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_ss_neg_run as nr  # noqa: E402


def test_adapter_maps_control_form_and_pass_two_only():
    t = {"runs": [{"run_id": "a", "arm": "single", "class": "no_use", "control": False, "control_form": None, "follower": "kimi"},
                  {"run_id": "c", "arm": "clean", "class": "unclear", "control": True, "control_form": "full", "follower": "sol"}],
         "pass2_agreement": {"n": 20, "identical": 18}}
    rows, p2 = nr.adapt(t)
    assert rows[0] == {"run_id": "a", "arm": "single", "class": "no_use", "control": False, "follower": "kimi"}
    assert rows[1]["form"] == "full" and rows[1]["control"] is True and "control_form" not in rows[1]
    assert p2 == {"n": 20, "identical": 18}


def test_display_adapter_reads_pairs_and_form_suffixed_fields():
    t = {"pairs": [{"run_id": "x", "arm": "single", "class_own_form": "no_use", "class_other_form": "acts_other_words"}],
         "two_by_two": {}}
    rows = nr.adapt_display(t)
    assert rows == [{"run_id": "x", "arm": "single", "class_own": "no_use", "class_other": "acts_other_words"}]
    assert nr.adapt_display([{"run_id": "y", "arm": "planted", "class_own": "omits", "class_other": "no_use"}])[0]["class_own"] == "omits"
