"""
Five disturbance scenarios (paper Table 1) and their weather calibration.

    clear      constant irradiance, steady wind            (baseline)
    cloud      successive cloud shadows over the array     (PV ramp)
    wind_drop  gust collapse towards cut-in                (wind lull)
    night      no solar, gusty low wind                    (no PV)
    combined   simultaneous PV collapse + wind collapse    (worst case)

Each returns irradiance G [W/m^2], ambient T [degC], wind v [m/s] and a
turbulence sigma [m/s], sampled at the control period.

Data provenance (be precise about this in the paper):
  * The STEADY LEVELS and the disturbance DEPTHS come from a calibration
    file (data/weather_calibration.json).  Regenerate it from the
    Open-Meteo historical archive (ERA5 reanalysis, hourly) with
        python -m vsg_rl.weather --calibrate --start 2024-01-01 --end 2024-12-31
    These are reanalysis/model data for the site, NOT on-site measurements.
  * The SUB-SECOND SHAPES are synthetic: no public dataset resolves weather
    at the time scale on which inertia emulation acts.
"""
import argparse
import json
import os

import numpy as np

from . import config as C
from .utils import lowpass_noise

SCENARIOS = ["clear", "cloud", "wind_drop", "night", "combined"]

SYNTHETIC_LEVELS = dict(irr=950.0, temp=28.0, wind=10.0, cloud_depth=0.90,
                        wind_before=11.0, wind_after=3.5, night_wind=5.5,
                        night_temp=15.0)


def load_calibration(path=None) -> dict | None:
    path = path or C.CALIBRATION_FILE
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


class WeatherScenarios:
    """Deterministic, repeatable disturbance profiles.

    All event times are written for a 10 s reference window and rescaled by
    ``sc = duration / 10`` so they spread over the configured episode.
    """

    def __init__(self, levels: dict | None = None, dt: float | None = None,
                 duration: float | None = None):
        self.dt = C.CONTROL_DT if dt is None else dt
        self.duration = C.EPISODE_DURATION if duration is None else duration
        self.N = int(round(self.duration / self.dt))
        self.t = np.arange(self.N) * self.dt
        self.sc = self.duration / 10.0
        lv = dict(SYNTHETIC_LEVELS)
        lv.update({k: v for k, v in (levels or {}).items() if k in SYNTHETIC_LEVELS})
        lv["wind"] = max(3.0, lv["wind"])
        self.lv = lv
        self.source = (levels or {}).get("source", "synthetic")

    def _const(self, value: float) -> np.ndarray:
        return np.full(self.N, float(value))

    # -- the five scenarios ---------------------------------------
    def clear(self):
        b = self.lv
        return (self._const(b["irr"]), self._const(b["temp"]),
                self._const(b["wind"]), self._const(0.12 * b["wind"] * 0.35))

    def cloud(self):
        b = self.lv
        t_start, t_end = 2.0 * self.sc, 5.0 * self.sc
        n_clouds = max(3, int(round(3 * self.sc)))
        irr = self._const(b["irr"])
        for tc in np.linspace(t_start, t_end, n_clouds):
            d = self.t - tc
            mask = (d > -0.5) & (d < 2.0)
            atten = b["cloud_depth"] * np.exp(-((d - 0.75) ** 2) / 0.30)
            irr[mask] *= (1.0 - atten[mask])
        return (np.clip(irr, 0.0, 1400.0), self._const(b["temp"]),
                self._const(b["wind"] * 0.95), self._const(0.45))

    def wind_drop(self):
        b = self.lv
        t_drop, t_rec = 2.0 * self.sc, 6.0 * self.sc
        v_before, v_after = b["wind_before"], b["wind_after"]
        wind = np.empty(self.N)
        for i, ti in enumerate(self.t):
            if ti < t_drop:
                wind[i] = v_before + 0.5 * np.sin(2 * np.pi * ti)
            elif ti < t_rec:
                prog = (ti - t_drop) / (t_rec - t_drop)
                wind[i] = v_after + (v_before - v_after) * np.exp(-3.0 * prog)
                wind[i] += 0.3 * np.sin(5 * np.pi * ti)
            else:
                wind[i] = v_after + 2.0 * (1.0 - np.exp(-0.5 / self.sc * (ti - t_rec)))
                wind[i] += 0.2 * np.sin(3 * np.pi * ti)
        return (self._const(b["irr"] * 0.79), self._const(b["temp"] - 2.0),
                np.clip(wind, 2.0, 25.0), self._const(0.65))

    def night(self):
        b = self.lv
        wind = (self._const(b["night_wind"])
                + 0.8 * np.sin(2 * np.pi * self.t / 3.0)
                + 0.3 * np.sin(5 * np.pi * self.t))
        return (np.zeros(self.N), self._const(b["night_temp"]),
                np.clip(wind, 2.0, 25.0), self._const(0.85))

    def combined(self):
        b = self.lv
        irr = self._const(b["irr"])
        v0 = b["wind"] * 1.1
        wind = self._const(v0)
        t_pv, t_w = 2.0 * self.sc, 2.5 * self.sc
        for i, ti in enumerate(self.t):
            if ti >= t_pv:
                irr[i] = max(80.0, b["irr"] * np.exp(-0.5 / self.sc * (ti - t_pv)))
                irr[i] += 20.0 * np.sin(3.0 * ti)
            if ti >= t_w:
                wind[i] = max(3.0, v0 - (v0 - 3.0)
                              * (1.0 - np.exp(-2.0 / self.sc * (ti - t_w))))
                wind[i] += 0.4 * np.sin(4.0 * ti)
        return (np.clip(irr, 0.0, 1400.0), self._const(b["temp"] + 4.0),
                np.clip(wind, 2.5, 25.0), self._const(0.75))

    # -- dispatch -------------------------------------------------
    def get(self, name: str, stochastic: bool = False, rng=None):
        fn = getattr(self, name) if name in SCENARIOS else self.clear
        irr, temp, wind, turb = fn()
        if stochastic:
            rng = rng or np.random.default_rng()
            irr = irr * rng.uniform(0.85, 1.10) + lowpass_noise(rng, self.N, self.dt, 0.5) * 25.0
            wind = wind * rng.uniform(0.88, 1.12) + lowpass_noise(rng, self.N, self.dt, 0.5) * 0.5
            temp = temp + rng.uniform(-3.0, 3.0)
            irr, temp = np.clip(irr, 0.0, 1400.0), np.clip(temp, -5.0, 55.0)
            wind, turb = np.clip(wind, 1.0, 25.0), np.clip(turb, 0.05, 2.0)
        return irr, temp, wind, turb


