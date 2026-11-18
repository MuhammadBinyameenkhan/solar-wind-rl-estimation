"""Validation of the Study 3 model with voltage control (salient diesel + IEEE 421.5 AC8C, VSG Q-V droop,
PV/wind volt-var). See DESIGN.md for the parameter sources.

V2   initial point: the dynamic network reproduces the load flow (voltages, machine P and Q).
V2b  equilibrium: with no load steps, no load noise and constant wind, nothing moves (state drift).
V4   voltage profile on the test scenarios (fixed tuned VSG): min / max bus voltage over the episode,
     reported against ANSI C84.1 Range A (0.95-1.05 pu) and Range B (0.917-1.058 pu); frequency nadir
     with and without voltage control.
Usage (from the repository root):  python study3_ieee33/scripts/validate_voltage_control.py [--n 6]
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
from vsgrl.controllers import make_baseline  # noqa: E402
from vsgrl.data.hybrid import load_processed  # noqa: E402
from vsgrl.rollout import run_episode  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=6)
a = ap.parse_args()

cfg = load_config(ROOT / "study3_ieee33/configs/ieee33.yaml")
assert cfg["system"]["network"].get("voltage_control"), "voltage_control is off in the config"
df = load_processed(cfg)
env = Ieee33VSGEnv(cfg, df, split="test", record_trace=True)
scs = env.sampler.fixed_set("test", a.n, cfg["eval"]["scenario_seed"])
mg = env.mg

# ---------------- V2: initial point
wv = wp = wq = 0.0
for sc in scs:
    mg.reset(sc, env.episode_s)
    fd = mg.feeder
    S_inj = -mg.load0 * (fd.share_p + 1j * fd.qp)
    S_inj[mg.bus_r - 1] += mg.p_w0 + mg.pv_base + 1j * mg.q_res
    I_inj = np.conj(S_inj / mg.V0) + mg.y_corr * mg.V0
    E = np.array([mg.Ed_mag * np.exp(1j * mg.th_d), mg.Ev_mag * np.exp(1j * mg.th_v)])
    V, S_m = mg.net_on.solve(E, I_inj)
    S1 = mg.V0[0] * np.conj(mg.feeder.Y_lines[0] @ mg.V0)
    wv = max(wv, float(np.max(np.abs(V - mg.V0))))
    wp = max(wp, abs(S_m[0].real - mg.Pe_d0), abs(mg.net_on.S_vt.real - mg.pb0))
    wq = max(wq, abs(S_m[0].imag - S1.imag), abs(mg.net_on.S_vt.imag - mg.q_v0))
    print(f"  sc {sc.idx if hasattr(sc, 'idx') else '-'}: load {sc.load_mw:.2f} MW, V_R(AVR) = {mg.avr.VR:.2f}, "
          f"E_fd = {mg.efd0:.3f} pu, E'q = {mg.Ed_mag:.3f}, Q_res = {mg.q_res * mg.Sb:.3f} Mvar, "
          f"Q_vsg = {mg.q_v0 * mg.Sb:.3f} Mvar, Vmin = {np.abs(mg.V0).min():.4f}, Vmax = {np.abs(mg.V0).max():.4f}")
ok2 = wv < 1e-8 and wp < 1e-8 and wq < 1e-8
print(f"V2 initial point: max|dV| {wv:.1e}, max|dP| {wp:.1e}, max|dQ| {wq:.1e} pu  ->", "PASS" if ok2 else "FAIL")

# ---------------- V2b: equilibrium (no events, no noise, frozen wind)
cfg_q = copy.deepcopy(cfg)
cfg_q["system"]["load"]["noise_frac"] = 0.0
cfg_q["system"]["wind"]["turbulence_intensity"] = 0.0
envq = Ieee33VSGEnv(cfg_q, df, split="test", record_trace=True)
drift = 0.0
for sc in scs[:3]:
    sc0 = copy.deepcopy(sc)
    sc0.events = []
    if hasattr(sc0, "dist_mw"):
        sc0.dist_mw = 0.0
    m, tr = run_episode(envq, make_baseline("fixed_tuned", cfg_q, envq), sc0)
    drift = max(drift, float(np.max(np.abs(tr.df_hz.values))))
print(f"V2b equilibrium (3 scenarios, no events/noise): max |df| = {drift:.2e} Hz  ->", "PASS" if drift < 1e-6 else "CHECK")

# ---------------- V4: voltages and nadir with / without voltage control
cfg_nv = copy.deepcopy(cfg)
cfg_nv["system"]["network"]["voltage_control"] = False
env_nv = Ieee33VSGEnv(cfg_nv, load_processed(cfg_nv), split="test", record_trace=True)
print(f"\nV4 test scenarios, fixed tuned VSG: bus voltage range over the episode, and nadir")
print(f"{'sc':>3} {'load MW':>8} {'Vmin VC':>8} {'Vmax VC':>8} {'Vmin noVC':>9} {'nadir VC':>9} {'nadir noVC':>10}")
rows = []
for i, sc in enumerate(scs):
    m1, _ = run_episode(env, make_baseline("fixed_tuned", cfg, env), sc)
    v1min, v1max = env.mg.vmin, env.mg.vmax
    m0, _ = run_episode(env_nv, make_baseline("fixed_tuned", cfg_nv, env_nv), sc)
    rows.append((v1min, v1max, env_nv.mg.vmin, m1["nadir_hz"], m0["nadir_hz"]))
    print(f"{i:>3} {sc.load_mw:>8.3f} {v1min:>8.4f} {v1max:>8.4f} {env_nv.mg.vmin:>9.4f} {m1['nadir_hz']:>9.3f} "
          f"{m0['nadir_hz']:>10.3f}")
R = np.array(rows)
print(f"with voltage control: Vmin {R[:, 0].min():.4f}, Vmax {R[:, 1].max():.4f} pu "
      f"(ANSI C84.1 Range A 0.95-1.05: {'inside' if R[:, 0].min() >= 0.95 and R[:, 1].max() <= 1.05 else 'outside'}; "
      f"Range B 0.917-1.058: {'inside' if R[:, 0].min() >= 0.917 and R[:, 1].max() <= 1.058 else 'outside'})")
