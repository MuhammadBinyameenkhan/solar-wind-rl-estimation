# Results

Seeds: [0, 1, 2]. Episodes per run: 1000. Weather: measured. Test = five deterministic paper scenarios (seed 70007); stress = 50 randomised held-out episodes. RL values: mean ± 95 % CI over seeds (each seed averaged over the episodes). Baselines are deterministic and tuned on the validation episodes only.

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
| DDPG-VSG (n=3) | 1.873 ± 0.154 | 0.274 ± 0.049 | 25.74 ± 1.38 | 49.807 ± 0.036 | 0.408 ± 0.060 | 0.172 ± 0.215 | 27.3 ± 5.5 | 0.231 ± 0.088 | 7.8 ± 10.7 | 0.751 ± 0.021 | 0.00 ± 0.00 |
| TD3-VSG (n=3) | 1.885 ± 0.309 | 0.284 ± 0.092 | 25.56 ± 2.57 | 49.805 ± 0.047 | 0.444 ± 0.087 | 0.183 ± 0.272 | 28.6 ± 9.1 | 0.248 ± 0.093 | 11.8 ± 14.0 | 0.751 ± 0.045 | 0.00 ± 0.00 |
| DDPG-VSG (final ckpt) (n=3) | 2.562 ± 0.697 | 0.557 ± 0.493 | 35.01 ± 9.57 | 49.695 ± 0.186 | 0.663 ± 0.451 | 0.397 ± 0.525 | 27.0 ± 18.1 | 0.245 ± 0.140 | 26.0 ± 23.6 | 0.661 ± 0.101 | 0.00 ± 0.00 |
| TD3-VSG (final ckpt) (n=3) | 2.430 ± 1.354 | 0.496 ± 0.525 | 37.31 ± 26.20 | 49.775 ± 0.077 | 0.474 ± 0.115 | 0.404 ± 0.640 | 23.8 ± 13.5 | 0.330 ± 0.037 | 52.9 ± 16.1 | 0.695 ± 0.139 | 0.00 ± 0.00 |

## Held-out stress test

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 12.346 | 13.426 | 181.73 | 48.043 | 4.011 | 3.080 | 50.8 | 0.000 | 0.0 | 0.000 | 0.02 |
| Fixed low | 4.748 | 1.719 | 65.75 | 49.487 | 1.030 | 0.751 | 21.3 | 0.180 | 0.0 | 0.673 | 0.00 |
| Fixed high | 3.176 | 0.814 | 43.46 | 49.703 | 0.610 | 0.248 | 11.8 | 0.424 | 99.6 | 0.868 | 0.00 |
| Fixed max | 4.032 | 1.311 | 55.35 | 49.622 | 0.672 | 0.398 | 10.3 | 0.421 | 100.0 | 0.776 | 0.00 |
| Fixed tuned | 2.180 | 0.365 | 29.84 | 49.766 | 0.494 | 0.081 | 21.6 | 0.342 | 20.1 | 1.023 | 0.00 |
| Rule-based adaptive | 2.278 | 0.377 | 31.85 | 49.757 | 0.521 | 0.128 | 24.2 | 0.256 | 7.6 | 1.000 | 0.00 |
| DDPG-VSG (n=3) | 2.216 ± 0.227 | 0.365 ± 0.085 | 30.75 ± 3.35 | 49.779 ± 0.034 | 0.481 ± 0.060 | 0.171 ± 0.056 | 19.7 ± 1.6 | 0.258 ± 0.041 | 10.4 ± 16.0 | 0.998 ± 0.028 | 0.00 ± 0.00 |
| TD3-VSG (n=3) | 2.241 ± 0.386 | 0.380 ± 0.166 | 30.74 ± 3.36 | 49.775 ± 0.066 | 0.499 ± 0.105 | 0.143 ± 0.168 | 20.6 ± 6.4 | 0.272 ± 0.087 | 12.7 ± 3.6 | 0.995 ± 0.049 | 0.00 ± 0.00 |
| DDPG-VSG (final ckpt) (n=3) | 3.075 ± 0.594 | 0.734 ± 0.102 | 43.99 ± 15.82 | 49.665 ± 0.189 | 0.737 ± 0.320 | 0.456 ± 0.594 | 19.7 ± 11.9 | 0.264 ± 0.110 | 23.0 ± 7.6 | 0.887 ± 0.075 | 0.00 ± 0.00 |
| TD3-VSG (final ckpt) (n=3) | 2.836 ± 2.004 | 0.655 ± 0.839 | 41.81 ± 35.48 | 49.733 ± 0.082 | 0.581 ± 0.194 | 0.355 ± 0.760 | 17.6 ± 8.9 | 0.363 ± 0.040 | 48.6 ± 4.7 | 0.934 ± 0.224 | 0.00 ± 0.00 |

## Statistical comparisons (Welch t on per-seed means)

