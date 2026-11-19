"""Values for note v1.0's figures: everything in figure_data_v09.py, plus the changed single-statement
figure (carry rates, script count, in place of carried and missed) and the retention box's new terms.

Same form: (value, record path relative to results/stage3/v5/ (work/stage3/v5/ in the project), exact string in that record).
"""
from figure_data_v09 import *  # noqa: F401,F403

PCK = "LIVE/power-check-v0.md"  # written before the live run; assumption 6 cites the replay's counts only
SSU = "SS/result-SS-v1.md"

# Figure 3 of v1.0: one statement against the full plant.
SINGLE10 = {
    "missed_single": SINGLE["missed_single"],
    "missed_full": SINGLE["missed_full"],
    "carried_single": (0.639, SSU, "| single | both | 0.639 [0.517, 0.757] |"),
    "carried_full": (0.771, SSU, "| full plant | both | 0.771 [0.670, 0.854] |"),
}

# Figure 6 of v1.0: the retention box says what the replay is, beside the pilot's overwrites.
RETENTION10 = {
    "ignored_edits": (119, PCK, "119 edits aimed at text a plant had displaced (54 of 184 applications)"),
    "ignored_on": (54, PCK, "119 edits aimed at text a plant had displaced (54 of 184 applications)"),
    "pilot_overwrites": (3, "OW/ow-result.md",  # repository: the OW record, not the decisions log
                         "The forensics record lists three honest sessions that overwrote a planted line"),
}
