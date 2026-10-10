"""
Measured high-resolution weather -> the five scenarios.

Instead of synthetic disturbance shapes, every episode is cut from a real
time series (ideally 1-second irradiance and 1-second wind):

  clear      the steadiest high-irradiance windows
  cloud      the deepest irradiance drops (relative, over 5 s)
  wind_drop  the largest wind-speed falls (over 10 s)
  night      windows with irradiance ~ 0 (or zero irradiance if the record
             has no night data) with real wind
  combined   a measured cloud window AND a measured wind-drop window played
             simultaneously (the two events are real, their coincidence is
             the designed worst case)

Events are aligned so the disturbance starts 20 % into the window, like the
synthetic scenarios.  The record is split by TIME into train / validation /
test segments, so the windows the agents learn on never appear in the
reported tests.

Everything is configured in one JSON file (default
data/measured/dataset.json, template in data/measured/dataset.example.json);
changing the data means editing that file only.  Check what was detected with

    python -m vsg_rl.realdata --check
"""
import argparse
import csv
import json
import os

import numpy as np

from . import config as C
from .weather import WeatherScenarios

EVENT_AT = 0.20          # event onset as a fraction of the window
N_CANDIDATES = 40        # windows kept per scenario and split
CLOUD_HORIZON_S = 5.0
WIND_HORIZON_S = 10.0
SPLITS = ("train", "val", "test")

_CACHE = {}


# ----------------------------------------------------------------
# Reading
# ----------------------------------------------------------------
def _parse_time(values):
    """Numeric seconds, or ISO-8601 timestamps ('2010-03-18 07:00:01')."""
    try:
        return np.array([float(v) for v in values])
    except ValueError:
        t = np.array([v.strip().replace(" ", "T").rstrip("Z") for v in values],
                     dtype="datetime64[ms]")
        return (t - t[0]).astype("timedelta64[ms]").astype(float) / 1000.0, t[0]


def read_series(spec: dict, base_dir: str):
    """-> (t seconds since the first sample of the record, values, t0 label)."""
    path = spec["file"]
    if not os.path.isabs(path):
        path = os.path.join(base_dir, path)
    cache = path + ".npz"
    if os.path.exists(cache) and os.path.getmtime(cache) >= os.path.getmtime(path):
        z = np.load(cache, allow_pickle=False)
        return z["t"], z["v"], str(z["t0"])
    times, vals = [], []
    with open(path, newline="") as fh:
        rdr = csv.DictReader(fh, delimiter=spec.get("delimiter", ","))
        tc, vc = spec["time_column"], spec["value_column"]
        missing = spec.get("missing_values", ["", "NaN", "nan", "-9999", "-999"])
        for row in rdr:
            v = row.get(vc, "")
            if v in missing:
                continue
            times.append(row[tc])
            vals.append(float(v))
    parsed = _parse_time(times)
    t0 = "0"
    if isinstance(parsed, tuple):
        parsed, t0 = parsed
        t0 = str(t0)
    else:
        parsed = parsed - parsed[0]
    v = np.asarray(vals, dtype=float) * float(spec.get("scale", 1.0))
    order = np.argsort(parsed, kind="stable")
    t, v = parsed[order], v[order]
    keep = np.concatenate([[True], np.diff(t) > 0])
    t, v = t[keep], v[keep]
    np.savez(cache, t=t, v=v, t0=t0)
    return t, v, t0


# ----------------------------------------------------------------
# Event detection
# ----------------------------------------------------------------
def despike(v, jump, settle_frac=0.5):
    """Replace isolated single-sample outliers (sensor dropouts / spikes).

    A sample is a spike if it departs from BOTH neighbours by more than
    ``jump`` in opposite directions while the neighbours agree with each
    other to within ``settle_frac * jump``; it is replaced by their mean.
    Real gusts persist for several samples and are left untouched.
    Returns (cleaned copy, number of samples replaced).
    """
    v = np.asarray(v, dtype=float).copy()
    if len(v) < 3:
        return v, 0
    a, b, c = v[:-2], v[1:-1], v[2:]
    spike = ((np.abs(b - a) > jump) & (np.abs(c - b) > jump)
             & (np.sign(b - a) != np.sign(c - b)) & (np.abs(c - a) < settle_frac * jump))
    idx = np.where(spike)[0] + 1
    v[idx] = 0.5 * (v[idx - 1] + v[idx + 1])
    return v, int(len(idx))


