"""以固定验证表现控制训练结束。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConvergenceTracker:
    target_win_rate: float = 0.85
    patience: int = 10
    min_delta: float = 0.01
    best_win_rate: float = float("-inf")
    best_quality_score: float = float("-inf")
    stale_evaluations: int = 0

    def update(self, win_rate, timeout_rate=0.0):
        quality_score = win_rate - timeout_rate
        if win_rate >= self.target_win_rate and timeout_rate == 0.0:
            return True, True, "target_win_rate", quality_score
        if quality_score > self.best_quality_score + self.min_delta:
            self.best_win_rate = win_rate
            self.best_quality_score = quality_score
            self.stale_evaluations = 0
            return True, False, "improved", quality_score
        self.stale_evaluations += 1
        if self.stale_evaluations >= self.patience:
            return False, True, "plateau", quality_score
        return False, False, "continue", quality_score
