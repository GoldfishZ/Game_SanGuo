"""
测试张角专属技能“太平要术”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_ally(name, force=4, intelligence=4):
    return General(
        general_id=9940,
        name=name,
        camp=Camp.TA,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def kill(general):
    general.current_hp = 0
    general.is_alive = False


def test_zhang_jiao_data_and_skill():
    zhang_jiao = get_general_by_name("张角")

    assert zhang_jiao.camp == Camp.TA
    assert zhang_jiao.rarity == Rarity.COMMON
    assert zhang_jiao.cost == 1.0
    assert zhang_jiao.force == 2
    assert zhang_jiao.intelligence == 8
    assert "魅力" in [attr.value for attr in zhang_jiao.attribute]
    assert zhang_jiao.active_skill.name == "太平要术"
    assert zhang_jiao.active_skill.morale_cost == 6


def test_taiping_arts_revives_all_dead_allies_at_half_hp():
    zhang_jiao = get_general_by_name("张角")
    dead_a = make_ally("阵亡甲", 5, 5)
    dead_b = make_ally("阵亡乙", 3, 4)
    alive = make_ally("存活友军", 4, 6)
    team = Team("黄巾军")
    enemy_team = Team("敌队")

    for general in [zhang_jiao, dead_a, dead_b, alive]:
        team.add_general(general)
    kill(dead_a)
    kill(dead_b)
    alive.current_hp = 3

    result = team.use_skill(zhang_jiao, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["targets_affected"] == 2
    assert result["uses_remaining"] == 1
    assert team.current_morale == 6
    assert dead_a.is_alive is True
    assert dead_a.current_hp == dead_a.max_hp // 2
    assert dead_b.is_alive is True
    assert dead_b.current_hp == dead_b.max_hp // 2
    assert alive.current_hp == 3


def test_taiping_arts_can_only_be_used_twice_per_game():
    zhang_jiao = get_general_by_name("张角")
    dead = make_ally("阵亡友军", 4, 4)
    team = Team("黄巾军")
    enemy_team = Team("敌队")

    team.add_general(zhang_jiao)
    team.add_general(dead)
    kill(dead)

    first = team.use_skill(zhang_jiao, [], BattleContext(team, enemy_team))
    assert first["success"] is True
    assert team.current_morale == 6

    team.current_morale = 12
    kill(dead)
    second = team.use_skill(zhang_jiao, [], BattleContext(team, enemy_team))
    assert second["success"] is True
    assert team.current_morale == 6

    team.current_morale = 12
    kill(dead)
    third = team.use_skill(zhang_jiao, [], BattleContext(team, enemy_team))
    assert third["success"] is False
    assert team.current_morale == 12
    assert dead.is_alive is False


if __name__ == "__main__":
    test_zhang_jiao_data_and_skill()
    test_taiping_arts_revives_all_dead_allies_at_half_hp()
    test_taiping_arts_can_only_be_used_twice_per_game()
    print("张角太平要术测试通过")
