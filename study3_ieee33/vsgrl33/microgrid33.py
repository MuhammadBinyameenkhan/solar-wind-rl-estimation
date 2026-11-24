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

from .avr import AC8C
from .network import DynamicNetwork, DynamicNetworkVC, Feeder


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
        # ---- voltage control (DESIGN.md): salient-pole diesel with IEEE 421.5 AC8C AVR, VSG Q-V droop (UNIFI v3)
        self.vc = bool(nw.get("voltage_control", False))
        # PV / wind active-power support: "vsg_share" = Study 2 PV share alpha (PV in the virtual unit);
        # "ieee1547_droop" = IEEE 1547-2018 frequency droop at the RES inverters, independent of the VSG
        # (author decision 18 Nov 2026; on the feeder the alpha loop between buses 33 and 18 is unstable).
        self.res_droop = nw.get("res_support", "vsg_share") == "ieee1547_droop"
        if self.res_droop:
            fdp = cfg["system"]["res_freq_droop"]
            self.fd_db = fdp["deadband_hz"] / fdp["standard_f_nom_hz"]     # per-unit deadband
            self.fd_k = fdp["droop"]
            self.fd_tau = fdp["olrt_s"] / 2.3
            self.P_pv_np = cfg["system"]["pv"]["rated_mw"] / self.Sb
            self.P_w_np = cfg["system"]["wind"]["rated_mw"] / self.Sb
        if self.vc:
            d = cfg["system"]["diesel"]
            m = d["machine"]
            to_sys = self.Sb / m["rated_mva"]                     # machine pu -> system pu (ideal step-up transformer)
            self.Xd_s, self.Xq_s, self.Xdp_s = m["xd"] * to_sys, m["xq"] * to_sys, m["xdp"] * to_sys
            self.Tdo = m["tdo_s"]
            self.avr_cfg = d["avr"]
            v = cfg["system"]["vsg"]
            self.mQ = v["q_droop_mq"]                              # pu voltage per pu reactive power (own rating)
            b = cfg["system"]["bess"]
            self.S_conv = b["power_mw"] * math.sqrt(1.0 + v["q_capability_frac"] ** 2)   # MVA
            # PV and wind inverters: IEEE 1547-2018 Category B volt-var (defaults as in EPRI OpenDER)
            vv = cfg["system"]["res_volt_var"]
            self.vv_V = [vv["v1"], vv["v2"], vv["v3"], vv["v4"]]
            self.vv_Q = [vv["q1"], vv["q2"], vv["q3"], vv["q4"]]
            self.vv_tau = vv["olrt_s"] / 2.3                       # OpenDER: first-order lag, 90 % at the OLRT
            s_np = (cfg["system"]["pv"]["rated_mw"] + cfg["system"]["wind"]["rated_mw"]) * \
                math.sqrt(1.0 + vv["q_capability_frac"] ** 2)
            self.S_np_res = s_np / self.Sb                         # nameplate apparent power (system pu)

    def headroom_up(self):
        """Upward reserve behind the VSG commitments: with RES on their own droop, the BESS only."""
        if self.res_droop:
            dis, _ = self.bess_limits(self.soc)
            return max(dis - self.pb0, 0.0)
        return super().headroom_up()

    def headroom_down(self):
        if self.res_droop:
            _, ch = self.bess_limits(self.soc)
            return max(ch + self.pb0, 0.0)
        return super().headroom_down()

    def volt_var(self, v):
        """IEEE 1547-2018 volt-var curve: reactive power (system pu, + = injection) at voltage v (pu)."""
        q = float(np.interp(v, self.vv_V, self.vv_Q))
        return q * self.S_np_res

    # ------------------------------------------------------------------ setup
    def reset(self, sc, episode_s):
        super().reset(sc, episode_s)                  # Study 2 dispatch: load0, pd0, pb0, p_w0, pv_base, ...
        fd = self.feeder
        gen = {self.bus_v: self.pb0, self.bus_r: self.p_w0 + self.pv_base}
        V0, S1 = fd.load_flow(self.load0, gen)        # constant-power loads, diesel terminal at 1.0 pu
        self.q_res = self.q_v0 = 0.0
        if self.vc:
            # steady state with the VSG on its UNIFI Q-V droop line around 1.0 pu and the PV/wind volt-var:
            # damped fixed point on the two reactive injections, each limited to its converter capability
            mq_sys = self.mQ * self.Sb / self.S_conv               # pu voltage per system-pu reactive power
            q_lim = math.sqrt(max((self.S_conv / self.Sb) ** 2 - self.pb0 ** 2, 0.0))
            for _ in range(2000):
                q_r = self.volt_var(abs(V0[self.bus_r - 1]))
                q_v = min(max((1.0 - abs(V0[self.bus_v - 1])) / mq_sys, -q_lim), q_lim)
                dq = max(abs(q_r - self.q_res), abs(q_v - self.q_v0))
                if dq < 1e-10:
                    break
                self.q_res += 0.2 * (q_r - self.q_res)
                self.q_v0 += 0.2 * (q_v - self.q_v0)
                gen = {self.bus_v: self.pb0 + 1j * self.q_v0, self.bus_r: self.p_w0 + self.pv_base + 1j * self.q_res}
                V0, S1 = fd.load_flow(self.load0, gen)
            else:
                raise RuntimeError("reactive-power steady state did not converge")
        self.V0 = V0
        self.losses0 = S1.real + sum(float(np.real(g)) for g in gen.values()) - self.load0
        # EMFs behind the internal reactances (diesel supplies the feeder losses as well)
        I_d = np.conj(S1 / V0[self.bus_d - 1])
        S_v = self.pb0 + 1j * self.q_v0
        I_v = np.conj(S_v / V0[self.bus_v - 1])
        E_d = V0[self.bus_d - 1] + 1j * self.X_d * I_d
        E_v = V0[self.bus_v - 1] + 1j * self.X_v * I_v
        self.Ed_mag, self.Ev_mag = abs(E_d), abs(E_v)
        self.th_d, self.th_v = math.atan2(E_d.imag, E_d.real), math.atan2(E_v.imag, E_v.real)
        if self.vc:
            self.net_on = DynamicNetworkVC(fd, V0, self.load0, self.bus_d, self.bus_v, self.Xdp_s, self.Xq_s,
                                           self.X_v, True)
            self.net_off = DynamicNetworkVC(fd, V0, self.load0, self.bus_d, self.bus_v, self.Xdp_s, self.Xq_s,
                                            1e9, True)
            V1 = V0[self.bus_d - 1]
            I1 = np.conj(S1 / V1)
            delta = float(np.angle(V1 + 1j * self.Xq_s * I1))        # q axis along V + j X_q I
            e = np.exp(1j * (delta - 0.5 * math.pi))
            i_d = float((I1 * np.conj(e)).real)
            v_q = float((V1 * np.conj(e)).imag)
            Eq = v_q + self.Xdp_s * i_d
            efd = Eq + (self.Xd_s - self.Xdp_s) * i_d                 # = I_FD in steady state
            self.avr = AC8C(self.avr_cfg)
            self.avr.initialise(efd, efd, abs(V1))
            self.Ed_mag, self.th_d = Eq, delta                       # Ed_mag holds E'_q in this model
            self.efd0 = efd
            self.Vref_v, self.Q0_v = 1.0, 0.0                        # droop line V = 1.0 - m_Q Q (own rating)
            self.q_f, self.vv_f = self.q_v0, abs(V0[self.bus_v - 1])
        else:
            self.net_on = DynamicNetwork(fd, V0, self.load0, self.bus_d, self.bus_v, self.X_d, self.X_v, True)
            self.net_off = DynamicNetwork(fd, V0, self.load0, self.bus_d, self.bus_v, self.X_d, 1e9, True)
        self.Pe_d0 = S1.real                          # diesel electrical power incl. feeder losses
        self.p_gov = self.p_d = self.Pe_d0
        # The loads' admittance at the initial point is in the bus matrix of both networks; with constant-power
        # loads only the difference to constant power enters as a correction current (y_corr V), which keeps
        # the per-step fixed-point iteration contractive on the full feeder.
        self.y_corr = 0.0 if self.const_z else self.net_on.y_load
        self.V = V0.copy()
        self.p_w_s = 0.0                              # wind frequency-droop adjustment (IEEE 1547 mode)
        self.ang_v_prev = np.angle(V0[self.bus_v - 1])
        self.ang_d_prev = np.angle(V0[self.bus_d - 1])
        self.f_pll = 0.0                              # angle-based frequency at the VSG bus (PLL-like, analysis only)
        self.vmin = float(np.abs(V0).min())
        self.vmax = float(np.abs(V0).max())

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
            S_inj[ir] += self.p_w + self.pv_base + self.p_pv_s + self.p_w_s + 1j * self.q_res   # PV and wind at bus 33
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
            # --- network solution, iterated to convergence within the step (implicit in the bus voltages)
            E = np.array([self.Ed_mag * np.exp(1j * self.th_d), self.Ev_mag * np.exp(1j * self.th_v)])
            for _it in range(20):
                I_inj = np.conj(S_inj / V) + self.y_corr * V
                V_new, S_m = net.solve(E, I_inj)
                dv = float(np.max(np.abs(V_new - V)))
                V = V_new
                if dv < 1e-10:
                    break
            self.n_it_max = max(getattr(self, "n_it_max", 0), _it + 1)
            if vsg_on:
                P_vnet = S_m[1].real                   # BESS power delivered by the grid-forming VSG
                pv_req = P_vnet - self.pb0 + (0.0 if self.res_droop else self.p_pv_s)   # fast support asked of the VSG unit
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
            pv = pb_fast + (0.0 if self.res_droop else self.p_pv_s)   # fast support of the VSG unit
            Pe_d = S_m[0].real
            if self.vc:
                # diesel field flux and AC8C excitation (system pu; X i products are base-independent)
                dX = self.Xd_s - self.Xdp_s
                ifd = self.Ed_mag + dX * net.i_d
                efd = self.avr.step(abs(V[idd]), ifd, dt)
                self.Ed_mag += dt * (efd - self.Ed_mag - dX * net.i_d) / self.Tdo
                if vsg_on:
                    # UNIFI v3 Q-V droop on the VSG terminal voltage, through the measurement filter T_f
                    S_vt = net.S_vt
                    self.q_f += dt * (S_vt.imag - self.q_f) / self.Tf
                    self.vv_f += dt * (abs(V[iv]) - self.vv_f) / self.Tf
                    v_tgt = self.Vref_v - self.mQ * (self.q_f - self.Q0_v) * Sb / self.S_conv
                    err = v_tgt - self.vv_f
                    q_max = math.sqrt(max((self.S_conv / Sb) ** 2 - S_vt.real ** 2, 0.0))
                    if (S_vt.imag >= q_max - 1e-9 and err > 0.0) or (S_vt.imag <= -q_max + 1e-9 and err < 0.0):
                        err = 0.0                      # converter reactive limit: stop raising / lowering the EMF
                    self.Ev_mag += dt * err / self.Tf
                # PV / wind volt-var (IEEE 1547-2018 Cat. B, OLRT as first-order lag)
                self.q_res += dt * (self.volt_var(abs(V[ir])) - self.q_res) / self.vv_tau

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
                if not self.res_droop:
                    pv_tgt = min(max(alpha * pv_req, -self.pv_base), self.h_pv)
                    self.p_pv_s += dt * (pv_tgt - self.p_pv_s) / self.Tpv
            else:
                self.dw_v = self.dw_b = self.dw_d
                if self.res_droop:
                    pass
                elif droop_on:
                    pv_tgt = min(max(alpha * pv_req, -self.pv_base), self.h_pv)
                    self.p_pv_s += dt * (pv_tgt - self.p_pv_s) / self.Tpv
                else:
                    self.p_pv_s = 0.0
            if self.res_droop:
                # IEEE 1547-2018 frequency droop (OpenDER defaults): deadband, 5 % droop on nameplate power,
                # OLRT as first-order lag; PV up to its de-loaded reserve, wind (at MPP) only downwards
                fm = self.f_meas
                dp = (-self.fd_db - fm) / self.fd_k if fm < -self.fd_db else \
                    (-(fm - self.fd_db) / self.fd_k if fm > self.fd_db else 0.0)
                pv_t = min(max(dp * self.P_pv_np, -self.pv_base), self.h_pv)
                w_t = min(max(dp * self.P_w_np, -self.p_w), 0.0)
                self.p_pv_s += dt * (pv_t - self.p_pv_s) / self.fd_tau
                self.p_w_s += dt * (w_t - self.p_w_s) / self.fd_tau
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
            self.vmax = max(self.vmax, float(vm.max()))
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
