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

---

## Formulation study on the 2024 site data: how much can adaptive H/D scheduling gain?

This is the central methodological result so far. Across every formulation tried, **a single well-tuned fixed VSG is within 1–3 % of an oracle that picks the best fixed (H, D) for each scenario in advance**, so adaptive scheduling (RL or rule-based) has very little room to add value in this plant.

| # | Formulation | Best fixed VSG (val) | Per-scenario oracle gain | Best adaptive rule | TD3 result |
|---|---|---|---|---|---|
| 1 | Single 10 s event, quadratic Δf penalty, w_bess 0.05 | D = 50 (= d_max), H 5 | – | adaptive-RoCoF k_d → ∞ (= max damping) | 4 seeds × 1000 ep: −27.2 vs −17.4 for tuned fixed (test) |
| 1b | as 1 with w_bess 0.5 (10×) | D = 50 still | – | same | – |
| 2 | 30 s, 2–3 events, ±0.2 Hz band, w_bess 1.0, diesel AGC only | D 30 interior | +2.5 (3 %) | band-switching rules worse (−91…−435 vs −82) | – |
| 3 | as 2 + BESS secondary control (K_i 2.0) | H 5, D 25 | – | adaptive k_d = 0 | 4 seeds: drifts below its starting point (−65…−77 vs −56.8), stopped at ep 350 |
| 4 | as 3 + band-power projection + 0.25 s rate limit | unchanged (projection costs 0.06) | – | – | 4 seeds: −63…−66 vs −56.8, stopped at ep 150 |
| 5 | as 4 + fast-power cost (w_fast 2, w_bess 0.1) | H 3, D 15 | +1.3 (1 %) | adaptive k_h = k_d = 0 | pilot 2 seeds × 150 ep: −106…−124 vs −88 |

Why:

* **Strong grid-forming coupling.** At t = 0⁺ the VSG takes K_s/(K_s+K_d) ≈ 71 % of any step through its synchronising coefficient, whatever H and D are. RoCoF stays well inside 1 Hz/s for every reasonable H, so inertia scheduling has little to improve.
* **Secondary control** (diesel + BESS) restores frequency within about 10–20 s. After that, H and D only shape a short transient.
* **Operating points differ mainly in headroom and diesel spare.** Under the projection these change the *feasible* parameter range, but hardly the *optimal* one.
* **Low signal-to-noise.** The 1–3 % available gain is smaller than the variation in return between scenarios, so TD3's critic cannot resolve it, and the residual policy drifts away from its (already near-optimal) starting point.

Implications for the paper (decision for the author):

1. **Report it as the finding.** Under realistic grid-forming VSG + secondary control, a well-tuned fixed VSG is near-optimal, and the value of RL lies elsewhere. The feasibility projection is nearly free and removes saturation, which supports "feasible synthetic inertia". This is a credible, reviewer-proof negative result with the full evidence above.
2. **Pareto framing.** Sweep the reward weights and plot band violation against BESS fast-power energy for the fixed-VSG family vs RL. RL is a contribution only where its points lie beyond the fixed-VSG front.
3. **Change the plant to where adaptation matters.** Candidates: weak grid-forming coupling (lower K_s, or a grid-following BESS with virtual inertia), no or slow secondary control (islanded diesel without AGC), larger events relative to headroom (BESS sized smaller than the event), or communication delays. Check with the oracle test (`per-scenario best fixed` vs `best single fixed`) **before** training: if the oracle gain is under about 5 %, RL will not show a clear win.

---

## Final results: 2024 site data, EMS on, multi-event band formulation

Setup: `configs/default.yaml` as committed. EMS enabled; 30 s episodes with 2–3 events; ±0.2 Hz band; BESS secondary control; reward with fast-power cost. TD3 and DDPG are zero-initialised residual policies on the tuned VSG, **3 seeds × 600 episodes** each (≈35 min per seed). The 200 held-out test scenarios are drawn from the weekly-block test weeks (7.4 % adequacy rejection). Baselines are tuned on validation under the same objective. "Return" is the **objective** return, without the RL training regularisers.

