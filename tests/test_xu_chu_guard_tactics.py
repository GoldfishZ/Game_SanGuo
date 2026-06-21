"""
测试许褚专属技能“防护战术”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_attacker():
    return General(
        general_id=9908,
        name="测试攻击者",
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=6,
        intelligence=4,
    )


def test_xu_chu_data_and_skill():
    xu_chu = get_general_by_name("许褚")

    assert xu_chu.camp == Camp.WEI
    assert xu_chu.rarity == Rarity.EPIC
    assert xu_chu.cost == 2.0
    assert xu_chu.force == 8
    assert xu_chu.intelligence == 2
    assert {attr.value for attr in xu_chu.attribute} == {"募兵"}
    assert xu_chu.active_skill.name == "防护战术"
    assert xu_chu.active_skill.morale_cost == 4


def test_guard_tactics_reduces_next_damage_once():
    xu_chu = get_general_by_name("许褚")
    attacker = make_attacker()
    team = Team("魏军")
    enemy_team = Team("敌军")
    team.add_general(xu_chu)
    enemy_team.add_general(attacker)
    context = BattleContext(team, enemy_team)

    result = team.use_skill(xu_chu, [], context)

    assert result["success"] is True
    assert team.current_morale == 8
    assert xu_chu.has_buff_type("damage_shield")

    actual_damage = xu_chu.take_damage(5, attacker, "skill")

    assert actual_damage == 2
    assert xu_chu.current_hp == xu_chu.max_hp - 2
    assert not xu_chu.has_buff_type("damage_shield")

    second_damage = xu_chu.take_damage(4, attacker, "skill")

    assert second_damage == 4
    assert xu_chu.current_hp == xu_chu.max_hp - 6


def test_guard_tactics_can_fully_block_small_damage():
    xu_chu = get_general_by_name("许褚")
    attacker = make_attacker()
    team = Team("魏军")
    enemy_team = Team("敌军")
    team.add_general(xu_chu)
    enemy_team.add_general(attacker)
    context = BattleContext(team, enemy_team)

    result = team.use_skill(xu_chu, [], context)
    actual_damage = xu_chu.take_damage(2, attacker, "skill")

    assert result["success"] is True
    assert actual_damage == 0
    assert xu_chu.current_hp == xu_chu.max_hp
    assert not xu_chu.has_buff_type("damage_shield")


if __name__ == "__main__":
    test_xu_chu_data_and_skill()
    test_guard_tactics_reduces_next_damage_once()
    test_guard_tactics_can_fully_block_small_damage()
    print("许褚防护战术测试通过")
