# Validation in MATLAB / Simulink / Simscape Electrical

## 0. MATLAB implementation of the study (done, cross-validated)

`matlab/sim/` is an independent MATLAB implementation of the whole simulation: the two-machine RMS model, the EMS dispatch, BESS SoC and secondary control, the band-power projection, the 0.25 s rate limit with feasibility clipping, the exported TD3 policy, and the metrics. It runs in MATLAB (no toolboxes needed) and in GNU Octave.

```bash
python scripts/export_matlab_validation.py          # scenarios, exact noise, TD3 policy, Python reference
```
```matlab
cd matlab
run_matlab_validation                                % about 3 min in Octave, faster in MATLAB
```
```bash
python scripts/plot_matlab_validation.py            # paper figure: results/figures/fig_matlab_validation.pdf
```

**Result (12 test scenarios × 3 controllers; MATLAB R2021a and GNU Octave 8.4 give identical numbers):**
* The operating-point dispatch is identical.
* Fixed and projected VSG traces are bit-identical (max |Δ| = 0).
* TD3-policy traces differ by at most 1.1·10⁻⁷ Hz and 6·10⁻⁸ MW. The only source is float32 arithmetic in the PyTorch actor.
* All metrics (nadir, RoCoF, BESS energy, infeasible commitments, saturation, return) agree to 0.00 %.

See `matlab/results/validation_summary.txt`. This verifies the implementation across tools (code-to-code); it is not yet a circuit-level validation. Section 0b adds that.

## 0b. Circuit-level (EMT) model in Simscape Electrical (`matlab/simscape/`)

A three-phase 400 V, 50 Hz model of the same microgrid, simulated at 100 µs (Specialized Power Systems, discrete). It is built by a script, so there's no manual wiring:

```matlab
cd matlab/simscape
run_simscape_validation        % builds vsgrl_emt.slx on the first run, then simulates and compares
```

| Part | Circuit-level model | RMS model it is compared with |
|---|---|---|
| VSG (BESS + PV support) | average-model converter: 3 controlled voltage sources behind R + jX_v; swing equation on **measured** power; power limiter on the angle; bus-voltage regulation | algebraic power share, hard clip |
| Diesel generator | EMF behind R + jX_d, swing equation, governor + engine lag, droop + AGC | same mechanics, algebraic network |
| Wind, PV base, load | grid-following current injection synchronised to its PLL (constant power) + 2 % shunt resistance | power balance |
| Frequency measurement | SRF-PLL (20 Hz) on the bus voltage, then the same 20 ms filter | ideal bus frequency + 20 ms filter |
| Control | identical 50 ms decisions: fixed / projected VSG / exported TD3 actor with the band-power projection | — |

* **Same parameters as the RMS model:** X_v = 1/K_s = 0.5 pu and X_d = 1/K_d = 1.25 pu (X/R = 10). The operating point, events and wind/load noise are those of the RMS model.
* **Where differences come from:** network electromagnetics, the E·V·cos δ nonlinearity, reactive power and voltage, the PLL, and the converter limiter acting on measured power.
* **Warm-up and sign check:** a 0.5 s warm-up precedes each 30 s episode. During it, the controller checks the current-measurement and current-source polarity of the blocks and corrects them automatically.
* **Controller code:** all control code is in `vsgrl_emt_ctrl.m`, called from one MATLAB Function block.
* **Without Simulink:** `vsgrl_emt_bench.m` solves the identical circuit as a script (`USE_SIMULINK = false`, also works in Octave). It is the cross-check for the Simulink model.

**Results** (script-only solver of the same circuit, 12 test scenarios × 3 controllers; `python scripts/plot_emt_validation.py`):

| Metric | EMT vs RMS |
|---|---|
| Δf RMSE | 0.014–0.018 Hz |
| Nadir, fixed controllers | within 0.2 % |
| Nadir, TD3 | 4 % deeper (0.521 vs 0.502 Hz) |
| BESS energy | within 0.8 % |
| RoCoF, 100 ms window | ×2.5 (phase-jump spikes in the PLL) |
| RoCoF, 500 ms window | +3 to +11 % |
| Converter saturation time | ×2.3–2.7 (the limiter acts on measured power, including first-cycle transients) |
| Infeasible commitments, projected controllers | ≤ 0.03 s |

* **The controller ordering is the same in both models for every metric.**
* **Simscape confirmation is pending:** run `run_simscape_validation` (with `USE_SIMULINK = true`) in MATLAB R2021a.

Sections 1–4 below are the original manual-build notes, kept for reference.

