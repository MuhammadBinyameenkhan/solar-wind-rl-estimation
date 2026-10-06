"""
DDPG and TD3 with SumTree prioritised replay.

The two agents share everything except the three TD3 changes:

    DDPG                          TD3
    1 critic                      2 critics, target = min(Q1, Q2)
    target = Q'(s', mu'(s'))      + clipped Gaussian target-policy smoothing
    actor + targets every update  actor + targets every POLICY_FREQ updates
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
    """Picklable deterministic policy wrapper: state -> physical action."""

    def __init__(self, actor: nn.Module):
        self.actor = copy.deepcopy(actor).cpu().eval()

    @torch.no_grad()
    def __call__(self, s):
        a = self.actor(torch.as_tensor(np.asarray(s, np.float32)).unsqueeze(0))
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

    @torch.no_grad()
    def act_norm(self, state, noise: float = 0.0) -> np.ndarray:
        s = torch.as_tensor(np.asarray(state, np.float32), device=DEVICE).unsqueeze(0)
        a = self.actor(s).cpu().numpy()[0]
        if noise > 0.0:
            a = a + noise * self.rng.standard_normal(self.a_dim)
        return np.clip(a, -1.0, 1.0).astype(np.float32)

    def act(self, state, noise: float = 0.0) -> np.ndarray:
        return to_env_action(self.act_norm(state, noise))

    def policy(self) -> ActorPolicy:
        return ActorPolicy(self.actor)

    @torch.no_grad()
    def q_policy(self, states: np.ndarray) -> dict:
        """Critic estimates of Q(s, mu(s)) for the actor's own actions."""
        s = torch.as_tensor(np.asarray(states, np.float32), device=DEVICE)
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
        return {k: getattr(self, k).state_dict()
                for k in ("actor", "critic", "actor_t", "critic_t", "opt_a", "opt_c")}

    def load_state_dict(self, sd):
        for k, v in sd.items():
            getattr(self, k).load_state_dict(v)

    def _actor_step(self, s):
        loss_a = -self.critic.q1(s, self.actor(s)).mean()
        self.opt_a.zero_grad(set_to_none=True)
        loss_a.backward()
        nn.utils.clip_grad_norm_(self.actor.parameters(), C.GRAD_CLIP)
        self.opt_a.step()
        self._soft_update()
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
        s, a, r, s2, d, idxs, w = self.buffer.sample(C.BATCH_SIZE, self.beta)
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
        s, a, r, s2, d, idxs, w = self.buffer.sample(C.BATCH_SIZE, self.beta)
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
