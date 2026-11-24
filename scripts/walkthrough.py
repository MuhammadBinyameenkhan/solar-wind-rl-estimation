# %% [markdown]
# # Walkthrough: RL-driven VSG control for a PV-Wind-BESS-Diesel microgrid
#
# Run this file **cell by cell** in VS Code: click "Run Cell" above each `# %%`, or press
# Shift+Enter. It needs the Python + Jupyter extensions and `pip install ipykernel`.
# Each cell is short and explains one idea; the whole file runs in a few minutes on a laptop.
#
# Order of the story:
#   1. configuration           →  configs/default.yaml
#   2. real data               →  vsgrl/data/  (ERA5 wind + NASA POWER solar, 2024)
#   3. one operating point     →  vsgrl/microgrid.py  (dispatch + EMS)
#   4. one disturbance event   →  three controllers compared
#   5. feasibility projection  →  vsgrl/envs/vsg_env.py :: param_bounds
#   6. the RL environment      →  observation, action, reward
#   7. oracle idea             →  why a tuned fixed VSG is hard to beat here
#   8. a tiny TD3 training run →  vsgrl/agents/td3.py, vsgrl/train.py

# %% 1. Configuration — every number of the study lives in one YAML file
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if "__file__" in globals() else Path.cwd()
sys.path.insert(0, str(ROOT))

import matplotlib.pyplot as plt
import numpy as np

from vsgrl.config import load_config

cfg = load_config(ROOT / "configs/default.yaml")
s = cfg["system"]
print(f"Base {s['s_base_mva']} MVA, {s['f_nominal_hz']} Hz")
print(f"Wind {s['wind']['rated_mw']} MW | PV {s['pv']['rated_mw']} MW (de-load {s['pv']['deload_fraction']:.0%})"
      f" | BESS {s['bess']['power_mw']} MW / {s['bess']['energy_mwh']} MWh | Diesel {s['diesel']['rated_mw']} MW")
print("Disturbances:", s["disturbance"]["step_mw_range"], "MW,", s["disturbance"]["n_events_range"], "events / episode")

# %% 2. Real data — hourly operating points from ERA5 (wind) + NASA POWER (solar)
from vsgrl.data.hybrid import load_processed, summarize

df = load_processed(cfg)            # builds data/processed/hourly_resource.csv on first run
print(summarize(df, cfg).round(3).to_string(index=False))

week = df.loc["2024-04-01":"2024-04-07"]
fig, ax = plt.subplots(figsize=(8, 3))
ax.plot(week.index, week.p_wind_mw, label="Wind (ERA5)")
ax.plot(week.index, week.p_pv_mpp_mw, label="PV MPP (NASA POWER)")
ax.plot(week.index, week.load_mw, label="Load")
ax.set_ylabel("MW"); ax.legend(); ax.set_title("One week of operating points")
plt.show()

# %% 3. One operating point — the hourly data sets the dispatch; the EMS commits BESS power
from vsgrl.data.hybrid import wind_curve_from_cfg
from vsgrl.microgrid import Microgrid, Scenario

mg = Microgrid(cfg, wind_curve_from_cfg(cfg))
import pandas as pd

t_pick = pd.Timestamp("2024-04-03 12:00", tz="UTC")          # 19:00 local time (UTC+7): evening peak
row = df.iloc[df.index.get_indexer([t_pick], method="nearest")[0]]
sc = Scenario(time_utc=str(row.name), ws_hub_ms=row.ws_hub_ms, rho_kgm3=row.rho_kgm3,
              p_pv_mpp_mw=row.p_pv_mpp_mw, load_mw=row.load_mw, soc0=0.6,
              dist_mw=0.3, dist_time_s=1.0, noise_seed=1, events="1.0:+0.30;12.0:-0.20")
mg.reset(sc, episode_s=30.0)
Sb = mg.Sb
print(f"load {mg.load0*Sb:.2f} MW = diesel {mg.pd0*Sb:.2f} + wind {mg.p_w0*Sb:.2f} + PV {mg.pv_base*Sb:.2f}"
      f" + BESS base {mg.pb0*Sb:+.2f}")
print(f"upward headroom for the VSG: {mg.headroom_up()*Sb:.2f} MW  (BESS limit − base + PV headroom)")

# %% 4. One episode, three controllers — what synthetic inertia does
#   none  : diesel alone (only physical inertia: H = 0.5 s on the system base)
#   droop : grid-following BESS, P = −D·Δf  (fast, but no inertia)
#   vsg   : grid-forming VSG with H = 3 s, D = 15
fig, axs = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
for mode, H, D in [("none", 0.2, 0.0), ("droop", 0.2, 15.0), ("vsg", 3.0, 15.0)]:
    mg.reset(sc, 30.0)
    trace = {"every": 5, "rows": []}
    mg.advance(H, D, 0.7, n_steps=int(30.0 / mg.dt), mode=mode, trace=trace)
    t = np.array([r[0] for r in trace["rows"]]); f = np.array([r[1] for r in trace["rows"]])
    pv = np.array([r[4] for r in trace["rows"]])
    axs[0].plot(t, f, label=mode); axs[1].plot(t, pv, label=mode)
