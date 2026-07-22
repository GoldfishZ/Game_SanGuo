"""训练环境内的非学习方策略。"""
from __future__ import annotations

import random


class RandomOpponent:
    def choose_action(self, env):
        legal = env.legal_actions()
        return env.rng.choice(legal)


class HeuristicOpponent:
    """优先伤害最低生命目标的轻量基线对手。"""
    def choose_action(self, env):
        legal = env.legal_actions()
        attack_actions = [action for action in legal if env.decode_action(action).kind == "attack"]
        if attack_actions:
            return min(attack_actions, key=lambda action: env.attack_target_hp(action))
        skill_actions = [action for action in legal if env.decode_action(action).kind.startswith("skill")]
        return self._rng_choice(env, skill_actions or legal)

    @staticmethod
    def _rng_choice(env, actions):
        return env.rng.choice(actions)


class ModelOpponent:
    """使用冻结 ActorCritic 快照行动的 self-play 对手。"""

    def __init__(self, model, device="cpu", deterministic=False, opponent_id="current"):
        self.model = model
        self.device = device
        self.deterministic = deterministic
        self.opponent_id = opponent_id

    def choose_action(self, env):
        import torch
        with torch.no_grad():
            observation = torch.as_tensor(
                env.observation(), dtype=torch.float32, device=self.device,
            ).unsqueeze(0)
            mask = torch.as_tensor(
                env.action_mask(), dtype=torch.bool, device=self.device,
            ).unsqueeze(0)
            logits, _ = self.model(observation, mask)
            if self.deterministic:
                return int(logits.argmax(dim=-1).item())
            return int(torch.distributions.Categorical(logits=logits).sample().item())
