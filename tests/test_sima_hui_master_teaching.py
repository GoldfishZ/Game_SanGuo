"""
测试司马徽专属技能“夫子的教诲”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_ally(name, intelligence=5):
    return General(
        general_id=9920,
        name=name,
        camp=Camp.TA,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=3,
        intelligence=intelligence,
    )


def test_sima_hui_data_and_skill():
    sima_hui = get_general_by_name("司马徽")

    assert sima_hui.camp == Camp.TA
    assert sima_hui.rarity == Rarity.COMMON
    assert sima_hui.cost == 1.0
    assert sima_hui.force == 1
    assert sima_hui.intelligence == 8
    assert {"防栅", "募兵"} <= {attr.value for attr in sima_hui.attribute}
    assert sima_hui.active_skill.name == "夫子的教诲"
    assert sima_hui.active_skill.morale_cost == 3


def test_master_teaching_boosts_same_row_intelligence():
    sima_hui = get_general_by_name("司马徽")
    same_row = make_ally("同排友军", 5)
    other_row = make_ally("异排友军", 6)
    team = Team("他军")
    enemy_team = Team("敌队")

    for general in [sima_hui, same_row, other_row]:
        team.add_general(general)
    team.position_general(sima_hui, 1, 0)
    team.position_general(same_row, 1, 2)
    team.position_general(other_row, 2, 0)

    result = team.use_skill(sima_hui, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["targets_affected"] == 2
    assert team.current_morale == 9
    assert sima_hui.get_effective_intelligence() == 10
    assert same_row.get_effective_intelligence() == 7
    assert other_row.get_effective_intelligence() == 6


if __name__ == "__main__":
    test_sima_hui_data_and_skill()
    test_master_teaching_boosts_same_row_intelligence()
    print("司马徽夫子的教诲测试通过")
