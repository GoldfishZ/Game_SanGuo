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
