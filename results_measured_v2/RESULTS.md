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
| Rule-based adaptive | 1.860 | 0.266 | 25.52 | 49.754 | 0.481 | 0.084 | 25.3 | 0.244 | 10.2 | 0.762 | 0.00 |
| DDPG-VSG (n=10) | 2.320 ± 0.224 | 0.434 ± 0.092 | 33.21 ± 3.75 | 49.742 ± 0.044 | 0.570 ± 0.086 | 0.340 ± 0.140 | 27.6 ± 4.4 | 0.233 ± 0.031 | 14.1 ± 5.9 | 0.702 ± 0.027 | 0.00 ± 0.00 |
| TD3-VSG (n=10) | 1.989 ± 0.094 | 0.303 ± 0.026 | 28.18 ± 1.90 | 49.793 ± 0.014 | 0.455 ± 0.020 | 0.254 ± 0.104 | 26.2 ± 3.1 | 0.233 ± 0.020 | 13.5 ± 4.8 | 0.736 ± 0.011 | 0.00 ± 0.00 |
| DDPG-VSG (final ckpt) (n=10) | 3.038 ± 0.658 | 0.940 ± 0.461 | 41.33 ± 7.71 | 49.613 ± 0.096 | 0.798 ± 0.159 | 0.353 ± 0.176 | 25.2 ± 8.3 | 0.296 ± 0.043 | 57.5 ± 13.9 | 0.610 ± 0.078 | 0.00 ± 0.00 |
| TD3-VSG (final ckpt) (n=10) | 2.689 ± 0.413 | 0.589 ± 0.174 | 38.98 ± 6.81 | 49.734 ± 0.043 | 0.548 ± 0.047 | 0.490 ± 0.256 | 18.6 ± 4.1 | 0.314 ± 0.029 | 60.4 ± 13.9 | 0.663 ± 0.043 | 0.00 ± 0.00 |

## Held-out stress test

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 12.346 | 13.426 | 181.73 | 48.043 | 4.011 | 3.080 | 50.8 | 0.000 | 0.0 | 0.000 | 0.02 |
| Fixed low | 4.748 | 1.719 | 65.75 | 49.487 | 1.030 | 0.751 | 21.3 | 0.180 | 0.0 | 0.673 | 0.00 |
| Fixed high | 3.176 | 0.814 | 43.46 | 49.703 | 0.610 | 0.248 | 11.8 | 0.424 | 99.6 | 0.868 | 0.00 |
| Fixed max | 4.032 | 1.311 | 55.35 | 49.622 | 0.672 | 0.398 | 10.3 | 0.421 | 100.0 | 0.776 | 0.00 |
| Fixed tuned | 2.180 | 0.365 | 29.84 | 49.766 | 0.494 | 0.081 | 21.6 | 0.342 | 20.1 | 1.023 | 0.00 |
| Rule-based adaptive | 2.282 | 0.379 | 31.88 | 49.716 | 0.581 | 0.117 | 19.2 | 0.256 | 7.6 | 0.999 | 0.00 |
| DDPG-VSG (n=10) | 2.523 ± 0.170 | 0.483 ± 0.069 | 36.16 ± 3.18 | 49.723 ± 0.040 | 0.621 ± 0.072 | 0.289 ± 0.093 | 20.9 ± 2.7 | 0.268 ± 0.024 | 16.6 ± 5.2 | 0.965 ± 0.021 | 0.00 ± 0.00 |
| TD3-VSG (n=10) | 2.261 ± 0.080 | 0.374 ± 0.020 | 31.96 ± 1.73 | 49.774 ± 0.010 | 0.512 ± 0.017 | 0.205 ± 0.078 | 21.2 ± 2.3 | 0.270 ± 0.018 | 14.6 ± 4.0 | 0.993 ± 0.010 | 0.00 ± 0.00 |
| DDPG-VSG (final ckpt) (n=10) | 3.842 ± 0.886 | 1.445 ± 0.765 | 53.07 ± 10.47 | 49.560 ± 0.115 | 0.882 ± 0.198 | 0.405 ± 0.158 | 18.6 ± 6.0 | 0.333 ± 0.044 | 58.1 ± 12.7 | 0.804 ± 0.106 | 0.00 ± 0.00 |
| TD3-VSG (final ckpt) (n=10) | 3.068 ± 0.446 | 0.772 ± 0.274 | 44.70 ± 6.60 | 49.705 ± 0.056 | 0.624 ± 0.083 | 0.403 ± 0.204 | 13.9 ± 2.5 | 0.342 ± 0.025 | 54.7 ± 11.4 | 0.904 ± 0.048 | 0.00 ± 0.00 |

