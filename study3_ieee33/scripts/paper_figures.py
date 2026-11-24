"""Figures and numbers for the IEEE 33-bus manuscript (paper/make_ieee33_manuscript.js).

Everything is read from the committed result files; nothing is re-simulated.
  results/per_scenario.csv          test set (200 scenarios), every controller and seed
  results/significance.csv          paired Wilcoxon / Holm (scripts/analyze.py)
  runs/{td3,ddpg}/seed*/val_log.csv validation curves
  results/convergence/*.csv         convergence verdicts and references
  results/oracle_map/summary.csv    scenario-level oracle over 12 plant conditions
  results/oracle_event/summary.csv  event-wise oracle (nominal, most_room)
  runs_hp/*/seed*/summary.json      hyperparameter screen
Outputs: results/figures/fig_{test_paired,convergence_paper,oracle,traces}.png/.pdf
         results/paper_numbers.json
Run: python study3_ieee33/scripts/paper_figures.py
"""
import glob
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from scipy.stats import wilcoxon

S3 = Path(__file__).resolve().parents[1]
R = S3 / "results"
FIG = R / "figures"
FIG.mkdir(parents=True, exist_ok=True)

for f in font_manager.findSystemFonts():
    if "NimbusRoman" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Nimbus Roman", "mathtext.fontset": "stix", "font.size": 8,
                     "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42})
# categorical order (validated: CVD dE >= 9, normal-vision dE >= 24); text stays black
C = {"td3": "#1f5fa8", "ddpg": "#d9822b", "bang_bang": "#2e7d32", "fixed_feasible": "#7b4fa0",
     "fixed_tuned": "#404040", "grid": "#d0d0d0"}
NAME = {"fixed": "Fixed VSG (untuned)", "fixed_tuned": "Fixed VSG (tuned)", "fixed_feasible": "Fixed VSG + projection",
        "bang_bang": "Bang-bang", "adaptive_rocof": "Adaptive RoCoF", "adaptive_dir": "Direction-aware",
        "fuzzy": "Fuzzy", "td3": "TD3", "ddpg": "DDPG"}


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=600, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("wrote", FIG / f"{name}.png")


# ------------------------------------------------------------------ test-set numbers
A = pd.read_csv(R / "per_scenario.csv")
MET = ["return", "nadir_hz", "rocof_max_hz_s", "settling_time_s", "bess_energy_kwh", "qss_dev_hz",
       "infeasible_commit_s", "saturation_s", "rocof_violation", "f_violation", "collapsed"]
