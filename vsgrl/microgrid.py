"""RMS (average-value) frequency-dynamics model of the PV-Wind-BESS-Diesel
microgrid with a grid-forming Virtual Synchronous Generator (VSG).

Two voltage-source "machines" share the load bus through synchronising
coefficients: the diesel synchronous generator (K_d) and the VSG-controlled
BESS/PV inverter (K_s). Wind and the de-loaded PV base output are
grid-following constant-power injections. All powers in per-unit of S_base
(2 MVA); frequencies in per-unit of f_0. See docs/METHODOLOGY.md §2.

  Network (algebraic, incremental around the dispatch point):
      ΔP_net = ΔP_L − ΔP_w + D_L P_L0 Δω_b
      P_v  = K_s (K_d δ + ΔP_net) / (K_d + K_s)        δ = θ_v − θ_d
      ΔP_e,d = ΔP_net − P_v
      Δω_b = (K_d Δω_d + K_s Δω_v) / (K_d + K_s)       bus frequency
  Diesel SG:   2 H_d dΔω_d/dt = ΔP_m − ΔP_e,d − D_d (Δω_d − Δω_b)
               P_ref = P_d0 − Δω_b/R + x_agc,  dx_agc/dt = −K_i Δω_b
               T_g dP_gov/dt = P_ref − P_gov,  T_e dP_m/dt = P_gov − P_m (ramp-limited)
  VSG:         2 H_v dΔω_v/dt = − P_v − D_v Δω_v
               dδ/dt = ω_0 (Δω_v − Δω_d)
  Headroom:    P_v ∈ [−(P_ch,max(SoC) + P_b0) + P_pv,s ,  P_dis,max(SoC) − P_b0 + P_pv,s]
               (current-limited: VSG becomes a current source, angle anti-windup)
  Allocation:  T_pv dP_pv,s/dt = clip(α P_v,req, −P_pv,0, h_pv) − P_pv,s
               P_bess = P_b0 + P_v − P_pv,s
  Wind:        v = v_hub (1 + TI·n_OU),  T_r dP_w/dt = min(P_curve(v, ρ), cap) − P_w

Integration: symplectic (semi-implicit) Euler, dt = 2 ms.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from .components.resources import WindPowerCurve, pv_power_mw


@dataclass
class Scenario:
    """One disturbance episode at a real-data operating point."""
    time_utc: str
    ws_hub_ms: float
    rho_kgm3: float
    p_pv_mpp_mw: float
    load_mw: float
    soc0: float
    dist_mw: float          # + load increase (under-frequency), − load rejection
    dist_time_s: float
    noise_seed: int
    split: str = "train"

    def to_dict(self):
        return asdict(self)


class Microgrid:
    def __init__(self, cfg: dict, wind_curve: WindPowerCurve):
        s = cfg["system"]
        self.cfg = cfg
        self.curve = wind_curve
        self.f0 = s["f_nominal_hz"]
        self.w0 = 2.0 * math.pi * self.f0
        self.Sb = s["s_base_mva"]
        self.dt = cfg["env"]["sim_dt_s"]

        d = s["diesel"]
        self.Pd_rat = d["rated_mw"] / self.Sb
        self.inv_R = (1.0 / d["droop"]) * self.Pd_rat
        self.Tg, self.Te = d["governor_time_s"], d["engine_time_s"]
        self.Pd_min = d["min_load_frac"] * self.Pd_rat
        self.Pd_disp_max = d["max_dispatch_frac"] * self.Pd_rat
        self.ramp = d["ramp_pu_per_s"] * self.Pd_rat
        self.Ki = d["secondary_ki"]
        self.H_d = d["inertia_h_s"] * d["rated_mw"] / self.Sb
        self.D_d = d["damping_pu"] * self.Pd_rat
        self.Kd = d["sync_coeff_pu"]

        b = s["bess"]
        self.Pb_max = b["power_mw"] / self.Sb
        self.Eb = b["energy_mwh"]
        self.soc_min, self.soc_max, self.soc_taper = b["soc_min"], b["soc_max"], b["soc_taper"]
        self.eta_c, self.eta_d = b["eta_charge"], b["eta_discharge"]

        p = s["pv"]
        self.pv_cfg = p
        self.deload = p["deload_fraction"]
        self.Tpv = max(p["response_time_s"], self.dt)

        w = s["wind"]
        self.TI = w["turbulence_intensity"]
        self.Tturb = w["turbulence_time_constant_s"]
        self.Trot = max(w["rotor_smoothing_s"], self.dt)

        self.DL = s["load"]["damping_pu"]
        self.load_noise = s["load"]["noise_frac"]

        v = s["vsg"]
        self.Ks = v["sync_coeff_pu"]
        self.Tf = max(v["measurement_filter_s"], self.dt)
        self.T_gfl = max(v.get("gfl_response_s", 0.05), self.dt)

    # ------------------------------------------------------------------ setup
    def bess_limits(self, soc):
        dis = self.Pb_max * min(max((soc - self.soc_min) / self.soc_taper, 0.0), 1.0)
        ch = self.Pb_max * min(max((self.soc_max - soc) / self.soc_taper, 0.0), 1.0)
        return dis, ch

    def reset(self, sc: Scenario, episode_s: float):
        Sb = self.Sb
        self.sc = sc
        self.t = 0.0
        p_w_av = self.curve.scalar(sc.ws_hub_ms, sc.rho_kgm3) / Sb
        mpp = sc.p_pv_mpp_mw / Sb
        pv_base = (1.0 - self.deload) * mpp
        headroom = self.deload * mpp
        load = sc.load_mw / Sb
        soc = sc.soc0
        dis_max, _ = self.bess_limits(soc)

        # --- economic dispatch at the operating point ---------------------
        wind_cap = p_w_av
        pb0 = 0.0
        self.load_clipped = 0.0
        residual = load - p_w_av - pv_base
        if residual < self.Pd_min:                      # RES surplus: curtail wind, then PV
            cut = self.Pd_min - residual
            wcut = min(cut, p_w_av)
            wind_cap = p_w_av - wcut
            cut -= wcut
            if cut > 0:
                pcut = min(cut, pv_base)
                pv_base -= pcut
                headroom += pcut                        # curtailed PV is extra upward headroom
                cut -= pcut
            if cut > 0:                                 # still surplus: raise load to diesel min (document)
                load += cut
                self.load_clipped = -cut
            residual = self.Pd_min
        if residual > self.Pd_disp_max:                 # deficit: BESS base discharge, then clip load
            deficit = residual - self.Pd_disp_max
            pb0 = min(deficit, 0.6 * dis_max)
            rest = deficit - pb0
            load -= rest
            self.load_clipped = rest
            residual = self.Pd_disp_max + pb0
        pd0 = residual - pb0

        self.p_w_av0, self.wind_cap, self.pv_base, self.h_pv = p_w_av, wind_cap, pv_base, headroom
        self.pv_mpp = mpp
        self.load0 = load
        self.pb0 = pb0
        self.pd0 = pd0
        self.dist = sc.dist_mw / Sb
        self.dist_t = sc.dist_time_s

        # --- states --------------------------------------------------------
        self.dw_d = 0.0
        self.dw_v = 0.0
        self.dw_b = 0.0
        self.delta = 0.0
        self.p_vsg = 0.0
        self.p_pv_s = 0.0
        self.p_gfl = 0.0
        self.p_gov = pd0
        self.p_d = pd0
        self.x_agc = 0.0
        self.soc = soc
        self.p_w0 = min(p_w_av, wind_cap)
        self.p_w = self.p_w0
        self.f_meas = 0.0
        self.rocof_meas = 0.0
        self.sat = 0.0

        # --- pre-generated stochastic signals (deterministic per scenario) --
        n = int(round(episode_s / self.dt)) + 2
        rng = np.random.default_rng(sc.noise_seed)
        self._turb = self._ou(rng, n, self.Tturb)
        self._lnoise = self._ou(rng, n, 1.0)
        self._k = 0

    def _ou(self, rng, n, tau):
        a = math.exp(-self.dt / tau)
        e = rng.normal(0.0, math.sqrt(1 - a * a), n)
        x = np.empty(n)
        x[0] = 0.0
        for i in range(1, n):
            x[i] = a * x[i - 1] + e[i]
        return x

    # -------------------------------------------------------------- headroom
    def headroom_up(self):
        """Fast upward reserve the VSG can actually deliver now (S_base pu)."""
        dis, _ = self.bess_limits(self.soc)
        return max(dis - self.pb0, 0.0) + self.h_pv

    def headroom_down(self):
        _, ch = self.bess_limits(self.soc)
        return max(ch + self.pb0, 0.0) + self.pv_base

    # ------------------------------------------------------------- dynamics
    def advance(self, H_v, D_v, alpha, n_steps, mode="vsg", trace=None):
        """Integrate n_steps of dt with fixed controller parameters.

        mode = "vsg"   grid-forming VSG with (H_v, D_v, alpha)
               "droop" grid-following BESS/PV droop  P = −D_v Δf_meas (no inertia), lag T_gfl
               "none"  no fast frequency support (diesel only)
        Returns interval statistics used by the reward."""
        vsg_on = mode == "vsg"
        droop_on = mode == "droop"
        dt, w0, Sb = self.dt, self.w0, self.Sb
        Kd = self.Kd
        Ks = self.Ks if vsg_on else 0.0
        Ksum = Kd + Ks
        H2d, H2v = 2.0 * self.H_d, 2.0 * max(H_v, 1e-3)
        DLP = self.DL * self.load0
        gc = self.cfg["system"]["grid_code"]
        f_lim, r_lim = gc["f_dev_limit_hz"] / self.f0, gc["rocof_limit_hz_s"] / self.f0
        sum_f2 = sum_r2 = sum_pb2 = sum_sat = 0.0
        n_viol = 0
        for _ in range(n_steps):
            k = self._k
            t = self.t
            # --- exogenous inputs
            v = self.sc.ws_hub_ms * (1.0 + self.TI * self._turb[k])
            pw_t = min(self.curve.scalar(max(v, 0.0), self.sc.rho_kgm3) / Sb, self.wind_cap)
            load = self.load0 * (1.0 + self.load_noise * self._lnoise[k])
            if t >= self.dist_t:
                load += self.dist

            # --- network solution and headroom-limited VSG power
            dP = (load - self.load0) - (self.p_w - self.p_w0) + DLP * self.f_meas
            dis, ch = self.bess_limits(self.soc)
            hi = dis - self.pb0 + self.p_pv_s
            lo = -(ch + self.pb0) + self.p_pv_s
            if vsg_on:
                pv_req = Ks * (Kd * self.delta + dP) / Ksum
                pv = min(max(pv_req, lo), hi)
                sat = abs(pv_req - pv)
            elif droop_on:
                pv_req = -D_v * self.f_meas
                self.p_gfl += dt * (pv_req - self.p_gfl) / self.T_gfl
                pv = min(max(self.p_gfl, lo), hi)
                sat = abs(self.p_gfl - pv)
            else:
                pv_req = pv = sat = 0.0
            pd_e = dP - pv                               # incremental diesel electrical power

            # --- rotor velocities first (symplectic Euler)
            acc_d = (self.p_d - self.pd0 - pd_e - self.D_d * (self.dw_d - self.dw_b)) / H2d
            self.dw_d += dt * acc_d
            if vsg_on:
                self.dw_v += dt * (-pv - D_v * self.dw_v) / H2v
                self.delta += dt * w0 * (self.dw_v - self.dw_d)
                if sat > 0.0:                            # current limit: angle anti-windup
                    self.delta = (pv * Ksum / Ks - dP) / Kd
                    self.dw_v = self.dw_d
                    self.dw_b = self.dw_d
                else:
                    self.dw_b = (Kd * self.dw_d + Ks * self.dw_v) / Ksum
                pv_tgt = min(max(alpha * pv_req, -self.pv_base), self.h_pv)
                self.p_pv_s += dt * (pv_tgt - self.p_pv_s) / self.Tpv
            else:
                self.dw_v = self.dw_b = self.dw_d
                if droop_on:
                    pv_tgt = min(max(alpha * pv_req, -self.pv_base), self.h_pv)
                    self.p_pv_s += dt * (pv_tgt - self.p_pv_s) / self.Tpv
                else:
                    self.p_pv_s = 0.0
            self.p_vsg = pv

            # --- diesel governor (droop) + AGC
            p_ref = self.pd0 - self.inv_R * self.f_meas + self.x_agc
            self.x_agc -= dt * self.Ki * self.f_meas
            self.p_gov += dt * (p_ref - self.p_gov) / self.Tg
            self.p_gov = min(max(self.p_gov, 0.0), self.Pd_rat)
            dpd = min(max((self.p_gov - self.p_d) / self.Te, -self.ramp), self.ramp)
            self.p_d = min(max(self.p_d + dt * dpd, 0.0), self.Pd_rat)

            # --- wind electrical power
            self.p_w += dt * (pw_t - self.p_w) / self.Trot

            # --- BESS energy
            p_b = self.pb0 + pv - self.p_pv_s
            p_b_mw = p_b * Sb
            if p_b_mw >= 0.0:
                self.soc -= p_b_mw / self.eta_d / self.Eb * dt / 3600.0
            else:
                self.soc -= p_b_mw * self.eta_c / self.Eb * dt / 3600.0

            # --- bus-frequency measurement (PLL low-pass) and RoCoF
            self.rocof_meas = (self.dw_b - self.f_meas) / self.Tf
            self.f_meas += dt * self.rocof_meas

            # --- statistics
            fm, rm = self.f_meas, self.rocof_meas
            sum_f2 += fm * fm
            sum_r2 += rm * rm
            dpb = p_b - self.pb0
            sum_pb2 += dpb * dpb
            sum_sat += sat
            if abs(fm) > f_lim or abs(rm) > r_lim:
                n_viol += 1
            self.sat = sat
            self._k = k + 1
            self.t = t + dt
            if trace is not None and k % trace["every"] == 0:
                trace["rows"].append((self.t, fm * self.f0, rm * self.f0, self.dw_v * self.f0,
                                      pv * Sb, self.p_pv_s * Sb, p_b_mw, self.p_d * Sb,
                                      self.p_w * Sb, load * Sb, self.soc, sat * Sb, H_v, D_v, alpha))
        n = float(n_steps)
        return {
            "msf_hz2": sum_f2 / n * self.f0 ** 2,
            "msr_hz2s2": sum_r2 / n * self.f0 ** 2,
            "ms_pbess": sum_pb2 / n,
            "mean_sat": sum_sat / n,
            "viol_frac": n_viol / n,
        }

    TRACE_COLUMNS = ["t", "df_hz", "rocof_hz_s", "dfv_hz", "p_vsg_mw", "p_pv_support_mw", "p_bess_mw",
                     "p_diesel_mw", "p_wind_mw", "p_load_mw", "soc", "sat_mw", "H_v", "D_v", "alpha"]
