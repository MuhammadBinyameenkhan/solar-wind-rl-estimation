"""
Curriculum training with clean data splits.

* Training episodes are stochastic (randomised weather and contingency).
* Model selection uses the fixed VALIDATION episodes (baselines.validation_
  episodes) -- never the five test scenarios that are reported.
* Every evaluation also measures CRITIC CALIBRATION: the critic's
  Q(s, mu(s)) on the validation states against the Monte-Carlo discounted
  return actually obtained from those states.  This is the quantity the
  paper's "critic bias" discussion needs; the replay-batch mean Q logged by
  the previous version was over old actions and could not support it.
* Both algorithms see identical scenario sequences and episode seeds.
"""
import copy
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import torch

from . import config as C
from .agents import make_agent, to_env_action
from .baselines import validation_episodes
from .env import MicrogridVSGEnv
from .utils import log, set_global_seed

MC_TAIL = 300          # ignore the last steps: gamma^300 ~ 0.05, return-to-go truncated


def convergence_episode(eval_eps, eval_rewards, window=None, tol=None):
    window = window or C.CONV_WINDOW
    tol = tol or C.CONV_TOL
    if len(eval_rewards) < window + 1:
        return None, float("nan")
    r = np.asarray(eval_rewards, dtype=float)
    run = np.array([r[max(0, i - window + 1):i + 1].mean() for i in range(len(r))])
    for i in range(window, len(run)):
        seg = run[i - window + 1:i + 1]
        if (np.abs(np.diff(seg)) / max(abs(run[i]), 1e-9) < tol).all():
            return int(eval_eps[i]), float(run[i])
    return None, float(run[-1])


def curriculum_scenarios(ep: int, episodes: int):
    frac = (ep + 1) / max(episodes, 1)
    for threshold, scenarios in C.CURRICULUM:
        if frac <= threshold:
            return scenarios
    return C.CURRICULUM[-1][1]


def discounted_returns(rewards, gamma):
    g = np.zeros(len(rewards))
    acc = 0.0
    for i in range(len(rewards) - 1, -1, -1):
        acc = rewards[i] + gamma * acc
        g[i] = acc
    return g


def validate(agent) -> dict:
    """Validation return (model selection) + critic calibration."""
    env = MicrogridVSGEnv(stochastic=True, split="val")
    pol = agent.policy()
    rets, q1s, qmins, mcs = [], [], [], []
    for sc, seed in validation_episodes():
        env.scenario = sc
        rec = env.rollout(pol, seed=seed, keep_states=True)
        rets.append(rec["total_reward"])
        n = rec["n_valid"]
        g = discounted_returns(rec["reward"][:n], C.GAMMA)
        m = max(1, n - MC_TAIL) if not rec["tripped"] else n
        q = agent.q_policy(rec["states"][:m])
        q1s.append(q["q1"]); qmins.append(q["q_min"]); mcs.append(g[:m])
    q1, qmin, mc = (np.concatenate(x) for x in (q1s, qmins, mcs))
    return dict(val_return=float(np.mean(rets)), q_mean=float(q1.mean()),
                q_min_mean=float(qmin.mean()), mc_mean=float(mc.mean()),
                q_bias=float((q1 - mc).mean()), q_min_bias=float((qmin - mc).mean()))


def _paths(algo, seed):
    d = C.out_path("checkpoints", "x")
    d = os.path.dirname(d)
    return (os.path.join(d, f"{algo}_seed{seed}_checkpoint.pt"),
            os.path.join(d, f"{algo}_seed{seed}_best_actor.pt"),
            os.path.join(d, f"{algo}_seed{seed}_history.json"))


