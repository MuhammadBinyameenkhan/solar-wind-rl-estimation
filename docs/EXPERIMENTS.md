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

---

## Pilot results (SYNTHETIC sample data — pipeline check only, not reportable)

Setup: `configs/smoke.yaml` data; TD3 with residual mapping and the direction-aware projection; 4 seeds × 600 episodes (≈21 min per seed, 4 in parallel); 60 held-out test scenarios; adaptive baselines tuned on the validation split.

| Controller | Max \|Δf\| (Hz) | Max RoCoF (Hz/s) | QSS \|Δf\| (Hz) | Settling (s) | Saturation (s) | Return |
|---|---|---|---|---|---|---|
| Adaptive-RoCoF VSG (tuned) | 0.275 | 0.954 | 0.186 | 0.70 | 0.133 | −48.4 |
| **TD3-VSG (4 seeds)** | **0.299** | **0.958** | **0.219** | **0.76** | **0.062** | **−68.7** |
| Bang-bang VSG (tuned) | 0.402 | 1.009 | 0.310 | 1.40 | 0.056 | −90.6 |
| Fixed VSG | 0.404 | 1.077 | 0.310 | 1.31 | 0.058 | −91.1 |
| Fixed VSG + projection | 0.414 | 1.078 | 0.329 | 1.31 | 0.037 | −102.3 |
| BESS droop (no inertia) | 0.591 | 4.801 | 0.307 | 1.78 | 0.319 | −177.8 |
| Diesel only | 3.03 (90 % collapse) | 7.04 | 0.90 | – | 0 | −490.1 |

What the pilot showed:

1. **TD3 vs fixed, bang-bang and droop:** TD3 is significantly better on nadir, RoCoF, QSS deviation and settling time (Wilcoxon + Holm, p < 0.01).
2. **TD3 vs the tuned adaptive VSG:** no significant difference on any frequency metric. TD3 wins in 60 % of scenarios (median return +1.9). Its *mean* is worse because of a few high-load scenarios: there all seeds choose low damping to avoid headroom saturation, which the reward penalises with `w_sat`. TD3 saturates the headroom **about half as often** (0.062 s vs 0.133 s). This is the feasibility trade-off the paper is about. How much it is worth depends on `w_sat` and `w_bess`, so run the reward-weight sensitivity study.
3. **Design fixes found by the pilot (already in the code):** (a) residual action mapping gives consistent seeds; (b) action-rate weight 0.3 removes bang-bang inertia switching; (c) the direction-aware projection removed the over-frequency failure mode (validation return −43 → −32).
4. **Training budget:** seeds agree closely (best validation −30 to −34). Going from 300 to 1000 episodes did not change test performance in an earlier variant, so 1000 episodes is enough.

---

## Interim results on the 2024 site data (Nakhon Ratchasima)

200 held-out test scenarios (weekly-block test split; 10.7 % adequacy rejection). Baselines tuned on the validation split. TD3 = 4 seeds × 1000 episodes, residual mapping centred on the *standard* VSG (H = 3 s, D = 20); this run is stored as `runs/td3_resnominal`.

| Controller | Max \|Δf\| (Hz) | Max RoCoF (Hz/s) | QSS \|Δf\| (Hz) | Saturation (s) | Return |
|---|---|---|---|---|---|
| Fixed VSG, tuned (H 5 s, D 50 = max, α 0.7) | 0.164 | 0.757 | 0.130 | 0.011 | −17.4 |
| Adaptive-RoCoF VSG, tuned (k_d 480) | 0.165 | 0.835 | 0.130 | 0.012 | −17.7 |
| TD3, residual on standard VSG | 0.188 | 0.776 | 0.156 | 0.001 | −27.2 |
| Bang-bang VSG | 0.328 | 0.922 | 0.275 | 0.002 | −64.8 |
| Fixed VSG, standard (H 3, D 20) | 0.330 | 0.998 | 0.275 | 0.002 | −65.0 |
| BESS droop (no inertia) | 0.547 | 4.872 | 0.274 | 0.045 | −104.5 |
| Diesel only | 3.04 (91 % collapse) | 7.16 | 0.84 | 0 | −491.9 |

**Key finding: the single-event problem has a trivial optimum.** Tuning shows that *maximum damping* is optimal for both fixed and adaptive VSGs, even with a 10× BESS-usage cost (`w_bess` 0.5). After a 0.2–0.4 MW step the diesel has only 0.1–0.2 MW spare, so the BESS must deliver the energy anyway; damping only sets how much frequency error is tolerated meanwhile. Within one 10 s event, nothing makes a lower damping worthwhile, so a fixed max-damping VSG is a near-optimal benchmark that RL cannot clearly beat. To show the value of learned, headroom-aware scheduling, the formulation needs a real trade-off (see the options in PAPER_OUTLINE / the session notes).
