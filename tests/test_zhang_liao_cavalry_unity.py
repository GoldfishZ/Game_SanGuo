"""
测试张辽专属技能“人马一体”。
"""

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name, force=4, intelligence=10):
    return General(
        general_id=9300,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_zhang_liao_data_and_skill():
    zhang_liao = get_general_by_name("张辽")

    assert zhang_liao.camp == Camp.LIANG
    assert zhang_liao.force == 7
    assert zhang_liao.intelligence == 6
    assert "连计" in [attr.value for attr in zhang_liao.attribute]
    assert zhang_liao.active_skill.name == "人马一体"
    assert zhang_liao.active_skill.morale_cost == 3


def test_cavalry_unity_grants_force_and_one_double_attack_judgment():
    zhang_liao = get_general_by_name("张辽")
    target = make_enemy("靶子")
    team = Team("西凉骑军")
    enemy_team = Team("敌军")
    team.add_general(zhang_liao)
    enemy_team.add_general(target)

    result = team.use_skill(zhang_liao, [zhang_liao], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 9
    assert zhang_liao.get_effective_force() == 9
    assert zhang_liao.has_buff_type("attack_speed_judgment")

    with patch("src.models.general.random.choice", return_value="even"), \
            patch("src.models.general.random.randint", return_value=4):
        damage = zhang_liao.attack(target)

    assert damage == 10
    assert target.current_hp == target.max_hp - 10
    assert not zhang_liao.has_buff_type("attack_speed_judgment")
    assert zhang_liao.last_attack_speed_judgment["success"] is True


if __name__ == "__main__":
    test_zhang_liao_data_and_skill()
    test_cavalry_unity_grants_force_and_one_double_attack_judgment()
    print("张辽人马一体测试通过")
