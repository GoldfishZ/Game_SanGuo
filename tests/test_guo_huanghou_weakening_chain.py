"""
测试郭皇后专属技能“衰弱的连计”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(general_id, name, force=6, intelligence=4):
    return General(
        general_id=general_id,
        name=name,
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_guo_huanghou_data_and_skill():
    guo_huanghou = get_general_by_name("郭皇后")

    assert guo_huanghou.camp == Camp.WEI
    assert guo_huanghou.rarity == Rarity.COMMON
    assert guo_huanghou.cost == 1.0
    assert guo_huanghou.force == 2
    assert guo_huanghou.intelligence == 7
    assert {attr.value for attr in guo_huanghou.attribute} == {"魅力"}
    assert guo_huanghou.active_skill.name == "衰弱的连计"
    assert guo_huanghou.active_skill.morale_cost == 4


def test_weakening_chain_reduces_one_enemy_without_chain_allies():
    guo_huanghou = get_general_by_name("郭皇后")
    enemies = [
        make_enemy(9301, "高武目标", 8),
        make_enemy(9302, "中武目标", 6),
        make_enemy(9303, "低武目标", 4),
    ]
    team = Team("魏军")
    enemy_team = Team("敌军")
    team.add_general(guo_huanghou)
    for enemy in enemies:
        enemy_team.add_general(enemy)

    result = team.use_skill(guo_huanghou, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["chain_count"] == 0
    assert result["target_limit"] == 1
    assert result["targets_affected"] == 1
    assert team.current_morale == 8
    assert enemies[0].get_effective_force() == 5
    assert enemies[1].get_effective_force() == 6
    assert enemies[2].get_effective_force() == 4


def test_weakening_chain_adds_targets_for_multiple_chain_generals():
    guo_huanghou = get_general_by_name("郭皇后")
    zhang_liao = get_general_by_name("张辽")
    yu_jin = get_general_by_name("于禁")
    enemies = [
        make_enemy(9311, "目标甲", 8),
        make_enemy(9312, "目标乙", 7),
        make_enemy(9313, "目标丙", 5),
    ]
    team = Team("魏军")
    enemy_team = Team("敌军")
    for general in [guo_huanghou, zhang_liao, yu_jin]:
        team.add_general(general)
    for enemy in enemies:
        enemy_team.add_general(enemy)

    result = team.use_skill(guo_huanghou, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["chain_count"] == 2
    assert result["target_limit"] == 2
    assert result["targets_affected"] == 2
    assert enemies[0].get_effective_force() == 5
    assert enemies[1].get_effective_force() == 4
    assert enemies[2].get_effective_force() == 5


if __name__ == "__main__":
    test_guo_huanghou_data_and_skill()
    test_weakening_chain_reduces_one_enemy_without_chain_allies()
    test_weakening_chain_adds_targets_for_multiple_chain_generals()
    print("郭皇后衰弱的连计测试通过")
