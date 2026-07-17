"""
测试贾诩专属技能“离间谋略”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name, force=6, intelligence=6):
    return General(
        general_id=9950,
        name=name,
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def build_block():
    jia_xu = get_general_by_name("贾诩")
    enemies = [
        make_enemy("目标A"),
        make_enemy("目标B"),
        make_enemy("目标C"),
        make_enemy("范围外"),
    ]
    team = Team("魏军")
    enemy_team = Team("敌队")

    team.add_general(jia_xu)
    for enemy in enemies:
        enemy_team.add_general(enemy)
    enemy_team.position_general(enemies[0], 0, 0)
    enemy_team.position_general(enemies[1], 0, 1)
    enemy_team.position_general(enemies[2], 1, 0)
    enemy_team.position_general(enemies[3], 2, 3)
    return jia_xu, enemies, team, enemy_team


def test_jia_xu_data_and_skill():
    jia_xu = get_general_by_name("贾诩")

    assert jia_xu.camp == Camp.WEI
    assert jia_xu.rarity == Rarity.COMMON
    assert jia_xu.cost == 1.0
    assert jia_xu.force == 1
    assert jia_xu.intelligence == 9
    assert jia_xu.attribute == []
    assert jia_xu.active_skill.name == "离间谋略"
    assert jia_xu.active_skill.morale_cost == 6


def test_discord_strategy_can_apply_for_ally_attack_immediately():
    jia_xu, enemies, team, enemy_team = build_block()
    context = BattleContext(team, enemy_team)
    context.skill_options = {"row": 0, "col": 0, "timing": "ally_attack"}

    result = team.use_skill(jia_xu, [], context)

    assert result["success"] is True
    assert result["mode"] == "ally_attack"
    assert result["targets_affected"] == 3
    assert team.current_morale == 6
    for target in enemies[:3]:
        assert target.get_effective_force() == 4
        assert target.get_effective_intelligence() == 4
        assert len(target.pending_debuffs) == 0
    assert enemies[3].get_effective_force() == 6
    assert enemies[3].get_effective_intelligence() == 6


def test_discord_strategy_can_wait_until_enemy_attack():
    jia_xu, enemies, team, enemy_team = build_block()
    context = BattleContext(team, enemy_team)
    context.skill_options = {"row": 0, "col": 0, "timing": "enemy_attack"}

    result = team.use_skill(jia_xu, [], context)

    assert result["success"] is True
    assert result["mode"] == "enemy_attack"
    for target in enemies[:3]:
        assert target.get_effective_force() == 6
        assert target.get_effective_intelligence() == 6
        assert len(target.pending_debuffs) == 2

    enemy_team.update_effects()

    for target in enemies[:3]:
        assert target.get_effective_force() == 4
        assert target.get_effective_intelligence() == 4
        assert len(target.pending_debuffs) == 0
    assert enemies[3].get_effective_force() == 6
    assert enemies[3].get_effective_intelligence() == 6


if __name__ == "__main__":
    test_jia_xu_data_and_skill()
    test_discord_strategy_can_apply_for_ally_attack_immediately()
    test_discord_strategy_can_wait_until_enemy_attack()
    print("贾诩离间谋略测试通过")
