"""
Paper figures.  Every panel is drawn from the same rollouts / tables that
produce the reported numbers.

  figure2_generation_profiles   PV and wind models, seasonal profiles
  figure3_weather_scenarios     the five scenarios and the no-VSG response
  figure4_ddpg_training / figure5_td3_training
                                training curves (mean +/- sd over seeds),
                                learned parameters, critic calibration
  figure6_comparison            time-domain comparison, combined stress
  figure7_metrics               error integrals with 95 % CIs, the fixed-gain
                                Pareto frontier, held-out stress test
"""
import os
import re

import numpy as np

from . import config as C
from .baselines import FixedPolicy
from .env import MicrogridVSGEnv
from .models import SolarPV, WindTurbine
from .utils import log


def apply_plot_style() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": "#FFFFFF", "axes.facecolor": "#F7F8FA",
        "axes.edgecolor": "#B0B4BD", "axes.labelcolor": C.COLORS["text"],
        "axes.titlesize": 10.5, "axes.labelsize": 9.5,
        "xtick.color": "#4A4F5C", "ytick.color": "#4A4F5C",
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "grid.color": "#D8DBE2", "grid.linewidth": 0.6,
        "text.color": C.COLORS["text"], "legend.fontsize": 8,
        "legend.facecolor": "#FFFFFF", "legend.edgecolor": "#B0B4BD",
        "lines.linewidth": 1.8, "font.size": 10, "figure.dpi": 110,
        "savefig.dpi": 300, "savefig.bbox": "tight",
    })


apply_plot_style()
import matplotlib.pyplot as plt          # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402


def _fig_dir():
    d = os.path.join(C.OUT_DIR, "figures")
    os.makedirs(d, exist_ok=True)
    return d


def _panel_dir():
    d = os.path.join(_fig_dir(), "panels")
    os.makedirs(d, exist_ok=True)
    return d


SEASONS = ["summer", "winter", "spring", "autumn"]
SEASON_C = {"summer": "#E65100", "winter": "#1565C0",
            "spring": "#2E7D32", "autumn": "#8E24AA"}


def _panel_slug(title: str, maxlen: int = 44) -> str:
    """Filename-safe stub from a panel title, mathtext stripped."""
    t = title.replace("\u2014", "-").replace("\u2212", "-")
    t = re.sub(r"\$[^$]*\$", "", t)          # drop mathtext
    t = re.sub(r"^\s*\([a-z]\)\s*", "", t)   # drop the "(a) " prefix
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s-]+", "_", t.strip())
    return t.lower()[:maxlen].strip("_")


