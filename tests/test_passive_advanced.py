"""
测试魅力被动技能的反弹伤害效果
"""

import sys
import os
from unittest.mock import patch
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.general import General, Camp, Rarity, Attribute
from game_data.skills_config import get_skill_by_id
from game_data.passive_skills_config import get_passive_skills_for_attributes, round_half_up


def test_charisma_passive():
    """测试魅力被动技能的反弹伤害"""
    print("💔 测试魅力被动技能反弹伤害")
    
    # 创建拥有魅力属性的武将
    charisma_general = General(
        general_id=2001,
        name="魅力武将",
        camp=Camp.SHU,
        rarity=Rarity.RARE,
        cost=2.0,
        force=3,
        intelligence=3,  # 最大生命 = 6
        attribute=[Attribute.CHARISMA],
        active_skill=None
    )
    charisma_general.passive_skills = get_passive_skills_for_attributes(charisma_general.attribute)
    
    # 创建攻击者
    attacker = General(
        general_id=2002,
        name="攻击者",
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=8,
        intelligence=2,  # 最大生命 = 10
        attribute=[],
        active_skill=None
    )
    
    print(f"   魅力武将: 生命{charisma_general.current_hp}/{charisma_general.max_hp}")
    print(f"   攻击者: 生命{attacker.current_hp}/{attacker.max_hp}")
    
    # 先让魅力武将受到一些伤害，然后再进行致死攻击
    charisma_general.take_damage(1)  # 减少到5/6
    print(f"   预先受伤后: 生命{charisma_general.current_hp}/{charisma_general.max_hp}")
    
    # 计算致死伤害
    damage = attacker.calculate_damage_to(charisma_general)
    print(f"   计算致死伤害: {damage}")
    
    # 攻击者击杀魅力武将
    with patch("game_data.passive_skills_config.random.choice", return_value="even"), \
         patch("game_data.passive_skills_config.random.randint", return_value=2):
        actual_damage = attacker.attack(charisma_general)
    
    print(f"   实际伤害: {actual_damage}")
    print(f"   魅力武将状态: 生命{charisma_general.current_hp}/{charisma_general.max_hp}, 存活:{charisma_general.is_alive}")
    print(f"   攻击者状态: 生命{attacker.current_hp}/{attacker.max_hp}, 存活:{attacker.is_alive}")
    
    # 检验魅力反弹效果
    expected_return_damage = round_half_up(actual_damage / 2)
    expected_attacker_hp = 10 - expected_return_damage
    
    if attacker.current_hp == expected_attacker_hp:
        print(f"   ✅ 魅力被动技能反弹成功！返还伤害: {expected_return_damage}")
    else:
        print(f"   ❌ 魅力被动技能反弹失败")
        print(f"   期望攻击者生命: {expected_attacker_hp}, 实际: {attacker.current_hp}")


def test_combined_passives():
    """测试多个被动技能组合效果"""
    print("\n🔥 测试被动技能组合效果")
    
    # 创建拥有多个属性的武将
    multi_general = General(
        general_id=3001,
        name="多属性武将",
        camp=Camp.TA,
        rarity=Rarity.EPIC,
        cost=3.0,
        force=4,
        intelligence=4,  # 最大生命 = 8
        attribute=[Attribute.BRAVERY, Attribute.FENCE, Attribute.RECRUIT],  # 勇猛+防栅+募兵
        active_skill=None
    )
    multi_general.passive_skills = get_passive_skills_for_attributes(multi_general.attribute)
    
    print(f"   多属性武将拥有被动技能: {[skill.name for skill in multi_general.passive_skills]}")
    print(f"   初始状态: 生命{multi_general.current_hp}/{multi_general.max_hp}")
    
    # 创建攻击者
    enemy = General(
        general_id=3002,
        name="敌人",
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=6,
        intelligence=2,
        attribute=[],
        active_skill=None
    )
    
    # 第一次攻击（应该被防栅抵挡）
    print("\n   第一次攻击（测试防栅）:")
    damage1 = enemy.attack(multi_general)
    print(f"   伤害: {damage1}, 武将生命: {multi_general.current_hp}/{multi_general.max_hp}")
    
    # 第二次攻击（防栅失效，受到伤害）
    print("\n   第二次攻击（防栅失效）:")
    damage2 = enemy.attack(multi_general)
    print(f"   伤害: {damage2}, 武将生命: {multi_general.current_hp}/{multi_general.max_hp}")
    
    # 触发募兵恢复（回合开始）
    print("\n   回合开始（测试募兵）:")
    multi_general.trigger_turn_start_passives()
    print(f"   募兵恢复后: 生命{multi_general.current_hp}/{multi_general.max_hp}")
    
    # 低血量反击（测试勇猛）
    print("\n   低血量反击（测试勇猛）:")
    print(f"   生命条件: {multi_general.current_hp} < {multi_general.max_hp / 2} ? {multi_general.current_hp < multi_general.max_hp / 2}")
    with patch("game_data.passive_skills_config.random.choice", return_value="odd"), \
         patch("game_data.passive_skills_config.random.randint", return_value=3):
        counter_damage = multi_general.attack(enemy)
    print(f"   反击伤害: {counter_damage}, 敌人生命: {enemy.current_hp}/{enemy.max_hp}")


def main():
    print("🎮 被动技能高级测试")
    print("=" * 50)
    
    test_charisma_passive()
    test_combined_passives()
    
    print("\n" + "=" * 50)
    print("✅ 被动技能高级测试完成！")


if __name__ == "__main__":
    main()
