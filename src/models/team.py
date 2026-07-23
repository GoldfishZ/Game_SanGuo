"""
队伍类
管理武将队伍和士气系统
"""

from typing import List, Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .general import General

# 导入阵营枚举
from enum import Enum

class Camp(Enum):
    """阵营枚举"""
    WEI = "魏"
    SHU = "蜀"
    WU = "吴"
    YUAN = "袁"
    QUN = "群"

class Team:
    """队伍类"""
    
    def __init__(self, team_name: str = "", camp: Camp = None, max_morale: int = 12):
        """
        初始化队伍
        
        Args:
            team_name: 队伍名称
            camp: 队伍阵营
            max_morale: 初始最大士气值（默认为12，可以通过技能修改）
        """
        self.team_name = team_name
        self.camp = camp
        self.generals: List[General] = []
        self.max_morale = 12  # 初始士气上限为12，可以通过技能修改
        self.current_morale = 12
        self.morale_spent = 0
        
        # 阵型系统 - 3行4列的方格 (行, 列)
        self.formation: List[List[Optional[General]]] = [[None for _ in range(4)] for _ in range(3)]
        self.formation_setup_complete = False
        self.temporary_formation_effects = []
        self.pending_morale_rewards = []

    def position_general(self, general: 'General', row: int, col: int) -> bool:
        """
        将武将放置到指定位置
        
        Args:
            general: 要放置的武将
            row: 行位置 (0-2)
            col: 列位置 (0-3)
            
        Returns:
            bool: 是否成功放置
        """
        if not (0 <= row < 3 and 0 <= col < 4):
            return False
            
        if self.formation[row][col] is not None:
            return False
            
        # 检查武将是否已经在其他位置
        for r in range(3):
            for c in range(4):
                if self.formation[r][c] == general:
                    self.formation[r][c] = None
                    
        self.formation[row][col] = general
        return True
    
    def get_general_position(self, general: 'General') -> Optional[Tuple[int, int]]:
        """
        获取武将的位置
        
        Args:
            general: 要查找的武将
            
        Returns:
            Tuple[int, int]: 武将的位置 (row, col)，如果未找到返回None
        """
        for row in range(3):
            for col in range(4):
                if self.formation[row][col] == general:
                    return (row, col)
        return None
    
    def get_front_row_generals(self) -> List['General']:
        """
        获取最前排的武将（按列计算），跳过已阵亡的武将

        Returns:
            List[General]: 最前排的武将列表
        """
        front_row_generals = []

        # 对每一列，找到最前排的存活武将
        for col in range(4):
            for row in range(3):
                general = self.formation[row][col]
                if general is not None and general.is_alive:
                    front_row_generals.append(general)
                    break  # 找到该列最前排的武将就停止
                    
        return front_row_generals
    
    def get_attackable_targets(self) -> List['General']:
        """
        获取可以被普攻的目标（只有最前排且未处于伏兵隐藏状态的武将可以被攻击）
        
        Returns:
            List[General]: 可以被攻击的武将列表
        """
        return [
            general for general in self.get_front_row_generals()
            if general.can_be_targeted_by_enemy(self.generals)
        ]

    def swap_general_positions(self, first: 'General', second: 'General') -> bool:
        """交换两名武将在阵型中的位置。"""
        first_pos = self.get_general_position(first)
        second_pos = self.get_general_position(second)
        if first_pos is None or second_pos is None:
            return False
        first_row, first_col = first_pos
        second_row, second_col = second_pos
        self.formation[first_row][first_col] = second
        self.formation[second_row][second_col] = first
        return True

    def knock_back_with_rear_general(self, target: 'General') -> bool:
        """将目标与同列后一格武将交换位置。"""
        target_pos = self.get_general_position(target)
        if target_pos is None:
            return False
        row, col = target_pos
        rear_row = row + 1
        if rear_row >= 3:
            return False
        rear_general = self.formation[rear_row][col]
        if rear_general is None or not rear_general.is_alive:
            return False
        return self.swap_general_positions(target, rear_general)

    def resolve_ambush_interception(self, attacker: 'General', target: 'General', damage: int) -> int:
        """伏兵反击：若目标相邻格子有隐藏伏兵，攻击者受到一半伤害的反击。

        新机制：
        - 邻格（上下左右+对角线）的隐藏伏兵可以反击
        - 反击伤害 = 造成伤害的一半
        - 每局每个伏兵只能触发一次
        - 不再交换位置
        """
        if target not in self.generals:
            return damage

        # 获取目标的位置
        target_pos = self.get_general_position(target)
        if not target_pos:
            return damage
        tr, tc = target_pos

        # 查找邻格中可触发反击的隐藏伏兵
        for general in self.get_alive_generals():
            if general == target:
                continue
            ambush_passive = general.get_passive_skill("伏兵")
            if not ambush_passive or not ambush_passive.can_counter():
                continue

            # 检查是否与目标相邻（8方向：上下左右+对角线）
            ambush_pos = self.get_general_position(general)
            if not ambush_pos:
                continue
            ar, ac = ambush_pos
            if max(abs(tr - ar), abs(tc - ac)) != 1:
                continue  # 不相邻

            # 触发反击！
            counter_damage = max(1, damage // 2)
            ambush_passive.trigger_counter()
            actual_counter = attacker.take_damage(counter_damage, general, "ambush_counter")
            general.record_combat_event(
                "ambush_counter", attacker=attacker.name,
                attacker_id=attacker.general_id, protected=target.name,
                protected_id=target.general_id, damage=actual_counter,
            )
            # 只触发一个伏兵的反击
            break

        return damage

    def get_front_target_in_column(self, col: int) -> Optional['General']:
        """获取指定列最前方且可被普攻选中的目标。"""
        if not (0 <= col < 4):
            return None
        for row in range(3):
            general = self.formation[row][col]
            if general is not None and general.can_be_targeted_by_enemy(self.generals):
                return general
        return None

    def apply_temporary_2x2_rearrangement(self, selected_row=None, selected_col=None) -> dict:
        """临时重排敌方一个 2x2 方格内的武将，回合结束后可恢复。"""
        best_positions = []
        best_generals = []

        if selected_row is not None and selected_col is not None:
            row = max(0, min(1, int(selected_row)))
            col = max(0, min(2, int(selected_col)))
            best_positions = [
                (row, col), (row, col + 1),
                (row + 1, col), (row + 1, col + 1),
            ]
            best_generals = [
                self.formation[r][c]
                for r, c in best_positions
                if self.formation[r][c] is not None
                and self.formation[r][c].is_alive
            ]

        if selected_row is None or selected_col is None:
            for row in range(2):
                for col in range(3):
                    block_positions = [
                        (row, col), (row, col + 1),
                        (row + 1, col), (row + 1, col + 1),
                    ]
                    block_generals = [
                        self.formation[r][c]
                        for r, c in block_positions
                        if self.formation[r][c] is not None
                        and self.formation[r][c].is_alive
                    ]
                    if len(block_generals) > len(best_generals):
                        best_positions = block_positions
                        best_generals = block_generals

        if not best_generals:
            return {"success": False, "message": "目标 2x2 方格内没有可移动武将"}

        original_positions = {
            general: self.get_general_position(general)
            for general in best_generals
        }
        occupied_positions = [original_positions[general] for general in best_generals]
        new_positions = list(reversed(occupied_positions))

        for general in best_generals:
            current_pos = self.get_general_position(general)
            if current_pos:
                self.formation[current_pos[0]][current_pos[1]] = None

        moves = []
        for general, new_pos in zip(best_generals, new_positions):
            self.formation[new_pos[0]][new_pos[1]] = general
            moves.append({
                "general": general.name,
                "from": original_positions[general],
                "to": new_pos,
            })

        self.temporary_formation_effects.append({
            "generals": list(best_generals),
            "positions": original_positions,
        })

        return {
            "success": True,
            "block": best_positions,
            "moves": moves,
        }

    def revert_temporary_formations(self) -> None:
        """恢复本回合临时阵型调整。"""
        while self.temporary_formation_effects:
            effect = self.temporary_formation_effects.pop()
            generals = effect["generals"]
            original_positions = effect["positions"]

            for general in generals:
                current_pos = self.get_general_position(general)
                if current_pos:
                    self.formation[current_pos[0]][current_pos[1]] = None

            for general, position in original_positions.items():
                if general.is_alive and position:
                    self.formation[position[0]][position[1]] = general
    
    def is_position_empty(self, row: int, col: int) -> bool:
        """
        检查指定位置是否为空
        
        Args:
            row: 行位置 (0-2)
            col: 列位置 (0-3)
            
        Returns:
            bool: 位置是否为空
        """
        if not (0 <= row < 3 and 0 <= col < 4):
            return False
        return self.formation[row][col] is None
    
    def remove_general_from_formation(self, general: 'General') -> bool:
        """
        从阵型中移除武将
        
        Args:
            general: 要移除的武将
            
        Returns:
            bool: 是否成功移除
        """
        for row in range(3):
            for col in range(4):
                if self.formation[row][col] == general:
                    self.formation[row][col] = None
                    return True
        return False
    
    def setup_formation_phase(self) -> bool:
        """
        开始阵型布置阶段
        
        Returns:
            bool: 是否可以开始布置
        """
        if len(self.generals) == 0:
            return False
        
        # 重置阵型
        self.formation = [[None for _ in range(4)] for _ in range(3)]
        self.formation_setup_complete = False
        return True
    
    def complete_formation_setup(self) -> bool:
        """
        完成阵型布置
        
        Returns:
            bool: 是否成功完成布置
        """
        # 检查所有武将是否都已放置
        placed_generals = []
        for row in range(3):
            for col in range(4):
                if self.formation[row][col] is not None:
                    placed_generals.append(self.formation[row][col])
        
        if len(placed_generals) != len(self.generals):
            return False
            
        self.formation_setup_complete = True
        return True
    
    def get_formation_display(self) -> str:
        """
        获取阵型的显示字符串
        
        Returns:
            str: 阵型显示字符串
        """
        display = f"{self.team_name} 阵型:\n"
        for row in range(3):
            row_str = ""
            for col in range(4):
                general = self.formation[row][col]
                if general is not None:
                    row_str += f"[{general.name[:2]}]"
                else:
                    row_str += "[  ]"
                if col < 3:
                    row_str += " "
            display += row_str + "\n"
        return display

    def add_general(self, general: 'General') -> bool:
        """
        添加武将到队伍

        Args:
            general: 要添加的武将

        Returns:
            bool: 是否成功添加
        """
        if general not in self.generals:
            self.generals.append(general)
            general._team = self  # 设置队伍引用（用于连环等被动技能）
            return True
        return False

    def remove_general(self, general: 'General') -> bool:
        """
        从队伍中移除武将

        Args:
            general: 要移除的武将

        Returns:
            bool: 是否成功移除
        """
        if general in self.generals:
            self.generals.remove(general)
            general._team = None  # 清除队伍引用
            # 同时从阵型中移除
            self.remove_general_from_formation(general)
            return True
        return False
    
    def get_alive_generals(self) -> List['General']:
        """
        获取存活的武将列表

        Returns:
            List[General]: 存活的武将列表
        """
        return [general for general in self.generals if general.is_alive]

    def get_living_generals(self) -> List['General']:
        """获取存活武将列表（get_alive_generals 的别名）"""
        return self.get_alive_generals()

    def get_defeated_generals(self) -> List['General']:
        """
        获取已败的武将列表

        Returns:
            List[General]: 已败的武将列表
        """
        return [general for general in self.generals if not general.is_alive]

    def get_dead_generals(self) -> List['General']:
        """获取已阵亡武将列表（get_defeated_generals 的别名）"""
        return self.get_defeated_generals()
    
    def is_defeated(self) -> bool:
        """
        检查队伍是否已败（所有武将都被击败）
        
        Returns:
            bool: 队伍是否已败
        """
        return len(self.get_alive_generals()) == 0
    
    def calculate_team_force(self) -> int:
        """
        计算队伍总武力值（存活武将的武力值之和）
        
        Returns:
            int: 队伍总武力值
        """
        return sum(general.force for general in self.get_alive_generals())
    
    def calculate_team_intelligence(self) -> int:
        """
        计算队伍总智力值（存活武将的智力值之和）
        
        Returns:
            int: 队伍总智力值
        """
        return sum(general.intelligence for general in self.get_alive_generals())
    
    def get_morale_status(self) -> str:
        """
        获取士气状态描述
        
        Returns:
            str: 士气状态描述
        """
        ratio = self.current_morale / self.max_morale
        if ratio >= 0.8:
            return "士气高昂"
        elif ratio >= 0.6:
            return "士气良好"
        elif ratio >= 0.4:
            return "士气一般"
        elif ratio >= 0.2:
            return "士气低落"
        else:
            return "士气涣散"
    
    def lose_morale(self, amount: int) -> int:
        """
        失去士气
        
        Args:
            amount: 失去的士气值
            
        Returns:
            int: 实际失去的士气值
        """
        actual_loss = min(amount, self.current_morale)
        self.current_morale -= actual_loss
        return actual_loss
    
    def gain_morale(self, amount: int) -> int:
        """
        获得士气
        
        Args:
            amount: 获得的士气值
            
        Returns:
            int: 实际获得的士气值
        """
        actual_gain = min(amount, self.max_morale - self.current_morale)
        self.current_morale += actual_gain
        return actual_gain
    
    def set_max_morale(self, new_max: int) -> None:
        """
        设置最大士气值
        
        Args:
            new_max: 新的最大士气值
        """
        old_max = self.max_morale
        self.max_morale = new_max
        
        # 如果当前士气超过新的上限，则调整到上限
        if self.current_morale > self.max_morale:
            self.current_morale = self.max_morale
    
    def reset_morale(self) -> None:
        """重置士气到最大值"""
        self.current_morale = self.max_morale
    
    def consume_morale(self, amount: int) -> bool:
        """
        消耗士气（技能使用时的士气扣除）

        Args:
            amount: 要消耗的士气值

        Returns:
            bool: 是否成功消耗
        """
        if self.current_morale < amount:
            return False
        self.current_morale -= amount
        self.morale_spent += amount
        return True

    def add_pending_morale_reward(
            self,
            amount: int,
            delay_turns: int,
            required_alive_generals: List['General'] = None) -> None:
        """添加延迟士气奖励，结算时要求指定武将仍然存活。"""
        self.pending_morale_rewards.append({
            "amount": amount,
            "delay_turns": max(1, delay_turns),
            "required_alive_generals": list(required_alive_generals or []),
        })

    def resolve_pending_morale_rewards(self) -> None:
        """结算到期的延迟士气奖励。"""
        remaining_rewards = []
        for reward in self.pending_morale_rewards:
            reward["delay_turns"] -= 1
            if reward["delay_turns"] <= 0:
                required_generals = reward.get("required_alive_generals", [])
                if all(general.is_alive for general in required_generals):
                    self.gain_morale(reward["amount"])
            else:
                remaining_rewards.append(reward)
        self.pending_morale_rewards = remaining_rewards

    def can_use_skill(self, general: 'General') -> bool:
        """
        检查武将是否可以使用主动技能

        Args:
            general: 要检查的武将

        Returns:
            bool: 是否可以使用技能
        """
        if not general.is_alive:
            return False
        if not general.active_skill:
            return False
        if general.active_skill_cooldown > 0:
            return False
        if self.current_morale < general.active_skill.morale_cost:
            return False
        return True

    def use_skill(self, general: 'General', targets: list, battle_context) -> dict:
        """
        使用武将的主动技能

        Args:
            general: 使用技能的武将
            targets: 目标列表
            battle_context: 战斗上下文

        Returns:
            dict: 技能使用结果
        """
        return general.use_active_skill(targets, battle_context, self)

    def update_effects(self):
        """更新队伍中所有武将的回合开始被动、效果持续时间和技能冷却"""
        events = []
        self.resolve_pending_morale_rewards()
        for general in self.generals:
            if general.is_alive:
                events.extend(general.trigger_turn_start_passives())
            general.update_effects()
        return events

    def get_team_info(self) -> str:
        """
        获取队伍信息字符串
        
        Returns:
            str: 队伍信息
        """
        alive_count = len(self.get_alive_generals())
        total_count = len(self.generals)
        defeated_count = total_count - alive_count
        
        info = f"队伍: {self.team_name}\n"
        if self.camp:
            info += f"阵营: {self.camp.value}\n"
        info += f"武将: {alive_count}/{total_count} (存活/总数)\n"
        if defeated_count > 0:
            info += f"败将: {defeated_count}\n"
        info += f"士气: {self.current_morale}/{self.max_morale} ({self.get_morale_status()})\n"
        info += f"总武力: {self.calculate_team_force()}\n"
        info += f"总智力: {self.calculate_team_intelligence()}\n"
        
        return info
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Team({self.team_name}, {len(self.generals)} generals, {self.current_morale}/{self.max_morale} morale)"
    
    def __repr__(self) -> str:
        """调试用字符串表示"""
        return self.__str__()
