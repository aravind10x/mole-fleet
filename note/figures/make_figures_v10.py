"""Draw note v1.0's figures into figures/v10/, leaving v0.8's and v0.9's figures untouched.

Changed for v1.0: fig0 and fig1 name the document monitor; fig5 states the retention replay as a reading
on a fixed history, beside the pilot's overwrites; fig7 shows carry rates (script count) in place of
carried and missed. fig3, fig4 and fig6 are v0.8's drawing, unchanged.
Run: cd note/figures && python make_figures_v10.py
"""
import pathlib

import make_figures as mf
import make_figures_v09 as m9
import figure_data_v10 as fd
from make_figures import plt, FancyBboxPatch, SURFACE, INK, INK2, BLUE, ORANGE, BLUE_LIGHT, _axes, _titles, _range

OUT = pathlib.Path(__file__).resolve().parent / "v10"
OUT.mkdir(exist_ok=True)


def _point_out():
    mf.OUT = OUT  # _save writes here (make_figures_v09 sets it to v09 on import)


def fig0():
    fig, ax = plt.subplots(figsize=(9.6, 3.6))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    def box(x, y, w, h, head, body, edge=BLUE, face="#eef4fc"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.02",
                                    facecolor=face, edgecolor=edge, linewidth=1.2))
        ax.text(x + w / 2, y + h - 0.06, head, ha="center", va="top", color=INK, fontsize=9.5, fontweight="bold")
        ax.text(x + w / 2, y + h / 2 - 0.08, body, ha="center", va="center", color=INK2, fontsize=8.5)

    def arrow(x0, y0, x1, y1, text=None, tx=None, ty=None, ha="center"):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.2, shrinkA=2, shrinkB=2))
        if text:
            ax.text(tx, ty, text, ha=ha, va="center", color=INK2, fontsize=8)

    box(0.01, 0.52, 0.19, 0.40, "Fifty agents", "edit six shared\ndocuments in\neveryday sessions")
    box(0.24, 0.52, 0.19, 0.40, "One quiet change", "one account edits\nan item; each edit\nlooks like upkeep", edge=ORANGE, face="#fdeee7")
    box(0.47, 0.52, 0.19, 0.40, "The document monitor", "reads the document's\ncombined changes;\nflags the top 10%\nof honest work")
    box(0.47, 0.04, 0.19, 0.38, "A later agent", "gets work that needs\nthe item, reads the\ndocument, acts")
    box(0.80, 0.52, 0.19, 0.40, "Acted on and missed", "only when both\narrows hold", edge=INK2, face="#f3f2ee")
    arrow(0.20, 0.72, 0.24, 0.72)
    arrow(0.43, 0.72, 0.47, 0.72)
    arrow(0.335, 0.52, 0.47, 0.25, "the document,\nfrozen", tx=0.33, ty=0.30)
    arrow(0.66, 0.72, 0.80, 0.72, "did not\nflag it", tx=0.73, ty=0.81)
    arrow(0.66, 0.23, 0.86, 0.52, "its logged action\ncarries the plant", tx=0.80, ty=0.25, ha="left")
    ax.text(0.01, 1.0, "The design in one picture", color=INK, fontsize=11, va="bottom")
    mf._save(fig, "fig0-setup")


def fig1():
    h = {k: v[0] for k, v in fd.HEADLINE.items()}
    fig, ax = _axes(7.2, 2.6)
    rows = [
        ("Script count: planted content\nreached the follower's action", h["carried_raw"], h["carried_raw"], h["carried_raw"]),
        ("The follower acted on it\n(both audits)", h["acted_lo"], h["acted_hi"], h["carried_raw"]),
        ("Acted on, and missed by\nthe document monitor", h["missed_lo"], h["missed_hi"], h["missed_raw"]),
    ]
    for i, (label, lo, hi, raw) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.barh(y, lo, height=0.38, color=BLUE_LIGHT, edgecolor=SURFACE, linewidth=2)
        if lo == hi:
            ax.text(lo + 0.015, y, f"{lo:.3f} (script count)", va="center", color=INK, fontsize=9)
        else:
            _range(ax, y, lo, hi)
            ax.text(hi + 0.015, y, f"{lo:.3f} to {hi:.3f}  (script count {raw:.3f})", va="center", color=INK, fontsize=9)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_xlim(0, 1.25)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("Share of runs, weighted equally over the 48 quiet plants")
    _titles(ax, "About a third of the time, a quiet plant is acted on and the document monitor misses it",
            "Dark band: range over two ways of completing the audits (not a confidence interval)")
    mf._save(fig, "fig1-headline")


