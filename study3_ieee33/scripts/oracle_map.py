"""Oracle map: how much could ANY scenario-level (J_v, D_v) scheduler gain, as a function of the plant sizing?

For every plant condition the oracle of scripts/oracle_test.py is computed (same 24-setting grid, validation
scenarios): best single fixed setting vs. the best setting chosen per scenario. Only the sizing is varied;
all control parameters stay at their sourced values (configs/ieee33.yaml, DESIGN.md).

Dimensions (author decision 18 Nov 2026, option 1):
  bess   BESS power as a fraction of the published peak load 3.715 MW (energy = 4 h at that power)
  dsl    diesel rating in MVA (published machine per-unit data; P = 0.8 x MVA; X'_d on S_base recomputed)
  ev     factor on the load-step sizes and the cumulative-step limit

Output: study3_ieee33/results/oracle_map/{grid_returns.csv (per condition, setting, scenario), summary.csv}
Usage:  python study3_ieee33/scripts/oracle_map.py --n 20 --workers 4
"""
import argparse
import copy
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from _common import make_env  # noqa: E402
from oracle_test import D_GRID, H_GRID  # noqa: E402

from vsgrl.config import load_config  # noqa: E402
from vsgrl.controllers import FixedTunedVSG  # noqa: E402
from vsgrl.data.hybrid import load_processed  # noqa: E402
from vsgrl.rollout import run_episode  # noqa: E402

P_PEAK = 3.715
BESS = [0.25, 0.625, 1.0]
DSL = [2.45, 4.9]
EV = [0.5, 1.0]
OUT = ROOT / "study3_ieee33/results/oracle_map"


def condition_cfg(base, bess, dsl, ev):
    c = copy.deepcopy(base)
    s = c["system"]
    s["bess"]["power_mw"] = bess * P_PEAK
    s["bess"]["energy_mwh"] = 4.0 * bess * P_PEAK
    m = s["diesel"]["machine"]
    s["diesel"]["rated_mw"] = 0.8 * dsl
    m["rated_mva"] = dsl
    s["diesel"]["sync_coeff_pu"] = 1.0 / (m["xdp"] * s["s_base_mva"] / dsl)
    d = s["disturbance"]
    d["step_mw_range"] = [x * ev for x in d["step_mw_range"]]
    d["max_cumulative_mw"] *= ev
    d["design_step_mw"] *= ev
    return c


def job(args):
    base, (bess, dsl, ev), (H, D), n = args
    cfg = condition_cfg(base, bess, dsl, ev)
    env = make_env(cfg, load_processed(cfg), "val")
    scs = env.sampler.fixed_set("val", n, cfg["eval"]["scenario_seed"] + 7)
    ctrl = FixedTunedVSG(cfg, env, h=H, d=D, alpha=0.0)
    rows = []
    for i, sc in enumerate(scs):
        m = run_episode(env, ctrl, sc)[0]
        rows.append({"bess_frac": bess, "diesel_mva": dsl, "event_factor": ev, "H": H, "D": D, "scenario": i,
                     "return": m["return"], "nadir_hz": m["nadir_hz"], "collapsed": m.get("collapsed", False)})
    st = env.sampler.stats.get("val", {})
    for r in rows:
        r["screen_rejected_frac"] = st.get("rejected", 0) / max(st.get("drawn", 1), 1)
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    base = load_config(ROOT / "study3_ieee33/configs/ieee33.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "grid_returns.csv"
    done = set()
    if f.exists():
        prev = pd.read_csv(f)
        done = set(map(tuple, prev[["bess_frac", "diesel_mva", "event_factor", "H", "D"]].values.tolist()))
    conds = list(itertools.product(BESS, DSL, EV))
    jobs = [(base, c, hd, a.n) for c in conds for hd in itertools.product(H_GRID, D_GRID)
            if (*c, *hd) not in done]
    print(f"{len(conds)} conditions x {len(H_GRID) * len(D_GRID)} settings; {len(jobs)} jobs to run", flush=True)
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(a.workers) as pool:
        for k, rows in enumerate(pool.imap_unordered(job, jobs), 1):
            pd.DataFrame(rows).to_csv(f, mode="a", header=not f.exists(), index=False)
            print(f"  {k}/{len(jobs)} done: bess {rows[0]['bess_frac']}, diesel {rows[0]['diesel_mva']} MVA, "
                  f"ev {rows[0]['event_factor']}, H={rows[0]['H']:g}, D={rows[0]['D']:g}", flush=True)

    G = pd.read_csv(f)
    summ = []
    for c, g in G.groupby(["bess_frac", "diesel_mva", "event_factor"]):
        R = g.pivot_table(index="scenario", columns=["H", "D"], values="return")
        best = R.mean().idxmax()
        r_fix, r_or = R.mean().max(), R.max(axis=1).mean()
        summ.append({"bess_frac": c[0], "bess_mw": c[0] * P_PEAK, "diesel_mva": c[1], "event_factor": c[2],
                     "best_H": best[0], "best_D": best[1], "R_best_fixed": r_fix, "R_oracle": r_or,
                     "oracle_gain": r_or - r_fix, "oracle_gain_pct": 100 * (r_or - r_fix) / abs(r_fix),
                     "scen_gain_gt_1pct": int(((R.max(axis=1) - R[best]) / R[best].abs() > 0.01).sum()),
                     "n_scen": len(R), "collapse_frac_best": float(g[(g.H == best[0]) & (g.D == best[1])].collapsed.mean()),
                     "screen_rejected_frac": float(g.screen_rejected_frac.max())})
    S = pd.DataFrame(summ).sort_values("oracle_gain_pct", ascending=False)
    S.to_csv(OUT / "summary.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20, "display.float_format", "{:.3f}".format):
        print(S.to_string(index=False))
