# Results

Seeds: [0, 1, 2, 3, 4]. Episodes per run: 1000. Weather: calibrated. Test = five deterministic paper scenarios (seed 70007); stress = 50 randomised held-out episodes. RL values: mean ± 95 % CI over seeds (each seed averaged over the episodes). Baselines are deterministic and tuned on the validation episodes only.

* **Fixed tuned**: J = 0.0, D = 30.0, Kq = 20.0  
* **Rule-based adaptive**: J0 = 0.0, kJ = 0.0, D0 = 20.0, kD = 80.0, Kq = 20.0

## Test scenarios (average of the five)

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 8.908 | 5.988 | 128.17 | 48.408 | 3.222 | 2.972 | 60.4 | 0.000 | 0.0 | 0.000 | 0.00 |
| Fixed low | 3.664 | 1.064 | 50.51 | 49.579 | 0.828 | 0.656 | 25.4 | 0.180 | 0.0 | 0.521 | 0.00 |
| Fixed high | 2.644 | 0.594 | 36.13 | 49.730 | 0.541 | 0.204 | 17.2 | 0.385 | 100.0 | 0.646 | 0.00 |
| Fixed max | 3.319 | 0.934 | 45.48 | 49.665 | 0.592 | 0.324 | 14.6 | 0.383 | 100.0 | 0.576 | 0.00 |
| Fixed tuned | 1.857 | 0.273 | 25.27 | 49.778 | 0.450 | 0.084 | 26.4 | 0.299 | 6.1 | 0.768 | 0.00 |
| Rule-based adaptive | 1.859 | 0.261 | 25.76 | 49.787 | 0.450 | 0.096 | 29.5 | 0.244 | 8.4 | 0.761 | 0.00 |
| DDPG-VSG (n=5) | 1.857 ± 0.185 | 0.267 ± 0.048 | 26.06 ± 3.14 | 49.807 ± 0.011 | 0.423 ± 0.039 | 0.326 ± 0.206 | 29.0 ± 10.4 | 0.238 ± 0.055 | 10.9 ± 7.2 | 0.754 ± 0.024 | 0.00 ± 0.00 |
| TD3-VSG (n=5) | 1.888 ± 0.064 | 0.274 ± 0.020 | 27.17 ± 1.45 | 49.812 ± 0.006 | 0.399 ± 0.025 | 0.494 ± 0.161 | 26.5 ± 4.8 | 0.229 ± 0.037 | 16.0 ± 7.5 | 0.749 ± 0.009 | 0.00 ± 0.00 |

## Held-out stress test

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 11.514 | 11.787 | 170.26 | 48.211 | 3.742 | 5.504 | 47.4 | 0.000 | 0.0 | 0.000 | 0.02 |
| Fixed low | 4.412 | 1.474 | 61.40 | 49.528 | 0.962 | 0.668 | 19.4 | 0.180 | 0.0 | 0.629 | 0.00 |
| Fixed high | 3.184 | 0.823 | 43.87 | 49.694 | 0.622 | 0.238 | 11.3 | 0.383 | 100.0 | 0.780 | 0.00 |
| Fixed max | 3.997 | 1.302 | 55.17 | 49.616 | 0.687 | 0.373 | 10.0 | 0.380 | 100.0 | 0.692 | 0.00 |
| Fixed tuned | 2.233 | 0.381 | 30.75 | 49.760 | 0.517 | 0.093 | 22.6 | 0.299 | 7.2 | 0.919 | 0.00 |
| Rule-based adaptive | 2.191 | 0.347 | 30.59 | 49.772 | 0.512 | 0.120 | 24.8 | 0.251 | 10.1 | 0.919 | 0.00 |
| DDPG-VSG (n=5) | 2.248 ± 0.193 | 0.360 ± 0.052 | 31.74 ± 3.18 | 49.784 ± 0.007 | 0.495 ± 0.035 | 0.434 ± 0.382 | 21.2 ± 6.5 | 0.242 ± 0.052 | 13.3 ± 9.2 | 0.911 ± 0.025 | 0.00 ± 0.00 |
| TD3-VSG (n=5) | 2.304 ± 0.048 | 0.366 ± 0.016 | 33.15 ± 1.02 | 49.788 ± 0.010 | 0.480 ± 0.029 | 0.518 ± 0.202 | 18.3 ± 3.4 | 0.233 ± 0.035 | 17.7 ± 6.6 | 0.905 ± 0.008 | 0.00 ± 0.00 |

