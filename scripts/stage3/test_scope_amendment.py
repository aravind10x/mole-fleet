"""Dated scope amendment to the frozen grouping measure (design v4 section 11.6; brief 07b
F2.6): the like-for-like scope gains ownCloud and GitLab documents (artefact types `file`,
`repo`) when the amendment is switched on, and is byte-for-byte the Stage 2b scope when it is
not (the default). Stage 2b numbers are not recomputed.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_scope_amendment.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import generators as gen  # noqa: E402
import grouping_measure as gm  # noqa: E402
import mole_corpus as mc  # noqa: E402

PROJECT = HERE.parent.parent
PREFIX = PROJECT / "work" / "mole-fork" / "data" / "corpus" / "spike" / "prefix_v1.jsonl"
S5C = PROJECT / "work" / "mole-fork" / "data" / "corpus" / "spike" / "s5c_objective_benign_1.jsonl"
FROZEN_LIKE = ("ticket", "checkpoint", "eval", "secret", "group", "org_record")
AMENDMENT = "stage3-shared-documents-2026-10-20"


def _g1_counts(corpus: Path) -> tuple[list[int], object]:
    br = gm.load_branch(corpus, None, mc.load_org_template(str(gm.DEFAULT_TEMPLATE)))
    spec = gm.GenSpec("G1", "G1", 1)
    return [len(gm.day_groups(br, spec, d).sets) for d in br.bdays], br


def test_default_scope_is_the_frozen_stage2b_like_for_like_tuple():
    assert mc.scope_amendment() is None
    assert mc.scope_types("likeforlike") == FROZEN_LIKE == mc.LIKE_TYPES
    assert mc.like_types() == FROZEN_LIKE


def test_amendment_is_dated_and_adds_file_and_repo_only():
    assert AMENDMENT in mc.SCOPE_AMENDMENTS and AMENDMENT.endswith("2026-10-20")
    with mc.scope_amendment_context(AMENDMENT):
        assert mc.scope_amendment() == AMENDMENT
        assert mc.scope_types("likeforlike") == FROZEN_LIKE + ("file", "repo")
        assert "mail" not in mc.like_types() and "chat" not in mc.like_types()
        assert mc.scope_types("allservices") == mc.ALL_TYPES          # unchanged
    assert mc.scope_amendment() is None                               # restored
    with pytest.raises(ValueError):
        mc.set_scope_amendment("not-an-amendment")


@pytest.mark.skipif(not PREFIX.exists(), reason="prefix_v1 corpus not on disk")
def test_stage2b_inputs_give_stage2b_outputs_under_the_old_scope():
    """The Stage 2b G1 like-for-like group counts per prefix day (109, 74, 21; the numbers the
    rung-1 pre-registration printed from the frozen measure) are reproduced with the amendment
    off, and are unchanged with it on (the in-process prefix has no file or repo touches)."""
    counts, _ = _g1_counts(PREFIX)
    assert counts == [109, 74, 21]
    with mc.scope_amendment_context(AMENDMENT):
        counts_amended, _ = _g1_counts(PREFIX)
    assert counts_amended == [109, 74, 21]


@pytest.mark.skipif(not S5C.exists(), reason="S5.3 lab corpus not on disk")
def test_amended_scope_sees_the_owncloud_document_group_but_not_chat_or_mail():
    """On the S5.3 lab corpus (three accounts wrote /shared/README.md on one day) the frozen
    scope emits no group; the amended scope emits the README writers' group; the all-services
    scope emits more (chat and mail pairs), which the amendment does not admit."""
    counts_old, br = _g1_counts(S5C)
    assert counts_old == [0]
    with mc.scope_amendment_context(AMENDMENT):
        counts_new, br2 = _g1_counts(S5C)
        sets = gm.day_groups(br2, gm.GenSpec("G1", "G1", 1), br2.bdays[0]).sets
    # two file co-writes that day: /shared/README.md by all three accounts, and a
    # safety-reports note by two of them; nothing from chat or mail
    assert counts_new == [2]
    names = {frozenset(br2.ci.accounts[i] for i in s) for s in sets}
    assert frozenset({"deepa.a1", "priya.a84", "wei.n2"}) in names
    assert frozenset({"priya.a84", "wei.n2"}) in names
    inv = {v: k for k, v in gen.TYPE_CODES.items()}
    win = gen.window_touches(br2.ci, br2.bdays[0], 1, "likeforlike")
    assert {inv[int(t)] for t in win.type} <= set(FROZEN_LIKE) | {"file", "repo"}
    # the all-services scope admits every amended group and nothing the amendment forbids
    # is needed to form them (on this corpus the chat and mail pairs coincide with the
    # file pair, so the distinct member sets are the same two)
    g, _ = gen.g1(br.ci, br.bdays[0], 1, "allservices", want_members=True)
    all_names = {frozenset(br.ci.accounts[i] for i in set(m)) for m in g.members if len(set(m)) >= 2}
    assert names <= all_names


def test_measure_cli_exposes_the_amendment_and_records_it():
    src = (HERE / "grouping_measure.py").read_text(encoding="utf-8")
    assert "--scope-amendment" in src and AMENDMENT in src
    assert "scope_amendment" in src.split("def measure(")[0]      # named in the module header
