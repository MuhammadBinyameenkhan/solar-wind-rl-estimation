# Methodology

Everything here matches the code. Parameter values are the defaults in `configs/default.yaml`.

## 1. Study system

| Unit | Rating | Role / model | Inertia |
|---|---|---|---|
| Diesel SG | 0.5 MW | Voltage source behind K_d; droop R = 5 % (own base), governor T_g = 0.2 s, engine T_e = 0.5 s, ramp 1 pu/s, AGC K_i = 0.3 | H_d = 2 s (own base) → **0.5 s on 2 MVA** |
| Wind | 1.0 MW, IEC III (cut-in 2.5, rated 10 m/s, 100 m hub) | Grid-following MPPT; ERA5 hourly mean + OU turbulence (TI 10 %, τ = 2 s); rotor/converter lag 0.5 s | none |
| PV | 0.8 MW (sweep 0.5–0.8) | Grid-following, **de-loaded MPPT**: base output (1−d)P_mpp, headroom h_pv = d·P_mpp (d = 0.15); headroom release lag T_pv = 80 ms | none |
| BESS | 0.5 MW / 2 MWh | DC source of the grid-forming VSG; η_c = η_d = 0.95; SoC limits 0.10–0.95 with a 5 % linear power taper | **virtual: H_v ∈ [0.2, 8] s, D_v ∈ [0, 50] pu** |
| Load | 0.3–0.8 MW | Daily profile in local time UTC+7 (or measured CSV); damping D_L = 1 pu; 0.5 % OU noise | – |

Base: S_b = 2 MVA, f_0 = 50 Hz. All powers below are per-unit of S_b and frequencies are per-unit of f_0.

**Why "low inertia":** the only rotating mass is the diesel SG, giving H_sys = 0.5 s on the system base. A 0.3 MW step (0.15 pu) without fast support produces an initial RoCoF of roughly 0.15/(2·0.5) pu/s ≈ 7.5 Hz/s. The `none` baseline confirms collapse in most scenarios.

### 1.1 Operating point (per episode) from real data

For the sampled hour: P_w,av = P_curve(v_hub, ρ) (ERA5) and P_mpp = PV(GHI, T_amb) (NASA POWER), plus the load from the profile or CSV. Economic dispatch then sets the operating point:

1. residual = P_L − P_w,av − (1−d)P_mpp
2. If residual < P_d,min (30 % of diesel rating), curtail wind first, then PV. Curtailed PV is added to the PV headroom.
3. If residual > 0.85·P_d,rated (keeping 15 % spinning reserve), the BESS discharges a base power P_b0 ≤ 0.6·P_dis,max(SoC). Any remaining deficit means load would be shed at dispatch, and the hour is rejected by the adequacy screen.
4. P_d0 = residual − P_b0

**Adequacy screen** (`scenarios.py`): an operating point is kept only if no load is shed at dispatch and the upward reserve (diesel spare plus VSG headroom) covers the step. This excludes hours where *no* controller could survive the event. The study is about frequency-stability control, not generation adequacy. Report the rejection rate, which `evaluate.py` prints.

## 2. Dynamic model (`vsgrl/microgrid.py`)

The model is an RMS (phasor-averaged) two-machine model. The diesel SG and the VSG are both voltage sources. They share the load bus through synchronising coefficients K_d = 0.8 and K_s = 2.0 pu. Wind and the PV base output are constant-power injections.

**Network (algebraic, incremental):**

```
ΔP_net = ΔP_L − ΔP_w + D_L P_L0 Δω_b
P_v    = K_s (K_d δ + ΔP_net) / (K_d + K_s),      δ = θ_v − θ_d
ΔP_e,d = ΔP_net − P_v
Δω_b   = (K_d Δω_d + K_s Δω_v)/(K_d + K_s)
```

At t = 0⁺ of a step, the VSG instantly takes K_s/(K_s+K_d) ≈ 71 % of it, which is the defining grid-forming behaviour.

**Diesel SG:**

```
2H_d dΔω_d/dt = ΔP_m − ΔP_e,d − D_d(Δω_d − Δω_b)
P_ref = P_d0 − Δf_meas/R + x_agc,      dx_agc/dt = −K_i Δf_meas            (K_i = 2.0)
T_g dP_gov/dt = P_ref − P_gov,         T_e dP_m/dt = P_gov − P_m   (ramp- and rating-limited)
```

**VSG (virtual rotor) with BESS secondary control:**

```
2H_v dΔω_v/dt = P_set − P_v − D_v Δω_v
dδ/dt = ω_0 (Δω_v − Δω_d)
dP_set/dt = −K_i,b Δf_meas,   P_set clipped to the current headroom     (K_i,b = 2.0)
```

The BESS takes part in secondary control. Without this, the diesel saturates after a large step and the frequency stays 0.2–0.4 Hz off-nominal for tens of seconds, which no choice of H or D can fix. With the integral gains at 2.0, frequency is restored within about 10–20 s. H and D then shape the *transient*, which is what synthetic inertia is for.

