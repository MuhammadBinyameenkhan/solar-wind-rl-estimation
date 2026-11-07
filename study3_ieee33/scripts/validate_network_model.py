"""Validation of the Study 3 network model before it is used for learning.

V2  Initial operating point: the dynamic network (EMFs behind reactances, constant-impedance
    loads) must reproduce the Newton-Raphson load flow it was initialised from.
V3  Single-bus limit: with the feeder impedances scaled to ~0, the IEEE 33-bus model must reproduce
    the Study 2 two-machine model on the same test scenarios (fixed tuned VSG).
Usage (from the repository root):  python study3_ieee33/scripts/validate_network_model.py [--n 6]
"""
import argparse
import copy
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "study3_ieee33"))
from vsgrl33.env33 import Ieee33VSGEnv  # noqa: E402

from vsgrl.config import load_config  # noqa: E402
from vsgrl.controllers import BASELINES  # noqa: E402
from vsgrl.data.hybrid import load_processed  # noqa: E402
from vsgrl.envs import VSGEnv  # noqa: E402
from vsgrl.rollout import run_episode  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=6)
a = ap.parse_args()

cfg3 = load_config(ROOT / "study3_ieee33/configs/ieee33.yaml")
env3 = Ieee33VSGEnv(cfg3, load_processed(cfg3), split="test", record_trace=True)
scs3 = env3.sampler.fixed_set("test", a.n, cfg3["eval"]["scenario_seed"])

# ---------------- V2: initial operating point
worst_v = worst_p = 0.0
for sc in scs3:
    mg = env3.mg
    mg.reset(sc, env3.episode_s)
    E = np.array([mg.Ed_mag * np.exp(1j * mg.th_d), mg.Ev_mag * np.exp(1j * mg.th_v)])
    fd = mg.feeder
    S_inj = np.zeros(fd.n, complex) if mg.const_z else -mg.load0 * (fd.share_p + 1j * fd.qp)
    S_inj[mg.bus_r - 1] += mg.p_w0 + mg.pv_base
    I_inj = np.conj(S_inj / mg.V0)
    V, S_m = mg.net_on.solve(E, I_inj)
    worst_v = max(worst_v, np.max(np.abs(V - mg.V0)))
    worst_p = max(worst_p, abs(S_m[0].real - mg.Pe_d0), abs(S_m[1].real - mg.pb0))
print(f"V2 initial point: max |dV| = {worst_v:.1e} pu, max |dP machines| = {worst_p:.1e} pu  ->",
      "PASS" if worst_v < 1e-8 and worst_p < 1e-8 else "FAIL")

# ---------------- V3: single-bus limit vs Study 2
cfg2 = load_config(ROOT / "configs/default.yaml")
env2 = VSGEnv(cfg2, load_processed(cfg2), split="test", record_trace=True)
scs2 = env2.sampler.fixed_set("test", a.n, cfg2["eval"]["scenario_seed"])
cfg3s = copy.deepcopy(cfg3)
cfg3s["system"]["network"]["impedance_scale"] = 1e-3
env3s = Ieee33VSGEnv(cfg3s, load_processed(cfg3s), split="test", record_trace=True)
k = cfg3["system"]["s_base_mva"] / cfg2["system"]["s_base_mva"]
print(f"\nV3 single-bus limit (fixed tuned VSG), Study 2 vs IEEE 33-bus model with feeder impedance x1e-3:")
print(f"{'sc':>3} {'load MW (S2 x k / S3)':>24} {'nadir S2':>9} {'nadir S3':>9} {'diff':>7} {'RMS dDf':>8}")
rel = []
for i, (s2, s3) in enumerate(zip(scs2, scs3)):
    m2, tr2 = run_episode(env2, BASELINES["fixed_tuned"](cfg2, env2), s2)
    m3, tr3 = run_episode(env3s, BASELINES["fixed_tuned"](cfg3s, env3s), s3)
    rms = float(np.sqrt(np.mean((tr2.df_hz.values - tr3.df_hz.values[:len(tr2)]) ** 2)))
    rel.append(abs(m3["nadir_hz"] / m2["nadir_hz"] - 1))
    print(f"{i:>3} {s2.load_mw * k:>11.3f} / {s3.load_mw:<10.3f} {m2['nadir_hz']:>9.3f} {m3['nadir_hz']:>9.3f} "
          f"{100 * rel[-1]:>6.1f}% {rms:>8.4f}")
print(f"max nadir difference {100 * max(rel):.1f} %")
