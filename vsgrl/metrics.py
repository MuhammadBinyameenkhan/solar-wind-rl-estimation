"""Frequency-response metrics computed from an episode trace (one row per 10 ms)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _infeasible_s(tr: pd.DataFrame, cfg: dict, dt: float) -> float:
    if "headroom_mw" not in tr:
        return float("nan")
    s = cfg["system"]
    f0, sb = s["f_nominal_hz"], s["s_base_mva"]
    band = (cfg["env"]["reward"].get("f_band_hz") or s["grid_code"]["f_target_hz"]) / f0
    rocof = s["grid_code"]["rocof_limit_hz_s"] / f0
    h = tr["headroom_mw"].to_numpy() / sb
    need = np.maximum(tr["D_v"].to_numpy() * band, 2.0 * tr["H_v"].to_numpy() * rocof)
    return float(np.sum(need > h + 1e-6) * dt)


def episode_metrics(tr: pd.DataFrame, sc: dict, cfg: dict) -> dict:
    """Metrics over all events of the episode. Per event (window = event time → next event):
    nadir in the event's direction and settling time; aggregated as worst / mean."""
    from .microgrid import Scenario
    gc = cfg["system"]["grid_code"]
    band_hz = cfg["env"]["reward"].get("f_band_hz", 0.0) or gc["settling_band_hz"]
    t = tr["t"].to_numpy()
    df = tr["df_hz"].to_numpy()
    dt = float(np.median(np.diff(t))) if len(t) > 1 else cfg["env"]["sim_dt_s"]
    events = Scenario(**{k: sc[k] for k in Scenario.__dataclass_fields__ if k in sc}).event_list()

    w = max(int(round(gc["rocof_window_s"] / dt)), 1)
    rocof_w = (df[w:] - df[:-w]) / (w * dt) if len(df) > w else np.array([0.0])

    nadirs, settles, t_nad = [], [], []
    for i, (t_e, mw) in enumerate(events):
        t_end = events[i + 1][0] if i + 1 < len(events) else t[-1] + dt
        win = (t >= t_e) & (t < t_end)
        if not win.any():
            continue
        sign = 1.0 if mw >= 0 else -1.0
        dev = -sign * df[win]
        k = int(np.argmax(dev))
        nadirs.append(float(dev[k]))
        t_nad.append(float(t[win][k] - t_e))
        tw, fw = t[win], df[win]
        final = float(np.mean(fw[tw >= tw[-1] - 1.0]))
        out = np.where(np.abs(fw - final) > gc["settling_band_hz"])[0]
        settles.append(float(tw[out[-1]] - t_e) if len(out) else 0.0)

    p_b = tr["p_bess_mw"].to_numpy()
    p_pv = tr["p_pv_support_mw"].to_numpy()
    return {
        "nadir_hz": max(nadirs) if nadirs else 0.0,                 # worst event
        "mean_nadir_hz": float(np.mean(nadirs)) if nadirs else 0.0,
        "t_nadir_s": t_nad[int(np.argmax(nadirs))] if nadirs else 0.0,
        "rocof_max_hz_s": float(np.max(np.abs(rocof_w))),
        "qss_dev_hz": abs(float(np.mean(df[t >= t[-1] - 1.0]))),
        "settling_time_s": float(np.mean(settles)) if settles else 0.0,
        "time_outside_band_s": float(np.sum(np.abs(df) > band_hz) * dt),
        "n_events": len(events),
        "bess_energy_kwh": float(np.sum(np.abs(p_b - p_b[0])) * dt * 1000 / 3600),
        "bess_peak_mw": float(np.max(np.abs(p_b - p_b[0]))),
        "bess_rms_mw": float(np.sqrt(np.mean((p_b - p_b[0]) ** 2))),
        "pv_headroom_energy_kwh": float(np.sum(np.abs(p_pv)) * dt * 1000 / 3600),
        # VSG power above its secondary set-point = the inertial + damping response H and D control
        "vsg_fast_energy_kwh": float(np.sum(np.abs(tr["p_vsg_mw"].to_numpy() - tr["p_set_mw"].to_numpy()))
                                     * dt * 1000 / 3600) if "p_set_mw" in tr else float("nan"),
        "saturation_s": float(np.sum(tr["sat_mw"].to_numpy() > 1e-4) * dt),
        # Infeasible commitment: the scheduled D (damping power at the band edge) or H (inertial
        # power at the RoCoF limit) needs more power than the direction-aware headroom.
        "infeasible_commit_s": _infeasible_s(tr, cfg, dt),
        "soc_drop": float(tr["soc"].iloc[0] - tr["soc"].iloc[-1]),
        "f_violation": bool(np.max(np.abs(df)) > gc["f_dev_limit_hz"]),
        "rocof_violation": bool(np.max(np.abs(rocof_w)) > gc["rocof_limit_hz_s"]),
        "mean_H": float(tr["H_v"].mean()), "mean_D": float(tr["D_v"].mean()),
        "mean_alpha": float(tr["alpha"].mean()),
    }


METRIC_COLUMNS = ["nadir_hz", "rocof_max_hz_s", "qss_dev_hz", "settling_time_s", "time_outside_band_s",
                  "bess_energy_kwh", "bess_rms_mw",
                  "bess_peak_mw", "pv_headroom_energy_kwh", "saturation_s", "infeasible_commit_s", "f_violation",
                  "rocof_violation", "return", "collapsed"]
