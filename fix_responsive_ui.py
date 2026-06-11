'''
FilePath: \Game_SanGuo\fix_responsive_ui.py
Author: GoldfishZ 2366385033@qq.com
Date: 2026-06-11 21:22:31
LastEditors: GoldfishZ 2366385033@qq.com
LastEditTime: 2026-06-11 21:22:31
Copyright: 2026 CUHK(SZ).DS institude. All Rights Reserved.
Description: Work done by GoldfishZ!
'''
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修改 pygame_ui.py 使其响应窗口大小变化
"""
import re
import os

file_path = os.path.join(os.path.dirname(__file__), 'src', 'ui', 'pygame_ui.py')

# 读取文件
print(f"读取文件: {file_path}")
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # 检查是否在 show_dice_roll 函数中
    if 'def show_dice_roll' in line:
        # 找到 while pygame.time.get_ticks() - start_time < 1200: 这一行
        j = i
        while j < len(lines) and 'while pygame.time.get_ticks() - start_time < 1200:' not in lines[j]:
            j += 1
        
        # 复制到这一行
        new_lines.extend(lines[i:j+1])
        i = j + 1
        
        # 添加 current_w, current_h 的获取
        indent = '            '
        new_lines.append(f'{indent}current_w, current_h = self.screen.get_size()\n')
        
        # 继续处理后面的行，替换 SCREEN_WIDTH
        while i < len(lines) and (lines[i].startswith('            ') or lines[i].strip() == ''):
            line = lines[i]
            if 'SCREEN_WIDTH' in line:
                line = line.replace('SCREEN_WIDTH', 'current_w')
            new_lines.append(line)
            i += 1
            
            # 检查是否到了 while 循环的结尾（下一个 self.screen.fill）
            if lines[i-1].strip().startswith('self.screen.fill(Colors.BG)'):
                # 这是第二个 self.screen.fill，意味着我们要添加 current_w, current_h 再次
                if i < len(lines) and 'SCREEN_WIDTH' in lines[i]:
                    new_lines.append(f'{indent}current_w, current_h = self.screen.get_size()\n')
                break
    else:
        # 对于其他行，检查是否需要替换 SCREEN_WIDTH
        if 'SCREEN_WIDTH' in line and 'def ' not in line:
            # 检查是否已经有 current_w 定义（简单启发式）
            if i > 0 and 'current_w, current_h = self.screen.get_size()' not in ''.join(new_lines[-5:]):
                # 替换
                line = line.replace('SCREEN_WIDTH', 'current_w')
        
        new_lines.append(line)
        i += 1

# 写回文件
print(f"写入修改后的文件...")
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✓ 修改完成")
