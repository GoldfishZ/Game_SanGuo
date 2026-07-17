"""
测试曹仁专属技能“刹那的号令”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_ally(name, force=4, intelligence=5):
    return General(
        general_id=9800,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_cao_ren_data_and_skill():
    cao_ren = get_general_by_name("曹仁")

    assert cao_ren.camp == Camp.WEI
    assert cao_ren.rarity == Rarity.RARE
    assert cao_ren.cost == 1.5
    assert cao_ren.force == 5
    assert cao_ren.intelligence == 6
    assert cao_ren.attribute == []
    assert cao_ren.active_skill.name == "刹那的号令"
    assert cao_ren.active_skill.morale_cost == 3
    assert cao_ren.active_skill.cooldown == 2


def test_momentary_order_buffs_best_2x2_block_including_self():
    cao_ren = get_general_by_name("曹仁")
    ally_in_block = make_ally("范围友军A")
    ally_in_block_2 = make_ally("范围友军B")
    ally_outside = make_ally("范围外友军")
    team = Team("曹仁队")
    enemy_team = Team("敌队")

    for general in [cao_ren, ally_in_block, ally_in_block_2, ally_outside]:
        team.add_general(general)
    team.position_general(cao_ren, 1, 1)
    team.position_general(ally_in_block, 1, 2)
    team.position_general(ally_in_block_2, 2, 1)
    team.position_general(ally_outside, 0, 3)

    result = team.use_skill(cao_ren, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["targets_affected"] == 3
    assert team.current_morale == 9
    assert cao_ren.get_effective_force() == 7
    assert ally_in_block.get_effective_force() == 6
    assert ally_in_block_2.get_effective_force() == 6
    assert ally_outside.get_effective_force() == 4


def test_momentary_order_cannot_be_used_next_own_turn():
    cao_ren = get_general_by_name("曹仁")
    team = Team("曹仁队")
    enemy_team = Team("敌队")
    team.add_general(cao_ren)

    result = team.use_skill(cao_ren, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert cao_ren.active_skill_cooldown == 2

    team.update_effects()
    assert cao_ren.active_skill_cooldown == 1
    assert not cao_ren.can_use_active_skill()

    team.update_effects()
    assert cao_ren.active_skill_cooldown == 0
    assert cao_ren.can_use_active_skill()


def test_momentary_order_respects_selected_2x2_containing_caster():
    cao_ren = get_general_by_name("曹仁")
    chosen_ally = make_ally("选区友军")
    outside = make_ally("选区外友军")
    team = Team("曹仁队")
    enemy_team = Team("敌队")
    for general in [cao_ren, chosen_ally, outside]:
        team.add_general(general)
    team.position_general(cao_ren, 1, 1)
    team.position_general(chosen_ally, 0, 0)
    team.position_general(outside, 2, 2)

    result = team.use_skill(
        cao_ren,
        [{"row": 0, "col": 0}],
        BattleContext(team, enemy_team),
    )

    assert result["block"] == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert chosen_ally.get_effective_force() == 6
    assert outside.get_effective_force() == 4


if __name__ == "__main__":
    test_cao_ren_data_and_skill()
    test_momentary_order_buffs_best_2x2_block_including_self()
    test_momentary_order_cannot_be_used_next_own_turn()
    print("曹仁刹那的号令测试通过")
