"""
Pygame GUI 界面
主菜单 → 选将 → 布阵 → 掷骰 → 战斗 → 结算，完整图形流程
"""

import pygame
import sys
import time
import random as rnd
from typing import Optional, Tuple, List

from src.battle.battle_system import BattleCallbacks, BattleEvent, BattleStatusData
from src.models.team import Team
from src.models.general import General


# ==================== 常量 ====================

class Colors:
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    RED = (255, 50, 50)
    GREEN = (50, 200, 50)
    BLUE = (50, 100, 255)
    GRAY = (150, 150, 150)
    LIGHT_GRAY = (210, 210, 210)
    DARK_GRAY = (60, 60, 60)
    YELLOW = (255, 220, 50)
    ORANGE = (255, 150, 50)
    HP_BAR_BG = (50, 50, 50)
    CARD_BG = (240, 240, 245)
    CARD_SELECTED = (180, 210, 255)
    CARD_HOVER = (220, 230, 250)
    BG = (30, 30, 40)
    PANEL_BG = (45, 45, 55)
    BUTTON_BG = (70, 130, 200)
    BUTTON_HOVER = (90, 150, 220)
    BUTTON_DISABLED = (100, 100, 100)
    MORALE_BAR_BG = (40, 40, 40)
    MORALE_BAR_FILL = (100, 180, 255)
    TEXT_PRIMARY = (230, 230, 230)
    TEXT_SECONDARY = (180, 180, 180)

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
CELL_WIDTH = 90
CELL_HEIGHT = 120
CELL_GAP = 6
GRID_LEFT_X = 40
GRID_RIGHT_X = 700
GRID_Y = 100
IMAGE_AREA_HEIGHT = 75
LOG_Y = 540
LOG_MAX_LINES = 8
BUTTON_Y = 500
FPS = 30
FORMATION_COLS = 4
FORMATION_ROWS = 3

# ==================== 中文字体 ====================

_CJK_FONT_NAME = None


def _init_cjk_font():
    global _CJK_FONT_NAME
    if _CJK_FONT_NAME is not None:
        return _CJK_FONT_NAME
    candidates = ["simhei", "microsoftyahei", "simsun", "notosanscjk", "wenquanyimicrohei"]
    for name in candidates:
        try:
            pygame.font.SysFont(name, 24)
            _CJK_FONT_NAME = name
            return name
        except:
            continue
    import os as _os
    font_dirs = ["C:/Windows/Fonts", "/usr/share/fonts", "/System/Library/Fonts"]
    font_files = ["simhei.ttf", "msyh.ttc", "msyh.ttf", "simsun.ttc"]
    for fdir in font_dirs:
        if not _os.path.exists(fdir):
            continue
        for fname in font_files:
            fpath = _os.path.join(fdir, fname)
            if _os.path.exists(fpath):
                try:
                    pygame.font.Font(fpath, 24)
                    _CJK_FONT_NAME = fpath
                    return fpath
                except:
                    continue
    _CJK_FONT_NAME = ""
    return None


def get_font(size: int) -> pygame.font.Font:
    name = _init_cjk_font()
    if name and _CJK_FONT_NAME:
        if "/" in str(name) or "\\" in str(name):
            return pygame.font.Font(name, size)
        return pygame.font.SysFont(name, size)
    return pygame.font.Font(None, size)


# ==================== 渲染工具函数 ====================

def render_health_bar(surface, x, y, width, height, current_hp, max_hp):
    pygame.draw.rect(surface, Colors.HP_BAR_BG, (x, y, width, height))
    if max_hp > 0:
        ratio = max(0, min(1, current_hp / max_hp))
        fill_width = int(width * ratio)
        if ratio > 0.6:
            color = Colors.GREEN
        elif ratio > 0.3:
            color = Colors.YELLOW
        else:
            color = Colors.RED
        pygame.draw.rect(surface, color, (x, y, fill_width, height))
    pygame.draw.rect(surface, Colors.GRAY, (x, y, width, height), 1)


def render_morale_bar(surface, x, y, width, height, current, max_val):
    pygame.draw.rect(surface, Colors.MORALE_BAR_BG, (x, y, width, height))
    if max_val > 0:
        ratio = current / max_val
        pygame.draw.rect(surface, Colors.MORALE_BAR_FILL, (x, y, int(width * ratio), height))
    pygame.draw.rect(surface, Colors.GRAY, (x, y, width, height), 1)


