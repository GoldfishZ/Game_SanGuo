"""跟踪固定验证的最佳质量分，用于维护 ppo_best.pt。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConvergenceTracker:
    min_delta: float = 0.01
    best_win_rate: float = float("-inf")
    best_quality_score: float = float("-inf")

    def update(self, win_rate, timeout_rate=0.0):
        """返回是否应保存 best checkpoint；不再请求结束整个训练。"""
        quality_score = win_rate - timeout_rate
        is_best = quality_score > self.best_quality_score + self.min_delta
        if is_best:
            self.best_win_rate = win_rate
            self.best_quality_score = quality_score
        return is_best, quality_score
