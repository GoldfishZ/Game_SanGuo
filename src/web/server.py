"""
三国武将卡牌游戏 — Web 版服务器
使用 Python 内置 http.server，零外部依赖。
启动后浏览器访问 http://localhost:8089 即可游玩。
"""

import json
import os
import random
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from src.models.game_flow import GameFlowController, Player
from src.models.general import General
from src.models.team import Team
from src.battle.battle_system import BattleSystem
from src.battle.rules_service import BattleRulesService
from src.rl.pve import PVEController
from src.game_data.generals_data import GENERALS_DATA
from src.game_data.generals_bios import GENERALS_BIOGRAPHY
from src.game_data.skills_config import ALL_SKILLS
from src.paths import (
    ASSETS_DIR as PROJECT_ASSETS_DIR,
    BACKGROUNDS_DIR as PROJECT_BACKGROUNDS_DIR,
    BACKGROUNDS_WEBP_DIR as PROJECT_BACKGROUNDS_WEBP_DIR,
    GENERALS_DIR as PROJECT_GENERALS_DIR,
    GENERALS_FULL_DIR as PROJECT_GENERALS_FULL_DIR,
    GENERALS_WEBP_DIR as PROJECT_GENERALS_WEBP_DIR,
    WEB_STATIC_DIR,
)

