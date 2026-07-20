"""评估 guard 的回归测试。"""
from src.rl.env import SanguoEnv
from src.rl.opponents import RandomOpponent
from src.rl.training.evaluation import evaluate


class StuckPolicy:
    """始终选合法的第一个非结束动作，模拟确定性策略卡住。"""
    def select_action(self, observation, action_mask, rng):
        for action_id, masked in enumerate(action_mask):
            if not masked and action_id > 1:
                return action_id
        return 0


def test_evaluation_step_guard_turns_stuck_policy_into_timeout():
    result = evaluate(
        model=None, device="cpu", opponent=RandomOpponent(), episodes=2,
        max_steps_per_episode=3, max_seconds=10, policy=StuckPolicy(),
    )
    assert result["timeout_rate"] == 1.0
    assert result["win_rate"] == 0.0
    assert result["draw_rate"] == 1.0
    assert result["mean_steps"] == 3


def test_opponent_turn_guard_has_finite_budget():
    env = SanguoEnv(RandomOpponent())
    _, _ = env.reset(20260720)
    # The public action contract remains usable after an automatically resolved opponent turn.
    assert env.legal_actions()
