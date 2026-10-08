# Findings with measured weather (Cabauw 1 Hz irradiance + FINO1 80 m wind)

Full tables: [`results_measured/RESULTS.md`](../results_measured/RESULTS.md);
figures in `results_measured/figures/`. Same protocol as the synthetic study:
10 seeds × {DDPG, TD3} × 1000 episodes, baselines tuned on validation
episodes, chronological train / validation / test split of the records.

## Data

| | Source | Record | Validity |
|---|---|---|---|
| Irradiance | BSRN Cabauw 1 Hz GHI (Knap & Mol 2022, Zenodo 7093164) | 31 Mar, 17 Jul, 22 Jul 2015 (259 065 s) | no missing or negative values; night ≤ 1.7 W/m²; timestamps match the computed sunrise and solar noon (UTC); max clearness index 1.14 (cloud enhancement, below the 1.4 limit); no stuck sensor |
| Wind | FINO1 sonic anemometer, 80 m, 10 Hz → 1 s means | 21–23 Jan 2007 (255 599 s) | one 1 h gap (skipped); 0.1–25.4 m/s; median turbulence intensity 8 % (typical offshore); 13 isolated single-sample dropouts (0.005 %) removed by despiking |

Windows keep their measured relative variability and are rescaled to the
Nakhon Ratchasima levels (`rescale_to_site: true`).

## Results (mean ± 95 % CI over 10 seeds)

The study was first run with 5 seeds and then extended to 10. The number 10
was fixed before the extra seeds were trained, and the 10-seed results are
reported as they came out. **The 5-seed headline did not survive** (see the
last section).

### Held-out stress test (50 randomised episodes on unseen weather)

| Controller | IAE (Hz·s) | Nadir (Hz) | RoCoF (Hz/s) | Reserve (pu) |
|---|---|---|---|---|
| Fixed high (paper) | 3.321 | 49.688 | 0.648 | 0.394 (100 % derated) |
| Fixed tuned | 2.392 | 49.738 | 0.546 | 0.299 |
| Rule-based adaptive | 2.280 | 49.757 | 0.525 | 0.255 |
| **DDPG** | **2.258 ± 0.058** | 49.780 ± 0.006 | 0.495 ± 0.010 | 0.228 ± 0.013 |
| TD3 | 2.332 ± 0.102 | 49.769 ± 0.010 | 0.505 ± 0.022 | **0.221 ± 0.009** |

What holds on every seed:
* **Reserve:** both agents commit **24–26 % less headroom** than the tuned
  constant controller (t = −12.4 and −20.1, 10/10 seeds) and **10–13 % less**
  than the rule-based controller (t = −4.7 and −8.8).
* **Full objective (reward):** both agents beat both baselines (t ≥ 2.97).

Regulation (IAE):
* DDPG: **−5.6 % vs the tuned constant controller, significant** (t = −5.20,
  df = 9, p < 0.001; 9/10 seeds, 34/50 episodes).
* TD3: −2.5 %, **not significant** (t = −1.35). Two seeds are clearly worse
  (2.57 and 2.56 Hz·s).
* Against the rule-based controller, neither agent differs significantly
  (−1.0 % DDPG, +2.3 % TD3).
* The tuned baselines still settle faster (0.11–0.13 s vs 0.37–0.46 s).

### Test scenarios (five deterministic real-weather windows)

The learned controllers tie the tuned baselines on IAE (+1 to +3 %, |t| < 1.6).
They reserve 29–32 % less headroom than the tuned constant controller and
13–16 % less than the rule-based one, and give the highest nadir
(49.80–49.81 Hz).

### TD3 vs DDPG

There is no significant difference on any metric (Welch |t| ≤ 2.0). The
practical difference is *when* the best policy appears: TD3 peaks at
episodes 30–300 (median 75), DDPG at 20–780 (median 385). The earlier,
less-trained TD3 checkpoints fit its larger seed-to-seed spread in IAE.

### Critic bias, with real weather (10 seeds)

| | Selected checkpoint (Q − G) | Episode 1000 (Q − G) |
|---|---|---|
| DDPG | −11 to +55 (8 of 10 positive) | +42 to +79 (all positive) |
| TD3 | −16 to −48 (all negative) | −160 to −210 (all negative) |

### 5 seeds vs 10 seeds

| Claim | 5 seeds | 10 seeds |
|---|---|---|
| TD3 IAE vs tuned constant (stress) | −5.5 %, t = −2.82 (significant) | −2.5 %, t = −1.35 (not significant) |
| DDPG IAE vs tuned constant (stress) | −5.1 %, t = −2.61 (not significant) | −5.6 %, t = −5.20 (significant) |
| Reserve vs tuned constant | −24 to −27 % | −24 to −26 % (10/10 seeds) |

Algorithm rankings from few seeds are fragile, and the manuscript now says
so explicitly. The headroom saving at equal regulation is the robust result.

## Synthetic vs measured weather

| | Synthetic | Measured |
|---|---|---|
| Best agent vs fixed tuned, stress IAE | TD3 +3.2 % (worse) | **DDPG −5.6 % (significant, 10 seeds)** |
| Agent reserve vs fixed tuned (test) | −20 to −23 % | **−29 to −32 %** |
| TD3 vs DDPG | not significant | not significant |

The learned controllers gain more over constant gains when the disturbances
are real. Measured cloud edges and turbulent wind vary more than the smooth
synthetic profiles, so a state-feedback policy has more to adapt to. This is
the most useful message for the paper.

## Suggested abstract claims (10-seed measured-data study)

> On 50 held-out measured-weather episodes, both learned controllers match
> the regulation of the tuned controllers while reserving 24–26 % less
> converter headroom than the tuned constant-gain VSG and 10–13 % less than a
> rule-based adaptive VSG, consistently over ten seeds; DDPG additionally
> reduces the integral absolute frequency error by 5.6 % (significant),
> whereas TD3's 2.5 % reduction is not significant.
