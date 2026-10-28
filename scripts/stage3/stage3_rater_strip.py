#!/usr/bin/env python3
"""Brief 07k K0: strip the T1 placeholder files for the blind rater.

Reads the three payload files (T1 v1, v2, v3), shuffles with `random.Random(20261130)` and writes under
the output directory:
  stripped-statements.json  one record per statement: opaque statement id, document path, op, anchor
                            (replace) or region (append), statement text. Nothing else.
  stripped-payloads.json    one record per payload: opaque payload id, document path, the three statement
                            texts in document order, composed_effect ("" where the writer gave none: v1
                            and the sham arm). Nothing else: no arm, kind, token, harm_needs, alone,
                            justification, id prefix.
  key.json                  the join from opaque ids to file, payload id, statement index, arm, kind and the
                            writer's harm_needs and alone, plus the salt. Committed by hash; the rater never
                            opens it.
Opaque ids are sha256 of a salted key (salt in key.json); without the salt neither the file nor the payload
order can be recovered from an id. Document order of a payload's statements: by the anchor's line in the
document's day-0 state (the class seeder's text), appends after every replace, ties and unresolved anchors
by statement text (so the writer's statement order, which carries harm_needs, does not leak).

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_rater_strip.py \\
        --payloads ../stage3/t1/payloads-v1.json ../stage3/t1v2/payloads-v2.json ../stage3/t1v3/payloads-v3.json \\
        --out-dir ../stage3/t1k-rater

Brief 07s H0 and its amendment B2 (2026-10-28, additive; the 07k path is unchanged): the honest edits of the null
beside a re-draw of 07k's statements, and the planted and honest triples (see the section above `main_07s`):

    cd work/checks && ../mole-fork/.venv/bin/python -I stage3_rater_strip.py 07s \\
        --corpus /abs/.../prefix_rw_v2c.jsonl --t1k-statements ../stage3/t1k-rater/stripped-statements.json \\
        --payloads v1=../stage3/t1/payloads-v1.json v2=../stage3/t1v2/payloads-v2.json \\
                   v3=../stage3/t1v3/payloads-v3-planting.json replant=../stage3/t1-replant/payloads-replant-planting.json \\
        --out-dir ../stage3/t1k-rater
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import secrets
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

SHUFFLE_SEED = 20261130
STATEMENT_FIELDS = ("statement_id", "document", "op", "anchor_or_region", "text")
PAYLOAD_FIELDS = ("payload_id", "document", "statements", "composed_effect")


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def statement_text(st: Mapping[str, Any]) -> str:
    return str(st["replace"] if st["op"] == "replace" else st["text"])


def anchor_or_region(st: Mapping[str, Any]) -> str:
    if st["op"] == "replace":
        return str(st.get("anchor") or "")
    return str(st.get("region") or "end of document")


def doc_position(st: Mapping[str, Any], doc_text: str | None) -> tuple[int, int, str]:
    """Sort key for document order: (0, anchor line) for a replace whose anchor is a line prefix of the
    day-0 text, (1, 0) for a replace whose anchor does not resolve there, (2, 0) for an append; ties by text."""
    text = statement_text(st)
    if st["op"] == "replace":
        anchor = str(st.get("anchor") or "")
        if doc_text is not None and anchor:
            for i, line in enumerate(doc_text.splitlines()):
                if line.startswith(anchor):
                    return (0, i, text)
        return (1, 0, text)
    return (2, 0, text)


def strip(files: list[tuple[str, dict]], base: Mapping[str, str] | None, salt: str,
          seed: int = SHUFFLE_SEED) -> tuple[list[dict], list[dict], dict]:
    """files: [(name, parsed payload file)]; base: {document path: day-0 text} (None: appends after
    replaces, replaces by text). Returns (statements, payloads, key)."""
    statements: list[dict] = []
    payloads: list[dict] = []
    key: dict[str, Any] = {"salt": salt, "shuffle_seed": seed, "files": [n for n, _ in files], "statements": {}, "payloads": {}}
    for name, d in files:
        for p in d["payloads"]:
            pid = sha256(f"{salt}|{name}|{p['id']}")
            doc = str(p["document"])
            doc_text = (base or {}).get(doc)
            ordered = sorted(p["statements"], key=lambda st: doc_position(st, doc_text))
            payloads.append({"payload_id": pid, "document": doc, "statements": [statement_text(st) for st in ordered],
                             "composed_effect": str(p.get("composed_effect") or "")})
            key["payloads"][pid] = {"file": name, "id": p["id"], "arm": p.get("arm"), "kind": p.get("kind"),
                                    "harm_needs": p.get("harm_needs"), "document_order": [p["statements"].index(st) for st in ordered]}
            for i, st in enumerate(p["statements"]):
                sid = sha256(f"{salt}|{name}|{p['id']}|{i}")
                statements.append({"statement_id": sid, "document": doc, "op": str(st["op"]),
                                   "anchor_or_region": anchor_or_region(st), "text": statement_text(st)})
                key["statements"][sid] = {"file": name, "payload_id": p["id"], "statement_index": i, "arm": p.get("arm"),
                                          "kind": st.get("kind", p.get("kind")), "alone": st.get("alone")}
    rng = random.Random(seed)
    rng.shuffle(statements)
    rng.shuffle(payloads)
    return statements, payloads, key


# ── brief 07s H0 and amendment B2 (2026-10-28, additive): honest edits and triples in the rater pool ──
#
# The 07k path above is unchanged. Two further outputs, both built from the honest null `prefix_rw_v2c`:
#   stripped-statements-2.json / key-2.json   every successful honest content edit of a class document in the
#       three days (no-ops excluded), sampled 20 per document with random.Random(20261137) (every edit where a
#       document has fewer), shuffled with a re-draw of 60 of 07k's 348 stripped statements on the same stream;
#   stripped-triples.json / key-triples.json  every planted payload of v1, v2, v3 and the re-plant as a triple
#       (identical triples across plantings once, every planting in the key) beside two honest nulls drawn with
#       random.Random(20261142): 20 random triples per document (any authors) and every same-author triple
#       (sampled to at most 60).
# An honest edit is rendered from the document states around it (the shared reader's timeline): an append as the
# appended lines; a replace as the full line(s) the `find` touched, after the edit, with the old first line's
# prefix as the anchor; a whole write as its changed lines (a unified diff without file headers). The edit's own
# day becomes `{date}`, the placeholders' convention; nothing else in the text changes.

HONEST_SEED = 20261137
TRIPLE_SEED = 20261142
HONEST_PER_DOC = 20
REDRAW_N = 60
RANDOM_TRIPLES_PER_DOC = 20
SAME_AUTHOR_MAX = 60
ANCHOR_COLON_MAX = 40   # an anchor runs through the old line's first ':' when it is this early ...
ANCHOR_PREFIX_LEN = 24  # ... else it is the line's first 24 characters (the placeholders' two anchor shapes)
TRIPLE_FIELDS = ("triple_id", "document", "statements")
TRIPLE_STATEMENT_FIELDS = ("op", "anchor_or_region", "text")


def anchor_prefix(line: str) -> str:
    i = line.find(":")
    if 0 <= i < ANCHOR_COLON_MAX:
        return line[: i + 1]
    return line[:ANCHOR_PREFIX_LEN]


def _strip_blank_ends(text: str) -> str:
    lines = text.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def render_honest(action: str, args: Mapping[str, Any], before: str, after: str, path: str,
                  day: str) -> dict[str, str] | None:
    """(op, anchor_or_region, text) of one honest content write, from the states around it; None for a no-op."""
    if before == after:
        return None
    if action == "append_to_file" and after.startswith(before):
        out = {"op": "append", "anchor_or_region": "end of document", "text": _strip_blank_ends(after[len(before):])}
    elif action == "replace_in_file" and str(args.get("find") or "") in before:
        find, repl = str(args.get("find")), str(args.get("replace") or "")
        pos = before.find(find)
        start = before.rfind("\n", 0, pos) + 1
        end = pos + len(find)
        if end > start and before[end - 1] == "\n":
            stop = end - 1
        else:
            nl = before.find("\n", end)
            stop = len(before) if nl < 0 else nl
        new_block = before[start:pos] + repl + before[end:stop]
        if before[:start] + new_block + before[stop:] != after:
            raise ValueError(f"replace_in_file on {path} at {day}: the rendered lines do not rebuild the state after")
        old_first = before[start:stop].split("\n")[0]
        out = {"op": "replace", "anchor_or_region": anchor_prefix(old_first), "text": _strip_blank_ends(new_block)}
    else:
        import difflib
        body = list(difflib.unified_diff(before.splitlines(), after.splitlines(), n=0, lineterm=""))[2:]
        out = {"op": "write", "anchor_or_region": "whole document", "text": "\n".join(body)}
    return {k: v.replace(day, "{date}") for k, v in out.items()}


def honest_edits(rows: list[Mapping[str, Any]], docs: list[str], base: Mapping[Any, Any]) -> list[dict]:
    """Every successful content write to a class document, in file order per document (documents in `docs`
    order), rendered; no-ops dropped. Each: document, row index, ts, day, account, action, task_id, rendering."""
    import stage3_views as sv
    out = []
    for path in docs:
        for ch in sv.document_timeline(rows, path, base):
            day = str(ch.ts)[:10]
            r = render_honest(ch.action, rows[ch.index].get("args") or {}, ch.before or "", ch.after or "", path, day)
            if r is None:
                continue
            out.append({"document": path, "index": ch.index, "ts": ch.ts, "day": day, "account": ch.account,
                        "action": ch.action, "task_id": ch.task_id, **r})
    return out


def strip_honest_pool(honest: list[dict], t1k_statements: list[dict], salt: str, docs: list[str],
                      seed: int = HONEST_SEED) -> tuple[list[dict], dict]:
    """Brief 07s H0: the stratified honest sample beside a re-draw of 07k's stripped statements, one stream."""
    rng = random.Random(seed)
    picked: list[dict] = []
    per_doc = {}
    for path in docs:
        frame = [h for h in honest if h["document"] == path]
        take = rng.sample(frame, min(HONEST_PER_DOC, len(frame)))
        per_doc[path] = {"eligible": len(frame), "sampled": len(take)}
        picked.extend(sorted(take, key=lambda h: h["index"]))
    redraw = rng.sample(range(len(t1k_statements)), REDRAW_N)
    items: list[dict] = []
    key: dict[str, Any] = {"salt": salt, "seed": seed, "per_document": per_doc, "statements": {}}
    for h in picked:
        sid = sha256(f"{salt}|honest|{h['document']}|{h['index']}")
        items.append({"statement_id": sid, "document": h["document"], "op": h["op"],
                      "anchor_or_region": h["anchor_or_region"], "text": h["text"]})
        key["statements"][sid] = {"source": "honest", "row_index": h["index"], "ts": h["ts"], "account": h["account"],
                                  "action": h["action"], "task_id": h["task_id"]}
    for i in sorted(redraw):
        st = t1k_statements[i]
        sid = sha256(f"{salt}|t1k|{st['statement_id']}")
        items.append({"statement_id": sid, **{f: st[f] for f in STATEMENT_FIELDS if f != "statement_id"}})
        key["statements"][sid] = {"source": "t1k_redraw", "t1k_position": i, "t1k_statement_id": st["statement_id"]}
    rng.shuffle(items)
    return items, key


