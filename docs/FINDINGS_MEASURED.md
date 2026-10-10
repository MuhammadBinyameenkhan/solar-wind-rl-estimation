# Findings with measured weather (Cabauw 1 Hz irradiance + FINO1 80 m wind)

Full tables: [`results_measured/RESULTS.md`](../results_measured/RESULTS.md);
figures in `results_measured/figures/`. Protocol: 10 seeds × {DDPG, TD3} ×
1000 episodes, baselines tuned on the validation episodes with the agents'
reward, chronological train / validation / test split of the records.
Per-seed results are compared with the deterministic baselines by a
one-sample t-test (df = 9, |t| > 2.262 ⇒ p < 0.05) and between algorithms by
Welch's t.

## Data: what is measured and what is assumed

| | Source | Record | Validity |
|---|---|---|---|
| Irradiance | BSRN Cabauw 1 Hz GHI (Knap & Mol 2022, Zenodo 7093164) | 31 Mar, 17 Jul, 22 Jul 2015 (259 065 s) | no missing or negative values; night ≤ 1.7 W/m²; timestamps match sunrise and solar noon (UTC); max clearness index 1.14 (cloud enhancement); no stuck sensor |
| Wind | FINO1 sonic anemometer, 80 m, 10 Hz → 1 s means | 21–23 Jan 2007 (255 599 s) | one 1 h gap (skipped); 0.1–25.4 m/s; median turbulence intensity 8 %; 13 isolated single-sample dropouts (0.005 %) removed by despiking |

* **Levels are the recorded ones.** Nothing is rescaled
  (`rescale_to_site: false`), and no reanalysis or invented level enters the
  measured study. The earlier measured runs rescaled the windows to
  708 W/m² and 5–7 m/s, which were not measurements. Those runs are
  withdrawn; they remain in the git history only.
* **One assumption:** the irradiance file has no temperature, so PV cell
  temperature uses a constant 25 °C ambient (`ambient_temp_c`). Replace it
  with KNMI CESAR air temperature for the same days if available.
* **Microgrid ratings** (500 kW PV, 500 kW wind, 1800 kW load, 2500 kVA
  BESS) are design parameters, not data.
* **Load contingencies** are designed grid-code tests, not data.
* **Distribution shift (report it).** The chronological split puts the windy
  first day in training: mean wind 13.1 m/s in training, 6.6 m/s in
  validation and 5.0 m/s in test. The test irradiance segment is the
  afternoon of 22 July 2015. The agents are therefore tested on calmer
  weather than they trained on. This is the real situation the split
  produces, and the paper should say so.

Test windows at recorded levels:
* clear: about 694 W/m²;
* cloud: 744 → 133 W/m² within about 6 s;
* wind lull: 8.9 → 5.3 m/s;
* other scenarios: wind 3.0–4.1 m/s.

## Tuned baselines

* **Fixed tuned:** J = 0, D = 35, Kq = 20. Its declared requirement
  (0.35 pu) often exceeds the available headroom, so it is **derated in
  40.8 % of test steps** and 20.1 % of stress steps. This includes 100 % of
  the night test window, where the BESS also carries the load, and 71 % of
  the cloud window.
* **Rule-based adaptive:** J0 = 0, kJ = 0, D0 = 20, kD = 80, Kq = 20. Tuning
  switched off its inertia term, so it is a frequency-proportional damping
  rule.

Both tuned baselines chose J = 0. On this system, damping buys more
regulation per unit of headroom than inertia does (0.08 pu per unit J vs
0.01 pu per unit D).

## Results (mean ± 95 % CI over 10 seeds)

### Held-out stress test (50 randomised episodes on unseen weather)

| Controller | IAE (Hz·s) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Reserve (pu) | Derated (%) |
|---|---|---|---|---|---|---|
| Fixed high (paper, J=4, D=30) | 3.176 | 49.703 | 0.610 | 0.248 | 0.424 | 99.6 |
| Fixed tuned | 2.180 | 49.766 | 0.494 | **0.081** | 0.342 | 20.1 |
| Rule-based adaptive | 2.278 | 49.757 | 0.521 | 0.128 | 0.256 | **7.6** |
| DDPG | 2.222 ± 0.076 | 49.772 ± 0.019 | 0.492 ± 0.020 | 0.315 ± 0.101 | 0.258 ± 0.015 | 13.0 ± 2.0 |
| TD3 | **2.161 ± 0.054** | **49.786 ± 0.010** | **0.475 ± 0.015** | 0.350 ± 0.093 | **0.250 ± 0.013** | 11.8 ± 4.5 |

### Test scenarios (five deterministic measured windows)

| Controller | IAE (Hz·s) | Nadir (Hz) | RoCoF (Hz/s) | Settling (s) | Reserve (pu) | Derated (%) |
|---|---|---|---|---|---|---|
| Fixed tuned | **1.734** | 49.800 | 0.416 | **0.056** | 0.333 | 40.8 |
| Rule-based adaptive | 1.857 | 49.786 | 0.440 | 0.088 | 0.244 | 10.2 |
| DDPG | 1.884 ± 0.067 | 49.802 ± 0.012 | 0.428 ± 0.019 | 0.275 ± 0.127 | 0.236 ± 0.020 | 14.1 ± 3.3 |
| TD3 | 1.857 ± 0.054 | **49.809 ± 0.009** | **0.414 ± 0.016** | 0.310 ± 0.125 | **0.228 ± 0.018** | **9.8 ± 3.7** |

