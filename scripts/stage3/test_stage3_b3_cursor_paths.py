"""Tests for stage3_b3_cursor_paths.py (brief 15 A5.4, A5.13): the Cursor export's tool calls to the
trace audit's `paths` format. Synthetic records in Cursor's two shapes (stored bubbles with
`toolFormerData`, native `tool_use` blocks) on a temporary workspace; nothing from any real export.

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_b3_cursor_paths.py
"""
from __future__ import annotations

import filecmp
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import stage3_b3_cursor_paths as cp  # noqa: E402
import stage3_b3_trace_audit as ta  # noqa: E402

INPUTS = ta.DEFAULT_ALLOW


@pytest.fixture
def ws(tmp_path):
    w = tmp_path / "writer"
    for rel in INPUTS:
        (w / rel).parent.mkdir(parents=True, exist_ok=True)
        (w / rel).write_text("x\n")
    (w / "work/stage3/b3/parts").mkdir()
    for n in ("a.tmp", "b.tmp", "s.py", "x.json"):
        (w / "work/stage3/b3/parts" / n).write_text("x\n")
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / "other.md").write_text("x\n")
    return w


def _bubble(name, params=None, raw=None):
    return {"bubbleId": "b", "type": 2, "text": "", "toolFormerData": {
        "name": name, "status": "completed", "params": json.dumps(params) if params is not None else "",
        "rawArgs": json.dumps(raw) if raw is not None else None}}


