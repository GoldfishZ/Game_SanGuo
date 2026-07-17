"""
测试李傕和郭汜专属技能“卑劣的奇袭”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, Rarity
from src.models.team import Team


def build_team(enemy_spent=0):
    li_guo = get_general_by_name("李傕和郭汜")
    team = Team("凉军")
    enemy_team = Team("敌军")
    team.add_general(li_guo)
    team.position_general(li_guo, 0, 0)
    enemy_team.morale_spent = enemy_spent
    return li_guo, team, enemy_team


def test_li_jue_guo_si_data_and_skill():
    li_guo = get_general_by_name("李傕和郭汜")

    assert li_guo.camp == Camp.LIANG
    assert li_guo.rarity == Rarity.RARE
    assert li_guo.cost == 1.5
    assert li_guo.force == 6
    assert li_guo.intelligence == 3
    assert li_guo.attribute == []
    assert li_guo.active_skill.name == "卑劣的奇袭"
    assert li_guo.active_skill.morale_cost == 3


def test_vile_raid_has_minimum_two_boost():
    li_guo, team, enemy_team = build_team(enemy_spent=0)
    context = BattleContext(team, enemy_team)

    result = team.use_skill(li_guo, [], context)

    assert result["success"] is True
    assert result["enemy_morale_spent"] == 0
    assert result["force_boost"] == 2
    assert team.current_morale == 9
    assert team.morale_spent == 3
    assert li_guo.get_effective_force() == 8


def test_vile_raid_scales_with_enemy_spent_morale():
    li_guo, team, enemy_team = build_team(enemy_spent=5)
    context = BattleContext(team, enemy_team)

    result = team.use_skill(li_guo, [], context)

    assert result["success"] is True
    assert result["enemy_morale_spent"] == 5
    assert result["force_boost"] == 3
    assert li_guo.get_effective_force() == 9


def test_team_tracks_spent_morale():
    team = Team("测试队")

    assert team.morale_spent == 0
    assert team.consume_morale(4) is True
    assert team.current_morale == 8
    assert team.morale_spent == 4
    assert team.consume_morale(20) is False
    assert team.morale_spent == 4


if __name__ == "__main__":
    test_li_jue_guo_si_data_and_skill()
    test_vile_raid_has_minimum_two_boost()
    test_vile_raid_scales_with_enemy_spent_morale()
    test_team_tracks_spent_morale()
    print("李傕和郭汜卑劣的奇袭测试通过")
