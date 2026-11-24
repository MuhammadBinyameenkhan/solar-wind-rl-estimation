"""EMT (circuit-level) vs averaged-model figure and summary numbers.

Inputs (from matlab/simscape, run_simscape_validation and export_emt_traces_csv):
  results/simscape_metrics*.csv   per scenario/controller metrics, columns controller,scenario,metric,rms,emt
  results/emt_traces_sc1.csv      traces of one scenario
Outputs: results/figures/fig_emt_validation.{pdf,png}, paper/emt_numbers.json, and a printed summary.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from _common import ROOT, base_parser, setup  # noqa: E402
from plot import PALETTE, save, style  # noqa: E402

SIM = ROOT / "matlab" / "simscape" / "results"
CTRL = [("fixed_tuned", "Fixed VSG (tuned)", PALETTE[0]), ("fixed_feasible", "Fixed VSG + projection", PALETTE[1]),
        ("policy", "TD3 policy", PALETTE[6])]

if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--scenario", type=int, default=1)
    a = p.parse_args()
    cfg = setup(a)
    m = pd.concat([pd.read_csv(f) for f in sorted(SIM.glob("simscape_metrics*.csv"))], ignore_index=True)
    m = m.drop_duplicates(["controller", "scenario", "metric"])
    piv = m.pivot_table(index=["controller", "scenario"], columns="metric", values=["rms", "emt"])
    n_sc = m["scenario"].nunique()
    print(f"{n_sc} scenarios, {m['controller'].nunique()} controllers")
    summ = m.groupby(["controller", "metric"])[["rms", "emt"]].mean().unstack("controller")
    with pd.option_context("display.width", 200, "display.float_format", "{:.4f}".format):
        print(summ)

    def rel(metric):
        r, e = piv["rms"][metric], piv["emt"][metric]
        return 100 * (e.mean() - r.mean()) / r.mean()

    rmse = piv["emt"]["rmse_df_hz"].groupby(level="controller").mean()
    proj = piv["emt"]["infeasible_commit_s"].loc[["fixed_feasible", "policy"]]
    nums = {
        "n_scenarios": int(n_sc),
        "rmse_range": f"{rmse.min():.3f}–{rmse.max():.3f}",
        "nadir_diff": f"{rel('nadir_hz'):+.0f} % deeper" if rel("nadir_hz") > 0 else f"{-rel('nadir_hz'):.0f} % shallower",
        "bess_diff": f"{rel('bess_energy_kwh'):+.1f} %",
        "rocof100_factor": f"{(piv['emt']['rocof_max_hz_s'].mean() / piv['rms']['rocof_max_hz_s'].mean()):.1f}",
        "rocof500_diff": f"{rel('rocof_500ms_hz_s'):+.0f} %",
        "infeasible_emt": f"≤ {proj.groupby(level='controller').mean().max():.2f} s",
        "solver_note": "The results below were obtained with a fixed-step script solver of the same three-phase "
                       "circuit; the Simscape Electrical model built from the same files is provided for "
                       "confirmation in MATLAB R2021a.",
    }
    print(json.dumps(nums, indent=1, ensure_ascii=False))
    (ROOT / "paper" / "emt_numbers.json").write_text(json.dumps(nums, indent=1, ensure_ascii=False))

    tr = pd.read_csv(SIM / f"emt_traces_sc{a.scenario}.csv")
    style()
    fig, axs = plt.subplots(2, 3, figsize=(10.0, 4.6), sharex=True)
    for j, (c, lab, col) in enumerate(CTRL):
        for i, (y, ylab) in enumerate([("df_hz", "Δf (Hz)"), ("p_vsg_mw", "VSG power (MW)")]):
            ax = axs[i, j]
            r = tr[(tr.controller == c) & (tr.model == "rms")]
            e = tr[(tr.controller == c) & (tr.model == "emt")]
            ax.plot(r.t, r[y], color="#b5b4ae", lw=2.6, label="Averaged (RMS) model")
            ax.plot(e.t, e[y], color=col, lw=1.1, ls="--", label="Three-phase EMT model")
            if j == 0:
                ax.set_ylabel(ylab)
            if i == 0:
                ax.set_title(lab, fontsize=9)
            if i == 1:
                ax.set_xlabel("Time (s)")
    h, l = axs[0, 0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.legend(h, l, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.0), fontsize=8, frameon=False)
    out = ROOT / "results" / "figures"
    save(fig, out, "fig_emt_validation")
