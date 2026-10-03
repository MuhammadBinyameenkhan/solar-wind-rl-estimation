"""Export everything Simulink/Simscape validation needs into matlab/export/:

  vsgrl_policy_<tag>_seed<k>.mat  actor weights (W1,b1,...), activation list, action/obs scaling
  vsgrl_params.mat                all system parameters in SI / per-unit (mirrors the YAML)
  scenarios_test.csv              the exact test scenarios (operating point + disturbance)
  traces/                         Python reference traces for those scenarios (for overlay plots)

In MATLAB:  p = load('vsgrl_params.mat');  pol = load('vsgrl_policy_td3_seed0.mat');
            [H, D, alpha] = vsgrl_policy(obs, pol);   (see matlab/vsgrl_policy.m)
"""
import shutil

import numpy as np
import torch
import yaml
from _common import ROOT, base_parser, setup
from scipy.io import savemat

from vsgrl.config import resolve_path
from vsgrl.envs import OBS_NAMES


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "_"))
        elif isinstance(v, (int, float, bool)):
            out[key] = float(v)
        elif isinstance(v, list) and v and all(isinstance(x, (int, float)) for x in v):
            out[key] = np.asarray(v, float)
    return out


if __name__ == "__main__":
    p = base_parser(__doc__)
    p.add_argument("--algos", nargs="*", default=["td3", "ddpg"])
    a = p.parse_args()
    cfg = setup(a)
    dst = ROOT / "matlab" / "export"
    dst.mkdir(parents=True, exist_ok=True)

    params = flatten({"system": cfg["system"], "env": cfg["env"]})
    params = {k[:63]: v for k, v in params.items()}       # MATLAB field-name limit
    savemat(dst / "vsgrl_params.mat", params)
    print("wrote", dst / "vsgrl_params.mat", f"({len(params)} fields)")

    v = cfg["system"]["vsg"]
    runs = resolve_path(cfg["train"]["out_dir"])
    for algo in a.algos:
        for ck in sorted((runs / algo).glob("seed*/best.pt")):
            sd = torch.load(ck, map_location="cpu", weights_only=False)
            run_env = cfg["env"]
            if (ck.parent / "config.yaml").exists():   # the env settings this policy was trained with
                run_env = yaml.safe_load((ck.parent / "config.yaml").read_text())["env"]
            layers = [(k, t.numpy().astype(np.float64)) for k, t in sd["actor"].items()]
            m = {}
            for i in range(0, len(layers), 2):
                m[f"W{i // 2 + 1}"] = layers[i][1]
                m[f"b{i // 2 + 1}"] = layers[i + 1][1].reshape(-1, 1)
            m.update({
                "n_layers": float(len(layers) // 2), "hidden_activation": "relu", "output_activation": "tanh",
                "obs_names": np.array(OBS_NAMES, dtype=object),
                "h_min": v["h_min_s"], "h_max": v["h_max_s"], "d_min": v["d_min_pu"], "d_max": v["d_max_pu"],
                "alpha_min": v["alpha_min"], "alpha_max": v["alpha_max"],
                "headroom_constraint": float(run_env["headroom_constraint"]),
                "residual": float(run_env.get("action_mode", "absolute") == "residual"),
                "nominal_h": v["nominal_h_s"], "nominal_d": v["nominal_d_pu"], "nominal_alpha": v["nominal_alpha"],
                "design_step_pu": cfg["system"]["disturbance"]["design_step_mw"] / cfg["system"]["s_base_mva"],
                "agent_dt_s": run_env["agent_dt_s"],
            })
            name = f"vsgrl_policy_{algo}_{ck.parent.name}.mat"
            savemat(dst / name, m)
            print("wrote", dst / name)

    ev = resolve_path(cfg["eval"]["out_dir"])
    if (ev / "scenarios_test.csv").exists():
        shutil.copy(ev / "scenarios_test.csv", dst / "scenarios_test.csv")
    if (ev / "traces").exists():
        shutil.copytree(ev / "traces", dst / "traces", dirs_exist_ok=True)
    print("done →", dst)