def _ordered(statements: list[dict], doc_text: str | None) -> list[dict]:
    """Document order by the 07k rule (a whole write sorts with the unresolved replaces)."""
    def pos(st: Mapping[str, Any]) -> tuple[int, int, str]:
        if st["op"] == "write":
            return (1, 0, st["text"])
        as_payload = {"op": st["op"], "anchor": st["anchor_or_region"], "replace": st["text"], "text": st["text"]}
        return doc_position(as_payload, doc_text)
    return sorted(statements, key=pos)


def planted_triples(files: list[tuple[str, dict]]) -> dict[tuple, list[dict]]:
    """{(document, statements as (op, anchor_or_region, text) in a canonical order): [every planting of it]}."""
    out: dict[tuple, list[dict]] = {}
    for name, d in files:
        for p in d["payloads"]:
            sts = tuple(sorted((str(st["op"]), anchor_or_region(st), statement_text(st)) for st in p["statements"]))
            out.setdefault((str(p["document"]), sts), []).append(
                {"file": name, "id": p["id"], "arm": p.get("arm"), "kind": p.get("kind"), "harm_needs": p.get("harm_needs")})
    return out


def honest_triples(honest: list[dict], docs: list[str], rng: random.Random) -> tuple[list[tuple], list[tuple], dict]:
    """(random, same_author, counts): triples as (document, three row indices in file order)."""
    rand: list[tuple] = []
    counts: dict[str, Any] = {"random": {}, "same_author_eligible": 0}
    for path in docs:
        frame = [h["index"] for h in honest if h["document"] == path]
        seen: set[tuple] = set()
        while len(seen) < RANDOM_TRIPLES_PER_DOC:
            seen.add(tuple(sorted(rng.sample(frame, 3))))
            if len(seen) == len(frame) * (len(frame) - 1) * (len(frame) - 2) // 6:
                break
        rand.extend((path, t) for t in sorted(seen))
        counts["random"][path] = len(seen)
    same: list[tuple] = []
    from itertools import combinations
    for path in docs:
        by_author: dict[str, list[int]] = {}
        for h in honest:
            if h["document"] == path:
                by_author.setdefault(h["account"], []).append(h["index"])
        for acct in sorted(by_author):
            same.extend((path, t) for t in combinations(sorted(by_author[acct]), 3))
    counts["same_author_eligible"] = len(same)
    if len(same) > SAME_AUTHOR_MAX:
        same = sorted(rng.sample(same, SAME_AUTHOR_MAX))
    counts["same_author_sampled"] = len(same)
    return rand, same, counts


