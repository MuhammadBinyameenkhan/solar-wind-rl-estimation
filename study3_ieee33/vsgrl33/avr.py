"""IEEE Std 421.5-2016 Type AC8C excitation system (digital PID AVR, brushless AC exciter).

Structure: Figure 16 (AC8C) with the AC rotating exciter of Figure 8; data: Table H.18 (Annex H.13).
Not modelled (inputs inactive): load compensation (R_C = X_C = 0 in the sample data), OEL / UEL / PSS.
V_PIDmax/V_PIDmin and V_Emin are not given in Table H.18 and are therefore not applied; V_E is kept
non-negative (diode rectifier) and above a tiny value only to evaluate I_N = K_C I_FD / V_E.

Exciter saturation S_E(V_E) is defined by the two points of Table H.18 and represented by the quadratic
function S_E = B (V_E - A)^2 / V_E for V_E > A (0 otherwise). The rectifier regulation F_EX(I_N) is the
piecewise characteristic of IEEE Std 421.5 for exciters with non-controlled rectifiers.
"""
from __future__ import annotations

import math


def fex(i_n: float) -> float:
    """Rectifier regulation characteristic F_EX = f(I_N) (IEEE Std 421.5)."""
    if i_n <= 0.0:
        return 1.0
    if i_n <= 0.433:
        return 1.0 - 0.577 * i_n
    if i_n <= 0.75:
        return math.sqrt(max(0.75 - i_n * i_n, 0.0))
    if i_n <= 1.0:
        return 1.732 * (1.0 - i_n)
    return 0.0


class AC8C:
    def __init__(self, p: dict):
        self.KPR, self.KIR, self.KDR, self.TDR = p["k_pr"], p["k_ir"], p["k_dr"], p["t_dr"]
        self.KA, self.TA = p["k_a"], p["t_a"]
        self.VRmax, self.VRmin = p["v_rmax"], p["v_rmin"]
        self.KP, self.VBmax = p["k_p"], p["v_bmax"]
        self.KC, self.KD, self.KE, self.TE = p["k_c"], p["k_d"], p["k_e"], p["t_e"]
        self.VFEmax = p["v_femax"]
        e1, s1, e2, s2 = p["e1"], p["se_e1"], p["e2"], p["se_e2"]
        # quadratic saturation through (E1, S_E(E1)) and (E2, S_E(E2)):  S_E * V_E = B (V_E - A)^2
        r = math.sqrt((s1 * e1) / (s2 * e2))
        self.A = (e1 - r * e2) / (1.0 - r)
        self.B = s1 * e1 / (e1 - self.A) ** 2

    def se(self, ve: float) -> float:
        return self.B * (ve - self.A) ** 2 / ve if ve > self.A else 0.0

    def _efd_of_ve(self, ve, ifd):
        return ve * fex(self.KC * ifd / max(ve, 1e-9))

    # ------------------------------------------------------------------ steady state
    def initialise(self, efd: float, ifd: float, vt: float):
        """Steady state for a given field voltage E_FD, field current I_FD and terminal voltage V_T."""
        lo, hi = 1e-6, 50.0                                   # bisection: E_FD = V_E F_EX(K_C I_FD / V_E)
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if self._efd_of_ve(mid, ifd) < efd:
                lo = mid
            else:
                hi = mid
        self.VE = 0.5 * (lo + hi)
        vfe = self.VE * self.se(self.VE) + self.KE * self.VE + self.KD * ifd
        vb = min(self.KP * vt, self.VBmax)                    # SW1 position A, K_I = X_L = K_C1 = 0
        self.VR = vfe / vb
        if not (self.VRmin <= self.VR <= self.VRmax):
            raise ValueError(f"AC8C initial V_R = {self.VR:.3f} outside [{self.VRmin}, {self.VRmax}]")
        self.xi = self.VR / self.KA                           # integrator holds the PID output (error = 0)
        self.xdf = 0.0                                        # derivative-filter state (error = 0)
        self.Vref = vt
        self.efd = efd
        return self.Vref

    # ------------------------------------------------------------------ one step
    def step(self, vt: float, ifd: float, dt: float) -> float:
        err = self.Vref - vt                                  # T_R = 0: no transducer lag
        u = self.KPR * err + self.xi + self.KDR * (err - self.xdf) / self.TDR
        self.xi += dt * self.KIR * err
        self.xdf += dt * (err - self.xdf) / self.TDR
        self.VR += dt * (self.KA * u - self.VR) / self.TA      # K_A / (1 + s T_A), non-windup limits
        self.VR = min(max(self.VR, self.VRmin), self.VRmax)
        vb = min(self.KP * vt, self.VBmax)
        efe = self.VR * vb
        vfe = self.VE * self.se(self.VE) + self.KE * self.VE + self.KD * ifd
        self.VE += dt * (efe - vfe) / self.TE
        ve_max = (self.VFEmax - self.KD * ifd) / (self.KE + self.se(self.VE))
        self.VE = min(max(self.VE, 0.0), ve_max)
        self.efd = self._efd_of_ve(self.VE, ifd)
        return self.efd
