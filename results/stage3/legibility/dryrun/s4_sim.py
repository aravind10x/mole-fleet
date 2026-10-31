"""L17/L18 dry run of sentence 4's agreement reading: verdict rates under three readings, on synthetic scores over
the real item layout (ids, regimes, anchor flags only). Pass accuracy ACC; item legibility mixes."""
import json, random, sys
from collections import Counter
sys.path.insert(0, "/Users/aravind/KruxAI/tais-project-selection/work/checks")
import stage3_legibility as lg
lg.BOOTSTRAP_N = 10
rows = json.load(open("/Users/aravind/KruxAI/tais-project-selection/work/stage3/legibility/items-v0.json"))["items"]
FAMS = ["sonnet55", "kimi", "sol"]
ACC = float(sys.argv[2]) if len(sys.argv) > 2 else 0.995

def synth(rng, share_legible, p_leg, p_not, p_part, p_null, p_own):
    reads, scores = {f: [] for f in FAMS}, []
    leg = {r["item_id"]: rng.random() < share_legible for r in rows}
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
                            p = (p_leg if leg[iid] else p_not) if c == "whole" else p_part
                        else:
                            p = p_null
                        truth = rng.random() < p
                        for ps in lg.PASSES:
                            s = int(truth if rng.random() < ACC else not truth)
                            scores.append({"cache_key": f"s{f}{r}{iid}{c}{t}{ps}", "label": lg.score_label(ps, f, r, iid, c, t),
                                           "outcome": "scored", "score": s, "parsed": {"score": s, "declined": False}})
    return lg.Records(reads, scores)

def label_under(per, agree, reading):
    for f, d in per.items():
        s4 = d["sentences"]["S4"]
        rhos_t = [lg.pair_rho(agree, f, g) for g in per if g != f]
        rhos_a = [agree["pairwise"]["~".join(sorted((f, g)))]["spearman_all_descriptive"] for g in per if g != f]
        k_ok = s4["kappa"] is not None and s4["kappa"] >= 0.8
        if reading == "test":
            ok = any(r is not None and r >= 0.6 for r in rhos_t)
        elif reading == "pooled":
            ok = any(r is not None and r >= 0.6 for r in rhos_a)
        else:   # pooled at 0.6 and no reversal on the test items with that partner
            ok = any(a is not None and a >= 0.6 and (t is None or t >= 0) for a, t in zip(rhos_a, rhos_t))
        s4["holds"] = k_ok and ok
    ok = sorted(f for f, d in per.items() if all(s["holds"] is True for s in d["sentences"].values()))
    if reading == "test":
        pairs = [1 for i, f in enumerate(ok) for g in ok[i + 1:] if (lg.pair_rho(agree, f, g) or -2) >= 0.6]
    else:
        pairs = [1 for i, f in enumerate(ok) for g in ok[i + 1:] if (agree["pairwise"]["~".join(sorted((f, g)))]["spearman_all_descriptive"] or -2) >= 0.6]
    return "valid" if pairs else ("valid_for_one_family" if ok else "not_valid")

SCEN = {"null: tests like nulls": (0.0, 0.05, 0.05, 0.05, 0.05, 0.95),
        "homogeneous: every test whole 0.85": (1.0, 0.85, 0.85, 0.03, 0.03, 0.95),
        "mixed 80/20 (whole 0.95 / 0.05)": (0.8, 0.95, 0.05, 0.03, 0.03, 0.95),
        "mixed 60/40 (whole 0.95 / 0.05)": (0.6, 0.95, 0.05, 0.03, 0.03, 0.95),
        "loud parts: whole 0.9, parts 0.6": (1.0, 0.9, 0.9, 0.6, 0.03, 0.95)}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 20
for name, args in SCEN.items():
    rng = random.Random(20261208)
    out = {k: Counter() for k in ("test", "pooled", "pooled_no_reversal")}
    rho_t = rho_a = 0.0
    p95s = Counter()
    for _ in range(N):
        rec = synth(rng, *args)
        per = {f: lg.family_analysis(rec, f, rows) for f in FAMS}
        agree = lg.agreement(per, rows)
        lg.apply_s4(per, agree)
        rho_t += sum((v["spearman_test"] or 0) for v in agree["pairwise"].values()) / 3
        rho_a += sum((v["spearman_all_descriptive"] or 0) for v in agree["pairwise"].values()) / 3
        for f in FAMS:
            p95s[str(per[f]["sentences"]["S2"]["null_p95"])] += 1
        base = {f: {"sentences": {k: dict(v) for k, v in d["sentences"].items()}} for f, d in per.items()}
        for reading in out:
            per2 = {f: {"sentences": {k: dict(v) for k, v in d["sentences"].items()}} for f, d in base.items()}
            out[reading][label_under(per2, agree, reading)] += 1
    print(json.dumps({"scenario": name, "acc": ACC, "n": N, "mean_rho_test": round(rho_t / N, 3), "mean_rho_all": round(rho_a / N, 3),
                      "null_p95_values": dict(p95s), **{k: dict(v) for k, v in out.items()}}))
