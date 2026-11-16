"""Print or check where each number in the note comes from.

    python note/numbermap.py list            # one line per row
    python note/numbermap.py show N05        # the record lines (or values) that hold row N05's numbers
    python note/numbermap.py check           # every released row: record present, locators found, numbers present
    python note/numbermap.py table           # the map as a Markdown table

The map is note/numbers-v0.json. Paths are relative to the repository root.
Standard library only.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP = Path(__file__).resolve().parent / "numbers-v0.json"


def norm(s: str) -> str:
    """Compare text the way the trace does: unicode minus as '-', no bold or code marks, one space."""
    s = s.replace("−", "-").replace("**", "").replace("`", "").replace("\\|", "|")
    return re.sub(r"[ \t]+", " ", s)


def load_map(path: Path = MAP) -> dict:
    return json.loads(path.read_text())


def find(row: dict, root: Path = ROOT) -> list[tuple[dict, list[str] | None]]:
    """For each locator, the matching record lines or values (None when not found)."""
    out = []
    rec = row.get("record")
    for loc in row.get("locate", []):
        if "line" in loc:
            text = norm((root / rec).read_text(errors="replace"))
            needle = norm(loc["line"]).strip()
            hits = [ln.strip() for ln in text.splitlines() if needle in ln]
            if not hits:  # a locator may span a wrapped table cell; fall back to the whole text
                hits = [needle] if needle in re.sub(r"\s+", " ", text) else []
            out.append((loc, hits or None))
        elif "json_expr" in loc:
            d = json.loads((root / rec).read_text())
            val = eval(loc["json_expr"], {"__builtins__": {"sum": sum, "len": len, "min": min, "max": max}}, {"d": d})
            out.append((loc, [str(val)]))
        elif "pytest" in loc:
            out.append((loc, ["run: python -m pytest -q " + loc["pytest"]]))
    return out


def number_in(num: str, text: str) -> bool:
    n = num.replace("−", "").lstrip("-+")
    return re.search(r"(?<![\d.])" + re.escape(n) + r"(?![\d])", text) is not None


def check_row(row: dict, root: Path = ROOT) -> list[str]:
    errs = []
    if row["status"] != "released":
        return errs
    rec = row.get("record")
    if not rec or not (root / rec).exists():
        return [f"{row['id']}: record missing: {rec}"]
    if any("pytest" in loc for loc in row["locate"]):
        return errs  # checked by running the named test
    found = find(row, root)
    text = " ".join(" ".join(h) for _, h in found if h)
    for loc, hits in found:
        if hits is None:
            errs.append(f"{row['id']}: locator not found in {rec}: {loc}")
    for num in row.get("numbers", []):
        if not number_in(num, text) and not number_in(num, row.get("derived", "")):
            errs.append(f"{row['id']}: number {num} not in the located lines")
    return errs


def run_pytests(doc: dict, root: Path = ROOT) -> list[str]:
    errs = []
    for row in doc["rows"]:
        for loc in row.get("locate", []):
            if "pytest" in loc:
                p = root / loc["pytest"]
                r = subprocess.run([sys.executable, "-m", "pytest", "-q", p.name], cwd=p.parent,
                                   capture_output=True, text=True)
                if r.returncode != 0:
                    errs.append(f"{row['id']}: {loc['pytest']} failed:\n{r.stdout[-2000:]}")
    return errs


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cmd = argv[0] if argv else "list"
    doc = load_map()
    rows = {r["id"]: r for r in doc["rows"]}
    if cmd == "list":
        for r in doc["rows"]:
            print(f"{r['id']:6} {r['status']:18} {r.get('record') or '-'}  {r['as_written']}")
        return 0
    if cmd == "show":
        r = rows[argv[1]]
        print(f"{r['id']}  {r['as_written']}\nrecord: {r.get('record')}  status: {r['status']}")
        for loc, hits in (find(r) if r["status"] == "released" else []):
            for h in hits or ["NOT FOUND: " + json.dumps(loc)]:
                print("  " + h)
        if r.get("derived"):
            print("  derived: " + r["derived"])
        if r.get("note"):
            print("  note: " + r["note"])
        return 0
    if cmd == "check":
        errs = [e for r in doc["rows"] for e in check_row(r)]
        if "--no-pytest" not in argv:
            errs += run_pytests(doc)
        n = sum(1 for r in doc["rows"] if r["status"] == "released")
        for e in errs:
            print("FAIL " + e)
        print(f"{n} released rows checked; {len(errs)} failures; "
              f"{sum(1 for r in doc['rows'] if r['status'] != 'released')} rows not released (design, slot, not in repository)")
        return 1 if errs else 0
    if cmd == "table":
        print("| id | where in the note | as written | record | how to print it | status |")
        print("|---|---|---|---|---|---|")
        for r in doc["rows"]:
            how = f"`python note/numbermap.py show {r['id']}`" if r["status"] == "released" else "—"
            rec = f"`{r['record']}`" if r.get("record") else "—"
            print(f"| {r['id']} | {r['section']} | {r['as_written']} | {rec} | {how} | {r['status']} |")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
