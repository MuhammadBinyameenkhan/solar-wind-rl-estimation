"""Reader for NASA POWER hourly CSV files (power.larc.nasa.gov).

The standard download has a text header between `-BEGIN HEADER-` and
`-END HEADER-`, then columns like
    YEAR,MO,DY,HR,ALLSKY_SFC_SW_DWN,T2M,WS10M     (or YEAR,DOY,HR,...)
Missing values are -999. Hourly ALLSKY_SFC_SW_DWN is the hourly mean
irradiance (Wh/m^2 per hour == W/m^2).

The time standard (UTC or LST) is read from the header ("... in LST").
LST is converted to UTC with `utc_offset_hours` (or longitude/15).
"""
from __future__ import annotations

import io
import logging
import re

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

GHI_NAMES = ["ALLSKY_SFC_SW_DWN", "GHI", "ghi", "irradiance", "SWGDN"]
T2M_NAMES = ["T2M", "t2m", "temperature", "T2M_C"]
WS_NAMES = ["WS10M", "WS2M", "WS50M"]


def _split_header(text: str) -> tuple[str, str]:
    if "-END HEADER-" in text:
        head, body = text.split("-END HEADER-", 1)
        return head, body.lstrip("\r\n")
    return "", text


def parse_header(head: str) -> dict:
    meta = {}
    m = re.search(r"\bin\s+(LST|UTC)\b", head)
    if m:
        meta["time_standard"] = m.group(1)
    m = re.search(r"Latitude\s+(-?\d+\.?\d*)\s+Longitude\s+(-?\d+\.?\d*)", head)
    if m:
        meta["latitude"], meta["longitude"] = float(m.group(1)), float(m.group(2))
    m = re.search(r"Elevation.*?=\s*(-?\d+\.?\d*)\s*meters", head)
    if m:
        meta["elevation_m"] = float(m.group(1))
    return meta


def _pick(df, names, override):
    if override:
        return override
    for n in names:
        if n in df.columns:
            return n
    return None


def load_nasa_power_csv(path, overrides: dict | None = None, time_standard: str = "auto",
                        utc_offset_hours: float | None = None) -> pd.DataFrame:
    """Return an hourly UTC-indexed frame with columns ghi_wm2, t2m_c (and ws10m_ms if present)."""
    overrides = overrides or {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    head, body = _split_header(text)
    meta = parse_header(head)
    df = pd.read_csv(io.StringIO(body))
    df.columns = [c.strip() for c in df.columns]
    df = df.replace([-999, -999.0, -99, -99.0], np.nan)

    if {"YEAR", "MO", "DY", "HR"} <= set(df.columns):
        t = pd.to_datetime(dict(year=df.YEAR, month=df.MO, day=df.DY, hour=df.HR))
    elif {"YEAR", "DOY", "HR"} <= set(df.columns):
        t = (pd.to_datetime(df.YEAR.astype(str) + "-01-01") + pd.to_timedelta(df.DOY - 1, unit="D")
             + pd.to_timedelta(df.HR, unit="h"))
    elif {"YEAR", "MO", "DY"} <= set(df.columns) or {"YEAR", "DOY"} <= set(df.columns):
        raise ValueError("This NASA POWER file is DAILY. Download the HOURLY product "
                         "(temporal average = Hourly); frequency dynamics need hourly resource data.")
    else:
        tcol = _pick(df, ["time", "datetime", "date", "timestamp"], overrides.get("time"))
        if tcol is None:
            raise KeyError(f"Cannot find time columns in {path}: {list(df.columns)}")
        t = pd.to_datetime(df[tcol])

    t = pd.DatetimeIndex(t)
    std = time_standard if time_standard != "auto" else meta.get("time_standard", "UTC")
    if t.tz is None:
        if std.upper() == "LST":
            off = utc_offset_hours
            if off is None:
                if "longitude" not in meta:
                    raise ValueError("NASA POWER file is in LST but no longitude in header; "
                                     "set data.nasa_utc_offset_hours.")
                off = meta["longitude"] / 15.0
            log.info("NASA POWER: converting LST to UTC with offset %+.2f h", off)
            t = t - pd.to_timedelta(off, unit="h")
        t = t.tz_localize("UTC")
    else:
        t = t.tz_convert("UTC")

    ghi_col = _pick(df, GHI_NAMES, overrides.get("ghi"))
    if ghi_col is None:
        raise KeyError(f"No irradiance column (ALLSKY_SFC_SW_DWN) in {path}: {list(df.columns)}")
    out = pd.DataFrame(index=pd.DatetimeIndex(t, name="time_utc"))
    ghi = df[ghi_col].to_numpy(float)
    if np.nanmax(ghi) < 2.0:  # kW/m^2 or kWh/m^2/h
        log.info("NASA POWER irradiance looks like kW/m^2; converting to W/m^2.")
        ghi = ghi * 1000.0
    out["ghi_wm2"] = np.clip(ghi, 0.0, None)
    t2m_col = _pick(df, T2M_NAMES, overrides.get("t2m"))
    out["t2m_c"] = df[t2m_col].to_numpy(float) if t2m_col else 25.0
    ws_col = _pick(df, WS_NAMES, overrides.get("ws10m"))
    if ws_col:
        out["ws10m_ms"] = df[ws_col].to_numpy(float)

    out = out[~out.index.duplicated(keep="first")].sort_index()
    out = out.resample("1h").mean()
    out["ghi_wm2"] = out["ghi_wm2"].interpolate(limit=3).fillna(0.0)
    out["t2m_c"] = out["t2m_c"].interpolate(limit=24)
    out.attrs.update(meta)
    return out
