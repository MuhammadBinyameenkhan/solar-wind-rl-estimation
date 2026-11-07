"""Grid-search the gains of the adaptive baselines on the VALIDATION split (fair tuning
budget vs RL model selection). Prints a YAML block for eval.baseline_params."""
import itertools
import multiprocessing as mp

import numpy as np
import torch
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

_W = {}


def _init(cfg, n):
    torch.set_num_threads(1)
    env = VSGEnv(cfg, load_processed(cfg), split="val", record_trace=True)
    _W.update(cfg=cfg, env=env, scs=env.sampler.fixed_set("val", n, cfg["eval"]["scenario_seed"] + 7))


def _score(job):
    name, kw = job
    ctrl = BASELINES[name](_W["cfg"], _W["env"], **kw)
    return name, kw, float(np.mean([run_episode(_W["env"], ctrl, sc)[0]["return"] for sc in _W["scs"]]))


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--workers", type=int, default=1, help="parallel processes (results are identical)")
    a = p.parse_args()
    cfg = setup(a)
    jobs = [(name, dict(zip(grid.keys(), vals))) for name, grid in GRIDS.items()
            for vals in itertools.product(*grid.values())]
    if a.workers > 1:
        with mp.get_context("spawn").Pool(a.workers, initializer=_init, initargs=(cfg, a.n)) as pool:
            out = pool.map(_score, jobs, chunksize=1)
    else:
        _init(cfg, a.n)
        out = [_score(j) for j in jobs]
    best = {}
    for name in GRIDS:
        res = [(r, kw) for n_, kw, r in out if n_ == name]
        for r, kw in res:
            print(f"{name:15s} {kw}  val return {r:.2f}")
        best[name] = max(res, key=lambda x: x[0])[1]
    print("\n# paste into configs/default.yaml under eval:")
    print(yaml.safe_dump({"baseline_params": best}, sort_keys=False))
