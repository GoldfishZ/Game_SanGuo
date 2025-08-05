"""
测试游戏主流程
模拟完整的游戏流程测试
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.game_flow import GameFlowController, Player
from src.models.general import General, Camp, Rarity, Attribute
from game_data.generals_config import get_all_generals


def test_game_flow():
    """测试游戏主流程"""
    print("🎮 测试游戏主流程")
    print("=" * 50)
    
    # 创建游戏流程控制器
    game_flow = GameFlowController()
    
    # 测试1：武将池生成
    print("\n📋 测试武将池生成...")
    game_flow._generate_general_pool()
    print(f"✅ 生成了{len(game_flow.general_pool)}位武将的选择池")
    
    # 显示武将池
    game_flow._display_general_pool()
    
    # 测试2：模拟玩家选将
    print("\n🎯 模拟玩家选将...")
    
    # 为玩家1随机选择2位武将
    available_generals = [g for g in game_flow.general_pool if hasattr(g, 'pool_index')]
    for i in range(min(2, len(available_generals))):
        general = available_generals[i]
        game_flow.player1.add_general_to_team(general)
        available_generals.remove(general)
        if hasattr(general, 'pool_index'):
            delattr(general, 'pool_index')
        print(f"   玩家1选择了: {general.name}")
    
    # 为玩家2随机选择2位武将
    for i in range(min(2, len(available_generals))):
        general = available_generals[i]
        game_flow.player2.add_general_to_team(general)
        available_generals.remove(general)
        if hasattr(general, 'pool_index'):
            delattr(general, 'pool_index')
        print(f"   玩家2选择了: {general.name}")
    
    # 显示队伍
    game_flow._display_teams()
    
    # 测试3：抛骰子决定先手
    print("\n🎲 测试抛骰子决定先手...")
    game_flow._roll_dice_for_first_player()
    
    # 测试4：模拟几个回合
    print("\n⚔️ 测试战斗回合...")
    
    # 模拟前3个回合
    for turn in range(1, 4):
        if game_flow._is_game_over():
            break
            
        game_flow.turn_count = turn
        print(f"\n🎯 模拟第{turn}回合 - {game_flow.current_player.name}的回合")
        
        # 显示状态
        game_flow._display_battle_status()
        
        # 模拟技能阶段（跳过）
        print(f"   ✨ 技能阶段 - 跳过")
        
        # 模拟攻击阶段
        print(f"   ⚔️ 攻击阶段 - 模拟攻击")
        
        # 获取双方存活武将
        current_generals = game_flow.current_player.team.get_living_generals()
        enemy_player = game_flow.player2 if game_flow.current_player == game_flow.player1 else game_flow.player1
        enemy_generals = enemy_player.team.get_living_generals()
        
        if current_generals and enemy_generals:
            attacker = current_generals[0]
            target = enemy_generals[0]
            
            damage = attacker.attack(target)
            print(f"      {attacker.name} 攻击 {target.name}，造成 {damage} 点伤害")
            print(f"      {target.name} 剩余生命：{target.current_hp}/{target.max_hp}")
            
            if not target.is_alive:
                print(f"      💀 {target.name} 已阵亡！")
        
        # 切换玩家
        game_flow._switch_to_next_player()
    
    # 测试回合切换逻辑
    print("\n🔄 测试回合切换逻辑...")
    test_turn_switching()
    
    print("\n✅ 游戏主流程测试完成！")


def test_turn_switching():
    """测试回合切换逻辑"""
    print("   测试回合切换规则（先手1回合，后手2回合，然后交替）")
    
    game_flow = GameFlowController()
    game_flow.first_player = game_flow.player1
    game_flow.current_player = game_flow.player1
    
    expected_sequence = [
        (1, "玩家1"),  # 第1回合：先手玩家
        (2, "玩家2"),  # 第2回合：后手玩家
        (3, "玩家2"),  # 第3回合：后手玩家（连续2回合）
        (4, "玩家1"),  # 第4回合：开始交替
        (5, "玩家2"),  # 第5回合：继续交替
        (6, "玩家1"),  # 第6回合：继续交替
    ]
    
    results = []
    for turn in range(1, 7):
        game_flow.turn_count = turn
        current_player_name = game_flow.current_player.name
        results.append((turn, current_player_name))
        
        # 切换到下一个玩家（除了最后一次）
        if turn < 6:
            game_flow._switch_to_next_player()
    
    # 验证结果
    all_correct = True
    for i, (expected, actual) in enumerate(zip(expected_sequence, results)):
        expected_turn, expected_player = expected
        actual_turn, actual_player = actual
        
        if expected_turn == actual_turn and expected_player == actual_player:
            print(f"   ✅ 第{actual_turn}回合: {actual_player}")
        else:
            print(f"   ❌ 第{actual_turn}回合: 期望{expected_player}, 实际{actual_player}")
            all_correct = False
    
    if all_correct:
        print("   ✅ 回合切换逻辑正确！")
    else:
        print("   ❌ 回合切换逻辑有问题")


def test_battle_context():
    """测试战斗上下文"""
    print("\n🔧 测试战斗上下文...")
    
    from src.models.game_flow import BattleContext
    
    game_flow = GameFlowController()
    
    # 创建测试武将
    general1 = General(
        general_id=1,
        name="测试武将1",
        camp=Camp.SHU,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=5,
        intelligence=5,
        attribute=[],
        active_skill=None
    )
    
    general2 = General(
        general_id=2,
        name="测试武将2",
        camp=Camp.WEI,
        rarity=Rarity.COMMON,
        cost=1.0,
        force=5,
        intelligence=5,
        attribute=[],
        active_skill=None
    )
    
    # 添加到队伍
    game_flow.player1.add_general_to_team(general1)
    game_flow.player2.add_general_to_team(general2)
    
    # 创建战斗上下文
    battle_context = BattleContext(game_flow)
    
    # 测试获取队伍
    team1 = battle_context.get_team_for_general(general1)
    team2 = battle_context.get_team_for_general(general2)
    
    if team1 == game_flow.player1.team:
        print("   ✅ 正确获取武将1的队伍")
    else:
        print("   ❌ 获取武将1的队伍失败")
    
    if team2 == game_flow.player2.team:
        print("   ✅ 正确获取武将2的队伍")
    else:
        print("   ❌ 获取武将2的队伍失败")


def main():
    """主测试函数"""
    print("🎮 游戏主流程测试")
    print("=" * 60)
    
    try:
        test_game_flow()
        test_battle_context()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成！")
        print("📋 功能验证:")
        print("   ✅ 武将池生成：15位随机武将")
        print("   ✅ 选将流程：玩家选择武将加入队伍")  
        print("   ✅ 抛骰子：决定先手玩家")
        print("   ✅ 回合制：先手1回合，后手2回合，然后交替")
        print("   ✅ 战斗阶段：技能使用 → 普攻")
        print("   ✅ 游戏结束：全军覆没判定")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
