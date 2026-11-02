"""Tests for stage3_b3_preflight (brief 31 G4): the block is parsed strictly from plan.md, every hash is recomputed and
printed, any mismatch, missing file, differing fork copy or uncommitted plan refuses, the last block is the list, S3's
values are checked against the plan's, and the real tree passes at the hashes S1 committed.

    cd work/checks && ../mole-fork/.venv/bin/python -I -m pytest -q test_stage3_b3_preflight.py
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage3_b3_preflight as pf  # noqa: E402

CLIENT_PINS = {"work/checks/judge_client.py": "72d394e33584f7a5fe9ab638f4fc95c57ae9d0d7d0c93bf2c2d15928c4daf198",
               "work/checks/judge_openrouter.py": "e812157cb991445c12cd4c9197505b27cc03c04f1b23dbde447d417d88b71034"}


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def block(entries) -> str:
    return "```" + pf.FENCE + "\n" + "".join(f"{x}  {p}\n" for x, p in entries) + "```\n"


def make_tree(tmp_path: Path, files: dict[str, bytes], plan_text: str, commit: bool = True) -> tuple[Path, Path]:
    """A project root with the files and plan.md, and a fork git repo holding the committed plan copy."""
    root, fork = tmp_path / "root", tmp_path / "fork"
    for rel, data in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    (root / pf.PLAN).parent.mkdir(parents=True, exist_ok=True)
    (root / pf.PLAN).write_text(plan_text, encoding="utf-8")
    (fork / "scripts" / "stage3").mkdir(parents=True)
    for rel, data in files.items():
        if rel.startswith("work/checks/") and rel.endswith(".py"):
            (fork / "scripts" / "stage3" / Path(rel).name).write_bytes(data)
    subprocess.run(["git", "init", "-q", str(fork)], check=True)
    if commit:
        (fork / pf.PLAN_IN_FORK).parent.mkdir(parents=True)
        (fork / pf.PLAN_IN_FORK).write_text(plan_text, encoding="utf-8")
        subprocess.run(["git", "-C", str(fork), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(fork), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "plan"], check=True)
    return root, fork


FILES = {"work/checks/a.py": b"print(1)\n", "work/stage3/x/null.json": b'{"n": 1}\n'}


def test_parse_blocks_is_strict():
    ok = block([(h(b"a"), "work/a.py"), (h(b"b"), "work/b.json")])
    assert pf.parse_blocks("text\n" + ok + "more\n") == [(3, [(h(b"a"), "work/a.py"), (h(b"b"), "work/b.json")])]
    for bad, msg in [(block([("abc", "work/a.py")]), "not '<sha256>  <path>'"),
                     (block([(h(b"a"), "work/a.py"), (h(b"b"), "work/a.py")]), "listed twice"),
                     (block([(h(b"a"), "/abs/a.py")]), "relative"),
                     (block([(h(b"a"), "work/../a.py")]), "relative"),
                     ("```" + pf.FENCE + "\n```\n", "empty"),
                     ("```" + pf.FENCE + "\n" + h(b"a") + "  work/a.py\n", "not closed"),
                     ("no block here\n", "no " + pf.FENCE)]:
        with pytest.raises(pf.Malformed, match=re.escape(msg)):
            pf.parse_blocks(bad)


def test_all_match_passes_and_prints_every_hash(tmp_path):
    entries = [(h(v), k) for k, v in FILES.items()]
    root, fork = make_tree(tmp_path, FILES, "# plan\n" + block(entries))
    out = pf.run(root, fork, prompts=False)
    assert out["pass"] and out["n_files"] == 2 and out["plan_matches_fork_head"]
    text = "\n".join(pf.report(out))
    assert all(x in text for x, _p in entries) and text.endswith("PRE-FLIGHT PASS")


def test_a_changed_or_missing_file_refuses_and_prints_what_it_found(tmp_path):
    entries = [(h(v), k) for k, v in FILES.items()] + [(h(b"gone"), "work/stage3/missing.json")]
    root, fork = make_tree(tmp_path, FILES, block(entries))
    (root / "work/stage3/x/null.json").write_bytes(b'{"n": 2}\n')
    out = pf.run(root, fork, prompts=False)
    st = {r["path"]: r["status"] for r in out["files"]}
    assert not out["pass"] and st == {"work/checks/a.py": "OK", "work/stage3/x/null.json": "MISMATCH", "work/stage3/missing.json": "MISSING"}
    text = "\n".join(pf.report(out))
    assert h(b'{"n": 2}\n') in text and "PRE-FLIGHT REFUSED (2)" in text


def test_a_differing_fork_copy_refuses(tmp_path):
    root, fork = make_tree(tmp_path, FILES, block([(h(v), k) for k, v in FILES.items()]))
    (fork / "scripts/stage3/a.py").write_bytes(b"print(2)\n")
    out = pf.run(root, fork, prompts=False)
    assert not out["pass"] and out["refusals"] == ["FORK COPY DIFFERS: work/checks/a.py"]


def test_an_uncommitted_plan_refuses(tmp_path):
    text = block([(h(v), k) for k, v in FILES.items()])
    root, fork = make_tree(tmp_path, FILES, text)
    (root / pf.PLAN).write_text(text + "\nan edit after the commit\n", encoding="utf-8")
    out = pf.run(root, fork, prompts=False)
    assert not out["pass"] and not out["plan_matches_fork_head"] and "differs from the fork's committed" in out["refusals"][0]
    root2, fork2 = make_tree(tmp_path / "n", FILES, text, commit=False)
    assert "no committed copy found" in pf.run(root2, fork2, prompts=False)["refusals"][0]


def test_the_last_block_is_the_list(tmp_path):
    old = [(h(b"old"), "work/checks/a.py"), (h(FILES["work/stage3/x/null.json"]), "work/stage3/x/null.json")]
    new = [(h(v), k) for k, v in FILES.items()]
    root, fork = make_tree(tmp_path, FILES, block(old) + "\n## Dated note: a pin moved\n\n" + block(new))
    out = pf.run(root, fork, prompts=False)
    assert out["pass"] and out["blocks"] == 2


def test_values_against_the_plan():
    good = {**pf.PLAN_VALUES, "arm_seeds": {str(t): pf.arm_seed(t) for t in (1, 2, 3, 4)}}
    assert pf.check_values(good) == [] and pf.arm_seed(1) == 2026118110 and pf.arm_seed(4) == 2026118140
    assert pf.check_values({**good, "arm_seeds": {**good["arm_seeds"], "5": pf.arm_seed(5)}}) == []
    bad = pf.check_values({**good, "tie_seed": 1, "arm_seeds": {"1": pf.arm_seed(1), "2": 7, "3": pf.arm_seed(3), "7": 1}})
    assert bad == ["tie_seed: plan 20261112, config 1", "arm_seeds: arm 4 missing", "arm_seeds: arm 2 plan 2026118120, config 7",
                   "arm_seeds: arm 7 is not one of the plan's"]


def test_plan_values_are_the_plans_own():
    text = (pf.ROOT / pf.PLAN).read_text(encoding="utf-8")
    para = text.split("**Values the pre-flight checks against its own configuration**", 1)[1].split("\n\n", 1)[0]
    assert "placement seed 20261181" in para and "20261181 × 100 + 10 t for t = 1 to 4 (5 and 6 only if approved at S2" in para
    assert "bootstrap seed 20261152 with 2,000 replicates" in para and "tie seed 20261112" in para
    assert "m_s 18.22 (carrier) and 19.37 (second named instrument), with m_L 18.22" in para


def test_the_real_plan_lists_24_files_with_both_client_pins():
    blocks = pf.parse_blocks((pf.ROOT / pf.PLAN).read_text(encoding="utf-8"))
    entries = dict((p, x) for x, p in blocks[-1][1])
    # 2026-11-02, plan.md's post-S2 dated note (brief 32 plan-note direction 13ab9943): the restated block has 26 entries.
    # 2026-11-02, plan.md's dated note 3 (brief 33's dated note 2, G1 revised): 27 entries, work/stage3/views/p_author_c0.json (3c61dd4d) pinned.
    assert len(entries) == 27 and all(entries[p] == x for p, x in CLIENT_PINS.items())
    assert {"work/stage3/b3/inserter-dry-run-v1.json", "work/checks/stage3_b3_inserter_dry_run_v1.py"} <= set(entries)
    assert entries["work/stage3/views/p_author_c0.json"].startswith("3c61dd4d")


def test_the_real_tree_passes_the_pre_flight():
    """Fails when a pinned file changes without a dated note moving its pin (brief 31's rule)."""
    out = pf.run()
    assert out["pass"], out["refusals"]
    assert [r["status"] for r in out["prompts"]] == ["OK", "OK", "OK"]
