"""
测试夏侯惇专属技能“魏王的卫兵”。
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
        general_id=9200,
        name=name,
        camp=Camp.WU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_xiahou_dun_data_and_skill():
    xiahou_dun = get_general_by_name("夏侯惇")

    assert xiahou_dun.camp == Camp.WEI
    assert xiahou_dun.force == 8
    assert xiahou_dun.intelligence == 6
    assert "勇猛" in [attr.value for attr in xiahou_dun.attribute]
    assert xiahou_dun.active_skill.name == "魏王的卫兵"
    assert xiahou_dun.active_skill.morale_cost == 4


def test_wei_king_guard_grants_force_and_one_double_attack_judgment():
    xiahou_dun = get_general_by_name("夏侯惇")
    target = make_enemy("靶子", force=5, intelligence=10)
    team = Team("魏军")
    enemy_team = Team("敌军")
    team.add_general(xiahou_dun)
    enemy_team.add_general(target)

    result = team.use_skill(xiahou_dun, [xiahou_dun], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 8
    assert xiahou_dun.get_effective_force() == 11
    assert xiahou_dun.has_buff_type("attack_speed_judgment")

    with patch("src.models.general.random.choice", return_value="odd"), \
            patch("src.models.general.random.randint", return_value=3):
        damage = xiahou_dun.attack(target)

    assert damage == 12
    assert target.current_hp == target.max_hp - 12
    assert not xiahou_dun.has_buff_type("attack_speed_judgment")
    assert xiahou_dun.last_attack_speed_judgment["success"] is True


def test_xiahou_dun_passively_shares_cao_cao_damage():
    xiahou_dun = get_general_by_name("夏侯惇")
    cao_cao = get_general_by_name("曹操")
    attacker = make_enemy("攻击者", force=12, intelligence=4)
    team = Team("魏军")
    enemy_team = Team("敌军")
    team.add_general(xiahou_dun)
    team.add_general(cao_cao)
    enemy_team.add_general(attacker)

    actual_damage = cao_cao.take_damage(5, attacker, "skill")

    assert actual_damage == 2
    assert cao_cao.current_hp == cao_cao.max_hp - 2
    assert xiahou_dun.current_hp == xiahou_dun.max_hp - 3


if __name__ == "__main__":
    test_xiahou_dun_data_and_skill()
    test_wei_king_guard_grants_force_and_one_double_attack_judgment()
    test_xiahou_dun_passively_shares_cao_cao_damage()
    print("夏侯惇魏王的卫兵测试通过")
