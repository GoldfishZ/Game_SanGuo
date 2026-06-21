"""
测试马岱专属技能“质实刚健”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy():
    return General(
        general_id=9501,
        name="敌军",
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=4,
        intelligence=4,
    )


def test_ma_dai_data_and_skill():
    ma_dai = get_general_by_name("马岱")

    assert ma_dai.camp == Camp.SHU
    assert ma_dai.rarity == Rarity.RARE
    assert ma_dai.cost == 1.5
    assert ma_dai.force == 5
    assert ma_dai.intelligence == 7
    assert {attr.value for attr in ma_dai.attribute} == {"伏兵"}
    assert ma_dai.active_skill.name == "质实刚健"
    assert ma_dai.active_skill.morale_cost == 3


def test_steadfast_clears_debuffs_and_blocks_new_debuffs():
    ma_dai = get_general_by_name("马岱")
    enemy = make_enemy()
    team = Team("蜀军")
    enemy_team = Team("敌军")
    team.add_general(ma_dai)
    enemy_team.add_general(enemy)

    ma_dai.add_debuff("force_reduction", 3, 1)
    assert ma_dai.get_effective_force() == 2

    result = team.use_skill(ma_dai, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 9
    assert ma_dai.get_effective_force() == 7
    assert ma_dai.has_buff_type("debuff_immunity")
    assert ma_dai.debuffs == []

    ma_dai.add_debuff("force_reduction", 3, 1)
    ma_dai.add_debuff("intelligence_reduction", 3, 1)

    assert ma_dai.debuffs == []
    assert ma_dai.get_effective_force() == 7
    assert ma_dai.get_effective_intelligence() == 7


if __name__ == "__main__":
    test_ma_dai_data_and_skill()
    test_steadfast_clears_debuffs_and_blocks_new_debuffs()
    print("马岱质实刚健测试通过")
