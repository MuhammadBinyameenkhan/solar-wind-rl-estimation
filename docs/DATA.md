# Real-data pipeline: ERA5 (wind) + NASA POWER (solar)

## Why hybrid

| Variable | Source | Reason |
|---|---|---|
| Hub-height wind speed | **ERA5** `u100`, `v100` | ERA5 provides 100 m wind directly (close to hub height). NASA POWER's MERRA-2 wind is at 2/10/50 m and coarser. |
| Air density | **ERA5** `t2m`, `sp` → ρ = p/(R_d T) | Used for the IEC 61400-12-1 density correction of the power curve. |
| Irradiance (GHI) | **NASA POWER** `ALLSKY_SFC_SW_DWN` | Satellite-derived (CERES) all-sky surface irradiance. ERA5 radiation is model-derived and tends to be biased under clouds. |
| Ambient temperature for PV | **NASA POWER** `T2M` | Kept consistent with the irradiance source for the cell-temperature model. |

## Accepted ERA5 CSV layouts (`vsgrl/data/era5.py`)

The column names are detected automatically, case-insensitive:

| Meaning | Accepted names |
|---|---|
| time (UTC) | `valid_time`, `time`, `date`, `datetime`, `timestamp` |
| 100 m wind | `u100`+`v100`, or `ws100` / `wind_speed_100m` |
| 10 m wind (fallback, extrapolated) | `u10`+`v10`, or `ws10` / `si10` |
| temperature | `t2m` (K; °C detected automatically) |
| surface pressure | `sp` (Pa; hPa detected automatically) |
| grid point | `latitude`, `longitude`; with several points, the nearest to `site.latitude/longitude` is used |

If your columns have other names, map them in the config:
```yaml
data:
  era5_columns: {time: my_time_col, u100: U100m, v100: V100m}
```

**Download** (Copernicus CDS, `reanalysis-era5-single-levels`, hourly): select `100m_u_component_of_wind`, `100m_v_component_of_wind`, `2m_temperature` and `surface_pressure` for your site's grid cell. The CDS point time-series product, or `xarray.open_dataset(...).to_dataframe().to_csv()` on a NetCDF download, both produce a layout listed above.

Hub-height extrapolation uses the power law v_hub = v_100 (h_hub/100)^α, with α = 1/7 by default (`system.wind.shear_exponent`). If you have a site-specific shear exponent, set it there.

## Accepted NASA POWER CSV (`vsgrl/data/nasa_power.py`)

This is the standard **hourly** download with its `-BEGIN HEADER- … -END HEADER-` block, followed by columns `YEAR,MO,DY,HR,...` (or `YEAR,DOY,HR`). Missing values (−999) are interpolated over at most 3 h; night-time gaps become 0.

**Time standard:** POWER hourly files are in LST (local solar time) or UTC, and the header says which ("… in LST"). LST is converted to UTC using `data.nasa_utc_offset_hours`, or longitude/15 if that is not set. Getting this wrong shifts the PV profile against the wind and load, so check the solar-noon hour that `scripts/inspect_data.py` reports.

**Download** (power.larc.nasa.gov → Data Access Viewer, or the API):
```
https://power.larc.nasa.gov/api/temporal/hourly/point?parameters=ALLSKY_SFC_SW_DWN,T2M,WS10M
    &community=RE&latitude=<lat>&longitude=<lon>&start=YYYYMMDD&end=YYYYMMDD&format=CSV&time-standard=UTC
```
Daily files are rejected with a clear error. Frequency studies need at least hourly operating points.

## Processing (`vsgrl/data/hybrid.py`, `scripts/prepare_data.py`)

1. Both sources are resampled to an hourly UTC index and inner-joined. The script prints the overlap, which should cover the same period.
2. Wind: v_hub → density-corrected generic 1 MW curve (cut-in 3, rated 12, cut-out 25 m/s), or your manufacturer curve via `system.wind.power_curve_csv` (columns `wind_speed_ms,power_mw`).
3. PV: P = P_rated · 0.90 · (G/1000) · [1 − 0.004 (T_cell − 25)], with T_cell = T_amb + (NOCT − 20)/800 · G.
4. Load: a measured `data.load_csv` (`time,load_mw`) if provided. Otherwise a synthetic daily, weekly and seasonal profile scaled to 0.45–1.2 MW in local time. **State this in the paper**, or provide measured data.
5. Chronological train/val/test split on whole days (`data.split`).

Output: `data/processed/hourly_resource.csv` plus `_summary.csv`. The summary contains capacity factors, mean GHI and RES share per split, which is the data table for the paper.

## Sanity checks to do on your real data

* Run `python scripts/inspect_data.py` and check: wind mean 4–9 m/s at most sites; GHI max 900–1100 W/m²; solar noon near 12:00 local time; overlap equal to the expected number of hours.
* The wind capacity factor at 100 m from ERA5 is typically 20–40 % at decent sites. If it is under 10 %, check the units and the hub-height setting.
* Run `python scripts/plot.py` and look at `fig_data_overview.pdf`, which shows the daily means and the split.
