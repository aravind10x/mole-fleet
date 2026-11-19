"""Values for note v0.9's figures: everything in figure_data.py, plus the single-statement figure.

Same form: (value, record path relative to results/stage3/v5/ (work/stage3/v5/ in the project), exact string in that record).
"""
from figure_data import *  # noqa: F401,F403

SS1 = "SS/result-SS-v1.md"
SS0 = "SS/result-SS.md"

# Figure 3 of v0.9: one statement against the full plant (frozen-state scores; their own fresh baseline).
SINGLE = {
    "missed_single": (0.750, SS0, "Missed as a single statement 36 of 48 (0.750)"),
    "missed_full": (0.354, SS0, "as the full plant 17 of 48 (0.354)"),
    "cm_single_lo": (0.359, SS1, "| single | 0.438 [0.309, 0.563] | 0.396 [0.278, 0.514] | 0.359 [0.253, 0.467] |"),
    "cm_single_hi": (0.438, SS1, "| single | 0.438 [0.309, 0.563] | 0.396 [0.278, 0.514] | 0.359 [0.253, 0.467] |"),
    "cm_full_lo": (0.205, SS1, "| full plant | 0.236 [0.132, 0.347] | 0.229 [0.128, 0.337] | 0.205 [0.114, 0.302] |"),
    "cm_full_hi": (0.236, SS1, "| full plant | 0.236 [0.132, 0.347] | 0.229 [0.128, 0.337] | 0.205 [0.114, 0.302] |"),
}
