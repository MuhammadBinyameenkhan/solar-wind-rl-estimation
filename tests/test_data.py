import numpy as np
import pandas as pd
import pytest

from vsgrl.data.era5 import load_era5_csv
from vsgrl.data.nasa_power import load_nasa_power_csv


def test_hybrid_dataset(df):
    assert {"train", "val", "test"} == set(df.split.unique())
    assert df.index.is_monotonic_increasing and str(df.index.tz) == "UTC"
    assert (df.p_wind_mw.between(0, 1.0)).all() and (df.p_pv_mpp_mw.between(0, 0.8)).all()
    # chronological split: all train before all test
    assert df[df.split == "train"].index.max() < df[df.split == "test"].index.min()


def test_nasa_lst_to_utc(cfg):
    from vsgrl.config import resolve_path
    s = load_nasa_power_csv(resolve_path(cfg["data"]["nasa_power_csv"]))
    assert s.attrs["time_standard"] == "LST"
    # solar noon at lon 67E is ~07:30 UTC
    noon = s.groupby(s.index.hour).ghi_wm2.mean().idxmax()
    assert 6 <= noon <= 9


def test_era5_variants(tmp_path):
    t = pd.date_range("2022-01-01", periods=200, freq="1h")
    pd.DataFrame({"date": t, "wind_speed_100m": 8.0, "t2m": 20.0, "sp": 1013.0}).to_csv(tmp_path / "a.csv", index=False)
    w = load_era5_csv(tmp_path / "a.csv", hub_height_m=100.0)
    assert np.allclose(w.ws_hub_ms, 8.0)
    assert np.allclose(w.t2m_k, 293.15) and np.allclose(w.sp_pa, 101300.0)   # °C and hPa converted
    assert 1.15 < w.rho_kgm3.iloc[0] < 1.25


def test_nasa_daily_rejected(tmp_path):
    p = tmp_path / "d.csv"
    p.write_text("-BEGIN HEADER-\nx in LST\n-END HEADER-\nYEAR,MO,DY,ALLSKY_SFC_SW_DWN\n2020,1,1,5.1\n")
    with pytest.raises(ValueError, match="DAILY"):
        load_nasa_power_csv(p)


def test_weekly_block_split_covers_all_seasons():
    from vsgrl.data.hybrid import assign_split
    idx = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="1h", tz="UTC")
    lab = pd.Series(assign_split(idx, {"method": "weekly_blocks"}), index=idx)
    for sp in ("train", "val", "test"):
        assert lab[lab == sp].index.quarter.nunique() == 4      # every season in every split
    assert abs((lab == "train").mean() - 5 / 7) < 0.02
    # a whole week never spans two splits
    assert lab.groupby((idx - idx[0]).days // 7).nunique().max() == 1


def test_era5_netcdf_interpolation(tmp_path):
    xr = pytest.importorskip("xarray")
    pytest.importorskip("netCDF4")
    t = pd.date_range("2024-01-01", periods=48, freq="1h")
    lat, lon = np.array([15.0, 14.75]), np.array([102.0, 102.25])
    u = np.zeros((48, 2, 2)); u[:, :, 0], u[:, :, 1] = 4.0, 8.0     # u varies with longitude only
    ds = xr.Dataset({"u100": (("valid_time", "latitude", "longitude"), u),
                     "v100": (("valid_time", "latitude", "longitude"), np.zeros_like(u))},
                    coords={"valid_time": t, "latitude": lat, "longitude": lon})
    ds.to_netcdf(tmp_path / "e.nc")
    w = load_era5_csv(tmp_path / "e.nc", site_lat=14.9, site_lon=102.125, hub_height_m=100.0)
    assert np.allclose(w.ws_hub_ms, 6.0)                 # bilinear midpoint
    assert w.rho_kgm3.isna().all()                       # no t2m/sp → filled by hybrid builder
