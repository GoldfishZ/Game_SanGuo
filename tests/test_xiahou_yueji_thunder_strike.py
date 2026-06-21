"""
测试夏侯月姬专属技能“雷击”。
"""

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name, intelligence=4):
    return General(
        general_id=9910,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=5,
        intelligence=intelligence,
    )


def build_enemy_block():
    xiahou_yueji = get_general_by_name("夏侯月姬")
    target_a = make_enemy("雷击目标A", 4)
    target_b = make_enemy("雷击目标B", 4)
    outside = make_enemy("范围外目标", 1)
    team = Team("蜀军")
    enemy_team = Team("敌队")

    team.add_general(xiahou_yueji)
    enemy_team.add_general(target_a)
    enemy_team.add_general(target_b)
    enemy_team.add_general(outside)
    enemy_team.position_general(target_a, 0, 0)
    enemy_team.position_general(target_b, 0, 1)
    enemy_team.position_general(outside, 2, 3)
    return xiahou_yueji, target_a, target_b, outside, team, enemy_team


def test_xiahou_yueji_data_and_skill():
    xiahou_yueji = get_general_by_name("夏侯月姬")

    assert xiahou_yueji.camp == Camp.SHU
    assert xiahou_yueji.rarity == Rarity.COMMON
    assert xiahou_yueji.cost == 1.0
    assert xiahou_yueji.force == 2
    assert xiahou_yueji.intelligence == 7
    assert "魅力" in [attr.value for attr in xiahou_yueji.attribute]
    assert xiahou_yueji.active_skill.name == "雷击"
    assert xiahou_yueji.active_skill.morale_cost == 6


def test_thunder_strike_deals_damage_when_enemy_guess_fails():
    xiahou_yueji, target_a, target_b, outside, team, enemy_team = build_enemy_block()

    with patch("src.models.general.random.choice", return_value="odd"), \
            patch("src.models.general.random.randint", return_value=2):
        result = team.use_skill(xiahou_yueji, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["strike_count"] == 2
    assert result["total_damage"] == 12
    assert team.current_morale == 6
    assert target_a.current_hp == target_a.max_hp - 6
    assert target_b.current_hp == target_b.max_hp - 6
    assert outside.current_hp == outside.max_hp


def test_thunder_strike_no_damage_when_enemy_guess_succeeds():
    xiahou_yueji, target_a, target_b, outside, team, enemy_team = build_enemy_block()

    with patch("src.models.general.random.choice", return_value="even"), \
            patch("src.models.general.random.randint", return_value=2):
        result = team.use_skill(xiahou_yueji, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["total_damage"] == 0
    assert target_a.current_hp == target_a.max_hp
    assert target_b.current_hp == target_b.max_hp


if __name__ == "__main__":
    test_xiahou_yueji_data_and_skill()
    test_thunder_strike_deals_damage_when_enemy_guess_fails()
    test_thunder_strike_no_damage_when_enemy_guess_succeeds()
    print("夏侯月姬雷击测试通过")
