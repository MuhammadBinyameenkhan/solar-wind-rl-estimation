# Toward Feasible Synthetic Inertia: RL-Driven VSG Control for Low-Inertia PV-Wind-BESS Microgrids

Code for the thesis and paper. A TD3 (and DDPG) agent schedules the **virtual inertia _H_, damping _D_ and PV/BESS allocation α** of a grid-forming Virtual Synchronous Generator every 50 ms. A **headroom feasibility projection** keeps each commitment within the power that the BESS (at its current SoC) and the de-loaded PV can actually deliver. Operating points come from **real data**: ERA5 for wind and NASA POWER for solar.

**Workflow:** train in Python (Gymnasium + PyTorch) → validate in MATLAB/Simscape (exported policy + identical scenarios).

| | |
|---|---|
| System base | 2.0 MVA, 50 Hz |
| Wind | 1.0 MW, grid-following MPPT, no inertia (ERA5 100 m wind → hub height, air-density-corrected power curve) |
| PV | 0.5–0.8 MW, **de-loaded MPPT** (default d = 15 % headroom) (NASA POWER GHI + T2M) |
| BESS | 0.5 MW / 2 MWh, SoC-dependent power limits, grid-forming VSG |
| Diesel | 0.5 MW synchronous generator (the only physical inertia, H = 2 s on its own base), droop + AGC |
| Disturbances | 0.2–0.4 MW load steps (75 % increases, 25 % rejections) |
| Training | 1000 episodes × 5 seeds, TD3 and DDPG |
| Baselines | diesel-only, BESS droop (no inertia), fixed VSG, fixed VSG + projection, bang-bang adaptive inertia, RoCoF-adaptive VSG |

---

## 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # numpy pandas scipy matplotlib gymnasium torch pyyaml pytest
python -m pytest -q                    # 17 tests, ~10 s
```

## 2. Put your real data in place

```
data/raw/era5_wind.csv           ERA5 hourly: time + u100, v100 (+ t2m, sp)      → wind
data/raw/nasa_power_solar.csv    NASA POWER hourly: ALLSKY_SFC_SW_DWN, T2M       → solar
```
Different paths? Edit `data.era5_csv` and `data.nasa_power_csv` in `configs/default.yaml`. Then check that both files parse correctly:

```bash
python scripts/inspect_data.py        # shows detected columns, units, time span, ERA5/NASA overlap
python scripts/prepare_data.py        # builds data/processed/hourly_resource.csv + summary table
```
See **[docs/DATA.md](docs/DATA.md)** for the accepted CSV layouts, how to download the right variables, time-zone handling, and the load-profile assumption.

## 3. Run the experiments

```bash
# main study (≈35 min per seed per algorithm on one CPU core; use --workers N)
python scripts/train.py --algo td3  --workers 5
python scripts/train.py --algo ddpg --workers 5

python scripts/evaluate.py            # all controllers on the same 200 held-out test scenarios
python scripts/analyze.py             # mean ± std over seeds, bootstrap CIs, Wilcoxon + Holm, LaTeX table
python scripts/plot.py                # paper figures → results/figures/*.pdf
python scripts/export_matlab.py       # policy weights + parameters + scenarios → matlab/export/
```
Or all at once: `bash run_all.sh`. Ablations and sweeps (headroom constraint off, PV 0.5/0.65/0.8 MW, de-load fraction, α fixed) are in **[docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)**.

**Quick end-to-end check without your data** (synthetic files in the same CSV formats; results from these are *not* reportable):
```bash
python scripts/make_sample_data.py
python scripts/train.py --config configs/smoke.yaml --algo td3
python scripts/evaluate.py --config configs/smoke.yaml && python scripts/analyze.py --config configs/smoke.yaml
```

## 4. Repository layout

```
configs/default.yaml        every parameter of the study (system, VSG ranges, reward, TD3, evaluation)
vsgrl/data/                 ERA5 + NASA POWER readers, hybrid merge, chronological split, synthetic sample generator
vsgrl/components/           wind power curve, PV model (NOCT), load profile
vsgrl/microgrid.py          plant: diesel SG + grid-forming VSG two-machine RMS model, BESS SoC, headroom limits
vsgrl/envs/vsg_env.py       Gymnasium env: observation, action → (H, D, α) with feasibility projection, reward
vsgrl/agents/td3.py         TD3 / DDPG (PyTorch)
vsgrl/controllers.py        baseline controllers
vsgrl/metrics.py            nadir, RoCoF (100 ms window), settling, BESS energy, saturation, violations
scripts/                    inspect / prepare / train / evaluate / analyze / plot / export_matlab
matlab/                     policy forward pass, headroom projection, observation builder, Python↔Simscape comparison
docs/                       METHODOLOGY, DATA, EXPERIMENTS, SIMULINK_VALIDATION, PAPER_OUTLINE
tests/                      unit + integration tests
```

## 5. Documentation

* **[docs/METHODOLOGY.md](docs/METHODOLOGY.md)**: model equations, parameter table, MDP (state, action, reward), headroom projection, algorithms, metrics, statistics
* **[docs/DATA.md](docs/DATA.md)**: real-data pipeline (ERA5 + NASA POWER hybrid)
* **[docs/EXPERIMENTS.md](docs/EXPERIMENTS.md)**: experiment matrix with exact commands and expected runtimes
* **[docs/SIMULINK_VALIDATION.md](docs/SIMULINK_VALIDATION.md)**: how to build the Simscape model and validate the exported policy
* **[docs/PAPER_OUTLINE.md](docs/PAPER_OUTLINE.md)**: section-by-section paper plan, contribution statement, threats to validity