def save_panels(fig, prefix: str) -> list:
    """Write every panel of a composite figure as a standalone PNG.

    Each panel is saved by clipping the rendered figure to that axes'
    tight bounding box, so the panel is byte-identical in content to the
    composite version - no replotting, no risk of the two disagreeing.
    Twin axes (a left and right y-axis sharing one panel) are merged, and
    inset axes are folded into their parent rather than exported twice.
    """
    from matplotlib.transforms import Bbox

    os.makedirs(_panel_dir(), exist_ok=True)
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()

    # group axes that occupy the same rectangle -> twinx pairs
    groups = []
    for ax in fig.axes:
        pos = ax.get_position()
        key = (round(pos.x0, 4), round(pos.y0, 4),
               round(pos.x1, 4), round(pos.y1, 4))
        for g in groups:
            if g["key"] == key:
                g["axes"].append(ax)
                break
        else:
            groups.append(dict(key=key, axes=[ax]))

    # discard insets: a rectangle wholly contained in another one
    def _inside(a, b):
        return (a[0] >= b[0] - 1e-6 and a[1] >= b[1] - 1e-6
                and a[2] <= b[2] + 1e-6 and a[3] <= b[3] + 1e-6)

    groups = [g for g in groups
              if not any(h is not g and _inside(g["key"], h["key"])
                         for h in groups)]
    # reading order: top row first, then left to right
    groups.sort(key=lambda g: (-round(g["key"][3], 2), g["key"][0]))

    sup = getattr(fig, "_suptitle", None)
    paths, captions = [], []
    for i, g in enumerate(groups):
        title = next((ax.get_title() for ax in g["axes"] if ax.get_title()), "")
        bb = Bbox.union([ax.get_tightbbox(rend) for ax in g["axes"]])
        e = bb.transformed(fig.dpi_scale_trans.inverted())
        # additive padding in inches - expanded() scales about the centre
        # and clips long tick labels on wide panels
        e = Bbox.from_extents(e.x0 - 0.14, e.y0 - 0.12,
                              e.x1 + 0.12, e.y1 + 0.14)
        # Hide everything outside this panel before saving.  Padding alone
        # lets a neighbouring panel's axis label bleed into the crop, which
        # is how "Loss (log)" ended up inside the learned-parameters panel.
        hidden = [a for a in fig.axes if a not in g["axes"] and a.get_visible()]
        for a in hidden:
            a.set_visible(False)
        if sup is not None:
            sup.set_visible(False)
        num = i + 1
        stub = _panel_slug(title)
        name = f"{prefix}_{num}" + (f"_{stub}" if stub else "") + ".png"
        path = os.path.join(_panel_dir(), name)
        fig.savefig(path, bbox_inches=e, facecolor="white", dpi=300)
        for a in hidden:
            a.set_visible(True)
        if sup is not None:
            sup.set_visible(True)
        paths.append(path)
        captions.append((name, title or f"panel {num}"))

    # append to a running caption list for the manuscript
    try:
        idx = os.path.join(_panel_dir(), "CAPTIONS.md")
        first = not os.path.exists(idx)
        with open(idx, "a") as fh:
            if first:
                fh.write("# Individual result panels\n\n"
                         "One row per exported figure. Titles are taken from "
                         "the panel itself; edit into full captions for the "
                         "manuscript.\n")
            fh.write(f"\n## {prefix}\n\n| File | Panel title |\n|---|---|\n")
            for n, t in captions:
                fh.write(f"| `{n}` | {t} |\n")
    except OSError:
        pass
    return paths


def _save(fig, name: str) -> str:
    path = os.path.join(_fig_dir(), name)
    fig.savefig(path)
    if C.SAVE_PANELS:
        try:
            n = len(save_panels(fig, os.path.splitext(name)[0]))
            log(f"  saved {path}  (+{n} panels)")
        except Exception as exc:                       # noqa: BLE001
            log(f"  saved {path}  (panel export failed: {exc})")
    else:
        log(f"  saved {path}")
    plt.close(fig)
    return path


def _smooth(x, w=20):
    x = np.asarray(x, dtype=float)
    if len(x) < 2:
        return x
    w = max(1, min(w, len(x)))
    k = np.ones(w) / w
    pad = np.concatenate([np.full(w - 1, x[0]), x])
    return np.convolve(pad, k, mode="valid")


