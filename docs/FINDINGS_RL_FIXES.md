# RL fixes (items 1–10): 10-seed rerun of DDPG and TD3

Full tables: [`results_measured_v2/RESULTS.md`](../results_measured_v2/RESULTS.md).
Figures: `results_measured_v2/figures/` (Figs. 4–5 training, 6 comparison,
7 metrics, 8 critic calibration). Per-seed CSVs:
`results_measured_v2/checkpoints/{algo}_seed{s}_{training,validation}.csv`.

## Protocol

Both agents use:
- the same 10 seeds, 1000 episodes, network sizes, replay buffer and
  curriculum;
- the same validation episodes and exploration-noise schedule;
- measured weather at its recorded levels.

Values are the mean ± 95 % CI over seeds (t × SD/√10). The comparison
between algorithms is Welch's t; agents are compared with the deterministic
baselines by a one-sample t-test (df = 9, |t| > 2.26 ⇒ p < 0.05). The
baselines were re-tuned under the new reward: fixed tuned J = 0, D = 35,
Kq = 20; the rule-based controller again turned its inertia term off
(kJ = 0).

## What was changed

| Item | Change | Scope |
|---|---|---|
| 1 | Action-rate penalty 0.05·(\|ΔJ\|/J_range + \|ΔD\|/D_range); first-order actuator filter τ = 0.08 s; running obs mean/std normalisation (std floor 0.05, clip ±5) | shared |
| 2 | Steps at action bounds logged (training, validation, test); RoCoF weight 10 → 25 on the 500 ms relay window + hinge 20·max(0, \|RoCoF\|/2 − 1); RoCoF-stress training episodes (H_sys 0.15–0.35 s, load step 25–35 %, p = 0.15/0.30 in curriculum stages 2/3). Headroom cost kept as Eq. (22). J not forced. | shared |
| 3 | Cause found and fixed (below) | shared |
| 4 | Grad-norm clip 1.0 (actor and critic); actor LR 1e-4, critic LR 1e-3, cosine annealing; τ = 0.005; same noise schedule; learner reward 1e-3·(r − 1) with a policy-invariant trip correction, so returns fall in about [−12, 0] | shared |
| 5 | Best and final checkpoints saved and both evaluated; best episode reported; same validation episodes; per-seed CSVs | shared |
| 6 | (d) axis overlap fixed; (a) symlog; mean ± 95 % CI + per-seed lines; (g) zoom panels for the first 1 s after each of the four transitions; DDPG "critic Q"; new Fig. 8 | shared |
| 7 | Target smoothing in the normalised action space (verified); σ 0.2 → 0.1, clip 0.5 → 0.3; both critics regress to y = r + γ·min(Q1′, Q2′); d = 2 | TD3 only |
| 8 | D bounds logged; actor LR 1e-4; L2 2e-5 on pre-tanh outputs, applied to **both** agents because it is a generic regulariser, not a TD3 component | shared |
| 9–10 | Single critic kept; only the shared fixes | DDPG |

**Three further shared fixes came out of the pilot runs (seed 0, 200 episodes):**

1. **Weight decay removed.** Coupled L2 inside Adam shrinks every weight by
   about the learning rate per step whenever the loss gradient is small. In
   the **previous** run, 29 % (DDPG) and 51 % (TD3) of critic weights had
   already collapsed to ~1e-30. With the scaled reward, 56–89 % of all
   weights collapsed by episode 260. After the change, none collapse.
2. **Pre-tanh L2 lowered from 1e-4 to 2e-5.** At 1e-4 its gradient was
   28–42 % of the Q-term's, enough to pull J and D toward mid-range, which is
   a form of hard-coding. At 2e-5 it is about 1–2 %.
3. **Adam ε lowered from 1e-8 to 1e-10.** With the scaled reward, the critic's
   gradient RMS (~1e-7) was close to ε, which damped its updates.

## Item 3: the J spike at contingency release