# ---- Static files serving ----
WEB_DIR = str(WEB_STATIC_DIR)
ASSETS_DIR = str(PROJECT_ASSETS_DIR)
GENERALS_IMG_DIR = str(PROJECT_GENERALS_DIR)
GENERALS_WEBP_DIR = str(PROJECT_GENERALS_WEBP_DIR)
GENERALS_FULL_DIR = str(PROJECT_GENERALS_FULL_DIR)
BG_DIR = str(PROJECT_BACKGROUNDS_DIR)
BG_WEBP_DIR = str(PROJECT_BACKGROUNDS_WEBP_DIR)

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
        self.rules = None
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
        self.mode = "pvp"
        self.pve_controller = None
        self.last_ai_actions = []
        self.ai_subphase = "skill"
        self.ai_action_count = 0
        self.ai_step_lock = threading.Lock()
        # 仅供 Web 展示阵亡卡；不会写回权威阵型或参与目标判定。
        self.display_positions = {}

    def _make_pool(self, chosen_data):
        """Generate one player's draft pool from already selected raw general data."""
        pool = []
        for i, data in enumerate(chosen_data):
            from src.game_data.generals_config import create_general_from_data
            g = create_general_from_data(data)
            g.pool_index = i + 1
            pool.append(g)
        return pool

    def _make_distinct_pools(self, pool_size=16):
        """Split the full roster into two non-overlapping draft pools."""
        from src.game_data.generals_data import GENERALS_DATA
        import random as _rnd
        shuffled = list(GENERALS_DATA)
        _rnd.shuffle(shuffled)
        first = shuffled[:pool_size]
        second = shuffled[pool_size:pool_size * 2]
        return self._make_pool(first), self._make_pool(second)

    def reset(self, mode="pvp"):
        self.mode = mode if mode in ("pvp", "pve") else "pvp"
        self.controller = GameFlowController()
        if self.mode == "pve":
            self.controller.player2.name = "电脑"
        self.pool_p1, self.pool_p2 = self._make_distinct_pools()
        self.phase = "select_p1"
        self.battle_system = None
        self.rules = None
        self.last_ai_actions = []
        self.ai_subphase = "skill"
        self.ai_action_count = 0
        self.last_event = "人机对战已初始化" if self.mode == "pve" else "双人对战已初始化"
        self.turn_count = 0
        self.winner = ""
        self.dice_p1 = 0
        self.dice_p2 = 0
        self.compensation = ""
        self.display_positions = {}

    def ensure_pve_controller(self):
        if self.pve_controller is None:
            self.pve_controller = PVEController(device="cpu")
        return self.pve_controller

    def auto_ai_draft(self):
        ai = self.controller.player2
        choices = self.ensure_pve_controller().choose_draft(
            self.pool_p2, self.controller.player1.selected_generals,
            self.cost_limit,
        )
        if not choices:
            raise RuntimeError("电脑未找到合法选将组合")
        for general in choices:
            ai.add_general_to_team(general)
            if hasattr(general, "pool_index"):
                delattr(general, "pool_index")

    def auto_ai_formation(self):
        ai = self.controller.player2
        positions = self.ensure_pve_controller().choose_formation(
            ai.selected_generals, self.controller.player1,
        )
        if len(positions) != len(ai.selected_generals):
            raise RuntimeError("电脑未生成完整布阵")
        for position in positions:
            general = next(
                general for general in ai.selected_generals
                if general.general_id == int(position["general_id"])
            )
            if not ai.team.position_general(
                general, int(position["row"]), int(position["col"]),
            ):
                raise RuntimeError("电脑生成了冲突阵位")
        ai.team.complete_formation_setup()

    def is_ai_turn(self):
        return bool(
            self.mode == "pve" and self.phase == "battle" and self.battle_system
            and self.battle_system.current_side is self.controller.player2.team
        )

    def begin_ai_turn(self):
        if self.is_ai_turn():
            self.ai_subphase = "skill"
            self.ai_action_count = 0
            self.last_ai_actions = []

    def step_ai_action(self):
        with self.ai_step_lock:
            if not self.is_ai_turn():
                return {"kind": "idle", "success": False, "done": self.phase == "over"}
            if self.ai_action_count >= 64:
                raise RuntimeError("电脑单回合动作超过安全上限")
            trace = self.ensure_pve_controller().step_battle_turn(
                self, self.controller.player2.team, self.controller.player1.team,
                self.ai_subphase,
            )
            self.ai_action_count += 1
            self.ai_subphase = trace.get("next_subphase", self.ai_subphase)
            self.last_ai_actions.append(trace)
            return trace

    def finish_battle(self):
        """结束 Web 战斗，并把引擎队名统一转换为前端玩家名。"""
        if not self.battle_system or not self.controller:
            return
        outcome = self.rules.outcome() if self.rules else BattleRulesService(self.battle_system).outcome()
        self.phase = "over"
        if outcome.timeout:
            self.winner = "平局"
            self.last_event = "战斗结束：达到回合上限，本局平局"
            return
        winner_team = outcome.winner
        self.winner = winner_team or "平局"
        for player in (self.controller.player1, self.controller.player2):
            if player.team.team_name == winner_team:
                self.winner = player.name
                break
        self.last_event = f"战斗结束，{self.winner} 获胜"

    def ensure_rules(self):
        """兼容测试/旧调用方直接注入 BattleSystem，同时维持单一规则入口。"""
        if self.battle_system is not None and (
            self.rules is None or self.rules.battle_system is not self.battle_system
        ):
            self.rules = BattleRulesService(self.battle_system)
        return self.rules

    def clear_combat_events(self):
        """清空双方武将的表现事件，确保一次接口只返回本次结算。"""
        if not self.controller:
            return
        for player in (self.controller.player1, self.controller.player2):
            for general in player.selected_generals:
                general.drain_combat_events()

    def drain_combat_events(self):
        """按队伍及阵位顺序收集本次结算产生的表现事件。"""
        if not self.controller:
            return []
        events = []
        for player_key, player in (("p1", self.controller.player1),
                                   ("p2", self.controller.player2)):
            for general in player.selected_generals:
                for event in general.drain_combat_events():
                    event.setdefault("team", player_key)
                    events.append(event)
        return events

    @staticmethod
    def _effect_json(effect):
        """把 buff/debuff 转为安全 DTO，过滤其中可能存在的 General 引用。"""
        result = {
            "type": effect.get("type", ""),
            "duration": effect.get("duration", 0),
        }
        value = effect.get("value", 0)
        if isinstance(value, (str, int, float, bool)) or value is None:
            result["value"] = value
        elif hasattr(value, "general_id"):
            result["value"] = getattr(value, "name", "")
            result["target_id"] = value.general_id
        else:
            result["value"] = str(value)
        return result

    def to_json(self):
        c = self.controller
        if not c:
            return json.dumps({"phase": "menu"})
        result = {"phase": self.phase, "event": self.last_event,
                  "turn": self.turn_count, "winner": self.winner,
                  "cost_limit": self.cost_limit, "mode": self.mode,
                  "human_team": "p1", "ai_team": "p2" if self.mode == "pve" else None}
        if self.mode == "pve":
            ai = self.ensure_pve_controller()
            result["ai_ready"] = ai.available
            result["ai_errors"] = list(ai.load_errors)
            result["ai_actions"] = list(self.last_ai_actions)
            result["ai_thinking"] = self.is_ai_turn()
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
            if pos is not None:
                self.display_positions[g.general_id] = pos
            elif not g.is_alive:
                pos = self.display_positions.get(g.general_id)
            forced_target = g.get_forced_attack_target()
            general_json = {
                "name": g.name, "id": g.general_id,
                "hp": g.current_hp, "maxHp": g.max_hp,
                "force": g.force, "intelligence": g.intelligence,
                "cost": g.cost, "camp": g.camp.value, "rarity": g.rarity.name,
                "effective_force": g.get_effective_force(),
                "effective_intelligence": g.get_effective_intelligence(),
                "alive": g.is_alive,
                "row": pos[0] if pos else -1, "col": pos[1] if pos else -1,
                "skill": g.active_skill.name if g.active_skill else "",
                "skill_id": g.active_skill.skill_id if g.active_skill else "",
                "skill_desc": g.active_skill.description if g.active_skill else "",
                "cooldown": g.active_skill_cooldown,
                "image": g.image_file or "",
                "attributes": [a.value for a in (g.attribute or [])],
                "buffs": [self._effect_json(buff) for buff in g.buffs],
                "debuffs": [self._effect_json(debuff) for debuff in g.debuffs],
                "_ambushHidden": g.get_passive_skill("伏兵").is_hidden if g.has_passive_skill("伏兵") else False,
                "_ambushTriggered": g.get_passive_skill("伏兵").triggered if g.has_passive_skill("伏兵") else False,
                "_fenceActive": g.get_passive_skill("防栅").is_active if g.has_passive_skill("防栅") else False,
                "_fenceBroken": not g.get_passive_skill("防栅").is_active if g.has_passive_skill("防栅") else False,
                "_reviveUsed": g.get_passive_skill("复活").has_revived if g.has_passive_skill("复活") else False,
                "_hasAttacked": g._has_attacked_this_turn,
                "_hasExtraAttack": g._extra_attack_available,
                "_hasUsedSkill": g._has_used_skill_this_turn,
                "_hasSpeedJudgment": g.has_buff_type("attack_speed_judgment"),
                "_hasSpeedRequired": g.has_debuff_type("attack_speed_required"),
                "_braveryReady": bool(
                    g.is_alive and g.has_passive_skill("勇猛")
                    and g.current_hp < g.max_hp / 2
                ),
                "_braveryJudgment": (
                    dict(g.get_passive_skill("勇猛").last_judgment)
                    if g.has_passive_skill("勇猛")
                    and g.get_passive_skill("勇猛").last_judgment else None
                ),
                "_charismaReady": bool(g.is_alive and g.has_passive_skill("魅力")),
                "_charismaJudgment": (
                    dict(g.get_passive_skill("魅力").last_judgment)
                    if g.has_passive_skill("魅力")
                    and g.get_passive_skill("魅力").last_judgment else None
                ),
                "_frontOnlyAttack": g.has_buff_type("front_only_attack"),
                "_forcedTargetId": forced_target.general_id if forced_target else None,
                "_targetType": g.active_skill.target_type.name if (g.active_skill and hasattr(g.active_skill, 'target_type')) else "",
                "skill_cost": g.active_skill.morale_cost if g.active_skill else 0,
            }
            ambush = g.get_passive_skill("伏兵") if g.has_passive_skill("伏兵") else None
            concealed = bool(
                self.mode == "pve" and p is self.controller.player2
                and g.is_alive and ambush and ambush.is_hidden
            )
            if concealed:
                # Keep only board occupancy and rule-state fields. Identity, art,
                # stats, traits and skill data stay server-side until reveal.
                general_json.update({
                    "name": "未知伏兵", "hp": 0, "maxHp": 0,
                    "force": 0, "intelligence": 0, "cost": 0,
                    "camp": "", "rarity": "",
                    "effective_force": 0, "effective_intelligence": 0,
                    "skill": "", "skill_id": "", "skill_desc": "",
                    "_targetType": "", "skill_cost": 0,
                    "image": "", "attributes": [], "buffs": [], "debuffs": [],
                    "_ambushConcealed": True,
                })
            else:
                general_json["_ambushConcealed"] = False
            gens.append(general_json)
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
        STATE.reset(body.get("mode", "pvp"))
        return STATE.to_json()

    # POST /api/select → {"general_ids": [1,2,...]}
    if path == "/api/select":
        if c is None or STATE.phase not in ("select_p1", "select_p2"):
            STATE.last_event = "当前阶段不能选将"
            return STATE.to_json()
        ids = body.get("general_ids", [])
        selected_ids = set()
        for gid in ids:
            try:
                selected_ids.add(int(gid))
            except (TypeError, ValueError):
                continue
        pool = STATE.pool_p1 if STATE.phase == "select_p1" else STATE.pool_p2
        target_player = c.player1 if STATE.phase == "select_p1" else c.player2
        selected = [g for g in pool if g.general_id in selected_ids and hasattr(g, "pool_index")]
        selected_cost = sum(g.cost for g in selected)
        if not selected:
            STATE.last_event = "请至少选择一名武将"
            return STATE.to_json()
        if selected_cost > STATE.cost_limit:
            STATE.last_event = f"选将费用超过上限 {STATE.cost_limit}"
            return STATE.to_json()
        for g in selected:
            target_player.add_general_to_team(g)
            delattr(g, "pool_index")
        if STATE.phase == "select_p1":
            if STATE.mode == "pve":
                try:
                    STATE.auto_ai_draft()
                except Exception as exc:
                    STATE.last_event = f"电脑选将失败：{exc}"
                    return STATE.to_json()
                STATE.phase = "formation_p1"
                STATE.last_event = "电脑已完成选将，请为玩家1布阵"
            else:
                STATE.phase = "select_p2"
                STATE.last_event = "玩家1已选择，轮到玩家2"
        else:
            STATE.phase = "formation_p1"
            STATE.last_event = "选将完成，进入布阵"
        return STATE.to_json()

    # POST /api/place → {"positions": {"row": 0, "col": 0, "general_id": 1}, ...}
    if path == "/api/place":
        if c is None or STATE.phase not in ("formation_p1", "formation_p2"):
            STATE.last_event = "当前阶段不能布阵"
            return STATE.to_json()
        positions = body.get("positions", [])
        target_player = c.player1 if STATE.phase == "formation_p1" else c.player2
        expected_ids = {g.general_id for g in target_player.selected_generals}
        normalized = []
        try:
            for position in positions:
                normalized.append((
                    int(position["general_id"]),
                    int(position["row"]),
                    int(position["col"]),
                ))
        except (KeyError, TypeError, ValueError):
            normalized = []
        placed_ids = {general_id for general_id, _, _ in normalized}
        cells = {(row, col) for _, row, col in normalized}
        valid = (
            len(normalized) == len(expected_ids)
            and placed_ids == expected_ids
            and len(cells) == len(normalized)
            and all(0 <= row < 3 and 0 <= col < 4 for _, row, col in normalized)
        )
        if not valid:
            STATE.last_event = "请把全部武将放入互不重叠的合法阵位"
            return STATE.to_json()
        for general_id, row, col in normalized:
            general = next(g for g in target_player.selected_generals
                           if g.general_id == general_id)
            if not target_player.team.position_general(general, row, col):
                STATE.last_event = "阵位冲突，布阵未完成"
                return STATE.to_json()

        target_player.team.complete_formation_setup()
        if STATE.phase == "formation_p1":
            if STATE.mode == "pve":
                try:
                    STATE.auto_ai_formation()
                except Exception as exc:
                    STATE.last_event = f"电脑布阵失败：{exc}"
                    return STATE.to_json()
                STATE.phase = "dice"
                STATE.last_event = "双方布阵完成，准备掷骰"
            else:
                STATE.phase = "formation_p2"
                STATE.last_event = "玩家1布阵完成，轮到玩家2布阵"
        else:
            STATE.phase = "dice"
            STATE.last_event = "布阵完成，准备掷骰"
        return STATE.to_json()

    # POST /api/dice → 掷骰子
    if path == "/api/dice":
        if c is None or STATE.phase != "dice":
            STATE.last_event = "双方完成布阵后才能掷骰"
            return STATE.to_json()
        d1 = d2 = 0
        while d1 == d2:
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
        STATE.rules = BattleRulesService(STATE.battle_system)
        STATE.battle_system.turn_count = 1
        STATE.turn_count = 1
        STATE.battle_system.current_side.update_effects()
        STATE.clear_combat_events()
        STATE.begin_ai_turn()
        return STATE.to_json()

    # POST /api/pve/step -> execute exactly one visible computer sub-action.
    if path == "/api/pve/step":
        if c is None or STATE.mode != "pve" or STATE.phase != "battle":
            STATE.last_event = "当前没有可执行的电脑回合"
            return STATE.to_json()
        if not STATE.is_ai_turn():
            STATE.last_event = "当前轮到玩家行动"
            return STATE.to_json()
        try:
            trace = STATE.step_ai_action()
        except Exception as exc:
            STATE.last_event = f"电脑行动失败：{exc}"
            response = STATE.to_json()
            response["ai_error"] = str(exc)
            return response
        response = STATE.to_json()
        response["ai_action"] = trace
        return response

    # POST /api/battle/next or /api/battle/skip -> end current player's turn
    if path in ("/api/battle/next", "/api/battle/skip") and STATE.battle_system and STATE.phase == "battle":
        bs = STATE.battle_system
        if STATE.is_ai_turn():
            STATE.last_event = "电脑正在行动，请等待"
            return STATE.to_json()
        if bs._is_game_over():
            STATE.finish_battle()
            return STATE.to_json()

        # 权威规则：达到回合上限一律平局。
        if bs.turn_count >= bs.max_turns:
            STATE.finish_battle()
            return STATE.to_json()

        # 回合结束后切换；效果只在新行动方回合开始时结算一次。
        STATE.clear_combat_events()
        turn_result = STATE.ensure_rules().end_turn()
        morale_event = turn_result["morale_event"]
        ending_team = "p1" if turn_result["ending_team"] == c.player1.team.team_name else "p2"
        morale_event["team"] = ending_team
        STATE.turn_count = bs.turn_count
        turn_events = [morale_event] + STATE.drain_combat_events()
        current_player = c.player1.name if bs.current_side == c.player1.team else c.player2.name
        STATE.last_event = f"第{STATE.turn_count}回合，轮到{current_player}行动"
        STATE.begin_ai_turn()
        response = STATE.to_json()
        response["turn_events"] = turn_events
        return response

    # POST /api/battle/skill -> {"general_id": 1}
    if path == "/api/battle/skill" and STATE.battle_system and STATE.phase == "battle":
        if STATE.is_ai_turn():
            STATE.last_event = "电脑正在行动，请等待"
            return STATE.to_json()
        bs = STATE.battle_system
        from src.skills.skill_base import TargetType
        caster = None
        skill_result = None
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
            if not caster.can_use_skill():
                STATE.last_event = f"{caster.name} 本回合已使用过技能"
                return STATE.to_json()
            tt = caster.active_skill.target_type
            # 确定施法者所属队伍（用于士气扣除和目标选择）
            caster_team = (bs.team1 if caster in bs.team1.get_alive_generals()
                          else bs.team2)
            skill_options = {}
            try:
                if body.get("area_row") is not None:
                    skill_options["row"] = int(body["area_row"])
                if body.get("area_col") is not None:
                    skill_options["col"] = int(body["area_col"])
            except (TypeError, ValueError):
                skill_options = {}
            if body.get("area_orientation") in ("horizontal", "vertical"):
                skill_options["orientation"] = body["area_orientation"]
            if body.get("skill_mode"):
                skill_options["mode"] = body["skill_mode"]
            if body.get("skill_timing"):
                skill_options["timing"] = body["skill_timing"]
            try:
                requested_target_id = (int(body["target_id"])
                                       if body.get("target_id") is not None else None)
            except (TypeError, ValueError):
                requested_target_id = None
            if tt == TargetType.SELF:
                # 石兵八阵虽标为 SELF，但实际需要玩家指定敌方 2x2 区域。
                targets = ([skill_options] if
                           caster.active_skill.skill_id == "stone_sentinel_maze"
                           and skill_options else [caster])
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
            elif tt == TargetType.AREA_ALLY:
                targets = [skill_options] if skill_options else [caster]
            elif tt in (TargetType.SINGLE_ENEMY, TargetType.FRONT_ROW_ENEMY, TargetType.BACK_ROW_ENEMY, TargetType.RANDOM_ENEMY):
                enemy_team = bs.team2 if caster_team == bs.team1 else bs.team1
                enemy = enemy_team.get_alive_generals()
                if tt == TargetType.FRONT_ROW_ENEMY:
                    enemy = enemy_team.get_front_row_generals() if hasattr(enemy_team, 'get_front_row_generals') else enemy
                elif tt == TargetType.BACK_ROW_ENEMY:
                    front = enemy_team.get_front_row_generals() if hasattr(enemy_team, 'get_front_row_generals') else []
                    enemy = [general for general in enemy if general not in front]
                requested_target = next(
                    (general for general in enemy if general.general_id == requested_target_id),
                    None,
                )
                # RANDOM_ENEMY 保留技能内部的随机语义；其余单体技能尊重玩家点选。
                targets = ([requested_target] if requested_target is not None
                           and tt != TargetType.RANDOM_ENEMY else enemy[:1])
            elif tt == TargetType.ALL_ENEMIES:
                enemy_team = bs.team2 if caster_team == bs.team1 else bs.team1
                targets = enemy_team.get_alive_generals()
            elif tt == TargetType.AREA_ENEMY:
                enemy_team = bs.team2 if caster_team == bs.team1 else bs.team1
                if caster.active_skill.skill_id == "meteor_rite":
                    # 新的 4×3 视觉布局中，logical row 对应一整条视觉竖列。
                    # 用选项字典传递给技能，避免被通用 2×2 区域逻辑改写。
                    try:
                        skill_row = int(body.get("skill_row"))
                    except (TypeError, ValueError):
                        skill_row = None
                    targets = [{"row": skill_row}] if skill_row in range(3) else []
                elif skill_options:
                    # 所有可选矩形范围统一传选区起点，由各技能按自身尺寸结算。
                    targets = [skill_options]
                else:
                    # CLI/旧客户端未选区域时保留技能内部的自动选择兜底。
                    targets = []
            else:
                enemy_team = bs.team2 if caster_team == bs.team1 else bs.team1
                targets = enemy_team.get_alive_generals()[:1]
            # 攻速判定猜奇偶（如雷击需要）
            guess = body.get("guess", None)
            STATE.clear_combat_events()
            skill_result = STATE.ensure_rules().skill_targets(caster, targets, guess=guess)
            STATE.last_event = f"{caster.name} 使用 {caster.active_skill.name}" if skill_result.get("success") else (skill_result.get("message") or "技能失败")
            if skill_result.get("success"):
                detail = skill_result.get("details", [])
                if detail:
                    effects = "; ".join(d.get("effect", "") for d in detail[:3] if d.get("effect"))
                    if effects:
                        STATE.last_event += f"：{effects}"
            if bs._is_game_over():
                STATE.finish_battle()
        else:
            STATE.last_event = "该武将无法使用技能（冷却中、已阵亡或士气不足）"
        response = STATE.to_json()
        if skill_result is not None:
            response["skill_result"] = skill_result
            response["skill_id"] = caster.active_skill.skill_id
            response["caster_id"] = caster.general_id
            response["combat_events"] = STATE.drain_combat_events()
        return response

    # POST /api/battle/attack -> {"attacker_id": 1, "target_id": 2} or legacy indexes
    if path == "/api/battle/attack" and STATE.battle_system and STATE.phase == "battle":
        if STATE.is_ai_turn():
            STATE.last_event = "电脑正在行动，请等待"
            return STATE.to_json()
        bs = STATE.battle_system
        attackers = bs.current_side.get_alive_generals()
        enemy_team = bs._get_enemy_team()
        attacker = None
        target = None
        attack_result = None
        speed_judgment = None

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
            bravery_guess = body.get("bravery_guess", None)
            charisma_guess = body.get("charisma_guess", None)
            speed_mode = None
            if attacker.has_debuff_type("attack_speed_required"):
                speed_mode = "attack_required"
            elif attacker.has_buff_type("attack_speed_judgment"):
                speed_mode = "bonus_attack"
            if speed_mode:
                # 避免读取到该武将上一回合遗留的判定结果。
                attacker.last_attack_speed_judgment = None
            target_pos_before = (c.player1.team.get_general_position(target) or
                                c.player2.team.get_general_position(target))
            attacker_pos_before = (c.player1.team.get_general_position(attacker) or
                                   c.player2.team.get_general_position(attacker))
            if target_pos_before is not None:
                STATE.display_positions[target.general_id] = target_pos_before
            if attacker_pos_before is not None:
                STATE.display_positions[attacker.general_id] = attacker_pos_before
            STATE.clear_combat_events()
            attack_result = STATE.ensure_rules().attack(
                attacker, target, guess=guess,
                bravery_guess=bravery_guess, charisma_guess=charisma_guess,
            )
            dmg = attack_result.get("damage", 0)
            if speed_mode and attacker.last_attack_speed_judgment:
                speed_judgment = dict(attacker.last_attack_speed_judgment)
                speed_judgment["mode"] = speed_mode
                if speed_mode == "attack_required":
                    speed_judgment["message"] = (
                        "判定成功，普攻正常发动"
                        if speed_judgment["success"]
                        else "判定失败，本次普攻被取消"
                    )
                else:
                    speed_judgment["message"] = (
                        "判定成功，获得追加普攻"
                        if speed_judgment["success"]
                        else "判定失败，本次没有追加普攻"
                    )
            attack_performed = not (
                speed_mode == "attack_required"
                and speed_judgment
                and not speed_judgment["success"]
            )
            attack_result.update({"events": STATE.drain_combat_events()})
            # 保留位置快照，便于未来阵型类普攻效果给出准确提示。
            target_pos_after = (c.player1.team.get_general_position(target) or
                               c.player2.team.get_general_position(target))
            pos_changed = (target_pos_before != target_pos_after)
            if not attack_performed:
                STATE.last_event = f"{attacker.name} 攻速判定失败，未能对 {target.name} 发动普攻"
            elif dmg == 0:
                STATE.last_event = f"{attacker.name} 攻击 {target.name}，但被防栅/护盾挡下"
            elif pos_changed:
                STATE.last_event = f"{attacker.name} 攻击触发阵位变化！{target.name} 受 {dmg} 点伤害"
            else:
                STATE.last_event = f"{attacker.name} 普攻 {target.name} [-{dmg}]"
            if not target.is_alive:
                STATE.last_event += f" {target.name} 阵亡！"
            # 检查魅力反弹是否击杀了攻击者
            if not attacker.is_alive:
                STATE.last_event += f" {attacker.name} 被魅力反噬阵亡！"
            if speed_judgment:
                guess_label = "奇" if speed_judgment["guess"] == "odd" else "偶"
                parity_label = "奇" if speed_judgment["parity"] == "odd" else "偶"
                STATE.last_event += (
                    f" 攻速判定：选择{guess_label}，掷出{speed_judgment['dice']}点"
                    f"（{parity_label}），{'成功' if speed_judgment['success'] else '失败'}。"
                )
                if speed_mode == "bonus_attack" and speed_judgment["success"]:
                    STATE.last_event += " 获得一次可重新选择目标的追加普攻。"
            if bs._is_game_over():
                STATE.finish_battle()
        else:
            STATE.last_event = "请选择合法的普攻目标（只能攻击敌方前排）"
        response = STATE.to_json()
        if attack_result is not None:
            response["attack_result"] = attack_result
        if speed_judgment is not None:
            response["speed_judgment"] = speed_judgment
        return response

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
    protocol_version = "HTTP/1.1"

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
            with open(fp, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
            self.send_header("Content-Length", str(len(content)))
            # Cache headers
            cache_age = CACHE_MAX_AGE.get(ext, 0)
            if cache_age > 0:
                self.send_header("Cache-Control", f"public, max-age={cache_age}")
            else:
                self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

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
        encoded = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # quiet


def start():
    os.makedirs(WEB_DIR, exist_ok=True)
    port = int(os.environ.get("PORT", "8090"))
    server = ThreadingHTTPServer(("0.0.0.0", port), GameServer)
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