## Statistical comparisons (Welch t on per-seed means)

| Comparison | Metric | Test: mean A − mean B | t | Stress: mean A − mean B | t |
|---|---|---|---|---|---|
| TD3 − DDPG | iae | -0.3315 | -3.08 | -0.2618 | -3.15 |
| TD3 − DDPG | ise | -0.1311 | -3.10 | -0.1090 | -3.45 |
| TD3 − DDPG | settle_s | -0.0860 | -1.12 | -0.0837 | -1.56 |
| TD3 − DDPG | reserve_pu | +0.0001 | +0.01 | +0.0019 | +0.15 |
| TD3 − DDPG | reward | +258.8509 | +2.71 | +268.4691 | +3.40 |

## RL vs best non-learning controller (seeds that beat it)

* DDPG vs Fixed tuned — iae (test): 0/10 seeds better (RL mean 2.32, baseline 1.734)
* DDPG vs Fixed tuned — iae (stress): 1/10 seeds better (RL mean 2.523, baseline 2.18)
* DDPG vs Fixed tuned — reward (test): 2/10 seeds better (RL mean 52.52, baseline 267.5)
* DDPG vs Fixed tuned — reward (stress): 0/10 seeds better (RL mean -132.6, baseline 166)
* DDPG vs Rule-based adaptive — iae (test): 0/10 seeds better (RL mean 2.32, baseline 1.86)
* DDPG vs Rule-based adaptive — iae (stress): 2/10 seeds better (RL mean 2.523, baseline 2.282)
* DDPG vs Rule-based adaptive — reward (test): 0/10 seeds better (RL mean 52.52, baseline 433.8)
* DDPG vs Rule-based adaptive — reward (stress): 0/10 seeds better (RL mean -132.6, baseline 240.7)
* TD3 vs Fixed tuned — iae (test): 0/10 seeds better (RL mean 1.989, baseline 1.734)
* TD3 vs Fixed tuned — iae (stress): 4/10 seeds better (RL mean 2.261, baseline 2.18)
* TD3 vs Fixed tuned — reward (test): 9/10 seeds better (RL mean 311.4, baseline 267.5)
* TD3 vs Fixed tuned — reward (stress): 3/10 seeds better (RL mean 135.8, baseline 166)
* TD3 vs Rule-based adaptive — iae (test): 2/10 seeds better (RL mean 1.989, baseline 1.86)
* TD3 vs Rule-based adaptive — iae (stress): 6/10 seeds better (RL mean 2.261, baseline 2.282)
* TD3 vs Rule-based adaptive — reward (test): 2/10 seeds better (RL mean 311.4, baseline 433.8)
* TD3 vs Rule-based adaptive — reward (stress): 0/10 seeds better (RL mean 135.8, baseline 240.7)

## DDPG vs TD3 summary (mean ± 95 % CI over seeds)

Each seed is first averaged over the episodes. 'best' = validation-selected checkpoint (deployed); 'final' = the network after the last episode. Critic bias is measured on the validation states, in learner-reward units. t = Welch t, TD3 − DDPG, on the per-seed values.

