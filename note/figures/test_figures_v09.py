"""v0.9's figures: every plotted value equals its record, and every figure is built.
Run: cd note/figures && python -m pytest -q test_figures_v09.py
"""
import pathlib

import figure_data_v09 as fd
import test_figures as t08

V5 = t08.V5


def _entries():
    yield from t08._entries()
    for key, (val, rec, s) in fd.SINGLE.items():
        yield f"SINGLE.{key}", val, rec, s


def test_every_string_occurs_in_its_record():
    cache, missing = {}, []
    for name, _v, rec, s in _entries():
        if rec not in cache:
            cache[rec] = t08._norm((V5 / rec).read_text())
        if t08._norm(s) not in cache[rec]:
            missing.append((name, rec, s))
    assert not missing, missing


def test_every_value_occurs_in_its_string():
    bad = [(n, v, s) for n, v, _r, s in _entries() if not any(f in t08._norm(s) for f in t08._fmt(v))]
    assert not bad, bad


def test_v09_figures_built_and_v08_untouched():
    here = pathlib.Path(__file__).resolve().parent
    before = {p.name: p.read_bytes() for p in here.glob("fig*.png")}
    import make_figures_v09
    make_figures_v09.main()
    out = here / "v09"
    for stem in ("fig0-setup", "fig1-headline", "fig3-monitors", "fig4-warned-follower",
                 "fig5-harm-accounting", "fig6-honest-deviance", "fig7-single-statement"):
        assert (out / f"{stem}.png").exists() and (out / f"{stem}.svg").exists(), stem
    after = {p.name: p.read_bytes() for p in here.glob("fig*.png")}
    assert before == after
