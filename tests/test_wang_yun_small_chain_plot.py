"""
测试王允专属技能“小连环计”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name, force=6, intelligence=4):
    return General(
        general_id=9970,
        name=name,
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def build_grid():
    wang_yun = get_general_by_name("王允")
    enemies = [
        make_enemy("目标A"),
        make_enemy("目标B"),
        make_enemy("目标C"),
    ]
    team = Team("他军")
    enemy_team = Team("敌军")

    team.add_general(wang_yun)
    for enemy in enemies:
        enemy_team.add_general(enemy)
    enemy_team.position_general(enemies[0], 0, 0)
    enemy_team.position_general(enemies[1], 1, 0)
    enemy_team.position_general(enemies[2], 0, 1)
    return wang_yun, enemies, team, enemy_team


def test_wang_yun_data_and_skill():
    wang_yun = get_general_by_name("王允")

    assert wang_yun.camp == Camp.TA
    assert wang_yun.rarity == Rarity.COMMON
    assert wang_yun.cost == 1.0
    assert wang_yun.force == 2
    assert wang_yun.intelligence == 8
    assert wang_yun.attribute == []
    assert wang_yun.active_skill.name == "小连环计"
    assert wang_yun.active_skill.morale_cost == 5


def test_small_chain_plot_delays_attack_block():
    wang_yun, enemies, team, enemy_team = build_grid()
    context = BattleContext(team, enemy_team)
    context.skill_options = {"row": 0, "col": 0}

    result = team.use_skill(wang_yun, [], context)

    assert result["success"] is True
    assert result["targets_affected"] == 2
    assert result["block"] == [(0, 0), (1, 0)]
    assert team.current_morale == 7
    assert len(enemies[0].pending_debuffs) == 1
    assert len(enemies[1].pending_debuffs) == 1
    assert len(enemies[2].pending_debuffs) == 0

    enemy_team.update_effects()
    assert enemies[0].has_debuff_type("attack_speed_required")
    assert enemies[1].has_debuff_type("attack_speed_required")
    assert not enemies[2].has_debuff_type("attack_speed_required")


if __name__ == "__main__":
    test_wang_yun_data_and_skill()
    test_small_chain_plot_delays_attack_block()
    print("王允小连环计测试通过")