def _write_jsonl(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return str(path)


def _native(name, inp):
    return {"role": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


def test_shell_paths_resolve_cd_args_redirects_and_skip_flags_numbers_patterns_and_sinks(ws):
    b3 = ws / "work/stage3/b3"
    cmd = (f"cd {b3} && cat parts/a.tmp parts/b.tmp > out.json && python3 parts/s.py 2>/dev/null; "
           "shasum -a 256 out.json; grep -n somepattern parts/a.tmp; ls -la parts")
    got = cp.shell_paths(cmd, str(ws))
    want = {str(b3), str(b3 / "parts/a.tmp"), str(b3 / "parts/b.tmp"), str(b3 / "out.json"),
            str(b3 / "parts/s.py"), str(b3 / "parts")}
    assert got == want
    assert not any(p.endswith(("/256", "/somepattern", "/-la", "/null")) for p in got)


def test_python_c_code_counts_only_existing_files_and_mkdir_mv_args_count(ws):
    cmd = (f"cd {ws} && mkdir -p scratch && mv work/stage3/b3/parts scratch/parts && "
           "python3 -c \"import json; json.load(open('work/stage3/b3/parts/x.json')); open('nope.json')\"")
    got = cp.shell_paths(cmd, "/")
    assert str(ws / "scratch") in got and str(ws / "work/stage3/b3/parts") in got and str(ws / "scratch/parts") in got
    assert str(ws / "work/stage3/b3/parts/x.json") in got                 # quoted, exists
    assert not any(p.endswith("nope.json") for p in got)                  # quoted, does not exist


def test_absolute_tokens_in_the_command_text_count(tmp_path, ws):
    other = tmp_path / "elsewhere" / "other.md"
    assert str(other) in cp.shell_paths(f"wc -l {other} | head -1", str(ws))
    assert cp.shell_paths("echo hello > /dev/null", str(ws)) == set()


def test_conversation_bubbles_by_tool(ws, tmp_path):
    spec = str(ws / INPUTS[0])
    rows = [
        {"bubbleId": "u", "type": 1, "text": "hi"},
        _bubble("read_file_v2", {"targetFile": spec, "effectiveUri": spec}, {"path": spec}),
        _bubble("edit_file_v2", {"relativeWorkspacePath": "work/stage3/b3/writer-record.md"}),
        _bubble("ripgrep_raw_search", {"path": str(ws / INPUTS[2]), "pattern": "^#"}, {"path": str(ws / INPUTS[2])}),
        _bubble("run_terminal_command_v2", {"command": "cat parts/a.tmp", "cwd": str(ws / "work/stage3/b3")}),
        _bubble("some_new_tool", {"where": str(tmp_path / "elsewhere"), "n": 3}),
    ]
    uses, tools, unknown = cp.from_conversation(_write_jsonl(tmp_path / "conv.jsonl", rows), str(ws))
    paths = {u["path"] for u in uses}
    assert paths == {spec, str(ws / "work/stage3/b3/writer-record.md"), str(ws / INPUTS[2]),
                     str(ws / "work/stage3/b3/parts/a.tmp"), str(tmp_path / "elsewhere")}
    assert tools["read_file_v2"] == 1 and tools["run_terminal_command_v2"] == 1 and unknown == ["some_new_tool"]


def test_native_uses_and_script_text(ws, tmp_path):
    other = tmp_path / "elsewhere" / "other.md"
    script = "#!/usr/bin/env python3\nimport json\nREF = '%s'\nGONE = '/no/such/file.json'\n" % other
    rows = [_native("Read", {"path": str(ws / INPUTS[1])}),
            _native("Write", {"path": str(ws / "work/stage3/b3/parts/s.py"), "contents": script}),
            _native("StrReplace", {"path": str(ws / "work/stage3/b3/parts/s.py"), "old_string": "a",
                                   "new_string": "b"}),
            _native("Shell", {"command": f"cd {ws / 'work/stage3/b3'} && python3 parts/s.py"}),
            {"type": "status", "status": "error"}]
    f = _write_jsonl(tmp_path / "native.jsonl", rows)
    uses, tools, scripts = cp.from_native(f, str(ws), script_paths=True)
    assert {u["path"] for u in uses} == {str(ws / INPUTS[1]), str(ws / "work/stage3/b3/parts/s.py"),
                                         str(ws / "work/stage3/b3")}
    assert [s["path"] for s in scripts] == [str(other)]                    # shebang and missing file skipped
    assert tools == {"Read": 1, "Write": 1, "StrReplace": 1, "Shell": 1}
    _, _, none = cp.from_native(f, str(ws), script_paths=False)
    assert none == []


def test_main_writes_paths_and_the_audit_reads_them_both_ways(ws, tmp_path):
    inputs_ws = [str(ws / r) for r in INPUTS]
    out_b3 = ws / "work/stage3/b3"
    conv = [_bubble("read_file_v2", {"targetFile": p}, {"path": p}) for p in inputs_ws]
    conv.append(_bubble("edit_file_v2", {"relativeWorkspacePath": str(out_b3 / "payloads-b3-candidates.json")}))
    nat = [_native("Read", {"path": p}) for p in inputs_ws]
    nat.append(_native("Write", {"path": str(out_b3 / "payloads-b3-candidates.json"), "contents": "{}"}))
    paths, report = tmp_path / "paths.txt", tmp_path / "report.json"
    rc = cp.main(["--conversation", _write_jsonl(tmp_path / "c.jsonl", conv),
                  "--native", _write_jsonl(tmp_path / "n.jsonl", nat), "--workspace", str(ws),
                  "--script-paths", "--out", str(paths), "--report", str(report)])
    assert rc == 0
    rep = json.loads(report.read_text())
    assert rep["cross_check"]["non_shell_paths_equal"] and rep["cross_check"]["tool_call_totals_equal"]
    res = ta.audit(ta.paths_from_list(str(paths)), str(ws), ta.DEFAULT_ALLOW)
    assert res["verdict"] == "PASS" and len(res["opened_ok"]) == 5
    res = ta.audit(ta.paths_from_list(str(paths)), str(tmp_path / "elsewhere"), ta.DEFAULT_ALLOW)
    assert res["verdict"] == "FAIL" and len(res["opened_outside"]) == 5    # the same reads, wrong folder


def test_cross_check_reports_a_path_seen_by_one_source_only(ws, tmp_path):
    p = str(ws / INPUTS[0])
    conv = [_bubble("read_file_v2", {"targetFile": p}, {"path": p})]
    nat = [_native("Read", {"path": p}), _native("Read", {"path": str(ws / INPUTS[3])})]
    report = tmp_path / "r.json"
    cp.main(["--conversation", _write_jsonl(tmp_path / "c.jsonl", conv), "--native",
             _write_jsonl(tmp_path / "n.jsonl", nat), "--workspace", str(ws), "--out", str(tmp_path / "p.txt"),
             "--report", str(report)])
    cc = json.loads(report.read_text())["cross_check"]
    assert not cc["non_shell_paths_equal"] and cc["only_in_native"] == [str(ws / INPUTS[3])]
    assert not cc["tool_call_totals_equal"]


@pytest.mark.parametrize("name", ["stage3_b3_cursor_paths.py", "test_stage3_b3_cursor_paths.py"])
def test_fork_copy_is_byte_identical(name):
    fork = HERE.parent / "mole-fork" / "scripts" / "stage3" / name
    assert fork.exists(), f"{name} has no fork copy"
    assert filecmp.cmp(HERE / name, fork, shallow=False), f"{name} differs from its fork copy"