def _uniform(t, v, dt):
    """Resample onto a uniform grid; mark samples next to data gaps."""
    grid = np.arange(t[0], t[-1], dt)
    vi = np.interp(grid, t, v)
    idx = np.searchsorted(t, grid)
    idx = np.clip(idx, 1, len(t) - 1)
    gap = (t[idx] - t[idx - 1]) > 5.0 * dt
    return grid, vi, gap


def _split_ranges(gap, fractions):
    """Chronological split by the amount of DATA, not calendar time: a record
    of a few separate days (e.g. March and July) must not put a whole split
    inside the gap between them."""
    edges = np.concatenate([[0], np.cumsum(fractions)]) / np.sum(fractions)
    have = np.cumsum(~gap)
    cut = np.searchsorted(have, edges * have[-1], side="left") + 1   # exclusive end
    cut[0], cut[-1] = 0, len(gap)
    return {s: (int(cut[i]), int(cut[i + 1])) for i, s in enumerate(SPLITS)}


def _top_events(score, valid, w, k, lo, hi):
    """Indices of the k highest scores in [lo, hi), at least w apart."""
    s = np.where(valid[lo:hi], score[lo:hi], -np.inf)
    order = np.argsort(s)[::-1]
    taken, out = np.zeros(hi - lo, bool), []
    for i in order:
        if not np.isfinite(s[i]) or len(out) >= k:
            break
        if taken[max(0, i - w):i + w].any():
            continue
        taken[i] = True
        out.append(lo + i)
    return out


def _window_ok(gap, start, n):
    return start >= 0 and start + n <= len(gap) and not gap[start:start + n].any()