**No state discontinuity.** The load ramps over 0.1 s, and every observed
feature changes smoothly.

**The cause was the reward's RoCoF term.** It used the instantaneous RoCoF
with a 50 ms filter:
- during the release ramp it reached 1.67 Hz/s, costing −3.9 to −7.0 per
  step;
- at the same moment the 500 ms relay window, which is the Eq. (20)
  quantity and the reported metric, read 0.28 Hz/s;
- the observed RoCoF lags by about 40 ms.

So the agent learned to throw a large J at the transition to suppress a
transient the relay never sees. The reward now uses the relay window.

**Result** (best actors, J peak in the first 1 s after release minus the
mean J of the second before it, five test scenarios × 10 seeds):

| | Before (as deployed) | After |
|---|---|---|
| DDPG | +2.66 s | **+0.50 s** |
| TD3 | +2.69 s | **+0.55 s** |

## Items 1, 2, 8: chattering and bounds (best actors, test scenarios)

"Before" = the previous run's actors as deployed (no actuator filter).

| | DDPG before | DDPG after | TD3 before | TD3 after |
|---|---|---|---|---|
| Quiet-period \|ΔJ\| per step (s) | 0.125 | **0.016** | 0.115 | **0.026** |
| Quiet-period \|ΔD\| per step (pu) | 0.656 | **0.282** | 0.536 | **0.148** |
| D std during contingency 1 (pu) | 3.03 | 3.00 | 2.46 | **1.87** |
| J at lower bound, whole episode (%) | 63.8 | 59.4 | 63.7 | **33.7** |
| J at lower bound, during contingency 1 (%) | 84.1 | 70.4 | 84.9 | **44.4** |
| Mean J during contingency 1 (s) | 0.26 | 0.38 | 0.18 | 0.46 |
| J at upper bound / D at either bound (%) | 0 / – | 0 / 7.1 | 0 / – | 0 / 7.7 |

**What these numbers mean:**

- **Chattering.** Most of the reduction comes from the actuator filter.
  Running the *old* actors through the new filter gives |ΔJ| 0.02 and |ΔD|
  0.10–0.11, which is as good as or better than the new actors. So the
  policies themselves do not chatter less. The likely cause is the
  observation normalisation, which amplifies PLL noise in quiet periods by
  up to 20× (the std floor). Fig. 5(h) still shows visible J/D oscillation
  during contingency 1 for the representative TD3 seed.
- **Inertia collapse.** Reduced for TD3: J at its lower bound drops from 85 %
  to 44 % of contingency-1 steps. For DDPG it barely changes (84 % → 70 %).
  J stays small (mean 0.4–0.5 s during events) because damping acts
  through the same converter almost as fast as inertia and costs 8× less
  headroom per unit (Eq. 22). Both tuned baselines also choose J = 0.
- **D drift.** D does not run to its upper bound (D_hi ≈ 0 in training, and
  D is at a bound in 5–8 % of test steps, mostly the lower bound). The D seed
  band is still wide for DDPG.

## Summary table (best = deployed, validation-selected checkpoint)

