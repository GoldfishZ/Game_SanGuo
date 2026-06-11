'''
FilePath: \Game_SanGuo\apply_responsive_patch.py
Author: GoldfishZ 2366385033@qq.com
Date: 2026-06-11 21:25:00
LastEditors: GoldfishZ 2366385033@qq.com
LastEditTime: 2026-06-11 21:25:00
Copyright: 2026 CUHK(SZ).DS institude. All Rights Reserved.
Description: Work done by GoldfishZ!
'''
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pygame_ui.py 的响应式布局补丁
在 pygame_ui.py 中动态获取窗口大小
"""

import sys
import os

def apply_responsive_layout_patch():
    """应用响应式布局补丁到 pygame_ui.py"""
    file_path = os.path.join(os.path.dirname(__file__), 'src', 'ui', 'pygame_ui.py')
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. 在 show_dice_roll 的第一个 while 循环中添加 current_w, current_h
    old_code = """        while pygame.time.get_ticks() - start_time < 1200:
            self.screen.fill(Colors.BG)"""
    
    new_code = """        while pygame.time.get_ticks() - start_time < 1200:
            current_w, current_h = self.screen.get_size()
            self.screen.fill(Colors.BG)"""
    
    content = content.replace(old_code, new_code)
    
    # 2. 在第二个 screen.fill 前添加
    old_code2 = """        self.screen.fill(Colors.BG)
        self.screen.blit(ft.render("掷骰子决定先手...", True, Colors.YELLOW), ft.render("X", True, Colors.BG).get_rect(center=(SCREEN_WIDTH//2, 200)))
        self.screen.blit(ft.render("掷骰子决定先手...", True, Colors.YELLOW), (SCREEN_WIDTH//2 - 150, 200))"""
    
    new_code2 = """        current_w, current_h = self.screen.get_size()
        self.screen.fill(Colors.BG)
        self.screen.blit(ft.render("掷骰子决定先手...", True, Colors.YELLOW), (current_w//2 - 150, 200))"""
    
    content = content.replace(old_code2, new_code2)
    
    # 3. 替换 show_dice_roll 中的所有 SCREEN_WIDTH // 2
    # 保留只在这个函数中的替换
    lines = content.split('\n')
    new_lines = []
    in_dice_roll = False
    
    for i, line in enumerate(lines):
        if 'def show_dice_roll' in line:
            in_dice_roll = True
        elif in_dice_roll and line.startswith('    def '):
            in_dice_roll = False
        
        if in_dice_roll and 'SCREEN_WIDTH' in line:
            line = line.replace('SCREEN_WIDTH', 'current_w')
        
        new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True

if __name__ == '__main__':
    try:
        if apply_responsive_layout_patch():
            print("✓ 响应式布局补丁已应用")
            sys.exit(0)
    except Exception as e:
        print(f"✗ 应用补丁失败: {e}")
        sys.exit(1)
