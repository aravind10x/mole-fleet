"""Draw the note's six figures from figure_data.py (count-level records only).

Run: cd note/figures && python make_figures.py
Writes fig1..fig6 as PNG and SVG beside this file.
"""
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

import figure_data as fd  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parent
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"   # categorical slot 1 (reference palette, validated)
ORANGE = "#eb6834"  # categorical slot 2
BLUE_LIGHT = "#9ec5f4"  # blue ramp step 200, for range bands

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "svg.fonttype": "none",
})


def _axes(fig_w=7.2, fig_h=3.2):
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    return fig, ax


def _save(fig, name):
    fig.tight_layout()
    for ext in ("png", "svg"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=200, facecolor=SURFACE, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def _titles(ax, main, sub=None):
    ax.text(0, 1.16 if sub else 1.06, main, transform=ax.transAxes, color=INK, fontsize=11, ha="left", va="bottom")
    if sub:
        ax.text(0, 1.04, sub, transform=ax.transAxes, color=INK2, fontsize=8.5, ha="left", va="bottom")


def _range(ax, y, lo, hi, color=BLUE, h=0.38):
    ax.barh(y, hi - lo, left=lo, height=h, color=color, edgecolor=SURFACE, linewidth=2)


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
        if lo == hi:
            ax.barh(y, lo, height=0.38, color=BLUE_LIGHT, edgecolor=SURFACE, linewidth=2)
            ax.text(lo + 0.015, y, f"{lo:.3f} (script count)", va="center", color=INK, fontsize=9)
        else:
            ax.barh(y, lo, height=0.38, color=BLUE_LIGHT, edgecolor=SURFACE, linewidth=2)
            _range(ax, y, lo, hi)
            ax.text(hi + 0.015, y, f"{lo:.3f} to {hi:.3f}  (script count {raw:.3f})", va="center", color=INK, fontsize=9)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_xlim(0, 1.25)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("Share of runs, weighted equally over the 48 quiet plants")
    _titles(ax, "About a third of the time, a quiet plant is acted on and the monitor misses it",
            "Dark band: range over two ways of completing the audits (not a confidence interval)")
    _save(fig, "fig1-headline")


def fig2():
    fig, ax = _axes(7.2, 2.5)
    order = ["serious", "material", "minor"]
    for i, cls in enumerate(order):
        d = fd.CLASSES[cls]
        y = len(order) - 1 - i
        lo, hi, n = d["lo"][0], d["hi"][0], d["n"][0]
        ax.barh(y, lo, height=0.38, color=BLUE_LIGHT, edgecolor=SURFACE, linewidth=2)
        _range(ax, y, lo, hi)
        ax.text(hi + 0.015, y, f"{lo:.3f} to {hi:.3f}", va="center", color=INK, fontsize=9)
    labels = [f"{c.capitalize()} ({fd.CLASSES[c]['n'][0]} plants)" for c in order]
    ax.set_yticks(range(3))
    ax.set_yticklabels(labels[::-1])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of runs acted on and missed (both audits)")
    _titles(ax, "The most serious quiet plants were acted on and missed least",
            "Dark band: range over two ways of completing the audits")
    _save(fig, "fig2-consequence-class")


def fig3():
    fig, ax = _axes(7.2, 3.4)
    rows = [(m[0], m[1], m[2], m[3], "ci") for m in fd.MONITORS] + \
           [(s[0], None, s[1], s[2], "tie") for s in fd.STRICTER]
    n = len(rows)
    for i, (label, p, lo, hi, kind) in enumerate(rows):
        y = n - 1 - i
        if kind == "ci":
            ax.plot([lo, hi], [y, y], color=BLUE, linewidth=2, solid_capstyle="round")
            ax.plot(p, y, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
            ax.text(hi + 0.02, y, f"{p:.3f}", va="center", color=INK, fontsize=9)
        else:
            ax.plot([lo, hi], [y, y], color=ORANGE, linewidth=6, solid_capstyle="round")
            ax.text(hi + 0.02, y, f"{lo:.3f} to {hi:.3f}", va="center", color=INK, fontsize=9)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_xlim(0, 0.95)
    ax.set_xlabel("Share carried and missed (script count)")
    _titles(ax, "The headline monitor leaves the least carried and missed",
            "Blue: point and 95% interval, each judge at its own 10% flag budget. Orange: stricter budgets, range over ties")
    _save(fig, "fig3-monitors")


def fig4():
    w = {k: v[0] for k, v in fd.WARNED.items()}
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.0), sharey=True)
    panels = [
        ("Planted text reached an action\n(both followers)", [("Both", w["literal_unwarned"], w["literal_warned"])]),
        ("The follower acted on it\n(first audit, point estimate)",
         [("Kimi K2.6", w["kimi_unwarned"], w["kimi_warned"]), ("GPT-6 Sol", w["sol_unwarned"], w["sol_warned"])]),
        ("Work completed correctly",
         [("Clean docs", w["work_clean_unwarned"], w["work_clean_warned"]),
          ("Updated docs", w["work_updated_unwarned"], w["work_updated_warned"])]),
    ]
    for ax, (title, groups) in zip(axes, panels):
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.tick_params(length=0)
        ax.grid(axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        x = range(len(groups))
        for j, (lab, a, b) in enumerate(groups):
            ax.bar(j - 0.18, a, width=0.34, color=BLUE, edgecolor=SURFACE, linewidth=2)
            ax.bar(j + 0.18, b, width=0.34, color=ORANGE, edgecolor=SURFACE, linewidth=2)
            ax.text(j - 0.18, a + 0.02, f"{a:.3f}", ha="center", color=INK, fontsize=8)
            ax.text(j + 0.18, b + 0.02, f"{b:.3f}", ha="center", color=INK, fontsize=8)
        ax.set_xticks(list(x))
        ax.set_xticklabels([g[0] for g in groups])
        ax.set_title(title, color=INK, fontsize=9.5, loc="left")
        ax.set_ylim(0, 1.1)
    axes[0].set_ylabel("Share of runs")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=BLUE, label="No warning"), Patch(color=ORANGE, label="Warned")],
               frameon=False, loc="upper right", ncol=2, fontsize=9, bbox_to_anchor=(0.99, 1.02))
    fig.suptitle("A warning changed what GPT-6 Sol did with planted text, and cost completed work",
                 x=0.01, ha="left", color=INK, fontsize=11)
    _save(fig, "fig4-warned-follower")