def strip_triples(files: list[tuple[str, dict]], honest: list[dict], base: Mapping[str, str] | None, salt: str,
                  docs: list[str], seed: int = TRIPLE_SEED) -> tuple[list[dict], dict]:
    """Amendment B2: planted triples (once each) and the two honest nulls, shuffled together, opaque ids."""
    rng = random.Random(seed)
    rand, same, counts = honest_triples(honest, docs, rng)
    by_index = {(h["document"], h["index"]): h for h in honest}
    records: list[dict] = []
    key: dict[str, Any] = {"salt": salt, "seed": seed, "counts": counts, "triples": {}}
    honest_kinds: dict[tuple, list[str]] = {}
    for kind, triples in (("random", rand), ("same_author", same)):
        for t in triples:
            honest_kinds.setdefault(t, []).append(kind)
    for (path, idx), kinds in honest_kinds.items():
        sts = [{f: by_index[(path, i)][f] for f in TRIPLE_STATEMENT_FIELDS} for i in idx]
        tid = sha256(f"{salt}|honest|{path}|{'|'.join(map(str, idx))}")
        records.append({"triple_id": tid, "document": path, "statements": _ordered(sts, (base or {}).get(path))})
        key["triples"][tid] = {"source": "honest", "null": kinds, "row_indices": list(idx),
                               "accounts": [by_index[(path, i)]["account"] for i in idx],
                               "days": [by_index[(path, i)]["day"] for i in idx]}
    planted = planted_triples(files)
    for (path, sts), plantings in planted.items():
        recs = [dict(zip(TRIPLE_STATEMENT_FIELDS, st)) for st in sts]
        tid = sha256(f"{salt}|planted|{plantings[0]['file']}|{plantings[0]['id']}")
        records.append({"triple_id": tid, "document": path, "statements": _ordered(recs, (base or {}).get(path))})
        key["triples"][tid] = {"source": "planted", "plantings": plantings}
    counts["planted_unique"] = len(planted)
    counts["planted_instances"] = sum(len(v) for v in planted.values())
    counts["honest_unique"] = len(honest_kinds)
    rng.shuffle(records)
    return records, key


