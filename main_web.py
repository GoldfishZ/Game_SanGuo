"""
三国武将卡牌游戏 — Web 版服务器
使用 Python 内置 http.server，零外部依赖。
启动后浏览器访问 http://localhost:8088 即可游玩。
"""

import json
import os
import sys
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.game_flow import GameFlowController, Player
from src.models.general import General
from src.models.team import Team
from src.battle.battle_system import BattleSystem
from game_data.generals_data import GENERALS_DATA
from game_data.generals_bios import GENERALS_BIOGRAPHY
from game_data.skills_config import ALL_SKILLS

# ---- Static files serving ----
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "ui", "static")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
GENERALS_IMG_DIR = os.path.join(ASSETS_DIR, "images", "generals")
BG_DIR = os.path.join(ASSETS_DIR, "images", "backgrounds")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".js":   "application/javascript; charset=utf-8",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".ico":  "image/x-icon",
    ".json": "application/json",
}


class GameState:
    """全局游戏状态——单例（简单实现，不涉及并发安全）"""
    def __init__(self):
        self.controller: GameFlowController = None
        self.phase = "menu"
        self.battle_system: BattleSystem = None
        self.battle_callbacks = None
        self.last_event = ""
        self.turn_count = 0
        self.winner = ""
        self.cost_limit = 8.0
        self.pool_p1 = []  # 玩家1的独立选将池
        self.pool_p2 = []  # 玩家2的独立选将池

    def _make_pool(self, chosen_data):
        """Generate one player's draft pool from already selected raw general data."""
        pool = []
        for i, data in enumerate(chosen_data):
            from game_data.generals_config import create_general_from_data
            g = create_general_from_data(data)
            g.pool_index = i + 1
            pool.append(g)
        return pool

    def _make_distinct_pools(self, pool_size=16):
        """Split the full roster into two non-overlapping draft pools."""
        from game_data.generals_data import GENERALS_DATA
        import random as _rnd
        shuffled = list(GENERALS_DATA)
        _rnd.shuffle(shuffled)
        first = shuffled[:pool_size]
        second = shuffled[pool_size:pool_size * 2]
        return self._make_pool(first), self._make_pool(second)

    def reset(self):
        self.controller = GameFlowController()
        self.pool_p1, self.pool_p2 = self._make_distinct_pools()
        self.phase = "select_p1"
        self.battle_system = None
        self.last_event = "游戏已初始化"

    def to_json(self):
        c = self.controller
        if not c:
            return json.dumps({"phase": "menu"})
        result = {"phase": self.phase, "event": self.last_event,
                  "turn": self.turn_count, "winner": self.winner,
                  "cost_limit": self.cost_limit}
        if self.battle_system:
            current_team = self.battle_system.current_side
            result["current_team"] = "p1" if current_team == c.player1.team else "p2"
            result["current_player"] = c.player1.name if current_team == c.player1.team else c.player2.name
        # 武将池——根据当前阶段返回对应玩家的池子
        active_pool = self.pool_p1 if self.phase == "select_p1" else self.pool_p2
        result["pool"] = [{"id": g.general_id, "name": g.name,
                           "camp": g.camp.value, "rarity": g.rarity.name,
                           "force": g.force, "intelligence": g.intelligence,
                           "cost": g.cost, "image": g.image_file or "",
                           "attributes": [a.value for a in (g.attribute or [])],
                           "skill": g.active_skill.name if g.active_skill else "无",
                           "skill_desc": g.active_skill.description if g.active_skill else "",
                           "bio": GENERALS_BIOGRAPHY.get(g.name, {}).get("text", ""),
                           "years": GENERALS_BIOGRAPHY.get(g.name, {}).get("years", ""),
                           "courtesy": GENERALS_BIOGRAPHY.get(g.name, {}).get("courtesy", ""),
                           }
                          for g in active_pool]
        # 双方队伍
        if c.player1 and c.player1.selected_generals:
            result["p1"] = self._team_json(c.player1)
        if c.player2 and c.player2.selected_generals:
            result["p2"] = self._team_json(c.player2)
        # 先手
        if c.first_player:
            result["first"] = c.first_player.name
        if c.second_player:
            result["second"] = c.second_player.name
        return result

    def _team_json(self, player):
        p = player
        gens = []
        for g in p.selected_generals:
            pos = p.team.get_general_position(g)
            gens.append({
                "name": g.name, "id": g.general_id,
                "hp": g.current_hp, "maxHp": g.max_hp,
                "force": g.force, "intelligence": g.intelligence,
                "alive": g.is_alive,
                "row": pos[0] if pos else -1, "col": pos[1] if pos else -1,
                "skill": g.active_skill.name if g.active_skill else "",
                "skill_desc": g.active_skill.description if g.active_skill else "",
                "cooldown": g.active_skill_cooldown,
                "image": g.image_file or "",
            })
        return {
            "name": p.name,
            "morale": p.team.current_morale,
            "maxMorale": p.team.max_morale,
            "generals": gens,
        }


