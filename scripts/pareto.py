"""Pareto comparison: is RL better than ANY fixed VSG, whatever the reward weights?

1. Sweeps the family of fixed VSGs (grid of H × D) on the held-out TEST scenarios.
2. Reads RL and baseline results from <eval.out_dir>/per_scenario.csv (run evaluate.py first).
3. Plots two trade-offs, each against the VSG fast energy (BESS/PV effort that H and D control):
     * time outside the ±0.2 Hz band     * worst-event frequency nadir
   A controller is a contribution only if no fixed VSG is at least as good on every objective
   (fast energy, band time, nadir, RoCoF) — checked numerically below the plot.

Outputs: <eval.out_dir>/pareto_fixed.csv, pareto_summary.csv, figures/fig_pareto.{pdf,png}

Example
  python scripts/evaluate.py && python scripts/pareto.py
"""
import itertools

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from _common import base_parser, setup  # noqa: E402
from plot import LABEL, MUTED, color, save, style  # noqa: E402

from vsgrl.config import resolve_path  # noqa: E402
from vsgrl.controllers import FixedTunedVSG  # noqa: E402
from vsgrl.data.hybrid import load_processed  # noqa: E402
from vsgrl.envs import VSGEnv  # noqa: E402
from vsgrl.rollout import run_episode  # noqa: E402
from vsgrl.scenarios import scenarios_from_frame  # noqa: E402

H_GRID = [1.0, 3.0, 5.0, 8.0]
D_GRID = [5.0, 10.0, 15.0, 20.0, 30.0, 50.0]
X = "vsg_fast_energy_kwh"
YS = [("time_outside_band_s", "Time outside ±0.2 Hz band (s / episode)"),
      ("nadir_hz", "Worst-event frequency deviation (Hz)"),
      ("rocof_max_hz_s", "Max RoCoF, 100 ms window (Hz/s)")]


def front(df, x, y):
    """Lower-left Pareto front (minimise both)."""
    pts = df.sort_values([x, y])
    keep, best = [], np.inf
    for _, r in pts.iterrows():
        if r[y] < best:
            keep.append(r)
            best = r[y]
    return pd.DataFrame(keep)


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--alpha", type=float, default=0.7)
    p.add_argument("--reuse", action="store_true", help="reuse pareto_fixed.csv if present")
    a = p.parse_args()
    cfg = setup(a)
    out = resolve_path(cfg["eval"]["out_dir"])
    scen_file = out / "scenarios_test.csv"
    if not scen_file.exists():
        raise SystemExit("Run scripts/evaluate.py first (it creates the test scenario set).")
    scs = scenarios_from_frame(pd.read_csv(scen_file))

    fixed_file = out / "pareto_fixed.csv"
    if a.reuse and fixed_file.exists():
        fixed = pd.read_csv(fixed_file)
    else:
        env = VSGEnv(cfg, load_processed(cfg), split="test", record_trace=True)
        rows = []
        for H, D in itertools.product(H_GRID, D_GRID):
            ctrl = FixedTunedVSG(cfg, env, h=H, d=D, alpha=a.alpha)
            ms = [run_episode(env, ctrl, sc)[0] for sc in scs]
            r = {"H": H, "D": D, **{k: float(np.mean([m[k] for m in ms])) for k in
                                     [X, "time_outside_band_s", "nadir_hz", "rocof_max_hz_s", "return",
                                      "saturation_s"]}}
            rows.append(r)
            print(f"fixed H={H:3.0f} D={D:4.0f}: fast {r[X]:.3f} kWh  out-of-band {r['time_outside_band_s']:.2f} s"
                  f"  nadir {r['nadir_hz']:.3f} Hz  return {r['return']:.2f}")
        fixed = pd.DataFrame(rows)
        fixed.to_csv(fixed_file, index=False)

    res = pd.read_csv(out / "per_scenario.csv")
    if X not in res:
        raise SystemExit(f"{out / 'per_scenario.csv'} predates the fast-energy metric: re-run evaluate.py.")
    cols = [X, "time_outside_band_s", "nadir_hz", "rocof_max_hz_s", "return", "saturation_s"]
    per_seed = res.groupby(["controller", "seed"])[cols].mean().reset_index()
    summ = per_seed.groupby("controller")[cols].agg(["mean", "std"])
    summ.to_csv(out / "pareto_summary.csv")

    # Multi-objective dominance: a controller is beaten only if some fixed VSG is at least as
    # good on ALL of (fast energy, band time, nadir, RoCoF) and strictly better on one.
    OBJ = [X, "time_outside_band_s", "nadir_hz", "rocof_max_hz_s"]
    print("\nDominance vs the fixed-VSG family (objectives: " + ", ".join(OBJ) + "):")
    for c, g in per_seed.groupby("controller"):
        if c in ("none", "droop"):        # references: collapse ends episodes early / RoCoF far over limit
            continue
        m = g[OBJ].mean()
        dom = fixed[(fixed[OBJ] <= m.values + 1e-9).all(axis=1) & (fixed[OBJ] < m.values - 1e-9).any(axis=1)]
        if len(dom):
            best = dom.sort_values(X).iloc[0]
            tag = f"dominated by fixed H={best.H:.0f} s, D={best.D:.0f} ({len(dom)} fixed settings)"
        else:
            tag = "NON-dominated — no fixed VSG is at least as good on every objective"
        print(f"  {c:16s} fast {m[X]:.3f} kWh, band {m['time_outside_band_s']:.2f} s, nadir {m['nadir_hz']:.3f} Hz,"
              f" RoCoF {m['rocof_max_hz_s']:.3f} Hz/s → {tag}")

    style()
    fig, axs = plt.subplots(1, 3, figsize=(10.0, 3.1))
    for ax, (y, ylab) in zip(axs, YS):
        ax.scatter(fixed[X], fixed[y], s=14, color=MUTED, alpha=0.5, linewidths=0, label="Fixed VSG family")
        f = front(fixed, X, y)
        ax.plot(f[X], f[y], color=MUTED, lw=1.2, ls="--", drawstyle="steps-post",
                label="Fixed-VSG front (attainable)")
        for c, g in per_seed.groupby("controller"):
            if c in ("none", "droop", "fixed_feasible"):     # references; fixed_feasible ≈ fixed_tuned
                continue
            ax.errorbar(g[X].mean(), g[y].mean(), xerr=g[X].std() if len(g) > 1 else None,
                        yerr=g[y].std() if len(g) > 1 else None, fmt="o", ms=6, color=color(c),
                        mec="white", mew=1.0, elinewidth=1.0, capsize=2, label=LABEL.get(c, c))
        ax.set_xlabel("VSG fast energy (kWh / episode)")
        ax.set_ylabel(ylab)
    h, l = axs[0].get_legend_handles_labels()
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    fig.legend(h, l, ncol=4, loc="upper center", bbox_to_anchor=(0.5, 1.0), fontsize=7)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    save(fig, out / "figures", "fig_pareto")
