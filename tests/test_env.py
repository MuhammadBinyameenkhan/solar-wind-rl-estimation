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
