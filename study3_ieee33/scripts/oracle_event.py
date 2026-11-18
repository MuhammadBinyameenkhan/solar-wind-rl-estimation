"""Event-wise oracle (option 2): how much could a scheduler gain that changes (J_v, D_v) at every load event?

The scenario-level oracle (oracle_test.py / oracle_map.py) picks one (H, D) per scenario. Here the
setting may change at each event of the episode: segment k runs from event k to event k+1 (the first
segment also covers the time before the first event). The best sequence of grid settings is found per
scenario, with hindsight of the event times, by coordinate descent: start from the scenario's best single
setting, then optimise one segment at a time over the 24 grid settings, repeating passes until no segment
improves (at most --passes). Coordinate descent can miss the joint optimum, so the event-wise gain it
reports is a lower estimate of the true event-wise oracle; all scenario-level references are exact.
Switching passes through the same parameter rate limit (env.param_filter_s) as every controller.

Reported per condition:
  R_best_fixed    best single (H, D) over all scenarios
  R_scen_oracle   best (H, D) per scenario
  R_event_oracle  best (H, D) sequence per scenario (coordinate descent)
Output: study3_ieee33/results/oracle_event/{per_scenario.jsonl, summary.csv}
Usage:  python study3_ieee33/scripts/oracle_event.py --n 20 --workers 4 [--condition nominal most_room]
"""
import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle_map import condition_cfg  # noqa: E402
from oracle_test import D_GRID, H_GRID  # noqa: E402

from vsgrl.config import load_config  # noqa: E402
from vsgrl.controllers import BaseController  # noqa: E402
from vsgrl.data.hybrid import load_processed  # noqa: E402
from vsgrl.envs import make_env  # noqa: E402
from vsgrl.rollout import run_episode  # noqa: E402

GRID = list(itertools.product(H_GRID, D_GRID))
OUT = ROOT / "study3_ieee33/results/oracle_event"
# nominal = the published plant; most_room = the practical condition with the largest scenario-level
# oracle gain in the oracle map (BESS 1.0 x peak, diesel 4.9 MVA, half-size events: 2.7 %)
CONDITIONS = {"nominal": None, "most_room": (1.0, 4.9, 0.5)}


class ScheduleVSG(BaseController):
    """Fixed VSG whose (H, D) switch at given times: settings[k] applies from switch_s[k]."""
    name = "schedule"

    def __init__(self, cfg, env, switch_s, settings):
        super().__init__(cfg, env)
        self.sw, self.st = list(switch_s), list(settings)
        self.dt = cfg["env"]["agent_dt_s"]
        self.k = 0

    def reset(self):
        self.k = 0

    def params(self, obs):
        t = self.k * self.dt
        self.k += 1
        i = max(j for j, s in enumerate(self.sw) if t >= s - 1e-9)
        H, D = self.st[i]
        return H, D, self.a0


def solve(args):
    cname, cfg, i, sc, passes = args
    env = make_env(cfg, load_processed(cfg), "val")
    ev = [t for t, _ in sc.event_list()]
    switch = [0.0] + ev[1:]                     # segment k starts at event k (k >= 2)

    def R(seq):
        return run_episode(env, ScheduleVSG(cfg, env, switch, seq), sc)[0]["return"]

    single = {g: R([g] * len(switch)) for g in GRID}
    g0 = max(single, key=single.get)
    seq, best, n_eval = [g0] * len(switch), single[g0], len(GRID)
    for _ in range(passes if len(switch) > 1 else 0):
        improved = False
        for k in range(len(switch)):
            for g in GRID:
                if g == seq[k]:
                    continue
                s2 = seq[:k] + [g] + seq[k + 1:]
                r = R(s2)
                n_eval += 1
                if r > best + 1e-9:
                    seq, best, improved = s2, r, True
        if not improved:
            break
    return {"condition": cname, "scenario": i, "n_events": len(ev), "switch_s": switch,
            "single": {f"H{h:g}_D{d:g}": v for (h, d), v in single.items()},
            "scen_oracle": single[g0], "scen_best": list(g0), "event_oracle": best,
            "event_seq": [list(g) for g in seq], "episodes_run": n_eval}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--condition", nargs="+", default=list(CONDITIONS), choices=list(CONDITIONS))
    a = ap.parse_args()
    base = load_config(ROOT / "study3_ieee33/configs/ieee33.yaml")
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / "per_scenario.jsonl"
    done = set()
    if f.exists():
        done = {(r["condition"], r["scenario"]) for r in map(json.loads, f.read_text().splitlines()) if r}
    jobs = []
    for cname in a.condition:
        c = CONDITIONS[cname]
        cfg = base if c is None else condition_cfg(base, *c)
        env = make_env(cfg, load_processed(cfg), "val")
        scs = env.sampler.fixed_set("val", a.n, cfg["eval"]["scenario_seed"] + 7)   # as in oracle_map.py
        jobs += [(cname, cfg, i, sc, a.passes) for i, sc in enumerate(scs) if (cname, i) not in done]
    print(f"{len(jobs)} scenario jobs to run", flush=True)
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(a.workers) as pool:
        for r in pool.imap_unordered(solve, jobs):
            with open(f, "a") as fh:
                fh.write(json.dumps(r) + "\n")
            print(f"  {r['condition']} sc {r['scenario']}: {r['n_events']} events, scenario oracle "
                  f"{r['scen_oracle']:.3f}, event oracle {r['event_oracle']:.3f} ({r['episodes_run']} episodes)",
                  flush=True)

    rows = [json.loads(x) for x in f.read_text().splitlines() if x]
    summ = []
    for cname in a.condition:
        rs = sorted((r for r in rows if r["condition"] == cname), key=lambda r: r["scenario"])
        S = pd.DataFrame([r["single"] for r in rs])
        best_col = S.mean().idxmax()
        r_fix = S[best_col].mean()
        r_sc = np.mean([r["scen_oracle"] for r in rs])
        r_ev = np.mean([r["event_oracle"] for r in rs])
        summ.append({"condition": cname, "n_scen": len(rs), "best_fixed": best_col, "R_best_fixed": r_fix,
                     "R_scen_oracle": r_sc, "R_event_oracle": r_ev,
                     "scen_gain_pct": 100 * (r_sc - r_fix) / abs(r_fix),
                     "event_gain_pct": 100 * (r_ev - r_fix) / abs(r_fix),
                     "event_over_scen_pct": 100 * (r_ev - r_sc) / abs(r_fix),
                     "scen_event_gt_1pct": int(sum((r["event_oracle"] - S[best_col][k]) / abs(S[best_col][k]) > 0.01
                                                   for k, r in enumerate(rs)))})
    T = pd.DataFrame(summ)
    T.to_csv(OUT / "summary.csv", index=False)
    with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
        print(T.to_string(index=False))
