import numpy as np
from gymnasium.utils.env_checker import check_env

from vsgrl.agents.td3 import TD3Agent
from vsgrl.controllers import BASELINES
from vsgrl.envs import VSGEnv
from vsgrl.rollout import run_episode


def test_gym_api(cfg, df):
    env = VSGEnv(cfg, df)
    check_env(env, skip_render_check=True)


def test_projection_shrinks_with_headroom(cfg, df):
    env = VSGEnv(cfg, df)
    env.reset(seed=0)
    env.mg.soc = 0.9
    hi = env.param_bounds()
    env.mg.soc = 0.12
    lo = env.param_bounds()
    assert lo[0] < hi[0] and lo[1] < hi[1]
    env.headroom_constraint = False
    assert env.param_bounds() == (cfg["system"]["vsg"]["h_max_s"], cfg["system"]["vsg"]["d_max_pu"])


def test_baselines_run(cfg, df):
    env = VSGEnv(cfg, df, split="test", record_trace=True)
    s = env.sampler.fixed_set("test", 2, 0)
    for name, C in BASELINES.items():
        m, tr = run_episode(env, C(cfg, env), s[0])
        assert np.isfinite(m["return"]) and len(tr) > 0


def test_agent_update_save_load_and_matlab_parity(cfg, df, tmp_path):
    from scipy.io import loadmat, savemat
    env = VSGEnv(cfg, df)
    ag = TD3Agent(env.observation_space.shape[0], 3, cfg["train"], seed=0)
    o, _ = env.reset(seed=1)
    for _ in range(64):
        a = ag.act(o, noise=0.3)
        o2, r, te, tr, _ = env.step(a)
        ag.buffer.add(o, a, r, o2, float(te))
        o = env.reset()[0] if (te or tr) else o2
    assert "critic_loss" in ag.update()
    ag.save(tmp_path / "a.pt")
    ag2 = TD3Agent.load(tmp_path / "a.pt", cfg["train"])
    assert np.allclose(ag.act(o), ag2.act(o))
    # same layout as scripts/export_matlab.py → numpy forward pass must match torch
    layers = [t.numpy().astype(float) for t in ag.actor.state_dict().values()]
    savemat(tmp_path / "p.mat", {f"{'W' if i % 2 == 0 else 'b'}{i // 2 + 1}": l for i, l in enumerate(layers)})
    m = loadmat(tmp_path / "p.mat")
    x = o.astype(float)
    n = len(layers) // 2
    for i in range(1, n + 1):
        x = m[f"W{i}"] @ x + m[f"b{i}"].ravel()
        x = np.maximum(x, 0) if i < n else np.tanh(x)
    assert np.allclose(x, ag.act(o), atol=1e-5)
