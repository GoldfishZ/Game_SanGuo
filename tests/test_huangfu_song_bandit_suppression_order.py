"""
测试皇甫嵩专属技能“贼军讨伐令”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_general(name, camp=Camp.TA, force=4, intelligence=4):
    return General(
        general_id=9300,
        name=name,
        camp=camp,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_huangfu_song_data_and_skill():
    huangfu_song = get_general_by_name("皇甫嵩")

    assert huangfu_song.camp == Camp.TA
    assert huangfu_song.rarity == Rarity.RARE
    assert huangfu_song.cost == 1.5
    assert huangfu_song.force == 5
    assert huangfu_song.intelligence == 5
    assert {attr.value for attr in huangfu_song.attribute} == {"募兵"}
    assert huangfu_song.active_skill.name == "贼军讨伐令"
    assert huangfu_song.active_skill.morale_cost == 5


def test_bandit_suppression_order_buffs_row_by_opposite_enemy_count():
    huangfu_song = get_general_by_name("皇甫嵩")
    ally_same_row = make_general("同排汉军")
    ally_other_row = make_general("异排汉军")
    enemy_a = make_general("黄巾A", Camp.YUAN)
    enemy_b = make_general("黄巾B", Camp.YUAN)
    enemy_other_row = make_general("别排黄巾", Camp.YUAN)
    team = Team("汉军")
    enemy_team = Team("敌军")

    for general in [huangfu_song, ally_same_row, ally_other_row]:
        team.add_general(general)
    for general in [enemy_a, enemy_b, enemy_other_row]:
        enemy_team.add_general(general)
    team.position_general(huangfu_song, 1, 0)
    team.position_general(ally_same_row, 1, 1)
    team.position_general(ally_other_row, 2, 0)
    enemy_team.position_general(enemy_a, 1, 0)
    enemy_team.position_general(enemy_b, 1, 2)
    enemy_team.position_general(enemy_other_row, 2, 0)

    result = team.use_skill(huangfu_song, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["enemy_count"] == 2
    assert result["targets_affected"] == 2
    assert team.current_morale == 7
    assert huangfu_song.get_effective_force() == 7
    assert ally_same_row.get_effective_force() == 6
    assert ally_other_row.get_effective_force() == 4


def test_bandit_suppression_order_can_apply_zero_boost_against_empty_row():
    huangfu_song = get_general_by_name("皇甫嵩")
    team = Team("汉军")
    enemy_team = Team("敌军")
    team.add_general(huangfu_song)
    team.position_general(huangfu_song, 0, 0)

    result = team.use_skill(huangfu_song, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["enemy_count"] == 0
    assert huangfu_song.get_effective_force() == 5


if __name__ == "__main__":
    test_huangfu_song_data_and_skill()
    test_bandit_suppression_order_buffs_row_by_opposite_enemy_count()
    test_bandit_suppression_order_can_apply_zero_boost_against_empty_row()
    print("皇甫嵩贼军讨伐令测试通过")