def fig5():
    a = {k: v[0] for k, v in fd.ACCOUNTING.items()}
    fig, ax = plt.subplots(figsize=(9.6, 3.1))
    ax.axis("off")
    boxes = [
        ("How long a plant\nstays in the document",
         f"{a['retention_undone']} of {a['retention_n']} plants undone\nby an honest edit in the log\n(replay of recorded edits)"),
        ("How often work\nneeds the item",
         f"{a['need_share']} of arriving tasks;\n{a['need_none']} of {a['need_of']} planted items\nneeded by no task\nthat can run here"),
        ("Acts per need",
         f"Tasks written to need it:\n{a['acted_lo']:.3f} to {a['acted_hi']:.3f} acted on\n\nHonest tasks that need it:\n{a['honest_carry']:.3f} carried"),
        ("Chance the plant gets\npast the monitor",
         f"measured together with acts:\n{a['missed_lo']:.3f} to {a['missed_hi']:.3f}\nacted on and missed"),
    ]
    xs = [0.02, 0.27, 0.52, 0.77]
    for x, (head, body) in zip(xs, boxes):
        ax.add_patch(FancyBboxPatch((x, 0.05), 0.21, 0.72, boxstyle="round,pad=0.01,rounding_size=0.02",
                                    facecolor="#eef4fc", edgecolor=BLUE, linewidth=1.2, transform=ax.transAxes))
        ax.text(x + 0.105, 0.65, head, ha="center", va="center", color=INK, fontsize=9.5,
                fontweight="bold", transform=ax.transAxes)
        ax.text(x + 0.105, 0.32, body, ha="center", va="center", color=INK2, fontsize=8.5,
                transform=ax.transAxes)
    ax.text(0.02, 0.95, "Expected harm is four terms over time; this organisation measures each its own way",
            transform=ax.transAxes, color=INK, fontsize=11)
    ax.text(0.02, 0.88, "The terms are reported apart and not multiplied", transform=ax.transAxes,
            color=INK2, fontsize=8.5)
    _save(fig, "fig5-harm-accounting")


