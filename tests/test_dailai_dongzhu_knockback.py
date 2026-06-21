"""
测试带来洞主专属技能“击飞战术”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(general_id, name, force=3, intelligence=3):
    return General(
        general_id=general_id,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_dailai_dongzhu_data_and_skill():
    dailai = get_general_by_name("带来洞主")

    assert dailai.camp == Camp.TA
    assert dailai.rarity == Rarity.RARE
    assert dailai.cost == 1.5
    assert dailai.force == 5
    assert dailai.intelligence == 3
    assert {attr.value for attr in dailai.attribute} == {"复活"}
    assert dailai.active_skill.name == "击飞战术"
    assert dailai.active_skill.morale_cost == 3


def test_knockback_tactics_swaps_damaged_target_with_rear_general():
    dailai = get_general_by_name("带来洞主")
    front = make_enemy(9701, "前排")
    rear = make_enemy(9702, "后排")
    team = Team("他军")
    enemy_team = Team("敌军")
    team.add_general(dailai)
    enemy_team.add_general(front)
    enemy_team.add_general(rear)
    enemy_team.position_general(front, 0, 0)
    enemy_team.position_general(rear, 1, 0)

    result = team.use_skill(dailai, [], BattleContext(team, enemy_team))
    damage = dailai.attack(front)

    assert result["success"] is True
    assert team.current_morale == 9
    assert dailai.get_effective_force() == 7
    assert damage > 0
    assert enemy_team.get_general_position(front) == (1, 0)
    assert enemy_team.get_general_position(rear) == (0, 0)


def test_knockback_tactics_does_not_move_without_rear_general():
    dailai = get_general_by_name("带来洞主")
    front = make_enemy(9711, "孤立前排")
    team = Team("他军")
    enemy_team = Team("敌军")
    team.add_general(dailai)
    enemy_team.add_general(front)
    enemy_team.position_general(front, 0, 0)

    team.use_skill(dailai, [], BattleContext(team, enemy_team))
    damage = dailai.attack(front)

    assert damage > 0
    assert enemy_team.get_general_position(front) == (0, 0)


if __name__ == "__main__":
    test_dailai_dongzhu_data_and_skill()
    test_knockback_tactics_swaps_damaged_target_with_rear_general()
    test_knockback_tactics_does_not_move_without_rear_general()
    print("带来洞主击飞战术测试通过")
