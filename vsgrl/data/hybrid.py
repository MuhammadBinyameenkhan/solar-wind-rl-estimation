"""Hybrid dataset: ERA5 wind + air density, NASA POWER irradiance + ambient
temperature, merged on an hourly UTC index, converted to available power and
split chronologically into train / val / test."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..components.resources import WindPowerCurve, pv_power_mw, synthetic_load_mw
from ..config import resolve_path
from .era5 import load_era5_csv
from .nasa_power import load_nasa_power_csv

log = logging.getLogger(__name__)

COLUMNS = ["ws_hub_ms", "rho_kgm3", "ghi_wm2", "t2m_c", "p_wind_mw", "p_pv_mpp_mw", "load_mw", "split"]


def wind_curve_from_cfg(cfg) -> WindPowerCurve:
    w = cfg["system"]["wind"]
    return WindPowerCurve(w["rated_mw"], w["cut_in_ms"], w["rated_speed_ms"], w["cut_out_ms"],
                          resolve_path(w.get("power_curve_csv")))


def assign_split(index: pd.DatetimeIndex, split_cfg: dict) -> np.ndarray:
    n = len(index)
    lab = np.empty(n, dtype=object)
    if split_cfg.get("method", "chronological") == "by_year":
        years = index.year
        lab[:] = "train"
        lab[np.isin(years, split_cfg.get("val_years", []))] = "val"
        lab[np.isin(years, split_cfg.get("test_years", []))] = "test"
        return lab
    # Chronological split on whole days (no day spans two splits).
    days = index.normalize()
    udays = days.unique()
    n_tr = int(round(len(udays) * split_cfg["train"]))
    n_va = int(round(len(udays) * split_cfg["val"]))
    d_tr, d_va = udays[:n_tr], udays[n_tr:n_tr + n_va]
    lab[:] = "test"
    lab[days.isin(d_va)] = "val"
    lab[days.isin(d_tr)] = "train"
    return lab


def build_hybrid_dataset(cfg) -> pd.DataFrame:
    d, s = cfg["data"], cfg["system"]
    era5 = load_era5_csv(resolve_path(d["era5_csv"]), d.get("era5_columns") or {},
                         cfg["site"].get("latitude"), cfg["site"].get("longitude"),
                         s["wind"]["hub_height_m"], s["wind"]["shear_exponent"])
    nasa = load_nasa_power_csv(resolve_path(d["nasa_power_csv"]), d.get("nasa_columns") or {},
                               d.get("nasa_time_standard", "auto"), d.get("nasa_utc_offset_hours"))

    df = era5[["ws_hub_ms", "rho_kgm3"]].join(nasa[["ghi_wm2", "t2m_c"]], how="inner")
    log.info("ERA5 %s → %s (%d h); NASA POWER %s → %s (%d h); overlap %d h",
             era5.index.min(), era5.index.max(), len(era5),
             nasa.index.min(), nasa.index.max(), len(nasa), len(df))
    if len(df) < 24 * 7:
        raise ValueError(f"Only {len(df)} overlapping hours between ERA5 and NASA POWER — "
                         "check that both files cover the same period and time zones.")
    df = df.dropna()

    curve = wind_curve_from_cfg(cfg)
    df["p_wind_mw"] = curve(df["ws_hub_ms"].to_numpy(), df["rho_kgm3"].to_numpy())
    pv = s["pv"]
    df["p_pv_mpp_mw"] = pv_power_mw(df["ghi_wm2"], df["t2m_c"], pv["rated_mw"], pv["temp_coeff_per_c"],
                                    pv["noct_c"], pv["derate"])

    if d.get("load_csv"):
        ld = pd.read_csv(resolve_path(d["load_csv"]))
        tcol = [c for c in ld.columns if c.lower() in ("time", "time_utc", "datetime", "timestamp")][0]
        ld.index = pd.to_datetime(ld[tcol], utc=True)
        df["load_mw"] = ld["load_mw"].resample("1h").mean().reindex(df.index).interpolate(limit=6)
        df = df.dropna()
    else:
        lon = nasa.attrs.get("longitude", cfg["site"].get("longitude")) or 0.0
        df["load_mw"] = synthetic_load_mw(df.index, s["load"]["peak_mw"], s["load"]["min_mw"],
                                          utc_offset_h=lon / 15.0, seed=0)
    df["split"] = assign_split(df.index, d["split"])
    return df[COLUMNS]


def load_processed(cfg) -> pd.DataFrame:
    """Load the processed hourly dataset, building it from the raw CSVs if missing."""
    path = resolve_path(cfg["data"]["processed_csv"])
    if path.exists():
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        return df
    df = build_hybrid_dataset(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)
    return df


def summarize(df: pd.DataFrame, cfg) -> pd.DataFrame:
    s = cfg["system"]
    rows = []
    for name, g in [("all", df)] + list(df.groupby("split")):
        rows.append({
            "split": name, "hours": len(g), "start": g.index.min(), "end": g.index.max(),
            "mean_ws_hub_ms": g.ws_hub_ms.mean(),
            "wind_cf": g.p_wind_mw.mean() / s["wind"]["rated_mw"],
            "pv_cf": g.p_pv_mpp_mw.mean() / s["pv"]["rated_mw"],
            "mean_ghi_wm2": g.ghi_wm2.mean(), "mean_load_mw": g.load_mw.mean(),
            "res_share": ((g.p_wind_mw + g.p_pv_mpp_mw).clip(upper=g.load_mw)).sum() / g.load_mw.sum(),
        })
    return pd.DataFrame(rows)
