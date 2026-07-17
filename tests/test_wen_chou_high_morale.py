"""
测试文丑专属技能“士气旺盛”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, Rarity
from src.models.team import Team


def build_team(max_morale=12):
    wen_chou = get_general_by_name("文丑")
    team = Team("袁军")
    enemy_team = Team("敌军")
    team.add_general(wen_chou)
    team.position_general(wen_chou, 0, 0)
    team.max_morale = max_morale
    team.current_morale = max_morale
    return wen_chou, team, enemy_team


def test_wen_chou_data_and_skill():
    wen_chou = get_general_by_name("文丑")

    assert wen_chou.camp == Camp.YUAN
    assert wen_chou.rarity == Rarity.EPIC
    assert wen_chou.cost == 2.0
    assert wen_chou.force == 8
    assert wen_chou.intelligence == 3
    assert {attr.value for attr in wen_chou.attribute} == {"勇猛"}
    assert wen_chou.active_skill.name == "士气旺盛"
    assert wen_chou.active_skill.morale_cost == 4


def test_high_morale_boosts_four_at_initial_cap():
    wen_chou, team, enemy_team = build_team(12)
    context = BattleContext(team, enemy_team)

    result = team.use_skill(wen_chou, [], context)

    assert result["success"] is True
    assert result["force_boost"] == 4
    assert result["max_morale"] == 12
    assert team.current_morale == 8
    assert wen_chou.get_effective_force() == 12


def test_high_morale_scales_with_extra_max_morale():
    wen_chou, team, enemy_team = build_team(16)
    context = BattleContext(team, enemy_team)

    result = team.use_skill(wen_chou, [], context)

    assert result["success"] is True
    assert result["force_boost"] == 6
    assert result["max_morale"] == 16
    assert team.current_morale == 12
    assert wen_chou.get_effective_force() == 14


if __name__ == "__main__":
    test_wen_chou_data_and_skill()
    test_high_morale_boosts_four_at_initial_cap()
    test_high_morale_scales_with_extra_max_morale()
    print("文丑士气旺盛测试通过")
