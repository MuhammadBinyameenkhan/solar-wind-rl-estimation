"""Reviewer item M2: does the oracle bound depend on the reward weights?

Each of the 24 grid settings (oracle_test.py) is run once on the validation scenarios of the oracle
(scenario_seed + 7). The plant does not depend on the reward, so every cost component of every decision is
recorded once (unweighted, normalised exactly as in VSGEnv.step_params) and the return is then recomputed
for each weighting below. The weightings were fixed before any result was seen:
  base             the weights of the paper
  freq_x5          frequency deviation (outside and inside the band) five times heavier
  rocof_x5         RoCoF beyond the limit five times heavier
  storage_div5     BESS power and VSG fast power five times lighter
  storage_x5       BESS power and VSG fast power five times heavier
For each weighting: best fixed setting, scenario-level oracle gain with a bootstrap 95 % interval.
The episode extremes of the bus voltages are recorded as well (reviewer checklist, voltage range).
Output: study3_ieee33/results/oracle_weights/{components.csv, summary.csv}
Usage:  python study3_ieee33/scripts/oracle_weights.py --n 20 --workers 4
"""
import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from oracle_test import D_GRID, H_GRID  # noqa: E402

from vsgrl.config import load_config  # noqa: E402
from vsgrl.controllers import FixedTunedVSG  # noqa: E402
from vsgrl.data.hybrid import load_processed  # noqa: E402
from vsgrl.envs import make_env  # noqa: E402
from vsgrl.rollout import run_episode  # noqa: E402

OUT = ROOT / "study3_ieee33/results/oracle_weights"
COMP = ["f_out", "f_in", "rocof_out", "bess", "fast", "sat", "viol"]
WEIGHTINGS = {"base": {}, "freq_x5": {"f_out": 5, "f_in": 5}, "rocof_x5": {"rocof_out": 5},
              "storage_div5": {"bess": 0.2, "fast": 0.2}, "storage_x5": {"bess": 5, "fast": 5}}


def job(args):
    cfg, (H, D), n = args
    env = make_env(cfg, load_processed(cfg), "val")
    scs = env.sampler.fixed_set("val", n, cfg["eval"]["scenario_seed"] + 7)
    rw, gc = cfg["env"]["reward"], cfg["system"]["grid_code"]
    W = {"f_out": rw["w_freq"], "f_in": rw.get("w_freq_inband", 0.0), "rocof_out": rw["w_rocof"], "bess": rw["w_bess"],
         "fast": rw.get("w_fast", 0.0), "sat": rw["w_sat"], "viol": rw["w_violation"]}
    acc = {}
    orig = env.mg.advance

    def advance(*a, **kw):                     # record the unweighted, normalised components of each decision
        st = orig(*a, **kw)
        pb = env.mg.Pb_max ** 2
        c = {"f_out": st["msf_excess_hz2"] / gc["f_target_hz"] ** 2, "f_in": st["msf_hz2"] / gc["f_target_hz"] ** 2,
             "rocof_out": st["msr_excess_hz2s2"] / gc["rocof_limit_hz_s"] ** 2, "bess": st["ms_pbess"] / pb,
             "fast": st["ms_pfast"] / pb, "sat": st["mean_sat"] / 0.05, "viol": st["viol_frac"]}
        for k, v in c.items():
            acc[k] = acc.get(k, 0.0) + v
        return st
    env.mg.advance = advance
    ctrl = FixedTunedVSG(cfg, env, h=H, d=D, alpha=0.0)
    rows = []
    for i, sc in enumerate(scs):
        acc.clear()
        m = run_episode(env, ctrl, sc)[0]
        r = {"H": H, "D": D, "scenario": i, "return": m["return"], "collapsed": bool(m.get("collapsed", False)),
             "vmin": env.mg.vmin, "vmax": env.mg.vmax, **{k: acc.get(k, 0.0) for k in COMP}}
        rec = -sum(W[k] * r[k] for k in COMP) - (cfg["env"]["reward"]["collapse_penalty"] if r["collapsed"] else 0.0)
        assert abs(rec - r["return"]) < 1e-6 * max(1.0, abs(r["return"])), (rec, r["return"])   # decomposition is exact
        rows.append(r)
    return rows, W


def summarise(df, W, pen, n_boot=2000):
    rng = np.random.default_rng(0)
    out = []
    for name, mult in WEIGHTINGS.items():
        w = {k: W[k] * mult.get(k, 1.0) for k in COMP}
        R = -sum(w[k] * df[k] for k in COMP) - pen * df["collapsed"]
        P = df.assign(R=R).pivot_table(index="scenario", columns=["H", "D"], values="R").to_numpy()
        cols = df.pivot_table(index="scenario", columns=["H", "D"], values="return").columns
        best = P.mean(0).argmax()
        gain = lambda M: 100 * (M.max(1).mean() - M.mean(0).max()) / abs(M.mean(0).max())   # noqa: E731
        bs = [gain(P[rng.integers(0, len(P), len(P))]) for _ in range(n_boot)]
        out.append({"weighting": name, "best_H": cols[best][0], "best_D": cols[best][1],
                    "R_best_fixed": float(P.mean(0).max()), "R_oracle": float(P.max(1).mean()),
                    "oracle_gain_pct": float(gain(P)), "gain_ci_lo": float(np.percentile(bs, 2.5)),
                    "gain_ci_hi": float(np.percentile(bs, 97.5)),
                    "rank_of_paper_setting": int((P.mean(0) > P.mean(0)[list(cols).index((3.0, 10.0))]).sum()) + 1})
    return pd.DataFrame(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    cfg = load_config(ROOT / "study3_ieee33/configs/ieee33.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(a.workers) as pool:
        res = pool.map(job, [(cfg, g, a.n) for g in itertools.product(H_GRID, D_GRID)])
    W = res[0][1]
    df = pd.DataFrame([r for rows, _ in res for r in rows])
    df.to_csv(OUT / "components.csv", index=False)
    S = summarise(df, W, cfg["env"]["reward"]["collapse_penalty"])
    S.to_csv(OUT / "summary.csv", index=False)
    with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
        print(S.to_string(index=False))
    t = df[(df.H == 3.0) & (df.D == 10.0)]
    print(f"bus voltages, tuned setting (H 3, D 10): {t.vmin.min():.3f}-{t.vmax.max():.3f} pu; "
          f"all settings: {df.vmin.min():.3f}-{df.vmax.max():.3f} pu")
