"""
测试于禁专属技能“魏武精英”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy():
    return General(
        general_id=9601,
        name="敌军",
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=4,
        intelligence=4,
    )


def test_yu_jin_data_and_skill():
    yu_jin = get_general_by_name("于禁")

    assert yu_jin.camp == Camp.WEI
    assert yu_jin.rarity == Rarity.RARE
    assert yu_jin.cost == 1.5
    assert yu_jin.force == 5
    assert yu_jin.intelligence == 6
    assert {attr.value for attr in yu_jin.attribute} == {"连计"}
    assert yu_jin.active_skill.name == "魏武精英"
    assert yu_jin.active_skill.morale_cost == 3


def test_wei_elite_boosts_force_for_two_turns():
    yu_jin = get_general_by_name("于禁")
    enemy = make_enemy()
    team = Team("魏军")
    enemy_team = Team("敌军")
    team.add_general(yu_jin)
    enemy_team.add_general(enemy)

    result = team.use_skill(yu_jin, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 9
    assert yu_jin.get_effective_force() == 7
    assert yu_jin.buffs[0]["duration"] == 2

    yu_jin.update_effects()
    assert yu_jin.get_effective_force() == 7
    assert yu_jin.buffs[0]["duration"] == 1

    yu_jin.update_effects()
    assert yu_jin.get_effective_force() == 5
    assert yu_jin.buffs == []


if __name__ == "__main__":
    test_yu_jin_data_and_skill()
    test_wei_elite_boosts_force_for_two_turns()
    print("于禁魏武精英测试通过")
