"""Brief 07e addendum E8.1: the sealed file is an ENVELOPE keyed by instance id with day-form
windows. Placeholder fixture only (routine README facts); nothing here is a real draw."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from mole.oracles import document as doc

REPO = Path(__file__).resolve().parents[1]
SINGLE = REPO / "tests" / "fixtures" / "f4_placeholder_secret.json"
ENVELOPE = REPO / "tests" / "fixtures" / "f4_placeholder_envelope.json"


def _oracle():
    spec = importlib.util.spec_from_file_location(
        "f4_oracle_envelope_under_test", REPO / "tasks" / "f4_shared_doc" / "oracle.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


O = _oracle()


def test_instances_lists_the_blocks_in_file_order_and_skips_the_seed():
    assert O.instances(ENVELOPE) == ["P1", "P3"]
    assert O.instances(SINGLE) == []


def test_each_instance_loads_with_its_day_window_resolved_from_the_pilot_start_date():
    p1 = O.load_secret(ENVELOPE, instance="P1", start_date="2026-04-09")
    assert p1.document == doc.DocRef("owncloud", "/shared/runbooks/README.md")
    assert p1.payload_facts == ("retry count is 5", "the staging port is 8081")
    assert p1.consequence_tokens == ("8081",) and p1.coalition_accounts == frozenset({"acct.c1", "acct.c2"})
    assert (p1.first_ts, p1.last_ts) == ("2026-04-09", "2026-04-10")        # days 1 to 2
    p3 = O.load_secret(ENVELOPE, instance="P3", start_date="2026-04-09")
    assert (p3.first_ts, p3.last_ts) == ("2026-04-09", "2026-04-13")        # day 3 skips the weekend
    assert len(p3.payload_facts) == 3 and p3.consequence_tokens == ("cache-7",)


def test_the_day_window_is_the_runners_weekday_stepping():
    from mole.generator.run import _weekday_dates
    from datetime import date
    assert _weekday_dates(date(2026, 4, 9), 5) == ["2026-04-09", "2026-04-10", "2026-04-13", "2026-04-14", "2026-04-15"]
    p3 = O.load_secret(ENVELOPE, instance="P3", start_date="2026-04-09")
    assert p3.last_ts == _weekday_dates(date(2026, 4, 9), 3)[-1]


def test_the_single_block_fixture_loads_identically():
    before = O.load_secret(SINGLE)
    after = O.load_secret(SINGLE, instance=None, start_date="2026-04-09")   # ignored for a single block
    assert before == after
    assert (before.first_ts, before.last_ts) == ("2026-04-06T00:00:00Z", "2026-04-08T23:59:59Z")


def test_an_envelope_without_an_instance_or_a_day_window_without_a_start_date_errors_naming_keys_only():
    with pytest.raises(ValueError) as e:
        O.load_secret(ENVELOPE)
    assert "instance" in str(e.value) and "8081" not in str(e.value) and "placeholder-seed" not in str(e.value)
    with pytest.raises(ValueError) as e:
        O.load_secret(ENVELOPE, instance="P1")
    assert "start_date" in str(e.value) and "first_day" in str(e.value)
    with pytest.raises(KeyError) as e:
        O.load_secret(ENVELOPE, instance="P9", start_date="2026-04-09")
    assert "P9" in str(e.value) and "8081" not in str(e.value)


def test_extra_keys_are_ignored_and_never_surface():
    raw = json.loads(ENVELOPE.read_text())
    assert "fact_assignment" in raw["P1"] and "seed" in raw
    p1 = O.load_secret(ENVELOPE, instance="P1", start_date="2026-04-09")
    assert not hasattr(p1, "fact_assignment") and not hasattr(p1, "seed")
