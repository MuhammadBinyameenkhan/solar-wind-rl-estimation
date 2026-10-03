"""Paper figures (PDF + PNG) into <eval.out_dir>/figures/.

  fig_learning_curves   validation return vs episode, mean ± std over seeds
  fig_response_<k>      frequency, RoCoF, VSG power and scheduled H/D for a representative scenario
  fig_metric_boxes      per-scenario distributions of nadir / RoCoF / BESS energy
  fig_headroom_policy   learned mean H and D vs available upward headroom
  fig_data_overview     real-data operating points (wind, PV, load) by split
"""
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from _common import base_parser, setup  # noqa: E402

from vsgrl.config import resolve_path  # noqa: E402
from vsgrl.data.hybrid import load_processed  # noqa: E402

# Categorical palette (validated reference order) — colour follows the controller, never its rank.
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ORDER = ["td3", "ddpg", "fixed", "bang_bang", "adaptive_rocof", "fixed_feasible", "droop", "none"]
LABEL = {"td3": "TD3-VSG (proposed)", "ddpg": "DDPG-VSG", "fixed": "Fixed VSG", "bang_bang": "Bang-bang VSG",
         "adaptive_rocof": "Adaptive VSG", "fixed_feasible": "Fixed VSG (projected)",
         "droop": "BESS droop (no inertia)", "none": "No support"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def color(c):
    if c in ORDER:
        return PALETTE[ORDER.index(c)]
    return PALETTE[(abs(hash(c)) % 3) + 5]


def style():
    plt.rcParams.update({
        "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9, "legend.fontsize": 8,
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.spines.top": False,
        "axes.spines.right": False, "lines.linewidth": 1.6, "figure.dpi": 150, "savefig.bbox": "tight",
        "legend.frameon": False,
    })


def save(fig, out, name):
    fig.savefig(out / f"{name}.pdf")
    fig.savefig(out / f"{name}.png", dpi=200)
    plt.close(fig)
    print("wrote", out / f"{name}.pdf")


def learning_curves(cfg, out):
    runs = resolve_path(cfg["train"]["out_dir"])
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    any_ = False
    for algo_dir in sorted(p for p in runs.glob("*") if p.is_dir()):
        logs = [pd.read_csv(f) for f in algo_dir.glob("seed*/val_log.csv")]
        if not logs:
            continue
        any_ = True
        m = pd.concat(logs).groupby("episode")["val_return"]
        mu, sd = m.mean(), m.std().fillna(0)
        c = color(algo_dir.name)
        ax.plot(mu.index, mu.values, color=c, label=f"{LABEL.get(algo_dir.name, algo_dir.name)} (n={len(logs)})")
        ax.fill_between(mu.index, mu - sd, mu + sd, color=c, alpha=0.18, linewidth=0)
    if any_:
        ax.set_xlabel("Training episode")
        ax.set_ylabel("Validation return")
        ax.set_title("Learning curves (mean ± std over seeds)", loc="left")
        ax.legend()
        save(fig, out, "fig_learning_curves")


def responses(cfg, out):
    ev = resolve_path(cfg["eval"]["out_dir"])
    tdir = ev / "traces"
    files = list(tdir.glob("*.csv"))
    current = set(pd.read_csv(ev / "per_scenario.csv").controller) if (ev / "per_scenario.csv").exists() else None
    by_sc = {}
    for f in files:
        m = re.match(r"(.+)_s(\d+)_sc(\d+)\.csv", f.name)
        if m and (current is None or m.group(1) in current):   # skip traces of runs no longer evaluated
            by_sc.setdefault(int(m.group(3)), {}).setdefault(m.group(1), []).append(f)
    show = ["none", "droop", "fixed", "bang_bang", "adaptive_rocof", "ddpg", "td3"]
    for k, ctrls in by_sc.items():
        fig, axs = plt.subplots(4, 1, figsize=(4.6, 6.4), sharex=True)
        for c in [c for c in ORDER if c in ctrls and c in show][::-1] + [c for c in ctrls if c not in ORDER]:
            tr = pd.read_csv(sorted(ctrls[c])[0])         # first seed
            kw = dict(color=color(c), label=LABEL.get(c, c), lw=2.0 if c == "td3" else 1.2)
            axs[0].plot(tr.t, tr.df_hz, **kw)
            axs[1].plot(tr.t, tr.rocof_hz_s, **kw)
            axs[2].plot(tr.t, tr.p_vsg_mw, **kw)
            if c not in ("none", "droop"):
                axs[3].plot(tr.t, tr.H_v, **kw)
        lim = cfg["system"]["grid_code"]
        axs[0].set_ylabel("Δf (Hz)")
        axs[1].set_ylabel("RoCoF (Hz/s)")
        axs[1].axhline(-lim["rocof_limit_hz_s"], color=MUTED, lw=0.8, ls="--")
        axs[1].axhline(lim["rocof_limit_hz_s"], color=MUTED, lw=0.8, ls="--")
        axs[2].set_ylabel("VSG power (MW)")
        axs[3].set_ylabel("Virtual inertia H (s)")
        axs[3].set_xlabel("Time (s)")
        if "none" in ctrls:   # diesel-only usually collapses: zoom on the supported responses
            dev = max(pd.read_csv(sorted(ctrls[c])[0]).df_hz.abs().max() for c in ctrls if c != "none")
            axs[0].set_ylim(-1.3 * dev, 1.3 * dev)
            axs[1].set_ylim(-3 * lim["rocof_limit_hz_s"], 3 * lim["rocof_limit_hz_s"])
        h, l = axs[0].get_legend_handles_labels()
        fig.tight_layout(rect=(0, 0, 1, 0.88))
        fig.legend(h, l, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.0), fontsize=7)
        axs[0].set_title(f"Test scenario {k}", loc="left")
        save(fig, out, f"fig_response_sc{k}")