Goal: show that a policy trained on the fast RMS model keeps its advantage in a circuit-level (average-value converter) model. The scenarios, parameters and policy are identical; only the plant fidelity changes.

> The MATLAB files in `matlab/` could not be executed in the environment where they were written. The numerical logic is mirrored and tested in Python: the forward-pass parity test is in `tests/test_env_agent.py`. Run `vsgrl_policy.m` once against a Python trace before relying on it.

## 1. Export from Python

```bash
python scripts/evaluate.py       # creates results/scenarios_test.csv and reference traces
python scripts/export_matlab.py  # → matlab/export/{vsgrl_params.mat, vsgrl_policy_<algo>_seed<k>.mat, scenarios_test.csv, traces/}
```

## 2. Simscape model to build (`microgrid_vsg.slx`)

| Block | Simscape Electrical component | Parameters (from `vsgrl_params.mat`) |
|---|---|---|
| Diesel SG | Synchronous Machine (round rotor, standard) + Diesel Engine Governor + excitation (AC1A/ST1A) | 0.5 MVA, H = `system_diesel_inertia_h_s`, droop `system_diesel_droop`, T_g, T_e |
| BESS + VSG inverter | Average-value 2-level VSC + DC source/battery (Battery block with SoC) | 0.5 MW, 2 MWh, SoC limits |
| PV | PV array + average-value boost/inverter with **de-loaded MPPT** (P_ref = (1−d)·P_mpp) | `system_pv_rated_mw`, `system_pv_deload_fraction` |
| Wind | Type-4 average model (PMSG + full converter), or a controlled current source fed with P_w(t) | 1 MW |
| Load | Three-Phase Dynamic Load or a switched RLC step | step `dist_mw` at `dist_time_s` |
| Network | 0.4 kV or 11 kV bus; filter/line X such that K_d ≈ 0.8 pu, K_s ≈ 2.0 pu on 2 MVA | – |

**VSG control (inside the BESS inverter):**
1. Active-power loop (swing equation): `2H dω/dt = P_ref − P_e − D(ω − ω_0)`, `dθ/dt = ω`. H and D come from the RL block.
2. Q–V droop for the voltage magnitude reference.
3. Virtual impedance, then cascaded voltage and current loops (PI in dq), then PWM or an average-value model.
4. Current limiting with angle anti-windup. This is the circuit-level counterpart of `P_v` saturation in `microgrid.py`.
5. PV headroom release: `P_pv,ref = (1−d)P_mpp + clip(α·P_vsg, −P_pv0, h_pv)` through the DC-link controller.

**RL block:** a MATLAB Function block running at a 50 ms sample time:
```matlab
obs    = vsgrl_build_obs(m, applied, p);                % measurements + currently applied H, D, alpha
h = h_up; if df > 0, h = h_dn; end                     % direction-aware headroom
bounds = vsgrl_headroom_bounds(h, load0, p);            % feasibility projection
[H, D, alpha, a] = vsgrl_policy(obs, pol, bounds);      % actor forward pass
applied = applied + 0.2 * ([H; D; alpha] - applied);    % rate limit, tau = 0.25 s at 50 ms
```
Load the policy struct with `pol = load('export/vsgrl_policy_td3_seed0.mat')`. Pass it as a parameter, or use `coder.load` for code generation. Measurements: bus frequency from a PLL with a 20 ms low-pass filter, RoCoF as the derivative of the filtered value, SoC from the battery block, and headroom from SoC (taper) plus d·P_mpp.

## 3. Validation runs

1. **Model agreement (fixed VSG):** run the `fixed` controller (H = 3 s, D = 20, α = 0.3) on 3–5 test scenarios in both models. Compare nadir, RoCoF and P_vsg with `compare_python_simulink.m`. Target: nadir and RoCoF within about 10–15 %, with the same ranking across scenarios.
2. **Policy transfer:** run the TD3 policy (best seed, plus one median seed) on the same scenarios.
3. **Report a table** with columns: scenario | controller | nadir Py / Sim | RoCoF Py / Sim | BESS peak Py / Sim. The claim to support is that the controller ranking is preserved in the circuit-level model.
4. If agreement is poor, first re-tune K_d and K_s in the YAML to match the Simscape network's synchronising power. Then retrain and re-export.

## 4. Optional: fine-tune in Simulink

Reinforcement Learning Toolbox can import the actor (`rlContinuousDeterministicActor` built from the exported weights). You can then fine-tune it with `rlTD3Agent` on the Simscape model for a few hundred episodes. This is a "sim-to-sim transfer" result.
