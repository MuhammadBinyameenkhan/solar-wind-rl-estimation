"""Reader for ERA5 (single levels) wind/thermo data — NetCDF (.nc, as downloaded
from the CDS) or CSV.

NetCDF: variables u100/v100 (and optionally u10/v10, t2m, sp) on a lat/lon grid;
components are bilinearly interpolated to the site (nearest point if outside the grid).

Handles the common CSV layouts:
  * CDS "timeseries" download:      valid_time,u100,v100,u10,v10,t2m,sp,...
  * xarray `.to_dataframe().to_csv()`: time,latitude,longitude,u100,v100,t2m,sp
  * hand-processed:                   date,ws100 (or wind_speed_100m),t2m,sp

ERA5 conventions assumed (they are the CDS defaults):
  time in UTC, wind components in m/s, t2m in K, sp in Pa.
Temperatures that are clearly in °C (max < 100) and pressures in hPa (< 2000)
are converted automatically and reported.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

ALIASES = {
    "time": ["valid_time", "time", "date", "datetime", "timestamp", "date_time"],
    "u100": ["u100", "100m_u_component_of_wind", "u_100m", "u100m"],
    "v100": ["v100", "100m_v_component_of_wind", "v_100m", "v100m"],
    "u10": ["u10", "10m_u_component_of_wind", "u_10m", "u10m"],
    "v10": ["v10", "10m_v_component_of_wind", "v_10m", "v10m"],
    "ws100": ["ws100", "wind_speed_100m", "ws_100m", "wind100", "ws100m"],
    "ws10": ["ws10", "wind_speed_10m", "ws_10m", "si10", "wind10", "ws10m"],
    "t2m": ["t2m", "2m_temperature", "temperature_2m", "temp_2m"],
    "sp": ["sp", "surface_pressure", "pressure", "msl"],
    "lat": ["latitude", "lat"],
    "lon": ["longitude", "lon", "long"],
}


def _find(df: pd.DataFrame, key: str, overrides: dict) -> str | None:
    if key in overrides and overrides[key]:
        if overrides[key] not in df.columns:
            raise KeyError(f"ERA5 override column '{overrides[key]}' for '{key}' not in CSV: {list(df.columns)}")
        return overrides[key]
    lower = {c.lower().strip(): c for c in df.columns}
    for alias in ALIASES[key]:
        if alias in lower:
            return lower[alias]
    return None


def detect_columns(df: pd.DataFrame, overrides: dict | None = None) -> dict:
    overrides = overrides or {}
    return {k: _find(df, k, overrides) for k in ALIASES}


def _read_netcdf(path, site_lat, site_lon) -> pd.DataFrame:
    try:
        import xarray as xr
    except ImportError as e:  # pragma: no cover
        raise ImportError("Reading ERA5 NetCDF needs xarray + netCDF4: pip install xarray netCDF4") from e
    ds = xr.open_dataset(path)
    tdim = "valid_time" if "valid_time" in ds.dims else "time"
    keep = [v for v in ("u100", "v100", "u10", "v10", "si10", "t2m", "sp") if v in ds.data_vars]
    if not keep:
        raise KeyError(f"No ERA5 wind variables in {path}: {list(ds.data_vars)}")
    ds = ds[keep]
    if "latitude" in ds.dims and ds.sizes["latitude"] * ds.sizes.get("longitude", 1) > 1:
        lats, lons = ds.latitude.values, ds.longitude.values
        if site_lat is None or site_lon is None:
            raise ValueError("ERA5 NetCDF has several grid points: set site.latitude/longitude "
                             "(or they are taken from the NASA POWER header via the hybrid builder).")
        inside = lats.min() <= site_lat <= lats.max() and lons.min() <= site_lon <= lons.max()
        if inside:
            ds = ds.interp(latitude=site_lat, longitude=site_lon)        # bilinear on components
            log.info("ERA5: bilinear interpolation of %d grid points to (%.4f, %.4f)",
                     len(lats) * len(lons), site_lat, site_lon)
        else:
            ds = ds.sel(latitude=site_lat, longitude=site_lon, method="nearest")
            log.info("ERA5: site outside grid; nearest point used")
    elif "latitude" in ds.dims:
        ds = ds.isel(latitude=0, longitude=0)
    df = ds.to_dataframe().reset_index()
    return df[[tdim] + keep].rename(columns={tdim: "valid_time"})


def load_era5(path, overrides: dict | None = None, site_lat=None, site_lon=None,
              hub_height_m: float = 80.0, shear_exponent: float = 0.143) -> pd.DataFrame:
    """Return an hourly UTC-indexed frame with columns
    ws_ref_ms, ref_height_m, ws_hub_ms, t2m_k, sp_pa, rho_kgm3.
    t2m/sp/rho are NaN when the file has no temperature/pressure (filled by the hybrid builder)."""
    if str(path).lower().endswith((".nc", ".nc4", ".netcdf")):
        df = _read_netcdf(path, site_lat, site_lon)
    else:
        df = pd.read_csv(path, comment="#")
    cols = detect_columns(df, overrides)
    if cols["time"] is None:
        raise KeyError(f"No time column found in {path}. Columns: {list(df.columns)}. "
                       "Set data.era5_columns.time in the config.")

    # Multiple grid points → keep the one nearest to the site (or the first).
    if cols["lat"] and cols["lon"] and df[[cols["lat"], cols["lon"]]].drop_duplicates().shape[0] > 1:
        pts = df[[cols["lat"], cols["lon"]]].drop_duplicates()
        if site_lat is not None and site_lon is not None:
            d = (pts[cols["lat"]] - site_lat) ** 2 + (pts[cols["lon"]] - site_lon) ** 2
            lat0, lon0 = pts.loc[d.idxmin()].tolist()
        else:
            lat0, lon0 = pts.iloc[0].tolist()
            log.warning("ERA5 CSV has %d grid points and no site lat/lon configured; using (%.3f, %.3f)",
                        len(pts), lat0, lon0)
        df = df[(df[cols["lat"]] == lat0) & (df[cols["lon"]] == lon0)]

    t = pd.to_datetime(df[cols["time"]], utc=True)
    out = pd.DataFrame(index=pd.DatetimeIndex(t, name="time_utc"))

    def arr(key):
        return df[cols[key]].to_numpy(dtype=float)

    if cols["u100"] and cols["v100"]:
        ws_ref, h_ref = np.hypot(arr("u100"), arr("v100")), 100.0
    elif cols["ws100"]:
        ws_ref, h_ref = arr("ws100"), 100.0
    elif cols["u10"] and cols["v10"]:
        ws_ref, h_ref = np.hypot(arr("u10"), arr("v10")), 10.0
        log.warning("ERA5: no 100 m wind found; extrapolating from 10 m (less accurate).")
    elif cols["ws10"]:
        ws_ref, h_ref = arr("ws10"), 10.0
        log.warning("ERA5: no 100 m wind found; extrapolating from 10 m (less accurate).")
    else:
        raise KeyError(f"No wind columns (u100/v100, ws100, u10/v10, ws10) in {path}: {list(df.columns)}")

    out["ws_ref_ms"] = ws_ref
    out["ref_height_m"] = h_ref
    out["ws_hub_ms"] = ws_ref * (hub_height_m / h_ref) ** shear_exponent

    if cols["t2m"]:
        t2m = arr("t2m")
        if np.nanmax(t2m) < 100.0:
            log.info("ERA5 t2m looks like °C; converting to K.")
            t2m = t2m + 273.15
        out["t2m_k"] = t2m
    else:
        out["t2m_k"] = np.nan
    if cols["sp"]:
        sp = arr("sp")
        if np.nanmax(sp) < 2000.0:
            log.info("ERA5 surface pressure looks like hPa; converting to Pa.")
            sp = sp * 100.0
        out["sp_pa"] = sp
    else:
        out["sp_pa"] = np.nan
    out["rho_kgm3"] = out["sp_pa"] / (287.05 * out["t2m_k"])

    out = out[~out.index.duplicated(keep="first")].sort_index()
    n_bad = int(out["ws_hub_ms"].isna().sum())
    if n_bad:
        log.warning("ERA5: %d missing wind values interpolated (limit 6 h).", n_bad)
    out = out.resample("1h").mean()
    out["ws_hub_ms"] = out["ws_hub_ms"].interpolate(limit=6)
    out["ws_ref_ms"] = out["ws_ref_ms"].interpolate(limit=6)
    return out


load_era5_csv = load_era5  # backwards-compatible name
