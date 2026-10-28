"""Brief 07s part R (amendment B2): check the four pass files and aggregate them.

Reads the two stripped inputs, the four pass files and the rubric files (for hashes only).
Writes ratings-2.json, ratings-triples.json and ratings-2-summary.md beside this script.
Prints counts, checks and agreement numbers; never prints an item's text or reason.
Exits non-zero, writing nothing, if any pass file fails the id check.
"""
import collections
import hashlib
import json
import math
import os
import sys

D = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(D, "passes")

RATER = {"model": "claude-opus-5-5", "effort": "xhigh", "session": "local_a2747ac3-da65-4bf6-8f65-ff71add49e74"}
PASSES = {"agent_model": "fable (Fable 5.1, claude-fable-5-1)", "effort": "high",
          "subagent_type": "general-purpose", "context": "fresh"}
BAND_RULE = ("band = min(4, floor(score / 20)): 0-19 -> '0 to 20', 20-39 -> '20 to 40', "
             "40-59 -> '40 to 60', 60-79 -> '60 to 80', 80-100 -> '80 to 100'")


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_pass(path, idkey, input_ids):
    """Return ({id: (score, reason)}, problems)."""
    problems, rows = [], {}
    seen = collections.Counter()
    with open(path) as f:
        lines = f.read().splitlines()
    for n, line in enumerate(lines, 1):
        if not line.strip():
            problems.append(f"line {n}: blank")
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as e:
            problems.append(f"line {n}: not JSON ({e.msg})")
            continue
        if set(obj) != {idkey, "score", "reason"}:
            problems.append(f"line {n}: fields {sorted(obj)}")
        i, s, r = obj.get(idkey), obj.get("score"), obj.get("reason")
        seen[i] += 1
        if not (isinstance(s, int) and not isinstance(s, bool) and 0 <= s <= 100):
            problems.append(f"line {n}: score {s!r} not an integer 0..100")
        if not isinstance(r, str) or not r.strip() or "\n" in r:
            problems.append(f"line {n}: reason empty or not one line")
        rows[i] = (s, r)
    ids = set(input_ids)
    dup = [i for i, c in seen.items() if c > 1]
    missing = [i for i in input_ids if i not in seen]
    extra = [i for i in seen if i not in ids]
    if dup:
        problems.append(f"{len(dup)} ids more than once")
    if missing:
        problems.append(f"{len(missing)} input ids missing")
    if extra:
        problems.append(f"{len(extra)} ids not in the input")
    order_ok = [json.loads(l)[idkey] for l in lines if l.strip()] == list(input_ids)
    long_reasons = sum(1 for s, r in rows.values() if isinstance(r, str) and len(r.split()) > 25)
    return rows, problems, {"lines": len(lines), "file_order": order_ok, "reasons_over_25_words": long_reasons}


def avg_ranks(xs):
    order = sorted(range(len(xs)), key=lambda k: xs[k])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else float("nan")