def render_general_cell(surface, x, y, w, h, name, hp, max_hp,
                         force=0, intelligence=0, skill_name="",
                         cooldown=0, is_alive=True,
                         selected=False, hover=False, selectable=True,
                         image=None):
    if selected:
        bg_color = Colors.CARD_SELECTED
        border_color = Colors.YELLOW
        border_w = 4
    elif hover and selectable:
        bg_color = Colors.CARD_HOVER
        border_color = Colors.YELLOW
        border_w = 3
    else:
        bg_color = Colors.PANEL_BG
        border_color = Colors.GRAY
        border_w = 2
    pygame.draw.rect(surface, bg_color, (x, y, w, h), border_radius=6)
    pygame.draw.rect(surface, border_color, (x, y, w, h), border_w, border_radius=6)

    image_y = y + 3
    image_h = IMAGE_AREA_HEIGHT

    if not is_alive:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((0, 0, 0, 160))
        surface.blit(s, (x, y))

    img_x = x + 3
    img_w = w - 6
    if image:
        scaled = pygame.transform.smoothscale(image, (img_w, image_h))
        surface.blit(scaled, (img_x, image_y))
    else:
        placeholder = pygame.Surface((img_w, image_h))
        placeholder.fill((50, 50, 65))
        pygame.draw.rect(placeholder, (100, 100, 120), (0, 0, img_w, image_h), 1)
        surface.blit(placeholder, (img_x, image_y))

    name_bg = pygame.Surface((img_w, 20), pygame.SRCALPHA)
    name_bg.fill((0, 0, 0, 140))
    surface.blit(name_bg, (img_x, image_y + image_h - 20))
    font = get_font( 20)
    name_text = font.render(name, True, Colors.WHITE if is_alive else Colors.GRAY)
    surface.blit(name_text, (img_x + 4, image_y + image_h - 18))

    stat_y = image_y + image_h + 2
    stat_font = get_font( 16)
    bar_y = stat_y + 15
    bar_h = 6
    render_health_bar(surface, img_x, bar_y, img_w, bar_h, hp if is_alive else 0, max_hp)

    hp_str = f"HP:{hp}/{max_hp}" if is_alive else "阵亡"
    hp_text = stat_font.render(hp_str, True, Colors.TEXT_PRIMARY if is_alive else Colors.RED)
    surface.blit(hp_text, (img_x, bar_y + bar_h + 2))

    stat_str = f"武{force} 智{intelligence}"
    stat_text = stat_font.render(stat_str, True, Colors.TEXT_SECONDARY)
    surface.blit(stat_text, (img_x + img_w - 55, bar_y + bar_h + 2))

    if skill_name and skill_name != "无技能":
        skill_font = get_font( 14)
        skill_text = skill_font.render(skill_name[:5], True, Colors.ORANGE)
        surface.blit(skill_text, (img_x + 2, y + h - 14))