# ================================================================
# FIGURE 1 — generation profiles
# ================================================================
def figure2_generation() -> str:
    pv, wt = SolarPV(), WindTurbine()
    hours = np.linspace(0, 24, 480)
    fig = plt.figure(figsize=(15, 10))
    gs = GridSpec(3, 3, figure=fig, hspace=0.42, wspace=0.28)
    fig.suptitle("Figure 2 — Generation profiles: 500 kW solar PV + 500 kW wind\n"
                 "Nakhon Ratchasima microgrid, seasonal variation",
                 fontsize=13, fontweight="bold")

    ax = fig.add_subplot(gs[0, 0])
    for s in SEASONS:
        p = [pv.power(pv.daily_irradiance(h, s), pv.daily_temperature(h, s)) / 1e3
             for h in hours]
        ax.plot(hours, p, color=SEASON_C[s], label=s)
    ax.axhline(C.PV_RATED / 1e3, ls=":", color=C.COLORS["dim"])
    ax.set(title="Seasonal PV generation", xlabel="Hour of day",
           ylabel="PV power (kW)", xlim=(0, 24))
    ax.legend(); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[0, 1])
    for s in SEASONS:
        p = [wt.power_static(wt.daily_wind_speed(h, s)) / 1e3 for h in hours]
        ax.plot(hours, p, color=SEASON_C[s], label=s)
    ax.axhline(C.WT_RATED / 1e3, ls=":", color=C.COLORS["dim"])
    ax.set(title="Seasonal wind generation", xlabel="Hour of day",
           ylabel="Wind power (kW)", xlim=(0, 24))
    ax.legend(); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[0, 2])
    ppv = np.array([pv.power(pv.daily_irradiance(h, "summer"),
                             pv.daily_temperature(h, "summer")) / 1e3 for h in hours])
    pw = np.array([wt.power_static(wt.daily_wind_speed(h, "summer")) / 1e3
                   for h in hours])
    pb = np.clip(C.P_LOAD_NOM / 1e3 - ppv - pw, 0, None)
    ax.stackplot(hours, ppv, pw, pb,
                 colors=[C.COLORS["solar"], C.COLORS["wind"], C.COLORS["bess"]],
                 labels=["Solar", "Wind", "BESS"], alpha=.85)
    ax.axhline(C.P_LOAD_NOM / 1e3, ls="--", color=C.COLORS["load"], label="Load 1800 kW")
    ax.set(title="Summer generation stack", xlabel="Hour of day",
           ylabel="Power (kW)", xlim=(0, 24))
    ax.legend(loc="upper right"); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[1, 0])
    G = np.linspace(0, 1100, 300)
    for T, ls in [(25, "-"), (40, "--")]:
        ax.plot(G, [pv.power(g, T) / 1e3 for g in G], ls,
                color=C.COLORS["solar"], label=f"T_amb = {T} °C")
    ax.set(title="PV output vs irradiance (NOCT cell heating)",
           xlabel="Irradiance (W/m²)", ylabel="PV power (kW)")
    ax.legend(); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[1, 1])
    v = np.linspace(0, 26, 400)
    ax.plot(v, [wt.power_static(x) / 1e3 for x in v], color=C.COLORS["wind"])
    for x, lab in [(wt.v_in, "cut-in"), (wt.v_rated, "rated"), (wt.v_out, "cut-out")]:
        ax.axvline(x, ls=":", color=C.COLORS["dim"])
        ax.text(x, 520, lab, rotation=90, fontsize=7, va="bottom", ha="right")
    ax.set(title=f"Wind power curve (R = {wt.R:.1f} m)",
           xlabel="Wind speed (m/s)", ylabel="Wind power (kW)", ylim=(0, 600))
    ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[1, 2])
    lam = np.linspace(0.5, 14, 400)
    for beta, c in [(0, C.COLORS["wind"]), (5, C.COLORS["J"]), (10, C.COLORS["D"])]:
        ax.plot(lam, [wt.cp(l, beta) for l in lam], color=c, label=f"β = {beta}°")
    ax.plot(wt.lambda_opt, wt.cp_max, "o", color=C.COLORS["limit"])
    ax.annotate(f"λ_opt = {wt.lambda_opt:.2f}\nCp = {wt.cp_max:.3f}",
                (wt.lambda_opt, wt.cp_max), textcoords="offset points",
                xytext=(8, -22), fontsize=8)
    ax.set(title="Power coefficient Cp(λ, β)", xlabel="Tip-speed ratio λ",
           ylabel="Cp")
    ax.legend(); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[2, 0])
    ax.plot(hours, [pv.daily_irradiance(h, "summer") for h in hours],
            color=C.COLORS["solar"], label="Irradiance")
    ax.set(title="Weather drivers — summer day", xlabel="Hour of day",
           ylabel="Irradiance (W/m²)")
    ax2 = ax.twinx()
    ax2.plot(hours, [wt.daily_wind_speed(h, "summer") for h in hours],
             "--", color=C.COLORS["wind"], label="Wind speed")
    ax2.set_ylabel("Wind speed (m/s)")
    ax.grid(alpha=.4)
    ax.legend(loc="upper left"); ax2.legend(loc="upper right")

    ax = fig.add_subplot(gs[2, 1])
    x = np.arange(len(SEASONS))
    pv_avg = [np.mean([pv.power(pv.daily_irradiance(h, s),
                                pv.daily_temperature(h, s)) / 1e3 for h in hours])
              for s in SEASONS]
    w_avg = [np.mean([wt.power_static(wt.daily_wind_speed(h, s)) / 1e3
                      for h in hours]) for s in SEASONS]
    ax.bar(x - .2, pv_avg, .4, color=C.COLORS["solar"], label="Solar PV")
    ax.bar(x + .2, w_avg, .4, color=C.COLORS["wind"], label="Wind")
    ax.set_xticks(x); ax.set_xticklabels(SEASONS)
    ax.set(title="Seasonal average generation", ylabel="Average power (kW)")
    ax.legend(); ax.grid(alpha=.4, axis="y")

    ax = fig.add_subplot(gs[2, 2])
    env = MicrogridVSGEnv(scenario="wind_drop")
    rec = env.rollout(FixedPolicy(4, 30), seed=3)
    ax.plot(rec["t"], rec["v_wind"], color=C.COLORS["wind"], label="Wind speed")
    ax.set(title="Rotor dynamics during a gust collapse",
           xlabel="Time (s)", ylabel="Wind speed (m/s)")
    ax2 = ax.twinx()
    ax2.plot(rec["t"], rec["P_wind"] / 1e3, color=C.COLORS["J"], label="Wind power")
    ax2.set_ylabel("Wind power (kW)")
    ax.grid(alpha=.4)
    ax.legend(loc="upper right", fontsize=7)
    ax2.legend(loc="lower left", fontsize=7)
    return _save(fig, "figure2_generation_profiles.png")