def band(s):
    return min(4, s // 20)


def agreement(a, b):
    n = len(a)
    ba, bb = [band(x) for x in a], [band(x) for x in b]
    return {
        "n": n,
        "spearman": round(pearson(avg_ranks(a), avg_ranks(b)), 4),
        "mean_absolute_difference": round(sum(abs(x - y) for x, y in zip(a, b)) / n, 2),
        "band_within_one": round(sum(abs(x - y) <= 1 for x, y in zip(ba, bb)) / n, 4),
        "band_exact": round(sum(x == y for x, y in zip(ba, bb)) / n, 4),
        "pass1_mean": round(sum(a) / n, 2),
        "pass2_mean": round(sum(b) / n, 2),
    }


def consistency(groups, rows):
    """Count groups of identical items whose scores differ within one pass."""
    multi = [g for g in groups.values() if len(g) > 1]
    unequal = sum(1 for g in multi if len({rows[i][0] for i in g}) > 1)
    return {"groups_with_repeats": len(multi), "groups_with_unequal_scores": unequal}


def run(kind):
    if kind == "statements":
        inp, idkey = "stripped-statements-2.json", "statement_id"
        files = ("pass1-statements-2.jsonl", "pass2-statements-2.jsonl")
        out, section = "ratings-2.json", "2 (standalone visibility)"
    else:
        inp, idkey = "stripped-triples.json", "triple_id"
        files = ("pass1-triples.jsonl", "pass2-triples.jsonl")
        out, section = "ratings-triples.json", "2b (composition)"
    with open(os.path.join(D, inp)) as f:
        items = json.load(f)
    ids = [x[idkey] for x in items]
    passes, checks = [], {}
    for name in files:
        rows, problems, info = load_pass(os.path.join(P, name), idkey, ids)
        checks[name] = {"sha256": sha(os.path.join(P, name)), "problems": problems, **info}
        print(f"{name}: lines {info['lines']}, file order {info['file_order']}, "
              f"reasons over 25 words {info['reasons_over_25_words']}, problems {problems or 'none'}")
        passes.append(rows)
    if any(c["problems"] for c in checks.values()):
        print("id or format check failed; nothing written")
        sys.exit(1)
    if kind == "statements":
        key = lambda x: (x["document"], x["text"])
    else:
        key = lambda x: (x["document"], tuple((y["op"], y["anchor_or_region"], y["text"]) for y in x["statements"]))
    groups = collections.defaultdict(list)
    for x in items:
        groups[key(x)].append(x[idkey])
    cons = {name: consistency(groups, rows) for name, rows in zip(files, passes)}
    a = [passes[0][i][0] for i in ids]
    b = [passes[1][i][0] for i in ids]
    agr = agreement(a, b)
    per = {}
    for x in items:
        i = x[idkey]
        rec = {"document": x["document"]}
        if kind == "statements":
            rec["op"] = x["op"]
        else:
            rec["ops"] = [y["op"] for y in x["statements"]]
        rec["pass1"] = {"score": passes[0][i][0], "reason": passes[0][i][1]}
        rec["pass2"] = {"score": passes[1][i][0], "reason": passes[1][i][1]}
        per[i] = rec
    doc = {
        "brief": "07s part R, amendment B2",
        "written": "2026-10-28",
        "rubric_section_scored": section,
        "rubric": {"rubric.md": sha(os.path.join(D, "rubric.md")),
                   "rubric-passes-2.md": sha(os.path.join(D, "rubric-passes-2.md"))},
        "input": {"file": inp, "sha256": sha(os.path.join(D, inp)), "n": len(ids)},
        "rater_session": RATER,
        "passes": {**PASSES, "pass1_primary": files[0], "pass2_reliability": files[1], "checks": checks},
        "band_rule": BAND_RULE,
        "agreement": agr,
        "identical_items_consistency": cons,
        ("statements" if kind == "statements" else "triples"): per,
    }
    print(f"{out}: agreement {agr}; identical-item consistency {cons}")
    return out, doc, agr, cons


if __name__ == "__main__":
    results = {k: run(k) for k in ("statements", "triples")}
    for out, doc, _, _ in results.values():
        with open(os.path.join(D, out), "w") as f:
            json.dump(doc, f, indent=1, ensure_ascii=False)
            f.write("\n")
    lines = ["# Brief 07s part R (amendment B2): pass agreement", "",
             "Agreement between the two fresh-context passes (`fable`, high effort) on each input. "
             "Pass 1 is primary, pass 2 the reliability check. " + BAND_RULE + ".", "",
             "| Input | Rubric section | n | Spearman | Mean absolute difference | Band within one | Band exact |",
             "|---|---|---|---|---|---|---|"]
    for kind, label, section in (("statements", "`stripped-statements-2.json` (`ratings-2.json`)", "2"),
                                 ("triples", "`stripped-triples.json` (`ratings-triples.json`)", "2b")):
        out, _, agr, cons = results[kind]
        lines.append(f"| {label} | {section} | {agr['n']} | {agr['spearman']:.3f} | "
                     f"{agr['mean_absolute_difference']:.2f} | {agr['band_within_one']:.3f} | {agr['band_exact']:.3f} |")
    lines.append("")
    for kind, label in (("statements", "Single edits"), ("triples", "Triples")):
        out, _, agr, cons = results[kind]
        parts ="; ".join(f"{name}: {c['groups_with_unequal_scores']} of {c['groups_with_repeats']} groups unequal"
                          for name, c in cons.items())
        lines.append(f"{label}, identical items scored equally within each pass: {parts}.")
    lines.append("")
    with open(os.path.join(D, "ratings-2-summary.md"), "w") as f:
        f.write("\n".join(lines))
    print("ratings-2-summary.md written")
