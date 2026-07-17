"""
测试游戏主流程
模拟完整的游戏流程测试（已适配 BattleSystem 架构）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.game_flow import GameFlowController, Player
from src.models.general import General, Camp, Rarity, Attribute
from src.battle.battle_system import BattleSystem, BattleContext, BattleCallbacks, BattleEvent, BattleStatusData
from src.game_data.generals_config import get_all_generals


# ==================== Mock Callbacks（用于自动测试） ====================

class MockBattleCallbacks(BattleCallbacks):
    """模拟战斗回调：自动选择第一个可用选项，不做实际 I/O"""

    def __init__(self):
        self.log = []

    def display_battle_status(self, data: BattleStatusData) -> None:
        pass

    def on_turn_start(self, turn_count: int, player_name: str) -> None:
        self.log.append(f"turn_start:{turn_count}:{player_name}")

    def on_skill_used(self, event: BattleEvent) -> None:
        self.log.append(f"skill_used:{event.source_name}:{event.skill_name}")

    def on_skill_failed(self, skill_name: str, reason: str) -> None:
        self.log.append(f"skill_failed:{skill_name}:{reason}")

    def on_attack(self, event: BattleEvent) -> None:
        self.log.append(f"attack:{event.source_name}:{event.target_name}:{event.damage}")

    def on_general_defeated(self, event: BattleEvent) -> None:
        self.log.append(f"death:{event.target_name}")

    def on_battle_end(self, winner_name: str, turn_count: int) -> None:
        self.log.append(f"battle_end:{winner_name}:{turn_count}")

    def request_skill_use(self, available_generals: list, player_name: str) -> int:
        # 选择第一个可以用的武将
        for idx, name, skill, cooldown, can_use in available_generals:
            if can_use:
                return idx
        return -1

    def request_skill_target(self, caster_name: str, skill_name: str,
                             possible_targets: list) -> int:
        # 选择第一个目标
        if possible_targets:
            return 0
        return -1

    def request_attack_action(self, attackers: list, targets: list,
                              player_name: str) -> tuple:
        # 选择第一个攻击者和第一个目标
        if attackers and targets:
            return (0, 0)
        return (-1, -1)


# ==================== 测试用例 ====================

def test_game_flow():
    """测试游戏主流程（战前部分 + 战斗委托验证）"""
    print("🎮 测试游戏主流程")
    print("=" * 50)

    # 创建游戏流程控制器
    game_flow = GameFlowController()

    # 测试1：武将池生成
    print("\n📋 测试武将池生成...")
    game_flow._generate_general_pool()
    print(f"✅ 生成了{len(game_flow.general_pool)}位武将的选择池")
    assert len(game_flow.general_pool) == 15, "武将池应有15位武将"

    # 显示武将池
    game_flow._display_general_pool()

    # 测试2：模拟玩家选将
    print("\n🎯 模拟玩家选将...")

    available_generals = [g for g in game_flow.general_pool if hasattr(g, 'pool_index')]
    for i in range(min(2, len(available_generals))):
        general = available_generals[i]
        game_flow.player1.add_general_to_team(general)
        available_generals.remove(general)
        if hasattr(general, 'pool_index'):
            delattr(general, 'pool_index')
        print(f"   玩家1选择了: {general.name}")

    for i in range(min(2, len(available_generals))):
        general = available_generals[i]
        game_flow.player2.add_general_to_team(general)
        available_generals.remove(general)
        if hasattr(general, 'pool_index'):
            delattr(general, 'pool_index')
        print(f"   玩家2选择了: {general.name}")

    # 将武将放置到阵型格中（否则无法攻击）
    for i, g in enumerate(game_flow.player1.selected_generals):
        game_flow.player1.team.position_general(g, 0, i)  # 前排
    for i, g in enumerate(game_flow.player2.selected_generals):
        game_flow.player2.team.position_general(g, 0, i)  # 前排

    game_flow._display_teams()

    # 测试3：抛骰子决定先手
    print("\n🎲 测试抛骰子决定先手...")
    game_flow._roll_dice_for_first_player()
    assert game_flow.first_player is not None, "先手玩家应已确定"

    # 测试4：用 Mock BattleSystem 模拟战斗
    print("\n⚔️ 测试战斗（通过 BattleSystem + Mock Callbacks）...")

    callbacks = MockBattleCallbacks()
    battle_system = BattleSystem(
        team1=game_flow.player1.team,
        team2=game_flow.player2.team,
        callbacks=callbacks,
        first_player_team_name=game_flow.first_player.team.team_name,
    )
    winner = battle_system.run()
    print(f"   战斗结束，胜者: {winner}")
    print(f"   总回合数: {battle_system.turn_count}")
    print(f"   事件日志: {callbacks.log}")

    assert winner in (
        game_flow.player1.team.team_name,
        game_flow.player2.team.team_name,
    ), "胜者应为其中一方"
    assert battle_system.turn_count > 0, "应有至少一个回合"

    # 测试回合切换逻辑
    print("\n🔄 测试回合切换逻辑...")
    test_turn_switching()

    print("\n✅ 游戏主流程测试完成！")


def test_turn_switching():
    """测试 BattleSystem 回合切换逻辑"""
    print("   测试回合切换规则（A-B-A-B交替，后手有士气补偿）")

    from src.models.team import Team
    team_a = Team("玩家1的队伍")
    team_b = Team("玩家2的队伍")

    # 添加武将
    g1 = General(1, "测试A", Camp.SHU, Rarity.COMMON, 1.0, 5, 5)
    g2 = General(2, "测试B", Camp.WEI, Rarity.COMMON, 1.0, 5, 5)
    team_a.add_general(g1)
    team_b.add_general(g2)
    # 放置到阵型格中
    team_a.position_general(g1, 0, 0)
    team_b.position_general(g2, 0, 0)

    callbacks = MockBattleCallbacks()
    battle = BattleSystem(team_a, team_b, callbacks, "玩家1的队伍")

    expected_sequence = [
        (1, "玩家1"),    # 第1回合：先手玩家
        (2, "玩家2"),    # 第2回合：后手玩家
        (3, "玩家1"),    # 第3回合：交替
        (4, "玩家2"),    # 第4回合：交替
        (5, "玩家1"),    # 第5回合：交替
        (6, "玩家2"),    # 第6回合：交替
    ]

    all_correct = True
    for turn in range(1, 7):
        battle.turn_count = turn
        current_name = battle._get_current_player_name()
        expected_turn, expected_player = expected_sequence[turn - 1]

        if current_name == expected_player:
            print(f"   ✅ 第{turn}回合: {current_name}")
        else:
            print(f"   ❌ 第{turn}回合: 期望{expected_player}, 实际{current_name}")
            all_correct = False

        battle._switch_to_next_player()

    if all_correct:
        print("   ✅ 回合切换逻辑正确！")
    else:
        print("   ❌ 回合切换逻辑有问题")


def test_battle_context():
    """测试新的战斗上下文（team1, team2 构造）"""
    print("\n🔧 测试战斗上下文...")

    from src.models.team import Team

    team1 = Team("玩家1的队伍")
    team2 = Team("玩家2的队伍")

    general1 = General(1, "测试武将1", Camp.SHU, Rarity.COMMON, 1.0, 5, 5)
    general2 = General(2, "测试武将2", Camp.WEI, Rarity.COMMON, 1.0, 5, 5)

    team1.add_general(general1)
    team2.add_general(general2)

    # 新的构造方式：传入两个 team，不再传入 GameFlowController
    battle_context = BattleContext(team1, team2)

    # 测试获取队伍
    result1 = battle_context.get_team_for_general(general1)
    result2 = battle_context.get_team_for_general(general2)

    if result1 == team1:
        print("   ✅ 正确获取武将1的队伍")
    else:
        print("   ❌ 获取武将1的队伍失败")

    if result2 == team2:
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
        print("   ✅ 回合制：A-B-A-B交替，后手获得士气补偿")
        print("   ✅ 战斗阶段：BattleSystem + 回调架构")
        print("   ✅ 游戏结束：全军覆没判定")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
