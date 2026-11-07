"""Go/no-go check BEFORE training: how much could ANY adaptive (H, D) scheduler gain?

It evaluates a grid of FIXED VSGs on validation scenarios and compares
  * the best single fixed VSG (one setting for all scenarios), with
  * a per-scenario oracle (the best fixed setting chosen separately for each scenario,
    i.e. a controller that knows the operating point and the coming events in advance).

The oracle gain is an upper-bound proxy for what scenario-level adaptation can add. If it
is small (rule of thumb < 5 % of the return), RL is unlikely to beat a well-tuned fixed VSG,
so change the plant or reward first. It also reports how the oracle's choice depends on
the available headroom — the "feasible synthetic inertia" signal.

Example
  python scripts/oracle_test.py --n 40
  python scripts/oracle_test.py --set system.ems.enabled=false
"""
import itertools

import numpy as np
import pandas as pd
from _common import base_parser, setup

from vsgrl.controllers import FixedTunedVSG
from vsgrl.data.hybrid import load_processed
from vsgrl.envs import VSGEnv
from vsgrl.rollout import run_episode

H_GRID = [1.0, 3.0, 5.0, 8.0]
D_GRID = [5.0, 10.0, 15.0, 20.0, 30.0, 50.0]

if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--n", type=int, default=40, help="validation scenarios")
    p.add_argument("--alpha", type=float, default=0.7)
    a = p.parse_args()
    cfg = setup(a)
    env = VSGEnv(cfg, load_processed(cfg), split="val", record_trace=True)
    scs = env.sampler.fixed_set("val", a.n, cfg["eval"]["scenario_seed"] + 7)

    combos = list(itertools.product(H_GRID, D_GRID))
    R = np.zeros((len(scs), len(combos)))
    head = []
    for i, sc in enumerate(scs):
        env.mg.reset(sc, 1.0)
        head.append(env.mg.headroom_up() * env.mg.Sb)
    for j, (H, D) in enumerate(combos):
        ctrl = FixedTunedVSG(cfg, env, h=H, d=D, alpha=a.alpha)
        for i, sc in enumerate(scs):
            R[i, j] = run_episode(env, ctrl, sc)[0]["return"]
        print(f"H={H:3.0f} s  D={D:4.0f} pu   mean return {R[:, j].mean():8.2f}")

    mean = R.mean(0)
    jb = int(mean.argmax())
    oracle = R.max(1)
    gain = oracle.mean() - mean[jb]
    print(f"\nbest single fixed VSG : H={combos[jb][0]:.0f} s, D={combos[jb][1]:.0f}  →  {mean[jb]:.2f}")
    print(f"per-scenario oracle   : {oracle.mean():.2f}")
    print(f"oracle gain           : {gain:.2f}  ({100 * gain / abs(mean[jb]):.1f} % of the best fixed return)")

    # does the oracle's choice depend on headroom?
    best = [combos[k] for k in R.argmax(1)]
    df = pd.DataFrame({"headroom_up_mw": head, "H_best": [b[0] for b in best], "D_best": [b[1] for b in best],
                       "gain": oracle - R[:, jb]})
    df["headroom_bin"] = pd.qcut(df.headroom_up_mw, 3, labels=["low", "mid", "high"])
    print("\nOracle choice vs available upward headroom:")
    print(df.groupby("headroom_bin", observed=True)[["headroom_up_mw", "H_best", "D_best", "gain"]].mean().round(2))
    verdict = "GO — adaptation has room to help" if gain / abs(mean[jb]) >= 0.05 else \
        "NO-GO — a tuned fixed VSG is near-optimal; change the plant/reward first"
    print(f"\nVerdict: {verdict}")
