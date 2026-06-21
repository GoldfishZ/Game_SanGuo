"""
测试陈宫专属技能“破坏性的献策”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_ally(name, force=6, intelligence=4):
    return General(
        general_id=9500,
        name=name,
        camp=Camp.LIANG,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_chen_gong_data_and_skill():
    chen_gong = get_general_by_name("陈宫")

    assert chen_gong.camp == Camp.LIANG
    assert chen_gong.rarity == Rarity.RARE
    assert chen_gong.cost == 1.5
    assert chen_gong.force == 4
    assert chen_gong.intelligence == 7
    assert {attr.value for attr in chen_gong.attribute} == {"防栅"}
    assert chen_gong.active_skill.name == "破坏性的献策"
    assert chen_gong.active_skill.morale_cost == 3


def test_destructive_advice_buffs_highest_force_ally_and_hurts_caster():
    chen_gong = get_general_by_name("陈宫")
    strongest = make_ally("强袭武将", force=8, intelligence=3)
    weaker = make_ally("普通武将", force=5, intelligence=7)
    team = Team("西凉军")
    enemy_team = Team("敌军")

    for general in [chen_gong, strongest, weaker]:
        team.add_general(general)

    result = team.use_skill(chen_gong, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 9
    assert result["self_damage"] == 4
    assert strongest.get_effective_force() == 13
    assert weaker.get_effective_force() == 5
    assert chen_gong.current_hp == chen_gong.max_hp - 4


def test_destructive_advice_doubles_effect_on_lv_bu():
    chen_gong = get_general_by_name("陈宫")
    lv_bu = get_general_by_name("吕布")
    ally = make_ally("副将", force=8, intelligence=8)
    team = Team("西凉军")
    enemy_team = Team("敌军")

    for general in [chen_gong, lv_bu, ally]:
        team.add_general(general)

    result = team.use_skill(chen_gong, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["details"][0]["target"] == "吕布"
    assert lv_bu.get_effective_force() == 20
    assert ally.get_effective_force() == 8
    assert chen_gong.current_hp == chen_gong.max_hp - 4


if __name__ == "__main__":
    test_chen_gong_data_and_skill()
    test_destructive_advice_buffs_highest_force_ally_and_hurts_caster()
    test_destructive_advice_doubles_effect_on_lv_bu()
    print("陈宫破坏性的献策测试通过")
