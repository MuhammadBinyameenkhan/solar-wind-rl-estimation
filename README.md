# RL-based VSG control for a low-inertia solar–wind–BESS microgrid

Code for the paper *“Reinforcement Learning-Based Virtual Synchronous Generator
Control for a Low-Inertia Solar–Wind–BESS Microgrid: A Converter
Headroom-Feasible Approach”* (M. B. Khan, A. Oonsivilai, Suranaree University
of Technology).

DDPG and TD3 agents adapt the virtual inertia **J**, damping **D** and reactive
droop **Kq** of a 2500 kVA grid-forming BESS in a 50 Hz, 100 % inverter-based
microgrid (500 kW PV, 500 kW Type-4 wind, 1800 kW load). An explicit
converter-headroom constraint (paper Eqs. 20–25) derates any (J, D) that the
converter cannot physically reserve.

## Quick start

```bash
pip install -r requirements.txt
python -m pytest -q tests          # physics / metric / data-split checks (~10 s)
python -m vsg_rl --smoke           # end-to-end pipeline check (~1 min)
python -m vsg_rl                   # full study: 5 seeds x {DDPG, TD3}, 1000 episodes
```

Useful options:

| Option | Meaning |
|---|---|
| `--seeds 0,1,2,3,4` | training seeds (default five) |
| `--workers N` | parallel processes; each (algorithm, seed) trains in its own process |
| `--episodes 1000` | episodes per run |
| `--stage train / evaluate / figures` | run part of the pipeline; training resumes from checkpoints |
| `--n-stress 50` | held-out randomised episodes per controller |
| `--weather calibrated / synthetic / measured` | synthetic shapes with calibrated or built-in levels, or real 30 s windows cut from measured 1 s data (see [`docs/REAL_DATA.md`](docs/REAL_DATA.md)) |
| `--fresh` | delete `results/` and start over |

On a 4-core CPU one 1000-episode run takes roughly 1 h; the full ten-run study
with `--workers 4` takes about 3–4 h. A GPU is not needed.

## Results of the 5-seed study

Summary (test scenarios, mean ± 95 % CI over 5 seeds; full tables in
[`results/RESULTS.md`](results/RESULTS.md), interpretation in
[`docs/FINDINGS.md`](docs/FINDINGS.md)):

| Controller | IAE (Hz·s) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Reserve (pu) |
|---|---|---|---|---|---|
| No VSG | 8.908 | 48.408 | 3.222 | 2.972 | 0.000 |
| Fixed high (paper, J=4, D=30) | 2.644 | 49.730 | 0.541 | 0.204 | 0.385 (100 % derated) |
| Fixed tuned (J=0, D=30, Kq=20) | 1.857 | 49.778 | 0.450 | 0.084 | 0.299 |
| Rule-based adaptive | 1.859 | 49.787 | 0.450 | 0.096 | 0.244 |
| DDPG-VSG | 1.857 ± 0.185 | 49.807 ± 0.011 | 0.423 ± 0.039 | 0.326 ± 0.206 | 0.238 ± 0.055 |
| TD3-VSG | 1.888 ± 0.064 | 49.812 ± 0.006 | 0.399 ± 0.025 | 0.494 ± 0.161 | 0.229 ± 0.037 |

The learned controllers match the tuned baselines on the error integrals,
give the best nadir and RoCoF, and reserve ~20 % less headroom than the tuned
constant controller. TD3 and DDPG are not significantly different. Trained
actors and training histories are in `results/checkpoints/`, so
`python -m vsg_rl --stage evaluate` reproduces every table and figure
without retraining.

### With measured weather

Re-run on measured 1 Hz Cabauw irradiance and FINO1 80 m wind
(`--weather measured`; [`results_measured/RESULTS.md`](results_measured/RESULTS.md),
[`docs/FINDINGS_MEASURED.md`](docs/FINDINGS_MEASURED.md)). On held-out real
weather **TD3 reduces IAE by 5.5 % against the tuned constant controller
(significant over 5 seeds) while reserving 27 % less headroom** (0.218 vs
0.299 pu), and it matches the rule-based adaptive VSG with 15 % less reserve.

## Outputs (`results/`)

