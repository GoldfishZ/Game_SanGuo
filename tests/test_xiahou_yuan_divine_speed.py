"""
测试夏侯渊专属技能“神速战术”。
"""

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name="靶子", force=5, intelligence=10):
    return General(
        general_id=9100,
        name=name,
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_xiahou_yuan_data_and_skill():
    xiahou_yuan = get_general_by_name("夏侯渊")

    assert xiahou_yuan.camp == Camp.WEI
    assert xiahou_yuan.rarity == Rarity.EPIC
    assert xiahou_yuan.cost == 2.0
    assert xiahou_yuan.force == 8
    assert xiahou_yuan.intelligence == 4
    assert {attr.value for attr in xiahou_yuan.attribute} == {"募兵"}
    assert xiahou_yuan.active_skill.name == "神速战术"
    assert xiahou_yuan.active_skill.morale_cost == 4


def test_divine_speed_grants_force_and_attack_speed_judgment():
    xiahou_yuan = get_general_by_name("夏侯渊")
    target = make_enemy()
    team = Team("魏军")
    enemy_team = Team("敌军")
    team.add_general(xiahou_yuan)
    enemy_team.add_general(target)

    result = team.use_skill(xiahou_yuan, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 8
    assert xiahou_yuan.get_effective_force() == 10
    assert xiahou_yuan.has_buff_type("attack_speed_judgment")

    with patch("src.models.general.random.choice", return_value="even"), \
            patch("src.models.general.random.randint", return_value=4):
        damage = xiahou_yuan.attack(target)

    assert damage == 5
    assert target.current_hp == target.max_hp - 5
    assert not xiahou_yuan.has_buff_type("attack_speed_judgment")
    assert xiahou_yuan.last_attack_speed_judgment["success"] is True
    assert xiahou_yuan.can_attack()

    second_damage = xiahou_yuan.attack(target)
    assert second_damage == 5
    assert target.current_hp == target.max_hp - 10
    assert not xiahou_yuan.can_attack()


if __name__ == "__main__":
    test_xiahou_yuan_data_and_skill()
    test_divine_speed_grants_force_and_attack_speed_judgment()
    print("夏侯渊神速战术测试通过")
