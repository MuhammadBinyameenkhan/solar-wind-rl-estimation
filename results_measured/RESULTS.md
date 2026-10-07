# Results

Seeds: [0, 1, 2, 3, 4]. Episodes per run: 1000. Weather: measured. Test = five deterministic paper scenarios (seed 70007); stress = 50 randomised held-out episodes. RL values: mean ± 95 % CI over seeds (each seed averaged over the episodes). Baselines are deterministic and tuned on the validation episodes only.

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
| DDPG-VSG (n=5) | 1.856 ± 0.073 | 0.268 ± 0.010 | 25.95 ± 1.90 | 49.803 ± 0.016 | 0.429 ± 0.018 | 0.356 ± 0.164 | 27.6 ± 2.1 | 0.210 ± 0.028 | 11.9 ± 3.8 | 0.744 ± 0.010 | 0.00 ± 0.00 |
| TD3-VSG (n=5) | 1.844 ± 0.070 | 0.274 ± 0.013 | 25.08 ± 1.38 | 49.798 ± 0.014 | 0.429 ± 0.022 | 0.335 ± 0.196 | 24.6 ± 4.6 | 0.200 ± 0.014 | 7.8 ± 6.2 | 0.744 ± 0.009 | 0.00 ± 0.00 |

## Held-out stress test

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 12.311 | 13.383 | 181.46 | 48.044 | 4.008 | 3.052 | 51.1 | 0.000 | 0.0 | 0.000 | 0.02 |
| Fixed low | 4.725 | 1.709 | 65.49 | 49.488 | 1.029 | 0.755 | 21.7 | 0.180 | 0.0 | 0.670 | 0.00 |
| Fixed high | 3.321 | 0.890 | 45.35 | 49.688 | 0.648 | 0.250 | 13.3 | 0.394 | 100.0 | 0.845 | 0.00 |
| Fixed max | 4.200 | 1.424 | 57.52 | 49.604 | 0.716 | 0.401 | 11.9 | 0.391 | 100.0 | 0.750 | 0.00 |
| Fixed tuned | 2.392 | 0.438 | 32.83 | 49.738 | 0.546 | 0.106 | 22.5 | 0.299 | 5.0 | 0.989 | 0.00 |
| Rule-based adaptive | 2.280 | 0.380 | 31.86 | 49.757 | 0.525 | 0.127 | 25.0 | 0.255 | 8.4 | 0.995 | 0.00 |
| DDPG-VSG (n=5) | 2.271 ± 0.129 | 0.374 ± 0.031 | 31.98 ± 3.03 | 49.776 ± 0.010 | 0.498 ± 0.023 | 0.420 ± 0.057 | 21.7 ± 2.4 | 0.226 ± 0.025 | 16.4 ± 5.7 | 0.985 ± 0.016 | 0.00 ± 0.00 |
| TD3-VSG (n=5) | 2.261 ± 0.129 | 0.381 ± 0.034 | 30.99 ± 2.00 | 49.768 ± 0.017 | 0.510 ± 0.044 | 0.358 ± 0.199 | 18.5 ± 4.2 | 0.218 ± 0.018 | 9.8 ± 5.4 | 0.986 ± 0.016 | 0.00 ± 0.00 |

## Statistical comparisons (Welch t on per-seed means)

| Comparison | Metric | Test: mean A − mean B | t | Stress: mean A − mean B | t |
|---|---|---|---|---|---|
| TD3 − DDPG | iae | -0.0120 | -0.33 | -0.0097 | -0.15 |
| TD3 − DDPG | ise | +0.0057 | +0.96 | +0.0066 | +0.40 |
| TD3 − DDPG | settle_s | -0.0208 | -0.23 | -0.0611 | -0.82 |
| TD3 − DDPG | reserve_pu | -0.0101 | -0.90 | -0.0077 | -0.70 |
| TD3 − DDPG | reward | +12.5022 | +0.51 | +24.7384 | +0.65 |

## RL vs best non-learning controller (seeds that beat it)

* DDPG vs Fixed tuned — iae (test): 2/5 seeds better (RL mean 1.856, baseline 1.845)
* DDPG vs Fixed tuned — iae (stress): 4/5 seeds better (RL mean 2.271, baseline 2.392)
* DDPG vs Fixed tuned — reward (test): 4/5 seeds better (RL mean 439.4, baseline 404.5)
* DDPG vs Fixed tuned — reward (stress): 5/5 seeds better (RL mean 216, baseline 121.1)
* DDPG vs Rule-based adaptive — iae (test): 2/5 seeds better (RL mean 1.856, baseline 1.847)
* DDPG vs Rule-based adaptive — iae (stress): 4/5 seeds better (RL mean 2.271, baseline 2.28)
* DDPG vs Rule-based adaptive — reward (test): 4/5 seeds better (RL mean 439.4, baseline 389.4)
* DDPG vs Rule-based adaptive — reward (stress): 4/5 seeds better (RL mean 216, baseline 170.1)
* TD3 vs Fixed tuned — iae (test): 3/5 seeds better (RL mean 1.844, baseline 1.845)
* TD3 vs Fixed tuned — iae (stress): 5/5 seeds better (RL mean 2.261, baseline 2.392)
* TD3 vs Fixed tuned — reward (test): 5/5 seeds better (RL mean 451.9, baseline 404.5)
* TD3 vs Fixed tuned — reward (stress): 5/5 seeds better (RL mean 240.7, baseline 121.1)
* TD3 vs Rule-based adaptive — iae (test): 3/5 seeds better (RL mean 1.844, baseline 1.847)
* TD3 vs Rule-based adaptive — iae (stress): 3/5 seeds better (RL mean 2.261, baseline 2.28)
* TD3 vs Rule-based adaptive — reward (test): 5/5 seeds better (RL mean 451.9, baseline 389.4)
* TD3 vs Rule-based adaptive — reward (stress): 4/5 seeds better (RL mean 240.7, baseline 170.1)

## Critic calibration at the selected checkpoint (validation states)

Bias = critic estimate − Monte-Carlo discounted return actually obtained.

| Algorithm | Seed | Q1 − G | min(Q1,Q2) − G |
|---|---|---|---|
| DDPG | 0 | -9.60 | -9.60 |
| DDPG | 1 | +30.37 | +30.37 |
| DDPG | 2 | +43.15 | +43.15 |
| DDPG | 3 | +8.58 | +8.58 |
| DDPG | 4 | +55.44 | +55.44 |
| TD3 | 0 | -33.37 | -35.54 |
| TD3 | 1 | -27.12 | -29.23 |
| TD3 | 2 | -48.48 | -51.04 |
| TD3 | 3 | -20.59 | -21.52 |
| TD3 | 4 | -32.62 | -34.77 |
