"""
图片优化工具
将 PNG 武将图和背景图转换为 WebP 格式，减小文件大小。

用法: python tools/optimize_images.py

输出:
  assets/images/generals_webp/  — 战斗用缩略图 (max 600px 高度, quality 80)
  assets/images/generals_full/  — 预览/图鉴用 (max 900px 高度, quality 85)
  assets/images/backgrounds_webp/ — 背景图 (1920px 宽, quality 80)

WebP 格式比 PNG 小 85-97%，同时保持良好画质。
"""

import os
import sys
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "assets", "images")
GENERALS_SRC = os.path.join(SRC_DIR, "generals")
BACKGROUNDS_SRC = os.path.join(SRC_DIR, "backgrounds")

GENERALS_WEBP = os.path.join(SRC_DIR, "generals_webp")
GENERALS_FULL = os.path.join(SRC_DIR, "generals_full")
BACKGROUNDS_WEBP = os.path.join(SRC_DIR, "backgrounds_webp")


def convert_to_webp(src_path, dst_path, max_width=None, max_height=None, quality=80):
    """将图片转为 WebP，可选缩放。"""
    img = Image.open(src_path)

    # 如果原图是 RGBA，转为 RGB（WebP 支持 RGBA 但文件更大）
    if img.mode == "RGBA":
        # 用白色背景替换透明
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 缩放
    if max_width or max_height:
        w, h = img.size
        if max_width and w > max_width:
            ratio = max_width / w
            w, h = max_width, int(h * ratio)
        if max_height and h > max_height:
            ratio = max_height / h
            w, h = int(w * ratio), max_height
        if (w, h) != img.size:
            img = img.resize((w, h), Image.LANCZOS)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    img.save(dst_path, "WEBP", quality=quality)
    return os.path.getsize(dst_path)


def format_size(size_bytes):
    """格式化文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def main():
    print("=" * 50)
    print("三国武将卡牌游戏 — 图片优化")
    print("=" * 50)

    total_original = 0
    total_optimized = 0

    # 1. 武将图 — 战斗缩略图
    print("\n[1/3] 武将战斗缩略图 (max 600px 高) → generals_webp/")
    if not os.path.exists(GENERALS_SRC):
        print("  跳过 — 武将图目录不存在")
    else:
        pngs = [f for f in os.listdir(GENERALS_SRC) if f.endswith(".png")]
        for fname in sorted(pngs):
            src = os.path.join(GENERALS_SRC, fname)
            dst = os.path.join(GENERALS_WEBP, fname.replace(".png", ".webp"))
            orig_size = os.path.getsize(src)
            opt_size = convert_to_webp(src, dst, max_height=600, quality=80)
            total_original += orig_size
            total_optimized += opt_size
            print(f"  {fname}: {format_size(orig_size)} → {format_size(opt_size)} ({opt_size/orig_size*100:.0f}%)")

    # 2. 武将图 — 预览全尺寸
    print("\n[2/3] 武将预览图 (max 900px 高) → generals_full/")
    if not os.path.exists(GENERALS_SRC):
        print("  跳过")
    else:
        pngs = [f for f in os.listdir(GENERALS_SRC) if f.endswith(".png")]
        for fname in sorted(pngs):
            src = os.path.join(GENERALS_SRC, fname)
            dst = os.path.join(GENERALS_FULL, fname.replace(".png", ".webp"))
            orig_size = os.path.getsize(src)
            opt_size = convert_to_webp(src, dst, max_height=900, quality=85)
            total_original += orig_size
            total_optimized += opt_size
            print(f"  {fname}: {format_size(orig_size)} → {format_size(opt_size)} ({opt_size/orig_size*100:.0f}%)")

    # 3. 背景图
    print("\n[3/3] 背景图 (max 1920px 宽) → backgrounds_webp/")
    if not os.path.exists(BACKGROUNDS_SRC):
        print("  跳过")
    else:
        pngs = [f for f in os.listdir(BACKGROUNDS_SRC) if f.endswith(".png")]
        for fname in sorted(pngs):
            src = os.path.join(BACKGROUNDS_SRC, fname)
            dst = os.path.join(BACKGROUNDS_WEBP, fname.replace(".png", ".webp"))
            orig_size = os.path.getsize(src)
            opt_size = convert_to_webp(src, dst, max_width=1920, quality=80)
            total_original += orig_size
            total_optimized += opt_size
            print(f"  {fname}: {format_size(orig_size)} → {format_size(opt_size)} ({opt_size/orig_size*100:.0f}%)")

    print(f"\n{'=' * 50}")
    print(f"总计: {format_size(total_original)} → {format_size(total_optimized)}")
    if total_original > 0:
        print(f"节省: {format_size(total_original - total_optimized)} ({(1 - total_optimized/total_original)*100:.1f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
