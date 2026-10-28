"""TD3 (Fujimoto et al., ICML 2018) and DDPG (Lillicrap et al., ICLR 2016) in PyTorch.

DDPG here is TD3 with the three TD3 ingredients switched off (single critic,
no target-policy smoothing, actor updated every step), so the two algorithms
differ only in those ingredients — a clean ablation.
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def mlp(inp, out, hidden, out_act=None):
    layers, d = [], inp
    for h in hidden:
        layers += [nn.Linear(d, h), nn.ReLU()]
        d = h
    layers.append(nn.Linear(d, out))
    if out_act is not None:
        layers.append(out_act)
    return nn.Sequential(*layers)


class Actor(nn.Module):
    def __init__(self, obs_dim, act_dim, hidden, zero_init=False):
        super().__init__()
        self.net = mlp(obs_dim, act_dim, hidden, nn.Tanh())
        if zero_init:
            # Residual RL: output exactly 0 at start → the untrained policy IS the base controller
            last = self.net[-2]
            nn.init.zeros_(last.weight)
            nn.init.zeros_(last.bias)

    def forward(self, o):
        return self.net(o)


class Critic(nn.Module):
    def __init__(self, obs_dim, act_dim, hidden, twin=True):
        super().__init__()
        self.q1 = mlp(obs_dim + act_dim, 1, hidden)
        self.q2 = mlp(obs_dim + act_dim, 1, hidden) if twin else None

    def forward(self, o, a):
        x = torch.cat([o, a], dim=-1)
        return self.q1(x), (self.q2(x) if self.q2 is not None else None)


class ReplayBuffer:
    def __init__(self, obs_dim, act_dim, size, device):
        self.o = np.zeros((size, obs_dim), np.float32)
        self.a = np.zeros((size, act_dim), np.float32)
        self.r = np.zeros((size, 1), np.float32)
        self.o2 = np.zeros((size, obs_dim), np.float32)
        self.d = np.zeros((size, 1), np.float32)
        self.size, self.ptr, self.n, self.device = size, 0, 0, device

    def add(self, o, a, r, o2, d):
        i = self.ptr
        self.o[i], self.a[i], self.r[i], self.o2[i], self.d[i] = o, a, r, o2, d
        self.ptr = (i + 1) % self.size
        self.n = min(self.n + 1, self.size)

    def sample(self, batch, rng):
        idx = rng.integers(0, self.n, size=batch)
        t = lambda x: torch.as_tensor(x[idx], device=self.device)
        return t(self.o), t(self.a), t(self.r), t(self.o2), t(self.d)


class TD3Agent:
    def __init__(self, obs_dim, act_dim, cfg_train: dict, algo="td3", seed=0):
        c = cfg_train
        self.algo = algo
        self.td3 = algo == "td3"
        self.device = torch.device(c.get("device", "cpu"))
        torch.manual_seed(seed)
        self.rng = np.random.default_rng(seed)
        hidden = list(c["hidden"])
        self.actor = Actor(obs_dim, act_dim, hidden, zero_init=c.get("actor_zero_init", False)).to(self.device)
        self.critic = Critic(obs_dim, act_dim, hidden, twin=self.td3).to(self.device)
        self.actor_t = copy.deepcopy(self.actor)
        self.critic_t = copy.deepcopy(self.critic)
        self.a_opt = torch.optim.Adam(self.actor.parameters(), lr=c["actor_lr"])
        self.c_opt = torch.optim.Adam(self.critic.parameters(), lr=c["critic_lr"])
        self.gamma, self.tau = c["gamma"], c["tau"]
        self.policy_noise = c["policy_noise"] if self.td3 else 0.0
        self.noise_clip = c["noise_clip"]
        self.policy_delay = c["policy_delay"] if self.td3 else 1
        self.batch = c["batch_size"]
        self.act_dim, self.obs_dim = act_dim, obs_dim
        self.buffer = ReplayBuffer(obs_dim, act_dim, int(c["buffer_size"]), self.device)
        self.n_updates = 0
        self.hidden = hidden

    @torch.no_grad()
    def act(self, obs, noise=0.0):
        o = torch.as_tensor(np.asarray(obs, np.float32), device=self.device).unsqueeze(0)
        a = self.actor(o).cpu().numpy()[0]
        if noise > 0:
            a = a + self.rng.normal(0, noise, size=a.shape)
        return np.clip(a, -1.0, 1.0).astype(np.float32)

    def update(self):
        o, a, r, o2, d = self.buffer.sample(self.batch, self.rng)
        with torch.no_grad():
            a2 = self.actor_t(o2)
            if self.policy_noise > 0:
                eps = (torch.randn_like(a2) * self.policy_noise).clamp(-self.noise_clip, self.noise_clip)
                a2 = (a2 + eps).clamp(-1.0, 1.0)
            q1t, q2t = self.critic_t(o2, a2)
            qt = torch.min(q1t, q2t) if q2t is not None else q1t
            y = r + self.gamma * (1.0 - d) * qt
        q1, q2 = self.critic(o, a)
        loss_c = F.mse_loss(q1, y) + (F.mse_loss(q2, y) if q2 is not None else 0.0)
        self.c_opt.zero_grad()
        loss_c.backward()
        self.c_opt.step()
        self.n_updates += 1
        info = {"critic_loss": loss_c.item()}
        if self.n_updates % self.policy_delay == 0:
            loss_a = -self.critic(o, self.actor(o))[0].mean()
            self.a_opt.zero_grad()
            loss_a.backward()
            self.a_opt.step()
            with torch.no_grad():
                for net, tgt in ((self.actor, self.actor_t), (self.critic, self.critic_t)):
                    for p, pt in zip(net.parameters(), tgt.parameters()):
                        pt.mul_(1 - self.tau).add_(self.tau * p)
            info["actor_loss"] = loss_a.item()
        return info

    def save(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save({"actor": self.actor.state_dict(), "critic": self.critic.state_dict(),
                    "obs_dim": self.obs_dim, "act_dim": self.act_dim, "hidden": self.hidden,
                    "algo": self.algo}, path)

    @classmethod
    def load(cls, path, cfg_train):
        ck = torch.load(path, map_location="cpu", weights_only=False)
        c = dict(cfg_train, hidden=ck["hidden"], buffer_size=1)
        ag = cls(ck["obs_dim"], ck["act_dim"], c, algo=ck["algo"])
        ag.actor.load_state_dict(ck["actor"])
        ag.critic.load_state_dict(ck["critic"])
        return ag