STATE = GameState()


# ---- API Handler ----
def handle_api(path, body, handler):
    global STATE
    c = STATE.controller

    # POST /api/new → 开始新游戏
    if path == "/api/new":
        STATE.reset()
        return STATE.to_json()

    # POST /api/select → {"general_ids": [1,2,...]}
    if path == "/api/select":
        ids = body.get("general_ids", [])
        selected_ids = set()
        for gid in ids:
            try:
                selected_ids.add(int(gid))
            except (TypeError, ValueError):
                continue
        pool = STATE.pool_p1 if STATE.phase == "select_p1" else STATE.pool_p2
        target_player = c.player1 if STATE.phase == "select_p1" else c.player2
        for gid in selected_ids:
            for g in pool:
                if g.general_id == gid and hasattr(g, 'pool_index'):
                    target_player.add_general_to_team(g)
                    delattr(g, 'pool_index')
        if STATE.phase == "select_p1":
            STATE.phase = "select_p2"
            STATE.last_event = "玩家1已选择，轮到玩家2"
        else:
            STATE.phase = "formation_p1"
            STATE.last_event = "选将完成，进入布阵"
        return STATE.to_json()

    # POST /api/place → {"positions": {"row": 0, "col": 0, "general_id": 1}, ...}
    if path == "/api/place":
        positions = body.get("positions", [])
        target_player = c.player1 if STATE.phase == "formation_p1" else c.player2
        for p in positions:
            g = next((gen for gen in target_player.selected_generals
                      if gen.general_id == p["general_id"]), None)
            if g:
                target_player.team.position_general(g, p["row"], p["col"])
        if positions:
            STATE.last_event = f"{target_player.name}已更新布阵"
            return STATE.to_json()
        if STATE.phase == "formation_p1":
            STATE.phase = "formation_p2"
            STATE.last_event = "玩家1布阵完成"
        else:
            STATE.phase = "dice"
            STATE.last_event = "布阵完成，准备掷骰"
        return STATE.to_json()

    # POST /api/dice → 掷骰子
    if path == "/api/dice":
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        if d1 > d2:
            c.first_player, c.second_player = c.player1, c.player2
        else:
            c.first_player, c.second_player = c.player2, c.player1
        c.current_player = c.first_player
        # 后手补偿
        c.second_player.team.max_morale += 2
        c.second_player.team.current_morale += 2
        STATE.phase = "battle"
        STATE.last_event = f"{c.first_player.name} 先手！骰子: {d1} vs {d2}"
        STATE.turn_count = 0
        # 启动战斗
        STATE.battle_system = BattleSystem(
            team1=c.player1.team, team2=c.player2.team,
            callbacks=None,
            first_player_team_name=c.first_player.team.team_name,
        )
        STATE.battle_system.turn_count = 1
        STATE.turn_count = 1
        STATE.battle_system.current_side.update_effects()
        return STATE.to_json()

    # POST /api/battle/next or /api/battle/skip -> end current player's turn
    if path in ("/api/battle/next", "/api/battle/skip") and STATE.battle_system:
        bs = STATE.battle_system
        if bs._is_game_over():
            STATE.phase = "over"
            STATE.winner = bs._determine_winner()
            wn = STATE.winner
            for p in [c.player1, c.player2]:
                if p.team.team_name == wn:
                    STATE.winner = p.name
            STATE.last_event = f"战斗结束，{STATE.winner} 获胜"
            return STATE.to_json()

        bs._end_turn_cleanup()
        bs._switch_to_next_player()
        bs.turn_count += 1
        STATE.turn_count = bs.turn_count
        bs.current_side.update_effects()
        current_player = c.player1.name if bs.current_side == c.player1.team else c.player2.name
        STATE.last_event = f"第{STATE.turn_count}回合，轮到{current_player}行动"
        return STATE.to_json()

    # POST /api/battle/skill -> {"general_id": 1} or legacy {"general_index": 0}
    if path == "/api/battle/skill" and STATE.battle_system:
        bs = STATE.battle_system
        caster = None
        gid = body.get("general_id", None)
        if gid is not None:
            try:
                gid = int(gid)
            except (TypeError, ValueError):
                gid = None
            caster = next((g for g in bs.current_side.get_alive_generals()
                           if g.general_id == gid), None)
        else:
            idx = body.get("general_index", -1)
            alive = bs.current_side.get_alive_generals()
            if 0 <= idx < len(alive):
                caster = alive[idx]

        if caster and caster.can_use_active_skill():
            from src.skills.skill_base import TargetType
            tt = caster.active_skill.target_type
            if tt == TargetType.SELF:
                targets = [caster]
            elif tt == TargetType.ALL_ALLIES:
                targets = bs.current_side.get_alive_generals()
            else:
                enemy = bs._get_enemy_team().get_alive_generals()
                targets = [enemy[0]] if enemy else []
            result = caster.use_active_skill(targets, bs.battle_context, bs.current_side)
            STATE.last_event = f"{caster.name} 使用 {caster.active_skill.name}" if result.get("success") else result.get("message", "技能失败")
            if bs._is_game_over():
                STATE.phase = "over"
                STATE.winner = bs._determine_winner()
        else:
            STATE.last_event = "该武将无法使用技能"
        return STATE.to_json()

    # POST /api/battle/attack -> {"attacker_id": 1, "target_id": 2} or legacy indexes
    if path == "/api/battle/attack" and STATE.battle_system:
        bs = STATE.battle_system
        attackers = bs.current_side.get_alive_generals()
        enemy_team = bs._get_enemy_team()
        attacker = None
        target = None

        attacker_id = body.get("attacker_id", None)
        target_id = body.get("target_id", None)
        if attacker_id is not None:
            try:
                attacker_id = int(attacker_id)
            except (TypeError, ValueError):
                attacker_id = None
            attacker = next((g for g in attackers if g.general_id == attacker_id), None)
        else:
            a = body.get("attacker", 0)
            if 0 <= a < len(attackers):
                attacker = attackers[a]

        if attacker:
            legal_targets = bs._get_attack_targets_for_attacker(attacker)
            if target_id is not None:
                try:
                    target_id = int(target_id)
                except (TypeError, ValueError):
                    target_id = None
                target = next((g for g in legal_targets if g.general_id == target_id), None)
            else:
                t = body.get("target", 0)
                if 0 <= t < len(legal_targets):
                    target = legal_targets[t]

        if attacker and target:
            dmg = attacker.attack(target)
            STATE.last_event = f"{attacker.name} 普攻 {target.name} [-{dmg}]"
            if not target.is_alive:
                enemy_team.remove_general_from_formation(target)
                STATE.last_event += f" {target.name} 阵亡"
            if bs._is_game_over():
                STATE.phase = "over"
                STATE.winner = bs._determine_winner()
        else:
            STATE.last_event = "请选择合法的普攻目标"
        return STATE.to_json()

    # GET /api/state
    if path == "/api/state":
        return STATE.to_json()

    # GET /api/generals → 武将展示用（无需启动游戏）
    if path == "/api/generals":
        pool = []
        for data in GENERALS_DATA:
            pool.append({
                "id": data["id"], "name": data["name"],
                "camp": data["camp"], "rarity": data["rarity"],
                "force": data["force"], "intelligence": data["intelligence"],
                "cost": data["cost"],
                "image": data.get("image_file", ""),
                "attributes": data.get("attributes", []),
                "skill": ALL_SKILLS.get(data.get("skill_id","")).name if data.get("skill_id") in ALL_SKILLS else "无",
                "skill_desc": ALL_SKILLS.get(data.get("skill_id","")).description if data.get("skill_id") in ALL_SKILLS else "",
                "bio": GENERALS_BIOGRAPHY.get(data["name"], {}).get("text", ""),
                "years": GENERALS_BIOGRAPHY.get(data["name"], {}).get("years", ""),
                "courtesy": GENERALS_BIOGRAPHY.get(data["name"], {}).get("courtesy", ""),
            })
        return json.dumps({"phase": "gallery", "pool": pool}, ensure_ascii=False)

    return json.dumps({"error": "unknown API"})


