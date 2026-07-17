"""
测试田丰专属技能“缜密的攻势”。
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_ally(name, force=5, intelligence=5):
    return General(
        general_id=9900,
        name=name,
        camp=Camp.YUAN,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def build_front_block_team():
    tian_feng = get_general_by_name("田丰")
    front_a = make_ally("前方友军A")
    front_b = make_ally("前方友军B")
    front_c = make_ally("前方友军C")
    outside = make_ally("范围外友军")
    team = Team("袁军")
    enemy_team = Team("敌队")

    for general in [tian_feng, front_a, front_b, front_c, outside]:
        team.add_general(general)
    team.position_general(tian_feng, 2, 1)
    team.position_general(front_a, 0, 1)
    team.position_general(front_b, 1, 1)
    team.position_general(front_c, 1, 2)
    team.position_general(outside, 2, 3)
    return tian_feng, front_a, front_b, front_c, outside, team, enemy_team


def test_tian_feng_data_and_skill():
    tian_feng = get_general_by_name("田丰")

    assert tian_feng.camp == Camp.YUAN
    assert tian_feng.rarity == Rarity.RARE
    assert tian_feng.cost == 1.5
    assert tian_feng.force == 4
    assert tian_feng.intelligence == 9
    assert "伏兵" in [attr.value for attr in tian_feng.attribute]
    assert tian_feng.active_skill.name == "缜密的攻势"
    assert tian_feng.active_skill.morale_cost == 5


def test_meticulous_offense_buffs_front_2x2_and_rewards_morale_next_turn():
    tian_feng, front_a, front_b, front_c, outside, team, enemy_team = build_front_block_team()

    result = team.use_skill(tian_feng, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["targets_affected"] == 3
    assert team.current_morale == 7
    assert front_a.get_effective_force() == 8
    assert front_b.get_effective_force() == 8
    assert front_c.get_effective_force() == 8
    assert outside.get_effective_force() == 5
    assert len(team.pending_morale_rewards) == 1

    team.update_effects()

    assert team.current_morale == 10
    assert team.pending_morale_rewards == []


def test_meticulous_offense_morale_reward_fails_if_buffed_general_dies():
    tian_feng, front_a, front_b, front_c, outside, team, enemy_team = build_front_block_team()

    result = team.use_skill(tian_feng, [], BattleContext(team, enemy_team))
    assert result["success"] is True
    front_b.current_hp = 0
    front_b.is_alive = False

    team.update_effects()

    assert team.current_morale == 7
    assert team.pending_morale_rewards == []


def test_meticulous_offense_respects_selected_front_2x2():
    tian_feng, front_a, front_b, front_c, outside, team, enemy_team = build_front_block_team()

    result = team.use_skill(
        tian_feng,
        [{"row": 0, "col": 0}],
        BattleContext(team, enemy_team),
    )

    assert result["block"] == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert front_a.get_effective_force() == 8
    assert front_b.get_effective_force() == 8
    assert front_c.get_effective_force() == 5
    assert outside.get_effective_force() == 5


if __name__ == "__main__":
    test_tian_feng_data_and_skill()
    test_meticulous_offense_buffs_front_2x2_and_rewards_morale_next_turn()
    test_meticulous_offense_morale_reward_fails_if_buffed_general_dies()
    print("田丰缜密的攻势测试通过")
