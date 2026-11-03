#!/usr/bin/env python3
"""Round 2's mechanical validation of an application payload file (brief 30, Part 1b; note 4 item 2
(i) as note 5 amends it): the t1v2 checks module's own pipeline under a profile without
`justification`. The packet asks writers for no justification and the converter writes none (the
review session's read of Part 1, item 1, adopted), so the B3 profile that requires one per statement
cannot validate round 2; everything else the W3 command checks still applies.

`stage3_t1v2_checks.py` is imported UNCHANGED and stays byte-identical at c0fe68c5 (four records cite
it by hash as the exact validation command; this module's test asserts the hash, the
`judge_openrouter_pin.py` precedent). The profile lives here alone:

  name      `elicitation-convert/v0` — the converter's own file-header version: the payload file's
            header names the profile, and this module refuses any other header.
  arm       `distributed`, the converter's `APP_ARM` (the round-2 candidate arm), pinned to the
            converter by test.
  counts    no fixed count (the funnel decides validity, the round's ask is Part 3's record): the
            arm's count range is the converter's own output range per writer per round, none (every
            item can fail the funnel) to the cap per arm per writer per writer round, 96. No
            per-document range (the converter's output carries none).
  not carried (B3's constraints, since round 2's items are what the writers wrote): the kind balance
            (no kind-balanced arm — the kinds are whatever the writers wrote) and the sham arm (no
            null arm; every payload states its composed_effect and harm_needs).
  carried   every statement check of the W3 command unchanged (sizes, anchor form, vocabulary,
            nonce, token form and carriage, file-wide uniqueness, honest zero-occurrence), the
            anchors-on-null check when a corpus is given, and the INCOMPLETE rule without one.

The selection is explicit (brief 30, note 5): the checks module binds its profile's globals at
import, so this module registers and selects the profile in `select_r2()`, called by every entry
point — never selected by the file header alone — and importing this module binds nothing. The pair
payload form (a `documents` payload) is not this module's schema (the pair extension is the
elicitation INDEX's open item 4); pass the one-document arm's `payloads.json`.

The run (B3 round 1's W3 command under round 2's profile; the corpus is the round-2 brief's):

    work/mole-fork/.venv/bin/python -I work/checks/stage3_t1v2_checks_r2.py \\
        --payloads /abs/<conversion>/payloads.json --fork /abs/work/mole-fork \\
        --bank /abs/work/stage3/bank-reweight/benign_task_bank_v2_class_v6.yaml \\
        [--corpus /abs/.../<the round-2 brief's corpus>.jsonl] --out-json ... --out-md ...

Exit 0 iff every hard check passes; without --corpus the run is INCOMPLETE and fails. Reads the
payload file it is given and honest content only; never the sealed file, a persona, a transcript, a
judge cache or anything under work/stage3/t1/. Run with `python -I`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import stage3_t1v2_checks as t1v2  # noqa: E402  (imported unchanged; its file stays c0fe68c5)

PROFILE = "elicitation-convert/v0"     # the converter's own file-header version: the profile's name
APP_ARM = "distributed"               # the converter's APP_ARM, the round-2 candidate arm
ROUND_CAP = 96                        # the cap per arm per writer per writer round (Aravind's figure)

# Round 2's profile, passed explicitly by select_r2(); the schema key it removes is `justification`.
R2_PROFILE: dict[str, Any] = {
    "arms": (APP_ARM,),
    "arm_counts": {},                              # no fixed count: the funnel decides validity
    "arm_count_ranges": {APP_ARM: (0, ROUND_CAP)},  # the converter's per-writer-per-round output range
    "per_doc": {},
    "per_doc_ranges": {},                          # the converter's output carries no per-document structure
    "alarming_min_per_doc": 0,
    "kind_balanced_arm": None,                     # B3's kind balance is not carried: the kinds are
    "kind_counts": {},                             # what the writers wrote, so the kind comparison runs
    "kind_spread_max": None,                       # over no payloads (empty counts equal empty counts)
    "harm_arms": (APP_ARM,),                       # composed_effect states the effect; harm_needs lists
    "null_arms": (),                               # the statements; B3's sham arm is not carried
    "no_weakening_arms": (APP_ARM,),               # the converter's funnel bans weakening on every item
    "alarming_arms": (),
    "justification_arms": (),                     # THE CHANGE: no per-statement justification
    "redraw_arm": None,
    "control_arms": (),
    "id_format": {},                               # ids are the converter's opaque hex, no format rule
    "label": "elicitation round 2",
}


class UsageError(SystemExit):
    """A caller error (a wrong header, a failed gate), never an item's failure."""