### What the data support

**Against the tuned constant controller (J = 0, D = 35):**
* **Headroom:** both agents reserve 24–32 % less headroom on every seed:
  * test: −29.2 % (DDPG, t = −10.8) and −31.7 % (TD3, t = −13.6);
  * stress: −24.5 % (t = −13.0) and −26.7 % (t = −16.5).
* **Derating:** both agents are derated far less often: 10–14 % of test
  steps vs 41 %.
* **Regulation on the five test windows:** the constant controller is
  better. IAE is **+8.6 % for DDPG and +7.1 % for TD3** (t = +5.0 and +5.2,
  1/10 seeds better).
* **Regulation on the 50 stress episodes:** no significant IAE difference
  (DDPG +1.9 %, t = +1.2; TD3 −0.9 %, t = −0.8). TD3 has lower ISE (−5.8 %,
  t = −3.3), a higher nadir (t = +4.4) and lower RoCoF (−3.9 %, t = −3.0).
* **Settling:** the constant controller settles faster (0.06–0.08 s vs
  0.28–0.35 s).

**Against the rule-based adaptive controller:**
* **Headroom:** no significant saving. The differences are −3.3 % / −6.7 %
  on test (TD3 t = −2.09, not significant) and +0.9 % / −2.1 % on stress.
* **Regulation:**
  * TD3 is better on the stress set: IAE −5.2 % (t = −4.9, 9/10 seeds),
    ISE −8.7 %, RoCoF −8.9 % (t = −7.2) and a higher nadir (t = +6.7).
  * DDPG is not significantly different on IAE (−2.5 %, t = −1.7), but its
    RoCoF is lower (−5.7 %, t = −3.4).
  * On the five test windows both agents equal the rule on IAE (+1.5 % and
    0.0 %). TD3 has a lower RoCoF (−5.9 %, t = −3.7) and a higher nadir.
* **Reward:** TD3 beats the rule on stress (+32 %, t = 4.7, 10/10 seeds);
  DDPG does not (t = −0.2).

**Honest headline.** On held-out measured weather, the learned controllers
reach the regulation of the best constant-gain VSG while committing about
25 % less converter headroom and being derated far less often. On the five
test windows, however, the constant controller keeps a 7–9 % IAE advantage.
The rule-based adaptive VSG reaches a similar headroom level, so against it
the agents' gain is regulation (TD3 only), not reserve. The earlier claim of
"10–13 % less headroom than the rule-based controller" does **not** hold on
unscaled data.

### TD3 vs DDPG

No metric differs significantly (Welch |t| ≤ 1.89 on test and stress).
TD3 is better than DDPG in every comparison against the baselines above,
but the direct test does not separate them.

### Training behaviour and critic bias

* **Early best checkpoints.** The best validation checkpoint comes early:
  * DDPG: episodes 30–80 on 9 of 10 seeds (one at 880), median 50;
  * TD3: episodes 60–230, median 125.

  Validation return then declines (Fig. 6b) while training return keeps
  rising. This is consistent with the distribution shift: training wind is
  mostly above rated, validation and test wind is below it. Validation-based
  checkpoint selection is what keeps the reported policies good, and the
  paper should say that longer training did not help.
* **Critic bias (Q − G):**

  | | Selected checkpoint | Episode 1000 |
  |---|---|---|
  | DDPG | −9 to +35 | +37 to +299 (all positive) |
  | TD3 | −26 to −56 (all negative) | −80 to −168 (all negative) |

  DDPG overestimates and TD3 underestimates, as expected from their
  critics. The bias grows with training on both.

## Comparison with the withdrawn (rescaled) measured runs

| Claim | Rescaled (withdrawn) | Recorded levels (this study) |
|---|---|---|
| Reserve vs tuned constant | −24 to −32 % | −24 to −32 % (holds) |
| Reserve vs rule-based | −10 to −16 % | not significant (does not hold) |
| IAE vs tuned constant, stress | DDPG −5.6 % (significant) | DDPG +1.9 %, TD3 −0.9 % (both not significant) |
| IAE vs tuned constant, test | +1 to +3 % (not significant) | +7 to +9 % (significant, constant is better) |
| IAE vs rule-based, stress | not significant | TD3 −5.2 % (significant) |
| TD3 vs DDPG | not significant | not significant |

## Suggested abstract claims

> On 50 held-out episodes of measured weather, both learned controllers
> matched the frequency regulation of the best constant-gain VSG (IAE
> within ±2 %, not significant) while committing 25–27 % less converter
> headroom and being derated less often, on all ten seeds. TD3 also reduced
> IAE by 5 % and RoCoF by 9 % relative to a tuned rule-based adaptive VSG.
> On five deterministic test windows, the constant-gain VSG retained a 7–9 %
> IAE advantage. DDPG and TD3 did not differ significantly.
