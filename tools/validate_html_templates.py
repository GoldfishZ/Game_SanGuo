"""
HTML模板括号校验工具
解析 game.js / dom-utils.js 中的 HTML 字符串拼接代码，校验标签括号配对。

用法: python tools/validate_html_templates.py
"""

import re
import os
import sys

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "ui", "static")

# 自闭合标签（不需要配对闭合标签）
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

# 用于从 JS 字符串拼接中提取 HTML 标签的模式
TAG_PATTERN = re.compile(r"<\s*/?\s*(\w+)[^>]*/?\s*>", re.IGNORECASE)


def extract_html_from_js(filepath):
    """从 JS 文件中提取所有 HTML 相关的代码行。"""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    html_lines = []
    in_html = False
    buffer = ""

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # 检测 HTML 字符串拼接行
        has_html_tag = bool(re.search(r"<\s*(\w+)", stripped))
        has_html_attr = bool(re.search(r"class\s*=\s*['\"]|data-\w+\s*=", stripped))
        if has_html_tag or (in_html and has_html_attr):
            in_html = True
            buffer += " " + stripped
            # 检测行尾是否结束 HTML 段
            if stripped.rstrip().endswith(";") or stripped.rstrip().endswith("+"):
                html_lines.append((i, buffer.strip()))
                buffer = ""
                in_html = False
        elif in_html:
            # 继续累积
            buffer += " " + stripped
            if stripped.rstrip().endswith(";") or not stripped.endswith("+"):
                html_lines.append((i, buffer.strip()))
                buffer = ""
                in_html = False

    return html_lines


def validate_tags_in_line(line_text):
    """检查一行中的 HTML 标签配对。"""
    errors = []
    tags = TAG_PATTERN.findall(line_text)
    stack = []

    for tag_match in re.finditer(TAG_PATTERN, line_text):
        full = tag_match.group(0)
        tag = tag_match.group(1).lower()

        if tag in VOID_ELEMENTS:
            continue
        if full.startswith("</"):
            # 闭合标签
            if not stack:
                errors.append(f"多余的闭合标签 </{tag}>（无对应开标签）")
            elif stack[-1] != tag:
                errors.append(f"标签不匹配：期望 </{stack[-1]}>，但遇到 </{tag}>")
                # 尝试恢复：弹出直到匹配
                temp = list(stack)
                while temp and temp[-1] != tag:
                    temp.pop()
                if not temp:
                    stack.pop()
                else:
                    stack = temp
                    stack.pop()
            else:
                stack.pop()
        elif not full.endswith("/>"):
            # 开标签
            stack.append(tag)

    if stack:
        errors.append(f"未闭合标签: {', '.join(f'<{t}>' for t in stack)}")

    return errors


def validate_innerhtml_calls(filepath):
    """检查 innerHTML 赋值中的 HTML 字符串。"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找所有 innerHTML = ... 的模式
    pattern = re.compile(r"\.innerHTML\s*=\s*(.+?);", re.DOTALL)
    matches = pattern.findall(content)

    all_errors = []
    for i, match in enumerate(matches):
        # 简化：只检查这个赋值中的标签配对
        errors = validate_tags_in_line(match)
        if errors:
            # 找到在文件中的行号
            line_no = content[: content.find(match)].count("\n") + 1
            for err in errors:
                all_errors.append(f"行 {line_no}: {err}")

    return all_errors


def main():
    game_js = os.path.join(STATIC_DIR, "game.js")
    dom_utils_js = os.path.join(STATIC_DIR, "dom-utils.js")

    all_errors = []

    for filepath in [game_js, dom_utils_js]:
        if not os.path.exists(filepath):
            print(f"[SKIP] {filepath} — 文件不存在")
            continue

        print(f"[CHECK] {filepath}")

        # 方式1: 逐行检查 HTML 标签
        html_lines = extract_html_from_js(filepath)
        line_errors = 0
        for line_no, text in html_lines:
            errors = validate_tags_in_line(text)
            for err in errors:
                all_errors.append(f"{os.path.basename(filepath)}:{line_no}: {err}")
                line_errors += 1

        if line_errors:
            print(f"  ✗ 逐行检查发现 {line_errors} 个问题")
        else:
            print(f"  ✓ 逐行检查通过")

        # 方式2: 检查 innerHTML 赋值
        inner_errors = validate_innerhtml_calls(filepath)
        for err in inner_errors:
            all_errors.append(f"{os.path.basename(filepath)}: {err}")

        if inner_errors:
            print(f"  ✗ innerHTML 检查发现 {len(inner_errors)} 个问题")
        else:
            print(f"  ✓ innerHTML 检查通过")

    if all_errors:
        print(f"\n{'='*50}")
        print(f"共发现 {len(all_errors)} 个问题:")
        for err in all_errors:
            print(f"  • {err}")
        print(f"\n建议在修改代码后重新运行此脚本验证。")
        return 1

    print(f"\n{'='*50}")
    print("✓ 所有 HTML 标签配对检查通过！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
