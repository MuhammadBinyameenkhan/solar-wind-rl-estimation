# Experiment matrix

All runs use the same test scenarios (`results/scenarios_test.csv`, fixed seed), so they can be compared pairwise. Runtime is about 2 s per training episode on one CPU core, which is about 35 min per seed for 1000 episodes. `--workers N` runs seeds in parallel.

## E1 — Main comparison (RQ1: does RL-scheduled VSG beat fixed/adaptive VSG?)

```bash
python scripts/tune_baselines.py                     # tune adaptive-baseline gains on the VALIDATION split
#   → paste the printed block into configs/default.yaml under eval.baseline_params
python scripts/train.py --algo td3  --workers 5      # 5 seeds × 1000 episodes
python scripts/train.py --algo ddpg --workers 5
python scripts/evaluate.py
python scripts/analyze.py
python scripts/plot.py
```
Outputs:
* `results/summary.csv` and `table_main.tex` (mean ± seed-std)
* `results/significance.csv` (Wilcoxon + Holm)
* `results/figures/fig_learning_curves`, `fig_metric_boxes`, `fig_response_sc*`, `fig_headroom_policy`

## E2 — Headroom-constraint ablation (RQ2: does the feasibility projection matter?)

```bash
python scripts/train.py --algo td3 --tag td3_noproj --workers 5 --set env.headroom_constraint=false
python scripts/evaluate.py --controllers td3 td3_noproj fixed fixed_feasible
```
Compare saturation time, BESS peak and the number of scenarios with SoC-limited saturation. Also compare `fixed` vs `fixed_feasible`, which applies the same projection to a non-learning controller.

> `evaluate.py` automatically evaluates each RL run with the `env` settings it was trained with
> (from `runs/<tag>/seed*/config.yaml`), so no extra flags are needed here.

## E3 — Multi-source allocation (RQ3: does learning α help?)

```bash
python scripts/train.py --algo td3 --tag td3_fixalpha --workers 5 --set env.action_dims=2
python scripts/evaluate.py --controllers td3 td3_fixalpha
```
Compare BESS energy throughput (a degradation proxy) and PV-headroom energy.

## E4 — Sensitivity to PV size and de-loading level

Each setting changes the dataset (PV MW) or the headroom. Use a separate results folder for each:

```bash
for PV in 0.5 0.65 0.8; do
  S="system.pv.rated_mw=$PV data.processed_csv=data/processed/hourly_pv$PV.csv train.out_dir=runs_pv$PV eval.out_dir=results_pv$PV"
  python scripts/prepare_data.py --set $S
  python scripts/train.py --algo td3 --workers 5 --set $S
  python scripts/evaluate.py --set $S
  python scripts/analyze.py --set $S
done
# de-loading fraction d ∈ {0.05, 0.10, 0.15, 0.20}: same pattern with system.pv.deload_fraction=<d>
```

## E5 — Robustness (generalisation without retraining)

Evaluate the E1 policies on perturbed plants. Write each to a separate results folder and keep the same test scenarios by copying `scenarios_test.csv` in first:

```bash
mkdir -p results_rob_h && cp results/scenarios_test.csv results_rob_h/
python scripts/evaluate.py --set eval.out_dir=results_rob_h system.diesel.inertia_h_s=1.5
# also: system.vsg.sync_coeff_pu=1.5 ; system.pv.response_time_s=0.15 ; system.disturbance.step_mw_range=[0.4,0.5]
```

## E6b — Action-mapping ablation (residual vs absolute)

```bash
python scripts/train.py --algo td3 --tag td3_absolute --workers 5 --set env.action_mode=absolute
python scripts/evaluate.py --controllers td3 td3_absolute
```
In the pilot (synthetic data, 300 episodes, 2 seeds), residual mapping gave consistent seeds (return −76 / −77 vs −102 / −75) and fewer RoCoF violations (27.5 % vs 38 %).

## E6 — Training budget / sample efficiency

The learning curves from E1 already cover this: `val_log.csv` holds 20 validation evaluations per seed. Report the episode at which each algorithm first beats the best baseline's validation return.

## Reward-weight sensitivity (recommended)

The BESS-usage weight `env.reward.w_bess` sets how expensive damping is. With a small value, the best policy is close to "maximum damping during every event". A simple adaptive rule can approximate that, which makes the advantage of RL small. Report results for 2–3 values (e.g. 0.05, 0.5, 2.0), each with its own run and results folder:
```bash
python scripts/train.py --algo td3 --tag td3_wb05 --workers 5 --set env.reward.w_bess=0.5 eval.out_dir=results_wb05
python scripts/tune_baselines.py --set env.reward.w_bess=0.5
python scripts/evaluate.py --set env.reward.w_bess=0.5 eval.out_dir=results_wb05 --controllers fixed bang_bang adaptive_rocof td3_wb05
```

## Reporting checklist

- [ ] Rejection rate of the adequacy screen (printed by `evaluate.py`)
- [ ] Mean ± std over **5 seeds**, and 95 % CIs over **200 test scenarios**
- [ ] Holm-corrected p-values for every metric/baseline pair
- [ ] Wall-clock training time per seed (`runs/<algo>/seed*/summary.json`)
- [ ] Policy behaviour: `fig_headroom_policy` (H and D vs available headroom)
- [ ] Simulink validation table (docs/SIMULINK_VALIDATION.md)
