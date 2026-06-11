"""
图片加载器
负责加载、缓存和缩放任意的武将卡图片
"""

import os
import pygame
from typing import Optional, Dict


class ImageLoader:
    """加载并缓存 pygame Surface，处理缺失图片的降级方案"""

    def __init__(self, assets_root: str = None):
        if assets_root is None:
            # 默认：项目根目录下的 assets/
            assets_root = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "assets"
            )
        self.assets_root = assets_root
        self._cache: Dict[str, pygame.Surface] = {}
        self._placeholder: Optional[pygame.Surface] = None

    @property
    def generals_dir(self) -> str:
        return os.path.join(self.assets_root, "images", "generals")

    def get_general_image(self, image_file: str, size: tuple = None) -> pygame.Surface:
        """
        获取武将卡图片

        Args:
            image_file: 图片文件名（如 'zhang_ren.png'）
            size: 目标尺寸 (w, h)，None = 保持原始尺寸

        Returns:
            pygame Surface
        """
        if not image_file:
            return self._get_placeholder(size)

        cache_key = f"{image_file}:{size}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # 尝试加载
        path = os.path.join(self.generals_dir, image_file)
        surf = self._load_and_scale(path, size)
        if surf is None:
            surf = self._get_placeholder(size)

        self._cache[cache_key] = surf
        return surf

    def _load_and_scale(self, path: str, size: tuple) -> Optional[pygame.Surface]:
        """加载并缩放图片，失败返回 None"""
        try:
            if not os.path.exists(path):
                return None
            surf = pygame.image.load(path).convert_alpha()
            if size:
                surf = pygame.transform.smoothscale(surf, size)
            return surf
        except Exception:
            return None

    def _get_placeholder(self, size: tuple) -> pygame.Surface:
        """获取占位图片（带武将图标）"""
        cache_key = f"__placeholder__:{size}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        w, h = size if size else (80, 80)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # 背景色块
        pygame.draw.rect(surf, (60, 60, 80), (0, 0, w, h), border_radius=6)
        pygame.draw.rect(surf, (120, 120, 140), (0, 0, w, h), 2, border_radius=6)

        # 文字 "武将"
        font = pygame.font.Font(None, max(16, w // 3))
        text = font.render("武将", True, (200, 200, 200))
        text_rect = text.get_rect(center=(w // 2, h // 2))
        surf.blit(text, text_rect)

        self._cache[cache_key] = surf
        return surf

    def preload_all(self, image_files: list, size: tuple = None):
        """预加载一批图片到缓存"""
        for f in image_files:
            if f:
                self.get_general_image(f, size)

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


# 全局单例
_loader: Optional[ImageLoader] = None


def get_image_loader() -> ImageLoader:
    global _loader
    if _loader is None:
        _loader = ImageLoader()
    return _loader
