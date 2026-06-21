"""
测试朱然专属技能“防栅重建”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from game_data.passive_skills_config import get_passive_skills_for_attributes
from src.battle.battle_system import BattleContext
from src.models.general import Attribute, Camp, General, Rarity
from src.models.team import Team


def make_general(name, attributes=None):
    general = General(
        general_id=9930,
        name=name,
        camp=Camp.WU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=3,
        intelligence=4,
        attribute=attributes or [],
    )
    general.passive_skills = get_passive_skills_for_attributes(general.attribute)
    return general


def break_fence(general):
    fence = general.get_passive_skill("防栅")
    fence.is_active = False
    fence.rebuild_turns_remaining = 2
    return fence


def test_zhu_ran_data_and_skill():
    zhu_ran = get_general_by_name("朱然")

    assert zhu_ran.camp == Camp.WU
    assert zhu_ran.rarity == Rarity.RARE
    assert zhu_ran.cost == 1.5
    assert zhu_ran.force == 4
    assert zhu_ran.intelligence == 6
    assert {"防栅", "募兵"} <= {attr.value for attr in zhu_ran.attribute}
    assert zhu_ran.active_skill.name == "防栅重建"
    assert zhu_ran.active_skill.morale_cost == 6


def test_fence_rebuild_restores_all_alive_ally_fences_only():
    zhu_ran = get_general_by_name("朱然")
    ally_fence = make_general("友军防栅", [Attribute.FENCE])
    ally_no_fence = make_general("无栅友军")
    dead_fence = make_general("阵亡防栅", [Attribute.FENCE])
    enemy_fence = make_general("敌方防栅", [Attribute.FENCE])
    team = Team("吴军")
    enemy_team = Team("敌队")

    for general in [zhu_ran, ally_fence, ally_no_fence, dead_fence]:
        team.add_general(general)
    enemy_team.add_general(enemy_fence)

    zhu_ran_fence = break_fence(zhu_ran)
    ally_fence_state = break_fence(ally_fence)
    dead_fence_state = break_fence(dead_fence)
    enemy_fence_state = break_fence(enemy_fence)
    dead_fence.is_alive = False

    result = team.use_skill(zhu_ran, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["targets_affected"] == 2
    assert team.current_morale == 6
    assert zhu_ran_fence.is_active is True
    assert zhu_ran_fence.rebuild_turns_remaining == 0
    assert ally_fence_state.is_active is True
    assert ally_fence_state.rebuild_turns_remaining == 0
    assert not ally_no_fence.has_passive_skill("防栅")
    assert dead_fence_state.is_active is False
    assert dead_fence_state.rebuild_turns_remaining == 2
    assert enemy_fence_state.is_active is False
    assert enemy_fence_state.rebuild_turns_remaining == 2


if __name__ == "__main__":
    test_zhu_ran_data_and_skill()
    test_fence_rebuild_restores_all_alive_ally_fences_only()
    print("朱然防栅重建测试通过")
