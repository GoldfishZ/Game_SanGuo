"""
测试张飞专属技能“轮枪战术”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name, force, intelligence=4):
    return General(
        general_id=9100,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_zhang_fei_data_and_skill():
    zhang_fei = get_general_by_name("张飞")

    assert zhang_fei.force == 8
    assert zhang_fei.intelligence == 4
    assert zhang_fei.cost == 2.0
    assert "勇猛" in [attr.value for attr in zhang_fei.attribute]
    assert zhang_fei.active_skill.name == "轮枪战术"
    assert zhang_fei.active_skill.morale_cost == 4


def test_spear_wheel_damages_best_2x2_block_by_weakest_force_basis():
    zhang_fei = get_general_by_name("张飞")
    team = Team("张飞队")
    enemy_team = Team("敌队")
    team.add_general(zhang_fei)

    weak = make_enemy("弱敌", 2)
    guard_a = make_enemy("敌A", 6)
    guard_b = make_enemy("敌B", 7)
    outside = make_enemy("圈外", 3)
    for enemy in [weak, guard_a, guard_b, outside]:
        enemy_team.add_general(enemy)

    team.position_general(zhang_fei, 0, 0)
    enemy_team.position_general(weak, 0, 0)
    enemy_team.position_general(guard_a, 0, 1)
    enemy_team.position_general(guard_b, 1, 0)
    enemy_team.position_general(outside, 2, 3)

    result = team.use_skill(
        zhang_fei,
        [],
        BattleContext(team, enemy_team),
    )

    assert result["success"] is True
    assert result["damage_basis_target"] == "弱敌"
    assert result["base_damage"] == 6
    assert result["shared_damage"] == 2
    assert result["targets_hit"] == 3
    assert team.current_morale == 8
    assert weak.current_hp == weak.max_hp - 2
    assert guard_a.current_hp == guard_a.max_hp - 2
    assert guard_b.current_hp == guard_b.max_hp - 2
    assert outside.current_hp == outside.max_hp


def test_spear_wheel_respects_player_selected_2x2_block():
    zhang_fei = get_general_by_name("张飞")
    team = Team("张飞队")
    enemy_team = Team("敌队")
    team.add_general(zhang_fei)
    crowded_a = make_enemy("自动区A", 3)
    crowded_b = make_enemy("自动区B", 4)
    selected = make_enemy("玩家选中", 5)
    for enemy in [crowded_a, crowded_b, selected]:
        enemy_team.add_general(enemy)
    enemy_team.position_general(crowded_a, 0, 0)
    enemy_team.position_general(crowded_b, 0, 1)
    enemy_team.position_general(selected, 2, 3)
    selected_hp = selected.current_hp

    result = team.use_skill(
        zhang_fei,
        [{"row": 1, "col": 2}],
        BattleContext(team, enemy_team),
    )

    assert result["block"] == [(1, 2), (1, 3), (2, 2), (2, 3)]
    assert selected.current_hp < selected_hp
    assert crowded_a.current_hp == crowded_a.max_hp
    assert crowded_b.current_hp == crowded_b.max_hp


if __name__ == "__main__":
    test_zhang_fei_data_and_skill()
    test_spear_wheel_damages_best_2x2_block_by_weakest_force_basis()
    print("张飞轮枪战术测试通过")
