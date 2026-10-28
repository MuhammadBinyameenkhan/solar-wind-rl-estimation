"""Figure for the headroom-rule ablation (run scripts/headroom_ablation.py first).

Dot plot: one row per fixed VSG setting, one marker per feasibility treatment, three panels
(converter saturation, worst-event nadir, objective return). Output: figures/fig_headroom_ablation.*
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from _common import base_parser, setup  # noqa: E402
from plot import MUTED, PALETTE, save, style  # noqa: E402

from vsgrl.config import resolve_path  # noqa: E402

TREAT = [("none", "No constraint", "#8a8985", "o"),
         ("max_clip", "Max rule, separate clip", PALETTE[0], "s"),
         ("max_scale", "Max rule, joint scaling", PALETTE[1], "D"),
         ("sum_scale", "Sum rule, joint scaling", PALETTE[2], "^"),
         ("sum_scale_wide", "Sum rule, joint, 0.5 Hz / 2 Hz/s", PALETTE[3], "v")]
SETTINGS = [("tuned", "Tuned (J 3, D 15)"), ("standard", "Standard (J 3, D 20)"), ("low", "Low (J 1, D 10)"),
            ("high", "High (J 4, D 30)"), ("range_max", "Range max (J 8, D 50)")]
PANELS = [("saturation_s", "Converter saturation (s / episode)"),
          ("nadir_hz", "Worst-event nadir deviation (Hz)"),
          ("return", "Objective return (higher is better)")]

if __name__ == "__main__":
    a = base_parser(__doc__).parse_args()
    cfg = setup(a)
    out = resolve_path(cfg["eval"]["out_dir"])
    s = pd.read_csv(out / "headroom_ablation_summary.csv").set_index(["controller", "treatment"])
    style()
    fig, axs = plt.subplots(1, 3, figsize=(10.0, 3.4), sharey=True)
    off = {t[0]: (i - 2) * 0.13 for i, t in enumerate(TREAT)}
    for ax, (col, lab) in zip(axs, PANELS):
        for y, (c, _) in enumerate(SETTINGS):
            ax.axhline(y, color="#e4e3df", lw=0.8, zorder=0)
            for t, tl, colr, mk in TREAT:
                ax.plot(s.loc[(c, t), col], y + off[t], marker=mk, ms=6, color=colr, mec="white", mew=0.8,
                        ls="none", label=tl if (y == 0 and col == PANELS[0][0]) else None)
        ax.set_xlabel(lab)
        ax.grid(axis="y", visible=False)
    axs[0].set_yticks(range(len(SETTINGS)))
    axs[0].set_yticklabels([sl for _, sl in SETTINGS])
    axs[0].invert_yaxis()
    h, l = axs[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0, 1, 0.86))
    fig.legend(h, l, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.0), fontsize=7, frameon=False,
               labelcolor=MUTED)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    save(fig, out / "figures", "fig_headroom_ablation")