class MeasuredRecord:
    """Detected scenario windows on a uniform 1 s grid, per split."""

    def __init__(self, cfg_path: str):
        with open(cfg_path) as fh:
            cfg = json.load(fh)
        base = os.path.dirname(os.path.abspath(cfg_path))   # files relative to the JSON
        self.cfg = cfg
        self.dt = float(cfg.get("analysis_dt_s", 1.0))
        win = int(round(C.EPISODE_DURATION / self.dt))
        self.win = win
        lead = int(round(EVENT_AT * win))
        frac = cfg.get("split_fractions", [0.7, 0.15, 0.15])

        ti, gi, self.t0_irr = read_series(cfg["irradiance"], base)
        self.t_irr, self.g, self.g_gap = _uniform(ti, np.maximum(gi, 0.0), self.dt)
        tw, vw, self.t0_wind = read_series(cfg["wind"], base)
        self.n_despiked = 0
        if cfg["wind"].get("despike", True):
            vw, self.n_despiked = despike(vw, float(cfg["wind"].get("despike_jump_ms", 3.0)))
        h = float(cfg["wind"].get("height_m", 80.0))
        hub = float(cfg.get("hub_height_m", 80.0))
        vw = vw * (hub / h) ** float(cfg.get("shear_exponent", 0.14))
        self.t_w, self.v, self.v_gap = _uniform(tw, np.maximum(vw, 0.0), self.dt)
        # Ambient temperature: a measured series on the irradiance clock if
        # one is configured, otherwise an explicit, reported assumption.
        self.temp = None
        self.ambient_temp_c = float(cfg.get("ambient_temp_c", 25.0))
        if cfg.get("temperature"):
            tt, vt, t0_temp = read_series(cfg["temperature"], base)
            try:
                shift = float((np.datetime64(self.t0_irr) - np.datetime64(t0_temp))
                              / np.timedelta64(1, "s"))
            except ValueError:
                shift = 0.0          # numeric time columns: assume a common origin
            self.temp = (tt - shift, vt)   # temperature time on the irradiance clock

        g, v = self.g, self.v
        day = g > 50.0
        self.g_hi = float(np.quantile(g[day], 0.90)) if day.any() else 0.0
        hc = int(round(CLOUD_HORIZON_S / self.dt))
        hw = int(round(WIND_HORIZON_S / self.dt))

        # scores
        g_now, g_fut = g[:-hc], g[hc:]
        cloud = np.full(len(g), -np.inf)
        cloud[:-hc] = np.where(g_now > 0.5 * self.g_hi, (g_now - g_fut) / np.maximum(g_now, 1.0), -np.inf)
        wfall = np.full(len(v), -np.inf)
        wfall[:-hw] = np.where(v[:-hw] > 4.0, v[:-hw] - v[hw:], -np.inf)
        # steadiness of irradiance over a window: -coefficient of variation
        cs, cs2 = np.cumsum(np.r_[0, g]), np.cumsum(np.r_[0, g * g])
        m = (cs[win:] - cs[:-win]) / win
        sd = np.sqrt(np.maximum((cs2[win:] - cs2[:-win]) / win - m * m, 0.0))
        steady = np.full(len(g), -np.inf)
        steady[:len(m)] = np.where(m > 0.6 * self.g_hi, -sd / np.maximum(m, 1.0), -np.inf)
        night = np.full(len(g), -np.inf)
        dark = np.convolve((g < 5.0).astype(float), np.ones(win), "valid") == win
        night[:len(dark)] = np.where(dark, 0.0, -np.inf)

        def starts(idx_list, aligned):
            return [i - lead if aligned else i for i in idx_list]

        ok_g = lambda s: _window_ok(self.g_gap, s, win)
        ok_v = lambda s: _window_ok(self.v_gap, s, win)
        self.cand = {}
        rg = _split_ranges(self.g_gap, frac)
        rv = _split_ranges(self.v_gap, frac)
        rng = np.random.default_rng(0)
        for sp in SPLITS:
            lo, hi = rg[sp]
            lov, hiv = rv[sp]
            valid_g = np.isfinite(cloud)
            c_cloud = [s for s in starts(_top_events(cloud, valid_g, win, 4 * N_CANDIDATES, lo, hi), True) if ok_g(s)][:N_CANDIDATES]
            c_clear = [s for s in _top_events(steady, np.isfinite(steady), win, 4 * N_CANDIDATES, lo, hi) if ok_g(s)][:N_CANDIDATES]
            c_night = [s for s in _top_events(night + rng.uniform(0, 1, len(night)), np.isfinite(night), win, 4 * N_CANDIDATES, lo, hi) if ok_g(s)][:N_CANDIDATES]
            c_wdrop = [s for s in starts(_top_events(wfall, np.isfinite(wfall), win, 4 * N_CANDIDATES, lov, hiv), True) if ok_v(s)][:N_CANDIDATES]
            any_v = np.arange(lov, max(lov + 1, hiv - win), max(win, 1))
            c_wind = [int(s) for s in rng.permutation(any_v) if ok_v(int(s)) and v[s:s + win].mean() > 3.0][:N_CANDIDATES]
            self.cand[sp] = dict(cloud=c_cloud, clear=c_clear, night=c_night,
                                 wind_drop=c_wdrop, wind_any=c_wind)

    # ------------------------------------------------------------
    def window(self, scenario: str, split: str, rank: int):
        """(irr, wind, info) on the 1 s analysis grid for one candidate."""
        cd, win = self.cand[split], self.win

        def pick(key, r):
            lst = cd[key]
            if not lst:
                return None
            return lst[r % len(lst)]

        if scenario == "clear":
            sg, sv = pick("clear", rank), pick("wind_any", rank)
        elif scenario == "cloud":
            sg, sv = pick("cloud", rank), pick("wind_any", rank)
        elif scenario == "wind_drop":
            sg, sv = pick("clear", rank), pick("wind_drop", rank)
        elif scenario == "night":
            sg, sv = pick("night", rank), pick("wind_any", rank)
        else:   # combined
            sg, sv = pick("cloud", rank), pick("wind_drop", rank)
        if scenario != "night" and sg is None:
            raise RuntimeError(f"no '{scenario}' irradiance window found in the {split} split")
        if sv is None:
            raise RuntimeError(f"no wind window found in the {split} split")
        irr = np.zeros(win) if sg is None else self.g[sg:sg + win].copy()
        wind = self.v[sv:sv + win].copy()
        return irr, wind, dict(irr_start_s=None if sg is None else float(self.t_irr[sg]),
                               wind_start_s=float(self.t_w[sv]))

    def summary(self) -> dict:
        return {sp: {k: len(v) for k, v in d.items()} for sp, d in self.cand.items()}


def get_record(cfg_path: str | None = None) -> MeasuredRecord:
    cfg_path = cfg_path or C.MEASURED_CONFIG
    key = (os.path.abspath(cfg_path), C.EPISODE_DURATION)
    if key not in _CACHE:
        _CACHE[key] = MeasuredRecord(cfg_path)
    return _CACHE[key]