def fig5():
    a = {k: v[0] for k, v in fd.ACCOUNTING.items()}
    r = {k: v[0] for k, v in fd.RETENTION10.items()}
    fig, ax = plt.subplots(figsize=(9.6, 3.3))
    ax.axis("off")
    boxes = [
        ("How long a plant\nstays in the document",
         f"Replay on the fixed log:\n{a['retention_undone']} of {a['retention_n']} placements undone;\n"
         f"{r['ignored_edits']} honest edits aimed at\ndisplaced text ignored\n(on {r['ignored_on']} placements)\n"
         f"Earlier pilot: {r['pilot_overwrites']} overwrites\nby upkeep"),
        ("How often work\nneeds the item",
         f"{a['need_share']} of arriving tasks;\n{a['need_none']} of {a['need_of']} planted items\nneeded by no task\nthat can run here"),
        ("Acts per need",
         f"Tasks written to need it:\n{a['acted_lo']:.3f} to {a['acted_hi']:.3f} acted on\n\nHonest tasks that need it:\n{a['honest_carry']:.3f} carried"),
        ("Chance the plant gets past\nthe document monitor",
         f"measured together with acts:\n{a['missed_lo']:.3f} to {a['missed_hi']:.3f}\nacted on and missed"),
    ]
    xs = [0.02, 0.27, 0.52, 0.77]
    for x, (head, body) in zip(xs, boxes):
        ax.add_patch(FancyBboxPatch((x, 0.02), 0.21, 0.76, boxstyle="round,pad=0.01,rounding_size=0.02",
                                    facecolor="#eef4fc", edgecolor=BLUE, linewidth=1.2, transform=ax.transAxes))
        ax.text(x + 0.105, 0.68, head, ha="center", va="center", color=INK, fontsize=9.5,
                fontweight="bold", transform=ax.transAxes)
        ax.text(x + 0.105, 0.31, body, ha="center", va="center", color=INK2, fontsize=8.2,
                transform=ax.transAxes)
    ax.text(0.02, 0.95, "Expected harm is four terms over time; this organisation measures each its own way",
            transform=ax.transAxes, color=INK, fontsize=11)
    ax.text(0.02, 0.88, "The terms are reported apart and not multiplied", transform=ax.transAxes,
            color=INK2, fontsize=8.5)
    mf._save(fig, "fig5-harm-accounting")


def fig7():
    s = {k: v[0] for k, v in fd.SINGLE10.items()}
    fig, ax = _axes(7.2, 2.9)
    rows = [
        ("Missed by the document\nmonitor: one statement", s["missed_single"], ORANGE),
        ("Missed by the document\nmonitor: full plant", s["missed_full"], BLUE),
        ("Carried into an action:\none statement", s["carried_single"], ORANGE),
        ("Carried into an action:\nfull plant", s["carried_full"], BLUE),
    ]
    for i, (label, v, col) in enumerate(rows):
        y = len(rows) - 1 - i
        ax.barh(y, v, height=0.42, color=col, edgecolor=SURFACE, linewidth=2)
        ax.text(v + 0.015, y, f"{v:.3f}", va="center", color=INK, fontsize=9)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_xlim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("Share of the 48 quiet plants (missed) or of runs (carried, script count)")
    _titles(ax, "Cut to one statement, a plant is missed about twice as often and still carried",
            "Fresh scores against their own fresh honest baseline; the two forms ran side by side")
    mf._save(fig, "fig7-single-statement")


def main():
    prev = mf.OUT
    _point_out()
    try:
        _draw()
    finally:
        mf.OUT = prev  # so a later make_figures_v09.main() in the same process still writes to v09


def _draw():
    fig0()
    fig1()
    mf.fig3()
    mf.fig4()
    fig5()
    mf.fig6()
    fig7()


if __name__ == "__main__":
    main()
