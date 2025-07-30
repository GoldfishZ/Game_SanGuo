"""
阵型类
管理武将的位置布局和阵型效果
"""

from typing import List, Dict, Optional, Tuple
from enum import Enum
from ..models.general import General, Position


class FormationType(Enum):
    """阵型类型"""
    OFFENSIVE = "攻击阵型"    # 提升攻击力
    DEFENSIVE = "防御阵型"   # 提升防御力
    BALANCED = "均衡阵型"    # 平衡加成
    SPEED = "速度阵型"       # 提升速度


class Formation:
    """阵型类"""
    
    def __init__(self, formation_type: FormationType = FormationType.BALANCED):
        """
        初始化阵型
        
        Args:
            formation_type: 阵型类型
        """
        self.formation_type = formation_type
        
        # 3x3的位置网格 (前排、中排、后排，每排3个位置)
        self.positions: Dict[Tuple[int, int], Optional[General]] = {}
        for row in range(3):  # 0=前排, 1=中排, 2=后排
            for col in range(3):  # 0=左, 1=中, 2=右
                self.positions[(row, col)] = None
        
        # 阵型加成效果
        self.formation_bonuses = self._get_formation_bonuses()
    
    def _get_formation_bonuses(self) -> Dict[str, float]:
        """获取阵型加成效果"""
        bonuses = {
            FormationType.OFFENSIVE: {
                "attack_multiplier": 1.2,
                "defense_multiplier": 0.9,
                "speed_multiplier": 1.0
            },
            FormationType.DEFENSIVE: {
                "attack_multiplier": 0.9,
                "defense_multiplier": 1.3,
                "speed_multiplier": 1.0
            },
            FormationType.BALANCED: {
                "attack_multiplier": 1.1,
                "defense_multiplier": 1.1,
                "speed_multiplier": 1.1
            },
            FormationType.SPEED: {
                "attack_multiplier": 1.0,
                "defense_multiplier": 0.8,
                "speed_multiplier": 1.4
            }
        }
        return bonuses.get(self.formation_type, bonuses[FormationType.BALANCED])
    
    def place_general(self, general: General, row: int, col: int) -> bool:
        """
        放置武将到指定位置
        
        Args:
            general: 武将对象
            row: 行位置 (0=前排, 1=中排, 2=后排)
            col: 列位置 (0=左, 1=中, 2=右)
            
        Returns:
            是否放置成功
        """
        if not self._is_valid_position(row, col):
            return False
        
        if self.positions[(row, col)] is not None:
            return False  # 位置已被占用
        
        # 移除武将之前的位置
        self.remove_general(general)
        
        # 放置武将
        self.positions[(row, col)] = general
        
        # 设置武将位置属性
        if row == 0:
            general.position = Position.FRONT
        elif row == 1:
            general.position = Position.MIDDLE
        else:
            general.position = Position.BACK
        
        # 应用阵型加成
        self._apply_formation_bonus(general)
        
        return True
    
    def remove_general(self, general: General) -> bool:
        """
        移除武将
        
        Args:
            general: 要移除的武将
            
        Returns:
            是否移除成功
        """
        for pos, g in self.positions.items():
            if g is general:
                self.positions[pos] = None
                general.position = None
                self._remove_formation_bonus(general)
                return True
        return False
    
    def move_general(self, general: General, new_row: int, new_col: int) -> bool:
        """
        移动武将到新位置
        
        Args:
            general: 要移动的武将
            new_row: 新行位置
            new_col: 新列位置
            
        Returns:
            是否移动成功
        """
        if not self._is_valid_position(new_row, new_col):
            return False
        
        if self.positions[(new_row, new_col)] is not None:
            return False  # 目标位置已被占用
        
        # 找到武将当前位置并移除
        current_pos = None
        for pos, g in self.positions.items():
            if g is general:
                current_pos = pos
                break
        
        if current_pos is None:
            return False  # 武将不在阵型中
        
        # 移动武将
        self.positions[current_pos] = None
        return self.place_general(general, new_row, new_col)
    
    def swap_generals(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> bool:
        """
        交换两个位置的武将
        
        Args:
            pos1: 位置1
            pos2: 位置2
            
        Returns:
            是否交换成功
        """
        if not (self._is_valid_position(pos1[0], pos1[1]) and 
                self._is_valid_position(pos2[0], pos2[1])):
            return False
        
        general1 = self.positions[pos1]
        general2 = self.positions[pos2]
        
        self.positions[pos1] = general2
        self.positions[pos2] = general1
        
        # 更新位置属性
        if general1:
            self._update_general_position(general1, pos2)
        if general2:
            self._update_general_position(general2, pos1)
        
        return True
    
    def get_generals_by_row(self, row: int) -> List[General]:
        """获取指定行的所有武将"""
        generals = []
        for col in range(3):
            general = self.positions.get((row, col))
            if general and general.is_alive:
                generals.append(general)
        return generals
    
    def get_front_row(self) -> List[General]:
        """获取前排武将"""
        return self.get_generals_by_row(0)
    
    def get_middle_row(self) -> List[General]:
        """获取中排武将"""
        return self.get_generals_by_row(1)
    
    def get_back_row(self) -> List[General]:
        """获取后排武将"""
        return self.get_generals_by_row(2)
    
    def get_all_generals(self) -> List[General]:
        """获取所有武将"""
        generals = []
        for general in self.positions.values():
            if general and general.is_alive:
                generals.append(general)
        return generals
    
    def get_living_generals(self) -> List[General]:
        """获取所有存活的武将"""
        return [g for g in self.get_all_generals() if g.is_alive]
    
    def is_defeated(self) -> bool:
        """检查是否全军覆没"""
        return len(self.get_living_generals()) == 0
    
    def _is_valid_position(self, row: int, col: int) -> bool:
        """检查位置是否有效"""
        return 0 <= row < 3 and 0 <= col < 3
    
    def _update_general_position(self, general: General, pos: Tuple[int, int]):
        """更新武将的位置属性"""
        row = pos[0]
        if row == 0:
            general.position = Position.FRONT
        elif row == 1:
            general.position = Position.MIDDLE
        else:
            general.position = Position.BACK
    
    def _apply_formation_bonus(self, general: General):
        """应用阵型加成到武将"""
        # 这里可以实现阵型加成逻辑
        # 例如：修改武将的属性或添加特殊buff
        pass
    
    def _remove_formation_bonus(self, general: General):
        """移除武将的阵型加成"""
        # 这里可以实现移除阵型加成的逻辑
        pass
    
    def get_formation_info(self) -> Dict:
        """获取阵型信息"""
        return {
            "formation_type": self.formation_type.value,
            "bonuses": self.formation_bonuses,
            "generals_count": len(self.get_all_generals()),
            "living_count": len(self.get_living_generals())
        }
    
    def __str__(self) -> str:
        """字符串表示"""
        lines = [f"=== {self.formation_type.value} ==="]
        
        for row in range(3):
            row_name = ["前排", "中排", "后排"][row]
            generals = []
            for col in range(3):
                general = self.positions[(row, col)]
                if general:
                    generals.append(f"{general.name}({general.current_hp})")
                else:
                    generals.append("空")
            lines.append(f"{row_name}: {' | '.join(generals)}")
        
        return "\n".join(lines)