* `RESULTS.md` — all tables, statistical tests and critic calibration
* `tables/test_summary.csv`, `tables/stress_summary.csv` — mean, sd and 95 % CI per controller
* `tables/test_per_episode.csv`, `tables/stress_per_episode.csv` — every run, every episode
* `tuned_baselines.json` — tuned baseline parameters and the full fixed-gain grid
* `figures/figure2…figure7*.png` and `figures/panels/` — paper figures, each panel also saved separately
* `checkpoints/` — best actor, full checkpoint and training history per (algorithm, seed)

## Package layout

```
vsg_rl/
  config.py     every constant with units; data-split seeds
  models.py     PV, wind turbine (rotor dynamics), BESS
  weather.py    the five scenarios + Open-Meteo archive calibration tool
  realdata.py   measured 1 s data -> scenario windows (train/val/test by time)
  env.py        swing equation, BESS droop + VSG, headroom limiter, voltage loop, reward
  baselines.py  fixed and rule-based adaptive VSG, tuned on validation episodes
  agents.py     SumTree PER, DDPG, TD3
  train.py      curriculum training, validation model selection, critic calibration
  evaluate.py   metrics, test sweep, stress test, multi-seed statistics
  plots.py      paper figures
  cli.py        `python -m vsg_rl`
tests/          pytest checks
data/           weather calibration
```

## Experimental protocol

The data splits never overlap (this is checked in `tests/`):

| Split | Episodes | Used for |
|---|---|---|
| train | stochastic; seed = `run_seed*100000 + episode` | learning |
| validation | 10 fixed stochastic episodes | RL model selection **and** tuning of the non-learning baselines |
| test | the five deterministic paper scenarios | reported tables |
| stress | 50 randomised held-out episodes | generalisation |

**Controllers compared**

* No VSG (J = D = 0), and the paper's three fixed configurations: low (1, 10), high (4, 30), max (15, 60)
* **Fixed tuned** — the best constant (J, D) from a grid, chosen on the validation episodes by the same reward the agents maximise
* **Rule-based adaptive** — extra inertia while |Δf| is growing and damping proportional to |Δf| (the Alipoor 2014 / Li 2016 family), tuned the same way
* DDPG and TD3, each trained with five seeds

An RL controller should be judged against the two tuned baselines. The paper's
original fixed configurations are infeasible (derated in 100 % of steps) and
make a weak reference point.

**Statistics.** Each seed is averaged over the episodes. Tables report the mean ±
95 % CI over seeds; TD3 and DDPG are compared with Welch's t on the per-seed means.

**Critic calibration.** At every evaluation the critic's Q(s, μ(s)) is compared
with the Monte-Carlo discounted return actually obtained from the same
validation states. This is the measurement the paper's discussion of critic
bias needs.

## Reward

Per control step (20 ms), with fixed weights from `config.py`:

```
r = −25·Δf² − 10·(RoCoF/2)² − 6·(ΔV/0.05)² − 5·‖Δa‖² − 2·|SOC−0.5|
    − 0.3·(P_vsg/S)² − 0.5·h_req − 8·max(0, h_req − h_avail) + 1[|Δf| < 0.5 Hz]
    − 100·1[trip]
```

`h_req = 0.08 J + 0.01 D` is the paper's Eq. (22), so the reserve cost the
agent pays is the same quantity reported in the tables. The tuned baselines
are selected with this same reward.

## Weather data

`data/weather_calibration.json` holds the scenario levels (irradiance,
temperature, wind, cloud depth, wind fall). The shipped file reproduces the
operating point of the manuscript's calibration run. To regenerate it from a
fixed, reproducible window of the Open-Meteo **historical archive** (ERA5
reanalysis) on a machine with internet access:

```bash
python -m vsg_rl.weather --calibrate --start 2024-01-01 --end 2024-12-31
```

These are reanalysis data for the site coordinates, not on-site
measurements, and the sub-second disturbance shapes are synthetic. The paper
should state both.

**Measured data.** To replace the synthetic disturbance shapes with real
high-resolution irradiance and wind records, follow
[`docs/REAL_DATA.md`](docs/REAL_DATA.md). It lists the data sources and gives the
step-by-step procedure. Only `data/measured/dataset.json` changes.

See [`docs/CHANGES.md`](docs/CHANGES.md) for every correction relative to the
original single-file script and the matching edits the manuscript needs.