**Headroom limits (the feasibility constraint in the physics):**

```
P_v ∈ [ −(P_ch,max(SoC) + P_b0) + P_pv,s ,  P_dis,max(SoC) − P_b0 + P_pv,s ]
P_dis,max = P_b,rated · clip((SoC − SoC_min)/0.05, 0, 1)
P_ch,max  = P_b,rated · clip((SoC_max − SoC)/0.05, 0, 1)
```

When the requested P_v exceeds the limit, the VSG becomes current-limited. Angle-based anti-windup clamps δ, and the virtual rotor follows the diesel speed. The amount of saturation is logged and penalised.

**Allocation between PV headroom and BESS:**

```
T_pv dP_pv,s/dt = clip(α P_v,req, −P_pv,0, h_pv) − P_pv,s
P_bess = P_b0 + P_v − P_pv,s
dSoC/dt = −P_bess/(η_d E)   (discharge)   or   −η_c P_bess/E   (charge)
```

PV headroom is "free" energy that is already reserved, but it is slower (T_pv) and capped at h_pv. The BESS is fast but costs cycling. Learning α captures this trade-off.

**Measurement:** the bus frequency passes through a first-order PLL low-pass (T_f = 20 ms). RoCoF is the derivative of the filtered signal. The phase-jump term of the bus angle is excluded from Δω_b, which is standard for RMS models.

**Integration:** symplectic (semi-implicit) Euler at 2 ms, with velocities updated before angles. This is stable for the stiffest setting (H_v = 0.2 s, D_v = 50), and the tests check this over the whole action range.

**Baseline "droop" (grid-following BESS):** P = −D·Δf_meas, with PLL plus current-loop lag T = 50 ms. It provides fast frequency response but no inertia.

## 3. MDP formulation (`vsgrl/envs/vsg_env.py`)

* **Episode:** 30 s with **2–3 load events**. The first comes at t ∈ U[0.5, 1.5] s; the rest are at least 7 s apart, and none falls in the last 5 s. Each step is U[0.2, 0.4] MW; it is a load increase with probability 0.75, and the sign flips if needed to keep the net change within ±0.4 MW. SoC, AGC state, the BESS set-point and the committed headroom all carry over from one event to the next. The adequacy screen uses the largest cumulative load increase.
* **Decision interval:** 50 ms (200 decisions per episode), with 25 plant sub-steps per decision.
* **Observation (16 values, normalised):** Δf, RoCoF, P_vsg, Δω_v − Δω_d, upward headroom h_up, downward headroom h_dn, PV headroom h_pv, SoC, P_wind, P_pv,mpp, P_diesel, diesel spare, pre-event load, previous action (3).
* **Action:** a ∈ [−1, 1]³ → (H_v, D_v, α). There are two mappings (`env.action_mode`):
  * `absolute`: a spans [min, projected upper bound] linearly.
  * `residual`: a = 0 is the nominal VSG (H = 3 s, D = 20, α = 0.3). a = ±1 moves to the projected bounds, so the policy learns *corrections* to a working VSG. This is residual policy learning: early exploration is safe, and the agent never starts from an arbitrary point in parameter space.

### 3.1 Headroom feasibility projection

Before mapping, the action's upper bounds are made to depend on the headroom in the direction of the event. While Δf ≤ 0 (pre-event or under-frequency), that is the upward headroom h = h_up = max(P_dis,max(SoC) − P_b0, 0) + h_pv. During an over-frequency event (Δf > 0), it is the downward headroom h = h_dn = max(P_ch,max(SoC) + P_b0, 0) + P_pv,base.

*Why direction-aware:* an earlier version used h_up only. At high SoC the BESS charge limit tapers, so in load-rejection events high damping saturated the charge side, and the agent learned to drop D to about 8. That was the dominant failure mode in the pilot. The formulas below use h for whichever headroom applies:

```
s     = min(h / ΔP_design, 0.95)                    ΔP_design = 0.4 MW = 0.2 pu
D_ub  = min(D_max, β s/(1−s)),     β = 1/R_sb + D_L P_L0
        (the VSG's quasi-steady share D/(D+β) of the design step must fit in h)
ρ     = min(1, h / (K_s/(K_s+K_d) · ΔP_design))
H_ub  = H_min + ρ (H_max − H_min)
        (the inertia commitment is scaled by headroom relative to the VSG's instantaneous share of the design step)
H = H_min + (a_1+1)/2 · (H_ub − H_min),   D = D_min + (a_2+1)/2 · (D_ub − D_min)
```

The agent therefore cannot promise synthetic inertia or damping that the BESS and PV cannot physically back. This is the "feasible" in the title. The ablation `--set env.headroom_constraint=false` removes the projection, leaving only the reward penalty.

