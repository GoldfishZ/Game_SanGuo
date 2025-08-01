"""
测试被动技能系统
验证七个属性对应的被动技能效果
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.general import General, Camp, Rarity, Attribute
from src.models.team import Team
from game_data.skills_config import get_skill_by_id
from game_data.passive_skills_config import get_passive_skills_for_attributes


def test_bravery_passive():
    """测试勇猛被动技能"""
    print("🔥 测试勇猛被动技能")
    
    # 创建拥有勇猛属性的武将
    zhang_ren = General(
        general_id=1001,
        name="张任",
        camp=Camp.TA,
        rarity=Rarity.COMMON,
        cost=1.5,
        force=6,
        intelligence=6,  # 最大生命 = 12
        attribute=[Attribute.BRAVERY],
        active_skill=get_skill_by_id("strength_tactics")
    )
    zhang_ren.passive_skills = get_passive_skills_for_attributes(zhang_ren.attribute)
    
    # 创建目标武将
    target = General(
        general_id=1002,
        name="目标",
        camp=Camp.WU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=3,
        intelligence=1,
        attribute=[],
        active_skill=None
    )
    
    print(f"   张任初始状态: 生命{zhang_ren.current_hp}/{zhang_ren.max_hp}")
    print(f"   目标初始状态: 生命{target.current_hp}/{target.max_hp}")
    
    # 让张任受伤到一半以下
    zhang_ren.take_damage(7)  # 生命变为5/12（小于等于6）
    print(f"   张任受伤后: 生命{zhang_ren.current_hp}/{zhang_ren.max_hp}")
    
    # 张任攻击目标
    original_damage = zhang_ren.calculate_damage_to(target)
    actual_damage = zhang_ren.attack(target)
    
    print(f"   基础伤害: {original_damage}")
    print(f"   实际伤害: {actual_damage}")
    print(f"   目标剩余生命: {target.current_hp}/{target.max_hp}")
    
    # 验证勇猛效果
    expected_enhanced_damage = round(original_damage * 1.5)
    if actual_damage == expected_enhanced_damage:
        print("   ✅ 勇猛被动技能触发成功！")
    else:
        print("   ❌ 勇猛被动技能未触发")


def test_recruit_passive():
    """测试募兵被动技能"""
    print("\n💚 测试募兵被动技能")
    
    # 创建拥有募兵属性的武将
    recruit_general = General(
        general_id=1003,
        name="募兵武将",
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=5,
        intelligence=5,  # 最大生命 = 10
        attribute=[Attribute.RECRUIT],
        active_skill=None
    )
    recruit_general.passive_skills = get_passive_skills_for_attributes(recruit_general.attribute)
    
    print(f"   初始状态: 生命{recruit_general.current_hp}/{recruit_general.max_hp}")
    
    # 让武将受伤
    recruit_general.take_damage(3)
    print(f"   受伤后: 生命{recruit_general.current_hp}/{recruit_general.max_hp}")
    
    # 触发募兵被动技能（回合开始）
    recruit_general.trigger_turn_start_passives()
    print(f"   募兵触发后: 生命{recruit_general.current_hp}/{recruit_general.max_hp}")
    
    # 验证是否回复了1点生命
    if recruit_general.current_hp == 8:  # 7+1
        print("   ✅ 募兵被动技能生效！")
    else:
        print("   ❌ 募兵被动技能未生效")


def test_fence_passive():
    """测试防栅被动技能"""
    print("\n🛡️ 测试防栅被动技能")
    
    # 创建拥有防栅属性的武将
    lu_su = General(
        general_id=1004,
        name="鲁肃",
        camp=Camp.WU,
        rarity=Rarity.RARE,
        cost=1.5,
        force=4,
        intelligence=8,  # 最大生命 = 12
        attribute=[Attribute.FENCE],
        active_skill=get_skill_by_id("alliance_pact")
    )
    lu_su.passive_skills = get_passive_skills_for_attributes(lu_su.attribute)
    
    # 创建攻击者
    attacker = General(
        general_id=1005,
        name="攻击者",
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=6,
        intelligence=2,
        attribute=[],
        active_skill=None
    )
    
    print(f"   鲁肃初始状态: 生命{lu_su.current_hp}/{lu_su.max_hp}")
    print(f"   防栅状态: {lu_su.get_passive_skill('防栅').is_active}")
    
    # 第一次攻击（应该被防栅抵挡）
    damage1 = attacker.attack(lu_su)
    print(f"   第一次攻击伤害: {damage1}")
    print(f"   鲁肃生命: {lu_su.current_hp}/{lu_su.max_hp}")
    print(f"   防栅状态: {lu_su.get_passive_skill('防栅').is_active}")
    
    # 第二次攻击（防栅已失效）
    damage2 = attacker.attack(lu_su)
    print(f"   第二次攻击伤害: {damage2}")
    print(f"   鲁肃生命: {lu_su.current_hp}/{lu_su.max_hp}")
    
    if damage1 == 0 and damage2 > 0:
        print("   ✅ 防栅被动技能生效！")
    else:
        print("   ❌ 防栅被动技能未生效")


def test_revive_passive():
    """测试复活被动技能"""
    print("\n⚡ 测试复活被动技能")
    
    # 创建拥有复活属性的武将
    revive_general = General(
        general_id=1006,
        name="复活武将",
        camp=Camp.TA,
        rarity=Rarity.EPIC,
        cost=2.0,
        force=3,
        intelligence=3,  # 最大生命 = 6
        attribute=[Attribute.REVIVE],
        active_skill=None
    )
    revive_general.passive_skills = get_passive_skills_for_attributes(revive_general.attribute)
    
    print(f"   初始状态: 生命{revive_general.current_hp}/{revive_general.max_hp}, 存活:{revive_general.is_alive}")
    print(f"   复活状态: {revive_general.get_passive_skill('复活').has_revived}")
    
    # 造成致死伤害
    revive_general.take_damage(10)  # 足够致死的伤害
    print(f"   致死攻击后: 生命{revive_general.current_hp}/{revive_general.max_hp}, 存活:{revive_general.is_alive}")
    print(f"   复活状态: {revive_general.get_passive_skill('复活').has_revived}")
    
    if revive_general.is_alive and revive_general.current_hp == 3:  # 50%生命
        print("   ✅ 复活被动技能生效！")
    else:
        print("   ❌ 复活被动技能未生效")


def test_ambush_passive():
    """测试伏兵被动技能"""
    print("\n👤 测试伏兵被动技能")
    
    # 创建拥有伏兵属性的武将
    ambush_general = General(
        general_id=1007,
        name="伏兵武将",
        camp=Camp.TA,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=4,
        intelligence=2,
        attribute=[Attribute.AMBUSH],
        active_skill=None
    )
    ambush_general.passive_skills = get_passive_skills_for_attributes(ambush_general.attribute)
    
    # 创建普通武将
    normal_general = General(
        general_id=1008,
        name="普通武将",
        camp=Camp.TA,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=3,
        intelligence=3,
        attribute=[],
        active_skill=None
    )
    
    team_generals = [ambush_general, normal_general]
    
    print(f"   伏兵隐藏状态: {ambush_general.get_passive_skill('伏兵').is_hidden}")
    print(f"   伏兵可被选中: {ambush_general.can_be_targeted_by_enemy(team_generals)}")
    
    # 普通武将阵亡
    normal_general.is_alive = False
    print(f"   普通武将阵亡后...")
    print(f"   伏兵隐藏状态: {ambush_general.get_passive_skill('伏兵').is_hidden}")
    print(f"   伏兵可被选中: {ambush_general.can_be_targeted_by_enemy(team_generals)}")
    
    if ambush_general.can_be_targeted_by_enemy(team_generals):
        print("   ✅ 伏兵自动破隐成功！")
    else:
        print("   ❌ 伏兵自动破隐失败")


def main():
    """主测试函数"""
    print("🎮 被动技能系统测试")
    print("=" * 50)
    
    test_bravery_passive()
    test_recruit_passive()
    test_fence_passive()
    test_revive_passive()
    test_ambush_passive()
    
    print("\n" + "=" * 50)
    print("✅ 被动技能系统测试完成！")
    print("📋 已实现的被动技能:")
    print("   🔥 勇猛: 低血量时攻击伤害*1.5")
    print("   💚 募兵: 有伤时每回合回复1点生命")
    print("   🛡️ 防栅: 抵挡一次攻击后失效")
    print("   ⚡ 复活: 死亡后以50%生命复活一次")
    print("   👤 伏兵: 隐藏状态，自动破隐机制")
    print("🚧 待完善:")
    print("   💔 魅力: 死亡反弹伤害（需要判定系统）")
    print("   🔗 连环: 效果共享和伤害分担（需要团队系统）")


if __name__ == "__main__":
    main()
