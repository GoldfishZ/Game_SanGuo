"""
测试勇猛/魅力的猜奇偶判定实现
"""

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.game_data.passive_skills_config import get_passive_skills_for_attributes
from src.models.general import Attribute, Camp, General, Rarity


def make_general(name, force, intelligence, attributes=None):
    general = General(
        general_id=1,
        name=name,
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=force,
        intelligence=intelligence,
        attribute=attributes or [],
    )
    general.passive_skills = get_passive_skills_for_attributes(general.attribute)
    return general


def test_bravery_success_below_half_hp():
    attacker = make_general("勇猛武将", 6, 6, [Attribute.BRAVERY])
    target = make_general("目标", 3, 1)
    attacker.take_damage(7)

    with patch("src.game_data.passive_skills_config.random.choice", return_value="odd"), \
         patch("src.game_data.passive_skills_config.random.randint", return_value=3):
        damage = attacker.attack(target)

    assert damage == 5
    assert target.current_hp == 0
    assert attacker.get_passive_skill("勇猛").last_judgment["success"] is True


def test_bravery_does_not_trigger_at_exactly_half_hp():
    attacker = make_general("勇猛武将", 6, 6, [Attribute.BRAVERY])
    target = make_general("目标", 3, 1)
    attacker.take_damage(6)

    with patch("src.game_data.passive_skills_config.random.choice", return_value="odd"), \
         patch("src.game_data.passive_skills_config.random.randint", return_value=3):
        damage = attacker.attack(target)

    assert damage == 3
    assert attacker.get_passive_skill("勇猛").last_judgment is None


def test_charisma_reflects_rounded_half_of_fatal_damage():
    victim = make_general("魅力武将", 3, 3, [Attribute.CHARISMA])
    attacker = make_general("攻击者", 5, 5)
    victim.take_damage(1)

    with patch("src.game_data.passive_skills_config.random.choice", return_value="even"), \
         patch("src.game_data.passive_skills_config.random.randint", return_value=2):
        actual_damage = victim.take_damage(5, attacker)

    assert actual_damage == 5
    assert victim.is_alive is False
    assert attacker.current_hp == 7
    assert victim.get_passive_skill("魅力").last_judgment["success"] is True


def test_charisma_does_not_reflect_when_judgment_fails():
    victim = make_general("魅力武将", 3, 3, [Attribute.CHARISMA])
    attacker = make_general("攻击者", 5, 5)
    victim.take_damage(1)

    with patch("src.game_data.passive_skills_config.random.choice", return_value="odd"), \
         patch("src.game_data.passive_skills_config.random.randint", return_value=2):
        actual_damage = victim.take_damage(5, attacker)

    assert actual_damage == 5
    assert victim.is_alive is False
    assert attacker.current_hp == attacker.max_hp
    assert victim.get_passive_skill("魅力").last_judgment["success"] is False


if __name__ == "__main__":
    test_bravery_success_below_half_hp()
    test_bravery_does_not_trigger_at_exactly_half_hp()
    test_charisma_reflects_rounded_half_of_fatal_damage()
    test_charisma_does_not_reflect_when_judgment_fails()
    print("勇猛/魅力猜奇偶判定测试通过")
