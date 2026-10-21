"""The Stage 3 class documents seeded at world start (brief 07c, C1 prerequisite), and the
class bank selected by path. No Docker: the ownCloud manager is faked."""
from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from mole.generator.agentic_member import load_task_bank
from mole.generator.run import simulate
from mole.oracles.document import DocRef, content_at
from mole.seeders.seed_class_docs import (CLASS_DOCUMENTS, class_documents_record,
                                          class_seed_mapping, seed_class_documents)

ROOT = Path(__file__).resolve().parents[1]
CLASS_BANK = ROOT / "results/stage3/bank-reweight/benign_task_bank_v2_class.yaml"      # v5 (prefix_rw_v1)
CLASS_BANK_V6 = ROOT / "results/stage3/bank-reweight/benign_task_bank_v2_class_v6.yaml"  # v6 (brief 07e E3)
SHIPPED_BANK = ROOT / "bootstrap/benign_task_bank_v2.yaml"


def _rung1_class_list():
    """CLASS from scripts/stage3/stage3_rung1_class.py, read as a literal (the script's
    imports need the work/checks tree)."""
    import ast
    tree = ast.parse((ROOT / "scripts/stage3/stage3_rung1_class.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "CLASS":
            return ast.literal_eval(node.value)
    raise AssertionError("CLASS not found")


def test_every_class_document_is_seeded_with_every_item_its_tasks_name():
    cls = _rung1_class_list()
    assert set(CLASS_DOCUMENTS) == {d["path"] for d in cls}
    for d in cls:
        text = CLASS_DOCUMENTS[d["path"]].lower()
        for item in d["items"]:
            assert item.lower() in text, (d["path"], item)


def test_the_seeded_class_is_the_assignment_files_class():
    doc = yaml.safe_load((ROOT / "results/stage3/pilot/coalitions_f4_pilot.yaml").read_text())
    assert {(c["service"], c["path"]) for c in doc["class_documents"]} == {
        ("owncloud", p) for p in CLASS_DOCUMENTS}


def test_seed_writes_six_documents_and_skips_without_owncloud():
    written: dict[str, str] = {}

    class FakeOwnCloud:
        async def write_file(self, *, path, content=""):
            written[path] = content

    assert asyncio.run(seed_class_documents(SimpleNamespace(owncloud=FakeOwnCloud()))) == 6
    assert written == CLASS_DOCUMENTS
    assert asyncio.run(seed_class_documents(SimpleNamespace())) == 0


def test_the_document_reader_sees_the_seed_as_day_zero_content():
    path = "/shared/ops/oncall-runbook.md"
    ref = DocRef("owncloud", path)
    assert content_at([], ref, None, base=class_seed_mapping()) == CLASS_DOCUMENTS[path]
    rec = class_documents_record()
    assert [r["path"] for r in rec] == list(CLASS_DOCUMENTS)
    assert all(len(r["sha256"]) == 64 for r in rec)


@pytest.mark.parametrize("bank", [CLASS_BANK, CLASS_BANK_V6])
def test_the_class_bank_loads_by_path_and_adds_only_class_tasks(bank):
    shipped, klass = load_task_bank(str(SHIPPED_BANK), rich=True), load_task_bank(
        str(bank), rich=True)
    assert set(shipped) == set(klass)
    for team, tasks in shipped.items():
        assert klass[team][: len(tasks)] == tasks            # additions only
        for extra in klass[team][len(tasks):]:
            assert any(p in extra for p in CLASS_DOCUMENTS), extra
    assert sum(len(v) for v in klass.values()) > sum(len(v) for v in shipped.values())


def test_class_flags_are_refused_where_they_cannot_apply(tmp_path):
    with pytest.raises(ValueError, match="sandbox_mode='lab'"):
        asyncio.run(simulate(mode="rules", sandbox_mode="dryrun", n_personas=2, n_days=1,
                             out_path=tmp_path / "a.jsonl", class_documents=True))
    with pytest.raises(ValueError, match="inherits the parent's documents"):
        asyncio.run(simulate(mode="agentic", sandbox_mode="lab", n_personas=2, n_days=1,
                             out_path=tmp_path / "b.jsonl", class_documents=True,
                             branch_from=tmp_path / "parent.jsonl", llm=object()))


def test_rules_mode_accepts_the_class_flags_verbatim(tmp_path):
    """The L15 rules rehearsal runs the agentic flags unchanged; rules mode ignores them."""
    out = tmp_path / "r.jsonl"
    asyncio.run(simulate(mode="rules", sandbox_mode="lab", n_personas=2, n_days=1,
                         sessions_per_day=1, out_path=out, class_documents=True,
                         task_bank_path=CLASS_BANK))
    assert out.exists()
