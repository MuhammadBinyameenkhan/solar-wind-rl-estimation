"""
DDPG and TD3 with SumTree prioritised replay.

The two agents share everything except the three TD3 changes:

    DDPG                          TD3
    1 critic                      2 critics, target = min(Q1, Q2)
    target = Q'(s', mu'(s'))      + clipped Gaussian target-policy smoothing
                                    (normalised action space, sigma 0.1, clip 0.3)
    actor + targets every update  actor + targets every POLICY_FREQ updates

Shared by both: running observation normalisation, PER, gradient-norm
clipping (1.0) on actor and critic, Adam with cosine-annealed learning
rates, Polyak tau, and a small L2 penalty on the actor's pre-tanh output.
"""
import copy

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from . import config as C

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# Weight decay drives many weights into the denormal range during long runs;
# on CPU that made updates ~10x slower by mid-training.  Flushing them to zero
# only affects values below ~1e-38.
torch.set_flush_denormal(True)


def _bounds():
    b = C.action_bounds()
    return (np.array([x[0] for x in b], dtype=np.float32),
            np.array([x[1] for x in b], dtype=np.float32))


def to_env_action(a_norm) -> np.ndarray:
    lo, hi = _bounds()
    a = np.clip(np.asarray(a_norm, dtype=np.float32), -1.0, 1.0)
    return lo + (a + 1.0) * 0.5 * (hi - lo)


# ================================================================
# Observation normalisation (running mean / std, shared by both agents)
# ================================================================
class RunningNorm:
    """Welford running statistics; ``normalize`` uses a std floor and clip."""

    def __init__(self, dim: int):
        self.mean = np.zeros(dim, dtype=np.float64)
        self.var = np.ones(dim, dtype=np.float64)
        self.count = 1e-4

    def update(self, x) -> None:
        x = np.asarray(x, dtype=np.float64).reshape(-1, self.mean.size)
        b_mean, b_var, b_n = x.mean(0), x.var(0), x.shape[0]
        delta = b_mean - self.mean
        tot = self.count + b_n
        self.mean = self.mean + delta * b_n / tot
        m2 = self.var * self.count + b_var * b_n + delta ** 2 * self.count * b_n / tot
        self.var = m2 / tot
        self.count = tot

    def arrays(self):
        std = np.maximum(np.sqrt(self.var), C.OBS_NORM_MIN_STD)
        return self.mean.astype(np.float32), std.astype(np.float32)

    def state_dict(self):
        return dict(mean=self.mean.tolist(), var=self.var.tolist(), count=self.count)

    def load_state_dict(self, sd):
        self.mean = np.asarray(sd["mean"], dtype=np.float64)
        self.var = np.asarray(sd["var"], dtype=np.float64)
        self.count = float(sd["count"])


def normalize_obs(x, mean, std):
    """Works on numpy arrays and torch tensors alike."""
    if mean is None:
        return x
    if isinstance(x, torch.Tensor):
        m = torch.as_tensor(mean, device=x.device)
        sd = torch.as_tensor(std, device=x.device)
        return ((x - m) / sd).clamp(-C.OBS_NORM_CLIP, C.OBS_NORM_CLIP)
    return np.clip((x - mean) / std, -C.OBS_NORM_CLIP, C.OBS_NORM_CLIP).astype(np.float32)


