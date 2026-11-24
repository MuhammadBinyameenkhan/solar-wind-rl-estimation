"""A training run interrupted after a validation checkpoint and resumed gives the same result
as an uninterrupted run (vsgrl.train.train_one, resume.pt)."""
import copy

import pandas as pd
import pytest
import torch

import vsgrl.train as T


def _small(cfg):
    cfg = copy.deepcopy(cfg)
    t = cfg["train"]
    t.update(episodes=4, eval_every=2, eval_episodes=2, warmup_steps=200, batch_size=32, buffer_size=5000,
             hidden=[16, 16])
    cfg["env"]["episode_s"] = 4.0
    return cfg


def test_resume_identical(cfg, tmp_path, monkeypatch):
    cfg = _small(cfg)
    a = T.train_one(cfg, "td3", 0, tmp_path / "a")

    real, calls = T.evaluate_policy, {"n": 0}

    def flaky(*args, **kw):
        calls["n"] += 1
        if calls["n"] == 3:                   # ep 0, ep 2 (checkpoint written), then fail at ep 4
            raise KeyboardInterrupt
        return real(*args, **kw)

    monkeypatch.setattr(T, "evaluate_policy", flaky)
    with pytest.raises(KeyboardInterrupt):
        T.train_one(cfg, "td3", 0, tmp_path / "b")
    assert (tmp_path / "b" / "resume.pt").exists()
    monkeypatch.setattr(T, "evaluate_policy", real)
    b = T.train_one(cfg, "td3", 0, tmp_path / "b")
    assert not (b / "resume.pt").exists()

    va, vb = pd.read_csv(a / "val_log.csv"), pd.read_csv(b / "val_log.csv")
    pd.testing.assert_frame_equal(va, vb)
    ta, tb = pd.read_csv(a / "train_log.csv"), pd.read_csv(b / "train_log.csv")
    pd.testing.assert_frame_equal(ta.drop(columns="wall_s"), tb.drop(columns="wall_s"))
    wa, wb = torch.load(a / "final.pt")["actor"], torch.load(b / "final.pt")["actor"]
    assert all(torch.equal(wa[k], wb[k]) for k in wa)