def render_button(surface, x, y, w, h, text, enabled=True, hover=False):
    if not enabled:
        color = Colors.BUTTON_DISABLED
    elif hover:
        color = Colors.BUTTON_HOVER
    else:
        color = Colors.BUTTON_BG
    pygame.draw.rect(surface, color, (x, y, w, h), border_radius=6)
    font = get_font( 28)
    text_color = Colors.WHITE if enabled else Colors.GRAY
    text_surf = font.render(text, True, text_color)
    text_rect = text_surf.get_rect(center=(x + w // 2, y + h // 2))
    surface.blit(text_surf, text_rect)
    return pygame.Rect(x, y, w, h)


# ==================== Pygame 主界面 ====================

class PygameUI:

    def __init__(self):
        self.screen = None
        self.clock = None
        self._init_display()

    def _init_display(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("三国武将卡牌游戏")
        self.clock = pygame.time.Clock()

    # —— 主菜单 ——

    def show_main_menu(self) -> str:
        menu_frame = 0
        while True:
            menu_frame += 1
            current_w, current_h = self.screen.get_size()
            
            # 绘制渐变背景
            for y in range(current_h):
                ratio = y / current_h
                r = int(30 + ratio * 20)
                g = int(30 + ratio * 15)
                b = int(40 + ratio * 30)
                pygame.draw.line(self.screen, (r, g, b), (0, y), (current_w, y))
            
            # 绘制装饰边框
            pygame.draw.line(self.screen, (255, 220, 50), (0, 0), (current_w, 0), 3)
            pygame.draw.line(self.screen, (255, 220, 50), (0, current_h - 1), (current_w, current_h - 1), 3)
            pygame.draw.line(self.screen, (100, 150, 200), (0, 80), (current_w, 80), 2)
            
            # 绘制装饰图案（左右边框）
            for i in range(5):
                pygame.draw.circle(self.screen, (255, 150, 50), (30, 120 + i * 120), 8)
                pygame.draw.circle(self.screen, (255, 150, 50), (current_w - 30, 120 + i * 120), 8)
            
            # 标题
            font_title = get_font(80)
            title = font_title.render("三国武将卡牌游戏", True, Colors.YELLOW)
            title_rect = title.get_rect(center=(current_w // 2, 120))
            # 标题阴影效果
            shadow = font_title.render("三国武将卡牌游戏", True, (50, 50, 50))
            self.screen.blit(shadow, (title_rect.x + 3, title_rect.y + 3))
            self.screen.blit(title, title_rect)
            
            # 副标题
            font_sub = get_font(32)
            sub = font_sub.render("霸·三国志大战 卡牌对战", True, (200, 220, 255))
            self.screen.blit(sub, sub.get_rect(center=(current_w // 2, 200)))
            
            # 装饰分割线
            pygame.draw.line(self.screen, (100, 150, 200), (current_w // 2 - 150, 240), (current_w // 2 + 150, 240), 2)
            
            # 按钮
            mx, my = pygame.mouse.get_pos()
            btn_start_rect = pygame.Rect(current_w // 2 - 120, 310, 240, 70)
            btn_quit_rect = pygame.Rect(current_w // 2 - 120, 410, 240, 70)
            
            # 绘制按钮with渐变和发光效果
            for btn_rect, text, is_start in [(btn_start_rect, "开 始 游 戏", True), 
                                              (btn_quit_rect, "退 出", False)]:
                is_hover = btn_rect.collidepoint(mx, my)
                
                # 按钮背景
                if is_hover:
                    color = (120, 180, 255)
                    glow_color = (150, 200, 255)
                    pygame.draw.rect(self.screen, glow_color, btn_rect.inflate(8, 8), border_radius=15)
                else:
                    color = (70, 130, 200)
                
                pygame.draw.rect(self.screen, color, btn_rect, border_radius=12)
                pygame.draw.rect(self.screen, (255, 220, 50) if is_hover else (100, 150, 200), btn_rect, 3, border_radius=12)
                
                # 按钮文字
                font_btn = get_font(36)
                btn_text = font_btn.render(text, True, Colors.WHITE)
                self.screen.blit(btn_text, btn_text.get_rect(center=btn_rect.center))
            
            # 底部信息
            font_info = get_font(14)
            info_lines = [
                "15位三国武将 | 6种主动技能 | 7种被动属性",
                "回合制策略对战 | 排兵布阵 | 技能消耗士气"
            ]
            for idx, line in enumerate(info_lines):
                info_text = font_info.render(line, True, Colors.TEXT_SECONDARY)
                self.screen.blit(info_text, info_text.get_rect(center=(current_w // 2, current_h - 70 + idx * 25)))
            
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_start_rect.collidepoint(event.pos): return "start"
                    if btn_quit_rect.collidepoint(event.pos): return "quit"
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE): return "start"
                    if event.key == pygame.K_ESCAPE: return "quit"
            self.clock.tick(FPS)

    # —— 选将 ——

    def show_general_selection(self, general_pool, player_name: str) -> list:
        selected = {}
        pool = list(general_pool)
        cards_per_row = 5
        card_w, card_h = 200, 280
        gap = 16
        scroll_offset = 0
        image_cache = {}

        while True:
            current_w, current_h = self.screen.get_size()
            start_x = (current_w - cards_per_row * (card_w + gap)) // 2
            start_y = 60
            rows = (len(pool) + cards_per_row - 1) // cards_per_row
            
            self.screen.fill(Colors.BG)
            title_font = get_font(36)
            title = title_font.render(
                f"{player_name} — 选择武将 (已选 {len(selected)} 人)", True, Colors.YELLOW)
            self.screen.blit(title, (30, 12))
            hint = get_font(18)
            self.screen.blit(hint.render("点击卡牌选择/取消，选完后点击「完成」", True, Colors.TEXT_SECONDARY), (30, 45))

            mx, my = pygame.mouse.get_pos()
            card_rects = []

            for i, general in enumerate(pool):
                row, col = i // cards_per_row, i % cards_per_row
                cx = start_x + col * (card_w + gap)
                cy = start_y + row * (card_h + gap) + scroll_offset
                if cy + card_h < 50 or cy > current_h - 100:
                    card_rects.append(None)
                    continue
                is_selected = general.general_id in selected
                rect = pygame.Rect(cx, cy, card_w, card_h)
                card_rects.append(rect)
                bg = Colors.CARD_SELECTED if is_selected else (
                    Colors.CARD_HOVER if rect.collidepoint(mx, my) else Colors.PANEL_BG)
                pygame.draw.rect(self.screen, bg, rect, border_radius=8)
                border_color = Colors.YELLOW if is_selected else Colors.GRAY
                pygame.draw.rect(self.screen, border_color, rect, 3, border_radius=8)

                if general.image_file and general.image_file not in image_cache:
                    try:
                        from src.utils.image_loader import get_image_loader
                        img = get_image_loader().get_general_image(general.image_file, size=(card_w - 8, 140))
                        image_cache[general.image_file] = img
                    except:
                        image_cache[general.image_file] = None
                img = image_cache.get(general.image_file)
                if img:
                    self.screen.blit(img, (cx + 4, cy + 4))
                else:
                    ph = pygame.Surface((card_w - 8, 140)); ph.fill((60, 60, 80))
                    self.screen.blit(ph, (cx + 4, cy + 4))

                name_bg = pygame.Surface((card_w - 8, 22), pygame.SRCALPHA); name_bg.fill((0, 0, 0, 150))
                self.screen.blit(name_bg, (cx + 4, cy + 122))
                fn = get_font( 18)
                self.screen.blit(fn.render(general.name, True, Colors.WHITE), (cx + 10, cy + 124))
                fs = get_font( 16)
                self.screen.blit(fs.render(f"{general.camp.value} | {general.rarity.name}", True, Colors.TEXT_SECONDARY), (cx + 8, cy + 152))
                self.screen.blit(fs.render(f"武{general.force} 智{general.intelligence} HP{general.max_hp}", True, Colors.TEXT_PRIMARY), (cx + 8, cy + 172))
                if general.attribute:
                    self.screen.blit(fs.render(f"属性: {' '.join(a.value for a in general.attribute)}", True, Colors.GREEN), (cx + 8, cy + 192))
                sk = get_font( 14)
                sk_name = general.active_skill.name if general.active_skill else "无"
                self.screen.blit(sk.render(f"技能: {sk_name}", True, Colors.ORANGE), (cx + 8, cy + 210))
                self.screen.blit(fs.render(f"费:{general.cost}", True, Colors.YELLOW), (cx + card_w - 40, cy + 6))
                if is_selected:
                    idx = list(selected.keys()).index(general.general_id) + 1
                    self.screen.blit(fn.render(f"✓ 第{idx}选", True, Colors.GREEN), (cx + 8, cy + 235))

            if selected:
                pf = get_font(22)
                self.screen.blit(pf.render("已选: " + "  ".join(g.name for g in selected.values()), True, Colors.YELLOW), (30, current_h - 90))

            btn_done = render_button(self.screen, current_w // 2 - 80, current_h - 50, 160, 42,
                                      f"完成选择 ({len(selected)}人)", len(selected) > 0,
                                      hover=pygame.Rect(current_w//2-80, current_h-50, 160, 42).collidepoint(mx, my))
            if rows > 2:
                self.screen.blit(hint.render("滚轮上下翻页", True, Colors.GRAY), (current_w - 120, 12))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); return None
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit(); return None
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if btn_done.collidepoint(event.pos) and len(selected) > 0:
                        return list(selected.values())
                    for i, rect in enumerate(card_rects):
                        if rect and rect.collidepoint(event.pos):
                            g = pool[i]
                            if g.general_id in selected: del selected[g.general_id]
                            else: selected[g.general_id] = g
                            break
                if event.type == pygame.MOUSEWHEEL:
                    scroll_offset += event.y * 40
                    min_scroll = min(0, -(rows * (card_h + gap) - (current_h - 200)))
                    scroll_offset = max(min_scroll, min(0, scroll_offset))
            self.clock.tick(FPS)

    # —— 布阵 ——

    def show_formation_setup(self, team, generals: list, player_name: str) -> bool:
        selected_general = None
        placed = set()
        g_cell_w, g_cell_h, g_gap = 100, 130, 6
        card_w, card_h = 400, 70

        while True:
            current_w, current_h = self.screen.get_size()
            # 动态计算位置：左边武将列表，右边阵型
            list_start_x = 30
            list_start_y = 100
            grid_start_x = list_start_x + card_w + 40
            grid_start_y = 100
            
            self.screen.fill(Colors.BG)
            ft = get_font(32)
            self.screen.blit(ft.render(f"{player_name} — 布置阵型", True, Colors.YELLOW), (30, 15))
            self.screen.blit(get_font(18).render("先点左边武将选中，再点右边格子放置。右键/空格取消选中。", True, Colors.TEXT_SECONDARY), (30, 50))

            mx, my = pygame.mouse.get_pos()
            fc = get_font(24); fs = get_font(18)
            self.screen.blit(fc.render("未放置的武将（点击选中）", True, Colors.TEXT_PRIMARY), (list_start_x, list_start_y - 30))

            unplaced = [g for g in generals if g.general_id not in placed]
            left_rects = []
            for i, general in enumerate(unplaced):
                cy = list_start_y + i * (card_h + 8)
                rect = pygame.Rect(list_start_x, cy, card_w, card_h)
                left_rects.append((rect, general))
                is_hover = rect.collidepoint(mx, my)
                is_sel = selected_general and selected_general.general_id == general.general_id
                bg = Colors.CARD_SELECTED if is_sel else (Colors.CARD_HOVER if is_hover else Colors.PANEL_BG)
                pygame.draw.rect(self.screen, bg, rect, border_radius=6)
                pygame.draw.rect(self.screen, Colors.YELLOW if is_sel else Colors.GRAY, rect, 2, border_radius=6)
                self.screen.blit(fc.render(general.name, True, Colors.WHITE), (list_start_x + 10, cy + 8))
                self.screen.blit(fs.render(f"武{general.force} 智{general.intelligence} HP{general.max_hp}", True, Colors.TEXT_SECONDARY), (list_start_x + 10, cy + 34))
                self.screen.blit(fs.render(f"技能: {general.active_skill.name if general.active_skill else '无'}", True, Colors.ORANGE), (list_start_x + 200, cy + 20))
                if general.attribute:
                    self.screen.blit(fs.render(f"属性: {' '.join(a.value for a in general.attribute)}", True, Colors.GREEN), (list_start_x + 200, cy + 44))

            self.screen.blit(fc.render("阵型 (点击放置)", True, Colors.TEXT_PRIMARY), (grid_start_x, grid_start_y - 30))
            grid_rects = {}
            for row in range(FORMATION_ROWS):
                for col in range(FORMATION_COLS):
                    cx = grid_start_x + col * (g_cell_w + g_gap)
                    cy = grid_start_y + row * (g_cell_h + g_gap)
                    rect = pygame.Rect(cx, cy, g_cell_w, g_cell_h)
                    grid_rects[(row, col)] = rect
                    pg = team.formation[row][col]
                    if pg:
                        pygame.draw.rect(self.screen, Colors.CARD_HOVER if rect.collidepoint(mx, my) else Colors.PANEL_BG, rect, border_radius=6)
                        pygame.draw.rect(self.screen, Colors.GRAY, rect, 2, border_radius=6)
                        self.screen.blit(fc.render(pg.name, True, Colors.WHITE), (cx + 5, cy + 30))
                        self.screen.blit(fs.render(f"{pg.force}武 {pg.intelligence}智", True, Colors.TEXT_SECONDARY), (cx + 5, cy + 60))
                        self.screen.blit(fs.render(f"HP{pg.max_hp}", True, Colors.GREEN), (cx + 5, cy + 85))
                    else:
                        is_hover = rect.collidepoint(mx, my) and selected_general is not None
                        pygame.draw.rect(self.screen, Colors.CARD_HOVER if is_hover else Colors.DARK_GRAY, rect, border_radius=6)
                        pygame.draw.rect(self.screen, Colors.GRAY, rect, 1, border_radius=6)
                        if is_hover:
                            self.screen.blit(fs.render("+", True, Colors.YELLOW), (cx + g_cell_w//2 - 6, cy + g_cell_h//2 - 8))

            btn_done = render_button(self.screen, grid_start_x + 250, current_h - 55, 160, 40,
                                      f"完成布置 ({len(placed)}/{len(generals)})", len(placed) == len(generals),
                                      hover=pygame.Rect(grid_start_x+250, current_h-55, 160, 40).collidepoint(mx, my))
            if selected_general:
                self.screen.blit(fc.render(f"已选中: {selected_general.name} → 点击右侧格子放置", True, Colors.GREEN), (30, current_h - 40))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); return False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_SPACE): selected_general = None
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, general in left_rects:
                        if rect.collidepoint(event.pos): selected_general = general; break
                    for (row, col), rect in grid_rects.items():
                        if rect.collidepoint(event.pos):
                            if selected_general and team.formation[row][col] is None:
                                for r in range(FORMATION_ROWS):
                                    for c in range(FORMATION_COLS):
                                        if team.formation[r][c] == selected_general:
                                            team.formation[r][c] = None
                                team.formation[row][col] = selected_general
                                placed.add(selected_general.general_id)
                                selected_general = None
                            elif team.formation[row][col] is not None and not selected_general:
                                selected_general = team.formation[row][col]
                                team.formation[row][col] = None
                                placed.discard(selected_general.general_id)
                            break
                    if btn_done.collidepoint(event.pos) and len(placed) == len(generals):
                        return True
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    selected_general = None
            self.clock.tick(FPS)

    # —— 掷骰 ——

    def show_dice_roll(self, p1_name: str, p2_name: str, dice1: int, dice2: int, first_player_name: str) -> bool:
        ft = get_font( 48); fd = get_font( 80); fn = get_font( 30)
        start_time = pygame.time.get_ticks()
        while pygame.time.get_ticks() - start_time < 1200:
            current_w, current_h = self.screen.get_size()
            self.screen.fill(Colors.BG)
            t = ft.render("掷骰子决定先手...", True, Colors.YELLOW)
            self.screen.blit(t, t.get_rect(center=(current_w // 2, 200)))
            ad1, ad2 = rnd.randint(1, 6), rnd.randint(1, 6)
            self.screen.blit(fd.render(str(ad1), True, Colors.RED), (current_w // 2 - 160, 320))
            self.screen.blit(fd.render(str(ad2), True, Colors.BLUE), (current_w // 2 + 60, 320))
            self.screen.blit(fn.render(p1_name, True, Colors.RED), (current_w // 2 - 130, 430))
            self.screen.blit(fn.render(p2_name, True, Colors.BLUE), (current_w // 2 + 70, 430))
            pygame.display.flip(); self.clock.tick(20)

        current_w, current_h = self.screen.get_size()
        self.screen.fill(Colors.BG)
        self.screen.blit(ft.render("掷骰子决定先手...", True, Colors.YELLOW), (current_w//2 - 150, 200))
        self.screen.blit(fd.render(str(dice1), True, Colors.RED), (current_w // 2 - 160, 320))
        self.screen.blit(fd.render(str(dice2), True, Colors.BLUE), (current_w // 2 + 60, 320))
        self.screen.blit(fn.render(p1_name, True, Colors.RED), (current_w // 2 - 130, 430))
        self.screen.blit(fn.render(p2_name, True, Colors.BLUE), (current_w // 2 + 70, 430))
        self.screen.blit(ft.render(f"{first_player_name} 获得先手！", True, Colors.GREEN), (current_w//2 - 200, 520))
        self.screen.blit(fn.render("点击继续...", True, Colors.GRAY), (current_w//2 - 70, 600))
        pygame.display.flip()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); return False
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN): return True
            self.clock.tick(FPS)

    def show_game_over(self, winner_name: str, turn_count: int) -> None:
        waiting = True
        while waiting:
            current_w, current_h = self.screen.get_size()
            self.screen.fill(Colors.BG)
            self.screen.blit(get_font(60).render("战斗结束", True, Colors.YELLOW), (current_w//2 - 120, 250))
            self.screen.blit(get_font(42).render(f"胜利方：{winner_name}", True, Colors.GREEN), (current_w//2 - 130, 340))
            self.screen.blit(get_font(30).render(f"总回合数：{turn_count}", True, Colors.TEXT_SECONDARY), (current_w//2 - 90, 400))
            self.screen.blit(get_font(30).render("点击任意处退出", True, Colors.GRAY), (current_w//2 - 110, 500))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False
            self.clock.tick(FPS)


# ==================== 战斗 Callbacks（重写版） ====================

class PygameBattleCallbacks(BattleCallbacks):

    def __init__(self, pygame_ui: PygameUI, team1_name: str, team2_name: str):
        self.ui = pygame_ui
        self.screen = pygame_ui.screen
        self.clock = pygame_ui.clock
        self.team1_name = team1_name
        self.team2_name = team2_name
        self.log_lines: List[str] = []
        self._last_status: Optional[BattleStatusData] = None
        self._image_cache: dict = {}
        self._quit_requested = False

    def _add_log(self, msg: str):
        self.log_lines.append(msg)
        if len(self.log_lines) > 100:
            self.log_lines = self.log_lines[-50:]

    # ===== 通知方法 =====

    def display_battle_status(self, data: BattleStatusData) -> None:
        self._last_status = data

    def on_turn_start(self, turn_count: int, player_name: str) -> None:
        self._add_log(f"══════ 第{turn_count}回合 - {player_name}的回合 ══════")
        self._render_and_pause(500)

    def on_skill_used(self, event: BattleEvent) -> None:
        self._add_log(f"🔥 {event.source_name} 使用「{event.skill_name}」")
        for d in event.details:
            self._add_log(f"   {d}")
        self._render_and_pause(900)

    def on_skill_failed(self, skill_name: str, reason: str) -> None:
        self._add_log(f"❌ 技能失败: {reason}")
        self._render_and_pause(400)

    def on_attack(self, event: BattleEvent) -> None:
        self._add_log(f"⚔ {event.source_name} 攻击 {event.target_name}，造成 {event.damage} 点伤害")
        self._render_and_pause(500)

    def on_general_defeated(self, event: BattleEvent) -> None:
        self._add_log(f"💀 {event.target_name} 阵亡！")
        self._render_and_pause(700)

    def on_battle_end(self, winner_name: str, turn_count: int) -> None:
        self._add_log(f"══════ 战斗结束！胜者：{winner_name} ══════")
        self._render_and_pause(500)
        self.ui.show_game_over(
            winner_name.split("的队伍")[0] if "的队伍" in winner_name else winner_name,
            turn_count)

    # ===== 请求方法（带退出检查和视觉反馈） =====

    def request_skill_use(self, available_generals: list, player_name: str) -> int:
        self._add_log(f"—— {player_name} 的技能阶段 ——")
        selected = -1

        while True:
            mx, my = pygame.mouse.get_pos()
            cell_rects = self._get_skill_cell_rects(available_generals)
            hover_idx = -1
            for i, rect in enumerate(cell_rects):
                if rect and rect.collidepoint(mx, my):
                    hover_idx = i
                    break

            self._render_battle_screen("skill", selected, hover_idx, available_generals, None)
            btn = render_button(self.screen, SCREEN_WIDTH // 2 - 80, BUTTON_Y + 20, 160, 48, "跳过技能阶段")
            sf = get_font( 26)
            self.screen.blit(sf.render("技能阶段 — 点击武将使用技能，或点击「跳过」", True, Colors.YELLOW), (SCREEN_WIDTH // 2 - 280, BUTTON_Y - 30))
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_0: return -1
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx2, my2 = event.pos
                    if btn.collidepoint(mx2, my2): return -1
                    for i, rect in enumerate(cell_rects):
                        if rect and rect.collidepoint(mx2, my2):
                            _, name, _, _, can_use = available_generals[i]
                            if can_use:
                                self._add_log(f"  {name} 准备使用技能")
                                return i
                            else:
                                self._add_log(f"  {name} 无法使用技能（冷却中或士气不足）")
            self.clock.tick(FPS)
        return -1

    def request_skill_target(self, caster_name: str, skill_name: str, possible_targets: list) -> int:
        self._add_log(f"{caster_name} 选择 {skill_name} 的目标...")
        while True:
            mx, my = pygame.mouse.get_pos()
            rects = self._get_enemy_cell_rects(possible_targets)
            hover_idx = -1
            for i, rect in enumerate(rects):
                if rect and rect.collidepoint(mx, my):
                    hover_idx = i
                    break
            self._render_battle_screen("skill_target", -1, hover_idx, None, possible_targets, caster_name, skill_name)
            sf = get_font( 26)
            self.screen.blit(sf.render(f"选择「{skill_name}」的目标 — 点击敌方武将", True, Colors.ORANGE), (SCREEN_WIDTH // 2 - 220, BUTTON_Y - 30))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx2, my2 = event.pos
                    for i, rect in enumerate(rects):
                        if rect and rect.collidepoint(mx2, my2): return i
            self.clock.tick(FPS)
        return -1

    def request_attack_action(self, attackers: list, targets: list, player_name: str) -> Tuple[int, int]:
        self._add_log(f"—— {player_name} 的攻击阶段 ——")
        selected_attacker = -1
        stage = 1

        while True:
            mx, my = pygame.mouse.get_pos()
            self._render_battle_screen("attack", selected_attacker, -1, attackers if stage == 1 else None, None)
            sf = get_font( 26)
            if stage == 1:
                hint = "攻击阶段 — 步骤1: 选择攻击武将（点击我方武将）"
            else:
                hint = f"攻击阶段 — 步骤2: {attackers[selected_attacker][1]} 已选中 → 点击敌方武将为目标"
            self.screen.blit(sf.render(hint, True, Colors.YELLOW), (SCREEN_WIDTH // 2 - 310, BUTTON_Y - 30))
            if selected_attacker >= 0:
                self.screen.blit(sf.render(f"攻击者: {attackers[selected_attacker][1]}", True, Colors.GREEN), (30, BUTTON_Y + 10))
                self.screen.blit(sf.render("右键/ESC 取消", True, Colors.GRAY), (SCREEN_WIDTH - 200, BUTTON_Y + 10))

            # 高亮悬停的敌人
            if stage == 2:
                enemy_rects = self._get_enemy_cell_rects(targets)
                for i, rect in enumerate(enemy_rects):
                    if rect and rect.collidepoint(mx, my):
                        pygame.draw.rect(self.screen, Colors.YELLOW, rect, 3, border_radius=6)
                        break

            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mx2, my2 = event.pos
                    if stage == 1:
                        rects_a = self._get_ally_cell_rects(attackers)
                        for i, rect in enumerate(rects_a):
                            if rect and rect.collidepoint(mx2, my2):
                                selected_attacker = i; stage = 2
                                self._add_log(f"  选择 {attackers[i][1]} 攻击")
                                break
                    else:
                        rects_t = self._get_enemy_cell_rects(targets)
                        for i, rect in enumerate(rects_t):
                            if rect and rect.collidepoint(mx2, my2):
                                self._add_log(f"  目标: {targets[i][1]}")
                                return (selected_attacker, i)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                    if stage == 2: stage = 1; selected_attacker = -1; self._add_log("  取消选择")
            self.clock.tick(FPS)
        return (-1, -1)

    # ===== 渲染辅助 =====

    def _render_and_pause(self, pause_ms: int):
        self._render_battle_screen("pause", -1, -1, None, None)
        pygame.display.flip()
        start_time = time.time()
        while time.time() - start_time < pause_ms / 1000.0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
            self.clock.tick(FPS)

    def _render_battle_screen(self, mode, selected_idx, hover_idx, highlight_generals, target_generals=None, caster_name="", skill_name=""):
        self.screen.fill(Colors.BG)
        data = self._last_status
        if not data:
            return

        phase_names = {"skill": "技能使用阶段", "skill_target": "技能目标选择", "attack": "普攻阶段", "pause": "战斗中"}
        phase_colors = {"skill": (100, 180, 100), "skill_target": (220, 150, 50), "attack": (200, 80, 80), "pause": (100, 100, 100)}
        ft = get_font( 32)
        self.screen.blit(ft.render(f"第{data.turn_count}回合 — {data.current_player_name} — {phase_names.get(mode, '战斗中')}", True, Colors.YELLOW), (SCREEN_WIDTH // 2 - 300, 15))
        pygame.draw.rect(self.screen, phase_colors.get(mode, (100, 100, 100)), (0, 52, SCREEN_WIDTH, 4))

        morale_y = 65
        fs = get_font( 20)
        for side, tn, morale, max_morale, xs in [(0, data.team1_name, data.team1_morale, data.team1_max_morale, GRID_LEFT_X), (1, data.team2_name, data.team2_morale, data.team2_max_morale, GRID_RIGHT_X)]:
            sn = tn.split("的队伍")[0] if "的队伍" in tn else tn
            self.screen.blit(fs.render(sn, True, Colors.TEXT_PRIMARY), (xs, morale_y))
            render_morale_bar(self.screen, xs + 60, morale_y + 2, 160, 14, morale, max_morale)
            self.screen.blit(fs.render(f"{morale}/{max_morale}", True, Colors.TEXT_SECONDARY), (xs + 225, morale_y))

        ally_data = data.team1_generals if self._is_team1_current() else data.team2_generals
        enemy_data = data.team2_generals if self._is_team1_current() else data.team1_generals

        self._render_team_grid("我方", ally_data, GRID_LEFT_X, GRID_Y, selected_idx, hover_idx, highlight_generals if mode != "skill_target" else None, True)
        self._render_team_grid("敌方", enemy_data, GRID_RIGHT_X, GRID_Y, selected_idx, hover_idx if mode in ("skill_target",) else -1, target_generals, False)

        log_font = get_font( 20)
        self.screen.blit(log_font.render("战斗日志", True, Colors.GRAY), (20, LOG_Y - 22))
        log_panel_top = LOG_Y
        pygame.draw.rect(self.screen, (35, 35, 45), (15, log_panel_top, SCREEN_WIDTH - 30, LOG_MAX_LINES * 22 + 4), border_radius=4)
        for i, line in enumerate(self.log_lines[-LOG_MAX_LINES:]):
            self.screen.blit(log_font.render(line[:90], True, Colors.TEXT_SECONDARY), (22, log_panel_top + 4 + i * 22))

    def _render_team_grid(self, label, generals, start_x, start_y, selected_idx, hover_idx, highlight_data, is_ally):
        fc = get_font( 22)
        self.screen.blit(fc.render(label, True, Colors.TEXT_PRIMARY), (start_x, start_y - 26))
        for row in range(FORMATION_ROWS):
            for col in range(FORMATION_COLS):
                cx = start_x + col * (CELL_WIDTH + CELL_GAP)
                cy = start_y + row * (CELL_HEIGHT + CELL_GAP)
                rect = pygame.Rect(cx, cy, CELL_WIDTH, CELL_HEIGHT)
                g = None
                for gen in generals:
                    if gen.get("position", "-") == f"({row},{col})":
                        g = gen; break
                mx, my = pygame.mouse.get_pos()
                is_hover = rect.collidepoint(mx, my)
                is_selected = False
                if highlight_data and is_ally and g:
                    for j, hd in enumerate(highlight_data):
                        if isinstance(hd, tuple) and j == selected_idx and hd[1] == g["name"]:
                            is_selected = True; break
                if g:
                    image = self._get_general_image(g)
                    render_general_cell(self.screen, cx, cy, CELL_WIDTH, CELL_HEIGHT, g["name"], g["current_hp"], g["max_hp"],
                                         force=g.get("force", 0), intelligence=g.get("intelligence", 0),
                                         skill_name=g.get("active_skill_name", ""), cooldown=g.get("active_skill_cooldown", 0),
                                         is_alive=g["is_alive"], selected=is_selected, hover=is_hover,
                                         selectable=is_ally and g["is_alive"], image=image)
                else:
                    pygame.draw.rect(self.screen, Colors.DARK_GRAY, rect, border_radius=6)
                    pygame.draw.rect(self.screen, (100, 100, 150) if is_hover else Colors.GRAY, rect, 1, border_radius=6)

    def _get_general_image(self, gen_data: dict):
        image_file = gen_data.get("image_file", "")
        if not image_file:
            return None
        if image_file in self._image_cache:
            return self._image_cache[image_file]
        try:
            from src.utils.image_loader import get_image_loader
            img = get_image_loader().get_general_image(image_file, size=(CELL_WIDTH - 6, IMAGE_AREA_HEIGHT))
            self._image_cache[image_file] = img
            return img
        except:
            return None

    def _is_team1_current(self) -> bool:
        if not self._last_status:
            return True
        return self._last_status.current_player_name in self.team1_name

    def _get_skill_cell_rects(self, available_generals):
        start_x = GRID_LEFT_X if self._is_team1_current() else GRID_RIGHT_X
        return [pygame.Rect(start_x, GRID_Y + i * (CELL_HEIGHT + CELL_GAP), CELL_WIDTH, CELL_HEIGHT) for i in range(len(available_generals))]

    def _get_enemy_cell_rects(self, targets):
        start_x = GRID_RIGHT_X if self._is_team1_current() else GRID_LEFT_X
        data = self._last_status
        if not data: return []
        gens = data.team2_generals if self._is_team1_current() else data.team1_generals
        rects = []
        for g in gens:
            if not g["is_alive"]: rects.append(None); continue
            ps = g.get("position", "-")
            if ps != "-":
                try:
                    pos = ps.strip("()").split(","); row, col = int(pos[0]), int(pos[1])
                    rects.append(pygame.Rect(start_x + col * (CELL_WIDTH + CELL_GAP), GRID_Y + row * (CELL_HEIGHT + CELL_GAP), CELL_WIDTH, CELL_HEIGHT))
                except: rects.append(None)
            else: rects.append(None)
        return rects

    def _get_ally_cell_rects(self, attackers):
        start_x = GRID_LEFT_X if self._is_team1_current() else GRID_RIGHT_X
        data = self._last_status
        if not data: return []
        gens = data.team1_generals if self._is_team1_current() else data.team2_generals
        rects = []
        for g in gens:
            if not g["is_alive"]: rects.append(None); continue
            ps = g.get("position", "-")
            if ps != "-":
                try:
                    pos = ps.strip("()").split(","); row, col = int(pos[0]), int(pos[1])
                    rects.append(pygame.Rect(start_x + col * (CELL_WIDTH + CELL_GAP), GRID_Y + row * (CELL_HEIGHT + CELL_GAP), CELL_WIDTH, CELL_HEIGHT))
                except: rects.append(None)
            else: rects.append(None)
        return rects
