"""
测试曹操专属技能：全军攻城
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity, Attribute
from src.models.team import Team
from src.game_data.passive_skills_config import get_passive_skills_for_attributes


def make_general(name, force, intelligence, attributes=None):
    general = General(
        general_id=9000,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
        attribute=attributes or [],
    )
    general.passive_skills = get_passive_skills_for_attributes(general.attribute)
    return general


def test_cao_cao_data_and_skill():
    cao_cao = get_general_by_name("曹操")

    assert cao_cao.force == 7
    assert cao_cao.intelligence == 9
    assert cao_cao.cost == 2.0
    assert "魅力" in [attr.value for attr in cao_cao.attribute]
    assert cao_cao.active_skill.name == "全军攻城"
    assert cao_cao.active_skill.morale_cost == 6


def test_siege_buffs_same_row_and_consumes_morale():
    cao_cao = get_general_by_name("曹操")
    ally_same_row = make_general("同排友军", 5, 5)
    ally_other_row = make_general("异排友军", 5, 5)
    team = Team("曹操队")
    enemy_team = Team("敌队")

    for general in [cao_cao, ally_same_row, ally_other_row]:
        team.add_general(general)
    team.position_general(cao_cao, 0, 0)
    team.position_general(ally_same_row, 0, 1)
    team.position_general(ally_other_row, 1, 0)

    result = team.use_skill(cao_cao, [cao_cao], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert team.current_morale == 6
    assert cao_cao.get_effective_force() == 10
    assert ally_same_row.get_effective_force() == 8
    assert ally_other_row.get_effective_force() == 5
    assert ally_same_row.has_buff_type("ignore_fence")
    assert ally_same_row.has_buff_type("front_only_attack")


def test_siege_ignores_fence_and_limits_front_target():
    cao_cao = get_general_by_name("曹操")
    attacker = make_general("攻城友军", 7, 5)
    enemy_front = make_general("防栅目标", 4, 8, [Attribute.FENCE])
    enemy_other_col = make_general("旁列目标", 1, 1)
    team = Team("曹操队")
    enemy_team = Team("敌队")

    team.add_general(cao_cao)
    team.add_general(attacker)
    enemy_team.add_general(enemy_front)
    enemy_team.add_general(enemy_other_col)
    team.position_general(cao_cao, 0, 0)
    team.position_general(attacker, 0, 1)
    enemy_team.position_general(enemy_front, 0, 1)
    enemy_team.position_general(enemy_other_col, 0, 2)

    team.use_skill(cao_cao, [cao_cao], BattleContext(team, enemy_team))

    invalid_damage = attacker.attack(enemy_other_col)
    assert invalid_damage == 0
    assert enemy_other_col.current_hp == enemy_other_col.max_hp

    damage = attacker.attack(enemy_front)
    assert damage > 0
    assert enemy_front.current_hp < enemy_front.max_hp
    assert enemy_front.get_passive_skill("防栅").is_active is True


if __name__ == "__main__":
    test_cao_cao_data_and_skill()
    test_siege_buffs_same_row_and_consumes_morale()
    test_siege_ignores_fence_and_limits_front_target()
    print("曹操全军攻城测试通过")
