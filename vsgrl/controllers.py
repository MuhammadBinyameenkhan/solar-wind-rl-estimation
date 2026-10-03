"""Benchmark controllers. All act on the same 50 ms decision grid as the RL agent.

none            no fast frequency support (diesel only) — reference, usually collapses
droop           grid-following BESS/PV droop, P = −D Δf (fast frequency response, no inertia)
fixed           VSG with constant (H, D, alpha) — the standard VSG
fixed_tuned     constant VSG parameters grid-searched on the validation split
fixed_feasible  constant VSG parameters passed through the same headroom projection as RL
bang_bang       adaptive-inertia VSG (Alipoor, Miura & Ise, IEEE JESTPE 2015):
                H = H_big while the frequency is moving away from nominal, H_small otherwise
adaptive_rocof  self-adaptive VSG: H and D grow with |RoCoF| and |Δf| (common in the
                adaptive-VSG literature; gains chosen once on the validation split)
td3 / ddpg      learned policies (see vsgrl/agents)
"""
from __future__ import annotations

import numpy as np


class BaseController:
    name = "base"
    mode = "vsg"

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
        return env.step_params(H, D, a, mode=self.mode)


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
    name = "fixed_feasible"

    def params(self, obs):
        h_ub, d_ub = self.env.param_bounds()
        return min(self.H0, h_ub), min(self.D0, d_ub), self.a0


class BangBangVSG(BaseController):
    name = "bang_bang"

    def __init__(self, cfg, env, h_big=None, h_small=None, thr_hz=0.01, **_):
        super().__init__(cfg, env)
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
        gc = cfg["system"]["grid_code"]
        self.k_h, self.k_d = k_h, k_d          # s per (Hz/s), pu per Hz
        self.rs, self.fs = gc["rocof_limit_hz_s"], gc["f_target_hz"]

    def params(self, obs):
        rocof_hz = abs(obs[1]) * self.rs
        df_hz = abs(obs[0]) * self.fs
        return self.H0 + self.k_h * rocof_hz, self.D0 + self.k_d * df_hz, self.a0


class PolicyController:
    """Wraps a trained actor (deterministic) as a controller."""
    mode = "vsg"

    def __init__(self, name, agent):
        self.name, self.agent = name, agent

    def reset(self):
        pass

    def step(self, env, obs):
        return env.step(self.agent.act(obs, noise=0.0))


BASELINES = {c.name: c for c in [NoSupport, Droop, FixedVSG, FixedTunedVSG, FixedFeasibleVSG, BangBangVSG, AdaptiveRocofVSG]}


def make_baseline(name, cfg, env):
    """Instantiate a baseline with gains from cfg['eval']['baseline_params'][name] if present
    (written by scripts/tune_baselines.py)."""
    kw = (cfg.get("eval", {}).get("baseline_params") or {}).get(name, {}) or {}
    return BASELINES[name](cfg, env, **kw)
