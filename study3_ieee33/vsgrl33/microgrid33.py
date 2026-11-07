"""Islanded IEEE 33-bus microgrid: the Study 2 plant on the published Baran & Wu feeder.

Ieee33Microgrid subclasses the Study 2 Microgrid and keeps its EMS dispatch, BESS limits, PV
de-loading and share, wind model, governor, AGC, secondary control and statistics. Only the
network changes: instead of sharing each imbalance between the diesel and the VSG through two
synchronising coefficients at one bus, the published feeder is solved as a phasor network at every
step, with the diesel EMF behind X_d at bus 1, the VSG EMF behind X_v at bus 18 and PV + wind at
bus 33 (see DESIGN.md)."""
from __future__ import annotations

import math

import numpy as np

from vsgrl.microgrid import Microgrid

from .network import DynamicNetwork, Feeder


SAT_TOL = 1e-6      # pu; exceedances below this are numerical, not saturation


def _wrap(a):
    return (a + math.pi) % (2.0 * math.pi) - math.pi


class Ieee33Microgrid(Microgrid):
    def __init__(self, cfg, wind_curve):
        super().__init__(cfg, wind_curve)
        nw = cfg["system"]["network"]
        self.bus_d, self.bus_v, self.bus_r = nw["bus_diesel"], nw["bus_vsg"], nw["bus_res"]
        self.feeder = Feeder(self.Sb, nw.get("v_base_kv", 12.66))
        self.X_d = 1.0 / self.Kd              # same internal reactances as Study 2 (pu on S_base)
        self.X_v = 1.0 / self.Ks
        self.const_z = nw.get("load_model", "constant_power") == "constant_impedance"
        self.feeder_scale = nw.get("impedance_scale", 1.0)   # 1 = published feeder; ~0 = single-bus limit
        if self.feeder_scale != 1.0:
            self.feeder.Y_lines = self.feeder.Y_lines / max(self.feeder_scale, 1e-9)

    # ------------------------------------------------------------------ setup
    def reset(self, sc, episode_s):
        super().reset(sc, episode_s)                  # Study 2 dispatch: load0, pd0, pb0, p_w0, pv_base, ...
        fd = self.feeder
        gen = {self.bus_v: self.pb0, self.bus_r: self.p_w0 + self.pv_base}
        V0, S1 = fd.load_flow(self.load0, gen)        # constant-power loads, diesel terminal at 1.0 pu
        self.V0 = V0
        self.losses0 = S1.real + sum(gen.values()) - self.load0
        # EMFs behind the internal reactances (diesel supplies the feeder losses as well)
        I_d = np.conj(S1 / V0[self.bus_d - 1])
        S_v = self.pb0 + 0j
        I_v = np.conj(S_v / V0[self.bus_v - 1])
        E_d = V0[self.bus_d - 1] + 1j * self.X_d * I_d
        E_v = V0[self.bus_v - 1] + 1j * self.X_v * I_v
        self.Ed_mag, self.Ev_mag = abs(E_d), abs(E_v)
        self.th_d, self.th_v = math.atan2(E_d.imag, E_d.real), math.atan2(E_v.imag, E_v.real)
        self.net_on = DynamicNetwork(fd, V0, self.load0, self.bus_d, self.bus_v, self.X_d, self.X_v, self.const_z)
        self.net_off = DynamicNetwork(fd, V0, self.load0, self.bus_d, self.bus_v, self.X_d, 1e9, self.const_z)
        self.Pe_d0 = S1.real                          # diesel electrical power incl. feeder losses
        self.p_gov = self.p_d = self.Pe_d0
        self.V = V0.copy()
        self.ang_v_prev = np.angle(V0[self.bus_v - 1])
        self.ang_d_prev = np.angle(V0[self.bus_d - 1])
        self.f_pll = 0.0                              # angle-based frequency at the VSG bus (PLL-like, analysis only)
        self.vmin = float(np.abs(V0).min())

    # ------------------------------------------------------------- dynamics
    def advance(self, H_v, D_v, alpha, n_steps, mode="vsg", trace=None):
        vsg_on = mode == "vsg"
        droop_on = mode == "droop"
        dt, w0, Sb = self.dt, self.w0, self.Sb
        fd = self.feeder
        net = self.net_on if vsg_on else self.net_off
        iv, ir, idd = self.bus_v - 1, self.bus_r - 1, self.bus_d - 1
        share_s = fd.share_p + 1j * fd.qp          # complex load share per bus (published P and Q)
        H2d, H2v = 2.0 * self.H_d, 2.0 * max(H_v, 1e-3)
        DLP = self.DL * self.load0
        gc = self.cfg["system"]["grid_code"]
        f_lim, r_lim = gc["f_dev_limit_hz"] / self.f0, gc["rocof_limit_hz_s"] / self.f0
        f_band = self.cfg["env"]["reward"].get("f_band_hz", 0.0) / self.f0
        r_band = self.cfg["env"]["reward"].get("rocof_band_hz_s", 0.0) / self.f0
        sum_f2 = sum_r2 = sum_pb2 = sum_sat = sum_ef2 = sum_er2 = sum_fast2 = 0.0
        n_viol = 0
        for _ in range(n_steps):
            k = self._k
            t = self.t
            # --- exogenous inputs (as in Study 2)
            v = self.sc.ws_hub_ms * (1.0 + self.TI * self._turb[k])
            pw_t = min(self.curve.scalar(max(v, 0.0), self.sc.rho_kgm3) / Sb, self.wind_cap)
            while self._ev_i < len(self.events) and t >= self.events[self._ev_i][0]:
                self.load_step += self.events[self._ev_i][1]
                self._ev_i += 1
            dload = self.load0 * self.load_noise * self._lnoise[k] + self.load_step
            load_bus = dload + (0.0 if self.const_z else self.load0)   # part of the load entering as injection

            # --- bus current injections (positive into the network), using last step's voltages
            V = self.V
            S_inj = -(load_bus * share_s) - DLP * self.f_meas * fd.share_p
            S_inj[ir] += self.p_w + self.pv_base + self.p_pv_s          # PV and wind at bus 33
            dis, ch = self.bess_limits(self.soc)
            if droop_on:
                pv_req = self.p_set - D_v * self.f_meas
                self.p_gfl += dt * (pv_req - self.p_gfl) / self.T_gfl
                pb_fast = min(max(self.p_gfl - self.p_pv_s, -(ch + self.pb0)), dis - self.pb0)
                sat = abs(self.p_gfl - self.p_pv_s - pb_fast)
                S_inj[iv] += self.pb0 + pb_fast
            elif not vsg_on:
                pv_req = pb_fast = sat = 0.0
                S_inj[iv] += self.pb0
            I_inj = np.conj(S_inj / V)

            # --- network solution
            E = np.array([self.Ed_mag * np.exp(1j * self.th_d), self.Ev_mag * np.exp(1j * self.th_v)])
            V, S_m = net.solve(E, I_inj)
            if vsg_on:
                P_vnet = S_m[1].real                   # BESS power delivered by the grid-forming VSG
                pv_req = P_vnet - self.pb0 + self.p_pv_s   # total fast support asked by the network
                P_lim = min(max(P_vnet, -ch), dis)
                sat = abs(P_vnet - P_lim)
                if sat > SAT_TOL:                      # current limit: move the virtual rotor to the limit
                    for _ in range(4):                 # P = E V sin(th_E - th_V) / X_v, re-solved until on the limit
                        vt = V[iv]
                        s = P_lim * self.X_v / (self.Ev_mag * abs(vt))
                        self.th_v = math.atan2(vt.imag, vt.real) + math.asin(min(max(s, -1.0), 1.0))
                        E[1] = self.Ev_mag * np.exp(1j * self.th_v)
                        V, S_m = net.solve(E, I_inj)
                        P_vnet = S_m[1].real
                        if abs(P_vnet - P_lim) < SAT_TOL:
                            break
                else:
                    sat = 0.0
                pb_fast = P_vnet - self.pb0
            pv = pb_fast + self.p_pv_s                 # total fast support (BESS + PV share)
            Pe_d = S_m[0].real

            # --- angle-based frequency at the VSG bus (PLL-like; recorded for analysis, includes
            #     the phase-jump spikes at load steps that the EMT validation also showed)
            ang_v = math.atan2(V[iv].imag, V[iv].real)
            dw_v_bus = _wrap(ang_v - self.ang_v_prev) / (w0 * dt)
            self.ang_v_prev = ang_v
            self.f_pll += dt * (dw_v_bus - self.f_pll) / self.Tf

            # --- rotors (symplectic Euler); damper and measurement act on the rotor-weighted
            #     frequency dw_b exactly as in Study 2, so that only the network differs
            acc_d = (self.p_d - Pe_d - self.D_d * (self.dw_d - self.dw_b)) / H2d
            self.dw_d += dt * acc_d
            self.th_d += dt * w0 * self.dw_d
            if vsg_on:
                if sat > 0.0:
                    self.dw_v = self.dw_d              # anti-windup as in Study 2
                    self.dw_b = self.dw_d
                else:
                    self.dw_v += dt * (self.p_set - pv - D_v * self.dw_v) / H2v
                    self.dw_b = (self.Kd * self.dw_d + self.Ks * self.dw_v) / (self.Kd + self.Ks)
                self.th_v += dt * w0 * self.dw_v
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
            self.V = V

            # --- diesel governor (droop) + AGC on the measured frequency, as in Study 2
            p_ref = self.Pe_d0 - self.inv_R * self.f_meas + self.x_agc
            self.x_agc -= dt * self.Ki * self.f_meas
            if self.Ki_b > 0.0 and (vsg_on or droop_on):
                lo, hi = -(ch + self.pb0) + self.p_pv_s, dis - self.pb0 + self.p_pv_s
                self.p_set = min(max(self.p_set - dt * self.Ki_b * self.f_meas, lo), hi)
            self.p_gov += dt * (p_ref - self.p_gov) / self.Tg
            self.p_gov = min(max(self.p_gov, 0.0), self.Pd_rat)
            dpd = min(max((self.p_gov - self.p_d) / self.Te, -self.ramp), self.ramp)
            self.p_d = min(max(self.p_d + dt * dpd, 0.0), self.Pd_rat)

            # --- wind electrical power
            self.p_w += dt * (pw_t - self.p_w) / self.Trot

            # --- BESS energy
            p_b = self.pb0 + pb_fast
            p_b_mw = p_b * Sb
            if p_b_mw >= 0.0:
                self.soc -= p_b_mw / self.eta_d / self.Eb * dt / 3600.0
            else:
                self.soc -= p_b_mw * self.eta_c / self.Eb * dt / 3600.0

            # --- measured frequency (20 ms filter of dw_b, as in Study 2) and RoCoF
            self.rocof_meas = (self.dw_b - self.f_meas) / self.Tf
            self.f_meas += dt * self.rocof_meas

            # --- statistics (as in Study 2)
            fm, rm = self.f_meas, self.rocof_meas
            sum_f2 += fm * fm
            sum_r2 += rm * rm
            ef = abs(fm) - f_band
            if ef > 0.0:
                sum_ef2 += ef * ef
            er = abs(rm) - r_band
            if er > 0.0:
                sum_er2 += er * er
            dpb = p_b - self.pb0
            sum_pb2 += dpb * dpb
            fast = pv - self.p_set
            sum_fast2 += fast * fast
            sum_sat += sat
            if abs(fm) > f_lim or abs(rm) > r_lim:
                n_viol += 1
            self.sat = sat
            vm = np.abs(V)
            self.vmin = min(self.vmin, float(vm.min()))
            self._k = k + 1
            self.t = t + dt
            if trace is not None and k % trace["every"] == 0:
                trace["rows"].append((self.t, fm * self.f0, rm * self.f0, self.dw_v * self.f0,
                                      pv * Sb, self.p_pv_s * Sb, p_b_mw, self.p_d * Sb,
                                      self.p_w * Sb, (self.load0 + dload) * Sb, self.soc, sat * Sb, H_v, D_v, alpha,
                                      self.p_set * Sb,
                                      (self.headroom_up() if fm <= 0.0 else self.headroom_down()) * Sb))
        n = float(n_steps)
        return {
            "msf_hz2": sum_f2 / n * self.f0 ** 2,
            "msr_hz2s2": sum_r2 / n * self.f0 ** 2,
            "msf_excess_hz2": sum_ef2 / n * self.f0 ** 2,
            "msr_excess_hz2s2": sum_er2 / n * self.f0 ** 2,
            "ms_pbess": sum_pb2 / n,
            "ms_pfast": sum_fast2 / n,
            "mean_sat": sum_sat / n,
            "viol_frac": n_viol / n,
        }
