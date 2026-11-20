"""Circuit schematic of the three-phase Simscape Electrical (Specialized Power Systems) model of Study 2.

Mirrors matlab/simscape/build_vsgrl_simscape.m block for block; the component values are computed with
the formulas of matlab/simscape/vsgrl_emt_params.m from configs/default.yaml and the constants in that file.
Output: paper/proposal_figs/fig_simscape_schematic.{png,pdf,svg}
Run:    python paper/fig_simscape_schematic.py
"""
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import yaml
from matplotlib import font_manager
from matplotlib.patches import Arc, Circle, Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[1]
cfg = yaml.safe_load(open(ROOT / "configs/default.yaml"))
src = (ROOT / "matlab/simscape/vsgrl_emt_params.m").read_text()


def mconst(name):
    """Numeric constant assigned in vsgrl_emt_params.m, e.g. 'PRM.V_LL = 400;'."""
    m = re.search(rf"PRM\.{re.escape(name)}\s*=\s*([0-9.eE+-]+)\s*;", src)
    return float(m.group(1))


f0 = cfg["system"]["f_nominal_hz"]
Sb = cfg["system"]["s_base_mva"] * 1e6
Kd, Ks = cfg["system"]["diesel"]["sync_coeff_pu"], cfg["system"]["vsg"]["sync_coeff_pu"]
V_LL, XR, P_sh, Ts = mconst("V_LL"), mconst("XR"), mconst("P_sh"), mconst("Ts")
f_pll = float(re.search(r"pll_ki\s*=\s*\(2\s*\*\s*pi\s*\*\s*([0-9.]+)\)", src).group(1))
w0 = 2 * math.pi * f0
Zb = V_LL ** 2 / Sb
X_v, X_d = 1 / Ks, 1 / Kd
R_v, L_v = X_v / XR * Zb, X_v * Zb / w0
R_d, L_d = X_d / XR * Zb, X_d * Zb / w0
R_sh = V_LL ** 2 / (P_sh * Sb)

for f in font_manager.findSystemFonts():
    if "NimbusRoman" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Nimbus Roman", "mathtext.fontset": "stix", "font.size": 7.5,
                     "svg.fonttype": "none", "pdf.fonttype": 42})
K, BLUE, RED, GREEN, GREY = "black", "#1f5fa8", "#b2322b", "#2e7d32", "#7f7f7f"
LW = 0.9
DASH = (0, (3, 1.5))

fig, ax = plt.subplots(figsize=(7.16, 4.1))
ax.set_xlim(0, 100)
ax.set_ylim(3, 59)
ax.set_aspect("equal")
ax.axis("off")


def line(xs, ys, c=K, lw=LW, ls="-", z=2):
    ax.plot(xs, ys, color=c, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")


def arrow(x0, y0, x1, y1, c=K, ls="-"):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=4,
                arrowprops=dict(arrowstyle="-|>", color=c, lw=LW, ls=ls, mutation_scale=7, shrinkA=0, shrinkB=0))


def block(x, y, w, h, text, c=K, fill="white", fs=6.6, pad=1.2):
    t = ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=5, linespacing=1.15)
    fig.canvas.draw()
    bb = t.get_window_extent().transformed(ax.transData.inverted())
    w, h = max(w, bb.width + 2 * pad), max(h, bb.height + 1.6)
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=fill, ec=c, lw=LW, zorder=3))
    return w, h


def three_phase_mark(x, y, c=K):
    for d in (-0.8, 0.0, 0.8):
        line([x + d - 0.45, x + d + 0.45], [y - 0.9, y + 0.9], c=c, lw=0.7, z=4)


def ground(x, y):
    line([x, x], [y, y - 1.2])
    for i, w in enumerate((1.6, 1.0, 0.4)):
        line([x - w, x + w], [y - 1.2 - 0.5 * i, y - 1.2 - 0.5 * i], lw=0.8)


def cvs(x, y, label, c):
    """Controlled voltage source (diamond with + and -), drawn vertically: top terminal at y+2.6."""
    ax.add_patch(Polygon([[x, y + 2.6], [x + 2.2, y], [x, y - 2.6], [x - 2.2, y]], fc="white", ec=c, lw=LW, zorder=3))
    ax.text(x, y + 1.0, "+", ha="center", va="center", fontsize=6.5, zorder=5)
    ax.text(x, y - 1.1, "−", ha="center", va="center", fontsize=6.5, zorder=5)
    ax.text(x - 3.0, y, label, ha="right", va="center", fontsize=6.6, color=c, linespacing=1.1)


def ccs(x, y, label, c):
    ax.add_patch(Polygon([[x, y + 2.6], [x + 2.2, y], [x, y - 2.6], [x - 2.2, y]], fc="white", ec=c, lw=LW, zorder=3))
    arrow(x, y - 1.4, x, y + 1.4, c=K)
    ax.text(x + 3.0, y, label, ha="left", va="center", fontsize=6.6, color=c, linespacing=1.1)


def resistor(x0, y, length=4.0):
    n, a = 6, 0.7
    xs = [x0] + [x0 + length * (i + 0.5) / n for i in range(n)] + [x0 + length]
    ys = [y] + [y + (a if i % 2 == 0 else -a) for i in range(n)] + [y]
    ax.plot(xs, ys, color=K, lw=LW, zorder=3)


def resistor_v(x, y0, length=4.0):
    n, a = 6, 0.7
    ys = [y0] + [y0 - length * (i + 0.5) / n for i in range(n)] + [y0 - length]
    xs = [x] + [x + (a if i % 2 == 0 else -a) for i in range(n)] + [x]
    ax.plot(xs, ys, color=K, lw=LW, zorder=3)


