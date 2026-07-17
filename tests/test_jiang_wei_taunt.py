"""
测试姜维专属技能“挑衅”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name, force=6, intelligence=4):
    return General(
        general_id=9990,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def make_ally(name):
    return General(
        general_id=9991,
        name=name,
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=3,
        intelligence=3,
    )


def build_grid():
    jiang_wei = get_general_by_name("姜维")
    ally = make_ally("友军")
    enemies = [
        make_enemy("目标A"),
        make_enemy("目标B"),
        make_enemy("目标C"),
        make_enemy("范围外"),
    ]
    team = Team("蜀军")
    enemy_team = Team("敌军")

    for general in [jiang_wei, ally]:
        team.add_general(general)
    team.position_general(jiang_wei, 0, 0)
    team.position_general(ally, 0, 1)

    for enemy in enemies:
        enemy_team.add_general(enemy)
    enemy_team.position_general(enemies[0], 0, 0)
    enemy_team.position_general(enemies[1], 0, 1)
    enemy_team.position_general(enemies[2], 1, 0)
    enemy_team.position_general(enemies[3], 2, 3)
    return jiang_wei, ally, enemies, team, enemy_team


def test_jiang_wei_data_and_skill():
    jiang_wei = get_general_by_name("姜维")

    assert jiang_wei.camp == Camp.SHU
    assert jiang_wei.rarity == Rarity.EPIC
    assert jiang_wei.cost == 2.0
    assert jiang_wei.force == 7
    assert jiang_wei.intelligence == 7
    assert {attr.value for attr in jiang_wei.attribute} == {"募兵"}
    assert jiang_wei.active_skill.name == "挑衅"
    assert jiang_wei.active_skill.morale_cost == 3


def test_taunt_forces_2x2_enemies_to_attack_jiang_wei():
    jiang_wei, ally, enemies, team, enemy_team = build_grid()
    context = BattleContext(team, enemy_team)
    context.skill_options = {"row": 0, "col": 0}

    result = team.use_skill(jiang_wei, [], context)

    assert result["success"] is True
    assert result["targets_affected"] == 3
    assert team.current_morale == 9
    for target in enemies[:3]:
        assert target.get_forced_attack_target() is jiang_wei
    assert enemies[3].get_forced_attack_target() is None

    blocked_damage = enemies[0].attack(ally)
    assert blocked_damage == 0
    damage = enemies[0].attack(jiang_wei)
    assert damage > 0


def test_taunt_expires_when_jiang_wei_defeated():
    jiang_wei, ally, enemies, team, enemy_team = build_grid()
    context = BattleContext(team, enemy_team)
    context.skill_options = {"row": 0, "col": 0}
    team.use_skill(jiang_wei, [], context)

    jiang_wei.take_damage(jiang_wei.current_hp, enemies[0], "skill")

    assert not jiang_wei.is_alive
    assert enemies[0].get_forced_attack_target() is None
    damage = enemies[0].attack(ally)
    assert damage > 0


if __name__ == "__main__":
    test_jiang_wei_data_and_skill()
    test_taunt_forces_2x2_enemies_to_attack_jiang_wei()
    test_taunt_expires_when_jiang_wei_defeated()
    print("姜维挑衅测试通过")
