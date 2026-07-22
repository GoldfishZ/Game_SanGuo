"""笔记本GPU适配：每个PPO update后归还未使用的CUDA缓存。"""
from __future__ import annotations

from src.rl.training.ppo_v3 import ppo_update as _ppo_update


def ppo_update(*args, **kwargs):
    metrics = _ppo_update(*args, **kwargs)
    import torch
    device = kwargs.get("device")
    if torch.cuda.is_available() and str(device).startswith("cuda"):
        torch.cuda.empty_cache()
    return metrics
