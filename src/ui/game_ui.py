"""
游戏UI界面
使用Pygame实现基本的游戏界面
"""

import pygame
import sys
from typing import Optional, Tuple
from ..models.game import Game, GameState


class Colors:
    """颜色常量"""
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    BLUE = (0, 0, 255)
    GRAY = (128, 128, 128)
    LIGHT_GRAY = (200, 200, 200)
    DARK_GRAY = (64, 64, 64)
    YELLOW = (255, 255, 0)
    ORANGE = (255, 165, 0)


class GameUI:
    """游戏UI类"""
    
    def __init__(self, game: Game):
        """
        初始化游戏UI
        
        Args:
            game: 游戏实例
        """
        self.game = game
        self.screen_width = 1024
        self.screen_height = 768
        self.screen = None
        self.clock = None
        self.font = None
        self.title_font = None
        self.running = True
        
        # UI状态
        self.selected_general = None
        self.selected_position = None
        
    def initialize(self):
        """初始化Pygame"""
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("三国武将卡牌游戏")
        self.clock = pygame.time.Clock()
        
        # 初始化字体
        try:
            self.font = pygame.font.Font(None, 24)
            self.title_font = pygame.font.Font(None, 48)
        except:
            # 如果系统字体不可用，使用默认字体
            self.font = pygame.font.SysFont("arial", 24)
            self.title_font = pygame.font.SysFont("arial", 48)
    
    def run(self):
        """运行游戏主循环"""
        self.initialize()
        
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(60)  # 60 FPS
        
        pygame.quit()
    
    def handle_events(self):
        """处理事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.handle_keydown(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_mouse_click(event)
    
    def handle_keydown(self, event):
        """处理键盘事件"""
        if event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key == pygame.K_SPACE:
            if self.game.state == GameState.BATTLE:
                # 空格键执行战斗回合
                self.game.execute_battle_turn()
        elif event.key == pygame.K_RETURN:
            if self.game.state == GameState.MENU:
                # 回车键开始战斗
                self.game.start_new_battle()
        elif event.key == pygame.K_r:
            # R键重置游戏
            self.game.reset_game()
    
    def handle_mouse_click(self, event):
        """处理鼠标点击事件"""
        mouse_x, mouse_y = event.pos
        
        if self.game.state == GameState.FORMATION_SETUP:
            # 在阵型设置界面处理点击
            self.handle_formation_click(mouse_x, mouse_y)
    
    def handle_formation_click(self, x: int, y: int):
        """处理阵型设置点击"""
        # 这里应该实现阵型设置的点击逻辑
        # 简化版本，暂不实现
        pass
    
    def update(self):
        """更新游戏逻辑"""
        # 这里可以添加需要每帧更新的逻辑
        pass
    
    def render(self):
        """渲染画面"""
        self.screen.fill(Colors.WHITE)
        
        if self.game.state == GameState.MENU:
            self.render_menu()
        elif self.game.state == GameState.FORMATION_SETUP:
            self.render_formation_setup()
        elif self.game.state == GameState.BATTLE:
            self.render_battle()
        elif self.game.state == GameState.VICTORY:
            self.render_victory()
        elif self.game.state == GameState.DEFEAT:
            self.render_defeat()
        
        pygame.display.flip()
    
    def render_menu(self):
        """渲染主菜单"""
        # 标题
        title_text = self.title_font.render("三国武将卡牌游戏", True, Colors.BLACK)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # 菜单选项
        menu_items = [
            "按 ENTER 开始战斗",
            "按 ESC 退出游戏"
        ]
        
        for i, item in enumerate(menu_items):
            text = self.font.render(item, True, Colors.BLACK)
            text_rect = text.get_rect(center=(self.screen_width // 2, 300 + i * 40))
            self.screen.blit(text, text_rect)
    
    def render_formation_setup(self):
        """渲染阵型设置界面"""
        # 标题
        title_text = self.title_font.render("阵型设置", True, Colors.BLACK)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 50))
        self.screen.blit(title_text, title_rect)
        
        # 渲染阵型网格
        self.render_formation_grid(200, 150, self.game.player_formation)
        
        # 渲染可用武将
        self.render_available_generals(50, 500)
    
    def render_battle(self):
        """渲染战斗界面"""
        # 标题
        title_text = self.title_font.render("战斗中", True, Colors.RED)
        title_rect = title_text.get_rect(center=(self.screen_width // 2, 30))
        self.screen.blit(title_text, title_rect)
        
        if self.game.current_battle:
            battle_state = self.game.current_battle.get_battle_state()
            
            # 渲染回合信息
            turn_text = f"第 {battle_state['turn']} 回合"
            turn_surface = self.font.render(turn_text, True, Colors.BLACK)
            self.screen.blit(turn_surface, (50, 80))
            
            # 渲染玩家阵型
            self.render_formation_grid(50, 120, self.game.player_formation, "玩家阵型")
            
            # 渲染敌方阵型
            if self.game.current_battle.enemy_formation:
                self.render_formation_grid(550, 120, self.game.current_battle.enemy_formation, "敌方阵型")
            
            # 渲染战斗日志
            self.render_battle_log(50, 400)
            
            # 操作提示
            hint_text = "按 SPACE 执行回合 | 按 ESC 退出"
            hint_surface = self.font.render(hint_text, True, Colors.BLUE)
            self.screen.blit(hint_surface, (50, 700))
    
    def render_victory(self):
        """渲染胜利界面"""
        # 胜利标题
        victory_text = self.title_font.render("胜利！", True, Colors.GREEN)
        victory_rect = victory_text.get_rect(center=(self.screen_width // 2, 300))
        self.screen.blit(victory_text, victory_rect)
        
        # 重新开始提示
        restart_text = self.font.render("按 R 重新开始", True, Colors.BLACK)
        restart_rect = restart_text.get_rect(center=(self.screen_width // 2, 400))
        self.screen.blit(restart_text, restart_rect)
    
    def render_defeat(self):
        """渲染失败界面"""
        # 失败标题
        defeat_text = self.title_font.render("失败！", True, Colors.RED)
        defeat_rect = defeat_text.get_rect(center=(self.screen_width // 2, 300))
        self.screen.blit(defeat_text, defeat_rect)
        
        # 重新开始提示
        restart_text = self.font.render("按 R 重新开始", True, Colors.BLACK)
        restart_rect = restart_text.get_rect(center=(self.screen_width // 2, 400))
        self.screen.blit(restart_text, restart_rect)
    
    def render_formation_grid(self, x: int, y: int, formation, title: str = ""):
        """渲染阵型网格"""
        if title:
            title_surface = self.font.render(title, True, Colors.BLACK)
            self.screen.blit(title_surface, (x, y - 30))
        
        cell_size = 80
        gap = 5
        
        for row in range(3):
            for col in range(3):
                cell_x = x + col * (cell_size + gap)
                cell_y = y + row * (cell_size + gap)
                
                # 绘制格子
                rect = pygame.Rect(cell_x, cell_y, cell_size, cell_size)
                pygame.draw.rect(self.screen, Colors.LIGHT_GRAY, rect)
                pygame.draw.rect(self.screen, Colors.BLACK, rect, 2)
                
                # 绘制武将
                general = formation.positions.get((row, col))
                if general:
                    self.render_general_in_cell(cell_x, cell_y, cell_size, general)
    
    def render_general_in_cell(self, x: int, y: int, size: int, general):
        """在格子中渲染武将"""
        # 武将名字
        name_surface = self.font.render(general.name, True, Colors.BLACK)
        name_rect = name_surface.get_rect(center=(x + size // 2, y + 15))
        self.screen.blit(name_surface, name_rect)
        
        # 生命值
        hp_text = f"HP: {general.current_hp}/{general.max_hp}"
        hp_surface = self.font.render(hp_text, True, Colors.RED)
        hp_rect = hp_surface.get_rect(center=(x + size // 2, y + 35))
        self.screen.blit(hp_surface, hp_rect)
        
        # 生命值条
        bar_width = size - 10
        bar_height = 8
        bar_x = x + 5
        bar_y = y + 50
        
        # 背景条
        bg_rect = pygame.Rect(bar_x, bar_y, bar_width, bar_height)
        pygame.draw.rect(self.screen, Colors.GRAY, bg_rect)
        
        # 生命值条
        if general.max_hp > 0:
            hp_ratio = general.current_hp / general.max_hp
            hp_width = int(bar_width * hp_ratio)
            hp_rect = pygame.Rect(bar_x, bar_y, hp_width, bar_height)
            
            # 根据生命值比例选择颜色
            if hp_ratio > 0.6:
                hp_color = Colors.GREEN
            elif hp_ratio > 0.3:
                hp_color = Colors.YELLOW
            else:
                hp_color = Colors.RED
            
            pygame.draw.rect(self.screen, hp_color, hp_rect)
    
    def render_available_generals(self, x: int, y: int):
        """渲染可用武将列表"""
        title_surface = self.font.render("可用武将:", True, Colors.BLACK)
        self.screen.blit(title_surface, (x, y))
        
        for i, general in enumerate(self.game.player_generals):
            general_text = f"{general.name} (HP:{general.current_hp}/{general.max_hp})"
            general_surface = self.font.render(general_text, True, Colors.BLACK)
            self.screen.blit(general_surface, (x, y + 30 + i * 25))
    
    def render_battle_log(self, x: int, y: int):
        """渲染战斗日志"""
        title_surface = self.font.render("战斗日志:", True, Colors.BLACK)
        self.screen.blit(title_surface, (x, y))
        
        if self.game.current_battle and self.game.current_battle.battle_log:
            # 显示最近的几条日志
            recent_logs = self.game.current_battle.battle_log[-8:]
            for i, log in enumerate(recent_logs):
                log_surface = self.font.render(log, True, Colors.DARK_GRAY)
                self.screen.blit(log_surface, (x, y + 25 + i * 20))
