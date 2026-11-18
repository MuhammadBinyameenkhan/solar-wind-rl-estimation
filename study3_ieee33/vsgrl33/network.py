"""Published IEEE 33-bus feeder as a phasor network for the islanded microgrid of Study 3.

The network data are read unchanged from data/source/case33bw_matpower.m (Baran & Wu 1989).
All quantities are per unit on S_base (config system.s_base_mva) and V_base = 12.66 kV.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ieee33_data import load_ieee33  # noqa: E402


class Feeder:
    """Line admittances, published loads and helpers to solve the network at every step."""

    def __init__(self, s_base_mva: float, v_base_kv: float = 12.66):
        buses, lines = load_ieee33()
        self.n = len(buses)
        self.Sb = s_base_mva
        self.Zb = v_base_kv ** 2 / s_base_mva
        self.p_pub = buses.p_kw.to_numpy() / 1e3          # published peak loads (MW)
        self.q_pub = buses.q_kvar.to_numpy() / 1e3
        self.P_total = self.p_pub.sum()                    # 3.715 MW
        self.share_p = self.p_pub / self.P_total           # how the feeder load divides over buses
        self.qp = self.q_pub / self.P_total                # Q per MW of total load, per bus
        self.lines = lines[lines.in_service].reset_index(drop=True)
        Y = np.zeros((self.n, self.n), complex)
        for f, t, r, x in zip(self.lines["from"] - 1, self.lines.to - 1, self.lines.r_ohm, self.lines.x_ohm):
            y = 1.0 / ((r + 1j * x) / self.Zb)
            Y[f, f] += y
            Y[t, t] += y
            Y[f, t] -= y
            Y[t, f] -= y
        self.Y_lines = Y

    # ------------------------------------------------------------------ steady state
    def load_flow(self, load_pu, gen, v_slack=1.0, tol=1e-10, it_max=50):
        """Newton-Raphson load flow (polar). Bus 1 is the slack (diesel terminal).

        load_pu : total feeder load (pu), divided over buses by the published shares, with the
                  published Q/P ratio per bus (constant power).
        gen     : {bus_number: P_pu} constant-power injections at unity power factor.
        Returns complex bus voltages V (pu) and the slack power S1 (pu)."""
        n = self.n
        S_inj = -(load_pu * (self.share_p + 1j * self.qp)).astype(complex)
        for b, p in gen.items():
            S_inj[b - 1] += p
        Y = self.Y_lines
        V = np.ones(n, complex) * v_slack
        pq = np.arange(1, n)
        for _ in range(it_max):
            S_calc = V * np.conj(Y @ V)
            mis = S_inj - S_calc
            F = np.r_[mis.real[pq], mis.imag[pq]]
            if np.max(np.abs(F)) < tol:
                break
            # Jacobian in polar form
            Ibus = Y @ V
            dS_dVa = 1j * np.diag(V) @ np.conj(np.diag(Ibus) - Y @ np.diag(V))
            dS_dVm = np.diag(V) @ np.conj(Y @ np.diag(V / np.abs(V))) + np.diag(V / np.abs(V)) @ np.conj(np.diag(Ibus))
            J = np.block([[dS_dVa.real[np.ix_(pq, pq)], dS_dVm.real[np.ix_(pq, pq)]],
                          [dS_dVa.imag[np.ix_(pq, pq)], dS_dVm.imag[np.ix_(pq, pq)]]])
            dx = np.linalg.solve(J, F)
            Va, Vm = np.angle(V), np.abs(V)
            Va[pq] += dx[:len(pq)]
            Vm[pq] += dx[len(pq):]
            V = Vm * np.exp(1j * Va)
        else:
            raise RuntimeError("load flow did not converge")
        S1 = (V * np.conj(Y @ V))[0]
        return V, S1


class DynamicNetwork:
    """Phasor network with two internal EMFs (diesel at bus_d, VSG at bus_v) behind reactances.

    Loads are constant-power current injections (as in the published case and Study 2) or, as an
    option, constant admittances from the initial voltages; every change (load steps, load noise,
    load-frequency damping, renewable output) enters as a bus current injection, so the network
    matrix is factorised once per episode:
        V = Zbb @ (I_inj - Ybm @ E),   I_m = Ymm @ E + Ymb @ V  (current out of each EMF)."""

    def __init__(self, feeder: Feeder, V0, load_pu, bus_d, bus_v, X_d, X_v, const_z_loads=False):
        n = feeder.n
        self.bd, self.bv = bus_d - 1, bus_v - 1
        if const_z_loads:      # S = V conj(yV) -> y = conj(S)/|V|^2 at the initial voltages
            y_load = load_pu * (feeder.share_p - 1j * feeder.qp) / np.abs(V0) ** 2
        else:                  # constant-power loads enter as current injections instead
            y_load = np.zeros(n, complex)
        Ybb = feeder.Y_lines + np.diag(y_load)
        yd, yv = 1.0 / (1j * X_d), 1.0 / (1j * X_v)
        Ybb[self.bd, self.bd] += yd
        Ybb[self.bv, self.bv] += yv
        self.Zbb = np.linalg.inv(Ybb)
        self.Ybm = np.zeros((n, 2), complex)
        self.Ybm[self.bd, 0] = -yd
        self.Ybm[self.bv, 1] = -yv
        self.Ymm = np.diag([yd, yv])
        self.Ymb = self.Ybm.T.copy()
        self.y_load = y_load

    def solve(self, E, I_inj):
        V = self.Zbb @ (I_inj - self.Ybm @ E)
        I_m = self.Ymm @ E + self.Ymb @ V
        S_m = E * np.conj(I_m)          # power delivered by each EMF into the network
        return V, S_m


class DynamicNetworkVC:
    """Phasor network with a salient-pole diesel machine (one-axis model) at bus_d and the VSG EMF behind X_v.

    Diesel stator (R_s = 0) in its rotor frame (q axis at angle delta):  v_d = X_q i_q,  v_q = E'_q - X'_d i_d.
    In the network frame (theta = delta - pi/2) the machine current into the network is
        I = (E'_q / X'_d) e^{j theta} + j a V + j b conj(V) e^{2 j theta},
        a = (1/X'_d + 1/X_q) / 2,  b = (1/X_q - 1/X'_d) / 2.
    The term j a V is a constant shunt and goes into the bus matrix; the conj(V) term is solved exactly as a
    2 x 2 real system at the machine bus, so no iteration is needed."""

    def __init__(self, feeder: Feeder, V0, load_pu, bus_d, bus_v, Xdp, Xq, X_v, const_z_loads=False):
        n = feeder.n
        self.bd, self.bv = bus_d - 1, bus_v - 1
        if const_z_loads:
            y_load = load_pu * (feeder.share_p - 1j * feeder.qp) / np.abs(V0) ** 2
        else:
            y_load = np.zeros(n, complex)
        self.Xdp, self.Xq = Xdp, Xq
        self.a = 0.5 * (1.0 / Xdp + 1.0 / Xq)
        self.b = 0.5 * (1.0 / Xq - 1.0 / Xdp)
        Ybb = feeder.Y_lines + np.diag(y_load)
        Ybb[self.bd, self.bd] += -1j * self.a           # current j a V into the network = shunt -j a
        self.yv = 1.0 / (1j * X_v)
        Ybb[self.bv, self.bv] += self.yv
        self.Zbb = np.linalg.inv(Ybb)
        self.z_dd = self.Zbb[self.bd, self.bd]
        self.y_load = y_load
        self.i_d = self.i_q = 0.0
        self.I_d = 0j
        self.S_vt = 0j

    def solve(self, E, I_inj):
        """E[0] = E'_q e^{j delta} (diesel), E[1] = VSG EMF phasor. Returns V and the power delivered by
        each machine (diesel at its terminal, VSG at its EMF)."""
        Eq, delta = abs(E[0]), np.angle(E[0])
        e = np.exp(1j * (delta - 0.5 * np.pi))
        rhs = I_inj.astype(complex).copy()
        rhs[self.bd] += (Eq / self.Xdp) * e
        rhs[self.bv] += self.yv * E[1]
        V = self.Zbb @ rhs
        w = V[self.bd]
        k = self.z_dd * 1j * self.b * e * e
        kr, ki = k.real, k.imag
        det = (1.0 - kr) * (1.0 + kr) - ki * ki
        x = ((1.0 + kr) * w.real + ki * w.imag) / det
        y = (ki * w.real + (1.0 - kr) * w.imag) / det
        V1 = x + 1j * y
        extra = 1j * self.b * e * e * np.conj(V1)
        V = V + self.Zbb[:, self.bd] * extra
        I_d = (Eq / self.Xdp) * e + 1j * self.a * V[self.bd] + extra
        Ir = I_d * np.conj(e)
        self.i_d, self.i_q, self.I_d = Ir.real, Ir.imag, I_d
        I_v = self.yv * (E[1] - V[self.bv])
        self.S_vt = V[self.bv] * np.conj(I_v)               # VSG power at its terminal
        S_m = np.array([V[self.bd] * np.conj(I_d), E[1] * np.conj(I_v)])
        return V, S_m
