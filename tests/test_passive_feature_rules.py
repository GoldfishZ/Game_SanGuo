"""
测试募兵、防栅、连计、复活、伏兵的新规则细节
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.passive_skills_config import get_passive_skills_for_attributes
from src.game_data.skills_config import get_skill_by_id
from src.battle.battle_system import BattleContext
from src.models.general import Attribute, Camp, General, Rarity
from src.models.team import Team


def make_general(name, force, intelligence, attributes=None, active_skill=None):
    general = General(
        general_id=1,
        name=name,
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
        attribute=attributes or [],
        active_skill=active_skill,
    )
    general.passive_skills = get_passive_skills_for_attributes(general.attribute)
    return general


def test_recruit_heals_each_turn_only_when_damaged():
    general = make_general("募兵", 5, 5, [Attribute.RECRUIT])

    general.trigger_turn_start_passives()
    assert general.current_hp == general.max_hp

    general.take_damage(3, damage_source="skill")
    general.trigger_turn_start_passives()
    assert general.current_hp == general.max_hp - 2


def test_fence_blocks_one_basic_attack_until_rebuilt_by_skill():
    defender = make_general("防栅", 4, 8, [Attribute.FENCE])
    attacker = make_general("攻击者", 6, 2)

    assert attacker.attack(defender) == 0
    fence = defender.get_passive_skill("防栅")
    assert fence.is_active is False

    defender.update_effects()
    assert fence.is_active is False
    defender.update_effects()
    assert fence.is_active is False


def test_fence_does_not_block_skill_damage():
    defender = make_general("防栅", 4, 8, [Attribute.FENCE])
    attacker = make_general("攻击者", 8, 4, active_skill=get_skill_by_id("fierce_attack"))

    team_a = Team("攻击队")
    team_b = Team("防守队")
    team_a.add_general(attacker)
    team_b.add_general(defender)
    result = attacker.use_active_skill([defender], BattleContext(team_a, team_b), team_a)

    assert result["success"] is True
    assert defender.current_hp < defender.max_hp
    assert defender.get_passive_skill("防栅").is_active is True


def test_chain_shares_effects_and_damage():
    first = make_general("连计1", 5, 8, [Attribute.CHAIN])
    second = make_general("连计2", 5, 8, [Attribute.CHAIN])
    attacker = make_general("攻击者", 8, 4)
    team = Team("连计队")
    team.add_general(first)
    team.add_general(second)

    first.add_buff("force_boost", 2, 1)
    assert second.buffs == first.buffs

    before_first = first.current_hp
    before_second = second.current_hp
    first.take_damage(6, attacker, "basic_attack")

    assert first.current_hp == before_first - 3
    assert second.current_hp == before_second - 3


def test_chain_effect_sync_does_not_duplicate_each_turn():
    first = make_general("连计1", 5, 8, [Attribute.CHAIN])
    second = make_general("连计2", 5, 8, [Attribute.CHAIN])
    team = Team("连计队")
    team.add_general(first)
    team.add_general(second)
    first.add_buff("force_boost", 2, 200)

    for _ in range(100):
        first.sync_chain_effects()
        second.sync_chain_effects()

    assert len(first.buffs) == 1
    assert len(second.buffs) == 1


def test_revive_once_at_half_hp():
    general = make_general("复活", 3, 3, [Attribute.REVIVE])

    general.take_damage(10, damage_source="skill")
    assert general.is_alive is True
    assert general.current_hp == 3

    general.take_damage(10, damage_source="skill")
    assert general.is_alive is False
    assert general.current_hp == 0


def test_ambush_is_not_basic_attack_target_and_can_counter():
    target = make_general("友军", 4, 4)
    ambush = make_general("伏兵", 4, 6, [Attribute.AMBUSH])
    attacker = make_general("攻击者", 8, 4)
    team = Team("伏兵队")
    team.add_general(target)
    team.add_general(ambush)
    team.position_general(target, 0, 0)
    team.position_general(ambush, 1, 0)

    assert ambush not in team.get_attackable_targets()

    expected_damage = attacker.calculate_damage_to(target)
    attacker_hp_before = attacker.current_hp
    damage = attacker.attack(target)
    assert damage == expected_damage
    assert target.current_hp == target.max_hp - expected_damage
    assert ambush.current_hp == ambush.max_hp
    assert attacker.current_hp == attacker_hp_before - max(1, expected_damage // 2)
    assert ambush.get_passive_skill("伏兵").is_hidden is False
    assert team.get_general_position(target) == (0, 0)
    assert team.get_general_position(ambush) == (1, 0)
    event = next(event for event in ambush.drain_combat_events() if event["type"] == "ambush_counter")
    assert event["attacker_id"] == attacker.general_id
    assert event["protected_id"] == target.general_id
    assert event["damage"] == max(1, expected_damage // 2)


if __name__ == "__main__":
    test_recruit_heals_each_turn_only_when_damaged()
    test_fence_blocks_one_basic_attack_until_rebuilt_by_skill()
    test_fence_does_not_block_skill_damage()
    test_chain_shares_effects_and_damage()
    test_revive_once_at_half_hp()
    test_ambush_is_not_basic_attack_target_and_can_counter()
    print("被动特性规则测试通过")


def test_ambush_active_skill_records_reveal_event():
    ambush = make_general(
        "伏兵", 7, 5, [Attribute.AMBUSH], active_skill=get_skill_by_id("fierce_attack"),
    )
    target = make_general("目标", 4, 4)
    own_team = Team("伏兵队")
    enemy_team = Team("目标队")
    own_team.add_general(ambush)
    enemy_team.add_general(target)
    own_team.position_general(ambush, 1, 0)
    enemy_team.position_general(target, 0, 0)

    result = ambush.use_active_skill(
        [target], BattleContext(own_team, enemy_team), own_team,
    )

    assert result["success"] is True
    assert ambush.get_passive_skill("伏兵").is_hidden is False
    reveal = next(event for event in ambush.drain_combat_events() if event["type"] == "ambush_reveal")
    assert reveal["reason"] == "skill"
    assert reveal["skill"] == ambush.active_skill.name