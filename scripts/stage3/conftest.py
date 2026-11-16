"""Fork only: make the helpers that live elsewhere in scripts/ importable from these tests.

In the project every module sits flat in work/checks/; in this repository some helpers live in scripts/ and
scripts/track_a|b/. The paths are appended, so a module in scripts/stage3/ always wins over a same-named one elsewhere.
"""
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent
for _p in (_SCRIPTS, _SCRIPTS / "track_a", _SCRIPTS / "track_b"):
    if str(_p) not in sys.path:
        sys.path.append(str(_p))