# ================================================================
# FIGURE 2 — input scenarios and weather effect on frequency
# ================================================================
def figure3_scenarios() -> str:
    recs = {sc: MicrogridVSGEnv(scenario=sc).rollout(FixedPolicy(0, 0), seed=7)
            for sc in C.EVAL_SCENARIOS}

    fig = plt.figure(figsize=(15, 10))
    gs = GridSpec(3, 3, figure=fig, hspace=0.42, wspace=0.28)
    fig.suptitle("Figure 3 — Input scenarios and their effect on frequency\n"
                 "Five 30 s disturbance profiles, no VSG (J = D = 0)",
                 fontsize=13, fontweight="bold")

    panels = [
        ("irr", "Solar irradiance", "Irradiance (W/m²)", 1.0),
        ("v_wind", "Wind speed", "Wind speed (m/s)", 1.0),
        ("P_pv", "PV power", "PV power (kW)", 1e-3),
        ("P_wind", "Wind power", "Wind power (kW)", 1e-3),
    ]
    positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for (key, title, ylab, scale), pos in zip(panels, positions):
        ax = fig.add_subplot(gs[pos])
        for sc in C.EVAL_SCENARIOS:
            ax.plot(recs[sc]["t"], recs[sc][key] * scale,
                    color=C.SCENARIO_COLORS[sc], label=C.SCENARIO_LABELS[sc])
        ax.set(title=title, xlabel="Time (s)", ylabel=ylab)
        ax.grid(alpha=.4)
        if pos == (0, 0):
            ax.legend(fontsize=7)

    ax = fig.add_subplot(gs[0, 2])
    for sc in C.EVAL_SCENARIOS:
        r = recs[sc]
        ax.plot(r["t"], (r["P_pv"] + r["P_wind"]) / 1e3,
                color=C.SCENARIO_COLORS[sc], label=C.SCENARIO_LABELS[sc])
    ax.axhline(C.P_LOAD_NOM / 1e3, ls="--", color=C.COLORS["load"], label="Load 1800 kW")
    ax.set(title="Total renewable generation", xlabel="Time (s)",
           ylabel="Generation (kW)")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[1, 2])
    for sc in C.EVAL_SCENARIOS:
        ax.plot(recs[sc]["t"], recs[sc]["P_load"] / 1e3,
                color=C.SCENARIO_COLORS[sc], label=C.SCENARIO_LABELS[sc])
    for a, b in C.event_windows():
        ax.axvspan(a, b, color=C.COLORS["limit"], alpha=.10)
    ax.text(np.mean(C.event_windows()[0]), C.P_LOAD_NOM / 1e3 * 1.02,
            "contingency 1", ha="center", fontsize=7, color=C.COLORS["limit"])
    ax.text(np.mean(C.event_windows()[-1]), C.P_LOAD_NOM / 1e3 * 1.02,
            "contingency 2", ha="center", fontsize=7, color=C.COLORS["limit"])
    ax.set(title="Load contingency — two opposite-sign events",
           xlabel="Time (s)", ylabel="Load (kW)")
    ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[2, :2])
    for sc in C.EVAL_SCENARIOS:
        ax.plot(recs[sc]["t"], recs[sc]["f"], color=C.SCENARIO_COLORS[sc],
                label=f"{C.SCENARIO_LABELS[sc]} (nadir {recs[sc]['f'].min():.2f} Hz)")
    ax.axhline(C.F_NOM - C.F_BAND_OK, ls=":", color=C.COLORS["limit"])
    ax.axhline(C.F_NOM + C.F_BAND_OK, ls=":", color=C.COLORS["limit"])
    ax.axhline(C.F_NOM, ls="-", lw=.8, color=C.COLORS["dim"])
    ax.set(title="Frequency response with NO VSG — the case for adaptive inertia",
           xlabel="Time (s)", ylabel="Frequency (Hz)")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[2, 2])
    x = np.arange(len(C.EVAL_SCENARIOS))
    dev = [abs(recs[sc]["f"].min() - C.F_NOM) for sc in C.EVAL_SCENARIOS]
    roc = [np.abs(recs[sc]["rocof"]).max() for sc in C.EVAL_SCENARIOS]
    ax.bar(x - .2, dev, .4, color=C.COLORS["none"], label="|Δf| nadir (Hz)")
    ax.bar(x + .2, roc, .4, color=C.COLORS["rocof"], label="peak RoCoF (Hz/s)")
    ax.axhline(0.5, ls="--", color=C.COLORS["limit"], lw=1)
    ax.axhline(C.ROCOF_LIMIT, ls=":", color=C.COLORS["limit"], lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels([C.SCENARIO_LABELS[s].split()[0] for s in C.EVAL_SCENARIOS],
                       rotation=30, ha="right")
    ax.set(title="Severity without VSG")
    ax.legend(fontsize=7); ax.grid(alpha=.4, axis="y")
    return _save(fig, "figure3_weather_scenarios.png")


# ================================================================
# helpers for multi-seed figures
# ================================================================
RL = ("ddpg", "td3")


def _seed_band(ax, hists: dict, key: str, color, label, x_key=None, smooth=20):
    """Mean +/- sd over seeds of a per-episode (or per-eval) history series."""
    series = [np.asarray(h.get(key, []), dtype=float) for h in hists.values() if h.get(key)]
    if not series:
        return
    n = min(len(s) for s in series)
    arr = np.stack([_smooth(s[:n], smooth) if smooth > 1 else s[:n] for s in series])
    x = (np.asarray(list(hists.values())[0][x_key][:n]) if x_key else np.arange(1, n + 1))
    mu, sd = np.nanmean(arr, 0), np.nanstd(arr, 0)
    ax.plot(x, mu, color=color, label=f"{label} (n={len(series)})")
    if len(series) > 1:
        ax.fill_between(x, mu - sd, mu + sd, color=color, alpha=.18, lw=0)


def _shade_events(ax, rec):
    for a, b in rec.get("event_windows", C.event_windows()):
        ax.axvspan(a, b, color=C.COLORS["limit"], alpha=.08)


def _per_scenario(per_key, controller, metric):
    """Mean over seeds of a metric, per test scenario."""
    rows = [r for (c, s), r in per_key.items() if c == controller]
    return [float(np.mean([rr[i][metric] for rr in rows])) for i in range(len(C.EVAL_SCENARIOS))]


def _label(c):
    return C.CONTROLLER_LABELS.get(c, c)


# ================================================================
# FIGURES 4 & 5 -- per-algorithm training performance
# ================================================================
def figure_training(algo: str, hists: dict, recs: dict, fignum: int) -> str:
    c = C.COLORS[algo]
    fig = plt.figure(figsize=(15, 10))
    gs = GridSpec(3, 3, figure=fig, hspace=0.45, wspace=0.32)
    extra = ("clipped double Q-learning, target policy smoothing, delayed updates"
             if algo == "td3" else "single critic, prioritised replay, curriculum")
    fig.suptitle(f"Figure {fignum} — {algo.upper()} training performance "
                 f"(mean ± sd over {len(hists)} seeds)\n{extra}",
                 fontsize=13, fontweight="bold")

    ax = fig.add_subplot(gs[0, 0])
    _seed_band(ax, hists, "reward", c, "training return")
    ax.set(title="(a) Training return", xlabel="Episode", ylabel="Episode return")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[0, 1])
    _seed_band(ax, hists, "val_return", C.COLORS["limit"], "validation return",
               x_key="eval_ep", smooth=1)
    ax.set(title="(b) Validation return (model selection)", xlabel="Episode",
           ylabel="Mean return, 10 held-out episodes")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[0, 2])
    _seed_band(ax, hists, "nadir", c, "nadir")
    ax.axhline(C.F_NOM - C.F_BAND_OK, ls="--", color=C.COLORS["limit"], label="operational limit")
    ax.set(title="(c) Frequency nadir during training", xlabel="Episode", ylabel="Nadir (Hz)")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[1, 0])
    _seed_band(ax, hists, "J_mean", C.COLORS["J"], "mean J")
    ax.set(title="(d) Learned parameters", xlabel="Episode", ylabel="Virtual inertia J (s)")
    ax2 = ax.twinx()
    _seed_band(ax2, hists, "D_mean", C.COLORS["D"], "mean D")
    ax2.set_ylabel("Virtual damping D (pu)")
    ax.legend(loc="upper left", fontsize=7); ax2.legend(loc="upper right", fontsize=7)
    ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[1, 1])
    _seed_band(ax, hists, "rocof", C.COLORS["rocof"], "peak RoCoF")
    ax.axhline(C.ROCOF_LIMIT, ls="--", color=C.COLORS["limit"], label="2 Hz/s relay limit")
    ax.set(title="(e) Peak RoCoF during training", xlabel="Episode", ylabel="RoCoF (Hz/s)")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[1, 2])
    _seed_band(ax, hists, "mc_mean", "k", "Monte-Carlo return", x_key="eval_ep", smooth=1)
    _seed_band(ax, hists, "q_mean", C.COLORS["q1"], "critic Q1(s, μ(s))", x_key="eval_ep", smooth=1)
    if algo == "td3":
        _seed_band(ax, hists, "q_min_mean", C.COLORS["q2"], "min(Q1, Q2)", x_key="eval_ep", smooth=1)
    ax.set(title="(f) Critic calibration on validation states", xlabel="Episode",
           ylabel="Discounted return")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[2, 0:2])
    for n in ("none", "fixed_high", "fixed_tuned", "adaptive_rule"):
        if n in recs:
            r = recs[n]
            ax.plot(r["t"], r["f"], "--", lw=1.1, color=C.COLORS[n],
                    label=f"{_label(n)} (nadir {r['f'].min():.2f} Hz)")
    r = recs[algo]
    ax.plot(r["t"], r["f"], color=c, lw=2.2, label=f"{algo.upper()}-VSG (nadir {r['f'].min():.2f} Hz)")
    ax.axhline(C.F_NOM - C.F_BAND_OK, ls=":", color=C.COLORS["limit"])
    _shade_events(ax, r)
    ax.set(title="(g) Frequency response — combined stress (test scenario)",
           xlabel="Time (s)", ylabel="Frequency (Hz)")
    ax.legend(fontsize=7, ncol=2); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[2, 2])
    ax.plot(r["t"], r["J"], color=C.COLORS["J"], label="J")
    ax.set(title="(h) Adaptive J and D — combined stress", xlabel="Time (s)",
           ylabel="Virtual inertia J (s)")
    ax2 = ax.twinx()
    ax2.plot(r["t"], r["D"], color=C.COLORS["D"], label="D")
    ax2.set_ylabel("Virtual damping D (pu)")
    _shade_events(ax, r)
    ax.legend(loc="upper left", fontsize=7); ax2.legend(loc="upper right", fontsize=7)
    ax.grid(alpha=.4)
    return _save(fig, f"figure{fignum}_{algo}_training.png")


