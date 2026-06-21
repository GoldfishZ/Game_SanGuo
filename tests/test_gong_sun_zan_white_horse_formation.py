"""
测试公孙瓒专属技能“白马阵”。
"""

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_general(name, force=5, intelligence=5):
    return General(
        general_id=9200,
        name=name,
        camp=Camp.TA,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def make_enemy(name="靶子", force=4, intelligence=10):
    return General(
        general_id=9201,
        name=name,
        camp=Camp.YUAN,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_gong_sun_zan_data_and_skill():
    gong_sun_zan = get_general_by_name("公孙瓒")

    assert gong_sun_zan.camp == Camp.TA
    assert gong_sun_zan.rarity == Rarity.RARE
    assert gong_sun_zan.cost == 1.5
    assert gong_sun_zan.force == 5
    assert gong_sun_zan.intelligence == 5
    assert {"魅力", "募兵"} <= {attr.value for attr in gong_sun_zan.attribute}
    assert gong_sun_zan.active_skill.name == "白马阵"
    assert gong_sun_zan.active_skill.morale_cost == 5


def test_white_horse_formation_grants_attack_speed_to_same_row():
    gong_sun_zan = get_general_by_name("公孙瓒")
    same_row = make_general("白马义从")
    other_row = make_general("后排骑兵")
    team = Team("白马军")
    enemy_team = Team("敌军")

    for general in [gong_sun_zan, same_row, other_row]:
        team.add_general(general)
    team.position_general(gong_sun_zan, 1, 0)
    team.position_general(same_row, 1, 1)
    team.position_general(other_row, 2, 0)

    result = team.use_skill(gong_sun_zan, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["targets_affected"] == 2
    assert team.current_morale == 7
    assert gong_sun_zan.has_buff_type("attack_speed_judgment")
    assert same_row.has_buff_type("attack_speed_judgment")
    assert not other_row.has_buff_type("attack_speed_judgment")


def test_white_horse_formation_attack_speed_can_double_attack():
    gong_sun_zan = get_general_by_name("公孙瓒")
    target = make_enemy()
    team = Team("白马军")
    enemy_team = Team("敌军")
    team.add_general(gong_sun_zan)
    enemy_team.add_general(target)
    team.position_general(gong_sun_zan, 0, 0)

    team.use_skill(gong_sun_zan, [], BattleContext(team, enemy_team))

    with patch("src.models.general.random.choice", return_value="odd"), \
            patch("src.models.general.random.randint", return_value=3):
        damage = gong_sun_zan.attack(target)

    assert damage == 2
    assert target.current_hp == target.max_hp - 2
    assert not gong_sun_zan.has_buff_type("attack_speed_judgment")
    assert gong_sun_zan.last_attack_speed_judgment["success"] is True


if __name__ == "__main__":
    test_gong_sun_zan_data_and_skill()
    test_white_horse_formation_grants_attack_speed_to_same_row()
    test_white_horse_formation_attack_speed_can_double_attack()
    print("公孙瓒白马阵测试通过")