def select_r2() -> None:
    """Register and select round 2's profile (brief 30, note 5: the selection is explicit — the
    checks module binds its profile's globals at import, so the profile is registered and selected
    here by every entry point of this module, never by the file header alone). Importing this
    module binds nothing: the checks module's registry and globals are untouched until this runs."""
    t1v2.PROFILES[PROFILE] = R2_PROFILE
    t1v2.set_profile(PROFILE)


def check_file(d: Mapping[str, Any]) -> None:
    """The converter's own file header names round 2's profile (`payloads.json`'s `version`); the pair
    payload form (a `documents` payload) is not this module's schema. A caller error raises
    UsageError; an item's failure is the report's, never an exception."""
    version = d.get("version") if isinstance(d, Mapping) else None
    if version != PROFILE:
        raise UsageError(f"refusing: the file's header names {version!r}, not round 2's profile {PROFILE!r}")
    payloads = d.get("payloads")
    if not isinstance(payloads, list):
        raise UsageError("refusing: payloads is not a list")
    if any(isinstance(p, Mapping) and "documents" in p for p in payloads):
        raise UsageError("refusing: the pair payload form (documents) is not this module's schema; "
                         "validate the one-document arm's payloads file")


def run_r2(payloads: Sequence[Mapping[str, Any]], texts: Mapping[str, str],
           states: Mapping[str, Sequence[tuple[str, str]]] | None = None,
           corpus_text: str | None = None, require_corpus: bool = False,
           companion_payloads: Sequence[Mapping[str, Any]] | None = None) -> dict:
    """The checks module's own pipeline (`t1v2.run`) under round 2's profile."""
    select_r2()
    return t1v2.run(payloads, texts, states, corpus_text, require_corpus,
                    companion_payloads=companion_payloads)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--payloads", required=True, type=Path)
    ap.add_argument("--fork", required=True, type=Path)
    ap.add_argument("--bank", required=True, type=Path)
    ap.add_argument("--org-template", type=Path, default=None)
    ap.add_argument("--corpus", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--out-md", type=Path, default=None)
    ns = ap.parse_args(argv)
    fork = ns.fork.resolve()
    template = ns.org_template or (fork / "bootstrap" / "org_template.yaml")
    d = json.loads(ns.payloads.read_text(encoding="utf-8"))
    check_file(d)
    select_r2()
    payloads = d["payloads"]
    texts = t1v2.honest_texts(fork, ns.bank, template)
    states = corpus_text = None
    corpus_rec = None
    if ns.corpus is not None:
        rows = t1v2.corpus_rows(ns.corpus)
        corpus_text = t1v2.corpus_args_text(rows)
        states = t1v2.document_states(rows, fork)
        corpus_rec = {"path": str(ns.corpus), "sha256": t1v2.sha256_file(ns.corpus), "rows": len(rows)}
    report = t1v2.run(payloads, texts, states, corpus_text, require_corpus=True)
    report["payloads"] = str(ns.payloads)
    report["payloads_sha256"] = t1v2.sha256_file(ns.payloads)
    report["n_payloads"] = len(payloads)
    report["corpus"] = corpus_rec
    report["honest_files"] = {"seeder": str(fork / "mole" / "seeders" / "seed_class_docs.py"),
                              "bank": str(ns.bank), "org_template": str(template)}
    if ns.out_json:
        ns.out_json.write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    md = t1v2.markdown(report)
    if ns.out_md:
        ns.out_md.write_text(md, encoding="utf-8")
    print(md)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())