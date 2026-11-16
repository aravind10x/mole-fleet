"""Every value plotted in the note's figures, with the record it comes from.

Each entry is (value, record path relative to work/stage3/v5/, exact string that
occurs in that record). `test_figures.py` checks every string against its record
and every value against its string. Counts and shares only; no plant text.
"""

# Paths are relative to results/stage3/v5/ in the repository (work/stage3/v5/ in the project).
J1 = "P1/joins-v1.md"
J0 = "P1/joins-v0.md"
FT = "FT/ft-results-v1.md"
W1 = "P2/result-W-v1.md"
W0 = "P2/result-W.md"
H = "P2/result-H.md"
S3T = "S3/s3-table-v1-public.md"
DEC = "P2/result-H.md"  # repository: re-pointed from the decisions log (not released) to the block H result
RET = "P3/retention-v0.md"
USE = "P3/result-use-v1.md"

# Figure 1: the headline, routine and middle plants (48), followers mixed equally.
HEADLINE = {
    "carried_raw": (0.799, FT, "| RM uptake, mixture (48 payloads) | 0.799 [0.701, 0.885] |"),
    "acted_lo": (0.771, J1, "| both audits, lower (positive lower, unclear not acting) | 0.771 [0.710, 0.830] |"),
    "acted_hi": (0.835, J1, "| both audits, upper (positive upper, unclear acting) | 0.835 [0.772, 0.897] |"),
    "missed_raw": (0.295, FT, "| S | 0.295 [0.188, 0.413] |"),
    "missed_lo": (0.340, J1, "0.771 [0.710, 0.830] | 0.551 [0.374, 0.728] | 0.340 [0.230, 0.457]"),
    "missed_hi": (0.367, J1, "0.835 [0.772, 0.897] | 0.645 [0.478, 0.832] | 0.367 [0.249, 0.492]"),
}

# Figure 2: acted on and missed by potential consequence class (reader A), both audits.
CLASSES = {
    "serious": {"n": (25, J1, "| S3 (25 / 8) |"),
                "lo": (0.187, J1, "0.187 [0.062, 0.329]"), "hi": (0.213, J1, "0.213 [0.067, 0.373]")},
    "material": {"n": (17, J1, "| S2 (17 / 0) |"),
                 "lo": (0.459, J1, "0.459 [0.268, 0.647]"), "hi": (0.489, J1, "0.489 [0.293, 0.685]")},
    "minor": {"n": (6, J1, "| S1 (6 / 0) |"),
              "lo": (0.642, J1, "0.642 [0.540, 0.823]"), "hi": (0.666, J1, "0.666 [0.582, 0.833]")},
}

# Figure 3: the raw missed-and-carried share under each monitor (shares only; no rule figure).
MONITORS = [
    # label, point, lo, hi, record, string
    ("Opus 4.8, document view, 10%", 0.295, 0.188, 0.413, J0, "0.295 [0.188, 0.413]"),
    ("GPT-6 Sol, document view, 10%", 0.431, 0.306, 0.559, J0, "0.431 [0.306, 0.559]"),
    ("GLM 5.3, document view, 10%", 0.455, 0.330, 0.580, J0, "0.455 [0.330, 0.580]"),
    ("Sonnet 5, document view, 10%", 0.615, 0.486, 0.747, J0, "0.615 [0.486, 0.747]"),
    ("Opus 4.8, per-author view", 0.431, 0.299, 0.556, J0, "| per-agent view, P_author | 0.431 [0.299, 0.556] |"),
]
# Stricter rules on Opus 4.8's recorded scores: a range over how ties fall (not an interval).
STRICTER = [
    ("Opus 4.8, document view, 5%", 0.337, 0.420, FT, "5 percent rule: S 0.337 (ties flagged) to 0.420 (ties missed)"),
    ("Opus 4.8, document view, 2%", 0.420, 0.549, J0, "| ties missed | 0.549 [0.427, 0.681] |"),
]
STRICTER_CHECK = [(0.420, J0, "| ties flagged | 0.420 [0.299, 0.552] |")]

# Figure 4: the warned follower.
WARNED = {
    "literal_unwarned": (0.785, W1, "| unwarned | both | 0.785 [0.691, 0.875] |"),
    "literal_warned": (0.701, W1, "| warned | both | 0.701 [0.611, 0.792] |"),
    "kimi_unwarned": (0.719, W1, "| unwarned | Kimi | | 0.719 [0.611, 0.823] |"),
    "kimi_warned": (0.672, W1, "| warned | Kimi | | 0.672 [0.563, 0.779] |"),
    "sol_unwarned": (0.636, W1, "| unwarned | Sol | | 0.636 [0.521, 0.756] |"),
    "sol_warned": (0.000, W1, "| warned | Sol | | 0.000 [0.000, 0.000] |"),
    "work_clean_unwarned": (0.946, W0, "| clean | 56 | 0.946 | 0.830 |"),
    "work_clean_warned": (0.830, W0, "| clean | 56 | 0.946 | 0.830 |"),
    "work_updated_unwarned": (0.927, W0, "| benign | 16 | 0.927 | 0.583 |"),
    "work_updated_warned": (0.583, W0, "| benign | 16 | 0.927 | 0.583 |"),
}

# Figure 5: the harm accounting, this world's measured terms (stated apart, not multiplied).
ACCOUNTING = {
    "retention_undone": (0, RET, "Applications: 184; composed 184; ended by an honest edit 0; censored 184."),
    "retention_n": (184, RET, "Applications: 184; composed 184; ended by an honest edit 0; censored 184."),
    "need_share": (0.0013, DEC, "the rule-defined need share has a mean of 0.0013 of all arrival weight"),
    "need_none": (35, DEC, "35 of the 54 payloads have no runnable task that needs their slot"),
    "need_of": (54, DEC, "35 of the 54 payloads have no runnable task that needs their slot"),
    "honest_carry": (0.500, H, "| need | 0.500 [0.329, 0.684] |"),
    "acted_lo": HEADLINE["acted_lo"],
    "acted_hi": HEADLINE["acted_hi"],
    "missed_lo": HEADLINE["missed_lo"],
    "missed_hi": HEADLINE["missed_hi"],
}

# Figure 6: honest writes their task does not license, by generator (MOLE released corpora, judge).
GENERATORS = [
    ("GPT-5.3", 0.136, 0.109, 0.165, S3T, "0.136 [0.109, 0.165] (81/596)"),
    ("Kimi K2.6", 0.625, 0.587, 0.664, S3T, "0.625 [0.587, 0.664] (375/600)"),
    ("Qwen", 0.632, 0.593, 0.672, S3T, "0.632 [0.593, 0.672] (378/598)"),
    ("DeepSeek", 0.759, 0.724, 0.793, S3T, "0.759 [0.724, 0.793] (455/600)"),
]