# ================================================================
# Prioritised experience replay
# ================================================================
class SumTree:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.tree = np.zeros(2 * capacity, dtype=np.float64)
        self.size = 0
        self.ptr = 0

    def total(self) -> float:
        return float(self.tree[1])

    def add(self, priority: float) -> int:
        idx = self.ptr
        self.update(idx, priority)
        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)
        return idx

    def update(self, idx: int, priority: float) -> None:
        i = idx + self.capacity
        delta = priority - self.tree[i]
        self.tree[i] = priority
        i //= 2
        while i >= 1:
            self.tree[i] += delta
            i //= 2

    def sample(self, value: float) -> int:
        i = 1
        while i < self.capacity:
            left = 2 * i
            if value <= self.tree[left]:
                i = left
            else:
                value -= self.tree[left]
                i = left + 1
        return i - self.capacity

    def priority(self, idx: int) -> float:
        return float(self.tree[idx + self.capacity])

    # -- vectorised batch operations (same semantics, ~10x less Python) --
    def sample_batch(self, values: np.ndarray) -> np.ndarray:
        """Vectorised `sample`; leaves may sit at two depths (capacity need
        not be a power of two), so each walker stops on its own."""
        i = np.ones(len(values), dtype=np.int64)
        v = np.asarray(values, dtype=np.float64).copy()
        act = i < self.capacity
        while act.any():
            left = 2 * i[act]
            lv = self.tree[left]
            right = v[act] > lv
            v[act] = np.where(right, v[act] - lv, v[act])
            i[act] = np.where(right, left + 1, left)
            act = i < self.capacity
        return i - self.capacity

    def update_batch(self, idxs: np.ndarray, priorities: np.ndarray) -> None:
        """Vectorised `update`: set leaves, then recompute every ancestor
        bottom-up (a node's last recompute follows all of its children's)."""
        leaf = np.asarray(idxs, dtype=np.int64) + self.capacity
        self.tree[leaf] = priorities
        nodes = np.unique(leaf // 2)
        while nodes.size:
            self.tree[nodes] = self.tree[2 * nodes] + self.tree[2 * nodes + 1]
            nodes = np.unique(nodes[nodes > 1] // 2)


class PrioritizedReplay:
    def __init__(self, capacity=None, s_dim=None, a_dim=None, rng=None):
        capacity = capacity or C.PER_CAPACITY
        s_dim = s_dim or C.STATE_DIM
        a_dim = a_dim or C.ACTION_DIM
        self.alpha = C.PER_ALPHA
        self.tree = SumTree(capacity)
        self.max_priority = 1.0
        self.rng = rng or np.random.default_rng(0)
        self.s = np.zeros((capacity, s_dim), dtype=np.float32)
        self.a = np.zeros((capacity, a_dim), dtype=np.float32)
        self.r = np.zeros((capacity, 1), dtype=np.float32)
        self.s2 = np.zeros((capacity, s_dim), dtype=np.float32)
        self.d = np.zeros((capacity, 1), dtype=np.float32)

    def __len__(self) -> int:
        return self.tree.size

    def push(self, s, a, r, s2, done) -> None:
        idx = self.tree.add(self.max_priority ** self.alpha)
        self.s[idx], self.a[idx], self.r[idx] = s, a, r
        self.s2[idx], self.d[idx] = s2, float(done)

    def sample(self, batch, beta):
        total = self.tree.total()
        seg = total / batch
        vals = self.rng.uniform(np.arange(batch) * seg, (np.arange(batch) + 1) * seg)
        idxs = np.clip(self.tree.sample_batch(vals), 0, max(self.tree.size - 1, 0))
        probs = self.tree.tree[idxs + self.tree.capacity] / max(total, 1e-12)
        w = (self.tree.size * np.maximum(probs, 1e-12)) ** (-beta)
        w /= w.max()
        t = lambda x: torch.as_tensor(x, device=DEVICE)
        return (t(self.s[idxs]), t(self.a[idxs]), t(self.r[idxs]), t(self.s2[idxs]),
                t(self.d[idxs]), idxs, t(w.astype(np.float32)).unsqueeze(1))

    def update_priorities(self, idxs, td_errors) -> None:
        p = np.abs(np.asarray(td_errors, dtype=np.float64).ravel()) + C.PER_EPS
        self.max_priority = max(self.max_priority, float(p.max()))
        self.tree.update_batch(np.asarray(idxs), p ** self.alpha)


# ================================================================
# Networks
# ================================================================
class Actor(nn.Module):
    def __init__(self, s_dim, a_dim, h):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(s_dim, h), nn.LayerNorm(h), nn.ReLU(),
            nn.Linear(h, h), nn.LayerNorm(h), nn.ReLU(),
            nn.Linear(h, a_dim), nn.Tanh())

    def forward(self, s):
        return self.net(s)

    def pre_tanh(self, s):
        return self.net[:-1](s)


class Critic(nn.Module):
    def __init__(self, s_dim, a_dim, h, n_q=1):
        super().__init__()
        self.heads = nn.ModuleList([nn.Sequential(
            nn.Linear(s_dim + a_dim, h), nn.LayerNorm(h), nn.ReLU(),
            nn.Linear(h, h), nn.LayerNorm(h), nn.ReLU(),
            nn.Linear(h, 1)) for _ in range(n_q)])

    def forward(self, s, a):
        sa = torch.cat([s, a], dim=1)
        return [head(sa) for head in self.heads]

    def q1(self, s, a):
        return self.heads[0](torch.cat([s, a], dim=1))


class ActorPolicy:
    """Picklable deterministic policy wrapper: state -> physical action.
    Carries a frozen copy of the observation-normalisation statistics."""

    def __init__(self, actor: nn.Module, obs_mean=None, obs_std=None):
        self.actor = copy.deepcopy(actor).cpu().eval()
        self.obs_mean, self.obs_std = obs_mean, obs_std

    @torch.no_grad()
    def __call__(self, s):
        x = normalize_obs(np.asarray(s, np.float32), self.obs_mean, self.obs_std)
        a = self.actor(torch.as_tensor(x).unsqueeze(0))
        return to_env_action(a.numpy()[0])


# ================================================================
# Agents
# ================================================================
class BaseAgent:
    name = "base"
    n_critics = 1

    def __init__(self, seed=0):
        torch.manual_seed(seed)
        s_dim, a_dim, h = C.STATE_DIM, C.ACTION_DIM, C.HIDDEN
        self.a_dim = a_dim
        self.rng = np.random.default_rng(seed + 7919)
        self.actor = Actor(s_dim, a_dim, h).to(DEVICE)
        self.actor_t = copy.deepcopy(self.actor)
        self.critic = Critic(s_dim, a_dim, h, n_q=self.n_critics).to(DEVICE)
        self.critic_t = copy.deepcopy(self.critic)
        self.opt_a = torch.optim.Adam(self.actor.parameters(), lr=C.LR_ACTOR,
                                      weight_decay=C.WEIGHT_DECAY)
        self.opt_c = torch.optim.Adam(self.critic.parameters(), lr=C.LR_CRITIC,
                                      weight_decay=C.WEIGHT_DECAY)
        self.buffer = PrioritizedReplay(s_dim=s_dim, a_dim=a_dim, rng=self.rng)
        self.updates = 0
        self.beta = C.PER_BETA_START
        self.obs_norm = RunningNorm(s_dim) if C.OBS_NORM else None

    # -- observation normalisation --------------------------------
    def observe(self, state) -> None:
        """Update the running statistics with a visited state (training)."""
        if self.obs_norm is not None:
            self.obs_norm.update(state)

    def norm_arrays(self):
        return self.obs_norm.arrays() if self.obs_norm is not None else (None, None)

    def _norm(self, x):
        mean, std = self.norm_arrays()
        return normalize_obs(x, mean, std)

    @torch.no_grad()
    def act_norm(self, state, noise: float = 0.0) -> np.ndarray:
        s = torch.as_tensor(self._norm(np.asarray(state, np.float32)),
                            device=DEVICE).unsqueeze(0)
        a = self.actor(s).cpu().numpy()[0]
        if noise > 0.0:
            a = a + noise * self.rng.standard_normal(self.a_dim)
        return np.clip(a, -1.0, 1.0).astype(np.float32)

    def act(self, state, noise: float = 0.0) -> np.ndarray:
        return to_env_action(self.act_norm(state, noise))

    def policy(self) -> ActorPolicy:
        return ActorPolicy(self.actor, *self.norm_arrays())

    @torch.no_grad()
    def q_policy(self, states: np.ndarray) -> dict:
        """Critic estimates of Q(s, mu(s)) for the actor's own actions."""
        s = torch.as_tensor(self._norm(np.asarray(states, np.float32)), device=DEVICE)
        qs = [q.squeeze(1).cpu().numpy() for q in self.critic(s, self.actor(s))]
        return dict(q1=qs[0], q_min=np.min(np.stack(qs), axis=0))

    def _soft_update(self):
        with torch.no_grad():
            for net, tgt in ((self.actor, self.actor_t), (self.critic, self.critic_t)):
                for p, pt in zip(net.parameters(), tgt.parameters()):
                    pt.mul_(1 - C.TAU_SOFT).add_(C.TAU_SOFT * p)

    def set_beta(self, progress: float):
        self.beta = C.PER_BETA_START + (C.PER_BETA_END - C.PER_BETA_START) * progress

    def set_lr(self, lr_a, lr_c):
        for g in self.opt_a.param_groups:
            g["lr"] = lr_a
        for g in self.opt_c.param_groups:
            g["lr"] = lr_c

    def state_dict(self):
        sd = {k: getattr(self, k).state_dict()
              for k in ("actor", "critic", "actor_t", "critic_t", "opt_a", "opt_c")}
        if self.obs_norm is not None:
            sd["obs_norm"] = self.obs_norm.state_dict()
        return sd

    def load_state_dict(self, sd):
        for k, v in sd.items():
            if k == "obs_norm":
                if self.obs_norm is not None:
                    self.obs_norm.load_state_dict(v)
            else:
                getattr(self, k).load_state_dict(v)

    def actor_snapshot(self) -> dict:
        """Deployable actor: weights + frozen normalisation statistics."""
        sd = {"actor": copy.deepcopy(self.actor.state_dict())}
        if self.obs_norm is not None:
            sd["obs_norm"] = self.obs_norm.state_dict()
        return sd

    def load_actor_snapshot(self, snap) -> None:
        if "actor" not in snap:                  # legacy file: bare state_dict
            self.actor.load_state_dict(snap)
            self.obs_norm = None
            return
        self.actor.load_state_dict(snap["actor"])
        if "obs_norm" in snap:
            self.obs_norm = RunningNorm(C.STATE_DIM)
            self.obs_norm.load_state_dict(snap["obs_norm"])
        else:
            self.obs_norm = None

    def _sample(self):
        """PER batch; raw states are stored, normalised with current stats."""
        s, a, r, s2, d, idxs, w = self.buffer.sample(C.BATCH_SIZE, self.beta)
        return self._norm(s), a, r, self._norm(s2), d, idxs, w

    def _actor_step(self, s):
        pre = self.actor.pre_tanh(s)
        q_term = -self.critic.q1(s, torch.tanh(pre)).mean()
        loss_a = q_term + C.ACTOR_PRE_L2 * (pre ** 2).mean()
        self.opt_a.zero_grad(set_to_none=True)
        loss_a.backward()
        nn.utils.clip_grad_norm_(self.actor.parameters(), C.GRAD_CLIP)
        self.opt_a.step()
        self._soft_update()
        self.last_q_term = float(q_term.item())
        return float(loss_a.item())

    def _critic_step(self, qs, y, w):
        loss_c = sum((w * F.mse_loss(q, y, reduction="none")).mean() for q in qs)
        self.opt_c.zero_grad(set_to_none=True)
        loss_c.backward()
        nn.utils.clip_grad_norm_(self.critic.parameters(), C.GRAD_CLIP)
        self.opt_c.step()
        return float(loss_c.item())


class DDPGAgent(BaseAgent):
    name = "ddpg"
    n_critics = 1

    def update(self):
        if len(self.buffer) < C.BATCH_SIZE:
            return {}
        s, a, r, s2, d, idxs, w = self._sample()
        with torch.no_grad():
            y = r + C.GAMMA * (1.0 - d) * self.critic_t(s2, self.actor_t(s2))[0]
        q = self.critic(s, a)[0]
        td = (q - y).detach()
        out = {"critic_loss": self._critic_step([q], y, w),
               "q1": float(q.mean().item()), "q2": float(q.mean().item())}
        out["actor_loss"] = self._actor_step(s)
        self.buffer.update_priorities(idxs, td.cpu().numpy())
        self.updates += 1
        return out


class TD3Agent(BaseAgent):
    name = "td3"
    n_critics = 2

    def update(self):
        if len(self.buffer) < C.BATCH_SIZE:
            return {}
        s, a, r, s2, d, idxs, w = self._sample()
        with torch.no_grad():
            noise = (torch.randn_like(a) * C.POLICY_NOISE).clamp(-C.NOISE_CLIP, C.NOISE_CLIP)
            a2 = (self.actor_t(s2) + noise).clamp(-1.0, 1.0)
            q1_t, q2_t = self.critic_t(s2, a2)
            y = r + C.GAMMA * (1.0 - d) * torch.min(q1_t, q2_t)
        q1, q2 = self.critic(s, a)
        # priority from the larger of the two TD errors
        td = torch.max((q1 - y).abs(), (q2 - y).abs()).detach()
        out = {"critic_loss": self._critic_step([q1, q2], y, w),
               "q1": float(q1.mean().item()), "q2": float(q2.mean().item())}
        self.updates += 1
        if self.updates % C.POLICY_FREQ == 0:
            out["actor_loss"] = self._actor_step(s)
        self.buffer.update_priorities(idxs, td.cpu().numpy())
        return out


def make_agent(algo: str, seed: int = 0) -> BaseAgent:
    algo = algo.lower()
    if algo == "ddpg":
        return DDPGAgent(seed=seed)
    if algo == "td3":
        return TD3Agent(seed=seed)
    raise ValueError(f"unknown algorithm '{algo}'")
