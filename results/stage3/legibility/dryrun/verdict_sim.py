"""L17 dry run of brief 23's verdict rules (full and downstream) on synthetic scores over the real item layout
(ids, regimes, anchor flags from items-v0.json; no text). Prints outcome rates per scenario."""
import json, random, sys
from collections import Counter
sys.path.insert(0, "/Users/aravind/KruxAI/tais-project-selection/work/checks")
import stage3_legibility as lg
lg.BOOTSTRAP_N = 20
rows = json.load(open("/Users/aravind/KruxAI/tais-project-selection/work/stage3/legibility/items-v0.json"))["items"]
FAMS = ["sonnet55", "kimi", "sol"]
ACC = float(sys.argv[2]) if len(sys.argv) > 2 else 0.95

def synth(rng, p_whole_test, p_part_test, p_null, p_own, item_effect):
    reads, scores = {f: [] for f in FAMS}, []
    eff = {r["item_id"]: rng.random() for r in rows}   # shared item legibility, so families can agree
    for f in FAMS:
        for row in rows:
            iid = row["item_id"]
            for r in lg.repeats_of(row):
                for c in lg.CONDS:
                    reads[f].append({"cache_key": f"{f}{r}{iid}{c}", "label": lg.read_label(r, iid, c), "outcome": "scored",
                                     "parsed": {"answer": "a", "declined_token": False}})
                    for t in lg.scoring_targets(row, r):
                        if t == "own":
                            p = p_own
                        elif row["regime"] in lg.TEST_REGIMES:
                            # an item's legibility moves its whole condition only (parts stay quiet)
                            p = min(1, max(0, p_whole_test + item_effect * (eff[iid] - 0.5))) if c == "whole" else p_part_test
                        else:
                            p = p_null
                        truth = rng.random() < p          # the answer is creditable or not
                        for ps in lg.PASSES:
                            s = int(truth if rng.random() < ACC else not truth)   # each pass reads it with accuracy ACC
                            scores.append({"cache_key": f"s{f}{r}{iid}{c}{t}{ps}", "label": lg.score_label(ps, f, r, iid, c, t),
                                           "outcome": "scored", "score": s, "parsed": {"score": s, "declined": False}})
    return lg.Records(reads, scores)

SCEN = {"null (test like nulls)": (0.05, 0.05, 0.05, 0.9, 0.0),
        "weak (whole 0.4, parts 0.1)": (0.4, 0.1, 0.05, 0.9, 0.6),
        "legible (whole 0.8, parts 0.1)": (0.8, 0.1, 0.05, 0.9, 0.6),
        "loud parts (whole 0.8, parts 0.6)": (0.8, 0.6, 0.05, 0.9, 0.6),
        "strict scorer (own 0.6)": (0.8, 0.1, 0.05, 0.6, 0.6)}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
for name, args in SCEN.items():
    rng = random.Random(20261207)
    full, down, dis, fail = Counter(), Counter(), Counter(), Counter()
    for _ in range(N):
        res = lg.analyse(synth(rng, *args), rows, FAMS)
        full[res["verdict"]["label"]] += 1
        down[res["verdict_downstream"]["label"]] += 1
        dis["any_disagreement"] += bool(res["resolved_disagreements"])
        for f, d in res["per_family"].items():
            dis["kappa_sum"] += d["sentences"]["S4"]["kappa"] or 0
            dis["agree_sum"] += d["sentences"]["S4"]["agreement_test"] or 0
        for f, ks in res["verdict"]["failing_by_family"].items():
            for k in ks:
                fail[k] += 1
    print(json.dumps({"scenario": name, "n": N, "acc": ACC, "full": dict(full), "downstream": dict(down), **dis, "family_sentence_fails": dict(fail)}))
