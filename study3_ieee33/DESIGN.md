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

## Voltage-control parameter sources (collected 16 Nov 2026)
| Item | Value | Source | Status |
|---|---|---|---|
| BESS grid-forming VSG: steady-state Q–V droop m_Q(0) | 0.05 pu/pu (range 0.01–0.05) | UNIFI Consortium, "UNIFI Specifications for Grid-forming Inverter-based Resources — Version 3", UNIFI-2026-2-1 / NLR/TP-5D00-98381, Jan. 2026, Table 7, p. 33 | sourced |
| BESS grid-forming VSG: steady-state P–f droop m_P(0) | 0.05 pu/pu (range 0.01–0.05) | same, Table 7 | sourced (for reference; Study 3 keeps the VSG damping D_v as the action) |
| GFM minimum reactive stiffness \|Q/V\|min | 0.5 pu/pu (range 0.5–10) | same, Table 8, p. 33–34 | sourced (acceptance check) |
| GFM maximum equivalent inductance L_max | 0.75 pu (range 0.1–0.75) | same, Table 8 | sourced (acceptance check on X_v = 0.5 pu) |
| PV / wind (grid-following) reactive capability, Category B | ≥ 44 % injecting and ≥ 44 % absorbing | D. Narang, "Highlights of IEEE Standard 1547-2018", NREL webinar, Oct. 2019 (rev. Nov. 2019), slide 30 | sourced (capability only) |
| PV / wind volt-var default curve (V1–V4, Q1–Q4) and response time | — | IEEE Std 1547-2018, Clause 5.3 table (not in the highlights) | **missing** |
| Diesel excitation system | Type AC9C, sample data set 1 (thyristor bridge supplying the exciter field), values below | IEEE Std 421.5-2016, Annex H.14, Table H.19, p. 152 | sourced; block diagram (Figure 17) still needed |
| Diesel alternator data | 4900 kVA, pf 0.8, 11 kV, 50 Hz, 1500 rpm; Xd 2.18, Xq 0.950, X'd 0.286, X''d 0.190, X''q 0.255 pu; T'do 4.0 s, T'd 0.59 s, T''d 14 ms | K. Mahtani, J. Muñoz-Antón, S. B. Lee, C. A. Platero, "Online diagnostics of brushless synchronous machine exciter field winding through temperature and resistance measurement," IEEE Trans. Ind. Appl., vol. 61, no. 3, pp. 3774–, May/Jun. 2025, Table II | sourced (author decision 18 Nov 2026: option A, diesel rated 4.9 MVA / 3.92 MW at 0.8 pf) |
| Diesel inertia constant H | 2 s (own base), as in Study 2 | not given in the machine source | to confirm |

### IEEE 421.5-2016 Table H.19 — AC9C sample data, set 1 (p. 152)
R_C 0, X_C 0 pu; T_R 0.01 s; K_PR 10 pu; K_IR 10 pu/s; K_DR 0 pu·s; T_DR 0.01 s; V_PIDmax 1.6, V_PIDmin 0 pu;
K_PA 4 pu; K_IA 0 pu/s; V_Amax 0.996, V_Amin −0.866 pu; K_A 20 pu; T_A 0.0018 s; V_Rmax 19.92, V_Rmin −17.32 pu;
K_F 0.2 pu; T_F 0.01 s; K_FW 0; V_FWmax 10, V_FWmin 0 pu; S_CT 1; K_C 0; K_D 1; K_E 1 pu; T_E 1 s; V_FEmax 16, V_Emin 0 pu;
E_1 4.167 pu, S_E(E_1) 0.001; E_2 3.125 pu, S_E(E_2) 0.01; SW_1 position A; K_C1 0; K_P 1; K_I1 0; X_L 0; θ_P 0°;
V_B1max 100 pu; K_C2 0; K_I2 0; V_B2max 0 pu.

### IEEE 421.5-2016 model structure received
* Type AC8C block diagram (screenshot received 18 Nov 2026): V_C, V_REF, V_S summing → HV gate (UEL) → LV gate (OEL)
  → PID K_PR + K_IR/s + sK_DR/(1+sT_DR), limits V_PIDmax/V_PIDmin → HV / LV gates → K_A/(1+sT_A), limits V_Rmax/V_Rmin
  → × V_B (power source: SW_1 position A = potential/compound source V_E1 = |K_P V_T + j(K_I + K_P X_L) I_T|,
  I_N1 = K_C1 V_FE / V_E1, F_EX1 = f(I_N1), V_B ≤ V_Bmax; position B = constant) → E_FE → AC rotating exciter → E_FD.
  Decision: AC8C is used (digital PID AVR with brushless exciter); its sample-data table is still needed.
* Figure 8 — AC rotating exciter with non-controlled rectifier:
  T_E dV_E/dt = E_FE − V_FE,  V_Emin ≤ V_E ≤ (V_FEmax − K_D I_FD)/(K_E + S_E(V_E));
  V_FE = V_E S_E(V_E) + K_E V_E + K_D I_FD;  I_N = K_C I_FD / V_E;  F_EX = f(I_N);  E_FD = V_E F_EX.
