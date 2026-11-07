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
