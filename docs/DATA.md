# Real-data pipeline: ERA5 (wind) + NASA POWER (solar)

## The study dataset (2024, Nakhon Ratchasima, Thailand)

| File | Content |
|---|---|
| `data/raw/era5_wind_2024.nc` | ERA5 single levels, `u100`, `v100`, hourly UTC, grid 15.0/14.75° N × 102.0/102.25° E |
| `data/raw/nasa_power_solar_2024.csv` | NASA POWER hourly point 14.98° N 102.10° E, LST: `ALLSKY_SFC_SW_DWN`, `T2M`, `WS10M`, `WS50M` |

Results of `scripts/prepare_data.py` (8777 overlapping hours):

| | Hub wind (m/s) | Wind CF | PV CF | Mean GHI (W/m²) | Mean load (MW) | RES share |
|---|---|---|---|---|---|---|
| all | 4.19 | 9.5 % | 17.3 % | 213 | 0.64 | 36 % |
| train | 4.38 | 10.5 % | 17.2 % | 212 | 0.64 | 37 % |
| val | 3.71 | 7.7 % | 17.1 % | 211 | 0.64 | 33 % |
| test | 3.67 | 6.3 % | 18.1 % | 223 | 0.64 | 32 % |

Site-specific decisions (all in `configs/default.yaml`):

* **Low-wind site.** ERA5 100 m wind averages 4.2 m/s (monthly 3.1–5.8 m/s) and the hourly maximum in 2024 is 11.2 m/s. MERRA-2 50 m wind from the POWER file averages 5.1 m/s, with an hourly correlation of 0.78 against ERA5. The two reanalyses agree that this is a low-wind site. ERA5 is the lower of the two, so wind output here is conservative; a sensitivity check with a local measurement or MERRA-2 50 m wind is worth mentioning. A generic 12 m/s-rated turbine would reach a capacity factor of only 4.4 %. The study therefore uses an **IEC class III** turbine (cut-in 2.5 m/s, rated 10 m/s) on a **100 m hub**, which is ERA5's own height, so no shear extrapolation is needed. That gives a CF of 9.5 %.
* **Air density.** The ERA5 file has no `t2m` or `sp`. ρ = p/(R_d T), with T from NASA T2M and p = 101325·(1 − 2.25577·10⁻⁵ h)^5.25588 at h = 226 m (elevation from the POWER header), giving about 1.15 kg/m³.
* **Time zones.** POWER is in LST (offset longitude/15 = 6.81 h) and converted to UTC. GHI peaks at 11:00 local, as expected. The load profile uses clock time, UTC+7.
* **Split.** With a single year, a chronological split would put only November–December (dry season) in the test set. **Weekly blocks** are used instead: 5 train / 1 val / 1 test of every 7 weeks. All four quarters appear in every split, and whole weeks limit autocorrelation leakage.
* **Load sizing.** The synthetic load is scaled to 0.3–0.8 MW. At 1.2 MW peak, 51 % of operating points failed the adequacy screen, because the evening peak comes after sunset with weak wind and the firm capacity (diesel + BESS) is about 1 MW. At 0.8 MW the rejection rate is 7 %, and night hours keep their natural share (44 % vs 46 %).

## Why hybrid

| Variable | Source | Reason |
|---|---|---|
| Hub-height wind speed | **ERA5** `u100`, `v100` | ERA5 provides 100 m wind directly (close to hub height). NASA POWER's MERRA-2 wind is at 2/10/50 m and coarser. |
| Air density | **ERA5** `t2m`, `sp` → ρ = p/(R_d T) | Used for the IEC 61400-12-1 density correction of the power curve. |
| Irradiance (GHI) | **NASA POWER** `ALLSKY_SFC_SW_DWN` | Satellite-derived (CERES) all-sky surface irradiance. ERA5 radiation is model-derived and tends to be biased under clouds. |
| Ambient temperature for PV | **NASA POWER** `T2M` | Kept consistent with the irradiance source for the cell-temperature model. |

## Accepted ERA5 files (`vsgrl/data/era5.py`)

**NetCDF** (`.nc`, the CDS download): variables `u100`/`v100` (plus optionally `u10`/`v10`, `t2m`, `sp`) on `valid_time × latitude × longitude`. The components are bilinearly interpolated to `site.latitude/longitude`; if those are null, the NASA POWER header location is used. Needs `xarray` + `netCDF4`.

**CSV:** column names are detected automatically, case-insensitive:

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
