"""Every plotted value equals its record. Run: cd note/figures && python -m pytest -q test_figures.py"""
import pathlib
import re

import figure_data as fd

V5 = pathlib.Path(__file__).resolve().parents[2] / "results" / "stage3" / "v5"


def _norm(s):
    return re.sub(r"\s+", " ", s.replace("−", "-").replace("**", "").replace("`", "")).strip()


def _entries():
    for name in ("HEADLINE", "WARNED", "ACCOUNTING"):
        for key, (val, rec, s) in getattr(fd, name).items():
            yield f"{name}.{key}", val, rec, s
    for cls, d in fd.CLASSES.items():
        for key, (val, rec, s) in d.items():
            yield f"CLASSES.{cls}.{key}", val, rec, s
    for label, p, lo, hi, rec, s in fd.MONITORS:
        for v in (p, lo, hi):
            yield f"MONITORS.{label}", v, rec, s
    for label, lo, hi, rec, s in fd.STRICTER:
        yield f"STRICTER.{label}", hi, rec, s
    for val, rec, s in fd.STRICTER_CHECK:
        yield "STRICTER_CHECK", val, rec, s
    for label, p, lo, hi, rec, s in fd.GENERATORS:
        for v in (p, lo, hi):
            yield f"GENERATORS.{label}", v, rec, s


def _fmt(v):
    if isinstance(v, int):
        return {str(v)}
    return {f"{v:.3f}", f"{v:.4f}", f"{v:g}"}


def test_every_string_occurs_in_its_record():
    cache = {}
    missing = []
    for name, _v, rec, s in _entries():
        if rec not in cache:
            cache[rec] = _norm((V5 / rec).read_text())
        if _norm(s) not in cache[rec]:
            missing.append((name, rec, s))
    assert not missing, missing


def test_every_value_occurs_in_its_string():
    bad = []
    for name, v, _rec, s in _entries():
        if not any(f in _norm(s) for f in _fmt(v)):
            bad.append((name, v, s))
    assert not bad, bad


def test_stricter_lower_ends_are_in_records():
    # The 5 percent range's lower end is in its own string; the 2 percent range's lower end is STRICTER_CHECK.
    assert "0.337" in fd.STRICTER[0][4]
    assert fd.STRICTER[1][1] == fd.STRICTER_CHECK[0][0]


def test_figures_exist_after_build():
    out = pathlib.Path(__file__).resolve().parent
    import make_figures
    make_figures.main()
    for n in range(0, 7):
        assert any(out.glob(f"fig{n}-*.png")), n
        assert any(out.glob(f"fig{n}-*.svg")), n
