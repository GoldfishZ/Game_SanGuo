"""
测试王异专属技能“以牙还牙”。
"""

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name, force=6, intelligence=4):
    return General(
        general_id=9960,
        name=name,
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def build_enemy_grid():
    wang_yi = get_general_by_name("王异")
    enemies = [
        make_enemy("目标A"),
        make_enemy("目标B"),
        make_enemy("目标C"),
        make_enemy("范围外"),
    ]
    team = Team("魏军")
    enemy_team = Team("敌队")

    team.add_general(wang_yi)
    for enemy in enemies:
        enemy_team.add_general(enemy)
    enemy_team.position_general(enemies[0], 0, 0)
    enemy_team.position_general(enemies[1], 0, 1)
    enemy_team.position_general(enemies[2], 1, 0)
    enemy_team.position_general(enemies[3], 2, 3)
    return wang_yi, enemies, team, enemy_team


def test_wang_yi_data_and_skill():
    wang_yi = get_general_by_name("王异")

    assert wang_yi.camp == Camp.WEI
    assert wang_yi.rarity == Rarity.RARE
    assert wang_yi.cost == 1.5
    assert wang_yi.force == 4
    assert wang_yi.intelligence == 8
    assert {"魅力", "防栅"} <= {attr.value for attr in wang_yi.attribute}
    assert wang_yi.active_skill.name == "以牙还牙"
    assert wang_yi.active_skill.morale_cost == 5


def test_tooth_for_tooth_wide_mode_reduces_2x2_force():
    wang_yi, enemies, team, enemy_team = build_enemy_grid()
    context = BattleContext(team, enemy_team)
    context.skill_options = {"mode": "wide", "row": 0, "col": 0}

    result = team.use_skill(wang_yi, [], context)

    assert result["success"] is True
    assert result["mode"] == "wide"
    assert result["targets_affected"] == 3
    assert team.current_morale == 7
    for target in enemies[:3]:
        assert target.get_effective_force() == 3
        assert not target.has_debuff_type("attack_speed_required")
    assert enemies[3].get_effective_force() == 6


def test_tooth_for_tooth_focused_mode_requires_next_attack_judgment():
    wang_yi, enemies, team, enemy_team = build_enemy_grid()
    context = BattleContext(team, enemy_team)
    context.skill_options = {"mode": "focused", "row": 0, "col": 0}

    result = team.use_skill(wang_yi, [], context)

    assert result["success"] is True
    assert result["mode"] == "focused"
    assert result["targets_affected"] == 2
    for target in [enemies[0], enemies[2]]:
        assert target.get_effective_force() == 3
        assert len(target.pending_debuffs) == 1
    assert enemies[1].get_effective_force() == 6

    enemy_team.update_effects()
    assert enemies[0].has_debuff_type("attack_speed_required")

    with patch("src.models.general.random.choice", return_value="odd"), \
            patch("src.models.general.random.randint", return_value=2):
        damage = enemies[0].attack(wang_yi)

    assert damage == 0
    assert enemies[0].last_attack_speed_judgment["success"] is False
    assert not enemies[0].has_debuff_type("attack_speed_required")


if __name__ == "__main__":
    test_wang_yi_data_and_skill()
    test_tooth_for_tooth_wide_mode_reduces_2x2_force()
    test_tooth_for_tooth_focused_mode_requires_next_attack_judgment()
    print("王异以牙还牙测试通过")