per = A.groupby(["controller", "scenario"])[MET].mean()            # RL: mean over seeds per scenario
order = ["fixed", "fixed_tuned", "fixed_feasible", "bang_bang", "adaptive_rocof", "adaptive_dir", "fuzzy", "ddpg", "td3"]
num = {"test": {}, "seed_return": {}, "paired": {}}
rng = np.random.default_rng(0)
for c in order:
    d = per.loc[c]
    row = {}
    for m in MET:
        x = d[m].to_numpy(float)
        bs = rng.choice(x, size=(2000, len(x))).mean(1)
        row[m] = [float(x.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    num["test"][c] = row
    num["seed_return"][c] = A[A.controller == c].groupby("seed")["return"].mean().round(4).tolist()


def paired(a, b, m):
    x = per.loc[a][m].to_numpy(float) - per.loc[b][m].to_numpy(float)
    nz = x[np.abs(x) > 1e-12]
    p = float(wilcoxon(nz).pvalue) if len(nz) > 0 else 1.0
    return {"mean_diff": float(x.mean()), "median_diff": float(np.median(x)),
            "a_better_frac": float(np.mean(x > 1e-12) if m == "return" else np.mean(x < -1e-12)), "p": p}


# the comparisons reported in the text (raw p; Holm-adjusted values are in significance.csv)
for a, b in [("td3", "fixed_tuned"), ("td3", "fixed_feasible"), ("td3", "ddpg"), ("ddpg", "fixed_feasible"),
             ("td3", "fixed"), ("fixed_tuned", "fixed")]:
    num["paired"][f"{a}_vs_{b}"] = {m: paired(a, b, m) for m in
                                    ["return", "nadir_hz", "rocof_max_hz_s", "settling_time_s", "bess_energy_kwh"]}
sig = pd.read_csv(R / "significance.csv")
num["holm"] = {f"{r.vs}|{r.metric}": [float(r.median_diff), float(r.ref_better_frac), float(r.p), float(r.p_holm)]
               for r in sig.itertuples() if r.reference == "td3"}
num["n_test"] = int(per.loc["td3"].shape[0])

# per-seed TD3 / DDPG against their own base controller (fixed VSG + projection)
num["seed_vs_base"] = {}
base = A[A.controller == "fixed_feasible"].set_index("scenario")["return"]
for c in ("td3", "ddpg"):
    for s, g in A[A.controller == c].groupby("seed"):
        x = g.set_index("scenario")["return"] - base
        nz = x[np.abs(x) > 1e-12]
        num["seed_vs_base"][f"{c}_s{s}"] = {"mean_diff": float(x.mean()),
                                            "p": float(wilcoxon(nz).pvalue) if len(nz) else 1.0,
                                            "identical": bool(len(nz) == 0)}

# ------------------------------------------------------------------ Fig. test: paired differences
fig, axs = plt.subplots(1, 4, figsize=(7.16, 2.15))
cs = ["bang_bang", "fixed_feasible", "ddpg", "td3"]
specs = [("return", "$\\Delta$ return (higher = better)", 1), ("nadir_hz", "$\\Delta$ max $|\\Delta f|$ (Hz)", 1),
         ("rocof_max_hz_s", "$\\Delta$ max RoCoF (Hz/s)", 1), ("settling_time_s", "$\\Delta$ settling time (s)", 1)]
for ax, (m, lab, _) in zip(axs, specs):
    ref = per.loc["fixed_tuned"][m].to_numpy(float)
    data = [per.loc[c][m].to_numpy(float) - ref for c in cs]
    bp = ax.boxplot(data, widths=0.55, showfliers=False, patch_artist=True,
                    medianprops=dict(color="black", lw=0.9), whiskerprops=dict(lw=0.6), capprops=dict(lw=0.6))
    for patch, c in zip(bp["boxes"], cs):
        patch.set(facecolor=C[c], alpha=0.35, edgecolor=C[c], lw=0.8)
    for i, (d, c) in enumerate(zip(data, cs)):
        ax.plot(i + 1, d.mean(), marker="D", ms=3.2, color=C[c], mec="white", mew=0.4, zorder=4)
    ax.axhline(0, color="black", lw=0.5, ls=(0, (2, 2)))
    ax.set_xticks(range(1, 5), ["Bang-\nbang", "Fixed +\nproj.", "DDPG", "TD3"], fontsize=7)
    ax.set_title(lab, fontsize=7.5)
    ax.yaxis.grid(True, color=C["grid"], lw=0.4)
    ax.set_axisbelow(True)
fig.tight_layout(w_pad=1.0)
save(fig, "fig_test_paired")

# ------------------------------------------------------------------ Fig. convergence (paper style)
conv = pd.read_csv(R / "convergence" / "convergence_seeds.csv")
ref = pd.read_csv(R / "convergence" / "reference_val.csv")
num["convergence"] = {"seeds": conv.to_dict("records"),
                      "summary": pd.read_csv(R / "convergence" / "convergence_summary.csv").to_dict("records"),
                      }
fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.3), sharey=True)
cs_ = pd.read_csv(R / "convergence" / "convergence_summary.csv")
r_fix, r_orc = float(cs_.R_best_fixed.iloc[0]), float(cs_.R_oracle.iloc[0])
for ax, algo in zip(axs, ("td3", "ddpg")):
    curves = []
    for f in sorted(glob.glob(str(S3 / f"runs/{algo}/seed*/val_log.csv"))):
        v = pd.read_csv(f)
        ax.plot(v.episode, v.val_return, color="#b0b0b0", lw=0.6)
        curves.append(v.val_return.to_numpy())
    M = np.mean(curves, 0)
    ax.plot(v.episode, M, color=C[algo], lw=1.4, label=f"{algo.upper()}, mean of 5 seeds")
    if r_fix is not None:
        ax.axhline(r_fix, color="black", lw=0.7, ls=(0, (1.5, 1.5)), label="Best fixed VSG (tuned)")
    if r_orc is not None:
        ax.axhline(r_orc, color="#b2322b", lw=0.7, ls=(0, (4, 2)), label="Per-scenario oracle")
    ax.axvspan(750, 1000, color="#eeeeee", zorder=0)
    ax.set_xlabel("Training episode")
    nconv = int((conv[conv.run == algo].verdict.str.startswith("converged")).sum())
    ax.set_title(f"{algo.upper()}: plateau in {nconv}/5 seeds", fontsize=8)
    ax.set_ylim(-72, -46.5)
    ax.yaxis.grid(True, color=C["grid"], lw=0.4)
    ax.legend(fontsize=6.5, frameon=False, loc="lower right")
