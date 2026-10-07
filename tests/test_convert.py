"""tools/convert_to_csv.py on mock NetCDF-4 (HDF5) and .mat files."""
import importlib.util
import os

import numpy as np
import pytest

h5py = pytest.importorskip("h5py")
scipy_io = pytest.importorskip("scipy.io")

spec = importlib.util.spec_from_file_location(
    "convert_to_csv", os.path.join(os.path.dirname(__file__), "..", "tools", "convert_to_csv.py"))
conv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conv)


def test_netcdf_irradiance_with_cf_time(tmp_path):
    for day in (1, 2):
        with h5py.File(tmp_path / f"cabauw_2015010{day}.nc", "w") as f:
            t = f.create_dataset("time", data=np.arange(0, 7200, 1.0))
            t.attrs["units"] = f"seconds since 2015-01-0{day} 08:00:00"
            f.create_dataset("GHI", data=300 + 50 * np.sin(np.arange(7200) / 300))
    out = tmp_path / "irr.csv"
    conv.main(["irradiance", "--var", "ghi", "--out", str(out), str(tmp_path / "*.nc")])
    lines = out.read_text().splitlines()
    assert lines[0] == "time,value" and lines[1].startswith("2015-01-01T08:00:00")
    assert len(lines) == 1 + 2 * 7200


def test_mat_wind_10hz_to_1s_with_time_from_name(tmp_path):
    rng = np.random.default_rng(0)
    for hour in (13, 14):
        u = 8 + rng.standard_normal(36000)
        v = 0.5 * rng.standard_normal(36000)
        scipy_io.savemat(tmp_path / f"FINO1_80m_20070612_{hour}00.mat", {"u": u, "v": v, "w": v})
    out = tmp_path / "wind.csv"
    conv.main(["wind", "--u", "u", "--v", "v", "--hz", "10", "--out", str(out),
               str(tmp_path / "*.mat")])
    lines = out.read_text().splitlines()
    assert len(lines) == 1 + 2 * 3600
    assert lines[1].startswith("2007-06-12T13:00:00") and lines[3601].startswith("2007-06-12T14:00:00")
    speeds = np.array([float(l.split(",")[1]) for l in lines[1:]])
    assert 7.5 < speeds.mean() < 8.5          # 1 s means of the horizontal speed