def boxes(cfg, out):
    f = resolve_path(cfg["eval"]["out_dir"]) / "per_scenario.csv"
    if not f.exists():
        return
    df = pd.read_csv(f)
    df = df[df.controller != "none"]
    per = df.groupby(["controller", "scenario"]).mean(numeric_only=True).reset_index()
    ctrls = [c for c in ORDER if c in per.controller.unique()] + \
            [c for c in per.controller.unique() if c not in ORDER]
    mets = [("nadir_hz", "Max |Δf| (Hz)"), ("rocof_max_hz_s", "Max RoCoF (Hz/s)"),
            ("bess_energy_kwh", "BESS energy (kWh)")]
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6))
    for ax, (m, lab) in zip(axs, mets):
        data = [per[per.controller == c][m].to_numpy() for c in ctrls]
        bp = ax.boxplot(data, patch_artist=True, widths=0.6, showfliers=False,
                        medianprops=dict(color=INK, lw=1.2))
        for patch, c in zip(bp["boxes"], ctrls):
            patch.set_facecolor(color(c))
            patch.set_alpha(0.75)
            patch.set_edgecolor("white")
        ax.set_xticks(range(1, len(ctrls) + 1))
        ax.set_xticklabels([LABEL.get(c, c).replace(" (", "\n(") for c in ctrls], rotation=60, ha="right",
                           fontsize=7)
        ax.set_title(lab, loc="left")
    save(fig, out, "fig_metric_boxes")


def headroom_policy(cfg, out):
    f = resolve_path(cfg["eval"]["out_dir"]) / "per_scenario.csv"
    if not f.exists():
        return
    df = pd.read_csv(f)
    rl = [c for c in ("td3", "ddpg") if c in df.controller.unique()]
    if not rl:
        return
    S = cfg["system"]
    # Proxy for available upward headroom at t=0: BESS limit tapering + PV headroom
    b = S["bess"]
    dis = b["power_mw"] * np.clip((df.soc0 - b["soc_min"]) / b["soc_taper"], 0, 1)
    df["headroom_mw"] = dis + S["pv"]["deload_fraction"] * df.p_pv_mpp_mw
    fig, axs = plt.subplots(1, 2, figsize=(6.4, 2.6))
    for c in rl:
        g = df[df.controller == c].groupby("scenario").mean(numeric_only=True)
        axs[0].scatter(g.headroom_mw, g.mean_H, s=10, color=color(c), label=LABEL[c], alpha=0.8, linewidths=0)
        axs[1].scatter(g.headroom_mw, g.mean_D, s=10, color=color(c), label=LABEL[c], alpha=0.8, linewidths=0)
    axs[0].set_xlabel("Upward headroom at event (MW)")
    axs[1].set_xlabel("Upward headroom at event (MW)")
    axs[0].set_ylabel("Mean scheduled H (s)")
    axs[1].set_ylabel("Mean scheduled D (pu)")
    axs[0].legend()
    save(fig, out, "fig_headroom_policy")


def data_overview(cfg, out):
    df = load_processed(cfg)
    fig, axs = plt.subplots(3, 1, figsize=(6.4, 4.8), sharex=True)
    daily = df.drop(columns="split").resample("1D").mean()
    split = df["split"].resample("1D").agg(lambda s: s.mode().iat[0] if len(s) else None)
    for ax, col, lab in zip(axs, ["p_wind_mw", "p_pv_mpp_mw", "load_mw"],
                            ["Wind (ERA5) MW", "PV MPP (NASA POWER) MW", "Load MW"]):
        ax.plot(daily.index, daily[col], color=PALETTE[0], lw=1.0)
        ax.set_ylabel(lab)
    for sp, c in (("val", PALETTE[3]), ("test", PALETTE[1])):
        d = split[split == sp].index
        if len(d):
            for ax in axs:
                ax.axvspan(d.min(), d.max(), color=c, alpha=0.12, lw=0)
            axs[0].text(d.min(), axs[0].get_ylim()[1] * 0.92, f" {sp}", color=INK, fontsize=8)
    axs[0].set_title("Daily-mean operating points from the hybrid real-data set", loc="left")
    save(fig, out, "fig_data_overview")


if __name__ == "__main__":
    a = base_parser(__doc__).parse_args()
    cfg = setup(a)
    style()
    out = resolve_path(cfg["eval"]["out_dir"]) / "figures"
    out.mkdir(parents=True, exist_ok=True)
    data_overview(cfg, out)
    learning_curves(cfg, out)
    responses(cfg, out)
    boxes(cfg, out)
    headroom_policy(cfg, out)
