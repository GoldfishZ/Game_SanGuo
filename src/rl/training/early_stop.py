"""以固定验证表现控制训练结束。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConvergenceTracker:
    target_win_rate: float = 0.85
    patience: int = 10
    min_delta: float = 0.01
    best_win_rate: float = float("-inf")
    stale_evaluations: int = 0

    def update(self, win_rate):
        if win_rate >= self.target_win_rate:
            return True, True, "target_win_rate"
        if win_rate > self.best_win_rate + self.min_delta:
            self.best_win_rate = win_rate
            self.stale_evaluations = 0
            return True, False, "improved"
        self.stale_evaluations += 1
        if self.stale_evaluations >= self.patience:
            return False, True, "plateau"
        return False, False, "continue"
