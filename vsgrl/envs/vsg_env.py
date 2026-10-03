"""Gymnasium environment: an RL agent schedules the VSG parameters
(virtual inertia H_v, damping D_v, PV-headroom share alpha) every 50 ms
during a multi-event disturbance episode drawn from real ERA5 / NASA POWER
operating points.
"""
from __future__ import annotations

import gymnasium as gym
import numpy as np
import pandas as pd
from gymnasium import spaces

from ..data.hybrid import load_processed, wind_curve_from_cfg
from ..microgrid import Microgrid, Scenario
from ..scenarios import ScenarioSampler

OBS_NAMES = ["df", "rocof", "p_vsg", "dfv_minus_df", "headroom_up", "headroom_down", "headroom_pv", "soc",
             "p_wind", "p_pv_mpp", "p_diesel", "diesel_spare", "load",
             "H_applied", "D_applied", "alpha_applied"]


class VSGEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, cfg: dict, df: pd.DataFrame | None = None, split: str = "train",
                 record_trace: bool = False, trace_every: int = 5):
        super().__init__()
        self.cfg = cfg
        e, s = cfg["env"], cfg["system"]
        self.df = df if df is not None else load_processed(cfg)
        self.mg = Microgrid(cfg, wind_curve_from_cfg(cfg))
        self.sampler = ScenarioSampler(cfg, self.df, self.mg)
        self.split = split
        self.episode_s = e["episode_s"]
        self.n_sub = int(round(e["agent_dt_s"] / e["sim_dt_s"]))
        self.max_steps = int(round(self.episode_s / e["agent_dt_s"]))
        self.f0 = s["f_nominal_hz"]
        self.gc = s["grid_code"]
        self.vsg = s["vsg"]
        self.rw = e["reward"]
        self.headroom_constraint = e["headroom_constraint"]
        self.projection = e.get("projection", "steady_share")
        # First-order rate limit on the applied VSG parameters (0 → none)
        self.param_tau = e.get("param_filter_s", 0.0)
        self.act_dims = e.get("action_dims", 3)
        self.action_mode = e.get("action_mode", "absolute")
        # Centre of the residual mapping: the nominal VSG, or the validation-tuned fixed VSG.
        v = s["vsg"]
        base = (v["nominal_h_s"], v["nominal_d_pu"], v["nominal_alpha"])
        if e.get("residual_base", "nominal") == "tuned":
            t = (cfg.get("eval", {}).get("baseline_params") or {}).get("fixed_tuned") or {}
            base = (t.get("h", base[0]), t.get("d", base[1]), t.get("alpha", base[2]))
        self.res_base = base
        self.record_trace = record_trace
        self.trace_every = trace_every

        self.action_space = spaces.Box(-1.0, 1.0, shape=(self.act_dims,), dtype=np.float32)
        self.observation_space = spaces.Box(-10.0, 10.0, shape=(len(OBS_NAMES),), dtype=np.float32)
        self._rng = np.random.default_rng()
        self.scenario: Scenario | None = None

        # design-basis quantities for the feasibility projection
        mg = self.mg
        self.dP_design = s["disturbance"]["design_step_mw"] / mg.Sb
        self.share0 = mg.Ks / (mg.Ks + mg.Kd)

    # ----------------------------------------------------------- mappings
    def param_bounds(self):
        """Upper bounds of (H_v, D_v) after the headroom feasibility projection.

        The headroom h is direction-aware: upward (BESS discharge + PV headroom) while the
        frequency is at or below nominal, downward (BESS charge + PV curtailment) during an
        over-frequency event.

        projection = "band_power" (default):
          * D·Δf_band ≤ h: the damping power at the edge of the allowed band must be deliverable.
          * 2H·RoCoF_lim ≤ h: the inertial power at the RoCoF limit must be deliverable.
        projection = "steady_share" (earlier single-event formulation):
          * D/(D + β)·ΔP_design ≤ h and H scaled by h / (K_s/(K_s+K_d)·ΔP_design).
        Without the constraint the bounds are the static ranges."""
        v = self.vsg
        if not self.headroom_constraint:
            return v["h_max_s"], v["d_max_pu"]
        mg = self.mg
        h = mg.headroom_up() if mg.f_meas <= 0.0 else mg.headroom_down()
        if self.projection == "band_power":
            f_band = (self.rw.get("f_band_hz") or self.gc["f_target_hz"]) / self.f0
            rocof_lim = self.gc["rocof_limit_hz_s"] / self.f0
            d_ub = min(v["d_max_pu"], max(v["d_min_pu"], h / f_band))
            h_ub = min(v["h_max_s"], max(v["h_min_s"], h / (2.0 * rocof_lim)))
            return h_ub, d_ub
        s = min(h / self.dP_design, 0.95)
        beta = mg.inv_R + mg.DL * mg.load0
        d_ub = min(v["d_max_pu"], max(v["d_min_pu"], beta * s / (1.0 - s)))
        rho = min(1.0, h / (self.share0 * self.dP_design))
        h_ub = v["h_min_s"] + rho * (v["h_max_s"] - v["h_min_s"])
        return h_ub, d_ub

    def action_to_params(self, a):
        """Map a ∈ [-1,1]^k to (H, D, alpha).

        absolute: a spans [min, projected upper bound] linearly.
        residual: a = 0 is the nominal VSG (H0, D0, alpha0); a = ±1 moves to the
                  (projected) bounds — the policy learns corrections to a working VSG
                  (residual policy learning), which makes early training safe."""
        v = self.vsg
        a = np.clip(np.asarray(a, dtype=float), -1.0, 1.0)
        h_ub, d_ub = self.param_bounds()
        if self.action_mode == "residual":
            h0, d0, a0 = self.res_base
            H = self._residual(a[0], h0, v["h_min_s"], h_ub)
            D = self._residual(a[1], d0, v["d_min_pu"], d_ub)
            alpha = self._residual(a[2], a0, v["alpha_min"], v["alpha_max"]) if self.act_dims >= 3 else a0
            return float(H), float(D), float(alpha)
        H = v["h_min_s"] + 0.5 * (a[0] + 1.0) * (h_ub - v["h_min_s"])
        D = v["d_min_pu"] + 0.5 * (a[1] + 1.0) * (d_ub - v["d_min_pu"])
        if self.act_dims >= 3:
            alpha = v["alpha_min"] + 0.5 * (a[2] + 1.0) * (v["alpha_max"] - v["alpha_min"])
        else:
            alpha = v["nominal_alpha"]
        return float(H), float(D), float(alpha)

    @staticmethod
    def _residual(a, nominal, lo, hi):
        nominal = min(max(nominal, lo), hi)          # nominal itself respects the projection
        return nominal + a * (hi - nominal) if a >= 0 else nominal + a * (nominal - lo)

    def params_to_action(self, H, D, alpha):
        """Inverse map (unprojected ranges) — used to log baselines in action space."""
        v = self.vsg
        h = 2 * (H - v["h_min_s"]) / (v["h_max_s"] - v["h_min_s"]) - 1
        d = 2 * (D - v["d_min_pu"]) / (v["d_max_pu"] - v["d_min_pu"]) - 1
        al = 2 * (alpha - v["alpha_min"]) / (v["alpha_max"] - v["alpha_min"]) - 1
        return np.clip(np.array([h, d, al][: self.act_dims], dtype=np.float32), -1, 1)

    # --------------------------------------------------------------- core
    def _obs(self):
        mg = self.mg
        Sb = mg.Sb
        v = self.vsg
        Hp, Dp, Ap = self._applied if self._applied is not None else (v["nominal_h_s"], v["nominal_d_pu"], v["nominal_alpha"])
        o = np.array([
            mg.f_meas * self.f0 / self.gc["f_target_hz"],
            mg.rocof_meas * self.f0 / self.gc["rocof_limit_hz_s"],
            mg.p_vsg / 0.25,
            (mg.dw_v - mg.dw_d) * self.f0 / 0.1,
            mg.headroom_up() / 0.3,
            mg.headroom_down() / 0.3,
            mg.h_pv / 0.1,
            (mg.soc - 0.5) / 0.4,
            mg.p_w * Sb / 1.0,
            mg.pv_mpp * Sb / 0.8,
            mg.p_d / mg.Pd_rat,
            (mg.Pd_rat - mg.p_d) / mg.Pd_rat,
            mg.load0 * Sb / 1.2,
            2.0 * Hp / v["h_max_s"] - 1.0,
            2.0 * Dp / v["d_max_pu"] - 1.0,
            2.0 * Ap - 1.0,
        ], dtype=np.float32)
        return np.clip(o, -10.0, 10.0)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._rng = np.random.default_rng(seed)
        options = options or {}
        self.scenario = options.get("scenario") or self.sampler.sample(self._rng, options.get("split", self.split))
        self.mg.reset(self.scenario, self.episode_s)
        self.mode = options.get("mode", "vsg")
        self._k = 0
        self._prev_a = np.zeros(self.act_dims, dtype=np.float32)
        self._applied = None
        self._trace = {"every": self.trace_every, "rows": []} if self.record_trace else None
        self._ep = {"max_df_hz": 0.0, "max_rocof_hz_s": 0.0, "sat_s": 0.0, "return": 0.0, "collapsed": False}
        return self._obs(), {"scenario": self.scenario.to_dict()}

    def step(self, action):
        H, D, alpha = self.action_to_params(action)
        return self.step_params(H, D, alpha, action=np.asarray(action, dtype=np.float32))

    def step_params(self, H, D, alpha, action=None, mode=None):
        """Advance one decision interval with explicit physical parameters (used by baselines)."""
        mode = mode or self.mode
        if action is None:
            action = self.params_to_action(H, D, alpha)
        if self.param_tau > 0.0 and self._applied is not None:
            k = min(self.cfg["env"]["agent_dt_s"] / self.param_tau, 1.0)
            H0, D0, A0 = self._applied
            H, D, alpha = H0 + k * (H - H0), D0 + k * (D - D0), A0 + k * (alpha - A0)
        self._applied = (H, D, alpha)
        st = self.mg.advance(H, D, alpha, self.n_sub, mode=mode, trace=self._trace)
        self._k += 1

        rw, gc = self.rw, self.gc
        da = np.asarray(action, dtype=np.float32) - self._prev_a
        # Frequency/RoCoF are penalised only beyond the grid-code band (band = 0 → plain
        # quadratic); a small in-band term keeps a gentle pull towards nominal.
        cost = (rw["w_freq"] * st["msf_excess_hz2"] / gc["f_target_hz"] ** 2
                + rw.get("w_freq_inband", 0.0) * st["msf_hz2"] / gc["f_target_hz"] ** 2
                + rw["w_rocof"] * st["msr_excess_hz2s2"] / gc["rocof_limit_hz_s"] ** 2
                + rw["w_bess"] * st["ms_pbess"] / self.mg.Pb_max ** 2
                + rw.get("w_fast", 0.0) * st["ms_pfast"] / self.mg.Pb_max ** 2
                + rw["w_sat"] * st["mean_sat"] / 0.05
                + rw["w_violation"] * st["viol_frac"]
                + rw["w_action_rate"] * float(np.dot(da, da)))
        reward = -cost
        self._prev_a = np.asarray(action, dtype=np.float32)

        mg = self.mg
        dfz = abs(mg.f_meas) * self.f0
        ep = self._ep
        ep["max_df_hz"] = max(ep["max_df_hz"], dfz)
        ep["max_rocof_hz_s"] = max(ep["max_rocof_hz_s"], abs(mg.rocof_meas) * self.f0)
        if st["mean_sat"] > 1e-6:
            ep["sat_s"] += self.cfg["env"]["agent_dt_s"]
        terminated = dfz > self.cfg["env"]["terminate_dev_hz"] or not np.isfinite(dfz)
        if terminated:
            reward -= rw["collapse_penalty"]
            ep["collapsed"] = True
        truncated = self._k >= self.max_steps and not terminated
        ep["return"] += reward
        info = {"H": H, "D": D, "alpha": alpha, **st}
        if terminated or truncated:
            info["episode"] = dict(ep)
        return self._obs(), float(reward), bool(terminated), bool(truncated), info

    def trace_frame(self) -> pd.DataFrame:
        if not self._trace:
            return pd.DataFrame(columns=Microgrid.TRACE_COLUMNS)
        return pd.DataFrame(self._trace["rows"], columns=Microgrid.TRACE_COLUMNS)
