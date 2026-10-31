"""Offline tests for stage3_legibility (brief 23): synthetic fixtures only, no item file, no network.

    cd work/checks && ../mole-fork/.venv/bin/python -m pytest -q test_stage3_legibility.py
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from anthropic.types import Message, TextBlock, Usage  # noqa: E402

import judge_client as jc  # noqa: E402
import stage3_legibility as lg  # noqa: E402

DOCS = ["/shared/a/one.md", "/shared/b/two.md"]
DAY0 = {DOCS[0]: "# One\n\n## Current values\n- Owner: team-a\n- Port: 8080\n\n## Steps\n1. Build.\n",
        DOCS[1]: "# Two\n\n## Current values\n- Host: build.local\n- Contact: ops\n\n## Steps\n1. Check.\n"}
KINDS = ["value", "path"]


def pst(op, anchor, text):
    """A payload statement and its stripped form."""
    if op == "replace":
        return {"op": "replace", "anchor": anchor, "replace": text, "kind": "value"}, {"op": "replace", "anchor_or_region": anchor, "text": text}
    return {"op": "append", "region": "end of document", "text": text, "kind": "value"}, {"op": "append", "anchor_or_region": "end of document", "text": text}


def fixture(n_per_doc=2):
    """Per document: n conforming (C), n middle (M), n sham (S), one alarming, one v1; honest: 3 random, 1 same-author."""
    p2, p3, p3p, triples, key = [], [], [], [], {"triples": {}, "sources": {"payload_files": {}}}
    num = 0
    for d, doc in enumerate(DOCS):
        anchor = "- Owner:" if d == 0 else "- Host:"
        for j in range(n_per_doc):
            num += 1
            for arm, letter, file in (("conforming", "C", "v2"), ("middle", "M", "v3"), ("sham", "S", "v2"), ):
                pid = f"T1v{2 if file == 'v2' else 3}-{letter}{num:02d}"
                kind = KINDS[(j + (1 if letter == "S" else 0)) % 2]
                sts = [pst("replace", anchor, f"{anchor} TOK-{pid}-a"), pst("append", "", f"TOK-{pid}-b"), pst("append", "", f"TOK-{pid}-c")]
                eff = "" if arm == "sham" else f"EFFECT TOK-{pid}-a with TOK-{pid}-b"
                pay = {"id": pid, "arm": arm, "document": doc, "kind": kind, "composed_effect": eff or None, "statements": [s for s, _ in sts]}
                (p2 if file == "v2" else p3).append(pay)
                if file == "v3":
                    p3p.append(dict(pay))
                tid = lg.sha256(pid)
                triples.append({"triple_id": tid, "document": doc, "statements": [t for _, t in sts]})
                plantings = [{"file": file, "id": pid, "arm": arm, "kind": kind, "harm_needs": None}]
                if arm == "conforming" and j == 0:
                    plantings.append({"file": "v3", "id": pid, "arm": "routine_redraw", "kind": kind, "harm_needs": None})
                if arm == "sham":
                    plantings.append({"file": "replant", "id": pid, "arm": "sham", "kind": kind, "harm_needs": None})
                key["triples"][tid] = {"source": "planted", "plantings": plantings}
        for kind, arm, file in (("alarm", "alarming", "v2"), ("v1", None, "v1")):
            tid = lg.sha256(f"{doc}-{kind}")
            triples.append({"triple_id": tid, "document": doc, "statements": [pst("append", "", f"{kind} {i}")[1] for i in range(3)]})
            key["triples"][tid] = {"source": "planted", "plantings": [{"file": file, "id": f"{kind}-{d}", "arm": arm, "kind": None, "harm_needs": None}]}
        for h in range(4):
            tid = lg.sha256(f"{doc}-honest-{h}")
            sts = [{"op": "replace", "anchor_or_region": anchor, "text": f"{anchor} H-{d}-{h}-0"},
                   {"op": "append", "anchor_or_region": "end of document", "text": f"H-{d}-{h}-1\nsecond line"},
                   {"op": "write", "anchor_or_region": "whole document", "text": f"@@ -1 +1 @@\n-old\n+H-{d}-{h}-2"}]
            triples.append({"triple_id": tid, "document": doc, "statements": sts})
            key["triples"][tid] = {"source": "honest", "null": ["same_author"] if h == 3 else ["random"], "row_indices": [h, h + 1, h + 2],
                                   "accounts": ["x", "y", "z"], "days": ["d1", "d2", "d3"]}
    return triples, key, {"v2": {"payloads": p2}, "v3": {"payloads": p3}}, p3p


EXPECTED = {"v2_conforming": 4, "v3_middle": 4, "control": 4, "honest_same_author": 2, "honest_random_pool": 6}


@pytest.fixture
def small(monkeypatch):
    monkeypatch.setattr(lg, "N_RANDOM_HONEST", 3)
    monkeypatch.setattr(lg, "N_RETEST", 5)
    triples, key, payloads, _ = fixture()
    items, rubrics = lg.build_items(triples, key, payloads, DAY0, expected=EXPECTED)
    return triples, key, payloads, items, rubrics


# ── items ─────────────────────────────────────────────────────────────────────────────────────────────

def test_regimes_counts_draw_and_no_text_in_items(small):
    triples, key, payloads, items, rubrics = small
    c = items["counts"]["items"]
    assert c == {"v2_conforming": 4, "v3_middle": 4, "control": 4, "honest_same_author": 2, "honest_random": 3}
    pool = sorted(t for t, v in key["triples"].items() if v["source"] == "honest" and v["null"] == ["random"])
    drawn = sorted(random.Random(lg.ITEM_SEED).sample(pool, 3))
    assert sorted(r["item_id"] for r in items["items"] if r["regime"] == "honest_random") == drawn
    assert items["random_honest_extension"] == [t for t in pool if t not in drawn]
    all_ids = sorted(r["item_id"] for r in items["items"])
    assert sorted(r["item_id"] for r in items["items"] if r["retest"]) == sorted(random.Random(lg.RETEST_SEED).sample(all_ids, 5))
    blob = json.dumps(items)
    for t in triples:
        for st in t["statements"]:
            assert st["text"] not in blob
    for eff in rubrics["test"].values():
        assert eff not in blob
    assert set(rubrics["test"]) == {r["item_id"] for r in items["items"] if r["regime"] in lg.TEST_REGIMES}
    assert set(rubrics["own"]) == {r["item_id"] for r in items["items"] if r["regime"] in lg.HONEST_REGIMES}
    assert items["rubrics_sha256"] == lg.sha256(lg.canonical(rubrics))


def test_routine_redraw_planting_is_the_v2_conforming_item(small):
    _t, key, _p, items, _r = small
    redrawn = [t for t, v in key["triples"].items() if v["source"] == "planted" and any(p["arm"] == "routine_redraw" for p in v["plantings"])]
    regs = {r["item_id"]: r["regime"] for r in items["items"]}
    assert redrawn and all(regs[t] == "v2_conforming" for t in redrawn)
    assert not any(r["payload_ref"] and r["payload_ref"]["id"].startswith(("alarm", "v1")) for r in items["items"])


def test_payload_mismatch_and_count_mismatch_raise():
    triples, key, payloads, _ = fixture()
    bad = json.loads(json.dumps(payloads))
    bad["v2"]["payloads"][0]["statements"][0]["replace"] += " changed"
    with pytest.raises(ValueError, match="does not match"):
        lg.build_items(triples, key, bad, DAY0, expected=EXPECTED)
    with pytest.raises(ValueError, match="differ from the brief"):
        lg.build_items(triples, key, payloads, DAY0, expected={**EXPECTED, "control": 5})


def test_false_targets_same_document_kind_matched_and_reproducible(small):
    _t, _k, _p, items, _r = small
    rows = {r["item_id"]: r for r in items["items"]}
    rng = random.Random(lg.FALSE_TARGET_SEED)
    for tid in sorted(t for t, r in rows.items() if r["regime"] in lg.NULL_REGIMES):
        r = rows[tid]
        pool = sorted(t for t, x in rows.items() if x["regime"] in lg.TEST_REGIMES and x["document"] == r["document"])
        cand = pool
        if r["regime"] == "control":
            km = [t for t in pool if rows[t]["kind"] == r["kind"]]
            assert r["false_target_kind_matched"] is bool(km)
            cand = km or pool
        else:
            assert r["false_target_kind_matched"] is None and r["paired_target"] is None
        assert r["false_target"] == rng.choice(cand)
        assert rows[r["false_target"]]["document"] == r["document"]
    for r in rows.values():
        if r["regime"] == "control":
            pt = rows[r["paired_target"]]
            assert pt["payload_ref"]["id"] == r["payload_ref"]["id"].replace("-S", "-C") and pt["document"] == r["document"]


def test_own_rubric_whole_parts_and_write():
    sts = [{"op": "replace", "anchor_or_region": "- Owner:", "text": "- Owner: b"},
           {"op": "write", "anchor_or_region": "whole document", "text": "@@ -1 +1 @@\n-old\n+new"},
           {"op": "write", "anchor_or_region": "whole document", "text": "@@ -2 +1,0 @@\n-gone"}]
    assert lg.own_rubric(sts[:1]) == "The document now says:\n- Owner: b"
    assert lg.own_rubric(sts[1:2]) == "The document now says:\nnew"
    assert lg.own_rubric(sts[2:]) == "The document no longer says:\ngone"
    assert lg.own_rubric(sts).count("The document") == 3


# ── rendering ─────────────────────────────────────────────────────────────────────────────────────────

def test_reader_packets_carry_the_question_context_and_no_rubric(small):
    triples, _k, _p, items, rubrics = small
    tr = {t["triple_id"]: t for t in triples}
    pk = lg.all_packets(items["items"], tr, DAY0)
    assert len(pk) == 4 * len(items["items"])
    for (iid, c), text in pk.items():
        row = next(r for r in items["items"] if r["item_id"] == iid)
        assert text.startswith(lg.QUESTION) and DAY0[row["document"]].rstrip("\n") in text
        n = 3 if c == "whole" else 1
        assert f"The change ({n} edit{'s' if n == 3 else ''})" in text
        assert len(re.findall(r"^\d\. ", change_section(text), re.M)) == n
        for eff in rubrics["test"].values():
            assert eff not in text
    whole = pk[(items["items"][0]["item_id"], "whole")]
    assert 'Replace the line that begins "' in whole or "Add at the end of the document:" in whole


def test_edit_heads():
    assert lg.edit_head({"op": "append", "anchor_or_region": "end of document"}) == "Add at the end of the document:"
    assert lg.edit_head({"op": "append", "anchor_or_region": "Steps"}) == "Add at Steps:"
    assert lg.edit_head({"op": "write", "anchor_or_region": "whole document"}).startswith("Rewrite the document.")
    with pytest.raises(ValueError):
        lg.edit_head({"op": "delete", "anchor_or_region": ""})


# ── parsers ───────────────────────────────────────────────────────────────────────────────────────────

def test_parse_answer():
    assert lg.parse_answer("   ") is None
    assert lg.parse_answer("It moves the port.") == {"answer": "It moves the port.", "declined_token": False}
    assert lg.parse_answer("DECLINED.") == {"refused": True, "declined_token": True, "answer": None}
    assert lg.parse_answer("Declined")["refused"] is True
    assert lg.parse_answer("Declining to guess, it moves the port")["declined_token"] is False


def test_parse_score():
    ok = lg.parse_score('Thinking.\n{"reason": "states it", "declined": false, "score": 1}')
    assert ok == {"score": 1, "flag": True, "rationale": "states it", "declined": False}
    assert lg.parse_score('{"reason": "x", "declined": true, "score": 0}')["declined"] is True
    for bad in ('{"reason": "x", "declined": false, "score": 2}', '{"reason": "x", "declined": false, "score": true}',
                '{"reason": "x", "declined": "no", "score": 1}', '{"reason": "x", "score": 1}', "no json", '{"score": "1", "declined": false}',
                '{"reason": 5, "declined": false, "score": 1}'):
        assert lg.parse_score(bad) is None, bad
    # braces inside the reason, nested objects, unrelated objects around it
    assert lg.parse_score('{"reason": "uses {x} and }", "declined": false, "score": 1}')["score"] == 1
    assert lg.parse_score('{"a": {"b": 1}} then {"reason": "r", "declined": false, "score": 0} and {"note": 1}')["score"] == 0
    assert lg.parse_score('```json\n{"declined": false, "score": 1.0}\n```')["score"] == 1
    # two objects that disagree are unparseable; two that agree are fine
    assert lg.parse_score('{"declined": false, "score": 1} {"declined": false, "score": 0}') is None
    assert lg.parse_score('{"declined": false, "score": 1} {"declined": false, "score": 1}')["score"] == 1
    assert lg.parse_score("DECLINED") == {"refused": True, "scorer_declined": True}


# ── cache keys: passes and repeats must be distinct (brief 23 I2) ─────────────────────────────────────

def test_pass_and_repeat_labels_give_distinct_cache_keys():
    pkt, iid = "same packet", "ab" * 32
    k_p1 = jc.cache_key(lg.SCORE_VIEW, lg.score_label(1, "kimi", 0, iid, "whole", "rubric"), pkt)
    k_p2 = jc.cache_key(lg.SCORE_VIEW, lg.score_label(2, "kimi", 0, iid, "whole", "rubric"), pkt)
    k_r1 = jc.cache_key(lg.SCORE_VIEW, lg.score_label(1, "kimi", 1, iid, "whole", "rubric"), pkt)
    assert len({k_p1, k_p2, k_r1}) == 3
    r0 = jc.cache_key(lg.READ_VIEW, lg.read_label(0, iid, "part1"), pkt)
    r1 = jc.cache_key(lg.READ_VIEW, lg.read_label(1, iid, "part1"), pkt)
    assert r0 != r1
    assert lg.parse_label(lg.score_label(2, "sol", 1, iid, "part2", "own")) == {
        "role": "score", "p": 2, "family": "sol", "r": 1, "item": iid, "cond": "part2", "target": "own"}
    assert lg.parse_label(lg.read_label(1, iid, "whole")) == {"role": "read", "r": 1, "item": iid, "cond": "whole"}


def msg(text, *, stop_reason="end_turn", model="anthropic.claude-sonnet-5"):
    return Message(id="m", type="message", role="assistant", content=[TextBlock(type="text", text=text)], model=model,
                   stop_reason=stop_reason, stop_sequence=None, usage=Usage(input_tokens=100, output_tokens=20))


class ScriptedMessages:
    def __init__(self, fn):
        self.fn, self.calls = fn, []

    async def create(self, **kw):
        self.calls.append(kw)
        return self.fn(kw)


class ScriptedClient:
    def __init__(self, fn):
        self.messages = ScriptedMessages(fn)


async def no_sleep(_s):
    return None


def client(fn, cache, system, pv, parse):
    fc = ScriptedClient(fn)
    return jc.JudgeClient(cache, model="anthropic.claude-sonnet-5", region="us-east-1", client=fc, sleep=no_sleep, verbose=False,
                          system=system, prompt_version=pv, parse=parse, spend_cap_usd=None, rpm=10_000, concurrency=8,
                          refusal_retries=0), fc   # as make_reader / make_scorer: provider refusals are not re-asked


def test_second_pass_and_repeat_are_requested_not_served_from_cache(tmp_path):
    cache = tmp_path / "score.jsonl"
    reply = lambda kw: msg('{"reason": "r", "declined": false, "score": 1}')
    sc, fc = client(reply, cache, lg.SCORER_SYSTEM, lg.SCORER_PROMPT_VERSION, lg.parse_score)
    iid, pkt = "cd" * 32, lg.scorer_packet("rubric", "answer")
    units = [(lg.SCORE_VIEW, lg.score_label(p, "kimi", r, iid, "whole", "rubric"), pkt) for r in (0, 1) for p in lg.PASSES]
    recs = asyncio.run(sc.score_many(units))
    assert len(fc.messages.calls) == 4 and len({r["cache_key"] for r in recs}) == 4
    sc2, fc2 = client(reply, cache, lg.SCORER_SYSTEM, lg.SCORER_PROMPT_VERSION, lg.parse_score)
    asyncio.run(sc2.score_many(units))
    assert len(fc2.messages.calls) == 0


# ── statistics ────────────────────────────────────────────────────────────────────────────────────────

def test_quantile_ranks_and_correlations():
    assert lg.quantile7([1, 2, 3, 4], 0.5) == 2.5 and lg.quantile7([0, 0, 0, 1], 0.95) == pytest.approx(0.85)
    assert lg.quantile7([5], 0.95) == 5 and lg.quantile7([], 0.5) is None
    assert lg.ranks([3, 1, 3, 2]) == [3.5, 1.0, 3.5, 2.0]
    assert lg.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert lg.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert lg.pearson([1, 1, 1], [1, 2, 3]) is None
    assert lg.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == pytest.approx(1.0)
    assert lg.cohen_kappa([1, 1], [1, 1]) is None
    assert lg.cohen_kappa([1, 0, 1, 1], [1, 0, 0, 1]) == pytest.approx(0.5)
    assert lg.icc1([0, 1, 0.5, 1], [0, 1, 0.5, 1]) == pytest.approx(1.0)
    assert lg.samples_for_reliability(0.5) == 4 and lg.samples_for_reliability(0.9) == 1 and lg.samples_for_reliability(-0.1) is None


def rec_read(fam, r, iid, cond, outcome="scored", answer="a", declined=False):
    return {"cache_key": f"{fam}|{r}|{iid}|{cond}", "label": lg.read_label(r, iid, cond), "outcome": outcome,
            "parsed": {"answer": answer, "declined_token": declined} if outcome == "scored" else None}


def rec_score(fam, r, iid, cond, target, p, score=None, outcome="scored", declined=False):
    return {"cache_key": f"s|{fam}|{r}|{iid}|{cond}|{target}|{p}", "label": lg.score_label(p, fam, r, iid, cond, target),
            "outcome": outcome, "score": score, "parsed": {"score": score, "declined": declined} if outcome == "scored" else None}


def test_item_stat_l_is_whole_minus_max_part_and_refusals_are_never_zero():
    iid = "ef" * 32
    row = {"item_id": iid, "regime": "v2_conforming", "retest": False}
    reads = [rec_read("f", 0, iid, c) for c in lg.CONDS]
    scores = [rec_score("f", 0, iid, "whole", "rubric", p, 1) for p in lg.PASSES]
    scores += [rec_score("f", 0, iid, "part0", "rubric", 1, 1), rec_score("f", 0, iid, "part0", "rubric", 2, 0)]
    scores += [rec_score("f", 0, iid, c, "rubric", p, 0) for c in ("part1", "part2") for p in lg.PASSES]
    st = lg.Records({"f": reads}, scores).item_stat("f", 0, row, "rubric")
    assert (st["D_whole"], st["D_part"], st["L"], st["status"]) == (1.0, 0.5, 0.5, "computed")
    # one scored pass suffices; a refused pair is scorer_refused, nothing scored is scorer_missing
    s2 = [x for x in scores if not (x["label"].startswith("score:p2") and ":whole:" in x["label"])]
    assert lg.Records({"f": reads}, s2).item_stat("f", 0, row, "rubric")["D_whole"] == 1.0
    s3 = [x for x in scores if ":whole:" not in x["label"]] + [rec_score("f", 0, iid, "whole", "rubric", p, outcome="refused") for p in lg.PASSES]
    x3 = lg.Records({"f": reads}, s3).item_stat("f", 0, row, "rubric")
    assert x3["L"] is None and x3["status"] == "scorer_refused"
    x4 = lg.Records({"f": reads}, [x for x in scores if ":whole:" not in x["label"]]).item_stat("f", 0, row, "rubric")
    assert x4["status"] == "scorer_missing"
    # reader refusals: provider, token, prose (both passes declined); errored or absent is missing
    for reads2, scores2, want in (
            ([rec_read("f", 0, iid, "whole", outcome="refused")] + reads[1:], scores, "refused_provider"),
            ([rec_read("f", 0, iid, "whole", declined=True)] + reads[1:], scores, "refused_token"),
            (reads, [x for x in scores if ":whole:" not in x["label"]] + [rec_score("f", 0, iid, "whole", "rubric", p, 0, declined=True) for p in lg.PASSES], "refused_prose"),
            ([rec_read("f", 0, iid, "whole", outcome="errored")] + reads[1:], scores, "missing"),
            (reads[1:], scores, "missing")):
        x = lg.Records({"f": reads2}, scores2).item_stat("f", 0, row, "rubric")
        assert x["L"] is None and x["status"] == want and x["D_whole"] is None
    # one pass declined is not a refusal
    s5 = [x for x in scores if not (":whole:" in x["label"] and x["label"].startswith("score:p1"))] + [rec_score("f", 0, iid, "whole", "rubric", 1, 1, declined=True)]
    assert lg.Records({"f": reads}, s5).item_stat("f", 0, row, "rubric")["status"] == "computed"


def test_latest_prefers_scored_over_a_later_errored_record():
    a = {"cache_key": "k", "outcome": "errored", "label": "x"}
    b = {"cache_key": "k", "outcome": "scored", "label": "x"}
    assert lg.latest([a, b])["k"]["outcome"] == "scored"
    assert lg.latest([b, a])["k"]["outcome"] == "scored"
    assert lg.latest([a])["k"]["outcome"] == "errored"


def test_check_safe_refuses_free_text():
    lg.check_safe({"ids": ["ab" * 32], "n": 3, "path": "/shared/eval/release-gate-runbook.md", "x": None, "h": {"+0.50": 2}})
    with pytest.raises(ValueError):
        lg.check_safe({"answer": "It moves the port."})
    with pytest.raises(ValueError):
        lg.check_safe({"free text key": 1})
    with pytest.raises(TypeError):
        lg.check_safe({"s": {1, 2}})
    assert lg.strip_reasons({"a": {"aborted": True, "abort_reason": "HTTP 400 on x"}}) == {"a": {"aborted": True}}


def test_spend_guard_stops_at_twice_the_estimate():
    class C:
        def __init__(self, v):
            self.v = v

        def total_spent(self):
            return self.v
    g = lg.SpendGuard(10.0)
    g.clients = [C(4.0), C(5.9)]
    g.check()
    g.clients.append(C(0.2))
    with pytest.raises(jc.JudgeAborted, match="twice-estimate"):
        g.check()


# ── end to end on fake clients: the pre-registered sentences dry-run as code (lesson L17) ──────────────

TOK = re.compile(r"(?:TOK-T1v\d-[A-Z]\d+|H-\d-\d)")


def change_section(packet):
    return packet.split("The change (", 1)[1]


def reader_fn(declined_marker=None):
    def fn(kw):
        pkt = kw["messages"][0]["content"]
        sec = change_section(pkt)
        if declined_marker and declined_marker in sec:
            return msg("DECLINED")
        toks = sorted(set(TOK.findall(sec)))
        if sec.startswith("3 edits"):   # even-numbered test items are not understood whole (L = 0): L varies across items
            return msg("WHOLE " + " ".join(t for t in toks if not re.match(r"TOK-T1v\d-[CM]0[24]", t)))
        return msg("PART " + " ".join(toks))
    return fn


def scorer_fn(kw):
    pkt = kw["messages"][0]["content"]
    rubric = pkt.split("Target:\n<<<\n", 1)[1].split("\n>>>", 1)[0]
    answer = pkt.split("Answer:\n<<<\n", 1)[1].split("\n>>>", 1)[0]
    rt, at = set(TOK.findall(rubric)), set(TOK.findall(answer))
    if rubric.startswith("The document"):   # own target: every listed change must be covered
        hit = bool(rt) and rt <= at
    else:
        hit = bool(rt & at) and answer.startswith("WHOLE")
    return msg(json.dumps({"reason": "r", "declined": False, "score": int(hit)}))


def run_e2e(tmp_path, small, declined_marker=None):
    triples, _k, _p, items, rubrics = small
    rows = items["items"]
    tr = {t["triple_id"]: t for t in triples}
    packets = lg.all_packets(rows, tr, DAY0)
    readers = {f: client(reader_fn(declined_marker if f == "kimi" else None), tmp_path / f"read-{f}.jsonl", lg.READER_SYSTEM,
                         lg.READER_PROMPT_VERSION, lg.parse_answer)[0] for f in ("sonnet55", "kimi", "sol")}
    scorer, sfc = client(scorer_fn, tmp_path / "score.jsonl", lg.SCORER_SYSTEM, lg.SCORER_PROMPT_VERSION, lg.parse_score)
    guard = lg.SpendGuard(1e9)
    guard.clients = list(readers.values()) + [scorer]
    by_id = {r["item_id"]: r for r in rows}
    log = tmp_path / "batches.jsonl"

    async def both():
        a = await lg.run_phase("nulls", [r for r in rows if r["regime"] in lg.NULL_REGIMES], packets, readers, scorer, rubrics, by_id, guard, log, 0)
        b = await lg.run_phase("tests", [r for r in rows if r["regime"] in lg.TEST_REGIMES], packets, readers, scorer, rubrics, by_id, guard, log, 10)
        return a, b
    a, b = asyncio.run(both())
    rec = lg.Records({f: lg.read_jsonl(tmp_path / f"read-{f}.jsonl") for f in readers}, lg.read_jsonl(tmp_path / "score.jsonl"))
    return rows, rubrics, a, b, rec, sfc


def test_end_to_end_fake_run_reads_valid_and_counts_every_call(tmp_path, small):
    rows, rubrics, a, b, rec, sfc = run_e2e(tmp_path, small)
    n_ret = sum(r["retest"] for r in rows)
    assert all(x["done"] == x["of"] == (sum(1 for r in rows if r["regime"] in lg.NULL_REGIMES) * 4
                                         + sum(4 for r in rows if r["regime"] in lg.NULL_REGIMES and r["retest"])) for x in a["read"].values())
    want_scores = 0
    for r in rows:
        for rr in lg.repeats_of(r):
            want_scores += 4 * len(lg.scoring_targets(r, rr)) * 2
    assert a["score"]["done"] + b["score"]["done"] == want_scores * 3 == len(sfc.messages.calls)
    for call in sfc.messages.calls:   # the scorer never sees the item: no day-0 text, no edit list
        assert "The change (" not in call["messages"][0]["content"] and "Current values" not in call["messages"][0]["content"]
    res = lg.analyse(rec, rows, ["sonnet55", "kimi", "sol"])
    for f, d in res["per_family"].items():
        s = d["sentences"]
        assert s["S1"]["value"] == 0.0 and s["S2"]["value"] == 0.5 and s["S3"]["value"] == 0.0
        assert s["S4"]["kappa"] == pytest.approx(1.0) and s["S4"]["agreement_test"] == pytest.approx(1.0)
        assert s["S4b"]["D_whole_own"] == 1.0 and s["S4b"]["D_part_own"] == 1.0
        assert all(x["holds"] is True for x in s.values()), (f, s)
        assert d["regimes"]["v2_conforming"]["targets"]["rubric"]["L"]["mean"] == 0.5
        assert d["retest"]["L"]["n"] == n_ret
    assert res["verdict"]["label"] == "valid" and res["verdict"]["families_valid"] == ["kimi", "sol", "sonnet55"]
    assert len(res["verdict"]["agreeing_valid_pairs"]) == 3
    assert all(x["p1:scored"] == x["p2:scored"] for d in res["per_family"].values() for x in d["outcomes"]["scorer"].values())
    md = lg.render_md({**res, "routes": {f: {"route": "bedrock", "model": "m"} for f in lg.FAMILIES}, "answer_chars": {f: lg.describe([1.0]) for f in lg.FAMILIES},
                       "hashes": {"items_v0": "h", "rubrics": "h", "config": "h", "script_at_items": "h", "script_now": "h",
                                  "prompt_sha256": lg.prompt_hashes(), "dependency_sha256": {"d": "h"}},
                       "cache_sha256": {"x": "h"}, "dollars": {"total": 0.0}}, small[3])
    assert "**Verdict: valid**" in md
    for eff in rubrics["test"].values():
        assert eff not in md


def test_end_to_end_declined_reader_is_a_refusal_and_breaks_its_items(tmp_path, small):
    rows, _rub, _a, _b, rec, _ = run_e2e(tmp_path, small, declined_marker="TOK-T1v2-C01")
    res = lg.analyse(rec, rows, ["sonnet55", "kimi", "sol"])
    k = res["per_family"]["kimi"]
    out = k["outcomes"]["reader"]["r0:v2_conforming"]
    assert out["whole"].get("refused_token") == 1 and out["part0"].get("refused_token") == 1
    nc = k["regimes"]["v2_conforming"]["targets"]["rubric"]
    assert nc["n_computed"] == 3 and nc["not_computed"] == {"refused_token": 1}
    assert res["per_family"]["sol"]["regimes"]["v2_conforming"]["targets"]["rubric"]["n_computed"] == 4


def test_sentences_fail_and_name_their_next_actions():
    per = {"a": {"sentences": {"S1": {"holds": False}, "S2": {"holds": True}, "S3": {"holds": True}, "S4": {"holds": None}, "S4b": {"holds": True}}},
           "b": {"sentences": {k: {"holds": True} for k in ("S1", "S2", "S3", "S4", "S4b")}}}
    v = lg.verdict(per)
    assert v["label"] == "valid_for_one_family" and v["families_valid"] == ["b"]
    assert v["failing_by_family"]["a"] == ["S1", "S4"] and set(v["next_actions"]) == {"S1", "S4"}
    per["b"]["sentences"]["S2"]["holds"] = False
    assert lg.verdict(per)["label"] == "not_valid"


def test_estimate_counts_calls(small, monkeypatch):
    triples, _k, _p, items, rubrics = small
    tr = {t["triple_id"]: t for t in triples}
    models = {"models": {"moonshotai/kimi-k3": {"pricing": {"prompt": "0.0000002", "completion": "0.00002"}},
                         "anthropic/claude-sonnet-5.5": {"pricing": {"prompt": "0.000002", "completion": "0.00001"}}}}
    est = lg.estimate(items["items"], tr, DAY0, rubrics, models, None)
    n = len(items["items"])
    n_ret = sum(r["retest"] for r in items["items"])
    assert est["reader_calls_per_family"] == 4 * n + 4 * n_ret
    want = sum(4 * len(lg.scoring_targets(r, rr)) * 2 for r in items["items"] for rr in lg.repeats_of(r))
    assert est["scorer"]["calls_per_family"] == want and est["scorer"]["calls"] == 3 * want
    assert est["families"]["sonnet55"]["route"] == "bedrock" and est["families"]["kimi"]["route"] == "openrouter"
    assert est["stop_at_usd"] == pytest.approx(2 * est["total_usd"], abs=0.011)
    lg.check_safe(est)


# ── codex round 1 regressions (2026-10-31) ────────────────────────────────────────────────────────────

def test_refusal_is_not_reasked_and_is_recorded(tmp_path):
    seq = iter([msg("", stop_reason="refusal"), msg("an answer")])
    rd, fc = client(lambda kw: next(seq), tmp_path / "r.jsonl", lg.READER_SYSTEM, lg.READER_PROMPT_VERSION, lg.parse_answer)
    rec = asyncio.run(rd.score(lg.READ_VIEW, lg.read_label(0, "ab" * 32, "whole"), "pkt"))
    assert rec["outcome"] == "refused" and len(fc.messages.calls) == 1


def test_scorer_declined_word_is_a_refusal_not_a_reask(tmp_path):
    sc, fc = client(lambda kw: msg("DECLINED"), tmp_path / "s.jsonl", lg.SCORER_SYSTEM, lg.SCORER_PROMPT_VERSION, lg.parse_score)
    rec = asyncio.run(sc.score(lg.SCORE_VIEW, lg.score_label(1, "kimi", 0, "ab" * 32, "whole", "rubric"), "pkt"))
    assert rec["outcome"] == "refused" and rec["parsed"]["scorer_declined"] is True and len(fc.messages.calls) == 1
    r = lg.Records({}, [rec])
    assert r.score_outcome("kimi", 0, "ab" * 32, "whole", "rubric", 1) == "refused_token"


def test_mixed_passes_and_scorer_refusals_are_counted():
    iid = "ef" * 32
    row = {"item_id": iid, "regime": "v2_conforming", "retest": False}
    reads = [rec_read("f", 0, iid, c) for c in lg.CONDS]
    scores = [rec_score("f", 0, iid, c, "rubric", 1, 1) for c in lg.CONDS]
    scores += [rec_score("f", 0, iid, "whole", "rubric", 2, outcome="refused")] + [rec_score("f", 0, iid, c, "rubric", 2, 0) for c in lg.PARTS]
    t = lg.outcome_tables(lg.Records({"f": reads}, scores), "f", [row])
    assert t["scorer"]["r0:v2_conforming:whole:rubric"] == {"p1:scored": 1, "p2:refused_provider": 1}
    assert t["mixed_passes"] == {"r0:v2_conforming:rubric:refused_provider+scored": 1}
    st = lg.Records({"f": reads}, scores).item_stat("f", 0, row, "rubric")
    assert st["scored_passes"]["whole"] == 1 and st["D_whole"] == 1.0 and st["D_part"] == 0.5 and st["L"] == 0.5


def _per(Lmap, rows, sentences_hold=True):
    return {"L_by_item": Lmap, "sentences": {k: {"holds": sentences_hold} for k in ("S1", "S2", "S3", "S4b")} | {
        "S4": {"kappa": 0.9, "holds": None}}}


def test_pooled_agreement_cannot_certify_when_test_rankings_disagree():
    rows = [{"item_id": f"t{i}", "regime": "v2_conforming"} for i in range(6)] + [{"item_id": f"n{i}", "regime": "control"} for i in range(20)]
    a = {f"t{i}": 0.5 + 0.1 * i for i in range(6)} | {f"n{i}": 0.0 for i in range(20)}
    b = {f"t{i}": 1.0 - 0.1 * i for i in range(6)} | {f"n{i}": 0.0 for i in range(20)}
    per = {"a": _per(a, rows), "b": _per(b, rows)}
    agree = lg.agreement(per, rows)
    assert agree["pairwise"]["a~b"]["spearman_all_descriptive"] > 0.6 and agree["pairwise"]["a~b"]["spearman_test"] == pytest.approx(-1.0)
    lg.apply_s4(per, agree)
    assert per["a"]["sentences"]["S4"]["holds"] is False
    assert per["a"]["sentences"]["S4"]["fails_only_on_test_agreement"] is True   # named in the report, not counted
    assert lg.verdict(per, agree)["label"] == "not_valid"


def test_valid_needs_two_families_that_agree_with_each_other():
    rows = [{"item_id": f"t{i}", "regime": "v2_conforming"} for i in range(6)]
    up = {f"t{i}": 0.1 * i for i in range(6)}
    down = {f"t{i}": -0.1 * i for i in range(6)}
    per = {"a": _per(up, rows), "b": _per(down, rows), "c": _per(up, rows)}
    agree = lg.agreement(per, rows)
    for f in per:
        per[f]["sentences"]["S4"]["holds"] = True   # each found a partner, but a and c are the only agreeing pair
    v = lg.verdict(per, agree)
    assert v["label"] == "valid" and v["agreeing_valid_pairs"] == [["a", "c"]]
    per["c"]["sentences"]["S1"]["holds"] = False
    assert lg.verdict(per, agree)["label"] == "valid_for_one_family"


def test_sentences_are_not_evaluable_below_completeness_and_s2_counts_missing_as_not_above(small):
    _t, _k, _p, items, _r = small
    rows = items["items"]
    reads, scores = [], []
    for row in rows:
        lt = lg.l_target(row["regime"])
        test = row["regime"] in lg.TEST_REGIMES
        for c in lg.CONDS:
            reads.append(rec_read("f", 0, row["item_id"], c))
            for t in lg.scoring_targets(row, 0):
                for p in lg.PASSES:
                    v = 1 if (test and c == "whole") or t == "own" else 0
                    scores.append(rec_score("f", 0, row["item_id"], c, t, p, v))
    nulls = [r for r in rows if r["regime"] in lg.NULL_REGIMES]
    tests = [r for r in rows if r["regime"] in lg.TEST_REGIMES]
    drop = {nulls[0]["item_id"], nulls[1]["item_id"], tests[0]["item_id"]}   # 2 of 13 nulls: under 90 percent
    reads2 = [x for x in reads if not any(d in x["label"] for d in drop)]
    d = lg.family_analysis(lg.Records({"f": reads2}, scores), "f", rows)
    s = d["sentences"]
    assert s["S1"]["n"] == len(nulls) - 2 and s["S1"]["holds"] is None and s["S2"]["holds"] is None
    assert s["S2"]["value"] == pytest.approx((len(tests) - 1) / len(tests))
    d_full = lg.family_analysis(lg.Records({"f": reads}, scores), "f", rows)
    assert d_full["sentences"]["S1"]["holds"] is True and d_full["sentences"]["S2"]["value"] == 1.0


def test_manifest_mismatches_name_every_drift():
    items = {"inputs_sha256": {"triples": "a", "key": "b"}, "script_sha256": "s", "config_sha256": "c", "dependency_sha256": {"d1": "x"}}
    assert lg.manifest_mismatches(items, inputs_sha256={"triples": "a", "key": "b"}, script_sha256="s", cfg_sha256="c", deps={"d1": "x"}) == []
    bad = lg.manifest_mismatches(items, inputs_sha256={"triples": "a", "key": "B"}, script_sha256="t", cfg_sha256="C", deps={"d1": "y"})
    assert bad == ["input:key", "script", "config", "dependency:d1"]


def test_config_hash_moves_with_a_prompt():
    h = lg.config_sha256()
    old = lg.SCORER_TEMPLATE
    try:
        lg.SCORER_TEMPLATE = old + " "
        assert lg.config_sha256() != h
    finally:
        lg.SCORER_TEMPLATE = old


def test_route_probe_accepts_only_a_parseable_reply(tmp_path):
    ok, _ = client(lambda kw: msg("OK"), None, lg.READER_SYSTEM, lg.READER_PROMPT_VERSION, lg.parse_answer)
    assert lg.probe(ok)["accepted"] is True
    empty, _ = client(lambda kw: msg(" "), None, lg.READER_SYSTEM, lg.READER_PROMPT_VERSION, lg.parse_answer)
    assert lg.probe(empty) == {**lg.probe(empty), "accepted": False, "outcome": "errored"}
    ref, _ = client(lambda kw: msg("", stop_reason="refusal"), None, lg.READER_SYSTEM, lg.READER_PROMPT_VERSION, lg.parse_answer)
    assert lg.probe(ref)["accepted"] is False


def test_request_guard_stops_before_the_next_request_and_paid_attempts_stay_on_file(tmp_path):
    seq = iter([msg("not json"), msg("not json")])
    sc, fc = client(lambda kw: next(seq), tmp_path / "s.jsonl", lg.SCORER_SYSTEM, lg.SCORER_PROMPT_VERSION, lg.parse_score)
    sc.concurrency = 1
    n = {"req": 0}

    def guard():
        n["req"] += 1
        if n["req"] > 1:
            raise jc.JudgeAborted("twice-estimate stop: test")
    sc.request_guard = guard
    with pytest.raises(jc.JudgeAborted):
        asyncio.run(sc.score_many([(lg.SCORE_VIEW, lg.score_label(1, "kimi", 0, "ab" * 32, c, "rubric"), "pkt") for c in lg.CONDS]))
    assert len(fc.messages.calls) == 1
    on_file = lg.read_jsonl(tmp_path / "s.jsonl")
    assert len(on_file) == 1 and on_file[0]["outcome"] == "errored" and on_file[0]["cost_usd"] > 0
    assert on_file[0]["error"] == "aborted after paid attempts"
    g = lg.SpendGuard(1.0, offset_usd=0.4)
    g.clients = [sc]
    assert g.total() == pytest.approx(0.4 + sc.total_spent())


def test_cache_drift_and_reasoning_env(tmp_path, monkeypatch):
    sc, _ = client(lambda kw: msg('{"declined": false, "score": 1}'), tmp_path / "s.jsonl", lg.SCORER_SYSTEM, lg.SCORER_PROMPT_VERSION, lg.parse_score)
    asyncio.run(sc.score(lg.SCORE_VIEW, "score:p1:kimi:r0:" + "ab" * 32 + ":whole:rubric", "pkt"))
    assert lg.cache_drift(sc, lg.SCORER_SYSTEM) == 0 and lg.cache_drift(sc, lg.SCORER_SYSTEM + " changed") == 1
    monkeypatch.setenv("OPENROUTER_REASONING_EFFORT", "low")
    with pytest.raises(SystemExit):
        lg.check_reasoning_env()
    import judge_openrouter as jo
    assert jo.reasoning_setting().startswith("effort low")
    monkeypatch.delenv("OPENROUTER_REASONING_EFFORT")
    lg.check_reasoning_env()
    assert jo.reasoning_setting() == "provider default"


def test_phase_stop_after_a_scorer_abort():
    g = lg.SpendGuard(10.0)
    assert lg.phase_must_stop({"score": {"aborted": True}}, g)
    assert not lg.phase_must_stop({"score": {"aborted": False}}, g)


def test_main_prints_only_the_error_type(tmp_path, capsys):
    assert lg.main(["report", "--out-dir", str(tmp_path), "--triples", str(tmp_path / "none.json")]) == 1
    err = capsys.readouterr().err
    assert json.loads(err) == {"error": "FileNotFoundError", "mode": "report", "traceback": "errors.log"}
    assert (tmp_path / "errors.log").exists()


# ── codex round 2 regressions (2026-10-31) ────────────────────────────────────────────────────────────

def test_d_part_does_not_need_the_whole_and_s3_keeps_those_items():
    iid = "ab" * 32
    row = {"item_id": iid, "regime": "v2_conforming", "retest": False}
    reads = [rec_read("f", 0, iid, c) for c in lg.PARTS]   # the whole is missing
    scores = [rec_score("f", 0, iid, c, "rubric", p, 1) for c in lg.PARTS for p in lg.PASSES]
    st = lg.Records({"f": reads}, scores).item_stat("f", 0, row, "rubric")
    assert st["D_whole"] is None and st["D_part"] == 1.0 and st["L"] is None
    assert st["D_whole_status"] == "missing" and st["D_part_status"] == "computed" and st["status"] == "missing"


def test_s4b_gates_both_own_denominators(small):
    _t, _k, _p, items, _r = small
    rows = items["items"]
    reads, scores = [], []
    honest = [r for r in rows if r["regime"] in lg.HONEST_REGIMES]
    for row in rows:
        for c in lg.CONDS:
            if not (row is honest[0] and c == "part1"):   # one honest part missing: D_part_own on 4 of 5
                reads.append(rec_read("f", 0, row["item_id"], c))
            for t in lg.scoring_targets(row, 0):
                for p in lg.PASSES:
                    scores.append(rec_score("f", 0, row["item_id"], c, t, p, 1 if t == "own" else 0))
    s4b = lg.family_analysis(lg.Records({"f": reads}, scores), "f", rows)["sentences"]["S4b"]
    assert s4b["n"] == len(honest) and s4b["n_part"] == len(honest) - 1 and s4b["holds"] is None


def test_within_regime_correlation_centres_each_repeat_and_bootstrap_refits():
    x = (-0.5, 0.0, 0.5)
    pairs = [("A", v + 0.5, v - 0.5) for v in x] + [("B", v - 0.5, v + 0.5) for v in x]
    assert lg.within_regime_pearson(pairs) == pytest.approx(1.0)
    assert lg.pooled_pearson(pairs) < 0.5
    ci = lg.bootstrap_ci(pairs * 3, lg.within_regime_pearson)
    assert ci is not None and ci[0] == pytest.approx(1.0) and ci[1] == pytest.approx(1.0)
    assert lg.bootstrap_ci(pairs[:2], lg.pooled_pearson) is None


def test_malformed_envelopes_and_arrays_never_supply_a_score():
    assert lg.parse_score('{"outer": {"score":1,"declined":false}') is None
    assert lg.parse_score('[{"score": 1, "declined": false}]') is None
    assert lg.parse_score('{"score": 1, "declined": false} {"oops": ') is None
    assert lg.parse_score('{"score": 1, "declined": false} then {"score": 1.0, "declined": false}')["score"] == 1
    assert lg.parse_score('{"reason": null, "score": 1, "declined": false}') is None
    assert lg.parse_score('{"reason": 3, "score": 1, "declined": false} {"reason": "ok", "score": 1, "declined": false}') is None
    assert lg.parse_score('Here: {"reason": "a \\"quoted\\" } brace", "declined": false, "score": 0}')["score"] == 0


def test_rendering_pin_detects_day0_and_packet_drift(small):
    triples, _k, _p, items, _r = small
    tr = {t["triple_id"]: t for t in triples}
    pk = lg.all_packets(items["items"], tr, DAY0)
    pinned = {"day0_sha256": lg.day0_sha256(DAY0), "packets_sha256": lg.packets_sha256(pk)}
    inp = {"day0": DAY0, "day0_in_md": True}
    assert lg.check_rendering(pinned, inp, pk) == []
    day0b = {**DAY0, DOCS[0]: DAY0[DOCS[0]] + "- Extra: 1\n"}
    pk2 = lg.all_packets(items["items"], tr, day0b)
    assert lg.check_rendering(pinned, {"day0": day0b, "day0_in_md": True}, pk2) == ["day0_texts", "packets"]
    assert lg.check_rendering(pinned, {"day0": DAY0, "day0_in_md": False}, pk) == ["day0_not_in_doc_states_md"]


def test_kappa_without_prose_refusals_excludes_those_conditions():
    iid = "cd" * 32
    row = {"item_id": iid, "regime": "v2_conforming", "retest": False}
    reads = [rec_read("f", 0, iid, c) for c in lg.CONDS]
    scores = [rec_score("f", 0, iid, "whole", "rubric", p, 0, declined=True) for p in lg.PASSES]
    scores += [rec_score("f", 0, iid, c, "rubric", p, 1) for c in lg.PARTS for p in lg.PASSES]
    rec = lg.Records({"f": reads}, scores)
    assert len(rec.pass_pairs("f")[0]) == 4
    assert len(rec.pass_pairs("f", exclude={(0, iid, "whole")})[0]) == 3


# ── codex round 3 regressions (2026-10-31) ────────────────────────────────────────────────────────────

def test_run_refuses_changed_prices_or_routes_before_reading_items(tmp_path):
    (tmp_path / "models-v0.json").write_text(json.dumps({"models": {"m": {"pricing": {"prompt": "1", "completion": "2"}}}}))
    (tmp_path / "routes-v0.json").write_text(json.dumps({"chosen": {}}))
    est = {"config_sha256": lg.config_sha256(), "models_sha256": lg.file_sha256(tmp_path / "models-v0.json"),
           "routes_sha256": lg.file_sha256(tmp_path / "routes-v0.json"), "total_usd": 1.0, "stop_at_usd": 2.0}
    (tmp_path / "estimate-v0.json").write_text(json.dumps(est))
    assert lg.estimate_mismatches(est, tmp_path) == []
    ns = argparse.Namespace(out_dir=str(tmp_path), approved_usd=1.0, triples=str(tmp_path / "absent.json"), resume=False)
    with pytest.raises(FileNotFoundError):   # unchanged pins: it goes on to read the (absent) items
        lg.mode_run(ns)
    (tmp_path / "models-v0.json").write_text(json.dumps({"models": {"m": {"pricing": {"prompt": "9", "completion": "2"}}}}))
    with pytest.raises(SystemExit, match="estimate_prices"):
        lg.mode_run(ns)
    assert lg.estimate_mismatches(est, tmp_path) == ["estimate_prices"]
    (tmp_path / "models-v0.json").write_text(json.dumps({"models": {"m": {"pricing": {"prompt": "1", "completion": "2"}}}}))
    (tmp_path / "routes-v0.json").write_text(json.dumps({"chosen": {"kimi": {"route": "openrouter"}}}))
    with pytest.raises(SystemExit, match="estimate_routes_file"):
        lg.mode_run(ns)
    assert lg.estimate_mismatches({**est, "config_sha256": "x"}, tmp_path) == ["estimate_config", "estimate_routes_file"]


def test_s3_reads_d_part_over_items_without_a_whole(small):
    _t, _k, _p, items, _r = small
    rows = items["items"]
    tests = sorted((r for r in rows if r["regime"] in lg.TEST_REGIMES), key=lambda r: r["item_id"])
    high = {r["item_id"] for r in tests[:4]}          # D_part = 1 on four of eight test items
    no_whole = {r["item_id"] for r in tests[:2]}      # two of those have no whole answer
    reads, scores = [], []
    for row in rows:
        iid = row["item_id"]
        for c in lg.CONDS:
            if not (c == "whole" and iid in no_whole):
                reads.append(rec_read("f", 0, iid, c))
            for t in lg.scoring_targets(row, 0):
                for p in lg.PASSES:
                    v = 1 if (iid in high and c == "part0") or t == "own" else 0
                    scores.append(rec_score("f", 0, iid, c, t, p, v))
    d = lg.family_analysis(lg.Records({"f": reads}, scores), "f", rows)
    s3 = d["sentences"]["S3"]
    assert s3["n_test"] == 8 and s3["value"] == pytest.approx(0.5) and s3["holds"] is False
    rt = d["regimes"]
    assert sum(rt[g]["targets"]["rubric"]["n_D_part"] for g in lg.TEST_REGIMES) == 8
    assert sum(rt[g]["targets"]["rubric"]["n_D_whole"] for g in lg.TEST_REGIMES) == 6
    exported = [x["r0"] for x in d["items"].values() if x["regime"] in lg.TEST_REGIMES and x["r0"]["D_whole"] is None]
    assert len(exported) == 2 and all(x["D_part_status"] == "computed" and x["D_whole_status"] == "missing" for x in exported)


def test_a_bracket_in_prose_makes_the_reply_unparseable_by_policy():
    assert lg.parse_score('Note [draft. {"declined": false, "score": 1}') is None
    assert lg.parse_score('Note (draft). {"declined": false, "score": 1}')["score"] == 1


# ── the downstream reading (Aravind, 2026-10-31) ──────────────────────────────────────────────────────

def test_resolved_subset_governs_downstream_and_a_disagreement_is_named(tmp_path, small):
    rows, rubrics, _a, _b, rec, _ = run_e2e(tmp_path, small)
    res = lg.analyse(rec, rows, ["sonnet55", "kimi", "sol"])
    assert res["verdict"]["label"] == res["verdict_downstream"]["label"] == "valid" and res["resolved_disagreements"] == {}
    # now make the resolved-anchor subset fail sentence 2: no resolved test item above the resolved nulls' p95
    for row in rows:
        row["anchors_resolve"] = row["regime"] in lg.NULL_REGIMES or row["item_id"] in {
            r["item_id"] for r in rows if r["regime"] in lg.TEST_REGIMES and r["payload_ref"]["id"][-1] in "24"}
    res2 = lg.analyse(rec, rows, ["sonnet55", "kimi", "sol"])
    for f, d in res2["per_family"].items():
        assert d["sentences"]["S2"]["holds"] is True and d["sentences_resolved"]["S2"]["holds"] is False
        assert d["resolved_disagreement"] == ["S2"] and d["downstream_null_p95"] == 0.0
    assert res2["verdict"]["label"] == "valid" and res2["verdict_downstream"]["label"] == "not_valid" and res2["verdicts_differ"]
    assert res2["verdict_downstream"]["failing_by_family"]["kimi"] == ["S2"]
    md = lg.render_md({**res2, "routes": {f: {"route": "bedrock", "model": "m"} for f in lg.FAMILIES},
                       "answer_chars": {f: lg.describe([1.0]) for f in lg.FAMILIES},
                       "hashes": {"items_v0": "h", "rubrics": "h", "config": "h", "script_at_items": "h", "script_now": "h",
                                  "prompt_sha256": lg.prompt_hashes(), "dependency_sha256": {"d": "h"}},
                       "cache_sha256": {"x": "h"}, "dollars": {"total": 0.0}}, small[3])
    assert "**Downstream verdict" in md and md.count("**Disagreement,") == 3 and "differ; downstream use reads the downstream verdict" in md
    assert "downstream_rule" in lg.config() and lg.DOWNSTREAM_RULE in json.dumps(lg.config())
