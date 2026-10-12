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
| DDPG-VSG (n=10) | 1.909 ± 0.075 | 0.284 ± 0.019 | 26.50 ± 1.39 | 49.802 ± 0.011 | 0.427 ± 0.016 | 0.268 ± 0.110 | 25.8 ± 3.0 | 0.243 ± 0.015 | 9.9 ± 3.5 | 0.747 ± 0.009 | 0.00 ± 0.00 |
| TD3-VSG (n=10) | 1.842 ± 0.073 | 0.272 ± 0.019 | 25.32 ± 1.21 | 49.806 ± 0.009 | 0.424 ± 0.027 | 0.177 ± 0.127 | 24.5 ± 2.8 | 0.253 ± 0.019 | 14.6 ± 6.2 | 0.755 ± 0.009 | 0.00 ± 0.00 |
| DDPG-VSG (final ckpt) (n=10) | 2.571 ± 0.754 | 0.614 ± 0.443 | 36.51 ± 11.60 | 49.727 ± 0.078 | 0.545 ± 0.086 | 0.541 ± 0.264 | 25.5 ± 5.5 | 0.271 ± 0.044 | 37.2 ± 18.2 | 0.677 ± 0.070 | 0.00 ± 0.00 |
| TD3-VSG (final ckpt) (n=10) | 2.254 ± 0.273 | 0.418 ± 0.091 | 32.28 ± 5.55 | 49.770 ± 0.025 | 0.507 ± 0.056 | 0.369 ± 0.230 | 25.3 ± 6.3 | 0.294 ± 0.031 | 38.1 ± 16.7 | 0.713 ± 0.027 | 0.00 ± 0.00 |

## Held-out stress test

| Controller | IAE (Hz·s) | ISE (Hz²·s) | ITAE (Hz·s²) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Overshoot (%) | Reserve (pu) | Derated (%) | E_vsg (kWh) | Trip rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| No VSG | 12.346 | 13.426 | 181.73 | 48.043 | 4.011 | 3.080 | 50.8 | 0.000 | 0.0 | 0.000 | 0.02 |
| Fixed low | 4.748 | 1.719 | 65.75 | 49.487 | 1.030 | 0.751 | 21.3 | 0.180 | 0.0 | 0.673 | 0.00 |
| Fixed high | 3.176 | 0.814 | 43.46 | 49.703 | 0.610 | 0.248 | 11.8 | 0.424 | 99.6 | 0.868 | 0.00 |
| Fixed max | 4.032 | 1.311 | 55.35 | 49.622 | 0.672 | 0.398 | 10.3 | 0.421 | 100.0 | 0.776 | 0.00 |
| Fixed tuned | 2.180 | 0.365 | 29.84 | 49.766 | 0.494 | 0.081 | 21.6 | 0.342 | 20.1 | 1.023 | 0.00 |
| Rule-based adaptive | 2.278 | 0.377 | 31.85 | 49.757 | 0.521 | 0.128 | 24.2 | 0.256 | 7.6 | 1.000 | 0.00 |
| DDPG-VSG (n=10) | 2.204 ± 0.061 | 0.357 ± 0.015 | 30.76 ± 1.26 | 49.781 ± 0.007 | 0.486 ± 0.018 | 0.288 ± 0.082 | 18.5 ± 2.2 | 0.270 ± 0.014 | 12.2 ± 2.9 | 1.000 ± 0.008 | 0.00 ± 0.00 |
| TD3-VSG (n=10) | 2.148 ± 0.067 | 0.349 ± 0.020 | 29.83 ± 1.16 | 49.787 ± 0.007 | 0.473 ± 0.013 | 0.235 ± 0.133 | 18.5 ± 1.9 | 0.275 ± 0.018 | 14.5 ± 4.1 | 1.007 ± 0.008 | 0.00 ± 0.00 |
| DDPG-VSG (final ckpt) (n=10) | 2.982 ± 0.854 | 0.767 ± 0.506 | 42.81 ± 13.90 | 49.700 ± 0.071 | 0.613 ± 0.084 | 0.500 ± 0.283 | 18.1 ± 4.6 | 0.306 ± 0.045 | 39.1 ± 16.9 | 0.914 ± 0.084 | 0.00 ± 0.00 |
| TD3-VSG (final ckpt) (n=10) | 2.632 ± 0.333 | 0.551 ± 0.128 | 38.31 ± 7.60 | 49.739 ± 0.020 | 0.583 ± 0.044 | 0.386 ± 0.264 | 18.9 ± 3.9 | 0.324 ± 0.032 | 32.7 ± 12.5 | 0.957 ± 0.033 | 0.00 ± 0.00 |

