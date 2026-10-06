"""
Physical component models: solar PV, Type-4 PMSG wind turbine with rotor
dynamics, and a power/energy-limited BESS (discharge positive).
"""
import numpy as np

from .config import (E_BESS_WH, ETA_BESS, PV_DEGRADATION, PV_G_REF, PV_NOCT_RISE,
                     PV_RATED, PV_T_COEFF, PV_T_REF, S_BASE, SOC_MAX, SOC_MIN,
                     WT_H, WT_LAMBDA_OPT, WT_RADIUS, WT_RATED, WT_RHO,
                     WT_TAU_CONV, WT_V_CUTIN, WT_V_CUTOUT, WT_V_RATED)

# ================================================================
# SOLAR PV — BUS 203
# ================================================================
class SolarPV:
    """500 kW PV plant.

        P_pv = P_rated * (G/G_ref) * [1 - Ct (Tcell - Tref)] * eta_deg

    Cell temperature uses the standard NOCT-style linear rise above
    ambient, T_cell = T_amb + k*G, so temperature derating grows
    with irradiance instead of being tied to ambient alone.
    """

    def __init__(self, rated: float = PV_RATED):
        self.P_rated = rated
        self.G_ref = PV_G_REF
        self.T_ref = PV_T_REF
        self.Ct = PV_T_COEFF
        self.degradation = PV_DEGRADATION

    # -- static characteristic ------------------------------------
    def cell_temperature(self, T_amb: float, G: float) -> float:
        return T_amb + PV_NOCT_RISE * G

    def power(self, G: float, T_amb: float = 25.0,
              soiling: float = 1.0) -> float:
        irr_factor = np.clip(G / self.G_ref, 0.0, 1.2)
        T_cell = self.cell_temperature(T_amb, G)
        temp_factor = max(0.0, 1.0 - self.Ct * (T_cell - self.T_ref))
        p = self.P_rated * irr_factor * temp_factor * soiling * self.degradation
        return float(np.clip(p, 0.0, self.P_rated))

    # -- daily profiles (used by Graph 1) -------------------------
    @staticmethod
    def daily_irradiance(hour: float, season: str = "summer") -> float:
        if hour < 5.0 or hour > 21.0:
            return 0.0
        p = {
            "summer": (1050.0, 13.5, 3.8),
            "winter": (750.0, 12.5, 3.0),
            "spring": (900.0, 13.0, 3.5),
            "autumn": (800.0, 12.8, 3.2),
        }.get(season, (1050.0, 13.5, 3.8))
        peak, centre, sigma = p
        return float(peak * np.exp(-0.5 * ((hour - centre) / sigma) ** 2))

    @staticmethod
    def daily_temperature(hour: float, season: str = "summer") -> float:
        T_min, T_max = {
            "summer": (18.0, 38.0),
            "winter": (5.0, 18.0),
            "spring": (10.0, 25.0),
            "autumn": (8.0, 22.0),
        }.get(season, (18.0, 38.0))
        phase = np.pi * (hour - 6.0) / 14.0
        return float(T_min + (T_max - T_min) * max(0.0, np.sin(phase)) ** 1.5)


