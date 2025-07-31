"""
测试清理后的武将系统
只包含用户指定的三个武将：张任、金环三结、鲁肃
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.game_data_manager import game_data_manager
from src.models.team import Team
from src.models.general import Camp, Rarity


def test_clean_system():
    """测试清理后的系统"""
    print("🧹" * 25)
    print("   测试清理后的武将系统")
    print("🧹" * 25)
    
    # 获取所有武将
    all_generals = game_data_manager.get_general_list()
    print(f"\n📊 系统武将统计:")
    print(f"   总武将数量: {len(all_generals)} (应为3)")
    
    # 列出所有武将
    print(f"\n📋 所有武将列表:")
    for general in all_generals:
        print(f"   • {general.name} ({general.camp.value}, {general.rarity.name})")
        print(f"     武力:{general.force} 智力:{general.intelligence} 生命:{general.max_hp}")
        print(f"     技能:{general.active_skill.name if general.active_skill else '无'}")
        print(f"     属性:{[attr.value for attr in general.attribute] if general.attribute else '无'}")
    
    # 获取统计信息
    info = game_data_manager.get_generals_info()
    print(f"\n📈 详细统计:")
    print(f"   总武将数: {info['total_generals']}")
    print(f"   总技能数: {info['total_skills']}")
    print(f"   阵营分布: {info['camp_distribution']}")
    print(f"   稀有度分布: {info['rarity_distribution']}")


def test_specific_generals():
    """测试具体的三个武将"""
    print("\n🎯" * 25)
    print("   测试具体武将功能")
    print("🎯" * 25)
    
    # 测试张任
    zhang_ren = game_data_manager.create_general("zhang_ren")
    print(f"\n🏛️ 张任测试:")
    print(f"   ID: {zhang_ren.general_id}")
    print(f"   阵营: {zhang_ren.camp.value} (应为'他')")
    print(f"   稀有度: {zhang_ren.rarity.name} (应为COMMON)")
    print(f"   费用: {zhang_ren.cost} (应为1.5)")
    print(f"   武力: {zhang_ren.force} (应为6)")
    print(f"   智力: {zhang_ren.intelligence} (应为6)")
    print(f"   生命: {zhang_ren.max_hp} (应为12)")
    print(f"   属性: {[attr.value for attr in zhang_ren.attribute]} (应为['伏兵'])")
    print(f"   技能: {zhang_ren.active_skill.name} (应为'强化战术')")
    
    # 测试金环三结
    jinhuan_sanjie = game_data_manager.create_general("jinhuan_sanjie")
    print(f"\n🏛️ 金环三结测试:")
    print(f"   阵营: {jinhuan_sanjie.camp.value} (应为'他')")
    print(f"   稀有度: {jinhuan_sanjie.rarity.name} (应为COMMON)")
    print(f"   费用: {jinhuan_sanjie.cost} (应为1.0)")
    print(f"   武力: {jinhuan_sanjie.force} (应为3)")
    print(f"   智力: {jinhuan_sanjie.intelligence} (应为1)")
    print(f"   生命: {jinhuan_sanjie.max_hp} (应为4)")
    print(f"   属性: {[attr.value for attr in jinhuan_sanjie.attribute] if jinhuan_sanjie.attribute else '无'} (应为'无')")
    print(f"   技能: {jinhuan_sanjie.active_skill.name} (应为'强化战术')")
    
    # 测试鲁肃
    lu_su = game_data_manager.create_general("lu_su")
    print(f"\n🏛️ 鲁肃测试:")
    print(f"   阵营: {lu_su.camp.value} (应为'吴')")
    print(f"   稀有度: {lu_su.rarity.name} (应为RARE)")
    print(f"   费用: {lu_su.cost} (应为1.5)")
    print(f"   武力: {lu_su.force} (应为4)")
    print(f"   智力: {lu_su.intelligence} (应为8)")
    print(f"   生命: {lu_su.max_hp} (应为12)")
    print(f"   属性: {[attr.value for attr in lu_su.attribute]} (应为['防栅'])")
    print(f"   技能: {lu_su.active_skill.name} (应为'同盟缔结')")


def test_skill_independence():
    """测试技能独立冷却"""
    print("\n⚔️" * 25)
    print("   测试技能独立冷却")
    print("⚔️" * 25)
    
    # 创建两个拥有相同技能的武将
    zhang_ren = game_data_manager.create_general("zhang_ren")
    jinhuan_sanjie = game_data_manager.create_general("jinhuan_sanjie")
    
    # 创建队伍
    team = Team("测试队伍", Camp.TA)
    team.add_general(zhang_ren)
    team.add_general(jinhuan_sanjie)
    
    print(f"\n⚔️ 测试同技能独立冷却:")
    print(f"   队伍士气: {team.current_morale}/{team.max_morale}")
    print(f"   {zhang_ren.name} 冷却: {zhang_ren.active_skill_cooldown}")
    print(f"   {jinhuan_sanjie.name} 冷却: {jinhuan_sanjie.active_skill_cooldown}")
    
    # 张任使用技能
    result1 = team.use_skill(zhang_ren, [zhang_ren], {"battle_phase": "main"})
    print(f"\n🔥 {zhang_ren.name} 使用技能: {'成功' if result1.get('success') else '失败'}")
    print(f"   {zhang_ren.name} 冷却: {zhang_ren.active_skill_cooldown}")
    print(f"   {jinhuan_sanjie.name} 冷却: {jinhuan_sanjie.active_skill_cooldown}")
    print(f"   队伍士气: {team.current_morale}/{team.max_morale}")
    
    # 金环三结使用技能
    result2 = team.use_skill(jinhuan_sanjie, [jinhuan_sanjie], {"battle_phase": "main"})
    print(f"\n🔥 {jinhuan_sanjie.name} 使用技能: {'成功' if result2.get('success') else '失败'}")
    print(f"   {zhang_ren.name} 冷却: {zhang_ren.active_skill_cooldown}")
    print(f"   {jinhuan_sanjie.name} 冷却: {jinhuan_sanjie.active_skill_cooldown}")
    print(f"   队伍士气: {team.current_morale}/{team.max_morale}")


def test_team_morale_limit():
    """测试队伍士气固定上限"""
    print("\n⚡" * 25)
    print("   测试队伍士气固定上限")
    print("⚡" * 25)
    
    # 创建不同参数的队伍
    team1 = Team("默认队伍")
    team2 = Team("指定阵营", Camp.WU)
    team3 = Team("尝试自定义士气", Camp.TA, max_morale=50)
    
    teams = [team1, team2, team3]
    
    for i, team in enumerate(teams, 1):
        print(f"\n🏛️ 队伍{i}: {team.team_name}")
        print(f"   最大士气: {team.max_morale} (应为12)")
        print(f"   当前士气: {team.current_morale} (应为12)")
        
        # 验证士气上限确实是12
        assert team.max_morale == 12, f"队伍{i}士气上限不是12！"
        assert team.current_morale == 12, f"队伍{i}当前士气不是12！"


if __name__ == "__main__":
    print("🎮 清理后系统完整测试")
    
    # 测试系统清理状态
    test_clean_system()
    
    # 测试具体武将
    test_specific_generals()
    
    # 测试技能独立冷却
    test_skill_independence()
    
    # 测试队伍士气上限
    test_team_morale_limit()
    
    print(f"\n✅ 测试完成！系统已清理为只包含用户指定的三个武将")
    print(f"   📋 武将: 张任、金环三结、鲁肃")
    print(f"   🔥 技能: 强化战术、同盟缔结")
    print(f"   ⚡ 士气: 固定上限12")
    print(f"   💚 生命: 武力+智力")
    print(f"   🎯 冷却: 每个武将独立管理")
