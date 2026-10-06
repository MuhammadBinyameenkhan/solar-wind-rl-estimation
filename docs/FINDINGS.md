# Findings from the corrected 5-seed study

Full tables: [`results/RESULTS.md`](../results/RESULTS.md). Figures: `results/figures/`.
Setup: 5 seeds × {DDPG, TD3} × 1000 episodes; baselines tuned on validation
episodes with the agents' own reward; test = five paper scenarios; stress = 50
held-out randomised episodes. Values are mean ± 95 % CI over seeds.

## 1. What the paper can claim

| Claim | Evidence (test scenarios) |
|---|---|
| Every VSG controller dramatically outperforms no virtual inertia | IAE 8.91 → ≈1.86 Hz·s (−79 %), nadir 48.41 → 49.81 Hz, RoCoF 3.22 → 0.40 Hz/s, below the 2 Hz/s relay limit |
| The paper's high-gain fixed designs are infeasible, and higher gains don't help once feasibility is enforced | Fixed high/max are derated in 100 % of steps; Fixed max is worse than Fixed high (IAE 3.32 vs 2.64) |
| The learned controllers give the **best nadir and RoCoF** | Nadir 49.81 Hz (TD3 49.812 ± 0.006, DDPG 49.807 ± 0.011) vs 49.78–49.79 Hz for the tuned baselines; RoCoF 0.40 ± 0.03 (TD3) vs 0.45 Hz/s |
| The learned controllers reserve **less headroom than the tuned constant controller** at equal IAE | Reserve 0.229 ± 0.037 (TD3), 0.238 ± 0.055 (DDPG) vs 0.299 pu for Fixed tuned (−20 to −23 %); IAE 1.86–1.89 vs 1.86 Hz·s |
| The learned policies are event-triggered | Fig. 5(h): J and D are held low in quiescent periods and raised at contingency onsets |
| DDPG overestimates and TD3 underestimates the true return | At episode 1000, critic Q(s, μ(s)) minus the Monte-Carlo return G: DDPG +29 to +67; TD3 −217 to −261 (all seeds) |

## 2. What the paper can no longer claim

* **"Both RL controllers outperform every fixed configuration on all error
  integrals."** Against a properly tuned constant controller (J = 0, D = 30,
  Kq = 20) the IAE/ISE/ITAE are statistically indistinguishable: 1.857 ± 0.185
  (DDPG) and 1.888 ± 0.064 (TD3) vs 1.857 Hz·s. On the held-out stress test
  the rule-based adaptive controller is marginally better than both agents.
* **"TD3 outperforms DDPG on all six indices."** No metric differs
  significantly between them (|t| < 1.8 for every metric, test and stress).
  DDPG has slightly higher reward; TD3 has lower variance across seeds.
* **Settling time.** The tuned baselines settle faster (0.08–0.10 s) than the
  agents (0.33–0.49 s), because the agents release damping early to save
  reserve.
* **The −62 % / −24 % IAE improvements and 47 % reserve saving in the
  abstract.** They were measured against a mislabelled "No VSG" (it had D = 5)
  and against infeasible fixed baselines.

## 3. Training dynamics (new, worth a paragraph)

| Run | Best validation checkpoint (episode) | Q − G at episode 1000 |
|---|---|---|
| DDPG seeds 0–4 | 20, 230, 570, 10, 50 | +51, +29, +33, +38, +67 |
| TD3 seeds 0–4 | 50, 70, 90, 90, 70 | −226, −261, −234, −218, −217 |

Validation return peaks early (within ~100 episodes for 8 of 10 runs) and then
declines; TD3's decline follows its critic's growing pessimism (Fig. 5 b, f).
Validation-based model selection is therefore essential, and "train longer"
does not help. This is a genuine and publishable observation about clipped
double-Q learning in this control problem.

## 4. Inertia vs damping

Both tuned baselines chose **J = 0**. On the headroom-weighted objective, a
second of virtual inertia (0.08 pu) buys less than 8 pu of damping. The learned
agents use J only transiently at contingency onsets. The paper's framing
should reflect that the controllers mainly schedule damping, with inertia as a
short transient supplement.

## 5. Suggested reframing

> *A headroom-feasible VSG formulation shows that conventional high-gain
> designs cannot be delivered by the converter. Under this constraint, DDPG
> and TD3 controllers match the regulation of the best tuned constant and
> rule-based controllers while improving nadir and RoCoF and reserving
> ~20 % less converter headroom than the tuned constant design. Critic
> diagnostics confirm DDPG overestimation and TD3 underestimation; the
> latter grows during training and degrades the TD3 policy, making
> validation-based model selection essential.*

## 6. Next experiments that could legitimately improve the RL result

Tune each of these on the validation episodes only, never on the test scenarios:

1. Fix the growing TD3 underestimation: lower critic learning rate, larger
   τ, or remove PER (its IS weighting interacts with the clipped target).
2. Train for ~200 episodes and spend the compute on more seeds instead.
3. Add the previous action to the observation: the effort penalty depends on
   it, but only the slew-limited parameters are observed.
4. Report a reward-weight sensitivity study (W_RESERVE, W_EFFORT), because
   the RL vs baseline trade-off depends on them.
