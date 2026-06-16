"""
测试太史慈专属技能“天衣无缝”。
"""

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.generals_config import get_general_by_name
from src.battle.battle_system import BattleContext
from src.models.general import Camp, General, Rarity
from src.models.team import Team


def make_enemy(name, force=6, intelligence=10):
    return General(
        general_id=9500,
        name=name,
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
    )


def test_taishi_ci_data_and_skill():
    taishi_ci = get_general_by_name("太史慈")

    assert taishi_ci.camp == Camp.WU
    assert taishi_ci.rarity == Rarity.EPIC
    assert taishi_ci.cost == 2.0
    assert taishi_ci.force == 8
    assert taishi_ci.intelligence == 4
    assert taishi_ci.attribute == []
    assert taishi_ci.active_skill.name == "天衣无缝"
    assert taishi_ci.active_skill.morale_cost == 6


def test_flawless_speed_mode_grants_force_and_attack_speed_judgment():
    taishi_ci = get_general_by_name("太史慈")
    target = make_enemy("靶子")
    team = Team("吴军")
    enemy_team = Team("敌军")
    team.add_general(taishi_ci)
    enemy_team.add_general(target)

    result = team.use_skill(taishi_ci, [], BattleContext(team, enemy_team))

    assert result["success"] is True
    assert result["mode"] == "speed"
    assert team.current_morale == 6
    assert taishi_ci.get_effective_force() == 12
    assert taishi_ci.has_buff_type("attack_speed_judgment")

    with patch("src.models.general.random.choice", return_value="odd"), \
            patch("src.models.general.random.randint", return_value=3):
        damage = taishi_ci.attack(target)

    assert damage == 12
    assert target.current_hp == target.max_hp - 12
    assert taishi_ci.last_attack_speed_judgment["success"] is True


def test_flawless_saved_mode_can_activate_on_future_turn():
    taishi_ci = get_general_by_name("太史慈")
    team = Team("吴军")
    enemy_team = Team("敌军")
    team.add_general(taishi_ci)
    context = BattleContext(team, enemy_team)
    context.skill_options = {
        "mode": "saved",
        "delay_turns": 2,
        "force_boost": 4,
    }

    result = team.use_skill(taishi_ci, [], context)

    assert result["success"] is True
    assert result["mode"] == "saved"
    assert result["details"][0]["force_boost"] == 4
    assert result["details"][0]["intelligence_boost"] == 2
    assert taishi_ci.get_effective_force() == 8
    assert taishi_ci.get_effective_intelligence() == 4
    assert len(taishi_ci.pending_buffs) == 2

    taishi_ci.update_effects()
    assert taishi_ci.get_effective_force() == 8
    assert taishi_ci.get_effective_intelligence() == 4

    taishi_ci.update_effects()
    assert taishi_ci.get_effective_force() == 12
    assert taishi_ci.get_effective_intelligence() == 6

    taishi_ci.update_effects()
    assert taishi_ci.get_effective_force() == 8
    assert taishi_ci.get_effective_intelligence() == 4


if __name__ == "__main__":
    test_taishi_ci_data_and_skill()
    test_flawless_speed_mode_grants_force_and_attack_speed_judgment()
    test_flawless_saved_mode_can_activate_on_future_turn()
    print("太史慈天衣无缝测试通过")
