# Study 3 design — IEEE 33-bus islanded microgrid

Decisions by the author (6 Nov 2026): keep the published feeder and loads; scale the Study 2 plant
by 3.715 / 0.8 = 4.644; diesel at bus 1, BESS-VSG at bus 18, PV and wind at bus 33.

## What is taken from published sources (unchanged)
| Item | Value | Source |
|---|---|---|
| Line r, x (32 lines, 5 open ties) | as published | Baran & Wu 1989 via MATPOWER case33bw (verified, see README) |
| Bus loads at peak | 3715 kW / 2300 kVAr, per-bus values as published | same |
| Base voltage | 12.66 kV | same |
| Load shape over the year | EGAT 2024 Northeast-region demand | Zenodo EGAT system data (as in Study 2) |
| Weather | ERA5 wind, NASA POWER solar, Nakhon Ratchasima 2024 | as in Study 2 |

## What is scaled from Study 2 (factor k = 3.715 / 0.8 = 4.644)
Every MW / MWh rating and every load step is multiplied by k, and the per-unit base is
S_base = 2 MVA × k = 9.2875 MVA, so that every per-unit parameter of Study 2 (inertia, droop,
governor, AGC, BESS limits, VSG ranges, reward weights, feasibility limits) is unchanged.

| Item | Study 2 | Study 3 |
|---|---|---|
| Diesel | 0.5 MW, H = 2 s | 2.322 MW, H = 2 s |
| BESS (grid-forming VSG) | 0.5 MW / 2 MWh | 2.322 MW / 9.288 MWh |
| PV (15 % de-loaded) | 0.8 MW | 3.715 MW |
| Wind (class III) | 1.0 MW | 4.644 MW |
| Load peak | 0.8 MW | 3.715 MW (= published total) |
| Load steps | 0.2–0.4 MW | 0.93–1.86 MW |

## Network model (what changes)
Study 2 shares each imbalance between the diesel and the VSG through two synchronising
coefficients at one bus (X_d = 1/K_d = 1.25 pu, X_v = 1/K_s = 0.5 pu). Study 3 keeps the two
internal reactances and places them at buses 1 and 18 of the published feeder:

* Phasor (RMS) network solution at every 2 ms step: the diesel and VSG are EMFs E∠δ behind
  X_d and X_v; loads are constant power with the published P and Q per bus (as in the published
  case and in Study 2), entered as current injections from the previous step's voltages;
  constant-impedance loads are available as an option. PV and wind are grid-following current
  injections at bus 33 (P from the resource, unity power factor).
* The bus admittance matrix (lines + machine reactances) is inverted once per episode, so each
  step costs one 33×33 complex matrix-vector product.
* Each machine's electrical power follows from the network solution; the rotor equations, the
  governor, AGC, EMS, BESS limits, PV share and feasibility layer are those of Study 2.
* Frequency used by the controllers, the reward and the metrics is defined exactly as in Study 2:
  the K-weighted mean of the diesel and virtual rotor speeds, through the same 20 ms filter. The
  angle-based (PLL-like) frequency at bus 18 is recorded separately; it contains phase-jump spikes
  at load steps (−0.30 Hz for 20 ms in one test), the effect already seen in the EMT validation.
* Governor, AGC and BESS secondary control act on the measured frequency, as in Study 2.
* EMF magnitudes are fixed at their initial values (no AVR in this first version).

## Validation results (scripts/validate_network_model.py)
* V1 feeder data: published base case reproduced (202.68 kW, Vmin 0.9131 pu at bus 18); own
  Newton-Raphson load flow equals pandapower within 3e-9 pu.
* V2 initial point: the dynamic network reproduces the load flow within 1e-10 pu (voltages and
  machine powers).
* V3 single-bus limit (feeder impedances x1e-3, fixed tuned VSG, 6 test scenarios): nadir within
  0.2–1.1 % of Study 2 and RMS frequency difference 0.002–0.007 Hz in the five scenarios without
  converter saturation. In the one scenario where the BESS reaches its discharge limit the nadir
  differs by 7 %: the BESS stays at its limit for 0.33 s instead of 0.22 s, because the exact
  sine power-angle relation and Study 2's linearised sharing release the limit at different times.
  Note: Study 2 flags saturation on about half of the steps it spends at the limit (0.11 of 0.22 s
  here); the reported saturation time of both models therefore under-counts the time at the limit.

## Validation plan
1. Feeder data: reproduce the published base case (done: 202.68 kW, Vmin 0.9131 pu at bus 18).
2. Network solution: the initial operating point must match an independent pandapower load flow
   with the same injections.
3. Single-bus limit: with all feeder impedances set to (nearly) zero, the model must reproduce the
   Study 2 two-machine response for the same scenario.
4. Then: oracle bound, feasibility rules, learning, evaluation as in Study 2.

## Decisions (6 Nov 2026, continued)
* Feeders: IEEE 33-bus is the main study; the key results are repeated on the IEEE 69-bus feeder
  (Baran & Wu, IEEE Trans. Power Del. 4(1):725–734, 1989) as a robustness check.

## Open points (to confirm with the author)
* Load steps are distributed over the buses in proportion to the published loads (a feeder-wide
  change). A step at a single bus is an alternative.
* No AVR on the diesel and VSG in this first version.
* Saturation-time metric: count the time the BESS is at its limit (proposed for Study 3), or keep
  Study 2's definition for comparability.
