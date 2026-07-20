"""训练运行时设备与资源自适应配置。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import os


@dataclass(frozen=True)
class RuntimeProfile:
    device: str
    device_name: str
    vram_gb: float
    cpu_count: int
    num_workers: int
    rollout_steps: int
    minibatch_size: int

    def to_dict(self):
        return asdict(self)


def _auto_values(vram_gb: float, cpu_count: int):
    if vram_gb <= 0:
        return max(1, cpu_count // 2), 4096, 256
    if vram_gb <= 6:
        return min(6, max(1, cpu_count - 2)), 4096, 256
    if vram_gb <= 12:
        return min(8, max(1, cpu_count - 2)), 8192, 512
    return min(12, max(1, cpu_count - 2)), 16384, 1024


def _resolve(value, automatic):
    return automatic if value in (None, "auto") else int(value)


def detect_runtime(device="auto", num_workers="auto", rollout_steps="auto", minibatch_size="auto"):
    """选择可运行的 learner 设备及保守的初始采样/批量配置。

    环境 worker 永远运行在 CPU；GPU 仅运行 learner 的 PPO 更新。
    """
    try:
        import torch
    except ImportError:
        torch = None
    cpu_count = os.cpu_count() or 1
    cuda_available = bool(torch and torch.cuda.is_available())
    if device == "auto":
        selected = "cuda:0" if cuda_available else "cpu"
    elif device == "cuda":
        selected = "cuda:0"
    else:
        selected = device
    if selected.startswith("cuda") and not cuda_available:
        raise RuntimeError("请求 CUDA，但 PyTorch 未检测到可用 NVIDIA CUDA 设备")

    vram_gb = 0.0
    device_name = "CPU"
    if selected.startswith("cuda"):
        index = int(selected.split(":")[1]) if ":" in selected else 0
        props = torch.cuda.get_device_properties(index)
        vram_gb = props.total_memory / 1024 ** 3
        device_name = props.name
    auto_workers, auto_rollout, auto_minibatch = _auto_values(vram_gb, cpu_count)
    return RuntimeProfile(
        device=selected,
        device_name=device_name,
        vram_gb=round(vram_gb, 2),
        cpu_count=cpu_count,
        num_workers=_resolve(num_workers, auto_workers),
        rollout_steps=_resolve(rollout_steps, auto_rollout),
        minibatch_size=_resolve(minibatch_size, auto_minibatch),
    )
