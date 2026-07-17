"""
测试小乔专属技能“流星的仪式”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name, force=5, intelligence=5):
    return General(
        general_id=9980,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def build_row_targets():
    xiao_qiao = get_general_by_name("小乔")
    enemies = [
        make_enemy("同排A"),
        make_enemy("同排B"),
        make_enemy("异排C"),
    ]
    team = Team("吴军")
    enemy_team = Team("敌军")

    team.add_general(xiao_qiao)
    for enemy in enemies:
        enemy_team.add_general(enemy)
    enemy_team.position_general(enemies[0], 1, 0)
    enemy_team.position_general(enemies[1], 1, 2)
    enemy_team.position_general(enemies[2], 2, 0)
    return xiao_qiao, enemies, team, enemy_team


def test_xiao_qiao_data_and_skill():
    xiao_qiao = get_general_by_name("小乔")

    assert xiao_qiao.camp == Camp.WU
    assert xiao_qiao.rarity == Rarity.RARE
    assert xiao_qiao.cost == 1.5
    assert xiao_qiao.force == 2
    assert xiao_qiao.intelligence == 5
    assert {"防栅", "魅力"} <= {attr.value for attr in xiao_qiao.attribute}
    assert xiao_qiao.active_skill.name == "流星的仪式"
    assert xiao_qiao.active_skill.morale_cost == 5


def test_meteor_rite_deals_fixed_damage_to_enemy_row():
    xiao_qiao, enemies, team, enemy_team = build_row_targets()
    context = BattleContext(team, enemy_team)
    context.skill_options = {"row": 1}

    result = team.use_skill(xiao_qiao, [], context)

    assert result["success"] is True
    assert result["row"] == 1
    assert result["targets_affected"] == 2
    assert result["total_damage"] == 4
    assert team.current_morale == 7
    assert enemies[0].current_hp == enemies[0].max_hp - 2
    assert enemies[1].current_hp == enemies[1].max_hp - 2
    assert enemies[2].current_hp == enemies[2].max_hp


def test_meteor_rite_selects_best_row_by_default():
    xiao_qiao, enemies, team, enemy_team = build_row_targets()
    context = BattleContext(team, enemy_team)

    result = team.use_skill(xiao_qiao, [], context)

    assert result["success"] is True
    assert result["row"] == 1
    assert result["targets_affected"] == 2


if __name__ == "__main__":
    test_xiao_qiao_data_and_skill()
    test_meteor_rite_deals_fixed_damage_to_enemy_row()
    test_meteor_rite_selects_best_row_by_default()
    print("小乔流星的仪式测试通过")