## Statistical comparisons (Welch t on per-seed means)

| Comparison | Metric | Test: mean A − mean B | t | Stress: mean A − mean B | t |
|---|---|---|---|---|---|
| TD3 − DDPG | iae | -0.0668 | -1.44 | -0.0562 | -1.41 |
| TD3 − DDPG | ise | -0.0128 | -1.08 | -0.0087 | -0.79 |
| TD3 − DDPG | settle_s | -0.0916 | -1.23 | -0.0529 | -0.76 |
| TD3 − DDPG | reserve_pu | +0.0101 | +0.93 | +0.0054 | +0.53 |
| TD3 − DDPG | reward | -0.3480 | -0.01 | +14.1705 | +0.51 |

## RL vs best non-learning controller (seeds that beat it)

* DDPG vs Fixed tuned — iae (test): 0/10 seeds better (RL mean 1.909, baseline 1.734)
* DDPG vs Fixed tuned — iae (stress): 4/10 seeds better (RL mean 2.204, baseline 2.18)
* DDPG vs Fixed tuned — reward (test): 10/10 seeds better (RL mean 382.3, baseline 267.5)
* DDPG vs Fixed tuned — reward (stress): 8/10 seeds better (RL mean 211.8, baseline 166)
* DDPG vs Rule-based adaptive — iae (test): 3/10 seeds better (RL mean 1.909, baseline 1.857)
* DDPG vs Rule-based adaptive — iae (stress): 8/10 seeds better (RL mean 2.204, baseline 2.278)
* DDPG vs Rule-based adaptive — reward (test): 2/10 seeds better (RL mean 382.3, baseline 438.1)
* DDPG vs Rule-based adaptive — reward (stress): 4/10 seeds better (RL mean 211.8, baseline 247.1)
* TD3 vs Fixed tuned — iae (test): 1/10 seeds better (RL mean 1.842, baseline 1.734)
* TD3 vs Fixed tuned — iae (stress): 6/10 seeds better (RL mean 2.148, baseline 2.18)
* TD3 vs Fixed tuned — reward (test): 9/10 seeds better (RL mean 382, baseline 267.5)
* TD3 vs Fixed tuned — reward (stress): 9/10 seeds better (RL mean 226, baseline 166)
* TD3 vs Rule-based adaptive — iae (test): 5/10 seeds better (RL mean 1.842, baseline 1.857)
* TD3 vs Rule-based adaptive — iae (stress): 9/10 seeds better (RL mean 2.148, baseline 2.278)
* TD3 vs Rule-based adaptive — reward (test): 2/10 seeds better (RL mean 382, baseline 438.1)
* TD3 vs Rule-based adaptive — reward (stress): 4/10 seeds better (RL mean 226, baseline 247.1)

## DDPG vs TD3 summary (mean ± 95 % CI over seeds)

Each seed is first averaged over the episodes. 'best' = validation-selected checkpoint (deployed); 'final' = the network after the last episode. Critic bias is measured on the validation states, in learner-reward units. t = Welch t, TD3 − DDPG, on the per-seed values.

