#!/usr/bin/env python3
"""Brief 13 W0g: re-pin brief 22 after its dated note 2 of 2026-11-03 (F5 amended; the coordinator's request). $0.

Additive, by W0f's conventions: one new amendment record with brief 22's new pin; the fork copy is mirrored in the same
commit so the pinned copies agree. Refuses unless brief 22 is the only drift; leaves no drift behind."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys

import stage3_paper_w0 as w0
import stage3_paper_w0f as w0f

BY = "brief 13 W0g (the writing session, Opus 5.5): brief 22 re-pinned after its dated note 2 of 2026-11-03"
PATH, FORK = "briefs/22-b4-conditional-2026-10-31.md", "results/stage3/b4/brief-22-b4-conditional.md"


def _sha(p) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    raw = w0.MANIFEST.read_bytes()
    m = json.loads(raw)
    if (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode() != raw:
        raise SystemExit("refusing: the manifest does not re-serialise byte-identically")
    if any(a.get("by") == BY for a in m["amendments"]):
        raise SystemExit("refusing: W0g's amendment already exists")
    bad = set(w0f.drift(m))
    if not bad or not bad <= {f"main {PATH}", f"fork {PATH}"}:
        raise SystemExit(f"refusing: the drift is not brief 22 alone: {sorted(bad)}")
    shutil.copyfile(w0.ROOT / PATH, w0.FORK / FORK)
    e = {"path": PATH, "path_root": "project root", "sha256": _sha(w0.ROOT / PATH), "bytes": (w0.ROOT / PATH).stat().st_size,
         "fork_copy_path": FORK, "sha256_fork_copy": _sha(w0.FORK / FORK)}
    e["copies_identical"] = e["sha256"] == e["sha256_fork_copy"]
    e.update({"tag": "design", "cited_only": True, "added_beyond_brief_list": False,
              "tag_source": ("brief 22 (B4, conditional design) with its dated notes of 2026-11-02 (the gates from B3's round 1) and "
                             "2026-11-03 (F5 amended, conditional on the coordinator's adoption of the monitor study's v1); the paper "
                             "states the gates as the 2026-11-02 note does and does not cite the monitor study")})
    m["amendments"].append({"date": "2026-11-03", "by": BY, "entries": [e],
                            "note": "brief 22's fork copy mirrored in the same commit; no other entry changed"})
    left = w0f.drift(m)
    if left:
        raise SystemExit(f"refusing: drift remains {left}")
    out = (json.dumps(m, indent=1, ensure_ascii=False) + "\n").encode()
    w0.MANIFEST.write_bytes(out)
    (w0.FORK_STAGE3 / "b0" / "frozen-tables.json").write_bytes(out)
    print(f"written: brief 22 {e['sha256'][:8]}; pins {len(w0f.current_pins(m))}; sha256 {hashlib.sha256(out).hexdigest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