| Metric | DDPG test | TD3 test | t | DDPG stress | TD3 stress | t |
|---|---|---|---|---|---|---|
| IAE (Hz·s) | 2.320 ± 0.224 | **1.989 ± 0.094** | −3.08 | 2.523 ± 0.170 | **2.261 ± 0.080** | −3.15 |
| ISE (Hz²·s) | 0.434 ± 0.092 | **0.303 ± 0.026** | −3.10 | 0.483 ± 0.069 | **0.374 ± 0.020** | −3.45 |
| ITAE (Hz·s²) | 33.21 ± 3.75 | **28.18 ± 1.90** | −2.71 | 36.16 ± 3.18 | **31.96 ± 1.73** | −2.62 |
| Settling (s) | 0.340 ± 0.140 | 0.254 ± 0.104 | −1.12 | 0.289 ± 0.093 | 0.205 ± 0.078 | −1.56 |
| Overshoot (%) | 27.6 ± 4.4 | 26.2 ± 3.1 | −0.61 | 20.9 ± 2.7 | 21.2 ± 2.3 | +0.18 |
| Nadir (Hz) | 49.742 ± 0.044 | **49.793 ± 0.014** | +2.52 | 49.723 ± 0.040 | **49.774 ± 0.010** | +2.83 |
| Peak RoCoF (Hz/s) | 0.570 ± 0.086 | **0.455 ± 0.020** | −2.96 | 0.621 ± 0.072 | **0.512 ± 0.017** | −3.31 |
| Reserve (pu) | 0.233 ± 0.031 | 0.233 ± 0.020 | +0.01 | 0.268 ± 0.024 | 0.270 ± 0.018 | +0.15 |
| At bounds (%) | 64.2 ± 16.6 | **38.4 ± 10.7** | −2.95 | 65.3 ± 14.2 | **44.5 ± 10.3** | −2.69 |
| Critic bias Q − G (learner units) | +0.116 ± 0.063 | −0.059 ± 0.011 | | | | |

Final checkpoints, stress test: IAE 3.842 ± 0.886 (DDPG) vs 3.068 ± 0.446
(TD3), t = −1.76. Critic bias at episode 1000: DDPG +79 ± 89 (+3.9 to +400
by seed), TD3 −0.16 ± 0.05.

**Best-checkpoint episodes:**
- DDPG: 150, 50, 170, 300, 100, 80, 100, 90, 100, 90 (median 100).
- TD3: 360, 140, 160, 260, 390, 400, 200, 330, 260, 330 (median 295).

## Findings, as they came out

1. **TD3 now beats DDPG significantly on regulation:**
   - IAE −14 % (test) and −10 % (stress), |t| ≈ 3.1;
   - ISE, ITAE, nadir and RoCoF are also significantly better;
   - reserve is equal.

   DDPG does not win any metric significantly. In the previous run the two
   were indistinguishable.
2. **DDPG's critic diverges after about episode 300** on every seed. The
   bias goes from ≈ +0.1 at the selected checkpoint to +3.9 to +400 at
   episode 1000, against Monte-Carlo returns of about −0.5. Gradient
   clipping, the lower learning rates and reward scaling did not prevent
   this. Validation-based selection hides most of it: the deployed DDPG
   actors come from episodes 50–300. This is the overestimation TD3's twin
   critics are designed to stop, and TD3's own bias stays small and negative
   (−0.06 selected, −0.16 final).
3. **Both deployed agents regulate worse than in the previous run:**

   | | Previous run | This run |
   |---|---|---|
   | TD3 test IAE | 1.857 | 1.989 |
   | DDPG test IAE | 1.884 | 2.320 |
   | TD3 stress IAE | 2.161 | 2.261 |
   | DDPG stress IAE | 2.222 | 2.523 |

   Against the baselines (one-sample t):
   - **Tuned constant controller:** TD3 is now significantly worse on the
     stress test (IAE +3.7 %, t = +2.3); previously it matched it. DDPG is
     +15.7 % (t = +4.6).
   - **Rule-based controller:** TD3 matches it on IAE (−0.9 %, n.s.) and has
     lower RoCoF (−11.8 %, t = −9.0). DDPG is worse (+10.6 %, t = +3.2).
   - **Headroom:** the saving against the tuned constant controller holds,
     at −21 to −30 % on all seeds.

   This run changed several things at once, so it does not isolate the
   cause. The candidates are:
   - the changed objective (RoCoF term, rate penalty);
   - observation normalisation;
   - the early checkpoints.

   An ablation (one change at a time, 3 seeds each) would identify it.
4. **The previous run was affected by weight-decay collapse:** 29–51 % of
   critic weights were dead. Results built on that run (including the
   current manuscript) used partly collapsed critics.
