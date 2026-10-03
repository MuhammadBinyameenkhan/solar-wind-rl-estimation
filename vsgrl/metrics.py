"""Frequency-response metrics computed from an episode trace (one row per 10 ms)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def episode_metrics(tr: pd.DataFrame, sc: dict, cfg: dict) -> dict:
    gc = cfg["system"]["grid_code"]
    t = tr["t"].to_numpy()
    df = tr["df_hz"].to_numpy()
    dt = float(np.median(np.diff(t))) if len(t) > 1 else cfg["env"]["sim_dt_s"]
    t_d = sc["dist_time_s"]
    post = t >= t_d
    sign = 1.0 if sc["dist_mw"] >= 0 else -1.0       # under- (+) / over- (−) frequency event

    # RoCoF over a sliding window (as protection relays measure it)
    w = max(int(round(gc["rocof_window_s"] / dt)), 1)
    rocof_w = (df[w:] - df[:-w]) / (w * dt) if len(df) > w else np.array([0.0])
    dev = -sign * df                                 # positive = in the direction of the event
    k_nadir = int(np.argmax(np.where(post, dev, -np.inf)))
    final = float(np.mean(df[t >= t[-1] - 1.0]))

    band = gc["settling_band_hz"]
    outside = np.where(post & (np.abs(df - final) > band))[0]
    settle = float(t[outside[-1]] - t_d) if len(outside) else 0.0

    p_b = tr["p_bess_mw"].to_numpy()
    p_pv = tr["p_pv_support_mw"].to_numpy()
    return {
        "nadir_hz": float(dev[k_nadir]),                     # max deviation magnitude (Hz)
        "t_nadir_s": float(t[k_nadir] - t_d),
        "rocof_max_hz_s": float(np.max(np.abs(rocof_w))),
        "qss_dev_hz": abs(final),                            # quasi-steady deviation at episode end
        "settling_time_s": settle,
        "bess_energy_kwh": float(np.sum(np.abs(p_b - p_b[0])) * dt * 1000 / 3600),
        "bess_peak_mw": float(np.max(np.abs(p_b - p_b[0]))),
        "pv_headroom_energy_kwh": float(np.sum(np.abs(p_pv)) * dt * 1000 / 3600),
        "saturation_s": float(np.sum(tr["sat_mw"].to_numpy() > 1e-4) * dt),
        "soc_drop": float(tr["soc"].iloc[0] - tr["soc"].iloc[-1]),
        "f_violation": bool(np.max(np.abs(df)) > gc["f_dev_limit_hz"]),
        "rocof_violation": bool(np.max(np.abs(rocof_w)) > gc["rocof_limit_hz_s"]),
        "mean_H": float(tr["H_v"].mean()), "mean_D": float(tr["D_v"].mean()),
        "mean_alpha": float(tr["alpha"].mean()),
    }


METRIC_COLUMNS = ["nadir_hz", "rocof_max_hz_s", "qss_dev_hz", "settling_time_s", "bess_energy_kwh",
                  "bess_peak_mw", "pv_headroom_energy_kwh", "saturation_s", "f_violation",
                  "rocof_violation", "return", "collapsed"]
