"""Steady-state resource → power conversion (hourly), used to set each
episode's operating point from real ERA5 / NASA POWER data."""
from __future__ import annotations

import numpy as np
import pandas as pd

RHO_STD = 1.225


class WindPowerCurve:
    """Generic pitch-regulated turbine curve (normalised cubic between cut-in and
    rated), or a manufacturer curve from CSV (wind_speed_ms, power_mw).
    Air density correction per IEC 61400-12-1: v_eq = v·(rho/1.225)^(1/3)."""

    def __init__(self, rated_mw, cut_in_ms=3.0, rated_speed_ms=12.0, cut_out_ms=25.0, curve_csv=None):
        self.rated_mw = float(rated_mw)
        self.cut_in, self.v_rated, self.cut_out = cut_in_ms, rated_speed_ms, cut_out_ms
        self._table = None
        if curve_csv:
            tab = pd.read_csv(curve_csv)
            self._table = (tab.iloc[:, 0].to_numpy(float), tab.iloc[:, 1].to_numpy(float))
            self.rated_mw = float(self._table[1].max())

    def __call__(self, v, rho=RHO_STD):
        v = np.asarray(v, dtype=float) * (np.asarray(rho, dtype=float) / RHO_STD) ** (1.0 / 3.0)
        if self._table is not None:
            p = np.interp(v, *self._table, left=0.0, right=0.0)
            return np.where(v > self._table[0].max(), 0.0, p)
        x = (v**3 - self.cut_in**3) / (self.v_rated**3 - self.cut_in**3)
        p = self.rated_mw * np.clip(x, 0.0, 1.0)
        return np.where((v < self.cut_in) | (v >= self.cut_out), 0.0, p)

    def scalar(self, v, rho=RHO_STD):
        """Fast scalar version for the inner simulation loop."""
        v = v * (rho / RHO_STD) ** (1.0 / 3.0)
        if self._table is not None:
            return float(self(v))
        if v < self.cut_in or v >= self.cut_out:
            return 0.0
        if v >= self.v_rated:
            return self.rated_mw
        return self.rated_mw * (v**3 - self.cut_in**3) / (self.v_rated**3 - self.cut_in**3)


def pv_power_mw(ghi_wm2, t_amb_c, rated_mw, temp_coeff=-0.004, noct_c=45.0, derate=0.90):
    """Available (MPP) PV power. NOCT cell-temperature model, linear temperature
    derating, horizontal-plane irradiance as a proxy for plane-of-array."""
    ghi = np.clip(np.asarray(ghi_wm2, dtype=float), 0.0, None)
    t_cell = np.asarray(t_amb_c, dtype=float) + (noct_c - 20.0) / 800.0 * ghi
    p = rated_mw * derate * (ghi / 1000.0) * (1.0 + temp_coeff * (t_cell - 25.0))
    return np.clip(p, 0.0, rated_mw)


# Normalised 24-h demand shape (mixed residential/commercial feeder, 0..1).
_DEFAULT_SHAPE = np.array([0.42, 0.37, 0.34, 0.33, 0.35, 0.42, 0.55, 0.68, 0.76, 0.80, 0.82, 0.84,
                           0.83, 0.82, 0.80, 0.79, 0.81, 0.88, 0.97, 1.00, 0.95, 0.83, 0.67, 0.52])


def synthetic_load_mw(index_utc: pd.DatetimeIndex, peak_mw, min_mw, utc_offset_h=0.0, seed=0):
    """Deterministic load profile: daily shape + weekend dip + seasonal swing + AR(1) noise.
    Used only when no measured load CSV is supplied (documented assumption)."""
    rng = np.random.default_rng(seed)
    local = index_utc + pd.to_timedelta(utc_offset_h, unit="h")
    hours = local.hour.to_numpy() + local.minute.to_numpy() / 60.0
    shape = np.interp(hours, np.arange(25), np.r_[_DEFAULT_SHAPE, _DEFAULT_SHAPE[0]])
    weekend = np.where(local.dayofweek.to_numpy() >= 5, 0.92, 1.0)
    season = 1.0 + 0.08 * np.cos(2 * np.pi * (local.dayofyear.to_numpy() - 200) / 365.25)
    noise = np.zeros(len(index_utc))
    e = rng.normal(0, 0.03, len(index_utc))
    for i in range(1, len(noise)):
        noise[i] = 0.8 * noise[i - 1] + e[i]
    x = np.clip(shape * weekend * season * (1 + noise), 0.0, 1.1)
    return min_mw + (peak_mw - min_mw) * np.clip(x, 0, 1)