# ----------------------------------------------------------------
# Scenario generator used by the environment
# ----------------------------------------------------------------
class MeasuredWeatherScenarios(WeatherScenarios):
    """Scenario windows cut from the measured record, at their MEASURED levels.

    Nothing is rescaled by default: irradiance and wind are exactly what the
    instruments recorded (after the despiking and height correction set in
    dataset.json).  Ambient temperature comes from a measured series when one
    is configured; otherwise the constant ``ambient_temp_c`` (default 25 degC,
    the IEC standard test temperature) is used and must be reported as an
    assumption.

    ``rescale_to_site: true`` is still available for site-transfer studies,
    but then the target levels must be given explicitly under ``site_levels``
    in dataset.json together with their source; there is no hidden default.
    """

    def __init__(self, dt=None, duration=None):
        super().__init__(None, dt=dt, duration=duration)
        self.rec = get_record()
        cfg = self.rec.cfg
        self.rescale = bool(cfg.get("rescale_to_site", False))
        if self.rescale:
            lv = cfg.get("site_levels")
            need = {"irr", "wind", "wind_before", "night_wind", "source"}
            if not lv or not need <= set(lv):
                raise ValueError("rescale_to_site=true requires site_levels with keys "
                                 f"{sorted(need)} (including their data source) in dataset.json")
            self.lv = lv
        self.source = "measured"

    def _to_control_grid(self, x):
        t_src = np.arange(len(x)) * self.rec.dt
        return np.interp(self.t, t_src, x)

    def _temperature(self, info, n):
        rec = self.rec
        if rec.temp is None or info.get("irr_start_s") is None:
            return np.full(n, rec.ambient_temp_c)
        tt, vt = rec.temp
        return np.interp(info["irr_start_s"] + np.arange(n) * rec.dt, tt, vt)

    def get(self, name: str, stochastic: bool = False, rng=None, split: str = "test"):
        rng = rng or np.random.default_rng()
        rank = int(rng.integers(0, N_CANDIDATES)) if stochastic else 0
        irr, wind, info = self.rec.window(name, split, rank)
        temp = self._temperature(info, len(irr))
        if self.rescale:
            lead = max(1, int(round(EVENT_AT * len(irr))))
            lv = self.lv
            if irr.max() > 0:
                irr = irr * lv["irr"] / max(irr[:lead].mean(), 1.0)
            target = {"wind_drop": lv["wind_before"], "combined": lv["wind_before"],
                      "night": lv["night_wind"]}.get(name, lv["wind"])
            wind = wind * target / max(wind[:lead].mean(), 0.5)
        irr = np.clip(self._to_control_grid(irr), 0.0, 1400.0)
        wind = np.clip(self._to_control_grid(wind), 0.0, 40.0)
        temp = self._to_control_grid(temp)
        turb = self._const(0.0)      # measured wind already carries its turbulence
        return irr, temp, wind, turb


# ----------------------------------------------------------------
# CLI: inspect what was detected
# ----------------------------------------------------------------
def _check(cfg_path, out_png):
    rec = get_record(cfg_path)
    print(f"irradiance: {len(rec.g)} samples at {rec.dt} s  (record start {rec.t0_irr}); "
          f"daytime P90 = {rec.g_hi:.0f} W/m2")
    print(f"wind:       {len(rec.v)} samples at {rec.dt} s  (record start {rec.t0_wind}); "
          f"{rec.n_despiked} isolated spikes removed")
    print("candidate windows per split:")
    for sp, d in rec.summary().items():
        print(f"  {sp:<5}  " + "  ".join(f"{k}={n}" for k, n in d.items()))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    w = MeasuredWeatherScenarios()
    fig, axes = plt.subplots(2, 5, figsize=(18, 6), sharex=True)
    for j, sc in enumerate(C.EVAL_SCENARIOS):
        irr, _, wind, _ = w.get(sc, stochastic=False, split="test")
        axes[0, j].plot(w.t, irr, color=C.COLORS["solar"])
        axes[1, j].plot(w.t, wind, color=C.COLORS["wind"])
        axes[0, j].set_title(f"{C.SCENARIO_LABELS[sc]} (test window)")
        axes[1, j].set_xlabel("Time (s)")
    axes[0, 0].set_ylabel("Irradiance (W/m²)")
    axes[1, 0].set_ylabel("Hub wind (m/s)")
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    print(f"preview of the five test scenarios: {out_png}")


def _cli():
    ap = argparse.ArgumentParser(description="Measured weather data tool")
    ap.add_argument("--check", action="store_true", help="detect windows and plot the test scenarios")
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", default=os.path.join("results", "measured_preview.png"))
    args = ap.parse_args()
    if args.config:
        C.MEASURED_CONFIG = args.config
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    if args.check:
        _check(C.MEASURED_CONFIG, args.out)


if __name__ == "__main__":
    _cli()
