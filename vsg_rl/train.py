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
* Both algorithms see identical scenario sequences, episode seeds and
  RoCoF-stress draws.
* The learner is trained on a scaled, shifted reward (``learner_reward``);
  critic bias is therefore reported in learner units.  Validation return and
  every table use the unscaled environment reward.
* Each run saves the best-validated AND the final actor, and exports per-seed
  CSVs of the training and validation histories.
"""
import csv
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
from .evaluate import bound_fractions
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


def curriculum_stage(ep: int, episodes: int) -> int:
    frac = (ep + 1) / max(episodes, 1)
    for i, (threshold, _) in enumerate(C.CURRICULUM):
        if frac <= threshold:
            return i
    return len(C.CURRICULUM) - 1


def curriculum_scenarios(ep: int, episodes: int):
    return C.CURRICULUM[curriculum_stage(ep, episodes)][1]


def rocof_stress_overrides(seed: int, ep: int, episodes: int) -> dict:
    """RoCoF-stress draw for one training episode.  Depends only on (seed,
    episode), so DDPG and TD3 get identical episodes and resuming is exact."""
    p = C.ROCOF_STRESS_PROB[min(curriculum_stage(ep, episodes), len(C.ROCOF_STRESS_PROB) - 1)]
    rng = np.random.default_rng([seed, ep, 17])
    if rng.uniform() >= p:
        return {}
    return dict(H_sys=float(rng.uniform(*C.ROCOF_STRESS_H)),
                step_frac=float(rng.uniform(*C.ROCOF_STRESS_STEP)))


def learner_reward(r, tripped):
    """Scaled, shifted reward the networks are trained on (see config)."""
    out = C.REWARD_SCALE * (np.asarray(r, dtype=float) - (C.R_ALIVE if C.REWARD_SHIFT else 0.0))
    if tripped:
        out = out - trip_shift()
    return out


def trip_shift() -> float:
    """Shift owed for the steps a trip cuts off: sum_{i>=1} gamma^i R_ALIVE,
    so every state's discounted value moves by exactly -R_ALIVE/(1-gamma)."""
    if not C.REWARD_SHIFT:
        return 0.0
    return C.REWARD_SCALE * C.R_ALIVE * C.GAMMA / (1.0 - C.GAMMA)


def discounted_returns(rewards, gamma):
    g = np.zeros(len(rewards))
    acc = 0.0
    for i in range(len(rewards) - 1, -1, -1):
        acc = rewards[i] + gamma * acc
        g[i] = acc
    return g


def validate(agent) -> dict:
    """Validation return (model selection) + critic calibration.  The
    Monte-Carlo return is computed from the learner reward, the quantity the
    critic estimates, so Q - G is a like-for-like bias."""
    env = MicrogridVSGEnv(stochastic=True, split="val")
    pol = agent.policy()
    rets, q1s, qmins, mcs, nad, roc, Js, Ds = [], [], [], [], [], [], [], []
    for sc, seed in validation_episodes():
        env.scenario = sc
        rec = env.rollout(pol, seed=seed, keep_states=True)
        rets.append(rec["total_reward"])
        n = rec["n_valid"]
        rl = learner_reward(rec["reward"][:n], False)
        if rec["tripped"]:
            rl[-1] -= trip_shift()
        g = discounted_returns(rl, C.GAMMA)
        m = max(1, n - MC_TAIL) if not rec["tripped"] else n
        q = agent.q_policy(rec["states"][:m])
        q1s.append(q["q1"]); qmins.append(q["q_min"]); mcs.append(g[:m])
        nad.append(float(rec["f"][:n].min())); roc.append(float(np.abs(rec["rocof"][:n]).max()))
        Js.append(rec["J"][:n]); Ds.append(rec["D"][:n])
    q1, qmin, mc = (np.concatenate(x) for x in (q1s, qmins, mcs))
    b = bound_fractions(np.concatenate(Js), np.concatenate(Ds))
    return dict(val_return=float(np.mean(rets)), q_mean=float(q1.mean()),
                q_min_mean=float(qmin.mean()), mc_mean=float(mc.mean()),
                q_bias=float((q1 - mc).mean()), q_min_bias=float((qmin - mc).mean()),
                val_nadir=float(np.mean(nad)), val_rocof=float(np.mean(roc)),
                val_J=float(np.mean(np.concatenate(Js))), val_D=float(np.mean(np.concatenate(Ds))),
                val_J_lo=b["J_lo"], val_D_hi=b["D_hi"])


