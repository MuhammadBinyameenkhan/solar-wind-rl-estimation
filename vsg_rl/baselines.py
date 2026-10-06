"""
Non-learning controllers and their fair tuning.

A learned controller is only interesting if it beats the best controller
that does NOT learn, tuned with the same information.  Two such baselines
are provided, both tuned on the VALIDATION episodes (never on the test
scenarios) by maximising the SAME reward the RL agents maximise:

  fixed_tuned    best constant (J, D, Kq) from a grid
  adaptive_rule  rule-based adaptive VSG in the spirit of Alipoor et al.
                 (2014) and Li et al. (2016): extra inertia while the
                 deviation is growing, extra damping proportional to |df|
"""
import json
import os
from concurrent.futures import ProcessPoolExecutor
from itertools import product

import numpy as np

from . import config as C
from .env import MicrogridVSGEnv
from .utils import log


class FixedPolicy:
    def __init__(self, J: float, D: float, Kq: float | None = None):
        self.a = np.array([J, D, C.KQ_VSG if Kq is None else Kq], dtype=float)

    def __call__(self, s):
        return self.a


class AdaptiveRulePolicy:
    """J = J0 + kJ |RoCoF| while |df| is growing, else J0;  D = D0 + kD |df|.

    Uses only the measured (PLL) frequency and RoCoF from the observation.
    Kq is a tuned constant: the agents adapt Kq, so a baseline stuck at the
    default droop would lose on the voltage term for reasons unrelated to
    frequency control.
    """

    def __init__(self, J0, kJ, D0, kD, Kq=None):
        self.J0, self.kJ, self.D0, self.kD = J0, kJ, D0, kD
        self.Kq = C.KQ_VSG if Kq is None else Kq

    def __call__(self, s):
        df = float(s[0]) * 0.5                  # Hz
        rocof = float(s[1]) * C.ROCOF_LIMIT     # Hz/s
        growing = df * rocof > 0.0
        J = self.J0 + (self.kJ * abs(rocof) if growing else 0.0)
        D = self.D0 + self.kD * abs(df)
        return np.array([min(J, C.J_MAX), min(D, C.D_MAX), self.Kq])

    def params(self):
        return dict(J0=self.J0, kJ=self.kJ, D0=self.D0, kD=self.kD, Kq=self.Kq)


RULE_GRID = dict(J0=[0.0, 0.5], kJ=[0.0, 5.0], D0=[10.0, 20.0, 30.0],
                 kD=[0.0, 40.0, 80.0], Kq=[8.0, 14.0, 20.0])


# ----------------------------------------------------------------
# Validation set (shared with RL model selection)
# ----------------------------------------------------------------
def validation_episodes():
    return [(C.EVAL_SCENARIOS[i % len(C.EVAL_SCENARIOS)], C.VAL_SEED0 + i)
            for i in range(C.N_VAL)]


def validation_score(policy) -> float:
    """Mean episode return over the fixed validation episodes."""
    env = MicrogridVSGEnv(stochastic=True)
    total = 0.0
    for sc, seed in validation_episodes():
        env.scenario = sc
        total += env.rollout(policy, seed=seed)["total_reward"]
    return total / C.N_VAL


def _score_job(spec):
    kind, params = spec
    pol = FixedPolicy(*params) if kind == "fixed" else AdaptiveRulePolicy(*params)
    return spec, validation_score(pol)


def tune_baselines(workers: int = 4, cache: str | None = None, fresh: bool = False):
    """Grid-search both tunable baselines on the validation set (cached)."""
    cache = cache or C.out_path("tuned_baselines.json")
    if not fresh and os.path.exists(cache):
        with open(cache) as fh:
            return json.load(fh)
    specs = [("fixed", p) for p in product(C.FIXED_GRID_J, C.FIXED_GRID_D, C.FIXED_GRID_KQ)]
    specs += [("rule", p) for p in product(*RULE_GRID.values())]
    log(f"[baselines] tuning on {C.N_VAL} validation episodes: "
        f"{len(specs)} candidates, {workers} workers ...")
    with ProcessPoolExecutor(max_workers=workers) as ex:
        scored = list(ex.map(_score_job, specs))
    fixed = [(p, s) for (k, p), s in scored if k == "fixed"]
    rule = [(p, s) for (k, p), s in scored if k == "rule"]
    (Jb, Db, Kb), sf = max(fixed, key=lambda x: x[1])
    pr, sr = max(rule, key=lambda x: x[1])
    out = dict(
        fixed_tuned=dict(J=Jb, D=Db, Kq=Kb, val_return=sf),
        adaptive_rule=dict(zip(RULE_GRID.keys(), pr), val_return=sr),
        fixed_grid=[dict(J=p[0], D=p[1], Kq=p[2], val_return=s) for p, s in fixed],
    )
    with open(cache, "w") as fh:
        json.dump(out, fh, indent=1)
    log(f"[baselines] fixed_tuned   J={Jb} D={Db} Kq={Kb}  val return {sf:.1f}")
    log(f"[baselines] adaptive_rule {dict(zip(RULE_GRID.keys(), pr))}  val return {sr:.1f}")
    return out


def make_policy(name: str, agents: dict | None = None, tuned: dict | None = None):
    if name in C.BASELINES:
        b = C.BASELINES[name]
        return FixedPolicy(b["J"], b["D"])
    if name == "fixed_tuned":
        t = tuned["fixed_tuned"]
        return FixedPolicy(t["J"], t["D"], t.get("Kq"))
    if name == "adaptive_rule":
        t = tuned["adaptive_rule"]
        return AdaptiveRulePolicy(t["J0"], t["kJ"], t["D0"], t["kD"], t.get("Kq"))
    agent = (agents or {}).get(name)
    if agent is None:
        raise ValueError(f"controller '{name}' needs a trained agent")
    return agent.policy()
