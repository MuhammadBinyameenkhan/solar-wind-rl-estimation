"""YAML configuration loading with `base:` inheritance and CLI overrides."""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _parse_value(text: str) -> Any:
    return yaml.safe_load(text)


def apply_overrides(cfg: dict, overrides: Iterable[str]) -> dict:
    """Apply `a.b.c=value` overrides (value parsed as YAML)."""
    cfg = copy.deepcopy(cfg)
    for item in overrides or []:
        key, _, raw = item.partition("=")
        if not _:
            raise ValueError(f"Override '{item}' must look like section.key=value")
        node = cfg
        parts = key.strip().split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = _parse_value(raw)
    return cfg


def load_config(path: str | Path = "configs/default.yaml", overrides: Iterable[str] = ()) -> dict:
    path = Path(path)
    if not path.is_absolute() and not path.exists():
        path = REPO_ROOT / path
    with open(path) as fh:
        cfg = yaml.safe_load(fh) or {}
    base = cfg.pop("base", None)
    if base:
        cfg = _deep_merge(load_config(path.parent / base), cfg)
    return apply_overrides(cfg, overrides)


def resolve_path(p: str | Path | None) -> Path | None:
    """Resolve a config path relative to the repository root."""
    if p is None:
        return None
    p = Path(p)
    return p if p.is_absolute() else REPO_ROOT / p
