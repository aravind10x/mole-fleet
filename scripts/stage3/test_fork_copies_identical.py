"""Every Stage 3 brief-07f script and test in work/checks has a byte-identical copy in the fork's
scripts/stage3 (the fork is what is committed and pushed; the canonical copies live here)."""
from __future__ import annotations

import filecmp
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FORK = HERE.parent / "mole-fork" / "scripts" / "stage3"
FILES = ["stage3_views.py", "test_stage3_views.py", "stage3_thresholds.py", "test_stage3_thresholds.py",
         "stage3_t1.py", "test_stage3_t1.py", "stage3_t1_score.py", "test_stage3_t1_score.py",
         "stage3_views_seal.py", "score_fork_corpus.py", "score_o_composed.py", "test_score_o_composed.py",
         "test_scope_amendment_f26.py", "test_fork_copies_identical.py",
         "stage3_t1v2_checks.py", "test_stage3_t1v2_checks.py", "stage3_t1v2_score.py", "test_stage3_t1v2_score.py", "stage3_t1v2_row3_material.py",
         "stage3_synthetic_q1q2.py", "test_stage3_synthetic_q1q2.py", "judge_opus_q1q2.py", "test_judge_client_opus.py", "judge_openrouter.py", "test_judge_openrouter.py", "judge_dep_q1q2.py", "stage3_rater_strip.py", "test_stage3_rater_strip.py",
         "stage3_t1v3_score.py", "test_stage3_t1v3_score.py", "stage3_t1v3_write.py", "test_stage3_t1v3_checks.py",
         "stage3_t1replant_score.py", "test_stage3_t1replant_score.py",
         "judge_extra.py", "test_judge_extra.py",
         "stage3_b0.py", "test_stage3_b0.py",
         "stage3_rater_join_07s.py", "test_stage3_rater_join_07s.py",
         "stage3_author_doc.py", "test_stage3_author_doc.py", "stage3_b1_dossier.py", "test_stage3_b1_dossier.py",
         "stage3_b4r_design.py", "stage3_b4r.py", "stage3_b4r_views.py", "test_stage3_b4r.py", "stage3_rung1_class.py", "stage3_b4r_rehearsal_check.py",
         "stage3_pilot_live_check.py", "test_stage3_pilot_live_check.py", "stage3_rater_pilot.py", "test_stage3_rater_pilot.py",
         "stage3_pilot_footprint.py", "test_stage3_pilot_footprint.py",
         "test_judge_client_converse.py", "stage3_sol_provider_check.py", "test_stage3_sol_provider_check.py", "judge_client.py",
         "stage3_pilot_archive.py", "test_stage3_pilot_archive.py"]


@pytest.mark.parametrize("name", FILES)
def test_fork_copy_is_byte_identical(name):
    assert (FORK / name).exists(), f"{name} has no fork copy"
    assert filecmp.cmp(HERE / name, FORK / name, shallow=False), f"{name} differs from its fork copy"