**RQ1 — oracle bound** (`scripts/oracle_test.py`, 40 validation scenarios): the best single fixed VSG (H 3 s, D 15) scores −94.78 and the per-scenario oracle −92.83. **Gain 2.1 % → NO-GO**: adaptive scheduling has very little room to help, and the oracle's choice of D hardly varies with headroom (12–15).

**RQ2 — test-set results** (`results/summary.csv`; RL = seed-averaged):

| Controller | Nadir (Hz) | RoCoF (Hz/s) | Band time (s) | BESS energy (kWh) | Return |
|---|---|---|---|---|---|
| Fixed VSG, tuned (H 3, D 15, α 1.0) | 0.573 | 1.474 | 7.40 | 0.775 | **−105.9** |
| Fixed VSG, tuned + projection | 0.573 | 1.478 | 7.41 | 0.775 | −106.0 |
| TD3 / DDPG, validation-selected (= base; 6 of 6 runs) | 0.573 | 1.476 | 7.42 | 0.801 | −106.1 |
| Fixed VSG, standard (H 3, D 20) | 0.508 | 1.452 | 5.68 | 0.934 | −115.8 |
| Bang-bang VSG | 0.505 | 1.423 | 5.66 | 0.936 | −116.4 |
| **TD3, final policy** | 0.539 | 1.464 | 7.60 | 0.875 | −120.0 |
| DDPG, final policy | 0.604 | 1.533 | 7.84 | 0.878 | −131.6 |
| BESS droop (no inertia) | 0.732 | 5.520 | 5.18 | 0.927 | −286.8 |
| Diesel only | 3.06 (97.5 % collapse) | 7.38 | – | 0 | −557.7 |

Adaptive-RoCoF tuned to k_h = k_d = 0, so it is identical to the standard fixed VSG.

Paired Wilcoxon, Holm-corrected, TD3 final vs tuned fixed VSG:
* **Better frequency:** nadir −0.037 Hz (better in 74 % of scenarios, p ≈ 4·10⁻¹⁰) and RoCoF −0.022 Hz/s (p ≈ 0.004).
* **More BESS energy:** +0.076 kWh (more in 93 % of scenarios, p ≈ 2·10⁻²⁸).
* **Worse objective return:** −10.7 (p ≈ 9·10⁻³²).

TD3 beats DDPG on nadir, RoCoF and return (all p < 10⁻⁵).

**Pareto / dominance** (`scripts/pareto.py`, objectives: fast energy, band time, nadir, RoCoF):
* **TD3 final is non-dominated.** It sits between the fixed D = 15 and D = 20 settings, with a nadir close to what a fixed D ≈ 17 would give and a slightly worse band time. It is a different point on the same trade-off, not a better one.
* **DDPG final is dominated** by the tuned fixed VSG.

**RQ3 — cost of feasibility:** the projection changes the tuned VSG's return by −0.1 (−105.9 → −106.0) and its metrics by < 1 %. Synthetic-inertia commitments can be made deliverable at essentially no cost.

**Learning dynamics** (`fig_learning_curves`): in all 6 runs the best validation checkpoint is episode 0 (the base controller). Training moves both algorithms below it; TD3 degrades less and with smaller seed spread. Diagnosis: the attainable improvement (≈2 %, RQ1) is below the noise in the critic's value estimates across operating points and events, so policy gradients follow noise.

Training-curve values include the RL regularisers (action rate, trust region), so they sit below the test-set objective returns.

To reproduce at the paper's full budget: `bash run_all.sh` (5 seeds × 1000 episodes; ≈4 h on 4 cores).

---

## Full-budget results (5 seeds × 1000 episodes) + projection ablation — **use these in the paper**

