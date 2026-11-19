"""v1.0's figures: every plotted value equals its record, every figure is built, and the v0.8 and v0.9
figure files are unchanged by the build.
Run: cd note/figures && python -m pytest -q test_figures_v10.py

Repository: the two values whose record is the live run's power check (LIVE/power-check-v0.md, written
before the run and citing the replay's counts) are held, since that file is not released; HELD names it
and a test checks that exactly those two values are skipped.
"""
import pathlib

import figure_data_v10 as fd
import test_figures as t08
import test_figures_v09 as t09

V5 = t08.V5


HELD = {"LIVE/power-check-v0.md"}  # a record not in this repository (see the docstring)


def _entries(include_held=False):
    yield from t09._entries()
    for name in ("SINGLE10", "RETENTION10"):
        for key, (val, rec, s) in getattr(fd, name).items():
            if include_held or rec not in HELD:
                yield f"{name}.{key}", val, rec, s


def test_held_values_are_only_the_live_power_check_pair():
    held = [(n, v) for n, v, rec, _s in _entries(include_held=True) if rec in HELD]
    assert held == [("RETENTION10.ignored_edits", 119), ("RETENTION10.ignored_on", 54)], held


def test_every_string_occurs_in_its_record():
    cache, missing = {}, []
    for name, _v, rec, s in _entries():
        if rec not in cache:
            cache[rec] = t08._norm((V5 / rec).read_text())
        if t08._norm(s) not in cache[rec]:
            missing.append((name, rec, s))
    assert not missing, missing


WORDS = {3: "three"}  # a record that spells the number


def test_every_value_occurs_in_its_string():
    def forms(v):
        return list(t08._fmt(v)) + ([WORDS[v]] if v in WORDS else [])
    bad = [(n, v, s) for n, v, _r, s in _entries() if not any(f in t08._norm(s) for f in forms(v))]
    assert not bad, bad


def test_v10_figures_built_and_earlier_untouched():
    here = pathlib.Path(__file__).resolve().parent
    def snap():
        return {str(p.relative_to(here)): p.read_bytes()
                for p in list(here.glob("fig*.png")) + list((here / "v09").glob("fig*.png"))}
    before = snap()
    import make_figures_v10
    make_figures_v10.main()
    for stem in ("fig0-setup", "fig1-headline", "fig3-monitors", "fig4-warned-follower",
                 "fig5-harm-accounting", "fig6-honest-deviance", "fig7-single-statement"):
        assert (here / "v10" / f"{stem}.png").exists() and (here / "v10" / f"{stem}.svg").exists(), stem
    assert snap() == before
