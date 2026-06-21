"""
测试张郃专属技能“率先立功”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, Rarity
from src.models.team import Team


def test_zhang_he_data_and_skill():
    zhang_he = get_general_by_name("张郃")

    assert zhang_he.camp == Camp.YUAN
    assert zhang_he.rarity == Rarity.RARE
    assert zhang_he.cost == 1.5
    assert zhang_he.force == 6
    assert zhang_he.intelligence == 5
    assert zhang_he.attribute == []
    assert zhang_he.active_skill.name == "率先立功"
    assert zhang_he.active_skill.morale_cost == 3


def test_first_merit_rewards_morale_next_turn_if_alive():
    zhang_he = get_general_by_name("张郃")
    team = Team("袁军")
    enemy_team = Team("敌军")
    team.add_general(zhang_he)

    result = team.use_skill(zhang_he, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 9
    assert zhang_he.get_effective_force() == 8
    assert len(team.pending_morale_rewards) == 1

    team.update_effects()

    assert team.current_morale == 11
    assert team.pending_morale_rewards == []


def test_first_merit_reward_fails_if_zhang_he_dies():
    zhang_he = get_general_by_name("张郃")
    team = Team("袁军")
    enemy_team = Team("敌军")
    team.add_general(zhang_he)

    result = team.use_skill(zhang_he, [], BattleContext(team, enemy_team))
    zhang_he.take_damage(zhang_he.current_hp, damage_source="skill")
    team.update_effects()

    assert result["success"] is True
    assert not zhang_he.is_alive
    assert team.current_morale == 9
    assert team.pending_morale_rewards == []


if __name__ == "__main__":
    test_zhang_he_data_and_skill()
    test_first_merit_rewards_morale_next_turn_if_alive()
    test_first_merit_reward_fails_if_zhang_he_dies()
    print("张郃率先立功测试通过")
