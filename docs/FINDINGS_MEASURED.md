# Findings with measured weather (Cabauw 1 Hz irradiance + FINO1 80 m wind)

Full tables: [`results_measured/RESULTS.md`](../results_measured/RESULTS.md);
figures in `results_measured/figures/`. Same protocol as the synthetic study:
5 seeds × {DDPG, TD3} × 1000 episodes, baselines tuned on validation
episodes, chronological train / validation / test split of the records.

## Data

| | Source | Record | Validity |
|---|---|---|---|
| Irradiance | BSRN Cabauw 1 Hz GHI (Knap & Mol 2022, Zenodo 7093164) | 31 Mar, 17 Jul, 22 Jul 2015 (259 065 s) | no missing or negative values; night ≤ 1.7 W/m²; timestamps match the computed sunrise and solar noon (UTC); max clearness index 1.14 (cloud enhancement, below the 1.4 limit); no stuck sensor |
| Wind | FINO1 sonic anemometer, 80 m, 10 Hz → 1 s means | 21–23 Jan 2007 (255 599 s) | one 1 h gap (skipped); 0.1–25.4 m/s; median turbulence intensity 8 % (typical offshore); 13 isolated single-sample dropouts (0.005 %) removed by despiking |

Windows keep their measured relative variability and are rescaled to the
Nakhon Ratchasima levels (`rescale_to_site: true`).

## Results (mean ± 95 % CI over 5 seeds)

### Held-out stress test (50 randomised episodes on unseen weather)

| Controller | IAE (Hz·s) | Nadir (Hz) | RoCoF (Hz/s) | Reserve (pu) |
|---|---|---|---|---|
| Fixed high (paper) | 3.321 | 49.688 | 0.648 | 0.394 (100 % derated) |
| Fixed tuned | 2.392 | 49.738 | 0.546 | 0.299 |
| Rule-based adaptive | 2.280 | 49.757 | 0.525 | 0.255 |
| DDPG | 2.271 ± 0.129 | 49.776 ± 0.010 | 0.498 ± 0.023 | 0.226 ± 0.025 |
| **TD3** | **2.261 ± 0.129** | 49.768 ± 0.017 | 0.510 ± 0.044 | **0.218 ± 0.018** |

* **TD3 beats the tuned constant controller on IAE by 5.5 %** on held-out
  real weather. It is better on 5 of 5 seeds and on 33 of 50 episodes, and the
  difference is significant (one-sample t = −2.82, df = 4, critical value
  2.78).
* DDPG improves IAE by 5.1 % (4 of 5 seeds), just short of significance (t = −2.61).
* Against the rule-based adaptive controller both agents are equal on IAE
  (−0.4 to −0.8 %, not significant), but they reserve **11–15 % less
  headroom** and give a higher nadir and lower RoCoF.
* Reward (the full multi-objective): TD3 beats both baselines on 5/5 and 4/5
  seeds (stress); DDPG on 5/5 and 4/5.

### Test scenarios (five deterministic real-weather windows)

TD3 ties both tuned baselines on IAE (1.844 vs 1.845 / 1.847 Hz·s). It uses
**0.200 pu reserve vs 0.299 pu for the tuned constant controller (−33 %)**
and 0.243 pu for the rule-based one (−18 %), with the fewest derated steps
among the learned controllers (7.8 % vs 11.9 % for DDPG).

### TD3 vs DDPG

No metric differs significantly (|t| < 1 everywhere). TD3 is marginally
better on IAE, reserve and derating, but within seed noise.

### Critic bias, with real weather

| | Selected checkpoint (Q − G) | Episode 1000 (Q − G) |
|---|---|---|
| DDPG | −10, +30, +43, +9, +55 (4 of 5 positive) | +79, +52, +56, +73, +57 |
| TD3 | −33, −27, −48, −21, −33 (all negative) | −210, −200, −189, −179, −160 |

This confirms the paper's claim that DDPG over- and TD3 underestimates, now
with a direct Monte-Carlo measurement (Fig. 6c). TD3's pessimism grows during
training. The best checkpoints come at episodes 30–300 (TD3) and 20–410
(DDPG), so validation-based model selection is again essential.

### What does not change with real data

* The tuned baselines still settle faster (0.08–0.09 s vs 0.34–0.36 s).
* Both tuned baselines still choose J = 0: the controllers mainly schedule
  damping, with inertia raised briefly at contingency onsets.

## Synthetic vs measured weather

| | Synthetic | Measured |
|---|---|---|
| TD3 vs fixed tuned, stress IAE | +3.2 % (worse) | **−5.5 % (better, significant)** |
| TD3 reserve vs fixed tuned (test) | −23 % | **−33 %** |
| TD3 vs DDPG | not significant | not significant |

The learned controllers gain more over constant gains when the disturbances
are real. Measured cloud edges and turbulent wind vary more than the smooth
synthetic profiles, so a state-feedback policy has more to adapt to. This is
the most useful message for the paper.

## Suggested abstract claims (measured-data study)

> On held-out measured weather (1-Hz BSRN irradiance and 80-m offshore sonic
> wind), the TD3 controller reduces the integral absolute frequency error by
> 5.5 % relative to the best feasible constant-gain VSG (significant over
> five seeds), while reserving 27 % less converter headroom (0.218 vs
> 0.299 pu). Against a tuned rule-based adaptive VSG it achieves equal
> regulation with 15 % less reserved headroom. All high-gain constant designs
> from the literature are infeasible and derated in 100 % of timesteps.
> Monte-Carlo critic diagnostics confirm DDPG overestimation and growing TD3
> underestimation.
