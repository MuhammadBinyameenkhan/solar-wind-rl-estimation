# Changes relative to `vsg_rl_complete_4.py`, and what the manuscript must change

Each item lists the defect, the fix in this repository, and the matching
edit to the paper.

## A. Physics and model

| # | Defect in the original script | Fix | Manuscript edit |
|---|---|---|---|
| A1 | **"No VSG" was not zero.** `env.step` clipped every action to J ≥ 0.05, D ≥ 5, so the "No VSG" baseline ran with D = 5 pu (hence its 0.054 pu reserve in Table 2). | `env.step` accepts J = D = 0; the agents remain inside [J_MIN, J_MAX] × [D_MIN, D_MAX] through their tanh map. | Re-run Table 2 and Fig. 3. The true no-VSG case is much worse, which strengthens the motivation. |
| A2 | **Governor with no physical source.** A "governor" droop injected up to ~330 kW into a microgrid described as 100 % inverter-based, and none of it counted against any converter rating. | The droop is now part of the BESS setpoint: `P_bess = P_agc + P_droop + P_vsg`, limited by the 2500 kVA rating, and it reduces the available headroom `h_avail`. | Section 3.4: describe the 10 % droop as the BESS's primary response and update Eqs. (10)–(12) and (23). |
| A3 | Kq changed instantly while J and D were slew-limited. | Kq is slew-limited at the same rate. | Section 3.4, slew paragraph. |
| A4 | `CalibratedWeatherScenarios` hard-coded 10 s event timings, so with 30 s episodes the cloud and wind events all fell inside the first 6 s. | Every scenario scales with the episode length. | Fig. 3 changes. |
| A5 | Unused `tip_speed_ratio` returned the tip speed rather than the ratio. | Removed. | — |

## B. Reinforcement-learning formulation

| # | Defect | Fix | Manuscript edit |
|---|---|---|---|
| B1 | The **actuator state was not observed.** J, D and Kq are slew-limited, so the values in force belong to the plant state, yet they were missing from the observation, as was `h_avail`, the quantity the feasibility constraint is checked against. | State is 14-dimensional: adds J/J_max, D/D_max, normalised Kq and h_avail. | Eq. (27). |
| B2 | `r_var` penalised renewable variability, which the action cannot affect, so it only added noise to the critic. | Removed. | Eq. (28): remove the variability term. |
| B3 | The reserve cost used an arbitrary 0.3/0.7 split of J/J_max and D/D_max, unrelated to the Eq. (22) headroom the paper reports. | `−W_RESERVE · h_req`, with h_req from Eq. (22). | Eq. (28). |
| B4 | Time-limit episode ends were stored as terminal, cutting off bootstrapping. | Only a protection trip is terminal. | — |
| B5 | Exploration noise used the global NumPy RNG. | Each agent has its own seeded RNG, so runs reproduce exactly. | — |
| B6 | Priority updates used `|Q1 − y|` only. | Uses `max(|Q1 − y|, |Q2 − y|)` for TD3. | — |

## C. Evaluation and statistics

| # | Defect | Fix | Manuscript edit |
|---|---|---|---|
| C1 | **Overshoot measured the wrong event.** It took the maximum after the nadir over the whole episode, which is the response to contingency 2 (the load drop). That produced the 106 % / 73 % values discussed in §4.7. | Overshoot is the rebound after the contingency-1 nadir and before contingency 2 starts. The contingency-2 peak is reported separately as `zenith_hz`. | Table 2, Fig. 7(b), §4.7 (the overshoot discussion largely disappears). |
| C2 | **Model selection on the test set.** The best checkpoint was chosen on the same five scenarios used for reporting, and the training, selection and test seeds overlapped. | Three disjoint splits (train, validation, test) plus a held-out stress test. A pytest checks they don't overlap. | Section 3.8: describe the splits. |
| C3 | **No tuned baseline.** The paper's fixed configurations are infeasible, and a tuned constant (J ≈ 0, D ≈ 30) beat TD3 on IAE, ISE, ITAE, settling and overshoot. | `fixed_tuned` and `adaptive_rule` baselines, tuned on the validation set with the agents' own reward, plus a Pareto frontier over the full fixed-gain grid in Fig. 7(g). | Tables 2–3, Fig. 7, abstract, conclusions. |
| C4 | **Single seed.** | Five seeds by default, mean ± 95 % CI, and Welch t-tests for TD3 vs DDPG. | Remove the single-seed limitation; report CIs. |
| C5 | **The critic-bias claim had no supporting measurement.** The logged Q was a replay-batch mean over old actions, and no "true discounted return" was ever computed. | At each evaluation, Q(s, μ(s)) is compared with the Monte-Carlo discounted return on the validation states (`q_bias`, `q_min_bias`). | Rewrite the critic-calibration paragraphs (§4.2, 4.3, 4.7, conclusions) from the measured biases. |
| C6 | The held-out stress test existed but was never reported. | Reported in `RESULTS.md` and Fig. 7(h). | Add a generalisation table. |
| C7 | `evaluate()` and the training loop hard-coded 60 Hz. | Use `F_NOM`. | — |
| C8 | `--smoke`, `--real-data` and `--live` had no effect, because `main()` assigned module globals without `global`. | `config` attributes are read at call time, and the CLI sets them. | — |

## D. Data provenance

| # | Issue | Fix | Manuscript edit |
|---|---|---|---|
| D1 | "768 site measurements" were Open-Meteo **model** output: 7 past days plus 1 forecast day of a moving window, re-downloaded at run time, so the results could not be reproduced. | Calibration lives in a committed JSON file. `python -m vsg_rl.weather --calibrate` rebuilds it from a fixed window of the Open-Meteo historical archive (ERA5). | Describe the data as reanalysis for the site coordinates, not on-site measurements. Give the archive dates. |
| D2 | The 30 % cloud depth equalled the lower clip bound (`np.clip(…, 0.30, 0.95)`), and the "largest drop" statistic included sunset ramps. | Cloud depth is the 99th-percentile relative hour-to-hour drop while irradiance is above half its daytime P90, with no silent clipping. | §4.1, Table 1. |

## E. Text inconsistencies to fix in the manuscript

* §4.3 says inertia is weighted "four times" damping in Eq. (22); §3.4.1 and §4.6 say "eight times". The coefficients are 0.08 and 0.01, but they multiply J (seconds) and D (pu), so "eight times" depends on the units. Prefer: "one second of virtual inertia costs as much headroom as 8 pu of damping".
* The abstract says the high-gain fixed configurations "require 0.394 pu". They require 0.62 and 1.80 pu. 0.394 pu is what they deliver after derating.
* The RL agents adapt Kq, while every fixed controller keeps Kq = 8, so the voltage comparison in §4.4(h) is not like-for-like. Say so, or add a tuned-Kq baseline.
* Section 3.6 says "Action: … virtual inertia and damping"; the action is [J, D, Kq].
* Remove "Banshee Feeder 2" if it is not the actual site name; the paper places the system at Nakhon Ratchasima.
