"""兼容启动入口：桌面发行版实现在 src.web.desktop。"""

from src.web.desktop import main


if __name__ == "__main__":
    raise SystemExit(main())