| Comparison | Metric | Test: mean A − mean B | t | Stress: mean A − mean B | t |
|---|---|---|---|---|---|
| TD3 − DDPG | iae | +0.0119 | +0.15 | +0.0255 | +0.24 |
| TD3 − DDPG | ise | +0.0097 | +0.40 | +0.0153 | +0.35 |
| TD3 − DDPG | settle_s | +0.0107 | +0.13 | -0.0276 | -0.67 |
| TD3 − DDPG | reserve_pu | +0.0167 | +0.56 | +0.0139 | +0.62 |
| TD3 − DDPG | reward | -41.8061 | -1.24 | -21.4464 | -0.45 |

## RL vs best non-learning controller (seeds that beat it)

* DDPG vs Fixed tuned — iae (test): 0/3 seeds better (RL mean 1.873, baseline 1.734)
* DDPG vs Fixed tuned — iae (stress): 1/3 seeds better (RL mean 2.216, baseline 2.18)
* DDPG vs Fixed tuned — reward (test): 3/3 seeds better (RL mean 429.3, baseline 267.5)
* DDPG vs Fixed tuned — reward (stress): 3/3 seeds better (RL mean 226.1, baseline 166)
* DDPG vs Rule-based adaptive — iae (test): 1/3 seeds better (RL mean 1.873, baseline 1.857)
* DDPG vs Rule-based adaptive — iae (stress): 3/3 seeds better (RL mean 2.216, baseline 2.278)
* DDPG vs Rule-based adaptive — reward (test): 1/3 seeds better (RL mean 429.3, baseline 438.1)
* DDPG vs Rule-based adaptive — reward (stress): 0/3 seeds better (RL mean 226.1, baseline 247.1)
* TD3 vs Fixed tuned — iae (test): 0/3 seeds better (RL mean 1.885, baseline 1.734)
* TD3 vs Fixed tuned — iae (stress): 2/3 seeds better (RL mean 2.241, baseline 2.18)
* TD3 vs Fixed tuned — reward (test): 3/3 seeds better (RL mean 387.5, baseline 267.5)
* TD3 vs Fixed tuned — reward (stress): 2/3 seeds better (RL mean 204.6, baseline 166)
* TD3 vs Rule-based adaptive — iae (test): 2/3 seeds better (RL mean 1.885, baseline 1.857)
* TD3 vs Rule-based adaptive — iae (stress): 2/3 seeds better (RL mean 2.241, baseline 2.278)
* TD3 vs Rule-based adaptive — reward (test): 1/3 seeds better (RL mean 387.5, baseline 438.1)
* TD3 vs Rule-based adaptive — reward (stress): 1/3 seeds better (RL mean 204.6, baseline 247.1)

## DDPG vs TD3 summary (mean ± 95 % CI over seeds)

Each seed is first averaged over the episodes. 'best' = validation-selected checkpoint (deployed); 'final' = the network after the last episode. Critic bias is measured on the validation states, in learner-reward units. t = Welch t, TD3 − DDPG, on the per-seed values.

### Best checkpoint — test scenarios

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 1.873 ± 0.154 | 1.885 ± 0.309 | +0.15 |
| ISE (Hz²·s) | 0.274 ± 0.049 | 0.284 ± 0.092 | +0.40 |
| ITAE (Hz·s²) | 25.74 ± 1.38 | 25.56 ± 2.57 | -0.27 |
| Settling (s) | 0.172 ± 0.215 | 0.183 ± 0.272 | +0.13 |
| Overshoot (%) | 27.3 ± 5.5 | 28.6 ± 9.1 | +0.52 |
| Nadir (Hz) | 49.807 ± 0.036 | 49.805 ± 0.047 | -0.18 |
| Peak RoCoF (Hz/s) | 0.408 ± 0.060 | 0.444 ± 0.087 | +1.45 |
| Reserve (pu) | 0.231 ± 0.088 | 0.248 ± 0.093 | +0.56 |
| At bounds (%) | 53.1 ± 29.1 | 43.7 ± 53.3 | -0.67 |
| J at bound (%) | 51.4 ± 34.4 | 43.5 ± 53.5 | -0.53 |
| D at bound (%) | 2.7 ± 11.7 | 0.2 ± 0.7 | -0.93 |
| Critic bias Q − G | +0.0426 ± 0.0155 | -0.0538 ± 0.1211 | -3.40 |
| min(Q1,Q2) − G | +0.0426 ± 0.0155 | -0.0549 ± 0.1205 | -3.45 |