def train_agent(algo: str, seed: int = 0, episodes: int | None = None,
                max_steps: int | None = None, resume: bool = True, log_every: int = 10):
    episodes = episodes or C.EPISODES
    max_steps = max_steps or C.max_steps()
    t0 = time.time()
    ckpt_path, best_path, hist_path = _paths(algo, seed)
    set_global_seed(seed)
    agent = make_agent(algo, seed=seed)
    env = MicrogridVSGEnv(stochastic=True, split="train")

    keys = ["reward", "nadir", "rocof", "J_mean", "D_mean", "Kq_mean", "critic_loss",
            "actor_loss", "q1", "q2", "scenario", "noise", "lr", "eval_ep",
            "val_return", "q_mean", "q_min_mean", "mc_mean", "q_bias", "q_min_bias"]
    hist = {k: [] for k in keys}
    best_score, best_state, start_ep, total_steps = -np.inf, None, 0, 0

    if resume and os.path.exists(ckpt_path):
        try:
            ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
            agent.load_state_dict(ck["agent"])
            hist, start_ep = ck["history"], ck["episode"]
            best_score, best_state = ck["best_score"], ck["best_state"]
            total_steps = ck["total_steps"]
            log(f"[{algo.upper()} s{seed}] resumed at episode {start_ep}/{episodes} "
                "(replay buffer restarts empty)")
        except Exception as exc:                       # noqa: BLE001
            log(f"[{algo.upper()} s{seed}] checkpoint unreadable ({exc}); fresh start")

    curr_rng = np.random.default_rng(seed)
    for _ in range(start_ep):
        curr_rng.integers(0, 5)

    log(f"[{algo.upper()} s{seed}] training {episodes} episodes x {max_steps} steps")
    for ep in range(start_ep, episodes):
        pool = curriculum_scenarios(ep, episodes)
        sc = pool[int(curr_rng.integers(0, len(pool)))]
        decay = min(1.0, ep / max(C.NOISE_DECAY_FRACTION * episodes, 1))
        noise = C.EXPL_NOISE_START + (C.EXPL_NOISE_END - C.EXPL_NOISE_START) * decay
        agent.set_beta(ep / max(episodes - 1, 1))
        lr_a, lr_c = C.LR_ACTOR, C.LR_CRITIC
        if C.LR_ANNEAL:
            k = 0.5 * (1.0 + np.cos(np.pi * min(1.0, ep / max(episodes, 1))))
            lr_a, lr_c = lr_a * (0.05 + 0.95 * k), lr_c * (0.05 + 0.95 * k)
            agent.set_lr(lr_a, lr_c)

        env.scenario = sc
        state = env.reset(seed=seed * 100_000 + ep)
        ep_r, nadir, rocof = 0.0, C.F_NOM, 0.0
        Js, Ds, Ks, cl, al, q1s, q2s = [], [], [], [], [], [], []
        for _ in range(max_steps):
            if total_steps < C.WARMUP_STEPS:
                a_norm = agent.rng.uniform(-1.0, 1.0, agent.a_dim).astype(np.float32)
            else:
                a_norm = agent.act_norm(state, noise)
            nxt, r, done, info = env.step(to_env_action(a_norm))
            # bootstrap through time-limit truncation; stop only on a trip
            agent.buffer.push(state, a_norm, r, nxt, info["tripped"])
            state = nxt
            total_steps += 1
            ep_r += r
            nadir = min(nadir, info["f"])
            rocof = max(rocof, abs(info["rocof"]))
            Js.append(info["J"]); Ds.append(info["D"]); Ks.append(info["Kq"])
            if total_steps >= C.WARMUP_STEPS and total_steps % C.UPDATE_EVERY == 0:
                st = agent.update()
                if st:
                    cl.append(st["critic_loss"])
                    if "actor_loss" in st:
                        al.append(st["actor_loss"])
                    q1s.append(st["q1"]); q2s.append(st["q2"])
            if done:
                break

        m = lambda x: float(np.mean(x)) if x else float("nan")
        for k_, v in (("reward", ep_r), ("nadir", nadir), ("rocof", rocof),
                      ("J_mean", m(Js)), ("D_mean", m(Ds)), ("Kq_mean", m(Ks)),
                      ("critic_loss", m(cl)), ("actor_loss", m(al)), ("q1", m(q1s)),
                      ("q2", m(q2s)), ("scenario", sc), ("noise", noise), ("lr", lr_a)):
            hist[k_].append(v)

        if (ep + 1) % C.EVAL_EVERY == 0 or ep == episodes - 1:
            v = validate(agent)
            hist["eval_ep"].append(ep + 1)
            for k_ in ("val_return", "q_mean", "q_min_mean", "mc_mean", "q_bias", "q_min_bias"):
                hist[k_].append(v[k_])
            if v["val_return"] > best_score:
                best_score = v["val_return"]
                best_state = copy.deepcopy(agent.actor.state_dict())
            torch.save({"agent": agent.state_dict(), "history": hist, "episode": ep + 1,
                        "best_score": best_score, "best_state": best_state,
                        "total_steps": total_steps}, ckpt_path)

        if (ep + 1) % log_every == 0:
            el = time.time() - t0
            eta = el / max(ep + 1 - start_ep, 1) * (episodes - ep - 1)
            val = hist["val_return"][-1] if hist["val_return"] else float("nan")
            log(f"  [{algo} s{seed}] ep {ep+1:4d}/{episodes} | R {np.mean(hist['reward'][-log_every:]):8.1f}"
                f" | nadir {np.mean(hist['nadir'][-log_every:]):.3f} | J {hist['J_mean'][-1]:5.2f}"
                f" D {hist['D_mean'][-1]:5.1f} | val {val:8.1f} | {el:5.0f}s ETA {eta:5.0f}s")

    conv_ep, conv_val = convergence_episode(hist["eval_ep"], hist["val_return"])
    hist["converged_at"], hist["converged_value"] = conv_ep, conv_val
    hist["best_val_return"] = best_score
    if best_state is not None:
        agent.actor.load_state_dict(best_state)
    torch.save(agent.actor.state_dict(), best_path)
    with open(hist_path, "w") as fh:
        json.dump(hist, fh)
    log(f"[{algo.upper()} s{seed}] done in {time.time()-t0:.0f}s | best val return "
        f"{best_score:.1f} | converged at {conv_ep}")
    return agent, hist