def build_weather(dt=None, duration=None) -> WeatherScenarios:
    levels = None
    if C.WEATHER_SOURCE == "calibrated":
        levels = load_calibration()
    return WeatherScenarios(levels, dt=dt, duration=duration)


# ================================================================
# Calibration from the Open-Meteo historical archive (run locally)
# ================================================================
def fetch_archive(lat, lon, start, end):
    """Hourly ERA5 reanalysis: irradiance, 2 m temperature, 100 m wind."""
    import urllib.request
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
           "&hourly=shortwave_radiation,temperature_2m,wind_speed_100m"
           "&wind_speed_unit=ms&timezone=auto")
    with urllib.request.urlopen(url, timeout=60) as resp:
        h = json.loads(resp.read().decode())["hourly"]
    f = lambda xs, d: np.array([d if x is None else float(x) for x in xs])
    return dict(time=h["time"], irr=f(h["shortwave_radiation"], 0.0),
                temp=f(h["temperature_2m"], np.nan),
                wind=f(h["wind_speed_100m"], 0.0))


def calibrate(series: dict, hub_height: float = 80.0) -> dict:
    """Scenario levels from a measured / reanalysis record.

    Cloud depth is the 99th percentile of the RELATIVE hour-to-hour drop in
    irradiance, restricted to hours where the previous value was already above
    half the daytime 90th percentile -- this excludes the deterministic
    sunset ramp, which the previous version mistook for a cloud.
    No silent clipping: the raw values are stored alongside.
    """
    g, t, v = series["irr"], series["temp"], series["wind"]
    v = v * (hub_height / 100.0) ** 0.14          # 100 m -> hub height
    ok = ~np.isnan(t)
    g, t, v = g[ok], t[ok], v[ok]
    day = g > 50.0
    hi = float(np.quantile(g[day], 0.90))
    prev, nxt = g[:-1], g[1:]
    sel = prev > 0.5 * hi
    rel_drop = np.clip((prev[sel] - nxt[sel]) / prev[sel], 0.0, 1.0)
    depth = float(np.quantile(rel_drop, 0.99)) if sel.any() else 0.3
    dv = np.diff(v)
    w_hi = float(np.quantile(v, 0.90))
    w_fall = float(np.quantile(-dv[dv < 0], 0.99)) if (dv < 0).any() else 3.0
    return dict(
        source="open-meteo-archive (ERA5 reanalysis, hourly)",
        samples=int(len(g)),
        span=f"{series['time'][0]} -> {series['time'][-1]}",
        irr=hi, temp=float(np.median(t[day])), wind=float(np.median(v[day])),
        cloud_depth=depth, wind_before=w_hi, wind_after=max(2.0, w_hi - w_fall),
        night_wind=float(np.median(v[~day])), night_temp=float(np.median(t[~day])),
    )


def _cli():
    ap = argparse.ArgumentParser(description="Weather calibration tool")
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default="2024-12-31")
    ap.add_argument("--out", default=C.CALIBRATION_FILE)
    args = ap.parse_args()
    if args.calibrate:
        cal = calibrate(fetch_archive(C.REAL_LAT, C.REAL_LON, args.start, args.end))
        cal["lat"], cal["lon"] = C.REAL_LAT, C.REAL_LON
        with open(args.out, "w") as fh:
            json.dump(cal, fh, indent=1)
        print(json.dumps(cal, indent=1))


if __name__ == "__main__":
    _cli()
