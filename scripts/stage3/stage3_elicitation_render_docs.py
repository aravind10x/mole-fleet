#!/usr/bin/env python3
"""Brief 29 E0-2: read-only render of the six class documents of one seed version, in the format of
`work/stage3/t1k-rater/doc-states-day0.md`, so that the document state the writers write against and the
state the certification readers see are one file named by hash (the same-state rule of brief 29 E0-3).

    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_render_docs.py v7 --out PATH
    work/mole-fork/.venv/bin/python -I work/checks/stage3_elicitation_render_docs.py v6 --check PATH_OF_EXISTING_V6

`--check` renders the version and exits 1 unless the bytes equal the existing file (the v6 render must equal
`doc-states-day0.md` byte for byte: that is the test that this renderer reproduces the rendering briefs 23 and 25
used). Nothing is written to the seeder, a corpus or a document store; only the named `--out` file is written.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

FORK = Path(__file__).resolve().parents[1] / "mole-fork"


def render(version: str) -> str:
    sys.path.insert(0, str(FORK))
    from mole.seeders.seed_class_docs import class_seed_mapping  # noqa: PLC0415  (fork import after path setup)

    docs = {path: text for (_, path), text in class_seed_mapping(version).items()}
    parts: list[str] = []
    if version == "v6":
        parts.append("# The six class documents, day-0 state (as the class seeder wrote them)\n")
        parts.append("\nRendered read-only from `mole.seeders.seed_class_docs.class_seed_mapping()`, the same source "
                     "`stage3_t1v2_checks.document_states` uses for its `seed` state. Documents in `DOCS` order. "
                     "Each document body is shown verbatim inside a fenced block.\n\n")
    else:
        parts.append(f"# The six class documents, day-0 state, seed version {version} (as the class seeder wrote them)\n")
        parts.append(f"\nRendered read-only from `mole.seeders.seed_class_docs.class_seed_mapping(\"{version}\")`. "
                     "Documents in the seeder's order. Each document body is shown verbatim inside a fenced block. "
                     "The lines of this version that its predecessor does not carry are the shared lines of the "
                     "cross-document items.\n\n")
    for path, text in docs.items():
        lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        parts.append(f"\n## `{path}`\n\n({lines} lines, {len(text)} characters)\n\n````markdown\n{text}\n````\n\n")
    return "".join(parts)[:-1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version", choices=("v6", "v7"))
    ap.add_argument("--out", type=Path, help="write the render here")
    ap.add_argument("--check", type=Path, help="exit 1 unless the render equals this existing file byte for byte")
    args = ap.parse_args(argv)
    text = render(args.version)
    data = text.encode("utf-8")
    print(f"version={args.version} bytes={len(data)} sha256={hashlib.sha256(data).hexdigest()}")
    if args.check is not None:
        same = args.check.read_bytes() == data
        print(f"check={'IDENTICAL' if same else 'DIFFERENT'} against {args.check.name}")
        if not same:
            return 1
    if args.out is not None:
        args.out.write_bytes(data)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