### Best checkpoint — test scenarios

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 2.320 ± 0.224 | 1.989 ± 0.094 | -3.08 |
| ISE (Hz²·s) | 0.434 ± 0.092 | 0.303 ± 0.026 | -3.10 |
| ITAE (Hz·s²) | 33.21 ± 3.75 | 28.18 ± 1.90 | -2.71 |
| Settling (s) | 0.340 ± 0.140 | 0.254 ± 0.104 | -1.12 |
| Overshoot (%) | 27.6 ± 4.4 | 26.2 ± 3.1 | -0.61 |
| Nadir (Hz) | 49.742 ± 0.044 | 49.793 ± 0.014 | +2.52 |
| Peak RoCoF (Hz/s) | 0.570 ± 0.086 | 0.455 ± 0.020 | -2.96 |
| Reserve (pu) | 0.233 ± 0.031 | 0.233 ± 0.020 | +0.01 |
| At bounds (%) | 64.2 ± 16.6 | 38.4 ± 10.7 | -2.95 |
| J at bound (%) | 59.4 ± 20.4 | 33.7 ± 10.3 | -2.54 |
| D at bound (%) | 7.1 ± 5.3 | 7.7 ± 4.7 | +0.19 |
| Critic bias Q − G | +0.1164 ± 0.0632 | -0.0586 ± 0.0109 | -6.17 |
| min(Q1,Q2) − G | +0.1164 ± 0.0632 | -0.0607 ± 0.0107 | -6.25 |

### Best checkpoint — held-out stress test

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 2.523 ± 0.170 | 2.261 ± 0.080 | -3.15 |
| ISE (Hz²·s) | 0.483 ± 0.069 | 0.374 ± 0.020 | -3.45 |
| ITAE (Hz·s²) | 36.16 ± 3.18 | 31.96 ± 1.73 | -2.62 |
| Settling (s) | 0.289 ± 0.093 | 0.205 ± 0.078 | -1.56 |
| Overshoot (%) | 20.9 ± 2.7 | 21.2 ± 2.3 | +0.18 |
| Nadir (Hz) | 49.723 ± 0.040 | 49.774 ± 0.010 | +2.83 |
| Peak RoCoF (Hz/s) | 0.621 ± 0.072 | 0.512 ± 0.017 | -3.31 |
| Reserve (pu) | 0.268 ± 0.024 | 0.270 ± 0.018 | +0.15 |
| At bounds (%) | 65.3 ± 14.2 | 44.5 ± 10.3 | -2.69 |
| J at bound (%) | 61.6 ± 15.8 | 41.3 ± 9.6 | -2.48 |
| D at bound (%) | 5.4 ± 3.7 | 5.4 ± 4.4 | +0.03 |
| Critic bias Q − G | +0.1164 ± 0.0632 | -0.0586 ± 0.0109 | -6.17 |
| min(Q1,Q2) − G | +0.1164 ± 0.0632 | -0.0607 ± 0.0107 | -6.25 |

### Final checkpoint — test scenarios

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 3.038 ± 0.658 | 2.689 ± 0.413 | -1.02 |
| ISE (Hz²·s) | 0.940 ± 0.461 | 0.589 ± 0.174 | -1.61 |
| ITAE (Hz·s²) | 41.33 ± 7.71 | 38.98 ± 6.81 | -0.52 |
| Settling (s) | 0.353 ± 0.176 | 0.490 ± 0.256 | +1.00 |
| Overshoot (%) | 25.2 ± 8.3 | 18.6 ± 4.1 | -1.61 |
| Nadir (Hz) | 49.613 ± 0.096 | 49.734 ± 0.043 | +2.62 |
| Peak RoCoF (Hz/s) | 0.798 ± 0.159 | 0.548 ± 0.047 | -3.41 |
| Reserve (pu) | 0.296 ± 0.043 | 0.314 ± 0.029 | +0.78 |
| At bounds (%) | 60.6 ± 15.6 | 40.0 ± 16.9 | -2.02 |
| J at bound (%) | 46.7 ± 17.7 | 25.1 ± 16.6 | -2.01 |
| D at bound (%) | 28.3 ± 13.3 | 20.7 ± 12.7 | -0.93 |
| Critic bias Q − G | +79.3259 ± 88.7848 | -0.1633 ± 0.0515 | -2.03 |
| min(Q1,Q2) − G | +79.3259 ± 88.7848 | -0.1809 ± 0.0511 | -2.03 |

