"""
测试于夫罗专属技能“联合围攻”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_ally(name, force=4, intelligence=4):
    return General(
        general_id=9400,
        name=name,
        camp=Camp.YUAN,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_yu_fuluo_data_and_skill():
    yu_fuluo = get_general_by_name("于夫罗")

    assert yu_fuluo.camp == Camp.YUAN
    assert yu_fuluo.rarity == Rarity.COMMON
    assert yu_fuluo.cost == 1.0
    assert yu_fuluo.force == 3
    assert yu_fuluo.intelligence == 3
    assert {attr.value for attr in yu_fuluo.attribute} == {"连计"}
    assert yu_fuluo.active_skill.name == "联合围攻"
    assert yu_fuluo.active_skill.morale_cost == 4


def test_united_siege_boosts_by_alive_allies_count():
    yu_fuluo = get_general_by_name("于夫罗")
    ally_a = make_ally("部族骑兵A")
    ally_b = make_ally("部族骑兵B")
    fallen = make_ally("阵亡骑兵")
    team = Team("袁军")
    enemy_team = Team("敌军")

    for general in [yu_fuluo, ally_a, ally_b, fallen]:
        team.add_general(general)
    fallen.is_alive = False
    fallen.current_hp = 0

    result = team.use_skill(yu_fuluo, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["ally_count"] == 3
    assert team.current_morale == 8
    assert yu_fuluo.get_effective_force() == 6
    assert result["details"][0]["effect"] == "武力+3"


def test_united_siege_counts_only_self_when_alone():
    yu_fuluo = get_general_by_name("于夫罗")
    team = Team("袁军")
    enemy_team = Team("敌军")
    team.add_general(yu_fuluo)

    result = team.use_skill(yu_fuluo, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["ally_count"] == 1
    assert yu_fuluo.get_effective_force() == 4


if __name__ == "__main__":
    test_yu_fuluo_data_and_skill()
    test_united_siege_boosts_by_alive_allies_count()
    test_united_siege_counts_only_self_when_alone()
    print("于夫罗联合围攻测试通过")
