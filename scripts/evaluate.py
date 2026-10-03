"""Evaluate every controller on the same fixed TEST scenario set.

For RL algorithms every trained seed is evaluated (runs/<tag>/seed*/best.pt).
Outputs (in eval.out_dir):
  scenarios_test.csv     the scenario set (also used for Simulink validation)
  per_scenario.csv       one row per (controller, seed, scenario) with all metrics
  traces/<ctrl>_s<seed>_sc<k>.csv  time series for representative scenarios

Examples
  python scripts/evaluate.py
  python scripts/evaluate.py --controllers fixed bang_bang td3 td3_noheadroom
"""
import copy

import pandas as pd
import torch
import yaml
from _common import base_parser, setup

from vsgrl.agents.td3 import TD3Agent
from vsgrl.config import resolve_path
from vsgrl.controllers import BASELINES, PolicyController, make_baseline
from vsgrl.data.hybrid import load_processed
from vsgrl.envs import VSGEnv
from vsgrl.rollout import run_episode
from vsgrl.scenarios import scenarios_from_frame, scenarios_to_frame


def representative(scs):
    """Indices of: largest under-frequency step, lowest headroom proxy (night/low SoC), an over-frequency event."""
    d = pd.DataFrame([s.to_dict() for s in scs])
    idx = {int(d.dist_mw.idxmax())}
    under = d[d.dist_mw > 0]
    idx.add(int((under.soc0 + under.p_pv_mpp_mw).idxmin()))
    if (d.dist_mw < 0).any():
        idx.add(int(d.dist_mw.idxmin()))
    return sorted(idx)


def controllers_for(names, cfg, df, split, checkpoint="best"):
    """Yield (name, seed, controller, env). An RL run is evaluated with the `env` section it
    was trained with (action mapping, projection), and the current `system` section (so
    robustness studies with --set system.* still apply)."""
    runs = resolve_path(cfg["train"]["out_dir"])
    base_env = VSGEnv(cfg, df, split=split, record_trace=True)
    for n in names:
        if n in BASELINES:
            yield n, 0, make_baseline(n, cfg, base_env), base_env
            continue
        ckpts = sorted((runs / n).glob(f"seed*/{checkpoint}.pt"))
        if not ckpts:
            print(f"[skip] no trained checkpoints for '{n}' in {runs / n}")
            continue
        for ck in ckpts:
            seed = int(ck.parent.name.replace("seed", ""))
            run_cfg_file = ck.parent / "config.yaml"
            c = cfg
            if run_cfg_file.exists():
                run_cfg = yaml.safe_load(run_cfg_file.read_text())
                c = copy.deepcopy(cfg)
                c["env"] = run_cfg["env"]
                # the residual base (tuned fixed VSG) the policy was trained around
                base = (run_cfg.get("eval", {}).get("baseline_params") or {}).get("fixed_tuned")
                if base:
                    c.setdefault("eval", {}).setdefault("baseline_params", {})["fixed_tuned"] = base
            env = VSGEnv(c, df, split=split, record_trace=True)
            label = n if checkpoint == "best" else f"{n}_{checkpoint}"
            yield label, seed, PolicyController(label, TD3Agent.load(ck, cfg["train"])), env


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--controllers", nargs="*", default=None)
    p.add_argument("--n", type=int, default=None, help="number of test scenarios")
    p.add_argument("--split", default="test")
    p.add_argument("--checkpoint", choices=["best", "final"], default="best",
                   help="RL checkpoint: best = validation-selected (default), final = end of training "
                        "(reported as <algo>_final)")
    a = p.parse_args()
    cfg = setup(a)
    torch.set_num_threads(1)   # tiny MLP: one thread per process avoids oversubscription
    out = resolve_path(cfg["eval"]["out_dir"])
    (out / "traces").mkdir(parents=True, exist_ok=True)
    df = load_processed(cfg)
    env = VSGEnv(cfg, df, split=a.split, record_trace=True)

    scen_file = out / f"scenarios_{a.split}.csv"
    n = a.n or cfg["eval"]["n_scenarios"]
    if scen_file.exists() and len(pd.read_csv(scen_file)) == n:
        scs = scenarios_from_frame(pd.read_csv(scen_file))
    else:
        scs = env.sampler.fixed_set(a.split, n, cfg["eval"]["scenario_seed"])
        scenarios_to_frame(scs).to_csv(scen_file, index_label="scenario")
        print(f"{a.split} adequacy-screen rejection rate: {env.sampler.rejection_rate(a.split):.1%}")
    reps = representative(scs)

    rows = []
    for name, seed, ctrl, cenv in controllers_for(a.controllers or cfg["eval"]["controllers"], cfg, df, a.split,
                                               a.checkpoint):
        for k, sc in enumerate(scs):
            m, tr = run_episode(cenv, ctrl, sc)
            rows.append({"controller": name, "seed": seed, "scenario": k, **sc.to_dict(), **m})
            if k in reps:
                tr.to_csv(out / "traces" / f"{name}_s{seed}_sc{k}.csv", index=False)
        sub = pd.DataFrame([r for r in rows if r["controller"] == name and r["seed"] == seed])
        print(f"{name:16s} seed {seed}: nadir {sub.nadir_hz.mean():.3f} Hz  RoCoF {sub.rocof_max_hz_s.mean():.3f} Hz/s"
              f"  BESS {sub.bess_energy_kwh.mean():.3f} kWh  return {sub['return'].mean():.2f}")

    res = pd.DataFrame(rows)
    f = out / "per_scenario.csv"
    if f.exists():  # keep results of controllers not re-run now
        old = pd.read_csv(f)
        res = pd.concat([old[~old.controller.isin(res.controller.unique())], res], ignore_index=True)
    res.to_csv(f, index=False)
    print("wrote", f)
