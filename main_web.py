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
GENERALS_WEBP_DIR = os.path.join(ASSETS_DIR, "images", "generals_webp")
GENERALS_FULL_DIR = os.path.join(ASSETS_DIR, "images", "generals_full")
BG_DIR = os.path.join(ASSETS_DIR, "images", "backgrounds")
BG_WEBP_DIR = os.path.join(ASSETS_DIR, "images", "backgrounds_webp")

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".js":   "application/javascript; charset=utf-8",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".webp": "image/webp",
    ".ico":  "image/x-icon",
    ".json": "application/json",
}

# 静态资源缓存时间（秒）
CACHE_MAX_AGE = {
    ".png": 604800,   # 7 天
    ".jpg": 604800,
    ".webp": 604800,
    ".css": 3600,     # 1 小时
    ".js": 3600,
    ".html": 0,       # 不缓存 HTML
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
        self.dice_p1 = 0   # 玩家1骰子值
        self.dice_p2 = 0   # 玩家2骰子值
        self.compensation = ""  # 后手补偿说明

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
        if self.dice_p1 or self.dice_p2:
            result["d1"] = self.dice_p1
            result["d2"] = self.dice_p2
            result["compensation"] = self.compensation
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
                "effective_force": g.get_effective_force(),
                "effective_intelligence": g.get_effective_intelligence(),
                "alive": g.is_alive,
                "row": pos[0] if pos else -1, "col": pos[1] if pos else -1,
                "skill": g.active_skill.name if g.active_skill else "",
                "skill_desc": g.active_skill.description if g.active_skill else "",
                "cooldown": g.active_skill_cooldown,
                "image": g.image_file or "",
                "attributes": [a.value for a in (g.attribute or [])],
                "_ambushHidden": g.get_passive_skill("伏兵").is_hidden if g.has_passive_skill("伏兵") else False,
                "_ambushTriggered": g.get_passive_skill("伏兵").triggered if g.has_passive_skill("伏兵") else False,
                "_hasAttacked": g._has_attacked_this_turn,
                "_hasUsedSkill": g._has_used_skill_this_turn,
                "_hasSpeedJudgment": g.has_buff_type("attack_speed_judgment"),
                "_hasSpeedRequired": g.has_debuff_type("attack_speed_required"),
                "_targetType": g.active_skill.target_type.value if (g.active_skill and hasattr(g.active_skill, 'target_type')) else "",
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
        # 始终执行阶段切换
        if STATE.phase == "formation_p1":
            STATE.phase = "formation_p2"
            STATE.last_event = "玩家1布阵完成，轮到玩家2布阵"
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
        elif d2 > d1:
            c.first_player, c.second_player = c.player2, c.player1
        else:
            # 平局则重掷
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
        STATE.dice_p1 = d1
        STATE.dice_p2 = d2
        STATE.compensation = f"{c.second_player.name} 后手，士气上限+2"
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

        # 回合结束：清理当前方过期效果后切换
        bs.current_side.update_effects()
        bs._end_turn_cleanup()
        bs._switch_to_next_player()
        bs.turn_count += 1
        STATE.turn_count = bs.turn_count
        # 新回合方也更新效果（防栅重建等）
        bs.current_side.update_effects()
        current_player = c.player1.name if bs.current_side == c.player1.team else c.player2.name
        STATE.last_event = f"第{STATE.turn_count}回合，轮到{current_player}行动"
        return STATE.to_json()

    # POST /api/battle/skill -> {"general_id": 1}
    if path == "/api/battle/skill" and STATE.battle_system:
        bs = STATE.battle_system
        from src.skills.skill_base import TargetType
        caster = None
        gid = body.get("general_id", None)
        if gid is not None:
            try:
                gid = int(gid)
            except (TypeError, ValueError):
                gid = None
            # 从双方队伍中查找施法者（不只是当前方）
            for team in [bs.team1, bs.team2]:
                caster = next((g for g in team.get_alive_generals()
                              if g.general_id == gid), None)
                if caster:
                    break
        else:
            idx = body.get("general_index", -1)
            alive = bs.current_side.get_alive_generals()
            if 0 <= idx < len(alive):
                caster = alive[idx]

        if caster and caster.can_use_active_skill():
            if not caster.can_use_skill():
                STATE.last_event = f"{caster.name} 本回合已使用过技能"
                return STATE.to_json()
            tt = caster.active_skill.target_type
            # 确定施法者所属队伍（用于士气扣除和目标选择）
            caster_team = (bs.team1 if caster in bs.team1.get_alive_generals()
                          else bs.team2)
            if tt == TargetType.SELF:
                targets = [caster]
            elif tt == TargetType.SINGLE_ALLY:
                # 选己方武力最高者（若无则选自己）
                allies = caster.get_team(bs).get_alive_generals() if hasattr(caster, 'get_team') else bs.current_side.get_alive_generals()
                if not allies:
                    # 尝试从双方确定所属队伍
                    allies = (bs.team1.get_alive_generals() if caster in bs.team1.get_alive_generals()
                              else bs.team2.get_alive_generals())
                targets = [max(allies, key=lambda g: g.get_effective_force())] if allies else [caster]
            elif tt == TargetType.ALL_ALLIES:
                targets = caster_team.get_alive_generals()
            elif tt in (TargetType.SINGLE_ENEMY, TargetType.FRONT_ROW_ENEMY, TargetType.BACK_ROW_ENEMY, TargetType.RANDOM_ENEMY):
                enemy_team = bs.team2 if caster_team == bs.team1 else bs.team1
                enemy = enemy_team.get_alive_generals()
                if tt == TargetType.FRONT_ROW_ENEMY:
                    enemy = enemy_team.get_front_row_generals() if hasattr(enemy_team, 'get_front_row_generals') else enemy
                targets = [enemy[0]] if enemy else []
            elif tt == TargetType.ALL_ENEMIES:
                enemy_team = bs.team2 if caster_team == bs.team1 else bs.team1
                targets = enemy_team.get_alive_generals()
            elif tt == TargetType.AREA_ENEMY:
                enemy_team = bs.team2 if caster_team == bs.team1 else bs.team1
                area_r = body.get("area_row", None)
                area_c = body.get("area_col", None)
                if area_r is not None and area_c is not None:
                    # 前端选择了2x2区域——只取该区域内的存活武将
                    try:
                        area_r = int(area_r); area_c = int(area_c)
                    except (TypeError, ValueError):
                        area_r = area_c = None
                    if area_r is not None:
                        targets = [g for g in enemy_team.get_alive_generals()
                                   if area_r <= g.get_position()[0] <= area_r + 1
                                   and area_c <= g.get_position()[1] <= area_c + 1]
                    else:
                        targets = enemy_team.get_alive_generals()[:2]
                else:
                    # 未选区域——传空列表，技能内部自动选择最佳块
                    targets = []
            else:
                enemy_team = bs.team2 if caster_team == bs.team1 else bs.team1
                targets = enemy_team.get_alive_generals()[:1]
            # 攻速判定猜奇偶（如雷击需要）
            guess = body.get("guess", None)
            result = caster.use_active_skill(targets, bs.battle_context, caster_team, guess=guess)
            STATE.last_event = f"{caster.name} 使用 {caster.active_skill.name}" if result.get("success") else (result.get("message") or "技能失败")
            if result.get("success"):
                detail = result.get("details", [])
                if detail:
                    effects = "; ".join(d.get("effect", "") for d in detail[:3] if d.get("effect"))
                    if effects:
                        STATE.last_event += f"：{effects}"
            if bs._is_game_over():
                STATE.phase = "over"
                STATE.winner = bs._determine_winner()
        else:
            STATE.last_event = "该武将无法使用技能（冷却中、已阵亡或士气不足）"
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
            if not attacker.can_attack():
                STATE.last_event = f"{attacker.name} 本回合已普攻过，不可再次攻击"
                return STATE.to_json()
            target_hp_before = target.current_hp
            guess = body.get("guess", None)  # 攻速判定奇偶猜测
            target_pos_before = (c.player1.team.get_general_position(target) or
                                c.player2.team.get_general_position(target))
            dmg = attacker.attack(target, guess)
            # 检查是否发生了伏兵替位（目标位置变了）
            target_pos_after = (c.player1.team.get_general_position(target) or
                               c.player2.team.get_general_position(target))
            pos_changed = (target_pos_before != target_pos_after)
            if dmg == 0:
                STATE.last_event = f"{attacker.name} 攻击 {target.name}，但被防栅/护盾挡下"
            elif pos_changed:
                STATE.last_event = f"{attacker.name} 攻击触发伏兵替位！{target.name} 受 {dmg} 点伤害"
            else:
                STATE.last_event = f"{attacker.name} 普攻 {target.name} [-{dmg}]"
            if not target.is_alive:
                STATE.last_event += f" {target.name} 阵亡！"
            # 检查魅力反弹是否击杀了攻击者
            if not attacker.is_alive:
                STATE.last_event += f" {attacker.name} 被魅力反噬阵亡！"
            if bs._is_game_over():
                STATE.phase = "over"
                STATE.winner = bs._determine_winner()
        else:
            STATE.last_event = "请选择合法的普攻目标（只能攻击敌方前排）"
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
        # Static files — check multiple directories
        fp = os.path.join(WEB_DIR, p.lstrip("/"))
        # Try WebP versions first for images (smaller)
        img_dirs = [GENERALS_WEBP_DIR, GENERALS_FULL_DIR, GENERALS_IMG_DIR, BG_WEBP_DIR, BG_DIR]
        for d in img_dirs:
            if os.path.exists(fp) and os.path.isfile(fp):
                break
            if p.endswith((".png", ".jpg", ".webp")):
                alt = os.path.join(d, os.path.basename(p).replace(".png", ".webp").replace(".jpg", ".webp"))
                if os.path.exists(alt) and os.path.isfile(alt):
                    fp = alt; break
                alt2 = os.path.join(d, os.path.basename(p))
                if os.path.exists(alt2) and os.path.isfile(alt2):
                    fp = alt2; break
        if os.path.exists(fp) and os.path.isfile(fp):
            ext = os.path.splitext(fp)[1]
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
            # Cache headers
            cache_age = CACHE_MAX_AGE.get(ext, 0)
            if cache_age > 0:
                self.send_header("Cache-Control", f"public, max-age={cache_age}")
            else:
                self.send_header("Cache-Control", "no-cache")
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
