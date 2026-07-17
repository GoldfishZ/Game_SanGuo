"""
测试董卓专属技能“人马大号令”。
"""

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_general(name, force=5, intelligence=5):
    return General(
        general_id=9600,
        name=name,
        camp=Camp.LIANG,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def make_enemy(name="靶子", force=5, intelligence=10):
    return General(
        general_id=9601,
        name=name,
        camp=Camp.WU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_dong_zhuo_data_and_skill():
    dong_zhuo = get_general_by_name("董卓")

    assert dong_zhuo.camp == Camp.LIANG
    assert dong_zhuo.rarity == Rarity.EPIC
    assert dong_zhuo.cost == 2.5
    assert dong_zhuo.force == 8
    assert dong_zhuo.intelligence == 7
    assert "魅力" in [attr.value for attr in dong_zhuo.attribute]
    assert dong_zhuo.active_skill.name == "人马大号令"
    assert dong_zhuo.active_skill.morale_cost == 7


def test_grand_cavalry_order_buffs_same_row_and_consumes_morale():
    dong_zhuo = get_general_by_name("董卓")
    ally_same_row = make_general("同排骑兵")
    ally_other_row = make_general("异排骑兵")
    team = Team("董卓队")
    enemy_team = Team("敌队")

    for general in [dong_zhuo, ally_same_row, ally_other_row]:
        team.add_general(general)
    team.position_general(dong_zhuo, 1, 0)
    team.position_general(ally_same_row, 1, 1)
    team.position_general(ally_other_row, 2, 0)

    result = team.use_skill(dong_zhuo, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["targets_affected"] == 2
    assert team.current_morale == 5
    assert dong_zhuo.get_effective_force() == 12
    assert ally_same_row.get_effective_force() == 9
    assert ally_other_row.get_effective_force() == 5
    assert dong_zhuo.has_buff_type("attack_speed_judgment")
    assert ally_same_row.has_buff_type("attack_speed_judgment")
    assert not ally_other_row.has_buff_type("attack_speed_judgment")


def test_grand_cavalry_order_attack_speed_judgment_can_double_attack():
    dong_zhuo = get_general_by_name("董卓")
    target = make_enemy()
    team = Team("董卓队")
    enemy_team = Team("敌队")
    team.add_general(dong_zhuo)
    enemy_team.add_general(target)
    team.position_general(dong_zhuo, 0, 0)

    team.use_skill(dong_zhuo, [], BattleContext(team, enemy_team))

    with patch("src.models.general.random.choice", return_value="odd"), \
            patch("src.models.general.random.randint", return_value=3):
        damage = dong_zhuo.attack(target)

    assert damage == 14
    assert target.current_hp == target.max_hp - 14
    assert not dong_zhuo.has_buff_type("attack_speed_judgment")
    assert dong_zhuo.last_attack_speed_judgment["success"] is True


if __name__ == "__main__":
    test_dong_zhuo_data_and_skill()
    test_grand_cavalry_order_buffs_same_row_and_consumes_morale()
    test_grand_cavalry_order_attack_speed_judgment_can_double_attack()
    print("董卓人马大号令测试通过")
