# Results

Seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]. Episodes per run: 1000. Weather: measured. Test = five deterministic paper scenarios (seed 70007); stress = 50 randomised held-out episodes. RL values: mean ± 95 % CI over seeds (each seed averaged over the episodes). Baselines are deterministic and tuned on the validation episodes only.

* **Fixed tuned**: J = 0.0, D = 35.0, Kq = 20.0  
* **Rule-based adaptive**: J0 = 0.0, kJ = 0.0, D0 = 20.0, kD = 80.0, Kq = 20.0

## Test scenarios (average of the five)

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 8.871 | 5.915 | 127.07 | 48.432 | 3.116 | 3.104 | 60.6 | 0.000 | 0.0 | 0.000 | 0.00 |
| Fixed low | 3.670 | 1.079 | 50.16 | 49.586 | 0.812 | 0.684 | 25.5 | 0.180 | 0.0 | 0.521 | 0.00 |
| Fixed high | 2.657 | 0.601 | 36.08 | 49.739 | 0.540 | 0.200 | 17.5 | 0.382 | 100.0 | 0.646 | 0.00 |
| Fixed max | 3.335 | 0.943 | 45.42 | 49.671 | 0.590 | 0.320 | 14.9 | 0.380 | 100.0 | 0.575 | 0.00 |
| Fixed tuned | 1.734 | 0.243 | 23.35 | 49.800 | 0.416 | 0.056 | 28.7 | 0.333 | 40.8 | 0.788 | 0.00 |
| Rule-based adaptive | 1.857 | 0.264 | 25.50 | 49.786 | 0.440 | 0.088 | 30.5 | 0.244 | 10.2 | 0.762 | 0.00 |
| DDPG-VSG (n=10) | 1.884 ± 0.067 | 0.280 ± 0.021 | 25.80 ± 0.96 | 49.802 ± 0.012 | 0.428 ± 0.019 | 0.275 ± 0.127 | 25.8 ± 4.7 | 0.236 ± 0.020 | 14.1 ± 3.3 | 0.751 ± 0.009 | 0.00 ± 0.00 |
| TD3-VSG (n=10) | 1.857 ± 0.054 | 0.271 ± 0.014 | 25.58 ± 0.91 | 49.809 ± 0.009 | 0.414 ± 0.016 | 0.310 ± 0.125 | 25.8 ± 3.6 | 0.228 ± 0.018 | 9.8 ± 3.7 | 0.752 ± 0.006 | 0.00 ± 0.00 |

## Held-out stress test

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 12.346 | 13.426 | 181.73 | 48.043 | 4.011 | 3.080 | 50.8 | 0.000 | 0.0 | 0.000 | 0.02 |
| Fixed low | 4.748 | 1.719 | 65.75 | 49.487 | 1.030 | 0.751 | 21.3 | 0.180 | 0.0 | 0.673 | 0.00 |
| Fixed high | 3.176 | 0.814 | 43.46 | 49.703 | 0.610 | 0.248 | 11.8 | 0.424 | 99.6 | 0.868 | 0.00 |
| Fixed max | 4.032 | 1.311 | 55.35 | 49.622 | 0.672 | 0.398 | 10.3 | 0.421 | 100.0 | 0.776 | 0.00 |
| Fixed tuned | 2.180 | 0.365 | 29.84 | 49.766 | 0.494 | 0.081 | 21.6 | 0.342 | 20.1 | 1.023 | 0.00 |
| Rule-based adaptive | 2.278 | 0.377 | 31.85 | 49.757 | 0.521 | 0.128 | 24.2 | 0.256 | 7.6 | 1.000 | 0.00 |
| DDPG-VSG (n=10) | 2.222 ± 0.076 | 0.370 ± 0.036 | 30.54 ± 0.82 | 49.772 ± 0.019 | 0.492 ± 0.020 | 0.315 ± 0.101 | 18.4 ± 3.1 | 0.258 ± 0.015 | 13.0 ± 2.0 | 1.000 ± 0.010 | 0.00 ± 0.00 |
| TD3-VSG (n=10) | 2.161 ± 0.054 | 0.344 ± 0.014 | 30.03 ± 1.03 | 49.786 ± 0.010 | 0.475 ± 0.015 | 0.350 ± 0.093 | 18.6 ± 2.5 | 0.250 ± 0.013 | 11.8 ± 4.5 | 1.005 ± 0.006 | 0.00 ± 0.00 |