# ---- HTTP Server ----
class GameServer(BaseHTTPRequestHandler):
    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/" or p == "":
            p = "/index.html"
        if p.startswith("/api/"):
            self._json(handle_api(p, {}, self))
            return
        # Static files
        fp = os.path.join(WEB_DIR, p.lstrip("/"))
        if not os.path.exists(fp) and p.endswith((".png", ".jpg")):
            # Try generals dir
            fp = os.path.join(GENERALS_IMG_DIR, os.path.basename(p))
        if not os.path.exists(fp) and p.endswith((".png", ".jpg")):
            # Try backgrounds dir
            fp = os.path.join(BG_DIR, os.path.basename(p))
        if os.path.exists(fp) and os.path.isfile(fp):
            ext = os.path.splitext(fp)[1]
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
            self.end_headers()
            with open(fp, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        p = urlparse(self.path).path
        cl = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(cl).decode()) if cl > 0 else {}
        self._json(handle_api(p, body, self))

    def _json(self, data):
        if isinstance(data, str):
            text = data
        else:
            text = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # quiet


def start():
    os.makedirs(WEB_DIR, exist_ok=True)
    port = int(os.environ.get("PORT", "8088"))
    server = HTTPServer(("0.0.0.0", port), GameServer)
    print("=== 三国武将卡牌游戏 Web 版 ===")
    print(f"   打开浏览器访问: http://localhost:{port}")
    print(f"   按 Ctrl+C 停止服务器")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    start()
