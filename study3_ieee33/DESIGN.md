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
  X_d and X_v; loads are constant impedances evaluated from the operating-point P, Q at 1 pu
  (classical transient-stability load model, Kundur 1994); PV and wind are grid-following
  current injections at bus 33 (P from the resource, unity power factor).
* The network is Kron-reduced to the machine nodes and bus 33; the reduction is recomputed only
  when the load changes (load steps), so each step costs a few small complex matrix products.
* Each machine's electrical power follows from the network solution; the rotor equations, the
  governor, AGC, EMS, BESS limits, PV share and feasibility layer are those of Study 2.
* Frequency for the VSG controller and the metrics is measured at bus 18 (the VSG bus) through
  the same 20 ms filter; voltages are available at every bus.
* EMF magnitudes are fixed at their initial values (no AVR in this first version).

## Validation plan
1. Feeder data: reproduce the published base case (done: 202.68 kW, Vmin 0.9131 pu at bus 18).
2. Network solution: the initial operating point must match an independent pandapower load flow
   with the same injections.
3. Single-bus limit: with all feeder impedances set to (nearly) zero, the model must reproduce the
   Study 2 two-machine response for the same scenario.
4. Then: oracle bound, feasibility rules, learning, evaluation as in Study 2.

## Open points (to confirm with the author)
* Load steps are distributed over the buses in proportion to the published loads (a feeder-wide
  change). A step at a single bus is an alternative.
* No AVR on the diesel and VSG in this first version.
