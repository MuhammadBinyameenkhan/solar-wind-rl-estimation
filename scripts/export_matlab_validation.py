"""Export a MATLAB cross-validation package (run this, then matlab/run_matlab_validation.m).

Writes to matlab/export/:
  vsgrl_params.mat       all system / env parameters (flattened, same as export_matlab.py)
  vsgrl_policy_val.mat   actor weights of the chosen RL run + action-mapping fields
  vsgrl_validation.mat   N test scenarios, their exact wind/load noise sequences, the Python
                         dispatch, and Python reference traces + metrics for three controllers:
                         fixed_tuned, fixed_feasible, and the RL policy

The MATLAB implementation (matlab/sim/) re-simulates the same scenarios from scratch; matching
traces show the MATLAB model is a faithful, independent implementation of the Python one.

Example
  python scripts/export_matlab_validation.py --n 12 --algo td3 --checkpoint final --seed 1
"""
import copy

import numpy as np
import pandas as pd
import torch
import yaml
from _common import ROOT, base_parser, setup
from export_matlab import _residual_base, flatten
from scipy.io import savemat

from vsgrl.agents.td3 import TD3Agent
from vsgrl.config import resolve_path
from vsgrl.controllers import PolicyController, make_baseline
from vsgrl.data.hybrid import load_processed
from vsgrl.envs import OBS_NAMES, VSGEnv
from vsgrl.rollout import run_episode
from vsgrl.scenarios import scenarios_from_frame

TRACE_KEYS = ["df_hz", "rocof_hz_s", "p_vsg_mw", "p_bess_mw", "p_diesel_mw", "soc", "H_v", "D_v", "alpha",
              "p_set_mw", "headroom_mw"]
METRIC_KEYS = ["nadir_hz", "rocof_max_hz_s", "bess_energy_kwh", "infeasible_commit_s", "saturation_s", "return"]