Setup as in the previous section, at the full budget: TD3, DDPG and TD3 **without** the projection (`td3_noproj`), 5 seeds × 1000 episodes each (≈52–65 min per seed). Parameters are now clipped to the feasible bounds *after* the rate limit (feasibility before smoothness). There are 200 test scenarios. P-values are paired Wilcoxon, Holm-corrected over all comparisons. Source: `results/summary.csv`, `results/significance.csv`.

| Controller | Nadir (Hz) | RoCoF (Hz/s) | BESS (kWh) | Saturation (s) | **Infeasible commit. (s)** | Return |
|---|---|---|---|---|---|---|
| Fixed VSG, tuned (H 3, D 15) | 0.573 | 1.474 | 0.775 | 0.103 | 2.330 | **−105.9** |
| Fixed VSG, tuned + projection | 0.573 | 1.479 | 0.775 | 0.123 | **0.007** | −106.1 |
| TD3 / DDPG validation-selected (= base, 10/10 runs) | 0.573 | 1.479 | 0.775 | 0.123 | 0.007 | −106.1 |
| Fixed VSG, standard (H 3, D 20) | 0.508 | 1.452 | 0.934 | 0.126 | 2.340 | −115.8 |
| Bang-bang VSG | 0.505 | 1.423 | 0.936 | 0.121 | 2.989 | −116.4 |
| **TD3, final policy** | 0.522 | 1.482 | 0.849 | 0.136 | **0.019** | −122.0 |
| TD3 *without projection*, final policy | 0.540 | 1.457 | 0.832 | 0.108 | 5.069 | −124.2 |
| DDPG, final policy | 0.596 | 1.594 | 0.845 | 0.128 | 0.022 | −133.4 |
| BESS droop (no inertia) | 0.732 | 5.520 | 0.927 | 0.645 | 1.103 | −286.8 |
| Diesel only | 3.06 (97.5 % collapse) | 7.38 | 0 | 0 | 0 | −557.7 |

"Infeasible commitment" is the time per 30 s episode during which the scheduled D (damping power at the ±0.2 Hz band edge) or H (inertial power at 1 Hz/s) needs more power than the direction-aware BESS + PV headroom.

**E2 — projection ablation (the paper's main positive result):**
* **Without the projection, TD3 learns to over-commit.** It has infeasible commitments for 5.07 s of every 30 s episode (4–7 s on every seed), more than the fixed VSG (2.33 s). With the projection this falls to 0.02 s: lower in 98 % of scenarios, p_Holm ≈ 6·10⁻³².
* **The projection also improves TD3's nadir:** 0.522 vs 0.540 Hz, p_Holm ≈ 3·10⁻⁶. Its effect on return (−122.0 vs −124.2) is not significant after Holm correction (raw p = 0.003, p_Holm = 0.087).
* **For the tuned fixed VSG, feasibility costs almost nothing:** infeasible time 2.33 → 0.007 s, nadir unchanged (p = 0.56), return −105.93 → −106.06.
* **Caveat to report:** actual current-limit saturation is slightly *higher* with the projection (0.123 vs 0.103 s for the fixed VSG; 0.136 vs 0.108 s for TD3). It is small in absolute terms. A likely cause is that lower damping lets frequency drift further, so BESS secondary control raises the set-point harder.

**RL vs tuned fixed VSG (full budget):**
* TD3's learned policy lowers the nadir by 0.061 Hz (better in 85 % of scenarios, p_Holm ≈ 7·10⁻²¹). RoCoF is not significantly different.
* It uses 0.067 kWh more BESS energy (p_Holm ≈ 10⁻³¹), giving a worse return (−13.5, p_Holm ≈ 6·10⁻³²).
* It is non-dominated against the fixed-VSG family (fast energy, band time, nadir, RoCoF): a different trade-off, not a better one.
* DDPG's learned policy is dominated by the tuned fixed VSG and is worse than TD3 on nadir, RoCoF and return (all p_Holm < 10⁻⁹).
* In all 15 runs the best validation checkpoint is the untrained base controller. More training (600 → 1000 episodes) does not change this.