# ================================================================
# WIND TURBINE — BUS 204 (Type-4 PMSG)
# ================================================================
class WindTurbine:
    """500 kW variable-speed turbine with rotor dynamics.

    Mechanical power       P_m   = 0.5 rho pi R^2 Cp(lam,beta) v^3
    Tip-speed ratio        lam   = omega_r R / v
    Rotor swing            2H dw/dt = (T_m - T_e)/T_base
    MPPT torque control    T_e*  = k_opt omega_r^2   (below rated)
    Converter lag          T_e   tracks T_e* with time constant tau

    Above rated wind speed the pitch controller (simple proportional
    law on rotor over-speed) feathers beta to hold rated power.
    """

    def __init__(self, rated: float = WT_RATED):
        self.P_rated = rated
        self.rho = WT_RHO
        self.R = WT_RADIUS
        self.A = np.pi * self.R ** 2
        self.v_in, self.v_rated, self.v_out = WT_V_CUTIN, WT_V_RATED, WT_V_CUTOUT
        self.lambda_opt = WT_LAMBDA_OPT
        self.H = WT_H

        self.cp_max = self.cp(self.lambda_opt, 0.0)
        # k_opt such that T_e = k_opt w^2 sits exactly on the MPPT locus
        self.k_opt = (0.5 * self.rho * self.A * self.R ** 3
                      * self.cp_max / self.lambda_opt ** 3)

        # rated operating point (used as the torque base)
        self.omega_rated = self.lambda_opt * self.v_rated / self.R
        self.T_base = self.P_rated / self.omega_rated

        self.reset()

    # -- states ---------------------------------------------------
    def reset(self, v0: float = 10.0) -> None:
        v0 = float(np.clip(v0, self.v_in, self.v_out))
        self.omega_r = float(np.clip(self.lambda_opt * v0 / self.R,
                                     0.3 * self.omega_rated,
                                     1.2 * self.omega_rated))
        self.beta = 0.0
        self.P_e = self.power_static(v0)

    # -- aerodynamics ---------------------------------------------
    @staticmethod
    def cp(lam: float, beta: float = 0.0) -> float:
        """Slootweg et al. (2003) Cp(lambda, beta) curve."""
        if lam <= 0.0:
            return 0.0
        inv_li = 1.0 / (lam + 0.08 * beta) - 0.035 / (beta ** 3 + 1.0)
        if inv_li <= 0.0:
            return 0.0
        li = 1.0 / inv_li
        val = 0.5176 * (116.0 / li - 0.4 * beta - 5.0) * np.exp(-21.0 / li) \
            + 0.0068 * lam
        return float(np.clip(val, 0.0, 0.48))

    def power_static(self, v: float, beta: float = 0.0) -> float:
        """Steady-state (perfect-MPPT) power — used for power curves."""
        v = float(v)
        if v < self.v_in or v > self.v_out:
            return 0.0
        p = 0.5 * self.rho * self.A * self.cp(self.lambda_opt, beta) * v ** 3
        return float(np.clip(p, 0.0, self.P_rated))

    # -- dynamic step ---------------------------------------------
    def step(self, v: float, dt: float) -> float:
        """Advance the rotor one step, return electrical power (W)."""
        v = float(max(v, 0.1))
        if v < self.v_in or v > self.v_out:
            # cut out: torque to zero, rotor coasts down
            self.P_e += (0.0 - self.P_e) * dt / WT_TAU_CONV
            self.omega_r = max(0.05 * self.omega_rated,
                               self.omega_r - 0.5 * dt)
            return float(max(0.0, self.P_e))

        lam = self.omega_r * self.R / v
        # pitch controller: feather only when the rotor tries to
        # exceed rated speed (i.e. above rated wind)
        beta_cmd = np.clip(12.0 * (self.omega_r / self.omega_rated - 1.0),
                           0.0, 27.0)
        self.beta += (beta_cmd - self.beta) * dt / 0.30      # pitch servo

        cp = self.cp(lam, self.beta)
        P_m = 0.5 * self.rho * self.A * cp * v ** 3
        T_m = P_m / max(self.omega_r, 1e-3)

        # MPPT torque demand, capped at rated torque
        T_ref = min(self.k_opt * self.omega_r ** 2,
                    self.P_rated / max(self.omega_r, 1e-3))
        T_e = T_ref  # converter torque loop is much faster than dt

        # rotor swing equation in per-unit
        dw = (T_m - T_e) / self.T_base / (2.0 * self.H) * self.omega_rated
        self.omega_r = float(np.clip(self.omega_r + dw * dt,
                                     0.2 * self.omega_rated,
                                     1.25 * self.omega_rated))

        P_target = float(np.clip(T_e * self.omega_r, 0.0, self.P_rated))
        self.P_e += (P_target - self.P_e) * dt / WT_TAU_CONV
        return float(np.clip(self.P_e, 0.0, self.P_rated))

    # -- daily profile (used by Graph 1) --------------------------
    @staticmethod
    def daily_wind_speed(hour: float, season: str = "summer") -> float:
        base, amp, phase = {
            "summer": (6.5, 2.0, 2.0),
            "winter": (9.0, 3.0, 3.0),
            "spring": (7.5, 2.5, 2.0),
            "autumn": (8.0, 2.8, 2.0),
        }.get(season, (6.5, 2.0, 2.0))
        diurnal = amp * np.sin(np.pi * (hour - phase) / 12.0)
        return float(np.clip(base + diurnal + 0.3 * np.sin(2 * np.pi * hour / 24.0),
                             1.5, 20.0))

    @staticmethod
    def turbulence_intensity(v: float) -> float:
        """IEC-style: TI falls with wind speed."""
        if v <= 3.0:
            return 0.18
        if v <= 15.0:
            return float(0.16 - 0.006 * v)
        return 0.07


# ================================================================
# BATTERY ENERGY STORAGE SYSTEM — BUS 202
# ================================================================
class BESS:
    """Power- and energy-limited battery.

    Sign convention: P > 0 = DISCHARGING (injecting into the grid),
    which therefore *reduces* SOC.  (The original script added
    P/S_base*dt to SOC, i.e. discharging charged the battery.)
    """

    def __init__(self, s_rated: float = S_BASE, e_wh: float = E_BESS_WH):
        self.S_rated = s_rated
        self.E_wh = e_wh
        self.eta = np.sqrt(ETA_BESS)
        self.reset()

    def reset(self, soc: float = 0.5) -> None:
        self.soc = float(soc)
        self.P = 0.0
        self.energy_throughput_wh = 0.0

    def available_power(self) -> tuple[float, float]:
        """(max discharge, max charge) in W, respecting SOC limits."""
        p_dis = self.S_rated if self.soc > SOC_MIN else 0.0
        p_chg = -self.S_rated if self.soc < SOC_MAX else 0.0
        return p_dis, p_chg

    def apply(self, p_request: float, dt: float) -> float:
        """Clip request to power/SOC limits, integrate SOC, return
        the power actually delivered (W)."""
        p_dis, p_chg = self.available_power()
        p = float(np.clip(p_request, p_chg, p_dis))

        # discharging is less efficient at the DC side
        if p >= 0.0:
            dE = p / self.eta * dt / 3600.0          # Wh drawn
        else:
            dE = p * self.eta * dt / 3600.0          # Wh stored
        self.soc = float(np.clip(self.soc - dE / self.E_wh, 0.0, 1.0))
        self.energy_throughput_wh += abs(p) * dt / 3600.0
        self.P = p
        return p

    def q_capability(self, p_active: float) -> float:
        """Reactive headroom from the apparent-power circle."""
        return float(np.sqrt(max(self.S_rated ** 2 - p_active ** 2, 0.0)))