### Best checkpoint — held-out stress test

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 2.216 ± 0.227 | 2.241 ± 0.386 | +0.24 |
| ISE (Hz²·s) | 0.365 ± 0.085 | 0.380 ± 0.166 | +0.35 |
| ITAE (Hz·s²) | 30.75 ± 3.35 | 30.74 ± 3.36 | -0.01 |
| Settling (s) | 0.171 ± 0.056 | 0.143 ± 0.168 | -0.67 |
| Overshoot (%) | 19.7 ± 1.6 | 20.6 ± 6.4 | +0.58 |
| Nadir (Hz) | 49.779 ± 0.034 | 49.775 ± 0.066 | -0.25 |
| Peak RoCoF (Hz/s) | 0.481 ± 0.060 | 0.499 ± 0.105 | +0.65 |
| Reserve (pu) | 0.258 ± 0.041 | 0.272 ± 0.087 | +0.62 |
| At bounds (%) | 50.9 ± 26.0 | 39.7 ± 28.6 | -1.24 |
| J at bound (%) | 49.2 ± 27.8 | 37.9 ± 27.9 | -1.24 |
| D at bound (%) | 2.5 ± 3.6 | 1.9 ± 7.7 | -0.29 |
| Critic bias Q − G | +0.0426 ± 0.0155 | -0.0538 ± 0.1211 | -3.40 |
| min(Q1,Q2) − G | +0.0426 ± 0.0155 | -0.0549 ± 0.1205 | -3.45 |

### Final checkpoint — test scenarios

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 2.562 ± 0.697 | 2.430 ± 1.354 | -0.37 |
| ISE (Hz²·s) | 0.557 ± 0.493 | 0.496 ± 0.525 | -0.37 |
| ITAE (Hz·s²) | 35.01 ± 9.57 | 37.31 ± 26.20 | +0.35 |
| Settling (s) | 0.397 ± 0.525 | 0.404 ± 0.640 | +0.03 |
| Overshoot (%) | 27.0 ± 18.1 | 23.8 ± 13.5 | -0.61 |
| Nadir (Hz) | 49.695 ± 0.186 | 49.775 ± 0.077 | +1.69 |
| Peak RoCoF (Hz/s) | 0.663 ± 0.451 | 0.474 ± 0.115 | -1.74 |
| Reserve (pu) | 0.245 ± 0.140 | 0.330 ± 0.037 | +2.53 |
| At bounds (%) | 48.2 ± 59.3 | 44.6 ± 39.4 | -0.22 |
| J at bound (%) | 36.4 ± 34.9 | 29.7 ± 42.2 | -0.53 |
| D at bound (%) | 16.8 ± 41.6 | 14.9 ± 32.7 | -0.15 |
| Critic bias Q − G | +0.3731 ± 0.6023 | -0.1549 ± 0.1352 | -3.68 |
| min(Q1,Q2) − G | +0.3731 ± 0.6023 | -0.1596 ± 0.1371 | -3.71 |

### Final checkpoint — held-out stress test

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 3.075 ± 0.594 | 2.836 ± 2.004 | -0.49 |
| ISE (Hz²·s) | 0.734 ± 0.102 | 0.655 ± 0.839 | -0.40 |
| ITAE (Hz·s²) | 43.99 ± 15.82 | 41.81 ± 35.48 | -0.24 |
| Settling (s) | 0.456 ± 0.594 | 0.355 ± 0.760 | -0.45 |
| Overshoot (%) | 19.7 ± 11.9 | 17.6 ± 8.9 | -0.60 |
| Nadir (Hz) | 49.665 ± 0.189 | 49.733 ± 0.082 | +1.42 |
| Peak RoCoF (Hz/s) | 0.737 ± 0.320 | 0.581 ± 0.194 | -1.79 |
| Reserve (pu) | 0.264 ± 0.110 | 0.363 ± 0.040 | +3.62 |
| At bounds (%) | 45.8 ± 49.0 | 39.6 ± 8.6 | -0.54 |
| J at bound (%) | 33.5 ± 30.7 | 28.7 ± 32.3 | -0.46 |
| D at bound (%) | 17.0 ± 26.9 | 10.9 ± 32.1 | -0.62 |
| Critic bias Q − G | +0.3731 ± 0.6023 | -0.1549 ± 0.1352 | -3.68 |
| min(Q1,Q2) − G | +0.3731 ± 0.6023 | -0.1596 ± 0.1371 | -3.71 |

* DDPG best-checkpoint episodes by seed: [370, 190, 310]
* TD3 best-checkpoint episodes by seed: [170, 160, 200]

## Critic calibration and model selection per seed (validation states)

Bias = critic estimate − Monte-Carlo discounted return actually obtained, both in learner-reward units (REWARD_SCALE = 0.001, shifted by −R_ALIVE).

| Algorithm | Seed | Best episode | Q − G (best) | min(Q1,Q2) − G (best) | Q − G (final) | min(Q1,Q2) − G (final) |
|---|---|---|---|---|---|---|
| DDPG | 0 | 370 | +0.0354 | +0.0354 | +0.3239 | +0.3239 |
| DDPG | 1 | 190 | +0.0453 | +0.0453 | +0.1590 | +0.1590 |
| DDPG | 2 | 310 | +0.0469 | +0.0469 | +0.6363 | +0.6363 |
| TD3 | 0 | 170 | -0.1099 | -0.1108 | -0.1962 | -0.2010 |
| TD3 | 1 | 160 | -0.0220 | -0.0238 | -0.0932 | -0.0969 |
| TD3 | 2 | 200 | -0.0295 | -0.0301 | -0.1752 | -0.1808 |
