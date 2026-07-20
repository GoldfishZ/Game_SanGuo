"""可恢复、原子化的 PPO checkpoint 管理。"""
from __future__ import annotations

import os
from pathlib import Path


class CheckpointManager:
    def __init__(self, directory="artifacts/rl/checkpoints", keep_last=5):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.keep_last = keep_last

    def save(self, state, update, *, is_best=False):
        import torch
        numbered = self.directory / f"ppo_step_{update:06d}.pt"
        temporary = numbered.with_suffix(".tmp")
        torch.save(state, temporary)
        os.replace(temporary, numbered)
        torch.save(state, self.directory / "ppo_latest.pt")
        if is_best:
            torch.save(state, self.directory / "ppo_best.pt")
        self.prune()
        return numbered

    def prune(self):
        files = sorted(self.directory.glob("ppo_step_*.pt"), key=lambda item: item.stat().st_mtime, reverse=True)
        for path in files[self.keep_last:]:
            path.unlink()

    @staticmethod
    def load(path, device="cpu"):
        import torch
        return torch.load(path, map_location=device)
