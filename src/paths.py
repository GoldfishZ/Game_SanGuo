"""项目路径的单一来源，兼容源码运行和 PyInstaller 单文件运行。"""

from __future__ import annotations

from pathlib import Path
import sys


if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

ASSETS_DIR = PROJECT_ROOT / "assets"
MODELS_DIR = ASSETS_DIR / "models"
PVE_MODELS_DIR = MODELS_DIR / "pve"
IMAGES_DIR = ASSETS_DIR / "images"
GENERALS_DIR = IMAGES_DIR / "generals"
GENERALS_WEBP_DIR = IMAGES_DIR / "generals_webp"
GENERALS_FULL_DIR = IMAGES_DIR / "generals_full"
BACKGROUNDS_DIR = IMAGES_DIR / "backgrounds"
BACKGROUNDS_WEBP_DIR = IMAGES_DIR / "backgrounds_webp"
WEB_STATIC_DIR = PROJECT_ROOT / "src" / "web" / "static"
