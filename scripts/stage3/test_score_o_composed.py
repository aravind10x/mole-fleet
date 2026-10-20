"""Offline tests for score_o_composed.py (no network: the Bedrock client inside JudgeClient is a
fake) and for score_fork_corpus.py's --whole-key flag (P and O see the same document text).

Synthetic corpus: a routine shared README on ownCloud edited by three accounts over two days
(placeholder edits only). Prefix checks read work/mole-fork/data/corpus/spike/prefix_v1.jsonl
and its managers snapshots (read only).

Run: cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_score_o_composed.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from anthropic.types import Message, RefusalStopDetails, TextBlock, Usage  # noqa: E402

import judge_client as jcm  # noqa: E402
import score_fork_corpus as sfc  # noqa: E402
import score_o_composed as soc  # noqa: E402
from mole.oracles import document as doc  # noqa: E402

MODEL = "anthropic.claude-sonnet-5"
SLUG = "anthropic-claude-sonnet-5"
PREFIX = jcm.FORK / "data" / "corpus" / "spike" / "prefix_v1.jsonl"
D1, D2 = "2026-04-06", "2026-04-07"
README = "/shared/README.md"
NOTES = "/shared/notes.md"
V1 = "# Team README\n\nSetup steps are in the wiki.\n"
V2 = V1 + "Today's date: 2026-04-06.\n"
V3 = V2 + "Reviewed the setup steps; no changes needed.\n"
LONG = "".join(f"Step {i}: follow the routine setup checklist item {i}.\n" for i in range(250))
LOW = '{"score": 4, "flag": false, "rationale": "Routine notes."}'
REFUSAL = RefusalStopDetails(type="refusal", category="cyber", explanation="classifier")


def ev(i, ts, account, path, content, code=0):
    return {"event_id": f"e{i}", "ts": ts, "account": account, "service": "owncloud",
            "action": "write_file", "resource_id": path,
            "args": {"path": path, "content": content}, "exit_code": code, "result_meta": {},
            "is_malicious": True, "task_id": "t"}          # never read by the scorer


EVENTS = [
    ev(0, f"{D1}T09:00:00Z", "ana.b", README, V1),
    ev(1, f"{D1}T10:00:00Z", "ben.c", README, V2),
    ev(2, f"{D1}T11:00:00Z", "ana.b", NOTES, "notes v1\n"),
    ev(3, f"{D2}T09:00:00Z", "cy.d", README, V3),
    ev(4, f"{D2}T10:00:00Z", "ana.b", README, V3),             # same content again
    ev(5, f"{D2}T11:00:00Z", "ben.c", README, "broken", code=1),
    ev(6, f"{D2}T12:00:00Z", "ben.c", "/shared/long.md", LONG),
    {"event_id": "e7", "ts": f"{D2}T13:00:00Z", "account": "cy.d", "service": "owncloud",
     "action": "read_file", "resource_id": README, "args": {"path": README}, "exit_code": 0},
]


@pytest.fixture()
def corpus(tmp_path) -> Path:
    p = tmp_path / "synth_docs.jsonl"
    p.write_text("".join(json.dumps(e) + "\n" for e in EVENTS), encoding="utf-8")
    return p


# ── fake Bedrock client ──────────────────────────────────────────────

def msg(text=None, *, stop_reason="end_turn", stop_details=None, inp=1000, out=40):
    content = [] if text is None else [TextBlock(type="text", text=text)]
    return Message(id="m", type="message", role="assistant", content=content, model=MODEL,
                   stop_reason=stop_reason, stop_sequence=None, stop_details=stop_details,
                   usage=Usage(input_tokens=inp, output_tokens=out))


class FakeMessages:
    """long.md -> refusal; otherwise a score that depends on the document."""

    def __init__(self):
        self.calls: list[dict] = []

    async def create(self, **kw):
        self.calls.append(kw)
        pk = kw["messages"][0]["content"]
        if "long.md" in pk:
            return msg("", stop_reason="refusal", stop_details=REFUSAL, inp=len(pk) // 2)
        score = 60 if "notes.md" in pk else 4
        return msg(LOW.replace('"score": 4', f'"score": {score}'), inp=len(pk) // 2)


class Fake:
    def __init__(self):
        self.messages = FakeMessages()


async def no_sleep(_s):
    return None


def factory(fake):
    def make(**kw):
        return jcm.JudgeClient(region="us-east-1", client=fake, sleep=no_sleep, verbose=False, **kw)
    return make


def ns_for(corpus: Path, out_dir: Path, *extra):
    return soc.build_parser().parse_args(
        ["--corpus", str(corpus), "--out", str(out_dir / "o.json"),
         "--cache", str(out_dir / f"judge-cache.ocomp.{SLUG}.jsonl"), "--model", MODEL,
         "--date", D2, "--rpm", "1000", *extra])


def run(ns, fake):
    return asyncio.run(soc.amain(ns, client_factory=factory(fake)))


# ── selection and packets ────────────────────────────────────────────

def test_top_writer_docs(corpus):
    rows, _ = sfc.read_jsonl(corpus)
    top = soc.top_writer_docs(rows, "owncloud", D2, 5)
    assert top == [{"doc": f"owncloud:{README}", "n_writers": 2, "n_writes": 2},
                   {"doc": "owncloud:/shared/long.md", "n_writers": 1, "n_writes": 1}]
    assert soc.top_writer_docs(rows, "owncloud", D1, 1)[0]["n_writers"] == 2


def test_whole_and_diff_packets(corpus):
    rows, _ = sfc.read_jsonl(corpus)
    docs = [{"doc": f"owncloud:{README}"}, {"doc": f"owncloud:{NOTES}"}]
    whole = soc.build_items(corpus, rows, docs, "whole", D2, None)
    pk = whole[0]["packet"]
    assert pk.startswith(soc.O_COMPOSED_INTRO_WHOLE)
    assert pk.endswith(V3) and f"Document: owncloud:{README}" in pk and "end of 2026-04-07" in pk
    assert whole[0]["label"] == f"synth_docs:Ocomp:owncloud:{README}/{D2}"
    assert whole[0]["source"] == "log" and not whole[0]["truncated"]
    diff = soc.build_items(corpus, rows, docs, "diff", D2, D1)
    d = diff[0]["packet"]
    assert d.startswith(soc.O_COMPOSED_INTRO_DIFF)
    assert "+Reviewed the setup steps; no changes needed.\n" in d
    assert "Setup steps are in the wiki" in d                     # context line only
    assert diff[0]["label"] == f"synth_docs:Ocomp:owncloud:{README}/{D1}..{D2}"
    assert diff[1]["skip"] == "unchanged" and diff[1]["packet"] is None
    # the packet carries no secret, no oracle output, no label, no writer list
    for it in whole + diff:
        for txt in filter(None, [it["packet"]]):
            for s in ("is_malicious", "ana.b", "ben.c", "cy.d", "oracle", "secret"):
                assert s not in txt
    absent = soc.build_items(corpus, rows, [{"doc": "owncloud:/nope.md"}], "whole", D2, None)
    assert absent[0]["skip"] == soc.UNKNOWN_SKIP == "unknown (seeded outside the log, no base)"
    # first written on day 2, so its day-1 state is unknown from the log alone: no diff
    late = soc.build_items(corpus, rows, [{"doc": "owncloud:/shared/long.md"}], "diff", D2, D1)
    assert late[0]["skip"] == soc.UNKNOWN_SKIP and late[0]["packet"] is None
    assert late[0]["since_chars"] is None and late[0]["content_chars"] == len(LONG)


def test_dry_run_writes_nothing(corpus, tmp_path, capsys):
    out_dir = tmp_path / "o"
    ns = ns_for(corpus, out_dir, "--service", "owncloud", "--top-writers", "3", "--dry-run")
    assert run(ns, Fake()) == 0
    cap = capsys.readouterr().out
    assert soc.O_COMPOSED_INTRO_WHOLE in cap
    summary = json.loads(cap.strip().splitlines()[-1])
    assert summary["n_calls"] == 2 and summary["est_output_tokens"] == 2 * 230
    assert not out_dir.exists()


def test_full_run_outcomes_summary_and_resume(corpus, tmp_path):
    fake = Fake()
    args = ("--doc", f"owncloud:{README}", "--doc", f"owncloud:{NOTES}",
            "--doc", "owncloud:/shared/long.md", "--doc", "owncloud:/nope.md")
    assert run(ns_for(corpus, tmp_path, *args), fake) == 0
    assert len(fake.messages.calls) == 3 + 1                       # long.md refused, re-asked once
    call = fake.messages.calls[0]
    assert call["system"] == jcm.JUDGE_SYSTEM and call["max_tokens"] == jcm.MAX_TOKENS
    assert "temperature" not in call
    res = json.loads((tmp_path / "o.json").read_text())
    by = {r["doc"]: r for r in res["rows"]}
    assert by[f"owncloud:{README}"]["outcome"] == "scored" and by[f"owncloud:{README}"]["score"] == 4
    assert by[f"owncloud:{NOTES}"]["score"] == 60
    assert by["owncloud:/shared/long.md"]["outcome"] == "refused"
    assert by["owncloud:/nope.md"]["outcome"] == "skipped"
    s = res["summary"]
    assert s["by_outcome"] == {"scored": 2, "refused": 1, "errored": 0, "skipped": 1, "missing": 0}
    assert (s["min"], s["median"], s["max"], s["n_ge_50"]) == (4.0, 32.0, 60.0, 1)
    assert res["meta"]["view"] == "Ocomp" and res["meta"]["intro_version"] == soc.INTRO_VERSION
    cache = tmp_path / f"judge-cache.ocomp.{SLUG}.jsonl"
    labels = {json.loads(l)["label"] for l in cache.read_text().splitlines()}
    assert f"synth_docs:Ocomp:owncloud:{README}/{D2}" in labels
    fake2 = Fake()                                                 # rerun: all from the cache
    assert run(ns_for(corpus, tmp_path, *args), fake2) == 0 and fake2.messages.calls == []
    assert json.loads((tmp_path / "o.json").read_text())["rows"] == res["rows"]


def test_argument_guards(corpus, tmp_path):
    with pytest.raises(SystemExit, match="--since"):
        run(ns_for(corpus, tmp_path, "--doc", f"owncloud:{README}", "--mode", "diff"), Fake())
    with pytest.raises(SystemExit, match="either --doc"):
        run(ns_for(corpus, tmp_path), Fake())
    ns = ns_for(corpus, tmp_path, "--doc", f"owncloud:{README}")
    ns.cache = str(tmp_path / "judge-cache.jsonl")
    with pytest.raises(SystemExit, match="does not carry"):
        run(ns, Fake())


# ── P and O see the same document text (--whole-key) ─────────────────

def test_whole_key_gives_p_the_same_text_as_o(corpus):
    rows, _ = sfc.read_jsonl(corpus)
    assert len(LONG) > 10_000
    keys, day_idx, by_key = sfc.account_days(rows)
    k = [("ben.c", D2)]
    capped = sfc.build_items("synth_docs", k, day_idx, by_key)[0]["packet"]
    whole = sfc.build_items("synth_docs", k, day_idx, by_key, whole_keys=["content"])[0]["packet"]
    esc = json.dumps(LONG, ensure_ascii=False)[1:-1]               # as rendered in the args JSON
    assert esc in whole and esc not in capped and "chars]" in capped
    o = soc.build_items(corpus, rows, [{"doc": "owncloud:/shared/long.md"}], "whole", D2, None)
    assert o[0]["packet"].endswith(LONG)
    # the flag reaches build_items from the CLI and the default packets are unchanged
    p = sfc.build_parser()
    assert p.parse_args(["--corpus", "c", "--out", "o", "--cache", "x", "--whole-key", "content",
                         "--whole-key", "body"]).whole_key == ["content", "body"]
    assert p.parse_args(["--corpus", "c", "--out", "o", "--cache", "x"]).whole_key == []
    assert sfc.build_items("synth_docs", k, day_idx, by_key, whole_keys=[])[0]["packet"] == capped


# ── the honest prefix: snapshot and log readings agree ───────────────

@pytest.mark.skipif(not (PREFIX.exists() and doc.managers_path(PREFIX, D2).exists()),
                    reason="honest prefix not on disk")
def test_prefix_top10_plane_snapshot_equals_log():
    rows, _ = sfc.read_jsonl(PREFIX)
    docs = soc.top_writer_docs(rows, "plane", D2, 10)
    assert len(docs) == 10 and all(d["n_writers"] >= 4 for d in docs)
    for d in docs:                                # all created inside the log
        assert doc.content_writes(rows, doc.parse_doc_id(d["doc"]), until=D2)[0].action == \
            "create_issue"
    for mode, since in (("whole", None), ("diff", D1)):
        snap = soc.build_items(PREFIX, rows, docs, mode, D2, since, "snapshot")
        log = soc.build_items(PREFIX, rows, docs, mode, D2, since, "log")
        for a, b in zip(snap, log):
            assert (a["source"], b["source"]) == ("snapshot", "log")
            assert a["skip"] is None, (mode, a["doc"])
            if mode == "diff" and a["since_chars"] is None:
                # created on day 2: the snapshot says absent on day 1 (whole-document additions);
                # the log alone cannot tell absent from seeded, so it skips as unknown
                assert b["skip"] == soc.UNKNOWN_SKIP, a["doc"]
            else:
                assert a["packet"] == b["packet"], (mode, a["doc"])
