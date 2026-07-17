"""兼容启动入口：Web 服务器实现在 src.web.server。"""

from src.web.server import *  # noqa: F401,F403 - 保留原有公共导入接口


if __name__ == "__main__":
    start()