def load_agent(algo: str, seed: int):
    _, best_path, hist_path = _paths(algo, seed)
    if not os.path.exists(best_path):
        return None, {}
    agent = make_agent(algo, seed=seed)
    agent.actor.load_state_dict(torch.load(best_path, map_location="cpu"))
    hist = {}
    if os.path.exists(hist_path):
        with open(hist_path) as fh:
            hist = json.load(fh)
    return agent, hist


# ----------------------------------------------------------------
# Parallel multi-seed training
# ----------------------------------------------------------------
_OVERRIDE_KEYS = ("EPISODES", "EVAL_EVERY", "WARMUP_STEPS", "EPISODE_DURATION",
                  "F_NOM", "WEATHER_SOURCE", "OUT_DIR", "N_VAL", "MEASURED_CONFIG")


def config_overrides() -> dict:
    return {k: getattr(C, k) for k in _OVERRIDE_KEYS}


def _worker(job):
    algo, seed, episodes, max_steps, resume, overrides = job
    for k, v in overrides.items():
        setattr(C, k, v)
    torch.set_num_threads(1)
    train_agent(algo, seed=seed, episodes=episodes, max_steps=max_steps, resume=resume)
    return algo, seed


def train_many(algos, seeds, episodes=None, max_steps=None, resume=True, workers=1):
    jobs = [(a, s, episodes, max_steps, resume, config_overrides())
            for s in seeds for a in algos]
    if workers <= 1:
        for j in jobs:
            _worker(j)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for algo, seed in ex.map(_worker, jobs):
                log(f"[train] finished {algo} seed {seed}")
