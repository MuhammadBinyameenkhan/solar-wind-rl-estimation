"""Generate SYNTHETIC files in the exact ERA5 / NASA POWER CSV layouts.

FOR TESTING THE PIPELINE ONLY — never report results obtained on these files.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def make_sample_files(out_dir, year=2023, lat=25.0, lon=67.0, seed=0, time_standard="LST"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    t = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="1h", tz="UTC")
    n = len(t)

    # ERA5-like: Weibull-ish 100 m wind with diurnal + synoptic variability.
    syn = np.zeros(n)
    e = rng.normal(0, 1, n)
    for i in range(1, n):
        syn[i] = 0.97 * syn[i - 1] + 0.25 * e[i]
    doy = t.dayofyear.to_numpy()
    hour = t.hour.to_numpy()
    ws = np.clip(7.0 + 1.5 * np.sin(2 * np.pi * (doy - 150) / 365) + 1.0 * np.sin(2 * np.pi * (hour - 15) / 24)
                 + 2.2 * syn, 0.2, None)
    direction = rng.uniform(0, 2 * np.pi) + 0.3 * np.cumsum(rng.normal(0, 0.05, n))
    t2m_k = 273.15 + 27 + 7 * np.sin(2 * np.pi * (doy - 110) / 365) + 4 * np.sin(2 * np.pi * (hour - 10 + lon / 15) / 24)
    era5 = pd.DataFrame({
        "valid_time": t.strftime("%Y-%m-%d %H:%M:%S"),
        "latitude": lat, "longitude": lon,
        "u100": ws * np.cos(direction), "v100": ws * np.sin(direction),
        "u10": 0.75 * ws * np.cos(direction), "v10": 0.75 * ws * np.sin(direction),
        "t2m": t2m_k, "sp": 100800 + 400 * syn,
    })
    era5.to_csv(out_dir / "era5_SYNTHETIC.csv", index=False)

    # NASA POWER-like hourly file with header, in LST (or UTC).
    off = lon / 15.0 if time_standard == "LST" else 0.0
    tl = t + pd.Timedelta(hours=off)
    lat_r = np.radians(lat)
    decl = np.radians(23.45) * np.sin(2 * np.pi * (284 + tl.dayofyear.to_numpy()) / 365)
    ha = np.radians(15 * (tl.hour.to_numpy() + 0.5 - 12))
    cosz = np.sin(lat_r) * np.sin(decl) + np.cos(lat_r) * np.cos(decl) * np.cos(ha)
    clear = 1050 * np.clip(cosz, 0, None) ** 1.15
    cloud = np.clip(1 - 0.35 * np.clip(rng.normal(0.3, 0.4, n // 24 + 2), 0, 1).repeat(24)[:n]
                    - 0.15 * rng.random(n), 0.05, 1)
    ghi = np.round(clear * cloud, 2)
    t2m_c = np.round(t2m_k - 273.15 + rng.normal(0, 0.5, n), 2)
    ws10 = np.round(0.75 * ws, 2)
    ghi[rng.random(n) < 0.002] = -999
    header = (
        "-BEGIN HEADER-\n"
        "NASA/POWER CERES/MERRA2 Native Resolution Hourly Data  (SYNTHETIC SAMPLE — NOT REAL DATA)\n"
        f"Dates (month/day/year): 01/01/{year} through 12/31/{year} in {time_standard}\n"
        f"Location: Latitude  {lat:.4f}   Longitude {lon:.4f}\n"
        "Value for missing model data cannot be computed or out of model availability range: -999\n"
        "Parameter(s):\n"
        "ALLSKY_SFC_SW_DWN     CERES SYN1deg All Sky Surface Shortwave Downward Irradiance (Wh/m^2)\n"
        "T2M                   MERRA-2 Temperature at 2 Meters (C)\n"
        "WS10M                 MERRA-2 Wind Speed at 10 Meters (m/s)\n"
        "-END HEADER-\n"
    )
    nasa = pd.DataFrame({"YEAR": tl.year, "MO": tl.month, "DY": tl.day, "HR": tl.hour,
                         "ALLSKY_SFC_SW_DWN": ghi, "T2M": t2m_c, "WS10M": ws10})
    with open(out_dir / "nasa_power_SYNTHETIC.csv", "w") as fh:
        fh.write(header)
        nasa.to_csv(fh, index=False)
    return out_dir / "era5_SYNTHETIC.csv", out_dir / "nasa_power_SYNTHETIC.csv"
