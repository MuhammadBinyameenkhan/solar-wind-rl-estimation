"""Figure for the paper: MATLAB vs Python cross-validation (run after matlab/run_matlab_validation.m).

Reads matlab/results/validation_traces_sc1.csv and validation_metrics.csv and writes
results/figures/fig_matlab_validation.{pdf,png}.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from _common import ROOT, base_parser, setup  # noqa: E402
from plot import MUTED, PALETTE, save, style  # noqa: E402

LAB = {"fixed_tuned": "Fixed VSG (tuned)", "fixed_feasible": "Fixed VSG + projection", "policy": "TD3 policy"}
COL = {"fixed_tuned": PALETTE[5], "fixed_feasible": "#6f6e69", "policy": PALETTE[6]}

if __name__ == "__main__":
    a = base_parser(__doc__).parse_args()
    setup(a)
    style()
    res = ROOT / "matlab" / "results"
    tr = pd.read_csv(res / "validation_traces_sc1.csv")
    met = pd.read_csv(res / "validation_metrics.csv")
    fig = plt.figure(figsize=(7.2, 4.4))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.25, 1])
    ax = fig.add_subplot(gs[0, :])
    for c in ["fixed_tuned", "policy"]:
        g = tr[tr.controller == c]
        ax.plot(g.t, g.df_python_hz, color=COL[c], lw=3.0, alpha=0.35, label=f"{LAB[c]} — Python")
        ax.plot(g.t, g.df_matlab_hz, color=COL[c], lw=1.1, ls="--", label=f"{LAB[c]} — MATLAB")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Δf (Hz)")
    ax.set_title("Test scenario 1: frequency deviation, Python vs MATLAB", loc="left")
    ax.legend(ncol=2, fontsize=7)
    for j, (m, lab) in enumerate([("nadir_hz", "Nadir (Hz)"), ("bess_energy_kwh", "BESS energy (kWh)"),
                                  ("return", "Return")]):
        ax = fig.add_subplot(gs[1, j])
        g = met[met.metric == m]
        for c in LAB:
            h = g[g.controller == c]
            ax.scatter(h.python, h.matlab, s=16, color=COL[c], label=LAB[c], linewidths=0)
        lo, hi = g[["python", "matlab"]].min().min(), g[["python", "matlab"]].max().max()
        ax.plot([lo, hi], [lo, hi], color=MUTED, lw=0.8, ls=":")
        ax.set_xlabel(f"Python — {lab}")
        ax.set_ylabel("MATLAB")
        if j == 0:
            ax.legend(fontsize=6, loc="upper left")
    fig.tight_layout()
    out = ROOT / "results" / "figures"
    save(fig, out, "fig_matlab_validation")
    print("done")
