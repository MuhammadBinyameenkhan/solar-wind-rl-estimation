# Final 10-seed run (setup chosen by the ablation)

Full tables: [`results_measured_final/RESULTS.md`](../results_measured_final/RESULTS.md).

**Setup.**
- Original setup, plus three changes: no weight decay (bug fix),
  relay-window RoCoF reward, and learner reward scaling.
- TD3 target smoothing: σ 0.1, clip 0.3.
- 10 seeds × 1000 episodes; measured weather at its recorded levels.
- Values are the mean ± 95 % CI over seeds. Agents are compared with the
  deterministic baselines by a one-sample t-test (df = 9, |t| > 2.26 ⇒
  significant), and with each other by Welch's t.

## Stress-test IAE across the three runs (deployed best checkpoints)

| | Original run | First fixes run (v2) | **Final run** |
|---|---|---|---|
| TD3 | 2.161 | 2.261 | **2.148 ± 0.067** |
| DDPG | 2.222 | 2.523 | **2.204 ± 0.061** |

Test-scenario IAE: TD3 1.857 / 1.989 / **1.842**; DDPG 1.884 / 2.320 / **1.909**.

## Against the tuned baselines (final run)

| | TD3 stress | DDPG stress | TD3 test | DDPG test |
|---|---|---|---|---|
| IAE vs fixed tuned | −1.5 % (n.s.) | +1.1 % (n.s.) | +6.2 % (t = 3.3) | +10.1 % (t = 5.3) |
| IAE vs rule-based | **−5.7 % (t = −4.4)** | **−3.3 % (t = −2.8)** | −0.8 % (n.s.) | +2.8 % (n.s.) |
| RoCoF vs fixed tuned | **−4.3 % (t = −3.6)** | −1.5 % (n.s.) | +2.0 % | +2.7 % |
| RoCoF vs rule-based | **−9.3 % (t = −8.2)** | **−6.7 % (t = −4.4)** | −3.6 % | −2.9 % |
| Reserve vs fixed tuned | **−19.4 %** | **−20.9 %** | **−24.0 %** | **−27.1 %** |
| Reserve vs rule-based | +7.7 % (t = 2.5) | +5.6 % (t = 2.3) | +3.8 % | −0.4 % |

## DDPG vs TD3

- **No significant difference on any regulation metric** (|t| ≤ 1.44). TD3
  is numerically ahead on IAE, ISE, ITAE, settling and nadir.
- **Critic bias differs significantly** (t = −6.4):
  - selected checkpoints: DDPG +0.049, TD3 −0.061;
  - episode 1000: DDPG +0.13 to +7.9 (still drifting upward, far less than
    the +400 in v2), TD3 −0.04 to −0.22.
- **Best checkpoints:**
  - DDPG: episodes 60–450 (median 165);
  - TD3: episodes 100–350 (median 270).
- **Final checkpoints are worse for both agents** (stress IAE: DDPG 2.98,
  TD3 2.63), so validation-based selection remains essential.

## The original symptoms (test scenarios, best actors)

| | Original | Final run |
|---|---|---|
| J spike at contingency release (s) | 2.66 / 2.69 | 2.29 / 2.75 (DDPG / TD3) |
| Quiet \|ΔJ\| per step (s) | 0.125 / 0.115 | 0.112 / 0.144 |
| Quiet \|ΔD\| per step (pu) | 0.66 / 0.54 | 0.72 / 0.79 |
| J at its lower bound (%) | 64 / 64 | 50 / 50 |

The relay-window reward alone did **not** remove the J spike or the
chattering. In the v2 run those improvements came from the actuator filter,
which the ablation showed costs regulation (+4.5 % TD3, +18 % DDPG stress
IAE). Inertia collapse is only slightly reduced.

**Remaining trade-off.** One option is to add a lighter actuator filter
(τ ≈ 0.02–0.04 s, untested). The other is to report the residual chattering
and release spike as a limitation.

## Ablation: no time feature t/T (seeds 0–2, `results_measured_notime/`)

DDPG and TD3 were retrained with the normalised episode time t/T zeroed in the
observation. Everything else is identical to the final run, including the
tuned baselines. The comparison uses the same three seeds of the final run.

**Pre-event J rise** (mean J in the 1 s before contingency 1, minus the
earlier quiet period; five test windows):

| | DDPG | TD3 |
|---|---|---|
| With t/T | +0.20 s | +0.70 s |
| Without t/T | +0.03 s | +0.03 s |

With t/T, the policies, TD3 in particular, anticipate the fixed contingency
time of the test windows. Without t/T they do not.

**Regulation and reserve, with → without t/T:**

| | DDPG | TD3 |
|---|---|---|
| Test IAE | 2.025 → 1.873 (−7.5 %, t = −2.67) | 1.813 → 1.885 (+4.0 %, n.s.) |
| Stress IAE | −2.2 % (n.s.) | +4.7 % (n.s.) |
| Stress reserve | −1.4 % (n.s.) | −1.3 % (n.s.) |

The reported results do not depend on t/T.
