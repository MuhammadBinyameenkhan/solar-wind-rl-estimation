"""
Microgrid + grid-forming BESS (VSG) environment, Gym-style API.

FREQUENCY (per unit on S_BASE, dw = (f - f0) / f0)
    VSG law            p_vsg = -2 J dw/dt - D dw_m
    Swing equation     2 H_sys dw/dt = dP_ext + p_vsg
    Closed form        dw/dt = (dP_ext - D dw_m) / (2 (H_sys + J))
    dP_ext             (P_pv + P_wind + P_sched - P_load) / S_base
    P_sched            P_agc + p_droop * S_base       (BESS schedule + droop)

The BESS is the only dispatchable converter, so its scheduled duty
(P_agc), its primary droop (p_droop) and the VSG term (p_vsg) all come out
of the same 2500 kVA rating.  [Fix: the earlier version added a governor
term with no physical source, ~330 kW in the no-VSG case.]

HEADROOM (paper Section 3.4.1, Eqs. 20-25)
    h_req   = 2 J RoCoF_max / f0 + D df_max / f0   = 0.08 J + 0.01 D at 50 Hz
    h_avail = (S - |P_sched|) / S
    if h_req > h_avail the declared (J, D) are derated by h_avail / h_req.

If the BESS still saturates (rating or SOC) the step is re-solved with
only the physical inertia H_sys.

VOLTAGE
    T_v dV/dt = X_th (Q_vsg - Q_load) / S + (V_nom - V)
    Q_vsg     = Kq (V_nom - V), bounded by sqrt(S^2 - P_bess^2)
"""
import collections

import numpy as np

from . import config as C
from .models import BESS, SolarPV, WindTurbine
from .weather import build_weather