axs[0].set_ylabel("Validation return")
fig.tight_layout(w_pad=1.0)
save(fig, "fig_convergence_paper")

# ------------------------------------------------------------------ Fig. oracle bounds
om = pd.read_csv(R / "oracle_map" / "summary.csv")
ev = pd.read_csv(R / "oracle_event" / "summary.csv")
num["oracle_map"] = om.to_dict("records")
num["oracle_event"] = ev.to_dict("records")
fig, axs = plt.subplots(1, 2, figsize=(7.16, 2.35), gridspec_kw={"width_ratios": [2.2, 1]})
om = om.sort_values(["diesel_mva", "event_factor", "bess_frac"]).reset_index(drop=True)
lab = [f"{b:g}/{d:g}/{e:g}" for b, d, e in zip(om.bess_frac, om.diesel_mva, om.event_factor)]
cols = ["#1f5fa8" if (b == 0.625 and d == 4.9 and e == 1.0) else "#9fb7d6" for b, d, e in
        zip(om.bess_frac, om.diesel_mva, om.event_factor)]
axs[0].bar(range(len(om)), om.oracle_gain_pct, color=cols, width=0.7)
for i, g in enumerate(om.oracle_gain_pct):
    axs[0].text(i, g + 0.08, f"{g:.2f}", ha="center", va="bottom", fontsize=6)
axs[0].set_xticks(range(len(om)), lab, rotation=55, ha="right", fontsize=6.5)
axs[0].set_ylabel("Oracle gain over best fixed (%)")
axs[0].set_xlabel("BESS (× peak load) / diesel (MVA) / event-size factor")
axs[0].set_title("(a) Scenario-level oracle over 12 plant conditions", fontsize=8)
axs[0].yaxis.grid(True, color=C["grid"], lw=0.4)
axs[0].set_axisbelow(True)
x = np.arange(len(ev))
axs[1].bar(x - 0.18, ev.scen_gain_pct, width=0.34, color="#9fb7d6", label="One setting per scenario")
axs[1].bar(x + 0.18, ev.event_gain_pct, width=0.34, color="#1f5fa8", label="New setting at each event")
for i in x:
    axs[1].text(i - 0.18, ev.scen_gain_pct[i] + 0.12, f"{ev.scen_gain_pct[i]:.2f}", ha="center", fontsize=6)
    axs[1].text(i + 0.18, ev.event_gain_pct[i] + 0.12, f"{ev.event_gain_pct[i]:.2f}", ha="center", fontsize=6)
axs[1].set_xticks(x, ["Published\nplant", "Largest-room\ncondition"], fontsize=7)
axs[1].set_title("(b) Event-wise oracle", fontsize=8)
axs[1].legend(fontsize=6.3, frameon=False, loc="upper left")
axs[1].set_ylim(0, 10.5)
axs[1].yaxis.grid(True, color=C["grid"], lw=0.4)
axs[1].set_axisbelow(True)
fig.tight_layout(w_pad=1.2)
save(fig, "fig_oracle")

# ------------------------------------------------------------------ Fig. time response (one test scenario)
sc = 24
tr = {c: pd.read_csv(R / "traces" / f"{c}_sc{sc}.csv") for c in ("fixed_tuned_s0", "td3_s0", "ddpg_s0")}
num["trace_scenario"] = sc
fig, axs = plt.subplots(2, 2, figsize=(7.16, 3.4), sharex=True)
lines = [("fixed_tuned_s0", "Fixed VSG (tuned)", C["fixed_tuned"], (0, (3, 1.5))), ("ddpg_s0", "DDPG (seed 0)", C["ddpg"], "-"),
         ("td3_s0", "TD3 (seed 0)", C["td3"], "-")]
