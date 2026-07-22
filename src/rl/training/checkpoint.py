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
        self._atomic_save(torch, state, self.directory / "ppo_latest.pt")
        if is_best:
            self._atomic_save(torch, state, self.directory / "ppo_best.pt")
        self.prune()
        return numbered

    @staticmethod
    def _atomic_save(torch, state, path):
        temporary = path.with_suffix(".tmp")
        torch.save(state, temporary)
        os.replace(temporary, path)

    def prune(self):
        files = sorted(self.directory.glob("ppo_step_*.pt"), key=lambda item: item.stat().st_mtime, reverse=True)
        for path in files[self.keep_last:]:
            path.unlink()

    @staticmethod
    def load(path, device="cpu"):
        import torch
        return torch.load(path, map_location=device)

    @staticmethod
    def validate_schema(state, *, observation_schema, observation_size, action_size,
                        model_schema):
        expected = (observation_schema, int(observation_size), int(action_size), model_schema)
        actual = (
            state.get("observation_schema"),
            state.get("observation_size"),
            state.get("action_size"),
            state.get("model_schema"),
        )
        if actual != expected:
            raise ValueError(
                "checkpoint 与当前训练 schema 不兼容："
                f"checkpoint={actual}, current={expected}。请从 v2 新模型开始训练。"
            )
