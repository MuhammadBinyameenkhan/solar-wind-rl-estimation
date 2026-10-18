"""
Figure 1 -- architecture of the headroom-feasible RL-VSG framework.

    python -m vsg_rl.fig1 [--out results_measured_final/figures]

(a) offline training: measured weather drives the simulated microgrid; the
    DDPG/TD3 agent observes 14 states, sets (J, D, Kq) through the slew and
    headroom limiters, and learns from the multi-objective reward.
(b) online deployment: only the trained actor and the two limiters run in
    the inverter controller.
Every number is taken from config.py, so the figure matches the code.
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                           # noqa: E402
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch  # noqa: E402

from . import config as C                                # noqa: E402

import re

INK = "#1F2430"
_GREEK = {"φ": r"\phi", "θ": r"\theta"}


def sub(t):
    """'h_req' -> h$_{req}$ (proper subscripts in matplotlib mathtext)."""
    def rep(m):
        body = "".join(_GREEK.get(c, c) for c in m.group(2))
        return f"{m.group(1)}$_{{{body}}}$"
    return re.sub(r"([A-Za-zΔμτσω])_([A-Za-z0-9φθ]+)", rep, t)
EDGE = "#5B6170"
FILL = {"plant": "#E8F1FB", "weather": "#EEF0F3", "limit": "#FDF0D9",
        "agent": "#E7F5EE", "reward": "#F7EAF3", "deploy": "#EAF0FA", "frame": "#FFFFFF"}


def box(ax, x, y, w, h, title, body="", kind="plant", fs=8.2, tfs=8.8):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.9",
                                fc=FILL[kind], ec=EDGE, lw=1.0))
    if body:
        ax.text(x + w / 2, y + h - 1.55, sub(title), ha="center", va="top", fontsize=tfs,
                fontweight="bold", color=INK)
        ax.text(x + w / 2, y + h - 1.55 - 2.4, sub(body), ha="center", va="top", fontsize=fs,
                color=INK, linespacing=1.32)
    else:
        ax.text(x + w / 2, y + h / 2, sub(title), ha="center", va="center", fontsize=tfs,
                fontweight="bold", color=INK)


def frame(ax, x, y, w, h, label):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.3,rounding_size=1.4",
                                fc="none", ec="#9AA0AC", lw=1.1, ls=(0, (4, 3))))
    ax.text(x + 1.2, y + h - 1.0, label, ha="left", va="top", fontsize=8.6,
            fontweight="bold", color="#4A4F5C")


def arrow(ax, p, q, label="", lpos=None, color=INK, ha="center", fs=7.9, style="-|>", rad=0.0):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=11, lw=1.2,
                                 color=color, connectionstyle=f"arc3,rad={rad}"))
    if label:
        lx, ly = lpos if lpos else ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        ax.text(lx, ly, sub(label), ha=ha, va="center", fontsize=fs, color=color,
                bbox=dict(fc="white", ec="none", pad=0.6))


def polyarrow(ax, pts, label="", lpos=None, color=INK, fs=7.9, ha="center"):
    xs, ys = zip(*pts)
    ax.plot(xs[:-1], ys[:-1], color=color, lw=1.2, solid_capstyle="butt")
    arrow(ax, pts[-2], pts[-1], color=color)
    if label:
        ax.text(*lpos, sub(label), ha=ha, va="center", fontsize=fs, color=color,
                bbox=dict(fc="white", ec="none", pad=0.6))


def draw(path_png):
    kw = lambda v: f"{v / 1e3:.0f}"
    fig = plt.figure(figsize=(16, 9.6))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 160)
    ax.set_ylim(0, 96)
    ax.axis("off")

    # ------------------------------------------------------------ (a) training
    ax.text(2, 95, "(a) Offline training", fontsize=11.5, fontweight="bold", color=INK, va="top")
    frame(ax, 1.5, 3.5, 57.5, 88, f"MICROGRID PLANT  (decision step {C.CONTROL_DT * 1e3:.0f} ms, "
                                  f"physics {C.CONTROL_DT / C.PHYS_SUBSTEPS * 1e3:.0f} ms)")
    frame(ax, 74, 3.5, 34.5, 88, "DDPG / TD3 AGENT")

    box(ax, 4, 78, 52, 9.5, "Measured weather (recorded levels)",
        "BSRN Cabauw 1-Hz GHI  ·  FINO1 80 m sonic wind (1 s)\n"
        "chronological train / validation / test split", kind="weather")
    box(ax, 4, 65, 25, 9.5, f"Solar PV  {kw(C.PV_RATED)} kW", "P_pv = f(G, T_cell)")
    box(ax, 31, 65, 25, 9.5, f"Type-4 wind turbine  {kw(C.WT_RATED)} kW",
        "rotor dynamics, MPPT, pitch")
    arrow(ax, (17, 78), (17, 74.6))
    arrow(ax, (43, 78), (43, 74.6))
    box(ax, 4, 51, 25, 10.5, f"Load  {kw(C.P_LOAD_NOM)} kW",
        "+ two load contingencies\n(randomised in training)")
    box(ax, 31, 49, 25, 12.5, f"Grid-forming BESS  {C.S_BASE / 1e3:.0f} kVA",
        f"{C.E_BESS_WH / 1e3:.0f} kWh;  schedule (τ_sch = {C.TAU_AGC:.0f} s)\n"
        f"+ {100 / C.K_DROOP:.0f} % droop + VSG:\n"
        "p_vsg = −2J_eff dΔω/dt − D_eff Δω_m")
    box(ax, 4, 34, 52, 11, "Converter headroom limiter (Eqs. 20–25)",
        "h_req = 0.08 J + 0.01 D   vs   h_avail = (S − |P_sched|) / S\n"
        "if h_req > h_avail:  (J_eff, D_eff) = (J, D) · h_avail / h_req", kind="limit")
    arrow(ax, (43.5, 45.2), (43.5, 48.8), "J_eff, D_eff", (50.2, 47.0), fs=7.6)
    box(ax, 4, 19, 25, 11.5, "Swing equation",
        f"H_sys = {C.H_SYS} s,  f₀ = {C.F_NOM:.0f} Hz\nΔP = P_pv + P_w + P_bess − P_load")
    box(ax, 31, 19, 25, 11.5, "Voltage channel",
        f"Q–V droop K_q,  X_th = {C.X_TH} pu\nPCC voltage V")
    arrow(ax, (16.5, 33.8), (16.5, 30.7))
    box(ax, 4, 6, 52, 9.5, "PLL / measurement",
        f"τ = {C.PLL_TAU * 1e3:.0f} ms,  σ = {C.PLL_NOISE_HZ * 1e3:.0f} mHz   →   Δf_m, RoCoF_m, "
        "V, P, SOC, h_avail")
    arrow(ax, (16.5, 18.8), (16.5, 15.7))

    # agent column
    box(ax, 77, 76, 14.2, 12.5, "DDPG", "one critic Q_φ(s, a)\n17→256→256→1\n+ target critic",
        kind="agent", fs=7.6, tfs=8.6)
    box(ax, 92.6, 76, 14.2, 12.5, "TD3", "twin critics Q_φ1, Q_φ2\ny = r + γ min(Q′₁, Q′₂)\n"
        f"smoothing σ {C.POLICY_NOISE}, clip {C.NOISE_CLIP}\nactor every {C.POLICY_FREQ} updates",
        kind="agent", fs=7.2, tfs=8.6)
    box(ax, 77, 64, 29.8, 9, "Prioritised replay buffer",
        f"SumTree, {C.PER_CAPACITY:.0e} (s, a, r, s′), α {C.PER_ALPHA}, β {C.PER_BETA_START}→{C.PER_BETA_END}"
        .replace("2e+05", "2×10⁵"), kind="agent", fs=7.5)
    arrow(ax, (91.9, 73.2), (91.9, 75.8), "minibatch", (99.0, 74.6), fs=7.2)
    box(ax, 77, 47.5, 29.8, 13.5, "Multi-objective reward r_t",
        "frequency, RoCoF (500 ms) + 2 Hz/s hinge,\nvoltage, effort, SOC, BESS power,\n"
        "reserve 0.5·h_req, infeasibility, in-band, trip\n"
        f"learner reward {C.REWARD_SCALE:g}·(r − 1)".replace("0.001", "10⁻³"),
        kind="reward", fs=7.4)
    arrow(ax, (91.9, 61.2), (91.9, 63.8))
    box(ax, 77, 31, 29.8, 13, "Actor μ_θ(s)",
        f"{C.STATE_DIM}→{C.HIDDEN}→{C.HIDDEN}→{C.ACTION_DIM}, LayerNorm + ReLU, tanh\n"
        f"Polyak targets τ = {C.TAU_SOFT}\n+ exploration noise 0.30 → 0.03", kind="agent", fs=7.5)
    polyarrow(ax, [(107.2, 82), (108.2, 82), (108.2, 37.5), (107.0, 37.5)],
              "∇ₐQ", (108.2, 60), fs=7.6)
    box(ax, 77, 6, 29.8, 20.5, f"State s_t  ({C.STATE_DIM} inputs)",
        "Δf_m, RoCoF_m, t/T,\nP_pv, P_w, v_w, G, SOC,\nΔV, P_bess,\nJ, D, K_q (values in force),\n"
        "h_avail", kind="agent", fs=7.5)
    arrow(ax, (91.9, 26.7), (91.9, 30.8))

    # interface arrows plant <-> agent
    arrow(ax, (76.8, 37.5), (56.3, 39.5),
          f"action a_t = [J, D, K_q]\nslew limit (full range {C.SLEW_TIME} s)", (66.4, 42.7), fs=7.6)
    arrow(ax, (56.3, 10.5), (76.8, 13.5), "state s_t", (66.4, 13.6), fs=7.6)
    arrow(ax, (56.3, 55.0), (76.8, 54.0), "Δf, RoCoF, V,\nh_req, h_avail, trip", (66.4, 57.4), fs=7.3)

    # ------------------------------------------------------------ (b) deployment
    ax.text(114, 95, "(b) Online deployment", fontsize=11.5, fontweight="bold", color=INK, va="top")
    frame(ax, 113, 3.5, 45.5, 88, "INVERTER CONTROLLER  (every 20 ms)")
    bx, bw = 117, 37.5
    box(ax, bx, 74, bw, 10, "Measurements", "PLL frequency and RoCoF, V, P, SOC, h_avail\n→ state s_t (14)",
        kind="deploy", fs=7.6)
    box(ax, bx, 58, bw, 10.5, "Trained actor μ_θ (frozen)",
        "best validated checkpoint\n0.083 ms per 20 ms decision (one CPU core)", kind="agent", fs=7.6)
    box(ax, bx, 45, bw, 8, "Slew-rate limiter", f"J, D, K_q: full range in {C.SLEW_TIME} s",
        kind="deploy", fs=7.6)
    box(ax, bx, 31, bw, 9.5, "Headroom limiter (Eq. 24)",
        "derate (J, D) to the available headroom", kind="limit", fs=7.6)
    box(ax, bx, 15, bw, 11, "BESS inverter control",
        "VSG (J_eff, D_eff) + droop + Q–V droop K_q\n→ microgrid", kind="deploy", fs=7.6)
    for y0, y1 in ((73.8, 68.7), (57.8, 53.2), (44.8, 40.7), (30.8, 26.2)):
        arrow(ax, (bx + bw / 2, y0), (bx + bw / 2, y1))
    polyarrow(ax, [(bx + bw + 0.2, 20.5), (bx + bw + 2.2, 20.5), (bx + bw + 2.2, 79), (bx + bw + 0.2, 79)],
              "plant\nresponse", (bx + bw + 2.2, 48), fs=7.2)
    ax.text(bx + bw / 2, 8.5, "Critics, replay buffer and reward are used only\nduring offline training.",
            ha="center", va="center", fontsize=7.8, style="italic", color="#4A4F5C")

    os.makedirs(os.path.dirname(path_png) or ".", exist_ok=True)
    fig.savefig(path_png, dpi=300, facecolor="white")
    fig.savefig(os.path.splitext(path_png)[0] + ".pdf", facecolor="white")
    fig.savefig(os.path.splitext(path_png)[0] + ".svg", facecolor="white")
    plt.close(fig)
    return path_png


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("results_measured_final", "figures"))
    args = ap.parse_args(argv)
    print(draw(os.path.join(args.out, "figure1_architecture.png")))


if __name__ == "__main__":
    main()
