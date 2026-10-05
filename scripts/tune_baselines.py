"""Grid-search the gains of the adaptive baselines on the VALIDATION split (fair tuning
budget vs RL model selection). Prints a YAML block for eval.baseline_params."""
import itertools

import numpy as np
import yaml
from _common import base_parser, setup

from vsgrl.controllers import BASELINES
from vsgrl.data.hybrid import load_processed
from vsgrl.envs import VSGEnv
from vsgrl.rollout import run_episode

GRIDS = {
    "fixed_tuned": {"h": [1.0, 3.0, 5.0, 8.0], "d": [10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0], "alpha": [0.0, 0.3, 0.7, 1.0]},
    "bang_bang": {"h_big": [4.0, 6.0, 8.0], "h_small": [0.5, 1.5, 3.0]},
    "adaptive_rocof": {"k_h": [0.0, 2.0, 4.0, 8.0], "k_d": [0.0, 30.0, 60.0, 120.0, 240.0, 480.0]},
}

if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--n", type=int, default=40)
    a = p.parse_args()
    cfg = setup(a)
    env = VSGEnv(cfg, load_processed(cfg), split="val", record_trace=True)
    scs = env.sampler.fixed_set("val", a.n, cfg["eval"]["scenario_seed"] + 7)
    best = {}
    for name, grid in GRIDS.items():
        results = []
        for vals in itertools.product(*grid.values()):
            kw = dict(zip(grid.keys(), vals))
            ctrl = BASELINES[name](cfg, env, **kw)
            ret = np.mean([run_episode(env, ctrl, sc)[0]["return"] for sc in scs])
            results.append((ret, kw))
            print(f"{name:15s} {kw}  val return {ret:.2f}")
        best[name] = max(results, key=lambda r: r[0])[1]
    print("\n# paste into configs/default.yaml under eval:")
    print(yaml.safe_dump({"baseline_params": best}, sort_keys=False))
