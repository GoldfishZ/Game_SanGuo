"""Web、训练环境和模拟客户端共用的权威战斗规则服务。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.battle.turn_actions import (
    apply_attack_action,
    apply_resolved_skill_action,
    apply_skill_action,
    advance_turn,
)


@dataclass(frozen=True)
class BattleOutcome:
    done: bool
    timeout: bool
    winner: Optional[str]
    outcome: str


class BattleRulesService:
    """调用方选择动作；本服务负责合法性、结算、回合与终局口径。"""

    def __init__(self, battle_system):
        self.battle_system = battle_system

    def skill(self, caster, **selection):
        return apply_skill_action(self.battle_system, caster, **selection)

    def skill_targets(self, caster, targets, *, guess=None):
        return apply_resolved_skill_action(
            self.battle_system, caster, targets, guess=guess,
        )

    def attack(self, attacker, target, *, guess=None, bravery_guess=None,
               charisma_guess=None):
        return apply_attack_action(
            self.battle_system, attacker, target, guess=guess,
            bravery_guess=bravery_guess, charisma_guess=charisma_guess,
        )

    def end_turn(self):
        return advance_turn(self.battle_system)

    def outcome(self) -> BattleOutcome:
        bs = self.battle_system
        timeout = bs.turn_count >= bs.max_turns
        if timeout:
            return BattleOutcome(True, True, None, "draw")
        if not bs._is_game_over():
            return BattleOutcome(False, False, None, "ongoing")
        return BattleOutcome(True, False, bs._determine_winner(), "win")
