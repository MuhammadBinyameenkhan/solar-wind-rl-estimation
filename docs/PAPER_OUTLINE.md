# Paper plan (recommended framing)

## Recommended framing: feasibility + "when does RL pay off?"

The study's strongest, most defensible result is **not** "RL beats every baseline". It is the following:

> In a realistic low-inertia PV-Wind-BESS-diesel microgrid (grid-forming VSG, secondary control, EMS-committed BESS, real 2024 meteorological data), synthetic-inertia commitments can be made **feasible** at almost no cost through a headroom projection. A simple **oracle bound** shows how little room is left for adaptive (H, D) scheduling: 1–3 % of the cost, under every formulation tested. Multi-seed TD3/DDPG agents, trained as residual policies on a tuned VSG, **do not improve on it**. Their learned deviations make performance worse, and validation-based selection returns the base controller.

This framing:
* keeps the title's core idea ("feasible synthetic inertia") as the positive contribution;
* answers a question reviewers increasingly ask of RL-for-power-systems papers (do you beat a properly tuned baseline?) with a reusable test;
* is fully backed by the code and data in this repository, so every number can be reproduced.

### Title options

1. *Toward Feasible Synthetic Inertia: A Headroom-Constrained Assessment of Reinforcement-Learning VSG Control in a Real-Data PV-Wind-BESS Microgrid* (keeps your title, honest scope)
2. *Does Reinforcement Learning Pay Off for Virtual Synchronous Generator Tuning? A Feasibility-Constrained Study on a Low-Inertia PV-Wind-BESS Microgrid*
3. *Feasible Synthetic Inertia under Headroom Constraints: Oracle Bounds and Reinforcement-Learning Benchmarks for VSG Control*

### Contributions (draft)

1. **Headroom feasibility projection.** Direction-aware bounds on H and D, such that the damping power at the band edge and the inertial power at the RoCoF limit fit within the BESS (SoC-dependent) and de-loaded PV headroom. It is nearly free in performance (tuned VSG −56.86 vs −56.80 on validation) and removes headroom saturation.
2. **Real-data operating envelope.** ERA5 (wind) + NASA POWER (solar) for Nakhon Ratchasima in 2024, with a rule-based EMS committing BESS power, weekly-block train/val/test split, and an adequacy screen.
3. **Oracle bound for adaptive inertia** (`scripts/oracle_test.py`). The gap between the best single fixed VSG and a per-scenario oracle bounds what scenario-level adaptation can gain. It is 1–3 % here, a reusable go/no-go test before training RL.
4. **Rigorous RL benchmark.** TD3 and DDPG as zero-initialised residual policies on the validation-tuned VSG, multiple seeds, a 30 s multi-event grid-code-band formulation, Pareto comparison against the whole fixed-VSG family, and Wilcoxon + Holm tests.
5. **Formulation study** (EXPERIMENTS.md). Seven reward and plant formulations, showing *why* adaptation has little value: strong grid-forming synchronising coupling (the VSG takes ~71 % of any step instantly), secondary control restoring frequency within 10–20 s, and optimal parameters that hardly depend on the operating point.
6. **Train-in-Python, validate-in-Simscape workflow** with exported policies and identical scenarios.

## Section plan

| § | Content | Produced by |
|---|---|---|
| 1 Introduction | Low inertia; VSG; adaptive-VSG and RL claims; the feasibility gap; research questions RQ1–RQ3 | – |
| 2 Related work | PRISMA review (adaptive VSG, RL for virtual inertia, multi-source VSG, PV headroom). Gap table: few studies bound the attainable gain or compare with a *tuned* fixed VSG | your review |
| 3 System & model | Single-line diagram; ratings table; two-machine RMS model; EMS dispatch; BESS secondary control | `docs/METHODOLOGY.md` §1–2 |
| 4 Data | ERA5 + NASA POWER hybrid, low-wind site, density fallback, weekly-block split, load sizing | `docs/DATA.md`, `fig_data_overview` |
| 5 Feasibility projection | Derivation, direction-aware headroom, rate limit; cost-of-feasibility result | `vsg_env.param_bounds`, `fixed_feasible` vs `fixed_tuned` |
| 6 Problem formulation | Multi-event episodes, band reward, fast-power cost; MDP; residual TD3/DDPG | METHODOLOGY §3–4 |
| 7 Results | 7.1 oracle bound (RQ1); 7.2 baselines vs tuned VSG; 7.3 RL learning curves and test results, best vs final checkpoint (RQ2); 7.4 Pareto vs the fixed family; 7.5 feasibility: saturation with/without projection (RQ3); 7.6 formulation study | `oracle_test.py`, `evaluate.py`, `analyze.py`, `pareto.py`, `plot.py` |
| 8 Simscape validation | Fixed VSG and projection on 3–5 scenarios: ranking preserved | `docs/SIMULINK_VALIDATION.md` |
| 9 Discussion | When would RL pay off? Weak synchronising coupling, no fast secondary control, communication delays, scarce headroom relative to events, unknown plant parameters, so run the oracle test first | – |
| 10 Conclusion | – | – |

### Research questions

* **RQ1:** How much can adaptive (H, D) scheduling gain over a tuned fixed VSG, at most? (oracle bound)
* **RQ2:** Do multi-seed TD3/DDPG residual policies realise that gain? (test set, Pareto)
* **RQ3:** What does feasibility cost, and what does it prevent? (projection ablation, saturation)

## Positioning against the closest work

From your review: Oboreh-Snapps et al. (2024), Zhou et al. (2026), and the fuzzy-logic PV-wind-battery VSG paper. Fill in from your notes; nothing here is assumed about their content:

| Paper | Adaptive method | Compared with a *tuned* fixed VSG? | Headroom / SoC feasibility? | Real meteorological data? | Seeds / statistics |
|---|---|---|---|---|---|
| Oboreh-Snapps et al. 2024 | | | | | |
| Zhou et al. 2026 | | | | | |
| Fuzzy PV-wind-battery VSG | fuzzy | | | | |
| **This work** | TD3 / DDPG residual | ✓ (validation-tuned) | ✓ projection | ✓ ERA5 + NASA POWER | ✓ multi-seed, Wilcoxon + Holm, oracle bound |

## Threats to validity (state them)

* **Model:** RMS two-machine model; Simscape validation planned.
* **Load:** synthetic profile (0.3–0.8 MW), sized to firm capacity; a measured profile would strengthen the study.
* **One year and one site:** generalisation to other sites is untested. The pipeline accepts any ERA5/POWER files.
* **The RL result depends on the plant.** The discussion should list the conditions under which the oracle bound grows (§9) rather than claim RL never helps.
* **Training budget:** 3 seeds × 600 episodes in the reported run; `run_all.sh` reproduces 5 × 1000 for the final version.