## Statistical comparisons (Welch t on per-seed means)

| Comparison | Metric | Test: mean A − mean B | t | Stress: mean A − mean B | t |
|---|---|---|---|---|---|
| TD3 − DDPG | iae | +0.0310 | +0.44 | +0.0563 | +0.78 |
| TD3 − DDPG | ise | +0.0065 | +0.35 | +0.0061 | +0.31 |
| TD3 − DDPG | settle_s | +0.1680 | +1.78 | +0.0846 | +0.54 |
| TD3 − DDPG | reserve_pu | -0.0087 | -0.37 | -0.0089 | -0.40 |
| TD3 − DDPG | reward | -65.8204 | -1.71 | -52.5294 | -1.62 |

## RL vs best non-learning controller (seeds that beat it)

* DDPG vs Fixed tuned — iae (test): 3/5 seeds better (RL mean 1.857, baseline 1.857)
* DDPG vs Fixed tuned — iae (stress): 3/5 seeds better (RL mean 2.248, baseline 2.233)
* DDPG vs Fixed tuned — reward (test): 4/5 seeds better (RL mean 435, baseline 399.2)
* DDPG vs Fixed tuned — reward (stress): 5/5 seeds better (RL mean 258.7, baseline 213.9)
* DDPG vs Rule-based adaptive — iae (test): 3/5 seeds better (RL mean 1.857, baseline 1.859)
* DDPG vs Rule-based adaptive — iae (stress): 2/5 seeds better (RL mean 2.248, baseline 2.191)
* DDPG vs Rule-based adaptive — reward (test): 5/5 seeds better (RL mean 435, baseline 394.2)
* DDPG vs Rule-based adaptive — reward (stress): 5/5 seeds better (RL mean 258.7, baseline 218.3)
* TD3 vs Fixed tuned — iae (test): 1/5 seeds better (RL mean 1.888, baseline 1.857)
* TD3 vs Fixed tuned — iae (stress): 0/5 seeds better (RL mean 2.304, baseline 2.233)
* TD3 vs Fixed tuned — reward (test): 3/5 seeds better (RL mean 369.1, baseline 399.2)
* TD3 vs Fixed tuned — reward (stress): 3/5 seeds better (RL mean 206.1, baseline 213.9)
* TD3 vs Rule-based adaptive — iae (test): 1/5 seeds better (RL mean 1.888, baseline 1.859)
* TD3 vs Rule-based adaptive — iae (stress): 0/5 seeds better (RL mean 2.304, baseline 2.191)
* TD3 vs Rule-based adaptive — reward (test): 3/5 seeds better (RL mean 369.1, baseline 394.2)
* TD3 vs Rule-based adaptive — reward (stress): 3/5 seeds better (RL mean 206.1, baseline 218.3)

## Critic calibration at the selected checkpoint (validation states)

Bias = critic estimate − Monte-Carlo discounted return actually obtained.

| Algorithm | Seed | Q1 − G | min(Q1,Q2) − G |
|---|---|---|---|
| DDPG | 0 | -14.71 | -14.71 |
| DDPG | 1 | +29.71 | +29.71 |
| DDPG | 2 | +31.54 | +31.54 |
| DDPG | 3 | -15.49 | -15.49 |
| DDPG | 4 | +8.77 | +8.77 |
| TD3 | 0 | -22.19 | -23.17 |
| TD3 | 1 | -23.90 | -26.58 |
| TD3 | 2 | -44.29 | -46.03 |
| TD3 | 3 | -31.94 | -34.80 |
| TD3 | 4 | -32.29 | -34.94 |
