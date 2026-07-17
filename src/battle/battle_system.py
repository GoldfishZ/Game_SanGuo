"""
纯战斗系统引擎
管理回合制战斗逻辑，所有 I/O 通过 BattleCallbacks 抽象
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from src.models.general import General
from src.models.team import Team
from src.skills.skill_base import TargetType


# ==================== 数据结构 ====================

@dataclass
class BattleEvent:
    """战斗事件数据"""
    event_type: str            # "skill", "attack", "death", "turn_start", "battle_end"
    source_name: str = ""
    target_name: str = ""
    damage: int = 0
    source_hp: int = 0
    target_hp: int = 0
    source_max_hp: int = 0
    target_max_hp: int = 0
    skill_name: str = ""
    details: list = field(default_factory=list)
    turn_count: int = 0
    current_player_name: str = ""


@dataclass
class BattleStatusData:
    """完整战斗状态快照"""
    turn_count: int
    current_player_name: str
    team1_name: str
    team1_morale: int
    team1_max_morale: int
    team1_generals: list           # list of (name, current_hp, max_hp, is_alive, position, cooldown)
    team2_name: str
    team2_morale: int
    team2_max_morale: int
    team2_generals: list


# ==================== 回调抽象 ====================

class BattleCallbacks(ABC):
    """战斗UI交互回调抽象基类"""

    @abstractmethod
    def display_battle_status(self, data: BattleStatusData) -> None:
        """显示当前战斗状态（替换 _display_battle_status 的 print）"""
        ...

    @abstractmethod
    def on_turn_start(self, turn_count: int, player_name: str) -> None:
        """回合开始时调用"""
        ...

    @abstractmethod
    def on_skill_used(self, event: BattleEvent) -> None:
        """技能使用成功后调用"""
        ...

    @abstractmethod
    def on_skill_failed(self, skill_name: str, reason: str) -> None:
        """技能使用失败时调用"""
        ...

    @abstractmethod
    def on_attack(self, event: BattleEvent) -> None:
        """攻击结算后调用"""
        ...

    @abstractmethod
    def on_general_defeated(self, event: BattleEvent) -> None:
        """武将阵亡时调用"""
        ...

    @abstractmethod
    def on_battle_end(self, winner_name: str, turn_count: int) -> None:
        """战斗结束时调用"""
        ...

    @abstractmethod
    def request_skill_use(self, available_generals: list, player_name: str) -> int:
        """
        请求玩家选择使用技能的武将
        返回: 武将索引（0-based），或 -1 跳过
        available_generals: [(index, name, skill_name, cooldown, can_use), ...]
        """
        ...

    @abstractmethod
    def request_skill_target(self, caster_name: str, skill_name: str, possible_targets: list) -> int:
        """
        请求选择技能目标
        返回: 目标索引（0-based），或 -1 取消
        possible_targets: [(index, name, current_hp, max_hp), ...]
        """
        ...

    @abstractmethod
    def request_attack_action(self, attackers: list, targets: list, player_name: str) -> Tuple[int, int]:
        """
        请求选择攻击者和目标
        返回: (attacker_index, target_index) 或 (-1, -1) 跳过
        attackers: [(index, name, current_hp, max_hp, position), ...]
        targets: [(index, name, current_hp, max_hp, position), ...]
        """
        ...


# ==================== 战斗上下文 ====================

class BattleContext:
    """战斗上下文，为技能提供队伍信息"""

    def __init__(self, team1: Team, team2: Team):
        self.team1 = team1
        self.team2 = team2

    def get_team_for_general(self, general: General) -> Optional[Team]:
        """根据武将获取所属队伍"""
        if general in self.team1.generals:
            return self.team1
        elif general in self.team2.generals:
            return self.team2
        return None


# ==================== 战斗引擎 ====================

class BattleSystem:
    """纯战斗逻辑引擎，所有 I/O 通过 callbacks"""

    def __init__(self, team1: Team, team2: Team, callbacks: BattleCallbacks,
                 first_player_team_name: str, max_turns: int = 200):
        """
        初始化战斗系统

        Args:
            team1: 队伍1
            team2: 队伍2
            callbacks: UI 回调接口
            first_player_team_name: 先手玩家的队伍名称
        """
        self.team1 = team1
        self.team2 = team2
        self.callbacks = callbacks
        self.turn_count = 0
        self.max_turns = max_turns
        self.battle_context = BattleContext(team1, team2)

        # 根据队伍名确定当前操作方
        if first_player_team_name == team1.team_name:
            self.current_side = team1
        else:
            self.current_side = team2

    # ---- 公共接口 ----

    def run(self) -> str:
        """运行完整战斗循环，返回胜利者的队伍名称"""
        while not self._is_game_over() and self.turn_count < self.max_turns:
            self._execute_turn()
        winner = self._determine_winner()
        self.callbacks.on_battle_end(winner, self.turn_count)
        return winner

    # ---- 回合编排 ----

    def _execute_turn(self):
        """执行一个完整的回合"""
        self.turn_count += 1
        player_name = self._get_current_player_name()
        self.callbacks.on_turn_start(self.turn_count, player_name)

        # 更新武将效果（被动技能冷却、buff/debuff）
        self.current_side.update_effects()

        # 显示战斗状态
        self._display_status_callback()

        # 技能使用阶段
        self._execute_skill_phase()

        # 普攻阶段
        if not self._is_game_over():
            self._execute_attack_phase()

        self._end_turn_cleanup()
        if self._is_game_over():
            return

        # 切换下一方
        self._switch_to_next_player()

    def _display_status_callback(self):
        """构建 BattleStatusData 并发送给回调"""
        data = BattleStatusData(
            turn_count=self.turn_count,
            current_player_name=self._get_current_player_name(),
            team1_name=self.team1.team_name,
            team1_morale=self.team1.current_morale,
            team1_max_morale=self.team1.max_morale,
            team1_generals=self._build_general_list(self.team1),
            team2_name=self.team2.team_name,
            team2_morale=self.team2.current_morale,
            team2_max_morale=self.team2.max_morale,
            team2_generals=self._build_general_list(self.team2),
        )
        self.callbacks.display_battle_status(data)

    def _build_general_list(self, team: Team) -> list:
        """构建武将状态列表"""
        result = []
        for general in team.generals:
            pos = team.get_general_position(general)
            pos_str = f"({pos[0]},{pos[1]})" if pos else "-"
            result.append({
                "name": general.name,
                "current_hp": general.current_hp,
                "max_hp": general.max_hp,
                "is_alive": general.is_alive,
                "position": pos_str,
                "active_skill_name": general.active_skill.name if general.active_skill else "无",
                "active_skill_cooldown": general.active_skill_cooldown,
                "force": general.force,
                "intelligence": general.intelligence,
                "image_file": general.image_file,
                "camp": general.camp.value if hasattr(general.camp, 'value') else str(general.camp),
            })
        return result

    # ---- 技能阶段 ----

    def _execute_skill_phase(self):
        """执行技能使用阶段"""
        available_generals = self.current_side.get_alive_generals()
        if not available_generals:
            return

        # 构建选择列表
        generals_data = []
        for i, general in enumerate(available_generals):
            skill_name = general.active_skill.name if general.active_skill else "无技能"
            can_use = general.can_use_active_skill() and \
                      self.current_side.current_morale >= (general.active_skill.morale_cost if general.active_skill else 0)
            generals_data.append((
                i, general.name, skill_name,
                general.active_skill_cooldown, can_use
            ))

        idx = self.callbacks.request_skill_use(
            generals_data, self._get_current_player_name()
        )

        if idx < 0 or idx >= len(available_generals):
            return

        caster = available_generals[idx]
        if caster.can_use_active_skill():
            self._use_skill(caster)

    def _use_skill(self, caster: General):
        """使用武将的主动技能"""
        if not caster.active_skill:
            self.callbacks.on_skill_failed("", f"{caster.name} 没有可用技能")
            return

        skill_name = caster.active_skill.name
        targets = self._select_skill_targets(caster)

        if targets is None or len(targets) == 0:
            return

        team = self.current_side
        result = caster.use_active_skill(targets, self.battle_context, team)

        if result.get("success"):
            details = [str(d) for d in result.get("details", [])]
            event = BattleEvent(
                event_type="skill",
                source_name=caster.name,
                skill_name=skill_name,
                details=details,
                turn_count=self.turn_count,
                current_player_name=self._get_current_player_name(),
            )
            self.callbacks.on_skill_used(event)
        else:
            self.callbacks.on_skill_failed(
                skill_name, result.get("message", "未知错误")
            )

    def _select_skill_targets(self, caster: General) -> List[General]:
        """根据技能类型选择目标"""
        target_type = caster.active_skill.target_type

        if target_type == TargetType.SELF:
            return [caster]

        elif target_type == TargetType.ALL_ALLIES:
            return self.current_side.get_alive_generals()

        elif target_type == TargetType.SINGLE_ENEMY:
            enemy_team = self._get_enemy_team()
            enemy_generals = enemy_team.get_alive_generals()

            if not enemy_generals:
                return []

            targets_data = [
                (i, g.name, g.current_hp, g.max_hp)
                for i, g in enumerate(enemy_generals)
            ]

            idx = self.callbacks.request_skill_target(
                caster.name, caster.active_skill.name, targets_data
            )

            if 0 <= idx < len(enemy_generals):
                return [enemy_generals[idx]]

        return []

    # ---- 攻击阶段 ----

    def _execute_attack_phase(self):
        """执行普攻阶段"""
        attackers = self.current_side.get_alive_generals()
        enemy_team = self._get_enemy_team()
        targets = enemy_team.get_attackable_targets()

        if not attackers or not targets:
            return

        attackers_data = []
        for i, g in enumerate(attackers):
            pos = self.current_side.get_general_position(g)
            pos_str = f"({pos[0]},{pos[1]})" if pos else "-"
            attackers_data.append((i, g.name, g.current_hp, g.max_hp, pos_str))

        targets_data = []
        for i, g in enumerate(targets):
            pos = enemy_team.get_general_position(g)
            pos_str = f"({pos[0]},{pos[1]})" if pos else "-"
            targets_data.append((i, g.name, g.current_hp, g.max_hp, pos_str))

        a_idx, t_idx = self.callbacks.request_attack_action(
            attackers_data, targets_data, self._get_current_player_name()
        )

        if a_idx < 0 or t_idx < 0 or a_idx >= len(attackers) or t_idx >= len(targets):
            return

        attacker = attackers[a_idx]
        legal_targets = self._get_attack_targets_for_attacker(attacker)
        if not legal_targets:
            return

        target = targets[t_idx]
        if target not in legal_targets:
            target = legal_targets[0]

        # 执行攻击
        damage = attacker.attack(target)

        event = BattleEvent(
            event_type="attack",
            source_name=attacker.name,
            target_name=target.name,
            damage=damage,
            target_hp=target.current_hp,
            target_max_hp=target.max_hp,
            turn_count=self.turn_count,
            current_player_name=self._get_current_player_name(),
        )
        self.callbacks.on_attack(event)

        # 处理阵亡
        if not target.is_alive:
            enemy_team.remove_general_from_formation(target)
            death_event = BattleEvent(
                event_type="death",
                source_name=attacker.name,
                target_name=target.name,
                target_hp=0,
                target_max_hp=target.max_hp,
                turn_count=self.turn_count,
                current_player_name=self._get_current_player_name(),
            )
            self.callbacks.on_general_defeated(death_event)

    # ---- 辅助方法 ----

    def _get_current_player_name(self) -> str:
        """获取当前操作方的玩家名"""
        # team_name 格式为 "{player_name}的队伍"
        name = self.current_side.team_name
        if "的队伍" in name:
            return name.split("的队伍")[0]
        return name

    def _get_enemy_team(self) -> Team:
        """获取敌方队伍"""
        return self.team2 if self.current_side == self.team1 else self.team1

    def _get_attack_targets_for_attacker(self, attacker: General) -> List[General]:
        """根据攻击者状态获取合法普攻目标。"""
        enemy_team = self._get_enemy_team()
        if not attacker.has_buff_type("front_only_attack"):
            return enemy_team.get_attackable_targets()

        attacker_pos = self.current_side.get_general_position(attacker)
        if attacker_pos is None:
            return enemy_team.get_attackable_targets()

        target = enemy_team.get_front_target_in_column(attacker_pos[1])
        return [target] if target else []

    def _switch_to_next_player(self):
        """切换到下一个玩家（A-B-A-B 交替）"""
        self.current_side = self._get_enemy_team()

    def _end_turn_cleanup(self):
        """回合结束清理临时效果，并为结束行动的一方恢复 2 点士气。"""
        self.team1.revert_temporary_formations()
        self.team2.revert_temporary_formations()
        gained = self.current_side.gain_morale(2)
        return {
            "type": "morale_restore",
            "team_name": self.current_side.team_name,
            "amount": gained,
            "morale": self.current_side.current_morale,
            "max_morale": self.current_side.max_morale,
        }

    def _is_game_over(self) -> bool:
        """检查战斗是否结束"""
        return self.team1.is_defeated() or self.team2.is_defeated()

    def _determine_winner(self) -> str:
        """确定胜利者队伍名"""
        if self.team1.is_defeated():
            return self.team2.team_name
        if self.team2.is_defeated():
            return self.team1.team_name
        team1_hp = sum(g.current_hp for g in self.team1.get_alive_generals())
        team2_hp = sum(g.current_hp for g in self.team2.get_alive_generals())
        if team2_hp > team1_hp:
            return self.team2.team_name
        return self.team1.team_name
