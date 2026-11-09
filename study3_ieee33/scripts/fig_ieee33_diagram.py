"""Single-line diagram of the islanded IEEE 33-bus feeder of Study 3 with the plant placement.

Connectivity is read from data/ieee33_lines.csv (Baran & Wu 1989, MATPOWER case33bw) and the plant
ratings from configs/ieee33.yaml, so the figure follows the data and the configuration.
Output: study3_ieee33/results/figures/fig_ieee33_diagram.{png,pdf,svg}
Run:    python study3_ieee33/scripts/fig_ieee33_diagram.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib import font_manager
from matplotlib.patches import Arc, Circle, FancyArrowPatch, Polygon, Rectangle

S3 = Path(__file__).resolve().parents[1]
lines = pd.read_csv(S3 / "data/ieee33_lines.csv")
buses = pd.read_csv(S3 / "data/ieee33_buses.csv")
cfg = yaml.safe_load(open(S3 / "configs/ieee33.yaml"))
sy, nw = cfg["system"], cfg["system"]["network"]

for f in font_manager.findSystemFonts():
    if "NimbusRoman" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Nimbus Roman", "mathtext.fontset": "stix", "font.size": 7.5,
                     "svg.fonttype": "none", "pdf.fonttype": 42})
K, BLUE, GREEN, RED, GREY = "black", "#1f5fa8", "#2e7d32", "#b2322b", "#8c8c8c"
LW = 0.9

# ---------------------------------------------------------------- bus positions (conventional layout)
P = {}
for b in range(1, 19):                 # main feeder 1-18
    P[b] = (b - 1.0, 0.0)
for i, b in enumerate(range(19, 23)):  # lateral from bus 2
    P[b] = (1.0 + i, -1.7)
for i, b in enumerate(range(23, 26)):  # lateral from bus 3
    P[b] = (2.0 + i, 1.7)
for i, b in enumerate(range(26, 34)):  # lateral from bus 6
    P[b] = (5.0 + i, -3.4)

fig, ax = plt.subplots(figsize=(7.16, 3.55))
ax.set_xlim(-3.2, 18.6)
ax.set_ylim(-6.6, 4.4)
ax.set_aspect("equal")
ax.axis("off")


def seg(a, b, **kw):
    ax.plot([a[0], b[0]], [a[1], b[1]], **kw)


# ---------------------------------------------------------------- lines (in service) and tie lines (open)
for _, r in lines.iterrows():
    a, b = P[int(r["from"])], P[int(r["to"])]
    if r.in_service:
        if a[1] != b[1] and a[0] != b[0]:             # branch start: go down/up first, then along
            seg(a, (a[0], b[1]), color=K, lw=LW, zorder=2)
            seg((a[0], b[1]), b, color=K, lw=LW, zorder=2)
        else:
            seg(a, b, color=K, lw=LW, zorder=2)
    else:
        rad = 0.35 if a[1] == b[1] else -0.25
        ax.add_patch(FancyArrowPatch(a, b, connectionstyle=f"arc3,rad={rad}", arrowstyle="-", lw=0.7,
                                     ls=(0, (3, 2)), color=GREY, zorder=1))

# ---------------------------------------------------------------- buses, numbers and loads
for b, (x, y) in P.items():
    seg((x - 0.22, y), (x + 0.22, y), color=K, lw=2.4, zorder=3)
    above = b in range(23, 26)
    if b == nw["bus_res"]:                             # number beside the bar, clear of the PV / wind connection
        ax.text(x + 0.12, y - 0.30, str(b), ha="left", va="top", fontsize=6.4, zorder=4)
    else:
        ax.text(x, y + (0.28 if above else -0.30), str(b), ha="center", va="bottom" if above else "top",
                fontsize=6.4, zorder=4)
    p = float(buses.loc[buses.bus == b, "p_kw"].iloc[0])
    if p > 0:                                          # published load at this bus
        d = 1                                          # all load arrows point up, clear of the bus numbers
        ax.annotate("", xy=(x + 0.12, y + d * 0.62), xytext=(x + 0.12, y + d * 0.06), zorder=3,
                    arrowprops=dict(arrowstyle="-|>", lw=0.5, color=GREY, mutation_scale=4, shrinkA=0, shrinkB=0))


# ---------------------------------------------------------------- plant symbols
def gen_symbol(x, y, label, c):
    ax.add_patch(Circle((x, y), 0.42, fc="white", ec=c, lw=LW, zorder=5))
    t = np.linspace(-np.pi, np.pi, 40)
    ax.plot(x + 0.22 * t / np.pi, y + 0.08 * np.sin(t) - 0.08, color=c, lw=0.7, zorder=6)
    ax.text(x, y + 0.12, label, ha="center", va="center", fontsize=5.6, color=c, zorder=6)


def conv_symbol(x, y, c, top="=", bot="~"):
    s = 0.8
    ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, fc="white", ec=c, lw=LW, zorder=5))
    seg((x - s / 2, y - s / 2), (x + s / 2, y + s / 2), color=c, lw=0.7, zorder=6)
    ax.text(x - s / 4, y + s / 4, top, ha="center", va="center", fontsize=5.5, color=c, zorder=6)
    ax.text(x + s / 4, y - s / 4, bot, ha="center", va="center", fontsize=6, color=c, zorder=6)


def battery(x, y, c):
    for w, dy, lw in [(0.6, 0.18, 1.2), (0.32, 0.06, 2.0), (0.6, -0.06, 1.2), (0.32, -0.18, 2.0)]:
        seg((x - w / 2, y + dy), (x + w / 2, y + dy), color=c, lw=lw, zorder=6)


def pv(x, y, c):
    ax.add_patch(Polygon([[x - 0.42, y - 0.25], [x + 0.3, y - 0.25], [x + 0.45, y + 0.25], [x - 0.27, y + 0.25]],
                         fc="#dfe8f3", ec=c, lw=0.7, zorder=6))


def turbine(x, y, c):
    """Three-bladed rotor on its hub (hub at the end of the connecting line)."""
    hub = (x, y + 0.15)
    for a in (90, 210, 330):
        r = np.deg2rad(a)
        seg(hub, (hub[0] + 0.36 * np.cos(r), hub[1] + 0.36 * np.sin(r)), color=c, lw=1.0, zorder=6)
    ax.add_patch(Circle(hub, 0.07, fc=c, ec=c, zorder=7))


mw = lambda v: f"{v:.2f}".rstrip("0").rstrip(".")      # noqa: E731
# diesel SG at the head of the feeder (replaces the substation of the published grid-connected case)
xb, yb = P[nw["bus_diesel"]]
seg((xb - 0.22, yb), (xb - 1.2, yb), color=RED, lw=LW, zorder=2)
gen_symbol(xb - 1.65, yb, "SG", RED)
ax.text(xb - 1.65, yb + 0.62, f"Diesel SG\n{mw(sy['diesel']['rated_mw'])} MW\n(slack)", ha="center", va="bottom",
        fontsize=6.4, color=RED, linespacing=1.05)

# BESS + grid-forming VSG
xb, yb = P[nw["bus_vsg"]]
xb -= 0.1                                              # keep clear of the load arrow at this bus
seg((xb, yb + 0.06), (xb, yb + 1.05), color=BLUE, lw=LW, zorder=2)
conv_symbol(xb, yb + 1.45, BLUE)
seg((xb, yb + 1.85), (xb, yb + 2.15), color=BLUE, lw=LW, zorder=2)
battery(xb, yb + 2.35, BLUE)
ax.text(xb - 0.55, yb + 1.9, f"BESS\n{mw(sy['bess']['power_mw'])} MW /\n{mw(sy['bess']['energy_mwh'])} MWh\ngrid-forming VSG",
        ha="right", va="center", fontsize=6.4, color=BLUE, linespacing=1.05)

# PV + wind (grid-following)
xb, yb = P[nw["bus_res"]]
for dx, kind in ((-0.55, "pv"), (0.55, "wind")):
    x = xb + dx
    seg((xb, yb - 0.06), (xb, yb - 0.75), color=GREEN, lw=LW, zorder=2)
    seg((xb, yb - 0.75), (x, yb - 0.75), color=GREEN, lw=LW, zorder=2)
    seg((x, yb - 0.75), (x, yb - 1.05), color=GREEN, lw=LW, zorder=2)
    conv_symbol(x, yb - 1.45, GREEN, top="=" if kind == "pv" else "~")
    seg((x, yb - 1.85), (x, yb - 2.05), color=GREEN, lw=LW, zorder=2)
    (pv if kind == "pv" else turbine)(x, yb - 2.4, GREEN)
ax.text(xb + 1.25, yb - 1.75, f"PV {mw(sy['pv']['rated_mw'])} MW (de-loaded)\nWind {mw(sy['wind']['rated_mw'])} MW\ngrid-following",
        ha="left", va="center", fontsize=6.4, color=GREEN, linespacing=1.05)

# ---------------------------------------------------------------- notes and legend
tot_p, tot_q = buses.p_kw.sum() / 1e3, buses.q_kvar.sum() / 1e3
ax.text(-3.1, -4.75, f"Islanded IEEE 33-bus feeder, {nw.get('v_base_kv', 12.66)} kV [Baran & Wu 1989]\n"
        f"Peak load {tot_p:.3f} MW + j{tot_q:.2f} Mvar (published), scaled hourly\n"
        f"by the measured EGAT 2024 Northeast demand", ha="left", va="top", fontsize=6.4, linespacing=1.1)
lx0, ly = 4.2, 3.95
items = [(K, "-", "Line in service"), (GREY, (0, (3, 2)), "Tie line (open)"), (GREY, "arrow", "Load (published P, Q)")]
for i, (c, ls, t) in enumerate(items):
    y, lx = ly, lx0 + [0, 3.6, 7.2][i]
    if ls == "arrow":
        ax.annotate("", xy=(lx + 0.35, y + 0.25), xytext=(lx + 0.35, y - 0.25),
                    arrowprops=dict(arrowstyle="-|>", lw=0.5, color=c, mutation_scale=4, shrinkA=0, shrinkB=0))
    else:
        seg((lx, y), (lx + 0.7, y), color=c, lw=0.8, ls=ls)
    ax.text(lx + 0.95, y, t, va="center", fontsize=6.4)

out = S3 / "results" / "figures"
out.mkdir(parents=True, exist_ok=True)
for ext in ("png", "pdf", "svg"):
    fig.savefig(out / f"fig_ieee33_diagram.{ext}", dpi=600, bbox_inches="tight", pad_inches=0.03)
print("wrote", out / "fig_ieee33_diagram.png")