if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--n", type=int, default=12, help="number of test scenarios")
    p.add_argument("--algo", default="td3")
    p.add_argument("--checkpoint", choices=["best", "final"], default="final")
    p.add_argument("--seed", type=int, default=1)
    a = p.parse_args()
    cfg = setup(a)
    torch.set_num_threads(1)
    dst = ROOT / "matlab" / "export"
    dst.mkdir(parents=True, exist_ok=True)

    # --- parameters ----------------------------------------------------
    params = {k[:63]: v for k, v in flatten({"system": cfg["system"], "env": cfg["env"]}).items()}
    savemat(dst / "vsgrl_params.mat", params)

    # --- RL policy (with the env settings it was trained with) -----------
    run = resolve_path(cfg["train"]["out_dir"]) / a.algo / f"seed{a.seed}"
    run_cfg = yaml.safe_load((run / "config.yaml").read_text())
    pcfg = copy.deepcopy(cfg)
    pcfg["env"] = run_cfg["env"]
    base = (run_cfg.get("eval", {}).get("baseline_params") or {}).get("fixed_tuned")
    if base:
        pcfg.setdefault("eval", {}).setdefault("baseline_params", {})["fixed_tuned"] = base
    ck = run / f"{a.checkpoint}.pt"
    agent = TD3Agent.load(ck, cfg["train"])
    sd = torch.load(ck, map_location="cpu", weights_only=False)["actor"]
    layers = [t.numpy().astype(np.float64) for t in sd.values()]
    v = cfg["system"]["vsg"]
    pol = {f"{'W' if i % 2 == 0 else 'b'}{i // 2 + 1}": (l if i % 2 == 0 else l.reshape(-1, 1))
           for i, l in enumerate(layers)}
    pol.update({
        "n_layers": float(len(layers) // 2), "obs_names": np.array(OBS_NAMES, dtype=object),
        "h_min": v["h_min_s"], "h_max": v["h_max_s"], "d_min": v["d_min_pu"], "d_max": v["d_max_pu"],
        "alpha_min": v["alpha_min"], "alpha_max": v["alpha_max"],
        "headroom_constraint": float(run_cfg["env"]["headroom_constraint"]),
        "residual": float(run_cfg["env"].get("action_mode", "absolute") == "residual"),
        **dict(zip(("nominal_h", "nominal_d", "nominal_alpha"), _residual_base(run_cfg, run_cfg["env"]))),
        "agent_dt_s": run_cfg["env"]["agent_dt_s"],
        "source": f"{a.algo}/seed{a.seed}/{a.checkpoint}.pt",
    })
    savemat(dst / "vsgrl_policy_val.mat", pol)

    # --- scenarios, noise, Python reference ------------------------------
    df = load_processed(cfg)
    scs = scenarios_from_frame(pd.read_csv(resolve_path(cfg["eval"]["out_dir"]) / "scenarios_test.csv"))[: a.n]
    env = VSGEnv(cfg, df, split="test", record_trace=True)
    penv = VSGEnv(pcfg, df, split="test", record_trace=True)
    ctrls = {"fixed_tuned": (make_baseline("fixed_tuned", cfg, env), env),
             "fixed_feasible": (make_baseline("fixed_feasible", cfg, env), env),
             "policy": (PolicyController("policy", agent), penv)}

    n_noise = int(round(cfg["env"]["episode_s"] / cfg["env"]["sim_dt_s"])) + 2
    n_tr = int(np.ceil(cfg["env"]["episode_s"] / cfg["env"]["sim_dt_s"] / 5))
    out = {"sc_ws_hub_ms": [], "sc_rho_kgm3": [], "sc_p_pv_mpp_mw": [], "sc_load_mw": [], "sc_soc0": [],
           "ev_t": np.full((len(scs), 3), np.nan), "ev_mw": np.full((len(scs), 3), np.nan),
           "turb": np.zeros((len(scs), n_noise)), "lnoise": np.zeros((len(scs), n_noise)),
           "py_pd0": [], "py_pb0": [], "py_load0": [], "py_wind_cap": [], "py_pv_base": [], "py_h_pv": []}
    for c in ctrls:
        for k in TRACE_KEYS:
            out[f"{c}_{k}"] = np.full((len(scs), n_tr), np.nan)
        for k in METRIC_KEYS:
            out[f"{c}_m_{k}"] = np.zeros(len(scs))
    for i, sc in enumerate(scs):
        for key, attr in [("sc_ws_hub_ms", "ws_hub_ms"), ("sc_rho_kgm3", "rho_kgm3"),
                          ("sc_p_pv_mpp_mw", "p_pv_mpp_mw"), ("sc_load_mw", "load_mw"), ("sc_soc0", "soc0")]:
            out[key].append(getattr(sc, attr))
        for j, (t, mw) in enumerate(sc.event_list()[:3]):
            out["ev_t"][i, j], out["ev_mw"][i, j] = t, mw
        env.mg.reset(sc, cfg["env"]["episode_s"])
        mg = env.mg
        out["turb"][i], out["lnoise"][i] = mg._turb, mg._lnoise
        for key, val in [("py_pd0", mg.pd0), ("py_pb0", mg.pb0), ("py_load0", mg.load0),
                         ("py_wind_cap", mg.wind_cap), ("py_pv_base", mg.pv_base), ("py_h_pv", mg.h_pv)]:
            out[key].append(val * mg.Sb)
        for c, (ctrl, cenv) in ctrls.items():
            m, tr = run_episode(cenv, ctrl, sc)
            for k in TRACE_KEYS:
                out[f"{c}_{k}"][i, : len(tr)] = tr[k].to_numpy()
            for k in METRIC_KEYS:
                out[f"{c}_m_{k}"][i] = m[k]
        print(f"scenario {i}: events {sc.event_list()}  policy return {out['policy_m_return'][i]:.2f}")
    out = {k: np.asarray(v, dtype=float) if isinstance(v, list) else v for k, v in out.items()}
    out["trace_dt_s"] = 5 * cfg["env"]["sim_dt_s"]
    savemat(dst / "vsgrl_validation.mat", out, do_compression=True)
    print("wrote", dst / "vsgrl_validation.mat", dst / "vsgrl_params.mat", dst / "vsgrl_policy_val.mat")
