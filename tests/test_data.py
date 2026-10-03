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
