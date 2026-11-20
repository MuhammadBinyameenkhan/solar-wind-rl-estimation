import sys
from pathlib import Path

from .vsg_env import OBS_NAMES, VSGEnv

__all__ = ["VSGEnv", "OBS_NAMES", "make_env"]


def make_env(cfg, df, split="train", record_trace=False, **kw):
    """Study 2 single-bus environment, or the Study 3 IEEE 33-bus feeder environment when
    system.network.model == "ieee33"."""
    if (cfg["system"].get("network") or {}).get("model") == "ieee33":
        s3 = str(Path(__file__).resolve().parents[2] / "study3_ieee33")
        if s3 not in sys.path:
            sys.path.insert(0, s3)
        from vsgrl33.env33 import Ieee33VSGEnv
        return Ieee33VSGEnv(cfg, df, split=split, record_trace=record_trace, **kw)
    return VSGEnv(cfg, df, split=split, record_trace=record_trace, **kw)