def inductor(x0, y, n=4, r=0.7):
    for i in range(n):
        ax.add_patch(Arc((x0 + r + 2 * r * i, y), 2 * r, 2 * r, theta1=0, theta2=180, lw=LW, color=K, zorder=3))
    return x0 + 2 * r * n


def vi_meas(x, y):
    ax.add_patch(Rectangle((x - 1.6, y - 1.6), 3.2, 3.2, fc="white", ec=K, lw=LW, zorder=3))
    ax.text(x, y, "V-I", ha="center", va="center", fontsize=5.6, zorder=5)


# ---------------------------------------------------------------- power circuit
BUS_X = 64
YV, YD = 47, 25            # VSG and diesel branches
line([BUS_X, BUS_X], [YD - 3, YV + 3], lw=3.0)
ax.text(BUS_X, YD - 3.8, f"Bus, {V_LL:g} V, {f0:g} Hz", ha="center", va="top", fontsize=6.8, style="italic")
XS = 13                    # source column


def branch(y, name, c, R, L, X, src_label, tag):
    cvs(XS, y - 4.5, "", c)
    ground(XS, y - 7.1)
    ax.text(XS, y - 9.6, src_label, ha="center", va="top", fontsize=6.4, color=c, linespacing=1.1)
    line([XS, XS], [y - 1.9, y])
    line([XS, 24], [y, y])
    three_phase_mark(19, y)
    resistor(24, y)
    x = inductor(28.4, y)
    line([x, 36.5], [y, y])
    ax.text(30.6, y + 2.0, f"$Z_{{{name}}}$: {R * 1e3:.0f} mΩ + {L * 1e6:.0f} µH\n($X$ = {X:g} pu, $X/R$ = {XR:g})",
            ha="center", va="bottom", fontsize=6.2, linespacing=1.1)
    vi_meas(38.1, y)
    ax.text(38.1, y - 2.2, tag, ha="center", va="top", fontsize=6.4)
    line([39.7, BUS_X], [y, y])
    three_phase_mark(52, y)


branch(YV, "v", BLUE, R_v, L_v, X_v, "VSG converter\n(average model):\n3 × controlled\nvoltage source", "$i_v$")
branch(YD, "d", RED, R_d, L_d, X_d, "Diesel SG EMF:\n3 × controlled\nvoltage source", "$i_d$")

# shunt resistance
YS = 34
line([BUS_X, 70], [YS, YS])
resistor_v(70, YS, 4.0)
ground(70, YS - 4.0)
ax.text(71.6, YS - 2.0, f"$R_{{sh}}$ = {R_sh:g} Ω\n({100 * P_sh:g} % load)", ha="left", va="center", fontsize=6.2,
        linespacing=1.1)

# load - wind - PV injection
YL = 47
XL = 88
line([BUS_X, 76.4], [YL, YL])
vi_meas(78, YL)
ax.text(78, YL - 2.2, "$v_B$, $i_L$", ha="center", va="top", fontsize=6.4)
line([79.6, XL], [YL, YL])
line([XL, XL], [YL, YL - 1.9])
ccs(XL, YL - 4.5, "", GREEN)
ground(XL, YL - 7.1)
ax.text(XL, YL - 9.6, "Load − wind − PV:\n3 × controlled\ncurrent source", ha="center", va="top", fontsize=6.4,
        color=GREEN, linespacing=1.1)

# ---------------------------------------------------------------- control (discrete, unit delay)
YC = 7.0
mw, _ = block(26, YC, 10, 4.2, "Mux + unit delay\n$z^{-1}$, %g µs" % (Ts * 1e6))
cw, _ = block(60, YC, 30, 4.2, "Controller (MATLAB Function, vsgrl_emt_ctrl.m):\n"
              f"SRF-PLL {f_pll:g} Hz, VSG swing equation, power limiter,\n"
              "headroom projection, TD3 actor / fixed VSG, diesel, EMS", c=BLUE, fill="#e8eff8")
arrow(26 + mw / 2, YC, 60 - cw / 2, YC)
arrow(26 - mw / 2 - 5.5, YC, 26 - mw / 2, YC, ls=DASH)
ax.text(26 - mw / 2 - 6.0, YC, "$v_B$, $i_L$, $i_v$, $i_d$", ha="right", va="center", fontsize=6.4)
# controller outputs to the sources
XO = 60 + cw / 2
line([XO, 97], [YC, YC], c=BLUE)
line([97, 97], [YC, 56], c=BLUE)
line([97, 3], [56, 56], c=BLUE)
line([3, 3], [56, YD - 4.5], c=BLUE)
arrow(3, YV - 4.5, XS - 2.2, YV - 4.5, c=BLUE)
arrow(3, YD - 4.5, XS - 2.2, YD - 4.5, c=BLUE)
arrow(97, YL - 4.5, XL + 2.2, YL - 4.5, c=BLUE)
ax.text(50, 56.6, "source references: VSG and diesel phase voltages, injected phase currents", fontsize=6.2,
        ha="center", va="bottom", color=BLUE)

# powergui
block(84, 21.0, 10, 4.2, "powergui\nDiscrete, %g µs" % (Ts * 1e6), fs=6.2, fill="#f2f2f2")

out = ROOT / "paper" / "proposal_figs"
for ext in ("png", "pdf", "svg"):
    fig.savefig(out / f"fig_simscape_schematic.{ext}", dpi=600, bbox_inches="tight", pad_inches=0.03)
print("wrote", out / "fig_simscape_schematic.png")
print(f"Z_v = {R_v * 1e3:.2f} mOhm + {L_v * 1e6:.1f} uH;  Z_d = {R_d * 1e3:.2f} mOhm + {L_d * 1e6:.1f} uH;  R_sh = {R_sh:.2f} Ohm")
