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
from mole.seeders.seed_class_docs import (CLASS_DOCUMENTS, CLASS_DOCUMENTS_V7, CLASS_SEED_VERSIONS,
                                          SHARED_LINES_V7, class_documents, class_documents_record,
                                          class_seed_mapping, seed_class_documents)

ROOT = Path(__file__).resolve().parents[1]
CLASS_BANK = ROOT / "results/stage3/bank-reweight/benign_task_bank_v2_class.yaml"      # v5 (prefix_rw_v1)
CLASS_BANK_V6 = ROOT / "results/stage3/bank-reweight/benign_task_bank_v2_class_v6.yaml"  # v6 (brief 07e E3)
CLASS_BANK_V7 = ROOT / "results/stage3/bank-reweight/benign_task_bank_v2_class_v7.yaml"  # v7 (brief 14 R1)
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


@pytest.mark.parametrize("bank", [CLASS_BANK, CLASS_BANK_V6, CLASS_BANK_V7])
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


# ── brief 14 (B4-R): the versioned seeds, v6 the default and unchanged, v7 = v6 + shared lines ──

#: sha256 of the v6 documents as `prefix_rw_v2` recorded them (data/corpus/spike/prefix_rw_v2.jsonl.resume.json)
V6_SHA256 = {
    "/shared/infra/training-pipeline/README.md": "06d0543bb8dd4971ed86f0ec5f8b1844df7df90841051c2f270fe5fe694b422a",
    "/shared/eval/release-gate-runbook.md": "a17f1f145b187fc36e39d60410af9f6f24a0a635ab49b57bf9df20d9ab30c974",
    "/shared/capabilities/finetune-guide.md": "3672757cc35f8dd274f66f21d8129b4713082c7649f5752df0b3774446c66800",
    "/shared/alignment/redteam-checklist.md": "4cf9ce220927fa6f789416763af0bfba9e9badb08f70f03fd14cb2d07f6b281f",
    "/shared/ops/oncall-runbook.md": "ff36a4c1401ffe81ab35c10f175ffe09bb0b180f6817973cbbab5d236b19518a",
    "/shared/onboarding/engineering-setup.md": "079fba2251be3bd94f5e04e3beedd3182bc7545c85d1924a612c28d4b3a6e76e",
}


def _shared_table():
    """SHARED from scripts/stage3/stage3_b4r_design.py, read as a literal (paths named by the
    module's constants are resolved from its own assignments)."""
    import ast
    tree = ast.parse((ROOT / "scripts/stage3/stage3_b4r_design.py").read_text())
    names = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            names[node.targets[0].id] = node.value.value
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "SHARED":
            src = ast.unparse(node.value)
            return eval(src, {"__builtins__": {}}, dict(names))  # noqa: S307 (a literal table)
    raise AssertionError("SHARED not found")


def test_v6_is_the_default_and_byte_identical_to_what_prefix_rw_v2_seeded():
    import hashlib
    assert CLASS_SEED_VERSIONS["v6"] is CLASS_DOCUMENTS and class_documents() is CLASS_DOCUMENTS
    assert {p: hashlib.sha256(c.encode()).hexdigest() for p, c in CLASS_DOCUMENTS.items()} == V6_SHA256
    assert class_seed_mapping() == class_seed_mapping("v6")
    assert class_documents_record() == class_documents_record("v6")


def test_v7_only_adds_the_shared_lines_inside_current_values_before_the_review_date():
    assert list(CLASS_DOCUMENTS_V7) == list(CLASS_DOCUMENTS)
    for p, v6 in CLASS_DOCUMENTS.items():
        a, b = v6.split("\n"), CLASS_DOCUMENTS_V7[p].split("\n")
        added = SHARED_LINES_V7.get(p, [])
        assert len(b) == len(a) + len(added), p
        at = next((i for i, ln in enumerate(b) if ln in added), None)
        if not added:
            assert a == b, p
            continue
        assert b[at:at + len(added)] == added, p                    # contiguous, in table order
        assert b[:at] + b[at + len(added):] == a, p                 # every v6 line kept, in order
        assert b[at + len(added)].startswith("- Last-reviewed date:"), p
        assert "## Current values" in b[:at]


def test_every_shared_item_is_cited_verbatim_by_both_of_its_v7_documents():
    rows = _shared_table()
    assert len(rows) == 8
    for r in rows:
        for p in r["docs"]:
            text = CLASS_DOCUMENTS_V7[p]
            assert r["line"] in text.split("\n"), (r["item"], p)
            assert r["item"].lower() in text.lower(), (r["item"], p)
    # every added line belongs to a row of one of its documents, and nothing else was added
    want = {(p, r["line"]) for r in rows for p in r["docs"] if r["line"] not in CLASS_DOCUMENTS[p].split("\n")}
    assert want == {(p, ln) for p, lns in SHARED_LINES_V7.items() for ln in lns}


def test_v7_seeds_maps_and_records_its_own_content():
    import hashlib
    written: dict[str, str] = {}

    class FakeOwnCloud:
        async def write_file(self, *, path, content=""):
            written[path] = content

    assert asyncio.run(seed_class_documents(SimpleNamespace(owncloud=FakeOwnCloud()), version="v7")) == 6
    assert written == CLASS_DOCUMENTS_V7
    assert class_seed_mapping("v7") == {("owncloud", p): c for p, c in CLASS_DOCUMENTS_V7.items()}
    assert [r["sha256"] for r in class_documents_record("v7")] == [
        hashlib.sha256(c.encode()).hexdigest() for c in CLASS_DOCUMENTS_V7.values()]
    path = "/shared/alignment/redteam-checklist.md"
    assert content_at([], DocRef("owncloud", path), None, base=class_seed_mapping("v7")) == CLASS_DOCUMENTS_V7[path]
    with pytest.raises(KeyError, match="unknown class-document version"):
        class_documents("v8")


def test_the_version_flag_is_refused_where_it_cannot_apply(tmp_path):
    with pytest.raises(ValueError, match="needs class_documents"):
        asyncio.run(simulate(mode="rules", sandbox_mode="lab", n_personas=2, n_days=1,
                             out_path=tmp_path / "a.jsonl", class_documents_version="v7"))
    with pytest.raises(ValueError, match="class_documents_version must be one of"):
        asyncio.run(simulate(mode="rules", sandbox_mode="lab", n_personas=2, n_days=1,
                             out_path=tmp_path / "b.jsonl", class_documents=True,
                             class_documents_version="v9"))


def test_rules_mode_accepts_the_v7_flags_verbatim(tmp_path):
    out = tmp_path / "r7.jsonl"
    asyncio.run(simulate(mode="rules", sandbox_mode="lab", n_personas=2, n_days=1,
                         sessions_per_day=1, out_path=out, class_documents=True,
                         class_documents_version="v7", task_bank_path=CLASS_BANK_V7))
    assert out.exists()


def test_the_v7_bank_adds_cross_document_tasks_naming_two_class_documents():
    v6, v7 = load_task_bank(str(CLASS_BANK_V6), rich=True), load_task_bank(str(CLASS_BANK_V7), rich=True)
    assert set(v6) == set(v7)
    n_cross = 0
    for team, tasks in v6.items():
        assert v7[team][: len(tasks)] == tasks                     # v6's tasks first, unchanged
        extra = v7[team][len(tasks):]
        assert len(set(extra)) == len(extra)                       # distinct texts within a team
        for t in extra:
            assert sum(p in t for p in CLASS_DOCUMENTS) == 2, t
        n_cross += len(extra)
    assert n_cross == 68