class MicrogridVSGEnv:

    def __init__(self, scenario: str = "combined", stochastic: bool = False,
                 seed: int | None = None, dt: float | None = None,
                 duration: float | None = None, split: str = "test"):
        self.dt = C.CONTROL_DT if dt is None else dt
        self.duration = C.EPISODE_DURATION if duration is None else duration
        self.n_steps = int(round(self.duration / self.dt))
        self.h = self.dt / C.PHYS_SUBSTEPS
        self.scenario = scenario
        self.stochastic = stochastic
        self.split = split          # "train" / "val" / "test": which part of a
        #                             measured record the weather is cut from
        self.rng = np.random.default_rng(seed)

        self.pv = SolarPV()
        self.wt = WindTurbine()
        self.bess = BESS()
        self.weather = build_weather(dt=self.dt, duration=self.duration)
        self.Q_load_nom = C.P_LOAD_NOM * np.tan(np.arccos(C.PF_LOAD))
        self.action_dim = C.ACTION_DIM
        self.state_dim = C.STATE_DIM
        self.bounds = C.action_bounds()
        self.reset()

    # ------------------------------------------------------------
    def _load_profile(self):
        irr, temp, wind, turb = self.weather.get(
            self.scenario, stochastic=self.stochastic, rng=self.rng, split=self.split)
        n = self.n_steps
        self._irr = np.resize(irr, n)
        self._temp = np.resize(temp, n)
        wind_base = np.resize(wind, n)
        turb = np.resize(turb, n)

        # turbulence drawn once per episode (observation == dynamics)
        w = self.rng.standard_normal(n)
        a = np.exp(-self.dt / 0.4)
        acc, col = 0.0, np.empty(n)
        for i in range(n):
            acc = a * acc + (1 - a) * w[i]
            col[i] = acc
        col /= (np.std(col) + 1e-9)
        self._wind_series = np.clip(wind_base + turb * col, 0.5, 28.0)
        self._ppv_series = np.array(
            [self.pv.power(self._irr[i], self._temp[i]) for i in range(n)])

        step_frac = C.LOAD_STEP.get(self.scenario, 0.0)
        events = list(C.LOAD_EVENTS)
        if self.stochastic:
            step_frac = float(self.rng.uniform(*C.RAND_STEP_FRAC))
            j = C.RAND_JITTER
            events = [(a_ * float(self.rng.uniform(1 - j, 1 + j)),
                       b_ * float(self.rng.uniform(1 - j, 1 + j)),
                       m_ * float(self.rng.uniform(0.7, 1.3)))
                      for a_, b_, m_ in events]
        t = np.arange(n) * self.dt
        self._pulse = np.zeros(n)
        self.event_windows = []
        for a_, b_, mag in events:
            t_a = a_ * self.duration
            t_b = max(b_, a_ + 0.05) * self.duration
            up = np.clip((t - t_a) / C.LOAD_STEP_RAMP, 0.0, 1.0)
            down = np.clip((t - t_b) / C.LOAD_STEP_RAMP, 0.0, 1.0)
            self._pulse = self._pulse + mag * (up - down)
            self.event_windows.append((t_a, t_b))
        self.step_frac = step_frac
        self._load_series = C.P_LOAD_NOM * (1.0 + step_frac * self._pulse)

    def reset(self, scenario: str | None = None, stochastic: bool | None = None,
              seed: int | None = None):
        if scenario is not None:
            self.scenario = scenario
        if stochastic is not None:
            self.stochastic = stochastic
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self._load_profile()

        self.k, self.t = 0, 0.0
        self.dw = 0.0
        self.f = C.F_NOM
        self.rocof_inst = self.rocof_filt = self.rocof_filt_meas = 0.0
        self.rocof_meas = 0.0
        self.f_meas, self.dw_meas, self.f_noise = C.F_NOM, 0.0, 0.0
        self._first_action = True
        self.p_droop = 0.0
        self.P_vsg = self.P_agc = self.P_bess = self.Q_vsg = 0.0
        self.P_sched = 0.0
        self.J = self.D = self.J_eff = self.D_eff = 0.0
        self.Kq = C.KQ_VSG
        self.h_req, self.h_avail = 0.0, 1.0
        self.tripped = False

        self.bess.reset(C.SOC_INIT)
        self.wt.reset(float(self._wind_series[0]))
        self.V = self._equilibrium_voltage()
        self.P_pv = float(self._ppv_series[0])
        self.P_wind = self.wt.P_e
        self.P_gen_filt = self.P_pv + self.P_wind
        self.P_load_actual = C.P_LOAD_NOM
        self.P_agc = C.P_LOAD_NOM * (self.V / C.V_NOM) ** C.LOAD_V_EXP - self.P_gen_filt
        self.P_sched = self.P_bess = self.P_agc
        self.h_avail = max(0.0, (self.bess.S_rated - abs(self.P_sched)) / C.S_BASE)
        self._prev_action_norm = np.zeros(self.action_dim)
        nwin = max(2, int(round(C.ROCOF_WINDOW / self.dt)))
        self._f_hist = collections.deque([C.F_NOM] * nwin, maxlen=nwin)
        return self._state()

    def _equilibrium_voltage(self) -> float:
        V = C.V_NOM
        for _ in range(200):
            q_load = self.Q_load_nom * (V / C.V_NOM) ** 2 / C.S_BASE
            V_new = C.V_NOM + C.X_TH * (self.Kq * (C.V_NOM - V) - q_load)
            if abs(V_new - V) < 1e-12:
                break
            V = 0.5 * V + 0.5 * V_new
        return float(V)

    # ------------------------------------------------------------
    def _state(self) -> np.ndarray:
        k = min(self.k, self.n_steps - 1)
        kq_lo, kq_hi = C.KQ_MIN, C.KQ_MAX
        return np.array([
            (self.f_meas - C.F_NOM) / 0.5,
            self.rocof_filt_meas / C.ROCOF_LIMIT,
            self.t / self.duration,
            self.P_pv / self.pv.P_rated,
            self.P_wind / self.wt.P_rated,
            self._wind_series[k] / 25.0,
            self._irr[k] / 1000.0,
            self.bess.soc,
            (self.V - C.V_NOM) / 0.10,
            self.P_bess / C.S_BASE,
            self.J / C.J_MAX,
            self.D / C.D_MAX,
            2.0 * (self.Kq - kq_lo) / (kq_hi - kq_lo) - 1.0,
            self.h_avail,
        ], dtype=np.float32)

    # ------------------------------------------------------------
    def step(self, action):
        a = np.asarray(action, dtype=float).ravel()
        # Baselines may request J = D = 0 (true "no VSG"); the RL agents
        # are confined to [J_MIN, J_MAX] x [D_MIN, D_MAX] by their tanh map.
        J_cmd = float(np.clip(a[0], 0.0, C.J_MAX))
        D_cmd = float(np.clip(a[1], 0.0, C.D_MAX))
        Kq_cmd = (float(np.clip(a[2], C.KQ_MIN, C.KQ_MAX))
                  if (self.action_dim >= 3 and a.size >= 3) else C.KQ_VSG)

        if self._first_action:
            self.J, self.D, self.Kq = J_cmd, D_cmd, Kq_cmd
            self._first_action = False
        else:
            s = self.dt / C.SLEW_TIME
            self.J += float(np.clip(J_cmd - self.J, -C.J_MAX * s, C.J_MAX * s))
            self.D += float(np.clip(D_cmd - self.D, -C.D_MAX * s, C.D_MAX * s))
            dK = (C.KQ_MAX - C.KQ_MIN) * s
            self.Kq += float(np.clip(Kq_cmd - self.Kq, -dK, dK))

        self.f_noise = float(self.rng.normal(0.0, C.PLL_NOISE_HZ))
        k = min(self.k, self.n_steps - 1)
        P_pv_now = float(self._ppv_series[k])
        v_wind = float(self._wind_series[k])
        P_load_nom_now = float(self._load_series[k])

        for _ in range(C.PHYS_SUBSTEPS):
            self._substep(P_pv_now, v_wind, P_load_nom_now)
            if self.tripped:
                break

        self._f_hist.append(self.f)
        self.rocof_meas = (self._f_hist[-1] - self._f_hist[0]) / C.ROCOF_WINDOW

        reward = self._reward(a)
        self.k += 1
        self.t = self.k * self.dt
        done = bool(self.tripped or self.k >= self.n_steps)
        # Time-limit end is not a true terminal state; tell the learner.
        truncated = bool(self.k >= self.n_steps and not self.tripped)
        info = dict(f=self.f, V=self.V, rocof=self.rocof_meas,
                    rocof_inst=self.rocof_inst, J=self.J, D=self.D, Kq=self.Kq,
                    J_eff=self.J_eff, D_eff=self.D_eff,
                    h_req=self.h_req, h_avail=self.h_avail,
                    P_pv=self.P_pv, P_wind=self.P_wind, P_bess=self.P_bess,
                    P_vsg=self.P_vsg, P_agc=self.P_agc,
                    P_droop=self.p_droop * C.S_BASE, Q_vsg=self.Q_vsg,
                    soc=self.bess.soc, P_load=self.P_load_actual,
                    v_wind=v_wind, irr=float(self._irr[k]),
                    tripped=self.tripped, truncated=truncated)
        return self._state(), reward, done, info

    # ------------------------------------------------------------
    def _substep(self, P_pv_now, v_wind, P_load_nom_now):
        h = self.h
        F0 = C.F_NOM

        # PLL: lag + noise, causal
        self.f_meas += (self.f + self.f_noise - self.f_meas) * h / C.PLL_TAU
        dw_meas_new = (self.f_meas - F0) / F0
        rocof_m = F0 * (dw_meas_new - self.dw_meas) / h
        self.dw_meas = dw_meas_new
        self.rocof_filt_meas += (rocof_m - self.rocof_filt_meas) * h / C.ROCOF_FILT_TAU

        # generation
        self.P_pv = P_pv_now
        self.P_wind = self.wt.step(v_wind, h)
        P_gen = self.P_pv + self.P_wind

        # loads
        v_ratio = max(self.V / C.V_NOM, 0.1)
        self.P_load_actual = P_load_nom_now * v_ratio ** C.LOAD_V_EXP
        q_scale = 1.0 + C.Q_STEP_RATIO * (P_load_nom_now / C.P_LOAD_NOM - 1.0)
        Q_load = self.Q_load_nom * q_scale * v_ratio ** 2

        # BESS schedule: slow AGC tracking + primary droop on measured dw
        self.P_gen_filt += (P_gen - self.P_gen_filt) * h / C.TAU_AGC
        self.P_agc = C.P_LOAD_NOM * v_ratio ** C.LOAD_V_EXP - self.P_gen_filt
        self.p_droop += (-C.K_DROOP * self.dw_meas - self.p_droop) * h / C.T_DROOP
        self.P_sched = self.P_agc + self.p_droop * C.S_BASE

        # headroom feasibility (Eqs. 22-25)
        h_avail = max(0.0, (self.bess.S_rated - abs(self.P_sched)) / C.S_BASE)
        h_req = (2.0 * self.J * (C.ROCOF_LIMIT / F0) + self.D * (C.F_BAND_OK / F0))
        if h_req > h_avail and h_req > 1e-9:
            kd = h_avail / h_req
            self.J_eff, self.D_eff = self.J * kd, self.D * kd
        else:
            self.J_eff, self.D_eff = self.J, self.D
        self.h_req, self.h_avail = h_req, h_avail

        # swing equation, VSG law solved in closed form
        dP_ext = (P_gen + self.P_sched - self.P_load_actual) / C.S_BASE
        ddw = (dP_ext - self.D_eff * self.dw_meas) / (2.0 * (C.H_SYS + self.J_eff))
        p_vsg = -2.0 * self.J_eff * ddw - self.D_eff * self.dw_meas

        P_req = self.P_sched + p_vsg * C.S_BASE
        P_act = self.bess.apply(P_req, h)
        if abs(P_act - P_req) > 1.0:                 # rating / SOC saturation
            ddw = (P_gen + P_act - self.P_load_actual) / C.S_BASE / (2.0 * C.H_SYS)
            p_vsg = (P_act - self.P_sched) / C.S_BASE
        self.P_bess = P_act
        self.P_vsg = p_vsg * C.S_BASE

        self.dw += ddw * h
        self.f = F0 * (1.0 + self.dw)
        self.rocof_inst = F0 * ddw
        self.rocof_filt += (self.rocof_inst - self.rocof_filt) * h / C.ROCOF_FILT_TAU

        # reactive / voltage channel
        q_cap = self.bess.q_capability(abs(self.P_bess))
        Q_req = self.Kq * (C.V_NOM - self.V) * C.S_BASE
        self.Q_vsg = float(np.clip(Q_req, -q_cap, q_cap))
        dV = (C.X_TH * (self.Q_vsg - Q_load) / C.S_BASE + (C.V_NOM - self.V)) / C.T_VOLT
        self.V = float(np.clip(self.V + dV * h, 0.0, 2.0))

        lo, hi = C.f_trip()
        if not (lo < self.f < hi) or not (C.V_TRIP_LO < self.V < C.V_TRIP_HI):
            self.tripped = True

    # ------------------------------------------------------------
    def _reward(self, action) -> float:
        df = self.f - C.F_NOM
        dv = self.V - C.V_NOM
        a_norm = self.normalise_action(action)
        r = (-C.W_FREQ * df ** 2
             - C.W_ROCOF * (self.rocof_filt / C.ROCOF_LIMIT) ** 2
             - C.W_VOLT * (dv / 0.05) ** 2
             - C.W_EFFORT * float(np.mean((a_norm - self._prev_action_norm) ** 2))
             - C.W_SOC * abs(self.bess.soc - 0.5)
             - C.W_BESS * (self.P_vsg / C.S_BASE) ** 2
             - C.W_RESERVE * self.h_req
             - C.W_INFEAS * max(0.0, self.h_req - self.h_avail)
             + (C.R_ALIVE if abs(df) < C.F_BAND_OK else 0.0))
        self._prev_action_norm = a_norm
        if self.tripped:
            r -= C.R_TERM_PENALTY
        return float(r)

    def normalise_action(self, a) -> np.ndarray:
        a = np.asarray(a, dtype=float).ravel()
        out = []
        for i, (lo, hi) in enumerate(self.bounds):
            v = float(a[i]) if i < a.size else (C.KQ_VSG if i == 2 else lo)
            out.append(2.0 * (v - lo) / (hi - lo) - 1.0)
        return np.asarray(out)

    # ------------------------------------------------------------
    REC_KEYS = ["t", "f", "rocof", "rocof_inst", "V", "J", "D", "Kq", "P_pv",
                "P_wind", "P_bess", "P_vsg", "P_agc", "P_droop", "Q_vsg", "soc",
                "P_load", "v_wind", "irr", "reward", "J_eff", "D_eff",
                "h_req", "h_avail"]

    def rollout(self, policy, seed: int = 0, keep_states: bool = False):
        """Run one episode with ``policy(state) -> action`` and record it."""
        state = self.reset(seed=seed)
        if hasattr(policy, "reset"):
            policy.reset()
        n = self.n_steps
        rec = {k: np.zeros(n) for k in self.REC_KEYS}
        states = np.zeros((n, self.state_dim), dtype=np.float32) if keep_states else None
        total_r = 0.0
        last = n - 1
        for i in range(n):
            if keep_states:
                states[i] = state
            action = policy(state)
            state, r, done, info = self.step(action)
            total_r += r
            rec["t"][i] = self.t
            rec["reward"][i] = r
            for k in self.REC_KEYS[1:]:
                if k in info:
                    rec[k][i] = info[k]
            if done:
                last = i
                break
        if last < n - 1:
            for k in self.REC_KEYS:
                rec[k][last + 1:] = rec[k][last]
            rec["t"][last + 1:] = np.arange(last + 2, n + 1) * self.dt
            rec["reward"][last + 1:] = 0.0
        rec["n_valid"] = last + 1
        rec["total_reward"] = total_r
        rec["tripped"] = bool(self.tripped)
        rec["energy_kwh"] = self.bess.energy_throughput_wh / 1e3
        rec["event_windows"] = list(self.event_windows)
        if keep_states:
            rec["states"] = states[:last + 1]
        return rec
