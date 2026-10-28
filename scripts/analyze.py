"""Statistics for the paper: multi-seed summary table, bootstrap CIs, paired
Wilcoxon signed-rank tests with Holm correction, and a LaTeX table.

RL controllers: metrics are first averaged over seeds per scenario (so each
scenario is one paired observation); seed-to-seed spread is reported
separately as mean ± std of the per-seed means.
"""
import numpy as np
import pandas as pd
from _common import base_parser, setup
from scipy.stats import wilcoxon

from vsgrl.config import resolve_path
from vsgrl.controllers import BASELINES

METRICS = [("nadir_hz", "Max |Δf| (Hz)", "min"), ("rocof_max_hz_s", "Max RoCoF (Hz/s)", "min"),
           ("qss_dev_hz", "QSS |Δf| (Hz)", "min"), ("settling_time_s", "Settling (s)", "min"),
           ("bess_energy_kwh", "BESS energy (kWh)", "min"), ("saturation_s", "Saturation (s)", "min"),
           ("infeasible_commit_s", "Infeasible commit. (s)", "min"),
           ("return", "Return", "max")]


def boot_ci(x, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    m = rng.choice(x, size=(n, len(x)), replace=True).mean(1)
    return np.percentile(m, [2.5, 97.5])


def holm(pvals):
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for i, k in enumerate(order):
        run = max(run, (len(p) - i) * p[k])
        adj[k] = min(run, 1.0)
    return adj


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--reference", default=None, help="controller tested against all others (default: best RL)")
    a = p.parse_args()
    cfg = setup(a)
    out = resolve_path(cfg["eval"]["out_dir"])
    df = pd.read_csv(out / "per_scenario.csv")
    df["f_violation"] = df["f_violation"].astype(float)
    df["rocof_violation"] = df["rocof_violation"].astype(float)
    df["collapsed"] = df["collapsed"].astype(float)
    cols = [m for m, _, _ in METRICS] + ["f_violation", "rocof_violation", "collapsed"]

    per_sc = df.groupby(["controller", "scenario"])[cols].mean().reset_index()   # seed-averaged
    per_seed = df.groupby(["controller", "seed"])[cols].mean().reset_index()

    rows = []
    for c, g in per_sc.groupby("controller"):
        r = {"controller": c, "n_seeds": df[df.controller == c].seed.nunique(), "n_scenarios": len(g)}
        for m in cols:
            r[m] = g[m].mean()
            lo, hi = boot_ci(g[m])
            r[m + "_ci_lo"], r[m + "_ci_hi"] = lo, hi
            r[m + "_seed_std"] = per_seed[per_seed.controller == c][m].std(ddof=1) if r["n_seeds"] > 1 else 0.0
        rows.append(r)
    summ = pd.DataFrame(rows).sort_values("return", ascending=False)
    summ.to_csv(out / "summary.csv", index=False)

    show = ["controller", "n_seeds"] + cols
    print("\n=== Mean over test scenarios (RL: seed-averaged) ===")
    print(summ[show].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # --- paired significance tests ------------------------------------
    rl = [c for c in summ.controller if c not in BASELINES]          # summ is sorted by return
    ref = a.reference or (rl[0] if rl else summ.controller.iloc[0])
    tests = []
    piv = {m: per_sc.pivot(index="scenario", columns="controller", values=m) for m, _, _ in METRICS}
    for m, label, _ in METRICS:
        for c in piv[m].columns:
            if c == ref:
                continue
            x, y = piv[m][ref], piv[m][c]
            ok = x.notna() & y.notna()
            d = (x - y)[ok]
            pval = wilcoxon(x[ok], y[ok]).pvalue if (d != 0).any() else 1.0
            tests.append({"reference": ref, "vs": c, "metric": m, "median_diff": float(np.median(d)),
                          "ref_better_frac": float(np.mean(d > 0) if m == "return" else np.mean(d < 0)),
                          "p": pval})
    t = pd.DataFrame(tests)
    if len(t):
        t["p_holm"] = holm(t["p"])
        t.to_csv(out / "significance.csv", index=False)
        print(f"\n=== Wilcoxon signed-rank, {ref} vs others (Holm-adjusted) ===")
        print(t.to_string(index=False, float_format=lambda x: f"{x:.4g}"))

    # --- LaTeX table ----------------------------------------------------
    lines = [r"\begin{tabular}{l" + "c" * len(METRICS[:6]) + "}", r"\toprule",
             "Controller & " + " & ".join(l for _, l, _ in METRICS[:6]) + r" \\", r"\midrule"]
    for _, r in summ.iterrows():
        cells = []
        for m, _, _ in METRICS[:6]:
            s = f"{r[m]:.3f}"
            if r["n_seeds"] > 1:
                s += f" $\\pm$ {r[m + '_seed_std']:.3f}"
            cells.append(s)
        lines.append(r["controller"].replace("_", r"\_") + " & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (out / "table_main.tex").write_text("\n".join(lines))
    print("\nwrote", out / "summary.csv", out / "table_main.tex")