def _paths(algo, seed):
    d = C.out_path("checkpoints", "x")
    d = os.path.dirname(d)
    return (os.path.join(d, f"{algo}_seed{seed}_checkpoint.pt"),
            os.path.join(d, f"{algo}_seed{seed}_best_actor.pt"),
            os.path.join(d, f"{algo}_seed{seed}_history.json"))


def _final_path(algo, seed):
    return os.path.join(os.path.dirname(_paths(algo, seed)[0]), f"{algo}_seed{seed}_final_actor.pt")


TRAIN_CSV_KEYS = ["reward", "reward_learner", "nadir", "rocof", "J_mean", "D_mean", "Kq_mean",
                  "J_lo", "J_hi", "D_lo", "D_hi", "critic_loss", "actor_loss", "actor_q_term",
                  "q1", "q2", "noise", "lr", "scenario", "rocof_stress", "H_sys", "step_frac"]
VAL_CSV_KEYS = ["val_return", "q_mean", "q_min_mean", "mc_mean", "q_bias", "q_min_bias",
                "val_nadir", "val_rocof", "val_J", "val_D", "val_J_lo", "val_D_hi"]


def export_history_csv(algo, seed, hist) -> None:
    """Per-seed CSVs: one row per training episode, one per validation."""
    d = os.path.dirname(_paths(algo, seed)[0])
    with open(os.path.join(d, f"{algo}_seed{seed}_training.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["episode"] + TRAIN_CSV_KEYS)
        for i in range(len(hist["reward"])):
            w.writerow([i + 1] + [hist[k][i] if i < len(hist.get(k, [])) else ""
                                  for k in TRAIN_CSV_KEYS])
    with open(os.path.join(d, f"{algo}_seed{seed}_validation.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["episode", "is_best"] + VAL_CSV_KEYS)
        for i, ep in enumerate(hist["eval_ep"]):
            w.writerow([ep, int(ep == hist.get("best_episode"))]
                       + [hist[k][i] for k in VAL_CSV_KEYS])


def train_agent(algo: str, seed: int = 0, episodes: int | None = None,
                max_steps: int | None = None, resume: bool = True, log_every: int = 10):
    episodes = episodes or C.EPISODES
    max_steps = max_steps or C.max_steps()
    t0 = time.time()
    ckpt_path, best_path, hist_path = _paths(algo, seed)
    set_global_seed(seed)
    agent = make_agent(algo, seed=seed)
    env = MicrogridVSGEnv(stochastic=True, split="train")

    keys = TRAIN_CSV_KEYS + ["eval_ep"] + VAL_CSV_KEYS
    hist = {k: [] for k in keys}
    best_score, best_state, start_ep, total_steps = -np.inf, None, 0, 0
    best_ep = None

    if resume and os.path.exists(ckpt_path):
        try:
            ck = torch.load(ckpt_path, map_location="cpu", weights_only=False)
            agent.load_state_dict(ck["agent"])
            hist, start_ep = ck["history"], ck["episode"]
            best_score, best_state = ck["best_score"], ck["best_state"]
            total_steps = ck["total_steps"]
            best_ep = ck.get("best_episode")
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
        ovr = rocof_stress_overrides(seed, ep, episodes)
        state = env.reset(seed=seed * 100_000 + ep, overrides=ovr)
        agent.observe(state)
        ep_r, ep_rl, nadir, rocof = 0.0, 0.0, C.F_NOM, 0.0
        Js, Ds, Ks, cl, al, aq, q1s, q2s = [], [], [], [], [], [], [], []
        for _ in range(max_steps):
            if total_steps < C.WARMUP_STEPS:
                a_norm = agent.rng.uniform(-1.0, 1.0, agent.a_dim).astype(np.float32)
            else:
                a_norm = agent.act_norm(state, noise)
            nxt, r, done, info = env.step(to_env_action(a_norm))
            r_l = float(learner_reward(r, info["tripped"]))
            # bootstrap through time-limit truncation; stop only on a trip
            agent.buffer.push(state, a_norm, r_l, nxt, info["tripped"])
            agent.observe(nxt)
            state = nxt
            total_steps += 1
            ep_r += r
            ep_rl += r_l
            nadir = min(nadir, info["f"])
            rocof = max(rocof, abs(info["rocof"]))
            Js.append(info["J"]); Ds.append(info["D"]); Ks.append(info["Kq"])
            if total_steps >= C.WARMUP_STEPS and total_steps % C.UPDATE_EVERY == 0:
                st = agent.update()
                if st:
                    cl.append(st["critic_loss"])
                    if "actor_loss" in st:
                        al.append(st["actor_loss"])
                        aq.append(agent.last_q_term)
                    q1s.append(st["q1"]); q2s.append(st["q2"])
            if done:
                break

        m = lambda x: float(np.mean(x)) if x else float("nan")
        bf = bound_fractions(Js, Ds)
        for k_, v in (("reward", ep_r), ("reward_learner", ep_rl), ("nadir", nadir),
                      ("rocof", rocof), ("J_mean", m(Js)), ("D_mean", m(Ds)), ("Kq_mean", m(Ks)),
                      ("J_lo", bf["J_lo"]), ("J_hi", bf["J_hi"]), ("D_lo", bf["D_lo"]),
                      ("D_hi", bf["D_hi"]), ("critic_loss", m(cl)), ("actor_loss", m(al)),
                      ("actor_q_term", m(aq)), ("q1", m(q1s)), ("q2", m(q2s)), ("noise", noise),
                      ("lr", lr_a), ("scenario", sc), ("rocof_stress", int(bool(ovr))),
                      ("H_sys", env.H_sys), ("step_frac", env.step_frac)):
            hist[k_].append(v)

        if (ep + 1) % C.EVAL_EVERY == 0 or ep == episodes - 1:
            v = validate(agent)
            hist["eval_ep"].append(ep + 1)
            for k_ in VAL_CSV_KEYS:
                hist[k_].append(v[k_])
            if v["val_return"] > best_score:
                best_score = v["val_return"]
                best_state = agent.actor_snapshot()
                best_ep = ep + 1
            torch.save({"agent": agent.state_dict(), "history": hist, "episode": ep + 1,
                        "best_score": best_score, "best_state": best_state,
                        "best_episode": best_ep, "total_steps": total_steps}, ckpt_path)

        if (ep + 1) % log_every == 0:
            el = time.time() - t0
            eta = el / max(ep + 1 - start_ep, 1) * (episodes - ep - 1)
            val = hist["val_return"][-1] if hist["val_return"] else float("nan")
            log(f"  [{algo} s{seed}] ep {ep+1:4d}/{episodes} | R {np.mean(hist['reward'][-log_every:]):8.1f}"
                f" ({np.mean(hist['reward_learner'][-log_every:]):6.2f})"
                f" | nadir {np.mean(hist['nadir'][-log_every:]):.3f} | J {hist['J_mean'][-1]:5.2f}"
                f" D {hist['D_mean'][-1]:5.1f} | Jlo {hist['J_lo'][-1]:.2f} Dhi {hist['D_hi'][-1]:.2f}"
                f" | val {val:8.1f} | {el:5.0f}s ETA {eta:5.0f}s")

    conv_ep, conv_val = convergence_episode(hist["eval_ep"], hist["val_return"])
    hist["converged_at"], hist["converged_value"] = conv_ep, conv_val
    hist["best_val_return"] = best_score
    hist["best_episode"] = best_ep
    torch.save(agent.actor_snapshot(), _final_path(algo, seed))       # final checkpoint
    if best_state is not None:
        agent.load_actor_snapshot(best_state)
    torch.save(agent.actor_snapshot(), best_path)                     # best validated
    with open(hist_path, "w") as fh:
        json.dump(hist, fh)
    export_history_csv(algo, seed, hist)
    log(f"[{algo.upper()} s{seed}] done in {time.time()-t0:.0f}s | best val return "
        f"{best_score:.1f} at episode {best_ep} | converged at {conv_ep}")
    return agent, hist


def load_agent(algo: str, seed: int, which: str = "best"):
    """``which`` = "best" (validation-selected) or "final" (last episode)."""
    _, best_path, hist_path = _paths(algo, seed)
    path = best_path if which == "best" else _final_path(algo, seed)
    if not os.path.exists(path):
        return None, {}
    agent = make_agent(algo, seed=seed)
    agent.load_actor_snapshot(torch.load(path, map_location="cpu", weights_only=False))
    hist = {}
    if os.path.exists(hist_path):
        with open(hist_path) as fh:
            hist = json.load(fh)
    return agent, hist


# ----------------------------------------------------------------
# Parallel multi-seed training
# ----------------------------------------------------------------
_OVERRIDE_KEYS = ("EPISODES", "EVAL_EVERY", "WARMUP_STEPS", "EPISODE_DURATION",
                  "F_NOM", "WEATHER_SOURCE", "OUT_DIR", "N_VAL", "MEASURED_CONFIG",
                  "N_STRESS",
                  # switches used by the ablation study (vsg_rl/ablation.py)
                  "ROCOF_REWARD_WINDOW", "W_ROCOF", "W_ROCOF_HINGE", "W_RATE",
                  "ACTION_FILTER_TAU", "OBS_NORM", "REWARD_SCALE", "REWARD_SHIFT",
                  "ROCOF_STRESS_PROB", "ADAM_EPS", "PER_EPS")


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
