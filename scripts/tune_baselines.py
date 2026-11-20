"""Grid-search the gains of the baselines on the VALIDATION split (fair tuning budget vs RL model
selection). Two stages: the fixed VSG is tuned first; the adaptive rules are then tuned around it
when eval.adaptive_base = tuned (the same centre as the residual RL policy).
Prints a YAML block for eval.baseline_params and, with --out, writes every score to a CSV.

Examples
  python scripts/tune_baselines.py --workers 4
  python scripts/tune_baselines.py --config study3_ieee33/configs/ieee33.yaml --workers 4 \
      --out study3_ieee33/results/tuning/tune_val.csv
"""
import copy
import json
import itertools
import multiprocessing as mp

import numpy as np
import pandas as pd
import torch
import yaml
from _common import base_parser, setup

from vsgrl.config import resolve_path
from vsgrl.controllers import BASELINES
from vsgrl.data.hybrid import load_processed
from vsgrl.envs import make_env
from vsgrl.rollout import run_episode

FIXED_GRID = {"h": [1.0, 3.0, 5.0, 8.0], "d": [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0]}
ALPHA_GRID = [0.0, 0.3, 0.7, 1.0]          # only when the PV share is an action (env.action_dims = 3)
ADAPTIVE_GRIDS = {
    "bang_bang": {"h_big": [4.0, 6.0, 8.0], "h_small": [0.5, 1.5, 3.0]},
    "adaptive_rocof": {"k_h": [0.0, 2.0, 4.0, 8.0], "k_d": [0.0, 30.0, 60.0, 120.0, 240.0, 480.0]},
    "adaptive_dir": {"k_h": [0.0, 2.0, 4.0, 8.0], "k_d": [0.0, 30.0, 60.0, 120.0, 240.0]},
    "fuzzy": {"k_h": [0.0, 1.0, 2.0, 4.0], "k_d": [0.0, 5.0, 10.0, 20.0, 40.0]},
}

_W = {}


def _init(cfg, n):
    torch.set_num_threads(1)
    env = make_env(cfg, load_processed(cfg), split="val", record_trace=True)
    _W.update(cfg=cfg, env=env, scs=env.sampler.fixed_set("val", n, cfg["eval"]["scenario_seed"] + 7))


def _score(job):
    name, kw = job
    ctrl = BASELINES[name](_W["cfg"], _W["env"], **kw)
    ms = [run_episode(_W["env"], ctrl, sc)[0] for sc in _W["scs"]]
    return {"controller": name, **kw, "val_return": float(np.mean([m["return"] for m in ms])),
            "val_return_sd": float(np.std([m["return"] for m in ms], ddof=1)),
            "nadir_hz": float(np.mean([m["nadir_hz"] for m in ms])),
            "collapse_rate": float(np.mean([m.get("collapsed", False) for m in ms]))}


def _key(name, kw):
    return name + "|" + ",".join(f"{k}={float(v):g}" for k, v in sorted(kw.items()))


def run(cfg, jobs, n, workers, part=None):
    """Score the jobs; with `part` (a JSON-lines file) finished scores are appended as they arrive and
    re-used on a restart, so an interrupted tuning resumes where it stopped (results are identical)."""
    done = {}
    if part is not None and part.exists():
        for line in part.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                done[r["key"]] = r
    todo = [j for j in jobs if _key(*j) not in done]
    print(f"{len(jobs) - len(todo)} of {len(jobs)} scores re-used, {len(todo)} to run", flush=True)

    def keep(r, j):
        r = dict(r, key=_key(*j))
        done[r["key"]] = r
        if part is not None:
            with open(part, "a") as fh:
                fh.write(json.dumps(r) + "\n")
        print(f"  {r['key']}: val return {r['val_return']:.3f}", flush=True)

    if todo and workers > 1:
        with mp.get_context("spawn").Pool(workers, initializer=_init, initargs=(cfg, n)) as pool:
            for j, r in zip(todo, pool.imap(_score, todo, chunksize=1)):
                keep(r, j)
    elif todo:
        _init(cfg, n)
        for j in todo:
            keep(_score(j), j)
    out = []
    for j in jobs:
        out.append({k: v for k, v in done[_key(*j)].items() if k != "key"})
    return out


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--workers", type=int, default=1, help="parallel processes (results are identical)")
    p.add_argument("--only", nargs="*", default=None, help="tune only these baselines")
    p.add_argument("--out", default=None, help="CSV with every score")
    a = p.parse_args()
    cfg = setup(a)
    names = a.only or ["fixed_tuned", *ADAPTIVE_GRIDS]
    act3 = cfg["env"].get("action_dims", 3) >= 3
    best, rows = {}, []
    part = resolve_path(a.out).with_suffix(".partial.jsonl") if a.out else None
    if part is not None:
        part.parent.mkdir(parents=True, exist_ok=True)

    if "fixed_tuned" in names:
        grid = dict(FIXED_GRID, alpha=ALPHA_GRID if act3 else [cfg["system"]["vsg"]["nominal_alpha"]])
        jobs = [("fixed_tuned", dict(zip(grid, v))) for v in itertools.product(*grid.values())]
        out = run(cfg, jobs, a.n, a.workers, part)
        rows += out
        b = max(out, key=lambda r: r["val_return"])
        best["fixed_tuned"] = {k: b[k] for k in grid}
        cfg = copy.deepcopy(cfg)
        cfg["eval"].setdefault("baseline_params", {})["fixed_tuned"] = best["fixed_tuned"]
        print("stage 1, fixed VSG:", best["fixed_tuned"], f"val return {b['val_return']:.3f}", flush=True)

    jobs = [(nm, dict(zip(g, v))) for nm, g in ADAPTIVE_GRIDS.items() if nm in names
            for v in itertools.product(*g.values())]
    if jobs:
        out = run(cfg, jobs, a.n, a.workers, part)
        rows += out
        for nm, g in ADAPTIVE_GRIDS.items():
            res = [r for r in out if r["controller"] == nm]
            if res:
                b = max(res, key=lambda r: r["val_return"])
                best[nm] = {k: b[k] for k in g}

    R = pd.DataFrame(rows)
    with pd.option_context("display.width", 200, "display.max_rows", 500, "display.float_format", "{:.3f}".format):
        print(R.to_string(index=False))
    if a.out:
        f = resolve_path(a.out)
        f.parent.mkdir(parents=True, exist_ok=True)
        R.to_csv(f, index=False)
        print("wrote", f)
    print("\n# paste into the config under eval:")
    print(yaml.safe_dump({"baseline_params": best}, sort_keys=False))
