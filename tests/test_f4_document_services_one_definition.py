"""L4: the set of services a shared F4 document may live on has ONE definition, the shared
reader's `mole.oracles.document.SERVICES`, and the coalition loader uses that object (branch
review 2026-10-20, smell: F4_DOCUMENT_SERVICES duplicated document.SERVICES)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from mole.generator import coalitions as co
from mole.oracles import document as doc

REPO = Path(__file__).resolve().parents[1]


def test_coalitions_uses_the_readers_service_set_object():
    assert co.F4_DOCUMENT_SERVICES is doc.SERVICES


def test_coalitions_source_has_no_second_literal_of_the_service_set():
    src = (REPO / "mole" / "generator" / "coalitions.py").read_text(encoding="utf-8")
    # no tuple literal naming the services on its own: the only definition is the import
    assert not re.search(r'F4_DOCUMENT_SERVICES\s*=\s*\(', src)
    assert re.search(r"from mole\.oracles\.document import .*SERVICES|import .*document", src)


def test_loader_rejects_a_service_the_reader_does_not_know(tmp_path):
    d = {"schema": "coalitions-v2", "threat": "f4_shared_doc", "variant": "k1",
         "branches": {"T": {"instances": [
             {"id": "T1", "document": {"service": "rocketchat", "path": "#general"},
              "roles": {"editor_1": "deepa.a1"},
              "campaign_window": {"first_day": 1, "last_day": 1}}]}}}
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="document.service"):
        co.load_coalitions(p, "T")
    for svc in doc.SERVICES:                   # every reader service loads
        d["branches"]["T"]["instances"][0]["document"] = {
            "service": svc, "path": "proj:main/x.md" if svc == "gitlab" else "/shared/x.md"}
        p.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
        assert co.load_coalitions(p, "T")[0].document["service"] == svc
