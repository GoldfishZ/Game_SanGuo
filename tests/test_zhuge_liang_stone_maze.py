"""
测试诸葛亮专属技能：石兵八阵
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext, BattleSystem
from tests.test_game_flow import MockBattleCallbacks
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_general(name):
    return General(
        general_id=9001,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=5,
        intelligence=5,
    )


def test_zhuge_liang_data_and_skill():
    zhuge = get_general_by_name("诸葛亮")

    assert zhuge.force == 3
    assert zhuge.intelligence == 10
    assert zhuge.cost == 1.5
    assert "防栅" in [attr.value for attr in zhuge.attribute]
    assert zhuge.active_skill.name == "石兵八阵"
    assert zhuge.active_skill.morale_cost == 4


def test_stone_maze_rearranges_enemy_2x2_then_reverts():
    zhuge = get_general_by_name("诸葛亮")
    ally = make_general("友军")
    e1 = make_general("敌1")
    e2 = make_general("敌2")
    e3 = make_general("敌3")
    e4 = make_general("敌4")

    team = Team("诸葛队")
    enemy_team = Team("敌队")
    team.add_general(zhuge)
    team.add_general(ally)
    enemy_team.add_general(e1)
    enemy_team.add_general(e2)
    enemy_team.add_general(e3)
    enemy_team.add_general(e4)

    team.position_general(zhuge, 0, 0)
    team.position_general(ally, 0, 1)
    enemy_team.position_general(e1, 0, 0)
    enemy_team.position_general(e2, 0, 1)
    enemy_team.position_general(e3, 1, 0)
    enemy_team.position_general(e4, 1, 1)

    original_positions = {
        general.name: enemy_team.get_general_position(general)
        for general in [e1, e2, e3, e4]
    }

    result = team.use_skill(zhuge, [zhuge], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 8
    assert enemy_team.get_general_position(e1) != original_positions["敌1"]
    assert enemy_team.get_general_position(e4) != original_positions["敌4"]

    enemy_team.revert_temporary_formations()

    assert {
        general.name: enemy_team.get_general_position(general)
        for general in [e1, e2, e3, e4]
    } == original_positions


def test_battle_system_reverts_stone_maze_at_turn_end():
    zhuge = get_general_by_name("诸葛亮")
    enemy = make_general("敌1")
    team = Team("玩家1的队伍")
    enemy_team = Team("玩家2的队伍")
    team.add_general(zhuge)
    enemy_team.add_general(enemy)
    team.position_general(zhuge, 0, 0)
    enemy_team.position_general(enemy, 0, 0)

    original_position = enemy_team.get_general_position(enemy)
    battle = BattleSystem(team, enemy_team, MockBattleCallbacks(), "玩家1的队伍")
    battle._execute_turn()

    assert enemy_team.get_general_position(enemy) == original_position


if __name__ == "__main__":
    test_zhuge_liang_data_and_skill()
    test_stone_maze_rearranges_enemy_2x2_then_reverts()
    test_battle_system_reverts_stone_maze_at_turn_end()
    print("诸葛亮石兵八阵测试通过")
