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
    """验证网页、PvP、关键技能，以及三档 PvE 模型加载和推理。"""
    from src.battle.battle_system import BattleContext
    from src.game_data.generals_config import get_general_by_name
    from src.models.team import Team
    from src.rl.env_v3 import SanguoEnv
    from src.rl.opponents import HeuristicOpponent
    from src.web.server import GameState

    pvp = GameState()
    pvp.reset("pvp")
    if pvp.mode != "pvp" or pvp.phase != "select_p1":
        raise RuntimeError("PvP 初始化失败")

    concealed_state = GameState()
    concealed_state.reset("pve")
    ambush = get_general_by_name("张任")
    concealed_state.controller.player2.add_general_to_team(ambush)
    if not concealed_state.controller.player2.team.position_general(ambush, 1, 2):
        raise RuntimeError("伏兵测试阵位初始化失败")
    concealed = concealed_state.to_json()["p2"]["generals"][0]
    if "id" in concealed or (concealed["row"], concealed["col"]) != (-1, -1):
        raise RuntimeError("PvE 未显形伏兵泄露了身份或阵位")
    ambush.get_passive_skill("伏兵").trigger_counter()
    revealed = concealed_state.to_json()["p2"]["generals"][0]
    if (
        revealed.get("id") != ambush.general_id
        or (revealed.get("row"), revealed.get("col")) != (1, 2)
    ):
        raise RuntimeError("PvE 伏兵显形后未恢复武将卡和阵位")

    revival_team = Team("黄巾军")
    revival_enemy = Team("复活测试敌军")
    zhang_jiao = get_general_by_name("张角")
    fallen_ally = get_general_by_name("甘宁")
    for general in (zhang_jiao, fallen_ally):
        revival_team.add_general(general)
    revival_team.position_general(zhang_jiao, 0, 0)
    revival_team.position_general(fallen_ally, 1, 1)
    fallen_ally.is_alive = False
    fallen_ally.current_hp = 0
    revival_team.remove_general_from_formation(fallen_ally)
    revival = revival_team.use_skill(
        zhang_jiao, [], BattleContext(revival_team, revival_enemy),
    )
    if (
        not revival.get("success")
        or not fallen_ally.is_alive
        or revival_team.get_general_position(fallen_ally) != (1, 1)
    ):
        raise RuntimeError("太平要术未把阵亡武将复活到战场原位")

    weakening_team = Team("魏军")
    weakening_enemy = Team("连计测试敌军")
    guo_huanghou = get_general_by_name("郭皇后")
    strong_enemy = get_general_by_name("张飞")
    weak_enemy = get_general_by_name("张角")
    weakening_team.add_general(guo_huanghou)
    weakening_enemy.add_general(strong_enemy)
    weakening_enemy.add_general(weak_enemy)
    strong_force = strong_enemy.get_effective_force()
    weakening = weakening_team.use_skill(
        guo_huanghou, [], BattleContext(weakening_team, weakening_enemy),
    )
    if (
        not weakening.get("success")
        or strong_enemy.get_effective_force() != strong_force - 3
        or weak_enemy.get_effective_force() != weak_enemy.force
    ):
        raise RuntimeError("电脑衰弱的连计未自动选择高武力敌将")

    for difficulty in ("easy", "normal", "hard"):
        pve = GameState()
        pve.reset("pve", difficulty)
        controller = pve.ensure_pve_controller().load()
        if not controller.available or not controller.prebattle.available:
            raise RuntimeError(
                f"{difficulty} 档模型加载失败: {'; '.join(controller.load_errors)}"
            )

        draft = controller.choose_draft(
            pve.pool_p2[:4], pve.controller.player1.selected_generals, pve.cost_limit,
        )
        formation = controller.choose_formation(draft, pve.controller.player1)
        if not draft or len(formation) != len(draft):
            raise RuntimeError(f"{difficulty} 档选将或布阵推理失败")

        env = SanguoEnv(HeuristicOpponent())
        observation, info = env.reset(2026072500)
        action = controller.choose_battle_action(observation, info["action_mask"])
        if action is None or info["action_mask"][action] != 0:
            raise RuntimeError(f"{difficulty} 档战斗模型生成了非法动作")

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
        print("桌面启动器自检通过：PvP、三档 PvE 模型、伏兵与关键技能均可用")
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
