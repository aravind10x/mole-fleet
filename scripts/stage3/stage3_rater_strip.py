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


def main(argv: list[str] | None = None) -> int:
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