## Statistical comparisons (Welch t on per-seed means)

| Comparison | Metric | Test: mean A − mean B | t | Stress: mean A − mean B | t |
|---|---|---|---|---|---|
| TD3 − DDPG | iae | -0.0273 | -0.72 | -0.0607 | -1.47 |
| TD3 − DDPG | ise | -0.0091 | -0.82 | -0.0264 | -1.53 |
| TD3 − DDPG | settle_s | +0.0356 | +0.45 | +0.0356 | +0.58 |
| TD3 − DDPG | reserve_pu | -0.0081 | -0.69 | -0.0078 | -0.93 |
| TD3 − DDPG | reward | +58.1127 | +1.77 | +69.1876 | +1.89 |

## RL vs best non-learning controller (seeds that beat it)

* DDPG vs Fixed tuned — iae (test): 1/10 seeds better (RL mean 1.884, baseline 1.734)
* DDPG vs Fixed tuned — iae (stress): 4/10 seeds better (RL mean 2.222, baseline 2.18)
* DDPG vs Fixed tuned — reward (test): 9/10 seeds better (RL mean 351.9, baseline 223.7)
* DDPG vs Fixed tuned — reward (stress): 8/10 seeds better (RL mean 179.1, baseline 113)
* DDPG vs Rule-based adaptive — iae (test): 4/10 seeds better (RL mean 1.884, baseline 1.857)
* DDPG vs Rule-based adaptive — iae (stress): 7/10 seeds better (RL mean 2.222, baseline 2.278)
* DDPG vs Rule-based adaptive — reward (test): 4/10 seeds better (RL mean 351.9, baseline 391.3)
* DDPG vs Rule-based adaptive — reward (stress): 6/10 seeds better (RL mean 179.1, baseline 187.5)
* TD3 vs Fixed tuned — iae (test): 1/10 seeds better (RL mean 1.857, baseline 1.734)
* TD3 vs Fixed tuned — iae (stress): 6/10 seeds better (RL mean 2.161, baseline 2.18)
* TD3 vs Fixed tuned — reward (test): 10/10 seeds better (RL mean 410, baseline 223.7)
* TD3 vs Fixed tuned — reward (stress): 10/10 seeds better (RL mean 248.3, baseline 113)
* TD3 vs Rule-based adaptive — iae (test): 5/10 seeds better (RL mean 1.857, baseline 1.857)
* TD3 vs Rule-based adaptive — iae (stress): 9/10 seeds better (RL mean 2.161, baseline 2.278)
* TD3 vs Rule-based adaptive — reward (test): 6/10 seeds better (RL mean 410, baseline 391.3)
* TD3 vs Rule-based adaptive — reward (stress): 10/10 seeds better (RL mean 248.3, baseline 187.5)

## Critic calibration at the selected checkpoint (validation states)

Bias = critic estimate − Monte-Carlo discounted return actually obtained.

| Algorithm | Seed | Q1 − G | min(Q1,Q2) − G |
|---|---|---|---|
| DDPG | 0 | -7.12 | -7.12 |
| DDPG | 1 | -8.45 | -8.45 |
| DDPG | 2 | +25.24 | +25.24 |
| DDPG | 3 | +31.47 | +31.47 |
| DDPG | 4 | -0.28 | -0.28 |
| DDPG | 5 | +34.97 | +34.97 |
| DDPG | 6 | -8.77 | -8.77 |
| DDPG | 7 | +16.35 | +16.35 |
| DDPG | 8 | +10.31 | +10.31 |
| DDPG | 9 | +20.22 | +20.22 |
| TD3 | 0 | -38.47 | -39.00 |
| TD3 | 1 | -51.22 | -53.09 |
| TD3 | 2 | -36.83 | -37.67 |
| TD3 | 3 | -56.46 | -57.68 |
| TD3 | 4 | -41.78 | -43.25 |
| TD3 | 5 | -54.40 | -55.25 |
| TD3 | 6 | -38.32 | -40.20 |
| TD3 | 7 | -27.42 | -28.11 |
| TD3 | 8 | -36.58 | -37.57 |
| TD3 | 9 | -26.30 | -27.81 |
