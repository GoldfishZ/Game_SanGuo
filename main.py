"""
三国武将卡牌游戏主程序
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 应用响应式布局补丁（在导入其他模块之前）
def _apply_responsive_ui_patch():
    """应用响应式布局补丁，使UI适应窗口大小变化"""
    import os
    pygame_ui_path = os.path.join(os.path.dirname(__file__), 'src', 'ui', 'pygame_ui.py')
    try:
        with open(pygame_ui_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查补丁是否已应用
        if 'current_w, current_h = self.screen.get_size()' in content and 'while pygame.time.get_ticks() - start_time < 1200:' in content:
            # 检查 show_dice_roll 函数是否需要补丁
            if 'while pygame.time.get_ticks() - start_time < 1200:\n            current_w, current_h' not in content:
                # 应用补丁
                content = content.replace(
                    '        while pygame.time.get_ticks() - start_time < 1200:\n            self.screen.fill(Colors.BG)',
                    '        while pygame.time.get_ticks() - start_time < 1200:\n            current_w, current_h = self.screen.get_size()\n            self.screen.fill(Colors.BG)'
                )
                content = content.replace(
                    '        self.screen.fill(Colors.BG)\n        self.screen.blit(ft.render("掷骰子决定先手...", True, Colors.YELLOW), ft.render("X", True, Colors.BG).get_rect(center=(SCREEN_WIDTH//2, 200)))\n        self.screen.blit(ft.render("掷骰子决定先手...", True, Colors.YELLOW), (SCREEN_WIDTH//2 - 150, 200))',
                    '        current_w, current_h = self.screen.get_size()\n        self.screen.fill(Colors.BG)\n        self.screen.blit(ft.render("掷骰子决定先手...", True, Colors.YELLOW), (current_w//2 - 150, 200))'
                )
                # 替换 show_dice_roll 中的 SCREEN_WIDTH
                lines = content.split('\n')
                new_lines = []
                in_dice_roll = False
                for line in lines:
                    if 'def show_dice_roll' in line:
                        in_dice_roll = True
                    elif in_dice_roll and line.startswith('    def '):
                        in_dice_roll = False
                    if in_dice_roll and 'SCREEN_WIDTH' in line:
                        line = line.replace('SCREEN_WIDTH', 'current_w')
                    new_lines.append(line)
                content = '\n'.join(new_lines)
                
                with open(pygame_ui_path, 'w', encoding='utf-8') as f:
                    f.write(content)
    except Exception:
        pass  # 补丁应用失败不应该中断游戏

_apply_responsive_ui_patch()

from game_data.game_data_manager import game_data_manager
from game_data.generals_gallery import show_generals_gallery, interactive_gallery


def show_main_menu():
    """显示主菜单"""
    print("\n🎮 三国武将卡牌游戏 🎮")
    print("=" * 40)
    print("1. 开始游戏 (命令行)")
    print("2. 开始游戏 (图形界面)")
    print("3. 武将图鉴")
    print("4. 交互式武将图鉴")
    print("5. 游戏说明")
    print("6. 退出游戏")
    print("=" * 40)


def show_game_info():
    """显示游戏说明"""
    print("\n📖 游戏说明")
    print("=" * 30)
    print("🎯 游戏特性:")
    print("- 三国武将卡牌对战")
    print("- 武力/智力属性系统")
    print("- 七大武将属性: 勇猛、魅力、募兵、防栅、连环、复活、伏兵")
    print("- 主动/被动技能系统")
    print("- 六大阵营: 蜀、魏、吴、凉、袁、他")
    print("- 团队士气管理")
    print("- 排兵布阵战略")

    print("\n⚔️ 战斗系统:")
    print("- 武力影响物理伤害")
    print("- 智力影响策略伤害")
    print("- 技能需要消耗团队士气")
    print("- 被动技能自动触发")

    print("\n📝 开发信息:")
    print("- 当前版本: 开发版")
    print("- GUI模式: 选将和布阵使用命令行，战斗使用图形界面")


def start_game():
    """开始游戏（命令行模式）"""
    print("\n🚀 启动游戏（命令行模式）...")

    try:
        from src.models.game_flow import GameFlowController

        game_flow = GameFlowController()

        print("✅ 游戏初始化成功!")

        info = game_data_manager.get_generals_info()
        print(f"\n📊 游戏数据:")
        print(f"  可用武将: {info['total_generals']}名")
        print(f"  可用技能: {info['total_skills']}个")

        print("\n🎮 开始游戏流程...")
        game_flow.start_game()

        return True

    except Exception as e:
        print(f"❌ 游戏初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def start_game_gui():
    """开始游戏（完整图形界面模式）"""
    import pygame
    try:
        from src.models.game_flow import GameFlowController
        from src.ui.pygame_ui import PygameUI, PygameBattleCallbacks

        pygame_ui = PygameUI()

        # 主菜单循环
        while True:
            choice = pygame_ui.show_main_menu()
            if choice == "quit":
                pygame.quit()
                return True
            elif choice == "rules":
                pygame_ui.show_rules()
            elif choice == "gallery":
                pygame_ui.show_general_gallery()
            elif choice == "start":
                break  # 进入游戏流程

        game_flow = GameFlowController()
        game_flow._generate_general_pool()

        # ===== 玩家1选将 =====
        p1_generals = pygame_ui.show_general_selection(
            game_flow.general_pool, "玩家1"
        )
        if p1_generals is None:  # 窗口被关闭
            pygame.quit()
            return True
        for g in p1_generals:
            game_flow.player1.add_general_to_team(g)
            if hasattr(g, 'pool_index'):
                delattr(g, 'pool_index')

        # ===== 玩家2选将 =====
        remaining_pool = [g for g in game_flow.general_pool
                          if g not in game_flow.player1.selected_generals]
        p2_generals = pygame_ui.show_general_selection(
            remaining_pool, "玩家2"
        )
        if p2_generals is None:
            pygame.quit()
            return True
        for g in p2_generals:
            game_flow.player2.add_general_to_team(g)
            if hasattr(g, 'pool_index'):
                delattr(g, 'pool_index')

        # ===== 布阵 =====
        if not pygame_ui.show_formation_setup(
            game_flow.player1.team, game_flow.player1.selected_generals, "玩家1"
        ):
            pygame.quit()
            return True
        if not pygame_ui.show_formation_setup(
            game_flow.player2.team, game_flow.player2.selected_generals, "玩家2"
        ):
            pygame.quit()
            return True

        # ===== 掷骰子 =====
        import random
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        if dice1 > dice2:
            game_flow.first_player = game_flow.player1
            game_flow.second_player = game_flow.player2
        else:
            game_flow.first_player = game_flow.player2
            game_flow.second_player = game_flow.player1
        game_flow.current_player = game_flow.first_player
        compensation = 2
        game_flow.second_player.team.max_morale += compensation
        game_flow.second_player.team.current_morale += compensation

        if not pygame_ui.show_dice_roll(
            game_flow.player1.name, game_flow.player2.name,
            dice1, dice2, game_flow.first_player.name
        ):
            pygame.quit()
            return True

        # ===== 战斗 =====
        gui_callbacks = PygameBattleCallbacks(
            pygame_ui,
            game_flow.player1.team.team_name,
            game_flow.player2.team.team_name,
        )
        game_flow._battle_callbacks = gui_callbacks

        # 检查 Pygame 是否还活着
        if not pygame.get_init():
            return True

        game_flow._enter_battle_phase()

        pygame.quit()
        return True

    except SystemExit:
        try: pygame.quit()
        except: pass
        return True
    except Exception as e:
        print(f"❌ GUI模式启动失败: {e}")
        import traceback
        traceback.print_exc()
        try:
            pygame.quit()
        except:
            pass
        return False


def main():
    """主函数"""
    import game_data.generals_config  # 确保初始化

    # --gui 参数：直接启动图形界面，跳过菜单
    if "--gui" in sys.argv or "-g" in sys.argv:
        print("🎮 直接启动图形界面...")
        start_game_gui()
        print("👋 再见!")
        return

    print("🎮 欢迎来到三国武将卡牌游戏! 🎮")

    while True:
        show_main_menu()

        try:
            choice = input("\n请选择操作 (1-6): ").strip()

            if choice == "1":
                if start_game():
                    print("🎉 游戏体验完成!")
                else:
                    print("❌ 游戏启动失败!")

            elif choice == "2":
                import pygame
                start_game_gui()
                # GUI模式退出后直接返回菜单

            elif choice == "3":
                show_generals_gallery()

            elif choice == "4":
                interactive_gallery()

            elif choice == "5":
                show_game_info()

            elif choice == "6":
                print("👋 感谢游玩三国武将卡牌游戏!")
                break

            else:
                print("❌ 无效的选择，请输入 1-6 之间的数字!")

        except KeyboardInterrupt:
            print("\n\n👋 游戏被用户中断，再见!")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()
            print("🔄 返回主菜单...")


if __name__ == "__main__":
    main()
