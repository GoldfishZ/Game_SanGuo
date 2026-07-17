"""
测试汉献帝专属技能“敕命”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_ally(name, force, intelligence=5):
    return General(
        general_id=9700,
        name=name,
        camp=Camp.TA,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_han_xian_di_data_and_skill():
    han_xian_di = get_general_by_name("汉献帝")

    assert han_xian_di.camp == Camp.TA
    assert han_xian_di.rarity == Rarity.COMMON
    assert han_xian_di.cost == 1.0
    assert han_xian_di.force == 1
    assert han_xian_di.intelligence == 5
    assert [attr.value for attr in han_xian_di.attribute] == ["魅力", "防栅"]
    assert han_xian_di.active_skill.name == "敕命"
    assert han_xian_di.active_skill.morale_cost == 4


def test_imperial_edict_buffs_highest_force_ally_and_consumes_morale():
    han_xian_di = get_general_by_name("汉献帝")
    strongest = make_ally("最强武将", 8)
    weaker = make_ally("普通武将", 6)
    team = Team("汉室队")
    enemy_team = Team("敌队")

    for general in [han_xian_di, strongest, weaker]:
        team.add_general(general)

    result = team.use_skill(han_xian_di, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["targets_affected"] == 1
    assert result["details"][0]["target"] == "最强武将"
    assert team.current_morale == 8
    assert strongest.get_effective_force() == 13
    assert weaker.get_effective_force() == 6
    assert han_xian_di.get_effective_force() == 1


def test_imperial_edict_uses_current_effective_force():
    han_xian_di = get_general_by_name("汉献帝")
    base_high = make_ally("基础高武", 8)
    buffed_high = make_ally("临时高武", 6)
    buffed_high.add_buff("force_boost", 3, 1)
    team = Team("汉室队")
    enemy_team = Team("敌队")

    for general in [han_xian_di, base_high, buffed_high]:
        team.add_general(general)

    result = team.use_skill(han_xian_di, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["details"][0]["target"] == "临时高武"
    assert buffed_high.get_effective_force() == 14
    assert base_high.get_effective_force() == 8


if __name__ == "__main__":
    test_han_xian_di_data_and_skill()
    test_imperial_edict_buffs_highest_force_ally_and_consumes_morale()
    test_imperial_edict_uses_current_effective_force()
    print("汉献帝敕命测试通过")