def _write(out: Path, objs: list[tuple[str, Any]]) -> dict[str, str]:
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, obj in objs:
        text = json.dumps(obj, indent=1, ensure_ascii=False)
        (out / name).write_text(text, encoding="utf-8")
        written[name] = sha256(text)
    return written


def main_07s(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="brief 07s H0 and amendment B2: honest edits and triples")
    ap.add_argument("--corpus", required=True, help="the honest null, prefix_rw_v2c.jsonl")
    ap.add_argument("--t1k-statements", required=True, help="07k's stripped-statements.json")
    ap.add_argument("--payloads", nargs="+", required=True, help="planting files for the triples, as name=path")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--salt", default=None, help="test only; the default is a fresh secrets.token_hex(16)")
    ns = ap.parse_args(argv)
    import stage3_views as sv
    from stage3_t1v2_checks import corpus_rows, DOCS
    rows = corpus_rows(Path(ns.corpus))
    seed_map = sv.seed_base()
    honest = honest_edits(rows, list(DOCS), seed_map)
    base = {k[1]: v for k, v in seed_map.items()}
    t1k = json.loads(Path(ns.t1k_statements).read_text(encoding="utf-8"))
    files = []
    for spec in ns.payloads:
        name, _, f = spec.partition("=")
        files.append((name, json.loads(Path(f).read_text(encoding="utf-8"))))
    salt = ns.salt or secrets.token_hex(16)
    singles, key2 = strip_honest_pool(honest, t1k, salt, list(DOCS))
    triples, key3 = strip_triples(files, honest, base, salt, list(DOCS))
    src = {"corpus": str(Path(ns.corpus).name), "corpus_sha256": hashlib.sha256(Path(ns.corpus).read_bytes()).hexdigest(),
           "t1k_statements_sha256": hashlib.sha256(Path(ns.t1k_statements).read_bytes()).hexdigest(),
           "payload_files": {n: hashlib.sha256(Path(s.partition('=')[2]).read_bytes()).hexdigest()
                             for (n, _), s in zip(files, ns.payloads)},
           "honest_frame": len(honest)}
    key2["sources"] = src
    key3["sources"] = src
    written = _write(Path(ns.out_dir), [("stripped-statements-2.json", singles), ("key-2.json", key2),
                                         ("stripped-triples.json", triples), ("key-triples.json", key3)])
    print(json.dumps({"n_singles": len(singles), "per_document": key2["per_document"], "n_triples": len(triples),
                      "triple_counts": key3["counts"], "sources": src, "sha256": written}, indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "07s":
        return main_07s(argv[1:])
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--payloads", nargs="+", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--salt", default=None, help="test only; the default is a fresh secrets.token_hex(16)")
    ap.add_argument("--no-base", action="store_true", help="order without the day-0 documents (tests)")
    ns = ap.parse_args(argv)
    files = []
    for f in ns.payloads:
        pth = Path(f)
        if not pth.exists():
            raise SystemExit(f"missing payload file: {pth}")
        files.append((pth.name, json.loads(pth.read_text(encoding="utf-8"))))
    base = None
    if not ns.no_base:
        import stage3_views as sv
        base = {k[1]: v for k, v in sv.seed_base().items()}
    salt = ns.salt or secrets.token_hex(16)
    statements, payloads, key = strip(files, base, salt)
    out = Path(ns.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, obj in (("stripped-statements.json", statements), ("stripped-payloads.json", payloads), ("key.json", key)):
        text = json.dumps(obj, indent=1, ensure_ascii=False)
        (out / name).write_text(text, encoding="utf-8")
        written[name] = sha256(text)
    print(json.dumps({"n_statements": len(statements), "n_payloads": len(payloads), "files": [n for n, _ in files],
                      "sha256": written, "statement_fields": STATEMENT_FIELDS, "payload_fields": PAYLOAD_FIELDS}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
