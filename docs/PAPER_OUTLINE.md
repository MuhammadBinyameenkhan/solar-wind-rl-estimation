# Paper outline: "Toward Feasible Synthetic Inertia: Reinforcement Learning-Driven Virtual Synchronous Generator Control for Low-Inertia PV-Wind-BESS Microgrids"

## Contribution statement (draft)

1. **Feasibility-constrained synthetic inertia.** The VSG's inertia and damping commitments are projected onto the real-time upward headroom of the BESS (SoC-dependent) and the de-loaded PV, so the agent never schedules inertia that the DC sources cannot deliver (§3.1 of METHODOLOGY).
2. **Multi-source RL-VSG.** One TD3 agent jointly schedules H, D and the PV/BESS allocation α. It exploits slow but free PV headroom together with fast but cycling-costly BESS power.
3. **Real-data operating envelope.** Operating points come from a hybrid ERA5 (wind, air density) and NASA POWER (irradiance, temperature) dataset with a chronological, held-out test period. This replaces the synthetic profiles of earlier work.
4. **Statistically grounded evaluation.** 5 seeds × 1000 episodes; 200 paired held-out scenarios; Wilcoxon signed-rank tests with Holm correction; ablations of the constraint, the allocation action, and TD3 vs DDPG.
5. **Train-in-Python, validate-in-Simscape** workflow, with exported policy weights and identical scenarios (reproducibility).

## Section plan

| § | Content | Source in repo |
|---|---|---|
| 1 Introduction | Low-inertia problem; why VSG; why fixed or heuristic-adaptive parameters fall short; the feasibility gap (inertia promised vs headroom available) | – |
| 2 Related work | PRISMA-style review: (a) adaptive VSG (bang-bang, RoCoF-adaptive, fuzzy), (b) RL for VSG and virtual inertia, (c) multi-source PV-wind-BESS VSG, (d) headroom / de-loaded PV reserve. Gap table: RL × multi-source × headroom constraint | your PRISMA flow diagram + gap table |
| 3 System & modelling | Fig: single-line diagram; Table: ratings (METHODOLOGY §1); equations (§2) | `vsgrl/microgrid.py` |
| 4 Data | ERA5 + NASA POWER hybrid rationale, processing, split; Table: data summary; Fig: data overview | `prepare_data.py`, `fig_data_overview` |
| 5 RL formulation | MDP, projection, reward, TD3; Table: hyper-parameters | METHODOLOGY §3–4 |
| 6 Results | 6.1 learning curves; 6.2 main table + significance; 6.3 time-domain responses (largest step, low-headroom case, over-frequency); 6.4 learned policy vs headroom; 6.5 ablations (E2, E3); 6.6 sensitivity (E4) and robustness (E5) | `results/` |
| 7 Simscape validation | Agreement table and transfer of the controller ranking | SIMULINK_VALIDATION |
| 8 Discussion | Limitations (RMS model, synthetic load if used, single bus, hourly operating points), computational cost, deployability (a 50 ms MLP inference fits in any DSP) | – |
| 9 Conclusion | – | – |

## Positioning against closest work

Your review identified three closest competitors: **Oboreh-Snapps et al. (2024)**, **Zhou et al. (2026)**, and a fuzzy-logic PV-wind-battery VSG paper. For each one, write down what that paper actually covers (fill in from your notes; nothing is assumed here):

| Paper | RL-based? | Multi-source (PV + wind + BESS)? | Explicit headroom/SoC feasibility of H, D? | Real meteorological data? | Multi-seed statistics? |
|---|---|---|---|---|---|
| Oboreh-Snapps et al. 2024 | | | | | |
| Zhou et al. 2026 | | | | | |
| Fuzzy PV-wind-battery VSG | ✗ (fuzzy) | ✓ | | | |
| **This work** | ✓ TD3 | ✓ | ✓ projection + penalty | ✓ ERA5 + NASA POWER | ✓ 5 seeds, Wilcoxon |

Include the fuzzy-logic VSG as an extra baseline if reviewers ask. `vsgrl/controllers.py` shows the interface: a controller only needs `params(obs) → (H, D, α)`.

## Threats to validity (write these honestly)

* **Model fidelity:** RMS model only. Mitigated by the Simscape validation.
* **Load data:** synthetic profile unless a measured one is used. Mitigated by the sensitivity analysis or a measured feeder profile.
* **Adequacy screen:** operating points where no controller survives are excluded. Report the rejection rate.
* **Baseline tuning:** baseline gains are set once from the literature or nominal values, not optimised per scenario. Consider tuning the adaptive baselines on the validation split, with the same budget as RL model selection, to pre-empt the "weak baseline" critique.
* **Reward design:** the weights are a design choice. Report a small weight-sensitivity study if space allows.