# ================================================================
# FIGURE 6 -- head-to-head comparison
# ================================================================
def figure_comparison(hists_by_algo: dict, recs: dict, per_key: dict, controllers) -> str:
    fig = plt.figure(figsize=(15, 10))
    gs = GridSpec(3, 3, figure=fig, hspace=0.5, wspace=0.32)
    fig.suptitle("Figure 6 — DDPG vs TD3 vs tuned non-learning controllers\n"
                 "training statistics over seeds; time traces for the median-validation seed",
                 fontsize=13, fontweight="bold")

    ax = fig.add_subplot(gs[0, 0])
    for a, h in hists_by_algo.items():
        _seed_band(ax, h, "reward", C.COLORS[a], a.upper())
    ax.set(title="(a) Training return", xlabel="Episode", ylabel="Smoothed return")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[0, 1])
    for a, h in hists_by_algo.items():
        _seed_band(ax, h, "val_return", C.COLORS[a], a.upper(), x_key="eval_ep", smooth=1)
    ax.set(title="(b) Validation return", xlabel="Episode", ylabel="Mean return")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[0, 2])
    for a, h in hists_by_algo.items():
        _seed_band(ax, h, "q_bias", C.COLORS[a], f"{a.upper()} Q1 − G", x_key="eval_ep", smooth=1)
        if a == "td3":
            _seed_band(ax, h, "q_min_bias", C.COLORS["q2"], "TD3 min(Q1,Q2) − G",
                       x_key="eval_ep", smooth=1)
    ax.axhline(0, color="k", lw=.8)
    ax.set(title="(c) Critic bias vs Monte-Carlo return", xlabel="Episode", ylabel="Bias")
    ax.legend(fontsize=7); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[1, 0:2])
    for n in controllers:
        if n not in recs:
            continue
        r = recs[n]
        rl = n in RL
        ax.plot(r["t"], r["f"], "-" if rl else "--", lw=2.0 if rl else 1.1,
                color=C.COLORS[n], label=f"{_label(n)} ({r['f'].min():.2f} Hz)")
    ax.axhline(C.F_NOM - C.F_BAND_OK, ls=":", color=C.COLORS["limit"])
    _shade_events(ax, recs[controllers[0]])
    ax.set(title="(d) Frequency — combined stress", xlabel="Time (s)", ylabel="Frequency (Hz)")
    ax.legend(fontsize=7, ncol=2); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[1, 2])
    for n in controllers:
        if n in recs:
            ax.plot(recs[n]["t"], recs[n]["rocof"], lw=1.8 if n in RL else 1.0,
                    color=C.COLORS[n], label=_label(n))
    for s in (1, -1):
        ax.axhline(s * C.ROCOF_LIMIT, ls="--", color=C.COLORS["limit"])
    ax.set(title="(e) RoCoF, 500 ms window", xlabel="Time (s)", ylabel="RoCoF (Hz/s)")
    ax.grid(alpha=.4)

    x = np.arange(len(C.EVAL_SCENARIOS))
    w = 0.8 / len(controllers)
    for col, (metric, title, ylab, lim) in enumerate([
            ("df_max_hz", "(f) Peak |Δf| by scenario", "|Δf| (Hz)", C.F_BAND_OK),
            ("rocof_win", "(g) Peak RoCoF by scenario", "RoCoF (Hz/s)", C.ROCOF_LIMIT)]):
        ax = fig.add_subplot(gs[2, col])
        for i, n in enumerate(controllers):
            ax.bar(x + (i - len(controllers) / 2 + .5) * w, _per_scenario(per_key, n, metric),
                   w, color=C.COLORS[n], label=_label(n))
        ax.axhline(lim, ls="--", color=C.COLORS["limit"])
        ax.set_xticks(x)
        ax.set_xticklabels([C.SCENARIO_LABELS[s].split()[0] for s in C.EVAL_SCENARIOS],
                           rotation=30, ha="right")
        ax.set(title=title, ylabel=ylab)
        ax.grid(alpha=.4, axis="y")
        if col == 0:
            ax.legend(fontsize=6)

    ax = fig.add_subplot(gs[2, 2])
    for n in controllers:
        if n in recs:
            ax.plot(recs[n]["t"], recs[n]["V"], lw=1.8 if n in RL else 1.0, color=C.COLORS[n])
    ax.set(title="(h) PCC voltage — combined stress", xlabel="Time (s)", ylabel="V (pu)")
    ax.grid(alpha=.4)
    return _save(fig, "figure6_comparison.png")


