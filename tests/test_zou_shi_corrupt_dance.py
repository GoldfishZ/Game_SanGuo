"""
测试邹氏专属技能“堕落之舞”。
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
        general_id=9995,
        name=name,
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def build_enemies():
    zou_shi = get_general_by_name("邹氏")
    enemies = [
        make_enemy("敌将A"),
        make_enemy("敌将B"),
        make_enemy("已阵亡"),
    ]
    team = Team("凉军")
    enemy_team = Team("敌军")

    team.add_general(zou_shi)
    team.position_general(zou_shi, 0, 0)
    for enemy in enemies:
        enemy_team.add_general(enemy)
    enemy_team.position_general(enemies[0], 0, 0)
    enemy_team.position_general(enemies[1], 1, 0)
    enemy_team.position_general(enemies[2], 2, 0)
    enemies[2].take_damage(enemies[2].current_hp, damage_source="skill")
    return zou_shi, enemies, team, enemy_team


def test_zou_shi_data_and_skill():
    zou_shi = get_general_by_name("邹氏")

    assert zou_shi.camp == Camp.LIANG
    assert zou_shi.rarity == Rarity.COMMON
    assert zou_shi.cost == 1.0
    assert zou_shi.force == 2
    assert zou_shi.intelligence == 7
    assert {"伏兵", "魅力"} <= {attr.value for attr in zou_shi.attribute}
    assert zou_shi.active_skill.name == "堕落之舞"
    assert zou_shi.active_skill.morale_cost == 5


def test_corrupt_dance_damages_all_alive_enemies():
    zou_shi, enemies, team, enemy_team = build_enemies()
    context = BattleContext(team, enemy_team)

    result = team.use_skill(zou_shi, [], context)

    assert result["success"] is True
    assert result["targets_affected"] == 2
    assert result["total_damage"] == 2
    assert team.current_morale == 7
    assert enemies[0].current_hp == enemies[0].max_hp - 1
    assert enemies[1].current_hp == enemies[1].max_hp - 1
    assert enemies[2].current_hp == 0


if __name__ == "__main__":
    test_zou_shi_data_and_skill()
    test_corrupt_dance_damages_all_alive_enemies()
    print("邹氏堕落之舞测试通过")
