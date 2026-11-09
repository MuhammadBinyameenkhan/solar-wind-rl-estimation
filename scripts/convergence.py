"""Reward-convergence check: has training reached a plateau, and how close is it to the attainable optimum?

For every run (algorithm or tag) and seed in <train.out_dir>, the validation return logged during training
(deterministic policy, the same fixed validation scenarios at every evaluation) is tested for convergence,
and the result is placed between two references computed on exactly those validation scenarios:

  best fixed  the best single fixed VSG of the oracle grid (scripts/oracle_test.py), and the tuned fixed VSG;
  oracle      the best grid setting chosen separately for each scenario (upper bound for scenario-level
              adaptation; a policy that adapts within an episode may in principle exceed it).

Criteria (fixed before any result is seen; no tuned thresholds):
  plateau     ordinary least-squares slope of validation return against episode over the last --window
              fraction of the evaluations; "converged" if the slope is not significantly different from zero
              (two-sided t-test, p >= 0.05), "still improving" if significantly positive, "degrading" if
              significantly negative.
  gap closed  (R_policy - R_best_fixed) / (R_oracle - R_best_fixed) for the final and the selected (best
              validation) checkpoint; 1 = oracle reached, 0 = no better than the best fixed setting.
  seeds       interquartile mean (IQM) of the final validation returns with a 95 % percentile-bootstrap
              confidence interval (Agarwal et al., NeurIPS 2021), and mean +- s.d. learning curves.
  critic      the same slope test on the episode-mean critic loss over the last window (reported only).

Outputs: <eval.out_dir>/convergence/{convergence_seeds.csv, convergence_summary.csv, reference_val.csv}
         <eval.out_dir>/figures/fig_convergence.{png,pdf}

Example
  python scripts/convergence.py --tags td3 ddpg td3_noproj
  python scripts/convergence.py --config study3_ieee33/configs/ieee33.yaml --tags td3 ddpg
"""
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from _common import base_parser, setup
from oracle_test import D_GRID, H_GRID
from scipy import stats

from vsgrl.config import resolve_path
from vsgrl.controllers import FixedTunedVSG, make_baseline
from vsgrl.data.hybrid import load_processed
from vsgrl.rollout import run_episode


def make_env(cfg, df, split):
    """Study 2 single-bus environment, or the Study 3 feeder environment when the config selects it."""
    if cfg["system"].get("network", {}).get("model") == "ieee33":
        import sys
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "study3_ieee33"))
        from vsgrl33.env33 import Ieee33VSGEnv
        return Ieee33VSGEnv(cfg, df, split=split, record_trace=True)
    from vsgrl.envs import VSGEnv
    return VSGEnv(cfg, df, split=split, record_trace=True)


