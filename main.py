"""
三国武将卡牌游戏主程序
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game_data.game_data_manager import game_data_manager
from game_data.generals_gallery import show_generals_gallery, interactive_gallery


def show_main_menu():
    """显示主菜单"""
    print("\n🎮 三国武将卡牌游戏 🎮")
    print("=" * 40)
    print("1. 开始游戏")
    print("2. 武将图鉴")
    print("3. 交互式武将图鉴")
    print("4. 游戏说明")
    print("5. 退出游戏")
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
    print("- 三大阵营: 蜀、魏、吴")
    print("- 团队士气管理")
    print("- 排兵布阵战略")
    
    print("\n⚔️ 战斗系统:")
    print("- 武力影响物理伤害")
    print("- 智力影响策略伤害")
    print("- 技能需要消耗团队士气")
    print("- 被动技能自动触发")
    
    print("\n📝 开发信息:")
    print("- 详细开发指南: DEVELOPMENT_GUIDE.md")
    print("- 当前版本: 开发版")
    print("- GUI界面: 开发中...")


def start_game():
    """开始游戏"""
    print("\n🚀 启动游戏...")
    
    try:
        # 导入游戏流程控制器
        from src.models.game_flow import GameFlowController
        
        # 创建游戏流程控制器
        game_flow = GameFlowController()
        
        print("✅ 游戏初始化成功!")
        
        # 显示快速游戏数据概览
        info = game_data_manager.get_generals_info()
        print(f"\n📊 游戏数据:")
        print(f"  可用武将: {info['total_generals']}名")
        print(f"  可用技能: {info['total_skills']}个")
        
        print("\n🎮 开始游戏流程...")
        
        # 启动游戏主流程
        game_flow.start_game()
        
        return True
        
    except Exception as e:
        print(f"❌ 游戏初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🎮 欢迎来到三国武将卡牌游戏! 🎮")
    
    while True:
        show_main_menu()
        
        try:
            choice = input("\n请选择操作 (1-5): ").strip()
            
            if choice == "1":
                # 开始游戏
                if start_game():
                    print("🎉 游戏体验完成!")
                else:
                    print("❌ 游戏启动失败!")
                    
            elif choice == "2":
                # 武将图鉴
                show_generals_gallery()
                
            elif choice == "3":
                # 交互式武将图鉴
                interactive_gallery()
                
            elif choice == "4":
                # 游戏说明
                show_game_info()
                
            elif choice == "5":
                # 退出游戏
                print("👋 感谢游玩三国武将卡牌游戏!")
                break
                
            else:
                print("❌ 无效的选择，请输入 1-5 之间的数字!")
                
        except KeyboardInterrupt:
            print("\n\n👋 游戏被用户中断，再见!")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")
            print("🔄 返回主菜单...")


if __name__ == "__main__":
    main()