### Best checkpoint — test scenarios

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 1.909 ± 0.075 | 1.842 ± 0.073 | -1.44 |
| ISE (Hz²·s) | 0.284 ± 0.019 | 0.272 ± 0.019 | -1.08 |
| ITAE (Hz·s²) | 26.50 ± 1.39 | 25.32 ± 1.21 | -1.44 |
| Settling (s) | 0.268 ± 0.110 | 0.177 ± 0.127 | -1.23 |
| Overshoot (%) | 25.8 ± 3.0 | 24.5 ± 2.8 | -0.76 |
| Nadir (Hz) | 49.802 ± 0.011 | 49.806 ± 0.009 | +0.65 |
| Peak RoCoF (Hz/s) | 0.427 ± 0.016 | 0.424 ± 0.027 | -0.23 |
| Reserve (pu) | 0.243 ± 0.015 | 0.253 ± 0.019 | +0.93 |
| At bounds (%) | 54.9 ± 12.8 | 52.6 ± 9.1 | -0.33 |
| J at bound (%) | 50.5 ± 13.8 | 50.2 ± 9.4 | -0.04 |
| D at bound (%) | 5.4 ± 2.6 | 2.7 ± 3.2 | -1.48 |
| Critic bias Q − G | +0.0489 ± 0.0163 | -0.0612 ± 0.0354 | -6.39 |
| min(Q1,Q2) − G | +0.0489 ± 0.0163 | -0.0624 ± 0.0354 | -6.47 |

### Best checkpoint — held-out stress test

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 2.204 ± 0.061 | 2.148 ± 0.067 | -1.41 |
| ISE (Hz²·s) | 0.357 ± 0.015 | 0.349 ± 0.020 | -0.79 |
| ITAE (Hz·s²) | 30.76 ± 1.26 | 29.83 ± 1.16 | -1.23 |
| Settling (s) | 0.288 ± 0.082 | 0.235 ± 0.133 | -0.76 |
| Overshoot (%) | 18.5 ± 2.2 | 18.5 ± 1.9 | -0.05 |
| Nadir (Hz) | 49.781 ± 0.007 | 49.787 ± 0.007 | +1.33 |
| Peak RoCoF (Hz/s) | 0.486 ± 0.018 | 0.473 ± 0.013 | -1.39 |
| Reserve (pu) | 0.270 ± 0.014 | 0.275 ± 0.018 | +0.53 |
| At bounds (%) | 55.5 ± 10.2 | 54.5 ± 8.3 | -0.18 |
| J at bound (%) | 51.5 ± 10.6 | 51.4 ± 8.6 | -0.01 |
| D at bound (%) | 5.1 ± 2.3 | 3.6 ± 3.3 | -0.83 |
| Critic bias Q − G | +0.0489 ± 0.0163 | -0.0612 ± 0.0354 | -6.39 |
| min(Q1,Q2) − G | +0.0489 ± 0.0163 | -0.0624 ± 0.0354 | -6.47 |

### Final checkpoint — test scenarios

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 2.571 ± 0.754 | 2.254 ± 0.273 | -0.90 |
| ISE (Hz²·s) | 0.614 ± 0.443 | 0.418 ± 0.091 | -0.98 |
| ITAE (Hz·s²) | 36.51 ± 11.60 | 32.28 ± 5.55 | -0.74 |
| Settling (s) | 0.541 ± 0.264 | 0.369 ± 0.230 | -1.11 |
| Overshoot (%) | 25.5 ± 5.5 | 25.3 ± 6.3 | -0.05 |
| Nadir (Hz) | 49.727 ± 0.078 | 49.770 ± 0.025 | +1.18 |
| Peak RoCoF (Hz/s) | 0.545 ± 0.086 | 0.507 ± 0.056 | -0.84 |
| Reserve (pu) | 0.271 ± 0.044 | 0.294 ± 0.031 | +0.94 |
| At bounds (%) | 49.9 ± 15.1 | 51.5 ± 22.1 | +0.13 |
| J at bound (%) | 34.3 ± 17.2 | 40.8 ± 22.1 | +0.52 |
| D at bound (%) | 19.5 ± 14.0 | 14.2 ± 14.3 | -0.60 |
| Critic bias Q − G | +1.7077 ± 1.9362 | -0.1439 ± 0.0324 | -2.16 |
| min(Q1,Q2) − G | +1.7077 ± 1.9362 | -0.1507 ± 0.0340 | -2.17 |

### Final checkpoint — held-out stress test

