"""人工控制训练模式下的 best checkpoint 追踪测试。"""
from src.rl.training.early_stop import ConvergenceTracker


def test_tracker_never_requests_training_stop():
    tracker = ConvergenceTracker(min_delta=0.02)
    first_best, first_quality = tracker.update(0.9, timeout_rate=0.0)
    assert first_best
    assert first_quality == 0.9

    for _ in range(20):
        is_best, quality = tracker.update(0.1, timeout_rate=0.0)
        assert not is_best
        assert quality == 0.1
    assert tracker.best_quality_score == 0.9


def test_tracker_uses_timeout_adjusted_quality():
    tracker = ConvergenceTracker(min_delta=0.01)
    assert tracker.update(0.50, timeout_rate=0.0)[0]
    # 虽然原始胜率更高，但 timeout 抵消后不应覆盖稳定模型。
    assert not tracker.update(0.52, timeout_rate=0.04)[0]
