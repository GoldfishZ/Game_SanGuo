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
        
        # 阵型系统 - 3行4列的方格 (行, 列)
        self.formation: List[List[Optional[General]]] = [[None for _ in range(4)] for _ in range(3)]
        self.formation_setup_complete = False

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
        获取最前排的武将（按列计算）
        
        Returns:
            List[General]: 最前排的武将列表
        """
        front_row_generals = []
        
        # 对每一列，找到最前排的武将
        for col in range(4):
            for row in range(3):
                if self.formation[row][col] is not None:
                    front_row_generals.append(self.formation[row][col])
                    break  # 找到该列最前排的武将就停止
                    
        return front_row_generals
    
    def get_attackable_targets(self) -> List['General']:
        """
        获取可以被攻击的目标（只有最前排的武将可以被攻击）
        
        Returns:
            List[General]: 可以被攻击的武将列表
        """
        return self.get_front_row_generals()
    
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
        return [general for general in self.generals if general.is_alive()]
    
    def get_defeated_generals(self) -> List['General']:
        """
        获取已败的武将列表
        
        Returns:
            List[General]: 已败的武将列表
        """
        return [general for general in self.generals if not general.is_alive()]
    
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