# ================================================================
# FIGURE 7 -- metrics, Pareto frontier, held-out stress test
# ================================================================
def _pareto(points):
    """Lower-left frontier of (reserve, iae) points."""
    pts = sorted(points)
    front, best = [], np.inf
    for r, e in pts:
        if e < best:
            front.append((r, e))
            best = e
    return np.array(front)


def figure_metrics(agg: dict, per_key: dict, grid: list, stress_rows: dict,
                   recs: dict, controllers) -> str:
    names = [c for c in controllers if c in agg]
    x = np.arange(len(names))
    fig = plt.figure(figsize=(15, 11))
    gs = GridSpec(3, 3, figure=fig, hspace=0.6, wspace=0.32)
    fig.suptitle("Figure 7 — Optimization metrics on the five test scenarios "
                 "(RL: mean ± 95 % CI over seeds)\n"
                 "with the fixed-gain Pareto frontier and the held-out stress test",
                 fontsize=13, fontweight="bold")
    panels = [("settle_s", "(a) Recovery settling (±0.05 Hz)", "s"),
              ("overshoot_pct", "(b) Overshoot after contingency 1", "% of nadir depth"),
              ("iae", "(c) IAE ∫|Δf|dt", "Hz·s"),
              ("ise", "(d) ISE ∫Δf²dt", "Hz²·s"),
              ("itae", "(e) ITAE ∫t|Δf|dt", "Hz·s²"),
              ("reserve_pu", "(f) Delivered headroom commitment", "pu of 2500 kVA")]
    for i, (k, title, ylab) in enumerate(panels):
        ax = fig.add_subplot(gs[i // 3, i % 3])
        mu = [agg[n][k][0] for n in names]
        ci = [agg[n][k][2] if agg[n][k][3] > 1 else 0.0 for n in names]
        bars = ax.bar(x, mu, yerr=ci, capsize=3, color=[C.COLORS[n] for n in names])
        for b, v in zip(bars, mu):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f"{v:.3g}",
                    ha="center", va="bottom", fontsize=6.5)
        ax.set_xticks(x)
        ax.set_xticklabels([_label(n) for n in names], rotation=35, ha="right", fontsize=7)
        ax.set(title=title, ylabel=ylab)
        ax.grid(alpha=.4, axis="y")

    ax = fig.add_subplot(gs[2, 0])
    if grid:
        g = np.array([(p["reserve_pu"], p["iae"]) for p in grid])
        ax.scatter(g[:, 0], g[:, 1], s=14, color="#BDBDBD", label="fixed (J, D) grid")
        fr = _pareto([tuple(p) for p in g])
        ax.plot(fr[:, 0], fr[:, 1], "-", color=C.COLORS["dim"], lw=1.2,
                label="fixed-gain Pareto frontier")
    for n in names:
        pts = [(np.mean([r["reserve_pu"] for r in rows]), np.mean([r["iae"] for r in rows]))
               for (c, s), rows in per_key.items() if c == n]
        pts = np.array(pts)
        if n in RL:
            ax.scatter(pts[:, 0], pts[:, 1], s=14, color=C.COLORS[n], alpha=.5)
        ax.scatter(pts[:, 0].mean(), pts[:, 1].mean(), s=90, color=C.COLORS[n],
                   edgecolor="w", zorder=3, label=_label(n))
    ax.set(title="(g) Regulation vs headroom (lower-left is better)",
           xlabel="Delivered headroom (pu)", ylabel="IAE (Hz·s)")
    ax.legend(fontsize=6); ax.grid(alpha=.4)

    ax = fig.add_subplot(gs[2, 1])
    data = [np.concatenate([[r["iae"] for r in rows] for (c, s), rows in stress_rows.items()
                            if c == n]) for n in names]
    bp = ax.boxplot(data, patch_artist=True, showfliers=False)
    for patch, n in zip(bp["boxes"], names):
        patch.set_facecolor(C.COLORS[n]); patch.set_alpha(.7)
    ax.set_xticks(np.arange(1, len(names) + 1))
    ax.set_xticklabels([_label(n) for n in names], rotation=35, ha="right", fontsize=7)
    ax.set(title=f"(h) Held-out stress test: IAE ({C.N_STRESS} episodes)", ylabel="IAE (Hz·s)")
    ax.grid(alpha=.4, axis="y")

    ax = fig.add_subplot(gs[2, 2])
    for n in [c for c in names if c in RL] + ["fixed_tuned", "fixed_high"]:
        if n in recs:
            ax.plot(recs[n]["t"], recs[n]["P_vsg"] / 1e3, lw=1.8 if n in RL else 1.0,
                    ls="-" if n in RL else "--", color=C.COLORS[n], label=_label(n))
    if names:
        _shade_events(ax, recs[names[0]])
    ax.set(title="(i) VSG power injection — combined stress", xlabel="Time (s)",
           ylabel="P_vsg (kW)")
    ax.legend(fontsize=7); ax.grid(alpha=.4)
    return _save(fig, "figure7_metrics.png")
