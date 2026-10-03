"""Training loop for TD3 / DDPG on the VSG environment (one seed)."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

from .agents.td3 import TD3Agent
from .config import resolve_path
from .data.hybrid import load_processed
from .envs import VSGEnv

log = logging.getLogger(__name__)


def evaluate_policy(env: VSGEnv, agent: TD3Agent, scenarios) -> dict:
    rets, devs, rocofs, col = [], [], [], []
    for sc in scenarios:
        obs, _ = env.reset(options={"scenario": sc})
        done = False
        while not done:
            obs, r, term, trunc, info = env.step(agent.act(obs, noise=0.0))
            done = term or trunc
        ep = info["episode"]
        rets.append(ep["return"]); devs.append(ep["max_df_hz"])
        rocofs.append(ep["max_rocof_hz_s"]); col.append(ep["collapsed"])
    return {"val_return": float(np.mean(rets)), "val_max_df_hz": float(np.mean(devs)),
            "val_max_rocof": float(np.mean(rocofs)), "val_collapse_rate": float(np.mean(col))}


def train_one(cfg: dict, algo: str, seed: int, out_dir: Path, df: pd.DataFrame | None = None) -> Path:
    torch.set_num_threads(1)
    t = cfg["train"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "config.yaml", "w") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False)

    df = df if df is not None else load_processed(cfg)
    env = VSGEnv(cfg, df, split="train")
    val_env = VSGEnv(cfg, df, split="val")
    val_set = val_env.sampler.fixed_set("val", t["eval_episodes"], cfg["eval"]["scenario_seed"] + 1)
    agent = TD3Agent(env.observation_space.shape[0], env.action_space.shape[0], t, algo=algo, seed=seed)

    rng = np.random.default_rng(seed)
    obs, _ = env.reset(seed=seed)
    total_steps, best = 0, -np.inf
    rows, vrows = [], []
    t0 = time.time()
    n_ep = t["episodes"]
    for ep in range(1, n_ep + 1):
        if ep > 1:
            obs, _ = env.reset()
        noise = t["expl_noise"] + (t["expl_noise_final"] - t["expl_noise"]) * (ep - 1) / max(n_ep - 1, 1)
        done, Hs, Ds, As, closs = False, [], [], [], []
        while not done:
            if total_steps < t["warmup_steps"]:
                a = rng.uniform(-1, 1, env.action_space.shape).astype(np.float32)
            else:
                a = agent.act(obs, noise=noise)
            obs2, r, term, trunc, info = env.step(a)
            agent.buffer.add(obs, a, r, obs2, float(term))   # truncation bootstraps
            obs, done = obs2, term or trunc
            total_steps += 1
            Hs.append(info["H"]); Ds.append(info["D"]); As.append(info["alpha"])
            if total_steps >= t["warmup_steps"]:
                for _ in range(t["updates_per_step"]):
                    closs.append(agent.update()["critic_loss"])
        e = info["episode"]
        sc = env.scenario
        rows.append({"episode": ep, "steps": total_steps, "return": e["return"], "max_df_hz": e["max_df_hz"],
                     "max_rocof_hz_s": e["max_rocof_hz_s"], "sat_s": e["sat_s"], "collapsed": e["collapsed"],
                     "mean_H": np.mean(Hs), "mean_D": np.mean(Ds), "mean_alpha": np.mean(As),
                     "dist_mw": sc.dist_mw, "critic_loss": np.mean(closs) if closs else np.nan,
                     "noise": noise, "wall_s": time.time() - t0})
        if ep % t["eval_every"] == 0 or ep == n_ep:
            v = evaluate_policy(val_env, agent, val_set)
            v.update({"episode": ep, "steps": total_steps})
            vrows.append(v)
            if v["val_return"] > best:
                best = v["val_return"]
                agent.save(out_dir / "best.pt")
            log.info("[%s seed %d] ep %d/%d  train R=%.2f  val R=%.2f  val |Δf|max=%.3f Hz  (%.0fs)",
                     algo, seed, ep, n_ep, e["return"], v["val_return"], v["val_max_df_hz"], time.time() - t0)
            pd.DataFrame(rows).to_csv(out_dir / "train_log.csv", index=False)
            pd.DataFrame(vrows).to_csv(out_dir / "val_log.csv", index=False)
    agent.save(out_dir / "final.pt")
    with open(out_dir / "summary.json", "w") as fh:
        json.dump({"algo": algo, "seed": seed, "episodes": n_ep, "steps": total_steps,
                   "best_val_return": best, "wall_s": time.time() - t0,
                   "train_scenario_rejection_rate": env.sampler.rejection_rate("train")}, fh, indent=2)
    return out_dir


def run_dir(cfg, algo, seed, tag=None) -> Path:
    return resolve_path(cfg["train"]["out_dir"]) / (tag or algo) / f"seed{seed}"
