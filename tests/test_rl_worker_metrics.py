"""多 worker episode summary 与训练指标聚合测试。"""
import math
import numpy as np

from src.rl.evaluation.strength import GeneralStrengthTracker
from src.rl.observation import OBSERVATION_SIZE
from src.rl.training.vector_env import EpisodeSummary, GeneralRecord, RolloutFragment
from tools.rl.train_ppo import linear_schedule, rollout_metrics_from_fragments


def _summary(outcome, steps=4, turns=2, reward=1.0, no_progress=1):
    return EpisodeSummary(
        outcome=outcome,
        winner_name="self" if outcome == "win" else "enemy" if outcome == "loss" else "",
        timeout=outcome == "draw",
        turns=turns,
        steps=steps,
        episode_reward=reward,
        no_progress_count=no_progress,
        action_counts={"skill": 1, "attack": 2, "end": 1},
        damage_by_general_id={1: 3.0},
        learning_team_name="self",
        enemy_team_name="enemy",
        learning_generals=[GeneralRecord(1, "甲", 0.8, True)],
        enemy_generals=[GeneralRecord(2, "乙", 0.0, False)],
    )


def _fragment(summaries):
    return RolloutFragment(
        observations=np.zeros((12, OBSERVATION_SIZE), dtype=np.float32),
        masks=np.zeros((12, 722), dtype=np.bool_),
        actions=np.zeros(12, dtype=np.int64),
        log_probs=np.zeros(12, dtype=np.float32),
        rewards=np.zeros(12, dtype=np.float32),
        values=np.zeros(12, dtype=np.float32),
        dones=np.zeros(12, dtype=np.bool_),
        bootstrap_value=0.0,
        episode_summaries=summaries,
    )


def test_worker_summary_metrics_and_strength_are_aggregated():
    tracker = GeneralStrengthTracker()
    metrics = rollout_metrics_from_fragments(
        [_fragment([_summary("win"), _summary("loss")]), _fragment([_summary("draw")])],
        tracker,
    )
    assert metrics["episodes"] == 3
    assert metrics["win_rate"] == 1 / 3
    assert metrics["loss_rate"] == 1 / 3
    assert metrics["draw_rate"] == 1 / 3
    assert metrics["timeout_rate"] == 1 / 3
    assert metrics["mean_turns"] == 2
    assert metrics["mean_episode_steps"] == 4
    assert metrics["no_progress_rate"] == 3 / 24
    assert tracker.balance_metrics()["general_count"] == 2


def test_empty_worker_summaries_are_safe():
    metrics = rollout_metrics_from_fragments([_fragment([])])
    assert metrics["episodes"] == 0
    assert metrics["win_rate"] == 0.0
    assert metrics["mean_turns"] == 0.0


def test_linear_schedule_clamps_at_final_value():
    assert math.isclose(linear_schedule(3e-4, 1e-4, 0.0), 3e-4)
    assert math.isclose(linear_schedule(3e-4, 1e-4, 0.5), 2e-4)
    assert math.isclose(linear_schedule(3e-4, 1e-4, 3.0), 1e-4)
    assert math.isclose(linear_schedule(0.05, 0.01, 1.0), 0.01)
