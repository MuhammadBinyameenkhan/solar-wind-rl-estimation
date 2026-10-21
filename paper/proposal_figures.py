"""Figures for the thesis proposal (and Fig. 1 of the IREA manuscript).

  fig_prisma.png          PRISMA 2020 flow diagram (database counts left blank to be filled from the search log)
  fig_concept.png         conceptual framework of the thesis
  fig_single_line.png     single-line diagram of the hybrid diesel-PV-wind-BESS microgrid

Run: python paper/proposal_figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

OUT = Path(__file__).resolve().parent / "proposal_figs"
OUT.mkdir(exist_ok=True)
INK, MUTED, EDGE, FILL, ACC = "#0b0b0b", "#52514e", "#6f6e69", "#f3f2ef", "#2a78d6"
plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 9})


def box(ax, x, y, w, h, text, fill=FILL, edge=EDGE, bold=False, fs=8.5, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.015", fc=fill, ec=edge,
                                lw=1.0, ls=ls))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=INK,
            fontweight="bold" if bold else "normal", wrap=True, linespacing=1.35)


def arrow(ax, x0, y0, x1, y1, color=EDGE):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=10, color=color, lw=1.0))


def prisma():
    fig, ax = plt.subplots(figsize=(7.2, 8.4))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    stages = [("Identification", 0.80, 0.97), ("Screening", 0.28, 0.79), ("Included", 0.03, 0.26)]
    for name, y0, y1 in stages:
        ax.add_patch(FancyBboxPatch((0.0, y0), 0.06, y1 - y0, boxstyle="round,pad=0,rounding_size=0.01",
                                    fc="#dbe7f7", ec=ACC, lw=0.8))
        ax.text(0.03, (y0 + y1) / 2, name, rotation=90, ha="center", va="center", fontsize=9, fontweight="bold",
                color=INK)
    L, R, W = 0.10, 0.60, 0.40
    box(ax, L, 0.82, W, 0.14, "Records identified from databases:\nScopus (n = ____)\nIEEE Xplore (n = ____)\n"
        "ScienceDirect (n = ____)\nWeb of Science (n = ____)")
    box(ax, R, 0.84, W - 0.02, 0.10, "Removed before screening:\nduplicates (n = ____)\n"
        "year / language filter (n = ____)", fs=7.8)
    box(ax, L, 0.67, W, 0.08, "Records screened on\ntitle and abstract (n = ____)")
    box(ax, R, 0.66, W - 0.02, 0.10, "Records excluded (n = ____):\nno inertia/damping adaptation\nor no frequency dynamics", fs=7.8)
    box(ax, L, 0.53, W, 0.08, "Reports sought for retrieval\n(n = ____)")
    box(ax, R, 0.53, W - 0.02, 0.08, "Reports not retrieved\n(n = ____)")
    box(ax, L, 0.33, W, 0.14, "Reports assessed for eligibility\n(full text)\n(n = ____)")
    box(ax, R, 0.31, W - 0.02, 0.18, "Reports excluded (n = ____):\nE1 parameters not adapted\n(fixed VSG only)\n"
        "E2 no quantitative\nfrequency results\nE3 not peer reviewed\nE4 duplicate of same model", fs=7.8)
    box(ax, L, 0.07, W, 0.14, "Studies included in the review\n(n = 17; Tables 2.1–2.2)\n"
        "incl. records from citation\nsearching (n = ____)", fill="#e8f1e4", edge="#008300", bold=False)
    box(ax, R, 0.09, W - 0.02, 0.10, "Records from citation searching\nof included studies (n = ____)", ls="--")
    for y0, y1 in [(0.82, 0.75), (0.67, 0.61), (0.53, 0.47), (0.33, 0.21)]:
        arrow(ax, L + W / 2, y0, L + W / 2, y1)
    for y in [0.89, 0.71, 0.57, 0.40]:
        arrow(ax, L + W, y, R, y)
    arrow(ax, R, 0.14, L + W, 0.14)
    ax.text(0.5, 0.005, "PRISMA 2020 flow diagram (Page et al., 2021). Counts marked ____ are filled from the logged searches "
            "(Table 2.1 search strings).", ha="center", fontsize=7, color=MUTED, style="italic")
    fig.savefig(OUT / "fig_prisma.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def concept():
    fig, ax = plt.subplots(figsize=(7.4, 5.0))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    cols = [(0.01, "INPUTS"), (0.27, "MODELS"), (0.53, "CONTROL LAYER"), (0.79, "EVALUATION")]
    for x, t in cols:
        ax.text(x + 0.095, 0.97, t, ha="center", fontsize=8.5, fontweight="bold", color=ACC)
    box(ax, 0.01, 0.72, 0.19, 0.20, "Weather data\n1-Hz records (Study 1)\nERA5 + NASA POWER\nThai site, 2024\n(Study 2)", fs=6.6)
    box(ax, 0.01, 0.45, 0.19, 0.20, "Load and events\nrandomised load\ncontingencies\n(two or three per\n30 s episode)", fs=6.6)
    box(ax, 0.01, 0.18, 0.19, 0.20, "Grid-code limits\nRoCoF, frequency\nband, converter\nrating, SoC window", fs=6.6)
    box(ax, 0.27, 0.62, 0.19, 0.30, "Study 1\nconverter-only\nmicrogrid\nPV + wind\n+ BESS-VSG", fs=6.6)
    box(ax, 0.27, 0.18, 0.19, 0.38, "Study 2\nhybrid microgrid\ndiesel SG\n+ BESS-VSG\n+ de-loaded PV\n+ wind, EMS,\nsecondary control", fs=6.6)
    box(ax, 0.53, 0.70, 0.19, 0.22, "DRL agent\nDDPG / TD3\nschedules J, D\n(+ Kq or α)\nevery 20–50 ms", fs=6.6,
        fill="#dbe7f7", edge=ACC)
    box(ax, 0.53, 0.42, 0.19, 0.22, "Headroom\nfeasibility layer\nsum or max rule;\nclip or joint\nscaling", fs=6.6,
        fill="#dbe7f7", edge=ACC)
    box(ax, 0.53, 0.18, 0.19, 0.18, "Rate limiter\nthen feasibility\n(feasibility before\nsmoothness)", fs=6.6,
        fill="#dbe7f7", edge=ACC)
    box(ax, 0.79, 0.70, 0.20, 0.22, "Fair benchmarking\ntuned constant\nand rule-based VSG,\nmulti-seed statistics", fs=6.6)
    box(ax, 0.79, 0.42, 0.20, 0.22, "Oracle bound\nmaximum gain\nof any scheduler,\nbefore training", fs=6.6)
    box(ax, 0.79, 0.18, 0.20, 0.18, "Validation\nMATLAB\nre-implementation;\nthree-phase EMT", fs=6.6)
    for y in [0.82, 0.55, 0.28]:
        arrow(ax, 0.20, y, 0.27, y if y != 0.82 else 0.77)
    arrow(ax, 0.46, 0.77, 0.53, 0.81)
    arrow(ax, 0.46, 0.37, 0.53, 0.53)
    arrow(ax, 0.625, 0.70, 0.625, 0.64)
    arrow(ax, 0.625, 0.42, 0.625, 0.36)
    for y in [0.81, 0.53, 0.27]:
        arrow(ax, 0.72, y, 0.79, y)
    ax.text(0.5, 0.06, "Thesis outcome: feasible synthetic inertia — VSG schedules that the converter can deliver, "
            "evaluated fairly and validated beyond the averaged model", ha="center", fontsize=8, style="italic", color=INK)
    fig.savefig(OUT / "fig_concept.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def single_line():
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.plot([0.04, 0.88], [0.52, 0.52], color=INK, lw=4)
    ax.text(0.89, 0.52, "AC bus\n400 V\n50 Hz", va="center", fontsize=7.5)
    units = [(0.13, "Diesel SG 0.5 MW\nH = 2 s\ndroop + AGC", "#efe5d6"),
             (0.35, "BESS 0.5 MW/2 MWh\ngrid-forming VSG\n(J, D, α)", "#dbe7f7"),
             (0.57, "PV 0.8 MW\nde-loaded MPPT\n(15 % reserve)", "#f6efd6"),
             (0.79, "Wind 1.0 MW\nIEC class III\ngrid-following", "#e3f0ea")]
    for x, t, c in units:
        box(ax, x - 0.10, 0.70, 0.20, 0.20, t, fill=c, fs=7)
        ax.plot([x, x], [0.70, 0.52], color=INK, lw=1.2)
    box(ax, 0.62, 0.16, 0.24, 0.18, "Load 0.3–0.8 MW\nsteps 0.2–0.4 MW", fs=7)
    ax.plot([0.74, 0.74], [0.52, 0.34], color=INK, lw=1.2)
    box(ax, 0.02, 0.10, 0.26, 0.20, "EMS (hourly)\nBESS dispatch,\ncurtailment,\ndiesel at 60 %", fs=7, ls="--")
    box(ax, 0.31, 0.10, 0.27, 0.20, "Scheduler (50 ms)\nDRL agent or fixed VSG\n+ headroom projection", fs=7,
        fill="#dbe7f7", edge=ACC, ls="--")
    arrow(ax, 0.40, 0.30, 0.38, 0.70, color=ACC)
    arrow(ax, 0.15, 0.30, 0.30, 0.70, color=EDGE)
    fig.savefig(OUT / "fig_single_line.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    prisma(); concept(); single_line()
    print("wrote", *sorted(p.name for p in OUT.glob("*.png")))
