"""Windows 桌面发行版入口。

双击打包后的 exe 会在本机回环地址启动游戏服务器、打开默认浏览器，
并在控制台按回车后安全关闭。游戏不会监听局域网地址。
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request
import webbrowser

from .server import GameServer, ThreadingHTTPServer


def create_server(port: int = 0) -> ThreadingHTTPServer:
    """创建仅本机可访问的服务器；port=0 时由系统选择空闲端口。"""
    return ThreadingHTTPServer(("127.0.0.1", port), GameServer)


def smoke_test() -> int:
    """供构建脚本验证打包入口和静态/API资源是否可用。"""
    server = create_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/state", timeout=10
        ) as response:
            state = json.load(response)
        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/index.html", timeout=10
        ) as response:
            page = response.read().decode("utf-8")
        if state.get("phase") != "menu" or "三国武将卡牌游戏" not in page:
            raise RuntimeError("启动器返回了异常的游戏内容")
        print("桌面启动器自检通过")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def run(open_browser: bool = True) -> int:
    server = create_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"

    print("=" * 48)
    print("  三国武将卡牌游戏")
    print("=" * 48)
    print(f"游戏地址：{url}")
    print("请保留此窗口；关闭窗口或按回车即可退出游戏。")

    if open_browser:
        # 给服务器一点启动时间，避免浏览器首次访问撞上启动瞬间。
        timer = threading.Timer(0.45, lambda: webbrowser.open(url, new=1))
        timer.daemon = True
        timer.start()

    try:
        input("\n按回车关闭游戏……")
    except (EOFError, KeyboardInterrupt):
        while thread.is_alive():
            time.sleep(0.25)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="三国武将卡牌游戏桌面启动器")
    parser.add_argument("--smoke-test", action="store_true", help="启动后自检并退出")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    options = parser.parse_args()
    if options.smoke_test:
        return smoke_test()
    return run(open_browser=not options.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
