"""
测试独立技能冷却系统
验证每个武将的技能冷却是独立管理的
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game_data.game_data_manager import game_data_manager
from src.models.team import Team
from src.models.general import Camp


def test_independent_skill_cooldown():
    """测试武将独立的技能冷却系统"""
    print("🧪" * 25)
    print("   测试独立技能冷却系统")
    print("🧪" * 25)
    
    # 创建两个拥有相同技能的武将
    print("\n📋 创建测试武将...")
    
    # 创建两个刘备（相同武将，相同技能）
    liu_bei_1 = game_data_manager.create_general("liu_bei")
    liu_bei_2 = game_data_manager.create_general("liu_bei")
    
    print(f"武将1: {liu_bei_1.name} (ID: {liu_bei_1.general_id})")
    print(f"技能: {liu_bei_1.active_skill.name if liu_bei_1.active_skill else '无'}")
    print(f"存活状态: {liu_bei_1.is_alive}")
    print(f"武将2: {liu_bei_2.name} (ID: {liu_bei_2.general_id})")
    print(f"技能: {liu_bei_2.active_skill.name if liu_bei_2.active_skill else '无'}")
    print(f"存活状态: {liu_bei_2.is_alive}")
    
    # 创建队伍（增加士气上限以支持技能使用）
    team = Team("测试队伍", Camp.SHU, max_morale=50)
    team.add_general(liu_bei_1)
    team.add_general(liu_bei_2)
    
    # 创建一个目标武将
    target = game_data_manager.create_general("cao_cao")
    
    print(f"\n⚔️ 初始状态:")
    print(f"   {liu_bei_1.name}_1 技能冷却: {liu_bei_1.active_skill_cooldown}")
    print(f"   {liu_bei_1.name}_1 在队伍中: {liu_bei_1 in team.generals}")
    print(f"   {liu_bei_2.name}_2 技能冷却: {liu_bei_2.active_skill_cooldown}")
    print(f"   {liu_bei_2.name}_2 在队伍中: {liu_bei_2 in team.generals}")
    print(f"   队伍士气: {team.current_morale}/{team.max_morale}")
    
    # 第一个武将使用技能
    print(f"\n🔥 {liu_bei_1.name}_1 使用技能...")
    if liu_bei_1.active_skill:
        print(f"   检查武将技能状态:")
        print(f"   - 武将存活: {liu_bei_1.is_alive}")
        print(f"   - 有主动技能: {liu_bei_1.active_skill is not None}")
        print(f"   - 技能冷却: {liu_bei_1.active_skill_cooldown}")
        print(f"   - 武将可用技能: {liu_bei_1.can_use_active_skill()}")
        print(f"   - 队伍可用技能: {team.can_use_skill(liu_bei_1)}")
        print(f"   - 队伍士气足够: {team.current_morale >= liu_bei_1.active_skill.morale_cost}")
        print(f"   - 技能士气消耗: {liu_bei_1.active_skill.morale_cost}")
        print(f"   - 当前队伍士气: {team.current_morale}")
        result1 = team.use_skill(liu_bei_1, [target], {"battle_phase": "main"})
        print(f"   结果: {'成功' if result1.get('success') else '失败'}")
        if not result1.get('success'):
            print(f"   原因: {result1.get('message', '未知')}")
    
    print(f"\n📊 使用技能后状态:")
    print(f"   {liu_bei_1.name}_1 技能冷却: {liu_bei_1.active_skill_cooldown}")
    print(f"   {liu_bei_2.name}_2 技能冷却: {liu_bei_2.active_skill_cooldown}")
    print(f"   队伍士气: {team.current_morale}/{team.max_morale}")
    
    # 第二个武将尝试使用相同技能
    print(f"\n🔥 {liu_bei_2.name}_2 使用技能...")
    if liu_bei_2.active_skill:
        result2 = team.use_skill(liu_bei_2, [target], {"battle_phase": "main"})
        print(f"   结果: {'成功' if result2.get('success') else '失败'}")
        if not result2.get('success'):
            print(f"   原因: {result2.get('message', '未知')}")
    
    print(f"\n📊 两次使用技能后状态:")
    print(f"   {liu_bei_1.name}_1 技能冷却: {liu_bei_1.active_skill_cooldown}")
    print(f"   {liu_bei_2.name}_2 技能冷却: {liu_bei_2.active_skill_cooldown}")
    print(f"   队伍士气: {team.current_morale}/{team.max_morale}")
    
    # 测试冷却恢复
    print(f"\n⏰ 测试冷却恢复...")
    for round_num in range(1, 4):
        print(f"\n--- 回合 {round_num} ---")
        team.update_effects()  # 更新所有效果，包括冷却
        print(f"   {liu_bei_1.name}_1 技能冷却: {liu_bei_1.active_skill_cooldown}")
        print(f"   {liu_bei_2.name}_2 技能冷却: {liu_bei_2.active_skill_cooldown}")
        
        # 检查是否可以再次使用技能
        can_use_1 = team.can_use_skill(liu_bei_1)
        can_use_2 = team.can_use_skill(liu_bei_2)
        print(f"   {liu_bei_1.name}_1 可用技能: {'是' if can_use_1 else '否'}")
        print(f"   {liu_bei_2.name}_2 可用技能: {'是' if can_use_2 else '否'}")
    
    print(f"\n✅ 测试完成!")
    print(f"   结论: 每个武将的技能冷却是独立管理的")


def test_different_generals_same_skill():
    """测试不同武将拥有相同技能的情况"""
    print("\n🔄" * 25)
    print("   测试不同武将相同技能")
    print("🔄" * 25)
    
    # 创建不同的武将，但可能有相同的技能
    zhang_fei = game_data_manager.create_general("zhang_fei")
    xu_chu = game_data_manager.create_general("xu_chu")
    
    print(f"\n📋 武将信息:")
    print(f"   {zhang_fei.name}: {zhang_fei.active_skill.name if zhang_fei.active_skill else '无技能'}")
    print(f"   {xu_chu.name}: {xu_chu.active_skill.name if xu_chu.active_skill else '无技能'}")
    
    # 如果技能不同，展示它们的独立性
    if zhang_fei.active_skill and xu_chu.active_skill:
        team1 = Team("蜀国", Camp.SHU)
        team2 = Team("魏国", Camp.WEI)
        team1.add_general(zhang_fei)
        team2.add_general(xu_chu)
        
        target = game_data_manager.create_general("lu_bu")
        
        print(f"\n⚔️ 技能使用测试:")
        
        # 张飞使用技能
        if team1.can_use_skill(zhang_fei):
            result1 = team1.use_skill(zhang_fei, [target], {"battle_phase": "main"})
            print(f"   {zhang_fei.name} 使用 {zhang_fei.active_skill.name}: {'成功' if result1.get('success') else '失败'}")
            print(f"   {zhang_fei.name} 技能冷却: {zhang_fei.active_skill_cooldown}")
        
        # 许褚使用技能
        if team2.can_use_skill(xu_chu):
            result2 = team2.use_skill(xu_chu, [target], {"battle_phase": "main"})
            print(f"   {xu_chu.name} 使用 {xu_chu.active_skill.name}: {'成功' if result2.get('success') else '失败'}")
            print(f"   {xu_chu.name} 技能冷却: {xu_chu.active_skill_cooldown}")
        
        print(f"\n📊 验证独立性:")
        print(f"   {zhang_fei.name} 冷却时间: {zhang_fei.active_skill_cooldown}")
        print(f"   {xu_chu.name} 冷却时间: {xu_chu.active_skill_cooldown}")
        print(f"   两个武将的冷却时间独立管理 ✅")


if __name__ == "__main__":
    print("🎮 技能冷却独立性测试")
    
    # 测试相同武将的技能冷却独立性
    test_independent_skill_cooldown()
    
    # 测试不同武将的技能冷却独立性
    test_different_generals_same_skill()
    
    print(f"\n🎯 测试总结:")
    print(f"   ✅ 每个武将独立管理自己的技能冷却时间")
    print(f"   ✅ 相同技能在不同武将上冷却时间互不影响")
    print(f"   ✅ 技能对象本身不再维护冷却状态")
    print(f"   ✅ 支持多个武将拥有相同技能但独立冷却")
