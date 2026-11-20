# Running and understanding the project in VS Code

This guide uses **Visual Studio Code** (free; Windows, macOS, Linux). The full Visual Studio IDE with its Python workload can also run the scripts, but the debug and task configurations here are for VS Code.

## 1. Get the code

```bash
git clone https://github.com/MuhammadBinyameenkhan/solar-wind-rl-estimation.git
cd solar-wind-rl-estimation
git checkout claude/determined-ptolemy-8ggnob      # until PR #1 is merged
code .                                             # opens VS Code in this folder
```
When VS Code asks, install the **recommended extensions**: Python, Pylance, Python Debugger, Jupyter, Rainbow CSV and YAML.

## 2. Create the Python environment (once)

Python 3.10–3.12 recommended.

**Windows (PowerShell, in the VS Code terminal `Ctrl+``):**
```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Or use **Terminal → Run Task → "Setup: create .venv and install requirements"**.

Then **Ctrl+Shift+P → "Python: Select Interpreter" → `.venv`**. Check the install: **Terminal → Run Task → Run tests** should report `22 passed`.

> PyTorch on Windows: if `pip install torch` fails, install it first with the command from pytorch.org (CPU build), then re-run `pip install -r requirements.txt`.

## 3. Learn the project with the walkthrough (start here)

Open `scripts/walkthrough.py`. Each `# %%` line starts a **cell**. Click **Run Cell** above it, or press **Shift+Enter**, to run it in the Interactive Window with its plots. The cells follow the paper's story:

| Cell | What you see | Code to read next |
|---|---|---|
| 1 | All study parameters | `configs/default.yaml` |
| 2 | Your 2024 ERA5 + NASA POWER data as hourly operating points | `vsgrl/data/era5.py`, `nasa_power.py`, `hybrid.py` |
| 3 | How one hour becomes a dispatch (diesel, wind, PV, BESS base power from the EMS) | `vsgrl/microgrid.py` → `reset()` |
| 4 | One 30 s episode: no support vs BESS droop vs VSG (frequency and support power) | `vsgrl/microgrid.py` → `advance()` |
| 5 | The feasibility projection: how headroom limits H and D | `vsgrl/envs/vsg_env.py` → `param_bounds()` |
| 6 | The RL interface: 16 observations, 3 actions, reward | `vsgrl/envs/vsg_env.py` → `_obs()`, `step_params()` |
| 7 | The oracle idea (why a tuned fixed VSG is hard to beat) | `scripts/oracle_test.py` |
| 8 | A tiny TD3 training loop | `vsgrl/agents/td3.py`, `vsgrl/train.py` |
| 9 | Results table once the full study has run | `scripts/evaluate.py`, `analyze.py` |

Experiment by editing a cell and re-running it. For example, in cell 4 change `H, D` or the `events` string, or in cell 5 change the SoC values.

## 4. Run the study from the Run and Debug panel

Open **Run and Debug** (`Ctrl+Shift+D`), pick a configuration from the drop-down and press **F5**. They are numbered in pipeline order:

| Configuration | Time (laptop CPU) | Output |
|---|---|---|
| 1. Inspect raw data | seconds | parsed columns, units, time span, solar-noon check |
| 2. Prepare hybrid dataset | seconds | `data/processed/hourly_resource.csv` + summary |
| 3. Oracle test | ~2 min (20 scenarios) | go/no-go: how much can adaptation gain at most? |
| 4. Tune baselines | ~20 min | gains to paste into `eval.baseline_params` |
| 5a. Train TD3 — quick | ~2 min | `runs/td3_quick/seed0/` (checks that everything works) |
| 5b / 5c. Train TD3 / DDPG — paper | ~1 h per seed (4 in parallel) | `runs/td3/seed*/`, `runs/ddpg/seed*/` |
| 6. Evaluate | ~15 min | `results/per_scenario.csv`, `results/traces/` |
| 7. Statistics | seconds | `results/summary.csv`, `significance.csv`, `table_main.tex` |
| 8. Pareto | ~10 min | `results/figures/fig_pareto.pdf` |
| 9. Paper figures | seconds | `results/figures/*.pdf` |
| 10. Export to MATLAB | seconds | `matlab/export/` |

For the whole pipeline at once: `bash run_all.sh` (macOS/Linux, or Git Bash on Windows).

## 5. Use the debugger to see the physics step by step

1. Open `vsgrl/microgrid.py` and click left of the line number in `advance()` at `acc_d = ...` to set a **breakpoint**.
2. Run **"0. Walkthrough (whole file)"** with F5. Execution stops inside the simulation.
3. In the **Variables** pane, inspect `self.dw_d` (diesel speed), `self.dw_v` (VSG virtual rotor), `pv` (VSG power), `hi` / `lo` (headroom limits), `self.soc`.
4. Press **F10** to step one line at a time, and **F5** to continue to the next 2 ms step.

Other good breakpoints:
* `VSGEnv.param_bounds`: the feasibility projection
* `VSGEnv.step_params`: the reward
* `TD3Agent.update`: one learning step

## 6. Where to change things

| You want to… | Edit |
|---|---|
| Change system sizes (PV 0.5 MW, BESS…) | `configs/default.yaml → system` |
| Use another site or year of data | `configs/default.yaml → data`, `site` |
| Change events (size, number) | `system.disturbance` |
| Change the reward | `env.reward` |
| Switch the EMS off (idle BESS) | `system.ems.enabled: false` |
| Train longer or on more seeds | `train.episodes`, `train.seeds` |

Any key can also be overridden without editing the file: add `--set key=value` to a script's arguments. For example, add `"--set", "system.pv.rated_mw=0.5"` to a launch configuration's `args` in `.vscode/launch.json`.
