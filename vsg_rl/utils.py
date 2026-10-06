"""Logging, seeding and small numerical helpers."""
import os
import random
import time

import numpy as np

from . import config as C


def log_file() -> str:
    return C.out_path("training_log.txt")


def log(msg: str = "") -> None:
    """Print and append to results/training_log.txt (survives disconnects)."""
    print(msg, flush=True)
    try:
        with open(log_file(), "a") as fh:
            fh.write(str(msg) + "\n")
    except OSError:
        pass


def reset_log() -> None:
    try:
        with open(log_file(), "w") as fh:
            fh.write(f"VSG-RL run started {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    except OSError:
        pass


def set_global_seed(seed: int) -> None:
    np.random.seed(seed)
    random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def trapz(y, x):
    return np.trapezoid(y, x) if hasattr(np, "trapezoid") else np.trapz(y, x)


def lowpass_noise(rng, n: int, dt: float, tau: float) -> np.ndarray:
    """Unit-variance first-order low-pass filtered white noise."""
    w = rng.standard_normal(n)
    a = np.exp(-dt / tau)
    out = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc = a * acc + (1 - a) * w[i]
        out[i] = acc
    return out / (np.std(out) + 1e-9)


# Two-sided 95 % Student-t critical values, df = 1..30
_T95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
        2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
        2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


def mean_ci95(x):
    """(mean, sample std, 95 % CI half-width) for a small sample."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 2:
        return float(x.mean()) if n else float("nan"), 0.0, float("nan")
    sd = float(x.std(ddof=1))
    t = _T95[min(n - 1, len(_T95)) - 1] if n - 1 <= len(_T95) else 1.96
    return float(x.mean()), sd, float(t * sd / np.sqrt(n))


def welch_t(a, b):
    """Welch's t statistic and approximate dof (no scipy dependency)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    t = (a.mean() - b.mean()) / np.sqrt(va + vb + 1e-300)
    dof = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1) + 1e-300)
    return float(t), float(dof)


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path