### 3.2 Reward (per decision, averaged over the 25 sub-steps)

```
r = −[ w_f ⟨(|Δf| − 0.2)₊²⟩/0.5² + w_in ⟨Δf²⟩/0.5² + w_r ⟨(|RoCoF| − 1)₊²⟩/1²
       + w_b ⟨ΔP_bess²⟩/P_b,max² + w_s ⟨sat⟩/0.05
       + w_v · frac(|Δf| > 1 Hz or |RoCoF| > 1 Hz/s) + w_a ‖a_t − a_{t−1}‖² ]
w = (w_f 1.0, w_in 0.02, w_r 0.5, w_b 1.0, w_s 2.0, w_v 1.0, w_a 0.3)
```

**Grid-code band.** Frequency is penalised only outside ±0.2 Hz (the ENTSO-E Continental Europe maximum steady-state deviation) and RoCoF only above 1 Hz/s; a small in-band term keeps a pull towards nominal. Inside the band, BESS power is the only significant cost, so the agent should support frequency *just enough*. Lower damping lets the diesel droop and AGC take more of the deficit and saves BESS power, but too little damping breaks the band.

**Why this formulation.** With a plain quadratic frequency penalty on single 10 s events, tuning showed that *maximum damping* was optimal for fixed and adaptive VSGs alike, even with a 10× BESS cost. The problem had a trivial optimum, and a fixed max-damping VSG matched RL. With the band, multi-event episodes and BESS secondary control, the best fixed damping is *interior* (D ≈ 20), so there is a real trade-off. The BESS weight w_b = 1.0 was calibrated so that this is the case (`docs/EXPERIMENTS.md`).

The action-rate term (w_a = 0.3) matters. With a small weight (0.02), both TD3 and DDPG learned bang-bang switching of H between its bounds, and the switching transients caused RoCoF spikes above 1 Hz/s. Parameter changes in a real VSG are not free, so smooth schedules are a requirement, not a cosmetic choice.

If |Δf| > 3 Hz, the episode terminates with a −50 penalty. Truncation at 10 s is treated as non-terminal, so TD3 bootstraps through it.

## 4. Learning algorithms (`vsgrl/agents/td3.py`)

| Hyper-parameter | Value |
|---|---|
| Actor / critic | MLP 256-256, ReLU, tanh output |
| Optimiser | Adam, lr 3e-4 (both) |
| γ, τ | 0.98, 0.005 |
| Batch, buffer | 256, 1e6 |
| Warm-up | 5000 random steps |
| Exploration | Gaussian, σ 0.15 → 0.05 (linear) |
| TD3 extras | twin critics, target smoothing σ = 0.2 (clip 0.5), policy delay 2 |
| Episodes × seeds | 1000 × 5 (200 k steps per seed) |
| Model selection | best mean return on 20 fixed **validation** scenarios, evaluated every 50 episodes |

DDPG is the same code with twin critics, target smoothing and policy delay all switched off. The TD3 vs DDPG comparison is therefore a clean ablation of those three ingredients.

## 5. Evaluation protocol

* **Data split:** weekly blocks (5 train / 1 val / 1 test of every 7 weeks) over 2024, so every season is in every split and whole weeks limit leakage. Test weeks are never seen during training or model selection. With multi-year data, use `split.method: chronological` or `by_year`.
* **Test set:** 200 scenarios with a fixed seed. Every controller and every seed sees exactly the same scenarios, which allows paired tests. They are saved to `results/scenarios_test.csv` and reused in Simulink.
* **Metrics** (`vsgrl/metrics.py`): frequency nadir (max |Δf| in the event direction), max RoCoF over a 100 ms sliding window (as relays measure it), quasi-steady deviation (mean of the last 1 s), settling time (±0.1 Hz band around the final value), BESS energy throughput, peak BESS power, PV-headroom energy, saturation time, and frequency/RoCoF violation flags.
* **Statistics** (`scripts/analyze.py`):
  * For RL, metrics are averaged over seeds per scenario. Results are reported as the mean with a bootstrap 95 % CI over scenarios, plus ± std of the per-seed means to show seed sensitivity.
  * Comparisons use paired Wilcoxon signed-rank tests between the best RL controller and each baseline, per metric, with a Holm–Bonferroni correction.

## 6. Modelling assumptions to state in the paper

1. RMS model: no electromagnetic transients, inner current or voltage loops, or reactive power and voltage dynamics. These are covered by the Simscape validation stage.
2. Aggregated single-bus microgrid: no network impedance between units apart from the synchronising coefficients.
3. Irradiance is constant within a 10 s episode. Wind varies through the OU turbulence model.
4. Load profile is synthetic unless `data.load_csv` is provided. Say this explicitly, or provide a measured feeder profile.
5. Hourly ERA5 and NASA POWER data set the *operating point*. Sub-second dynamics come from the models above, not from the data.
