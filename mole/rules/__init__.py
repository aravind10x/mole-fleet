"""Release-workflow policy rules (defender side).

`dossier.build_release_dossier` assembles everything about one production
deployment from the audit log plus manager state (live ctx or a loaded
managers.json); `release_rules.run_rules` applies the policy checks
(coverage minimum, change authorisation, separation of duties) to it.
"""
from .dossier import build_release_dossier
from .release_rules import RULES, run_rules

__all__ = ["RULES", "build_release_dossier", "run_rules"]
