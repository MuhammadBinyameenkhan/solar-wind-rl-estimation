"""Benchmark controllers. All act on the same 50 ms decision grid as the RL agent.

none            no fast frequency support (diesel only) — reference, usually collapses
droop           grid-following BESS/PV droop, P = −D Δf (fast frequency response, no inertia)
fixed           VSG with constant (H, D, alpha) — the standard VSG
fixed_tuned     constant VSG parameters grid-searched on the validation split
fixed_feasible  the tuned fixed VSG passed through the same headroom projection as RL
bang_bang       adaptive-inertia VSG (Alipoor, Miura & Ise, IEEE JESTPE 2015):
                H = H_big while the frequency is moving away from nominal, H_small otherwise
adaptive_rocof  self-adaptive VSG: H and D grow with |RoCoF| and |Δf| (common in the
                adaptive-VSG literature; gains chosen once on the validation split)
adaptive_dir    direction-aware self-adaptive VSG (rule of the self-adaptive inertia and damping
                combination control, Li et al. 2017): H grows with |RoCoF| only while the frequency
                moves away from nominal, D grows with |Δf|
fuzzy           fuzzy-logic (H, D) scheduler: zero-order Sugeno rule base on (Δf, RoCoF) with
                triangular N/Z/P sets; input scales = grid-code band and RoCoF limit; output gains
                tuned on the validation split
With eval.adaptive_base = tuned, the adaptive rules (bang_bang, adaptive_rocof, adaptive_dir, fuzzy)
are centred on the tuned fixed VSG, i.e. the same base as the residual RL policy.
td3 / ddpg      learned policies (see vsgrl/agents)
"""
from __future__ import annotations

import numpy as np


class BaseController:
    name = "base"
    mode = "vsg"
    projected = False          # True → applied parameters are clipped to the feasible bounds

    def __init__(self, cfg, env, **_):
        self.cfg, self.env = cfg, env
        v = cfg["system"]["vsg"]
        self.H0, self.D0, self.a0 = v["nominal_h_s"], v["nominal_d_pu"], v["nominal_alpha"]
        self.hmin, self.hmax = v["h_min_s"], v["h_max_s"]
        self.dmin, self.dmax = v["d_min_pu"], v["d_max_pu"]

    def reset(self):
        pass

    def params(self, obs):
        raise NotImplementedError

    def step(self, env, obs):
        H, D, a = self.params(obs)
        H = float(np.clip(H, self.hmin, self.hmax))
        D = float(np.clip(D, self.dmin, self.dmax))
        return env.step_params(H, D, a, mode=self.mode, enforce_bounds=self.projected and env.headroom_constraint)


class NoSupport(BaseController):
    name, mode = "none", "none"

    def params(self, obs):
        return self.hmin, 0.0, 0.0


class Droop(BaseController):
    name, mode = "droop", "droop"

    def params(self, obs):
        return self.hmin, self.D0, self.a0


class FixedVSG(BaseController):
    name = "fixed"

    def params(self, obs):
        return self.H0, self.D0, self.a0


class FixedTunedVSG(BaseController):
    """Fixed VSG whose (H, D, alpha) are grid-searched on the validation split
    (scripts/tune_baselines.py) — the strongest non-adaptive benchmark."""
    name = "fixed_tuned"

    def __init__(self, cfg, env, h=None, d=None, alpha=None, **_):
        super().__init__(cfg, env)
        self.h = self.H0 if h is None else h
        self.d = self.D0 if d is None else d
        self.al = self.a0 if alpha is None else alpha

    def params(self, obs):
        return self.h, self.d, self.al


class FixedFeasibleVSG(BaseController):
    """The tuned fixed VSG passed through the same headroom projection as the RL agent."""
    name = "fixed_feasible"
    projected = True

    def __init__(self, cfg, env, **_):
        super().__init__(cfg, env)
        t = (cfg.get("eval", {}).get("baseline_params") or {}).get("fixed_tuned") or {}
        self.H0, self.D0, self.a0 = t.get("h", self.H0), t.get("d", self.D0), t.get("alpha", self.a0)

    def params(self, obs):
        h_ub, d_ub = self.env.param_bounds()
        return min(self.H0, h_ub), min(self.D0, d_ub), self.a0


def _tuned_base(ctrl, cfg):
    """Centre an adaptive rule on the tuned fixed VSG when eval.adaptive_base == 'tuned'."""
    if (cfg.get("eval") or {}).get("adaptive_base", "nominal") == "tuned":
        t = (cfg["eval"].get("baseline_params") or {}).get("fixed_tuned") or {}
        ctrl.H0, ctrl.D0, ctrl.a0 = t.get("h", ctrl.H0), t.get("d", ctrl.D0), t.get("alpha", ctrl.a0)


class BangBangVSG(BaseController):
    name = "bang_bang"

    def __init__(self, cfg, env, h_big=None, h_small=None, thr_hz=0.01, **_):
        super().__init__(cfg, env)
        _tuned_base(self, cfg)
        self.h_big = h_big or 2.0 * self.H0
        self.h_small = h_small or 0.5 * self.H0
        self.thr = thr_hz / cfg["system"]["grid_code"]["f_target_hz"]

    def params(self, obs):
        df, rocof = obs[0], obs[1]
        if abs(df) < self.thr:
            return self.H0, self.D0, self.a0
        return (self.h_big if df * rocof > 0 else self.h_small), self.D0, self.a0


