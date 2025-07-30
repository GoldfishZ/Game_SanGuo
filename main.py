"""
三国武将卡牌游戏主程序
"""

import pygame
import sys
from src.ui.game_ui import GameUI
from src.models.game import Game


def main():
    """主程序入口"""
    # 初始化pygame
    pygame.init()
    
    # 创建游戏实例
    game = Game()
    
    # 创建游戏界面
    ui = GameUI(game)
    
    # 游戏主循环
    try:
        ui.run()
    except KeyboardInterrupt:
        print("游戏被用户中断")
    except Exception as e:
        print(f"游戏运行出错: {e}")
    finally:
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    main()
