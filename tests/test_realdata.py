"""Measured-data pipeline on a small generated record (format test only)."""
import json

import numpy as np

from vsg_rl import config as C


def _write_record(tmp_path, hours=6):
    rng = np.random.default_rng(1)
    n = hours * 3600
    t = np.arange(n)
    # daytime irradiance with occasional cloud dips, then a dark tail
    g = 800 + 20 * rng.standard_normal(n)
    for c in rng.choice(n - 600, 40, replace=False):
        g[c:c + 60] *= 0.4
    g[-4000:] = 0.0
    v = 8 + 0.5 * rng.standard_normal(n)
    for c in rng.choice(n - 600, 30, replace=False):
        v[c:c + 120] -= 4.0
    stamp = lambda i: f"2010-07-01T{6 + i // 3600:02d}:{(i // 60) % 60:02d}:{i % 60:02d}"
    with open(tmp_path / "irr.csv", "w") as fh:
        fh.write("time,ghi\n" + "".join(f"{stamp(i)},{g[i]:.2f}\n" for i in t))
    with open(tmp_path / "wind.csv", "w") as fh:
        fh.write("t_s,ws\n" + "".join(f"{i},{v[i]:.3f}\n" for i in t))
    cfg = {"irradiance": {"file": "irr.csv", "time_column": "time", "value_column": "ghi"},
           "wind": {"file": "wind.csv", "time_column": "t_s", "value_column": "ws", "height_m": 80},
           "split_fractions": [0.6, 0.2, 0.2]}
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(cfg))
    return str(path)


def test_measured_scenarios_end_to_end(tmp_path, monkeypatch):
    from vsg_rl import realdata
    from vsg_rl.baselines import FixedPolicy
    from vsg_rl.env import MicrogridVSGEnv
    monkeypatch.setattr(C, "MEASURED_CONFIG", _write_record(tmp_path))
    monkeypatch.setattr(C, "WEATHER_SOURCE", "measured")
    realdata._CACHE.clear()

    rec = realdata.get_record()
    for sp in ("train", "val", "test"):
        assert rec.cand[sp]["cloud"] and rec.cand[sp]["wind_drop"]
    # splits never share a window
    tr = set(rec.cand["train"]["cloud"]); te = set(rec.cand["test"]["cloud"])
    assert not tr & te

    w = realdata.MeasuredWeatherScenarios()
    irr, temp, wind, turb = w.get("cloud", split="test")
    assert len(irr) == w.N and irr.min() < 0.8 * irr[: w.N // 5].mean()   # a real dip
    irr, _, wind, _ = w.get("combined", split="test")
    assert wind[-1] < wind[: w.N // 5].mean()

    env = MicrogridVSGEnv("combined", split="test")
    out = env.rollout(FixedPolicy(1.0, 20.0), seed=0)
    assert np.isfinite(out["f"]).all() and not out["tripped"]
    realdata._CACHE.clear()


def test_split_ignores_calendar_gaps():
    from vsg_rl.realdata import _split_ranges
    # 100 s of data, a 10 000 s gap, 100 s of data
    gap = np.r_[np.zeros(100, bool), np.ones(10_000, bool), np.zeros(100, bool)]
    r = _split_ranges(gap, [0.5, 0.25, 0.25])
    have = lambda a, b: int((~gap[a:b]).sum())
    assert have(*r["train"]) == 100 and have(*r["val"]) == 50 and have(*r["test"]) == 50