for key, lb, col, ls in lines:
    t = tr[key]
    axs[0, 0].plot(t.t, t.df_hz, color=col, lw=0.9, ls=ls, label=lb)
    axs[0, 1].plot(t.t, t.p_bess_mw, color=col, lw=0.9, ls=ls)
    axs[1, 0].plot(t.t, t.H_v, color=col, lw=0.9, ls=ls)
    axs[1, 1].plot(t.t, t.D_v, color=col, lw=0.9, ls=ls)
for ax, yl in zip(axs.flat, ["$\\Delta f$ (Hz)", "BESS power (MW)", "Virtual inertia $H_v$ (s)", "Virtual damping $D_v$ (pu)"]):
    ax.set_ylabel(yl)
    ax.yaxis.grid(True, color=C["grid"], lw=0.4)
axs[0, 0].axhspan(-0.2, 0.2, color="#eeeeee", zorder=0)
fig.legend(*axs[0, 0].get_legend_handles_labels(), fontsize=7, frameon=False, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.04))
for ax in axs[1]:
    ax.set_xlabel("Time (s)")
fig.tight_layout(h_pad=0.6, w_pad=1.0)
save(fig, "fig_traces")

# ------------------------------------------------------------------ hyperparameter screen
hp = []
for f in sorted(glob.glob(str(S3 / "runs_hp/*/seed*/summary.json"))):
    s = json.load(open(f))
    tag = Path(f).parts[-3]
    v = pd.read_csv(Path(f).with_name("val_log.csv"))
    hp.append({"run": tag, "seed": s["seed"], "best": s["best_val_return"], "final": float(v.val_return.iloc[-1])})
H = pd.DataFrame(hp)
H[["algo", "h"]] = H.run.str.split("_", expand=True)
num["hp_screen"] = H.groupby(["algo", "h"])[["best", "final"]].mean().reset_index().to_dict("records")
num["hp_runs"] = hp

json.dump(num, open(R / "paper_numbers.json", "w"), indent=1)
print("wrote", R / "paper_numbers.json")

# ------------------------------------------------------------------ reviewer items (added in revision 1)
extra = {}
ci = R / "oracle_ci.json"
if ci.exists():
    extra["oracle_ci"] = json.load(open(ci))
w = R / "oracle_weights" / "summary.csv"
if w.exists():
    extra["weights"] = pd.read_csv(w).to_dict("records")
    comp = pd.read_csv(R / "oracle_weights" / "components.csv")
    t = comp[(comp.H == 3.0) & (comp.D == 10.0)]
    extra["voltage"] = {"tuned_min": float(t.vmin.min()), "tuned_max": float(t.vmax.max()),
                        "all_min": float(comp.vmin.min()), "all_max": float(comp.vmax.max())}
hf = R / "half_events" / "per_scenario.csv"
if hf.exists():
    B = pd.read_csv(hf)
    ph = B.groupby(["controller", "scenario"])[MET].mean()
    extra["half"] = {c: {m: float(ph.loc[c][m].mean()) for m in MET} for c in ph.index.get_level_values(0).unique()}
    extra["half_paired"] = {}
    for a, b in [("td3", "fixed_tuned"), ("td3", "fixed_feasible"), ("ddpg", "fixed_feasible")]:
        if a in extra["half"] and b in extra["half"]:
            extra["half_paired"][f"{a}_vs_{b}"] = {}
            for m in ["return", "nadir_hz", "rocof_max_hz_s"]:
                x = ph.loc[a][m].to_numpy(float) - ph.loc[b][m].to_numpy(float)
                nz = x[np.abs(x) > 1e-12]
                extra["half_paired"][f"{a}_vs_{b}"][m] = {"mean_diff": float(x.mean()), "p": float(wilcoxon(nz).pvalue) if len(nz) else 1.0}
num.update(extra)
json.dump(num, open(R / "paper_numbers.json", "w"), indent=1)
print("added reviewer items:", list(extra))