class AdaptiveRocofVSG(BaseController):
    name = "adaptive_rocof"

    def __init__(self, cfg, env, k_h=4.0, k_d=60.0, **_):
        super().__init__(cfg, env)
        _tuned_base(self, cfg)
        gc = cfg["system"]["grid_code"]
        self.k_h, self.k_d = k_h, k_d          # s per (Hz/s), pu per Hz
        self.rs, self.fs = gc["rocof_limit_hz_s"], gc["f_target_hz"]

    def params(self, obs):
        rocof_hz = abs(obs[1]) * self.rs
        df_hz = abs(obs[0]) * self.fs
        return self.H0 + self.k_h * rocof_hz, self.D0 + self.k_d * df_hz, self.a0


class AdaptiveDirectionalVSG(BaseController):
    """H = H0 + k_h |RoCoF| while Δf·RoCoF > 0 (frequency moving away) and |Δf| > thr, else H0;
    D = D0 + k_d |Δf|. Units: k_h in s per Hz/s, k_d in pu per Hz."""
    name = "adaptive_dir"

    def __init__(self, cfg, env, k_h=0.0, k_d=0.0, thr_hz=0.01, **_):
        super().__init__(cfg, env)
        _tuned_base(self, cfg)
        gc = cfg["system"]["grid_code"]
        self.k_h, self.k_d, self.thr = k_h, k_d, thr_hz
        self.rs, self.fs = gc["rocof_limit_hz_s"], gc["f_target_hz"]

    def params(self, obs):
        df_hz, rocof_hz = obs[0] * self.fs, obs[1] * self.rs
        away = df_hz * rocof_hz > 0.0 and abs(df_hz) > self.thr
        return self.H0 + (self.k_h * abs(rocof_hz) if away else 0.0), self.D0 + self.k_d * abs(df_hz), self.a0


class FuzzyVSG(BaseController):
    """Zero-order Sugeno fuzzy scheduler of (H, D).

    Inputs, normalised and clipped to [-1, 1]: x = Δf / f_band, y = RoCoF / RoCoF_lim, with f_band the
    reward band (env.reward.f_band_hz) and RoCoF_lim the grid-code limit. Each input has the three
    triangular sets N(x) = max(0, -x), Z(x) = 1 - |x|, P(x) = max(0, x) (a partition of unity).
    Rules (product inference, weighted-average defuzzification):
      H: (N,N) and (P,P) frequency moving away  -> +1  (large inertia)
         (N,P) and (P,N) frequency recovering   -> -1  (small inertia, faster return)
         any Z                                   ->  0  (base inertia)
      D: Δf is N or P -> +1, Δf is Z -> 0
    H = H0 + k_h * u_H, D = D0 + k_d * u_D; k_h (s) and k_d (pu) are tuned on the validation split."""
    name = "fuzzy"

    def __init__(self, cfg, env, k_h=0.0, k_d=0.0, **_):
        super().__init__(cfg, env)
        _tuned_base(self, cfg)
        gc, rw = cfg["system"]["grid_code"], cfg["env"]["reward"]
        self.k_h, self.k_d = k_h, k_d
        self.fs, self.rs = gc["f_target_hz"], gc["rocof_limit_hz_s"]
        self.fb = rw.get("f_band_hz") or gc["f_target_hz"]

    @staticmethod
    def _sets(v):
        v = float(np.clip(v, -1.0, 1.0))
        return max(0.0, -v), 1.0 - abs(v), max(0.0, v)

    def params(self, obs):
        nx, zx, px = self._sets(obs[0] * self.fs / self.fb)
        ny, zy, py = self._sets(obs[1])                 # obs[1] is RoCoF / RoCoF_lim
        u_h = (nx * ny + px * py) - (nx * py + px * ny)  # weights sum to 1 over the 9 rules
        u_d = nx + px
        return self.H0 + self.k_h * u_h, self.D0 + self.k_d * u_d, self.a0


class PolicyController:
    """Wraps a trained actor (deterministic) as a controller."""
    mode = "vsg"

    def __init__(self, name, agent):
        self.name, self.agent = name, agent

    def reset(self):
        pass

    def step(self, env, obs):
        return env.step(self.agent.act(obs, noise=0.0))


BASELINES = {c.name: c for c in [NoSupport, Droop, FixedVSG, FixedTunedVSG, FixedFeasibleVSG, BangBangVSG, AdaptiveRocofVSG,
                                AdaptiveDirectionalVSG, FuzzyVSG]}


def make_baseline(name, cfg, env):
    """Instantiate a baseline with gains from cfg['eval']['baseline_params'][name] if present
    (written by scripts/tune_baselines.py)."""
    kw = (cfg.get("eval", {}).get("baseline_params") or {}).get(name, {}) or {}
    return BASELINES[name](cfg, env, **kw)
