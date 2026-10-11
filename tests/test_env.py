"""Physics, metric and data-split checks (no training required)."""
import numpy as np
import pytest

from vsg_rl import config as C
from vsg_rl.baselines import AdaptiveRulePolicy, FixedPolicy, validation_episodes
from vsg_rl.env import MicrogridVSGEnv
from vsg_rl.evaluate import compute_metrics, stress_episodes
from vsg_rl.evaluate import test_episodes as _test_episodes
from vsg_rl.models import BESS, WindTurbine


def rollout(J, D, scenario="combined", seed=7):
    return MicrogridVSGEnv(scenario).rollout(FixedPolicy(J, D), seed=seed)


def test_no_vsg_is_really_zero():
    rec = rollout(0.0, 0.0)
    assert rec["J"].max() == 0.0 and rec["D"].max() == 0.0
    assert np.allclose(rec["P_vsg"], 0.0)
    assert compute_metrics(rec)["reserve_pu"] == 0.0


def test_headroom_formula_eq22():
    # 0.08 J + 0.01 D per unit at 50 Hz
    rec = rollout(1.0, 10.0, scenario="clear")
    assert np.allclose(rec["h_req"], 0.18)
    m = compute_metrics(rec)
    assert m["derate_pct"] == 0.0 and abs(m["reserve_pu"] - 0.18) < 1e-9


def test_infeasible_gains_are_derated_to_available_headroom():
    rec = rollout(15.0, 60.0)
    assert (rec["h_req"] > rec["h_avail"]).all()
    delivered = 0.08 * rec["J_eff"] + 0.01 * rec["D_eff"]
    assert np.allclose(delivered, rec["h_avail"], atol=1e-9)


def test_bess_power_includes_droop_and_respects_rating():
    rec = rollout(0.0, 0.0)
    # no phantom source: BESS = schedule + droop + VSG (VSG zero here)
    assert np.allclose(rec["P_bess"], rec["P_agc"] + rec["P_droop"], atol=5e3)
    assert np.abs(rec["P_bess"]).max() <= C.S_BASE + 1e-6


def test_vsg_improves_frequency():
    none, vsg = compute_metrics(rollout(0, 0)), compute_metrics(rollout(1, 20))
    assert vsg["iae"] < none["iae"] and vsg["nadir_hz"] > none["nadir_hz"]


def test_overshoot_measures_contingency1_only():
    rec = rollout(1.0, 20.0)
    m = compute_metrics(rec)
    a2 = rec["event_windows"][-1][0]
    t, f = rec["t"], rec["f"]
    w1 = (t >= rec["event_windows"][0][0]) & (t < a2)
    i = np.where(w1)[0][np.argmin(f[w1])]
    expected = max(0.0, f[(t >= t[i]) & (t < a2)].max() - C.F_NOM)
    assert abs(m["overshoot_hz"] - expected) < 1e-12
    assert m["zenith_hz"] > C.F_NOM       # contingency 2 is over-frequency


def test_bess_discharge_reduces_soc():
    b = BESS()
    b.reset(0.5)
    b.apply(1e6, 60.0)
    assert b.soc < 0.5


def test_wind_turbine_rated_power():
    wt = WindTurbine()
    assert abs(wt.power_static(11.5) - 500e3) < 1e3


def test_rollout_is_deterministic():
    a, b = rollout(2, 20, "cloud", 3), rollout(2, 20, "cloud", 3)
    assert np.array_equal(a["f"], b["f"])


def test_observation_contains_actuator_state():
    env = MicrogridVSGEnv("clear")
    env.reset(seed=0)
    s, *_ = env.step([3.0, 30.0, 8.0])
    assert s.shape == (C.STATE_DIM,)
    assert abs(s[10] - 3.0 / C.J_MAX) < 1e-6 and abs(s[11] - 30.0 / C.D_MAX) < 1e-6


def test_adaptive_rule_raises_inertia_only_when_deviation_grows():
    p = AdaptiveRulePolicy(J0=0.5, kJ=5.0, D0=20.0, kD=40.0)
    s = np.zeros(C.STATE_DIM, dtype=np.float32)
    s[0], s[1] = -0.4, -0.5          # falling and still falling
    assert p(s)[0] > 0.5
    s[1] = +0.5                      # falling but recovering
    assert p(s)[0] == 0.5


def test_data_splits_do_not_overlap():
    val = {seed for _, seed in validation_episodes()}
    stress = {seed for _, _, seed in stress_episodes()}
    test = {seed for _, _, seed in _test_episodes()}
    assert not (val & stress) and not (val & test) and not (stress & test)
    # training episode seeds are run_seed * 100_000 + episode
    assert all(not (s * 100_000 <= v < s * 100_000 + C.EPISODES)
               for s in C.DEFAULT_SEEDS for v in val | stress | test)


