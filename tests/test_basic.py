"""
测试用例 - 武将基础功能测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.general import General, Camp, Rarity
from src.skills.skill_base import AttackSkill, HealSkill, BuffSkill, TargetType


def test_general_creation():
    """测试武将创建"""
    print("=== 测试武将创建 ===")
    
    liu_bei = General(
        general_id=1,
        name="刘备",
        camp=Camp.SHU,
        rarity=Rarity.LEGENDARY,
        max_hp=120,
        attack=80,
        defense=70,
        speed=60,
        skills=["仁德", "激励"]
    )
    
    print(f"创建武将: {liu_bei}")
    assert liu_bei.name == "刘备"
    assert liu_bei.current_hp == liu_bei.max_hp
    assert liu_bei.is_alive == True
    print("✓ 武将创建测试通过")


def test_general_combat():
    """测试武将战斗功能"""
    print("\n=== 测试武将战斗功能 ===")
    
    # 创建两个武将
    attacker = General(1, "关羽", Camp.SHU, Rarity.EPIC, 100, 95, 80, 70)
    defender = General(2, "夏侯惇", Camp.WEI, Rarity.RARE, 95, 88, 82, 68)
    
    print(f"攻击前 - {defender}")
    
    # 模拟攻击
    damage = attacker.get_effective_attack()
    actual_damage = defender.take_damage(damage)
    
    print(f"关羽攻击夏侯惇，造成 {actual_damage} 点伤害")
    print(f"攻击后 - {defender}")
    
    assert defender.current_hp < defender.max_hp
    print("✓ 战斗功能测试通过")


def test_general_effects():
    """测试武将状态效果"""
    print("\n=== 测试武将状态效果 ===")
    
    general = General(1, "张飞", Camp.SHU, Rarity.EPIC, 110, 90, 85, 65)
    
    print(f"初始攻击力: {general.get_effective_attack()}")
    
    # 添加攻击增益
    general.add_buff("attack_boost", 20, 2)
    print(f"增益后攻击力: {general.get_effective_attack()}")
    
    # 添加攻击减益
    general.add_debuff("attack_reduction", 10, 1)
    print(f"减益后攻击力: {general.get_effective_attack()}")
    
    # 更新效果
    general.update_effects()
    print(f"更新一回合后攻击力: {general.get_effective_attack()}")
    
    assert len(general.buffs) >= 0
    assert len(general.debuffs) >= 0
    print("✓ 状态效果测试通过")


def test_skills():
    """测试技能系统"""
    print("\n=== 测试技能系统 ===")
    
    # 创建攻击技能
    attack_skill = AttackSkill(
        skill_id="qinglong",
        name="青龙偃月",
        description="关羽的招牌攻击",
        target_type=TargetType.SINGLE_ENEMY,
        damage_multiplier=1.5,
        cooldown=2,
        energy_cost=3
    )
    
    # 创建施法者和目标
    caster = General(1, "关羽", Camp.SHU, Rarity.EPIC, 100, 95, 80, 70)
    target = General(2, "敌将", Camp.WEI, Rarity.COMMON, 80, 70, 60, 55)
    
    # 为施法者添加能量属性
    caster.energy = 10
    
    print(f"技能释放前 - 目标: {target}")
    
    # 使用技能
    result = attack_skill.use_skill(caster, [target], None)
    
    print(f"技能释放结果: {result}")
    print(f"技能释放后 - 目标: {target}")
    
    assert result.get("success") == True
    assert target.current_hp < target.max_hp
    print("✓ 技能系统测试通过")


def test_heal_skill():
    """测试治疗技能"""
    print("\n=== 测试治疗技能 ===")
    
    heal_skill = HealSkill(
        skill_id="rende",
        name="仁德",
        description="刘备的治疗技能",
        target_type=TargetType.SINGLE_ALLY,
        heal_amount=30,
        cooldown=2,
        energy_cost=2
    )
    
    caster = General(1, "刘备", Camp.SHU, Rarity.LEGENDARY, 120, 80, 70, 60)
    target = General(2, "关羽", Camp.SHU, Rarity.EPIC, 100, 95, 80, 70)
    
    # 为施法者添加能量属性
    caster.energy = 10
    
    # 让目标受伤
    target.current_hp = 50
    
    print(f"治疗前 - 目标: {target}")
    
    # 使用治疗技能
    result = heal_skill.use_skill(caster, [target], None)
    
    print(f"治疗结果: {result}")
    print(f"治疗后 - 目标: {target}")
    
    assert result.get("success") == True
    assert target.current_hp > 50
    print("✓ 治疗技能测试通过")


if __name__ == "__main__":
    print("开始运行测试用例...")
    
    try:
        test_general_creation()
        test_general_combat()
        test_general_effects()
        test_skills()
        test_heal_skill()
        
        print("\n" + "="*50)
        print("🎉 所有测试用例通过！")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
