"""IEEE-style single-line diagram of the Study 2 hybrid microgrid and its control structure.

Output: paper/proposal_figs/fig_microgrid_ieee.{png,pdf,svg}  (600 dpi PNG, vector PDF/SVG)
Run:    python paper/fig_microgrid_ieee.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyBboxPatch, Polygon, Rectangle, Arc

for f in font_manager.findSystemFonts():
    if "NimbusRoman" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Nimbus Roman", "mathtext.fontset": "stix", "font.size": 7.5,
                     "svg.fonttype": "none", "pdf.fonttype": 42})

K = "black"
BLUE = "#1f5fa8"      # learning / scheduling path
RED = "#b2322b"       # energy management and secondary control
GREY = "#f2f2f2"
LW = 0.9

fig, ax = plt.subplots(figsize=(7.16, 4.6))
ax.set_xlim(0, 100)
ax.set_ylim(-4.5, 60)
ax.set_aspect("equal")
ax.axis("off")


def line(xs, ys, c=K, lw=LW, ls="-", z=2):
    ax.plot(xs, ys, color=c, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")


def arrow(x0, y0, x1, y1, c=K, ls="-", lw=LW):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=4,
                arrowprops=dict(arrowstyle="-|>", color=c, lw=lw, ls=ls, mutation_scale=7, shrinkA=0, shrinkB=0))


def block(x, y, w, h, text, c=K, fill="white", fs=7, ls="-", bold=False):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="square,pad=0", lw=LW, ec=c,
                                fc=fill, ls=ls, zorder=3))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=5, color=K,
            fontweight="bold" if bold else "normal", linespacing=1.15)


def converter(x, y, top="=", bot="~", s=4.2):
    """Power-electronic converter: square with a diagonal, DC/AC marks."""
    ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, fc="white", ec=K, lw=LW, zorder=3))
    line([x - s / 2, x + s / 2], [y - s / 2, y + s / 2], z=4)
    ax.text(x - s / 4, y + s / 4, top, ha="center", va="center", fontsize=7, zorder=5)
    ax.text(x + s / 4, y - s / 4, bot, ha="center", va="center", fontsize=8, zorder=5)


def inductor(x, y_top, n=3, r=0.65):
    """Vertical inductor (series coupling reactance) drawn as semicircles, top to bottom."""
    for i in range(n):
        yc = y_top - r - 2 * r * i
        ax.add_patch(Arc((x, yc), 2 * r, 2 * r, theta1=-90, theta2=90, lw=LW, color=K, zorder=3))
    return y_top - 2 * r * n


def breaker(x, y, s=1.4):
    ax.add_patch(Rectangle((x - s / 2, y - s / 2), s, s, fc="white", ec=K, lw=LW, zorder=3))


def battery(x, y):
    for i, (w, dy) in enumerate([(3.4, 1.2), (1.8, 0.4), (3.4, -0.4), (1.8, -1.2)]):
        line([x - w / 2, x + w / 2], [y + dy, y + dy], lw=1.4 if w > 2 else 2.2, z=4)
    line([x, x], [y + 1.2, y + 2.6])
    line([x, x], [y - 1.2, y - 2.6])
    ax.text(x - 2.4, y + 1.5, "+", fontsize=6, ha="center", va="center")


def pv_array(x, y):
    ax.add_patch(Polygon([[x - 2.6, y - 1.6], [x + 1.8, y - 1.6], [x + 2.8, y + 1.6], [x - 1.6, y + 1.6]],
                         closed=True, fc="#dfe8f3", ec=K, lw=LW, zorder=3))
    for t in (1 / 3, 2 / 3):
        xa = (x - 2.6) + t * 4.4
        line([xa, xa + 1.0], [y - 1.6, y + 1.6], lw=0.5, z=4)
    line([x - 2.1, x + 2.3], [y, y], lw=0.5, z=4)


def wind_turbine(x, y):
    line([x, x], [y - 3.0, y + 1.6], lw=1.3)
    hub = (x, y + 1.6)
    for a in (90, 210, 330):
        r = np.deg2rad(a)
        tip = (hub[0] + 3.0 * np.cos(r), hub[1] + 3.0 * np.sin(r))
        ax.add_patch(Polygon([hub, (hub[0] + 1.2 * np.cos(r + 0.35), hub[1] + 1.2 * np.sin(r + 0.35)), tip],
                             closed=True, fc="white", ec=K, lw=0.7, zorder=4))
    ax.add_patch(Circle(hub, 0.45, fc=K, zorder=5))


def generator(x, y, r=2.1):
    ax.add_patch(Circle((x, y), r, fc="white", ec=K, lw=LW, zorder=3))
    ax.text(x, y + 0.45, "SG", ha="center", va="center", fontsize=6.5, zorder=5)
    t = np.linspace(-np.pi, np.pi, 50)
    ax.plot(x + 0.9 * t / np.pi, y - 0.8 + 0.35 * np.sin(t), color=K, lw=0.7, zorder=5)


# ---------------------------------------------------------------- AC bus
BUS_Y = 33
line([4, 96], [BUS_Y, BUS_Y], lw=3.2)
ax.text(96, BUS_Y + 1.6, "AC bus, 400 V, 50 Hz", ha="right", va="bottom", fontsize=7, style="italic")

# ---------------------------------------------------------------- source feeders
X_D, X_B, X_P, X_W = 11, 34, 57, 79
TOP = 54

# diesel: engine -> shaft -> SG -> X_d -> breaker -> bus
block(X_D, TOP + 1.2, 7.5, 3.6, "Diesel\nengine", fs=6.5, fill=GREY)
line([X_D - 0.25, X_D - 0.25], [TOP - 0.6, TOP - 3.0]); line([X_D + 0.25, X_D + 0.25], [TOP - 0.6, TOP - 3.0])
generator(X_D, TOP - 5.1)
line([X_D, X_D], [TOP - 7.2, 42.2]); y = inductor(X_D, 42.2); line([X_D, X_D], [y, 36.4])
breaker(X_D, 35.6); line([X_D, X_D], [34.9, BUS_Y])
ax.text(X_D + 1.6, 40.3, r"$X_d$", fontsize=7, va="center")
ax.text(X_D + 4.6, TOP - 5.1, "0.5 MW\n$H_d$ = 2 s", fontsize=6.8, va="center", linespacing=1.1)

# BESS: battery -> DC/AC (grid-forming) -> X_v -> breaker -> bus
battery(X_B, TOP + 1.0)
line([X_B, X_B], [TOP - 1.6, TOP - 2.7]); converter(X_B, TOP - 4.8)
line([X_B, X_B], [TOP - 6.9, 42.2]); y = inductor(X_B, 42.2); line([X_B, X_B], [y, 36.4])
breaker(X_B, 35.6); line([X_B, X_B], [34.9, BUS_Y])
ax.text(X_B + 1.6, 40.3, r"$X_v$", fontsize=7, va="center")
ax.text(X_B + 3.2, TOP + 1.0, "BESS\n0.5 MW / 2 MWh", fontsize=6.8, va="center", linespacing=1.1)
ax.text(X_B + 3.2, TOP - 4.8, "grid-forming\nVSG", fontsize=6.8, va="center", linespacing=1.1, color=BLUE)

# PV: array -> DC/AC (grid-following) -> breaker -> bus
pv_array(X_P, TOP + 1.0)
line([X_P, X_P], [TOP - 0.6, TOP - 2.7]); converter(X_P, TOP - 4.8)
line([X_P, X_P], [TOP - 6.9, 36.3]); breaker(X_P, 35.6); line([X_P, X_P], [34.9, BUS_Y])
ax.text(X_P + 3.6, TOP + 1.0, "PV 0.8 MW\n15 % de-loaded", fontsize=6.8, va="center", linespacing=1.1)
ax.text(X_P + 3.2, TOP - 4.8, "grid-\nfollowing", fontsize=6.8, va="center", linespacing=1.1)

# wind: turbine -> AC/DC/AC -> breaker -> bus
wind_turbine(X_W, TOP + 0.6)
line([X_W, X_W], [TOP - 2.4, TOP - 2.7]); converter(X_W, TOP - 4.8, top="~", bot="~")
line([X_W, X_W], [TOP - 6.9, 36.3]); breaker(X_W, 35.6); line([X_W, X_W], [34.9, BUS_Y])
ax.text(X_W + 3.6, TOP + 1.0, "Wind 1.0 MW\nIEC class III", fontsize=6.8, va="center", linespacing=1.1)
ax.text(X_W + 3.2, TOP - 4.8, "grid-\nfollowing", fontsize=6.8, va="center", linespacing=1.1)

# load below the bus
X_L = 91
line([X_L, X_L], [BUS_Y, 30.0]); breaker(X_L, 29.3); line([X_L, X_L], [28.6, 26.0])
arrow(X_L, 26.0, X_L, 22.6)
ax.text(X_L, 21.6, "Load\n0.3–0.8 MW\n(EGAT 2024)\nsteps\n0.2–0.4 MW", fontsize=6.6, ha="center", va="top", linespacing=1.1)

# ---------------------------------------------------------------- control layer
ax.add_patch(Rectangle((2.5, 0.8), 83.0, 30.0, fc="none", ec="#7f7f7f", lw=0.6, ls=(0, (4, 2)), zorder=1))
ax.text(84.8, 1.6, "Control layer", fontsize=6.8, style="italic", color="#555555", ha="right", va="bottom")
DASH = (0, (3, 1.5))

# measurement -> PLL -> scheduler -> projection (blue path)
XM = 46
ax.add_patch(Circle((XM, BUS_Y), 0.55, fc="white", ec=K, lw=LW, zorder=6))
line([XM, XM], [BUS_Y - 0.55, 29.3], ls=DASH, lw=0.8)
block(XM, 27.2, 18.0, 4.2, "PLL + 20 ms filter: $\\Delta f$, RoCoF", fs=6.6)
arrow(XM, 25.1, XM, 21.6, ls=DASH)
ax.text(XM + 0.7, 23.35, "$s_t$", fontsize=6.8, va="center")
block(XM, 19.5, 25.0, 4.2, "DRL agent (residual TD3 / DDPG)\nor fixed VSG, every 50 ms", fs=6.6, c=BLUE)
arrow(XM, 17.4, XM, 11.6, c=BLUE)
ax.text(XM + 0.7, 14.5, r"$(J_v, D_v, \alpha)_{\rm cmd}$", fontsize=6.6, color=BLUE, va="center")
block(XM, 9.5, 25.0, 4.2, "Direction-aware headroom projection\n(clipping or joint scaling)", fs=6.6, c=BLUE, fill="#e8eff8")
XB_ = 30.2
line([XM - 12.5, XB_, XB_], [9.5, 9.5, 45.6], c=BLUE)
arrow(XB_, 45.6, X_B - 2.1, 47.6, c=BLUE)
ax.text(XB_ + 0.6, 39.5, r"$J_v, D_v, \alpha$", fontsize=6.6, color=BLUE, va="center", rotation=90)

# headroom available to the VSG
block(73, 9.5, 19.0, 4.2, "Headroom $h_{up}$, $h_{dn}$\n(SoC limits, PV reserve)", fs=6.6)
arrow(73 - 9.5, 9.5, XM + 12.5, 9.5)

# EMS (red)
block(73, 19.5, 19.0, 4.2, "EMS (hourly): BESS\ndispatch, curtailment", fs=6.6, c=RED)
arrow(73, 17.4, 73, 11.6, c=RED, ls=DASH)
ax.text(73.7, 14.5, "$P_{b0}$", fontsize=6.8, color=RED, va="center")
line([73, 73], [21.6, 44.5], c=RED, ls=DASH)
line([X_P + 4.5, X_W - 4.5], [44.5, 44.5], c=RED, ls=DASH)
arrow(X_P + 4.5, 44.5, X_P + 2.1, 46.6, c=RED, ls=DASH)
arrow(X_W - 4.5, 44.5, X_W - 2.1, 46.6, c=RED, ls=DASH)
ax.text(72.3, 39.0, "curtailment", fontsize=6.2, color=RED, rotation=90, va="center", ha="right")

# secondary control (red): AGC to the diesel governor, set-point to the VSG
XS = 17
ax.add_patch(Circle((XS + 3, BUS_Y), 0.55, fc="white", ec=K, lw=LW, zorder=6))
line([XS + 3, XS + 3], [BUS_Y - 0.55, 21.6], ls=DASH, lw=0.8)
ax.text(XS + 3.6, 26.5, r"$\Delta f$", fontsize=6.8, va="center")
block(XS, 19.5, 18.0, 4.2, "Secondary control:\nAGC, BESS set-point", fs=6.6, c=RED)
line([XS - 9, 5.0, 5.0], [19.5, 19.5, 55.2], c=RED)
arrow(5.0, 55.2, X_D - 3.75, 55.2, c=RED)
ax.text(4.3, 44.0, r"$\Delta P_{ref}$ (governor)", fontsize=6.4, color=RED, rotation=90, va="center", ha="right")
XR = 27.4
line([XS + 9, XR, XR], [19.5, 19.5, 46.4], c=RED)
arrow(XR, 46.4, X_B - 2.1, 49.4, c=RED)
ax.text(XR - 0.6, 39.5, "$P_{set}$", fontsize=6.8, color=RED, rotation=90, va="center", ha="right")

# legend (below the drawing)
lx, ly = 1.0, -2.6
for i, (c, ls, t) in enumerate([(K, "-", "Power circuit"), (BLUE, "-", "VSG parameter scheduling"),
                                (RED, "-", "Secondary control"), (RED, DASH, "EMS (hourly)"),
                                (K, DASH, "Frequency measurement")]):
    x0 = lx + [0, 17.0, 42.0, 63.0, 79.0][i]
    line([x0, x0 + 3.5], [ly, ly], c=c, ls=ls)
    ax.text(x0 + 4.3, ly, t, fontsize=6.6, va="center")

out = Path(__file__).resolve().parent / "proposal_figs"
for ext in ("png", "pdf", "svg"):
    fig.savefig(out / f"fig_microgrid_ieee.{ext}", dpi=600, bbox_inches="tight", pad_inches=0.03)
print("wrote", out / "fig_microgrid_ieee.png")