@pytest.mark.parametrize("cap", [7, 1000, 200_000])
def test_sumtree_vectorised_matches_scalar(cap):
    pytest.importorskip("torch")
    from vsg_rl.agents import SumTree
    rng = np.random.default_rng(0)
    a, b = SumTree(cap), SumTree(cap)
    for x in rng.uniform(0.1, 3, min(cap, 3000)):
        a.add(x); b.add(x)
    idx = np.unique(rng.integers(0, min(cap, 3000), 200))
    newp = rng.uniform(0.1, 5, len(idx))
    for i, q in zip(idx, newp):
        a.update(int(i), q)
    b.update_batch(idx, newp)
    assert np.allclose(a.tree, b.tree)
    vals = rng.uniform(0, a.total(), 300)
    assert (np.array([a.sample(v) for v in vals]) == b.sample_batch(vals)).all()


# ---------------------------------------------------------------- RL fixes
def test_rocof_reward_uses_relay_window():
    """The RoCoF term must use the 500 ms relay-window value (Eq. 20 quantity),
    not the unobservable 50 ms-filtered instantaneous RoCoF, which spikes far
    above the window value during a 0.1 s load ramp."""
    env = MicrogridVSGEnv("combined")
    env.reset(seed=C.TEST_SEED)
    pol = FixedPolicy(0.5, 20.0, 14.0)
    inst, win = [], []
    while True:
        _, _, done, _ = env.step(pol(None))
        if 6.0 < env.t < 6.3:
            inst.append(abs(env.rocof_filt)); win.append(abs(env.rocof_meas))
        if done:
            break
    assert max(inst) > 2 * max(win)            # the mismatch that caused the J spike
    import inspect
    src = inspect.getsource(MicrogridVSGEnv._reward)
    assert "rocof_meas" in src and "rocof_filt" not in src


def test_learner_reward_shift_is_policy_invariant():
    """Shift by -R_ALIVE per step plus -R_ALIVE/(1-gamma) on a trip moves the
    discounted value of every state by the same constant."""
    from vsg_rl.train import discounted_returns, learner_reward
    g = C.GAMMA
    r_env = np.array([1.0, 0.4, -2.0, 0.9])
    alive = discounted_returns(learner_reward(r_env, False), g)[0] / C.REWARD_SCALE \
        - discounted_returns(r_env, g)[0]
    r_trip = np.array([1.0, -100.0])
    lr = np.array([float(learner_reward(r_trip[0], False)),
                   float(learner_reward(r_trip[1], True))])   # per step, as in training
    trip = discounted_returns(lr, g)[0] / C.REWARD_SCALE - discounted_returns(r_trip, g)[0]
    # infinite-horizon shift is -1/(1-g); a full episode sees the truncated
    # sum, a tripped one the exact constant
    assert abs(trip - (-1.0 / (1 - g))) < 1e-6
    assert alive < 0 and abs(alive - (-(1 - g ** 4) / (1 - g))) < 1e-6


def test_rocof_stress_draws_are_identical_for_both_algorithms():
    from vsg_rl.train import rocof_stress_overrides
    a = [rocof_stress_overrides(3, ep, 1000) for ep in range(1000)]
    b = [rocof_stress_overrides(3, ep, 1000) for ep in range(1000)]
    assert a == b
    assert not any(a[:300])                             # none in stage 1
    frac = np.mean([bool(x) for x in a[600:]])
    assert 0.2 < frac < 0.4
    env = MicrogridVSGEnv("cloud", stochastic=True)
    env.reset(seed=1, overrides=dict(H_sys=0.2, step_frac=0.3))
    assert env.H_sys == 0.2 and env.step_frac == 0.3
    env.reset(seed=1)
    assert env.H_sys == C.H_SYS


def test_action_filter_smooths_commands():
    env = MicrogridVSGEnv("clear")
    env.reset(seed=0)
    env.step([1.0, 10.0, 8.0])
    env.step([10.0, 50.0, 8.0])                         # big jump
    alpha = env.dt / (C.ACTION_FILTER_TAU + env.dt)
    assert abs(env._cmd_filt[0] - (1.0 + alpha * 9.0)) < 1e-9
    assert env.J < 10.0


def test_obs_norm_snapshot_roundtrip():
    from vsg_rl.agents import make_agent
    ag = make_agent("ddpg", seed=0)
    rng = np.random.default_rng(0)
    for _ in range(50):
        ag.observe(rng.normal(2.0, 3.0, C.STATE_DIM))
    s = rng.normal(size=C.STATE_DIM).astype(np.float32)
    a1 = ag.policy()(s)
    ag2 = make_agent("ddpg", seed=1)
    ag2.load_actor_snapshot(ag.actor_snapshot())
    assert np.allclose(ag2.policy()(s), a1)
    assert abs(ag.obs_norm.mean.mean() - 2.0) < 1.0


def test_bound_fractions():
    from vsg_rl.evaluate import bound_fractions
    b = bound_fractions([C.J_MIN, C.J_MIN, 5.0, C.J_MAX], [C.D_MAX, 30.0, 30.0, 30.0])
    assert b["J_lo"] == 0.5 and b["J_hi"] == 0.25 and b["D_hi"] == 0.25 and b["D_lo"] == 0.0
