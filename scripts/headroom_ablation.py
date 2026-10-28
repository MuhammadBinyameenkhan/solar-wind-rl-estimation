"""Headroom-rule ablation: how should a commanded (H, D) be made feasible?

Compares, on the held-out TEST scenarios and the hybrid diesel + VSG plant, fixed VSG settings
under five feasibility treatments:
  none        no constraint (the plant's current limit still clips the delivered power)
  max_clip    band-power projection of this study: D·Δf_band ≤ h and 2H·RoCoF_lim ≤ h, each
              parameter clipped to its own bound
  max_scale   same requirement, H and D scaled by one common factor
  sum_scale   rule of the authors' earlier fully-converter studies: 2H·RoCoF_lim + D·Δf_band ≤ h
              (worst RoCoF and worst deviation at the same instant), common scaling
  sum_scale_wide  sum_scale with the wider limits of the earlier studies (2 Hz/s, 0.5 Hz)

The physical result of an infeasible commitment is converter saturation (time at the current
limit), which is reported next to frequency metrics, BESS energy and the objective return.

Outputs: <eval.out_dir>/headroom_ablation.csv (per scenario), headroom_ablation_summary.csv

Example
  python scripts/headroom_ablation.py --n 200 --workers 4
"""
import copy
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd
from _common import base_parser, setup

from vsgrl.config import resolve_path
from vsgrl.controllers import FixedTunedVSG
from vsgrl.data.hybrid import load_processed
from vsgrl.envs import VSGEnv
from vsgrl.rollout import run_episode
from vsgrl.scenarios import scenarios_from_frame

TREATMENTS = {
    "none": {"env.headroom_constraint": False},
    "max_clip": {"env.headroom_constraint": True, "env.projection": "band_power"},
    "max_scale": {"env.headroom_constraint": True, "env.projection": "max_scale"},
    "sum_scale": {"env.headroom_constraint": True, "env.projection": "sum_scale"},
    "sum_scale_wide": {"env.headroom_constraint": True, "env.projection": "sum_scale",
                       "env.projection_f_hz": 0.5, "env.projection_rocof_hz_s": 2.0},
}
COLS = ["nadir_hz", "rocof_max_hz_s", "time_outside_band_s", "bess_energy_kwh", "saturation_s",
        "infeasible_commit_s", "infeasible_sum_s", "return", "mean_H", "mean_D"]


def _set(cfg, dotted, value):
    d = cfg
    *path, last = dotted.split(".")
    for k in path:
        d = d[k]
    d[last] = value


def _job(args):
    cfg, scen_rows, treatment, name, H, D, alpha = args
    import torch
    torch.set_num_threads(1)
    c = copy.deepcopy(cfg)
    for k, v in TREATMENTS[treatment].items():
        _set(c, k, v)
    env = VSGEnv(c, load_processed(c), split="test", record_trace=True)
    ctrl = FixedTunedVSG(c, env, h=H, d=D, alpha=alpha)
    ctrl.projected = treatment != "none"
    rows = []
    for i, sc in enumerate(scenarios_from_frame(pd.DataFrame(scen_rows))):
        m, tr = run_episode(env, ctrl, sc)
        rows.append({"treatment": treatment, "controller": name, "H_cmd": H, "D_cmd": D, "scenario": i,
                     **{k: m.get(k, np.nan) for k in COLS if not k.startswith("mean_")},
                     "mean_H": float(tr["H_v"].mean()), "mean_D": float(tr["D_v"].mean())})
    return rows


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--n", type=int, default=200, help="number of test scenarios")
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    cfg = setup(a)
    out = resolve_path(cfg["eval"]["out_dir"])
    scen = pd.read_csv(out / "scenarios_test.csv").head(a.n).to_dict("records")
    tuned = cfg["eval"]["baseline_params"]["fixed_tuned"]
    al = tuned.get("alpha", 1.0)
    settings = [("tuned", tuned["h"], tuned["d"]),           # validation-tuned VSG of this study
                ("standard", 3.0, 20.0),                     # nominal VSG
                ("low", 1.0, 10.0),                          # 'Fixed low' of the earlier studies
                ("high", 4.0, 30.0),                         # 'Fixed high' of the earlier studies
                ("range_max", 8.0, 50.0)]                    # largest setting the ranges allow
    jobs = [(cfg, scen, t, n, H, D, al) for t in TREATMENTS for (n, H, D) in settings]
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for r in ex.map(_job, jobs):
            rows += r
            print(f"{r[0]['treatment']:15s} {r[0]['controller']:10s} done "
                  f"(return {np.mean([x['return'] for x in r]):.2f}, sat {np.mean([x['saturation_s'] for x in r]):.3f} s)",
                  flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out / "headroom_ablation.csv", index=False)
    summ = df.groupby(["controller", "treatment"], sort=False)[COLS].mean()
    summ.to_csv(out / "headroom_ablation_summary.csv")
    with pd.option_context("display.width", 200, "display.max_columns", 20, "display.float_format", "{:.3f}".format):
        print(summ)