### Final checkpoint — held-out stress test

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 3.842 ± 0.886 | 3.068 ± 0.446 | -1.76 |
| ISE (Hz²·s) | 1.445 ± 0.765 | 0.772 ± 0.274 | -1.87 |
| ITAE (Hz·s²) | 53.07 ± 10.47 | 44.70 ± 6.60 | -1.53 |
| Settling (s) | 0.405 ± 0.158 | 0.403 ± 0.204 | -0.02 |
| Overshoot (%) | 18.6 ± 6.0 | 13.9 ± 2.5 | -1.66 |
| Nadir (Hz) | 49.560 ± 0.115 | 49.705 ± 0.056 | +2.56 |
| Peak RoCoF (Hz/s) | 0.882 ± 0.198 | 0.624 ± 0.083 | -2.72 |
| Reserve (pu) | 0.333 ± 0.044 | 0.342 ± 0.025 | +0.41 |
| At bounds (%) | 59.4 ± 14.0 | 37.7 ± 16.0 | -2.31 |
| J at bound (%) | 43.5 ± 15.2 | 25.9 ± 15.9 | -1.81 |
| D at bound (%) | 30.8 ± 13.0 | 16.4 ± 9.6 | -2.02 |
| Critic bias Q − G | +79.3259 ± 88.7848 | -0.1633 ± 0.0515 | -2.03 |
| min(Q1,Q2) − G | +79.3259 ± 88.7848 | -0.1809 ± 0.0511 | -2.03 |

* DDPG best-checkpoint episodes by seed: [150, 50, 170, 300, 100, 80, 100, 90, 100, 90]
* TD3 best-checkpoint episodes by seed: [360, 140, 160, 260, 390, 400, 200, 330, 260, 330]

## Critic calibration and model selection per seed (validation states)

Bias = critic estimate − Monte-Carlo discounted return actually obtained, both in learner-reward units (REWARD_SCALE = 0.001, shifted by −R_ALIVE).

| Algorithm | Seed | Best episode | Q − G (best) | min(Q1,Q2) − G (best) | Q − G (final) | min(Q1,Q2) − G (final) |
|---|---|---|---|---|---|---|
| DDPG | 0 | 150 | +0.0550 | +0.0550 | +3.9411 | +3.9411 |
| DDPG | 1 | 50 | +0.1267 | +0.1267 | +19.4494 | +19.4494 |
| DDPG | 2 | 170 | +0.1148 | +0.1148 | +9.8257 | +9.8257 |
| DDPG | 3 | 300 | +0.0854 | +0.0854 | +64.5171 | +64.5171 |
| DDPG | 4 | 100 | +0.1326 | +0.1326 | +171.2144 | +171.2144 |
| DDPG | 5 | 80 | +0.0117 | +0.0117 | +11.9284 | +11.9284 |
| DDPG | 6 | 100 | +0.0897 | +0.0897 | +7.5414 | +7.5414 |
| DDPG | 7 | 90 | +0.2025 | +0.2025 | +82.8517 | +82.8517 |
| DDPG | 8 | 100 | +0.0320 | +0.0320 | +21.9020 | +21.9020 |
| DDPG | 9 | 90 | +0.3139 | +0.3139 | +400.0876 | +400.0876 |
| TD3 | 0 | 360 | -0.0693 | -0.0713 | -0.0911 | -0.1188 |
| TD3 | 1 | 140 | -0.0330 | -0.0362 | -0.1493 | -0.1610 |
| TD3 | 2 | 160 | -0.0534 | -0.0543 | -0.1767 | -0.1949 |
| TD3 | 3 | 260 | -0.0728 | -0.0752 | -0.2264 | -0.2397 |
| TD3 | 4 | 390 | -0.0488 | -0.0507 | -0.2671 | -0.2812 |
| TD3 | 5 | 400 | -0.0688 | -0.0706 | -0.1796 | -0.2147 |
| TD3 | 6 | 200 | -0.0562 | -0.0584 | -0.1122 | -0.1272 |
| TD3 | 7 | 330 | -0.0391 | -0.0418 | -0.0306 | -0.0462 |
| TD3 | 8 | 260 | -0.0803 | -0.0826 | -0.1611 | -0.1700 |
| TD3 | 9 | 330 | -0.0639 | -0.0663 | -0.2391 | -0.2557 |
