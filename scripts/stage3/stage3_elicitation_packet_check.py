#!/usr/bin/env python3
"""Brief 29 E0-2: mechanical checks on the writer packet. Prints counts, hashes and pass/fail only; it never
prints a line of the packet or a matched word.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_packet_check.py check \
        --packet work/stage3/elicitation/writer-packet-v0.md --taxonomy work/stage3/elicitation/taxonomy-v0.md
    ... extract --packet P --out PATH      writes the sent bytes (the text between the PACKET markers)
    ... fields  --legibility work/checks/stage3_legibility.py

`check` (exit 1 on any failure):
  1. the PACKET markers occur once each and the text between them is the sent body (its sha256 is printed);
  2. the text between the body's TAXONOMY markers equals, byte for byte, the text between the TAXONOMY markers of the
     taxonomy file;
  3. scan of the body, by class, for zero hits: the filter-field, framing and weakening vocabulary lists of
     `stage3_t1v2_checks.py` (imported, not copied); brief and amendment numbers; repository paths; model, vendor and
     instrument names; and the application and measurement words brief 26 v2 replaced;
  4. the schema blocks of the body parse as JSON once their placeholders are filled, and carry exactly the key sets
     the reader code reads (item: id, document, kind, composed_effect, statements; pair: id, documents, kind,
     composed_effect, statements; statement: op, anchor_or_region, text, plus document for pairs; results layout).
`fields` checks that every field name the schema uses occurs in the reader's source (`stage3_legibility.py`) as a subscript
or a `.get` key. That is all it proves: the names occur in the reader's source. It does not show that a writer's file loads;
the reader's loader takes stripped triples joined to payloads by key, so a load test belongs to the converter of brief 30.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKET_B, PACKET_E = "<<<PACKET BEGIN>>>", "<<<PACKET END>>>"
TAX_B, TAX_E = "<<<TAXONOMY BEGIN>>>", "<<<TAXONOMY END>>>"

ITEM_KEYS = {"id", "document", "kind", "composed_effect", "statements"}
PAIR_KEYS = {"id", "documents", "kind", "composed_effect", "statements"}
STATEMENT_KEYS = {"op", "anchor_or_region", "text"}
PAIR_STATEMENT_KEYS = STATEMENT_KEYS | {"document"}
RESULT_KEYS = {"id", "valid", "failed_checks", "statements", "recovery"}
RESULT_STATEMENT_KEYS = {"index", "rating", "within_target"}
RECOVERY_KEYS = {"whole", "parts"}
READER_FIELDS = ("document", "kind", "composed_effect", "statements", "op", "anchor_or_region", "text")

# Classes of text the body must not carry (brief 29 E0-2 exclusions, brief 26 v2 vocabulary). Matched case-insensitively
# on word boundaries; hits are counted by class and never printed.
NUMBER_PATTERNS = [r"\bbrief\s+\d+", r"\bA\d+(\.\d+)+\b", r"\bE\d\b", r"\bG\d\b", r"\bS\d\b", r"\bB[0-9]\b", r"\bP[0-9]\.[0-9]\b"]
# File names inside the writer's own folder (packet.md, round.md, items.json) are not repository paths and are not matched.
PATH_PATTERNS = [r"\bwork/", r"\bbriefs/", r"\bresults/", r"\bscripts/", r"/Users/", r"\.py\b", r"\bSTATUS\b", r"\bPLAN\b"]
NAME_WORDS = ["kimi", "sol", "opus", "sonnet", "haiku", "glm", "muse", "wonder", "gpt", "claude", "codex", "openrouter",
              "bedrock", "wafer", "anthropic", "openai", "judge", "judges", "rater", "raters", "monitor", "sealed", "threshold",
              "instrument", "certif", "stratum", "baseline", "null", "pilot", "cohort", "scorer", "corpus"]
BRIEF26_WORDS = ["plant", "planted", "planting", "insert", "inserted", "insertion", "inserter", "sham", "payload", "payloads",
                 "collusion", "coalition", "attack", "attacker", "adversarial", "exfiltrate", "backdoor", "sabotage"]


def _lines(text: str) -> list[str]:
    return text.split("\n")


def between(text: str, begin: str, end: str) -> str:
    """The text strictly between two marker lines (each on a line of its own, once)."""
    lines = _lines(text)
    bi = [i for i, ln in enumerate(lines) if ln == begin]
    ei = [i for i, ln in enumerate(lines) if ln == end]
    if len(bi) != 1 or len(ei) != 1 or bi[0] >= ei[0]:
        raise ValueError(f"markers {begin!r}/{end!r} must each occur once, begin before end (found {len(bi)}/{len(ei)})")
    return "\n".join(lines[bi[0] + 1:ei[0]])


def _word_hits(text: str, words) -> int:
    low = text.lower()
    n = 0
    for w in words:
        # whole words and phrases; stems that end in a hyphenless prefix ('exfiltrat', 'certif') match as prefixes
        pat = r"(?<![a-z0-9])" + re.escape(w.lower()) + (r"" if w.lower() in {"exfiltrat", "certif"} else r"(?![a-z0-9])")
        n += len(re.findall(pat, low))
    return n


def scan(body: str) -> dict[str, int]:
    sys.path.insert(0, str(HERE))
    import stage3_t1v2_checks as c  # noqa: PLC0415

    hits = {
        "filter_field": _word_hits(body, c.FILTER_FIELD_WORDS),
        "framing": _word_hits(body, c.HARM_FRAME_WORDS),
        "weakening": _word_hits(body, c.WEAKENING_PHRASES) + len(c.SAFETY_FALSE.findall(body)),
        "brief_and_amendment_numbers": sum(len(re.findall(p, body)) for p in NUMBER_PATTERNS),
        "repository_paths": sum(len(re.findall(p, body, re.M)) for p in PATH_PATTERNS),
        "model_and_instrument_names": _word_hits(body, NAME_WORDS),
        "brief26_replaced_words": _word_hits(body, BRIEF26_WORDS),
        "nonce_like": len(re.findall(r"[0-9a-fA-F]{8,}", body)) + len(re.findall(r"[A-Za-z0-9]{16,}", body)),
    }
    return hits


_PLACEHOLDER = re.compile(r'(?<!")<[^">]*>(?!")')


def schema_blocks(body: str) -> list[dict]:
    """The JSON-looking blocks of the body (a '{' at column 0 to the matching '}' at column 0), placeholders filled."""
    blocks, cur = [], None
    for ln in _lines(body):
        if cur is None and ln == "{":
            cur = [ln]
        elif cur is not None:
            cur.append(ln)
            if ln == "}":
                text = "\n".join(cur)
                text = _PLACEHOLDER.sub("0", text)  # bare placeholders (booleans and numbers) become 0
                blocks.append(json.loads(text))
                cur = None
    if cur is not None:
        raise ValueError("unterminated schema block")
    return blocks


def check_schema(blocks: list[dict]) -> list[str]:
    errs: list[str] = []
    if len(blocks) != 3:
        return [f"expected 3 schema blocks (answer, pair, results), found {len(blocks)}"]
    answer, pair, results = blocks
    if set(answer) != {"items"} or len(answer["items"]) != 1:
        errs.append("answer block must be {'items': [one placeholder item]}")
    else:
        item = answer["items"][0]
        if set(item) != ITEM_KEYS:
            errs.append("item keys differ from the reader code's")
        if len(item["statements"]) != 3 or any(set(s) != STATEMENT_KEYS for s in item["statements"]):
            errs.append("item must show three statements with keys op, anchor_or_region, text")
    if set(pair) != PAIR_KEYS or len(pair["documents"]) != 2:
        errs.append("pair keys differ (id, documents[2], kind, composed_effect, statements)")
    elif len(pair["statements"]) != 2 or any(set(s) != PAIR_STATEMENT_KEYS for s in pair["statements"]):
        errs.append("pair must show two statements with keys document, op, anchor_or_region, text")
    elif pair["kind"] != "cross-document":
        errs.append("pair kind must be cross-document")
    if set(results) != {"results"} or len(results["results"]) != 1:
        errs.append("results block must be {'results': [one placeholder result]}")
    else:
        r = results["results"][0]
        if set(r) != RESULT_KEYS:
            errs.append("result keys differ")
        elif any(set(s) != RESULT_STATEMENT_KEYS for s in r["statements"]) or set(r["recovery"]) != {"colleague_a", "colleague_b"} \
                or any(set(v) != RECOVERY_KEYS for v in r["recovery"].values()):
            errs.append("result statement or recovery keys differ")
    return errs


def check_fields(legibility_src: str) -> dict[str, bool]:
    """Per field name: does it occur in the reader's source as a subscript or a `.get` key? Not a load test."""
    return {f: bool(re.search(r"\[\s*[\"']" + re.escape(f) + r"[\"']\s*\]|\.get\(\s*[\"']" + re.escape(f) + r"[\"']", legibility_src))
            for f in READER_FIELDS}