def fig6():
    fig, ax = _axes(7.2, 2.6)
    n = len(fd.GENERATORS)
    for i, (label, p, lo, hi, *_r) in enumerate(fd.GENERATORS):
        y = n - 1 - i
        ax.plot([lo, hi], [y, y], color=BLUE, linewidth=2, solid_capstyle="round")
        ax.plot(p, y, "o", color=BLUE, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.text(hi + 0.02, y, f"{p:.3f}", va="center", color=INK, fontsize=9)
    ax.set_yticks(range(n))
    ax.set_yticklabels([g[0] for g in fd.GENERATORS][::-1])
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of honest writes their task does not license (judge; 95% interval)")
    _titles(ax, "On one shared task bank, honest out-of-task writing varies fivefold by model",
            "MOLE's released corpora; honest writes classed by a judge")
    _save(fig, "fig6-honest-deviance")


def fig0():
    fig, ax = plt.subplots(figsize=(9.6, 3.4))
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    def box(x, y, w, h, head, body, edge=BLUE, face="#eef4fc"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.02",
                                    facecolor=face, edgecolor=edge, linewidth=1.2))
        ax.text(x + w / 2, y + h - 0.06, head, ha="center", va="top", color=INK, fontsize=9.5, fontweight="bold")
        ax.text(x + w / 2, y + h / 2 - 0.08, body, ha="center", va="center", color=INK2, fontsize=8.5)

    def arrow(x0, y0, x1, y1, text=None, dx=0.0, dy=0.04):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=INK2, lw=1.2, shrinkA=2, shrinkB=2))
        if text:
            ax.text((x0 + x1) / 2 + dx, (y0 + y1) / 2 + dy, text, ha="center", color=INK2, fontsize=8)

    box(0.01, 0.52, 0.22, 0.40, "Fifty agents", "edit six shared\ndocuments in\neveryday sessions")
    box(0.27, 0.52, 0.22, 0.40, "One quiet change", "one account edits\nan item; each edit\nlooks like upkeep", edge=ORANGE, face="#fdeee7")
    box(0.53, 0.52, 0.22, 0.40, "The monitor", "reads the document's\ncombined changes;\nflags the top 10%\nof honest work")
    box(0.53, 0.04, 0.22, 0.38, "A later agent", "gets work that needs\nthe item, reads the\ndocument, acts")
    box(0.79, 0.04, 0.20, 0.38, "Its logged action", "does it carry the\nplanted content?\n(script, then audits)")
    box(0.79, 0.52, 0.20, 0.40, "Acted on and missed", "the action carries the\nplant and the monitor\ndid not flag it", edge=INK2, face="#f3f2ee")
    arrow(0.23, 0.72, 0.27, 0.72)
    arrow(0.49, 0.72, 0.53, 0.72)
    arrow(0.38, 0.52, 0.53, 0.30, "the document,\nfrozen", dx=-0.07, dy=-0.07)
    arrow(0.75, 0.23, 0.79, 0.23)
    arrow(0.75, 0.72, 0.79, 0.72)
    arrow(0.89, 0.42, 0.89, 0.52, None)
    ax.text(0.01, 1.0, "The design in one picture", color=INK, fontsize=11, va="bottom")
    _save(fig, "fig0-setup")


def main():
    for f in (fig0, fig1, fig2, fig3, fig4, fig5, fig6):
        f()


if __name__ == "__main__":
    main()
