> **SUPERSEDED.** These results used weather windows rescaled to levels that were not measurements (708 W/m², 5–7 m/s wind). A re-run at the measured levels is in progress and will replace this file.

# Results

Seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]. Episodes per run: 1000. Weather: measured. Test = five deterministic paper scenarios (seed 70007); stress = 50 randomised held-out episodes. RL values: mean ± 95 % CI over seeds (each seed averaged over the episodes). Baselines are deterministic and tuned on the validation episodes only.

* **Fixed tuned**: J = 0.0, D = 30.0, Kq = 20.0  
* **Rule-based adaptive**: J0 = 0.0, kJ = 0.0, D0 = 20.0, kD = 80.0, Kq = 20.0

## Test scenarios (average of the five)

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 8.813 | 5.863 | 126.58 | 48.432 | 3.112 | 3.104 | 60.7 | 0.000 | 0.0 | 0.000 | 0.00 |
| Fixed low | 3.640 | 1.065 | 49.87 | 49.587 | 0.812 | 0.676 | 25.8 | 0.180 | 0.0 | 0.517 | 0.00 |
| Fixed high | 2.659 | 0.611 | 36.11 | 49.739 | 0.545 | 0.200 | 17.9 | 0.380 | 100.0 | 0.638 | 0.00 |
| Fixed max | 3.336 | 0.959 | 45.45 | 49.672 | 0.597 | 0.328 | 15.2 | 0.378 | 100.0 | 0.567 | 0.00 |
| Fixed tuned | 1.845 | 0.273 | 24.97 | 49.780 | 0.434 | 0.080 | 27.6 | 0.299 | 7.0 | 0.764 | 0.00 |
| Rule-based adaptive | 1.847 | 0.264 | 25.41 | 49.789 | 0.444 | 0.088 | 31.2 | 0.243 | 9.3 | 0.756 | 0.00 |
| DDPG-VSG (n=10) | 1.869 ± 0.050 | 0.273 ± 0.013 | 26.08 ± 1.05 | 49.807 ± 0.007 | 0.427 ± 0.015 | 0.328 ± 0.078 | 27.4 ± 1.7 | 0.212 ± 0.014 | 10.5 ± 4.1 | 0.744 ± 0.006 | 0.00 ± 0.00 |
| TD3-VSG (n=10) | 1.908 ± 0.091 | 0.286 ± 0.020 | 26.39 ± 1.70 | 49.801 ± 0.009 | 0.438 ± 0.020 | 0.388 ± 0.118 | 26.0 ± 2.4 | 0.204 ± 0.009 | 8.7 ± 3.3 | 0.737 ± 0.010 | 0.00 ± 0.00 |

## Held-out stress test

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 12.311 | 13.383 | 181.46 | 48.044 | 4.008 | 3.052 | 51.1 | 0.000 | 0.0 | 0.000 | 0.02 |
| Fixed low | 4.725 | 1.709 | 65.49 | 49.488 | 1.029 | 0.755 | 21.7 | 0.180 | 0.0 | 0.670 | 0.00 |
| Fixed high | 3.321 | 0.890 | 45.35 | 49.688 | 0.648 | 0.250 | 13.3 | 0.394 | 100.0 | 0.845 | 0.00 |
| Fixed max | 4.200 | 1.424 | 57.52 | 49.604 | 0.716 | 0.401 | 11.9 | 0.391 | 100.0 | 0.750 | 0.00 |
| Fixed tuned | 2.392 | 0.438 | 32.83 | 49.738 | 0.546 | 0.106 | 22.5 | 0.299 | 5.0 | 0.989 | 0.00 |
| Rule-based adaptive | 2.280 | 0.380 | 31.86 | 49.757 | 0.525 | 0.127 | 25.0 | 0.255 | 8.4 | 0.995 | 0.00 |
| DDPG-VSG (n=10) | 2.258 ± 0.058 | 0.372 ± 0.016 | 31.64 ± 1.33 | 49.780 ± 0.006 | 0.495 ± 0.010 | 0.368 ± 0.069 | 21.6 ± 1.8 | 0.228 ± 0.013 | 14.3 ± 3.5 | 0.988 ± 0.007 | 0.00 ± 0.00 |
| TD3-VSG (n=10) | 2.332 ± 0.102 | 0.399 ± 0.027 | 32.52 ± 1.94 | 49.769 ± 0.010 | 0.505 ± 0.022 | 0.456 ± 0.116 | 19.1 ± 1.8 | 0.221 ± 0.009 | 10.3 ± 2.6 | 0.978 ± 0.012 | 0.00 ± 0.00 |