def cmd_check(args) -> int:
    packet = Path(args.packet).read_text(encoding="utf-8")
    taxonomy = Path(args.taxonomy).read_text(encoding="utf-8")
    ok = True
    body = between(packet, PACKET_B, PACKET_E)
    print(f"body_sha256={hashlib.sha256(body.encode('utf-8')).hexdigest()} body_chars={len(body)} body_words={len(body.split())}")
    emb = between(body, TAX_B, TAX_E)
    ref = between(taxonomy, TAX_B, TAX_E)
    same = emb == ref
    ok &= same
    print(f"taxonomy_embedded_equals_file={same} taxonomy_sha256={hashlib.sha256(ref.encode('utf-8')).hexdigest()[:16]}")
    for cls, n in scan(body).items():
        ok &= n == 0
        print(f"scan[{cls}]={n}")
    errs = check_schema(schema_blocks(body))
    ok &= not errs
    print(f"schema_blocks_ok={not errs}" + (f" errors={len(errs)}" if errs else ""))
    for e in errs:
        print("  schema:", e)
    print("RESULT", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_extract(args) -> int:
    body = between(Path(args.packet).read_text(encoding="utf-8"), PACKET_B, PACKET_E)
    data = body.encode("utf-8")
    Path(args.out).write_bytes(data)
    print(f"wrote {args.out} bytes={len(data)} sha256={hashlib.sha256(data).hexdigest()}")
    return 0


def cmd_fields(args) -> int:
    res = check_fields(Path(args.legibility).read_text(encoding="utf-8"))
    for k, v in res.items():
        print(f"field {k}: {'occurs in the reader source' if v else 'NOT FOUND in the reader source'}")
    print("claim: the field names occur in the reader's source; this is not a load test of a writer's file")
    return 0 if all(res.values()) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("--packet", required=True); c.add_argument("--taxonomy", required=True)
    e = sub.add_parser("extract"); e.add_argument("--packet", required=True); e.add_argument("--out", required=True)
    f = sub.add_parser("fields"); f.add_argument("--legibility", default=str(HERE / "stage3_legibility.py"))
    args = ap.parse_args(argv)
    return {"check": cmd_check, "extract": cmd_extract, "fields": cmd_fields}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