def slope_test(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 3 or np.ptp(y) == 0.0:
        return np.nan, np.nan
    r = stats.linregress(x, y)
    return float(r.slope), float(r.pvalue)


def verdict(slope, p, alpha=0.05):
    if not np.isfinite(p):
        return "n/a"
    if p >= alpha:
        return "converged (plateau)"
    return "still improving" if slope > 0 else "degrading"


def iqm_ci(x, n_boot=10000, seed=0):
    x = np.sort(np.asarray(x, float))
    iqm = lambda v: stats.trim_mean(v, 0.25)                      # noqa: E731
    rng = np.random.default_rng(seed)
    boots = [iqm(rng.choice(x, len(x), replace=True)) for _ in range(n_boot)]
    return iqm(x), np.percentile(boots, 2.5), np.percentile(boots, 97.5)


def references(cfg, out_csv, alpha):
    """Fixed-grid returns on the training validation scenarios (cached)."""
    if out_csv.exists():
        return pd.read_csv(out_csv)
    df = load_processed(cfg)
    env = make_env(cfg, df, "val")
    t = cfg["train"]
    scs = env.sampler.fixed_set("val", t["eval_episodes"], cfg["eval"]["scenario_seed"] + 1)   # as in vsgrl/train.py
    rows = []
    for H, D in itertools.product(H_GRID, D_GRID):
        ctrl = FixedTunedVSG(cfg, env, h=H, d=D, alpha=alpha)
        for i, sc in enumerate(scs):
            rows.append({"controller": f"grid_H{H:g}_D{D:g}", "scenario": i, "return": run_episode(env, ctrl, sc)[0]["return"]})
        print(f"  reference grid H={H:g} s, D={D:g} pu done")
    tuned = make_baseline("fixed_tuned", cfg, env)          # tuned gains from eval.baseline_params
    for i, sc in enumerate(scs):
        rows.append({"controller": "fixed_tuned", "scenario": i, "return": run_episode(env, tuned, sc)[0]["return"]})
    ref = pd.DataFrame(rows)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    ref.to_csv(out_csv, index=False)
    return ref


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--tags", nargs="+", default=["td3", "ddpg"])
    p.add_argument("--window", type=float, default=0.25, help="fraction of the evaluations used for the plateau test")
    p.add_argument("--alpha", type=float, default=0.7, help="PV share of the oracle grid (as in oracle_test.py)")
    a = p.parse_args()
    cfg = setup(a)
    runs = resolve_path(cfg["train"]["out_dir"])
    out = resolve_path(cfg["eval"]["out_dir"]) / "convergence"

    ref = references(cfg, out / "reference_val.csv", a.alpha)
    grid = ref[ref.controller.str.startswith("grid_")].pivot(index="scenario", columns="controller", values="return")
    R_fixed = float(grid.mean().max())
    R_oracle = float(grid.max(axis=1).mean())
    R_tuned = float(ref[ref.controller == "fixed_tuned"]["return"].mean())
    print(f"validation references: best fixed {R_fixed:.2f} ({grid.mean().idxmax()}), tuned fixed {R_tuned:.2f}, "
          f"oracle {R_oracle:.2f}")
    gap = R_oracle - R_fixed

    seed_rows, curves = [], {}
    for tag in a.tags:
        for sd in sorted((runs / tag).glob("seed*")):
            v = pd.read_csv(sd / "val_log.csv")
            tr = pd.read_csv(sd / "train_log.csv")
            n_w = max(3, int(np.ceil(a.window * len(v))))
            last = v.tail(n_w)
            s, pv = slope_test(last.episode, last.val_return)
            ep_cut = last.episode.min()
            cl = tr[tr.episode >= ep_cut]
            cs, cp = slope_test(cl.episode, cl.critic_loss)
            r_final, r_best = float(v.val_return.iloc[-1]), float(v.val_return.max())
            seed_rows.append({
                "run": tag, "seed": sd.name, "evaluations": len(v), "window_evals": n_w,
                "window_from_episode": int(ep_cut), "slope_per_100_ep": 100 * s, "p_slope": pv,
                "verdict": verdict(s, pv), "val_return_untrained": float(v.val_return.iloc[0]),
                "val_return_final": r_final, "val_return_best": r_best,
                "best_at_episode": int(v.episode.iloc[int(v.val_return.values.argmax())]),
                "window_mean": float(last.val_return.mean()), "window_sd": float(last.val_return.std(ddof=1)),
                "gap_closed_final": (r_final - R_fixed) / gap if gap > 0 else np.nan,
                "gap_closed_best": (r_best - R_fixed) / gap if gap > 0 else np.nan,
                "critic_slope_per_100_ep": 100 * cs, "p_critic_slope": cp})
            curves.setdefault(tag, []).append(v.set_index("episode").val_return)
    S = pd.DataFrame(seed_rows)
    out.mkdir(parents=True, exist_ok=True)
    S.to_csv(out / "convergence_seeds.csv", index=False)

    summ = []
    for tag, g in S.groupby("run", sort=False):
        m, lo, hi = iqm_ci(g.val_return_final)
        summ.append({"run": tag, "seeds": len(g), "converged_seeds": int((g.verdict == "converged (plateau)").sum()),
                     "improving_seeds": int((g.verdict == "still improving").sum()),
                     "degrading_seeds": int((g.verdict == "degrading").sum()),
                     "iqm_final": m, "iqm_ci_low": lo, "iqm_ci_high": hi,
                     "mean_gap_closed_final": g.gap_closed_final.mean(), "mean_gap_closed_best": g.gap_closed_best.mean(),
                     "R_best_fixed": R_fixed, "R_tuned_fixed": R_tuned, "R_oracle": R_oracle})
    T = pd.DataFrame(summ)
    T.to_csv(out / "convergence_summary.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_columns", 30, "display.float_format", "{:.3f}".format):
        print(S[["run", "seed", "verdict", "slope_per_100_ep", "p_slope", "val_return_final", "val_return_best",
                 "gap_closed_final", "gap_closed_best"]].to_string(index=False))
        print()
        print(T.to_string(index=False))

    # ---------------------------------------------------------------- figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(curves), figsize=(3.3 * len(curves), 2.6), sharey=True, squeeze=False)
    for ax, (tag, cs) in zip(axes[0], curves.items()):
        C = pd.concat(cs, axis=1)
        for c in C:
            ax.plot(C.index, C[c], color="0.75", lw=0.7)
        ax.plot(C.index, C.mean(1), color="C0", lw=1.6, label="mean of seeds")
        ax.fill_between(C.index, C.mean(1) - C.std(1), C.mean(1) + C.std(1), color="C0", alpha=0.15, lw=0)
        ax.axhline(R_oracle, color="C3", ls="--", lw=1.0, label="oracle bound")
        ax.axhline(R_fixed, color="k", ls=":", lw=1.0, label="best fixed (grid)")
        ax.axhline(R_tuned, color="C2", ls="-.", lw=1.0, label="tuned fixed")
        w0 = S[S.run == tag].window_from_episode.min()
        ax.axvspan(w0, C.index.max(), color="0.9", lw=0, zorder=0)
        n_conv = int((S[S.run == tag].verdict == "converged (plateau)").sum())
        ax.set_title(f"{tag}: plateau in {n_conv}/{C.shape[1]} seeds", fontsize=8)
        ax.set_xlabel("Training episode")
    axes[0][0].set_ylabel("Validation return")
    axes[0][0].legend(fontsize=6, loc="lower right")
    fig.tight_layout()
    figdir = resolve_path(cfg["eval"]["out_dir"]) / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(figdir / f"fig_convergence.{ext}", dpi=300)
    print("wrote", out, "and", figdir / "fig_convergence.png")