## Statistical comparisons (Welch t on per-seed means)

| Comparison | Metric | Test: mean A − mean B | t | Stress: mean A − mean B | t |
|---|---|---|---|---|---|
| TD3 − DDPG | iae | +0.0386 | +0.84 | +0.0737 | +1.42 |
| TD3 − DDPG | ise | +0.0133 | +1.25 | +0.0274 | +2.00 |
| TD3 − DDPG | settle_s | +0.0592 | +0.95 | +0.0883 | +1.48 |
| TD3 − DDPG | reserve_pu | -0.0078 | -1.10 | -0.0074 | -1.07 |
| TD3 − DDPG | reward | +11.9495 | +0.70 | +4.6194 | +0.20 |

## RL vs best non-learning controller (seeds that beat it)

* DDPG vs Fixed tuned — iae (test): 3/10 seeds better (RL mean 1.869, baseline 1.845)
* DDPG vs Fixed tuned — iae (stress): 9/10 seeds better (RL mean 2.258, baseline 2.392)
* DDPG vs Fixed tuned — reward (test): 8/10 seeds better (RL mean 430, baseline 404.5)
* DDPG vs Fixed tuned — reward (stress): 10/10 seeds better (RL mean 221.6, baseline 121.1)
* DDPG vs Rule-based adaptive — iae (test): 3/10 seeds better (RL mean 1.869, baseline 1.847)
* DDPG vs Rule-based adaptive — iae (stress): 8/10 seeds better (RL mean 2.258, baseline 2.28)
* DDPG vs Rule-based adaptive — reward (test): 8/10 seeds better (RL mean 430, baseline 389.4)
* DDPG vs Rule-based adaptive — reward (stress): 8/10 seeds better (RL mean 221.6, baseline 170.1)
* TD3 vs Fixed tuned — iae (test): 4/10 seeds better (RL mean 1.908, baseline 1.845)
* TD3 vs Fixed tuned — iae (stress): 8/10 seeds better (RL mean 2.332, baseline 2.392)
* TD3 vs Fixed tuned — reward (test): 9/10 seeds better (RL mean 442, baseline 404.5)
* TD3 vs Fixed tuned — reward (stress): 10/10 seeds better (RL mean 226.3, baseline 121.1)
* TD3 vs Rule-based adaptive — iae (test): 4/10 seeds better (RL mean 1.908, baseline 1.847)
* TD3 vs Rule-based adaptive — iae (stress): 4/10 seeds better (RL mean 2.332, baseline 2.28)
* TD3 vs Rule-based adaptive — reward (test): 10/10 seeds better (RL mean 442, baseline 389.4)
* TD3 vs Rule-based adaptive — reward (stress): 9/10 seeds better (RL mean 226.3, baseline 170.1)

## Critic calibration at the selected checkpoint (validation states)

Bias = critic estimate − Monte-Carlo discounted return actually obtained.

| Algorithm | Seed | Q1 − G | min(Q1,Q2) − G |
|---|---|---|---|
| DDPG | 0 | -9.60 | -9.60 |
| DDPG | 1 | +30.37 | +30.37 |
| DDPG | 2 | +43.15 | +43.15 |
| DDPG | 3 | +8.58 | +8.58 |
| DDPG | 4 | +55.44 | +55.44 |
| DDPG | 5 | -10.94 | -10.94 |
| DDPG | 6 | +31.72 | +31.72 |
| DDPG | 7 | +30.61 | +30.61 |
| DDPG | 8 | +37.29 | +37.29 |
| DDPG | 9 | +17.18 | +17.18 |
| TD3 | 0 | -33.37 | -35.54 |
| TD3 | 1 | -27.12 | -29.23 |
| TD3 | 2 | -48.48 | -51.04 |
| TD3 | 3 | -20.59 | -21.52 |
| TD3 | 4 | -32.62 | -34.77 |
| TD3 | 5 | -32.51 | -35.00 |
| TD3 | 6 | -15.59 | -16.06 |
| TD3 | 7 | -22.77 | -23.36 |
| TD3 | 8 | -16.50 | -17.34 |
| TD3 | 9 | -19.02 | -20.63 |
