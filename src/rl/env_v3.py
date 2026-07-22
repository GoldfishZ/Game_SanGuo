"""使用战术势能奖励的 v3 训练环境。"""
from __future__ import annotations

from src.rl.env import SanguoEnv as BaseSanguoEnv
from src.rl.reward_v3 import RewardHandler


class SanguoEnv(BaseSanguoEnv):
    """规则与 observation 保持 v2 一致，仅升级奖励归因。"""

    def __init__(self, opponent=None, *, team_size=3, cost_limit=8.0,
                 max_turns=200, reward_config=None):
        super().__init__(
            opponent, team_size=team_size, cost_limit=cost_limit,
            max_turns=max_turns, reward_config=reward_config,
        )
        self.reward_handler = RewardHandler(reward_config)

    def step(self, action_id: int):
        if self.done:
            raise RuntimeError("本 episode 已结束，请先 reset")
        mask = self.action_mask()
        if not 0 <= action_id < self.action_size or mask[action_id]:
            raise ValueError(f"非法动作: {action_id}")
        action = self.decode_action(action_id)
        result = self._apply_learning_action(action)
        self._finalize_if_over()
        if not self.done and action.kind == "end_attack":
            self.rules.end_turn()
            self._run_opponent_turn()
            self._finalize_if_over()
        outcome = self.rules.outcome()
        reward = self.reward_handler.step(
            self.learning_team, self.enemy_team,
            action_success=bool(result.get("success")), action_kind=action.kind,
            done=self.done, winner=outcome.winner, timeout=outcome.timeout,
        )
        response_info = self.info(action_id, result)
        response_info["no_progress"] = self.reward_handler.last_no_progress
        response_info["reward_components"] = dict(self.reward_handler.last_components)
        return self.observation(), reward, self.done, response_info