axs[0].axhspan(-0.2, 0.2, color="0.9", zorder=0, label="±0.2 Hz band")
axs[0].set_ylim(-1.5, 1.0); axs[0].set_ylabel("Δf (Hz)"); axs[0].legend(ncol=4)
axs[1].set_ylabel("Support power (MW)"); axs[1].set_xlabel("Time (s)")
plt.show()
# Try: change H or D above, or set events to a bigger step, and re-run this cell.

# %% 5. Feasibility projection — never promise inertia the BESS/PV cannot deliver
from vsgrl.envs import OBS_NAMES, VSGEnv

env = VSGEnv(cfg, df, split="train", record_trace=True)
env.reset(options={"scenario": sc})
for soc in [0.9, 0.5, 0.2, 0.12]:
    env.mg.soc = soc
    h_ub, d_ub = env.param_bounds()
    print(f"SoC {soc:.2f}: headroom {env.mg.headroom_up()*Sb:.2f} MW → H ≤ {h_ub:.2f} s, D ≤ {d_ub:.1f} pu")
# Rule (band_power): D·0.2 Hz ≤ headroom and 2H·(1 Hz/s) ≤ headroom, in per unit.

# %% 6. The RL environment — what the agent sees, does, and is rewarded for
obs, info = env.reset(seed=0)
print("observation (16 values):")
for n, v in zip(OBS_NAMES, obs):
    print(f"  {n:15s} {v:+.3f}")
a = np.zeros(3, dtype=np.float32)          # residual action 0 = the tuned base VSG
print("action 0 →", np.round(env.action_to_params(a), 2), "(H s, D pu, alpha)")
total = 0.0
done = False
while not done:
    obs, r, term, trunc, info = env.step(a)
    total += r
    done = term or trunc
print(f"episode return with the base VSG: {total:.2f}   (events: {env.scenario.events or env.scenario.dist_mw})")

# %% 7. Oracle idea — how much could adaptation gain at most?
# The full test is scripts/oracle_test.py; here a 5-scenario taste of it.
from vsgrl.controllers import FixedTunedVSG
from vsgrl.rollout import run_episode

val = VSGEnv(cfg, df, split="val", record_trace=True)
scs = val.sampler.fixed_set("val", 5, 123)
grid = [(3.0, 10.0), (3.0, 15.0), (5.0, 25.0)]
R = np.array([[run_episode(val, FixedTunedVSG(cfg, val, h=H, d=D, alpha=0.7), x)[0]["return"] for H, D in grid]
              for x in scs])
print("returns (rows = scenarios, cols = fixed settings):\n", R.round(1))
print(f"best single setting {R.mean(0).max():.2f} vs per-scenario oracle {R.max(1).mean():.2f}")

# %% 8. A tiny TD3 training run (≈2 min) — the real runs use scripts/train.py
import torch

from vsgrl.agents.td3 import TD3Agent

torch.set_num_threads(1)
tcfg = dict(cfg["train"], warmup_steps=600, batch_size=128)
agent = TD3Agent(env.observation_space.shape[0], env.action_space.shape[0], tcfg, algo="td3", seed=0)
rng = np.random.default_rng(0)
for ep in range(4):
    obs, _ = env.reset(seed=ep)
    done, R_ep, steps = False, 0.0, 0
    while not done:
        a = rng.uniform(-1, 1, 3).astype(np.float32) if agent.buffer.n < tcfg["warmup_steps"] \
            else agent.act(obs, noise=0.1)
        obs2, r, term, trunc, _ = env.step(a)
        agent.buffer.add(obs, a, r, obs2, float(term))
        obs, done, R_ep, steps = obs2, term or trunc, R_ep + r, steps + 1
        if agent.buffer.n >= tcfg["warmup_steps"] and steps % 2 == 0:
            agent.update()
    print(f"episode {ep}: return {R_ep:.1f}")
# Four episodes teach nothing yet; the study uses 600–1000 episodes × several seeds.

# %% 9. Results of the full study (after scripts/evaluate.py and scripts/pareto.py)
res_file = ROOT / cfg["eval"]["out_dir"] / "per_scenario.csv"
if res_file.exists():
    r = pd.read_csv(res_file)
    print(r.groupby("controller")[["nadir_hz", "time_outside_band_s", "rocof_max_hz_s", "return"]].mean().round(3))
else:
    print("No results yet — run: python scripts/evaluate.py")
