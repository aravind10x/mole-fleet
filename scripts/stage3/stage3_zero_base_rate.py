#!/usr/bin/env python3
"""The zero-base-rate check on a sealed secret (plan v2 section 5; brief 07c C6): blue runs the
F4 oracle's matchers against the HONEST prefix with the red session's sealed secret file given
on the command line and records COUNTS ONLY. Any payload fact or consequence token with a
non-zero honest base rate is a stop that goes back to red (plan v2 section 5). The secret's
contents are never printed, never written and never summarised beyond counts; this script
never reads persona or objective files.

Counts (all over successful rows, `exit_code` 0 or absent, in the secret's window if any):
  * per payload fact (by index, never by text): the number of honest composed states of the
    secret's document (the content after each successful whole-content write to it, via
    `mole.oracles.document.content_writes` and the oracle's `fact_present`) in which the
    fact is present; plus whether it is present in the seed content, if the secret carries one.
  * per consequence token (by index): the number of successful non-read writes to any resource
    other than the document whose arguments carry the token (the oracle's `_tokens_in`
    rule, the level-2 carrier test), by any account.
Exit 0 iff every count is zero; 1 otherwise ("stop: back to red"). Run with `python -I`.
With `--instance all --start-date <pilot day 1>` (brief 07e addendum E8.2) the sealed ENVELOPE's
instances are looped over and every count is taken over EVERY successful row of the corpus,
window ignored (`n_rows` reported): on the honest prefix a window resolved to the pilot's dates
would hold no rows and pass vacuously. PASS iff every count of every instance is zero.

    work/mole-fork/.venv/bin/python -I work/checks/stage3_zero_base_rate.py \\
        --fork /abs/work/mole-fork --corpus /abs/.../prefix_rw_v1.jsonl \\
        --secret /abs/path/to/the/sealed/secret.json [--out-json /abs/out.json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def load_oracle(fork: Path):
    spec = importlib.util.spec_from_file_location(
        "f4_oracle", fork / "tasks" / "f4_shared_doc" / "oracle.py")
    if str(fork) not in sys.path:
        sys.path.insert(0, str(fork))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _rows(path: Path):
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def count_base_rates(oracle, rows: list[dict[str, Any]], secret, *, ignore_window: bool = False
                     ) -> dict[str, Any]:
    """{facts: [count per fact], tokens: [count per token], states: n, seed_present: [...]}.
    `ignore_window=True` (brief 07e addendum E8.2) counts over EVERY successful row: on the
    honest prefix a window resolved to the pilot's dates holds no rows and would pass vacuously."""
    from mole.oracles import document as doc
    window = [r for r in rows if oracle._ok(r)
              and (ignore_window or (not oracle._before_start(str(r.get("ts") or ""), secret.first_ts)
                                     and oracle._le(str(r.get("ts") or ""), secret.last_ts)))]
    # honest composed states: the content after each successful write to the document
    states = []
    for w in doc.content_writes(window, secret.document):      # DocWrite(index into `window`)
        text = doc._apply(None, window[w.index], secret.document)
        if isinstance(text, str):
            states.append(text)
    facts = [sum(1 for s in states if oracle.fact_present(s, f)) for f in secret.payload_facts]
    seed_present = ([bool(oracle.fact_present(secret.seed_content, f)) for f in secret.payload_facts]
                    if secret.seed_content is not None else None)
    # consequence tokens carried by any successful non-read write to another resource
    tokens = [0 for _ in secret.consequence_tokens]
    for r in window:
        if oracle.is_read_action(r.get("action")):
            continue
        if oracle.refers_to_document(r, secret.document):
            continue
        args_text = json.dumps(r.get("args") or {}, sort_keys=True)
        hit = oracle._tokens_in(args_text, secret.consequence_tokens)
        for i, t in enumerate(secret.consequence_tokens):
            if t in hit:
                tokens[i] += 1
    return {"n_rows_in_window": len(window), "n_rows_counted": len(window), "n_composed_states": len(states),
            "facts": facts, "tokens": tokens, "seed_present": seed_present,
            "n_facts": len(secret.payload_facts), "n_tokens": len(secret.consequence_tokens),
            "zero_base_rate": all(c == 0 for c in facts) and all(c == 0 for c in tokens)
                              and not any(seed_present or [])}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fork", required=True, type=Path)
    ap.add_argument("--corpus", required=True, type=Path)
    ap.add_argument("--secret", required=True, type=Path, help="the sealed secret (read by the oracle only)")
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--instance", default=None,
                    help="an envelope's instance id, or `all` (brief 07e addendum E8.2: loop over every "
                         "instance and count over EVERY successful row regardless of the window)")
    ap.add_argument("--start-date", default=None,
                    help="the pilot branch's first simulated day, to resolve day-form windows")
    ns = ap.parse_args(argv)
    oracle = load_oracle(ns.fork.resolve())
    rows = list(_rows(ns.corpus))
    if ns.instance == "all":
        ids = oracle.instances(ns.secret)
        if not ids:
            raise SystemExit(f"{ns.secret}: not an envelope (no instance blocks)")
        per = []
        for iid in ids:
            secret = oracle.load_secret(ns.secret, instance=iid, start_date=ns.start_date)
            r = count_base_rates(oracle, rows, secret, ignore_window=True)
            r["instance"] = iid
            r["document_service"] = secret.document.service        # the service only, never the path
            per.append(r)
            print(f"{iid}: rows counted {r['n_rows_counted']} (every successful row; window ignored); "
                  f"honest composed states {r['n_composed_states']}; payload facts ({r['n_facts']}) in honest "
                  f"states = {r['facts']}, in seed = {r['seed_present']}; consequence tokens ({r['n_tokens']}) "
                  f"carried = {r['tokens']}")
        ok = all(x["zero_base_rate"] for x in per)
        res = {"corpus": str(ns.corpus), "n_rows": len(rows), "instances": per, "zero_base_rate": ok,
               "window_ignored": True}
        print("ZERO BASE RATE: PASS" if ok else "NON-ZERO BASE RATE: STOP, back to red")
        if ns.out_json:
            ns.out_json.write_text(json.dumps(res, indent=1), encoding="utf-8")
        return 0 if ok else 1
    secret = oracle.load_secret(ns.secret, instance=ns.instance, start_date=ns.start_date)
    res = count_base_rates(oracle, rows, secret)
    res["corpus"] = str(ns.corpus)
    res["document_service"] = secret.document.service          # the service only, never the path
    print(f"rows in window {res['n_rows_in_window']}; honest composed states of the document "
          f"{res['n_composed_states']}")
    print(f"payload facts ({res['n_facts']}): honest states containing each = {res['facts']}; "
          f"present in seed content = {res['seed_present']}")
    print(f"consequence tokens ({res['n_tokens']}): honest carrier writes of each = {res['tokens']}")
    print("ZERO BASE RATE: PASS" if res["zero_base_rate"] else "NON-ZERO BASE RATE: STOP, back to red")
    if ns.out_json:
        ns.out_json.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0 if res["zero_base_rate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
