"""Hybrid dataset: ERA5 wind + air density, NASA POWER irradiance + ambient
temperature, merged on an hourly UTC index, converted to available power and
split chronologically into train / val / test."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..components.resources import WindPowerCurve, pv_power_mw, synthetic_load_mw
from ..config import resolve_path
from .era5 import load_era5
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
    method = split_cfg.get("method", "chronological")
    if method == "weekly_blocks":
        # Whole ISO-style weeks assigned cyclically (5 train, 1 val, 1 test of every 7 weeks):
        # every season appears in every split, and one-week blocks limit autocorrelation leakage.
        pattern = split_cfg.get("pattern", ["train"] * 5 + ["val", "test"])
        week = ((index - index[0].normalize()).days // 7).to_numpy()
        return np.array([pattern[w % len(pattern)] for w in week], dtype=object)
    if method == "by_year":
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
    nasa = load_nasa_power_csv(resolve_path(d["nasa_power_csv"]), d.get("nasa_columns") or {},
                               d.get("nasa_time_standard", "auto"), d.get("nasa_utc_offset_hours"))
    lat = cfg["site"].get("latitude") or nasa.attrs.get("latitude")
    lon = cfg["site"].get("longitude") or nasa.attrs.get("longitude")
    era5 = load_era5(resolve_path(d["era5_csv"]), d.get("era5_columns") or {}, lat, lon,
                     s["wind"]["hub_height_m"], s["wind"]["shear_exponent"])

    df = era5[["ws_hub_ms", "rho_kgm3"]].join(nasa[["ghi_wm2", "t2m_c"]], how="inner")
    if df["rho_kgm3"].isna().all():
        # ERA5 file without t2m/sp: air density from NASA POWER T2M and barometric pressure
        # at the site elevation (header of the POWER file, or site.elevation_m).
        elev = cfg["site"].get("elevation_m") or nasa.attrs.get("elevation_m") or 0.0
        p_pa = 101325.0 * (1.0 - 2.25577e-5 * elev) ** 5.25588
        df["rho_kgm3"] = p_pa / (287.05 * (df["t2m_c"] + 273.15))
        log.info("Air density from NASA T2M + standard-atmosphere pressure at %.0f m (%.0f Pa)", elev, p_pa)
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
        off = cfg["site"].get("utc_offset_hours")
        if off is None:
            off = (lon or 0.0) / 15.0
        df["load_mw"] = synthetic_load_mw(df.index, s["load"]["peak_mw"], s["load"]["min_mw"],
                                          utc_offset_h=off, seed=0)
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