| Metric | DDPG | TD3 | t (TD3 − DDPG) |
|---|---|---|---|
| IAE (Hz·s) | 2.982 ± 0.854 | 2.632 ± 0.333 | -0.86 |
| ISE (Hz²·s) | 0.767 ± 0.506 | 0.551 ± 0.128 | -0.94 |
| ITAE (Hz·s²) | 42.81 ± 13.90 | 38.31 ± 7.60 | -0.64 |
| Settling (s) | 0.500 ± 0.283 | 0.386 ± 0.264 | -0.66 |
| Overshoot (%) | 18.1 ± 4.6 | 18.9 ± 3.9 | +0.32 |
| Nadir (Hz) | 49.700 ± 0.071 | 49.739 ± 0.020 | +1.22 |
| Peak RoCoF (Hz/s) | 0.613 ± 0.084 | 0.583 ± 0.044 | -0.72 |
| Reserve (pu) | 0.306 ± 0.045 | 0.324 ± 0.032 | +0.75 |
| At bounds (%) | 48.5 ± 15.8 | 48.7 ± 18.3 | +0.02 |
| J at bound (%) | 32.9 ± 17.3 | 38.7 ± 19.0 | +0.51 |
| D at bound (%) | 19.8 ± 14.3 | 12.4 ± 11.8 | -0.90 |
| Critic bias Q − G | +1.7077 ± 1.9362 | -0.1439 ± 0.0324 | -2.16 |
| min(Q1,Q2) − G | +1.7077 ± 1.9362 | -0.1507 ± 0.0340 | -2.17 |

* DDPG best-checkpoint episodes by seed: [450, 140, 60, 310, 140, 330, 60, 200, 190, 70]
* TD3 best-checkpoint episodes by seed: [230, 100, 350, 180, 280, 290, 260, 290, 350, 160]

## Critic calibration and model selection per seed (validation states)

Bias = critic estimate − Monte-Carlo discounted return actually obtained, both in learner-reward units (REWARD_SCALE = 0.001, shifted by −R_ALIVE).

| Algorithm | Seed | Best episode | Q − G (best) | min(Q1,Q2) − G (best) | Q − G (final) | min(Q1,Q2) − G (final) |
|---|---|---|---|---|---|---|
| DDPG | 0 | 450 | +0.0363 | +0.0363 | +0.2743 | +0.2743 |
| DDPG | 1 | 140 | +0.0697 | +0.0697 | +0.2107 | +0.2107 |
| DDPG | 2 | 60 | +0.0367 | +0.0367 | +0.1596 | +0.1596 |
| DDPG | 3 | 310 | +0.0376 | +0.0376 | +3.0667 | +3.0667 |
| DDPG | 4 | 140 | +0.0397 | +0.0397 | +0.1332 | +0.1332 |
| DDPG | 5 | 330 | +0.0378 | +0.0378 | +0.1763 | +0.1763 |
| DDPG | 6 | 60 | +0.0663 | +0.0663 | +0.1338 | +0.1338 |
| DDPG | 7 | 200 | +0.0483 | +0.0483 | +7.8673 | +7.8673 |
| DDPG | 8 | 190 | +0.0192 | +0.0192 | +4.8530 | +4.8530 |
| DDPG | 9 | 70 | +0.0978 | +0.0978 | +0.2019 | +0.2019 |
| TD3 | 0 | 230 | -0.0886 | -0.0910 | -0.1325 | -0.1379 |
| TD3 | 1 | 100 | -0.0471 | -0.0475 | -0.1200 | -0.1252 |
| TD3 | 2 | 350 | -0.0430 | -0.0442 | -0.1574 | -0.1621 |
| TD3 | 3 | 180 | -0.0424 | -0.0432 | -0.2222 | -0.2350 |
| TD3 | 4 | 280 | -0.0641 | -0.0657 | -0.0445 | -0.0491 |
| TD3 | 5 | 290 | -0.0424 | -0.0435 | -0.1487 | -0.1550 |
| TD3 | 6 | 260 | -0.0367 | -0.0378 | -0.1401 | -0.1444 |
| TD3 | 7 | 290 | -0.0131 | -0.0142 | -0.1344 | -0.1381 |
| TD3 | 8 | 350 | -0.0436 | -0.0450 | -0.1630 | -0.1756 |
| TD3 | 9 | 160 | -0.1909 | -0.1915 | -0.1758 | -0.1844 |
