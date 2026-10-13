# Weather-only test and scheduling-loop sensitivity (trained actors, no retraining)

Load contingencies switched off; only measured irradiance and wind disturb the frequency. tau_sch = time constant of the BESS scheduling loop (TAU_AGC, 1 s in all other results). RL: best actors, mean ± 95 % CI over seeds.

## 50 held-out stress windows

| tau_sch (s) | Controller | IAE (Hz·s) | max |Δf| (Hz) | RoCoF (Hz/s) | Reserve (pu) |
|---|---|---|---|---|---|
| 1 | No VSG | 0.400 | 0.063 | 0.075 | 0.000 |
| 1 | Fixed tuned | 0.152 | 0.023 | 0.046 | 0.343 |
| 1 | Rule-based adaptive | 0.163 | 0.024 | 0.039 | 0.205 |
| 1 | DDPG-VSG | 0.185 ± 0.011 | 0.027 ± 0.001 | 0.036 ± 0.002 | 0.202 ± 0.030 |
| 1 | TD3-VSG | 0.176 ± 0.016 | 0.025 ± 0.002 | 0.035 ± 0.002 | 0.208 ± 0.026 |
| 10 | No VSG | 2.016 | 0.161 | 0.099 | 0.000 |
| 10 | Fixed tuned | 0.477 | 0.046 | 0.050 | 0.343 |
| 10 | Rule-based adaptive | 0.604 | 0.052 | 0.045 | 0.217 |
| 10 | DDPG-VSG | 0.798 ± 0.082 | 0.061 ± 0.005 | 0.046 ± 0.003 | 0.206 ± 0.028 |
| 10 | TD3-VSG | 0.729 ± 0.095 | 0.057 ± 0.005 | 0.045 ± 0.004 | 0.218 ± 0.027 |
| 30 | No VSG | 3.146 | 0.196 | 0.103 | 0.000 |
| 30 | Fixed tuned | 0.720 | 0.053 | 0.050 | 0.343 |
| 30 | Rule-based adaptive | 0.882 | 0.061 | 0.046 | 0.224 |
| 30 | DDPG-VSG | 1.190 ± 0.118 | 0.078 ± 0.007 | 0.049 ± 0.003 | 0.209 ± 0.027 |
| 30 | TD3-VSG | 1.082 ± 0.145 | 0.073 ± 0.008 | 0.048 ± 0.005 | 0.225 ± 0.027 |

## Five test windows

| tau_sch (s) | Controller | IAE (Hz·s) | max |Δf| (Hz) | RoCoF (Hz/s) | Reserve (pu) |
|---|---|---|---|---|---|
| 1 | No VSG | 0.354 | 0.069 | 0.077 | 0.000 |
| 1 | Fixed tuned | 0.143 | 0.025 | 0.044 | 0.335 |
| 1 | Rule-based adaptive | 0.151 | 0.026 | 0.037 | 0.205 |
| 1 | DDPG-VSG | 0.158 ± 0.008 | 0.027 ± 0.002 | 0.033 ± 0.003 | 0.197 ± 0.027 |
| 1 | TD3-VSG | 0.152 ± 0.014 | 0.025 ± 0.003 | 0.032 ± 0.001 | 0.209 ± 0.027 |
| 10 | No VSG | 2.345 | 0.179 | 0.106 | 0.000 |
| 10 | Fixed tuned | 0.556 | 0.049 | 0.047 | 0.338 |
| 10 | Rule-based adaptive | 0.690 | 0.055 | 0.044 | 0.219 |
| 10 | DDPG-VSG | 0.874 ± 0.106 | 0.062 ± 0.006 | 0.042 ± 0.004 | 0.200 ± 0.026 |
| 10 | TD3-VSG | 0.808 ± 0.128 | 0.058 ± 0.008 | 0.043 ± 0.007 | 0.220 ± 0.030 |
| 30 | No VSG | 3.912 | 0.211 | 0.109 | 0.000 |
| 30 | Fixed tuned | 0.896 | 0.057 | 0.048 | 0.339 |
| 30 | Rule-based adaptive | 1.063 | 0.063 | 0.045 | 0.229 |
| 30 | DDPG-VSG | 1.389 ± 0.156 | 0.079 ± 0.009 | 0.046 ± 0.005 | 0.205 ± 0.024 |
| 30 | TD3-VSG | 1.280 ± 0.203 | 0.075 ± 0.011 | 0.048 ± 0.010 | 0.228 ± 0.030 |

